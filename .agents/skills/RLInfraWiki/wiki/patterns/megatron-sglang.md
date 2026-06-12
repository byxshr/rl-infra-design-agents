---
id: pattern-megatron-sglang
title: Megatron plus SGLang
type: pattern
frameworks:
- slime
backends:
- megatron
- sglang
components:
- training
- rollout
- weight-sync
algorithms:
- ppo
- grpo
deployment_modes:
- colocated
- disaggregated
tags:
- pattern
- architecture
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
summary: Pattern for a Megatron trainer and SGLang rollout engines connected by
  slime weight sync, with explicit conversion, cache, version, fallback, and
  rollback boundaries.
risks:
- stale-policy
- version-mismatch
- observability-gap
---

# Megatron plus SGLang

Use this pattern when Megatron owns training state and SGLang owns rollout generation. slime is the integration layer that connects the two with Ray actors and one of four weight sync paths: disk, tensor, distributed group, or delta.

## Use When

- The task objective names these frameworks or components.
- The acceptance criteria require explicit failure modes, rollback, and observability.
- The rollout and training surfaces have different latency, memory, or scaling needs.

## Evidence Basis

- `system-slime` cites `../slime/train.py:26` and `../slime/train_async.py:24` for mandatory initial weight push into rollout engines.
- `weight-sync-distributed-group-sync` cites `../slime/slime/backends/megatron_utils/update_weight/update_weight_from_distributed.py:102` for pause -> flush -> bucket broadcast -> continue.
- `weight-sync-disk-checkpoint-sync` cites `../slime/slime/backends/megatron_utils/update_weight/update_weight_from_disk.py:61` for versioned checkpoint directory publication.
- `weight-sync-delta-weight-sync` cites `../slime/slime/backends/megatron_utils/update_weight/update_weight_from_distributed_delta.py:568` for seeded snapshot followed by diff/encode/finalize.
- `backend-sglang` cites `../sglang/docs/advanced_features/sglang_for_rl.md:63` and later endpoint sections for SGLang refit APIs.
- `training-megatron` cites `../Megatron-LM/examples/rl/README.md:36` and `:66` for checkpoint conversion and TP/PP settings.

## Design Implications

- Define the trainer-to-rollout boundary in terms of parameter names, tensor shapes, dtypes, load format, and `weight_version`.
- Pick one primary sync path and one full checkpoint fallback. Delta is never enough by itself because initial snapshot, receiver drift, or checksum mismatch needs recovery.
- Pause and cache-flush semantics are design decisions, not implementation details; they determine whether rollout data is on-policy enough for review.
- Keep SGLang routing and PD disaggregation separate from weight sync. A correct weight update can still be hidden by router affinity or mixed-version engines.

## Validation Ideas

- Version monotonicity test.
- Cache flush or cache namespace test.
- Rollout/train logprob mismatch smoke test.
- Failure injection for sync timeout or partial reward.

## Failure Modes

- NCCL group mismatch causes rollout engines to wait forever for a broadcast.
- HF conversion changes names or splits expert tensors differently from SGLang's loader expectation.
- The rollout manager resumes generation before every engine confirms the same `weight_version`.
- Delta updates apply against the wrong baseline snapshot.
- Disk fallback points at a mutable checkpoint directory and reloads a half-written model.

## Open Gaps

- No local run has validated the complete Megatron -> slime -> SGLang chain on GPUs.
- The pattern does not yet cover vLLM as an alternate rollout backend; that belongs to the P1 rollout backend selection track.

All capability statements on this page are source-reported unless explicitly marked otherwise. Local throughput or quality claims require separate evidence.
