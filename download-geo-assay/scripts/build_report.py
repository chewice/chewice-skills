#!/usr/bin/env python3
"""生成单文件、中文、可离线阅读的 GEO/SRA 项目报告。"""

from __future__ import annotations

import argparse
import base64
import csv
import fcntl
import html
import json
import os
import re
import statistics
import sys
from collections import Counter
from collections.abc import Iterable
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from project_layout import iter_download_manifests

STATUS_ZH = {
    "PASS": "通过",
    "FAIL": "失败",
    "ERROR": "错误",
    "WARNING": "警告",
    "INFO": "信息",
    "available": "可用",
    "missing": "缺失",
    "invalid": "无效",
    "unreachable": "不可达",
    "not_probed": "未探测",
    "complete": "完成",
    "running": "运行中",
    "pending": "待处理",
    "in_progress": "进行中",
    "retryable_failed": "可恢复失败",
    "terminal_failed": "终止失败",
}

CHECK_ZH = {
    "unique_run": "run 唯一性",
    "gse_format": "GSE 格式",
    "gsm_format": "GSM 格式",
    "run_format": "run 格式",
    "layout": "文库布局",
    "numeric_field": "数值字段",
    "source": "数据源",
    "provenance": "数据来源属性",
    "ngdc_status": "NGDC 状态",
    "final_product": "最终产品",
    "source_arrays": "数据源数组",
    "read_roles": "read 角色",
    "filename_roles": "文件名与 read 角色",
    "file_size": "文件大小",
    "md5": "MD5",
    "ngdc_priority": "NGDC 优先级",
    "fallback_reason": "回退原因",
    "ngdc_provenance": "NGDC provenance",
    "sample_count": "样本数量",
    "run_count": "run 数量",
    "multi_run": "多 run",
    "multi_lane": "多 lane",
    "size_outlier": "大小异常",
    "space_guard": "空间预算",
    "quota_detection": "用户配额探测",
    "summary": "预检汇总",
}

LABELS = {
    "gse": "GSE",
    "gsm": "GSM",
    "srx": "SRX",
    "srr": "SRR",
    "title": "标题",
    "organism": "物种",
    "tissue": "组织",
    "condition": "条件",
    "treatment": "处理",
    "chemistry": "Chemistry",
    "run_count": "run 数",
    "lane_count": "lane 数",
    "read_structure": "Read structure",
    "library_layout": "文库布局",
    "selected_source": "最终数据源",
    "selected_provenance": "Provenance",
    "object_class": "对象类别",
    "quality_class": "质量类别",
    "transport_endpoint": "传输端点",
    "selection_reason": "选择原因",
    "final_product": "最终产品",
    "expected_spots": "预期 spots",
    "ngdc_status": "NGDC 状态",
    "ngdc_url": "NGDC URL",
    "ngdc_bytes": "NGDC 字节数",
    "fallback_reason": "回退原因",
    "level": "级别",
    "check": "检查项",
    "message": "技术详情",
    "source": "数据源",
    "provenance": "Provenance",
    "observed_r1": "R1 records",
    "observed_r2": "R2 records",
    "status": "状态",
    "raw_shape": "Raw shape",
    "filtered_shape": "Filtered shape",
    "loom_shape": "Loom shape",
    "expected_bytes": "预期字节数",
    "observed_bytes": "实际字节数",
    "completed_at": "完成时间",
    "instrument_model": "测序仪",
    "platform": "平台",
    "expected_samples": "预期样本数",
    "expected_runs": "预期 run 数",
    "bioproject": "BioProject",
    "summary": "研究摘要",
    "overall_design": "整体设计",
    "publication": "文献",
    "sample": "样本名",
    "batch": "Batch",
    "sex": "Sex",
    "number_of_reads": "Reads",
    "reads_with_valid_barcodes": "Valid barcodes",
    "sequencing_saturation": "Sequencing saturation",
    "reads_mapped_genome_unique": "Unique genome mapping",
    "reads_mapped_genefull_unique": "Unique GeneFull mapping",
    "estimated_number_of_cells": "Estimated cells",
    "fraction_unique_reads_in_cells": "Reads in cells",
    "median_reads_per_cell": "Median reads/cell",
    "median_umi_per_cell": "Median UMI/cell",
    "median_genefull_per_cell": "Median GeneFull/cell",
    "deletion_time": "删除时间",
    "storage_mode": "存储模式",
    "source_preference": "来源偏好",
    "allow_sra_lite": "允许 SRA Lite",
    "confirmed_at": "确认时间",
    "release_status": "释放状态",
    "retain_raw_files": "保留 raw files",
    "retain_raw_fastq": "保留 FASTQ",
    "assay_type": "Assay",
    "raw_file_type": "原始文件类型",
    "workflow": "Workflow",
    "validation_status": "验证状态",
    "deletion_status": "删除状态",
    "tool": "工具",
    "tool_version": "工具版本",
    "input_fastq": "输入 FASTQ",
    "output_matrix": "输出 matrix",
    "deleted_at": "删除时间",
    "samples": "样本数",
    "total_cells": "细胞总数",
    "median_cells": "细胞数中位数",
    "cell_range": "细胞数范围",
    "median_saturation": "Saturation 中位数",
    "median_reads_in_cells": "Reads in cells 中位数",
}


