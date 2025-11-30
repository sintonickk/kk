#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$SCRIPT_DIR"
START_SH="$APP_DIR/start.sh"

# Stop existing start.sh processes (match full path to be precise)
PIDS=$(pgrep -f -- "$START_SH" || true)
if [[ -n "${PIDS}" ]]; then
  echo "Stopping start.sh (PIDs: ${PIDS})"
  kill ${PIDS} || true
  sleep 1
  PIDS2=$(pgrep -f -- "$START_SH" || true)
  if [[ -n "${PIDS2}" ]]; then
    echo "Forcing kill for PIDs: ${PIDS2}"
    kill -9 ${PIDS2} || true
  fi
  echo "Stopped."
else
  echo "No running start.sh found."
fi
