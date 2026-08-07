    # CLAUDE.md

Guidance for Claude Code sessions working in this repository.

## What this repo is

Documentation, source code, and hardware design files for the **Automator** — a Raspberry Pi-controlled gantry robot built by a student (Rohan R) at The Sainsbury Laboratory, Norwich, that automatically photographs QR-labelled Petri dishes on a schedule. It combines a 3-axis stepper gantry (Klipper/Moonraker on an MKS Robin Nano V3.1), a vacuum lid-lifting mechanism, two cameras, and a Flask web UI.

This clone is primarily used as the **reference documentation** for the physical instrument. The deployed, running copy of the code lives on the robot's Raspberry Pi at `/home/pi/Automator/` — changes made here do not affect the instrument unless pulled onto the Pi.

**Status (August 2026):** the robot has been moved out of its home (BINDER growth chamber TSL PGC07, TSL Building Ground Floor) into temporary storage. The move (7 Aug 2026) required destructive cable removal — the as-built wiring did not match the documentation — so the rebuild will need re-wiring, a re-printed cradle, and full recalibration. See `documentation/Move_Incident_Record_2026-08-07.md` and `documentation/Move_Procedure.md`.

## Repository layout

| Path | Contents |
| --- | --- |
| `documentation/` | All user/admin docs (see map below) |
| `hardware/` | Electrical docs, KiCad schematic, datasheets, component photos |
| `mechanical/` | STL files for 3D-printed parts, print specs, assembly photos |
| `dev2/` | The Python controller: Flask+SocketIO web UI (`maincontroller.py`), G-code sender, camera pipelines, GPIO handlers |
| `config/` | Read-only, **redacted** export of the Pi's system-level config (network profiles, systemd units, `printer.cfg`, MKS firmware binary). Reference only, not deployed from here. See `config/MANIFEST.txt` |
| `data/` | Calibration file and the YOLO ONNX model (`bestnew.onnx`) for plate detection |
| `raw/` | Runtime state/log output directory (empty in repo; populated on the Pi) |

## Where to find answers

| Question | Document |
| --- | --- |
| How is it wired / powered / pinned? | `hardware/Hardware_Documentation.md` (power tree, GPIO map, MKS pin map) |
| How does a new maintainer take over / rebuild from scratch? | `documentation/HandOver.md` — the most comprehensive doc; full install, network setup, code guide, troubleshooting |
| How do users run an imaging session? | `documentation/HowToUseAutomator.md`, `documentation/QuickStartGuide.md` |
| Operations, safety, emergencies, decommissioning | `documentation/RunBook.md` |
| How to move the robot to another location | `documentation/Move_Procedure.md` |
| What did it cost / what parts are in it? | `documentation/Bill_of_Materials.md` |
| 3D-printed parts and assembly photos | `mechanical/mechanical_guide.md` |
| Physical buttons, buzzer, systemd services | `documentation/HARDWARE_BUTTONS_AND_SERVICES.md` |
| Networking (MacBook direct Ethernet, kiosk mode) | `documentation/Raspberry_Pi_Direct_Ethernet_Access_from_MacBook_UPDATED.md`, `documentation/raspberry-pi-automator-kiosk-admin-desktop.md`, `documentation/networkandprintsettings.md` |
| Security model, credentials policy | `documentation/Security_Model_Credential_Management.md`, `documentation/SECURITY.md` |
| ML model provenance (plate detector) | `documentation/model_provenance.md` |

## Key facts worth knowing up front

- **Architecture:** Pi 4B runs the Flask controller (port 8080), Klipper host, and Moonraker (port 7125); the MKS Robin Nano V3.1 (STM32F407) executes motion. The controller talks to Moonraker over HTTP, never serial.
- **Safety is hardware-first:** a latching AC-side E-stop cuts every PSU; door interlock (proximity sensor, GPIO 26) and X/Y/Z end-stops back it up in software.
- **Two power domains:** 12 V PSU → MKS/motors/buck converter (→ 5 V peripherals); a separate dedicated 5 V PSU → Pi only.
- **Calibration is position-dependent:** `data/calibration.json` maps USB-camera pixels to gantry coordinates; moving or re-mounting hardware invalidates it (re-run `dev2/calibration.py`).
- **Access:** kiosk display on the Pi, or direct MacBook Ethernet at `http://192.168.50.2:8080/`. Web login user is `admin`; the password lives only in the systemd unit files on the Pi.

## Conventions

- **Git remotes:** `origin` is the student's repo (`rotsl/Automator`) — do not push there. Push to `teammaclean` (`TeamMacLean/Automator`), which is this group's fork and the default push target.
- **Licensing is per-file via SPDX headers:** code is MIT, hardware is CERN-OHL-S-2.0, documentation is CC-BY-4.0. New docs should carry an `SPDX-License-Identifier: CC-BY-4.0` HTML comment header like the existing ones.
- Markdown files follow markdownlint; some files disable `MD060` (table formatting) in the header where needed.
- Contacts: Dan MacLean <dan.maclean@tsl.ac.uk> (owner), Rohan R <phonics-tiffs1i@icloud.com> (original builder), Christopher Rickett <christopher.rickett@tsl.ac.uk> (IT/network).