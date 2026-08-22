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
STATE_HELPER="$SCRIPT_DIR/transfer_state.py"
LAYOUT_HELPER="$SCRIPT_DIR/project_layout.py"
[[ -s "$MANIFEST" ]] || { echo "Missing $MANIFEST" >&2; exit 2; }
[[ -s "$VALIDATOR" && -s "$STATE_HELPER" && -s "$LAYOUT_HELPER" ]] || {
    echo "Missing download helper scripts" >&2
    exit 2
}

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

[[ "$SRR" == "$RUN" ]] || { echo "Run parser mismatch" >&2; exit 2; }
eval "$(python "$LAYOUT_HELPER" --root "$ROOT" --gsm "$GSM" --srr "$SRR" --print-dirs)"
[[ -n "${FASTQ_DIR:-}" && -n "${WORK_DIR:-}" && -n "${RETAIN_RAW:-}" ]] || {
    echo "Failed to resolve project layout for $SRR" >&2
    exit 2
}
if [[ "$RETAIN_RAW" != true && "$FINAL_PRODUCT" != matrix_velocity && "$FINAL_PRODUCT" != matrix_10x && "$FINAL_PRODUCT" != gene_count_matrix ]]; then
    echo "Mode B requires final_product=matrix_velocity|matrix_10x|gene_count_matrix" >&2
    exit 2
fi
STAGING_DIR="$WORK_DIR/staging"
DOWNLOAD_DIR="$STAGING_DIR/download"
CONVERT_DIR="$STAGING_DIR/fasterq"
SCRATCH="$WORK_DIR/fasterq_tmp"
QUARANTINE_DIR="$WORK_DIR/quarantine"
LOG_DIR="$ROOT/reports/logs"
STATUS_DIR="$ROOT/reports/status"
COMPLETE_MARKER="$STATUS_DIR/${SRR}.complete"
TRANSFER_STATE="$STATUS_DIR/${SRR}.transfer.json"
PUBLISH_JOURNAL="$WORK_DIR/publish.json"
VALIDATION_REPORT="$WORK_DIR/fastq_validation.json"
mkdir -p "$DOWNLOAD_DIR" "$CONVERT_DIR" "$SCRATCH" "$QUARANTINE_DIR" \
    "$LOG_DIR" "$STATUS_DIR" "$(dirname "$DOWNLOAD_MANIFEST")"
if [[ "$FINAL_PRODUCT" == sra ]]; then
    mkdir -p "$SRA_DIR"
else
    mkdir -p "$FASTQ_DIR"
fi
exec > >(tee -a "$LOG_DIR/${GSM}_${SRR}.log") 2>&1

exec 8>"$WORK_DIR/run.lock"
flock -n 8 || {
    echo "Another process is already handling $SRR" >&2
    exit 75
}

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
RETRY_DELAYS=${GEO_SRA_RETRY_DELAYS:-0,30,120}
[[ "$MAX_ATTEMPTS" =~ ^[1-9][0-9]*$ ]] || {
    echo "GEO_SRA_MAX_ATTEMPTS must be a positive integer" >&2
    exit 2
}
IFS=',' read -r -a DELAYS <<< "$RETRY_DELAYS"

SOURCE_FINGERPRINT=$(
    python "$STATE_HELPER" fingerprint \
        --source "$SOURCE" --urls "$URLS_TEXT" --bytes "$BYTES_TEXT" \
        --md5 "$MD5_TEXT" --roles "$ROLES_TEXT" --final-product "$FINAL_PRODUCT"
)

state_update() {
    python "$STATE_HELPER" update --path "$TRANSFER_STATE" --run "$SRR" \
        --fingerprint "$SOURCE_FINGERPRINT" "$@"
}

state_get() {
    python "$STATE_HELPER" get --path "$TRANSFER_STATE" --field "$1" \
        --default "${2:-}"
}

state_update --phase preflight --status in_progress --clear-error