def read_tsv(path: Path) -> list[dict[str, str]]:
    if not path.is_file() or path.stat().st_size == 0:
        return []
    try:
        with path.open(newline="", errors="replace") as handle:
            return list(csv.DictReader(handle, delimiter="\t"))
    except (OSError, csv.Error):
        return []


def clean(value: object, root: Path) -> str:
    text = "" if value is None else str(value)
    return text.replace(str(root), ".").replace("\r", "")


def esc(value: object, root: Path) -> str:
    return html.escape(clean(value, root), quote=True)


def format_bytes(value: int) -> str:
    size = float(value)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if size < 1024 or unit == "TiB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{value} B"


def project_relative(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root).as_posix()
    except (OSError, ValueError):
        return path.name


def report_href(output: Path, target: Path) -> str:
    return os.path.relpath(target, output.parent).replace(os.sep, "/")


def source_line(root: Path, output: Path, paths: Iterable[Path]) -> str:
    items = []
    seen: set[str] = set()
    for path in paths:
        relative = project_relative(root, path)
        if relative in seen:
            continue
        seen.add(relative)
        label = html.escape(relative)
        if path.exists():
            href = html.escape(report_href(output, path), quote=True)
            items.append(f'<a href="{href}"><code>{label}</code></a>')
        else:
            items.append(f"<code>{label}</code>")
    return '<p class="sources">项目相对路径：' + " · ".join(items) + "</p>"


def zh_status(value: str) -> str:
    return STATUS_ZH.get(value, value)


def status_class(value: str) -> str:
    lowered = value.lower()
    if lowered in {"pass", "available", "complete", "completed"}:
        return "ok"
    if lowered in {"fail", "error", "invalid", "missing", "unreachable"}:
        return "bad"
    if lowered in {"warning", "running"}:
        return "warn"
    return "neutral"


def render_value(key: str, value: str, root: Path) -> str:
    value = clean(value, root)
    if key in {"status", "level", "ngdc_status", "validation"}:
        label = zh_status(value)
        return f'<span class="badge {status_class(value)}">{html.escape(label)}</span>'
    if key == "check":
        return html.escape(CHECK_ZH.get(value, value))
    if key.endswith("_bytes") and value.isdigit():
        return f"{html.escape(value)}<br><small>{format_bytes(int(value))}</small>"
    if key in {
        "reads_with_valid_barcodes",
        "sequencing_saturation",
        "reads_mapped_genome_unique",
        "reads_mapped_genefull_unique",
        "fraction_unique_reads_in_cells",
    }:
        parsed = numeric(value)
        return f"{parsed * 100:.1f}%" if parsed is not None else html.escape(value)
    if key.endswith("_url") and value.startswith(("https://", "http://")):
        safe = html.escape(value, quote=True)
        return f'<a href="{safe}">{html.escape(value)}</a>'
    if key == "message" and value:
        return (
            "<details><summary>查看原始技术信息</summary>"
            f"<pre>{html.escape(value)}</pre></details>"
        )
    return html.escape(value)


def table(
    rows: list[dict[str, str]],
    columns: list[str],
    root: Path,
    empty: str = "尚无数据。",
) -> str:
    if not rows:
        return f'<p class="empty">{html.escape(empty)}</p>'
    header = "".join(f"<th>{html.escape(LABELS.get(key, key))}</th>" for key in columns)
    body = []
    for row in rows:
        cells = "".join(
            f"<td>{render_value(key, row.get(key, ''), root)}</td>" for key in columns
        )
        body.append(f"<tr>{cells}</tr>")
    return (
        '<div class="table-wrap"><table class="filterable"><thead><tr>'
        f"{header}</tr></thead><tbody>{''.join(body)}</tbody></table></div>"
    )


def numeric(value: str) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def starsolo_distribution(
    rows: list[dict[str, str]], field: str, label: str, percent: bool = False
) -> str:
    points = [
        (row, value)
        for row in rows
        if (value := numeric(row.get(field, ""))) is not None
    ]
    if not points:
        return ""
    maximum = max(value for _, value in points) or 1
    bars = []
    for row, value in sorted(points, key=lambda item: item[1]):
        display = f"{value * 100:.1f}%" if percent else f"{value:,.0f}"
        title = html.escape(f"{row.get('gsm', '')}: {display}", quote=True)
        bars.append(
            f'<i style="height:{max(2.0, value / maximum * 100):.2f}%" '
            f'title="{title}"></i>'
        )
    return (
        '<div class="distribution"><strong>'
        + html.escape(label)
        + f"</strong><div>{''.join(bars)}</div>"
        + "<small>每根柱代表一个 GSM；按数值从低到高排列，悬停查看样本和数值。</small></div>"
    )


