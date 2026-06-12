#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from _rlinfra import load_jsonl, load_source_manifests


def main() -> int:
    parser = argparse.ArgumentParser(description='Prepare a source manifest draft for a local upstream repo.')
    parser.add_argument("--workspace", default=".")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if "candidate" in Path(__file__).name:
        rows = load_jsonl(Path(args.workspace) / "candidates.jsonl")
        print(f"candidate_count: {len(rows)}")
        for row in rows:
            print(f"- {row.get('id')} {row.get('status')} {row.get('summary')}")
    else:
        manifests = load_source_manifests()
        print(f"source_manifest_count: {len(manifests)}")
        for sid, manifest in sorted(manifests.items()):
            print(f"- {sid}: {manifest.get('local_path') or manifest.get('repo')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
