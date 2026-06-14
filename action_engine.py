import json
import os
from datetime import datetime, timezone

from analyzer import Analyzer
from portfolio_manager import PortfolioManager
from stock_data import normalize_sector


TECHNICAL_DATA_FILE = "data/technical_data.json"
FUNDAMENTAL_DATA_FILE = "data/pse_fundamentals.json"
METADATA_FILE = "data/stock_metadata.json"
OUTCOMES_FILE = "data/action_outcomes.json"
OUTPUT_FILE = "data/daily_actions.json"
HISTORY_FILE = "data/daily_action_history.json"
DIGEST_FILE = "daily_actions.md"


def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


class ActionEngine:
    def __init__(self, monthly_budget=10000, max_position_pct=15.0, max_sector_pct=35.0, risk_per_trade_pct=1.0):
        self.monthly_budget = float(monthly_budget)
        self.max_position_pct = float(max_position_pct)
        self.max_sector_pct = float(max_sector_pct)
        self.risk_per_trade_pct = float(risk_per_trade_pct)
        self.analyzer = Analyzer()
        self.learning_profile = self._load_learning_profile()

    def _load_learning_profile(self):
        outcomes = load_json(OUTCOMES_FILE)
        profile = outcomes.get("learning_profile", {}) if isinstance(outcomes, dict) else {}
        adjustments = profile.get("adjustments", {})
        return {
            "status": profile.get("status", "collecting"),
            "preferred_horizon": profile.get("preferred_horizon", "30"),
            "sample_size": profile.get("sample_size", 0),
            "add_mom_threshold_delta": int(adjustments.get("add_mom_threshold_delta", 0) or 0),
            "add_reward_risk_delta": float(adjustments.get("add_reward_risk_delta", 0.0) or 0.0),
            "watchlist_mom_threshold_delta": int(adjustments.get("watchlist_mom_threshold_delta", 0) or 0),
        }

    def _thresholds(self):
        return {
            "holding_add_mom": max(40, 45 + self.learning_profile["add_mom_threshold_delta"]),
            "candidate_add_mom": max(45, 50 + self.learning_profile["add_mom_threshold_delta"]),
            "watchlist_mom": max(35, 40 + self.learning_profile["watchlist_mom_threshold_delta"]),
            "add_reward_risk": max(1.0, 1.2 + self.learning_profile["add_reward_risk_delta"]),
        }

    def _score_action(self, action, mom_score, gain_loss_pct, allocation_pct, sector_allocation_pct):
        priority = {
            "Review Risk": 100,
            "Trim Watch": 82,
            "Add": 74,
            "Watchlist": 62,
            "Hold": 34,
        }.get(action, 0)
        priority += min(20, max(0, mom_score) / 5)
        if gain_loss_pct < -8:
            priority += min(16, abs(gain_loss_pct))
        if allocation_pct > self.max_position_pct:
            priority += 10
        if sector_allocation_pct > self.max_sector_pct:
            priority += 8
        return round(priority, 2)

    def _plan_trade(self, symbol, tech, total_equity):
        last_close = float(tech.get("last_close") or 0)
        support = float(tech.get("support") or 0)
        resistance = float(tech.get("resistance") or 0)
        stop_loss = float(tech.get("stop_loss") or 0)

        if not stop_loss and support:
            stop_loss = support * 0.97

        if resistance and resistance > last_close:
            target_price = resistance
        elif last_close > 0:
            target_price = last_close * 1.08
        else:
            target_price = 0

        risk_per_share = max(last_close - stop_loss, 0) if last_close and stop_loss else 0
        reward_per_share = max(target_price - last_close, 0) if last_close and target_price else 0
        reward_risk = (reward_per_share / risk_per_share) if risk_per_share > 0 else 0

        risk_budget = total_equity * (self.risk_per_trade_pct / 100.0) if total_equity > 0 else self.monthly_budget * 0.1
        risk_sized_shares = int(risk_budget / risk_per_share) if risk_per_share > 0 else 0
        budget_sized_shares = int(self.monthly_budget / last_close) if last_close > 0 else 0
        suggested_shares = max(0, min(risk_sized_shares or budget_sized_shares, budget_sized_shares))
        suggested_amount = suggested_shares * last_close

        return {
            "entry_price": last_close,
            "stop_loss": stop_loss,
            "target_price": target_price,
            "risk_per_share": risk_per_share,
            "reward_risk": reward_risk,
            "risk_budget": risk_budget,
            "suggested_shares": suggested_shares,
            "suggested_amount": suggested_amount,
        }

    def _classify_holding(self, mom_score, trend, gain_loss_pct, allocation_pct, sector_allocation_pct, reward_risk):
        thresholds = self._thresholds()
        if gain_loss_pct <= -8 or mom_score < 20 or "Strong Downtrend" in trend:
            return "Review Risk"
        if allocation_pct > self.max_position_pct or sector_allocation_pct > self.max_sector_pct:
            return "Trim Watch"
        if mom_score >= thresholds["holding_add_mom"] and gain_loss_pct >= -3 and "Uptrend" in trend and reward_risk >= thresholds["add_reward_risk"]:
            return "Add"
        if mom_score >= thresholds["watchlist_mom"] and "Downtrend" not in trend:
            return "Watchlist"
        return "Hold"

    def _classify_candidate(self, mom_score, trend, rsi, reward_risk, allocation_exists):
        thresholds = self._thresholds()
        if allocation_exists:
            return None
        if mom_score >= thresholds["candidate_add_mom"] and "Uptrend" in trend and 40 <= rsi <= 72 and reward_risk >= thresholds["add_reward_risk"]:
            return "Add"
        if mom_score >= thresholds["watchlist_mom"] and "Downtrend" not in trend:
            return "Watchlist"
        return None

    def _add_readiness(self, symbol, source, mom_score, trend, rsi, reward_risk, gain_loss_pct, trade_plan, sector):
        thresholds = self._thresholds()
        mom_threshold = thresholds["holding_add_mom"] if source == "portfolio" else thresholds["candidate_add_mom"]
        blockers = []

        if mom_score < mom_threshold:
            blockers.append(f"MoM {mom_score} below Add threshold {mom_threshold}")
        if "Uptrend" not in trend:
            blockers.append(f"Trend is {trend}")
        if source == "candidate" and not (40 <= rsi <= 72):
            blockers.append(f"RSI {rsi:.1f} outside 40-72 range")
        if reward_risk < thresholds["add_reward_risk"]:
            blockers.append(f"R/R {reward_risk:.2f} below {thresholds['add_reward_risk']:.2f}")
        if source == "portfolio" and gain_loss_pct < -3:
            blockers.append(f"Position G/L {gain_loss_pct:+.1f}% below -3% Add guard")

        mom_component = min(35.0, max(0.0, mom_score / max(mom_threshold, 1) * 35.0))
        trend_component = 20.0 if "Strong Uptrend" in trend else 15.0 if "Uptrend" in trend else 0.0
        rr_component = min(25.0, max(0.0, reward_risk / max(thresholds["add_reward_risk"], 0.01) * 25.0))
        rsi_component = 15.0 if source == "portfolio" or 40 <= rsi <= 72 else max(0.0, 15.0 - min(abs(rsi - 56), 30) / 30 * 15.0)
        gain_component = 5.0 if source == "candidate" or gain_loss_pct >= -3 else 0.0
        readiness_score = round(min(100.0, mom_component + trend_component + rr_component + rsi_component + gain_component), 1)

        return {
            "symbol": symbol,
            "source": source,
            "sector": sector,
            "readiness_score": readiness_score,
            "qualified": len(blockers) == 0,
            "blockers": blockers[:4],
            "mom_score": mom_score,
            "required_mom": mom_threshold,
            "trend": trend,
            "rsi": rsi,
            "reward_risk": reward_risk,
            "required_reward_risk": thresholds["add_reward_risk"],
            "gain_loss_pct": gain_loss_pct,
            "entry_price": trade_plan["entry_price"],
            "stop_loss": trade_plan["stop_loss"],
            "target_price": trade_plan["target_price"],
        }

    def _latest_market_date(self, tech_data):
        dates = []
        for tech in tech_data.values():
            for row in tech.get("history", []):
                if row.get("time"):
                    dates.append(row["time"])
        return max(dates) if dates else datetime.now(timezone.utc).date().isoformat()

    def _build_allocation_plan(self, actions, add_readiness, sector_values, total_equity):
        budget = self.monthly_budget
        thresholds = self._thresholds()
        eligible_actions = [
            action for action in actions
            if action["action"] == "Add"
            and action["trade_plan"]["suggested_shares"] > 0
            and action.get("sector_allocation_pct", 0) < self.max_sector_pct
        ]
        near_misses = [
            item for item in add_readiness
            if not item["qualified"] and item["readiness_score"] >= 85
        ][:5]

        suggestions = []
        remaining_budget = budget
        for action in eligible_actions[:4]:
            plan = action["trade_plan"]
            entry = plan["entry_price"]
            if entry <= 0 or remaining_budget < entry:
                continue
            max_amount = min(remaining_budget, plan["suggested_amount"], budget * 0.45)
            shares = int(max_amount / entry)
            amount = shares * entry
            if shares <= 0:
                continue
            remaining_budget -= amount
            suggestions.append({
                "symbol": action["symbol"],
                "action": "Allocate",
                "source": action["source"],
                "sector": action["sector"],
                "amount": amount,
                "shares": shares,
                "entry_price": entry,
                "mom_score": action["mom_score"],
                "reward_risk": plan["reward_risk"],
                "reason": "Clears Add rules and position sizing guardrails.",
            })

        stance = "Deploy selectively" if suggestions else "Wait"
        if not suggestions and near_misses:
            stance = "Wait for cleaner entry"

        return {
            "budget": budget,
            "remaining_budget": remaining_budget,
            "stance": stance,
            "max_position_pct": self.max_position_pct,
            "max_sector_pct": self.max_sector_pct,
            "thresholds": thresholds,
            "suggestions": suggestions,
            "waitlist": near_misses,
            "notes": [
                "No capital is allocated unless a name clears Add rules." if not suggestions else "Allocation is capped by monthly budget and risk-sized shares.",
                f"Sector exposure guard is {self.max_sector_pct:.0f}% and position guard is {self.max_position_pct:.0f}%.",
            ],
        }

    def generate(self):
        tech_data = load_json(TECHNICAL_DATA_FILE)
        fund_data = load_json(FUNDAMENTAL_DATA_FILE)
        meta_data = load_json(METADATA_FILE)

        portfolio_mgr = PortfolioManager()
        current_prices = {s: t.get("last_close", 0) for s, t in tech_data.items()}
        portfolio_summary = portfolio_mgr.get_portfolio_summary(current_prices)
        total_equity = portfolio_summary["total_equity"]

        sector_values = {}
        held_symbols = {p["symbol"] for p in portfolio_summary["positions"]}
        for p in portfolio_summary["positions"]:
            symbol = p["symbol"]
            sector = normalize_sector(meta_data.get(symbol, {}).get("sector", "Unknown"))
            sector_values[sector] = sector_values.get(sector, 0.0) + p["market_value"]

        actions = []
        add_readiness = []

        for p in portfolio_summary["positions"]:
            symbol = p["symbol"]
            tech = tech_data.get(symbol, {})
            fund = fund_data.get(symbol, {})
            meta = meta_data.get(symbol, {})
            sector = normalize_sector(meta.get("sector", "Unknown"))
            mom_score, reasons = self.analyzer.calculate_monthly_gain_score(tech, fund)
            trend = tech.get("trend", "Unknown")
            allocation_pct = (p["market_value"] / total_equity * 100.0) if total_equity else 0.0
            sector_allocation_pct = (sector_values.get(sector, 0.0) / total_equity * 100.0) if total_equity else 0.0
            trade_plan = self._plan_trade(symbol, tech, total_equity)
            action = self._classify_holding(
                mom_score,
                trend,
                p["gain_loss_pct"],
                allocation_pct,
                sector_allocation_pct,
                trade_plan["reward_risk"],
            )
            priority = self._score_action(action, mom_score, p["gain_loss_pct"], allocation_pct, sector_allocation_pct)
            readiness = self._add_readiness(
                symbol,
                "portfolio",
                mom_score,
                trend,
                float(tech.get("rsi") or 50),
                trade_plan["reward_risk"],
                p["gain_loss_pct"],
                trade_plan,
                sector,
            )
            add_readiness.append(readiness)

            actions.append({
                "symbol": symbol,
                "name": meta.get("name", symbol),
                "source": "portfolio",
                "action": action,
                "priority": priority,
                "sector": sector,
                "mom_score": mom_score,
                "base_score": self.analyzer.calculate_score(tech, fund)[0],
                "trend": trend,
                "last_close": tech.get("last_close", p["current_price"]),
                "allocation_pct": allocation_pct,
                "sector_allocation_pct": sector_allocation_pct,
                "gain_loss_pct": p["gain_loss_pct"],
                "risk_pct": tech.get("risk_pct", 0),
                "add_readiness": readiness,
                "reasons": reasons[:5],
                "trade_plan": trade_plan,
            })

        candidates = []
        for symbol, tech in tech_data.items():
            if symbol in held_symbols:
                continue
            fund = fund_data.get(symbol, {})
            if fund.get("status") in ["Suspended", "Halted"]:
                continue
            meta = meta_data.get(symbol, {})
            sector = normalize_sector(meta.get("sector", "Unknown"))
            mom_score, reasons = self.analyzer.calculate_monthly_gain_score(tech, fund)
            trade_plan = self._plan_trade(symbol, tech, total_equity)
            rsi = float(tech.get("rsi") or 50)
            readiness = self._add_readiness(
                symbol,
                "candidate",
                mom_score,
                tech.get("trend", "Unknown"),
                rsi,
                trade_plan["reward_risk"],
                0,
                trade_plan,
                sector,
            )
            add_readiness.append(readiness)
            action = self._classify_candidate(
                mom_score,
                tech.get("trend", "Unknown"),
                rsi,
                trade_plan["reward_risk"],
                False,
            )
            if not action:
                continue
            base_score, _ = self.analyzer.calculate_score(tech, fund)
            candidates.append({
                "symbol": symbol,
                "name": meta.get("name", symbol),
                "source": "candidate",
                "action": action,
                "priority": self._score_action(action, mom_score, 0, 0, 0),
                "sector": sector,
                "mom_score": mom_score,
                "base_score": base_score,
                "trend": tech.get("trend", "Unknown"),
                "last_close": tech.get("last_close", 0),
                "allocation_pct": 0,
                "sector_allocation_pct": (sector_values.get(sector, 0.0) / total_equity * 100.0) if total_equity else 0.0,
                "gain_loss_pct": 0,
                "risk_pct": tech.get("risk_pct", 0),
                "add_readiness": readiness,
                "reasons": reasons[:5],
                "trade_plan": trade_plan,
            })

        candidates.sort(key=lambda x: (x["priority"], x["mom_score"], x["base_score"]), reverse=True)
        actions.extend(candidates[:20])
        actions.sort(key=lambda x: (x["priority"], x["mom_score"]), reverse=True)
        closest_adds = [
            item for item in sorted(add_readiness, key=lambda x: (x["qualified"], x["readiness_score"], x["mom_score"]), reverse=True)
            if not item["qualified"]
        ][:15]
        allocation_plan = self._build_allocation_plan(actions, closest_adds, sector_values, total_equity)

        generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        market_date = self._latest_market_date(tech_data)
        result = {
            "generated_at": generated_at,
            "market_date": market_date,
            "settings": {
                "monthly_budget": self.monthly_budget,
                "max_position_pct": self.max_position_pct,
                "max_sector_pct": self.max_sector_pct,
                "risk_per_trade_pct": self.risk_per_trade_pct,
                "learned_thresholds": self._thresholds(),
                "learning_profile": self.learning_profile,
            },
            "summary": {
                "total_actions": len(actions),
                "review_risk": len([a for a in actions if a["action"] == "Review Risk"]),
                "add": len([a for a in actions if a["action"] == "Add"]),
                "watchlist": len([a for a in actions if a["action"] == "Watchlist"]),
                "trim_watch": len([a for a in actions if a["action"] == "Trim Watch"]),
                "hold": len([a for a in actions if a["action"] == "Hold"]),
            },
            "add_readiness": {
                "thresholds": self._thresholds(),
                "qualified_count": len([item for item in add_readiness if item["qualified"]]),
                "near_miss_count": len(closest_adds),
                "closest": closest_adds,
            },
            "allocation_plan": allocation_plan,
            "actions": actions,
        }

        save_json(OUTPUT_FILE, result)
        self._append_history(result)
        self._write_digest(result)
        print(f"Generated {len(actions)} daily actions -> {OUTPUT_FILE}")
        return result

    def _append_history(self, result):
        history = load_json(HISTORY_FILE)
        if not isinstance(history, list):
            history = []
        action_date = result.get("market_date") or result["generated_at"][:10]
        run_date = result["generated_at"][:10]
        history = [
            item for item in history
            if item.get("date") != action_date
            and not (item.get("generated_at", "")[:10] == run_date and not item.get("market_date"))
        ]
        history.append({
            "date": action_date,
            "market_date": action_date,
            "generated_at": result["generated_at"],
            "summary": result["summary"],
            "top_actions": [
                {
                    "symbol": action["symbol"],
                    "action": action["action"],
                    "priority": action["priority"],
                    "mom_score": action["mom_score"],
                }
                for action in result["actions"][:12]
            ],
            "tracked_actions": [
                {
                    "symbol": action["symbol"],
                    "action": action["action"],
                    "source": action["source"],
                    "priority": action["priority"],
                    "mom_score": action["mom_score"],
                    "trend": action["trend"],
                    "sector": action["sector"],
                    "entry_price": action["trade_plan"]["entry_price"],
                    "stop_loss": action["trade_plan"]["stop_loss"],
                    "target_price": action["trade_plan"]["target_price"],
                    "reward_risk": action["trade_plan"]["reward_risk"],
                }
                for action in result["actions"]
            ],
        })
        history = history[-120:]
        save_json(HISTORY_FILE, history)

    def _write_digest(self, result):
        lines = [
            "# Daily Action Digest",
            "",
            f"Generated: {result['generated_at']}",
            "",
            "## Summary",
            "",
            f"- Review Risk: {result['summary']['review_risk']}",
            f"- Add: {result['summary']['add']}",
            f"- Watchlist: {result['summary']['watchlist']}",
            f"- Trim Watch: {result['summary']['trim_watch']}",
            "",
            "## Top Actions",
            "",
            "| Symbol | Action | Priority | MoM | Trend | Entry | Stop | Target | R/R |",
            "|---|---|---:|---:|---|---:|---:|---:|---:|",
        ]
        for action in result["actions"][:15]:
            plan = action["trade_plan"]
            lines.append(
                f"| {action['symbol']} | {action['action']} | {action['priority']:.1f} | "
                f"{action['mom_score']} | {action['trend']} | {plan['entry_price']:.2f} | "
                f"{plan['stop_loss']:.2f} | {plan['target_price']:.2f} | {plan['reward_risk']:.2f} |"
            )
        with open(DIGEST_FILE, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    ActionEngine().generate()
