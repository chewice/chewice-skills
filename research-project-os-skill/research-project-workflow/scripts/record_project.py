#!/usr/bin/env python3
"""Preview or record mechanical Question and Artifact bookkeeping."""

from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import re
import sys
from typing import Any


SKILL_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_ROOT = SKILL_ROOT / "assets/templates"
QUESTION_PATTERN = re.compile(r"Q-(\d{3})")
ARTIFACT_PATTERN = re.compile(r"A-(\d{3})")
ANALYSIS_MODES = {"exploratory", "confirmatory"}


def now() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def replace_field(text: str, name: str, value: str) -> str:
    pattern = re.compile(rf"^{re.escape(name)}:[ \t]*[^\r\n]*$", re.MULTILINE)
    if pattern.search(text) is None:
        raise ValueError(f"Template lacks metadata field: {name}")
    return pattern.sub(f"{name}: {value}", text, count=1)


def next_id(texts: list[str], pattern: re.Pattern[str], prefix: str) -> str:
    numbers = [int(match.group(1)) for text in texts for match in pattern.finditer(text)]
    number = max(numbers, default=0) + 1
    if number > 999:
        raise ValueError(f"No {prefix}-ID remains in the three-digit namespace")
    return f"{prefix}-{number:03d}"


def has_substantive_content(body: str) -> bool:
    for line in body.splitlines():
        value = line.strip()
        if not value or value.startswith("###"):
            continue
        if value.startswith("|"):
            cells = [cell.strip() for cell in value.strip("|").split("|")]
            if all(not cell or set(cell) <= {"-", ":"} for cell in cells):
                continue
            if "XXX" in value or any(
                cell in {
                    "Hypothesis",
                    "Alternative explanation",
                    "Claim",
                    "Decisive evidence",
                    "Current evidence",
                    "Assessment",
                }
                for cell in cells
            ):
                continue
            if any(cells):
                return True
            continue
        if ":" in value:
            _, field_value = value.split(":", 1)
            if field_value.strip() and "XXX" not in field_value:
                return True
            continue
        return True
    return False


def table(text: str, required_column: str) -> tuple[int, list[str], int]:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if not line.startswith("|"):
            continue
        columns = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if required_column in columns:
            if index + 1 >= len(lines) or "---" not in lines[index + 1]:
                raise ValueError(f"Table for {required_column} lacks a separator row")
            end = index + 2
            while end < len(lines) and lines[end].startswith("|"):
                end += 1
            return index, columns, end
    raise ValueError(f"Missing table with column: {required_column}")


def table_rows(text: str, required_column: str) -> tuple[list[str], list[dict[str, str]]]:
    start, columns, end = table(text, required_column)
    lines = text.splitlines()
    rows: list[dict[str, str]] = []
    for line in lines[start + 2 : end]:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != len(columns):
            raise ValueError(f"Malformed {required_column} table row: {line}")
        rows.append(dict(zip(columns, cells)))
    return columns, rows


def append_question_row(
    text: str,
    *,
    question_id: str,
    question: str,
    context: str,
    brief: str,
    timestamp: str,
) -> str:
    _, columns, end = table(text, "Q-ID")
    values = {
        "Q-ID": question_id,
        "Question": question,
        "Research question": question,
        "Brief": brief,
        "Updated": timestamp,
        "Closure decision": "open",
        "Design review": "pending",
    }
    clean_question = " ".join(question.split()).replace("|", "\\|")
    values["Question"] = clean_question
    values["Research question"] = clean_question
    row = "| " + " | ".join(values.get(column, "") for column in columns) + " |"
    lines = text.splitlines()
    lines.insert(end, row)
    return "\n".join(lines) + "\n"


