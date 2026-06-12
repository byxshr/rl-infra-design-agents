#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

REQUIRED = ["# Goal Contract", "## Goal ID", "## Status", "## Outcome", "## Acceptance criteria", "## Review policy"]


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a goal contract markdown file")
    parser.add_argument("--goal", default="docs/goal.md")
    args = parser.parse_args()
    path = Path(args.goal)
    text = path.read_text(encoding="utf-8")
    missing = [item for item in REQUIRED if item not in text]
    if missing:
        print(f"ERROR: {path} missing sections: {', '.join(missing)}")
        return 1
    if "active" not in text and "completed" not in text and "blocked" not in text and "needs-amendment" not in text:
        print(f"ERROR: {path} has no recognized status")
        return 1
    print(f"goal contract valid: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
