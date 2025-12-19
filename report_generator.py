# report_generator.py
# Generates modern HTML dashboard for stock analysis
import datetime
import webbrowser
import os
import json
import base64
from typing import Dict
from stock_data import STOCK_CATEGORIES
from analyzer import Analyzer

class ReportGenerator:
    def __init__(self):
        self.analyzer = Analyzer()

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

    def _generate_onclick(self, item, official_meta):
        """Generate the onclick attribute for showing stock details."""
        t = item['tech']
        f = item['fund']
        
        official = official_meta
        # Fallback to category/sector in item if official mapping fails, but usually official has it.
        official = official_meta
        # Fallback to category/sector in item if official mapping fails
        
        o_sector = official.get('sector', 'Unknown')
        o_subsector = official.get('subsector', '-')
        o_date = official.get('listingDate', '-')
        
        mk_cap = f.get('market_cap', 0)
        high_52 = f.get('high_52', 0)
        low_52 = f.get('low_52', 0)
        
        # News
        news_items = self.news_data.get(item['symbol'], [])
        
        data_dict = {
            "symbol": item['symbol'],
            "name": item.get('company_name', item['symbol']),
            "price": t.get('last_close', 0),
            "high_52": f.get('high_52', 0),
            "low_52": f.get('low_52', 0),
            "eps": f.get('eps', 0),
            "pe": f.get('pe_ratio', 0),
            "mkt_cap": f.get('market_cap', 0),
            "shares": f.get('outstanding_shares', 0),
            "sector": official.get('sector', 'Unknown'),
            "subsector": official.get('subsector', '-'),
            "listing_date": official.get('listingDate', '-'),
            "divYield": f.get('div_yield'),
            "div_history": f.get('div_history', []),
            "news": news_items,
            "stop_loss": t.get('stop_loss', 0),
            "risk_pct": t.get('risk_pct', 0),
            "support": t.get('support', 0),
            "resistance": t.get('resistance', 0),
            "history": t.get('history', []) # Add history for chart
        }
        
        # Create JSON and Base64 Encode
        # data_json = json.dumps(data_dict)
        # data_b64 = base64.b64encode(data_json.encode('utf-8')).decode('utf-8')
        
        # Store in Global Dict
        self.all_stock_data[item['symbol']] = data_dict
        
        call = f"showStockDetails('{item['symbol']}')"
        return f'onclick="{call}" style="cursor:pointer;"'

    def _generate_card_html(self, item, stock_meta):
        """Generate consistent HTML for a stock card."""
        t = item['tech']
        f = item['fund']
        
        trend = t.get('trend', 'Neutral')
        trend_cls = "green" if "Uptrend" in trend else "red" if "Downtrend" in trend else "gray"
        
        pe_display = f"{f.get('pe_ratio'):.2f}" if f and f.get('pe_ratio') else '-'
        yield_display = f"{f.get('div_yield'):.2f}%" if f and f.get('div_yield') else "-"
        
        # Sparkline
        spark_svg = self._generate_sparkline_svg(t.get('sparkline', []), width=80, height=20, color="#10b981" if "Uptrend" in trend else "#ef4444")
        
        # Status Badge
        status_val = f.get('status', 'Active')
        status_badge = ""
        is_suspended = status_val in ['Suspended', 'Halted']
        
        if is_suspended:
             status_badge = f'<span class="trend-badge" style="background:rgba(245, 158, 11, 0.15); color:#f59e0b;">{status_val.upper()}</span> '
        
        # Trend Badge
        trend_badge = f'<span class="trend-badge {trend_cls}">{trend}</span>'
        if is_suspended and trend in ['Suspended', 'Unknown', 'Neutral']:
            trend_badge = ""

        # Badges
        badges = status_badge + trend_badge
        if t.get('golden_cross', False):
            badges += ' <span class="trend-badge gold">GOLDEN CROSS</span>'
        if t.get('volume_spike', False):
            badges += ' <span class="trend-badge" style="background:rgba(59, 130, 246, 0.2); color:#60a5fa;">VOL SPIKE</span>'

        # Official Metadata Lookup (Use passed stock_meta dict to find this stock)
        official = stock_meta.get(item['symbol'], {})
        o_sector = official.get('sector', 'Unknown')
        
        data_attrs = f'data-name="{item["company_name"]}" data-sector="{o_sector}" '
        data_attrs += f'data-rsi="{t.get("rsi", 50)}" data-pe="{f.get("pe_ratio", 999)}" '
        data_attrs += f'data-golden="{str(t.get("golden_cross", False)).lower()}" data-trend="{trend}" '
        data_attrs += f'data-yield="{f.get("div_yield", 0)}" data-price="{t.get("last_close", 0)}" '
        data_attrs += f'data-winrate="{t.get("win_rate", 0)}" '

        # Prepare extended data for Modal
        onclick_attr = self._generate_onclick(item, official)

        return f"""
            <div class="card" {onclick_attr} {data_attrs}>
                <div class="card-header">
                    <div>
                        <div class="symbol mono" style="color:var(--accent);">{item['symbol']}</div>
                        <div style="font-size:0.75rem; color:var(--text-tertiary); margin-top:4px;">{item['company_name'][:30]}</div>
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

    def generate_dashboard(self, output_file: str = "report.html"):
        """Generate a modern HTML dashboard merging Technical and Fundamental data."""
        
        # Load Data
        tech_data = self.load_json("data/technical_data.json")
        # metadata.json is for progress, stock_metadata.json is official info
        stock_meta = self.load_json("data/stock_metadata.json") 
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Load Official Fundamentals (Deep Scrape)
        official_fund = self.load_json("data/pse_fundamentals.json")
        
        # Load News Data
        self.news_data = self.load_json("data/news_data.json")
        
        # Merge Data per Industry
        # Dynamic Sector Generation
        all_sectors = set()
        for s_data in stock_meta.values():
            sec = s_data.get('sector')
            if sec:
                # Normalize: Mining & Oil -> Mining and Oil
                sec = sec.replace(' & ', ' and ')
                sec = sec.replace('Small, Medium and Emerging Board', 'SME Board')
                all_sectors.add(sec)
        
        # Sort and ensure "SME / Others" is last if it exists, or just sort alphabetically
        sorted_sectors = sorted(list(all_sectors))
        if "SME Board" in sorted_sectors:
             sorted_sectors.remove("SME Board")
             sorted_sectors.append("SME Board")
            
        grouped_data = {cat: [] for cat in sorted_sectors}
        # Add a catch-all if needed, but let's try to stick to official
        if "Uncategorized" not in grouped_data:
            grouped_data["Uncategorized"] = []
            
        top_picks = []
        div_picks = []
        
        # Iterate over ALL available symbols (union of tech and meta)
        all_symbols = set(tech_data.keys()) | set(stock_meta.keys())
    
        # Global Data Store for Client Side
        self.all_stock_data = {}
    
        for symbol in all_symbols:
            # Get Official Name/Sector from Metadata
            meta = stock_meta.get(symbol, {})
            sector = meta.get('sector', 'Uncategorized')
            # Normalize Sector Name
            sector = sector.replace(' & ', ' and ')
            sector = sector.replace('Small, Medium and Emerging Board', 'SME Board')
            
            if sector not in grouped_data:
                sector = 'Uncategorized' # Fallback
            
            # Retrieve Data or Default
            t = tech_data.get(symbol)
            f = {}
            official_fund_data = official_fund.get(symbol, {})
            status_val = official_fund_data.get('status', 'Active')

            # If no Tech Data, but we have metadata
            if not t:
                # Create dummy tech data for display if it's active or suspended
                t = {
                    "last_close": 0.0,
                    "trend": "Unknown",
                    "rsi": 0,
                    "sparkline": [],
                    "history": []
                }
                if status_val == 'Suspended':
                    t['trend'] = 'Suspended'
            
            # Check if we should process
            if t:
                    # Sync Official Fundamentals
                    of = official_fund_data
                    if of:
                        if of.get('pe_ratio'): f['pe_ratio'] = of['pe_ratio']
                        if of.get('eps'): f['eps'] = of['eps']
                        if of.get('status'): f['status'] = of['status'] # Sync Status
                        if of.get('market_cap'): f['market_cap'] = of['market_cap']
                        if of.get('outstanding_shares'): f['outstanding_shares'] = of['outstanding_shares']
                        if of.get('high_52'): f['high_52'] = of['high_52']
                        if of.get('low_52'): f['low_52'] = of['low_52']
                        if of.get('div_history'): f['div_history'] = of['div_history']
                        # Calculate Dividend Amount from History (TTM)
                        if of.get('div_history'):
                            total_div = 0.0
                            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=365)
                            
                            pay_months = []
                            
                            for d in of['div_history']:
                                try:
                                    # Parse date "Sep 05, 2025" or similar
                                    # Using raw string match might be safer or try/except
                                    d_date = None
                                    date_str = d.get('ex_date', '') # Use Ex-Date for consistency
                                    if date_str:
                                        # Try multiple formats if needed, usually "Mon DD, YYYY"
                                        d_date = datetime.datetime.strptime(date_str, "%b %d, %Y")
                                    
                                    if d_date and d_date > cutoff_date:
                                        amt = d.get('amount')
                                        if amt: 
                                            total_div += float(amt)
                                            pay_months.append(d_date.strftime("%b"))
                                except:
                                    continue
                            
                            # Deduplicate pay_months
                            pay_months = list(set(pay_months)) # Dedupe: "Mar, Mar" -> "Mar"
                            # Sort by calendar month
                            month_map = {m: i for i, m in enumerate(["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"])}
                            pay_months.sort(key=lambda x: month_map.get(x, 99))
                            
                            if total_div > 0:
                                f['div_amount'] = total_div
                                
                                # Frequency Detection
                                unique_months = len(pay_months)
                                if unique_months >= 4:
                                    f['div_freq'] = "Quarterly"
                                elif unique_months >= 2:
                                    f['div_freq'] = "Semi-Annual"
                                else:
                                    f['div_freq'] = "Annual"
                                    
                                f['div_sched'] = ", ".join(pay_months)
                                
                                # Recalculate Yield based on Technical Last Close
                                if t.get('last_close') and t['last_close'] > 0:
                                    f['div_yield'] = (total_div / t['last_close']) * 100.0
                    
                    # Get Official Name from Metadata
                    meta = stock_meta.get(symbol, {})
                    official_name = meta.get('name', f.get('company_name', symbol))
                    
                    # Create combined object
                    item = {
                        "symbol": symbol,
                        "company_name": official_name,
                        "tech": t,
                        "fund": f,
                        "score": 0, # Top Pick Score
                        "div_score": 0, # Dividend Score
                        "payout_ratio": 0
                    }
                    
                    # --- TOP PICK SCORING ---
                    score = 0
                    trend = t.get('trend', '')
                    # --- TOP PICK SCORING (Enhanced) ---
                    # Logic moved to analyzer.py for reusability (report + backtest)
                    score, score_reasons = self.analyzer.calculate_score(t, f)
                    
                    item['score'] = score
                    item['score_reasons'] = score_reasons
                    
                    if sector in grouped_data:
                        grouped_data[sector].append(item)
                    
                    # Threshold for "Top Pick" (Optimized via Backtest)
                    if score >= 7:
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
        # Top Picks: Sort by Score Descending, then Yield Descending (Tie-breaker)
        top_picks.sort(key=lambda x: (x['score'], x['fund'].get('div_yield', 0)), reverse=True)
        top_picks = top_picks[:20]
        
        # Assign Ranks
        for i, item in enumerate(top_picks):
            item['rank'] = i + 1
            
        # Dividend Picks: Filtered by Score >= 40 already
        
        # Dividend Picks: Filtered by Score >= 40 already
        div_picks.sort(key=lambda x: x['symbol']) # Display A-Z

        # Sort Industry Lists by Symbol
        for cat in grouped_data:
            grouped_data[cat].sort(key=lambda x: x['symbol'])

        # --- HTML COMPONENT GENERATION ---
        
        # 1. Industry Nav
        industry_nav = ""
        for cat in sorted_sectors:
            if cat not in grouped_data or not grouped_data[cat]: continue
            count = len(grouped_data[cat])
            cat_id = cat.replace(" ", "_").replace("&", "").replace(",", "")
            industry_nav += f'<div class="nav-item" onclick="showSection(\'{cat_id}\')">{cat} <span class="nav-badge">{count}</span></div>'
            
        # 2. All Cards (Overview) - Flat A-Z List
        all_cards_html = ""
        
        # Flatten all grouped data to get unique items for Overview
        all_overview_items = []
        for cat, items in grouped_data.items():
            all_overview_items.extend(items)
            
        # Sort All Overview Items by Symbol
        all_overview_items.sort(key=lambda x: x['symbol'])
        
        for item in all_overview_items:
             card_html = self._generate_card_html(item, stock_meta)
             all_cards_html += card_html

        # 3. Industry Sections
        industry_sections = ""
        
        for cat in sorted_sectors:
            items = grouped_data.get(cat, [])
            if not items: continue
            
            cat_id = cat.replace(" ", "_").replace("&", "").replace(",", "")
            
            section_html = f'<div id="{cat_id}" class="section"><h2 style="margin-bottom:1.5rem;">{cat} <span class="nav-badge" style="font-size:1rem;">{len(items)}</span></h2><div class="dashboard-grid">'
            
            for item in items:
                 card_html = self._generate_card_html(item, stock_meta)
                 section_html += card_html
                
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
            
            # Name display (Use Official Name)
            name = item.get('company_name', item['symbol'])
            official = stock_meta.get(item['symbol'], {})
            onclick_attr = self._generate_onclick(item, official)
            
            # Badge
            rank = item.get('rank', 99)
            badge_html = ""
            if rank == 1: badge_html = '<span class="rank-badge rank-1">#1</span>'
            elif rank == 2: badge_html = '<span class="rank-badge rank-2">#2</span>'
            elif rank == 3: badge_html = '<span class="rank-badge rank-3">#3</span>'
            elif rank <= 10: badge_html = f'<span class="rank-badge rank-other">#{rank}</span>'
            
            # Format Score Tooltip
            reasons = item.get('score_reasons', [])
            score_tooltip_text = "&#10;".join(reasons)
            score_val = item.get('score', 0)
            
            score_cls = "text-muted"
            if score_val >= 9: score_cls = "green" # High Confidence
            elif score_val >= 7: score_cls = "accent" # Medium Confidence
            else: score_cls = "gray"
            
            # New Columns
            win_rate = t.get('win_rate', 0)
            avg_ret = t.get('avg_monthly_return', 0)
            consistency_display = f"{win_rate:.0f}% <span style='font-size:0.75rem; color:#64748b;'>({avg_ret:+.1f}%)</span>"
            
            freq = f.get('div_freq', '-')
            
            yld = f.get('div_yield', 0)
            yield_display = f"{yld:.2f}%" if yld > 0 else "-"
            yield_cls = "text-green" if yld > 4 else ""

            top_picks_html += f"""
                <tr {onclick_attr}>
                    <td>
                        <div class="mono" style="font-weight:700; color:var(--accent);">{item['symbol']} {badge_html}</div>
                        <div style="font-size:0.75rem; color:#64748b;">{name[:20]}</div>
                    </td>
                    <td class="mono">₱{t['last_close']:.2f}</td>
                    <td><span class="{trend_cls}">{trend}</span></td>
                    <td class="mono">{consistency_display}</td>
                    <td class="mono" style="font-size:0.8rem;">{freq}</td>
                    <td class="mono {yield_cls}">{yield_display}</td>
                    <td class="mono">{pe}</td>
                    <td class="mono" title="{score_tooltip_text}">
                        <span class="{score_cls}" style="font-weight:bold; padding:2px 8px; border-radius:4px;">{item['score']}</span>
                    </td>
                </tr>
            """

            
        # 4. Dividends Rows
        div_picks_html = ""
        for item in div_picks:
            t = item['tech']
            f = item['fund']
            trend = t.get('trend', 'Neutral')
            
            # Data preparation
            payout = item.get('payout_ratio', 0)
            yield_val = f.get('div_yield', 0)
            div_amt = f.get('div_amount', 0)
            pe_val = f.get('pe_ratio', 0)
            
            # Name display (Use Official Name)
            name = item.get('company_name', item['symbol'])
            official = stock_meta.get(item['symbol'], {})
            onclick_attr = self._generate_onclick(item, official)
            
            # Logic for Value Trap / Safety
            is_uptrend = "Uptrend" in trend
            is_downtrend = "Downtrend" in trend
            
            # Payout Logic
            payout_cls = "text-green"
            if payout > 60: payout_cls = "text-muted"
            if payout > 90: payout_cls = "text-red"
            
            # Value Trap Detection
            # High Yield (>8%) + (Bad Payout OR Downtrend)
            is_value_trap = False
            if yield_val > 8.0 and (payout > 100 or is_downtrend):
                is_value_trap = True
            
            trend_display = trend
            if is_value_trap:
                trend_display += ' <span style="background:rgba(239, 68, 68, 0.2); color:#ef4444; padding:2px 6px; border-radius:4px; font-size:0.7em;">TRAP?</span>'
            
            pe_display = f"{pe_val:.2f}" if pe_val else "-"
            div_amt_display = f"₱{div_amt:.2f}" if div_amt else "-"
            
            freq = f.get('div_freq', '-')
            sched = f.get('div_sched', '-')
            eps_val = f.get('eps', 0)
            eps_display = f"₱{eps_val:.2f}" if eps_val else "-"
            
            div_picks_html += f"""
                <tr {onclick_attr}>
                    <td>
                        <div class="mono" style="font-weight:700; color:var(--accent);">{item['symbol']}</div>
                        <div style="font-size:0.75rem; color:#64748b;">{name[:20]}</div>
                    </td>
                    <td class="mono">₱{t['last_close']:.2f}</td>
                    <td class="text-green mono" style="font-weight:700;">{yield_val:.2f}%</td>
                    <td class="mono">{div_amt_display}</td>
                    <td class="mono" style="font-weight:bold;">{eps_display}</td>
                    <td class="mono {payout_cls}">{payout:.1f}%</td>
                    <td class="mono" style="text-align:center;">{freq}</td>
                    <td class="mono" style="font-size:0.8rem;">{sched}</td>
                    <td class="mono">{pe_display}</td>
                    <td>{trend_display}</td>
                    <td class="mono">{item['div_score']}</td>
                </tr>
            """

        # Generate sector options for the filter dropdown
        sector_options = "".join([f'<option value="{c}">{c}</option>' for c in sorted_sectors])

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
                
                .rank-badge {{
                    font-size: 0.7rem;
                    padding: 2px 8px;
                    border-radius: 12px;
                    margin-left: 8px;
                    font-weight: 800;
                    display: inline-block;
                    vertical-align: middle;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.3);
                    color: #0f172a; /* Dark text for contrast */
                    text-shadow: none;
                }}
                .rank-1 {{ background: linear-gradient(135deg, #FFD700 0%, #FDB931 100%); border: 1px solid #E6C200; }}
                .rank-2 {{ background: linear-gradient(135deg, #E0E0E0 0%, #B0B0B0 100%); border: 1px solid #A0A0A0; }}
                .rank-3 {{ background: linear-gradient(135deg, #CD7F32 0%, #A0522D 100%); border: 1px solid #8B4513; color: #fff; }}
                .rank-other {{ background: var(--bg-panel-hover); color: var(--text-secondary); border: 1px solid var(--border); }}
                
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
                    overflow-x: auto;
                    max-height: 80vh; /* Allow scrolling within the table */
                    overflow-y: auto;
                }}
                
                .data-table {{ width: 100%; border-collapse: collapse; text-align: left; }}
                .data-table th {{
                    padding: 1rem;
                    background: var(--bg-panel); 
                    color: var(--text-secondary);
                    font-size: 0.75rem;
                    text-transform: uppercase;
                    cursor: pointer;
                    position: sticky; /* Sticky Header */
                    top: 0;
                    z-index: 10;
                    border-bottom: 2px solid var(--border); 
                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); 
                }}
                .data-table td {{ padding: 1rem; border-bottom: 1px solid var(--border); color: var(--text-primary); }}
                
                /* Zebra Striping & Hover */
                .data-table tr:nth-child(even) {{ background: rgba(255, 255, 255, 0.02); }}
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
                
                /* Modal */
                .modal-overlay {{
                    display: none;
                    position: fixed;
                    top: 0; left: 0;
                    width: 100%; height: 100%;
                    background: rgba(0,0,0,0.8);
                    z-index: 1000;
                    justify-content: center;
                    align-items: center;
                }}
                .modal-content {{
                    background: var(--bg-panel);
                    width: 90%;
                    max-width: 1000px;
                    height: 80vh; /* Fixed height relative to viewport */
                    max-height: 800px;
                    border-radius: 12px;
                    padding: 20px;
                    position: relative;
                    display: flex;
                    flex-direction: column;
                    overflow: hidden; /* Contain children */
                }}
                .close-btn {{
                    position: absolute;
                    top: 15px; right: 20px;
                    font-size: 24px;
                    cursor: pointer;
                    color: var(--text-secondary);
                    z-index: 10; /* Ensure visible above scroll */
                }}
                #chart-container {{
                    flex-grow: 1;
                    width: 100%;
                    margin-top: 10px;
                    display: flex;
                    flex-direction: column;
                    overflow-y: auto; /* Enable Scrolling */
                    min-height: 0; /* Required for flex scrolling */
                    padding-right: 5px; /* Space for scrollbar */
                }}
                .metric-row {{
                    display: flex;
                    justify-content: space-between;
                    padding: 4px 0;
                    border-bottom: 1px dashed var(--border);
                }}
                .metric-row:last-child {{ border-bottom: none; }}
                .metric-row .label {{ color: var(--text-tertiary); font-size: 0.85rem; }}
                .metric-row .val {{ color: var(--text-primary); font-family: 'JetBrains Mono', monospace; font-size: 0.9rem; }}
            </style>
            <script src="https://unpkg.com/lightweight-charts@4.1.1/dist/lightweight-charts.standalone.production.js"></script>
        </head>
        <body>
            <nav>
                <div class="brand">PSE<span>PRO</span> v2.0</div>
                <div class="nav-item active" onclick="showSection('overview')">
                    Market Overview <span class="nav-badge">All</span>
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
                    </div>
                    <div style="font-size:0.8rem; color:var(--text-tertiary);">Last Updated: {timestamp}</div>
                </header>
                
                <main>
                    <!-- OVERVIEW (All Stocks Grid) -->
                    <div id="overview" class="section active">
                        <h2 style="margin-bottom:1.5rem;">Market Overview</h2>
                        
                        <!-- Search Controls -->
                        <div style="margin-bottom: 2rem; display: flex; gap: 15px; align-items: center; background: var(--bg-panel); padding: 20px; border-radius: 12px; border: 1px solid var(--border);">
                    <div class="search-container" style="display:flex; gap:12px; align-items:center;">
                         <!-- Search Input -->
                        <div class="search-input-wrapper" style="position:relative; flex-grow:1;">
                             <span style="position:absolute; left:12px; top:50%; transform:translateY(-50%); color:#64748b;">
                                <svg width="16" height="16" fill="none" class="feather feather-search" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
                            </span>
                            <input type="text" id="search_input" onkeyup="filterStocks()" placeholder="Search symbol or company..." style="width:100%; padding:10px 10px 10px 36px; background:#1e293b; border:1px solid #334155; color:#fff; border-radius:6px; outline:none;">
                        </div>

                        <!-- Filter: Sector -->
                        <select id="filter_sector" onchange="filterStocks()" style="padding:10px; background:#1e293b; border:1px solid #334155; color:#fff; border-radius:6px; outline:none; cursor:pointer;">
                            <option value="All">All Sectors</option>
                            {sector_options}
                        </select>
                        
                         <!-- Filter: Trend -->
                        <select id="filter_trend" onchange="filterStocks()" style="padding:10px; background:#1e293b; border:1px solid #334155; color:#fff; border-radius:6px; outline:none; cursor:pointer;">
                            <option value="all">Trend: All</option>
                            <option value="uptrend">Uptrend</option>
                            <option value="strong">Strong Uptrend</option>
                            <option value="golden">Golden Cross</option>
                        </select>
                        
                        <!-- Filter: Value -->
                        <select id="filter_val" onchange="filterStocks()" style="padding:10px; background:#1e293b; border:1px solid #334155; color:#fff; border-radius:6px; outline:none; cursor:pointer;">
                            <option value="all">Value: All</option>
                            <option value="cheap">Cheap (P/E < 15)</option>
                            <option value="fair">Fair (P/E < 25)</option>
                        </select>
                        
                        <!-- Filter: Yield -->
                        <select id="filter_yield" onchange="filterStocks()" style="padding:10px; background:#1e293b; border:1px solid #334155; color:#fff; border-radius:6px; outline:none; cursor:pointer;">
                            <option value="all">Yield: All</option>
                            <option value="3">Yield > 3%</option>
                            <option value="6">Yield > 6%</option>
                        </select>
                    </div>
                        </div>

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
                                        <th onclick="sortTable('table_top_picks', 3, 'num')" title="Monthly Win Rate & Avg Return">Consistency ⬍</th>
                                        <th onclick="sortTable('table_top_picks', 4)" title="Dividend Frequency">Freq ⬍</th>
                                        <th onclick="sortTable('table_top_picks', 5, 'num')" title="Dividend Yield">Yield ⬍</th>
                                        <th onclick="sortTable('table_top_picks', 6, 'num')" title="Price-to-Earnings Ratio">P/E ⬍</th>
                                        <th onclick="sortTable('table_top_picks', 7, 'num')" title="Confidence Score">Score ⬍</th>
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
                        <h2 style="margin-bottom:1.5rem;">Dividend Gems <span class="nav-badge" style="font-size:1rem;">{len(div_picks)}</span></h2>
                         <div class="table-container">
                            <table class="data-table" id="table_dividends">
                                <thead>
                                    <tr>
                                        <th onclick="sortTable('table_dividends', 0)" title="Stock Symbol">Symbol ⬍</th>
                                        <th onclick="sortTable('table_dividends', 1, 'num')" title="Last Closing Price">Price ⬍</th>
                                        <th onclick="sortTable('table_dividends', 2, 'num')" title="Annual Dividend Yield: Return on investment from dividends.&#10;Formula: (Annual Div / Price) * 100&#10;&#10;Guide:&#10;• < 2%: Low (Typical for Growth Stocks)&#10;• 2% - 5%: Good (Beats Banks/Inflation)&#10;• > 6%: Great (High Income)&#10;• > 10%: Caution (Risk of 'Value Trap')">Yield ⬍</th>
                                        <th onclick="sortTable('table_dividends', 3, 'num')" title="Total Annual Dividend">Est. Div (₱) ⬍</th>
                                        <th onclick="sortTable('table_dividends', 4, 'num')" title="Earnings Per Share (Basis for Payout)">EPS ⬍</th>
                                        <th onclick="sortTable('table_dividends', 5, 'num')" title="Payout Ratio">Payout ⬍</th>
                                        <th onclick="sortTable('table_dividends', 6, 'num')" title="Payments per year">Freq ⬍</th>
                                        <th title="Payment Months">Schedule</th>
                                        <th onclick="sortTable('table_dividends', 8, 'num')" title="Price-to-Earnings Ratio">P/E ⬍</th>
                                        <th onclick="sortTable('table_dividends', 9)" title="Trend Direction">Trend ⬍</th>
                                        <th onclick="sortTable('table_dividends', 10, 'num')" title="Safety Score">Score ⬍</th>
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
                    // Update Active State
                    if (!document.getElementById(id)) return;
                    
                    if (id !== 'search_results' && id !== 'search_tab') {{
                        document.getElementById('search_input').value = "";
                        previousSectionId = id;
                        // Reset filters
                        document.getElementById('filter_sector').value = "All";
                        document.getElementById('filter_trend').value = "all";
                        document.getElementById('filter_val').value = "all";
                        document.getElementById('filter_yield').value = "all";
                        filterStocks(); 
                    }}
                    
                    document.querySelectorAll('.section').forEach(el => el.classList.remove('active'));
                    document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
                    
                    document.getElementById(id).classList.add('active');
                    
                     // Highlight nav
                     let navLink = document.querySelector(`.nav-item[onclick*="'${{id}}'"]`);
                     if (navLink) navLink.classList.add('active');
                }}
                
                function filterStocks() {{
                    let input = document.getElementById('search_input');
                    let filter = input.value.toUpperCase();
                    
                    let sectorVal = document.getElementById('filter_sector').value;
                    let trendVal = document.getElementById('filter_trend').value;
                    let valVal = document.getElementById('filter_val').value;
                    let yieldVal = document.getElementById('filter_yield').value;
                    
                    let grid = document.getElementById('all_stocks_grid');
                    let cards = grid.getElementsByClassName('card');
                    let visibleCount = 0;
                    
                    for (let i = 0; i < cards.length; i++) {{
                        let card = cards[i];
                        let txtValue = card.getAttribute('data-name');
                        let symValue = card.querySelector('.symbol').innerText;
                        let secValue = card.getAttribute('data-sector');
                        
                        let trendAttr = card.getAttribute('data-trend') || "";
                        let peAttr = parseFloat(card.getAttribute('data-pe') || "999");
                        let yieldAttr = parseFloat(card.getAttribute('data-yield') || "0");
                        let goldenAttr = card.getAttribute('data-golden') === "true";
                        
                        let show = true;
                        
                        // 1. Text Search
                        if (filter) {{
                            if (txtValue.toUpperCase().indexOf(filter) === -1 && symValue.toUpperCase().indexOf(filter) === -1) {{
                                show = false;
                            }}
                        }}
                        
                        // 2. Sector Filter
                        if (sectorVal !== 'All' && secValue !== sectorVal) {{
                            show = false;
                        }}
                        
                        // 3. Trend Filter
                        if (trendVal !== 'all') {{
                            if (trendVal === 'uptrend' && trendAttr.indexOf('Uptrend') === -1) show = false;
                            if (trendVal === 'strong' && trendAttr.indexOf('Strong Uptrend') === -1) show = false;
                            if (trendVal === 'golden' && !goldenAttr) show = false;
                        }}
                        
                        // 4. Value Filter
                        if (valVal !== 'all') {{
                            if (valVal === 'cheap' && (peAttr > 15 || isNaN(peAttr))) show = false;
                            if (valVal === 'fair' && (peAttr > 25 || isNaN(peAttr))) show = false;
                        }}
                        
                        // 5. Yield Filter
                        if (yieldVal !== 'all') {{
                            let minYield = parseFloat(yieldVal);
                            if (yieldAttr < minYield) show = false;
                        }}
                        
                        if (show) {{
                            card.style.display = "";
                            visibleCount++;
                        }} else {{
                            card.style.display = "none";
                        }}
                    }}
                    
                    // Update Count
                    let countEl = document.getElementById('overview_count');
                    if(countEl) countEl.innerText = visibleCount;
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
                                if (xVal > yVal) {{
                                    shouldSwitch = true;
                                    break;
                                }}
                            }} else if (dir == "desc") {{
                                if (xVal < yVal) {{
                                    shouldSwitch = true;
                                    break;
                                }}
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

            <!-- Modal -->
            <div id="chartModal" class="modal-overlay">
                <div class="modal-content">
                    <span class="close-btn" onclick="closeModal()">&times;</span>
                    <h2 id="modalTitle" style="margin:0;">Stock Chart</h2>
                    <div id="chart-container"></div>
                </div>
            </div>

            <script>
                let chart; 
                
                function formatCurrency(val) {{
                    if (!val) return "-";
                    if (val >= 1e12) return "₱" + (val / 1e12).toFixed(2) + "T";
                    if (val >= 1e9) return "₱" + (val / 1e9).toFixed(2) + "B";
                    if (val >= 1e6) return "₱" + (val / 1e6).toFixed(2) + "M";
                    return "₱" + val.toLocaleString();
                }}

                function formatNumber(val) {{
                    if (!val) return "-";
                    if (val >= 1e12) return (val / 1e12).toFixed(2) + "T";
                    if (val >= 1e9) return (val / 1e9).toFixed(2) + "B";
                    if (val >= 1e6) return (val / 1e6).toFixed(2) + "M";
                    return val.toLocaleString();
                }}

                function showStockDetails(symbol) {{
                    const data = STOCK_DATA[symbol];
                    if(!data) return;
                    
                    document.getElementById('chartModal').style.display = 'flex';
                    
                    // 1. HEADER
                    const headerHtml = `
                        <div style="display:flex; justify-content:space-between; align-items:end; margin-bottom:15px;">
                            <div>
                                <h2 style="margin:0; color:var(--text-primary); font-family:'JetBrains Mono'; font-size:1.8rem;">${{data.symbol}}</h2>
                                <div style="color:var(--text-secondary); font-size:0.9rem;">${{data.name}}</div>
                            </div>
                            <div style="text-align:right; font-size:0.8rem; color:var(--text-tertiary);">
                                <div><span style="color:var(--accent);">${{data.sector}}</span> <span style="margin:0 4px;">•</span> ${{data.subsector}}</div>
                                <div>Listed: ${{data.listing_date}}</div>
                            </div>
                        </div>
                    `;
                    document.getElementById('modalTitle').innerHTML = headerHtml;
                    
                    
                    // 2. FUNDAMENTAL STATS GRID
                    let caps = formatCurrency(parseFloat(data.mkt_cap));
                    let yieldVal = parseFloat(data.divYield) > 0 ? parseFloat(data.divYield).toFixed(2) + "%" : "-";
                    let peVal = parseFloat(data.pe) > 0 ? parseFloat(data.pe).toFixed(2) : "-";
                    let epsVal = parseFloat(data.eps) != 0 ? parseFloat(data.eps).toFixed(2) : "-";
                    
                    const statsHtml = `
                        <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap:10px; margin-bottom:20px; background:var(--bg-panel); padding:15px; border-radius:8px; border:1px solid var(--border);">
                            <div class="metric"><span class="metric-label" title="Market Capitalization: Total value of all shares.\nFormula: Price x Outstanding Shares.\nDenomination: B = Billions, T = Trillions">Market Cap ⓘ</span><span class="metric-val mono" style="color:#fff;">${{caps}}</span></div>
                            <div class="metric"><span class="metric-label">P/E Ratio</span><span class="metric-val mono">${{peVal}}</span></div>
                            <div class="metric"><span class="metric-label">EPS</span><span class="metric-val mono">${{epsVal}}</span></div>
                            <div class="metric"><span class="metric-label">Div Yield</span><span class="metric-val mono text-green">${{yieldVal}}</span></div>
                            <div class="metric"><span class="metric-label">52-Wk High</span><span class="metric-val mono text-green">${{data.high_52.toFixed(2)}}</span></div>
                            <div class="metric"><span class="metric-label">52-Wk Low</span><span class="metric-val mono text-red">${{data.low_52.toFixed(2)}}</span></div>
                        </div>

                        <div style="margin-bottom:20px; background:rgba(59, 130, 246, 0.05); padding:15px; border-radius:8px; border:1px solid rgba(59, 130, 246, 0.2);">
                            <h3 style="font-size:0.9rem; margin-bottom:10px; color:var(--accent); text-transform:uppercase; letter-spacing:1px; font-weight:700;">Trading Plan</h3>
                            <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap:15px;">
                                <div class="metric">
                                    <span class="metric-label">Support Level</span>
                                    <span class="metric-val mono">₱${{parseFloat(data.support).toFixed(2)}}</span>
                                </div>
                                <div class="metric">
                                    <span class="metric-label" style="color:var(--red);">Suggested Stop Loss</span>
                                    <span class="metric-val mono text-red" style="font-weight:700; font-size:1.1rem;">₱${{parseFloat(data.stop_loss).toFixed(2)}}</span>
                                    <span style="font-size:0.75rem; color:var(--text-tertiary);">Risk: -${{parseFloat(data.risk_pct).toFixed(1)}}%</span>
                                </div>
                                <div class="metric">
                                    <span class="metric-label" style="color:var(--green);">Target (Resistance)</span>
                                    <span class="metric-val mono text-green">₱${{parseFloat(data.resistance).toFixed(2)}}</span>
                                </div>
                            </div>
                        </div>
                    `;
                    
                    // 3. CHART CONTAINER
                    const container = document.getElementById('chart-container');
                    container.innerHTML = statsHtml + '<div id="main-chart" style="width:100%; height:400px; flex-shrink: 0; border:1px solid var(--border); border-radius:8px; overflow:hidden;"></div>';
                    
                    // 4. DIVIDEND HISTORY (Bottom)
                    let divs = data.div_history;
                    if (divs && divs.length > 0) {{
                        let rows = "";
                        divs.slice(0, 5).forEach(d => {{
                             rows += `<tr>
                                <td style="padding:8px; border-bottom:1px solid #334155; font-size:0.8rem;">${{d.ex_date}}</td>
                                <td style="padding:8px; border-bottom:1px solid #334155; font-size:0.8rem;">${{d.pay_date}}</td>
                                <td style="padding:8px; border-bottom:1px solid #334155; font-size:0.8rem;">${{d.type}}</td>
                                <td style="padding:8px; border-bottom:1px solid #334155; font-size:0.8rem; font-family:'JetBrains Mono'; text-align:right;">₱${{parseFloat(d.amount).toFixed(4)}}</td>
                             </tr>`;
                        }});
                        
                        container.innerHTML += `
                            <div style="margin-top:20px;">
                                <h3 style="font-size:1rem; margin-bottom:10px; color:var(--text-secondary);">Recent Dividends</h3>
                                <table style="width:100%; border-collapse:collapse;">
                                    <thead>
                                        <tr style="text-align:left; color:var(--text-tertiary); font-size:0.75rem; text-transform:uppercase;">
                                            <th style="padding:8px;">Ex-Date</th>
                                            <th style="padding:8px;">Pay-Date</th>
                                            <th style="padding:8px;">Type</th>
                                            <th style="padding:8px; text-align:right;">Amount</th>
                                        </tr>
                                    </thead>
                                    <tbody>${{rows}}</tbody>
                                </table>
                            </div>
                        `;
                    }}
                    
                    // 5. RECENT NEWS
                    if (data.news && data.news.length > 0) {{
                        let newsHtml = '<div style="margin-top:20px; border-top:1px solid #334155; padding-top:15px;">';
                        newsHtml += '<h3 style="font-size:1rem; margin-bottom:10px; color:var(--text-secondary);">Recent News</h3>';
                        newsHtml += '<div style="display:flex; flex-direction:column; gap:10px;">';
                        
                        data.news.forEach(item => {{
                            newsHtml += `
                            <div style="background:var(--bg-secondary); padding:10px; border-radius:6px; border:1px solid var(--border);">
                                <a href="${{item.link}}" target="_blank" style="display:block; color:var(--text-primary); text-decoration:none; font-weight:600; margin-bottom:4px; font-size:0.95rem;">${{item.title}}</a>
                                <div style="display:flex; justify-content:space-between; font-size:0.75rem; color:var(--text-tertiary);">
                                    <span>${{item.source}}</span>
                                    <span>${{new Date(item.date).toLocaleDateString()}}</span>
                                </div>
                            </div>
                            `;
                        }});
                        
                        newsHtml += '</div></div>';
                        container.innerHTML += newsHtml;
                    }}

                    // RENDER CHART
                    // Parse data
                    const historyData = data.history || [];
                    const chartDiv = document.getElementById('main-chart');
                    
                    if(!historyData || historyData.length === 0) {{
                        chartDiv.innerHTML = '<div style="display:flex; height:100%; justify-content:center; align-items:center; color:var(--text-tertiary);">No Price History Available</div>';
                        return;
                    }}

                    chart = LightweightCharts.createChart(chartDiv, {{
                        width: chartDiv.clientWidth,
                        height: chartDiv.clientHeight,
                        layout: {{
                            background: {{ type: 'solid', color: '#1e293b' }},
                            textColor: '#94a3b8',
                        }},
                        grid: {{
                            vertLines: {{ color: '#334155' }},
                            horzLines: {{ color: '#334155' }},
                        }},
                         rightPriceScale: {{
                            borderColor: '#485c7b',
                        }},
                        timeScale: {{
                            borderColor: '#485c7b',
                        }},
                    }});

                    const candlestickSeries = chart.addCandlestickSeries({{
                        upColor: '#10b981',
                        downColor: '#ef4444', 
                        borderVisible: false, 
                        wickUpColor: '#10b981',
                        wickDownColor: '#ef4444',
                    }});

                    candlestickSeries.setData(historyData);
                    chart.timeScale().fitContent();
                    
                    // ResizeObserver to handle modal resize
                    new ResizeObserver(entries => {{
                        if (entries.length === 0 || entries[0].target !== chartDiv) {{ return; }}
                        const newRect = entries[0].contentRect;
                        chart.applyOptions({{ width: newRect.width, height: newRect.height }});
                    }}).observe(chartDiv);
                }}

                function closeModal() {{
                    document.getElementById('chartModal').style.display = 'none';
                    if (chart) {{
                        chart.remove();
                        chart = null;
                    }}
                }}
                
                // Close on click outside
                window.onclick = function(event) {{
                    const modal = document.getElementById('chartModal');
                    if (event.target == modal) {{
                        closeModal();
                    }}
                }}
            </script>
            <!-- Inject Global Data -->
            <script>
                const STOCK_DATA = {json.dumps(self.all_stock_data)};
            </script>
        </body>
        </html>
        """
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return os.path.abspath(output_file)

    def open_in_browser(self, file_path: str):
        webbrowser.open('file://' + file_path)
