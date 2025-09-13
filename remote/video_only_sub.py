# viewer_sub.py
import cv2, zmq, json, numpy as np, argparse, time

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--connect", default="tcp://100.97.205.28:5555")  # replace PI_IP
    ap.add_argument("--win", default="view")
    ap.add_argument("--conflate", action="store_true", help="only keep newest frame")
    args = ap.parse_args()

    ctx = zmq.Context.instance()
    sub = ctx.socket(zmq.SUB)
    if args.conflate:
        sub.setsockopt(zmq.CONFLATE, 1)
    sub.setsockopt(zmq.RCVHWM, 1)
    sub.connect(args.connect)
    sub.setsockopt(zmq.SUBSCRIBE, b"video")

    last_ts = None
    print(f"[viewer] SUB {args.connect}")

    while True:
        _topic, meta_b, payload = sub.recv_multipart()
        meta = json.loads(meta_b.decode())
        img = cv2.imdecode(np.frombuffer(payload, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            continue

        # FPS + one-way latency (pub->sub)
        now_ns = time.time_ns()
        if last_ts is not None:
            fps = 1e9 / (now_ns - last_ts)
        else:
            fps = 0.0
        last_ts = now_ns
        src_ts_ns = meta.get("ts_ns", now_ns)
        latency_ms = (now_ns - src_ts_ns) / 1e6

        cv2.putText(img, f"FPS:{fps:4.1f}  Latency:{latency_ms:5.1f}ms",
                    (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,255), 1, cv2.LINE_AA)

        cv2.imshow(args.win, img)
        if cv2.waitKey(1) & 0xFF == 27:  # ESC to quit
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
