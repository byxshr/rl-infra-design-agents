.PHONY: setup validate test status indices check render-example review-gate demo

WORKSPACE ?= /tmp/rl-infra-task-workspace
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
