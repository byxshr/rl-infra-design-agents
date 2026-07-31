# Current Project Status

Last reviewed: 2026-07-21

## Purpose

This document gives future developers and AI agents a compact handoff summary of the current `rl-infra-design-agents` project state, what already works, what was recently improved, and where to continue next.

For detailed ledgers, use:

- `docs/rlinfrawiki-content-status.md` for RLInfraWiki page maturity.
- `docs/project-improvement-status.md` for project-level runnable workflow and usability improvements.
- `docs/ai-agent-code-review-reference.md` for prior code-review context.

## Repository State

Current branch: `main`

Key migration commits:

| commit | summary |
|---|---|
| `ac8f346` | Document published RLInfraWiki remote |
| `38d1602` | Make RLInfraWiki a standalone dependency |
| `b3c6458` | Add project improvement status ledger |

At this migration handoff, standalone RLInfraWiki is published at `https://github.com/byxshr/RLInfraWiki`, and the main repo migration is committed in `38d1602`.

## What The Project Is

`rl-infra-design-agents` is a lightweight workflow and knowledge-base project for RL infrastructure design agents. It is not an RL training framework and does not wrap slime, SGLang, vLLM, verl, ROLL, AReaL, or Megatron directly.

The final migration plan is `docs/RLInfraWiki独立仓库改进方案_v1_1.md`. The older `docs/RLInfraWiki独立仓库改进方案_v1.md` is background only and should be used only for non-conflicting supplemental details.

The main workflow is:

1. Use the standalone RLInfraWiki dependency to compose a four-pack context bundle.
2. Render a task workspace from a task contract.
3. Lock the plan and prepare review context.
4. Validate the review gate before promotion.

Important commands:

```bash
conda run -n rl-infra-design-agents make check
conda run -n rl-infra-design-agents make demo
conda run -n rl-infra-design-agents make demo-slime-grpo-contract
conda run -n rl-infra-design-agents make demo-rollout-backend-selection
conda run -n rl-infra-design-agents make demo-training-rollout-mismatch-debug
conda run -n rl-infra-design-agents make render-example
conda run -n rl-infra-design-agents make review-gate
```

## Current Runnable Baseline

The core project workflow is runnable.

Last validated commands:

