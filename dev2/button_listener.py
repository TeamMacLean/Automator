# SPDX-License-Identifier: MIT
# Copyright (c) 2025–2026 Rohan R

try:
    from gpiozero import Button
except ImportError:
    Button = None  # type: ignore[assignment,misc]
from signal import pause
import subprocess
import requests
import os

# ---------------- GPIO CONFIG ----------------
START_GPIO = 17   # START
STOP_GPIO  = 27   # STOP (pause / resume )

# ---------------- API ----------------
BASE_URL = "http://127.0.0.1:8080"
STATE_URL = f"{BASE_URL}/system/state"
PAUSE_URL = f"{BASE_URL}/system/pause"
UNPAUSE_URL = f"{BASE_URL}/system/unpause"
EMERGENCY_URL = f"{BASE_URL}/emergency_stop"

password = os.environ.get("AUTOMATOR_ADMIN_PASSWORD")

if not password:
    raise RuntimeError("AUTOMATOR_ADMIN_PASSWORD not set")

AUTH = ("admin", password)


# ---------------- HELPERS ----------------
def controller_running() -> bool:
    """True if automator-controller.service is active."""
    return subprocess.run(
        ["systemctl", "is-active", "--quiet", "automator-controller.service"]
    ).returncode == 0

def get_pause_state():
    """Return (paused, imaging_active) or (None, None) on failure."""
    try:
        r = requests.get(STATE_URL, auth=AUTH, timeout=2)
        r.raise_for_status()
        data = r.json()
        return data.get("paused", False), data.get("imaging_active", False)
    except (requests.exceptions.RequestException, ValueError) as e:
        print("Failed to read controller state:", e)
        return None, None

# ---------------- START BUTTON ----------------
def start_controller():
    if controller_running():
        print("START ignored: controller already running")
        return

    subprocess.run(["systemctl", "start", "automator-controller.service"])
    print("START: controller started")

# ---------------- STOP BUTTON ----------------
def short_press_stop():
    if not controller_running():
        print("STOP ignored: controller not running")
        return

    paused, imaging = get_pause_state()
    if paused is None:
        return

    if not imaging:
        print("STOP ignored: imaging not active")
        return

    try:
        if paused:
            r = requests.post(UNPAUSE_URL, auth=AUTH, timeout=2)
            print("STOP short-press: resume response:", r.status_code, r.text, flush=True)
            r.raise_for_status()
        else:
            r = requests.post(PAUSE_URL, auth=AUTH, timeout=2)
            print("STOP short-press: pause response:", r.status_code, r.text, flush=True)
            r.raise_for_status()

    except requests.exceptions.RequestException as e:
        print("Pause/resume request failed:", e)

def long_press_stop():
    try:
        requests.post(EMERGENCY_URL, auth=AUTH, timeout=2)
        print("STOP long-press (≥5s): EMERGENCY STOP")
    except requests.exceptions.RequestException as e:
        print("Emergency stop failed:", e)

# ---------------- BUTTON SETUP ----------------
start_button = Button(START_GPIO)

stop_button = Button(
    STOP_GPIO,
    hold_time=15.0,        # 🔴 ≥15 seconds = emergency
    hold_repeat=False
)

start_button.when_pressed = start_controller
stop_button.when_pressed = short_press_stop
stop_button.when_held    = long_press_stop

print("Automator button listener running")
pause()
