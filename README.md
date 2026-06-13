# PSE Pro Dashboard
![Daily Stock Scrape](https://github.com/aubrey1983/pse/actions/workflows/daily_scrape.yml/badge.svg)

A professional-grade stock analysis and monitoring tool for the Philippine Stock Exchange (PSE).

## Features
- **Dual-Data System**:
  - **Technical Analysis**: Real-time prices, trends, RSI, Support/Resistance via Investagrams API.
  - **Fundamental Analysis**: Deep scraping of PSE Edge for P/E Ratio, EPS, Market Cap, and Dividends.
- **Dynamic Dashboard**:
  - **Market Overview**: Sortable, categorized view of all 280+ active stocks.
  - **Top Picks**: Auto-scored recommendations based on momentum and value.
  - **Dividend Gems**: Yield calculator, payout ratio analysis, and "Value Trap" detection.
  - **Interactive Charts**: Sparklines and modal views with 1-year price history.
- **Automated Workflow**:
  - Smart scraping logic with parallel processing.
  - "AI Slop" free codebase—clean, efficient, and professional.
- **Month-on-Month Gain Objective**:
  - Dedicated MoM score that rewards positive monthly return consistency, trend confirmation, manageable volatility, and clean risk/reward.
  - Dashboard Top Picks and portfolio suggestions now prioritize the MoM score while still showing the original confidence score.

## Project Structure
| File | Description |
|Data Source| |
| `data_fetcher.py` | Fetches daily technical data (Investagrams API). |
| `fetch_pse_fundamentals.py` | Scrapes official fundamentals (PSE Edge). |
| `scrape_pse_list.py` | Utilities to fetch official stock list & metadata. |
|Core Logic| |
| `analyzer.py` | Technical analysis engine (RSI, Trends, Golden Cross). |
| `recommender.py` | Scoring engine for "Top Picks" and "Dividend Gems". |
| `report_generator.py` | Generates the HTML Dashboard (`report.html`). |
|Process| |
| `main.py` | Master controller for the analysis pipeline. |
| `regenerate_report.py` | Quick utility to rebuild HTML without re-fetching data. |

## Quick Start
1. **Setup**: Install dependencies.
   ```sh
   pip install -r requirements.txt
   ```
2. **Fetch Data**:
   ```sh
   # 1. Fetch Technical Data (Fast) & Analyze
   python main.py
   
   # 2. Fetch Fundamental Data (Deep Scrape, takes ~10-15 mins)
   python fetch_pse_fundamentals.py
   ```
3. **View Report**:
   - Open `report.html` in your browser.

## Strategy Tools
```sh
# Suggest a diversified portfolio using the month-on-month gain objective
python suggest_portfolio.py --amount 10000 --stocks 5

# Backtest the month-on-month objective over recent history
python backtest.py --objective monthly_gain --months 12

# Compare against the original scoring model
python backtest.py --objective base --months 12

# Validate sector grouping metadata and write data/metadata_health.json
python validate_industries.py

# Generate daily action plan, sizing, stops, targets, and action history
python action_engine.py

# Optionally send daily_actions.md to Telegram when TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are set
python notify_actions.py
```
Backtests write objective-specific files such as `backtest_results_monthly_gain.md` and `backtest_results_base.md`.

## Tech Stack
- **Python**: Core logic, Scikit-learn/Pandas (Analysis).
- **Selenium**: Advanced scraping for PSE Edge.
- **HTML/CSS/JS**: Modern, responsive dashboard (Dark Mode, Sticky Headers).
