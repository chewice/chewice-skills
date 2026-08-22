#!/usr/bin/env python3
"""Select a per-run source using fixed NGDC -> ENA -> NCBI priority."""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse


FIELDS = [
    "gse",
    "gsm",
    "srx",
    "srr",
    "run_alias",
    "lane",
    "library_layout",
    "read_structure",
    "expected_spots",
    "cb_length",
    "umi_length",
    "ngdc_status",
    "ngdc_run_page",
    "ngdc_url",
    "ngdc_bytes",
    "selected_source",
    "selected_provenance",
    "selected_urls",
    "selected_bytes",
    "selected_md5",
    "read_roles",
    "final_product",
    "fallback_reason",
]


def refresh_report_from_output(output: Path) -> None:
    reporter = Path(__file__).with_name("build_report.py")
    root = output.resolve().parent.parent
    if output.parent.name == "metadata" and reporter.is_file():
        subprocess.run(
            [sys.executable, str(reporter), "--root", str(root)],
            check=False,
        )


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def split(value: str) -> list[str]:
    return [item.strip() for item in value.rstrip("\r").split(";") if item.strip()]


def https_url(value: str) -> str:
    if re.match(r"^https?://", value):
        return value
    return f"https://{value.lstrip('/')}"


def infer_roles(urls: list[str], layout: str) -> list[str]:
    roles: list[str] = []
    for url in urls:
        name = Path(urlparse(url).path).name.upper()
        role = "OTHER"
        for candidate in ("R1", "R2", "I1", "I2"):
            if re.search(rf"(?:^|[_.-]){candidate}(?:[_.-]|$)", name):
                role = candidate
                break
        if role == "OTHER":
            match = re.search(r"_([12])\.F(?:AST)?Q(?:\.GZ)?$", name)
            if match:
                role = f"R{match.group(1)}"
        roles.append(role)
    if layout.upper() == "SINGLE" and len(urls) == 1 and roles == ["OTHER"]:
        roles = ["R1"]
    if layout.upper() == "PAIRED" and len(urls) == 2 and set(roles) == {"OTHER"}:
        roles = ["R1", "R2"]
    return roles


