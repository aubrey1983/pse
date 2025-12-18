import json
import re
import stock_data

OFFICIAL_LIST_FILE = "data/official_pse_list.json"
TARGET_FILE = "stock_data.py"

# Known renames or mapping fixes
FIX_MAP = {
    "RCBC": "RCB",
    "EMP": "EMI",
    "POPI": "ALLHC",
    "CHIB": "CHIB", # China Bank is CHIB? Wait, let's check official list.
    "EVER": "EVER", # Ever Gotesco? Might be delisted or renamed.
}

def fix_list():
    with open(OFFICIAL_LIST_FILE, 'r') as f:
        official_symbols = set(json.load(f))
        
    current_symbols_list = stock_data.get_all_symbols()
    current_symbols = set(current_symbols_list)
    
    # Calculate invalids again
    invalid_symbols = current_symbols - official_symbols
    
    print(f"Processing {len(invalid_symbols)} invalid symbols...")
    
    removals = []
    replacements = {}
    
    for sym in invalid_symbols:
        # Check map
        if sym in FIX_MAP:
            target = FIX_MAP[sym]
            if target in official_symbols:
                # If target is already in our list, just remove the old one (merge)
                if target in current_symbols:
                    print(f"  Removing {sym} (duplicate of {target})")
                    removals.append(sym)
                else:
                    print(f"  Renaming {sym} -> {target}")
                    replacements[sym] = target
            else:
                 # Map target invalid? Remove.
                 print(f"  Removing {sym} (Target {target} also invalid)")
                 removals.append(sym)
        else:
             # Just remove
             print(f"  Removing {sym} (Delisted/Unknown)")
             removals.append(sym)
             
    # Now read the stock_data.py file as text to perform surgical replacement/removal
    with open(TARGET_FILE, 'r') as f:
        lines = f.readlines()
        
    new_lines = []
    for line in lines:
        # We need to be careful not to replace partial strings.
        # Regex replacement might be safer
        
        # Simple string processing:
        # Identify quoted symbols in the line: "SYM"
        
        # We will reconstruct the line if it contains a stock symbol.
        if '"' in line:
            # Check for removals
            for rem in removals:
                # Remove "REM", 
                line = line.replace(f'"{rem}", ', '')
                line = line.replace(f'"{rem}"', '')
            
            # Check for replacements
            for old, new in replacements.items():
                line = line.replace(f'"{old}"', f'"{new}"')
                
            # Cleanup double commas or empty items if any
            line = line.replace(', ,', ',')
            line = line.replace('", , "', '", "')
            
        new_lines.append(line)
        
    with open(TARGET_FILE, 'w') as f:
        f.writelines(new_lines)
        
    print("stock_data.py updated.")

if __name__ == "__main__":
    fix_list()
