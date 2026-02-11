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
# RSI TAKİP EDİLENLER
# =====================
SYMBOLS = {
    "ALTIN": "GC=F",
    "GUMUS": "SI=F",
    "NASDAQ100": "^NDX"
}

# =====================
# HİSSE TAKİP
# =====================
STOCKS = {
   "BIST100": "XU100.IS",
    "ASELSAN": "ASELS.IS",
    "BIMAS": "BIMAS.IS",
    "THYAO": "THYAO.IS",
    "TUPRS": "TUPRS.IS",
    "KCHOL": "KCHOL.IS",
    "MIGROS": "MGROS.IS",
    "AKBANK": "AKBNK.IS",
    "GARANTI": "GARAN.IS",
    "EMLAK_GYO": "EKGYO.IS",
    "ZIRAAT_GYO": "ZRGYO.IS"
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
# RSI VERİ ÇEKME
# =====================
def fetch(symbol, retries=3, wait=5):
    for attempt in range(retries):
        try:
            df_1h = yf.download(symbol, interval="1h", period="7d", progress=False)

            if df_1h.empty:
                time.sleep(wait)
                continue

            close_1h = df_1h["Close"]
            rsi_1h = rsi(close_1h)

            df_4h = df_1h.resample("4h", label="right", closed="right").last()
            rsi_4h = rsi(df_4h["Close"])

            price = float(close_1h.values[-1].item())

            return {
                "price": price,
                "rsi_1h_closed": float(rsi_1h.values[-2]),
                "rsi_1h_open": float(rsi_1h.values[-1]),
                "rsi_4h_closed": float(rsi_4h.values[-2]),
                "rsi_4h_open": float(rsi_4h.values[-1]),
            }

        except Exception as e:
            time.sleep(wait)

    return None

# =====================
# HİSSE VERİ ÇEKME (HAFİF)
# =====================
def fetch_stock(symbol):
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.fast_info

        last_price = data.get("lastPrice")
        previous_close = data.get("previousClose")

        if last_price and previous_close:
            change_pct = ((last_price - previous_close) / previous_close) * 100
            return round(last_price, 2), round(change_pct, 2)

    except Exception as e:
        print(symbol, "hisse hatası:", e)

    return None, None

# =====================
# RAPOR
# =====================
def send_report():
    now = datetime.now().strftime("%H:%M TR")
    text = f"📊 RSI RAPOR | {now}\n"

    # -------- RSI KISMI --------
    for name, symbol in SYMBOLS.items():
        data = fetch(symbol)

        if not data:
            text += f"{name}: Veri alınamadı!\n"
        else:
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

        time.sleep(3)

    # -------- HİSSE KISMI --------
    text += "\n📈 HİSSE RAPORU\n"

     # -------- HİSSE KISMI --------
    text += "\n📈 HİSSE RAPORU (% DEĞİŞİM SIRALI)\n"

    bist_data = None
    other_stocks = []

    # verileri çek
    for name, symbol in STOCKS.items():
        price, change = fetch_stock(symbol)
        time.sleep(3)

        if name == "BIST100":
            bist_data = (name, price, change)
        else:
            other_stocks.append((name, price, change))

    # diğer hisseleri değişime göre sırala (büyükten küçüğe)
    other_stocks.sort(
        key=lambda x: (x[2] is not None, x[2]),
        reverse=True
    )

    # 1️⃣ BIST100 en üstte
    if bist_data:
        name, price, change = bist_data
        if price is None:
            text += f"\n{name}: Veri alınamadı\n"
        else:
            emoji = "🟢" if change > 0 else "🔴"
            text += f"""
{emoji} {name}
Fiyat: {price}
Değişim: {change}%
"""

    # 2️⃣ Diğer hisseler sıralı
    for name, price, change in other_stocks:
        if price is None:
            text += f"\n{name}: Veri alınamadı\n"
        else:
            emoji = "🟢" if change > 0 else "🔴"
            text += f"""
{emoji} {name}
Fiyat: {price}
Değişim: {change}%
"""


    print(text)
    send_telegram(text)

# =====================
# ÇALIŞTIR
# =====================
if __name__ == "__main__":
    send_report()
