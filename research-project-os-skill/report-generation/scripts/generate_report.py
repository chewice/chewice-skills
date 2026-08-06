#!/usr/bin/env python3
"""Generate or validate an HTML report from Human-reviewed research records."""

from __future__ import annotations

import argparse
import hashlib
from html import escape
import json
from pathlib import Path
import re
import shutil
import sys
from typing import Any
from urllib.parse import unquote, urlparse

from markdown_it import MarkdownIt


SKILL_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = SKILL_ROOT / "assets/templates/report.html"
CSS = SKILL_ROOT / "assets/css/report.css"
QUESTION_PATTERN = re.compile(r"Q-\d{3}")
ARTIFACT_PATTERN = re.compile(r"A-\d{3}")
LINK_PATTERN = re.compile(r"(?P<image>!)?\[(?P<label>[^\]]*)\]\((?P<url>[^)\s]+)\)")
FORBIDDEN_PATTERN = re.compile(r"(?i)(?:javascript|vbscript|file|data):")
PLACEHOLDERS = ("尚未填写", "TODO", "TBD")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def markdown_field(text: str, name: str) -> str:
    match = re.search(rf"^{re.escape(name)}:\s*(.*?)\s*$", text, re.MULTILINE)
    return match.group(1).strip() if match else ""


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
        if len(cells) == 5 and cells[0] == question_id:
            return dict(zip(("id", "question", "status", "brief", "updated"), cells))
    raise ValueError(f"Question is not registered: {question_id}")


def validated_inputs(
    root: Path,
    question_id: str,
    artifact_ids: list[str],
) -> tuple[dict[str, str], list[Path]]:
    if QUESTION_PATTERN.fullmatch(question_id) is None:
        raise ValueError("Question must match Q-NNN")
    if not artifact_ids:
        raise ValueError("At least one --artifact is required")
    if len(set(artifact_ids)) != len(artifact_ids):
        raise ValueError("Artifact IDs must be unique")
    row = question_row(root, question_id)
    expected_brief = f"docs/questions/{question_id}/BRIEF.md"
    if row["brief"] != expected_brief:
        raise ValueError(f"Question BRIEF path must be {expected_brief}")
    brief = safe_path(root, root / expected_brief, must_exist=True)
    brief_text = brief.read_text(encoding="utf-8")
    review = markdown_field(brief_text, "Human review status").lower()
    if review in {"", "pending", "待审核"}:
        raise ValueError("BRIEF has not received Human review")
    sources = [brief]
    for artifact_id in artifact_ids:
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
        if markdown_field(text, "Status") != "审核通过":
            raise ValueError(f"Artifact is not approved: {artifact_id}")
        review_section = re.search(
            r"^## 8\. Human Review\s*$\n(?P<body>.*?)(?=^## |\Z)",
            text,
            re.MULTILINE | re.DOTALL,
        )
        decision = (
            markdown_field(review_section.group("body"), "Decision")
            if review_section
            else ""
        )
        if decision != "审核通过":
            raise ValueError(f"Artifact lacks Human approval: {artifact_id}")
        sources.append(result)
    return row, sources


def demote_headings(text: str) -> str:
    return re.sub(
        r"^(#{1,5})(\s+)",
        lambda match: "#" + match.group(1) + match.group(2),
        text,
        flags=re.MULTILINE,
    )


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


