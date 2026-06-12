#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from _rlinfra import iter_wiki_pages, load_source_manifests, load_version_claims, QUERIES_DIR


def main() -> int:
    pages = iter_wiki_pages()
    sources = load_source_manifests()
    versions = load_version_claims()
    by_type = Counter(page.get("type", "unknown") for page in pages)
    print("RLInfraWiki status")
    print(f"wiki_pages: {len(pages)}")
    for key, count in sorted(by_type.items()):
        print(f"  {key}: {count}")
    print(f"source_manifests: {len(sources)}")
    print(f"version_claims: {len(versions)}")
    print(f"query_indices: {len(list(QUERIES_DIR.glob('*.md'))) if QUERIES_DIR.exists() else 0}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
