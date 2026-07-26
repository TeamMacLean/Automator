# SPDX-License-Identifier: MIT
# Copyright (c) 2025–2026 Rohan R

# ============================================================================
# USB CAMERA YOLO + COLOR-BASED PERMANENT RE-ID  
# ============================================================================
# Coordinate system:  TOP-LEFT origin (matches Klipper X=0,Y=0)
# X_MAX = 290 mm, Y_MAX = 300 mm  (after homography)
# ============================================================================

import os
import cv2
import math
import time
import numpy as np
import onnxruntime as ort
import sqlite3
import json
import traceback
import re
import zxingcpp
from datetime import datetime

# ---------------------------------------------------------------------------
# CONFIGURATION  (env vars override hard-coded paths)
# ---------------------------------------------------------------------------
YOLO_MODEL   = os.environ.get("YOLO_MODEL")   or os.path.expanduser("~/Automator/data/bestnew.onnx")
DB_PATH      = os.environ.get("DB_PATH")      or os.path.expanduser("~/Automator/raw/petri_reid.db")
CALIB_PATH   = os.environ.get("CALIB_PATH")   or os.path.expanduser("~/Automator/data/calibration.json")
CAMERA_CACHE = os.environ.get("CAM_CACHE")    or os.path.expanduser("~/Automator/data/usb_camera_index.json")
RAW_DIR = os.environ.get("RAW_DIR") or os.path.expanduser("~/Automator/raw")

# ---------------------------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------------------------
CONF_THRES   = 0.75
IOU_THRES    = 0.45
X_MAX_MM     = 290
Y_MAX_MM     = 300
DISH_DIAM_MM = 100
MICRO_QR_MAX_LEN = 45
O_QR_MAX_LEN = 45

MICRO_QR_REGEX = re.compile(
    r'^[0-9A-Za-zΔ_.\-,+]+$'
)

# ---------------------------------------------------------------------------
# GEOMETRIC FALLBACK CONSTANTS
# Camera crop 780×1340 px ≈ 300×290 mm; 90-100mm dishes appear as ellipses
# major axis ≈ 414-460 px, minor axis ≈ 234-260 px at this camera geometry.
# ---------------------------------------------------------------------------
FALLBACK_DETECTION_ENABLED        = True
FALLBACK_MIN_RADIUS_PX            = 90     # half the minor axis of a 90mm dish
FALLBACK_MAX_RADIUS_PX            = 260    # half the major axis of a 100mm dish + margin
FALLBACK_MIN_AREA_PX              = 50000  # ~65% of π×117×207; allows partial contours
FALLBACK_MAX_AREA_PX              = 140000
FALLBACK_MIN_CIRCULARITY          = 0.45   # relaxed for perspective-distorted ellipses
FALLBACK_MIN_ASPECT_RATIO         = 0.40   # minor/major; dishes ≈ 0.56 at this camera angle
FALLBACK_MAX_ASPECT_RATIO         = 1.0    # minor/major aspect; must be ≤ 1
FALLBACK_CONFIRM_FRAMES           = 2      # consecutive scan calls before confirming
FALLBACK_STALE_SECONDS            = 300    # 5 min without re-detection → stale
FALLBACK_YOLO_OVERLAP_IOU         = 0.20   # IoU above this → YOLO already covers it
FALLBACK_CENTRE_MATCH_DISTANCE_PX = 80     # px; link candidate to existing track across frames
FALLBACK_DETECT_EVERY_N_FRAMES    = 1      # run on every scan call (1 = always)
FALLBACK_WORKSPACE_MARGIN_PX      = 15     # reject centres within this many px of crop edge
FALLBACK_SCAN_FRAME_COUNT         = 3      # frames captured per scan request
FALLBACK_SCAN_FRAME_DELAY_SEC     = 0.10   # seconds between captured frames
FALLBACK_TRACK_MIN_IOU            = 0.10   # secondary match criterion (vs size ratio)
FALLBACK_TRACK_MAX_SIZE_CHANGE_RATIO = 0.35  # reject track match if bbox dim change > this
FALLBACK_DEBUG_OVERLAY            = False  # draw rejected contours in debug mode