| command | result |
|---|---|
| `git submodule update --init --recursive` | Passed in the authoring workspace. The standalone remote now exists at `https://github.com/byxshr/RLInfraWiki`; a fresh remote clone should resolve `.gitmodules` URL `../RLInfraWiki` to the sibling GitHub repository after the main repo commit is pushed. |
| `conda run -n rl-infra-design-agents make check` | Passed: generated query indices current, RLInfraWiki validation passed, strict SourcePack hash validation passed, content ledger validation passed, policy-only `humanize-gate-invariants-v1` validation warned that no runtime root was supplied, golden path snapshot tests passed, `157 passed`. |
| Humanize-focused tests in the five root test modules | Passed: `73 tests`; includes target hygiene, bridge v1/v2 compatibility, operator schema v3, runtime discovery/validation, contract fingerprints, shared guidance-corpus compatibility, policy-only warning behavior, launcher `--plugin-dir` quoting, strict verdict import, legacy warning behavior, and no-partial-write rejection of gate-conflicting review output. |
| `python scripts/validate_humanize_review_contract.py --humanize-root ../humanize` | Passed against the local Humanize source runtime with shared-corpus validation, `static_contract_probe`, and contract fingerprint `sha256:8d88a5833551485d55cc735946884ae1e5b60b89cde128a2358dc88f23136405`. The installed marketplace `humanize@PolyArch` 1.16.0 predates this contract and is not claimed compatible despite reporting the same version. |
| `python scripts/validate_content_ledger.py` | Passed: `docs/rlinfrawiki-content-status.md` matches the pinned `RLInfraWiki` page IDs, paths, status enums, themes, source IDs, and review-ready structure checks. |
| `conda run -n rl-infra-design-agents make validate-golden-paths` | Passed: `8 passed`; four golden paths render into temporary workspaces, pass review gate, keep context sidecars, retain key semantic anchors, and enforce runtime-claim guard behavior. |
| `conda run -n rl-infra-design-agents make demo` | Passed: check, render, review gate, P0 query; printed workspace/context paths. |
| `conda run -n rl-infra-design-agents make demo-slime-grpo-contract` | Passed: rendered and review-gated a slime-compatible GRPO/RLVR algorithm data-contract workspace. |
| `conda run -n rl-infra-design-agents make demo-rollout-backend-selection` | Passed: rendered and review-gated `/tmp/rollout-backend-selection-workspace`, queried rollout backend selection pages, and printed workspace/context paths. |
| `conda run -n rl-infra-design-agents make demo-training-rollout-mismatch-debug` | Passed: rendered and review-gated `/tmp/training-rollout-mismatch-debug-workspace`, queried mismatch debugging pages, and printed workspace/context paths. |
| `conda run -n rl-infra-design-agents make render-example` | Passed: rendered `/tmp/rl-infra-task-workspace` with context bundle artifacts. |
| `conda run -n rl-infra-design-agents make review-gate` | Passed: review gate accepted the rendered example workspace. |
| GitHub Actions `validate` workflow | Updated: checkout with recursive submodules, install dev dependencies, run `make check`, `make render-example`, `make review-gate`, P0 query smoke, slime GRPO/RLVR data-contract demo, rollout backend selection demo, and training/rollout mismatch debug demo on push/PR. First remote Actions run should be checked after push. |
| `python scripts/validate.py` in standalone `RLInfraWiki/` | Passed. |
| `python scripts/generate_indices.py --check` in standalone `RLInfraWiki/` | Passed. |
| `python scripts/verify_source_refs.py --strict-hash` in standalone `RLInfraWiki/` | Passed: strict metadata/hash validation succeeded with `0 warning(s)`. |
| `python scripts/verify_source_refs.py --check-local --source-root .. --strict-hash` in standalone `RLInfraWiki/` | Passed: sibling local clones matched recorded commits, paths, line ranges, and snippet hashes with `0 warning(s)`. |
| `python scripts/refresh_sources.py --dry-run --source-root .. --strict-hash --fail-on-errors` in standalone `RLInfraWiki/` | Passed: produced a non-mutating source refresh report with no drift errors and `0 warning(s)`. |
| `conda run -n rl-infra-design-agents make validate-source-drift SOURCE_ROOT=..` | Passed: main repo wrapper ran the strict local SourcePack drift checker against sibling clones. |
| `python scripts/compose_context.py ... && python scripts/validate_context_bundle.py ...` in standalone `RLInfraWiki/` | Passed. |
| `python .agents/skills/RLInfraWiki/scripts/query.py 'async agentic RL Ray orchestration tool calling multi-turn rollout stale policy' --limit 10` | Passed: returned agentic tool-calling, Ray multi-role, OpenAI-compatible agent app, multi-turn environment, orchestration options, async rollout, AReaL, and ROLL pages in the top 10. |
| `python .agents/skills/RLInfraWiki/scripts/compare_frameworks.py areal roll --capability async-rollout` | Passed: both AReaL and ROLL report `source-reported` async rollout evidence from SourcePack-backed sources. |
| `conda run -n rl-infra-design-agents python -m pytest -q` via the main repo plus pinned `RLInfraWiki` dependency | Passed through `make check`: `145 passed`. Bare base `pytest` previously exited 139 in this environment, so conda env is the validated test runner. |

## Completed Progress

### Initial Workflow Implementation

The repository contains the core RL design-agent workflow:

- RLInfraWiki mounted under `.agents/skills/RLInfraWiki/` from standalone canonical `../RLInfraWiki`.
- Query, page fetch, index generation, validation, task rendering, plan locking, review-context rendering, and review-gate scripts.
- Example task contract: `examples/task_contracts/slime-weight-sync.yaml`.
- Tests for schema, query, rendering, review gate, goal handling, and review-loop utilities.

### P0 RLInfraWiki Content

The first content track, `slime + Megatron + SGLang weight sync`, has been promoted to `review-ready`.

Key P0 pages now contain code/doc evidence, design implications, failure modes, validation ideas, and open gaps:

- `wiki/systems/slime.md`
- `wiki/backends/sglang.md`
- `wiki/training/megatron.md`
- `wiki/patterns/megatron-sglang.md`
- `wiki/recipes/design-weight-sync.md`
- `wiki/weight-sync/overview.md`
- `wiki/weight-sync/disk-checkpoint-sync.md`
- `wiki/weight-sync/distributed-group-sync.md`
- `wiki/weight-sync/tensor-in-memory-sync.md`
- `wiki/weight-sync/delta-weight-sync.md`
- `wiki/weight-sync/full-weight-sync-fallback.md`

The evidence style intentionally follows KernelWiki's layered discipline:

- `sources/` stores traceable source manifests.
- `wiki/` stores synthesized design knowledge.
- `queries/` stores generated indices.

Large upstream docs or source files are not copied into the Wiki. Pages use evidence summaries and SourcePack source refs with source IDs, upstream commits, repo-relative paths, line ranges, claim IDs, and provenance. Local clones are ingestion backends only.

### Slime GRPO/RLVR Data Contract

