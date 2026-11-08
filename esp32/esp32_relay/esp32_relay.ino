/*
 * ==============================================================================
 * پروژه کنترل رله با ESP32 و بات تلگرام (دور زدن فیلترینگ)
 * کانال یوتیوب: Elecnotech  |  کانال تلگرام: @IWnull
 * 
 * نیازمندی‌ها:
 *  - برد ESP32 (هر مدلی مانند NodeMCU-32S, ESP32 Wroom)
 *  - ماژول رله ۱ یا ۲ یا ۴ کاناله (۵ ولت با تحریک اپتوکوپلر)
 *  - ال‌ای‌دی نمایشگر روی برد (GPIO 2)
 * 
 * بدون نیاز به نصب هیچ کتابخانه جانبی! 
 * (کتابخانه‌های WiFi.h و HTTPClient.h به صورت پیش‌فرض در هسته ESP32 وجود دارند)
 * ==============================================================================
 */

#include <WiFi.h>
#include <HTTPClient.h>

// ==================== تنظیمات وای‌فای (WiFi) ====================
const char* WIFI_SSID     = "********";      // نام مودم وای‌فای خود را بنویسید
const char* WIFI_PASSWORD = "********";  // رمز عبور وای‌فای

// ==================== تنظیمات سرور و وب‌سرویس ====================
// آی‌پی سرور مجازی (VPS) یا دامنه خود را به همراه پورت وارد کنید
const char* SERVER_HOST   = "128.***.61.50";      // آی‌پی سرور شما
const int   SERVER_PORT   = 8085;
const char* DEVICE_TOKEN  = "elecno_secret_key_8849"; // دقیقاً مطابق با config.py سرور

// بازه زمانی استعلام وضعیت از سرور (میلی‌ثانیه) - پیش‌فرض ۵ ثانیه
const unsigned long POLL_INTERVAL = 5000; 

// ==================== تنظیمات پین‌های سخت‌افزاری ====================
#define RELAY1_PIN   26   // پین فرمان رله ۱ (لامپ ۱)
#define RELAY2_PIN   27   // پین فرمان رله ۲ (لامپ ۲ - اختیاری)
#define STATUS_LED    2   // ال‌ای‌دی آبی روی خود برد ESP32

// آیا ماژول رله شما Active Low است؟ 
// (در ۹۵٪ ماژول‌های رله بازار، صفر ولت رله را روشن و ۳.۳ ولت خاموش می‌کند)
#define RELAY_ACTIVE_LOW true

// ==================== متغیرهای داخلی ====================
unsigned long lastPollTime = 0;
int currentRelay1State = -1; // -1: نامشخص در ابتدای کار
int currentRelay2State = -1;

// تابع راه‌اندازی و ست کردن وضعیت رله
void setRelay(int pin, int state) {
  if (RELAY_ACTIVE_LOW) {
    digitalWrite(pin, state == 1 ? LOW : HIGH);
  } else {
    digitalWrite(pin, state == 1 ? HIGH : LOW);
  }
}

// تابع اتصال به شبکه وای‌فای با قابلیت تلاش مجدد خودکار
void connectToWiFi() {
  Serial.println();
  Serial.print("در حال اتصال به وای‌فای: ");
  Serial.println(WIFI_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 30) {
    delay(500);
    digitalWrite(STATUS_LED, !digitalRead(STATUS_LED)); // چشمک زدن ال‌ای‌دی
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    digitalWrite(STATUS_LED, HIGH); // روشن ماندن دائم ال‌ای‌دی به نشانه اتصال موفق
    Serial.println();
    Serial.println("==================================================");
    Serial.println("✅ اتصال به وای‌فای با موفقیت برقرار شد!");
    Serial.print("📌 آی‌پی محلی برد: ");
    Serial.println(WiFi.localIP());
    Serial.print("📶 قدرت سیگنال (RSSI): ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");
    Serial.println("==================================================");
  } else {
    digitalWrite(STATUS_LED, LOW);
    Serial.println("\n❌ خطا در اتصال به وای‌فای! مجدداً تلاش خواهد شد...");
  }
}

