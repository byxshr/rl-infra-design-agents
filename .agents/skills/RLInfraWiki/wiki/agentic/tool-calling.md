---
id: agentic-tool-calling
title: Tool Calling
type: agentic
frameworks:
- areal
- slime
- verl
- roll
backends:
- openai-compatible
- sglang
- vllm
components:
- environment
- reward
- rollout
algorithms:
- rlvr
- grpo
deployment_modes:
- async
- external-service
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
summary: Tool-calling RL needs transcript capture, token/logprob attribution, timeout
  handling, and reward provenance.
risks:
- reward-delay
- long-tail-rollout
- stale-policy
---

# Tool Calling

Tool-calling RL needs transcript capture, token/logprob attribution, timeout handling, and reward provenance.

## Design Checks

- Define environment API separately from trainer API.
- Store tool calls, observations, sampled tokens, rewards, and failure state.
- Specify timeout, retry, cancellation, and partial trajectory behavior.
- Track policy version for every rollout segment.

All capability statements on this page are source-reported unless explicitly marked otherwise. Local throughput or quality claims require separate evidence.
