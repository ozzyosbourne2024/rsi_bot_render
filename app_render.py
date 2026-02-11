import yfinance as yf
import pandas as pd
import requests
from datetime import datetime
import time  # test gecikmesi için

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
# RSI TOPLU ÇEKİM
# =====================
def fetch_all_rsi():
    tickers = list(SYMBOLS.values())
    df = yf.download(
        tickers,
        interval="1h",
        period="7d",
        group_by="ticker",
        progress=False,
        threads=False
    )
    results = {}
    for name, symbol in SYMBOLS.items():
        try:
            data = df[symbol].dropna()
            close_1h = data["Close"]
            rsi_1h = rsi(close_1h)
            df_4h = data.resample("4h").last()
            rsi_4h = rsi(df_4h["Close"])
            results[name] = {
                "price": float(close_1h.iloc[-1]),
                "rsi_1h_closed": float(rsi_1h.iloc[-2]),
                "rsi_1h_open": float(rsi_1h.iloc[-1]),
                "rsi_4h_closed": float(rsi_4h.iloc[-2]),
                "rsi_4h_open": float(rsi_4h.iloc[-1]),
            }
        except:
            results[name] = None
    return results

# =====================
# HİSSE TOPLU ÇEKİM
# =====================
def fetch_all_stocks():
    tickers = list(STOCKS.values())
    df = yf.download(
        tickers,
        period="2d",
        interval="1d",
        group_by="ticker",
        progress=False,
        threads=False
    )
    results = {}
    for name, symbol in STOCKS.items():
        try:
            data = df[symbol].dropna()
            last = data["Close"].iloc[-1]
            prev = data["Close"].iloc[-2]
            change = ((last - prev) / prev) * 100
            results[name] = (round(last, 2), round(change, 2))
        except:
            results[name] = (None, None)
    return results

# =====================
# ZAMAN KONTROLÜ
# =====================
def should_send_report():
    now = datetime.now()
    hour = now.hour
    minute = now.minute
    weekday = now.weekday()  # 0=Mon, 6=Sun

    # Hafta içi (Pzt-Cum)
    if weekday < 5:
        if (hour == 6 and minute == 0) or \
           (8 <= hour <= 17 and minute == 0) or \
           (hour == 18 and minute == 30) or \
           (hour == 21 and minute == 0):
            return True

    # Hafta sonu (Cmt-Paz)
    else:
        if (hour == 6 and minute == 0) or \
           (hour == 18 and minute == 30) or \
           (hour == 21 and minute == 0):
            return True

    return False

# =====================
# RAPOR GÖNDERME
# =====================
def send_report():
    now = datetime.now().strftime("%H:%M TR")
    text = f"📊 RSI RAPOR | {now}\n"

    # RSI
    rsi_data = fetch_all_rsi()
    for name in SYMBOLS.keys():
        data = rsi_data.get(name)
        if not data:
            text += f"\n{name}: Veri alınamadı!\n"
            continue
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

    # Hisseler
    text += "\n📈 HİSSE RAPORU (% DEĞİŞİM SIRALI)\n"
    stock_data = fetch_all_stocks()
    bist = stock_data.get("BIST100")
    others = [(k, v[0], v[1]) for k, v in stock_data.items() if k != "BIST100"]
    others.sort(key=lambda x: (x[2] is not None, x[2]), reverse=True)

    if bist:
        price, change = bist
        if price is not None:
            emoji = "🟢" if change > 0 else "🔴"
            text += f"\n{emoji} BIST100\nFiyat: {price}\nDeğişim: {change}%\n"

    for name, price, change in others:
        if price is None:
            text += f"\n{name}: Veri alınamadı\n"
        else:
            emoji = "🟢" if change > 0 else "🔴"
            text += f"\n{emoji} {name}\nFiyat: {price}\nDeğişim: {change}%\n"

    print(text)
    send_telegram(text)

# =====================
# ANA ÇALIŞMA
# =====================
TEST_MODE = False  # True: hemen rapor / False: sadece zamanlama geçerli

if __name__ == "__main__":
    if TEST_MODE:
        print("⚡ TEST MODU: 1 dakika sonra test raporu gönderilecek...")
        time.sleep(60)
        send_report()
    elif should_send_report():
        send_report()
    else:
        print("Şu an zamanlama dışında, rapor gönderilmiyor.")
