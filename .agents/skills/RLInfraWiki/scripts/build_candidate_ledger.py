#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from _rlinfra import load_jsonl


def main() -> int:
    parser = argparse.ArgumentParser(description='Summarize candidates.jsonl in a task workspace.')
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--output", help="Optional JSON summary output path")
    args = parser.parse_args()
    rows = load_jsonl(Path(args.workspace) / "candidates.jsonl")
    summary = {
        "candidate_count": len(rows),
        "by_status": dict(sorted(Counter(str(row.get("status", "unknown")) for row in rows).items())),
        "candidates": [
            {
                "id": row.get("id"),
                "status": row.get("status"),
                "summary": row.get("summary"),
            }
            for row in rows
        ],
    }
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {out}")
    else:
        print(f"candidate_count: {len(rows)}")
        for status, count in summary["by_status"].items():
            print(f"{status}: {count}")
        for row in rows:
            print(f"- {row.get('id')} {row.get('status')} {row.get('summary')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
