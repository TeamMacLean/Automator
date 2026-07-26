<!--
SPDX-License-Identifier: CC-BY-4.0
Copyright (c) 2025–2026 Rohan R
-->

# Raspberry Pi Automatic Direct MacBook Ethernet Access



## Purpose

This document describes the setup for direct MacBook Ethernet access to the Raspberry Pi. When an Ethernet cable is connected from a MacBook to the Pi, the auto-switch script activates the `mac-direct-auto` profile and starts a DHCP server so the MacBook receives an IP address automatically. No terminal commands are needed on the MacBook.

The intended result is:

```text
Raspberry Pi connected directly to a MacBook:
  eth0 profile: mac-direct-auto
  eth0 IP:      192.168.50.2/24
  DHCP server:  ON, bound only to eth0

MacBook direct Ethernet:
  Configure IPv4: Using DHCP / automatic
  MacBook IP:     192.168.50.x/24 from the Pi

MacBook browser URL:
  http://192.168.50.2:8080/

Raspberry Pi Wi-Fi:
  wlan0 currently uses the IOT profile.
```

The setup keeps Wi-Fi and Ethernet separate. The Raspberry Pi Wi-Fi profile currently active on `wlan0` is `IOT`. All automatic switching logic applies only to `eth0`.

The earlier `169.254.50.2/16` link-local design was replaced because macOS sometimes routed `169.254.0.0/16` via Wi-Fi, or accepted packets without reliably replying over Ethernet. The private subnet `192.168.50.0/24` with direct-mode DHCP is more predictable for MacBook users.

---

## Confirmed Network Details

### Raspberry Pi interfaces

| Interface | Purpose |
|---|---|
| `wlan0` | IOT Wi-Fi |
| `eth0` | Direct MacBook Ethernet |
| `lo` | loopback |

### Confirmed profiles

| Purpose | NetworkManager profile | UUID | Interface |
|---|---|---|---|
| Current Wi-Fi | `IOT` | `e51d7392-116a-4dc6-8333-39fd9c718dbf` | `wlan0` |
| Automatic direct profile | `mac-direct-auto` | `65c3e7b6-303b-421a-9590-e41b9f1ce6b2` | `eth0` |

The removed `mac-direct` profile should not appear in `nmcli con show`.

### Confirmed direct MacBook values

```text
Raspberry Pi direct eth0 address: 192.168.50.2/24
Direct DHCP range given to Mac:    192.168.50.10 - 192.168.50.100
MacBook URL:                       http://192.168.50.2:8080/
```

### Confirmed interface MAC addresses

These values were read from the Raspberry Pi while `eth0` was connected directly to a MacBook and `wlan0` was connected to the `IOT` Wi-Fi profile.

```text
eth0 MAC:  2c:cf:67:8e:b5:a9
wlan0 MAC: 2c:cf:67:8e:b5:aa
```

---

## Important Design Decisions

### Why direct mode uses `192.168.50.0/24`

The original direct Ethernet design used:

```text
Pi:      169.254.50.2/16
MacBook: 169.254.x.x/16
```

During testing, macOS repeatedly routed `169.254.50.2` through Wi-Fi (`en0`) instead of Ethernet (`en8`), and packet captures showed unreliable reply behaviour even when packets crossed the cable.

The working direct Ethernet design now uses a normal private subnet:

```text
Pi:      192.168.50.2/24
MacBook: 192.168.50.x/24, assigned automatically by DHCP
```

This avoids macOS link-local routing ambiguity and gives a stable direct URL:

```text
http://192.168.50.2:8080/
```

### Why DHCP is started only in direct MacBook mode

For a normal Mac user, the Ethernet adapter should stay on:

```text
Configure IPv4: Using DHCP / automatic
```

The Raspberry Pi starts a small DHCP server only when `eth0` is in direct MacBook mode. This gives the MacBook a `192.168.50.x` address automatically. The user does not need to run `ifconfig`, `route`, or any terminal command.

### Why a lock is used

NetworkManager dispatcher events can trigger repeatedly when a profile changes. Without protection, the script can be started many times at once, causing repeated switching between profiles.

The final script uses `flock` with:

```text
/run/eth0-auto-switch.lock
```

This prevents overlapping runs.

### Why a systemd timer is used

Cable changes do not always produce the expected NetworkManager dispatcher event. A periodic systemd timer makes the Raspberry Pi self-correct after cable changes.

The timer runs the check every 15 seconds.

---

# Full Setup Instructions

## 1. Show current devices and profiles

Run on the Raspberry Pi:

```bash
nmcli dev status
nmcli con show
nmcli con show --active
```