The second golden path is `examples/task_contracts/slime-grpo-rlvr-data-contract.yaml`. It renders a slime-compatible algorithm data-contract design workspace rather than a full GRPO/RLVR implementation.

The rendered workspace covers:

- rollout sample fields, `old_logprob`, optional `reference_logprob`, reward/verifier output, `group_id`, and `policy_version`.
- boundaries between rollout backend, reward service, data buffer, and trainer batch materialization.
- validation/risk pages for sample schema drift, logprob consistency, grouped rollout invariants, reward timeout, stale-policy bound, and train/infer schema match.
- explicit non-claims for GPU, distributed training, throughput, latency, production readiness, and source-reported behavior.

### Rollout Backend Selection

The third golden path is `examples/task_contracts/rollout-backend-selection.yaml`. It renders a target-aware, cross-framework backend selection workspace for choosing SGLang versus vLLM as the rollout backend for verl RLVR/GRPO design.

The rendered workspace covers:

- Target, Generic, Cross-Framework, and Validation & Risk context packs.
- `primary_backend`, `fallback_backend`, primary weight update path, full fallback, `weight_version`, cache policy, and logprob policy.
- source-backed evidence from `capability-rollout-backend-selection`, `comparisons-rollout-backends`, `backend-sglang`, `backend-vllm`, colocated/disaggregated/PD topology pages, stale-cache/logprob failure pages, and validation pages.
- explicit non-claims for GPU, NCCL, multi-node execution, throughput, latency, production readiness, and source-reported backend behavior.

### Training/Rollout Mismatch Debugging

The fourth golden path is `examples/task_contracts/training-rollout-mismatch-debug.yaml`. It renders a slime-targeted, cross-framework debugging workspace for training/rollout mismatch analysis rather than a runtime fix.

The rendered workspace covers:

- version identity for `policy_version`, `weight_version`, trainer step, rollout request, backend ID, and artifact references.
- cache, logprob replay/recompute, token/mask/schema, reward/data-buffer, backend, and topology isolation order.
- Target, Generic, Cross-Framework, and Validation & Risk context packs using `recipe-debug-training-rollout-mismatch`, `observability-training-inference-mismatch`, logprob/schema/version validation pages, and stale-cache/sample-drift/stale-policy failure pages.
- explicit non-claims for GPU, NCCL, multi-node execution, performance, production readiness, and source-reported backend/framework behavior.

### Standalone RLInfraWiki

Top-level `RLInfraWiki/` is now the canonical skill root and RL infra dictionary repository. It includes:

- `sources/`, `wiki/`, `queries/`, `candidates/`, `artifacts/`, `data/`, `references/`, `tests/`, `Makefile`, and `pyproject.toml`.
- Context bundle tooling: `compose_context.py`, `validate_context_bundle.py`, `suggest_cross_framework.py`, `trace_related.py`, `render_context_bundle.py`.
- Unknown-framework tooling: `map_framework.py`, `plan_adapter.py`, `diff_capabilities.py`, `compare_frameworks.py`, `search_symbols.py`, `explain.py`, `resolve_alias.py`.
- First dictionary layer: concept, capability, interface, algorithm, framework-profile, failure-mode, validation-pattern, and adapter-recipe pages.

The main repo pins standalone commit `0c2e91f` at `.agents/skills/RLInfraWiki`. `.gitmodules` uses the relative URL `../RLInfraWiki`, which resolves to the sibling GitHub repository `https://github.com/byxshr/RLInfraWiki` for normal clones of `https://github.com/byxshr/rl-infra-design-agents`.

### Source Refresh / Drift Checker

`RLInfraWiki` now has a non-mutating SourcePack refresh workflow:

- `verify_source_refs.py --strict-hash` validates source-ref metadata and rejects legacy hash placeholders in main repo `make check`.
- `verify_source_refs.py --check-local --source-root .. --strict-hash` verifies sibling clone commits, paths, line ranges, and real snippet hashes for local source refresh work.
- `refresh_sources.py --dry-run --source-root .. --strict-hash` renders a refresh report without fetching, rewriting manifests, or vendoring upstream code; `--fail-on-errors` is available for automation that should fail on drift.
- Legacy `sha256: source-reported` refs have been refreshed to real snippet hashes; raw non-strict checks are reserved for migration/audit use.

### Source Manifests

SGLang RL docs were added as a first-class source manifest:

- `.agents/skills/RLInfraWiki/sources/docs/sglang-rl-docs.yaml`

The SGLang version claim now includes `doc-sglang-rl-systems`, so `get_page.py --follow-sources` can trace P0 SGLang refit claims to the local docs snapshot.

### Status Ledgers

Two maintenance ledgers now exist:

