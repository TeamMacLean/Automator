#!/usr/bin/env bash
set -u

LOCK_FILE="/run/eth0-auto-switch.lock"
ETH_DEV="eth0"

INSTITUTE_PROFILE_UUID="c3612a53-4d0a-4587-b00c-6f6eaaef9f04"
INSTITUTE_PROFILE_NAME="Instrument connection"
INSTITUTE_GATEWAY="10.0.8.1"

DIRECT_PROFILE="mac-direct-auto"
DIRECT_IP="192.168.50.2"
DIRECT_PREFIX="24"
DIRECT_DHCP_SERVICE="automator-direct-dhcp.service"

LOG_TAG="eth0-auto-switch"

log() {
  logger -t "$LOG_TAG" "$*"
  echo "$*"
}

start_direct_dhcp() {
  log "Starting direct MacBook DHCP service: $DIRECT_DHCP_SERVICE"
  systemctl start "$DIRECT_DHCP_SERVICE" >/dev/null 2>&1 || true
}

stop_direct_dhcp() {
  log "Stopping direct MacBook DHCP service: <REDACTED>
  systemctl stop "$DIRECT_DHCP_SERVICE" >/dev/null 2>&1 || true
}

# Prevent overlapping runs from dispatcher/service/timer.
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
  log "Another eth0-auto-switch instance is already running; exiting"
  exit 0
fi

if ! ip link show "$ETH_DEV" >/dev/null 2>&1; then
  log "$ETH_DEV does not exist; exiting"
  exit 0
fi

CARRIER_FILE="/sys/class/net/${ETH_DEV}/carrier"

if [ ! -f "$CARRIER_FILE" ]; then
  log "No carrier file for $ETH_DEV; exiting"
  exit 0
fi

if [ "$(cat "$CARRIER_FILE")" != "1" ]; then
  log "$ETH_DEV has no Ethernet carrier; stopping direct DHCP and exiting"
  stop_direct_dhcp
  exit 0
fi

CURRENT_CON="$(nmcli -t -f NAME,DEVICE con show --active | awk -F: -v dev="$ETH_DEV" '$2==dev{print $1; exit}')"
CURRENT_UUID="$(nmcli -t -f UUID,DEVICE con show --active | awk -F: -v dev="$ETH_DEV" '$2==dev{print $1; exit}')"

log "$ETH_DEV has carrier; current active eth0 profile: ${CURRENT_CON:-none}"
log "Checking whether Institute gateway $INSTITUTE_GATEWAY is reachable on $ETH_DEV"

# Do not bring up Instrument connection before this test.
# This checks whether the real Institute LAN gateway exists on the physical Ethernet link.
if arping -I "$ETH_DEV" -c 3 -w 3 "$INSTITUTE_GATEWAY" >/dev/null 2>&1; then
  log "Institute gateway $INSTITUTE_GATEWAY is reachable; Institute LAN is physically connected"

  # Safety: never run the direct MacBook DHCP server on the Institute LAN.
  stop_direct_dhcp

  if [ "$CURRENT_UUID" = "$INSTITUTE_PROFILE_UUID" ] || [ "$CURRENT_CON" = "$INSTITUTE_PROFILE_NAME" ]; then
    log "Already on $INSTITUTE_PROFILE_NAME; no switch needed"
    exit 0
  fi

  log "Switching to $INSTITUTE_PROFILE_NAME"
  nmcli con up "$INSTITUTE_PROFILE_UUID" ifname "$ETH_DEV" >/dev/null 2>&1 || true

  sleep 3

  if ip -4 addr show "$ETH_DEV" | grep -q "inet 10.0.8.72/"; then
    log "$INSTITUTE_PROFILE_NAME active on 10.0.8.72/24"
  else
    log "WARNING: $INSTITUTE_PROFILE_NAME did not show 10.0.8.72/24 after switching"
    ip -4 addr show "$ETH_DEV" | logger -t "$LOG_TAG"
  fi

  exit 0
fi

log "Institute gateway $INSTITUTE_GATEWAY not reachable; assuming direct MacBook cable"

if [ "$CURRENT_CON" = "$DIRECT_PROFILE" ]; then
  if ip -4 addr show "$ETH_DEV" | grep -q "inet ${DIRECT_IP}/"; then
    log "Already on $DIRECT_PROFILE with ${DIRECT_IP}/${DIRECT_PREFIX}; ensuring DHCP service is running"
    start_direct_dhcp
    exit 0
  fi
fi

log "Switching to $DIRECT_PROFILE"

nmcli con up "$DIRECT_PROFILE" ifname "$ETH_DEV" >/dev/null 2>&1 || true

for i in $(seq 1 15); do
  if ip -4 addr show "$ETH_DEV" | grep -q "inet ${DIRECT_IP}/"; then
    log "Direct MacBook mode active on ${DIRECT_IP}/${DIRECT_PREFIX}"
    start_direct_dhcp
    exit 0
  fi
  sleep 1
done

log "WARNING: $DIRECT_PROFILE did not appear to assign ${DIRECT_IP}/${DIRECT_PREFIX} after waiting"
ip -4 addr show "$ETH_DEV" | logger -t "$LOG_TAG"

# If direct IP did not come up, do not run DHCP.
stop_direct_dhcp

exit 0
