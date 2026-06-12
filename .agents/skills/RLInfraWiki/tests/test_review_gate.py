import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def render_locked_workspace(tmp_path):
    ws = tmp_path / "task"
    subprocess.run([
        sys.executable, str(ROOT / ".agents/skills/RLInfraWiki/scripts/render_task_bundle.py"),
        "--contract", str(ROOT / "examples/task_contracts/slime-weight-sync.yaml"),
        "--output", str(ws),
    ], check=True, cwd=ROOT)
    subprocess.run([sys.executable, str(ROOT / ".agents/skills/RLInfraWiki/scripts/lock_plan.py"), "--workspace", str(ws)], check=True, cwd=ROOT)
    return ws


def run_gate(ws):
    return subprocess.run(
        [sys.executable, str(ROOT / ".agents/skills/RLInfraWiki/scripts/validate_review_gate.py"), "--workspace", str(ws)],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )


def test_review_gate_blocks_p1(tmp_path):
    ws = render_locked_workspace(tmp_path)
    issue = {"id": "review-test-p1", "round_id": "round-001", "severity": "P1", "status": "open", "summary": "missing validation"}
    (ws / "review_issues.jsonl").write_text(json.dumps(issue) + "\n")
    result = run_gate(ws)
    assert result.returncode == 1
    assert "unresolved P1" in result.stdout


def test_review_gate_blocks_p1_waiver(tmp_path):
    ws = render_locked_workspace(tmp_path)
    issue = {"id": "review-test-p1-waived", "round_id": "round-001", "severity": "P1", "status": "waived", "summary": "missing validation"}
    waiver = {"id": "waiver-test", "issue_id": "review-test-p1-waived", "status": "approved", "approved_by": "human", "reason": "not allowed for P1"}
    (ws / "review_issues.jsonl").write_text(json.dumps(issue) + "\n")
    (ws / "review_waivers.jsonl").write_text(json.dumps(waiver) + "\n")
    result = run_gate(ws)
    assert result.returncode == 1
    assert "unresolved P1" in result.stdout


def test_review_gate_rejects_unknown_severity(tmp_path):
    ws = render_locked_workspace(tmp_path)
    issue = {"id": "review-test-p9", "round_id": "round-001", "severity": "P9", "status": "open", "summary": "typo"}
    (ws / "review_issues.jsonl").write_text(json.dumps(issue) + "\n")
    result = run_gate(ws)
    assert result.returncode == 1
    assert "unknown issue severity" in result.stdout


def test_review_gate_requires_p2_waiver_approval(tmp_path):
    ws = render_locked_workspace(tmp_path)
    issue = {"id": "review-test-p2", "round_id": "round-001", "severity": "P2", "status": "waived", "summary": "needs explicit waiver"}
    (ws / "review_issues.jsonl").write_text(json.dumps(issue) + "\n")
    result = run_gate(ws)
    assert result.returncode == 1
    assert "unresolved P2 without approved waiver" in result.stdout

    waiver = {"id": "waiver-test", "issue_id": "review-test-p2", "status": "approved", "approved_by": "human", "reason": "accepted residual risk"}
    (ws / "review_waivers.jsonl").write_text(json.dumps(waiver) + "\n")
    result = run_gate(ws)
    assert result.returncode == 0, result.stdout + result.stderr


def test_review_gate_schema_validates_issue_rows(tmp_path):
    ws = render_locked_workspace(tmp_path)
    issue = {"id": "review-test-p1", "severity": "P1", "status": "open", "summary": "missing round", "evidence": "see notes"}
    (ws / "review_issues.jsonl").write_text(json.dumps(issue) + "\n")
    result = run_gate(ws)
    assert result.returncode == 1
    assert "review_issues.jsonl:1" in result.stdout
    assert "schema" in result.stdout


def test_review_gate_schema_validates_waivers_before_honoring(tmp_path):
    ws = render_locked_workspace(tmp_path)
    issue = {"id": "review-test-p2", "round_id": "round-001", "severity": "P2", "status": "waived", "summary": "needs explicit waiver"}
    waiver = {"id": "waiver-test", "issue_id": "review-test-p2", "status": "approved", "approved_by": "human"}
    (ws / "review_issues.jsonl").write_text(json.dumps(issue) + "\n")
    (ws / "review_waivers.jsonl").write_text(json.dumps(waiver) + "\n")
    result = run_gate(ws)
    assert result.returncode == 1
    assert "review_waivers.jsonl:1" in result.stdout
    assert "unresolved P2 without approved waiver" in result.stdout


