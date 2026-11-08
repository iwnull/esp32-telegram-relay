# -*- coding: utf-8 -*-
"""
سرور مرکزی و وب‌سرویس کنترل رله ESP32 + ربات تلگرام
کانال یوتیوب: Elecnotech | کانال تلگرام: @IWnull
طراحی شده برای دور زدن فیلترینگ تلگرام با استفاده از سرور واسط (VPS)
"""

import os
import json
import time
import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, JSONResponse
import uvicorn
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)
from telegram.error import NetworkError, TimedOut, Conflict

try:
    import config
except ImportError:
    from server import config

# تنظیمات لاگ
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("ESP32-Server")

# ==================== مدیریت وضعیت سیستم ====================

STATE_FILE = config.STATE_FILE

default_state: Dict[str, Any] = {
    "relay1": 0,
    "relay2": 0,
    "last_updated": time.time()
}

device_info: Dict[str, Any] = {
    "last_seen": 0,
    "rssi": 0,
    "uptime": 0,
    "ip": "Unknown"
}


def load_state() -> Dict[str, Any]:
    """خواندن وضعیت رله‌ها از دیسک"""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading state file: {e}")
    return default_state.copy()


def save_state(state: Dict[str, Any]):
    """ذخیره وضعیت رله‌ها روی دیسک جهت پایداری بعد از ریستارت"""
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving state file: {e}")


relay_state = load_state()


def is_admin(user_id: int) -> bool:
    """بررسی دسترسی ادمین در تلگرام"""
    return not config.ADMIN_IDS or user_id in config.ADMIN_IDS


def is_device_online() -> bool:
    """بررسی آنلاین بودن برد ESP32 بر اساس پینگ‌های ارسال شده"""
    if device_info["last_seen"] == 0:
        return False
    diff = time.time() - device_info["last_seen"]
    return diff <= config.OFFLINE_THRESHOLD_SECONDS


# ==================== ربات تلگرام ====================

