import json
import stock_data

OFFICIAL_LIST_FILE = "data/official_pse_list.json"

def validate():
    try:
        with open(OFFICIAL_LIST_FILE, 'r') as f:
            official_symbols = set(json.load(f))
    except FileNotFoundError:
        print(f"Error: {OFFICIAL_LIST_FILE} not found.")
        return

    current_symbols = set(stock_data.get_all_symbols())
    
    # intersection
    valid_symbols = current_symbols.intersection(official_symbols)
    
    # differences
    invalid_symbols = current_symbols - official_symbols
    missing_official = official_symbols - current_symbols
    
    print(f"Total Current Symbols: {len(current_symbols)}")
    print(f"Total Official Symbols: {len(official_symbols)}")
    print(f"Valid Symbols: {len(valid_symbols)}")
    print("-" * 30)
    
    if invalid_symbols:
        print(f"INVALID SYMBOLS found in our list ({len(invalid_symbols)}):")
        for s in sorted(list(invalid_symbols)):
            print(f" - {s}")
    else:
        print("All current symbols are VALID!")
        
    print("-" * 30)
    print(f"Missing Official Symbols (available to add): {len(missing_official)}")
    # Uncomment to see missing
    # print(missing_official)

if __name__ == "__main__":
    validate()
