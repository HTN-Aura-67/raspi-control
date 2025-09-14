"""
TOF Sensor API Tests
Tests for the VL53L0X distance sensor API functionality
"""

import unittest
import requests
import time
import json
from typing import Dict, Any

class TestTOFSensorAPI(unittest.TestCase):
    """Test cases for TOF Sensor API"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.base_url = "http://localhost:5001"
        self.timeout = 5
    
    def test_distance_reading(self):
        """Test single distance reading"""
        print("\n🔍 Testing single distance reading...")
        
        try:
            response = requests.get(f"{self.base_url}/tof/distance", timeout=self.timeout)
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertTrue(data.get("success"))
            self.assertIn("distance_mm", data)
            self.assertIn("timestamp", data)
            
            # Check distance is reasonable (0-8000mm for VL53L0X)
            distance = data["distance_mm"]
            self.assertGreaterEqual(distance, 0)
            self.assertLessEqual(distance, 8000)
            
            print(f"✅ Distance reading: {distance}mm")
            
        except requests.exceptions.ConnectionError:
            self.skipTest("TOF API server not running on port 5001")
    
    def test_multiple_readings(self):
        """Test multiple distance readings"""
        print("\n📊 Testing multiple readings...")
        
        try:
            params = {"count": 5, "interval": 0.1}
            response = requests.get(f"{self.base_url}/tof/multiple", 
                                  params=params, timeout=self.timeout)
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertTrue(data.get("success"))
            self.assertIn("readings", data)
            self.assertIn("statistics", data)
            
            readings = data["readings"]
            self.assertEqual(len(readings), 5)
            
            # Check each reading structure
            for reading in readings:
                self.assertIn("distance_mm", reading)
                self.assertIn("timestamp", reading)
                self.assertIn("reading", reading)
            
            # Check statistics
            stats = data["statistics"]
            self.assertIn("min", stats)
            self.assertIn("max", stats)
            self.assertIn("avg", stats)
            self.assertIn("count", stats)
            
            print(f"✅ Got {len(readings)} readings")
            print(f"   Stats: min={stats['min']}mm, max={stats['max']}mm, avg={stats['avg']:.1f}mm")
            
        except requests.exceptions.ConnectionError:
            self.skipTest("TOF API server not running on port 5001")
    
    def test_sensor_status(self):
        """Test sensor status endpoint"""
        print("\n📋 Testing sensor status...")
        
        try:
            response = requests.get(f"{self.base_url}/tof/status", timeout=self.timeout)
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertIn("initialized", data)
            self.assertIn("hardware_available", data)
            self.assertIn("timestamp", data)
            
            print(f"✅ Sensor initialized: {data['initialized']}")
            print(f"   Hardware available: {data['hardware_available']}")
            
        except requests.exceptions.ConnectionError:
            self.skipTest("TOF API server not running on port 5001")
    
    def test_sensor_initialization(self):
        """Test sensor re-initialization"""
        print("\n🔄 Testing sensor initialization...")
        
        try:
            response = requests.post(f"{self.base_url}/tof/init", timeout=self.timeout)
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertIn("success", data)
            self.assertIn("message", data)
            
            print(f"✅ Initialization result: {data['message']}")
            
        except requests.exceptions.ConnectionError:
            self.skipTest("TOF API server not running on port 5001")
    
    def test_invalid_parameters(self):
        """Test API with invalid parameters"""
        print("\n⚠️  Testing invalid parameters...")
        
        try:
            # Test with extreme values
            params = {"count": 1000, "interval": 10}
            response = requests.get(f"{self.base_url}/tof/multiple", 
                                  params=params, timeout=15)
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            # Should be clamped to reasonable values
            self.assertLessEqual(len(data["readings"]), 100)
            
            print("✅ Parameter validation working")
            
        except requests.exceptions.ConnectionError:
            self.skipTest("TOF API server not running on port 5001")

def run_tof_tests():
    """Run all TOF sensor tests"""
    print("🔍 Running TOF Sensor API Tests")
    print("=" * 50)
    
    suite = unittest.TestLoader().loadTestsFromTestCase(TestTOFSensorAPI)
    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)
    
    print(f"\n📊 TOF Test Results:")
    print(f"   Tests run: {result.testsRun}")
    print(f"   Failures: {len(result.failures)}")
    print(f"   Errors: {len(result.errors)}")
    print(f"   Skipped: {len(result.skipped)}")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    run_tof_tests()