# ---------------------------------------------------------------------------
# GEOMETRIC FALLBACK TRACKER STATE  (module-level, persists across scan calls)
# ---------------------------------------------------------------------------
_fallback_tracker: dict = {}     # stable_id → {bbox, centre_px, consecutive_hits, last_seen_scan_id, last_seen_time, first_seen_time, status}
_fallback_next_id: list = [1]    # mutable int counter via single-element list
_fallback_dismissed: list = []   # [(cx_mm, cy_mm, expiry_time)]
_fallback_scan_counter: list = [0]

# ---------------------------------------------------------------------------
# LOGGING
# ---------------------------------------------------------------------------
def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[detector] {ts}  {msg}", flush=True)

# ---------------------------------------------------------------------------
# CALIBRATION  (homography)
# ---------------------------------------------------------------------------
def load_calibration():
    if not os.path.exists(CALIB_PATH):
        log("⚠  No calibration.json — mm conversion disabled.")
        return None
    try:
        with open(CALIB_PATH, "r") as f:
            data = json.load(f)
        H = np.array(data["H"], dtype=np.float64)
        assert H.shape == (3, 3), "Bad H shape"
        assert abs(np.linalg.det(H)) > 1e-3, "Singular H"
        return H
    except Exception as e:
        log("❌ Calibration invalid: " + traceback.format_exc())
        return None

H_matrix = load_calibration()

def px_to_mm(px: float, py: float):
    if H_matrix is None:
        return None, None
    p = np.array([px, py, 1.0]).reshape(3, 1)
    w = H_matrix @ p
    if w[2, 0] == 0:
        return None, None
    mx = float(w[0, 0] / w[2, 0])
    my = float(w[1, 0] / w[2, 0])
    mx = np.clip(mx, 0, X_MAX_MM)
    my = np.clip(my, 0, Y_MAX_MM)
    return mx, my


def px_to_mm_unclamped(px: float, py: float):
    if H_matrix is None:
        return None, None
    p = np.array([px, py, 1.0]).reshape(3, 1)
    w = H_matrix @ p
    if w[2, 0] == 0:
        return None, None
    mx = float(w[0, 0] / w[2, 0])
    my = float(w[1, 0] / w[2, 0])
    if not (0 <= mx <= X_MAX_MM and 0 <= my <= Y_MAX_MM):
        return None, None
    return mx, my


def begin_fallback_scan() -> int:
    _fallback_scan_counter[0] += 1
    return _fallback_scan_counter[0]


def reset_fallback_tracking() -> None:
    _fallback_tracker.clear()
    _fallback_dismissed.clear()
    _fallback_next_id[0] = 1
    _fallback_scan_counter[0] = 0

# ---------------------------------------------------------------------------
# CAMERA DISCOVERY  (correct resource handling)
# ---------------------------------------------------------------------------
def find_camera() -> int:
    if os.path.exists(CAMERA_CACHE):
        try:
            with open(CAMERA_CACHE, "r") as f:
                idx = int(json.load(f)["index"])
            cap = cv2.VideoCapture(idx)
            try:
                if cap.isOpened() and cap.read()[0]:
                    log(f"Using cached USB camera index {idx}")
                    return idx
            finally:
                cap.release()
        except Exception as e:
            log("Camera cache invalid — rescanning: " + str(e))

    for idx in range(6):
        cap = cv2.VideoCapture(idx)
        try:
            if cap.isOpened() and cap.read()[0]:
                log(f"USB camera detected at index {idx}")
                try:
                    with open(CAMERA_CACHE, "w") as f:
                        json.dump({"index": idx}, f)
                except Exception as e:
                    log("Failed to cache camera index: " + str(e))
                return idx
        finally:
            cap.release()
    raise RuntimeError("No USB camera found")

# ---------------------------------------------------------------------------
# IMAGE PRE-PROCESSING
# ---------------------------------------------------------------------------
def mm_to_px_local(box_w_px: int, box_h_px: int, dish_diameter_mm: float = DISH_DIAM_MM) -> float:
    avg_px = 0.5 * (box_w_px + box_h_px)
    return avg_px / dish_diameter_mm

def zoom_roi(img: np.ndarray, scale: float = 3.0) -> np.ndarray:
    h, w = img.shape[:2]
    return cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)

def is_grayscale(img: np.ndarray, sat_thresh: float = 15) -> bool:
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    return np.mean(hsv[:, :, 1]) < sat_thresh

