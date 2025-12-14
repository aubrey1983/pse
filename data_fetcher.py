# data_fetcher.py
# Fetches daily PSE stock data
import pandas as pd
import requests
import yfinance as yf
from bs4 import BeautifulSoup
import datetime
import time
import investpy

class DataFetcher:
    def fetch_daily_data(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        """Fetch daily stock data for a given symbol from PSE Edge."""
        # PSE Edge uses a specific endpoint for historical prices
        # We'll use the company symbol to get the security ID first
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Referer': 'https://edge.pse.com.ph/',
        }
        search_url = f"https://edge.pse.com.ph/common/CompanySearchResult.json?company={symbol}"
        resp = requests.get(search_url, headers=headers)
        if resp.status_code != 200 or not resp.json().get('records'):
            raise Exception(f"Failed to find security ID for {symbol} on PSE Edge.")
        security_id = resp.json()['records'][0]['securityId']
        # Now fetch historical prices
        # PSE Edge returns data in pages, so we may need to loop
        prices = []
        page = 0
        while True:
            price_url = (
                f"https://edge.pse.com.ph/common/DisclosureCht.json?"
                f"company={symbol}&security={security_id}&startDate={start}&endDate={end}&page={page}"
            )
            price_resp = requests.get(price_url, headers=headers)
            if price_resp.status_code != 200:
                break
            data = price_resp.json().get('records', [])
            if not data:
                break
            prices.extend(data)
            page += 1
            time.sleep(0.2)  # Be polite to the server
        if not prices:
            raise Exception(f"No price data found for {symbol} on PSE Edge.")
        # Convert to DataFrame
        df = pd.DataFrame(prices)
        # Standardize columns
        df['date'] = pd.to_datetime(df['tradeDate'])
        df = df.rename(columns={
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume',
        })
        df = df[['date', 'Open', 'High', 'Low', 'Close', 'Volume']]
        df = df.set_index('date')
        # Filter by date range
        df = df.loc[(df.index >= pd.to_datetime(start)) & (df.index <= pd.to_datetime(end))]
        return df

    def fetch_from_csv(self, csv_path: str) -> pd.DataFrame:
        """Load stock data from a CSV file exported from PSE Edge or similar."""
        df = pd.read_csv(csv_path)
        # Try to standardize columns
        col_map = {
            'Date': 'date',
            'Open': 'Open',
            'High': 'High',
            'Low': 'Low',
            'Close': 'Close',
            'Volume': 'Volume',
        }
        df = df.rename(columns={k: v for k, v in col_map.items() if k in df.columns})
        df['date'] = pd.to_datetime(df['date'])
        df = df[['date', 'Open', 'High', 'Low', 'Close', 'Volume']]
        df = df.set_index('date')
        return df

    def fetch_investpy(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        """Fetch daily stock data for a given symbol from investpy."""
        # investpy expects the symbol and country
        df = investpy.get_stock_historical_data(
            stock=symbol,
            country='philippines',
            from_date=pd.to_datetime(start).strftime('%d/%m/%Y'),
            to_date=pd.to_datetime(end).strftime('%d/%m/%Y')
        )
        df = df.rename(columns={
            'Open': 'Open',
            'High': 'High',
            'Low': 'Low',
            'Close': 'Close',
            'Volume': 'Volume',
        })
        df = df[['Open', 'High', 'Low', 'Close', 'Volume']]
        return df
