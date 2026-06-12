# Code Review — Round 12 — rl-infra-design-agents

- Date: 2026-06-12
- Scope: triaged fix from `docs/code-review-2026-06-12-round-11.md` plus end-of-series sweep
- Reference: `docs/ai-agent-code-review-reference.md` §"Review Triage Notes"
- Reviewer posture: independent gatekeeper

## Validation Run

| Command | Result |
|---|---|
| `python .agents/skills/RLInfraWiki/scripts/validate.py` | PASS |
| `python .agents/skills/RLInfraWiki/scripts/generate_indices.py --check` | PASS |
| `pytest -q` | PASS — 37 passed (was 36) |
| Real-parse → ingest → architect sets `owner=alice`, `notes=WIP` → re-parse → `--allow-overwrite` | `owner=alice` ✓, `notes=WIP` ✓, `created_at` stable ✓, `suggested_fix` updated ✓ |
| `parsed_issues.jsonl` validated directly against `schemas/review_issue.schema.json` | PASS — schema requires only id/round_id/severity/status/summary, all still emitted |
| Workspace with one P2 open (no waiver) → `validate_review_gate.py` | `ERROR: unresolved P2 without approved waiver blocks promotion`, exit 1 |
| Same workspace → `summarize_rlcr.py --workspace .` | `promotion_readiness: review-gate-check-needed` (NOT "blocked") |

Baseline: 11 test files, 37 tests, all green. Round-11 added `test_append_review_round_real_parse_overwrite_preserves_owner`.

## Round-11 Triage

| Round-11 finding | Status | Notes |
|---|---|---|
| P3 — `merge_issue` clobbers architect-set fields the parser populates with defaults (`owner`, `created_at`, `resolved_at`, `resolution`) | **FIXED** | Two-part fix: (1) `parse_codex_review.py:33-44` no longer emits `owner`/`created_at`/`resolved_at`/`resolution`; (2) `append_review_round.py:10-16` introduces `DEFAULT_ISSUE_FIELDS` and `issue_with_defaults` (lines 43-47), applied to fresh issues only at line 102. For existing-conflict-overwrite at line 88, `merge_issue(existing, normalized_incoming)` now preserves the existing row's parser-default fields because the incoming dict no longer carries them. Verified empirically via the new test and a fresh end-to-end reproducer. |

The round-11 fix landed cleanly. End-of-series sweep surfaced one minor consistency drift between `summarize_rlcr.py` and the actual review gate.

## New Findings

### P3 (unfixed): `summarize_rlcr.py` reports `promotion_readiness: review-gate-check-needed` for workspaces the gate actually rejects (P2 unwaived, P1 waived, etc.)

- File/path: `.agents/skills/RLInfraWiki/scripts/summarize_rlcr.py:25`
- Evidence:
  ```python
  # summarize_rlcr.py
  counts = Counter(i.get("severity", "unknown") for i in issues if issue_needs_review_attention(i, approved_waivers))
  ...
  print(f"promotion_readiness: {'blocked' if counts.get('P0') or counts.get('P1') else 'review-gate-check-needed'}")
  ```
  ```python
  # validate_review_gate.py:112-117
  if severity in {"P0", "P1"}:
      errors.append(f"unresolved {severity} issue blocks promotion: ...")
  elif severity == "P2":
      if status == "waived" and issue_id in waivers:
          continue
      errors.append(f"unresolved P2 without approved waiver blocks promotion: ...")
  ```
  The gate blocks for: open P0/P1 (any status that isn't terminal), P1 waived (waivers don't help P0/P1), P2 unwaived, P2 with waiver row that fails schema, unknown severity/status. The summary line only flags P0/P1 counts; everything else collapses to "review-gate-check-needed."

- Reproducer (verified empirically — see Validation Run row 6 vs row 7):
  ```bash
  # Workspace with one open P2 issue, no waiver
  validate_review_gate.py → "Review gate failed; ERROR: unresolved P2 without approved waiver blocks promotion", exit 1
  summarize_rlcr.py     → "open_issues_by_severity: P2: 1; promotion_readiness: review-gate-check-needed"
  ```
  The summary's wording is technically defensible ("you should run the gate"), but it gives the architect a "yellow light" feel when the gate would actually red-light the workspace. Compare to the P0/P1 case where the summary correctly says "blocked."

