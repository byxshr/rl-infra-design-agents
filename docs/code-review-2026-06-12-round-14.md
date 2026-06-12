# Code Review — Round 14 — rl-infra-design-agents

- Date: 2026-06-12
- Scope: triaged fix from `docs/code-review-2026-06-12-round-13.md` plus end-of-series sweep
- Reference: `docs/ai-agent-code-review-reference.md` §"Review Triage Notes"
- Reviewer posture: independent gatekeeper

## Validation Run

| Command | Result |
|---|---|
| `python .agents/skills/RLInfraWiki/scripts/validate.py` | PASS |
| `python .agents/skills/RLInfraWiki/scripts/generate_indices.py --check` | PASS |
| `pytest -q` | PASS — 40 passed (was 39) |
| Round-13 reproducer: P2 waived + minimal `{"issue_id":"i1","status":"approved"}` waiver → `summarize_rlcr.py` | `promotion_readiness: blocked` ✓ (was `ready` pre-fix) |
| Same workspace → `validate_review_gate.py` | exit 1, three schema errors + `unresolved P2 without approved waiver` |
| Same workspace → `render_rlcr_context.py --round 1` | SystemExit `review waiver schema validation failed` (existing round-2 contract preserved) |
| Edge case: P2 with two waivers for same issue id (one `rejected`, one `approved`, both schema-valid) → `summarize_rlcr.py` | `promotion_readiness: ready (run gate to confirm)` ✓; gate exit 0 (approved row honored) |

Baseline: 12 test files, 40 tests, all green. Round-13 added `test_summarize_rlcr_ignores_schema_invalid_approved_waiver`.

## Round-13 Triage

| Round-13 finding | Status | Notes |
|---|---|---|
| P3 — `summarize_rlcr.py:16` honors schema-invalid `status="approved"` waivers; gate rejects them. Round-12 contract not fully delivered for waiver-side schema. | **FIXED** | Shared helper `_rlinfra.load_review_waivers(workspace) -> (waivers, approved, errors)` introduced (`_rlinfra.py:212-227`). Returns the full waiver list, the schema-validated approved set, and per-row schema errors. Three consumers refactored to use it: `summarize_rlcr.py:22` (discards errors — quick-look tool), `validate_review_gate.py:94` (extends gate errors), `render_rlcr_context.py:36-39` (raises SystemExit on errors, preserving the round-2 contract). Verified empirically across all three: malformed approved waiver no longer slips past summary. New regression test `test_summarize_rlcr_ignores_schema_invalid_approved_waiver` encodes the exact round-13 reproducer. |

The round-13 fix landed cleanly. Three end-of-series sweeps over the consumer surface, schema files, and edge cases turned up no new findings.

## New Findings

None.

## Sweep Coverage (no findings, recorded for series closure)

To make round-14's "no findings" claim auditable, here is the sweep I ran:

1. **Round-13 invariant verified end-to-end.** Reproducer from round-13 (`{"issue_id":"i1","status":"approved"}` + P2 waived issue) now produces consistent verdicts across all three consumers — summary says `blocked`, gate exits 1 with schema errors, render aborts with SystemExit. No silent acceptance path remains.

2. **Helper signature is consistent across callers.** `load_review_waivers` returns `(list[dict], set[str], list[str])`. `summarize_rlcr.py:22` unpacks `(waivers, approved, _errors)`; `validate_review_gate.py:94` unpacks `(_, approved, errors)`; `render_rlcr_context.py:36` unpacks `(waivers, approved, errors)`. Each consumer uses the elements it needs and discards the rest cleanly. No off-by-one or wrong-index unpack.

3. **`approved` set keying is symmetric.** Helper does `approved.add(str(normalized.get("issue_id")))` (line 226). `issue_blocks_promotion` does `issue_id = str(issue.get("id", ""))` (line 245). Both str-convert, so set membership matches. Schema requires `issue_id` to be a non-empty string, so neither side sees `"None"` or `""` for valid rows.

