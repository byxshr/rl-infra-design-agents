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


def test_append_goal_update_validates_status_enum(tmp_path):
    ws = render_workspace(tmp_path)
    result = subprocess.run([
        sys.executable, str(ROOT / ".agents/skills/RLInfraWiki/scripts/append_goal_update.py"),
        "--workspace", str(ws),
        "--status", "complete",
        "--reason", "typo",
    ], cwd=ROOT, text=True, capture_output=True)
    assert result.returncode != 0
    assert "invalid choice" in result.stderr


def test_append_goal_update_appends_schema_valid_row(tmp_path):
    ws = render_workspace(tmp_path)
    result = subprocess.run([
        sys.executable, str(ROOT / ".agents/skills/RLInfraWiki/scripts/append_goal_update.py"),
        "--workspace", str(ws),
        "--status", "blocked",
        "--reason", "waiting for evidence",
        "--approved-by", "human",
    ], cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr
    rows = [json.loads(line) for line in (ws / "goal_versions.jsonl").read_text().splitlines()]
    assert rows[-1]["status"] == "blocked"
    assert rows[-1]["reason"] == "waiting for evidence"
    assert rows[-1]["approved_by"] == "human"