def update_root_handoff(
    text: str,
    *,
    timestamp: str,
    context: str,
    question_id: str,
    artifact_id: str,
    checkpoint: str,
    next_action: str,
) -> str:
    text = replace_field(text, "Updated", timestamp)
    text = replace_field(text, "Active context", context)
    start, columns, end = table(text, "Context")
    lines = text.splitlines()
    context_index = columns.index("Context")
    root_line_index: int | None = None
    root_cells: list[str] = []
    for line_index in range(start + 2, end):
        cells = [cell.strip() for cell in lines[line_index].strip().strip("|").split("|")]
        if len(cells) == len(columns) and cells[context_index] == context:
            root_line_index = line_index
            root_cells = cells
            break
    if root_line_index is None:
        raise ValueError(f"Context Map lacks Context: {context}")
    updates = {
        "Active question": question_id,
        "Current artifact": artifact_id,
        "Checkpoint": checkpoint,
        "Blocker": "none",
        "Next decisive action": next_action,
    }
    for column, value in updates.items():
        if column not in columns:
            raise ValueError(f"Context Map lacks column: {column}")
        root_cells[columns.index(column)] = value
    lines[root_line_index] = "| " + " | ".join(root_cells) + " |"
    return "\n".join(lines) + "\n"


def update_local_handoff(
    text: str,
    *,
    timestamp: str,
    question_id: str,
    artifact_id: str,
    checkpoint: str,
    next_action: str,
) -> str:
    for name, value in (
        ("Updated", timestamp),
        ("Active question", question_id),
        ("Current artifact", artifact_id),
        ("Last verified checkpoint", checkpoint),
        ("Blocker", "none"),
        ("Next decisive action", next_action),
    ):
        text = replace_field(text, name, value)
    return text


def context_row(text: str, context: str) -> dict[str, str]:
    _, rows = table_rows(text, "Context")
    row = next((item for item in rows if item.get("Context") == context), None)
    if row is None:
        raise ValueError(f"Context Map lacks Context: {context}")
    return row


def context_handoff(root: Path, root_handoff: str, context: str) -> tuple[str, str]:
    row = context_row(root_handoff, context)
    relative = row.get("Handoff", "")
    pure = Path(relative)
    if not relative or pure.is_absolute() or ".." in pure.parts:
        raise ValueError(f"Invalid Handoff path for Context {context}: {relative}")
    try:
        (root / pure).resolve().relative_to(root)
    except ValueError as error:
        raise ValueError(
            f"Invalid Handoff path for Context {context}: {relative}"
        ) from error
    path = root / pure
    if not path.is_file():
        raise ValueError(f"Declared Handoff is missing for Context {context}: {relative}")
    return relative, path.read_text(encoding="utf-8")


def handoff_updates(
    root: Path,
    handoff: str,
    *,
    context: str,
    timestamp: str,
    question_id: str,
    artifact_id: str,
    checkpoint: str,
    next_action: str,
) -> list[dict[str, str]]:
    new_root = update_root_handoff(
        handoff,
        timestamp=timestamp,
        context=context,
        question_id=question_id,
        artifact_id=artifact_id,
        checkpoint=checkpoint,
        next_action=next_action,
    )
    files = [plan_file("CURRENT_HANDOFF.md", "update", new_root, handoff)]
    if context != "root":
        relative, local = context_handoff(root, handoff, context)
        new_local = update_local_handoff(
            local,
            timestamp=timestamp,
            question_id=question_id,
            artifact_id=artifact_id,
            checkpoint=checkpoint,
            next_action=next_action,
        )
        files.append(plan_file(relative, "update", new_local, local))
    return files


def safe_scope(root: Path, scope: str) -> str:
    path = Path(scope)
    if not scope or path.is_absolute() or ".." in path.parts or scope in {".", "./"}:
        raise ValueError(f"Scope must be a non-root project-relative path: {scope}")
    resolved = (root / path).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as error:
        raise ValueError(f"Scope escapes the project: {scope}") from error
    return path.as_posix().rstrip("/")