Expected active state when connected directly to a MacBook:

```text
IOT                wifi      wlan0
mac-direct-auto    ethernet  eth0
```

---

## 2. Confirm the old manual `mac-direct` profile has been removed

The old `mac-direct` profile used the earlier manual direct-Ethernet design. It has now been removed. The only direct MacBook Ethernet profile that should remain is:

```text
mac-direct-auto
```

Verify that `mac-direct-auto` exists and `mac-direct` is absent:

```bash
nmcli con show | grep -Ei 'mac-direct|direct|auto' || true
nmcli con show mac-direct 2>/dev/null || echo "mac-direct profile not found"
```

Expected:

```text
mac-direct-auto         65c3e7b6-303b-421a-9590-e41b9f1ce6b2  ethernet   eth0
mac-direct profile not found
```

## 3. Create or correct the automatic direct MacBook profile

The direct MacBook profile is:

```text
Profile name: mac-direct-auto
Pi address:   192.168.50.2/24
Interface:    eth0
```

Create it if it does not already exist:

```bash
sudo nmcli con add type ethernet ifname eth0 con-name mac-direct-auto \
  ipv4.method manual \
  ipv4.addresses 192.168.50.2/24 \
  ipv4.gateway "" \
  ipv4.never-default yes \
  ipv6.method ignore \
  connection.autoconnect yes \
  connection.autoconnect-priority -50
```

If it already exists, enforce the correct settings:

```bash
sudo nmcli con modify mac-direct-auto \
  ipv4.method manual \
  ipv4.addresses 192.168.50.2/24 \
  ipv4.gateway "" \
  ipv4.routes "" \
  ipv4.never-default yes \
  ipv6.method ignore \
  connection.autoconnect yes \
  connection.autoconnect-priority -50
```

Verify:

```bash
nmcli con show mac-direct-auto | grep -E 'connection.id|connection.interface-name|connection.autoconnect|connection.autoconnect-priority|ipv4.method|ipv4.addresses|ipv4.gateway|ipv4.routes|ipv4.never-default|ipv6.method'
```

Expected:

```text
connection.id:                     mac-direct-auto
connection.interface-name:         eth0
connection.autoconnect:            yes
connection.autoconnect-priority:   -50
ipv4.method:                       manual
ipv4.addresses:                    192.168.50.2/24
ipv4.gateway:                      --
ipv4.routes:                       --
ipv4.never-default:                yes
ipv6.method:                       ignore
```

---

## 4. Install required tools

Install `arping`, `dnsmasq`, and optional debugging tools:

```bash
sudo apt update
sudo apt install -y arping dnsmasq tcpdump
```

Disable the default `dnsmasq` service. The system will use a dedicated direct-mode DHCP service instead.

```bash
sudo systemctl disable --now dnsmasq
```

Verify `arping`:

```bash
command -v arping
```

Expected:

```text
/usr/sbin/arping
```

---

## 5. Configure direct-mode DHCP with `dnsmasq`

Create a dnsmasq configuration file for direct Ethernet only:

```bash
sudo nano /etc/dnsmasq.d/automator-direct-eth0.conf
```

Paste:

```ini
interface=eth0
bind-interfaces

dhcp-authoritative
dhcp-range=192.168.50.10,192.168.50.100,255.255.255.0,12h

# Do not give the MacBook a router or DNS server.
# This direct link is only for Automator access.
dhcp-option=3
dhcp-option=6
dhcp-option=1,255.255.255.0

log-dhcp
```

Create a dedicated systemd service:

```bash
sudo nano /etc/systemd/system/automator-direct-dhcp.service
```

Paste:

```ini
[Unit]
Description=Direct MacBook DHCP server for Automator eth0
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/usr/sbin/dnsmasq --no-daemon --conf-file=/etc/dnsmasq.d/automator-direct-eth0.conf
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Reload systemd:

```bash
sudo systemctl daemon-reload
```

Do **not** enable this service globally. It must be started and stopped only by the auto-switch script.

Check that it is currently stopped:

```bash
systemctl is-active automator-direct-dhcp.service
```

Expected before direct mode is active:

```text
inactive
```

---

## 6. Create the final auto-switch script

Create or edit the script:

```bash
sudo nano /usr/local/sbin/eth0-auto-switch.sh
```

Paste the following complete script:

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
```

Save and exit:

```text
Ctrl + O
Enter
Ctrl + X
```

Make the script executable:

```bash
sudo chmod +x /usr/local/sbin/eth0-auto-switch.sh
```

Verify the script contains the current direct subnet and DHCP service name:

```bash
grep -nE '169\.254|192\.168\.50|automator-direct-dhcp' /usr/local/sbin/eth0-auto-switch.sh
```

