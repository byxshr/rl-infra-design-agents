# Code Review — Round 3 — rl-infra-design-agents

- Date: 2026-06-12
- Scope: triaged fixes from `docs/code-review-2026-06-12-round-2.md` plus surrounding code
- Reference: `docs/ai-agent-code-review-reference.md` (incl. updated §"Second-Round Review Notes" describing what fixes the team made)
- Reviewer posture: independent gatekeeper

## Validation Run

| Command | Result |
|---|---|
| `python .agents/skills/RLInfraWiki/scripts/validate.py` | PASS — `RLInfraWiki validation passed` |
| `python .agents/skills/RLInfraWiki/scripts/generate_indices.py --check` | PASS — `generated query indices are current` |
| `pytest -q` | PASS — 18 passed (was 13) |
| `render_task_bundle.py` (1st run) | PASS |
| `render_task_bundle.py` (2nd run, no `--force`) | PASS — refuses with planned-writes list, exits 1 |
| `render_task_bundle.py --force` after writing a P0 row into `review_issues.jsonl` | PASS — review_issues.jsonl preserved verbatim |
| `render_task_bundle.py --force --reset-ledgers` | PASS — ledgers wiped as advertised |
| `Draft202012Validator(wiki_page.schema.json)` against verified-page samples | PASS — 1 error when `hardware|context` missing, 2 when both pairs missing |

Baseline: 10 test files (was 9), 18 tests, all green.

## Round-2 Triage

