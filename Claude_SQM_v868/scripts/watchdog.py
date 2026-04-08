# -*- coding: utf-8 -*-
"""
SQM Watchdog v1
===============
Bridge 감시 + 죽으면 Telegram 알림 + 자동 재시작
"""
import os
import sys
import time
import subprocess
import requests
import logging
from datetime import datetime

# .env 로드
env_path = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'
)
if os.path.exists(env_path):
    with open(env_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                os.environ.setdefault(key.strip(), val.strip())

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHAT_ID   = os.getenv("CHAT_ID", "")

logs_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs'
)
os.makedirs(logs_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [WATCHDOG] %(message)s",
    handlers=[
        logging.FileHandler(
            os.path.join(logs_dir, 'watchdog.log'), encoding='utf-8'
        ),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger("watchdog")


def send_telegram(text: str) -> bool:
    if not BOT_TOKEN or not CHAT_ID:
        return False
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        res = requests.post(url, json={
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
        }, timeout=10)
        return res.status_code == 200
    except Exception as e:
        logger.error(f"Telegram 전송 실패: {e}")
        return False


def run_bridge(project_dir: str, bridge_path: str) -> int:
    """Bridge 실행 후 종료 코드 반환."""
    try:
        proc = subprocess.Popen(
            [sys.executable, bridge_path],
            cwd=project_dir,
        )
        proc.wait()
        return proc.returncode
    except Exception as e:
        logger.error(f"Bridge 실행 실패: {e}")
        return -1


def main():
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bridge_path = os.path.join(project_dir, 'scripts', 'telegram_bridge.py')

    if not os.path.exists(bridge_path):
        print(f"ERROR: bridge 없음: {bridge_path}")
        sys.exit(1)

    restart_count  = 0
    start_time     = time.time()
    MAX_RESTARTS   = 10       # 최대 재시작 횟수
    RESTART_DELAY  = 5        # 재시작 대기 초

    logger.info("=" * 50)
    logger.info("SQM Watchdog 시작")
    send_telegram(
        "<b>🐕 SQM Watchdog 시작</b>\n"
        f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Bridge 감시 중...\n"
        f"최대 재시작: {MAX_RESTARTS}회"
    )

    while restart_count < MAX_RESTARTS:
        logger.info(f"Bridge 시작 (시도: {restart_count + 1}회)")

        exit_code = run_bridge(project_dir, bridge_path)
        elapsed_min = int((time.time() - start_time) / 60)
        restart_count += 1

        logger.warning(
            f"Bridge 종료! 코드: {exit_code} | "
            f"실행: {elapsed_min}분 | 재시작: {restart_count}회"
        )

        # 정상 종료 (0) 는 재시작 안 함
        if exit_code == 0:
            send_telegram(
                "<b>✅ Bridge 정상 종료</b>\n"
                f"총 실행: {elapsed_min}분\n"
                f"재시작 없이 종료합니다."
            )
            logger.info("정상 종료 — Watchdog 종료")
            break

        # 비정상 종료 → 재시작
        if restart_count < MAX_RESTARTS:
            send_telegram(
                f"<b>🚨 Bridge 비정상 종료!</b>\n"
                f"종료 코드: {exit_code}\n"
                f"총 실행: {elapsed_min}분\n"
                f"재시작: {restart_count}/{MAX_RESTARTS}회\n\n"
                f"{RESTART_DELAY}초 후 자동 재시작합니다...\n\n"
                f"중지하려면: 중지"
            )
            logger.info(f"{RESTART_DELAY}초 후 재시작...")
            time.sleep(RESTART_DELAY)
        else:
            send_telegram(
                f"<b>❌ Bridge 최대 재시작 횟수 초과!</b>\n"
                f"재시작: {restart_count}/{MAX_RESTARTS}회\n"
                f"총 실행: {elapsed_min}분\n\n"
                f"수동으로 run_master.bat 을 다시 실행해 주세요."
            )
            logger.error("최대 재시작 초과 — Watchdog 종료")

    logger.info("Watchdog 종료")


if __name__ == "__main__":
    main()