def test_review_gate_rejects_stale_plan_lock(tmp_path):
    ws = render_locked_workspace(tmp_path)
    (ws / "docs" / "plan.md").write_text("# Changed Plan\n\nDifferent body.\n")
    result = run_gate(ws)
    assert result.returncode == 1
    assert "plan.lock.md plan_sha256 does not match docs/plan.md" in result.stdout

    relock = subprocess.run([
        sys.executable, str(ROOT / ".agents/skills/RLInfraWiki/scripts/lock_plan.py"),
        "--workspace", str(ws),
    ], cwd=ROOT, text=True, capture_output=True)
    assert relock.returncode == 0, relock.stdout + relock.stderr
    result = run_gate(ws)
    assert result.returncode == 0, result.stdout + result.stderr


def test_review_gate_plan_lock_ignores_embedded_plan_hash_examples(tmp_path):
    ws = tmp_path / "task"
    subprocess.run([
        sys.executable, str(ROOT / ".agents/skills/RLInfraWiki/scripts/render_task_bundle.py"),
        "--contract", str(ROOT / "examples/task_contracts/slime-weight-sync.yaml"),
        "--output", str(ws),
    ], check=True, cwd=ROOT)
    with (ws / "docs" / "plan.md").open("a", encoding="utf-8") as f:
        f.write("\n## Plan Lock Documentation\n")
        f.write("- plan_sha256: example-plan-hash\n")
        f.write("- task_contract_sha256: example-contract-hash\n")
        f.write("- goal_sha256: example-goal-hash\n")
    subprocess.run([sys.executable, str(ROOT / ".agents/skills/RLInfraWiki/scripts/lock_plan.py"), "--workspace", str(ws)], check=True, cwd=ROOT)

    result = run_gate(ws)
    assert result.returncode == 0, result.stdout + result.stderr


def test_review_gate_rejects_stale_validation_matrix_after_contract_amendment(tmp_path):
    ws = render_locked_workspace(tmp_path)
    contract = tmp_path / "amended-contract.yaml"
    original = (ROOT / "examples/task_contracts/slime-weight-sync.yaml").read_text()
    amended = original.replace(
        '  - "python .agents/skills/RLInfraWiki/scripts/validate.py"\n',
        '  - "python .agents/skills/RLInfraWiki/scripts/validate.py"\n  - "echo NEW-VALIDATION-CMD"\n',
    )
    contract.write_text(amended)
    render = subprocess.run([
        sys.executable, str(ROOT / ".agents/skills/RLInfraWiki/scripts/render_task_bundle.py"),
        "--contract", str(contract),
        "--output", str(ws),
        "--force",
    ], cwd=ROOT, text=True, capture_output=True)
    assert render.returncode == 0, render.stdout + render.stderr
    assert "WARN: contract changed; scaffolded docs under docs/ were preserved" in render.stderr

    relock = subprocess.run([
        sys.executable, str(ROOT / ".agents/skills/RLInfraWiki/scripts/lock_plan.py"),
        "--workspace", str(ws),
    ], cwd=ROOT, text=True, capture_output=True)
    assert relock.returncode == 0, relock.stdout + relock.stderr
    result = run_gate(ws)
    assert result.returncode == 1
    assert "validation_matrix.md missing validation command from task_contract.yaml: echo NEW-VALIDATION-CMD" in result.stdout


def test_review_gate_matches_validation_matrix_commands_exactly(tmp_path):
    ws = tmp_path / "task"
    contract = tmp_path / "prefix-contract.yaml"
    data = (ROOT / "examples/task_contracts/slime-weight-sync.yaml").read_text()
    data = data.replace(
        '  - "python .agents/skills/RLInfraWiki/scripts/query.py \'Megatron SGLang weight sync\' --limit 8"\n  - "python .agents/skills/RLInfraWiki/scripts/validate.py"\n  - "python .agents/skills/RLInfraWiki/scripts/validate_review_gate.py --workspace ."\n',
        '  - "pytest"\n  - "pytest -k integration"\n',
    )
    contract.write_text(data)
    render = subprocess.run([
        sys.executable, str(ROOT / ".agents/skills/RLInfraWiki/scripts/render_task_bundle.py"),
        "--contract", str(contract),
        "--output", str(ws),
    ], cwd=ROOT, text=True, capture_output=True)
    assert render.returncode == 0, render.stdout + render.stderr
    (ws / "docs" / "validation_matrix.md").write_text(
        "# Validation Matrix\n\n"
        "| requirement | validation command | expected result | evidence path | status |\n"
        "|---|---|---|---|---|\n"
        "| contract validation | `pytest -k integration` | exits 0 | evidence/01-validation.log | pending |\n"
    )
    relock = subprocess.run([
        sys.executable, str(ROOT / ".agents/skills/RLInfraWiki/scripts/lock_plan.py"),
        "--workspace", str(ws),
    ], cwd=ROOT, text=True, capture_output=True)
    assert relock.returncode == 0, relock.stdout + relock.stderr

    result = run_gate(ws)
    assert result.returncode == 1
    assert "validation_matrix.md missing validation command from task_contract.yaml: pytest" in result.stdout