array_value() {
    local index=$1
    shift
    local -a values=("$@")
    if (( index < ${#values[@]} )); then
        printf '%s' "${values[$index]}"
    fi
}

relative_path() {
    python - "$ROOT" "$1" <<'PY'
import os
import sys
print(os.path.relpath(sys.argv[2], sys.argv[1]))
PY
}

quarantine_paths() {
    local label=$1
    shift
    local stamp target path
    stamp=$(date +%Y%m%dT%H%M%S)
    for path in "$@"; do
        [[ -e "$path" ]] || continue
        target="$QUARANTINE_DIR/${stamp}_${label}_$(basename "$path")"
        mv "$path" "$target"
        echo "Quarantined $(relative_path "$path") -> $(relative_path "$target")" >&2
    done
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
}

probe_remote() {
    local url=$1 header=$2
    local -a command=(
        curl -fsSIL --connect-timeout 20 --max-time 40 --retry 0
        --output "$header" "$url"
    )
    if [[ "$SOURCE" == ngdc_* && "$NGDC_DIRECT" == 1 ]]; then
        env -u http_proxy -u https_proxy -u all_proxy \
            -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY "${command[@]}" || return 1
    else
        "${command[@]}" || return 1
    fi
}

header_value() {
    python - "$1" "$2" <<'PY'
import sys
from pathlib import Path

path, wanted = Path(sys.argv[1]), sys.argv[2].lower()
blocks = path.read_text(errors="replace").replace("\r\n", "\n").split("\n\n")
headers = {}
for line in next((block for block in reversed(blocks) if block.startswith("HTTP/")), "").splitlines()[1:]:
    if ":" in line:
        key, value = line.split(":", 1)
        headers[key.strip().lower()] = value.strip()
print(headers.get(wanted, ""))
PY
}

record_failure() {
    local error_class=$1 error_key=$2 message=$3 fatal=${4:-0}
    local count status=retryable_failed
    (( fatal == 1 )) && status=terminal_failed
    count=$(state_update --phase transfer --status "$status" \
        --error-class "$error_class" --error-key "$error_key" \
        --message "$message" --print-field same_error_count)
    if (( fatal == 1 || count >= MAX_ATTEMPTS )); then
        state_update --phase transfer --status terminal_failed >/dev/null
        echo "Terminal failure for $SRR: $error_class: $message" >&2
        return 10
    fi
    local delay=${DELAYS[$count]:-${DELAYS[-1]:-0}}
    [[ "$delay" =~ ^[0-9]+$ ]] || delay=0
    (( delay > 0 )) && sleep "$delay"
    return 0
}

download_staged() {
    local url=$1 staged=$2 role=$3 expected_size=$4 expected_md5=$5
    local part="${staged}.part"
    local control="${part}.aria2"
    local resume_meta="${part}.resume.json"
    local headers="${part}.headers"
    local etag="" modified="" remote_size="" offset=0 rc=0 error_class error_key count
    mkdir -p "$(dirname "$staged")"
    if validate_downloaded_file "$staged" "$role" "$expected_size" "$expected_md5"; then
        echo "Reusing validated staged $(basename "$staged")"
        return 0
    fi
    [[ ! -e "$staged" ]] || quarantine_paths invalid_staged "$staged"

    if [[ -f "$part" && ( ! -f "$control" || ! -f "$resume_meta" ) ]]; then
        quarantine_paths untrusted_partial "$part" "$control" "$resume_meta"
    fi
    if [[ ! -f "$part" && ( -f "$control" || -f "$resume_meta" ) ]]; then
        quarantine_paths orphan_resume "$control" "$resume_meta"
    fi
    if probe_remote "$url" "$headers"; then
        etag=$(header_value "$headers" etag)
        modified=$(header_value "$headers" last-modified)
        remote_size=$(header_value "$headers" content-length)
    fi
    unlink "$headers" 2>/dev/null || true
    if [[ -n "$expected_size" && -n "$remote_size" && "$remote_size" =~ ^[0-9]+$ ]] \
        && (( remote_size != expected_size )); then
        record_failure remote_changed "${role}:remote_changed" \
            "Content-Length $remote_size differs from expected $expected_size" 1 || true
        return 1
    fi
    if [[ -f "$part" ]]; then
        set +e
        python "$STATE_HELPER" resume-check --path "$resume_meta" \
            --fingerprint "$SOURCE_FINGERPRINT" --url "$url" --role "$role" \
            --expected-bytes "$expected_size" --expected-md5 "$expected_md5" \
            --etag "$etag" --last-modified "$modified" --remote-bytes "$remote_size"
        rc=$?
        set -e
        if (( rc != 0 )); then
            if (( rc == 10 )); then
                quarantine_paths stale_partial "$part" "$control" "$resume_meta"
            else
                return "$rc"
            fi
        fi
    fi
    python "$STATE_HELPER" resume-check --path "$resume_meta" \
        --fingerprint "$SOURCE_FINGERPRINT" --url "$url" --role "$role" \
        --expected-bytes "$expected_size" --expected-md5 "$expected_md5" \
        --etag "$etag" --last-modified "$modified" --remote-bytes "$remote_size"

    while true; do
        offset=0
        [[ -f "$part" ]] && offset=$(stat -c %s "$part")
        state_update --phase transfer --status in_progress --attempt-delta 1 \
            --bytes-resumed "$offset" >/dev/null
        (( offset > 0 )) && state_update --resume-delta 1 >/dev/null
        echo "Downloading $(basename "$staged") offset=$offset"
        local -a aria=(
            aria2c --allow-overwrite=true --auto-file-renaming=false
            --check-integrity=true --connect-timeout=30 --continue=true
            --console-log-level=notice --file-allocation=none
            --max-connection-per-server="$DOWNLOAD_CONNECTIONS" --max-tries=1
            --min-split-size=16M --retry-wait=0 --split="$DOWNLOAD_CONNECTIONS"
            --summary-interval=30 --timeout=30
        )
        [[ -n "$expected_md5" ]] && aria+=(--checksum="md5=$expected_md5")
        if [[ "$SOURCE" == ngdc_* && "$NGDC_DIRECT" == 1 ]]; then
            env -u http_proxy -u https_proxy -u all_proxy \
                -u HTTP_PROXY -u HTTPS_PROXY -u ALL_PROXY \
                "${aria[@]}" --dir="$(dirname "$part")" \
                --out="$(basename "$part")" "$url" && rc=0 || rc=$?
        else
            "${aria[@]}" --dir="$(dirname "$part")" \
                --out="$(basename "$part")" "$url" && rc=0 || rc=$?
        fi
        if validate_downloaded_file "$part" "$role" "$expected_size" "$expected_md5"; then
            unlink "$control" 2>/dev/null || true
            unlink "$resume_meta" 2>/dev/null || true
            mv "$part" "$staged"
            state_update --phase transfer --status in_progress --clear-error >/dev/null
            return 0
        fi
        error_class=network_interrupted
        if [[ -f "$part" && -n "$expected_size" ]] \
            && (( $(stat -c %s "$part") == expected_size )); then
            error_class=checksum_or_integrity
            quarantine_paths corrupt_full "$part" "$control" "$resume_meta"
            python "$STATE_HELPER" resume-check --path "$resume_meta" \
                --fingerprint "$SOURCE_FINGERPRINT" --url "$url" --role "$role" \
                --expected-bytes "$expected_size" --expected-md5 "$expected_md5" \
                --etag "$etag" --last-modified "$modified" --remote-bytes "$remote_size"
        elif [[ -f "$part" && ! -f "$control" ]]; then
            quarantine_paths untrusted_partial "$part" "$resume_meta"
        fi
        error_key="${role}:${error_class}"
        if ! record_failure "$error_class" "$error_key" \
            "aria2 exit=$rc; validation did not pass"; then
            return 1
        fi
        count=$(state_get same_error_count 0)
        (( count < MAX_ATTEMPTS )) || return 1
    done
}

prefetch_staged() {
    local staged=$1
    local prefetch_root="$WORK_DIR/ncbi"
    local source_file="$prefetch_root/$SRR/$SRR.sra"
    local rc count error_class
    if validate_downloaded_file "$staged" SRA "" ""; then
        return 0
    fi
    while true; do
        mkdir -p "$prefetch_root"
        state_update --phase prefetch --status in_progress --attempt-delta 1 >/dev/null
        prefetch "$SRR" --max-size u -O "$prefetch_root" && rc=0 || rc=$?
        if [[ -s "$source_file" ]] && vdb-validate "$source_file"; then
            mv "$source_file" "$staged"
            state_update --phase prefetch --status in_progress --clear-error >/dev/null
            return 0
        fi
        error_class=network_interrupted
        if [[ -s "$source_file" ]]; then
            error_class=checksum_or_integrity
            quarantine_paths invalid_prefetch "$source_file"
        fi
        if ! record_failure "$error_class" "SRA:prefetch:${error_class}" \
            "prefetch exit=$rc; cache retained for resume"; then
            return 1
        fi
        count=$(state_get same_error_count 0)
        (( count < MAX_ATTEMPTS )) || return 1
    done
}

compress_staged() {
    local input=$1 output=$2
    local temp="${output}.tmp"
    if command -v pigz >/dev/null 2>&1; then
        pigz -p "$COMPRESS_THREADS" -c "$input" > "$temp"
    else
        gzip -c "$input" > "$temp"
    fi
    gzip -t "$temp"
    mv "$temp" "$output"
}

write_download_manifest() {
    python - "$ROOT" "$DOWNLOAD_MANIFEST" "$GSE" "$GSM" "$SRR" "$SOURCE" \
        "$PROVENANCE" "$FINAL_PRODUCT" "$URLS_TEXT" "$BYTES_TEXT" "$MD5_TEXT" \
        "$EXPECTED_SPOTS" "$VALIDATION_REPORT" "$TRANSFER_STATE" \
        "$SOURCE_FINGERPRINT" "${RETAINED_FILES[@]}" <<'PY'
import csv
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

(
    root, manifest_path, gse, gsm, srr, source, provenance, final_product, urls,
    expected_bytes, expected_md5, expected_spots, validation_path, state_path,
    source_fingerprint, *files
) = sys.argv[1:]
root = Path(root)

def md5(path):
    value = hashlib.md5()
    with open(path, "rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            value.update(chunk)
    return value.hexdigest()

validation = json.loads(Path(validation_path).read_text()) if Path(validation_path).is_file() else {}
state = json.loads(Path(state_path).read_text()) if Path(state_path).is_file() else {}
observed = [Path(path) for path in files]
if not observed or any(not path.is_file() for path in observed):
    raise SystemExit("Cannot record missing retained files")
methods = ["format_validation", "run_transaction"]
if any(expected_bytes.split(";")):
    methods.append("provider_bytes")
if any(expected_md5.split(";")):
    methods.append("provider_md5")
if final_product != "sra":
    methods.append("paired_read_count")
    if expected_spots:
        methods.append("expected_spots")
row = {
    "gse": gse, "gsm": gsm, "srr": srr, "source": source,
    "provenance": provenance, "final_product": final_product, "urls": urls,
    "expected_bytes": expected_bytes,
    "observed_bytes": ";".join(str(path.stat().st_size) for path in observed),
    "expected_md5": expected_md5,
    "observed_md5": ";".join(md5(path) for path in observed),
    "expected_spots": expected_spots,
    "observed_r1": str(validation.get("reads_per_mate", "")),
    "observed_r2": str(validation.get("reads_per_mate", "")) if validation.get("r2") else "",
    "validation": "PASS",
    "completed_at": datetime.now().astimezone().isoformat(),
    "retained_files": ";".join(os.path.relpath(path, root) for path in observed),
    "retained_bytes": ";".join(str(path.stat().st_size) for path in observed),
    "retained_md5": ";".join(md5(path) for path in observed),
    "integrity_methods": ";".join(methods),
    "attempt_count": str(state.get("attempt_count", 0)),
    "resume_count": str(state.get("resume_count", 0)),
    "source_fingerprint": source_fingerprint,
}
path = Path(manifest_path)
existing = []
if path.is_file():
    with path.open(newline="") as handle:
        existing = [item for item in csv.DictReader(handle, delimiter="\t") if item["srr"] != srr]
temp = path.with_suffix(path.suffix + ".tmp")
with temp.open("w", newline="") as handle:
    writer = csv.DictWriter(handle, fieldnames=list(row), delimiter="\t", lineterminator="\n")
    writer.writeheader()
    for item in existing:
        writer.writerow({key: item.get(key, "") for key in row})
    writer.writerow(row)
    handle.flush()
    os.fsync(handle.fileno())
os.replace(temp, path)
PY
}

complete_run() {
    exec 7>"$MANIFEST_LOCK"
    flock 7
    write_download_manifest
    flock -u 7
    printf 'gse\t%s\ngsm\t%s\nsrr\t%s\nsource\t%s\nprovenance\t%s\nfinal_product\t%s\nsource_fingerprint\t%s\nvalidation\tPASS\ncompleted_at\t%s\n' \
        "$GSE" "$GSM" "$SRR" "$SOURCE" "$PROVENANCE" "$FINAL_PRODUCT" \
        "$SOURCE_FINGERPRINT" "$(date -Is)" > "${COMPLETE_MARKER}.tmp"
    mv "${COMPLETE_MARKER}.tmp" "$COMPLETE_MARKER"
    state_update --phase complete --status complete --clear-error >/dev/null
    unlink "$PUBLISH_JOURNAL" 2>/dev/null || true
    find "$STAGING_DIR" -type f -delete
    find "$STAGING_DIR" -depth -type d -empty -delete
    find "$SCRATCH" -type f -delete 2>/dev/null || true
    find "$SCRATCH" -depth -type d -empty -delete 2>/dev/null || true
    if [[ -f "$ROOT/scripts/build_report.py" ]]; then
        python "$ROOT/scripts/build_report.py" --root "$ROOT" \
            || echo "WARNING: HTML 报告刷新失败" >&2
    fi
    echo "[$(date -Is)] COMPLETE $GSE/$GSM/$SRR source=$SOURCE product=$FINAL_PRODUCT"
}

if [[ -s "$COMPLETE_MARKER" && -s "$DOWNLOAD_MANIFEST" ]] && \
    python - "$ROOT" "$DOWNLOAD_MANIFEST" "$SRR" "$SOURCE_FINGERPRINT" <<'PY'
import csv
import hashlib
import sys
from pathlib import Path

root, manifest, run, fingerprint = sys.argv[1:]
with open(manifest, newline="") as handle:
    rows = [row for row in csv.DictReader(handle, delimiter="\t") if row["srr"] == run]
if len(rows) != 1 or rows[0].get("source_fingerprint") != fingerprint:
    raise SystemExit(1)
files = [item for item in rows[0].get("retained_files", "").split(";") if item]
checksums = [item for item in rows[0].get("retained_md5", "").split(";") if item]
sizes = [item for item in rows[0].get("retained_bytes", "").split(";") if item]
if not files or not (len(files) == len(checksums) == len(sizes)):
    raise SystemExit(1)
for name, checksum, size in zip(files, checksums, sizes, strict=True):
    path = Path(root, name)
    if not path.is_file() or path.stat().st_size != int(size):
        raise SystemExit(1)
    value = hashlib.md5()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            value.update(chunk)
    if value.hexdigest() != checksum:
        raise SystemExit(1)
PY
then
    state_update --phase complete --status complete --clear-error >/dev/null
    unlink "$PUBLISH_JOURNAL" 2>/dev/null || true
    find "$STAGING_DIR" -type f -delete
    find "$STAGING_DIR" -depth -type d -empty -delete
    find "$SCRATCH" -type f -delete 2>/dev/null || true
    find "$SCRATCH" -depth -type d -empty -delete 2>/dev/null || true
    echo "[$(date -Is)] COMPLETE $GSE/$GSM/$SRR already validated"
    exit 0
fi

declare -a RETAINED_FILES=()
if [[ -s "$PUBLISH_JOURNAL" ]]; then
    state_update --phase publishing --status in_progress >/dev/null
    mapfile -t RETAINED_FILES < <(
        python "$STATE_HELPER" publish --journal "$PUBLISH_JOURNAL" \
            --fingerprint "$SOURCE_FINGERPRINT"
    )
    complete_run
    exit 0
fi

SRA_FILE=""
R1_FILE=""
R2_FILE=""
declare -a STAGED_FILES=()
declare -a FINAL_FILES=()

if [[ "$SOURCE" == ncbi_sra ]]; then
    SRA_FILE="$DOWNLOAD_DIR/${SRR}.sra"
    prefetch_staged "$SRA_FILE"
else
    for index in "${!URLS[@]}"; do
        url=${URLS[$index]}
        role=${ROLES[$index]}
        expected_size=$(array_value "$index" "${EXPECTED_BYTES[@]}")
        expected_md5=$(array_value "$index" "${EXPECTED_MD5[@]}")
        case "$role" in
            SRA) output="$DOWNLOAD_DIR/${SRR}.sra"; SRA_FILE=$output ;;
            R1|R2|I1|I2) output="$DOWNLOAD_DIR/${SRR}_${role}.fastq.gz" ;;
            BAM) output="$DOWNLOAD_DIR/${SRR}.bam" ;;
            *) echo "Unsupported role: $role" >&2; exit 2 ;;
        esac
        download_staged "$url" "$output" "$role" "$expected_size" "$expected_md5"
    done
