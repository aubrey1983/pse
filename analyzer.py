# analyzer.py
# Analyzes stock trends with enhanced financial indicators
import pandas as pd
import numpy as np

class Analyzer:
    def _calculate_rsi(self, series, period=14):
        """Calculate Relative Strength Index (RSI)."""
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / loss
        # Handle division by zero (if loss is 0, rs is inf)
        rs = rs.replace([np.inf, -np.inf], np.nan)
        
        rsi = 100 - (100 / (1 + rs))
        return rsi.fillna(50) # Return Neutral 50 if RSI calculation fails


    def _calculate_support_resistance(self, df: pd.DataFrame, window=60) -> tuple:
        """
        Calculate potential Support and Resistance levels.
        Support = Lowest Low of last 'window' days (~3 months)
        Resistance = Highest High of last 'window' days (~3 months)
        """
        if len(df) < window:
            window = len(df)
            
        recent_data = df.tail(window)
        support = recent_data['Low'].min()
        resistance = recent_data['High'].max()
        
        return support, resistance

    def analyze_trend(self, data: pd.DataFrame) -> dict:
        """Analyze stock trend and return summary statistics with technical indicators."""
        if data is None or data.empty:
            return {}

        # Calculate Indicators
        # We use .copy() to avoid SettingWithCopyWarning if data is a slice
        df = data.copy()
        df['SMA_50'] = df['Close'].rolling(window=50).mean()
        df['SMA_200'] = df['Close'].rolling(window=200).mean()
        df['RSI'] = self._calculate_rsi(df['Close'])
        
        last_row = df.iloc[-1]
        last_close = last_row['Close']
        
        # New: Support & Resistance
        support, resistance = self._calculate_support_resistance(df)
        
        # Volatility (Standard Deviation of returns * sqrt(252) for annualized, 
        # but here simply std of price for simple "instability" measure or ATR could be better.
        # Sticking to price std for now as requested by previous codebase style, but let's improve it slightly.)
        # Let's use ATR (Average True Range) for a better "Volatility" measure if possible, 
        # but to keep it simple and consistent with previous "std_close", we'll just check std of close over 20 days.
        std_close = df['Close'].tail(20).std()
        
        # Determine Trend (Price vs SMA50 vs SMA200)
        trend_status = "Neutral"
        sma_50 = last_row['SMA_50']
        sma_200 = last_row['SMA_200']
        
        if pd.notna(sma_50):
            if last_close > sma_50:
                trend_status = "Uptrend"
                if pd.notna(sma_200) and last_close > sma_200:
                    trend_status = "Strong Uptrend"
            elif last_close < sma_50:
                trend_status = "Downtrend"
                if pd.notna(sma_200) and last_close < sma_200:
                    trend_status = "Strong Downtrend"
            
        result = {
            'last_close': last_close,
            'rsi': last_row['RSI'] if pd.notna(last_row['RSI']) else 50.0,
            'sma_50': sma_50 if pd.notna(sma_50) else 0.0,
            'sma_200': sma_200 if pd.notna(sma_200) else 0.0,
            'trend': trend_status,
            'support': support,
            'resistance': resistance,
            'std_close': std_close if pd.notna(std_close) else 0.0
        }
        return result
