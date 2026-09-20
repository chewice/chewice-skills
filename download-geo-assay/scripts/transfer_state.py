#!/usr/bin/env python3
"""Atomic state, resume-identity, and publish helpers for download_run.sh."""

from __future__ import annotations

import argparse
from contextlib import ExitStack
import fcntl
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def acceptance_fingerprint(row: dict) -> str:
    """Bind local acceptance requirements separately from remote object identity."""
    payload = {key: str(row.get(key, "")).strip() for key in (
        "library_layout", "expected_spots", "cb_length", "umi_length",
        "read_roles", "final_product",
    )}
    payload["acceptance_version"] = 1
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def source_fingerprint(row: dict) -> str:
    columns = (("source", "selected_source"), ("urls", "selected_urls"), ("bytes", "selected_bytes"),
               ("md5", "selected_md5"), ("roles", "read_roles"), ("final_product", "final_product"))
    payload = {key: row.get(column, "") for key, column in columns}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def source_row(root: Path, run: str) -> dict:
    from project_layout import read_tsv
    rows = [row for row in read_tsv(root / "metadata/source_manifest.tsv") if row.get("srr") == run]
    if len(rows) != 1:
        raise ValueError(f"Expected one source row for {run}")
    return rows[0]


def acceptance(args) -> int:
    print(acceptance_fingerprint(source_row(args.root, args.run)))
    return 0


def ready(args) -> int:
    """Record/verify the acquired objects; this never denotes final acceptance."""
    from artifact_integrity import safe_path
    if args.check:
        receipt = read_json(args.path)
        if receipt.get("source_fingerprint") != args.fingerprint or receipt.get("run") != args.run:
            return 1
        entries = receipt.get("files", [])
        expected_roles = set(source_row(args.root, args.run).get("read_roles", "").split(";"))
        if not entries or len(entries) != len(expected_roles) or {item.get("role") for item in entries} != expected_roles:
            return 1
        for item in entries:
            path = safe_path(args.root, item["path"])
            if path.stat().st_size != item["bytes"] or digest(path) != item["md5"]:
                return 1
            print(f'{item["role"]}\t{path}')
        return 0
    entries = []
    for item in args.file:
        role, name = item.split("=", 1)
        relative = str(Path(name).resolve().relative_to(args.root.resolve()))
        path = safe_path(args.root, relative)
        entries.append({"role": role, "path": relative, "bytes": path.stat().st_size, "md5": digest(path)})
    if not entries or len({item["role"] for item in entries}) != len(entries):
        raise ValueError("Acquired objects require unique roles")
    write_json(args.path, {"version": 1, "run": args.run, "status": "acquired",
                          "source_fingerprint": args.fingerprint,
                          "acceptance_fingerprint": acceptance_fingerprint(source_row(args.root, args.run)),
                          "files": entries, "acquired_at": now()})
    return 0


def validate_local_acceptance(source, paths, report, root) -> int:
    run = source["srr"]
    roles = {"R1", "R2"} if source.get("library_layout") == "PAIRED" else {"R1"}
    roles |= set(source.get("read_roles", "").split(";")) & {"I1", "I2"}
    expected = {f'{run}_{role}.fastq.gz' for role in roles}
    if source.get("final_product") == "sra":
        expected = {f'{run}.sra'}
    if {path.name for path in paths} != expected:
        print("Current acceptance contract does not match retained read roles", file=sys.stderr)
        return 12
    if source.get("final_product") == "sra":
        from acquisition_runtime import managed_run
        result = managed_run(root, ["vdb-validate", str(paths[0])], stdout=sys.stderr)
        if result.returncode:
            return 12
    else:
        by_name = {path.name: path for path in paths}
        command = [sys.executable, str(Path(__file__).with_name("validate_fastq_pair.py")),
                   "--srr", run, "--r1", str(by_name[f'{run}_R1.fastq.gz']),
                   "--report", str(report)]
        if "R2" in roles:
            command += ["--r2", str(by_name[f'{run}_R2.fastq.gz'])]
        for key in ("expected_spots", "cb_length", "umi_length"):
            if source.get(key):
                command += ["--" + key.replace("_", "-"), source[key]]
        if subprocess.run(command, stdout=sys.stderr).returncode:
            return 12
        for role in sorted(roles & {"I1", "I2"}):
            command = [sys.executable, str(Path(__file__).with_name("validate_fastq_pair.py")),
                       "--srr", run, "--r1", str(by_name[f'{run}_{role}.fastq.gz'])]
            if source.get("expected_spots"):
                command += ["--expected-spots", source["expected_spots"]]
            if subprocess.run(command, stdout=sys.stderr).returncode:
                return 12
    return 0


