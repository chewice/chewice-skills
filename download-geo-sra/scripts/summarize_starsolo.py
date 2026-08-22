#!/usr/bin/env python3
"""将样本级 STARsolo Summary.csv 汇总为每个 GSM 一行的 TSV。"""

from __future__ import annotations

import argparse
import csv
import fcntl
import os
import re
import tempfile
from pathlib import Path


METRICS = [
    ("Number of Reads", "number_of_reads"),
    ("Reads With Valid Barcodes", "reads_with_valid_barcodes"),
    ("Sequencing Saturation", "sequencing_saturation"),
    ("Q30 Bases in CB+UMI", "q30_bases_cb_umi"),
    ("Q30 Bases in RNA read", "q30_bases_rna_read"),
    ("Reads Mapped to Genome: Unique+Multiple", "reads_mapped_genome_unique_multiple"),
    ("Reads Mapped to Genome: Unique", "reads_mapped_genome_unique"),
    ("Reads Mapped to GeneFull: Unique GeneFull", "reads_mapped_genefull_unique"),
    ("Estimated Number of Cells", "estimated_number_of_cells"),
    ("Unique Reads in Cells Mapped to GeneFull", "unique_reads_in_cells_genefull"),
    ("Fraction of Unique Reads in Cells", "fraction_unique_reads_in_cells"),
    ("Mean Reads per Cell", "mean_reads_per_cell"),
    ("Median Reads per Cell", "median_reads_per_cell"),
    ("UMIs in Cells", "umis_in_cells"),
    ("Mean UMI per Cell", "mean_umi_per_cell"),
    ("Median UMI per Cell", "median_umi_per_cell"),
    ("Mean GeneFull per Cell", "mean_genefull_per_cell"),
    ("Median GeneFull per Cell", "median_genefull_per_cell"),
    ("Total GeneFull Detected", "total_genefull_detected"),
]
ACCESSION = re.compile(r"^(?:GSE|GSM)\d+$")


def read_tsv(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8", errors="replace") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def metadata(root: Path) -> tuple[dict[str, dict[str, str]], set[str]]:
    rows = read_tsv(root / "metadata/sample_processing_manifest.tsv")
    if not rows:
        rows = read_tsv(root / "metadata/sample_metadata.tsv")
    by_gsm = {row.get("gsm", ""): row for row in rows if row.get("gsm", "")}
    return by_gsm, set(by_gsm)


def discover(root: Path) -> list[Path]:
    candidates = {
        *root.glob("reports/starsolo/**/GeneFull_Summary.csv"),
        *root.glob("reports/starsolo/**/Summary.csv"),
        *root.glob("processed/*/starsolo/**/GeneFull_Summary.csv"),
        *root.glob("processed/*/starsolo/**/Summary.csv"),
        *root.glob("GSM*/starsolo/**/GeneFull_Summary.csv"),
        *root.glob("GSM*/starsolo/**/Summary.csv"),
    }
    return sorted(path for path in candidates if path.is_file() and path.stat().st_size)


def accessions(path: Path, root: Path, meta: dict[str, dict[str, str]]) -> tuple[str, str]:
    parts = path.relative_to(root).parts
    gsm = next((part for part in parts if part.startswith("GSM") and ACCESSION.fullmatch(part)), "")
    gse = next((part for part in parts if part.startswith("GSE") and ACCESSION.fullmatch(part)), "")
    if gsm and not gse:
        gse = meta.get(gsm, {}).get("gse", "")
    if not gsm:
        raise ValueError(f"无法从相对路径识别 GSM：{path.relative_to(root)}")
    return gse, gsm


def read_summary(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    with path.open(newline="", encoding="utf-8", errors="replace") as handle:
        for row in csv.reader(handle):
            if len(row) >= 2:
                values[row[0].strip()] = row[1].strip()
    return values


def write_atomic(path: Path, fields: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.parent / f".{path.name}.lock"
    with lock_path.open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
                writer = csv.DictWriter(
                    handle, fieldnames=fields, delimiter="\t", lineterminator="\n"
                )
                writer.writeheader()
                writer.writerows(rows)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            Path(temporary).unlink(missing_ok=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="汇总 STARsolo GeneFull Summary.csv")
    parser.add_argument("--root", required=True, type=Path, help="GSE 项目根目录")
    parser.add_argument("--output", type=Path, help="默认 reports/starsolo_summary.tsv")
    parser.add_argument(
        "--allow-partial",
        action="store_true",
        help="允许仅汇总当前已有的样本；默认要求 metadata 中所有 GSM 均存在 Summary",
    )
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output or root / "reports/starsolo_summary.tsv"
    if not output.is_absolute():
        output = root / output

    meta, expected = metadata(root)
    paths = discover(root)
    if not paths:
        raise SystemExit("未发现样本级 STARsolo GeneFull_Summary.csv 或 Summary.csv")

    rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for path in paths:
        gse, gsm = accessions(path, root, meta)
        if gsm in seen:
            raise SystemExit(f"同一 GSM 发现多个 STARsolo Summary：{gsm}")
        seen.add(gsm)
        sample = meta.get(gsm, {})
        values = read_summary(path)
        row = {
            "gse": gse,
            "gsm": gsm,
            "sample": sample.get("paper_sample", sample.get("title", "")),
            "condition": sample.get("paper_Condition", sample.get("condition", "")),
            "batch": sample.get("paper_Batch", sample.get("batch", "")),
            "sex": sample.get("paper_Sex", sample.get("sex", "")),
            "chemistry": sample.get("chemistry", ""),
            "summary_relative_path": path.relative_to(root).as_posix(),
        }
        row.update({destination: values.get(source, "") for source, destination in METRICS})
        rows.append(row)

    missing = expected - seen
    if missing and not args.allow_partial:
        raise SystemExit(
            f"缺少 {len(missing)} 个 metadata 样本的 STARsolo Summary："
            + ",".join(sorted(missing))
        )
    rows.sort(key=lambda row: (row["gse"], row["gsm"]))
    fields = list(rows[0])
    write_atomic(output, fields, rows)
    try:
        output_label = output.relative_to(root).as_posix()
    except ValueError:
        output_label = str(output)
    print(
        f"STARSOLO_SUMMARY samples={len(rows)} expected={len(expected) or '?'} "
        f"missing={len(missing)} output={output_label}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
