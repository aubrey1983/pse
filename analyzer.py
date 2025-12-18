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

    def _calculate_macd(self, df):
        """Calculate MACD (12, 26, 9)."""
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        macd = exp1 - exp2
        signal = macd.ewm(span=9, adjust=False).mean()
        return macd, signal

    def analyze_consistency(self, df: pd.DataFrame) -> dict:
        """
        Analyze Monthly consistency and returns.
        Returns: {
            'win_rate': % of positive months,
            'avg_monthly_return_pct': average monthly gain,
            'monthly_volatility': std dev of monthly returns,
            'months_analyzed': count
        }
        """
        if df is None or len(df) < 30:
            return {'win_rate': 0, 'avg_monthly_return_pct': 0, 'monthly_volatility': 0}
            
        # Resample to Monthly End
        # 'M' usually gives month end
        try:
            monthly_close = df['Close'].resample('ME').last()
            monthly_returns = monthly_close.pct_change(fill_method=None).dropna()
            
            if len(monthly_returns) < 1:
                return {'win_rate': 0, 'avg_monthly_return_pct': 0, 'monthly_volatility': 0}
            
            positive_months = len(monthly_returns[monthly_returns > 0])
            total_months = len(monthly_returns)
            
            win_rate = (positive_months / total_months) * 100.0
            avg_return = monthly_returns.mean() * 100.0
            volatility = monthly_returns.std() * 100.0
            
            return {
                'win_rate': win_rate,
                'avg_monthly_return_pct': avg_return,
                'monthly_volatility': volatility,
                'months_analyzed': total_months
            }
        except:
            return {'win_rate': 0, 'avg_monthly_return_pct': 0, 'monthly_volatility': 0}

    def analyze_trend(self, data: pd.DataFrame) -> dict:
        """Analyze stock trend and return summary statistics with technical indicators."""
        if data is None or data.empty:
            return {}

        # Calculate Indicators
        df = data.copy()
        df['SMA_50'] = df['Close'].rolling(window=50).mean()
        df['SMA_200'] = df['Close'].rolling(window=200).mean()
        df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
        df['EMA_200'] = df['Close'].ewm(span=200, adjust=False).mean()
        
        df['RSI'] = self._calculate_rsi(df['Close'])
        macd, signal = self._calculate_macd(df)
        df['MACD'] = macd
        df['MACD_Signal'] = signal
        
        last_row = df.iloc[-1]
        last_close = last_row['Close']
        
        # New: Support & Resistance
        support, resistance = self._calculate_support_resistance(df)
        
        # New: Consistency Analysis
        consistency = self.analyze_consistency(df)
        
        # determine Trend (Price vs EMA50 vs EMA200 preferred for modern analysis)
        trend_status = "Neutral"
        ema_50 = last_row['EMA_50']
        ema_200 = last_row['EMA_200']
        
        # Trend Logic using EMA
        if pd.notna(ema_50):
            if last_close > ema_50:
                trend_status = "Uptrend"
                if pd.notna(ema_200) and last_close > ema_200:
                    trend_status = "Strong Uptrend"
            elif last_close < ema_50:
                trend_status = "Downtrend"
                if pd.notna(ema_200) and last_close < ema_200:
                    trend_status = "Strong Downtrend"
        
        # Sparkline Data (Last 30 closes)
        sparkline_data = df['Close'].tail(30).tolist()
        
        # Full History for Charts
        history_df = df.tail(252)
        history_data = []
        for idx, row in history_df.iterrows():
            date_str = idx.strftime('%Y-%m-%d') if isinstance(idx, pd.Timestamp) else str(idx)
            history_data.append({
                'time': date_str,
                'open': row.get('Open', row['Close']),
                'high': row.get('High', row['Close']),
                'low': row.get('Low', row['Close']),
                'close': row['Close']
            })
        
        # Golden Cross (SMA 50 crosses above SMA 200 - Classic)
        sma_50 = last_row['SMA_50']
        sma_200 = last_row['SMA_200']
        golden_cross = (pd.notna(sma_50) and pd.notna(sma_200) and sma_50 > sma_200)
        
        # Volume Spike (Volume > 2x 20-day Average)
        vol_sma_20 = df['Volume'].rolling(window=20).mean().iloc[-1]
        current_vol = last_row['Volume']
        volume_spike = False
        if pd.notna(vol_sma_20) and vol_sma_20 > 0:
            if current_vol > (2.0 * vol_sma_20):
                volume_spike = True
            
        result = {
            'last_close': last_close,
            'rsi': last_row['RSI'] if pd.notna(last_row['RSI']) else 50.0,
            'sma_50': sma_50 if pd.notna(sma_50) else 0.0,
            'sma_200': sma_200 if pd.notna(sma_200) else 0.0,
            'ema_50': ema_50 if pd.notna(ema_50) else 0.0,
            'ema_200': ema_200 if pd.notna(ema_200) else 0.0,
            'macd': last_row['MACD'] if pd.notna(last_row['MACD']) else 0.0,
            'macd_signal': last_row['MACD_Signal'] if pd.notna(last_row['MACD_Signal']) else 0.0,
            'trend': trend_status,
            'support': support,
            'resistance': resistance,
            'win_rate': consistency['win_rate'],
            'avg_monthly_return': consistency['avg_monthly_return_pct'],
            'monthly_volatility': consistency['monthly_volatility'],
            'sparkline': sparkline_data,
            'history': history_data,
            'golden_cross': golden_cross,
            'volume_spike': volume_spike,
            'volume_avg': vol_sma_20 if pd.notna(vol_sma_20) else 0.0
        }
        return result

    def calculate_score(self, tech_data: dict, fund_data: dict) -> tuple:
        """
        Calculate 'Top Pick' score based on technical and fundamental factors.
        Returns: (score, score_reasons_list)
        """
        score = 0
        score_reasons = []
        
        if not tech_data:
            return 0, []

        # 1. Trend (Technical)
        trend = tech_data.get('trend', '')
        last_close = tech_data.get('last_close', 0)
        
        # Penalize Downtrends (Don't catch falling knives)
        if "Downtrend" in trend:
            score -= 5
            score_reasons.append("Downtrend (-5)")
        else:
            if "Strong Uptrend" in trend: 
                score += 1 # Reduced to +1 to avoid buying extended tops
                score_reasons.append("Strong Uptrend (+1)")
            elif "Uptrend" in trend: 
                score += 1
                score_reasons.append("Uptrend (+1)")
            
            # EMA Confirmation
            ema_50 = tech_data.get('ema_50', 0)
            if ema_50 and last_close > ema_50:
                score += 1
                score_reasons.append("Above EMA 50 (+1)")
                
            # Golden Cross (Start of Trend)
            if tech_data.get('golden_cross'):
                score += 3
                score_reasons.append("Golden Cross (+3)")

        # 2. Momentum (Technical)

        # 2. Momentum (Technical)
        rsi = tech_data.get('rsi', 50)
        if 40 < rsi < 70 and "Uptrend" in trend:
            score += 1
            score_reasons.append("Healthy Momentum (+1)")
        
        macd_val = tech_data.get('macd', 0)
        macd_sig = tech_data.get('macd_signal', 0)
        if macd_val > macd_sig:
            score += 1
            score_reasons.append("MACD Bullish (+1)")
        
        # 3. Value (Fundamental)
        if fund_data:
            pe = fund_data.get('pe_ratio')
            try: pe = float(pe)
            except: pe = None
            
            if pe and 0 < pe < 15: 
                score += 2
                score_reasons.append(f"Undervalued P/E {pe:.1f} (+2)")
            
            # 4. Income (Quarterly Dividends)
            div_freq = fund_data.get('div_freq', '-')
            if div_freq == "Quarterly":
                score += 2
                score_reasons.append("Quarterly Dividends (+2)")
        
        # 5. Consistency (Monthly Win Rate)
        win_rate = tech_data.get('win_rate', 0)
        if win_rate > 60:
            score += 3
            score_reasons.append(f"Highly Consistent ({win_rate:.0f}% Win) (+3)")
            
        return score, score_reasons
