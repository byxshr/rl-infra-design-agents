---
id: weight-sync-distributed-group-sync
title: Distributed Group Sync
type: weight-sync
frameworks:
- slime
- vllm
- sglang
backends:
- vllm
- sglang
components:
- weight-sync
algorithms:
- rlhf
deployment_modes:
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
summary: Distributed group sync uses a dedicated NCCL group between slime training
  ranks and SGLang rollout engines, broadcasting HF-converted Megatron weight
  buckets with explicit group, lock, cache, and version boundaries.
risks:
- partial-weight-update
- version-mismatch
- cache-staleness
- rollback-gap
---

# Distributed Group Sync

Distributed group sync is the primary disaggregated path when trainer and rollout GPUs can join a dedicated communication group. It avoids checkpoint I/O but makes rank mapping, group lifetime, and deadlock handling part of the design contract.

## Evidence Basis

- `repo-thudm-slime-readme` / upstream code `../slime/slime/backends/megatron_utils/update_weight/update_weight_from_distributed.py:23` defines `UpdateWeightFromDistributed`.
- `../slime/slime/backends/megatron_utils/update_weight/update_weight_from_distributed.py:55` creates `slime-pp_{pp_rank}` groups only on PP source ranks.
- `../slime/slime/backends/megatron_utils/update_weight/update_weight_from_distributed.py:102` pauses generation, flushes cache, sends weights, and resumes generation.
- `../slime/slime/backends/megatron_utils/update_weight/update_weight_from_distributed.py:155` gathers non-expert TP parameters and converts them to HF chunks.
- `../slime/slime/backends/megatron_utils/update_weight/update_weight_from_distributed.py:183` handles expert parameters through EP gather and HF conversion.
- `../slime/slime/backends/megatron_utils/update_weight/update_weight_from_distributed.py:247` uses a rollout engine lock before bucket broadcast to avoid deadlock.
- `../slime/slime/backends/megatron_utils/update_weight/update_weight_from_distributed.py:295` creates the NCCL group with rank offsets and total world size.
- `../slime/slime/backends/megatron_utils/update_weight/update_weight_from_distributed.py:335` sends metadata via Ray and broadcasts tensors through NCCL.
- `doc-sglang-rl-systems` (`../sglang/docs/advanced_features/sglang_for_rl.md:172`, `:187`, `:202`) documents init, update, and destroy endpoints for distributed weight update groups.

## Design Implications

- The design must include group name, master address/port selection, rank offsets, world size, backend, and teardown.
- TP and EP are separate conversion/gather concerns. MoE models need explicit expert-parameter handling in review.
- Bucket size (`--update-weight-buffer-size`) affects sync granularity and partial-update risk.
- A lock is part of correctness because concurrent broadcasts can deadlock rollout engines.
- Disk checkpoint sync remains the recovery path if group initialization or broadcast fails.

## Failure Modes

- Rank offset or engine GPU count mismatch leaves engines waiting in NCCL.
- A timeout after some buckets land creates partial weights unless rollout ingestion is stopped.
- PP source rank assumptions break when the deployment changes pipeline topology.
- Expert parameters are skipped or converted under the wrong EP grouping.
- Destroy group is missed after failure, poisoning later sync attempts.

## Validation Ideas

- Review a concrete rank map: trainer rank 0 plus every rollout engine GPU and offset.
- Smoke the endpoint lifecycle: init group, update one small bucket, destroy group.
- Log bucket count, target `weight_version`, group name, and engine count for each update.
- Add a failure-injection review case for lock acquisition timeout or NCCL broadcast timeout.

## Open Gaps

- No local multi-node NCCL run was executed for this page.
- RLInfraWiki does not yet capture cluster-specific timeout/retry policies.

All capability statements on this page are source-reported unless explicitly marked otherwise. Local throughput or quality claims require separate evidence.