def insert_context_row(text: str, values: dict[str, str]) -> str:
    _, columns, end = table(text, "Context")
    row = "| " + " | ".join(values.get(column, "") for column in columns) + " |"
    lines = text.splitlines()
    lines.insert(end, row)
    return "\n".join(lines) + "\n"


def build_new_context_plan(
    root: Path,
    *,
    context: str,
    scope: str,
    timestamp: str | None = None,
) -> dict[str, Any]:
    root = root.expanduser().resolve()
    if context == "root" or re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", context) is None:
        raise ValueError(f"Context must be a non-root lowercase slug: {context}")
    scope = safe_scope(root, scope)
    _, handoff = require_control_files(root)
    _, rows = table_rows(handoff, "Context")
    if any(row.get("Context") == context for row in rows):
        raise ValueError(f"Context already exists: {context}")
    if any(row.get("Scope") == scope for row in rows):
        raise ValueError(f"Context Scope already exists: {scope}")
    target_relative = f"{scope}/CURRENT_HANDOFF.md"
    if (root / target_relative).exists():
        raise ValueError(f"Refusing to overwrite existing path: {target_relative}")
    timestamp = timestamp or now()
    template = TEMPLATE_ROOT / "CONTEXT_HANDOFF.md"
    if not template.is_file():
        raise ValueError("Skill asset is missing: assets/templates/CONTEXT_HANDOFF.md")
    local = template.read_text(encoding="utf-8")
    for name, value in (
        ("Context", context),
        ("Scope", scope),
        ("Updated", timestamp),
        ("Active question", "none"),
        ("Current artifact", "none"),
        ("Last verified checkpoint", "Context registered; no scientific record active"),
        ("Blocker", "none"),
        ("Next decisive action", "Select or register a Research Question"),
    ):
        local = replace_field(local, name, value)
    new_handoff = replace_field(handoff, "Updated", timestamp)
    new_handoff = insert_context_row(
        new_handoff,
        {
            "Context": context,
            "Scope": scope,
            "Active question": "none",
            "Current artifact": "none",
            "Checkpoint": "Context registered; no scientific record active",
            "Blocker": "none",
            "Next decisive action": "Select or register a Research Question",
            "Handoff": target_relative,
        },
    )
    return {
        "operation": "new-context",
        "project": str(root),
        "context": context,
        "scope": scope,
        "timestamp": timestamp,
        "files": [
            plan_file(target_relative, "create", local),
            plan_file("CURRENT_HANDOFF.md", "update", new_handoff, handoff),
        ],
    }


def plan_file(path: str, action: str, content: str, original: str | None = None) -> dict[str, str]:
    item = {"path": path, "action": action, "content": content}
    if original is not None:
        item["original"] = original
    return item


def require_control_files(root: Path) -> tuple[str, str]:
    questions_path = root / "QUESTIONS.md"
    handoff_path = root / "CURRENT_HANDOFF.md"
    if not questions_path.is_file() or not handoff_path.is_file():
        raise ValueError("Project must be scaffolded before recording work")
    return (
        questions_path.read_text(encoding="utf-8"),
        handoff_path.read_text(encoding="utf-8"),
    )


