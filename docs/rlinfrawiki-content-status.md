# RLInfraWiki Content Status

## Purpose

This file tracks RLInfraWiki content maturity for future content implementation work. It is a maintenance ledger for wiki quality, not a task workspace, benchmark log, or source of implementation artifacts.

Use it to answer:

- Which pages are still placeholders or thin summaries.
- Which pages already have enough metadata to be queried but still lack code-level evidence.
- Which content themes should be implemented first.
- What the next agent should inspect before editing a page.

The canonical content is now the standalone top-level `RLInfraWiki/` repository. The main repo consumes it at `.agents/skills/RLInfraWiki/` as a pinned gitlink/submodule-style dependency. Older references to `.agents/skills/RLInfraWiki/` describe the mounted dependency path, not the canonical authoring location.

`docs/RLInfraWiki独立仓库改进方案_v1_1.md` is the final execution plan for this migration. `docs/RLInfraWiki独立仓库改进方案_v1.md` is retained only as background and non-conflicting supplemental detail.

## Status Taxonomy

| status | meaning | promotion requirement |
|---|---|---|
| `stub` | Category README or very thin placeholder that cannot support a design decision. | Add frontmatter-backed page content or decide that the file should stay a navigational placeholder. |
| `indexed` | Has frontmatter, summary, sources, risks, and can be found by `query.py`, but lacks code-level evidence. | Add local code paths, function/config names, source-doc paths, design implications, failure modes, and validation ideas. |
| `code-evidenced` | Cites SourcePack source IDs/source refs, upstream commits, repo-relative paths, line ranges, claim IDs, functions/configs, or official doc paths that substantiate the design notes. | Add review-ready structure: design implications, failure modes, validation plan, open gaps, and source boundary notes. |
| `review-ready` | Can directly support architecture/design review with code evidence, design tradeoffs, failure modes, validation ideas, and open gaps. | Keep refreshed with upstream version claims and prevent unverified performance claims. |

## Theme Roadmap

| theme | priority | current_status | target_status | pages | next_action |
|---|---|---|---|---:|---|
| slime + Megatron + SGLang weight sync | P0 | review-ready | review-ready | 11 | Use the P0 pages for task-bundle review; refresh source paths after upstream changes or local GPU validation. |
| RL infra dictionary and context bundle | P0 | review-ready | review-ready | 76 | Maintain concept/capability/interface/algorithm/framework-profile/failure/validation/adapter pages and context-bundle quality gates in standalone `RLInfraWiki/`. |
| rollout backend selection | P1 | indexed | code-evidenced | 7 | Add vLLM/SGLang API and failure-mode evidence for rollout backend selection. |
| async agentic RL | P1 | indexed | code-evidenced | 6 | Add AReaL/ROLL/verl/slime agentic rollout and async lifecycle evidence. |
| Ray orchestration and multi-role pipelines | P1 | indexed | code-evidenced | 3 | Add ROLL/Ray role, placement, and lifecycle evidence. |
| training backend comparison | P1 | indexed | code-evidenced | 2 | Add Megatron/FSDP code and config evidence, especially checkpoint and parallelism boundaries. |
| observability and mismatch debugging | P2 | indexed | code-evidenced | 2 | Add concrete metrics, logprob mismatch checks, deterministic inference, and evidence paths. |
| migration and general playbooks | P2 | indexed | code-evidenced | 2 | Add cross-page references and example task outputs after primary themes mature. |
| category navigation pages | P2 | stub | indexed | 4 | Decide whether to keep as README-only navigation or convert to real indexed pages. |

## Page Inventory

