# Code Review — Round 13 — rl-infra-design-agents

- Date: 2026-06-12
- Scope: triaged fix from `docs/code-review-2026-06-12-round-12.md` plus end-of-series sweep
- Reference: `docs/ai-agent-code-review-reference.md` §"Review Triage Notes"
- Reviewer posture: independent gatekeeper

## Validation Run

| Command | Result |
|---|---|
| `python .agents/skills/RLInfraWiki/scripts/validate.py` | PASS |
| `python .agents/skills/RLInfraWiki/scripts/generate_indices.py --check` | PASS |
| `pytest -q` | PASS — 39 passed (was 37) |
| One open P2 (no waiver) → `summarize_rlcr.py` | `promotion_readiness: blocked` ✓ (was `review-gate-check-needed` pre-fix) |
| One waived P0 with approved waiver → `summarize_rlcr.py` | `promotion_readiness: blocked` ✓ (P0/P1 never honor waivers) |
| Invalid severity `P9` → `summarize_rlcr.py` | `promotion_readiness: blocked` ✓ (fail-closed via helper) |
| One waived P2 + schema-INVALID approved waiver (missing `id`/`approved_by`/`reason`) → `summarize_rlcr.py` | `promotion_readiness: ready (run gate to confirm)` ⚠ |
| Same workspace → `validate_review_gate.py` | exit 1, schema errors + `unresolved P2 without approved waiver` |

Baseline: 12 test files, 39 tests, all green. Round-12 added `test_summarize_rlcr.py` with two cases (`unwaived_p2_as_blocked`, `approved_p2_waiver_as_ready`).

## Round-12 Triage

| Round-12 finding | Status | Notes |
|---|---|---|
| P3 — `summarize_rlcr.py` reports `review-gate-check-needed` for workspaces the gate rejects (P2 unwaived, P1 waived, unknown severity) | **FIXED** | New helper `issue_blocks_promotion(issue, approved_waivers)` in `_rlinfra.py:226-239` encodes the gate's per-issue blocking semantics. `summarize_rlcr.py:19` and `validate_review_gate.py:113` both consume it (DRY achieved). New test file `tests/test_summarize_rlcr.py` covers the unwaived-P2 and approved-P2-waiver paths. Verified empirically across P2 unwaived, P0 waived, P9 (invalid severity) — all three correctly report `blocked`. |

The round-12 fix landed cleanly. End-of-series sweep surfaced one narrow follow-up: `summarize_rlcr.py` doesn't schema-validate waivers before honoring them, so a malformed approved waiver still slips past the summary even though the gate rejects it.

## New Findings

### P3 (unfixed): `summarize_rlcr.py` honors schema-invalid `status="approved"` waivers and reports `ready` while the gate rejects them

- File/path: `.agents/skills/RLInfraWiki/scripts/summarize_rlcr.py:16`
- Evidence:
  ```python
  # summarize_rlcr.py
  approved_waivers = {w.get("issue_id") for w in load_jsonl(ws / "review_waivers.jsonl") if str(w.get("status", "")).lower() == "approved"}
  ```
  ```python
  # validate_review_gate.py:94-100 — gate path
  for idx, waiver in enumerate(load_jsonl(ws / "review_waivers.jsonl"), 1):
      normalized = normalize_review_waiver(waiver)
      waiver_errors = schema_validation_errors(normalized, "review_waiver.schema.json", f"review_waivers.jsonl:{idx}")
      errors.extend(waiver_errors)
      if not waiver_errors and normalized.get("status") == "approved":
          waivers.add(normalized.get("issue_id"))
  ```
  The gate adds an `issue_id` to its `waivers` set **only if** schema validation passes. The summary adds it whenever `status == "approved"`, regardless of schema. So a waiver row missing required fields (`id`, `approved_by`, `reason` per `schemas/review_waiver.schema.json:37-43`) but carrying `status: "approved"` is honored by summary and rejected by gate.

- Reproducer (verified empirically — Validation Run rows 7–8):
  ```bash
  # P2 issue waived, plus a malformed "approved" waiver
  echo '{"id":"i1","round_id":"r","severity":"P2","status":"waived","summary":"foo"}' > review_issues.jsonl
  echo '{"issue_id":"i1","status":"approved"}' > review_waivers.jsonl   # missing id/approved_by/reason

  summarize_rlcr.py    → "promotion_readiness: ready (run gate to confirm)"
  validate_review_gate.py → exit 1
    ERROR: review_waivers.jsonl:1: schema <root>: 'id' is a required property
    ERROR: review_waivers.jsonl:1: schema <root>: 'approved_by' is a required property
    ERROR: review_waivers.jsonl:1: schema <root>: 'reason' is a required property
    ERROR: unresolved P2 without approved waiver blocks promotion: i1 foo
  ```