def build_plan(
    root: Path,
    question_id: str,
    artifact_ids: list[str],
    *,
    title: str | None = None,
    overwrite: bool = False,
) -> dict[str, Any]:
    root = root.expanduser().resolve()
    row, sources = validated_inputs(root, question_id, artifact_ids)
    output = safe_path(root, root / f"reports/{question_id}/report.html")
    metadata_path = output.with_suffix(".build.json")
    if not overwrite and (output.exists() or metadata_path.exists()):
        raise FileExistsError(f"Report output already exists: {output}")
    records: dict[str, dict[str, Any]] = {}
    parts = [f"# {title or row['question']}", "## 问题工作依据"]
    brief_text = sources[0].read_text(encoding="utf-8")
    parts.append(
        demote_headings(
            rewrite_resources(
                brief_text,
                source=sources[0],
                root=root,
                records=records,
            )
        )
    )
    for artifact_id, source in zip(artifact_ids, sources[1:]):
        parts.append(f"## 审核通过的 Explore：{artifact_id}")
        parts.append(
            demote_headings(
                rewrite_resources(
                    source.read_text(encoding="utf-8"),
                    source=source,
                    root=root,
                    records=records,
                )
            )
        )
    markdown = "\n\n".join(parts)
    renderer = MarkdownIt("commonmark", {"html": False}).enable("table")
    body = renderer.render(markdown)
    rendered_title = title or row["question"]
    html = (
        TEMPLATE.read_text(encoding="utf-8")
        .replace("{{TITLE}}", escape(rendered_title))
        .replace("{{CSS}}", CSS.read_text(encoding="utf-8"))
        .replace("{{QUESTION}}", escape(question_id))
        .replace("{{ARTIFACTS}}", escape(", ".join(artifact_ids)))
        .replace("{{BODY}}", body)
    )
    source_records = [
        {
            "path": source.relative_to(root).as_posix(),
            "sha256": sha256_file(source),
        }
        for source in sources
    ]
    metadata = {
        "schema_version": "1.0.0",
        "question": question_id,
        "artifacts": artifact_ids,
        "output": output.relative_to(root).as_posix(),
        "output_sha256": hashlib.sha256(html.encode("utf-8")).hexdigest(),
        "sources": source_records,
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
    }


def apply_plan(plan: dict[str, Any]) -> dict[str, Any]:
    root = Path(plan["root"])
    output = Path(plan["output"])
    metadata_path = Path(plan["metadata_path"])
    if not plan["overwrite"] and (output.exists() or metadata_path.exists()):
        raise FileExistsError(f"Report output appeared after planning: {output}")
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
        shutil.copy2(source, target)
    for source in plan["metadata"]["sources"]:
        path = safe_path(root, root / source["path"], must_exist=True)
        if sha256_file(path) != source["sha256"]:
            raise ValueError(f"Report source changed after planning: {path}")
    output.write_text(plan["html"], encoding="utf-8")
    metadata_path.write_text(
        json.dumps(plan["metadata"], ensure_ascii=False, indent=2, sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    result = validate_report(root, output)
    if not result["ok"]:
        raise ValueError("; ".join(result["errors"]))
    return {"output": str(output), "metadata": str(metadata_path)}


def validate_report(root: Path, output: Path) -> dict[str, Any]:
    root = root.expanduser().resolve()
    output = safe_path(root, output, must_exist=True)
    errors: list[str] = []
    match = re.fullmatch(r"reports/(Q-\d{3})/report\.html", output.relative_to(root).as_posix())
    if match is None:
        return {"ok": False, "errors": ["Report path must be reports/<Q-ID>/report.html"]}
    metadata_path = output.with_suffix(".build.json")
    if not metadata_path.is_file():
        return {"ok": False, "errors": ["Missing report build metadata"]}
    try:
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if metadata.get("question") != match.group(1):
            errors.append("Question does not match report path")
        if metadata.get("output_sha256") != sha256_file(output):
            errors.append("Report HTML hash mismatch")
        html = output.read_text(encoding="utf-8")
        for required in ('<html lang="zh-CN">', '<meta charset="utf-8">', "<main>"):
            if required not in html:
                errors.append(f"Missing HTML contract: {required}")
        if FORBIDDEN_PATTERN.search(html) or "<script" in html.lower():
            errors.append("Report contains forbidden active content")
        for placeholder in PLACEHOLDERS:
            if placeholder.lower() in html.lower():
                errors.append(f"Report contains placeholder: {placeholder}")
        artifacts = metadata.get("artifacts")
        if not isinstance(artifacts, list):
            errors.append("Artifact metadata is malformed")
            artifacts = []
        try:
            validated_inputs(root, metadata.get("question", ""), artifacts)
        except ValueError as error:
            errors.append(str(error))
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
            raise ValueError(
                "PDF renderer is not configured; generate and validate HTML instead"
            )
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
                "sources": plan["metadata"]["sources"],
                "assets": plan["assets"],
                "applied": applied,
            }
        if args.json:
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(json.dumps(result, ensure_ascii=False))
        return 0 if result.get("ok", True) else 1
    except (FileExistsError, OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
