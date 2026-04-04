# -*- coding: utf-8 -*-
"""Telegram Bot 연결 테스트 스크립트."""
import os
import sys

# .env 파일에서 읽기
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
        print("ERROR: BOT_TOKEN 또는 CHAT_ID가 비어 있습니다.")
        print(f"  .env 경로: {env_path}")
        sys.exit(1)

    print(f"BOT_TOKEN: {BOT_TOKEN[:10]}...{BOT_TOKEN[-4:]}")
    print(f"CHAT_ID: {CHAT_ID}")
    print("Telegram 전송 중...")

    try:
        import requests
    except ImportError:
        print("ERROR: requests 패키지가 없습니다. pip install requests")
        sys.exit(1)

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    res = requests.post(url, json={
        "chat_id": CHAT_ID,
        "text": "SQM v867 Telegram 연결 테스트 성공"
    }, timeout=10)

    if res.status_code == 200:
        print("SUCCESS: Telegram 메시지 전송 성공!")
    else:
        print(f"FAIL: {res.status_code} - {res.text}")
        sys.exit(1)


if __name__ == "__main__":
    main()