- Why it matters: round-12's stated promise (reference §"Review Triage Notes" line 150) is *"`summarize_rlcr.py` should report `promotion_readiness: blocked` for the same issue states that would block `validate_review_gate.py`."* A schema-invalid approved waiver IS a state the gate blocks; summary reports `ready (run gate to confirm)`. Strictly speaking, the round-12 contract isn't fully delivered for this edge case. The mitigation is the hedge `(run gate to confirm)` — the architect is explicitly told to confirm — so this is not a hard misdirection.

  P3 (not P2) because: (a) hand-crafting an approved waiver missing required fields is unusual; (b) the summary's wording hedges; (c) the architect running the gate immediately sees the schema error and the block. But it's the natural completion of round-12's intent.

- Suggested fix: have `summarize_rlcr.py` validate waivers via the same `schema_validation_errors` helper before adding to `approved_waivers`:
  ```python
  approved_waivers = set()
  for waiver in load_jsonl(ws / "review_waivers.jsonl"):
      normalized = normalize_review_waiver(waiver)
      if schema_validation_errors(normalized, "review_waiver.schema.json", "summary"):
          continue
      if str(normalized.get("status", "")).lower() == "approved":
          approved_waivers.add(normalized.get("issue_id"))
  ```
  Or extract a shared `load_approved_waivers(ws) -> set[str]` helper to `_rlinfra.py` and have both `validate_review_gate.py` and `summarize_rlcr.py` consume it. The latter is cleaner and parallels how round-12 introduced `issue_blocks_promotion` for the issue-side decision.

  Add a regression test mirroring the round-13 reproducer: write a P2 waived issue + an approved waiver missing `id`/`approved_by`/`reason`, run summary, assert `promotion_readiness: blocked`.

## Open Questions

- Symmetric question: should `summarize_rlcr.py` also schema-validate `review_issues.jsonl` rows, since the gate does? Currently a malformed issue row (e.g., missing `severity`) is treated by the helper as invalid and reports `blocked` — already fail-closed by accident. So no behavioral divergence in practice; I am not flagging this as a finding. Worth noting only because the issue-side and waiver-side asymmetry is the dual of this finding.
- Workspace-level gate failures (missing `plan.lock.md`, stale lock hashes, missing `validation_matrix.md`, missing `docs/goal.md`) are NOT reflected by `summarize_rlcr.py`. The hedge `(run gate to confirm)` is the documented contract for these. Acceptable as-is; flagging only as a reminder of summary's intentional scope limit.
- Thirteen rounds in, the residual surface is now genuinely thin. After this P3 lands — or is explicitly accepted as a documented limitation — there is no remaining material concern I can find. Recommend declaring the review series closed after round-13 triage.

## Summary

The round-12 fix landed cleanly: `_rlinfra.issue_blocks_promotion` encodes the gate's per-issue blocking semantics, and both `summarize_rlcr.py` and `validate_review_gate.py` consume it (DRY). Empirical verification across P2 unwaived, P0 waived (with approved waiver), and P9 (invalid severity) all correctly report `promotion_readiness: blocked`. Tests grew 37 → 39 with a new dedicated test file.

One narrow P3 surfaced from auditing the round-12 contract:

- **P3 (unfixed)** `summarize_rlcr.py:16` builds `approved_waivers` without schema validation, so a malformed `status="approved"` waiver row (missing `id`/`approved_by`/`reason`) is honored by summary while the gate rejects it on schema. Verified by reproducer: P2 waived issue + minimal `{"issue_id":"i1","status":"approved"}` waiver → summary says `ready (run gate to confirm)`, gate exit 1 with three schema errors plus `unresolved P2 without approved waiver`. Round-12's contract — "summary should report `blocked` for the same issue states that block the gate" — is satisfied for the issue-side decision but not for waiver-side schema validation.

Recommended fix: schema-validate waivers in summary before honoring them, or extract a shared `load_approved_waivers(ws)` helper to `_rlinfra.py` mirroring round-12's `issue_blocks_promotion` extraction.

Thirteen rounds in, this is the last narrow correctness concern I can find. After it lands — or is explicitly accepted as a documented "summary is best-effort; gate is authoritative" limitation — the review series can close cleanly.
