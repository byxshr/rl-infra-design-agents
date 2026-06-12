---
id: comparisons-orchestration-options
title: Orchestration Options
type: comparison
frameworks:
- slime
- verl
- areal
- roll
backends:
- ray
- openai-compatible
components:
- scheduler
- training
- rollout
- reward
algorithms:
- rlvr
deployment_modes:
- ray-multirole
- async
- external-service
tags:
- comparison
- decision-matrix
confidence: inferred
reproducibility: concept
sources:
- repo-alibaba-roll-readme
- repo-inclusionai-areal-readme
- repo-thudm-slime-readme
version_sensitive: []
created_at: '2026-06-12'
updated_at: '2026-06-12'
summary: Compare controller-worker, Ray multi-role, fully async, and external service
  orchestration.
risks:
- provenance-gap
- observability-gap
---

# Orchestration Options

Compare controller-worker, Ray multi-role, fully async, and external service orchestration.

## Decision Matrix

| Dimension | Questions to answer |
|---|---|
| Backend fit | Which training and rollout engines are required? |
| Dataflow | How do prompts, trajectories, rewards, and trainer batches move? |
| Weight sync | What is the primary path and fallback path? |
| Async behavior | How are stale policies, delayed rewards, and long-tail rollouts handled? |
| Observability | Which metrics, traces, and evidence logs prove correctness? |

All capability statements on this page are source-reported unless explicitly marked otherwise. Local throughput or quality claims require separate evidence.
