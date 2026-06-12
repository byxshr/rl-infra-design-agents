---
id: system-slime
title: slime
type: system
frameworks:
- slime
backends:
- sglang
- megatron
components:
- training
- rollout
- data-buffer
- weight-sync
- router
algorithms:
- ppo
- grpo
deployment_modes:
- colocated
- disaggregated
- async
tags:
- slime
- sglang
- megatron-lm
- weight-sync
- agentic
confidence: source-reported
reproducibility: concept
sources:
- repo-thudm-slime-readme
- doc-sglang-rl-systems
- repo-sglang-readme
- repo-nvidia-megatron-lm-readme
version_sensitive:
- vs-slime-main-2026-06-12
- vs-sglang-main-2026-06-12
- vs-megatron-main-2026-06-12
created_at: '2026-06-12'
updated_at: '2026-06-13'
summary: slime wires Megatron training to SGLang rollout through Ray-managed rollout
  managers and explicit update_weights paths, including disk, tensor, distributed,
  and delta variants with version and cache boundaries.
risks:
- partial-weight-update
- version-mismatch
- long-tail-rollout
---

# slime

slime is the integration spine for the P0 design. It creates rollout engines, creates Megatron-backed training models, and pushes actor weights into rollout engines before and during training. A design using slime should preserve those framework-specific control points instead of hiding them behind a generic "serving backend" abstraction.

## Evidence Basis

- `repo-thudm-slime-readme` / upstream code `../slime/train.py:15` creates the rollout manager first, then creates training models at `../slime/train.py:20`.
- `../slime/train.py:26` pushes actor weights once initial weights are loaded; `../slime/train.py:89` updates weights again after each train step in the synchronous loop.
- `../slime/train_async.py:24` performs the initial push, and `../slime/train_async.py:65` gates later updates on `args.update_weights_interval` after waiting for in-flight generation.
- `../slime/slime/backends/megatron_utils/update_weight/update_weight_from_disk.py:61` implements full checkpoint sync through a versioned directory and `engine.update_weights_from_disk`.
- `../slime/slime/backends/megatron_utils/update_weight/update_weight_from_distributed.py:102` implements pause -> flush -> send -> continue for NCCL distributed updates.
- `../slime/slime/backends/megatron_utils/update_weight/update_weight_from_tensor.py:147` implements a colocated tensor path with CUDA IPC cleanup.
- `../slime/slime/backends/megatron_utils/update_weight/update_weight_from_distributed_delta.py:568` implements delta sync after an initial snapshot seed.
- `../slime/slime_plugins/rollout_buffer/README.md:5` and `../slime/slime_plugins/rollout_buffer/buffer.py:325` show the Data Buffer / remote rollout entrypoint for asynchronous agent trajectory generation.

## Design Implications

- The rollout manager is a lifecycle dependency, because the trainer needs rollout engine handles before it can connect weight update paths.
- Initial weight push is mandatory. A task plan should not wait for the first optimizer step before synchronizing rollout engines.
- Async training must avoid updating weights in the middle of generation; slime already waits for pending generation before the interval-based update.
- The selected sync mode must be reflected in the validation matrix because disk, tensor, distributed, and delta paths have different rollback and observability surfaces.
- Data Buffer is a separate agentic rollout surface; it should not be mixed into core weight sync unless the task explicitly needs asynchronous external trajectory generation.

## Risks

- Version mismatch between trainer and rollout when `weight_version` is missing from logs.
- Stale cache when rollout engines continue using KV/prefix cache built under older weights.
- Partial update if Ray or NCCL fails after some buckets land.
- Long-tail rollout in async paths delaying the next safe update window.
- Data Buffer producing trajectories under a weight version different from the one used for training.

## Validation Ideas

- Assert the initial `actor_model.update_weights()` path is exercised before first rollout.
- Log `rollout_id`, `training_step_id`, `weight_version`, sync mode, and cache flush status for every update.
- Run a small `check_weights` or equivalent compare action after initial sync when enabled by the task contract.
- Inject one failed update in design review and confirm the plan falls back to disk checkpoint sync or stops rollout ingestion.

## Open Gaps

- RLInfraWiki has not yet traced slime's actor model class that selects a specific update implementation from args.
- No local distributed smoke run has validated the Ray/NCCL behavior; current claims are source-reported from code reading.

All capability statements on this page are source-reported unless explicitly marked otherwise. Local throughput or quality claims require separate evidence.
