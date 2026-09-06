#!/usr/bin/env python3
"""Validate assay-specific processed products (count matrix, 10x, optional velocity)."""

from __future__ import annotations

import argparse
import csv
import gzip
import math
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from project_layout import (
    locate_outputs,
    policy_for_gsm,
    processed_audit_path,
    read_tsv,
    write_tsv_atomic,
)

import numpy as np
from scipy.io import mminfo, mmread
from artifact_integrity import IntegrityError, atomic_json, conversion_receipt, check_receipt


def refresh_report(root: Path) -> None:
    summarizer = Path(__file__).with_name("summarize_starsolo.py")
    if summarizer.is_file() and list(root.glob("reports/starsolo/**/Summary.csv")):
        subprocess.run(
            [sys.executable, str(summarizer), "--root", str(root)],
            check=False,
        )
    reporter = Path(__file__).with_name("build_report.py")
    if reporter.is_file():
        subprocess.run(
            [sys.executable, str(reporter), "--root", str(root)],
            check=False,
        )


def gzip_lines(path: Path) -> int:
    with gzip.open(path, "rt") as handle:
        return sum(1 for _ in handle)


def gzip_crc(path: Path) -> None:
    with gzip.open(path, "rb") as handle:
        while handle.read(8 * 1024 * 1024):
            pass


def read_matrix(path: Path):
    rows, cols, nonzero, kind, field, symmetry = mminfo(path)
    if kind != "coordinate" or field != "integer" or symmetry != "general":
        raise ValueError("Count MEX must be coordinate integer general")
    matrix = mmread(path, spmatrix=True).tocoo()
    if matrix.shape != (rows, cols) or matrix.nnz != nonzero:
        raise ValueError("Actual matrix dimensions/entry count differ from header")
    if not np.all(np.isfinite(matrix.data)) or np.any(matrix.data < 0):
        raise ValueError("Counts must be finite nonnegative integers")
    compressed = matrix.tocsr()
    if compressed.nnz != matrix.nnz:
        raise ValueError("Duplicate matrix coordinates")
    return compressed


def shape(path: Path) -> tuple[int, int, int]:
    matrix = read_matrix(path)
    return (*matrix.shape, matrix.nnz)


def identifiers(path: Path, features=False):
    with gzip.open(path, "rt") as handle:
        rows = [line.rstrip("\r\n").split("\t") for line in handle]
    columns = 3 if features else 1
    if (features and not rows) or any(len(row) != columns or any(not cell for cell in row) for row in rows):
        raise ValueError(f"Invalid metadata columns: {path.name}")
    if len({row[0] for row in rows}) != len(rows):
        raise ValueError(f"Duplicate identifiers: {path.name}")
    return rows


def routing_by_gsm(root: Path) -> dict[str, dict[str, str]]:
    return {
        row.get("gsm", ""): row
        for row in read_tsv(root / "metadata/assay_routing.tsv")
        if row.get("gsm")
    }


def product_for_gsm(rows: list[dict[str, str]], gsm: str) -> str:
    for row in rows:
        if row.get("gsm") == gsm and row.get("final_product"):
            return row["final_product"]
    return ""


