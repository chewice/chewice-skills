#!/usr/bin/env python3
"""Resolve GSE-level raw/temporary/processed paths and storage policy."""

from __future__ import annotations

import argparse
import csv
import os
import re
from pathlib import Path

STORAGE_POLICY_FIELDS = [
    "gse",
    "assay_type",
    "raw_file_type",
    "retain_raw_files",
    "storage_mode",
    "validation_status",
    "deletion_status",
    "deletion_time",
]
ASSAY_TYPES = {
    "",
    "pending",
    "RNA-seq",
    "ATAC-seq",
    "ChIP-seq",
    "miRNA-seq",
    "sequencing",
    "microarray",
    "methylation",
}
RAW_FILE_TYPES = {"", "pending", "FASTQ", "SRA", "CEL", "IDAT"}
RAW_SUBDIRS = {
    "FASTQ": "fastq",
    "SRA": "sra",
    "CEL": "CEL",
    "IDAT": "IDAT",
}
CONVERSION_PROVENANCE_FIELDS = [
    "gse",
    "gsm",
    "tool",
    "tool_version",
    "input_fastq",
    "output_matrix",
    "validated_at",
]
DELETION_LOG_FIELDS = [
    "gse",
    "gsm",
    "srr",
    "path",
    "bytes",
    "md5",
    "validation_report",
    "deleted_at",
]
RETAIN_VALUES = {"true", "false"}
STORAGE_MODES = {"retain", "delete_after_validation"}
VALIDATION_STATUSES = {
    "pending",
    "conversion_pending",
    "validated",
    "failed",
    "not_applicable",
}
DELETION_STATUSES = {"not_applicable", "pending", "deleted", "blocked"}
GSM_RE = re.compile(r"^GSM\d+$")


class StoragePolicyError(ValueError):
    """Invalid or missing storage policy."""


def read_tsv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def write_tsv_atomic(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    with temp.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            delimiter="\t",
            lineterminator="\n",
            extrasaction="ignore",
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)


def storage_policy_path(root: Path) -> Path:
    return root / "metadata/storage_policy.tsv"


def conversion_provenance_path(root: Path) -> Path:
    return root / "reports/conversion_provenance.tsv"


def deletion_log_path(root: Path) -> Path:
    return root / "reports/storage_deletion_log.tsv"


def coerce_retain_flag(row: dict[str, str]) -> str:
    raw = (
        row.get("retain_raw_files")
        or row.get("retain_raw_fastq")
        or ""
    ).rstrip("\r").strip().lower()
    if raw in {"true", "1", "yes"}:
        return "true"
    if raw in {"false", "0", "no"}:
        return "false"
    raise StoragePolicyError(
        f"invalid retain_raw_files={row.get('retain_raw_files') or row.get('retain_raw_fastq')!r}"
    )


def normalize_policy(row: dict[str, str]) -> dict[str, str]:
    normalized = {field: row.get(field, "").rstrip("\r").strip() for field in STORAGE_POLICY_FIELDS}
    normalized["retain_raw_files"] = coerce_retain_flag(row)
    if not normalized["gse"]:
        raise StoragePolicyError("storage_policy.tsv 缺少 gse")
    assay = normalized["assay_type"]
    raw_type = normalized["raw_file_type"]
    if assay not in ASSAY_TYPES:
        raise StoragePolicyError(f"invalid assay_type={assay!r}")
    if raw_type not in RAW_FILE_TYPES:
        raise StoragePolicyError(f"invalid raw_file_type={raw_type!r}")
    expected_mode = (
        "retain" if normalized["retain_raw_files"] == "true" else "delete_after_validation"
    )
    if normalized["storage_mode"] not in STORAGE_MODES:
        raise StoragePolicyError(f"invalid storage_mode={normalized['storage_mode']!r}")
    if normalized["storage_mode"] != expected_mode:
        raise StoragePolicyError(
            "retain_raw_files 与 storage_mode 不一致："
            f"{normalized['retain_raw_files']} / {normalized['storage_mode']}"
        )
    if normalized["validation_status"] not in VALIDATION_STATUSES:
        raise StoragePolicyError(
            f"invalid validation_status={normalized['validation_status']!r}"
        )
    if normalized["deletion_status"] not in DELETION_STATUSES:
        raise StoragePolicyError(
            f"invalid deletion_status={normalized['deletion_status']!r}"
        )
    if normalized["retain_raw_files"] == "true":
        if normalized["deletion_status"] != "not_applicable":
            raise StoragePolicyError("Mode A 的 deletion_status 必须是 not_applicable")
    else:
        if normalized["deletion_status"] == "not_applicable":
            raise StoragePolicyError("Mode B 不得使用 deletion_status=not_applicable")
    return normalized


