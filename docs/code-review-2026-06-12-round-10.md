# Code Review — Round 10 — rl-infra-design-agents

- Date: 2026-06-12
- Scope: triaged fix from `docs/code-review-2026-06-12-round-9.md`
- Reference: `docs/ai-agent-code-review-reference.md` §"Review Triage Notes"
- Reviewer posture: independent gatekeeper

## Validation Run

| Command | Result |
|---|---|
| `python .agents/skills/RLInfraWiki/scripts/validate.py` | PASS |
| `python .agents/skills/RLInfraWiki/scripts/generate_indices.py --check` | PASS |
| `pytest -q` | PASS — 35 passed (was 34) |
| Amend contract → bare `--force` re-render | `WARN: contract changed; scaffolded docs under docs/ were preserved and may be stale.` |
| Amend contract → bare `--force` → `lock_plan.py` → `validate_review_gate.py` | `ERROR: validation_matrix.md missing validation command from task_contract.yaml: echo NEW-VALIDATION-CMD`, exit 1 |

Baseline: 11 test files, 35 tests, all green. Round-9 added a test for the warn-and-block path.

## Round-9 Triage

| Round-9 finding | Status | Notes |
|---|---|---|
| P1 — Contract amendment + bare `--force` + re-lock silently passes the gate with stale matrix | **FIXED** | Two-part fix landed: (1) `render_task_bundle.py` emits a stderr warning when `contract_changed and preserve_human_docs`, (2) `validate_review_gate.py:57-70` `validate_contract_validation_matrix` walks `contract.validation_commands` and errors on any command not appearing in `docs/validation_matrix.md`. Verified empirically. |

The round-9 fix landed cleanly. Auditing it surfaced one residual P2 — the new gate check uses a fragile substring match.

## New Findings

### P2 (new): `validate_contract_validation_matrix` uses a substring `command in matrix_text` check; commands that are prefixes of other commands silently pass even when their row is missing

- File/path: `.agents/skills/RLInfraWiki/scripts/validate_review_gate.py:67-70`
- Evidence:
  ```python
  matrix = matrix_path.read_text(encoding="utf-8")
  for command in contract.get("validation_commands", []) or []:
      if str(command) not in matrix:
          errors.append(f"validation_matrix.md missing validation command from task_contract.yaml: {command}")
  ```
  The check is `command in matrix` over the entire file text. If one contract command is a substring of another, the check silently passes for the prefix command even when its row is absent — because the prefix appears as a substring of any longer command's row.

- Reproducer (verified empirically):
  ```yaml
  # task_contract.yaml
  validation_commands:
    - pytest
    - pytest -k integration
  ```
  ```
  render → lock → matrix has 2 rows → gate passes ✓
  hand-edit matrix to REMOVE the `| pytest |` row, keep only `| pytest -k integration |`
  re-lock → gate runs:
    "pytest" in matrix_text → True (it's a substring of "pytest -k integration")
    "pytest -k integration" in matrix_text → True
    → "Review gate passed", exit 0
  ```
  The matrix is missing a row for the `pytest` contract command, but the gate accepts it.
- Why it blocks: this is precisely the failure mode round-9 was designed to prevent — *"Lets a candidate promote without required validation evidence"* (reference §"Blocking Review Checks"). The check's purpose is to catch matrix↔contract drift; substring matching defeats that purpose for any contract whose commands share prefixes. Realistic triggers:
  - `pytest` and `pytest -k …` (a smoke test plus a focused subset)
  - `npm test` and `npm test -- --watch`
  - `make test` and `make test-integration`
  - Any command split into a base and a flagged variant

  P2 (not P1) because it requires an architect to actively delete a matrix row or write a matrix where the prefix command never had its own row — but both are realistic during workspace cleanup.
- Suggested fix: replace the substring check with format-aware matching against the renderer's known wrapping. The renderer at `render_task_bundle.py:181` writes each command as `` | contract validation | `{cmd}` | `` — the command appears between backticks. Build a set of backtick-quoted commands found in the matrix and check exact membership:
  ```python
  import re
  found = set(re.findall(r"`([^`]+)`", matrix))
  for command in contract.get("validation_commands", []) or []:
      if str(command) not in found:
          errors.append(...)
  ```
  Add a regression test where the contract has `pytest` and `pytest -k integration`, the matrix has only the second row, and the gate fails with `validation_matrix.md missing validation command from task_contract.yaml: pytest`.

## Open Questions

- The substring-vs-format-aware question generalizes: the gate's matrix check assumes the renderer's exact wrapping (backticks). If a future contract carries a command containing backticks itself, the regex would split it. Acceptable today (no such command in the seed contracts), but worth a comment in the gate to anchor the contract.
- Round-9's matrix check covers `validation_commands` but not `promotion_criteria` — the reference §"Review Triage Notes" line 151 only mentions validation commands. Promotion criteria appear in `plan.md`'s "Promotion criteria" section but no gate check verifies they are present after a contract amendment. Probably fine as-is (promotion criteria are softer; reviewers check them by reading the packet) — flag as an open question, not a finding.
- This is round 10. The residual surface is now genuinely thin. Recommend the team either close the review series after fixing this finding, or run one final retrospective sweep to confirm nothing else is hiding.

## Summary

The round-9 fix landed cleanly: bare `--force` now warns when the contract changed and docs are preserved; the gate now refuses promotion when the validation matrix is missing a contract command. Test count grew 34 → 35.

One residual P2:

- **P2 (new)** `validate_contract_validation_matrix` checks `command in matrix_text` as a substring match. When one contract command is a prefix of another (e.g., `pytest` and `pytest -k integration`), the gate silently passes a matrix that is missing the prefix command's row — because the prefix appears as a substring of the longer command. Verified by reproducer: hand-edited matrix with only the long-form row → gate passes despite the contract listing both. Fix: parse backtick-wrapped commands from the matrix and use exact set membership.

After this fix, ten rounds in, the residual surface is essentially closed. Recommend declaring the review series complete after the round-10 triage.
