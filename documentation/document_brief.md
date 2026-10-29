<!--
SPDX-License-Identifier: CC-BY-4.0
-->
<!-- markdownlint-disable MD060 -->

# Document Summary

**This is a reading of the existing documents, not an as-built record.**

**Prepared:** 29 October 2026, Dan MacLean, from the repository documents only. Nobody has yet checked these statements against the physical parts, in part because nobody at TSL fully understands them.

---

## 1. Quick history

The Automator was taken out of growth chamber TSL PGC07 on 7 August 2026. The wiring could not be disconnected cleanly and much of it was cut. See [Move_Incident_Record_2026-08-07.md](Move_Incident_Record_2026-08-07.md). The instrument now needs re-wiring before it can run again.

The existing documentation was written as a design description. It was not checked against the build, and the build turned out to be considerably more improvised than the documents suggest. The documents also disagree with each other on several electrically important points.

This document therefore does **not** try to say how the Automator is wired. It tries three things:

1. Lists what every source says, and marks which sources are as-deployed and which are as-designed.
2. Records every contradiction found between sources, suggests a physical check that would resolve it.
3. Lists what is not documented anywhere and will have to be determined from the parts in hand.

Where this brief states a connection, treat it as a hypothesis to confirm, not an instruction. An expert's own inspection of the parts would outrank everything written here. 

---

## 2. Source hierarchy

Not all sources are equally trustworthy. The workshop should weight them in this order.

| Rank | Source | Why |
| --- | --- | --- |
| 1 | The physical parts, their labels, and the MKS board silkscreen | The only as-built evidence that exists |
| 2 | `printer.cfg` on the Pi's SD card at `/home/pi/printer_data/config/printer.cfg` | As-deployed. Defines which MKS pins drive what. The copy in this repo (`config/klipper/printer.cfg`) has every pin value redacted, so it cannot be used for this purpose |
| 3 | The Python code in `dev2/` (`led.py`, `doorsense.py`, `button_listener.py`) | As-deployed. Defines which Pi GPIO pins are used and their logic sense |
| 4 | `hardware/Hardware_Documentation.md` | As-designed. The most complete single description, and the only place the MKS pin map is written down in the clear. Internally inconsistent in places (see section 6) |
| 5 | `documentation/Bill_of_Materials.md` | What was bought. Useful for part ratings. Does not say where each part went, and some listed parts appear in no diagram |
| 6 | `hardware/Schematic Automator .pdf` | A one-page block-wiring sketch drawn in KiCad with placeholder symbols. Shows topology only. The MKS board is drawn as an unlabelled box, so no MKS pin assignments appear on it |
| 7 | `documentation/HandOver.md` §3 and §4.15, `documentation/HARDWARE_BUTTONS_AND_SERVICES.md` | Secondary descriptions that largely repeat source 4, with one or two additions |
| 8 | Photographs (see section 3) | Show the as-built state, but at low resolution and without labels. Useful for cross-checking, not for reading connections |

---

## 3. Documents and images to have open

- `hardware/Hardware_Documentation.md`, in particular §2 (power), §3 (power tree), §7 (sensor logic), §8 (pin maps).
- `hardware/Schematic Automator .pdf` (one A4 page, image only).
- `documentation/Move_Incident_Record_2026-08-07.md` (what was cut; the inventory table in it is still empty).
- `documentation/Bill_of_Materials.md` §2, §6, §8, §9.
- `documentation/HARDWARE_BUTTONS_AND_SERVICES.md` (Pi GPIO table including the buzzer).
- Photographs:
  - `hardware/images/` for close-ups of each component type and the E-stop box (`estop.jpg`).
  - `documentation/images/Controller_sideview.jpg`, `controller_topview.jpg`, `Pi_power_hdmi.JPG` for the controller enclosure.
  - `documentation/images/doorsensor.jpg`, `endstops.jpg`, `pump_servohousing.JPG`, `usb_camera_and_light.jpg`, `suctioncup_rpicamera.JPG` for the gantry end.
  - `mechanical/IMG_5643.JPG` to `IMG_5649.JPG` for assembly and the cable chain. `IMG_5647.JPG` shows the taped joints that the incident record describes.

---

## 4. Topology all sources agree on

