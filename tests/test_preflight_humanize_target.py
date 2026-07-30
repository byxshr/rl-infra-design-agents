from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PREFLIGHT = ROOT / "scripts" / "preflight_humanize_target.py"
TARGET_PLAN = "docs/superpowers/rlcr/test-plan.md"


def run(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True)


def load_preflight_module():
    spec = importlib.util.spec_from_file_location("preflight_humanize_target_under_test", PREFLIGHT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run(["git", *args], cwd=repo)


def commit_all(repo: Path, message: str) -> None:
    add = git(repo, "add", "-A")
    assert add.returncode == 0, add.stderr
    commit = git(repo, "commit", "-m", message)
    assert commit.returncode == 0, commit.stderr


def make_target(tmp_path: Path) -> tuple[Path, Path, Path]:
    target = tmp_path / "target"
    workspace = tmp_path / "workspace"
    target.mkdir()
    workspace_plan = workspace / "docs" / "plan.md"
    workspace_plan.parent.mkdir(parents=True)
    workspace_plan.write_text("# Test Plan\n\nImplement the requested target change.\n", encoding="utf-8")
    plan_hash = hashlib.sha256(workspace_plan.read_bytes()).hexdigest()
    plan_lock = workspace / ".humanize" / "plan.lock.md"
    plan_lock.parent.mkdir(parents=True)
    plan_lock.write_text(f"# Plan Lock\n\n- plan_sha256: {plan_hash}\n", encoding="utf-8")

    init = git(target, "init", "-b", "main")
    assert init.returncode == 0, init.stderr
    assert git(target, "config", "user.email", "imp018@example.com").returncode == 0
    assert git(target, "config", "user.name", "IMP 018 Test").returncode == 0
    target_plan = target / TARGET_PLAN
    target_plan.parent.mkdir(parents=True)
    target_plan.write_bytes(workspace_plan.read_bytes())
    (target / ".gitignore").write_text("# tracked ignore file\n", encoding="utf-8")
    commit_all(target, "Initialize target")

    bridge_path = workspace / ".humanize" / "rlinfra_bridge.json"
    bridge_path.parent.mkdir(parents=True, exist_ok=True)
    bridge_path.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "execution_mode": "target_repo",
                "workspace": str(workspace.resolve()),
                "target_repo": str(target.resolve()),
                "diff_base": "main",
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return target, workspace, target_plan


def run_preflight(
    target: Path,
    workspace: Path,
    *,
    target_plan: str = TARGET_PLAN,
    diff_base: str = "main",
) -> subprocess.CompletedProcess[str]:
    return run(
        [
            sys.executable,
            str(PREFLIGHT),
            "--target-repo",
            str(target),
            "--workspace",
            str(workspace),
            "--target-plan",
            target_plan,
            "--diff-base",
            diff_base,
            "--print-json",
        ],
        cwd=ROOT,
    )


def test_preflight_passes_and_idempotently_adds_local_exclude(tmp_path):
    target, workspace, _ = make_target(tmp_path)
    gitignore_before = (target / ".gitignore").read_text(encoding="utf-8")

    first = run_preflight(target, workspace)
    second = run_preflight(target, workspace)

    assert first.returncode == 0, first.stdout + first.stderr
    assert second.returncode == 0, second.stdout + second.stderr
    first_report = json.loads(first.stdout)
    second_report = json.loads(second.stdout)
    assert first_report["status"] == "passed"
    assert first_report["checks"]["local_ignore"]["updated"] is True
    assert second_report["checks"]["local_ignore"]["updated"] is False
    assert first_report["plan_sha256"] == first_report["checks"]["target_plan"]["prepared_sha256"]
    assert first_report["checks"]["working_tree"] == {
        "passed": True,
        "entry_count": 0,
        "entries": [],
        "tracked_entries": [],
        "untracked_entries": [],
        "staged_entries": [],
        "unstaged_entries": [],
    }
    exclude_path = Path(git(target, "rev-parse", "--git-path", "info/exclude").stdout.strip())
    if not exclude_path.is_absolute():
        exclude_path = target / exclude_path
    assert exclude_path.read_text(encoding="utf-8").splitlines().count("/.humanize/") == 1
    nested = git(target, "check-ignore", "--no-index", "--", "nested/.humanize/state.md")
    assert nested.returncode == 1
    assert (target / ".gitignore").read_text(encoding="utf-8") == gitignore_before
    assert git(target, "status", "--short").stdout == ""
    assert git(target, "ls-files", "--", ".humanize").stdout == ""
    on_disk = json.loads((workspace / ".humanize" / "rlinfra_target_preflight.json").read_text(encoding="utf-8"))
    assert on_disk["report_path"].endswith("rlinfra_target_preflight.json")


@pytest.mark.parametrize(
    "invalid_plan",
    [
        "/tmp/absolute-plan.md",
        "../outside-plan.md",
        "docs/plan with spaces.md",
        ".humanize/plan.md",
    ],
)
def test_preflight_rejects_unsafe_target_plan_paths(tmp_path, invalid_plan):
    target, workspace, _ = make_target(tmp_path)

    result = run_preflight(target, workspace, target_plan=invalid_plan)

    assert result.returncode == 3
    report = json.loads(result.stdout)
    assert report["status"] == "failed"
    assert report["errors"]
    assert len(report["remediation"]) == 1
    assert "relative plan path outside .humanize" in report["remediation"][0]


def test_preflight_rejects_bridge_target_mismatch(tmp_path):
    target, workspace, _ = make_target(tmp_path)
    bridge_path = workspace / ".humanize" / "rlinfra_bridge.json"
    bridge = json.loads(bridge_path.read_text(encoding="utf-8"))
    bridge["target_repo"] = str(tmp_path / "wrong-target")
    bridge_path.write_text(json.dumps(bridge), encoding="utf-8")

    result = run_preflight(target, workspace)

    assert result.returncode == 3
    report = json.loads(result.stdout)
    assert "bridge target_repo does not match" in report["errors"][0]
    assert report["error_code"] == "bridge_metadata"
    assert "target-aware prepare/start flow" in report["remediation"][0]


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("schema_version", 1, "schema v2 target_repo"),
        ("execution_mode", "workspace", "schema v2 target_repo"),
        ("workspace", "/tmp/wrong-workspace", "bridge workspace does not match"),
    ],
)
def test_preflight_rejects_incompatible_bridge_metadata(tmp_path, field, value, message):
    target, workspace, _ = make_target(tmp_path)
    bridge_path = workspace / ".humanize" / "rlinfra_bridge.json"
    bridge = json.loads(bridge_path.read_text(encoding="utf-8"))
    bridge[field] = value
    bridge_path.write_text(json.dumps(bridge), encoding="utf-8")

    result = run_preflight(target, workspace)

    assert result.returncode == 3
    assert message in result.stdout