def apply_ir_correction(img: np.ndarray, gamma: float = 0.6, brightness_scale: float = 0.7) -> np.ndarray:
    inv_gamma = 1.0 / gamma
    table = np.array([(i / 255.0) ** inv_gamma * 255 for i in range(256)]).astype("uint8")
    img = cv2.LUT(img, table)
    return cv2.convertScaleAbs(img, alpha=brightness_scale, beta=0)

def normalise_for_qr(img: np.ndarray) -> np.ndarray:
    if is_grayscale(img):
        img = apply_ir_correction(img)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    gray = cv2.GaussianBlur(gray, (3, 3), 0)
    return gray

# ---------------------------------------------------------------------------
# YOLO INFERENCE
# ---------------------------------------------------------------------------
def preprocess(img: np.ndarray, input_size: int):
    h, w = img.shape[:2]
    scale = input_size / max(h, w)
    nh, nw = int(h * scale), int(w * scale)
    canvas = np.full((input_size, input_size, 3), 114, dtype=np.uint8)
    top, left = (input_size - nh) // 2, (input_size - nw) // 2
    canvas[top:top + nh, left:left + nw] = cv2.resize(img, (nw, nh))
    blob = np.transpose(canvas.astype(np.float32) / 255.0, (2, 0, 1))[None]
    return blob, scale, left, top, w, h

def postprocess(pred, scale, dx, dy, orig_w, orig_h):
    boxes, scores = [], []
    for det in pred[0][0]:
        conf = float(det[4])
        if conf < CONF_THRES:
            continue
        x, y, w, h = det[:4]
        x1 = (x - w / 2 - dx) / scale
        y1 = (y - h / 2 - dy) / scale
        x2 = (x + w / 2 - dx) / scale
        y2 = (y + h / 2 - dy) / scale
        boxes.append([x1, y1, x2, y2])
        scores.append(conf)
    if not boxes:
        return []
    rects = [[int(a), int(b), int(c - a), int(d - b)] for a, b, c, d in boxes]
    idx = cv2.dnn.NMSBoxes(rects, scores, CONF_THRES, IOU_THRES)
    if idx is None or len(idx) == 0:
        return []
    return [(boxes[i][0], boxes[i][1], boxes[i][2], boxes[i][3], scores[i]) for i in idx.flatten()]

# ---------------------------------------------------------------------------
# QR CODE
# ---------------------------------------------------------------------------
def validate_micro_qr(payload: str):
    if not payload:
        return False, "empty"
    payload = payload.strip().upper()
    if len(payload) > MICRO_QR_MAX_LEN:
        return False, "length"
    if not MICRO_QR_REGEX.match(payload):
        return False, "charset"
    return True, None

def detect_qr(gray: np.ndarray):
    try:
        results = zxingcpp.read_barcodes(gray)
        return [r.text.strip().upper() for r in results if r.text]
    except Exception as e:
        log("QR decode error: " + traceback.format_exc())
        return []

# ---------------------------------------------------------------------------
# GEOMETRIC FALLBACK DETECTION
# ---------------------------------------------------------------------------
def _iou(boxA: list, boxB: list) -> float:
    ax1, ay1, ax2, ay2 = boxA
    bx1, by1, bx2, by2 = boxB
    ix1 = max(ax1, bx1); iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2); iy2 = min(ay2, by2)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    if inter == 0:
        return 0.0
    areaA = max(0, ax2 - ax1) * max(0, ay2 - ay1)
    areaB = max(0, bx2 - bx1) * max(0, by2 - by1)
    union = areaA + areaB - inter
    return inter / union if union > 0 else 0.0


