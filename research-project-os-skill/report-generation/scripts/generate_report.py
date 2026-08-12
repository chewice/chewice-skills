#!/usr/bin/env python3
"""Generate or validate a question-centred HTML research report."""

from __future__ import annotations

import argparse
import hashlib
from html import escape
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
from typing import Any
from urllib.parse import unquote, urlparse

from markdown_it import MarkdownIt


SKILL_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = SKILL_ROOT / "assets/templates/report.html"
CSS = SKILL_ROOT / "assets/css/report.css"
QUESTION_PATTERN = re.compile(r"Q-\d{3}")
ARTIFACT_PATTERN = re.compile(r"A-\d{3}")
EVIDENCE_PATTERN = re.compile(r"E-\d{3}")
CLAIM_PATTERN = re.compile(r"C-\d{3}")
LINK_PATTERN = re.compile(r"(?P<image>!)?\[(?P<label>[^\]]*)\]\((?P<url>[^)\s]+)\)")
FORBIDDEN_PATTERN = re.compile(r"(?i)(?:javascript|vbscript|file|data):")
PLACEHOLDERS = ("尚未填写", "TODO", "TBD")
RELATIONS = {"support", "null", "negative", "contradictory", "inconclusive"}
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


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def markdown_field(text: str, name: str) -> str:
    match = re.search(
        rf"^{re.escape(name)}:[ \t]*(.*?)[ \t]*$", text, re.MULTILINE
    )
    return match.group(1).strip() if match else ""


