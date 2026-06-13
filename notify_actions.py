import os
import requests


DIGEST_FILE = "daily_actions.md"


def load_digest():
    if not os.path.exists(DIGEST_FILE):
        return ""
    with open(DIGEST_FILE, "r", encoding="utf-8") as f:
        return f.read()


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
    digest = load_digest()
    if not digest:
        print("No daily action digest found; skipping notification.")
        return

    top_section = digest.split("## Top Actions", 1)
    message = digest if len(top_section) == 1 else top_section[0] + "## Top Actions" + top_section[1]
    send_telegram(message)


if __name__ == "__main__":
    main()
