#!/usr/bin/env python3
from __future__ import annotations

from _rlinfra import iter_wiki_pages, load_source_manifests, load_version_claims


def main() -> int:
    sources = load_source_manifests()
    versions = load_version_claims()
    errors = []
    for page in iter_wiki_pages():
        for sid in page.get("sources", []) or []:
            if sid not in sources:
                errors.append(f"{page.get('id')}: unknown source {sid}")
        for vid in page.get("version_sensitive", []) or []:
            if vid not in versions:
                errors.append(f"{page.get('id')}: unknown version claim {vid}")
    if errors:
        print("Provenance check failed")
        for err in errors:
            print(f"  - {err}")
        return 1
    print("Provenance check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
