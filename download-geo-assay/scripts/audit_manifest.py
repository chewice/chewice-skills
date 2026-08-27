#!/usr/bin/env python3
"""Fail-fast source/provenance audit and per-GSM peak-space preflight."""

from __future__ import annotations

import argparse
import csv
import os
import re
import shutil
import statistics
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from capabilities import CapabilityError, classify_source, load_source_capabilities  # noqa: E402
from project_layout import policy_for_gsm, read_config, read_tsv  # noqa: E402

REQUIRED = {
    "gse", "gsm", "srx", "srr", "library_layout", "expected_spots",
    "ngdc_status", "selected_source", "selected_provenance", "selected_urls",
    "selected_bytes", "selected_md5", "read_roles", "final_product",
}
NGDC_STATUS = {"available", "missing", "invalid", "unreachable", "not_probed"}
ROLES = {"SRA", "R1", "R2", "I1", "I2", "BAM", "OTHER"}
PRODUCTS = {"pending", "fastq", "sra", "matrix_velocity", "matrix_10x", "gene_count_matrix"}


def refresh_report(root: Path) -> None:
    reporter = Path(__file__).with_name("build_report.py")
    if reporter.is_file():
        subprocess.run([sys.executable, str(reporter), "--root", str(root)], check=False)


def split(value: str) -> list[str]:
    return [item.strip() for item in value.rstrip("\r").split(";") if item.strip()]


def directory_bytes(path: Path) -> int:
    total = 0
    for directory, _, files in os.walk(path):
        for name in files:
            try:
                total += (Path(directory) / name).stat().st_size
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


