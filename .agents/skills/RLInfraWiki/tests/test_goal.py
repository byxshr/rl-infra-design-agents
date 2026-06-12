import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def test_render_and_validate_goal(tmp_path):
    goal = tmp_path / "goal.md"
    render = subprocess.run([
        sys.executable, str(ROOT / ".agents/skills/RLInfraWiki/scripts/render_goal.py"),
        "--contract", str(ROOT / "examples/task_contracts/slime-weight-sync.yaml"),
        "--output", str(goal),
    ], cwd=ROOT, text=True, capture_output=True)
    assert render.returncode == 0, render.stdout + render.stderr
    validate = subprocess.run([
        sys.executable, str(ROOT / ".agents/skills/RLInfraWiki/scripts/validate_goal.py"),
        "--goal", str(goal),
    ], cwd=ROOT, text=True, capture_output=True)
    assert validate.returncode == 0, validate.stdout + validate.stderr
