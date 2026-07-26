# SPDX-License-Identifier: MIT
# Copyright (c) 2025–2026 Rohan R

# See README.md for the full A-L sequence description.



import os
import time
import json
import re
import signal
import threading
import sqlite3
import onnxruntime as ort
from pathlib import Path
import cv2
import traceback                       
from datetime import datetime
from datetime import timedelta
import numpy as np
import secrets
from flask import Flask, jsonify, request, render_template, send_file
from flask_socketio import SocketIO
from flask_wtf.csrf import CSRFProtect
import segno
import subprocess
import urllib.request
import urllib.error
import contextlib
from queue import Queue, Full
from maingcodesender import prepare_printer, move_to, get_position, send_gcode
from doorsense import init_door_sensor, door_state
from led import turn_on_led, turn_off_led, turn_off_led_no_pulse, send_pulse
from mainusbcamera import (
    detect_plates,
    preprocess, postprocess, px_to_mm, detect_qr, validate_micro_qr,
    find_camera, mm_to_px_local, crop_circular_roi, zoom_roi, normalise_for_qr,
    YOLO_MODEL, CONF_THRES, IOU_THRES, PlateID, DB_PATH,
    FALLBACK_DETECTION_ENABLED, FALLBACK_SCAN_FRAME_COUNT, FALLBACK_SCAN_FRAME_DELAY_SEC,
    begin_fallback_scan, detect_geometric_plate_candidates,
    update_fallback_tracks, get_confirmed_fallback_plates_for_scan,
    retire_fallback_tracks_overlapping_yolo, dismiss_fallback_track, reset_fallback_tracking,
)
try:
    from picamera2 import Picamera2
    from libcamera import controls
except ImportError:
    Picamera2 = None  # type: ignore[assignment,misc]
    controls = None   # type: ignore[assignment]

from dotenv import load_dotenv


load_dotenv()

ADMIN_PASSWORD = os.getenv("AUTOMATOR_ADMIN_PASSWORD")
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SMTP_FROM = "no-reply-tslautomator@nbi.ac.uk"


def send_run_email(plate_id, plate_desc, start_time, finish_time, path, recipients):
    try:
        msg = MIMEMultipart()
        msg["From"] = SMTP_FROM
        msg["To"] = ", ".join(recipients)
        msg["Subject"] = f"run: {plate_desc}"

        body = f"""<html><body style="font-family: sans-serif; font-size: 14px;">
<p><strong>Imaging Run Completed</strong></p>
<p>
  <strong>Plate ID:</strong> {plate_id}<br>
  <strong>Plate Description:</strong> {plate_desc}<br>
  <strong>Time Started:</strong> {start_time}<br>
  <strong>Time Finished:</strong> {finish_time}
</p>
<p>All images are saved to the Raspberry Pi's internal storage at
<code>/home/pi/Automator/data</code>. To take images off the Automator,
plug a USB pen drive into the USB hub provided. The system will automatically
copy it into your pen drive. Wait until you hear a beep and then unplug your
pen drive from the USB hub.</p>
<hr style="margin-top: 24px;">
<p style="font-size: 11px; color: #666;">
  &#x26A0;&#xFE0F; Images in the <code>captures/</code> folder are automatically
  deleted after 21 days. Run folders under <code>/home/pi/Automator/data/</code>
  are also deleted after 21 days. The data folder is kept under 5 GiB automatically
  &mdash; if it exceeds this limit, the oldest items (minimum 14 days old) are
  removed first. Export any images you want to keep permanently before the 21-day
  window closes.
</p>
</body></html>"""

        msg.attach(MIMEText(body, "html"))

        with smtplib.SMTP("smtp.nbi.ac.uk", 25, timeout=5) as server:
            server.sendmail(SMTP_FROM, recipients, msg.as_string())

        log(f"Run email sent for {plate_id}")

    except (smtplib.SMTPException, OSError) as e:
        log(f"Email sending failed: {e}")
# ---------------------------------------------------------------------
# PATHS
# ---------------------------------------------------------------------
BASE = "/home/pi/Automator/dev2"
DATA = "/home/pi/Automator/data"
CAPTURES = "/home/pi/Automator/data/captures"
NET_CAPTURES = "/mnt/AutomatorPiTSL"
RAW = "/home/pi/Automator/raw"
os.makedirs(RAW, exist_ok=True)
PLATES_JSON = os.path.join(RAW, "plates_db.json")
STATE_JSON = os.path.join(RAW, "controller_state.json")
LOG_FILE = os.path.join(RAW, "controller.log")
os.makedirs(CAPTURES, exist_ok=True)




# ---------------------------------------------------------------------
# FLASK / SOCKET.IO
# ---------------------------------------------------------------------
app = Flask(__name__, template_folder="templates", static_folder="static")
app.secret_key = os.environ.get("AUTOMATOR_SESSION_SECRET", secrets.token_hex(32))
csrf = CSRFProtect(app)
socketio = SocketIO(app, cors_allowed_origins=[
    "http://127.0.0.1:8080",
    "http://localhost:8080",
    "http://automator.local:8080",
    "http://10.0.8.72:8080",
    "http://192.168.50.2:8080",
])
# ---------------------------------------------------------------------
# AUTH (Basic Auth for LOCAL access)
# ---------------------------------------------------------------------
from functools import wraps
from flask import Response
from werkzeug.security import check_password_hash, generate_password_hash

ADMIN_PASSWORD = os.environ.get("AUTOMATOR_ADMIN_PASSWORD")
if not ADMIN_PASSWORD:
    raise RuntimeError("AUTOMATOR_ADMIN_PASSWORD is not set")

USERS = {
    "admin": generate_password_hash(ADMIN_PASSWORD)
}

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or auth.username not in USERS:
            return Response(
                "Unauthorized",
                401,
                {"WWW-Authenticate": 'Basic realm="Automator"'}
            )
        if not check_password_hash(USERS[auth.username], auth.password):
            return Response(
                "Unauthorized",
                401,
                {"WWW-Authenticate": 'Basic realm="Automator"'}
            )
        return f(*args, **kwargs)
    return decorated
# ---------------------------------------------------------------------
# GLOBAL STATE
# ---------------------------------------------------------------------
plates = {}
unresolved_detections: dict = {}   # keyed by stable position ID, see _unres_key()
schedule = []
door_open = False
imaging_active = False
_detect_running = False
_detect_lock = threading.Lock()
_scheduler_wakeup = threading.Event()  # set on abort/emergency to wake abortable_sleep immediately
last_door_state = None
pause_requested = False
paused = False
emergency_active = False
stop_cycle_requested = False
start_stop_generation = 0
imaging_task_progress = {"task": None, "stage": "idle", "stage_state": {}}
state_lock = threading.RLock()
_door_servo_retracted = threading.Event()   # set when any handler has commanded servo to 90°; cleared per plate
_pump_warmed     = False   # True after first SUCK_HOLD of a run; reset when imaging_cycle starts
_suck_hold_count = 0       # cumulative SUCK_HOLD cycles in the current run; reset when imaging_cycle starts
_led_off_time    = 0.0     # time.monotonic() of last LED-off; used by Fix D extended-settle logic
position = {"x": 0.0, "y": 0.0, "z": 0.0, "rotate": 0, "vacuum": 0, "sol": 0}
system_booting = False
notify_list = []
experiment_tag = ""
# Machine limits
X_MAX = 290.0
Y_MAX = 300.0
SAFE_Z = 50.0
LOW_Z = 0.0
LONG_GAP_PARK_SEC = 5 * 60
PLATE_STAGGER_SEC = 90          # seconds between each plate's first capture (1.5 min)
SERVO_SETTLE_SEC  = 1.5         # seconds to wait after servo PWM command before next motion
SOLENOID_PRIME_SEC = 1.0        # seconds to wait after HOLD before sending SUCK_HOLD
VACUUM_SETTLE_SEC  = 6.0        # seconds to wait after SUCK_HOLD before lifting Z
VACUUM_SETTLE_COLD_SEC = 8.0    # extended dwell for the first SUCK_HOLD of each run (cold pump)
CAMERA_SETTLE_SEC          = 1.5    # camera stabilisation delay before each capture
CAMERA_SETTLE_EXTENDED_SEC = 5.0    # extended settle after LED-off gap > threshold
CAMERA_SETTLE_DARK_THRESH  = 60.0   # seconds of LED-off that triggers extended settle
EXPERIMENT_TAG_MAX_LEN = 15

# Camera debug gate for Pi camera preview + manual continue.
# Set to True to enable the blocking debug preview before each capture.
PI_CAMERA_DEBUG_BLOCK   = False
PI_CAMERA_SENSOR_MODE   = (4608, 2592)                 # step 1: full IMX708 sensor readout
PI_CAMERA_STILL_SIZE    = (4608, 2592)                 # step 1: full IMX708 resolution
PI_CAMERA_AE_ENABLE     = False                         # disable auto-exposure; use fixed shutter
PI_CAMERA_EXPOSURE_TIME = 100000                        # µs = 100 ms; 10 full UK-mains cycles
PI_CAMERA_ANALOGUE_GAIN = 8.0                           # tune up if too dark, down if too bright
PI_CAMERA_COLOUR_GAINS  = (1.2, 2.2)                   # (red_gain, blue_gain); reduced R + boosted B to correct warm/yellow NoIR cast
PI_CAMERA_SHARPNESS     = 3.0                           # default 1.0; increase for more edge detail, max 16.0
PI_CAMERA_ZOOM_PCT      = 120                           # 1.2× hardware sensor crop via ScalerCrop; 100 = no zoom


# ---------------------------------------------------------------------
# LOGGING
# ---------------------------------------------------------------------
def log(msg: str):
    stamp = f"[{datetime.now():%Y-%m-%d %H:%M:%S}] {msg}"
    print(stamp, flush=True)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(stamp + "\n")
    except OSError:
        pass
    try:
        socketio.emit("status", {"msg": msg})
    except Exception:
        pass


def clear_dir_contents(path: str):
    if not os.path.isdir(path):
        return False, 0, 0

    removed_files = 0
    removed_dirs = 0

    for root, dirs, files in os.walk(path, topdown=False):
        for name in files:
            fp = os.path.join(root, name)
            try:
                os.remove(fp)
                removed_files += 1
            except OSError as e:
                log(f"Failed to remove file {fp}: {e}")
        for name in dirs:
            dp = os.path.join(root, name)
            try:
                if os.path.islink(dp):
                    os.unlink(dp)
                else:
                    os.rmdir(dp)
                removed_dirs += 1
            except OSError as e:
                log(f"Failed to remove directory {dp}: {e}")

    return True, removed_files, removed_dirs

# ---------------------------------------------------------------------
# SIGNAL HANDLING (systemd safe shutdown)
# ---------------------------------------------------------------------
def handle_sigterm(signum, frame):
    log("SIGTERM received — shutting down safely")
    try:
        turn_off_led_no_pulse()
        send_gcode("SET_PIN PIN=vacuum_pump VALUE=0.05")
        send_gcode("SET_PIN PIN=solenoid_valve VALUE=0.05")
    except Exception:
        pass
    os.kill(os.getpid(), signal.SIGINT)

signal.signal(signal.SIGTERM, handle_sigterm)

# ---------------------------------------------------------------------
# STATE PERSISTENCE 
# ---------------------------------------------------------------------
def save_state(complete: bool = False):
    
    state = {
        "plates": dict(plates),
        "experiment_tag": experiment_tag,
        "position": dict(position),
        "schedule": list(schedule),
        "pause_requested": pause_requested,
        "paused": paused,
        "imaging_active": imaging_active,
        "stop_cycle_requested": stop_cycle_requested,
        "unresolved_detections": dict(unresolved_detections),
        "imaging_task_progress": {
            "task": dict(imaging_task_progress.get("task", {}) or {}) if isinstance(imaging_task_progress.get("task"), dict) else imaging_task_progress.get("task"),
            "stage": imaging_task_progress.get("stage"),
            "stage_state": dict(imaging_task_progress.get("stage_state", {}) or {}),
        },
        "complete": complete,
    }
    try:
        with open(STATE_JSON, "w") as f:
            json.dump(state, f, indent=2)
    except (OSError, TypeError) as e:
        log(f"Failed to save controller state: {e}")

# ---------------------------------------------------------------------
# ACTUATORS
# ---------------------------------------------------------------------
def z_move_up():
    try:
        send_gcode(f"G1 Z{SAFE_Z:.2f} F3000")
        log(f"Z -> {SAFE_Z} mm (safe height)")
        time.sleep(0.3)
    except Exception as e:
        log(f"z_move_up failed: {e}")

def z_move_down():
    try:
        send_gcode(f"G1 Z{LOW_Z:.2f} F3000")
        log(f"Z -> {LOW_Z} mm (imaging height)")
        time.sleep(0.3)
    except Exception as e:
        log(f"z_move_down failed: {e}")

def rotate_servo(angle: int):
    try:
        send_gcode(f"ROTATE ANGLE={angle}")   # call the macro
        send_gcode("M400")                    # block until macro finishes
        time.sleep(SERVO_SETTLE_SEC)          # wait for servo PWM travel to complete
        with state_lock:
            position["rotate"] = angle
        log(f"Servo rotated -> {angle}°")
    except Exception as e:
        log(f"rotate_servo failed: {e}")

