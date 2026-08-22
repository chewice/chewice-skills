#!/usr/bin/env python3
"""Download GEO supplementary raw files (CEL/IDAT) into raw or temporary GSM dirs."""

from __future__ import annotations

import argparse
import hashlib
import os
import sys
import tarfile
import urllib.request
import zipfile
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


RAW_SUFFIXES = (".cel", ".cel.gz", ".idat", ".idat.gz")


def is_raw_member(name: str) -> bool:
    lower = Path(name).name.lower()
    return any(lower.endswith(suffix) for suffix in RAW_SUFFIXES)


def record(
    items: list[dict[str, str]],
    *,
    gse: str,
    gsm: str,
    filename: str,
    url: str,
    file_type: str,
    path: Path,
    root: Path,
) -> None:
    items.append(
        {
            "gse": gse,
            "gsm": gsm,
            "filename": filename,
            "url": url,
            "file_type": file_type,
            "observed_bytes": str(path.stat().st_size),
            "observed_md5": md5(path),
            "path": path.relative_to(root).as_posix(),
            "validation": "PASS",
        }
    )


def verify_expected(row: dict[str, str], path: Path) -> None:
    expected_bytes = row.get("expected_bytes", "").strip()
    observed = path.stat().st_size
    if expected_bytes and expected_bytes.isdigit() and int(expected_bytes) != observed:
        raise SystemExit(
            f"byte mismatch {path.name}: expected {expected_bytes} observed {observed}"
        )
    expected_md5 = row.get("expected_md5", "").strip().lower()
    if expected_md5 and expected_md5 != md5(path):
        raise SystemExit(f"md5 mismatch {path.name}")


def extract_raw_members(archive: Path, directory: Path) -> list[Path]:
    extracted: list[Path] = []
    name = archive.name.lower()

    def take(member_name: str, reader) -> None:
        if not is_raw_member(member_name):
            return
        target = directory / Path(member_name).name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("wb") as handle:
            while chunk := reader.read(8 * 1024 * 1024):
                handle.write(chunk)
        extracted.append(target)

    if name.endswith(".zip"):
        with zipfile.ZipFile(archive) as bundle:
            for info in bundle.infolist():
                if info.is_dir():
                    continue
                with bundle.open(info) as reader:
                    take(info.filename, reader)
    elif name.endswith(".tar") or name.endswith(".tar.gz") or name.endswith(".tgz"):
        with tarfile.open(archive) as bundle:
            for info in bundle.getmembers():
                if not info.isfile():
                    continue
                reader = bundle.extractfile(info)
                if reader is None:
                    continue
                with reader:
                    take(info.name, reader)
    return extracted


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
        verify_expected(row, destination)
        if name.lower().endswith(".gz") and not name.lower().endswith(".tar.gz"):
            import gzip

            with gzip.open(destination, "rb") as handle:
                handle.read(1)
        items = by_gsm.setdefault(gsm, [])
        record(
            items,
            gse=row.get("gse", policy["gse"]),
            gsm=gsm,
            filename=name,
            url=row["url"],
            file_type=file_type,
            path=destination,
            root=root,
        )
        for extracted in extract_raw_members(destination, directory):
            record(
                items,
                gse=row.get("gse", policy["gse"]),
                gsm=gsm,
                filename=extracted.name,
                url=row["url"],
                file_type=file_type,
                path=extracted,
                root=root,
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