def build_new_question_plan(
    root: Path,
    *,
    question: str,
    context: str = "root",
    timestamp: str | None = None,
) -> dict[str, Any]:
    root = root.expanduser().resolve()
    if not question.strip():
        raise ValueError("Question must not be empty")
    questions, handoff = require_control_files(root)
    _, rows = table_rows(questions, "Q-ID")
    question_id = next_id(
        [row.get("Q-ID", "") for row in rows], QUESTION_PATTERN, "Q"
    )
    timestamp = timestamp or now()
    brief_relative = f"docs/questions/{question_id}/BRIEF.md"
    brief_path = root / brief_relative
    if brief_path.exists():
        raise ValueError(f"Refusing to overwrite existing path: {brief_relative}")
    brief = (TEMPLATE_ROOT / "BRIEF.md").read_text(encoding="utf-8")
    brief = brief.replace("Q-XXX", question_id)
    for name, value in (
        ("Q-ID", question_id),
        ("Created", timestamp),
        ("Updated", timestamp),
        ("Design review", "pending"),
        ("Reviewed at", ""),
        ("Review rationale", ""),
        ("Closure decision", "open"),
        ("Closed at", ""),
        ("Closure rationale", ""),
    ):
        brief = replace_field(brief, name, value)
    question_section = re.search(
        r"^##\s+1\. Research Question and Decision\s*$\n(.*?)(?=^##\s+|\Z)",
        brief,
        re.MULTILINE | re.DOTALL,
    )
    if question_section is None:
        raise ValueError("Template lacks heading: 1. Research Question and Decision")
    updated_body = replace_field(question_section.group(1), "Research question", question)
    brief = (
        brief[: question_section.start(1)]
        + updated_body
        + brief[question_section.end(1) :]
    )
    new_questions = append_question_row(
        questions,
        question_id=question_id,
        question=question,
        context=context,
        brief=brief_relative,
        timestamp=timestamp,
    )
    handoff_files = handoff_updates(
        root,
        handoff,
        context=context,
        timestamp=timestamp,
        question_id=question_id,
        artifact_id="none",
        checkpoint="Question recorded; study design pending",
        next_action=f"Complete and review {brief_relative}",
    )
    return {
        "operation": "new-question",
        "project": str(root),
        "context": context,
        "question_id": question_id,
        "timestamp": timestamp,
        "files": [
            plan_file(brief_relative, "create", brief),
            plan_file("QUESTIONS.md", "update", new_questions, questions),
            *handoff_files,
        ],
    }


def build_new_artifact_plan(
    root: Path,
    *,
    question_id: str,
    analysis_mode: str,
    context: str = "root",
    timestamp: str | None = None,
) -> dict[str, Any]:
    root = root.expanduser().resolve()
    if QUESTION_PATTERN.fullmatch(question_id) is None:
        raise ValueError(f"Invalid Question ID: {question_id}")
    if analysis_mode not in ANALYSIS_MODES:
        raise ValueError(f"Invalid Analysis mode: {analysis_mode}")
    questions, handoff = require_control_files(root)
    _, rows = table_rows(questions, "Q-ID")
    row = next((item for item in rows if item.get("Q-ID") == question_id), None)
    if row is None:
        raise ValueError(f"Question is not registered: {question_id}")
    brief_relative = row.get("Brief", f"docs/questions/{question_id}/BRIEF.md")
    brief_path = root / brief_relative
    if not brief_path.is_file():
        raise ValueError(f"Question BRIEF is missing: {brief_relative}")
    brief = brief_path.read_text(encoding="utf-8")
    if (
        not re.search(r"^Design review:\s*approved\s*$", brief, re.MULTILINE)
        or not re.search(r"^Reviewed at:\s*\S", brief, re.MULTILINE)
        or not re.search(r"^Review rationale:\s*\S", brief, re.MULTILINE)
    ):
        raise ValueError(
            f"Question requires an approved Study Design review receipt: {brief_relative}"
        )
    for heading in (
        "1. Research Question and Decision",
        "2. Hypotheses and Falsifiers",
        "3. Estimand and Inference Unit",
        "4. Study Design and Evidence Eligibility",
        "5. Analysis and Uncertainty",
        "6. Claim-Evidence Matrix",
        "7. Acceptance, Stopping and Risks",
    ):
        match = re.search(
            rf"^##\s+{re.escape(heading)}\s*$\n(.*?)(?=^##\s+|\Z)",
            brief,
            re.MULTILINE | re.DOTALL,
        )
        if match is None or not has_substantive_content(match.group(1)):
            raise ValueError(
                f"Approved Study Design has an empty section in {brief_relative}: {heading}"
            )
    artifact_parent = root / f"explore/{question_id}"
    existing = [path.name for path in artifact_parent.glob("A-*") if path.is_dir()]
    artifact_id = next_id(existing, ARTIFACT_PATTERN, "A")
    timestamp = timestamp or now()
    result_relative = f"explore/{question_id}/{artifact_id}/RESULT.md"
    if (root / result_relative).exists():
        raise ValueError(f"Refusing to overwrite existing path: {result_relative}")
    result = (TEMPLATE_ROOT / "RESULT.md").read_text(encoding="utf-8")
    result = result.replace("Q-XXX", question_id).replace("A-XXX", artifact_id)
    for name, value in (
        ("Question", question_id),
        ("Artifact", artifact_id),
        ("Analysis mode", analysis_mode),
        ("Created", timestamp),
        ("Updated", timestamp),
    ):
        result = replace_field(result, name, value)
    handoff_files = handoff_updates(
        root,
        handoff,
        context=context,
        timestamp=timestamp,
        question_id=question_id,
        artifact_id=artifact_id,
        checkpoint="Artifact record created; no evidence evaluated",
        next_action=f"Record provenance and observed evidence in {result_relative}",
    )
    return {
        "operation": "new-artifact",
        "project": str(root),
        "context": context,
        "question_id": question_id,
        "artifact_id": artifact_id,
        "timestamp": timestamp,
        "files": [plan_file(result_relative, "create", result), *handoff_files],
    }


