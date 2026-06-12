#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
from _rlinfra import SKILL_ROOT


def main() -> int:
    parser = argparse.ArgumentParser(description="Grep RLInfraWiki markdown, YAML, and scripts")
    parser.add_argument("pattern")
    parser.add_argument("--ignore-case", action="store_true", default=True)
    parser.add_argument("--case-sensitive", action="store_true")
    args = parser.parse_args()
    flags = 0 if args.case_sensitive else re.IGNORECASE
    rx = re.compile(args.pattern, flags)
    roots = ["wiki", "sources", "data", "references"]
    count = 0
    for root in roots:
        base = SKILL_ROOT / root
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in {".md", ".yaml", ".yml", ".json"}:
                continue
            for lineno, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if rx.search(line):
                    count += 1
                    print(f"{path.relative_to(SKILL_ROOT)}:{lineno}: {line}")
    if count == 0:
        print("No matches.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
