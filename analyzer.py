# analyzer.py
# Analyzes stock trends
import pandas as pd

class Analyzer:
    def analyze_trend(self, data: pd.DataFrame) -> dict:
        """Analyze stock trend and return summary statistics."""
        trend = {
            'mean_close': data['Close'].mean(),
            'std_close': data['Close'].std(),
            'last_close': data['Close'].iloc[-1] if not data.empty else None
        }
        return trend
