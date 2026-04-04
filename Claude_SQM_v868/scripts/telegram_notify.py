# -*- coding: utf-8 -*-
"""Telegram 진행 알림 유틸리티."""
import os
import sys
import json
import requests

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
if os.path.exists(env_path):
    with open(env_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                os.environ.setdefault(key.strip(), val.strip())

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")

PROGRESS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.progress.json')


def send(message: str):
    """Send a message to Telegram."""
    if not BOT_TOKEN or not CHAT_ID:
        print("ERROR: BOT_TOKEN or CHAT_ID missing")
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        res = requests.post(url, json={
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }, timeout=10)
        return res.status_code == 200
    except Exception as e:
        print(f"Telegram send error: {e}")
        return False


def update_progress(phase: str, detail: str, percent: int):
    """Update progress file and send Telegram message."""
    data = {"phase": phase, "detail": detail, "percent": percent}
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)

    bar = "█" * (percent // 5) + "░" * (20 - percent // 5)
    msg = (
        f"<b>SQM v867 진행 알림</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📍 <b>{phase}</b>\n"
        f"📝 {detail}\n"
        f"📊 [{bar}] {percent}%\n"
        f"━━━━━━━━━━━━━━━━━━"
    )
    return send(msg)


if __name__ == "__main__":
    if len(sys.argv) >= 4:
        update_progress(sys.argv[1], sys.argv[2], int(sys.argv[3]))
    elif len(sys.argv) >= 2:
        send(sys.argv[1])
    else:
        print("Usage: python telegram_notify.py <phase> <detail> <percent>")
        print("   or: python telegram_notify.py <message>")
