@echo off
echo ==========================================
echo Starting PSE Stock Analyzer (Dual Mode)
echo ==========================================

echo 1. Launching Fast Technical Analyzer...
start "PSE Technical Analyzer" cmd /k "python main.py"

echo 2. Launching Slow Fundamental Fetcher (Selenium)...
start "PSE Fundamental Fetcher" cmd /k "python fetch_pse_fundamentals.py"

echo ==========================================
echo Both processes started!
echo The Dashboard will open automatically when main.py finishes.
echo Fundamentals will update live.
echo ==========================================
pause
