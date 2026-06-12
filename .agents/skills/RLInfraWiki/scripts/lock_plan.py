#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from _rlinfra import now_iso, sha256_file


def main() -> int:
    parser = argparse.ArgumentParser(description="Lock docs/plan.md into .humanize/plan.lock.md")
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args()
    ws = Path(args.workspace)
    plan = ws / "docs" / "plan.md"
    if not plan.exists():
        print(f"ERROR: missing {plan}")
        return 1
    lock = ws / ".humanize" / "plan.lock.md"
    lock.parent.mkdir(parents=True, exist_ok=True)
    header = f"""# Plan Lock

- locked_at: {now_iso()}
- plan_sha256: {sha256_file(plan)}
- task_contract_sha256: {sha256_file(ws / 'task_contract.yaml')}
- goal_sha256: {sha256_file(ws / 'docs' / 'goal.md')}

---

"""
    lock.write_text(header + plan.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"wrote {lock}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
