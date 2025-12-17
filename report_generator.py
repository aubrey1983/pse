# report_generator.py
# Generates modern HTML dashboard for stock analysis
import datetime
import webbrowser
import os
import json
from typing import Dict
from stock_data import STOCK_CATEGORIES

class ReportGenerator:
    def load_json(self, filepath):
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}

    def generate_dashboard(self, output_file: str = "stock_analysis_report.html"):
        """Generate a modern HTML dashboard merging Technical and Fundamental data."""
        
        # Load Data
        tech_data = self.load_json("data/technical_data.json")
        fund_data = self.load_json("data/fundamental_data.json")
        metadata = self.load_json("data/metadata.json")
        
        # Merge Data per Industry
        grouped_data = {cat: [] for cat in STOCK_CATEGORIES}
        top_picks = []
        div_picks = []
        
        for cat, symbols in STOCK_CATEGORIES.items():
            for symbol in symbols:
                if symbol in tech_data:
                    t = tech_data[symbol]
                    f = fund_data.get(symbol, {})
                    
                    # Create combined object
                    item = {
                        "symbol": symbol,
                        "tech": t,
                        "fund": f,
                        "score": 0, # Top Pick Score
                        "div_score": 0, # Dividend Score
                        "payout_ratio": 0
                    }
                    
                    # --- TOP PICK SCORING ---
                    score = 0
                    trend = t.get('trend', '')
                    if "Strong Uptrend" in trend: score += 3
                    elif "Uptrend" in trend: score += 1
                    
                    rsi = t.get('rsi', 50)
                    if rsi < 30: score += 2 # Oversold opportunity
                    if rsi > 70 and "Strong Uptrend" in trend: score += 1 # Momentum
                    
                    pe = f.get('pe_ratio')
                    try: pe = float(pe)
                    except: pe = None
                    
                    if pe and 0 < pe < 15: score += 2
                    
                    item['score'] = score
                    grouped_data[cat].append(item)
                    
                    if score >= 3:
                        top_picks.append(item)

                    # --- DIVIDEND GEM SCORING ---
                    # Proxy for: Elastic Net (Stability), LightGBM (Quality), Survival (Cut Risk)
                    div_score = 0
                    yield_val = f.get('div_yield') # e.g. 5.5
                    eps = f.get('eps')
                    price = t.get('last_close', 0)
                    
                    if yield_val:
                        try:
                            # Quality (Yield Gate)
                            if yield_val >= 3.0: div_score += 20
                            if yield_val >= 5.0: div_score += 10
                            
                            # Cut Risk (Payout Ratio)
                            # DPS = (Yield/100) * Price
                            # Payout = DPS / EPS
                            dps = (yield_val / 100.0) * price
                            if eps and eps > 0:
                                payout = (dps / eps) * 100.0
                                item['payout_ratio'] = payout
                                
                                if payout < 90: div_score += 20    # Safe
                                if payout < 60: div_score += 20    # Very Safe (Retained Earnings)
                                if payout > 100: div_score -= 50   # Danger Zone (Paying from debt/assets)
                            elif eps and eps < 0:
                                div_score -= 50 # Unprofitable but paying dividends = Danger
                            
                            # Stability (Technical Trend)
                            if "Uptrend" in trend: div_score += 20
                            elif "Downtrend" in trend: div_score -= 10
                            
                            item['div_score'] = div_score
                            
                            if div_score >= 10:
                                div_picks.append(item)
                        except:
                            pass

        # Sort Picks
        top_picks.sort(key=lambda x: x['score'], reverse=True)
        top_picks = top_picks[:20]
        
        div_picks.sort(key=lambda x: x['div_score'], reverse=True)

        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        tech_prog = metadata.get('technical_progress', {})
        fund_prog = metadata.get('fundamentals_progress', {})
        
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>PSE Analytics Terminal</title>
            <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Inter:wght@400;600;800&display=swap" rel="stylesheet">
            <style>
                :root {{
                    /* Fintech Pro Theme */
                    --bg-app: #0f172a;
                    --bg-panel: #1e293b;
                    --bg-panel-hover: #334155;
                    
                    --border: #334155;
                    
                    --text-primary: #f1f5f9;
                    --text-secondary: #94a3b8;
                    --text-tertiary: #64748b;
                    
                    --accent: #3b82f6; /* Blue */
                    --accent-glow: rgba(59, 130, 246, 0.3);
                    
                    --up: #10b981; /* Green */
                    --down: #ef4444; /* Red */
                    --neutral: #64748b;
                    
                    --font-sans: 'Inter', sans-serif;
                    --font-mono: 'JetBrains Mono', monospace;
                    
                    --sidebar-w: 260px;
                }}
                
                * {{ box-sizing: border-box; }}
                
                body {{
                    font-family: var(--font-sans);
                    background-color: var(--bg-app);
                    color: var(--text-primary);
                    margin: 0;
                    height: 100vh;
                    display: flex;
                    overflow: hidden;
                }}
                
                /* Layout */
                .app-container {{
                    display: flex;
                    width: 100%;
                }}
                
                aside {{
                    width: var(--sidebar-w);
                    background: var(--bg-panel);
                    border-right: 1px solid var(--border);
                    display: flex;
                    flex-direction: column;
                    padding: 1.5rem 1rem;
                    flex-shrink: 0;
                }}
                
                main {{
                    flex: 1;
                    overflow-y: auto;
                    display: block; /* Simpler layout to avoid flex collapse */
                    position: relative;
                }}
                
                /* Typography & Utilites */
                h1, h2, h3 {{ margin: 0; font-weight: 800; }}
                .mono {{ font-family: var(--font-mono); }}
                .text-green {{ color: var(--up); }}
                .text-red {{ color: var(--down); }}
                .text-muted {{ color: var(--text-secondary); }}
                
                /* Sidebar Components */
                .brand {{
                    font-size: 1.25rem;
                    color: var(--accent);
                    margin-bottom: 2.5rem;
                    display: flex;
                    align-items: center;
                    gap: 0.5rem;
                    text-transform: uppercase;
                    letter-spacing: 1px;
                }}
                
                .nav-group-title {{
                    font-size: 0.7rem;
                    text-transform: uppercase;
                    color: var(--text-tertiary);
                    margin: 1rem 0 0.5rem 0.5rem;
                    letter-spacing: 0.05em;
                }}
                
                .nav-item {{
                    padding: 0.6rem 0.75rem;
                    margin-bottom: 2px;
                    border-radius: 4px;
                    cursor: pointer;
                    color: var(--text-secondary);
                    font-size: 0.9rem;
                    font-weight: 500;
                    transition: 0.2s all;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }}
                
                .nav-item:hover {{
                    background: var(--bg-panel-hover);
                    color: var(--text-primary);
                }}
                
                .nav-item.active {{
                    background: rgba(59, 130, 246, 0.15);
                    color: var(--accent);
                    border-left: 3px solid var(--accent);
                }}
                
                .nav-badge {{
                    font-size: 0.7rem;
                    background: var(--bg-app);
                    padding: 1px 6px;
                    border-radius: 10px;
                    color: var(--text-tertiary);
                }}
                
                .search-box {{
                    background: var(--bg-app);
                    border: 1px solid var(--border);
                    padding: 0.6rem;
                    border-radius: 6px;
                    color: var(--text-primary);
                    width: 100%;
                    margin-bottom: 1.5rem;
                    font-family: var(--font-sans);
                    outline: none;
                }}
                .search-box:focus {{ border-color: var(--accent); box-shadow: 0 0 0 2px var(--accent-glow); }}
                
                /* Header */
                header {{
                    position: sticky; top: 0; z-index: 10;
                    background: rgba(15, 23, 42, 0.95);
                    backdrop-filter: blur(8px);
                    border-bottom: 1px solid var(--border);
                    padding: 1rem 2rem;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                }}
                
                .status-pill {{
                    font-size: 0.75rem;
                    padding: 0.25rem 0.75rem;
                    border-radius: 20px;
                    background: rgba(16, 185, 129, 0.1);
                    color: var(--up);
                    border: 1px solid rgba(16, 185, 129, 0.2);
                    display: flex;
                    align-items: center;
                    gap: 0.4rem;
                }}
                .status-dot {{ width: 6px; height: 6px; background: var(--up); border-radius: 50%; box-shadow: 0 0 8px var(--up); }}
                
                /* Content Grid */
                .section {{ display: none; padding: 2rem; }}
                .section.active {{ display: block; }}
                
                .dashboard-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                    gap: 1.5rem;
                }}
                
                /* Stock Card */
                .card {{
                    background: var(--bg-panel);
                    border: 1px solid var(--border);
                    border-radius: 6px;
                    padding: 1.25rem;
                    transition: transform 0.2s, box-shadow 0.2s;
                    position: relative;
                    overflow: hidden;
                }}
                
                .card:hover {{
                    transform: translateY(-2px);
                    box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
                    border-color: var(--text-tertiary);
                }}
                
                .card-header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-start;
                    margin-bottom: 1rem;
                }}
                
                .symbol {{
                    font-size: 1.5rem;
                    font-weight: 800;
                    letter-spacing: -1px;
                }}
                
                .price {{
                    font-size: 1.25rem;
                    font-weight: 700;
                    text-align: right;
                }}
                
                .trend-badge {{
                    font-size: 0.7rem;
                    text-transform: uppercase;
                    font-weight: 700;
                    padding: 2px 6px;
                    border-radius: 4px;
                    background: rgba(255,255,255,0.05);
                }}
                .trend-badge.green {{ color: var(--up); background: rgba(16, 185, 129, 0.15); }}
                .trend-badge.red {{ color: var(--down); background: rgba(239, 68, 68, 0.15); }}
                
                /* Metrics Grid within Card */
                .metrics {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 1rem;
                    margin-top: 1rem;
                    padding-top: 1rem;
                    border-top: 1px solid var(--border);
                }}
                
                .metric {{ display: flex; flex-direction: column; }}
                .metric-label {{ font-size: 0.7rem; color: var(--text-tertiary); text-transform: uppercase; margin-bottom: 2px; }}
                .metric-val {{ font-size: 0.9rem; font-weight: 600; color: var(--text-primary); }}
                
                /* Tables */
                .table-container {{
                    background: var(--bg-panel);
                    border: 1px solid var(--border);
                    border-radius: 8px;
                    overflow: hidden;
                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.2);
                }}
                
                table {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; }}
                
                th {{
                    background: rgba(15, 23, 42, 0.5);
                    text-align: left;
                    padding: 1rem;
                    color: var(--text-secondary);
                    font-size: 0.8rem;
                    text-transform: uppercase;
                    border-bottom: 1px solid var(--border);
                    cursor: pointer;
                    user-select: none;
                }}
                th:hover {{ color: var(--text-primary); }}
                
                td {{
                    padding: 1rem;
                    border-bottom: 1px solid var(--border);
                    color: var(--text-primary);
                }}
                
                tr:last-child td {{ border-bottom: none; }}
                tr:hover {{ background: rgba(255,255,255,0.02); }}
                
                /* Scrollbar */
                ::-webkit-scrollbar {{ width: 8px; }}
                ::-webkit-scrollbar-track {{ background: var(--bg-app); }}
                ::-webkit-scrollbar-thumb {{ background: var(--bg-panel-hover); border-radius: 4px; }}
                ::-webkit-scrollbar-thumb:hover {{ background: var(--text-tertiary); }}
                
            </style>
        </head>
        <body>
            <nav>
                <aside>
                    <div class="brand">
                        <span>PSE</span><span style="color:white">TERMINAL</span>
                    </div>
                    
                    <input type="text" id="searchInput" class="search-box" placeholder="SEARCH (CMD+K)" onkeyup="filterStocks()">
                    
                    <div class="nav-item active" onclick="showSection('overview')">
                        <span>MARKET OVERVIEW</span>
                    </div>
                    
                    <div class="nav-group-title">OPPORTUNITIES</div>
                    <div class="nav-item" onclick="showSection('top_picks')">
                        <span>Top Picks</span> <span class="nav-badge">{len(top_picks)}</span>
                    </div>
                    <div class="nav-item" onclick="showSection('dividends')">
                        <span>Dividend Gems</span> <span class="nav-badge" style="color:var(--accent)">{len(div_picks)}</span>
                    </div>
                    
                    <div class="nav-group-title">SECTORS</div>
        """
        
        # Sidebar Links
        for cat, items in grouped_data.items():
             cat_id = cat.replace(" ", "_").replace("&", "")
             html_content += f'<div class="nav-item" onclick="showSection(\'{cat_id}\')"><span>{cat}</span> <span class="nav-badge">{len(items)}</span></div>'
            
        html_content += f"""
                </aside>
            </nav>
            
            <main>
                <header>
                    <div class="mono" style="font-size:0.8rem; color:var(--text-secondary);">
                        MARKET STATUS: <span style="color:var(--text-primary)">OPEN</span> | {timestamp}
                    </div>
                    <div class="status-pill">
                        <div class="status-dot"></div>
                        <span>SYSTEM ONLINE</span>
                    </div>
                </header>
                
                <!-- MARKET OVERVIEW (Landing) -->
                <div id="overview" class="section active">
                    <h2 style="margin-bottom:1.5rem;">Market Overview</h2>
                    <div class="dashboard-grid">
                        <div class="card" style="border-left: 4px solid var(--up);">
                            <div class="metric-label">Top Gainer Potential</div>
                            <div class="symbol" style="margin-top:0.5rem">{top_picks[0]['symbol'] if top_picks else 'N/A'}</div>
                            <div class="text-green mono" style="font-size:1.1rem; margin-top:0.25rem;">Strong Uptrend</div>
                        </div>
                        <div class="card" style="border-left: 4px solid var(--accent);">
                            <div class="metric-label">Highest Yield (Safe)</div>
                            <div class="symbol" style="margin-top:0.5rem">{div_picks[0]['symbol'] if div_picks else 'N/A'}</div>
                             <div class="text-green mono" style="font-size:1.1rem; margin-top:0.25rem;">{div_picks[0]['fund'].get('div_yield') if div_picks else 0}% Yield</div>
                        </div>
                         <div class="card">
                            <div class="metric-label">Data Coverage</div>
                            <div class="symbol" style="margin-top:0.5rem">{fund_prog.get('percentage', 0)}%</div>
                            <div class="text-muted" style="font-size:0.9rem; margin-top:0.25rem;">Fundamentals Scraped</div>
                        </div>
                    </div>
                    
                    <h3 style="margin: 2.5rem 0 1rem 0;">Top Performer Highlights</h3>
                    <div class="table-container">
                         <table class="data-table" id="table_overview">
                            <thead>
                                <tr>
                                    <th>Symbol</th>
                                    <th>Close</th>
                                    <th>Trend</th>
                                    <th>RSI</th>
                                    <th>P/E</th>
                                    <th>Strategy</th>
                                </tr>
                            </thead>
                            <tbody>
        """
        # Overview Table (Top 5 picks)
        for item in top_picks[:5]:
            t = item['tech']
            f = item['fund']
            trend = t.get('trend', 'Neutral')
            pe = f"{f.get('pe_ratio'):.2f}" if f and f.get('pe_ratio') else "-"
            trend_cls = "text-green" if "Uptrend" in trend else "text-red" if "Downtrend" in trend else "text-muted"
            
            html_content += f"""
                <tr>
                    <td class="mono" style="font-weight:700; color:var(--accent);">{item['symbol']}</td>
                    <td class="mono">₱{t['last_close']:.2f}</td>
                    <td><span class="{trend_cls}">{trend}</span></td>
                    <td class="mono">{t.get('rsi', 0):.1f}</td>
                    <td class="mono">{pe}</td>
                    <td style="font-weight:600; color:#cbd5e1;">{t.get('strategy', 'Hold')}</td>
                </tr>
            """
            
        html_content += """
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <!-- SEARCH RESULTS -->
                 <div id="search_results" class="section">
                    <h2 style="margin-bottom:1.5rem;">Search Results <span id="search_count" class="mono text-muted" style="font-size:1rem; margin-left:1rem;"></span></h2>
                    <div class="dashboard-grid" id="search_grid"></div>
                </div>

                <!-- TOP PICKS -->
                <div id="top_picks" class="section">
                    <h2 style="margin-bottom:1.5rem;">Top Picks <span class="nav-badge" style="font-size:1rem;">""" + str(len(top_picks)) + """</span></h2>
                    <div class="table-container">
                        <table class="data-table" id="table_top_picks">
                            <thead>
                                <tr>
                                    <th onclick="sortTable('table_top_picks', 0)" title="Stock Symbol">Symbol ⬍</th>
                                    <th onclick="sortTable('table_top_picks', 1, 'num')" title="Last Closing Price">Close ⬍</th>
                                    <th onclick="sortTable('table_top_picks', 2)" title="Trend Direction (MA50/100)">Trend ⬍</th>
                                    <th onclick="sortTable('table_top_picks', 3, 'num')" title="Relative Strength Index (Momentum)">RSI ⬍</th>
                                    <th onclick="sortTable('table_top_picks', 4, 'num')" title="Price-to-Earnings Ratio (Valuation)">P/E ⬍</th>
                                    <th onclick="sortTable('table_top_picks', 5)" title="Technical Strategy Recommendation">Strategy ⬍</th>
                                </tr>
                            </thead>
                            <tbody>
        """
        
        # Top Picks Rows
        html_content_2 = ""
        for item in top_picks:
            t = item['tech']
            f = item['fund']
            trend = t.get('trend', 'Neutral')
            pe = f"{f.get('pe_ratio'):.2f}" if f and f.get('pe_ratio') else "-"
            trend_cls = "text-green" if "Uptrend" in trend else "text-red" if "Downtrend" in trend else "text-muted"
            
            html_content_2 += f"""
                <tr>
                    <td class="mono" style="font-weight:700; color:var(--accent);">{item['symbol']}</td>
                    <td class="mono">₱{t['last_close']:.2f}</td>
                    <td><span class="{trend_cls}">{trend}</span></td>
                    <td class="mono">{t.get('rsi', 0):.1f}</td>
                    <td class="mono">{pe}</td>
                    <td style="font-weight:600; color:#cbd5e1;">{t.get('strategy', 'Hold')}</td>
                </tr>
            """
            
        html_content += html_content_2
        
        html_content += """
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <!-- DIVIDENDS -->
                <div id="dividends" class="section">
                    <h2 style="margin-bottom:1.5rem;">Dividend Gems</h2>
                     <div class="table-container">
                        <table class="data-table" id="table_dividends">
                            <thead>
                                <tr>
                                    <th onclick="sortTable('table_dividends', 0)" title="Stock Symbol">Symbol ⬍</th>
                                    <th onclick="sortTable('table_dividends', 1, 'num')" title="Last Closing Price">Price ⬍</th>
                                    <th onclick="sortTable('table_dividends', 2, 'num')" title="Annual Dividend Yield">Yield ⬍</th>
                                    <th onclick="sortTable('table_dividends', 3, 'num')" title="% of Earnings paid as Dividends (<90% is safer)">Payout ⬍</th>
                                    <th onclick="sortTable('table_dividends', 4)" title="Trend Direction">Trend ⬍</th>
                                    <th onclick="sortTable('table_dividends', 5, 'num')" title="Composite Safety Score (0-100)">Safety Score ⬍</th>
                                </tr>
                            </thead>
                            <tbody>
        """
        
        for item in div_picks:
            t = item['tech']
            f = item['fund']
            trend = t.get('trend', 'Neutral')
            payout = item.get('payout_ratio', 0)
            
            payout_cls = "text-green" if payout < 60 else "text-muted" if payout < 90 else "text-red"
            
            html_content += f"""
                <tr>
                    <td class="mono" style="font-weight:700; color:var(--accent);">{item['symbol']}</td>
                    <td class="mono">₱{t['last_close']:.2f}</td>
                    <td class="text-green mono" style="font-weight:700;">{f.get('div_yield', 0):.2f}%</td>
                    <td class="mono {payout_cls}">{payout:.1f}%</td>
                    <td>{trend}</td>
                    <td class="mono">{item['div_score']}</td>
                </tr>
            """
            
        html_content += """
                            </tbody>
                        </table>
                    </div>
                </div>
        """
        
        # INDUSTRY SECTIONS
        for cat, items in grouped_data.items():
            cat_id = cat.replace(" ", "_").replace("&", "")
            
            html_content += f"""
                <div id="{cat_id}" class="section">
                    <h2 style="margin-bottom:1.5rem;">{cat} <span class="nav-badge" style="font-size:1rem;">{len(items)}</span></h2>
                    <div class="dashboard-grid">
            """
            
            for item in items:
                t = item['tech']
                f = item['fund']
                
                trend = t.get('trend', 'Neutral')
                trend_cls = "green" if "Uptrend" in trend else "red" if "Downtrend" in trend else "gray"
                
                pe_display = f"{f.get('pe_ratio'):.2f}" if f and f.get('pe_ratio') else '<span style="color:#475569">-</span>'
                eps_display = f"{f.get('eps'):.2f}" if f and f.get('eps') else "-"
                yield_display = f"{f.get('div_yield'):.2f}%" if f and f.get('div_yield') else "-"
                
                html_content += f"""
                    <div class="card" data-name="{f.get('company_name', '')}">
                        <div class="card-header">
                            <div>
                                <div class="symbol mono" style="color:var(--accent);">{item['symbol']}</div>
                                <div style="font-size:0.75rem; color:var(--text-tertiary); margin-top:4px;">{f.get('company_name', '')[:25]}</div>
                            </div>
                            <div class="price mono">₱{t['last_close']:.2f}</div>
                        </div>
                        
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                             <span class="trend-badge {trend_cls}">{trend}</span>
                             {"<span class='trend-badge' style='background:rgba(139, 92, 246, 0.2); color:#a78bfa;'>HIGH YIELD</span>" if f and f.get('div_yield',0) > 4 else ""}
                        </div>
                        
                        <div class="metrics">
                            <div class="metric">
                                <span class="metric-label" title="Relative Strength Index. &#010;<30: Oversold (Undervalued) &#010;>70: Overbought (Overvalued)">RSI</span>
                                <span class="metric-val mono { 'text-red' if t.get('rsi',50) < 30 else 'text-green' if t.get('rsi',50) > 70 else '' }">{t.get('rsi',0):.1f}</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label" title="Support: Price floor (Hard to break below) &#010;Resistance: Price ceiling (Hard to break above)">Supp/Res</span>
                                <span class="metric-val mono">{t.get('support',0):.2f} / {t.get('resistance',0):.2f}</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label" title="Price-to-Earnings Ratio. &#010;Lower is generally 'Cheaper'. &#010;Avg ~15-20.">P/E Ratio</span>
                                <span class="metric-val mono">{pe_display}</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label" title="Annual Dividend Yield based on last price.">Yield</span>
                                <span class="metric-val mono text-green">{yield_display}</span>
                            </div>
                        </div>
                    </div>
                """
            html_content += "</div></div>"
            
        html_content += """
            </main>
        </div>
        
        <script>
            let previousSectionId = 'overview';
            
            function showSection(id) {
                console.log("Switching to section:", id);
                if (!document.getElementById(id)) {
                    console.error("Section ID not found:", id);
                    return;
                }
                
                // Reset search if escaping search results
                if (id !== 'search_results') {
                     document.getElementById('searchInput').value = "";
                     previousSectionId = id;
                }
                
                document.querySelectorAll('.section').forEach(el => el.classList.remove('active'));
                document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
                
                document.getElementById(id).classList.add('active');
                
                // Highlight nav item (approximate match)
                document.querySelectorAll('.nav-item').forEach(el => {
                    if (el.getAttribute('onclick') && el.getAttribute('onclick').includes(id)) {
                        el.classList.add('active');
                    }
                });
            }
            
            function filterStocks() {
                let input = document.getElementById('searchInput');
                let filter = input.value.toUpperCase();
                let resultsSection = document.getElementById('search_results');
                let resultsGrid = document.getElementById('search_grid');
                let countSpan = document.getElementById('search_count');
                
                if (filter.length === 0) {
                    showSection(previousSectionId);
                    return;
                }
                
                // Switch to search view
                document.querySelectorAll('.section').forEach(el => el.classList.remove('active'));
                resultsSection.classList.add('active');
                document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
                
                resultsGrid.innerHTML = '';
                let count = 0;
                let seen = new Set();
                
                // Search logic - grab all cards
                let allCards = document.querySelectorAll('.section:not(#search_results) .card');
                
                allCards.forEach(card => {
                    let txt = card.innerText; 
                    let name = card.getAttribute('data-name') || "";
                    let symbolEl = card.querySelector('.symbol');
                    if (!symbolEl) return;
                    let symbol = symbolEl.innerText;
                    
                    if (seen.has(symbol)) return;
                    
                    if (txt.toUpperCase().indexOf(filter) > -1 || name.toUpperCase().indexOf(filter) > -1) {
                        let clone = card.cloneNode(true);
                        resultsGrid.appendChild(clone);
                        seen.add(symbol);
                        count++;
                    }
                });
                countSpan.innerText = count + " Found";
            }
            
            function sortTable(tableId, n, type) {
                var table, rows, switching, i, x, y, shouldSwitch, dir, switchcount = 0;
                table = document.getElementById(tableId);
                switching = true;
                dir = "asc";
                
                while (switching) {
                    switching = false;
                    rows = table.rows;
                    for (i = 1; i < (rows.length - 1); i++) {
                        shouldSwitch = false;
                        x = rows[i].getElementsByTagName("TD")[n];
                        y = rows[i + 1].getElementsByTagName("TD")[n];
                        
                        let xVal = x.textContent.trim();
                        let yVal = y.textContent.trim();
                        
                        if (type === 'num') {
                            xVal = parseFloat(xVal.replace(/[^0-9.-]+/g,"")) || 0;
                            yVal = parseFloat(yVal.replace(/[^0-9.-]+/g,"")) || 0;
                        }
                        
                        if (dir == "asc") {
                            if (xVal > yVal) { shouldSwitch = true; break; }
                        } else if (dir == "desc") {
                            if (xVal < yVal) { shouldSwitch = true; break; }
                        }
                    }
                    if (shouldSwitch) {
                        rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
                        switching = true;
                        switchcount ++;
                    } else {
                        if (switchcount == 0 && dir == "asc") {
                            dir = "desc";
                            switching = true;
                        }
                    }
                }
            }
        </script>
        </body>
        </html>
        """
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return os.path.abspath(output_file)

    def open_in_browser(self, file_path: str):
        webbrowser.open('file://' + file_path)
