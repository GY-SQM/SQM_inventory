# -*- coding: utf-8 -*-
"""
Claude AutoPilot — Telegram y/n 응답 대기
키보드 입력 없음 — Telegram 응답만으로 진행 결정
y/yes → exit(0) 진행
n/no  → exit(1) 중단
60분 타임아웃 → exit(0) 자동 진행
"""
import os, sys, time

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
TIMEOUT   = 3600  # 60분
POLL      = 3


def get_updates(offset=0):
    try:
        import requests
        res = requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates",
            params={"offset": offset, "timeout": 2},
            timeout=10
        )
        if res.status_code == 200:
            return res.json().get("result", [])
    except Exception:
        pass
    return []


def send(msg: str):
    try:
        import requests
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": msg},
            timeout=10
        )
    except Exception:
        pass


step = sys.argv[1] if len(sys.argv) > 1 else "확인"
print(f"[wait_confirm] {step} — Telegram y 응답 대기 (60분 타임아웃)")

offset = 0
start  = time.time()

while time.time() - start < TIMEOUT:
    for u in get_updates(offset):
        offset = u["update_id"] + 1
        chat   = str(u.get("message", {}).get("chat", {}).get("id", ""))
        text   = u.get("message", {}).get("text", "").strip().lower()
        if chat != CHAT_ID:
            continue
        if text in ["y", "yes", "예", "확인", "ok"]:
            send(f"✅ {step} 확인 — 다음 단계 진행")
            print("[wait_confirm] y 수신 → 진행")
            sys.exit(0)
        elif text in ["n", "no", "아니오", "취소", "stop"]:
            send(f"❌ {step} 취소")
            print("[wait_confirm] n 수신 → 중단")
            sys.exit(1)
    time.sleep(POLL)

send(f"⏰ {step} 60분 타임아웃 — 자동 진행")
print("[wait_confirm] 타임아웃 → 자동 진행")
sys.exit(0)
