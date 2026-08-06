#!/usr/bin/env python3
"""Atomic state, resume-identity, and publish helpers for download_run.sh."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path


def now() -> str:
    return datetime.now().astimezone().isoformat()


def read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Invalid JSON state {path}: {exc}")
    if not isinstance(value, dict):
        raise SystemExit(f"Invalid JSON object {path}")
    return value


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    with temp.open("w") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)


def digest(path: Path) -> str:
    value = hashlib.md5()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            value.update(chunk)
    return value.hexdigest()


def fingerprint(args: argparse.Namespace) -> int:
    payload = {
        "source": args.source,
        "urls": args.urls,
        "bytes": args.bytes,
        "md5": args.md5,
        "roles": args.roles,
        "final_product": args.final_product,
    }
    data = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    print(hashlib.sha256(data).hexdigest())
    return 0


def update(args: argparse.Namespace) -> int:
    path = args.path
    state = read_json(path)
    if state.get("source_fingerprint") not in (None, args.fingerprint):
        previous = path.with_name(
            f"{path.stem}.{datetime.now().astimezone().strftime('%Y%m%dT%H%M%S%f')}.stale.json"
        )
        os.replace(path, previous)
        state = {}
    state.setdefault("run", args.run)
    state.setdefault("source_fingerprint", args.fingerprint)
    state.setdefault("created_at", now())
    state.setdefault("attempt_count", 0)
    state.setdefault("resume_count", 0)
    state.setdefault("error_counts", {})
    state["updated_at"] = now()
    if args.phase is not None:
        state["phase"] = args.phase
    if args.status is not None:
        state["status"] = args.status
    if args.attempt_delta:
        state["attempt_count"] += args.attempt_delta
    if args.resume_delta:
        state["resume_count"] += args.resume_delta
    if args.error_class:
        key = args.error_key or args.error_class
        state["error_class"] = args.error_class
        state["last_error"] = args.message or ""
        state["error_counts"][key] = state["error_counts"].get(key, 0) + 1
        state["same_error_count"] = state["error_counts"][key]
    elif args.clear_error:
        state.pop("error_class", None)
        state.pop("last_error", None)
        state["same_error_count"] = 0
    if args.bytes_resumed is not None:
        state["bytes_resumed"] = args.bytes_resumed
    write_json(path, state)
    if args.print_field:
        value = state.get(args.print_field, "")
        print(value if not isinstance(value, (dict, list)) else json.dumps(value))
    return 0


def get_field(args: argparse.Namespace) -> int:
    value = read_json(args.path).get(args.field, args.default)
    print(value if not isinstance(value, (dict, list)) else json.dumps(value))
    return 0


def resume_check(args: argparse.Namespace) -> int:
    current = {
        "source_fingerprint": args.fingerprint,
        "url": args.url,
        "role": args.role,
        "expected_bytes": args.expected_bytes,
        "expected_md5": args.expected_md5,
        "etag": args.etag,
        "last_modified": args.last_modified,
        "remote_bytes": args.remote_bytes,
    }
    previous = read_json(args.path)
    if previous:
        fixed = (
            "source_fingerprint",
            "url",
            "role",
            "expected_bytes",
            "expected_md5",
        )
        if any(previous.get(key, "") != current[key] for key in fixed):
            return 10
        for key in ("etag", "last_modified", "remote_bytes"):
            if previous.get(key) and current[key] and previous[key] != current[key]:
                return 10
        current = {**previous, **{k: v for k, v in current.items() if v}}
    current["checked_at"] = now()
    write_json(args.path, current)
    return 0


def publish(args: argparse.Namespace) -> int:
    journal = read_json(args.journal)
    if journal.get("source_fingerprint") != args.fingerprint:
        raise SystemExit("Publish journal source fingerprint mismatch")
    items = journal.get("files")
    if not isinstance(items, list) or not items:
        raise SystemExit("Publish journal has no files")
    for item in items:
        staged = Path(item["staged"])
        final = Path(item["final"])
        expected_md5 = item["md5"]
        expected_bytes = int(item["bytes"])
        candidate = staged if staged.is_file() else final
        if not candidate.is_file():
            raise SystemExit(f"Publish recovery missing both paths for {final}")
        if candidate.stat().st_size != expected_bytes or digest(candidate) != expected_md5:
            raise SystemExit(f"Publish recovery integrity mismatch for {candidate}")
        if staged.is_file():
            final.parent.mkdir(parents=True, exist_ok=True)
            if final.exists():
                if final.stat().st_size != expected_bytes or digest(final) != expected_md5:
                    raise SystemExit(f"Refusing to replace differing final file {final}")
                staged.unlink()
            else:
                os.replace(staged, final)
        print(final)
    journal["published_at"] = journal.get("published_at") or now()
    write_json(args.journal, journal)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)

    command = commands.add_parser("fingerprint")
    for name in ("source", "urls", "bytes", "md5", "roles", "final-product"):
        command.add_argument(f"--{name}", required=True)
    command.set_defaults(function=fingerprint)

    command = commands.add_parser("update")
    command.add_argument("--path", required=True, type=Path)
    command.add_argument("--run", required=True)
    command.add_argument("--fingerprint", required=True)
    command.add_argument("--phase")
    command.add_argument("--status")
    command.add_argument("--attempt-delta", type=int, default=0)
    command.add_argument("--resume-delta", type=int, default=0)
    command.add_argument("--bytes-resumed", type=int)
    command.add_argument("--error-class")
    command.add_argument("--error-key")
    command.add_argument("--message")
    command.add_argument("--clear-error", action="store_true")
    command.add_argument("--print-field")
    command.set_defaults(function=update)

    command = commands.add_parser("get")
    command.add_argument("--path", required=True, type=Path)
    command.add_argument("--field", required=True)
    command.add_argument("--default", default="")
    command.set_defaults(function=get_field)

    command = commands.add_parser("resume-check")
    command.add_argument("--path", required=True, type=Path)
    command.add_argument("--fingerprint", required=True)
    for name in (
        "url",
        "role",
        "expected-bytes",
        "expected-md5",
        "etag",
        "last-modified",
        "remote-bytes",
    ):
        command.add_argument(f"--{name}", default="")
    command.set_defaults(function=resume_check)

    command = commands.add_parser("publish")
    command.add_argument("--journal", required=True, type=Path)
    command.add_argument("--fingerprint", required=True)
    command.set_defaults(function=publish)
    args = parser.parse_args()
    return args.function(args)


if __name__ == "__main__":
    sys.exit(main())
