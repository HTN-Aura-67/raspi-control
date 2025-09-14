#!/usr/bin/env python3
"""
Pi Hardware Demo - Interactive demonstration of Pi capabilities
Shows off all the hardware features in a fun demo sequence
"""

import requests
import time
import argparse
import json
import random

class PiDemo:
    def __init__(self, host: str, port: int = 5000):
        self.base_url = f"http://{host}:{port}"
        self.host = host
        self.port = port
        
    def check_connection(self) -> bool:
        """Check if Pi is connected and responding"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_services_status(self) -> dict:
        """Get current service status"""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                return response.json().get("services", {})
        except:
            pass
        return {}
    
    def demo_expressions(self):
        """Demo all available LED expressions"""
        print("\n🎭 LED Expression Demo")
        print("-" * 30)
        
        try:
            # Get available expressions
            response = requests.get(f"{self.base_url}/led/expressions", timeout=5)
            if response.status_code != 200:
                print("⚠️  LED controller not available")
                return
            
            expressions = response.json().get("expressions", [])
            print(f"Available expressions: {', '.join(expressions)}")
            
            # Show each expression
            for i, expr in enumerate(expressions):
                print(f"   {i+1}/{len(expressions)} Showing: {expr}")
                requests.post(f"{self.base_url}/led/expression/{expr}", timeout=5)
                time.sleep(2)
            
            print("✅ Expression demo complete")
            
        except Exception as e:
            print(f"❌ Expression demo failed: {e}")
    
    def demo_blink_sequence(self):
        """Demo different blink patterns"""
        print("\n👀 Blink Demo")
        print("-" * 30)
        
        try:
            # Different blink patterns
            patterns = [
                {"base_expression": "normal", "duration": 0.1, "name": "Quick blink"},
                {"base_expression": "happy", "duration": 0.3, "name": "Slow blink"},
                {"base_expression": "love", "duration": 0.2, "name": "Love blink"}
            ]
            
            for pattern in patterns:
                print(f"   {pattern['name']}")
                for _ in range(3):
                    response = requests.post(f"{self.base_url}/led/blink", 
                                           json=pattern, timeout=5)
                    if response.status_code != 200:
                        print("⚠️  LED controller not available")
                        return
                    time.sleep(0.8)
                time.sleep(1)
            
            print("✅ Blink demo complete")
            
        except Exception as e:
            print(f"❌ Blink demo failed: {e}")
    
    def demo_animation(self):
        """Demo LED animation sequences"""
        print("\n🎬 Animation Demo")
        print("-" * 30)
        
        try:
            animations = [
                {
                    "name": "Happy sequence",
                    "expressions": ["normal", "happy", "love", "happy", "normal"],
                    "duration": 0.8
                },
                {
                    "name": "Emotion cycle", 
                    "expressions": ["sad", "normal", "happy", "love"],
                    "duration": 1.0
                },
                {
                    "name": "Wink sequence",
                    "expressions": ["normal", "wink", "normal", "wink"],
                    "duration": 0.6
                }
            ]
            
            for anim in animations:
                print(f"   {anim['name']}: {' → '.join(anim['expressions'])}")
                
                response = requests.post(f"{self.base_url}/led/animate",
                                       json={
                                           "expressions": anim["expressions"],
                                           "duration": anim["duration"],
                                           "loop": False
                                       }, timeout=5)
                
                if response.status_code != 200:
                    print("⚠️  LED controller not available")
                    return
                
                # Wait for animation to complete
                time.sleep(len(anim["expressions"]) * anim["duration"] + 1)
                
                # Stop animation (just in case)
                requests.post(f"{self.base_url}/led/stop", timeout=5)
                time.sleep(1)
            
            print("✅ Animation demo complete")
            
        except Exception as e:
            print(f"❌ Animation demo failed: {e}")
    
    def demo_distance_monitoring(self):
        """Demo distance sensor with live readings"""
        print("\n📏 Distance Sensor Demo")
        print("-" * 30)
        
        try:
            print("Taking 10 distance readings...")
            
            readings = []
            for i in range(10):
                response = requests.get(f"{self.base_url}/tof/distance", timeout=5)
                if response.status_code != 200:
                    print("⚠️  TOF sensor not available")
                    return
                
                data = response.json()
                distance = data.get("distance_mm")
                readings.append(distance)
                
                # Visual distance bar
                bar_length = 20
                max_distance = 2000  # mm
                bar_fill = int((distance / max_distance) * bar_length)
                bar = "█" * bar_fill + "░" * (bar_length - bar_fill)
                
                print(f"   {i+1:2d}: {distance:4d}mm |{bar}|")
                time.sleep(0.5)
            
            # Statistics
            print(f"\n   📊 Statistics:")
            print(f"      Min: {min(readings)}mm")
            print(f"      Max: {max(readings)}mm") 
            print(f"      Avg: {sum(readings)/len(readings):.1f}mm")
            print("✅ Distance demo complete")
            
        except Exception as e:
            print(f"❌ Distance demo failed: {e}")
    
    def demo_proximity_reactions(self):
        """Demo proximity-based reactions"""
        print("\n🤖 Proximity Reaction Demo")
        print("-" * 30)
        
        try:
            print("Testing proximity reactions (10 readings)...")
            
            for i in range(10):
                response = requests.post(f"{self.base_url}/actions/proximity_reaction", timeout=5)
                if response.status_code != 200:
                    print("⚠️  Hardware not available for proximity reactions")
                    return
                
                data = response.json()
                distance = data.get("distance_mm")
                expression = data.get("expression")
                
                # Reaction explanation
                if distance < 100:
                    reaction = "😍 Very close - showing love!"
                elif distance < 300:
                    reaction = "😊 Close - showing happiness!"
                elif distance < 800:
                    reaction = "😐 Medium distance - normal expression"
                else:
                    reaction = "😢 Far away - looking sad"
                
                print(f"   {i+1:2d}: {distance:4d}mm → {expression:6s} | {reaction}")
                time.sleep(1.5)
            
            print("✅ Proximity reaction demo complete")
            
        except Exception as e:
            print(f"❌ Proximity reaction demo failed: {e}")
    
    def demo_interactive_mode(self):
        """Interactive mode - respond to user input"""
        print("\n🎮 Interactive Mode")
        print("-" * 30)
        print("Commands: happy, sad, love, wink, normal, blink, quit")
        
        try:
            while True:
                cmd = input("Enter command: ").strip().lower()
                
                if cmd == "quit":
                    break
                elif cmd == "blink":
                    response = requests.post(f"{self.base_url}/led/blink", timeout=5)
                    if response.status_code == 200:
                        print("👀 Blink!")
                    else:
                        print("❌ Blink failed")
                elif cmd in ["happy", "sad", "love", "wink", "normal", "closed", "off"]:
                    response = requests.post(f"{self.base_url}/led/expression/{cmd}", timeout=5)
                    if response.status_code == 200:
                        print(f"🎭 Set to {cmd}")
                    else:
                        print(f"❌ Failed to set {cmd}")
                elif cmd == "distance":
                    response = requests.get(f"{self.base_url}/tof/distance", timeout=5)
                    if response.status_code == 200:
                        data = response.json()
                        print(f"📏 Distance: {data.get('distance_mm')}mm")
                    else:
                        print("❌ Distance reading failed")
                else:
                    print("❓ Unknown command")
            
            print("✅ Interactive mode ended")
            
        except KeyboardInterrupt:
            print("\n✅ Interactive mode ended")
        except Exception as e:
            print(f"❌ Interactive mode failed: {e}")
    
    def run_full_demo(self):
        """Run the complete demo sequence"""
        print("🎪 Raspberry Pi Hardware Demo")
        print("=" * 50)
        print(f"Target: {self.host}:{self.port}")
        
        # Check connection
        if not self.check_connection():
            print(f"❌ Cannot connect to Pi at {self.host}:{self.port}")
            return False
        
        # Check services
        services = self.get_services_status()
        print("\n📊 Service Status:")
        for service, info in services.items():
            status = "🟢" if info.get("initialized") else "🟡" if info.get("available") else "🔴"
            print(f"   {status} {service}: available={info.get('available')}, initialized={info.get('initialized')}")
        
        print("\n🚀 Starting demo sequence...")
        
        # Run demo sections
        self.demo_expressions()
        time.sleep(2)
        
        self.demo_blink_sequence()
        time.sleep(2)
        
        self.demo_animation()
        time.sleep(2)
        
        self.demo_distance_monitoring()
        time.sleep(2)
        
        self.demo_proximity_reactions()
        time.sleep(2)
        
        # Reset to normal
        print("\n🔄 Resetting to normal state...")
        requests.post(f"{self.base_url}/led/expression/normal", timeout=5)
        
        print("\n🎉 Demo complete! Your Pi hardware is working great!")
        
        # Offer interactive mode
        try:
            choice = input("\nStart interactive mode? (y/N): ").strip().lower()
            if choice in ['y', 'yes']:
                self.demo_interactive_mode()
        except KeyboardInterrupt:
            pass
        
        return True

def main():
    parser = argparse.ArgumentParser(description="Interactive Pi hardware demo")
    parser.add_argument("host", help="Pi hostname or IP")
    parser.add_argument("--port", type=int, default=5000, help="API port")
    parser.add_argument("--quick", action="store_true", help="Quick demo (skip some sections)")
    
    args = parser.parse_args()
    
    demo = PiDemo(args.host, args.port)
    
    try:
        success = demo.run_full_demo()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
        exit(1)

if __name__ == "__main__":
    main()