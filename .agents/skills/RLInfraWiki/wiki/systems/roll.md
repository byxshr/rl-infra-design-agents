---
id: system-roll
title: ROLL
type: system
frameworks:
- roll
backends:
- ray
- vllm
- sglang
- megatron-lm
components:
- training
- rollout
- reward
- scheduler
algorithms:
- ppo
- grpo
- rlvr
deployment_modes:
- ray-multirole
- async
tags:
- roll
- ray
- agentic
- rlvr
confidence: source-reported
reproducibility: concept
sources:
- repo-alibaba-roll-readme
version_sensitive:
- vs-roll-main-2026-06-12
created_at: '2026-06-12'
updated_at: '2026-06-12'
summary: ROLL is a Ray-based multi-role RL library for RLVR and agentic pipelines
  with Megatron-Core, SGLang, and vLLM integration.
risks:
- observability-gap
- long-tail-rollout
- rollback-gap
---

# ROLL

ROLL is a useful reference when designing Ray multi-role worker placement, RLVR reward roles, and agentic asynchronous rollout.

## Design Notes

- Keep actor_train, actor_infer, reference, reward, and validation roles explicit.
- Ray scheduling and resource placement are part of the architecture, not deployment afterthoughts.
- RLVR reward functions should have local debugging and evidence paths.

All capability statements on this page are source-reported unless explicitly marked otherwise. Local throughput or quality claims require separate evidence.
