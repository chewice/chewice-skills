#!/usr/bin/env python3
"""Stream-validate paired FASTQ gzip files and expected read geometry."""

from __future__ import annotations

import argparse
import gzip
import itertools
import json
import re
import sys
from pathlib import Path


def records(path: Path):
    with gzip.open(path, "rt") as handle:
        while True:
            header = handle.readline()
            if not header:
                return
            sequence = handle.readline()
            plus = handle.readline()
            quality = handle.readline()
            if not sequence or not plus or not quality:
                raise ValueError(f"{path}: truncated FASTQ record")
            header = header.rstrip("\r\n")
            sequence = sequence.rstrip("\r\n")
            plus = plus.rstrip("\r\n")
            quality = quality.rstrip("\r\n")
            if not header.startswith("@") or not plus.startswith("+"):
                raise ValueError(f"{path}: invalid FASTQ structure at {header[:80]!r}")
            if len(sequence) != len(quality):
                raise ValueError(
                    f"{path}: sequence/quality length mismatch at {header[:80]!r}"
                )
            yield header, len(sequence)


def read_id(header: str) -> str:
    token = header[1:].split()[0]
    return re.sub(r"(?:/[12])$", "", token)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--r1", required=True, type=Path)
    parser.add_argument("--r2", type=Path)
    parser.add_argument("--srr", required=True)
    parser.add_argument("--expected-spots", type=int)
    parser.add_argument("--cb-length", type=int, default=0)
    parser.add_argument("--umi-length", type=int, default=0)
    parser.add_argument("--skip-name-match", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    paths = (args.r1, args.r2) if args.r2 else (args.r1,)
    for path in paths:
        if not path.is_file() or path.stat().st_size == 0:
            raise SystemExit(f"Missing or empty FASTQ: {path}")

    count = 0
    min_r1: int | None = None
    min_r2: int | None = None
    if args.r2:
        for left, right in itertools.zip_longest(records(args.r1), records(args.r2)):
            if left is None or right is None:
                raise SystemExit(f"{args.srr}: R1/R2 record counts differ at {count}")
            if not args.skip_name_match and read_id(left[0]) != read_id(right[0]):
                raise SystemExit(
                    f"{args.srr}: mate IDs differ at record {count + 1}: "
                    f"{left[0]!r} vs {right[0]!r}"
                )
            count += 1
            min_r1 = left[1] if min_r1 is None else min(min_r1, left[1])
            min_r2 = right[1] if min_r2 is None else min(min_r2, right[1])
    else:
        for left in records(args.r1):
            count += 1
            min_r1 = left[1] if min_r1 is None else min(min_r1, left[1])

    if count == 0:
        raise SystemExit(f"{args.srr}: FASTQ pair contains no records")
    if args.expected_spots is not None and count != args.expected_spots:
        raise SystemExit(
            f"{args.srr}: expected {args.expected_spots} reads/mate, observed {count}"
        )
    required = args.cb_length + args.umi_length
    if required and (min_r1 or 0) < required:
        raise SystemExit(
            f"{args.srr}: min R1={min_r1} shorter than CB+UMI={required}"
        )

    result = {
        "srr": args.srr,
        "r1": str(args.r1),
        "r2": str(args.r2) if args.r2 else "",
        "reads_per_mate": count,
        "min_r1": min_r1,
        "min_r2": min_r2,
        "cb_length": args.cb_length,
        "umi_length": args.umi_length,
        "status": "PASS",
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        temp = args.report.with_suffix(args.report.suffix + ".tmp")
        temp.write_text(json.dumps(result, indent=2) + "\n")
        temp.replace(args.report)
    print(
        f"PASS {args.srr}: {count} reads/mate; min_R1={min_r1}; "
        f"min_R2={min_r2}; CB={args.cb_length}; UMI={args.umi_length}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