4. **Edge cases probed**:
   - Two waivers for same issue (rejected + approved): approved row's id added to set; gate and summary both treat issue as approved. Consistent.
   - Approved waiver pointing at a nonexistent issue id: dangling entry in approved set, never matched. No false positive.
   - P0 waived with approved waiver: `issue_blocks_promotion` returns `True` for P0 regardless of approval — blocks. Both summary and gate. Consistent with reference §"Review Triage Notes" line 151.
   - Empty `review_waivers.jsonl` and missing file: helper returns `([], set(), [])`. All consumers handle.
   - Schema-valid waiver with `status="rejected"`: not added to approved set, no errors emitted. Issue with that waiver still blocks. Correct.

5. **No regression vs round-12**. The pre-helper inline loops in `validate_review_gate.py` and `render_rlcr_context.py` had per-row labels `f"review_waivers.jsonl:{idx}"`. The helper preserves that exact label format (line 222). The gate's existing test `test_review_gate_schema_validates_waivers_before_honoring` still passes, asserting both the schema error and the downstream block.

6. **Documented limitations confirmed unchanged** (these are intentional, not findings):
   - Workspace-level gate failures (missing `plan.lock.md`, stale lock hashes, missing `validation_matrix.md`, missing `docs/goal.md`) are NOT reflected by `summarize_rlcr.py`. The hedge `(run gate to confirm)` is the documented contract.
   - Architect-set `status` (e.g., `in_progress`) is reset to parser default `open` on `--allow-overwrite` re-ingest because `status` is in `SIGNIFICANT_FIELDS`. Documented as "non-conflicting" semantics in CLAUDE.md.
   - Heading rename mid-round creates a new content-hash issue id and orphans the prior. Documented as intentional re-ingestion event.
   - Broad framework-mention scan not implemented as a hard validator (false-positive risk). Documented at reference line 173.

## Open Questions

- `load_jsonl` does not catch `JSONDecodeError`, so a malformed line in `review_waivers.jsonl` (or `review_issues.jsonl`, or `goal_versions.jsonl`) crashes the consumer with a Python traceback rather than a clean error message. This pre-dates round 13 and applies to all JSONL consumers in the project. Not flagging as a finding because: (a) the project's contract is that JSONL files are produced by tooling, not hand-edited freely; (b) the traceback is recoverable; (c) it would be a larger refactor than the typical end-of-series polish. Worth a future P3 if the project ever opens JSONL editing to less-careful consumers.
- The series has now reached 14 triaged rounds. Findings have been: 3 P0 (round 1, all instances fixed), 8 P1 (across rounds 2–9, all fixed), ~7 P2 (across rounds 1–10, all fixed or waived), ~7 P3 (across rounds 11–13, all fixed). The codebase has materially converged. **Recommend declaring the review series complete after round-14.**

## Summary

The round-13 fix landed cleanly: a shared `_rlinfra.load_review_waivers(workspace)` helper now returns the full waiver list, the schema-validated approved set, and per-row schema errors. All three consumers (`summarize_rlcr.py`, `validate_review_gate.py`, `render_rlcr_context.py`) consume it consistently. The exact round-13 reproducer is encoded as a regression test. Empirical verification confirms summary, gate, and render packet now agree on schema-invalid approved waivers. Tests grew 39 → 40.

End-of-series sweep across consumer surface, schema files, edge cases (multi-waiver, dangling waiver, P0 waived, empty file), and round-12/13 invariants found **no new material concerns**. The remaining "soft" gaps (workspace-level checks not in summary, JSON parse errors as raw tracebacks, status reset under `--allow-overwrite`) are all either documented as intentional limitations or pre-existing concerns that span the entire codebase rather than the round-13 change.

Fourteen rounds in, with the round-13 P3 closed and no new finding visible after a thorough sweep, this review series can be declared complete. The codebase has converged to a state where remaining concerns are workflow-design tradeoffs rather than correctness bugs.
