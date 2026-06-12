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
| Core checks | done | `conda run -n rl-infra-design-agents make check` passed with 40 tests. | Keep green after every workflow or content change. |
| P0 RLInfraWiki content | done | `slime + Megatron + SGLang weight sync` pages promoted to `review-ready`. | Use as the first end-to-end demo content track. |
| Example rendering | done | `make render-example` produced `/tmp/rl-infra-task-workspace`. | Inspect generated docs for design quality and template gaps. |
| Review gate | done | `make review-gate` passed for the rendered example workspace. | Strengthen review gate after demo quality is improved. |
| Git state | done | Local commit `83bd029 Implement P0 RLInfraWiki evidence content` exists; branch is ahead of `origin/main` by 1. | Push when ready. |

## Improvement Roadmap

| item_id | theme | priority | status | target | next_action | acceptance_check | last_reviewed |
|---|---|---|---|---|---|---|---|
| IMP-001 | Golden demo path | P0 | todo | Provide a single documented command path that proves the project runs end-to-end. | Add `make demo` or a documented equivalent that runs checks, renders the slime weight-sync example, and validates review gate. | A fresh user can run one command or one short documented sequence and see generated workspace paths plus `Review gate passed`. | 2026-06-13 |
| IMP-002 | Generated workspace quality | P0 | todo | Make `/tmp/rl-infra-task-workspace` docs useful for architecture review, not just template output. | Inspect generated `architecture.md`, `interfaces.md`, `validation_matrix.md`, `risk_register.md`, and update renderer/templates/prompts so P0 evidence appears in the right sections. | Generated docs mention primary sync path, full fallback, `weight_version`, `flush_cache`, failure modes, and cited Wiki/source IDs. | 2026-06-13 |
| IMP-003 | README quickstart | P0 | todo | Make the project immediately runnable from README. | Add a short "Run the P0 demo" section with conda env, `make check`, `make render-example`, `make review-gate`, and expected outputs. | README answers "how do I run this project now?" without reading internal docs. | 2026-06-13 |
| IMP-004 | Task contract library | P1 | todo | Cover common RL infra/algorithm design scenarios beyond weight sync. | Add example task contracts for rollout backend selection, async agentic RL pipeline, GRPO infra design, training-inference mismatch debug, and training backend comparison. | Each new contract renders successfully and has required Wiki queries that return relevant pages. | 2026-06-13 |
| IMP-005 | P1 Wiki evidence | P1 | todo | Promote high-impact P1 Wiki tracks to `code-evidenced`. | Implement rollout backend selection, async agentic RL, Ray orchestration, and training backend comparison entries from `docs/rlinfrawiki-content-status.md`. | Relevant P1 pages cite local repo/doc paths and update the content status ledger. | 2026-06-13 |
| IMP-006 | Algorithm infra recipe | P1 | todo | Help users design RL algorithm changes, not only infra component choices. | Add a recipe for algorithm-to-infra mapping: rollout fields, old logprobs, KL/reference policy, reward/verifier hooks, stale policy controls, eval metrics, and data contracts. | A GRPO/DAPO-style task can render a design packet with algorithm assumptions mapped to infra requirements. | 2026-06-13 |
| IMP-007 | Content ledger validation | P1 | todo | Prevent Wiki maturity status from drifting. | Add a lightweight checker for `docs/rlinfrawiki-content-status.md`: page exists, status enum valid, `review-ready` pages contain required sections, and source IDs resolve. | Checker passes locally and is wired into `make check` after rules stabilize. | 2026-06-13 |
| IMP-008 | Demo workspace fixture | P1 | todo | Make generated demo output reviewable in git without relying on `/tmp`. | Add a small expected-workspace fixture or golden snapshot strategy that records key generated sections without committing volatile run artifacts. | Tests can detect when renderer output loses required P0 evidence. | 2026-06-13 |
| IMP-009 | Review gate strengthening | P2 | todo | Make review gate check design quality, not only file presence/status. | Extend review gate to require cited Wiki page IDs, source IDs, validation matrix rows, fallback path, and unresolved-risk handling for P0 tasks. | A deliberately weak rendered workspace fails review gate with actionable errors. | 2026-06-13 |
| IMP-010 | Source refresh workflow | P2 | deferred | Keep local source manifests aligned with upstream clones. | After content stabilizes, improve refresh scripts or docs so agents can refresh source manifests and version claims safely. | Source refresh can update commit/version metadata without breaking `make check`. | 2026-06-13 |

## Immediate Recommended Sequence

1. Implement `IMP-001` and `IMP-003` together so the project has a clear runnable demo path.
2. Use that demo to inspect output quality, then implement `IMP-002`.
3. Add task contracts from `IMP-004` only after the P0 generated workspace is strong enough to be a template for other workflows.
4. Promote P1 Wiki tracks from `IMP-005` in the order needed by the new task contracts.

## Maintenance Rules

- Keep this file task-level and project-level; do not duplicate every Wiki page row from `docs/rlinfrawiki-content-status.md`.
- Every `done` item should name a command, file, or artifact that proves completion.
- Do not mark GPU/distributed behavior as done unless it has local runtime evidence.
- When a new task contract is added, add or update one row here and one row in the relevant Wiki content status theme if content maturity changes.
