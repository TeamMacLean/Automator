#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2025–2026 Rohan R

"""
Standalone MJPEG server 
Safe against browser refreshes and reconnects
"""

import cv2
import time
import signal
import sys
from flask import Flask, Response

app = Flask(__name__)

# --------------------------------------------------
# CAMERA INITIALIZATION (ONCE)
# --------------------------------------------------
def find_camera():
    print("🔍 Scanning for available camera...")
    for idx in range(5):
        cap = cv2.VideoCapture(idx)
        time.sleep(0.3)
        ret, _ = cap.read()
        if ret:
            print(f"🎥 Camera detected at index {idx}")
            return cap, idx
        cap.release()
    return None, None


cap, CAMERA_INDEX = find_camera()
if cap is None:
    raise RuntimeError("❌ No available USB camera found")

cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
print(f"🎥 MJPEG camera initialized (index {CAMERA_INDEX})")

def cleanup_and_exit(signum=None, frame=None):
    try:
        if cap is not None:
            cap.release()
    finally:
        if signum is not None:
            print(f"🛑 MJPEG server exiting on signal {signum}")
        sys.exit(0)

signal.signal(signal.SIGINT, cleanup_and_exit)
signal.signal(signal.SIGTERM, cleanup_and_exit)

# --------------------------------------------------
# STREAM GENERATOR 
# --------------------------------------------------
def generate_stream():
    while True:
        ret, frame = cap.read()
        if not ret:
            time.sleep(0.02)
            continue

        frame = cv2.flip(frame, 1)
        ok, jpeg = cv2.imencode(".jpg", frame)
        if not ok:
            continue

        yield (
            b"--frame\r\n"
            b"Content-Type: image/jpeg\r\n\r\n"
            + jpeg.tobytes()
            + b"\r\n"
        )

# --------------------------------------------------
# ROUTE
# --------------------------------------------------
@app.route("/stream")
def stream():
    return Response(
        generate_stream(),
        mimetype="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0, no-transform",
            "Pragma": "no-cache",
            "X-Accel-Buffering": "no",
            "Access-Control-Allow-Origin": "*",
        },
    )

# --------------------------------------------------
# MAIN
# --------------------------------------------------
if __name__ == "__main__":
    print("📡 MJPEG server running at http://0.0.0.0:9000/stream")
    try:
        app.run(host="0.0.0.0", port=9000, threaded=True, use_reloader=False)
    finally:
        cleanup_and_exit()
