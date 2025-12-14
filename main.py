# main.py
# Entry point for PSE stock monitoring
from data_fetcher import DataFetcher
from analyzer import Analyzer
from recommender import Recommender
import datetime

STOCK_LIST = ['ALI', 'AC', 'SM', 'BDO', 'JFC']  # Example PSE symbols
START_DATE = (datetime.date.today() - datetime.timedelta(days=365)).isoformat()
END_DATE = datetime.date.today().isoformat()

def main():
    fetcher = DataFetcher()
    analyzer = Analyzer()
    recommender = Recommender()
    analysis_results = {}
    for symbol in STOCK_LIST:
        try:
            # Try investpy first
            data = fetcher.fetch_investpy(symbol, START_DATE, END_DATE)
            analysis = analyzer.analyze_trend(data)
            analysis_results[symbol] = analysis
        except Exception as e:
            print(f"Warning: {e}")
    if analysis_results:
        best_stock = recommender.recommend(analysis_results)
        print(f"Best stock to buy today: {best_stock}")
    else:
        print("No valid stock data available.")

if __name__ == "__main__":
    main()
