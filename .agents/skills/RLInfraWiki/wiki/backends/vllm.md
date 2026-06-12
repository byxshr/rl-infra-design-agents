---
id: backend-vllm
title: vLLM
type: backend
frameworks:
- vllm
backends:
- vllm
components:
- rollout
- inference
- weight-sync
- router
algorithms:
- rlhf
- grpo
deployment_modes:
- external-service
- disaggregated
tags:
- vllm
- pagedattention
- prefix-caching
- openai-compatible
confidence: source-reported
reproducibility: concept
sources:
- repo-vllm-readme
- doc-vllm-training-weight-transfer
version_sensitive:
- vs-vllm-main-2026-06-12
created_at: '2026-06-12'
updated_at: '2026-06-12'
summary: vLLM provides LLM serving features including PagedAttention, continuous batching,
  chunked prefill, prefix caching, OpenAI-compatible serving, and RL weight transfer
  docs.
risks:
- nondeterminism
- cache-staleness
- version-mismatch
---

# vLLM

vLLM is a strong rollout backend candidate when the design needs general serving, OpenAI-compatible APIs, prefix caching, chunked prefill, or pluggable weight transfer for RL workflows.

## Design Checks

- Identify whether the task uses offline generation, online HTTP serving, or a colocated trainer/engine.
- Specify weight transfer control plane, data plane, version tags, pause/resume behavior, and rollback.
- Treat performance claims as workload- and hardware-sensitive.

All capability statements on this page are source-reported unless explicitly marked otherwise. Local throughput or quality claims require separate evidence.
