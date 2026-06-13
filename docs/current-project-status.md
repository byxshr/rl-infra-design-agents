# Current Project Status

Last reviewed: 2026-06-13

## Purpose

This document gives future developers and AI agents a compact handoff summary of the current `rl-infra-design-agents` project state, what already works, what was recently improved, and where to continue next.

For detailed ledgers, use:

- `docs/rlinfrawiki-content-status.md` for RLInfraWiki page maturity.
- `docs/project-improvement-status.md` for project-level runnable workflow and usability improvements.
- `docs/ai-agent-code-review-reference.md` for prior code-review context.

## Repository State

Current branch: `main`

Recent commits:

| commit | summary |
|---|---|
| `b3c6458` | Add project improvement status ledger |
| `83bd029` | Implement P0 RLInfraWiki evidence content |
| `e96e175` | Implement RL infra design agents workflow |

At this migration handoff, standalone RLInfraWiki changes are committed, while the main repo migration changes are staged but not yet represented by a main repo commit.

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
conda run -n rl-infra-design-agents make render-example
conda run -n rl-infra-design-agents make review-gate
```

## Current Runnable Baseline

The core project workflow is runnable.

Last validated commands:

| command | result |
|---|---|
| `git submodule update --init --recursive` | Passed in the authoring workspace with local standalone RLInfraWiki dependency. This is not yet a remote-reproducible validation because `https://github.com/byxshr/RLInfraWiki` was unavailable. |
| `conda run -n rl-infra-design-agents make check` | Passed: generated query indices current, RLInfraWiki validation passed, `45 passed`. |
| `conda run -n rl-infra-design-agents make demo` | Passed: check, render, review gate, P0 query; printed workspace/context paths. |
| `conda run -n rl-infra-design-agents make render-example` | Passed: rendered `/tmp/rl-infra-task-workspace` with context bundle artifacts. |
| `conda run -n rl-infra-design-agents make review-gate` | Passed: review gate accepted the rendered example workspace. |
| `python scripts/validate.py` in standalone `RLInfraWiki/` | Passed. |
| `python scripts/generate_indices.py --check` in standalone `RLInfraWiki/` | Passed. |
| `python scripts/compose_context.py ... && python scripts/validate_context_bundle.py ...` in standalone `RLInfraWiki/` | Passed. |
| `conda run -n rl-infra-design-agents pytest -q` in standalone `RLInfraWiki/` | Passed: `45 passed`. Bare base `pytest` exited 139 in this environment, so conda env is the validated test runner. |

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

### Standalone RLInfraWiki

Top-level `RLInfraWiki/` is now the canonical skill root and RL infra dictionary repository. It includes:

- `sources/`, `wiki/`, `queries/`, `candidates/`, `artifacts/`, `data/`, `references/`, `tests/`, `Makefile`, and `pyproject.toml`.
- Context bundle tooling: `compose_context.py`, `validate_context_bundle.py`, `suggest_cross_framework.py`, `trace_related.py`, `render_context_bundle.py`.
- Unknown-framework tooling: `map_framework.py`, `plan_adapter.py`, `diff_capabilities.py`, `compare_frameworks.py`, `search_symbols.py`, `explain.py`, `resolve_alias.py`.
- First dictionary layer: concept, capability, interface, algorithm, framework-profile, failure-mode, validation-pattern, and adapter-recipe pages.

The main repo pins standalone commit `7768121` at `.agents/skills/RLInfraWiki`. `.gitmodules` currently uses fallback relative URL `../RLInfraWiki`; the authoring workspace uses a local `.git/config` override to the sibling standalone checkout for validation before the remote exists. Switch to `https://github.com/byxshr/RLInfraWiki` when the remote exists.

### Source Manifests

SGLang RL docs were added as a first-class source manifest:

- `.agents/skills/RLInfraWiki/sources/docs/sglang-rl-docs.yaml`

The SGLang version claim now includes `doc-sglang-rl-systems`, so `get_page.py --follow-sources` can trace P0 SGLang refit claims to the local docs snapshot.

### Status Ledgers

Two maintenance ledgers now exist:

- `docs/rlinfrawiki-content-status.md`: page-level Wiki maturity and evidence gaps.
- `docs/project-improvement-status.md`: project-level runnable workflow and usability improvements.

## Current Limitations

- The project is runnable as a design workflow, but it has not run real distributed RL training.
- P0 content is source-backed through local code/docs/source refs, but no GPU or multi-node NCCL smoke run has been executed.
- No real distributed training, SGLang/Megatron runtime integration, NCCL group update, or performance benchmark has been locally verified.
- P1 framework/content tracks are still mostly source summaries or dictionary-level contracts, not runtime-validated implementations.
- Bare base-environment `pytest` exited with code 139; `conda run -n rl-infra-design-agents pytest -q` is the validated test runner.

## Recommended Next Work

Use `docs/project-improvement-status.md` as the source of truth for detailed item status. The immediate sequence is:

1. Keep standalone `RLInfraWiki/` validation and main repo `make demo` green when changing the submodule.
2. Switch `.gitmodules` to `https://github.com/byxshr/RLInfraWiki` once the remote exists.
3. Add more task contracts from `IMP-004` using the context bundle workflow.
4. Promote P1 Wiki tracks from `docs/rlinfrawiki-content-status.md`, starting with rollout backend selection and async agentic RL.

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
```

- Do not mark performance, latency, or distributed correctness as verified unless there is local runtime evidence with commands, context, and logs/artifacts.
