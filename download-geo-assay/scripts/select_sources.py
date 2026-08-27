#!/usr/bin/env python3
"""Select object class first, then a transport endpoint, per run."""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from capabilities import (  # noqa: E402
    CapabilityError,
    classify_source,
    load_source_capabilities,
    source_capability,
)
from project_layout import policy_for_gsm, read_config  # noqa: E402

FIELDS = [
    "gse", "gsm", "srx", "srr", "run_alias", "lane", "library_layout",
    "read_structure", "expected_spots", "cb_length", "umi_length",
    "ngdc_status", "ngdc_run_page", "ngdc_url", "ngdc_bytes",
    "selected_source", "selected_provenance", "object_class", "quality_class",
    "transport_endpoint", "selected_urls", "selected_bytes", "selected_md5",
    "read_roles", "final_product", "selection_evidence", "selection_reason",
    "fallback_reason",
]


def refresh_report_from_output(output: Path) -> None:
    reporter = Path(__file__).with_name("build_report.py")
    root = output.resolve().parent.parent
    if output.parent.name == "metadata" and reporter.is_file():
        subprocess.run([sys.executable, str(reporter), "--root", str(root)], check=False)


def read_tsv(path: Path | None) -> list[dict[str, str]]:
    if path is None or not path.is_file():
        return []
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


def provider(source: str) -> str:
    return source.split("_", 1)[0]


def make_candidate(
    source: str,
    provenance: str,
    urls: list[str],
    sizes: list[str],
    md5s: list[str],
    roles: list[str],
    evidence: str,
    root: Path,
) -> dict[str, object]:
    object_class, quality_class, object_info = classify_source(source, provenance, root)
    source_info = source_capability(source, root)
    return {
        "source": source,
        "provenance": provenance,
        "object_class": object_class,
        "quality_class": quality_class,
        "urls": urls,
        "sizes": sizes,
        "md5s": md5s,
        "roles": roles,
        "evidence": evidence,
        "fidelity_rank": int(object_info.get("fidelity_rank", 999)),
        "transport_rank": int(source_info.get("auto_transport_rank", 999)),
        "transport": str(source_info.get("transport", "")),
    }


def ena_candidates(row: dict[str, str], expected: dict[str, str], root: Path) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    layout = expected.get("library_layout", "")
    submitted_urls = split(row.get("submitted_ftp", ""))
    submitted_roles = infer_roles(submitted_urls, layout)
    submitted_fastq = bool(submitted_urls) and all(
        re.search(r"\.F(?:AST)?Q(?:\.GZ)?$", Path(urlparse(url).path).name.upper())
        for url in submitted_urls
    )
    if submitted_fastq and "OTHER" not in submitted_roles:
        candidates.append(
            make_candidate(
                "ena_submitted", "AUTHOR_SUBMITTED",
                [https_url(url) for url in submitted_urls],
                split(row.get("submitted_bytes", "")), split(row.get("submitted_md5", "")),
                submitted_roles, "ENA submitted file metadata", root,
            )
        )
    fastq_urls = split(row.get("fastq_ftp", ""))
    if fastq_urls:
        file_roles = split(row.get("fastq_file_role", ""))
        source = (
            "ena_submitted"
            if file_roles and all(role == "SUBMITTED_FILE" for role in file_roles)
            else "ena_fastq"
        )
        provenance = "AUTHOR_SUBMITTED" if source == "ena_submitted" else "ARCHIVE_GENERATED_FASTQ"
        candidate = make_candidate(
            source, provenance, [https_url(url) for url in fastq_urls],
            split(row.get("fastq_bytes", "")), split(row.get("fastq_md5", "")),
            infer_roles(fastq_urls, layout), f"ENA {'submitted' if source == 'ena_submitted' else 'generated'} FASTQ metadata", root,
        )
        signature = (candidate["source"], tuple(candidate["urls"]))
        if all((item["source"], tuple(item["urls"])) != signature for item in candidates):
            candidates.append(candidate)
    return candidates


