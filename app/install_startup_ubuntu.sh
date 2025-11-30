#!/usr/bin/env bash
set -euo pipefail

# Resolve repo/app directory
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$SCRIPT_DIR"
START_SH="$APP_DIR/start.sh"
LOG_DIR="$APP_DIR/logs"
LOG_FILE="$LOG_DIR/startup.log"

mkdir -p "$LOG_DIR"

if [[ ! -x "$START_SH" ]]; then
  echo "[info] start.sh is not executable, attempting to set +x"
  chmod +x "$START_SH" || true
fi

# Prepare crontab line
CRON_LINE="@reboot bash \"$START_SH\" >> \"$LOG_FILE\" 2>&1"

# Install/replace in user's crontab
TMP_CRON="$(mktemp)"
crontab -l 2>/dev/null | grep -v "start.sh" > "$TMP_CRON" || true
# Avoid duplicate by checking exact line
if ! grep -Fq "$CRON_LINE" "$TMP_CRON"; then
  echo "$CRON_LINE" >> "$TMP_CRON"
fi
crontab "$TMP_CRON"
rm -f "$TMP_CRON"

echo "[ok] Installed @reboot crontab entry to run: $START_SH"
echo "[note] Logs will go to: $LOG_FILE"

echo "[tip] You can test immediately by running:"
echo "      nohup bash '$START_SH' >> '$LOG_FILE' 2>&1 & disown"
