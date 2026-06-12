# AI Agent Code Review Reference

This document is a compact briefing for AI agents reviewing changes in this repository.

## Repository Role

`rl-infra-design-agents` is a task-agnostic workflow, wiki, schema, and tooling repository for RL infrastructure design agents. It is not an RL framework and should not contain task implementations, model weights, datasets, benchmark dumps, private logs, or generated training outputs.

The default workflow is Humanize-compatible RLCR:

- Human Architect defines the task and approves goal amendments.
- Claude Builder implements or fixes one candidate batch at a time.
- Codex Reviewer independently reviews goal alignment, provenance, validation, and diff quality.
- CI and scripts validate schemas, wiki pages, generated indices, task bundles, and review gates.

## Review Posture

Review as an independent gatekeeper, not as a builder. In review mode, do not modify files. Report findings with severity, file/path, concrete evidence, why it matters, and suggested fix.

Prioritize correctness and workflow integrity over wording polish. A small documentation typo is less important than a broken provenance rule, invalid review gate, or task workspace that cannot be regenerated.

## Key Paths

| Path | Purpose |
|---|---|
| `AGENTS.md` | Root guidance for Codex, including review severity rules. |
| `CLAUDE.md` | Builder instructions for Claude in the RLCR loop. |
| `.agents/skills/RLInfraWiki/` | Canonical skill, wiki, data, scripts, tests, and source manifests. |
| `.agents/skills/RLInfraWiki/wiki/` | Seed RL infrastructure knowledge pages with YAML frontmatter. |
| `.agents/skills/RLInfraWiki/sources/` | Source manifests and source summaries. |
| `.agents/skills/RLInfraWiki/data/version_claims.yaml` | Version-sensitive claim registry. |
| `.agents/skills/RLInfraWiki/queries/` | Generated query indices. Do not hand-edit. |
| `.agents/skills/RLInfraWiki/scripts/` | Query, validation, workspace rendering, goal, and RLCR scripts. |
| `schemas/` | JSON schemas for contracts, goals, wiki pages, evidence, and review artifacts. |
| `examples/task_contracts/` | Example contracts used to generate task workspaces. |
| `integrations/humanize/` | Optional Humanize-compatible RLCR adapter prompts and config. |

## Blocking Review Checks

Flag P0 or P1 when a change:

- Silently changes objective, acceptance criteria, non-goals, or review gate behavior.
- Lets a candidate promote without required validation evidence.
- Marks an upstream claim as `verified` without local reproduction evidence.
- Breaks source IDs, version claim IDs, wiki frontmatter, schemas, or generated index checks.
- Manually edits generated query indices instead of regenerating them.
- Adds private data, model weights, datasets, benchmark logs, or task-specific implementation artifacts.
- Makes performance, scale, or production claims without source, context, confidence, and reproducibility metadata.
- Weakens `validate_review_gate.py` so unresolved P0/P1 issues no longer block promotion.
- Causes `render_task_bundle.py`, `lock_plan.py`, or `render_rlcr_context.py` to produce incomplete RLCR workspaces.

## Important P2 Checks

Flag P2 when a change:

- Adds wiki pages with thin summaries, missing risks, or vague source provenance.
- Adds scripts without tests for success and failure paths.
- Leaves task contracts without concrete validation commands or promotion criteria.
- Makes interface boundaries ambiguous between trainer, rollout backend, reward service, environment, or review system.
- Omits rollback, cache/version policy, or observability where the design topic requires it.
- Introduces duplicated schema logic or ad hoc parsing where existing helpers in `_rlinfra.py` should be reused.

## Usually P3

Use P3 for naming, style, grammar, or documentation polish that does not affect workflow correctness, validation, provenance, or review gate behavior.

## Provenance Rules

All upstream framework claims are `source-reported` unless there is local reproduction evidence. Local evidence must include command, commit, hardware/context, log or artifact path, and result.

Wiki pages must cite source IDs that exist under `.agents/skills/RLInfraWiki/sources/`. Version-sensitive claims must resolve through `.agents/skills/RLInfraWiki/data/version_claims.yaml`.

