#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="configure-pci-eth.service"
TARGET_SCRIPT="/usr/local/sbin/configure_pci_eth.sh"
UNIT_FILE="/etc/systemd/system/${SERVICE_NAME}"

require_root() {
  if [ "${EUID:-$(id -u)}" -ne 0 ]; then
    echo "This script must be run as root." >&2
    exit 1
  fi
}

check_systemd() {
  if ! command -v systemctl >/dev/null 2>&1; then
    echo "systemctl not found. This script requires systemd." >&2
    exit 1
  fi
}

install_script() {
  local repo_dir
  repo_dir="$(cd "$(dirname "$0")" && pwd)"
  local src_script="${repo_dir}/configure_pci_eth.sh"
  if [ ! -f "$src_script" ]; then
    echo "Source script not found: $src_script" >&2
    exit 1
  fi
  install -m 0755 "$src_script" "$TARGET_SCRIPT"
  echo "Installed: $TARGET_SCRIPT"
}

write_unit() {
  cat > "$UNIT_FILE" << 'EOF'
[Unit]
Description=Configure extra IP for PCI Ethernet
After=network-pre.target
Wants=network-pre.target
Before=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/configure_pci_eth.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF
  chmod 0644 "$UNIT_FILE"
  echo "Wrote unit: $UNIT_FILE"
}

enable_service() {
  systemctl daemon-reload
  systemctl enable --now "$SERVICE_NAME"
  systemctl status --no-pager "$SERVICE_NAME" || true
}

main() {
  require_root
  check_systemd
  install_script
  write_unit
  enable_service
  echo "Auto-start registered."
}

main "$@"
