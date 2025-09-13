# camera_pub.py
import cv2, zmq, json, time, argparse, numpy as np

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bind", default="tcp://0.0.0.0:5555")
    ap.add_argument("--cam", type=int, default=0)
    ap.add_argument("--w", type=int, default=640)
    ap.add_argument("--h", type=int, default=480)
    ap.add_argument("--fps", type=int, default=15)
    ap.add_argument("--quality", type=int, default=80)  # JPEG quality [0..100]
    args = ap.parse_args()

    cap = cv2.VideoCapture(args.cam)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  args.w)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.h)
    cap.set(cv2.CAP_PROP_FPS, args.fps) if hasattr(cv2, "CAP_PROP_FPS") else None

    ctx = zmq.Context.instance()
    pub = ctx.socket(zmq.PUB)
    pub.setsockopt(zmq.SNDHWM, 1)        # drop if slow consumer
    pub.bind(args.bind)

    print(f"[camera_pub] {args.w}x{args.h}@{args.fps} → {args.bind} (JPEG Q={args.quality})")
    seq = 0
    interval = 1.0 / max(args.fps, 1)
    next_t = time.time()

    while True:
        ok, frame = cap.read()
        if not ok:
            time.sleep(0.01)
            continue

        # throttle to ~fps
        now = time.time()
        if now < next_t:
            time.sleep(next_t - now)
        next_t += interval

        ok, jpg = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, args.quality])
        if not ok:
            continue

        header = {
            "seq": seq,
            "ts_ns": time.time_ns(),
            "w": frame.shape[1],
            "h": frame.shape[0],
            "fmt": "jpg"
        }
        # topic | json header | jpeg bytes
        pub.send_multipart([b"video", json.dumps(header).encode(), jpg.tobytes()], copy=False)
        seq += 1

if __name__ == "__main__":
    main()
