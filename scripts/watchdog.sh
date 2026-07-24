#!/usr/bin/env bash
set -Eeuo pipefail

[[ $# -ge 1 && $# -le 2 ]] || {
    echo "Usage: $0 <GSE-project-root> [interval-seconds]" >&2
    exit 2
}
ROOT=$(cd "$1" && pwd)
INTERVAL=${2:-1800}
[[ "$INTERVAL" =~ ^[0-9]+$ ]] && (( INTERVAL >= 60 )) || {
    echo "Interval must be an integer >= 60" >&2
    exit 2
}
MANIFEST="$ROOT/metadata/source_manifest.tsv"
[[ -s "$MANIFEST" ]] || { echo "Missing $MANIFEST" >&2; exit 2; }
GSE=$(awk -F '\t' 'NR==2 {gsub(/\r/,"",$1); print $1}' "$MANIFEST")
SESSION=${GEO_SRA_PIPELINE_SESSION:-"geo_${GSE}"}
RUNNER=${GEO_SRA_RUNNER:-"$ROOT/scripts/run_all.sh"}
AUTO_RESTART=${GEO_SRA_AUTO_RESTART:-1}
MAX_RESTARTS=${GEO_SRA_MAX_RESTARTS:-3}
LOG_DIR="$ROOT/reports/logs"
STATE_DIR="$ROOT/reports/watchdog"
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
if [[ -s "$STATE" ]]; then
    restart_streak=$(awk -F '\t' '$1=="restart_streak" {print $2}' "$STATE")
    [[ "$restart_streak" =~ ^[0-9]+$ ]] || restart_streak=0
    last_completed=$(awk -F '\t' '$1=="last_completed" {print $2}' "$STATE")
    [[ "$last_completed" =~ ^[0-9]+$ ]] || last_completed=0
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

while true; do
    completed=$(find "$ROOT/reports/status" -maxdepth 1 -type f -name '*.complete' 2>/dev/null | wc -l)
    bytes=$(du -sb "$ROOT" | awk '{print $1}')
    free=$(df -B1 --output=avail "$ROOT" | tail -n 1 | tr -d ' ')
    current_phase=$(phase)
    if tmux has-session -t "$SESSION" 2>/dev/null; then
        pipeline=running
    else
        pipeline=missing
    fi
    recent_errors=$(find "$LOG_DIR" -type f -name '*.log' -mmin -35 -print0 2>/dev/null \
        | xargs -0 -r tail -n 200 2>/dev/null \
        | grep -Eic '(^|[^[:alpha:]])(error|failed|corrupt|mismatch)([^[:alpha:]]|$)' || true)
    printf '[%s] CHECK pipeline=%s phase=%s completed=%s/%s bytes=%s free=%s recent_errors=%s restart_streak=%s\n' \
        "$(date -Is)" "$pipeline" "$current_phase" "$completed" "$expected" \
        "$bytes" "$free" "$recent_errors" "$restart_streak" | tee -a "$LOG"
    refresh_report

    if (( completed > last_completed )); then
        restart_streak=0
        last_completed=$completed
    fi

    if (( completed == expected )); then
        printf '[%s] COMPLETE all %s runs finished; watchdog exiting\n' \
            "$(date -Is)" "$expected" | tee -a "$LOG"
        printf 'last_completed\t%s\nrestart_streak\t0\n' "$completed" > "${STATE}.tmp"
        mv "${STATE}.tmp" "$STATE"
        exit 0
    fi

    if [[ "$pipeline" == missing && "$AUTO_RESTART" == 1 ]]; then
        if (( restart_streak >= MAX_RESTARTS )); then
            printf '[%s] STOP restart limit reached (%s)\n' \
                "$(date -Is)" "$MAX_RESTARTS" | tee -a "$LOG"
            exit 1
        fi
        if [[ -x "$RUNNER" ]]; then
            restart_streak=$((restart_streak + 1))
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
    printf 'last_completed\t%s\nrestart_streak\t%s\n' \
        "$completed" "$restart_streak" > "${STATE}.tmp"
    mv "${STATE}.tmp" "$STATE"
    sleep "$INTERVAL"
done
