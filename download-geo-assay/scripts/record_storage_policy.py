#!/usr/bin/env python3
"""Record the user-confirmed per-assay raw-data storage policy for a GSE project."""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from project_layout import (  # noqa: E402
    FINAL_PRODUCTS,
    MODALITIES,
    SOURCE_PREFERENCES,
    STORAGE_POLICY_FIELDS,
    StoragePolicyError,
    default_policy,
    policy_key,
    read_storage_policies,
    write_storage_policy,
)
from capabilities import CapabilityError, assay_capability  # noqa: E402


def parse_retain(args: argparse.Namespace) -> bool:
    retain = args.retain_raw_files or args.retain_raw_fastq
    if retain is None:
        raise SystemExit("必须指定 --retain-raw-files true|false，不允许默认")
    return retain == "true"


def update_config(root: Path, updates: dict[str, str]) -> None:
    path = root / "metadata/acquisition_config.tsv"
    rows: list[dict[str, str]] = []
    if path.is_file():
        with path.open(newline="") as handle:
            rows = list(csv.DictReader(handle, delimiter="\t"))
    existing = {row.get("key", ""): row for row in rows}
    for key, value in updates.items():
        if key in existing:
            existing[key]["value"] = value
        else:
            row = {"key": key, "value": value}
            rows.append(row)
            existing[key] = row
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
    if len(policies) == 1 and policies[0]["gse"] == gse and not assay_type and not modality:
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
    parser.add_argument("--final-product", choices=tuple(sorted(FINAL_PRODUCTS)))
    parser.add_argument("--source-preference", choices=tuple(sorted(SOURCE_PREFERENCES)))
    parser.add_argument("--allow-sra-lite", choices=("true", "false"))
    parser.add_argument("--authorize-auto-recovery", choices=("true", "false"))
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
    parser.add_argument("--max-project-gib", type=int)
    args = parser.parse_args()
    root = args.root.resolve()
    gse = args.gse.upper()
    retain = parse_retain(args)
    config_updates: dict[str, str] = {}
    for value, key, flag in (
        (args.max_temporary_gib, "max_temporary_bytes", "--max-temporary-gib"),
        (args.max_project_gib, "max_project_bytes", "--max-project-gib"),
    ):
        if value is not None:
            if value <= 0:
                raise SystemExit(f"{flag} 必须为正整数")
            config_updates[key] = str(value * 1024**3)
    if args.authorize_auto_recovery is not None:
        config_updates["auto_restart"] = args.authorize_auto_recovery
    try:
        policies = read_storage_policies(root, required=False)
    except StoragePolicyError as exc:
        raise SystemExit(str(exc)) from exc
    existing = matching_existing(policies, gse, args.assay_type, args.modality)
    assay_type = args.assay_type or (existing["assay_type"] if existing else "")
    raw_file_type = args.raw_file_type or (existing["raw_file_type"] if existing else "")
    modality = args.modality or (existing["modality"] if existing else "")
    final_product = args.final_product or (existing["final_product"] if existing else "pending")
    source_preference = args.source_preference or (
        existing["source_preference"] if existing else "auto"
    )
    allow_sra_lite = (
        args.allow_sra_lite
        if args.allow_sra_lite is not None
        else (existing["allow_sra_lite"] if existing else "false")
    )
    if not retain:
        if final_product in {"pending", "fastq", "sra", "CEL", "IDAT"}:
            raise SystemExit("删除 raw 需要明确的可审计转换产品，不能使用 pending/raw 产品")
        if modality and modality != "pending":
            try:
                _, capability = assay_capability(modality, root)
            except CapabilityError as exc:
                raise SystemExit(str(exc)) from exc
            allowed = set(capability.get("standard_products", [])) | set(
                capability.get("optional_products", [])
            )
            if capability.get("workflow") == "raw_only" or final_product not in allowed:
                raise SystemExit(
                    f"modality={modality} 不允许以 final_product={final_product} 删除 raw"
                )
    confirmed_at = datetime.now(timezone.utc).isoformat()
    row = default_policy(
        gse,
        retain,
        assay_type=assay_type,
        raw_file_type=raw_file_type,
        modality=modality,
        final_product=final_product,
        source_preference=source_preference,
        allow_sra_lite=allow_sra_lite == "true",
        confirmed_at=confirmed_at,
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
    config_updates.update(
        {
            "final_product": final_product,
            "retain_raw_files": "true" if retain else "false",
            "source_preference": source_preference,
            "allow_sra_lite": allow_sra_lite,
        }
    )
    if config_updates:
        update_config(root, config_updates)
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
