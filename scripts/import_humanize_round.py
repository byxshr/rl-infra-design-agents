#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shlex
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROUND_FILE_RE = re.compile(r"round-(\d+)-(summary|review-result|prompt|review-prompt|contract)\.md$")
TIMESTAMP_DIR_RE = re.compile(r"^\d{4}-\d{2}-\d{2}[_T]\d{2}[-:]\d{2}[-:]\d{2}")
HEADING_FINDING_RE = re.compile(r"^#{2,6}\s+(P[0-9])\s*[:\-]\s*(.+)$", re.IGNORECASE)
BRACKET_FINDING_RE = re.compile(r"^\s*(?:[-*]\s*)?\[(P[0-9])\]\s+(.+)$", re.IGNORECASE)
NO_FINDING_RE = re.compile(
    r"(^|\b)(COMPLETE|no\s+(?:open\s+)?(?:issues|findings|problems)|no\s+\[P[0-9]\]\s+issues|no\s+blocking\s+issues)(\b|$)",
    re.IGNORECASE | re.MULTILINE,
)
SUPPORTED_BRIDGE_SCHEMA_VERSIONS = frozenset({1, 2})


class ImportErrorWithMessage(Exception):
    pass


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def mtime_iso(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).replace(microsecond=0).isoformat()


