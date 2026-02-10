import time
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime, timezone

# =====================
# TELEGRAM
# =====================
TELEGRAM_TOKEN = "8541248285:AAFBU1zNp7wtdrM5tfUh1gsu8or4HiQ1NJc"
CHAT_ID = "1863652639"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print("Telegram gönderim hatası:", e)

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
# RSI HESAPLAMA
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
# VERİ ÇEKME (GitHub için tek seferlik)
# =====================
def fetch(symbol, retries=2, wait=2):
    for attempt in range(retries):
        try:
            df_1h = yf.download(symbol, interval="1h", period="10d", progress=False)
            if df_1h.empty:
                print(f"{symbol}: Veri alınamadı, {attempt+1}. deneme...")
                time.sleep(wait)
                continue

            close_1h = df_1h["Close"]
            rsi_1h = rsi(close_1h)

            df_4h = df_1h.resample("4h", label="right", closed="right").last()
            rsi_4h = rsi(df_4h["Close"])

            price = float(close_1h.values[-1]) if not pd.isna(close_1h.values[-1]) else 0.0
            rsi_1h_closed = float(rsi_1h.values[-2]) if len(rsi_1h) >= 2 and not pd.isna(rsi_1h.values[-2]) else 0.0
            rsi_1h_open = float(rsi_1h.values[-1]) if not pd.isna(rsi_1h.values[-1]) else 0.0
            rsi_4h_closed = float(rsi_4h.values[-2]) if len(rsi_4h) >= 2 and not pd.isna(rsi_4h.values[-2]) else 0.0
            rsi_4h_open = float(rsi_4h.values[-1]) if not pd.isna(rsi_4h.values[-1]) else 0.0

            return {
                "price": price,
                "rsi_1h_closed": rsi_1h_closed,
                "rsi_1h_open": rsi_1h_open,
                "rsi_4h_closed": rsi_4h_closed,
                "rsi_4h_open": rsi_4h_open,
            }
        except Exception as e:
            print(f"{symbol} veri çekme hatası: {e}, {attempt+1}. deneme")
            time.sleep(wait)
    return None

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
    now = datetime.now(timezone.utc).strftime("%H:%M UTC")
    text = f"📊 RSI RAPOR | {now}\n"

    for name, symbol in SYMBOLS.items():
        data = fetch(symbol, retries=2, wait=2)
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
# GitHub Actions için tek seferlik çalıştır
# =====================
if __name__ == "__main__":
    send_report()
