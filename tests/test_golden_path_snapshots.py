from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "golden_path_expectations.yaml"
RENDER = ROOT / ".agents" / "skills" / "RLInfraWiki" / "scripts" / "render_task_bundle.py"
LOCK = ROOT / ".agents" / "skills" / "RLInfraWiki" / "scripts" / "lock_plan.py"
REVIEW_GATE = ROOT / ".agents" / "skills" / "RLInfraWiki" / "scripts" / "validate_review_gate.py"

AFFIRMATIVE_RUNTIME_CLAIM_RE = re.compile(
    r"\b(?:gpu|nccl|performance|production|throughput|latency)\b[^\n]{0,40}"
    r"\b(?:verified|validated|reproduced)\b",
    re.IGNORECASE,
)
NON_CLAIM_PATTERNS = [
    re.compile(r"\bunverified\b[^\n]{0,80}\b(?:gpu|nccl|performance|production|throughput|latency)\b", re.IGNORECASE),
    re.compile(
        r"\b(?:gpu|nccl|performance|production|throughput|latency)\b[^\n]{0,40}"
        r"\b(?:verified|validated|reproduced)\b[^\n]{0,30}[:=]\s*(?:false|no|none|pending)\b",
        re.IGNORECASE,
    ),
    re.compile(r"\bsource-reported\b[^\n]{0,80}\b(?:verified|validated|reproduced)\b", re.IGNORECASE),
    re.compile(r"\bnot\s+(?:locally\s+)?(?:verified|validated|reproduced)\b", re.IGNORECASE),
]


def load_expectations() -> list[dict]:
    data = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    paths = data.get("golden_paths")
    assert isinstance(paths, list)
    return paths


# Load at collection time so a malformed fixture fails before any expensive rendering starts.
GOLDEN_PATHS = load_expectations()


def run_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=ROOT, text=True, capture_output=True)


def assert_command_passes(args: list[str]) -> None:
    result = run_command(args)
    assert result.returncode == 0, result.stdout + result.stderr


def find_affirmative_runtime_claim(text: str) -> str | None:
    for line in text.splitlines():
        match = AFFIRMATIVE_RUNTIME_CLAIM_RE.search(line)
        if match and not any(pattern.search(line) for pattern in NON_CLAIM_PATTERNS):
            return match.group(0)
    return None


def test_golden_path_expectations_are_well_formed():
    names = [item["name"] for item in GOLDEN_PATHS]
    assert len(names) == 4
    assert len(names) == len(set(names))

    for item in GOLDEN_PATHS:
        contract = ROOT / item["contract"]
        assert contract.exists(), item["contract"]
        assert item["workspace"]
        assert set(item["required_context_files"]) == {
            "context/context_bundle.md",
            "context/context_bundle.json",
            "context/context_sources.yaml",
        }
        assert item["scan_files"]
        assert item["must_contain"]
        assert item["must_not_contain"]


def test_affirmative_runtime_claim_guard_catches_rephrased_claims():
    assert find_affirmative_runtime_claim("GPU was verified locally on cluster A") == "GPU was verified"
    assert find_affirmative_runtime_claim("performance is validated by benchmark X") == "performance is validated"


def test_affirmative_runtime_claim_guard_allows_explicit_non_claims():
    assert find_affirmative_runtime_claim("GPU verified locally: false") is None
    assert find_affirmative_runtime_claim("performance verified: pending local artifact") is None
    assert find_affirmative_runtime_claim("Source-reported throughput was validated upstream only") is None
    assert find_affirmative_runtime_claim("not locally verified performance result") is None


def test_affirmative_runtime_claim_guard_rejects_ambiguous_negation_lines():
    assert find_affirmative_runtime_claim("GPU verified on workload A (not B)") == "GPU verified"
    assert find_affirmative_runtime_claim("GPU verified by team X but no benchmark logs") == "GPU verified"
    assert find_affirmative_runtime_claim("NCCL validated, latency unless beyond 100ms") == "NCCL validated"
    assert find_affirmative_runtime_claim("performance was verified, source-reported elsewhere") == "performance was verified"
    assert find_affirmative_runtime_claim("production verified at scale; pending public release") == "production verified"


@pytest.mark.parametrize("expectation", GOLDEN_PATHS, ids=[item["name"] for item in GOLDEN_PATHS])
def test_golden_path_rendered_workspace_keeps_key_semantics(tmp_path, expectation):
    workspace = tmp_path / expectation["workspace"]
    contract = ROOT / expectation["contract"]

    assert_command_passes(
        [
            sys.executable,
            str(RENDER),
            "--contract",
            str(contract),
            "--output",
            str(workspace),
            "--force",
            "--overwrite-human-docs",
        ]
    )
    assert_command_passes([sys.executable, str(LOCK), "--workspace", str(workspace)])
    assert_command_passes([sys.executable, str(REVIEW_GATE), "--workspace", str(workspace)])

    for rel_path in expectation["required_context_files"]:
        assert (workspace / rel_path).exists(), rel_path

    rendered_parts = []
    for rel_path in expectation["scan_files"]:
        path = workspace / rel_path
        assert path.exists(), rel_path
        rendered_parts.append(path.read_text(encoding="utf-8"))
    rendered = "\n".join(rendered_parts)

    for needle in expectation["must_contain"]:
        assert needle in rendered, f"{expectation['name']} missing {needle!r}"
    for needle in expectation["must_not_contain"]:
        assert needle not in rendered, f"{expectation['name']} unexpectedly contains {needle!r}"

    claim = find_affirmative_runtime_claim(rendered)
    assert claim is None, f"{expectation['name']} contains unverified runtime claim {claim!r}"
