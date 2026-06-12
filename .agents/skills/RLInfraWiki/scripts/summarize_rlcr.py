#!/usr/bin/env python3
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
from _rlinfra import (
    issue_blocks_promotion,
    issue_needs_review_attention,
    load_jsonl,
    load_review_waivers,
    normalize_review_issue,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize an RLCR workspace")
    parser.add_argument("--workspace", required=True)
    args = parser.parse_args()
    ws = Path(args.workspace)
    issues = load_jsonl(ws / "review_issues.jsonl")
    waivers, approved_waivers, _waiver_errors = load_review_waivers(ws)
    normalized_issues = [normalize_review_issue(issue) for issue in issues]
    counts = Counter(
        i.get("severity", "unknown")
        for i in normalized_issues
        if issue_needs_review_attention(i, approved_waivers)
    )
    blocking = [issue for issue in normalized_issues if issue_blocks_promotion(issue, approved_waivers)]
    rounds = sorted((ws / "review_rounds").glob("round-*")) if (ws / "review_rounds").exists() else []
    print(f"round_count: {len(rounds)}")
    print("open_issues_by_severity:")
    for sev in ["P0", "P1", "P2", "P3", "unknown"]:
        if counts.get(sev):
            print(f"  {sev}: {counts[sev]}")
    print(f"waived_issues: {len(waivers)}")
    print(f"promotion_readiness: {'blocked' if blocking else 'ready (run gate to confirm)'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
