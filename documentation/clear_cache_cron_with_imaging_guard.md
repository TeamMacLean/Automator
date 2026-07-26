# Clear Cache Cron Job with Automator Imaging Guard

This runbook documents the setup and verification of `/home/pi/clear_cache.sh` on the Raspberry Pi host `automator`.

The goal is to clear cache on a schedule, but **never run cache cleanup while Automator imaging is active**.

Sensitive values, including the Automator admin password, have been removed and replaced with placeholders.

---

## Final Outcome

The system now has:

- A root-run cron job that executes `/home/pi/clear_cache.sh` every 2 days at midnight.
- A cache cleanup script that checks Automator state before deleting anything.
- A safety guard that skips cleanup when `imaging_active=true`.
- Logging to `/var/log/clear_cache.log`.
- The Automator admin password stored in a root-only environment file, not directly in cron.

---

## Final Root Cron Schedule

Root's crontab contains only this cache cleanup schedule:

```cron
0 0 */2 * * /bin/bash /home/pi/clear_cache.sh
```

Check it with:

```bash
sudo crontab -l
```

This runs the script as `root` at midnight every 2 days.

---

## Final `pi` User Crontab

The `pi` user's crontab keeps the Klipper health check only:

```cron
*/30 * * * * /home/pi/check-klipper-status.sh >> /home/pi/klipper-health.log 2>&1
```

Check it with:

```bash
crontab -l
```

---

## Final `/home/pi/clear_cache.sh`

```bash
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
```

---

## Install or Replace the Script

Use this command to install the script:

````bash
sudo tee /home/pi/clear_cache.sh > /dev/null <<'EOF'
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

if [[ -f "$ENV_FILE" ]]; then
  source "$ENV_FILE"
