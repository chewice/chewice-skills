#!/usr/bin/env bash
set -Eeuo pipefail

[[ $# -ge 1 && $# -le 2 ]] || {
    echo "Usage: $0 <GSE-project-root> [interval-seconds]" >&2
    exit 2
}
ROOT=$(cd "$1" && pwd)
INTERVAL=${2:-1800}
if [[ ! "$INTERVAL" =~ ^[0-9]+$ ]] || (( INTERVAL < 60 )); then
    echo "Interval must be an integer >= 60" >&2
    exit 2
fi
MANIFEST="$ROOT/metadata/source_manifest.tsv"
[[ -s "$MANIFEST" ]] || { echo "Missing $MANIFEST" >&2; exit 2; }
GSE=$(awk -F '\t' 'NR==2 {gsub(/\r/,"",$1); print $1}' "$MANIFEST")
SESSION=${GEO_SRA_PIPELINE_SESSION:-"geo_${GSE}"}
RUNNER=${GEO_SRA_RUNNER:-"$ROOT/scripts/run_all.sh"}
CONFIG="$ROOT/metadata/acquisition_config.tsv"
config_value() {
    local key=$1 fallback=$2 value
    value=$(awk -F '\t' -v key="$key" '$1==key {gsub(/\r/,"",$2); print $2}' "$CONFIG" 2>/dev/null | tail -n 1)
    printf '%s' "${value:-$fallback}"
}
AUTO_RESTART=${GEO_SRA_AUTO_RESTART:-$(config_value auto_restart false)}
MAX_RESTARTS=${GEO_SRA_MAX_RESTARTS:-$(config_value max_auto_restarts 0)}
[[ "$AUTO_RESTART" == true || "$AUTO_RESTART" == 1 ]] && AUTO_RESTART=1 || AUTO_RESTART=0
[[ "$MAX_RESTARTS" =~ ^[0-9]+$ ]] || { echo "max_auto_restarts must be an integer" >&2; exit 2; }
if (( AUTO_RESTART == 1 && MAX_RESTARTS == 0 )); then
    echo "Auto recovery requires a persistent positive max_auto_restarts budget" >&2
    exit 2
fi
LOG_DIR="$ROOT/reports/logs"
STATE_DIR="$ROOT/reports/watchdog"
TRANSFER_STATUS_DIR="$ROOT/reports/status"
LOG="$LOG_DIR/watchdog.log"
STATE="$STATE_DIR/state.tsv"
mkdir -p "$LOG_DIR" "$STATE_DIR"

refresh_report() {
    if [[ -f "$ROOT/scripts/build_report.py" ]]; then
        python "$ROOT/scripts/build_report.py" --root "$ROOT" \
            || printf '[%s] WARNING HTML report refresh failed\n' "$(date -Is)" >> "$LOG"
    fi
}

exec 9>"$STATE_DIR/watchdog.lock"
flock -n 9 || { echo "Another watchdog is already active" >&2; exit 2; }

expected=$(awk 'END {print NR-1}' "$MANIFEST")
restart_streak=0
last_completed=0
last_restart_completed=-1
seen_running=0
if [[ -s "$STATE" ]]; then
    restart_streak=$(awk -F '\t' '$1=="restart_streak" {print $2}' "$STATE")
    [[ "$restart_streak" =~ ^[0-9]+$ ]] || restart_streak=0
    last_completed=$(awk -F '\t' '$1=="last_completed" {print $2}' "$STATE")
    [[ "$last_completed" =~ ^[0-9]+$ ]] || last_completed=0
    last_restart_completed=$(awk -F '\t' '$1=="last_restart_completed" {print $2}' "$STATE")
    [[ "$last_restart_completed" =~ ^-?[0-9]+$ ]] || last_restart_completed=-1
    seen_running=$(awk -F '\t' '$1=="seen_running" {print $2}' "$STATE")
    [[ "$seen_running" =~ ^[01]$ ]] || seen_running=0
fi

phase() {
    local processes
    processes=$(pgrep -afu "$USER" 2>/dev/null | grep -F "$ROOT" || true)
    if grep -Eq 'aria2c|curl .*download' <<< "$processes"; then echo download
    elif grep -Eq 'prefetch' <<< "$processes"; then echo prefetch
    elif grep -Eq 'fasterq-dump' <<< "$processes"; then echo fasterq
    elif grep -Eq 'fastqc' <<< "$processes"; then echo fastqc
    elif grep -Eq 'STAR|STARsolo' <<< "$processes"; then echo starsolo
    else echo idle
    fi
}

transfer_summary() {
    python - "$TRANSFER_STATUS_DIR" <<'PY'
import json
import sys
from collections import Counter
from pathlib import Path

states = []
for path in Path(sys.argv[1]).glob("*.transfer.json"):
    try:
        states.append(json.loads(path.read_text()))
    except (OSError, json.JSONDecodeError):
        continue
terminal = sorted(
    state.get("run", "") for state in states
    if state.get("status") == "terminal_failed"
)
classes = Counter(
    state.get("error_class", "") for state in states
    if state.get("error_class")
)
print(",".join(item for item in terminal if item))
print(",".join(f"{key}:{value}" for key, value in sorted(classes.items())))
PY
}

while true; do
    completed=$(find "$ROOT/reports/status" -maxdepth 1 -type f -name '*.complete' 2>/dev/null | wc -l)
    bytes=$(du -sb "$ROOT" | awk '{print $1}')
    free=$(df -B1 --output=avail "$ROOT" | tail -n 1 | tr -d ' ')
    current_phase=$(phase)
    if tmux has-session -t "$SESSION" 2>/dev/null; then
        pipeline=running
        seen_running=1
    else
        pipeline=missing
    fi
    recent_errors=$(find "$LOG_DIR" -type f -name '*.log' -mmin -35 -print0 2>/dev/null \
        | xargs -0 -r tail -n 200 2>/dev/null \
        | grep -Eic '(^|[^[:alpha:]])(error|failed|corrupt|mismatch)([^[:alpha:]]|$)' || true)
    mapfile -t transfer < <(transfer_summary)
    terminal_runs=${transfer[0]:-}
    error_classes=${transfer[1]:-}
    printf '[%s] CHECK pipeline=%s phase=%s completed=%s/%s bytes=%s free=%s recent_errors=%s restart_streak=%s terminal_runs=%s error_classes=%s\n' \
        "$(date -Is)" "$pipeline" "$current_phase" "$completed" "$expected" \
        "$bytes" "$free" "$recent_errors" "$restart_streak" \
        "${terminal_runs:-none}" "${error_classes:-none}" | tee -a "$LOG"
    refresh_report

    if (( completed > last_completed )); then
        restart_streak=0
        last_completed=$completed
    fi

    if (( completed == expected )); then
        printf '[%s] COMPLETE all %s runs finished; watchdog exiting\n' \
            "$(date -Is)" "$expected" | tee -a "$LOG"
        printf 'last_completed\t%s\nrestart_streak\t0\nlast_restart_completed\t%s\nseen_running\t%s\n' \
            "$completed" "$last_restart_completed" "$seen_running" > "${STATE}.tmp"
        mv "${STATE}.tmp" "$STATE"
        exit 0
    fi

    if [[ -n "$terminal_runs" ]]; then
        printf '[%s] STOP terminal transfer failure requires review: %s\n' \
            "$(date -Is)" "$terminal_runs" | tee -a "$LOG"
        printf 'last_completed\t%s\nrestart_streak\t%s\nlast_restart_completed\t%s\nseen_running\t%s\nterminal_runs\t%s\n' \
            "$completed" "$restart_streak" "$last_restart_completed" "$seen_running" "$terminal_runs" > "${STATE}.tmp"
        mv "${STATE}.tmp" "$STATE"
        exit 1
    fi

    if [[ "$pipeline" == missing && "$AUTO_RESTART" == 1 ]]; then
        if (( seen_running == 0 )); then
            printf '[%s] SNAPSHOT missing pipeline; no prior running state, not starting a new session\n' \
                "$(date -Is)" | tee -a "$LOG"
        elif (( restart_streak > 0 && completed <= last_restart_completed )); then
            printf '[%s] STOP no new progress after authorized restart; manual review required\n' \
                "$(date -Is)" | tee -a "$LOG"
            exit 1
        elif (( restart_streak >= MAX_RESTARTS )); then
            printf '[%s] STOP restart limit reached (%s)\n' \
                "$(date -Is)" "$MAX_RESTARTS" | tee -a "$LOG"
            exit 1
        elif [[ -x "$RUNNER" ]]; then
            restart_streak=$((restart_streak + 1))
            last_restart_completed=$completed
            tmux new-session -d -s "$SESSION" \
                "cd '$ROOT' && pixi run --locked bash '$RUNNER'"
            printf '[%s] RESTART session=%s attempt=%s\n' \
                "$(date -Is)" "$SESSION" "$restart_streak" | tee -a "$LOG"
        else
            printf '[%s] STOP missing executable runner: %s\n' \
                "$(date -Is)" "$RUNNER" | tee -a "$LOG"
            exit 1
        fi
    fi
    printf 'last_completed\t%s\nrestart_streak\t%s\nlast_restart_completed\t%s\nseen_running\t%s\n' \
        "$completed" "$restart_streak" "$last_restart_completed" "$seen_running" > "${STATE}.tmp"
    mv "${STATE}.tmp" "$STATE"
    sleep "$INTERVAL"
done
