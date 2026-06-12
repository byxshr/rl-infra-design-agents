# Code Review — Round 4 — rl-infra-design-agents

- Date: 2026-06-12
- Scope: triaged fixes from `docs/code-review-2026-06-12-round-3.md` plus surrounding code
- Reference: `docs/ai-agent-code-review-reference.md` §"Review Triage Notes"
- Reviewer posture: independent gatekeeper

## Validation Run

| Command | Result |
|---|---|
| `python .agents/skills/RLInfraWiki/scripts/validate.py` | PASS — `RLInfraWiki validation passed` |
| `python .agents/skills/RLInfraWiki/scripts/generate_indices.py --check` | PASS — `generated query indices are current` |
| `pytest -q` | PASS — 23 passed (was 18) |
| Three consecutive `render_task_bundle.py … --force` runs against unchanged contract | PASS — 1 row in `goal_versions.jsonl`, 1 line in `progress_log.md` (idempotent) |
| `--force` after editing `task_contract.yaml` | PASS — appends new `goal_versions` row + `progress_log` line with verb `contract amended -> workspace re-rendered` |
| `Draft202012Validator(wiki_page.schema.json)` against verified-page samples | PASS — schema correctly enforces `hardware\|context` and `log\|artifact_path` |

Baseline: 10 test files, 23 tests, all green.

## Round-3 Triage

| Round-3 finding | Status | Notes |
|---|---|---|
| P2 — `--force` re-render duplicates `goal_versions.jsonl` / `progress_log.md` | **FIXED** | `render_task_bundle.py:67-72` adds `last_contract_hash`; lines 198-213 only append when `contract_hash` differs and use a distinct `contract amended` verb. Test `test_render_task_bundle_records_contract_amendments_only` covers it. |
| P3 — `render_rlcr_context.py` "Changed Files Snapshot" includes prior rounds | **FIXED** | Lines 42-48 skip `review_rounds/round-*` entries that don't match current `round_id`. Test asserts prior packet is filtered. Bonus: waiver schema validation now happens at packet-render time (lines 30-40). |
| P3 — `append_review_round.py` dedupe drops legitimate status corrections | **FIXED** | Lines 26-27, 60-76 implement fail-on-conflict-with-`--allow-overwrite`. CLAUDE.md updated to document the contract. |
| P3 — Negative-path tests for new `--reset-ledgers` / `--overwrite-human-docs` flags | **FIXED** | `test_render_task_bundle_force_flag_guards` covers both negative paths plus the positive `--force --overwrite-human-docs` path. |
| Bonus — schema cache | **FIXED** | `_rlinfra.py:180-194` adds `@lru_cache` on `load_project_schema`; gate and packet rendering both go through `schema_validation_errors`. |

All four round-3 findings landed cleanly. The remaining issues are narrow corners or polish.

## New / Remaining Findings

### P2: `append_review_round.py` does not detect intra-ingestion duplicate issue ids — silently violates the CLAUDE.md "ingestion fails by default" contract

- File/path: `.agents/skills/RLInfraWiki/scripts/append_review_round.py:53-71`
- Evidence:
  ```python
  existing_by_id = {row.get("id"): idx for idx, row in enumerate(existing) if row.get("id")}
  ...
  for issue in issues:
      issue_id = issue.get("id")
      if issue_id in existing_by_id:
          ...
          continue
      new_issues.append(issue)
  ```
  `existing_by_id` is built once from the prior ledger and never updated as new rows are added in the loop. Two rows in the same `parsed_issues.jsonl` sharing an id both fail the `if issue_id in existing_by_id` test (False, since the id is new to the ledger) and both land in `new_issues`.
- Reproducer (verified):
  ```bash
  cat > parsed_issues.jsonl <<'EOF'
  {"id":"review-round-001-001-p1",...,"summary":"first",...}
  {"id":"review-round-001-001-p1",...,"summary":"second-DIFFERENT",...}
  EOF
  python3 append_review_round.py --workspace WS --round-dir review_rounds/round-001
  # → "appended 2 issue(s)" (rc=0)
  # → review_issues.jsonl now has two rows with the same id and different summaries
  ```
