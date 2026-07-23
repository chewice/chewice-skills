#!/usr/bin/env python3
"""Audit that every expected run has validated, source-matched download evidence."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def split(value: str) -> list[str]:
    return [item for item in value.rstrip("\r").split(";") if item]


def md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def gzip_test(path: Path) -> None:
    with gzip.open(path, "rb") as handle:
        while handle.read(8 * 1024 * 1024):
            pass


def legacy_log_audit(
    root: Path,
    source_rows: list[dict[str, str]],
    output: Path,
) -> int:
    processing_path = root / "metadata/sample_processing_manifest.tsv"
    if not processing_path.is_file():
        raise SystemExit(
            "Legacy source manifest detected but sample_processing_manifest.tsv is absent"
        )
    processing = read_tsv(processing_path)
    sources = {row["run_accession"]: row for row in source_rows}
    expected_runs = {
        run
        for sample in processing
        for run in split(sample["srrs"])
    }
    errors: list[str] = []
    report_rows: list[dict[str, str]] = []
    for sample in processing:
        gse, gsm = sample["gse"], sample["gsm"]
        label = f"{gse}/{gsm}"
        log_path = root / "reports/logs" / f"{gse}_{gsm}.log"
        marker = root / "reports/status" / gse / f"{gsm}.complete"
        if not log_path.is_file() or not marker.is_file():
            errors.append(f"{label}: missing log or completion marker")
            continue
        log = log_path.read_text(errors="replace")
        validation_end = -1
        for run in split(sample["srrs"]):
            source = sources.get(run)
            if source is None:
                errors.append(f"{label}/{run}: absent from source manifest")
                continue
            expected = int(source["expected_spots"].rstrip("\r"))
            pattern = re.compile(
                rf"Validated {re.escape(run)} FASTQ pairs: "
                rf"(\d+) reads/mate; min_R1=(\d+); CB=(\d+) UMI=(\d+)"
            )
            matches = list(pattern.finditer(log))
            row_errors: list[str] = []
            if not matches:
                row_errors.append("missing successful paired FASTQ validation")
                reads = min_r1 = cb = umi = 0
            else:
                match = matches[-1]
                validation_end = max(validation_end, match.end())
                reads, min_r1, cb, umi = map(int, match.groups())
                if reads != expected:
                    row_errors.append(f"reads={reads} expected={expected}")
                if cb != int(sample["cb_length"]) or umi != int(sample["umi_length"]):
                    row_errors.append("CB/UMI geometry mismatch")
                if min_r1 < cb + umi:
                    row_errors.append("R1 shorter than CB+UMI")
                if source["source"] == "ngdc_sra":
                    evidence = re.compile(
                        rf"Database '{re.escape(run)}\.sra' is consistent"
                    )
                    if not evidence.search(log, 0, match.end()):
                        row_errors.append("missing vdb-validate consistency evidence")
                elif source["source"] == "ena_fastq":
                    for mate in ("1", "2"):
                        evidence = re.compile(
                            rf"{re.escape(run)}_{mate}\.fastq\.gz(?:\.part)?: OK"
                        )
                        if not evidence.search(log, 0, match.end()):
                            row_errors.append(f"missing mate-{mate} MD5 evidence")
                else:
                    row_errors.append(f"unknown legacy source {source['source']}")
            errors.extend(f"{label}/{run}: {message}" for message in row_errors)
            report_rows.append(
                {
                    "gse": gse,
                    "gsm": gsm,
                    "srr": run,
                    "source": source["source"],
                    "provenance": (
                        "NGDC_MIRROR_SRA"
                        if source["source"] == "ngdc_sra"
                        else "ARCHIVE_GENERATED_FASTQ"
                    ),
                    "final_product": "matrix_velocity",
                    "expected_spots": str(expected),
                    "observed_r1": str(reads),
                    "observed_r2": str(reads),
                    "status": "FAIL" if row_errors else "PASS",
                    "message": "; ".join(row_errors),
                }
            )
        completes = list(
            re.finditer(rf"\[[^\]]+\] COMPLETE {re.escape(label)}(?:\s|$)", log)
        )
        if not completes or completes[-1].start() <= validation_end:
            errors.append(f"{label}: completion event missing or precedes validation")

    if set(sources) != expected_runs:
        errors.append("legacy source/run set mismatch")
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_suffix(output.suffix + ".tmp")
    fields = [
        "gse", "gsm", "srr", "source", "provenance", "final_product",
        "expected_spots", "observed_r1", "observed_r2", "status", "message",
    ]
    with temp.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(report_rows)
    temp.replace(output)
    counts = Counter(row["source"] for row in report_rows)
    passed = sum(row["status"] == "PASS" for row in report_rows)
    print(
        f"AUDIT runs={len(report_rows)} unique={len(expected_runs)} "
        f"passed={passed} sources={dict(counts)} errors={len(errors)} report={output}"
    )
    for error in errors:
        print(f"ERROR {error}")
    return 1 if errors else 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--deep", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    manifest = args.manifest or root / "metadata/source_manifest.tsv"
    output = args.output or root / "reports/download_integrity_audit.tsv"
    source_rows = read_tsv(manifest)
    if source_rows and "selected_source" not in source_rows[0]:
        return legacy_log_audit(root, source_rows, output)
    errors: list[str] = []
    report_rows: list[dict[str, str]] = []
    observed: dict[str, dict[str, str]] = {}

    for path in root.glob("GSM*/download_manifest.tsv"):
        for row in read_tsv(path):
            run = row["srr"]
            if run in observed:
                errors.append(f"{run}: duplicate download-manifest rows")
            observed[run] = row

    expected_runs = {row["srr"] for row in source_rows}
    if set(observed) != expected_runs:
        for run in sorted(expected_runs - set(observed)):
            errors.append(f"{run}: missing download-manifest row")
        for run in sorted(set(observed) - expected_runs):
            errors.append(f"{run}: unexpected download-manifest row")

    for source in source_rows:
        run = source["srr"]
        gsm = source["gsm"]
        row_errors: list[str] = []
        evidence = observed.get(run)
        if evidence is None:
            continue
        if evidence.get("validation") != "PASS":
            row_errors.append("validation is not PASS")
        for source_key, evidence_key in (
            ("gse", "gse"),
            ("gsm", "gsm"),
            ("selected_source", "source"),
            ("selected_provenance", "provenance"),
            ("final_product", "final_product"),
        ):
            if source.get(source_key, "") != evidence.get(evidence_key, ""):
                row_errors.append(
                    f"{evidence_key}={evidence.get(evidence_key)!r} "
                    f"expected={source.get(source_key)!r}"
                )
        expected_spots = source.get("expected_spots", "").rstrip("\r")
        if expected_spots and evidence.get("expected_spots") != expected_spots:
            row_errors.append("expected_spots differs from source manifest")
        if source["final_product"] != "sra":
            if evidence.get("observed_r1") != expected_spots:
                row_errors.append(
                    f"R1={evidence.get('observed_r1')} expected={expected_spots}"
                )
            if source.get("library_layout", "").upper() == "PAIRED":
                if evidence.get("observed_r2") != expected_spots:
                    row_errors.append(
                        f"R2={evidence.get('observed_r2')} expected={expected_spots}"
                    )

        sample = root / gsm
        product = source["final_product"]
        files: list[Path] = []
        if product == "fastq":
            files.append(sample / "fastq" / f"{run}_R1.fastq.gz")
            if source.get("library_layout", "").upper() == "PAIRED":
                files.append(sample / "fastq" / f"{run}_R2.fastq.gz")
        elif product == "sra":
            files.append(sample / "sra" / f"{run}.sra")
        elif product == "matrix_velocity":
            final_report = root / "reports/final_output_audit.tsv"
            if not final_report.is_file():
                row_errors.append("matrix_velocity cleanup lacks final-output audit")

        for path in files:
            if not path.is_file() or path.stat().st_size == 0:
                row_errors.append(f"missing/empty terminal file {path}")
                continue
            try:
                if path.suffix == ".gz":
                    gzip_test(path)
                elif path.suffix == ".sra":
                    result = subprocess.run(
                        ["vdb-validate", str(path)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        check=False,
                    )
                    if result.returncode:
                        row_errors.append(f"vdb-validate failed for {path}")
                if args.deep:
                    recorded_paths = split(evidence.get("observed_md5", ""))
                    digest = md5(path)
                    if recorded_paths and digest not in recorded_paths:
                        row_errors.append(f"retained MD5 changed for {path}")
            except Exception as exc:
                row_errors.append(f"{path}: {exc}")

        marker = root / "reports/status" / f"{run}.complete"
        if not marker.is_file() or marker.stat().st_size == 0:
            row_errors.append("missing completion marker")
        errors.extend(f"{run}: {message}" for message in row_errors)
        report_rows.append(
            {
                "gse": source["gse"],
                "gsm": gsm,
                "srr": run,
                "source": source["selected_source"],
                "provenance": source["selected_provenance"],
                "final_product": product,
                "expected_spots": expected_spots,
                "observed_r1": evidence.get("observed_r1", ""),
                "observed_r2": evidence.get("observed_r2", ""),
                "status": "FAIL" if row_errors else "PASS",
                "message": "; ".join(row_errors),
            }
        )

    partials = [
        path
        for path in root.rglob("*")
        if path.is_file()
        and (path.name.endswith(".part") or path.name.endswith(".aria2") or path.name.endswith(".tmp"))
    ]
    if partials and len(observed) == len(expected_runs):
        errors.extend(f"residual partial: {path}" for path in partials)

    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_suffix(output.suffix + ".tmp")
    fields = [
        "gse",
        "gsm",
        "srr",
        "source",
        "provenance",
        "final_product",
        "expected_spots",
        "observed_r1",
        "observed_r2",
        "status",
        "message",
    ]
    with temp.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(report_rows)
    temp.replace(output)
    passed = sum(row["status"] == "PASS" for row in report_rows)
    print(
        f"AUDIT expected_runs={len(expected_runs)} observed={len(observed)} "
        f"passed={passed} errors={len(errors)} report={output}"
    )
    for error in errors:
        print(f"ERROR {error}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
