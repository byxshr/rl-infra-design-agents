from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_content_ledger.py"
LEDGER = ROOT / "docs" / "rlinfrawiki-content-status.md"
WIKI_ROOT = ROOT / ".agents" / "skills" / "RLInfraWiki"


def run_validator(ledger: Path, wiki_root: Path = WIKI_ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--ledger", str(ledger), "--wiki-root", str(wiki_root)],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )


def write_ledger(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "rlinfrawiki-content-status.md"
    path.write_text(text, encoding="utf-8")
    return path


def test_current_content_ledger_passes():
    result = run_validator(LEDGER)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Content ledger validation passed" in result.stdout


def test_invalid_status_is_rejected(tmp_path):
    text = LEDGER.read_text(encoding="utf-8").replace(
        "| async agentic RL | P1 | code-evidenced | review-ready |",
        "| async agentic RL | P1 | almost-done | review-ready |",
        1,
    )
    result = run_validator(write_ledger(tmp_path, text))
    assert result.returncode == 1
    assert "invalid status 'almost-done'" in result.stdout


def test_missing_inventory_page_path_is_rejected(tmp_path):
    text = LEDGER.read_text(encoding="utf-8").replace(
        "wiki/agentic/tool-calling.md",
        "wiki/agentic/missing-tool-calling.md",
        1,
    )
    result = run_validator(write_ledger(tmp_path, text))
    assert result.returncode == 1
    assert "path does not exist: wiki/agentic/missing-tool-calling.md" in result.stdout


def test_unknown_page_source_id_is_rejected(tmp_path):
    wiki_copy = tmp_path / "RLInfraWiki"
    shutil.copytree(WIKI_ROOT, wiki_copy, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", ".git"))
    page = wiki_copy / "wiki" / "agentic" / "tool-calling.md"
    page.write_text(
        page.read_text(encoding="utf-8").replace("- repo-inclusionai-areal-readme", "- missing-source-id", 1),
        encoding="utf-8",
    )

    result = run_validator(LEDGER, wiki_copy)
    assert result.returncode == 1
    assert "unknown source id 'missing-source-id'" in result.stdout


def test_review_ready_page_requires_review_structure(tmp_path):
    wiki_copy = tmp_path / "RLInfraWiki"
    shutil.copytree(WIKI_ROOT, wiki_copy, ignore=shutil.ignore_patterns("__pycache__", ".pytest_cache", ".git"))
    page = wiki_copy / "wiki" / "agentic" / "tool-calling.md"
    original = page.read_text(encoding="utf-8")
    frontmatter = original.split("---", 2)[1]
    page.write_text(
        f"---{frontmatter}---\n\n"
        "# Tool Calling\n\n"
        "This deliberately minimal body keeps valid frontmatter and sources but omits review-ready sections.\n",
        encoding="utf-8",
    )

    text = LEDGER.read_text(encoding="utf-8").replace(
        "| agentic-tool-calling | wiki/agentic/tool-calling.md | agentic | async agentic RL | code-evidenced | review-ready |",
        "| agentic-tool-calling | wiki/agentic/tool-calling.md | agentic | async agentic RL | review-ready | review-ready |",
        1,
    )
    result = run_validator(write_ledger(tmp_path, text), wiki_copy)
    assert result.returncode == 1
    assert "review-ready page 'agentic-tool-calling' missing review structure" in result.stdout
