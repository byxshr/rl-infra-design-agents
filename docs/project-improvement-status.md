# Project Improvement Status

## Purpose

This file tracks project-level improvements needed to make `rl-infra-design-agents` easier to run and more useful for RL infrastructure and algorithm development.

It is separate from `docs/rlinfrawiki-content-status.md`:

- `rlinfrawiki-content-status.md` tracks Wiki page maturity.
- This file tracks runnable workflows, generated workspace quality, task contracts, review gates, and developer-facing usability.

Update this file whenever an improvement item is completed, re-scoped, blocked, or promoted to a higher priority.

## Status Taxonomy

| status | meaning |
|---|---|
| `done` | Implemented and validated with the listed acceptance check. |
| `in-progress` | Work has started, but acceptance checks are not complete. |
| `todo` | Ready for a future agent to implement. |
| `blocked` | Requires missing input, external environment, or a prior item. |
| `deferred` | Useful, but intentionally postponed. |

## Current Baseline

| area | status | evidence | next_action |
|---|---|---|---|
| Core checks | done | `conda run -n rl-infra-design-agents make check` passed with 46 tests. | Keep green after every workflow or content change. |
| P0 RLInfraWiki content | done | Standalone `RLInfraWiki/` is pinned by `.agents/skills/RLInfraWiki` and preserves `slime + Megatron + SGLang weight sync` query/render/review behavior. | Keep standalone validation green before updating the submodule pointer. |
| Example rendering | done | `make render-example` produced `/tmp/rl-infra-task-workspace` with `context/context_bundle.md`, `context/context_bundle.json`, and `context/context_sources.yaml`. | Use generated context artifacts in review. |
| Algorithm data-contract path | done | `conda run -n rl-infra-design-agents make demo-slime-grpo-contract` renders and review-gates a slime-compatible GRPO/RLVR algorithm data-contract workspace. | Use as the second golden path for algorithm-to-infra design tasks. |
| Review gate | done | `make review-gate` passed and now rejects missing/invalid context bundles. | Keep no-target-only and page/source ID checks green. |
| Git state | done | Main repo uses `.agents/skills/RLInfraWiki` as a gitlink pinned to standalone `RLInfraWiki`; tracked `.gitmodules` uses relative URL `../RLInfraWiki`, which resolves to published sibling repo `https://github.com/byxshr/RLInfraWiki`. | Keep submodule initialization green in fresh clones and CI. |
| CI | done | `.github/workflows/validate.yml` checks out submodules, installs dev dependencies, runs `make check`, renders the P0 workspace, validates the review gate, and performs a P0 query smoke. | Watch the first remote Actions run after push and keep it green. |

## Improvement Roadmap

