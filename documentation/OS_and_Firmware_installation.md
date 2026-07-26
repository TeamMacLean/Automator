<!--
SPDX-License-Identifier: CC-BY-4.0
Copyright (c) 2025–2026 Rohan R
-->

# Raspberry Pi 4B + MKS Robin Nano V3.1

Complete Installation, Firmware, Network, and Configuration Guide

This document describes the full setup of a Raspberry Pi–based Klipper system, including operating system installation, network configuration (IOT Wi-Fi, Eduroam, MacBook direct Ethernet), Klipper firmware for the MKS Robin Nano V3.1, and associated support files.

---

## 1. Installing Raspberry Pi OS (64-bit)

### 1.1 Hardware and software requirements

- Raspberry Pi 4 Model B (8 GB RAM)
- microSD card, 32 GB or larger
- SD card reader
- 5 V power supply capable of at least 3 A
- Network access (Wi-Fi)
- Host computer for flashing

---

### 1.2 Download Raspberry Pi imager

Official source:  
[https://www.raspberrypi.com/software/](https://www.raspberrypi.com/software/)

Install Raspberry Pi Imager for your operating system.

---

### 1.3 Flash Raspberry Pi OS

1. Insert the microSD card into your computer
2. Open Raspberry Pi Imager
3. Select:
   - Operating System: Raspberry Pi OS (64-bit)
   - Storage: target microSD card
4. Open Advanced Options:
   - Enable SSH
   - Set username and password
   - Configure Wi-Fi (optional)
   - Set locale and timezone
5. Write the image
6. Safely eject the card

Source:  
[https://www.raspberrypi.com/documentation/computers/getting-started.html](https://www.raspberrypi.com/documentation/computers/getting-started.html  )  

---

### 1.4 First boot and system update

Insert the SD card into the Raspberry Pi and power it on.

Connect via SSH:

```bash
ssh pi@automator.local
````

Update the system:

```bash
sudo apt update
sudo apt full-upgrade -y
sudo reboot
```

---

## 2. Network configuration

### 2.1 Network overview

The system uses three network connections:

- **IOT Wi-Fi** — primary connection for normal operation
- **Eduroam** (WPA2-Enterprise / 802.1X) — fallback Wi-Fi
- **mac-direct-auto** — MacBook direct Ethernet connection via `automator-direct-dhcp.service`; the Pi acts as a DHCP server on eth0 when a MacBook is plugged in directly

The authoritative configuration and commands are documented here:

[https://github.com/rotsl/Automator/blob/main/documentation/networkandprintsettings.md](https://github.com/rotsl/Automator/blob/main/documentation/networkandprintsettings.md)

This file should be followed exactly for the deployed network profiles.

---

### 2.2 IOT Wi-Fi (primary)

List available networks:

```bash
nmcli dev wifi list
```

Connect to the IOT network:

```bash
nmcli dev wifi connect "IOT" password "PASSWORD"
```

Verify:

```bash
nmcli device status
```

---

### 2.3 Eduroam (fallback)

Eduroam requires WPA2-Enterprise configuration using NetworkManager.

- EAP method
- Phase 2 authentication
- Identity and anonymous identity
- Certificate handling

Parameters are institution-specific and defined in:

[https://github.com/rotsl/Automator/blob/main/documentation/networkandprintsettings.md](https://github.com/rotsl/Automator/blob/main/documentation/networkandprintsettings.md)

After configuration, verify connectivity:

```bash
ping -c 4 8.8.8.8
ping -c 4 google.com
```

---

## 3. Installing Klipper on the Raspberry Pi

### 3.1 Clone Klipper repository

```bash
cd ~
git clone https://github.com/Klipper3d/klipper.git
```

---

### 3.2 Install Klipper host services

```bash
./klipper/scripts/install-octopi.sh
```

This installs:

- Klipper host service
- Moonraker API
- Mainsail or Fluidd web interface

Source:
[https://www.klipper3d.org/Installation.html](https://www.klipper3d.org/Installation.html)

---

## 4. Building Klipper firmware for MKS Robin Nano V3.1

### 4.1 Board reference

Official documentation:
[https://github.com/makerbase-mks/MKS-Robin-Nano-V3.X](https://github.com/makerbase-mks/MKS-Robin-Nano-V3.X)

---

### 4.2 Firmware configuration

```bash
cd ~/klipper
make menuconfig
```

Required settings:

- MCU Architecture: STM32
- Processor Model: STM32F407
- Bootloader offset: 32KiB
- Clock Reference: 8 MHz crystal
- Communication interface: USB (PA11/PA12)

Save and exit.

---

### 4.3 Compile firmware

```bash
make clean
make
```

Firmware output:

```text
out/klipper.bin
```

---

### 4.4 Flash firmware

1. Rename:

   ```text
   klipper.bin --> robin_nano.bin
   ```

2. Copy to a FAT32-formatted SD card
3. Insert into the MKS Robin Nano
4. Power on the board
5. Wait approximately 10 seconds

Successful flashing renames the file to:

```text
FIRMWARE.CUR
```

Source:
[https://github.com/makerbase-mks/MKS-Robin-Nano-V3.X](https://github.com/makerbase-mks/MKS-Robin-Nano-V3.X)

---

### 4.5 Pre-built firmware for this setup

The compiled firmware used in this Automator deployment is stored in the repository at:

```text
config/firmware mks/firmware.bin
```

Copy this file to a FAT32 SD card, rename it to `robin_nano.bin`, and flash as described in §4.4. Building from source (§4.2–§4.3) is only necessary if the firmware configuration needs to change.

---

## 5. Connecting MKS Robin Nano to Raspberry Pi

Connect the board via USB.

Identify the serial device:

```bash
ls /dev/serial/by-id/
```

Example:

```text
usb-Klipper_stm32f407xx_47003B001951343035323830-if00
```

---

## 6. Klipper configuration

### 6.1 Printer configuration

The printer configuration file is maintained here:

[https://github.com/rotsl/Automator/blob/main/config/printer.cfg](https://github.com/rotsl/Automator/blob/main/config/printer.cfg)

Install to:

```bash
~/printer_data/config/printer.cfg
```

No modifications should be made without documenting changes.

---

## 7. Associated files

### 7.1 Documentation requirements (requirements.txt)

Used only for building documentation with MkDocs.

```text
# Python virtualenv module requirements for mkdocs
jinja2==3.1.6
mkdocs==1.2.4
mkdocs-material==8.1.3
mkdocs-simple-hooks==0.1.3
mkdocs-exclude==1.0.2
mdx-truly-sane-lists==1.2
mdx-breakless-lists==1.0.1
py-gfm==1.0.2
markdown==3.3.7
```

---

### 7.2 Klipper markdown landing file

Introductory project documentation.

Welcome to the Klipper project!

[![Klipper](https://raw.githubusercontent.com/Klipper3d/klipper/master/docs/img/klipper-logo-small.png)](https://www.klipper3d.org/)

[https://www.klipper3d.org/](https://www.klipper3d.org/)

This file does not affect runtime behavior.

---

### 7.3 Moonraker configuration (change based on your setup)

```ini
[server]
host: 0.0.0.0
port: 7125
klippy_uds_address: /home/pi/printer_data/comms/klippy.sock

trusted_forwarded_ips:
    IP1
    IP2

[authorization]
trusted_clients:
    Trusted IPS's

cors_domains:
    http://192.168.50.2:8080
    http://automator.local:8080

[machine]
name: Rohan-Automator

```

Security note:
`0.0.0.0/0` allows all IPv4 addresses and should only be used behind a firewall or trusted proxy.

Source:
[https://moonraker.readthedocs.io/](https://moonraker.readthedocs.io/)

---

## 8. Restart and verification

Restart services:

```bash
sudo systemctl restart klipper
sudo systemctl restart moonraker
```

Verify Moonraker:

```bash
ss -tuln | grep 7125
```

Verify Klipper socket:

```bash
ls ~/printer_data/comms/klippy.sock
```

Open web interface:

```text
http://automator.local
```

---

## 9. References

Raspberry Pi Documentation
[https://www.raspberrypi.com/documentation/](https://www.raspberrypi.com/documentation/)

Klipper Documentation
[https://www.klipper3d.org/](https://www.klipper3d.org/)

MKS Robin Nano V3.X
[https://github.com/makerbase-mks/MKS-Robin-Nano-V3.X](https://github.com/makerbase-mks/MKS-Robin-Nano-V3.X)

Automator Network and Print Settings
[https://github.com/rotsl/Automator/blob/main/documentation/networkandprintsettings.md](https://github.com/rotsl/Automator/blob/main/documentation/networkandprintsettings.md)

---

## Use and license context

This Raspberry Pi 4B + MKS Robin Nano V3.1 configuration is intended to be used as
part of the Automator system for automated imaging and motion-controlled workflows.

Primary project repository:  
[https://github.com/rotsl/Automator](https://github.com/rotsl/Automator)

Operational workflows, controller software, and system architecture are documented
in the Automator repository and should be consulted alongside this file.

---

## Intended use

This setup is designed for research automation, laboratory imaging, and engineering
development. It is not a certified laboratory instrument unless explicitly approved
by the hosting institution.

Users are responsible for validating the system for their experimental context and
for complying with applicable safety and regulatory requirements.

---

---

## License notice

This project is licensed under the MIT License.

All third-party software is used in accordance with its respective license.
Detailed information is provided in [`THIRD_PARTY_NOTICES.md`](https://github.com/rotsl/Automator/blob/main/documentation/Third_Party_Notices.md).
