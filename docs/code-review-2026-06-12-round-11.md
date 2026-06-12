# Code Review — Round 11 — rl-infra-design-agents

- Date: 2026-06-12
- Scope: triaged fix from `docs/code-review-2026-06-12-round-10.md` plus end-of-series sweep
- Reference: `docs/ai-agent-code-review-reference.md` §"Review Triage Notes"
- Reviewer posture: independent gatekeeper

## Validation Run

| Command | Result |
|---|---|
| `python .agents/skills/RLInfraWiki/scripts/validate.py` | PASS |
| `python .agents/skills/RLInfraWiki/scripts/generate_indices.py --check` | PASS |
| `pytest -q` | PASS — 36 passed (was 35) |
| Contract `[pytest, pytest -k integration]` → matrix has only the long row → re-lock → gate | FAIL with `validation_matrix.md missing validation command from task_contract.yaml: pytest`, exit 1 |
| Empty `validation_commands` contract → render → lock → gate | PASS — no false positive |
| Schema validation (`Draft202012Validator.iter_errors`) on a verified wiki page, a source manifest, and a task contract | PASS — zero errors each |

Baseline: 11 test files, 36 tests, all green. Round-10 added `test_review_gate_matches_validation_matrix_commands_exactly`.

## Round-10 Triage

