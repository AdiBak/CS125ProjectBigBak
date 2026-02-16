import sqlite3
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIGURATION ---
DB_NAME = "bigbak.db"
MAX_ITEMS_PER_CAT = 50  # UPDATED: Set to 50 (or 100+) to crawl more
DELAY_BETWEEN_CATS = 5
DELAY_BETWEEN_PAGES = 4

CATEGORIES_TO_SCRAPE = [
    {"name": "Food", "url": "https://www.traderjoes.com/home/products/category/food-8"},
    {
        "name": "Beverages",
        "url": "https://www.traderjoes.com/home/products/category/beverages-182",
    },
    {
        "name": "Cheese",
        "url": "https://www.traderjoes.com/home/products/category/cheese-29",
    },
    {
        "name": "Fresh Prepared",
        "url": "https://www.traderjoes.com/home/products/category/fresh-prepared-foods-80",
    },
    {
        "name": "Snacks",
        "url": "https://www.traderjoes.com/home/products/category/snacks-sweets-81",
    },
]


# --- 1. DATABASE SETUP ---
def setup_database():
    print(f">>> Creating/Connecting to {DB_NAME}...")
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            price TEXT,
            category TEXT,
            url TEXT,
            image_url TEXT,
            scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    return conn


# --- 2. THE SCRAPER ---
def scrape_category_products(driver, category_name, category_url):
    print(f"\n>>> VISITING: {category_name}")
    print(f"    URL: {category_url}")
    driver.get(category_url)

    # Wait for the dynamic content to load
    time.sleep(5)

    products_found = []
    scraped_urls = set()  # Keep track to avoid duplicates
    page_num = 1

    # --- PAGINATION LOOP ---
    while len(products_found) < MAX_ITEMS_PER_CAT:
        print(f"    [Page {page_num}] Scanning items...")

        try:
            # 1. FIND CARDS on current page
            cards = driver.find_elements(
                By.CSS_SELECTOR, "section[class*='ProductCard_card']"
            )

            items_on_page_count = 0

            for card in cards:
                # Stop if we hit the limit mid-page
                if len(products_found) >= MAX_ITEMS_PER_CAT:
                    break

                try:
                    # 2. EXTRACT TITLE
                    try:
                        title_element = card.find_element(By.CSS_SELECTOR, "h2 a")
                        name = title_element.text.strip()
                        item_url = title_element.get_attribute("href")
                    except:
                        continue

                    # DUPLICATE CHECK
                    if item_url in scraped_urls:
                        continue

                    # 3. EXTRACT PRICE
                    try:
                        price_element = card.find_element(
                            By.CSS_SELECTOR,
                            "span[class*='ProductPrice_productPrice__price']",
                        )
                        price = price_element.text.strip()
                    except:
                        price = "N/A"

                    # 4. EXTRACT IMAGE
                    try:
                        img_element = card.find_element(By.TAG_NAME, "img")
                        image_url = img_element.get_attribute("src")
                    except:
                        image_url = ""

                    # 5. SAVE
                    if name:
                        p_data = (name, price, category_name, item_url, image_url)
                        products_found.append(p_data)
                        scraped_urls.add(item_url)
                        items_on_page_count += 1
                        print(f"      + Scraped: {name} ({price})")

                except Exception:
                    continue

            print(f"    -> Found {items_on_page_count} new items on Page {page_num}.")

            # CHECK IF WE ARE DONE BEFORE CLICKING NEXT
            if len(products_found) >= MAX_ITEMS_PER_CAT:
                print("    Target limit reached!")
                break

            # 6. CLICK NEXT PAGE
            try:
                # Look for button with aria-label="Next page..."
                next_button = driver.find_element(
                    By.CSS_SELECTOR, "button[aria-label*='Next page']"
                )

                # Check if it's disabled (end of list)
                if not next_button.is_enabled():
                    print("    End of category (Next button disabled).")
                    break

                # Scroll to it to ensure it's clickable
                driver.execute_script("arguments[0].scrollIntoView();", next_button)
                time.sleep(1)  # Small pause for scroll

                next_button.click()
                print("    >>> Clicking Next Page...")

                # Wait for new items to load
                time.sleep(4 + DELAY_BETWEEN_PAGES)
                page_num += 1

            except Exception:
                print("    No 'Next Page' button found (End of Category).")
                break

        except Exception as e:
            print(f"    CRITICAL ERROR ON PAGE: {e}")
            break

    return products_found


# --- 3. MAIN LOOP ---
def main():
    conn = setup_database()
    cursor = conn.cursor()

    options = Options()
    # options.add_argument("--headless") # Optional: run without window
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), options=options
    )

    try:
        total_saved = 0

        for cat in CATEGORIES_TO_SCRAPE:
            items = scrape_category_products(driver, cat["name"], cat["url"])

            if items:
                cursor.executemany(
                    """
                    INSERT INTO products (name, price, category, url, image_url)
                    VALUES (?, ?, ?, ?, ?)
                """,
                    items,
                )
                conn.commit()
                print(f"    -> Committed {len(items)} items to DB.")
                total_saved += len(items)

            time.sleep(DELAY_BETWEEN_CATS)

        print("\n" + "=" * 40)
        print(f"DONE! Total products saved: {total_saved}")
        print(f"Data stored in file: {DB_NAME}")
        print("=" * 40)

    finally:
        driver.quit()
        conn.close()


if __name__ == "__main__":
    main()
