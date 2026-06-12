# Code Review — Round 9 — rl-infra-design-agents

- Date: 2026-06-12
- Scope: triaged fix from `docs/code-review-2026-06-12-round-8.md` plus contract-amendment workflow audit
- Reference: `docs/ai-agent-code-review-reference.md` §"Review Triage Notes"
- Reviewer posture: independent gatekeeper

## Validation Run

| Command | Result |
|---|---|
| `python .agents/skills/RLInfraWiki/scripts/validate.py` | PASS |
| `python .agents/skills/RLInfraWiki/scripts/generate_indices.py --check` | PASS |
| `pytest -q` | PASS — 34 passed (was 33) |
| Substantive content in all 10 `docs/*.md` → `--force` (no `--overwrite-human-docs`) | PASS — all 10 preserved verbatim |
| Same → `--force --overwrite-human-docs` | PASS — all 10 re-rendered to scaffold templates |

Baseline: 11 test files, 34 tests, all green. Round-8 added `test_render_task_bundle_force_preserves_all_scaffolded_docs` (covers all 10 files).

## Round-8 Triage

| Round-8 finding | Status | Notes |
|---|---|---|
| P1 — `--force` overwrites `validation_matrix.md` / `risk_register.md` and 4 other docs | **FIXED** | `render_task_bundle.py:109-183` now routes all 10 `docs/*.md` files through `doc_writer`. Reference §"Suggested Review Commands" line 191 updated to reflect new semantics. Verified empirically. |

The round-8 fix landed cleanly. However, by switching contract-derived docs to "preserve by default," it introduced a new failure mode: **a contract amendment now leaves `docs/validation_matrix.md` and the contract-derived sections of `docs/plan.md` silently stale relative to `task_contract.yaml`, and the gate does not catch it.**

## New Findings

### P1 (new): Contract amendment + bare `--force` + re-lock silently passes the gate with stale `validation_matrix.md` and `plan.md` validation/promotion sections

- File/path: `.agents/skills/RLInfraWiki/scripts/render_task_bundle.py:101-237`; `.agents/skills/RLInfraWiki/scripts/validate_review_gate.py:18-22`
- Evidence (rendered scripts):
  ```python
  # render_task_bundle.py
  doc_writer = write_if_missing if preserve_human_docs else write
  doc_writer(output / "docs" / "plan.md", ...)              # preserved by default
  doc_writer(output / "docs" / "validation_matrix.md", ...) # preserved by default
  ```
  ```python
  # validate_review_gate.py
  LOCKED_HASHES = {
      "plan_sha256": "docs/plan.md",
      "task_contract_sha256": "task_contract.yaml",
      "goal_sha256": "docs/goal.md",
  }
  ```
  After round-8, `plan.md` and `validation_matrix.md` are preserved during bare `--force`. `validation_matrix.md` is **contract-derived** — its rows are generated from `contract.get("validation_commands", [])`. When the architect amends `task_contract.yaml` to add a new validation command and runs bare `--force`, the matrix retains its old rows. The gate (`validate_review_gate.py`) only hashes `plan.md`, `goal.md`, `task_contract.yaml` — it does not enforce contract↔matrix consistency.

- Reproducer (verified empirically):
  ```bash
  render_task_bundle.py --contract C.yaml --output WS    # 3 validation_commands → 3 matrix rows
  lock_plan.py --workspace WS                             # gate passes
  validate_review_gate.py --workspace WS                  # PASS

  # amend contract: add 'echo NEW-VALIDATION-CMD' to validation_commands
  render_task_bundle.py --contract C.yaml --output WS --force
  grep -c "contract validation" WS/docs/validation_matrix.md   # → 3 (still old count)
  grep -c "NEW-VALIDATION-CMD" WS/docs/{plan.md,validation_matrix.md}
  # → 0 (the new command is in task_contract.yaml only, not propagated to plan.md or matrix)

  lock_plan.py --workspace WS                             # re-lock against the preserved files
  validate_review_gate.py --workspace WS                  # → "Review gate passed", exit 0
  ```
  `render_rlcr_context.py:69-75` then excerpts the stale `validation_matrix.md` into the review packet, so Codex reviews against an incomplete matrix that does not list the new contract command.