| Round-10 finding | Status | Notes |
|---|---|---|
| P2 — `validate_contract_validation_matrix` substring-match fragility | **FIXED** | `validate_review_gate.py:70` now uses `re.findall(r"`([^`]+)`", matrix)` to extract exactly backtick-wrapped tokens; checks exact set membership. Verified empirically with the prefix-collision case `pytest` vs `pytest -k integration`. |

The round-10 fix landed cleanly. End-of-series sweep surfaced one narrow residual that ten rounds had not addressed: `merge_issue` silently overwrites architect-set fields when the parser provides a default for the same field.

## New Findings

### P3 (unfixed): `merge_issue` clobbers architect-set fields that `parse_codex_review.py` populates with defaults (e.g., `owner`, `created_at`, `resolved_at`, `resolution`)

- File/path: `.agents/skills/RLInfraWiki/scripts/append_review_round.py:30-33`; default-populating code at `.agents/skills/RLInfraWiki/scripts/parse_codex_review.py:34-49`
- Evidence:
  ```python
  # append_review_round.py
  def merge_issue(existing: dict, incoming: dict) -> dict:
      merged = dict(existing)
      merged.update(incoming)
      return merged
  ```
  ```python
  # parse_codex_review.py — every parsed issue gets these defaults:
  current = {
      "id": iid, "round_id": ..., "severity": ..., "status": "open",
      ...
      "owner": "claude-builder",          # ← parser default
      "created_at": now_iso(),            # ← parser default (changes on re-parse)
      "resolved_at": None,                # ← parser default
      "resolution": None,                 # ← parser default
  }
  ```
  `dict(existing).update(incoming)` makes incoming win whenever the same key exists in both. For fields the parser doesn't emit (e.g., `notes`), the architect's value survives — which the round-4 fix was designed to deliver. But for fields the parser emits with a *default* value (`owner: "claude-builder"`, `resolved_at: null`), the architect's value is silently overwritten because the parser's default is treated as "incoming truth."

- Reproducer (verified empirically):
  ```bash
  # 1. Initial ingestion via the real parse path
  parse_codex_review.py → parsed_issues.jsonl (owner: claude-builder)
  append_review_round.py → review_issues.jsonl row has owner: claude-builder

  # 2. Architect curates the ledger
  edit review_issues.jsonl: rows[0].owner = "alice"; rows[0].notes = "human-context"

  # 3. Reviewer corrects codex_review.md (adds Suggested fix line)
  parse_codex_review.py → fresh parsed_issues.jsonl (owner: claude-builder again)

  # 4. Re-ingest with --allow-overwrite
  append_review_round.py … --allow-overwrite

  # Result:
  owner after: claude-builder      ← CLOBBERED (architect's alice gone)
  notes after: human-context        ← preserved (parser doesn't emit notes)
  suggested_fix after: "…"          ← updated correctly
  ```
- Why it matters: the round-4 design intent (and reference §"Review Triage Notes" line 148) is "overwrite should preserve non-conflicting human annotations." The fix preserves fields the parser doesn't touch, but silently reverts any field the parser emits with a default — including `owner`, which is a primary annotation the architect uses to assign a fix to a builder. The existing test `test_append_review_round_conflict_requires_explicit_overwrite` only passes because it hand-crafts `parsed_issues.jsonl` without `owner`/`created_at`/etc.; under the real `parse_codex_review.py` path, those fields always come back as parser defaults.

  P3 (not P2) because: (a) the path requires same-round re-parse + architect curation between, (b) the architect notices on inspection, (c) the parser's default is reasonable when the row is genuinely fresh. But the contract that the docs imply ("owner is preserved") is not enforced.

- Suggested fix: pick one of three:
  1. **Drop parser defaults that the architect should own.** In `parse_codex_review.py`, only set fields that come from the markdown content (`id`, `round_id`, `severity`, `status: "open"`, `summary`, `file`, `suggested_fix`, `evidence`). Leave `owner`, `created_at`, `resolved_at`, `resolution` to be set by `append_review_round.py` (or by the architect). Then `merge_issue` automatically preserves architect edits on those fields because the incoming dict simply doesn't have them.
  2. **Smarter merge.** Compute parser defaults and treat them as "absent" in the incoming row: `if incoming[k] == PARSER_DEFAULTS.get(k): existing[k] survives else incoming wins`. More magical, harder to read.
  3. **Document and accept.** Update CLAUDE.md to say "fields with parser defaults — owner, created_at, resolved_at, resolution — are reset on `--allow-overwrite`." Lowest cost, but contradicts the spirit of round-4.

  Either (1) or (3) is fine; (1) is the cleanest. Add a regression test that runs the **real** `parse_codex_review → append_review_round` path twice with hand-set `owner` between, and asserts `owner` survives.

## Open Questions

- Round-1 to round-11 has now triaged 11 distinct rounds. Severity distribution: 1 P0 (round 1, 3 instances all fixed), 8 P1 across rounds (all fixed), ~6 P2, ~5 P3. The system is materially production-ready. Recommend the team either (a) fix this P3 and close the series, or (b) accept it as a documented limitation and close the series.
- One genuinely unaddressed concern carried over from round 5: heading rename mid-round creates a new content-hash id and orphans the prior. The reference §"Review Triage Notes" line 151 documents this as intentional ("renaming a heading mid-round creates a new issue id and should be intentional"). Acceptable as documented behavior — flagging here only as a reminder that this is the only other "feature documented in lieu of fix" decision in the series.

## Summary

The round-10 fix landed cleanly: the gate's contract↔matrix check now uses backtick-wrapped exact-match instead of substring matching. Tests grew 35 → 36.

One narrow P3 surfaced from the end-of-series sweep:

- **P3 (unfixed)** `merge_issue` in `append_review_round.py` silently overwrites architect-set `owner`/`created_at`/`resolved_at`/`resolution` when re-ingesting same-round parsed issues, because `parse_codex_review.py` populates those fields with defaults that win in the merge. The existing test passes only because it sanitizes `parsed_issues.jsonl`; the real-workflow re-ingest path clobbers `owner`. Recoverable, but contradicts the round-4 "preserve non-conflicting human annotations" design intent.

Recommended fix: drop `owner`/`created_at`/`resolved_at`/`resolution` from `parse_codex_review.py`'s emitted row and let `append_review_round.py` (or the architect) own them.

Eleven rounds in, this is the last narrow correctness concern. After it lands — or is explicitly accepted as a limitation — the review series can close cleanly.
