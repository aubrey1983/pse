import argparse
from portfolio_manager import PortfolioManager
from analyzer import Analyzer
import pandas as pd
import json

def main():
    parser = argparse.ArgumentParser(description="PSE Portfolio Manager")
    parser.add_argument('action', choices=['add', 'remove', 'list', 'update'], help="Action to perform")
    parser.add_argument('--symbol', '-s', help="Stock Symbol")
    parser.add_argument('--price', '-p', type=float, help="Average Buy Price")
    parser.add_argument('--shares', '-q', type=float, help="Number of Shares")
    
    args = parser.parse_args()
    
    manager = PortfolioManager()
    
    if args.action == 'add':
        if not args.symbol or not args.price or not args.shares:
            print("❌ Error: --symbol, --price, and --shares are required for 'add'.")
            return
        manager.add_position(args.symbol, args.shares, args.price)
        
    elif args.action == 'remove':
        if not args.symbol:
            print("❌ Error: --symbol is required for 'remove'.")
            return
        manager.remove_position(args.symbol)
        
    elif args.action == 'list':
        # Load latest prices for context
        try:
            with open('data/technical_data.json', 'r') as f:
                tech_data = json.load(f)
                # Helper to flatten price dict
                prices = {k: v.get('last_close', 0) for k, v in tech_data.items()}
        except:
            prices = {}
            
        summary = manager.get_portfolio_summary(prices)
        
        print(f"\n{'='*60}")
        print(f" PORTFOLIO SUMMARY")
        print(f"{'='*60}")
        print(f" Total Equity:   ₱{summary['total_equity']:,.2f}")
        print(f" Cost Basis:     ₱{summary['total_cost']:,.2f}")
        print(f" Gain/Loss:      ₱{summary['total_gain_loss']:,.2f} ({summary['total_gain_loss_pct']:.2f}%)")
        print(f"{'-'*60}")
        print(f" {'SYMBOL':<10} {'SHARES':<10} {'AVG PRICE':<12} {'CURRENT':<10} {'G/L %':<10}")
        print(f"{'-'*60}")
        
        for p in summary['positions']:
            color = "🟢" if p['gain_loss'] >= 0 else "🔴"
            print(f" {color} {p['symbol']:<8} {p['shares']:<10,.0f} ₱{p['avg_price']:<11.2f} ₱{p['current_price']:<9.2f} {p['gain_loss_pct']:>6.2f}%")
        print(f"{'='*60}\n")
        
    elif args.action == 'update':
        # Interactive Mode
        symbol = input("Stock Symbol: ").upper()
        shares = float(input("Shares to Add: "))
        price = float(input("Buy Price: "))
        manager.add_position(symbol, shares, price)

if __name__ == "__main__":
    main()