| item_id | theme | priority | status | target | next_action | acceptance_check | last_reviewed |
|---|---|---|---|---|---|---|---|
| IMP-001 | Golden demo path | P0 | done | Provide a single documented command path that proves the project runs end-to-end. | `make demo` now runs check, renders the slime weight-sync example, validates review gate, and prints workspace/context paths. | `conda run -n rl-infra-design-agents make demo` passed and printed `Review gate passed`. | 2026-06-13 |
| IMP-002 | Generated workspace quality | P0 | done | Make `/tmp/rl-infra-task-workspace` docs useful for architecture review, not just template output. | Renderer now writes context bundle artifacts and P0 draft/plan sections for primary sync path, full fallback, `weight_version`, `flush_cache`, failure modes, Wiki page IDs, and source IDs. | `make render-example` plus `make review-gate` passed with context artifacts present. | 2026-06-13 |
| IMP-003 | README quickstart | P0 | done | Make the project immediately runnable from README. | README now documents submodule init through the published `RLInfraWiki` sibling remote, `make demo`, manual context bundle, render, and review commands. | README answers "how do I run this project now?" from the Quick Start section. | 2026-06-13 |
| IMP-004 | Task contract library | P1 | in-progress | Cover common RL infra/algorithm design scenarios beyond weight sync. | Added `slime-grpo-rlvr-data-contract.yaml` as the second golden path; next promote rollout backend selection and mismatch debugging. | Each new contract renders successfully and has required Wiki queries that return relevant pages. | 2026-06-13 |
| IMP-005 | P1 Wiki evidence | P1 | todo | Promote high-impact P1 Wiki tracks to `code-evidenced`. | Implement rollout backend selection, async agentic RL, Ray orchestration, and training backend comparison entries from `docs/rlinfrawiki-content-status.md`. | Relevant P1 pages cite local repo/doc paths and update the content status ledger. | 2026-06-13 |
| IMP-006 | Algorithm infra recipe | P1 | in-progress | Help users design RL algorithm changes, not only infra component choices. | `make demo-slime-grpo-contract` now renders a slime-compatible GRPO/RLVR data-contract design packet covering rollout fields, old/ref logprobs, reward/verifier hooks, sample grouping, stale-policy controls, and validation. | A GRPO/DAPO-style task can render a design packet with algorithm assumptions mapped to infra requirements. | 2026-06-13 |
| IMP-007 | Content ledger validation | P1 | todo | Prevent Wiki maturity status from drifting. | Add a lightweight checker for `docs/rlinfrawiki-content-status.md`: page exists, status enum valid, `review-ready` pages contain required sections, and source IDs resolve. | Checker passes locally and is wired into `make check` after rules stabilize. | 2026-06-13 |
| IMP-008 | Demo workspace fixture | P1 | todo | Make generated demo output reviewable in git without relying on `/tmp`. | Add a small expected-workspace fixture or golden snapshot strategy that records key generated sections without committing volatile run artifacts. | Tests can detect when renderer output loses required P0 evidence. | 2026-06-13 |
| IMP-009 | Review gate strengthening | P2 | done | Make review gate check design quality, not only file presence/status. | Review gate now requires context bundle markdown/json/source files, validates four-pack coverage, page IDs, source IDs, generic/cross-framework/validation packs, and keeps performance/production claims tied to context. Round-2 review found no blocker; the noted P3 branch coverage gap was closed with direct regression tests for invalid, missing validation/risk, missing source IDs, and missing sources-map contexts. | `make review-gate` passed for the upgraded rendered workspace; missing context artifacts fail locally; standalone `tests/test_review_gate.py` now has 15 passing gate tests. | 2026-06-13 |
| IMP-010 | Source refresh workflow | P2 | deferred | Keep local source manifests aligned with upstream clones. | After content stabilizes, improve refresh scripts or docs so agents can refresh source manifests and version claims safely. | Source refresh can update commit/version metadata without breaking `make check`. | 2026-06-13 |
| IMP-011 | GitHub Actions CI | P1 | done | Make published repositories self-checking after push and PRs. | Enhanced `validate.yml` to checkout the RLInfraWiki submodule, install dev dependencies, run `make check`, render the P0 task workspace, validate review gate, run a P0 query smoke, and render/review the slime GRPO/RLVR data-contract path. | Local equivalents passed before CI change; first remote Actions run should pass after push. | 2026-06-13 |

## Immediate Recommended Sequence

1. Keep `make demo`, `make check`, `make render-example`, and `make review-gate` green after any RLInfraWiki submodule update.
2. Promote rollout backend selection and mismatch debugging contracts to golden paths using the context bundle workflow.
3. Promote P1 Wiki tracks from `IMP-005` in the standalone `RLInfraWiki/` repository, then update the main repo gitlink.
4. Watch GitHub Actions after each push; fix submodule, dependency, or review-gate drift before expanding content.

## Maintenance Rules

- Keep this file task-level and project-level; do not duplicate every Wiki page row from `docs/rlinfrawiki-content-status.md`.
- Every `done` item should name a command, file, or artifact that proves completion.
- Do not mark GPU/distributed behavior as done unless it has local runtime evidence.
- When a new task contract is added, add or update one row here and one row in the relevant Wiki content status theme if content maturity changes.
