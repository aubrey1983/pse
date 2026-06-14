import os
import json
from datetime import datetime, timezone
import requests


DIGEST_FILE = "daily_actions.md"
DAILY_ACTIONS_FILE = "data/daily_actions.json"
ACTION_OUTCOMES_FILE = "data/action_outcomes.json"
METADATA_HEALTH_FILE = "data/metadata_health.json"
DASHBOARD_URL = "https://aubrey1983.github.io/pse/"


def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_digest():
    if not os.path.exists(DIGEST_FILE):
        return ""
    with open(DIGEST_FILE, "r", encoding="utf-8") as f:
        return f.read()


def parse_date(value):
    if not value or value == "-":
        return None
    try:
        if "T" in value:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        return datetime.fromisoformat(value[:10]).date()
    except ValueError:
        return None


def days_old(value):
    parsed = parse_date(value)
    if not parsed:
        return None
    return (datetime.now(timezone.utc).date() - parsed).days


def freshness_status(actions, outcomes, metadata_health):
    market_age = days_old(actions.get("market_date"))
    actions_age = days_old(actions.get("generated_at"))
    outcomes_age = days_old(outcomes.get("generated_at"))
    issues = []
    if market_age is None or market_age > 5:
        issues.append("market data")
    if actions_age is None or actions_age > 2:
        issues.append("action plan")
    if outcomes_age is None or outcomes_age > 2:
        issues.append("outcomes")
    if metadata_health.get("status") not in (None, "", "ok"):
        issues.append("metadata")
    if len(issues) >= 2:
        return "Needs Attention", issues
    if issues:
        return "Stale", issues
    return "Fresh", []


def money(value):
    return f"PHP {float(value or 0):,.0f}"


def build_smart_digest():
    actions = load_json(DAILY_ACTIONS_FILE)
    if not actions:
        return ""

    outcomes = load_json(ACTION_OUTCOMES_FILE)
    metadata_health = load_json(METADATA_HEALTH_FILE)
    summary = actions.get("summary", {})
    allocation = actions.get("allocation_plan", {})
    readiness = actions.get("add_readiness", {})
    status, issues = freshness_status(actions, outcomes, metadata_health)

    lines = [
        "PSE Daily Strategy Brief",
        f"Generated: {actions.get('generated_at', '-')}",
        f"Market date: {actions.get('market_date', '-')}",
        "",
        f"Data: {status}" + (f" ({', '.join(issues)})" if issues else ""),
        f"Rebalance: {allocation.get('stance', 'Wait')}",
        f"Budget: {money(allocation.get('budget', 0))} | Suggested: {money((allocation.get('budget', 0) or 0) - (allocation.get('remaining_budget', 0) or 0))}",
        "",
        "Action Summary",
        f"Review Risk: {summary.get('review_risk', 0)} | Add: {summary.get('add', 0)} | Watchlist: {summary.get('watchlist', 0)} | Trim: {summary.get('trim_watch', 0)}",
    ]

    suggestions = allocation.get("suggestions", [])
    if suggestions:
        lines.extend(["", "Suggested Allocation"])
        for item in suggestions[:4]:
            lines.append(
                f"- {item.get('symbol')}: {money(item.get('amount', 0))}, {item.get('shares', 0):,.0f} shares @ PHP {item.get('entry_price', 0):.2f} | MoM {item.get('mom_score', 0)} | R/R {item.get('reward_risk', 0):.2f}"
            )
    else:
        lines.extend(["", "Suggested Allocation", "- None today. Waiting for cleaner Add setup."])

    near_adds = readiness.get("closest", [])[:5]
    if near_adds:
        lines.extend(["", "Closest Add Setups"])
        for item in near_adds:
            blockers = "; ".join(item.get("blockers", [])[:2]) or "Needs confirmation"
            lines.append(
                f"- {item.get('symbol')} ({item.get('readiness_score', 0):.1f}% ready): {blockers}"
            )

    risk_reviews = [item for item in actions.get("actions", []) if item.get("action") == "Review Risk"][:5]
    if risk_reviews:
        lines.extend(["", "Top Risk Reviews"])
        for item in risk_reviews:
            plan = item.get("trade_plan", {})
            lines.append(
                f"- {item.get('symbol')}: MoM {item.get('mom_score', 0)} | {item.get('trend', '-')} | Stop PHP {plan.get('stop_loss', 0):.2f}"
            )

    learning = actions.get("settings", {}).get("learning_profile", {})
    lines.extend([
        "",
        f"Learning: {learning.get('status', 'collecting')} | sample {learning.get('sample_size', 0)} on {learning.get('preferred_horizon', '30')}D",
        f"Dashboard: {DASHBOARD_URL}",
    ])

    return "\n".join(lines)


def send_telegram(message):
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("Telegram secrets not configured; skipping notification.")
        return False

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message[:3900],
        "disable_web_page_preview": True,
    }
    response = requests.post(url, json=payload, timeout=20)
    response.raise_for_status()
    print("Telegram digest sent.")
    return True


def main():
    digest = build_smart_digest() or load_digest()
    if not digest:
        print("No daily action digest found; skipping notification.")
        return

    send_telegram(digest)


if __name__ == "__main__":
    main()
