---
id: recipe-design-weight-sync
title: Design Weight Sync
type: recipe
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
- recipe
- playbook
confidence: inferred
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
summary: Review-ready recipe for designing Megatron-to-SGLang weight sync through
  slime, including primary path selection, full checkpoint fallback, version tags,
  cache policy, rollback, and validation evidence.
risks:
- provenance-gap
- rollback-gap
- observability-gap
---

# Design Weight Sync

This recipe is the entry point for the P0 slime + Megatron + SGLang weight sync task. Use it to turn the source evidence into a concrete architecture review packet.

## Evidence Basis

- `system-slime` establishes the runtime lifecycle: create rollout manager, create training models, push initial weights, generate/train, update weights.
- `backend-sglang` establishes the rollout refit APIs: disk, tensor, and distributed group, all with cache/version controls.
- `training-megatron` establishes the training-side concerns: TP/PP/EP/CP, checkpoint conversion, and GRPO examples.
- `weight-sync-overview` and child pages define the sync mode taxonomy and fallback expectations.

## Design Procedure

1. State the exact objective, model family, training backend, rollout backend, and non-goals.
2. Record source IDs and local code paths for every capability claim.
3. Choose one primary sync path:
   - `distributed-group-sync` for disaggregated NCCL broadcast.
   - `tensor-in-memory-sync` for colocated GPU tensor transfer.
   - `delta-weight-sync` only when snapshot baseline, checksum, and full fallback are explicit.
   - `disk-checkpoint-sync` when safety and elastic rollout matter more than sync latency.
4. Always define `full-weight-sync-fallback` through a versioned, immutable checkpoint directory.
5. Specify the pause policy: abort running requests, retract/pause, or wait for generation to drain.
6. Specify cache policy: flush KV/prefix cache, namespace cache by `weight_version`, or explicitly accept stale-cache risk.
7. Specify observability: `training_step_id`, `rollout_id`, `weight_version`, sync mode, cache flush status, engine count, and failure reason.
8. Specify rollback: stop ingesting rollout data on failed update, reload last known-good checkpoint, or destroy/recreate the update group.

## Failure Modes

- Partial update: some engines apply a bucket or checkpoint while others fail.
- Version mismatch: rollout data is trained under a different weight version than the one recorded in the batch.
- Stale cache: cache entries generated under old weights are reused after refit.
- Conversion mismatch: Megatron tensor names or shards do not map to SGLang loader names.
- Deadlock: distributed update group rank offsets or world size differ between trainer and rollout engines.
- Rollback gap: the design has a delta path but no full checkpoint recovery path.

## Validation Ideas

- Run `query.py "Megatron SGLang weight sync" --limit 8` and attach the cited page IDs to the design packet.
- Render the example task bundle and confirm `architecture.md`, `interfaces.md`, `validation_matrix.md`, and `risk_register.md` contain primary path, fallback path, cache policy, and rollback.
- For code review, require at least one evidence bullet from slime, one from SGLang docs, and one from Megatron docs.
- In runtime validation, fail closed if any rollout engine does not confirm the target `weight_version`.

## Open Gaps

- The recipe does not provide measured sync latency or memory overhead.
- Local GPU execution is outside the current project scope; review-ready here means evidence-backed design, not reproduced training.

All capability statements on this page are source-reported unless explicitly marked otherwise. Local throughput or quality claims require separate evidence.