def default_policy(
    gse: str,
    retain_raw_files: bool,
    assay_type: str = "",
    raw_file_type: str = "",
) -> dict[str, str]:
    if assay_type not in ASSAY_TYPES:
        raise StoragePolicyError(f"invalid assay_type={assay_type!r}")
    if raw_file_type not in RAW_FILE_TYPES:
        raise StoragePolicyError(f"invalid raw_file_type={raw_file_type!r}")
    if retain_raw_files:
        return {
            "gse": gse,
            "assay_type": assay_type,
            "raw_file_type": raw_file_type,
            "retain_raw_files": "true",
            "storage_mode": "retain",
            "validation_status": "not_applicable",
            "deletion_status": "not_applicable",
            "deletion_time": "",
        }
    return {
        "gse": gse,
        "assay_type": assay_type,
        "raw_file_type": raw_file_type,
        "retain_raw_files": "false",
        "storage_mode": "delete_after_validation",
        "validation_status": "conversion_pending",
        "deletion_status": "pending",
        "deletion_time": "",
    }


def read_storage_policy(root: Path, required: bool = True) -> dict[str, str] | None:
    path = storage_policy_path(root)
    rows = read_tsv(path)
    if not rows:
        if required:
            raise StoragePolicyError(f"缺少 {path.relative_to(root)}")
        return None
    if len(rows) != 1:
        raise StoragePolicyError("storage_policy.tsv 必须恰好一行")
    return normalize_policy(rows[0])


def write_storage_policy(root: Path, row: dict[str, str]) -> dict[str, str]:
    normalized = normalize_policy(row)
    write_tsv_atomic(storage_policy_path(root), STORAGE_POLICY_FIELDS, [normalized])
    return normalized


def retain_raw_files(root: Path, required: bool = True) -> bool | None:
    policy = read_storage_policy(root, required=required)
    if policy is None:
        return None
    return policy["retain_raw_files"] == "true"


def retain_raw_fastq(root: Path, required: bool = True) -> bool | None:
    return retain_raw_files(root, required=required)


def is_array_raw(policy: dict[str, str] | None) -> bool:
    if not policy:
        return False
    return policy.get("raw_file_type", "") in {"CEL", "IDAT"}


def deletion_completed(root: Path) -> bool:
    policy = read_storage_policy(root, required=False)
    return bool(policy and policy["deletion_status"] == "deleted")


def raw_dir(root: Path, gsm: str) -> Path:
    return root / "raw" / gsm


def temporary_dir(root: Path, gsm: str) -> Path:
    return root / "temporary" / gsm


def processed_dir(root: Path, gsm: str) -> Path:
    return root / "processed" / gsm


def work_dir(root: Path, gsm: str, srr: str) -> Path:
    return temporary_dir(root, gsm) / "work" / srr


def download_manifest_path(root: Path, gsm: str) -> Path:
    current = root / "metadata/download_manifests" / f"{gsm}.tsv"
    if current.is_file():
        return current
    legacy = root / gsm / "download_manifest.tsv"
    return legacy if legacy.is_file() else current


def iter_download_manifests(root: Path) -> list[Path]:
    paths = sorted((root / "metadata/download_manifests").glob("GSM*.tsv"))
    if paths:
        return paths
    return sorted(root.glob("GSM*/download_manifest.tsv"))


def published_raw_dir(
    root: Path,
    gsm: str,
    file_type: str,
    retain: bool | None = None,
) -> Path:
    kind = file_type.upper()
    subdir = RAW_SUBDIRS.get(kind, kind.lower() or "assay_files")
    if retain is None:
        retain = retain_raw_files(root, required=False)
    if retain is False:
        return temporary_dir(root, gsm) / subdir
    current = raw_dir(root, gsm) / subdir
    if current.exists() or retain is True or kind != "FASTQ":
        return current
    legacy = root / gsm / subdir
    return legacy if legacy.exists() else current


def published_fastq_dir(root: Path, gsm: str, retain: bool | None = None) -> Path:
    return published_raw_dir(root, gsm, "FASTQ", retain)


def published_sra_dir(root: Path, gsm: str) -> Path:
    current = raw_dir(root, gsm) / "sra"
    if current.exists():
        return current
    legacy = root / gsm / "sra"
    return legacy if legacy.exists() else current


