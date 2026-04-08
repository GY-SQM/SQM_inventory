# -*- coding: utf-8 -*-
"""Claude AutoPilot — 단순 Telegram 알림 발송 유틸리티"""
import os, sys

_env_candidates = [
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'),
    '.env',
]
for _p in _env_candidates:
    if os.path.exists(_p):
        with open(_p, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    os.environ.setdefault(k.strip(), v.strip())
        break

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHAT_ID   = os.getenv("CHAT_ID", "")


def send(message: str) -> bool:
    if not BOT_TOKEN or not CHAT_ID:
        print("ERROR: BOT_TOKEN 또는 CHAT_ID 없음 — .env 확인")
        return False
    try:
        import requests
        res = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"},
            timeout=10
        )
        return res.status_code == 200
    except Exception as e:
        print(f"Telegram 전송 오류: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) >= 2:
        ok = send(" ".join(sys.argv[1:]))
        sys.exit(0 if ok else 1)
    else:
        print("사용법: python telegram_notify.py 메시지")
