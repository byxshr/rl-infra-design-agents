#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


CONTRACT_ID = "humanize-gate-invariants-v1"
PASS_VERDICT = "PASS"
CONFLICT_VERDICT = "TOOL-CONTRACT-CONFLICT"
VERDICT_RE = re.compile(r"^\s*Humanize Gate Verdict:\s*(\S.*?)\s*$", re.MULTILINE)
PRIORITY_RE = re.compile(r"(^#{1,6}\s+P[01](?:[\s:\-]|$)|\[(?:P0|P1)\])", re.MULTILINE | re.IGNORECASE)
ACTION = r"(?:force[- ]?add|add|commit(?:s|ted|ting)?|stag(?:e|es|ed|ing)|track(?:s|ed|ing)?)"
DIRECTIVE_PREFIX = r"""
    (?:
        ^\s*(?:(?:\d+[.)]|-)\s+)?(?:please\s+(?:also\s+)?)?
        |
        \b(?:must|should|have\s+to|has\s+to|need(?:s)?\s+to|required\s+to|then|the\s+fix\s+is\s+to)
        \s+(?:please\s+(?:also\s+)?)?
        |
        \b(?:i\s+)?(?:recommend(?:ed)?|suggest(?:ed)?)\s+(?:to\s+)?
    )
"""
ACTIONABLE_HUMANIZE_RE = re.compile(
    rf"{DIRECTIVE_PREFIX}{ACTION}[^,;.!?]{{0,100}}\.humanize(?:/|\b)",
    re.IGNORECASE | re.VERBOSE,
)
GIT_ADD_RE = re.compile(
    r"""\bgit(?:\s+-c\s+(?:"[^"]+"|'[^']+'|\S+))?\s+add\b""",
    re.IGNORECASE,
)
FORCE_RE = re.compile(r"(?:^|\s)(?:-f|--force|-fa|-af)(?=\s|$)", re.IGNORECASE)
ALL_RE = re.compile(r"(?:^|\s)(?:\.|-a|--all)(?=\s|$)", re.IGNORECASE)
RUNTIME_CONTRACT_RELPATHS = (
    ".claude-plugin/plugin.json",
    "prompt-template/codex/gate-invariants-section.md",
    "prompt-template/codex/gate-guidance-corpus.tsv",
    "prompt-template/codex/regular-review.md",
    "prompt-template/codex/full-alignment-review.md",
    "prompt-template/codex/code-review-phase.md",
    "hooks/loop-codex-stop-hook.sh",
    "hooks/lib/review-contract.sh",
)


@dataclass(frozen=True)
class ReviewValidation:
    valid: bool
    verdict: str | None
    errors: tuple[str, ...]
    warnings: tuple[str, ...] = ()


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def unsafe_review_lines(text: str) -> list[str]:
    unsafe: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        lower = line.lower()
        normalized = line.translate(str.maketrans({"`": " ", "*": " ", "_": " "}))
        if not line:
            continue
        if GIT_ADD_RE.search(line) and ".humanize" in lower:
            unsafe.append(line)
            continue
        if GIT_ADD_RE.search(normalized) and FORCE_RE.search(normalized) and ALL_RE.search(normalized):
            unsafe.append(line)
            continue
        if ".humanize" in lower and ACTIONABLE_HUMANIZE_RE.search(normalized):
            unsafe.append(line)
    return unsafe


def validate_guidance_corpus(path: Path) -> list[str]:
    errors: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        return [f"unable to read Humanize guidance corpus {path}: {exc}"]
    case_count = 0
    for line_number, raw_line in enumerate(lines, start=1):
        if not raw_line or raw_line.startswith("#"):
            continue
        try:
            expected, guidance = raw_line.split("\t", 1)
        except ValueError:
            errors.append(f"invalid guidance corpus row {path}:{line_number}: expected TAB-separated label and text")
            continue
        if expected not in {"safe", "unsafe"}:
            errors.append(f"invalid guidance corpus label {path}:{line_number}: {expected!r}")
            continue
        case_count += 1
        actual = "unsafe" if unsafe_review_lines(guidance) else "safe"
        if actual != expected:
            errors.append(
                f"guidance corpus mismatch {path}:{line_number}: expected {expected}, got {actual}: {guidance}"
            )
    if case_count == 0:
        errors.append(f"Humanize guidance corpus contains no cases: {path}")
    return errors


def runtime_contract_fingerprint(root: Path) -> str | None:
    paths = [root / relpath for relpath in RUNTIME_CONTRACT_RELPATHS]
    if not all(path.is_file() for path in paths):
        return None
    digest = hashlib.sha256()
    for relpath, path in zip(RUNTIME_CONTRACT_RELPATHS, paths):
        digest.update(relpath.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return f"sha256:{digest.hexdigest()}"


def validate_review_text(text: str, *, require_verdict: bool) -> ReviewValidation:
    errors: list[str] = []
    warnings: list[str] = []
    verdicts = [match.strip() for match in VERDICT_RE.findall(text)]
    verdict = verdicts[0] if len(verdicts) == 1 else None

    if require_verdict:
        if len(verdicts) != 1:
            errors.append(f"review must contain exactly one Humanize Gate Verdict; found {len(verdicts)}")
        elif verdict not in {PASS_VERDICT, CONFLICT_VERDICT}:
            errors.append(f"invalid Humanize Gate Verdict: {verdict}")
    elif not verdicts:
        warnings.append(f"legacy review has no {CONTRACT_ID} verdict")
    elif len(verdicts) != 1:
        errors.append(f"review must not contain multiple Humanize Gate Verdict lines; found {len(verdicts)}")
    elif verdict not in {PASS_VERDICT, CONFLICT_VERDICT}:
        errors.append(f"invalid Humanize Gate Verdict: {verdict}")

    unsafe = unsafe_review_lines(text)
    if unsafe:
        errors.append(f"review contains gate-conflicting Humanize Git guidance: {unsafe[0]}")

    if verdict == CONFLICT_VERDICT:
        if not PRIORITY_RE.search(text):
            errors.append("TOOL-CONTRACT-CONFLICT requires a P0/P1 finding")
        semantic_lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip() and not line.lstrip().startswith("Humanize Gate Verdict:")
        ]
        if semantic_lines and semantic_lines[-1] == "COMPLETE":
            errors.append("TOOL-CONTRACT-CONFLICT review must not end with COMPLETE")

    return ReviewValidation(not errors, verdict, tuple(errors), tuple(warnings))


def validate_review_file(path: Path, *, require_verdict: bool) -> ReviewValidation:
    if not path.exists():
        return ReviewValidation(False, None, (f"review result does not exist: {path}",))
    if not path.is_file():
        return ReviewValidation(False, None, (f"review result is not a file: {path}",))
    text = path.read_text(encoding="utf-8", errors="replace")
    if not text.strip():
        return ReviewValidation(False, None, (f"review result is empty: {path}",))
    return validate_review_text(text, require_verdict=require_verdict)


def read_plugin_manifest(root: Path) -> tuple[dict[str, Any] | None, list[str]]:
    manifest_path = root / ".claude-plugin" / "plugin.json"
    if not manifest_path.is_file():
        return None, [f"missing Humanize plugin manifest: {manifest_path}"]
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return None, [f"invalid Humanize plugin manifest: {manifest_path}: {exc}"]
    if not isinstance(data, dict):
        return None, [f"Humanize plugin manifest must be a JSON object: {manifest_path}"]
    return data, []


def validate_runtime_root(root: Path) -> dict[str, Any]:
    resolved = root.expanduser().resolve()
    errors: list[str] = []
    manifest, manifest_errors = read_plugin_manifest(resolved)
    errors.extend(manifest_errors)
    if manifest is not None and manifest.get("name") != "humanize":
        errors.append(f"plugin manifest name must be humanize, got {manifest.get('name')!r}")

    gate_path = resolved / "prompt-template" / "codex" / "gate-invariants-section.md"
    corpus_path = resolved / "prompt-template" / "codex" / "gate-guidance-corpus.tsv"
    templates = [
        resolved / "prompt-template" / "codex" / "regular-review.md",
        resolved / "prompt-template" / "codex" / "full-alignment-review.md",
        resolved / "prompt-template" / "codex" / "code-review-phase.md",
    ]
    hook_path = resolved / "hooks" / "loop-codex-stop-hook.sh"
    validator_path = resolved / "hooks" / "lib" / "review-contract.sh"

    for path in [gate_path, corpus_path, *templates, hook_path, validator_path]:
        if not path.is_file():
            errors.append(f"missing gate-aware runtime file: {path}")

    if gate_path.is_file() and CONTRACT_ID not in gate_path.read_text(encoding="utf-8"):
        errors.append(f"gate invariant section does not declare {CONTRACT_ID}: {gate_path}")
    for path in templates:
        if path.is_file() and "HUMANIZE_GATE_INVARIANTS_SECTION" not in path.read_text(encoding="utf-8"):
            errors.append(f"review template does not inject Humanize gate invariants: {path}")
    if hook_path.is_file():
        hook = hook_path.read_text(encoding="utf-8")
        for marker in ["review-contract.sh", "validate_humanize_gate_review_file", "codex review"]:
            if marker not in hook:
                errors.append(f"Humanize stop hook is missing gate-aware marker {marker!r}: {hook_path}")
    if validator_path.is_file() and CONTRACT_ID not in validator_path.read_text(encoding="utf-8"):
        errors.append(f"Humanize review validator does not declare {CONTRACT_ID}: {validator_path}")
    if corpus_path.is_file():
        errors.extend(validate_guidance_corpus(corpus_path))

    return {
        "contract_id": CONTRACT_ID,
        "status": "compatible" if not errors else "incompatible",
        "validation_kind": "static_contract_probe",
        "root": str(resolved),
        "plugin_name": manifest.get("name") if manifest else None,
        "plugin_version": manifest.get("version") if manifest else None,
        "contract_fingerprint": runtime_contract_fingerprint(resolved),
        "errors": errors,
    }


def validate_main_policy(root: Path) -> list[str]:
    errors: list[str] = []
    prompt = root / "prompts" / "codex-review-prompt.md"
    agents = root / "AGENTS.md"
    for path in [prompt, agents]:
        if not path.is_file():
            errors.append(f"missing main-repo review policy file: {path}")
            continue
        text = path.read_text(encoding="utf-8")
        if CONTRACT_ID not in text:
            errors.append(f"main-repo review policy does not declare {CONTRACT_ID}: {path}")
        if "Humanize Gate Verdict:" not in text:
            errors.append(f"main-repo review policy does not require a Humanize Gate Verdict: {path}")
    return errors


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate the IMP-020 Humanize/Codex gate-aware review contract.")
    parser.add_argument("--repo-root", default=None, help="Main rl-infra-design-agents repository root.")
    parser.add_argument("--humanize-root", default=None, help="Humanize plugin runtime root to validate.")
    parser.add_argument("--review-result", default=None, help="Review result file to validate.")
    parser.add_argument("--require-verdict", action="store_true", help="Require exactly one v1 gate verdict.")
    parser.add_argument("--print-json", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.repo_root).expanduser().resolve() if args.repo_root else repo_root()
    errors = validate_main_policy(root)
    report: dict[str, Any] = {
        "contract_id": CONTRACT_ID,
        "main_repo": str(root),
        "main_policy_status": "compatible" if not errors else "incompatible",
        "errors": list(errors),
        "warnings": [],
    }

    if args.humanize_root:
        runtime = validate_runtime_root(Path(args.humanize_root))
        report["runtime"] = runtime
        report["errors"].extend(runtime["errors"])
    else:
        report["warnings"].append(
            "main policy only: no Humanize runtime root was provided; pass --humanize-root to validate runtime files"
        )

    if args.review_result:
        review = validate_review_file(Path(args.review_result), require_verdict=args.require_verdict)
        report["review"] = {
            "path": str(Path(args.review_result).expanduser().resolve()),
            "status": "valid" if review.valid else "invalid",
            "verdict": review.verdict,
            "errors": list(review.errors),
            "warnings": list(review.warnings),
        }
        report["errors"].extend(review.errors)
        report["warnings"].extend(review.warnings)

    report["status"] = "passed" if not report["errors"] else "failed"
    if args.print_json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for warning in report["warnings"]:
            print(f"WARN: {warning}")
        if report["errors"]:
            for error in report["errors"]:
                print(f"ERROR: {error}", file=sys.stderr)
        else:
            print(f"Humanize review contract validation passed ({CONTRACT_ID})")
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
