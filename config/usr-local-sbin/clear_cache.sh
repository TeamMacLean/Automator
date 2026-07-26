#!/bin/bash
set -Eeuo pipefail
# SPDX-License-Identifier: MIT
# Copyright (c) 2025–2026 Rohan R

LOG_FILE="/var/log/clear_cache.log"
ENV_FILE="/root/automator-clear-cache.env"
STATE_URL="http://127.0.0.1:8080/system/state"

log() {
  echo "[$(date '+%Y-%m-%d %H:%M:%S %Z')] $*" >> "$LOG_FILE"
}

# Load Automator admin password for /system/state.
if [[ -f "$ENV_FILE" ]]; then
  # shellcheck disable=SC1090
  source "$ENV_FILE"
fi

# If the controller is running, check whether imaging is active.
# If state cannot be confirmed, skip cache clearing as a safety-first default.
if systemctl is-active --quiet automator-controller.service; then
  if [[ -z "${AUTOMATOR_ADMIN_PASSWORD:-}" ]]; then
    log "SKIPPED: automator-controller.service is active, but AUTOMATOR_ADMIN_PASSWORD is not available."
    exit 0
  fi

  STATE_JSON="$(curl -fsS --max-time 5 -u "admin:${AUTOMATOR_ADMIN_PASSWORD}" "$STATE_URL" || true)"

  if [[ -z "$STATE_JSON" ]]; then
    log "SKIPPED: automator-controller.service is active, but /system/state could not be read."
    exit 0
  fi

  IMAGING_ACTIVE="$(
    python3 -c '
import json, sys
try:
    data = json.load(sys.stdin)
except Exception:
    print("unknown")
    sys.exit(0)
print(str(data.get("imaging_active", "unknown")).lower())
' <<< "$STATE_JSON"
  )"

  if [[ "$IMAGING_ACTIVE" == "true" ]]; then
    log "SKIPPED: imaging_active=true."
    exit 0
  fi

  if [[ "$IMAGING_ACTIVE" == "unknown" ]]; then
    log "SKIPPED: could not determine imaging_active from /system/state."
    exit 0
  fi
fi

log "STARTED: cache cleanup."

# Clear APT package cache
apt-get clean

# Clear thumbnail cache
rm -rf /home/pi/.cache/thumbnails/*

# Clear user cache
rm -rf /home/pi/.cache/*

# Clear specific folder cache
rm -rf /home/pi/Automator/dev2/__pycache__/*

log "FINISHED: cache cleanup."
