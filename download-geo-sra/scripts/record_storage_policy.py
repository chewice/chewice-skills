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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--gse", required=True)
    parser.add_argument(
        "--retain-raw-fastq",
        required=True,
        choices=("true", "false"),
    )
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
    retain = args.retain_raw_fastq == "true"
    try:
        existing = read_storage_policy(root, required=False)
    except StoragePolicyError as exc:
        raise SystemExit(str(exc)) from exc
    row = default_policy(gse, retain)
    if existing and existing["gse"] == gse:
        row["validation_status"] = existing["validation_status"]
        row["deletion_status"] = existing["deletion_status"]
        row["deletion_time"] = existing["deletion_time"]
        if existing["retain_raw_fastq"] != row["retain_raw_fastq"] and (
            existing["deletion_status"] == "deleted"
        ):
            raise SystemExit("不得在 FASTQ 已删除后改写 retain_raw_fastq")
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
