"""
Combined Hardware API Server
Serves both TOF sensor and LED control functionality in a single API
"""

import sys
import os

# Add current directory and subdirectories to path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)
sys.path.insert(0, os.path.join(current_dir, 'tof'))
sys.path.insert(0, os.path.join(current_dir, 'led_control'))

from flask import Flask, jsonify, request
from flask_cors import CORS
import time

# Import our modules with better error handling
tof_sensor = None
led_controller = None
tof_available = False
led_available = False

try:
    # Try importing TOF sensor components directly
    import board
    import busio
    import adafruit_vl53l0x
    from typing import Optional, Dict, Any
    
    class TOFSensor:
        def __init__(self):
            self.sensor = None
            self.is_initialized = False
            self.last_reading = None
            self.last_error = None
            self.initialize_sensor()
        
        def initialize_sensor(self) -> bool:
            try:
                i2c = busio.I2C(board.SCL, board.SDA)
                self.sensor = adafruit_vl53l0x.VL53L0X(i2c)
                self.is_initialized = True
                return True
            except Exception as e:
                self.last_error = str(e)
                print(f"TOF sensor init failed: {e}")
                return False
        
        def read_distance(self) -> Optional[int]:
            try:
                if self.sensor:
                    distance = self.sensor.range
                    self.last_reading = distance
                    return distance
                else:
                    # Mock reading
                    import random
                    distance = random.randint(100, 2000)
                    self.last_reading = distance
                    return distance
            except Exception as e:
                self.last_error = str(e)
                return None
        
        def get_status(self) -> Dict[str, Any]:
            return {
                "initialized": self.is_initialized,
                "hardware_available": True,
                "last_reading": self.last_reading,
                "last_error": self.last_error,
                "timestamp": time.time()
            }
        
        def read_multiple(self, count: int = 10, interval: float = 0.1) -> Dict[str, Any]:
            readings = []
            start_time = time.time()
            
            for i in range(count):
                distance = self.read_distance()
                if distance is not None:
                    readings.append({
                        "reading": i + 1,
                        "distance_mm": distance,
                        "timestamp": time.time()
                    })
                time.sleep(interval)
            
            if readings:
                distances = [r["distance_mm"] for r in readings]
                stats = {
                    "min": min(distances),
                    "max": max(distances),
                    "avg": sum(distances) / len(distances),
                    "count": len(distances)
                }
            else:
                stats = {"min": None, "max": None, "avg": None, "count": 0}
            
            return {
                "readings": readings,
                "statistics": stats,
                "duration_seconds": time.time() - start_time
            }
    
    tof_sensor = TOFSensor()
    tof_available = True
    print("✅ TOF sensor module loaded successfully")
    
except ImportError as e:
    tof_available = False
    print(f"⚠️  TOF sensor hardware not available: {e}")
except Exception as e:
    tof_available = False
    print(f"❌ TOF sensor initialization failed: {e}")

