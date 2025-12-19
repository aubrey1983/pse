import json
import os
from datetime import datetime

class PortfolioManager:
    def __init__(self, data_file="data/portfolio.json"):
        self.data_file = data_file
        self.portfolio = self.load_portfolio()

    def load_portfolio(self):
        """Load portfolio data from JSON file."""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def save_portfolio(self):
        """Save portfolio data to JSON file."""
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        with open(self.data_file, 'w') as f:
            json.dump(self.portfolio, f, indent=4)

    def add_position(self, symbol, shares, avg_price):
        """Add or update a stock position."""
        symbol = symbol.upper()
        
        if symbol in self.portfolio:
            # Weighted Average Price Calculation if adding to existing
            current_shares = self.portfolio[symbol]['shares']
            current_avg = self.portfolio[symbol]['avg_price']
            
            total_shares = current_shares + shares
            new_avg = ((current_shares * current_avg) + (shares * avg_price)) / total_shares
            
            self.portfolio[symbol] = {
                'shares': total_shares,
                'avg_price': new_avg,
                'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        else:
            self.portfolio[symbol] = {
                'shares': float(shares),
                'avg_price': float(avg_price),
                'date_added': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'last_updated': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        
        self.save_portfolio()
        print(f"✅ Position for {symbol} updated. Total Shares: {self.portfolio[symbol]['shares']:.0f} @ ₱{self.portfolio[symbol]['avg_price']:.2f}")

    def remove_position(self, symbol):
        """Remove a stock position."""
        symbol = symbol.upper()
        if symbol in self.portfolio:
            del self.portfolio[symbol]
            self.save_portfolio()
            print(f"🗑️ Removed {symbol} from portfolio.")
        else:
            print(f"⚠️ {symbol} not found in portfolio.")

    def get_portfolio_summary(self, current_prices):
        """
        Calculate portfolio performance based on current market prices.
        current_prices: dict { 'SYMBOL': price, ... }
        """
        summary = {
            'total_equity': 0.0,
            'total_cost': 0.0,
            'total_gain_loss': 0.0,
            'total_gain_loss_pct': 0.0,
            'positions': []
        }
        
        for symbol, data in self.portfolio.items():
            shares = data['shares']
            avg_price = data['avg_price']
            current_price = current_prices.get(symbol, 0.0)
            
            if current_price == 0:
                # Fallback if price missing
                current_price = avg_price 
            
            market_value = shares * current_price
            cost_basis = shares * avg_price
            gain_loss = market_value - cost_basis
            gain_loss_pct = ((current_price - avg_price) / avg_price) * 100.0 if avg_price > 0 else 0.0
            
            summary['total_equity'] += market_value
            summary['total_cost'] += cost_basis
            
            summary['positions'].append({
                'symbol': symbol,
                'shares': shares,
                'avg_price': avg_price,
                'current_price': current_price,
                'market_value': market_value,
                'gain_loss': gain_loss,
                'gain_loss_pct': gain_loss_pct
            })
            
        summary['total_gain_loss'] = summary['total_equity'] - summary['total_cost']
        if summary['total_cost'] > 0:
            summary['total_gain_loss_pct'] = (summary['total_gain_loss'] / summary['total_cost']) * 100.0
            
        return summary
