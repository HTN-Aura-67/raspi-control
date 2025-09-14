#!/usr/bin/env python3
"""
Quick Pi Test - Simple connectivity and functionality test
A lightweight version for quick checks
"""

import requests
import time
import argparse
import json

def quick_test(host: str, port: int = 5000):
    """Run a quick test of Pi functionality"""
    base_url = f"http://{host}:{port}"
    
    print(f"🔌 Quick Pi Test: {host}:{port}")
    print("-" * 40)
    
    try:
        # 1. Health check
        print("1️⃣  Health check...", end=" ")
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ {data['status']}")
            
            # Show service status
            services = data.get("services", {})
            for service, info in services.items():
                status = "🟢" if info.get("initialized") else "🟡" if info.get("available") else "🔴"
                print(f"   {status} {service}")
        else:
            print(f"❌ Status {response.status_code}")
            return False
        
        # 2. TOF reading
        print("2️⃣  TOF sensor...", end=" ")
        response = requests.get(f"{base_url}/tof/distance", timeout=5)
        if response.status_code == 200:
            data = response.json()
            distance = data.get("distance_mm", "N/A")
            print(f"✅ {distance}mm")
        elif response.status_code == 503:
            print("⚠️  Hardware not available")
        else:
            print(f"❌ Error {response.status_code}")
        
        # 3. LED expression
        print("3️⃣  LED expression...", end=" ")
        response = requests.post(f"{base_url}/led/expression/happy", timeout=5)
        if response.status_code == 200:
            print("✅ Set to happy")
            time.sleep(1)
            
            # Reset to normal
            requests.post(f"{base_url}/led/expression/normal", timeout=5)
        elif response.status_code == 503:
            print("⚠️  Hardware not available")
        else:
            print(f"❌ Error {response.status_code}")
        
        # 4. LED blink
        print("4️⃣  LED blink...", end=" ")
        response = requests.post(f"{base_url}/led/blink", 
                               json={"duration": 0.2}, timeout=5)
        if response.status_code == 200:
            print("✅ Blink successful")
        elif response.status_code == 503:
            print("⚠️  Hardware not available")
        else:
            print(f"❌ Error {response.status_code}")
        
        # 5. Proximity reaction
        print("5️⃣  Proximity reaction...", end=" ")
        response = requests.post(f"{base_url}/actions/proximity_reaction", timeout=5)
        if response.status_code == 200:
            data = response.json()
            distance = data.get("distance_mm", "N/A")
            expression = data.get("expression", "N/A")
            print(f"✅ {distance}mm → {expression}")
        elif response.status_code == 503:
            print("⚠️  Hardware not available")
        else:
            print(f"❌ Error {response.status_code}")
        
        print("\n🎉 Quick test completed!")
        return True
        
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to {host}:{port}")
        print("💡 Is your Pi running the API server?")
        return False
    except requests.exceptions.Timeout:
        print("❌ Request timeout")
        print("💡 Pi may be slow or overloaded")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Quick Pi connectivity test")
    parser.add_argument("host", help="Pi hostname or IP")
    parser.add_argument("--port", type=int, default=5000, help="API port")
    
    args = parser.parse_args()
    
    success = quick_test(args.host, args.port)
    exit(0 if success else 1)

if __name__ == "__main__":
    main()