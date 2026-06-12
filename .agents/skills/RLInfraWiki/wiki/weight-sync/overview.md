---
id: weight-sync-overview
title: Weight Sync Overview
type: weight-sync
frameworks:
- slime
- vllm
- sglang
backends:
- sglang
- vllm
- megatron
components:
- weight-sync
- checkpoint
algorithms:
- rlhf
- grpo
deployment_modes:
- colocated
- disaggregated
tags:
- weight-sync
- checkpoint
confidence: inferred
reproducibility: concept
sources:
- repo-thudm-slime-readme
- doc-sglang-rl-systems
- repo-sglang-readme
version_sensitive:
- vs-slime-main-2026-06-12
- vs-sglang-main-2026-06-12
created_at: '2026-06-12'
updated_at: '2026-06-13'
summary: Overview of Megatron-to-SGLang weight sync through slime, covering disk,
  tensor, distributed-group, delta, full fallback, version tags, cache policy,
  rollback, and observability.
risks:
- partial-weight-update
- version-mismatch
- cache-staleness
- rollback-gap
---

# Weight Sync Overview

This page is the entry map for P0 weight sync. In slime, the trainer updates SGLang rollout engines through dedicated update implementations. SGLang documents matching refit APIs for disk, tensor, and distributed group updates. A design should choose one primary path and always keep a full checkpoint fallback.

## Evidence Basis

- `repo-thudm-slime-readme` / upstream code `../slime/train.py:26` and `../slime/train_async.py:24` push actor weights before rollout begins.
- `../slime/train.py:89` performs synchronous post-train updates; `../slime/train_async.py:65` updates on `args.update_weights_interval` after draining pending generation.
- `../slime/slime/backends/megatron_utils/update_weight/update_weight_from_disk.py:61` implements versioned disk checkpoint sync.
- `../slime/slime/backends/megatron_utils/update_weight/update_weight_from_tensor.py:147` implements colocated in-memory tensor sync.
- `../slime/slime/backends/megatron_utils/update_weight/update_weight_from_distributed.py:102` implements distributed group sync.
- `../slime/slime/backends/megatron_utils/update_weight/update_weight_from_distributed_delta.py:568` implements delta sync with snapshot seeding and finalize.
- `doc-sglang-rl-systems` (`../sglang/docs/advanced_features/sglang_for_rl.md:63`) documents disk, tensor, and distributed SGLang refit strategies.

## Design Implications

- `weight_version` is the contract between trainer, rollout engine, generated data, and review logs.
- Pause/flush/continue is the correctness envelope for any update path that can race with generation.
- Disk sync is the full fallback and recovery path even when the primary path is distributed, tensor, or delta.
- Delta sync reduces transfer volume only if both sides share the same baseline snapshot and verify checksum/application results.
- Cache behavior belongs in the design. The default review posture is to flush KV/prefix cache after weight updates unless the design proves cache namespacing.

## Mode Selection

| mode | best fit | required fallback |
|---|---|---|
| Disk checkpoint sync | Elastic or safest rollout reloads | Last known-good versioned checkpoint |
| Tensor in-memory sync | Colocated trainer and rollout engines | Disk checkpoint sync |
| Distributed group sync | Disaggregated NCCL/IB broadcast | Disk checkpoint sync plus group teardown |
| Delta weight sync | Large models with sparse update deltas and stable baseline | Full checkpoint resync |

## Failure Modes

- Partial update across engines or tensor buckets.
- Stale cache after rollout resumes.
- Weight version not attached to rollout samples.
- Rank/world-size mismatch in distributed update group.
- Delta baseline drift or checksum mismatch.
- Fallback checkpoint is mutable or deleted before rollback.

## Validation Ideas

- For every update, log `training_step_id`, `rollout_id`, `weight_version`, mode, engine count, and cache flush status.
- Compare all rollout engines' recorded `weight_version` after initial sync and after one training update.
- Include one forced-failure review scenario per selected mode and verify fallback behavior.
- Run a small deterministic logprob/cache check when the design depends on exact train/inference probability alignment.

## Open Gaps

- This page does not include measured sync latency, memory pressure, or throughput.
- Endpoint-level SGLang implementation paths are not yet indexed; current source boundary is SGLang docs plus slime caller code.

All capability statements on this page are source-reported unless explicitly marked otherwise. Local throughput or quality claims require separate evidence.
