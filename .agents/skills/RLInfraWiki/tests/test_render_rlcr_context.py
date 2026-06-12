import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def render_workspace(tmp_path):
    ws = tmp_path / "task"
    render = subprocess.run([
        sys.executable, str(ROOT / ".agents/skills/RLInfraWiki/scripts/render_task_bundle.py"),
        "--contract", str(ROOT / "examples/task_contracts/slime-weight-sync.yaml"),
        "--output", str(ws),
    ], cwd=ROOT, text=True, capture_output=True)
    assert render.returncode == 0, render.stdout + render.stderr
    return ws


def lock_workspace(ws):
    lock = subprocess.run([
        sys.executable, str(ROOT / ".agents/skills/RLInfraWiki/scripts/lock_plan.py"),
        "--workspace", str(ws),
    ], cwd=ROOT, text=True, capture_output=True)
    assert lock.returncode == 0, lock.stdout + lock.stderr


def render_packet(ws, round_number):
    return subprocess.run([
        sys.executable, str(ROOT / ".agents/skills/RLInfraWiki/scripts/render_rlcr_context.py"),
        "--workspace", str(ws),
        "--round", str(round_number),
    ], cwd=ROOT, text=True, capture_output=True)


def test_render_rlcr_context_requires_plan_lock(tmp_path):
    ws = render_workspace(tmp_path)
    packet = subprocess.run([
        sys.executable, str(ROOT / ".agents/skills/RLInfraWiki/scripts/render_rlcr_context.py"),
        "--workspace", str(ws),
        "--round", "1",
    ], cwd=ROOT, text=True, capture_output=True)
    assert packet.returncode == 1
    assert "missing" in packet.stderr
    assert "plan.lock.md" in packet.stderr

    lock_workspace(ws)
    issue = {"id": "review-test-p1-waived", "round_id": "round-001", "severity": "P1", "status": "waived", "summary": "still blocks"}
    waiver = {"id": "waiver-test", "issue_id": "review-test-p1-waived", "status": "approved", "approved_by": "human", "reason": "not allowed for P1"}
    (ws / "review_issues.jsonl").write_text(json.dumps(issue) + "\n")
    (ws / "review_waivers.jsonl").write_text(json.dumps(waiver) + "\n")
    packet = render_packet(ws, 1)
    assert packet.returncode == 0, packet.stdout + packet.stderr
    content = (ws / "review_rounds" / "round-001" / "review_packet.md").read_text()
    assert "review-test-p1-waived" in content
    assert "## Waivers" in content
    assert "waiver-test: issue=review-test-p1-waived" in content


def test_render_rlcr_context_skips_prior_round_files(tmp_path):
    ws = render_workspace(tmp_path)
    lock_workspace(ws)
    old_round = ws / "review_rounds" / "round-001"
    old_round.mkdir(parents=True)
    (old_round / "review_packet.md").write_text("old packet")
    (old_round / "parsed_issues.jsonl").write_text("")

    packet = render_packet(ws, 2)
    assert packet.returncode == 0, packet.stdout + packet.stderr
    content = (ws / "review_rounds" / "round-002" / "review_packet.md").read_text()
    assert "review_rounds/round-001/review_packet.md" not in content
    assert "review_rounds/round-001/parsed_issues.jsonl" not in content


def test_render_rlcr_context_rejects_malformed_waiver(tmp_path):
    ws = render_workspace(tmp_path)
    lock_workspace(ws)
    issue = {"id": "review-test-p2", "round_id": "round-001", "severity": "P2", "status": "waived", "summary": "needs valid waiver"}
    waiver = {"id": "waiver-test", "issue_id": "review-test-p2", "status": "approved", "approved_by": "human"}
    (ws / "review_issues.jsonl").write_text(json.dumps(issue) + "\n")
    (ws / "review_waivers.jsonl").write_text(json.dumps(waiver) + "\n")

    packet = render_packet(ws, 1)
    assert packet.returncode == 1
    assert "review waiver schema validation failed" in packet.stderr
    assert "review_waivers.jsonl:1" in packet.stderr