- Why it blocks: `CLAUDE.md` (line 43, just updated) states "If the same issue ID appears with changed severity, status, summary, file, suggested fix, or evidence, ingestion fails by default; rerun with `--allow-overwrite` only when intentionally replacing that round's issue row." This script is the sole writer of `review_issues.jsonl`; the contract is silently violated for hand-crafted or externally-emitted `parsed_issues.jsonl`. The gate then sees two `open` rows for the same id — fixing one (status → resolved) leaves the other still blocking; both also count toward `issue_count` in `loop_state.json`. Realistic-ness caveat: `parse_codex_review.py` itself mints positional ids (`{round}-{n:03d}-{sev}`) so it cannot organically produce duplicates; this is an external-input defense-in-depth gap, which is why P2 rather than P1.
- Suggested fix: track ids seen during the current ingestion loop (`incoming_seen: dict[str, dict] = {}`); on a second occurrence in the same call, treat exactly like an existing-id collision — compare significant fields, accept silently if identical, record a conflict otherwise. When `--allow-overwrite` is in effect, also update `existing_by_id` and `updated[]` after each replacement so subsequent same-round occurrences see the latest state.

### P3: `--allow-overwrite` replaces the whole row, silently dropping non-significant human-added fields

- File/path: `.agents/skills/RLInfraWiki/scripts/append_review_round.py:65-67`
- Evidence:
  ```python
  if args.allow_overwrite:
      updated[idx] = issue
      replaced += 1
  ```
  `issue` is the parser's row; any human-added keys not in `SIGNIFICANT_FIELDS` (e.g. `owner: alice`, `notes: ...`, custom `resolution` metadata) are wiped on replace. The conflict detector compares only `SIGNIFICANT_FIELDS`, but the replacement is total.
- Why it matters: not a gate-bypass, but the script is the documented path for re-ingesting corrected reviewer feedback. A human curating the ledger reasonably expects their non-conflicting annotations to survive the re-ingest. Currently they don't.
- Suggested fix: merge instead of replace — `updated[idx] = {**existing[idx], **issue}` so non-significant keys carry over and the parser's significant + provenance fields take precedence. Alternatively, document the destructive semantic in `--help` and `CLAUDE.md`, and have the script print a one-line diff of dropped keys per replaced row.

### P3: Empty `goal_versions.jsonl` is treated as "contract changed", producing a spurious `amended` log entry

- File/path: `.agents/skills/RLInfraWiki/scripts/render_task_bundle.py:67-72, 198-213`
- Evidence:
  ```python
  def last_contract_hash(path: Path) -> str | None:
      rows = load_jsonl(path)
      if not rows:
          return None
      ...
  contract_changed = not preserve_ledgers or not goal_versions_path.exists() or last_contract_hash(goal_versions_path) != contract_hash
  ```
  When `goal_versions.jsonl` exists but is empty (manual truncation, accidental sync, merge artifact), `last_contract_hash` returns `None`, `None != contract_hash` is `True`, and the rendering takes the `contract amended` path even though the contract is identical to the last real run.
- Why it matters: misleading audit history. Reproducer: truncate `goal_versions.jsonl` to zero bytes and re-render with `--force` → progress log records `contract amended -> workspace re-rendered` falsely. Edge case (requires explicit truncation), so P3.
- Suggested fix: distinguish "no prior history yet" from "prior history says different hash." If `last_contract_hash(...) is None`, write a fresh first row and use the bare `workspace rendered` progress verb (treating empty-ledger as a fresh workspace). Reserve the `contract amended` verb for the case where a prior hash existed and differed.

### P3: Review packet does not surface waiver state to the reviewer

- File/path: `.agents/skills/RLInfraWiki/scripts/render_rlcr_context.py:78-80`
- Evidence:
  ```python
  open_issues = [i for i in issues if issue_needs_review_attention(i, approved_waivers)]
  packet += "\n".join(f"- {i.get('severity')} {i.get('id')}: {i.get('summary')}" for i in open_issues) or "None"
  ```
  Waivers are loaded and validated, but `approved_waivers` is the only thing surfaced — and only implicitly via the filtered open-issues list. There is no `## Waivers` section listing waiver rows, statuses, requesters, or reasons.
- Why it matters: a reviewer reading the packet cannot tell apart (a) an issue that was approved-waived, (b) an issue with a pending (status: requested) waiver, and (c) an issue with no waiver at all but a status that excludes it from the open-issues list. CLAUDE.md guarantees `P1_waiver` requires the human architect; if the architect has not yet approved a P1-waiver request, that should be visible in the packet, not silently filtered to "None."
- Suggested fix: render a `## Waivers` section listing every row in `review_waivers.jsonl` with `id / issue_id / severity / status / approved_by / reason`. Optionally split open issues into `Open Issues` and `Waived (approved)` so the reviewer can see both sets without recomputing.

