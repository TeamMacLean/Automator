<!--
SPDX-License-Identifier: CC-BY-4.0
Copyright (c) 2025–2026 Rohan R
-->
<!-- markdownlint-disable MD060 MD029 -->

# Automated Petri-Dish Imaging System Run Book

---

## Document Information

| Field | Value |
|:---|:---|
| **Version** | 0.0.2 |
| **Author** | Rohan R |
| **Effective Date** | 2026-03-23 |
| **Last Updated** | 2026-07-26 (v3.0.0) |
| **Review Cycle** | Every 6 months |

---

## Table of Contents

1. [Document control](#1-document-control)
2. [System overview](#2-system-overview)
3. [Roles and responsibilities](#3-roles-and-responsibilities)
4. [Safety guidelines](#4-safety-guidelines)
5. [Installation procedure](#5-installation-procedure)
6. [System startup procedure](#6-system-startup-procedure)
7. [Calibration procedure](#7-calibration-procedure)
8. [Imaging workflow operation](#8-imaging-workflow-operation)
9. [Monitoring and health checks](#9-monitoring-and-health-checks)
10. [Backup and data management](#10-backup-and-data-management)
11. [Failure scenarios and troubleshooting](#11-failure-scenarios-and-troubleshooting)
12. [Recovery procedures](#12-recovery-procedures)
13. [Maintenance schedule](#13-maintenance-schedule)
14. [Security considerations](#14-security-considerations)
15. [Decommissioning procedure](#15-decommissioning-procedure)

---

## 1. Document control

### 1.1 Change history

| Version | Date | Author | Change Summary |
|:---|:---|:---|:---|
| **3.0.0** | 2026-07-26 | Rohan R | Updated for v3.0.0: repo reinitialised, version bump |
| **2.0.0** | 2026-07-26 | Rohan R | Updated for v2.0.0: 6-dish workspace limit, round Petri dishes/plates 90–100 mm, grid overlay, popup, Select All |
| **1.0.1** | 2026-07-20 | Rohan R | Added fallback detection, unresolved plate workflow, 5-dish workspace limit, green sticker placement |
| **1.0.0** | 2026-06-26 | Rohan R | Updated to match v1.0.0 software release |
| 0.0.2 | 2026-03-23 | Rohan R | Added validation columns for all procedures; improved formatting; restructured maintenance schedule |
| 0.0.1 | 2026-03-16 | Rohan R | Updated against current repository behavior: current UI labels/workflow, interval units/modes |

---

## 2. System overview

### 2.1 Architecture summary

The Automated Petri-Dish Imaging System is a Raspberry Pi–controlled laboratory platform combining:

1. Cartesian motion hardware (X/Y/Z gantry, stepper motors, belt drive, camera rail).
2. Imaging hardware (Raspberry Pi camera, USB camera for detection).
3. Control electronics (Raspberry Pi + MKS Robin Nano + relay-driven peripherals).
4. A Flask/SocketIO software controller (`dev2/maincontroller.py`) with a browser UI.

Primary purpose:

1. Detect QR-labelled plates in workspace.
2. Schedule repeated image captures per selected plate.
3. Save images locally and to network storage.
4. Support pause/resume/start-stop controls with safety-first behavior.
5. Detect plate positions geometrically (OpenCV fallback) for dishes whose QR code cannot be read; expose these as unresolved detections for manual identification.

### 2.2 Hardware diagram description (textual)

1. External PSU feeds motion and control electronics.
2. Raspberry Pi hosts web app, camera stack, scheduling logic, and state.
3. MKS Robin Nano executes motion commands from Pi via Klipper/Moonraker.
4. Gantry axes move imaging head/camera over Petri platform.
5. Door sensor and stop controls gate safe operation.
6. LED/relay/vacuum/servo controls execute per-capture sequence.
7. Ethernet provides local network and storage/service connectivity.

### 2.3 Software architecture

All software runs from `/home/pi/Automator/` on the Raspberry Pi.

#### Production controller — dev2/maincontroller.py (Flask + SocketIO, port 8080)

This is the primary runtime for all imaging operations. Key endpoints:

1. UI pages: `/`, `/main`.
2. Detection/config/scheduling: `/detect` (optional `?pulse=1`), `/config` (optional `?pulse=1`), `/system/start`.
3. Runtime controls: `/system/pause`, `/system/unpause`, `/system/start_stop`.
4. Telemetry/status: `/system/state`, `/system/logs`, `/system/disk`, `/system/version`.
5. QR workflow: `/qr/generate`, `/qr/print_sheet` (downloads an A4 PDF; it does not print from the Pi).
6. File browsing (local/LAN): `/files/*`.

Hard-coded runtime paths:

1. `/home/pi/Automator/dev2`
2. `/home/pi/Automator/data`
3. `/home/pi/Automator/raw`

#### Diagnostics tools (internal use only)

`dev2/maindiagnostics.py` and `dev2/main_mjpeg_server.py` provide a live MJPEG stream, position telemetry, and diagnostics UI for internal testing and troubleshooting. These are separate from the production controller and are documented in `documentation/diagnosticsserver.md`. They are not required for normal imaging operations.

### 2.4 Data flow

1. Operator creates QR labels, downloads the generated A4 PDF sheet, prints it from their own computer, and labels dishes. (Labels can alternatively be generated offline via the standalone `qr-generator-Automator` PyPI package — see `documentation/HowToUseAutomator.md`.)
2. Operator proceeds to the main imaging page.
3. USB camera workspace scan detects plates and maps coordinates.
3a. Plates detected by shape but with unreadable QR codes are placed in the unresolved detections list. Operators may identify them manually (entering QR data via the UI) or dismiss them.
4. Operator configures optional experiment tag, per-plate interval, runtime duration, and selection.
5. Scheduler builds tasks for selected plates.
6. Motion + capture sequence runs repeatedly.
7. Image saved to `/home/pi/Automator/data/captures/` (local only).
8. USB export: if a USB drive is plugged in, the local Automator image/data folder is automatically copied to `/images/` on the drive and the drive is unmounted safely.
9. Filenames/folders include `_tag-<clean_tag>` suffix when an experiment tag is set.
10. Logs emitted to UI and persisted in `raw/controller.log`.
11. Optional completion emails sent at schedule completion (institute addresses only: `@nbi.ac.uk` / `@tsl.ac.uk`; entered on the imaging page below the experiment tag).

State and persistence:

1. Plate DB: `/home/pi/Automator/raw/plates_db.json`
2. Runtime state: `/home/pi/Automator/raw/controller_state.json`
3. Logs: `/home/pi/Automator/raw/controller.log`

### 2.5 Key hardware and software components

All software runs from `/home/pi/Automator/` on the Raspberry Pi. The following four components must all be running for the system to operate correctly.

#### Raspberry Pi 4B

The Raspberry Pi 4B is the host computer for the Automator. It runs the Flask web server (port 8080) that operators use through their browser, manages the imaging schedule, controls the cameras, sends motion commands to the motor controller, and handles the GPIO lines for buttons, LEDs, and the door sensor.

Hardware details: BCM2711 quad-core processor, 8 GB RAM, 64 GB microSD card. Interfaces in use: two USB 3.0 ports for cameras, micro-HDMI for a maintenance display, Ethernet for LAN or direct MacBook connection, GPIO header for buttons (pins 17/27), LED relay (pin 23), and door sensor (pin 26).

For Pi desktop access during maintenance, connect the micro-HDMI end of the display cable to the Pi 4B, connect the normal HDMI end to a monitor, and connect keyboard and mouse to the Pi USB ports.

#### MKS Robin Nano V3.1

The MKS Robin Nano V3.1 is a motion controller board based on the STM32F407 microcontroller, originally designed for 3D printers. In the Automator it drives the X, Y, and Z stepper motors that move the camera arm over the Petri dish workspace, controls the servo that lifts plate lids, and handles relay outputs for LEDs and the vacuum hold system.

The board connects to the Raspberry Pi over USB serial and runs Klipper's MCU firmware, which receives motion commands from the Klipper host process on the Pi and generates the step pulses that drive the stepper motor drivers. If the board loses power or its USB connection drops, Klipper reports an MCU error and motion stops.

#### Klipper

Klipper is an open-source firmware for motion control. It is split into two parts:

1. A host process on the Raspberry Pi (systemd service `klipper`) that handles motion planning, G-code interpretation, and configuration. Its configuration file is at `~/printer_data/config/printer.cfg`.
2. A firmware binary on the MKS Robin Nano that generates step pulses with microsecond precision.

The Automator's Flask controller (`dev2/maincontroller.py`) sends G-code commands through Klipper via Moonraker. These commands move the axes (`G28`, `G0`, `G1`), control GPIO pins (`SET_PIN`), and run macros defined in `printer.cfg`. If Klipper is not running, the controller cannot move the camera arm.

To check Klipper status:

```bash
sudo systemctl status klipper
journalctl -u klipper -n 50 --no-pager
```

#### Moonraker

Moonraker is an HTTP and WebSocket API server that wraps Klipper, running on port 7125. The Flask controller sends HTTP requests to Moonraker, which translates them to Klipper commands and returns status information. Moonraker runs as a systemd service (`moonraker`) with configuration at `~/printer_data/config/moonraker.conf`.

To check Moonraker status:

```bash
sudo systemctl status moonraker
journalctl -u moonraker -n 50 --no-pager
```

If either Klipper or Moonraker is not running, restart both before troubleshooting motion failures:

```bash
sudo systemctl restart klipper moonraker
```

Normal users can restart Klipper or Moonraker individually from the web UI by clicking **Troubleshooting** in the `/main` footer.

---

## 3. Roles and responsibilities

### 3.1 Operator

1. Prepare and label plates.
2. Run UI workflow (scan, select, configure, save, start).
3. Monitor run status and disk/log indicators.
4. Use Pause/Resume/Start-Stop during normal intervention.
5. Use the physical AC-side emergency stop only for unsafe conditions.
6. Use one of the supported normal-user access paths:
   - **Kiosk display** (monitor + keyboard + mouse connected to the Pi) — boots automatically into a full-screen browser; no MacBook needed.
   - **MacBook Ethernet** — connect directly by Ethernet cable (MacBook adapter on Using DHCP); the Pi assigns a `192.168.50.x` address automatically; navigate to `http://192.168.50.2:8080/` or `http://automator.local:8080/`.
   - Use only one access method at a time to avoid latency.
7. Do not use Raspberry Pi desktop, Pi-local browser, terminal, NetworkManager, or service controls during normal operation.
8. Retrieve images through the web UI preview/file browser or USB export. Operators are not expected to use terminal commands.

### 3.2 Lab technician

1. Verify calibration quality and imaging consistency.
2. Perform daily/weekly physical checks.
3. Verify image output and metadata naming correctness.
4. Execute first-level troubleshooting and incident logging.

### 3.3 System administrator

1. Manage service lifecycle (`automator-controller.service` and related services).
2. Maintain OS/packages/security updates.
3. Maintain credentials/environment variables.
4. Ensure network mount and storage availability.
5. Perform backup/restore operations.
6. Use terminal or Raspberry Pi desktop access for maintenance when required. For direct desktop access, connect the micro-HDMI end of the display cable to the Pi 4B, connect the normal HDMI end to the monitor/display, and connect keyboard/mouse to the Pi USB ports.
7. Exit kiosk with `Ctrl+Alt+A` before opening the Pi desktop browser; `Windows+K` returns to kiosk. From the Pi desktop browser: `http://127.0.0.1:8080/` or `http://automator.local:8080/` (both always available).

### 3.4 Hardware engineer

1. Validate mechanical alignment, endstops, wiring integrity.
2. Diagnose motion faults, thermal and electrical issues.
3. Maintain controller board/driver/gantry components.
4. Approve return to service after hardware incidents.

### 3.5 Escalation matrix

| Severity | Definition | Initial Responder | Escalate To | Target Response |
|---|---|---|---|---|
| Sev 1 | Safety risk, uncontrolled motion, smoke/odor, injury risk | Operator (stop immediately) | Hardware Engineer + System Administrator + Lab Lead | Immediate (0–5 min) |
| Sev 2 | System down, no imaging capability, physical E-stop recovery failure | Lab Technician | System Administrator, then Hardware Engineer | 15 min |
| Sev 3 | Partial degradation (camera, storage copy errors, UI instability) | Lab Technician | System Administrator | 1 hour |
| Sev 4 | Minor issue, cosmetic/UI text, non-blocking warning | Operator | Lab Technician | Next business day |

### 3.6 Technical support contacts

For technical issues with software, network configuration, code, or services, contact the TSL Bioinformatics team:

| Name | Email |
|---|---|
| Dan MacLean | <dan.maclean@tsl.ac.uk> |
| Rohan R | <phonics-tiffs1i@icloud.com> |

For IT or network-related issues (access permissions, IP address changes, printer registration), contact TSL IT via Christopher Rickett: <christopher.rickett@tsl.ac.uk>.

---

## 4. Safety guidelines

### 4.1 Electrical safety

1. Use only approved PSU and cable ratings.
2. Inspect power connectors before each day's first run.
3. Do not operate with exposed conductors.
4. De-energize before opening wiring enclosures.

### 4.2 Moving parts safety

1. Keep hands clear of gantry and rail while energized.
2. Never bypass guards/interlocks during operation.
3. Keep loose clothing, gloves, and cables away from moving axes.

### 4.3 Emergency stop procedure

1. Press the physical, hard-wired, latching AC-side emergency stop.
2. Confirm power is removed from all system supplies (reference: [`hardware/images/estop.jpg`](../hardware/images/estop.jpg)).
3. Confirm motion ceases.
4. Do not resume until root cause is identified.
5. Record incident in lab incident log.

### 4.4 Biohazard considerations

1. Follow local biosafety SOP for plate handling and disposal.
2. Use appropriate PPE for organism/risk category.
3. Decontaminate work surface after spills or contamination events.

### 4.5 Do not move conditions

Do not command motion when any of the following are true:

1. Door/interlock indicates open condition.
2. Any cable harness is loose or dragging in axis path.
3. Endstop behavior is uncertain.
4. Plate holders are unstable or protruding.
5. Camera module or gantry has visible mechanical damage.

### 4.6 Power isolation procedure

1. Stop the run with Pause/Start-Stop if safe; use the physical emergency stop if unsafe.
2. Turn off controller service if possible.
3. Switch off main power source.
4. Wait for all indicators/fans to stop.
5. Verify zero motion/power before touching internals.

### 4.7 Lid and vacuum safety

**Vacuum failure (lid drop risk):** If the vacuum pump fails or a hose disconnects during an imaging cycle, the suction cup will lose grip and the lid may fall onto the plate. Symptoms: audible change in pump tone, lid visibly drooping, imaging arm fails to lift. If observed, press the physical E-stop immediately. Do not attempt to catch the falling lid — it may be contaminated. Inspect the hose connections and pump before resuming.

**Servo failure (trapped lid risk):** If the servo motor stalls mid-rotation, the lid may be left at an intermediate angle. Do not command further motion — the servo may be mechanically bound and forcing motion could damage the linkage. Press the physical E-stop, manually rotate the lid to the fully open or closed position, and investigate the servo before resuming.

---

## 5. Installation procedure

### 5.1 Environmental requirements

1. Stable bench with low vibration.
2. Ambient temperature in equipment-approved range.
3. Adequate ventilation for fans/controllers.
4. Low-glare consistent lighting around imaging area.
5. Reliable Ethernet connectivity to required network resources.

### 5.2 Physical setup

1. Assemble/verify gantry frame and axis travel.
2. Mount camera module on vertical rail.
3. Verify Petri platform alignment and flatness.
4. Verify emergency stop hardware accessibility.
5. Verify cable routing does not intersect axis travel.

### 5.3 Power wiring

1. Connect PSU per approved wiring diagram.
2. Verify polarity and connector seating.
3. Verify fan power and airflow direction.
4. Verify Pi and controller board powered from approved rails.

### 5.4 Network configuration

The Raspberry Pi uses two physical interfaces: `eth0` (wired Ethernet) and `wlan0` (Wi-Fi). NetworkManager manages the following connection profiles:

| Profile name | Interface | Mode | Purpose |
|---|---|---|---|
| mac-direct-auto | eth0 | Static `192.168.50.2/24` | Direct MacBook access |
| IOT | wlan0 | DHCP | Wi-Fi for internet and updates (primary) |

Do not connect the Ethernet cable to the instrument or institute network. The previous instrument network configuration (`Instrument connection`, `10.0.8.72/24`) is archived in [instrument_network.md](instrument_network.md).

#### Ethernet direct MacBook design

`eth0` is used exclusively for direct MacBook access. An auto-switch script (`/usr/local/sbin/eth0-auto-switch.sh`) fires every 15 seconds via a systemd timer (`eth0-auto-switch.timer`) and on interface events via a NetworkManager dispatcher hook (`/etc/NetworkManager/dispatcher.d/90-eth0-auto-switch`). When a cable is detected, the script activates `mac-direct-auto` (`192.168.50.2/24`) and starts the DHCP service so the MacBook receives an address automatically.

Verify the timer is active after boot:

```bash
systemctl status eth0-auto-switch.timer
journalctl -t eth0-auto-switch -n 30 --no-pager
```

Full setup commands, script content, and service files are in [HandOver.md](HandOver.md) section 4.9.

#### NTP

The Pi synchronises time using `ntp.nbi.ac.uk` (NBI IT policy; do not use public NTP pools). Verify synchronisation:

```bash
chronyc tracking
chronyc sources
```

#### MacBook direct connection (normal user access)

Normal users access the web interface from a MacBook connected directly by Ethernet cable and USB-C to Ethernet adapter.

Setup steps:

1. Plug the USB-C to Ethernet adapter into the MacBook's USB-C port, then plug the Ethernet cable into the Ethernet port on the Automator.
2. Wait 15–20 seconds for the auto-switch to activate.
3. Confirm the MacBook USB-C Ethernet adapter is set to Using DHCP (System Settings → Network → USB Ethernet adapter → Details → TCP/IP → Configure IPv4: Using DHCP). No manual IP is needed.
4. Open a browser and go to `http://192.168.50.2:8080/`.

#### Admin access paths

From the Raspberry Pi desktop browser (connect display to Pi micro-HDMI, keyboard and mouse to Pi USB; exit kiosk with `Ctrl+Alt+A`):

- `http://127.0.0.1:8080/` — always available from the Pi desktop
- `http://automator.local:8080/` — mDNS; works from the Pi desktop browser and from a connected MacBook

Terminal, NetworkManager, service, and desktop settings access is reserved for technical/admin work.

#### Web UI login credentials

| Field | Value |
|:---|:---|
| Username | `admin` |
| Password | `tsl` |

#### Raspberry Pi desktop login credentials

Used to log in to the Pi desktop (different from the Automator web UI).

| Field | Value |
|:---|:---|
| Username | `pi` |
| Password | `rohan` |

### 5.5 Software installation (Raspberry Pi OS)

1. Clone repository to expected path:

```bash
cd /home/pi
git clone https://github.com/rotsl/Automator.git
cd /home/pi/Automator
```

2. Create and populate runtime environment:

```bash
python3 -m venv venv_clean
source venv_clean/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 5.6 Initial boot validation

1. Set runtime env vars:

   ```bash
   export AUTOMATOR_ADMIN_PASSWORD='strong-password'
   export AUTOMATOR_SESSION_SECRET='long-random-secret'
   ```

   - `AUTOMATOR_ADMIN_PASSWORD` is mandatory — controller startup fails if missing.
   - `AUTOMATOR_SESSION_SECRET` is strongly recommended for stable session signing.

2. Email notifications require no credentials — emails are sent from `no-reply-tslautomator@nbi.ac.uk` via `smtp.nbi.ac.uk` automatically. Only institute addresses (`@nbi.ac.uk` or `@tsl.ac.uk`) are supported. Verify reachability if needed: `nc -vz smtp.nbi.ac.uk 25`.

3. Start controller manually (for testing):

```bash
cd /home/pi/Automator/dev2
source /home/pi/Automator/venv_clean/bin/activate
python maincontroller.py
```

For production, the controller is managed as a systemd service (see §6).

4. Validate UI/API:

```bash
curl -u admin:<password> http://localhost:8080/system/version
curl -u admin:<password> http://localhost:8080/system/state
```

---

## 6. System startup procedure

### 6.0 Baseline PolicyKit and button service

PolicyKit rule:

1. File: `/etc/polkit-1/rules.d/10-moonraker.rules`
2. Must allow user `pi` for:
   - `org.freedesktop.systemd1.manage-units`
   - `org.freedesktop.login1.power-off`
   - `org.freedesktop.login1.power-off-multiple-sessions`
   - `org.freedesktop.login1.reboot`
   - `org.freedesktop.login1.reboot-multiple-sessions`

Button listener service baseline (`/etc/systemd/system/automator-buttons.service`):

```ini
[Unit]
Description=Automator GPIO Button Listener
After=network.target moonraker.service klipper.service
Requires=moonraker.service klipper.service

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/Automator/dev2
Environment="AUTOMATOR_ADMIN_PASSWORD=****"
ExecStartPre=/bin/sleep 5
ExecStart=/home/pi/Automator/venv_clean/bin/python /home/pi/Automator/dev2/button_listener.py
Restart=always
RestartSec=2
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### 6.1 Pre-checks

| Step | Check Item | Validation Method | Expected Result | Status |
|---|---|---|---|---|
| 1 | Physical obstructions on stage/gantry | Visual inspection | No obstructions in travel path | ☐ Pass / ☐ Fail |
| 2 | Door/interlock safety state | UI dashboard or door sensor | Door closed, interlock engaged | ☐ Pass / ☐ Fail |
| 3 | Cameras connected | `v4l2-ctl --list-devices` and Pi camera test | USB camera listed, Pi camera accessible | ☐ Pass / ☐ Fail |
| 4 | Services running | `systemctl status klipper moonraker automator-controller.service automator-buttons.service` | All services show `active (running)` | ☐ Pass / ☐ Fail |

### 6.2 Power-on sequence

| Step | Action | Validation Method | Expected Result | Status |
|---|---|---|---|---|
| 1 | Energize PSU/controller hardware | Check LED indicators on PSU and controller board | All power indicators illuminate | ☐ Pass / ☐ Fail |
| 2 | Boot Raspberry Pi | Wait for boot completion (30–60s) | Pi responds to network ping | ☐ Pass / ☐ Fail |
| 3 | Start automator-controller.service | `sudo systemctl restart automator-controller.service` | Service enters `active (running)` state | ☐ Pass / ☐ Fail |
| 4 | Verify service status | `sudo systemctl status automator-controller.service automator-buttons.service` | Both services show `active (running)` | ☐ Pass / ☐ Fail |

### 6.3 Network verification

| Check | Command | Validation Criteria | Expected Result | Status |
|---|---|---|---|---|
| IP address assigned | `hostname -I` | IP in lab network range | IP displays (e.g., `192.168.x.x`) | ☐ Pass / ☐ Fail |
| Default route configured | `ip route` | Default gateway reachable | Gateway IP listed as default route | ☐ Pass / ☐ Fail |
| Gateway connectivity | `ping -c 3 <gateway-ip>` | All packets received, no loss | 3/3 packets received, 0% loss | ☐ Pass / ☐ Fail |
| Local storage accessible | `ls -la /home/pi/Automator/data/` | Directory exists and is readable | Directory listing shows contents | ☐ Pass / ☐ Fail |

### 6.4 UI access verification

| Step | Action | Validation Method | Expected Result | Status |
|---|---|---|---|---|
| 1 | Open normal-user controller UI (MacBook) | Connect MacBook directly via USB-C to Ethernet adapter (on Using DHCP), wait 15–20s for `mac-direct-auto` and DHCP assignment, navigate to `http://192.168.50.2:8080/` or `http://automator.local:8080/` | Auth prompt appears | ☐ Pass / ☐ Fail |
| 1a | Open admin Pi-local UI | Connect display to Pi micro-HDMI, keyboard/mouse to Pi USB; exit kiosk with `Ctrl+Alt+A`; open Pi desktop browser at `http://127.0.0.1:8080/` or `http://automator.local:8080/` | Auth prompt appears | ☐ Pass / ☐ Fail |
| 2 | Authenticate as admin | Enter username `admin` and password | Login succeeds, redirects to main page | ☐ Pass / ☐ Fail |
| 3 | Verify dashboard loads | Dashboard renders without errors | All UI elements visible (scan, config, start buttons) | ☐ Pass / ☐ Fail |
| 4 | Verify API responsiveness | `curl -u admin:<pw> http://localhost:8080/system/state` | Valid JSON state response (200 OK) | ☐ Pass / ☐ Fail |
| 5 | Verify QR PDF download | Open `/`, add a QR code, click "Download PDF Sheet" | Browser downloads an A4 PDF; no printer/CUPS dependency | ☐ Pass / ☐ Fail |

### 6.5 Motor initialization

| Check | Validation Method | Acceptable Result | Failure Indicator | Status |
|---|---|---|---|---|
| Safe-home completed | Inspect controller logs or UI log panel | "safe_home success" or G28 completion message present | Timeout, axis error, or endstop not triggered | ☐ Pass / ☐ Fail |
| Klipper motor status | `journalctl -u klipper -n 50 \| grep -i error` | No "error" or "fail" messages in last startup | Any motor/axis/driver errors reported | ☐ Pass / ☐ Fail |
| Z-axis ready height | Verify gantry position visually | Z at ready height (~50 mm) | Z not at expected height or drifting | ☐ Pass / ☐ Fail |
| No unintended movement | Observe gantry for 10s at idle | Gantry remains motionless | Any creep, vibration, or unexpected motion | ☐ Pass / ☐ Fail |

### 6.6 Camera validation

| Camera | Test Method | Expected Result | Failure Mode | Status |
|---|---|---|---|---|
| USB camera detection | Run `/detect` (Generate Preview Image) in UI; use **↻** beside the button to reload the page first if needed | Scan completes, plate count > 0 | "No plates detected" or scan timeout | ☐ Pass / ☐ Fail |
| USB camera image quality | Inspect generated preview image | Image is sharp, well-lit, QR codes readable | Blurry, dark, or unreadable image | ☐ Pass / ☐ Fail |
| Pi camera capture | Run test capture via `dev2/qrtest.py` | Image file created in expected path | Capture fails or corrupted file | ☐ Pass / ☐ Fail |
| Pi camera focus | Inspect captured image on reference plate | Colony edges sharp, QR code readable | Out-of-focus or blurry capture | ☐ Pass / ☐ Fail |

> **Diagnostics tools** (`maindiagnostics.py`, `main_mjpeg_server.py`) are internal-only and not required for production operation. See `documentation/diagnosticsserver.md` for their setup and use.

---

## 7. Calibration procedure

### 7.1 Axis homing

| Step | Action | Validation Method | Pass Criteria | Failure Action | Status |
| --- | --- | --- | --- | --- | --- |
| 1 | Clear workspace | Visual inspection | No obstructions in gantry path | Remove obstacles, recheck | ☐ Pass / ☐ Fail |
| 2 | Trigger safe home | Click "Start" in UI or run `/system/start` | Motion commands execute | Check Klipper logs, restart service | ☐ Pass / ☐ Fail |
| 3 | Verify homing completion | `grep "safe_home" /home/pi/Automator/raw/controller.log` | Message "safe_home success" present, Z at ready height | Retry homing; escalate if endstop fault | ☐ Pass / ☐ Fail |
| 4 | Verify no errors | Check for axis/driver errors in Klipper | No error messages in logs | Inspect wiring, test endstops, escalate | ☐ Pass / ☐ Fail |

### 7.2 Workspace scanning

| Step | Action | Validation Method | Pass Criteria | Failure Action | Status |
| --- | --- | --- | --- | --- | --- |
| 1 | Prepare test plates | Place QR-labeled plates at known positions | Plates physically positioned and labeled | Verify labels are clear and correctly generated | ☐ Pass / ☐ Fail |
| 2 | Trigger scan | Click "Generate Preview Image" in UI | Scan initiates without UI errors | Check controller logs for scan start | ☐ Pass / ☐ Fail |
| 3 | Wait for completion | Monitor UI "Wait" status | Status changes to "Now tick plates to be included" | Check logs for timeout; verify camera is connected | ☐ Pass / ☐ Fail |
| 4 | Verify plate count | Count displayed plate blocks in UI | Plate count matches expected number | Re-run scan with different lighting or plate positions | ☐ Pass / ☐ Fail |

### 7.3 Plate detection validation

| Check | Validation Method | Pass Criteria | Failure Action | Status |
|---|---|---|---|---|
| Plate ID stability | Re-run scan 3 times; compare plate IDs | IDs identical across all 3 scans | Adjust lighting or plate contrast | ☐ Pass / ☐ Fail |
| Position mapping accuracy | Compare detected positions to physical layout | Detected coordinates match physical positions | Check USB camera calibration, re-run | ☐ Pass / ☐ Fail |
| QR code readability | Inspect preview image for QR visibility | All QR codes visible and readable | Re-position plates, improve lighting, check focus | ☐ Pass / ☐ Fail |
| Unresolved plate handling | Place a plate with a damaged/obscured QR label; run scan | Orange bounding box appears; plate appears in Unresolved panel | No detection at all | ☐ Pass / ☐ Fail |
| Glare/shadow detection | Review preview image for hot spots or dark regions | Even illumination across all plates | Adjust lighting angles, reposition light sources | ☐ Pass / ☐ Fail |

### 7.4 Camera focus calibration

| Step | Action | Validation Method | Pass Criteria | Failure Action | Status |
| --- | --- | --- | --- | --- | --- |
| 1 | Position reference plate | Place reference plate in center of workspace | Plate stationary and visible | Secure plate, check for reflections | ☐ Pass / ☐ Fail |
| 2 | Capture test image | Run single capture via UI or `qrtest.py` | Image file written to `/home/pi/Automator/data/` | Check file permissions, validate camera write path | ☐ Pass / ☐ Fail |
| 3 | Assess sharpness | Inspect image at 100% zoom | Edges sharp, no blur at magnification | Adjust camera focus ring slightly | ☐ Pass / ☐ Fail |
| 4 | Verify QR readability | Attempt to read QR code in image | QR code legible and decodable | Improve focus, increase lighting | ☐ Pass / ☐ Fail |
| 5 | Fine-tune focus (if needed) | Adjust camera mount or focus ring incrementally | Repeat steps 2–4 until acceptable | Document final focus setting for reference | ☐ Pass / ☐ Fail |

### 7.5 Lighting calibration

| Check | Validation Method | Pass Criteria | Failure Action | Status |
|---|---|---|---|---|
| Hotspot/saturation check | Inspect test image for overexposed areas | No blown highlights | Reposition/adjust light intensity, diffuse source | ☐ Pass / ☐ Fail |
| Illumination uniformity | Analyze brightness across workspace regions | Brightness variation < 15% across quadrants | Reposition light sources, use diffusers | ☐ Pass / ☐ Fail |
| Shadow detection | Inspect for dark regions or unlit areas | No dark shadows or unlit corners | Adjust light angle, add fill light | ☐ Pass / ☐ Fail |
| Repeatability (3 captures) | Capture same plate 3 times without moving lights | Lighting consistent across captures | Check for light source drift, secure fixtures | ☐ Pass / ☐ Fail |
| Color accuracy (optional) | Compare captures to known reference | Color representation consistent | Adjust white balance, verify camera calibration | ☐ Pass / ☐ Fail |

### 7.6 Calibration validation checklist

| Task | Validation Criteria | Test Method | Pass/Fail | Notes | Signed Off By |
| --- | --- | --- | --- | --- | --- |
| Homing repeatable and accurate | Z reaches ready height within ±2 mm on 5 consecutive runs | Run safe_home 5 times, measure final Z | ☐ | Final position: _____ mm | |
| Scan detects all expected plates | 100% of physically present plates detected | Place 4 test plates, run scan 3 times | ☐ | Detection rate: _____ % | |
| No false-positive plate mapping | No spurious detections on empty workspace | Run scan on empty stage | ☐ | Count: _____ false positives | |
| Capture sharpness acceptable | Colony edges sharp at 1:1 zoom, QR codes readable | Capture reference plate 3 times | ☐ | Focus setting: _____ | |
| Lighting uniform and stable | < 15% brightness variation across quadrants | Analyze 3 captures for hotspots/shadows | ☐ | Min/max brightness: _____ / _____ | |
| Image file creation | Images always written to local path | Run 5-image test capture | ☐ | Local OK: ☐ | |
| Metadata accuracy | Filenames include timestamp and tag (if set) | Check filename patterns in saved images | ☐ | Example filename: _____ | |
| Temperature nominal | CPU temp < 70°C, motor temps normal | Run 10-min calibration cycle | ☐ | Temps: CPU _____ °C | |

Calibration approved on: __________ By: __________ Next review due: __________

---

## 8. Imaging workflow operation

### 8.0 UI accessibility controls

1. The top-right control strip includes:
   - `AAA` button: cycles text size (`normal`, `large`, `extra large`).
   - `♿️` button: toggles color-blind text mode.
2. These controls are UI-only and do not alter imaging schedule, motion, or capture logic.

### 8.0.1 Optional experiment tag

1. The operator may enter an experiment tag on the main imaging page.
2. Tag entry is capped at 15 characters.
3. If a tag is supplied, the controller appends a cleaned version to image and folder names as `_tag-<clean_tag>`.

### 8.1 Generate preview image

| Step | Action | Validation Method | Expected Result | Status |
|---|---|---|---|---|
| 1 | Place labelled dishes in workspace | Visual inspection | Dishes are 90–100 mm round Petri dishes/plates, placed flat (not stacked) on green sticker positions, max 6 dishes, QR codes visible | ☐ Pass / ☐ Fail |
| 2 | Click "Generate Preview Image" (↻ beside it reloads the page without re-scanning) | Monitor UI status | `/detect` endpoint called | ☐ Pass / ☐ Fail |
| 3 | Wait for scan completion | Watch UI helper text and log output | Text changes to "Now tick plates to be included" | ☐ Pass / ☐ Fail |
| 4 | Verify plate detection | Count plate blocks in UI | Plate count matches physical count | ☐ Pass / ☐ Fail |
| 5 | Verify preview image quality | Inspect generated preview image | QR codes readable, lighting uniform | ☐ Pass / ☐ Fail |

### 8.1.1 Unresolved plate identification

Applies when the workspace scan detects a plate shape but cannot read the QR code.

| Step | Action | Validation Method | Expected Result | Status |
|---|---|---|---|---|
| 1 | Observe orange bounding boxes in preview image | Inspect preview | Boxes labelled "No QR (QR unreadable)" visible for affected plates | ☐ Pass / ☐ Fail |
| 2 | Review Unresolved plates panel | Check panel below scan preview | Each unresolved plate shows Identify and Dismiss buttons | ☐ Pass / ☐ Fail |
| 3 | Identify each unresolved plate | Click Identify, enter QR data string, click Save | Plate moves from unresolved list to main plate list with correct description | ☐ Pass / ☐ Fail |
| 4 | Or dismiss unresolved plate | Click Dismiss | Plate removed from unresolved list; not shown in subsequent scans | ☐ Pass / ☐ Fail |
| 5 | Proceed with configuration | Identified plates appear in per-plate config panel | Identified plates configurable like normally detected plates | ☐ Pass / ☐ Fail |

### 8.2 Select plates

| Step | Action | Validation Method | Expected Result | Status |
|---|---|---|---|---|
| 1 | Review plate list in UI | Verify all detected plates are displayed | Plate blocks correspond to physical layout | ☐ Pass / ☐ Fail |
| 2 | Select target plates | Check desired plates, uncheck unwanted ones | Checkboxes reflect selection without errors | ☐ Pass / ☐ Fail |
| 3 | Verify selection count | Count checked boxes | Selected count matches intended run scope | ☐ Pass / ☐ Fail |

### 8.3 Configure imaging interval

| Step | Action | Validation Method | Expected Result | Status |
|---|---|---|---|---|
| 1 | Enter interval for each plate | Input field accepts numeric values | Value entered without error (e.g., "5" for 5 min) | ☐ Pass / ☐ Fail |
| 2 | Verify UI computes duration | Check if UI shows estimated runtime | Estimated end time appears | ☐ Pass / ☐ Fail |
| 3 | Confirm value storage | Check config in UI or backend logs | `every_min` field stored correctly | ☐ Pass / ☐ Fail |

### 8.4 Set runtime duration

| Step | Action | Validation Method | Expected Result | Status |
|---|---|---|---|---|
| 1 | Enter runtime hours for each plate | Input field accepts numeric values | Value accepted without error | ☐ Pass / ☐ Fail |
| 2 | Verify UI computes duration | Check if UI shows estimated end time | Estimated end time appears | ☐ Pass / ☐ Fail |
| 3 | Verify computed schedule | Check scheduler state in logs | Runtime correctly parsed, total captures calculated | ☐ Pass / ☐ Fail |

### 8.5 Send run details to Automator Robot

| Step | Action | Validation Method | Expected Result | Status |
|---|---|---|---|---|
| 1 | Click "Send Run Details to Automator Robot" button | Monitor UI and logs | `/config` endpoint called | ☐ Pass / ☐ Fail |
| 2 | Verify config saved | Check log output in UI | Log entry: "config saved" or "schedule rebuilt" | ☐ Pass / ☐ Fail |
| 3 | Confirm no errors | Check for validation or save errors | No error dialog, status remains "ready" | ☐ Pass / ☐ Fail |

### 8.6 Run imaging

| Step | Action | Validation Method | Expected Result | Status |
|---|---|---|---|---|
| 1 | Click "Run Imaging" button | Monitor UI status | `/system/start` called, UI shows "Running" | ☐ Pass / ☐ Fail |
| 2 | Verify motion begins | Observe gantry movement | Gantry moves to first plate position within 5s | ☐ Pass / ☐ Fail |
| 3 | Confirm first capture | Monitor log and file output | First image file created in `/home/pi/Automator/data/` | ☐ Pass / ☐ Fail |
| 4 | Verify cycle loop | Monitor repeated motion and captures | Captures continue at configured interval | ☐ Pass / ☐ Fail |

### 8.7 Pause / resume / start-stop usage

#### Pause/resume button

| Scenario | Action | Validation Method | Expected Result | Status |
|---|---|---|---|---|
| Pause during imaging | Click Pause button during active run | Confirm dialog appears | Motion stops at safe point within 2s | ☐ Pass / ☐ Fail |
| State preservation | Monitor backend state file | Check `controller_state.json` | Runtime state (plates, schedule, position) saved | ☐ Pass / ☐ Fail |
| LED off during pause | Observe LED | LED turns off on pause | Visual confirmation | ☐ Pass / ☐ Fail |
| Vacuum release | Check vacuum/hold state | Inspect logs or physical feedback | Vacuum released, hold disengaged | ☐ Pass / ☐ Fail |
| Resume from pause | Click Resume button | Confirm dialog: "Resuming from remaining time..." | Run continues from saved position with exact schedule | ☐ Pass / ☐ Fail |
| Resume LED restore | Monitor LED during resume | LED restores to pre-pause state | LED ON if it was on before pause | ☐ Pass / ☐ Fail |
| Pause when idle | Click Pause outside imaging | Monitor backend response | Request ignored (`imaging_inactive` logged) | ☐ Pass / ☐ Fail |

#### Start/stop button

| Scenario | Action | Validation Method | Expected Result | Status |
|---|---|---|---|---|
| Stop during imaging | Click Start/Stop during active run | Confirm dialog: "Are you sure you want to Stop?" | Run terminates, system readies for new cycle | ☐ Pass / ☐ Fail |
| Safe home execution | Monitor motion after stop | Inspect logs for G28 command | Safe-home completes, Z raised to 50 | ☐ Pass / ☐ Fail |
| Start when idle | Click Start/Stop at idle | Confirm dialog: "Starting New Cycle..." | Safe-home executes, Z raised to ready height | ☐ Pass / ☐ Fail |
| Cancel during prep | Click Start/Stop during launch preparation | Monitor for cancellation signal | Imaging launch cancelled before thread starts | ☐ Pass / ☐ Fail |

### 8.8 Physical emergency stop usage

| Step | Action | Validation Method | Expected Result | Status |
|---|---|---|---|---|
| 1 | Assess safety condition | Determine if immediate stop needed | Uncontrolled motion or unsafe conditions present | ☐ Pass / ☐ Fail |
| 2 | Activate emergency stop | Press the physical AC-side latching emergency stop | Power is cut to all system supplies | ☐ Pass / ☐ Fail |
| 3 | Verify motion halts | Observe gantry | Motion ceases immediately after power isolation | ☐ Pass / ☐ Fail |
| 4 | Record incident | Document emergency activation | Incident log entry created with timestamp | ☐ Pass / ☐ Fail |
| 5 | Reset before next run | Resolve root cause, release physical E-stop, restart service if needed | System ready for a controlled test cycle | ☐ Pass / ☐ Fail |

### 8.9 Pulse behavior in workflow

1. `detect` stage can send a dedicated pulse (`/detect?pulse=1`) before USB scan, then waits 2s.
2. `config` stage can send a dedicated pulse (`/config?pulse=1`) after run details are submitted.
3. LED ON sends a pulse and arms the OFF pulse; LED OFF sends a pulse only if armed by a prior LED ON.

### 8.10 Verify images saved correctly

| Check | Validation Method | Expected Result | Failure Signal | Status |
|---|---|---|---|---|
| Local file creation | `ls -la /home/pi/Automator/data/<run-folder>/` | Image files present with timestamps | Directory empty or inaccessible | ☐ Pass / ☐ Fail |
| Naming pattern | Inspect filenames | Format includes date, plate ID, and tag | Malformed names or missing components | ☐ Pass / ☐ Fail |
| File integrity | `file <image-path>` and visual inspection | All files valid JPEG, images viewable | Corrupted/unreadable files | ☐ Pass / ☐ Fail |
| Timestamp accuracy | Compare file mtime with capture time in logs | File modification time matches log timestamp ±1s | Timestamps off by > 5s | ☐ Pass / ☐ Fail |
| Metadata correctness | Inspect image EXIF (if available) | Expected plate ID, run date, tag in metadata | Missing or incorrect metadata | ☐ Pass / ☐ Fail |
| UI file browser (LAN) | Click "Preview Images" button | File browser loads, shows run folder and images | UI error, files not visible | ☐ Pass / ☐ Fail |
| Cloud routes absent | Visit `/cloud`, `/cloud/main`, `/cloud/login`, `/cloud/captures/` | All return 404 or connection refused; `/main` still loads correctly | Any `/cloud` path serves content | ☐ Pass / ☐ Fail |

The gallery page includes a **← Back to Automator** button in the header (beside Refresh) to navigate back to `/main`.

---

## 9. Monitoring and health checks

### 9.1 Disk space thresholds

| Threshold Level | Free Space | Action Required | Test Command | Pass Criteria | Current Status | Last Checked |
| --- | --- | --- | --- | --- | --- | --- |
| Normal | > 20% | Continue operations | `curl -u admin:<pw> http://localhost:8080/system/disk` | Free space > 20% | _____ % | _____ |
| Warning | 10–20% | Plan cleanup/backup within 24h | `df -h /home/pi/Automator/data` | Alert issued, no ops blocked | _____ % | _____ |
| Critical | 5–10% | Pause new runs; cleanup immediately | `df -h /home/pi/Automator/data` | Cleanup initiated | _____ % | _____ |
| Stop | < 5% | Do not start imaging | Check both paths | Imaging blocked, escalate | _____ % | _____ |

Automated cleanup: `cleanup-jpgs.service` runs every 3 days (via `cleanup-jpgs.timer`) and keeps `/home/pi/Automator/data` under 5 GiB by deleting JPG captures and dynamic run folders older than 21 days. An emergency pass trims items older than 14 days if the folder still exceeds 5 GiB after the first pass. See [JPG_Cleanup_Workflow.md](JPG_Cleanup_Workflow.md) for full rules and manual commands.

### 9.2 CPU temperature

| Level | Threshold | Action | Test Command | Expected Result | Current Temp | Last Checked |
| --- | --- | --- | --- | --- | --- | --- |
| Normal | < 75°C | Continue normal operation | `vcgencmd measure_temp` | "temp=__°C" | _____ °C | _____ |
| Warning | 75–80°C | Check airflow/fans; reduce load | Inspect fan operation, clear vents | Fans running, temp stabilizes | _____ °C | _____ |
| Critical | > 80°C | Stop imaging; inspect cooling | Reduce workload, check thermal contact | Temp drops below 75°C | _____ °C | _____ |

### 9.3 Network status

| Check | Command | Expected Result | Acceptable Value | Current Status | Last Checked |
| --- | --- | --- | --- | --- | --- |
| IP address assigned | `ip a` | IP listed in lab network range | Non-loopback, RUNNING state | _____ | _____ |
| Default route | `ip route` | Default gateway present | Route via eth0 or wlan0 | _____ | _____ |
| Gateway connectivity | `ping -c 3 <gateway-ip>` | 3/3 packets received, 0% loss | < 5% packet loss acceptable | _____ % loss | _____ |
| Storage host reachable | `ping -c 3 <storage-host>` | 3/3 packets received | < 5% loss, < 20 ms acceptable | _____ ms | _____ |
| DNS resolution | `nslookup github.com 8.8.8.8` | IP address resolved successfully | DNS responds with valid IP | _____ | _____ |

### 9.4 Motor error detection

| Check | Command | Pass Criteria | Failure Signal | Status | Last Checked |
| --- | --- | --- | --- | --- | --- |
| Klipper service state | `sudo systemctl status klipper` | "active (running)" | "inactive" or "failed" | ☐ Pass / ☐ Fail | _____ |
| Recent Klipper logs | `journalctl -u klipper -n 200 \| grep -i error` | No error/fail messages | Any "ERROR", "FAIL", stepper error | ☐ Pass / ☐ Fail | _____ |
| Moonraker state | `sudo systemctl status moonraker` | "active (running)" | "inactive" or "failed" | ☐ Pass / ☐ Fail | _____ |
| Motion command success | Run test motion via UI or `/system/start` | Motion completes without error | Timeout, axis error, or driver fault | ☐ Pass / ☐ Fail | _____ |
| Homing stability | Run safe_home 3 consecutive times | All 3 complete with same final position (±2 mm) | Any homing failure or position variance > 2 mm | ☐ Pass / ☐ Fail | _____ |

### 9.5 Log inspection

| Log Source | Command | Expected Content | Red Flags | Last Checked | Reviewed By |
| --- | --- | --- | --- | --- | --- |
| Controller log | `tail -n 200 /home/pi/Automator/raw/controller.log` | Timestamp entries with state changes, motion events | "ERROR", "exception", repeated motion failures | _____ | |
| UI system logs | `curl -u admin:<pw> http://localhost:8080/system/logs` | Chronological events, capture completions | Authentication failures, missing endpoints | _____ | |
| Service journal | `journalctl -u automator-controller.service -n 200 --no-pager` | Service start/stop, no crash dumps | "segfault", "killed", "core dumped" | _____ | |
| Klipper logs | `journalctl -u klipper -n 100 --no-pager` | Initialization and command execution | "error", "shutdown", "restart requested" | _____ | |
| Moonraker logs | `journalctl -u moonraker -n 100 --no-pager` | Socket listening, RPC activity | "error", "failed", "exception" | _____ | |

### 9.6 Alert conditions

Trigger operational alert (Sev 3 or above per Section 3.5) when any of the following occur:

| Alert Condition | Detection Method | Severity | Action | Owner | Date Triggered | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Repeated camera capture failures | > 2 consecutive failures in 1 session | Sev 3 | Check camera connection, focus, restart service | Lab Technician | _____ | Failure count: _____ |
| Repeated plate detection failures | 0 plates in known-good setup 2+ times | Sev 3 | Inspect lighting, camera cleanliness | Lab Technician | _____ | Retry count: _____ |
| Physical emergency stop activations | > 1 per week during normal ops | Sev 2 | Review incident logs, assess safety controls | Hardware Engineer | _____ | Incident count (7d): _____ |
| Storage critical threshold | Free space < 5% on either path | Sev 2 | Stop new runs, initiate cleanup immediately | System Administrator | _____ | Free space: _____ % |
| Service restart loop | > 3 restarts in 1 hour | Sev 2 | Capture error logs, escalate | System Administrator | _____ | Restart count (1h): _____ |

---

## 10. Backup and data management

### 10.1 Image storage structure

Images are written to `/home/pi/Automator/data/captures/` (local storage only).

To browse images from a browser, normal users use the local UI file browser while connected through direct MacBook Ethernet. Admins can also use the Pi desktop browser during maintenance.

To export images to a USB drive, plug a drive into the Pi. The USB export system automatically copies the local Automator image/data folder to `/images/` on the drive, then unmounts it. For headless operator use, wait 2-3 minutes before unplugging. If the expected images are not present on the USB drive, repeat the export with a known-good exFAT/FAT32/NTFS/ext4 USB drive and inspect the export service logs before deleting any local data.

Common folder pattern: `DDMMM_STRAIN_MEDIA_COND_tag-<clean_tag>`

### 10.2 Backup procedure

Use USB export to copy all image data to an external drive, or rsync to a separate destination of your choice. Example to a mounted USB drive:

```bash
rsync -avh /home/pi/Automator/data/ /media/pi/<drive>/automator_backup/
```

Log/state backup:

```bash
tar -czf /media/pi/<drive>/raw_$(date +%F).tgz /home/pi/Automator/raw
```

### 10.3 Retention policy example

1. Hot data on primary storage: 90 days.
2. Compressed archive: 12 months.
3. Critical run artifacts/logs retained per project compliance policy.

### 10.4 Disk cleanup procedure

1. Confirm backups completed and verified.
2. Remove only aged/approved datasets.
3. Never delete a current active run directory.

```bash
find /home/pi/Automator/data -maxdepth 1 -type d -mtime +120 -print
# Review output, then delete approved paths only
```

### 10.5 Automated cache cleanup

A root cron job runs `/home/pi/clear_cache.sh` every 2 days at midnight. The script clears APT package cache, thumbnail cache, user cache, and Python `__pycache__`. It checks the Automator imaging state before running and skips cleanup if imaging is active.

See [clear_cache_cron_with_imaging_guard.md](clear_cache_cron_with_imaging_guard.md) for setup, verification, the environment file for the admin password, and expected log output.

Check the log:

```bash
sudo tail -n 20 /var/log/clear_cache.log
```

---

## 11. Failure scenarios and troubleshooting

### 11.1 Troubleshooting table

| Symptom | Likely Cause | Diagnostic Steps | Resolution Steps | Verification | Escalation |
| --- | --- | --- | --- | --- | --- |
| UI not loading | Controller service down, auth misconfig, network issue | `systemctl status automator-controller.service`; `curl -u admin:<pw> http://localhost:8080/system/version` | Restart: `sudo systemctl restart automator-controller.service`; verify `AUTOMATOR_ADMIN_PASSWORD`; verify IP with `hostname -I` | `curl http://localhost:8080/` returns 200; UI loads; auth succeeds | Sev 2 if unresolved in 15 min |
| Motors not moving | Klipper down, macro mismatch, wiring/driver fault | `systemctl status klipper`; controller logs for movement errors; `journalctl -u klipper -n 50` | Web UI first: click **Troubleshooting** in the footer → "Restart Klipper". Terminal fallback: `sudo systemctl restart klipper`; validate `printer.cfg` macros and pin definitions; inspect wiring | Run test motion; gantry moves smoothly; no errors in logs | Sev 2 if unsafe movement or no recovery |
| Camera not detected | USB mapping failure or Pi camera stack issue | `v4l2-ctl --list-devices`; `python /home/pi/Automator/dev2/qrtest.py`; inspect `controller.log` for capture errors | Reconnect USB camera to different port; restart automator service: `sudo systemctl restart automator-controller.service` | `/detect` scan finds plates; test capture succeeds; image file created | Sev 3 if persistent after 3 reconnection attempts |
| Images corrupted | Storage medium issue, capture write interruption | Inspect sample images (`file <image>`); check logs for I/O errors; `dmesg \| grep -i error` | Replace failing storage media; validate disk health; rerun capture validation; backup immediately | All test images valid; file sizes consistent; no I/O errors in `dmesg` | Sev 2 if data integrity risk detected |
| Disk full | Retention/backup gap | `df -h /home/pi/Automator/data`; check `/system/disk` | Stop new runs; backup recent data; remove aged datasets (> 90 days) | Free space > 20%; `/system/disk` reports green; new test capture succeeds | Sev 2 at < 5% free |
| System frozen | Process deadlock, hardware comm stall | `curl -u admin:<pw> http://localhost:8080/system/state`; `journalctl -u automator-controller.service -n 50`; `top` | Safe restart: `sudo systemctl restart automator-controller.service`; if unresponsive, hard cycle (Section 4.6) | UI responds; logs update normally; test motion executes | Sev 2 if repeated within 24h |
| Overheating | Fan failure, blocked airflow, ambient conditions | `vcgencmd measure_temp` at idle and load; inspect fan operation; check vents | Clean vents/filters; check thermal paste contact; add external cooling | `vcgencmd measure_temp` < 75°C idle, < 80°C under load | Sev 1 if thermal hazard persists; Sev 2 if consistent > 80°C |
| Network unreachable | Ethernet path loss, switch/gateway issues | `ip a`; `ip route`; `ping -c 5 <gateway-ip>` | Restore Ethernet when possible; restart networking: `sudo systemctl restart networking` | Network restored; MacBook/kiosk access resumes | Sev 3 only if local captures also failing |
| Lid drops / suction lost during imaging | Vacuum pump failure, hose disconnection, or pump underpowered | Listen for pump tone change; inspect vacuum hose connections; check `SUCK_HOLD` macro logs | Press physical E-stop; inspect hose and pump; reconnect or replace hose; restart run | Lid lifts and holds for ≥ 5 s without drooping | Sev 1 if lid contacts sample/culture |
| Lid stuck mid-rotate or does not open/close | Servo motor stall, mechanical obstruction, or power fault | Observe servo movement in manual test via Klipper console: `ROTATE ANGLE=0` / `ROTATE ANGLE=90`; listen for clicking | Press physical E-stop; manually rotate lid clear; inspect servo linkage and power connector; replace servo if no movement under manual command | Servo completes full rotation (0°→90°→0°) without clicking or binding | Sev 2 if obstruction cannot be cleared manually |

---

## 12. Recovery procedures

### 12.1 Safe restart

| Step | Action | Validation Method | Expected Result | Status |
|---|---|---|---|---|
| 1 | Assess safety | Determine if hazard present | System deemed safe to proceed | ☐ Pass / ☐ Fail |
| 2 | Use physical emergency stop if unsafe | Press the physical AC-side E-stop if needed | Power isolated, system safe | ☐ Pass / ☐ Fail |
| 3 | Resolve immediate hazard | Remove obstructions, cool system, etc. | Hazard condition cleared | ☐ Pass / ☐ Fail |
| 4 | Restart service | `sudo systemctl restart automator-controller.service` | Service transitions to `active (running)` | ☐ Pass / ☐ Fail |
| 5 | Verify service health | `sudo systemctl status automator-controller.service` | Status shows "active (running)" | ☐ Pass / ☐ Fail |
| 6 | Test API | `curl -u admin:<pw> http://localhost:8080/system/state` | JSON state response (HTTP 200) | ☐ Pass / ☐ Fail |
| 7 | Test UI | Open `http://<pi-ip>:8080/` in browser | Dashboard loads, no errors | ☐ Pass / ☐ Fail |
| 8 | Resume operations | Return to normal workflow | System ready for scan/config/start | ☐ Pass / ☐ Fail |

### 12.2 Soft reboot (OS)

| Step | Action | Validation Method | Expected Result | Status |
|---|---|---|---|---|
| 1 | Stop active imaging | Click Pause/Stop or wait for cycle completion | No imaging in progress | ☐ Pass / ☐ Fail |
| 2 | Issue reboot command | `sudo reboot` | System initiates graceful shutdown | ☐ Pass / ☐ Fail |
| 3 | Wait for reboot | Monitor for system to power cycle (2–3 min) | System boots and comes online | ☐ Pass / ☐ Fail |
| 4 | Verify network | `hostname -I`, `systemctl status eth0-auto-switch.timer`, and `journalctl -t eth0-auto-switch -n 30` | IP assigned; auto-switch timer active; expected profile selected | ☐ Pass / ☐ Fail |
| 5 | Verify services | `systemctl status automator-controller.service klipper moonraker` | All services "active (running)" | ☐ Pass / ☐ Fail |
| 6 | Verify cameras | Run test scan or `v4l2-ctl --list-devices` | Cameras detected and functional | ☐ Pass / ☐ Fail |
| 7 | Re-run workflow | Execute scan → config → start | System proceeds normally | ☐ Pass / ☐ Fail |

### 12.3 Hard power cycle

Use only if OS is unresponsive:

| Step | Action | Validation Method | Expected Result | Status |
|---|---|---|---|---|
| 1 | Confirm unresponsiveness | API ping fails, system unresponsive | No response after 2+ minutes | ☐ Pass / ☐ Fail |
| 2 | Isolate power safely | Follow Section 4.6 | Power isolated, all indicators off | ☐ Pass / ☐ Fail |
| 3 | Wait for discharge | Wait minimum 20 seconds | All capacitors discharged | ☐ Pass / ☐ Fail |
| 4 | Re-energize | Apply power in normal sequence | System powers on, boot sequence starts | ☐ Pass / ☐ Fail |
| 5 | Wait for boot | Monitor for full startup (30–60s) | Services auto-start, system online | ☐ Pass / ☐ Fail |
| 6 | Verify connectivity | `hostname -I` and `curl /system/version` | IP assigned, API responds | ☐ Pass / ☐ Fail |
| 7 | Run Section 6 checks | Execute all startup pre-checks | All checks pass | ☐ Pass / ☐ Fail |
| 8 | Run calibration checklist | Execute Section 7.6 | All calibration checks pass | ☐ Pass / ☐ Fail |

### 12.4 Restore from backup

| Step | Action | Validation Method | Expected Result | Status |
|---|---|---|---|---|
| 1 | Stop controller service | `sudo systemctl stop automator-controller.service` | Service transitions to "inactive (dead)" | ☐ Pass / ☐ Fail |
| 2 | Verify service stopped | `systemctl status automator-controller.service` | No process running | ☐ Pass / ☐ Fail |
| 3 | Locate backup | Find most recent backup on USB drive or external destination | Backup chosen before data loss event | ☐ Pass / ☐ Fail |
| 4 | Restore image data | `rsync -av /media/pi/<drive>/automator_backup/ /home/pi/Automator/data/` | Files restored to original path | ☐ Pass / ☐ Fail |
| 5 | Restore raw artifacts (if needed) | `tar -xzf /media/pi/<drive>/raw_<date>.tgz -C /home/pi/Automator/` | Raw logs and state restored | ☐ Pass / ☐ Fail |
| 6 | Verify file integrity | Spot-check restored files with `file` and visual inspection | Files valid and readable | ☐ Pass / ☐ Fail |
| 8 | Restart service | `sudo systemctl restart automator-controller.service` | Service "active (running)" | ☐ Pass / ☐ Fail |
| 9 | Verify API | `curl -u admin:<pw> http://localhost:8080/system/state` | JSON response with valid state | ☐ Pass / ☐ Fail |
| 10 | Test file access | Try loading restored files via UI file browser | Files visible and accessible | ☐ Pass / ☐ Fail |

### 12.5 Recalibration after failure

Mandatory recalibration after any of:

| Trigger Event | Reason | Recalibration Scope | Validation Check | Status |
|---|---|---|---|---|
| Mechanical intervention (gantry repair, bearing replacement) | Alignment may have shifted | Full Section 7 | Homing repeatable, scan stable, focus sharp | ☐ Pass / ☐ Fail |
| Camera repositioning or focus adjustment | Imaging parameters changed | Sections 7.4 and 7.5 | Camera sharpness, lighting uniformity verified | ☐ Pass / ☐ Fail |
| Significant thermal or vibration event | Mechanical stress | Sections 7.1 and 7.2 | Homing consistent, plate detection stable | ☐ Pass / ☐ Fail |
| Collision-like incident (E-stop, impact) | Mechanical damage possible | Full Section 7 + physical inspection | No visible damage, all subsystems nominal | ☐ Pass / ☐ Fail |
| Extended downtime (> 2 weeks) | Mechanical drift | Sections 7.1 and 7.4 | Homing and focus verified after idle period | ☐ Pass / ☐ Fail |

Before resuming production imaging:

- Complete all applicable recalibration procedures
- Document findings in Section 7.6 checklist
- Run one full test cycle to validate end-to-end imaging

---

## 13. Maintenance schedule

### 13.1 Schedule table

#### Daily maintenance

| Task | Validation Method | Pass Criteria | Status | Performed By | Date |
| --- | --- | --- | --- | --- | --- |
| Visual inspection (gantry, stage) | Walk around system, check for obstructions/damage | No visible damage, obstructions, or loose parts | ☐ Pass / ☐ Fail | | |
| Run scan check | Execute Generate Preview Image | Plate count > 0 and consistent with expected layout | ☐ Pass / ☐ Fail | | |
| Disk free-space check | `curl -u admin:<pw> http://localhost:8080/system/disk` | Free space > 20% on both paths | ☐ Pass / ☐ Fail | | |
| Log check for errors | `tail -n 50 /home/pi/Automator/raw/controller.log` | No ERROR or CRITICAL entries in last 50 lines | ☐ Pass / ☐ Fail | | |

#### Weekly maintenance

| Task | Validation Method | Pass Criteria | Status | Performed By | Date |
| --- | --- | --- | --- | --- | --- |
| Camera cleanliness/focus | Inspect lens, capture test image | Lens clear, image sharp at edges | ☐ Pass / ☐ Fail | | |
| Cable harness inspection | Visual + gentle tug test on all connectors | No loose/frayed cables, secure connections | ☐ Pass / ☐ Fail | | |
| Service status validation | `systemctl status automator-controller.service klipper moonraker` | All services "active (running)" | ☐ Pass / ☐ Fail | | |
| Door interlock function test | Close/open door, verify UI state changes | Door open (held ≥ 3 s) → UI shows "door open", imaging pauses; closed → ready. Brief tap < 3 s must NOT trigger a pause (debounce filter). | ☐ Pass / ☐ Fail | | |
| Vacuum system inspection | Inspect hose connections at pump, solenoid, and suction cup; listen to pump at idle and under `HOLD` | No audible leaks; pump tone consistent; hose connections firm | ☐ Pass / ☐ Fail | | |
| Servo range-of-motion test | Send `ROTATE ANGLE=0` then `ROTATE ANGLE=90` via Klipper console and observe lid movement | Lid completes full rotation in both directions without clicking, binding, or stalling | ☐ Pass / ☐ Fail | | |

#### Monthly maintenance

| Task | Validation Method | Pass Criteria | Status | Performed By | Date |
| --- | --- | --- | --- | --- | --- |
| Retention/backup audit | List backup files, verify sizes | Latest full backup < 3 days old, size > 0 | ☐ Pass / ☐ Fail | | |
| Local storage check | `df -h /home/pi/Automator/data` | Free space > 20% | ☐ Pass / ☐ Fail | | |
| Physical emergency-stop drill | Press the physical AC-side E-stop and verify power isolation | Power is removed from all system supplies | ☐ Pass / ☐ Fail | | |
| Thermal check | `vcgencmd measure_temp` during idle and load | Idle < 60°C, load < 75°C | ☐ Pass / ☐ Fail | | |

#### Quarterly maintenance

| Task | Validation Method | Pass Criteria | Status | Performed By | Date |
| --- | --- | --- | --- | --- | --- |
| Full calibration verification | Execute all steps in Section 7 | All checks from 7.6 pass | ☐ Pass / ☐ Fail | | |
| Firmware/software update review | Check latest releases on GitHub, test | Updates vetted, tested, no breaking changes | ☐ Pass / ☐ Fail | | |
| Mechanical stress inspection | Inspect bearings, belt, stepper mounts for wear | No visible damage, no loose fasteners | ☐ Pass / ☐ Fail | | |

#### Every 6 months

| Task | Validation Method | Pass Criteria | Status | Performed By | Date |
| --- | --- | --- | --- | --- | --- |
| SOP and run-book review | Compare document against current code/workflow | Doc matches current UI labels, endpoints, behavior | ☐ Pass / ☐ Fail | | |
| Full system health audit | Run all checks from Sections 6–9 | All checks pass without escalation | ☐ Pass / ☐ Fail | | |
| Credentials rotation | Update `AUTOMATOR_ADMIN_PASSWORD`, `AUTOMATOR_SESSION_SECRET` | New credentials deployed, old ones revoked | ☐ Pass / ☐ Fail | | |

### 13.2 Firmware/software update procedure

| Step | Action | Validation Method | Expected Result | Status |
|---|---|---|---|---|
| 1 | Announce maintenance window | Notify lab operators | No active imaging during update | ☐ Pass / ☐ Fail |
| 2 | Stop active imaging | Wait for run to complete or Pause/Stop | System idle, no pending tasks | ☐ Pass / ☐ Fail |
| 3 | Backup data | `rsync -av /home/pi/Automator/data/ /media/pi/<drive>/pre-update/` | Backup completes successfully | ☐ Pass / ☐ Fail |
| 4 | Backup raw logs | `tar -czf /media/pi/<drive>/raw_preupdate_$(date +%F).tgz /home/pi/Automator/raw` | Tar file created, size > 0 | ☐ Pass / ☐ Fail |
| 5 | Pull reviewed code | `cd /home/pi/Automator && git pull` | Latest commits fetched, no conflicts | ☐ Pass / ☐ Fail |
| 6 | Update Python dependencies | `source venv_clean/bin/activate && pip install -r requirements.txt` | Pip install succeeds, no errors | ☐ Pass / ☐ Fail |
| 7 | Verify no breaking changes | Review ChangeLog.md or commit messages | No critical API/config changes | ☐ Pass / ☐ Fail |
| 8 | Restart service | `sudo systemctl restart automator-controller.service` | Service "active (running)" | ☐ Pass / ☐ Fail |
| 9 | Verify API | `curl -u admin:<pw> http://localhost:8080/system/version` | Version endpoint returns 200 OK | ☐ Pass / ☐ Fail |
| 10 | Run test cycle | Full scan → config → start → 5–10 image capture | Test run completes; images saved locally | ☐ Pass / ☐ Fail |
| 11 | Validate test output | Inspect test images and logs | Images valid, no errors in logs | ☐ Pass / ☐ Fail |
| 12 | Announce update complete | Notify team, resume normal operations | Operations resumed, monitoring active | ☐ Pass / ☐ Fail |

### 13.3 Hardware peripheral failure modes

#### Vacuum pump

| Symptom | Likely Cause | Action |
| --- | --- | --- |
| No suction; pump runs normally | Hose disconnected or kinked | Inspect all hose joints; re-seat or straighten |
| Weak suction; pump runs normally | Hose micro-crack or loose fitting | Run soapy-water test along hose; replace if bubbling |
| Pump noisy / rattling | Loose pump mount or worn diaphragm | Re-tighten mount; replace pump if persists |
| Pump does not start | Power fault or Klipper macro error | Check `SET_PIN PIN=vacuum_pump` in Klipper console; verify wiring |

#### Servo motor

| Symptom | Likely Cause | Action |
| --- | --- | --- |
| Servo clicks repeatedly without moving | Mechanical obstruction or servo stall | Power off; manually clear obstruction; inspect linkage |
| Servo moves partway and stops | Angle limit misconfigured or torque insufficient | Check `ROTATE ANGLE=` limits in `printer.cfg`; inspect for binding |
| Servo drifts after positioning | PWM signal interference or worn potentiometer | Check cable routing; replace servo if drift > 5° |
| No movement, no sound | Power or signal fault | Check servo power and signal wires at controller; verify `ROTATE` macro executes in Klipper |

---

## 14. Security considerations

### 14.1 Password management

1. Do not commit secrets to Git.
2. Set `AUTOMATOR_ADMIN_PASSWORD` and `AUTOMATOR_SESSION_SECRET` via secure runtime/service config.
3. Rotate credentials periodically and after incidents.

### 14.2 Network isolation

1. Restrict controller access to the supported paths only: direct MacBook Ethernet for normal users and Pi desktop browser access for admins.
2. The controller binds to `0.0.0.0` for the supported local/direct workflows, but must not be exposed to the public internet.

### 14.3 Patch and update management

1. Apply OS and dependency patches in controlled maintenance windows.
2. Test in non-production mode before lab rollout.
3. Record applied versions in change history.

### 14.4 Access control

1. Limit admin credentials to authorized technical staff.
2. Separate operator and admin responsibilities operationally.
3. Revoke access promptly when personnel changes occur.

### 14.5 Audit logs

Retain and review:

1. `/home/pi/Automator/raw/controller.log`
2. `journalctl -u automator-controller.service`
3. Incident notes and escalation records

### 14.6 config/ reference folder

The repository's `config/` folder holds copies of the Raspberry Pi's system-level configuration files (network profiles, systemd units, Klipper/Moonraker config, etc.) kept for reference only — it is not deployed or executed from this location. All passwords, keys, and other sensitive values in these files are redacted (e.g. `<REDACTED>`, `<REDACTED-MAC>`, `<REDACTED-IP>`) before being committed; see `config/MANIFEST.txt` for the current file inventory.

---

## 15. Decommissioning procedure

### 15.1 Safe shutdown

1. Stop active imaging run.
2. Confirm no scheduled capture is pending.
3. Stop services:

```bash
sudo systemctl stop automator-controller.service
```

4. Isolate power per Section 4.6.

### 15.2 Data archival

1. Archive image datasets and logs to approved long-term storage.
2. Export final metadata index for traceability.
3. Verify archive readability before deletion.

### 15.3 Hardware disassembly checklist

- [ ] System powered off and isolated
- [ ] Cables labeled before disconnect
- [ ] Camera modules safely packed
- [ ] Controller boards ESD-protected
- [ ] Mechanical components documented and boxed
- [ ] Decommission record signed by lab lead and engineering owner

---

## Appendix A: Quick reference

### A.1 Key API endpoints and commands

| Purpose | Command/Endpoint | Auth Required |
|:---|:---|:---|
| **Controller Status** | `curl -u admin:<pw> http://localhost:8080/system/state` | Yes |
| **System Version** | `curl -u admin:<pw> http://localhost:8080/system/version` | Yes |
| **Disk Space** | `curl -u admin:<pw> http://localhost:8080/system/disk` | Yes |
| **Logs** | `curl -u admin:<pw> http://localhost:8080/system/logs` | Yes |
| **Detect Plates** | `http://localhost:8080/detect` | Yes |
| **Start Imaging** | `http://localhost:8080/system/start` | Yes |
| **Pause Imaging** | `http://localhost:8080/system/pause` | Yes |
| **Resume Imaging** | `http://localhost:8080/system/unpause` | Yes |

### A.2 Key log files and paths

| Resource | Path | Access |
|:---|:---|:---|
| **Controller Log** | `/home/pi/Automator/raw/controller.log` | File |
| **Plate Database** | `/home/pi/Automator/raw/plates_db.json` | File |
| **Controller State** | `/home/pi/Automator/raw/controller_state.json` | File |
| **Local Image Data** | `/home/pi/Automator/data/` | Directory |
| **Klipper Logs** | `journalctl -u klipper` | System |
| **Moonraker Logs** | `journalctl -u moonraker` | System |
| **Service Logs** | `journalctl -u automator-controller.service` | System |

### A.3 Critical contacts and resources

| Role/Resource | Contact/Details |
|:---|:---|
| **Lab Operations Manager** | __________________________ |
| **System Administrator** | __________________________ |
| **Hardware Engineering** | __________________________ |
| **Emergency Support** | __________________________ |
| **Backup Storage Location** | USB drive or external destination |
| **Documentation Repo** | `https://github.com/rotsl/Automator` |

### A.4 Safety quick-check

Before each imaging session, verify:

- [ ] No obstructions in gantry path
- [ ] Door closed and interlock engaged
- [ ] Cameras connected and functional
- [ ] Storage mount accessible
- [ ] Services running (`systemctl status automator-controller.service`)
- [ ] Disk space > 20% (`/system/disk`)
- [ ] Cleanup timer active (`systemctl is-active cleanup-jpgs.timer`)
- [ ] CPU temperature < 75°C (`vcgencmd measure_temp`)
- [ ] Network connectivity confirmed (`ping <gateway>`)
- [ ] Emergency stop hardware accessible and functional

### A.5 Common emergency procedures

| Emergency Scenario | Immediate Action | Reference Section |
|:---|:---|:---|
| **Uncontrolled motion** | Press the physical AC-side emergency stop | 4.3, 8.8 |
| **Fire/smoke** | Press the physical AC-side emergency stop + evacuate + alert authorities | 4.1, 4.3 |
| **Electrical fault** | Isolate power (Section 4.6) → call engineer | 4.1, 4.6 |
| **System frozen** | Check API, restart service, hard cycle if needed | 11.1, 12.1, 12.3 |
| **Data corruption** | Stop imaging, verify backups, escalate | 10.2, 12.4 |
| **Network down** | Fallback to local capture, notify SysAdmin | 9.3, 11.1 |

---

## Appendix B: Maintenance schedule summary

| Frequency | Key Tasks | Checklist Reference |
|:---|:---|:---|
| **Daily** | Visual inspection, scan check, disk check, log review | Section 13.1 |
| **Weekly** | Camera/focus, cable inspection, service status | Section 13.1 |
| **Monthly** | Backup audit, mount integrity, physical E-stop drill, thermal check | Section 13.1 |
| **Quarterly** | Full calibration, firmware review, mechanical inspection | Section 13.1 |
| **6-Monthly** | Complete SOP review, full system audit, credential rotation | Section 13.1 |

---

## Appendix C: Severity and escalation matrix

| Severity | Criteria | Response Time | Escalation |
|:---|:---|:---|:---|
| **Sev 1** | Safety risk, uncontrolled motion, injury risk | **Immediate** | Hardware Engineer + SysAdmin + Lab Lead |
| **Sev 2** | System down, no imaging, physical E-stop recovery failure | **15 minutes** | SysAdmin → Hardware Engineer |
| **Sev 3** | Partial degradation (camera, storage, UI issues) | **1 hour** | Lab Technician → SysAdmin |
| **Sev 4** | Minor issues, cosmetic/non-blocking | **Next business day** | Operator → Lab Technician |

---

Document End

For questions or updates to this runbook, contact the TSL Bioinformatics Team.

Last verified: 2026-06-26
