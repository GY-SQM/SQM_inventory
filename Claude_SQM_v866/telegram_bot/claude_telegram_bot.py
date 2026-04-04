# -*- coding: utf-8 -*-
"""
Claude Code 텔레그램 양방향 봇
텔레그램에서 메시지 보내면 → Claude Code 실행 → 결과 텔레그램으로 회신

사용법:
  python claude_telegram_bot.py

텔레그램에서:
  일반 메시지 → Claude에게 질문 (SQM 프로젝트 컨텍스트)
  /status     → 현재 git 상태 확인
  /diff       → 변경된 파일 목록
  /compile    → 주요 파일 py_compile 검증
  /stop       → 봇 종료
"""

import os
import sys
import json
import time
import subprocess
import logging
import requests

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('telegram_bot.log', encoding='utf-8'),
    ]
)
logger = logging.getLogger(__name__)

# ── 설정 ──────────────────────────────────────────────────
BOT_TOKEN = "8665850610:AAFx9Jcti2_jCKqjs1ZxFcHd18FtywO5-h8"
CHAT_ID = 538125119
PROJECT_DIR = r"F:\프로그램\Sqm 재고관리\Claude_SQM_v865"
GIT_ROOT = r"F:\프로그램\Sqm 재고관리"
TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
MAX_MESSAGE_LENGTH = 4000  # 텔레그램 메시지 최대 길이

# ── 텔레그램 API ─────────────────────────────────────────

def send_message(text: str, chat_id: int = CHAT_ID):
    """텔레그램 메시지 전송. 긴 메시지는 분할."""
    chunks = []
    while len(text) > MAX_MESSAGE_LENGTH:
        split_at = text.rfind('\n', 0, MAX_MESSAGE_LENGTH)
        if split_at <= 0:
            split_at = MAX_MESSAGE_LENGTH
        chunks.append(text[:split_at])
        text = text[split_at:]
    chunks.append(text)

    for chunk in chunks:
        if not chunk.strip():
            continue
        try:
            resp = requests.post(
                f"{TELEGRAM_API}/sendMessage",
                json={"chat_id": chat_id, "text": chunk},
                timeout=30,
            )
            if not resp.json().get("ok"):
                logger.warning(f"Send failed: {resp.text}")
        except Exception as e:
            logger.error(f"Telegram send error: {e}")
        time.sleep(0.3)  # rate limit


def get_updates(offset: int = 0) -> list:
    """텔레그램 업데이트 폴링."""
    try:
        resp = requests.get(
            f"{TELEGRAM_API}/getUpdates",
            params={"offset": offset, "timeout": 30},
            timeout=35,
        )
        data = resp.json()
        if data.get("ok"):
            return data.get("result", [])
    except requests.exceptions.Timeout:
        pass
    except Exception as e:
        logger.error(f"getUpdates error: {e}")
    return []


# ── 명령 처리 ────────────────────────────────────────────

def run_shell(cmd: str, cwd: str = PROJECT_DIR, timeout: int = 60) -> str:
    """셸 명령 실행 후 결과 반환."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            cwd=cwd, timeout=timeout, encoding='utf-8', errors='replace',
        )
        output = (result.stdout or '') + (result.stderr or '')
        return output.strip() or "(no output)"
    except subprocess.TimeoutExpired:
        return "(timeout - 명령이 시간 초과됨)"
    except Exception as e:
        return f"(error: {e})"


def run_claude(prompt: str, timeout: int = 300) -> str:
    """Claude Code CLI 실행. 결과 반환."""
    cmd = f'claude -p "{prompt}" --max-turns 3'
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True,
            cwd=PROJECT_DIR, timeout=timeout,
            encoding='utf-8', errors='replace',
        )
        output = (result.stdout or '').strip()
        if not output:
            output = (result.stderr or '').strip() or "(Claude 응답 없음)"
        return output
    except subprocess.TimeoutExpired:
        return "(timeout - Claude 응답 시간 초과. 5분 제한)"
    except Exception as e:
        return f"(Claude 실행 오류: {e})"


def handle_command(text: str) -> str:
    """명령어 처리."""
    text = text.strip()

    if text == '/start':
        return (
            "SQM Claude Bot 시작!\n\n"
            "사용 가능한 명령:\n"
            "/status — git 상태\n"
            "/diff — 변경 파일 목록\n"
            "/log — 최근 커밋 5개\n"
            "/compile — py_compile 검증\n"
            "/stop — 봇 종료\n\n"
            "일반 메시지 → Claude에게 질문"
        )

    if text == '/status':
        return "Git Status:\n" + run_shell("git status --short", cwd=GIT_ROOT)

    if text == '/diff':
        return "Changed files:\n" + run_shell("git diff --stat", cwd=GIT_ROOT)

    if text == '/log':
        return "Recent commits:\n" + run_shell("git log --oneline -5", cwd=GIT_ROOT)

    if text == '/compile':
        files = [
            "engine_modules/inventory_modular/outbound_mixin.py",
            "gui_app_modular/dialogs/onestop_inbound.py",
            "gui_app_modular/handlers/outbound_handlers.py",
            "core/barcode_scan_engine.py",
        ]
        results = []
        for f in files:
            r = run_shell(f'python -m py_compile "{f}"')
            status = "PASS" if "Error" not in r and "error" not in r else f"FAIL: {r}"
            results.append(f"  {os.path.basename(f)}: {status}")
        return "py_compile:\n" + "\n".join(results)

    if text == '/stop':
        send_message("Bot stopping. Goodbye!")
        sys.exit(0)

    # 일반 메시지 → Claude에게 전달
    send_message("Claude 실행 중... (최대 5분 소요)")
    return run_claude(text)


# ── 메인 루프 ────────────────────────────────────────────

def main():
    logger.info("Claude Telegram Bot started")
    send_message("Claude Telegram Bot started!\n/start 로 명령어 확인")

    offset = 0
    while True:
        updates = get_updates(offset)
        for update in updates:
            offset = update["update_id"] + 1
            msg = update.get("message", {})
            chat_id = msg.get("chat", {}).get("id")
            text = msg.get("text", "")

            if not text or chat_id != CHAT_ID:
                continue

            logger.info(f"Received: {text[:100]}")

            try:
                response = handle_command(text)
                send_message(response, chat_id)
            except Exception as e:
                logger.error(f"Handle error: {e}")
                send_message(f"Error: {e}", chat_id)


if __name__ == "__main__":
    main()
