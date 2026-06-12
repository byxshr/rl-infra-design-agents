import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def test_query_finds_sglang_rollout():
    result = subprocess.run([sys.executable, str(ROOT / ".agents/skills/RLInfraWiki/scripts/query.py"), "SGLang rollout", "--limit", "3"], cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert "sglang" in result.stdout.lower()
