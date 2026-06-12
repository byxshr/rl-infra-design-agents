---
id: comparisons-rollout-backends
title: Rollout Backends
type: comparison
frameworks:
- vllm
- sglang
backends:
- vllm
- sglang
components:
- rollout
- inference
- router
- weight-sync
algorithms:
- rlhf
- grpo
deployment_modes:
- external-service
- disaggregated
tags:
- comparison
- decision-matrix
confidence: inferred
reproducibility: concept
sources:
- repo-vllm-readme
- repo-sglang-readme
- doc-vllm-training-weight-transfer
- doc-sglang-faq-determinism
version_sensitive: []
created_at: '2026-06-12'
updated_at: '2026-06-12'
summary: Compare vLLM and SGLang for RL rollout serving, caching, refit, deterministic
  evaluation, and PD disaggregation.
risks:
- provenance-gap
- observability-gap
---

# Rollout Backends

Compare vLLM and SGLang for RL rollout serving, caching, refit, deterministic evaluation, and PD disaggregation.

## Decision Matrix

| Dimension | Questions to answer |
|---|---|
| Backend fit | Which training and rollout engines are required? |
| Dataflow | How do prompts, trajectories, rewards, and trainer batches move? |
| Weight sync | What is the primary path and fallback path? |
| Async behavior | How are stale policies, delayed rewards, and long-tail rollouts handled? |
| Observability | Which metrics, traces, and evidence logs prove correctness? |

All capability statements on this page are source-reported unless explicitly marked otherwise. Local throughput or quality claims require separate evidence.
