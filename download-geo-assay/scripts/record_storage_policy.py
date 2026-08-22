#!/usr/bin/env python3
"""Record the user-confirmed per-assay raw-data storage policy for a GSE project."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from project_layout import (  # noqa: E402
    MODALITIES,
    STORAGE_POLICY_FIELDS,
    StoragePolicyError,
    default_policy,
    policy_key,
    read_storage_policies,
    write_storage_policy,
)


def parse_retain(args: argparse.Namespace) -> bool:
    retain = args.retain_raw_files or args.retain_raw_fastq
    if retain is None:
        raise SystemExit("必须指定 --retain-raw-files true|false，不允许默认")
    return retain == "true"


def update_quota(root: Path, gib: int) -> None:
    path = root / "metadata/acquisition_config.tsv"
    rows: list[dict[str, str]] = []
    if path.is_file():
        with path.open(newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
    updated = False
    value = str(gib * 1024**3)
    for row in rows:
        if row.get("key") == "max_temporary_bytes":
            row["value"] = value
            updated = True
    if not updated:
        rows.append({"key": "max_temporary_bytes", "value": value})
    fields = ["key", "value"]
    temp = path.with_name(path.name + ".tmp")
    path.parent.mkdir(parents=True, exist_ok=True)
    with temp.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})
    temp.replace(path)


def matching_existing(
    policies: list[dict[str, str]],
    gse: str,
    assay_type: str,
    modality: str,
) -> dict[str, str] | None:
    for row in policies:
        if policy_key(row) == (gse, assay_type, modality):
            return row
    for row in policies:
        if row["gse"] == gse and row["assay_type"] == assay_type and not modality:
            return row
    if len(policies) == 1 and policies[0]["gse"] == gse and not policies[0]["assay_type"]:
        return policies[0]
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--gse", required=True)
    parser.add_argument("--retain-raw-files", choices=("true", "false"))
    parser.add_argument(
        "--retain-raw-fastq",
        choices=("true", "false"),
        help="兼容旧参数；等价于 --retain-raw-files",
    )
    parser.add_argument("--assay-type", default="", choices=(
        "",
        "pending",
        "RNA-seq",
        "ATAC-seq",
        "ChIP-seq",
        "miRNA-seq",
        "sequencing",
        "microarray",
        "methylation",
    ))
    parser.add_argument("--modality", default="", choices=tuple(sorted(MODALITIES)))
    parser.add_argument("--raw-file-type", default="", choices=(
        "",
        "pending",
        "FASTQ",
        "SRA",
        "CEL",
        "IDAT",
    ))
    parser.add_argument("--validation-status", choices=(
        "pending",
        "conversion_pending",
        "validated",
        "failed",
        "not_applicable",
    ))
    parser.add_argument("--deletion-status", choices=(
        "not_applicable",
        "pending",
        "deleted",
        "blocked",
    ))
    parser.add_argument("--deletion-time", default="")
    parser.add_argument("--max-temporary-gib", type=int)
    args = parser.parse_args()
    root = args.root.resolve()
    gse = args.gse.upper()
    retain = parse_retain(args)
    if args.max_temporary_gib is not None:
        if args.max_temporary_gib <= 0:
            raise SystemExit("--max-temporary-gib 必须为正整数")
        update_quota(root, args.max_temporary_gib)
    try:
        policies = read_storage_policies(root, required=False)
    except StoragePolicyError as exc:
        raise SystemExit(str(exc)) from exc
    existing = matching_existing(policies, gse, args.assay_type, args.modality)
    assay_type = args.assay_type or (existing["assay_type"] if existing else "")
    raw_file_type = args.raw_file_type or (existing["raw_file_type"] if existing else "")
    modality = args.modality or (existing["modality"] if existing else "")
    row = default_policy(
        gse,
        retain,
        assay_type=assay_type,
        raw_file_type=raw_file_type,
        modality=modality,
    )
    if existing and existing["gse"] == gse:
        row["validation_status"] = existing["validation_status"]
        row["deletion_status"] = existing["deletion_status"]
        row["deletion_time"] = existing["deletion_time"]
        if existing["retain_raw_files"] != row["retain_raw_files"] and (
            existing["deletion_status"] == "deleted"
        ):
            raise SystemExit("不得在 raw files 已删除后改写 retain_raw_files")
    if args.validation_status:
        row["validation_status"] = args.validation_status
    if args.deletion_status:
        row["deletion_status"] = args.deletion_status
    if args.deletion_time:
        row["deletion_time"] = args.deletion_time
    if retain:
        row["deletion_status"] = "not_applicable"
        row["deletion_time"] = ""
        if not args.validation_status:
            row["validation_status"] = existing["validation_status"] if existing else "not_applicable"
    try:
        written = write_storage_policy(root, row)
    except StoragePolicyError as exc:
        raise SystemExit(str(exc)) from exc
    print(
        "STORAGE_POLICY "
        + " ".join(f"{field}={written[field]}" for field in STORAGE_POLICY_FIELDS)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
