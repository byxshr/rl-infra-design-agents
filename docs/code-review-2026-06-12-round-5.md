# Code Review — Round 5 — rl-infra-design-agents

- Date: 2026-06-12
- Scope: triaged fixes from `docs/code-review-2026-06-12-round-4.md` plus end-to-end RLCR flow
- Reference: `docs/ai-agent-code-review-reference.md` §"Review Triage Notes"
- Reviewer posture: independent gatekeeper

## Validation Run

| Command | Result |
|---|---|
| `python .agents/skills/RLInfraWiki/scripts/validate.py` | PASS — `RLInfraWiki validation passed` |
| `python .agents/skills/RLInfraWiki/scripts/generate_indices.py --check` | PASS — `generated query indices are current` |
| `pytest -q` | PASS — 26 passed (was 23) |
| Intra-ingestion duplicate ids in `parsed_issues.jsonl` | PASS — `ERROR: duplicate review issue id(s) changed`, exit 1; with `--allow-overwrite` collapses to one row |
| `--allow-overwrite` with seeded `owner=alice` | PASS — `owner` survives the merge (`merge_issue` preserves non-significant keys) |
| Empty `goal_versions.jsonl` re-render | PASS — fresh row written, no `amended` log entry |
| `metrics.csv` header drift | PASS — `metrics.csv header mismatch`, exit 1 |
| `## Waivers` section | PASS — present in rendered review packet |

Baseline: 10 test files, 26 tests, all green.

## Round-4 Triage

| Round-4 finding | Status | Notes |
|---|---|---|
| P2 — Intra-ingestion duplicate ids bypass conflict detection | **FIXED** | `append_review_round.py:65` adds `pending_by_id`; conflicts detected within same ingestion. Test `test_append_review_round_detects_incoming_duplicate_conflicts` covers it. |
| P3 — `--allow-overwrite` wipes non-significant fields | **FIXED** | `append_review_round.py:30-33` `merge_issue` preserves existing keys; `test_append_review_round_conflict_requires_explicit_overwrite` asserts `owner=alice` survives. |
| P3 — Empty `goal_versions.jsonl` triggers spurious "amended" | **FIXED** | `render_task_bundle.py:216-220` treats `prior_contract_hash is None` as fresh history. `test_render_task_bundle_empty_goal_versions_is_fresh_history` covers it. |
| P3 — Review packet has no Waivers section | **FIXED** | `render_rlcr_context.py:82-89` adds `## Waivers` listing id/issue_id/severity/status/approved_by/reason. |
| P3 — `metrics.csv` header drift | **FIXED** | `validate_metrics_header` (`render_task_bundle.py:78-88`) raises `SystemExit` on mismatch; `test_render_task_bundle_detects_metrics_header_drift` covers it. |
| P3 — Test gap | **FIXED** | All five fixes have new tests (26 total, was 23). |

All round-4 findings landed cleanly. However, the new `last_contract_hash` heuristic and `prior_contract_hash is None ⇒ fresh history` rule introduced in rounds 3/4 didn't account for `append_goal_update.py`, which writes records to the same file under a different shape. That regression dominates this round.

## New / Remaining Findings

### P1 (regression): `render_task_bundle.py --force` silently truncates `goal_versions.jsonl` after `append_goal_update.py` has written a record

- File/path: `.agents/skills/RLInfraWiki/scripts/render_task_bundle.py:70-75, 215-221`
- Evidence:
  ```python
  def last_contract_hash(path: Path) -> str | None:
      rows = load_jsonl(path)
      if not rows:
          return None
      value = rows[-1].get("contract_hash")
      return str(value) if value else None
  ...
  prior_contract_hash = last_contract_hash(goal_versions_path) if goal_versions_path.exists() else None
  contract_changed = prior_contract_hash is not None and prior_contract_hash != contract_hash
  if preserve_ledgers and contract_changed:
      append_jsonl(goal_versions_path, [goal_version])
  elif not preserve_ledgers or not goal_versions_path.exists() or prior_contract_hash is None:
      write(goal_versions_path, json.dumps(goal_version) + "\n")
  ```
  `append_goal_update.py:18-20` writes records of shape `{timestamp, status, reason, approved_by}` — these rows have **no `contract_hash` field**. When that record is the last row, `last_contract_hash` returns `None`. The render then takes the `prior_contract_hash is None` branch → `write()` (not `append_jsonl()`) → **the entire file is overwritten with a single fresh row, deleting the goal-update record and the original contract row.**

