import json
import argparse
from datetime import datetime
from portfolio_manager import PortfolioManager

def suggest_portfolio(investment_amount=10000, max_stocks=10, simulate=False, objective="monthly_gain"):
    """
    Suggests a portfolio based on the selected objective.
    If simulate=True, adds them to the persistent portfolio.json with 'investment_amount' allocated.
    """
    
    # 1. Load Data
    try:
        with open('data/technical_data.json', 'r') as f:
            tech_data = json.load(f)
        with open('data/stock_metadata.json', 'r') as f:
            meta_data = json.load(f)
        with open('data/pse_fundamentals.json', 'r') as f:
            fund_data = json.load(f)
    except Exception as e:
        print(f"[ERROR] Error loading data: {e}")
        return

    print(f"\nAnalyzing {len(tech_data)} stocks for {objective.replace('_', ' ').title()} picks...")

    # 2. Filter & Score
    candidates = []

    # Quick Analyzer instantiation
    from analyzer import Analyzer
    analyzer = Analyzer()
    
    for symbol, t_data in tech_data.items():
        if not t_data: continue
        
        f_data = fund_data.get(symbol, {})
        
        # Filter: Must not be suspended
        if f_data.get('status') == 'Suspended': continue
        
        base_score, base_reasons = analyzer.calculate_score(t_data, f_data)
        if objective == "base":
            score, reasons = base_score, base_reasons
            threshold = 6
        else:
            score, reasons = analyzer.calculate_monthly_gain_score(t_data, f_data)
            threshold = 35
        
        if score >= threshold:
             candidates.append({
                 'symbol': symbol,
                 'score': score,
                 'base_score': base_score,
                 'price': t_data['last_close'],
                 'reasons': reasons,
                 'win_rate': t_data.get('win_rate', 0),
                 'avg_monthly_return': t_data.get('avg_monthly_return', 0),
                 'sector': meta_data.get(symbol, {}).get('sector', 'Unknown')
             })

    # 3. Sort
    candidates.sort(key=lambda x: (x['score'], x['base_score']), reverse=True)
    
    # 4. Diversification (Max 2 per sector)
    final_picks = []
    sector_counts = {}
    
    for c in candidates:
        if len(final_picks) >= max_stocks: break
        
        sec = c['sector']
        if sector_counts.get(sec, 0) >= 2: continue # Skip if sector full
        
        final_picks.append(c)
        sector_counts[sec] = sector_counts.get(sec, 0) + 1
        
    if not final_picks:
        print("[WARN] No suitable stocks found for the selected objective.")
        return

    print(f"[OK] Found {len(final_picks)} picks for Portfolio:\n")
    
    # 5. Allocation (Equal Weight)
    allocation_per_stock = investment_amount / len(final_picks)
    
    manager = PortfolioManager() if simulate else None
    
    print(f"{'SYMBOL':<8} {'MOM':<5} {'BASE':<5} {'AVG/MO':<8} {'WIN':<6} {'PRICE':<10} {'SHARES':<8} {'COST':<10} {'SECTOR'}")
    print("-" * 95)
    
    total_invested = 0
    
    for p in final_picks:
        price = p['price']
        if price <= 0: continue
        
        # Calculate shares (floor)
        shares = int(allocation_per_stock / price)
        if shares == 0: shares = 1 # Force at least 1 share if possible, or skip?
        
        cost = shares * price
        total_invested += cost
        
        print(
            f"{p['symbol']:<8} {p['score']:<5} {p['base_score']:<5} "
            f"{p['avg_monthly_return']:+.1f}%   {p['win_rate']:.0f}%   "
            f"PHP {price:<6.2f} {shares:<8} PHP {cost:<8.2f} {p['sector']}"
        )
        
        if simulate:
            manager.add_position(p['symbol'], shares, price)

    print("-" * 95)
    print(f"Total Invested: PHP {total_invested:,.2f} / PHP {investment_amount:,.2f}")
    
    if simulate:
        print(f"\nSimulation Active: Added these positions to 'data/portfolio.json'.")
        print("Run 'python regenerate_report.py' to view them in dashboard.")
    else:
        print(f"\nTo write this allocation to the local portfolio file, run with --simulate.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--amount', type=int, default=10000, help="Investment Amount (PHP)")
    parser.add_argument('--stocks', type=int, default=5, help="Max Number of Stocks")
    parser.add_argument('--simulate', action='store_true', help="Write to portfolio.json")
    parser.add_argument(
        '--objective',
        choices=['monthly_gain', 'base'],
        default='monthly_gain',
        help="Optimization objective. monthly_gain targets month-on-month performance; base uses the original score."
    )
    
    args = parser.parse_args()
    suggest_portfolio(args.amount, args.stocks, args.simulate, args.objective)
