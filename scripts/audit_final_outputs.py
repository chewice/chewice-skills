#!/usr/bin/env python3
"""Validate raw/filtered 10x matrices and RNA-velocity outputs for every GSM."""

from __future__ import annotations

import argparse
import csv
import gzip
import subprocess
import sys
from pathlib import Path

import h5py
from scipy.io import mminfo


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


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def gzip_lines(path: Path) -> int:
    with gzip.open(path, "rt") as handle:
        return sum(1 for _ in handle)


def gzip_crc(path: Path) -> None:
    with gzip.open(path, "rb") as handle:
        while handle.read(8 * 1024 * 1024):
            pass


def shape(path: Path) -> tuple[int, int, int]:
    rows, cols, nonzero, *_ = mminfo(path)
    return int(rows), int(cols), int(nonzero)


def locate(root: Path, gse: str, gsm: str):
    new_matrix = root / gsm / "matrix_10x"
    new_velocity = root / gsm / "velocity"
    if new_matrix.is_dir():
        matrix = new_matrix
        velocity = new_velocity
        loom = new_velocity / f"{gsm}.loom"
    else:
        matrix = root / "matrix_10x" / gse / gsm
        velocity = root / "velocity" / gse / gsm
        loom = root / "velocity" / gse / f"{gsm}.loom"
    return matrix, velocity, loom


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--skip-full-gzip", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()
    if args.manifest:
        manifest = args.manifest
    elif (root / "metadata/source_manifest.tsv").is_file():
        manifest = root / "metadata/source_manifest.tsv"
    else:
        manifest = root / "metadata/sample_processing_manifest.tsv"
    rows = read_tsv(manifest)
    samples = sorted({(row["gse"], row["gsm"]) for row in rows})
    output = args.output or root / "reports/final_output_audit.tsv"
    report_rows: list[dict[str, str]] = []
    all_errors: list[str] = []

    for gse, gsm in samples:
        errors: list[str] = []
        matrix_dir, velocity_dir, loom_path = locate(root, gse, gsm)
        shapes: dict[str, tuple[int, int, int]] = {}
        gzip_paths: list[Path] = []
        for subset in ("raw", "filtered"):
            directory = matrix_dir / f"{subset}_feature_bc_matrix"
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
                matrix_shape = shape(paths["matrix"])
                shapes[subset] = matrix_shape
                if gzip_lines(paths["features"]) != matrix_shape[0]:
                    errors.append(f"{subset} feature count mismatch")
                if gzip_lines(paths["barcodes"]) != matrix_shape[1]:
                    errors.append(f"{subset} barcode count mismatch")
            except Exception as exc:
                errors.append(f"{subset} matrix error: {exc}")
        raw = shapes.get("raw")
        filtered = shapes.get("filtered")
        if raw and filtered and (raw[0] != filtered[0] or filtered[1] > raw[1]):
            errors.append(f"raw/filtered shapes inconsistent: {raw} vs {filtered}")

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
                if len(set(velocity_shapes.values())) != 1:
                    errors.append(f"velocity layer shapes differ: {velocity_shapes}")
                first = next(iter(velocity_shapes.values()))
                if raw and first[:2] != raw[:2]:
                    errors.append(f"velocity/raw shape mismatch: {first} vs {raw}")
                if gzip_lines(vf) != first[0] or gzip_lines(vb) != first[1]:
                    errors.append("velocity feature/barcode count mismatch")
            except Exception as exc:
                errors.append(f"velocity error: {exc}")

        loom_shape: tuple[int, int] | None = None
        if not loom_path.is_file() or loom_path.stat().st_size == 0:
            errors.append("missing loom")
        else:
            try:
                with h5py.File(loom_path, "r") as loom:
                    loom_shape = tuple(int(value) for value in loom["matrix"].shape)
                    layers = set(loom["layers"].keys())
                    if layers != {"spliced", "unspliced", "ambiguous"}:
                        errors.append(f"loom layers={sorted(layers)}")
                    if filtered and loom_shape != filtered[:2]:
                        errors.append(f"loom/filtered shape mismatch: {loom_shape} vs {filtered}")
                    for layer in layers:
                        if tuple(loom["layers"][layer].shape) != loom_shape:
                            errors.append(f"loom layer {layer} shape mismatch")
            except Exception as exc:
                errors.append(f"loom error: {exc}")

        if not args.skip_full_gzip:
            for path in gzip_paths:
                try:
                    gzip_crc(path)
                except Exception as exc:
                    errors.append(f"gzip CRC failed {path}: {exc}")

        all_errors.extend(f"{gse}/{gsm}: {message}" for message in errors)
        report_rows.append(
            {
                "gse": gse,
                "gsm": gsm,
                "raw_shape": "x".join(map(str, raw[:2])) if raw else "",
                "filtered_shape": "x".join(map(str, filtered[:2])) if filtered else "",
                "loom_shape": "x".join(map(str, loom_shape)) if loom_shape else "",
                "status": "FAIL" if errors else "PASS",
                "message": "; ".join(errors),
            }
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_suffix(output.suffix + ".tmp")
    with temp.open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=("gse", "gsm", "raw_shape", "filtered_shape", "loom_shape", "status", "message"),
            delimiter="\t",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(report_rows)
    temp.replace(output)
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