def apply_plan(plan: dict[str, Any]) -> dict[str, Any]:
    root = Path(plan["project"])
    for item in plan["files"]:
        target = root / item["path"]
        if item["action"] == "create" and target.exists():
            raise ValueError(f"Target appeared after planning: {target}")
        if item["action"] == "update":
            if not target.is_file():
                raise ValueError(f"Update target disappeared after planning: {target}")
            if target.read_text(encoding="utf-8") != item["original"]:
                raise ValueError(f"Update target changed after planning: {target}")
    written: list[str] = []
    for item in plan["files"]:
        target = root / item["path"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(item["content"], encoding="utf-8")
        written.append(item["path"])
    return {"project": str(root), "written": written}


def public_plan(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        **{key: value for key, value in plan.items() if key != "files"},
        "files": [
            {"path": item["path"], "action": item["action"]}
            for item in plan["files"]
        ],
    }


def parse_args(arguments: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command", choices=("new-context", "new-question", "new-artifact")
    )
    parser.add_argument("--project", type=Path, default=Path("."))
    parser.add_argument("--context", default="root")
    parser.add_argument("--question")
    parser.add_argument("--question-id")
    parser.add_argument("--scope")
    parser.add_argument("--analysis-mode", choices=sorted(ANALYSIS_MODES))
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(arguments)


def main(arguments: list[str] | None = None) -> int:
    args = parse_args(arguments)
    try:
        if args.command == "new-context":
            if args.scope is None:
                raise ValueError("new-context requires --scope")
            plan = build_new_context_plan(
                args.project,
                context=args.context,
                scope=args.scope,
            )
        elif args.command == "new-question":
            if args.question is None:
                raise ValueError("new-question requires --question")
            plan = build_new_question_plan(
                args.project, question=args.question, context=args.context
            )
        else:
            if args.question_id is None or args.analysis_mode is None:
                raise ValueError(
                    "new-artifact requires --question-id and --analysis-mode"
                )
            plan = build_new_artifact_plan(
                args.project,
                question_id=args.question_id,
                analysis_mode=args.analysis_mode,
                context=args.context,
            )
        applied = apply_plan(plan) if args.apply else None
        result = {
            "mode": "apply" if args.apply else "dry-run",
            "plan": public_plan(plan),
            "applied": applied,
        }
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"{result['mode']}: {plan['operation']}")
            for item in result["plan"]["files"]:
                print(f"{item['action']}: {item['path']}")
        return 0
    except (OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
