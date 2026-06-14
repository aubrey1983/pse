import json
import os
from datetime import datetime, timezone


TECHNICAL_DATA_FILE = "data/technical_data.json"
HISTORY_FILE = "data/daily_action_history.json"
OUTPUT_FILE = "data/action_outcomes.json"
HORIZONS = [5, 10, 20, 30]
MIN_LEARNING_SAMPLE = 12


def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def get_history_series(tech_data, symbol):
    rows = tech_data.get(symbol, {}).get("history", [])
    clean_rows = []
    for row in rows:
        time = row.get("time")
        close = row.get("close")
        low = row.get("low", close)
        high = row.get("high", close)
        if time and close is not None:
            clean_rows.append({
                "time": time,
                "close": float(close),
                "low": float(low if low is not None else close),
                "high": float(high if high is not None else close),
            })
    clean_rows.sort(key=lambda x: x["time"])
    return clean_rows


def find_entry_index(series, action_date):
    for idx, row in enumerate(series):
        if row["time"] >= action_date:
            return idx
    return None


def evaluate_action(action_date, action, series):
    idx = find_entry_index(series, action_date)
    if idx is None:
        return None

    entry = float(action.get("entry_price") or series[idx]["close"] or 0)
    if entry <= 0:
        return None

    stop_loss = float(action.get("stop_loss") or 0)
    target_price = float(action.get("target_price") or 0)
    max_available = len(series) - idx - 1
    horizons = {}

    for horizon in HORIZONS:
        if max_available < horizon:
            horizons[str(horizon)] = {"status": "pending", "days_available": max_available}
            continue

        window = series[idx + 1: idx + horizon + 1]
        end = window[-1]["close"]
        low = min(row["low"] for row in window)
        high = max(row["high"] for row in window)
        return_pct = ((end - entry) / entry) * 100.0
        max_drawdown_pct = ((low - entry) / entry) * 100.0
        max_runup_pct = ((high - entry) / entry) * 100.0
        stop_hit = bool(stop_loss and low <= stop_loss)
        target_hit = bool(target_price and high >= target_price)

        horizons[str(horizon)] = {
            "status": "complete",
            "return_pct": return_pct,
            "max_drawdown_pct": max_drawdown_pct,
            "max_runup_pct": max_runup_pct,
            "stop_hit": stop_hit,
            "target_hit": target_hit,
            "end_date": window[-1]["time"],
        }

    return {
        "date": action_date,
        "symbol": action.get("symbol"),
        "action": action.get("action"),
        "source": action.get("source"),
        "sector": action.get("sector"),
        "priority": action.get("priority", 0),
        "mom_score": action.get("mom_score", 0),
        "trend": action.get("trend"),
        "entry_price": entry,
        "stop_loss": stop_loss,
        "target_price": target_price,
        "reward_risk": action.get("reward_risk", 0),
        "horizons": horizons,
    }


def summarize(outcomes):
    summary = {}
    for horizon in HORIZONS:
        h_key = str(horizon)
        complete = [o for o in outcomes if o["horizons"].get(h_key, {}).get("status") == "complete"]
        pending = [o for o in outcomes if o["horizons"].get(h_key, {}).get("status") == "pending"]
        by_action = {}
        overall = {
            "count": len(complete),
            "win_count": 0,
            "avg_return_pct": 0.0,
            "avg_drawdown_pct": 0.0,
            "avg_runup_pct": 0.0,
            "target_hits": 0,
            "stop_hits": 0,
        }

        for outcome in complete:
            action = outcome["action"]
            h = outcome["horizons"][h_key]
            bucket = by_action.setdefault(action, {
                "count": 0,
                "win_count": 0,
                "avg_return_pct": 0.0,
                "avg_drawdown_pct": 0.0,
                "avg_runup_pct": 0.0,
                "target_hits": 0,
                "stop_hits": 0,
            })
            bucket["count"] += 1
            win = 1 if h["return_pct"] > 0 else 0
            target_hit = 1 if h["target_hit"] else 0
            stop_hit = 1 if h["stop_hit"] else 0
            bucket["win_count"] += win
            bucket["avg_return_pct"] += h["return_pct"]
            bucket["avg_drawdown_pct"] += h["max_drawdown_pct"]
            bucket["avg_runup_pct"] += h["max_runup_pct"]
            bucket["target_hits"] += target_hit
            bucket["stop_hits"] += stop_hit

            overall["win_count"] += win
            overall["avg_return_pct"] += h["return_pct"]
            overall["avg_drawdown_pct"] += h["max_drawdown_pct"]
            overall["avg_runup_pct"] += h["max_runup_pct"]
            overall["target_hits"] += target_hit
            overall["stop_hits"] += stop_hit

        for bucket in by_action.values():
            count = bucket["count"] or 1
            bucket["win_rate_pct"] = (bucket["win_count"] / count) * 100.0
            bucket["avg_return_pct"] = bucket["avg_return_pct"] / count
            bucket["avg_drawdown_pct"] = bucket["avg_drawdown_pct"] / count
            bucket["avg_runup_pct"] = bucket["avg_runup_pct"] / count
            bucket["target_hit_rate_pct"] = (bucket["target_hits"] / count) * 100.0
            bucket["stop_hit_rate_pct"] = (bucket["stop_hits"] / count) * 100.0

        if complete:
            count = len(complete)
            overall["win_rate_pct"] = (overall["win_count"] / count) * 100.0
            overall["avg_return_pct"] = overall["avg_return_pct"] / count
            overall["avg_drawdown_pct"] = overall["avg_drawdown_pct"] / count
            overall["avg_runup_pct"] = overall["avg_runup_pct"] / count
            overall["target_hit_rate_pct"] = (overall["target_hits"] / count) * 100.0
            overall["stop_hit_rate_pct"] = (overall["stop_hits"] / count) * 100.0
        else:
            overall.update({
                "win_rate_pct": 0.0,
                "target_hit_rate_pct": 0.0,
                "stop_hit_rate_pct": 0.0,
            })

        summary[h_key] = {
            "complete": len(complete),
            "pending": len(pending),
            "overall": overall,
            "by_action": by_action,
        }
    return summary


