#!/usr/bin/env python3
"""Read-only structural consistency checks for a research project."""

from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath
import re
import sys
from typing import Any


REQUIRED_FILES = (
    "AGENTS.md",
    "QUESTIONS.md",
    "CURRENT_HANDOFF.md",
    "README.md",
    ".gitignore",
)
LEGACY_PATHS = (
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
    "## Reasoning\n\n- 遵循第一性原理、奥卡姆剃刀原理",
    "## Superpowers\n\n- You may use superpowers, but do not write any spec or plan.",
)
QUESTION_COLUMNS = (
    "Q-ID",
    "Research question",
    "Design review",
    "Closure decision",
    "Brief",
    "Updated",
)
DESIGN_REVIEWS = {"pending", "approved", "rejected"}
CLOSURE_DECISIONS = {"open", "answered", "stopped"}
BRIEF_HEADINGS = (
    "1. Research Question and Decision",
    "2. Hypotheses and Falsifiers",
    "3. Estimand and Inference Unit",
    "4. Study Design and Evidence Eligibility",
    "5. Analysis and Uncertainty",
    "6. Claim-Evidence Matrix",
    "7. Acceptance, Stopping and Risks",
)
RESULT_HEADINGS = (
    "1. Question and Claims",
    "2. Provenance Receipt",
    "3. Method and Deviations",
    "4. Observed Evidence",
    "5. Validation",
    "6. Inference",
    "7. Limitations and Applicability",
    "8. Next Decisive Test",
    "9. Human Review",
    "10. Implementation Reuse",
)
ANALYSIS_MODES = {"exploratory", "confirmatory"}
ARTIFACT_STATUSES = {"draft", "review-ready", "reviewed"}
REVIEW_DECISIONS = {"pending", "approved", "rejected"}
REUSE_DECISIONS = {"not-assessed", "approved", "rejected"}
INFERENCE_ASSESSMENTS = {"pending", "support", "contradict", "inconclusive", "context"}
EVIDENCE_RELATIONS = {
    "pending",
    "support",
    "null",
    "negative",
    "contradictory",
    "inconclusive",
}
CONTEXT_COLUMNS = (
    "Context",
    "Scope",
    "Active question",
    "Current artifact",
    "Checkpoint",
    "Blocker",
    "Next decisive action",
    "Handoff",
)


def field(text: str, name: str) -> str:
    match = re.search(
        rf"^{re.escape(name)}:[ \t]*(.*?)[ \t]*$", text, re.MULTILINE
    )
    return match.group(1).strip() if match else ""


