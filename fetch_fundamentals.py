# fetch_fundamentals.py
import json
import os
import time
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Import symbols
from stock_data import get_all_symbols
from report_generator import ReportGenerator

DATA_FILE = "data/fundamental_data.json"
METADATA_FILE = "data/metadata.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def update_progress(processed, total):
    # Optimization: Only write to disk every 5 items or if complete, to save IO
    if processed % 5 != 0 and processed != total:
        return

    meta = {}
    if os.path.exists(METADATA_FILE):
        try:
            with open(METADATA_FILE, 'r') as f:
                meta = json.load(f)
        except:
            pass
    
    meta['fundamentals_progress'] = {
        'processed': processed,
        'total': total,
        'percentage': int((processed / total) * 100)
    }
    
    with open(METADATA_FILE, 'w') as f:
        json.dump(meta, f, indent=4)

import time
import json
import os
import re
import random
from concurrent.futures import ProcessPoolExecutor, as_completed
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from stock_data import STOCK_CATEGORIES
from report_generator import ReportGenerator

# File to store data
DATA_FILE = "data/fundamental_data.json"

def get_chrome_driver():
    """Create a new headless driver instance."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--log-level=3")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def fetch_single_stock(symbol):
    """Worker function to scrape a single stock."""
    print(f"Starting fetch for {symbol}...")
    driver = None
    data = {}
    
    try:
        driver = get_chrome_driver()
        url = f"https://www.investagrams.com/Stock/{symbol}"
        driver.get(url)
        
        # Trigger lazy load
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(5 + random.random() * 3) # Random sleep 5-8s
        
        source = driver.page_source
        
        # 1. Company Name/Header
        # e.g. "Title: JFC: 187.30..."
        page_title = driver.title
        data['company_name'] = page_title.split('-')[0].strip() if '-' in page_title else symbol

        # Price extraction
        price_match = re.search(r':\s*([\d\.,]+)', page_title)
        if not price_match:
             price_match = re.search(r'-\s*([\d\.,]+)', page_title)
        
        stock_price = float(price_match.group(1).replace(',', '')) if price_match else None
        
        # 2. Dividend Yield
        div = re.search(r'Dividend Yield.*?class="fw-700[^"]*">([\d\.]+)%', source, re.DOTALL)
        if div:
            try: data["div_yield"] = float(div.group(1))
            except: pass

        # 3. P/E Ratio
        pe = re.search(r'P/E Ratio(?:.|\n)*?class="[^"]*fs-20[^"]*ng-binding[^"]*">\s*([\d\.,]+)', source, re.IGNORECASE)
        pe_val = None
        if pe:
            try:
                pe_val = float(pe.group(1).replace(',', ''))
                data["pe_ratio"] = pe_val
            except: pass
            
        # 4. Market Cap
        mc = re.search(r'Market Cap.*?([\d\.,]+)\s*([BM]?)', source, re.IGNORECASE | re.DOTALL)
        if mc:
            try:
                val = mc.group(1).replace(',', '')
                suffix = mc.group(2).upper()
                mult = 1_000_000_000 if suffix == 'B' else 1_000_000 if suffix == 'M' else 1
                data["market_cap"] = float(val) * mult
            except: pass
            
        # 5. EPS & Dividend Amount Calculation
        if stock_price and pe_val and pe_val > 0:
            data["eps"] = round(stock_price / pe_val, 4)
        else:
             # Fallback regex for EPS
             eps = re.search(r'(?:EPS|Earnings Per Share)(?:.|\n)*?class="[^"]*fs-20[^"]*ng-binding[^"]*">\s*([\d\.,\-]+)', source, re.IGNORECASE)
             if eps:
                 try: data["eps"] = float(eps.group(1).replace(',', ''))
                 except: pass

        yield_val = data.get("div_yield")
        if yield_val and stock_price:
             data["div_amount"] = round(stock_price * (yield_val / 100.0), 4)

        # Debug print
        d_str = f"PE={data.get('pe_ratio','?')} Div={data.get('div_yield','?')}%"
        print(f"Done {symbol}: {d_str}")
        
        return symbol, data

    except Exception as e:
        print(f"Failed {symbol}: {e}")
        return symbol, None
    finally:
        if driver:
            driver.quit()

def main():
    print("Initializing Parallel Scraper...")
    
    # Load existing data
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            existing_data = json.load(f)
    else:
        existing_data = {}

    all_symbols = []
    for cat, symbols in STOCK_CATEGORIES.items():
        all_symbols.extend(symbols)
    
    # Filter only missing
    stocks_to_fetch = [s for s in all_symbols if s not in existing_data]
    
    # Shuffle to mix heavy/light pages potentially
    random.shuffle(stocks_to_fetch)
    
    print(f"Found {len(stocks_to_fetch)} stocks to fetch.")
    
    # Use 8 workers to push performance without crashing memory/getting blocked
    # 50 workers would consume too much RAM and likely trigger WAF blocks.
    MAX_WORKERS = 8
    
    with ProcessPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_symbol = {executor.submit(fetch_single_stock, s): s for s in stocks_to_fetch}
        
        count = 0
        total = len(stocks_to_fetch)
        
        for future in as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            try:
                sym, result = future.result()
                if result:
                    existing_data[sym] = result
                    
                    # Periodic save (every 5 items) to prevent total loss
                    if len(existing_data) % 5 == 0:
                        with open(DATA_FILE, 'w') as f:
                            json.dump(existing_data, f, indent=4)
                        # Skipped intermediate dashboard gen to prevent corruption/race conditions
                        print(f"Saved {len(existing_data)} stocks.")
                        
            except Exception as exc:
                print(f'{symbol} generated an exception: {exc}')
            
            count += 1
            print(f"Progress: {count}/{total} completed.")

    # Final Save
    with open(DATA_FILE, 'w') as f:
        json.dump(existing_data, f, indent=4)
        
    print("Scraping Completed.")
    gen = ReportGenerator()
    gen.generate_dashboard()

if __name__ == "__main__":
    main()
