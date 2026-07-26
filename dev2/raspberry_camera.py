# SPDX-License-Identifier: MIT
# Copyright (c) 2025–2026 Rohan R

"""
Raspberry Pi Camera Capture Utility
-----------------------------------
Calibration-aware camera utility with:
- PiCameraCapture: compatible capture interface (`capture_image`)
- HeadlessCameraIndividual: preview + high-res test workflow
"""

import json
import os
import time

import cv2
try:
    from libcamera import controls
    from picamera2 import Picamera2
except ImportError:
    controls = None   # type: ignore[assignment]
    Picamera2 = None  # type: ignore[assignment,misc]

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DATA_DIR = os.path.join(BASE_DIR, "data", "captures")
CONFIG_FILE = os.path.join(DATA_DIR, "camera_config.json")
os.makedirs(DATA_DIR, exist_ok=True)

if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "r") as f:
        _cfg = json.load(f)
else:
    _cfg = {}

EXPOSURE = float(_cfg.get("exposure", 0))
FOCUS = _cfg.get("focus", 0)
DATA_TX_SCALE = 1.0  # Current: 1.0 (full data rate). Set 0.5 for ~75% less pixel data, or 0.25 for ~94% less.
STILL_SIZE = (max(1, int(3280 * DATA_TX_SCALE)), max(1, int(2464 * DATA_TX_SCALE)))
PREVIEW_SIZE = (max(1, int(1600 * DATA_TX_SCALE)), max(1, int(1200 * DATA_TX_SCALE)))
CAMERA_BUFFER_COUNT = 4
CAMERA_WARMUP_SEC = 1.0
CAMERA_PRIME_FRAMES = 2


def _prime_camera_stream(picam2: Picamera2, frames: int = CAMERA_PRIME_FRAMES):
    """Discard startup frames; helps settle exposure/readout before capture."""
    for _ in range(max(0, int(frames))):
        try:
            picam2.capture_array()
        except RuntimeError:
            break


def _apply_calibration(picam2: Picamera2):
    """Apply configured camera controls safely."""
    try:
        controls_dict = {"ExposureValue": EXPOSURE}
        if FOCUS not in (None, "", 0):
            controls_dict["AfMode"] = controls.AfModeEnum.Manual
            controls_dict["LensPosition"] = float(FOCUS)
        else:
            controls_dict["AfMode"] = controls.AfModeEnum.Continuous
        picam2.set_controls(controls_dict)
        time.sleep(0.8)
    except RuntimeError as e:
        print(f"Some controls not supported: {e}")


class PiCameraCapture:
    """
    Backward-compatible camera wrapper used by controller integrations.
    """

    def __init__(self, save_dir):
        self.save_dir = save_dir
        os.makedirs(self.save_dir, exist_ok=True)
        self.picam2 = None

    def _open_camera(self):
        """Initialize PiCamera2 safely."""
        try:
            self.picam2 = Picamera2()
            config = self.picam2.create_still_configuration(
                main={"size": STILL_SIZE},
                buffer_count=CAMERA_BUFFER_COUNT,
            )
            self.picam2.configure(config)
            self.picam2.start()
            time.sleep(CAMERA_WARMUP_SEC)
            _apply_calibration(self.picam2)
            _prime_camera_stream(self.picam2)
            print("PiCamera started")
        except RuntimeError as e:
            print(f"Failed to start PiCamera: {e}")
            self.picam2 = None

    def close(self):
        if not self.picam2:
            return
        try:
            self.picam2.stop()
            self.picam2.close()
        except RuntimeError:
            pass
        self.picam2 = None

    def capture_image(self, filename):
        """Capture an image and auto-release camera."""
        path = os.path.join(self.save_dir, filename)
        self._open_camera()
        if not self.picam2:
            print("PiCamera not initialized; skipping capture")
            return None
        try:
            self.picam2.capture_file(path)
            print(f"Image saved -> {path}")
            return path
        except RuntimeError as e:
            print(f"Capture failed: {e}")
            return None
        finally:
            self.close()


class HeadlessCameraIndividual:
    """
    Preview + high-res utility for direct testing outside controller runtime.
    """

    def __init__(self):
        self.picam2 = Picamera2()
        self.highres_config = self.picam2.create_still_configuration(
            main={"size": STILL_SIZE},
            buffer_count=CAMERA_BUFFER_COUNT,
        )
        self.preview_config = self.picam2.create_preview_configuration(
            main={"size": PREVIEW_SIZE},
            buffer_count=CAMERA_BUFFER_COUNT,
        )
        self.picam2.configure(self.preview_config)
        self.picam2.start()
        time.sleep(CAMERA_WARMUP_SEC)
        _apply_calibration(self.picam2)
        _prime_camera_stream(self.picam2)

    def capture_preview(self):
        return self.picam2.capture_array()

    def capture_highres(self, prefix="individual"):
        self.picam2.stop()
        self.picam2.configure(self.highres_config)
        self.picam2.start()
        time.sleep(CAMERA_WARMUP_SEC)
        _prime_camera_stream(self.picam2)
        frame = self.picam2.capture_array()
        fname = f"{prefix}_{int(time.time())}.png"
        path = os.path.join(DATA_DIR, fname)
        cv2.imwrite(path, cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
        print(f"Saved {path}")
        self.picam2.stop()
        self.picam2.configure(self.preview_config)
        self.picam2.start()
        _apply_calibration(self.picam2)
        return path, frame

    def close(self):
        try:
            self.picam2.stop()
            self.picam2.close()
        except RuntimeError:
            pass


if __name__ == "__main__":
    import tkinter as tk
    from tkinter import messagebox

    def capture_button_action():
        path, _ = cam.capture_highres("test_individual")
        messagebox.showinfo("Capture", f"High-res image saved: {path}")

    cam = HeadlessCameraIndividual()
    root = tk.Tk()
    root.title("Individual Camera Test")
    capture_btn = tk.Button(root, text="Capture High-Res", command=capture_button_action)
    capture_btn.pack(pady=10)
    try:
        while True:
            img = cam.capture_preview()
            cv2.imshow("Preview", cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
            key = cv2.waitKey(100)
            if key == ord("c"):
                cam.capture_highres("test_individual")
            if key == 27:  # ESC
                break
            root.update()
    finally:
        cam.close()
        cv2.destroyAllWindows()
        root.destroy()