def build_telegram_keyboard() -> InlineKeyboardMarkup:
    """ساخت کیبورد شیشه‌ای کنترل رله‌ها و وضعیت"""
    r1_icon = "🟢 روشن" if relay_state.get("relay1") == 1 else "🔴 خاموش"
    r2_icon = "🟢 روشن" if relay_state.get("relay2") == 1 else "🔴 خاموش"
    online_icon = "🟢 آنلاین" if is_device_online() else "🔴 آفلاین"

    keyboard = [
        [
            InlineKeyboardButton(f"💡 لامپ ۱: {r1_icon}", callback_data="toggle_relay_1"),
        ],
        [
            InlineKeyboardButton(f"💡 لامپ ۲: {r2_icon}", callback_data="toggle_relay_2"),
        ],
        [
            InlineKeyboardButton(f"📶 وضعیت ESP32: {online_icon}", callback_data="check_status"),
        ],
        [
            InlineKeyboardButton("🔄 بروزرسانی", callback_data="refresh_menu"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def build_status_text() -> str:
    """متن پیام وضعیت سیستم در تلگرام"""
    r1_txt = "روشن 🟢" if relay_state.get("relay1") == 1 else "خاموش 🔴"
    r2_txt = "روشن 🟢" if relay_state.get("relay2") == 1 else "خاموش 🔴"

    if is_device_online():
        seconds_ago = int(time.time() - device_info["last_seen"])
        dev_status = (
            f"🟢 <b>متصل (آنلاین)</b>\n"
            f"   ├─ آخرین ارتباط: <code>{seconds_ago} ثانیه پیش</code>\n"
            f"   ├─ قدرت سیگنال وای‌فای: <code>{device_info['rssi']} dBm</code>\n"
            f"   └─ آی‌پی محلی: <code>{device_info['ip']}</code>"
        )
    else:
        dev_status = "🔴 <b>قطع (آفلاین)</b> - بردی در شبکه پاسخگو نیست"

    msg = (
        f"⚡ <b>پنل هوشمند کنترل رله با ESP32</b>\n"
        f"📺 <i>یوتیوب: {config.COMMUNITY['youtube']} | تلگرام: {config.COMMUNITY['telegram']}</i>\n"
        f"────────────────────\n"
        f"💡 <b>وضعیت لامپ ۱:</b> {r1_txt}\n"
        f"💡 <b>وضعیت لامپ ۲:</b> {r2_txt}\n"
        f"────────────────────\n"
        f"📡 <b>وضعیت برد ESP32:</b>\n"
        f"{dev_status}\n"
        f"────────────────────\n"
        f"<i>برای تغییر حالت هر لامپ، دکمه‌های زیر را لمس کنید:</i>"
    )
    return msg


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر دستور /start در تلگرام"""
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text(
            f"⛔ <b>دسترسی غیرمجاز!</b>\n"
            f"آیدی عددی شما: <code>{user.id}</code>\n"
            f"جهت استفاده، این آیدی باید در فایل <code>config.py</code> سرور تعریف شود.",
            parse_mode="HTML"
        )
        return

    text = build_status_text()
    keyboard = build_telegram_keyboard()
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هندلر کلیک روی دکمه‌های شیشه‌ای ربات"""
    query = update.callback_query
    user = query.from_user

    if not is_admin(user.id):
        await query.answer("⛔ شما اجازه دسترسی به این پنل را ندارید!", show_alert=True)
        return

    data = query.data

    if data == "toggle_relay_1":
        new_val = 0 if relay_state.get("relay1") == 1 else 1
        relay_state["relay1"] = new_val
        relay_state["last_updated"] = time.time()
        save_state(relay_state)
        state_str = "روشن 🟢" if new_val == 1 else "خاموش 🔴"
        await query.answer(f"💡 لامپ ۱ {state_str} شد.")

    elif data == "toggle_relay_2":
        new_val = 0 if relay_state.get("relay2") == 1 else 1
        relay_state["relay2"] = new_val
        relay_state["last_updated"] = time.time()
        save_state(relay_state)
        state_str = "روشن 🟢" if new_val == 1 else "خاموش 🔴"
        await query.answer(f"💡 لامپ ۲ {state_str} شد.")

    elif data == "check_status":
        if is_device_online():
            diff = int(time.time() - device_info["last_seen"])
            await query.answer(
                f"✅ برد آنلاین است!\nسیگنال: {device_info['rssi']} dBm\nآخرین پینگ: {diff} ثانیه پیش",
                show_alert=True
            )
        else:
            await query.answer("❌ برد آفلاین است! اتصال برق و وای‌فای برد را بررسی کنید.", show_alert=True)

    elif data == "refresh_menu":
        await query.answer("🔄 منو بروزرسانی شد.")

    # ویرایش متن پیام و کیبورد در تلگرام
    try:
        new_text = build_status_text()
        new_keyboard = build_telegram_keyboard()
        await query.edit_message_text(new_text, reply_markup=new_keyboard, parse_mode="HTML")
    except Exception as e:
        # اگر پیام تغییری نکرده باشد تلگرام خطا می‌دهد که طبیعی است
        pass


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """کنترل خطاهای تلگرام بدون کرش سرور"""
    error = context.error
    if isinstance(error, (NetworkError, TimedOut)):
        logger.warning(f"Telegram Network/Timeout: {error}")
        return
    if isinstance(error, Conflict):
        logger.error("Telegram Conflict: Another bot instance is running!")
        return
    logger.error(f"Telegram unhandled error: {error}", exc_info=context.error)


# ==================== وب‌سرویس FastAPI ====================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """مدیریت چرخه حیات ربات تلگرام در دل سرور FastAPI"""
    logger.info("در حال استارت ربات تلگرام...")
    bot_app = ApplicationBuilder().token(config.BOT_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start_handler))
    bot_app.add_handler(CommandHandler("status", start_handler))
    bot_app.add_handler(CallbackQueryHandler(callback_handler))
    bot_app.add_error_handler(error_handler)

    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_polling(drop_pending_updates=True)
    app.state.bot_app = bot_app
    logger.info(f"ربات تلگرام با موفقیت فعال شد! پورت وب‌سرور: {config.SERVER_PORT}")

    yield

    logger.info("در حال خاموش‌سازی ربات...")
    await bot_app.updater.stop()
    await bot_app.stop()
    await bot_app.shutdown()
    logger.info("ربات با موفقیت متوقف شد.")


app = FastAPI(
    title="ESP32 Telegram IoT Gateway",
    description="وب‌سرویس کنترل رله برای ESP32 در شرایط فیلترینگ تلگرام",
    version="2.0.0",
    lifespan=lifespan
)


def verify_token(token: str):
    """اعتبارسنجی توکن ارسالی از ESP32"""
    if config.DEVICE_TOKEN and token != config.DEVICE_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid device token")


# --- اندپوینت‌های اختصاصی ESP32 ---

@app.get("/api/status")
async def get_status(token: str = Query(..., description="Device security token")):
    """
    دریافت وضعیت کامل رله‌ها به صورت JSON (برای ESP32)
    """
    verify_token(token)
    return {
        "status": "ok",
        "relay1": relay_state.get("relay1", 0),
        "relay2": relay_state.get("relay2", 0),
        "online": is_device_online(),
        "timestamp": int(time.time())
    }


@app.get("/api/relay/{relay_num}/raw", response_class=PlainTextResponse)
async def get_relay_raw(relay_num: int, token: str = Query(...)):
    """
    ساده‌ترین حالت: ارسال عدد 1 یا 0 به صورت متن خالص (بدون نیاز به کتابخانه JSON در ESP32)
    """
    verify_token(token)
    key = f"relay{relay_num}"
    val = relay_state.get(key, 0)
    return str(val)


@app.get("/api/heartbeat")
async def receive_heartbeat(
    request: Request,
    token: str = Query(...),
    rssi: int = Query(0),
    uptime: int = Query(0)
):
    """
    اعلام زنده بودن و آنلاین بودن برد ESP32 همراه با کیفیت سیگنال وای‌فای
    """
    verify_token(token)
    client_ip = request.client.host if request.client else "Unknown"
    device_info["last_seen"] = time.time()
    device_info["rssi"] = rssi
    device_info["uptime"] = uptime
    device_info["ip"] = client_ip

    return {
        "status": "acknowledged",
        "relay1": relay_state.get("relay1", 0),
        "relay2": relay_state.get("relay2", 0),
    }


@app.post("/api/set")
async def set_relay_state(
    relay: int = Query(..., ge=1, le=2),
    state: int = Query(..., ge=0, le=1),
    token: str = Query(...)
):
    """تغییر مستقیم وضعیت رله از طریق API خارجی"""
    verify_token(token)
    key = f"relay{relay}"
    relay_state[key] = state
    relay_state["last_updated"] = time.time()
    save_state(relay_state)
    return {"status": "ok", "relay": relay, "new_state": state}


# --- داشبورد تحت وب شیک و اختصاصی ---

@app.get("/", response_class=HTMLResponse)
async def web_dashboard():
    """صفحه کنترل تحت وب ریسپانسیو و دارک‌مود"""
    r1_class = "active" if relay_state.get("relay1") == 1 else ""
    r2_class = "active" if relay_state.get("relay2") == 1 else ""
    r1_text = "روشن" if relay_state.get("relay1") == 1 else "خاموش"
    r2_text = "روشن" if relay_state.get("relay2") == 1 else "خاموش"

    online_badge = (
        '<span class="badge online">🟢 برد آنلاین</span>'
        if is_device_online()
        else '<span class="badge offline">🔴 برد آفلاین</span>'
    )

    html_content = f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>پنل هوشمند رله ESP32 | Elecnotech</title>
    <style>
        :root {{
            --bg: #0f172a;
            --card-bg: rgba(30, 41, 59, 0.7);
            --border: rgba(255, 255, 255, 0.1);
            --primary: #38bdf8;
            --success: #22c55e;
            --danger: #ef4444;
            --text: #f8fafc;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: system-ui, -apple-system, sans-serif; }}
        body {{
            background: radial-gradient(circle at top, #1e293b, var(--bg));
            color: var(--text);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }}
        .card {{
            background: var(--card-bg);
            backdrop-filter: blur(12px);
            border: 1px solid var(--border);
            border-radius: 24px;
            padding: 32px;
            width: 100%;
            max-width: 440px;
            box-shadow: 0 20px 50px rgba(0,0,0,0.4);
            text-align: center;
        }}
        h1 {{ font-size: 1.5rem; margin-bottom: 8px; color: var(--primary); }}
        p.subtitle {{ color: #94a3b8; font-size: 0.9rem; margin-bottom: 24px; }}
        .badge {{
            display: inline-block;
            padding: 6px 14px;
            border-radius: 50px;
            font-size: 0.85rem;
            margin-bottom: 24px;
            font-weight: bold;
        }}
        .badge.online {{ background: rgba(34, 197, 94, 0.15); color: var(--success); border: 1px solid var(--success); }}
        .badge.offline {{ background: rgba(239, 68, 68, 0.15); color: var(--danger); border: 1px solid var(--danger); }}
        .relays {{ display: flex; flex-direction: column; gap: 16px; margin-bottom: 28px; }}
        .relay-item {{
            background: rgba(15, 23, 42, 0.6);
            border: 1px solid var(--border);
            padding: 16px 20px;
            border-radius: 16px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .relay-item span {{ font-size: 1.1rem; font-weight: 500; }}
        .btn {{
            border: none;
            padding: 10px 22px;
            border-radius: 12px;
            cursor: pointer;
            font-size: 0.95rem;
            font-weight: 600;
            transition: all 0.2s ease;
            background: #334155;
            color: #94a3b8;
        }}
        .btn.active {{
            background: var(--success);
            color: #fff;
            box-shadow: 0 0 16px rgba(34, 197, 94, 0.4);
        }}
        .footer {{
            border-top: 1px solid var(--border);
            padding-top: 18px;
            font-size: 0.8rem;
            color: #64748b;
        }}
        .footer a {{ color: var(--primary); text-decoration: none; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="card">
        <h1>⚡ کنترل هوشمند رله</h1>
        <p class="subtitle">دروازه اختصاصی دور زدن فیلترینگ تلگرام</p>
        {online_badge}
        
        <div class="relays">
            <div class="relay-item">
                <span>💡 لامپ شماره ۱</span>
                <button class="btn {r1_class}" onclick="toggleRelay(1)">{r1_text}</button>
            </div>
            <div class="relay-item">
                <span>💡 لامپ شماره ۲</span>
                <button class="btn {r2_class}" onclick="toggleRelay(2)">{r2_text}</button>
            </div>
        </div>

        <div class="footer">
            طراحی شده برای کانال یوتیوب <a href="https://youtube.com/@Elecnotech" target="_blank">Elecnotech</a><br>
            کانال تلگرام: <a href="https://t.me/IWnull" target="_blank">@IWnull</a>
        </div>
    </div>

    <script>
        const TOKEN = "{config.DEVICE_TOKEN}";
        async function toggleRelay(num) {{
            const btn = event.target;
            const isCurrentlyActive = btn.classList.contains("active");
            const newState = isCurrentlyActive ? 0 : 1;
            
            try {{
                const res = await fetch(`/api/set?relay=${{num}}&state=${{newState}}&token=${{TOKEN}}`, {{ method: "POST" }});
                if(res.ok) {{
                    location.reload();
                }} else {{
                    alert("خطا در برقراری ارتباط با وب‌سرویس");
                }}
            }} catch(e) {{
                alert("خطای اتصال شبکه");
            }}
        }}
        
        // بازخوانی خودکار هر 6 ثانیه جهت همگام‌سازی با تغییرات تلگرام
        setTimeout(() => location.reload(), 6000);
    </script>
</body>
</html>"""
    return HTMLResponse(content=html_content)


def main():
    """اجرای سرور"""
    uvicorn.run(
        "app:app",
        host=config.SERVER_HOST,
        port=config.SERVER_PORT,
        log_level="info",
        reload=False
    )


if __name__ == "__main__":
    main()
