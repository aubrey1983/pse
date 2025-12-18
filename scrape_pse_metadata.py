import time
import json
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

METADATA_FILE = "data/stock_metadata.json"
PSE_DIRECTORY_URL = "https://edge.pse.com.ph/companyDirectory/form.do"

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.add_argument("--log-level=3") 
    chrome_options.add_argument("--window-size=1920,1080")
    
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
    return driver

def scrape_metadata():
    driver = get_driver()
    stock_metadata = {}
    
    print(f"Navigating to {PSE_DIRECTORY_URL}...")
    driver.get(PSE_DIRECTORY_URL)
    time.sleep(3)
    
    page_num = 1
    while True:
        print(f"Scraping page {page_num}...")
        
        try:
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "table#companyListTable")))
            
            # The table headers are typically: Company Name | Stock Symbol | Sector | Subsector | Listing Date
            # Let's verify columns by assuming standard layout or checking headers?
            # Standard PSE Edge Directory layout:
            # 1: Company Name
            # 2: Stock Symbol
            # 3: Sector
            # 4: Subsector
            # 5: Listing Date
            
            rows = driver.find_elements(By.CSS_SELECTOR, "table#companyListTable tbody tr")
            print(f"  Found {len(rows)} rows.")
            
            for row in rows:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) >= 5:
                    company_name = cols[0].text.strip()
                    symbol = cols[1].text.strip()
                    sector = cols[2].text.strip()
                    subsector = cols[3].text.strip()
                    listing_date = cols[4].text.strip()
                    
                    if symbol:
                        # Extract clean symbol from text (sometimes might be a link)
                        # But .text usually handles it well.
                        
                        stock_metadata[symbol] = {
                            "company_name": company_name,
                            "symbol": symbol,
                            "sector": sector,
                            "subsector": subsector,
                            "listing_date": listing_date
                        }
                        
        except Exception as e:
            print(f"Error scraping page {page_num}: {e}")
            import traceback
            traceback.print_exc()
        
        # Next Page logic
        try:
            next_link = driver.find_elements(By.LINK_TEXT, str(page_num + 1))
            
            if next_link:
                print(f"  Clicking page {page_num + 1}...")
                driver.execute_script("arguments[0].scrollIntoView(true);", next_link[0])
                time.sleep(0.5)
                # Ensure click is robust
                driver.execute_script("arguments[0].click();", next_link[0])
                time.sleep(3)
                page_num += 1
            else:
                print("No next page link found.")
                break
        except Exception as e:
            print(f"Pagination error: {e}")
            break
            
    driver.quit()
    
    sorted_symbols = sorted(stock_metadata.keys())
    print(f"Scraped metadata for {len(sorted_symbols)} symbols.")
    
    # Save to file
    with open(METADATA_FILE, 'w') as f:
        json.dump(stock_metadata, f, indent=4)
        
    return stock_metadata

if __name__ == "__main__":
    scrape_metadata()
