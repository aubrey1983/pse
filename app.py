from flask import Flask, request, jsonify, send_file
import os
import json
from report_generator import ReportGenerator
from portfolio_manager import PortfolioManager

app = Flask(__name__)
portfolio_mgr = PortfolioManager()
generator = ReportGenerator()

@app.route('/')
def dashboard():
    # Always regenerate for fresh data
    output_path = generator.generate_dashboard()
    # Serve the file content directly
    with open(output_path, 'r', encoding='utf-8') as f:
        return f.read()

@app.route('/api/add', methods=['POST'])
def add_position():
    data = request.json
    symbol = data.get('symbol')
    shares = float(data.get('shares', 0))
    price = float(data.get('price', 0))
    
    if not symbol or shares <= 0 or price <= 0:
        return jsonify({'success': False, 'error': 'Invalid input'}), 400
        
    portfolio_mgr.add_position(symbol, shares, price)
    return jsonify({'success': True})

@app.route('/api/remove', methods=['POST'])
def remove_position():
    data = request.json
    symbol = data.get('symbol')
    
    if not symbol:
        return jsonify({'success': False, 'error': 'Symbol required'}), 400
        
    portfolio_mgr.remove_position(symbol)
    return jsonify({'success': True})

@app.route('/api/refresh', methods=['POST'])
def refresh():
    # Just regenerating the report is enough, the client reload will fetch it
    generator.generate_dashboard()
    return jsonify({'success': True})

if __name__ == '__main__':
    print("🚀 Starting PSE Pro Dashboard...")
    print("👉 Open http://localhost:5000 in your browser")
    app.run(debug=True, port=5000)