- Reproducer (verified empirically):
  ```bash
  python3 render_task_bundle.py --contract slime-weight-sync.yaml --output WS
  cat WS/goal_versions.jsonl                       # 1 row (contract)
  python3 append_goal_update.py --workspace WS \
      --status needs-amendment --reason test --approved-by human
  cat WS/goal_versions.jsonl                       # 2 rows (contract + needs-amendment)
  python3 render_task_bundle.py --contract slime-weight-sync.yaml --output WS --force
  cat WS/goal_versions.jsonl                       # 1 row — needs-amendment record GONE
  ```
- Why it blocks: Reference §"Blocking Review Checks" lists "Silently changes objective, acceptance criteria, non-goals, or review gate behavior" and "Causes `render_task_bundle.py`, `lock_plan.py`, or `render_rlcr_context.py` to produce incomplete RLCR workspaces." A human-architect–approved goal amendment (the entire reason `append_goal_update.py` exists) is silently erased on the next `--force` re-render. The gate keeps reporting "active" because the canonical goal_status.md is also re-stamped, but the audit trail of the amendment is gone. This is a regression introduced by the round-3/4 idempotency work, which only considered render-vs-render rows and did not account for a pre-existing schema-distinct row type living in the same JSONL.
- Suggested fix: Make `last_contract_hash` ignore rows that don't carry a `contract_hash` — iterate from the end backwards and return the first row that has the field. Then preserve the file when there are non-contract rows present:
  ```python
  def last_contract_hash(path: Path) -> str | None:
      for row in reversed(load_jsonl(path)):
          ch = row.get("contract_hash")
          if ch:
              return str(ch)
      return None
  ```
  Additionally, when `prior_contract_hash is None` AND the file is **non-empty**, append a fresh contract row instead of overwriting (the file holds at least one goal-update record worth keeping). Add a regression test that runs `append_goal_update.py` between two renders and asserts both rows survive.

### P2: `parse_codex_review.py` mints positional ids; re-parsing the same round after editing the markdown shifts every id and orphans prior ledger rows

- File/path: `.agents/skills/RLInfraWiki/scripts/parse_codex_review.py:24`
- Evidence:
  ```python
  "id": f"review-{round_id}-{len(issues)+1:03d}-{severity.lower()}",
  ```
  ID is determined by heading order. Adding/removing/reordering a heading and re-parsing assigns the SAME ids to DIFFERENT issues (and new ids to issues that previously held the old ids). `append_review_round.py` dedupes by id, so all the shifted ids become NEW rows while the old rows stay as orphans.

- Reproducer (verified empirically):
  ```
  Round-1 codex_review.md has [P1 missing validation, P2 minor doc nit]
   → ledger has 2 rows: review-round-001-001-p1, review-round-001-002-p2

  Reviewer prepends ### P0: critical regression to the same file, re-parse + re-ingest
   → parsed: [P0 critical, P1 missing validation, P2 minor doc nit]
            ids: 001-p0, 002-p1, 003-p2
   → append_review_round (with --allow-overwrite, none of these ids exist in ledger)
   → ledger now has 5 rows:
       review-round-001-001-p1  (orphan: original P1)
       review-round-001-002-p2  (orphan: original P2)
       review-round-001-001-p0  (new)
       review-round-001-002-p1  (NEW row for the same logical "missing validation")
       review-round-001-003-p2  (NEW row for the same logical "minor doc nit")
  ```
  Gate now reports 2 P1 blockers for one logical issue; resolving the issue requires fixing two ledger rows. Inflates the gate's blocker count at the moment a reviewer corrects their own packet.
- Why it matters: realistic trigger — any builder-driven re-parse after the reviewer edits `codex_review.md` (typo, clarification, added finding). Today's CLAUDE.md doesn't tell operators to delete the round's parsed_issues.jsonl + matching ledger rows before re-parsing; the silent ledger inflation will mislead reviewers and gate metrics.
- Suggested fix: make ids stable across re-parses of the same round by hashing content rather than position:
  ```python
  digest = hashlib.sha256(f"{severity}|{title}".encode()).hexdigest()[:10]
  "id": f"review-{round_id}-{digest}-{severity.lower()}",
  ```
  Or, in `append_review_round.py`, when ingesting into a `round_id` that already has rows in the ledger, treat each parse as authoritative for its round (delete-and-rewrite the `round_id` subset before merging in the new rows). Either approach should ship with a regression test that re-parses the same round after inserting a heading and asserts the ledger row count equals the markdown heading count.

