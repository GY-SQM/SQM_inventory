# -*- coding: utf-8 -*-
"""
Telegram y 응답 대기 스크립트
- 사용자 키보드 입력 없음
- Telegram 에서 y 받으면 exit(0) → 다음 단계 진행
- Telegram 에서 n 받으면 exit(1) → 중단
- 60분 타임아웃 시 exit(0) → 자동 진행
"""
import os, sys, time, requests

env_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'
)
if os.path.exists(env_path):
    with open(env_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())

BOT_TOKEN = os.getenv('BOT_TOKEN', '')
CHAT_ID   = os.getenv('CHAT_ID', '')
TIMEOUT   = 3600  # 60분 대기
POLL      = 3     # 3초마다 polling

def get_updates(offset=0):
    try:
        res = requests.get(
            f'https://api.telegram.org/bot{BOT_TOKEN}/getUpdates',
            params={'offset': offset, 'timeout': 2}, timeout=10
        )
        if res.status_code == 200:
            return res.json().get('result', [])
    except Exception:
        pass
    return []

def send(msg):
    try:
        requests.post(
            f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage',
            json={'chat_id': CHAT_ID, 'text': msg}, timeout=10
        )
    except Exception:
        pass

step = sys.argv[1] if len(sys.argv) > 1 else '확인'
print(f'[wait_confirm] {step} 기동님 Telegram y 응답 대기 중...')
print(f'[wait_confirm] y = 다음 진행 / n = 중단 / 60분 후 자동 진행')

offset = 0
start  = time.time()

while time.time() - start < TIMEOUT:
    updates = get_updates(offset)
    for u in updates:
        offset = u['update_id'] + 1
        chat   = str(u.get('message', {}).get('chat', {}).get('id', ''))
        text   = u.get('message', {}).get('text', '').strip().lower()
        if chat != CHAT_ID:
            continue
        if text in ['y', 'yes', '예', '확인', 'ok']:
            send(f'✅ {step} 확인 완료 — 다음 단계 자동 진행')
            print(f'[wait_confirm] y 수신 → 진행')
            sys.exit(0)
        elif text in ['n', 'no', '아니오', '취소', 'stop']:
            send(f'❌ {step} 취소 — 배치 중단')
            print(f'[wait_confirm] n 수신 → 중단')
            sys.exit(1)
    time.sleep(POLL)

# 타임아웃 → 자동 진행
send(f'⏰ {step} 60분 타임아웃 — 자동 진행합니다')
print(f'[wait_confirm] 타임아웃 → 자동 진행')
sys.exit(0)
