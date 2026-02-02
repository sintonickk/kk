#!/bin/bash
set -euo pipefail

# 切换到 ranqi_server 根目录（本脚本位于 ranqi_server/app/）
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$APP_ROOT"

# 优先使用 python3，其次 python
if command -v python3 >/dev/null 2>&1; then
  PY=python3
else
  PY=python
fi

# 运行主程序
exec "$PY" -u main.py