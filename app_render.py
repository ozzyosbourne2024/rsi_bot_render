import time
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime

# ===================== TELEGRAM =====================
TELEGRAM_TOKEN = "8541248285:AAFBU1zNp7wtdrM5tfUh1gsu8or4HiQ1NJc"
CHAT_ID = "1863652639"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print("Telegram error:", e)

# ===================== Semboller ve Hisseler =====================
SYMBOLS = {"ALTIN":"GC=F","GUMUS":"SI=F","NASDAQ100":"^NDX"}
STOCKS = {
    "BIST100":"XU100.IS","ASELSAN":"ASELS.IS","BIMAS":"BIMAS.IS","THYAO":"THYAO.IS",
    "TUPRS":"TUPRS.IS","KCHOL":"KCHOL.IS","MIGROS":"MGROS.IS","AKBANK":"AKBNK.IS",
    "EMLAK_GYO":"EKGYO.IS","ZIRAAT_GYO":"ZRGYO.IS","Turk Altin":"TRALT.IS",
    "PEGASSUS":"PGSUS.IS","VAKIFBANK":"VAKBN.IS","SISECAM":"SISE.IS","CVK MADEN":"CVKMD.IS"
}

# ===================== RSI Hesaplama =====================
def rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# ===================== Safe download =====================
def safe_download(symbol, interval="1h", period="7d", retries=5):
    for _ in range(retries):
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(interval=interval, period=period)
            if not df.empty:
                time.sleep(1)
                return df
        except:
            pass
        time.sleep(2)
    return None

# ===================== RSI çekim =====================
def fetch_rsi_for(symbol_tuple):
    name, symbol = symbol_tuple
    for _ in range(5):
        data = safe_download(symbol, interval="1h", period="7d")
        if data is None or data.empty:
            continue

        close_1h = pd.to_numeric(data["Close"], errors='coerce').dropna()
        if close_1h.empty:
            continue

        try:
            price = round(float(close_1h.iloc[-1]), 2)

            df_4h = close_1h.resample("4h").last().ffill()
            rsi_1h = rsi(close_1h)
            rsi_4h = rsi(df_4h)

            def safe_val(series, idx):
                return round(float(series.iloc[idx]), 2) if len(series) > abs(idx) else None

            return (name, {
                "price": price,
                "rsi_1h_closed": safe_val(rsi_1h, -2),
                "rsi_1h_open": safe_val(rsi_1h, -1),
                "rsi_4h_closed": safe_val(rsi_4h, -2),
                "rsi_4h_open": safe_val(rsi_4h, -1)
            })
        except:
            time.sleep(1)
    return (name, None)

def fetch_all_rsi():
    results = {}
    for symbol_tuple in SYMBOLS.items():
        name, data = fetch_rsi_for(symbol_tuple)
        results[name] = data
    return results

# ===================== Hisse çekim =====================
def fetch_stock_for(symbol_tuple):
    name, symbol = symbol_tuple
    for _ in range(5):
        data = safe_download(symbol, interval="1d", period="7d")
        if data is None or data.empty:
            continue

        close = pd.to_numeric(data["Close"], errors='coerce').dropna()
        if len(close) < 2:
            continue

        try:
            last = round(float(close.iloc[-1]), 2)
            prev = round(float(close.iloc[-2]), 2)
            change = round((last-prev)/prev*100, 2)
            return (name, (last, change))
        except:
            time.sleep(1)
    return (name, (None,None))

def fetch_all_stocks():
    results = {}
    for symbol_tuple in STOCKS.items():
        name, data = fetch_stock_for(symbol_tuple)
        results[name] = data
    return results

def safe_change(val):
    return float(val) if val is not None else -9999

# ===================== Spot Prices =====================
def get_spot_prices():
    headers = {"User-Agent": "Mozilla/5.0"}

    silver_spot = None
    gold_spot = None

    try:
        r = requests.get("https://api.gold-api.com/price/XAG", headers=headers, timeout=5)
        if r.status_code == 200:
            silver_spot = r.json().get("price")
    except:
        pass

    try:
        r = requests.get("https://api.gold-api.com/price/XAU", headers=headers, timeout=5)
        if r.status_code == 200:
            gold_spot = r.json().get("price")
    except:
        pass

    return silver_spot, gold_spot

# ===================== Rapor =====================
def send_report():
    now = datetime.now().strftime("%H:%M TR")
    text = f"📊 RSI RAPOR | {now}\n"

    rsi_data = fetch_all_rsi()
    silver_spot, gold_spot = get_spot_prices()

    for name in SYMBOLS.keys():
        data = rsi_data.get(name)

        if not data:
            text += f"\n{name}: Veri alınamadı!\n"
            continue

        if name == "GUMUS" and silver_spot:
            price_line = f"{data['price']:.2f} / {silver_spot:.2f}"
        elif name == "ALTIN" and gold_spot:
            price_line = f"{data['price']:.2f} / {gold_spot:.2f}"
        else:
            price_line = f"{data['price']:.2f}"

        text += f"""
{name}
Fiyat: {price_line}

1H RSI
Kapalı: {data['rsi_1h_closed'] if data['rsi_1h_closed'] is not None else 'NA'}
Açık  : {data['rsi_1h_open'] if data['rsi_1h_open'] is not None else 'NA'}

4H RSI
Kapalı: {data['rsi_4h_closed'] if data['rsi_4h_closed'] is not None else 'NA'}
Açık  : {data['rsi_4h_open'] if data['rsi_4h_open'] is not None else 'NA'}
"""

    text += "\n📈 HİSSE RAPORU (% DEĞİŞİM SIRALI)\n"

    stock_data = fetch_all_stocks()
    bist = stock_data.get("BIST100")
    others = [(k, v[0], v[1]) for k, v in stock_data.items() if k != "BIST100"]
    others.sort(key=lambda x: safe_change(x[2]), reverse=True)

    if bist and bist[0] is not None:
        price, change = bist
        emoji = "🟢" if change > 0 else "🔴"
        text += f"\n{emoji} BIST100\nFiyat: {price}\nDeğişim: {change}%\n"

    for name, price, change in others:
        if price is None:
            text += f"\n{name}: Veri alınamadı\n"
        else:
            emoji = "🟢" if change > 0 else "🔴"
            text += f"\n{emoji} {name}\nFiyat: {price}\nDeğişim: {change}%\n"

    send_telegram(text)

if __name__ == "__main__":
    send_report()
