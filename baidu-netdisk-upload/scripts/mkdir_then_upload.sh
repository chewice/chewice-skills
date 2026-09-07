#!/usr/bin/env bash
# 先为每个含文件目录 mkdir，再探针，再 BaiduPCS-Go upload。
# 用法见 SKILL.md。不要在目录未建齐时直接 upload。
set -u

usage() {
  cat <<'EOF'
Usage:
  mkdir_then_upload.sh --src DIR --remote-parent PAN_DIR [options]

Options:
  --src DIR              本地源目录
  --remote-parent DIR    网盘父目录（upload 会在其下创建 basename(src)）
  --log-dir DIR          日志目录（默认: <src>/../logs 或 $PWD/logs）
  --session NAME         tmux 会话名（默认: baidu-netdisk-upload）
  --retry N              upload 失败重试（默认: 5）
  --load N               同时上传文件数 -l（默认: 4）
  --mkdir-only           只建目录，不探针、不上传
  --no-tmux              前台上传（不推荐大目录）
  -h, --help             显示帮助
EOF
}

SRC=""
REMOTE_PARENT=""
LOG_DIR=""
SESSION="baidu-netdisk-upload"
RETRY=5
LOAD=4
MKDIR_ONLY=0
NO_TMUX=0

while [ $# -gt 0 ]; do
  case "$1" in
    --src) SRC="$2"; shift 2 ;;
    --remote-parent) REMOTE_PARENT="$2"; shift 2 ;;
    --log-dir) LOG_DIR="$2"; shift 2 ;;
    --session) SESSION="$2"; shift 2 ;;
    --retry) RETRY="$2"; shift 2 ;;
    --load) LOAD="$2"; shift 2 ;;
    --mkdir-only) MKDIR_ONLY=1; shift ;;
    --no-tmux) NO_TMUX=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

if [ -z "$SRC" ] || [ -z "$REMOTE_PARENT" ]; then
  usage >&2
  exit 2
fi

if ! command -v BaiduPCS-Go >/dev/null 2>&1; then
  echo "BaiduPCS-Go not found in PATH" >&2
  exit 127
fi

SRC="$(readlink -f "$SRC")"
if [ ! -d "$SRC" ]; then
  echo "src is not a directory: $SRC" >&2
  exit 2
fi

BASE="$(basename "$SRC")"
REMOTE_ROOT="${REMOTE_PARENT%/}/$BASE"

if [ -z "$LOG_DIR" ]; then
  if [ -d "$(dirname "$SRC")/logs" ]; then
    LOG_DIR="$(dirname "$SRC")/logs"
  else
    LOG_DIR="$PWD/logs"
  fi
fi
mkdir -p "$LOG_DIR"

MKLOG="$LOG_DIR/baidupcs_mkdir.log"
UPLOG="$LOG_DIR/baidupcs_upload.log"
DIRLIST="$LOG_DIR/baidupcs_dirlist.txt"
: > "$MKLOG"

mkdir_one() {
  local remote="$1"
  local out
  out=$(BaiduPCS-Go mkdir "$remote" 2>&1) || true
  if printf '%s\n' "$out" | grep -q '创建目录成功'; then
    echo "OK $remote"
    return 0
  fi
  if printf '%s\n' "$out" | grep -q '31061\|文件已存在'; then
    echo "EXISTS $remote"
    return 0
  fi
  echo "FAIL $remote :: $out"
  sleep 1
  out=$(BaiduPCS-Go mkdir "$remote" 2>&1) || true
  if printf '%s\n' "$out" | grep -q '创建目录成功\|31061\|文件已存在'; then
    echo "RETRY-OK $remote"
    return 0
  fi
  return 1
}

echo "==== START MKDIR $(date) src=$SRC remote_root=$REMOTE_ROOT ====" | tee -a "$MKLOG"
mkdir_one "$REMOTE_PARENT" | tee -a "$MKLOG"
mkdir_one "$REMOTE_ROOT" | tee -a "$MKLOG"

