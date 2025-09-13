# camera_pub_ws.py
import cv2, json, time, argparse, numpy as np, asyncio, websockets

async def video_stream(websocket, args):
    cap = cv2.VideoCapture(args.cam)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  args.w)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.h)
    cap.set(cv2.CAP_PROP_FPS, args.fps) if hasattr(cv2, "CAP_PROP_FPS") else None

    print(f"[camera_pub_ws] {args.w}x{args.h}@{args.fps} → ws://0.0.0.0:{args.port} (JPEG Q={args.quality})")
    seq = 0
    interval = 1.0 / max(args.fps, 1)
    next_t = time.time()

    try:
        while True:
            ok, frame = cap.read()
            if not ok:
                await asyncio.sleep(0.01)
                continue

            now = time.time()
            if now < next_t:
                await asyncio.sleep(next_t - now)
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
            # Send header and image as a single binary message: header (json) + b'\n' + jpg bytes
            await websocket.send(json.dumps(header).encode() + b'\n' + jpg.tobytes())
            seq += 1
    except websockets.ConnectionClosed:
        print("Client disconnected")
    finally:
        cap.release()

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--cam", type=int, default=0)
    ap.add_argument("--w", type=int, default=640)
    ap.add_argument("--h", type=int, default=480)
    ap.add_argument("--fps", type=int, default=15)
    ap.add_argument("--quality", type=int, default=80)
    return ap.parse_args()

def main():
    args = parse_args()
    
    async def handler(websocket, path=None):
        await video_stream(websocket, args)
    
    async def start_server():
        server = await websockets.serve(
            handler, 
            "0.0.0.0", 
            args.port
        )
        print(f"WebSocket server started on ws://0.0.0.0:{args.port}")
        await server.wait_closed()
    
    asyncio.run(start_server())

if __name__ == "__main__":
    main()
