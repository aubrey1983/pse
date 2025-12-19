import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from analyzer import Analyzer
import os

class Backtester:
    def __init__(self):
        self.analyzer = Analyzer()
        self.tech_data = self._load_json("data/technical_data.json")
        self.fund_data = self._load_json("data/pse_fundamentals.json")
        # stock_meta not strictly needed if we iterate tech_data keys
        
        # Prepare data cache to avoid re-parsing for every date
        self.history_cache = {} 
        for symbol, data in self.tech_data.items():
            if 'history' in data:
                self.history_cache[symbol] = pd.DataFrame(data['history'])
                
    def _load_json(self, path):
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f)
        return {}

    def run_backtest(self, months_back=12, thresholds=[5, 6, 7]):
        results_md = "# Backtest Results\n\n"
        results_md += f"**Date**: {datetime.now().strftime('%Y-%m-%d')}\n"
        results_md += f"**Period**: Last {months_back} Months\n\n"

        # Generate test dates (1st and 15th of each month)
        today = datetime.now()
        checkpoints = []
        for i in range(months_back * 2, 0, -1): # Twice a month
            d = today - timedelta(days=15*i)
            # Find nearest Friday if weekend? Simplified: just use date
            checkpoints.append(d)

        print(f"Running backtest on {len(checkpoints)} checkpoints...")
        
        summary_table = "| Threshold | Win Rate | Avg Return (30d) | Market Return | Alpha | Trades |\n"
        summary_table += "|---|---|---|---|---|---|\n"

        for min_score in thresholds:
            print(f"Testing Score >= {min_score}...")
            
            total_trades = 0
            winning_trades = 0
            total_return = 0.0
            total_market_return = 0.0
            
            # Monthly breakdown
            monthly_logs = []

            for cutoff_date in checkpoints:
                date_str = cutoff_date.strftime('%Y-%m-%d')
                
                # Market Return for this period
                # We need a proxy for "Market". Let's use the average of ALL stocks available.
                period_market_gains = []
                
                # Picks
                picks = []
                
                # 1. State Reconstruction & Analysis
                for symbol, full_df in self.history_cache.items():
                    # Slice data UP TO date_str
                    # full_df['time'] is string 'YYYY-MM-DD'
                    past_data = full_df[full_df['time'] < date_str]
                    
                    if len(past_data) < 60: continue # Need enough history
                    
                    # Construct Analysis DF
                    df_analysis = past_data.copy()
                    df_analysis.rename(columns={'close': 'Close', 'open': 'Open', 'high': 'High', 'low': 'Low'}, inplace=True)
                    df_analysis['Volume'] = 1000 # Dummy
                    
                    # RUN STRATEGY
                    trend_res = self.analyzer.analyze_trend(df_analysis)
                    f_data = self.fund_data.get(symbol, {})
                    score, _ = self.analyzer.calculate_score(trend_res, f_data)
                    
                    # 2. Outcome Measurement (Next 30 Days)
                    # Find price 30 days later (or nearest available)
                    future_date_str = (cutoff_date + timedelta(days=30)).strftime('%Y-%m-%d')
                    
                    # Get future slice
                    future_data = full_df[(full_df['time'] > date_str) & (full_df['time'] <= future_date_str)]
                    
                    if future_data.empty: continue
                    
                    start_price = past_data.iloc[-1]['close']
                    end_price = future_data.iloc[-1]['close']
                    
                    if start_price == 0: continue
                    
                    pct_gain = ((end_price - start_price) / start_price) * 100.0
                    period_market_gains.append(pct_gain)
                    
                    if score >= min_score:
                        picks.append(pct_gain)

                # Aggregate Period Stats
                if picks:
                    avg_pick_gain = sum(picks) / len(picks)
                    total_trades += len(picks)
                    winning_trades += len([p for p in picks if p > 0])
                    total_return += avg_pick_gain # Sum of averages (simple cumulative)
                
                if period_market_gains:
                    avg_mkt_gain = sum(period_market_gains) / len(period_market_gains)
                    total_market_return += avg_mkt_gain

            # Calc Final Stats for Threshold
            num_periods = len(checkpoints)
            avg_return_per_period = total_return / num_periods if num_periods > 0 else 0
            avg_market_return_per_period = total_market_return / num_periods if num_periods > 0 else 0
            
            win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
            alpha = avg_return_per_period - avg_market_return_per_period
            
            summary_table += f"| {min_score} | {win_rate:.1f}% | {avg_return_per_period:+.2f}% | {avg_market_return_per_period:+.2f}% | **{alpha:+.2f}%** | {total_trades} |\n"

        results_md += "## Strategy Performance Summary\n"
        results_md += "Comparison of different Score Thresholds over 30-day holding periods.\n\n"
        results_md += summary_table
        
        results_md += "\n> **Note**: Returns are average monthly holding period returns, not compounded portfolio growth.\n"
        
        # Save Report
        with open("backtest_results.md", "w") as f:
            f.write(results_md)
            
        print("\nBacktest Complete. Results saved to backtest_results.md")
        print(summary_table)

if __name__ == "__main__":
    b = Backtester()
    b.run_backtest(months_back=12)
