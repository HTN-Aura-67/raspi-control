# track_and_stream_pi.py
import cv2, numpy as np, time, sys, argparse, subprocess, shlex, os

# ---- Defaults from your code ----
CAM_INDEX = 0
FRAME_W, FRAME_H = 320, 240
TRACKER_KIND = "CSRT"   # "CSRT" or "KCF"
TARGET_AREA = 12000
Kp_turn = 0.7
EMA_ALPHA = 0.3
MIN_AREA = 60
FPS = 15

def eprint(*a, **k): print(*a, file=sys.stderr, **k)
def clamp(x, lo, hi): return lo if x < lo else hi if x > hi else x

def create_tracker(kind: str):
    k = kind.upper()
    if k == "CSRT":
        return cv2.legacy.TrackerCSRT_create()
    elif k == "KCF":
        return cv2.legacy.TrackerKCF_create()
    else:
        raise ValueError("TRACKER_KIND must be 'CSRT' or 'KCF'.")

def build_ffmpeg_cmd(w, h, fps, out_mode, addr=None):
    """
    out_mode: 'stdout' | 'tcp-listen' | 'udp'
      - stdout: write H264 to stdout (good for SSH pipe)
      - tcp-listen: start a TCP server at addr like '0.0.0.0:8000' (MPEG-TS)
      - udp: send MPEG-TS to addr like '192.168.1.10:8000'
    """
    base_in = f"-f rawvideo -pix_fmt bgr24 -s {w}x{h} -r {fps} -i -"
    # ultralow latency x264 (software). If you have working HW encoder, you can replace with h264_v4l2m2m.
    vcodec = "-c:v libx264 -preset veryfast -tune zerolatency -g {g} -pix_fmt yuv420p".format(g=fps*2)

    if out_mode == "stdout":
        # raw H.264 bytestream to stdout
        out = "-f h264 -"
    else:
        # Use MPEG-TS over TCP/UDP for easier demuxing by ffplay
        if not addr or ":" not in addr:
            raise ValueError("addr must be host:port for tcp-listen/udp")
        if out_mode == "tcp-listen":
            # ffmpeg will listen; clients connect with ffplay tcp://ip:port
            out = f"-f mpegts tcp://{addr}?listen=1"
        elif out_mode == "udp":
            # ffplay udp://@:port  OR udp://PI:port from client
            out = f"-f mpegts udp://{addr}"
        else:
            raise ValueError("Invalid out_mode")

    cmd = f"ffmpeg -hide_banner -loglevel error {base_in} -an {vcodec} {out}"
    return cmd

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cam", type=int, default=CAM_INDEX)
    ap.add_argument("--w", type=int, default=FRAME_W)
    ap.add_argument("--h", type=int, default=FRAME_H)
    ap.add_argument("--fps", type=int, default=FPS)
    ap.add_argument("--kind", default=TRACKER_KIND, choices=["CSRT","KCF"])
    ap.add_argument("--roi", type=int, nargs=4, metavar=("X","Y","W","H"),
                    help="Initial ROI in pixels; if omitted, center box is used")
    ap.add_argument("--mode", choices=["stdout","tcp-listen","udp"], default="stdout",
                    help="Where to send encoded video")
    ap.add_argument("--addr", default=None, help="host:port for tcp-listen/udp (e.g. 0.0.0.0:8000 or 192.168.1.50:8000)")
    ap.add_argument("--use-hw", action="store_true",
                    help="Try Pi HW encoder (h264_v4l2m2m) instead of libx264")
    args = ap.parse_args()

    # Camera
    cap = cv2.VideoCapture(args.cam)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  args.w)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.h)
    cap.set(cv2.CAP_PROP_FPS,          args.fps)

    # ffmpeg pipeline
    cmd = build_ffmpeg_cmd(args.w, args.h, args.fps, args.mode, args.addr)

    # Optionally switch to hardware encoder if requested (works on many Pis; Zero may vary)
    if args.use_hw:
        cmd = cmd.replace("libx264", "h264_v4l2m2m")

    eprint("[track_and_stream] ffmpeg:", cmd)
    ff = subprocess.Popen(shlex.split(cmd), stdin=subprocess.PIPE, stdout=(sys.stdout.buffer if args.mode=="stdout" else None))

    # Tracking state
    TRACKER_KIND = args.kind
    tracker = None
    have_roi = False
    last_seen = 0.0
    mx_s, area_s = None, None
    fps = 0.0
    prev_time = 0

    # Prime first frame
    ok, frame = cap.read()
    if not ok or frame is None:
        eprint("Camera read failed at startup.")
        sys.exit(1)

    def init_tracker(frm):
        nonlocal tracker, have_roi, mx_s, area_s, last_seen
        H, W = frm.shape[:2]
        if args.roi:
            x,y,w,h = args.roi
        else:
            w = min(80, W//3); h = min(80, H//3)
            x = W//2 - w//2; y = H//2 - h//2
        tracker = create_tracker(TRACKER_KIND)
        have_roi = bool(tracker.init(frm, (float(x), float(y), float(w), float(h))))
        mx_s = area_s = None
        last_seen = time.time()
        eprint(f"Initialized {TRACKER_KIND} ROI=({x},{y},{w},{h}) have_roi={have_roi}")

    init_tracker(frame)

    while True:
        ok, frame = cap.read()
        if not ok or frame is None:
            time.sleep(0.005)
            continue

        now = cv2.getTickCount()
        if prev_time != 0:
            dt = (now - prev_time) / cv2.getTickFrequency()
            if dt > 0:
                fps = 1.0 / dt
        prev_time = now

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
                    # NOTE: we keep motor control local on Pi; replace with GPIO/PWM as needed
                    eprint(f"Drive L={left:+.2f} R={right:+.2f}")

                    # draw overlays
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (80, 220, 80), 2)
                    cv2.circle(frame, (int(mx_s), int(y + h / 2)), 3, (80, 220, 80), -1)
                    txt = f"{TRACKER_KIND} area={int(area_s)} fps={fps:.1f} fwd={fwd:.2f} turn={turn:+.2f}"
                    cv2.putText(frame, txt, (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,255), 1, cv2.LINE_AA)

                    last_seen = time.time()
                else:
                    ok = False

            if not ok:
                # searching spin (local)
                eprint("Lost target; spinning to search...")
                cv2.putText(frame, "Lost... reinit", (6, 18),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,200,255), 1, cv2.LINE_AA)
                init_tracker(frame)

        # Send this annotated frame to ffmpeg stdin
        try:
            ff.stdin.write(frame.tobytes())
        except (BrokenPipeError, ValueError):
            eprint("Encoder pipe closed.")
            break

    # cleanup
    try:
        ff.stdin.close()
        ff.wait(timeout=2)
    except Exception:
        pass
    cap.release()

if __name__ == "__main__":
    main()