def build_learning_profile(summary):
    preferred_horizon = "30"
    if summary.get("20", {}).get("complete", 0) > summary.get("30", {}).get("complete", 0):
        preferred_horizon = "20"

    horizon_summary = summary.get(preferred_horizon, {})
    by_action = horizon_summary.get("by_action", {})
    complete = horizon_summary.get("complete", 0)
    hints = []
    adjustments = {
        "add_mom_threshold_delta": 0,
        "add_reward_risk_delta": 0.0,
        "watchlist_mom_threshold_delta": 0,
    }

    if complete < MIN_LEARNING_SAMPLE:
        hints.append(
            f"Learning is collecting evidence. Need at least {MIN_LEARNING_SAMPLE} completed {preferred_horizon}-day outcomes before changing thresholds."
        )
        return {
            "status": "collecting",
            "preferred_horizon": preferred_horizon,
            "min_sample": MIN_LEARNING_SAMPLE,
            "sample_size": complete,
            "adjustments": adjustments,
            "hints": hints,
        }

    add_stats = by_action.get("Add", {})
    watch_stats = by_action.get("Watchlist", {})

    if add_stats.get("count", 0) >= MIN_LEARNING_SAMPLE:
        if add_stats.get("avg_return_pct", 0) < 0 or add_stats.get("win_rate_pct", 0) < 45:
            adjustments["add_mom_threshold_delta"] = 5
            adjustments["add_reward_risk_delta"] = 0.2
            hints.append("Add calls are underperforming; require stronger MoM score and reward/risk before adding.")
        elif add_stats.get("avg_return_pct", 0) >= 2 and add_stats.get("win_rate_pct", 0) >= 55 and add_stats.get("stop_hit_rate_pct", 0) <= 25:
            adjustments["add_mom_threshold_delta"] = -2
            adjustments["add_reward_risk_delta"] = -0.1
            hints.append("Add calls are working; allow slightly more qualified Add candidates.")

    if watch_stats.get("count", 0) >= MIN_LEARNING_SAMPLE:
        if watch_stats.get("avg_return_pct", 0) < -1 or watch_stats.get("win_rate_pct", 0) < 40:
            adjustments["watchlist_mom_threshold_delta"] = 5
            hints.append("Watchlist calls are weak; raise the MoM threshold for new watchlist names.")
        elif watch_stats.get("avg_return_pct", 0) >= 1.5 and watch_stats.get("win_rate_pct", 0) >= 55:
            adjustments["watchlist_mom_threshold_delta"] = -2
            hints.append("Watchlist calls are productive; keep monitoring for promotion into Add candidates.")

    if not hints:
        hints.append("Evidence is mature enough, but no threshold change is justified yet.")

    return {
        "status": "active",
        "preferred_horizon": preferred_horizon,
        "min_sample": MIN_LEARNING_SAMPLE,
        "sample_size": complete,
        "adjustments": adjustments,
        "hints": hints,
    }


def generate_outcomes():
    tech_data = load_json(TECHNICAL_DATA_FILE)
    action_history = load_json(HISTORY_FILE)
    if not isinstance(action_history, list):
        action_history = []

    series_cache = {}
    outcomes = []
    for day in action_history:
        action_date = day.get("date")
        actions = day.get("tracked_actions") or day.get("top_actions", [])
        for action in actions:
            symbol = action.get("symbol")
            if not symbol:
                continue
            if symbol not in series_cache:
                series_cache[symbol] = get_history_series(tech_data, symbol)
            outcome = evaluate_action(action_date, action, series_cache[symbol])
            if outcome:
                outcomes.append(outcome)

    summary = summarize(outcomes)
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "horizons": HORIZONS,
        "summary": summary,
        "learning_profile": build_learning_profile(summary),
        "outcomes": outcomes,
    }
    save_json(OUTPUT_FILE, result)
    print(f"Generated {len(outcomes)} action outcomes -> {OUTPUT_FILE}")
    return result


if __name__ == "__main__":
    generate_outcomes()
