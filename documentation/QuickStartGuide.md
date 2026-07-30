<!--
SPDX-License-Identifier: CC-BY-4.0
Copyright (c) 2025–2026 Rohan R
-->

# Quick Start Guide

> **Before you begin:** This system opens plate lids during imaging. The current installation in TSL PGC07 is for demonstration purposes only and is not suitable for live culture use. Organisms subject to containment requirements — including *Magnaporthe* cultures under a plant health licence — must not be used with this system until it is relocated to an appropriate facility. Confirm suitability with your supervisor before proceeding.

---

## 1. What you need

<table>
<thead>
<tr><th>Item</th><th>Detail</th></tr>
</thead>
<tbody>
<tr>
<td>Laptop</td>
<td>MacBook or similar with a USB-C port and a web browser</td>
</tr>
<tr>
<td>USB drive</td>
<td>For copying images off the Automator (exFAT, FAT32, or NTFS)</td>
</tr>
<tr>
<td>Login credentials</td>
<td>Username: <code>admin</code> &nbsp;&nbsp; Password: <code>tsl</code></td>
</tr>
</tbody>
</table>

---

## 2. Location

<table style="border-collapse:collapse;width:100%;">
<tr>
<td style="width:42%;vertical-align:top;padding-right:1.5rem;border:0;">
<img src="../images/Location_of_Automator_Growth_Chamber-TSL_PGC07.JPG" alt="TSL PGC07 growth chamber" style="max-width:100%;border-radius:4px;">
<p style="font-size:0.82em;font-style:italic;margin-top:0.3rem;">TSL PGC07 — BINDER growth chamber, Growth Room</p>
<img src="../images/Automator_Inside_Growth_Chamber.JPG" alt="Automator inside growth chamber" style="max-width:100%;border-radius:4px;margin-top:0.75rem;">
<p style="font-size:0.82em;font-style:italic;margin-top:0.3rem;">Automator inside TSL PGC07, door open</p>
</td>
<td style="vertical-align:middle;border:0;">
<p>The Automator is located inside <strong>TSL PGC07</strong>, a BINDER growth chamber in the Growth Room on the TSL Building Ground Floor, at the end of the room nearest the window.</p>
</td>
</tr>
</table>

---

## 3. Getting started

<table style="border-collapse:collapse;width:100%;margin-bottom:1.5rem;">
<tr>
<td style="width:42%;vertical-align:top;padding-right:1.5rem;border:0;">
<img src="../images/LAN_Connection_Mac_Location.JPG" alt="Ethernet cable beside TSL PGC07" style="max-width:100%;border-radius:4px;">
<p style="font-size:0.82em;font-style:italic;margin-top:0.3rem;">Ethernet cable hanging beside TSL PGC07</p>
<img src="../images/LAN_Connection_Mac.JPG" alt="USB-C to Ethernet adapter on MacBook" style="max-width:100%;border-radius:4px;margin-top:0.75rem;">
<p style="font-size:0.82em;font-style:italic;margin-top:0.3rem;">USB-C to Ethernet adapter connected to MacBook</p>
<img src="../images/Switch_Location.JPG" alt="START button location beside TSL PGC07" style="max-width:100%;border-radius:4px;margin-top:0.75rem;">
<p style="font-size:0.82em;font-style:italic;margin-top:0.3rem;">START button location beside TSL PGC07</p>
</td>
<td style="vertical-align:top;border:0;">
<p><strong>Connect and start</strong></p>
<ol>
<li>Take the Ethernet cable hanging on the wall beside TSL PGC07 (labelled <em>Cable to connect to your MacBook</em>).</li>
<li>Plug a USB-C to Ethernet adapter into your MacBook.</li>
<li>Connect the cable into the adapter. Wait ~15 seconds for the network to establish.</li>
<li>Press the green <strong>START</strong> button on the wall beside TSL PGC07.</li>
<li>Open <code>http://automator.local:8080/</code> in your browser.<br>Fallback: <code>http://192.168.50.2:8080/</code></li>
<li>Log in: username <code>admin</code>, password <code>tsl</code>.</li>
</ol>
</td>
</tr>
</table>

