# viewer_sub.py
import cv2, zmq, json, numpy as np, argparse

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--connect", default="tcp://100.97.205.28:5556")  # tracker PUB
    ap.add_argument("--topic", default="video.annot")
    args = ap.parse_args()

    ctx = zmq.Context.instance()
    sub = ctx.socket(zmq.SUB)
    sub.setsockopt(zmq.CONFLATE, 1)  # only most recent
    sub.connect(args.connect)
    sub.setsockopt(zmq.SUBSCRIBE, args.topic.encode())

    print(f"[viewer] SUB {args.connect} topic={args.topic}")
    while True:
        _topic, meta_b, payload = sub.recv_multipart()
        meta = json.loads(meta_b.decode())
        if meta.get("fmt") == "jpg":
            img = cv2.imdecode(np.frombuffer(payload, np.uint8), cv2.IMREAD_COLOR)
            if img is None: continue
            cv2.imshow("view", img)
            if cv2.waitKey(1) & 0xFF == 27: break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
