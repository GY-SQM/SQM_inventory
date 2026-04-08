# -*- coding: utf-8 -*-
"""
Telegram Bridge v4
==================
기능:
  1. 5분마다 정기 상태 알림
  2. yes/no 유형 대기 감지 + 사용자 응답
  3. 1/2/3 선택 유형 대기 감지 + 사용자 응답
  4. 자유 문장 지시 입력 → Claude 전달
  5. 무응답/idle 상태 감지 + 상세 알림
  6. 오류 메시지 감지 + Telegram 전파
  7. Phase 진행 자동 감지 + 기록
  8. 재시작 / 중지 명령 지원
"""
import os
import sys
import time
import re
import subprocess
import threading
import queue
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

try:
    import requests
except ImportError:
    print("ERROR: pip install requests")
    sys.exit(1)

BOT_TOKEN       = os.getenv("BOT_TOKEN", "")
CHAT_ID         = os.getenv("CHAT_ID", "")
IDLE_TIMEOUT    = int(os.getenv("IDLE_TIMEOUT", "120"))
POLL_INTERVAL   = int(os.getenv("POLL_INTERVAL", "2"))
STATUS_INTERVAL = 300

logs_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs'
)
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

# 감지 패턴
YES_NO_PATTERNS = [
    r'(yes|no|y/n|y or n)',
    r'(continue\?|proceed\?)',
    r'(overwrite\?)',
    r'(예|아니오|계속하시겠습니까|진행하시겠습니까|확인하시겠습니까)',
]
CHOICE_PATTERNS = [
    r'\b1\b.*\b2\b.*\b3\b',
    r'select.*option',
    r'choose.*\d',
    r'선택.*\d',
    r'\[1\].*\[2\]',
    r'enter choice',
]
ERROR_PATTERNS = [
    r'error:',
    r'traceback',
    r'exception',
    r'failed',
    r'fatal',
    r'오류',
    r'실패',
    r'\[fail\]',
    r'modulenotfounderror',
    r'syntaxerror',
    r'importerror',
    r'filenotfounderror',
    r'permissionerror',
]


def send_telegram(text: str) -> bool:
    if not BOT_TOKEN or not CHAT_ID:
        logger.warning("BOT_TOKEN/CHAT_ID 없음")
        return False
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    if len(text) > 4000:
        text = text[:4000] + "\n...(잘림)"
    try:
        res = requests.post(url, json={
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
        }, timeout=10)
        return res.status_code == 200
    except Exception as e:
        logger.error(f"Telegram 전송 실패: {e}")
        return False


def get_telegram_updates(offset=0):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    try:
        res = requests.get(url, params={"offset": offset, "timeout": 3}, timeout=10)
        if res.status_code == 200:
            return res.json().get("result", [])
    except Exception:
        pass
    return []


def enqueue_output(pipe, q):
    try:
        for line in iter(pipe.readline, ''):
            q.put(line)
        pipe.close()
    except Exception:
        pass


def detect_wait_type(text: str) -> str:
    lower = text.lower()
    for pat in ERROR_PATTERNS:
        if re.search(pat, lower):
            return 'error'
    for pat in YES_NO_PATTERNS:
        if re.search(pat, lower):
            return 'yes_no'
    for pat in CHOICE_PATTERNS:
        if re.search(pat, lower):
            return 'choice'
    return 'normal'


