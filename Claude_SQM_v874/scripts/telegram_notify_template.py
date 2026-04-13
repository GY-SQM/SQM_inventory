# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import requests

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

def send_message(message: str) -> None:
    if not BOT_TOKEN or not CHAT_ID:
        print("[WARN] Telegram env missing")
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    resp = requests.post(url, data=payload, timeout=15)
    print(resp.status_code, resp.text)

if __name__ == "__main__":
    send_message("[SQM] test message")
