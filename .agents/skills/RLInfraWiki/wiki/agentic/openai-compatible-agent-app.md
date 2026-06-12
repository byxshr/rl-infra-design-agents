---
id: agentic-openai-compatible-agent-app
title: OpenAI-Compatible Agent App
type: agentic
frameworks:
- areal
backends:
- openai-compatible
components:
- environment
- rollout
- reward
algorithms:
- rlvr
deployment_modes:
- external-service
- async
tags:
- agentic
- tool-calling
- multi-turn
confidence: inferred
reproducibility: concept
sources:
- repo-inclusionai-areal-readme
- repo-thudm-slime-readme
- repo-verl-readme
- repo-alibaba-roll-readme
version_sensitive:
- vs-areal-main-2026-06-12
- vs-slime-main-2026-06-12
- vs-verl-main-2026-06-12
- vs-roll-main-2026-06-12
created_at: '2026-06-12'
updated_at: '2026-06-12'
summary: OpenAI-compatible agent apps let existing agent runtimes connect through
  base_url style proxy patterns.
risks:
- reward-delay
- long-tail-rollout
- stale-policy
---

# OpenAI-Compatible Agent App

OpenAI-compatible agent apps let existing agent runtimes connect through base_url style proxy patterns.

## Design Checks

- Define environment API separately from trainer API.
- Store tool calls, observations, sampled tokens, rewards, and failure state.
- Specify timeout, retry, cancellation, and partial trajectory behavior.
- Track policy version for every rollout segment.

All capability statements on this page are source-reported unless explicitly marked otherwise. Local throughput or quality claims require separate evidence.
