#!/usr/bin/env python3
"""Read-only validation for a research workflow project."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any


REQUIRED_FILES = (
    "AGENTS.md",
    "QUESTIONS.md",
    "CURRENT_HANDOFF.md",
    "README.md",
    "pixi.toml",
    ".gitignore",
)
REQUIRED_DIRECTORIES = (
    "docs/questions",
    "docs/references/papers",
    "docs/references/official",
    "docs/references/datasets",
    "docs/template",
    "docs/methods",
    "docs/runbooks",
    "explore",
    "pipeline",
    "results",
    "reports",
    "logs",
    "configs",
    "tests",
)
FORBIDDEN_PATHS = (
    "project_manifest.yaml",
    "PLAN.md",
    "SPEC.md",
    "plans/current-plan.md",
    "archive",
    "external",
    "docs/architecture",
    "docs/paradigms",
    "docs/decisions",
    "docs/handoffs/archive",
    "work/audit",
)
AGENTS_INVARIANTS = (
    "## Language\n\n- 面向 human 的说明默认使用中文。 \n"
    "- 专业术语、code、paths、commands、IDs 和 machine-readable values "
    "等agent方便识别的内容保持英文。",
    "## Reasoning\n\n- 遵循第一性原理",
    "## Superpowers\n\n- You may use superpowers, but do not write any spec or plan.",
)
QUESTION_STATUSES = {"拟定", "解决中", "已解决", "废弃"}
ARTIFACT_STATUSES = {"草稿", "待审核", "审核通过", "拒绝"}
WORKSTREAM_STATUSES = {"待启动", "进行中", "已完成", "终止"}
BRIEF_HEADINGS = (
    "1. Human Question",
    "2. Problem Interpretation",
    "3. Context and Scope",
    "4. Evidence Basis",
    "5. Evidence Synthesis",
    "6. Proposed Resolution",
    "7. Inputs, Outputs and Dependencies",
    "8. Validation and Acceptance Criteria",
    "9. Open Questions and Risks",
    "10. Human Review",
    "11. Closure Summary",
)
RESULT_HEADINGS = (
    "1. Objective",
    "2. Inputs",
    "3. Method and Commands",
    "4. Outputs",
    "5. Technical Validation",
    "6. Results",
    "7. Limitations",
    "8. Human Review",
    "9. Promotion",
)


def field(text: str, name: str) -> str:
    match = re.search(rf"^{re.escape(name)}:\s*(.*?)\s*$", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


def section(text: str, heading: str) -> str:
    match = re.search(
        rf"^##\s+{re.escape(heading)}\s*$\n(?P<body>.*?)(?=^##\s+|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    return match.group("body").strip() if match else ""


def parse_questions(text: str) -> tuple[list[dict[str, str]], list[str]]:
    rows: list[dict[str, str]] = []
    errors: list[str] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells[:2] in (["Q-ID", "Question"], ["---", "---"]):
            continue
        if len(cells) != 5:
            errors.append(f"QUESTIONS.md line {line_number} must contain five columns")
            continue
        rows.append(dict(zip(("id", "question", "status", "brief", "updated"), cells)))
    return rows, errors


def validate_question(root: Path, row: dict[str, str], errors: list[str]) -> None:
    question_id = row["id"]
    if re.fullmatch(r"Q-\d{3}", question_id) is None:
        errors.append(f"Invalid Question ID: {question_id}")
        return
    if row["status"] not in QUESTION_STATUSES:
        errors.append(f"Invalid Question status for {question_id}: {row['status']}")
    expected = f"docs/questions/{question_id}/BRIEF.md"
    if row["brief"] != expected:
        errors.append(f"BRIEF path for {question_id} must be {expected}")
        return
    brief = root / expected
    if not brief.is_file():
        errors.append(f"Missing BRIEF for {question_id}: {expected}")
        return
    text = brief.read_text(encoding="utf-8")
    for heading in BRIEF_HEADINGS:
        if f"## {heading}" not in text:
            errors.append(f"{expected} lacks heading: {heading}")
    if field(text, "Status") != row["status"]:
        errors.append(f"Status mismatch between index and {expected}")
    review = field(text, "Human review status")
    if row["status"] in {"已解决", "废弃"} and review.lower() in {"", "pending"}:
        errors.append(f"{question_id} final status requires Human review")


def validate_artifacts(root: Path, errors: list[str]) -> None:
    explore = root / "explore"
    if not explore.is_dir():
        return
    for question_root in sorted(explore.iterdir()):
        if not question_root.is_dir():
            continue
        if re.fullmatch(r"Q-\d{3}", question_root.name) is None:
            errors.append(f"Invalid directory in explore/: {question_root.name}")
            continue
        for artifact_root in sorted(question_root.iterdir()):
            if not artifact_root.is_dir():
                errors.append(f"Unexpected file in {question_root.relative_to(root)}")
                continue
            if re.fullmatch(r"A-\d{3}", artifact_root.name) is None:
                errors.append(f"Invalid Artifact ID: {artifact_root.name}")
                continue
            result_path = artifact_root / "RESULT.md"
            label = result_path.relative_to(root).as_posix()
            if not result_path.is_file():
                errors.append(f"Missing RESULT.md: {label}")
                continue
            text = result_path.read_text(encoding="utf-8")
            for heading in RESULT_HEADINGS:
                if f"## {heading}" not in text:
                    errors.append(f"{label} lacks heading: {heading}")
            if field(text, "Question") != question_root.name:
                errors.append(f"Question ID mismatch in {label}")
            if field(text, "Artifact") != artifact_root.name:
                errors.append(f"Artifact ID mismatch in {label}")
            status = field(text, "Status")
            if status not in ARTIFACT_STATUSES:
                errors.append(f"Invalid Artifact status in {label}: {status}")
            validation = section(text, "5. Technical Validation")
            decision = field(section(text, "8. Human Review"), "Decision")
            promotion = section(text, "9. Promotion")
            if status in {"待审核", "审核通过"} and not validation:
                errors.append(f"{label} lacks technical validation")
            if status == "审核通过" and decision != "审核通过":
                errors.append(f"{label} lacks Human approval")
            if status == "拒绝" and decision != "拒绝":
                errors.append(f"{label} lacks Human rejection")
            if field(promotion, "Pipeline target") and status != "审核通过":
                errors.append(f"Unapproved Artifact has promotion facts: {label}")


def validate_handoff(root: Path, errors: list[str]) -> None:
    path = root / "CURRENT_HANDOFF.md"
    if not path.is_file():
        return
    text = path.read_text(encoding="utf-8")
    if len(text) > 2_000:
        errors.append("CURRENT_HANDOFF.md exceeds 2,000 characters")
    for heading in (
        "1. 当前目标",
        "2. 当前问题摘要",
        "3. 跨工作流状态",
        "4. 最近完成",
        "5. 当前阻塞",
        "6. 立即下一步",
        "7. 验证",
        "8. 读取路由",
    ):
        if f"## {heading}" not in text:
            errors.append(f"CURRENT_HANDOFF.md lacks heading: {heading}")
    status = field(text, "Status")
    if status not in WORKSTREAM_STATUSES:
        errors.append(f"Invalid active Workstream status: {status}")
    for line in section(text, "3. 跨工作流状态").splitlines():
        if not line.startswith("|") or "---" in line or "Workstream" in line:
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and cells[1] not in WORKSTREAM_STATUSES:
            errors.append(f"Invalid Workstream status in handoff: {cells[1]}")
    active = field(text, "Active question")
    if active not in {"", "none"}:
        if re.fullmatch(r"Q-\d{3}", active) is None:
            errors.append(f"Invalid active Question: {active}")
        elif not (root / f"docs/questions/{active}/BRIEF.md").is_file():
            errors.append(f"Active Question BRIEF is missing: {active}")


def validate_pipeline(root: Path, errors: list[str]) -> None:
    pipeline = root / "pipeline"
    if not pipeline.is_dir():
        return
    pattern = re.compile(r"(?:\.\./)*docs/template/|docs[\\/]+template[\\/]+")
    for path in pipeline.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {
            ".md",
            ".py",
            ".r",
            ".sh",
            ".toml",
            ".yaml",
            ".yml",
            ".json",
        }:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if pattern.search(text):
            errors.append(
                "Pipeline directly depends on docs/template/: "
                + path.relative_to(root).as_posix()
            )


def validate_project(root: Path) -> dict[str, Any]:
    root = root.expanduser().resolve()
    errors: list[str] = []
    warnings: list[str] = []
    for relative in REQUIRED_FILES:
        if not (root / relative).is_file():
            errors.append(f"Missing required file: {relative}")
    for relative in REQUIRED_DIRECTORIES:
        if not (root / relative).is_dir():
            errors.append(f"Missing required directory: {relative}/")
    for relative in FORBIDDEN_PATHS:
        if (root / relative).exists():
            errors.append(f"Forbidden legacy path exists: {relative}")
    agents = root / "AGENTS.md"
    if agents.is_file():
        text = agents.read_text(encoding="utf-8")
        for invariant in AGENTS_INVARIANTS:
            if invariant not in text:
                errors.append("AGENTS.md invariant is missing or changed")
    questions = root / "QUESTIONS.md"
    if questions.is_file():
        rows, row_errors = parse_questions(questions.read_text(encoding="utf-8"))
        errors.extend(row_errors)
        if not rows:
            warnings.append("No Question is registered")
        ids: set[str] = set()
        for row in rows:
            if row["id"] in ids:
                errors.append(f"Duplicate Question ID: {row['id']}")
            ids.add(row["id"])
            validate_question(root, row, errors)
    validate_handoff(root, errors)
    validate_artifacts(root, errors)
    validate_pipeline(root, errors)
    return {
        "ok": not errors,
        "project": str(root),
        "errors": errors,
        "warnings": warnings,
    }


def parse_args(arguments: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path("."))
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(arguments)


def main(arguments: list[str] | None = None) -> int:
    args = parse_args(arguments)
    try:
        result = validate_project(args.project)
    except OSError as error:
        print(str(error), file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print("valid" if result["ok"] else "invalid")
        for warning in result["warnings"]:
            print(f"warning: {warning}")
        for error in result["errors"]:
            print(f"error: {error}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
