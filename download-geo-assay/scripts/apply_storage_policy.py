#!/usr/bin/env python3
"""Release one GSM/library raw set after all conversion gates pass."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import re
import sys
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from artifact_integrity import IntegrityError, check_receipt, release_files, load

from capabilities import CapabilityError, assay_capability  # noqa: E402
from project_layout import (  # noqa: E402
    CONVERSION_PROVENANCE_FIELDS,
    DELETION_LOG_FIELDS,
    StoragePolicyError,
    conversion_provenance_path,
    deletion_log_path,
    infer_srr,
    list_temporary_raw_for_gsm,
    policy_for_gsm,
    processed_audit_path,
    read_release_states,
    read_storage_policies,
    read_tsv,
    write_release_state,
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


def split(value: str) -> list[str]:
    return [item for item in value.rstrip("\r").split(";") if item]


def matching_runs(root: Path, gsm: str) -> tuple[str, list[str]]:
    rows = [
        row for row in read_tsv(root / "metadata/source_manifest.tsv")
        if row.get("gsm") == gsm
    ]
    if not rows:
        rows = read_tsv(root / "metadata/download_manifests" / f"{gsm}.tsv")
        if not rows:
            raise StoragePolicyError(f"source/download manifest 中找不到 {gsm}")
        members = [row.get("srr") or row.get("filename", "") for row in rows]
        gses = {row.get("gse", "") for row in rows}
        if len(gses) != 1 or not all(members):
            raise StoragePolicyError(f"{gsm} 的 library members/GSE 不完整")
        return next(iter(gses)), sorted(set(members))
    gses = {row.get("gse", "") for row in rows}
    if len(gses) != 1:
        raise StoragePolicyError(f"{gsm} 的 GSE 映射不唯一")
    runs = [row.get("srr", "") for row in rows]
    if not all(runs) or len(runs) != len(set(runs)):
        raise StoragePolicyError(f"{gsm} 的成员 runs 缺失或重复")
    return next(iter(gses)), sorted(runs)


def gate_errors(
    root: Path,
    gsm: str,
    gse: str,
    runs: list[str],
    candidates: list[Path],
    policy: dict[str, str],
) -> list[str]:
    errors: list[str] = []
    try:
        check_receipt(root, gsm)
        from publish_sample import verify_delivery
        verify_delivery(root, gsm)
    except (IntegrityError, OSError, ValueError, KeyError) as exc:
        errors.append(f"content-bound release audit: {exc}")
    modality = policy.get("modality", "")
    if not policy.get("confirmed_at"):
        errors.append("storage policy 缺少 confirmed_at")
    if policy.get("final_product") in {"", "pending", "fastq", "sra", "CEL", "IDAT"}:
        errors.append("没有可审计的转换产品")
    if modality and modality != "pending":
        try:
            _, capability = assay_capability(modality, root)
        except CapabilityError as exc:
            errors.append(str(exc))
        else:
            allowed = set(capability.get("standard_products", [])) | set(
                capability.get("optional_products", [])
            )
            if capability.get("workflow") == "raw_only":
                errors.append(f"{modality} 是 raw-only assay，不具备删除资格")
            elif policy.get("final_product") not in allowed:
                errors.append(
                    f"{modality} 不允许 final_product={policy.get('final_product')}"
                )

    download_rows = {
        row.get("srr", ""): row
        for row in read_tsv(root / "reports/download_integrity_audit.tsv")
        if row.get("gsm") == gsm
    }
    raw_manifest = read_tsv(root / "metadata/download_manifests" / f"{gsm}.tsv")
    raw_validated = {
        row.get("srr") or row.get("filename", "")
        for row in raw_manifest
        if row.get("validation") == "PASS"
    }
    for run in runs:
        row = download_rows.get(run)
        if (row is None or row.get("status") != "PASS") and run not in raw_validated:
            errors.append(f"{run}: download integrity 未通过")

    audit_rows = [
        row for row in read_tsv(processed_audit_path(root)) if row.get("gsm") == gsm
    ]
    if len(audit_rows) != 1 or audit_rows[0].get("status") != "PASS":
        errors.append(f"{gsm}: processed output audit 未通过")

    provenance_rows = [
        row for row in read_tsv(conversion_provenance_path(root))
        if row.get("gsm") == gsm
    ]
    if len(provenance_rows) != 1:
        errors.append(f"{gsm}: conversion provenance 必须恰有一行")
    else:
        row = provenance_rows[0]
        missing = [field for field in CONVERSION_PROVENANCE_FIELDS if field not in row]
        if missing:
            errors.append(f"conversion provenance 缺列 {missing}")
        if row.get("gse") != gse or not row.get("tool") or not row.get("tool_version"):
            errors.append(f"{gsm}: conversion provenance 的 GSE/tool/version 不完整")
        inputs = split(row.get("input_files") or row.get("input_fastq", ""))
        outputs = split(row.get("output_matrix", ""))
        for item in inputs + outputs:
            candidate = Path(item)
            if candidate.is_absolute() or ".." in candidate.parts:
                errors.append(f"{gsm}: unsafe provenance path {item!r}")
        for run in runs:
            if not any(run in Path(item).name for item in inputs):
                errors.append(f"{gsm}: conversion inputs 未覆盖成员 run {run}")
        for item in outputs:
            path = root / item
            if not path.is_file() or path.stat().st_size == 0:
                errors.append(f"{gsm}: 输出缺失或为空 {item}")
        if not inputs or not outputs:
            errors.append(f"{gsm}: provenance 缺少输入或输出")

    if not candidates:
        errors.append(f"{gsm}: 没有 temporary raw 候选")
    for path in candidates:
        resolved = path.resolve()
        base = root / "temporary" / gsm
        cache_roots = {
            root / "temporary/prefetch_cache" / run for run in runs if re.fullmatch(r"[SED]RR\d+", run)
        }
        if (base not in resolved.parents and not cache_roots.intersection(resolved.parents)) or not path.is_file() or path.is_symlink():
            errors.append(f"{gsm}: 非法或已变化的删除候选 {path}")
    return errors


def policy_gsms(root: Path, policy: dict[str, str]) -> set[str]:
    routing = read_tsv(root / "metadata/assay_routing.tsv")
    return {
        row.get("gsm", "")
        for row in routing
        if row.get("gsm")
        and (not policy.get("assay_type") or row.get("assay_type") == policy["assay_type"])
        and (not policy.get("modality") or row.get("modality") == policy["modality"])
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument("--gsm")
    scope.add_argument("--unit", dest="gsm", help="当前等价于 --gsm")
    parser.add_argument(
        "--confirm-delete",
        action="store_true",
        help="确认执行已预先授权且门控通过的当前单元删除",
    )
    args = parser.parse_args()
    if not args.confirm_delete:
        raise SystemExit("必须显式传入 --confirm-delete；此参数不替代 storage policy 前置授权")
    root = args.root.resolve()
    gsm = args.gsm.upper()
    lock_path = root / "reports" / f"storage_release.{gsm}.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    release_lock = lock_path.open("a+")
    try:
        fcntl.flock(release_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        raise SystemExit(f"{gsm}: another release transaction is active") from exc
    try:
        policy = policy_for_gsm(root, gsm)
        if policy is None:
            raise StoragePolicyError(f"缺少 {gsm} 的 storage policy")
        gse, runs = matching_runs(root, gsm)
    except StoragePolicyError as exc:
        raise SystemExit(str(exc)) from exc
    if policy["retain_raw_files"] == "true":
        raise SystemExit(f"{gsm}: Mode A forbids raw deletion")

    # Hold the same locks as downloads/lookahead until the release transaction ends.
    object_locks = []
    for run in runs:
        if not re.fullmatch(r"[SED]RR\d+", run):
            continue
        for path in (root / "temporary" / gsm / "work" / run / "run.lock", root / "temporary/prefetch_cache" / f"{run}.lock"):
            path.parent.mkdir(parents=True, exist_ok=True)
            handle = path.open("a+")
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise SystemExit(f"{run}: active download/prefetch; raw retained") from exc
            object_locks.append(handle)

    candidates = list_temporary_raw_for_gsm(root, gsm)
    journal_path = root / f"reports/release_journals/{gsm}.json"
    resuming = journal_path.is_file()
    errors = [] if resuming else gate_errors(root, gsm, gse, runs, candidates, policy)
    if resuming:
        try:
            check_receipt(root, gsm, allow_missing_inputs=True)
        except (IntegrityError, OSError, ValueError, KeyError) as exc:
            errors.append(f"release recovery: {exc}")
    base_state = {
        "gse": gse,
        "gsm": gsm,
        "unit_id": gsm,
        "assay_type": policy.get("assay_type", ""),
        "modality": policy.get("modality", ""),
        "member_runs": ";".join(runs),
        "final_product": policy.get("final_product", ""),
        "policy_confirmed_at": policy.get("confirmed_at", ""),
        "download_status": "PASS" if not any("download integrity" in error for error in errors) else "FAIL",
        "conversion_status": "PASS" if not any("provenance" in error or "成员 run" in error for error in errors) else "FAIL",
        "processed_audit": "PASS" if not any("processed output" in error for error in errors) else "FAIL",
        "candidate_paths": ";".join(relative(root, path) for path in candidates),
        "candidate_bytes": ";".join(str(path.stat().st_size) for path in candidates),
        "candidate_md5": ";".join(md5(path) for path in candidates),
        "released_at": "",
        "message": "; ".join(errors),
    }
    if errors:
        write_release_state(root, base_state | {"release_status": "blocked"})
        print("ERROR " + "; ".join(errors), file=sys.stderr)
        return 1

    # The per-file JSON journal is authoritative across unlink/process interruptions.
    previous = [row for row in read_release_states(root) if row.get("gsm") == gsm]
    ready = previous[0] if resuming and previous else write_release_state(root, base_state | {"release_status": "ready"})
    try:
        journal = release_files(root, gsm, [relative(root, path) for path in candidates])
    except (IntegrityError, OSError, ValueError) as exc:
        raise SystemExit(f"Release paused with durable journal; {exc}") from exc
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    log_rows = read_tsv(deletion_log_path(root))
    logged = {(row.get("gsm"), row.get("path")) for row in log_rows}
    old_md5 = dict(zip(split(ready.get("candidate_paths", "")), split(ready.get("candidate_md5", ""))))
    for item in journal["files"]:
        name = item["path"]
        if (gsm, name) not in logged:
            log_rows.append({"gse": gse, "gsm": gsm, "srr": infer_srr(Path(name)),
                             "path": name, "bytes": str(item["bytes"]), "md5": old_md5.get(name, ""),
                             "validation_report": processed_audit_path(root).relative_to(root).as_posix(),
                             "deleted_at": now})
    write_tsv_atomic(deletion_log_path(root), DELETION_LOG_FIELDS, log_rows)
    write_release_state(root, ready | {"release_status": "released", "released_at": now, "message": ""})

    released = {
        row["gsm"] for row in read_release_states(root) if row["release_status"] == "released"
    }
    if policy_gsms(root, policy) and policy_gsms(root, policy).issubset(released):
        updated = dict(policy)
        updated["validation_status"] = "validated"
        updated["deletion_status"] = "deleted"
        updated["deletion_time"] = now
        write_storage_policy(root, updated)
    print(
        f"STORAGE_RELEASE gsm={gsm} runs={len(runs)} files={len(journal['files'])} "
        f"log={deletion_log_path(root).relative_to(root).as_posix()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
