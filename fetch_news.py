import json
import os
import requests
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from analyzer import Analyzer

# Files
TECHNICAL_DATA_FILE = "data/technical_data.json"
FUNDAMENTAL_DATA_FILE = "data/pse_fundamentals.json"
NEWS_DATA_FILE = "data/news_data.json"

def load_json(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except:
            return {}
    return {}

def fetch_rss(symbol):
    """Fetch Google News RSS for a symbol."""
    query = f"{symbol} stock philippines"
    url = f"https://news.google.com/rss/search?q={query}&hl=en-PH&gl=PH&ceid=PH:en"
    
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            root = ET.fromstring(resp.content)
            items = []
            count = 0
            for item in root.findall('.//item'):
                title = item.find('title').text
                pubDate = item.find('pubDate').text
                link = item.find('link').text
                
                # Clean Source from Title "Title - Source"
                source = "Unknown"
                if " - " in title:
                    parts = title.rsplit(" - ", 1)
                    title = parts[0]
                    source = parts[1]
                
                items.append({
                    "title": title,
                    "source": source,
                    "date": pubDate,
                    "link": link
                })
                count += 1
                if count >= 5: break # Limit to latest 5 news per stock
            return items
    except Exception as e:
        print(f"Error fetching {symbol}: {e}")
    return []

def run_news_fetch(targets=None):
    """
    Fetches news for the given specific list of targets.
    If targets is None, it calculates targets based on score >= 6.
    """
    print("Loading Data for News Fetch...")
    # existing Load Data logic
    
    if targets is None:
        tech_data = load_json(TECHNICAL_DATA_FILE)
        fund_data = load_json(FUNDAMENTAL_DATA_FILE)
        analyzer = Analyzer()
        
        # 1. Identify Target Stocks (Score >= 6 to be broader than Top Picks)
        targets = []
        print("Scoring Stocks for News Eligibility...")
        for symbol, t in tech_data.items():
            f = fund_data.get(symbol, {})
            score, _ = analyzer.calculate_score(t, f)
            
            # Fetch news for anything decent, or part of top picks
            if score >= 6: 
                targets.append(symbol)
                
    print(f"Fetching News for {len(targets)} stocks...")
    
    news_results = {}
    
    # Load existing news to avoid re-fetching if recent? 
    # For now, we overwrite or maybe we should merge? 
    # Let's keep it simple and overwrite as per original logic.
    
    # 2. Parallel Fetch
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_symbol = {executor.submit(fetch_rss, sym): sym for sym in targets}
        
        count = 0
        for future in as_completed(future_to_symbol):
            sym = future_to_symbol[future]
            try:
                data = future.result()
                if data:
                    news_results[sym] = data
                    count += 1
            except Exception as e:
                print(f"[{sym}] Failed: {e}")
                
            if count % 10 == 0:
                print(f"News Progress: {count}/{len(targets)}")

    print(f"Saving {len(news_results)} news records to {NEWS_DATA_FILE}...")
    with open(NEWS_DATA_FILE, 'w') as f:
        json.dump(news_results, f, indent=4)
        
    return news_results

if __name__ == "__main__":
    run_news_fetch()
