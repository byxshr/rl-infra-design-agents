from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
PREPARE = ROOT / "scripts" / "prepare_humanize_task.py"
IMPORT = ROOT / "scripts" / "import_humanize_round.py"
REVIEW_GATE = ROOT / ".agents" / "skills" / "RLInfraWiki" / "scripts" / "validate_review_gate.py"
CONTRACT = ROOT / "examples" / "task_contracts" / "training-rollout-mismatch-debug.yaml"


def run_command(args: list[str], *, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd, text=True, capture_output=True)


@pytest.fixture(scope="session")
def prepared_workspace_template(tmp_path_factory: pytest.TempPathFactory) -> Path:
    workspace = tmp_path_factory.mktemp("humanize-import-template") / "workspace"
    result = run_command(
        [
            sys.executable,
            str(PREPARE),
            "--contract",
            str(CONTRACT),
            "--workspace",
            str(workspace),
            "--force",
            "--overwrite-human-docs",
        ]
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return workspace


def copy_workspace(template: Path, tmp_path: Path, *, rewrite_bridge: bool = True) -> Path:
    workspace = tmp_path / "workspace"
    shutil.copytree(template, workspace)
    if not rewrite_bridge:
        return workspace
    bridge_path = workspace / ".humanize" / "rlinfra_bridge.json"
    bridge = json.loads(bridge_path.read_text(encoding="utf-8"))
    bridge["workspace"] = str(workspace.resolve())
    bridge["plan_lock"] = str((workspace / ".humanize" / "plan.lock.md").resolve())
    bridge["humanize_start"] = str((workspace / "humanize_start.md").resolve())
    bridge["context_paths"] = {
        "markdown": str((workspace / "context" / "context_bundle.md").resolve()),
        "json": str((workspace / "context" / "context_bundle.json").resolve()),
        "sources": str((workspace / "context" / "context_sources.yaml").resolve()),
    }
    bridge_path.write_text(json.dumps(bridge, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return workspace


def write_humanize_round(
    workspace: Path,
    *,
    loop_name: str = "2026-06-15_12-00-00",
    round_number: int = 1,
    review_text: str = "COMPLETE\n",
    summary_text: str = "# Round Summary\n\nImplemented the requested plan.\n",
) -> Path:
    loop_dir = workspace / ".humanize" / "rlcr" / loop_name
    loop_dir.mkdir(parents=True, exist_ok=True)
    (loop_dir / "state.md").write_text("current_round: 1\n", encoding="utf-8")
    (loop_dir / "goal-tracker.md").write_text("# Goal Tracker\n", encoding="utf-8")
    (loop_dir / f"round-{round_number}-prompt.md").write_text("# Prompt\n", encoding="utf-8")
    (loop_dir / f"round-{round_number}-review-prompt.md").write_text("# Review Prompt\n", encoding="utf-8")
    (loop_dir / f"round-{round_number}-summary.md").write_text(summary_text, encoding="utf-8")
    (loop_dir / f"round-{round_number}-review-result.md").write_text(review_text, encoding="utf-8")
    return loop_dir


def run_import(workspace: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return run_command([sys.executable, str(IMPORT), "--workspace", str(workspace), *extra])


def run_gate(workspace: Path) -> subprocess.CompletedProcess[str]:
    return run_command([sys.executable, str(REVIEW_GATE), "--workspace", str(workspace), "--require-review"])


def test_complete_round_import_creates_artifacts_and_gate_passes(tmp_path, prepared_workspace_template):
    workspace = copy_workspace(prepared_workspace_template, tmp_path)
    loop_dir = write_humanize_round(workspace, review_text="All acceptance criteria are met.\n\nCOMPLETE\n")

    result = run_import(workspace, "--humanize-loop-dir", str(loop_dir), "--round", "1")

    assert result.returncode == 0, result.stdout + result.stderr
    round_dir = workspace / "review_rounds" / "round-001"
    assert (round_dir / "claude_response.md").exists()
    assert (round_dir / "codex_review.md").exists()
    assert (round_dir / "parsed_issues.jsonl").read_text(encoding="utf-8") == ""
    metadata = json.loads((round_dir / "humanize_round_metadata.json").read_text(encoding="utf-8"))
    assert metadata["round"] == 1
    assert metadata["no_finding"] is True
    assert metadata["issue_count"] == 0
    assert metadata["bridge"]["schema_version"] == 1
    assert metadata["warnings"] == []
    assert set(metadata["source_files"]) >= {"summary", "review_result", "prompt", "review_prompt", "goal_tracker"}
    assert "No parser-compatible P0-P3 findings" in (round_dir / "codex_review.md").read_text(encoding="utf-8")

    gate = run_gate(workspace)
    assert gate.returncode == 0, gate.stdout + gate.stderr


def test_no_finding_review_accepts_bracket_priority_phrase(tmp_path, prepared_workspace_template):
    workspace = copy_workspace(prepared_workspace_template, tmp_path)
    loop_dir = write_humanize_round(workspace, review_text="There are no [P1] issues left.\n")

    result = run_import(workspace, "--humanize-loop-dir", str(loop_dir), "--round", "1")

    assert result.returncode == 0, result.stdout + result.stderr
    round_dir = workspace / "review_rounds" / "round-001"
    assert (round_dir / "parsed_issues.jsonl").read_text(encoding="utf-8") == ""
    metadata = json.loads((round_dir / "humanize_round_metadata.json").read_text(encoding="utf-8"))
    assert metadata["no_finding"] is True
    assert metadata["issue_count"] == 0


def test_p1_round_import_updates_ledger_and_gate_blocks(tmp_path, prepared_workspace_template):
    workspace = copy_workspace(prepared_workspace_template, tmp_path)
    loop_dir = write_humanize_round(
        workspace,
        review_text=(
            "Code review found one blocker.\n\n"
            "- [P1] Missing validation evidence - docs/validation_matrix.md:10\n"
            "  The round claims validation without artifact paths.\n"
        ),
    )

    result = run_import(workspace, "--humanize-loop-dir", str(loop_dir), "--round", "1")

    assert result.returncode == 0, result.stdout + result.stderr
    issues = [
        json.loads(line)
        for line in (workspace / "review_issues.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(issues) == 1
    assert issues[0]["severity"] == "P1"
    assert issues[0]["status"] == "open"
    assert issues[0]["summary"] == "Missing validation evidence"
    review_text = (workspace / "review_rounds" / "round-001" / "codex_review.md").read_text(encoding="utf-8")
    assert "### P1: Missing validation evidence" in review_text
    assert "> - [P1] Missing validation evidence" in review_text

    gate = run_gate(workspace)
    assert gate.returncode != 0
    assert "unresolved P1 issue blocks promotion" in gate.stdout


def test_title_split_uses_last_separator_before_path_suffix(tmp_path, prepared_workspace_template):
    workspace = copy_workspace(prepared_workspace_template, tmp_path)
    loop_dir = write_humanize_round(workspace, review_text="- [P1] complex - title - docs/plan.md:42\n")

    result = run_import(workspace, "--humanize-loop-dir", str(loop_dir), "--round", "1")

    assert result.returncode == 0, result.stdout + result.stderr
    issues = [
        json.loads(line)
        for line in (workspace / "review_issues.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert len(issues) == 1
    assert issues[0]["summary"] == "complex - title"
    assert issues[0]["file"] == "docs/plan.md:42"


def test_dry_run_prints_plan_and_does_not_write_round(tmp_path, prepared_workspace_template):
    workspace = copy_workspace(prepared_workspace_template, tmp_path)
    loop_dir = write_humanize_round(workspace, review_text="- [P1] Dry run issue - docs/plan.md:1\n")

    result = run_import(workspace, "--humanize-loop-dir", str(loop_dir), "--round", "1", "--dry-run")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Dry run: no files written." in result.stdout
    assert "issues: 1" in result.stdout
    assert not (workspace / "review_rounds" / "round-001" / "codex_review.md").exists()
    assert (workspace / "review_issues.jsonl").read_text(encoding="utf-8") == ""


def test_multiple_loop_dirs_without_clear_latest_fails(tmp_path, prepared_workspace_template):
    workspace = copy_workspace(prepared_workspace_template, tmp_path)
    write_humanize_round(workspace, loop_name="loop-a")
    write_humanize_round(workspace, loop_name="loop-b")
    for state in (workspace / ".humanize" / "rlcr").glob("*/state.md"):
        state.unlink()

    result = run_import(workspace, "--round", "1")

    assert result.returncode != 0
    assert "multiple Humanize loop dirs" in result.stderr
    assert "loop-a" in result.stderr
    assert "loop-b" in result.stderr


def test_existing_round_requires_allow_overwrite(tmp_path, prepared_workspace_template):
    workspace = copy_workspace(prepared_workspace_template, tmp_path)
    loop_dir = write_humanize_round(workspace, review_text="COMPLETE\n")

    first = run_import(workspace, "--humanize-loop-dir", str(loop_dir), "--round", "1")
    assert first.returncode == 0, first.stdout + first.stderr

    second = run_import(workspace, "--humanize-loop-dir", str(loop_dir), "--round", "1")
    assert second.returncode != 0
    assert "already exists" in second.stderr

    (loop_dir / "round-1-review-result.md").write_text("No issues remain.\n", encoding="utf-8")
    third = run_import(workspace, "--humanize-loop-dir", str(loop_dir), "--round", "1", "--allow-overwrite")
    assert third.returncode == 0, third.stdout + third.stderr


def test_unsupported_bridge_schema_fails_unless_explicitly_accepted(tmp_path, prepared_workspace_template):
    workspace = copy_workspace(prepared_workspace_template, tmp_path)
    bridge_path = workspace / ".humanize" / "rlinfra_bridge.json"
    bridge = json.loads(bridge_path.read_text(encoding="utf-8"))
    bridge["schema_version"] = 2
    bridge_path.write_text(json.dumps(bridge, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    loop_dir = write_humanize_round(workspace, review_text="COMPLETE\n")

    result = run_import(workspace, "--humanize-loop-dir", str(loop_dir), "--round", "1")

    assert result.returncode != 0
    assert "unsupported bridge schema_version: 2" in result.stderr

    accepted = run_import(
        workspace,
        "--humanize-loop-dir",
        str(loop_dir),
        "--round",
        "1",
        "--accept-bridge-schema",
        "2",
    )
    assert accepted.returncode == 0, accepted.stdout + accepted.stderr

    bridge["schema_version"] = 8
    bridge_path.write_text(json.dumps(bridge, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_humanize_round(workspace, round_number=2, review_text="COMPLETE\n")
    multi_accepted = run_import(
        workspace,
        "--humanize-loop-dir",
        str(loop_dir),
        "--round",
        "2",
        "--accept-bridge-schema",
        "7",
        "--accept-bridge-schema",
        "8",
    )
    assert multi_accepted.returncode == 0, multi_accepted.stdout + multi_accepted.stderr
    metadata = json.loads(
        (workspace / "review_rounds" / "round-002" / "humanize_round_metadata.json").read_text(encoding="utf-8")
    )
    assert metadata["bridge"]["schema_version"] == 8


def test_stale_bridge_workspace_warns_and_records_metadata(tmp_path, prepared_workspace_template):
    workspace = copy_workspace(prepared_workspace_template, tmp_path, rewrite_bridge=False)
    loop_dir = write_humanize_round(workspace, review_text="COMPLETE\n")

    result = run_import(workspace, "--humanize-loop-dir", str(loop_dir), "--round", "1")

    assert result.returncode == 0, result.stdout + result.stderr
    assert "WARN: bridge workspace path differs from --workspace" in result.stdout
    metadata = json.loads(
        (workspace / "review_rounds" / "round-001" / "humanize_round_metadata.json").read_text(encoding="utf-8")
    )
    assert any("bridge workspace path differs from --workspace" in warning for warning in metadata["warnings"])


def test_review_result_replacement_char_metadata(tmp_path, prepared_workspace_template):
    workspace = copy_workspace(prepared_workspace_template, tmp_path)
    loop_dir = write_humanize_round(workspace, review_text="COMPLETE\n")
    (loop_dir / "round-1-review-result.md").write_bytes(b"COMPLETE\n\xff\xfe\n")

    result = run_import(workspace, "--humanize-loop-dir", str(loop_dir), "--round", "1")

    assert result.returncode == 0, result.stdout + result.stderr
    metadata = json.loads(
        (workspace / "review_rounds" / "round-001" / "humanize_round_metadata.json").read_text(encoding="utf-8")
    )
    assert metadata["source_files"]["review_result"]["had_replacement_chars"] is True


def test_missing_bridge_summary_and_review_fail(tmp_path, prepared_workspace_template):
    workspace = tmp_path / "no-bridge"
    workspace.mkdir()
    result = run_import(workspace, "--round", "1")
    assert result.returncode != 0
    assert "missing bridge metadata" in result.stderr

    workspace = copy_workspace(prepared_workspace_template, tmp_path / "missing-summary")
    loop_dir = workspace / ".humanize" / "rlcr" / "2026-06-15_12-00-00"
    loop_dir.mkdir(parents=True)
    (loop_dir / "state.md").write_text("current_round: 1\n", encoding="utf-8")
    (loop_dir / "round-1-review-result.md").write_text("COMPLETE\n", encoding="utf-8")
    result = run_import(workspace, "--humanize-loop-dir", str(loop_dir), "--round", "1")
    assert result.returncode != 0
    assert "round-1-summary.md" in result.stderr

    workspace = copy_workspace(prepared_workspace_template, tmp_path / "missing-review")
    loop_dir = workspace / ".humanize" / "rlcr" / "2026-06-15_12-00-01"
    loop_dir.mkdir(parents=True)
    (loop_dir / "state.md").write_text("current_round: 1\n", encoding="utf-8")
    (loop_dir / "round-1-summary.md").write_text("# Summary\n", encoding="utf-8")
    result = run_import(workspace, "--humanize-loop-dir", str(loop_dir), "--round", "1")
    assert result.returncode != 0
    assert "round-1-review-result.md" in result.stderr


def test_unparseable_review_result_fails(tmp_path, prepared_workspace_template):
    workspace = copy_workspace(prepared_workspace_template, tmp_path)
    loop_dir = write_humanize_round(workspace, review_text="This review has no severity marker and no completion marker.\n")

    result = run_import(workspace, "--humanize-loop-dir", str(loop_dir), "--round", "1")

    assert result.returncode != 0
    assert "not parseable" in result.stderr
