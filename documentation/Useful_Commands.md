<!--
SPDX-License-Identifier: CC-BY-4.0
Copyright (c) 2025–2026 Rohan R
-->

# Live streaming, Klipper, and system management notes

## 1. Live stream using USB camera

This command starts a live stream using a USB camera.  
⚠️ The camera will be unavailable for other uses until you stop the process with **Ctrl + C**.

```bash
mjpg_streamer -i "input_uvc.so -d /dev/video0 -r 1024x768 -f 30" -o "output_http.so -p 8080 -w /usr/local/share/mjpg-streamer/www"
````

---

## 2. Live stream using Raspberry Pi camera

This stream uses the Raspberry Pi camera.
⚠️ The camera will be unavailable for other uses until you stop the process with **Ctrl + C**.

Local camera streams, when started manually, are available on the Pi/trusted network address you are using, for example:

```text
http://automator.local:8080/?action=stream
```

---

## 3. Moonraker / Mainsail / Klipper

### Web interface

```text
http://automator.local/
```

### Klipper service commands

```bash
sudo systemctl restart klipper
sudo systemctl status klipper
```

---

## 4. Mainsail Klipper console

```text
http://automator.local/
```

---

## 5. Diagnostics (admin and tech team only)

The diagnostics server is not part of normal imaging operation. It is only for admins and the technical team, and must be started manually from a terminal on the Raspberry Pi desktop. To access it, connect a display to the Pi micro-HDMI port and a keyboard/mouse to the Pi USB ports, then open a terminal and run:

```bash
cd /home/pi/Automator/dev2
source /home/pi/Automator/venv_clean/bin/activate
python maindiagnostics.py
```

The diagnostics web UI is then available from the Pi desktop browser at:

```text
http://127.0.0.1:8081/
```

The MJPEG stream is at:

```text
http://127.0.0.1:9000/stream
```

These ports are not accessible from a MacBook or from other computers on the network during normal operation. Stop the diagnostics server with Ctrl+C when done. Do not run `maindiagnostics.py` at the same time as `maincontroller.py`.

---

## 6. Main workflow

### Local workflow

```text
http://127.0.0.1:8080/
http://automator.local:8080/
http://192.168.50.2:8080/
```

Use `192.168.50.2` for direct MacBook Ethernet (MacBook Ethernet adapter must be on Using DHCP; the Pi assigns the MacBook a `192.168.50.x` address automatically). `automator.local` works from a connected MacBook and from the Pi desktop browser (mDNS). `127.0.0.1` is the Pi-local address used from the Pi desktop browser.

### Local image access

Use the web UI file browser from the local controller page, or browse the Pi/local storage directly:

```text
/home/pi/Automator/data/
```

---

---

## 7. Crontab & maintenance scripts

### View crontab

```bash
crontab -l
```

### Cache clearing script

```bash
nano ~/clear_cache.sh
chmod +x ~/clear_cache.sh
crontab -e
```

### JPG cleanup

```bash
# Dry run — prints what would be deleted, no files removed
python3 /home/pi/Automator/dev2/cleanup_jpgs.py

# Real deletion — deletes qualifying JPGs and dynamic folders
python3 /home/pi/Automator/dev2/cleanup_jpgs.py --delete

# Check timer status and next scheduled run
systemctl list-timers --all | grep cleanup-jpgs

# View logs from last automated run
journalctl -u cleanup-jpgs.service -n 100 --no-pager

# Show total size of data folder
du -sh /home/pi/Automator/data
```

### Logs

```bash
cat /home/pi/cache-clear.log
cat /home/pi/klipper-health.log
```
