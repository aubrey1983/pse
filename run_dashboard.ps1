Stop-Process -Name "python" -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1
python app.py
