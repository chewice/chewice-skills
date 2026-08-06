#!/usr/bin/env python3
"""Convert pixi.toml / pixi.lock conda mirror URLs to TUNA."""

from __future__ import annotations

import argparse
from pathlib import Path


REPLACEMENTS = {
    "https://mirrors.westlake.edu.cn/ANACONDA/cloud/conda-forge": "https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge",
    "https://mirrors.westlake.edu.cn/ANACONDA/cloud/bioconda": "https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/bioconda",
    "https://mirror.sjtu.edu.cn/anaconda/cloud/conda-forge": "https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge",
    "https://mirror.sjtu.edu.cn/anaconda/cloud/bioconda": "https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/bioconda",
    "https://conda.anaconda.org/conda-forge": "https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/conda-forge",
    "https://conda.anaconda.org/bioconda": "https://mirrors.tuna.tsinghua.edu.cn/anaconda/cloud/bioconda",
}


def convert_file(path: Path, dry_run: bool) -> int:
    if not path.exists():
        raise FileNotFoundError(path)
    if not path.is_file():
        raise IsADirectoryError(path)

    text = path.read_text(encoding="utf-8")
    converted = text
    count = 0

    for old, new in REPLACEMENTS.items():
        old_count = converted.count(old)
        if old_count:
            converted = converted.replace(old, new)
            count += old_count

    if converted != text and not dry_run:
        path.write_text(converted, encoding="utf-8")

    return count


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert pixi.toml / pixi.lock conda mirror URLs to TUNA.",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="Path(s) to pixi.toml and/or pixi.lock.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show replacement counts without editing files.",
    )
    args = parser.parse_args()

    total = 0
    for path in args.paths:
        count = convert_file(path, args.dry_run)
        total += count
        action = "would replace" if args.dry_run else "replaced"
        print(f"{path}: {action} {count} URL(s)")

    print(f"total: {'would replace' if args.dry_run else 'replaced'} {total} URL(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
