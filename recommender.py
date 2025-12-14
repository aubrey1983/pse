# recommender.py
# Suggests the best stock to buy each day
from typing import List, Dict

class Recommender:
    def recommend(self, analysis_results: Dict[str, dict]) -> str:
        """Recommend the best stock to buy based on analysis results."""
        # Example: pick the stock with the lowest std deviation (least volatile)
        best = min(analysis_results.items(), key=lambda x: x[1]['std_close'])
        return best[0]