def audit_gene_matrix(root: Path, gsm: str, errors: list[str]) -> None:
    path = root / f"processed/{gsm}/counts/counts.tsv.gz"
    if not path.is_file():
        errors.append(f"missing per-sample counts: {path.relative_to(root)}")
        return
    try:
        with gzip.open(path, "rt", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            fields = reader.fieldnames or []
            counts = [key for key in fields if key != "gene_id"]
            if not fields or fields[0] != "gene_id" or len(fields) != len(set(fields)) or not counts:
                raise ValueError("counts TSV requires unique gene_id and count columns")
            if not set(counts).issubset({"count", "unstranded", "forward", "reverse"}):
                raise ValueError("Unknown counting column semantics")
            seen = set()
            for row in reader:
                gene = row.get("gene_id")
                if not gene or gene in seen or None in row or any(not (row.get(key) or "").isdigit() for key in counts):
                    raise ValueError("Invalid/duplicate gene IDs or noninteger counts")
                seen.add(gene)
            if not seen:
                raise ValueError("Empty count table")
    except (OSError, ValueError, EOFError) as exc:
        errors.append(f"count table: {exc}")


def audit_array_product(root: Path, gsm: str, errors: list[str]) -> None:
    provenance = [
        row
        for row in read_tsv(root / "reports/conversion_provenance.tsv")
        if row.get("gsm") == gsm
    ]
    outputs = [
        root / item
        for row in provenance
        for item in row.get("output_matrix", "").split(";")
        if item
    ]
    if not outputs:
        errors.append(f"{gsm} 缺少 array conversion provenance/output")
        return
    for path in outputs:
        if not path.is_file() or path.stat().st_size == 0:
            errors.append(f"{gsm} 缺少非空 array product {path}")
            continue
        if not path.name.lower().endswith((".tsv", ".txt", ".tsv.gz", ".txt.gz")):
            errors.append(f"{gsm} array product 必须是可审计文本矩阵: {path.name}")
            continue
        opener = gzip.open if path.suffix.lower() == ".gz" else open
        with opener(path, "rt", newline="") as handle:
            reader = csv.DictReader(handle, delimiter="\t")
            fields = reader.fieldnames or []
            identifier = next((field for field in ("feature_id", "probe_id", "cpg_id") if field in fields), "")
            if not identifier or gsm not in fields or len(fields) != len(set(fields)):
                errors.append(f"{gsm} array product 缺少 feature/probe/CpG ID 或样本列")
                continue
            rows = list(reader)
        if not rows:
            errors.append(f"{gsm} array product 为空")
            continue
        identifiers: set[str] = set()
        for row in rows:
            feature = row.get(identifier, "")
            if not feature or feature in identifiers or None in row:
                errors.append(f"{gsm} array product feature ID 缺失或重复")
                break
            identifiers.add(feature)
            try:
                if not math.isfinite(float(row.get(gsm, ""))):
                    raise ValueError
            except (TypeError, ValueError):
                errors.append(f"{gsm} array product 含非数值或非有限值")
                break


def audit_10x(
    root: Path,
    gse: str,
    gsm: str,
    require_velocity: bool,
    skip_full_gzip: bool,
    errors: list[str],
) -> tuple[str, str, str]:
    matrix_dir, velocity_dir, loom_file = locate_outputs(root, gse, gsm)
    shapes: dict[str, tuple[int, int, int]] = {}
    gzip_paths: list[Path] = []
    triplets = {}
    for subset in ("raw", "filtered"):
        directory = matrix_dir / f"{subset}_feature_bc_matrix"
        if subset == "filtered" and not directory.exists():
            continue
        paths = {
            "matrix": directory / "matrix.mtx.gz",
            "features": directory / "features.tsv.gz",
            "barcodes": directory / "barcodes.tsv.gz",
        }
        if any(not path.is_file() or path.stat().st_size == 0 for path in paths.values()):
            errors.append(f"missing {subset} 10x triplet")
            continue
        gzip_paths.extend(paths.values())
        try:
            matrix = read_matrix(paths["matrix"])
            features = identifiers(paths["features"], features=True)
            barcodes = identifiers(paths["barcodes"])
            triplets[subset] = (matrix, features, barcodes)
            matrix_shape = (*matrix.shape, matrix.nnz)
            shapes[subset] = matrix_shape
            if len(features) != matrix_shape[0]:
                errors.append(f"{subset} feature count mismatch")
            if len(barcodes) != matrix_shape[1]:
                errors.append(f"{subset} barcode count mismatch")
        except Exception as exc:
            errors.append(f"{subset} matrix error: {exc}")
    raw = shapes.get("raw")
    filtered = shapes.get("filtered")
    if raw and filtered and (raw[0] != filtered[0] or filtered[1] > raw[1]):
        errors.append(f"raw/filtered shapes inconsistent: {raw} vs {filtered}")

    if "raw" in triplets and "filtered" in triplets:
        raw_m, raw_f, raw_b = triplets["raw"]
        fil_m, fil_f, fil_b = triplets["filtered"]
        positions = {row[0]: index for index, row in enumerate(raw_b)}
        if raw_f != fil_f:
            errors.append("raw/filtered feature IDs or order differ")
        elif any(row[0] not in positions for row in fil_b):
            errors.append("filtered barcodes are not a subset of raw")
        elif raw_m.shape[0] == fil_m.shape[0] and raw_m.shape[1] == len(raw_b) and fil_m.shape[1] == len(fil_b):
            if (raw_m[:, [positions[row[0]] for row in fil_b]] != fil_m).nnz:
                errors.append("filtered counts differ from matching raw columns")

    loom_shape: tuple[int, int] | None = None
    velocity_present = any(
        (velocity_dir / name).is_file()
        for name in (
            "spliced.mtx.gz",
            "unspliced.mtx.gz",
            "ambiguous.mtx.gz",
            "features.tsv.gz",
            "barcodes.tsv.gz",
        )
    )
    if require_velocity or velocity_present:
        velocity_paths = {
            name: velocity_dir / f"{name}.mtx.gz"
            for name in ("spliced", "unspliced", "ambiguous")
        }
        vf = velocity_dir / "features.tsv.gz"
        vb = velocity_dir / "barcodes.tsv.gz"
        if any(
            not path.is_file() or path.stat().st_size == 0
            for path in [*velocity_paths.values(), vf, vb]
        ):
            errors.append("missing velocity matrix/files")
        else:
            gzip_paths.extend([*velocity_paths.values(), vf, vb])
            try:
                velocity_shapes = {name: shape(path) for name, path in velocity_paths.items()}
                if len({value[:2] for value in velocity_shapes.values()}) != 1:
                    errors.append(f"velocity layer shapes differ: {velocity_shapes}")
                first = next(iter(velocity_shapes.values()))
                if raw and first[:2] != raw[:2]:
                    errors.append(f"velocity/raw shape mismatch: {first} vs {raw}")
                vfeatures, vbarcodes = identifiers(vf, features=True), identifiers(vb)
                if len(vfeatures) != first[0] or len(vbarcodes) != first[1]:
                    errors.append("velocity feature/barcode count mismatch")
                if "raw" in triplets and (vfeatures != triplets["raw"][1] or vbarcodes != triplets["raw"][2]):
                    errors.append("velocity/raw feature or barcode order differs")
            except Exception as exc:
                errors.append(f"velocity error: {exc}")

    if not skip_full_gzip:
        for path in gzip_paths:
            try:
                gzip_crc(path)
            except Exception as exc:
                errors.append(f"gzip CRC failed {path}: {exc}")
    return (
        "x".join(map(str, raw[:2])) if raw else "",
        "x".join(map(str, filtered[:2])) if filtered else "",
        "x".join(map(str, loom_shape)) if loom_shape else "",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--skip-full-gzip", action="store_true", help="Skip extra gzip scan only with --structure-only; formal audits always check CRC")
    parser.add_argument("--structure-only", action="store_true", help="Diagnostic structural check; never authorizes release")
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument("--gsm")
    scope.add_argument("--unit", dest="gsm", help="转换原子单元；当前等价于 --gsm")
    args = parser.parse_args()
    root = args.root.resolve()
    if args.manifest:
        manifest = args.manifest
    elif (root / "metadata/source_manifest.tsv").is_file():
        manifest = root / "metadata/source_manifest.tsv"
    else:
        manifest = root / "metadata/sample_processing_manifest.tsv"
    rows = read_tsv(manifest)
    if args.gsm:
        rows = [row for row in rows if row.get("gsm") == args.gsm]
        if not rows:
            raise SystemExit(f"manifest 中找不到 {args.gsm}")
    samples = sorted({(row["gse"], row["gsm"]) for row in rows})
    output = args.output or processed_audit_path(root)
    if output.name == "final_output_audit.tsv" and args.output is None:
        output = root / "reports/processed_output_audit.tsv"
    if not output.is_file() and args.output is None:
        output = root / "reports/processed_output_audit.tsv"
    routing = routing_by_gsm(root)
    report_rows: list[dict[str, str]] = []
    all_errors: list[str] = []

    for gse, gsm in samples:
        errors: list[str] = []
        sample = routing.get(gsm, {})
        modality = sample.get("modality", "")
        product = product_for_gsm(rows, gsm)
        policy = policy_for_gsm(root, gsm, required=False)
        if policy and policy.get("final_product") not in {"", "pending"}:
            product = policy["final_product"]
        raw_shape = filtered_shape = loom_shape = ""
        if modality in {"atac", "chip", "mirna", "sequencing"}:
            errors.append("raw-only assay 在本 Skill 中没有可审计转换产物")
        elif modality in {"microarray", "methylation"} or sample.get("raw_file_type") in {
            "CEL",
            "IDAT",
        }:
            if product in {"", "pending", "CEL", "IDAT", "fastq", "sra"}:
                errors.append("CEL/IDAT 未指定可审计转换产物")
            else:
                try:
                    audit_array_product(root, gsm, errors)
                except (OSError, ValueError, EOFError) as exc:
                    errors.append(f"array product: {exc}")
        elif modality == "bulk_rnaseq" or product == "gene_count_matrix":
            audit_gene_matrix(root, gsm, errors)
        else:
            require_velocity = product == "matrix_velocity" or (
                not modality and product != "matrix_10x"
            )
            raw_shape, filtered_shape, loom_shape = audit_10x(
                root, gse, gsm, require_velocity, args.skip_full_gzip and args.structure_only, errors
            )
        if not errors and not args.structure_only:
            try:
                receipt_path = root / f"reports/processed_receipts/{gsm}.json"
                released = any(row.get("gsm") == gsm and row.get("release_status") == "released"
                               for row in read_tsv(root / "reports/storage_release.tsv"))
                if released:
                    check_receipt(root, gsm, allow_missing_inputs=True)
                else:
                    if product == "gene_count_matrix" or modality == "bulk_rnaseq":
                        output_names = [f"processed/{gsm}/counts/counts.tsv.gz"]
                    elif modality in {"microarray", "methylation"} or sample.get("raw_file_type") in {"CEL", "IDAT"}:
                        output_names = [name for row in read_tsv(root / "reports/conversion_provenance.tsv")
                                        if row.get("gsm") == gsm for name in row.get("output_matrix", "").split(";") if name]
                    else:
                        matrix_dir, velocity_dir, loom = locate_outputs(root, gse, gsm)
                        candidates = [matrix_dir / f"{subset}_feature_bc_matrix" / name
                                      for subset in ("raw", "filtered")
                                      for name in ("matrix.mtx.gz", "features.tsv.gz", "barcodes.tsv.gz")]
                        candidates += [velocity_dir / name for name in
                                       ("spliced.mtx.gz", "unspliced.mtx.gz", "ambiguous.mtx.gz", "features.tsv.gz", "barcodes.tsv.gz")]
                        output_names = [path.relative_to(root).as_posix() for path in candidates if path.is_file()]
                    receipt = conversion_receipt(root, gsm, output_names)
                    atomic_json(receipt_path, receipt)
            except (IntegrityError, OSError, ValueError, KeyError) as exc:
                errors.append(f"content-bound audit: {exc}")
        all_errors.extend(f"{gse}/{gsm}: {message}" for message in errors)
        report_rows.append(
            {
                "gse": gse,
                "gsm": gsm,
                "raw_shape": raw_shape,
                "filtered_shape": filtered_shape,
                "loom_shape": loom_shape,
                "status": "FAIL" if errors else ("STRUCTURE_ONLY" if args.structure_only else "PASS"),
                "message": "; ".join(errors),
            }
        )

    fields = ["gse", "gsm", "raw_shape", "filtered_shape", "loom_shape", "status", "message"]
    if args.gsm:
        prior = [row for row in read_tsv(output) if row.get("gsm") != args.gsm]
        report_rows = prior + report_rows
    write_tsv_atomic(output, fields, report_rows)
    passed = sum(row["status"] == "PASS" for row in report_rows)
    print(
        f"AUDIT samples={len(samples)} passed={passed} errors={len(all_errors)} report={output}"
    )
    for error in all_errors:
        print(f"ERROR {error}")
    refresh_report(root)
    return 1 if all_errors else 0


if __name__ == "__main__":
    sys.exit(main())
