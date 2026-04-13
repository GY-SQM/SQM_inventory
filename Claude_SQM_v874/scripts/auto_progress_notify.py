# -*- coding: utf-8 -*-
"""
SQM AutoPilot - 작업 진행 상황 자동 텔레그램 알림
=================================================
5분 간격으로 진행 상황 파일(progress.json)을 읽어 텔레그램으로 발송.
Claude가 progress.json을 업데이트하면 다음 주기에 자동 반영.

사용법:
    python scripts/auto_progress_notify.py          # 기본 5분 간격
    python scripts/auto_progress_notify.py --interval 3  # 3분 간격
    python scripts/auto_progress_notify.py --once    # 1회만 발송
"""
import os
import sys
import json
import time
import argparse
from datetime import datetime

# .env 로드
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
CHAT_ID = os.getenv("CHAT_ID", "")
PROGRESS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    ".progress.json"
)


def send_telegram(message: str) -> bool:
    """텔레그램 메시지 발송"""
    if not BOT_TOKEN or not CHAT_ID:
        print("[ERROR] BOT_TOKEN/CHAT_ID 없음")
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
        print(f"[ERROR] 발송 실패: {e}")
        return False


def read_progress() -> dict:
    """진행 상황 파일 읽기"""
    if not os.path.exists(PROGRESS_FILE):
        return {}
    try:
        with open(PROGRESS_FILE, encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def update_progress(data: dict):
    """진행 상황 파일 쓰기 (Claude에서도 호출 가능)"""
    try:
        with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError as e:
        print(f"[ERROR] progress 파일 쓰기 실패: {e}")


def format_progress_message(progress: dict, cycle: int) -> str:
    """진행 상황을 텔레그램 메시지로 포맷"""
    now = datetime.now().strftime("%H:%M:%S")
    phase = progress.get("phase", "작업중")
    task = progress.get("current_task", "-")
    completed = progress.get("completed", [])
    total_tasks = progress.get("total_tasks", "?")
    errors = progress.get("errors", [])

    msg = f"<b>[SQM v871 진행 알림 #{cycle}]</b>\n"
    msg += f"{'='*28}\n"
    msg += f"<b>현재 단계:</b> {phase}\n"
    msg += f"<b>현재 작업:</b> {task}\n"
    msg += f"<b>완료:</b> {len(completed)}/{total_tasks}\n"

    if completed:
        recent = completed[-3:]  # 최근 3개만
        msg += f"\n<b>최근 완료:</b>\n"
        for item in recent:
            msg += f"  [OK] {item}\n"

    if errors:
        msg += f"\n<b>오류 {len(errors)}건:</b>\n"
        for err in errors[-2:]:
            msg += f"  [!] {err}\n"

    msg += f"\n<i>{now}</i>"
    return msg


def main():
    parser = argparse.ArgumentParser(description="SQM 진행 알림")
    parser.add_argument("--interval", type=int, default=5, help="알림 간격(분)")
    parser.add_argument("--once", action="store_true", help="1회만 발송")
    parser.add_argument("--message", type=str, help="직접 메시지 지정")
    args = parser.parse_args()

    if args.message:
        ok = send_telegram(args.message)
        sys.exit(0 if ok else 1)

    interval_sec = args.interval * 60
    cycle = 1
    last_progress_hash = ""

    print(f"[AUTO NOTIFY] 시작 - {args.interval}분 간격")
    print(f"[AUTO NOTIFY] progress 파일: {PROGRESS_FILE}")
    print(f"[AUTO NOTIFY] Ctrl+C로 종료")

    while True:
        progress = read_progress()
        progress_hash = json.dumps(progress, sort_keys=True)

        # 변경 있거나 주기 도래 시 발송
        msg = format_progress_message(progress, cycle)
        ok = send_telegram(msg)
        status = "OK" if ok else "FAIL"
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 알림 #{cycle} {status}")

        last_progress_hash = progress_hash
        cycle += 1

        if args.once:
            break

        time.sleep(interval_sec)


if __name__ == "__main__":
    main()
