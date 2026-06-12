# Code Review — Round 2 — rl-infra-design-agents

- Date: 2026-06-12
- Scope: triaged fixes from `docs/code-review-2026-06-12.md` plus surrounding code
- Reference: `docs/ai-agent-code-review-reference.md` (incl. §"Second-Round Review Notes")
- Reviewer posture: independent gatekeeper

## Validation Run

| Command | Result |
|---|---|
| `python .agents/skills/RLInfraWiki/scripts/validate.py` | PASS — `RLInfraWiki validation passed` |
| `python .agents/skills/RLInfraWiki/scripts/generate_indices.py --check` | PASS — `generated query indices are current` |
| `pytest -q` | PASS — 13 passed (was 7) |
| `render_task_bundle.py` (1st run) | PASS |
| `render_task_bundle.py` (2nd run, no `--force`) | PASS — refuses with planned-writes list, exits 1 |
| `lock_plan.py` → `render_rlcr_context.py --round 1` → `validate_review_gate.py` | PASS, gate WARN for missing `codex_review.md` (expected) |

Baseline: 9 test files (was 7), 13 tests, all green.

## Round-1 Triage

| Round-1 finding | Status | Notes |
|---|---|---|
| P0 — gate accepts `waived`/`backlog` for P0/P1 | **FIXED** | `_rlinfra.py:22-25` splits `TERMINAL_STATUSES` from `DEFERRED_STATUSES`; gate (`validate_review_gate.py:33-40`) blocks all non-terminal P0/P1, blocks P2 unless `status==waived AND id in approved_waivers`, blocks P2 backlog. Verified with concrete inputs. |
| P0 — re-render truncates ledgers | **FIXED (with caveat)** | `render_task_bundle.py:175-180` refuses non-empty workspace without `--force`. Caveat: `--force` is still all-or-nothing — see new finding #3 below. |
| P0 — re-render overwrites human-edited docs | **FIXED (same caveat)** | Same `--force` guard. |
| P1 — `verified` accepts truthy `local_evidence` | **FIXED** | `validate.py:37-50` requires dict + `command/commit/result` + `hardware|context` + `log|artifact_path`. (Schema half also updated, but introduced finding #1.) |
| P1 — no runtime jsonschema validation | **PARTIALLY FIXED** | `validate.py` now validates wiki frontmatter, source manifests, and task contracts against their schemas. `review_issues.jsonl` / `review_waivers.jsonl` rows still not validated — see finding #2. |
| P1 — gate accepts unknown/mistyped severity | **FIXED** | `validate_review_gate.py:27-32` normalizes severity to upper case and status to lower case, fails closed on values outside the enum. Verified with `severity=null`, `severity="p1"`, `severity="P5"`, `status="weird"`. |
| P1 — `generate_indices.py --check` blind to orphans | **FIXED** | Now walks `QUERIES_DIR.glob('*.md')` and exits 1 on unexpected files (only `README.md` allowlisted). |
| P2 — `parse_codex_review.py` HEADING_RE matches narrative | **FIXED** | Regex tightened so the heading prefix is required. Plain `P1: ...` body lines no longer match; `## P1`, `### P1`, `#### P1` still match. |
| P2 — `task_contract.schema.json` vs `validate.py` mismatch | **FIXED** | Schema now requires the same five fields, including `required_wiki_queries`. |
| P2 — `review_issue.schema.json` lacks severity enum | **FIXED** | Schema declares enums for `severity` and `status`. |
| P2 — `slime.md` / `verl.md` cite frameworks without source IDs | **FIXED** | Both pages now list the cross-framework source IDs and matching `version_sensitive` IDs. |
| P2 — `render_rlcr_context.py` empty `plan_lock_sha256` | **FIXED** | `render_rlcr_context.py:24-25` raises `SystemExit` if `plan.lock.md` is missing. Review packet now also surfaces P1-waived and P2-backlog under "Previous Unresolved Issues" via `issue_needs_review_attention` (`_rlinfra.py:178-189`). |
| P2 — `build_candidate_ledger.py` dead branch | **FIXED** | Dead filename branch removed; script now writes a real summary artifact. |

All round-1 P0s and the major P1s are closed. The remaining P1 gap (review-issue schema validation) is downgraded because the gate's normalize-then-enum check now blocks the dominant failure mode.

## New / Remaining Findings

### P2: `schemas/wiki_page.schema.json` has duplicate `anyOf` keys — `hardware|context` constraint is silently lost (regression introduced by round-1 fix)

- File/path: `schemas/wiki_page.schema.json:164` and `schemas/wiki_page.schema.json:176`
- Evidence: the `then.properties.local_evidence` object declares two `anyOf` keys at the same level — one for `hardware|context` (lines 164-175) and one for `log|artifact_path` (lines 176-187). Python's `json.loads` (and per the JSON spec, RFC 8259 §4 "names within an object SHOULD be unique") keeps only the last occurrence. Confirmed at runtime:

  ```python
  >>> json.loads(open('schemas/wiki_page.schema.json').read())['allOf'][0]['then']['properties']['local_evidence']
  {'required': ['command','commit','result'],
   'anyOf': [{'required':['log']},{'required':['artifact_path']}]}
  ```

  The `hardware|context` `anyOf` is gone. A `Draft202012Validator(schema)` against a `verified` page with `local_evidence={command, commit, result, log}` (no `hardware`, no `context`) yields zero errors.
- Why it blocks: The round-1 fix recommendation was explicitly "push this constraint into `wiki_page.schema.json` so both the static schema and `validate.py` share one source of truth." `validate.py:47-48` compensates with its own Python check, so this repo's CI still catches the gap — but any external consumer that loads `wiki_page.schema.json` (IDE validators, third-party CI, downstream tooling) will accept a `verified` page with no hardware/context. Schema and runtime now disagree, which is exactly what the round-1 fix promised to prevent.
- Suggested fix: replace the two adjacent `anyOf` blocks with a single `allOf`:
  ```json
  "allOf": [
    {"anyOf": [{"required":["hardware"]},{"required":["context"]}]},
    {"anyOf": [{"required":["log"]},{"required":["artifact_path"]}]}
  ]
  ```
  Add a unit test that runs `Draft202012Validator(wiki_page.schema.json)` against a `verified` instance with `command/commit/result/log` but neither `hardware` nor `context`, and asserts `iter_errors` is non-empty.

### P2: `validate.py` still does not schema-validate `review_issues.jsonl` / `review_waivers.jsonl`

- File/path: `.agents/skills/RLInfraWiki/scripts/validate.py:131-146`
- Evidence: `main()` calls `validate_sources`, `validate_data`, `validate_wiki`, `validate_contracts`. There is no `validate_review_issues` or equivalent. The schemas `schemas/review_issue.schema.json` (now with severity/status enums) and `schemas/review_waiver.schema.json` are loaded in `validate_schemas()` but never instantiated as validators against any artifact.
- Why it blocks: round-1 P1 #5 was only partially closed. `validate_review_gate.py:27-32` defends the dominant failure mode (mistyped severity/status) by normalizing case and enforcing enums, but other required fields from `review_issue.schema.json` — `id`, `round_id`, `summary`, structurally-typed `evidence` — are never checked. A row missing `round_id` or with `evidence: "see notes"` (string instead of array) flows through the gate untouched. Same for `review_waiver.schema.json`: a waiver row with `status: approved` but no `expiry`/`justification` fields is silently honored.
- Suggested fix: in the rendered workspace, fold schema validation into `validate_review_gate.py` so each row of `review_issues.jsonl` and `review_waivers.jsonl` is run through `Draft202012Validator(schemas['review_issue.schema.json'])` and `…review_waiver.schema.json` before the severity/status branch — append schema errors to the same `errors` list. Alternatively, add a `validate_workspace_artifacts(workspace)` callable that the gate and `append_review_round.py` both invoke.

### P2: `render_task_bundle.py --force` still silently truncates ledgers and rewrites human-edited docs

- File/path: `.agents/skills/RLInfraWiki/scripts/render_task_bundle.py:157-159`
- Evidence:
  ```python
  for rel in [".humanize/codex_invocations.jsonl",
              ".humanize/claude_iterations.jsonl",
              "review_issues.jsonl",
              "review_waivers.jsonl",
              "candidates.jsonl"]:
      write(output / rel, "")
  write(output / "goal_versions.jsonl", json.dumps({...}) + "\n")
  ```
  With `--force`, every JSONL is re-zeroed and `goal_versions.jsonl` is replaced with a single bootstrap row. Same for `docs/goal.md`, `docs/plan.md`, `docs/draft.md`, `docs/validation_matrix.md`, `docs/risk_register.md`, `docs/goal_status.md`, `.humanize/rlcr_config.yaml`, `.humanize/loop_state.json`, `progress_log.md`, `metrics.csv`.
- Why it blocks: round-1 P0s #2/#3 collapsed both ledger-truncation and human-doc-overwrite into a single `--force` flag. The reference §"Suggested Review Commands" accepts that as adequate. But for a real multi-round task, the architect's natural reason to re-render is to refresh contract-derived docs (`validation_matrix.md`, `draft.md`) after a contract amendment — and there is no way to do that without also wiping `review_issues.jsonl` and `goal_versions.jsonl`. The first re-render with `--force` then makes the gate report "passed" because there are no issues left.
- Suggested fix: split `--force` into per-group flags, e.g. `--force-docs` (re-render contract-derived docs only), `--force-config` (re-stamp `.humanize/rlcr_config.yaml`), `--force-ledgers` (the destructive path, gated behind a separate `--i-understand-this-wipes-issues` confirmation). For human-editable files (`goal.md`, `plan.md`, `goal_versions.jsonl`), prefer "write only if missing" even under `--force`, and append a new row to `goal_versions.jsonl` instead of replacing the file. Print a diff of files that will be touched and require y/N confirmation when stdin is a tty.

### P2: `append_review_round.py` blindly appends parsed issues — no dedupe, no schema validation

- File/path: `.agents/skills/RLInfraWiki/scripts/append_review_round.py:19-20`
- Evidence:
  ```python
  issues = load_jsonl(rdir / "parsed_issues.jsonl")
  append_jsonl(ws / "review_issues.jsonl", issues)
  ```
  Issue ids generated by `parse_codex_review.py` are deterministic given the same `codex_review.md` (`review-{round}-{n}-{severity}`), so re-running ingestion appends a second copy of every issue with the same id.
- Why it blocks: `review_issues.jsonl` is the gate's single source of truth. If a reviewer re-uploads a corrected `codex_review.md` and ingestion is re-run (no command currently prevents that), the gate now sees two `open` rows per issue — when the builder later marks one `resolved`, the duplicate still blocks. Conversely, a malformed row (e.g. `severity: "critical"`) sneaks past `parse_codex_review` if a reviewer hand-edits `parsed_issues.jsonl`, and only fails (or worse, lands in the unknown-severity branch) much later in the gate. This is the obvious place to add the defense-in-depth that the round-1 reference notes acknowledged was missing.
- Suggested fix: before appending, validate each row against `schemas/review_issue.schema.json` via `jsonschema.Draft202012Validator`; normalize `severity` to upper case and `status` to lower case via `_rlinfra.VALID_SEVERITIES`/`VALID_ISSUE_STATUSES` (or fail closed). Read existing `review_issues.jsonl`, build a set of seen `id`s, and either skip or update-in-place duplicates instead of `append_jsonl`-ing.

### P3: `append_review_round.py` overwrites `loop_state.json` wholesale

- File/path: `.agents/skills/RLInfraWiki/scripts/append_review_round.py:23`
- Evidence:
  ```python
  state_path.write_text(json.dumps({"status":"review-ingested","round":rdir.name,"issue_count":len(issues),"updated_at":now_iso()}, indent=2)+"\n", ...)
  ```
  Discards any other fields previously written there (the `render_task_bundle` initial state, or future fields added by other scripts like `last_validation_at`).
- Why it matters: not a gate-bypass, but `loop_state.json` is the obvious place an orchestration layer would persist additional flags. Any future field added by another script is silently dropped on the next review ingestion.
- Suggested fix: read-modify-write — load the existing state (defaulting to `{}` if missing), merge the new fields, write back. Or store round transitions in an append-only `.humanize/loop_events.jsonl` and keep `loop_state.json` minimal and well-defined.

## Open Questions

- Should `review_issues.jsonl` row-level schema validation live in `validate.py` (project-level) or in `validate_review_gate.py` / `append_review_round.py` (workspace-level)? The schemas exist — the only question is which actor enforces them. A workspace-level call point is the most natural since the JSONLs only exist inside rendered workspaces.
- Is `--force` ever expected to be safe for ledger-bearing workspaces? If "no, always start clean," consider deleting the path and recreating instead of overwriting in place — that makes the destruction visible. If "yes, sometimes," the per-group flags from finding #3 are needed.
- Round-1 follow-up: the reference's §"Second-Round Review Notes" states that a body-text framework scanner was deferred to avoid false positives. That is a reasonable trade-off, but should `check_provenance.py` at least surface a low-severity *warning* listing framework tokens found in body text without matching frontmatter source IDs, leaving the human to triage? It would make the deferred guarantee observable instead of invisible.
- `parse_codex_review.py` discards review-packet sections like "Why it blocks" and "Failure scenario." Worth keeping verbatim under `evidence` to give the builder the reasoning, not only the title?

## Summary

The triage closed all three round-1 P0s and the load-bearing P1s. The gate now correctly fails closed on `waived`/`backlog` for P0/P1, on missing approved waivers for P2, and on unknown severity/status. Workspace re-render is guarded behind `--force`. `validate.py` runs real `jsonschema` validators against wiki, sources, and contracts. The `parse_codex_review` regex tightened, the orphan-index check landed, the `plan_lock_sha256` fail-fast landed, the cross-framework provenance gaps in `slime.md` / `verl.md` are filled, and the test count grew from 7 to 13.

Five issues remain or were introduced by the fixes — all P2/P3, none gate-bypassing on their own:

1. **P2 (regression)** `wiki_page.schema.json` has duplicate `anyOf` keys, so the JSON schema silently no longer enforces `hardware|context` for verified evidence even though the round-1 fix promised the schema would be the source of truth.
2. **P2 (unfixed)** `review_issues.jsonl` / `review_waivers.jsonl` rows are still not schema-validated; the gate's enum normalization closes the worst case but other schema constraints never run.
3. **P2 (partial)** `render_task_bundle.py --force` is all-or-nothing — it still wipes the entire RLCR ledger when used to refresh contract-derived docs.
4. **P2 (new)** `append_review_round.py` appends without dedupe or schema validation, so re-ingesting a round duplicates issues.
5. **P3 (new)** `append_review_round.py` overwrites `loop_state.json` wholesale.

Recommend addressing #1 and #2 promptly — they are the only ones that affect the schema-as-contract guarantees the project sets up. #3, #4, #5 can be tracked as follow-ups; none can bypass the gate without explicit operator action.
