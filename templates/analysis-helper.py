#!/usr/bin/env python3
"""Perform one narrow file transformation for a bioinformatics analysis."""

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="TODO: describe the single transformation performed by this script."
    )
    parser.add_argument("input", type=Path, help="Input file")
    parser.add_argument("output_dir", type=Path, help="Output directory")
    args = parser.parse_args()

    if not args.input.is_file():
        raise FileNotFoundError(f"Input does not exist: {args.input}")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_file = args.output_dir / "TODO_OUTPUT_NAME.txt"

    # Read and inspect the minimum structure required by the task.
    lines = args.input.read_text(encoding="utf-8").splitlines()
    print(f"Read {len(lines)} lines from {args.input}")

    # TODO: replace this identity transformation with the task-specific linear logic.
    # Keep scientific parameters and decisions visible here. Add a small local helper
    # only if the same narrow operation is applied repeatedly.
    output_lines = lines

    output_file.write_text("\n".join(output_lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(output_lines)} lines to {output_file}")


if __name__ == "__main__":
    main()
