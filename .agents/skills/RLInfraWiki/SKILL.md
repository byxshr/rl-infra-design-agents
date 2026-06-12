---
name: RLInfraWiki
description: Use this skill for researching or designing RL/RLHF/RLVR/agentic-RL infrastructure involving slime, verl, AReaL, ROLL, vLLM, SGLang, Megatron-LM, rollout engines, training backends, weight synchronization, async pipelines, Ray multi-role orchestration, data buffers, reward services, tool-calling environments, or training-inference mismatch debugging.
---

# RLInfraWiki

Use this skill before proposing architecture or implementation plans for RL infrastructure tasks.

## Required workflow

1. Start with a broad query:
   ```bash
   python3 .agents/skills/RLInfraWiki/scripts/query.py "<topic>" --limit 8
   ```
2. Read relevant pages:
   ```bash
   python3 .agents/skills/RLInfraWiki/scripts/get_page.py <page-id> --follow-sources
   ```
3. Use grep for exact APIs, flags, or framework names:
   ```bash
   python3 .agents/skills/RLInfraWiki/scripts/grep_wiki.py "update_weights_from_distributed"
   ```
4. When making a design decision, cite page IDs, source IDs, confidence level, version sensitivity, and known gaps.

## Confidence levels

- `verified`: reproduced locally or checked against upstream code plus official docs.
- `source-reported`: stated by upstream README, docs, paper, blog, or release note.
- `inferred`: reasoned from multiple sources but not directly stated.
- `experimental`: observed in examples, issues, branches, or incomplete docs.
