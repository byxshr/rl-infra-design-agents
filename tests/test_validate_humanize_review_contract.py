from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_humanize_review_contract.py"
LOCAL_HUMANIZE_ROOT = ROOT.parent / "humanize"


def run_validator(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )


def write_review(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "review.md"
    path.write_text(text, encoding="utf-8")
    return path


def test_main_policy_and_fixture_runtime_are_compatible(compatible_humanize_root):
    result = run_validator("--humanize-root", str(compatible_humanize_root), "--print-json")

    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report["contract_id"] == "humanize-gate-invariants-v1"
    assert report["runtime"]["contract_fingerprint"].startswith("sha256:")
    assert report["runtime"]["validation_kind"] == "static_contract_probe"


def test_main_policy_only_reports_runtime_was_not_checked():
    result = run_validator()

    assert result.returncode == 0, result.stdout + result.stderr
    assert "main policy only" in result.stdout
    assert "--humanize-root" in result.stdout


@pytest.mark.skipif(not LOCAL_HUMANIZE_ROOT.is_dir(), reason="standalone Humanize checkout is not present")
def test_local_humanize_runtime_matches_shared_contract():
    result = run_validator("--humanize-root", str(LOCAL_HUMANIZE_ROOT))

    assert result.returncode == 0, result.stdout + result.stderr


def test_contract_fingerprint_disambiguates_same_version_runtime(tmp_path, compatible_humanize_root):
    modified = tmp_path / "modified-humanize"
    shutil.copytree(compatible_humanize_root, modified)
    gate = modified / "prompt-template" / "codex" / "gate-invariants-section.md"
    gate.write_text(gate.read_text(encoding="utf-8") + "\nAdditional compatible wording.\n", encoding="utf-8")

    original_result = run_validator("--humanize-root", str(compatible_humanize_root), "--print-json")
    modified_result = run_validator("--humanize-root", str(modified), "--print-json")

    assert original_result.returncode == 0, original_result.stdout + original_result.stderr
    assert modified_result.returncode == 0, modified_result.stdout + modified_result.stderr
    original = json.loads(original_result.stdout)["runtime"]
    changed = json.loads(modified_result.stdout)["runtime"]
    assert original["plugin_version"] == changed["plugin_version"] == "test-fixture"
    assert original["contract_fingerprint"] != changed["contract_fingerprint"]


def test_pass_and_conflict_reviews_validate(tmp_path):
    passed = write_review(tmp_path, "No findings.\nHumanize Gate Verdict: PASS\n")
    result = run_validator("--review-result", str(passed), "--require-verdict")
    assert result.returncode == 0, result.stdout + result.stderr

    conflict = write_review(
        tmp_path,
        "## P1: Plan conflicts with local-state gate\n"
        "Use a gate-compatible plan outside the runtime directory.\n"
        "Humanize Gate Verdict: TOOL-CONTRACT-CONFLICT\n",
    )
    result = run_validator("--review-result", str(conflict), "--require-verdict")
    assert result.returncode == 0, result.stdout + result.stderr

    conflict_stop = write_review(
        tmp_path,
        "## P1: Plan conflicts with local-state gate\n"
        "Use a gate-compatible plan outside the runtime directory.\n"
        "Humanize Gate Verdict: TOOL-CONTRACT-CONFLICT\n"
        "STOP\n",
    )
    result = run_validator("--review-result", str(conflict_stop), "--require-verdict")
    assert result.returncode == 0, result.stdout + result.stderr


def test_missing_duplicate_and_unsafe_reviews_fail(tmp_path):
    missing = write_review(tmp_path, "COMPLETE\n")
    result = run_validator("--review-result", str(missing), "--require-verdict")
    assert result.returncode == 1
    assert "found 0" in result.stderr

    duplicate = write_review(
        tmp_path,
        "Humanize Gate Verdict: PASS\nHumanize Gate Verdict: PASS\n",
    )
    result = run_validator("--review-result", str(duplicate), "--require-verdict")
    assert result.returncode == 1
    assert "found 2" in result.stderr

    unsafe = write_review(
        tmp_path,
        "Run git add -f .humanize before retrying.\nHumanize Gate Verdict: PASS\n",
    )
    result = run_validator("--review-result", str(unsafe), "--require-verdict")
    assert result.returncode == 1
    assert "gate-conflicting" in result.stderr

    unsafe_git_c = write_review(
        tmp_path,
        "Run git -C /tmp/target add -f .humanize before retrying.\nHumanize Gate Verdict: PASS\n",
    )
    result = run_validator("--review-result", str(unsafe_git_c), "--require-verdict")
    assert result.returncode == 1
    assert "gate-conflicting" in result.stderr


def test_legacy_review_warns_without_verdict_but_unsafe_still_fails(tmp_path):
    legacy = write_review(tmp_path, "COMPLETE\n")
    result = run_validator("--review-result", str(legacy))
    assert result.returncode == 0, result.stdout + result.stderr
    assert "legacy review has no" in result.stdout

    unsafe = write_review(tmp_path, "Commit .humanize/rlcr state, then COMPLETE.\n")
    result = run_validator("--review-result", str(unsafe))
    assert result.returncode == 1
    assert "gate-conflicting" in result.stderr