def markdown_section(text: str, heading: str) -> str:
    match = re.search(
        rf"^##\s+{re.escape(heading)}\s*$\n(?P<body>.*?)(?=^##\s+|\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    return match.group("body").strip() if match else ""


def require_sections(text: str, headings: tuple[str, ...], label: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    for heading in headings:
        body = markdown_section(text, heading)
        meaningful_lines = []
        for line in body.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("### "):
                continue
            if re.fullmatch(r"[^:|]+:\s*", stripped):
                continue
            if stripped.startswith("|") and set(stripped.replace("|", "").strip()) <= {
                "-",
                ":",
            }:
                continue
            meaningful_lines.append(stripped)
        if not body or not meaningful_lines:
            raise ValueError(f"{label} lacks substantive section: {heading}")
        if any(value.lower() in body.lower() for value in PLACEHOLDERS):
            raise ValueError(f"{label} contains placeholder in section: {heading}")
        sections[heading] = body
    return sections


def parse_markdown_table(text: str, required: tuple[str, ...], label: str) -> list[dict[str, str]]:
    lines = [line.strip() for line in text.splitlines() if line.strip().startswith("|")]
    for index in range(len(lines) - 1):
        headers = [cell.strip() for cell in lines[index].strip("|").split("|")]
        separator = [cell.strip() for cell in lines[index + 1].strip("|").split("|")]
        if headers != list(required) or len(separator) != len(headers):
            continue
        if not all(re.fullmatch(r":?-{3,}:?", cell) for cell in separator):
            continue
        rows: list[dict[str, str]] = []
        for line in lines[index + 2 :]:
            cells = [cell.strip() for cell in line.strip("|").split("|")]
            if len(cells) != len(headers):
                break
            if not all(cells):
                raise ValueError(f"{label} contains an incomplete table row")
            rows.append(dict(zip(headers, cells)))
        if not rows:
            raise ValueError(f"{label} table has no evidence rows")
        return rows
    raise ValueError(f"{label} lacks the required table contract")


def safe_path(root: Path, value: Path, *, must_exist: bool = False) -> Path:
    resolved = value.expanduser().resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"Path escapes project: {value}")
    if must_exist and not resolved.is_file():
        raise ValueError(f"Required file is missing: {value}")
    if resolved.is_symlink():
        raise ValueError(f"Symlink is not accepted: {value}")
    return resolved


def question_row(root: Path, question_id: str) -> dict[str, str]:
    path = root / "QUESTIONS.md"
    if not path.is_file():
        raise ValueError("Missing QUESTIONS.md")
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.startswith("|"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) == 6 and cells[0] == question_id:
            return dict(
                zip(
                    (
                        "id",
                        "research_question",
                        "design_review",
                        "closure_decision",
                        "brief",
                        "updated",
                    ),
                    cells,
                )
            )
    raise ValueError(f"Question is not registered with the current schema: {question_id}")


def human_review_decision(text: str) -> str:
    return markdown_field(markdown_section(text, "9. Human Review"), "Decision")


def select_artifact_ids(root: Path, question_id: str, requested: list[str]) -> tuple[list[str], bool]:
    if len(set(requested)) != len(requested):
        raise ValueError("Artifact IDs must be unique")
    if requested:
        return requested, False
    artifact_root = root / "explore" / question_id
    eligible: list[str] = []
    if artifact_root.is_dir():
        for candidate in sorted(artifact_root.iterdir()):
            result = candidate / "RESULT.md"
            if (
                candidate.is_dir()
                and ARTIFACT_PATTERN.fullmatch(candidate.name)
                and result.is_file()
            ):
                text = result.read_text(encoding="utf-8")
                if markdown_field(text, "Status") == "reviewed" and human_review_decision(text) == "approved":
                    eligible.append(candidate.name)
    if len(eligible) == 1:
        return eligible, True
    if not eligible:
        raise ValueError(f"No reviewed and Human-approved Artifact is available for {question_id}")
    rendered = ", ".join(eligible)
    raise ValueError(
        f"Multiple eligible Artifacts may change report scope ({rendered}); specify --artifact"
    )


def parse_evidence_blocks(text: str, artifact_id: str) -> dict[str, dict[str, str]]:
    section = markdown_section(text, "4. Observed Evidence")
    matches = list(re.finditer(r"^###\s+(E-\d{3})\s*$", section, re.MULTILINE))
    if not matches:
        raise ValueError(f"{artifact_id} has no E-NNN blocks in Observed Evidence")
    evidence: dict[str, dict[str, str]] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(section)
        body = section[match.end() : end].strip()
        evidence_id = match.group(1)
        values = {
            "claim": markdown_field(body, "Claim"),
            "relation": markdown_field(body, "Relation"),
            "source": markdown_field(body, "Source"),
            "output": markdown_field(body, "Output"),
            "observation": markdown_field(body, "Observation"),
            "effect_and_uncertainty": markdown_field(body, "Effect and uncertainty"),
        }
        if values["relation"] not in RELATIONS:
            raise ValueError(f"{artifact_id}/{evidence_id} has invalid Relation")
        if not all(values.values()):
            raise ValueError(
                f"{artifact_id}/{evidence_id} lacks claim, source, output, observation, or uncertainty"
            )
        evidence[evidence_id] = values
    return evidence


def validated_inputs(
    root: Path,
    question_id: str,
    artifact_ids: list[str],
) -> tuple[dict[str, str], Path, dict[str, dict[str, Any]], bool]:
    if QUESTION_PATTERN.fullmatch(question_id) is None:
        raise ValueError("Question must match Q-NNN")
    row = question_row(root, question_id)
    expected_brief = f"docs/questions/{question_id}/BRIEF.md"
    if row["brief"] != expected_brief:
        raise ValueError(f"Question BRIEF path must be {expected_brief}")
    if row["design_review"] != "approved":
        raise ValueError("Question Design review must be approved before reporting")
    brief = safe_path(root, root / expected_brief, must_exist=True)
    brief_text = brief.read_text(encoding="utf-8")
    if markdown_field(brief_text, "Q-ID") != question_id:
        raise ValueError("BRIEF Q-ID does not match Question")
    if markdown_field(brief_text, "Design review") != "approved":
        raise ValueError("BRIEF Design review must be exactly approved")
    if not markdown_field(brief_text, "Reviewed at") or not markdown_field(
        brief_text, "Review rationale"
    ):
        raise ValueError("BRIEF lacks the Design review receipt")
    closure = markdown_field(brief_text, "Closure decision")
    if closure not in {"open", "answered", "stopped"} or closure != row["closure_decision"]:
        raise ValueError("BRIEF Closure decision conflicts with QUESTIONS.md")
    if closure != "open" and (
        not markdown_field(brief_text, "Closed at")
        or not markdown_field(brief_text, "Closure rationale")
    ):
        raise ValueError("Closed Question lacks closure time or rationale")
    brief_sections = require_sections(brief_text, BRIEF_HEADINGS, "BRIEF")
    parse_markdown_table(
        brief_sections["2. Hypotheses and Falsifiers"],
        (
            "Hypothesis",
            "Alternative explanation",
            "Falsifier or observation that changes the judgement",
        ),
        "BRIEF Hypotheses and Falsifiers",
    )
    planned_claim_rows = parse_markdown_table(
        brief_sections["6. Claim-Evidence Matrix"],
        (
            "Claim",
            "Decisive evidence",
            "Current evidence",
            "Assessment",
        ),
        "BRIEF Claim-Evidence Matrix",
    )
    planned_claim_ids: set[str] = set()
    for planned in planned_claim_rows:
        match = re.match(r"(C-\d{3})(?:\s*:\s*|\s+)", planned["Claim"])
        if match is None:
            raise ValueError("BRIEF Claim must begin with C-NNN and a qualified claim")
        planned_claim_ids.add(match.group(1))

    selected, auto_selected = select_artifact_ids(root, question_id, artifact_ids)
    artifacts: dict[str, dict[str, Any]] = {}
    for artifact_id in selected:
        if ARTIFACT_PATTERN.fullmatch(artifact_id) is None:
            raise ValueError(f"Artifact must match A-NNN: {artifact_id}")
        result = safe_path(
            root,
            root / f"explore/{question_id}/{artifact_id}/RESULT.md",
            must_exist=True,
        )
        text = result.read_text(encoding="utf-8")
        if markdown_field(text, "Question") != question_id:
            raise ValueError(f"Question mismatch in {result}")
        if markdown_field(text, "Artifact") != artifact_id:
            raise ValueError(f"Artifact mismatch in {result}")
        if markdown_field(text, "Analysis mode") not in {"exploratory", "confirmatory"}:
            raise ValueError(f"Artifact has invalid Analysis mode: {artifact_id}")
        if markdown_field(text, "Status") != "reviewed":
            raise ValueError(f"Artifact is not reviewed: {artifact_id}")
        sections = require_sections(text, RESULT_HEADINGS, artifact_id)
        review = sections["9. Human Review"]
        if markdown_field(review, "Decision") != "approved":
            raise ValueError(f"Artifact lacks Human approval for report inclusion: {artifact_id}")
        if not markdown_field(review, "Reviewed at") or not markdown_field(
            review, "Review rationale"
        ):
            raise ValueError(f"Artifact lacks Human review receipt: {artifact_id}")
        reuse = markdown_field(sections["10. Implementation Reuse"], "Reuse decision")
        if reuse not in {"not-assessed", "approved", "rejected"}:
            raise ValueError(f"Artifact has invalid Reuse decision: {artifact_id}")
        evidence = parse_evidence_blocks(text, artifact_id)
        assessed_claim_ids = set(
            CLAIM_PATTERN.findall(markdown_field(sections["1. Question and Claims"], "Claims assessed"))
        )
        if not assessed_claim_ids:
            raise ValueError(f"Artifact has no stable C-NNN in Claims assessed: {artifact_id}")
        for evidence_id, record in evidence.items():
            if record["claim"] not in assessed_claim_ids:
                raise ValueError(
                    f"{artifact_id}/{evidence_id} Claim is not listed in Claims assessed"
                )
            if record["claim"] not in planned_claim_ids:
                raise ValueError(
                    f"{artifact_id}/{evidence_id} Claim is absent from the BRIEF matrix"
                )
        inference = sections["6. Inference"]
        assessment = markdown_field(inference, "Assessment")
        qualified_claim = markdown_field(inference, "Qualified claim")
        uncertainty = markdown_field(inference, "Uncertainty")
        if assessment not in {"support", "contradict", "inconclusive", "context"}:
            raise ValueError(f"Artifact has pending or invalid Inference Assessment: {artifact_id}")
        if not qualified_claim or not uncertainty:
            raise ValueError(f"Artifact lacks Qualified claim or Uncertainty: {artifact_id}")
        artifacts[artifact_id] = {
            "path": result,
            "text": text,
            "sections": sections,
            "evidence": evidence,
            "assessment": assessment,
            "qualified_claim": qualified_claim,
            "uncertainty": uncertainty,
            "review_decision": "approved",
            "reuse_decision": reuse,
        }
    return row, brief, artifacts, auto_selected


def rewrite_resources(
    text: str,
    *,
    source: Path,
    root: Path,
    records: dict[str, dict[str, Any]],
) -> str:
    def replace(match: re.Match[str]) -> str:
        raw_url = match.group("url")
        image = bool(match.group("image"))
        if raw_url.startswith("#"):
            return match.group(0)
        parsed = urlparse(raw_url)
        if parsed.scheme or parsed.netloc:
            if not image and parsed.scheme == "https":
                return match.group(0)
            raise ValueError(f"Remote image or unsafe URL is forbidden: {raw_url}")
        decoded = unquote(parsed.path)
        candidate = Path(decoded)
        if candidate.is_absolute():
            raise ValueError(f"Absolute report resource is forbidden: {raw_url}")
        resource = safe_path(root, source.parent / candidate, must_exist=True)
        digest = sha256_file(resource)
        target_name = f"{digest[:10]}-{resource.name}"
        records[target_name] = {
            "source": resource.relative_to(root).as_posix(),
            "target": f"assets/{target_name}",
            "sha256": digest,
            "size": resource.stat().st_size,
        }
        prefix = "!" if image else ""
        return f"{prefix}[{match.group('label')}](assets/{target_name})"

    return LINK_PATTERN.sub(replace, text)


def validate_source_links(text: str) -> None:
    """Reject active or remote image links even in source fields not rendered."""
    for match in LINK_PATTERN.finditer(text):
        raw_url = match.group("url")
        if raw_url.startswith("#"):
            continue
        parsed = urlparse(raw_url)
        if parsed.scheme or parsed.netloc:
            if match.group("image") or parsed.scheme != "https":
                raise ValueError(f"Remote image or unsafe URL is forbidden: {raw_url}")


def source_anchor(artifact_id: str, section: str, evidence_id: str | None = None) -> str:
    suffix = f" / {evidence_id}" if evidence_id else ""
    return f"{artifact_id} §{section}{suffix}"


def build_plan(
    root: Path,
    question_id: str,
    artifact_ids: list[str] | None = None,
    *,
    title: str | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    root = root.expanduser().resolve()
    row, brief, artifacts, auto_selected = validated_inputs(
        root, question_id, artifact_ids or []
    )
    selected = list(artifacts)
    output = safe_path(root, root / f"reports/{question_id}/report.html")
    metadata_path = output.with_suffix(".build.json")
    if not overwrite and (output.exists() or metadata_path.exists()):
        raise FileExistsError(f"Report output already exists: {output}")

    closure = row["closure_decision"]
    report_type = (
        "结论报告"
        if closure == "answered"
        else "停止报告（问题未回答）"
        if closure == "stopped"
        else "阶段性报告"
    )
    records: dict[str, dict[str, Any]] = {}
    brief_text = brief.read_text(encoding="utf-8")
    validate_source_links(brief_text)
    for artifact in artifacts.values():
        validate_source_links(artifact["text"])
    parts = [
        f"# {title or row['research_question']}",
        f"> **{report_type}** · Closure decision: `{closure}`",
        (
            "> Human approval 只决定材料可纳入报告；不等同于 scientific validity、"
            "technical validation 或 implementation reuse。"
        ),
        "## 1. 科研问题与设计边界",
    ]
    for heading, display in (
        ("1. Research Question and Decision", "Research question and decision"),
        ("2. Hypotheses and Falsifiers", "Hypotheses and falsifiers"),
        ("3. Estimand and Inference Unit", "Estimand and inference unit"),
        ("4. Study Design and Evidence Eligibility", "Study design and evidence eligibility"),
        ("5. Analysis and Uncertainty", "Planned analysis and uncertainty"),
        ("6. Claim-Evidence Matrix", "Planned claim-evidence criteria"),
        ("7. Acceptance, Stopping and Risks", "Acceptance, stopping and risks"),
    ):
        parts.extend(
            [
                f"### {display}",
                rewrite_resources(
                    markdown_section(brief_text, heading),
                    source=brief,
                    root=root,
                    records=records,
                ),
            ]
        )

    parts.append("## 2. Claim-Evidence 综合")
    claim_table = [
        (
            "| Claim | Artifact | Evidence | Relation | Inference assessment "
            "| Qualified claim | Source anchors |"
        ),
        "|---|---|---|---|---|---|---|",
    ]
    source_map: list[dict[str, Any]] = []
    relation_counts = {relation: 0 for relation in sorted(RELATIONS)}
    claim_relations: dict[str, set[str]] = {}
    for artifact_id, artifact in artifacts.items():
        for evidence_id, evidence in artifact["evidence"].items():
            relation = evidence["relation"]
            relation_counts[relation] += 1
            claim_relations.setdefault(evidence["claim"], set()).add(relation)
            evidence_anchor = source_anchor(artifact_id, "4", evidence_id)
            inference_anchor = source_anchor(artifact_id, "6")
            claim_text = evidence["claim"].replace("|", "\\|")
            qualified = artifact["qualified_claim"].replace("|", "\\|")
            claim_table.append(
                f"| {claim_text} | {artifact_id} | {evidence_id} | {relation} "
                f"| {artifact['assessment']} | {qualified} "
                f"| `{evidence_anchor}`; `{inference_anchor}` |"
            )
            source_map.append(
                {
                    "artifact": artifact_id,
                    "claim": evidence["claim"],
                    "evidence_id": evidence_id,
                    "relation": relation,
                    "inference_assessment": artifact["assessment"],
                    "qualified_claim": artifact["qualified_claim"],
                    "uncertainty": artifact["uncertainty"],
                    "result": artifact["path"].relative_to(root).as_posix(),
                    "anchors": [
                        source_anchor(artifact_id, "2"),
                        evidence_anchor,
                        source_anchor(artifact_id, "5"),
                        inference_anchor,
                        source_anchor(artifact_id, "7"),
                        source_anchor(artifact_id, "8"),
                    ],
                    "source": evidence["source"],
                    "output": evidence["output"],
                }
            )
    parts.append("\n".join(claim_table))
    parts.extend(["", "### Evidence relation summary"])
    for relation in ("support", "null", "negative", "contradictory", "inconclusive"):
        parts.append(f"- `{relation}`: {relation_counts[relation]}")
    conflicts = [
        f"{claim_id}: {', '.join(sorted(relations))}"
        for claim_id, relations in claim_relations.items()
        if len(relations) > 1
    ]
    if conflicts:
        parts.extend(
            [
                "",
                "### 保留的跨 Artifact 冲突或混合证据",
                *[f"- {item}" for item in conflicts],
            ]
        )

    parts.append("## 3. Observed Evidence")
    for artifact_id, artifact in artifacts.items():
        parts.append(f"### {artifact_id}")
        for evidence_id, evidence in artifact["evidence"].items():
            anchor = source_anchor(artifact_id, "4", evidence_id)
            source = rewrite_resources(
                evidence["source"],
                source=artifact["path"],
                root=root,
                records=records,
            )
            evidence_output = rewrite_resources(
                evidence["output"],
                source=artifact["path"],
                root=root,
                records=records,
            )
            observation = rewrite_resources(
                evidence["observation"],
                source=artifact["path"],
                root=root,
                records=records,
            )
            uncertainty = rewrite_resources(
                evidence["effect_and_uncertainty"],
                source=artifact["path"],
                root=root,
                records=records,
            )
            parts.extend(
                [
                    f"#### {evidence_id} · `{evidence['relation']}`",
                    f"Source anchor: `{anchor}`",
                    f"- Claim: {evidence['claim']}",
                    f"- Source: {source}",
                    f"- Output: {evidence_output}",
                    f"- Observation: {observation}",
                    f"- Effect and uncertainty: {uncertainty}",
                ]
            )

    for heading, section_number in (
        ("Validation and Robustness", "5"),
        ("Inference and Qualified Claims", "6"),
        ("Uncertainty, Limitations and Applicability", "7"),
        ("Next Decisive Test", "8"),
    ):
        parts.append(f"## {heading}")
        for artifact_id, artifact in artifacts.items():
            parts.extend(
                [
                    f"### {artifact_id}",
                    f"Source anchor: `{source_anchor(artifact_id, section_number)}`",
                    rewrite_resources(
                        artifact["sections"][f"{section_number}. " + {
                            "5": "Validation",
                            "6": "Inference",
                            "7": "Limitations and Applicability",
                            "8": "Next Decisive Test",
                        }[section_number]],
                        source=artifact["path"],
                        root=root,
                        records=records,
                    ),
                ]
            )

    parts.extend(
        [
            "## Provenance Appendix",
            f"- BRIEF: `{brief.relative_to(root).as_posix()}`",
        ]
    )
    for artifact_id, artifact in artifacts.items():
        parts.append(
            f"- {artifact_id}: `{artifact['path'].relative_to(root).as_posix()}` · "
            f"Human review=`{artifact['review_decision']}` · "
            f"Implementation reuse=`{artifact['reuse_decision']}`"
        )
        parts.extend(
            [
                f"  - Reproducibility receipt · `{source_anchor(artifact_id, '2')}`",
                rewrite_resources(
                    artifact["sections"]["2. Provenance Receipt"],
                    source=artifact["path"],
                    root=root,
                    records=records,
                ),
            ]
        )
    parts.append(
        "- Validation 只证明所声明的检查通过；不会自动把 observation 升格为 scientific support。"
    )

    markdown = "\n\n".join(parts)
    renderer = MarkdownIt("commonmark", {"html": False}).enable("table")
    body = renderer.render(markdown)
    rendered_title = title or row["research_question"]
    html = (
        TEMPLATE.read_text(encoding="utf-8")
        .replace("{{TITLE}}", escape(rendered_title))
        .replace("{{CSS}}", CSS.read_text(encoding="utf-8"))
        .replace("{{QUESTION}}", escape(question_id))
        .replace("{{ARTIFACTS}}", escape(", ".join(selected)))
        .replace("{{REPORT_TYPE}}", escape(report_type))
        .replace("{{BODY}}", body)
    )
    sources = [brief, *[artifact["path"] for artifact in artifacts.values()]]
    source_records = [
        {"path": source.relative_to(root).as_posix(), "sha256": sha256_file(source)}
        for source in sources
    ]
    metadata = {
        "schema_version": "2.0.0",
        "question": question_id,
        "closure_decision": closure,
        "report_type": report_type,
        "artifacts": selected,
        "artifact_selection": "automatic" if auto_selected else "explicit",
        "output": output.relative_to(root).as_posix(),
        "output_sha256": hashlib.sha256(html.encode("utf-8")).hexdigest(),
        "sources": source_records,
        "source_map": source_map,
        "assets": [records[name] for name in sorted(records)],
        "renderer": "markdown-it-py",
    }
    return {
        "root": str(root),
        "output": str(output),
        "metadata_path": str(metadata_path),
        "html": html,
        "metadata": metadata,
        "assets": [records[name] for name in sorted(records)],
        "overwrite": overwrite,
        "auto_selected": auto_selected,
    }


def atomic_copy(source: Path, target: Path) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    os.close(descriptor)
    temporary_path = Path(temporary)
    try:
        shutil.copy2(source, temporary_path)
        os.replace(temporary_path, target)
    finally:
        temporary_path.unlink(missing_ok=True)


def atomic_write(path: Path, content: str) -> None:
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def apply_plan(plan: dict[str, Any]) -> dict[str, Any]:
    root = Path(plan["root"])
    output = Path(plan["output"])
    metadata_path = Path(plan["metadata_path"])
    if not plan["overwrite"] and (output.exists() or metadata_path.exists()):
        raise FileExistsError(f"Report output appeared after planning: {output}")
    for source in plan["metadata"]["sources"]:
        path = safe_path(root, root / source["path"], must_exist=True)
        if sha256_file(path) != source["sha256"]:
            raise ValueError(f"Report source changed after planning: {path}")
    output.parent.mkdir(parents=True, exist_ok=True)
    assets_root = output.parent / "assets"
    if plan["assets"]:
        assets_root.mkdir(parents=True, exist_ok=True)
    for record in plan["assets"]:
        source = safe_path(root, root / record["source"], must_exist=True)
        if sha256_file(source) != record["sha256"]:
            raise ValueError(f"Report resource changed after planning: {source}")
        target = output.parent / record["target"]
        if target.exists() and not plan["overwrite"]:
            raise FileExistsError(f"Report asset already exists: {target}")
        atomic_copy(source, target)
    atomic_write(output, plan["html"])
    atomic_write(
        metadata_path,
        json.dumps(plan["metadata"], ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    result = validate_report(root, output)
    if not result["ok"]:
        raise ValueError("; ".join(result["errors"]))
    return {"output": str(output), "metadata": str(metadata_path)}


def validate_report(root: Path, output: Path) -> dict[str, Any]:
    root = root.expanduser().resolve()
    output = safe_path(root, output, must_exist=True)
    errors: list[str] = []
    relative = output.relative_to(root).as_posix()
    match = re.fullmatch(r"reports/(Q-\d{3})/report\.html", relative)
    if match is None:
        return {"ok": False, "errors": ["Report path must be reports/<Q-ID>/report.html"]}
    metadata_path = output.with_suffix(".build.json")
    if not metadata_path.is_file():
        return {"ok": False, "errors": ["Missing report build metadata"]}
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("schema_version") != "2.0.0":
            errors.append("Report metadata schema is not 2.0.0")
        if metadata.get("question") != match.group(1):
            errors.append("Question does not match report path")
        if metadata.get("output_sha256") != sha256_file(output):
            errors.append("Report HTML hash mismatch")
        html = output.read_text(encoding="utf-8")
        for required in (
            '<html lang="zh-CN">',
            '<meta charset="utf-8">',
            "<main>",
            "Claim-Evidence 综合",
            "Observed Evidence",
            "Validation and Robustness",
            "Inference and Qualified Claims",
            "Next Decisive Test",
            "Provenance Appendix",
            "Human approval 只决定材料可纳入报告",
        ):
            if required not in html:
                errors.append(f"Missing report contract: {required}")
        if FORBIDDEN_PATTERN.search(html) or "<script" in html.lower():
            errors.append("Report contains forbidden active content")
        for placeholder in PLACEHOLDERS:
            if placeholder.lower() in html.lower():
                errors.append(f"Report contains placeholder: {placeholder}")
        artifacts = metadata.get("artifacts")
        if not isinstance(artifacts, list) or not artifacts:
            errors.append("Artifact metadata is malformed")
            artifacts = []
        try:
            row, _, _, _ = validated_inputs(
                root, metadata.get("question", ""), artifacts
            )
            expected_type = (
                "结论报告"
                if row["closure_decision"] == "answered"
                else "停止报告（问题未回答）"
                if row["closure_decision"] == "stopped"
                else "阶段性报告"
            )
            if metadata.get("report_type") != expected_type:
                errors.append("Report type conflicts with Question closure")
        except ValueError as error:
            errors.append(str(error))
        source_map = metadata.get("source_map")
        if not isinstance(source_map, list) or not source_map:
            errors.append("Report lacks a claim-evidence source_map")
        else:
            for record in source_map:
                if record.get("relation") not in RELATIONS:
                    errors.append("source_map contains an invalid evidence relation")
                if not record.get("claim") or not record.get("evidence_id"):
                    errors.append("source_map contains an unanchored claim")
                if record.get("inference_assessment") not in {
                    "support",
                    "contradict",
                    "inconclusive",
                    "context",
                }:
                    errors.append("source_map contains an invalid inference assessment")
                if not record.get("qualified_claim") or not record.get("uncertainty"):
                    errors.append("source_map lacks a qualified claim or uncertainty")
                for anchor in record.get("anchors", []):
                    if anchor not in html:
                        errors.append(f"Report omits source anchor: {anchor}")
        for record in metadata.get("sources", []):
            path = safe_path(root, root / record["path"], must_exist=True)
            if sha256_file(path) != record.get("sha256"):
                errors.append(f"Report source changed: {record['path']}")
        for record in metadata.get("assets", []):
            path = safe_path(root, output.parent / record["target"], must_exist=True)
            if sha256_file(path) != record.get("sha256"):
                errors.append(f"Report asset changed: {record['target']}")
    except (KeyError, OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        errors.append(str(error))
    return {"ok": not errors, "errors": errors}


def parse_args(arguments: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path("."))
    parser.add_argument("--question", required=True)
    parser.add_argument("--artifact", action="append", default=[])
    parser.add_argument("--title")
    parser.add_argument("--format", choices=("html", "pdf"), default="html")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args(arguments)


def main(arguments: list[str] | None = None) -> int:
    args = parse_args(arguments)
    try:
        root = args.project.expanduser().resolve()
        output = root / f"reports/{args.question}/report.html"
        if args.format == "pdf":
            raise ValueError("PDF renderer is not configured; no PDF was created")
        if args.validate_only:
            result = validate_report(root, output)
        else:
            plan = build_plan(
                root,
                args.question,
                args.artifact,
                title=args.title,
                overwrite=args.overwrite,
            )
            applied = apply_plan(plan) if args.apply else None
            result = {
                "ok": True,
                "mode": "apply" if args.apply else "dry-run",
                "output": str(output),
                "report_type": plan["metadata"]["report_type"],
                "artifacts": plan["metadata"]["artifacts"],
                "artifact_selection": plan["metadata"]["artifact_selection"],
                "sources": plan["metadata"]["sources"],
                "assets": plan["assets"],
                "applied": applied,
            }
        print(json.dumps(result, ensure_ascii=False, indent=2 if args.json else None))
        return 0 if result.get("ok", True) else 1
    except (FileExistsError, OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