find "$SRC" -type f -printf '%h\n' | sort -u > "$DIRLIST"
total=$(wc -l < "$DIRLIST")
n=0
ok=0
fail=0

while IFS= read -r dir; do
  n=$((n + 1))
  if [ "$dir" = "$SRC" ]; then
    remote="$REMOTE_ROOT"
  else
    rel="${dir#"$SRC"/}"
    remote="$REMOTE_ROOT/$rel"
  fi
  if out=$(mkdir_one "$remote"); then
    ok=$((ok + 1))
    echo "[$n/$total] $out" | tee -a "$MKLOG"
  else
    fail=$((fail + 1))
    echo "[$n/$total] $out" | tee -a "$MKLOG"
  fi
done < "$DIRLIST"

echo "==== MKDIR DONE $(date) ok=$ok fail=$fail total=$total ====" | tee -a "$MKLOG"

if [ "$fail" -gt 0 ]; then
  echo "mkdir failures=$fail; refuse upload until directories exist" | tee -a "$MKLOG"
  exit 1
fi

if [ "$MKDIR_ONLY" -eq 1 ]; then
  exit 0
fi

: > "$UPLOG"

# 探针：选一个小于 64KiB 的原文件，上传到其已存在的父目录
probe_src="$(find "$SRC" -type f -size -64k -printf '%s\t%p\n' | sort -n | head -1 | cut -f2-)"
if [ -z "$probe_src" ]; then
  probe_src="$(find "$SRC" -type f -printf '%s\t%p\n' | sort -n | head -1 | cut -f2-)"
fi
if [ -z "$probe_src" ]; then
  echo "no files to upload under $SRC" >&2
  exit 1
fi

probe_rel="${probe_src#"$SRC"/}"
if [ "$(dirname "$probe_rel")" = "." ]; then
  probe_remote_dir="$REMOTE_ROOT"
else
  probe_remote_dir="$REMOTE_ROOT/$(dirname "$probe_rel")"
fi

echo "==== PROBE $(date) $probe_src -> $probe_remote_dir ====" | tee -a "$UPLOG"
if ! BaiduPCS-Go upload --retry "$RETRY" -l 1 --policy skip "$probe_src" "$probe_remote_dir" 2>&1 | tee -a "$UPLOG"; then
  echo "probe upload command failed" | tee -a "$UPLOG"
  exit 1
fi
if ! grep -qE '上传文件成功|秒传成功|跳过' "$UPLOG"; then
  if grep -q '代码: -9' "$UPLOG"; then
    echo "probe hit -9; parent dir still missing: $probe_remote_dir" | tee -a "$UPLOG"
  else
    echo "probe did not report success" | tee -a "$UPLOG"
  fi
  exit 1
fi

upload_cmd=(BaiduPCS-Go upload --retry "$RETRY" -l "$LOAD" --policy skip "$SRC" "$REMOTE_PARENT")
echo "==== START UPLOAD $(date) ${upload_cmd[*]} ====" | tee -a "$UPLOG"

if [ "$NO_TMUX" -eq 1 ]; then
  stdbuf -oL -eL "${upload_cmd[@]}" 2>&1 | tee -a "$UPLOG"
  echo "==== UPLOAD EXIT $? $(date) ====" | tee -a "$UPLOG"
  exit $?
fi

if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux not found; use --no-tmux or install tmux" >&2
  exit 127
fi

if tmux has-session -t "$SESSION" 2>/dev/null; then
  echo "tmux session already exists: $SESSION" | tee -a "$UPLOG"
  echo "attach: tmux attach -t $SESSION"
  exit 0
fi

tmux new-session -d -s "$SESSION" -c "$PWD"
tmux send-keys -t "$SESSION" "stdbuf -oL -eL $(printf '%q ' "${upload_cmd[@]}") 2>&1 | tee -a $(printf '%q' "$UPLOG"); echo EXIT:\$? | tee -a $(printf '%q' "$UPLOG"); date | tee -a $(printf '%q' "$UPLOG")" C-m
echo "started tmux session $SESSION"
echo "attach: tmux attach -t $SESSION"
echo "log: $UPLOG"
