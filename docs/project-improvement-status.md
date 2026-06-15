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
| Core checks | done | `conda run -n rl-infra-design-agents make check` passed with SourcePack metadata validation, content ledger validation, golden path snapshot tests, Humanize bridge tests, and 90 tests. | Keep green after every workflow or content change. |
| P0 RLInfraWiki content | done | Standalone `RLInfraWiki/` is pinned by `.agents/skills/RLInfraWiki` and preserves `slime + Megatron + SGLang weight sync` query/render/review behavior. | Keep standalone validation green before updating the submodule pointer. |
| Example rendering | done | `make render-example` produced `/tmp/rl-infra-task-workspace` with `context/context_bundle.md`, `context/context_bundle.json`, and `context/context_sources.yaml`. | Use generated context artifacts in review. |
| Algorithm data-contract path | done | `conda run -n rl-infra-design-agents make demo-slime-grpo-contract` renders and review-gates a slime-compatible GRPO/RLVR algorithm data-contract workspace. | Use as the second golden path for algorithm-to-infra design tasks. |
| Rollout backend selection path | done | `conda run -n rl-infra-design-agents make demo-rollout-backend-selection` renders and review-gates `/tmp/rollout-backend-selection-workspace` with SGLang/vLLM source-backed selection scaffold. | Use as the third golden path for backend selection design tasks. |
| Training/rollout mismatch debug path | done | `conda run -n rl-infra-design-agents make demo-training-rollout-mismatch-debug` renders and review-gates `/tmp/training-rollout-mismatch-debug-workspace` with a source-backed debugging scaffold. | Use as the fourth golden path for mismatch/debug design tasks. |
| Golden path snapshots | done | `conda run -n rl-infra-design-agents python -m pytest -q tests/test_golden_path_snapshots.py` renders all four golden paths into temporary workspaces, checks semantic anchors, and tests runtime-claim guard behavior. | Keep expectations focused on stable design meaning, not full-file snapshots. |
| P1 rollout/backend/debug/async evidence | done | Standalone `RLInfraWiki` commit `0c2e91f` is pinned by the main repo submodule and includes rollout backend selection, training/rollout mismatch debugging, async agentic RL, Ray orchestration evidence, and strict source-ref drift tooling. | Keep source-reported backend/debug/async claims distinct from local runtime verification. |
| Source refresh/drift workflow | done | Standalone `RLInfraWiki` commit `0c2e91f` adds metadata-safe source ref validation, local clone drift checking, non-mutating refresh reports, review-driven CLI/test hardening, and strict snippet-hash gates with zero legacy placeholders; main repo `make check` runs strict hash validation. | Run `make validate-source-drift SOURCE_ROOT=..` before refreshing SourcePack refs from sibling clones. |
| Review gate | done | `make review-gate` passed and now rejects missing/invalid context bundles. | Keep no-target-only and page/source ID checks green. |
| Git state | done | Main repo uses `.agents/skills/RLInfraWiki` as a gitlink pinned to standalone `RLInfraWiki`; tracked `.gitmodules` uses relative URL `../RLInfraWiki`, which resolves to published sibling repo `https://github.com/byxshr/RLInfraWiki`. | Keep submodule initialization green in fresh clones and CI. |
| CI | done | `.github/workflows/validate.yml` checks out submodules, installs dev dependencies, runs `make check`, renders/reviews P0, slime GRPO/RLVR data-contract, rollout backend selection, and training/rollout mismatch debug paths. | Watch the first remote Actions run after push and keep it green. |

## Improvement Roadmap

