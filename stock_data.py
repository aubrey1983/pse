# stock_data.py

# Curated & Validated list of PSE Stocks
# Classification based on best-effort mapping. Some stocks might be in "Others" if unclear.

STOCK_CATEGORIES = {
    "Financials": [
        "BDO", "BPI", "MBT", "SECB", "PNB", "EW", "UBP", "RCB", "AUB", 
        "PSB", "COL", "NRCP", "V", "RCI", "SLF"
    ],
    "Holding Firms": [
        "SM", "AC", "AEV", "LTG", "AGI", "GTCAP", "DMC", "FGEN", "ANS", 
        "FPH", "JGS", "FDC", "COSCO", "ABA", "ABG", "APC", "ATN", 
        "BHI", "DWC", "JOH", "KEP", "LPZ", "MHC", "MJIC", 
        "SGI", "SMC", "TFHI", "WIN", "ZHI"
    ],
    "Property": [
        "ALI", "SMPH", "RLC", "FLI", "MEG", "VLL", "CLI", "DD", "DDMPR", "AREIT",
        "FILRT", "MREIT", "RCR", "CREIT", "ALCO", "ALLHC", "ARA", "BEL", "BRN", 
        "CDC", "CEI", "CPG", "CROWN", "CYBR", "ELI", "GERI", "HOME", 
        "HOUSE", "KPH", "LAND", "LOTO", "MRC", "PA", "PHES", "PRIM", 
        "PTC", "ROCK", "SHNG", "SLI", "STN", "STR", "TFC", "UPM", "WPI"
    ],
    "Services": [
        "ICT", "TEL", "GLO", "JFC", "CNVRG", "DITO", "BLOOM", "CEB", "WLCON", 
        "RRHI", "PGOLD", "MAXS", "SSI", "MONDE", "PIZZA", "FB", "GSMI", "EMI", 
        "FRUIT", "ANI", "AXLM", "BALAI", "BCOR", "BSC", "DFNN", "FEU", "GMA7", 
        "HI", "IPM", "IS", "JAS", "LBC", "MAH", "MB", "MED", 
        "MRSGI", "NOW", "PHA", "PHN", "PPC", "PRMX", "SEVN", "STI", 
        "TBGI", "WEB"
    ],
    "Industrial": [
        "ACEN", "MER", "URC", "DNL", "AP", "FGEN", "MWC", "MWIDE", "PCOR", 
        "SHLPH", "PNX", "CHP", "EEI", "LSC", "MACAY", "MG", "PMPC", 
        "RFM", "ROX", "SPC", "TECH", "VITA", "VMC", "VVT",
        "ALHI", "BKR", "C", "CAT", "CNPF", "ENEX", "EURO", 
        "FOOD", "GREEN", "IMI", "ION", "LFM", "LMG", "MVC", "PHC", 
        "SFI", "SPNEC", "TOP", 
    ],
    "Mining & Oil": [
        "SCC", "NIKL", "APX", "FNI", "PX", "ORE", "MARC", "AT", "LC", "MA", 
        "AB", "APL", "BC", "COAL", "CPM", "DIZ", "GEO", "IPM", "NI", "OM", 
        "OPM", "OV", "PXP"
    ],
    "SME / Others": [
        # Catch-all for remaining stocks or those with unclear classification
        "ACE", "APO", "BMM", "HVN", "IDC", "LODE", 
        "MAC", "MFIN", "NRCP", "PAX", "PHR", "PTT", 
        "SUN", 
    ]
}


import json
import os

def load_official_symbols():
    try:
        # Resolve path relative to this file
        base_dir = os.path.dirname(os.path.abspath(__file__))
        json_path = os.path.join(base_dir, 'data', 'stock_ids.json')
        
        with open(json_path, 'r') as f:
            stock_ids = json.load(f)
        return list(stock_ids.keys())
    except Exception as e:
        print(f"[Warning] Could not load stock_ids.json: {e}")
        return []

# Dynamically update categories with unmapped official stocks
_val_official = load_official_symbols()
_val_categorized = set()
for cats in STOCK_CATEGORIES.values():
    _val_categorized.update(cats)

_val_uncategorized = [s for s in _val_official if s not in _val_categorized]

if _val_uncategorized:
    # Ensure SME / Others exists
    if "SME / Others" not in STOCK_CATEGORIES:
        STOCK_CATEGORIES["SME / Others"] = []
    
    # Add unique ones
    current_others = set(STOCK_CATEGORIES["SME / Others"])
    for s in _val_uncategorized:
        if s not in current_others:
            STOCK_CATEGORIES["SME / Others"].append(s)

def get_all_symbols():
    """Return a flat list of all unique symbols from the official list."""
    if _val_official:
        return _val_official
    # Fallback to hardcoded if JSON load fails
    symbols = []
    for cat_stocks in STOCK_CATEGORIES.values():
        symbols.extend(cat_stocks)
    return list(set(symbols))
