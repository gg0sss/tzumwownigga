import requests
import json
import os
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
DB_FILE = "products.json"

# Категории для отслеживания
CATEGORIES = [
    # Женские сумки
    "https://collect.tsum.ru/women/catalog/povsednevnye-sumki-82",
    "https://collect.tsum.ru/women/catalog/riukzaki-i-poiasnye-sumki-87",
    "https://collect.tsum.ru/women/catalog/dorozhnye-i-sportivnye-sumki-93",
    "https://collect.tsum.ru/women/catalog/klatchi-i-vechernie-sumki-90",
    # Мужские сумки
    "https://collect.tsum.ru/men/catalog/riukzaki-i-poiasnye-sumki-246",
    "https://collect.tsum.ru/men/catalog/povsednevnye-sumki-238",
    "https://collect.tsum.ru/men/catalog/dorozhnye-i-sportivnye-sumki-249"
]

def send(msg):
    """Отправить сообщение в Telegram"""
    try:
        requests.post(
            f"{TG_API}/sendMessage",
            json={"chat_id": CHAT_ID, "text": msg}
        )
    except Exception as e:
        print(f"Ошибка отправки: {e}")

def check_product_page(driver, url):
    """Проверить страницу товара - продан или в резерве"""
    try:
        driver.get(url)
        time.sleep(3)
        
        page_text = driver.page_source.lower()
        
        # Проверяем статус
        if "нет в наличии" in page_text:
            return "sold"  # Продано
        elif "в резерве" in page_text:
            return "reserved"  # В резерве
        else:
            return "available"  # В наличии
    except Exception as e:
        print(f"Ошибка проверки {url}: {e}")
        return "unknown"

# Загружаем старую базу
if os.path.exists(DB_FILE):
    with open(DB_FILE, "r", encoding="utf-8") as f:
        old_products = json.load(f)
else:
    old_products = {}

new_products = {}

# Настройка Chrome
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")

try:
    send("🤖 Начинаю проверку...")
    
    driver = webdriver.Chrome(options=chrome_options)
    
    # Парсим категории
    for category_url in CATEGORIES:
        print(f"\nПарсинг: {category_url}")
        driver.get(category_url)
        
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a[href*='/item/ITEM']"))
        )
        
        # Кликаем "Показать больше" до конца
        attempts = 0
        max_attempts = 200
        
        while attempts < max_attempts:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            try:
                button = driver.find_element(By.XPATH, "//p[contains(text(), 'Показать больше товаров')]")
                driver.execute_script("arguments[0].click();", button)
                time.sleep(3)
            except:
                break
            
            attempts += 1
        
        # Собираем все карточки
        cards = driver.find_elements(By.CSS_SELECTOR, "a[href*='/item/ITEM']")
        print(f"  Найдено товаров: {len(cards)}")
        
        for card in cards:
            try:
                url = card.get_attribute("href")
                
                if url in new_products:
                    continue
                
                # Достаём бренд
                try:
                    brand_img = card.find_element(By.CSS_SELECTOR, "img[data-brandlogo='true']")
                    brand_name = brand_img.get_attribute("alt")
                except:
                    brand_name = "Товар"
                
                new_products[url] = {
                    "title": brand_name,
                    "in_stock": True  # Если товар в списке - он доступен
                }
            
            except Exception as e:
                print(f"  Ошибка обработки карточки: {e}")
                continue
    
    print(f"\n✅ Всего товаров в каталогах: {len(new_products)}")
    
    # Проверяем какие товары пропали
    sold_count = 0
    for old_url, old_data in old_products.items():
        if old_data["in_stock"] and old_url not in new_products:
            # Товар пропал из списка - проверяем его страницу
            print(f"\n🔍 Проверяю: {old_url}")
            status = check_product_page(driver, old_url)
            
            if status == "sold":
                # РЕАЛЬНО ПРОДАН!
                send(f"❌ ПРОДАНО\n\n{old_data['title']}\n\n{old_url}")
                sold_count += 1
                print(f"  ✅ ПРОДАНО: {old_data['title']}")
            elif status == "reserved":
                print(f"  ⏳ В резерве (пропускаем)")
            else:
                print(f"  ❓ Статус неизвестен")
    
    driver.quit()
    
    # Сохраняем новую базу
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(new_products, f, ensure_ascii=False, indent=2)
    
    send(f"✅ Проверка завершена\n\nОтслеживается: {len(new_products)} товаров\nПродано: {sold_count}")

except Exception as e:
    send(f"⚠️ Ошибка:\n{str(e)}")
    print(f"ERROR: {e}")
    try:
        driver.quit()
    except:
        pass