def matrix_dir(root: Path, gsm: str, gse: str = "") -> Path:
    current = processed_dir(root, gsm) / "matrix_10x"
    if current.exists():
        return current
    sample = root / gsm / "matrix_10x"
    if sample.exists():
        return sample
    if gse:
        nested = root / "matrix_10x" / gse / gsm
        if nested.exists():
            return nested
    return current


def velocity_dir(root: Path, gsm: str, gse: str = "") -> Path:
    current = processed_dir(root, gsm) / "velocity"
    if current.exists():
        return current
    sample = root / gsm / "velocity"
    if sample.exists():
        return sample
    if gse:
        nested = root / "velocity" / gse / gsm
        if nested.exists():
            return nested
    return current


def loom_path(root: Path, gsm: str, gse: str = "") -> Path:
    directory = velocity_dir(root, gsm, gse)
    current = directory / f"{gsm}.loom"
    if current.exists():
        return current
    if gse:
        nested = root / "velocity" / gse / f"{gsm}.loom"
        if nested.exists():
            return nested
    return current


def locate_outputs(root: Path, gse: str, gsm: str) -> tuple[Path, Path, Path]:
    return matrix_dir(root, gsm, gse), velocity_dir(root, gsm, gse), loom_path(root, gsm, gse)


def fastq_name(srr: str, role: str) -> str:
    return f"{srr}_{role}.fastq.gz"


def published_fastq_files(
    root: Path,
    gsm: str,
    srr: str,
    layout: str,
    retain: bool | None = None,
) -> list[Path]:
    directory = published_fastq_dir(root, gsm, retain)
    files = [directory / fastq_name(srr, "R1")]
    if layout.upper() == "PAIRED":
        files.append(directory / fastq_name(srr, "R2"))
    return files


def list_temporary_raw(root: Path) -> list[Path]:
    files: list[Path] = []
    patterns = (
        "GSM*/fastq/*",
        "GSM*/CEL/*",
        "GSM*/IDAT/*",
        "GSM*/sra/*",
    )
    for pattern in patterns:
        for path in sorted((root / "temporary").glob(pattern)):
            if path.is_file() and not path.name.endswith((".part", ".aria2", ".json")):
                files.append(path)
    return files


def list_temporary_fastq(root: Path) -> list[Path]:
    return [
        path
        for path in list_temporary_raw(root)
        if path.parent.name == "fastq" and path.name.endswith(".fastq.gz")
    ]


def list_published_raw(root: Path) -> list[Path]:
    files: list[Path] = []
    patterns = (
        "GSM*/fastq/*.fastq.gz",
        "GSM*/sra/*.sra",
        "GSM*/CEL/*",
        "GSM*/IDAT/*",
    )
    for pattern in patterns:
        for path in sorted((root / "raw").glob(pattern)):
            if path.is_file():
                files.append(path)
    return files


def infer_gsm(path: Path, root: Path) -> str:
    for part in path.relative_to(root).parts:
        if GSM_RE.fullmatch(part):
            return part
    return ""


def infer_srr(path: Path) -> str:
    name = path.name
    for suffix in ("_R1.fastq.gz", "_R2.fastq.gz", "_I1.fastq.gz", "_I2.fastq.gz"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return path.stem


def print_dirs(root: Path, gsm: str, srr: str) -> None:
    policy = read_storage_policy(root)
    retain = policy["retain_raw_files"] == "true"
    mapping = {
        "RETAIN_RAW": "true" if retain else "false",
        "STORAGE_MODE": policy["storage_mode"],
        "FASTQ_DIR": str(published_fastq_dir(root, gsm, retain)),
        "SRA_DIR": str(published_sra_dir(root, gsm)),
        "WORK_DIR": str(work_dir(root, gsm, srr)),
        "DOWNLOAD_MANIFEST": str(root / "metadata/download_manifests" / f"{gsm}.tsv"),
        "MANIFEST_LOCK": str(root / "metadata/download_manifests" / f"{gsm}.lock"),
        "MATRIX_DIR": str(processed_dir(root, gsm) / "matrix_10x"),
        "VELOCITY_DIR": str(processed_dir(root, gsm) / "velocity"),
    }
    for key, value in mapping.items():
        print(f"{key}={value}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Print GSE project layout directories")
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--gsm", required=True)
    parser.add_argument("--srr", required=True)
    parser.add_argument("--print-dirs", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    if not args.print_dirs:
        raise SystemExit("Use --print-dirs")
    try:
        print_dirs(root, args.gsm, args.srr)
    except StoragePolicyError as exc:
        raise SystemExit(str(exc)) from exc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
