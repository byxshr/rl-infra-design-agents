# Code Review — Round 6 — rl-infra-design-agents

- Date: 2026-06-12
- Scope: triaged fixes from `docs/code-review-2026-06-12-round-5.md` plus end-to-end RLCR flow
- Reference: `docs/ai-agent-code-review-reference.md` §"Review Triage Notes"
- Reviewer posture: independent gatekeeper

## Validation Run

| Command | Result |
|---|---|
| `python .agents/skills/RLInfraWiki/scripts/validate.py` | PASS — `RLInfraWiki validation passed` |
| `python .agents/skills/RLInfraWiki/scripts/generate_indices.py --check` | PASS — `generated query indices are current` |
| `pytest -q` | PASS — 30 passed (was 26) |
| Goal-update preserved across `--force` | PASS — both contract row and `needs-amendment` row survive |
| Content-hash issue ids stable on re-parse | PASS — prepending P0 keeps `a58e6f12db-p1` and `80393ddb4a-p2`, only the new P0 gets a fresh id |
| `append_goal_update.py --status complete` (typo) | PASS — argparse rejects with `invalid choice`, exit 2 |

Baseline: 11 test files (was 10), 30 tests, all green.

## Round-5 Triage

| Round-5 finding | Status | Notes |
|---|---|---|
| P1 — `--force` truncates `goal_versions.jsonl` after `append_goal_update.py` | **FIXED** | `render_task_bundle.py:70-75` `last_contract_hash` now walks `reversed(rows)` and skips rows without `contract_hash`. Verified by reproducer: contract row + goal-update row → `--force` re-render preserves both. |
| P2 — Positional issue ids shift on re-parse | **FIXED** | `parse_codex_review.py:14-16` mints `review-{round}-{sha256(severity\|title)[:10]}-{sev}`. Re-parsing the same round after inserting a heading does not orphan prior rows. |
| P3 — `append_goal_update.py` accepts any `--status` | **FIXED** | `append_goal_update.py:14` declares `choices=VALID_GOAL_STATUSES`; record is also schema-validated against `goal_update.schema.json` before write. |

All three round-5 findings closed cleanly. The content-hash id change does, however, introduce a new collision class — finding #2 below.

## New / Remaining Findings

### P1 (unfixed): `validate_review_gate.py` does not detect drift between `plan.lock.md` and the current `docs/plan.md`

- File/path: `.agents/skills/RLInfraWiki/scripts/validate_review_gate.py:19-20` (and `lock_plan.py:18-30`)
- Evidence:
  ```python
  # validate_review_gate.py:19-20
  if not (ws / ".humanize" / "plan.lock.md").exists():
      errors.append("missing .humanize/plan.lock.md")
  ```
  The gate only checks that the lock *file* exists. `lock_plan.py:23` records `plan_sha256: <sha256_file(plan)>` (also `task_contract_sha256` and `goal_sha256`), but no caller ever validates those hashes against the current files.
- Reproducer (verified empirically):
  ```bash
  render_task_bundle.py --contract slime-weight-sync.yaml --output WS
  lock_plan.py --workspace WS                          # plan.lock.md records plan_sha256=8f0e...
  echo "# Completely different plan" > WS/docs/plan.md  # post-lock plan edit
  validate_review_gate.py --workspace WS                # → "Review gate passed", exit 0
  ```
  The same drift is reachable through the supported path: `render_task_bundle.py --force --overwrite-human-docs` rewrites `docs/plan.md` to the contract-derived default, but `plan.lock.md` is not regenerated, so the lock continues to point at the prior plan body.
- Why it blocks: Reference §"Blocking Review Checks" — "Causes `render_task_bundle.py`, `lock_plan.py`, or `render_rlcr_context.py` to produce incomplete RLCR workspaces" + "Weakens `validate_review_gate.py` so unresolved P0/P1 issues no longer block promotion." With drift, the review packet shows the **old** plan (the lock excerpt embedded in `review_packet.md`) while Claude implements the **new** plan; reviewer-vs-implementation skew goes undetected. The hash field exists in the lock specifically so it can be validated; today it is decorative. This is the same class of regression that round-1's empty-goal/plan-overwrite finding addressed for `goal_versions.jsonl`, but for `plan.lock.md`.
- Suggested fix: in `validate_review_gate.py`, parse the `plan_sha256:` line from `.humanize/plan.lock.md` and compare against `sha256_file(ws / 'docs' / 'plan.md')`; emit an error like `plan.lock.md does not match docs/plan.md; rerun lock_plan.py`. Apply the same to `task_contract_sha256` and `goal_sha256` (or document explicitly that those are advisory). Add a regression test that locks → edits `docs/plan.md` → asserts the gate fails until `lock_plan.py` is re-run.

### P2 (new): Round-5's content-hash issue id introduces a collision when two findings share severity+title; `--allow-overwrite` silently drops one of them

- File/path: `.agents/skills/RLInfraWiki/scripts/parse_codex_review.py:14-16`; `.agents/skills/RLInfraWiki/scripts/append_review_round.py:78-86`
- Evidence:
  ```python
  # parse_codex_review.py
  def issue_id(round_id: str, severity: str, title: str) -> str:
      digest = hashlib.sha256(f"{severity}|{title}".encode("utf-8")).hexdigest()[:10]
      return f"review-{round_id}-{digest}-{severity.lower()}"
  ```
  The id depends only on `severity + title`, so two distinct findings under identical headings collide. The intra-ingestion conflict path then triggers, with this error message in `append_review_round.py`:
  ```
  ERROR: duplicate review issue id(s) changed; rerun with --allow-overwrite to replace them
  ```
  …pushing the user toward `--allow-overwrite`, which calls `merge_issue` on the colliding rows and produces a single ledger row that contains only the second occurrence's `file`/`suggested_fix`.
