#!/usr/bin/env python3
"""Probe both NCBI source buckets and the full-quality SRA ODP object."""

from __future__ import annotations

import argparse
import csv
import json
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

FIELDS = ["srr", "source", "provenance", "status", "url", "bytes", "md5", "roles", "evidence"]
SOURCE_BUCKETS = ("sra-pub-src-1", "sra-pub-src-2")


def fetch(url: str, method: str = "GET") -> tuple[int, bytes, dict[str, str]]:
    request = urllib.request.Request(url, method=method, headers={"User-Agent": "download-geo-assay/1"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, response.read(), dict(response.headers.items())
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(), dict(exc.headers.items())


def source_objects(run: str, bucket: str, xml_bytes: bytes) -> list[tuple[str, str, str]]:
    root = ET.fromstring(xml_bytes)
    namespace = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
    objects: list[tuple[str, str, str]] = []
    for content in root.findall("s3:Contents", namespace) + root.findall("Contents"):
        key = content.findtext("s3:Key", default="", namespaces=namespace) or content.findtext("Key", "")
        size = content.findtext("s3:Size", default="", namespaces=namespace) or content.findtext("Size", "")
        etag = (content.findtext("s3:ETag", default="", namespaces=namespace) or content.findtext("ETag", "")).strip('"')
        if key and size.isdigit() and int(size) > 0:
            url = f"https://{bucket}.s3.amazonaws.com/{urllib.parse.quote(key, safe='/')}"
            objects.append((url, size, etag if len(etag) == 32 and "-" not in etag else ""))
    return objects


def infer_roles(urls: list[str]) -> list[str]:
    names = [Path(urllib.parse.urlparse(url).path).name.upper() for url in urls]
    roles: list[str] = []
    for name in names:
        if "_R1" in name or "_1.F" in name:
            roles.append("R1")
        elif "_R2" in name or "_2.F" in name:
            roles.append("R2")
        elif name.endswith(".SRA"):
            roles.append("SRA")
        else:
            roles.append("OTHER")
    return roles


def probe_run(run: str, fixture: dict[str, object] | None = None) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for bucket in SOURCE_BUCKETS:
        if fixture is not None:
            objects = [tuple(item) for item in fixture.get(run, {}).get(bucket, [])]  # type: ignore[union-attr]
            status = 200
        else:
            query = urllib.parse.urlencode({"list-type": "2", "prefix": run})
            status, body, _ = fetch(f"https://{bucket}.s3.amazonaws.com/?{query}")
            objects = source_objects(run, bucket, body) if status == 200 else []
        if objects:
            urls, sizes, md5s = zip(*objects)
            rows.append(
                {
                    "srr": run, "source": "ncbi_source", "provenance": "AUTHOR_SUBMITTED",
                    "status": "available", "url": ";".join(urls), "bytes": ";".join(sizes),
                    "md5": ";".join(md5s), "roles": ";".join(infer_roles(list(urls))),
                    "evidence": f"{bucket} selective source bucket list status={status}",
                }
            )
        else:
            rows.append(
                {
                    "srr": run, "source": "ncbi_source", "provenance": "AUTHOR_SUBMITTED",
                    "status": "missing", "url": "", "bytes": "", "md5": "", "roles": "",
                    "evidence": f"{bucket} selective source bucket has no matching object; not evidence that full archive is absent",
                }
            )
    odp_url = f"https://sra-pub-run-odp.s3.amazonaws.com/sra/{run}/{run}"
    if fixture is not None:
        odp_size = str(fixture.get(run, {}).get("odp_bytes", ""))  # type: ignore[union-attr]
        odp_status = 200 if odp_size.isdigit() and int(odp_size) > 0 else 404
    else:
        odp_status, _, headers = fetch(odp_url, method="HEAD")
        odp_size = headers.get("Content-Length", "")
    rows.append(
        {
            "srr": run, "source": "ncbi_ondemand", "provenance": "ARCHIVE_NORMALIZED_SRA",
            "status": "available" if odp_status == 200 and odp_size.isdigit() and int(odp_size) > 0 else "missing",
            "url": odp_url if odp_status == 200 else "", "bytes": odp_size if odp_status == 200 else "",
            "md5": "", "roles": "SRA" if odp_status == 200 else "",
            "evidence": f"SRA ODP exact object HEAD status={odp_status}; full-quality normalized SRA",
        }
    )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--fixture", type=Path, help="offline JSON fixture")
    args = parser.parse_args()
    with args.expected.open(newline="") as handle:
        runs = sorted({row["srr"].rstrip("\r") for row in csv.DictReader(handle, delimiter="\t")})
    fixture = json.loads(args.fixture.read_text()) if args.fixture else None
    rows = [row for run in runs for row in probe_run(run, fixture)]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temp = args.output.with_suffix(args.output.suffix + ".tmp")
    with temp.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    temp.replace(args.output)
    print(f"Wrote {args.output}: {len(rows)} probe rows")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
