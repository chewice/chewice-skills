#!/usr/bin/env python3
"""Download minimal official GPL metadata, with validated and bounded fallback."""

from __future__ import annotations

import argparse
import fcntl
import gzip
import http.client
import os
import re
import sys
import zlib
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from acquisition_runtime import ResourceLimitError, ResourceReservation, effective_config  # noqa: E402
from download_geo_supplement import download, md5  # noqa: E402
from project_layout import read_tsv, write_tsv_atomic  # noqa: E402

AUDIT_FIELDS = ["gpl", "scope", "url", "status", "bytes", "md5", "message", "checked_at", "content_type", "output_bytes", "output_md5"]


def geo_bucket(accession: str) -> str:
    match = re.fullmatch(r"([A-Z]+)(\d+)", accession.upper())
    if not match:
        raise ValueError(f"invalid GEO accession: {accession}")
    digits = match.group(2)
    return f"{match.group(1)}{digits[:-3] if len(digits) > 3 else ''}nnn"


def platform_lines(path: Path, gpl: str, maximum: int):
    """Scan to EOF so truncation after the platform block cannot hide in gzip."""
    with path.open("rb") as probe:
        compressed = probe.read(2) == b"\x1f\x8b"
    opener = gzip.open if compressed else open
    selected = seen = detail = table = table_closed = False
    total = 0
    with opener(path, "rb") as handle:
        while line := handle.readline(8 * 1024 * 1024 + 1):
            total += len(line)
            if total > maximum or len(line) > 8 * 1024 * 1024:
                raise ValueError("platform response exceeds bounded decoded size")
            text = line.decode("utf-8", errors="strict").rstrip("\r\n")
            if b"<html" in line[:2048].lower() or b"<!doctype html" in line[:2048].lower():
                raise ValueError("HTML/error page")
            if text.startswith("^"):
                if selected and table and not table_closed:
                    raise ValueError("incomplete platform table")
                selected = bool(re.fullmatch(rf"\^PLATFORM\s*=\s*{re.escape(gpl)}\s*", text, re.I))
                if selected and seen:
                    raise ValueError("duplicate target platform block")
                seen = seen or selected
            if selected:
                detail = detail or text.lower().startswith("!platform_")
                table = table or text.lower() == "!platform_table_begin"
                table_closed = table_closed or text.lower() == "!platform_table_end"
                yield (text + "\n").encode()
    if not seen or not detail:
        raise ValueError(f"response lacks complete {gpl} platform metadata")
    if table and not table_closed:
        raise ValueError("incomplete platform table")


def record_attempts(root: Path, gpl: str, attempts: list[dict[str, str]]) -> None:
    audit = root / "reports/platform_download.tsv"
    audit.parent.mkdir(parents=True, exist_ok=True)
    with (audit.parent / "platform_download.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        other = [row for row in read_tsv(audit) if row.get("gpl") != gpl]
        write_tsv_atomic(audit, AUDIT_FIELDS, other + attempts)


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
    if not re.fullmatch(r"GPL\d+", gpl):
        raise ValueError("invalid GPL accession")
    primary_urls = args.primary_url or [f"https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc={gpl}&targ=self&form=text&view=full"]
    if args.fallback_url:
        fallback_urls = args.fallback_url
    elif args.gse:
        gse = args.gse.upper()
        if not re.fullmatch(r"GSE\d+", gse):
            raise ValueError("invalid GSE accession")
        fallback_urls = [f"https://ftp.ncbi.nlm.nih.gov/geo/series/{geo_bucket(gse)}/{gse}/soft/{gse}_family.soft.gz"]
    else:
        fallback_urls = [f"https://ftp.ncbi.nlm.nih.gov/geo/platforms/{geo_bucket(gpl)}/{gpl}/soft/{gpl}_family.soft.gz"]
    root = args.root.resolve()
    output = args.output or root / "annotation/platform_annotation" / f"{gpl}.soft"
    if not output.is_absolute():
        output = root / output
    if not output.resolve().is_relative_to(root) or output.is_symlink():
        raise ValueError("platform output must be inside the project root")
    stage = root / "temporary/platform" / gpl
    stage.mkdir(parents=True, exist_ok=True)
    config = effective_config(root)
    maximum = int(config.get("platform_max_uncompressed_bytes", 2 * 1024**3))
    download_maximum = int(config["platform_max_download_bytes"]) if config.get("platform_max_download_bytes") else None
    unknown_maximum = int(config.get("platform_unknown_size_limit_bytes", 8 * 1024**2))
    if maximum <= 0 or unknown_maximum <= 0 or (download_maximum is not None and download_maximum <= 0):
        raise ValueError("platform size bounds must be positive")
    attempts = []
    with (stage / ".lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        for scope, urls in (("platform-only", primary_urls), ("official-family-fallback", fallback_urls)):
            for url in urls:
                attempt = {"gpl": gpl, "scope": scope, "url": url, "status": "FAIL", "bytes": "0", "md5": "", "message": "", "checked_at": datetime.now().astimezone().isoformat()}
                staged = stage / "response"
                extracted = stage / f"{gpl}.soft"
                try:
                    identity = download(root, url, staged, maximum_bytes=download_maximum, unknown_size_limit=unknown_maximum)
                    attempt.update({"bytes": str(staged.stat().st_size), "md5": md5(staged), "content_type": identity.get("content_type", "")})
                    if "text/html" in identity.get("content_type", "").lower():
                        raise ValueError("HTML/error page")
                    length = sum(len(line) for line in platform_lines(staged, gpl, maximum))
                    with ResourceReservation(root, f"platform-{gpl}", length, length, paths=(extracted,), temporary_paths=(extracted,)) as reservation:
                        with extracted.open("wb") as handle:
                            for line in platform_lines(staged, gpl, maximum):
                                reservation.check()
                                handle.write(line)
                            handle.flush()
                            os.fsync(handle.fileno())
                        reservation.check()
                        digest = md5(extracted)
                        output.parent.mkdir(parents=True, exist_ok=True)
                        os.replace(extracted, output)
                    attempt.update({"status": "PASS", "output_bytes": str(length), "output_md5": digest})
                except (OSError, ValueError, EOFError, ResourceLimitError, http.client.HTTPException, zlib.error) as exc:
                    attempt["message"] = f"{type(exc).__name__}: {exc}"
                attempts.append(attempt)
                record_attempts(root, gpl, attempts)
                if attempt["status"] == "PASS":
                    for name in ("response", "response.part", "response.part.resume.json"):
                        (stage / name).unlink(missing_ok=True)
                    print(f"PLATFORM gpl={gpl} scope={scope} output={output}")
                    return 0
    raise ValueError(f"{gpl}: platform-only 与官方 family fallback 均失败")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        raise SystemExit(str(error))