def preference_for_gsm(root: Path, gsm: str, explicit: str | None) -> str:
    if explicit:
        return explicit
    policy = policy_for_gsm(root, gsm, required=False)
    if policy:
        return policy.get("source_preference", "auto")
    return read_config(root).get("source_preference", "auto") or "auto"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected", required=True, type=Path)
    parser.add_argument("--ngdc", required=True, type=Path)
    parser.add_argument("--ena", required=True, type=Path)
    parser.add_argument("--ncbi", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--root", type=Path)
    parser.add_argument("--source-preference", choices=("auto", "ngdc", "ena", "ncbi"))
    parser.add_argument("--allow-sra-lite", action="store_true")
    parser.add_argument(
        "--final-product",
        choices=("pending", "fastq", "sra", "matrix_velocity", "matrix_10x", "gene_count_matrix"),
    )
    args = parser.parse_args()
    root = (args.root or args.output.resolve().parent.parent).resolve()
    load_source_capabilities(root)  # fail before producing a manifest

    expected = read_tsv(args.expected)
    coverage = {row["srr"]: row for row in read_tsv(args.ngdc)}
    ena = {row["run_accession"].rstrip("\r"): row for row in read_tsv(args.ena)}
    ncbi: dict[str, list[dict[str, str]]] = {}
    for row in read_tsv(args.ncbi):
        ncbi.setdefault(row.get("srr", ""), []).append(row)
    records: list[dict[str, str]] = []
    failures: list[str] = []

    for row in expected:
        run = row["srr"]
        ngdc = coverage.get(run, {"ngdc_status": "not_probed"})
        status = ngdc.get("ngdc_status", "not_probed")
        candidates: list[dict[str, object]] = []
        if status == "available" and ngdc.get("ngdc_url"):
            url = ngdc["ngdc_url"]
            if run.startswith("CRR") or ngdc.get("ngdc_file_type") != "sra":
                candidates.append(
                    make_candidate(
                        "ngdc_gsa", "GSA_AUTHOR_SUBMITTED", [url],
                        [ngdc.get("ngdc_bytes", "")], [ngdc.get("ngdc_md5", "")],
                        infer_roles([url], row.get("library_layout", "")),
                        "NGDC run/file probe", root,
                    )
                )
            else:
                candidates.append(
                    make_candidate(
                        "ngdc_insdc", "NGDC_MIRROR_SRA", [url],
                        [ngdc.get("ngdc_bytes", "")], [ngdc.get("ngdc_md5", "")],
                        ["SRA"], "NGDC INSDC mirror probe", root,
                    )
                )
        candidates.extend(ena_candidates(ena.get(run, {}), row, root))
        for ncbi_row in ncbi.get(run, []):
            if ncbi_row.get("status") != "available":
                continue
            candidates.append(
                make_candidate(
                    ncbi_row["source"], ncbi_row["provenance"],
                    split(ncbi_row.get("url", "")), split(ncbi_row.get("bytes", "")),
                    split(ncbi_row.get("md5", "")), split(ncbi_row.get("roles", "SRA")),
                    ncbi_row.get("evidence", "NCBI object probe"), root,
                )
            )
        # Resolver access is always a candidate, but actual Lite discovery is reclassified at download.
        candidates.append(
            make_candidate(
                "ncbi_sra", "ARCHIVE_NORMALIZED_SRA", [run],
                split(ena.get(run, {}).get("sra_bytes", "")),
                split(ena.get(run, {}).get("sra_md5", "")), ["SRA"],
                "NCBI SRA resolver; actual object class verified after prefetch", root,
            )
        )

        preference = preference_for_gsm(root, row["gsm"], args.source_preference)
        policy = policy_for_gsm(root, row["gsm"], required=False)
        final_product = (
            args.final_product
            or (policy.get("final_product") if policy else "")
            or read_config(root).get("final_product", "")
            or "pending"
        )
        eligible = [item for item in candidates if preference == "auto" or provider(str(item["source"])) == preference]
        allow_lite = args.allow_sra_lite or bool(
            policy and policy.get("allow_sra_lite") == "true"
        ) or read_config(root).get("allow_sra_lite") == "true"
        if not allow_lite:
            eligible = [item for item in eligible if item["object_class"] != "SRA_LITE"]
        if not eligible:
            failures.append(f"{run}: no usable source for explicit preference={preference}")
            continue
        selected = min(eligible, key=lambda item: (item["fidelity_rank"], item["transport_rank"]))
        urls = list(selected["urls"])
        sizes = list(selected["sizes"])
        md5s = list(selected["md5s"])
        roles = list(selected["roles"])
        source = str(selected["source"])
        if not urls or len(roles) != len(urls) or "OTHER" in roles:
            failures.append(f"{run}: ambiguous URL/read roles {roles}")
            continue
        for values, name in ((sizes, "bytes"), (md5s, "md5")):
            if values and len(values) != len(urls):
                failures.append(f"{run}: {name} array length {len(values)} != URLs {len(urls)}")
        if source in {"ena_submitted", "ena_fastq"}:
            if len(sizes) != len(urls) or len(md5s) != len(urls):
                failures.append(f"{run}: ENA FASTQ requires bytes and MD5 for every file")
            if any(not re.fullmatch(r"[0-9a-fA-F]{32}", value) for value in md5s):
                failures.append(f"{run}: ENA FASTQ contains invalid/missing MD5")
        if source.startswith("ngdc_") and len(sizes) != len(urls):
            failures.append(f"{run}: NGDC selection requires Content-Length")

        reason = (
            f"explicit source preference={preference}"
            if preference != "auto"
            else f"best fidelity rank={selected['fidelity_rank']}; transport rank={selected['transport_rank']}"
        )
        legacy_fallback = "" if source.startswith("ngdc_") else f"ngdc_{status}"
        records.append(
            {
                **{field: row.get(field, "") for field in FIELDS},
                "ngdc_status": status,
                "ngdc_run_page": ngdc.get("ngdc_run_page", ""),
                "ngdc_url": ngdc.get("ngdc_url", ""),
                "ngdc_bytes": ngdc.get("ngdc_bytes", ""),
                "selected_source": source,
                "selected_provenance": str(selected["provenance"]),
                "object_class": str(selected["object_class"]),
                "quality_class": str(selected["quality_class"]),
                "transport_endpoint": str(selected["transport"]),
                "selected_urls": ";".join(urls),
                "selected_bytes": ";".join(sizes),
                "selected_md5": ";".join(md5s),
                "read_roles": ";".join(roles),
                "final_product": final_product,
                "selection_evidence": str(selected["evidence"]),
                "selection_reason": reason,
                "fallback_reason": legacy_fallback,
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