def resolve_cli_path(value: str, *, base: Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = base / path
    return path.resolve()


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise ImportErrorWithMessage(f"missing bridge metadata: {path}; run IMP-013 prepare-humanize-task first")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ImportErrorWithMessage(f"bridge metadata is not valid JSON: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ImportErrorWithMessage(f"bridge metadata must be a JSON object: {path}")
    return data


def validate_bridge(bridge: dict[str, Any], workspace: Path, accepted_schema_versions: set[int]) -> list[str]:
    supported_versions = SUPPORTED_BRIDGE_SCHEMA_VERSIONS | accepted_schema_versions
    schema_version = bridge.get("schema_version")
    if schema_version not in supported_versions:
        raise ImportErrorWithMessage(
            f"unsupported bridge schema_version: {schema_version}; supported: {sorted(supported_versions)}"
        )

    warnings = []
    bridge_workspace = bridge.get("workspace")
    if isinstance(bridge_workspace, str) and bridge_workspace:
        resolved_bridge_workspace = Path(bridge_workspace).expanduser().resolve()
        if resolved_bridge_workspace != workspace:
            warnings.append(
                "bridge workspace path differs from --workspace: "
                f"bridge={resolved_bridge_workspace} actual={workspace}"
            )
    return warnings


def file_record(path: Path, *, data: bytes | None = None) -> dict[str, Any]:
    if data is None:
        data = path.read_bytes()
    return {
        "path": str(path),
        "sha256": hashlib.sha256(data).hexdigest(),
        "mtime": mtime_iso(path),
        "bytes": path.stat().st_size,
    }


def text_file_record(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    record = file_record(path, data=data)
    try:
        data.decode("utf-8")
        record["had_replacement_chars"] = False
    except UnicodeDecodeError:
        record["had_replacement_chars"] = True
    return record


def available_rounds(loop_dir: Path) -> dict[int, set[str]]:
    rounds: dict[int, set[str]] = {}
    for path in loop_dir.glob("round-*-*.md"):
        match = ROUND_FILE_RE.match(path.name)
        if match:
            rounds.setdefault(int(match.group(1)), set()).add(match.group(2))
    return rounds


def active_loop_dirs(base: Path) -> list[Path]:
    if not base.exists():
        return []
    active_markers = {"state.md", "finalize-state.md", "methodology-analysis-state.md"}
    return [
        path
        for path in sorted(base.iterdir())
        if path.is_dir() and any((path / marker).exists() for marker in active_markers)
    ]


def candidate_loop_dirs(base: Path) -> list[Path]:
    if not base.exists():
        return []
    candidates = []
    for path in sorted(base.iterdir()):
        if not path.is_dir():
            continue
        if available_rounds(path) or (path / "goal-tracker.md").exists():
            candidates.append(path)
    return candidates


def discover_under_base(base: Path, *, strict_ambiguity: bool) -> Path | None:
    actives = active_loop_dirs(base)
    if len(actives) == 1:
        return actives[0].resolve()
    if len(actives) > 1:
        listed = "\n".join(f"- {path}" for path in actives)
        raise ImportErrorWithMessage(f"multiple active Humanize loop dirs found; pass --humanize-loop-dir:\n{listed}")

    candidates = candidate_loop_dirs(base)
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0].resolve()
    if not strict_ambiguity and all(TIMESTAMP_DIR_RE.match(path.name) for path in candidates):
        return sorted(candidates, key=lambda path: path.name)[-1].resolve()
    listed = "\n".join(f"- {path}" for path in candidates)
    raise ImportErrorWithMessage(f"multiple Humanize loop dirs found and latest is ambiguous; pass --humanize-loop-dir:\n{listed}")


def discover_loop_dir(workspace: Path, explicit: str | None, bridge: dict[str, Any]) -> Path:
    if explicit:
        loop_dir = resolve_cli_path(explicit, base=Path.cwd())
        if not loop_dir.exists() or not loop_dir.is_dir():
            raise ImportErrorWithMessage(f"humanize loop dir does not exist or is not a directory: {loop_dir}")
        return loop_dir

    if bridge.get("schema_version") == 2 and bridge.get("execution_mode") == "target_repo":
        target_repo = bridge.get("target_repo")
        if not isinstance(target_repo, str) or not target_repo.strip():
            raise ImportErrorWithMessage("v2 target-repo bridge metadata is missing target_repo")
        target_base = Path(target_repo).expanduser().resolve() / ".humanize" / "rlcr"
        discovered = discover_under_base(target_base, strict_ambiguity=True)
        if discovered is not None:
            return discovered
        raise ImportErrorWithMessage(
            "no Humanize loop dirs found under the v2 target repository; "
            f"expected a loop under {target_base}. "
            "Pass --humanize-loop-dir only for a deliberate explicit import."
        )

    workspace_base = workspace / ".humanize" / "rlcr"
    discovered = discover_under_base(workspace_base, strict_ambiguity=False)
    if discovered is not None:
        return discovered
    raise ImportErrorWithMessage(f"no Humanize loop dirs found under {workspace_base}")


def discover_round(loop_dir: Path, requested: int | None) -> int:
    rounds = available_rounds(loop_dir)
    if requested is not None:
        if requested not in rounds:
            listed = ", ".join(str(num) for num in sorted(rounds)) or "none"
            raise ImportErrorWithMessage(f"round mismatch: round {requested} not found in {loop_dir}; available rounds: {listed}")
        return requested
    complete = [num for num, kinds in rounds.items() if {"summary", "review-result"} <= kinds]
    if not complete:
        listed = ", ".join(f"{num}:{','.join(sorted(kinds))}" for num, kinds in sorted(rounds.items())) or "none"
        raise ImportErrorWithMessage(f"no importable Humanize round found in {loop_dir}; available round files: {listed}")
    return max(complete)


def required_round_files(loop_dir: Path, round_number: int) -> tuple[Path, Path]:
    summary = loop_dir / f"round-{round_number}-summary.md"
    review = loop_dir / f"round-{round_number}-review-result.md"
    missing = []
    if not summary.exists():
        missing.append(summary.name)
    if not review.exists():
        missing.append(review.name)
    if missing:
        available = ", ".join(f"round {num}: {','.join(sorted(kinds))}" for num, kinds in sorted(available_rounds(loop_dir).items())) or "none"
        raise ImportErrorWithMessage(
            f"missing required Humanize round file(s) in {loop_dir}: {', '.join(missing)}; available: {available}"
        )
    return summary, review


def map_severity(raw: str) -> str:
    sev = raw.upper()
    if sev in {"P0", "P1", "P2", "P3"}:
        return sev
    return "P3"


def clean_title(title: str) -> tuple[str, str | None]:
    text = title.strip()
    file_path = None
    # Humanize code review often emits: "- [P1] title - path:line".
    match = re.match(r"(.+?)\s+-\s+(\S+:\d+(?:-\d+)?)\s*$", text)
    if match:
        text = match.group(1).strip()
        file_path = match.group(2).strip()
    return text or "Untitled Humanize finding", file_path


def extract_findings(text: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    seen = set()
    for line_number, line in enumerate(text.splitlines(), 1):
        match = HEADING_FINDING_RE.match(line.strip()) or BRACKET_FINDING_RE.match(line)
        if not match:
            continue
        raw_severity = match.group(1).upper()
        title, file_path = clean_title(match.group(2))
        severity = map_severity(raw_severity)
        if raw_severity != severity:
            title = f"Humanize {raw_severity}: {title}"
        key = (severity, title, file_path)
        if key in seen:
            continue
        seen.add(key)
        findings.append(
            {
                "severity": severity,
                "raw_severity": raw_severity,
                "title": title,
                "file": file_path,
                "line_number": line_number,
                "raw_line": line.strip(),
            }
        )
    return findings


def is_no_finding_review(text: str) -> bool:
    stripped = text.strip()
    return bool(stripped and NO_FINDING_RE.search(stripped))


def quote_markdown(text: str) -> str:
    if not text.strip():
        return "> (empty)\n"
    return "\n".join(f"> {line}" if line else ">" for line in text.splitlines()) + "\n"


def render_codex_review(round_id: str, round_number: int, review_text: str, findings: list[dict[str, Any]]) -> str:
    lines = [
        f"# Imported Humanize Codex Review: {round_id}",
        "",
        f"- imported_round: {round_number}",
        "- source: Humanize `.humanize/rlcr` review result",
        "- note: Raw Humanize output is preserved below; parser-compatible findings are normalized first.",
        "",
    ]
    if findings:
        lines.extend(["## Parser-Compatible Findings", ""])
        for finding in findings:
            lines.extend(
                [
                    f"### {finding['severity']}: {finding['title']}",
                    f"- File/path: {finding['file'] or 'unknown'}",
                    f"- Evidence: Original Humanize severity: {finding['raw_severity']}",
                    f"- Evidence: Humanize review result line {finding['line_number']}: {finding['raw_line']}",
                    "- Suggested fix: Follow the Humanize review result and record validation evidence before re-review.",
                    "",
                ]
            )
    else:
        lines.extend(
            [
                "## No Findings",
                "",
                "No parser-compatible P0-P3 findings were imported from this Humanize round.",
                "Humanize review result reported COMPLETE or an equivalent no-finding outcome.",
                "",
            ]
        )
    lines.extend(["## Raw Humanize Review Result", "", quote_markdown(review_text).rstrip(), ""])
    return "\n".join(lines)


def copy_optional_file(source: Path, dest: Path, *, dry_run: bool) -> bool:
    if not source.exists():
        return False
    if not dry_run:
        shutil.copyfile(source, dest)
    return True


def run_subprocess(args: list[str], *, cwd: Path, timeout: int) -> subprocess.CompletedProcess[str]:
    command = shlex.join(args)
    try:
        result = subprocess.run(args, cwd=cwd, text=True, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise ImportErrorWithMessage(f"command timed out after {timeout} seconds: {command}") from exc
    if result.stdout:
        print(result.stdout, end="")
    if result.stderr:
        print(result.stderr, end="", file=sys.stderr)
    return result


def import_round(args: argparse.Namespace) -> int:
    root = repo_root()
    workspace = resolve_cli_path(args.workspace, base=Path.cwd())
    bridge_path = workspace / ".humanize" / "rlinfra_bridge.json"
    bridge = load_json(bridge_path)
    bridge_warnings = validate_bridge(bridge, workspace, set(args.accept_bridge_schema))
    loop_dir = discover_loop_dir(workspace, args.humanize_loop_dir, bridge)
    round_number = discover_round(loop_dir, args.round)
    summary_path, review_path = required_round_files(loop_dir, round_number)
    review_text = review_path.read_text(encoding="utf-8", errors="replace")
    if not review_text.strip():
        raise ImportErrorWithMessage(f"Humanize review result is empty: {review_path}")
    findings = extract_findings(review_text)
    no_finding = not findings and is_no_finding_review(review_text)
    if not findings and not no_finding:
        raise ImportErrorWithMessage(
            f"Humanize review result is not parseable as findings and does not contain COMPLETE/no-finding marker: {review_path}"
        )

    round_id = f"round-{round_number:03d}"
    round_dir = workspace / "review_rounds" / round_id
    if round_dir.exists() and any(round_dir.iterdir()) and not args.allow_overwrite and not args.dry_run:
        raise ImportErrorWithMessage(f"target review round already exists: {round_dir}; rerun with --allow-overwrite")

    codex_review_text = render_codex_review(round_id, round_number, review_text, findings)
    prompt_path = loop_dir / f"round-{round_number}-prompt.md"
    review_prompt_path = loop_dir / f"round-{round_number}-review-prompt.md"
    contract_path = loop_dir / f"round-{round_number}-contract.md"
    goal_tracker_path = loop_dir / "goal-tracker.md"
    optional_sources = {
        "prompt": prompt_path,
        "review_prompt": review_prompt_path,
        "round_contract": contract_path,
        "goal_tracker": goal_tracker_path,
    }
    source_files = {
        "summary": text_file_record(summary_path),
        "review_result": text_file_record(review_path),
    }
    for key, path in optional_sources.items():
        if path.exists():
            source_files[key] = text_file_record(path)

    metadata = {
        "imported_at": now_iso(),
        "loop_dir": str(loop_dir),
        "round": round_number,
        "round_id": round_id,
        "issue_count": len(findings),
        "no_finding": no_finding,
        "bridge": {
            "path": str(bridge_path),
            "schema_version": bridge.get("schema_version"),
            "repo_commit": bridge.get("repo_commit"),
            "rlinfrawiki_commit": bridge.get("rlinfrawiki_commit"),
            "target_repo": bridge.get("target_repo"),
            "diff_base": bridge.get("diff_base"),
        },
        "source_files": source_files,
        "warnings": bridge_warnings,
        "allow_overwrite": bool(args.allow_overwrite),
    }

    print(f"Import plan:")
    print(f"  workspace: {workspace}")
    print(f"  loop_dir: {loop_dir}")
    print(f"  round: {round_number} -> {round_dir}")
    print(f"  issues: {len(findings)}")
    print(f"  no_finding: {no_finding}")
    for warning in bridge_warnings:
        print(f"WARN: {warning}")
    if args.dry_run:
        print("Dry run: no files written.")
        return 0

    round_dir.mkdir(parents=True, exist_ok=True)
    (round_dir / "claude_response.md").write_text(summary_path.read_text(encoding="utf-8", errors="replace"), encoding="utf-8")
    (round_dir / "codex_review.md").write_text(codex_review_text, encoding="utf-8")
    (round_dir / "humanize_round_metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    copy_optional_file(prompt_path, round_dir / "humanize_prompt.md", dry_run=False)
    copy_optional_file(review_prompt_path, round_dir / "humanize_review_prompt.md", dry_run=False)
    copy_optional_file(contract_path, round_dir / "humanize_round_contract.md", dry_run=False)
    copy_optional_file(goal_tracker_path, round_dir / "humanize_goal_tracker.md", dry_run=False)

    parse_script = root / ".agents" / "skills" / "RLInfraWiki" / "scripts" / "parse_codex_review.py"
    append_script = root / ".agents" / "skills" / "RLInfraWiki" / "scripts" / "append_review_round.py"
    parse_result = run_subprocess(
        [
            sys.executable,
            str(parse_script),
            "--input",
            str(round_dir / "codex_review.md"),
            "--output",
            str(round_dir / "parsed_issues.jsonl"),
        ],
        cwd=root,
        timeout=args.command_timeout,
    )
    if parse_result.returncode != 0:
        raise ImportErrorWithMessage(f"review could not be parsed: {round_dir / 'codex_review.md'}")

    append_args = [
        sys.executable,
        str(append_script),
        "--workspace",
        str(workspace),
        "--round-dir",
        str(round_dir),
    ]
    if args.allow_overwrite:
        append_args.append("--allow-overwrite")
    append_result = run_subprocess(append_args, cwd=root, timeout=args.command_timeout)
    if append_result.returncode != 0:
        raise ImportErrorWithMessage("parsed review issues could not be appended to workspace ledger")

    print(f"Imported Humanize round {round_number} into {round_dir}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import a Humanize RLCR round into an RLInfraWiki workspace.")
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--humanize-loop-dir", default=None)
    parser.add_argument("--round", type=int, default=None)
    parser.add_argument("--allow-overwrite", action="store_true")
    parser.add_argument("--require-review-result", action="store_true", help="Accepted for explicitness; review result is always required.")
    parser.add_argument(
        "--accept-bridge-schema",
        type=int,
        action="append",
        default=[],
        help="Explicitly accept an additional .humanize/rlinfra_bridge.json schema version.",
    )
    parser.add_argument(
        "--command-timeout",
        type=int,
        default=300,
        help="Seconds to wait for parser/appender subprocesses before failing.",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return import_round(args)
    except ImportErrorWithMessage as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