def starsolo_body(rows: list[dict[str, str]], root: Path) -> str:
    if not rows:
        return '<p class="empty">尚未生成 STARsolo 跨样本汇总。</p>'
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(row.get("gse", "") or "未标注 GSE", []).append(row)
    group_rows: list[dict[str, str]] = []
    for gse, items in sorted(grouped.items()):
        cells = [
            value
            for row in items
            if (value := numeric(row.get("estimated_number_of_cells", ""))) is not None
        ]
        saturation = [
            value
            for row in items
            if (value := numeric(row.get("sequencing_saturation", ""))) is not None
        ]
        reads_in_cells = [
            value
            for row in items
            if (value := numeric(row.get("fraction_unique_reads_in_cells", ""))) is not None
        ]
        group_rows.append(
            {
                "gse": gse,
                "samples": str(len(items)),
                "total_cells": f"{sum(cells):.0f}" if cells else "",
                "median_cells": f"{statistics.median(cells):.0f}" if cells else "",
                "cell_range": f"{min(cells):.0f}–{max(cells):.0f}" if cells else "",
                "median_saturation": (
                    f"{statistics.median(saturation) * 100:.1f}%" if saturation else ""
                ),
                "median_reads_in_cells": (
                    f"{statistics.median(reads_in_cells) * 100:.1f}%"
                    if reads_in_cells
                    else ""
                ),
            }
        )
    summary = table(
        group_rows,
        [
            "gse",
            "samples",
            "total_cells",
            "median_cells",
            "cell_range",
            "median_saturation",
            "median_reads_in_cells",
        ],
        root,
    )
    columns = [
        "gse",
        "gsm",
        "sample",
        "condition",
        "batch",
        "sex",
        "chemistry",
        "estimated_number_of_cells",
        "number_of_reads",
        "reads_with_valid_barcodes",
        "sequencing_saturation",
        "reads_mapped_genome_unique",
        "reads_mapped_genefull_unique",
        "fraction_unique_reads_in_cells",
        "median_umi_per_cell",
        "median_genefull_per_cell",
    ]
    detail = table(rows, columns, root)
    return (
        "<p><strong>注意：</strong><code>Estimated Number of Cells</code> 是 cell calling "
        "实际输出，不等同于 <code>nExpectedCells</code> 算法先验。</p>"
        + summary
        + '<div class="distribution-grid">'
        + starsolo_distribution(rows, "estimated_number_of_cells", "Estimated Number of Cells")
        + starsolo_distribution(
            rows, "sequencing_saturation", "Sequencing Saturation", percent=True
        )
        + "</div><details><summary>查看逐 GSM STARsolo 指标</summary>"
        + detail
        + "</details>"
    )


def section(
    title: str,
    body: str,
    root: Path,
    output: Path,
    paths: Iterable[Path],
    section_id: str,
) -> str:
    return (
        f'<section id="{html.escape(section_id, quote=True)}">'
        f"<h2>{html.escape(title)}</h2>"
        f"{source_line(root, output, paths)}{body}</section>"
    )


def locate_multiqc(root: Path, explicit: Path | None) -> Path | None:
    candidates = [
        explicit,
        root / "reports/.report_work/multiqc_report.html",
        root / "reports/multiqc/multiqc_report.html",
        root / "reports/multiqc_report.html",
        root / "reports/multiqc_data/embedded_multiqc.html",
    ]
    for candidate in candidates:
        if candidate and candidate.is_file() and candidate.stat().st_size:
            return candidate.resolve()
    return None


def existing_multiqc_payload(output: Path) -> str:
    if not output.is_file():
        return ""
    try:
        text = output.read_text(errors="replace")
    except OSError:
        return ""
    match = re.search(
        r'<script type="application/octet-stream" id="multiqc-data">([^<]+)</script>',
        text,
    )
    if not match:
        return ""
    payload = match.group(1).strip()
    try:
        base64.b64decode(payload, validate=True)
    except ValueError:
        return ""
    return payload


def legacy_reports(root: Path) -> list[Path]:
    candidates = [
        root / "reports/dataset_overview.md",
        root / "reports/preflight_summary.md",
        root / "reports/ngdc_mirror_audit.md",
    ]
    return [path for path in candidates if path.is_file() and path.stat().st_size]