Expected: references to `192.168.50.2` and `automator-direct-dhcp.service`; no `169.254.50.2` references.

---

## 7. Manually test direct MacBook mode

Connect the Raspberry Pi directly to a MacBook using Ethernet.

Run on the Raspberry Pi:

```bash
sudo /usr/local/sbin/eth0-auto-switch.sh
echo $?
```

Expected output (first run or after cable reconnect):

```text
eth0 has carrier; current active eth0 profile: none
Checking whether Institute gateway 10.0.8.1 is reachable on eth0
Institute gateway 10.0.8.1 not reachable; assuming direct MacBook cable
Switching to mac-direct-auto
Direct MacBook mode active on 192.168.50.2/24
Starting direct MacBook DHCP service: automator-direct-dhcp.service
0
```

Run a second time while still connected to the MacBook:

```bash
sudo /usr/local/sbin/eth0-auto-switch.sh
echo $?
```

Expected output:

```text
eth0 has carrier; current active eth0 profile: mac-direct-auto
Checking whether Institute gateway 10.0.8.1 is reachable on eth0
Institute gateway 10.0.8.1 not reachable; assuming direct MacBook cable
Already on mac-direct-auto with 192.168.50.2/24; ensuring DHCP service is running
Starting direct MacBook DHCP service: automator-direct-dhcp.service
0
```

Verify:

```bash
nmcli con show --active
ip -4 addr show eth0
systemctl status automator-direct-dhcp.service --no-pager
sudo ss -ltnp | grep ':8080'
```

Expected:

```text
mac-direct-auto   ethernet  eth0
inet 192.168.50.2/24
automator-direct-dhcp.service active/running
LISTEN ... 0.0.0.0:8080
```

If the web server only listens on `127.0.0.1:8080`, it will not be reachable from a MacBook. It must listen on `0.0.0.0:8080` or `*:8080`.

---

## 8. Create the boot-time systemd service

Create the service:

```bash
sudo nano /etc/systemd/system/eth0-auto-switch.service
```

Paste:

```ini
[Unit]
Description=Auto switch eth0 between Institute LAN and direct MacBook mode
After=NetworkManager.service
Wants=NetworkManager.service

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/eth0-auto-switch.sh
RemainAfterExit=no

[Install]
WantedBy=multi-user.target
```

Enable it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable eth0-auto-switch.service
```

Test it:

```bash
sudo systemctl start eth0-auto-switch.service
systemctl status eth0-auto-switch.service --no-pager
```

Expected successful oneshot state:

```text
Active: inactive (dead)
code=exited, status=0/SUCCESS
```

If an old failed state remains:

```bash
sudo systemctl reset-failed eth0-auto-switch.service
```

---

## 9. Create the NetworkManager dispatcher hook

The dispatcher reacts when NetworkManager sees Ethernet events.

Create the dispatcher file:

```bash
sudo nano /etc/NetworkManager/dispatcher.d/90-eth0-auto-switch
```

Paste:

```bash
#!/usr/bin/env bash

IFACE="$1"
STATUS="$2"

if [ "$IFACE" != "eth0" ]; then
  exit 0
fi

case "$STATUS" in
  up|connectivity-change)
    /usr/local/sbin/eth0-auto-switch.sh &
    ;;
esac

exit 0
```

Make it executable:

```bash
sudo chmod +x /etc/NetworkManager/dispatcher.d/90-eth0-auto-switch
```

Restart NetworkManager:

```bash
sudo systemctl restart NetworkManager
```

Check logs:

```bash
journalctl -t eth0-auto-switch --no-pager -n 50
```

Occasional messages such as this are acceptable:

```text
Another eth0-auto-switch instance is already running; exiting
```

Continuous repeated switching is not acceptable. The final script prevents overlapping runs using `flock`.

---

## 10. Create the systemd timer for reliable cable switching

Because dispatcher events may not always fire on cable changes, a timer is recommended.

Create the timer:

```bash
sudo nano /etc/systemd/system/eth0-auto-switch.timer
```

Paste:

```ini
[Unit]
Description=Run eth0 auto switch periodically

[Timer]
OnBootSec=20
OnUnitActiveSec=15
AccuracySec=5
Unit=eth0-auto-switch.service

[Install]
WantedBy=timers.target
```

Enable the timer:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now eth0-auto-switch.timer
```

Check:

```bash
systemctl status eth0-auto-switch.timer --no-pager
systemctl list-timers --all | grep eth0-auto-switch
```

Expected:

```text
eth0-auto-switch.timer loaded active waiting
```

