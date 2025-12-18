import json
import re

DATA_FILE = "data/fundamental_data.json"

def audit_names():
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        print("Data file not found.")
        return

    invalid_count = 0
    suspicious = []

    print(f"{'SYMBOL':<10} | {'CURRENT NAME':<40} | {'ISSUE'}")
    print("-" * 70)

    for symbol, details in data.items():
        name = details.get('company_name', '').strip()
        issue = None

        # Check 1: Name is same as Symbol
        if name == symbol:
            issue = "Same as Symbol"
        
        # Check 2: Contains "Title:" or similar artifacts from scraping
        elif "Title:" in name or "Symbol:" in name or "(" in name or ":" in name:
            issue = "Dirty Scrape"
            
        # Check 3: Too short (likely just an acronym or bad data)
        elif len(name) < 4 and name != symbol:
             # Some tickers might be short, but names usually aren't. 
             # Exception: "SM" is "SM" but usually "SM Investments..."
             issue = "Too Short"

        if issue:
            suspicious.append((symbol, name, issue))
            print(f"{symbol:<10} | {name:<40} | {issue}")
            invalid_count += 1

    print("-" * 70)
    print(f"Total Stocks: {len(data)}")
    print(f"Suspicious Names: {invalid_count}")
    
    # Generate a list for re-scraping
    if suspicious:
        print("\nTo fix these, we can run the scraper specifically for these symbols.")
        fix_list = [s[0] for s in suspicious]
        print(f"Fix List: {','.join(fix_list)}")

if __name__ == "__main__":
    audit_names()
