<!--
SPDX-License-Identifier: CC-BY-4.0
-->
<!-- markdownlint-disable MD060 -->

# Moving the Automator — shutdown, disconnection, and rebuild

This is a procedure for **relocating the Automator**, not decommissioning it. The system will be rebuilt shortly after the move, so no data archival, credential export, or component-level disassembly is needed — the goal is a clean shutdown, disconnection of the cabling that ties the gantry to the controller unit through the chamber access, and a quick reconnect at the other end.

For full decommissioning, see [RunBook.md §15](RunBook.md#15-decommissioning-procedure) instead.

**Time estimate:** 1–2 hours for the shutdown and disconnection; similar for the rebuild.

---

## 1. What moves as what

The system splits naturally into three units. Keep each unit intact — nothing inside them needs to come apart.

| Unit                | Contents                                                                                                                                                                                                                       | Location today             |
|---------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------------------------|
| **Controller unit** | Raspberry Pi + MKS motion board in their enclosure, both PSUs, buck converter, E-stop/switch box, gang lead                                                                                                                     | Outside the growth chamber |
| **Gantry**          | Frame, X/Y/Z steppers, belts, end-stops, cable chain, vacuum pump/solenoid/suction cup, servo, cameras, lights, door sensor                                                                                                     | Inside the growth chamber  |
| **The umbilical**   | The cable loom running between the two through the chamber access: stepper and end-stop cables, servo and pump/solenoid wiring, LED and door-sensor lines, the CSI camera ribbon (with extenders), and the USB camera lead      | Through the chamber port   |

The umbilical is the only thing that gets disconnected. Disconnect at the **controller end** wherever possible, so the loom travels with the gantry and the in-chamber routing is preserved.

---

## 2. Shut down

1. **Confirm nothing is running or scheduled.** Check the web UI (kiosk display, or `http://192.168.50.2:8080/` from a connected MacBook; login `admin`). Stop any active run and wait for the arm to park.
2. **Stop the services** (Pi terminal — `Ctrl+Alt+A` exits kiosk — or SSH):

   ```bash
   sudo systemctl stop automator-controller.service
   sudo systemctl stop automator-buttons.service
   ```

   A graceful stop releases the vacuum, retracts the servo, and turns the LEDs off, so nothing is left energised.
3. **Shut down the Pi:** `sudo shutdown -h now`. Wait for the activity LED to stop (~30 s).
4. **Isolate power:** press the latching E-stop, then unplug the gang lead from the wall. Wait for all fans and indicators to stop before touching wiring.

> Images and all configuration stay on the Pi's SD card and come back untouched at power-up. No backup is required for a short move — though if the move is rough or the timeline slips, a USB-stick image export (plug in, wait 2–3 min) is cheap insurance.

---

## 3. Disconnect the umbilical

1. **Photograph first.** A few phone photos of the controller-end connections and the loom's route through the chamber access is all you need — but take them before pulling anything.
2. **Label anything ambiguous.** Most connectors on the MKS board are keyed or unique; the ones worth a tape label are the **three stepper plugs and three end-stop plugs (X/Y/Z)**, which are interchangeable with each other. The GPIO lines (door sensor → 26, buttons → 17/27, LED relay → 23) are listed in [HandOver.md §4.15](HandOver.md) if a label goes missing.
3. **Disconnect at the controller end:**
   - MKS board: stepper ×3, end-stop ×3, servo, pump/solenoid relay outputs
   - Pi / GPIO breakout: door sensor, LED relay, buttons and buzzer if they route through the port
   - Pi ports: CSI ribbon and USB camera lead
   - **CSI ribbon caution:** the connector has a lift-up locking bar — release it, don't pull the ribbon. Coil the ribbon loosely; never fold or crease it.
4. **Withdraw the loom** through the chamber access toward the gantry side and coil it loosely on or beside the gantry. Leave the in-chamber routing and the cable chain alone — the routing was set up with the calibration and the less it's disturbed, the less rework later.
5. **Unplug mains from the two PSUs is not needed** — the whole controller unit moves as one piece with its power wiring intact. Just release (twist out) the E-stop latch so it isn't held under spring tension during the move.

---

## 4. Secure for the move

- **Gantry carriages:** slowly move each axis by hand to a mid-travel position and secure with a cable tie or foam block so nothing slams in transit. Move axes gently — back-driving steppers quickly generates voltage.
- **Suction cup and servo arm:** pad the toolhead so the cup and servo horn can't snag. Don't rotate the servo shaft by hand.
- **Cameras and lights:** they stay mounted; just confirm nothing dangles and the ring light and Pi camera housing are secure.
- **Vacuum tubing:** leave connected end-to-end; just make sure it can't catch on the door frame.
- Move the gantry level and by its frame, not by belts, rails, or the toolhead.

---

## 5. Rebuild at the new location

1. Position the gantry and controller unit, route the umbilical through the new access, and reconnect everything per your photos and labels. Double-check the X/Y/Z stepper and end-stop plugs went back to the right positions, and that the CSI ribbon is seated with the locking bars closed at both ends.
2. Power up (release E-stop if latched, plug in the gang lead). The Pi boots straight back into kiosk mode; all services and network profiles return automatically.
3. **Verify before first use:**
   - All four services up: `systemctl status klipper moonraker automator-controller.service automator-buttons.service`
   - Home each axis and confirm the end-stops trigger — this is your check that X/Y/Z plugs weren't swapped
   - Door interlock: open the door, confirm the UI reports it
   - Vacuum: lid lifts and holds ≥ 5 s
   - E-stop: press it, confirm everything loses power, release and re-boot
4. **Check the calibration.** The camera-to-gantry homography (`data/calibration.json`) assumes the mounting geometry hasn't changed. Since nothing on the gantry was disassembled it will likely still be valid — but confirm with a scan of a test plate and check the detected positions look right. If plates are detected in the wrong place, re-run `dev2/calibration.py`.
5. Run one complete imaging cycle with a single test plate before handing back to users.

---

## 6. Contacts

- Dan MacLean — <dan.maclean@tsl.ac.uk>
- Rohan R (original builder) — <phonics-tiffs1i@icloud.com>
- IT/network — <christopher.rickett@tsl.ac.uk>