### P3: `metrics.csv` header drift is never detected under `preserve_ledgers`

- File/path: `.agents/skills/RLInfraWiki/scripts/render_task_bundle.py:214-218`
- Evidence:
  ```python
  metrics_path = output / "metrics.csv"
  if preserve_ledgers:
      write_if_missing(metrics_path, "timestamp,metric,value,unit,notes\n")
  else:
      write(metrics_path, "timestamp,metric,value,unit,notes\n")
  ```
  When the canonical header changes (column added/renamed/reordered), an existing workspace silently keeps the old header. Downstream tools that parse by header position misalign.
- Why it matters: theoretical until the header changes, then silently breaks readers. Trivial to detect.
- Suggested fix: under `preserve_ledgers`, read the first line and warn (or fail) if it does not match the expected header constant. Either auto-migrate when safe, or print a notice telling the user to clear/reset `metrics.csv`.

### P3: Test coverage gap for intra-ingestion duplicates and `--allow-overwrite` field preservation

- File/path: `.agents/skills/RLInfraWiki/tests/test_append_review_round.py`
- Evidence: `test_append_review_round_conflict_requires_explicit_overwrite` covers existing-ledger conflict only. No test writes two rows with the same id in a single `parsed_issues.jsonl`; no test seeds `owner`/`notes` onto an existing row before `--allow-overwrite`.
- Why it matters: reference §"Important P2 Checks" — "scripts without tests for success and failure paths." The intra-ingestion bug above shipped because the test suite never exercised it. Future refactors of `append_review_round.py` have no safety net for these contracts.
- Suggested fix: add two cases — (1) `parsed_issues.jsonl` with two rows sharing id; assert ingestion fails (or coalesces to one) without `--allow-overwrite`; (2) seed `owner` on an existing ledger row, then run `--allow-overwrite`; assert the field survives (or, if intentionally destructive, that the script reports it as dropped).

## Open Questions

- Is `--allow-overwrite` intended to be **destructive** (replace row wholesale; humans must re-add curation each round) or **merge** (preserve human-added context)? Both are defensible — picking explicitly is what's missing. The current code is destructive; CLAUDE.md does not say which.
- For finding #4 (waiver visibility): which artifact should reflect waiver state — the review packet (current question), `loop_state.json`, or a dedicated `docs/waivers.md`? A short snippet in the packet is the lightest fix.
- Should `validate.py` (project-level) also schema-validate `examples/expected_workspaces/**` if/when those are populated? Currently empty, but the pattern of "validate on disk, not just at gate time" would generalize there.

## Summary

The round-3 triage fully closed the four findings raised in `code-review-2026-06-12-round-3.md`. `--force` is now idempotent for unchanged contracts, prior-round packets are filtered out of new packets, append-round conflicts fail loudly unless `--allow-overwrite` is explicit, the destructive flag interlocks are tested, and schema loads are cached. Test count grew 18 → 23.

Six issues remain — one P2, five P3, none gate-bypassing on their own:

1. **P2 (new)** Intra-ingestion duplicate ids in a single `parsed_issues.jsonl` bypass the conflict detector. The CLAUDE.md "ingestion fails by default" contract is silently violated for hand-crafted or externally-emitted parsed files. Verified by reproducer.
2. **P3 (new)** `--allow-overwrite` wipes non-significant human-added fields (`owner`, `notes`, etc.) on replace; the conflict detector compares only `SIGNIFICANT_FIELDS` but the replacement is total.
3. **P3 (new)** Empty `goal_versions.jsonl` is treated as "contract changed," producing a spurious `amended` log entry.
4. **P3 (unfixed)** Review packet has no `## Waivers` section; pending/rejected waivers are invisible to the reviewer.
5. **P3 (unfixed)** `metrics.csv` header drift is never detected under `preserve_ledgers`.
6. **P3 (unfixed)** Test gap covering finding #1 (intra-ingestion duplicates) and finding #2 (field preservation).

Recommend addressing #1 since it directly contradicts a freshly-documented CLAUDE.md contract; the rest are polish or defense-in-depth. The repository's gate-integrity, schema, provenance, and re-render guarantees are now solid — workflow integrity has stabilized.