class TelegramBridge:

    def __init__(self, master_path: str, project_dir: str):
        self.master_path      = master_path
        self.project_dir      = project_dir
        self.process          = None
        self.last_output_time = time.time()
        self.last_status_time = time.time()
        self.last_output      = ""
        self.recent_lines     = []
        self.update_offset    = 0
        self.running          = False
        self.output_queue     = queue.Queue()
        self.idle_notified    = False
        self.start_time       = time.time()
        self.phase_log        = []
        self.error_count      = 0
        self.wait_type        = 'normal'

    def start(self):
        logger.info("=" * 50)
        logger.info("Telegram Bridge v4 시작")

        send_telegram(
            "<b>🚀 SQM Telegram Bridge v4 시작</b>\n"
            f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"MASTER: {os.path.basename(self.master_path)}\n"
            f"Idle 감지: {IDLE_TIMEOUT}초 | 정기 알림: 5분\n\n"
            "<b>📋 지원 명령어:</b>\n"
            "  y, n → yes/no 응답\n"
            "  1, 2, 3 → 선택 응답\n"
            "  자유 문장 → Claude 에 직접 전달\n"
            "  상태 → 현재 상태 조회\n"
            "  재시작 → Claude 재시작\n"
            "  중지 → 전체 종료\n\n"
            "<b>⚡ 자동 감지:</b>\n"
            "  yes/no 대기 → 자동 알림\n"
            "  1/2/3 선택 → 자동 알림\n"
            "  오류 발생 → 즉시 알림\n"
            "  2분 무응답 → 알림\n"
            "  5분마다 → 정기 보고"
        )

        self.running = True
        self._start_claude()

        reader_thread = threading.Thread(
            target=enqueue_output,
            args=(self.process.stdout, self.output_queue),
            daemon=True
        )
        reader_thread.start()

        try:
            while self.running:

                if self.process.poll() is not None:
                    self._drain_output()
                    exit_code = self.process.returncode
                    elapsed_min = int((time.time() - self.start_time) / 60)
                    send_telegram(
                        f"<b>{'✅ Claude 완료!' if exit_code == 0 else '❌ 비정상 종료'}</b>\n"
                        f"종료 코드: {exit_code}\n"
                        f"총 실행: {elapsed_min}분\n"
                        f"오류 횟수: {self.error_count}회\n\n"
                        f"진행 단계:\n{self._phase_summary()}\n\n"
                        f"최근 출력:\n<pre>{self._safe_output(500)}</pre>"
                    )
                    break

                new_output = self._read_output()

                if new_output:
                    detected = detect_wait_type(new_output)

                    if detected == 'yes_no' and self.wait_type != 'yes_no':
                        self.wait_type = 'yes_no'
                        send_telegram(
                            "<b>❓ yes/no 응답 필요</b>\n\n"
                            f"<pre>{self._safe_lines(5)}</pre>\n\n"
                            "y → 예 | n → 아니오"
                        )

                    elif detected == 'choice' and self.wait_type != 'choice':
                        self.wait_type = 'choice'
                        send_telegram(
                            "<b>🔢 선택 필요 (1/2/3)</b>\n\n"
                            f"<pre>{self._safe_lines(5)}</pre>\n\n"
                            "1, 2, 또는 3 입력"
                        )

                    elif detected == 'error':
                        self.error_count += 1
                        send_telegram(
                            f"<b>🚨 오류 감지! ({self.error_count}번째)</b>\n"
                            f"시간: {datetime.now().strftime('%H:%M:%S')}\n\n"
                            f"<b>오류 내용:</b>\n"
                            f"<pre>{self._safe_output(600)}</pre>\n\n"
                            "진행 → 무시하고 계속\n"
                            "재시작 → Claude 재시작\n"
                            "중지 → 전체 종료"
                        )

                    else:
                        self.wait_type = 'normal'

                self._check_telegram()

                # 5분 정기 알림
                if time.time() - self.last_status_time >= STATUS_INTERVAL:
                    elapsed_min = int((time.time() - self.start_time) / 60)
                    idle_sec = int(time.time() - self.last_output_time)
                    send_telegram(
                        f"<b>📊 5분 정기 상태 보고</b>\n"
                        f"시간: {datetime.now().strftime('%H:%M:%S')}\n"
                        f"총 실행: {elapsed_min}분\n"
                        f"마지막 출력: {idle_sec}초 전\n"
                        f"오류 횟수: {self.error_count}회\n"
                        f"현재 상태: {self._wait_type_label()}\n\n"
                        f"진행 단계:\n{self._phase_summary()}\n\n"
                        f"최근 출력:\n<pre>{self._safe_output(400)}</pre>"
                    )
                    self.last_status_time = time.time()

                # idle 감지
                elapsed_idle = time.time() - self.last_output_time
                if elapsed_idle > IDLE_TIMEOUT and not self.idle_notified:
                    elapsed_min = int((time.time() - self.start_time) / 60)
                    send_telegram(
                        f"<b>⚠️ Claude 무응답 감지!</b>\n"
                        f"무응답: {int(elapsed_idle)}초\n"
                        f"총 실행: {elapsed_min}분\n"
                        f"오류 횟수: {self.error_count}회\n\n"
                        f"<b>현재 상황:</b>\n"
                        "Claude 가 입력을 기다리거나\n"
                        "작업이 멈췄을 수 있습니다.\n\n"
                        f"<b>최근 출력:</b>\n"
                        f"<pre>{self._safe_output(500)}</pre>\n\n"
                        "<b>명령:</b>\n"
                        "y/n → yes/no\n"
                        "1/2/3 → 선택\n"
                        "진행 → 계속\n"
                        "재시작 → 재시작\n"
                        "상태 → 상태 조회\n"
                        "또는 자유 문장 입력"
                    )
                    self.idle_notified = True

                time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            send_telegram("⛔ Ctrl+C 중단")
        except Exception as e:
            logger.error(f"Bridge 오류: {e}")
            send_telegram(f"<b>❌ Bridge 오류</b>\n{str(e)[:500]}")
        finally:
            self.running = False
            if self.process and self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.process.kill()
            send_telegram(
                f"<b>🔚 Bridge 종료</b>\n"
                f"총 실행: {int((time.time()-self.start_time)/60)}분\n"
                f"오류 횟수: {self.error_count}회"
            )

    def _start_claude(self):
        with open(self.master_path, 'r', encoding='utf-8') as f:
            master_content = f.read()
        cmd = ["claude", "--dangerously-skip-permissions", "-p", master_content]
        logger.info(f"Claude 실행: {len(master_content)}자")
        try:
            self.process = subprocess.Popen(
                cmd, cwd=self.project_dir,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True,
                bufsize=1, encoding='utf-8', errors='replace',
            )
            send_telegram(f"✅ Claude 시작 (PID: {self.process.pid})")
        except FileNotFoundError:
            send_telegram("❌ claude 명령어 없음")
            sys.exit(1)

    def _read_output(self) -> str:
        new_text = ""
        lines_read = 0
        while not self.output_queue.empty() and lines_read < 100:
            try:
                line = self.output_queue.get_nowait()
                if line:
                    self.last_output_time = time.time()
                    self.idle_notified = False
                    self.last_output += line
                    new_text += line
                    if len(self.last_output) > 3000:
                        self.last_output = self.last_output[-3000:]
                    self.recent_lines.append(line.rstrip())
                    if len(self.recent_lines) > 10:
                        self.recent_lines = self.recent_lines[-10:]
                    if any(kw in line for kw in
                           ["Phase", "완료", "✅", "PASSED", "[OK]", "SUCCESS"]):
                        self.phase_log.append(
                            f"{datetime.now().strftime('%H:%M:%S')} "
                            f"{line.rstrip()[:80]}"
                        )
                        if len(self.phase_log) > 50:
                            self.phase_log = self.phase_log[-50:]
                    logger.info(f"Claude: {line.rstrip()}")
                    lines_read += 1
            except queue.Empty:
                break
        return new_text

    def _drain_output(self):
        time.sleep(0.5)
        self._read_output()

    def _safe_output(self, chars=500) -> str:
        text = self.last_output[-chars:] if self.last_output else "(출력 없음)"
        return (text.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;"))

    def _safe_lines(self, n=5) -> str:
        lines = self.recent_lines[-n:] if self.recent_lines else ["(출력 없음)"]
        text = "\n".join(lines)
        return (text.replace("&", "&amp;")
                    .replace("<", "&lt;")
                    .replace(">", "&gt;"))

    def _phase_summary(self) -> str:
        if not self.phase_log:
            return "  (기록 없음)"
        return "\n".join(f"  {p}" for p in self.phase_log[-10:])

    def _wait_type_label(self) -> str:
        return {
            'yes_no': '❓ yes/no 대기',
            'choice': '🔢 선택 대기',
            'error':  '🚨 오류 상태',
            'normal': '✅ 정상 실행 중',
        }.get(self.wait_type, '알 수 없음')

    def _check_telegram(self):
        updates = get_telegram_updates(self.update_offset)
        for update in updates:
            self.update_offset = update["update_id"] + 1
            msg = update.get("message", {})
            chat_id = str(msg.get("chat", {}).get("id", ""))
            if chat_id != CHAT_ID:
                continue
            text = msg.get("text", "").strip()
            if not text:
                continue

            logger.info(f"Telegram 수신: {text}")

            if text == "상태":
                elapsed_min = int((time.time() - self.start_time) / 60)
                send_telegram(
                    f"<b>📊 상태 조회</b>\n"
                    f"시간: {datetime.now().strftime('%H:%M:%S')}\n"
                    f"총 실행: {elapsed_min}분\n"
                    f"마지막 출력: {int(time.time()-self.last_output_time)}초 전\n"
                    f"오류 횟수: {self.error_count}회\n"
                    f"현재 상태: {self._wait_type_label()}\n\n"
                    f"진행 단계:\n{self._phase_summary()}\n\n"
                    f"최근 10줄:\n<pre>{self._safe_lines(10)}</pre>"
                )

            elif text == "재시작":
                send_telegram("🔄 Claude 재시작 중...")
                if self.process and self.process.poll() is None:
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        self.process.kill()
                time.sleep(2)
                self._start_claude()
                reader_thread = threading.Thread(
                    target=enqueue_output,
                    args=(self.process.stdout, self.output_queue),
                    daemon=True
                )
                reader_thread.start()
                self.idle_notified = False
                self.wait_type = 'normal'
                self.last_output_time = time.time()

            elif text == "중지":
                send_telegram("⛔ 중지 요청. 종료합니다.")
                self.running = False

            else:
                # yes/no, 1/2/3, 자유 문장 모두 Claude stdin 전달
                if self.process and self.process.poll() is None and self.process.stdin:
                    try:
                        self.process.stdin.write(text + "\n")
                        self.process.stdin.flush()
                        self.idle_notified = False
                        self.wait_type = 'normal'
                        self.last_output_time = time.time()
                        send_telegram(f"✉️ 전달: <code>{text[:80]}</code>")
                    except Exception as e:
                        send_telegram(f"❌ 전달 실패: {e}")
                else:
                    send_telegram("⚠️ Claude 실행 중 아님")


def main():
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates = [
        "SQM_무중단_작업지시서.md",
        "MASTER_FINAL_v868_통합완성본.md",
        "MASTER_FINAL_v867_통합완성본.md",
    ]
    master_path = None
    for name in candidates:
        path = os.path.join(project_dir, name)
        if os.path.exists(path):
            master_path = path
            break
    if not master_path:
        print("ERROR: MASTER 파일 없음")
        sys.exit(1)
    print(f"MASTER: {master_path}")
    bridge = TelegramBridge(master_path, project_dir)
    bridge.start()


if __name__ == "__main__":
    main()
