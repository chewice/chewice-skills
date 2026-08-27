#!/usr/bin/env python3
"""Merge per-GSM STAR ReadsPerGene.out.tab files into gene × sample counts."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from project_layout import write_tsv_atomic  # noqa: E402

STRAND_COLUMN = {"unstranded": 1, "forward": 2, "reverse": 3}


def find_reads_per_gene(root: Path) -> list[tuple[str, Path]]:
    hits: list[tuple[str, Path]] = []
    for path in sorted(root.glob("processed/GSM*/counts/ReadsPerGene.out.tab")):
        gsm = path.parent.parent.name
        hits.append((gsm, path))
    return hits


def read_counts(path: Path, column: int) -> dict[str, int]:
    counts: dict[str, int] = {}
    with path.open() as handle:
        for line in handle:
            if not line.strip() or line.startswith("N_"):
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) <= column:
                raise SystemExit(f"ReadsPerGene 列不足: {path}")
            counts[fields[0]] = int(fields[column])
    if not counts:
        raise SystemExit(f"empty {path}")
    return counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument(
        "--strandedness",
        choices=("unknown", *STRAND_COLUMN),
        default="unknown",
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    files = find_reads_per_gene(root)
    if not files:
        raise SystemExit("未找到 processed/GSM*/counts/ReadsPerGene.out.tab")
    if args.strandedness == "unknown":
        by_sample_strand = {
            (gsm, strand): read_counts(path, column)
            for gsm, path in files
            for strand, column in STRAND_COLUMN.items()
        }
        genes = sorted(set().union(*by_sample_strand.values()))
        fields = [
            "gene_id",
            *[f"{gsm}__{strand}" for gsm, _ in files for strand in STRAND_COLUMN],
        ]
        rows = [
            {
                "gene_id": gene,
                **{
                    f"{gsm}__{strand}": str(by_sample_strand[(gsm, strand)].get(gene, 0))
                    for gsm, _ in files
                    for strand in STRAND_COLUMN
                },
            }
            for gene in genes
        ]
        output = args.output or root / "processed/star_gene_counts_all_strands.tsv"
    else:
        column = STRAND_COLUMN[args.strandedness]
        by_gsm = {gsm: read_counts(path, column) for gsm, path in files}
        genes = sorted(set().union(*by_gsm.values()))
        fields = ["gene_id", *[gsm for gsm, _ in files]]
        rows = [
            {
                "gene_id": gene,
                **{gsm: str(by_gsm[gsm].get(gene, 0)) for gsm, _ in files},
            }
            for gene in genes
        ]
        output = args.output or root / "processed/gene_count_matrix.tsv"
    write_tsv_atomic(output, fields, rows)
    print(
        f"GENE_COUNT_MATRIX genes={len(genes)} samples={len(files)} "
        f"strandedness={args.strandedness} output={output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