def detect_geometric_plate_candidates(frame_crop: np.ndarray, yolo_dets: list) -> list:
    h, w = frame_crop.shape[:2]
    gray = cv2.cvtColor(frame_crop, cv2.COLOR_BGR2GRAY)
    blur = cv2.GaussianBlur(gray, (9, 9), 2)
    edges = cv2.Canny(blur, 30, 80)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    edges = cv2.dilate(edges, kernel, iterations=1)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates = []
    margin = FALLBACK_WORKSPACE_MARGIN_PX

    n_total = len(contours)
    n_area = n_circ = n_aspect = n_workspace = n_yolo = 0

    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < FALLBACK_MIN_AREA_PX or area > FALLBACK_MAX_AREA_PX:
            n_area += 1
            continue

        perimeter = cv2.arcLength(cnt, True)
        if perimeter < 1:
            n_circ += 1
            continue
        circularity = 4 * math.pi * area / (perimeter ** 2)
        if circularity < FALLBACK_MIN_CIRCULARITY:
            n_circ += 1
            continue

        if len(cnt) < 5:
            n_aspect += 1
            continue
        (cx, cy), (axis_a, axis_b), _ = cv2.fitEllipse(cnt)
        major = max(axis_a, axis_b)
        minor = min(axis_a, axis_b)
        if minor < 1:
            n_aspect += 1
            continue
        aspect = minor / major
        if aspect < FALLBACK_MIN_ASPECT_RATIO or aspect > FALLBACK_MAX_ASPECT_RATIO:
            n_aspect += 1
            continue
        half_major = major / 2.0
        if half_major < FALLBACK_MIN_RADIUS_PX or half_major > FALLBACK_MAX_RADIUS_PX:
            n_aspect += 1
            continue

        if cx < margin or cx > w - margin or cy < margin or cy > h - margin:
            n_workspace += 1
            continue

        bx, by, bw, bh = cv2.boundingRect(cnt)
        bbox = [bx, by, bx + bw, by + bh]

        overlaps_yolo = False
        for yd in yolo_dets:
            ybox = [int(yd[0]), int(yd[1]), int(yd[2]), int(yd[3])]
            if _iou(bbox, ybox) > FALLBACK_YOLO_OVERLAP_IOU:
                overlaps_yolo = True
                break
            dist = math.hypot(cx - (yd[0] + yd[2]) / 2, cy - (yd[1] + yd[3]) / 2)
            if dist < FALLBACK_CENTRE_MATCH_DISTANCE_PX:
                overlaps_yolo = True
                break
        if overlaps_yolo:
            n_yolo += 1
            continue

        candidates.append({
            "bbox": bbox,
            "centre_px": [int(cx), int(cy)],
            "area": int(area),
            "circularity": round(circularity, 3),
            "aspect": round(aspect, 3),
        })

    n_accepted = len(candidates)
    log(f"Geometric candidates: {n_total} contours, area={n_area}, circ={n_circ}, "
        f"ellipse={n_aspect}, edge={n_workspace}, yolo={n_yolo}, accepted={n_accepted}")

    return candidates


def update_fallback_tracks(candidates: list, scan_id: int) -> None:
    now = time.time()

    stale = [tid for tid, t in _fallback_tracker.items()
             if now - t["last_seen_time"] > FALLBACK_STALE_SECONDS]
    for tid in stale:
        log(f"Fallback track {tid} stale — removing.")
        del _fallback_tracker[tid]

    matched_track_ids = set()
    for cand in candidates:
        ccx, ccy = cand["centre_px"]
        cbbox = cand["bbox"]
        best_id = None
        best_dist = FALLBACK_CENTRE_MATCH_DISTANCE_PX
        for tid, t in _fallback_tracker.items():
            if tid in matched_track_ids:
                continue
            tcx, tcy = t["centre_px"]
            dist = math.hypot(ccx - tcx, ccy - tcy)
            if dist >= best_dist:
                continue
            tbbox = t["bbox"]
            iou = _iou(cbbox, tbbox)
            tw = tbbox[2] - tbbox[0]; th = tbbox[3] - tbbox[1]
            cw = cbbox[2] - cbbox[0]; ch = cbbox[3] - cbbox[1]
            size_ok = False
            if tw > 0 and th > 0 and cw > 0 and ch > 0:
                wr = max(tw, cw) / min(tw, cw) - 1.0
                hr = max(th, ch) / min(th, ch) - 1.0
                size_ok = (wr <= FALLBACK_TRACK_MAX_SIZE_CHANGE_RATIO and
                           hr <= FALLBACK_TRACK_MAX_SIZE_CHANGE_RATIO)
            if iou < FALLBACK_TRACK_MIN_IOU and not size_ok:
                continue
            best_dist = dist
            best_id = tid

        if best_id is not None:
            t = _fallback_tracker[best_id]
            alpha = 0.3
            t["centre_px"] = [
                int(t["centre_px"][0] * (1 - alpha) + ccx * alpha),
                int(t["centre_px"][1] * (1 - alpha) + ccy * alpha),
            ]
            t["bbox"] = cand["bbox"]
            prev_scan = t.get("last_seen_scan_id", -999)
            if prev_scan == scan_id or prev_scan == scan_id - 1:
                t["consecutive_hits"] += 1
            else:
                t["consecutive_hits"] = 1
            t["last_seen_scan_id"] = scan_id
            t["last_seen_time"] = now
            if t["consecutive_hits"] >= FALLBACK_CONFIRM_FRAMES and t["status"] == "candidate":
                t["status"] = "confirmed"
                log(f"Fallback track {best_id} confirmed ({t['consecutive_hits']} consecutive).")
            matched_track_ids.add(best_id)
        else:
            new_id = f"FALLBACK-{_fallback_next_id[0]:04d}"
            _fallback_next_id[0] += 1
            _fallback_tracker[new_id] = {
                "bbox": cand["bbox"],
                "centre_px": cand["centre_px"],
                "consecutive_hits": 1,
                "last_seen_scan_id": scan_id,
                "last_seen_time": now,
                "first_seen_time": now,
                "status": "confirmed" if FALLBACK_CONFIRM_FRAMES <= 1 else "candidate",
            }
            log(f"New fallback track {new_id} at px {cand['centre_px']}.")


