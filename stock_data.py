# stock_data.py
# Dynamic Stock Configuration v2.0
# Loads categories and symbols strictly from data/stock_metadata.json

import json
import os

METADATA_FILE = "data/stock_metadata.json"
STOCK_IDS_FILE = "data/stock_ids.json"

def load_json(filename):
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base_dir, filename)
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"[Warning] Could not load {filename}: {e}")
    return {}

def _build_categories():
    """Dynamically build STOCK_CATEGORIES from metadata."""
    meta = load_json(METADATA_FILE)
    if not meta:
        # Fallback to simple list from stock_ids if metadata missing
        ids = load_json(STOCK_IDS_FILE)
        return {"All Stocks": list(ids.keys())} if ids else {}

    categories = {}
    for symbol, data in meta.items():
        sec = data.get('sector', 'Uncategorized')
        # Normalize
        sec = sec.replace(' & ', ' and ')
        sec = sec.replace('Small, Medium and Emerging Board', 'SME Board')
        
        if sec not in categories:
            categories[sec] = []
        categories[sec].append(symbol)
        
    return categories

# Dynamic Constants
STOCK_CATEGORIES = _build_categories()

def get_all_symbols():
    """Return a flat list of all unique symbols from the loaded categories."""
    symbols = []
    for cat_stocks in STOCK_CATEGORIES.values():
        symbols.extend(cat_stocks)
    return sorted(list(set(symbols)))
