#!/usr/bin/env bash
set -euo pipefail

IP1_CIDR="192.168.31.102/24"
IP2_CIDR="192.168.1.102/24"
: "${LAN1_IFACE:=}"
: "${LAN2_IFACE:=}"

require_root() {
  if [ "${EUID:-$(id -u)}" -ne 0 ]; then
    echo "This script must be run as root." >&2
    exit 1
  fi
}

find_pci_eth_ifaces() {
  for p in /sys/class/net/*; do
    iface="${p##*/}"
    [ "$iface" = "lo" ] && continue
    [ -e "$p/device" ] || continue
    [ -d "$p/wireless" ] && continue
    if [ -f "$p/type" ] && [ "$(cat "$p/type")" = "1" ]; then
      echo "$iface"
    fi
  done
}

has_ip() {
  ip -4 addr show dev "$1" | grep -qF " $2 "
}

main() {
  require_root
  # Determine LAN1 and LAN2 interfaces
  if [ -z "$LAN1_IFACE" ] || [ -z "$LAN2_IFACE" ]; then
    # Pick the first two PCI Ethernet ifaces in sorted order
    mapfile -t _ifaces < <(find_pci_eth_ifaces | sort)
    if [ -z "$LAN1_IFACE" ]; then LAN1_IFACE="${_ifaces[0]:-}"; fi
    if [ -z "$LAN2_IFACE" ]; then LAN2_IFACE="${_ifaces[1]:-}"; fi
  fi

  if [ -z "${LAN1_IFACE:-}" ] || [ -z "${LAN2_IFACE:-}" ]; then
    echo "Need two Ethernet interfaces for LAN1 and LAN2." >&2
    exit 1
  fi

  if [ "$LAN1_IFACE" = "$LAN2_IFACE" ]; then
    echo "LAN1_IFACE and LAN2_IFACE must be different." >&2
    exit 1
  fi

  for pair in "${LAN1_IFACE}:${IP1_CIDR}" "${LAN2_IFACE}:${IP2_CIDR}"; do
    iface="${pair%%:*}"
    cidr="${pair#*:}"
    ip link set dev "$iface" up || true
    if has_ip "$iface" "$cidr"; then
      echo "$cidr already present on $iface, skipping"
      continue
    fi
    ip addr add "$cidr" dev "$iface"
    echo "Configured $iface with $cidr"
  done
}

main "$@"