def test_preflight_rejects_symlink_target_plan(tmp_path):
    target, workspace, target_plan = make_target(tmp_path)
    target_plan.unlink()
    target_plan.symlink_to(workspace / "docs" / "plan.md")
    assert git(target, "add", "--", TARGET_PLAN).returncode == 0
    assert git(target, "commit", "-m", "Replace plan with symlink").returncode == 0

    result = run_preflight(target, workspace)

    assert result.returncode == 3
    assert "must not be a symlink" in result.stdout
    report = json.loads(result.stdout)
    assert report["error_code"] == "symlink_target_plan"


@pytest.mark.parametrize("scenario", ["untracked", "dirty", "hash-drift", "dirty-tree", "tracked-humanize"])
def test_preflight_rejects_target_hygiene_failures(tmp_path, scenario):
    target, workspace, target_plan = make_target(tmp_path)
    if scenario == "untracked":
        assert git(target, "rm", "--cached", TARGET_PLAN).returncode == 0
    elif scenario == "dirty":
        target_plan.write_text(target_plan.read_text(encoding="utf-8") + "dirty\n", encoding="utf-8")
    elif scenario == "hash-drift":
        target_plan.write_text("# Different committed plan\n", encoding="utf-8")
        commit_all(target, "Change target plan")
    elif scenario == "dirty-tree":
        (target / "untracked.txt").write_text("dirty\n", encoding="utf-8")
    elif scenario == "tracked-humanize":
        state = target / ".humanize" / "state.md"
        state.parent.mkdir(parents=True)
        state.write_text("local state\n", encoding="utf-8")
        assert git(target, "add", "-f", ".humanize/state.md").returncode == 0
        assert git(target, "commit", "-m", "Track forbidden state").returncode == 0

    result = run_preflight(target, workspace)

    assert result.returncode == 3, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == "failed"
    assert report["errors"]
    if scenario == "tracked-humanize":
        assert "tracked Humanize state is forbidden" in report["errors"][0]
        assert report["error_code"] == "tracked_humanize"
    if scenario == "dirty-tree":
        assert report["error_code"] == "working_tree_dirty"
        assert report["checks"]["working_tree"]["entries"] == ["?? untracked.txt"]
        assert report["checks"]["working_tree"]["tracked_entries"] == []
        assert report["checks"]["working_tree"]["untracked_entries"] == ["untracked.txt"]
        assert "0 tracked/staged entries and 1 untracked entries" in report["remediation"][1]
    if scenario == "hash-drift":
        assert report["error_code"] == "plan_hash_mismatch"
        assert "shasum" not in report["remediation"][0]
        assert sys.executable in report["remediation"][0]


