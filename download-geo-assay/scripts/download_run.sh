#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
    echo "Usage: $0 <GSE-project-root> <run-accession> [--stage acquire|materialize|all]" >&2
    exit 2
}

[[ $# -eq 2 || ( $# -eq 4 && "$3" == --stage ) ]] || usage
ROOT=$(cd "$1" && pwd)
RUN=$2
STAGE=${4:-all}
[[ "$STAGE" == acquire || "$STAGE" == materialize || "$STAGE" == all ]] || usage
MANIFEST="$ROOT/metadata/source_manifest.tsv"
SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
VALIDATOR="$SCRIPT_DIR/validate_fastq_pair.py"
STATE_HELPER="$SCRIPT_DIR/transfer_state.py"
RUNTIME_HELPER="$SCRIPT_DIR/acquisition_runtime.py"
LAYOUT_HELPER="$SCRIPT_DIR/project_layout.py"
[[ -s "$MANIFEST" ]] || { echo "Missing $MANIFEST" >&2; exit 2; }
if [[ "$STAGE" == all || "${GEO_SRA_MANAGED_STAGE:-}" != "$STAGE" ]]; then
    exec python3 "$STATE_HELPER" run-stage --root "$ROOT" --run "$RUN" --stage "$STAGE"
fi
[[ -s "$VALIDATOR" && -s "$STATE_HELPER" && -s "$LAYOUT_HELPER" ]] || {
    echo "Missing download helper scripts" >&2
    exit 2
}

mapfile -t ROW < <(
    python3 - "$MANIFEST" "$RUN" "$SCRIPT_DIR" <<'PY'
import csv
import sys

path, run, scripts = sys.argv[1:]
sys.path.insert(0, scripts)
from capabilities import read_role_errors

with open(path, newline="") as handle:
    matches = [
        row for row in csv.DictReader(handle, delimiter="\t")
        if row["srr"].rstrip("\r") == run
    ]
if len(matches) != 1:
    raise SystemExit(f"Expected one source-manifest row for {run}, found {len(matches)}")
row = matches[0]
roles = [role.strip() for role in row.get("read_roles", "").split(";")]
errors = read_role_errors(roles, row.get("library_layout", ""), row.get("final_product", ""))
if errors:
    raise SystemExit(f"{run}: " + "; ".join(errors))
fields = [
    "gse", "gsm", "srr", "library_layout", "expected_spots",
    "cb_length", "umi_length", "selected_source", "selected_provenance",
    "object_class", "quality_class",
    "selected_urls", "selected_bytes", "selected_md5", "read_roles",
    "final_product", "fallback_reason",
]
for field in fields:
    print(row.get(field, "").rstrip("\r").replace("\n", " "))
PY
)
(( ${#ROW[@]} == 17 )) || { echo "Manifest parser failed for $RUN" >&2; exit 2; }
GSE=${ROW[0]}
GSM=${ROW[1]}
SRR=${ROW[2]}
LAYOUT=${ROW[3]}
EXPECTED_SPOTS=${ROW[4]}
CB_LENGTH=${ROW[5]:-0}
UMI_LENGTH=${ROW[6]:-0}
SOURCE=${ROW[7]}
PROVENANCE=${ROW[8]}
OBJECT_CLASS=${ROW[9]}
QUALITY_CLASS=${ROW[10]}
URLS_TEXT=${ROW[11]}
BYTES_TEXT=${ROW[12]}
MD5_TEXT=${ROW[13]}
ROLES_TEXT=${ROW[14]}
FINAL_PRODUCT=${ROW[15]}
ACTUAL_PROVENANCE=$PROVENANCE
ACTUAL_OBJECT_CLASS=$OBJECT_CLASS
ACTUAL_QUALITY_CLASS=$QUALITY_CLASS

[[ "$SRR" == "$RUN" ]] || { echo "Run parser mismatch" >&2; exit 2; }
eval "$(python3 "$LAYOUT_HELPER" --root "$ROOT" --gsm "$GSM" --srr "$SRR" --print-dirs)"
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
READY_RECEIPT="$STATUS_DIR/${SRR}.ready.json"
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

# The runtime loads the explicit proxy and project configuration before admission.
# No provider-specific direct connection can override the selected transport.

exec 8>"$WORK_DIR/run.lock"
flock 8
if [[ "$STAGE" == materialize ]]; then
    exec 5>"$STATUS_DIR/materialize.lock"
    flock 5
fi

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
RUN_FASTQC=${GEO_SRA_RUN_FASTQC:-1}
RETRY_DELAYS=${GEO_SRA_RETRY_DELAYS:-0,30,120}
[[ "$MAX_ATTEMPTS" =~ ^[1-9][0-9]*$ ]] || {
    echo "GEO_SRA_MAX_ATTEMPTS must be a positive integer" >&2
    exit 2
}
IFS=',' read -r -a DELAYS <<< "$RETRY_DELAYS"

SOURCE_FINGERPRINT=$(
    python3 "$STATE_HELPER" fingerprint \
        --source "$SOURCE" --urls "$URLS_TEXT" --bytes "$BYTES_TEXT" \
        --md5 "$MD5_TEXT" --roles "$ROLES_TEXT" --final-product "$FINAL_PRODUCT"
)
ACCEPTANCE_FINGERPRINT=$(python3 "$STATE_HELPER" acceptance --root "$ROOT" --run "$RUN")

network_command() {
    local url=$1
    shift
    [[ "$STAGE" == acquire ]] || { echo "Network operation forbidden in materialize stage" >&2; return 2; }
    python3 "$RUNTIME_HELPER" exec --root "$ROOT" --network --url "$url" -- "$@"
}

# Toolkit commands may fetch dependencies implicitly. The runtime verifies a
# per-process KFG with remote access disabled for all local validation/conversion.
vdb-validate() {
    python3 "$RUNTIME_HELPER" exec --root "$ROOT" -- vdb-validate "$@"
}

fasterq-dump() {
    python3 "$RUNTIME_HELPER" exec --root "$ROOT" -- fasterq-dump "$@"
}

state_update() {
    python3 "$STATE_HELPER" update --path "$TRANSFER_STATE" --run "$SRR" \
        --fingerprint "$SOURCE_FINGERPRINT" --acceptance "$ACCEPTANCE_FINGERPRINT" "$@"
}

state_get() {
    python3 "$STATE_HELPER" get --path "$TRANSFER_STATE" --field "$1" \
        --default "${2:-}"
}

if [[ "$(state_get status)" == terminal_failed && "$(state_get source_fingerprint)" == "$SOURCE_FINGERPRINT" ]]; then
    if [[ "$(state_get error_class)" == read_validation && -n "$(state_get acceptance_fingerprint)" \
        && "$(state_get acceptance_fingerprint)" != "$ACCEPTANCE_FINGERPRINT" ]]; then
        echo "Acceptance requirements changed; retrying local validation only"
    else
        echo "Terminal failure already recorded for $SRR; review and archive state before manual retry" >&2
        exit 1
    fi
fi
if [[ -s "$PUBLISH_JOURNAL" ]] && ! python3 - "$PUBLISH_JOURNAL" "$SOURCE_FINGERPRINT" <<'PYJ'
import json, sys
journal = json.load(open(sys.argv[1]))
raise SystemExit(0 if journal.get("source_fingerprint") == sys.argv[2] else 1)
PYJ
then
    echo "Publish journal source fingerprint mismatch; local recovery required; preserve validated objects" >&2
    exit 2
fi
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
    python3 - "$ROOT" "$1" <<'PY'
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
        R1|R2|I1|I2)
            # CRC alone cannot establish equivalence to the provider object.
            [[ -n "$expected_md5" || ( -n "$expected_size" && -n "$EXPECTED_SPOTS" ) ]] || return 1
            gzip -t "$path" || return 1 ;;
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
    network_command "$url" "${command[@]}" || return 1
}

header_value() {
    python3 - "$1" "$2" <<'PY'
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
    local etag="" modified="" remote_size="" offset=0 rc=0 error_class error_key count complete_without_control=0
    mkdir -p "$(dirname "$staged")"
    if validate_downloaded_file "$staged" "$role" "$expected_size" "$expected_md5"; then
        echo "Reusing validated staged $(basename "$staged")"
        return 0
    fi
    [[ ! -e "$staged" ]] || quarantine_paths invalid_staged "$staged"

    # aria2 removes its control file at successful completion. A crash before our
    # rename must recover that complete object by content, without another GET.
    if [[ -f "$part" && ! -f "$control" ]] && validate_downloaded_file "$part" "$role" "$expected_size" "$expected_md5"; then
        if [[ -n "$expected_md5" ]]; then
            mv "$part" "$staged"
            unlink "$resume_meta" 2>/dev/null || true
            return 0
        elif [[ -f "$resume_meta" ]]; then
            complete_without_control=1
        fi
    fi
    if [[ -f "$part" && ( ! -f "$control" || ! -f "$resume_meta" ) && "$complete_without_control" == 0 ]]; then
        quarantine_paths untrusted_partial "$part" "$control" "$resume_meta"
    fi
    if [[ ! -f "$part" && ( -f "$control" || -f "$resume_meta" ) ]]; then
        quarantine_paths orphan_resume "$control" "$resume_meta"
    fi
    while true; do
        etag=""; modified=""; remote_size=""
        if probe_remote "$url" "$headers"; then
            etag=$(header_value "$headers" etag)
            modified=$(header_value "$headers" last-modified)
            remote_size=$(header_value "$headers" content-length)
        elif [[ -z "$expected_md5" ]]; then
            unlink "$headers" 2>/dev/null || true
            if ! record_failure network_interrupted "${role}:identity_probe" "Cannot verify remote identity before transfer"; then return 1; fi
            continue
        fi
        unlink "$headers" 2>/dev/null || true
        if [[ -n "$expected_size" && -n "$remote_size" && "$remote_size" =~ ^[0-9]+$ ]] \
            && (( remote_size != expected_size )); then
            record_failure remote_changed "${role}:remote_changed" "Remote Content-Length changed; review source" 1 || true
            return 1
        fi
        if [[ -f "$part" && -z "$expected_md5" && -z "$etag" && -z "$modified" ]]; then
            record_failure remote_changed "${role}:identity_unknown" "No provider digest or remote version validator for partial" 1 || true
            return 1
        fi
        python3 "$STATE_HELPER" resume-check --path "$resume_meta" \
            --fingerprint "$SOURCE_FINGERPRINT" --url "$url" --role "$role" \
            --expected-bytes "$expected_size" --expected-md5 "$expected_md5" \
            --etag "$etag" --last-modified "$modified" --remote-bytes "$remote_size" && rc=0 || rc=$?
        if (( rc == 10 )); then
            quarantine_paths changed_remote "$part" "$control" "$resume_meta"
            record_failure remote_changed "${role}:remote_changed" "Remote object changed; old partial quarantined" 1 || true
            return 1
        elif (( rc != 0 )); then
            return "$rc"
        fi
        if (( complete_without_control == 1 )); then
            mv "$part" "$staged"
            unlink "$resume_meta" 2>/dev/null || true
            return 0
        fi
        offset=0
        [[ -f "$part" ]] && offset=$(stat -c %s "$part")
        state_update --phase transfer --status in_progress --attempt-delta 1 >/dev/null
        (( offset > 0 )) && state_update --resume-delta 1 >/dev/null
        echo "Downloading $(basename "$staged") partial_logical_bytes=$offset; piece map controls resume"
        local -a aria=(
            aria2c --no-conf=true --allow-overwrite=true --auto-file-renaming=false
            --auto-save-interval=1
            --check-integrity=true --connect-timeout=30 --continue=true
            --console-log-level=notice --file-allocation=none
            --max-connection-per-server="$DOWNLOAD_CONNECTIONS" --max-tries=1
            --min-split-size=16M --retry-wait=0 --split="$DOWNLOAD_CONNECTIONS"
            --summary-interval=30 --timeout=30
        )
        [[ -n "$expected_md5" ]] && aria+=(--checksum="md5=$expected_md5")
        if [[ -n "$etag" && "$etag" != W/* ]]; then
            aria+=(--header="If-Match: $etag")
        elif [[ -n "$modified" ]]; then
            aria+=(--header="If-Unmodified-Since: $modified")
        fi
        network_command "$url" "${aria[@]}" --dir="$(dirname "$part")" \
            --out="$(basename "$part")" "$url" && rc=0 || rc=$?
        if (( rc == 9 || rc == 16 )); then
            record_failure disk_or_conversion "${role}:disk_write" "aria2 cannot write output (exit=$rc); partial retained" 1 || true
            return 1
        fi
        if (( rc == 0 )) && validate_downloaded_file "$part" "$role" "$expected_size" "$expected_md5"; then
            unlink "$control" 2>/dev/null || true
            unlink "$resume_meta" 2>/dev/null || true
            mv "$part" "$staged"
            state_update --phase transfer --status in_progress --clear-error >/dev/null
            return 0
        fi
        error_class=network_interrupted
        # A segmented partial can already have the final logical length. Only a
        # finished transfer or aria2's explicit checksum error proves corruption.
        if [[ -f "$part" ]] && (( rc == 0 || rc == 32 )); then
            error_class=checksum_or_integrity
            quarantine_paths corrupt_full "$part" "$control" "$resume_meta"
            python3 "$STATE_HELPER" resume-check --path "$resume_meta" \
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

restore_archive_identity() {
    local identity="$DOWNLOAD_DIR/${SRR}.object.tsv"
    local object_fingerprint
    if [[ -s "$identity" ]]; then
        IFS=$'\t' read -r ACTUAL_PROVENANCE ACTUAL_OBJECT_CLASS ACTUAL_QUALITY_CLASS object_fingerprint < "$identity"
        if [[ "$object_fingerprint" != "$SOURCE_FINGERPRINT" ]]; then
            echo "Staged object identity mismatch; local review required" >&2
            return 2
        fi
    elif [[ "$SOURCE" == ncbi_sra ]]; then
        echo "Missing full/Lite identity for staged archive; local review required" >&2
        return 2
    fi
    if [[ "$ACTUAL_OBJECT_CLASS" == SRA_LITE && "${ALLOW_SRA_LITE:-false}" != true ]]; then
        record_failure unsupported_object "SRA:lite_not_authorized" "SRA Lite requires explicit authorization" 1 || true
        return 1
    fi
}

adopt_archive() {
    local candidate=$1 staged=$2
    vdb-validate "$candidate" || return 1
    if [[ "$candidate" == *.sralite ]]; then
        [[ "${ALLOW_SRA_LITE:-false}" == true ]] || return 1
        ACTUAL_PROVENANCE=SRA_LITE
        ACTUAL_OBJECT_CLASS=SRA_LITE
        ACTUAL_QUALITY_CLASS=SIMPLIFIED
    else
        ACTUAL_PROVENANCE=ARCHIVE_NORMALIZED_SRA
        ACTUAL_OBJECT_CLASS=FULL_QUALITY_ARCHIVE
        ACTUAL_QUALITY_CLASS=FULL
    fi
    printf '%s\t%s\t%s\t%s\n' "$ACTUAL_PROVENANCE" "$ACTUAL_OBJECT_CLASS" "$ACTUAL_QUALITY_CLASS" "$SOURCE_FINGERPRINT" \
        > "$DOWNLOAD_DIR/${SRR}.object.tsv.tmp" || return 2
    mv "$DOWNLOAD_DIR/${SRR}.object.tsv.tmp" "$DOWNLOAD_DIR/${SRR}.object.tsv" || return 2
    mv "$candidate" "$staged" || return 2
    state_update --phase prefetch --status in_progress --clear-error >/dev/null
}

probe_odp() {
    local result
    while true; do
        [[ "$STAGE" == acquire ]] || return 2
        result=$(python3 "$SCRIPT_DIR/ncbi_odp.py" probe --root "$ROOT" --run "$SRR" --evidence "$STATUS_DIR/${SRR}.odp.json") || return 2
        IFS=$'\t' read -r ODP_STATUS ODP_METHOD <<< "$result"
        [[ "$ODP_STATUS" != unreachable ]] && return 0
        if ! record_failure network_interrupted "SRA:odp_probe" \
            "ODP identity unresolved after HEAD/AWS listing; prefetch/Lite not permitted"; then return 1; fi
    done
}

copy_odp() {
    local destination=$1 expected_size=${2:-} expected_md5=${3:-} rc error_class
    while true; do
        state_update --phase transfer --status in_progress --attempt-delta 1 >/dev/null
        [[ "$STAGE" == acquire ]] || return 2
        python3 "$SCRIPT_DIR/ncbi_odp.py" copy --root "$ROOT" --run "$SRR" --evidence "$STATUS_DIR/${SRR}.odp.json" \
            --destination "$destination" --expected-bytes "$expected_size" --expected-md5 "$expected_md5" && rc=0 || rc=$?
        (( rc == 0 )) && return 0
        case "$rc" in
            1) error_class=network_interrupted ;;
            3) error_class=checksum_or_integrity ;;
            4) record_failure remote_changed "SRA:aws_identity" "ODP object changed during AWS transfer" 1 || true; return 1 ;;
            *) record_failure disk_or_conversion "SRA:aws_local" "AWS copy blocked by local error" 1 || true; return 2 ;;
        esac
        if ! record_failure "$error_class" "SRA:aws_copy:$error_class" "AWS copy failed; partial preserved, no completion"; then return 1; fi
    done
}

prefetch_staged() {
    local staged=$1
    local prefetch_root="$WORK_DIR/ncbi"
    local cache_root="$ROOT/temporary/prefetch_cache"
    local source_file="$prefetch_root/$SRR/$SRR.sra"
    local lite_file="$prefetch_root/$SRR/$SRR.sralite"
    local odp_url="https://sra-pub-run-odp.s3.amazonaws.com/sra/$SRR/$SRR"
    local odp_status rc count error_class candidate
    mkdir -p "$cache_root" "$prefetch_root"
    exec 6>"$cache_root/${SRR}.lock"
    flock 6
    if validate_downloaded_file "$staged" SRA "" ""; then
        if [[ ! -s "$DOWNLOAD_DIR/${SRR}.object.tsv" ]]; then
            echo "Staged archive lacks object identity; inspect full/Lite before recovery" >&2
            return 2
        fi
        restore_archive_identity
        return
    fi
    # Reuse full archives before probing or transferring ODP again.
    for candidate in "$source_file" "$cache_root/$SRR/$SRR.sra"; do
        if [[ -s "$candidate" ]] && adopt_archive "$candidate" "$staged"; then return 0; fi
    done
    # Unknown HEAD status must resolve via the exact AWS key before selecting a transport.
    probe_odp
    odp_status=$ODP_STATUS
    if [[ "$odp_status" == available ]]; then
        if [[ "$ODP_METHOD" == aws_list ]]; then
            copy_odp "$cache_root/$SRR/$SRR.sra"
            adopt_archive "$cache_root/$SRR/$SRR.sra" "$staged"
            return
        fi
        download_staged "$odp_url" "$source_file" SRA "" ""
        adopt_archive "$source_file" "$staged"
        return
    fi
    if [[ "$odp_status" == missing && "${ALLOW_SRA_LITE:-false}" == true ]]; then
        for candidate in "$lite_file" "$cache_root/$SRR/$SRR.sralite"; do
            if [[ -s "$candidate" ]] && adopt_archive "$candidate" "$staged"; then return 0; fi
        done
    fi
    while true; do
        state_update --phase prefetch --status in_progress --attempt-delta 1 >/dev/null
        network_command "https://sra-download.ncbi.nlm.nih.gov" \
            prefetch "$SRR" --type sra --max-size u -O "$prefetch_root" && rc=0 || rc=$?
        if [[ -s "$source_file" ]] && adopt_archive "$source_file" "$staged"; then return 0; fi
        if [[ "$odp_status" == missing && "${ALLOW_SRA_LITE:-false}" == true ]]; then
            for candidate in "$lite_file" "$cache_root/$SRR/$SRR.sralite"; do
                if [[ -s "$candidate" ]] && adopt_archive "$candidate" "$staged"; then return 0; fi
            done
        fi
        if [[ -s "$lite_file" ]]; then
            record_failure unsupported_object "SRA:lite_not_eligible" \
                "Lite retained; requires authorization and ODP absence (ODP=$odp_status)" 1 || true
            return 1
        fi
        error_class=network_interrupted
        # Partial prefetch outputs can have .sra names; quarantine only after a successful transfer.
        if (( rc == 0 )) && [[ -s "$source_file" ]]; then
            error_class=checksum_or_integrity
            quarantine_paths invalid_prefetch "$source_file"
        fi
        if ! record_failure "$error_class" "SRA:prefetch:${error_class}" \
            "prefetch exit=$rc; cache retained for resume"; then return 1; fi
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
    python3 - "$ROOT" "$DOWNLOAD_MANIFEST" "$GSE" "$GSM" "$SRR" "$SOURCE" \
        "$PROVENANCE" "$ACTUAL_PROVENANCE" "$ACTUAL_OBJECT_CLASS" "$ACTUAL_QUALITY_CLASS" \
        "$FINAL_PRODUCT" "$URLS_TEXT" "$BYTES_TEXT" "$MD5_TEXT" \
        "$EXPECTED_SPOTS" "$VALIDATION_REPORT" "$TRANSFER_STATE" \
        "$SOURCE_FINGERPRINT" "$ACCEPTANCE_FINGERPRINT" "${RETAINED_FILES[@]}" <<'PY'
import csv
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

(
    root, manifest_path, gse, gsm, srr, source, selected_provenance,
    provenance, object_class, quality_class, final_product, urls,
    expected_bytes, expected_md5, expected_spots, validation_path, state_path,
    source_fingerprint, acceptance_fingerprint, *files
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
sizes = ";".join(str(path.stat().st_size) for path in observed)
checksums = ";".join(md5(path) for path in observed)
methods = ["format_validation", "run_transaction"]
if source != "ncbi_sra" and all(expected_bytes.split(";")):
    methods.append("provider_bytes")
if source != "ncbi_sra" and all(expected_md5.split(";")):
    methods.append("provider_md5")
if source in {"ncbi_sra", "ncbi_ondemand", "ngdc_insdc"}:
    methods.append("vdb_validate")
if final_product != "sra":
    methods.append("paired_read_count")
    if expected_spots:
        methods.append("expected_spots")
row = {
    "gse": gse, "gsm": gsm, "srr": srr, "source": source,
    "selected_provenance": selected_provenance,
    "provenance": provenance, "object_class": object_class,
    "replacement_note": "Recheck recorded source-bucket probes for full-quality replacement" if object_class == "SRA_LITE" else "",
    "quality_class": quality_class, "final_product": final_product, "urls": urls,
    "expected_bytes": expected_bytes,
    "observed_bytes": sizes,
    "expected_md5": expected_md5,
    "observed_md5": checksums,
    "expected_spots": expected_spots,
    "observed_r1": str(validation.get("reads_per_mate", "")),
    "observed_r2": str(validation.get("reads_per_mate", "")) if validation.get("r2") else "",
    "validation": "PASS",
    "completed_at": datetime.now().astimezone().isoformat(),
    "retained_files": ";".join(os.path.relpath(path, root) for path in observed),
    "retained_bytes": sizes,
    "retained_md5": checksums,
    "integrity_methods": ";".join(methods),
    "integrity_evidence": "provider_digest_verified" if "provider_md5" in methods else (
        "native_archive_verified" if "vdb_validate" in methods else "format_size_read_count_verified"),
    "attempt_count": str(state.get("attempt_count", 0)),
    "resume_count": str(state.get("resume_count", 0)),
    "source_fingerprint": source_fingerprint,
    "acceptance_fingerprint": acceptance_fingerprint,
    "odp_evidence": json.dumps(json.loads((root / f'reports/status/{srr}.odp.json').read_text()), sort_keys=True)
        if (root / f'reports/status/{srr}.odp.json').is_file() else "",
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
    printf 'gse\t%s\ngsm\t%s\nsrr\t%s\nsource\t%s\nprovenance\t%s\nfinal_product\t%s\nsource_fingerprint\t%s\nacceptance_fingerprint\t%s\nvalidation\tPASS\ncompleted_at\t%s\n' \
        "$GSE" "$GSM" "$SRR" "$SOURCE" "$ACTUAL_PROVENANCE" "$FINAL_PRODUCT" \
        "$SOURCE_FINGERPRINT" "$ACCEPTANCE_FINGERPRINT" "$(date -Is)" > "${COMPLETE_MARKER}.tmp"
    mv "${COMPLETE_MARKER}.tmp" "$COMPLETE_MARKER"
    state_update --phase complete --status complete --clear-error >/dev/null
    unlink "$PUBLISH_JOURNAL" 2>/dev/null || true
    unlink "$READY_RECEIPT" 2>/dev/null || true
    find "$STAGING_DIR" -type f -delete
    find "$STAGING_DIR" -depth -type d -empty -delete
    find "$SCRATCH" -type f -delete 2>/dev/null || true
    find "$SCRATCH" -depth -type d -empty -delete 2>/dev/null || true
    if [[ -f "$ROOT/scripts/build_report.py" ]]; then
        python3 "$ROOT/scripts/build_report.py" --root "$ROOT" \
            || echo "WARNING: HTML 报告刷新失败" >&2
    fi
    echo "[$(date -Is)] COMPLETE $GSE/$GSM/$SRR source=$SOURCE product=$FINAL_PRODUCT"
}

complete_rc=0
python3 "$STATE_HELPER" completed --root "$ROOT" --run "$SRR" \
    --manifest "$DOWNLOAD_MANIFEST" --marker "$COMPLETE_MARKER" --lock "$MANIFEST_LOCK" \
    --report "$VALIDATION_REPORT" --fingerprint "$SOURCE_FINGERPRINT" || complete_rc=$?
if (( complete_rc == 0 )); then
    state_update --phase complete --status complete --clear-error >/dev/null
    unlink "$PUBLISH_JOURNAL" 2>/dev/null || true
    unlink "$READY_RECEIPT" 2>/dev/null || true
    find "$STAGING_DIR" -type f -delete
    find "$STAGING_DIR" -depth -type d -empty -delete
    find "$SCRATCH" -type f -delete 2>/dev/null || true
    find "$SCRATCH" -depth -type d -empty -delete 2>/dev/null || true
    echo "[$(date -Is)] COMPLETE $GSE/$GSM/$SRR locally validated"
    exit 0
elif (( complete_rc == 12 )); then
    record_failure read_validation "FASTQ:acceptance_contract" \
        "Retained objects fail the current acceptance contract; preserved without downloading" 1 || true
    exit 1
elif (( complete_rc != 1 )); then
    exit "$complete_rc"
fi

declare -a RETAINED_FILES=()
if [[ -s "$PUBLISH_JOURNAL" && "$STAGE" == acquire ]]; then
    state_update --phase acquired --status acquired --clear-error >/dev/null
    echo "[$(date -Is)] ACQUIRED $GSE/$GSM/$SRR pending local publish recovery"
    exit 0
fi
if [[ -s "$PUBLISH_JOURNAL" && "$STAGE" == materialize ]]; then
    state_update --phase publishing --status in_progress >/dev/null
    restore_archive_identity
    published=$(python3 "$STATE_HELPER" publish --journal "$PUBLISH_JOURNAL" \
        --fingerprint "$SOURCE_FINGERPRINT" --root "$ROOT" --run "$SRR" --report "$VALIDATION_REPORT")
    mapfile -t RETAINED_FILES <<< "$published"
    complete_run
    exit 0
fi

SRA_FILE=""
R1_FILE=""
R2_FILE=""
declare -a STAGED_FILES=()
declare -a FINAL_FILES=()

if [[ "$STAGE" == acquire ]]; then
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
        if [[ "$SOURCE" == ncbi_ondemand && "$role" == SRA ]]; then
            cache="$ROOT/temporary/prefetch_cache/$SRR/$SRR.sra"
            mkdir -p "$ROOT/temporary/prefetch_cache"
            exec 6>"$ROOT/temporary/prefetch_cache/${SRR}.lock"
            flock 6
            if validate_downloaded_file "$cache" SRA "$expected_size" "$expected_md5"; then
                adopt_archive "$cache" "$output"
            fi
            if ! validate_downloaded_file "$output" SRA "$expected_size" "$expected_md5"; then
                probe_odp
                if [[ "$ODP_STATUS" == missing ]]; then
                    record_failure remote_changed "SRA:odp_missing" "Selected ODP object is absent; review manifest" 1 || true
                    exit 1
                fi
                if [[ "$ODP_METHOD" == aws_list ]]; then
                    copy_odp "$cache" "$expected_size" "$expected_md5"
                    adopt_archive "$cache" "$output"
                fi
            fi
        fi
        download_staged "$url" "$output" "$role" "$expected_size" "$expected_md5"
    done
fi

    ready_args=(python3 "$STATE_HELPER" ready --root "$ROOT" --path "$READY_RECEIPT"
                --run "$SRR" --fingerprint "$SOURCE_FINGERPRINT")
    if [[ -n "$SRA_FILE" ]]; then
        ready_args+=(--file "SRA=$SRA_FILE")
    else
        for role in "${ROLES[@]}"; do
            ready_args+=(--file "$role=$DOWNLOAD_DIR/${SRR}_${role}.fastq.gz")
        done
    fi
    "${ready_args[@]}"
    state_update --phase acquired --status acquired --clear-error >/dev/null
    echo "[$(date -Is)] ACQUIRED $GSE/$GSM/$SRR"
    exit 0
fi

ready_files=$(python3 "$STATE_HELPER" ready --root "$ROOT" --path "$READY_RECEIPT" \
    --run "$SRR" --fingerprint "$SOURCE_FINGERPRINT" --check) || {
    echo "Validated acquisition receipt required before materialization; network is disabled" >&2
    exit 2
}
while IFS=$'\t' read -r role path; do
    case "$role" in
        SRA) SRA_FILE=$path; vdb-validate "$path" ;;
        R1) R1_FILE=$path ;;
        R2) R2_FILE=$path ;;
        I1|I2) : ;;
        *) echo "Unsupported acquired role: $role" >&2; exit 2 ;;
    esac
done <<< "$ready_files"
[[ -z "$SRA_FILE" ]] || restore_archive_identity

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
        python3 "$VALIDATOR" --srr "$SRR" --r1 "$R1_FILE"
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
            python3 "$VALIDATOR" --srr "${SRR}_${role}" --r1 "$technical"
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

python3 - "$PUBLISH_JOURNAL" "$SOURCE_FINGERPRINT" "$ACCEPTANCE_FINGERPRINT" "$QUARANTINE_DIR" \
    "${#STAGED_FILES[@]}" "${STAGED_FILES[@]}" "${FINAL_FILES[@]}" <<'PY'
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

journal, fingerprint, acceptance, quarantine, count, *paths = sys.argv[1:]
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
    "acceptance_fingerprint": acceptance,
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
published=$(python3 "$STATE_HELPER" publish --journal "$PUBLISH_JOURNAL" \
    --fingerprint "$SOURCE_FINGERPRINT" --root "$ROOT" --run "$SRR" --report "$VALIDATION_REPORT")
mapfile -t RETAINED_FILES <<< "$published"
complete_run
