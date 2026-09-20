#!/usr/bin/env python3
"""Download and verify GEO CEL/IDAT objects before publishing a GSM transaction."""

from __future__ import annotations

import argparse
import fcntl
import gzip
import hashlib
import http.client
import json
import os
import re
import shutil
import sys
import tarfile
import urllib.error
import zipfile
import zlib
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from acquisition_runtime import ResourceLimitError, ResourceReservation, open_url  # noqa: E402
from project_layout import (  # noqa: E402
    published_raw_dir, read_storage_policies, read_tsv, retain_raw_for_gsm,
    write_tsv_atomic,
)

CHUNK = 1024 * 1024
RAW_SUFFIXES = (".cel", ".cel.gz", ".idat", ".idat.gz")
FIELDS = [
    "gse", "gsm", "filename", "url", "file_type", "observed_bytes",
    "observed_md5", "path", "validation", "integrity_methods", "response_bytes",
    "etag", "last_modified", "expected_bytes", "expected_md5", "member_of",
    "member_name", "source_fingerprint",
]


class UnverifiedDownload(ValueError):
    """A received object lacks enough independent integrity evidence to publish."""


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    with temp.open("w") as handle:
        json.dump(value, handle, sort_keys=True)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, path)


def md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(CHUNK), b""):
            digest.update(chunk)
    return digest.hexdigest()


def supplement_source_fingerprint(row: dict[str, str]) -> str:
    fields = ("gse", "gsm", "url", "filename", "file_type", "expected_bytes", "expected_md5")
    payload = {field: row.get(field, "").strip() for field in fields}
    payload["expected_md5"] = payload["expected_md5"].lower()
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def resolve_file_type(requested: str | None, policy: dict[str, str], rows: list[dict[str, str]]) -> str:
    if requested:
        return requested
    raw = policy.get("raw_file_type", "")
    if raw in {"CEL", "IDAT"}:
        return raw
    listed = {row.get("file_type", "").upper() for row in rows if row.get("file_type")}
    if listed == {"CEL"} or listed == {"IDAT"}:
        return listed.pop()
    raise ValueError("需要 --file-type CEL|IDAT 或唯一 storage_policy/supplement_files.file_type")


def safe_name(value: str) -> str:
    if not value or value in {".", ".."} or Path(value).name != value or "\\" in value:
        raise ValueError(f"unsafe supplement filename: {value!r}")
    return value


def positive_size(value: str) -> int | None:
    if not value:
        return None
    if not value.isdigit() or int(value) <= 0:
        raise ValueError("invalid/missing positive byte count")
    return int(value)


def remote_identity(response, url: str) -> dict[str, str]:
    return {
        "url": url, "response_bytes": response.headers.get("Content-Length", ""),
        "resolved_url": response.geturl(),
        "etag": response.headers.get("ETag", ""),
        "last_modified": response.headers.get("Last-Modified", ""),
        "content_type": response.headers.get("Content-Type", ""),
    }


def validator(identity: dict[str, str]) -> str:
    etag = identity.get("etag", "")
    return etag if etag and not etag.startswith("W/") else identity.get("last_modified", "")