def test_preflight_rejects_stale_plan_lock(tmp_path):
    target, workspace, _ = make_target(tmp_path)
    lock = workspace / ".humanize" / "plan.lock.md"
    lock.write_text("# Plan Lock\n\n- plan_sha256: " + "0" * 64 + "\n", encoding="utf-8")

    result = run_preflight(target, workspace)

    assert result.returncode == 3
    report = json.loads(result.stdout)
    assert report["error_code"] == "plan_lock"
    assert "plan lock does not match" in report["errors"][0]
    assert "restore the intended plan content" in report["remediation"][0]
    assert "lock_plan.py" in report["remediation"][1]
    lock_command = report["remediation"][1]
    assert str((ROOT / ".agents" / "skills" / "RLInfraWiki" / "scripts" / "lock_plan.py").resolve()) in lock_command


def test_dirty_tree_report_classifies_entries_and_caps_error_message(tmp_path):
    target, workspace, _ = make_target(tmp_path)
    (target / ".gitignore").write_text("# modified\n", encoding="utf-8")
    for index in range(25):
        (target / f"generated-{index:02d}.txt").write_text("local\n", encoding="utf-8")

    result = run_preflight(target, workspace)

    assert result.returncode == 3
    report = json.loads(result.stdout)
    tree = report["checks"]["working_tree"]
    assert tree["entry_count"] == 26
    assert tree["tracked_entries"] == [" M .gitignore"]
    assert len(tree["untracked_entries"]) == 25
    assert tree["staged_entries"] == []
    assert tree["unstaged_entries"] == [" M .gitignore"]
    assert "first 20" in report["errors"][0]
    assert "6 additional entries omitted" in report["errors"][0]
    assert "1 tracked/staged entries and 25 untracked entries" in report["remediation"][1]


def test_dirty_tree_report_preserves_raw_space_and_unicode_paths(tmp_path):
    target, workspace, _ = make_target(tmp_path)
    (target / "my notes.md").write_text("local\n", encoding="utf-8")
    (target / "spécial.md").write_text("local\n", encoding="utf-8")

    result = run_preflight(target, workspace)

    assert result.returncode == 3
    report = json.loads(result.stdout)
    assert report["checks"]["working_tree"]["untracked_entries"] == ["my notes.md", "spécial.md"]
    assert '"my notes.md"' not in report["checks"]["working_tree"]["untracked_entries"]
    assert "\\303" not in json.dumps(report["checks"]["working_tree"], ensure_ascii=False)


def test_remediation_failure_still_writes_report(tmp_path, monkeypatch):
    module = load_preflight_module()
    target, workspace, _ = make_target(tmp_path)
    bridge_path = workspace / ".humanize" / "rlinfra_bridge.json"
    bridge = json.loads(bridge_path.read_text(encoding="utf-8"))
    bridge["target_repo"] = str(tmp_path / "wrong-target")
    bridge_path.write_text(json.dumps(bridge), encoding="utf-8")
    report_path = workspace / "custom-report.json"

    def fail_remediation(*args, **kwargs):
        raise RuntimeError("synthetic remediation failure")

    monkeypatch.setattr(module, "remediation_for", fail_remediation)
    code, report = module.run_preflight(
        argparse.Namespace(
            target_repo=str(target),
            workspace=str(workspace),
            target_plan=TARGET_PLAN,
            diff_base="main",
            report=str(report_path),
        )
    )

    assert code == 3
    assert report_path.exists()
    on_disk = json.loads(report_path.read_text(encoding="utf-8"))
    assert on_disk == report
    assert "failed safely" in report["remediation"][0]
    assert "synthetic remediation failure" in report["remediation"][0]


def test_preflight_rejects_non_local_diff_base(tmp_path):
    target, workspace, _ = make_target(tmp_path)
    bridge_path = workspace / ".humanize" / "rlinfra_bridge.json"
    bridge = json.loads(bridge_path.read_text(encoding="utf-8"))
    bridge["diff_base"] = "missing-base"
    bridge_path.write_text(json.dumps(bridge), encoding="utf-8")

    result = run_preflight(target, workspace, diff_base="missing-base")

    assert result.returncode == 3
    assert "diff base is not a local branch" in result.stdout
