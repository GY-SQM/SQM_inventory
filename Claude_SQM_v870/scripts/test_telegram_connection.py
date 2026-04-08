# -*- coding: utf-8 -*-
"""Claude AutoPilot — Telegram 연결 테스트"""
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

if not BOT_TOKEN or not CHAT_ID:
    print("ERROR: BOT_TOKEN 또는 CHAT_ID 없음")
    print(".env 파일 확인")
    sys.exit(1)

print(f"BOT_TOKEN: {BOT_TOKEN[:10]}...{BOT_TOKEN[-4:]}")
print(f"CHAT_ID:   {CHAT_ID}")
print("테스트 메시지 발송 중...")

try:
    import requests
    res = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": "✅ Claude AutoPilot Telegram 연결 테스트 성공!"},
        timeout=10
    )
    if res.status_code == 200:
        print("SUCCESS: 스마트폰 Telegram에서 메시지 확인하세요!")
    else:
        print(f"FAIL: {res.status_code} - {res.text}")
        sys.exit(1)
except ImportError:
    print("ERROR: pip install requests")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}")
    sys.exit(1)
