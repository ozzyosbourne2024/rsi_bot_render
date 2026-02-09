import yfinance as yf
import pandas as pd
import requests
from datetime import datetime, timezone as tz
import os

# =====================
# TELEGRAM (Secrets + Direkt Token/Chat ID)
# =====================
LOCAL_TELEGRAM_TOKEN = "8541248285:AAFBU1zNp7wtdrM5tfUh1gsu8or4HiQ1NJc"
LOCAL_CHAT_ID = "1863652639"

# GitHub Actions secrets varsa kullan, yoksa local token
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", LOCAL_TELEGRAM_TOKEN)
CHAT_ID = os.getenv("CHAT_ID", LOCAL_CHAT_ID)

def send_telegram(message):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("❌ Telegram token veya chat ID eksik!")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        response = requests.post(url, data=payload)
        if response.status_code != 200:
            print("❌ Telegram gönderim hatası:", response.text)
    except Exception as e:
        print("❌ Telegram gönderim hatası:", e)

# =====================
# AYARLAR
# =====================
SYMBOLS = {
    "ALTIN": "GC=F",
    "GUMUS": "SI=F",
    "NDX": "^NDX"
}

RSI_PERIOD = 14
LAST_ALERT = {}

# =====================
# RSI HESAPLAMA (Wilder)
# =====================
def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# =====================
# VERİ ÇEKME
# =====================
def fetch(symbol):
    df_1h = yf.download(symbol, interval="1h", period="10d", progress=False)
    if df_1h.empty:
        return None

    close_1h = df_1h["Close"]
    rsi_1h = rsi(close_1h)

    df_4h = df_1h.resample("4h", label="right", closed="right").last()
    rsi_4h = rsi(df_4h["Close"])

    def safe_float(val):
        return val.item() if isinstance(val, pd.Series) else float(val)

    return {
        "price": safe_float(close_1h.iloc[-1]),
        "rsi_1h_closed": safe_float(rsi_1h.iloc[-2]),
        "rsi_1h_open": safe_float(rsi_1h.iloc[-1]),
        "rsi_4h_closed": safe_float(rsi_4h.iloc[-2]),
        "rsi_4h_open": safe_float(rsi_4h.iloc[-1]),
    }

# =====================
# ALARM KONTROL
# =====================
def check_alarm(name, rsi_val):
    prev = LAST_ALERT.get(name)

    if rsi_val < 30 and prev != "LOW":
        LAST_ALERT[name] = "LOW"
        return f"🔴 {name} RSI < 30 ({rsi_val:.2f})"
    if 45 < rsi_val <= 50 and prev != "MID":
        LAST_ALERT[name] = "MID"
        return f"🟠 {name} RSI 45–50 ({rsi_val:.2f})"
    if rsi_val > 50 and prev != "HIGH":
        LAST_ALERT[name] = "HIGH"
        return f"🟢 {name} RSI > 50 ({rsi_val:.2f})"
    return None

# =====================
# RAPOR
# =====================
def send_report():
    now = datetime.now(tz.utc).strftime("%H:%M UTC")
    text = f"📊 RSI RAPOR | {now}\n"

    for name, symbol in SYMBOLS.items():
        data = fetch(symbol)
        if not data:
            text += f"{name}: Veri alınamadı!\n"
            continue

        alarm = check_alarm(name, data["rsi_4h_closed"])

        text += f"""
{name}
Fiyat: {data['price']:.2f}

1H RSI
Kapalı: {data['rsi_1h_closed']:.2f}
Açık  : {data['rsi_1h_open']:.2f}

4H RSI
Kapalı: {data['rsi_4h_closed']:.2f}
Açık  : {data['rsi_4h_open']:.2f}
"""

        if alarm:
            text += f"\n🚨 ALARM: {alarm}\n"

    print(text)
    send_telegram(text)

# =====================
# Script doğrudan çalıştırıldığında rapor gönder
# =====================
if __name__ == "__main__":
    send_report()
