import json
import pandas as pd
from datetime import datetime, timedelta
from analyzer import Analyzer
import os

class Backtester:
    def __init__(self):
        self.analyzer = Analyzer()
        self.tech_data = self._load_json("data/technical_data.json")
        self.fund_data = self._load_json("data/pse_fundamentals.json")
        self.stock_meta = self._load_json("data/stock_metadata.json")

    def _load_json(self, path):
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f)
        return {}

    def run_backtest(self, months_back=6):
        """
        Run backtest for the last N months with multiple thresholds.
        """
        thresholds = [5, 6, 7, 8]
        
        for min_score in thresholds:
            print(f"\n{'='*40}")
            print(f"TESTING THRESHOLD: Score >= {min_score}")
            print(f"{'='*40}")
            
            # specific dates to check (1st of each month)
            today = datetime.now()
            checkpoints = []
            for i in range(months_back, 0, -1):
                d = today - timedelta(days=30*i)
                checkpoints.append(d)

            overall_results = []

            for cutoff_date in checkpoints:
                date_str = cutoff_date.strftime('%Y-%m-%d')
                
                top_picks = []
                market_returns = []

                for symbol, t_data in self.tech_data.items():
                    if not t_data.get('history'): continue
                    
                    history = t_data['history']
                    past_data = [h for h in history if h['time'] < date_str]
                    
                    if len(past_data) < 60: continue
                    
                    # Create DataFrame (Simplified state reconstruction)
                    df = pd.DataFrame(past_data)
                    df['Close'] = df['close']
                    df['Open'] = df['open']
                    df['High'] = df['high']
                    df['Low'] = df['low']
                    df['Volume'] = 1000 # Dummy volume for analyzer
                    
                    # Run Analysis on PAST data
                    trend_res = self.analyzer.analyze_trend(df)
                    f_data = self.fund_data.get(symbol, {})
                    score, reasons = self.analyzer.calculate_score(trend_res, f_data)
                    
                    if score >= min_score:
                        top_picks.append({
                            'symbol': symbol,
                            'score': score,
                            'close': trend_res['last_close']
                        })

                    # Calculate Future Return (Next 30 Days)
                    start_price = trend_res['last_close']
                    future_date = cutoff_date + timedelta(days=30)
                    future_date_str = future_date.strftime('%Y-%m-%d')
                    
                    future_candles = [h for h in history if h['time'] <= future_date_str and h['time'] > date_str]
                    
                    if not future_candles: continue 
                    
                    end_price = future_candles[-1]['close']
                    gain_pct = ((end_price - start_price) / start_price) * 100.0
                    market_returns.append(gain_pct)
                    
                    for p in top_picks:
                        if p['symbol'] == symbol:
                            p['return_30d'] = gain_pct

                if not top_picks:
                    continue
                    
                avg_pick_return = sum([p['return_30d'] for p in top_picks if 'return_30d' in p]) / len(top_picks)
                avg_market_return = sum(market_returns) / len(market_returns) if market_returns else 0.0
                
                check_res = {
                    'alpha': avg_pick_return - avg_market_return
                }
                overall_results.append(check_res)

            # Final Summary for this Threshold
            if overall_results:
                avg_alpha = sum([r['alpha'] for r in overall_results]) / len(overall_results)
                print(f"  >> Average Alpha: {avg_alpha:+.2f}%")
            else:
                print(f"  >> No valid months found.")

if __name__ == "__main__":
    b = Backtester()
    b.run_backtest()
