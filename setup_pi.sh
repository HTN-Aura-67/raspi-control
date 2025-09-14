#!/bin/bash
# Raspberry Pi Quick Setup Script
# Run with: curl -s https://raw.githubusercontent.com/HTN-Aura-67/raspi-control/main/setup_pi.sh | bash

echo "🤖 Raspberry Pi Hardware API Setup"
echo "=================================="

# Update system
echo "📦 Updating system packages..."
sudo apt update && sudo apt upgrade -y

# Install system dependencies
echo "🔧 Installing system dependencies..."
sudo apt install -y python3-pip python3-venv git i2c-tools

# Enable I2C and SPI
echo "⚡ Enabling I2C and SPI interfaces..."
sudo raspi-config nonint do_i2c 0
sudo raspi-config nonint do_spi 0

# Create virtual environment
echo "🐍 Creating Python virtual environment..."
python3 -m venv ~/raspi-venv
# shellcheck source=/dev/null
source ~/raspi-venv/bin/activate

# Install Python packages
echo "📚 Installing Python packages..."
pip install --upgrade pip
pip install adafruit-circuitpython-vl53l0x
pip install luma.led-matrix
pip install RPi.GPIO
pip install flask flask-cors requests websockets

# Add user to hardware groups
echo "👤 Adding user to hardware groups..."
sudo usermod -a -G spi,gpio,i2c $USER

# Clone repository (if not already present)
if [ ! -d "raspi-control" ]; then
    echo "📥 Cloning repository..."
    git clone https://github.com/HTN-Aura-67/raspi-control.git
fi

cd raspi-control || { echo "Failed to enter raspi-control directory"; exit 1; }

# Install project requirements
echo "📋 Installing project requirements..."
pip install -r requirements_api.txt 2>/dev/null || echo "No requirements_api.txt found, skipping..."

# Create systemd service
echo "🔧 Creating systemd service..."
sudo tee /etc/systemd/system/raspi-api.service > /dev/null << EOF
[Unit]
Description=Raspberry Pi Hardware API
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$HOME/raspi-control
Environment=PATH=$HOME/raspi-venv/bin
ExecStart=$HOME/raspi-venv/bin/python api_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start service
echo "🚀 Enabling API service..."
sudo systemctl enable raspi-api.service
sudo systemctl daemon-reload

# Test hardware connections
echo "🔍 Testing hardware connections..."
echo "I2C devices:"
sudo i2cdetect -y 1

echo "SPI devices:"
ls /dev/spi* 2>/dev/null || echo "No SPI devices found"

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Reboot your Pi: sudo reboot"
echo "2. Check service status: sudo systemctl status raspi-api"
echo "3. Test API: curl http://localhost:5000/health"
echo "4. View logs: sudo journalctl -u raspi-api -f"
echo ""
echo "🌐 Access your API at:"
echo "   http://$(hostname).local:5000"
echo "   http://$(hostname -I | awk '{print $1}'):5000"
echo ""
echo "🧪 Run tests with:"
echo "   cd raspi-control/tests && python run_tests.py --all"