- Why it blocks: Reference §"Blocking Review Checks" lists two triggers that apply:
  - **"Causes `render_task_bundle.py`, `lock_plan.py`, or `render_rlcr_context.py` to produce incomplete RLCR workspaces"** — the matrix is incomplete relative to the contract, and the workspace passes promotion in that state.
  - **"Lets a candidate promote without required validation evidence"** — the new validation command has no row in the matrix, no expected-result, no evidence path, no status. Nothing in the workflow forces an evidence row to exist for it before promotion.

  This is the inverse failure mode of the round-2 P0 #3 / round-8 P1 fixes. Round-2 stopped silently overwriting human edits; round-8 generalized that protection to all 10 docs. But contract-derived sections are now stuck on the architect's last `--overwrite-human-docs` decision: amend-then-bare-`--force` silently desyncs them. `goal_versions.jsonl` correctly records the amendment, but nothing surfaces the doc-vs-contract drift to the gate.

  This wasn't a bug before round-8 because `--force` always re-rendered `validation_matrix.md` from the contract. The round-8 fix solved one silent-data-loss path and opened a different one.

- Suggested fix (cheapest first):
  1. **WARN at render time** — when `contract_changed and preserve_human_docs`, emit a stderr warning in `render_bundle()`:
     ```
     WARN: contract changed; docs/plan.md (Validation commands, Promotion criteria) and
           docs/validation_matrix.md were preserved and may be stale. Re-run with
           --overwrite-human-docs (will reset evidence/status columns) or hand-edit those
           sections to reflect the new contract.
     ```
     This keeps the round-8 protection but makes the staleness visible to the operator.
  2. **Targeted refresh flag** — add `--refresh-contract-derived` that re-renders only the contract-driven sections of `plan.md` (Objective, Validation commands, Promotion criteria) and the matrix's command column, while preserving each row's evidence path / status fields. This is the most ergonomic answer but requires a structured-section approach to plan.md.
  3. **Gate enforcement** — extend `validate_review_gate.py` to verify that every entry in `task_contract.yaml.validation_commands` has a matching row in `validation_matrix.md` (the matrix's "validation command" column), and similarly that every `promotion_criteria` item appears in `plan.md`. This catches the staleness even when the architect doesn't notice the warning.

  The cheapest fix (#1) closes the silent-acceptance path with a one-line warning. The most thorough fix (#3) adds a contract↔matrix check to the gate.

  Add a regression test that amends the contract, runs `--force` (no `--overwrite-human-docs`), runs `lock_plan.py`, and asserts either (a) the gate fails because the new command has no matrix row, or (b) `--force` printed the contract-drift warning to stderr.

## Open Questions

- Round-8's new contract is "human-edited docs are preserved by default; explicit `--overwrite-human-docs` re-renders." Is the architect expected to keep `validation_matrix.md` in sync with `task_contract.yaml` by hand after every amendment, or is `--overwrite-human-docs` the supported refresh path? CLAUDE.md does not say. Either answer is fine, but it should be documented — a reviewer landing on a stale matrix today has no signal that this is expected.
- `goal_status.md` is also contract-/render-derived (status + `updated_at` timestamp). After bare `--force`, the timestamp is stale. No script consumes it, so this is cosmetic — not flagged. But it's the same class of issue and may surprise a future reader.
- This is round 9 of an originally short scaffold review. The system is solid; if the team accepts the round-9 finding's WARN-at-render fix, the residual surface really does close. Worth declaring the review series complete after one more triage.

## Summary

The round-8 fix landed cleanly: all 10 `docs/*.md` files now route through `doc_writer`, are preserved on bare `--force`, and re-render only with explicit `--overwrite-human-docs`. Test coverage extended to all 10 files. The user-facing help text now matches behavior.

One residual P1 surfaced from auditing the contract-amendment workflow:

- **P1 (new)** Contract amendment followed by bare `--force` and `lock_plan.py` silently passes the gate with stale `docs/validation_matrix.md` and stale contract-derived sections of `docs/plan.md`. The round-8 fix's "preserve by default" rule, combined with the lock comparing only the preserved files, means a newly-added validation command has no row in the matrix, no evidence path, and no enforcement before promotion. Verified by reproducer: 3 commands → contract amendment to 4 → bare `--force` → re-lock → gate passes with `validation_matrix.md` still at 3 rows and the new command nowhere in `plan.md`.

Recommend the cheap fix first — a stderr warning in `render_bundle()` when `contract_changed and preserve_human_docs`. Optional follow-up: extend the gate to verify contract↔matrix consistency.

After this fix, my retrospective review found no other material gap. Eight rounds in, the codebase has stabilized to the point where remaining concerns are workflow tradeoffs rather than bugs.
