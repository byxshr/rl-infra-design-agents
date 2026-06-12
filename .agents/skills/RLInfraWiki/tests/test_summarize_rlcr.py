import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def render_workspace(tmp_path):
    ws = tmp_path / "task"
    result = subprocess.run([
        sys.executable, str(ROOT / ".agents/skills/RLInfraWiki/scripts/render_task_bundle.py"),
        "--contract", str(ROOT / "examples/task_contracts/slime-weight-sync.yaml"),
        "--output", str(ws),
    ], cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr
    return ws


def run_summary(ws):
    return subprocess.run([
        sys.executable, str(ROOT / ".agents/skills/RLInfraWiki/scripts/summarize_rlcr.py"),
        "--workspace", str(ws),
    ], cwd=ROOT, text=True, capture_output=True)


def test_summarize_rlcr_reports_unwaived_p2_as_blocked(tmp_path):
    ws = render_workspace(tmp_path)
    issue = {
        "id": "review-test-p2",
        "round_id": "round-001",
        "severity": "P2",
        "status": "open",
        "summary": "needs waiver",
    }
    (ws / "review_issues.jsonl").write_text(json.dumps(issue) + "\n")

    result = run_summary(ws)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "P2: 1" in result.stdout
    assert "promotion_readiness: blocked" in result.stdout


def test_summarize_rlcr_reports_approved_p2_waiver_as_ready(tmp_path):
    ws = render_workspace(tmp_path)
    issue = {
        "id": "review-test-p2",
        "round_id": "round-001",
        "severity": "P2",
        "status": "waived",
        "summary": "accepted residual risk",
    }
    waiver = {
        "id": "waiver-test-p2",
        "issue_id": "review-test-p2",
        "status": "approved",
        "approved_by": "human",
        "reason": "accepted residual risk",
    }
    (ws / "review_issues.jsonl").write_text(json.dumps(issue) + "\n")
    (ws / "review_waivers.jsonl").write_text(json.dumps(waiver) + "\n")

    result = run_summary(ws)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "promotion_readiness: ready (run gate to confirm)" in result.stdout


def test_summarize_rlcr_ignores_schema_invalid_approved_waiver(tmp_path):
    ws = render_workspace(tmp_path)
    issue = {
        "id": "review-test-p2",
        "round_id": "round-001",
        "severity": "P2",
        "status": "waived",
        "summary": "malformed waiver should not count",
    }
    waiver = {
        "issue_id": "review-test-p2",
        "status": "approved",
    }
    (ws / "review_issues.jsonl").write_text(json.dumps(issue) + "\n")
    (ws / "review_waivers.jsonl").write_text(json.dumps(waiver) + "\n")

    result = run_summary(ws)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "P2: 1" in result.stdout
    assert "promotion_readiness: blocked" in result.stdout
