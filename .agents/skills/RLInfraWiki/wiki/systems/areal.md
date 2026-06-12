---
id: system-areal
title: AReaL
type: system
frameworks:
- areal
backends:
- sglang
- vllm
- fsdp
- megatron
components:
- training
- rollout
- environment
- reward
- scheduler
algorithms:
- ppo
- grpo
- dapo
- rloo
deployment_modes:
- async
- external-service
tags:
- areal
- agentic
- async
- openai-compatible
confidence: source-reported
reproducibility: concept
sources:
- repo-inclusionai-areal-readme
version_sensitive:
- vs-areal-main-2026-06-12
created_at: '2026-06-12'
updated_at: '2026-06-12'
summary: AReaL focuses on fully asynchronous RL and agentic workflows, including OpenAI-compatible
  application integration.
risks:
- stale-policy
- reward-delay
- long-tail-rollout
---

# AReaL

AReaL is useful when the task centers on fully asynchronous agentic RL, online proxy patterns, or existing agent applications reachable through OpenAI-compatible APIs.

## Design Notes

- Model rollout as asynchronous workflow execution with explicit policy version tracking.
- Separate agent runtime API from trainer API.
- Track delayed rewards, hanging tools, partial trajectories, and stale policy.

All capability statements on this page are source-reported unless explicitly marked otherwise. Local throughput or quality claims require separate evidence.
