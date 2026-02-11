import yfinance as yf
import pandas as pd
import requests
from datetime import datetime

# =====================
# TELEGRAM
# =====================
TELEGRAM_TOKEN = "TOKEN_BURAYA"
CHAT_ID = "CHAT_ID_BURAYA"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    requests.post(url, data=payload, timeout=10)

# =====================
# TAKİP
# =====================
SYMBOLS = {
    "ALTIN": "GC=F",
    "GUMUS": "SI=F",
    "NASDAQ100": "^NDX"
}

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

def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def send_report():
    now = datetime.now().strftime("%H:%M TR")
    text = f"📊 RSI RAPOR | {now}\n"

    df = yf.download(
        list(SYMBOLS.values()),
        interval="1h",
        period="7d",
        group_by="ticker",
        progress=False,
        threads=False
    )

    for name, symbol in SYMBOLS.items():
        try:
            data = df[symbol].dropna()
            close = data["Close"]
            rsi_val = rsi(close)
            price = close.iloc[-1]
            text += f"\n{name}\nFiyat: {price:.2f}\nRSI(1H): {rsi_val.iloc[-1]:.2f}\n"
        except:
            text += f"\n{name}: Veri alınamadı\n"

    text += "\n📈 HİSSE RAPORU\n"

    df2 = yf.download(
        list(STOCKS.values()),
        period="2d",
        interval="1d",
        group_by="ticker",
        progress=False,
        threads=False
    )

    for name, symbol in STOCKS.items():
        try:
            data = df2[symbol].dropna()
            last = data["Close"].iloc[-1]
            prev = data["Close"].iloc[-2]
            change = ((last - prev) / prev) * 100
            emoji = "🟢" if change > 0 else "🔴"
            text += f"\n{emoji} {name}\nFiyat: {last:.2f}\nDeğişim: {change:.2f}%\n"
        except:
            text += f"\n{name}: Veri alınamadı\n"

    print(text)
    send_telegram(text)

if __name__ == "__main__":
    send_report()
