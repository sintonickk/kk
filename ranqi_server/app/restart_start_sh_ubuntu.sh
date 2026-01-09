#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$SCRIPT_DIR"
START_SH="$APP_DIR/start.sh"
LOG_DIR="$APP_DIR/logs"
LOG_FILE="$LOG_DIR/restart.log"

mkdir -p "$LOG_DIR"

if [[ ! -x "$START_SH" ]]; then
  echo "[info] start.sh is not executable, attempting to set +x"
  chmod +x "$START_SH" || true
fi

# Stop existing start.sh processes (match full path to be precise)
PIDS=$(pgrep -f -- "$START_SH" || true)
if [[ -n "${PIDS}" ]]; then
  echo "[info] Stopping running start.sh (PIDs: ${PIDS})"
  # Try graceful then force
  kill ${PIDS} || true
  sleep 1
  PIDS2=$(pgrep -f -- "$START_SH" || true)
  if [[ -n "${PIDS2}" ]]; then
    echo "[warn] Forcing kill for PIDs: ${PIDS2}"
    kill -9 ${PIDS2} || true
  fi
else
  echo "[info] No running start.sh found"
fi

# Start in background
echo "[info] Starting start.sh in background"
nohup bash "$START_SH" >> "$LOG_FILE" 2>&1 & disown || true

echo "[ok] Restarted. Logs: $LOG_FILE"
