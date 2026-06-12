# Code Review — Round 7 — rl-infra-design-agents

- Date: 2026-06-12
- Scope: triaged fixes from `docs/code-review-2026-06-12-round-6.md` plus end-to-end RLCR flow
- Reference: `docs/ai-agent-code-review-reference.md` §"Review Triage Notes"
- Reviewer posture: independent gatekeeper

## Validation Run

| Command | Result |
|---|---|
| `python .agents/skills/RLInfraWiki/scripts/validate.py` | PASS |
| `python .agents/skills/RLInfraWiki/scripts/generate_indices.py --check` | PASS |
| `pytest -q` | PASS — 32 passed (was 30) |
| `lock_plan.py` then overwrite `docs/plan.md` → `validate_review_gate.py` | PASS — gate fails with `plan.lock.md plan_sha256 does not match docs/plan.md` |
| Same for `docs/goal.md` drift | PASS — gate fails with `goal_sha256 does not match` |
| `parse_codex_review.py` on a packet with two `### P1: missing validation` blocks | PASS — `ERROR: duplicate review finding heading in round-001: P1: missing validation; differentiate the headings`, exit 1 |
| `from _rlinfra import RESOLVED_STATUSES` | PASS — symbol removed; no callers in `scripts/` or `tests/` |

Baseline: 11 test files, 32 tests, all green. Round-6 added regression tests (`test_review_gate_rejects_stale_plan_lock`, `test_parser_rejects_duplicate_severity_title_in_same_round`).

## Round-6 Triage

| Round-6 finding | Status | Notes |
|---|---|---|
| P1 — Gate doesn't detect drift between `plan.lock.md` and current files | **FIXED** | `validate_review_gate.py:18-52` adds `LOCKED_HASHES`, `plan_lock_hashes()`, `validate_plan_lock()`. Gate checks plan/goal/task-contract hashes; drift fails the gate. Test covers it. |
| P2 — Content-hash issue id collides on dup severity+title | **FIXED** | `parse_codex_review.py:22-33` fails at parse time with a clear "differentiate the headings" message. Test covers it. |
| P3 — Dead `RESOLVED_STATUSES` alias | **FIXED** | Removed from `_rlinfra.py`; no callers. |

All three round-6 findings closed cleanly. The new lock-drift detector, however, has a parser bug — finding #1 below.

## New / Remaining Findings

### P1 (new): `plan_lock_hashes()` reads beyond the lock header into the embedded plan body, allowing legitimate plan content to override the recorded hashes

- File/path: `.agents/skills/RLInfraWiki/scripts/validate_review_gate.py:25-35`
- Evidence:
  ```python
  def plan_lock_hashes(lock_path: Path) -> dict[str, str]:
      hashes = {}
      for line in lock_path.read_text(encoding="utf-8").splitlines():
          text = line.strip()
          if not text.startswith("- ") or ":" not in text:
              continue
          key, value = text[2:].split(":", 1)
          key = key.strip()
          if key in LOCKED_HASHES:
              hashes[key] = value.strip()
      return hashes
  ```
  `lock_plan.py:20-30` writes the lock as `header + "\n---\n\n" + plan.read_text()`. The header carries the canonical hash bullets; the body is the embedded `docs/plan.md`. The parser scans **every** line of the file, so any bullet in the plan body matching `- key: value` for one of `plan_sha256`/`task_contract_sha256`/`goal_sha256` overrides the legitimate header value. Because the parser keeps the **last** occurrence (no `break` at `---`), body bullets always win.
- Reproducer (verified empirically):
  ```bash
  render_task_bundle.py --contract slime-weight-sync.yaml --output WS
  cat >> WS/docs/plan.md <<'EOF'
  ## Plan Lock Documentation
  - plan_sha256: <hash of docs/plan.md>
  - task_contract_sha256: <hash of task_contract.yaml>
  - goal_sha256: <hash of docs/goal.md>
  EOF
  lock_plan.py --workspace WS                   # writes the lock fine
  validate_review_gate.py --workspace WS
  # → exit 1, three "does not match" errors
  lock_plan.py --workspace WS                   # re-locking does NOT recover
  validate_review_gate.py --workspace WS
  # → still exit 1, same three errors
  ```
  The operator is trapped: the body of the plan documents the lock format with placeholders (or example hashes), and every re-lock embeds the same body, so the gate is stuck on perpetual false drift.
- Why it blocks: Reference §"Blocking Review Checks" — "Weakens `validate_review_gate.py` so unresolved P0/P1 issues no longer block promotion" / "Causes `render_task_bundle.py`, `lock_plan.py`, or `render_rlcr_context.py` to produce incomplete RLCR workspaces." This is the inverse failure mode of round-6's fix: the gate now produces **false positives** for any plan that legitimately mentions the lock keys (workflow docs, plan templates, runbooks, the round-6 fix itself if its plan is checked in). A workspace cannot be promoted until the operator either (a) deletes the offending bullets from `docs/plan.md` or (b) figures out that the parser is at fault — neither is documented anywhere. Realistic trigger: any team documenting the round-6 fix, any plan template that explains the lock schema, any plan that quotes `lock_plan.py`'s output.
- Suggested fix: stop parsing at the `---` header/body boundary that `lock_plan.py` already writes. Concretely:
  ```python
  for line in lock_path.read_text(encoding="utf-8").splitlines():
      text = line.strip()
      if text == "---":
          break
      if not text.startswith("- ") or ":" not in text:
          continue
      ...
  ```
  Add a regression test that locks a plan whose body legitimately contains `- plan_sha256: ...` bullets and asserts the gate still passes. Bonus: have `lock_plan.py` write the hashes into a structured marker (e.g., a fenced YAML block) that the parser can locate unambiguously, so future format changes don't reintroduce the same class of bug.

## Open Questions

- The body-override bug is the only material residual at round 7. After it's fixed, the residual surface is quite small. Is there value in a final round 8, or is `make check` + manual inspection of `lock_plan.py` / `validate_review_gate.py` interaction sufficient?
- `parse_codex_review.py` still hashes only `severity|title`, so a reviewer who renames a heading mid-round creates an orphan in the ledger (old id stays as resolved/whatever, new id appears as fresh). Round-6 considered this a known limitation. Worth surfacing in CLAUDE.md as a constraint reviewers must respect, or accept silently?
- `validate_review_gate.py:62-63` still uses simple existence checks for `docs/goal.md`. With the lock now hash-checking `docs/goal.md`, the existence check at line 62 is redundant — but harmless. Cleanup polish only.

## Summary

The round-6 triage closed all three round-6 findings with new tests (32 total, was 30). Plan/goal/task-contract drift is detected and reported with precise file paths; duplicate same-round headings fail at parse time with a clear "differentiate the headings" message; the dead `RESOLVED_STATUSES` alias is gone.

One material issue remains:

- **P1 (new)** `plan_lock_hashes()` reads beyond the `---` separator into the embedded plan body, so any legitimate `- {plan|task_contract|goal}_sha256:` bullet in `docs/plan.md` (workflow docs, plan templates, runbooks describing the round-6 fix itself) silently overrides the recorded header hash. The gate then reports false drift, and re-running `lock_plan.py` cannot recover because the offending bullets remain in the embedded plan body. Verified by reproducer.

Recommend a one-line fix (`if text == "---": break` in `plan_lock_hashes`) plus a regression test. After that, the system has a clean six-round triage record and the residual surface is essentially polish (parse-id orphan on heading rename, redundant existence check) — neither of which materially affects workflow integrity.

The repository's RLCR loop is otherwise solid through seven rounds of review.