| item_id | theme | priority | status | target | next_action | acceptance_check | last_reviewed |
|---|---|---|---|---|---|---|---|
| IMP-001 | Golden demo path | P0 | done | Provide a single documented command path that proves the project runs end-to-end. | `make demo` now runs check, renders the slime weight-sync example, validates review gate, and prints workspace/context paths. | `conda run -n rl-infra-design-agents make demo` passed and printed `Review gate passed`. | 2026-06-13 |
| IMP-002 | Generated workspace quality | P0 | done | Make `/tmp/rl-infra-task-workspace` docs useful for architecture review, not just template output. | Renderer now writes context bundle artifacts and P0 draft/plan sections for primary sync path, full fallback, `weight_version`, `flush_cache`, failure modes, Wiki page IDs, and source IDs. | `make render-example` plus `make review-gate` passed with context artifacts present. | 2026-06-13 |
| IMP-003 | README quickstart | P0 | done | Make the project immediately runnable from README. | README now documents submodule init through the published `RLInfraWiki` sibling remote, `make demo`, manual context bundle, render, and review commands. | README answers "how do I run this project now?" from the Quick Start section. | 2026-06-13 |
| IMP-004 | Task contract library | P1 | done | Cover common RL infra/algorithm design scenarios beyond weight sync. | Added training/rollout mismatch debugging as the fourth golden path after P0 weight sync, slime GRPO/RLVR data-contract, and rollout backend selection. | `conda run -n rl-infra-design-agents make demo-training-rollout-mismatch-debug` passed and rendered a source-backed context bundle with four required packs. | 2026-06-14 |
| IMP-005 | P1 Wiki evidence | P1 | in-progress | Promote high-impact P1 Wiki tracks to `code-evidenced`. | Rollout backend selection, training/rollout mismatch debugging, async agentic RL, and Ray orchestration are complete through standalone `RLInfraWiki` commit `0c2e91f`; next promote training backend comparison entries from `docs/rlinfrawiki-content-status.md`. | Main repo `make check` passed with strict SourcePack hash validation, content ledger validation, golden path snapshots, and 84 tests; all four demos passed review gate; async agentic/Ray query and `compare_frameworks.py areal roll --capability async-rollout` passed. Runtime GPU/NCCL/multi-node/performance claims remain unverified. | 2026-06-15 |
| IMP-006 | Algorithm infra recipe | P1 | in-progress | Help users design RL algorithm changes, not only infra component choices. | `make demo-slime-grpo-contract` now renders a slime-compatible GRPO/RLVR data-contract design packet covering rollout fields, old/ref logprobs, reward/verifier hooks, sample grouping, stale-policy controls, and validation. | A GRPO/DAPO-style task can render a design packet with algorithm assumptions mapped to infra requirements. | 2026-06-13 |
| IMP-007 | Content ledger validation | P1 | done | Prevent Wiki maturity status from drifting. | Added `scripts/validate_content_ledger.py` and root pytest coverage for valid ledger, invalid status, missing page path, unknown source ID, and missing review-ready structure. | `python scripts/validate_content_ledger.py` passed and `conda run -n rl-infra-design-agents make check` now runs the checker before `pytest -q`. | 2026-06-14 |
| IMP-008 | Demo workspace fixture | P1 | done | Make generated demo output reviewable in git without relying on `/tmp`. | Added semantic snapshot expectations for P0 weight sync, slime GRPO/RLVR data contract, rollout backend selection, and training/rollout mismatch debugging without committing generated workspaces. | `conda run -n rl-infra-design-agents python -m pytest -q tests/test_golden_path_snapshots.py` passed with 8 tests and `make check` now includes these regression tests. | 2026-06-14 |
| IMP-009 | Review gate strengthening | P2 | done | Make review gate check design quality, not only file presence/status. | Review gate now requires context bundle markdown/json/source files, validates four-pack coverage, page IDs, source IDs, generic/cross-framework/validation packs, and keeps performance/production claims tied to context. Round-2 review found no blocker; the noted P3 branch coverage gap was closed with direct regression tests for invalid, missing validation/risk, missing source IDs, and missing sources-map contexts. | `make review-gate` passed for the upgraded rendered workspace; missing context artifacts fail locally; standalone `tests/test_review_gate.py` now has 15 passing gate tests. | 2026-06-13 |
| IMP-010 | Source refresh workflow | P2 | done | Keep local source manifests aligned with upstream clones. | Added SourcePack metadata validation, local clone drift checking, strict hash mode, non-mutating refresh reports, collapsed warning output, `--verbose`, `--fail-on-errors`, nested relative `local_path` support, and strict UTF-8 source reads in standalone `RLInfraWiki`; main repo `make check` now runs strict metadata/hash validation and `make validate-source-drift SOURCE_ROOT=..` runs the strict local checker. | `conda run -n rl-infra-design-agents make check` passed with 84 tests; `conda run -n rl-infra-design-agents make validate-source-drift SOURCE_ROOT=..` passed with 0 legacy hash warnings and no drift errors. | 2026-06-15 |
| IMP-011 | GitHub Actions CI | P1 | done | Make published repositories self-checking after push and PRs. | Enhanced `validate.yml` to checkout the RLInfraWiki submodule, install dev dependencies, run `make check`, render/review the P0 task workspace, slime GRPO/RLVR data-contract path, rollout backend selection path, and training/rollout mismatch debug path. | Local equivalents passed before CI change; first remote Actions run should pass after push. | 2026-06-14 |
| IMP-012 | Strict evidence mode | P2 | done | Eliminate legacy SourcePack hash placeholders and make strict hash validation the default gate. | Refreshed the 9 remaining slime source refs from `sha256: source-reported` to real snippet hashes in standalone `RLInfraWiki` commit `0c2e91f`; standalone and main repo Makefile gates now call `verify_source_refs.py --strict-hash`. | `python scripts/verify_source_refs.py --strict-hash`, local strict drift check, strict refresh report, standalone `make check`, and main repo `make check` passed with 0 source-ref warnings. | 2026-06-15 |
| IMP-013 | Humanize-ready workspace bridge | P1 | done | Make rendered RL infra task workspaces directly usable as Humanize RLCR inputs. | Added `scripts/prepare_humanize_task.py` and `make prepare-humanize-task`; the bridge renders through pinned `RLInfraWiki`, validates and preserves the context trio, locks the plan, runs the pre-review gate without `--require-review`, records Humanize/Codex prerequisite warnings, target repo/diff-base status, schema version, and main/`RLInfraWiki` commit anchors, and writes `humanize_start.md` plus `.humanize/rlinfra_bridge.json`. IMP-014/015 remain the boundaries for importing Humanize rounds and exposing a stricter start wrapper. | `conda run -n rl-infra-design-agents python scripts/prepare_humanize_task.py --contract examples/task_contracts/training-rollout-mismatch-debug.yaml --workspace /tmp/rlinfra-humanize-task-workspace --target-repo /Users/bianyuxin/PycharmProjects/github-repos/slime --diff-base main --force --overwrite-human-docs`, `make prepare-humanize-task`, `make check`, four demos, and `git diff --check` passed. | 2026-06-15 |
| IMP-014 | Humanize round import/export | P1 | todo | Bridge Humanize `.humanize/rlcr/...` artifacts into this repo's RLCR review ledger and gate. | Add an import command that reads Humanize round summaries/review results, writes this workspace's `review_rounds/round-N/` artifacts, parses Codex findings into `review_issues.jsonl`, and lets `validate_review_gate.py --require-review` reason over imported rounds. | A Humanize-generated review round can be imported, summarized, and accepted/rejected by the existing review gate without hand-copying review files. | 2026-06-15 |
| IMP-015 | Humanize start wrapper | P1 | todo | Provide a stable user-facing command for starting a real RL infra Humanize task. | Add `make start-humanize-task CONTRACT=... WORKSPACE=...` that runs the IMP-013 preparation flow, prints the Claude Code slash command, records target repo/diff-base metadata, and fails early when the Humanize plugin or Codex CLI is missing. | A user can go from task contract to a ready-to-run Humanize session with one documented command plus one Claude Code slash command. | 2026-06-15 |
| IMP-016 | Full RLCR operator loop | P2 | deferred | Evaluate a near one-command loop from user demand to Claude Builder plus Codex Reviewer iterations. | After IMP-013 to IMP-015 are validated, decide whether to wrap Humanize execution further or keep Claude Code as the interactive loop owner; handle target repo isolation, branch/diff-base policy, open questions, failure recovery, and final delivery reports. | A pilot real task demonstrates end-to-end user demand, task contract, Humanize execution, Codex review import, gate pass, and final handoff without manual artifact copying. | 2026-06-15 |

