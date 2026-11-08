# -*- coding: utf-8 -*-
"""
تنظیمات پروژه کنترل رله با ESP32 و بات تلگرام
کانال یوتیوب: Elecnotech | کانال تلگرام: @IWnull
"""

import os

# توکن ربات تلگرام دریافت شده از BotFather
BOT_TOKEN = os.getenv("BOT_TOKEN", "9265429892:A**************3Vr-fFA")

# آیدی‌های عددی ادمین‌های مجاز تلگرام (جهت جلوگیری از دسترسی افراد غریبه)
# اگر لیست خالی باشد [] هر کاربری می‌تواند کنترل کند (پیشنهاد نمی‌شود)
ADMIN_IDS = [
    6046***533,  # آیدی شما
    5511***834,  # آیدی همکار
]

# توکن امنیتی اختصاصی برای ارتباط ESP32 با وب‌سرویس (برای جلوگیری از اسکنرهای اینترنت)
# همین مقدار را در کد آردوینو داخل متغیر DEVICE_TOKEN وارد کنید
DEVICE_TOKEN = os.getenv("DEVICE_TOKEN", "elecno_secret_key_8849")

# پورت و آدرس گوش دادن وب‌سرور روی VPS
SERVER_HOST = "0.0.0.0"
SERVER_PORT = int(os.getenv("PORT", "8085"))

# فایل ذخیره‌سازی وضعیت رله‌ها (تا در صورت ریستارت سرور وضعیت حفظ شود)
STATE_FILE = "relay_state.json"

# مدت زمان (به ثانیه) که اگر از ESP32 خبری نشد، آفلاین در نظر گرفته شود
OFFLINE_THRESHOLD_SECONDS = 20

# اطلاعات کانال و سازنده
COMMUNITY = {
    "youtube": "Elecnotech",
    "telegram": "@IWnull",
    "project": "ESP32 Telegram IoT Controller"
}