def legacy_tables(root: Path) -> dict[str, list[dict[str, str]]]:
    mapping_rows = read_tsv(root / "metadata/srr_gsm_mapping.tsv")
    mapping = {
        row.get("srr", ""): row for row in mapping_rows if row.get("srr", "")
    }
    expected = [
        {
            "gse": row.get("gse", ""),
            "gsm": row.get("gsm", ""),
            "srx": row.get("experiment_accession", ""),
            "srr": row.get("srr", ""),
            "lane": "",
            "library_layout": row.get("library_layout", ""),
            "read_structure": row.get("observed_read_lengths", ""),
            "expected_spots": row.get("read_count", ""),
        }
        for row in mapping_rows
    ]
    sources = []
    for row in read_tsv(root / "metadata/sra_source_manifest.tsv"):
        srr = row.get("run_accession", "")
        mapped = mapping.get(srr, {})
        source = row.get("source", "")
        is_ngdc = source == "ngdc_sra"
        sources.append(
            {
                "gse": row.get("gse", "") or mapped.get("gse", ""),
                "gsm": mapped.get("gsm", ""),
                "srx": mapped.get("experiment_accession", ""),
                "srr": srr,
                "ngdc_status": "available" if is_ngdc else "missing",
                "selected_source": "ngdc_insdc" if is_ngdc else "ena_fastq",
                "selected_provenance": (
                    "NGDC_MIRROR_SRA" if is_ngdc else "ARCHIVE_GENERATED_FASTQ"
                ),
                "final_product": "matrix_velocity",
                "expected_spots": row.get("expected_spots", ""),
                "fallback_reason": "" if is_ngdc else "legacy_ena_selection",
            }
        )
    preflight = [
        {
            "level": "ERROR" if row.get("status") == "FAIL" else "INFO",
            "gse": row.get("gse", ""),
            "gsm": "",
            "srr": "",
            "check": row.get("check", ""),
            "message": row.get("detail", ""),
        }
        for row in read_tsv(root / "reports/preflight_checks.tsv")
    ]
    downloads = []
    for row in read_tsv(root / "reports/download_integrity_audit.tsv"):
        srr = row.get("srr", "")
        source = row.get("source", "")
        downloads.append(
            {
                "gse": row.get("gse", ""),
                "gsm": row.get("gsm", ""),
                "srr": srr,
                "source": source,
                "provenance": (
                    "NGDC_MIRROR_SRA"
                    if source == "ngdc_sra"
                    else "ARCHIVE_GENERATED_FASTQ"
                ),
                "final_product": "matrix_velocity",
                "expected_spots": row.get("expected_spots", ""),
                "observed_r1": row.get("validated_reads_per_mate", ""),
                "observed_r2": row.get("validated_reads_per_mate", ""),
                "status": row.get("status", ""),
                "message": row.get("integrity_evidence", ""),
            }
        )
    return {
        "expected": expected,
        "sources": sources,
        "preflight": preflight,
        "downloads": downloads,
    }