| page_id | path | type | theme | current_status | target_status | priority | evidence_gaps | next_action | last_reviewed |
|---|---|---|---|---|---|---|---|---|---|
| category-algorithms-readme | wiki/algorithms/README.md | category-readme | category navigation pages | stub | indexed | P2 | No frontmatter or substantive algorithm taxonomy. | Add algorithm overview or keep as navigation-only and exclude from maturity goals. | 2026-06-12 |
| category-data-buffer-readme | wiki/data-buffer/README.md | category-readme | category navigation pages | stub | indexed | P1 | No Data Buffer code evidence or lifecycle notes. | Expand from slime rollout buffer code and Data Buffer docs. | 2026-06-12 |
| category-orchestration-readme | wiki/orchestration/README.md | category-readme | category navigation pages | stub | indexed | P1 | No Ray/multi-role orchestration map. | Add ROLL/Ray and slime placement-group pointers. | 2026-06-12 |
| category-rollout-readme | wiki/rollout/README.md | category-readme | category navigation pages | stub | indexed | P1 | No rollout backend taxonomy. | Add SGLang/vLLM rollout lifecycle overview. | 2026-06-12 |
| agentic-multi-turn-env | wiki/agentic/multi-turn-env.md | agentic | async agentic RL | indexed | code-evidenced | P1 | Missing code paths for multi-turn state, partial rollout, and long-tail handling. | Inspect AReaL/ROLL/slime agentic examples and cite concrete rollout state APIs. | 2026-06-12 |
| agentic-openai-compatible-agent-app | wiki/agentic/openai-compatible-agent-app.md | agentic | async agentic RL | indexed | code-evidenced | P1 | Missing OpenAI-compatible app proxy code and request lifecycle evidence. | Add AReaL black-box app and SGLang/OpenAI API references. | 2026-06-12 |
| agentic-tool-calling | wiki/agentic/tool-calling.md | agentic | async agentic RL | indexed | code-evidenced | P1 | Missing tool-call schema, environment loop, and reward/verifier code evidence. | Add local source paths for tool-call rollout examples and verifier hooks. | 2026-06-12 |
| backend-sglang | wiki/backends/sglang.md | backend | slime + Megatron + SGLang weight sync | review-ready | review-ready | P0 | Code/doc evidence added for SGLang refit APIs, cache flush, deterministic inference, and RL lifecycle; still lacks local GPU reproduction. | Use as the SGLang rollout/refit backend reference and refresh after SGLang API changes. | 2026-06-13 |
| backend-vllm | wiki/backends/vllm.md | backend | rollout backend selection | indexed | code-evidenced | P1 | Missing concrete vLLM weight transfer and serving API evidence. | Add code/doc paths from vLLM weight transfer docs and compare with SGLang refit path. | 2026-06-12 |
| comparisons-orchestration-options | wiki/comparisons/orchestration-options.md | comparison | Ray orchestration and multi-role pipelines | indexed | code-evidenced | P1 | Missing Ray role topology and placement evidence. | Cite ROLL and slime placement-group lifecycle paths. | 2026-06-12 |
| comparisons-rl-frameworks | wiki/comparisons/rl-frameworks.md | comparison | migration and general playbooks | indexed | code-evidenced | P2 | Missing code-level comparison across slime, verl, AReaL, and ROLL. | Add comparison matrix grounded in local source manifests and key entrypoints. | 2026-06-12 |
| comparisons-rollout-backends | wiki/comparisons/rollout-backends.md | comparison | rollout backend selection | indexed | code-evidenced | P1 | Missing SGLang/vLLM API-level differences and failure modes. | Add refit, cache, router, and determinism evidence from both backends. | 2026-06-12 |
| comparisons-training-backends | wiki/comparisons/training-backends.md | comparison | training backend comparison | indexed | code-evidenced | P1 | Missing FSDP/Megatron code evidence and checkpoint/parallelism tradeoffs. | Cite Megatron Core docs, Megatron RL example, and FSDP references. | 2026-06-12 |
| migration-kda-to-rl-infra | wiki/migrations/kda-to-rl-infra.md | migration | migration and general playbooks | indexed | code-evidenced | P2 | Missing concrete before/after examples from rendered task workspaces. | Add references to example task contracts and rendered workspace artifacts. | 2026-06-12 |
| observability-debug-playbook | wiki/observability/debug-playbook.md | observability | observability and mismatch debugging | indexed | code-evidenced | P2 | Missing concrete metrics, logs, and failure injection evidence. | Add validation matrix examples and framework-specific metrics paths. | 2026-06-12 |
| observability-training-inference-mismatch | wiki/observability/training-inference-mismatch.md | observability | observability and mismatch debugging | indexed | code-evidenced | P1 | Missing logprob mismatch, deterministic inference, and cache-hit test evidence. | Cite SGLang deterministic inference docs and test utilities for logprob/cache checks. | 2026-06-12 |
| pattern-async-rollout | wiki/patterns/async-rollout.md | pattern | async agentic RL | indexed | code-evidenced | P1 | Missing async train loop, update interval, and stale-policy evidence. | Add SourcePack refs for slime `train_async.py` plus AReaL/ROLL async lifecycle paths. | 2026-06-12 |
| pattern-colocated-train-rollout | wiki/patterns/colocated-train-rollout.md | pattern | rollout backend selection | indexed | code-evidenced | P1 | Missing memory/offload, sleep/wake, and colocated sync evidence. | Add SGLang sleep/wake and slime colocated lifecycle references. | 2026-06-12 |
| pattern-disaggregated-train-rollout | wiki/patterns/disaggregated-train-rollout.md | pattern | rollout backend selection | indexed | code-evidenced | P1 | Missing distributed group, disk fallback, and version boundary evidence. | Cite slime distributed/disk update paths and SGLang refit docs. | 2026-06-12 |
| pattern-megatron-sglang | wiki/patterns/megatron-sglang.md | pattern | slime + Megatron + SGLang weight sync | review-ready | review-ready | P0 | Cross-page evidence added for Megatron conversion, slime update paths, SGLang refit, cache, version, and fallback; still lacks end-to-end GPU run. | Use as the architecture pattern for P0 review packets. | 2026-06-13 |
| pattern-pd-disaggregation | wiki/patterns/pd-disaggregation.md | pattern | rollout backend selection | indexed | code-evidenced | P1 | Missing SGLang PD deployment and router evidence. | Add PD docs, prefill/decode failure surfaces, and route-level validation ideas. | 2026-06-12 |
| pattern-ray-multirole | wiki/patterns/ray-multirole.md | pattern | Ray orchestration and multi-role pipelines | indexed | code-evidenced | P1 | Missing Ray actor/placement lifecycle evidence. | Cite ROLL role setup and slime placement-group creation paths. | 2026-06-12 |
| recipe-design-agentic-rl-pipeline | wiki/recipes/design-agentic-rl-pipeline.md | recipe | async agentic RL | indexed | code-evidenced | P1 | Missing code-grounded steps for agent app, environment, verifier, and rollout buffer. | Add concrete checklist from AReaL/ROLL/slime agentic examples. | 2026-06-12 |
| recipe-design-weight-sync | wiki/recipes/design-weight-sync.md | recipe | slime + Megatron + SGLang weight sync | review-ready | review-ready | P0 | Review-ready checklist added for primary path, full fallback, version tags, cache policy, rollback, and validation; still lacks runtime benchmark criteria. | Use as the entry recipe for render-example and RLCR context review. | 2026-06-13 |
| recipe-select-stack | wiki/recipes/select-stack.md | recipe | rollout backend selection | indexed | code-evidenced | P1 | Missing source-grounded decision matrix for framework/backend combinations. | Add decision tree for slime/verl/AReaL/ROLL with SGLang/vLLM/Megatron evidence. | 2026-06-12 |
| system-areal | wiki/systems/areal.md | system | async agentic RL | indexed | code-evidenced | P1 | Missing fully async RL, black-box app, and backend selection code evidence. | Inspect AReaL local clone for async training and OpenAI-compatible app paths. | 2026-06-12 |
| system-roll | wiki/systems/roll.md | system | Ray orchestration and multi-role pipelines | indexed | code-evidenced | P1 | Missing Ray multi-role architecture and backend integration code evidence. | Inspect ROLL local clone for role definitions, worker setup, and SGLang/vLLM integration. | 2026-06-12 |
| system-slime | wiki/systems/slime.md | system | slime + Megatron + SGLang weight sync | review-ready | review-ready | P0 | Code evidence added for training loops, rollout manager ordering, update paths, Data Buffer, and async update interval; still lacks tracing of the arg-to-update-class selector. | Use as the slime system reference and backfill selector details in a later pass. | 2026-06-13 |
| system-verl | wiki/systems/verl.md | system | rollout backend selection | indexed | code-evidenced | P1 | Missing worker/controller, SGLang/vLLM backend, and memory/offload evidence. | Inspect verl local clone for SGLang worker and backend selection surfaces. | 2026-06-12 |
| training-fsdp | wiki/training/fsdp.md | training | training backend comparison | indexed | code-evidenced | P1 | Missing concrete FSDP/FSDP2 config and checkpoint boundaries. | Add Megatron/verl FSDP docs and worker code evidence. | 2026-06-12 |
| training-megatron | wiki/training/megatron.md | training | slime + Megatron + SGLang weight sync | review-ready | review-ready | P0 | Megatron RL example, checkpoint conversion, TP/PP, and FSDP checkpoint evidence added; still lacks executed checkpoint conversion. | Use as trainer-side evidence and add conversion dry-run if a task requires it. | 2026-06-13 |
| weight-sync-delta-weight-sync | wiki/weight-sync/delta-weight-sync.md | weight-sync | slime + Megatron + SGLang weight sync | review-ready | review-ready | P0 | Evidence added for snapshot seed, checksum, disk/NCCL transport, metrics, and fallback requirements; still lacks performance validation. | Use only with explicit full checkpoint resync and checksum validation in task designs. | 2026-06-13 |
| weight-sync-disk-checkpoint-sync | wiki/weight-sync/disk-checkpoint-sync.md | weight-sync | slime + Megatron + SGLang weight sync | review-ready | review-ready | P0 | Evidence added for versioned directory lifecycle, pause/flush, SGLang disk reload, cleanup, and filesystem failure modes; cluster durability policy remains task-specific. | Use as the required full fallback page for P0 designs. | 2026-06-13 |
| weight-sync-distributed-group-sync | wiki/weight-sync/distributed-group-sync.md | weight-sync | slime + Megatron + SGLang weight sync | review-ready | review-ready | P0 | Evidence added for NCCL group creation, rank offsets, TP/EP gather, bucket broadcast, lock, and teardown; no local NCCL smoke run yet. | Use as the primary disaggregated sync page when task hardware supports NCCL groups. | 2026-06-13 |
| weight-sync-full-weight-sync-fallback | wiki/weight-sync/full-weight-sync-fallback.md | weight-sync | slime + Megatron + SGLang weight sync | review-ready | review-ready | P0 | Evidence added for fallback trigger, recovery sequence, version confirmation, cache flush, and rollout ingestion stop; automated enforcement is still future work. | Require this page in any design that selects tensor, distributed, or delta primary sync. | 2026-06-13 |
| weight-sync-overview | wiki/weight-sync/overview.md | weight-sync | slime + Megatron + SGLang weight sync | review-ready | review-ready | P0 | Unified taxonomy added for disk, tensor, distributed, delta, fallback, versioning, cache, rollback, and observability; no measured sync cost. | Use as the first page for the P0 weight-sync content track. | 2026-06-13 |
| weight-sync-tensor-in-memory-sync | wiki/weight-sync/tensor-in-memory-sync.md | weight-sync | slime + Megatron + SGLang weight sync | review-ready | review-ready | P0 | Evidence added for tensor iterator, HF conversion chunks, CUDA IPC cleanup, SGLang tensor refit, and cache invalidation; no local colocated GPU smoke run. | Use for colocated designs only with disk fallback and tensor lifetime checks. | 2026-06-13 |