These points are consistent across every source. They are still as-designed statements and should be confirmed on the bench, but there is no known contradiction.

- Mains enters through a single latching E-stop switch on the AC side. Everything downstream loses power when it is pressed. The E-stop is in its own project box (`hardware/images/estop.jpg` shows two cables leaving the bottom of the box).
- Two separate AC-to-DC supplies sit downstream of the E-stop:
  - a 12 V, 5 A adapter feeding the MKS Robin Nano V3.1 and, through it or beside it, the steppers and a buck converter;
  - a 5 V, 3 A adapter (the Raspberry Pi kit supply) feeding the Raspberry Pi 4B only.
- The buck converter takes 12 V and produces a 5 V peripheral rail. It does not power the Pi.
- All grounds are common.
- The Pi talks to the MKS over USB. No Pi GPIO is used for motion.
- Three NEMA17 steppers (X, Y, Z) and three mechanical end-stops connect to the MKS board. End-stops are normally open and switch to ground, with the MCU's internal pull-ups.
- A servo (MG995 or MG996R, the sources vary), a vacuum pump, and an air solenoid are driven from MKS outputs.
- The Pi carries: a USB camera, a Camera Module 3 on CSI with ribbon extenders, two momentary buttons, a door sensor, an LED relay, and (per two of the documents) a buzzer.
- Three 5 V fans: two 80 mm in the controller enclosure cover, one small fan on the Z motor.

---

## 5. Connection register

One row per connection as the sources describe it. The **Confidence** column is a judgement of how far the sources agree and whether an as-deployed source backs the row. Treat **low** rows as open questions.

### 5.1 AC side

| From | To | What the sources say | Confidence | Check |
| --- | --- | --- | --- | --- |
| Wall socket | E-stop box | Gang extension lead, surge protected, in the BOM. Photo shows one cable in, two out of the E-stop box | medium | Confirm which conductors the E-stop actually breaks (live only, or live and neutral) |
| E-stop box | 12 V PSU | "Fuses (via Emergency Stop)" is the only mention of fusing. No rating given | low | Find out whether any fuse exists and what it is |
| E-stop box | 5 V Pi PSU | As above | low | As above |

### 5.2 12 V domain

| From | To | What the sources say | Confidence | Check |
| --- | --- | --- | --- | --- |
| 12 V PSU | MKS VIN | All sources | high | Polarity on the MKS power terminal |
| 12 V (source unstated) | Buck converter input | Power tree draws it under the MKS; schematic draws it from the 12 V rail. Unclear whether it is wired to the PSU directly or to a terminal on the MKS | medium | Trace the actual feed |
| MKS driver slots X, Y, Z | Steppers X, Y, Z | 4-pin XH to 6-pin cables in the BOM. The three plugs are interchangeable and were identified by labels on the old loom | high as to topology | Which driver modules are fitted is not documented (section 7) |

### 5.3 MKS pin map

From `Hardware_Documentation.md` §8, which claims to be derived from the un-redacted `printer.cfg`. The right-hand column gives the function those pins have in the generic Klipper configuration for this board. That correspondence is from the Klipper example config, not from this unit, and should be verified against the board silkscreen.

| Function | MCU pin (per doc) | Notes in doc | What that pin is on a standard Robin Nano V3 (unverified) |
| --- | --- | --- | --- |
| X step / dir / enable | PE3 / PE2 / PE4 | dir and enable inverted | X driver slot |
| Y step / dir / enable | PE0 / PB9 / PE1 | enable inverted | Y driver slot |
| Z step / dir / enable | PB5 / PB4 / PB8 | dir and enable inverted | Z driver slot |
| X end-stop | PA15 | pull-up | X- end-stop header |
| Y end-stop | PD2 | pull-up | Y- end-stop header |
| Z end-stop | PC8 | pull-up | Z- end-stop header |
| Servo signal | PA0 | software PWM, 0 to 90° | Heated-bed MOSFET output (HB), a 12 V low-side switched output, not a logic-level servo header |
| Vacuum pump | PE5 | software PWM, "drives relay" | Hotend heater MOSFET output (HE0), 12 V low-side switched |
| Solenoid valve | PB0 | software PWM, "drives relay" | Fan output FAN1, low-side switched |

