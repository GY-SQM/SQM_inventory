# -*- coding: utf-8 -*-
"""Claude AutoPilot — Watchdog: Bridge 감시 + 자동 재시작"""
import os, sys, time, subprocess, logging
from datetime import datetime

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

_logs_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs'
)
os.makedirs(_logs_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [WATCHDOG] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(_logs_dir, 'watchdog.log'), encoding='utf-8'),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger("watchdog")


def send_telegram(text: str):
    if not BOT_TOKEN or not CHAT_ID:
        return
    try:
        import requests
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"},
            timeout=10
        )
    except Exception as e:
        logger.error(f"Telegram 전송 실패: {e}")


def run_bridge(project_dir: str, bridge_path: str) -> int:
    try:
        proc = subprocess.Popen([sys.executable, bridge_path], cwd=project_dir)
        proc.wait()
        return proc.returncode
    except Exception as e:
        logger.error(f"Bridge 실행 실패: {e}")
        return -1


def main():
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    bridge_path = os.path.join(project_dir, 'scripts', 'telegram_bridge.py')

    if not os.path.exists(bridge_path):
        print(f"ERROR: {bridge_path} 없음")
        sys.exit(1)

    MAX_RESTARTS  = 10
    RESTART_DELAY = 5
    restart_count = 0
    start_time    = time.time()

    logger.info("=" * 50)
    logger.info("Claude AutoPilot Watchdog 시작")
    send_telegram(
        "<b>🐕 Watchdog 시작</b>\n"
        f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Bridge 감시 중 | 최대 재시작: {MAX_RESTARTS}회"
    )

    while restart_count < MAX_RESTARTS:
        logger.info(f"Bridge 시작 (시도: {restart_count + 1}회)")
        exit_code   = run_bridge(project_dir, bridge_path)
        elapsed_min = int((time.time() - start_time) / 60)
        restart_count += 1

        if exit_code == 0:
            send_telegram(
                "<b>✅ Bridge 정상 종료</b>\n"
                f"총 실행: {elapsed_min}분"
            )
            logger.info("정상 종료")
            break

        if restart_count < MAX_RESTARTS:
            send_telegram(
                f"<b>🚨 Bridge 비정상 종료!</b>\n"
                f"종료 코드: {exit_code} | 실행: {elapsed_min}분\n"
                f"재시작: {restart_count}/{MAX_RESTARTS}회\n"
                f"{RESTART_DELAY}초 후 자동 재시작..."
            )
            logger.info(f"{RESTART_DELAY}초 후 재시작...")
            time.sleep(RESTART_DELAY)
        else:
            send_telegram(
                f"<b>❌ 최대 재시작 횟수 초과!</b>\n"
                f"{MAX_RESTARTS}회 재시작 후 포기\n"
                "수동으로 run_master.bat 다시 실행 필요"
            )
            logger.error("최대 재시작 초과")

    logger.info("Watchdog 종료")


if __name__ == "__main__":
    main()