def completed(args) -> int:
    """Reuse completed content; changed acceptance rules require only local checks."""
    from artifact_integrity import safe_path, fsync_dir
    from project_layout import read_tsv, write_tsv_atomic
    source = source_row(args.root, args.run)
    if not args.marker.is_file() or not args.manifest.is_file():
        return 1
    rows = read_tsv(args.manifest)
    matches = [row for row in rows if row.get("srr") == args.run]
    if len(matches) != 1 or matches[0].get("source_fingerprint") != args.fingerprint:
        return 1
    record = matches[0]
    names, sizes, checks = (record.get(key, "").split(";") for key in ("retained_files", "retained_bytes", "retained_md5"))
    if not names or not names[0] or not len(names) == len(sizes) == len(checks):
        return 12
    paths = []
    for name, size, checksum in zip(names, sizes, checks):
        path = safe_path(args.root, name, exists=False)
        if not path.is_file() or str(path.stat().st_size) != size or digest(path) != checksum:
            print("Completed content has changed; preserve it for explicit recovery", file=sys.stderr)
            return 12
        paths.append(path)
    contract = acceptance_fingerprint(source)
    try:
        marker = dict(line.split("\t", 1) for line in args.marker.read_text().splitlines())
    except ValueError:
        return 12
    if (record.get("validation") == "PASS" and marker.get("validation") == "PASS"
            and marker.get("source_fingerprint") == args.fingerprint
            and record.get("acceptance_fingerprint") == contract
            and marker.get("acceptance_fingerprint") == contract):
        return 0
    if validate_local_acceptance(source, paths, args.report, args.root):
        return 12
    record["acceptance_fingerprint"] = contract
    record["expected_spots"] = source.get("expected_spots", "")
    record["validation"] = "PASS"
    record["gse"], record["gsm"] = source["gse"], source["gsm"]
    if source.get("final_product") != "sra":
        validation = read_json(args.report)
        record["observed_r1"] = str(validation["reads_per_mate"])
        record["observed_r2"] = str(validation["reads_per_mate"]) if validation.get("r2") else ""
    record["revalidated_at"] = now()
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with args.lock.open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        current = read_tsv(args.manifest)
        rows = [record if row.get("srr") == args.run else row for row in current]
        fields = list(dict.fromkeys([*fields, *(key for row in rows for key in row)]))
        write_tsv_atomic(args.manifest, fields, rows)
        marker["acceptance_fingerprint"] = contract
        marker["source_fingerprint"] = args.fingerprint
        marker["validation"] = "PASS"
        marker["gse"], marker["gsm"], marker["srr"] = source["gse"], source["gsm"], args.run
        marker["revalidated_at"] = now()
        temp = args.marker.with_name(args.marker.name + ".tmp")
        with temp.open("w") as handle:
            handle.write("".join(f"{key}\t{value}\n" for key, value in marker.items()))
            handle.flush(); os.fsync(handle.fileno())
        os.replace(temp, args.marker); fsync_dir(args.marker.parent)
    return 0


