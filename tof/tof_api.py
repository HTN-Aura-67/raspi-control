"""
TOF Sensor API
Provides functions and REST endpoints for VL53L0X distance sensor
"""

import time
import json
from typing import Optional, Dict, Any
from flask import Flask, jsonify, request

try:
    import board
    import busio
    import adafruit_vl53l0x
    HARDWARE_AVAILABLE = True
except ImportError:
    HARDWARE_AVAILABLE = False
    print("Warning: Hardware libraries not available. Using mock mode.")

class TOFSensor:
    def __init__(self):
        self.sensor = None
        self.is_initialized = False
        self.last_reading = None
        self.last_error = None
        
        if HARDWARE_AVAILABLE:
            self.initialize_sensor()
    
    def initialize_sensor(self) -> bool:
        """Initialize the TOF sensor"""
        try:
            if HARDWARE_AVAILABLE:
                i2c = busio.I2C(board.SCL, board.SDA)
                self.sensor = adafruit_vl53l0x.VL53L0X(i2c)
                self.is_initialized = True
                print("TOF sensor initialized successfully")
            return True
        except Exception as e:
            self.last_error = str(e)
            print(f"Failed to initialize TOF sensor: {e}")
            return False
    
    def read_distance(self) -> Optional[int]:
        """Read distance in millimeters"""
        if not self.is_initialized and HARDWARE_AVAILABLE:
            if not self.initialize_sensor():
                return None
        
        try:
            if HARDWARE_AVAILABLE and self.sensor:
                distance = self.sensor.range
                self.last_reading = distance
                self.last_error = None
                return distance
            else:
                # Mock reading for testing
                import random
                distance = random.randint(100, 2000)
                self.last_reading = distance
                return distance
        except Exception as e:
            self.last_error = str(e)
            print(f"Error reading distance: {e}")
            return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get sensor status and information"""
        return {
            "initialized": self.is_initialized,
            "hardware_available": HARDWARE_AVAILABLE,
            "last_reading": self.last_reading,
            "last_error": self.last_error,
            "timestamp": time.time()
        }
    
    def read_multiple(self, count: int = 10, interval: float = 0.1) -> Dict[str, Any]:
        """Read multiple distance measurements"""
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

# Global sensor instance
tof_sensor = TOFSensor()

# Flask API
app = Flask(__name__)

@app.route('/tof/distance', methods=['GET'])
def get_distance():
    """Get current distance reading"""
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

@app.route('/tof/status', methods=['GET'])
def get_status():
    """Get sensor status"""
    return jsonify(tof_sensor.get_status())

@app.route('/tof/multiple', methods=['GET'])
def get_multiple_readings():
    """Get multiple distance readings"""
    count = request.args.get('count', 10, type=int)
    interval = request.args.get('interval', 0.1, type=float)
    
    # Limit to reasonable values
    count = max(1, min(count, 100))
    interval = max(0.01, min(interval, 5.0))
    
    result = tof_sensor.read_multiple(count, interval)
    result["success"] = True
    return jsonify(result)

@app.route('/tof/init', methods=['POST'])
def initialize():
    """Reinitialize the sensor"""
    success = tof_sensor.initialize_sensor()
    return jsonify({
        "success": success,
        "message": "Sensor initialized" if success else "Failed to initialize sensor",
        "error": tof_sensor.last_error if not success else None
    })

if __name__ == "__main__":
    print("Starting TOF Sensor API server...")
    print(f"Hardware available: {HARDWARE_AVAILABLE}")
    app.run(host='0.0.0.0', port=5001, debug=True)