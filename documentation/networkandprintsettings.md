<!--
SPDX-License-Identifier: CC-BY-4.0
Copyright (c) 2025–2026 Rohan R
-->

# Raspberry Pi network configuration

This document describes the design principles and operational behaviour of the Raspberry Pi network setup for the Automator system.

For the full step-by-step implementation (UUIDs, nmcli commands, scripts, and service files) see [HandOver.md](HandOver.md) sections 4.8–4.10 and [Raspberry_Pi_Direct_Ethernet_Access_from_MacBook_UPDATED.md](Raspberry_Pi_Direct_Ethernet_Access_from_MacBook_UPDATED.md).

---

## Scope and audience

This guide is intended as:

- A design reference
- An architecture overview
- A reusable pattern that can be adapted to other environments

It is not a copy-and-paste configuration for external networks.

---

## High-Level design

The Raspberry Pi uses two network interfaces managed by NetworkManager.

### Network roles

Wi-Fi (`wlan0`)

- Primary Internet access
- Default route under normal operation
- Used for system updates and web interfaces
- Active profile: `IOT`

Ethernet (`eth0`)

- Direct MacBook access only — the Pi assigns the MacBook a `192.168.50.x` address automatically via DHCP when a cable is connected directly
- Active profile: `mac-direct-auto` (`192.168.50.2/24`)
- Do not connect the Ethernet cable to the institute or instrument network

The auto-switch script (`/usr/local/sbin/eth0-auto-switch.sh`) activates `mac-direct-auto` and starts the DHCP service (`automator-direct-dhcp.service`) whenever an Ethernet cable is detected. The script is triggered at boot, on cable events, and every 15 seconds by a systemd timer.

---

## Traffic behaviour summary

<!-- markdownlint-disable MD060 -->
| Traffic Type      | Interface |
|-------------------|-----------|
| Internet          | Wi-Fi     |
| Controller web UI | Direct MacBook Ethernet for users; Pi desktop browser for admins |
| QR PDF download   | Browser path used for the controller web UI |
<!-- markdownlint-enable MD060 -->

---

## Key design principles

- Routing decisions are made at the OS level
- Route metrics determine preference and fallback
- Configuration is persistent, auditable, and aligned with enterprise IT practices

---

## Controller access

<!-- markdownlint-disable MD060 -->
| URL | When it works |
|-----|---------------|
| `http://192.168.50.2:8080/` | MacBook connected by direct Ethernet cable |
| `http://automator.local:8080/` | mDNS hostname — works from a connected MacBook and from the Pi desktop browser |
| `http://127.0.0.1:8080/` | Pi desktop browser only |
<!-- markdownlint-enable MD060 -->

- The MacBook USB-C Ethernet adapter must be set to Using DHCP (the default); the Pi assigns a `192.168.50.x` address automatically in direct mode
- The Pi boots into a full-screen kiosk at `http://127.0.0.1:8080/` when a monitor, keyboard, and mouse are connected — no MacBook needed. Use only one access method at a time to avoid latency
- Admins exit kiosk with `Ctrl+Alt+A` to reach the Pi desktop browser; `Windows+K` returns to kiosk
- Terminal, NetworkManager, service, and desktop access is for technical/admin maintenance only

---

## QR PDF printing

- The controller generates QR sheets as downloadable PDF files
- Printing is handled by the user's own computer after download
- The Raspberry Pi does not need an application-level network printer path for the Automator QR workflow

---

## File access

- Images are stored locally on the Pi at `/home/pi/Automator/data/`
- Image retrieval is via the web UI file browser (when connected by MacBook Ethernet or kiosk) or USB export

---

## Time synchronisation

- NTP server: `ntp.nbi.ac.uk` (NBI IT policy — public NTP pools are not used)
- Config file: `/etc/systemd/timesyncd.conf.d/nbi-ntp.conf`
- Time synchronisation persists across reboots; synchronises over Wi-Fi
- Verify: `timedatectl timesync-status` / `timedatectl status`

---

## Failure behaviour (intentional)

<!-- markdownlint-disable MD060 -->
| Scenario | Internet | Controller UI | File Access |
|----------|----------|---------------|-------------|
| Wi-Fi up, MacBook Ethernet active | Wi-Fi | Yes | Yes (local) |
| Wi-Fi down, MacBook Ethernet active | None | Yes | Yes (local) |
| Ethernet cable disconnected, Wi-Fi up | Wi-Fi | Yes, if reachable over Wi-Fi/local hostname | Yes (local) |
<!-- markdownlint-enable MD060 -->

This behaviour is intentional.

---

## Summary

This architecture provides:

- Clear separation of network roles
- Automatic direct MacBook Ethernet access
- User access through `http://192.168.50.2:8080/`
- IT-approved time synchronisation via Wi-Fi
- A maintainable Raspberry Pi deployment model

Public overview; internal details intentionally excluded.

Document updated on 23/06/2026 Rohan R.