If the standard mapping holds, the pump and solenoid are being switched directly by the board's heater and fan MOSFET outputs, which would be consistent with the BOM's "PWM module" blocks in the schematic being nothing more than those on-board outputs, and with the pump and solenoid being 12 V parts. It would also mean the servo signal is taken from a 12 V switched output, which is unusual and would need something in between. None of this is confirmed. See contradictions C2 and C3.

### 5.4 5 V peripheral rail (buck converter output)

| Load | What the sources say | Confidence | Check |
| --- | --- | --- | --- |
| Servo power | All sources: 5 V from buck | high | Confirm the buck is set to 5.0 V before connecting (section 7) |
| Proximity (door) sensor power | All sources: 5 V from buck | high | See C6 on logic level |
| Relay module coil | Hardware doc: 5 V from buck | medium | Which relay this is (Pi-side LED relay or something else) is unclear, see C4 |
| Fans ×3 | Power tree and schematic | medium | Fans are not in the Pi GPIO or MKS pin lists, so presumably hard-wired to the rail with no control |
| LED strip | Hardware doc: 5 V via relay. BOM: USB-powered COB strip and USB ring light | low | See C4 |
| Vacuum pump | Power tree: 5 V. Parts list: 12 V | low | See C2 |
| Solenoid | Power tree: 5 V. Parts list: 12 V. BOM: 5 V 0.26 A | low | See C2 |

### 5.5 Raspberry Pi GPIO

This table is backed by the code in `dev2/`, which is as-deployed. Physical pin numbers are from `HARDWARE_BUTTONS_AND_SERVICES.md`.

| BCM GPIO | Physical pin | Function | As-deployed evidence | Logic sense in code | Confidence |
| --- | --- | --- | --- | --- | --- |
| 17 | 11 | START button | `button_listener.py` | gpiozero `Button` default: internal pull-up, button closes to GND | high |
| 27 | 13 | STOP / pause button, 15 s hold = emergency stop | `button_listener.py` | as above | high |
| 23 | 16 | LED relay control | `led.py` `RELAY_PIN` | driven HIGH to turn LEDs on | high |
| 4 | 7 | "Relay pulse trigger" | `led.py` `PULSE_PIN` | pulsed HIGH for 100 ms at each LED on and off | high that it is driven; **its purpose is undocumented**, see C5 |
| 26 | 37 | Door sensor input | `doorsense.py` | configured as plain input with **no** pull-up; HIGH means door open | high as to pin; see C6 on wiring |
| 13 | 33 | Buzzer | Docs only. Driven by `/usr/local/sbin/automator-buzzer.sh` on the Pi, which is not in the repo | not verifiable from the repo | low |

The BOM includes a 40-pin GPIO screw-terminal breakout board. The photographs suggest GPIO connections were made to that rather than to the header directly.

### 5.6 Cameras and USB

| Connection | What the sources say | Confidence |
| --- | --- | --- |
| Pi CSI → Camera Module 3 Wide | 22-pin ribbon with 50 cm and 200 cm extension ribbons and two CSI extender boards in the BOM. Total ribbon length and extender count actually used are not recorded | medium |
| Pi USB → USB camera | Possibly via the USB 3.0 extension lead and the 4-port hub in the BOM | medium |
| Pi USB → MKS USB | Klipper serial | high |

---

## 6. Contradictions register

Each item gives the conflicting statements, where they are, and a physical check that would settle it.

### C1. Does the E-stop cut the Pi supply?

- `Hardware_Documentation.md` §2.1 and §4.1: yes, the Pi adaptor is downstream of the E-stop.
- `Move_Procedure.md` §2 step 4 implies the same.
- The photo `estop.jpg` shows one cable in and two out of the E-stop box. Two outputs are consistent with two PSUs, but the Pi could equally be on the gang lead upstream.
- **Check:** trace the Pi PSU's mains lead back to the E-stop box or to the gang lead.

### C2. Vacuum pump and solenoid: 5 V or 12 V?