fi

if [[ -n "$SRA_FILE" && "$FINAL_PRODUCT" != sra ]]; then
    state_update --phase converting --status in_progress >/dev/null
    find "$CONVERT_DIR" -type f -delete
    find "$SCRATCH" -type f -delete 2>/dev/null || true
    if ! fasterq-dump --split-files --threads "$SRA_THREADS" \
        --temp "$SCRATCH" --outdir "$CONVERT_DIR" --size-check only "$SRA_FILE"
    then
        record_failure disk_or_conversion "SRA:size_check" \
            "fasterq-dump size check failed" 1 || true
        exit 1
    fi
    if ! fasterq-dump --split-files --threads "$SRA_THREADS" \
        --temp "$SCRATCH" --outdir "$CONVERT_DIR" "$SRA_FILE"
    then
        record_failure conversion_failure "SRA:fasterq" \
            "fasterq-dump failed" 1 || true
        exit 1
    fi
    if [[ "$LAYOUT" == PAIRED ]]; then
        [[ -s "$CONVERT_DIR/${SRR}_1.fastq" && -s "$CONVERT_DIR/${SRR}_2.fastq" ]] || {
            record_failure conversion_failure "SRA:outputs" \
                "paired fasterq outputs missing" 1 || true
            exit 1
        }
        R1_FILE="$STAGING_DIR/${SRR}_R1.fastq.gz"
        R2_FILE="$STAGING_DIR/${SRR}_R2.fastq.gz"
        compress_staged "$CONVERT_DIR/${SRR}_1.fastq" "$R1_FILE"
        compress_staged "$CONVERT_DIR/${SRR}_2.fastq" "$R2_FILE"
    else
        input="$CONVERT_DIR/${SRR}.fastq"
        [[ -s "$input" ]] || input="$CONVERT_DIR/${SRR}_1.fastq"
        [[ -s "$input" ]] || {
            record_failure conversion_failure "SRA:outputs" \
                "single-end fasterq output missing" 1 || true
            exit 1
        }
        R1_FILE="$STAGING_DIR/${SRR}_R1.fastq.gz"
        compress_staged "$input" "$R1_FILE"
    fi