try:
    # Try importing LED controller components directly
    from luma.core.interface.serial import spi, noop
    from luma.led_matrix.device import max7219
    from luma.core.render import canvas
    import threading
    
    class LEDController:
        def __init__(self):
            self.device = None
            self.is_initialized = False
            self.current_expression = "normal"
            self.animation_thread = None
            self.stop_animation = False
            
            # Eye expressions (16x8 each)
            self.expressions = {
                "normal": [
                    [0,0,1,1,1,1,0,0,   0,0,1,1,1,1,0,0],
                    [0,1,0,0,0,0,1,0,   0,1,0,0,0,0,1,0],
                    [1,0,0,0,0,0,0,1,   1,0,0,0,0,0,0,1],
                    [1,0,0,0,0,0,0,1,   1,0,0,0,0,0,0,1],
                    [1,0,0,0,0,0,0,1,   1,0,0,0,0,0,0,1],
                    [1,0,0,0,0,0,0,1,   1,0,0,0,0,0,0,1],
                    [0,1,0,0,0,0,1,0,   0,1,0,0,0,0,1,0],
                    [0,0,1,1,1,1,0,0,   0,0,1,1,1,1,0,0]
                ],
                "happy": [
                    [0,0,1,1,1,1,0,0,   0,0,1,1,1,1,0,0],
                    [0,1,0,0,0,0,1,0,   0,1,0,0,0,0,1,0],
                    [1,0,0,0,0,0,0,1,   1,0,0,0,0,0,0,1],
                    [1,0,0,0,0,0,0,1,   1,0,0,0,0,0,0,1],
                    [1,0,0,1,1,0,0,1,   1,0,0,1,1,0,0,1],
                    [0,1,1,0,0,1,1,0,   0,1,1,0,0,1,1,0],
                    [0,0,0,0,0,0,0,0,   0,0,0,0,0,0,0,0],
                    [0,0,0,0,0,0,0,0,   0,0,0,0,0,0,0,0]
                ],
                "sad": [
                    [0,0,1,1,1,1,0,0,   0,0,1,1,1,1,0,0],
                    [0,1,0,0,0,0,1,0,   0,1,0,0,0,0,1,0],
                    [1,0,0,0,0,0,0,1,   1,0,0,0,0,0,0,1],
                    [1,0,0,0,0,0,0,1,   1,0,0,0,0,0,0,1],
                    [0,1,0,0,0,0,1,0,   0,1,0,0,0,0,1,0],
                    [0,0,1,0,0,1,0,0,   0,0,1,0,0,1,0,0],
                    [0,0,0,1,1,0,0,0,   0,0,0,1,1,0,0,0],
                    [0,0,0,0,0,0,0,0,   0,0,0,0,0,0,0,0]
                ],
                "wink": [
                    [0,0,1,1,1,1,0,0,   0,0,0,0,0,0,0,0],
                    [0,1,0,0,0,0,1,0,   0,0,0,0,0,0,0,0],
                    [1,0,0,0,0,0,0,1,   0,0,1,1,1,1,0,0],
                    [1,0,0,0,0,0,0,1,   0,1,0,0,0,0,1,0],
                    [1,0,0,0,0,0,0,1,   1,0,0,0,0,0,0,1],
                    [1,0,0,0,0,0,0,1,   0,0,0,0,0,0,0,0],
                    [0,1,0,0,0,0,1,0,   0,0,0,0,0,0,0,0],
                    [0,0,1,1,1,1,0,0,   0,0,0,0,0,0,0,0]
                ],
                "love": [
                    [0,0,0,0,0,0,0,0,   0,0,0,0,0,0,0,0],
                    [0,1,1,0,0,1,1,0,   0,1,1,0,0,1,1,0],
                    [1,1,1,1,1,1,1,1,   1,1,1,1,1,1,1,1],
                    [1,1,1,1,1,1,1,1,   1,1,1,1,1,1,1,1],
                    [0,1,1,1,1,1,1,0,   0,1,1,1,1,1,1,0],
                    [0,0,1,1,1,1,0,0,   0,0,1,1,1,1,0,0],
                    [0,0,0,1,1,0,0,0,   0,0,0,1,1,0,0,0],
                    [0,0,0,0,0,0,0,0,   0,0,0,0,0,0,0,0]
                ],
                "closed": [
                    [0,0,0,0,0,0,0,0,   0,0,0,0,0,0,0,0],
                    [0,0,0,0,0,0,0,0,   0,0,0,0,0,0,0,0],
                    [0,0,0,0,0,0,0,0,   0,0,0,0,0,0,0,0],
                    [1,1,1,1,1,1,1,1,   1,1,1,1,1,1,1,1],
                    [1,1,1,1,1,1,1,1,   1,1,1,1,1,1,1,1],
                    [0,0,0,0,0,0,0,0,   0,0,0,0,0,0,0,0],
                    [0,0,0,0,0,0,0,0,   0,0,0,0,0,0,0,0],
                    [0,0,0,0,0,0,0,0,   0,0,0,0,0,0,0,0]
                ],
                "off": [
                    [0,0,0,0,0,0,0,0,   0,0,0,0,0,0,0,0],
                    [0,0,0,0,0,0,0,0,   0,0,0,0,0,0,0,0],
                    [0,0,0,0,0,0,0,0,   0,0,0,0,0,0,0,0],
                    [0,0,0,0,0,0,0,0,   0,0,0,0,0,0,0,0],
                    [0,0,0,0,0,0,0,0,   0,0,0,0,0,0,0,0],
                    [0,0,0,0,0,0,0,0,   0,0,0,0,0,0,0,0],
                    [0,0,0,0,0,0,0,0,   0,0,0,0,0,0,0,0],
                    [0,0,0,0,0,0,0,0,   0,0,0,0,0,0,0,0]
                ]
            }
            
            self.initialize_device()
        
        def initialize_device(self) -> bool:
            try:
                serial = spi(port=0, device=0, gpio=noop())
                self.device = max7219(serial, cascaded=2, block_orientation=0, rotate=0)
                self.is_initialized = True
                print("✅ LED matrix hardware initialized successfully")
                return True
            except Exception as e:
                print(f"⚠️ LED matrix hardware init failed: {e}")
                print("   Falling back to mock mode for LED controller")
                self.is_initialized = False
                self.device = None
                return False
        
        def display_expression(self, expression: str) -> bool:
            if expression not in self.expressions:
                return False
            
            self.current_expression = expression
            eye_pattern = self.expressions[expression]
            
            if self.device and self.is_initialized:
                try:
                    with canvas(self.device) as draw:
                        for y, row in enumerate(eye_pattern):
                            for x, pixel in enumerate(row):
                                if pixel:
                                    draw.point((x, y), fill="white")
                    return True
                except Exception as e:
                    print(f"Error displaying expression: {e}")
                    return False
            else:
                print(f"🎭 Mock LED: Displaying expression '{expression}'")
                return True
        
        def blink(self, base_expression: str = None, duration: float = 0.15) -> bool:
            if base_expression is None:
                base_expression = self.current_expression
            
            if base_expression not in self.expressions:
                return False
            
            print(f"👀 LED Blink: {base_expression} -> closed -> {base_expression} (duration: {duration}s)")
            self.display_expression("closed")
            time.sleep(duration)
            self.display_expression(base_expression)
            return True
        
        def start_animation(self, expressions: list, duration: float = 1.0, loop: bool = True):
            self.stop_animation = False
            
            def animate():
                while not self.stop_animation:
                    for expr in expressions:
                        if self.stop_animation:
                            break
                        self.display_expression(expr)
                        time.sleep(duration)
                    if not loop:
                        break
            
            if self.animation_thread and self.animation_thread.is_alive():
                self.stop_animation = True
                self.animation_thread.join()
            
            self.animation_thread = threading.Thread(target=animate)
            self.animation_thread.start()
        
        def stop_current_animation(self):
            self.stop_animation = True
            if self.animation_thread and self.animation_thread.is_alive():
                self.animation_thread.join()
        
        def get_status(self) -> Dict[str, Any]:
            return {
                "initialized": self.is_initialized,
                "hardware_available": self.device is not None,
                "current_expression": self.current_expression,
                "available_expressions": list(self.expressions.keys()),
                "animation_running": self.animation_thread is not None and self.animation_thread.is_alive()
            }
    
    led_controller = LEDController()
    led_available = True
    if led_controller.is_initialized:
        print("✅ LED controller with hardware initialized successfully")
    else:
        print("⚠️ LED controller running in mock mode (no hardware)")

