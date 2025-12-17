# stock_data.py

# Curated & Validated list of PSE Stocks
# Classification based on best-effort mapping. Some stocks might be in "Others" if unclear.

STOCK_CATEGORIES = {
    "Financials": [
        "BDO", "BPI", "MBT", "SECB", "PNB", "EW", "UBP", "RCBC", "CHIB", "AUB", 
        "PSB", "COL", "NRCP", "V", "RCI", "SLF"
    ],
    "Holding Firms": [
        "SM", "AC", "JG", "AEV", "LTG", "AGI", "GTCAP", "DMC", "FGEN", "ANS", 
        "FPH", "JGS", "FDC", "COSCO", "ABA", "ABG", "APC", "ATN", "ATNB", 
        "BHI", "DWC", "JOH", "KEP", "LPZ", "MHC", "MJIC", "MPI", "MV", "POPI", 
        "SGI", "SMC", "SMC2I", "TFHI", "WIN", "ZHI"
    ],
    "Property": [
        "ALI", "SMPH", "RLC", "FLI", "MEG", "VLL", "CLI", "DD", "DDMPR", "AREIT",
        "FILRT", "MREIT", "RCR", "CREIT", "ALCO", "ALLHC", "ARA", "BEL", "BRN", 
        "CDC", "CEI", "CPG", "CROWN", "CYBR", "ELI", "EVER", "GERI", "HOME", 
        "HOUSE", "IRC", "KPH", "LAND", "LOTO", "MRC", "PA", "PHES", "PRIM", 
        "PTC", "ROCK", "SHNG", "SLI", "STN", "STR", "TFC", "UPM", "WPI"
    ],
    "Services": [
        "ICT", "TEL", "GLO", "JFC", "CNVRG", "DITO", "BLOOM", "CEB", "WLCON", 
        "RRHI", "PGOLD", "MAXS", "SSI", "MONDE", "PIZZA", "FB", "GSMI", "EMP", 
        "FRUIT", "ANI", "AXLM", "BALAI", "BCOR", "BSC", "DFNN", "FEU", "GMA7", 
        "GOLD", "HI", "IPM", "IS", "JAS", "LBC", "LR", "MAH", "MB", "MED", 
        "MRSGI", "NOW", "PHA", "PHN", "PPC", "PRMX", "RHI", "SEVN", "STI", 
        "TBGI", "WEB"
    ],
    "Industrial": [
        "ACEN", "MER", "URC", "DNL", "AP", "FGEN", "MWC", "MWIDE", "PCOR", 
        "SHLPH", "PNX", "CHP", "EEI", "HLCM", "LSC", "MACAY", "MG", "PMPC", 
        "RFM", "ROX", "S", "SPC", "SPL", "SSP", "TECH", "VITA", "VMC", "VVT",
        "ALHI", "BKR", "C", "CAT", "CIP", "CNPF", "EC", "ENEX", "EURO", 
        "FOOD", "GREEN", "IMI", "ION", "LFM", "LMG", "MVC", "PHC", "PPR", 
        "SFI", "SPNEC", "TOP", "VUL"
    ],
    "Mining & Oil": [
        "SCC", "NIKL", "APX", "FNI", "PX", "ORE", "MARC", "AT", "LC", "MA", 
        "AB", "APL", "BC", "COAL", "CPM", "DIZ", "GEO", "IPM", "NI", "OM", 
        "OPM", "OV", "PXP"
    ],
    "SME / Others": [
        # Catch-all for remaining stocks or those with unclear classification
        "ACE", "APO", "BMM", "CAB", "CLX", "HVN", "IDC", "KPS", "LODE", 
        "MAB", "MAC", "MFIN", "NRCP", "PAX", "PHR", "PLDF", "PRF", "PTT", 
        "SRA", "SUN", "TPC", "WPP"
    ]
}

def get_all_symbols():
    """Return a flat list of all unique symbols."""
    symbols = []
    for cat_stocks in STOCK_CATEGORIES.values():
        symbols.extend(cat_stocks)
    return list(set(symbols))
