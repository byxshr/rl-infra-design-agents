#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from _rlinfra import append_jsonl, now_iso, schema_validation_errors

VALID_GOAL_STATUSES = ["active", "completed", "blocked", "needs-amendment"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Append a goal update record")
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--status", required=True, choices=VALID_GOAL_STATUSES)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--approved-by", default="human-architect")
    args = parser.parse_args()
    ws = Path(args.workspace)
    record = {"timestamp": now_iso(), "status": args.status, "reason": args.reason, "approved_by": args.approved_by}
    errors = schema_validation_errors(record, "goal_update.schema.json", "goal update")
    if errors:
        print("ERROR: goal update failed schema validation")
        for err in errors:
            print(f"  - {err}")
        return 1
    append_jsonl(ws / "goal_versions.jsonl", [record])
    print(f"appended goal update: {args.status}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