def unit_peak(source_bytes: int, has_sra: bool, converted: bool, lookahead: int, headroom: int) -> tuple[int, int]:
    fastq_expansion = source_bytes * 4 if has_sra else source_bytes
    fasterq_scratch = source_bytes * 10 if has_sra else 0
    conversion_scratch = fastq_expansion if converted else 0
    processed = max(1024**3, fastq_expansion // 4) if converted else 0
    working = source_bytes + fastq_expansion + fasterq_scratch + conversion_scratch + lookahead
    return working, working + processed + headroom


def detect_user_quota_remaining() -> int | None:
    """Return a conservative remaining hard/soft quota in bytes when quota(1) exposes one."""
    if shutil.which("quota") is None:
        return None
    result = subprocess.run(
        ["quota", "-w", "-v"],
        text=True,
        capture_output=True,
        check=False,
        env={**os.environ, "LC_ALL": "C"},
    )
    if result.returncode not in {0, 1}:
        return None
    remaining: list[int] = []
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) < 4 or not all(value.isdigit() for value in fields[1:4]):
            continue
        used, soft, hard = map(int, fields[1:4])
        limit = hard or soft
        if limit > 0:
            remaining.append(max(0, limit - used) * 1024)
    return min(remaining) if remaining else None


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
    load_source_capabilities(root)

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
            {"level": level, "gse": row.get("gse", ""), "gsm": row.get("gsm", ""),
             "srr": row.get("srr", ""), "check": check, "message": message}
        )

    seen: set[str] = set()
    sample_runs: dict[str, list[dict[str, str]]] = defaultdict(list)
    all_sizes: list[int] = []
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
        if row["ngdc_status"] not in NGDC_STATUS:
            add("ERROR", row, "ngdc_status", f"invalid {row['ngdc_status']!r}")
        if row["final_product"] not in PRODUCTS:
            add("ERROR", row, "final_product", f"invalid {row['final_product']!r}")
        try:
            object_class, quality_class, object_info = classify_source(
                row["selected_source"], row["selected_provenance"], root
            )
        except CapabilityError as exc:
            add("ERROR", row, "source_capability", str(exc))
            object_class = quality_class = ""
            object_info = {}
        if row.get("object_class") and row["object_class"] != object_class:
            add("ERROR", row, "object_class", f"declared={row['object_class']} expected={object_class}")
        if row.get("quality_class") and row["quality_class"] != quality_class:
            add("ERROR", row, "quality_class", f"declared={row['quality_class']} expected={quality_class}")
        policy = policy_for_gsm(root, row["gsm"], required=False)
        allow_lite = bool(policy and policy.get("allow_sra_lite") == "true") or read_config(root).get("allow_sra_lite") == "true"
        if object_class == "SRA_LITE" and not allow_lite:
            add("ERROR", row, "sra_lite", "SRA Lite 未获显式授权")
        if object_info.get("raw_input") is False:
            add("ERROR", row, "object_class", "processed/aligned object 不能作为默认 raw input")

        urls, sizes, md5s, roles = (
            split(row["selected_urls"]), split(row["selected_bytes"]),
            split(row["selected_md5"]), split(row["read_roles"]),
        )
        if not urls:
            add("ERROR", row, "source_arrays", "no selected URL/accession")
        if len(roles) != len(urls):
            add("ERROR", row, "source_arrays", f"roles={len(roles)} URLs={len(urls)}")
        if sizes and len(sizes) != len(urls):
            add("ERROR", row, "source_arrays", f"bytes={len(sizes)} URLs={len(urls)}")
        if md5s and len(md5s) != len(urls):
            add("ERROR", row, "source_arrays", f"md5={len(md5s)} URLs={len(urls)}")
        if any(role not in ROLES for role in roles) or "OTHER" in roles:
            add("ERROR", row, "read_roles", f"ambiguous/invalid roles {roles}")
        filename_roles = [obvious_role(url) for url in urls]
        for url, declared, detected in zip(urls, roles, filename_roles):
            if detected and declared != detected:
                add("ERROR", row, "filename_roles", f"{Path(url).name}: filename={detected} declared={declared}")
        if row["library_layout"].upper() == "PAIRED" and set(roles).issubset({"R1", "R2", "I1", "I2"}) and not {"R1", "R2"}.issubset(roles):
            add("ERROR", row, "read_roles", f"paired layout lacks R1/R2: {roles}")
        for value in sizes:
            if not value.isdigit() or int(value) <= 0:
                add("ERROR", row, "file_size", f"invalid selected_bytes={value!r}")
            else:
                all_sizes.append(int(value))
        for value in md5s:
            if value and not re.fullmatch(r"[0-9a-fA-F]{32}", value):
                add("ERROR", row, "md5", f"invalid MD5 {value!r}")
        preference = policy.get("source_preference", "auto") if policy else read_config(root).get("source_preference", "auto")
        if preference != "auto" and not row["selected_source"].startswith(preference + "_"):
            add("ERROR", row, "source_preference", f"requested={preference} selected={row['selected_source']}")
        if not row.get("selection_reason") and not row.get("fallback_reason"):
            add("WARNING", row, "selection_reason", "legacy manifest lacks selection evidence")

    summary_row = {"gse": rows[0]["gse"], "gsm": "", "srr": ""}
    study_rows = read_tsv(root / "metadata/study_metadata.tsv")
    if study_rows:
        if args.expected_samples is None and study_rows[0].get("expected_samples", "").isdigit():
            args.expected_samples = int(study_rows[0]["expected_samples"])
        if args.expected_runs is None and study_rows[0].get("expected_runs", "").isdigit():
            args.expected_runs = int(study_rows[0]["expected_runs"])
    if args.expected_samples is not None and len(sample_runs) != args.expected_samples:
        add("ERROR", summary_row, "sample_count", f"expected={args.expected_samples} observed={len(sample_runs)}")
    if args.expected_runs is not None and len(rows) != args.expected_runs:
        add("ERROR", summary_row, "run_count", f"expected={args.expected_runs} observed={len(rows)}")
    for gsm, unit_rows in sorted(sample_runs.items()):
        if len(unit_rows) > 1:
            add("INFO", unit_rows[0], "multi_run", f"{gsm} has {len(unit_rows)} runs; one release unit")
    if all_sizes:
        median = statistics.median(all_sizes)
        for row in rows:
            for value in split(row["selected_bytes"]):
                if value.isdigit() and median and int(value) < median * 0.01:
                    add("WARNING", row, "size_outlier", f"{value} bytes is <1% of median {int(median)}")

    config = read_config(root)
    caps: dict[str, int] = {}
    if args.max_project_bytes is not None:
        caps["project"] = args.max_project_bytes
    for key, label in (
        ("max_project_bytes", "project"),
        ("max_temporary_bytes", "working"),
        ("user_quota_bytes", "quota"),
    ):
        if label not in caps and config.get(key, "").isdigit():
            caps[label] = int(config[key])
    detected_quota = None
    if "quota" not in caps:
        detected_quota = detect_user_quota_remaining()
        if detected_quota is not None:
            caps["quota"] = detected_quota
    headroom = int(config.get("min_headroom_bytes", 10 * 1024**3))
    current = directory_bytes(root)
    free = shutil.disk_usage(root).free
    unit_sources = {
        gsm: sum(int(value) for row in unit_rows for value in split(row["selected_bytes"]) if value.isdigit())
        for gsm, unit_rows in sample_runs.items()
    }
    lookahead = max(unit_sources.values(), default=0)
    for gsm, unit_rows in sorted(sample_runs.items()):
        source_bytes = unit_sources[gsm]
        has_sra = any("SRA" in split(row["read_roles"]) for row in unit_rows)
        converted = any(row["final_product"] not in {"pending", "fastq", "sra"} for row in unit_rows)
        working, addition = unit_peak(source_bytes, has_sra, converted, lookahead, headroom)
        row = unit_rows[0]
        limits = {"free_space": free, **caps}
        violated: list[str] = []
        for label, limit in limits.items():
            needed = current + addition if label in {"project", "quota"} else working + headroom
            if needed > limit:
                violated.append(f"{label}: needed={needed} limit={limit}")
        if violated:
            add("ERROR", row, "space_guard", f"unit_peak blocks next unit; {'; '.join(violated)}")
        else:
            add(
                "INFO", row, "space_guard",
                f"source={source_bytes} working_peak={working} project_addition={addition} "
                f"headroom={headroom} strict_limit={min(limits.values()) if limits else 'none'}",
            )

    add(
        "INFO",
        summary_row,
        "quota_detection",
        (
            f"remaining_bytes={caps['quota']} source={'quota(1)' if detected_quota is not None else 'config'}"
            if "quota" in caps
            else "quota(1) did not expose a finite user quota; free-space and configured caps still apply"
        ),
    )

    add(
        "INFO", summary_row, "summary",
        f"samples={len(sample_runs)} runs={len(rows)} sources={dict(Counter(row['selected_source'] for row in rows))}",
    )
    report = report if report.is_absolute() else root / report
    report.parent.mkdir(parents=True, exist_ok=True)
    temp = report.with_suffix(report.suffix + ".tmp")
    with temp.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=("level", "gse", "gsm", "srr", "check", "message"), delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(findings)
    temp.replace(report)
    levels = Counter(item["level"] for item in findings)
    print(f"AUDIT samples={len(sample_runs)} runs={len(rows)} errors={levels['ERROR']} warnings={levels['WARNING']} report={report}")
    refresh_report(root)
    return 1 if levels["ERROR"] else 0


if __name__ == "__main__":
    sys.exit(main())
