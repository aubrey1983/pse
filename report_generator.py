# report_generator.py
# Generates modern HTML dashboard for stock analysis
import datetime
import webbrowser
import os
import json
import base64
from typing import Dict
from stock_data import STOCK_CATEGORIES, normalize_sector
from analyzer import Analyzer
from portfolio_manager import PortfolioManager

class ReportGenerator:
    def __init__(self):
        self.analyzer = Analyzer()
        self.portfolio_mgr = PortfolioManager()

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
                        <div class="symbol mono" style="color:var(--accent); display:flex; align-items:center;">
                            {item['symbol']} 
                            <span class="watchlist-btn" onclick="event.stopPropagation(); openAddModal('{item['symbol']}', {t['last_close']})" title="Add to Portfolio">☆</span>
                        </div>
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
        
        # RELOAD PORTFOLIO DATA (Crucial for interactive updates)
        self.portfolio_mgr.portfolio = self.portfolio_mgr.load_portfolio()
        
        # Load Data
        tech_data = self.load_json("data/technical_data.json")
        # metadata.json is for progress, stock_metadata.json is official info
        stock_meta = self.load_json("data/stock_metadata.json") 
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Load Official Fundamentals (Deep Scrape)
        official_fund = self.load_json("data/pse_fundamentals.json")
        
        # Load News Data
        self.news_data = self.load_json("data/news_data.json")

        # Load Industry Metadata Health
        metadata_health = self.load_json("data/metadata_health.json")
        if not metadata_health:
            metadata_health = {
                "status": "unknown",
                "generated_at": "-",
                "symbol_count": len(stock_meta),
                "sector_counts": {},
                "missing_sector": [],
                "invalid_sector": [],
                "normalized_changes": [],
                "schema_warnings": [],
            }

        daily_actions = self.load_json("data/daily_actions.json")
        if not daily_actions:
            daily_actions = {
                "generated_at": "-",
                "summary": {"review_risk": 0, "add": 0, "watchlist": 0, "trim_watch": 0, "hold": 0},
                "actions": [],
            }
        action_lookup = {item.get("symbol"): item for item in daily_actions.get("actions", [])}

        action_outcomes = self.load_json("data/action_outcomes.json")
        if not action_outcomes:
            action_outcomes = {
                "generated_at": "-",
                "horizons": [5, 10, 20, 30],
                "summary": {},
                "learning_profile": {},
                "outcomes": [],
            }

        action_history = self.load_json("data/daily_action_history.json")
        if not isinstance(action_history, list):
            action_history = []

        sector_fallback = {}
        for outcome in action_outcomes.get("outcomes", []):
            sector = outcome.get("sector")
            if sector and sector != "Unknown":
                sector_fallback.setdefault(outcome.get("symbol"), sector)
        for day in action_history:
            for action in day.get("tracked_actions", []):
                sector = action.get("sector")
                if sector and sector != "Unknown":
                    sector_fallback.setdefault(action.get("symbol"), sector)

        def parse_date(value):
            if not value or value == "-":
                return None
            try:
                if "T" in value:
                    return datetime.datetime.fromisoformat(value.replace("Z", "+00:00")).date()
                return datetime.date.fromisoformat(value[:10])
            except Exception:
                return None

        def days_old(value):
            parsed = parse_date(value)
            if not parsed:
                return None
            return (datetime.datetime.now(datetime.timezone.utc).date() - parsed).days

        latest_market_date = "-"
        market_dates = []
        for tech in tech_data.values():
            for row in tech.get("history", []):
                if row.get("time"):
                    market_dates.append(row["time"])
        if market_dates:
            latest_market_date = max(market_dates)

        market_age = days_old(latest_market_date)
        actions_age = days_old(daily_actions.get("generated_at"))
        outcomes_age = days_old(action_outcomes.get("generated_at"))
        metadata_age = days_old(metadata_health.get("generated_at"))
        market_fresh = market_age is not None and market_age <= 5
        actions_fresh = actions_age is not None and actions_age <= 2
        outcomes_fresh = outcomes_age is not None and outcomes_age <= 2
        metadata_ok = metadata_health.get("status") == "ok"
        core_files = [
            "data/technical_data.json",
            "data/pse_fundamentals.json",
            "data/daily_actions.json",
            "data/action_outcomes.json",
            "data/metadata_health.json",
        ]
        missing_core_files = [path for path in core_files if not os.path.exists(path)]
        health_issues = []
        if not market_fresh:
            health_issues.append("Market data may be stale")
        if not actions_fresh:
            health_issues.append("Daily action plan may be stale")
        if not outcomes_fresh:
            health_issues.append("Action outcomes may be stale")
        if not metadata_ok:
            health_issues.append("Industry metadata needs attention")
        if missing_core_files:
            health_issues.append(f"Missing files: {', '.join(missing_core_files)}")

        system_status = "Fresh" if not health_issues else "Needs Attention" if len(health_issues) >= 2 else "Stale"
        system_cls = "action-good" if system_status == "Fresh" else "action-risk" if system_status == "Needs Attention" else "action-watch"
        health_issue_text = "; ".join(health_issues) if health_issues else "All core dashboard inputs are present and recent."
        
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
                        "mom_score": 0, # Month-on-month gain objective score
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

                    mom_score, mom_reasons = self.analyzer.calculate_monthly_gain_score(t, f)
                    item['mom_score'] = mom_score
                    item['mom_reasons'] = mom_reasons
                    
                    if sector in grouped_data:
                        grouped_data[sector].append(item)
                    
                    # Threshold for "Top Pick" now targets month-on-month gain quality.
                    if mom_score >= 35:
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
        # Top Picks: Sort by month-on-month objective score, then classic score.
        top_picks.sort(key=lambda x: (x['mom_score'], x['score'], x['fund'].get('div_yield', 0)), reverse=True)
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

        # --- PORTFOLIO DATA ---
        # Create a simplified price map for the portfolio manager
        current_prices = {s: tech_data.get(s, {}).get('last_close', 0) for s in tech_data}
        # Fallback to metadata price if tech data missing? Usually tech data is source of truth.
        portfolio_summary = self.portfolio_mgr.get_portfolio_summary(current_prices)

        # --- HTML COMPONENT GENERATION ---
        
        # 1. Industry Nav
        industry_nav = ""
        for cat in sorted_sectors:
            if cat not in grouped_data or not grouped_data[cat]: continue
            count = len(grouped_data[cat])
            cat_id = cat.replace(" ", "_").replace("&", "").replace(",", "")
            industry_nav += f'<div class="nav-item" data-section="{cat_id}" onclick="showSection(\'{cat_id}\')">{cat} <span class="nav-badge">{count}</span></div>'
            
        # 2. All Cards (Overview) - Flat A-Z List
        all_cards_html = ""
        
        # Flatten all grouped data to get unique items for Overview
        all_overview_items = []
        for cat, items in grouped_data.items():
            all_overview_items.extend(items)
            
        # Sort All Overview Items by Symbol
        all_overview_items.sort(key=lambda x: x['symbol'])

        active_items = [item for item in all_overview_items if item['tech'].get('last_close', 0) > 0]
        uptrend_count = len([item for item in active_items if "Uptrend" in item['tech'].get('trend', '')])
        dividend_count = len([item for item in active_items if item['fund'].get('div_yield', 0) > 0])
        strong_mom_count = len([item for item in active_items if item.get('mom_score', 0) >= 45])
        market_breadth = (uptrend_count / len(active_items) * 100.0) if active_items else 0.0
        avg_mom_score = (sum(item.get('mom_score', 0) for item in active_items) / len(active_items)) if active_items else 0.0
        
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
            reasons = item.get('mom_reasons', [])
            score_tooltip_text = "&#10;".join(reasons)
            score_val = item.get('mom_score', 0)
            
            score_cls = "text-muted"
            if score_val >= 50: score_cls = "green" # High MoM quality
            elif score_val >= 35: score_cls = "accent" # Medium MoM quality
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
                        <div class="mono" style="font-weight:700; color:var(--accent); display:flex; align-items:center;">
                            {item['symbol']} {badge_html}
                            <span class="watchlist-btn" onclick="event.stopPropagation(); openAddModal('{item['symbol']}', {t['last_close']})" title="Add to Portfolio">☆</span>
                        </div>
                        <div style="font-size:0.75rem; color:#64748b;">{name[:20]}</div>
                    </td>
                    <td class="mono">₱{t['last_close']:.2f}</td>
                    <td><span class="{trend_cls}">{trend}</span></td>
                    <td class="mono">{consistency_display}</td>
                    <td class="mono" style="font-size:0.8rem;">{freq}</td>
                    <td class="mono {yield_cls}">{yield_display}</td>
                    <td class="mono">{pe}</td>
                    <td class="mono" title="{score_tooltip_text}">
                        <span class="{score_cls}" style="font-weight:bold; padding:2px 8px; border-radius:4px;">{item['mom_score']}</span>
                    </td>
                    <td class="mono" title="Original confidence score">
                        {item['score']}
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
                        <div class="mono" style="font-weight:700; color:var(--accent); display:flex; align-items:center;">
                            {item['symbol']}
                            <span class="watchlist-btn" onclick="event.stopPropagation(); openAddModal('{item['symbol']}', {t['last_close']})" title="Add to Portfolio">☆</span>
                        </div>
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

        # --- DATA HEALTH HTML ---
        health_status = metadata_health.get("status", "unknown")
        health_cls = "action-good" if health_status == "ok" else "action-watch" if health_status == "warning" else "action-risk"
        sector_rows = ""
        for sector, count in metadata_health.get("sector_counts", {}).items():
            sector_rows += f"""
                <tr>
                    <td>{sector}</td>
                    <td class="mono">{count}</td>
                </tr>
            """

        normalized_changes = metadata_health.get("normalized_changes", [])
        schema_warnings = metadata_health.get("schema_warnings", [])
        invalid_sector = metadata_health.get("invalid_sector", [])
        missing_sector = metadata_health.get("missing_sector", [])

        normalized_preview = ", ".join([f"{x.get('symbol')} ({x.get('from')} -> {x.get('to')})" for x in normalized_changes[:6]]) or "None"
        schema_preview = ", ".join([f"{x.get('symbol')}: {x.get('issue')}" for x in schema_warnings[:6]]) or "None"
        invalid_preview = ", ".join([f"{x.get('symbol')} ({x.get('sector')})" for x in invalid_sector[:6]]) or "None"
        missing_preview = ", ".join(missing_sector[:12]) or "None"

        data_health_html = f"""
        <div id="data_health" class="section">
            <div class="page-head">
                <div>
                    <div class="eyebrow">System Health</div>
                    <h1 class="page-title">Data Freshness Monitor</h1>
                    <div class="page-subtitle">Checks whether the dashboard, action engine, outcome tracker, and industry metadata are working from recent source data.</div>
                </div>
                <span class="action-pill {system_cls}">{system_status.upper()}</span>
            </div>

            <div class="kpi-strip">
                <div class="kpi">
                    <div class="kpi-label">Market Data Date</div>
                    <div class="kpi-value" style="font-size:1.1rem;">{latest_market_date}</div>
                    <div class="kpi-note">{market_age if market_age is not None else '-'} calendar days old</div>
                </div>
                <div class="kpi">
                    <div class="kpi-label">Action Plan</div>
                    <div class="kpi-value" style="font-size:1.1rem;">{daily_actions.get('generated_at', '-')}</div>
                    <div class="kpi-note">{actions_age if actions_age is not None else '-'} calendar days old</div>
                </div>
                <div class="kpi">
                    <div class="kpi-label">Outcome Tracker</div>
                    <div class="kpi-value" style="font-size:1.1rem;">{action_outcomes.get('generated_at', '-')}</div>
                    <div class="kpi-note">{outcomes_age if outcomes_age is not None else '-'} calendar days old</div>
                </div>
                <div class="kpi">
                    <div class="kpi-label">Workflow</div>
                    <div class="kpi-value" style="font-size:1.1rem;">Weekdays</div>
                    <div class="kpi-note">10:00 UTC / 6:00 PM PH</div>
                </div>
            </div>

            <div class="glass-panel">
                <div class="panel-header">
                    <h3>Pipeline Status</h3>
                    <span class="status-pill">{system_status}</span>
                </div>
                <div class="metrics-grid">
                    <div class="metric-card"><span>Core Files Missing</span><strong>{len(missing_core_files)}</strong><small>{', '.join(missing_core_files) if missing_core_files else 'None'}</small></div>
                    <div class="metric-card"><span>Industry Metadata</span><strong>{health_status.upper()}</strong><small>{metadata_age if metadata_age is not None else '-'} calendar days old</small></div>
                    <div class="metric-card"><span>Tracked Outcomes</span><strong>{len(action_outcomes.get('outcomes', []))}</strong><small>Rows in performance tracker</small></div>
                    <div class="metric-card"><span>Daily Actions</span><strong>{daily_actions.get('summary', {}).get('total_actions', len(daily_actions.get('actions', [])))}</strong><small>Rows in action engine output</small></div>
                </div>
                <div style="margin-top:1rem; color:var(--text-secondary); font-size:0.9rem;">{health_issue_text}</div>
            </div>

            <div class="page-head" style="margin-top:1.5rem;">
                <div>
                    <div class="eyebrow">Data Health</div>
                    <h1 class="page-title" style="font-size:1.35rem;">Industry Metadata Audit</h1>
                    <div class="page-subtitle">Validates PSE sector groupings, schema consistency, and normalized sector labels used by the dashboard.</div>
                </div>
                <span class="action-pill {health_cls}">{health_status.upper()}</span>
            </div>

            <div class="kpi-strip">
                <div class="kpi">
                    <div class="kpi-label">Symbols Checked</div>
                    <div class="kpi-value">{metadata_health.get('symbol_count', 0)}</div>
                    <div class="kpi-note">Source: {metadata_health.get('source_file', 'data/stock_metadata.json')}</div>
                </div>
                <div class="kpi">
                    <div class="kpi-label">Missing Sectors</div>
                    <div class="kpi-value">{len(missing_sector)}</div>
                    <div class="kpi-note">Must be zero</div>
                </div>
                <div class="kpi">
                    <div class="kpi-label">Invalid Sectors</div>
                    <div class="kpi-value">{len(invalid_sector)}</div>
                    <div class="kpi-note">Outside approved taxonomy</div>
                </div>
                <div class="kpi">
                    <div class="kpi-label">Validated At</div>
                    <div class="kpi-value" style="font-size:1rem;">{metadata_health.get('generated_at', '-')}</div>
                    <div class="kpi-note">UTC timestamp</div>
                </div>
            </div>

            <div class="portfolio-command-grid">
                <div class="action-panel">
                    <div class="kpi-label" style="margin-bottom:0.75rem;">Audit Notes</div>
                    <div class="metric-row"><span class="label">Normalized labels</span><span class="val">{len(normalized_changes)}</span></div>
                    <div style="color:var(--text-secondary); font-size:0.82rem; margin:0.5rem 0 1rem;">{normalized_preview}</div>
                    <div class="metric-row"><span class="label">Schema warnings</span><span class="val">{len(schema_warnings)}</span></div>
                    <div style="color:var(--text-secondary); font-size:0.82rem; margin:0.5rem 0 1rem;">{schema_preview}</div>
                    <div class="metric-row"><span class="label">Missing sector symbols</span><span class="val">{len(missing_sector)}</span></div>
                    <div style="color:var(--text-secondary); font-size:0.82rem; margin-top:0.5rem;">{missing_preview}</div>
                    <div class="metric-row" style="margin-top:1rem;"><span class="label">Invalid sector symbols</span><span class="val">{len(invalid_sector)}</span></div>
                    <div style="color:var(--text-secondary); font-size:0.82rem; margin-top:0.5rem;">{invalid_preview}</div>
                </div>

                <div class="table-container">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Sector</th>
                                <th>Symbols</th>
                            </tr>
                        </thead>
                        <tbody>
                            {sector_rows}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        """

        # --- DAILY ACTIONS HTML ---
        action_rows = ""
        action_class_map = {
            "Add": "action-good",
            "Review Risk": "action-risk",
            "Trim Watch": "action-watch",
            "Watchlist": "action-watch",
            "Hold": "action-neutral",
        }

        def stock_onclick(symbol):
            tech = tech_data.get(symbol, {})
            if not symbol or not tech:
                return ""
            official = stock_meta.get(symbol, {})
            action_meta = action_lookup.get(symbol, {})
            if not official.get("sector") and action_meta.get("sector"):
                official = {**official, "sector": action_meta.get("sector")}
            if (not official.get("sector") or official.get("sector") == "Unknown") and sector_fallback.get(symbol):
                official = {**official, "sector": sector_fallback.get(symbol)}
            item = {
                "symbol": symbol,
                "company_name": official.get("name", symbol),
                "tech": tech,
                "fund": official_fund.get(symbol, {}),
            }
            return self._generate_onclick(item, official)

        for action in daily_actions.get("actions", [])[:40]:
            plan = action.get("trade_plan", {})
            action_cls = action_class_map.get(action.get("action"), "action-neutral")
            reasons = "; ".join(action.get("reasons", [])[:3])
            row_click = stock_onclick(action.get("symbol"))
            action_rows += f"""
                <tr {row_click}>
                    <td class="mono" style="font-weight:800; color:var(--accent);">{action.get('symbol')}</td>
                    <td><span class="action-pill {action_cls}">{action.get('action')}</span></td>
                    <td class="mono">{action.get('priority', 0):.1f}</td>
                    <td>{action.get('source', '-')}</td>
                    <td>{action.get('sector', '-')}</td>
                    <td class="mono">{action.get('mom_score', 0)}</td>
                    <td>{action.get('trend', '-')}</td>
                    <td class="mono">₱{plan.get('entry_price', 0):.2f}</td>
                    <td class="mono">₱{plan.get('stop_loss', 0):.2f}</td>
                    <td class="mono">₱{plan.get('target_price', 0):.2f}</td>
                    <td class="mono">{plan.get('reward_risk', 0):.2f}</td>
                    <td class="mono">{plan.get('suggested_shares', 0):,.0f}</td>
                    <td style="min-width:260px; color:var(--text-secondary); font-size:0.82rem;">{reasons}</td>
                </tr>
            """

        action_summary = daily_actions.get("summary", {})
        add_readiness = daily_actions.get("add_readiness", {})
        add_thresholds = add_readiness.get("thresholds", {})
        allocation_plan = daily_actions.get("allocation_plan", {})
        paper_symbols = set()
        for item in allocation_plan.get("suggestions", []):
            if item.get("symbol"):
                paper_symbols.add(item.get("symbol"))
        for action in daily_actions.get("actions", []):
            if action.get("symbol"):
                paper_symbols.add(action.get("symbol"))

        paper_price_map = {}
        paper_sector_map = {}
        for symbol in paper_symbols:
            action_item = action_lookup.get(symbol, {})
            meta = stock_meta.get(symbol, {})
            tech = tech_data.get(symbol, {})
            plan = action_item.get("trade_plan", {})
            paper_price_map[symbol] = (
                plan.get("entry_price")
                or tech.get("last_close")
                or 0
            )
            paper_sector_map[symbol] = normalize_sector(
                meta.get("sector")
                or action_item.get("sector")
                or sector_fallback.get(symbol)
                or "Unknown"
            )

        paper_payload = {
            "market_date": daily_actions.get("market_date") or daily_actions.get("generated_at", "-"),
            "generated_at": daily_actions.get("generated_at", "-"),
            "allocation_plan": allocation_plan,
            "actions": daily_actions.get("actions", [])[:40],
            "prices": paper_price_map,
            "sectors": paper_sector_map,
            "starting_cash": max(float(allocation_plan.get("budget", 0) or 0) * 10, 100000.0),
        }
        closest_add_rows = ""
        for item in add_readiness.get("closest", [])[:12]:
            blockers = "; ".join(item.get("blockers", [])[:3]) or "Qualified"
            row_click = stock_onclick(item.get("symbol"))
            closest_add_rows += f"""
                <tr {row_click}>
                    <td class="mono" style="font-weight:800; color:var(--accent);">{item.get('symbol')}</td>
                    <td>{item.get('source', '-')}</td>
                    <td>{item.get('sector', '-')}</td>
                    <td class="mono">{item.get('readiness_score', 0):.1f}</td>
                    <td class="mono">{item.get('mom_score', 0)} / {item.get('required_mom', 0)}</td>
                    <td>{item.get('trend', '-')}</td>
                    <td class="mono">{item.get('rsi', 0):.1f}</td>
                    <td class="mono">{item.get('reward_risk', 0):.2f} / {item.get('required_reward_risk', 0):.2f}</td>
                    <td class="mono">₱{item.get('entry_price', 0):.2f}</td>
                    <td style="min-width:300px; color:var(--text-secondary); font-size:0.82rem;">{blockers}</td>
                </tr>
            """

        allocation_rows = ""
        for item in allocation_plan.get("suggestions", []):
            row_click = stock_onclick(item.get("symbol"))
            allocation_rows += f"""
                <tr {row_click}>
                    <td class="mono" style="font-weight:800; color:var(--accent);">{item.get('symbol')}</td>
                    <td><span class="action-pill action-good">{item.get('action', 'Allocate')}</span></td>
                    <td>{item.get('sector', '-')}</td>
                    <td class="mono">₱{item.get('amount', 0):,.2f}</td>
                    <td class="mono">{item.get('shares', 0):,.0f}</td>
                    <td class="mono">₱{item.get('entry_price', 0):.2f}</td>
                    <td class="mono">{item.get('mom_score', 0)}</td>
                    <td class="mono">{item.get('reward_risk', 0):.2f}</td>
                    <td style="min-width:280px; color:var(--text-secondary); font-size:0.82rem;">{item.get('reason', '-')}</td>
                </tr>
            """

        waitlist_rows = ""
        for item in allocation_plan.get("waitlist", [])[:6]:
            blockers = "; ".join(item.get("blockers", [])[:2]) or "Waiting for confirmation"
            row_click = stock_onclick(item.get("symbol"))
            waitlist_rows += f"""
                <tr {row_click}>
                    <td class="mono" style="font-weight:800; color:var(--accent);">{item.get('symbol')}</td>
                    <td>{item.get('sector', '-')}</td>
                    <td class="mono">{item.get('readiness_score', 0):.1f}</td>
                    <td class="mono">{item.get('mom_score', 0)} / {item.get('required_mom', 0)}</td>
                    <td class="mono">{item.get('reward_risk', 0):.2f} / {item.get('required_reward_risk', 0):.2f}</td>
                    <td style="min-width:280px; color:var(--text-secondary); font-size:0.82rem;">{blockers}</td>
                </tr>
            """

        daily_actions_html = f"""
        <div id="daily_actions" class="section">
            <div class="page-head">
                <div>
                    <div class="eyebrow">Action Engine</div>
                    <h1 class="page-title">Today&apos;s Trade Plan</h1>
                    <div class="page-subtitle">Ranked actions combine portfolio exposure, MoM score, trend, stop risk, reward/risk, and position sizing rules.</div>
                </div>
                <div style="text-align:right; color:var(--text-tertiary); font-size:0.82rem;">
                    <div style="color:var(--text-secondary); font-weight:700;">Generated {daily_actions.get('generated_at', '-')}</div>
                    <div>Risk per trade: {daily_actions.get('settings', {}).get('risk_per_trade_pct', 1.0)}%</div>
                </div>
            </div>

            <div class="kpi-strip">
                <div class="kpi">
                    <div class="kpi-label">Review Risk</div>
                    <div class="kpi-value">{action_summary.get('review_risk', 0)}</div>
                    <div class="kpi-note">Positions needing attention</div>
                </div>
                <div class="kpi">
                    <div class="kpi-label">Add</div>
                    <div class="kpi-value">{action_summary.get('add', 0)}</div>
                    <div class="kpi-note">Meets buy and reward/risk rules</div>
                </div>
                <div class="kpi">
                    <div class="kpi-label">Watchlist</div>
                    <div class="kpi-value">{action_summary.get('watchlist', 0)}</div>
                    <div class="kpi-note">Strong setup, waiting for better entry</div>
                </div>
                <div class="kpi">
                    <div class="kpi-label">Trim Watch</div>
                    <div class="kpi-value">{action_summary.get('trim_watch', 0)}</div>
                    <div class="kpi-note">Allocation concentration checks</div>
                </div>
            </div>

            <div class="glass-panel">
                <div class="panel-header">
                    <h3>Rebalance Planner</h3>
                    <span class="status-pill">{allocation_plan.get('stance', 'Wait')}</span>
                </div>
                <div class="metrics-grid">
                    <div class="metric-card"><span>Monthly Budget</span><strong>₱{allocation_plan.get('budget', 0):,.0f}</strong><small>Capital available for new buys</small></div>
                    <div class="metric-card"><span>Suggested Spend</span><strong>₱{allocation_plan.get('budget', 0) - allocation_plan.get('remaining_budget', 0):,.0f}</strong><small>From qualified Add setups</small></div>
                    <div class="metric-card"><span>Remaining</span><strong>₱{allocation_plan.get('remaining_budget', 0):,.0f}</strong><small>Held back by rules</small></div>
                    <div class="metric-card"><span>Qualified Adds</span><strong>{len(allocation_plan.get('suggestions', []))}</strong><small>Ready for allocation</small></div>
                </div>
                <div style="margin-top:0.9rem; color:var(--text-secondary); font-size:0.86rem;">
                    {' '.join(allocation_plan.get('notes', []))}
                </div>
                <div class="table-container" style="margin-top:1rem;">
                    <table class="data-table" id="table_allocation_plan">
                        <thead>
                            <tr>
                                <th onclick="sortTable('table_allocation_plan', 0)">Symbol ↕</th>
                                <th onclick="sortTable('table_allocation_plan', 1)">Action ↕</th>
                                <th onclick="sortTable('table_allocation_plan', 2)">Sector ↕</th>
                                <th onclick="sortTable('table_allocation_plan', 3, 'num')">Amount ↕</th>
                                <th onclick="sortTable('table_allocation_plan', 4, 'num')">Shares ↕</th>
                                <th onclick="sortTable('table_allocation_plan', 5, 'num')">Entry ↕</th>
                                <th onclick="sortTable('table_allocation_plan', 6, 'num')">MoM ↕</th>
                                <th onclick="sortTable('table_allocation_plan', 7, 'num')">R/R ↕</th>
                                <th>Reason</th>
                            </tr>
                        </thead>
                        <tbody>
                            {allocation_rows or '<tr><td colspan="9" style="text-align:center; color:var(--text-tertiary);">No capital allocation today. The planner is waiting for a cleaner Add setup.</td></tr>'}
                        </tbody>
                    </table>
                </div>
                <div class="table-container" style="margin-top:1rem;">
                    <table class="data-table" id="table_allocation_waitlist">
                        <thead>
                            <tr>
                                <th onclick="sortTable('table_allocation_waitlist', 0)">Near Add ↕</th>
                                <th onclick="sortTable('table_allocation_waitlist', 1)">Sector ↕</th>
                                <th onclick="sortTable('table_allocation_waitlist', 2, 'num')">Ready ↕</th>
                                <th onclick="sortTable('table_allocation_waitlist', 3, 'num')">MoM / Need ↕</th>
                                <th onclick="sortTable('table_allocation_waitlist', 4, 'num')">R/R / Need ↕</th>
                                <th>Wait For</th>
                            </tr>
                        </thead>
                        <tbody>
                            {waitlist_rows or '<tr><td colspan="6" style="text-align:center; color:var(--text-tertiary);">No near-Add allocation candidates.</td></tr>'}
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="glass-panel">
                <div class="panel-header">
                    <h3>Add Readiness</h3>
                    <span class="status-pill">{add_readiness.get('qualified_count', 0)} qualified</span>
                </div>
                <div class="metrics-grid">
                    <div class="metric-card"><span>Portfolio Add MoM</span><strong>{add_thresholds.get('holding_add_mom', 45)}</strong><small>Held position threshold</small></div>
                    <div class="metric-card"><span>Candidate Add MoM</span><strong>{add_thresholds.get('candidate_add_mom', 50)}</strong><small>New position threshold</small></div>
                    <div class="metric-card"><span>Required R/R</span><strong>{add_thresholds.get('add_reward_risk', 1.2):.2f}</strong><small>Reward/risk hurdle</small></div>
                    <div class="metric-card"><span>Near Misses</span><strong>{add_readiness.get('near_miss_count', 0)}</strong><small>Closest non-Add setups</small></div>
                </div>
                <div class="table-container" style="margin-top:1rem;">
                    <table class="data-table" id="table_add_readiness">
                        <thead>
                            <tr>
                                <th onclick="sortTable('table_add_readiness', 0)">Symbol ↕</th>
                                <th onclick="sortTable('table_add_readiness', 1)">Source ↕</th>
                                <th onclick="sortTable('table_add_readiness', 2)">Sector ↕</th>
                                <th onclick="sortTable('table_add_readiness', 3, 'num')">Ready ↕</th>
                                <th onclick="sortTable('table_add_readiness', 4, 'num')">MoM / Need ↕</th>
                                <th onclick="sortTable('table_add_readiness', 5)">Trend ↕</th>
                                <th onclick="sortTable('table_add_readiness', 6, 'num')">RSI ↕</th>
                                <th onclick="sortTable('table_add_readiness', 7, 'num')">R/R / Need ↕</th>
                                <th onclick="sortTable('table_add_readiness', 8, 'num')">Entry ↕</th>
                                <th>What&apos;s Missing</th>
                            </tr>
                        </thead>
                        <tbody>
                            {closest_add_rows or '<tr><td colspan="10" style="text-align:center; color:var(--text-tertiary);">No near-miss Add candidates yet.</td></tr>'}
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="table-container">
                <table class="data-table" id="table_daily_actions">
                    <thead>
                        <tr>
                            <th onclick="sortTable('table_daily_actions', 0)">Symbol ↕</th>
                            <th onclick="sortTable('table_daily_actions', 1)">Action ↕</th>
                            <th onclick="sortTable('table_daily_actions', 2, 'num')">Priority ↕</th>
                            <th onclick="sortTable('table_daily_actions', 3)">Source ↕</th>
                            <th onclick="sortTable('table_daily_actions', 4)">Sector ↕</th>
                            <th onclick="sortTable('table_daily_actions', 5, 'num')">MoM ↕</th>
                            <th onclick="sortTable('table_daily_actions', 6)">Trend ↕</th>
                            <th onclick="sortTable('table_daily_actions', 7, 'num')">Entry ↕</th>
                            <th onclick="sortTable('table_daily_actions', 8, 'num')">Stop ↕</th>
                            <th onclick="sortTable('table_daily_actions', 9, 'num')">Target ↕</th>
                            <th onclick="sortTable('table_daily_actions', 10, 'num')">R/R ↕</th>
                            <th onclick="sortTable('table_daily_actions', 11, 'num')">Shares ↕</th>
                            <th>Rationale</th>
                        </tr>
                    </thead>
                    <tbody>
                        {action_rows}
                    </tbody>
                </table>
            </div>
        </div>
        """

        paper_trading_html = f"""
        <div id="paper_trading" class="section">
            <div class="page-head">
                <div>
                    <div class="eyebrow">Paper Execution</div>
                    <h1 class="page-title">Automated Paper Trading</h1>
                    <div class="page-subtitle">The action engine applies today&apos;s qualified allocation plan to a browser-local paper portfolio, with manual controls for review and overrides.</div>
                </div>
                <div style="text-align:right; color:var(--text-tertiary); font-size:0.82rem;">
                    <div style="color:var(--text-secondary); font-weight:700;">Market date {paper_payload.get('market_date', '-')}</div>
                    <div id="paper_auto_status">Waiting for sync</div>
                </div>
            </div>

            <div class="kpi-strip">
                <div class="kpi">
                    <div class="kpi-label">Paper Equity</div>
                    <div class="kpi-value mono" id="paper_equity">-</div>
                    <div class="kpi-note">Cash plus open positions</div>
                </div>
                <div class="kpi">
                    <div class="kpi-label">Cash</div>
                    <div class="kpi-value mono" id="paper_cash">-</div>
                    <div class="kpi-note">Available buying power</div>
                </div>
                <div class="kpi">
                    <div class="kpi-label">Invested</div>
                    <div class="kpi-value mono" id="paper_invested">-</div>
                    <div class="kpi-note">Current market value</div>
                </div>
                <div class="kpi">
                    <div class="kpi-label">Paper P/L</div>
                    <div class="kpi-value mono" id="paper_pl">-</div>
                    <div class="kpi-note">Unrealized plus cash drift</div>
                </div>
            </div>

            <div class="glass-panel">
                <div class="panel-header">
                    <h3>Execution Control</h3>
                    <span class="status-pill" id="paper_processed_badge">Local only</span>
                </div>
                <div style="display:flex; flex-wrap:wrap; gap:0.65rem;">
                    <button class="command-btn" onclick="runPaperAutomation()">Auto Sync</button>
                    <button class="command-btn paper-secondary-btn" onclick="exportPaperTrading()">Export JSON</button>
                    <button class="command-btn paper-danger-btn" onclick="resetPaperTrading()">Reset Paper</button>
                </div>
            </div>

            <div class="portfolio-command-grid paper-grid">
                <div class="glass-panel">
                    <div class="panel-header">
                        <h3>Open Paper Positions</h3>
                        <span class="status-pill" id="paper_position_count">0 positions</span>
                    </div>
                    <div class="table-container">
                        <table class="data-table" id="table_paper_positions">
                            <thead>
                                <tr>
                                    <th onclick="sortTable('table_paper_positions', 0)">Symbol ↕</th>
                                    <th onclick="sortTable('table_paper_positions', 1, 'num')">Shares ↕</th>
                                    <th onclick="sortTable('table_paper_positions', 2, 'num')">Avg ↕</th>
                                    <th onclick="sortTable('table_paper_positions', 3, 'num')">Current ↕</th>
                                    <th onclick="sortTable('table_paper_positions', 4, 'num')">Value ↕</th>
                                    <th onclick="sortTable('table_paper_positions', 5, 'num')">P/L ↕</th>
                                </tr>
                            </thead>
                            <tbody id="paper_positions_body"></tbody>
                        </table>
                    </div>
                </div>

                <div class="glass-panel">
                    <div class="panel-header">
                        <h3>Today&apos;s Paper Actions</h3>
                        <span class="status-pill">{len(allocation_plan.get('suggestions', []))} auto candidates</span>
                    </div>
                    <div class="table-container">
                        <table class="data-table" id="table_paper_actions">
                            <thead>
                                <tr>
                                    <th onclick="sortTable('table_paper_actions', 0)">Symbol ↕</th>
                                    <th onclick="sortTable('table_paper_actions', 1)">Action ↕</th>
                                    <th onclick="sortTable('table_paper_actions', 2, 'num')">Amount ↕</th>
                                    <th onclick="sortTable('table_paper_actions', 3, 'num')">Shares ↕</th>
                                    <th onclick="sortTable('table_paper_actions', 4, 'num')">Entry ↕</th>
                                    <th>Manual</th>
                                </tr>
                            </thead>
                            <tbody id="paper_actions_body"></tbody>
                        </table>
                    </div>
                </div>
            </div>

            <div class="glass-panel">
                <div class="panel-header">
                    <h3>Paper Ledger</h3>
                    <span class="status-pill" id="paper_ledger_count">0 entries</span>
                </div>
                <div class="table-container" style="max-height:420px;">
                    <table class="data-table" id="table_paper_ledger">
                        <thead>
                            <tr>
                                <th onclick="sortTable('table_paper_ledger', 0)">Date ↕</th>
                                <th onclick="sortTable('table_paper_ledger', 1)">Action ↕</th>
                                <th onclick="sortTable('table_paper_ledger', 2)">Symbol ↕</th>
                                <th onclick="sortTable('table_paper_ledger', 3, 'num')">Shares ↕</th>
                                <th onclick="sortTable('table_paper_ledger', 4, 'num')">Price ↕</th>
                                <th onclick="sortTable('table_paper_ledger', 5, 'num')">Amount ↕</th>
                                <th>Note</th>
                            </tr>
                        </thead>
                        <tbody id="paper_ledger_body"></tbody>
                    </table>
                </div>
            </div>
        </div>
        """.strip()

        # --- ACTION PERFORMANCE HTML ---
        outcome_rows = ""
        outcome_action_options = sorted(set([o.get("action", "-") for o in action_outcomes.get("outcomes", []) if o.get("action")]))
        outcome_action_options_html = "".join([f'<option value="{a}">{a}</option>' for a in outcome_action_options])
        default_horizon = "30"
        outcome_summary_30 = action_outcomes.get("summary", {}).get(default_horizon, {})
        outcome_overall_30 = outcome_summary_30.get("overall", {})
        learning_profile = action_outcomes.get("learning_profile", {})
        learning_adjustments = learning_profile.get("adjustments", {})
        learning_hints = learning_profile.get("hints", [])
        pending_30 = outcome_summary_30.get("pending", 0)
        complete_30 = outcome_summary_30.get("complete", 0)
        win_rate_30 = outcome_overall_30.get("win_rate_pct", 0.0)
        avg_return_30 = outcome_overall_30.get("avg_return_pct", 0.0)

        learning_hint_html = "".join([f"<li>{hint}</li>" for hint in learning_hints[:4]]) or "<li>Learning profile will appear after outcome data is generated.</li>"
        learning_status = learning_profile.get("status", "collecting").title()
        learning_sample = learning_profile.get("sample_size", 0)
        learning_horizon = learning_profile.get("preferred_horizon", default_horizon)
        add_threshold_delta = learning_adjustments.get("add_mom_threshold_delta", 0)
        rr_delta = learning_adjustments.get("add_reward_risk_delta", 0.0)
        watch_threshold_delta = learning_adjustments.get("watchlist_mom_threshold_delta", 0)

        action_summary_rows = ""
        for action, stats in sorted(outcome_summary_30.get("by_action", {}).items()):
            action_summary_rows += f"""
                <tr>
                    <td><span class="action-pill {action_class_map.get(action, 'action-neutral')}">{action}</span></td>
                    <td class="mono">{stats.get('count', 0)}</td>
                    <td class="mono">{stats.get('win_rate_pct', 0):.1f}%</td>
                    <td class="mono {'text-green' if stats.get('avg_return_pct', 0) > 0 else 'text-red' if stats.get('avg_return_pct', 0) < 0 else 'text-muted'}">{stats.get('avg_return_pct', 0):+.2f}%</td>
                    <td class="mono">{stats.get('avg_drawdown_pct', 0):+.2f}%</td>
                    <td class="mono">{stats.get('avg_runup_pct', 0):+.2f}%</td>
                    <td class="mono">{stats.get('target_hit_rate_pct', 0):.1f}%</td>
                    <td class="mono">{stats.get('stop_hit_rate_pct', 0):.1f}%</td>
                </tr>
            """

        for outcome in action_outcomes.get("outcomes", []):
            h30 = outcome.get("horizons", {}).get(default_horizon, {})
            status = h30.get("status", "pending")
            ret = h30.get("return_pct")
            dd = h30.get("max_drawdown_pct")
            runup = h30.get("max_runup_pct")
            target_hit = h30.get("target_hit", False)
            stop_hit = h30.get("stop_hit", False)
            ret_display = f"{ret:+.2f}%" if ret is not None else "-"
            dd_display = f"{dd:+.2f}%" if dd is not None else "-"
            runup_display = f"{runup:+.2f}%" if runup is not None else "-"
            ret_cls = "text-green" if (ret or 0) > 0 else "text-red" if ret is not None and ret < 0 else "text-muted"
            row_click = stock_onclick(outcome.get("symbol"))
            outcome_rows += f"""
                <tr {row_click} data-action="{outcome.get('action')}" data-horizons='{json.dumps(outcome.get("horizons", {}))}'>
                    <td class="mono" style="font-weight:800; color:var(--accent);">{outcome.get('symbol')}</td>
                    <td>{outcome.get('date')}</td>
                    <td><span class="action-pill {action_class_map.get(outcome.get('action'), 'action-neutral')}">{outcome.get('action')}</span></td>
                    <td class="mono">{outcome.get('priority', 0):.1f}</td>
                    <td class="mono">{outcome.get('mom_score', 0)}</td>
                    <td>{outcome.get('trend', '-')}</td>
                    <td class="mono">₱{outcome.get('entry_price', 0):.2f}</td>
                    <td class="mono outcome-return {ret_cls}">{ret_display}</td>
                    <td class="mono outcome-drawdown">{dd_display}</td>
                    <td class="mono outcome-runup">{runup_display}</td>
                    <td class="outcome-target">{'Yes' if target_hit else '-'}</td>
                    <td class="outcome-stop">{'Yes' if stop_hit else '-'}</td>
                    <td class="outcome-status">{status}</td>
                </tr>
            """

        action_performance_html = f"""
        <div id="action_performance" class="section">
            <div class="page-head">
                <div>
                    <div class="eyebrow">Action Performance</div>
                    <h1 class="page-title">Recommendation Outcomes</h1>
                    <div class="page-subtitle">Tracks whether past action calls produced positive forward returns, hit targets, or violated stops across 5/10/20/30 trading-day windows.</div>
                </div>
                <div style="text-align:right; color:var(--text-tertiary); font-size:0.82rem;">
                    <div style="color:var(--text-secondary); font-weight:700;">Generated {action_outcomes.get('generated_at', '-')}</div>
                    <div>Rows mature as more market days pass</div>
                </div>
            </div>

            <div class="kpi-strip">
                <div class="kpi">
                    <div class="kpi-label">30D Complete</div>
                    <div class="kpi-value" id="outcome_complete_count">{complete_30}</div>
                    <div class="kpi-note">Measured recommendations</div>
                </div>
                <div class="kpi">
                    <div class="kpi-label">30D Pending</div>
                    <div class="kpi-value" id="outcome_pending_count">{pending_30}</div>
                    <div class="kpi-note">Waiting for enough days</div>
                </div>
                <div class="kpi">
                    <div class="kpi-label">Visible Rows</div>
                    <div class="kpi-value" id="outcome_visible_count">{len(action_outcomes.get('outcomes', []))}</div>
                    <div class="kpi-note">After filters</div>
                </div>
                <div class="kpi">
                    <div class="kpi-label">30D Win Rate</div>
                    <div class="kpi-value">{win_rate_30:.1f}%</div>
                    <div class="kpi-note">Avg return {avg_return_30:+.2f}%</div>
                </div>
            </div>

            <div class="dashboard-grid learning-grid">
                <div class="glass-panel">
                    <div class="panel-header">
                        <h3>Learning Loop</h3>
                        <span class="status-pill">{learning_status}</span>
                    </div>
                    <div class="metrics-grid">
                        <div class="metric-card"><span>Sample</span><strong>{learning_sample}</strong><small>{learning_horizon}D completed outcomes</small></div>
                        <div class="metric-card"><span>Add MoM</span><strong>{add_threshold_delta:+}</strong><small>Threshold adjustment</small></div>
                        <div class="metric-card"><span>Add R/R</span><strong>{rr_delta:+.1f}</strong><small>Reward/risk adjustment</small></div>
                        <div class="metric-card"><span>Watchlist MoM</span><strong>{watch_threshold_delta:+}</strong><small>Threshold adjustment</small></div>
                    </div>
                    <ul style="margin:16px 0 0 18px; color:var(--text-secondary); line-height:1.7;">
                        {learning_hint_html}
                    </ul>
                </div>

                <div class="glass-panel">
                    <div class="panel-header">
                        <h3>30D Action Quality</h3>
                        <span class="status-pill">{complete_30} measured</span>
                    </div>
                    <div class="table-container" style="max-height:260px;">
                        <table class="data-table">
                            <thead>
                                <tr>
                                    <th>Action</th>
                                    <th>Count</th>
                                    <th>Win</th>
                                    <th>Avg Return</th>
                                    <th>Drawdown</th>
                                    <th>Runup</th>
                                    <th>Target</th>
                                    <th>Stop</th>
                                </tr>
                            </thead>
                            <tbody>
                                {action_summary_rows or '<tr><td colspan="8" style="text-align:center; color:var(--text-tertiary);">No completed 30D outcomes yet.</td></tr>'}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>

            <div class="control-panel" style="grid-template-columns: repeat(3, minmax(160px, 1fr));">
                <select class="control-field" id="outcome_action_filter" onchange="filterOutcomes()">
                    <option value="all">All Actions</option>
                    {outcome_action_options_html}
                </select>
                <select class="control-field" id="outcome_horizon_filter" onchange="filterOutcomes()">
                    <option value="5">5 Trading Days</option>
                    <option value="10">10 Trading Days</option>
                    <option value="20">20 Trading Days</option>
                    <option value="30" selected>30 Trading Days</option>
                </select>
                <select class="control-field" id="outcome_status_filter" onchange="filterOutcomes()">
                    <option value="all">All Status</option>
                    <option value="complete">Complete</option>
                    <option value="pending">Pending</option>
                </select>
            </div>

            <div class="table-container">
                <table class="data-table" id="table_action_performance">
                    <thead>
                        <tr>
                            <th onclick="sortTable('table_action_performance', 0)">Symbol ↕</th>
                            <th onclick="sortTable('table_action_performance', 1)">Date ↕</th>
                            <th onclick="sortTable('table_action_performance', 2)">Action ↕</th>
                            <th onclick="sortTable('table_action_performance', 3, 'num')">Priority ↕</th>
                            <th onclick="sortTable('table_action_performance', 4, 'num')">MoM ↕</th>
                            <th onclick="sortTable('table_action_performance', 5)">Trend ↕</th>
                            <th onclick="sortTable('table_action_performance', 6, 'num')">Entry ↕</th>
                            <th onclick="sortTable('table_action_performance', 7, 'num')">Return ↕</th>
                            <th onclick="sortTable('table_action_performance', 8, 'num')">Drawdown ↕</th>
                            <th onclick="sortTable('table_action_performance', 9, 'num')">Runup ↕</th>
                            <th>Target</th>
                            <th>Stop</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {outcome_rows}
                    </tbody>
                </table>
                { '<div style="padding:20px; text-align:center; color:var(--text-tertiary);">No mature outcomes yet. The tracker will populate after future daily action runs have enough forward price data.</div>' if not outcome_rows else '' }
            </div>
        </div>
        """

        # --- PORTFOLIO HTML ---
        portfolio_html = ""
        portfolio_rows = ""
        portfolio_actions = []
        sector_exposure = {}
        
        # Summary Cards
        total_eq = portfolio_summary['total_equity']
        total_cost = portfolio_summary['total_cost']
        total_gl = portfolio_summary['total_gain_loss']
        total_gl_pct = portfolio_summary['total_gain_loss_pct']
        
        gl_cls = "text-green" if total_gl >= 0 else "text-red"
        
        # Table Rows
        for p in portfolio_summary['positions']:
            sym = p['symbol']
            shares = p['shares']
            avg = p['avg_price']
            curr = p['current_price']
            gl = p['gain_loss']
            gl_pct = p['gain_loss_pct']
            
            p_gl_cls = "text-green" if gl >= 0 else "text-red"
            
            # Context for onclick
            official = stock_meta.get(sym, {})
            tech = tech_data.get(sym, {})
            fund = official_fund.get(sym, {})
            mom_score, _ = self.analyzer.calculate_monthly_gain_score(tech, fund)
            allocation_pct = (p['market_value'] / total_eq * 100.0) if total_eq > 0 else 0.0
            risk_pct = tech.get('risk_pct', 0)
            stop_loss = tech.get('stop_loss', 0)
            trend = tech.get('trend', 'Unknown')

            engine_action = action_lookup.get(sym)
            sector = normalize_sector(
                official.get('sector')
                or (engine_action or {}).get('sector')
                or sector_fallback.get(sym)
                or 'Unknown'
            )
            sector_exposure[sector] = sector_exposure.get(sector, 0.0) + p['market_value']
            if engine_action:
                action_label = engine_action.get("action", "Hold")
                action_cls = action_class_map.get(action_label, "action-neutral")
            elif mom_score >= 45 and gl_pct >= -3:
                action_label = "Watchlist"
                action_cls = "action-watch"
            elif gl_pct <= -8 or mom_score < 20:
                action_label = "Review Risk"
                action_cls = "action-risk"
            elif allocation_pct > 18:
                action_label = "Trim Watch"
                action_cls = "action-watch"
            else:
                action_label = "Hold"
                action_cls = "action-neutral"

            if action_label != "Hold":
                portfolio_actions.append({
                    "symbol": sym,
                    "action": action_label,
                    "class": action_cls,
                    "detail": f"{gl_pct:+.1f}% G/L | MoM {mom_score} | {trend}",
                    "priority": engine_action.get("priority", 0) if engine_action else 0,
                })

            # We need to construct a basic 'item' if it's not in our main list, but usually it is.
            # Use data from tech_data/stock_meta
            
            # Basic item reconstruction for onclick
            p_item = {
                'symbol': sym,
                'company_name': official.get('name', sym),
                'tech': tech if tech else {'last_close': curr},
                'fund': fund
            }
            official_for_modal = {**official, 'sector': sector}
            onclick = self._generate_onclick(p_item, official_for_modal)
            
            portfolio_rows += f"""
                <tr {onclick}>
                    <td class="mono" style="font-weight:700; color:var(--accent);">{sym}</td>
                    <td>{sector}</td>
                    <td class="mono">{shares:,.0f}</td>
                    <td class="mono">₱{avg:,.2f}</td>
                    <td class="mono">₱{curr:,.2f}</td>
                    <td class="mono">₱{p['market_value']:,.2f}</td>
                    <td class="mono">{allocation_pct:.1f}%</td>
                    <td class="mono {p_gl_cls}">₱{gl:,.2f}</td>
                    <td class="mono {p_gl_cls}">{gl_pct:+.2f}%</td>
                    <td class="mono">{mom_score}</td>
                    <td class="mono">{risk_pct:.1f}%</td>
                    <td><span class="action-pill {action_cls}">{action_label}</span></td>
                    <td>
                        <button onclick="event.stopPropagation(); removePosition('{sym}')" style="background:none; border:none; color:var(--text-tertiary); cursor:pointer;" title="Remove Position">
                            🗑️
                        </button>
                    </td>
                </tr>
            """

        portfolio_actions = sorted(
            portfolio_actions,
            key=lambda x: (x.get("priority", 0), 0 if x["action"] == "Review Risk" else 1),
            reverse=True,
        )[:4]
        action_cards_html = "".join([
            f"""
            <div class="action-card" {stock_onclick(a['symbol'])}>
                <div>
                    <div class="mono" style="font-weight:800; color:var(--text-primary);">{a['symbol']}</div>
                    <div style="color:var(--text-tertiary); font-size:0.78rem; margin-top:4px;">{a['detail']}</div>
                </div>
                <span class="action-pill {a['class']}">{a['action']}</span>
            </div>
            """
            for a in portfolio_actions
        ]) or '<div style="color:var(--text-tertiary); font-size:0.9rem;">No urgent portfolio actions from current rules.</div>'
            
        portfolio_html = f"""
        <div id="portfolio_section" class="section active">
            <div class="page-head">
                <div>
                    <div class="eyebrow">Portfolio Command</div>
                    <h1 class="page-title">Daily Decision Board</h1>
                    <div class="page-subtitle">Start here: inspect exposure, sort holdings by risk or performance, and act on the highest-signal positions first.</div>
                </div>
                <button class="command-btn" onclick="openAddModal()">
                    + Add Position
                </button>
            </div>
            
            <div class="portfolio-command-grid">
                <!-- Left: Metrics -->
                <div class="portfolio-health">
                    <div class="health-card">
                        <div class="kpi-label">Total Equity</div>
                        <div class="kpi-value">₱{total_eq:,.2f}</div>
                    </div>
                    <div class="health-card">
                        <div class="kpi-label">Cost Basis</div>
                        <div class="kpi-value">₱{total_cost:,.2f}</div>
                    </div>
                    <div class="health-card">
                        <div class="kpi-label">Unrealized P/L</div>
                        <div class="kpi-value {gl_cls}">₱{total_gl:,.2f}</div>
                        <div class="kpi-note">{total_gl_pct:+.2f}% total return</div>
                    </div>
                    <div class="action-panel">
                        <div class="kpi-label" style="margin-bottom:0.75rem;">Action Queue</div>
                        {action_cards_html}
                    </div>
                </div>
                
                <!-- Right: Charts -->
                <div class="chart-panel">
                    <div style="height:250px; position:relative;">
                        <canvas id="chartAllocation"></canvas>
                    </div>
                    <div style="height:250px; position:relative;">
                        <canvas id="chartSector"></canvas>
                    </div>
                </div>
            </div>

            <script>
                document.addEventListener('DOMContentLoaded', function() {{
                    // Portfolio Data from Python
                    const positions = {json.dumps(portfolio_summary['positions'])};
                    const sectorMap = {json.dumps(sector_exposure)};
                    
                    // 1. Asset Allocation Data
                    const labels = positions.map(p => p.symbol);
                    const values = positions.map(p => p.market_value);
                    const colors = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#ec4899', '#6366f1', '#14b8a6'];
                    
                    new Chart(document.getElementById('chartAllocation'), {{
                        type: 'doughnut',
                        data: {{
                            labels: labels,
                            datasets: [{{
                                data: values,
                                backgroundColor: colors,
                                borderColor: '#1e293b',
                                borderWidth: 2
                            }}]
                        }},
                        options: {{
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {{
                                legend: {{ position: 'right', labels: {{ color: '#94a3b8', font: {{ size: 10 }} }} }},
                                title: {{ display: true, text: 'Holdings Allocation', color: '#f1f5f9' }}
                            }}
                        }}
                    }});
                    
                    new Chart(document.getElementById('chartSector'), {{
                        type: 'pie',
                        data: {{
                            labels: Object.keys(sectorMap),
                            datasets: [{{
                                data: Object.values(sectorMap),
                                backgroundColor: ['#8b5cf6', '#ec4899', '#f59e0b', '#3b82f6', '#10b981', '#14b8a6', '#ef4444', '#64748b'],
                                borderColor: '#1e293b',
                                borderWidth: 2
                            }}]
                        }},
                        options: {{
                            responsive: true,
                            maintainAspectRatio: false,
                             plugins: {{
                                legend: {{ position: 'right', labels: {{ color: '#94a3b8', font: {{ size: 10 }} }} }},
                                title: {{ display: true, text: 'Sector Exposure', color: '#f1f5f9' }}
                            }}
                        }}
                    }});
                }});
            </script>
            
            <div class="table-container">
                <table class="data-table" id="table_portfolio">
                    <thead>
                        <tr>
                            <th onclick="sortTable('table_portfolio', 0)" title="Sort by stock symbol">Symbol ↕</th>
                            <th onclick="sortTable('table_portfolio', 1)" title="Sort by sector">Sector ↕</th>
                            <th onclick="sortTable('table_portfolio', 2, 'num')" title="Sort by number of shares">Shares ↕</th>
                            <th onclick="sortTable('table_portfolio', 3, 'num')" title="Sort by average buy price">Avg Price ↕</th>
                            <th onclick="sortTable('table_portfolio', 4, 'num')" title="Sort by current price">Current ↕</th>
                            <th onclick="sortTable('table_portfolio', 5, 'num')" title="Sort by market value">Market Value ↕</th>
                            <th onclick="sortTable('table_portfolio', 6, 'num')" title="Sort by allocation percentage">Alloc ↕</th>
                            <th onclick="sortTable('table_portfolio', 7, 'num')" title="Sort by peso gain or loss">Gain/Loss ↕</th>
                            <th onclick="sortTable('table_portfolio', 8, 'num')" title="Sort by percentage gain or loss">% ↕</th>
                            <th onclick="sortTable('table_portfolio', 9, 'num')" title="Sort by month-on-month score">MoM ↕</th>
                            <th onclick="sortTable('table_portfolio', 10, 'num')" title="Sort by stop-risk distance">Risk ↕</th>
                            <th onclick="sortTable('table_portfolio', 11)" title="Sort by suggested action">Plan ↕</th>
                            <th title="Remove position">Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {portfolio_rows}
                    </tbody>
                </table>
                { '<div style="padding:20px; text-align:center; color:var(--text-tertiary);">No positions yet. Use <code>python portfolio.py add</code> to track stocks.</div>' if not portfolio_rows else '' }
            </div>
        </div>
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
                    --bg-app: #0b0f14;
                    --bg-rail: #111820;
                    --bg-panel: #151d26;
                    --bg-panel-soft: #192431;
                    --bg-panel-hover: #223041;
                    --border: #273544;
                    --border-strong: #3a4b5d;
                    --text-primary: #eef4f8;
                    --text-secondary: #9fb0bd;
                    --text-tertiary: #6f8392;
                    --accent: #24b8db;
                    --accent-2: #f2b84b;
                    --accent-glow: rgba(36, 184, 219, 0.24);
                    --green: #35d07f;
                    --red: #ff5f57;
                    --gold: #f2b84b;
                    --shadow: 0 18px 45px rgba(0, 0, 0, 0.32);
                }}

                * {{ box-sizing: border-box; }}
                * {{ scrollbar-width: thin; scrollbar-color: var(--border-strong) transparent; }}
                ::-webkit-scrollbar {{ width: 10px; height: 10px; }}
                ::-webkit-scrollbar-thumb {{ background: var(--border-strong); border-radius: 999px; border: 3px solid transparent; background-clip: padding-box; }}
                ::-webkit-scrollbar-track {{ background: transparent; }}
                body {{
                    margin: 0;
                    font-family: 'Inter', sans-serif;
                    background:
                        radial-gradient(circle at 20% 0%, rgba(36, 184, 219, 0.09), transparent 34%),
                        linear-gradient(135deg, #0b0f14 0%, #101720 52%, #0b0f14 100%);
                    color: var(--text-primary);
                    display: flex;
                    height: 100vh;
                    overflow: hidden;
                    overflow-x: hidden;
                }}

                nav {{
                    width: 268px;
                    background: linear-gradient(180deg, rgba(17, 24, 32, 0.98), rgba(13, 18, 24, 0.98));
                    border-right: 1px solid var(--border);
                    display: flex;
                    flex-direction: column;
                    padding: 1.25rem 0.85rem;
                    box-shadow: 12px 0 35px rgba(0, 0, 0, 0.2);
                    z-index: 4;
                }}

                .brand {{
                    padding: 0.6rem 0.75rem 1.25rem;
                    margin-bottom: 0.75rem;
                    font-size: 1.2rem;
                    font-weight: 800;
                    letter-spacing: 0;
                    color: var(--text-primary);
                    display: flex;
                    align-items: center;
                    gap: 0.55rem;
                    border-bottom: 1px solid rgba(255,255,255,0.06);
                }}

                .brand::before {{
                    content: "";
                    width: 12px;
                    height: 28px;
                    border-radius: 3px;
                    background: linear-gradient(180deg, var(--accent), var(--accent-2));
                    box-shadow: 0 0 24px var(--accent-glow);
                    flex: 0 0 auto;
                }}

                .brand span {{ color: var(--accent-2); }}

                .nav-item {{
                    padding: 0.78rem 0.9rem;
                    margin: 0.14rem 0;
                    color: var(--text-secondary);
                    cursor: pointer;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    gap: 0.75rem;
                    font-size: 0.9rem;
                    transition: background 0.2s, color 0.2s, border-color 0.2s;
                    border: 1px solid transparent;
                    border-radius: 8px;
                }}

                .nav-item:hover, .nav-item.active {{
                    background: rgba(255, 255, 255, 0.045);
                    color: var(--text-primary);
                    border-color: rgba(36, 184, 219, 0.22);
                }}

                .nav-item.active {{
                    box-shadow: inset 3px 0 0 var(--accent);
                }}

                .nav-badge {{
                    background: rgba(255, 255, 255, 0.08);
                    border: 1px solid rgba(255, 255, 255, 0.07);
                    color: var(--text-secondary);
                    padding: 0.15rem 0.5rem;
                    border-radius: 99px;
                    font-size: 0.75rem;
                    line-height: 1.2;
                }}

                .content {{
                    flex: 1;
                    display: flex;
                    flex-direction: column;
                    overflow: hidden;
                    min-width: 0;
                    width: 100%;
                }}

                header {{
                    min-height: 70px;
                    border-bottom: 1px solid var(--border);
                    display: flex;
                    align-items: center;
                    padding: 0 1.75rem;
                    justify-content: space-between;
                    background: rgba(11, 15, 20, 0.72);
                    backdrop-filter: blur(16px);
                }}

                .header-title {{ font-weight: 700; color: var(--text-primary); }}

                .search-bar {{
                    background: var(--bg-panel-soft);
                    border: 1px solid var(--border);
                    border-radius: 8px;
                    padding: 0.7rem 0.8rem;
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
                    padding: 1.75rem;
                }}

                .page-head {{
                    display: grid;
                    grid-template-columns: minmax(0, 1fr) auto;
                    gap: 1.25rem;
                    align-items: end;
                    margin-bottom: 1.5rem;
                }}

                .eyebrow {{
                    color: var(--accent-2);
                    font-size: 0.72rem;
                    font-weight: 800;
                    text-transform: uppercase;
                    letter-spacing: 0.08em;
                    margin-bottom: 0.45rem;
                }}

                .page-title {{
                    margin: 0;
                    font-size: 2rem;
                    line-height: 1.1;
                    letter-spacing: 0;
                }}

                .page-subtitle {{
                    margin-top: 0.5rem;
                    color: var(--text-secondary);
                    max-width: 760px;
                    line-height: 1.45;
                    font-size: 0.95rem;
                    overflow-wrap: anywhere;
                }}

                .kpi-strip {{
                    display: grid;
                    grid-template-columns: repeat(4, minmax(150px, 1fr));
                    gap: 0.75rem;
                    margin-bottom: 1.25rem;
                }}

                .kpi {{
                    background: linear-gradient(180deg, rgba(255,255,255,0.045), rgba(255,255,255,0.018));
                    border: 1px solid var(--border);
                    border-radius: 8px;
                    padding: 0.9rem;
                    min-height: 88px;
                }}

                .kpi-label {{
                    color: var(--text-tertiary);
                    font-size: 0.72rem;
                    text-transform: uppercase;
                    font-weight: 800;
                    letter-spacing: 0.06em;
                }}

                .kpi-value {{
                    margin-top: 0.35rem;
                    font-size: 1.35rem;
                    font-weight: 800;
                    color: var(--text-primary);
                }}

                .kpi-note {{
                    margin-top: 0.3rem;
                    color: var(--text-secondary);
                    font-size: 0.78rem;
                }}

                .control-panel {{
                    margin-bottom: 1.35rem;
                    display: grid;
                    grid-template-columns: minmax(240px, 1fr) repeat(4, minmax(140px, 180px));
                    gap: 0.7rem;
                    align-items: center;
                    background: rgba(21, 29, 38, 0.76);
                    padding: 0.85rem;
                    border-radius: 8px;
                    border: 1px solid var(--border);
                    box-shadow: var(--shadow);
                }}

                .control-field {{
                    width: 100%;
                    min-height: 42px;
                    padding: 0.65rem 0.75rem;
                    background: #101820;
                    border: 1px solid var(--border);
                    color: var(--text-primary);
                    border-radius: 6px;
                    outline: none;
                    font-family: inherit;
                }}

                .control-field:focus {{
                    border-color: var(--accent);
                    box-shadow: 0 0 0 3px rgba(36,184,219,0.12);
                }}

                .command-btn {{
                    background: linear-gradient(135deg, var(--accent), #1f9fc0);
                    border: 1px solid rgba(255,255,255,0.14);
                    color: #061016;
                    padding: 0.72rem 1rem;
                    border-radius: 8px;
                    cursor: pointer;
                    font-size: 0.9rem;
                    font-weight: 800;
                    box-shadow: 0 14px 28px rgba(36,184,219,0.18);
                    white-space: nowrap;
                }}

                .paper-secondary-btn {{
                    background: rgba(255,255,255,0.06);
                    color: var(--text-primary);
                    box-shadow: none;
                }}

                .paper-danger-btn {{
                    background: rgba(239,68,68,0.18);
                    color: #fecaca;
                    box-shadow: none;
                }}

                .portfolio-command-grid {{
                    display: grid;
                    grid-template-columns: minmax(300px, 390px) minmax(0, 1fr);
                    gap: 1rem;
                    margin-bottom: 1.25rem;
                    align-items: start;
                }}

                .paper-grid {{
                    grid-template-columns: minmax(420px, 0.9fr) minmax(0, 1.1fr);
                }}

                .portfolio-health {{
                    display: grid;
                    grid-template-columns: 1fr;
                    gap: 0.75rem;
                }}

                .health-card, .action-panel, .chart-panel {{
                    background: linear-gradient(180deg, rgba(25, 36, 49, 0.96), rgba(18, 26, 35, 0.96));
                    border: 1px solid var(--border);
                    border-radius: 8px;
                    padding: 1rem;
                    box-shadow: var(--shadow);
                }}

                .glass-panel {{
                    background: linear-gradient(180deg, rgba(25, 36, 49, 0.9), rgba(18, 26, 35, 0.92));
                    border: 1px solid var(--border);
                    border-radius: 8px;
                    padding: 1rem;
                    box-shadow: var(--shadow);
                    margin-bottom: 1.25rem;
                    min-width: 0;
                }}

                .panel-header {{
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    gap: 0.75rem;
                    margin-bottom: 0.9rem;
                }}

                .panel-header h3 {{
                    margin: 0;
                    font-size: 1rem;
                    line-height: 1.2;
                }}

                .status-pill {{
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    padding: 0.24rem 0.58rem;
                    border-radius: 999px;
                    border: 1px solid rgba(36,184,219,0.22);
                    color: var(--accent-2);
                    background: rgba(36,184,219,0.1);
                    font-size: 0.72rem;
                    font-weight: 800;
                    white-space: nowrap;
                }}

                .metrics-grid {{
                    display: grid;
                    grid-template-columns: repeat(4, minmax(0, 1fr));
                    gap: 0.65rem;
                }}

                .metric-card {{
                    border: 1px solid rgba(255,255,255,0.08);
                    border-radius: 8px;
                    padding: 0.75rem;
                    background: rgba(10, 16, 22, 0.34);
                    min-width: 0;
                }}

                .metric-card span, .metric-card small {{
                    display: block;
                    color: var(--text-tertiary);
                    font-size: 0.72rem;
                    overflow-wrap: anywhere;
                }}

                .metric-card strong {{
                    display: block;
                    color: var(--text-primary);
                    font-size: 1.15rem;
                    margin: 0.24rem 0;
                }}

                .chart-panel {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 1rem;
                    align-items: center;
                    align-self: start;
                }}

                .action-card {{
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    gap: 0.75rem;
                    padding: 0.72rem 0;
                    border-top: 1px solid rgba(255,255,255,0.06);
                }}

                .action-card:first-of-type {{ border-top: none; padding-top: 0; }}

                .action-pill {{
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    min-width: 84px;
                    padding: 0.22rem 0.52rem;
                    border-radius: 999px;
                    font-size: 0.72rem;
                    font-weight: 800;
                    white-space: nowrap;
                    border: 1px solid transparent;
                }}

                .action-good {{ background: rgba(53,208,127,0.13); color: var(--green); border-color: rgba(53,208,127,0.2); }}
                .action-risk {{ background: rgba(255,95,87,0.13); color: var(--red); border-color: rgba(255,95,87,0.22); }}
                .action-watch {{ background: rgba(242,184,75,0.13); color: var(--gold); border-color: rgba(242,184,75,0.22); }}
                .action-neutral {{ background: rgba(255,255,255,0.07); color: var(--text-secondary); border-color: rgba(255,255,255,0.08); }}

                .search-input-wrapper {{ position: relative; }}
                .search-input-wrapper svg {{
                    position: absolute;
                    left: 0.85rem;
                    top: 50%;
                    transform: translateY(-50%);
                    color: var(--text-tertiary);
                }}
                .search-input-wrapper input {{ padding-left: 2.35rem; }}

                .dashboard-grid {{
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(310px, 1fr));
                    gap: 1rem;
                }}

                .learning-grid {{
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                }}

                .card {{
                    background: linear-gradient(180deg, rgba(25, 36, 49, 0.96), rgba(18, 26, 35, 0.96));
                    border: 1px solid var(--border);
                    border-radius: 8px;
                    padding: 1rem;
                    transition: transform 0.2s, border-color 0.2s, box-shadow 0.2s;
                    position: relative;
                    overflow: hidden;
                    box-shadow: 0 8px 24px rgba(0,0,0,0.18);
                }}

                .card:hover {{
                    transform: translateY(-3px);
                    border-color: var(--accent);
                    box-shadow: 0 18px 34px rgba(0,0,0,0.28);
                }}

                .card-header {{
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-start;
                    gap: 1rem;
                    margin-bottom: 0.85rem;
                }}

                .symbol {{ font-size: 1.1rem; font-weight: 700; font-family: 'JetBrains Mono', monospace; }}
                .price {{ font-size: 1.22rem; font-weight: 800; color: var(--text-primary); }}

                .trend-badge {{
                    font-size: 0.7rem;
                    padding: 0.22rem 0.52rem;
                    border-radius: 999px;
                    text-transform: uppercase;
                    font-weight: 700;
                    display: inline-block;
                    margin-bottom: 0.25rem;
                }}

                .green {{ background: rgba(53, 208, 127, 0.12); color: var(--green); }}
                .red {{ background: rgba(255, 95, 87, 0.12); color: var(--red); }}
                .gray {{ background: rgba(255,255,255,0.07); color: var(--text-tertiary); }}
                .gold {{ background: rgba(242, 184, 75, 0.16); color: var(--gold); }}

                .rank-badge {{
                    font-size: 0.7rem;
                    padding: 0.18rem 0.5rem;
                    border-radius: 999px;
                    margin-left: 8px;
                    font-weight: 800;
                    display: inline-block;
                    vertical-align: middle;
                    box-shadow: 0 8px 18px rgba(0,0,0,0.25);
                    color: #111820;
                    text-shadow: none;
                }}
                .rank-1 {{ background: linear-gradient(135deg, #FFD700 0%, #FDB931 100%); border: 1px solid #E6C200; }}
                .rank-2 {{ background: linear-gradient(135deg, #E0E0E0 0%, #B0B0B0 100%); border: 1px solid #A0A0A0; }}
                .rank-3 {{ background: linear-gradient(135deg, #CD7F32 0%, #A0522D 100%); border: 1px solid #8B4513; color: #fff; }}
                .rank-other {{ background: var(--bg-panel-hover); color: var(--text-secondary); border: 1px solid var(--border); }}
                
                .metrics {{
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: 0.7rem;
                    margin-top: 0.9rem;
                    padding-top: 0.85rem;
                    border-top: 1px solid var(--border);
                }}

                .metric {{ display: flex; flex-direction: column; }}
                .metric-label {{ font-size: 0.7rem; color: var(--text-tertiary); margin-bottom: 2px; }}
                .metric-val {{ font-size: 0.9rem; font-weight: 600; }}

                .table-container {{
                    background: rgba(21,29,38,0.88);
                    border-radius: 8px;
                    border: 1px solid var(--border);
                    overflow-x: auto;
                    max-height: 80vh; /* Allow scrolling within the table */
                    overflow-y: auto;
                    box-shadow: var(--shadow);
                }}

                .data-table {{ width: 100%; border-collapse: collapse; text-align: left; }}
                .data-table th {{
                    padding: 0.85rem 0.95rem;
                    background: #111820;
                    color: var(--text-secondary);
                    font-size: 0.75rem;
                    text-transform: uppercase;
                    cursor: pointer;
                    position: sticky; /* Sticky Header */
                    top: 0;
                    z-index: 10;
                    border-bottom: 1px solid var(--border-strong);
                    box-shadow: 0 8px 18px rgba(0, 0, 0, 0.18);
                }}
                .data-table td {{ padding: 0.9rem 0.95rem; border-bottom: 1px solid rgba(255,255,255,0.055); color: var(--text-primary); }}

                .data-table tr:nth-child(even) {{ background: rgba(255, 255, 255, 0.018); }}
                .data-table tr:hover {{ background: var(--bg-panel-hover); }}

                .mono {{ font-family: 'JetBrains Mono', monospace; }}
                .text-green {{ color: var(--green); }}
                .text-red {{ color: var(--red); }}
                .text-gold {{ color: var(--gold); }}
                .text-muted {{ color: var(--text-tertiary); }}
                
                .section {{ display: none; opacity: 0; transition: opacity 0.3s; }}
                .section.active {{ display: block; opacity: 1; }}
                
                .sparkline {{ margin-left: 10px; vertical-align: middle; }}

                @media (max-width: 1100px) {{
                    body {{ flex-direction: column; height: auto; min-height: 100vh; overflow: auto; }}
                    nav {{
                        width: 100%;
                        height: 230px;
                        max-height: 230px;
                        overflow-y: auto;
                        border-right: none;
                        border-bottom: 1px solid var(--border);
                        position: relative;
                        padding: 0.85rem;
                    }}
                    .brand {{ padding-bottom: 0.85rem; margin-bottom: 0.5rem; }}
                    .nav-item {{ padding: 0.65rem 0.8rem; }}
                    .content {{ overflow: visible; }}
                    header {{ padding: 1rem; align-items: flex-start; gap: 0.75rem; flex-direction: column; }}
                    header > div {{ min-width: 0; max-width: 100%; }}
                    header div {{ overflow-wrap: anywhere; }}
                    main {{ padding: 1rem; overflow: visible; }}
                    main, .section {{ width: 100%; max-width: 100%; overflow-x: hidden; }}
                    .page-head {{ grid-template-columns: 1fr; }}
                    .page-head > div:last-child {{ text-align: left !important; }}
                    .page-head > div:last-child div {{ display: inline-block; margin-right: 0.7rem; }}
                    .kpi-strip {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
                    .metrics-grid {{ grid-template-columns: repeat(2, minmax(0, 1fr)); }}
                    .control-panel {{ grid-template-columns: 1fr; }}
                    .portfolio-command-grid {{ grid-template-columns: 1fr; }}
                    .chart-panel {{ grid-template-columns: 1fr; }}
                    .dashboard-grid {{ grid-template-columns: 1fr; }}
                }}

                @media (max-width: 560px) {{
                    .page-title {{ font-size: 1.55rem; }}
                    .kpi-strip {{ grid-template-columns: 1fr; }}
                    .metrics-grid {{ grid-template-columns: 1fr; }}
                    .card-header {{ flex-direction: column; }}
                }}
                
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
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        </head>
        <body>
            <nav>
                <div class="brand">PSE<span>PRO</span></div>
                <div class="nav-item" data-section="overview" onclick="showSection('overview')">
                    Market Overview <span class="nav-badge">All</span>
                </div>
                
                <div class="nav-item active" data-section="portfolio_section" onclick="showSection('portfolio_section')">
                    My Portfolio
                </div>

                <div class="nav-item" data-section="daily_actions" onclick="showSection('daily_actions')">
                    Daily Actions <span class="nav-badge">{action_summary.get('total_actions', len(daily_actions.get('actions', [])))}</span>
                </div>

                <div class="nav-item" data-section="paper_trading" onclick="showSection('paper_trading')">
                    Paper Trading <span class="nav-badge">Auto</span>
                </div>

                <div class="nav-item" data-section="action_performance" onclick="showSection('action_performance')">
                    Performance <span class="nav-badge">{len(action_outcomes.get('outcomes', []))}</span>
                </div>

                <div class="nav-item" data-section="top_picks" onclick="showSection('top_picks')">
                    Top Picks <span class="nav-badge" style="background:var(--accent); color:#fff;">{len(top_picks)}</span>
                </div>

                <div class="nav-item" data-section="dividends" onclick="showSection('dividends')">
                    Dividend Gems <span class="nav-badge" style="background:#10b981; color:#fff;">{len(div_picks)}</span>
                </div>

                <div class="nav-item" data-section="data_health" onclick="showSection('data_health')">
                    Data Health <span class="nav-badge">{system_status}</span>
                </div>
                
                <div style="margin: 1.5rem 0.9rem 0.5rem; font-size:0.7rem; color:var(--text-tertiary); text-transform:uppercase; font-weight:800; letter-spacing:0.08em;">Industries</div>
                
                {industry_nav}
                
            </nav>
            
            <div class="content">
                <header>
                    <div style="display:flex; align-items:center;">
                         <div>
                            <div class="header-title">Philippine Market Command Center</div>
                            <div style="font-size:0.78rem; color:var(--text-tertiary); margin-top:4px;">MoM scoring, fundamentals, dividends, and portfolio risk in one view</div>
                         </div>
                    </div>
                    <div style="font-size:0.8rem; color:var(--text-tertiary);">Last Updated: {timestamp}</div>
                </header>
                
                <main>
                    {portfolio_html}
                    {daily_actions_html}
                    {paper_trading_html}
                    {action_performance_html}
                    {data_health_html}

                    <!-- OVERVIEW (All Stocks Grid) -->
                    <div id="overview" class="section">
                        <div class="page-head">
                            <div>
                                <div class="eyebrow">Market Overview</div>
                                <h1 class="page-title">PSE Opportunity Board</h1>
                                <div class="page-subtitle">Scan active listings by trend, value, yield, and the new month-on-month quality score. Cards stay compact so you can compare faster.</div>
                            </div>
                            <div style="text-align:right; color:var(--text-tertiary); font-size:0.82rem;">
                                <div style="color:var(--text-secondary); font-weight:700;">{len(active_items)} active symbols</div>
                                <div>{len(STOCK_CATEGORIES)} sectors tracked</div>
                            </div>
                        </div>

                        <div class="kpi-strip">
                            <div class="kpi">
                                <div class="kpi-label">Market Breadth</div>
                                <div class="kpi-value">{market_breadth:.0f}%</div>
                                <div class="kpi-note">{uptrend_count} active names in uptrend</div>
                            </div>
                            <div class="kpi">
                                <div class="kpi-label">MoM Watchlist</div>
                                <div class="kpi-value">{strong_mom_count}</div>
                                <div class="kpi-note">Score 45+ candidates</div>
                            </div>
                            <div class="kpi">
                                <div class="kpi-label">Dividend Coverage</div>
                                <div class="kpi-value">{dividend_count}</div>
                                <div class="kpi-note">Active names with yield data</div>
                            </div>
                            <div class="kpi">
                                <div class="kpi-label">Avg MoM Score</div>
                                <div class="kpi-value">{avg_mom_score:.1f}</div>
                                <div class="kpi-note">Across active symbols</div>
                            </div>
                        </div>

                        <div class="control-panel">
                            <div class="search-input-wrapper">
                                <svg width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
                                <input class="control-field" type="text" id="search_input" onkeyup="filterStocks()" placeholder="Search symbol or company...">
                            </div>
                            <select class="control-field" id="filter_sector" onchange="filterStocks()">
                                <option value="All">All Sectors</option>
                                {sector_options}
                            </select>
                            <select class="control-field" id="filter_trend" onchange="filterStocks()">
                                <option value="all">Trend: All</option>
                                <option value="uptrend">Uptrend</option>
                                <option value="strong">Strong Uptrend</option>
                                <option value="golden">Golden Cross</option>
                            </select>
                            <select class="control-field" id="filter_val" onchange="filterStocks()">
                                <option value="all">Value: All</option>
                                <option value="cheap">Cheap (P/E < 15)</option>
                                <option value="fair">Fair (P/E < 25)</option>
                            </select>
                            <select class="control-field" id="filter_yield" onchange="filterStocks()">
                                <option value="all">Yield: All</option>
                                <option value="3">Yield > 3%</option>
                                <option value="6">Yield > 6%</option>
                            </select>
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
                                        <th onclick="sortTable('table_top_picks', 7, 'num')" title="Month-on-month gain objective score">MoM ⬍</th>
                                        <th onclick="sortTable('table_top_picks', 8, 'num')" title="Original confidence score">Base ⬍</th>
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
                let previousSectionId = 'portfolio_section';
                
                function showSection(id) {{
                    // Update Active State
                    if (!document.getElementById(id)) return;
                    
                    localStorage.setItem('pse_active_section', id);
                    // ... rest of function ...
                    
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
                     let navLink = document.querySelector(`.nav-item[data-section="${{id}}"]`);
                     if (navLink) navLink.classList.add('active');
                }}

                // ... functions ...

                // Initialize from LocalStorage
                document.addEventListener('DOMContentLoaded', () => {{
                    const savedSection = localStorage.getItem('pse_active_section');
                    
                    if (savedSection && document.getElementById(savedSection)) {{
                        showSection(savedSection);
                    }}
                    
                    // Add Event Listeners
                    const searchInput = document.getElementById('search_input');
                    if (searchInput) {{
                        searchInput.addEventListener('keyup', filterStocks);
                        searchInput.addEventListener('search', filterStocks);
                    }}
                    
                    ['filter_sector', 'filter_trend', 'filter_val', 'filter_yield'].forEach(id => {{
                        const el = document.getElementById(id);
                        if (el) el.addEventListener('change', filterStocks);
                    }});
                }});
                
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

                function filterOutcomes() {{
                    const actionFilter = document.getElementById('outcome_action_filter');
                    const horizonFilter = document.getElementById('outcome_horizon_filter');
                    const statusFilter = document.getElementById('outcome_status_filter');
                    const table = document.getElementById('table_action_performance');
                    if (!actionFilter || !horizonFilter || !statusFilter || !table) return;

                    const actionVal = actionFilter.value;
                    const horizonVal = horizonFilter.value;
                    const statusVal = statusFilter.value;
                    let visible = 0;
                    let complete = 0;
                    let pending = 0;

                    Array.from(table.querySelectorAll('tbody tr')).forEach(row => {{
                        const horizons = JSON.parse(row.getAttribute('data-horizons') || '{{}}');
                        const h = horizons[horizonVal] || {{ status: 'pending' }};
                        const rowAction = row.getAttribute('data-action') || '';
                        const rowStatus = h.status || 'pending';

                        const retCell = row.querySelector('.outcome-return');
                        const ddCell = row.querySelector('.outcome-drawdown');
                        const runupCell = row.querySelector('.outcome-runup');
                        const targetCell = row.querySelector('.outcome-target');
                        const stopCell = row.querySelector('.outcome-stop');
                        const statusCell = row.querySelector('.outcome-status');

                        const ret = h.return_pct;
                        retCell.textContent = ret === undefined ? '-' : `${{ret >= 0 ? '+' : ''}}${{ret.toFixed(2)}}%`;
                        retCell.classList.remove('text-green', 'text-red', 'text-muted');
                        retCell.classList.add(ret === undefined ? 'text-muted' : ret > 0 ? 'text-green' : ret < 0 ? 'text-red' : 'text-muted');
                        ddCell.textContent = h.max_drawdown_pct === undefined ? '-' : `${{h.max_drawdown_pct >= 0 ? '+' : ''}}${{h.max_drawdown_pct.toFixed(2)}}%`;
                        runupCell.textContent = h.max_runup_pct === undefined ? '-' : `${{h.max_runup_pct >= 0 ? '+' : ''}}${{h.max_runup_pct.toFixed(2)}}%`;
                        targetCell.textContent = h.target_hit ? 'Yes' : '-';
                        stopCell.textContent = h.stop_hit ? 'Yes' : '-';
                        statusCell.textContent = rowStatus;

                        let show = true;
                        if (actionVal !== 'all' && rowAction !== actionVal) show = false;
                        if (statusVal !== 'all' && rowStatus !== statusVal) show = false;
                        row.style.display = show ? '' : 'none';
                        if (show) {{
                            visible++;
                            if (rowStatus === 'complete') complete++;
                            if (rowStatus === 'pending') pending++;
                        }}
                    }});

                    const visibleEl = document.getElementById('outcome_visible_count');
                    const completeEl = document.getElementById('outcome_complete_count');
                    const pendingEl = document.getElementById('outcome_pending_count');
                    if (visibleEl) visibleEl.textContent = visible;
                    if (completeEl) completeEl.textContent = complete;
                    if (pendingEl) pendingEl.textContent = pending;
                }}

                const PAPER_DATA = {json.dumps(paper_payload)};
                const PAPER_STORAGE_KEY = 'pse_paper_state_v1';

                function defaultPaperState() {{
                    const startingCash = Number(PAPER_DATA.starting_cash || 100000);
                    return {{
                        cash: startingCash,
                        initialCash: startingCash,
                        positions: {{}},
                        ledger: [],
                        processedKeys: []
                    }};
                }}

                function loadPaperState() {{
                    try {{
                        const raw = localStorage.getItem(PAPER_STORAGE_KEY);
                        if (!raw) return defaultPaperState();
                        const state = JSON.parse(raw);
                        return {{
                            ...defaultPaperState(),
                            ...state,
                            positions: state.positions || {{}},
                            ledger: Array.isArray(state.ledger) ? state.ledger : [],
                            processedKeys: Array.isArray(state.processedKeys) ? state.processedKeys : []
                        }};
                    }} catch (err) {{
                        return defaultPaperState();
                    }}
                }}

                function savePaperState(state) {{
                    localStorage.setItem(PAPER_STORAGE_KEY, JSON.stringify(state));
                }}

                function formatPaperCurrency(value) {{
                    const num = Number(value || 0);
                    return `₱${{num.toLocaleString(undefined, {{minimumFractionDigits: 2, maximumFractionDigits: 2}})}}`;
                }}

                function paperPrice(symbol) {{
                    const data = (typeof STOCK_DATA !== 'undefined' && STOCK_DATA[symbol]) ? STOCK_DATA[symbol] : null;
                    return Number(PAPER_DATA.prices[symbol] || (data ? data.price : 0) || 0);
                }}

                function paperSector(symbol) {{
                    const data = (typeof STOCK_DATA !== 'undefined' && STOCK_DATA[symbol]) ? STOCK_DATA[symbol] : null;
                    return PAPER_DATA.sectors[symbol] || (data ? data.sector : 'Unknown') || 'Unknown';
                }}

                function addPaperLedger(state, entry) {{
                    state.ledger.unshift({{
                        date: PAPER_DATA.market_date || new Date().toISOString().slice(0, 10),
                        created_at: new Date().toISOString(),
                        ...entry
                    }});
                }}

                function applyPaperBuy(state, item, source, key) {{
                    const symbol = item.symbol;
                    const price = Number(item.entry_price || item.price || paperPrice(symbol));
                    const desiredShares = Number(item.shares || item.suggested_shares || 0);
                    let shares = Math.floor(desiredShares);
                    if (!shares && item.amount && price > 0) shares = Math.floor(Number(item.amount) / price);
                    if (!shares || shares <= 0 || price <= 0) {{
                        addPaperLedger(state, {{
                            action: 'Skipped',
                            symbol,
                            shares: 0,
                            price,
                            amount: 0,
                            source,
                            note: 'No executable share quantity or price'
                        }});
                        if (key) state.processedKeys.push(key);
                        return false;
                    }}

                    let amount = shares * price;
                    if (amount > state.cash) {{
                        shares = Math.floor(state.cash / price);
                        amount = shares * price;
                    }}

                    if (!shares || amount <= 0 || amount > state.cash) {{
                        addPaperLedger(state, {{
                            action: 'Skipped',
                            symbol,
                            shares: 0,
                            price,
                            amount: 0,
                            source,
                            note: 'Insufficient paper cash'
                        }});
                        if (key) state.processedKeys.push(key);
                        return false;
                    }}

                    const existing = state.positions[symbol] || {{shares: 0, avg_price: 0, sector: paperSector(symbol)}};
                    const oldCost = Number(existing.shares || 0) * Number(existing.avg_price || 0);
                    const newShares = Number(existing.shares || 0) + shares;
                    state.positions[symbol] = {{
                        shares: newShares,
                        avg_price: (oldCost + amount) / newShares,
                        sector: item.sector || existing.sector || paperSector(symbol)
                    }};
                    state.cash = Number(state.cash || 0) - amount;
                    addPaperLedger(state, {{
                        action: 'Buy',
                        symbol,
                        shares,
                        price,
                        amount,
                        source,
                        note: item.reason || 'Executed from allocation plan'
                    }});
                    if (key) state.processedKeys.push(key);
                    return true;
                }}

                function runPaperAutomation() {{
                    const state = loadPaperState();
                    const marketDate = PAPER_DATA.market_date || PAPER_DATA.generated_at || 'unknown';
                    let executed = 0;
                    let skipped = 0;

                    (PAPER_DATA.allocation_plan.suggestions || []).forEach(item => {{
                        const key = `${{marketDate}}:AUTO:BUY:${{item.symbol}}`;
                        if (state.processedKeys.includes(key)) return;
                        const ok = applyPaperBuy(state, item, 'auto', key);
                        if (ok) executed++; else skipped++;
                    }});

                    state.lastAutoRun = new Date().toISOString();
                    state.lastMarketDate = marketDate;
                    savePaperState(state);
                    renderPaperTrading();

                    const status = document.getElementById('paper_auto_status');
                    if (status) {{
                        status.textContent = executed || skipped
                            ? `Auto synced: ${{executed}} executed, ${{skipped}} skipped`
                            : `Already synced for ${{marketDate}}`;
                    }}
                }}

                function manualPaperBuy(symbol) {{
                    const suggestion = (PAPER_DATA.allocation_plan.suggestions || []).find(item => item.symbol === symbol);
                    const action = (PAPER_DATA.actions || []).find(item => item.symbol === symbol);
                    const plan = action ? (action.trade_plan || {{}}) : {{}};
                    const price = Number((suggestion || {{}}).entry_price || plan.entry_price || paperPrice(symbol));
                    const state = loadPaperState();
                    const budget = Math.min(Number((suggestion || {{}}).amount || 10000), Number(state.cash || 0));
                    const shares = Math.floor(budget / price);
                    applyPaperBuy(state, {{
                        symbol,
                        shares,
                        entry_price: price,
                        sector: (suggestion || action || {{}}).sector || paperSector(symbol),
                        reason: 'Manual paper buy'
                    }}, 'manual');
                    savePaperState(state);
                    renderPaperTrading();
                }}

                function manualPaperNote(symbol, action) {{
                    const state = loadPaperState();
                    addPaperLedger(state, {{
                        action,
                        symbol,
                        shares: 0,
                        price: paperPrice(symbol),
                        amount: 0,
                        source: 'manual',
                        note: action === 'Watch' ? 'Marked for paper watch' : 'Skipped by manual review'
                    }});
                    savePaperState(state);
                    renderPaperTrading();
                }}

                function renderPaperTrading() {{
                    if (!document.getElementById('paper_positions_body')) return;

                    const state = loadPaperState();
                    const positions = Object.entries(state.positions || {{}})
                        .filter(([, pos]) => Number(pos.shares || 0) > 0)
                        .sort(([a], [b]) => a.localeCompare(b));

                    let invested = 0;
                    let cost = 0;
                    const positionRows = positions.map(([symbol, pos]) => {{
                        const shares = Number(pos.shares || 0);
                        const avg = Number(pos.avg_price || 0);
                        const current = paperPrice(symbol) || avg;
                        const value = shares * current;
                        const pl = value - (shares * avg);
                        invested += value;
                        cost += shares * avg;
                        const plClass = pl >= 0 ? 'text-green' : 'text-red';
                        const click = (typeof STOCK_DATA !== 'undefined' && STOCK_DATA[symbol]) ? `onclick="showStockDetails('${{symbol}}')" style="cursor:pointer;"` : '';
                        return `
                            <tr ${{click}}>
                                <td class="mono" style="font-weight:800; color:var(--accent);">${{symbol}}</td>
                                <td class="mono">${{shares.toLocaleString()}}</td>
                                <td class="mono">${{formatPaperCurrency(avg)}}</td>
                                <td class="mono">${{formatPaperCurrency(current)}}</td>
                                <td class="mono">${{formatPaperCurrency(value)}}</td>
                                <td class="mono ${{plClass}}">${{formatPaperCurrency(pl)}}</td>
                            </tr>
                        `;
                    }}).join('');

                    const equity = Number(state.cash || 0) + invested;
                    const totalPl = equity - Number(state.initialCash || 0);
                    document.getElementById('paper_positions_body').innerHTML = positionRows || '<tr><td colspan="6" style="text-align:center; color:var(--text-tertiary);">No paper positions yet.</td></tr>';
                    document.getElementById('paper_equity').textContent = formatPaperCurrency(equity);
                    document.getElementById('paper_cash').textContent = formatPaperCurrency(state.cash);
                    document.getElementById('paper_invested').textContent = formatPaperCurrency(invested);
                    document.getElementById('paper_pl').textContent = formatPaperCurrency(totalPl);
                    document.getElementById('paper_pl').classList.remove('text-green', 'text-red');
                    document.getElementById('paper_pl').classList.add(totalPl >= 0 ? 'text-green' : 'text-red');
                    document.getElementById('paper_position_count').textContent = `${{positions.length}} positions`;
                    document.getElementById('paper_processed_badge').textContent = `${{state.processedKeys.length}} processed`;

                    const actionRows = (PAPER_DATA.allocation_plan.suggestions || []).map(item => `
                        <tr>
                            <td class="mono" style="font-weight:800; color:var(--accent);">${{item.symbol}}</td>
                            <td><span class="action-pill action-good">${{item.action || 'Allocate'}}</span></td>
                            <td class="mono">${{formatPaperCurrency(item.amount)}}</td>
                            <td class="mono">${{Number(item.shares || 0).toLocaleString()}}</td>
                            <td class="mono">${{formatPaperCurrency(item.entry_price)}}</td>
                            <td>
                                <button class="command-btn paper-secondary-btn" onclick="manualPaperBuy('${{item.symbol}}')">Buy</button>
                                <button class="command-btn paper-secondary-btn" onclick="manualPaperNote('${{item.symbol}}', 'Watch')">Watch</button>
                                <button class="command-btn paper-danger-btn" onclick="manualPaperNote('${{item.symbol}}', 'Skipped')">Skip</button>
                            </td>
                        </tr>
                    `).join('');
                    document.getElementById('paper_actions_body').innerHTML = actionRows || '<tr><td colspan="6" style="text-align:center; color:var(--text-tertiary);">No allocation candidates today.</td></tr>';

                    const ledgerRows = (state.ledger || []).map(entry => {{
                        const symbolClick = (typeof STOCK_DATA !== 'undefined' && STOCK_DATA[entry.symbol]) ? `onclick="showStockDetails('${{entry.symbol}}')"` : '';
                        const actionClass = entry.action === 'Buy' ? 'action-good' : entry.action === 'Skipped' ? 'action-risk' : 'action-watch';
                        return `
                            <tr>
                                <td class="mono">${{entry.date || '-'}}</td>
                                <td><span class="action-pill ${{actionClass}}">${{entry.action}}</span></td>
                                <td class="mono" ${{symbolClick}} style="font-weight:800; color:var(--accent);">${{entry.symbol || '-'}}</td>
                                <td class="mono">${{Number(entry.shares || 0).toLocaleString()}}</td>
                                <td class="mono">${{formatPaperCurrency(entry.price)}}</td>
                                <td class="mono">${{formatPaperCurrency(entry.amount)}}</td>
                                <td style="min-width:260px; color:var(--text-secondary); font-size:0.82rem;">${{entry.note || '-'}}</td>
                            </tr>
                        `;
                    }}).join('');
                    document.getElementById('paper_ledger_body').innerHTML = ledgerRows || '<tr><td colspan="7" style="text-align:center; color:var(--text-tertiary);">Paper ledger is empty.</td></tr>';
                    document.getElementById('paper_ledger_count').textContent = `${{(state.ledger || []).length}} entries`;

                    const status = document.getElementById('paper_auto_status');
                    if (status && state.lastMarketDate) {{
                        status.textContent = `Last synced ${{state.lastMarketDate}}`;
                    }}
                }}

                function resetPaperTrading() {{
                    if (!confirm('Reset the local paper portfolio and ledger?')) return;
                    localStorage.removeItem(PAPER_STORAGE_KEY);
                    runPaperAutomation();
                }}

                function exportPaperTrading() {{
                    const state = loadPaperState();
                    const blob = new Blob([JSON.stringify(state, null, 2)], {{type: 'application/json'}});
                    const url = URL.createObjectURL(blob);
                    const link = document.createElement('a');
                    link.href = url;
                    link.download = `pse-paper-trading-${{PAPER_DATA.market_date || 'export'}}.json`;
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                    URL.revokeObjectURL(url);
                }}

                document.addEventListener('DOMContentLoaded', () => {{
                    runPaperAutomation();
                }});
                
                function sortTable(tableId, n, type) {{
                    var table, rows, switching, i, x, y, shouldSwitch, dir, switchcount = 0;
                    table = document.getElementById(tableId);
                    if (!table) return;
                    switching = true;
                    dir = "asc";
                    
                    while (switching) {{
                        switching = false;
                        rows = table.rows;
                        for (i = 1; i < (rows.length - 1); i++) {{
                            shouldSwitch = false;
                            x = rows[i].getElementsByTagName("TD")[n];
                            y = rows[i + 1].getElementsByTagName("TD")[n];
                            if (!x || !y) continue;
                            
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
            <!-- Client-Side Portfolio Logic -->
            <script>

                
                // Toast Notification
                function showToast(msg) {{
                    let toast = document.createElement('div');
                    toast.className = 'toast';
                    toast.innerText = msg;
                    document.body.appendChild(toast);
                    setTimeout(() => {{ toast.remove(); }}, 3000);
                }}
                
                // --- API INTEGRATION ---
                async function apiCall(endpoint, data) {{
                    try {{
                        const response = await fetch(endpoint, {{
                            method: 'POST',
                            headers: {{ 'Content-Type': 'application/json' }},
                            body: JSON.stringify(data)
                        }});
                        const res = await response.json();
                        if (res.success) {{
                            window.location.reload();
                        }} else {{
                            alert('Error: ' + (res.error || 'Unknown error'));
                        }}
                    }} catch (e) {{
                         alert('Server not running? Make sure to run "python app.py" to use this feature.');
                    }}
                }}

                let positionToRemove = null;
                function removePosition(symbol) {{
                    positionToRemove = symbol;
                    document.getElementById('remove_symbol_display').innerText = symbol;
                    document.getElementById('removeModal').style.display = 'flex';
                }}
                
                function confirmRemove() {{
                    if(positionToRemove) {{
                        apiCall('/api/remove', {{ symbol: positionToRemove }});
                    }}
                }}

                function openAddModal(symbol, price) {{
                    document.getElementById('addModal').style.display = 'flex';
                    if(symbol) document.getElementById('add_symbol').value = symbol;
                    if(price) document.getElementById('add_price').value = price;
                    document.getElementById('add_shares').value = "";
                }}
                
                function submitAddPosition() {{
                    const sym = document.getElementById('add_symbol').value.toUpperCase();
                    const shares = document.getElementById('add_shares').value;
                    const price = document.getElementById('add_price').value;
                    
                    if(!sym || !shares || !price) {{
                        alert("Please fill all fields");
                        return;
                    }}
                    
                    apiCall('/api/add', {{
                        symbol: sym,
                        shares: parseFloat(shares),
                        price: parseFloat(price)
                    }});
                }}

                // Initialize
            </script>
            <style>
                .watchlist-btn {{
                    cursor: pointer;
                    font-size: 1.2rem;
                    color: var(--text-tertiary);
                    margin-left: 8px;
                    transition: color 0.2s;
                    user-select: none;
                }}
                .watchlist-btn:hover {{ color: var(--accent); }}
                
                .toast {{
                    position: fixed;
                    bottom: 20px;
                    right: 20px;
                    background: var(--bg-panel);
                    color: #fff;
                    padding: 10px 20px;
                    border-radius: 8px;
                    border: 1px solid var(--accent);
                    z-index: 9999;
                    animation: fadeIn 0.3s;
                }}
                @keyframes fadeIn {{ from {{ opacity: 0; transform: translateY(10px); }} to {{ opacity: 1; transform: translateY(0); }} }}
            </style>
            <!-- Inject Global Data -->
            <script>
                const STOCK_DATA = {json.dumps(self.all_stock_data)};
            </script>
            <!-- Add Position Modal -->
            <div id="addModal" class="modal-overlay">
                <div class="modal-content" style="height:auto; max-width:400px; overflow:visible;">
                    <span class="close-btn" onclick="document.getElementById('addModal').style.display='none'">&times;</span>
                    <h2 style="margin-top:0;">Add Position</h2>
                    <div style="display:flex; flex-direction:column; gap:15px; margin-top:15px;">
                        <div>
                            <label style="color:var(--text-tertiary); font-size:0.8rem;">Symbol</label>
                            <input type="text" id="add_symbol" class="search-bar" style="width:100%;" placeholder="e.g. BDO">
                        </div>
                        <div>
                            <label style="color:var(--text-tertiary); font-size:0.8rem;">Shares</label>
                            <input type="number" id="add_shares" class="search-bar" style="width:100%;" placeholder="0">
                        </div>
                        <div>
                            <label style="color:var(--text-tertiary); font-size:0.8rem;">Avg Price</label>
                            <input type="number" id="add_price" class="search-bar" style="width:100%;" step="0.01" placeholder="0.00">
                        </div>
                        <button onclick="submitAddPosition()" style="background:var(--accent); color:white; border:none; padding:12px; border-radius:8px; font-weight:bold; cursor:pointer; margin-top:10px;">ADD TO PORTFOLIO</button>
                    </div>
                </div>
            </div>

            <!-- Remove Confirmation Modal -->
            <div id="removeModal" class="modal-overlay">
                <div class="modal-content" style="height:auto; max-width:400px;">
                     <h3 style="margin-top:0;">Confirm Removal</h3>
                     <p style="color:var(--text-secondary); margin:20px 0;">Are you sure you want to remove <strong id="remove_symbol_display" style="color:var(--text-primary);"></strong> from your portfolio?</p>
                     
                     <div style="display:flex; gap:10px; justify-content:flex-end;">
                          <button onclick="document.getElementById('removeModal').style.display='none'" style="background:transparent; border:1px solid var(--border); color:var(--text-secondary); padding:8px 16px; border-radius:6px; cursor:pointer;">Cancel</button>
                          <button onclick="confirmRemove()" style="background:var(--red); border:none; color:white; padding:8px 16px; border-radius:6px; cursor:pointer; font-weight:bold;">Remove Position</button>
                     </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        return os.path.abspath(output_file)

    def open_in_browser(self, file_path: str):
        if os.environ.get("CI") or os.environ.get("NO_BROWSER"):
            print(f"[CI] Skipping browser open for {file_path}")
            return
        webbrowser.open('file://' + file_path)
