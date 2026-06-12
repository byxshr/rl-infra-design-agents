---
id: observability-debug-playbook
title: Debug Playbook
type: observability
frameworks:
- slime
- verl
- areal
- roll
backends:
- sglang
- vllm
- megatron
components:
- observability
- reward
- rollout
algorithms:
- rlvr
- grpo
deployment_modes:
- async
- disaggregated
tags:
- observability
- debug
confidence: inferred
reproducibility: concept
sources:
- repo-thudm-slime-readme
- repo-verl-readme
- repo-inclusionai-areal-readme
- repo-alibaba-roll-readme
version_sensitive:
- vs-slime-main-2026-06-12
- vs-verl-main-2026-06-12
- vs-areal-main-2026-06-12
- vs-roll-main-2026-06-12
created_at: '2026-06-12'
updated_at: '2026-06-12'
summary: Debugging RL infra needs small repros, replayable trajectories, versioned
  weights, metrics, traces, and evidence logs.
risks:
- observability-gap
- version-mismatch
- nondeterminism
---

# Debug Playbook

Debugging RL infra needs small repros, replayable trajectories, versioned weights, metrics, traces, and evidence logs.

## Evidence To Collect

- Exact command and config.
- Source and target weight version.
- Prompt, response, token IDs, logprobs, reward, and route metadata.
- Rollout backend flags affecting cache, batching, and determinism.
- Failure logs and rollback action.

All capability statements on this page are source-reported unless explicitly marked otherwise. Local throughput or quality claims require separate evidence.
