#!/usr/bin/env python3
"""Derive STAR sjdbOverhang from authoritative read length and verify a pilot FASTQ."""

from __future__ import annotations

import argparse
import csv
import gzip
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from project_layout import read_tsv, write_tsv_atomic  # noqa: E402


def metadata_lengths(root: Path, gsm: str) -> set[int]:
    rows = read_tsv(root / "metadata/expected_runs.tsv")
    if gsm:
        rows = [row for row in rows if row.get("gsm") == gsm]
    lengths: set[int] = set()
    for row in rows:
        for value in re.findall(r"(?:R[12]|READ[12])\s*[:=]\s*(\d+)", row.get("read_structure", ""), re.I):
            lengths.add(int(value))
    return lengths


def pilot_lengths(path: Path, limit: int = 1000) -> set[int]:
    opener = gzip.open if path.suffix == ".gz" else open
    lengths: set[int] = set()
    with opener(path, "rt") as handle:
        for index, line in enumerate(handle):
            if index % 4 == 1:
                lengths.add(len(line.rstrip("\r\n")))
                if index // 4 + 1 >= limit:
                    break
    if not lengths:
        raise SystemExit(f"pilot FASTQ 无 read: {path}")
    return lengths


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--gsm", default="")
    parser.add_argument("--authoritative-read-length", type=int)
    parser.add_argument("--pilot-fastq", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    authority = args.authoritative_read_length
    evidence = "--authoritative-read-length"
    metadata = metadata_lengths(root, args.gsm)
    if authority is None:
        if len(metadata) != 1:
            raise SystemExit(
                f"权威 read length 不唯一：{sorted(metadata)}；请显式提供 --authoritative-read-length"
            )
        authority = next(iter(metadata))
        evidence = "metadata/expected_runs.tsv:read_structure"
    if authority <= 1:
        raise SystemExit("authoritative read length 必须大于 1")
    observed: set[int] = set()
    for path in args.pilot_fastq:
        observed.update(pilot_lengths(path))
    if observed and observed != {authority}:
        raise SystemExit(
            f"pilot FASTQ read length={sorted(observed)} 与权威长度={authority} 不一致"
        )
    output = args.output or root / "metadata/reference_parameters.tsv"
    if not output.is_absolute():
        output = root / output
    write_tsv_atomic(
        output,
        ["gsm", "parameter", "value", "authority", "pilot_observed"],
        [{
            "gsm": args.gsm,
            "parameter": "sjdbOverhang",
            "value": str(authority - 1),
            "authority": evidence,
            "pilot_observed": ";".join(map(str, sorted(observed))),
        }],
    )
    print(f"STAR_PARAMETER sjdbOverhang={authority - 1} authority={evidence} pilot={sorted(observed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
