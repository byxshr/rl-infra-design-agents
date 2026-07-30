from __future__ import annotations

import argparse
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
START = ROOT / "scripts" / "start_humanize_task.py"
PREPARE = ROOT / "scripts" / "prepare_humanize_task.py"
CONTRACT = ROOT / "examples" / "task_contracts" / "training-rollout-mismatch-debug.yaml"
TARGET_PLAN = "docs/superpowers/rlcr/test-plan.md"


def run_command(
    args: list[str], *, env: dict[str, str] | None = None, cwd: Path = ROOT
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True, env=env)


def run_start(workspace: Path, *extra: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return run_command(
        [
            sys.executable,
            str(START),
            "--contract",
            str(CONTRACT),
            "--workspace",
            str(workspace),
            "--force",
            "--overwrite-human-docs",
            *extra,
        ],
        env=env,
    )


def load_start_module():
    scripts_dir = ROOT / "scripts"
    if str(scripts_dir) not in sys.path:
        sys.path.insert(0, str(scripts_dir))
    spec = importlib.util.spec_from_file_location("start_humanize_task_under_test", START)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return run_command(["git", *args], cwd=repo)


def prepare_target_mode(tmp_path: Path) -> tuple[Path, Path]:
    target = tmp_path / "target with spaces"
    workspace = tmp_path / "workspace"
    target.mkdir()
    assert git(target, "init", "-b", "main").returncode == 0
    assert git(target, "config", "user.email", "imp018@example.com").returncode == 0
    assert git(target, "config", "user.name", "IMP 018 Test").returncode == 0
    (target / "README.md").write_text("# Target\n", encoding="utf-8")
    assert git(target, "add", "README.md").returncode == 0
    assert git(target, "commit", "-m", "Initialize target").returncode == 0

    prepared = run_command(
        [
            sys.executable,
            str(PREPARE),
            "--contract",
            str(CONTRACT),
            "--workspace",
            str(workspace),
            "--target-repo",
            str(target),
            "--diff-base",
            "main",
            "--force",
            "--overwrite-human-docs",
        ]
    )
    assert prepared.returncode == 0, prepared.stdout + prepared.stderr
    target_plan = target / TARGET_PLAN
    target_plan.parent.mkdir(parents=True)
    target_plan.write_bytes((workspace / "docs" / "plan.md").read_bytes())
    assert git(target, "add", TARGET_PLAN).returncode == 0
    assert git(target, "commit", "-m", "Add RLCR plan").returncode == 0
    return target, workspace


def run_target_start(target: Path, workspace: Path) -> subprocess.CompletedProcess[str]:
    return run_command(
        [
            sys.executable,
            str(START),
            "--contract",
            str(CONTRACT),
            "--workspace",
            str(workspace),
            "--target-repo",
            str(target),
            "--target-plan",
            TARGET_PLAN,
            "--diff-base",
            "main",
            "--force",
        ]
    )


def test_start_generates_operator_artifacts_and_does_not_create_loop(tmp_path):
    workspace = tmp_path / "workspace"

    result = run_start(workspace, "--round", "1")

    assert result.returncode == 0, result.stdout + result.stderr
    operator_doc = workspace / "humanize_operator.md"
    operator_metadata = workspace / ".humanize" / "rlinfra_operator.json"
    bridge_metadata = workspace / ".humanize" / "rlinfra_bridge.json"
    assert operator_doc.exists()
    assert operator_metadata.exists()
    assert bridge_metadata.exists()
    assert not (workspace / ".humanize" / "rlcr").exists()

    doc_text = operator_doc.read_text(encoding="utf-8")
    assert "/humanize:start-rlcr-loop docs/plan.md" in doc_text
    assert "make import-humanize-round" in doc_text
    assert "validate_review_gate.py" in doc_text
    assert "source-reported" in doc_text
    assert "RLInfraWiki page IDs and source IDs" in doc_text
    assert "IMP-014 owns this import boundary" in doc_text

    metadata = json.loads(operator_metadata.read_text(encoding="utf-8"))
    assert metadata["schema_version"] == 2
    assert metadata["execution_mode"] == "workspace"
    assert metadata["contract"] == str(CONTRACT.resolve())
    assert metadata["workspace"] == str(workspace.resolve())
    assert metadata["round"] == 1
    assert metadata["prepare_metadata_path"] == str(bridge_metadata.resolve())
    assert metadata["bridge_metadata_path"] == str(bridge_metadata.resolve())
    assert metadata["commands"]["humanize_start"] == "/humanize:start-rlcr-loop docs/plan.md"
    assert "make import-humanize-round" in metadata["commands"]["import_round"]
    assert "HUMANIZE_LOOP_DIR=" in metadata["commands"]["import_round_with_loop_dir"]
    assert "{{TIMESTAMP}}" in metadata["commands"]["import_round_with_loop_dir"]
    assert metadata["commands"]["python"] == sys.executable
    assert "validate_review_gate.py" in metadata["commands"]["review_gate"]
    assert isinstance(metadata["prereq_warnings"], list)


def test_print_json_outputs_parseable_operator_metadata(tmp_path):
    workspace = tmp_path / "workspace"

    result = run_start(workspace, "--print-json", "--round", "2")

    assert result.returncode == 0, result.stdout + result.stderr
    metadata = json.loads(result.stdout)
    assert metadata["workspace"] == str(workspace.resolve())
    assert metadata["round"] == 2
    assert metadata["prepare_metadata_path"].endswith(".humanize/rlinfra_bridge.json")
    assert metadata == json.loads((workspace / ".humanize" / "rlinfra_operator.json").read_text(encoding="utf-8"))
    assert "Humanize task workspace is ready." in result.stderr


def test_missing_contract_fails_with_prepare_stage(tmp_path):
    workspace = tmp_path / "workspace"
    missing_contract = tmp_path / "missing.yaml"

    result = run_command(
        [
            sys.executable,
            str(START),
            "--contract",
            str(missing_contract),
            "--workspace",
            str(workspace),
            "--force",
            "--overwrite-human-docs",
        ]
    )

    assert result.returncode != 0
    assert "stage prepare_humanize_task failed" in result.stderr
    assert "missing contract" in result.stderr
    assert not (workspace / ".humanize" / "rlinfra_operator.json").exists()


def test_invalid_round_and_empty_diff_base_fail_before_prepare(tmp_path):
    workspace = tmp_path / "workspace"

    invalid_round = run_start(workspace, "--round", "0")
    assert invalid_round.returncode != 0
    assert "must be >= 1" in invalid_round.stderr
    assert not (workspace / ".humanize" / "rlinfra_operator.json").exists()

    empty_diff_base = run_start(workspace, "--diff-base", "")
    assert empty_diff_base.returncode != 0
    assert "must not be empty" in empty_diff_base.stderr
    assert not (workspace / ".humanize" / "rlinfra_operator.json").exists()


def test_strict_prereq_failure_preserves_prepare_exit_code(tmp_path):
    workspace = tmp_path / "workspace"
    env = dict(os.environ)
    env["PATH"] = ""
    env.pop("HUMANIZE_ROOT", None)

    result = run_start(workspace, "--strict-prereqs", env=env)

    assert result.returncode == 2, result.stdout + result.stderr
    assert "stage prepare_humanize_task failed" in result.stderr
    assert "--strict-prereqs requested" in result.stderr
    assert "Humanize task workspace is ready." not in result.stdout
    assert not (workspace / ".humanize" / "rlinfra_operator.json").exists()


def test_print_json_strict_prereq_failure_leaves_stdout_empty(tmp_path):
    workspace = tmp_path / "workspace"
    env = dict(os.environ)
    env["PATH"] = ""
    env.pop("HUMANIZE_ROOT", None)

    result = run_start(workspace, "--strict-prereqs", "--print-json", env=env)

    assert result.returncode == 2, result.stdout + result.stderr
    assert result.stdout == ""
    assert "stage prepare_humanize_task failed" in result.stderr
    assert not (workspace / ".humanize" / "rlinfra_operator.json").exists()


def test_workspace_paths_with_spaces_are_quoted_in_commands(tmp_path):
    workspace = tmp_path / "workspace with spaces"

    result = run_start(workspace)

    assert result.returncode == 0, result.stdout + result.stderr
    metadata = json.loads((workspace / ".humanize" / "rlinfra_operator.json").read_text(encoding="utf-8"))
    quoted_workspace = f"'{workspace.resolve()}'"
    assert metadata["commands"]["enter_workspace"] == f"cd {quoted_workspace}"
    assert f"HUMANIZE_WORKSPACE={quoted_workspace}" in metadata["commands"]["import_round"]
    assert quoted_workspace in metadata["commands"]["review_gate"]


@pytest.mark.parametrize("target", ["prepare-humanize-task", "start-humanize-task"])
def test_make_humanize_targets_preserve_docs_unless_explicitly_overridden(tmp_path, target):
    common = ["make", "-n", target, f"HUMANIZE_WORKSPACE={tmp_path / 'workspace'}"]

    default = run_command(common)
    explicit = run_command([*common, "HUMANIZE_OVERWRITE_DOCS=1"])

    assert default.returncode == 0, default.stdout + default.stderr
    assert "--overwrite-human-docs" not in default.stdout
    assert explicit.returncode == 0, explicit.stdout + explicit.stderr
    assert "--overwrite-human-docs" in explicit.stdout


def test_unsupported_bridge_schema_fails_before_operator_doc_write(tmp_path, monkeypatch, capsys):
    module = load_start_module()
    workspace = tmp_path / "workspace"
    bridge_metadata_path = workspace / module.BRIDGE_METADATA_RELPATH
    bridge_metadata_path.parent.mkdir(parents=True)
    bridge_metadata_path.write_text(json.dumps({"schema_version": 99, "prereq_warnings": []}), encoding="utf-8")

    def fake_run_prepare(argv, *, root, print_json, timeout):
        return subprocess.CompletedProcess(argv, 0, stdout="", stderr="")

    monkeypatch.setattr(module, "run_prepare", fake_run_prepare)
    args = argparse.Namespace(
        contract=str(CONTRACT),
        workspace=str(workspace),
        target_repo=None,
        target_plan=None,
        diff_base="main",
        round=1,
        force=True,
        overwrite_human_docs=True,
        strict_prereqs=False,
        prepare_timeout=300,
        accept_bridge_schema=[],
        print_json=False,
    )

    result = module.start(args)

    captured = capsys.readouterr()
    assert result == 1
    assert "unsupported prepare bridge schema_version: 99" in captured.err
    assert not (workspace / "humanize_operator.md").exists()
    assert not (workspace / ".humanize" / "rlinfra_operator.json").exists()


def test_missing_bridge_schema_has_specific_error_message():
    module = load_start_module()

    with pytest.raises(module.StartError, match="missing prepare bridge schema_version"):
        module.validate_prepare_bridge_schema({}, [])


def test_run_prepare_timeout_returns_124(capsys):
    module = load_start_module()

    result = module.run_prepare(
        [sys.executable, "-c", "import time; time.sleep(5)"],
        root=ROOT,
        print_json=False,
        timeout=1,
    )

    captured = capsys.readouterr()
    assert result.returncode == 124
    assert "Command timed out after 1 seconds." in result.stderr
    assert "Command timed out after 1 seconds." in captured.err


def test_start_output_includes_three_step_operator_flow(tmp_path):
    workspace = tmp_path / "workspace"

    result = run_start(workspace)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "1. In Claude Code:" in result.stdout
    assert f"cd {workspace.resolve()}" in result.stdout
    assert "/humanize:start-rlcr-loop docs/plan.md" in result.stdout
    assert "2. After Humanize writes a round" in result.stdout
    assert "make import-humanize-round" in result.stdout
    assert "3. Run the review gate:" in result.stdout
    assert "validate_review_gate.py" in result.stdout


def test_target_mode_generates_launcher_and_launches_from_target_root(tmp_path):
    target, workspace = prepare_target_mode(tmp_path)

    result = run_target_start(target, workspace)

    assert result.returncode == 0, result.stdout + result.stderr
    launcher = workspace / "launch_humanize.sh"
    metadata_path = workspace / ".humanize" / "rlinfra_operator.json"
    report_path = workspace / ".humanize" / "rlinfra_target_preflight.json"
    assert launcher.exists()
    assert launcher.stat().st_mode & 0o111
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert metadata["schema_version"] == 2
    assert metadata["execution_mode"] == "target_repo"
    assert metadata["target_plan"] == TARGET_PLAN
    assert metadata["target_preflight"]["status"] == "passed"
    assert metadata["plan_sha256"] == metadata["target_preflight"]["plan_sha256"]
    assert metadata["commands"]["humanize_start"] == (
        f"/humanize:start-rlcr-loop {TARGET_PLAN} --track-plan-file --base-branch main"
    )
    assert str(target / ".humanize" / "rlcr" / "{{TIMESTAMP}}") in metadata["commands"]["import_round_with_loop_dir"]
    assert report_path.exists()

    capture = tmp_path / "claude-cwd.txt"
    fake_claude = tmp_path / "fake-claude.sh"
    fake_claude.write_text(
        '#!/usr/bin/env bash\nprintf "%s\\n" "$PWD" > "$RLINFRA_CAPTURE"\nprintf "%s\\n" "$*" >> "$RLINFRA_CAPTURE"\n',
        encoding="utf-8",
    )
    fake_claude.chmod(0o755)
    env = dict(os.environ)
    env["RLINFRA_CLAUDE_BIN"] = str(fake_claude)
    env["RLINFRA_CAPTURE"] = str(capture)
    launched = run_command([str(launcher), "--resume", "test-session"], cwd=ROOT, env=env)
    assert launched.returncode == 0, launched.stdout + launched.stderr
    captured = capture.read_text(encoding="utf-8").splitlines()
    assert captured == [str(target.resolve()), "--resume test-session"]
    assert git(target, "status", "--short").stdout == ""
    assert git(target, "ls-files", "--", ".humanize").stdout == ""


def test_target_start_preserves_refined_plan(tmp_path):
    target, workspace = prepare_target_mode(tmp_path)
    refinement = "\n## Human Refinement\n\nPreserve this decision.\n"
    workspace_plan = workspace / "docs" / "plan.md"
    target_plan = target / TARGET_PLAN
    refined = workspace_plan.read_text(encoding="utf-8") + refinement
    workspace_plan.write_text(refined, encoding="utf-8")
    target_plan.write_text(refined, encoding="utf-8")
    assert git(target, "add", TARGET_PLAN).returncode == 0
    assert git(target, "commit", "-m", "Refine RLCR plan").returncode == 0

    result = run_target_start(target, workspace)

    assert result.returncode == 0, result.stdout + result.stderr
    assert workspace_plan.read_text(encoding="utf-8") == refined
    report = json.loads(
        (workspace / ".humanize" / "rlinfra_target_preflight.json").read_text(encoding="utf-8")
    )
    assert report["checks"]["target_plan"]["plan_lock_sha256"] == report["plan_sha256"]


def test_start_rejects_stale_artifact_directory(tmp_path):
    workspace = tmp_path / "workspace"
    stale = workspace / "launch_humanize.sh"
    stale.mkdir(parents=True)

    result = run_command(
        [
            sys.executable,
            str(START),
            "--contract",
            str(CONTRACT),
            "--workspace",
            str(workspace),
            "--target-repo",
            str(tmp_path / "target"),
            "--target-plan",
            TARGET_PLAN,
            "--force",
        ]
    )

    assert result.returncode == 1
    assert "generated artifact path is a directory" in result.stderr


def test_target_preflight_failure_keeps_report_but_removes_stale_operator_artifacts(tmp_path):
    target, workspace = prepare_target_mode(tmp_path)
    first = run_target_start(target, workspace)
    assert first.returncode == 0, first.stdout + first.stderr

    target_plan = target / TARGET_PLAN
    target_plan.write_text("# Committed but stale plan\n", encoding="utf-8")
    assert git(target, "add", TARGET_PLAN).returncode == 0
    assert git(target, "commit", "-m", "Make plan stale").returncode == 0

    result = run_target_start(target, workspace)

    assert result.returncode == 3
    assert "stage target_hygiene_preflight failed" in result.stderr
    assert not (workspace / "humanize_operator.md").exists()
    assert not (workspace / ".humanize" / "rlinfra_operator.json").exists()
    assert not (workspace / "launch_humanize.sh").exists()
    report = json.loads((workspace / ".humanize" / "rlinfra_target_preflight.json").read_text(encoding="utf-8"))
    assert report["status"] == "failed"
    assert "hash does not match" in report["errors"][0]


def test_target_repo_requires_target_plan(tmp_path):
    workspace = tmp_path / "workspace"
    target = tmp_path / "target"
    target.mkdir()

    result = run_start(workspace, "--target-repo", str(target))

    assert result.returncode == 1
    assert "--target-plan is required" in result.stderr
    assert not workspace.exists()
