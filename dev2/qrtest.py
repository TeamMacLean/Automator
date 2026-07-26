# SPDX-License-Identifier: MIT
# Copyright (c) 2025–2026 Rohan R

import cv2
import zxingcpp
import numpy as np

CAMERA_INDEX = 2   # change if needed
FRAME_W = 680
FRAME_H = 680
FONT = cv2.FONT_HERSHEY_SIMPLEX

def enhance_variants(frame):
    """
    Generate multiple internal representations for robust QR detection.
    Returned images are NOT shown — only used for decoding.
    """
    variants = []

    # 1) Raw colour
    variants.append(frame)

    # 2) Grayscale + contrast stretch
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)
    variants.append(gray)

    # 3) Adaptive threshold
    thr = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31, 5
    )
    variants.append(thr)
    variants.append(255 - thr)

    # 4) Sharpened grayscale
    kernel = np.array([[0,-1,0],[-1,5,-1],[0,-1,0]])
    sharp = cv2.filter2D(gray, -1, kernel)
    variants.append(sharp)

    # 5) Zoomed versions (critical for small QR)
    for img in variants[:]:
        zoom = cv2.resize(img, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)
        variants.append(zoom)

    return variants

def draw_qr(frame, result, idx):
    pos = result.position
    if pos is None:
        return

    pts = np.array([
        [pos.top_left.x,     pos.top_left.y],
        [pos.top_right.x,    pos.top_right.y],
        [pos.bottom_right.x, pos.bottom_right.y],
        [pos.bottom_left.x,  pos.bottom_left.y],
    ], dtype=np.int32)

    cv2.polylines(frame, [pts], True, (0, 255, 0), 2)

    label = f"QR {idx}: {result.text}"
    x, y = pts[0]
    cv2.putText(frame, label, (x, y - 10),
                FONT, 0.6, (0, 255, 0), 2, cv2.LINE_AA)


def main():
    cap = cv2.VideoCapture(CAMERA_INDEX)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, FRAME_W)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)

    if not cap.isOpened():
        print("❌ Camera open failed")
        return

    print("📷 Live QR auto-detection running — press Q to quit")

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        found = {}
        variants = enhance_variants(frame)

        # Try all variants until QR found
        for img in variants:
            results = zxingcpp.read_barcodes(img)
            for r in results:
                if r.text and r.text not in found:
                    found[r.text] = r

        # Draw results on ORIGINAL colour frame
        for i, r in enumerate(found.values(), start=1):
            draw_qr(frame, r, i)

        cv2.imshow("Live QR Camera (robust)", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
