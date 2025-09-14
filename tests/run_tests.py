#!/usr/bin/env python3
"""
Hardware API Test Runner
Comprehensive testing suite for the consolidated hardware API

This script runs tests for:
- TOF Sensor API endpoints (on combined server port 5000)
- LED Control API endpoints (on combined server port 5000)  
- Combined API Server functionality
- Integration tests

Usage:
    python run_tests.py [--individual] [--integration] [--all] [--demo]
"""

import sys
import os
import time
import argparse
import subprocess
import threading
import requests
from typing import List, Tuple

# Add tests directory to path
sys.path.append(os.path.dirname(__file__))

try:
    from test_tof_api import run_tof_tests
    from test_led_api import run_led_tests
    from test_integration import run_integration_tests
except ImportError as e:
    print(f"Error importing test modules: {e}")
    sys.exit(1)

class TestRunner:
    """Main test runner class"""
    
    def __init__(self):
        self.results = {}
        self.servers = {
            "combined": {"port": 5000, "process": None}
        }
    
    def check_server(self, name: str, port: int, timeout: int = 5) -> bool:
        """Check if a server is running on the specified port"""
        try:
            response = requests.get(f"http://localhost:{port}/health", timeout=timeout)
            return response.status_code == 200
        except:
            try:
                # Try alternative endpoints
                endpoints = {
                    "combined": "/status"
                }
                endpoint = endpoints.get(name, "/health")
                response = requests.get(f"http://localhost:{port}{endpoint}", timeout=timeout)
                return response.status_code == 200
            except:
                return False
    
    def wait_for_server(self, name: str, port: int, timeout: int = 10) -> bool:
        """Wait for server to become available"""
        print(f"⏳ Waiting for {name} server on port {port}...")
        
        for i in range(timeout):
            if self.check_server(name, port, timeout=1):
                print(f"✅ {name} server is ready")
                return True
            time.sleep(1)
            print(f"   Attempt {i+1}/{timeout}")
        
        print(f"❌ {name} server not available after {timeout}s")
        return False
    
    def start_server(self, server_type: str) -> bool:
        """Start a server process"""
        server_files = {
            "combined": "api_server.py"
        }
        
        if server_type not in server_files:
            print(f"❌ Unknown server type: {server_type}")
            return False
        
        script_path = os.path.join("..", server_files[server_type])
        if not os.path.exists(script_path):
            print(f"❌ Server script not found: {script_path}")
            return False
        
        print(f"🚀 Starting {server_type} server...")
        try:
            process = subprocess.Popen([
                sys.executable, script_path
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            self.servers[server_type]["process"] = process
            
            # Wait for server to start
            return self.wait_for_server(server_type, self.servers[server_type]["port"])
            
        except Exception as e:
            print(f"❌ Failed to start {server_type} server: {e}")
            return False
    
    def stop_servers(self):
        """Stop all running server processes"""
        for name, info in self.servers.items():
            if info["process"]:
                print(f"🛑 Stopping {name} server...")
                info["process"].terminate()
                info["process"].wait()
                info["process"] = None
    
    def run_individual_tests(self) -> Tuple[bool, bool, bool]:
        """Run individual API tests"""
        print("\n" + "="*60)
        print("🧪 RUNNING INDIVIDUAL API TESTS")
        print("="*60)
        
        # Test TOF API endpoints on combined server
        print("\n1️⃣  TOF Sensor API Tests (via Combined API)")
        print("-" * 30)
        tof_success = False
        if self.check_server("combined", 5000):
            tof_success = run_tof_tests()
        else:
            print("⚠️  Combined API server not running on port 5000")
            print("   Run: python api_server.py")
        
        # Test LED API endpoints on combined server
        print("\n2️⃣  LED Control API Tests (via Combined API)")
        print("-" * 30)
        led_success = False
        if self.check_server("combined", 5000):
            led_success = run_led_tests()
        else:
            print("⚠️  Combined API server not running on port 5000")
            print("   Run: python api_server.py")
        
        return tof_success, led_success, True
    
    def run_integration_tests(self) -> bool:
        """Run integration tests"""
        print("\n" + "="*60)
        print("🔗 RUNNING INTEGRATION TESTS")
        print("="*60)
        
        if self.check_server("combined", 5000):
            return run_integration_tests()
        else:
            print("⚠️  Combined API server not running on port 5000")
            print("   Run: python api_server.py")
            return False
    
    def run_demo_sequence(self):
        """Run a demonstration sequence"""
        print("\n" + "="*60)
        print("🎭 RUNNING DEMO SEQUENCE")
        print("="*60)
        
        base_url = "http://localhost:5000"
        
        if not self.check_server("combined", 5000):
            print("❌ Combined API server not available for demo")
            return False
        
        try:
            print("\n🎬 Starting hardware demo...")
            
            # 1. Health check
            print("1️⃣  Checking system health...")
            response = requests.get(f"{base_url}/health", timeout=5)
            if response.status_code == 200:
                health = response.json()
                print(f"   ✅ System status: {health['status']}")
            
            # 2. Show available expressions
            print("\n2️⃣  Getting available LED expressions...")
            response = requests.get(f"{base_url}/led/expressions", timeout=5)
            if response.status_code == 200:
                data = response.json()
                print(f"   Available: {', '.join(data['expressions'])}")
            
            # 3. Expression demo
            print("\n3️⃣  LED expression demonstration...")
            expressions = ["normal", "happy", "love", "wink", "sad"]
            for expr in expressions:
                print(f"   👁️  Showing: {expr}")
                requests.post(f"{base_url}/led/expression/{expr}", timeout=5)
                time.sleep(1.5)
            
            # 4. Blink demo
            print("\n4️⃣  Blink demonstration...")
            for i in range(3):
                print(f"   👀 Blink {i+1}/3")
                requests.post(f"{base_url}/led/blink", 
                            json={"duration": 0.2}, timeout=5)
                time.sleep(0.8)
            
            # 5. Distance reading demo
            print("\n5️⃣  Distance sensor demonstration...")
            for i in range(5):
                response = requests.get(f"{base_url}/tof/distance", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    distance = data.get("distance_mm", "N/A")
                    print(f"   📏 Reading {i+1}: {distance}mm")
                time.sleep(0.5)
            
            # 6. Proximity reaction demo
            print("\n6️⃣  Proximity reaction demonstration...")
            for i in range(3):
                response = requests.post(f"{base_url}/actions/proximity_reaction", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    distance = data.get("distance_mm", "N/A")
                    expression = data.get("expression", "N/A")
                    print(f"   🤖 Reaction {i+1}: {distance}mm → {expression}")
                time.sleep(2)
            
            # 7. Animation demo
            print("\n7️⃣  Animation demonstration...")
            print("   🎭 Starting happy animation...")
            requests.post(f"{base_url}/led/animate", json={
                "expressions": ["normal", "happy", "love", "happy"],
                "duration": 0.8,
                "loop": False
            }, timeout=5)
            
            time.sleep(4)
            
            # 8. Reset to normal
            print("\n8️⃣  Resetting to normal...")
            requests.post(f"{base_url}/led/expression/normal", timeout=5)
            
            print("\n✅ Demo sequence completed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Demo failed: {e}")
            return False
    
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*60)
        print("📋 TEST SUMMARY")
        print("="*60)
        
        if not self.results:
            print("No tests were run")
            return
        
        total_success = all(self.results.values())
        
        for test_name, success in self.results.items():
            status = "✅ PASS" if success else "❌ FAIL"
            print(f"   {test_name}: {status}")
        
        print(f"\nOverall Result: {'✅ ALL TESTS PASSED' if total_success else '❌ SOME TESTS FAILED'}")
        
        # Recommendations
        print("\n💡 Recommendations:")
        if not self.check_server("combined", 5000):
            print("   • Start combined API server: python api_server.py")
        
        print("   • Install requirements: pip install -r requirements_api.txt")
        print("   • Check hardware connections on Raspberry Pi")

def main():
    parser = argparse.ArgumentParser(description="Hardware API Test Runner")
    parser.add_argument("--individual", action="store_true", 
                       help="Run individual API tests")
    parser.add_argument("--integration", action="store_true",
                       help="Run integration tests")
    parser.add_argument("--all", action="store_true",
                       help="Run all tests")
    parser.add_argument("--demo", action="store_true",
                       help="Run demo sequence")
    parser.add_argument("--auto-start", action="store_true",
                       help="Automatically start servers if needed")
    
    args = parser.parse_args()
    
    # Default to all tests if no specific option
    if not any([args.individual, args.integration, args.demo]):
        args.all = True
    
    runner = TestRunner()
    
    try:
        print("🧪 Hardware API Test Runner")
        print("=" * 60)
        
        # Auto-start servers if requested
        if args.auto_start:
            print("\n🚀 Auto-starting servers...")
            if not runner.check_server("combined", 5000):
                runner.start_server("combined")
        
        # Run requested tests
        if args.all or args.individual:
            tof_result, led_result, _ = runner.run_individual_tests()
            runner.results["TOF API"] = tof_result
            runner.results["LED API"] = led_result
        
        if args.all or args.integration:
            integration_result = runner.run_integration_tests()
            runner.results["Integration"] = integration_result
        
        if args.demo:
            demo_result = runner.run_demo_sequence()
            runner.results["Demo"] = demo_result
        
        # Print summary
        runner.print_summary()
        
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
    finally:
        if args.auto_start:
            runner.stop_servers()

if __name__ == "__main__":
    main()