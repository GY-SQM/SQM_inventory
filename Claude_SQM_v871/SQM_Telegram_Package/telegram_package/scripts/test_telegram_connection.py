# -*- coding: utf-8 -*-
"""Telegram Bot 연결 테스트 스크립트."""
import os
import sys

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

def main():
    if not BOT_TOKEN or not CHAT_ID:
        print("ERROR: BOT_TOKEN or CHAT_ID missing")
        sys.exit(1)
    print(f"BOT_TOKEN: {BOT_TOKEN[:10]}...{BOT_TOKEN[-4:]}")
    print(f"CHAT_ID: {CHAT_ID}")
    print("Sending test message...")
    try:
        import requests
    except ImportError:
        print("ERROR: pip install requests")
        sys.exit(1)
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    res = requests.post(url, json={
        "chat_id": CHAT_ID,
        "text": "SQM Telegram 연결 테스트 성공!"
    }, timeout=10)
    if res.status_code == 200:
        print("SUCCESS: Telegram message sent!")
    else:
        print(f"FAIL: {res.status_code} - {res.text}")
        sys.exit(1)

if __name__ == "__main__":
    main()
