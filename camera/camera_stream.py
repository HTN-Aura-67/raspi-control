# camera_pub_ws.py
import json, time, argparse, asyncio, websockets, subprocess, io
from PIL import Image

async def video_stream(websocket, args):
    print(f"[camera_pub_ws] {args.w}x{args.h}@{args.fps} → ws://0.0.0.0:{args.port} (JPEG Q={args.quality})")
    seq = 0
    interval = 1.0 / max(args.fps, 1)
    next_t = time.time()

    try:
        while True:
            # Capture frame using libcamera-still or raspistill
            try:
                # Try libcamera-still first (newer Raspberry Pi OS)
                cmd = [
                    'libcamera-still', 
                    '--output', '-',  # Output to stdout
                    '--width', str(args.w),
                    '--height', str(args.h),
                    '--quality', str(args.quality),
                    '--encoding', 'jpg',
                    '--timeout', '1',
                    '--nopreview'
                ]
                
                result = subprocess.run(cmd, capture_output=True, timeout=2)
                
                if result.returncode != 0:
                    # Fallback to raspistill (older systems)
                    cmd = [
                        'raspistill',
                        '-o', '-',  # Output to stdout
                        '-w', str(args.w),
                        '-h', str(args.h),
                        '-q', str(args.quality),
                        '-e', 'jpg',
                        '-t', '1',
                        '-n'  # No preview
                    ]
                    result = subprocess.run(cmd, capture_output=True, timeout=2)
                
                if result.returncode != 0:
                    print(f"Camera capture failed: {result.stderr.decode()}")
                    await asyncio.sleep(0.1)
                    continue
                    
                jpg_data = result.stdout
                
                if not jpg_data:
                    await asyncio.sleep(0.01)
                    continue

            except subprocess.TimeoutExpired:
                print("Camera capture timeout")
                await asyncio.sleep(0.01)
                continue
            except Exception as e:
                print(f"Camera error: {e}")
                await asyncio.sleep(0.1)
                continue

            # Throttle to target FPS
            now = time.time()
            if now < next_t:
                await asyncio.sleep(next_t - now)
            next_t += interval

            header = {
                "seq": seq,
                "ts_ns": time.time_ns(),
                "w": args.w,
                "h": args.h,
                "fmt": "jpg"
            }
            
            # Send header and image as a single binary message: header (json) + b'\n' + jpg bytes
            await websocket.send(json.dumps(header).encode() + b'\n' + jpg_data)
            seq += 1
            
    except websockets.ConnectionClosed:
        print("Client disconnected")
    except Exception as e:
        print(f"Stream error: {e}")

def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
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
