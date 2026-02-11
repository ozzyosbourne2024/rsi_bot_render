import time
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

GECKODRIVER_PATH = r"C:\Users\pc\Desktop\rsi_bot\diger\geckodriver.exe"
FIREFOX_BINARY_PATH = r"C:\Program Files\Mozilla Firefox\firefox.exe"
URL = "https://www.investing.com/commodities/silver"

options = Options()
options.binary_location = FIREFOX_BINARY_PATH
options.add_argument("--headless")  # başlıksız mod
service = Service(GECKODRIVER_PATH)
driver = webdriver.Firefox(service=service, options=options)

try:
    print("Sayfa yükleniyor...")
    driver.get(URL)
    WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    print("Sayfa yüklendi ✅")

    # iframe var mı kontrol et
    iframes = driver.find_elements(By.TAG_NAME, "iframe")
    print(f"{len(iframes)} iframe bulundu")
    for frame in iframes:
        driver.switch_to.default_content()
        driver.switch_to.frame(frame)
        if "RSI" in driver.page_source:
            print("✅ RSI iframe bulundu")
            break
    driver.switch_to.default_content()  # iframe'den çık

    # tabloyu bekle ve satırları tara
    table = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "table.technicalsTbl"))
    )

    rsi_1h = rsi_4h = None
    rows = table.find_elements(By.TAG_NAME, "tr")
    for row in rows:
        try:
            th = row.find_element(By.TAG_NAME, "th")
            if "RSI" in th.text:
                tds = row.find_elements(By.TAG_NAME, "td")
                rsi_1h = tds[0].text
                rsi_4h = tds[1].text
                break
        except:
            continue

    print("\n📊 RSI Sonuçları:")
    print(f"1H RSI: {rsi_1h}")
    print(f"4H RSI: {rsi_4h}")

except Exception as e:
    print(f"❌ Hata oluştu: {e}")

finally:
    driver.quit()
    print("Tarayıcı kapatıldı.")
