# -*- coding: utf-8 -*-
"""
Telegram Bridge — Claude 실행 중 멈춤 감지 + 사용자 원격 제어.
MASTER.md 기준 Telegram Bridge 사양 구현.

핵심 수정사항 (v2):
- --file → -p 플래그로 수정
- Windows 블로킹 readline → 스레드 기반 비차단 읽기
- idle 감지 + telegram 확인이 항상 동작
"""
import os
import sys
import time
import json
import subprocess
import threading
import queue
import logging
from datetime import datetime

# .env 로드
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
if os.path.exists(env_path):
    with open(env_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                os.environ.setdefault(key.strip(), val.strip())

try:
    import requests
except ImportError:
    print("ERROR: requests 패키지 필요. pip install requests")
    sys.exit(1)

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")
IDLE_TIMEOUT = int(os.getenv("IDLE_TIMEOUT", "300"))
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "2"))

# logs 디렉토리 확인
logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
os.makedirs(logs_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(logs_dir, 'bridge.log'), encoding='utf-8'),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger("bridge")


def send_telegram(text: str):
    """Telegram 메시지 전송."""
    if not BOT_TOKEN or not CHAT_ID:
        logger.warning("BOT_TOKEN 또는 CHAT_ID 없음 — 메시지 전송 불가")
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    # Telegram 메시지 최대 4096자
    if len(text) > 4000:
        text = text[:4000] + "\n...(잘림)"
    try:
        res = requests.post(url, json={
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
        }, timeout=10)
        if res.status_code == 200:
            return True
        else:
            logger.error(f"Telegram 응답 오류: {res.status_code} {res.text[:200]}")
            return False
    except Exception as e:
        logger.error(f"Telegram 전송 실패: {e}")
        return False


def get_telegram_updates(offset=0):
    """Telegram 업데이트 가져오기."""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    try:
        res = requests.get(url, params={"offset": offset, "timeout": 3}, timeout=10)
        if res.status_code == 200:
            return res.json().get("result", [])
    except Exception:
        pass
    return []


def enqueue_output(pipe, q):
    """별도 스레드에서 pipe를 읽어 queue에 넣는다 (블로킹 방지)."""
    try:
        for line in iter(pipe.readline, ''):
            q.put(line)
        pipe.close()
    except Exception:
        pass


