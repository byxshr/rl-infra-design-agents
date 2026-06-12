#!/usr/bin/env python3
from __future__ import annotations

import argparse
from _rlinfra import find_page, load_source_manifests, split_frontmatter, dump_yaml, SKILL_ROOT


def main() -> int:
    parser = argparse.ArgumentParser(description="Get an RLInfraWiki page by id or path")
    parser.add_argument("lookup")
    parser.add_argument("--body-only", action="store_true")
    parser.add_argument("--frontmatter-only", action="store_true")
    parser.add_argument("--follow-sources", action="store_true")
    args = parser.parse_args()

    path = find_page(args.lookup)
    if not path:
        print(f"ERROR: no page found for {args.lookup}")
        return 1
    fm, body = split_frontmatter(path)
    if args.frontmatter_only:
        print(dump_yaml(fm or {}), end="")
        return 0
    if args.body_only:
        print(body)
        return 0
    print(f"# {path.relative_to(SKILL_ROOT)}\n")
    print(path.read_text(encoding="utf-8"))
    if args.follow_sources and fm:
        manifests = load_source_manifests()
        print("\n---\n## Cited Sources\n")
        for sid in fm.get("sources", []):
            source = manifests.get(sid)
            if not source:
                print(f"### {sid}\nMissing source manifest.\n")
                continue
            print(f"### {sid}")
            print(f"- manifest: `{source.get('_path')}`")
            print(f"- name: {source.get('name')}")
            print(f"- repo: {source.get('repo')}")
            print(f"- commit: {source.get('upstream_commit')}")
            print(f"- confidence: source-reported unless local evidence says otherwise\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