Do not accept pages that cite a framework in body text but omit the relevant source ID in frontmatter.

## Generated Artifacts

The query index files under `.agents/skills/RLInfraWiki/queries/` are generated. If wiki frontmatter changes, reviewers should expect:

```bash
python .agents/skills/RLInfraWiki/scripts/generate_indices.py
python .agents/skills/RLInfraWiki/scripts/generate_indices.py --check
```

Do not approve hand-written index changes that are not reproducible by the generator.

## Task Workspace Contract

`render_task_bundle.py` should generate a complete workspace containing:

- `task_contract.yaml`
- `docs/goal.md`
- `docs/draft.md`
- `docs/plan.md`
- `docs/architecture.md`
- `docs/interfaces.md`
- `docs/validation_matrix.md`
- `docs/risk_register.md`
- `docs/review.md`
- `docs/goal_status.md`
- `docs/codex_tasks.md`
- `.humanize/rlcr_config.yaml`
- `.humanize/loop_state.json`
- `.humanize/plan.lock.md` after `lock_plan.py`
- `review_rounds/`
- `evidence/`
- `goal_versions.jsonl`
- `progress_log.md`
- `candidates.jsonl`
- `metrics.csv`
- `review_issues.jsonl`
- `review_waivers.jsonl`

Review changes to workspace rendering carefully because this is the core end-to-end product of the repository.

## RLCR Review Gate

`validate_review_gate.py` should fail for unresolved P0/P1 review issues. P2 issues require a fix or approved waiver. P3 issues may remain non-blocking or be deferred to backlog.

Missing `codex_review.md` in a newly rendered scaffold can be a warning when review has not yet happened. It should become blocking only when a command or config explicitly requires completed review.

## Review Triage Notes

The first review findings in `docs/code-review-2026-06-12.md` have been triaged. The accepted fixes touched the review gate, workspace rendering, schema validation, query-index checks, review parsing, review-packet rendering, candidate summaries, selected provenance frontmatter, docs, and tests.

The second review findings in `docs/code-review-2026-06-12-round-2.md` have also been triaged. Accepted fixes added row-level review issue/waiver schema validation, append-round dedupe, safer loop-state updates, a corrected `verified` evidence schema, and safer `--force` behavior for ledger-bearing workspaces.

The third review findings in `docs/code-review-2026-06-12-round-3.md` have been triaged. Accepted fixes made no-change `--force` renders idempotent for `goal_versions.jsonl` and `progress_log.md`, filtered prior review rounds out of new review packets, made duplicate issue-id corrections fail unless `--allow-overwrite` is explicit, added negative-path tests for destructive render flags, and cache schema loads during review artifact validation.

The fourth review findings in `docs/code-review-2026-06-12-round-4.md` have been triaged. Accepted fixes added intra-ingestion duplicate issue-id detection, merge-preserving `--allow-overwrite`, fresh-history handling for empty `goal_versions.jsonl`, a `## Waivers` section in review packets, metrics header drift detection, and regression tests for those paths.

The fifth review findings in `docs/code-review-2026-06-12-round-5.md` have been triaged. Accepted fixes preserve architect goal-update rows during `--force` re-renders, use content-hash review issue IDs that stay stable when headings are inserted, and validate `append_goal_update.py` status values against the goal-update schema.

The sixth review findings in `docs/code-review-2026-06-12-round-6.md` have been triaged. Accepted fixes make `validate_review_gate.py` reject stale `plan.lock.md` hashes for plan, goal, and task contract files; make `parse_codex_review.py` fail on duplicate same-round severity+title headings; and remove the dead `RESOLVED_STATUSES` alias.

The seventh review finding in `docs/code-review-2026-06-12-round-7.md` has been triaged. The plan-lock parser now stops at the `---` header/body separator, so explanatory hash bullets embedded in `docs/plan.md` cannot override the recorded lock header.

