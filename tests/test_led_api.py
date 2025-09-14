"""
LED Control API Tests
Tests for the MAX7219 LED matrix eye control API functionality
"""

import unittest
import requests
import time
import json
from typing import Dict, Any

class TestLEDControlAPI(unittest.TestCase):
    """Test cases for LED Control API"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.base_url = "http://localhost:5002"
        self.timeout = 5
        self.valid_expressions = [
            "normal", "happy", "sad", "wink", "love", "closed", "off"
        ]
    
    def test_get_expressions(self):
        """Test getting available expressions"""
        print("\n👁️  Testing available expressions...")
        
        try:
            response = requests.get(f"{self.base_url}/led/expressions", timeout=self.timeout)
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertIn("expressions", data)
            self.assertIn("current", data)
            
            expressions = data["expressions"]
            self.assertIsInstance(expressions, list)
            self.assertTrue(len(expressions) > 0)
            
            # Check that all expected expressions are available
            for expr in self.valid_expressions:
                self.assertIn(expr, expressions)
            
            print(f"✅ Available expressions: {', '.join(expressions)}")
            print(f"   Current: {data['current']}")
            
        except requests.exceptions.ConnectionError:
            self.skipTest("LED API server not running on port 5002")
    
    def test_set_expression_json(self):
        """Test setting expression via JSON payload"""
        print("\n😊 Testing expression setting (JSON)...")
        
        try:
            for expression in ["normal", "happy", "sad"]:
                payload = {"expression": expression}
                response = requests.post(f"{self.base_url}/led/expression",
                                       json=payload, timeout=self.timeout)
                self.assertEqual(response.status_code, 200)
                
                data = response.json()
                self.assertTrue(data.get("success"))
                self.assertEqual(data.get("expression"), expression)
                self.assertIn("timestamp", data)
                
                print(f"✅ Set expression: {expression}")
                time.sleep(0.5)  # Brief pause between expressions
                
        except requests.exceptions.ConnectionError:
            self.skipTest("LED API server not running on port 5002")
    
    def test_set_expression_path(self):
        """Test setting expression via URL path"""
        print("\n😉 Testing expression setting (URL path)...")
        
        try:
            for expression in ["wink", "love", "normal"]:
                response = requests.post(f"{self.base_url}/led/expression/{expression}",
                                       timeout=self.timeout)
                self.assertEqual(response.status_code, 200)
                
                data = response.json()
                self.assertTrue(data.get("success"))
                self.assertEqual(data.get("expression"), expression)
                
                print(f"✅ Set expression via path: {expression}")
                time.sleep(0.5)
                
        except requests.exceptions.ConnectionError:
            self.skipTest("LED API server not running on port 5002")
    
    def test_blink_animation(self):
        """Test blink animation"""
        print("\n👀 Testing blink animation...")
        
        try:
            # Test basic blink
            response = requests.post(f"{self.base_url}/led/blink", timeout=self.timeout)
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertTrue(data.get("success"))
            self.assertEqual(data.get("action"), "blink")
            
            print("✅ Basic blink successful")
            
            # Test blink with custom parameters
            payload = {"base_expression": "happy", "duration": 0.2}
            response = requests.post(f"{self.base_url}/led/blink",
                                   json=payload, timeout=self.timeout)
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertTrue(data.get("success"))
            self.assertEqual(data.get("duration"), 0.2)
            
            print("✅ Custom blink successful")
            
        except requests.exceptions.ConnectionError:
            self.skipTest("LED API server not running on port 5002")
    
    def test_animation_sequence(self):
        """Test animation sequence"""
        print("\n🎭 Testing animation sequence...")
        
        try:
            # Start animation
            payload = {
                "expressions": ["normal", "happy", "love"],
                "duration": 0.5,
                "loop": False
            }
            response = requests.post(f"{self.base_url}/led/animate",
                                   json=payload, timeout=self.timeout)
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertTrue(data.get("success"))
            self.assertEqual(data.get("action"), "start_animation")
            self.assertEqual(data.get("expressions"), payload["expressions"])
            
            print("✅ Animation started")
            
            # Wait for animation to run
            time.sleep(2)
            
            # Stop animation
            response = requests.post(f"{self.base_url}/led/stop", timeout=self.timeout)
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertTrue(data.get("success"))
            self.assertEqual(data.get("action"), "stop_animation")
            
            print("✅ Animation stopped")
            
        except requests.exceptions.ConnectionError:
            self.skipTest("LED API server not running on port 5002")
    
    def test_led_status(self):
        """Test LED controller status"""
        print("\n📋 Testing LED status...")
        
        try:
            response = requests.get(f"{self.base_url}/led/status", timeout=self.timeout)
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertIn("initialized", data)
            self.assertIn("hardware_available", data)
            self.assertIn("current_expression", data)
            self.assertIn("available_expressions", data)
            self.assertIn("animation_running", data)
            
            print(f"✅ LED initialized: {data['initialized']}")
            print(f"   Hardware available: {data['hardware_available']}")
            print(f"   Current expression: {data['current_expression']}")
            print(f"   Animation running: {data['animation_running']}")
            
        except requests.exceptions.ConnectionError:
            self.skipTest("LED API server not running on port 5002")
    
    def test_invalid_expression(self):
        """Test invalid expression handling"""
        print("\n⚠️  Testing invalid expression...")
        
        try:
            payload = {"expression": "invalid_expression"}
            response = requests.post(f"{self.base_url}/led/expression",
                                   json=payload, timeout=self.timeout)
            self.assertEqual(response.status_code, 400)
            
            data = response.json()
            self.assertFalse(data.get("success"))
            self.assertIn("error", data)
            self.assertIn("available", data)
            
            print("✅ Invalid expression properly rejected")
            
        except requests.exceptions.ConnectionError:
            self.skipTest("LED API server not running on port 5002")
    
    def test_expression_cycle(self):
        """Test cycling through all expressions"""
        print("\n🔄 Testing expression cycle...")
        
        try:
            response = requests.get(f"{self.base_url}/led/expressions", timeout=self.timeout)
            if response.status_code != 200:
                self.skipTest("Cannot get expressions list")
            
            expressions = response.json()["expressions"]
            
            for expression in expressions[:4]:  # Test first 4 to save time
                payload = {"expression": expression}
                response = requests.post(f"{self.base_url}/led/expression",
                                       json=payload, timeout=self.timeout)
                self.assertEqual(response.status_code, 200)
                
                data = response.json()
                self.assertTrue(data.get("success"))
                
                time.sleep(0.3)  # Brief display time
            
            print(f"✅ Successfully cycled through {len(expressions[:4])} expressions")
            
        except requests.exceptions.ConnectionError:
            self.skipTest("LED API server not running on port 5002")

def run_led_tests():
    """Run all LED control tests"""
    print("👁️  Running LED Control API Tests")
    print("=" * 50)
    
    suite = unittest.TestLoader().loadTestsFromTestCase(TestLEDControlAPI)
    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)
    
    print(f"\n📊 LED Test Results:")
    print(f"   Tests run: {result.testsRun}")
    print(f"   Failures: {len(result.failures)}")
    print(f"   Errors: {len(result.errors)}")
    print(f"   Skipped: {len(result.skipped)}")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    run_led_tests()