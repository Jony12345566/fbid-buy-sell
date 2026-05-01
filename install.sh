#!/bin/bash

echo "====================================="
echo "FB ID Bot Installation for Ubuntu"
echo "====================================="

# Update system
echo "📦 Updating system packages..."
sudo apt update

# Install Python3 and pip if not installed
echo "🐍 Installing Python3 and pip..."
sudo apt install -y python3 python3-pip python3-venv

# Create virtual environment (optional but recommended)
echo "📁 Creating virtual environment..."
python3 -m venv venv
source venv/bin/activate

# Install required packages
echo "📥 Installing Python packages..."
pip install --upgrade pip
pip install pyTelegramBotAPI==4.15.0
pip install telebot==0.0.4

# Make the bot executable
chmod +x fb_id_bot.py

# Create systemd service file (optional - for auto-start)
echo "🛠 Creating systemd service (optional)..."
sudo bash -c 'cat > /etc/systemd/system/fbidbot.service << EOF
[Unit]
Description=FB ID Telegram Bot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory='$(pwd)'
ExecStart='$(pwd)'/venv/bin/python3 '$(pwd)'/fb_id_bot.py
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF'

echo "====================================="
echo "✅ Installation Complete!"
echo "====================================="
echo ""
echo "To run the bot:"
echo "1. Activate virtual environment: source venv/bin/activate"
echo "2. Run: python3 fb_id_bot.py"
echo ""
echo "OR to run as service (auto-start):"
echo "sudo systemctl start fbidbot"
echo "sudo systemctl enable fbidbot"
echo ""
echo "To check bot status: sudo systemctl status fbidbot"
echo "To view logs: sudo journalctl -u fbidbot -f"
echo ""
echo "====================================="