<table style="border-collapse:collapse;width:100%;margin-bottom:1.5rem;">
<tr>
<td style="width:42%;vertical-align:top;padding-right:1.5rem;border:0;">
<img src="../images/qr_generator1.png" alt="QR code generator — experiment details" style="max-width:100%;border-radius:4px;">
<p style="font-size:0.82em;font-style:italic;margin-top:0.3rem;">QR code generator — experiment details form</p>
</td>
<td style="vertical-align:top;border:0;">
<p><strong>Make, print, and stick QR labels</strong></p>
<ol>
<li>Fill in the experiment details on the QR page (strain, media, condition, orientation).</li>
<li>Click <strong>Add QR to List</strong> for each plate.</li>
<li>Click <strong>Download PDF Sheet</strong>, print, and cut out the labels.</li>
<li>Stick each label on top of the lid of the corresponding plate with the QR code facing up.</li>
</ol>
</td>
</tr>
</table>

!!! tip "Save time — standalone QR generator"
    Generate and print QR labels on your laptop without connecting to the Automator. Install once:
    ```
    pip install qr-generator-Automator
    qr-generator
    ```
    Available at [pypi.org/project/qr-generator-Automator](https://pypi.org/project/qr-generator-Automator/).

<table style="border-collapse:collapse;width:100%;">
<tr>
<td style="width:42%;vertical-align:top;padding-right:1.5rem;border:0;">
<img src="../images/Plates_placement.JPG" alt="QR-labelled plates placed in the workspace" style="max-width:100%;border-radius:4px;">
<p style="font-size:0.82em;font-style:italic;margin-top:0.3rem;">QR-labelled plates placed in the workspace</p>
<img src="../images/left_workflow_instruction_panel.png" alt="On-screen workflow instructions panel" style="max-width:100%;border-radius:4px;margin-top:0.75rem;">
<p style="font-size:0.82em;font-style:italic;margin-top:0.3rem;">On-screen workflow instructions panel</p>
</td>
<td style="vertical-align:top;border:0;">
<p><strong>Proceed to imaging</strong></p>
<ol>
<li>Replug your USB-C to Ethernet adapter if you disconnected it to print.</li>
<li>Click <strong>Proceed to imaging system</strong> on the QR page (or go directly to <code>http://automator.local:8080/main</code>).</li>
<li>Place QR-labelled plates flat inside the workspace, QR label facing up, each on a <strong>green sticker position</strong> on the workspace floor. Up to <strong>6 dishes</strong> can be placed at once.</li>
<li>Follow the on-screen workflow steps:<br>
<strong>Generate preview image (Scan) → Refresh ↻</strong> → tick plates (or use **Select All**) → configure each plate → <strong>Run Imaging</strong>.</li>
<li>Optionally add an experiment tag and a notification email before starting.</li>
</ol>
</td>
</tr>
</table>

---

## 4. Extracting images

<table style="border-collapse:collapse;width:100%;">
<tr>
<td style="width:42%;vertical-align:top;padding-right:1.5rem;border:0;">
<img src="../images/Switch_Location.JPG" alt="USB hub and drive connected to the Automator" style="max-width:100%;border-radius:4px;">
<p style="font-size:0.82em;font-style:italic;margin-top:0.3rem;">USB hub and USB drive connected to the Automator</p>
</td>
<td style="vertical-align:top;border:0;">
<p><strong>Export to USB drive</strong></p>
<ol>
<li>Plug your USB drive into the USB hub connected to the Automator.</li>
<li>Export starts automatically — no button to press.</li>
<li>Wait for a beep confirming the copy is complete and the drive is safe to remove.</li>
<li>Remove the drive. Images are in the <code>images/</code> folder on the drive.</li>
</ol>
<p><strong>Note:</strong> Images are auto-deleted from the Automator after 21 days. Export before this window.</p>
</td>
</tr>
</table>

---

For detailed instructions and FAQ refer to [HowToUseAutomator.md](HowToUseAutomator.md).

!!! note ""
    If the network is down you will not receive an email notification when imaging completes.