- `docs/rlinfrawiki-content-status.md`: page-level Wiki maturity and evidence gaps.
- `docs/project-improvement-status.md`: project-level runnable workflow and usability improvements.

### Humanize Target Hygiene

IMP-018 upgrades real target-repository startup from a workspace hint to a checked two-stage flow:

- `prepare-humanize-task` renders a staging workspace; the generated target-mode guide no longer tells operators to launch Claude Code from `/tmp`.
- The target plan must be copied to a normal repository path, committed, clean, and byte-identical to the staged `docs/plan.md`.
- `preflight_humanize_target.py` rejects unsafe plan paths, stale plan locks, unresolved local base branches, dirty targets, bridge metadata mismatch, and tracked or staged `.humanize/` state. Both prepare and start preserve human docs by default. When needed, preflight adds anchored `/.humanize/` to local `.git/info/exclude` before later plan/tree checks, so that local-only write can remain even when a subsequent check fails; it does not edit tracked `.gitignore` or target source files.
- `start-humanize-task` validates the selected Humanize runtime against `humanize-gate-invariants-v1`. Target runtime failures return `2`; hygiene failures return `3`. An explicit local root is passed to Claude through `--plugin-dir`. Runtime provenance includes a deterministic SHA256 contract fingerprint so identical declared versions do not imply identical compatibility, and records the check as `static_contract_probe`.
- Bridge metadata remains schema v2. Operator metadata is schema v3 and records contract/runtime/fingerprint/checker provenance. Round import remains compatible with v1/v2 metadata, but schema v3 requires a valid gate verdict and every schema rejects explicit guidance to track or commit `.humanize/`. Runtime validation and the Humanize shell gate share one safe/unsafe guidance corpus; failed runtime revalidation does not delete the last validated operator bundle.

## Current Limitations

- The project is runnable as a design workflow, but it has not run real distributed RL training.
- P0 content is source-backed through local code/docs/source refs, but no GPU or multi-node NCCL smoke run has been executed.
- No real distributed training, SGLang/Megatron runtime integration, NCCL group update, or performance benchmark has been locally verified.
- P1 framework/content tracks are still mostly source summaries or dictionary-level contracts, not runtime-validated implementations.
- The IMP-020 launcher/import path was verified with synthetic targets, fake Claude/Codex, and local Humanize source. A real Claude Code/Humanize Stop-hook round has not yet been rerun with this implementation.
- Runtime compatibility is a static file/marker/corpus probe. It identifies and fingerprints the selected contract bytes but does not execute the Stop hook or prove end-to-end plugin capability.
- Humanize's IMP-020-specific shell suites and `claude plugin validate .` passed. The repository's Bash-4 parallel test runner cannot run under macOS system Bash 3.2, and an equivalent serial run still exposes pre-existing platform/tool assumptions such as GNU `sed`, `timeout`, `sha256sum`, and unrelated legacy test expectations.
- Bare base-environment `pytest` exited with code 139; `conda run -n rl-infra-design-agents pytest -q` is the validated test runner.

## Recommended Next Work

Use `docs/project-improvement-status.md` as the source of truth for detailed item status. The immediate sequence is:

1. Keep standalone `RLInfraWiki/` validation and main repo `make demo` green when changing the submodule.
2. Watch GitHub Actions after each push; fix submodule, dependency, or review-gate drift before expanding content.
3. Keep all four golden paths green in CI after each submodule pointer update.
4. Implement IMP-021 external-validation handoff, then IMP-022 AC-weighted progress and IMP-019 bounded review retry.
5. Publish or install a Humanize runtime containing `humanize-gate-invariants-v1`; until then use `HUMANIZE_PLUGIN_ROOT=../humanize`.
6. Rerun a real target-repository Humanize loop through the generated launcher and retain the preflight, Stop-hook, verdict, and import artifacts as pilot evidence.
7. Promote the remaining P1 Wiki tracks from `docs/rlinfrawiki-content-status.md`.

## Developer Notes

- Regenerate indices after Wiki frontmatter or summary changes:

```bash
conda run -n rl-infra-design-agents python .agents/skills/RLInfraWiki/scripts/generate_indices.py
```

- Validate the full project before committing workflow or Wiki changes:

```bash
conda run -n rl-infra-design-agents make check
```

- For the current P0 smoke path:

```bash
conda run -n rl-infra-design-agents python .agents/skills/RLInfraWiki/scripts/query.py "Megatron SGLang weight sync" --limit 8
conda run -n rl-infra-design-agents make render-example
conda run -n rl-infra-design-agents make review-gate
conda run -n rl-infra-design-agents make demo-training-rollout-mismatch-debug
```

- Do not mark performance, latency, or distributed correctness as verified unless there is local runtime evidence with commands, context, and logs/artifacts.
