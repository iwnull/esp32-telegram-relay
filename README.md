<div align="center">

# ⚡ ESP32 Telegram Relay IoT Gateway
### Smart Home Appliance Controller via Telegram Bot with Anti-Filtering Bypass Architecture

<p align="center">
  <a href="README.md">
    <img src="https://img.shields.io/badge/Language-English-blue?style=for-the-badge&logo=googletranslate&logoColor=white" alt="English">
  </a>
  <a href="README.fa.md">
    <img src="https://img.shields.io/badge/زبان-فارسی-green?style=for-the-badge&logo=googletranslate&logoColor=white" alt="Persian">
  </a>
</p>

[![YouTube Channel](https://img.shields.io/badge/YouTube-Elecnotech-red?style=for-the-badge&logo=youtube)](https://youtube.com/@Elecnotech)
[![Telegram Channel](https://img.shields.io/badge/Telegram-@IWnull-2CA5E0?style=for-the-badge&logo=telegram)](https://t.me/IWnull)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)
[![ESP32](https://img.shields.io/badge/Hardware-ESP32-E7352C?style=for-the-badge&logo=espressif&logoColor=white)](https://espressif.com)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)

<p align="center">
  A production-ready, reliable IoT solution designed to control AC/DC electrical appliances (lamps, outlets, motors) via Telegram, specifically engineered for environments where Telegram API is censored or blocked (e.g. Iran).
</p>

<p align="center">
  <a href="#-architecture">Architecture</a> •
  <a href="#-key-features">Key Features</a> •
  <a href="#-hardware--wiring">Hardware & Wiring</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-api-reference">API Reference</a> •
  <a href="#-web-dashboard">Web Dashboard</a> •
  <a href="#-author--community">Community</a>
</p>

</div>

---

## 🎯 The Problem & Our Solution

### ❌ The Challenge
In regions where `api.telegram.org` is strictly filtered or blocked (such as Iran), microcontrollers like **ESP32** or **ESP8266** cannot directly communicate with Telegram Bot APIs. Running VPN clients, WireGuard, or MTProto proxies directly on embedded microcontrollers is resource-heavy, unstable, and frequently disconnects.

### ✅ The Solution
This project introduces a **lightweight, decoupled Gateway Architecture**:
1. **Cloud Relay Server (VPS):** A Linux VPS outside the filtered zone hosts both the Telegram Bot worker and an ultra-fast **FastAPI** web service.
2. **User Control:** The user taps inline interactive buttons on Telegram (`@ElecnoTechbot`) to toggle relays.
3. **Local ESP32 Device:** The ESP32 connects to ordinary local home Wi-Fi (no VPN or proxy needed). It periodically polls the gateway using standard, lightweight HTTP requests to fetch relay states and executes switching commands.
4. **Heartbeat & Telemetry:** ESP32 continuously transmits Wi-Fi signal strength (`RSSI`) and uptime back to the server, enabling Telegram users to monitor live device connectivity (Online / Offline status).

---

## 🏗 System Architecture

```text
  ┌──────────────────────────────────────────────────────────────┐
  │                        TELEGRAM USER                         │
  │                  (Taps Inline Keyboard Buttons)              │
  └──────────────────────────────┬───────────────────────────────┘
                                 │ Telegram Bot API (HTTPS)
                                 ▼
  ┌──────────────────────────────────────────────────────────────┐
  │                    CENTRAL GATEWAY (VPS)                     │
  │                                                              │
  │  ┌──────────────────────┐          ┌──────────────────────┐  │
  │  │ Telegram Bot Worker  │◄────────►│  FastAPI REST Server │  │
  │  │  (python-telegram)   │          │  (Status & Web UI)   │  │
  │  └──────────────────────┘          └──────────┬───────────┘  │
  │                                               │              │
  │                    State Storage (JSON)       │              │
  └───────────────────────────────────────────────┼──────────────┘
                                                  │
                                                  │ HTTP Polling / Heartbeat
                                                  │ (Every 5s - No VPN Needed)
                                                  │
  ┌───────────────────────────────────────────────┼──────────────┐
  │ LOCAL NETWORK (Behind Filter / Firewall)      │              │
  │                                               ▼              │
  │                                    ┌──────────────────────┐  │
  │                                    │     ESP32 Board      │  │
  │                                    │  (WiFi + HTTPClient) │  │
  │                                    └──────────┬───────────┘  │
  │                                               │ GPIO Control │
  │                                               ▼              │
  │                                    ┌──────────────────────┐  │
  │                                    │     Relay Module     │  │
  │                                    │   (Optocoupler 5V)   │  │
  │                                    └──────────┬───────────┘  │
  │                                               │ 220V AC / DC │
  │                                               ▼              │
  │                                    ┌──────────────────────┐  │
  │                                    │  Lamp / Appliance    │  │
  └────────────────────────────────────┴──────────────────────┘──┘
```

---

## 🌟 Key Features

- 🚀 **Zero Third-Party Libraries on ESP32:** Uses native Arduino-ESP32 cores (`WiFi.h` and `HTTPClient.h`). No complex JSON libraries required on firmware.
- 🔒 **Dual-Layer Security:**
  - **Telegram Whitelist:** Strict numeric User ID authorization (`ADMIN_IDS`). Unauthorized users are blocked from executing relay actions.
  - **Device Token Authentication:** HTTP endpoints are protected with a pre-shared cryptographic token (`DEVICE_TOKEN`) against scanners and scrapers.
- 💾 **State Persistence:** In the event of a power outage or server restart, relay states are saved to disk (`relay_state.json`) and restored automatically.
- 📶 **Real-Time Telemetry & Heartbeat:** Tracks device connectivity, Wi-Fi RSSI signal quality (in dBm), and uptime seconds directly in the Telegram interface.
- 📱 **Responsive Dark-Mode Web Panel:** Built-in web dashboard accessible via mobile or desktop browser on port `8085`.
- 🛠 **One-Click Automated Linux Deployment:** Automated `setup.sh` installs virtual environments, dependencies, systemd daemon, and firewall rules.

---

## 🔌 Hardware & Wiring

### 1. ESP32 to Relay Module Pinout

| Relay Module Pin | ESP32 Pin | Description |
| :---: | :---: | :--- |
| **VCC** | **VIN / 5V** | 5V Power for relay coil (from USB charger) |
| **GND** | **GND** | Common Ground |
| **IN1** | **GPIO 26** | Control trigger for Relay 1 (Lamp 1) |
| **IN2** | **GPIO 27** | Control trigger for Relay 2 (Lamp 2 - Optional) |

> ℹ️ **Note on Relay Logic:** Most commercial optocoupler relay modules are **Active-LOW** (LOW signal triggers relay ON, HIGH signal turns OFF). This is configurable via `#define RELAY_ACTIVE_LOW true` in the firmware.

### 2. Mains AC Wiring (220V Lamp)

> ⚠️ **SAFETY WARNING:** High voltage AC power can be lethal. Ensure mains power is completely disconnected before wiring!

- Connect **Mains Phase (Line)** to the relay terminal marked **COM** (Common).
- Connect relay terminal **NO** (Normally Open) to one terminal of the lamp socket.
- Connect **Mains Neutral** directly to the second terminal of the lamp socket.

---

## 🚀 Quick Start

### Step 1: Server Setup (VPS)

1. SSH into your Ubuntu/Debian server:
   ```bash
   ssh root@YOUR_SERVER_IP
   ```
2. Navigate to the `server` directory:
   ```bash
   cd esp32-telegram-relay/server
   ```
3. Edit `config.py` to match your preferences:
   ```python
   BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
   ADMIN_IDS = [6046868533]       # Your numeric Telegram User ID
   DEVICE_TOKEN = "YOUR_SECRET_KEY" # Shared secret with ESP32
   SERVER_PORT = 8085
   ```
4. Run the automated installer:
   ```bash
   sudo bash setup.sh
   ```
   *The script sets up Python, isolates the environment, opens UFW port `8085`, and enables the `esp32-relay` systemd service.*

#### Manage Service
```bash
# View live logs
journalctl -u esp32-relay -f

# Restart or Stop service
systemctl restart esp32-relay
systemctl stop esp32-relay
```

---

### Step 2: Firmware Setup (ESP32 via Arduino IDE)

1. Open **Arduino IDE** (make sure ESP32 board package is installed).
2. Select your board from `Tools > Board > esp32 > DOIT ESP32 DEVKIT V1` (or your specific model).
3. Open `esp32/esp32_relay/esp32_relay.ino`.
4. Configure your Wi-Fi credentials and server address:
   ```cpp
   const char* WIFI_SSID     = "MyHomeWiFi";
   const char* WIFI_PASSWORD = "WiFiPassword123";
   const char* SERVER_HOST   = "128.140.61.50"; // Your VPS Public IP
   const int   SERVER_PORT   = 8085;
   const char* DEVICE_TOKEN  = "elecno_secret_key_8849";
   ```
5. Connect your ESP32 with a Micro-USB/Type-C cable and click **Upload**.
6. Open **Serial Monitor** at `115200` baud to verify Wi-Fi connection and heartbeat polling logs.

---

## 🤖 Telegram Bot Interface

1. Start a chat with your bot (e.g. `@ElecnoTechbot`).
2. Send `/start`.
3. An interactive inline dashboard will be displayed:

```text
⚡ Smart ESP32 Relay Controller
📺 YouTube: Elecnotech | Telegram: @IWnull
────────────────────
💡 Lamp 1 Status: ON 🟢
💡 Lamp 2 Status: OFF 🔴
────────────────────
📡 ESP32 Hardware Status:
🟢 Connected (Online)
   ├─ Last Seen: 2s ago
   ├─ Wi-Fi RSSI: -58 dBm
   └─ Local IP: 192.168.1.120
────────────────────
[ 💡 Lamp 1: 🟢 ON ]
[ 💡 Lamp 2: 🔴 OFF ]
[ 📶 ESP32 Status: 🟢 Online ]
[ 🔄 Refresh Menu ]
```

---

## 🌐 Web Dashboard

A lightweight, dark-mode web controller is accessible from any mobile or desktop browser:
```text
http://YOUR_SERVER_IP:8085/
```
Allows manual override and toggling without opening Telegram.

---

## 📡 API Reference

All requests must supply the device token via `?token=...`.

| Endpoint | Method | Query Parameters | Description |
| :--- | :---: | :--- | :--- |
| `/api/heartbeat` | `GET` | `token`, `rssi`, `uptime` | ESP32 heartbeat ping; returns current relay states |
| `/api/status` | `GET` | `token` | Full JSON status of all relays and connectivity |
| `/api/relay/{id}/raw` | `GET` | `token` | Returns raw string (`1` or `0`) for simple microcontrollers |
| `/api/set` | `POST` | `relay` (1-2), `state` (0-1), `token` | Direct programmatical relay control |

---

## 📁 Repository Structure

```text
esp32-telegram-relay/
├── LICENSE                 # MIT Open-Source License
├── README.md               # English Documentation (This file)
├── README.fa.md            # راهنمای جامع فارسی
├── server/
│   ├── app.py              # Unified FastAPI Server & Telegram Bot Engine
│   ├── config.py           # Configuration File (Tokens, Ports, Whitelists)
│   ├── requirements.txt    # Python Dependencies
│   └── setup.sh            # 1-Click Linux Systemd Auto-Installer
└── esp32/
    ├── wiring_diagram.txt  # Detailed Pinout and 220V AC wiring instructions
    └── esp32_relay/
        └── esp32_relay.ino # Production C++ ESP32 Firmware
```

---

## 👥 Author & Community

Developed and maintained by **Elecnotech**:
- 📺 **YouTube Channel:** [youtube.com/@Elecnotech](https://youtube.com/@Elecnotech) *(Subscribe for hardware tutorials & projects)*
- 📢 **Telegram Channel:** [t.me/IWnull](https://t.me/IWnull)

⭐ **If you find this project helpful, please give it a Star on GitHub!**

---

## 📄 License
This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.