def section(text: str, heading: str) -> str:
    match = re.search(
        rf"^##\s+{re.escape(heading)}\s*$\n(?P<body>.*?)(?=^##\s+|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    return match.group("body").strip() if match else ""


def parse_table(
    text: str, required_column: str, errors: list[str], label: str
) -> tuple[list[str], list[dict[str, str]]]:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if not line.startswith("|"):
            continue
        columns = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if required_column not in columns:
            continue
        if index + 1 >= len(lines) or "---" not in lines[index + 1]:
            errors.append(f"{label} table lacks separator row")
            return columns, []
        rows: list[dict[str, str]] = []
        for line_number, row_line in enumerate(lines[index + 2 :], start=index + 3):
            if not row_line.startswith("|"):
                break
            cells = [cell.strip() for cell in row_line.strip().strip("|").split("|")]
            if len(cells) != len(columns):
                errors.append(f"{label} line {line_number} has the wrong column count")
                continue
            rows.append(dict(zip(columns, cells)))
        return columns, rows
    errors.append(f"{label} lacks table column: {required_column}")
    return [], []


def safe_project_path(root: Path, value: str, label: str, errors: list[str]) -> Path | None:
    pure = PurePosixPath(value)
    if not value or pure.is_absolute() or ".." in pure.parts:
        errors.append(f"{label} must be a project-relative path: {value}")
        return None
    candidate = (root / pure).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        errors.append(f"{label} escapes the project: {value}")
        return None
    return candidate


def require_headings(text: str, headings: tuple[str, ...], label: str, errors: list[str]) -> None:
    for heading in headings:
        if f"## {heading}" not in text:
            errors.append(f"{label} lacks heading: {heading}")


def has_substantive_content(body: str) -> bool:
    """Return true when a section contains a value, prose, or a real table row."""
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


def validate_questions(
    root: Path, errors: list[str]
) -> tuple[set[str], dict[str, str], set[str]]:
    path = root / "QUESTIONS.md"
    if not path.is_file():
        return set(), {}, set()
    columns, rows = parse_table(path.read_text(encoding="utf-8"), "Q-ID", errors, "QUESTIONS.md")
    if tuple(columns) != QUESTION_COLUMNS:
        errors.append("QUESTIONS.md columns do not match the research-question contract")
    ids: set[str] = set()
    brief_paths: dict[str, str] = {}
    approved_designs: set[str] = set()
    for row in rows:
        question_id = row.get("Q-ID", "")
        if re.fullmatch(r"Q-\d{3}", question_id) is None:
            errors.append(f"Invalid Question ID: {question_id}")
            continue
        if question_id in ids:
            errors.append(f"Duplicate Question ID: {question_id}")
        ids.add(question_id)
        if row.get("Design review") not in DESIGN_REVIEWS:
            errors.append(f"Invalid Design review for {question_id}")
        if row.get("Closure decision") not in CLOSURE_DECISIONS:
            errors.append(f"Invalid Closure decision for {question_id}")
        expected = f"docs/questions/{question_id}/BRIEF.md"
        if row.get("Brief") != expected:
            errors.append(f"BRIEF path for {question_id} must be {expected}")
            continue
        brief_paths[question_id] = expected
        brief = root / expected
        if not brief.is_file():
            errors.append(f"Missing BRIEF for {question_id}: {expected}")
            continue
        text = brief.read_text(encoding="utf-8")
        require_headings(text, BRIEF_HEADINGS, expected, errors)
        for name in (
            "Q-ID",
            "Created",
            "Updated",
            "Design review",
            "Reviewed at",
            "Review rationale",
            "Closure decision",
            "Closed at",
            "Closure rationale",
        ):
            if re.search(rf"^{re.escape(name)}:", text, re.MULTILINE) is None:
                errors.append(f"{expected} lacks metadata: {name}")
        if field(text, "Q-ID") != question_id:
            errors.append(f"Q-ID mismatch in {expected}")
        if field(text, "Design review") != row.get("Design review"):
            errors.append(f"Design review mismatch between index and {expected}")
        if field(text, "Closure decision") != row.get("Closure decision"):
            errors.append(f"Closure decision mismatch between index and {expected}")
        if field(text, "Updated") != row.get("Updated"):
            errors.append(f"Updated mismatch between index and {expected}")
        if field(text, "Design review") != "pending" and (
            not field(text, "Reviewed at") or not field(text, "Review rationale")
        ):
            errors.append(f"Reviewed design lacks review receipt: {expected}")
        if field(text, "Design review") in {"approved", "rejected"}:
            for heading in BRIEF_HEADINGS:
                if not has_substantive_content(section(text, heading)):
                    errors.append(f"Reviewed design has empty section in {expected}: {heading}")
            matrix = section(text, "6. Claim-Evidence Matrix")
            matrix_columns, matrix_rows = parse_table(
                matrix, "Claim", errors, f"{expected} Claim-Evidence Matrix"
            )
            if tuple(matrix_columns) != (
                "Claim",
                "Decisive evidence",
                "Current evidence",
                "Assessment",
            ):
                errors.append(f"Claim-Evidence Matrix columns are invalid in {expected}")
            claim_ids: set[str] = set()
            for matrix_row in matrix_rows:
                claim = matrix_row.get("Claim", "")
                match = re.fullmatch(r"(C-\d{3}):\s*.+", claim)
                if match is None:
                    errors.append(f"Invalid qualified Claim in {expected}: {claim}")
                elif match.group(1) in claim_ids:
                    errors.append(f"Duplicate Claim ID in {expected}: {match.group(1)}")
                else:
                    claim_ids.add(match.group(1))
        if (
            field(text, "Design review") == "approved"
            and field(text, "Reviewed at")
            and field(text, "Review rationale")
        ):
            approved_designs.add(question_id)
        if field(text, "Closure decision") != "open" and (
            not field(text, "Closed at") or not field(text, "Closure rationale")
        ):
            errors.append(f"Closed Question lacks closure receipt: {expected}")
    return ids, brief_paths, approved_designs


def validate_artifact(
    path: Path,
    root: Path,
    question_ids: set[str],
    approved_designs: set[str],
    errors: list[str],
) -> tuple[str, str] | None:
    label = path.relative_to(root).as_posix()
    text = path.read_text(encoding="utf-8")
    require_headings(text, RESULT_HEADINGS, label, errors)
    question_id = field(text, "Question")
    artifact_id = field(text, "Artifact")
    expected_question = path.parents[1].name
    expected_artifact = path.parent.name
    if question_id != expected_question or question_id not in question_ids:
        errors.append(f"Question ID mismatch in {label}")
    elif question_id not in approved_designs:
        errors.append(f"Artifact lacks an approved Study Design review receipt: {label}")
    if artifact_id != expected_artifact or re.fullmatch(r"A-\d{3}", artifact_id) is None:
        errors.append(f"Artifact ID mismatch in {label}")
    if field(text, "Analysis mode") not in ANALYSIS_MODES:
        errors.append(f"Invalid Analysis mode in {label}")
    if field(text, "Status") not in ARTIFACT_STATUSES:
        errors.append(f"Invalid Artifact status in {label}")
    status = field(text, "Status")
    for name in ("Created", "Updated"):
        if not field(text, name):
            errors.append(f"{label} lacks metadata value: {name}")
    review = section(text, "9. Human Review")
    review_decision = field(review, "Decision")
    if review_decision not in REVIEW_DECISIONS:
        errors.append(f"Invalid Human Review decision in {label}")
    if review_decision != "pending" and (
        not field(review, "Reviewed at") or not field(review, "Review rationale")
    ):
        errors.append(f"Human Review lacks a review receipt in {label}")
    if status == "reviewed" and review_decision not in {"approved", "rejected"}:
        errors.append(f"reviewed Artifact requires a Human Review decision in {label}")
    if review_decision in {"approved", "rejected"} and status != "reviewed":
        errors.append(f"Human Review decision requires Status reviewed in {label}")
    reuse = section(text, "10. Implementation Reuse")
    reuse_decision = field(reuse, "Reuse decision")
    if reuse_decision not in REUSE_DECISIONS:
        errors.append(f"Invalid Implementation Reuse decision in {label}")
    if reuse_decision == "approved":
        for name in ("Target", "Recorded at", "Files"):
            if not field(reuse, name):
                errors.append(f"Approved reuse lacks {name} in {label}")
        reuse_paths = [field(reuse, "Target")]
        reuse_paths.extend(
            value.strip()
            for value in re.split(r"[,\n]", field(reuse, "Files"))
            if value.strip()
        )
        for value in reuse_paths:
            candidate = safe_project_path(root, value, f"Reuse path in {label}", errors)
            if candidate is not None and not candidate.exists():
                errors.append(f"Approved reuse path is missing in {label}: {value}")
    observed = section(text, "4. Observed Evidence")
    evidence_ids: set[str] = set()
    assessed_claims = set(
        re.findall(r"C-\d{3}", field(section(text, "1. Question and Claims"), "Claims assessed"))
    )
    for match in re.finditer(r"^###\s+(E-\d{3})\s*$", observed, re.MULTILINE):
        evidence_id = match.group(1)
        if evidence_id in evidence_ids:
            errors.append(f"Duplicate Evidence ID in {label}: {evidence_id}")
        evidence_ids.add(evidence_id)
        start = match.end()
        next_match = re.search(r"^###\s+", observed[start:], re.MULTILINE)
        body = observed[start : start + next_match.start()] if next_match else observed[start:]
        for name in ("Claim", "Relation", "Source", "Output"):
            if re.search(rf"^{name}:", body, re.MULTILINE) is None:
                errors.append(f"{evidence_id} lacks {name} in {label}")
        claim_id = field(body, "Claim")
        relation = field(body, "Relation")
        if status in {"review-ready", "reviewed"}:
            if claim_id not in assessed_claims:
                errors.append(f"{evidence_id} references unassessed Claim in {label}: {claim_id}")
            if relation not in EVIDENCE_RELATIONS - {"pending"}:
                errors.append(f"{evidence_id} has invalid review Relation in {label}: {relation}")
            for name in (
                "Claim",
                "Relation",
                "Source",
                "Output",
                "Observation",
                "Effect and uncertainty",
            ):
                if not field(body, name):
                    errors.append(f"{evidence_id} lacks {name} value in {label}")
    inference = section(text, "6. Inference")
    assessment = field(inference, "Assessment")
    if assessment not in INFERENCE_ASSESSMENTS:
        errors.append(f"Invalid Inference Assessment in {label}: {assessment}")
    for name in ("Qualified claim", "Uncertainty"):
        if re.search(rf"^{re.escape(name)}:", inference, re.MULTILINE) is None:
            errors.append(f"Inference lacks {name} in {label}")
    if status in {"review-ready", "reviewed"}:
        if not assessed_claims:
            errors.append(f"{label} lacks Claims assessed for review")
        required_sections = (
            "2. Provenance Receipt",
            "4. Observed Evidence",
            "5. Validation",
            "6. Inference",
            "7. Limitations and Applicability",
            "8. Next Decisive Test",
        )
        for heading in required_sections:
            if not has_substantive_content(section(text, heading)):
                errors.append(f"{label} has empty review section: {heading}")
        if re.search(r"^###\s+E-\d{3}\s*$", observed, re.MULTILINE) is None:
            errors.append(f"{label} lacks stable observed Evidence ID")
        if assessment == "pending":
            errors.append(f"{label} retains pending Inference Assessment for review")
        for name in ("Qualified claim", "Uncertainty"):
            if not field(inference, name):
                errors.append(f"{label} lacks {name} value for review")
    return (question_id, artifact_id) if question_id and artifact_id else None


def validate_artifacts(
    root: Path,
    question_ids: set[str],
    approved_designs: set[str],
    errors: list[str],
) -> set[tuple[str, str]]:
    artifact_ids: set[tuple[str, str]] = set()
    explore = root / "explore"
    if not explore.is_dir():
        return artifact_ids
    # Scientific records have a canonical shallow path; do not recursively discover work.
    for result in sorted(explore.glob("Q-???/A-???/RESULT.md")):
        identity = validate_artifact(
            result, root, question_ids, approved_designs, errors
        )
        if identity is None:
            continue
        if identity in artifact_ids:
            errors.append(f"Duplicate Artifact identity: {identity[0]}/{identity[1]}")
        artifact_ids.add(identity)
    return artifact_ids


def validate_local_handoff(
    path: Path,
    root: Path,
    row: dict[str, str],
    question_ids: set[str],
    artifact_ids: set[tuple[str, str]],
    errors: list[str],
) -> None:
    label = path.relative_to(root).as_posix()
    text = path.read_text(encoding="utf-8")
    for name in (
        "Context",
        "Scope",
        "Updated",
        "Active question",
        "Current artifact",
        "Last verified checkpoint",
        "Blocker",
        "Next decisive action",
    ):
        if re.search(rf"^{re.escape(name)}:", text, re.MULTILINE) is None:
            errors.append(f"{label} lacks metadata: {name}")
    for heading in ("Dependencies", "Required Reads"):
        if f"## {heading}" not in text:
            errors.append(f"{label} lacks heading: {heading}")
    if field(text, "Context") != row["Context"]:
        errors.append(f"Context mismatch in {label}")
    if field(text, "Scope") != row["Scope"]:
        errors.append(f"Scope mismatch in {label}")
    mappings = (
        ("Active question", "Active question"),
        ("Current artifact", "Current artifact"),
        ("Last verified checkpoint", "Checkpoint"),
        ("Blocker", "Blocker"),
        ("Next decisive action", "Next decisive action"),
    )
    for local_name, map_name in mappings:
        if field(text, local_name) != row[map_name]:
            errors.append(f"Context Map mismatch for {local_name} in {label}")
    validate_active_ids(row, question_ids, artifact_ids, label, errors)


def validate_active_ids(
    row: dict[str, str],
    question_ids: set[str],
    artifact_ids: set[tuple[str, str]],
    label: str,
    errors: list[str],
) -> None:
    question_id = row.get("Active question", "")
    artifact_id = row.get("Current artifact", "")
    if question_id not in {"", "none"} and question_id not in question_ids:
        errors.append(f"{label} references unknown Question: {question_id}")
    if artifact_id not in {"", "none"}:
        if question_id in {"", "none"}:
            errors.append(f"{label} has Current artifact without Active question")
        elif (question_id, artifact_id) not in artifact_ids:
            errors.append(
                f"{label} references unknown Artifact: {question_id}/{artifact_id}"
            )


def validate_handoffs(
    root: Path,
    question_ids: set[str],
    artifact_ids: set[tuple[str, str]],
    errors: list[str],
) -> None:
    root_handoff = root / "CURRENT_HANDOFF.md"
    if not root_handoff.is_file():
        return
    text = root_handoff.read_text(encoding="utf-8")
    for name in ("Updated", "Active context"):
        if re.search(rf"^{re.escape(name)}:", text, re.MULTILINE) is None:
            errors.append(f"CURRENT_HANDOFF.md lacks metadata: {name}")
    for heading in ("Context Map", "Cross-context Dependencies", "Required Reads"):
        if f"## {heading}" not in text:
            errors.append(f"CURRENT_HANDOFF.md lacks heading: {heading}")
    columns, rows = parse_table(text, "Context", errors, "CURRENT_HANDOFF.md Context Map")
    if tuple(columns) != CONTEXT_COLUMNS:
        errors.append("Context Map columns do not match the hierarchical handoff contract")
    contexts: set[str] = set()
    for row in rows:
        context = row.get("Context", "")
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", context):
            errors.append(f"Invalid Context ID: {context}")
            continue
        if context in contexts:
            errors.append(f"Duplicate Context ID: {context}")
        contexts.add(context)
        scope_value = row.get("Scope", "")
        handoff_value = row.get("Handoff", "")
        scope_path = safe_project_path(root, scope_value, f"Scope for {context}", errors)
        handoff_path = safe_project_path(root, handoff_value, f"Handoff for {context}", errors)
        if scope_path is None or handoff_path is None:
            continue
        if context == "root":
            if scope_value != "." or handoff_value != "CURRENT_HANDOFF.md":
                errors.append("root Context must use scope . and CURRENT_HANDOFF.md")
            validate_active_ids(row, question_ids, artifact_ids, "root Context", errors)
            continue
        expected = (PurePosixPath(scope_value) / "CURRENT_HANDOFF.md").as_posix()
        if handoff_value != expected:
            errors.append(f"Handoff for {context} must be {expected}")
            continue
        if not handoff_path.is_file():
            errors.append(f"Declared local Handoff is missing: {handoff_value}")
            continue
        validate_local_handoff(
            handoff_path, root, row, question_ids, artifact_ids, errors
        )
    if "root" not in contexts:
        errors.append("Context Map lacks the required root Context")
    active_context = field(text, "Active context")
    if active_context not in contexts:
        errors.append(f"Active context is not declared: {active_context}")


def validate_project(root: Path) -> dict[str, Any]:
    root = root.expanduser().resolve()
    errors: list[str] = []
    warnings: list[str] = []
    for relative in REQUIRED_FILES:
        if not (root / relative).is_file():
            errors.append(f"Missing required file: {relative}")
    for relative in LEGACY_PATHS:
        if (root / relative).exists():
            warnings.append(f"Legacy path preserved: {relative}")
    agents = root / "AGENTS.md"
    if agents.is_file():
        text = agents.read_text(encoding="utf-8")
        for invariant in AGENTS_INVARIANTS:
            if invariant not in text:
                errors.append("AGENTS.md invariant is missing or changed")
    question_ids, _, approved_designs = validate_questions(root, errors)
    artifact_ids = validate_artifacts(root, question_ids, approved_designs, errors)
    validate_handoffs(root, question_ids, artifact_ids, errors)
    return {
        "structure_consistent": not errors,
        "scientific_validity": "not_evaluated",
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
        state = "structure-consistent" if result["structure_consistent"] else "structure-inconsistent"
        print(state)
        print("scientific-validity: not-evaluated")
        for warning in result["warnings"]:
            print(f"warning: {warning}")
        for error in result["errors"]:
            print(f"error: {error}")
    return 0 if result["structure_consistent"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
