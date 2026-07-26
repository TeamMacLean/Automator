<!--
SPDX-License-Identifier: CC-BY-4.0
Copyright (c) 2025–2026 Rohan R
-->

# Diagnostics web server – internal build  

**Raspberry Pi 4B – Klipper – USB Camera**

---

## 1. Purpose

- Diagnostics stack is separate from production imaging control.  
  Use `dev2/maincontroller.py` for imaging runs and `maindiagnostics.py` only for diagnostics/testing.
- Live MJPEG video (`:9000/stream`)  
- 20 Hz position / vacuum / rotation state  
- Door-sensor status  
- Safe-home (forces servo 90° before `G28`)  
- Bootstrap UI served on `:8081`
- Automatic stale MJPEG process cleanup on diagnostics startup

---

## 2. Local diagnostics ports

| Service        | Port | Protocol | Purpose               |
|----------------|------|----------|-----------------------|
| Diagnostics    | 8081 | HTTP     | Web UI + WebSocket    |
| MJPEG stream   | 9000 | HTTP     | `<img src="/stream">` |

---

## 3. Access URLs

| Service        | Local/LAN URL                   |
|----------------|----------------------------------|
| Full UI        | http://<pi-ip>:8081/             |
| MJPEG stream   | http://<pi-ip>:9000/stream       |

Public Cloudflare diagnostics URLs are not part of the current supported setup.

---

## 4. Quick start

```bash
cd ~/Automator/dev2
source /home/pi/Automator/venv_clean/bin/activate
python maindiagnostics.py
```

- Browse locally --> [`http://<pi>:8081`](`http://<pi>:8081` )
- Login: `admin` / password from `AUTOMATOR_ADMIN_PASSWORD` env var

---

## 5. File layout

```text
~/Automator/dev2/
     ├── maindiagnostics.py           # main Flask + SocketIO + watchdog
     ├── main_mjpeg_server.py         # standalone MJPEG feed
     ├── maingcodesender.py           # Klipper UNIX-socket wrapper
     ├── led.py                       # relay pin for LED
     └── templates/
         ├── login.html
         └── diag_index.html          # Bootstrap UI

```

---

## 6. Tuning

| Task                     | Where to change               | Default |
|--------------------------|-------------------------------|---------|
| Position refresh rate    | `CFG["POS_HZ"] = 0.05`        | 20 Hz   |
| MJPEG fps throttle       | edit `main_mjpeg_server.py` loop | native  |
| Ports                    | **DO NOT CHANGE**             | 8081/9000 |
| Flask reloader           | hard-disabled in both servers | `False` |

---

## 7. Troubleshooting

| Symptom                       | Fix |
|------------------------------|-----|
| `Port 9000 already in use`   | Usually stale MJPEG process. Startup watchdog now auto-cleans. Verify with `lsof -nP -iTCP:9000 -sTCP:LISTEN`. If still blocked: `pkill -f main_mjpeg_server.py` then relaunch diagnostics |
| `Port 8081 already in use`   | Another diagnostics server already running. Check `lsof -nP -iTCP:8081 -sTCP:LISTEN` and stop old process |
| OpenCV warnings on boot      | harmless – camera found on index 2 |
| GPIO "channel already in use"| warning only – relay init twice |
| STOP clicked multiple times  | UI now ignores repeated clicks and disables STOP button after first request |

---

## 8. Shutdown / restart

- UI button **STOP** or `Ctrl-C` --> graceful GPIO cleanup, child `TERM`, then forced kill if child does not exit in time.
- MJPEG server handles `SIGINT`/`SIGTERM` and releases camera on exit.

---

## 9. Security notes (internal network)

- Password is read from `AUTOMATOR_ADMIN_PASSWORD` at startup (no hardcoded fallback). The diagnostics server will not start if the env var is unset.
- Session secret is read from `AUTOMATOR_SESSION_SECRET` at startup.
- Set both in the shell or service unit before launching — same env vars used by the controller.
- No public HTTPS endpoint is provided by this diagnostics service. Keep it on the local/trusted LAN.
- Service runs as user `pi`, group `gpio`.

---

*Last updated:* 2026-06-26  
*Build:* v3.0.0
