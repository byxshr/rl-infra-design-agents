---
id: training-fsdp
title: FSDP / FSDP2
type: training
frameworks:
- verl
- areal
backends:
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
- fsdp
- fsdp2
- checkpoint
confidence: source-reported
reproducibility: concept
sources:
- repo-verl-readme
- doc-megatron-fsdp
version_sensitive:
- vs-verl-main-2026-06-12
- vs-megatron-main-2026-06-12
created_at: '2026-06-12'
updated_at: '2026-06-12'
summary: FSDP and FSDP2 are sharded training strategies used by RL frameworks as alternatives
  or complements to Megatron-style parallelism.
risks:
- checkpoint
- version-mismatch
---

# FSDP / FSDP2

Use this page when the design compares Megatron-style model parallelism with sharded data-parallel training backends.

## Design Checks

- Specify how model parameters, optimizer states, gradients, and checkpoints are sharded.
- Check whether rollout backend weight loading expects Hugging Face, distributed checkpoint, or engine-native formats.
- Keep LoRA and quantized rollout paths version-scoped.

All capability statements on this page are source-reported unless explicitly marked otherwise. Local throughput or quality claims require separate evidence.
