#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
    echo "Usage: $0 <GSE-project-root> <run-accession>" >&2
    exit 2
}

[[ $# -eq 2 ]] || usage
ROOT=$(cd "$1" && pwd)
RUN=$2
MANIFEST="$ROOT/metadata/source_manifest.tsv"
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
VALIDATOR="$SCRIPT_DIR/validate_fastq_pair.py"
[[ -s "$MANIFEST" ]] || { echo "Missing $MANIFEST" >&2; exit 2; }
[[ -s "$VALIDATOR" ]] || { echo "Missing $VALIDATOR" >&2; exit 2; }

mapfile -t ROW < <(
    python - "$MANIFEST" "$RUN" <<'PY'
import csv
import sys

path, run = sys.argv[1:]
with open(path, newline="") as handle:
    matches = [
        row for row in csv.DictReader(handle, delimiter="\t")
        if row["srr"].rstrip("\r") == run
    ]
if len(matches) != 1:
    raise SystemExit(f"Expected one source-manifest row for {run}, found {len(matches)}")
row = matches[0]
fields = [
    "gse", "gsm", "srr", "library_layout", "expected_spots",
    "cb_length", "umi_length", "selected_source", "selected_provenance",
    "selected_urls", "selected_bytes", "selected_md5", "read_roles",
    "final_product", "fallback_reason",
]
for field in fields:
    print(row.get(field, "").rstrip("\r").replace("\n", " "))
PY
)
(( ${#ROW[@]} == 15 )) || { echo "Manifest parser failed for $RUN" >&2; exit 2; }
GSE=${ROW[0]}
GSM=${ROW[1]}
SRR=${ROW[2]}
LAYOUT=${ROW[3]}
EXPECTED_SPOTS=${ROW[4]}
CB_LENGTH=${ROW[5]:-0}
UMI_LENGTH=${ROW[6]:-0}
SOURCE=${ROW[7]}
PROVENANCE=${ROW[8]}
URLS_TEXT=${ROW[9]}
BYTES_TEXT=${ROW[10]}
MD5_TEXT=${ROW[11]}
ROLES_TEXT=${ROW[12]}
FINAL_PRODUCT=${ROW[13]}
FALLBACK_REASON=${ROW[14]}

[[ "$SRR" == "$RUN" ]] || { echo "Run parser mismatch" >&2; exit 2; }
SAMPLE_DIR="$ROOT/$GSM"
FASTQ_DIR="$SAMPLE_DIR/fastq"
SRA_DIR="$SAMPLE_DIR/sra"
WORK_DIR="$SAMPLE_DIR/work/$SRR"
LOG_DIR="$ROOT/reports/logs"
STATUS_DIR="$ROOT/reports/status"
DOWNLOAD_MANIFEST="$SAMPLE_DIR/download_manifest.tsv"
COMPLETE_MARKER="$STATUS_DIR/${SRR}.complete"
mkdir -p "$FASTQ_DIR" "$SRA_DIR" "$WORK_DIR" "$LOG_DIR" "$STATUS_DIR"
exec > >(tee -a "$LOG_DIR/${GSM}_${SRR}.log") 2>&1

IFS=';' read -r -a URLS <<< "$URLS_TEXT"
IFS=';' read -r -a EXPECTED_BYTES <<< "$BYTES_TEXT"
IFS=';' read -r -a EXPECTED_MD5 <<< "$MD5_TEXT"
IFS=';' read -r -a ROLES <<< "$ROLES_TEXT"
(( ${#URLS[@]} == ${#ROLES[@]} )) || {
    echo "URL/read-role array mismatch for $SRR" >&2
    exit 2
}

MAX_ATTEMPTS=${GEO_SRA_MAX_ATTEMPTS:-3}
DOWNLOAD_CONNECTIONS=${GEO_SRA_CONNECTIONS:-4}
SRA_THREADS=${GEO_SRA_SRA_THREADS:-8}
COMPRESS_THREADS=${GEO_SRA_COMPRESS_THREADS:-8}
NGDC_DIRECT=${GEO_SRA_NGDC_DIRECT:-1}
RUN_FASTQC=${GEO_SRA_RUN_FASTQC:-1}

array_value() {
    local index=$1
    shift
    local -a values=("$@")
    if (( index < ${#values[@]} )); then
        printf '%s' "${values[$index]}"
    fi
}

validate_downloaded_file() {
    local path=$1 role=$2 expected_size=$3 expected_md5=$4
    [[ -s "$path" ]] || return 1
    if [[ -n "$expected_size" ]]; then
        [[ "$expected_size" =~ ^[0-9]+$ ]] || return 1
        (( $(stat -c %s "$path") == expected_size )) || return 1
    fi
    if [[ -n "$expected_md5" ]]; then
        printf '%s  %s\n' "$expected_md5" "$path" | md5sum -c - || return 1
    fi
    case "$role" in
        R1|R2|I1|I2) gzip -t "$path" || return 1 ;;
        SRA) vdb-validate "$path" || return 1 ;;
        BAM) samtools quickcheck "$path" || return 1 ;;
        *) return 1 ;;
    esac
    return 0
}

download_atomic() {
    local url=$1 output=$2 role=$3 expected_size=$4 expected_md5=$5
    local part="${output}.part"
    local control="${part}.aria2"
    local attempt current_size
    if [[ -f "$output" ]]; then
        if validate_downloaded_file "$output" "$role" "$expected_size" "$expected_md5"; then
            echo "Reusing validated $(basename "$output")"
            return 0
        fi
        echo "Existing final file is invalid; replacing: $output" >&2
        unlink "$output"
    fi
    if [[ -f "$part" && ! -f "$control" ]]; then
        echo "Partial lacks aria2 piece metadata; restarting: $part" >&2
        unlink "$part"
    fi
    if [[ -n "$expected_size" && -f "$part" ]] \
        && (( $(stat -c %s "$part") > expected_size )); then
        unlink "$part"
        unlink "$control" 2>/dev/null || true
    fi

    local -a aria=(
        aria2c
        --allow-overwrite=true
        --auto-file-renaming=false
        --check-integrity=true
        --connect-timeout=30
        --continue=true
        --console-log-level=notice
        --file-allocation=none
        --max-connection-per-server="$DOWNLOAD_CONNECTIONS"
        --max-tries=10
        --min-split-size=16M
        --retry-wait=3
        --split="$DOWNLOAD_CONNECTIONS"
        --summary-interval=30
        --timeout=30
    )
    [[ -n "$expected_md5" ]] && aria+=(--checksum="md5=$expected_md5")

    for ((attempt=1; attempt<=MAX_ATTEMPTS; attempt++)); do
        current_size=0
        [[ -f "$part" ]] && current_size=$(stat -c %s "$part")
        echo "Downloading $(basename "$output") attempt=$attempt offset=$current_size"
        if [[ "$SOURCE" == ngdc_* && "$NGDC_DIRECT" == 1 ]]; then
            env -u http_proxy -u https_proxy -u all_proxy \
                -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY \
                "${aria[@]}" --dir="$(dirname "$part")" \
                --out="$(basename "$part")" "$url" || true
        else
            "${aria[@]}" --dir="$(dirname "$part")" \
                --out="$(basename "$part")" "$url" || true
        fi
        if validate_downloaded_file "$part" "$role" "$expected_size" "$expected_md5"; then
            unlink "$control" 2>/dev/null || true
            mv "$part" "$output"
            return 0
        fi
        if [[ -f "$part" && -n "$expected_size" ]] \
            && (( $(stat -c %s "$part") == expected_size )); then
            echo "Full-size transfer failed integrity; restarting from zero" >&2
            unlink "$part"
            unlink "$control" 2>/dev/null || true
        fi
    done
    echo "Download failed after $MAX_ATTEMPTS attempts: $url" >&2
    return 1
}

prefetch_ncbi() {
    local output=$1
    local attempt source_file prefetch_root="$WORK_DIR/ncbi"
    for ((attempt=1; attempt<=MAX_ATTEMPTS; attempt++)); do
        unlink "$output" 2>/dev/null || true
        find "$prefetch_root" -type f -delete 2>/dev/null || true
        find "$prefetch_root" -depth -type d -empty -delete 2>/dev/null || true
        mkdir -p "$prefetch_root"
        prefetch "$SRR" --max-size u -O "$prefetch_root" || continue
        source_file="$prefetch_root/$SRR/$SRR.sra"
        [[ -s "$source_file" ]] || continue
        if vdb-validate "$source_file"; then
            mv "$source_file" "$output"
            return 0
        fi
    done
    echo "NCBI prefetch failed after $MAX_ATTEMPTS attempts: $SRR" >&2
    return 1
}

compress_atomic() {
    local input=$1 output=$2
    pigz -p "$COMPRESS_THREADS" -c "$input" > "${output}.tmp"
    gzip -t "${output}.tmp"
    mv "${output}.tmp" "$output"
    unlink "$input"
}

SRA_FILE=""
R1_FILE=""
R2_FILE=""
declare -a RETAINED_FILES=()

if [[ "$SOURCE" == "ncbi_sra" ]]; then
    SRA_FILE="$SRA_DIR/${SRR}.sra"
    if [[ ! -s "$SRA_FILE" ]] || ! vdb-validate "$SRA_FILE"; then
        prefetch_ncbi "$SRA_FILE"
    fi
    RETAINED_FILES+=("$SRA_FILE")
else
    for index in "${!URLS[@]}"; do
        url=${URLS[$index]}
        role=${ROLES[$index]}
        expected_size=$(array_value "$index" "${EXPECTED_BYTES[@]}")
        expected_md5=$(array_value "$index" "${EXPECTED_MD5[@]}")
        case "$role" in
            SRA)
                output="$SRA_DIR/${SRR}.sra"
                SRA_FILE=$output
                ;;
            R1|R2|I1|I2)
                output="$FASTQ_DIR/${SRR}_${role}.fastq.gz"
                [[ "$role" == R1 ]] && R1_FILE=$output
                [[ "$role" == R2 ]] && R2_FILE=$output
                ;;
            BAM)
                output="$SAMPLE_DIR/${SRR}.bam"
                ;;
            *)
                echo "Unsupported role: $role" >&2
                exit 2
                ;;
        esac
        download_atomic "$url" "$output" "$role" "$expected_size" "$expected_md5"
        RETAINED_FILES+=("$output")
    done
fi

if [[ -n "$SRA_FILE" && "$FINAL_PRODUCT" != "sra" ]]; then
    CONVERT_DIR="$WORK_DIR/fasterq"
    SCRATCH="$WORK_DIR/fasterq_tmp"
    mkdir -p "$CONVERT_DIR" "$SCRATCH"
    fasterq-dump --split-files --threads "$SRA_THREADS" \
        --temp "$SCRATCH" --outdir "$CONVERT_DIR" --size-check only "$SRA_FILE"
    fasterq-dump --split-files --threads "$SRA_THREADS" \
        --temp "$SCRATCH" --outdir "$CONVERT_DIR" "$SRA_FILE"
    if [[ "$LAYOUT" == "PAIRED" ]]; then
        [[ -s "$CONVERT_DIR/${SRR}_1.fastq" && -s "$CONVERT_DIR/${SRR}_2.fastq" ]] || {
            echo "Expected paired fasterq outputs for $SRR" >&2
            exit 1
        }
        R1_FILE="$FASTQ_DIR/${SRR}_R1.fastq.gz"
        R2_FILE="$FASTQ_DIR/${SRR}_R2.fastq.gz"
        compress_atomic "$CONVERT_DIR/${SRR}_1.fastq" "$R1_FILE"
        compress_atomic "$CONVERT_DIR/${SRR}_2.fastq" "$R2_FILE"
        RETAINED_FILES+=("$R1_FILE" "$R2_FILE")
    else
        [[ -s "$CONVERT_DIR/${SRR}.fastq" || -s "$CONVERT_DIR/${SRR}_1.fastq" ]] || {
            echo "Expected single-end fasterq output for $SRR" >&2
            exit 1
        }
        input="$CONVERT_DIR/${SRR}.fastq"
        [[ -s "$input" ]] || input="$CONVERT_DIR/${SRR}_1.fastq"
        R1_FILE="$FASTQ_DIR/${SRR}_R1.fastq.gz"
        compress_atomic "$input" "$R1_FILE"
        RETAINED_FILES+=("$R1_FILE")
    fi
fi

VALIDATION_REPORT="$WORK_DIR/fastq_validation.json"
if [[ "$FINAL_PRODUCT" != "sra" ]]; then
    [[ -s "$R1_FILE" ]] || { echo "Missing retained R1 for $SRR" >&2; exit 1; }
    validator_args=(
        python "$VALIDATOR"
        --srr "$SRR"
        --r1 "$R1_FILE"
        --report "$VALIDATION_REPORT"
    )
    [[ -n "$R2_FILE" ]] && validator_args+=(--r2 "$R2_FILE")
    [[ -n "$EXPECTED_SPOTS" ]] && validator_args+=(--expected-spots "$EXPECTED_SPOTS")
    [[ "$CB_LENGTH" =~ ^[0-9]+$ ]] && validator_args+=(--cb-length "$CB_LENGTH")
    [[ "$UMI_LENGTH" =~ ^[0-9]+$ ]] && validator_args+=(--umi-length "$UMI_LENGTH")
    "${validator_args[@]}"
    if [[ "$RUN_FASTQC" == 1 ]]; then
        FASTQC_DIR="$ROOT/reports/fastqc/$GSM"
        mkdir -p "$FASTQC_DIR"
        fastqc_args=(fastqc --threads "$COMPRESS_THREADS" --outdir "$FASTQC_DIR" "$R1_FILE")
        [[ -n "$R2_FILE" ]] && fastqc_args+=("$R2_FILE")
        "${fastqc_args[@]}"
    fi
else
    vdb-validate "$SRA_FILE"
fi

python - "$DOWNLOAD_MANIFEST" "$GSE" "$GSM" "$SRR" "$SOURCE" "$PROVENANCE" \
    "$FINAL_PRODUCT" "$URLS_TEXT" "$BYTES_TEXT" "$MD5_TEXT" "$EXPECTED_SPOTS" \
    "$VALIDATION_REPORT" "${RETAINED_FILES[@]}" <<'PY'
import csv
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

(
    manifest_path, gse, gsm, srr, source, provenance, final_product, urls,
    expected_bytes, expected_md5, expected_spots, validation_path, *files
) = sys.argv[1:]

def md5(path):
    digest = hashlib.md5()
    with open(path, "rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()

validation = {}
if validation_path and Path(validation_path).is_file():
    validation = json.loads(Path(validation_path).read_text())
observed_files = [Path(path) for path in files if Path(path).is_file()]
row = {
    "gse": gse,
    "gsm": gsm,
    "srr": srr,
    "source": source,
    "provenance": provenance,
    "final_product": final_product,
    "urls": urls,
    "expected_bytes": expected_bytes,
    "observed_bytes": ";".join(str(path.stat().st_size) for path in observed_files),
    "expected_md5": expected_md5,
    "observed_md5": ";".join(md5(path) for path in observed_files),
    "expected_spots": expected_spots,
    "observed_r1": str(validation.get("reads_per_mate", "")),
    "observed_r2": str(validation.get("reads_per_mate", "")) if validation.get("r2") else "",
    "validation": "PASS",
    "completed_at": datetime.now(timezone.utc).astimezone().isoformat(),
}
fields = list(row)
path = Path(manifest_path)
existing = []
if path.is_file():
    with path.open(newline="") as handle:
        existing = [item for item in csv.DictReader(handle, delimiter="\t") if item["srr"] != srr]
path.parent.mkdir(parents=True, exist_ok=True)
temp = path.with_suffix(path.suffix + ".tmp")
with temp.open("w", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t", lineterminator="\n")
    writer.writeheader()
    writer.writerows(existing + [row])
os.replace(temp, path)
PY

printf 'gse\t%s\ngsm\t%s\nsrr\t%s\nsource\t%s\nprovenance\t%s\nfinal_product\t%s\ncompleted_at\t%s\n' \
    "$GSE" "$GSM" "$SRR" "$SOURCE" "$PROVENANCE" "$FINAL_PRODUCT" "$(date -Is)" \
    > "${COMPLETE_MARKER}.tmp"
mv "${COMPLETE_MARKER}.tmp" "$COMPLETE_MARKER"

if [[ "$FINAL_PRODUCT" == "fastq" ]]; then
    unlink "$SRA_FILE" 2>/dev/null || true
    find "$WORK_DIR" -type f -delete
    find "$WORK_DIR" -depth -type d -empty -delete
fi
if [[ -f "$ROOT/scripts/build_report.py" ]]; then
    python "$ROOT/scripts/build_report.py" --root "$ROOT" \
        || echo "WARNING: HTML 报告刷新失败" >&2
fi
echo "[$(date -Is)] COMPLETE $GSE/$GSM/$SRR source=$SOURCE product=$FINAL_PRODUCT"
