#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from _rlinfra import (
    issue_needs_review_attention,
    load_jsonl,
    load_review_waivers,
    now_iso,
    sha256_file,
)


def excerpt(path: Path, max_chars=3000) -> str:
    if not path.exists():
        return f"MISSING: {path.name}\n"
    text = path.read_text(encoding="utf-8", errors="replace")
    return text[:max_chars] + ("\n... truncated ...\n" if len(text) > max_chars else "")


def main() -> int:
    parser = argparse.ArgumentParser(description="Render an RLCR review packet")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--round", type=int, required=True)
    parser.add_argument("--diff-base", default="main")
    args = parser.parse_args()
    ws = Path(args.workspace)
    plan_lock = ws / ".humanize" / "plan.lock.md"
    if not plan_lock.exists():
        raise SystemExit(f"missing {plan_lock}; run lock_plan.py before rendering a review packet")
    round_id = f"round-{args.round:03d}"
    rdir = ws / "review_rounds" / round_id
    rdir.mkdir(parents=True, exist_ok=True)
    issues = load_jsonl(ws / "review_issues.jsonl")
    waivers, approved_waivers, waiver_errors = load_review_waivers(ws)
    if waiver_errors:
        details = "\n".join(f"- {err}" for err in waiver_errors)
        raise SystemExit(f"review waiver schema validation failed:\n{details}")
    changed_files = []
    for path in sorted(ws.rglob("*")):
        rel = path.relative_to(ws)
        parts = rel.parts
        if not path.is_file() or parts[0] in {"runs", "profile"}:
            continue
        if parts[0] == "review_rounds" and len(parts) > 1 and parts[1].startswith("round-") and parts[1] != round_id:
            continue
        changed_files.append(rel.as_posix())
    packet = f"""# RLCR Review Packet: {round_id}

## Metadata

- rendered_at: {now_iso()}
- workspace: {ws}
- diff_base: {args.diff_base}
- plan_lock_sha256: {sha256_file(plan_lock)}

## Goal Summary

{excerpt(ws / 'docs' / 'goal.md')}

## Plan Lock

{excerpt(plan_lock)}

## Validation Matrix

{excerpt(ws / 'docs' / 'validation_matrix.md')}

## Risk Register

{excerpt(ws / 'docs' / 'risk_register.md')}

## Previous Unresolved Issues

"""
    open_issues = [i for i in issues if issue_needs_review_attention(i, approved_waivers)]
    packet += "\n".join(f"- {i.get('severity')} {i.get('id')}: {i.get('summary')}" for i in open_issues) or "None"
    packet += "\n\n## Waivers\n\n"
    packet += "\n".join(
        (
            f"- {w.get('id')}: issue={w.get('issue_id')}, severity={w.get('severity')}, "
            f"status={w.get('status')}, approved_by={w.get('approved_by')}, reason={w.get('reason')}"
        )
        for w in waivers
    ) or "None"
    packet += "\n\n## Changed Files Snapshot\n\n" + "\n".join(f"- {f}" for f in changed_files[:200])
    packet += "\n\n## Review Instructions\n\nReview goal alignment, source provenance, validation evidence, failure modes, rollback, and unresolved issues. Do not modify files in review mode.\n"
    (rdir / "review_packet.md").write_text(packet, encoding="utf-8")
    print(f"wrote {rdir / 'review_packet.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
