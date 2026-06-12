---
id: backend-sglang
title: SGLang
type: backend
frameworks:
- sglang
backends:
- sglang
components:
- rollout
- inference
- router
- weight-sync
algorithms:
- rlhf
- grpo
deployment_modes:
- external-service
- disaggregated
tags:
- sglang
- radixattention
- prefix-caching
- pd-disaggregation
confidence: source-reported
reproducibility: concept
sources:
- repo-sglang-readme
- doc-sglang-rl-systems
- doc-sglang-faq-determinism
- doc-sglang-pd-disaggregation
version_sensitive:
- vs-sglang-main-2026-06-12
created_at: '2026-06-12'
updated_at: '2026-06-13'
summary: SGLang is the rollout/refit backend for the P0 slime + Megatron path, with
  documented disk, tensor, and distributed weight update APIs plus cache flush,
  sleep/wake, deterministic inference, PD, and router surfaces.
risks:
- nondeterminism
- cache-staleness
- partial-weight-update
---

# SGLang

SGLang is the rollout/refit backend for the P0 slime + Megatron weight sync path. Treat it as an inference engine with explicit lifecycle APIs, not as a passive model loader: the design must say when generation pauses, which weight update API is used, whether KV/prefix cache is flushed, and how `weight_version` is observed.

## Evidence Basis

- `doc-sglang-rl-systems` (`../sglang/docs/advanced_features/sglang_for_rl.md:23`) documents memory-aware sleep/wake for RL loops and states that releasing KV cache causes later requests to rebuild it.
- `doc-sglang-rl-systems` (`../sglang/docs/advanced_features/sglang_for_rl.md:63`) lists three refit strategies: disk, tensor, and distributed group.
- `doc-sglang-rl-systems` (`../sglang/docs/advanced_features/sglang_for_rl.md:82`, `:143`, `:172`, `:187`) documents `POST /update_weights_from_disk`, `POST /update_weights_from_tensor`, `POST /init_weights_update_group`, and `POST /update_weights_from_distributed`.
- `doc-sglang-rl-systems` (`../sglang/docs/advanced_features/sglang_for_rl.md:97`, `:151`, `:197`) includes `flush_cache` fields on weight update paths and `weight_version` fields on disk/tensor/distributed requests.
- `doc-sglang-faq-determinism` and `../sglang/docs/advanced_features/deterministic_inference.md:150` provide deterministic inference and radix-cache consistency test hooks for mismatch debugging.

## Design Implications

- Disk refit is the safest fallback because the checkpoint directory is an external source of truth and can bootstrap newly added rollout engines.
- Tensor refit is a colocated optimization and should only be selected when tensor ownership, GPU residency, and IPC/serialization boundaries are explicit.
- Distributed refit is the natural match for disaggregated slime rollout because training workers and rollout engines can join a dedicated NCCL group, but the design must include group creation and teardown.
- Cache policy is part of correctness. If updated weights change token probabilities, stale KV/prefix cache can invalidate rollout/train logprob comparison.
- PD disaggregation and Model Gateway routing add separate failure domains; prefill, decode, router health, and cache transfer should be monitored independently.

## Failure Modes

- Updating while requests are still running can create partial-version generations unless the scheduler is paused or requests are aborted.
- `flush_cache=false` can preserve throughput but risks stale-policy behavior after weight changes.
- A distributed group with mismatched rank offsets, world size, or backend can deadlock or leave engines waiting for tensors.
- Tensor updates can silently fail at the design level if dtype/shape/name lists do not match the engine loader expectation.
- Deterministic evaluation claims can be invalidated by dynamic batching, cache reuse, or non-deterministic sampling settings.

## Validation Ideas

- Exercise one disk update with `weight_version="smoke-v1"` and verify every rollout engine reports or logs the new version before accepting rollout data.
- For distributed refit, validate `init_weights_update_group` -> `update_weights_from_distributed` -> `destroy_weights_update_group` in one smoke run and fail closed on any Ray/NCCL timeout.
- Run a small cached-vs-uncached logprob check with deterministic inference settings when the design depends on reward or policy logprob equality.
- Record whether `flush_cache` was true for each weight update in the rollout metrics/log bundle.

## Open Gaps

- No local GPU run has verified SGLang latency, memory, or quality behavior for this project.
- RLInfraWiki does not yet index SGLang implementation symbols behind each HTTP endpoint; current evidence is official local docs plus slime caller code.

All capability statements on this page are source-reported unless explicitly marked otherwise. Local throughput or quality claims require separate evidence.
