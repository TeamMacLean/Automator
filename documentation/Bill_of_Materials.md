<!--
SPDX-License-Identifier: CC-BY-4.0
Copyright (c) 2025–2026 Rohan R
-->
<!-- markdownlint-disable MD060 -->

# Bill of Materials — Automator

All prices exclude VAT. This BOM covers the working model of the Automator. Gantry frame components, tools, some wiring, and test/prototype components are not included.

**Estimated total (ex VAT): £576.34** — excludes delivery charges.

---

## 1. Computing and Control

| # | Description | Qty | Unit Price (£ ex VAT) | Total (£ ex VAT) | Notes |
|---|-------------|-----|-----------------------|-----------------|-------|
| 1 | Raspberry Pi 4B 8 GB starter kit | 1 | 95.99 | 95.99 | Bundle includes: Pi 4B 8 GB board, case, cooling fan, 64 GB microSD, micro HDMI cable, 5 V / 3 A power supply |
| 2 | MKS Robin Nano V3.1 | 1 | 25.00 | 25.00 | STM32F407 motion controller; runs Klipper MCU firmware; 4 stepper driver slots |

---

## 2. Power Supplies and Distribution

| # | Description | Qty | Unit Price (£ ex VAT) | Total (£ ex VAT) | Notes |
|---|-------------|-----|-----------------------|-----------------|-------|
| 3 | 12 V 5 A DC power adapter | 1 | 11.12 | 11.12 | AC 100–240 V input; 60 W; powers MKS board, motors, and peripherals |
| 4 | Emergency stop switch | 1 | 16.79 | 16.79 | 220 V single phase; 16 A; latching; wired on AC side to cut all power |

---

## 3. Motion System

| # | Description | Qty | Unit Price (£ ex VAT) | Total (£ ex VAT) | Notes |
|---|-------------|-----|-----------------------|-----------------|-------|
| 5 | NEMA17 stepper motor 42×38 mm (pack of 3) | 1 | 19.99 | 19.99 | 17HS4401; 1.5 A / 3.8 V; 1.8°/step; with 1 m cable; used for X, Y, and Z axes |
| 6 | NEMA11 linear stepper motor, 200 mm stroke | 1 | 26.25 | 26.25 | T6×1 leadscrew; linear actuator |
| 7 | DRV8825 stepper motor driver | 1 | 3.00 | 3.00 | StepStick format |
| 8 | GT2 timing pulley, 16T, 5 mm bore | 2 | 5.19 | 10.38 | 6 mm belt width; 2 mm pitch; aluminium; with grub screws |
| 9 | GT2 open timing belt, 6 mm × 5 M | 2 | 3.99 | 7.98 | 2 mm pitch; rubber/fibreglass |

---

## 4. Plate Handling

| # | Description | Qty | Unit Price (£ ex VAT) | Total (£ ex VAT) | Notes |
|---|-------------|-----|-----------------------|-----------------|-------|
| 10 | Miniature air solenoid valve, DC 5 V | 1 | 7.99 | 7.99 | 2-way normally closed; 0.26 A; routes vacuum to suction cup |

---

## 5. Cameras and Imaging

| # | Description | Qty | Unit Price (£ ex VAT) | Total (£ ex VAT) | Notes |
|---|-------------|-----|-----------------------|-----------------|-------|
| 11 | Raspberry Pi Camera Module 3 Wide | 1 | 36.79 | 36.79 | Colony plate imaging; 22-pin MIPI CSI-2; wide-angle variant |
| 12 | Raspberry Pi camera protective case | 1 | 2.32 | 2.32 | Transparent; compatible with Camera Module 1, 2, and 3 |
| 13 | USB camera module | 1 | 25.99 | 25.99 | QR code scanning and plate position detection; UVC; 5 V USB powered |
| 14 | USB COB LED strip, 1 M, cold white | 1 | 6.39 | 6.39 | 320 LEDs/m; CRI 85+; 6000 K; USB powered; imaging illumination |
| 15 | Mini LED ring light, 16 cm | 1 | 3.19 | 3.19 | USB powered; fill light |
| 16 | 52 mm circular polarising filter | 1 | 11.99 | 11.99 | 30-layer multi-resistant nano coating; CPL; reduces glare on agar surface |
| 17 | CNC metal lens tripod mount ring | 1 | 28.79 | 28.79 | Camera arm mount |

---

## 6. Sensors and Safety

| # | Description | Qty | Unit Price (£ ex VAT) | Total (£ ex VAT) | Notes |
|---|-------------|-----|-----------------------|-----------------|-------|
| 18 | IR infrared obstacle avoidance sensor | 1 | 3.19 | 3.19 | Digital output; door interlock detection |
| 19 | Waterproof momentary push button switch | 1 | 4.152 | 4.152 | 2-pin; with wires; used for physical START/STOP buttons |
| 20 | Electronic Buzzer, 3–24 V Piezo | 1 | 3.432 | 3.432 | Active piezo; audio feedback |

---

## 7. Cooling

| # | Description | Qty | Unit Price (£ ex VAT) | Total (£ ex VAT) | Notes |
|---|-------------|-----|-----------------------|-----------------|-------|
| 21 | 80 mm × 10 mm DC 5 V fan | 1 | 7.19 | 7.19 | Dual ball bearings; brushless; enclosure ventilation |

---

## 8. Electronics and PCB

