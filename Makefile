.PHONY: setup validate test status indices check render-example review-gate demo render-slime-grpo-contract review-slime-grpo-contract demo-slime-grpo-contract

WORKSPACE ?= /tmp/rl-infra-task-workspace
GRPO_WORKSPACE ?= /tmp/slime-grpo-rlvr-data-contract-workspace
PYTHON ?= python

setup:
	$(PYTHON) -m pip install -e ".[dev]"

validate:
	$(PYTHON) .agents/skills/RLInfraWiki/scripts/validate.py

indices:
	$(PYTHON) .agents/skills/RLInfraWiki/scripts/generate_indices.py

review-gate:
	$(PYTHON) .agents/skills/RLInfraWiki/scripts/validate_review_gate.py --workspace $(WORKSPACE)

check:
	$(PYTHON) .agents/skills/RLInfraWiki/scripts/generate_indices.py --check
	$(PYTHON) .agents/skills/RLInfraWiki/scripts/validate.py
	pytest -q

status:
	$(PYTHON) .agents/skills/RLInfraWiki/scripts/repo_status.py

render-example:
	$(PYTHON) .agents/skills/RLInfraWiki/scripts/render_task_bundle.py \
	  --contract examples/task_contracts/slime-weight-sync.yaml \
	  --output $(WORKSPACE) \
	  --force \
	  --overwrite-human-docs
	$(PYTHON) .agents/skills/RLInfraWiki/scripts/lock_plan.py \
	  --workspace $(WORKSPACE)

demo: check render-example review-gate
	$(PYTHON) .agents/skills/RLInfraWiki/scripts/query.py "Megatron SGLang weight sync" --limit 8
	@echo "P0 demo workspace: $(WORKSPACE)"
	@echo "Context bundle: $(WORKSPACE)/context/context_bundle.md"

render-slime-grpo-contract:
	$(PYTHON) .agents/skills/RLInfraWiki/scripts/render_task_bundle.py \
	  --contract examples/task_contracts/slime-grpo-rlvr-data-contract.yaml \
	  --output $(GRPO_WORKSPACE) \
	  --force \
	  --overwrite-human-docs
	$(PYTHON) .agents/skills/RLInfraWiki/scripts/lock_plan.py \
	  --workspace $(GRPO_WORKSPACE)

review-slime-grpo-contract:
	$(PYTHON) .agents/skills/RLInfraWiki/scripts/validate_review_gate.py --workspace $(GRPO_WORKSPACE)

demo-slime-grpo-contract: render-slime-grpo-contract review-slime-grpo-contract
	$(PYTHON) .agents/skills/RLInfraWiki/scripts/query.py "slime GRPO RLVR algorithm data contract" --limit 8
	@echo "Slime GRPO/RLVR data-contract workspace: $(GRPO_WORKSPACE)"
	@echo "Context bundle: $(GRPO_WORKSPACE)/context/context_bundle.md"
