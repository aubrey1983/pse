import json
import os
from datetime import datetime, timezone


TECHNICAL_DATA_FILE = "data/technical_data.json"
HISTORY_FILE = "data/daily_action_history.json"
OUTPUT_FILE = "data/action_outcomes.json"
HORIZONS = [5, 10, 20, 30]


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

        for outcome in complete:
            action = outcome["action"]
            h = outcome["horizons"][h_key]
            bucket = by_action.setdefault(action, {
                "count": 0,
                "win_count": 0,
                "avg_return_pct": 0.0,
                "avg_drawdown_pct": 0.0,
                "target_hits": 0,
                "stop_hits": 0,
            })
            bucket["count"] += 1
            bucket["win_count"] += 1 if h["return_pct"] > 0 else 0
            bucket["avg_return_pct"] += h["return_pct"]
            bucket["avg_drawdown_pct"] += h["max_drawdown_pct"]
            bucket["target_hits"] += 1 if h["target_hit"] else 0
            bucket["stop_hits"] += 1 if h["stop_hit"] else 0

        for bucket in by_action.values():
            count = bucket["count"] or 1
            bucket["win_rate_pct"] = (bucket["win_count"] / count) * 100.0
            bucket["avg_return_pct"] = bucket["avg_return_pct"] / count
            bucket["avg_drawdown_pct"] = bucket["avg_drawdown_pct"] / count

        summary[h_key] = {
            "complete": len(complete),
            "pending": len(pending),
            "by_action": by_action,
        }
    return summary


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

    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "horizons": HORIZONS,
        "summary": summarize(outcomes),
        "outcomes": outcomes,
    }
    save_json(OUTPUT_FILE, result)
    print(f"Generated {len(outcomes)} action outcomes -> {OUTPUT_FILE}")
    return result


if __name__ == "__main__":
    generate_outcomes()