- `Hardware_Documentation.md` §2.2 (table): pump and solenoid on the 12 V rail.
- `Hardware_Documentation.md` §3 (power tree): both under the 5 V buck converter.
- `Hardware_Documentation.md` §6.1: "pump powered from 5 V via air solenoid; solenoid powered from 5 V".
- `Hardware_Documentation.md` §10 (parts list): "Vacuum pump (12 V)", "Air solenoid valve (12 V)".
- `Bill_of_Materials.md` item 10: solenoid is "DC 5 V, 0.26 A". No pump appears in the BOM at all.
- Schematic: "Air flow Solenoid 5V" is drawn beside a relay symbol, and two "PWM module" blocks sit between the MKS and the pump and solenoid.
- **Check:** read the voltage printed on the pump and the solenoid. Applying 12 V to a 5 V solenoid or pump will destroy it.

### C3. What switches the pump and solenoid?

- `Hardware_Documentation.md` §8.2: MKS pins PE5 and PB0 "drive relay".
- `HandOver.md` §3.3: "controlled via relay outputs from the MKS board".
- Schematic: two "PWM module" blocks (U2, U4), with VIN / SHDN / GND / NFB pins, which is a regulator footprint used as a placeholder. These are not relays.
- `printer.cfg`: both pins are configured as software PWM at about 38 Hz with a 5 % idle duty, which is only sensible driving a MOSFET or a MOSFET module, not a mechanical relay.
- If the standard pin mapping in §5.3 holds, PE5 and PB0 are the board's own heater and fan MOSFET outputs, and there may be no external module at all.
- **Check:** look for external MOSFET or relay modules in the salvaged parts; look at what is connected to the HE0 and FAN1 terminals of the MKS; read the live `printer.cfg`.

### C4. LED lighting: what is it, and how is it switched?

- `Hardware_Documentation.md` §6.3: "LED strip powered from 5 V peripheral rail, switched via relay".
- `Bill_of_Materials.md` items 14 and 15: a USB COB LED strip and a USB ring light, both USB powered.
- `Bill_of_Materials.md` item 24: one 5 V single-channel relay module with optocoupler, "supports high and low level trigger".
- Schematic: one relay K1 near the Pi, labelled "Relay 5V", with an LED series symbol D1.
- Code: GPIO 23 goes HIGH to turn the LEDs on.
- It is not stated whether the relay switches the strip, the ring light, or both, nor whether the switched supply is the buck 5 V rail or a USB port.
- **Check:** identify the light units and what the relay contacts were wired to. Note the relay module's trigger-level jumper position if it has one.

### C5. What is GPIO 4 for?

- Code pulses GPIO 4 HIGH for 100 ms every time the LEDs are switched on or off.
- `Hardware_Documentation.md` §8.4.1: "LED relay pulse output". `HandOver.md` §4.15: "Relay pulse trigger output". Neither says what it is connected to.
- There is only one relay module in the BOM. A pulse output alongside a level output suggests either a second, latching relay, or an earlier design that was never removed.
- **Check:** find out whether anything was ever wired to physical pin 7. If nothing, the workshop can ignore it.

### C6. Door sensor wiring and logic level

- `Hardware_Documentation.md` §7.1: "Normally open, wiring GPIO to GND, pull-up enabled".
- `HandOver.md` §4.15: "Internal pull-ups are used on all inputs. No external resistors are required".
- `doorsense.py` configures GPIO 26 as a plain input with **no** pull-up, and reads HIGH as door open.
- `Bill_of_Materials.md` item 18: the sensor is an "IR infrared obstacle avoidance sensor" module, which has a powered output stage, not a dry contact. It is powered from the 5 V rail per §5.4.
- A 5 V-powered module driving its output into a 3.3 V GPIO with no level shifting is a possibility the documents do not address. `HandOver.md` §5 notes that servo PWM noise on GPIO 26 is debounced in software, which hints the line is long and unbuffered.
- **Check:** identify the sensor module and its supply voltage, and whether its output is open-collector or push-pull. Decide whether a level shifter or divider is needed.

### C7. Servo part and drive

- `Hardware_Documentation.md` §10 links the MG995 datasheet. `printer.cfg` is headed "SERVO (MG996R)". These are similar parts, but the discrepancy shows the docs were not checked against the part.
- The servo pin PA0 is, on the standard board mapping, a 12 V heater MOSFET output. A servo signal line cannot be driven from that directly. Either the standard mapping does not hold for this unit, or something sits between the MKS and the servo, or the servo signal is taken from somewhere else entirely.
- **Check:** read the servo label; read the live `printer.cfg`; trace the servo signal wire.

