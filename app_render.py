import time
import yfinance as yf
import pandas as pd
import requests
from datetime import datetime
import schedule
from concurrent.futures import ThreadPoolExecutor

# ===================== TELEGRAM =====================
TELEGRAM_TOKEN = "8541248285:AAFBU1zNp7wtdrM5tfUh1gsu8or4HiQ1NJc"
CHAT_ID = "1863652639"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(url, data=payload, timeout=10)
        print("[INFO] Telegram gönderildi.")
    except Exception as e:
        print("[ERROR] Telegram gönderim hatası:", e)

# ===================== Semboller ve Hisseler =====================
SYMBOLS = {"ALTIN":"GC=F","GUMUS":"SI=F","NASDAQ100":"^NDX"}
STOCKS = {
    "BIST100":"XU100.IS","ASELSAN":"ASELS.IS","BIMAS":"BIMAS.IS","THYAO":"THYAO.IS",
    "TUPRS":"TUPRS.IS","KCHOL":"KCHOL.IS","MIGROS":"MGROS.IS","AKBANK":"AKBNK.IS",
    "GARANTI":"GARAN.IS","EMLAK_GYO":"EKGYO.IS","ZIRAAT_GYO":"ZRGYO.IS"
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
def safe_download(symbol, interval="1h", period="7d", retries=3):
    for i in range(retries):
        try:
            df = yf.download(symbol, interval=interval, period=period, progress=False, threads=False)
            if not df.empty:
                time.sleep(1)
                return df
        except Exception as e:
            print(f"[ERROR] {symbol} download hatası ({i+1}/{retries}): {e}")
        time.sleep(2)
    return None

# ===================== RSI paralel çekim =====================
def fetch_rsi_for(symbol_tuple):
    name, symbol = symbol_tuple
    for attempt in range(3):
        data = safe_download(symbol, interval="1h", period="7d")
        if data is None or data.empty:
            print(f"[WARN] {name} verisi boş, {attempt+1}. deneme...")
            time.sleep(2)
            continue

        close_1h = data["Close"]
        if isinstance(close_1h, pd.DataFrame):
            if isinstance(close_1h.columns, pd.MultiIndex):
                if symbol in close_1h.columns.get_level_values(0):
                    close_1h = close_1h[symbol]
                else:
                    close_1h = close_1h.iloc[:,0]
            close_1h = close_1h.astype(float)
        else:
            close_1h = close_1h.astype(float)

        try:
            price = round(float(close_1h.iloc[-1]), 2)
            print(f"[INFO] {name} fiyat alındı: {price}")

            df_4h = close_1h.resample("4h").last().ffill()
            rsi_1h = rsi(close_1h)
            rsi_4h = rsi(df_4h)

            def safe_val(series, idx):
                try:
                    return round(float(series.iloc[idx]), 2)
                except:
                    return None

            return (name, {
                "price": price,
                "rsi_1h_closed": safe_val(rsi_1h, -2),
                "rsi_1h_open": safe_val(rsi_1h, -1),
                "rsi_4h_closed": safe_val(rsi_4h, -2),
                "rsi_4h_open": safe_val(rsi_4h, -1)
            })
        except Exception as e:
            print(f"[ERROR] {name} RSI hesap hatası: {e}")
            time.sleep(1)
    return (name, None)

def fetch_all_rsi():
    results = {}
    with ThreadPoolExecutor(max_workers=2) as executor:
        for name, data in executor.map(fetch_rsi_for, SYMBOLS.items()):
            results[name] = data
    return results

# ===================== Hisse paralel çekim =====================
def fetch_stock_for(symbol_tuple):
    name, symbol = symbol_tuple
    data = safe_download(symbol, interval="1d", period="2d")
    if data is None or data.empty:
        return (name, (None,None))
    try:
        close = data["Close"]
        if isinstance(close, pd.DataFrame):
            close = close.iloc[:,0]
        last = round(float(close.iloc[-1]), 2)
        prev = round(float(close.iloc[-2]), 2)
        change = round((last-prev)/prev*100, 2)
        print(f"[INFO] {name} hisse verisi: {last}, değişim: {change}%")
        return (name, (last, change))
    except Exception as e:
        print(f"[ERROR] {name} hisse verisi hesap hatası: {e}")
        return (name, (None,None))

def fetch_all_stocks():
    results = {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        for name, data in executor.map(fetch_stock_for, STOCKS.items()):
            results[name] = data
    return results

# ===================== Güvenli sıralama =====================
def safe_change(val):
    if val is None:
        return -9999
    return float(val)

# ===================== Rapor oluşturma =====================
def send_report():
    now = datetime.now().strftime("%H:%M TR")
    text = f"📊 RSI RAPOR | {now}\n"

    rsi_data = fetch_all_rsi()
    for name in SYMBOLS.keys():
        data = rsi_data.get(name)
        if not data:
            text += f"\n{name}: Veri alınamadı!\n"
            continue
        text += f"""{name}
Fiyat: {data['price']:.2f}

1H RSI
Kapalı: {data['rsi_1h_closed']:.2f}
Açık  : {data['rsi_1h_open']:.2f}

4H RSI
Kapalı: {data['rsi_4h_closed']:.2f}
Açık  : {data['rsi_4h_open']:.2f}
"""

    text += "\n📈 HİSSE RAPORU (% DEĞİŞİM SIRALI)\n"
    stock_data = fetch_all_stocks()
    bist = stock_data.get("BIST100")
    others = [(k,v[0],v[1]) for k,v in stock_data.items() if k!="BIST100"]
    others.sort(key=lambda x: safe_change(x[2]), reverse=True)

    if bist:
        price, change = bist
        if price is not None:
            emoji = "🟢" if change>0 else "🔴"
            text += f"\n{emoji} BIST100\nFiyat: {price}\nDeğişim: {change}%\n"

    for name, price, change in others:
        if price is None:
            text += f"\n{name}: Veri alınamadı\n"
        else:
            emoji = "🟢" if change>0 else "🔴"
            text += f"\n{emoji} {name}\nFiyat: {price}\nDeğişim: {change}%\n"

    print("[INFO] Telegram gönderiliyor...")
    send_telegram(text)

# ===================== Tek seferlik bilgisayar testi =====================
if __name__ == "__main__":
    send_report()  # Bilgisayar testi için çalıştır
    # GitHub Actions kullanırken bu satırı sil veya schedule ile değiştir
