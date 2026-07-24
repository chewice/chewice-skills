#!/usr/bin/env python3
"""Fail-fast audit for a normalized GEO/SRA per-run source manifest."""

from __future__ import annotations

import argparse
import csv
import os
import re
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path


REQUIRED = {
    "gse",
    "gsm",
    "srx",
    "srr",
    "library_layout",
    "expected_spots",
    "ngdc_status",
    "selected_source",
    "selected_provenance",
    "selected_urls",
    "selected_bytes",
    "selected_md5",
    "read_roles",
    "final_product",
    "fallback_reason",
}
SOURCES = {"ngdc_gsa", "ngdc_insdc", "ena_submitted", "ena_fastq", "ncbi_sra"}
PROVENANCE = {
    "AUTHOR_SUBMITTED",
    "GSA_AUTHOR_SUBMITTED",
    "NGDC_MIRROR_SRA",
    "ARCHIVE_NORMALIZED_SRA",
    "ARCHIVE_GENERATED_FASTQ",
    "AUTHOR_SUBMITTED_BAM",
    "GEO_PROCESSED",
}
NGDC_STATUS = {"available", "missing", "invalid", "unreachable", "not_probed"}
ROLES = {"SRA", "R1", "R2", "I1", "I2", "BAM", "OTHER"}
PRODUCTS = {"fastq", "sra", "matrix_velocity"}


def refresh_report(root: Path) -> None:
    reporter = Path(__file__).with_name("build_report.py")
    if reporter.is_file():
        subprocess.run(
            [sys.executable, str(reporter), "--root", str(root)],
            check=False,
        )


def split(value: str) -> list[str]:
    return [item.strip() for item in value.rstrip("\r").split(";") if item.strip()]


def directory_bytes(path: Path) -> int:
    total = 0
    for root, _, files in os.walk(path):
        for name in files:
            try:
                total += (Path(root) / name).stat().st_size
            except FileNotFoundError:
                pass
    return total


