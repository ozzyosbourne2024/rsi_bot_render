import yfinance as yf
import pandas as pd
import requests
from datetime import datetime, timezone as tz
import os

# =====================
# TELEGRAM
# =====================
TELEGRAM_TOKEN = "8541248285:AAFBU1zNp7wtdrM5tfUh1gsu8or4HiQ1NJc"
CHAT_ID = "1863652639"

def send_telegram(message):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("❌ Telegram token veya chat ID eksik!")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        r = requests.post(url, data=payload, timeout=10)
        if r.status_code != 200:
            print("❌ Telegram gönderim hatası:", r.text)
    except Exception as e:
        print("❌ Telegram gönderim hatası:", e)

# =====================
# AYARLAR
# =====================
SYMBOLS = {
    "ALTIN": "GC=F",
    "GUMUS_FUTURES": "SI=F",
    "GUMUS_SPOT": "XAGUSD=X",
    "NDX": "^NDX"
}

RSI_PERIOD = 14
LAST_ALERT = {}

# =====================
# RSI (Wilder – TradingView uyumlu)
# =====================
def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def to_float(x):
    return float(x.iloc[-1]) if isinstance(x, pd.Series) else float(x)

# =====================
# VERİ ÇEKME
# =====================
def fetch(symbol):
    try:
        # -------- SPOT GÜMÜŞ --------
        if symbol == "XAGUSD=X":
            df_30m = yf.download(symbol, interval="30m", period="10d", progress=False)
            if df_30m.empty:
                return None

            close_30m = df_30m["Close"]
            rsi_30m = rsi(close_30m)

            # 4H = 8 adet 30m mum
            close_4h = close_30m.resample("4H").last()
            rsi_4h = rsi(close_4h)

            return {
                "price": to_float(close_30m),
                "rsi_1h_closed": to_float(rsi_30m.iloc[-2]),
                "rsi_1h_open": to_float(rsi_30m.iloc[-1]),
                "rsi_4h_closed": to_float(rsi_4h.iloc[-2]),
                "rsi_4h_open": to_float(rsi_4h.iloc[-1]),
            }

        # -------- FUTURES / ENDEKS --------
        df_1h = yf.download(symbol, interval="1h", period="10d", progress=False)
        if df_1h.empty:
            return None

        close_1h = df_1h["Close"]
        rsi_1h = rsi(close_1h)

        close_4h = close_1h.resample("4H").last()
        rsi_4h = rsi(close_4h)

        return {
            "price": to_float(close_1h),
            "rsi_1h_closed": to_float(rsi_1h.iloc[-2]),
            "rsi_1h_open": to_float(rsi_1h.iloc[-1]),
            "rsi_4h_closed": to_float(rsi_4h.iloc[-2]),
            "rsi_4h_open": to_float(rsi_4h.iloc[-1]),
        }

    except Exception as e:
        print(f"❌ {symbol} hata:", e)
        return None

# =====================
# ALARM
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
            text += f"\n{name}: ❌ Veri alınamadı\n"
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
            text += f"\n🚨 {alarm}\n"

    print(text)
    send_telegram(text)

# =====================
# TEST
# =====================
def send_test_message():
    send_telegram("✅ RSI bot test mesajı")

# =====================
# MAIN
# =====================
if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        send_test_message()
    else:
        send_report()
