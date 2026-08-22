#!/usr/bin/env python3
"""Create a self-contained GEO/GSE acquisition project without overwriting data."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from project_layout import default_policy, write_storage_policy

DONOR_HEADER = "gse\tdonor_id\tsex\tage\torganism\tnotes\n"
PLATFORM_HEADER = (
    "gse\tgpl\ttitle\ttechnology\tassay_type\traw_file_type\t"
    "array_type\tannotation_version\n"
)
ASSAY_HEADER = "gse\tgsm\tgpl\tassay_type\traw_file_type\tworkflow\tevidence\n"
EXPECTED_HEADER = (
    "gse\tgsm\tsrx\tsrr\trun_alias\tlane\tlibrary_layout\tread_structure\t"
    "expected_spots\tcb_length\tumi_length\tngdc_run_page\tngdc_url\n"
)
SAMPLE_HEADER = (
    "gse\tgsm\ttitle\torganism\ttissue\tcondition\ttreatment\tdonor_subject\t"
    "sex\tage\tbatch\tlibrary_strategy\tlibrary_source\tlibrary_selection\t"
    "platform\tinstrument_model\tchemistry\tsrx_list\tsrr_list\trun_count\t"
    "lane_count\tread_structure\tngdc_coverage\tprovenance\tselected_source\t"
    "final_product\texpected_bytes\tstatus\tnotes\n"
)
CHARACTERISTICS_HEADER = "gse\tgsm\tkey\tvalue\tsource_order\n"
MAPPING_HEADER = "gse\tgsm\tsrx\tsrr\trun_alias\tlane\n"
STUDY_HEADER = (
    "gse\ttitle\tsummary\toverall_design\torganism\tbioproject\tplatforms\t"
    "expected_samples\texpected_runs\tpublication\tmetadata_retrieved_at\n"
)


def write_new(path: Path, content: str) -> None:
    if path.exists():
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".tmp")
    temp.write_text(content)
    os.replace(temp, path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gse", required=True)
    parser.add_argument("--output-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--final-product",
        choices=(
            "pending",
            "fastq",
            "sra",
            "matrix_velocity",
            "CEL",
            "IDAT",
            "intensity",
            "processed",
        ),
        default="fastq",
    )
    parser.add_argument("--retain-raw-files", choices=("true", "false"))
    parser.add_argument(
        "--retain-raw-fastq",
        choices=("true", "false"),
        help="兼容旧参数；等价于 --retain-raw-files",
    )
    parser.add_argument(
        "--assay-type",
        default="",
        choices=(
            "",
            "pending",
            "RNA-seq",
            "ATAC-seq",
            "ChIP-seq",
            "miRNA-seq",
            "sequencing",
            "microarray",
            "methylation",
        ),
    )
    parser.add_argument(
        "--raw-file-type",
        default="",
        choices=("", "pending", "FASTQ", "SRA", "CEL", "IDAT"),
    )
    parser.add_argument("--max-project-gib", type=int, default=500)
    parser.add_argument("--monitor-interval", type=int, default=1800)
    args = parser.parse_args()

    gse = args.gse.upper()
    if not re.fullmatch(r"GSE\d+", gse):
        raise SystemExit(f"Invalid GSE accession: {args.gse}")
    if args.max_project_gib <= 0 or args.monitor_interval < 60:
        raise SystemExit("Storage cap must be positive and monitor interval >= 60")
    retain_flag = args.retain_raw_files or args.retain_raw_fastq
    if retain_flag is None:
        raise SystemExit("必须指定 --retain-raw-files true|false，不允许默认")
    retain_raw = retain_flag == "true"
    mode_b_products = {"matrix_velocity", "intensity", "processed"}
    if not retain_raw and args.final_product not in mode_b_products:
        raise SystemExit(
            "Mode B (--retain-raw-files false) 需要 --final-product "
            "matrix_velocity|intensity|processed"
        )

    output_root = args.output_root.resolve()
    geo_root = output_root if output_root.name.upper() == "GEO" else output_root / "GEO"
    project = geo_root / gse
    for directory in (
        project / "metadata",
        project / "metadata/download_manifests",
        project / "raw",
        project / "temporary",
        project / "processed",
        project / "annotation/platform_annotation",
        project / "qc",
        project / "reports/logs",
        project / "reports/status",
        project / "scripts",
    ):
        directory.mkdir(parents=True, exist_ok=True)

    write_new(
        project / "README.md",
        f"# {gse}\n\n"
        "Study -> Donor -> Sample (GSM) -> raw assay file。\n\n"
        "- 元数据：`metadata/`\n"
        "- 原始文件：`raw/GSM*/`（Mode A）或 `temporary/GSM*/`（Mode B）\n"
        "- 平台注释：`annotation/platform_annotation/`\n"
        "- QC：`qc/`\n"
        "- 报告：`reports/report.html`\n",
    )
    write_new(project / "metadata/study_metadata.tsv", STUDY_HEADER)
    write_new(project / "metadata/donor_metadata.tsv", DONOR_HEADER)
    write_new(project / "metadata/platform_metadata.tsv", PLATFORM_HEADER)
    write_new(project / "metadata/assay_routing.tsv", ASSAY_HEADER)
    write_new(
        project / "annotation/platform_annotation/probe_to_gene_mapping.tsv",
        "gpl\tprobe_id\tgene_symbol\tentrez_id\tannotation_version\n",
    )
    write_new(project / "metadata/sample_metadata.tsv", SAMPLE_HEADER)
    write_new(
        project / "metadata/sample_characteristics.tsv",
        CHARACTERISTICS_HEADER,
    )
    write_new(project / "metadata/srr_gsm_mapping.tsv", MAPPING_HEADER)
    write_new(project / "metadata/expected_runs.tsv", EXPECTED_HEADER)
    write_new(
        project / "metadata/acquisition_config.tsv",
        "key\tvalue\n"
        f"gse\t{gse}\n"
        f"final_product\t{args.final_product}\n"
        f"retain_raw_files\t{retain_flag}\n"
        f"assay_type\t{args.assay_type}\n"
        f"raw_file_type\t{args.raw_file_type}\n"
        f"max_project_bytes\t{args.max_project_gib * 1024**3}\n"
        f"monitor_interval_seconds\t{args.monitor_interval}\n"
        "max_same_error_attempts\t3\n"
        "retry_delays_seconds\t0;30;120\n"
        "provider_priority\tngdc_gsa;ngdc_insdc;ena_submitted;ena_fastq;ncbi_sra\n",
    )
    if not (project / "metadata/storage_policy.tsv").exists():
        write_storage_policy(
            project,
            default_policy(
                gse,
                retain_raw,
                assay_type=args.assay_type,
                raw_file_type=args.raw_file_type,
            ),
        )
    write_new(
        project / "pixi.toml",
        "[workspace]\n"
        f'name = "{gse.lower()}-acquisition"\n'
        'channels = ["conda-forge", "bioconda"]\n'
        'platforms = ["linux-64"]\n\n'
        "[dependencies]\n"
        'python = ">=3.12,<3.13"\n'
        'sra-tools = "*"\n'
        'star = "*"\n'
        'samtools = "*"\n'
        'fastqc = "*"\n'
        'multiqc = "*"\n'
        'pigz = "*"\n'
        'seqkit = "*"\n'
        'aria2 = "*"\n'
        'curl = "*"\n'
        'scipy = "*"\n'
        'h5py = "*"\n\n'
        'numpy = "*"\n'
        'loompy = "*"\n'
        'tmux = "*"\n\n'
        "[tasks]\n"
        'check-env = "python --version && fasterq-dump --version && '
        'STAR --version && samtools --version | head -n 1 && '
        'fastqc --version && multiqc --version && aria2c --version | head -n 1"\n',
    )
    write_new(
        project / "scripts/run_all.sh",
        "#!/usr/bin/env bash\n"
        "set -Eeuo pipefail\n"
        'ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)\n'
        'MANIFEST="$ROOT/metadata/source_manifest.tsv"\n'
        'REPORTER="$ROOT/scripts/build_report.py"\n'
        'MULTIQC_HTML="$ROOT/reports/multiqc_data/embedded_multiqc.html"\n'
        'refresh_report() {\n'
        '  local args=(python "$REPORTER" --root "$ROOT")\n'
        '  [[ -s "$MULTIQC_HTML" ]] && args+=(--multiqc-html "$MULTIQC_HTML")\n'
        '  "${args[@]}" || echo "WARNING: HTML 报告刷新失败" >&2\n'
        '}\n'
        "trap refresh_report EXIT\n"
        '[[ -s "$MANIFEST" ]] || { echo "Missing $MANIFEST" >&2; exit 2; }\n'
        "while IFS= read -r run; do\n"
        '  [[ -n "$run" ]] || continue\n'
        '  "$ROOT/scripts/download_run.sh" "$ROOT" "$run"\n'
        "done < <(awk -F '\\t' 'NR>1 {gsub(/\\r/,\"\",$4); print $4}' \"$MANIFEST\")\n"
        'if [[ -d "$ROOT/reports/fastqc" ]]; then\n'
        '  MULTIQC_DIR="$ROOT/reports/multiqc_data"\n'
        '  mkdir -p "$MULTIQC_DIR"\n'
        '  multiqc --force --data-dir --data-format json '
        '--filename embedded_multiqc.html --outdir "$MULTIQC_DIR" '
        '"$ROOT/reports/fastqc"\n'
        '  refresh_report\n'
        "fi\n"
        'python "$ROOT/scripts/audit_download_evidence.py" --root "$ROOT"\n'
        'python "$ROOT/scripts/audit_storage_policy.py" --root "$ROOT"\n'
        'if [[ -s "$MULTIQC_HTML" ]]; then\n'
        '  python "$REPORTER" --root "$ROOT" --multiqc-html "$MULTIQC_HTML" '
        '--consume-multiqc\n'
        "else\n"
        "  refresh_report\n"
        "fi\n"
        "trap - EXIT\n",
    )

    skill_scripts = Path(__file__).resolve().parent
    for source in skill_scripts.iterdir():
        if source.name in {Path(__file__).name, "self_test.py"} or not source.is_file():
            continue
        target = project / "scripts" / source.name
        if not target.exists():
            shutil.copy2(source, target)
    for script in (project / "scripts").iterdir():
        if script.is_file() and script.suffix in {".py", ".sh"}:
            script.chmod(script.stat().st_mode | 0o111)

    subprocess.run(
        [
            sys.executable,
            str(project / "scripts/build_report.py"),
            "--root",
            str(project),
        ],
        check=True,
    )

    print(f"Created/reused {project}")
    print(f"Next: populate metadata, then run `cd {project} && pixi lock`")


if __name__ == "__main__":
    main()