- Reproducer (verified empirically): a `codex_review.md` with two `### P1: missing validation` headings, one citing `foo.py`/`add foo guard` and another `bar.py`/`add bar guard`. `parse_codex_review.py` writes both rows with the same id `review-round-001-a58e6f12db-p1`. `append_review_round.py` (no flag) errors and prompts for `--allow-overwrite`. With `--allow-overwrite`, the ledger ends up with one row: `file=bar.py, suggested_fix=add bar guard`. The `foo.py` finding is silently lost.
- Why it matters: realistic trigger — a reviewer copy-pastes a heading template, or has two distinct sites of the same class of problem and gives them the same one-line title. The error message recommends the destructive action without warning that the two rows are different findings (the prior `--allow-overwrite` user model, set in `CLAUDE.md`, is "the SAME issue ID with changed fields → rerun with `--allow-overwrite`" — but here the two rows are not the same issue; they only happen to hash to the same id). The signal that two parsed rows share an id is available at parse time but never surfaced.
- Suggested fix: detect intra-`parsed_issues.jsonl` id collisions in `parse_codex_review.py` and fail with a message like `two findings in round-XXX share severity+title; differentiate the headings`. Alternatively, include a positional disambiguator in the digest input — e.g. `digest = sha256(f"{severity}|{title}|{order}")` — and reserve cross-round id stability for the case the reference describes ("unchanged findings keep the same severity and title"); positional disambiguator only kicks in when there's an actual same-round collision, leaving the round-5 stability guarantee intact for distinct headings. Add a regression test that ingests two same-titled findings and asserts neither is silently dropped.

### P3 (unfixed): Dead `RESOLVED_STATUSES` alias in `_rlinfra.py`

- File/path: `.agents/skills/RLInfraWiki/scripts/_rlinfra.py:27-28`
- Evidence:
  ```python
  # Backward-compatible alias for callers that mean "actually fixed".
  RESOLVED_STATUSES = TERMINAL_STATUSES
  ```
  No remaining caller in `scripts/` or `tests/` imports `RESOLVED_STATUSES`. The only references are inside historical review write-ups under `docs/`. Its presence implies a public-API contract that does not exist.
- Why it matters: not a runtime issue; reader confusion only. Cleanup, since the round-2 review-gate refactor is the original reason this alias was introduced and the codebase has since standardized on `TERMINAL_STATUSES` / `DEFERRED_STATUSES` / `CLOSED_STATUSES`.
- Suggested fix: delete `RESOLVED_STATUSES` and the comment. If any external skill is suspected to import it, mark with a `# Deprecated: external skills, switch to TERMINAL_STATUSES` comment and remove in a follow-up.

## Open Questions

- For finding #1, the lock also records `task_contract_sha256` and `goal_sha256`. After `--force`, `task_contract.yaml` is `shutil.copyfile`-overwritten to the contract on disk and `docs/goal.md` is regenerated (or preserved under default `--force`). Should the gate also enforce these? Most natural answer: yes — the lock exists precisely to detect this drift class, and the cost of failing the gate when stale is one extra `lock_plan.py` invocation.
- For finding #2's "positional disambiguator" alternative, the digest input becomes `severity|title|N` where N is the heading order. This sacrifices round-5's "unchanged finding keeps the same id when a heading is added above it" guarantee for any same-titled findings — but only for those, not for distinct headings. Choosing between "hard-fail on dup heading" and "soft-disambiguate by position" is a judgment call; either preserves the round-5 fix.
- `parse_codex_review.py` ids are 10-hex-char prefixes of sha256. At 30+ findings per round the birthday probability is still negligible (~1e-9), so cross-finding collisions on different titles are not a real risk; the only collision class is the one finding #2 names.

## Summary

The round-5 triage closed all three round-5 findings cleanly with new tests (30 total, was 26). Goal-update rows now survive `--force`, content-hash ids prevent the round-5 P2 ledger inflation, and `append_goal_update.py` enforces the goal-status enum.

Three issues remain — one P1, one P2, one P3:

1. **P1 (unfixed)** `validate_review_gate.py` does not check that `plan.lock.md`'s recorded `plan_sha256` matches the current `docs/plan.md`. After `--force --overwrite-human-docs` (or any post-lock plan edit), the lock is stale and the gate still passes; the review packet's plan excerpt diverges from what Claude implements. Verified by reproducer.
2. **P2 (new)** Round-5's content-hash id collides when two findings share severity+title within a round; `--allow-overwrite` (which the error message recommends) silently merges them and drops one finding's `file`/`suggested_fix`. Verified by reproducer.
3. **P3 (unfixed)** `RESOLVED_STATUSES` alias in `_rlinfra.py:27-28` has no callers and is dead code.

Recommend fixing finding #1 — it is the only remaining gate-integrity gap, and the lock already records the hash needed to fix it. Finding #2 should be tightened to either fail-on-dup-heading or position-disambiguate the digest. Finding #3 is a one-line cleanup.

The repository's RLCR loop, schema/provenance contracts, ledger preservation, and re-render guarantees are otherwise solid; six rounds in, the system is materially production-ready.