fi

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
apt-get clean
rm -rf /home/pi/.cache/thumbnails/*
rm -rf /home/pi/.cache/*
rm -rf /home/pi/Automator/dev2/__pycache__/*
log "FINISHED: cache cleanup."
EOF
````

Make it executable:

```bash
sudo chmod +x /home/pi/clear_cache.sh
```

Verify:

```bash
head -n 20 /home/pi/clear_cache.sh
ls -l /home/pi/clear_cache.sh
```

Expected permission example:

```text
-rwxr-xr-x 1 pi pi ... /home/pi/clear_cache.sh
```

---

## Automator Password Environment File

The script reads the Automator admin password from:

```text
/root/automator-clear-cache.env
```

Create or edit it:

```bash
sudo nano /root/automator-clear-cache.env
```

Add this, replacing the placeholder with the real password:

```bash
AUTOMATOR_ADMIN_PASSWORD='REPLACE_WITH_REAL_PASSWORD'
```

Lock it down:

```bash
sudo chmod 600 /root/automator-clear-cache.env
sudo chown root:root /root/automator-clear-cache.env
```

Verify that the variable exists without exposing the value:

```bash
sudo grep -n '^AUTOMATOR_ADMIN_PASSWORD=' /root/automator-clear-cache.env
```

Do not paste the real password into chat, tickets, logs, screenshots, or documentation.

---

## Automator State Check

The script checks Automator state using:

```text
http://127.0.0.1:8080/system/state
```

The relevant JSON field is:

```json
"imaging_active"
```

Manual check:

```bash
sudo bash -c 'source /root/automator-clear-cache.env && curl -fsS --max-time 5 -u "admin:${AUTOMATOR_ADMIN_PASSWORD}" http://127.0.0.1:8080/system/state'
```

Example response when imaging is not active:

```json
{
  "door_open": false,
  "experiment_tag": "",
  "imaging_active": false,
  "pause_requested": false,
  "paused": false,
  "plates": {},
  "position": {
    "rotate": 90,
    "sol": 0,
    "vacuum": 0,
    "x": 0.0,
    "y": 0.0,
    "z": 0.0
  },
  "schedule": []
}
```

Example response when imaging is active, sanitized:

```json
{
  "door_open": false,
  "experiment_tag": "",
  "imaging_active": true,
  "pause_requested": false,
  "paused": false,
  "plates": {
    "plate_01": {
      "confidence": 0.908,
      "count": 1,
      "desc": "example_plate_description",
      "end": "2026-07-06T16:34",
      "id": 1,
      "interval": 1,
      "mode": "runtime",
      "selected": false,
      "start_dt": null,
      "x_mm": 123.36,
      "y_mm": 300.0
    }
  },
  "schedule": []
}
```

---

## Expected Script Behaviour

| Automator state | Script behaviour |
|---|---|
| `imaging_active=false` | Runs cache cleanup |
| `imaging_active=true` | Skips cache cleanup |
| Controller active but password missing | Skips cache cleanup |
| Controller active but `/system/state` unavailable | Skips cache cleanup |
| Controller active but `imaging_active` cannot be parsed | Skips cache cleanup |
| Controller inactive | Runs cache cleanup |

The script is intentionally safety-first. If the controller is active and the imaging state cannot be confirmed, it skips cleanup.

---

## Testing

### Test when imaging is not active

```bash
sudo /bin/bash /home/pi/clear_cache.sh
sudo tail -n 50 /var/log/clear_cache.log
```

Expected log output:

```text
[2026-07-06 15:28:28 BST] STARTED: cache cleanup.
[2026-07-06 15:28:28 BST] FINISHED: cache cleanup.
```

### Test when imaging is active

First confirm Automator reports:

```json
"imaging_active": true
```

Then run:

```bash
sudo /bin/bash /home/pi/clear_cache.sh
sudo tail -n 20 /var/log/clear_cache.log
```

Expected log output:

```text
[2026-07-06 15:34:40 BST] SKIPPED: imaging_active=true.
```

This confirms the cleanup does not run while imaging is active.

---

## Log File

The script writes to:

```text
/var/log/clear_cache.log
```

Check recent entries:

```bash
sudo tail -n 50 /var/log/clear_cache.log
```

Example entries:

```text
[2026-07-06 15:28:28 BST] STARTED: cache cleanup.
[2026-07-06 15:28:28 BST] FINISHED: cache cleanup.
[2026-07-06 15:34:40 BST] SKIPPED: imaging_active=true.
```

Older warning lines such as this may remain from earlier versions of the script that used `apt clean`:

```text
WARNING: apt does not have a stable CLI interface. Use with caution in scripts.
```

The final script uses:

```bash
apt-get clean
```

so that warning should not be added by future runs.

---

## Useful Verification Commands

Check whether the Automator controller is active:

```bash
systemctl is-active automator-controller.service
```

Check root cron:

```bash
sudo crontab -l
```

Check `pi` user cron:

```bash
crontab -l
```

Check script content:

```bash
cat /home/pi/clear_cache.sh
```

Check script permissions:

```bash
ls -l /home/pi/clear_cache.sh
```

Check for systemd references:

```bash
sudo grep -R "/home/pi/clear_cache.sh" \
  /etc/systemd/system \
  /lib/systemd/system \
  /usr/lib/systemd/system \
  /home/pi/.config/systemd/user \
  2>/dev/null
```

Check for cron references:

```bash
sudo grep -R "clear_cache.sh" /etc/cron* /var/spool/cron/crontabs 2>/dev/null
```

---

## Earlier Findings from Troubleshooting

The original script was:

```bash
#!/bin/bash
# Clear APT package cache
sudo apt clean

# Clear thumbnail cache (common on Raspberry Pi)
rm -rf ~/.cache/thumbnails/*

# Clear user cache (excluding command history)
rm -rf ~/.cache/*

# Clear specific folder cache
rm -rf /home/pi/Automator/dev2/__pycache__/*
```

Important notes from the review:

1. `rm -rf ~/.cache/*` already covers `~/.cache/thumbnails/*`, so the thumbnail line is redundant.
2. `sudo apt clean` inside a scheduled job is unreliable unless the job runs as root.
3. The machine had no systemd timer referencing `clear_cache.sh`.
4. The schedule was actually in the `pi` user's crontab:

```cron
0 0 */2 * * /bin/bash /home/pi/clear_cache.sh
```

5. The cron job was moved to root's crontab so `apt-get clean` can run without `sudo` inside the script.
6. Logging was added so successful and skipped runs are visible in `/var/log/clear_cache.log`.
7. The Automator `/system/state` endpoint confirmed the correct imaging flag is `imaging_active`.

---

## Security Note

The Automator admin password was accidentally pasted during troubleshooting. Treat that credential as exposed.

Recommended action:

1. Rotate or change the Automator admin password.
2. Update `/root/automator-clear-cache.env` with the new value.
3. Keep `/root/automator-clear-cache.env` owned by root and set to mode `600`.
4. Do not store the password in cron, shell history, screenshots, chat messages, or documentation.

Update the file:

```bash
sudo nano /root/automator-clear-cache.env
```

Secure it:

```bash
sudo chmod 600 /root/automator-clear-cache.env
sudo chown root:root /root/automator-clear-cache.env
```

---

## Final Confirmed Evidence

Root cron:

```cron
0 0 */2 * * /bin/bash /home/pi/clear_cache.sh
```

Script permissions:

```text
-rwxr-xr-x 1 pi pi 1828 Jul  6 15:25 /home/pi/clear_cache.sh
```

Automator state when imaging was active:

```json
"imaging_active": true
```

Script log after active imaging test:

```text
[2026-07-06 15:34:40 BST] SKIPPED: imaging_active=true.
```

This confirms the final requirement: **the cache cleanup does not run when imaging is active on the Pi**.