except ImportError as e:
    led_available = False
    print(f"⚠️  LED controller hardware not available: {e}")
except Exception as e:
    led_available = False
    print(f"❌ LED controller initialization failed: {e}")

# Create mock classes if hardware not available
if not tof_available:
    class MockTOFSensor:
        def __init__(self):
            self.is_initialized = False
            self.last_reading = None
            self.last_error = "Hardware not available"
        
        def read_distance(self):
            import random
            self.last_reading = random.randint(100, 2000)
            return self.last_reading
        
        def get_status(self):
            return {
                "initialized": False,
                "hardware_available": False,
                "last_reading": self.last_reading,
                "last_error": self.last_error,
                "timestamp": time.time()
            }
        
        def read_multiple(self, count=10, interval=0.1):
            readings = []
            for i in range(count):
                distance = self.read_distance()
                readings.append({
                    "reading": i + 1,
                    "distance_mm": distance,
                    "timestamp": time.time()
                })
                time.sleep(interval)
            
            distances = [r["distance_mm"] for r in readings]
            return {
                "readings": readings,
                "statistics": {
                    "min": min(distances),
                    "max": max(distances),
                    "avg": sum(distances) / len(distances),
                    "count": len(distances)
                },
                "duration_seconds": count * interval
            }
    
    tof_sensor = MockTOFSensor()

