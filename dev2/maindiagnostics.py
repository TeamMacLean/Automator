#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2025–2026 Rohan R

"""
Diagnostics Web Server (internal build)
True MJPEG, 20 Hz position, safe-home with servo 90°, door sensor, etc.
"""

from __future__ import annotations

import os
import time
import signal
import threading
import cv2
import subprocess
import sys
import socket
from typing import Dict, Any

from flask import Flask, request, render_template, jsonify, redirect, url_for, session, Response
from flask_socketio import SocketIO

from maingcodesender import move_to, get_position, send_gcode, vacuum, rotate
from led import turn_on_led, turn_off_led

import RPi.GPIO as GPIO

# ------------------------------------------------------------------
# Single source of truth for constants
# ------------------------------------------------------------------
CFG: Dict[str, Any] = {
    "DIAG_PORT": 8081,
    "MJPEG_PORT": 9000,
    "CAM_WIDTH": 640,
    "CAM_HEIGHT": 480,
    "POS_HZ": 0.05,          # 20 Hz
    "DOOR_PIN": 26,
    "USERNAME": "admin",
    "PASSWORD": os.environ["AUTOMATOR_ADMIN_PASSWORD"],
}

BASE_DIR = os.path.expanduser("~/Automator/dev2")
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATE_DIR = os.path.join(BASE_DIR, "templates")
os.makedirs(STATIC_DIR, exist_ok=True)

# ------------------------------------------------------------------
# GPIO
# ------------------------------------------------------------------
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(CFG["DOOR_PIN"], GPIO.IN)

# ------------------------------------------------------------------
# Flask
# ------------------------------------------------------------------
app = Flask(__name__, template_folder=TEMPLATE_DIR, static_folder=STATIC_DIR)
app.secret_key = os.environ["AUTOMATOR_SESSION_SECRET"]
socketio = SocketIO(app, cors_allowed_origins="*")

# ------------------------------------------------------------------
# Shared state
# ------------------------------------------------------------------
last_position: Dict[str, Dict[str, Any]] = {
    "abs": {"x": 0.0, "y": 0.0, "z": 0.0, "vacuum": "IDLE", "rotate": 0},
    "rel": {"x": 0.0, "y": 0.0, "z": 0.0},
}
lock = threading.Lock()

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def log(msg: str) -> None:
    stamp = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(stamp)
    socketio.emit("log", {"msg": stamp})

def door_state() -> bool:
    return GPIO.input(CFG["DOOR_PIN"]) == GPIO.HIGH

# ==================================================================
# LOGIN
# ==================================================================
@app.route("/", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        u = request.form.get("username")
        p = request.form.get("password")
        if u == CFG["USERNAME"] and p == CFG["PASSWORD"]:
            session["logged_in"] = True
            log("🔑 Login successful")
            return redirect(url_for("dashboard"))
        return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():
    if not session.get("logged_in"):
        return redirect(url_for("login"))
    socketio.emit("door", {"status": "Door Open" if door_state() else "Door Closed"})
    socketio.emit("position", last_position)
    return render_template("diag_index.html")

# ==================================================================
# MJPEG STREAM  (internal true stream)
# ==================================================================
stream_enabled = False
camera_index: int | None = None

def detect_camera_index() -> int | None:
    global camera_index
    if camera_index is not None:
        return camera_index
    for idx in range(4):
        cap = cv2.VideoCapture(idx)
        time.sleep(0.2)
        ret, _ = cap.read()
        cap.release()
        if ret:
            log(f"📸 Camera detected for MJPEG at index {idx}")
            camera_index = idx
            return idx
    log("❌ No USB camera found for MJPEG")
    return None

def mjpeg_stream_generator():
    idx = detect_camera_index()
    if idx is None:
        yield b"--frame\r\nContent-Type: text/plain\r\n\r\nNo camera\r\n"
        return
    cap = cv2.VideoCapture(idx)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CFG["CAM_WIDTH"])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CFG["CAM_HEIGHT"])
    log(f"▶ MJPEG stream started on camera index {idx}")
    global stream_enabled
    try:
        while True:
            if not stream_enabled:
                time.sleep(0.05)
                continue
            ret, frame = cap.read()
            if not ret:
                continue
            ok, jpeg = cv2.imencode(".jpg", frame)
            if not ok:
                continue
            yield (
                b"--frame\r\n"
                b"Content-Type: image/jpeg\r\n\r\n" + jpeg.tobytes() + b"\r\n"
            )
    finally:
        cap.release()
        log("🛑 MJPEG stream stopped")

