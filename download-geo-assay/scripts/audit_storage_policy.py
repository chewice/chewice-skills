#!/usr/bin/env python3
"""Audit that FASTQ retention or deletion follows the recorded storage policy."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from project_layout import (  # noqa: E402
    StoragePolicyError,
    conversion_provenance_path,
    deletion_log_path,
    infer_gsm,
    is_array_raw,
    list_published_raw,
    list_temporary_raw,
    locate_outputs,
    read_storage_policy,
    read_tsv,
    storage_policy_path,
    write_tsv_atomic,
)


def refresh_report(root: Path) -> None:
    reporter = Path(__file__).with_name("build_report.py")
    if reporter.is_file():
        subprocess.run(
            [sys.executable, str(reporter), "--root", str(root)],
            check=False,
        )


def add(
    rows: list[dict[str, str]],
    gse: str,
    check: str,
    status: str,
    message: str,
    gsm: str = "",
) -> None:
    rows.append(
        {
            "gse": gse,
            "gsm": gsm,
            "check": check,
            "status": status,
            "message": message,
        }
    )


def sample_rows(root: Path) -> list[dict[str, str]]:
    manifest = root / "metadata/source_manifest.tsv"
    if manifest.is_file():
        return read_tsv(manifest)
    return read_tsv(root / "metadata/sample_metadata.tsv")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True, type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    output = args.output or root / "reports/storage_policy_audit.tsv"
    findings: list[dict[str, str]] = []
    errors = 0

    try:
        policy = read_storage_policy(root)
    except StoragePolicyError as exc:
        add(findings, root.name, "policy_exists", "FAIL", str(exc))
        write_tsv_atomic(
            output,
            ["gse", "gsm", "check", "status", "message"],
            findings,
        )
        print(f"AUDIT storage_policy errors=1 report={output}")
        print(f"ERROR {exc}")
        refresh_report(root)
        return 1

    gse = policy["gse"]
    add(
        findings,
        gse,
        "policy_exists",
        "PASS",
        storage_policy_path(root).relative_to(root).as_posix(),
    )
    add(
        findings,
        gse,
        "user_choice",
        "PASS",
        f"retain_raw_files={policy['retain_raw_files']} storage_mode={policy['storage_mode']}",
    )

    samples = {(row.get("gse", gse), row.get("gsm", "")) for row in sample_rows(root)}
    samples = {(gse_id, gsm) for gse_id, gsm in samples if gsm}
    temporary = list_temporary_raw(root)
    published = list_published_raw(root)
    deletion_log = read_tsv(deletion_log_path(root))
    provenance = read_tsv(conversion_provenance_path(root))
    final_audit = read_tsv(root / "reports/final_output_audit.tsv")
    array_raw = is_array_raw(policy)

    if policy["retain_raw_files"] == "true":
        if policy["deletion_status"] != "not_applicable":
            add(findings, gse, "mode_a_retention", "FAIL", "Mode A 不得删除 raw files")
            errors += 1
        elif deletion_log:
            add(findings, gse, "mode_a_retention", "FAIL", "Mode A 出现删除日志")
            errors += 1
        else:
            add(findings, gse, "mode_a_retention", "PASS", "deletion_status=not_applicable")
        if not published:
            add(findings, gse, "raw_present", "FAIL", "Mode A 缺少 raw 文件")
            errors += 1
        else:
            add(
                findings,
                gse,
                "raw_present",
                "PASS",
                f"files={len(published)}",
            )
        if temporary:
            add(
                findings,
                gse,
                "no_temporary_raw",
                "FAIL",
                "Mode A 不应留下 temporary raw files",
            )
            errors += 1
        else:
            add(findings, gse, "no_temporary_raw", "PASS", "temporary raw files 已清空或不存在")
    else:
        if policy["deletion_status"] == "not_applicable":
            add(findings, gse, "mode_b_status", "FAIL", "Mode B 不得使用 not_applicable")
            errors += 1
        else:
            add(
                findings,
                gse,
                "mode_b_status",
                "PASS",
                f"deletion_status={policy['deletion_status']}",
            )
        if policy["deletion_status"] == "deleted":
            if policy["validation_status"] != "validated":
                add(
                    findings,
                    gse,
                    "delete_after_validation",
                    "FAIL",
                    "删除发生时 validation_status 不是 validated",
                )
                errors += 1
            else:
                add(findings, gse, "delete_after_validation", "PASS", "validated then deleted")
            if not deletion_log:
                add(findings, gse, "deletion_log", "FAIL", "缺少 storage_deletion_log.tsv")
                errors += 1
            elif not policy["deletion_time"]:
                add(findings, gse, "deletion_log", "FAIL", "deletion_time 为空")
                errors += 1
            else:
                add(
                    findings,
                    gse,
                    "deletion_log",
                    "PASS",
                    f"rows={len(deletion_log)} time={policy['deletion_time']}",
                )
            if temporary:
                add(
                    findings,
                    gse,
                    "temporary_cleared",
                    "FAIL",
                    "deleted 后仍有 temporary raw files",
                )
                errors += 1
            else:
                add(findings, gse, "temporary_cleared", "PASS", "temporary raw files 已删除")
            raw_left = list((root / "raw").glob("GSM*/fastq/*")) + list(
                (root / "raw").glob("GSM*/CEL/*")
            ) + list((root / "raw").glob("GSM*/IDAT/*"))
            if (root / "raw").exists() and raw_left:
                add(findings, gse, "raw_forbidden", "FAIL", "Mode B 不得写入 raw files")
                errors += 1
            else:
                add(findings, gse, "raw_forbidden", "PASS", "raw files 不存在")
            missing_product = []
            for gse_id, gsm in sorted(samples):
                if array_raw:
                    outputs = []
                    for row in provenance:
                        if row.get("gsm") == gsm:
                            outputs.extend(
                                item
                                for item in row.get("output_matrix", "").split(";")
                                if item
                            )
                    if not outputs or any(
                        not (root / item).is_file() or (root / item).stat().st_size == 0
                        for item in outputs
                    ):
                        missing_product.append(gsm)
                    continue
                matrix_dir, _, _ = locate_outputs(root, gse_id, gsm)
                matrix = matrix_dir / "raw_feature_bc_matrix/matrix.mtx.gz"
                if not matrix.is_file() or matrix.stat().st_size == 0:
                    missing_product.append(gsm)
            if missing_product:
                add(
                    findings,
                    gse,
                    "matrix_retained",
                    "FAIL",
                    "缺少 processed 产物: " + ",".join(missing_product),
                )
                errors += 1
            else:
                add(findings, gse, "matrix_retained", "PASS", f"samples={len(samples)}")
            if not provenance:
                add(findings, gse, "conversion_provenance", "FAIL", "缺少 conversion provenance")
                errors += 1
            else:
                add(
                    findings,
                    gse,
                    "conversion_provenance",
                    "PASS",
                    f"rows={len(provenance)}",
                )
            if final_audit and any(row.get("status") != "PASS" for row in final_audit):
                add(findings, gse, "final_audit", "FAIL", "删除时 final-output audit 未全部通过")
                errors += 1
            elif final_audit:
                add(findings, gse, "final_audit", "PASS", "final-output audit PASS")
        elif policy["deletion_status"] == "pending":
            if not temporary:
                add(
                    findings,
                    gse,
                    "temporary_present",
                    "FAIL",
                    "Mode B pending 但 temporary raw files 不存在",
                )
                errors += 1
            else:
                add(
                    findings,
                    gse,
                    "temporary_present",
                    "PASS",
                    f"files={len(temporary)}",
                )
            if deletion_log:
                add(findings, gse, "no_premature_delete", "FAIL", "pending 时已有删除日志")
                errors += 1
            else:
                add(findings, gse, "no_premature_delete", "PASS", "尚未删除")
        else:
            add(
                findings,
                gse,
                "blocked_or_other",
                "PASS" if policy["deletion_status"] == "blocked" else "FAIL",
                f"deletion_status={policy['deletion_status']}",
            )
            if policy["deletion_status"] != "blocked":
                errors += 1

    for path in temporary:
        gsm = infer_gsm(path, root)
        add(findings, gse, "temporary_file", "INFO", path.relative_to(root).as_posix(), gsm)

    write_tsv_atomic(
        output,
        ["gse", "gsm", "check", "status", "message"],
        findings,
    )
    print(
        f"AUDIT storage_policy errors={errors} checks={len(findings)} report={output}"
    )
    for row in findings:
        if row["status"] == "FAIL":
            print(f"ERROR {row['check']}: {row['message']}")
    refresh_report(root)
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