### P3: `append_goal_update.py` has no schema validation, no status enum, and no parallel to the conflict/merge logic added to `append_review_round.py`

- File/path: `.agents/skills/RLInfraWiki/scripts/append_goal_update.py:10-21`
- Evidence:
  ```python
  parser.add_argument("--status", required=True)
  parser.add_argument("--reason", required=True)
  parser.add_argument("--approved-by", default="human-architect")
  ...
  record = {"timestamp": now_iso(), "status": args.status, "reason": args.reason, "approved_by": args.approved_by}
  with (ws / "goal_versions.jsonl").open("a", encoding="utf-8") as f:
      f.write(json.dumps(record) + "\n")
  ```
  Any string passed to `--status` is accepted, even though `validate_goal.py` uses a closed vocabulary (`active`, `completed`, `blocked`, `needs-amendment`). The script does not call `schema_validation_errors(record, "goal_update.schema.json", ...)` even though the schema exists. Combined with finding #1, `goal_versions.jsonl` is now a hybrid file where rows from `render_task_bundle` and `append_goal_update` have non-overlapping field sets — and the schema only matches the latter.
- Why it matters: a typo (`--status complete` instead of `completed`) is silently accepted; downstream readers/UI looking for the canonical enum see an unknown value. The schema exists but is unused — a latent inconsistency that's easy to fix.
- Suggested fix: restrict `--status` to a `choices=` enum matching `validate_goal.py`'s vocabulary; call `schema_validation_errors(record, "goal_update.schema.json", ...)` before write; tighten `goal_update.schema.json` to enumerate `status` and (optionally) set `additionalProperties: false`. At minimum, document in `CLAUDE.md` that `goal_versions.jsonl` carries two row types so reviewers don't treat one schema as the universal validator.

## Open Questions

- Should `goal_versions.jsonl` be split into `goal_contract_versions.jsonl` (contract hashes) and `goal_status_updates.jsonl` (architect status changes)? Each would conform to one schema and avoid the type-mixing that introduced finding #1. The cost is a docs/migration churn — but the upside is each file has a single schema.
- For finding #2: the simpler delete-and-rewrite per round is more robust to reviewer iteration; the content-hash id is more elegant for cross-round dedupe. Either is fine — the project should pick one and document.
- `lock_plan.py` is unaffected by `--overwrite-human-docs`: the lock is computed against the current `docs/plan.md`, so running `--force --overwrite-human-docs` and forgetting to re-run `lock_plan.py` leaves a `plan.lock.md` that no longer matches `docs/plan.md`. Today's `validate_review_gate.py` doesn't check that the lock matches the current `plan.md` — only that the lock file exists. Worth folding a sha256 comparison into the gate? (Not flagged because the operator is the gatekeeper here, but it's the same class of regression as finding #1.)

## Summary

The round-4 triage closed all five round-4 findings cleanly, with new tests for each. `--allow-overwrite` is now merge-preserving, intra-ingestion dups fail loudly, empty goal-versions are treated as fresh history, the review packet surfaces waivers, and metrics header drift fails fast. Test count grew 23 → 26.

Three issues remain — one **P1 regression**, one P2, one P3:

1. **P1 (regression)** `render_task_bundle.py --force` silently truncates `goal_versions.jsonl` after `append_goal_update.py` has written a record — the round-3/4 `last_contract_hash` heuristic ignores rows without a `contract_hash` field, so a goal-update record makes the render take the "fresh history" path and overwrite the file. Verified by reproducer; deletes architect-approved amendment audit history.
2. **P2 (unfixed)** `parse_codex_review.py` mints positional issue ids; re-parsing the same round after editing `codex_review.md` orphans prior ledger rows and inflates the gate's blocker count. Verified by reproducer.
3. **P3 (new)** `append_goal_update.py` does no schema validation and accepts any `--status` string; the `goal_update.schema.json` exists but is not enforced.

Recommend fixing finding #1 before any further round; it's the only regression and the only remaining gate-integrity gap. Findings #2 and #3 can be tracked as workflow polish.

The repository's gate-integrity, schema, provenance, and re-render guarantees are otherwise solid.