def vacuum_hold(task=None, stage=None):
    global _pump_warmed, _suck_hold_count
    try:
        send_gcode("SUCK_HOLD")
        send_gcode("M400")
        with state_lock:
            position["vacuum"] = 1
            position["sol"] = 1
        _suck_hold_count += 1
        if _suck_hold_count == 12:
            log(f"WARNING: pump has completed {_suck_hold_count} SUCK_HOLD cycles this run — "
                f"vacuum reliability may degrade. Check recent images; consider servicing pump between runs.")
        log("SUCK_HOLD macro executed")
        if not _pump_warmed:
            dwell = VACUUM_SETTLE_COLD_SEC
            log(f"Cold-pump first dwell: {VACUUM_SETTLE_COLD_SEC}s (subsequent captures use {VACUUM_SETTLE_SEC}s).")
            _pump_warmed = True
        elif task is not None and not task.get("_plate_warmed", True):
            dwell = VACUUM_SETTLE_COLD_SEC
            log(f"First grip for plate {task['id']} this sequence: extended dwell {VACUUM_SETTLE_COLD_SEC}s.")
            task["_plate_warmed"] = True
        else:
            dwell = VACUUM_SETTLE_SEC
        return abortable_sleep(dwell, task=task, stage=stage)
    except Exception as e:
        log(f"vacuum_hold failed: {e}")
        return "continue"

def vacuum_release():
    try:
        send_gcode("RELEASE")
        with state_lock:
            position["vacuum"] = 0
            position["sol"] = 0
        log("RELEASE macro executed")
        time.sleep(0.3)
    except Exception as e:
        log(f"vacuum_release failed: {e}")

def led_on():
    try:
        turn_on_led()
    except Exception:
        log("LED on failed: " + traceback.format_exc())  
    log("LED ON")
    

def led_off():
    global _led_off_time
    try:
        turn_off_led()
    except Exception:
        log("LED off failed: " + traceback.format_exc())
    _led_off_time = time.monotonic()
    log("LED OFF")

# ---------------------------------------------------------------------
# SAFE HOMING
# ---------------------------------------------------------------------
def safe_home():
    log("Running SAFE_HOME sequence...")
    try:
        send_gcode("SET_SERVO SERVO=arm_rotate ANGLE=90") # 90°
        with state_lock:
            position["rotate"] = 90
        time.sleep(0.4)
    except Exception as e:
        log(f"SAFE_HOME servo enforcement failed: {e}")
    try:
        send_gcode("G28 Z")
        log("Z homed")
        time.sleep(0.3)
        send_gcode(f"G1 Z{SAFE_Z:.2f} F3000")
        log(f"Z lifted to {SAFE_Z}")
        time.sleep(0.3)
        send_gcode("SET_VELOCITY_LIMIT ACCEL=100")
        send_gcode("G28 Y")
        log("Y homed")
        time.sleep(0.25)
        send_gcode("G28 X")
        send_gcode("SET_VELOCITY_LIMIT ACCEL=1000")
        log("X homed")
        time.sleep(0.25)
        with state_lock:
            position["z"] = SAFE_Z
    except Exception as e:
        log(f"SAFE_HOME X/Y home failed: {e}")
    log("SAFE_HOME complete.")

# ---------------------------------------------------------------------
# PAUSE HELPER
# ---------------------------------------------------------------------
def abort_requested():
    with state_lock:
        return bool(emergency_active or stop_cycle_requested)

def task_within_config_window(task):
    if not task:
        return True
    dish_id = task.get("id", "")
    with state_lock:
        plate = plates.get(dish_id, {})
        is_selected = bool(plate.get("selected", False))
        end_str = (plate.get("end") or "").strip()
    if not is_selected:
        log(f"Skipping {dish_id}: plate is no longer selected.")
        return False
    if not end_str:
        return True
    try:
        end_dt = datetime.fromisoformat(end_str)
    except ValueError:
        return True
    due_ts = task.get("due")
    if due_ts is not None:
        try:
            due_dt = datetime.fromtimestamp(float(due_ts))
        except (TypeError, ValueError, OSError):
            due_dt = datetime.now()
    else:
        due_dt = datetime.now()
    if due_dt <= end_dt:
        return True
    log(f"Skipping {dish_id}: scheduled time is after configured end time ({end_str}).")
    return False

def close_lid_then_release(stage=None, reason="safety"):
    """Close the plate lid before releasing vacuum/solenoid."""
    if stage is None:
        stage = {}
    try:
        if not _door_servo_retracted.is_set():
            log(f"{reason}: rotating servo to 90° before release.")
            rotate_servo(90)
            _door_servo_retracted.set()
        else:
            log(f"{reason}: servo already retracted by door handler — skipping rotation.")
    except Exception as e:
        log(f"{reason} servo close warning: {e}")
    try:
        vacuum_release()
    except Exception as e:
        log(f"{reason} release warning: {e}")
    try:
        if stage.get("led_on") or stage.get("_restore_led"):
            led_off()
    except Exception as e:
        log(f"{reason} LED warning: {e}")
    stage["hold_active"] = False
    stage["led_on"] = False
    stage["lid_open"] = False


def safe_pause_release(stage=None):
    """Release hardware and clear pause flags; called when a pause is lifted."""
    close_lid_then_release(stage, reason="Pause safety")

def set_imaging_task_progress(task=None, stage="idle", stage_state=None):
    global imaging_task_progress
    if stage_state is None:
        stage_state = {}
    with state_lock:
        imaging_task_progress = {
            "task": dict(task) if isinstance(task, dict) else task,
            "stage": stage,
            "stage_state": dict(stage_state),
        }

def apply_pause_state(task=None, stage=None):
    """Apply or clear the pause state under the state lock, emitting a SocketIO event if state changed."""
    global paused
    with state_lock:
        want_pause = bool(pause_requested)
    if not want_pause:
        with state_lock:
            if paused:
                paused = False
        return "continue"

    if stage is None:
        stage = {}

    with state_lock:
        need_pause_setup = not paused
        paused = True
    if need_pause_setup:
        stage["_restore_led"] = bool(stage.get("led_on", False))
        stage["_restore_hold"] = bool(stage.get("hold_active", False)) and not stage.get("_post_capture", False)
        stage["_restore_lid_open"] = bool(stage.get("lid_open", False))
        log("⏸ Imaging paused")
        safe_pause_release(stage)
        if stage.get("hold_active"):
            stage["_regrab_needed"] = True
        stage["_post_pause_release_done"] = True

    while True:
        with state_lock:
            if emergency_active or stop_cycle_requested:
                paused = False
                stage["_restore_led"] = False
                stage["_restore_hold"] = False
                stage["_restore_lid_open"] = False
                return "abort"
            if not pause_requested:
                break
        _scheduler_wakeup.wait(timeout=0.1)
        _scheduler_wakeup.clear()

    try:
        if stage.get("_restore_led"):
            led_on()
            stage["led_on"] = True
        if stage.get("_restore_hold") and stage.get("_post_pause_release_done"):
            send_gcode("HOLD")
            vacuum_hold()
            stage["hold_active"] = True
        if stage.get("_restore_lid_open"):
            rotate_servo(0)
            stage["lid_open"] = True
    except Exception as e:
        log(f"Pause restore warning: {e}")
    stage["_restore_led"] = False
    stage["_restore_hold"] = False
    stage["_restore_lid_open"] = False
    stage["_post_pause_release_done"] = False
    with state_lock:
        paused = False
    log("▶ Imaging resumed")
    return "continue"

def abortable_sleep(seconds, task=None, stage=None, step=0.1):
    end_ts = time.time() + max(0.0, float(seconds))
    while time.time() < end_ts:
        if abort_requested():
            return "abort"
        pause_state = apply_pause_state(task=task, stage=stage)
        if pause_state != "continue":
            return pause_state
        remaining = end_ts - time.time()
        sleep_for = step if remaining > step else remaining
        if sleep_for <= 0:
            break
        _scheduler_wakeup.wait(timeout=sleep_for)
        _scheduler_wakeup.clear()
    return "continue"

def pause_checkpoint(task=None, stage=None):
    if abort_requested():
        return "abort"
    return apply_pause_state(task=task, stage=stage)

# ---------------------------------------------------------------------
# INIT SYSTEM
# ---------------------------------------------------------------------
def init_system():
    global plates, position, schedule, system_booting, door_open, last_door_state, experiment_tag, unresolved_detections
    log("=== SYSTEM INITIALISING ===")
    system_booting = True
    door_open = False
    last_door_state = None

    if os.path.exists(STATE_JSON):
        try:
            with open(STATE_JSON, "r") as f:
                state = json.load(f)
            if not state.get("complete", False):
                with state_lock:
                    plates = state.get("plates", {}).copy()
                    experiment_tag = sanitize_experiment_tag(state.get("experiment_tag", ""))
                    position = state.get("position", position).copy()
                    schedule = state.get("schedule", []).copy()
                    unresolved_detections = state.get("unresolved_detections", {})
                log(f"[RESTORE] Loaded {len(plates)} plates.")
                if experiment_tag:
                    log(f"[RESTORE] Experiment tag restored: {experiment_tag}")
                socketio.emit("resume_available", {"plates": plates, "schedule": schedule})
            else:
                log("[RESTORE] Previous session complete – removing state file.")
                os.remove(STATE_JSON)
        except (OSError, json.JSONDecodeError, KeyError, ValueError) as e:
            log(f"[RESTORE ERROR] {e}")
    else:
        log("[RESTORE] No saved state found. Starting clean.")

    try:
        send_gcode("M115")
        log("Klipper connected.")
    except Exception as e:
        log(f"Klipper M115 failed: {e}")

    safe_home()

    try:
        send_gcode("SET_PIN PIN=vacuum_pump VALUE=0.05")
        send_gcode("SET_PIN PIN=solenoid_valve VALUE=0.05")
        rotate_servo(90)
        log("Actuators reset, servo at 90°.")
    except Exception as e:
        log(f"Actuator reset error: {e}")

    init_door_sensor()
    log("Door sensor initialised.")
    threading.Thread(target=door_monitor, daemon=True).start()
    threading.Thread(target=position_monitor, daemon=True).start()
    threading.Thread(target=_poll_services, daemon=True).start()
    threading.Thread(target=metadata_worker, daemon=True).start()
    system_booting = False
    log("=== SYSTEM READY ===")

# ---------------------------------------------------------------------
# DOOR MONITOR
# ---------------------------------------------------------------------
def door_monitor():
    global system_booting, door_open, last_door_state, pause_requested
    while True:
        try:
            if system_booting:
                time.sleep(0.5)
                continue
            s = door_state()
            with state_lock:
                changed = (s != last_door_state)
                if changed:
                    door_open = s
                    last_door_state = s
            if not changed:
                time.sleep(0.5)
                continue
            if s:
                time.sleep(3.0)
                re_check = door_state()
                if not re_check:
                    log("False door trigger ignored (resolved in <3 s — likely servo EMI).")
                    with state_lock:
                        door_open = False
                        last_door_state = False
                    continue
                log("Door opened — pausing imaging.")
                with state_lock:
                    pause_requested = True
                    current_rotate = position.get("rotate", 90)
                if current_rotate != 90:
                    if not _door_servo_retracted.is_set():
                        _door_servo_retracted.set()
                        log("Door opened — retracting servo to 90° before vacuum release.")
                        rotate_servo(90)
                    else:
                        log("Door opened — servo already being retracted, skipping duplicate call.")
                send_gcode("SET_PIN PIN=vacuum_pump VALUE=0.05")
                send_gcode("SET_PIN PIN=solenoid_valve VALUE=0.05")
            else:
                log("Door closed — system ready.")
                with state_lock:
                    pause_requested = False
        except Exception:
            log("door_monitor except: " + traceback.format_exc())
        time.sleep(0.5)

# ---------------------------------------------------------------------
# USB SCAN + DB BUILD
# ---------------------------------------------------------------------
_UNRES_GRID_MM = 5

def _unres_key(x_mm: float, y_mm: float) -> str:
    gx = round(round(x_mm / _UNRES_GRID_MM) * _UNRES_GRID_MM)
    gy = round(round(y_mm / _UNRES_GRID_MM) * _UNRES_GRID_MM)
    return f"unres_{gx:03d}x{gy:03d}"


def _next_plate_key(*plate_maps) -> str:
    used = set()
    for pm in plate_maps:
        for k in pm:
            if k.startswith("plate_") and k[6:].isdigit():
                used.add(int(k[6:]))
    n = 1
    while n in used:
        n += 1
    return f"plate_{n:02d}"


def reset_preview_detection_state():
    global plates, unresolved_detections, schedule
    with state_lock:
        plates = {}
        unresolved_detections = {}
        schedule = []
        save_state(complete=True)
    reset_fallback_tracking()
    log("Preview scan state reset; previous plate and unresolved values discarded.")


