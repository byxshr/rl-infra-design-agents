import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
from parse_codex_review import parse


def test_parser_ignores_narrative_priority_text():
    text = """Review summary

P1: this sentence describes a policy, not a finding.

### P2: real issue

- File/path: docs/plan.md
- Suggested fix: Add evidence.
"""
    issues = parse(text, "round-001")
    assert [issue["severity"] for issue in issues] == ["P2"]
    assert issues[0]["summary"] == "real issue"
    assert issues[0]["file"] == "docs/plan.md"


def test_parser_issue_ids_are_stable_when_headings_are_inserted():
    original = """### P1: missing validation

### P2: minor doc nit
"""
    edited = """### P0: critical regression

### P1: missing validation

### P2: minor doc nit
"""
    original_issues = parse(original, "round-001")
    edited_issues = parse(edited, "round-001")
    original_by_summary = {issue["summary"]: issue["id"] for issue in original_issues}
    edited_by_summary = {issue["summary"]: issue["id"] for issue in edited_issues}
    assert edited_by_summary["missing validation"] == original_by_summary["missing validation"]
    assert edited_by_summary["minor doc nit"] == original_by_summary["minor doc nit"]
    assert edited_by_summary["critical regression"] not in set(original_by_summary.values())


def test_parser_rejects_duplicate_severity_title_in_same_round():
    text = """### P1: missing validation

- File/path: foo.py

### P1: missing validation

- File/path: bar.py
"""
    with pytest.raises(ValueError, match="duplicate review finding heading"):
        parse(text, "round-001")