After connecting or disconnecting an Ethernet cable, the Raspberry Pi should self-correct within approximately 15 to 20 seconds.

---

# Final Validation

## Direct MacBook validation

Connect the Raspberry Pi directly to a MacBook and wait up to 20 seconds.

Run on the Raspberry Pi:

```bash
nmcli con show --active
ip -4 addr show eth0
systemctl status automator-direct-dhcp.service --no-pager
journalctl -t eth0-auto-switch --no-pager -n 30
sudo ss -ltnp | grep ':8080'
```

Expected:

```text
mac-direct-auto   ethernet  eth0
inet 192.168.50.2/24
automator-direct-dhcp.service active/running
LISTEN ... 0.0.0.0:8080
```

Expected log pattern:

```text
Institute gateway 10.0.8.1 not reachable; assuming direct MacBook cable
Direct MacBook mode active on 192.168.50.2/24
Starting direct MacBook DHCP service: automator-direct-dhcp.service
```

---

# MacBook Access Instructions

For normal use, a MacBook user should only need to:

1. Connect the Ethernet cable between the MacBook and Raspberry Pi.
2. Keep the MacBook Ethernet adapter on `Using DHCP` / automatic IPv4.
3. Wait approximately 15 to 20 seconds for the Raspberry Pi to switch mode and start DHCP.
4. Open:

```text
http://192.168.50.2:8080/
```

5. Log in when prompted.

No terminal commands should be required on the MacBook.

## Configure the MacBook Ethernet adapter in System Settings

On macOS:

1. Open **System Settings**.
2. Go to **Network**.
3. Select the USB Ethernet adapter.
4. Open **Details**.
5. Go to **TCP/IP**.
6. Set **Configure IPv4** to:

```text
Using DHCP
```

7. Leave router and DNS automatic/blank. The Pi direct DHCP server intentionally does not provide an internet router.

A working MacBook Ethernet address should look like:

```text
192.168.50.x
```

Example:

```text
MacBook Ethernet IP: 192.168.50.10/24
Raspberry Pi IP:     192.168.50.2/24
```

## Test from MacBook if needed

A normal user does not need these commands. They are only for troubleshooting.

Find the active Ethernet interface:

```bash
ifconfig
```

Check the route:

```bash
route -n get 192.168.50.2
```

Good result:

```text
interface: en8
```

Bad result:

```text
interface: en0
```

On many MacBooks, `en0` is Wi-Fi.

Test the web UI:

```bash
curl -v http://192.168.50.2:8080/
```

A successful unauthenticated curl should return:

```text
HTTP/1.1 401 UNAUTHORIZED
Www-Authenticate: Basic realm="Automator"
```

That is a good result. It means the web UI is reachable and is asking for Basic Authentication.

---

# MacBook Troubleshooting

## 1. Check the MacBook Ethernet interface

Run on the MacBook:

```bash
ifconfig
```

Find the active Ethernet interface. It may be named `en5`, `en6`, `en7`, `en8`, or similar.

A working Ethernet interface should show something like:

```text
en8:
  inet 192.168.50.10 netmask 0xffffff00
  media: autoselect (1000baseT <full-duplex>)
  status: active
```

If the address is still `169.254.x.x`, the MacBook did not receive DHCP from the Pi. Check that the Raspberry Pi is in direct mode and `automator-direct-dhcp.service` is active.

## 2. Renew DHCP on MacBook

From the macOS GUI, select the USB Ethernet adapter and use **Renew DHCP Lease**.

Optional terminal equivalent:

```bash
sudo ipconfig set en8 DHCP
```

Replace `en8` with the actual Ethernet interface if different.

## 3. Check the route to the Raspberry Pi

Run on the MacBook:

```bash
route -n get 192.168.50.2
```

Good result:

```text
interface: en8
```

Bad result:

```text
interface: en0
```

If it routes through Wi-Fi, temporarily disable Wi-Fi or add a host route:

```bash
sudo route -n delete -host 192.168.50.2 2>/dev/null
sudo route -n add -host 192.168.50.2 -interface en8
```

## 4. Remove old link-local routes if they interfere

The old design used `169.254.50.2`. If your Mac still has stale routes, remove them:

```bash
sudo route -n delete -host 169.254.50.2 2>/dev/null
sudo route -n delete -net 169.254.0.0/16 2>/dev/null
```

Then test the correct address:

```bash
route -n get 192.168.50.2
curl -v http://192.168.50.2:8080/
```

---

# Raspberry Pi Troubleshooting

## Check active profiles

```bash
nmcli con show --active
```

## Check Ethernet IP

```bash
ip -4 addr show eth0
```

Good direct-mode result:

```text
inet 192.168.50.2/24
```

## Check direct DHCP status

```bash
systemctl status automator-direct-dhcp.service --no-pager
```

In direct MacBook mode, expected:

```text
active/running
```

If DHCP is not running when expected, start it manually and then run the auto-switch script:

```bash
sudo /usr/local/sbin/eth0-auto-switch.sh
```

## Check DHCP logs

```bash
journalctl -u automator-direct-dhcp.service --no-pager -n 80
```

or live:

```bash
journalctl -u automator-direct-dhcp.service --follow
```

You should see DHCP requests and leases when a MacBook is connected.

## Check web server binding

```bash
sudo ss -ltnp | grep ':8080'
```

Good:

```text
0.0.0.0:8080
```

or:

```text
*:8080
```

Bad:

```text
127.0.0.1:8080
```

If the app listens only on `127.0.0.1`, it is reachable only from the Raspberry Pi itself.

## Check auto-switch logs

```bash
journalctl -t eth0-auto-switch --no-pager -n 50
```

Live view:

```bash
journalctl -t eth0-auto-switch --since "now" --follow
```

## Watch packets on `eth0`

For DHCP:

```bash
sudo tcpdump -ni eth0 'udp port 67 or udp port 68'
```

For web UI tests:

```bash
sudo tcpdump -ni eth0 'host 192.168.50.10 and tcp port 8080'
```

Replace `192.168.50.10` with the MacBook DHCP address if different.

---

# Recovery Commands

## Force direct MacBook mode

```bash
sudo nmcli con up mac-direct-auto ifname eth0
sudo systemctl start automator-direct-dhcp.service
```

Verify:

```bash
nmcli con show --active
ip -4 addr show eth0
systemctl status automator-direct-dhcp.service --no-pager
```

Expected:

```text
mac-direct-auto
192.168.50.2/24
automator-direct-dhcp.service active/running
```

## Restart automatic switching

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now eth0-auto-switch.timer
sudo systemctl restart eth0-auto-switch.timer
```

## Temporarily disable dispatcher

```bash
sudo chmod -x /etc/NetworkManager/dispatcher.d/90-eth0-auto-switch
```

## Re-enable dispatcher

```bash
sudo chmod +x /etc/NetworkManager/dispatcher.d/90-eth0-auto-switch
```

## Disable timer

```bash
sudo systemctl disable --now eth0-auto-switch.timer
```

## Re-enable timer

```bash
sudo systemctl enable --now eth0-auto-switch.timer
```

## Clear old failed service state

```bash
sudo systemctl reset-failed eth0-auto-switch.service
sudo systemctl reset-failed automator-direct-dhcp.service
```

---

# Final Expected Behaviour

## Raspberry Pi connected directly to a MacBook

```text
eth0 profile: mac-direct-auto
eth0 IP:      192.168.50.2/24
wlan0:        IOT unchanged
DHCP service: automator-direct-dhcp.service active
MacBook IP:   192.168.50.x/24 from DHCP
MacBook URL:  http://192.168.50.2:8080/
```

## Web UI authentication behaviour

A browser should prompt for login.

A curl test may show:

```text
HTTP/1.1 401 UNAUTHORIZED
Www-Authenticate: Basic realm="Automator"
```

This confirms that:

```text
MacBook can reach Raspberry Pi.
Raspberry Pi web app is running.
The / route is reachable.
Authentication is required.
```

---

# Notes on the old link-local design

The old direct MacBook design used:

```text
Raspberry Pi direct IP: 169.254.50.2/16
MacBook IP:             169.254.x.x/16
Browser URL:            http://169.254.50.2:8080/
```

This was replaced after testing showed that macOS could route `169.254.0.0/16` through Wi-Fi or behave inconsistently with link-local replies. The final working design is now:

```text
Raspberry Pi direct IP: 192.168.50.2/24
MacBook IP:             192.168.50.x/24 from Pi DHCP
Browser URL:            http://192.168.50.2:8080/
```

Do not use the old `169.254.50.2` URL for normal direct access.

---

# Safety Checklist

Before considering the setup complete, verify these three states.

## Direct MacBook mode

```bash
nmcli con show --active
ip -4 addr show eth0
systemctl is-active automator-direct-dhcp.service
curl -v http://192.168.50.2:8080/
```

Expected:

```text
mac-direct-auto active on eth0
192.168.50.2/24
active
HTTP/1.1 401 UNAUTHORIZED
```

## MacBook user mode

```text
MacBook Ethernet IPv4: Using DHCP
MacBook receives:       192.168.50.x
User opens:             http://192.168.50.2:8080/
No Mac terminal commands required.
```