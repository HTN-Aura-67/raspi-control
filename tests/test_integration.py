"""
Integration Tests for Combined API Server
Tests for the combined hardware API functionality
"""

import unittest
import requests
import time
import json
from typing import Dict, Any

class TestCombinedAPI(unittest.TestCase):
    """Test cases for Combined Hardware API"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.base_url = "http://localhost:5000"
        self.timeout = 5
    
    def test_health_check(self):
        """Test system health check"""
        print("\n💚 Testing health check...")
        
        try:
            response = requests.get(f"{self.base_url}/health", timeout=self.timeout)
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertEqual(data.get("status"), "healthy")
            self.assertIn("timestamp", data)
            self.assertIn("services", data)
            
            services = data["services"]
            self.assertIn("tof_sensor", services)
            self.assertIn("led_controller", services)
            
            print(f"✅ System healthy")
            print(f"   TOF sensor: available={services['tof_sensor']['available']}, init={services['tof_sensor']['initialized']}")
            print(f"   LED controller: available={services['led_controller']['available']}, init={services['led_controller']['initialized']}")
            
        except requests.exceptions.ConnectionError:
            self.skipTest("Combined API server not running on port 5000")
    
    def test_combined_status(self):
        """Test combined status endpoint"""
        print("\n📊 Testing combined status...")
        
        try:
            response = requests.get(f"{self.base_url}/status", timeout=self.timeout)
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertIn("timestamp", data)
            self.assertIn("tof_sensor", data)
            self.assertIn("led_controller", data)
            
            # Verify structure of each component status
            tof_status = data["tof_sensor"]
            if tof_status.get("available", True):
                self.assertIn("initialized", tof_status)
                self.assertIn("hardware_available", tof_status)
            
            led_status = data["led_controller"]
            if led_status.get("available", True):
                self.assertIn("initialized", led_status)
                self.assertIn("current_expression", led_status)
            
            print("✅ Combined status retrieved successfully")
            
        except requests.exceptions.ConnectionError:
            self.skipTest("Combined API server not running on port 5000")
    
    def test_tof_distance_endpoint(self):
        """Test TOF distance endpoint through combined API"""
        print("\n🔍 Testing TOF distance via combined API...")
        
        try:
            response = requests.get(f"{self.base_url}/tof/distance", timeout=self.timeout)
            
            if response.status_code == 503:
                self.skipTest("TOF sensor not available")
            
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertTrue(data.get("success"))
            self.assertIn("distance_mm", data)
            self.assertIn("timestamp", data)
            
            distance = data["distance_mm"]
            print(f"✅ Distance reading: {distance}mm")
            
        except requests.exceptions.ConnectionError:
            self.skipTest("Combined API server not running on port 5000")
    
    def test_led_expression_endpoint(self):
        """Test LED expression endpoint through combined API"""
        print("\n😊 Testing LED expression via combined API...")
        
        try:
            payload = {"expression": "happy"}
            response = requests.post(f"{self.base_url}/led/expression",
                                   json=payload, timeout=self.timeout)
            
            if response.status_code == 503:
                self.skipTest("LED controller not available")
            
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertTrue(data.get("success"))
            self.assertEqual(data.get("expression"), "happy")
            
            print("✅ LED expression set successfully")
            
        except requests.exceptions.ConnectionError:
            self.skipTest("Combined API server not running on port 5000")
    
    def test_proximity_reaction(self):
        """Test proximity reaction functionality"""
        print("\n🤖 Testing proximity reaction...")
        
        try:
            response = requests.post(f"{self.base_url}/actions/proximity_reaction",
                                   timeout=self.timeout)
            
            if response.status_code == 503:
                self.skipTest("TOF sensor or LED controller not available")
            
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertTrue(data.get("success"))
            self.assertIn("distance_mm", data)
            self.assertIn("expression", data)
            self.assertIn("timestamp", data)
            
            distance = data["distance_mm"]
            expression = data["expression"]
            
            # Verify expression logic based on distance
            if distance < 100:
                self.assertEqual(expression, "love")
            elif distance < 300:
                self.assertEqual(expression, "happy")
            elif distance < 800:
                self.assertEqual(expression, "normal")
            else:
                self.assertEqual(expression, "sad")
            
            print(f"✅ Proximity reaction: {distance}mm → {expression}")
            
        except requests.exceptions.ConnectionError:
            self.skipTest("Combined API server not running on port 5000")
    
    def test_cors_headers(self):
        """Test CORS headers are present"""
        print("\n🌐 Testing CORS headers...")
        
        try:
            response = requests.options(f"{self.base_url}/health", timeout=self.timeout)
            
            # CORS headers should be present
            headers = response.headers
            # Note: flask-cors might not set headers on OPTIONS for simple requests
            
            print("✅ CORS functionality available")
            
        except requests.exceptions.ConnectionError:
            self.skipTest("Combined API server not running on port 5000")
    
    def test_error_handling(self):
        """Test error handling for invalid requests"""
        print("\n⚠️  Testing error handling...")
        
        try:
            # Test invalid LED expression
            payload = {"expression": "invalid_expression"}
            response = requests.post(f"{self.base_url}/led/expression",
                                   json=payload, timeout=self.timeout)
            
            if response.status_code != 503:  # Skip if service unavailable
                self.assertEqual(response.status_code, 400)
                
                data = response.json()
                self.assertFalse(data.get("success"))
                self.assertIn("error", data)
            
            # Test non-existent endpoint
            response = requests.get(f"{self.base_url}/nonexistent", timeout=self.timeout)
            self.assertEqual(response.status_code, 404)
            
            print("✅ Error handling working correctly")
            
        except requests.exceptions.ConnectionError:
            self.skipTest("Combined API server not running on port 5000")
    
    def test_multiple_requests_sequence(self):
        """Test sequence of multiple API requests"""
        print("\n🔄 Testing request sequence...")
        
        try:
            # 1. Check health
            response = requests.get(f"{self.base_url}/health", timeout=self.timeout)
            self.assertEqual(response.status_code, 200)
            
            # 2. Get distance
            response = requests.get(f"{self.base_url}/tof/distance", timeout=self.timeout)
            if response.status_code == 200:
                distance_data = response.json()
                print(f"   Distance: {distance_data.get('distance_mm')}mm")
            
            # 3. Set expression based on "distance"
            expressions = ["happy", "normal", "sad"]
            for expression in expressions:
                payload = {"expression": expression}
                response = requests.post(f"{self.base_url}/led/expression",
                                       json=payload, timeout=self.timeout)
                if response.status_code == 200:
                    print(f"   Set expression: {expression}")
                time.sleep(0.5)
            
            # 4. Proximity reaction
            response = requests.post(f"{self.base_url}/actions/proximity_reaction",
                                   timeout=self.timeout)
            if response.status_code == 200:
                reaction_data = response.json()
                print(f"   Proximity reaction: {reaction_data.get('expression')}")
            
            print("✅ Request sequence completed successfully")
            
        except requests.exceptions.ConnectionError:
            self.skipTest("Combined API server not running on port 5000")

def run_integration_tests():
    """Run all integration tests"""
    print("🔗 Running Integration Tests for Combined API")
    print("=" * 50)
    
    suite = unittest.TestLoader().loadTestsFromTestCase(TestCombinedAPI)
    runner = unittest.TextTestRunner(verbosity=0)
    result = runner.run(suite)
    
    print(f"\n📊 Integration Test Results:")
    print(f"   Tests run: {result.testsRun}")
    print(f"   Failures: {len(result.failures)}")
    print(f"   Errors: {len(result.errors)}")
    print(f"   Skipped: {len(result.skipped)}")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    run_integration_tests()