def build(args: argparse.Namespace) -> tuple[str, Path | None]:
    root = args.root.resolve()
    output = args.output
    if output is None:
        output = root / "reports/report.html"
    elif not output.is_absolute():
        output = root / output
    output = output.resolve()

    paths = {
        "study": root / "metadata/study_metadata.tsv",
        "samples": root / "metadata/sample_metadata.tsv",
        "expected": root / "metadata/expected_runs.tsv",
        "sources": root / "metadata/source_manifest.tsv",
        "preflight": root / "reports/preflight_audit.tsv",
        "coverage": root / "reports/ngdc_coverage.tsv",
        "downloads": root / "reports/download_integrity_audit.tsv",
        "final": root / "reports/processed_output_audit.tsv"
        if (root / "reports/processed_output_audit.tsv").is_file()
        else root / "reports/final_output_audit.tsv",
        "tools": root / "reports/tool_versions.tsv",
        "starsolo": root / "reports/starsolo_summary.tsv",
        "storage": root / "metadata/storage_policy.tsv",
        "storage_audit": root / "reports/storage_policy_audit.tsv",
        "deletion_log": root / "reports/storage_deletion_log.tsv",
        "release": root / "reports/storage_release.tsv",
        "conversion": root / "reports/conversion_provenance.tsv",
        "assay": root / "metadata/assay_routing.tsv",
        "platforms": root / "metadata/platform_metadata.tsv",
        "donors": root / "metadata/donor_metadata.tsv",
    }
    data = {name: read_tsv(path) for name, path in paths.items()}
    legacy = legacy_tables(root)
    for name in ("expected", "sources", "preflight", "downloads"):
        if not data[name]:
            data[name] = legacy[name]
    download_manifests = iter_download_manifests(root)
    raw_download_rows = [
        row for manifest in download_manifests for row in read_tsv(manifest)
    ]
    transfer_states = []
    for path in sorted((root / "reports/status").glob("*.transfer.json")):
        try:
            state = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        transfer_states.append(
            {
                "run": state.get("run", path.name.removesuffix(".transfer.json")),
                "phase": state.get("phase", ""),
                "status": state.get("status", ""),
                "attempt_count": state.get("attempt_count", 0),
                "resume_count": state.get("resume_count", 0),
                "bytes_resumed": state.get("bytes_resumed", 0),
                "error_class": state.get("error_class", ""),
                "last_error": state.get("last_error", ""),
                "updated_at": state.get("updated_at", ""),
            }
        )

    all_rows = data["sources"] or data["expected"]
    gse_values = sorted(
        {
            row.get("gse", "")
            for row in [*data["study"], *all_rows]
            if row.get("gse", "")
        }
    )
    gse = " + ".join(gse_values) or root.name
    samples = {
        row.get("gsm", "")
        for row in (data["sources"] or data["expected"] or data["samples"])
        if row.get("gsm", "")
    }
    runs = {row.get("srr", "") for row in all_rows if row.get("srr", "")}
    completion_markers = list((root / "reports/status").rglob("*.complete"))
    errors = sum(
        row.get("level") == "ERROR" for row in data["preflight"]
    ) + sum(row.get("status") == "FAIL" for row in data["downloads"] + data["final"])
    warnings = sum(row.get("level") == "WARNING" for row in data["preflight"])
    terminal_failures = sum(
        row.get("status") == "terminal_failed" for row in transfer_states
    )
    errors += terminal_failures
    source_counts = Counter(row.get("selected_source", "") for row in data["sources"])
    provenance_counts = Counter(
        row.get("selected_provenance", "") for row in data["sources"]
    )
    ngdc_counts = Counter(row.get("ngdc_status", "") for row in data["coverage"])

    cards = [
        ("数据集", gse),
        ("GSM", str(len(samples))),
        ("run", str(len(runs))),
        ("完成 marker", f"{len(completion_markers)}/{len(runs) or '?'}"),
        ("终止传输", str(terminal_failures)),
        ("错误", str(errors)),
        ("警告", str(warnings)),
    ]
    card_html = "".join(
        f'<div class="card"><span>{html.escape(label)}</span><strong>{html.escape(value)}</strong></div>'
        for label, value in cards
    )

    nav_items = [
        ("overview", "研究概览"),
        ("directories", "目录与层级"),
        ("assay", "Assay 分流"),
        ("storage", "存储策略"),
        ("samples", "样本"),
        ("runs", "run 与 read"),
        ("preflight", "预检"),
        ("routing", "数据源与 provenance"),
        ("downloads", "下载与完整性"),
        ("transfer-recovery", "断点恢复"),
        ("outputs", "转换状态"),
        ("repro", "复现信息"),
    ]
    navigation = "".join(
        f'<a href="#{target}">{html.escape(label)}</a>' for target, label in nav_items
    )

    sections: list[str] = []
    study_columns = [
        key
        for key in (
            "gse",
            "title",
            "organism",
            "bioproject",
            "expected_samples",
            "expected_runs",
            "summary",
            "overall_design",
            "publication",
        )
        if any(key in row for row in data["study"])
    ]
    sections.append(
        section(
            "研究概览",
            table(data["study"], study_columns or ["gse", "title"], root),
            root,
            output,
            [paths["study"]],
            "overview",
        )
    )

    directory_rows = [
        {"level": "项目", "path": ".", "content": "单个 GSE 的项目根目录"},
        {"level": "说明", "path": "README.md", "content": "Study → Donor → Sample → raw assay file"},
        {"level": "元数据", "path": "metadata/", "content": "研究、donor、样本、平台、assay、run、来源与存储策略"},
        {"level": "下载证据", "path": "metadata/download_manifests/", "content": "每个 GSM 的已校验下载记录"},
        {"level": "Mode A FASTQ", "path": "raw/GSM*/fastq/", "content": "长期保存的 R1/R2/I1/I2 FASTQ"},
        {"level": "归档", "path": "raw/GSM*/sra/", "content": "需要保留时的 SRA 文件"},
        {"level": "Mode A CEL", "path": "raw/GSM*/CEL/", "content": "Affymetrix CEL / CEL.gz"},
        {"level": "Mode A IDAT", "path": "raw/GSM*/IDAT/", "content": "Illumina 表达或甲基化 IDAT"},
        {"level": "Mode B 临时 raw", "path": "temporary/GSM*/", "content": "仅供转换、验证后删除的 raw files"},
        {"level": "临时工作区", "path": "temporary/GSM*/work/", "content": "staging 与断点恢复"},
        {"level": "10x 矩阵", "path": "processed/GSM*/matrix_10x/", "content": "sc/snRNA 的 raw/filtered feature-barcode matrix"},
        {"level": "bulk count matrix", "path": "processed/gene_count_matrix.tsv", "content": "bulk RNA-seq gene × sample counts"},
        {"level": "RNA velocity（可选）", "path": "processed/GSM*/velocity/", "content": "仅 sc/snRNA 且用户要求时的 spliced/unspliced"},
        {"level": "平台注释", "path": "annotation/platform_annotation/", "content": "probe 到 gene 映射"},
        {"level": "QC", "path": "qc/", "content": "芯片或测序 QC 中间文件"},
        {"level": "统一报告", "path": "reports/report.html", "content": "唯一的人类可读报告"},
        {"level": "机器报告", "path": "reports/*.tsv", "content": "供程序读取的审计证据"},
        {"level": "日志", "path": "reports/logs/", "content": "下载与分析原始日志"},
        {"level": "状态", "path": "reports/status/", "content": "原子完成 marker"},
    ]
    directory_table = table(directory_rows, ["level", "path", "content"], root)
    sections.append(
        section(
            "目录与层级说明",
            directory_table,
            root,
            output,
            [root, root / "metadata", root / "reports"],
            "directories",
        )
    )
    sections.append(
        section(
            "Assay 分流",
            table(
                data["assay"],
                ["gse", "gsm", "gpl", "assay_type", "modality", "raw_file_type", "workflow", "evidence"],
                root,
                "尚未运行 detect_assay.py。",
            )
            + table(
                data["platforms"],
                ["gse", "gpl", "title", "technology", "assay_type", "raw_file_type", "array_type", "annotation_version"],
                root,
                "尚未写入 platform_metadata.tsv。",
            )
            + table(
                data["donors"],
                ["gse", "donor_id", "sex", "age", "organism", "notes"],
                root,
                "尚未写入 donor_metadata.tsv。",
            ),
            root,
            output,
            [paths["assay"], paths["platforms"], paths["donors"]],
            "assay",
        )
    )
    storage_body = (
        table(
            data["storage"],
            [
                "gse",
                "assay_type",
                "modality",
                "raw_file_type",
                "retain_raw_files",
                "storage_mode",
                "final_product",
                "source_preference",
                "allow_sra_lite",
                "confirmed_at",
                "validation_status",
                "deletion_status",
                "deletion_time",
            ],
            root,
            "尚未记录存储策略。大规模下载前必须确认是否长期保存 raw files。",
        )
        + table(
            data["storage_audit"],
            ["gse", "gsm", "check", "status", "message"],
            root,
            "尚未运行 storage policy audit。",
        )
        + table(
            data["release"],
            [
                "gse", "gsm", "member_runs", "final_product", "download_status",
                "conversion_status", "processed_audit", "release_status",
                "candidate_bytes", "released_at", "message",
            ],
            root,
            "尚无逐 GSM release 证据。",
        )
        + table(
            data["conversion"],
            [
                "gse",
                "gsm",
                "tool",
                "tool_version",
                "input_fastq",
                "output_matrix",
                "validated_at",
            ],
            root,
            "尚未记录 conversion provenance。",
        )
        + table(
            data["deletion_log"],
            ["gse", "gsm", "srr", "path", "bytes", "md5", "validation_report", "deleted_at"],
            root,
            "无 FASTQ 删除记录。",
        )
    )
    sections.append(
        section(
            "存储策略与原始数据生命周期",
            storage_body,
            root,
            output,
            [
                paths["storage"],
                paths["storage_audit"],
                paths["release"],
                paths["conversion"],
                paths["deletion_log"],
            ],
            "storage",
        )
    )

    sample_columns = [
        "gse",
        "gsm",
        "title",
        "organism",
        "tissue",
        "condition",
        "treatment",
        "chemistry",
        "instrument_model",
        "run_count",
        "lane_count",
        "read_structure",
        "selected_source",
        "final_product",
        "status",
    ]
    sections.append(
        section(
            "样本信息",
            table(data["samples"], sample_columns, root),
            root,
            output,
            [paths["samples"], root / "metadata/sample_characteristics.tsv"],
            "samples",
        )
    )

    run_columns = [
        "gse",
        "gsm",
        "srx",
        "srr",
        "lane",
        "library_layout",
        "read_structure",
        "expected_spots",
    ]
    sections.append(
        section(
            "run、lane 与 read 结构",
            table(data["expected"], run_columns, root),
            root,
            output,
            [paths["expected"], root / "metadata/srr_gsm_mapping.tsv"],
            "runs",
        )
    )

    sections.append(
        section(
            "下载前预检",
            table(
                data["preflight"],
                ["level", "gse", "gsm", "srr", "check", "message"],
                root,
                "尚未运行 preflight audit。",
            ),
            root,
            output,
            [paths["preflight"], root / "reports/preflight_checks.tsv"],
            "preflight",
        )
    )

    count_rows = [
        {"type": "NGDC coverage", "value": key, "count": str(value)}
        for key, value in sorted(ngdc_counts.items())
    ] + [
        {"type": "最终数据源", "value": key, "count": str(value)}
        for key, value in sorted(source_counts.items())
    ] + [
        {"type": "Provenance", "value": key, "count": str(value)}
        for key, value in sorted(provenance_counts.items())
    ]
    provenance_answer = (
        "<p><strong>作者原始上传还是数据库转换：</strong>"
        "按每个 run 的官方对象分类与 <code>selected_provenance</code> 判定，"
        "transport endpoint 与 provenance 分开；Phred 分布不用于证明 provenance。"
        "<code>NGDC_MIRROR_SRA</code> 不是作者原始 FASTQ，"
        "<code>ARCHIVE_GENERATED_FASTQ</code> 是数据库归档内容转换得到的 FASTQ，"
        "<code>SRA_LITE</code> 是显式 opt-in 的简化质量对象。</p>"
    )
    routing_detail = table(
        data["sources"],
        [
            "gse",
            "gsm",
            "srr",
            "ngdc_status",
            "selected_source",
            "selected_provenance",
            "object_class",
            "quality_class",
            "transport_endpoint",
            "final_product",
            "selection_reason",
        ],
        root,
        "尚未生成 source manifest。",
    )
    sections.append(
        section(
            "NGDC coverage、数据源与 provenance",
            provenance_answer
            + table(count_rows, ["type", "value", "count"], root)
            + "<details><summary>查看逐 run 路由</summary>"
            + routing_detail
            + "</details>",
            root,
            output,
            [
                paths["coverage"],
                paths["sources"],
                root / "metadata/sra_source_manifest.tsv",
            ],
            "routing",
        )
    )

    download_rows = data["downloads"] or raw_download_rows
    download_columns = (
        [
            "gse",
            "gsm",
            "srr",
            "source",
            "selected_provenance",
            "provenance",
            "object_class",
            "quality_class",
            "final_product",
            "expected_spots",
            "observed_r1",
            "observed_r2",
            "attempt_count",
            "resume_count",
            "integrity_methods",
            "status",
            "message",
        ]
        if data["downloads"]
        else [
            "gse",
            "gsm",
            "srr",
            "source",
            "provenance",
            "object_class",
            "quality_class",
            "final_product",
            "observed_r1",
            "observed_r2",
            "attempt_count",
            "resume_count",
            "integrity_methods",
            "validation",
            "completed_at",
        ]
    )
    sections.append(
        section(
            "下载、转换与完整性",
            table(download_rows, download_columns, root, "尚无完成的下载记录。"),
            root,
            output,
            [paths["downloads"], *download_manifests],
            "downloads",
        )
    )
    sections.append(
        section(
            "断点续传与失败状态",
            table(
                transfer_states,
                [
                    "run",
                    "phase",
                    "status",
                    "attempt_count",
                    "resume_count",
                    "bytes_resumed",
                    "error_class",
                    "last_error",
                    "updated_at",
                ],
                root,
                "尚无传输状态记录。",
            ),
            root,
            output,
            [root / "reports/status"],
            "transfer-recovery",
        )
    )

    sections.append(
        section(
            "转换状态",
            table(
                data["conversion"],
                [
                    "gse",
                    "gsm",
                    "tool",
                    "tool_version",
                    "input_fastq",
                    "output_matrix",
                    "validated_at",
                ],
                root,
                "尚未记录 conversion provenance。",
            )
            + table(
                data["final"],
                ["gse", "gsm", "raw_shape", "filtered_shape", "loom_shape", "status", "message"],
                root,
                "尚未运行 processed output audit，或本项目仅保留 raw files。",
            ),
            root,
            output,
            [paths["conversion"], paths["final"], root / "processed"],
            "outputs",
        )
    )

    legacy = legacy_reports(root)
    legacy_html = ""
    if legacy:
        rendered = []
        for path in legacy:
            rendered.append(
                "<details><summary>"
                f"{html.escape(project_relative(root, path))}</summary>"
                f"<pre>{esc(path.read_text(errors='replace'), root)}</pre></details>"
            )
        legacy_html = "<h3>已纳入的旧版 Markdown 报告</h3>" + "".join(rendered)
    sections.append(
        section(
            "工具版本、证据与复现信息",
            table(data["tools"], list(data["tools"][0]) if data["tools"] else ["tool", "version"], root)
            + legacy_html,
            root,
            output,
            [paths["tools"], root / "pixi.toml", root / "pixi.lock", *legacy],
            "repro",
        )
    )

    multiqc = locate_multiqc(root, args.multiqc_html)
    if multiqc is not None:
        multiqc_payload = base64.b64encode(multiqc.read_bytes()).decode("ascii")
    else:
        multiqc_payload = existing_multiqc_payload(output)
    multiqc_data = (
        '<script type="application/octet-stream" id="multiqc-data">'
        + multiqc_payload
        + "</script>"
        if multiqc_payload
        else ""
    )
    generated = datetime.now().astimezone().isoformat(timespec="seconds")
    document = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(gse)} 数据获取与转换报告</title>