- Why it matters: `summarize_rlcr.py` is the dashboard view an architect uses to triage workspace state at a glance. When summary says "review-gate-check-needed" the architect's mental model is "probably fine, just needs a check"; when it says "blocked" they know the gate will reject. The current threshold (P0/P1 only) understates blocking severity by treating P2 unwaived and P1 waived as ambiguous rather than clearly blocking. The information is computable: `summarize_rlcr.py` already has `approved_waivers`, `issue_needs_review_attention`, and the severity counts — replicating the gate's classification is straightforward.

  P3 (not P2) because: (a) the message hedges with "check-needed" rather than affirmatively stating "ready", so an architect who runs the gate will still see the rejection; (b) no automation gates on this string; (c) it's an information-clarity issue, not a correctness bug. But it's an unnecessary divergence — the summarizer has all the inputs to call it correctly.

- Suggested fix: in `summarize_rlcr.py`, replicate `validate_review_gate.py`'s classification:
  ```python
  blocks = []
  for issue in issues:
      if not issue_needs_review_attention(issue, approved_waivers):
          continue
      severity = str(issue.get("severity", "")).upper()
      status = str(issue.get("status", "open")).lower()
      if severity in {"P0", "P1"}:
          blocks.append(severity)
      elif severity == "P2" and not (status == "waived" and issue.get("id") in approved_waivers):
          blocks.append(severity)
      elif severity not in VALID_SEVERITIES:
          blocks.append("unknown")
  print(f"promotion_readiness: {'blocked' if blocks else 'ready (run gate to confirm)'}")
  ```
  Or extract the gate's per-issue classification into a shared helper in `_rlinfra.py` (`gate_decision(issue, approved_waivers) -> "block"|"warn"|"pass"`) and have both `validate_review_gate.py` and `summarize_rlcr.py` consume it. The latter is cleaner but a bigger touch.

  Add a regression test that constructs a workspace with one open P2 (no waiver) and asserts `summarize_rlcr.py` prints `promotion_readiness: blocked` (or whatever matches the gate's verdict).

## Open Questions

- Round-11 noted the parser still emits `status: "open"`, `category: "review"`, `source: "codex-review"` as constants. Of these, only `status` is in `SIGNIFICANT_FIELDS` and triggers conflict detection — meaning if the architect sets status to `in_progress` and then re-parses, the architect must use `--allow-overwrite` and accepts `status` resetting to `"open"`. This IS the documented contract ("overwrite should preserve **non-conflicting** human annotations" — reference §"Review Triage Notes" line 150), so it's not a bug. Flagging only because it's the natural follow-up question to round-11 and the answer is "by design." `category` and `source` are clobbered silently on `--allow-overwrite` but are workflow-identity fields no architect would meaningfully edit; not worth flagging.
- Twelve rounds in, the "summarizer vs gate" finding is the only material residual I can find. The rest of the system is genuinely production-ready.
- The originally suggested "broad framework-mention scan" (round-1) remains unimplemented as documented (reference line 168) — accepted as out of scope.

## Summary

The round-11 fix landed cleanly: `parse_codex_review.py` no longer emits parser-default fields (`owner`, `created_at`, `resolved_at`, `resolution`); `append_review_round.py`'s `issue_with_defaults` adds them only on first ingestion, so `--allow-overwrite` re-ingestions preserve architect-curated values. Verified end-to-end with a real-parse reproducer: `owner=alice` and `notes=WIP` survive a re-parse + `--allow-overwrite` cycle while `suggested_fix` updates correctly. Tests grew 36 → 37.

One narrow P3 surfaced from the end-of-series sweep:

- **P3 (unfixed)** `summarize_rlcr.py:25` reports `promotion_readiness: review-gate-check-needed` for workspaces the gate actually rejects (P2 unwaived, P1 waived, unknown severity). The summarizer threshold checks only P0/P1; the gate blocks more conditions. Consequence: an architect glancing at the summary sees "yellow light" when running the gate would show red. Not a correctness bug (the message hedges, no automation depends on it) but an unnecessary divergence between two views of the same data. Fix is straightforward: replicate the gate's per-issue classification in the summarizer, or extract it to a shared helper.

After this fix — or explicit acceptance as "summarizer is intentionally conservative" — the residual surface is genuinely closed. Twelve rounds in, the codebase has converged. Recommend declaring the review series complete after round-12 triage.