@app.route("/stream")
def stream():
    global stream_enabled
    stream_enabled = True
    return Response(
        mjpeg_stream_generator(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
    )

@app.route("/usb/start")
def usb_start():
    global stream_enabled
    stream_enabled = True
    log("▶ USB camera stream ENABLED")
    return jsonify({"ok": True})

@app.route("/usb/stop")
def usb_stop():
    global stream_enabled
    stream_enabled = False
    log("⏹ USB camera stream DISABLED")
    return jsonify({"ok": True})

# ==================================================================
# SAFE HOME
# ==================================================================
@app.route("/safe_home", methods=["POST"])
def safe_home():
    log("🏠 SAFE HOME requested")
    try:
        send_gcode("SET_PIN PIN=arm_rotate VALUE=0.10")
        last_position["abs"]["rotate"] = 90
        log("🔄 Servo forced to 90° (pre-home)")
        send_gcode("M18")
        time.sleep(0.3)
        send_gcode("SET_VELOCITY_LIMIT ACCEL=100")
        send_gcode("G28")
        log("🏁 Homing complete")
        send_gcode("G92 X0 Y0 Z0")
        send_gcode("SET_VELOCITY_LIMIT ACCEL=1000")
        return jsonify({"ok": True})
    except Exception as e:
        log(f"❌ Safe home error: {e}")
        return jsonify({"ok": False}), 500

# ==================================================================
# MOTION
# ==================================================================
@app.route("/move", methods=["POST"])
def move_axis():
    data = request.get_json()
    axis = list(data.keys())[0]
    delta = float(data[axis])
    with lock:
        prev_abs = last_position["abs"][axis]
        new_abs = prev_abs + delta
        move_to(**{axis: new_abs})
        last_position["abs"][axis] = new_abs
        last_position["rel"][axis] += delta
        socketio.emit("position", last_position)
    return jsonify(last_position)

# ==================================================================
# VACUUM
# ==================================================================
@app.route("/vacuum", methods=["POST"])
def vacuum_route():
    action = request.get_json().get("action", "").lower()
    if action not in {"suck_hold", "hold", "release"}:
        return jsonify({"error": "invalid"}), 400
    vacuum(action)
    last_position["abs"]["vacuum"] = action.upper()
    socketio.emit("position", last_position)
    log(f"🧲 Vacuum → {action}")
    return jsonify({"ok": True})

# ==================================================================
# ROTATE SERVO
# ==================================================================
@app.route("/rotate", methods=["POST"])
def rotate_route():
    ang = float(request.get_json().get("angle", 0))
    rotate(ang)
    last_position["abs"]["rotate"] = ang
    socketio.emit("position", last_position)
    log(f"🔄 Rotate → {ang}°")
    return jsonify({"ok": True})

# ==================================================================
# LED
# ==================================================================
@app.route("/led/<state>")
def led(state: str):
    if state == "on":
        turn_on_led()
        log("💡 LED ON")
    else:
        turn_off_led()
        log("💡 LED OFF")
    return jsonify({"ok": True})

# ==================================================================
# DOOR
# ==================================================================
@app.route("/door")
def door_check():
    st = "Door Open" if door_state() else "Door Closed"
    socketio.emit("door", {"status": st})
    log(f"🚪 {st}")
    return jsonify({"status": st})

def door_thread() -> None:
    last_st: str | None = None
    while True:
        st = "Door Open" if door_state() else "Door Closed"
        if st != last_st:
            socketio.emit("door", {"status": st})
            last_st = st
        time.sleep(0.3)

threading.Thread(target=door_thread, daemon=True).start()

# ==================================================================
# POSITION THREAD  (20 Hz)
# ==================================================================
def position_thread() -> None:
    last_pos: dict | None = None
    while True:
        try:
            pos = get_position()
            if pos:
                with lock:
                    last_position["abs"].update(pos)
                if pos != last_pos:
                    socketio.emit("position", last_position)
                    last_pos = pos
        except Exception:
            pass
        time.sleep(CFG["POS_HZ"])

threading.Thread(target=position_thread, daemon=True).start()

# ==================================================================
# RESET RELATIVE
# ==================================================================
@app.route("/reset_position", methods=["POST"])
def reset_position():
    with lock:
        for k in last_position["rel"]:
            last_position["rel"][k] = 0.0
    socketio.emit("position", last_position)
    log("🔁 Relative positions reset")
    return jsonify({"ok": True})

# ==================================================================
# STOP DIAGNOSTICS
# ==================================================================
@app.route("/stop")
def stop_diag():
    log("🛑 Diagnostics stopping…")
    os.kill(os.getpid(), signal.SIGINT)
    return jsonify({"ok": True})

# ==================================================================
# MJPEG sub-process watchdog
# ==================================================================
mjpeg_proc: subprocess.Popen | None = None

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0

def kill_stale_mjpeg_processes() -> None:
    pattern = os.path.join(BASE_DIR, "main_mjpeg_server.py")
    try:
        out = subprocess.run(
            ["pgrep", "-f", pattern],
            capture_output=True,
            text=True,
            check=False,
        ).stdout.strip()
        if not out:
            return
        stale_pids = []
        for raw in out.splitlines():
            raw = raw.strip()
            if not raw:
                continue
            pid = int(raw)
            if mjpeg_proc and pid == mjpeg_proc.pid:
                continue
            stale_pids.append(pid)
        if stale_pids:
            log(f"🧹 Killing stale MJPEG process(es): {stale_pids}")
            subprocess.run(["kill", "-TERM", *[str(p) for p in stale_pids]], check=False)
            time.sleep(0.4)
            if is_port_in_use(CFG["MJPEG_PORT"]):
                subprocess.run(["kill", "-KILL", *[str(p) for p in stale_pids]], check=False)
                time.sleep(0.2)
    except Exception as e:
        log(f"⚠️ Could not cleanup stale MJPEG process: {e}")

def start_mjpeg_server() -> subprocess.Popen | None:
    kill_stale_mjpeg_processes()
    cmd = [sys.executable, os.path.join(BASE_DIR, "main_mjpeg_server.py")]
    try:
        proc = subprocess.Popen(cmd, start_new_session=True)
        log(f"🎥 MJPEG server started (PID: {proc.pid}) on port {CFG['MJPEG_PORT']}")
        return proc
    except Exception as e:
        log(f"❌ Failed to start MJPEG server: {e}")
        return None

def watchdog_mjpeg() -> None:
    global mjpeg_proc
    while True:
        time.sleep(10)
        if mjpeg_proc and mjpeg_proc.poll() is None:   # still running
            continue
        if is_port_in_use(CFG["MJPEG_PORT"]):
            log("⚠️ Port 9000 occupied while MJPEG child is down; cleaning stale holder")
            kill_stale_mjpeg_processes()
            if is_port_in_use(CFG["MJPEG_PORT"]):
                log("⚠️ Port 9000 still occupied – waiting…")
                continue
        # safe to restart
        mjpeg_proc = start_mjpeg_server()

threading.Thread(target=watchdog_mjpeg, daemon=True).start()

# ==================================================================
# GRACEFUL SHUTDOWN
# ==================================================================
def _shutdown(signum: int, frame) -> None:
    global stream_enabled, mjpeg_proc
    log("Shutting down gracefully…")
    stream_enabled = False
    if mjpeg_proc and mjpeg_proc.poll() is None:
        mjpeg_proc.terminate()
        try:
            mjpeg_proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            log("⚠️ MJPEG child did not exit on TERM; forcing kill")
            mjpeg_proc.kill()
            try:
                mjpeg_proc.wait(timeout=1)
            except Exception:
                pass
    kill_stale_mjpeg_processes()
    GPIO.cleanup()
    sys.exit(0)

signal.signal(signal.SIGINT, _shutdown)
signal.signal(signal.SIGTERM, _shutdown)

# ==================================================================
# MAIN
# ==================================================================
if __name__ == "__main__":
    kill_stale_mjpeg_processes()
    mjpeg_proc = start_mjpeg_server()
    log(f"🌐 Diagnostics running at http://0.0.0.0:{CFG['DIAG_PORT']}")
    socketio.run(app, host="0.0.0.0", port=CFG["DIAG_PORT"], use_reloader=False)
