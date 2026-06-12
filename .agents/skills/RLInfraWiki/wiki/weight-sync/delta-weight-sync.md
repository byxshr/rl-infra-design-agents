---
id: weight-sync-delta-weight-sync
title: Delta Weight Sync
type: weight-sync
frameworks:
- slime
backends:
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
summary: Delta weight sync sends encoded changed positions and values after a seeded
  baseline snapshot, using either NCCL or disk transport, and requires checksum,
  version, metrics, and full checkpoint resync safeguards.
risks:
- partial-weight-update
- version-mismatch
- cache-staleness
- rollback-gap
---

# Delta Weight Sync

Delta weight sync is an optimization path, not a standalone recovery strategy. It is useful when full checkpoints are too expensive and most weights are unchanged or sparsely changed, but it only works if sender and receiver share the same baseline snapshot and can verify each delta application.

## Evidence Basis

- `repo-thudm-slime-readme` / upstream code `../slime/slime/backends/megatron_utils/update_weight/update_weight_from_distributed_delta.py:479` subclasses the distributed sync path as `UpdateWeightFromDistributedDelta`.
- `../slime/slime/backends/megatron_utils/update_weight/update_weight_from_distributed_delta.py:568` seeds a CPU snapshot on the first call and performs real engine RPCs only on later calls.
- `../slime/slime/backends/megatron_utils/update_weight/update_weight_from_distributed_delta.py:583` creates a version directory for disk transport.
- `../slime/slime/backends/megatron_utils/update_weight/update_weight_from_distributed_delta.py:588` pauses generation and flushes rollout caches before computing deltas.
- `../slime/slime/backends/megatron_utils/update_weight/update_weight_from_distributed_delta.py:625` splits non-expert and expert passes, with expert sub-passes to avoid a single end-of-sync bottleneck.
- `../slime/slime/backends/megatron_utils/update_weight/update_weight_from_distributed_delta.py:690` computes diffs, updates the snapshot, encodes sparse payloads, and counts density/wire bytes.
- `../slime/slime/backends/megatron_utils/update_weight/update_weight_from_distributed_delta.py:714` broadcasts `__positions__` and `__values__` with `load_format="delta"` for NCCL transport or writes safetensors files for disk transport.
- `../slime/slime/backends/megatron_utils/update_weight/update_weight_from_distributed_delta.py:857` records density, wire bytes, flush counts, and disk compression metrics.
- `doc-sglang-rl-systems` documents the underlying SGLang disk and distributed update APIs used by slime's delta transports.

## Design Implications

- Delta sync must name its baseline seeding moment. Rollout data before and after the seed should not be mixed without version labels.
- A full checkpoint resync is mandatory when checksum, baseline, or receiver apply state is suspect.
- Delta transport choice matters: NCCL keeps payload on the communication group; disk creates versioned delta files and async publish/finalize behavior.
- Metrics such as density, wire bytes, flush count, and compression ratio should be part of observability, because delta benefit is workload-dependent.
- Expert-parameter handling is part of the design for MoE models; sub-pass count and barriers affect progress and failure surfaces.

## Failure Modes

- Receiver applies a delta against the wrong baseline snapshot.
- Checksum mismatch is ignored and rollout resumes with corrupted weights.
- All-zero or tiny updates advance trainer state without updating engine version.
- Disk delta files are published before durability or visibility on the shared filesystem.
- Delta density grows until the optimization is slower or riskier than full sync.

## Validation Ideas

- Force the first call to seed snapshot, then require the next update to carry a new `weight_version`.
- Log delta density, wire bytes, flushes per rank, and transport for every update.
- Inject checksum mismatch in review and verify the design falls back to full checkpoint sync.
- Periodically perform a full checkpoint resync to bound baseline drift.

## Open Gaps

- No local benchmark establishes that delta sync is faster for the target model.
- RLInfraWiki does not yet document SGLang receiver-side delta loader internals.

All capability statements on this page are source-reported unless explicitly marked otherwise. Local throughput or quality claims require separate evidence.
