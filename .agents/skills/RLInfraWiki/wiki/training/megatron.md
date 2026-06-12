---
id: training-megatron
title: Megatron-LM / Megatron Core
type: training
frameworks:
- megatron-lm
backends:
- megatron
components:
- training
- checkpoint
algorithms:
- rlhf
- grpo
deployment_modes:
- colocated
- disaggregated
tags:
- megatron-lm
- tp
- pp
- dp
- ep
- cp
confidence: source-reported
reproducibility: concept
sources:
- repo-nvidia-megatron-lm-readme
version_sensitive:
- vs-megatron-main-2026-06-12
created_at: '2026-06-12'
updated_at: '2026-06-12'
summary: Megatron Core provides transformer training building blocks, TP/PP/DP/EP/CP
  parallelism, mixed precision, checkpointing, and RL examples.
risks:
- version-mismatch
- rollback-gap
---

# Megatron-LM / Megatron Core

Megatron is the training backend reference for large model parallelism and checkpoint conversion concerns.

## Design Checks

- Record tensor, pipeline, data, expert, and context parallel choices.
- Specify checkpoint format and conversion path between trainer and rollout backend.
- Include rollback on checkpoint conversion or weight-transfer failure.

All capability statements on this page are source-reported unless explicitly marked otherwise. Local throughput or quality claims require separate evidence.