def dismiss_fallback_track(track_id: str) -> None:
    t = _fallback_tracker.pop(track_id, None)
    if t is not None:
        mmx, mmy = px_to_mm(t["centre_px"][0], t["centre_px"][1])
        if mmx is not None:
            expiry = time.time() + FALLBACK_STALE_SECONDS
            _fallback_dismissed.append((mmx, mmy, expiry))
            log(f"Fallback {track_id} dismissed; position ({mmx:.1f},{mmy:.1f}) suppressed until {expiry:.0f}.")


def retire_fallback_tracks_overlapping_yolo(yolo_dets: list) -> list:
    retired = []
    for tid in list(_fallback_tracker.keys()):
        t = _fallback_tracker[tid]
        for yd in yolo_dets:
            ybox = [int(yd[0]), int(yd[1]), int(yd[2]), int(yd[3])]
            iou = _iou(t["bbox"], ybox)
            dist = math.hypot(t["centre_px"][0] - (yd[0] + yd[2]) / 2,
                              t["centre_px"][1] - (yd[1] + yd[3]) / 2)
            if iou > FALLBACK_YOLO_OVERLAP_IOU or dist < FALLBACK_CENTRE_MATCH_DISTANCE_PX:
                log(f"Fallback track {tid} superseded by YOLO (IoU={iou:.2f}, dist={dist:.1f}px).")
                retired.append(tid)
                _fallback_tracker.pop(tid, None)
                break
    return retired


def get_confirmed_fallback_plates_for_scan(scan_id: int) -> list:
    now = time.time()
    _fallback_dismissed[:] = [(x, y, exp) for x, y, exp in _fallback_dismissed if exp > now]

    result = []
    ghost_count = 0
    for tid, t in _fallback_tracker.items():
        if t["status"] != "confirmed":
            continue
        if t["last_seen_scan_id"] != scan_id:
            ghost_count += 1
            continue
        cx, cy = t["centre_px"]
        rx, ry = px_to_mm_unclamped(cx, cy)
        if rx is None:
            continue
        if any(abs(rx - dx) < 5 and abs(ry - dy) < 5 for dx, dy, _ in _fallback_dismissed):
            continue
        bx1, by1, bx2, by2 = t["bbox"]
        radius_px = int(math.hypot(bx2 - bx1, by2 - by1) / 2)
        result.append({
            "track_id": tid,
            "bbox": t["bbox"],
            "centre_px": [cx, cy],
            "radius_px": radius_px,
        })

    if ghost_count:
        log(f"Fallback: {ghost_count} ghost track(s) suppressed (not seen in scan {scan_id}).")
    log(f"Fallback: {len(result)} confirmed plate(s) published for scan {scan_id}.")
    return result


