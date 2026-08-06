#!/usr/bin/env python3
"""Probe expected runs against NGDC GSA/INSDC download endpoints."""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path


FIELDS = [
    "gse",
    "gsm",
    "srx",
    "srr",
    "ngdc_browse_url",
    "ngdc_run_page",
    "ngdc_status",
    "ngdc_url",
    "ngdc_file_type",
    "ngdc_bytes",
    "expected_spots",
    "probe_attempts",
    "probe_message",
]


def refresh_report_from_output(output: Path) -> None:
    reporter = Path(__file__).with_name("build_report.py")
    root = output.resolve().parent.parent
    if output.parent.name == "reports" and reporter.is_file():
        subprocess.run(
            [sys.executable, str(reporter), "--root", str(root)],
            check=False,
        )


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def candidate_urls(run: str, partitions: list[str]) -> list[str]:
    if not re.fullmatch(r"[SED]RR\d+", run):
        return []
    digits = re.search(r"\d+", run)
    assert digits is not None
    bucket = str(int(digits.group()) // 1_000_000)
    block = run[:-3]
    urls = []
    for partition in partitions:
        base = (
            f"https://download2.cncb.ac.cn/{partition}/SRA/"
            f"{bucket}/{block}/{run}"
        )
        urls.extend((f"{base}/{run}", f"{base}/{run}.sra"))
    return urls


def curl_head(url: str, timeout: int) -> tuple[str, int, str]:
    command = [
        "curl",
        "--proxy",
        "",
        "-k",
        "-sSIL",
        "--connect-timeout",
        str(timeout),
        "--max-time",
        str(timeout),
        "-w",
        "\n__HTTP__:%{http_code}\n",
        url,
    ]
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    text = result.stdout + "\n" + result.stderr
    http_matches = re.findall(r"__HTTP__:(\d+)", text)
    status_code = int(http_matches[-1]) if http_matches else 0
    lengths = re.findall(r"(?im)^content-length:\s*(\d+)\s*$", text)
    size = int(lengths[-1]) if lengths else 0
    if result.returncode == 0 and 200 <= status_code < 400:
        return ("available" if size > 0 else "invalid", size, f"http={status_code}")
    if status_code in (404, 410):
        return "missing", 0, f"http={status_code}"
    return "unreachable", 0, f"http={status_code} curl={result.returncode}"


def load_fixture(path: Path | None) -> dict[str, dict[str, str]]:
    if path is None:
        return {}
    return {row["srr"]: row for row in read_tsv(path)}


def probe_one(
    row: dict[str, str],
    partitions: list[str],
    attempts: int,
    timeout: int,
    fixture: dict[str, dict[str, str]],
) -> dict[str, str]:
    run = row["srr"].strip()
    if run in fixture:
        item = fixture[run]
        return {
            "gse": row["gse"],
            "gsm": row["gsm"],
            "srx": row.get("srx", ""),
            "srr": run,
            "ngdc_browse_url": "https://ngdc.cncb.ac.cn/gsa/browse/",
            "ngdc_run_page": item.get("ngdc_run_page", ""),
            "ngdc_status": item["ngdc_status"],
            "ngdc_url": item.get("ngdc_url", ""),
            "ngdc_file_type": item.get("ngdc_file_type", "sra"),
            "ngdc_bytes": item.get("ngdc_bytes", ""),
            "expected_spots": row.get("expected_spots", ""),
            "probe_attempts": "fixture",
            "probe_message": item.get("probe_message", "offline fixture"),
        }

    explicit_url = row.get("ngdc_url", "").strip()
    urls = [explicit_url] if explicit_url else candidate_urls(run, partitions)
    if not urls:
        return {
            "gse": row["gse"],
            "gsm": row["gsm"],
            "srx": row.get("srx", ""),
            "srr": run,
            "ngdc_browse_url": "https://ngdc.cncb.ac.cn/gsa/browse/",
            "ngdc_run_page": row.get("ngdc_run_page", ""),
            "ngdc_status": "not_probed",
            "ngdc_url": "",
            "ngdc_file_type": "",
            "ngdc_bytes": "",
            "expected_spots": row.get("expected_spots", ""),
            "probe_attempts": "0",
            "probe_message": "native/non-SRR run requires an explicit NGDC URL",
        }

    saw_missing = False
    saw_invalid = False
    messages: list[str] = []
    count = 0
    for attempt in range(1, attempts + 1):
        for url in urls:
            count += 1
            status, size, message = curl_head(url, timeout)
            messages.append(f"{Path(url).name}:{message}")
            if status == "available":
                return {
                    "gse": row["gse"],
                    "gsm": row["gsm"],
                    "srx": row.get("srx", ""),
                    "srr": run,
                    "ngdc_browse_url": "https://ngdc.cncb.ac.cn/gsa/browse/",
                    "ngdc_run_page": row.get("ngdc_run_page", ""),
                    "ngdc_status": "available",
                    "ngdc_url": url,
                    "ngdc_file_type": (
                        "sra" if url.lower().endswith(".sra") or run.startswith("SRR") else "other"
                    ),
                    "ngdc_bytes": str(size),
                    "expected_spots": row.get("expected_spots", ""),
                    "probe_attempts": str(count),
                    "probe_message": message,
                }
            saw_missing |= status == "missing"
            saw_invalid |= status == "invalid"
        if saw_missing and not saw_invalid:
            break

    final_status = "invalid" if saw_invalid else ("missing" if saw_missing else "unreachable")
    return {
        "gse": row["gse"],
        "gsm": row["gsm"],
        "srx": row.get("srx", ""),
        "srr": run,
        "ngdc_browse_url": "https://ngdc.cncb.ac.cn/gsa/browse/",
        "ngdc_run_page": row.get("ngdc_run_page", ""),
        "ngdc_status": final_status,
        "ngdc_url": "",
        "ngdc_file_type": "",
        "ngdc_bytes": "",
        "expected_spots": row.get("expected_spots", ""),
        "probe_attempts": str(count),
        "probe_message": "; ".join(messages[-4:]),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--fixture", type=Path)
    parser.add_argument(
        "--partitions",
        default="INSDC,INSDC1,INSDC2,INSDC3,INSDC4,INSDC5,INSDC6,INSDC7,INSDC8,INSDC9,INSDC10",
    )
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--jobs", type=int, default=8)
    args = parser.parse_args()

    rows = read_tsv(args.input)
    required = {"gse", "gsm", "srr", "expected_spots"}
    if not rows or not required.issubset(rows[0]):
        raise SystemExit(f"{args.input} must contain {sorted(required)}")
    if len({row["srr"] for row in rows}) != len(rows):
        raise SystemExit("Duplicate run accessions in expected-runs input")
    fixture = load_fixture(args.fixture)
    partitions = [value.strip() for value in args.partitions.split(",") if value.strip()]

    with ThreadPoolExecutor(max_workers=args.jobs) as executor:
        output_rows = list(
            executor.map(
                lambda item: probe_one(
                    item, partitions, args.attempts, args.timeout, fixture
                ),
                rows,
            )
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temp = args.output.with_suffix(args.output.suffix + ".tmp")
    with temp.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(output_rows)
    temp.replace(args.output)

    counts = {status: 0 for status in ("available", "missing", "invalid", "unreachable", "not_probed")}
    for row in output_rows:
        counts[row["ngdc_status"]] += 1
    print(f"expected_runs\t{len(output_rows)}")
    for status, count in counts.items():
        print(f"ngdc_{status}_runs\t{count}")
    refresh_report_from_output(args.output)


if __name__ == "__main__":
    main()
