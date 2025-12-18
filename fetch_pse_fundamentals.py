import json
import os
import re
import datetime
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed

# Files
STOCK_IDS_FILE = "data/stock_ids.json"
TECHNICAL_DATA_FILE = "data/technical_data.json"
OUTPUT_FILE = "data/pse_fundamentals.json"

# URLs
STOCK_DATA_URL = "https://edge.pse.com.ph/companyPage/stockData.do?cmpy_id={}&security_id={}"
FINANCIALS_URL = "https://edge.pse.com.ph/companyPage/financial_reports_view.do?cmpy_id={}"
DIVIDENDS_URL = "https://edge.pse.com.ph/companyPage/dividends_and_rights_form.do?cmpy_id={}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def load_json(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def word_to_num(text):
    """Simple helper to convert text numbers to float. Covers 0-99 and common variations."""
    text = text.lower().replace('-', ' ')
    units = {
        "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, 
        "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
        "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
        "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
        "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, 
        "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90
    }
    
    total = 0
    current = 0
    words = text.split()
    
    found = False
    for w in words:
        if w in units:
            current += units[w]
            found = True
    
    return float(current) if found else None

def clean_value(text):
    if not text:
        return None
    # Remove parentheses for negative values "(123.45)" -> "-123.45"
    if '(' in text and ')' in text:
        text = text.replace('(', '-').replace(')', '')
    text = text.replace(',', '').strip()
    
    # Handle "Fifty-five Centavos" Case
    if "centavo" in text.lower():
        num = word_to_num(text)
        if num is not None:
            return num / 100.0
            
    try:
        return float(text)
    except:
        return None

def scrape_stock_details(symbol, ids, tech_price):
    session = requests.Session()
    session.headers.update(HEADERS)
    
    data = {
        "symbol": symbol,
        "pe_ratio": None,
        "eps": None,
        "div_history": [],
        "last_updated": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "status": "Active" # Default
    }
    
    cmpy_id = ids.get('cmpy_id')
    security_id = ids.get('security_id')
    
    if not cmpy_id:
        return data

    # 1. PE Ratio (stockData.do)
    if security_id:
        try:
            resp = session.get(STOCK_DATA_URL.format(cmpy_id, security_id), timeout=10)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, 'html.parser')
                # Find TH with "P/E Ratio"
                th = soup.find('th', string=re.compile(r'P/E Ratio', re.I))
                if th:
                    # Value is in the following TD
                    td = th.find_next_sibling('td')
                    if td:
                        data['pe_ratio'] = clean_value(td.text)
                
                # Status
                th_stat = soup.find('th', string=re.compile(r'Status', re.I))
                if th_stat:
                    td_stat = th_stat.find_next_sibling('td')
                    if td_stat:
                        data['status'] = td_stat.text.strip()
        except Exception as e:
            pass # print(f"[{symbol}] PE Error: {e}")

    # 2. EPS (financial_reports_view.do)
    try:
        resp = session.get(FINANCIALS_URL.format(cmpy_id), timeout=15)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            # Look for Earnings/(Loss) Per Share (Basic)
            # Use specific text
            th = soup.find('th', string=re.compile(r'Earnings/\(Loss\) Per Share \(Basic\)', re.I))
            if not th:
                th = soup.find('th', string=re.compile(r'Earnings Per Share', re.I))
            
            if th:
                # Value is in the following TD
                td = th.find_next_sibling('td')
                if td:
                    data['eps'] = clean_value(td.text)
    except Exception as e:
        pass # print(f"[{symbol}] EPS Error: {e}")

    # 3. Dividend History (Ajax POST)
    DIVIDENDS_AJAX_URL = "https://edge.pse.com.ph/companyPage/dividends_and_rights_list.ax?DividendsOrRights=Dividends"
    try:
        # Must use POST with cmpy_id
        resp = session.post(DIVIDENDS_AJAX_URL, data={"cmpy_id": cmpy_id}, timeout=10)
        
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            # Find rows in the returned table
            rows = soup.find_all('tr')
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 4:
                    # In Ajax response: 
                    # Col 0: Type (Common)
                    # Col 1: Div Type (Cash)
                    # Col 2: Rate (PhP 1.00)
                    # Col 3: Ex-Date
                    # Col 4: Rec-Date
                    # Col 5: Pay-Date
                    
                    # Safety check on column count
                    if len(cols) < 6: continue
                    
                    security_name = cols[0].text.strip().upper()
                    # Filter: Must be "Common" or contain the Symbol (e.g. "GTCAP" but not "GTPPB" if possible, usually checking "Common" is safest)
                    # GTCAP example: "GTPPB" vs "Common"
                    # If it's a preferred share, it usually won't say "Common"
                    if "COMMON" not in security_name and symbol not in security_name:
                         # Extra safety: if symbol is GTCAP and security_name is GTPPB, we should skip
                         # But if security_name is just "GTCAP", we keep.
                         # If security_name is "GTPPB", symbol "GTCAP" is NOT in it (False) -> Wait, GTCAP is not in GTPPB? 
                         # Actually GTCAP is not a substring of GTPPB.
                         # Let's stick to: if "COMMON" is in it, take it. If record says "GTPPB", "PREF", etc, skip.
                         # Most PSE records say "Common" or "Preferred".
                         if "PREF" in security_name or "GTPPB" in security_name or "PCOR" not in security_name and symbol == "PCOR":
                             # specialized checks might be messy.
                             pass
                    
                    # Better Logic:
                    # If "PREFERRED" or "PF" or specific known preferreds in name -> SKIP
                    if "PREFERRED" in security_name or "PF" in security_name or "GTPPB" in security_name:
                        continue
                        
                    div_type = cols[1].text.strip() # "Cash" is in 2nd col usually
                    if "Cash" in div_type:
                        amount_text = cols[2].text.strip() # "PhP 1.00"
                        ex_date = cols[3].text.strip()
                        pay_date = cols[5].text.strip()
                        
                        # Clean amount "PhP 1.00" -> 1.00
                        # Handle "Php1.10 per share", "PHP 1.00", "₱1.00"
                        # Robust extraction
                        # 1. Try standard regex for digits "P0.42"
                        clean_text = amount_text.replace(',', '')
                        # print(f"[{symbol}] Raw Amount: {amount_text}") # DEBUG
                        match = re.search(r'(\d+(?:\.\d+)?)', clean_text)
                        
                        amount = None
                        if match:
                            try:
                                amount = float(match.group(1))
                            except: pass
                        else:
                            # 2. Fallback to Text Parsing
                            amount = clean_value(amount_text)
                        
                        data['div_history'].append({
                            "type": div_type,
                            "amount": amount,
                            "ex_date": ex_date,
                            "pay_date": pay_date
                        })
                        
    except Exception as e:
        pass # print(f"[{symbol}] Div Error: {e}")



    # Calculations
    # If EPS missing but have PE and Price -> Calc EPS
    if data['eps'] is None and data['pe_ratio'] and data['pe_ratio'] > 0 and tech_price:
        data['eps'] = round(tech_price / data['pe_ratio'], 4)
        
    # If PE missing but have EPS and Price -> Calc PE
    if data['pe_ratio'] is None and data['eps'] and data['eps'] != 0 and tech_price:
        data['pe_ratio'] = round(tech_price / data['eps'], 2)

    return data

