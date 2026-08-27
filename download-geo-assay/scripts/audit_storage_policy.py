#!/usr/bin/env python3
"""Audit per-assay policy and per-GSM release state without mutating raw data."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from capabilities import CapabilityError, assay_capability  # noqa: E402
from project_layout import (  # noqa: E402
    StoragePolicyError,
    deletion_log_path,
    list_published_raw,
    list_temporary_raw_for_gsm,
    policy_for_gsm,
    read_release_states,
    read_storage_policies,
    read_tsv,
    storage_policy_path,
    write_tsv_atomic,
)


def refresh_report(root: Path) -> None:
    reporter = Path(__file__).with_name("build_report.py")
    if reporter.is_file():
        subprocess.run([sys.executable, str(reporter), "--root", str(root)], check=False)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output or root / "reports/storage_policy_audit.tsv"
    findings: list[dict[str, str]] = []

    def add(gse: str, gsm: str, check: str, status: str, message: str) -> None:
        findings.append(
            {"gse": gse, "gsm": gsm, "check": check, "status": status, "message": message}
        )

    try:
        policies = read_storage_policies(root)
    except StoragePolicyError as exc:
        add(root.name, "", "policy_exists", "FAIL", str(exc))
        write_tsv_atomic(output, ["gse", "gsm", "check", "status", "message"], findings)
        refresh_report(root)
        return 1

    for policy in policies:
        add(
            policy["gse"],
            "",
            "policy",
            "PASS",
            f"{policy['assay_type']}/{policy['modality']} retain={policy['retain_raw_files']} "
            f"product={policy['final_product']} source={policy['source_preference']}",
        )
        if not policy.get("confirmed_at"):
            add(policy["gse"], "", "policy_confirmed", "FAIL", "缺少 confirmed_at")
        if policy["retain_raw_files"] == "false" and policy.get("modality") not in {"", "pending"}:
            try:
                _, capability = assay_capability(policy["modality"], root)
                allowed = set(capability.get("standard_products", [])) | set(
                    capability.get("optional_products", [])
                )
                if capability.get("workflow") == "raw_only" or policy["final_product"] not in allowed:
                    add(
                        policy["gse"],
                        "",
                        "release_eligibility",
                        "FAIL",
                        f"{policy['modality']} 不允许删除到 {policy['final_product']}",
                    )
            except CapabilityError as exc:
                add(policy["gse"], "", "capability", "FAIL", str(exc))

    source_rows = read_tsv(root / "metadata/source_manifest.tsv")
    gsms = sorted({row.get("gsm", "") for row in source_rows if row.get("gsm")})
    releases = {row.get("gsm", ""): row for row in read_release_states(root)}
    deleted_paths = {row.get("path", "") for row in read_tsv(deletion_log_path(root))}
    for gsm in gsms:
        policy = policy_for_gsm(root, gsm, required=False)
        if policy is None:
            add(root.name, gsm, "policy_mapping", "FAIL", "没有匹配的 assay policy")
            continue
        temporary = list_temporary_raw_for_gsm(root, gsm)
        release = releases.get(gsm)
        if policy["retain_raw_files"] == "true":
            if release and release.get("release_status") in {"ready", "released"}:
                add(policy["gse"], gsm, "mode_a", "FAIL", "Mode A 出现 release 记录")
            else:
                add(policy["gse"], gsm, "mode_a", "PASS", "raw 保留策略有效")
            continue
        if release is None:
            # Before download/conversion, pending with no temporary files is a valid state.
            add(
                policy["gse"],
                gsm,
                "release_pending",
                "PASS",
                f"尚未释放；temporary_files={len(temporary)}",
            )
        elif release.get("release_status") == "released":
            if temporary:
                add(policy["gse"], gsm, "released", "FAIL", "released 后仍有 temporary raw")
            elif not all(path in deleted_paths for path in release.get("candidate_paths", "").split(";") if path):
                add(policy["gse"], gsm, "released", "FAIL", "release 候选未完整进入删除日志")
            else:
                add(policy["gse"], gsm, "released", "PASS", "审计后已释放")
        elif release.get("release_status") == "blocked":
            if not temporary:
                add(policy["gse"], gsm, "blocked_keeps_raw", "FAIL", "blocked 但 raw 不存在")
            else:
                add(policy["gse"], gsm, "blocked_keeps_raw", "PASS", release.get("message", ""))
        else:
            add(policy["gse"], gsm, "release_state", "PASS", release.get("release_status", "pending"))

    if not gsms:
        add(root.name, "", "pre_download", "PASS", "尚无 source manifest；policy 可处于 pending")
    if list_published_raw(root) and any(row["retain_raw_files"] == "false" for row in policies):
        add(root.name, "", "mode_b_raw_location", "FAIL", "Mode B 的 raw 写入了 raw/ 而非 temporary/")

    write_tsv_atomic(output, ["gse", "gsm", "check", "status", "message"], findings)
    failures = [row for row in findings if row["status"] == "FAIL"]
    print(f"AUDIT storage_policy errors={len(failures)} checks={len(findings)} report={output}")
    for row in failures:
        print(f"ERROR {row['gsm']} {row['check']}: {row['message']}")
    refresh_report(root)
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
