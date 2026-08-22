#!/usr/bin/env python3
"""Download GEO supplementary raw files (CEL/IDAT) into raw or temporary GSM dirs."""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from project_layout import (  # noqa: E402
    published_raw_dir,
    read_storage_policy,
    read_tsv,
    retain_raw_files,
    write_tsv_atomic,
)


def resolve_file_type(
    requested: str | None,
    policy: dict[str, str],
    rows: list[dict[str, str]],
) -> str:
    if requested:
        return requested
    raw = policy.get("raw_file_type", "")
    if raw in {"CEL", "IDAT"}:
        return raw
    listed = {row.get("file_type", "").upper() for row in rows if row.get("file_type")}
    listed.discard("")
    if listed == {"CEL"} or listed == {"IDAT"}:
        return listed.pop()
    raise SystemExit(
        "需要 --file-type CEL|IDAT，或在 storage_policy.raw_file_type / "
        "supplement_files.file_type 中给出唯一类型"
    )


def md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.with_name(destination.name + ".part")
    with urllib.request.urlopen(url) as response, temp.open("wb") as handle:
        while chunk := response.read(8 * 1024 * 1024):
            handle.write(chunk)
            handle.flush()
            os.fsync(handle.fileno())
    os.replace(temp, destination)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--input", type=Path, help="supplement_files.tsv")
    parser.add_argument("--file-type", choices=("CEL", "IDAT"))
    args = parser.parse_args()
    root = args.root.resolve()
    policy = read_storage_policy(root)
    retain = retain_raw_files(root)
    source = args.input or root / "metadata/supplement_files.tsv"
    rows = read_tsv(source)
    if not rows:
        raise SystemExit(f"empty {source}")
    file_type = resolve_file_type(args.file_type, policy, rows)
    manifest_fields = [
        "gse",
        "gsm",
        "filename",
        "url",
        "file_type",
        "observed_bytes",
        "observed_md5",
        "path",
        "validation",
    ]
    by_gsm: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        gsm = row["gsm"]
        name = row.get("filename") or Path(row["url"].split("?")[0]).name
        directory = published_raw_dir(root, gsm, file_type, retain)
        destination = directory / name
        download(row["url"], destination)
        if destination.stat().st_size == 0:
            raise SystemExit(f"empty download {destination}")
        if name.lower().endswith(".gz"):
            import gzip

            with gzip.open(destination, "rb") as handle:
                handle.read(1)
        relative = destination.relative_to(root).as_posix()
        by_gsm.setdefault(gsm, []).append(
            {
                "gse": row.get("gse", policy["gse"]),
                "gsm": gsm,
                "filename": name,
                "url": row["url"],
                "file_type": file_type,
                "observed_bytes": str(destination.stat().st_size),
                "observed_md5": md5(destination),
                "path": relative,
                "validation": "PASS",
            }
        )
    for gsm, items in by_gsm.items():
        write_tsv_atomic(
            root / "metadata/download_manifests" / f"{gsm}.tsv",
            manifest_fields,
            items,
        )
    print(f"SUPPLEMENT files={sum(len(items) for items in by_gsm.values())} type={file_type}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