class TelegramBridge:
    """Claude 실행 + Telegram 원격 제어."""

    def __init__(self, master_path: str, project_dir: str):
        self.master_path = master_path
        self.project_dir = project_dir
        self.process = None
        self.last_output_time = time.time()
        self.last_output = ""
        self.update_offset = 0
        self.running = False
        self.output_queue = queue.Queue()
        self.idle_notified = False

    def start(self):
        """Bridge 시작."""
        logger.info("=" * 50)
        logger.info("Telegram Bridge v2 시작")
        logger.info("=" * 50)

        send_telegram(
            "<b>SQM v867 Telegram Bridge 시작</b>\n"
            f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"MASTER: {os.path.basename(self.master_path)}\n"
            f"Idle 감지: {IDLE_TIMEOUT}초\n\n"
            "명령어:\n"
            "  y / n — 질문 응답\n"
            "  1 / 2 / 3 — 선택\n"
            "  진행 — 다음 단계 진행\n"
            "  상태 — 현재 상태 조회\n"
            "  중지 — Bridge 종료"
        )

        self.running = True
        self._start_claude()

        # stdout 읽기 스레드 시작 (블로킹 방지 핵심)
        reader_thread = threading.Thread(
            target=enqueue_output,
            args=(self.process.stdout, self.output_queue),
            daemon=True
        )
        reader_thread.start()

        # 메인 모니터링 루프
        try:
            while self.running:
                # 프로세스 종료 확인
                if self.process.poll() is not None:
                    # 남은 출력 비우기
                    self._drain_output()
                    exit_code = self.process.returncode
                    send_telegram(
                        f"<b>Claude 프로세스 종료</b>\n"
                        f"종료 코드: {exit_code}\n"
                        f"시간: {datetime.now().strftime('%H:%M:%S')}\n\n"
                        f"최근 출력:\n<pre>{self._safe_output(500)}</pre>"
                    )
                    logger.info(f"Claude 종료 (코드: {exit_code})")
                    break

                # 1) 출력 읽기 (비차단)
                self._read_output()

                # 2) Telegram 메시지 확인
                self._check_telegram()

                # 3) idle 감지
                elapsed = time.time() - self.last_output_time
                if elapsed > IDLE_TIMEOUT and not self.idle_notified:
                    send_telegram(
                        f"<b>Claude {IDLE_TIMEOUT}초 무응답</b>\n"
                        f"시간: {datetime.now().strftime('%H:%M:%S')}\n\n"
                        f"최근 출력:\n<pre>{self._safe_output(400)}</pre>\n\n"
                        "'진행' 또는 명령을 보내세요."
                    )
                    self.idle_notified = True

                time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            logger.info("사용자 Ctrl+C 중단")
            send_telegram("Bridge: 사용자가 Ctrl+C로 중단했습니다.")
        except Exception as e:
            logger.error(f"Bridge 오류: {e}")
            send_telegram(f"<b>Bridge 오류 발생</b>\n{str(e)[:500]}")
        finally:
            self.running = False
            if self.process and self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.process.kill()
            send_telegram(
                f"<b>Bridge 종료</b>\n"
                f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            )

    def _start_claude(self):
        """Claude 프로세스 실행."""
        # MASTER 파일 내용 읽기
        with open(self.master_path, 'r', encoding='utf-8') as f:
            master_content = f.read()

        cmd = [
            "claude",
            "--dangerously-skip-permissions",
            "-p",
            master_content,
        ]
        logger.info(f"Claude 실행: claude --dangerously-skip-permissions -p <MASTER 내용 {len(master_content)}자>")
        logger.info(f"작업 디렉토리: {self.project_dir}")

        try:
            self.process = subprocess.Popen(
                cmd,
                cwd=self.project_dir,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                encoding='utf-8',
                errors='replace',
            )
            logger.info(f"Claude PID: {self.process.pid}")
            send_telegram(f"Claude 프로세스 시작 (PID: {self.process.pid})")
        except FileNotFoundError:
            send_telegram("<b>ERROR: claude 명령어를 찾을 수 없습니다.</b>\nClaude Code CLI가 설치되어 있는지 확인하세요.")
            sys.exit(1)

    def _read_output(self):
        """비차단으로 출력 읽기 (큐에서 가져옴)."""
        lines_read = 0
        while not self.output_queue.empty() and lines_read < 100:
            try:
                line = self.output_queue.get_nowait()
                if line:
                    self.last_output_time = time.time()
                    self.idle_notified = False
                    self.last_output += line
                    # 최근 3000자만 유지
                    if len(self.last_output) > 3000:
                        self.last_output = self.last_output[-3000:]
                    logger.info(f"Claude: {line.rstrip()}")
                    lines_read += 1
            except queue.Empty:
                break

    def _drain_output(self):
        """프로세스 종료 후 남은 출력 모두 읽기."""
        time.sleep(0.5)
        self._read_output()

    def _safe_output(self, chars=500):
        """HTML-safe한 최근 출력."""
        text = self.last_output[-chars:] if self.last_output else "(출력 없음)"
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def _check_telegram(self):
        """Telegram 메시지 확인 + 응답."""
        updates = get_telegram_updates(self.update_offset)
        for update in updates:
            self.update_offset = update["update_id"] + 1
            msg = update.get("message", {})
            chat_id = str(msg.get("chat", {}).get("id", ""))

            # 본인 CHAT_ID만 처리
            if chat_id != CHAT_ID:
                continue

            text = msg.get("text", "").strip()
            if not text:
                continue

            logger.info(f"Telegram 수신: {text}")

            if text == "상태":
                is_running = self.process and self.process.poll() is None
                elapsed = int(time.time() - self.last_output_time)
                send_telegram(
                    f"<b>현재 상태</b>\n"
                    f"실행 중: {'예' if is_running else '아니오'}\n"
                    f"마지막 출력: {elapsed}초 전\n\n"
                    f"최근 출력:\n<pre>{self._safe_output(500)}</pre>"
                )
            elif text == "중지":
                send_telegram("Bridge 중지 요청 수신. 종료합니다.")
                self.running = False
            else:
                # Claude stdin에 전달
                if self.process and self.process.poll() is None and self.process.stdin:
                    try:
                        self.process.stdin.write(text + "\n")
                        self.process.stdin.flush()
                        send_telegram(f"Claude에 전달: {text[:80]}")
                    except Exception as e:
                        send_telegram(f"전달 실패: {e}")
                else:
                    send_telegram("Claude 프로세스가 실행 중이 아닙니다.")


def main():
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    master_path = os.path.join(project_dir, "MASTER_FINAL_v867_통합완성본.md")

    if not os.path.exists(master_path):
        print(f"ERROR: MASTER 파일 없음: {master_path}")
        sys.exit(1)

    bridge = TelegramBridge(master_path, project_dir)
    bridge.start()


if __name__ == "__main__":
    main()
