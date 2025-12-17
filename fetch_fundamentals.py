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

def init_driver():
    options = Options()
    options.add_argument("--headless=new") # Run headless for background processing
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--log-level=3")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
    return driver

import re

def scrape_fundamentals(driver, symbol):
    url = f"https://www.investagrams.com/Stock/{symbol}"
    try:
        driver.get(url)
        time.sleep(5) # Give it 5 seconds to fully render
        
        source = driver.page_source
        
        data = {}
        
        # Dividend Yield (Confirmed structure based on debug: <div class="fw-700 fs-20 ng-binding">2.96%</div>)
        div = re.search(r'Dividend Yield.*?class="fw-700[^"]*">([\d\.]+)%', source, re.DOTALL)
        
        # P/E Ratio (Header: P/E Ratio </th> ... value in td?)
        # Broader search for number after label using HTML tags as separators
        pe = re.search(r'P/E Ratio.*?class="[^"]*text-right"[^>]*>\s*([\d\.]+)', source, re.DOTALL)
        pe = re.search(r'P/E Ratio.*?class="[^"]*text-right"[^>]*>\s*([\d\.]+)', source, re.DOTALL)
        # Note: Do NOT use a broad fallback here, it matches "30.00" labels in footers/ads.

             
        # EPS
        eps = re.search(r'EPS[^<]*<.*?([\d\.-]+)', source, re.DOTALL)
        
        # Market Cap
        mc = re.search(r'Market Cap.*?([\d\.,]+)\s*([BM]?)', source, re.IGNORECASE | re.DOTALL)

        if pe: 
            try: data["pe_ratio"] = float(pe.group(1))
            except: pass
        if eps: 
            try: data["eps"] = float(eps.group(1))
            except: pass
            
        if mc:
            try:
                val_str = mc.group(1).replace(',', '')
                suffix = mc.group(2).upper()
                val = float(val_str)
                if suffix == 'B': val *= 1_000_000_000
                elif suffix == 'M': val *= 1_000_000
                data["market_cap"] = val
            except: pass
            
        if div: 
            try: data["div_yield"] = float(div.group(1))
            except: pass
            
        # Company Name
        # Context 1: ng-bind="StockInfo.CompanyName">Jollibee Foods Corporation</h1>
        name_match = re.search(r'StockInfo\.CompanyName">([^<]+)<', source)
        if name_match:
            data["company_name"] = name_match.group(1).strip()
        else:
            # Fallback 1: Meta Description "Company Name (SYMBOL)"
            # <meta name="description" content="Jollibee Foods Corporation (JFC) - Look at ...
            meta_match = re.search(r'<meta name="description" content="([^"\(]+)\s*\(', source, re.IGNORECASE)
            if meta_match:
                data["company_name"] = meta_match.group(1).strip()
            else:
                 # Fallback 2: Title Tag "Stock - Company Name - Investagrams" or "Company Name Stock Price..."
                 title_match = re.search(r'<title>([^<\-]+)-', source, re.IGNORECASE)
                 if title_match:
                      data["company_name"] = title_match.group(1).strip()
        
        print(f"DEBUG {symbol}: PE={pe.group(1) if pe else 'None'} Div={div.group(1) if div else 'None'} Name={data.get('company_name', 'None')}")
        
        if data:
            return data
            
        return None
        
    except Exception as e:
        print(f"Error scraping {symbol}: {e}")
        return None

def main():
    print("Initializing Selenium Driver for Fundamentals...")
    driver = init_driver()
    report_gen = ReportGenerator()
    
    all_symbols = get_all_symbols()
    data = load_data()
    
    stocks_to_fetch = [s for s in all_symbols if s not in data]
    print(f"Found {len(stocks_to_fetch)} stocks missing fundamentals.")
    
    total = len(all_symbols)
    processed = len(data)
    
    try:
        for i, symbol in enumerate(stocks_to_fetch):
            print(f"[{processed + 1}/{total}] Fetching Fundamentals for {symbol}...")
            
            # Scrape
            fund_data = scrape_fundamentals(driver, symbol)
            
            # Even if None, we mark it as processed to handle "No Data" cases
            data[symbol] = fund_data if fund_data else {"error": "No Data"}
            
            # Save every stock to facilitate live updates
            save_data(data)
            processed += 1
            update_progress(processed, total)
            
            # Regenerate Dashboard to reflect new data
            # This ensures the static HTML is updated with new progress % and data
            print(f"Updating Dashboard... ({int((processed/total)*100)}%)")
            report_gen.generate_dashboard()
            
            # Sleep to be polite
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("Stopping scraper...")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
