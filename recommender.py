# recommender.py
# Suggests the best stock to buy each day with expert financial analysis
from typing import List, Dict

class Recommender:
    def recommend_by_category(self, analysis_results: Dict[str, dict], categories: Dict[str, list]) -> Dict[str, dict]:
        """
        Recommend the best stock for each category based on Technicals & Risk/Reward.
        """
        recommendations = {}
        
        for category, symbols in categories.items():
            # Filter results for this category
            cat_results = {k: v for k, v in analysis_results.items() if k in symbols and v and v.get('last_close')}
            
            if not cat_results:
                continue
            
            best_symbol = None
            best_score = -9999
            best_analysis = None
            
            for symbol, stats in cat_results.items():
                score = 0
                
                # 1. Trend Analysis
                trend = stats.get('trend', 'Neutral')
                if trend == "Strong Uptrend": score += 20
                elif trend == "Uptrend": score += 10
                elif trend == "Downtrend": score -= 10
                elif trend == "Strong Downtrend": score -= 20
                
                # 2. RSI Analysis
                rsi = stats.get('rsi', 50)
                if 40 <= rsi <= 60: score += 5 # Sweet spot for steady growth
                elif rsi < 30: score += 10 # Oversold bounce play
                elif rsi > 70: score -= 5 # potential pullback
                
                # 3. Volatility (Stability)
                vol = stats.get('std_close', 0)
                if vol > 0:
                    # Prefer lower volatility relative to price (coefficient of variation technically, but simple vol check here)
                    # We negate vol because higher vol = lower score for "safety"
                    score -= (vol / stats['last_close']) * 100 
                
                # 4. Risk / Reward Upside
                # Distance to Resistance
                last_price = stats['last_close']
                resistance = stats.get('resistance', last_price * 1.1)
                support = stats.get('support', last_price * 0.9)
                
                if resistance <= last_price: resistance = last_price * 1.1 # Logical fix if breaking ATH
                
                upside = (resistance - last_price) / last_price
                downside = (last_price - support) / last_price
                
                if downside == 0: downside = 0.01
                rr_ratio = upside / downside
                
                score += rr_ratio * 5 # Factor in R/R
                
                if score > best_score:
                    best_score = score
                    best_symbol = symbol
                    best_analysis = stats
            
            if best_symbol and best_analysis:
                recommendations[category] = self._generate_expert_advice(best_symbol, best_analysis)
            
        return recommendations

    def _generate_expert_advice(self, symbol: str, stats: dict) -> dict:
        """Generate detailed expert advice for the selected stock."""
        last_price = stats['last_close']
        support = stats.get('support', last_price * 0.90)
        resistance = stats.get('resistance', last_price * 1.10)
        rsi = stats.get('rsi', 50)
        trend = stats.get('trend', 'Neutral')
        
        # Determine Buy/Sell Zones
        # Buy Zone: Slightly above support or at current if momentum is strong
        if "Uptrend" in trend:
            buy_low = max(support, last_price * 0.98) # Don't wait for deep support in uptrend
            buy_high = last_price * 1.01
            strategy = "Momentum Buy"
        else:
            buy_low = support
            buy_high = support * 1.03 # Accumulate near support
            strategy = "Support Play"
            
        sell_target = max(resistance, last_price * 1.05) # Minimum 5% gain target
        
        # Generate Reasons
        reasons = []
        if "Uptrend" in trend:
            reasons.append(f"Stock is in a **{trend}**, indicating strong buying pressure.")
        elif rsi < 35:
            reasons.append(f"RSI is at **{rsi:.1f}**, suggesting the stock is Oversold and due for a bounce.")
        
        reasons.append(f"Price is respecting support levels at **₱{support:.2f}**.")
        
        if (sell_target - last_price) / last_price > 0.10:
             reasons.append(f"High upside potential of **{((sell_target - last_price) / last_price)*100:.1f}%** to next resistance.")
        
        return {
            "symbol": symbol,
            "stats": stats,
            "buy_price": f"₱{buy_low:.2f} - ₱{buy_high:.2f}",
            "sell_price": f"₱{sell_target:.2f}",
            "strategy": strategy,
            "reasons": reasons,
            "highlight": f"{trend} | RSI {rsi:.1f}"
        }

    def recommend(self, analysis_results: Dict[str, dict]) -> str:
        """Legacy support"""
        return None
