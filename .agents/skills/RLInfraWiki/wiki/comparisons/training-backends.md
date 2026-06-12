---
id: comparisons-training-backends
title: Training Backends
type: comparison
frameworks:
- verl
- areal
- roll
- megatron-lm
backends:
- megatron
- fsdp
components:
- training
- checkpoint
algorithms:
- ppo
- grpo
deployment_modes:
- colocated
- disaggregated
tags:
- comparison
- decision-matrix
confidence: inferred
reproducibility: concept
sources:
- repo-nvidia-megatron-lm-readme
- repo-verl-readme
- doc-megatron-fsdp
version_sensitive: []
created_at: '2026-06-12'
updated_at: '2026-06-12'
summary: Compare Megatron, Megatron-FSDP, FSDP/FSDP2, and framework-specific training
  backends.
risks:
- provenance-gap
- observability-gap
---

# Training Backends

Compare Megatron, Megatron-FSDP, FSDP/FSDP2, and framework-specific training backends.

## Decision Matrix

| Dimension | Questions to answer |
|---|---|
| Backend fit | Which training and rollout engines are required? |
| Dataflow | How do prompts, trajectories, rewards, and trainer batches move? |
| Weight sync | What is the primary path and fallback path? |
| Async behavior | How are stale policies, delayed rewards, and long-tail rollouts handled? |
| Observability | Which metrics, traces, and evidence logs prove correctness? |

All capability statements on this page are source-reported unless explicitly marked otherwise. Local throughput or quality claims require separate evidence.