def obvious_role(value: str) -> str:
    name = Path(value.split("?", 1)[0]).name.upper()
    for candidate in ("R1", "R2", "I1", "I2"):
        if re.search(rf"(?:^|[_.-]){candidate}(?:[_.-]|$)", name):
            return candidate
    match = re.search(r"_([12])\.F(?:AST)?Q(?:\.GZ)?$", name)
    return f"R{match.group(1)}" if match else ""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--expected-samples", type=int)
    parser.add_argument("--expected-runs", type=int)
    parser.add_argument("--max-project-bytes", type=int)
    args = parser.parse_args()
    root = args.root.resolve()
    manifest = args.manifest if args.manifest.is_absolute() else root / args.manifest
    report = args.report or root / "reports/preflight_audit.tsv"

    with manifest.open(newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fields = set(reader.fieldnames or [])
        rows = list(reader)
    missing_columns = REQUIRED - fields
    if missing_columns:
        raise SystemExit(f"Missing source-manifest columns: {sorted(missing_columns)}")
    if not rows:
        raise SystemExit("Source manifest is empty")

    findings: list[dict[str, str]] = []

    def add(level: str, row: dict[str, str], check: str, message: str) -> None:
        findings.append(
            {
                "level": level,
                "gse": row.get("gse", ""),
                "gsm": row.get("gsm", ""),
                "srr": row.get("srr", ""),
                "check": check,
                "message": message,
            }
        )

    seen: set[str] = set()
    sample_runs: dict[str, list[dict[str, str]]] = defaultdict(list)
    all_sizes: list[int] = []
    total_selected_bytes = 0
    for row in rows:
        run = row["srr"].strip()
        sample_runs[row["gsm"]].append(row)
        if run in seen:
            add("ERROR", row, "unique_run", "duplicate run accession")
        seen.add(run)
        if not re.fullmatch(r"GSE\d+", row["gse"]):
            add("ERROR", row, "gse_format", f"invalid {row['gse']!r}")
        if not re.fullmatch(r"GSM\d+", row["gsm"]):
            add("ERROR", row, "gsm_format", f"invalid {row['gsm']!r}")
        if not re.fullmatch(r"(?:[SED]RR|CRR)\d+", run):
            add("ERROR", row, "run_format", f"invalid {run!r}")
        if row["library_layout"].upper() not in {"PAIRED", "SINGLE"}:
            add("ERROR", row, "layout", f"invalid {row['library_layout']!r}")
        for column in ("expected_spots", "cb_length", "umi_length"):
            value = row.get(column, "").strip().rstrip("\r")
            if value and not value.isdigit():
                add("ERROR", row, "numeric_field", f"{column}={value!r}")
        if row["selected_source"] not in SOURCES:
            add("ERROR", row, "source", f"invalid {row['selected_source']!r}")
        if row["selected_provenance"] not in PROVENANCE:
            add(
                "ERROR",
                row,
                "provenance",
                f"invalid {row['selected_provenance']!r}",
            )
        if row["ngdc_status"] not in NGDC_STATUS:
            add("ERROR", row, "ngdc_status", f"invalid {row['ngdc_status']!r}")
        if row["final_product"] not in PRODUCTS:
            add("ERROR", row, "final_product", f"invalid {row['final_product']!r}")

        urls = split(row["selected_urls"])
        sizes = split(row["selected_bytes"])
        md5s = split(row["selected_md5"])
        roles = split(row["read_roles"])
        if not urls:
            add("ERROR", row, "source_arrays", "no selected URL/accession")
        if len(roles) != len(urls):
            add(
                "ERROR",
                row,
                "source_arrays",
                f"roles={len(roles)} URLs={len(urls)}",
            )
        if sizes and len(sizes) != len(urls):
            add(
                "ERROR",
                row,
                "source_arrays",
                f"bytes={len(sizes)} URLs={len(urls)}",
            )
        if md5s and len(md5s) != len(urls):
            add(
                "ERROR",
                row,
                "source_arrays",
                f"md5={len(md5s)} URLs={len(urls)}",
            )
        if any(role not in ROLES for role in roles) or "OTHER" in roles:
            add("ERROR", row, "read_roles", f"ambiguous/invalid roles {roles}")
        filename_roles = [obvious_role(url) for url in urls]
        for url, declared, detected in zip(urls, roles, filename_roles):
            if detected and declared != detected:
                add(
                    "ERROR",
                    row,
                    "filename_roles",
                    f"{Path(url).name}: filename={detected} declared={declared}",
                )
        if urls and not any(filename_roles) and all(
            role in {"R1", "R2", "I1", "I2"} for role in roles
        ):
            add(
                "WARNING",
                row,
                "filename_roles",
                f"no explicit R1/R2/I1/I2 pattern; roles rely on metadata: {roles}",
            )
        if row["library_layout"].upper() == "PAIRED" and set(roles).issubset(
            {"R1", "R2", "I1", "I2"}
        ):
            if not {"R1", "R2"}.issubset(roles):
                add("ERROR", row, "read_roles", f"paired layout lacks R1/R2: {roles}")
        for value in sizes:
            if not value.isdigit() or int(value) <= 0:
                add("ERROR", row, "file_size", f"invalid selected_bytes={value!r}")
            else:
                size = int(value)
                all_sizes.append(size)
                total_selected_bytes += size
        for value in md5s:
            if value and not re.fullmatch(r"[0-9a-fA-F]{32}", value):
                add("ERROR", row, "md5", f"invalid MD5 {value!r}")

        selected_ngdc = row["selected_source"].startswith("ngdc_")
        if row["ngdc_status"] == "available" and not selected_ngdc:
            if not row["fallback_reason"].strip():
                add(
                    "ERROR",
                    row,
                    "ngdc_priority",
                    "available NGDC run bypassed without fallback reason",
                )
            else:
                add(
                    "WARNING",
                    row,
                    "ngdc_priority",
                    f"NGDC bypassed: {row['fallback_reason']}",
                )
        if not selected_ngdc and not row["fallback_reason"].strip():
            add("ERROR", row, "fallback_reason", "non-NGDC source lacks reason")
        if row["selected_source"] == "ngdc_insdc" and (
            row["selected_provenance"] != "NGDC_MIRROR_SRA" or roles != ["SRA"]
        ):
            add(
                "ERROR",
                row,
                "ngdc_provenance",
                "NGDC INSDC must be NGDC_MIRROR_SRA with SRA role",
            )

    sample_count = len(sample_runs)
    run_count = len(rows)
    summary_row = {"gse": rows[0]["gse"], "gsm": "", "srr": ""}
    study_path = root / "metadata/study_metadata.tsv"
    if study_path.is_file():
        with study_path.open(newline="") as handle:
            study_rows = list(csv.DictReader(handle, delimiter="\t"))
        if study_rows:
            if args.expected_samples is None and study_rows[0].get("expected_samples", "").isdigit():
                args.expected_samples = int(study_rows[0]["expected_samples"])
            if args.expected_runs is None and study_rows[0].get("expected_runs", "").isdigit():
                args.expected_runs = int(study_rows[0]["expected_runs"])
    if args.expected_samples is not None and sample_count != args.expected_samples:
        add(
            "ERROR",
            summary_row,
            "sample_count",
            f"expected={args.expected_samples} observed={sample_count}",
        )
    if args.expected_runs is not None and run_count != args.expected_runs:
        add(
            "ERROR",
            summary_row,
            "run_count",
            f"expected={args.expected_runs} observed={run_count}",
        )
    for gsm, sample_rows in sorted(sample_runs.items()):
        lanes = {row.get("lane", "") for row in sample_rows if row.get("lane", "")}
        if len(sample_rows) > 1:
            add(
                "INFO",
                sample_rows[0],
                "multi_run",
                f"{gsm} has {len(sample_rows)} runs",
            )
        if len(lanes) > 1:
            add(
                "INFO",
                sample_rows[0],
                "multi_lane",
                f"{gsm} has lanes {sorted(lanes)}",
            )
    if all_sizes:
        median = statistics.median(all_sizes)
        for row in rows:
            for value in split(row["selected_bytes"]):
                if value.isdigit() and median > 0 and int(value) < median * 0.01:
                    add(
                        "WARNING",
                        row,
                        "size_outlier",
                        f"{value} bytes is <1% of median {int(median)}",
                    )

    if args.max_project_bytes is None:
        config_path = root / "metadata/acquisition_config.tsv"
        if config_path.is_file():
            with config_path.open(newline="") as handle:
                config = {
                    row["key"]: row["value"].rstrip("\r")
                    for row in csv.DictReader(handle, delimiter="\t")
                }
            if config.get("max_project_bytes", "").isdigit():
                args.max_project_bytes = int(config["max_project_bytes"])
    current_bytes = directory_bytes(root)
    projected_peak = current_bytes + total_selected_bytes * 4 + 30 * 1024**3
    if args.max_project_bytes is not None and projected_peak > args.max_project_bytes:
        add(
            "ERROR",
            summary_row,
            "space_guard",
            f"projected_peak={projected_peak} exceeds {args.max_project_bytes}",
        )
    else:
        add(
            "INFO",
            summary_row,
            "space_guard",
            f"current={current_bytes} selected={total_selected_bytes} projected_peak={projected_peak}",
        )

    source_counts = Counter(row["selected_source"] for row in rows)
    status_counts = Counter(row["ngdc_status"] for row in rows)
    add(
        "INFO",
        summary_row,
        "summary",
        f"samples={sample_count} runs={run_count} sources={dict(source_counts)} ngdc={dict(status_counts)}",
    )

    report = report if report.is_absolute() else root / report
    report.parent.mkdir(parents=True, exist_ok=True)
    temp = report.with_suffix(report.suffix + ".tmp")
    with temp.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=("level", "gse", "gsm", "srr", "check", "message"),
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(findings)
    temp.replace(report)

    levels = Counter(item["level"] for item in findings)
    print(
        f"AUDIT samples={sample_count} runs={run_count} "
        f"errors={levels['ERROR']} warnings={levels['WARNING']} report={report}"
    )
    refresh_report(root)
    return 1 if levels["ERROR"] else 0


if __name__ == "__main__":
    sys.exit(main())