### C8. Buzzer

- Listed on GPIO 13 in `Hardware_Documentation.md` and `HARDWARE_BUTTONS_AND_SERVICES.md`. Absent from `HandOver.md` §4.15 and from the schematic.
- Driven by a script that exists only on the Pi.
- **Check:** whether a buzzer exists among the salvaged parts, and read the script on the Pi.

### C9. Stepper driver count

- `Bill_of_Materials.md` lists one DRV8825 driver. Three axes need three drivers. The MKS board does not ship with drivers.
- **Check:** section 7, item 1.

### C10. Which cable types made up the umbilical

- The BOM contains 10-way ribbon cable, 4-core RGB extension cable, jumper wires, and stepper cables. Nothing records which signals ran on which cable.
- The incident record describes inline splices and knots, so the as-built cabling may not match the BOM at all.
- **Check:** the salvaged loom.

---

## 7. Not documented anywhere

These will have to be determined from the parts, from the Pi, or by decision.

1. **Stepper driver type, count, and current setting.** The driver modules fitted to the MKS X, Y, Z slots are not recorded, nor is the vref or run current. The driver type determines whether the board's UART/SPI jumpers must be set, and whether the Klipper config needs TMC sections. Look at the modules; if they are DRV8825 or A4988 the current is set by a trim pot that must be measured and set. The motors are rated 1.5 A per phase.
2. **Buck converter output setting.** It is an adjustable buck-boost module (BOM item 45) with a 5 to 40 V output range. It must be set to 5.0 V with no load before anything is connected to its output. Nothing records that this was done or how.
3. **The 15 A ideal diode and 1000 µF capacitor** (BOM items 46, 47) appear in no diagram or text. Their most plausible place is on the 5 V rail, but that is a guess.
4. **Fuse ratings and positions**, if any.
5. **Wire gauges** for the 12 V motor and pump wiring versus the signal wiring.
6. **Connector types at each end.** The incident record suggests JST-XH, spade, or screw terminal as appropriate. That is a suggestion, not a record.
7. **Fan wiring.** Three 5 V fans are drawn on the rail with no switching. Whether they were on the buck output or elsewhere is not recorded.
8. **The E-stop box internals**: what it switches and how the two output cables are terminated.
9. **USB topology**: whether the hub and extension in the BOM were used, and for which camera.
10. **CSI ribbon routing**: total length and number of extender boards in the chain.

---

## 8. Things worth getting from the Pi before starting

These would turn several "low" rows above into "high", and need no hardware work.

- A copy of `/home/pi/printer_data/config/printer.cfg` with the pin values intact.
- The script `/usr/local/sbin/automator-buzzer.sh`.
- Output of `pinctrl` or `raspi-gpio get` is of no use with the hardware disconnected, so the code remains the reference for the Pi side.

The Pi can be booted on its own 5 V supply with nothing else connected to read these off.

---

## 9. Before first power-up

Not a substitute for the workshop's own procedure. Collected from `Move_Incident_Record_2026-08-07.md` §3 and `HandOver.md` §11, which should be read in full.

- Inspect every re-made connection for shorts and polarity before connecting either PSU. The 12 V motor wiring and anything landing on the Pi GPIO header are the places where a mistake is expensive.
- Set and measure the buck converter output before connecting its loads.
- Power the MKS alone first and confirm it enumerates on USB. Validate Klipper homing and end-stops on each axis before running the Automator controller. Swapped X/Y/Z plugs show up here.
- Verify each Pi GPIO device individually: buttons, door sensor, LED relay, buzzer.
- Test the E-stop and confirm every supply drops.
- Full recalibration is required afterwards (`dev2/calibration.py`); the old `data/calibration.json` is invalid.

---

## 10. Contacts

- Dan MacLean, <dan.maclean@tsl.ac.uk>
- Rohan R (original builder), <phonics-tiffs1i@icloud.com>. The best source for the questions in sections 6 and 7.
- Christopher Rickett (IT/network), <christopher.rickett@tsl.ac.uk>
