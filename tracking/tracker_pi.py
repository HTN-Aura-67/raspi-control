# tracker_pi.py
import cv2, zmq, json, time, argparse, numpy as np
EMA_ALPHA=0.3; Kp_turn=0.7; TARGET_AREA=12000; MIN_AREA=60

def clamp(x, lo, hi): return lo if x < lo else hi if x > hi else x
def create_tracker(kind):
    k=kind.upper()
    if k=="CSRT": return cv2.legacy.TrackerCSRT_create()
    if k=="KCF":  return cv2.legacy.TrackerKCF_create()
    raise ValueError("kind must be CSRT or KCF")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--connect", default="tcp://127.0.0.1:5555")  # camera_pub endpoint
    ap.add_argument("--pub",     default="tcp://0.0.0.0:5556")    # where we publish results
    ap.add_argument("--kind",    default="CSRT", choices=["CSRT","KCF"])
    ap.add_argument("--roi",     type=int, nargs=4, metavar=("X","Y","W","H"))
    ap.add_argument("--show",    action="store_true")  # optional local preview (if HDMI)
    args = ap.parse_args()

    ctx = zmq.Context.instance()
    sub = ctx.socket(zmq.SUB)
    sub.setsockopt(zmq.RCVHWM, 1)
    sub.setsockopt(zmq.CONFLATE, 1)           # always keep only the newest frame
    sub.connect(args.connect)
    sub.setsockopt(zmq.SUBSCRIBE, b"video.raw")

    pub = ctx.socket(zmq.PUB)
    pub.bind(args.pub)

    print(f"[tracker_pi] SUB {args.connect} → PUB {args.pub} tracker={args.kind}")

    tracker=None; have_roi=False
    mx_s=area_s=None
    last_seen=time.time()
    prev_tick=0; fps=0.0
    seq_out=0

    while True:
        _topic, meta_b, jpg_b = sub.recv_multipart()
        meta = json.loads(meta_b.decode("utf-8"))
        frame = cv2.imdecode(np.frombuffer(jpg_b, dtype=np.uint8), cv2.IMREAD_COLOR)
        if frame is None: continue

        tick = cv2.getTickCount()
        if prev_tick:
            dt=(tick-prev_tick)/cv2.getTickFrequency()
            if dt>0: fps=1.0/dt
        prev_tick=tick

        # init ROI if needed
        if not have_roi:
            H,W=frame.shape[:2]
            if args.roi: x,y,w,h=args.roi
            else:
                w=min(80,W//3); h=min(80,H//3); x=W//2-w//2; y=H//2-h//2
            tracker=create_tracker(args.kind)
            have_roi=bool(tracker.init(frame, (float(x),float(y),float(w),float(h))))
            mx_s=area_s=None
            last_seen=time.time()

        ok, bbox = tracker.update(frame) if have_roi else (False,None)
        drive_l=drive_r=0.0
        state = {}

        if ok:
            x,y,w,h=[int(v) for v in bbox]
            area=w*h
            if area >= MIN_AREA:
                mx = x + w/2
                mx_s = mx if mx_s is None else (1-EMA_ALPHA)*mx_s + EMA_ALPHA*mx
                area_s = area if area_s is None else (1-EMA_ALPHA)*area_s + EMA_ALPHA*area
                cx = frame.shape[1]/2
                err_x = (mx_s - cx)/cx
                turn = clamp(-Kp_turn*err_x, -1, 1)
                fwd  = clamp((TARGET_AREA - area_s)/max(TARGET_AREA,1), 0.15, 0.7) if area_s < TARGET_AREA else 0.0
                drive_l, drive_r = clamp(fwd+turn, -1,1), clamp(fwd-turn, -1,1)
                last_seen=time.time()

                cv2.rectangle(frame,(x,y),(x+w,y+h),(80,220,80),2)
                cv2.circle(frame,(int(mx_s),int(y+h/2)),3,(80,220,80),-1)
                cv2.putText(frame, f"{args.kind} area={int(area_s)} errX={err_x:+.2f} fwd={fwd:.2f} turn={turn:+.2f} FPS:{fps:.1f}",
                            (6,18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,255), 1, cv2.LINE_AA)

                state = {
                    "bbox":[x,y,w,h],
                    "area": float(area_s),
                    "err_x": float(err_x),
                    "fwd": float(fwd),
                    "turn": float(turn),
                    "fps": float(fps)
                }
            else:
                ok=False

        if not ok:
            # searching behavior
            drive_l, drive_r = +0.25, -0.25
            if time.time()-last_seen>3.0: drive_l=drive_r=0.0
            cv2.putText(frame, "Lost... reinit", (6,18),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,200,255),1, cv2.LINE_AA)
            have_roi=False  # reinit next frame

        # --- publish annotated video ---
        okJ, jpg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if okJ:
            hdr = {"seq": seq_out, "ts_ns": time.time_ns(), "kind":"video", "w":frame.shape[1], "h":frame.shape[0], "fmt":"jpg"}
            pub.send_multipart([b"video.annot", json.dumps(hdr).encode(), jpg.tobytes()], copy=False)

        # --- publish tensor/state ---
        # as float32 array [l, r, (optional other floats...)]
        arr = np.array([drive_l, drive_r] + ([state.get("err_x",0.0), state.get("fwd",0.0), state.get("turn",0.0)]), dtype=np.float32)
        hdr = {"seq": seq_out, "ts_ns": time.time_ns(), "kind":"tensor", "name":"drive_state", "dtype": str(arr.dtype), "shape": list(arr.shape)}
        pub.send_multipart([b"tensor.state", json.dumps(hdr).encode(), memoryview(arr)], copy=False)

        # --- publish drive commands (e.g., another process controls motors) ---
        cmd = {"l": float(drive_l), "r": float(drive_r), "ts_ns": time.time_ns()}
        pub.send_multipart([b"drive.cmd", json.dumps(cmd).encode(), b""], copy=False)

        seq_out += 1

        if args.show:
            cv2.imshow("annot", frame)
            if cv2.waitKey(1) & 0xFF == 27: break

if __name__ == "__main__":
    main()
