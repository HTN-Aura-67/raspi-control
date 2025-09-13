import cv2
import json
import numpy as np
import argparse
import time
import asyncio
import websockets

async def video_client(uri, win):
    last_ts = None
    print(f"[viewer] WS {uri}")

    async with websockets.connect(uri, max_size=None) as ws:
        while True:
            try:
                # Receive combined message (header + newline + image bytes)
                message = await ws.recv()
                
                # Split at first newline to separate header from image data
                if b'\n' not in message:
                    continue
                    
                header_bytes, image_bytes = message.split(b'\n', 1)
                
                # Parse JSON header
                meta = json.loads(header_bytes.decode())
                
                # Decode image
                img = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
                if img is None:
                    continue

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

                cv2.imshow(win, img)
                if cv2.waitKey(1) & 0xFF == 27:
                    break
                    
            except websockets.exceptions.ConnectionClosed:
                print("Connection closed by server")
                break
            except json.JSONDecodeError as e:
                print(f"Failed to decode JSON: {e}")
                continue
            except Exception as e:
                print(f"Error processing frame: {e}")
                continue

    cv2.destroyAllWindows()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--connect", default="ws://100.112.177.9:8765")  # WebSocket URL
    ap.add_argument("--win", default="view")
    args = ap.parse_args()

    asyncio.run(video_client(args.connect, args.win))

if __name__ == "__main__":
    main()
