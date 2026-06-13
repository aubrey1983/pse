import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from analyzer import Analyzer
import os
import argparse

class Backtester:
    def __init__(self):
        self.analyzer = Analyzer()
        self.tech_data = self._load_json("data/technical_data.json")
        self.fund_data = self._load_json("data/pse_fundamentals.json")
        # stock_meta not strictly needed if we iterate tech_data keys
        
        # Prepare data cache to avoid re-parsing for every date
        self.history_cache = {} 
        self.latest_history_date = None
        for symbol, data in self.tech_data.items():
            if 'history' in data:
                df = pd.DataFrame(data['history'])
                self.history_cache[symbol] = df
                if not df.empty and 'time' in df:
                    dates = pd.to_datetime(df['time'], errors='coerce').dropna()
                    if not dates.empty:
                        latest = dates.max().to_pydatetime()
                        if self.latest_history_date is None or latest > self.latest_history_date:
                            self.latest_history_date = latest
                
    def _load_json(self, path):
        if os.path.exists(path):
            with open(path, 'r') as f:
                return json.load(f)
        return {}

    def _score(self, tech_data, fund_data, objective):
        if objective == "monthly_gain":
            return self.analyzer.calculate_monthly_gain_score(tech_data, fund_data)
        return self.analyzer.calculate_score(tech_data, fund_data)

    def run_backtest(self, months_back=12, thresholds=None, objective="monthly_gain"):
        if thresholds is None:
            thresholds = [35, 40, 45, 50] if objective == "monthly_gain" else [5, 6, 7]

        results_md = "# Backtest Results\n\n"
        results_md += f"**Date**: {datetime.now().strftime('%Y-%m-%d')}\n"
        results_md += f"**Period**: Last {months_back} Months\n\n"
        results_md += f"**Objective**: {objective.replace('_', ' ').title()}\n\n"

        # Generate test dates (1st and 15th of each month)
        # Anchor to available data, not wall-clock time, so stale checked-in
        # datasets still produce valid forward-return windows.
        today = self.latest_history_date - timedelta(days=30) if self.latest_history_date else datetime.now()
        checkpoints = []
        for i in range(months_back * 2, 0, -1): # Twice a month
            d = today - timedelta(days=15*i)
            # Find nearest Friday if weekend? Simplified: just use date
            checkpoints.append(d)

        print(f"Running {objective} backtest on {len(checkpoints)} checkpoints...")
        
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
                    score, _ = self._score(trend_res, f_data, objective)
                    
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
        output_file = f"backtest_results_{objective}.md"
        with open(output_file, "w") as f:
            f.write(results_md)
            
        print(f"\nBacktest Complete. Results saved to {output_file}")
        print(summary_table)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--months', type=int, default=12, help="Months to backtest")
    parser.add_argument(
        '--objective',
        choices=['monthly_gain', 'base'],
        default='monthly_gain',
        help="Strategy objective to test"
    )
    parser.add_argument(
        '--thresholds',
        nargs='*',
        type=int,
        help="Optional score thresholds to test"
    )
    args = parser.parse_args()

    b = Backtester()
    b.run_backtest(months_back=args.months, thresholds=args.thresholds, objective=args.objective)
