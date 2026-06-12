#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from _rlinfra import append_jsonl, load_jsonl, normalize_review_issue, now_iso, schema_validation_errors

SIGNIFICANT_FIELDS = ["severity", "status", "summary", "file", "suggested_fix", "evidence"]
DEFAULT_ISSUE_FIELDS = {
    "category": "review",
    "source": "codex-review",
    "owner": "claude-builder",
    "resolved_at": None,
    "resolution": None,
}


def load_state(path: Path) -> dict:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=False) + "\n" for row in rows), encoding="utf-8")


def issue_differs(existing: dict, incoming: dict) -> bool:
    return any(existing.get(field) != incoming.get(field) for field in SIGNIFICANT_FIELDS)


def merge_issue(existing: dict, incoming: dict) -> dict:
    merged = dict(existing)
    merged.update(incoming)
    return merged


def issue_with_defaults(issue: dict) -> dict:
    enriched = dict(DEFAULT_ISSUE_FIELDS)
    enriched.update(issue)
    enriched.setdefault("created_at", now_iso())
    return enriched


def main() -> int:
    parser = argparse.ArgumentParser(description="Append parsed review issues into workspace ledger")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--round-dir", required=True)
    parser.add_argument("--allow-overwrite", action="store_true", help="Merge incoming same-id review issue fields when significant fields differ")
    args = parser.parse_args()
    ws = Path(args.workspace)
    rdir = Path(args.round_dir)
    if not rdir.is_absolute():
        rdir = ws / rdir
    issues = []
    errors = []
    for idx, issue in enumerate(load_jsonl(rdir / "parsed_issues.jsonl"), 1):
        normalized = normalize_review_issue(issue)
        validated_issue = issue_with_defaults(normalized)
        errors.extend(schema_validation_errors(validated_issue, "review_issue.schema.json", f"{rdir / 'parsed_issues.jsonl'}:{idx}"))
        issues.append(normalized)
    if errors:
        print("ERROR: parsed review issues failed schema validation")
        for err in errors:
            print(f"  - {err}")
        return 1
    ledger_path = ws / "review_issues.jsonl"
    existing = load_jsonl(ledger_path)
    existing_by_id = {row.get("id"): idx for idx, row in enumerate(existing) if row.get("id")}
    updated = list(existing)
    new_issues = []
    conflicts = []
    replaced = 0
    skipped = 0
    pending_by_id = {}
    for issue in issues:
        issue_id = issue.get("id")
        if issue_id in existing_by_id:
            idx = existing_by_id[issue_id]
            if issue_differs(updated[idx], issue):
                conflicts.append(issue_id)
                if args.allow_overwrite:
                    updated[idx] = merge_issue(updated[idx], issue)
                    replaced += 1
                continue
            skipped += 1
            continue
        if issue_id in pending_by_id:
            prior = pending_by_id[issue_id]
            if issue_differs(prior, issue):
                conflicts.append(issue_id)
                if args.allow_overwrite:
                    pending_by_id[issue_id] = merge_issue(prior, issue)
                continue
            skipped += 1
            continue
        issue = issue_with_defaults(issue)
        pending_by_id[issue_id] = issue
        new_issues.append(issue)
    if conflicts and not args.allow_overwrite:
        print("ERROR: duplicate review issue id(s) changed; rerun with --allow-overwrite to replace them")
        for issue_id in conflicts:
            print(f"  - {issue_id}")
        return 1
    if args.allow_overwrite:
        new_issues = list(pending_by_id.values())
    if replaced:
        write_jsonl(ledger_path, updated + new_issues)
    else:
        append_jsonl(ledger_path, new_issues)
    state_path = ws / ".humanize" / "loop_state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        state = load_state(state_path)
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"ERROR: cannot update loop state: {exc}")
        return 1
    state.update({"status": "review-ingested", "round": rdir.name, "issue_count": len(issues), "updated_at": now_iso()})
    state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    print(f"appended {len(new_issues)} issue(s)")
    if replaced:
        print(f"replaced {replaced} existing issue(s)")
    if skipped:
        print(f"skipped {skipped} duplicate issue(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
