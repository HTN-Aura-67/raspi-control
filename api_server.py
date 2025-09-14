"""
Combined Hardware API Server
Serves both TOF sensor and LED control functionality in a single API
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'tof'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'led_control'))

from flask import Flask, jsonify, request
from flask_cors import CORS
import time

# Import our modules
try:
    from tof_api import TOFSensor
    tof_available = True
except ImportError:
    tof_available = False
    print("Warning: TOF sensor module not available")

try:
    from led_api import LEDController
    led_available = True
except ImportError:
    led_available = False
    print("Warning: LED controller module not available")

app = Flask(__name__)
CORS(app)  # Enable CORS for web interface

# Initialize hardware
tof_sensor = TOFSensor() if tof_available else None
led_controller = LEDController() if led_available else None

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