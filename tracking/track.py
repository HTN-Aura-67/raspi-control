import cv2
import numpy as np
import time

# -------- Settings --------
CAM_INDEX = 0
FRAME_W, FRAME_H = 320, 240
TRACKER_KIND = "CSRT"   # "CSRT" or "KCF"
TARGET_AREA = 12000
Kp_turn = 0.7
EMA_ALPHA = 0.3
MIN_AREA = 60

def clamp(x, lo, hi): return lo if x < lo else hi if x > hi else x
def drive(l, r): print(f"L={l:+.2f} R={r:+.2f}")

def create_tracker(kind: str):
    k = kind.upper()
    if k == "CSRT":
        return cv2.legacy.TrackerCSRT_create()
    elif k == "KCF":
        return cv2.legacy.TrackerKCF_create()
    else:
        raise ValueError("TRACKER_KIND must be 'CSRT' or 'KCF'.")

cap = cv2.VideoCapture(CAM_INDEX)
cap.set(cv2.CAP_PROP_FRAME_WIDTH,  FRAME_W)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, FRAME_H)

tracker = None
have_roi = False
bbox = None
last_seen = 0.0
mx_s, area_s = None, None  # EMA state
prev_time = 0
fps = 0.0

def select_roi(frame):
    box = cv2.selectROI("track", frame, fromCenter=False, showCrosshair=True)
    cv2.waitKey(1)
    return box

while True:
    ok, frame = cap.read()
    now = cv2.getTickCount()
    if prev_time != 0:
        time_diff = (now - prev_time) / cv2.getTickFrequency()
        if time_diff > 0:
            fps = 1.0 / time_diff
    prev_time = now
    if not ok:
        time.sleep(0.01)
        continue

    if have_roi and tracker is not None:
        ok, bbox = tracker.update(frame)
        if ok:
            x, y, w, h = [int(v) for v in bbox]
            area = w * h
            if area >= MIN_AREA:
                mx = x + w / 2
                # EMA smoothing
                mx_s = mx if mx_s is None else (1 - EMA_ALPHA) * mx_s + EMA_ALPHA * mx
                area_s = area if area_s is None else (1 - EMA_ALPHA) * area_s + EMA_ALPHA * area

                cx = frame.shape[1] / 2
                err_x = (mx_s - cx) / cx
                turn = clamp(-Kp_turn * err_x, -1, 1)
                fwd = clamp((TARGET_AREA - area_s) / max(TARGET_AREA, 1), 0.15, 0.7) if area_s < TARGET_AREA else 0.0
                left, right = clamp(fwd + turn, -1, 1), clamp(fwd - turn, -1, 1)
                drive(left, right)

                cv2.rectangle(frame, (x, y), (x + w, y + h), (80, 220, 80), 2)
                cv2.circle(frame, (int(mx_s), int(y + h / 2)), 3, (80, 220, 80), -1)
                txt = f"{TRACKER_KIND} area={int(area_s)} errX={err_x:+.2f} fwd={fwd:.2f} turn={turn:+.2f} FPS: {fps:.1f}"
                cv2.putText(frame, txt, (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,255), 1, cv2.LINE_AA)

                last_seen = time.time()
            else:
                ok = False  # treat tiny boxes as lost

        if not ok:
            drive(+0.25, -0.25)
            if time.time() - last_seen > 3.0:
                drive(0, 0)
            cv2.putText(frame, "Lost... press 's' to reselect", (6, 18),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,200,255), 1, cv2.LINE_AA)
    else:
        cv2.putText(frame, "Press 's' and drag to select target", (6, 18),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200,200,200), 1, cv2.LINE_AA)

    cv2.imshow("track", frame)
    k = cv2.waitKey(1) & 0xFF
    if k == 27:
        break
    elif k == ord('s'):
        box = select_roi(frame)
        if box is not None and box[2] > 0 and box[3] > 0:
            tracker = create_tracker(TRACKER_KIND)
            roi = tuple(float(v) for v in box)  # ensure float
            ok_init = tracker.init(frame, roi)
            have_roi = bool(ok_init)
            bbox = roi
            mx_s, area_s = None, None
            last_seen = time.time()

cap.release()
cv2.destroyAllWindows()