The eighth review finding in `docs/code-review-2026-06-12-round-8.md` has been triaged. All scaffolded docs under `docs/` are now preserved during `--force`; `--force --overwrite-human-docs` is required to re-render those files from the contract.

The ninth review finding in `docs/code-review-2026-06-12-round-9.md` has been triaged. Contract changes under bare `--force` now emit a stale-docs warning, and `validate_review_gate.py` fails when `docs/validation_matrix.md` omits any command listed in `task_contract.yaml.validation_commands`.

The tenth review finding in `docs/code-review-2026-06-12-round-10.md` has been triaged. Validation matrix checks now parse backtick-wrapped command cells and require exact command membership, so prefix commands such as `pytest` are not satisfied by longer commands such as `pytest -k integration`.

The eleventh review finding in `docs/code-review-2026-06-12-round-11.md` has been triaged. `parse_codex_review.py` no longer emits parser-owned defaults such as `owner`, `created_at`, `resolved_at`, or `resolution`; `append_review_round.py` adds those defaults only for fresh issues, so `--allow-overwrite` preserves architect-curated fields.

The twelfth review finding in `docs/code-review-2026-06-12-round-12.md` has been triaged. `summarize_rlcr.py` now uses the same promotion-blocking helper as the review gate, so unwaived P2 issues and other gate-blocking states report `promotion_readiness: blocked`.

The thirteenth review finding in `docs/code-review-2026-06-12-round-13.md` has been triaged. Approved waiver loading is now shared and schema-aware, so `summarize_rlcr.py`, `validate_review_gate.py`, and `render_rlcr_context.py` only honor schema-valid `status=approved` waiver rows.

The fourteenth review in `docs/code-review-2026-06-12-round-14.md` found no new material issues. It re-verified the shared waiver loader across summary, gate, and review-packet rendering, and recommends declaring this review series complete unless new scope is introduced.

Later reviewers should especially re-check:

- P0/P1 issues cannot be bypassed with `waived` or `backlog`; P2 requires an approved waiver; unknown severity/status fails closed.
- `summarize_rlcr.py` should report `promotion_readiness: blocked` for the same issue states that would block `validate_review_gate.py`.
- `review_issues.jsonl` and `review_waivers.jsonl` rows are schema-validated before review gate promotion decisions; schema-invalid approved waivers must not unblock summary or gate readiness.
- `append_review_round.py` schema-validates parsed issues, normalizes severity/status, skips duplicate issue IDs, and preserves existing `loop_state.json` fields.
- Duplicate issue IDs with changed severity/status/summary/file/suggested fix/evidence fail ingestion unless `append_review_round.py --allow-overwrite` is explicit; overwrite should preserve non-conflicting human annotations.
- Parser defaults such as `owner` and `resolution` should not overwrite architect-curated ledger fields during same-round re-ingestion.
- Review issue IDs should be stable across re-parses of the same round when unchanged findings keep the same severity and title.
- Duplicate same-round review headings with the same severity and title should fail at parse time; reviewers must distinguish the headings before ingestion.
- Review heading text participates in issue identity; renaming a heading mid-round creates a new issue id and should be intentional.
- `render_task_bundle.py` refuses non-empty workspaces unless `--force` is explicit; `--force` preserves ledgers and scaffolded docs under `docs/` by default, while `--reset-ledgers` and `--overwrite-human-docs` are required for destructive resets.
- If the task contract changes while docs are preserved, render output should warn that contract-derived docs may be stale, and the review gate must verify every contract validation command appears exactly as a backtick-wrapped command in `docs/validation_matrix.md`.
- Unchanged `--force` renders should not append duplicate `goal_versions.jsonl` rows or duplicate progress log entries; contract hash changes should append one goal version record.
- Empty `goal_versions.jsonl` should be treated as fresh history, not as a contract amendment; `metrics.csv` header drift should fail rather than silently preserving incompatible columns.
- `goal_versions.jsonl` is a mixed ledger: contract-version rows carry `contract_hash`, while architect goal-update rows carry `timestamp/status/reason/approved_by`. Re-rendering must not delete either row type.
- `validate.py` validates actual source manifests, wiki frontmatter, and example task contracts against JSON schemas, not only schema syntax.
- `wiki_page.schema.json` enforces verified evidence with `command/commit/result`, `hardware|context`, and `log|artifact_path`.
- `parse_codex_review.py` only extracts issue headings such as `### P1: title`, and ignores narrative `P1: ...` lines.
- `generate_indices.py --check` detects both stale generated indices and unexpected orphan `.md` index files.
- `render_rlcr_context.py` fails when `.humanize/plan.lock.md` is missing, schema-validates waivers before honoring them, renders a `## Waivers` section, filters prior round artifacts from Changed Files Snapshot, and still surfaces disallowed deferred issues such as P1 waived.
- `validate_review_gate.py` must verify that `.humanize/plan.lock.md` header hashes still match `docs/plan.md`, `docs/goal.md`, and `task_contract.yaml`; stale locks should block promotion until `lock_plan.py` is rerun. The parser should stop at the lock file's `---` separator and ignore the embedded plan body.
- `system-slime` and `system-verl` include explicit source/version references for their named backends.

