# main.py
# Entry point for PSE stock monitoring
import json
import numpy as np

class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.bool_):
            return bool(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(CustomEncoder, self).default(obj)

from data_fetcher import DataFetcher
from analyzer import Analyzer
from recommender import Recommender
from report_generator import ReportGenerator
import datetime
from stock_data import STOCK_CATEGORIES, get_all_symbols

# Configuration
START_DATE = "2023-01-01"
END_DATE = datetime.datetime.now().strftime("%Y-%m-%d")

def main():
    fetcher = DataFetcher()
    analyzer = Analyzer()
    recommender = Recommender()
    report_gen = ReportGenerator()
    
    analysis_results = {}
    all_symbols = get_all_symbols()
    
    print(f"Starting analysis for {len(all_symbols)} stocks across {len(STOCK_CATEGORIES)} industries...")
    
    print(f"Using max_workers=8 for faster fetching...")
    
    import concurrent.futures
    import threading
    
    # Thread-safe printer
    print_lock = threading.Lock()
    
    def process_stock(symbol):
        """Worker function to fetch and analyze a single stock."""
        try:
            # 1. Fetch Data
            data = fetcher.fetch_investagrams(symbol, days=365)
            
            if data is not None and not data.empty:
                analysis = analyzer.analyze_trend(data)
                
                with print_lock:
                    print(f"  [OK] [{symbol}] {analysis['last_close']:.2f} | {analysis.get('trend')} | RSI: {analysis.get('rsi', 0):.1f}")
                
                return symbol, analysis
            else:
                with print_lock:
                    print(f"  [X] [{symbol}] No data")
                return symbol, None
                
        except Exception as e:
            with print_lock:
                print(f"  [!] [{symbol}] Error: {e}")
            return symbol, None

    # Run in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        future_to_symbol = {executor.submit(process_stock, sym): sym for sym in all_symbols}
        
        completed_count = 0
        total_count = len(all_symbols)
        
        for future in concurrent.futures.as_completed(future_to_symbol):
            symbol, result = future.result()
            completed_count += 1
            if result:
                analysis_results[symbol] = result

    # Save Technical Data
    with open("data/technical_data.json", "w") as f:
        json.dump(analysis_results, f, indent=4, cls=CustomEncoder)

    fetcher.close()
    
    print(f"\nAnalysis Complete! {len(analysis_results)} stocks processed.")
    
    # News Integration
    import fetch_news
    print(f"\n[i] Fetching News...")
    try:
        # We can pass specific targets if we really want to filter, 
        # but the logic in fetch_news handles filtering (score >= 6).
        # Or we can pass 'analysis_results.keys()' if we want news for ALL processed stocks (might be too many).
        # Let's stick to fetch_news default logic (score >= 6) for now to save bandwidth, 
        # or we can pass the high scoring ones from our analysis.
        
        # Let's refine: Pass high scoring stocks from analysis_results to fetch_news?
        # main.py knows the exact analysis. fetch_news re-calculates. 
        # Optimization: Pass list of symbols with score >= 6 from analysis_results.
        
        # Actually, let's just let fetch_news do its thing to minimize main.py complexity for now.
        fetch_news.run_news_fetch() 
    except Exception as e:
        print(f"[!] News Fetch Error: {e}")
    
    # Generate Dashboard
    print(f"\n[i] Generating Dashboard...")
    report_gen.generate_dashboard() # Output file arg is default
    print(f"[OK] Dashboard saved.")
    
    print(f"\n[->] Opening dashboard in browser...")
    report_gen.open_in_browser("report.html")
    
    print(f"\n[NOTE] Run 'python fetch_pse_fundamentals.py' in a separate terminal to populate fundamental data.")


if __name__ == "__main__":
    main()

