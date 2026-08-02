"""Deterministic Markdown-to-HTML reporting API."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from html import escape
from importlib.metadata import version
import mimetypes
from pathlib import Path
import re
from typing import Any
from urllib.parse import unquote, urlparse
import base64
import binascii

from markdown_it import MarkdownIt

from .core import (
    ARCHIVE_VERSION_PATTERN,
    RELEASE_VERSION,
    REPORT_SCHEMA_VERSION,
    TASK_NAME_PATTERN,
    atomic_write,
    environment_hashes,
    git_commit,
    load_yaml,
    relative_link,
    relative_to_root,
    safe_project_path,
    sha256_file,
    sha256_text,
    yaml_text,
)

MARKDOWN_IT_VERSION = version("markdown-it-py")


class ReportKind(str, Enum):
    EXPLORE = "explore"
    RELEASE = "release"


@dataclass(frozen=True)
class ReportBuild:
    source: str | None
    source_mode: str
    output: str
    manifest: str
    source_sha256: str
    output_sha256: str
    assets: tuple[dict[str, Any], ...]
    kind: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


REQUIRED_HEADINGS = {
    ReportKind.EXPLORE: (
        "研究问题",
        "输入与方法",
        "结果",
        "限制",
        "结论与下一问题",
        "可复现信息",
    ),
    ReportKind.RELEASE: (
        "项目目的",
        "输入与方法",
        "主要结果",
        "限制",
        "结论",
        "可复现信息",
    ),
}

PLACEHOLDERS = ("尚未填写", "TODO", "TBD")
FORBIDDEN_URL_PATTERN = re.compile(r"(?i)(?:data|file|javascript|vbscript):(?:/{0,2})")

REPORT_CSS = """
:root { color-scheme: light; --ink: #172033; --muted: #5b6474; --line: #d9dee8;
  --accent: #1f5f8b; --paper: #ffffff; --wash: #f4f7fa; }
* { box-sizing: border-box; }
body { margin: 0; background: var(--wash); color: var(--ink);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans CJK SC",
  "Microsoft YaHei", sans-serif; line-height: 1.72; }
main { width: min(980px, calc(100% - 32px)); margin: 32px auto; padding: 48px;
  background: var(--paper); border: 1px solid var(--line); border-radius: 12px; }
h1, h2, h3 { line-height: 1.3; color: #153b57; }
h1 { border-bottom: 3px solid var(--accent); padding-bottom: 12px; }
h2 { margin-top: 2em; border-bottom: 1px solid var(--line); padding-bottom: 6px; }
img { max-width: 100%; height: auto; }
table { width: 100%; border-collapse: collapse; margin: 1em 0; }
th, td { border: 1px solid var(--line); padding: 8px 10px; text-align: left; }
th { background: var(--wash); }
code { background: var(--wash); padding: 0.12em 0.3em; border-radius: 4px; }
pre { overflow-x: auto; background: #111827; color: #f9fafb; padding: 16px;
  border-radius: 8px; }
.report-meta { color: var(--muted); font-size: 0.92rem; }
@media print {
  body { background: white; }
  main { width: auto; margin: 0; padding: 0; border: 0; }
  a { color: inherit; text-decoration: none; }
}
""".strip()

ATTRIBUTE_PATTERN = re.compile(
    r"(?P<prefix><(?P<tag>img|a)\b[^>]*?\s(?P<attr>src|href)=)"
    r"(?P<quote>[\"'])(?P<url>.*?)(?P=quote)",
    flags=re.IGNORECASE,
)
INLINE_SOURCE_PATTERN = re.compile(
    r'<template id="rpos-markdown-source" data-encoding="base64">'
    r"(?P<payload>[A-Za-z0-9+/=]+)</template>"
)


def parse_report_text(text: str, source: Path) -> tuple[dict[str, Any], str]:
    match = re.match(r"^---\s*\n(?P<meta>.*?)\n---\s*\n(?P<body>.*)\Z", text, re.S)
    if match is None:
        raise ValueError(f"Report source lacks YAML frontmatter: {source}")
    metadata = load_yaml_text(match.group("meta"), source)
    return metadata, match.group("body")


def parse_report_source(source: Path) -> tuple[dict[str, Any], str]:
    return parse_report_text(source.read_text(encoding="utf-8"), source)


def load_yaml_text(text: str, source: Path) -> dict[str, Any]:
    import yaml

    value = yaml.safe_load(text)
    if not isinstance(value, dict):
        raise ValueError(f"Report frontmatter must be a mapping: {source}")
    return value


def validate_source_contract(
    metadata: dict[str, Any],
    body: str,
    kind: ReportKind,
    *,
    require_complete: bool,
) -> list[str]:
    errors: list[str] = []
    if str(metadata.get("schema_version")) != REPORT_SCHEMA_VERSION:
        errors.append(f"schema_version must be {REPORT_SCHEMA_VERSION}")
    if metadata.get("kind") != kind.value:
        errors.append(f"kind must be {kind.value}")
    if metadata.get("language") != "zh-CN":
        errors.append("language must be zh-CN")
    if not isinstance(metadata.get("title"), str) or not metadata["title"].strip():
        errors.append("title must be a non-empty string")
    if kind is ReportKind.EXPLORE:
        task = metadata.get("task")
        if not isinstance(task, str) or TASK_NAME_PATTERN.fullmatch(task) is None:
            errors.append("explore report requires a valid task name")
    if kind is ReportKind.RELEASE:
        snapshots = metadata.get("snapshots")
        if not isinstance(snapshots, list) or not snapshots:
            errors.append("release report requires snapshots")
        else:
            for snapshot in snapshots:
                if not isinstance(snapshot, str) or "@" not in snapshot:
                    errors.append("release report contains an invalid snapshot")
                    continue
                task_name, version = snapshot.rsplit("@", 1)
                if (
                    TASK_NAME_PATTERN.fullmatch(task_name) is None
                    or ARCHIVE_VERSION_PATTERN.fullmatch(version) is None
                ):
                    errors.append(
                        f"release report contains an invalid snapshot: {snapshot}"
                    )
    receipts = metadata.get("run_receipts")
    if not isinstance(receipts, list):
        errors.append("run_receipts must be a list")
    heading_list = re.findall(r"^##\s+(.+?)\s*$", body, flags=re.MULTILINE)
    headings = set(heading_list)
    for heading in REQUIRED_HEADINGS[kind]:
        if heading not in headings:
            errors.append(f"missing required heading: {heading}")
    if all(heading in headings for heading in REQUIRED_HEADINGS[kind]):
        positions = [heading_list.index(heading) for heading in REQUIRED_HEADINGS[kind]]
        if positions != sorted(positions):
            errors.append("required headings are out of order")
    if require_complete:
        for placeholder in PLACEHOLDERS:
            if placeholder.lower() in body.lower():
                errors.append(f"report still contains placeholder: {placeholder}")
    return errors


def resolve_asset(
    *,
    project_root: Path,
    source_base: Path,
    output: Path,
    raw_url: str,
    embed: bool,
    is_image: bool,
) -> tuple[str, dict[str, Any] | None]:
    if raw_url.startswith("#"):
        return raw_url, None
    parsed = urlparse(raw_url)
    if parsed.scheme or parsed.netloc:
        if not is_image and parsed.scheme == "https":
            return raw_url, None
        raise ValueError(
            f"External or absolute report resource is forbidden: {raw_url}"
        )
    decoded = unquote(parsed.path)
    candidate = Path(decoded)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"Report resource escapes its source directory: {raw_url}")
    try:
        asset = safe_project_path(
            project_root,
            source_base / candidate,
            label="report resource",
            must_exist=True,
            allow_absolute=True,
            reject_symlink=True,
        )
    except ValueError as error:
        raise ValueError(
            f"Report resource is missing, unsafe, or outside the project: {raw_url}"
        ) from error
    if not asset.is_file():
        raise ValueError(f"Report resource is not a regular file: {raw_url}")
    if asset in {output, output.with_suffix(".build.yaml")}:
        raise ValueError(
            f"Report output or build manifest cannot be an input resource: {raw_url}"
        )
    record = {
        "path": relative_to_root(project_root, asset),
        "size": asset.stat().st_size,
        "sha256": sha256_file(asset),
        "mode": "embedded" if embed else "linked",
    }
    if embed:
        media_type = mimetypes.guess_type(asset.name)[0] or "application/octet-stream"
        encoded = base64.b64encode(asset.read_bytes()).decode("ascii")
        return f"data:{media_type};base64,{encoded}", record
    rewritten = relative_link(output.parent, asset)
    if parsed.fragment:
        rewritten += f"#{parsed.fragment}"
    return rewritten, record


def rewrite_and_validate_assets(
    html_body: str,
    *,
    project_root: Path,
    source_base: Path,
    output: Path,
    asset_mode: str,
) -> tuple[str, tuple[dict[str, Any], ...]]:
    if asset_mode not in {"embed", "relative"}:
        raise ValueError("asset_mode must be embed or relative")
    records: dict[str, dict[str, Any]] = {}

    def replace(match: re.Match[str]) -> str:
        tag = match.group("tag").lower()
        raw_url = match.group("url")
        embed = tag == "img" and asset_mode == "embed"
        rewritten, record = resolve_asset(
            project_root=project_root,
            source_base=source_base,
            output=output,
            raw_url=raw_url,
            embed=embed,
            is_image=tag == "img",
        )
        if record is not None:
            records[record["path"]] = record
        quote = match.group("quote")
        return f"{match.group('prefix')}{quote}{rewritten}{quote}"

    rewritten = ATTRIBUTE_PATTERN.sub(replace, html_body)
    return rewritten, tuple(records[path] for path in sorted(records))


def render_document(
    title: str,
    metadata: dict[str, Any],
    body: str,
    *,
    inline_source: str | None = None,
) -> str:
    meta_line = (
        f"类型：{escape(str(metadata['kind']))} · "
        f"语言：{escape(str(metadata['language']))} · "
        f"Schema：{escape(str(metadata['schema_version']))}"
    )
    source_template = ""
    if inline_source is not None:
        payload = base64.b64encode(inline_source.encode("utf-8")).decode("ascii")
        source_template = (
            '<template id="rpos-markdown-source" data-encoding="base64">'
            f"{payload}</template>\n"
        )
    return (
        "<!doctype html>\n"
        '<html lang="zh-CN">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{escape(title)}</title>\n"
        f"<style>{REPORT_CSS}</style>\n"
        "</head>\n"
        "<body>\n"
        "<main>\n"
        f'<p class="report-meta">{meta_line}</p>\n'
        f"{body}\n"
        f"{source_template}"
        "</main>\n"
        "</body>\n"
        "</html>\n"
    )


def reject_immutable_report_output(project_root: Path, output: Path) -> None:
    if output.is_relative_to(project_root / "archive"):
        raise FileExistsError(
            f"Archive content is immutable and cannot be rebuilt: {output}"
        )
    release_path = project_root / "pipeline/release.yaml"
    if not release_path.is_file():
        return
    if output.is_relative_to(project_root / "pipeline"):
        raise FileExistsError(
            f"Released pipeline is immutable and cannot receive reports: {output}"
        )
    release = load_yaml(release_path)
    metadata = release.get("release")
    if not isinstance(metadata, dict) or not isinstance(metadata.get("report"), str):
        raise ValueError(f"Malformed release manifest: {release_path}")
    released_report = safe_project_path(
        project_root,
        metadata["report"],
        label="released report",
    )
    if released_report == output:
        raise FileExistsError(
            f"Released report is immutable and cannot be rebuilt: {output}"
        )


def _build_report_text(
    *,
    source_text: str,
    source_label: Path,
    source_base: Path,
    source: Path | None,
    output: Path,
    project_root: Path,
    kind: ReportKind,
    asset_mode: str = "embed",
) -> ReportBuild:
    root = project_root.resolve()
    source_base = safe_project_path(
        root,
        source_base,
        label="report source base",
        must_exist=True,
        allow_root=True,
        allow_absolute=True,
        reject_symlink=True,
    )
    output = safe_project_path(
        root,
        output,
        label="report output",
        allow_absolute=True,
        reject_symlink=True,
    )
    if output.suffix.lower() != ".html":
        raise ValueError("Report output must be .html")
    reject_immutable_report_output(root, output)
    metadata, markdown = parse_report_text(source_text, source_label)
    errors = validate_source_contract(
        metadata,
        markdown,
        kind,
        require_complete=False,
    )
    if errors:
        raise ValueError("; ".join(errors))
    forbidden_url = FORBIDDEN_URL_PATTERN.search(markdown)
    if forbidden_url is not None:
        raise ValueError(f"Forbidden report URL scheme: {forbidden_url.group(0)}")
    renderer = MarkdownIt("commonmark", {"html": False}).enable("table")
    body = renderer.render(markdown)
    body, assets = rewrite_and_validate_assets(
        body,
        project_root=root,
        source_base=source_base,
        output=output,
        asset_mode=asset_mode,
    )
    document = render_document(
        str(metadata["title"]),
        metadata,
        body,
        inline_source=source_text if source is None else None,
    )
    manifest_path = output.with_suffix(".build.yaml")
    source_mode = "markdown" if source is not None else "inline"
    source_value = relative_to_root(root, source) if source is not None else None
    heading_list = re.findall(r"^##\s+(.+?)\s*$", markdown, flags=re.MULTILINE)
    completeness_errors = validate_source_contract(
        metadata,
        markdown,
        kind,
        require_complete=True,
    )
    build_manifest = {
        "schema_version": REPORT_SCHEMA_VERSION,
        "renderer": {
            "name": "research-project-os",
            "version": RELEASE_VERSION,
            "markdown_engine": "markdown-it-py",
            "markdown_engine_version": MARKDOWN_IT_VERSION,
            "raw_html": False,
            "asset_mode": asset_mode,
        },
        "report": {
            "kind": kind.value,
            "language": "zh-CN",
            "source_mode": source_mode,
            "source": source_value,
            "source_base": relative_to_root(root, source_base),
            "output": relative_to_root(root, output),
            "source_sha256": sha256_text(source_text),
            "output_sha256": sha256_text(document),
            "run_receipts": metadata.get("run_receipts", []),
            "source_metadata": metadata,
            "source_contract": {
                "headings": heading_list,
                "complete": not completeness_errors,
                "completeness_errors": completeness_errors,
            },
        },
        "assets": list(assets),
        "provenance": {
            "git_commit": git_commit(root),
            "environment": environment_hashes(root),
        },
    }
    atomic_write(output, document)
    atomic_write(manifest_path, yaml_text(build_manifest))
    return ReportBuild(
        source=source_value,
        source_mode=source_mode,
        output=relative_to_root(root, output),
        manifest=relative_to_root(root, manifest_path),
        source_sha256=build_manifest["report"]["source_sha256"],
        output_sha256=build_manifest["report"]["output_sha256"],
        assets=assets,
        kind=kind.value,
    )


def build_report(
    *,
    source: Path,
    output: Path,
    project_root: Path,
    kind: ReportKind,
    asset_mode: str = "embed",
) -> ReportBuild:
    root = project_root.resolve()
    source = safe_project_path(
        root,
        source,
        label="report source",
        must_exist=True,
        allow_absolute=True,
        reject_symlink=True,
    )
    if source.suffix.lower() != ".md":
        raise ValueError("Report source must be .md")
    return _build_report_text(
        source_text=source.read_text(encoding="utf-8"),
        source_label=source,
        source_base=source.parent,
        source=source,
        output=output,
        project_root=root,
        kind=kind,
        asset_mode=asset_mode,
    )


def build_report_text(
    *,
    source_text: str,
    source_base: Path,
    output: Path,
    project_root: Path,
    kind: ReportKind,
    asset_mode: str = "embed",
) -> ReportBuild:
    if not source_text.strip():
        raise ValueError("Inline report source must not be empty")
    return _build_report_text(
        source_text=source_text,
        source_label=source_base / "<inline-report.md>",
        source_base=source_base,
        source=None,
        output=output,
        project_root=project_root,
        kind=kind,
        asset_mode=asset_mode,
    )


def validate_report(
    *,
    output: Path,
    project_root: Path,
    kind: ReportKind | None = None,
    require_complete: bool = False,
) -> dict[str, Any]:
    root = project_root.resolve()
    errors: list[str] = []
    try:
        output = safe_project_path(
            root,
            output,
            label="report output",
            must_exist=True,
            allow_absolute=True,
            reject_symlink=True,
        )
    except ValueError as error:
        return {"ok": False, "errors": [str(error)]}
    manifest_path = output.with_suffix(".build.yaml")
    if not manifest_path.is_file():
        return {
            "ok": False,
            "errors": [f"Missing report build manifest: {manifest_path}"],
        }
    try:
        manifest = load_yaml(manifest_path)
        report = manifest.get("report")
        if manifest.get("schema_version") != REPORT_SCHEMA_VERSION:
            errors.append(f"Unsupported report manifest: {manifest_path}")
        if not isinstance(report, dict):
            errors.append(
                f"Report build manifest lacks report mapping: {manifest_path}"
            )
            report = {}
        if report.get("output_sha256") != sha256_file(output):
            errors.append(f"Report HTML hash mismatch: {output}")
        html = output.read_text(encoding="utf-8")
        resolved_kind = kind or ReportKind(str(report.get("kind")))
        source_mode = report.get("source_mode", "markdown")
        source_value = report.get("source")
        source_metadata = report.get("source_metadata")
        source_contract = report.get("source_contract")
        source = None
        body = None
        if source_mode == "markdown" and isinstance(source_value, str):
            source = safe_project_path(
                root,
                source_value,
                label="report source",
                must_exist=True,
                reject_symlink=True,
            )
            if report.get("source_sha256") != sha256_file(source):
                errors.append(f"Report source hash mismatch: {source}")
            source_metadata, body = parse_report_source(source)
        elif source_mode == "inline" and source_value is None:
            if not isinstance(report.get("source_sha256"), str):
                errors.append(f"Inline report lacks source hash: {manifest_path}")
            if not isinstance(source_metadata, dict):
                errors.append(f"Inline report lacks source metadata: {manifest_path}")
            if not isinstance(source_contract, dict):
                errors.append(f"Inline report lacks source contract: {manifest_path}")
            else:
                headings = source_contract.get("headings")
                if not isinstance(headings, list) or not all(
                    isinstance(value, str) for value in headings
                ):
                    errors.append(
                        f"Inline report has malformed heading contract: {manifest_path}"
                    )
            match = INLINE_SOURCE_PATTERN.search(html)
            if match is None:
                errors.append(f"Inline report lacks embedded source: {output}")
            else:
                decoded = base64.b64decode(
                    match.group("payload"), validate=True
                ).decode("utf-8")
                if report.get("source_sha256") != sha256_text(decoded):
                    errors.append(f"Inline report source hash mismatch: {output}")
                embedded_metadata, body = parse_report_text(
                    decoded,
                    output.with_suffix(".embedded.md"),
                )
                if embedded_metadata != source_metadata:
                    errors.append(f"Inline report source metadata mismatch: {output}")
                source_metadata = embedded_metadata
                embedded_headings = re.findall(
                    r"^##\s+(.+?)\s*$", body, flags=re.MULTILINE
                )
                if isinstance(source_contract, dict):
                    if source_contract.get("headings") != embedded_headings:
                        errors.append(f"Inline report heading contract mismatch: {output}")
                    completeness_errors = validate_source_contract(
                        source_metadata,
                        body,
                        resolved_kind,
                        require_complete=True,
                    )
                    if source_contract.get("complete") != (not completeness_errors):
                        errors.append(
                            f"Inline report completeness contract mismatch: {output}"
                        )
                    if source_contract.get("completeness_errors") != completeness_errors:
                        errors.append(
                            f"Inline report completeness errors mismatch: {output}"
                        )
        else:
            errors.append(f"Report build manifest has invalid source mode: {manifest_path}")
        if report.get("kind") != resolved_kind.value:
            errors.append(f"Report kind mismatch: {output}")
        if isinstance(source_metadata, dict) and body is not None:
            errors.extend(
                validate_source_contract(
                    source_metadata,
                    body,
                    resolved_kind,
                    require_complete=require_complete,
                )
            )
        if '<html lang="zh-CN">' not in html or '<meta charset="utf-8">' not in html:
            errors.append(f"HTML language or charset contract failed: {output}")
        for asset in manifest.get("assets", []):
            if not isinstance(asset, dict) or not isinstance(asset.get("path"), str):
                errors.append(f"Malformed report asset record: {manifest_path}")
                continue
            path = safe_project_path(
                root,
                asset["path"],
                label="report asset",
                must_exist=True,
                reject_symlink=True,
            )
            if asset.get("sha256") != sha256_file(path):
                errors.append(f"Report asset hash mismatch: {path}")
    except (OSError, ValueError, binascii.Error, UnicodeDecodeError) as error:
        errors.append(str(error))
    return {
        "ok": not errors,
        "errors": errors,
        "output": relative_to_root(root, output),
        "manifest": relative_to_root(root, manifest_path),
    }
