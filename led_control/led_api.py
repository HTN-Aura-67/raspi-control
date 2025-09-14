"""
LED Control API
Provides functions and REST endpoints for MAX7219 LED matrix eye control
"""

import time
import threading
from typing import Dict, List, Any, Optional
from flask import Flask, jsonify, request

try:
    from luma.core.interface.serial import spi, noop
    from luma.led_matrix.device import max7219
    from luma.core.render import canvas
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False
    print("Warning: LED hardware libraries not available. Using mock mode.")

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
        
        if HARDWARE_AVAILABLE:
            self.initialize_device()
    
    def initialize_device(self) -> bool:
        """Initialize the LED matrix device"""
        try:
            if HARDWARE_AVAILABLE:
                serial = spi(port=0, device=0, gpio=noop())
                self.device = max7219(serial, cascaded=2, block_orientation=0, rotate=0)
                self.is_initialized = True
                print("LED matrix initialized successfully")
            return True
        except Exception as e:
            print(f"Failed to initialize LED matrix: {e}")
            return False
    
    def display_expression(self, expression: str) -> bool:
        """Display a specific eye expression"""
        if expression not in self.expressions:
            return False
        
        self.current_expression = expression
        eye_pattern = self.expressions[expression]
        
        if HARDWARE_AVAILABLE and self.device:
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
            # Mock mode - just print
            print(f"Mock: Displaying expression '{expression}'")
            return True
    
    def blink(self, base_expression: str = None, duration: float = 0.15) -> bool:
        """Perform a blink animation"""
        if base_expression is None:
            base_expression = self.current_expression
        
        if base_expression not in self.expressions:
            return False
        
        # Display closed eyes
        self.display_expression("closed")
        time.sleep(duration)
        
        # Return to base expression
        self.display_expression(base_expression)
        return True
    
    def start_animation(self, expressions: List[str], duration: float = 1.0, loop: bool = True):
        """Start an animation cycling through expressions"""
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
        """Stop the current animation"""
        self.stop_animation = True
        if self.animation_thread and self.animation_thread.is_alive():
            self.animation_thread.join()
    
    def get_status(self) -> Dict[str, Any]:
        """Get LED controller status"""
        return {
            "initialized": self.is_initialized,
            "hardware_available": HARDWARE_AVAILABLE,
            "current_expression": self.current_expression,
            "available_expressions": list(self.expressions.keys()),
            "animation_running": self.animation_thread is not None and self.animation_thread.is_alive()
        }

# Global LED controller instance
led_controller = LEDController()

# Flask API
app = Flask(__name__)

@app.route('/led/expression', methods=['POST'])
def set_expression():
    """Set LED expression"""
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
    data = request.get_json()
    expressions = data.get('expressions', ['normal', 'happy'])
    duration = data.get('duration', 1.0)
    loop = data.get('loop', True)
    
    # Validate expressions
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
    led_controller.stop_current_animation()
    return jsonify({
        "success": True,
        "action": "stop_animation",
        "timestamp": time.time()
    })

@app.route('/led/status', methods=['GET'])
def get_status():
    """Get LED controller status"""
    return jsonify(led_controller.get_status())

@app.route('/led/expressions', methods=['GET'])
def get_expressions():
    """Get available expressions"""
    return jsonify({
        "expressions": list(led_controller.expressions.keys()),
        "current": led_controller.current_expression
    })

if __name__ == "__main__":
    print("Starting LED Control API server...")
    print(f"Hardware available: {HARDWARE_AVAILABLE}")
    app.run(host='0.0.0.0', port=5002, debug=True)