if not led_available:
    class MockLEDController:
        def __init__(self):
            self.is_initialized = False
            self.current_expression = "normal"
            self.expressions = {
                "normal": [], "happy": [], "sad": [], "wink": [], 
                "love": [], "closed": [], "off": []
            }
        
        def display_expression(self, expression):
            if expression in self.expressions:
                self.current_expression = expression
                print(f"Mock LED: Displaying {expression}")
                return True
            return False
        
        def blink(self, base_expression=None, duration=0.15):
            print(f"Mock LED: Blinking for {duration}s")
            return True
        
        def start_animation(self, expressions, duration=1.0, loop=True):
            print(f"Mock LED: Starting animation with {expressions}")
        
        def stop_current_animation(self):
            print("Mock LED: Stopping animation")
        
        def get_status(self):
            return {
                "initialized": False,
                "hardware_available": False,
                "current_expression": self.current_expression,
                "available_expressions": list(self.expressions.keys()),
                "animation_running": False
            }
    
    led_controller = MockLEDController()

app = Flask(__name__)
CORS(app)  # Enable CORS for web interface

# Health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    """System health check"""
    return jsonify({
        "status": "healthy",
        "timestamp": time.time(),
        "services": {
            "tof_sensor": {
                "available": tof_available,
                "initialized": tof_sensor.is_initialized if tof_sensor else False
            },
            "led_controller": {
                "available": led_available,
                "initialized": led_controller.is_initialized if led_controller else False
            }
        }
    })

# Combined status endpoint
@app.route('/status', methods=['GET'])
def get_combined_status():
    """Get status of all hardware components"""
    status = {
        "timestamp": time.time(),
        "tof_sensor": tof_sensor.get_status() if tof_sensor else {"available": False},
        "led_controller": led_controller.get_status() if led_controller else {"available": False}
    }
    return jsonify(status)

# === TOF Sensor Endpoints ===
@app.route('/tof/distance', methods=['GET'])
def get_distance():
    """Get current distance reading"""
    if not tof_sensor:
        return jsonify({"success": False, "error": "TOF sensor not available"}), 503
    
    distance = tof_sensor.read_distance()
    if distance is not None:
        return jsonify({
            "success": True,
            "distance_mm": distance,
            "timestamp": time.time()
        })
    else:
        return jsonify({
            "success": False,
            "error": tof_sensor.last_error,
            "timestamp": time.time()
        }), 500

@app.route('/tof/multiple', methods=['GET'])
def get_multiple_readings():
    """Get multiple distance readings"""
    if not tof_sensor:
        return jsonify({"success": False, "error": "TOF sensor not available"}), 503
    
    count = request.args.get('count', 10, type=int)
    interval = request.args.get('interval', 0.1, type=float)
    
    count = max(1, min(count, 100))
    interval = max(0.01, min(interval, 5.0))
    
    result = tof_sensor.read_multiple(count, interval)
    result["success"] = True
    return jsonify(result)

# === LED Controller Endpoints ===
@app.route('/led/expression', methods=['POST'])
def set_expression():
    """Set LED expression"""
    if not led_controller:
        return jsonify({"success": False, "error": "LED controller not available"}), 503
    
    data = request.get_json()
    expression = data.get('expression', 'normal')
    
    if expression not in led_controller.expressions:
        return jsonify({
            "success": False,
            "error": f"Unknown expression: {expression}",
            "available": list(led_controller.expressions.keys())
        }), 400
    
    success = led_controller.display_expression(expression)
    return jsonify({
        "success": success,
        "expression": expression,
        "timestamp": time.time()
    })

