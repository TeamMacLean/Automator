# SPDX-License-Identifier: MIT
# Copyright (c) 2025–2026 Rohan R

"""
Headless G-code Sender for Klipper + Moonraker
----------------------------------------------
Compatible with MKS Robin Nano V3.1 and vacuum system.

Includes:
- safe X/Y/Z movement
- automatic motor torque release (M84)
- vacuum pump + solenoid + rotation servo control
"""

import requests
import time
from datetime import datetime
import threading

_gcode_lock = threading.RLock()  # Global lock for G-code sending

# ===============================================================
# CONFIGURATION
# ===============================================================
MOONRAKER_URL = "http://localhost:7125/printer/gcode/script"
INFO_URL = "http://localhost:7125/printer/info"

# UPDATED LIMITS (PER NEW CONFIG)
MAX_X, MAX_Y, MAX_Z = 298, 300, 80

# Track current position without needing Klipper
current_pos = {"x": 0.0, "y": 0.0, "z": 0.0}

# ===============================================================
# LOGGING
# ===============================================================
def log(msg: str):
    """Log messages with a timestamp."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

# ===============================================================
# CORE: SEND RAW GCODE
# ===============================================================
def send_gcode(cmd: str, timeout: int | None = None) -> bool:
    """
    Send raw G-code to the printer via Moonraker.
    Thread-safe.
    """
    if timeout is None:
        # M400 blocks until the motion queue drains; long moves can exceed 3 s.
        timeout = 30 if cmd.strip().upper() == "M400" else 3
    payload = {"script": cmd}
    for attempt in range(2):
        try:
            with _gcode_lock:   # 🔒 CRITICAL CHANGE
                r = requests.post(MOONRAKER_URL, json=payload, timeout=timeout)

            if r.status_code == 200:
                log(f"✅ Sent: {cmd}")
                return True
            else:
                log(f"⚠️ HTTP {r.status_code}: {r.text}")
        except requests.exceptions.RequestException as e:
            log(f"❌ Error sending '{cmd}' (attempt {attempt+1}): {e}")
            time.sleep(1)

    return False

def send_gcode_sync(cmd: str):
    """
    Send G-code and wait for completion (M400 barrier).
    """
    
    ok = send_gcode(cmd)
    if not ok:
        return False

    # Wait for motion queue to finish
    return send_gcode("M400")

# ===============================================================
# INITIALIZE / PREPARE PRINTER
# ===============================================================
def prepare_printer():
    """
    Restart Klipper and wait for readiness.
    
    Returns:
        bool: True if the printer is ready, False otherwise.
    """
    log("🔄 Restarting Klipper firmware...")
    send_gcode("FIRMWARE_RESTART")
    time.sleep(2)

    # Wait for readiness
    for _ in range(25):
        try:
            r = requests.get(INFO_URL, timeout=2)
            if r.ok:
                state = r.json().get("result", {}).get("state", "")
                if state == "ready":
                    log("🟢 Klipper ready")
                    break
        except (requests.exceptions.RequestException, ValueError):
            pass
        time.sleep(1)
    else:
        log("⚠️ Timeout waiting for Klipper readiness")
        return False

    send_gcode("G90")
    return True

# ===============================================================
# MOVEMENT COMMANDS
# ===============================================================
def move_to(x=None, y=None, z=None, feed=None):
    """
    Synchronized trapezoidal XY motion.
    
    Parameters:
        x (float): The target X position.
        y (float): The target Y position.
        z (float): The target Z position.
        feed (int): The feedrate (default: 6000 for XY, 3000 for Z).
    
    Returns:
        dict: The updated current position.
    """
    # Clamp inputs to machine limits
    if x is not None:
        x = min(max(0, float(x)), MAX_X)
    if y is not None:
        y = min(max(0, float(y)), MAX_Y)
    if z is not None:
        z = min(max(0, float(z)), MAX_Z)

    # Auto feedrate logic
    if feed is None:
        if z is not None and (x is None and y is None):
            feed = 3000      # Z-only move
        else:
            feed = 6000      # XY or XYZ combined move

    # Build one single synchronized G1 block
    cmd = "G1"
    if x is not None:
        cmd += f" X{x:.2f}"
    if y is not None:
        cmd += f" Y{y:.2f}"
    if z is not None:
        cmd += f" Z{z:.2f}"
    cmd += f" F{feed}"

    # Emit synchronized trapezoidal motion
    if not send_gcode_sync(cmd):
        return False

    # Update internal position tracking
    if x is not None:
        current_pos["x"] = x
    if y is not None:
        current_pos["y"] = y
    if z is not None:
        current_pos["z"] = z

    return current_pos.copy()

def jog(dx=0, dy=0, dz=0, feed=None):
    """
    Relative move based on current stored position.
    
    Parameters:
        dx (float): The relative change in X position.
        dy (float): The relative change in Y position.
        dz (float): The relative change in Z position.
        feed (int): The feedrate (default: 4500 for Z, 6000 for XY).
    
    Returns:
        dict: The updated current position.
    """
    if feed is None:
        feed = 4500 if dz != 0 else 6000
    new_x = current_pos["x"] + dx if dx != 0 else None
    new_y = current_pos["y"] + dy if dy != 0 else None
    new_z = current_pos["z"] + dz if dz != 0 else None
    return move_to(new_x, new_y, new_z, feed)

def set_relative(mode=True):
    """
    Set the coordinate system to relative or absolute.
    
    Parameters:
        mode (bool): True for relative, False for absolute.
    """
    send_gcode("G91" if mode else "G90")

def get_position():
    """
    Get the current position.
    
    Returns:
        dict: The current position.
    """
    return dict(current_pos)

# ===============================================================
# SAFETY-ENHANCED MOTION (AUTO MOTOR RELEASE)
# ===============================================================
def safe_move_to(x=None, y=None, z=None, feed=3000, release_delay=0.2):
    """
    Safe move with auto motor release.
    
    Parameters:
        x (float): The target X position.
        y (float): The target Y position.
        z (float): The target Z position.
        feed (int): The feedrate.
        release_delay (float): The delay before releasing motors.
    
    Returns:
        dict: The updated current position.
    """
    pos = move_to(x, y, z, feed)
    time.sleep(release_delay)
    send_gcode("M84")
    log("💤 Motors released (auto torque-off).")
    return pos

def safe_jog(dx=0, dy=0, dz=0, feed=3000, release_delay=0.2):
    """
    Safe jog with auto motor release.
    
    Parameters:
        dx (float): The relative change in X position.
        dy (float): The relative change in Y position.
        dz (float): The relative change in Z position.
        feed (int): The feedrate.
        release_delay (float): The delay before releasing motors.
    
    Returns:
        dict: The updated current position.
    """
    pos = jog(dx, dy, dz, feed)
    time.sleep(release_delay)
    send_gcode("M84")
    log("💤 Motors released after jog.")
    return pos

# ===============================================================
# VACUUM SYSTEM 
# ===============================================================
def vacuum(action: str):
    """
    Execute a vacuum action.
    
    Parameters:
        action (str): The vacuum action ("suck_hold", "hold", "release").
    """
    macro_map = {
        "suck_hold": "SUCK_HOLD",
        "hold": "HOLD",
        "release": "RELEASE"
    }

    macro = macro_map.get(action.lower())
    if not macro:
        log(f"⚠️ Unknown vacuum action: {action}")
        return

    send_gcode_sync(macro)
    log(f"🧲 Executed vacuum action: {macro}")

# ===============================================================
# ROTATION SERVO CONTROL 
# ===============================================================
def rotate(angle: float):
    """
    Rotate the servo to a specified angle.
    
    Parameters:
        angle (float): The angle to rotate to (0-90 degrees).
    """
    send_gcode_sync(f"ROTATE ANGLE={angle}")
    log(f"🔄 Rotated servo to {angle}°")

# ===============================================================
# INITIALIZATION WRAPPER
# ===============================================================
def init_klipper():
    """
    Check Moonraker connectivity and initialize the printer.
    
    Returns:
        bool: True if Moonraker is reachable, False otherwise.
    """
    log("🔌 Checking Moonraker connectivity...")
    try:
        r = requests.get(INFO_URL, timeout=8)
        if r.ok:
            state = r.json().get("result", {}).get("state", "")
            log(f"🟢 Moonraker reachable — printer state: {state}")
            return True
        else:
            log(f"⚠️ Moonraker returned HTTP {r.status_code}")
            return False
    except (requests.exceptions.RequestException, ValueError) as e:
        log(f"❌ Cannot connect to Moonraker: {e}")
        return False

# ===============================================================
# STANDALONE TEST
# ===============================================================
if __name__ == "__main__":
    if prepare_printer():
        safe_move_to(x=20, y=20)
        time.sleep(1)
        safe_move_to(x=100, y=100)
        time.sleep(1)

        vacuum("suck_hold")
        time.sleep(1)
        vacuum("hold")
        time.sleep(1)
        vacuum("release")

        rotate(45)

        safe_move_to(x=0, y=0, z=0)
        log("✅ Motion + vacuum + servo test complete.")