def run_stage(args) -> int:
    """One supervised stage owns all of its run's writes and disk reservation."""
    from acquisition_runtime import (effective_config, managed_run, network_env, open_url,
                                     ResourceReservation, RuntimeCancelled,
                                     ResourceLimitError, RuntimeConfigurationError)
    from project_layout import work_dir, policy_for_gsm, published_fastq_dir, published_sra_dir, read_tsv
    root = args.root.resolve()
    row = source_row(root, args.run)
    config = effective_config(root)
    if args.stage == "all":
        for stage in ("acquire", "materialize"):
            result = run_stage(argparse.Namespace(root=root, run=args.run, stage=stage))
            if result:
                return result
        return 0
    env = dict(os.environ)
    env.update(GEO_SRA_PROJECT_ROOT=str(root), GEO_SRA_MANAGED_STAGE=args.stage, PYTHONDONTWRITEBYTECODE="1")
    for key, value in {
        "GEO_SRA_MAX_ATTEMPTS": config["max_same_error_attempts"],
        "GEO_SRA_RETRY_DELAYS": config["retry_delays_seconds"].replace(";", ","),
        "GEO_SRA_CONNECTIONS": config["download_connections"],
        "GEO_SRA_SRA_THREADS": config["sra_threads"],
        "GEO_SRA_COMPRESS_THREADS": config["compress_threads"],
    }.items():
        env.setdefault(key, value)
    work = work_dir(root, row["gsm"], args.run)
    cache = root / "temporary/prefetch_cache" / args.run
    policy = policy_for_gsm(root, row["gsm"])
    final = (published_sra_dir(root, row["gsm"]) if row.get("final_product") == "sra"
             else published_fastq_dir(root, row["gsm"], policy["retain_raw_files"] == "true"))
    completed_marker = root / f'reports/status/{args.run}.complete'
    completed_record = root / f'metadata/download_manifests/{row["gsm"]}.tsv'
    # A completed run only needs local validation; no remote size lookup is allowed here.
    current_fingerprint = source_fingerprint(row)
    locally_complete = completed_marker.is_file() and any(
        record.get("srr") == args.run and record.get("source_fingerprint") == current_fingerprint
        for record in read_tsv(completed_record))
    receipt = read_json(root / f'reports/status/{args.run}.ready.json')
    if receipt.get("source_fingerprint") != current_fingerprint:
        receipt = {}
    total = sum(item.get("bytes", 0) for item in receipt.get("files", []))
    journal = read_json(work / "publish.json")
    publishing = journal.get("source_fingerprint") == current_fingerprint and bool(journal.get("files"))
    if not total and publishing:
        total = sum(item["bytes"] for item in journal["files"])
    sizes = row.get("selected_bytes", "").split(";")
    if not total and sizes and all(value.isdigit() and int(value) > 0 for value in sizes):
        total = sum(map(int, sizes))
    try:
        if args.stage == "acquire" and not locally_complete and not publishing:
            urls = row.get("selected_urls", "").split(";")
            env = network_env(root, urls[0] if urls else None, env)
            if not total:
                if row["selected_source"] in {"ncbi_sra", "ncbi_ondemand"}:
                    from ncbi_odp import probe
                    evidence = probe(args.run, root)
                    if evidence.get("status") == "available" and str(evidence.get("bytes", "")).isdigit():
                        total = int(evidence["bytes"])
                    elif evidence.get("status") == "missing":
                        result = managed_run(root, ["vdb-dump", args.run, "--info"], network=True,
                                             env=env, capture_output=True, text=True, timeout=120)
                        match = re.search(r"^\s*size\s*:\s*([\d,]+)", result.stdout or "", re.MULTILINE)
                        if result.returncode == 0 and match:
                            total = int(match[1].replace(",", ""))
                else:
                    observed = []
                    for url in urls:
                        with open_url(root, url, method="HEAD") as response:
                            value = response.headers.get("Content-Length", "")
                        if not value.isdigit() or int(value) <= 0:
                            raise RuntimeConfigurationError("Cannot reserve an object of unknown size")
                        observed.append(int(value))
                    total = sum(observed)
        if total <= 0 and not locally_complete:
            raise RuntimeConfigurationError("Run size is unknown; obtain source metadata before acquisition")
        peak = total
        if args.stage == "materialize" and not publishing and "SRA" in row.get("read_roles", "").split(";") and row.get("final_product") != "sra":
            peak = int(config.get("materialize_peak_bytes") or total * 18)
        if locally_complete:
            peak = 0  # The child only reads/revalidates the recorded final objects.
        # Only reusable/current files offset this reservation. Quarantine, old
        # AWS copies and another run's final files remain charged independently.
        paths = [work / "staging/download", work / "ncbi" / args.run]
        paths += [cache / f'{args.run}{suffix}' for suffix in
                  (".sra", ".sralite", ".sra.aws.part", ".sra.aws.pending.json", ".sra.part", ".sra.part.aria2")]
        if args.stage == "materialize":
            paths += [work / "staging/fasterq", work / "fasterq_tmp"]
            for role in ("R1", "R2", "I1", "I2"):
                paths += [work / "staging" / f'{args.run}_{role}.fastq.gz',
                          work / "staging" / f'{args.run}_{role}.fastq.gz.tmp',
                          final / f'{args.run}_{role}.fastq.gz']
            paths += [final / f'{args.run}.sra']
        temporary_paths = tuple(path for path in paths if path.is_relative_to(root / "temporary"))
        with ResourceReservation(root, f'run-{args.run}-{args.stage}', peak, peak,
                                 paths=paths, temporary_paths=temporary_paths) as reservation:
            result = managed_run(root, ["bash", str(Path(__file__).with_name("download_run.sh")),
                                       str(root), args.run, "--stage", args.stage],
                                 env=env, reservation=reservation)
        return result.returncode
    except RuntimeCancelled as exc:
        return exc.returncode
    except (ResourceLimitError, RuntimeConfigurationError, OSError, ValueError) as exc:
        print(f"Stage blocked: {exc}", file=sys.stderr)
        return 2


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
    from artifact_integrity import fsync_dir
    fsync_dir(path.parent)


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
    if getattr(args, "acceptance", None) is not None:
        state["acceptance_fingerprint"] = args.acceptance
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