## Immediate Recommended Sequence

1. Keep `make demo`, `make check`, `make render-example`, and `make review-gate` green after any RLInfraWiki submodule update.
2. Keep `make demo-slime-grpo-contract`, `make demo-rollout-backend-selection`, and `make demo-training-rollout-mismatch-debug` green as the second, third, and fourth golden paths.
3. Use `make validate-source-drift SOURCE_ROOT=..` before changing SourcePack refs from local sibling clones; it now runs strict hash validation.
4. Use `make prepare-humanize-task` for real user tasks that need a Humanize-ready RLCR workspace.
5. Then implement `IMP-014` and `IMP-015` to import Humanize review rounds and expose a stable start command.
6. Promote the next P1 Wiki tracks from `IMP-005` in standalone `RLInfraWiki/`, starting with training backend comparison, after the Humanize bridge has a real-task smoke path.
7. Watch GitHub Actions after each push; fix submodule, dependency, or review-gate drift before expanding content.

## Maintenance Rules

- Keep this file task-level and project-level; do not duplicate every Wiki page row from `docs/rlinfrawiki-content-status.md`.
- Every `done` item should name a command, file, or artifact that proves completion.
- Do not mark GPU/distributed behavior as done unless it has local runtime evidence.
- When a new task contract is added, add or update one row here and one row in the relevant Wiki content status theme if content maturity changes.