elif [[ "$FINAL_PRODUCT" != sra ]]; then
    [[ -s "$DOWNLOAD_DIR/${SRR}_R1.fastq.gz" ]] && R1_FILE="$DOWNLOAD_DIR/${SRR}_R1.fastq.gz"
    [[ -s "$DOWNLOAD_DIR/${SRR}_R2.fastq.gz" ]] && R2_FILE="$DOWNLOAD_DIR/${SRR}_R2.fastq.gz"
fi

state_update --phase validating --status in_progress >/dev/null
if [[ "$FINAL_PRODUCT" != sra ]]; then
    [[ -s "$R1_FILE" ]] || { echo "Missing staged R1 for $SRR" >&2; exit 1; }
    validator_args=(
        python "$VALIDATOR" --srr "$SRR" --r1 "$R1_FILE"
        --report "$VALIDATION_REPORT"
    )
    [[ -n "$R2_FILE" ]] && validator_args+=(--r2 "$R2_FILE")
    [[ -n "$EXPECTED_SPOTS" ]] && validator_args+=(--expected-spots "$EXPECTED_SPOTS")
    [[ "$CB_LENGTH" =~ ^[0-9]+$ ]] && validator_args+=(--cb-length "$CB_LENGTH")
    [[ "$UMI_LENGTH" =~ ^[0-9]+$ ]] && validator_args+=(--umi-length "$UMI_LENGTH")
    if ! "${validator_args[@]}"; then
        record_failure read_validation "FASTQ:read_validation" \
            "paired/read-count validation failed" 1 || true
        exit 1
    fi
    for role in I1 I2; do
        technical="$DOWNLOAD_DIR/${SRR}_${role}.fastq.gz"
        [[ -s "$technical" ]] || continue
        technical_args=(
            python "$VALIDATOR" --srr "${SRR}_${role}" --r1 "$technical"
        )
        [[ -n "$EXPECTED_SPOTS" ]] && technical_args+=(--expected-spots "$EXPECTED_SPOTS")
        if ! "${technical_args[@]}"; then
            record_failure read_validation "${role}:read_validation" \
                "$role read-count validation failed" 1 || true
            exit 1
        fi
    done
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

