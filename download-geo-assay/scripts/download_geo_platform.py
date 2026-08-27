#!/usr/bin/env python3
"""Download minimal official GPL metadata, then use an official family fallback."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import os
import re
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path


def md5_bytes(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def fetch(url: str) -> tuple[bytes, str]:
    request = urllib.request.Request(url, headers={"User-Agent": "download-geo-assay/1"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read(), response.headers.get("Content-Type", "")


def validate(data: bytes, content_type: str, gpl: str) -> str:
    if not data:
        return "empty response"
    prefix = data[:2048].lower()
    if "text/html" in content_type.lower() or b"<html" in prefix or b"<!doctype html" in prefix:
        return "HTML/error page"
    try:
        inspected = gzip.decompress(data) if data[:2] == b"\x1f\x8b" else data
    except OSError:
        return "invalid gzip payload"
    text = inspected[:2_000_000].decode("utf-8", errors="ignore").upper()
    if not re.search(rf"(?m)^\^PLATFORM\s*=\s*{re.escape(gpl.upper())}\s*$", text):
        return f"content does not contain a {gpl} PLATFORM block"
    return ""


def platform_block(data: bytes, gpl: str) -> bytes:
    inspected = gzip.decompress(data) if data[:2] == b"\x1f\x8b" else data
    text = inspected.decode("utf-8", errors="replace")
    lines = text.splitlines()
    start = next(
        index
        for index, line in enumerate(lines)
        if re.fullmatch(rf"\^PLATFORM\s*=\s*{re.escape(gpl)}\s*", line, re.I)
    )
    end = len(lines)
    for index in range(start + 1, len(lines)):
        if lines[index].startswith("^"):
            end = index
            break
    return ("\n".join(lines[start:end]) + "\n").encode("utf-8")


def geo_bucket(accession: str) -> str:
    match = re.fullmatch(r"([A-Z]+)(\d+)", accession.upper())
    if not match:
        raise SystemExit(f"invalid GEO accession: {accession}")
    digits = match.group(2)
    prefix = digits[:-3] if len(digits) > 3 else ""
    return f"{match.group(1)}{prefix}nnn"


def write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    with temp.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--gpl", required=True)
    parser.add_argument("--gse")
    parser.add_argument("--primary-url", action="append", default=[])
    parser.add_argument("--fallback-url", action="append", default=[])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    gpl = args.gpl.upper()
    primary_urls = args.primary_url or [
        f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={gpl}&targ=self&form=text&view=full"
    ]
    if args.fallback_url:
        fallback_urls = args.fallback_url
    elif args.gse:
        gse = args.gse.upper()
        fallback_urls = [
            f"https://ftp.ncbi.nlm.nih.gov/geo/series/{geo_bucket(gse)}/{gse}/soft/{gse}_family.soft.gz"
        ]
    else:
        fallback_urls = [
            f"https://ftp.ncbi.nlm.nih.gov/geo/platforms/{geo_bucket(gpl)}/{gpl}/soft/{gpl}_family.soft.gz"
        ]
    root = args.root.resolve()
    output = args.output or root / "annotation/platform_annotation" / f"{gpl}.soft"
    if not output.is_absolute():
        output = root / output
    attempts: list[dict[str, str]] = []
    selected: tuple[bytes, str, str] | None = None
    for scope, urls in (("platform-only", primary_urls), ("official-family-fallback", fallback_urls)):
        for url in urls:
            try:
                data, content_type = fetch(url)
                error = validate(data, content_type, gpl)
            except (OSError, urllib.error.URLError) as exc:
                data, content_type, error = b"", "", f"fetch failed: {exc}"
            attempts.append(
                {
                    "gpl": gpl, "scope": scope, "url": url,
                    "status": "FAIL" if error else "PASS", "bytes": str(len(data)),
                    "md5": md5_bytes(data) if data else "", "message": error,
                    "checked_at": datetime.now().astimezone().isoformat(),
                }
            )
            if not error:
                selected = platform_block(data, gpl), scope, url
                break
        if selected:
            break
    audit = root / "reports/platform_download.tsv"
    fields = ["gpl", "scope", "url", "status", "bytes", "md5", "message", "checked_at"]
    audit.parent.mkdir(parents=True, exist_ok=True)
    temp = audit.with_name(audit.name + ".tmp")
    with temp.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(attempts)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, audit)
    if selected is None:
        raise SystemExit(f"{gpl}: platform-only 与官方 family fallback 均失败")
    write_atomic(output, selected[0])
    print(f"PLATFORM gpl={gpl} scope={selected[1]} output={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
