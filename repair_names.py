import json
import os
import re
import concurrent.futures
from fetch_fundamentals import fetch_single_stock

DATA_FILE = "data/fundamental_data.json"

def get_bads():
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
    except:
        return {}

    bads = []
    for symbol, details in data.items():
        name = details.get('company_name', '').strip()
        
        # Audit Logic
        is_bad = False
        if name == symbol: is_bad = True
        elif "Title:" in name or "Symbol:" in name or ":" in name or "(" in name: is_bad = True
        elif len(name) < 4 and name != symbol: is_bad = True
        
        # Explicit check for the pattern the user reported
        if re.search(r":\s*\d", name): is_bad = True
        
        if is_bad:
            bads.append(symbol)
            
    return bads

def main():
    bads = get_bads()
    print(f"Found {len(bads)} stocks with invalid names. Starting repair...")
    
    # Load existing data to update it
    with open(DATA_FILE, 'r') as f:
        full_data = json.load(f)
        
    # Run scraper in parallel for these specific stocks
    # Using 4 workers to be safe/gentle
    with concurrent.futures.ProcessPoolExecutor(max_workers=4) as executor:
        future_to_symbol = {executor.submit(fetch_single_stock, sym): sym for sym in bads}
        
        count = 0
        total = len(bads)
        
        for future in concurrent.futures.as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            try:
                sym, result = future.result()
                if result:
                    # Update the main data
                    full_data[sym] = result
                    print(f"FIXED [{sym}]: {result.get('company_name')}")
            except Exception as exc:
                print(f'{symbol} generated an exception: {exc}')
            
            count += 1
            if count % 5 == 0:
                 # Periodic save
                 with open(DATA_FILE, 'w') as f:
                    json.dump(full_data, f, indent=4)
                 print(f"Saved progress ({count}/{total})")

    # Final Save
    with open(DATA_FILE, 'w') as f:
        json.dump(full_data, f, indent=4)
        
    print("Repair Complete.")

if __name__ == "__main__":
    main()
