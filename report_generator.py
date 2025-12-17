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

    def _generate_sparkline_svg(self, data, width=100, height=30, color="#3b82f6"):
        """Generate a simple SVG sparkline."""
        if not data or len(data) < 2:
            return ""
            
        min_val = min(data)
        max_val = max(data)
        rng = max_val - min_val
        if rng == 0: rng = 1
        
        points = []
        for i, val in enumerate(data):
            x = (i / (len(data) - 1)) * width
            y = height - ((val - min_val) / rng) * height
            points.append(f"{x:.1f},{y:.1f}")
            
        polyline = f'<polyline points="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="1.5" />'
        return f'<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}">{polyline}</svg>'

    def generate_dashboard(self, output_file: str = "report.html"):
        """Generate a modern HTML dashboard merging Technical and Fundamental data."""
        
        # Load Data
        tech_data = self.load_json("data/technical_data.json")
        fund_data = self.load_json("data/fundamental_data.json")
        metadata = self.load_json("data/metadata.json")
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
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
                    
                    # Golden Cross Boost
                    if t.get('golden_cross', False): score += 2
                    
                    # Volume Spike Boost
                    if t.get('volume_spike', False): score += 1
                    
                    item['score'] = score
                    grouped_data[cat].append(item)
                    
                    if score >= 3:
                        top_picks.append(item)

                    # --- DIVIDEND GEM SCORING ---
                    div_score = 0
                    yield_val = f.get('div_yield')
                    eps = f.get('eps')
                    price = t.get('last_close', 0)
                    
                    if yield_val:
                        try:
                            if yield_val >= 3.0: div_score += 20
                            if yield_val >= 5.0: div_score += 10
                            
                            dps = (yield_val / 100.0) * price
                            if eps and eps > 0:
                                payout = (dps / eps) * 100.0
                                item['payout_ratio'] = payout
                                
                                if payout < 90: div_score += 20
                                if payout < 60: div_score += 20
                                if payout > 100: div_score -= 50
                            elif eps and eps < 0:
                                div_score -= 50
                            
                            if "Uptrend" in trend: div_score += 20
                            elif "Downtrend" in trend: div_score -= 10
                            
                            item['div_score'] = div_score
                            if div_score >= 40:
                                div_picks.append(item)
                                
                        except: pass

        # Sort Picks
        top_picks.sort(key=lambda x: x['score'], reverse=True)
        top_picks = top_picks[:20]
        
        div_picks.sort(key=lambda x: x['div_score'], reverse=True)

        # --- HTML COMPONENT GENERATION ---
        
        # 1. Industry Nav
        industry_nav = ""
        for cat in STOCK_CATEGORIES:
            cat_id = cat.replace(" ", "_").replace("&", "")
            industry_nav += f'<div class="nav-item" onclick="showSection(\'{cat_id}\')">{cat}</div>'
            
        # 2. All Cards (Overview) & Industry Sections
        all_cards_html = ""
        industry_sections = ""
        
        for cat, items in grouped_data.items():
            cat_id = cat.replace(" ", "_").replace("&", "")
            
            section_html = f'<div id="{cat_id}" class="section"><h2 style="margin-bottom:1.5rem;">{cat} <span class="nav-badge" style="font-size:1rem;">{len(items)}</span></h2><div class="dashboard-grid">'
            
            for item in items:
                t = item['tech']
                f = item['fund']
                
                trend = t.get('trend', 'Neutral')
                trend_cls = "green" if "Uptrend" in trend else "red" if "Downtrend" in trend else "gray"
                
                pe_display = f"{f.get('pe_ratio'):.2f}" if f and f.get('pe_ratio') else '-'
                yield_display = f"{f.get('div_yield'):.2f}%" if f and f.get('div_yield') else "-"
                
                # Sparkline
                spark_svg = self._generate_sparkline_svg(t.get('sparkline', []), width=80, height=20, color="#10b981" if "Uptrend" in trend else "#ef4444")
                
                # Badges
                badges = f'<span class="trend-badge {trend_cls}">{trend}</span>'
                if t.get('golden_cross', False):
                    badges += ' <span class="trend-badge gold">GOLDEN CROSS</span>'
                if t.get('volume_spike', False):
                    badges += ' <span class="trend-badge" style="background:rgba(59, 130, 246, 0.2); color:#60a5fa;">VOL SPIKE</span>'

                # Data Attributes for JS Filtering
                data_attrs = f'data-name="{f.get("company_name", "")}" data-sector="{cat}" '
                data_attrs += f'data-rsi="{t.get("rsi", 50)}" data-pe="{f.get("pe_ratio", 999)}" '
                data_attrs += f'data-golden="{str(t.get("golden_cross", False)).lower()}" data-trend="{trend}" '
                data_attrs += f'data-div-amt="{f.get("div_amount", 0)}"'

                card_html = f"""
                    <div class="card" {data_attrs}>
                        <div class="card-header">
                            <div>
                                <div class="symbol mono" style="color:var(--accent);">{item['symbol']}</div>
                                <div style="font-size:0.75rem; color:var(--text-tertiary); margin-top:4px;">{f.get('company_name', '')[:25]}</div>
                            </div>
                            <div style="text-align:right;">
                                <div class="price mono">₱{t['last_close']:.2f}</div>
                                {spark_svg}
                            </div>
                        </div>
                        
                        <div style="margin-bottom:8px;">
                             {badges}
                        </div>
                        
                        <div class="metrics">
                            <div class="metric">
                                <span class="metric-label" title="RSI">RSI</span>
                                <span class="metric-val mono { 'text-red' if t.get('rsi',50) < 30 else 'text-green' if t.get('rsi',50) > 70 else '' }">{t.get('rsi',0):.1f}</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Supp/Res</span>
                                <span class="metric-val mono">{t.get('support',0):.2f} / {t.get('resistance',0):.2f}</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">P/E Ratio</span>
                                <span class="metric-val mono">{pe_display}</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Yield</span>
                                <span class="metric-val mono text-green">{yield_display}</span>
                            </div>
                        </div>
                        { f'<div style="border-top:1px solid #334155; margin-top:8px; padding-top:4px; display:flex; justify-content:space-between; align-items:center;"><span style="font-size:0.75rem; color:#94a3b8;">Est. Div Amt</span><span class="mono" style="font-size:0.8rem; color:#fff;">₱{f.get("div_amount", 0):.2f}</span></div>' if f.get('div_amount') and f.get('div_amount') > 0 else '' }
                    </div>
                """
                
                all_cards_html += card_html
                section_html += card_html # Add to specific section too
                
            section_html += "</div></div>"
            industry_sections += section_html
            
        # 3. Top Picks Rows
        top_picks_html = ""
        for item in top_picks:
            t = item['tech']
            f = item['fund']
            trend = t.get('trend', 'Neutral')
            pe = f"{f.get('pe_ratio'):.2f}" if f and f.get('pe_ratio') else "-"
            trend_cls = "text-green" if "Uptrend" in trend else "text-red" if "Downtrend" in trend else "text-muted"
            
            top_picks_html += f"""
                <tr>
                    <td class="mono" style="font-weight:700; color:var(--accent);">{item['symbol']}</td>
                    <td class="mono">₱{t['last_close']:.2f}</td>
                    <td><span class="{trend_cls}">{trend}</span></td>
                    <td class="mono">{t.get('rsi', 0):.1f}</td>
                    <td class="mono">{pe}</td>
                    <td style="font-weight:600; color:#cbd5e1;">{t.get('strategy', 'Hold')}</td>
                </tr>
            """
            
        # 4. Dividends Rows
        div_picks_html = ""
        for item in div_picks:
            t = item['tech']
            f = item['fund']
            trend = t.get('trend', 'Neutral')
            payout = item.get('payout_ratio', 0)
            payout_cls = "text-green" if payout < 60 else "text-muted" if payout < 90 else "text-red"
            
            div_picks_html += f"""
                <tr>
                    <td class="mono" style="font-weight:700; color:var(--accent);">{item['symbol']}</td>
                    <td class="mono">₱{t['last_close']:.2f}</td>
                    <td class="text-green mono" style="font-weight:700;">{f.get('div_yield', 0):.2f}%</td>
                    <td class="mono {payout_cls}">{payout:.1f}%</td>
                    <td>{trend}</td>
                    <td class="mono">{item['div_score']}</td>
                </tr>
            """

        # --- FINAL HTML ASSEMBLY ---
        html_content = f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>PSE Pro Dashboard v2.0</title>
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
                    
                    --accent: #3b82f6;
                    --accent-glow: rgba(59, 130, 246, 0.5);
                    
                    --green: #10b981;
                    --red: #ef4444;
                    --gold: #eab308;
                }}
                
                * {{ box-sizing: border-box; }}
                body {{
                    margin: 0;
                    font-family: 'Inter', sans-serif;
                    background-color: var(--bg-app);
                    color: var(--text-primary);
                    display: flex;
                    height: 100vh;
                    overflow: hidden;
                }}
                
                /* Sidebar */
                nav {{
                    width: 240px;
                    background: var(--bg-panel);
                    border-right: 1px solid var(--border);
                    display: flex;
                    flex-direction: column;
                    padding: 1.5rem 0;
                }}
                
                .brand {{
                    padding: 0 1.5rem;
                    margin-bottom: 2rem;
                    font-size: 1.25rem;
                    font-weight: 800;
                    letter-spacing: -0.5px;
                    color: var(--text-primary);
                    display: flex;
                    align-items: center;
                    gap: 10px;
                }}
                
                .brand span {{ color: var(--accent); }}
                
                .nav-item {{
                    padding: 0.75rem 1.5rem;
                    color: var(--text-secondary);
                    cursor: pointer;
                    display: flex;
                    justify-content: space-between;
                    font-size: 0.9rem;
                    transition: all 0.2s;
                }}
                
                .nav-item:hover, .nav-item.active {{
                    background: var(--bg-app);
                    color: var(--text-primary);
                    border-left: 3px solid var(--accent);
                }}
                
                .nav-badge {{
                    background: var(--bg-panel-hover);
                    padding: 2px 8px;
                    border-radius: 99px;
                    font-size: 0.75rem;
                }}
                
                /* Content Area */
                .content {{
                    flex: 1;
                    display: flex;
                    flex-direction: column;
                    overflow: hidden;
                }}
                
                header {{
                    height: 64px;
                    border-bottom: 1px solid var(--border);
                    display: flex;
                    align-items: center;
                    padding: 0 2rem;
                    justify-content: space-between;
                }}
                
                .header-title {{ font-weight: 600; color: var(--text-secondary); }}
                
                .search-bar {{
                    background: var(--bg-panel);
                    border: 1px solid var(--border);
                    border-radius: 8px;
                    padding: 0.5rem 1rem;
                    color: var(--text-primary);
                    font-family: inherit;
                    width: 300px;
                    outline: none;
                }}
                
                .search-bar:focus {{ border-color: var(--accent); }}

                .filter-bar {{
                    display: flex;
                    gap: 10px;
                    margin-left: 20px;
                }}
                
                .filter-select {{
                    background: var(--bg-panel);
                    border: 1px solid var(--border);
                    color: var(--text-secondary);
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 0.8rem;
                }}
                
                main {{
                    flex: 1;
                    overflow-y: auto;
                    display: block;
                    position: relative;
                    padding: 2rem;
                }}
                
                /* Grid Layout */
                .dashboard-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                    gap: 1.5rem;
                }}
                
                /* Cards */
                .card {{
                    background: var(--bg-panel);
                    border: 1px solid var(--border);
                    border-radius: 12px;
                    padding: 1.25rem;
                    transition: transform 0.2s;
                    position: relative;
                    overflow: hidden;
                }}
                
                .card:hover {{
                    transform: translateY(-2px);
                    border-color: var(--accent);
                }}
                
                .card-header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-start;
                    margin-bottom: 1rem;
                }}
                
                .symbol {{ font-size: 1.1rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; }}
                .price {{ font-size: 1.25rem; font-weight: 600; color: var(--text-primary); }}
                
                .trend-badge {{
                    font-size: 0.7rem;
                    padding: 2px 8px;
                    border-radius: 4px;
                    text-transform: uppercase;
                    font-weight: 700;
                }}
                
                .green {{ background: rgba(16, 185, 129, 0.1); color: var(--green); }}
                .red {{ background: rgba(239, 68, 68, 0.1); color: var(--red); }}
                .gray {{ background: var(--bg-panel-hover); color: var(--text-tertiary); }}
                .gold {{ background: rgba(234, 179, 8, 0.15); color: var(--gold); }}
                
                .metrics {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 1rem;
                    margin-top: 1rem;
                    padding-top: 1rem;
                    border-top: 1px solid var(--border);
                }}
                
                .metric {{ display: flex; flex-direction: column; }}
                .metric-label {{ font-size: 0.7rem; color: var(--text-tertiary); margin-bottom: 2px; }}
                .metric-val {{ font-size: 0.9rem; font-weight: 600; }}
                
                /* Tables */
                .table-container {{
                    background: var(--bg-panel);
                    border-radius: 12px;
                    border: 1px solid var(--border);
                    overflow: hidden;
                }}
                
                .data-table {{ width: 100%; border-collapse: collapse; text-align: left; }}
                .data-table th {{
                    padding: 1rem;
                    background: var(--bg-app);
                    color: var(--text-secondary);
                    font-size: 0.75rem;
                    text-transform: uppercase;
                    cursor: pointer;
                }}
                .data-table td {{ padding: 1rem; border-bottom: 1px solid var(--border); color: var(--text-primary); }}
                .data-table tr:hover {{ background: var(--bg-panel-hover); }}
                
                /* Utility */
                .mono {{ font-family: 'JetBrains Mono', monospace; }}
                .text-green {{ color: var(--green); }}
                .text-red {{ color: var(--red); }}
                .text-gold {{ color: var(--gold); }}
                .text-muted {{ color: var(--text-tertiary); }}
                
                .section {{ display: none; opacity: 0; transition: opacity 0.3s; }}
                .section.active {{ display: block; opacity: 1; }}
                
                .sparkline {{ margin-left: 10px; vertical-align: middle; }}
            </style>
        </head>
        <body>
            <nav>
                <div class="brand">PSE<span>PRO</span> v2.0</div>
                <div class="nav-item active" onclick="showSection('overview')">
                    Overview <span class="nav-badge">All</span>
                </div>
                <div class="nav-item" onclick="showSection('top_picks')">
                    Top Picks <span class="nav-badge" style="color:var(--accent); font-weight:bold;">★</span>
                </div>
                <div class="nav-item" onclick="showSection('dividends')">
                    Dividend Gems <span class="nav-badge" style="color:var(--green);">$</span>
                </div>
                
                <div style="margin: 1.5rem 1.5rem 0.5rem; font-size:0.7rem; color:var(--text-tertiary); text-transform:uppercase;">Industries</div>
                
                {industry_nav}
                
            </nav>
            
            <div class="content">
                <header>
                    <div style="display:flex; align-items:center;">
                         <div class="header-title">Market Dashboard</div>
                         <div class="filter-bar">
                             <input type="text" id="searchInput" class="search-bar" placeholder="Search by Symbol or Name..." onkeyup="filterStocks()">
                             
                             <select id="sectorFilter" class="filter-select" onchange="filterStocks()">
                                 <option value="All">All Sectors</option>
                                 """ + "".join([f'<option value="{c}">{c}</option>' for c in STOCK_CATEGORIES]) + f"""
                             </select>
                             
                             <select id="metricFilter" class="filter-select" onchange="filterStocks()">
                                 <option value="None">Filter Risk...</option>
                                 <option value="oversold">RSI < 30 (Oversold)</option>
                                 <option value="cheap">P/E < 15 (Cheap)</option>
                                 <option value="uptrend">Golden Cross / Uptrend</option>
                             </select>
                         </div>
                    </div>
                    <div style="font-size:0.8rem; color:var(--text-tertiary);">Last Updated: {timestamp}</div>
                </header>
                
                <main>
                    <!-- OVERVIEW (All Stocks Grid) -->
                    <div id="overview" class="section active">
                        <h2 style="margin-bottom:1.5rem;">Market Overview</h2>
                        <div id="all_stocks_grid" class="dashboard-grid">
                            {all_cards_html}
                        </div>
                    </div>

                    <!-- SEARCH RESULTS -->
                    <div id="search_results" class="section">
                        <h2 style="margin-bottom:1.5rem;">Results <span class="nav-badge" id="search_count">0</span></h2>
                        <div class="dashboard-grid" id="search_grid"></div>
                    </div>
                
                    <!-- TOP PICKS -->
                    <div id="top_picks" class="section">
                        <h2 style="margin-bottom:1.5rem;">Top Picks <span class="nav-badge" style="font-size:1rem;">{len(top_picks)}</span></h2>
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
            {top_picks_html}
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
            {div_picks_html}
                                </tbody>
                            </table>
                        </div>
                    </div>
            
                    {industry_sections}
                </main>
            </div>
            
            <script>
                let previousSectionId = 'overview';
                
                function showSection(id) {{
                    console.log("Switching to section:", id);
                    if (!document.getElementById(id)) return;
                    
                    if (id !== 'search_results') {{
                        document.getElementById('searchInput').value = "";
                        previousSectionId = id;
                        // Reset filters
                        document.getElementById('sectorFilter').value = "All";
                        document.getElementById('metricFilter').value = "None";
                        filterStocks(); 
                    }}
                    
                    document.querySelectorAll('.section').forEach(el => el.classList.remove('active'));
                    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
                    
                    document.getElementById(id).classList.add('active');
                }}
                
                function filterStocks() {{
                    let text = document.getElementById('searchInput').value.toUpperCase();
                    let sector = document.getElementById('sectorFilter').value;
                    let metric = document.getElementById('metricFilter').value;
                    
                    let grid = document.getElementById('all_stocks_grid');
                    let cards = grid.getElementsByClassName('card');
                    
                    let activeSection = document.querySelector('.section.active').id;
                    if (activeSection !== 'overview' && (text.length > 0 || sector !== 'All' || metric !== 'None')) {{
                        showSection('overview');
                    }}
                    
                    for (let i = 0; i < cards.length; i++) {{
                        let card = cards[i];
                        let name = card.getAttribute('data-name') || "";
                        let sym = card.querySelector('.symbol').innerText;
                        let cardSector = card.getAttribute('data-sector') || "";
                        
                        let rsi = parseFloat(card.getAttribute('data-rsi') || "50");
                        let pe = parseFloat(card.getAttribute('data-pe') || "999");
                        let isGolden = card.getAttribute('data-golden') === "true";
                        let trend = card.getAttribute('data-trend') || "";
                        
                        let show = true;
                        
                        if (text.length > 0) {{
                            if (name.toUpperCase().indexOf(text) === -1 && sym.toUpperCase().indexOf(text) === -1) {{
                                show = false;
                            }}
                        }}
                        
                        if (sector !== 'All' && cardSector !== sector) {{
                            show = false;
                        }}
                        
                        if (metric === 'oversold' && rsi >= 30) show = false;
                        if (metric === 'cheap' && (pe > 15 || isNaN(pe))) show = false;
                        if (metric === 'uptrend' && !isGolden && trend.indexOf('Uptrend') === -1) show = false;
                        
                        card.style.display = show ? "" : "none";
                    }}
                }}
                
                function sortTable(tableId, n, type) {{
                    var table, rows, switching, i, x, y, shouldSwitch, dir, switchcount = 0;
                    table = document.getElementById(tableId);
                    switching = true;
                    dir = "asc";
                    
                    while (switching) {{
                        switching = false;
                        rows = table.rows;
                        for (i = 1; i < (rows.length - 1); i++) {{
                            shouldSwitch = false;
                            x = rows[i].getElementsByTagName("TD")[n];
                            y = rows[i + 1].getElementsByTagName("TD")[n];
                            
                            let xVal = x.textContent.trim();
                            let yVal = y.textContent.trim();
                            
                            if (type === 'num') {{
                                xVal = parseFloat(xVal.replace(/[^0-9.-]+/g,"")) || 0;
                                yVal = parseFloat(yVal.replace(/[^0-9.-]+/g,"")) || 0;
                            }}
                            
                            if (dir == "asc") {{
                                if (xVal > yVal) {{ shouldSwitch = true; break; }}
                            }} else if (dir == "desc") {{
                                if (xVal < yVal) {{ shouldSwitch = true; break; }}
                            }}
                        }}
                        if (shouldSwitch) {{
                            rows[i].parentNode.insertBefore(rows[i + 1], rows[i]);
                            switching = true;
                            switchcount ++;
                        }} else {{
                            if (switchcount == 0 && dir == "asc") {{
                                dir = "desc";
                                switching = true;
                            }}
                        }}
                    }}
                }}
            </script>
        </body>
        </html>
        """
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return os.path.abspath(output_file)

    def open_in_browser(self, file_path: str):
        webbrowser.open('file://' + file_path)
