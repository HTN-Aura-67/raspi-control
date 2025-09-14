# Raspberry Pi Setup Guide for Hardware API

## 🔧 Hardware Requirements

### Components:
- Raspberry Pi 4 (recommended) or Pi 3B+
- VL53L0X Time-of-Flight sensor
- MAX7219 LED matrix (8x8 or 16x8)
- MicroSD card (32GB+ recommended)
- Camera module (optional, for camera streaming)

### Connections:

#### VL53L0X TOF Sensor (I2C):
```
VL53L0X    →    Raspberry Pi
VCC        →    3.3V (Pin 1)
GND        →    GND (Pin 6)
SCL        →    GPIO 3 (SCL, Pin 5)
SDA        →    GPIO 2 (SDA, Pin 3)
```

#### MAX7219 LED Matrix (SPI):
```
MAX7219    →    Raspberry Pi
VCC        →    5V (Pin 2)
GND        →    GND (Pin 6)
DIN        →    GPIO 10 (MOSI, Pin 19)
CS         →    GPIO 8 (CE0, Pin 24)
CLK        →    GPIO 11 (SCLK, Pin 23)
```

## 📦 Software Installation

### 1. Update System:
```bash
sudo apt update && sudo apt upgrade -y
```

### 2. Enable Interfaces:
```bash
sudo raspi-config
# Navigate to: Interface Options
# Enable: I2C, SPI, Camera (if using)
sudo reboot
```

### 3. Install Python Dependencies:
```bash
# System packages
sudo apt install -y python3-pip python3-venv git

# Create virtual environment
python3 -m venv ~/raspi-venv
source ~/raspi-venv/bin/activate

# Install hardware libraries
pip install adafruit-circuitpython-vl53l0x
pip install luma.led-matrix
pip install RPi.GPIO

# Install API requirements
pip install flask flask-cors requests websockets

# For camera streaming (if needed)
pip install opencv-python  # or skip if not using OpenCV
```

### 4. Clone and Setup Project:
```bash
git clone https://github.com/HTN-Aura-67/raspi-control.git
cd raspi-control
source ~/raspi-venv/bin/activate
pip install -r requirements_api.txt
```

## 🚀 Running the APIs

### Option 1: Combined API Server (Recommended)
```bash
# Single server with all functionality
python api_server.py
```
- Runs on: http://raspberrypi.local:5000
- Includes: TOF sensor + LED control + health monitoring

### Option 2: Individual Servers
```bash
# Terminal 1 - TOF Sensor API
python tof/tof_api.py

# Terminal 2 - LED Control API  
python led_control/led_api.py

# Terminal 3 - Camera Stream (if needed)
python camera/camera_stream.py
```

### Option 3: Auto-start on Boot
```bash
# Create systemd service
sudo nano /etc/systemd/system/raspi-api.service
```

Add:
```ini
[Unit]
Description=Raspberry Pi Hardware API
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/raspi-control
Environment=PATH=/home/pi/raspi-venv/bin
ExecStart=/home/pi/raspi-venv/bin/python api_server.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl enable raspi-api.service
sudo systemctl start raspi-api.service
```

## 🧪 Testing on Raspberry Pi

### 1. Run Tests Locally:
```bash
cd tests
python run_tests.py --all
```

### 2. Test from Remote Computer:
```bash
# Replace 'raspberrypi.local' with your Pi's IP
curl http://raspberrypi.local:5000/health
curl http://raspberrypi.local:5000/tof/distance
curl -X POST http://raspberrypi.local:5000/led/expression/happy
```

### 3. Demo Mode:
```bash
python tests/run_tests.py --demo
```

## 🌐 Network Access

### Find Pi IP Address:
```bash
hostname -I
```

### Access from Other Devices:
- Replace `localhost` with Pi's IP address
- Example: `http://192.168.1.100:5000/health`
- Or use: `http://raspberrypi.local:5000/health`

## 🔍 Troubleshooting

### Common Issues:

#### 1. I2C/SPI Not Working:
```bash
# Check interfaces are enabled
sudo raspi-config

# Test I2C devices
sudo i2cdetect -y 1

# Test SPI
ls /dev/spi*
```

#### 2. Permission Errors:
```bash
# Add user to required groups
sudo usermod -a -G spi,gpio,i2c pi
```

#### 3. Hardware Not Detected:
```bash
# Check connections and power
# Verify wiring matches pinout above
# Test with simple scripts first
```

#### 4. Module Import Errors:
```bash
# Ensure virtual environment is activated
source ~/raspi-venv/bin/activate

# Reinstall problematic packages
pip install --upgrade adafruit-circuitpython-vl53l0x
pip install --upgrade luma.led-matrix
```

## 📊 Performance Tips

### For Better Performance:
```bash
# Increase GPU memory split
sudo raspi-config → Advanced Options → Memory Split → 128

# Disable unnecessary services
sudo systemctl disable bluetooth
sudo systemctl disable wifi-powersave

# Use faster SD card (Class 10 or better)
```

## 🔗 API Endpoints

Once running on Pi, access via:

### Health & Status:
- `GET /health` - System health check
- `GET /status` - Detailed component status

### TOF Sensor:
- `GET /tof/distance` - Current distance
- `GET /tof/multiple?count=10` - Multiple readings

### LED Control:
- `POST /led/expression/happy` - Set expression
- `POST /led/blink` - Blink animation
- `GET /led/expressions` - Available expressions

### Combined Actions:
- `POST /actions/proximity_reaction` - Auto-react to distance

## 📱 Mobile/Web Interface

The API supports CORS, so you can build web interfaces:

```javascript
// Example web interface
fetch('http://raspberrypi.local:5000/tof/distance')
  .then(response => response.json())
  .then(data => console.log('Distance:', data.distance_mm));

fetch('http://raspberrypi.local:5000/led/expression/happy', {
  method: 'POST'
});
```

Your Raspberry Pi is now ready to run the complete hardware API system! 🤖