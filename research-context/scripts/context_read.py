#!/usr/bin/env python3
"""Read a bounded UTF-8 text window without changing the source file."""

import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path, help="UTF-8 context or research record")
    parser.add_argument("--start", type=int, default=0, help="zero-based character offset")
    parser.add_argument("--chars", type=int, default=2000, help="maximum content characters")
    parser.add_argument("--expect-sha256", help="source fingerprint from the first window")
    args = parser.parse_args()

    if args.start < 0 or args.chars < 1:
        parser.error("--start must be nonnegative and --chars must be positive")
    if args.start > 0 and not args.expect_sha256:
        parser.error("--start > 0 requires --expect-sha256 from the first window")

    try:
        path = args.path.resolve()
        raw = path.read_bytes()
        source = raw.decode("utf-8")
    except (OSError, UnicodeError, RuntimeError) as exc:
        parser.error(str(exc))

    digest = hashlib.sha256(raw).hexdigest()
    if args.expect_sha256 and args.expect_sha256.lower() != digest:
        parser.error("source fingerprint changed; recheck the source before resuming")
    if args.start > len(source):
        parser.error("--start is past the end of the source")

    end = min(args.start + args.chars, len(source))
    result = {
        "path": str(path),
        "sha256": digest,
        "total_chars": len(source),
        "total_lines": source.count("\n") + int(bool(source) and not source.endswith("\n")),
        "start": args.start,
        "end": end,
        "text": source[args.start:end],
        "next_start": end if end < len(source) else None,
        "eof": end == len(source),
        "window_complete": True,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
