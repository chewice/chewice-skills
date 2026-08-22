#!/usr/bin/env python3
"""Record the user-confirmed raw-data storage policy for a GSE project."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from project_layout import (  # noqa: E402
    STORAGE_POLICY_FIELDS,
    StoragePolicyError,
    default_policy,
    read_storage_policy,
    write_storage_policy,
)


def parse_retain(args: argparse.Namespace) -> bool:
    retain = args.retain_raw_files or args.retain_raw_fastq
    if retain is None:
        raise SystemExit("必须指定 --retain-raw-files true|false，不允许默认")
    return retain == "true"


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
        "microarray",
        "methylation",
    ))
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
    args = parser.parse_args()
    root = args.root.resolve()
    gse = args.gse.upper()
    retain = parse_retain(args)
    try:
        existing = read_storage_policy(root, required=False)
    except StoragePolicyError as exc:
        raise SystemExit(str(exc)) from exc
    assay_type = args.assay_type or (existing["assay_type"] if existing else "")
    raw_file_type = args.raw_file_type or (existing["raw_file_type"] if existing else "")
    row = default_policy(gse, retain, assay_type=assay_type, raw_file_type=raw_file_type)
    if existing and existing["gse"] == gse:
        row["validation_status"] = existing["validation_status"]
        row["deletion_status"] = existing["deletion_status"]
        row["deletion_time"] = existing["deletion_time"]
        if not args.assay_type:
            row["assay_type"] = existing["assay_type"]
        if not args.raw_file_type:
            row["raw_file_type"] = existing["raw_file_type"]
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
