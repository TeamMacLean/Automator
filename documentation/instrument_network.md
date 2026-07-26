<!--
SPDX-License-Identifier: CC-BY-4.0
Copyright (c) 2025–2026 Rohan R
-->

# Instrument network — archived configuration

> **ARCHIVED — no longer active.**
> The Automator system no longer connects to the NBI instrument/institute LAN over `eth0`.
> The Pi now runs on **IOT Wi-Fi** (primary) and
> **mac-direct-auto** for direct MacBook Ethernet access.
>
> **Never plug the Raspberry Pi Ethernet cable into the instrument network.**
> Doing so would activate the `Instrument connection` NetworkManager profile
> (if it is still present on the device), which is no longer a supported or monitored path.

This document preserves all instrument-network configuration for reference, so that when
references are removed from the live operational documentation, nothing is lost.

---

## 1. What was the instrument network

The NBI/TSL instrument LAN provided:

- A static routable address for the Pi (`10.0.8.72/24`)
- Access to the SMB filestore (`10.0.0.170`) for image archiving
- A routed printer subnet (`149.155.211.0/24`)
- Internet fallback (metric 800, when Wi-Fi was down)
- Admin access URL `http://10.0.8.72:8080/` from the Pi desktop browser

The instrument LAN was carried on `eth0`. The interface was shared with the direct MacBook
access mode (`mac-direct-auto`), with an auto-switch script determining which profile to
activate based on whether the Institute gateway (`10.0.8.1`) replied to ARP.

---

## 2. NetworkManager profiles

### Full profile table (NBI deployment)

<!-- markdownlint-disable MD060 -->
| Profile name | Interface | UUID | Mode | Status |
|---|---|---|---|---|
| `Instrument connection` | `eth0` | `c3612a53-4d0a-4587-b00c-6f6eaaef9f04` | Static `10.0.8.72/24` | **Archived — no longer active** |
| `mac-direct-auto` | `eth0` | `65c3e7b6-303b-421a-9590-e41b9f1ce6b2` | Static `192.168.50.2/24` | Active (kept) |
| `IOT` | `wlan0` | `e51d7392-116a-4dc6-8333-39fd9c718dbf` | DHCP | Active (primary Wi-Fi) |
<!-- markdownlint-enable MD060 -->

### Interface MAC addresses (Raspberry Pi 4B, NBI unit)

```text
eth0  MAC:  2c:cf:67:8e:b5:a9
wlan0 MAC:  2c:cf:67:8e:b5:aa
```

### Instrument connection profile details

```text
Profile name:               Instrument connection
UUID:                       c3612a53-4d0a-4587-b00c-6f6eaaef9f04
Interface:                  eth0
IP method:                  manual (static)
Address:                    10.0.8.72/24
Gateway:                    10.0.8.1
Autoconnect priority:       100 (preferred over mac-direct-auto)
```

Verify (if still present on device):

```bash
nmcli con show c3612a53-4d0a-4587-b00c-6f6eaaef9f04 \
  | grep -E 'connection.id|connection.autoconnect|ipv4.method|ipv4.addresses|ipv4.gateway'
```

---

## 3. Routing configuration (archived)

When the instrument LAN profile was active, routing was configured as follows:

- `eth0` metric: **800** (internet fallback only; Wi-Fi metric 100 took priority)
- Explicit route for filestore: `10.0.0.170/32` via `10.0.8.1` over `eth0`
- Explicit route for printer subnet: `149.155.211.0/24` via `eth0`

### nmcli commands used to configure

Set Ethernet as internet fallback (high metric):

```bash
sudo nmcli connection modify c3612a53-4d0a-4587-b00c-6f6eaaef9f04 \
  ipv4.never-default no \
  ipv4.route-metric 800
```

Set Wi-Fi as primary (low metric):

```bash
sudo nmcli connection modify e51d7392-116a-4dc6-8333-39fd9c718dbf \
  ipv4.route-metric 100
```

Force filestore traffic over Ethernet:

```bash
sudo nmcli connection modify c3612a53-4d0a-4587-b00c-6f6eaaef9f04 \
  +ipv4.routes "10.0.0.170/32 10.0.8.1"
```

### Routing verification commands

```bash
ip route
ip route get 8.8.8.8    # expected: via wlan0
ip route get 10.0.0.170  # expected: via 10.0.8.1 dev eth0 src 10.0.8.72
```

### Note on `10.0.0.170`

The host `10.0.0.170` (filestore/NAS) did not reply to ping during testing. It was therefore
not used as the instrument LAN detection target. The ARP probe in the auto-switch script
targeted the Institute gateway `10.0.8.1` instead.

---

## 4. Auto-switch mechanism (archived)

The auto-switch system allowed `eth0` to serve either the instrument LAN or a directly
connected MacBook, with automatic detection. The detection half (instrument LAN) is archived
here; the direct MacBook half (`mac-direct-auto`) remains active.

### Script location

```text
/usr/local/sbin/eth0-auto-switch.sh
```

### Trigger sources

- **Boot**: `eth0-auto-switch.service` systemd unit
- **Cable events**: NetworkManager dispatcher at `/etc/NetworkManager/dispatcher.d/90-eth0-auto-switch`
- **Periodic self-correction**: `eth0-auto-switch.timer` fires every 15 seconds

### Detection logic

The script sent three ARP packets to the Institute gateway (`10.0.8.1`) over `eth0`:

- If the gateway **replied** → Institute LAN is physically connected → activate
  `Instrument connection` → stop the direct-mode DHCP service
- If the gateway **did not reply** → assume direct MacBook cable → activate
  `mac-direct-auto` → start `automator-direct-dhcp.service`

