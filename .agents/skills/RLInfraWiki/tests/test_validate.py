import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def test_validate_script_passes():
    result = subprocess.run([sys.executable, str(ROOT / ".agents/skills/RLInfraWiki/scripts/validate.py")], cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr
