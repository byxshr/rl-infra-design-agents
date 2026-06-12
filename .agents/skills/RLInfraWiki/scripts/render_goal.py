#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
from _rlinfra import markdown_list, read_task_contract


def render_goal(contract: dict) -> str:
    criteria = contract.get("promotion_criteria", [])
    constraints = contract.get("constraints", [])
    commands = contract.get("validation_commands", [])
    return f"""# Goal Contract

## Goal ID

{contract.get('task_name', 'unnamed-task')}

## Status

active

## Outcome

{contract.get('objective', '')}

## Acceptance criteria

{markdown_list(criteria)}
## Verification surface

| requirement | evidence type | command / artifact | pass condition |
|---|---|---|---|
""" + "".join(f"| validation | command log | `{cmd}` | exits 0 |\n" for cmd in commands) + f"""
## Constraints

{markdown_list(constraints)}
## Boundaries

- Keep implementation artifacts outside the workflow repository.
- Keep upstream claims at source-reported confidence unless locally reproduced.

## Non-goals

- Implementing a new RL framework.
- Producing GPU performance claims without evidence.

## Iteration policy

Claude Builder implements one candidate batch at a time and records evidence before review.

## Review policy

- P0/P1 review issues block promotion.
- P2 issues require fix or approved waiver.
- P3 issues may be backlog.

## Blocked stop condition

Stop when acceptance criteria cannot be met without goal amendment or external state change.

## Amendment policy

Objective, acceptance criteria, non-goals, and review gates require Human Architect approval.

## Current evidence

- Pending initial validation.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Render docs/goal.md from a task contract")
    parser.add_argument("--contract", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    contract = read_task_contract(Path(args.contract))
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_goal(contract), encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
