import yfinance as yf
import pandas as pd
import requests
from datetime import datetime
import pytz  # TR saat için

# =====================
# TELEGRAM
# =====================
TELEGRAM_TOKEN = "8541248285:AAFBU1zNp7wtdrM5tfUh1gsu8or4HiQ1NJc"
CHAT_ID = "1863652639"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": CHAT_ID, "text": message}, timeout=10)
    except Exception as e:
        print("Telegram gönderim hatası:", e)

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
# RAPOR
# =====================
def send_report():
    tz = pytz.timezone("Europe/Istanbul")
    now = datetime.now(tz).strftime("%H:%M TR")  # TR saatine göre
    text = f"📊 RSI RAPOR | {now}\n"

    # 1H ve 4H RSI
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
            close_1h = data["Close"]
            rsi_1h = rsi(close_1h)
            df_4h = data.resample("4h").last()
            rsi_4h = rsi(df_4h["Close"])
            price = close_1h.iloc[-1]

            text += f"\n{name}\nFiyat: {price:.2f}\n"
            text += f"RSI 1H: {rsi_1h.iloc[-1]:.2f}\n"
            text += f"RSI 4H: {rsi_4h.iloc[-1]:.2f}\n"
        except:
            text += f"\n{name}: Veri alınamadı\n"

    # Hisse raporu
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
