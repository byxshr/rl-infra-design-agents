---
id: comparisons-rl-frameworks
title: RL Frameworks
type: comparison
frameworks:
- slime
- verl
- areal
- roll
backends:
- sglang
- vllm
- megatron
- fsdp
components:
- training
- rollout
- weight-sync
- scheduler
algorithms:
- ppo
- grpo
- rlvr
deployment_modes:
- colocated
- disaggregated
- async
- ray-multirole
tags:
- comparison
- decision-matrix
confidence: inferred
reproducibility: concept
sources:
- repo-thudm-slime-readme
- repo-verl-readme
- repo-inclusionai-areal-readme
- repo-alibaba-roll-readme
version_sensitive: []
created_at: '2026-06-12'
updated_at: '2026-06-12'
summary: Compare slime, verl, AReaL, and ROLL by backend choices, orchestration style,
  async support, and agentic workflow fit.
risks:
- provenance-gap
- observability-gap
---

# RL Frameworks

Compare slime, verl, AReaL, and ROLL by backend choices, orchestration style, async support, and agentic workflow fit.

## Decision Matrix

| Dimension | Questions to answer |
|---|---|
| Backend fit | Which training and rollout engines are required? |
| Dataflow | How do prompts, trajectories, rewards, and trainer batches move? |
| Weight sync | What is the primary path and fallback path? |
| Async behavior | How are stale policies, delayed rewards, and long-tail rollouts handled? |
| Observability | Which metrics, traces, and evidence logs prove correctness? |

All capability statements on this page are source-reported unless explicitly marked otherwise. Local throughput or quality claims require separate evidence.
