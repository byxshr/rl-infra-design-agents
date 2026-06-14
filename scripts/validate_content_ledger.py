#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LEDGER = PROJECT_ROOT / "docs" / "rlinfrawiki-content-status.md"
DEFAULT_WIKI_ROOT = PROJECT_ROOT / ".agents" / "skills" / "RLInfraWiki"

VALID_STATUSES = {"stub", "indexed", "code-evidenced", "review-ready"}
VALID_PRIORITIES = {"P0", "P1", "P2", "P3"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

EXPECTED_STATUS_HEADERS = ["status", "meaning", "promotion requirement"]
EXPECTED_THEME_HEADERS = ["theme", "priority", "current_status", "target_status", "pages", "next_action"]
EXPECTED_INVENTORY_HEADERS = [
    "page_id",
    "path",
    "type",
    "theme",
    "current_status",
    "target_status",
    "priority",
    "evidence_gaps",
    "next_action",
    "last_reviewed",
]

REVIEW_STRUCTURE_GROUPS = {
    "evidence/design": ["evidence", "design", "basis", "procedure", "detection", "checklist"],
    "failure/risk": ["failure", "risk", "mitigation", "rollback", "stop condition"],
    "validation": ["validation", "validate", "test", "checklist"],
    "open-gap/non-claim": [
        "open gap",
        "gap",
        "non-claim",
        "non claim",
        "limitation",
        "does not verify",
        "does not provide",
        "source-reported",
        "requires separate evidence",
        "outside the current project scope",
    ],
}


@dataclass(frozen=True)
class Table:
    headers: list[str]
    rows: list[tuple[int, dict[str, str]]]


def strip_code(text: str) -> str:
    value = text.strip()
    if len(value) >= 2 and value.startswith("`") and value.endswith("`"):
        return value[1:-1]
    return value


def split_table_row(line: str) -> list[str]:
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def is_separator_row(cells: list[str]) -> bool:
    return all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)


def parse_table(lines: list[str], heading: str, expected_headers: list[str], errors: list[str]) -> Table:
    heading_line = f"## {heading}"
    try:
        start = next(idx for idx, line in enumerate(lines) if line.strip() == heading_line)
    except StopIteration:
        errors.append(f"{heading}: missing section")
        return Table(expected_headers, [])

    idx = start + 1
    while idx < len(lines) and not lines[idx].strip():
        idx += 1
    if idx >= len(lines) or not lines[idx].lstrip().startswith("|"):
        errors.append(f"{heading}: missing markdown table")
        return Table(expected_headers, [])

    headers = split_table_row(lines[idx])
    if headers != expected_headers:
        errors.append(f"{heading}: expected headers {expected_headers}, got {headers}")
    idx += 1
    if idx >= len(lines) or not is_separator_row(split_table_row(lines[idx])):
        errors.append(f"{heading}: missing markdown table separator row")
        return Table(headers, [])

    rows: list[tuple[int, dict[str, str]]] = []
    idx += 1
    while idx < len(lines) and lines[idx].lstrip().startswith("|"):
        cells = split_table_row(lines[idx])
        line_no = idx + 1
        if len(cells) != len(headers):
            errors.append(f"{heading}:{line_no}: expected {len(headers)} columns, got {len(cells)}")
        else:
            rows.append((line_no, dict(zip(headers, cells))))
        idx += 1
    if not rows:
        errors.append(f"{heading}: table has no rows")
    return Table(headers, rows)


def import_rlinfra(wiki_root: Path):
    wiki_root = wiki_root.resolve()
    os.environ["RLINFRA_WIKI_ROOT"] = str(wiki_root)
    scripts_dir = wiki_root / "scripts"
    sys.path.insert(0, str(scripts_dir))
    for module_name in ["_rlinfra", "_wiki_root"]:
        sys.modules.pop(module_name, None)
    try:
        import _rlinfra  # type: ignore
    except Exception as exc:  # pragma: no cover - exact import failure text is environment-specific.
        raise SystemExit(f"ERROR: failed to import RLInfraWiki helpers from {scripts_dir}: {exc}") from exc
    return _rlinfra


def validate_status(value: str, label: str, errors: list[str]) -> None:
    if value not in VALID_STATUSES:
        errors.append(f"{label}: invalid status {value!r}")


def validate_priority(value: str, label: str, errors: list[str]) -> None:
    if value not in VALID_PRIORITIES:
        errors.append(f"{label}: invalid priority {value!r}")


def validate_review_ready_body(page_id: str, body: str, label: str, errors: list[str]) -> None:
    headings = " ".join(re.findall(r"^##+\s+(.+)$", body, flags=re.MULTILINE)).lower()
    body_lower = body.lower()
    missing = []
    for group_name, terms in REVIEW_STRUCTURE_GROUPS.items():
        if not any(term in headings or term in body_lower for term in terms):
            missing.append(group_name)
    if missing:
        errors.append(f"{label}: review-ready page {page_id!r} missing review structure: {', '.join(missing)}")


