import json
import argparse
from datetime import datetime
from portfolio_manager import PortfolioManager

def suggest_portfolio(investment_amount=10000, max_stocks=10, simulate=False):
    """
    Suggests a portfolio based on 'Top Pick' scores.
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
        print(f"❌ Error loading data: {e}")
        return

    print(f"\n🔍 Analyzing {len(tech_data)} stocks for Top Picks...")

    # 2. Filter & Score
    candidates = []
    
    for symbol, data in tech_data.items():
        # Basic Filter: Score >= 7 (High Confidence)
        # Also check liquidity > 1M avg value? (approx)
        
        # Recalculate Score if needed, or use what's in tech/report? 
        # Actually analyzer.py calculates it on the fly usually, 
        # but report_generator logic put it in the HTML, not the JSON?
        # Wait, technical_data.json does NOT have the score. 
        # We need to Calculate it.
        
        # We need to import Analyzer logic or simpler:
        # Re-use the Analyzer class is best.
        pass

    # Quick Analyzer instantiation
    from analyzer import Analyzer
    analyzer = Analyzer()
    
    for symbol, t_data in tech_data.items():
        if not t_data: continue
        
        f_data = fund_data.get(symbol, {})
        
        # Filter: Must not be suspended
        if f_data.get('status') == 'Suspended': continue
        
        score, reasons = analyzer.calculate_score(t_data, f_data)
        
        if score >= 6: # Threshold
             candidates.append({
                 'symbol': symbol,
                 'score': score,
                 'price': t_data['last_close'],
                 'reasons': reasons,
                 'sector': meta_data.get(symbol, {}).get('sector', 'Unknown')
             })

    # 3. Sort
    # Sort by Score (Desc), then Price (Asc - easier to buy?), or Dividends?
    # Let's sort by Score Desc
    candidates.sort(key=lambda x: x['score'], reverse=True)
    
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
        print("⚠️ No suitable stocks found with score >= 6.")
        return

    print(f"✅ Found {len(final_picks)} Top Picks for Portfolio:\n")
    
    # 5. Allocation (Equal Weight)
    allocation_per_stock = investment_amount / len(final_picks)
    
    manager = PortfolioManager() if simulate else None
    
    print(f"{'SYMBOL':<8} {'SCORE':<6} {'PRICE':<10} {'SHARES':<10} {'COST':<10} {'SECTOR'}")
    print("-" * 70)
    
    total_invested = 0
    
    for p in final_picks:
        price = p['price']
        if price <= 0: continue
        
        # Calculate shares (floor)
        shares = int(allocation_per_stock / price)
        if shares == 0: shares = 1 # Force at least 1 share if possible, or skip?
        
        cost = shares * price
        total_invested += cost
        
        print(f"{p['symbol']:<8} {p['score']:<6} ₱{price:<9.2f} {shares:<10} ₱{cost:<9.2f} {p['sector']}")
        
        if simulate:
            manager.add_position(p['symbol'], shares, price)

    print("-" * 70)
    print(f"Total Invested: ₱{total_invested:,.2f} / ₱{investment_amount:,.2f}")
    
    if simulate:
        print(f"\n🚀 Simulation Active: Added these positions to 'data/portfolio.json'.")
        print("Run 'python regenerate_report.py' to view them in dashboard.")
    else:
        print(f"\nℹ️  To actually invest this amount, run with --simulate")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--amount', type=int, default=10000, help="Investment Amount (PHP)")
    parser.add_argument('--stocks', type=int, default=5, help="Max Number of Stocks")
    parser.add_argument('--simulate', action='store_true', help="Write to portfolio.json")
    
    args = parser.parse_args()
    suggest_portfolio(args.amount, args.stocks, args.simulate)
