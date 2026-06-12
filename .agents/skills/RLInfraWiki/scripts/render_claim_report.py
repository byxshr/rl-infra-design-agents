#!/usr/bin/env python3
from __future__ import annotations

from collections import defaultdict
from _rlinfra import iter_wiki_pages


def main() -> int:
    by_source = defaultdict(list)
    for page in iter_wiki_pages():
        for sid in page.get("sources", []) or []:
            by_source[sid].append(page.get("id"))
    print("# Claim / Source Coverage Report\n")
    for sid in sorted(by_source):
        print(f"## {sid}")
        for pid in sorted(by_source[sid]):
            print(f"- {pid}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