def archive_retry(args: argparse.Namespace) -> int:
    """Explicit operator recovery; retain old counters and all raw/publish evidence."""
    from project_layout import read_tsv
    from artifact_integrity import safe_path, fsync_dir
    root = args.root.resolve()
    if not re.fullmatch(r'(?:[SED]RR|CRR)\d+',args.run) or not args.reason.strip():
        raise SystemExit('Valid run and nonempty recovery reason required')
    rows = [row for row in read_tsv(root/'metadata/source_manifest.tsv') if row.get('srr') == args.run]
    if len(rows) != 1 or not re.fullmatch(r'GSM\d+',rows[0].get('gsm','')):
        raise SystemExit('Manifest must identify exactly one run and GSM')
    gsm = rows[0]['gsm']
    with ExitStack() as stack:
        for name in ['reports/status/queue.lock',f'temporary/{gsm}/work/{args.run}/run.lock',
                     f'temporary/prefetch_cache/{args.run}.lock']:
            path = safe_path(root,name,exists=False)
            path.parent.mkdir(parents=True,exist_ok=True)
            handle = stack.enter_context(path.open('a+'))
            try:
                fcntl.flock(handle,fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise SystemExit('Queue/run/cache is active; stop it before archiving retry state')
        path = safe_path(root,f'reports/status/{args.run}.transfer.json')
        state = read_json(path)
        if state.get('run') != args.run or state.get('status') == 'complete' or (path.parent/f'{args.run}.complete').exists():
            raise SystemExit('Refusing retry reset for mismatched/completed run')
        archive = path.with_name(f'{args.run}.transfer.{datetime.now().strftime("%Y%m%dT%H%M%S%f")}.archived.json')
        # Persist intent first, so even a crash between rename and fresh state is auditable.
        write_json(archive.with_suffix('.reason.json'),{'run':args.run,'reason':args.reason,'at':now()})
        os.replace(path,archive); fsync_dir(path.parent)
        write_json(path,{'run':args.run,'source_fingerprint':state.get('source_fingerprint'),
                         'status':'retryable_failed','phase':'manual_retry','error_counts':{},
                         'same_error_count':0,'attempt_count':0,'resume_count':0,
                         'retry_reason':args.reason,'previous_state':archive.name,'created_at':now()})
        print(f'RETRY_READY {args.run} archived={archive}')
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
    if getattr(args, "root", None):
        source = source_row(args.root, args.run)
        contract = acceptance_fingerprint(source)
        if journal.get("acceptance_fingerprint") != contract:
            paths = [Path(item["staged"]) if Path(item["staged"]).is_file() else Path(item["final"])
                     for item in items]
            if validate_local_acceptance(source, paths, args.report, args.root):
                return 12
            journal["acceptance_fingerprint"] = contract
            write_json(args.journal, journal)
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
                with staged.open("rb") as handle:
                    os.fsync(handle.fileno())
                os.replace(staged, final)
                from artifact_integrity import fsync_dir
                fsync_dir(final.parent)
        print(final)
    journal["published_at"] = journal.get("published_at") or now()
    write_json(args.journal, journal)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)

    command = commands.add_parser("run-stage")
    command.add_argument("--root", required=True, type=Path)
    command.add_argument("--run", required=True)
    command.add_argument("--stage", choices=("acquire", "materialize", "all"), default="all")
    command.set_defaults(function=run_stage)

    command = commands.add_parser("acceptance")
    command.add_argument("--root", required=True, type=Path)
    command.add_argument("--run", required=True)
    command.set_defaults(function=acceptance)

    command = commands.add_parser("ready")
    command.add_argument("--root", required=True, type=Path)
    command.add_argument("--path", required=True, type=Path)
    command.add_argument("--run", required=True)
    command.add_argument("--fingerprint", required=True)
    command.add_argument("--file", action="append", default=[])
    command.add_argument("--check", action="store_true")
    command.set_defaults(function=ready)

    command = commands.add_parser("completed")
    for name in ("root", "manifest", "marker", "lock", "report"):
        command.add_argument(f"--{name}", required=True, type=Path)
    command.add_argument("--run", required=True)
    command.add_argument("--fingerprint", required=True)
    command.set_defaults(function=completed)

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
    command.add_argument("--acceptance")
    command.add_argument("--attempt-delta", type=int, default=0)
    command.add_argument("--resume-delta", type=int, default=0)
    command.add_argument("--bytes-resumed", type=int)
    command.add_argument("--error-class")
    command.add_argument("--error-key")
    command.add_argument("--message")
    command.add_argument("--clear-error", action="store_true", help="Clear current error display only; persistent error_counts and retry budget are preserved")
    command.add_argument("--print-field")
    command.set_defaults(function=update)

    command = commands.add_parser("get")
    command.add_argument("--path", required=True, type=Path)
    command.add_argument("--field", required=True)
    command.add_argument("--default", default="")
    command.set_defaults(function=get_field)

    command = commands.add_parser('archive-retry', help='After operator review, archive run state and start a fresh retry budget')
    command.add_argument('--root',required=True,type=Path)
    command.add_argument('--run',required=True)
    command.add_argument('--reason',required=True)
    command.set_defaults(function=archive_retry)

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
    command.add_argument("--root", type=Path)
    command.add_argument("--run")
    command.add_argument("--report", type=Path)
    command.set_defaults(function=publish)
    args = parser.parse_args()
    return args.function(args)


if __name__ == "__main__":
    sys.exit(main())