def resolve_ledger_path(root: Path, rel_path: str, label: str, errors: list[str]) -> Path | None:
    rel = Path(rel_path)
    if rel.is_absolute() or ".." in rel.parts:
        errors.append(f"{label}: path must be repository-relative within RLInfraWiki: {rel_path}")
        return None
    return root / rel


def validate_theme_rows(table: Table, errors: list[str]) -> set[str]:
    themes = set()
    for line_no, row in table.rows:
        label = f"Theme Roadmap:{line_no}"
        theme = row["theme"]
        themes.add(theme)
        validate_priority(row["priority"], label, errors)
        validate_status(row["current_status"], f"{label}: current_status", errors)
        validate_status(row["target_status"], f"{label}: target_status", errors)
        if not row["pages"].isdigit():
            errors.append(f"{label}: pages must be a non-negative integer")
    return themes


def validate_status_taxonomy(table: Table, errors: list[str]) -> None:
    statuses = {strip_code(row["status"]) for _, row in table.rows}
    if statuses != VALID_STATUSES:
        errors.append(f"Status Taxonomy: expected statuses {sorted(VALID_STATUSES)}, got {sorted(statuses)}")


def validate_inventory_rows(table: Table, themes: set[str], wiki_root: Path, rlinfra: Any, errors: list[str]) -> None:
    sources = rlinfra.load_source_manifests()
    for line_no, row in table.rows:
        label = f"Page Inventory:{line_no}"
        page_id = row["page_id"]
        row_type = row["type"]
        current_status = row["current_status"]
        target_status = row["target_status"]

        validate_status(current_status, f"{label}: current_status", errors)
        validate_status(target_status, f"{label}: target_status", errors)
        validate_priority(row["priority"], label, errors)
        if not DATE_RE.fullmatch(row["last_reviewed"]):
            errors.append(f"{label}: last_reviewed must be YYYY-MM-DD")
        if row["theme"] not in themes:
            errors.append(f"{label}: unknown theme {row['theme']!r}")

        path = resolve_ledger_path(wiki_root, row["path"], label, errors)
        if path is None:
            continue
        if not path.exists():
            errors.append(f"{label}: path does not exist: {row['path']}")
            continue

        if row_type == "category-readme":
            if path.name != "README.md":
                errors.append(f"{label}: category-readme path must point at README.md")
            continue

        fm, body = rlinfra.split_frontmatter(path)
        if not fm:
            errors.append(f"{label}: missing or invalid YAML frontmatter in {row['path']}")
            continue
        frontmatter_id = str(fm.get("id", ""))
        if page_id != frontmatter_id:
            errors.append(f"{label}: page_id {page_id!r} does not match frontmatter id {frontmatter_id!r}")
        page_type = str(fm.get("page_type") or fm.get("type") or "")
        if row_type != page_type:
            errors.append(f"{label}: type {row_type!r} does not match frontmatter type/page_type {page_type!r}")

        page_sources = fm.get("sources")
        if not isinstance(page_sources, list) or not page_sources:
            errors.append(f"{label}: wiki page must have a non-empty sources list")
        else:
            for source_id in page_sources:
                if source_id not in sources:
                    errors.append(f"{label}: unknown source id {source_id!r}")

        if current_status == "review-ready":
            validate_review_ready_body(page_id, body, label, errors)


def validate_content_ledger(ledger_path: Path, wiki_root: Path) -> list[str]:
    errors: list[str] = []
    if not ledger_path.exists():
        return [f"ledger not found: {ledger_path}"]
    if not wiki_root.exists():
        return [f"RLInfraWiki root not found: {wiki_root}"]

    text = ledger_path.read_text(encoding="utf-8")
    lines = text.splitlines()
    status_table = parse_table(lines, "Status Taxonomy", EXPECTED_STATUS_HEADERS, errors)
    theme_table = parse_table(lines, "Theme Roadmap", EXPECTED_THEME_HEADERS, errors)
    inventory_table = parse_table(lines, "Page Inventory", EXPECTED_INVENTORY_HEADERS, errors)

    validate_status_taxonomy(status_table, errors)
    themes = validate_theme_rows(theme_table, errors)
    rlinfra = import_rlinfra(wiki_root)
    validate_inventory_rows(inventory_table, themes, wiki_root.resolve(), rlinfra, errors)
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate docs/rlinfrawiki-content-status.md against pinned RLInfraWiki")
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER, help="Path to rlinfrawiki-content-status.md")
    parser.add_argument("--wiki-root", type=Path, default=DEFAULT_WIKI_ROOT, help="Path to pinned RLInfraWiki root")
    args = parser.parse_args()

    errors = validate_content_ledger(args.ledger, args.wiki_root)
    if errors:
        print(f"ERROR: {len(errors)} content ledger issue(s)")
        for error in errors:
            print(f"  - {error}")
        return 1
    print("Content ledger validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