# ---------------------------------------------------------------------------
# PERSISTENT ID  (SQLite WAL mode for concurrency)
# ---------------------------------------------------------------------------
class PlateID:
    def __init__(self, cursor: sqlite3.Cursor):
        self.db = cursor
        self.fp_to_id = {}
        self.next_id = 0
        self._load_existing()

    def _load_existing(self):
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS plates (
                plate_id INTEGER PRIMARY KEY,
                qr_payload TEXT UNIQUE
            )
        """)
        self.db.execute(
            "CREATE INDEX IF NOT EXISTS idx_qr ON plates(qr_payload)"
        )
        for pid, payload in self.db.execute("SELECT plate_id, qr_payload FROM plates").fetchall():
            self.fp_to_id[payload] = pid
            self.next_id = max(self.next_id, pid + 1)

    def get_id(self, qr_list):
        payload = qr_list[0]
        if payload in self.fp_to_id:
            return self.fp_to_id[payload]
        pid = self.next_id
        self.next_id += 1
        self.fp_to_id[payload] = pid
        self.db.execute("INSERT OR IGNORE INTO plates (plate_id, qr_payload) VALUES (?, ?)", (pid, payload))
        return pid

# ---------------------------------------------------------------------------
# CIRCULAR CROP
# ---------------------------------------------------------------------------
def crop_circular_roi(img: np.ndarray, cx: int, cy: int, radius: int) -> np.ndarray:
    h, w = img.shape[:2]
    x1 = max(0, int(cx - radius))
    y1 = max(0, int(cy - radius))
    x2 = min(w, int(cx + radius))
    y2 = min(h, int(cy + radius))
    roi = img[y1:y2, x1:x2].copy()
    mask = np.zeros(roi.shape[:2], dtype=np.uint8)
    rr = min(roi.shape[0], roi.shape[1]) // 2
    cv2.circle(mask, (roi.shape[1] // 2, roi.shape[0] // 2), rr, 255, -1)
    return cv2.bitwise_and(roi, roi, mask=mask)

# ---------------------------------------------------------------------------
# MAIN DETECTION ENTRY POINT  
# ---------------------------------------------------------------------------
def detect_plates(save_path: str | None = None) -> dict:
    save_path = save_path or os.path.expanduser("~/Automator/dev2/static/workspace_overlay.png")
    seen_qr = set()

    # ---- camera ----
    idx = find_camera()
    cap = cv2.VideoCapture(idx)
    try:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
        ret, frame = cap.read()
        if not ret:
            log("❌ Camera capture failed")
            return {}
    finally:
        cap.release()

    # ---- crop to ROI ----
    frame = cv2.flip(frame, 1)
    frame = frame[120:900, 260:1600]

    # ---- YOLO ----
    if not os.path.exists(YOLO_MODEL):
        log(f"YOLO model not found: {YOLO_MODEL}")
        return {}
    ort_sess = ort.InferenceSession(YOLO_MODEL, providers=["CPUExecutionProvider"])
    in_name = ort_sess.get_inputs()[0].name
    in_size = ort_sess.get_inputs()[0].shape[2]
    blob, scale, dx, dy, ow, oh = preprocess(frame, in_size)
    preds = ort_sess.run(None, {in_name: blob})
    dets = postprocess(preds, scale, dx, dy, ow, oh)
    log(f"YOLO detected {len(dets)} plates")

    # ---- DB ----
    conn = sqlite3.connect(DB_PATH, timeout=10, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    cur = conn.cursor()
    idsys = PlateID(cur)

    out = {}
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

        # read QR
        payloads = detect_qr(gray)
        if not payloads:
            payloads = detect_qr(255 - gray)
        if not payloads:
            log(f"Plate {i} no QR")
            continue
        payload = payloads[0]
        valid, reason = validate_micro_qr(payload)
        if not valid:
            log(f"Plate {i} invalid QR [{payload}] ({reason})")
            continue
        if payload in seen_qr:
            log(f"Plate {i} duplicate QR [{payload}]")
            continue
        seen_qr.add(payload)
        pid = idsys.get_id([payload])
        mmx, mmy = px_to_mm((x1 + x2) / 2, (y1 + y2) / 2)
        key = f"plate_{i:02d}"
        out[key] = {
            "id": pid,
            "x_mm": round(mmx, 2),
            "y_mm": round(mmy, 2),
            "confidence": round(conf, 3),
            "desc": payload
        }
        # annotate frame
        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.putText(frame, f"{key} ID{pid}", (x1, y1 - 6), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 0), 2)

    # ---- save overlay ----
    cv2.imwrite(save_path, frame)
    log(f"Overlay saved → {save_path}")
    os.makedirs(RAW_DIR, exist_ok=True)
    raw_path = os.path.join(RAW_DIR, "plates_raw.json")

    with open(raw_path, "w") as f:
        json.dump(out, f, indent=2)
    conn.commit()
    conn.close()
    return out

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import json
    print(json.dumps(detect_plates(), indent=2))
