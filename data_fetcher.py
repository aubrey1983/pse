# data_fetcher.py
# Fetches daily PSE stock data
import pandas as pd
import requests
from bs4 import BeautifulSoup
import datetime
import time


class DataFetcher:
    def __init__(self):
        pass

    def close(self):
        """No-op for compatibility"""
        pass

    def fetch_daily_data(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        """Deprecated: Use fetch_investagrams instead."""
        print(f"WARNING: fetch_daily_data is deprecated. Unused arguments: {start}, {end}")
        return self.fetch_investagrams(symbol)


    # ... (skipping existing methods to focus on the new one) ...



    def fetch_investagrams(self, symbol: str, days: int = 365) -> pd.DataFrame:
        """
        Fetch historical data from Investagrams Internal API.
        """
        try:
            # Direct Investagrams API Fetch
            now = int(datetime.datetime.now().timestamp())
            past = int((datetime.datetime.now() - datetime.timedelta(days=days)).timestamp())
            
            url = f"https://webapi.investagrams.com/InvestaApi/TradingViewChart/history?symbol={symbol}&resolution=D&from={past}&to={now}"
            
            # Simplified headers, Mimic browser
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://www.investagrams.com/",
            }
            
            resp = requests.get(url, headers=headers, timeout=10)
            
            if resp.status_code != 200:
                return None
                
            data = resp.json()
            
            if "t" not in data or not data["t"]:
                return None
                
            # Parse Data
            dates = [datetime.datetime.fromtimestamp(ts) for ts in data["t"]]
            
            df = pd.DataFrame({
                'Open': data['o'],
                'High': data['h'],
                'Low': data['l'],
                'Close': data['c'],
                'Volume': data['v']
            }, index=dates)
            
            df.index.name = 'Date'
            return df
            
        except Exception as e:
            # print(f"    ⚠ Investagrams Fetch Error for {symbol}: {e}") # Reduce noise
            return None