def download(root: Path, url: str, destination: Path, row: dict[str, str] | None = None, *, maximum_bytes: int | None = None, unknown_size_limit: int | None = None) -> dict[str, str]:
    """Fetch into staging, retaining only identity-bound partials for Range resume."""
    row = row or {}
    expected = positive_size(row.get("expected_bytes", "").strip())
    expected_md5 = row.get("expected_md5", "").strip().lower()
    if expected_md5 and not re.fullmatch(r"[0-9a-f]{32}", expected_md5):
        raise ValueError("invalid expected MD5")
    destination.parent.mkdir(parents=True, exist_ok=True)
    part = destination.with_name(destination.name + ".part")
    sidecar = part.with_name(part.name + ".resume.json")
    contract = {"url": url, "expected_bytes": str(expected or ""), "expected_md5": expected_md5}
    previous = {}
    if sidecar.is_file():
        try:
            previous = json.loads(sidecar.read_text())
        except (OSError, ValueError):
            pass
    identity = {}
    try:
        with open_url(root, url, method="HEAD", headers={"Accept-Encoding": "identity"}, timeout=40) as response:
            identity = remote_identity(response, url)
    except (urllib.error.URLError, OSError, http.client.HTTPException):
        # GET may work when HEAD is unsupported; that path starts a fresh transfer.
        pass
    total = positive_size(identity.get("response_bytes", ""))
    if maximum_bytes is not None and (maximum_bytes <= 0 or (total and total > maximum_bytes)):
        raise ResourceLimitError("response exceeds configured download size bound")
    if total and expected and total != expected:
        raise ValueError("response Content-Length differs from expected_bytes")
    offset = 0
    same_identity = (previous.get("contract") == contract and identity
            and validator(identity) and validator(identity) == validator(previous)
            and identity.get("resolved_url") == previous.get("resolved_url")
            and identity.get("response_bytes") == previous.get("response_bytes"))
    if (same_identity and destination.is_file() and total == destination.stat().st_size
            and previous.get("completed_md5") == md5(destination)):
        return {**identity, "resume_count": "0"}
    if part.is_file() and same_identity:
        offset = part.stat().st_size
        if not total or offset > total:
            offset = 0
    if total and offset == total:
        os.replace(part, destination)
        atomic_json(sidecar, {**identity, "contract": contract, "completed_md5": md5(destination)})
        return {**identity, "resume_count": "1"}
    headers = {"Accept-Encoding": "identity"}
    if offset:
        headers.update({"Range": f"bytes={offset}-", "If-Range": validator(identity)})
    with open_url(root, url, headers=headers, timeout=40) as response:
        received = remote_identity(response, url)
        status = getattr(response, "status", None) or response.getcode()
        length = positive_size(received.get("response_bytes", ""))
        if offset and status == 206:
            match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+)", response.headers.get("Content-Range", ""))
            if not match or tuple(map(int, match.groups())) != (offset, total - 1, total):
                raise ValueError("resume Content-Range does not match partial and remote size")
            if (length != total - offset or validator(received) != validator(identity)
                    or received.get("resolved_url") != identity.get("resolved_url")):
                raise ValueError("resume length or remote validator changed")
            received["response_bytes"] = str(total)
        elif status == 200:
            offset = 0  # A server ignoring Range must never append its full body.
            total = length
        else:
            raise ValueError(f"unexpected download response status {status}")
        if expected and total and total != expected:
            raise ValueError("response Content-Length differs from expected_bytes")
        if not total and unknown_size_limit is None:
            raise UnverifiedDownload("UNVERIFIED: response has no Content-Length")
        if maximum_bytes is not None and total and total > maximum_bytes:
            raise ResourceLimitError("response exceeds configured download size bound")
        bound = total or min(unknown_size_limit, maximum_bytes or unknown_size_limit)
        identity = received
        paths = (part, destination)
        peak = bound + (destination.stat().st_size if destination.exists() else 0)
        with ResourceReservation(
            root, f"supplement-{hashlib.sha256(url.encode()).hexdigest()[:20]}",
            project_bytes=peak, temporary_bytes=peak, paths=paths, temporary_paths=paths,
        ) as reservation:
            with part.open("ab" if offset else "wb") as handle:
                if not offset:
                    handle.flush()
                    os.fsync(handle.fileno())
                # Never bind old partial bytes to a new validator before truncating.
                atomic_json(sidecar, {**identity, "contract": contract})
                observed = offset
                while chunk := response.read(min(CHUNK, bound - observed + 1)):
                    observed += len(chunk)
                    if observed > bound:
                        raise ValueError("response exceeds declared or configured size bound")
                    reservation.check()
                    handle.write(chunk)
                    handle.flush()
                    reservation.check()
                os.fsync(handle.fileno())
            if total and observed != total:
                raise ValueError(f"short HTTP body: expected {total}, received {observed}")
            os.replace(part, destination)
            atomic_json(sidecar, {**identity, "contract": contract, "completed_md5": md5(destination)})
    return {**identity, "resume_count": "1" if offset else "0"}


def verify_expected(row: dict[str, str], path: Path) -> list[str]:
    expected = positive_size(row.get("expected_bytes", "").strip())
    if expected is not None and path.stat().st_size != expected:
        raise ValueError(f"byte mismatch {path.name}")
    expected_md5 = row.get("expected_md5", "").strip().lower()
    methods = []
    if expected_md5:
        if not re.fullmatch(r"[0-9a-f]{32}", expected_md5) or md5(path) != expected_md5:
            raise ValueError(f"md5 mismatch {path.name}")
        methods.append("provider_md5")
    return methods