| Round-2 finding | Status | Notes |
|---|---|---|
| P2 — `wiki_page.schema.json` duplicate `anyOf` keys (regression) | **FIXED** | Schema rewritten as `allOf: [{anyOf: hardware\|context}, {anyOf: log\|artifact_path}]` (lines 164-193). Verified at runtime. New test `test_verified_wiki_schema_requires_context_and_artifact_evidence` covers it. |
| P2 — `validate.py` does not schema-validate `review_issues.jsonl` / `review_waivers.jsonl` rows | **FIXED** | `validate_review_gate.py:31-39` now calls `schema_validation_errors` against each row before applying severity/status logic. Tests `test_review_gate_schema_validates_issue_rows` and `test_review_gate_schema_validates_waivers_before_honoring` cover both. |
| P2 — `render_task_bundle.py --force` is all-or-nothing | **FIXED** | Split into `--force` (refresh scaffold, preserve ledgers + human docs), `--reset-ledgers` (requires `--force`), `--overwrite-human-docs` (requires `--force`). Empirically verified: a P0 row written into `review_issues.jsonl` survives `--force`. |
| P2 — `append_review_round.py` blindly appends parsed issues | **FIXED** | Now schema-validates each row, normalizes severity/status, and dedupes by `id`. (Caveat: dedupe-by-id-only — see finding #4 below.) |
| P3 — `append_review_round.py` overwrites `loop_state.json` wholesale | **FIXED** | Now `state = load_state(); state.update({...})` (lines 47-52). Existing fields are preserved. |

All five round-2 findings have material fixes. The remaining issues are new or are narrow corners of the round-2 fixes.

## New / Remaining Findings

### P2: `render_task_bundle.py --force` appends a duplicate `goal_versions.jsonl` row and `progress_log.md` line on every re-render, even when the contract is unchanged

- File/path: `.agents/skills/RLInfraWiki/scripts/render_task_bundle.py:186-197`
- Evidence:
  ```python
  goal_version = {"goal_id": ..., "contract_hash": sha256_file(contract_path), "created_at": now_iso()}
  goal_versions_path = output / "goal_versions.jsonl"
  if preserve_ledgers and goal_versions_path.exists():
      append_jsonl(goal_versions_path, [goal_version])
  ...
  if preserve_ledgers and progress_path.exists():
      append_text(progress_path, progress_entry)
  ```
  Verified empirically — two consecutive `render_task_bundle.py … --force` runs against an unchanged contract produced:
  ```
  goal_versions.jsonl (after 2 renders):
    {"goal_id":"slime-weight-sync","contract_hash":"d7b430e5...","created_at":"2026-06-12T10:10:25+00:00"}
    {"goal_id":"slime-weight-sync","contract_hash":"d7b430e5...","created_at":"2026-06-12T10:10:25+00:00"}
  progress_log.md (after 2 renders):
    - 2026-06-12T10:10:25+00:00: workspace rendered from `slime-weight-sync.yaml`.
    - 2026-06-12T10:10:25+00:00: workspace rendered from `slime-weight-sync.yaml`.
  ```
  Same `contract_hash`, identical `created_at` (rendered within the same second), no semantic difference.
- Why it blocks: The round-2 fix promised `--force` would be "safer for ledger-bearing workspaces." It is now safer for review-issue ledgers, but it converts `goal_versions.jsonl` into a noise-on-every-render log instead of an amendment ledger. Consumers asking "how many times has the goal been amended?" or `append_goal_update.py` callers that interleave real status records get the wrong answer. Reference §"Blocking Review Checks" — "Silently changes objective, acceptance criteria, non-goals, or review gate behavior" — applies obliquely: it does not alter the goal *content*, but it pollutes the very ledger that records goal changes.
- Suggested fix: Only append to `goal_versions.jsonl` when the new `contract_hash` differs from the last row's `contract_hash` (load the file, take the last row, compare). Apply the same guard to `progress_log.md`, or change the verb to disambiguate (e.g. `workspace re-rendered (no contract change)` vs `contract amended → workspace re-rendered`). Add a regression test in `tests/test_render_task_bundle.py` that runs `--force` twice against an unchanged contract and asserts `goal_versions.jsonl` still has exactly one row.

### P3: `render_rlcr_context.py` "Changed Files Snapshot" includes prior rounds' review packets

- File/path: `.agents/skills/RLInfraWiki/scripts/render_rlcr_context.py:32-34`
- Evidence:
  ```python
  for path in sorted(ws.rglob("*")):
      if path.is_file() and path.relative_to(ws).parts[0] not in {"runs", "profile"}:
          changed_files.append(path.relative_to(ws).as_posix())
  ```
  Only `runs/` and `profile/` are filtered. With multiple review rounds, `review_rounds/round-001/review_packet.md` (and any later parsed_issues.jsonl) leaks into round-002's "Changed Files Snapshot," and round-003's packet lists both prior rounds. The `[:200]` truncation can also push real signal off the list when many rounds accumulate.
- Why it matters: not a gate-bypass, but the reviewer is asked to assess a diff that explicitly includes the previous packet they wrote — purely self-referential noise that hurts review quality.
- Suggested fix: extend the skip set to ignore `review_rounds/round-*` entries that are not the current round. For example:
  ```python
  parts = path.relative_to(ws).parts
  if path.is_file() and parts[0] not in {"runs", "profile"} and not (
      parts[0] == "review_rounds" and len(parts) > 1 and parts[1] != round_id
  ):
      changed_files.append(...)
  ```

### P3: `append_review_round.py` dedupe by `id` alone silently drops legitimate status corrections

- File/path: `.agents/skills/RLInfraWiki/scripts/append_review_round.py:39-43`
- Evidence:
  ```python
  existing = load_jsonl(ws / "review_issues.jsonl")
  seen_ids = {row.get("id") for row in existing if row.get("id")}
  new_issues = [issue for issue in issues if issue.get("id") not in seen_ids]
  ```
  Comparison is by `id` only. `parse_codex_review.py` mints deterministic ids per round (`review-{round}-{n:03d}-{sev}`), so the same id reappears if a reviewer corrects a `codex_review.md` and the operator re-runs `parse_codex_review.py` + `append_review_round.py` for the same round.
- Why it matters: workflow path — (1) builder marks issue `resolved` in `review_issues.jsonl`; (2) reviewer notices the fix was incomplete and updates the same round's `codex_review.md`; (3) operator re-ingests. The deterministic id `review-round-001-001-p1` re-appears with status `open` in `parsed_issues.jsonl`, but this script silently drops it as a duplicate. The gate continues to treat the issue as resolved. In normal forward-only usage this is unlikely; with deterministic ids per round, it's a real corner.
- Suggested fix: when dedupe matches, compare the existing row's `status`/`severity`/`summary` to the incoming row. If any differ, either (a) print a WARN listing each conflict and exit 1 unless `--allow-overwrite` is passed, or (b) rewrite `review_issues.jsonl` with the incoming row replacing the matched-id row in place (preserving order). Document the chosen semantic in `CLAUDE.md`.

### P3: New negative-path guards in `render_task_bundle.py` are not test-covered

- File/path: `.agents/skills/RLInfraWiki/scripts/render_task_bundle.py:219-224`; tests under `.agents/skills/RLInfraWiki/tests/test_render_task_bundle.py`
- Evidence:
  ```python
  if args.reset_ledgers and not args.force:
      print("ERROR: --reset-ledgers requires --force")
      return 1
  if args.overwrite_human_docs and not args.force:
      print("ERROR: --overwrite-human-docs requires --force")
      return 1
  ```
  No test invokes `--reset-ledgers` alone or `--overwrite-human-docs` alone. The success path (`--force --reset-ledgers` wipes a sentinel) is covered, but the guards themselves are never asserted.
- Why it matters: reference §"Important P2 Checks" — "scripts without tests for success and failure paths." If a future refactor drops the `not args.force` half of either guard or moves it after the destructive write, the regression lands green. Specifically, if line 219's guard is dropped, `--reset-ledgers` alone reaches `render_bundle(..., preserve_ledgers=existing_nonempty and not args.reset_ledgers)` → `False` → the `LEDGER_FILES` loop takes the destructive branch on line 185 and silently zeros ledgers in a non-empty workspace.
- Suggested fix: add two short tests — (a) `--reset-ledgers` without `--force` against a non-empty workspace returns 1, prints `ERROR: --reset-ledgers requires --force`, and leaves the sentinel intact; (b) the same for `--overwrite-human-docs`. Bonus: a positive test for `--force --overwrite-human-docs` re-rendering `docs/goal.md` to the contract-derived default while still preserving `review_issues.jsonl`.

## Open Questions

- For finding #1 (`goal_versions.jsonl` duplicate appends): should the file represent **every render attempt** (current behavior, useful as an audit log) or **every contract amendment** (probably what callers expect, since a separate `progress_log.md` already records the render event)? The two semantics are reasonable but should be picked explicitly.
- `render_rlcr_context.py:30` collects approved waivers and passes them to `issue_needs_review_attention`. The waivers themselves are not schema-validated at packet-render time (only at gate time). Worth folding the schema check into `render_rlcr_context.py` so a malformed waiver is surfaced before the reviewer sees the packet, instead of after?
- Schema is re-read from disk inside `validate_review_gate.py` for every issue/waiver row (`schema_validation_errors` calls `json.loads` per call). Performance is fine at current ledger sizes, but a per-run cache would be cleaner — and would future-proof against larger workspaces.

## Summary

The round-2 triage closed all five round-2 findings cleanly: the duplicate `anyOf` schema bug is gone, `review_issues.jsonl`/`review_waivers.jsonl` rows are now schema-validated at the gate, `--force` was split into preserve-by-default + explicit destructive flags, `append_review_round.py` schema-validates and dedupes, and `loop_state.json` is now read-modify-write. Test count grew 13 → 18.

Four issues remain, all P2/P3, none gate-bypassing on their own:

1. **P2 (new)** `render_task_bundle.py --force` appends duplicate rows to `goal_versions.jsonl` and `progress_log.md` even when the contract is unchanged — the only one of these worth fixing soon, because it pollutes a ledger that downstream consumers reason about.
2. **P3 (new)** `render_rlcr_context.py` "Changed Files Snapshot" includes prior rounds' review packets — review-quality noise.
3. **P3 (unfixed)** `append_review_round.py` dedupe-by-id silently drops legitimate status corrections in the rare re-ingest path.
4. **P3 (new)** New negative-path guards in `render_task_bundle.py` are uncovered by tests — risk that a future refactor regresses the destructive flag interlocks.

Recommend addressing #1; #2-#4 can be tracked as polish. The repository's gate-integrity guarantees and provenance/schema contracts are now solid.
