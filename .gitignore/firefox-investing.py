import time
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# 🔧 CONFIG
GECKODRIVER_PATH = r"C:\Users\pc\Desktop\rsi_bot\diger\geckodriver.exe"
FIREFOX_BINARY_PATH = r"C:\Program Files\Mozilla Firefox\firefox.exe"
INVESTING_SILVER_URL = "https://www.investing.com/commodities/silver"

# 🚀 Firefox Driver init
options = Options()
options.binary_location = FIREFOX_BINARY_PATH
options.add_argument("--headless")  # Tarayıcıyı arka planda açmak için
service = Service(GECKODRIVER_PATH)
driver = webdriver.Firefox(service=service, options=options)

try:
    # 🌐 Sayfayı aç
    driver.get(INVESTING_SILVER_URL)
    WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    print("Sayfa yüklendi ✅")

    # 💰 Fiyatı çek
    try:
        price_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//span[@data-test='instrument-price-last']"))
        )
        price = price_element.text
        print(f"Güncel Silver Spot Fiyatı: {price}")
    except:
        print("❌ Fiyat elementi bulunamadı.")

    # 📊 Tablo verilerini çek (örnek: detaylı veriler tablosu)
    try:
        table = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//table[contains(@class,'genTbl')]"))
        )
        rows = table.find_elements(By.XPATH, ".//tr")
        print("\n📄 Tablo verileri:")
        for row in rows:
            cells = row.find_elements(By.XPATH, ".//th | .//td")
            row_data = [cell.text for cell in cells]
            print(row_data)
    except:
        print("❌ Tablo bulunamadı veya yüklenmedi.")

finally:
    driver.quit()
    print