if [[ "$FINAL_PRODUCT" == sra ]]; then
    STAGED_FILES=("$SRA_FILE")
    FINAL_FILES=("$SRA_DIR/${SRR}.sra")
else
    STAGED_FILES=("$R1_FILE")
    FINAL_FILES=("$FASTQ_DIR/${SRR}_R1.fastq.gz")
    if [[ -n "$R2_FILE" ]]; then
        STAGED_FILES+=("$R2_FILE")
        FINAL_FILES+=("$FASTQ_DIR/${SRR}_R2.fastq.gz")
    fi
    for role in I1 I2; do
        if [[ -s "$DOWNLOAD_DIR/${SRR}_${role}.fastq.gz" ]]; then
            STAGED_FILES+=("$DOWNLOAD_DIR/${SRR}_${role}.fastq.gz")
            FINAL_FILES+=("$FASTQ_DIR/${SRR}_${role}.fastq.gz")
        fi
    done
fi

python - "$PUBLISH_JOURNAL" "$SOURCE_FINGERPRINT" "$QUARANTINE_DIR" \
    "${#STAGED_FILES[@]}" "${STAGED_FILES[@]}" "${FINAL_FILES[@]}" <<'PY'
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

journal, fingerprint, quarantine, count, *paths = sys.argv[1:]
count = int(count)
staged = [Path(path) for path in paths[:count]]
finals = [Path(path) for path in paths[count:]]
quarantine = Path(quarantine)

def md5(path):
    value = hashlib.md5()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            value.update(chunk)
    return value.hexdigest()

items = []
quarantine.mkdir(parents=True, exist_ok=True)
stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
for source, final in zip(staged, finals, strict=True):
    if not source.is_file():
        raise SystemExit(f"Missing staged file {source}")
    checksum = md5(source)
    size = source.stat().st_size
    if final.exists() and (final.stat().st_size != size or md5(final) != checksum):
        os.replace(final, quarantine / f"{stamp}_invalid_final_{final.name}")
    items.append({"staged": str(source), "final": str(final), "bytes": size, "md5": checksum})
payload = {
    "source_fingerprint": fingerprint,
    "created_at": datetime.now().astimezone().isoformat(),
    "files": items,
}
path = Path(journal)
temp = path.with_suffix(path.suffix + ".tmp")
with temp.open("w") as handle:
    handle.write(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    handle.flush()
    os.fsync(handle.fileno())
os.replace(temp, path)
PY

state_update --phase publishing --status in_progress >/dev/null
mapfile -t RETAINED_FILES < <(
    python "$STATE_HELPER" publish --journal "$PUBLISH_JOURNAL" \
        --fingerprint "$SOURCE_FINGERPRINT"
)
complete_run
