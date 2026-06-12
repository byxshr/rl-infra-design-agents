# Topic Map

> Auto-generated. Do not edit manually.

- `agentic-multi-turn-env`: [Multi-Turn Environment](../wiki/agentic/multi-turn-env.md) - Multi-turn environments require state, session affinity, cache/version handling, and partial trajectory rules.
- `agentic-openai-compatible-agent-app`: [OpenAI-Compatible Agent App](../wiki/agentic/openai-compatible-agent-app.md) - OpenAI-compatible agent apps let existing agent runtimes connect through base_url style proxy patterns.
- `agentic-tool-calling`: [Tool Calling](../wiki/agentic/tool-calling.md) - Tool-calling RL needs transcript capture, token/logprob attribution, timeout handling, and reward provenance.
- `backend-sglang`: [SGLang](../wiki/backends/sglang.md) - SGLang provides RadixAttention prefix caching, runtime serving features, PD disaggregation, router paths, deterministic inference guidance, and RL/post-training adoption.
- `backend-vllm`: [vLLM](../wiki/backends/vllm.md) - vLLM provides LLM serving features including PagedAttention, continuous batching, chunked prefill, prefix caching, OpenAI-compatible serving, and RL weight transfer docs.
- `comparisons-orchestration-options`: [Orchestration Options](../wiki/comparisons/orchestration-options.md) - Compare controller-worker, Ray multi-role, fully async, and external service orchestration.
- `comparisons-rl-frameworks`: [RL Frameworks](../wiki/comparisons/rl-frameworks.md) - Compare slime, verl, AReaL, and ROLL by backend choices, orchestration style, async support, and agentic workflow fit.
- `comparisons-rollout-backends`: [Rollout Backends](../wiki/comparisons/rollout-backends.md) - Compare vLLM and SGLang for RL rollout serving, caching, refit, deterministic evaluation, and PD disaggregation.
- `comparisons-training-backends`: [Training Backends](../wiki/comparisons/training-backends.md) - Compare Megatron, Megatron-FSDP, FSDP/FSDP2, and framework-specific training backends.
- `migration-kda-to-rl-infra`: [KDA To RL Infra](../wiki/migrations/kda-to-rl-infra.md) - Map KDA workflow concepts to RL infrastructure design workspaces: wiki query, draft, plan, candidate, validation, evidence, review, and promotion.
- `observability-debug-playbook`: [Debug Playbook](../wiki/observability/debug-playbook.md) - Debugging RL infra needs small repros, replayable trajectories, versioned weights, metrics, traces, and evidence logs.
- `observability-training-inference-mismatch`: [Training Inference Mismatch](../wiki/observability/training-inference-mismatch.md) - Mismatch debugging compares rollout logprobs, trainer logprobs, tokenization, routing, precision, and policy versions.
- `pattern-async-rollout`: [Async Rollout](../wiki/patterns/async-rollout.md) - Pattern for asynchronous rollout where generation, tools, rewards, and training update do not advance in lockstep.
- `pattern-colocated-train-rollout`: [Colocated Train Rollout](../wiki/patterns/colocated-train-rollout.md) - Pattern for shared GPU pools where trainer and rollout engine sleep, wake, or share memory.
- `pattern-disaggregated-train-rollout`: [Disaggregated Train Rollout](../wiki/patterns/disaggregated-train-rollout.md) - Pattern for separate training and rollout resources with explicit weight version and transport boundary.
- `pattern-megatron-sglang`: [Megatron plus SGLang](../wiki/patterns/megatron-sglang.md) - Pattern for Megatron trainer plus SGLang rollout/router with explicit data buffer and weight sync.
- `pattern-pd-disaggregation`: [Prefill Decode Disaggregation](../wiki/patterns/pd-disaggregation.md) - Pattern for separating prefill and decode resources, with router and KV-transfer failure surfaces.
- `pattern-ray-multirole`: [Ray Multi-Role](../wiki/patterns/ray-multirole.md) - Pattern for explicit Ray roles such as actor_train, actor_infer, reference, reward, and validation.
- `recipe-design-agentic-rl-pipeline`: [Design Agentic RL Pipeline](../wiki/recipes/design-agentic-rl-pipeline.md) - Recipe for designing agentic RL sample lifecycle, tool runtime, reward aggregation, stale policy controls, and observability.
- `recipe-design-weight-sync`: [Design Weight Sync](../wiki/recipes/design-weight-sync.md) - Recipe for designing primary weight sync path, full fallback path, version tags, cache policy, and rollback.
- `recipe-select-stack`: [Select Stack](../wiki/recipes/select-stack.md) - Recipe for selecting framework, trainer, rollout backend, orchestration, and validation strategy.
- `system-areal`: [AReaL](../wiki/systems/areal.md) - AReaL focuses on fully asynchronous RL and agentic workflows, including OpenAI-compatible application integration.
- `system-roll`: [ROLL](../wiki/systems/roll.md) - ROLL is a Ray-based multi-role RL library for RLVR and agentic pipelines with Megatron-Core, SGLang, and vLLM integration.
- `system-slime`: [slime](../wiki/systems/slime.md) - slime is an LLM post-training framework centered on Megatron training, SGLang rollout/router, and a Data Buffer path.
- `system-verl`: [verl](../wiki/systems/verl.md) - verl exposes modular RL dataflows with multiple training and rollout backends.
- `training-fsdp`: [FSDP / FSDP2](../wiki/training/fsdp.md) - FSDP and FSDP2 are sharded training strategies used by RL frameworks as alternatives or complements to Megatron-style parallelism.
- `training-megatron`: [Megatron-LM / Megatron Core](../wiki/training/megatron.md) - Megatron Core provides transformer training building blocks, TP/PP/DP/EP/CP parallelism, mixed precision, checkpointing, and RL examples.
- `weight-sync-delta-weight-sync`: [Delta Weight Sync](../wiki/weight-sync/delta-weight-sync.md) - Send changed weight positions or buckets instead of full checkpoints when source and receiver share compatible semantics.
- `weight-sync-disk-checkpoint-sync`: [Disk Checkpoint Sync](../wiki/weight-sync/disk-checkpoint-sync.md) - Use shared filesystem or object storage to publish full checkpoints or update files to rollout backends.
- `weight-sync-distributed-group-sync`: [Distributed Group Sync](../wiki/weight-sync/distributed-group-sync.md) - Use NCCL or distributed collectives when trainer and rollout groups can form a compatible update group.
- `weight-sync-full-weight-sync-fallback`: [Full Weight Sync Fallback](../wiki/weight-sync/full-weight-sync-fallback.md) - Keep a full checkpoint fallback for delta, tensor, or distributed-group update paths.
- `weight-sync-tensor-in-memory-sync`: [Tensor In-Memory Sync](../wiki/weight-sync/tensor-in-memory-sync.md) - Transfer tensors directly when trainer and rollout engines can share process, device, IPC, or colocated communication paths.
- `weight-sync-overview`: [Weight Sync Overview](../wiki/weight-sync/overview.md) - Overview of checkpoint, tensor, distributed-group, delta, fallback, version tagging, cache policy, and rollback choices.
