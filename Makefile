.PHONY: setup validate test status indices validate-ledger validate-source-refs validate-source-drift validate-golden-paths check prepare-humanize-task start-humanize-task import-humanize-round render-example review-gate demo render-slime-grpo-contract review-slime-grpo-contract demo-slime-grpo-contract render-rollout-backend-selection review-rollout-backend-selection demo-rollout-backend-selection render-training-rollout-mismatch-debug review-training-rollout-mismatch-debug demo-training-rollout-mismatch-debug

WORKSPACE ?= /tmp/rl-infra-task-workspace
GRPO_WORKSPACE ?= /tmp/slime-grpo-rlvr-data-contract-workspace
ROLLOUT_BACKEND_WORKSPACE ?= /tmp/rollout-backend-selection-workspace
MISMATCH_DEBUG_WORKSPACE ?= /tmp/training-rollout-mismatch-debug-workspace
CONTRACT ?= examples/task_contracts/training-rollout-mismatch-debug.yaml
HUMANIZE_WORKSPACE ?= /tmp/rlinfra-humanize-task-workspace
HUMANIZE_LOOP_DIR ?=
ROUND ?= 1
TARGET_REPO ?=
DIFF_BASE ?= main
PYTHON ?= python
SOURCE_ROOT ?= ..

setup:
	$(PYTHON) -m pip install -e ".[dev]"

validate:
	$(PYTHON) .agents/skills/RLInfraWiki/scripts/validate.py

validate-ledger:
	$(PYTHON) scripts/validate_content_ledger.py

validate-source-refs:
	$(PYTHON) .agents/skills/RLInfraWiki/scripts/verify_source_refs.py --strict-hash

validate-source-drift:
	$(PYTHON) .agents/skills/RLInfraWiki/scripts/verify_source_refs.py --check-local --source-root $(SOURCE_ROOT) --strict-hash

validate-golden-paths:
	$(PYTHON) -m pytest -q tests/test_golden_path_snapshots.py

indices:
	$(PYTHON) .agents/skills/RLInfraWiki/scripts/generate_indices.py

review-gate:
	$(PYTHON) .agents/skills/RLInfraWiki/scripts/validate_review_gate.py --workspace $(WORKSPACE)

check:
	$(PYTHON) .agents/skills/RLInfraWiki/scripts/generate_indices.py --check
	$(PYTHON) .agents/skills/RLInfraWiki/scripts/validate.py
	$(PYTHON) .agents/skills/RLInfraWiki/scripts/verify_source_refs.py --strict-hash
	$(PYTHON) scripts/validate_content_ledger.py
	$(PYTHON) -m pytest -q

status:
	$(PYTHON) .agents/skills/RLInfraWiki/scripts/repo_status.py

prepare-humanize-task:
	$(PYTHON) scripts/prepare_humanize_task.py \
	  --contract "$(CONTRACT)" \
	  --workspace "$(HUMANIZE_WORKSPACE)" \
	  $(if $(TARGET_REPO),--target-repo "$(TARGET_REPO)",) \
	  --diff-base "$(DIFF_BASE)" \
	  --force \
	  --overwrite-human-docs

start-humanize-task:
	$(PYTHON) scripts/start_humanize_task.py \
	  --contract "$(CONTRACT)" \
	  --workspace "$(HUMANIZE_WORKSPACE)" \
	  $(if $(TARGET_REPO),--target-repo "$(TARGET_REPO)",) \
	  --diff-base "$(DIFF_BASE)" \
	  --round "$(ROUND)" \
	  --force \
	  --overwrite-human-docs

import-humanize-round:
	$(PYTHON) scripts/import_humanize_round.py \
	  --workspace "$(HUMANIZE_WORKSPACE)" \
	  $(if $(HUMANIZE_LOOP_DIR),--humanize-loop-dir "$(HUMANIZE_LOOP_DIR)",) \
	  --round "$(ROUND)"

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

render-rollout-backend-selection:
	$(PYTHON) .agents/skills/RLInfraWiki/scripts/render_task_bundle.py \
	  --contract examples/task_contracts/rollout-backend-selection.yaml \
	  --output $(ROLLOUT_BACKEND_WORKSPACE) \
	  --force \
	  --overwrite-human-docs
	$(PYTHON) .agents/skills/RLInfraWiki/scripts/lock_plan.py \
	  --workspace $(ROLLOUT_BACKEND_WORKSPACE)

review-rollout-backend-selection:
	$(PYTHON) .agents/skills/RLInfraWiki/scripts/validate_review_gate.py --workspace $(ROLLOUT_BACKEND_WORKSPACE)

demo-rollout-backend-selection: render-rollout-backend-selection review-rollout-backend-selection
	$(PYTHON) .agents/skills/RLInfraWiki/scripts/query.py "rollout backend selection SGLang vLLM cache logprob weight update" --limit 8
	@echo "Rollout backend selection workspace: $(ROLLOUT_BACKEND_WORKSPACE)"
	@echo "Context bundle: $(ROLLOUT_BACKEND_WORKSPACE)/context/context_bundle.md"

render-training-rollout-mismatch-debug:
	$(PYTHON) .agents/skills/RLInfraWiki/scripts/render_task_bundle.py \
	  --contract examples/task_contracts/training-rollout-mismatch-debug.yaml \
	  --output $(MISMATCH_DEBUG_WORKSPACE) \
	  --force \
	  --overwrite-human-docs
	$(PYTHON) .agents/skills/RLInfraWiki/scripts/lock_plan.py \
	  --workspace $(MISMATCH_DEBUG_WORKSPACE)

review-training-rollout-mismatch-debug:
	$(PYTHON) .agents/skills/RLInfraWiki/scripts/validate_review_gate.py --workspace $(MISMATCH_DEBUG_WORKSPACE)

demo-training-rollout-mismatch-debug: render-training-rollout-mismatch-debug review-training-rollout-mismatch-debug
	$(PYTHON) .agents/skills/RLInfraWiki/scripts/query.py "training rollout mismatch logprob policy_version cache schema drift" --limit 8
	@echo "Training/rollout mismatch debug workspace: $(MISMATCH_DEBUG_WORKSPACE)"
	@echo "Context bundle: $(MISMATCH_DEBUG_WORKSPACE)/context/context_bundle.md"