// تابع ارسال هارت‌بیت و استعلام وضعیت رله‌ها از وب‌سرویس سرور
void checkServerStatus() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("⚠️ ارتباط وای‌فای قطع شده است. در حال اتصال مجدد...");
    connectToWiFi();
    return;
  }

  HTTPClient http;
  http.setTimeout(4000); // مهلت زمانی پاسخ حداکثر ۴ ثانیه

  // ساخت آدرس درخواست به همراه توکن و اطلاعات سیگنال
  int rssi = WiFi.RSSI();
  unsigned long uptime = millis() / 1000;
  
  String url = "http://" + String(SERVER_HOST) + ":" + String(SERVER_PORT) + 
               "/api/heartbeat?token=" + String(DEVICE_TOKEN) + 
               "&rssi=" + String(rssi) + 
               "&uptime=" + String(uptime);

  Serial.println();
  Serial.print("🌐 ارسال درخواست به سرور: ");
  Serial.println(url);

  http.begin(url);
  int httpCode = http.GET();

  if (httpCode == HTTP_CODE_OK) {
    String payload = http.getString();
    Serial.print("📥 پاسخ سرور: ");
    Serial.println(payload);

    // پارس سبک و سریع پاسخ بدون نیاز به کتابخانه اضافی
    // پاسخ سرور: {"status":"acknowledged","relay1":1,"relay2":0}
    int newR1 = -1;
    int newR2 = -1;

    if (payload.indexOf("\"relay1\":1") != -1 || payload.indexOf("\"relay1\": 1") != -1) {
      newR1 = 1;
    } else if (payload.indexOf("\"relay1\":0") != -1 || payload.indexOf("\"relay1\": 0") != -1) {
      newR1 = 0;
    }

    if (payload.indexOf("\"relay2\":1") != -1 || payload.indexOf("\"relay2\": 1") != -1) {
      newR2 = 1;
    } else if (payload.indexOf("\"relay2\":0") != -1 || payload.indexOf("\"relay2\": 0") != -1) {
      newR2 = 0;
    }

    // اعمال تغییرات به رله ۱ در صورت تغییر وضعیت
    if (newR1 != -1 && newR1 != currentRelay1State) {
      currentRelay1State = newR1;
      setRelay(RELAY1_PIN, currentRelay1State);
      Serial.print("💡 [رله ۱] وضعیت تغییر کرد به: ");
      Serial.println(currentRelay1State == 1 ? "روشن (ON) 🟢" : "خاموش (OFF) 🔴");
    }

    // اعمال تغییرات به رله ۲ در صورت تغییر وضعیت
    if (newR2 != -1 && newR2 != currentRelay2State) {
      currentRelay2State = newR2;
      setRelay(RELAY2_PIN, currentRelay2State);
      Serial.print("💡 [رله ۲] وضعیت تغییر کرد به: ");
      Serial.println(currentRelay2State == 1 ? "روشن (ON) 🟢" : "خاموش (OFF) 🔴");
    }

  } else {
    Serial.print("❌ خطا در برقراری ارتباط با وب‌سرویس! کد خطا: ");
    Serial.println(httpCode);
    if (httpCode < 0) {
      Serial.println("علت: سرور در دسترس نیست یا فایروال پورت ۸۰۸۰ را بسته است.");
    }
  }

  http.end();
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println();
  Serial.println("==================================================");
  Serial.println("⚡ پروژه کنترل رله هوشمند با ESP32 و بات تلگرام");
  Serial.println("📺 کانال یوتیوب: Elecnotech  |  کانال تلگرام: @IWnull");
  Serial.println("==================================================");

  // پیکربندی پین‌های رله و ال‌ای‌دی
  pinMode(RELAY1_PIN, OUTPUT);
  pinMode(RELAY2_PIN, OUTPUT);
  pinMode(STATUS_LED, OUTPUT);

  // خاموش نگه داشتن اولیه رله‌ها
  setRelay(RELAY1_PIN, 0);
  setRelay(RELAY2_PIN, 0);
  currentRelay1State = 0;
  currentRelay2State = 0;

  // شروع اتصال به وای‌فای
  connectToWiFi();
}

void loop() {
  // زمان‌بندی غیرمسدودکننده با تابع millis
  unsigned long currentMillis = millis();

  if (currentMillis - lastPollTime >= POLL_INTERVAL) {
    lastPollTime = currentMillis;
    checkServerStatus();
  }

  // بررسی زنده بودن وای‌فای در پس‌زمینه
  if (WiFi.status() != WL_CONNECTED) {
    digitalWrite(STATUS_LED, LOW);
  } else {
    digitalWrite(STATUS_LED, HIGH);
  }
}