def run_usb_scan_with_unresolved(save_path=None):
    save_path = save_path or os.path.expanduser(
        "~/Automator/dev2/static/workspace_overlay.png"
    )
    seen_qr: set = set()
    resolved: dict = {}
    unresolved: dict = {}

    idx = find_camera()
    cap = cv2.VideoCapture(idx)
    try:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        captured_frames = []
        for fi in range(FALLBACK_SCAN_FRAME_COUNT):
            if fi > 0:
                time.sleep(FALLBACK_SCAN_FRAME_DELAY_SEC)
            ret, raw = cap.read()
            if not ret:
                if fi == 0:
                    log("USB scan (full): camera capture failed")
                    return {}, {}
                log(f"USB scan: frame {fi + 1} failed; proceeding with {fi} frame(s)")
                break
            f = cv2.flip(raw, 1)
            f = f[120:900, 260:1600]
            captured_frames.append(f)
    finally:
        cap.release()

    if not captured_frames:
        log("USB scan (full): no frames captured")
        return {}, {}

    frame = captured_frames[-1]

    if not os.path.exists(YOLO_MODEL):
        log(f"USB scan (full): YOLO model not found: {YOLO_MODEL}")
        return {}, {}

    ort_sess = ort.InferenceSession(YOLO_MODEL, providers=["CPUExecutionProvider"])
    in_name = ort_sess.get_inputs()[0].name
    in_size = ort_sess.get_inputs()[0].shape[2]
    blob, scale, dx, dy, ow, oh = preprocess(frame, in_size)
    preds = ort_sess.run(None, {in_name: blob})
    dets = postprocess(preds, scale, dx, dy, ow, oh)
    log(f"USB scan (full): YOLO detected {len(dets)} plates")

    conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    cur = conn.cursor()
    idsys = PlateID(cur)

    dets = sorted(dets, key=lambda d: (d[1], d[0]))
    for i, (x1, y1, x2, y2, conf) in enumerate(dets, start=1):
        x1, y1, x2, y2 = map(int, (x1, y1, x2, y2))
        roi_raw = frame[y1:y2, x1:x2]
        px_per_mm = mm_to_px_local(x2 - x1, y2 - y1)
        radius_px = int(50 * px_per_mm * 0.92)
        cx_local = (x2 - x1) // 2
        cy_local = (y2 - y1) // 2
        circle = crop_circular_roi(roi_raw, cx_local, cy_local, radius_px)
        zoom = zoom_roi(circle, scale=3.0)
        gray = normalise_for_qr(zoom)

        payloads = detect_qr(gray)
        if not payloads:
            payloads = detect_qr(255 - gray)

        mmx, mmy = px_to_mm((x1 + x2) / 2, (y1 + y2) / 2)
        if mmx is None or mmy is None:
            continue

        if not payloads:
            reason = "QR unreadable"
        else:
            payload = payloads[0]
            valid, reason = validate_micro_qr(payload)
            if valid and payload not in seen_qr:
                seen_qr.add(payload)
                pid = idsys.get_id([payload])
                key = f"plate_{i:02d}"
                resolved[key] = {
                    "id": pid,
                    "x_mm": round(mmx, 2),
                    "y_mm": round(mmy, 2),
                    "confidence": round(conf, 3),
                    "desc": payload,
                    "detection_source": "yolo",
                    "position_source": "existing_yolo_homography",
                    "identity_source": "qr",
                }
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                cv2.putText(
                    frame, f"{key} ID{pid}",
                    (x1, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2,
                )
                continue
            reason = reason if not valid else "duplicate QR"

        ukey = _unres_key(mmx, mmy)
        unresolved[ukey] = {
            "track_id": ukey,
            "status": "unresolved",
            "qr_data": None,
            "bbox": [x1, y1, x2, y2],
            "centre_px": [(x1 + x2) // 2, (y1 + y2) // 2],
            "position_mm": {"x": round(mmx, 2), "y": round(mmy, 2)},
            "position_source": "existing_yolo_homography",
            "detection_source": "yolo",
            "identity_source": None,
            "confidence": round(conf, 3),
        }
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 165, 255), 2)
        cv2.putText(
            frame, f"No QR ({reason})",
            (x1, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 165, 255), 2,
        )
        cv2.putText(
            frame, f"X={round(mmx,1)} Y={round(mmy,1)} mm",
            (x1 + 4, y1 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2,
        )
        log(f"Plate {i}: {reason} at ({mmx:.1f},{mmy:.1f}) -> {ukey}")

    conn.commit()
    conn.close()

    if FALLBACK_DETECTION_ENABLED:
        scan_id = begin_fallback_scan()
        retired = retire_fallback_tracks_overlapping_yolo(dets)
        if retired:
            log(f"Fallback: {len(retired)} track(s) superseded by YOLO.")
        for sub_frame in captured_frames:
            cands = detect_geometric_plate_candidates(sub_frame, dets)
            update_fallback_tracks(cands, scan_id)
        fallback_plates = get_confirmed_fallback_plates_for_scan(scan_id)
        for fb in fallback_plates:
            fb_cx, fb_cy = fb["centre_px"]
            mmx, mmy = px_to_mm(fb_cx, fb_cy)
            if mmx is None or mmy is None:
                continue
            fb_key = fb["track_id"]
            if fb_key in unresolved or fb_key in resolved:
                continue
            bx1, by1, bx2, by2 = fb["bbox"]
            roi_raw = frame[max(0, by1):by2, max(0, bx1):bx2]
            if roi_raw.size == 0:
                qr_payloads = []
            else:
                px_per_mm = mm_to_px_local(bx2 - bx1, by2 - by1)
                r_px = int(50 * px_per_mm * 0.92)
                circle = crop_circular_roi(roi_raw, (bx2 - bx1) // 2, (by2 - by1) // 2, r_px)
                zoom = zoom_roi(circle, scale=3.0)
                gray = normalise_for_qr(zoom)
                qr_payloads = detect_qr(gray) or detect_qr(255 - gray)
            if qr_payloads:
                payload = qr_payloads[0]
                valid, _ = validate_micro_qr(payload)
                if valid and payload not in seen_qr:
                    seen_qr.add(payload)
                    try:
                        fconn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
                        try:
                            fconn.execute("PRAGMA journal_mode=WAL")
                            fb_pid = PlateID(fconn.cursor()).get_id([payload])
                            fconn.commit()
                        finally:
                            fconn.close()
                    except Exception as e:
                        log(f"SQLite error for fallback QR {payload}: {e}")
                        continue
                    rkey = _next_plate_key(resolved)
                    resolved[rkey] = {
                        "id": fb_pid, "x_mm": round(mmx, 2), "y_mm": round(mmy, 2),
                        "confidence": None, "desc": payload,
                        "detection_source": "geometric_fallback",
                        "position_source": "existing_homography",
                        "identity_source": "qr",
                        "source_track_id": fb_key,
                    }
                    cv2.rectangle(frame, (bx1, by1), (bx2, by2), (0, 200, 0), 2)
                    cv2.putText(frame, f"{rkey} [FB-QR]", (bx1, by1 - 6),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 200, 0), 2)
                    log(f"Fallback {fb_key} QR decoded -> {rkey} ({payload})")
                    continue
            unresolved[fb_key] = {
                "track_id": fb_key,
                "status": "unresolved",
                "qr_data": None,
                "bbox": fb["bbox"],
                "centre_px": [fb_cx, fb_cy],
                "position_mm": {"x": round(mmx, 2), "y": round(mmy, 2)},
                "position_source": "existing_homography",
                "detection_source": "geometric_fallback",
                "identity_source": None,
                "confidence": None,
                "source_track_id": fb_key,
            }
            cv2.rectangle(frame, (bx1, by1), (bx2, by2), (255, 0, 200), 2)
            cv2.putText(frame, f"{fb_key} [FALLBACK]", (bx1, by1 - 6),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 0, 200), 2)
            cv2.putText(frame, f"X={round(mmx,1)} Y={round(mmy,1)} mm",
                        (bx1 + 4, by1 + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)
            log(f"Geometric fallback plate {fb_key} at ({mmx:.1f},{mmy:.1f}) -> unresolved")

    cv2.imwrite(save_path, frame)
    log(f"Overlay saved -> {save_path}")
    return resolved, unresolved


def run_usb_scan():
    log("Running USB workspace scan ...")
    try:
        detected = detect_plates()
        if not isinstance(detected, dict):
            detected = {}
        log(f"USB scan detected {len(detected)} plates.")
        return detected
    except Exception as e:
        log(f"USB scan failed: {e}")
        return {}


def detect_and_build_db():
    global plates, unresolved_detections
    log("Running USB workspace scan ...")
    try:
        resolved_raw, new_unresolved = run_usb_scan_with_unresolved()
    except Exception as e:
        log(f"USB scan failed: {e}")
        resolved_raw, new_unresolved = {}, {}

    with state_lock:
        plates = {}
        for pid, p in resolved_raw.items():
            try:
                mmx = float(p.get("x_mm", 0.0))
                mmy = float(p.get("y_mm", 0.0))
            except (TypeError, ValueError):
                mmx, mmy = 0.0, 0.0
            machine_x = max(0, min(X_MAX, mmx))
            machine_y = max(0, min(Y_MAX, mmy))
            plates[pid] = {
                "id": p.get("id", 0),
                "x_mm": round(machine_x, 2),
                "y_mm": round(machine_y, 2),
                "confidence": p.get("confidence", 0),
                "desc": p.get("desc", ""),
                "interval": 30, "count": 1, "end": "",
                "selected": False,
                "start_dt": None,
                "detection_source": p.get("detection_source", "yolo"),
                "position_source": p.get("position_source", "existing_yolo_homography"),
                "identity_source": p.get("identity_source", "qr"),
                "source_track_id": p.get("source_track_id"),
            }

        resolved_keys = {_unres_key(p["x_mm"], p["y_mm"]) for p in plates.values()}
        covered_mm = {(p["x_mm"], p["y_mm"]) for p in plates.values()}

        def _pos_covered(x: float, y: float) -> bool:
            return any(abs(x - cx) < _UNRES_GRID_MM and abs(y - cy) < _UNRES_GRID_MM
                       for cx, cy in covered_mm)

        prev_fallback_keys = {k for k in unresolved_detections if k.startswith("FALLBACK-")}
        unresolved_detections = {
            k: v for k, v in new_unresolved.items()
            if k not in resolved_keys
            and not _pos_covered(
                v.get("position_mm", {}).get("x", 0.0),
                v.get("position_mm", {}).get("y", 0.0),
            )
        }
        for unres_id, unres in unresolved_detections.items():
            pos = unres.get("position_mm", {})
            new_key = _next_plate_key(plates)
            plates[new_key] = {
                "id": 0,
                "x_mm": round(float(pos.get("x", 0.0)), 2),
                "y_mm": round(float(pos.get("y", 0.0)), 2),
                "confidence": unres.get("confidence"),
                "desc": "",
                "interval": 30, "count": 1, "end": "",
                "selected": False,
                "start_dt": None,
                "identity_source": "unresolved",
                "detection_source": unres.get("detection_source", "yolo"),
                "position_source": unres.get("position_source", "existing_yolo_homography"),
                "source_track_id": unres.get("source_track_id", unres_id),
                "unresolved_track_id": unres_id,
            }
        new_fallback_keys = {k for k in unresolved_detections if k.startswith("FALLBACK-")}
        for merged_key in prev_fallback_keys - new_fallback_keys:
            log(f"Fallback {merged_key} superseded by YOLO or position resolved.")

    log(f"Plate DB ready: {len(resolved_raw)} QR-resolved, {len(unresolved_detections)} QR-unreadable.")
    try:
        with open(PLATES_JSON, "w") as f:
            json.dump(plates, f, indent=2)
    except (OSError, TypeError) as e:
        log(f"Failed to write plates DB: {e}")
    raw_path = os.path.join(RAW, "plates_raw.json")
    with open(raw_path, "w") as f:
        json.dump(resolved_raw, f, indent=2)
    with state_lock:
        save_state()
    return plates

# ---------------------------------------------------------------------
# IMAGE NAMING HELPERS
# ---------------------------------------------------------------------

def parse_qr_payload(payload: str):
    # Expected: YYYYMMDD_STRAIN_MEDIA_COND_VIEW
    parts = payload.split("_", 4)
    if len(parts) != 5:
        return None

    try:
        start_date = datetime.strptime(parts[0], "%Y%m%d")
    except ValueError:
        return None

    return {
        "start_date": start_date,
        "strain": parts[1],
        "media": parts[2],
        "cond": parts[3],
        "view": parts[4]
    }


def sanitize_plate_detail(value: str, fallback: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9+-]+", "_", str(value or "").strip())
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned or fallback


def parse_plate_details(payload: str, fallback_start: datetime):
    qr_data = parse_qr_payload(payload)
    if qr_data:
        return {
            "start_date": qr_data["start_date"],
            "strain": sanitize_plate_detail(qr_data["strain"], "UNREADABLEQR"),
            "media": sanitize_plate_detail(qr_data["media"], "UNKNOWN"),
            "cond": sanitize_plate_detail(qr_data["cond"], "UNKNOWN"),
            "view": sanitize_plate_detail(qr_data["view"], "TOP"),
            "source": "qr",
        }

    parts = [p.strip() for p in str(payload or "").split("_") if p.strip()]
    start_date = fallback_start
    if parts and re.fullmatch(r"\d{8}", parts[0]):
        try:
            start_date = datetime.strptime(parts.pop(0), "%Y%m%d")
        except ValueError:
            start_date = fallback_start

    if len(parts) >= 4:
        strain, media, cond, view = parts[0], parts[1], parts[2], "_".join(parts[3:])
    elif len(parts) == 3:
        strain, media, cond, view = parts[0], parts[1], parts[2], "TOP"
    elif len(parts) == 2:
        strain, media, cond, view = parts[0], parts[1], "UNKNOWN", "TOP"
    elif len(parts) == 1:
        strain, media, cond, view = parts[0], "UNKNOWN", "UNKNOWN", "TOP"
    else:
        strain, media, cond, view = "UNREADABLEQR", "UNKNOWN", "UNKNOWN", "TOP"

    return {
        "start_date": start_date,
        "strain": sanitize_plate_detail(strain, "UNREADABLEQR")[:24],
        "media": sanitize_plate_detail(media, "UNKNOWN")[:24],
        "cond": sanitize_plate_detail(cond, "UNKNOWN")[:24],
        "view": sanitize_plate_detail(view, "TOP")[:24],
        "source": "manual",
    }


def compute_day_index(start_date, now, interval_sec):
    # Day index = calendar days since start date
    delta_days = (now.date() - start_date.date()).days
    idx = delta_days + 1
    return f"d{idx:02d}"


def ensure_dirs(base_dir, subfolder):
    path = os.path.join(base_dir, subfolder)
    os.makedirs(path, exist_ok=True)
    return path


def sanitize_experiment_tag(value):
    if value is None:
        return ""
    tag = str(value).replace("\r", " ").replace("\n", " ").strip()
    if len(tag) > EXPERIMENT_TAG_MAX_LEN:
        tag = tag[:EXPERIMENT_TAG_MAX_LEN]
    return tag


def format_tag_for_filename(tag: str) -> str:
    if tag is None:
        return ""
    cleaned = str(tag).strip().lower()
    if not cleaned:
        return ""
    cleaned = re.sub(r"\s+", "_", cleaned)
    cleaned = re.sub(r"[^a-z0-9_-]", "", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned)
    cleaned = re.sub(r"-+", "-", cleaned)
    cleaned = cleaned.strip("_-")
    if not cleaned:
        return ""
    return cleaned[:20]


def write_experiment_tag_exif(image_path: str, tag: str):
    safe_tag = sanitize_experiment_tag(tag)
    if not safe_tag:
        return False
    lower = (image_path or "").lower()
    if not (lower.endswith(".jpg") or lower.endswith(".jpeg")):
        return False

    # EXIF tag ids:
    # 270   -> ImageDescription
    # 37510 -> UserComment
    # 40092 -> XPComment
    # 40094 -> XPKeywords
    try:
        with Image.open(image_path) as img:
            exif = img.getexif()
            exif[270] = safe_tag
            exif[37510] = b"ASCII\x00\x00\x00" + safe_tag.encode("ascii", "ignore")
            exif[40092] = (f"Automator experiment tag: {safe_tag}\x00").encode("utf-16le")
            exif[40094] = (safe_tag + "\x00").encode("utf-16le")
            exif_bytes = exif.tobytes()

            try:
                # Preserve source JPEG quantization/subsampling where possible.
                img.save(
                    image_path,
                    exif=exif_bytes,
                    quality="keep",
                    subsampling="keep",
                    qtables="keep",
                )
            except Exception:
                # Fallback path if "keep" options are unsupported by current Pillow build.
                img.save(image_path, exif=exif_bytes)
        return True
    except Exception as e:
        log(f"EXIF tag write failed for {image_path}: {e}")
        return False


def write_standard_keywords(image_path: str):
    lower = (image_path or "").lower()
    if not (lower.endswith(".jpg") or lower.endswith(".jpeg")):
        return

    def _clean_to_tags(raw_value):
        if raw_value is None:
            return []

        values = raw_value if isinstance(raw_value, list) else [raw_value]
        out = []
        for item in values:
            text = str(item or "")
            text = text.replace("\x00", " ").replace("\r", " ").replace("\n", " ")
            text = text.strip()
            if not text:
                continue

            text = re.sub(r"^\s*automator\s+experiment\s+tag\s*:\s*", "", text, flags=re.IGNORECASE)
            if not text:
                continue

            # Split common separators into candidate tags.
            parts = re.split(r"[;,|]+", text)
            if len(parts) == 1:
                parts = [text]

            for part in parts:
                token = part.strip().lower()
                token = re.sub(r"\s+", "_", token)
                token = re.sub(r"_+", "_", token).strip("_")
                if token:
                    out.append(token)
        return out

    try:
        read_cmd = [
            "exiftool",
            "-j",
            "-XPKeywords",
            "-XPComment",
            "-Keywords",
            image_path
        ]
        read_res = subprocess.run(read_cmd, capture_output=True, text=True, check=True)
        rows = json.loads(read_res.stdout or "[]")
        meta = rows[0] if rows and isinstance(rows[0], dict) else {}

        raw_candidates = [
            meta.get("Keywords"),
            meta.get("XPKeywords"),
            meta.get("XPComment"),
            experiment_tag,
        ]

        tags = []
        seen = set()
        for raw in raw_candidates:
            for t in _clean_to_tags(raw):
                if t and t not in seen:
                    seen.add(t)
                    tags.append(t)

        if not tags:
            return

        write_cmd = ["exiftool", "-overwrite_original", "-Keywords="]
        for t in tags:
            write_cmd.append(f"-Keywords+={t}")
        write_cmd.append(image_path)
        subprocess.run(write_cmd, capture_output=True, text=True, check=True)
        log(f"Standard Keywords written: {tags}")
    except Exception as e:
        log(f"Failed to write standard keywords: {e}")


def write_path_tag_metadata(path: str, tag: str):
    safe_tag = sanitize_experiment_tag(tag)
    if not safe_tag or not path:
        return False

    wrote_any = False

    def _set_xattr_bytes(attr_name, raw_bytes):
        if not raw_bytes:
            return False
        if hasattr(os, "setxattr"):
            try:
                os.setxattr(path, attr_name, raw_bytes)
                return True
            except Exception:
                pass
        # macOS/Unix fallback using xattr tool with hex payload.
        return _run_quiet(["xattr", "-wx", attr_name, raw_bytes.hex(), path])

    def _run_quiet(cmd):
        try:
            subprocess.run(
                cmd,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return True
        except Exception:
            return False

    # Generic Unix xattrs first.
    xattr_pairs = [
        ("user.experiment_tag", safe_tag.encode("utf-8")),
        ("user.comment", f"Automator experiment tag: {safe_tag}".encode("utf-8")),
        ("user.xdg.tags", safe_tag.encode("utf-8")),
    ]

    if hasattr(os, "setxattr"):
        for key, value in xattr_pairs:
            try:
                os.setxattr(path, key, value)
                wrote_any = True
            except Exception:
                pass
    else:
        # Linux fallback via attr tools.
        for key, value in xattr_pairs:
            value_text = value.decode("utf-8", "ignore")
            if _run_quiet(["setfattr", "-n", key, "-v", value_text, path]):
                wrote_any = True
            elif _run_quiet(["xattr", "-w", key, value_text, path]):
                wrote_any = True

    # Linux desktop metadata fallback (shown in some file-manager "Properties").
    if _run_quiet(["gio", "set", path, "metadata::annotation", f"Automator experiment tag: {safe_tag}"]):
        wrote_any = True

    # macOS Finder metadata tags/comments.
    try:
        import plistlib
        # Finder tag strings use: "TagName\\n<colorIndex>" where color is 0..7.
        # Use blue (4) so tags are visibly marked in Finder.
        finder_tags_blob = plistlib.dumps(
            [f"{safe_tag}\n4"],
            fmt=plistlib.FMT_BINARY
        )
        finder_keywords_blob = plistlib.dumps(
            [safe_tag],
            fmt=plistlib.FMT_BINARY
        )
        finder_comment_blob = plistlib.dumps(
            f"Automator experiment tag: {safe_tag}",
            fmt=plistlib.FMT_BINARY
        )

        if _set_xattr_bytes("com.apple.metadata:kMDItemFinderComment", finder_comment_blob):
            wrote_any = True
        if _set_xattr_bytes("com.apple.metadata:_kMDItemUserTags", finder_tags_blob):
            wrote_any = True
        if _set_xattr_bytes("com.apple.metadata:kMDItemKeywords", finder_keywords_blob):
            wrote_any = True

        # Finder frequently writes this 32-byte marker alongside tag metadata.
        # Adding it improves compatibility with Finder tag rendering on some setups.
        if _set_xattr_bytes("com.apple.FinderInfo", bytes(32)):
            wrote_any = True
    except Exception:
        pass

    # Direct Finder fallback (only when running on macOS with Finder available).
    if _run_quiet([
        "osascript",
        "-e",
        "on run argv",
        "-e",
        "set p to POSIX file (item 1 of argv)",
        "-e",
        "set t to item 2 of argv",
        "-e",
        "tell application \"Finder\" to set tags of p to {t}",
        "-e",
        "end run",
        path,
        safe_tag,
    ]):
        wrote_any = True

    return wrote_any


def _apply_preview_zoom(frame_bgr, zoom_pct: int):
    zoom_pct = max(100, min(300, int(zoom_pct)))
    if zoom_pct == 100:
        return frame_bgr
    h, w = frame_bgr.shape[:2]
    factor = zoom_pct / 100.0
    crop_w = max(32, int(w / factor))
    crop_h = max(32, int(h / factor))
    x0 = max(0, (w - crop_w) // 2)
    y0 = max(0, (h - crop_h) // 2)
    cropped = frame_bgr[y0:y0 + crop_h, x0:x0 + crop_w]
    return cv2.resize(cropped, (w, h), interpolation=cv2.INTER_LINEAR)


def _apply_camera_zoom(cam: Picamera2, zoom_pct: int):
    try:
        crop_max = cam.camera_properties.get("ScalerCropMaximum")
        if not crop_max:
            return
        x, y, w, h = [int(v) for v in crop_max]
        factor = max(1.0, min(3.0, float(zoom_pct) / 100.0))
        crop_w = max(32, int(w / factor))
        crop_h = max(32, int(h / factor))
        nx = x + (w - crop_w) // 2
        ny = y + (h - crop_h) // 2
        cam.set_controls({"ScalerCrop": (nx, ny, crop_w, crop_h)})
    except Exception as e:
        log(f"Debug zoom control not applied: {e}")


def run_pi_camera_debug_gate(cam: Picamera2, dish_id: str):
    window = "Pi Camera Debug Preview"
    cv2.namedWindow(window, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(window, 1280, 720)

    cv2.createTrackbar("Brightness x100", window, 100, 200, lambda _v: None)
    cv2.createTrackbar("Contrast x100", window, 100, 200, lambda _v: None)
    cv2.createTrackbar("Sharpness x10", window, 10, 200, lambda _v: None)
    cv2.createTrackbar("Zoom %", window, 100, 300, lambda _v: None)
    cv2.createTrackbar("Manual Focus x100", window, 100, 1000, lambda _v: None)

    state = {
        "continue": False,
        "focus_mode": "autofocus",  # autofocus | manual
    }

    buttons = {
        "autofocus": (20, 20, 220, 60),
        "manual": (240, 20, 440, 60),
        "continue": (460, 20, 700, 60),
    }

    def in_rect(x, y, rect):
        x1, y1, x2, y2 = rect
        return x1 <= x <= x2 and y1 <= y <= y2

    def on_mouse(event, x, y, _flags, _param):
        if event != cv2.EVENT_LBUTTONDOWN:
            return
        if in_rect(x, y, buttons["autofocus"]):
            state["focus_mode"] = "autofocus"
        elif in_rect(x, y, buttons["manual"]):
            state["focus_mode"] = "manual"
        elif in_rect(x, y, buttons["continue"]):
            state["continue"] = True

    cv2.setMouseCallback(window, on_mouse)

    last_values = {
        "brightness": None,
        "contrast": None,
        "sharpness": None,
        "zoom": None,
        "focus_mode": None,
        "manual_focus": None,
    }

    while not state["continue"]:
        frame = cam.capture_array()
        preview = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

        brightness_tb = cv2.getTrackbarPos("Brightness x100", window)
        contrast_tb = cv2.getTrackbarPos("Contrast x100", window)
        sharpness_tb = cv2.getTrackbarPos("Sharpness x10", window)
        zoom_tb = cv2.getTrackbarPos("Zoom %", window)
        manual_focus_tb = cv2.getTrackbarPos("Manual Focus x100", window)

        brightness = (brightness_tb - 100) / 100.0
        contrast = max(0.0, contrast_tb / 100.0)
        sharpness = max(0.0, sharpness_tb / 10.0)
        zoom_pct = max(100, zoom_tb)
        manual_focus = manual_focus_tb / 100.0
        focus_mode = state["focus_mode"]

        if (
            last_values["brightness"] != brightness
            or last_values["contrast"] != contrast
            or last_values["sharpness"] != sharpness
            or last_values["focus_mode"] != focus_mode
            or (focus_mode == "manual" and last_values["manual_focus"] != manual_focus)
        ):
            ctrl = {
                "Brightness": brightness,
                "Contrast": contrast,
                "Sharpness": sharpness,
            }
            if focus_mode == "autofocus":
                ctrl["AfMode"] = controls.AfModeEnum.Continuous
            else:
                ctrl["AfMode"] = controls.AfModeEnum.Manual
                ctrl["LensPosition"] = manual_focus
            try:
                cam.set_controls(ctrl)
            except Exception as e:
                log(f"Debug camera control update failed: {e}")

        if last_values["zoom"] != zoom_pct:
            _apply_camera_zoom(cam, zoom_pct)

        preview = _apply_preview_zoom(preview, zoom_pct)

        max_w = 1280
        if preview.shape[1] > max_w:
            scale = max_w / float(preview.shape[1])
            preview = cv2.resize(preview, (max_w, int(preview.shape[0] * scale)))

        # Draw UI buttons (autofocus/manual are mutually exclusive).
        for key in ("autofocus", "manual", "continue"):
            x1, y1, x2, y2 = buttons[key]
            active = (
                (key == "autofocus" and focus_mode == "autofocus")
                or (key == "manual" and focus_mode == "manual")
            )
            if key == "continue":
                color = (60, 170, 60)
            elif active:
                color = (220, 180, 40)
            else:
                color = (90, 90, 90)
            cv2.rectangle(preview, (x1, y1), (x2, y2), color, -1)
            cv2.rectangle(preview, (x1, y1), (x2, y2), (20, 20, 20), 2)

        cv2.putText(preview, "Autofocus", (40, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        cv2.putText(preview, "Manual Focus", (255, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
        cv2.putText(preview, "Continue", (535, 48), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)

        cv2.putText(
            preview,
            f"Debug capture gate for {dish_id}: adjust controls, then click Continue.",
            (20, 90),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.65,
            (230, 230, 230),
            2,
        )

        focus_note = (
            "Focus: AUTOFocus active (manual focus disabled)"
            if focus_mode == "autofocus"
            else f"Focus: MANUAL active at lens position {manual_focus:.2f} (autofocus disabled)"
        )
        cv2.putText(preview, focus_note, (20, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (230, 230, 230), 2)

        cv2.imshow(window, preview)
        key = cv2.waitKey(30) & 0xFF
        if key == ord("c"):
            state["continue"] = True

        last_values["brightness"] = brightness
        last_values["contrast"] = contrast
        last_values["sharpness"] = sharpness
        last_values["zoom"] = zoom_pct
        last_values["focus_mode"] = focus_mode
        last_values["manual_focus"] = manual_focus

    cv2.destroyWindow(window)
# ---------------------------------------------------------------------
# CAPTURE
# ---------------------------------------------------------------------
def capture_image(cam: Picamera2, dish_id: str, task: dict):
    with state_lock:
        qr_payload = plates.get(dish_id, {}).get("desc", "").strip()
        capture_tag = experiment_tag

    now = datetime.now()
    try:
        fallback_start = datetime.fromisoformat(task.get("start_dt", ""))
    except (TypeError, ValueError):
        fallback_start = now
    qr_data = parse_plate_details(qr_payload, fallback_start)
    if qr_data.get("source") == "manual":
        log(f"Using manually entered plate details for {dish_id}: {qr_payload or 'UNREADABLEQR'}")

    capture_time = now.strftime("%H%M%S")
    capture_ms = f"{now.microsecond//1000:03d}"

    # Dates
    capture_date = now.strftime("%Y%m%d")
    ddmmm = now.strftime("%d%b").upper()

    # Plate
    # Extract numeric part from plate ID (e.g. "plate_01" -> 1)
    num = "".join(c for c in dish_id if c.isdigit())
    plate_no = f"P{int(num):03d}" if num else f"P000"

    # Day index
    start_dt = datetime.fromisoformat(task["start_dt"])
    d_index = compute_day_index(
        qr_data["start_date"],
        now,
        task["interval"]
    )

    # Parts
    strain = qr_data["strain"]
    media = qr_data["media"]
    cond = qr_data["cond"]
    view = qr_data["view"]

    # Folder (base structure preserved; optional searchable tag suffix added)
    folder_base = f"{ddmmm}_{strain}_{media}_{cond}"
    folder_tag_part = format_tag_for_filename(capture_tag)
    if folder_tag_part:
        folder_name = f"{folder_base}_tag-{folder_tag_part}"
    else:
        folder_name = folder_base

    local_dir = ensure_dirs(DATA, folder_name)

    # Filename (base structure preserved; optional searchable tag suffix added)
    base_name = (
        f"{capture_date}_"
        f"{plate_no}_"
        f"{ddmmm}_"
        f"{strain}_{media}_{cond}_"
        f"{d_index}_"
        f"{capture_time}{capture_ms}_"
        f"{view}"
    )
    tag_part = format_tag_for_filename(capture_tag)
    if tag_part:
        fname = f"{base_name}_tag-{tag_part}.JPG"
        log(f"Filename tag added: {tag_part}")
    else:
        fname = f"{base_name}.JPG"

    local_path = os.path.join(local_dir, fname)

    try:
        cam.capture_file(local_path)
        log(f"📸 Captured locally: {fname}")

        if capture_tag:
            try:
                metadata_q.put_nowait((local_dir, local_path, capture_tag))
                log(f"🏷️ Metadata queued for {fname}")
            except Full as e:
                log(f"⚠️ Metadata queue full or failed for {fname}: {e}")

        return fname

    except Exception as e:
        log(f"❌ Camera capture failed: {e}")
        return None


# ---------------------------------------------------------------------
# SCHEDULER
# ---------------------------------------------------------------------
from math import ceil

def build_schedule():
    """Build the ordered list of imaging slots from plate configs, sorted by scheduled time."""
    global schedule
    now_dt = datetime.now()
    now_ts = time.time()
    with state_lock:
        schedule.clear()
        selected = sorted(
            [(pid, p) for pid, p in plates.items() if p.get("selected", False)],
            key=lambda x: x[0]
        )
        for stagger_idx, (pid, p) in enumerate(selected):
            mode = str(p.get("mode") or "runtime").strip().lower()
            if mode not in ("runtime", "count"):
                mode = "runtime"
            interval_min = int(p.get("interval") or 1)
            interval = interval_min * 60
            if mode == "count":
                count = max(1, int(p.get("count") or 1))
            else:
                dur_min = int(p.get("duration_min") or 60)
                count = max(1, ceil(dur_min * 60 / interval))
            x_mm = max(0.0, min(X_MAX, float(p.get("x_mm", 0.0))))
            y_mm = max(0.0, min(Y_MAX, float(p.get("y_mm", 0.0))))
            if not plates[pid].get("start_dt"):
                stagger_dt = now_dt + timedelta(seconds=stagger_idx * PLATE_STAGGER_SEC)
                plates[pid]["start_dt"] = stagger_dt.isoformat()
            schedule.append({
                "id": pid,
                "x": x_mm,
                "y": y_mm,
                "_plate_warmed": False,
                "interval": interval,
                "count": count,
                "remaining": count,
                "next": now_ts + stagger_idx * PLATE_STAGGER_SEC,
                "start_dt": plates[pid]["start_dt"]
            })
        save_state()
    log(f"Built schedule for {len(schedule)} plates.")
    return schedule

def scheduler_tick():
    now = time.time()
    with state_lock:
        due_tasks = [
            task for task in schedule
            if task["remaining"] > 0 and now >= task["next"]
        ]
        if due_tasks:
            task = min(due_tasks, key=lambda t: (t["next"], t["id"]))
            run_task = dict(task)
            run_task["due"] = task["next"]
            task["next"] = task["next"] + task["interval"]
            task["remaining"] -= 1
            return run_task
    return None

# ---------------------------------------------------------------------
# IMAGING CYCLE
# ---------------------------------------------------------------------
def imaging_cycle():
    """Main imaging loop: iterate the schedule, move to each plate, capture, and handle pause/stop/abort."""
    global imaging_active, stop_cycle_requested
    with state_lock:
        if imaging_active:
            log("imaging_cycle already running.")
            return
        stop_cycle_requested = False
        imaging_active = True
    set_imaging_task_progress(stage="running", stage_state={})
    log("Imaging cycle started ...")
    # Prevent Klipper idle_timeout from firing during long dwells/camera operations
    try:
        send_gcode("SET_IDLE_TIMEOUT TIMEOUT=3600")
        send_gcode("M400")
        log("Idle timeout extended to 3600s for imaging run.")
    except Exception as e:
        log(f"Failed to extend idle timeout: {e}")

    # Camera wrapped to guarantee close
    try:
        _cam_instance = Picamera2()
    except Exception as e:
        log(f"Camera init failed: {e}")
        socketio.emit("status", {"msg": f"Camera unavailable — imaging aborted: {e}"})
        with state_lock:
            imaging_active = False
        return

    with contextlib.closing(_cam_instance) as cam:
        try:
            cfg = cam.create_still_configuration(
                main={"size": PI_CAMERA_STILL_SIZE},
                raw={"size": PI_CAMERA_SENSOR_MODE},
                buffer_count=4,
            )
            cam.configure(cfg)
            cam.start()
        except Exception as e:
            log(f"Camera start failed: {e}")
            socketio.emit("status", {"msg": f"Camera unavailable — imaging aborted: {e}"})
            with state_lock:
                imaging_active = False
            return

        try:
            af_controls = {}
            if controls is not None and hasattr(controls, "AfModeEnum"):
                af_controls["AfMode"] = controls.AfModeEnum.Manual
            cam.set_controls({
                "AwbEnable":    False,
                "ColourGains":  PI_CAMERA_COLOUR_GAINS,
                "AeEnable":     PI_CAMERA_AE_ENABLE,
                "ExposureTime": PI_CAMERA_EXPOSURE_TIME,
                "AnalogueGain": PI_CAMERA_ANALOGUE_GAIN,
                "Sharpness":    PI_CAMERA_SHARPNESS,
                **af_controls,
            })
        except Exception as e:
            log(f"Camera controls not applied: {e}")

        _apply_camera_zoom(cam, PI_CAMERA_ZOOM_PCT)

        warm_state = abortable_sleep(1.5)
        if warm_state == "abort":
            log("Stop/emergency requested during camera warm-up.")

        with state_lock:
            has_plates = bool(plates)
        if not has_plates:
            log("No plates DB present. Run workspace scan first.")
            with state_lock:
                imaging_active = False
            return

        global _pump_warmed, _suck_hold_count
        _pump_warmed = False
        _suck_hold_count = 0
        z_move_up()
        send_gcode("M400")
        build_schedule()
        parked_for_gap = False
        _captures_since_save = 0
        current_stage_state = None

        while imaging_active:
            if emergency_active:
                log("Emergency active — aborting imaging loop.")
                break
            with state_lock:
                if stop_cycle_requested:
                    log("Start/Stop requested — stopping imaging loop.")
                    break
            with state_lock:
                if door_open:
                    log("Door opened -> cold restart, deleting schedule.")
                    schedule.clear()
                    save_state(complete=False)
                    break

            task = scheduler_tick()
            if task is None:
                with state_lock:
                    _next_times = [t["next"] for t in schedule if t["remaining"] > 0]
                if not _next_times:
                    break
                _delay = max(0.05, min(_next_times) - time.time())
                idle_state = abortable_sleep(min(_delay, 30.0))
                if idle_state == "abort":
                    break
                if abort_requested():
                    break
                with state_lock:
                    pending_next = [t["next"] for t in schedule if t["remaining"] > 0]
                if pending_next:
                    next_gap_sec = min(pending_next) - time.time()
                    if abort_requested():
                        break
                    if next_gap_sec > LONG_GAP_PARK_SEC and not parked_for_gap:
                        log(
                            f"Next scheduled capture gap is {int(next_gap_sec)}s (>300s) — parking."
                        )
                        safe_home()
                        with state_lock:
                            for t in schedule:
                                t["_plate_warmed"] = False
                        log("Post-park: per-plate warm flags reset — next grip at each plate uses extended dwell.")
                        parked_for_gap = True
                    elif next_gap_sec <= LONG_GAP_PARK_SEC and parked_for_gap:
                        log("Next scheduled capture within 5 minutes — ready to resume.")
                        parked_for_gap = False
                with state_lock:
                    if not any(t["remaining"] > 0 for t in schedule):
                        break
                continue

            if parked_for_gap:
                log("Leaving parked state for scheduled capture.")
                parked_for_gap = False

            dish_id = task["id"]
            x = max(0.0, min(X_MAX, task["x"]))   
            y = max(0.0, min(Y_MAX, task["y"]))   
            if not task_within_config_window(task):
                continue
            _door_servo_retracted.clear()
            stage_state = {"led_on": False, "hold_active": False, "_post_pause_release_done": False, "_regrab_needed": False, "_post_capture": False}
            current_stage_state = stage_state
            set_imaging_task_progress(task=task, stage="task_selected", stage_state=stage_state)

            log(f"Moving XY to plate {dish_id}: X={x:.2f} Y={y:.2f} mm")
            ck = pause_checkpoint(task=task, stage=stage_state)
            if ck == "abort":
                break
            if ck == "skip":
                continue
            set_imaging_task_progress(task=task, stage="moving_xy", stage_state=stage_state)
            if not move_to(x=x, y=y):
                log("Klipper disconnected (XY move failed) — aborting imaging.")
                break
            ck = pause_checkpoint(task=task, stage=stage_state)
            if ck == "abort":
                break
            if ck == "skip":
                continue

            if abort_requested():
                break
            if not send_gcode("M400"):
                log("Klipper disconnected (M400 failed before z_down) — aborting imaging.")
                break
            z_move_down()
            if not send_gcode("M400"):
                log("Klipper disconnected (M400 failed after z_down) — aborting imaging.")
                break
            set_imaging_task_progress(task=task, stage="z_down_wait", stage_state=stage_state)
            sleep_state = abortable_sleep(2.0, task=task, stage=stage_state)
            if sleep_state == "abort":
                break
            if sleep_state == "skip":
                continue

            led_on()
            stage_state["led_on"] = True
            if not send_gcode("HOLD"):
                log(f"HOLD failed for {dish_id} — skipping plate")
                led_off()
                stage_state["led_on"] = False
                z_move_up()
                send_gcode("M400")
                continue
            else:
                log("HOLD macro executed")
                send_gcode("M400")
            sleep_state = abortable_sleep(SOLENOID_PRIME_SEC, task=task, stage=stage_state)
            if sleep_state == "abort":
                break
            if sleep_state == "skip":
                continue
            hold_state = vacuum_hold(task=task, stage=stage_state)
            if hold_state == "abort":
                break
            if hold_state == "skip":
                continue
            stage_state["hold_active"] = True
            set_imaging_task_progress(task=task, stage="hold_active", stage_state=stage_state)
            sleep_state = abortable_sleep(0.1, task=task, stage=stage_state)
            if sleep_state == "abort":
                break
            if sleep_state == "skip":
                continue
            z_move_up()
            send_gcode("M400")

            #sequence: rotate -> capture -> rotate back -> release -> z up

            # -------------------------------------------------
            # 1️⃣ Rotate servo to 0° and hard-wait
            # -------------------------------------------------
            log("Rotating servo to 0° for imaging...")
            rotate_servo(0)                 # blocks internally
            stage_state["lid_open"] = True
            if not send_gcode("M400"):      # extra safety barrier
                log("Klipper disconnected (M400 failed after servo 0°) — aborting imaging.")
                break
            sleep_state = abortable_sleep(1.2, task=task, stage=stage_state)  # mechanical settle
            if sleep_state == "abort":
                break
            if sleep_state == "skip":
                continue

            if abort_requested():
                break

            # -------------------------------------------------
            # 2️⃣ Camera stabilization delay
            # -------------------------------------------------
            _dark_gap = time.monotonic() - _led_off_time
            _settle = CAMERA_SETTLE_EXTENDED_SEC if _dark_gap > CAMERA_SETTLE_DARK_THRESH else CAMERA_SETTLE_SEC
            if _dark_gap > CAMERA_SETTLE_DARK_THRESH:
                log(f"Extended camera settle {CAMERA_SETTLE_EXTENDED_SEC}s (LED off {_dark_gap:.0f}s)")
            else:
                log("Waiting for camera stabilization...")
            sleep_state = abortable_sleep(_settle, task=task, stage=stage_state)
            if sleep_state == "abort":
                break
            if sleep_state == "skip":
                continue

            if stage_state.get("_regrab_needed"):
                log(f"Re-gripping lid for {dish_id} after pause-release...")
                z_move_down()
                if not send_gcode("M400"):
                    log("M400 failed during re-grip z_down — skipping plate")
                    z_move_up()
                    send_gcode("M400")
                    continue
                if not send_gcode("HOLD"):
                    log(f"HOLD failed on re-grip for {dish_id} — skipping plate")
                    z_move_up()
                    send_gcode("M400")
                    continue
                send_gcode("M400")
                log("HOLD macro executed (re-grip)")
                time.sleep(SOLENOID_PRIME_SEC)
                vacuum_hold()
                stage_state["hold_active"] = True
                z_move_up()
                send_gcode("M400")
                stage_state["_regrab_needed"] = False

            ck = pause_checkpoint(task=task, stage=stage_state)
            if ck == "abort":
                break
            if ck == "skip":
                continue
            if abort_requested():
                break

            # -------------------------------------------------
            # 3️⃣ Capture image (blocking)
            # -------------------------------------------------
            set_imaging_task_progress(task=task, stage="capturing", stage_state=stage_state)
            if PI_CAMERA_DEBUG_BLOCK:
                run_pi_camera_debug_gate(cam, dish_id)
            log("Capturing image...")
            fname = capture_image(cam, dish_id, task)
            stage_state["_post_capture"] = True

            if fname:
                with state_lock:
                    plates[dish_id].setdefault("images", []).append(fname)
                    _captures_since_save += 1
                    if _captures_since_save >= 5:
                        _captures_since_save = 0
                        save_state()

            # -------------------------------------------------
            # 4️⃣ Post-capture hold
            # -------------------------------------------------
            sleep_state = abortable_sleep(1.0, task=task, stage=stage_state)
            if sleep_state == "abort":
                break
            if sleep_state == "skip":
                continue

            if abort_requested():
                break

            # -------------------------------------------------
            # 5️⃣ Rotate back to 90° ONLY after capture
            # -------------------------------------------------
            log("Rotating servo back to 90°...")
            rotate_servo(90)
            stage_state["lid_open"] = False
            if not send_gcode("M400"):
                log("Klipper disconnected (M400 failed after servo 90°) — aborting imaging.")
                break
            sleep_state = abortable_sleep(1.0, task=task, stage=stage_state)
            if sleep_state == "abort":
                break
            if sleep_state == "skip":
                continue
            
            #Until here
            if abort_requested():
                break
            try:
                send_gcode("G1 Z5.00 F3000")
                log("Z -> 5.0 mm (release height)")
                send_gcode("M400")
                sleep_state = abortable_sleep(0.3, task=task, stage=stage_state)
                if sleep_state == "abort":
                    break
                if sleep_state == "skip":
                    continue
            except Exception as e:
                log(f"z_move_release_height failed: {e}")
            vacuum_release()
            led_off()
            stage_state["hold_active"] = False
            stage_state["led_on"] = False
            stage_state["lid_open"] = False
            set_imaging_task_progress(task=task, stage="release_complete", stage_state=stage_state)
            if abort_requested():
                break
            z_move_up()
            set_imaging_task_progress(stage="running", stage_state={})

        # normal completion
        with state_lock:
            all_done = all(t["remaining"] <= 0 for t in schedule)
        if all_done:
            log("All scheduled imaging complete.")

            finish_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            recipients = list(notify_list)  # ✅ use global list
            with state_lock:
                for pid, plate in plates.items():
                    if not plate.get("selected"):
                        continue

                    start_time = plate.get("start_dt", "Unknown")
                    desc = plate.get("desc", "")
                    folder_path = DATA  # images stored locally

                    if recipients:
                        send_run_email(
                            pid,
                            desc,
                            start_time,
                            finish_time,
                            folder_path,
                            recipients
                        )
    
        with state_lock:
            save_state(complete=True)
        try:
            os.remove(STATE_JSON)
        except OSError:
            pass

        if stop_cycle_requested:
            log("Start/Stop stop path — safe home, Z->0, then M18 Z.")
            set_imaging_task_progress(stage="start_stop_shutdown", stage_state={})
            try:
                close_lid_then_release(current_stage_state, reason="Start/Stop safety")
            except Exception as e:
                log(f"Start/Stop pre-home cleanup warning: {e}")
            safe_home()
            try:
                send_gcode("G90")
                send_gcode("G1 Z0.00 F9000")
                send_gcode("M400")
                send_gcode("M18 Z")
                with state_lock:
                    position["z"] = LOW_Z
            except Exception as e:
                log(f"Start/Stop Z deactivation path failed: {e}")
        elif not (emergency_active or door_open or pause_requested):
            log("Imaging complete – homing X/Y and returning Z to 0.")
            z_move_up()
            rotate_servo(90)
            send_gcode("SET_VELOCITY_LIMIT ACCEL=100")
            send_gcode("G28 Y")
            time.sleep(0.25)
            send_gcode("G28 X")
            send_gcode("G1 Y+10 F6000")
            time.sleep(0.25)
            z_move_down()
            send_gcode("G28 Y")
            send_gcode("SET_VELOCITY_LIMIT ACCEL=1000")
            with state_lock:
                position["x"] = 0.0
                position["y"] = 0.0
                position["z"] = LOW_Z
    
    
    # Restore normal idle timeout after imaging completes/terminates
    try:
        send_gcode("SET_IDLE_TIMEOUT TIMEOUT=5")
        send_gcode("M400")
        log("Idle timeout restored to 5s.")
    except Exception as e:
        log(f"Failed to restore idle timeout: {e}")
    with state_lock:
        imaging_active = False
        stop_cycle_requested = False
    set_imaging_task_progress(stage="idle", stage_state={})
    log("Imaging cycle ended." if not (door_open or pause_requested) else "Imaging cycle terminated.")

# ---------------------------------------------------------------------
# QR UTILS
# ---------------------------------------------------------------------
import qrcode
from io import BytesIO
from PIL import Image

def generate_qr_code(data: str):
    qr = qrcode.QRCode(version=1, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").resize((400, 400))
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return buffer

# ---------------------------------------------------------------------
# A4 SHEET WITH 40 mm QRs AND SUBTITLES + BOLD TRIM LINES  (Pdf)
# ---------------------------------------------------------------------
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import qrcode
import io

COLS = 4
ROWS = 5
MAX_QR = COLS * ROWS  # 20

QR_MM = 38            # 🔴 reduced from 40
PAD_MM = 3
GAP_MM = 4
TEXT_MM = 6
TEXT_GAP_MM = 2

CELL_W_MM = QR_MM + 2 * PAD_MM + GAP_MM
CELL_H_MM = QR_MM + PAD_MM + TEXT_GAP_MM + TEXT_MM + PAD_MM

def build_a4_qr_pdf(payloads, out_path):
    assert len(payloads) <= MAX_QR, "Max 20 QRs per A4 sheet"

    target = str(out_path) if isinstance(out_path, (str, os.PathLike)) else out_path
    c = canvas.Canvas(target, pagesize=A4)
    page_w, page_h = A4

    grid_w_mm = COLS * CELL_W_MM - GAP_MM
    grid_h_mm = ROWS * CELL_H_MM

    x0 = (210 - grid_w_mm) / 2 * mm
    y0 = (297 - grid_h_mm) / 2 * mm

    qr_size = QR_MM * mm

    for i, text in enumerate(payloads):
        row, col = divmod(i, COLS)

        cell_x = x0 + col * CELL_W_MM * mm
        cell_y = page_h - (y0 + (row + 1) * CELL_H_MM * mm)

        qr_x = cell_x + PAD_MM * mm
        qr_y = cell_y + PAD_MM * mm + TEXT_MM * mm + TEXT_GAP_MM * mm

        qr = qrcode.make(text, border=0)
        buf = io.BytesIO()
        qr.save(buf, format="PNG")
        buf.seek(0)

        qr_img = ImageReader(buf)

        c.drawImage(
            qr_img,
            qr_x,
            qr_y,
            width=qr_size,
            height=qr_size,
            preserveAspectRatio=True,
            mask="auto"
        )

        # subtitle
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(
            qr_x + qr_size / 2,
            cell_y + PAD_MM * mm,
            text
        )

    # ---- dotted cutting lines ----
    c.setLineWidth(0.6)
    c.setDash(2, 2)

    for col in range(COLS + 1):
        X = x0 + col * CELL_W_MM * mm
        c.line(X, page_h - y0, X, page_h - (y0 + grid_h_mm * mm))

    for row in range(ROWS + 1):
        Y = page_h - (y0 + row * CELL_H_MM * mm)
        c.line(x0, Y, x0 + grid_w_mm * mm, Y)

    c.showPage()
    c.save()


# ---------------------------------------------------------------------
# FLASK ROUTES
# ---------------------------------------------------------------------
@app.route("/system/state")
def system_state():
    with state_lock:
        return jsonify({
            "plates": dict(plates),
            "experiment_tag": experiment_tag,
            "position": dict(position),
            "schedule": list(schedule),
            "door_open": door_open,
            "imaging_active": imaging_active,
            "pause_requested": pause_requested,
            "paused": paused,
            "unresolved": list(unresolved_detections.values()),
        })

@app.route("/system/logs")
def get_logs():
    if not os.path.exists(LOG_FILE):
        return jsonify({"logs": []})
    with open(LOG_FILE, "r") as f:
        lines = f.readlines()
    return jsonify({"logs": lines[-200:]})

@app.route("/detect")
def detect_route():
    global _detect_running
    with _detect_lock:
        if _detect_running:
            return jsonify({"running": True}), 409
        _detect_running = True

    pulse_requested = request.args.get("pulse") == "1"

    def _run():
        global _detect_running
        led_was_off = not imaging_active
        try:
            reset_preview_detection_state()
            socketio.emit("workspace", {"plates": {}, "unresolved": []})
            if pulse_requested:
                try:
                    send_pulse()
                    log("/detect pre-scan pulse sent")
                except Exception:
                    log("Preview pulse failed: " + traceback.format_exc())
                time.sleep(2)
            if led_was_off:
                led_on()
            log("/detect triggered — scanning workspace")
            result = detect_and_build_db()
            ui_plates = {k: v for k, v in result.items() if not k.startswith("_")}
            socketio.emit("workspace", {
                "plates": ui_plates,
                "unresolved": list(unresolved_detections.values()),
            })
        except Exception as e:
            log(f"/detect error: {e}")
            socketio.emit("status", {"msg": f"Scan failed: {e}"})
        finally:
            if led_was_off:
                time.sleep(5)
                led_off()
            with _detect_lock:
                _detect_running = False

    threading.Thread(target=_run, daemon=True).start()
    return jsonify({"queued": True}), 202

def position_monitor():
    last_xy = None
    while True:
        try:
            pos = get_position()
            if pos:
                x = pos.get("x", position["x"])
                y = pos.get("y", position["y"])
                z = pos.get("z", position["z"])
                with state_lock:
                    position["x"] = x
                    position["y"] = y
                    position["z"] = z
                xy = (round(x, 2), round(y, 2))
                if imaging_active and xy != last_xy:
                    last_xy = xy
        except Exception:
            log("position_monitor except: " + traceback.format_exc())
        time.sleep(0.25)

@app.route("/config", methods=["POST"])
def config_route():
    global experiment_tag

    incoming = request.get_json() or {}
    cfg = incoming.get("plates") if isinstance(incoming, dict) and isinstance(incoming.get("plates"), dict) else incoming
    tag_supplied = isinstance(incoming, dict) and ("experiment_tag" in incoming)
    incoming_tag = sanitize_experiment_tag(incoming.get("experiment_tag", "")) if tag_supplied else experiment_tag
    pulse_requested = request.args.get("pulse") == "1"

    if not isinstance(cfg, dict):
        return jsonify({"error": "Invalid config payload"}), 400

    old_tag = experiment_tag
    with state_lock:
        if tag_supplied:
            experiment_tag = incoming_tag
        for pid, p in cfg.items():
            if pid not in plates:
                continue
            if not isinstance(p, dict):
                continue

            # ---- user-editable fields ----
            plates[pid]["desc"] = p.get("desc", "")
            plates[pid]["selected"] = bool(p.get("selected", False))

            # ---- scheduling inputs (UI-driven) ----
            every_min = int(p.get("every_min", 60))
            mode = str(p.get("mode") or "runtime").strip().lower()
            if mode not in ("runtime", "count"):
                mode = "runtime"
            image_count = max(1, int(p.get("image_count") or 1))
            duration_min = max(1, int(p.get("duration_min") or 60))

            # ---- authoritative scheduler fields ----
            plates[pid]["interval"] = max(1, every_min)  # minutes
            plates[pid]["mode"] = mode
            plates[pid]["duration_min"] = duration_min

            # In count mode, enforce exact number of captures from UI.
            # In runtime mode, count is derived from duration_min + interval.
            plates[pid]["count"] = image_count if mode == "count" else 1

        # Assign staggered start_dt and end for all selected plates, ordered by plate ID.
        # start_dt = button-press time + stagger; end = start_dt + duration.
        config_time = datetime.now()
        sorted_selected = sorted(
            [pid for pid in plates if plates[pid].get("selected", False)],
            key=lambda pid: pid
        )
        for idx, pid in enumerate(sorted_selected):
            stagger = timedelta(seconds=idx * PLATE_STAGGER_SEC)
            plate_start = config_time + stagger
            plates[pid]["start_dt"] = plate_start.isoformat()
            if plates[pid].get("mode", "runtime") == "runtime":
                dur_min = int(plates[pid].get("duration_min") or 60)
                plates[pid]["end"] = (plate_start + timedelta(minutes=dur_min)).isoformat()
            else:
                plates[pid]["end"] = ""

    if experiment_tag != old_tag:
        log(f"Experiment tag updated: {experiment_tag or '(empty)'}")

    # rebuild schedule immediately so UI + logs reflect reality
    build_schedule()

    try:
        with open(PLATES_JSON, "w") as f:
            json.dump(plates, f, indent=2)
    except (OSError, TypeError) as e:
        log(f"Failed to save plates DB from config: {e}")

    if pulse_requested:
        try:
            send_pulse()
            log("/config pulse sent")
        except Exception:
            log("Config pulse failed: " + traceback.format_exc())
        threading.Thread(
            target=lambda: subprocess.run(
                ["/usr/local/sbin/automator-buzzer.sh", "2"],
                check=False,
            ),
            daemon=True,
        ).start()

    log(f"Config saved -> schedule rebuilt. Awaiting Start Imaging. Experiment tag: {experiment_tag or '(empty)'}")
    return jsonify({"ok": True})



@app.route("/system/start", methods=["POST"])
@csrf.exempt
@require_auth
def start_system():
    global imaging_active, notify_list, start_stop_generation   # ✅ include notify_list

    # ✅ read notify_emails sent from frontend
    data = request.get_json(silent=True) or {}
    notify_emails = (data.get("notify_emails") or "").strip()

    # ✅ split by commas, strip spaces, drop empties
    new_notify_list = [e.strip() for e in notify_emails.split(",") if e.strip()]
    with state_lock:
        previous_notify_list = list(notify_list)
        notify_list = new_notify_list

    if notify_list != previous_notify_list:
        log(f"Notification emails updated from UI: {notify_list}")
    elif notify_list:
        log(f"Notification emails unchanged: {notify_list}")
    else:
        log("Notification emails empty.")

    log(f"/system/start called. notify_list={notify_list}")

    # ---- existing logic continues ----
    with state_lock:
        door_is_open = door_open
        has_plates = bool(plates)
        selected = [p for p in plates.values() if p.get("selected")]
        already_running = imaging_active
        start_guard = start_stop_generation

    if door_is_open:
        return jsonify({"error": "Door is open"}), 400
    if not has_plates:
        return jsonify({"error": "No plates detected"}), 400
    if not selected:
        return jsonify({"error": "No valid plate config"}), 400
    if already_running:
        return jsonify({"ok": True, "already_running": True})

    safe_home()
    with state_lock:
        if start_stop_generation != start_guard:
            log("Start aborted: Start/Stop was requested during start preparation.")
            return jsonify({"ok": False, "cancelled": "start_stop_requested"}), 409
    threading.Thread(target=imaging_cycle, daemon=True).start()
    log("Imaging cycle launched from /system/start.")
    return jsonify({"ok": True})

@app.route("/plates/<unres_id>/identify", methods=["POST"])
@csrf.exempt
@require_auth
def identify_unresolved_plate(unres_id):
    data = request.get_json(silent=True) or {}
    qr_data = (data.get("qr_data") or "").strip().upper()
    if not qr_data:
        return jsonify({"error": "qr_data is required"}), 400
    valid, reason = validate_micro_qr(qr_data)
    if not valid:
        return jsonify({"error": f"Invalid QR format: {reason}"}), 400
    try:
        iconn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
        try:
            iconn.execute("PRAGMA journal_mode=WAL")
            pid = PlateID(iconn.cursor()).get_id([qr_data])
            iconn.commit()
        finally:
            iconn.close()
    except Exception as e:
        return jsonify({"error": f"Database error: {e}"}), 500
    with state_lock:
        if unres_id not in unresolved_detections:
            return jsonify({"error": "Plate not found or already resolved"}), 404
        if any(p.get("desc") == qr_data for p in plates.values()):
            return jsonify({"error": "QR data already assigned to another plate"}), 409
        unres = unresolved_detections.pop(unres_id)
        new_key = next(
            (k for k, p in plates.items()
             if p.get("unresolved_track_id") == unres_id or p.get("source_track_id") == unres_id),
            None,
        )
        if new_key is None:
            new_key = _next_plate_key(plates)
            plates[new_key] = {
                "interval": 30, "count": 1, "end": "",
                "selected": False, "start_dt": None,
            }
        plates[new_key].update({
            "id": pid,
            "x_mm": unres["position_mm"]["x"],
            "y_mm": unres["position_mm"]["y"],
            "confidence": unres.get("confidence"),
            "desc": qr_data,
            "identity_source": "manual",
            "detection_source": unres.get("detection_source", "yolo"),
            "position_source": unres.get("position_source", "existing_yolo_homography"),
            "source_track_id": unres.get("source_track_id", unres_id),
        })
        plates[new_key].pop("unresolved_track_id", None)
        save_state()
    try:
        with open(PLATES_JSON, "w") as f:
            json.dump(plates, f, indent=2)
    except Exception as e:
        log(f"Plates persist failed after identify: {e}")
    log(f"Unresolved {unres_id} identified as {qr_data} -> {new_key}")
    ui_plates = {k: v for k, v in plates.items() if not k.startswith("_")}
    socketio.emit("workspace", {
        "plates": ui_plates,
        "unresolved": list(unresolved_detections.values()),
    })
    return jsonify({"ok": True, "plate_key": new_key})


@app.route("/plates/<unres_id>/dismiss", methods=["POST"])
@csrf.exempt
@require_auth
def dismiss_unresolved_plate(unres_id):
    with state_lock:
        if unres_id not in unresolved_detections:
            return jsonify({"error": "Plate not found"}), 404
        if unres_id.startswith("FALLBACK-"):
            dismiss_fallback_track(unres_id)
        unresolved_detections.pop(unres_id)
        for plate_key in [
            k for k, p in plates.items()
            if p.get("unresolved_track_id") == unres_id or p.get("source_track_id") == unres_id
        ]:
            plates.pop(plate_key, None)
        save_state()
    log(f"Unresolved {unres_id} dismissed.")
    ui_plates = {k: v for k, v in plates.items() if not k.startswith("_")}
    socketio.emit("workspace", {
        "plates": ui_plates,
        "unresolved": list(unresolved_detections.values()),
    })
    return jsonify({"ok": True})


@app.route("/system/pause", methods=["POST"])
@csrf.exempt
@require_auth
def pause_system():
    global pause_requested, paused
    with state_lock:
        if not imaging_active:
            pause_requested = False
            paused = False
            return jsonify({"paused": False, "ignored": "imaging_inactive"})
        if stop_cycle_requested:
            return jsonify({"paused": False, "ignored": "stop_requested"})
        pause_requested = True
        save_state(complete=False)
    log("Pause requested")
    return jsonify({"paused": True})

@app.route("/system/unpause", methods=["POST"])
@csrf.exempt
@require_auth
def unpause_system():
    global pause_requested, paused, plates, schedule, position, imaging_task_progress
    restore_state = None
    with state_lock:
        if not imaging_active:
            pause_requested = False
            paused = False
            return jsonify({"resumed": False, "ignored": "imaging_inactive"})
        if not schedule and os.path.exists(STATE_JSON):
            try:
                with open(STATE_JSON, "r") as f:
                    restore_state = json.load(f)
            except (OSError, json.JSONDecodeError):
                restore_state = None
    if restore_state:
        with state_lock:
            if not schedule:
                plates = restore_state.get("plates", {}).copy() or plates
                position = restore_state.get("position", {}).copy() or position
                schedule = restore_state.get("schedule", []).copy() or schedule
                imaging_task_progress = restore_state.get("imaging_task_progress", imaging_task_progress).copy()
                save_state(complete=False)
    with state_lock:
        pause_requested = False
        paused = False
    log("Resume requested")
    return jsonify({"resumed": True})

@app.route("/system/start_stop", methods=["POST"])
@csrf.exempt
@require_auth
def start_stop_system():
    global stop_cycle_requested, pause_requested, paused, start_stop_generation
    with state_lock:
        start_stop_generation += 1
        running = imaging_active
    if running:
        with state_lock:
            stop_cycle_requested = True
            pause_requested = False
            paused = False
        _scheduler_wakeup.set()
        log("Start/Stop requested: stopping imaging cycle safely.")
        return jsonify({"ok": True, "action": "stop_requested"})

    log("Start/Stop requested while idle: forcing SAFE_HOME then Z=50 ready.")
    safe_home()
    try:
        send_gcode("G90")
        send_gcode(f"G1 Z{SAFE_Z:.2f} F3000")
        send_gcode("M400")
        with state_lock:
            position["z"] = SAFE_Z
    except Exception as e:
        log(f"Start/Stop idle prepare failed: {e}")
        return jsonify({"ok": False, "error": str(e)}), 500
    return jsonify({"ok": True, "action": "ready"})

# ---------------------------------------------------------------------
# EMERGENCY STOP 
# ---------------------------------------------------------------------
@app.route("/emergency_stop", methods=["POST"])
@csrf.exempt
@require_auth
def emergency_stop():
    global imaging_active, emergency_active, notify_list
    with state_lock:
        emergency_active = True
        notify_list = []
    _scheduler_wakeup.set()
    log("Notification emails cleared due to EMERGENCY STOP.")
    log("EMERGENCY STOP — HARD ABORT")
    cache_targets = [
        (os.path.join(BASE, "__pycache__"), "Automator/dev2/__pycache__"),
        ("/home/pi/.cache/chromium/Default/Cache", "Chromium Cache"),
        ("/home/pi/.cache/chromium/Default/Code Cache", "Chromium Code Cache"),
        ("/home/pi/.cache/chromium/Default/GPUCache", "Chromium GPU Cache"),
    ]
    for path, label in cache_targets:
        exists, removed_files, removed_dirs = clear_dir_contents(path)
        if exists:
            log(f"Cleared {label}: files={removed_files}, dirs={removed_dirs}")
        else:
            log(f"{label} not found at {path}")
    try:
        turn_off_led_no_pulse()
        rotate_servo(90)
        send_gcode("SET_PIN PIN=vacuum_pump VALUE=0.05")
        send_gcode("SET_PIN PIN=solenoid_valve VALUE=0.05")
        try:
            send_gcode("G90")
            send_gcode("SET_VELOCITY_LIMIT ACCEL=2000")
            send_gcode("G1 Z0.00 F9000")
            send_gcode("M400")
        except Exception as e:
            log(f"Emergency Z-to-zero move failed: {e}")
        send_gcode("M400")
    except Exception:
        pass
    try:
        send_gcode("M112")
    except Exception:
        pass
    try:
        send_gcode("FIRMWARE_RESTART")
    except Exception:
        pass
    log("Controller shutting down via SIGINT …")
    os.kill(os.getpid(), signal.SIGINT)
    return jsonify({"stopped": True})

# ---------------------------------------------------------------------
# Directory Space
# ---------------------------------------------------------------------
import shutil

def shared_storage_available():
    return False

def active_storage_root():
    return {
        "path": DATA,
        "mode": "local",
        "label": "Disk Storage Local Pi",
        "mounted": False,
    }

@app.route("/system/disk")
@require_auth
def disk_status():
    try:
        storage = active_storage_root()
        total, used, free = shutil.disk_usage(storage["path"])
        return jsonify({
            "mode": storage["mode"],
            "label": storage["label"],
            "root": storage["path"],
            "shared_mounted": storage["mounted"],
            "total_gb": round(total / (1024**3), 1),
            "used_gb": round(used / (1024**3), 1),
            "free_gb": round(free / (1024**3), 1)
        })
    except OSError as e:
        return jsonify({"error": str(e)}), 500


@app.route("/system/services")
def services_status():
    return jsonify(dict(_services_cache))


@app.route("/system/restart-klipper", methods=["POST"])
@require_auth
def restart_klipper():
    result = subprocess.run(
        ["sudo", "systemctl", "restart", "klipper"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        return jsonify({"ok": True, "msg": "Klipper restart initiated."})
    return jsonify({"ok": False, "msg": result.stderr or "Failed to restart Klipper."}), 500


@app.route("/system/restart-moonraker", methods=["POST"])
@require_auth
def restart_moonraker():
    result = subprocess.run(
        ["sudo", "systemctl", "restart", "moonraker"],
        capture_output=True, text=True
    )
    if result.returncode == 0:
        return jsonify({"ok": True, "msg": "Moonraker restart initiated."})
    return jsonify({"ok": False, "msg": result.stderr or "Failed to restart Moonraker."}), 500


# ---------------------------------------------------------------------
# File Manager
# ---------------------------------------------------------------------
from flask import jsonify, send_from_directory, abort

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}

def is_gallery_image(name):
    return os.path.splitext(name or "")[1].lower() in IMAGE_EXTENSIONS

@app.route("/image-gallery-data")
@require_auth
def image_gallery_data():
    storage = active_storage_root()
    root = os.path.abspath(storage["path"])
    images = []

    try:
        for current_root, dirs, files in os.walk(root):
            dirs.sort()
            files.sort()
            for name in files:
                if not is_gallery_image(name):
                    continue
                full_path = os.path.join(current_root, name)
                try:
                    rel_path = os.path.relpath(full_path, root)
                    mtime = os.path.getmtime(full_path)
                except OSError:
                    continue
                images.append({
                    "path": rel_path.replace(os.sep, "/"),
                    "name": name,
                    "mtime": mtime,
                })
    except OSError as e:
        return jsonify({"error": str(e)}), 500

    images.sort(key=lambda item: item["mtime"], reverse=True)
    return jsonify({
        "mode": storage["mode"],
        "label": storage["label"],
        "root": storage["path"],
        "shared_mounted": storage["mounted"],
        "images": images,
    })

@app.route("/image-gallery")
@require_auth
def image_gallery():
    return """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Automator Image Preview</title>
<style>
:root {
  color-scheme: light dark;
  --bg: #f5f7f9;
  --text: #1f2933;
  --muted: #5d6b78;
  --panel: #ffffff;
  --border: #d9e2ec;
  --accent: #207b63;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #101418;
    --text: #edf2f7;
    --muted: #a0aec0;
    --panel: #171c22;
    --border: #2d3742;
    --accent: #5ed0aa;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: var(--bg);
  color: var(--text);
}
header {
  position: sticky;
  top: 0;
  z-index: 2;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 14px 18px;
  border-bottom: 1px solid var(--border);
  background: var(--panel);
}
h1 {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
}
#storage-label {
  color: var(--muted);
  font-size: 13px;
}
button {
  border: 1px solid var(--border);
  border-radius: 6px;
  background: transparent;
  color: var(--text);
  cursor: pointer;
  font: inherit;
  padding: 7px 11px;
}
button:hover { border-color: var(--accent); }
main { padding: 18px; }
#status {
  color: var(--muted);
  margin-bottom: 14px;
}
.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 14px;
}
.thumb {
  display: block;
  overflow: hidden;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--panel);
  color: inherit;
  text-decoration: none;
}
.thumb img {
  display: block;
  width: 100%;
  aspect-ratio: 1 / 1;
  object-fit: cover;
  background: #111;
}
.thumb-name {
  padding: 8px;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.25;
  overflow-wrap: anywhere;
}
</style>
</head>
<body>
<header>
  <div>
    <h1>Image Preview</h1>
    <div id="storage-label">Loading storage...</div>
  </div>
  <div style="display:flex;gap:8px;">
    <button type="button" onclick="window.location.assign('/main')">&#8592; Back to Automator</button>
    <button type="button" onclick="loadGallery()">Refresh</button>
  </div>
</header>
<main>
  <div id="status">Loading images...</div>
  <div id="gallery" class="grid"></div>
</main>
<script>
function encodePath(path){
  return String(path || "").split("/").map(encodeURIComponent).join("/");
}
function renderGallery(data){
  const label = document.getElementById("storage-label");
  if(label && data.label){
    label.textContent = data.label;
  }
  const images = data.images || [];
  const gallery = document.getElementById("gallery");
  const status = document.getElementById("status");
  gallery.innerHTML = "";
  status.textContent = images.length ? `${images.length} image${images.length === 1 ? "" : "s"}` : "No images available.";
  images.forEach(image => {
    const href = `/files/${encodePath(image.path)}`;
    const card = document.createElement("a");
    card.className = "thumb";
    card.href = href;
    card.target = "_blank";
    card.rel = "noopener";
    const img = document.createElement("img");
    img.loading = "lazy";
    img.src = href;
    img.alt = "";
    const name = document.createElement("div");
    name.className = "thumb-name";
    name.textContent = image.path;
    card.appendChild(img);
    card.appendChild(name);
    gallery.appendChild(card);
  });
}
async function loadGallery(){
  document.getElementById("status").textContent = "Loading images...";
  document.getElementById("gallery").innerHTML = "";
  try {
    const res = await fetch("/image-gallery-data");
    if(!res.ok){
      throw new Error(`HTTP ${res.status}`);
    }
    renderGallery(await res.json());
  } catch (err) {
    document.getElementById("status").textContent = `Unable to load images: ${err.message}`;
  }
}
loadGallery();
</script>
</body>
</html>"""

@app.route("/files/")
@app.route("/files/<path:req_path>")
@require_auth
def browse_files(req_path=""):
    storage = active_storage_root()
    file_root = Path(storage["path"]).resolve()

    # 🔒 Security: resolve symlinks and prevent path traversal
    try:
        abs_path = (file_root / req_path).resolve(strict=True)
    except OSError:
        abort(404)

    if not abs_path.is_relative_to(file_root):
        abort(403)

    # 📁 Directory listing
    if os.path.isdir(abs_path):
        entries = []
        for name in sorted(os.listdir(abs_path)):
            full = os.path.join(abs_path, name)
            entries.append({
                "name": name,
                "is_dir": os.path.isdir(full),
                "size": os.path.getsize(full) if os.path.isfile(full) else None
            })
        return jsonify({
            "mode": storage["mode"],
            "label": storage["label"],
            "root": storage["path"],
            "shared_mounted": storage["mounted"],
            "path": req_path,
            "entries": entries
        })

    # 📄 File download
    if os.path.isfile(abs_path):
        return send_from_directory(
            os.path.dirname(abs_path),
            os.path.basename(abs_path),
            as_attachment=True
        )

    abort(404)

# ---------------------------------------------------------------------
# VERSION ENDPOINT
# ---------------------------------------------------------------------
@app.route("/system/version")
def version():
    app_version = "1.0.0"
    try:
        sha = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"],
                                      cwd=os.path.dirname(__file__)).decode().strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"]))
        return jsonify({"version": app_version, "git": sha, "dirty": dirty})
    except (subprocess.SubprocessError, OSError):
        return jsonify({"version": app_version, "git": "unknown"})

# ---------------------------------------------------------------------
# QR ROUTES
# ---------------------------------------------------------------------
@app.route("/qr/generate", methods=["POST"])
def generate_qr():
    data = request.get_json() or {}
    payload = data.get("payload", "").strip()
    if not payload:
        return jsonify({"error": "Empty payload"}), 400
    qr_image = generate_qr_code(payload)
    return send_file(qr_image, mimetype="image/png", as_attachment=True, download_name="qr_code.png")

from flask import request, jsonify


# ---------------------------------------------------------------------
# QR PDF ROUTES
# ---------------------------------------------------------------------
@app.route("/qr/print_sheet", methods=["POST"])
@require_auth
def print_qr_sheet():
    data = request.get_json(silent=True) or {}
    payloads = data.get("payloads", [])

    if not isinstance(payloads, list) or not payloads:
        return jsonify({"error": "Missing or invalid payloads list"}), 400

    if len(payloads) > 20:
        return jsonify({
            "error": "Max 20 QR codes per A4 sheet at 40 mm size"
        }), 400

    clean_payloads = []
    for payload in payloads:
        if not isinstance(payload, str):
            return jsonify({"error": "All payloads must be strings"}), 400
        payload = payload.strip()
        if not payload:
            return jsonify({"error": "Payloads must not be empty"}), 400
        clean_payloads.append(payload)

    pdf_buffer = BytesIO()
    build_a4_qr_pdf(clean_payloads, pdf_buffer)
    pdf_buffer.seek(0)

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log(f"Generated downloadable A4 PDF sheet with {len(clean_payloads)} QR codes")
    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"automator_qr_sheet_{stamp}.pdf"
    )


# ---------------------------------------------------------------------
# UI ROUTES
# ---------------------------------------------------------------------
@app.route("/")
@require_auth
def local_qr_index():
    return render_template("index_qr.html")

@app.route("/main")
@require_auth
def local_main_ui():
    return render_template("index.html")

# ---------------------------------------------------------------------
# SERVICE HEALTH POLLING
# ---------------------------------------------------------------------
_services_cache = {"klipper": False, "moonraker": False}

# ---------------------------------------------------------------------------
# METADATA QUEUE
# ---------------------------------------------------------------------------
metadata_q: Queue = Queue(maxsize=200)

def metadata_worker() -> None:
    while True:
        try:
            local_dir, local_path, tag = metadata_q.get()
        except Exception:
            continue
        try:
            write_path_tag_metadata(local_dir, tag)
            write_path_tag_metadata(local_path, tag)
            write_experiment_tag_exif(local_path, tag)
            write_standard_keywords(local_path)
            log(f"🏷️ Metadata written for {os.path.basename(local_path)}")
        except (OSError, subprocess.SubprocessError, ValueError) as e:
            log(f"⚠️ Metadata failed for {os.path.basename(local_path)}: {e}")
        finally:
            metadata_q.task_done()

def _poll_services():
    while True:
        mk_ok = False
        kp_ok = False
        try:
            req = urllib.request.urlopen("http://localhost:7125/server/info", timeout=2)
            data = json.loads(req.read())
            mk_ok = True
            kp_ok = data.get("result", {}).get("klippy_state") == "ready"
        except (urllib.error.URLError, json.JSONDecodeError, OSError):
            pass
        _services_cache["klipper"] = kp_ok
        _services_cache["moonraker"] = mk_ok
        time.sleep(10)

# ---------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------
if __name__ == "__main__":
    log("Controller running on http://0.0.0.0:8080/")
    init_system()
    # Trusted LAN/direct-Ethernet binding for local Pi and MacBook access.
    # Do not expose this service to an untrusted network.
    socketio.run(app, host="0.0.0.0", port=8080, use_reloader=False)
