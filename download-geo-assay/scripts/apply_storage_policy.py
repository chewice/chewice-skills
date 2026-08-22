#!/usr/bin/env python3
"""Delete temporary FASTQ only after Mode B conversion validation succeeds."""

from __future__ import annotations

import argparse
import hashlib
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from project_layout import (  # noqa: E402
    CONVERSION_PROVENANCE_FIELDS,
    DELETION_LOG_FIELDS,
    StoragePolicyError,
    conversion_provenance_path,
    deletion_completed,
    deletion_log_path,
    infer_gsm,
    infer_srr,
    list_temporary_fastq,
    locate_outputs,
    read_storage_policy,
    read_tsv,
    write_storage_policy,
    write_tsv_atomic,
)


def md5(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def relative(root: Path, path: Path) -> str:
    return path.resolve().relative_to(root).as_posix()


def block(policy: dict[str, str], root: Path, message: str) -> int:
    if policy["retain_raw_fastq"] == "false":
        policy = dict(policy)
        policy["deletion_status"] = "blocked"
        write_storage_policy(root, policy)
    print(f"ERROR {message}", file=sys.stderr)
    return 1


def provenance_ok(root: Path, samples: set[tuple[str, str]]) -> list[str]:
    rows = read_tsv(conversion_provenance_path(root))
    errors: list[str] = []
    if not rows:
        return ["missing reports/conversion_provenance.tsv"]
    missing = [field for field in CONVERSION_PROVENANCE_FIELDS if field not in rows[0]]
    if missing:
        return [f"conversion provenance missing columns: {missing}"]
    by_gsm = {row.get("gsm", ""): row for row in rows}
    for gse, gsm in samples:
        row = by_gsm.get(gsm)
        if row is None:
            errors.append(f"{gsm}: missing conversion provenance")
            continue
        if row.get("gse", "") != gse:
            errors.append(f"{gsm}: provenance gse mismatch")
        if not row.get("tool") or not row.get("tool_version"):
            errors.append(f"{gsm}: missing conversion tool/version")
        inputs = [item for item in row.get("input_fastq", "").split(";") if item]
        outputs = [item for item in row.get("output_matrix", "").split(";") if item]
        if not inputs or not outputs:
            errors.append(f"{gsm}: provenance lacks input FASTQ or output matrix")
            continue
        for item in inputs + outputs:
            candidate = Path(item)
            if candidate.is_absolute() or ".." in candidate.parts:
                errors.append(f"{gsm}: unsafe provenance path {item!r}")
        for item in outputs:
            path = root / item
            if not path.is_file() or path.stat().st_size == 0:
                errors.append(f"{gsm}: missing/empty output matrix {item}")
        matrix_dir, _, _ = locate_outputs(root, gse, gsm)
        if not any(
            (root / item).resolve() == matrix_dir.resolve()
            or matrix_dir.resolve() in (root / item).resolve().parents
            or (root / item).is_file()
            for item in outputs
        ):
            errors.append(f"{gsm}: output_matrix is not under processed matrix directory")
    return errors


def audit_pass(root: Path) -> tuple[set[tuple[str, str]], list[str]]:
    rows = read_tsv(root / "reports/final_output_audit.tsv")
    if not rows:
        return set(), ["missing reports/final_output_audit.tsv"]
    samples: set[tuple[str, str]] = set()
    errors: list[str] = []
    for row in rows:
        gse, gsm = row.get("gse", ""), row.get("gsm", "")
        samples.add((gse, gsm))
        if row.get("status") != "PASS":
            errors.append(f"{gsm}: final-output audit is {row.get('status')!r}")
            continue
        matrix_dir, _, _ = locate_outputs(root, gse, gsm)
        raw_matrix = matrix_dir / "raw_feature_bc_matrix/matrix.mtx.gz"
        if not raw_matrix.is_file() or raw_matrix.stat().st_size == 0:
            errors.append(f"{gsm}: missing processed matrix after validation")
        if not row.get("raw_shape") or not row.get("filtered_shape"):
            errors.append(f"{gsm}: matrix shapes missing from audit")
    return samples, errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        policy = read_storage_policy(root)
    except StoragePolicyError as exc:
        raise SystemExit(str(exc)) from exc

    if policy["retain_raw_fastq"] == "true":
        print("ERROR Mode A forbids FASTQ deletion", file=sys.stderr)
        return 1
    if deletion_completed(root) and not list_temporary_fastq(root):
        print("STORAGE_POLICY already deleted; nothing to apply")
        return 0

    samples, errors = audit_pass(root)
    errors.extend(provenance_ok(root, samples))
    files = list_temporary_fastq(root)
    if not files:
        errors.append("Mode B has no temporary FASTQ to delete")
    if errors:
        return block(policy, root, "; ".join(errors))

    now = datetime.now().astimezone().isoformat(timespec="seconds")
    log_rows = read_tsv(deletion_log_path(root))
    for path in files:
        gsm = infer_gsm(path, root)
        log_rows.append(
            {
                "gse": policy["gse"],
                "gsm": gsm,
                "srr": infer_srr(path),
                "path": relative(root, path),
                "bytes": str(path.stat().st_size),
                "md5": md5(path),
                "validation_report": "reports/final_output_audit.tsv",
                "deleted_at": now,
            }
        )
        path.unlink()
        parent = path.parent
        if parent.is_dir() and not any(parent.iterdir()):
            parent.rmdir()

    write_tsv_atomic(deletion_log_path(root), DELETION_LOG_FIELDS, log_rows)
    policy["validation_status"] = "validated"
    policy["deletion_status"] = "deleted"
    policy["deletion_time"] = now
    write_storage_policy(root, policy)
    print(
        f"STORAGE_POLICY deleted files={len(files)} "
        f"log={deletion_log_path(root).relative_to(root).as_posix()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