def fallback_reason(status: str) -> str:
    return {
        "missing": "ngdc_missing",
        "invalid": "ngdc_size_invalid",
        "unreachable": "ngdc_unreachable_after_3_attempts",
        "not_probed": "ngdc_metadata_conflict",
    }.get(status, "ngdc_no_file_endpoint")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected", required=True, type=Path)
    parser.add_argument("--ngdc", required=True, type=Path)
    parser.add_argument("--ena", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--final-product",
        choices=("fastq", "sra", "matrix_velocity", "matrix_10x", "gene_count_matrix"),
        default="fastq",
    )
    args = parser.parse_args()

    expected = read_tsv(args.expected)
    coverage = {row["srr"]: row for row in read_tsv(args.ngdc)}
    ena = {row["run_accession"].rstrip("\r"): row for row in read_tsv(args.ena)}
    records: list[dict[str, str]] = []
    failures: list[str] = []

    for row in expected:
        run = row["srr"]
        ngdc = coverage.get(run, {"ngdc_status": "not_probed"})
        status = ngdc["ngdc_status"]
        selected_source = ""
        provenance = ""
        urls: list[str] = []
        sizes: list[str] = []
        md5s: list[str] = []
        roles: list[str] = []
        reason = ""

        if status == "available" and ngdc.get("ngdc_url"):
            url = ngdc["ngdc_url"]
            urls = [url]
            sizes = [ngdc.get("ngdc_bytes", "")]
            md5s = [ngdc.get("ngdc_md5", "")]
            if run.startswith("CRR") or ngdc.get("ngdc_file_type") != "sra":
                selected_source = "ngdc_gsa"
                provenance = "GSA_AUTHOR_SUBMITTED"
                roles = infer_roles(urls, row.get("library_layout", ""))
            else:
                selected_source = "ngdc_insdc"
                provenance = "NGDC_MIRROR_SRA"
                roles = ["SRA"]
        else:
            reason = fallback_reason(status)
            ena_row = ena.get(run, {})
            submitted_urls = split(ena_row.get("submitted_ftp", ""))
            submitted_roles = infer_roles(
                submitted_urls, row.get("library_layout", "")
            )
            submitted_fastq = bool(submitted_urls) and all(
                re.search(r"\.F(?:AST)?Q(?:\.GZ)?$", Path(urlparse(url).path).name.upper())
                for url in submitted_urls
            )
            submitted_usable = submitted_fastq and "OTHER" not in submitted_roles

            if submitted_usable:
                selected_source = "ena_submitted"
                provenance = "AUTHOR_SUBMITTED"
                urls = [https_url(url) for url in submitted_urls]
                sizes = split(ena_row.get("submitted_bytes", ""))
                md5s = split(ena_row.get("submitted_md5", ""))
                roles = submitted_roles
            else:
                fastq_urls = split(ena_row.get("fastq_ftp", ""))
                if fastq_urls:
                    file_roles = split(ena_row.get("fastq_file_role", ""))
                    selected_source = (
                        "ena_submitted"
                        if file_roles and all(role == "SUBMITTED_FILE" for role in file_roles)
                        else "ena_fastq"
                    )
                    provenance = (
                        "AUTHOR_SUBMITTED"
                        if selected_source == "ena_submitted"
                        else "ARCHIVE_GENERATED_FASTQ"
                    )
                    urls = [https_url(url) for url in fastq_urls]
                    sizes = split(ena_row.get("fastq_bytes", ""))
                    md5s = split(ena_row.get("fastq_md5", ""))
                    roles = infer_roles(urls, row.get("library_layout", ""))
                else:
                    selected_source = "ncbi_sra"
                    provenance = "ARCHIVE_NORMALIZED_SRA"
                    urls = [run]
                    sizes = split(ena_row.get("sra_bytes", ""))
                    md5s = split(ena_row.get("sra_md5", ""))
                    roles = ["SRA"]

        if not selected_source or not urls:
            failures.append(f"{run}: no usable source")
            continue
        if len(roles) != len(urls) or "OTHER" in roles:
            failures.append(f"{run}: ambiguous read roles {roles}")
            continue
        for values, name in ((sizes, "bytes"), (md5s, "md5")):
            if values and len(values) != len(urls):
                failures.append(
                    f"{run}: {name} array length {len(values)} != URLs {len(urls)}"
                )
        if selected_source in {"ena_submitted", "ena_fastq"}:
            if len(sizes) != len(urls) or len(md5s) != len(urls):
                failures.append(
                    f"{run}: ENA FASTQ selection requires bytes and MD5 for every file"
                )
            if any(not re.fullmatch(r"[0-9a-fA-F]{32}", value) for value in md5s):
                failures.append(f"{run}: ENA FASTQ contains an invalid/missing MD5")
        if selected_source.startswith("ngdc_") and len(sizes) != len(urls):
            failures.append(f"{run}: NGDC selection requires Content-Length")

        records.append(
            {
                "gse": row["gse"],
                "gsm": row["gsm"],
                "srx": row.get("srx", ""),
                "srr": run,
                "run_alias": row.get("run_alias", ""),
                "lane": row.get("lane", ""),
                "library_layout": row.get("library_layout", ""),
                "read_structure": row.get("read_structure", ""),
                "expected_spots": row.get("expected_spots", ""),
                "cb_length": row.get("cb_length", ""),
                "umi_length": row.get("umi_length", ""),
                "ngdc_status": status,
                "ngdc_run_page": ngdc.get("ngdc_run_page", ""),
                "ngdc_url": ngdc.get("ngdc_url", ""),
                "ngdc_bytes": ngdc.get("ngdc_bytes", ""),
                "selected_source": selected_source,
                "selected_provenance": provenance,
                "selected_urls": ";".join(urls),
                "selected_bytes": ";".join(sizes),
                "selected_md5": ";".join(md5s),
                "read_roles": ";".join(roles),
                "final_product": args.final_product,
                "fallback_reason": reason,
            }
        )

    if failures:
        raise SystemExit("\n".join(failures))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temp = args.output.with_suffix(args.output.suffix + ".tmp")
    with temp.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)
    temp.replace(args.output)
    print(f"Wrote {args.output}: {len(records)} runs")
    refresh_report_from_output(args.output)


if __name__ == "__main__":
    main()
