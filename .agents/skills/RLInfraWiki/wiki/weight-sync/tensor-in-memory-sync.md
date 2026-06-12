---
id: weight-sync-tensor-in-memory-sync
title: Tensor In-Memory Sync
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
- colocated
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
summary: Tensor in-memory sync is the colocated slime path that converts Megatron
  local weights to HF tensors and sends them to SGLang engines through IPC and
  optional distributed fallback, with cache and version controls.
risks:
- partial-weight-update
- version-mismatch
- cache-staleness
- rollback-gap
---

# Tensor In-Memory Sync

Tensor in-memory sync is a colocated optimization. It avoids a full checkpoint write and avoids creating a large trainer-to-rollout NCCL group for colocated engines, but it only works when tensor lifetime, device residency, and engine ownership are controlled.

## Evidence Basis

- `repo-thudm-slime-readme` / upstream code `../slime/slime/backends/megatron_utils/update_weight/update_weight_from_tensor.py:24` defines `UpdateWeightFromTensor`.
- `../slime/slime/backends/megatron_utils/update_weight/update_weight_from_tensor.py:147` increments `weight_version`, pauses generation, and flushes rollout caches.
- `../slime/slime/backends/megatron_utils/update_weight/update_weight_from_tensor.py:170` obtains Megatron local weights through `weights_getter`.
- `../slime/slime/backends/megatron_utils/update_weight/update_weight_from_tensor.py:172` iterates HF-converted chunks and sends them to engines.
- `../slime/slime/backends/megatron_utils/update_weight/update_weight_from_tensor.py:176` and `:183` call CUDA IPC cleanup after engine consumption.
- `../slime/slime/backends/megatron_utils/update_weight/update_weight_from_tensor.py:200` forwards `weight_version` through the colocated send path.
- `doc-sglang-rl-systems` (`../sglang/docs/advanced_features/sglang_for_rl.md:143`) documents SGLang `POST /update_weights_from_tensor` with serialized tensors, `load_format`, `flush_cache`, and `weight_version`.

## Design Implications

- Use this mode when trainer and rollout engines are colocated enough to share tensor/IPC semantics safely.
- Keep tensors GPU-resident until engines finish applying them; premature free can corrupt or fail IPC consumption.
- Tensor mode still needs disk fallback because it has no durable external recovery point.
- The design must name the `load_format` and tensor naming convention expected by SGLang.

## Failure Modes

- Tensor lifetime ends before rollout engines finish reading.
- CPU offload or host copy changes the expected in-memory update path.
- IPC handles leak or stale handles accumulate after failures.
- Dtype/shape/name metadata diverges from SGLang's loader expectation.
- Cache is not flushed after applying tensors.

## Validation Ideas

- Confirm one small tensor update returns from every engine before freeing long-lived tensors.
- Log CUDA IPC cleanup completion and engine acknowledgement for the target `weight_version`.
- Run with `flush_cache=true` first; only relax this after a deterministic mismatch check.
- Include disk fallback for any failed tensor update.

## Open Gaps

- No local colocated GPU smoke run was executed.
- Page does not yet cover vLLM tensor transfer details; that belongs to the P1 rollout backend selection track.

All capability statements on this page are source-reported unless explicitly marked otherwise. Local throughput or quality claims require separate evidence.
