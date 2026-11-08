#!/bin/bash
# ==============================================================================
# اسکریپت نصب و راه‌اندازی خودکار سرور کنترل رله ESP32 و بات تلگرام
# کانال یوتیوب: Elecnotech | کانال تلگرام: @IWnull
# ==============================================================================

set -e

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║          ESP32 Telegram IoT Gateway Auto-Installer         ║"
echo "║            YouTube: Elecnotech  |  Telegram: @IWnull       ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# بررسی دسترسی روت
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}[!] لطفاً این اسکریپت را با دسترسی root اجرا کنید (sudo bash setup.sh)${NC}"
  exit 1
fi

INSTALL_DIR="/opt/esp32-relay"
CURRENT_DIR=$(pwd)

echo -e "${YELLOW}[1/5] بروزرسانی پکیج‌ها و نصب پیش‌نیازها...${NC}"
apt-get update -y
apt-get install -y python3 python3-pip python3-venv curl ufw

echo -e "${YELLOW}[2/5] راه‌اندازی دایرکتوری در ${INSTALL_DIR}...${NC}"
mkdir -p "$INSTALL_DIR"
cp -r ./* "$INSTALL_DIR/"

echo -e "${YELLOW}[3/5] ایجاد محیط مجازی پایتون (Virtualenv)...${NC}"
cd "$INSTALL_DIR"
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo -e "${YELLOW}[4/5] باز کردن پورت 8085 در فایروال (UFW)...${NC}"
if command -v ufw >/dev/null 2>&1; then
    ufw allow 8085/tcp >/dev/null 2>&1 || true
fi

echo -e "${YELLOW}[5/5] ساخت و فعال‌سازی سرویس خودکار Systemd...${NC}"
cat << 'EOF' > /etc/systemd/system/esp32-relay.service
[Unit]
Description=ESP32 Telegram Relay IoT Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/esp32-relay
ExecStart=/opt/esp32-relay/venv/bin/python3 app.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable esp32-relay.service
systemctl restart esp32-relay.service

# دریافت آی‌پی سرور
SERVER_IP=$(curl -s -4 ifconfig.me || hostname -I | awk '{print $1}')

echo ""
echo -e "${GREEN}================================================================${NC}"
echo -e "${GREEN}🎉 نصب با موفقیت به پایان رسید و سرور فعال است!${NC}"
echo -e "${GREEN}================================================================${NC}"
echo ""
echo -e "🌐 ${BLUE}آدرس پنل تحت وب:${NC} http://${SERVER_IP}:8080"
echo -e "🤖 ${BLUE}آیدی ربات تلگرام:${NC} @ElecnoTechbot"
echo -e "⚙️ ${BLUE}پورت اتصال:${NC} 8080"
echo ""
echo -e "${YELLOW}📌 تنظیمات مورد نیاز در کد ESP32 (Arduino IDE):${NC}"
echo "--------------------------------------------------------"
echo "const char* serverUrl = \"http://${SERVER_IP}:8080/api/status?token=elecno_secret_key_8849\";"
echo "const char* heartbeatUrl = \"http://${SERVER_IP}:8080/api/heartbeat?token=elecno_secret_key_8849\";"
echo "--------------------------------------------------------"
echo ""
echo -e "دستورات کاربردی مدیریت سرویس:"
echo "  بررسی وضعیت لاگ:  journalctl -u esp32-relay -f"
echo "  ریستارت سرویس:    systemctl restart esp32-relay"
echo "  توقف سرویس:       systemctl stop esp32-relay"
echo ""
echo -e "کانال یوتیوب ما را دنبال کنید: ${BLUE}Elecnotech${NC}"
echo -e "کانال تلگرام: ${BLUE}@IWnull${NC}"
