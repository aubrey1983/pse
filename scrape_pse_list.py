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

OFFICIAL_LIST_FILE = "data/official_pse_list.json"
PSE_DIRECTORY_URL = "https://edge.pse.com.ph/companyDirectory/form.do"

def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new") 
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    chrome_options.add_argument("--log-level=3") 
    
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=chrome_options)
    return driver

def scrape_official_symbols():
    driver = get_driver()
    stock_ids = {}
    
    print(f"Navigating to {PSE_DIRECTORY_URL}...")
    driver.get(PSE_DIRECTORY_URL)
    time.sleep(3)
    
    import re
    
    page_num = 1
    while True:
        print(f"Scraping page {page_num}...")
        
        try:
            # Wait for table
            WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CSS_SELECTOR, "table#companyListTable")))
            
            rows = driver.find_elements(By.CSS_SELECTOR, "table#companyListTable tbody tr")
            print(f"  Found {len(rows)} rows.")
            
            for row in rows:
                cols = row.find_elements(By.TAG_NAME, "td")
                if len(cols) >= 2:
                    # Try to get text from the link inside
                    try:
                        link = cols[1].find_element(By.TAG_NAME, "a")
                        symbol_text = link.text.strip()
                        onclick_text = link.get_attribute("onclick")
                        
                        # Parse onclick="companyInfo('123', '456');"
                        if onclick_text:
                            match = re.search(r"companyInfo\('(\d+)',\s*'(\d+)'\)", onclick_text)
                            if match:
                                cmpy_id = match.group(1)
                                security_id = match.group(2)
                                stock_ids[symbol_text] = {
                                    "symbol": symbol_text,
                                    "cmpy_id": cmpy_id,
                                    "security_id": security_id
                                }
                    except Exception as e:
                        # print(f"Error parsing row: {e}")
                        pass
                        
        except Exception as e:
            print(f"Error scraping page {page_num}: {e}")
        
        # Next Page logic
        try:
            next_link = driver.find_elements(By.LINK_TEXT, str(page_num + 1))
            
            if next_link:
                print(f"  Clicking page {page_num + 1}...")
                driver.execute_script("arguments[0].scrollIntoView(true);", next_link[0])
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
    
    print(f"Found IDs for {len(stock_ids)} stocks.")
    
    with open("data/stock_ids.json", 'w') as f:
        json.dump(stock_ids, f, indent=4)
        
    return stock_ids

if __name__ == "__main__":
    scrape_official_symbols()