def main():
    stock_ids = load_json(STOCK_IDS_FILE)
    technical_data = load_json(TECHNICAL_DATA_FILE)
    
    if not stock_ids:
        print("No stock IDs found. Run scrape_pse_list.py first.")
        return

    results = {}
    
    # 10 workers for speed with requests
    max_workers = 10
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_symbol = {}
        
        # Test specific list only
        # test_items = [(s, stock_ids[s]) for s in ['ALI', 'JFC', 'BDO', 'TEL', 'SMPH'] if s in stock_ids]
        
        # FULL RUN (Uncomment below)
        test_items = stock_ids.items()
        # test_items = [(s, stock_ids[s]) for s in ['CNPF'] if s in stock_ids]
        
        for symbol, ids in test_items:
            tech = technical_data.get(symbol, {})
            price = tech.get('last_close')
            
            future = executor.submit(scrape_stock_details, symbol, ids, price)
            future_to_symbol[future] = symbol
            
        count = 0
        total = len(test_items)
        
        for future in as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            try:
                data = future.result()
                results[symbol] = data
                count += 1
                
                # Concise progress
                div_c = len(data['div_history'])
                print(f"[{symbol}] EPS:{data['eps']} PE:{data['pe_ratio']} Divs:{div_c}")
                
                if count % 10 == 0:
                    with open(OUTPUT_FILE, 'w') as f:
                        json.dump(results, f, indent=4)
                        
            except Exception as exc:
                print(f"[{symbol}] Error: {exc}")

    print("Scraping Complete!")
    with open(OUTPUT_FILE, 'w') as f:
        json.dump(results, f, indent=4)

if __name__ == "__main__":
    main()