The broad suggestion to scan every body mention of a framework name was not implemented as a hard validator because it can produce false positives when a page cites an upstream source that itself describes integrations. Reviewers should still flag obvious provenance gaps manually.

## Suggested Review Commands

Use the project conda environment if available:

```bash
conda run -n rl-infra-design-agents make check
```

Core commands:

```bash
python .agents/skills/RLInfraWiki/scripts/validate.py
python .agents/skills/RLInfraWiki/scripts/generate_indices.py --check
python .agents/skills/RLInfraWiki/scripts/repo_status.py
python .agents/skills/RLInfraWiki/scripts/query.py "async rollout agentic RL SGLang" --limit 8
python .agents/skills/RLInfraWiki/scripts/get_page.py comparisons-rl-frameworks --follow-sources
python .agents/skills/RLInfraWiki/scripts/render_task_bundle.py \
  --contract examples/task_contracts/slime-weight-sync.yaml \
  --output /tmp/rl-infra-task-workspace
python .agents/skills/RLInfraWiki/scripts/lock_plan.py \
  --workspace /tmp/rl-infra-task-workspace
python .agents/skills/RLInfraWiki/scripts/render_rlcr_context.py \
  --workspace /tmp/rl-infra-task-workspace \
  --round 1
python .agents/skills/RLInfraWiki/scripts/validate_review_gate.py \
  --workspace /tmp/rl-infra-task-workspace
pytest -q
```

`render_task_bundle.py` must refuse non-empty workspaces unless `--force` is explicit. Under `--force`, review ledgers, `goal_versions.jsonl`, progress/metrics, loop state, and scaffolded docs under `docs/` are preserved by default. Reviewers should treat accidental ledger/doc truncation as a blocker; destructive ledger reset must require `--reset-ledgers`, and doc regeneration must require `--overwrite-human-docs`.

## Current Expected Baseline

At the initial scaffold baseline, reviewers should expect roughly:

- 33 seed wiki pages.
- 12 source manifests.
- 7 version claim records.
- 9 generated query indices.
- 23 Python scripts under `.agents/skills/RLInfraWiki/scripts/`.
- 12 pytest test files, currently 40 tests.

Counts may grow over time, but a sudden drop usually deserves review scrutiny.

## Common False Positives

- A scaffolded review round may not have `codex_review.md` yet. Treat this as expected unless the workflow claims a completed review.
- `skills/RLInfraWiki` is a compatibility symlink to `.agents/skills/RLInfraWiki`, not a second source of truth.
- Source-reported framework capabilities are allowed when cited; they should not be upgraded to verified without evidence.

## Good Review Output Shape

```markdown
## Findings

### P1: <short title>

- File/path:
- Evidence:
- Why it blocks:
- Suggested fix:

## Open Questions

## Validation Run

## Summary
```

If no issues are found, say so clearly and still mention which validation commands were run and any residual risk.