def gzip_test(path: Path) -> None:
    with gzip.open(path, "rb") as handle:
        while handle.read(CHUNK):
            pass


def raw_header(path: Path) -> None:
    opener = gzip.open if path.name.lower().endswith(".gz") else open
    with opener(path, "rb") as handle:
        prefix = handle.read(2048)
    if not prefix or b"<html" in prefix.lower() or b"<!doctype html" in prefix.lower():
        raise ValueError(f"empty or HTML raw supplement: {path.name}")
    # These signatures cover text CEL, XDA CEL, Calvin CEL and Illumina IDAT.
    lower = path.name.lower().removesuffix(".gz")
    if lower.endswith(".cel") and not (prefix.startswith(b"[CEL]") or prefix[:4] == b"\x40\x00\x00\x00" or prefix[:2] == b"\x3b\x01"):
        raise ValueError(f"unrecognized CEL header: {path.name}")
    if lower.endswith(".idat") and not prefix.startswith(b"IDAT"):
        raise ValueError(f"unrecognized IDAT header: {path.name}")


def archive_members(archive: Path, file_type: str) -> list[tuple[str, str, int]]:
    """Validate the entire container and reject member aliases before extracting."""
    members = []
    names = set()
    expected_suffixes = (f".{file_type.lower()}", f".{file_type.lower()}.gz")
    is_zip = archive.name.lower().endswith(".zip")
    bundle = zipfile.ZipFile(archive) if is_zip else tarfile.open(archive)
    with bundle:
        entries = bundle.infolist() if is_zip else bundle.getmembers()
        for entry in entries:
            name = entry.filename if is_zip else entry.name
            parts = PurePosixPath(name).parts
            if not name or name.startswith("/") or ".." in parts or "\\" in name:
                raise ValueError(f"unsafe archive member: {name!r}")
            if is_zip:
                if (entry.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ValueError("archive symlinks are unsupported")
                if entry.is_dir():
                    continue
                size = entry.file_size
                reader = bundle.open(entry)
            else:
                if entry.isdir():
                    continue
                if not entry.isfile():
                    raise ValueError("archive links and special members are unsupported")
                size = entry.size
                reader = bundle.extractfile(entry)
            observed = 0
            with reader:
                while chunk := reader.read(CHUNK):
                    observed += len(chunk)
            if observed != size:
                raise ValueError(f"truncated archive member: {name}")
            if name.lower().endswith(RAW_SUFFIXES):
                if not name.lower().endswith(expected_suffixes):
                    raise ValueError("archive contains a different raw file type")
                base = safe_name(PurePosixPath(name).name)
                if base.casefold() in names or base.casefold() == archive.name.casefold():
                    raise ValueError(f"archive basename collision: {base}")
                names.add(base.casefold())
                members.append((name, base, size))
    if not members:
        raise ValueError("archive contains no requested raw members")
    if not is_zip:
        opener = gzip.open if archive.name.lower().endswith((".tar.gz", ".tgz")) else open
        tail = b""
        total = 0
        with opener(archive, "rb") as handle:
            while chunk := handle.read(CHUNK):
                total += len(chunk)
                tail = (tail + chunk)[-1024:]
        if total % 512 or tail != b"\0" * 1024:
            raise ValueError("tar archive lacks a complete end marker")
    return members


def validate_and_extract(root: Path, row: dict[str, str], staged: Path, file_type: str, identity: dict[str, str]) -> tuple[list[tuple[Path, str]], list[str]]:
    methods = verify_expected(row, staged)
    if not staged.stat().st_size:
        raise ValueError("empty supplement")
    if identity.get("response_bytes") != str(staged.stat().st_size):
        raise ValueError("download size differs from response length")
    methods.append("http_length")
    name = staged.name.lower()
    extracted = []
    if name.endswith((".zip", ".tar", ".tar.gz", ".tgz")):
        members = archive_members(staged, file_type)
        directory = staged.parent / "members"
        expanded = sum(size for _, _, size in members)
        with ResourceReservation(root, f"extract-{supplement_source_fingerprint(row)[:20]}", expanded, expanded, paths=(directory,), temporary_paths=(directory,)) as reservation:
            directory.mkdir(exist_ok=True)
            is_zip = name.endswith(".zip")
            bundle = zipfile.ZipFile(staged) if is_zip else tarfile.open(staged)
            with bundle:
                for member, base, size in members:
                    reservation.check()
                    target = directory / base
                    reader = bundle.open(member) if is_zip else bundle.extractfile(member)
                    with reader, target.open("wb") as output:
                        while chunk := reader.read(CHUNK):
                            reservation.check()
                            output.write(chunk)
                        output.flush()
                        os.fsync(output.fileno())
                    if target.stat().st_size != size:
                        raise ValueError(f"truncated extracted member: {member}")
                    if base.lower().endswith(".gz"):
                        gzip_test(target)
                    raw_header(target)
                    reservation.check()
                    extracted.append((target, member))
        methods.append("archive_full")
    else:
        if not name.endswith((f".{file_type.lower()}", f".{file_type.lower()}.gz")):
            raise ValueError("raw filename does not match selected file type")
        if name.endswith(".gz"):
            gzip_test(staged)
            methods.append("gzip_crc")
        raw_header(staged)
        if "provider_md5" not in methods and "gzip_crc" not in methods:
            raise UnverifiedDownload("UNVERIFIED: uncompressed CEL/IDAT needs a provider MD5 or complete format validation")
    return extracted, methods


def reusable(root: Path, row: dict[str, str], records: list[dict[str, str]]) -> bool:
    if not records:
        return False
    for record in records:
        name = Path(record.get("path", ""))
        if name.is_absolute() or ".." in name.parts:
            return False
        path = root / name
        if (record.get("validation") != "PASS" or not record.get("integrity_methods")
                or record.get("source_fingerprint") != supplement_source_fingerprint(row)
                or not path.is_file() or path.is_symlink()
                or str(path.stat().st_size) != record.get("observed_bytes")
                or md5(path) != record.get("observed_md5")):
            return False
    return sum(not item.get("member_of") for item in records) == 1


def recover_publish(root: Path, journal: Path) -> None:
    if not journal.is_file():
        return
    transaction = json.loads(journal.read_text())
    if transaction.get("state") != "committed":
        for item in reversed(transaction["files"]):
            destination, backup = root / item["destination"], root / item["backup"]
            if backup.exists():
                os.replace(backup, destination)
            elif not item["existed"]:
                destination.unlink(missing_ok=True)
        manifest = root / transaction["manifest"]
        if transaction["manifest_before"] is None:
            manifest.unlink(missing_ok=True)
        else:
            temp = manifest.with_name(manifest.name + ".tmp")
            temp.write_text(transaction["manifest_before"])
            os.replace(temp, manifest)
    for item in transaction["files"]:
        (root / item["backup"]).unlink(missing_ok=True)
    journal.unlink()


def publish(root: Path, stage: Path, directory: Path, prepared: list[tuple[Path, dict[str, str]]], manifest: Path, records: list[dict[str, str]]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    journal = stage / "publish.json"
    files = []
    for index, (source, record) in enumerate(prepared):
        destination = root / record["path"]
        if destination.is_symlink() or not destination.resolve().is_relative_to(root):
            raise ValueError("unsafe supplement publish path")
        files.append({"source": source.relative_to(root).as_posix(), "destination": record["path"], "backup": (stage / f"backup-{index}").relative_to(root).as_posix(), "existed": destination.exists()})
    transaction = {"state": "publishing", "files": files, "manifest": manifest.relative_to(root).as_posix(), "manifest_before": manifest.read_text() if manifest.exists() else None}
    atomic_json(journal, transaction)
    try:
        for item in files:
            source, destination, backup = (root / item[key] for key in ("source", "destination", "backup"))
            if item["existed"]:
                os.replace(destination, backup)
            os.replace(source, destination)
        write_tsv_atomic(manifest, FIELDS, records)
        transaction["state"] = "committed"
        atomic_json(journal, transaction)
    except BaseException:
        recover_publish(root, journal)
        raise
    recover_publish(root, journal)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--input", type=Path, help="supplement_files.tsv")
    parser.add_argument("--file-type", choices=("CEL", "IDAT"))
    parser.add_argument("--gsm", help="Download only one GSM")
    args = parser.parse_args()
    root = args.root.resolve()
    policies = read_storage_policies(root)
    policy = next((item for item in policies if item.get("raw_file_type") in {"CEL", "IDAT"}), policies[0])
    rows = read_tsv(args.input or root / "metadata/supplement_files.tsv")
    if args.gsm:
        rows = [row for row in rows if row.get("gsm") == args.gsm]
    if not rows:
        raise ValueError("empty supplement_files selection")
    file_type = resolve_file_type(args.file_type, policy, rows)
    by_gsm = {}
    for row in rows:
        if not re.fullmatch(r"GSM\d+", row.get("gsm", "")):
            raise ValueError("invalid GSM")
        by_gsm.setdefault(row["gsm"], []).append(row)
    failures = []
    for gsm, members in by_gsm.items():
        stage = root / "temporary" / gsm / "supplement"
        stage.mkdir(parents=True, exist_ok=True)
        manifest = root / "metadata/download_manifests" / f"{gsm}.tsv"
        with (stage / ".lock").open("a+") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            recover_publish(root, stage / "publish.json")
            records = read_tsv(manifest)
            directory = published_raw_dir(root, gsm, file_type, retain_raw_for_gsm(root, gsm))
            declared = [safe_name(row.get("filename") or Path(urlparse(row["url"]).path).name) for row in members]
            if len({name.casefold() for name in declared}) != len(declared):
                raise ValueError("duplicate supplement destination filenames")
            if len({row["url"] for row in members}) != len(members):
                raise ValueError("duplicate supplement source URL for a GSM")
            for row, name in zip(members, declared):
                fingerprint = supplement_source_fingerprint(row)
                own_records = [item for item in records if item.get("source_fingerprint") == fingerprint]
                failure_path = root / "reports/supplement_failures" / f"{gsm}-{fingerprint[:20]}.json"
                if reusable(root, row, own_records):
                    failure_path.unlink(missing_ok=True)
                    continue
                object_stage = stage / fingerprint
                object_stage.mkdir(exist_ok=True)
                try:
                    staged = object_stage / name
                    identity = download(root, row["url"], staged, row)
                    extracted, methods = validate_and_extract(root, row, staged, file_type, identity)
                    prepared = []
                    parent_path = (directory / name).relative_to(root).as_posix()
                    for source, member_name in [(staged, ""), *extracted]:
                        path = (directory / source.name).relative_to(root).as_posix()
                        conflicting = [item for item in records if item.get("path", "").casefold() == path.casefold() and item.get("url") != row["url"]]
                        if conflicting or (member_name and source.name.casefold() in {value.casefold() for value in declared}):
                            raise ValueError(f"supplement destination collision: {source.name}")
                        record = {
                            "gse": row.get("gse", policy["gse"]), "gsm": gsm, "filename": source.name,
                            "url": row["url"], "file_type": file_type, "observed_bytes": str(source.stat().st_size),
                            "observed_md5": md5(source), "path": path, "validation": "PASS",
                            "integrity_methods": ";".join(methods), "response_bytes": identity["response_bytes"],
                            "etag": identity.get("etag", ""), "last_modified": identity.get("last_modified", ""),
                            "expected_bytes": row.get("expected_bytes", ""), "expected_md5": row.get("expected_md5", ""),
                            "member_of": parent_path if member_name else "", "member_name": member_name,
                            "source_fingerprint": fingerprint,
                        }
                        prepared.append((source, record))
                    updated = [item for item in records if item.get("url") != row["url"]] + [record for _, record in prepared]
                    with ResourceReservation(root, f"publish-{gsm}", 0) as reservation:
                        reservation.check()
                        publish(root, stage, directory, prepared, manifest, updated)
                    records = updated
                    shutil.rmtree(object_stage)
                    failure_path.unlink(missing_ok=True)
                except (OSError, ValueError, EOFError, ResourceLimitError, http.client.HTTPException, tarfile.TarError, zipfile.BadZipFile, zlib.error) as exc:
                    status = "UNVERIFIED" if isinstance(exc, UnverifiedDownload) else "FAIL"
                    failure = {"gsm": gsm, "source_fingerprint": fingerprint, "status": status, "message": str(exc)}
                    atomic_json(failure_path, failure)
                    failures.append(f"{gsm}/{name}: {status}: {exc}")
                    break
    for failure in failures:
        print(failure, file=sys.stderr)
    print(f"SUPPLEMENT gsms={len(by_gsm)} failures={len(failures)} type={file_type}")
    return 1 if failures else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError) as error:
        raise SystemExit(str(error))