A static IP alone was not sufficient to detect which device was connected: `10.0.8.72/24`
can be assigned even when the cable goes directly to a MacBook. ARP checks physical presence
at the link layer.

### Script content (archived)

```bash
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
  log "Stopping direct MacBook DHCP service: $DIRECT_DHCP_SERVICE"
  systemctl stop "$DIRECT_DHCP_SERVICE" >/dev/null 2>&1 || true
}

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

CURRENT_CON="$(nmcli -t -f NAME,DEVICE con show --active \
  | awk -F: -v dev="$ETH_DEV" '$2==dev{print $1; exit}')"
CURRENT_UUID="$(nmcli -t -f UUID,DEVICE con show --active \
  | awk -F: -v dev="$ETH_DEV" '$2==dev{print $1; exit}')"

log "$ETH_DEV has carrier; current active eth0 profile: ${CURRENT_CON:-none}"
log "Checking whether Institute gateway $INSTITUTE_GATEWAY is reachable on $ETH_DEV"

if arping -I "$ETH_DEV" -c 3 -w 3 "$INSTITUTE_GATEWAY" >/dev/null 2>&1; then
  log "Institute gateway $INSTITUTE_GATEWAY is reachable; Institute LAN is physically connected"
  stop_direct_dhcp
  if [ "$CURRENT_UUID" = "$INSTITUTE_PROFILE_UUID" ] \
    || [ "$CURRENT_CON" = "$INSTITUTE_PROFILE_NAME" ]; then
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
stop_direct_dhcp
exit 0
```

---

## 5. Admin access via instrument network (archived)

When the Pi was connected to the instrument LAN, the controller was reachable at:

```text
http://10.0.8.72:8080/
```

This URL is no longer reachable. The supported admin access paths are:

```text
http://127.0.0.1:8080/      (Pi desktop browser, always available)
http://automator.local:8080/ (mDNS, Pi desktop and connected MacBook)
http://192.168.50.2:8080/   (MacBook connected directly by Ethernet cable)
```

### Moonraker CORS and Flask trusted origins (clean-up note)

`http://10.0.8.72:8080` was listed in:

- `~/printer_data/config/moonraker.conf` under `cors_domains`
- `dev2/maincontroller.py` Socket.IO CORS allowed origins

These entries should be removed if the instrument network profile is permanently retired
from the device.

---

## 6. CUPS printer route (archived)

The Pi had a CUPS printer configured for instrument-network printing:

- Protocol: AppSocket / HP JetDirect (TCP 9100)
- URI format: `socket://<printer-ip>:9100`
- Connectivity test: `nc -vz <printer-ip> 9100`
- Printer subnet: `149.155.211.0/24`
- Traffic was always routed via `eth0` when the instrument LAN was active

The explicit printer route was added with:

```bash
sudo nmcli connection modify c3612a53-4d0a-4587-b00c-6f6eaaef9f04 \
  +ipv4.routes "149.155.211.0/24 10.0.8.1"
```

The Automator controller no longer sends QR sheets to a CUPS printer. The `/qr/print_sheet`
route returns a PDF download to the browser, which the user prints from their own computer.

---

## 7. SMB filestore (archived — physically removed)

The instrument LAN provided access to an SMB/CIFS filestore:

```text
Share:       //files/slproj/MS_results_temp
Mount point: /mnt/ms_results
Bind mount:  /mnt/AutomatorPiTSL   (bind of /mnt/ms_results, used by controller)
Credentials: dedicated NBI service account (stored in /etc/smbcred — file redacted)
Filestore IP: 10.0.0.170
```

The controller (`dev2/maincontroller.py`) previously copied each captured image to the
network share after writing it locally. This behaviour has been removed:

- The SMB mount was unmounted and removed from `/etc/fstab`
- `shared_storage_available()` always returns `False`
- `active_storage_root()` always returns the local data directory (`/home/pi/Automator/data/`)
- Image retrieval is now via the web UI file browser or USB export

The constant `NET_CAPTURES = "/mnt/AutomatorPiTSL"` remains defined in `maincontroller.py`
but is unused.

---

## 8. NTP time synchronisation

The NBI IT-approved NTP server was required regardless of which network was active:

```text
NTP server: ntp.nbi.ac.uk
Config:     /etc/systemd/timesyncd.conf.d/nbi-ntp.conf
```

```ini
[Time]
NTP=ntp.nbi.ac.uk
FallbackNTP=
```

NTP does not depend on the instrument network. The Pi synchronises time over Wi-Fi
(`IOT`). This configuration remains in place.

---

## 9. Current network state (for reference)

The Pi currently has:

<!-- markdownlint-disable MD060 -->
| Interface | Active profile | Address | Purpose |
|---|---|---|---|
| `wlan0` | `IOT` | DHCP (~10.0.112.x) | Primary internet |
| `eth0` | `mac-direct-auto` | 192.168.50.2/24 | Direct MacBook Ethernet access |
<!-- markdownlint-enable MD060 -->

The `Instrument connection` profile (`10.0.8.72/24`) may still be present in NetworkManager
on the device. It should either be left disabled (autoconnect no) or deleted, depending on
whether the physical Ethernet port is ever re-used for another purpose.

To disable it permanently without deleting:

```bash
sudo nmcli con modify c3612a53-4d0a-4587-b00c-6f6eaaef9f04 connection.autoconnect no
```

To delete it:

```bash
sudo nmcli con delete c3612a53-4d0a-4587-b00c-6f6eaaef9f04
```

---

Document archived 2026-06-23. Source documents: HandOver.md sections 4.8–4.9,
Raspberry_Pi_Direct_Ethernet_Access_from_MacBook_UPDATED.md,
networkandprintsettings.md, RunBook.md section 5.4,
Security_Model_Credential_Management.md, OS_and_Firmware_installation.md.
