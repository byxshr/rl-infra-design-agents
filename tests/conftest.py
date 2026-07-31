from __future__ import annotations

import json
from pathlib import Path

import pytest


GUIDANCE_CORPUS = """\
safe\tA tracked plan must live outside `.humanize/`.
safe\t`.humanize/` is correctly untracked in the target repository.
safe\tThe gate blocks any commit of `.humanize/`.
safe\tThe importer must track review issues, and `.humanize/` stays local.
unsafe\tPlease stage `.humanize/rlcr` before review.
unsafe\tRun `git add -f .` to include everything.
unsafe\t1. Stage `.humanize/rlcr` before the next round.
unsafe\t2. Commit `.humanize/` so the reviewer can see it.
unsafe\t- **Stage** `.humanize/rlcr` first.
unsafe\tThe fix is to commit `.humanize/rlcr`.
unsafe\tI recommend committing `.humanize/` state.
unsafe\tPlease also stage `.humanize/rlcr`.
unsafe\tAdd `.humanize/rlcr` to the index.
unsafe\tYou have to commit `.humanize/` for this to work.
unsafe\tTrack `.humanize/rlcr` in Git.
"""


def create_compatible_humanize_runtime(root: Path) -> Path:
    files = {
        ".claude-plugin/plugin.json": json.dumps({"name": "humanize", "version": "test-fixture"}) + "\n",
        "prompt-template/codex/gate-invariants-section.md": (
            "Contract: humanize-gate-invariants-v1\nHumanize Gate Verdict: PASS\n"
        ),
        "prompt-template/codex/gate-guidance-corpus.tsv": GUIDANCE_CORPUS,
        "prompt-template/codex/regular-review.md": "{{HUMANIZE_GATE_INVARIANTS_SECTION}}\n",
        "prompt-template/codex/full-alignment-review.md": "{{HUMANIZE_GATE_INVARIANTS_SECTION}}\n",
        "prompt-template/codex/code-review-phase.md": "{{HUMANIZE_GATE_INVARIANTS_SECTION}}\n",
        "hooks/loop-codex-stop-hook.sh": (
            "source review-contract.sh\n"
            "validate_humanize_gate_review_file result.md\n"
            "codex review --base main -\n"
        ),
        "hooks/lib/review-contract.sh": (
            'HUMANIZE_GATE_CONTRACT_ID="humanize-gate-invariants-v1"\n'
        ),
    }
    for relative_path, content in files.items():
        path = root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    return root


@pytest.fixture
def compatible_humanize_root(tmp_path: Path) -> Path:
    return create_compatible_humanize_runtime(tmp_path / "compatible-humanize")
