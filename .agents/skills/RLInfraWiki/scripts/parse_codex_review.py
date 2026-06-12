#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

HEADING_RE = re.compile(r"^#{2,4}\s+(P[0-3])\s*[:\-]\s*(.+)$", re.IGNORECASE)


def issue_id(round_id: str, severity: str, title: str) -> str:
    digest = hashlib.sha256(f"{severity}|{title}".encode("utf-8")).hexdigest()[:10]
    return f"review-{round_id}-{digest}-{severity.lower()}"


def parse(text: str, round_id: str):
    issues = []
    current = None
    seen_ids = set()
    for line in text.splitlines():
        m = HEADING_RE.match(line.strip())
        if m:
            if current:
                issues.append(current)
            severity = m.group(1).upper()
            title = m.group(2).strip()
            iid = issue_id(round_id, severity, title)
            if iid in seen_ids:
                raise ValueError(f"duplicate review finding heading in {round_id}: {severity}: {title}; differentiate the headings")
            seen_ids.add(iid)
            current = {
                "id": iid,
                "round_id": round_id,
                "severity": severity,
                "status": "open",
                "category": "review",
                "source": "codex-review",
                "file": None,
                "summary": title,
                "evidence": [],
                "suggested_fix": None,
            }
            continue
        if current and line.strip().startswith("- File/path:"):
            current["file"] = line.split(":", 1)[1].strip() or None
        elif current and line.strip().startswith("- Suggested fix:"):
            current["suggested_fix"] = line.split(":", 1)[1].strip() or None
        elif current and line.strip().startswith("- Evidence:"):
            val = line.split(":", 1)[1].strip()
            if val:
                current["evidence"].append(val)
    if current:
        issues.append(current)
    return issues


def main() -> int:
    parser = argparse.ArgumentParser(description="Parse Codex review markdown into review issues JSONL")
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    inp = Path(args.input)
    round_id = inp.parent.name if inp.parent.name.startswith("round-") else "round-unknown"
    try:
        issues = parse(inp.read_text(encoding="utf-8"), round_id)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 1
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("".join(json.dumps(issue) + "\n" for issue in issues), encoding="utf-8")
    print(f"parsed {len(issues)} issue(s) into {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
