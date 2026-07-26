# SPDX-License-Identifier: MIT
# Copyright (c) 2025–2026 Rohan R

import cv2
import numpy as np
import json
import math
from datetime import datetime

# ============================================================
# SETTINGS
# ============================================================

CAMERA_INDEX = 0
WINDOW_NAME = "Calibration (click 4 corners)"

OUTPUT_JSON = "calibration.json"

CAPTURE_WIDTH = None
CAPTURE_HEIGHT = None

# ------------------------------------------------------------
# REAL WORLD WORKSPACE POINTS (mm)
# Order must match click order
#
# P0 = top-left
# P1 = bottom-left
# P2 = bottom-right
# P3 = top-right
# ------------------------------------------------------------

WORLD_POINTS_MM = np.array([
    [-70.659356, 502.220780],
    [97.263479, 504.052379],
    [110.161839, 353.802036],
    [-66.909346, 353.649422]
], dtype=np.float64)

# ============================================================
# GLOBALS
# ============================================================

clicked_pixels = []

frame_w = None
frame_h = None


# ============================================================
# FUNCTIONS
# ============================================================

def flip_raw_to_display(raw):
    return cv2.flip(raw, 1)


def apply_homography(H, x, y):

    p = np.array([x, y, 1.0], dtype=np.float64)
    q = H @ p

    return q[0] / q[2], q[1] / q[2]


def compute_resolution(H, width, height):

    corners = [
        (0,0),
        (width-1,0),
        (0,height-1),
        (width-1,height-1)
    ]

    pts_mm = [apply_homography(H,x,y) for x,y in corners]

    def dist(a,b):
        return math.hypot(b[0]-a[0], b[1]-a[1])

    top = dist(pts_mm[0],pts_mm[1])
    bottom = dist(pts_mm[2],pts_mm[3])
    left = dist(pts_mm[0],pts_mm[2])
    right = dist(pts_mm[1],pts_mm[3])

    return {
        "top_mm_per_px": top/(width-1),
        "bottom_mm_per_px": bottom/(width-1),
        "left_mm_per_px": left/(height-1),
        "right_mm_per_px": right/(height-1),
        "avg_x_mm_per_px": ((top+bottom)/2)/(width-1),
        "avg_y_mm_per_px": ((left+right)/2)/(height-1)
    }


def draw_overlay(frame):

    vis = frame.copy()

    text = f"Click 4 points: {len(clicked_pixels)}/4"

    cv2.putText(vis,text,(10,30),
        cv2.FONT_HERSHEY_SIMPLEX,0.8,(0,255,0),2)

    for i,p in enumerate(clicked_pixels):

        cv2.circle(vis,p,6,(0,0,255),-1)

        cv2.putText(vis,f"P{i}",
            (p[0]+10,p[1]-10),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,(0,255,255),2)

    return vis


# ============================================================
# MOUSE
# ============================================================

def mouse(event,x,y,flags,param):

    if event == cv2.EVENT_LBUTTONDOWN:

        if len(clicked_pixels) < 4:

            clicked_pixels.append((x,y))

            print("Clicked",len(clicked_pixels)-1,":",x,y)


# ============================================================
# MAIN
# ============================================================

def main():

    global frame_w,frame_h

    cap = cv2.VideoCapture(CAMERA_INDEX)

    if CAPTURE_WIDTH:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,CAPTURE_WIDTH)

    if CAPTURE_HEIGHT:
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT,CAPTURE_HEIGHT)

    ret,frame = cap.read()

    if not ret:
        print("Camera failed")
        return

    frame = flip_raw_to_display(frame)

    frame_h,frame_w = frame.shape[:2]

    cv2.namedWindow(WINDOW_NAME)
    cv2.setMouseCallback(WINDOW_NAME,mouse)

    while True:

        ret,frame = cap.read()

        if not ret:
            break

        frame = flip_raw_to_display(frame)

        vis = draw_overlay(frame)

        cv2.imshow(WINDOW_NAME,vis)

        if len(clicked_pixels)==4:
            break

        key = cv2.waitKey(1)&0xFF

        if key==27 or key==ord("q"):
            cap.release()
            cv2.destroyAllWindows()
            return

    cap.release()
    cv2.destroyAllWindows()

    # --------------------------------------------------------
    # COMPUTE HOMOGRAPHY
    # --------------------------------------------------------

    pixel_pts = np.array(clicked_pixels,dtype=np.float64)

    H,_ = cv2.findHomography(pixel_pts,WORLD_POINTS_MM)

    print("\nComputed Homography:\n")
    print(H)

    # --------------------------------------------------------
    # RESOLUTION
    # --------------------------------------------------------

    res = compute_resolution(H,frame_w,frame_h)

    print("\nPixel -> mm resolution")

    for k,v in res.items():
        print(k,":",v)

    # --------------------------------------------------------
    # SAVE JSON
    # --------------------------------------------------------

    data = {
        "H": H.tolist()
    }

    with open("calibration.json", "w") as f:
        json.dump(data, f, indent=2)

    print("\nSaved calibration.json")


if __name__=="__main__":
    main()