| # | Description | Qty | Unit Price (£ ex VAT) | Total (£ ex VAT) | Notes |
|---|-------------|-----|-----------------------|-----------------|-------|
| 22 | Raspberry Pi GPIO terminal block breakout board | 1 | 7.19 | 7.19 | 40-pin; compatible with Pi 4B/3B+/3B/2B/Zero |
| 23 | PCB prototyping board, 9 × 15 cm (2-pack) | 1 | 3.99 | 3.99 | Universal double-sided; for DIY soldering |
| 24 | 5 V 1-channel relay module with optocoupler | 1 | 3.19 | 3.19 | Supports high and low level trigger |
| 25 | 4-pin PCB screw terminal block connectors | 1 | 3.91 | 3.91 | 5 mm / 0.2 in pitch; 2-set pack (male + female); green |
| 45 | DC-DC Buck Boost Converter Module, 5 V–24 V to 5–40 V, 5 A | 1 | 3.16 | 3.16 | Adjustable voltage regulator |
| 46 | Electrolytic Capacitor, 10 V, 1000 µF | 1 | 3.112 | 3.112 | |
| 47 | Ideal Diode, 15 A | 1 | 5.912 | 5.912 | |

---

## 9. Cables and Connectivity

| # | Description | Qty | Unit Price (£ ex VAT) | Total (£ ex VAT) | Notes |
|---|-------------|-----|-----------------------|-----------------|-------|
| 26 | USB-C to Gigabit Ethernet adapter | 1 | 10.39 | 10.39 | For MacBook direct Ethernet connection to Automator |
| 27 | CSI/DSI flex ribbon cable, 50 cm (pack of 3) | 1 | 4.79 | 4.79 | Raspberry Pi camera/display extension |
| 28 | CSI/DSI flex ribbon cable, 200 cm (pack of 3) | 1 | 5.99 | 5.99 | Raspberry Pi camera/display extension |
| 29 | CSI/DSI cable extender for Raspberry Pi | 2 | 5.59 | 11.18 | Extends CSI/DSI cable length |
| 30 | Jumper wires F–M, 15 cm (pack of 120) | 1 | 11.64 | 11.64 | 20 AWG; 10 colours |
| 31 | 10-pin flat ribbon cable, 5 M | 1 | 7.15 | 7.15 | IDC; 2.54 mm pitch; PVC and copper |
| 32 | 4-pin RGB strip extension cable, 5 M | 2 | 3.96 | 7.92 | Signal extension wiring |
| 33 | XH2.54 4-pin to 6-pin stepper motor cables, 2 M (pack of 6) | 2 | 8.79 | 17.58 | For NEMA17 stepper motors |
| 34 | Cat 8 Ethernet cable, 5 M | 1 | 7.47 | 7.47 | 40 Gbps; for Pi network port |
| 35 | USB 3.0 extension cable, 2 M | 1 | 3.99 | 3.99 | USB-A male to female |
| 36 | Anker 4-Port USB 3.0 Hub | 1 | 5.992 | 5.992 | With 2 ft cable; USB-A |
| 37 | Split cable loom sleeving | 1 | 16.79 | 16.79 | 3/4 in; for cable management and protection |
| 38 | Gang Extension Lead with Surge Protection, Black | 1 | 7.992 | 7.992 | Workspace power distribution |

---

## 10. Enclosures and Cases

| # | Description | Qty | Unit Price (£ ex VAT) | Total (£ ex VAT) | Notes |
|---|-------------|-----|-----------------------|-----------------|-------|
| 39 | Aluminium alloy case for Raspberry Pi 4 | 1 | 16.00 | 16.00 | With 3510 PWM fan and passive heatsink |
| 40 | Waterproof ABS project box, IP65 | 1 | 7.99 | 7.99 | Black; for housing control electronics |
| 48 | Waterproof Plastic Project Box, ABS, IP65, Black | 1 | 7.992 | 7.992 | Switch box |

---

## 11. 3D-Printed Parts

STL files are in `mechanical/`. Parts can be self-printed on a desktop FDM printer. Prices below are from external printing at 200 µm layer thickness, 20% infill, black PETG.

| # | STL file | Dimensions (mm) | Qty | Unit Price (£ ex VAT) | Total (£ ex VAT) | Description |
|---|----------|-----------------|-----|-----------------------|-----------------|-------------|
| 41 | `Base_PIMKS.stl` | 182.0 × 134.0 × 35.0 | 1 | 22.46 | 22.46 | Base enclosure for Raspberry Pi and MKS board |
| 42 | `Cover_80mm_Two_Fans.stl` | 182.0 × 134.0 × 9.7 | 1 | 7.98 | 7.98 | Top cover housing two 80 mm fans |
| 43 | `LED_and_cam_case.stl` | 52.1 × 52.1 × 15.0 | 1 | 2.47 | 2.47 | Camera and LED enclosure lid |
| 44 | `Base_LED_and_cam_case.stl` | 52.0 × 16.7 × 61.8 | 1 | 4.20 | 4.20 | Camera and LED enclosure base |

**3D-printed parts subtotal (ex VAT, ex delivery): £37.11**

---

## Cost Summary

| Category | Total (£ ex VAT) |
|----------|-----------------|
| 1. Computing and Control | 120.99 |
| 2. Power Supplies and Distribution | 27.91 |
| 3. Motion System | 67.60 |
| 4. Plate Handling | 7.99 |
| 5. Cameras and Imaging | 115.46 |
| 6. Sensors and Safety | 10.77 |
| 7. Cooling | 7.19 |
| 8. Electronics and PCB | 30.46 |
| 9. Cables and Connectivity | 118.87 |
| 10. Enclosures and Cases | 31.98 |
| 11. 3D-Printed Parts | 37.11 |
| **Estimated total (ex VAT)** | **576.34** |

---

## Notes

This BOM covers the working model of the Automator. Gantry frame components, tools, some wiring, and test/prototype components are not included.