@app.route('/led/expression/<expression>', methods=['POST'])
def set_expression_path(expression):
    """Set LED expression via URL path"""
    if not led_controller:
        return jsonify({"success": False, "error": "LED controller not available"}), 503
    
    if expression not in led_controller.expressions:
        return jsonify({
            "success": False,
            "error": f"Unknown expression: {expression}",
            "available": list(led_controller.expressions.keys())
        }), 400
    
    success = led_controller.display_expression(expression)
    return jsonify({
        "success": success,
        "expression": expression,
        "timestamp": time.time()
    })

@app.route('/led/blink', methods=['POST'])
def blink():
    """Perform a blink animation"""
    if not led_controller:
        return jsonify({"success": False, "error": "LED controller not available"}), 503
    
    data = request.get_json() or {}
    base_expression = data.get('base_expression')
    duration = data.get('duration', 0.15)
    
    success = led_controller.blink(base_expression, duration)
    return jsonify({
        "success": success,
        "action": "blink",
        "duration": duration,
        "timestamp": time.time()
    })

@app.route('/led/animate', methods=['POST'])
def start_animation():
    """Start an expression animation"""
    if not led_controller:
        return jsonify({"success": False, "error": "LED controller not available"}), 503
    
    data = request.get_json()
    expressions = data.get('expressions', ['normal', 'happy'])
    duration = data.get('duration', 1.0)
    loop = data.get('loop', True)
    
    invalid = [e for e in expressions if e not in led_controller.expressions]
    if invalid:
        return jsonify({
            "success": False,
            "error": f"Unknown expressions: {invalid}",
            "available": list(led_controller.expressions.keys())
        }), 400
    
    led_controller.start_animation(expressions, duration, loop)
    return jsonify({
        "success": True,
        "action": "start_animation",
        "expressions": expressions,
        "duration": duration,
        "loop": loop,
        "timestamp": time.time()
    })

@app.route('/led/stop', methods=['POST'])
def stop_animation():
    """Stop current animation"""
    if not led_controller:
        return jsonify({"success": False, "error": "LED controller not available"}), 503
    
    led_controller.stop_current_animation()
    return jsonify({
        "success": True,
        "action": "stop_animation",
        "timestamp": time.time()
    })

@app.route('/led/expressions', methods=['GET'])
def get_expressions():
    """Get available expressions"""
    if not led_controller:
        return jsonify({"success": False, "error": "LED controller not available"}), 503
    
    return jsonify({
        "expressions": list(led_controller.expressions.keys()),
        "current": led_controller.current_expression
    })

# === Combined Actions ===
@app.route('/actions/proximity_reaction', methods=['POST'])
def proximity_reaction():
    """React to proximity - change expression based on distance"""
    if not tof_sensor or not led_controller:
        return jsonify({
            "success": False, 
            "error": "Both TOF sensor and LED controller required"
        }), 503
    
    distance = tof_sensor.read_distance()
    if distance is None:
        return jsonify({
            "success": False,
            "error": "Failed to read distance"
        }), 500
    
    # Determine expression based on distance
    if distance < 100:  # Very close
        expression = "love"
    elif distance < 300:  # Close
        expression = "happy" 
    elif distance < 800:  # Medium
        expression = "normal"
    else:  # Far
        expression = "sad"
    
    success = led_controller.display_expression(expression)
    return jsonify({
        "success": success,
        "distance_mm": distance,
        "expression": expression,
        "timestamp": time.time()
    })

if __name__ == "__main__":
    print("Starting Combined Hardware API server...")
    print(f"TOF sensor available: {tof_available}")
    print(f"LED controller available: {led_available}")
    print("\nAPI Endpoints:")
    print("  GET  /health - Health check")
    print("  GET  /status - Combined status")
    print("  GET  /tof/distance - Get distance")
    print("  GET  /tof/multiple - Get multiple readings")
    print("  POST /led/expression - Set expression")
    print("  POST /led/expression/<expr> - Set expression")
    print("  POST /led/blink - Blink animation")
    print("  POST /led/animate - Start animation")
    print("  POST /led/stop - Stop animation")
    print("  GET  /led/expressions - List expressions")
    print("  POST /actions/proximity_reaction - React to proximity")
    print()
    app.run(host='0.0.0.0', port=5000, debug=True)