<style>
:root{{--bg:#f3f6f8;--panel:#fff;--ink:#17212b;--muted:#66727d;--line:#dce3e8;--brand:#176b87;--ok:#16794a;--bad:#b42318;--warn:#a15c00}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 system-ui,-apple-system,"Noto Sans CJK SC","Microsoft YaHei",sans-serif}}
header{{padding:2.2rem max(1rem,calc((100% - 1500px)/2));background:linear-gradient(120deg,#0e526c,#2288a4);color:#fff}}
header h1{{margin:0 0 .5rem;font-size:clamp(1.7rem,4vw,2.6rem)}} header p{{margin:.2rem 0;opacity:.9}}
nav{{position:sticky;top:0;z-index:5;display:flex;gap:.35rem;overflow:auto;padding:.6rem max(1rem,calc((100% - 1500px)/2));background:#102d3a}}
nav a{{color:#e9f7fb;text-decoration:none;white-space:nowrap;padding:.35rem .65rem;border-radius:.35rem}} nav a:hover{{background:#24576a}}
main{{max-width:1500px;margin:auto;padding:1rem}} .cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:.7rem;margin:1rem 0}}
.card,section{{background:var(--panel);border:1px solid var(--line);border-radius:.7rem;box-shadow:0 2px 10px #1b3b4b0c}}
.card{{padding:.8rem}} .card span{{display:block;color:var(--muted);font-size:.85rem}} .card strong{{font-size:1.35rem}}
section{{margin:1rem 0;padding:1rem}} h2{{margin:.1rem 0;color:#124f66}} h3{{color:#24576a}}
.sources{{color:var(--muted);font-size:.86rem}} code{{background:#edf3f5;border-radius:.25rem;padding:.1rem .3rem}}
.table-wrap{{overflow:auto;max-height:640px;border:1px solid var(--line);border-radius:.45rem}} table{{width:100%;border-collapse:collapse;font-size:.9rem}}
th,td{{padding:.48rem .58rem;border-bottom:1px solid var(--line);vertical-align:top;text-align:left}} th{{position:sticky;top:0;background:#eaf1f4;z-index:1}} tr:hover{{background:#f5fafb}}
.badge{{display:inline-block;padding:.08rem .4rem;border-radius:999px;background:#e8edf0}} .badge.ok{{color:var(--ok);background:#e3f6ec}} .badge.bad{{color:var(--bad);background:#fde8e7}} .badge.warn{{color:var(--warn);background:#fff1d6}}
.empty{{color:var(--muted);font-style:italic}} details{{margin:.35rem 0}} summary{{cursor:pointer;color:#175f79}} pre{{white-space:pre-wrap;word-break:break-word;background:#f6f8f9;padding:.65rem;border-radius:.35rem}}
#report-filter{{width:min(520px,100%);padding:.55rem .7rem;border:1px solid var(--line);border-radius:.4rem}}
button{{padding:.5rem .8rem;border:0;border-radius:.4rem;background:var(--brand);color:#fff;cursor:pointer}}
#multiqc-frame{{width:100%;min-height:900px;border:1px solid var(--line);border-radius:.45rem;margin-top:.7rem;background:#fff}}
.distribution-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:.8rem;margin:1rem 0}} .distribution{{border:1px solid var(--line);border-radius:.45rem;padding:.7rem}} .distribution>div{{height:160px;display:flex;align-items:end;gap:2px;border-bottom:1px solid var(--line);margin:.5rem 0}} .distribution i{{display:block;flex:1;min-width:2px;background:#2288a4;border-radius:2px 2px 0 0}} .distribution small{{color:var(--muted)}}
footer{{color:var(--muted);text-align:center;padding:1.5rem}} a{{color:#086d91}} @media print{{nav,button,#report-filter{{display:none}} .table-wrap{{max-height:none;overflow:visible}} section{{break-inside:avoid}}}}
</style>
</head>
<body>
<header><h1>{html.escape(gse)} 数据获取与转换报告</h1>
<p>统一中文展示层；TSV、JSON、log 和 status marker 作为机器证据保留。</p>
<p>生成时间：{html.escape(generated)}　项目相对根目录：<code>.</code></p></header>
<nav>{navigation}</nav>
<main>
<div class="cards">{card_html}</div>
<p><label for="report-filter">筛选所有表格：</label> <input id="report-filter" type="search" placeholder="输入 GSM、SRR、状态或关键词"></p>
{''.join(sections)}
</main>
<footer>由 <code>download-geo-assay/scripts/build_report.py</code> 原子生成。</footer>
{multiqc_data}
<script>
const filter=document.getElementById("report-filter");
filter.addEventListener("input",()=>{{const q=filter.value.toLowerCase();document.querySelectorAll("table.filterable tbody tr").forEach(r=>r.hidden=!r.textContent.toLowerCase().includes(q));}});
function loadMultiQC(){{const data=document.getElementById("multiqc-data");const frame=document.getElementById("multiqc-frame");if(!data||!frame)return;const bytes=Uint8Array.from(atob(data.textContent.trim()),c=>c.charCodeAt(0));frame.srcdoc=new TextDecoder("utf-8").decode(bytes);}}
const multiqcButton=document.getElementById("load-multiqc");if(multiqcButton){{multiqcButton.addEventListener("click",loadMultiQC);loadMultiQC();}}
</script>
</body></html>
"""
    return document, multiqc


def main() -> int:
    parser = argparse.ArgumentParser(description="生成统一中文 HTML 项目报告")
    parser.add_argument("--root", required=True, type=Path, help="GSE 项目根目录")
    parser.add_argument("--output", type=Path, help="默认 reports/report.html")
    parser.add_argument("--multiqc-html", type=Path, help="需要完整内嵌的 MultiQC HTML")
    parser.add_argument(
        "--consume-multiqc",
        action="store_true",
        help="报告成功写入后删除明确指定且位于项目内的临时 MultiQC HTML",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    if not root.is_dir():
        raise SystemExit(f"项目根目录不存在：{root}")
    if args.multiqc_html and not args.multiqc_html.is_absolute():
        args.multiqc_html = (root / args.multiqc_html).resolve()
    if args.consume_multiqc and args.multiqc_html:
        try:
            args.multiqc_html.relative_to(root)
        except ValueError as exc:
            raise SystemExit("拒绝删除项目根目录外的 MultiQC 文件") from exc

    output = args.output
    if output is None:
        output = root / "reports/report.html"
    elif not output.is_absolute():
        output = root / output
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    lock_path = output.parent / ".report.lock"
    temp = output.with_name(f".{output.name}.tmp.{os.getpid()}")

    with lock_path.open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        document, multiqc = build(args)
        try:
            with temp.open("w", encoding="utf-8", newline="\n") as handle:
                handle.write(document)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp, output)
        finally:
            temp.unlink(missing_ok=True)

        if args.consume_multiqc and multiqc:
            try:
                multiqc.relative_to(root)
            except ValueError as exc:
                raise SystemExit("拒绝删除项目根目录外的 MultiQC 文件") from exc
            if multiqc != output:
                multiqc.unlink(missing_ok=True)

    print(f"REPORT path={project_relative(root, output)} bytes={output.stat().st_size}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
