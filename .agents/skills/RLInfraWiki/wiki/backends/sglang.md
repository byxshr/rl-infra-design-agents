---
id: backend-sglang
title: SGLang
type: backend
frameworks:
- sglang
backends:
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
- sglang
- radixattention
- prefix-caching
- pd-disaggregation
confidence: source-reported
reproducibility: concept
sources:
- repo-sglang-readme
- doc-sglang-faq-determinism
- doc-sglang-pd-disaggregation
version_sensitive:
- vs-sglang-main-2026-06-12
created_at: '2026-06-12'
updated_at: '2026-06-12'
summary: SGLang provides RadixAttention prefix caching, runtime serving features,
  PD disaggregation, router paths, deterministic inference guidance, and RL/post-training
  adoption.
risks:
- nondeterminism
- cache-staleness
- partial-weight-update
---

# SGLang

SGLang is a strong rollout backend candidate when the design needs SGLang-specific serving, routing, caching, PD disaggregation, or RL refit behavior.

## Design Checks

- Decide whether prefix cache should be preserved, flushed, or scoped by weight version.
- For deterministic RL evaluation, document batching, cache, and deterministic inference settings.
- For PD disaggregation, treat prefill, decode, router, and KV-transfer failure as separate surfaces.

All capability statements on this page are source-reported unless explicitly marked otherwise. Local throughput or quality claims require separate evidence.
