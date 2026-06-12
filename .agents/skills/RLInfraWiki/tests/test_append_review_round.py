import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def render_workspace(tmp_path):
    ws = tmp_path / "task"
    result = subprocess.run([
        sys.executable, str(ROOT / ".agents/skills/RLInfraWiki/scripts/render_task_bundle.py"),
        "--contract", str(ROOT / "examples/task_contracts/slime-weight-sync.yaml"),
        "--output", str(ws),
    ], cwd=ROOT, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr
    return ws


def run_append(ws, round_dir, *extra_args):
    return subprocess.run([
        sys.executable, str(ROOT / ".agents/skills/RLInfraWiki/scripts/append_review_round.py"),
        "--workspace", str(ws),
        "--round-dir", str(round_dir),
        *extra_args,
    ], cwd=ROOT, text=True, capture_output=True)


def run_parse(review_path, output_path):
    return subprocess.run([
        sys.executable, str(ROOT / ".agents/skills/RLInfraWiki/scripts/parse_codex_review.py"),
        "--input", str(review_path),
        "--output", str(output_path),
    ], cwd=ROOT, text=True, capture_output=True)


def test_append_review_round_validates_dedupes_and_merges_state(tmp_path):
    ws = render_workspace(tmp_path)
    rdir = ws / "review_rounds" / "round-001"
    rdir.mkdir(parents=True)
    issue = {
        "id": "review-round-001-001-p1",
        "round_id": "round-001",
        "severity": "p1",
        "status": "OPEN",
        "summary": "missing validation",
    }
    (rdir / "parsed_issues.jsonl").write_text(json.dumps(issue) + "\n")
    (ws / ".humanize" / "loop_state.json").write_text(json.dumps({"status": "initialized", "custom": True}) + "\n")

    first = run_append(ws, "review_rounds/round-001")
    assert first.returncode == 0, first.stdout + first.stderr
    rows = [json.loads(line) for line in (ws / "review_issues.jsonl").read_text().splitlines()]
    assert len(rows) == 1
    assert rows[0]["severity"] == "P1"
    assert rows[0]["status"] == "open"
    state = json.loads((ws / ".humanize" / "loop_state.json").read_text())
    assert state["custom"] is True
    assert state["status"] == "review-ingested"

    second = run_append(ws, "review_rounds/round-001")
    assert second.returncode == 0, second.stdout + second.stderr
    rows = [json.loads(line) for line in (ws / "review_issues.jsonl").read_text().splitlines()]
    assert len(rows) == 1
    assert "skipped 1 duplicate" in second.stdout


def test_append_review_round_rejects_malformed_issue(tmp_path):
    ws = render_workspace(tmp_path)
    rdir = ws / "review_rounds" / "round-001"
    rdir.mkdir(parents=True)
    issue = {"id": "review-round-001-001-p1", "severity": "P1", "status": "open", "summary": "missing round"}
    (rdir / "parsed_issues.jsonl").write_text(json.dumps(issue) + "\n")

    result = run_append(ws, "review_rounds/round-001")
    assert result.returncode == 1
    assert "failed schema validation" in result.stdout
    assert (ws / "review_issues.jsonl").read_text() == ""


def test_append_review_round_conflict_requires_explicit_overwrite(tmp_path):
    ws = render_workspace(tmp_path)
    rdir = ws / "review_rounds" / "round-001"
    rdir.mkdir(parents=True)
    issue = {
        "id": "review-round-001-001-p1",
        "round_id": "round-001",
        "severity": "P1",
        "status": "open",
        "summary": "missing validation",
    }
    (rdir / "parsed_issues.jsonl").write_text(json.dumps(issue) + "\n")
    first = run_append(ws, "review_rounds/round-001")
    assert first.returncode == 0, first.stdout + first.stderr

    issue["summary"] = "still missing validation"
    (rdir / "parsed_issues.jsonl").write_text(json.dumps(issue) + "\n")
    conflict = run_append(ws, "review_rounds/round-001")
    assert conflict.returncode == 1
    assert "duplicate review issue id" in conflict.stdout
    rows = [json.loads(line) for line in (ws / "review_issues.jsonl").read_text().splitlines()]
    assert rows[0]["summary"] == "missing validation"
    rows[0]["owner"] = "alice"
    (ws / "review_issues.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))

    overwrite = run_append(ws, "review_rounds/round-001", "--allow-overwrite")
    assert overwrite.returncode == 0, overwrite.stdout + overwrite.stderr
    assert "replaced 1 existing issue" in overwrite.stdout
    rows = [json.loads(line) for line in (ws / "review_issues.jsonl").read_text().splitlines()]
    assert len(rows) == 1
    assert rows[0]["summary"] == "still missing validation"
    assert rows[0]["owner"] == "alice"


def test_append_review_round_detects_incoming_duplicate_conflicts(tmp_path):
    ws = render_workspace(tmp_path)
    rdir = ws / "review_rounds" / "round-001"
    rdir.mkdir(parents=True)
    first = {
        "id": "review-round-001-001-p1",
        "round_id": "round-001",
        "severity": "P1",
        "status": "open",
        "summary": "first summary",
    }
    second = dict(first)
    second["summary"] = "second summary"
    (rdir / "parsed_issues.jsonl").write_text(json.dumps(first) + "\n" + json.dumps(second) + "\n")

    conflict = run_append(ws, "review_rounds/round-001")
    assert conflict.returncode == 1
    assert "duplicate review issue id" in conflict.stdout
    assert (ws / "review_issues.jsonl").read_text() == ""

    overwrite = run_append(ws, "review_rounds/round-001", "--allow-overwrite")
    assert overwrite.returncode == 0, overwrite.stdout + overwrite.stderr
    rows = [json.loads(line) for line in (ws / "review_issues.jsonl").read_text().splitlines()]
    assert len(rows) == 1
    assert rows[0]["summary"] == "second summary"


def test_append_review_round_real_parse_overwrite_preserves_owner(tmp_path):
    ws = render_workspace(tmp_path)
    rdir = ws / "review_rounds" / "round-001"
    rdir.mkdir(parents=True)
    review = rdir / "codex_review.md"
    parsed = rdir / "parsed_issues.jsonl"
    review.write_text("### P1: missing validation\n\n- File/path: docs/plan.md\n")
    parsed_once = run_parse(review, parsed)
    assert parsed_once.returncode == 0, parsed_once.stdout + parsed_once.stderr
    first = run_append(ws, "review_rounds/round-001")
    assert first.returncode == 0, first.stdout + first.stderr
    rows = [json.loads(line) for line in (ws / "review_issues.jsonl").read_text().splitlines()]
    rows[0]["owner"] = "alice"
    rows[0]["notes"] = "human-context"
    (ws / "review_issues.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))

    review.write_text(
        "### P1: missing validation\n\n"
        "- File/path: docs/plan.md\n"
        "- Suggested fix: Add validation evidence.\n"
    )
    parsed_twice = run_parse(review, parsed)
    assert parsed_twice.returncode == 0, parsed_twice.stdout + parsed_twice.stderr
    overwrite = run_append(ws, "review_rounds/round-001", "--allow-overwrite")
    assert overwrite.returncode == 0, overwrite.stdout + overwrite.stderr
    rows = [json.loads(line) for line in (ws / "review_issues.jsonl").read_text().splitlines()]
    assert len(rows) == 1
    assert rows[0]["owner"] == "alice"
    assert rows[0]["notes"] == "human-context"
    assert rows[0]["suggested_fix"] == "Add validation evidence."
