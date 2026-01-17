import requests
import json
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
DB_FILE = "products.json"

def send(msg):
    try:
        requests.post(f"{TG_API}/sendMessage", json={"chat_id": CHAT_ID, "text": msg})
    except:
        pass

def get_brand_from_page(driver, url):
    """Достаёт бренд со страницы товара"""
    try:
        driver.get(url)
        time.sleep(3)
        
        # Пробуем найти бренд по картинке
        try:
            brand_img = driver.find_element(By.CSS_SELECTOR, "img[data-brandlogo='true']")
            brand_name = brand_img.get_attribute("alt")
            if brand_name and brand_name.strip():
                return brand_name.strip()
        except:
            pass
        
        # Запасной вариант - ссылка на бренд
        try:
            brand_link = driver.find_element(By.CSS_SELECTOR, "a[href*='/brand/']")
            brand_img = brand_link.find_element(By.TAG_NAME, "img")
            brand_name = brand_img.get_attribute("alt")
            if brand_name and brand_name.strip():
                return brand_name.strip()
        except:
            pass
        
        return "Товар"
    except Exception as e:
        print(f"Ошибка парсинга бренда: {e}")
        return "Товар"

# Загружаем базу
with open(DB_FILE, "r", encoding="utf-8") as f:
    products = json.load(f)

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("user-agent=Mozilla/5.0")

try:
    send("🔄 Начинаю обновление брендов...")
    driver = webdriver.Chrome(options=chrome_options)
    
    total = len(products)
    updated = 0
    
    for i, (url, data) in enumerate(products.items(), 1):
        # Пропускаем если бренд уже есть и это не "Товар"
        if data.get("title") and data["title"] != "Товар":
            print(f"[{i}/{total}] Пропуск (бренд уже есть): {url}")
            continue
        
        print(f"[{i}/{total}] Обновляю бренд: {url}")
        brand_name = get_brand_from_page(driver, url)
        
        products[url]["title"] = brand_name
        updated += 1
        
        # Сохраняем после каждого обновления
        if updated % 10 == 0:
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(products, f, ensure_ascii=False, indent=2)
            print(f"  💾 Сохранено ({updated} обновлено)")
            send(f"📊 Обновлено {updated}/{total} брендов")
        
        time.sleep(1)  # Небольшая пауза между запросами
    
    driver.quit()
    
    # Финальное сохранение
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(products, f, ensure_ascii=False, indent=2)
    
    send(f"✅ Готово! Обновлено {updated} брендов из {total} товаров")
    print(f"\n✅ Обновление завершено: {updated} брендов")

except Exception as e:
    send(f"⚠️ Ошибка обновления брендов: {str(e)}")
    print(f"ERROR: {e}")
    try:
        driver.quit()
    except:
        pass
