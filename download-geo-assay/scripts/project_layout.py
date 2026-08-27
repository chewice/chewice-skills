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
    "modality",
    "raw_file_type",
    "retain_raw_files",
    "storage_mode",
    "final_product",
    "source_preference",
    "allow_sra_lite",
    "confirmed_at",
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
MODALITIES = {
    "",
    "pending",
    "bulk_rnaseq",
    "scRNAseq",
    "snRNAseq",
    "atac",
    "chip",
    "mirna",
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
RELEASE_FIELDS = [
    "gse",
    "gsm",
    "unit_id",
    "assay_type",
    "modality",
    "member_runs",
    "final_product",
    "policy_confirmed_at",
    "download_status",
    "conversion_status",
    "processed_audit",
    "release_status",
    "candidate_paths",
    "candidate_bytes",
    "candidate_md5",
    "released_at",
    "message",
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
FINAL_PRODUCTS = {
    "pending",
    "fastq",
    "sra",
    "matrix_velocity",
    "matrix_10x",
    "gene_count_matrix",
    "CEL",
    "IDAT",
    "intensity",
    "intensity_matrix",
    "methylation_matrix",
    "processed",
}
SOURCE_PREFERENCES = {"auto", "ngdc", "ena", "ncbi", "geo"}
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


def release_state_path(root: Path) -> Path:
    return root / "reports/storage_release.tsv"


def read_release_states(root: Path) -> list[dict[str, str]]:
    return [
        {field: row.get(field, "").rstrip("\r") for field in RELEASE_FIELDS}
        for row in read_tsv(release_state_path(root))
    ]


def write_release_state(root: Path, row: dict[str, str]) -> dict[str, str]:
    normalized = {field: row.get(field, "").rstrip("\r") for field in RELEASE_FIELDS}
    if not GSM_RE.fullmatch(normalized["gsm"]):
        raise StoragePolicyError(f"invalid release GSM: {normalized['gsm']!r}")
    normalized["unit_id"] = normalized["unit_id"] or normalized["gsm"]
    rows = read_release_states(root)
    updated = [item for item in rows if item["unit_id"] != normalized["unit_id"]]
    updated.append(normalized)
    write_tsv_atomic(release_state_path(root), RELEASE_FIELDS, updated)
    return normalized


def read_config(root: Path) -> dict[str, str]:
    return {
        row.get("key", ""): row.get("value", "").rstrip("\r")
        for row in read_tsv(root / "metadata/acquisition_config.tsv")
        if row.get("key")
    }


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
    normalized["final_product"] = normalized["final_product"] or "pending"
    normalized["source_preference"] = normalized["source_preference"] or "auto"
    normalized["allow_sra_lite"] = normalized["allow_sra_lite"].lower() or "false"
    if not normalized["gse"]:
        raise StoragePolicyError("storage_policy.tsv 缺少 gse")
    assay = normalized["assay_type"]
    raw_type = normalized["raw_file_type"]
    if assay not in ASSAY_TYPES:
        raise StoragePolicyError(f"invalid assay_type={assay!r}")
    modality = normalized.get("modality", "")
    if modality not in MODALITIES:
        raise StoragePolicyError(f"invalid modality={modality!r}")
    if raw_type not in RAW_FILE_TYPES:
        raise StoragePolicyError(f"invalid raw_file_type={raw_type!r}")
    if normalized["final_product"] not in FINAL_PRODUCTS:
        raise StoragePolicyError(f"invalid final_product={normalized['final_product']!r}")
    if normalized["source_preference"] not in SOURCE_PREFERENCES:
        raise StoragePolicyError(
            f"invalid source_preference={normalized['source_preference']!r}"
        )
    if normalized["allow_sra_lite"] not in RETAIN_VALUES:
        raise StoragePolicyError(
            f"invalid allow_sra_lite={normalized['allow_sra_lite']!r}"
        )
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


def policy_key(row: dict[str, str]) -> tuple[str, str, str]:
    return (
        row.get("gse", ""),
        row.get("assay_type", ""),
        row.get("modality", ""),
    )


def default_policy(
    gse: str,
    retain_raw_files: bool,
    assay_type: str = "",
    raw_file_type: str = "",
    modality: str = "",
    final_product: str = "pending",
    source_preference: str = "auto",
    allow_sra_lite: bool = False,
    confirmed_at: str = "",
) -> dict[str, str]:
    if assay_type not in ASSAY_TYPES:
        raise StoragePolicyError(f"invalid assay_type={assay_type!r}")
    if modality not in MODALITIES:
        raise StoragePolicyError(f"invalid modality={modality!r}")
    if raw_file_type not in RAW_FILE_TYPES:
        raise StoragePolicyError(f"invalid raw_file_type={raw_file_type!r}")
    if final_product not in FINAL_PRODUCTS:
        raise StoragePolicyError(f"invalid final_product={final_product!r}")
    if source_preference not in SOURCE_PREFERENCES:
        raise StoragePolicyError(f"invalid source_preference={source_preference!r}")
    shared = {
        "gse": gse,
        "assay_type": assay_type,
        "modality": modality,
        "raw_file_type": raw_file_type,
        "final_product": final_product,
        "source_preference": source_preference,
        "allow_sra_lite": "true" if allow_sra_lite else "false",
        "confirmed_at": confirmed_at,
    }
    if retain_raw_files:
        return shared | {
            "retain_raw_files": "true",
            "storage_mode": "retain",
            "validation_status": "not_applicable",
            "deletion_status": "not_applicable",
            "deletion_time": "",
        }
    return shared | {
        "retain_raw_files": "false",
        "storage_mode": "delete_after_validation",
        "validation_status": "conversion_pending",
        "deletion_status": "pending",
        "deletion_time": "",
    }


def read_storage_policies(root: Path, required: bool = True) -> list[dict[str, str]]:
    path = storage_policy_path(root)
    rows = read_tsv(path)
    if not rows:
        if required:
            raise StoragePolicyError(f"缺少 {path.relative_to(root)}")
        return []
    return [normalize_policy(row) for row in rows]


def read_storage_policy(
    root: Path,
    required: bool = True,
    assay_type: str = "",
    modality: str = "",
    gsm: str = "",
) -> dict[str, str] | None:
    if gsm:
        return policy_for_gsm(root, gsm, required=required)
    policies = read_storage_policies(root, required=required)
    if not policies:
        return None
    if assay_type:
        matches = [
            row
            for row in policies
            if row["assay_type"] == assay_type
            and (not modality or row["modality"] == modality)
        ]
        if not matches:
            if required:
                raise StoragePolicyError(
                    f"storage_policy.tsv 没有 assay_type={assay_type} modality={modality}"
                )
            return None
        return matches[0]
    if len(policies) == 1:
        return policies[0]
    flags = {row["retain_raw_files"] for row in policies}
    if len(flags) == 1:
        return policies[0]
    raise StoragePolicyError("storage_policy.tsv 有多个 assay 且 retain 不一致，需要指定 gsm 或 assay_type")


def write_storage_policy(root: Path, row: dict[str, str]) -> dict[str, str]:
    normalized = normalize_policy(row)
    existing = []
    path = storage_policy_path(root)
    if path.is_file():
        existing = [normalize_policy(item) for item in read_tsv(path)]
    key = policy_key(normalized)
    updated: list[dict[str, str]] = []
    replaced = False
    for item in existing:
        bootstrap = (
            len(existing) == 1
            and item["gse"] == normalized["gse"]
            and not item["assay_type"]
            and normalized["assay_type"]
        )
        same = policy_key(item) == key or (
            item["gse"] == normalized["gse"]
            and item["assay_type"] == normalized["assay_type"]
            and not normalized["modality"]
            and not item["modality"]
        )
        if bootstrap or same:
            updated.append(normalized)
            replaced = True
        else:
            updated.append(item)
    if not replaced:
        updated.append(normalized)
    write_tsv_atomic(path, STORAGE_POLICY_FIELDS, updated)
    return normalized


def retain_raw_files(root: Path, required: bool = True) -> bool | None:
    policies = read_storage_policies(root, required=required)
    if not policies:
        return None
    flags = {row["retain_raw_files"] == "true" for row in policies}
    if len(flags) != 1:
        if required:
            raise StoragePolicyError("多个 assay 的 retain_raw_files 不一致，改用 retain_raw_for_gsm")
        return None
    return True in flags


def retain_raw_for_gsm(root: Path, gsm: str, required: bool = True) -> bool | None:
    policy = policy_for_gsm(root, gsm, required=required)
    if policy is None:
        return None
    return policy["retain_raw_files"] == "true"


def policy_for_gsm(
    root: Path,
    gsm: str,
    required: bool = True,
) -> dict[str, str] | None:
    policies = read_storage_policies(root, required=required)
    if not policies:
        return None
    routing = {
        row.get("gsm", ""): row
        for row in read_tsv(root / "metadata/assay_routing.tsv")
        if row.get("gsm")
    }
    sample = routing.get(gsm, {})
    assay = sample.get("assay_type", "")
    modality = sample.get("modality", "")
    raw_type = sample.get("raw_file_type", "")
    for row in policies:
        if assay and row["assay_type"] == assay and (not row["modality"] or not modality or row["modality"] == modality):
            return row
    for row in policies:
        if assay and row["assay_type"] == assay:
            return row
    for row in policies:
        if raw_type and row["raw_file_type"] == raw_type:
            return row
    if len(policies) == 1:
        return policies[0]
    if required:
        raise StoragePolicyError(f"无法为 {gsm} 匹配 storage_policy")
    return None


def retain_raw_fastq(root: Path, required: bool = True) -> bool | None:
    return retain_raw_files(root, required=required)


def is_array_raw(policy: dict[str, str] | None) -> bool:
    if not policy:
        return False
    return policy.get("raw_file_type", "") in {"CEL", "IDAT"}


def deletion_completed(root: Path) -> bool:
    policies = read_storage_policies(root, required=False)
    mode_b = [row for row in policies if row["retain_raw_files"] == "false"]
    if not mode_b:
        return False
    return all(row["deletion_status"] == "deleted" for row in mode_b)


def processed_audit_path(root: Path) -> Path:
    current = root / "reports/processed_output_audit.tsv"
    if current.is_file():
        return current
    legacy = root / "reports/final_output_audit.tsv"
    return current if not legacy.is_file() else legacy


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
        retain = retain_raw_for_gsm(root, gsm, required=False)
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


def list_temporary_raw_for_gsm(root: Path, gsm: str) -> list[Path]:
    if not GSM_RE.fullmatch(gsm):
        raise StoragePolicyError(f"invalid GSM accession: {gsm!r}")
    base = (root / "temporary" / gsm).resolve()
    files = [path for path in list_temporary_raw(root) if base in path.resolve().parents]
    return sorted(files)


def allow_sra_lite_for_gsm(root: Path, gsm: str) -> bool:
    policy = policy_for_gsm(root, gsm, required=False)
    if policy is not None:
        return policy.get("allow_sra_lite", "false") == "true"
    return read_config(root).get("allow_sra_lite", "false").lower() == "true"


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
    policy = policy_for_gsm(root, gsm)
    if policy is None:
        raise StoragePolicyError(f"缺少 {gsm} 的 storage_policy")
    retain = policy["retain_raw_files"] == "true"
    mapping = {
        "RETAIN_RAW": "true" if retain else "false",
        "STORAGE_MODE": policy["storage_mode"],
        "ALLOW_SRA_LITE": policy.get("allow_sra_lite", "false"),
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
