# -*- coding: utf-8 -*-
"""
Claude AutoPilot — Telegram Bridge
====================================
범용 Claude Code + Telegram 자동화 모듈
어떤 프로젝트에도 사용 가능

기능:
  1. Claude Code 실행 + 출력 모니터링
  2. Telegram 양방향 통신 (명령/응답)
  3. 5분 정기 진행률 보고
  4. 단계 완료 즉시 알림
  5. 오류 즉시 알림
  6. 무응답 감지 알림
  7. Watchdog 자동 재시작 지원
  8. 슬래시 명령어 지원 (/help /status /progress 등)
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

# ── .env 로드 ─────────────────────────────────────────────
_env_candidates = [
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'),
    '.env',
]
for _env_path in _env_candidates:
    if os.path.exists(_env_path):
        with open(_env_path, encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    os.environ.setdefault(k.strip(), v.strip())
        break

try:
    import requests
except ImportError:
    print("ERROR: pip install requests")
    sys.exit(1)

# ── 설정 ──────────────────────────────────────────────────
BOT_TOKEN       = os.getenv("BOT_TOKEN", "")
CHAT_ID         = os.getenv("CHAT_ID", "")
CLAUDE_PATH     = os.getenv("CLAUDE_PATH", "claude")
IDLE_TIMEOUT    = int(os.getenv("IDLE_TIMEOUT", "120"))
POLL_INTERVAL   = int(os.getenv("POLL_INTERVAL", "2"))
STATUS_INTERVAL = 300  # 5분

# ── 로깅 ──────────────────────────────────────────────────
_logs_dir = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs'
)
os.makedirs(_logs_dir, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(os.path.join(_logs_dir, 'bridge.log'), encoding='utf-8'),
        logging.StreamHandler(),
    ]
)
logger = logging.getLogger("bridge")

# ── 진행률 계산 ────────────────────────────────────────────
def get_progress(logs_dir: str) -> dict:
    """completed_steps.txt 파싱 → 진행률 계산"""
    done_file = os.path.join(logs_dir, "completed_steps.txt")
    completed = []
    failed    = []

    if os.path.exists(done_file):
        with open(done_file, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                # 다양한 형식 지원
                # S1_PASS / S1_완료 / ✅ S1 / S1 PASS 등
                upper = line.upper()
                # 단계 ID 추출 (S숫자 또는 P숫자-S숫자 형식)
                match = re.match(r'^([A-Z0-9\-]+)[\s_]', line)
                if match:
                    step_id = match.group(1)
                    if any(kw in upper for kw in ["PASS", "완료", "SUCCESS", "OK"]):
                        if step_id not in completed:
                            completed.append(step_id)
                    elif any(kw in upper for kw in ["FAIL", "실패", "ERROR"]):
                        if step_id not in failed:
                            failed.append(step_id)

    done_count = len(completed)
    # 전체 단계 수 파악 (completed + failed + 미완료)
    total = max(done_count + len(failed) + 1, done_count, 1)

    pct    = min(int(done_count / total * 100), 100) if total > 0 else 0
    filled = pct // 5
    bar    = "█" * filled + "░" * (20 - filled)

    return {
        "completed":  completed,
        "failed":     failed,
        "done_count": done_count,
        "total":      total,
        "pct":        pct,
        "bar":        bar,
        "current":    completed[-1] if completed else "",
    }


def progress_msg(p: dict, title: str = "📊 진행 현황") -> str:
    lines = [
        f"<b>{title}</b>",
        f"─────────────────────",
        f"📈 진행률: {p['done_count']}/{p['total']}단계 ({p['pct']}%)",
        f"[{p['bar']}]",
    ]
    if p["current"]:
        lines.append(f"✅ 마지막 완료: {p['current']}")
    if p["failed"]:
        lines.append(f"❌ 실패: {', '.join(p['failed'][-3:])}")
    if p["completed"]:
        recent = p["completed"][-5:]
        lines.append("✅ 최근 완료:\n" + "\n".join(f"  {s}" for s in recent))
    return "\n".join(lines)


# ── Telegram API ───────────────────────────────────────────
def send_telegram(text: str) -> bool:
    if not BOT_TOKEN or not CHAT_ID:
        logger.warning("BOT_TOKEN/CHAT_ID 없음 — .env 확인")
        return False
    if len(text) > 4000:
        text = text[:4000] + "\n...(잘림)"
    try:
        res = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"},
            timeout=10
        )
        return res.status_code == 200
    except Exception as e:
        logger.error(f"Telegram 전송 실패: {e}")
        return False


def get_updates(offset=0):
    try:
        res = requests.get(
            f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates",
            params={"offset": offset, "timeout": 3},
            timeout=10
        )
        if res.status_code == 200:
            return res.json().get("result", [])
    except Exception:
        pass
    return []


# ── 감지 패턴 ──────────────────────────────────────────────
YES_NO_PATTERNS = [
    r'(yes|no|y/n|y or n)',
    r'(continue\?|proceed\?|overwrite\?)',
    r'(예|아니오|계속하시겠습니까|진행하시겠습니까)',
]
CHOICE_PATTERNS = [
    r'\b1\b.*\b2\b.*\b3\b',
    r'select.*option', r'choose.*\d', r'선택.*\d',
    r'\[1\].*\[2\]', r'enter choice',
]
ERROR_PATTERNS = [
    r'error:', r'traceback', r'exception', r'failed', r'fatal',
    r'오류', r'실패', r'\[fail\]',
    r'modulenotfounderror', r'syntaxerror', r'importerror',
    r'filenotfounderror', r'permissionerror',
]


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


def enqueue_output(pipe, q):
    try:
        for line in iter(pipe.readline, ''):
            q.put(line)
        pipe.close()
    except Exception:
        pass


# ── Bridge 메인 클래스 ─────────────────────────────────────
class TelegramBridge:

    def __init__(self, master_path: str, project_dir: str):
        self.master_path      = master_path
        self.project_dir      = project_dir
        self.process          = None
        self.master_content   = ""
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
        self._pending_text    = ""
        self._pending_confirm = False
        self.logs_dir         = os.path.join(project_dir, 'logs')
        self.last_done_count  = 0
        os.makedirs(self.logs_dir, exist_ok=True)

    def start(self):
        logger.info("=" * 50)
        logger.info("Claude AutoPilot Bridge 시작")

        p = get_progress(self.logs_dir)
        send_telegram(
            "<b>🚀 Claude AutoPilot 시작</b>\n"
            f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"MASTER: {os.path.basename(self.master_path)}\n"
            f"Idle 감지: {IDLE_TIMEOUT}초 | 정기 알림: 5분\n\n"
            + progress_msg(p, "📊 현재 진행률") + "\n\n"
            "<b>📋 명령어:</b>\n"
            "  /help /status /progress /log /error\n"
            "  /restart /stop\n"
            "  y/n  1/2/3  자유문장"
        )

        self.running = True
        self._start_claude()

        reader = threading.Thread(
            target=enqueue_output,
            args=(self.process.stdout, self.output_queue),
            daemon=True
        )
        reader.start()

        try:
            while self.running:
                # 프로세스 종료 감지
                if self.process.poll() is not None:
                    self._drain_output()
                    exit_code = self.process.returncode
                    elapsed   = int((time.time() - self.start_time) / 60)
                    p_final   = get_progress(self.logs_dir)
                    send_telegram(
                        f"<b>{'✅ 작업 완료!' if exit_code == 0 else '❌ 비정상 종료'}</b>\n"
                        f"종료 코드: {exit_code} | 총 실행: {elapsed}분\n"
                        f"오류 횟수: {self.error_count}회\n\n"
                        + progress_msg(p_final, "📊 최종 진행률") + "\n\n"
                        f"최근 출력:\n<pre>{self._safe_output(400)}</pre>"
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
                            f"<pre>{self._safe_output(600)}</pre>\n\n"
                            "진행 → 계속 | 재시작 → /restart | 중지 → /stop"
                        )
                    else:
                        self.wait_type = 'normal'

                self._check_telegram()

                # 5분 정기 보고
                if time.time() - self.last_status_time >= STATUS_INTERVAL:
                    elapsed  = int((time.time() - self.start_time) / 60)
                    idle_sec = int(time.time() - self.last_output_time)
                    p = get_progress(self.logs_dir)
                    send_telegram(
                        f"<b>📊 5분 정기 보고</b> | {datetime.now().strftime('%H:%M:%S')}\n"
                        f"⏱️ 총 실행: {elapsed}분 | 오류: {self.error_count}회\n"
                        f"마지막 출력: {idle_sec}초 전\n\n"
                        + progress_msg(p) + "\n\n"
                        f"최근 출력:\n<pre>{self._safe_output(300)}</pre>"
                    )
                    self.last_status_time = time.time()

                # 단계 완료 즉시 알림
                p_now = get_progress(self.logs_dir)
                if p_now["done_count"] > self.last_done_count:
                    self.last_done_count = p_now["done_count"]
                    send_telegram(
                        "<b>✅ 단계 완료!</b>\n"
                        + progress_msg(p_now, "📈 현재 진행률")
                    )

                # 무응답 감지
                elapsed_idle = time.time() - self.last_output_time
                if elapsed_idle > IDLE_TIMEOUT and not self.idle_notified:
                    send_telegram(
                        f"<b>⚠️ 무응답 감지!</b>\n"
                        f"무응답: {int(elapsed_idle)}초\n\n"
                        f"<pre>{self._safe_output(400)}</pre>\n\n"
                        "명령: y/n | 1/2/3 | /restart | 자유문장"
                    )
                    self.idle_notified = True

                try:
                    time.sleep(POLL_INTERVAL)
                except (EOFError, StopIteration):
                    continue

        except KeyboardInterrupt:
            send_telegram("⚠️ Ctrl+C 감지. 종료하려면 y 입력")
            for _ in range(5):
                time.sleep(2)
                for u in get_updates(self.update_offset):
                    self.update_offset = u["update_id"] + 1
                    txt = u.get("message", {}).get("text", "").strip().lower()
                    if txt in ['y', 'yes']:
                        send_telegram("⛔ 종료합니다.")
                        self.running = False
                        return
                    elif txt in ['n', 'no']:
                        send_telegram("✅ 취소. 계속 진행합니다.")
                        return
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
                f"오류: {self.error_count}회"
            )

    def _start_claude(self):
        with open(self.master_path, 'r', encoding='utf-8') as f:
            self.master_content = f.read()

        claude_cmd = CLAUDE_PATH
        cmd = [claude_cmd, "--dangerously-skip-permissions"]
        logger.info(f"Claude 시작: {claude_cmd} | MASTER {len(self.master_content)}자")

        try:
            kwargs = dict(
                cwd=self.project_dir,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                encoding='utf-8',
                errors='replace',
            )
            if sys.platform == 'win32':
                kwargs['creationflags'] = 0x00000010  # CREATE_NEW_CONSOLE
            self.process = subprocess.Popen(cmd, **kwargs)

            time.sleep(2)
            try:
                self.process.stdin.write(self.master_content + "\n")
                self.process.stdin.flush()
                logger.info("MASTER 내용 전달 완료")
            except Exception as e:
                logger.error(f"MASTER 전달 실패: {e}")

            send_telegram(f"✅ Claude Code 시작 (PID: {self.process.pid})")
        except FileNotFoundError:
            send_telegram(f"❌ Claude 실행 파일 없음: {claude_cmd}\n.env에 CLAUDE_PATH 설정 확인")
            sys.exit(1)

    def _read_output(self) -> str:
        new_text = ""
        lines_read = 0
        while not self.output_queue.empty() and lines_read < 100:
            try:
                line = self.output_queue.get_nowait()
                if line:
                    self.last_output_time = time.time()
                    self.idle_notified    = False
                    self.last_output     += line
                    new_text             += line
                    if len(self.last_output) > 3000:
                        self.last_output = self.last_output[-3000:]
                    self.recent_lines.append(line.rstrip())
                    if len(self.recent_lines) > 10:
                        self.recent_lines = self.recent_lines[-10:]
                    if any(kw in line for kw in ["완료", "✅", "PASSED", "[OK]", "SUCCESS", "PASS"]):
                        self.phase_log.append(
                            f"{datetime.now().strftime('%H:%M:%S')} {line.rstrip()[:80]}"
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
        return text.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

    def _safe_lines(self, n=5) -> str:
        lines = self.recent_lines[-n:] if self.recent_lines else ["(출력 없음)"]
        text  = "\n".join(lines)
        return text.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

    def _wait_label(self) -> str:
        return {
            'yes_no': '❓ yes/no 대기',
            'choice': '🔢 선택 대기',
            'error':  '🚨 오류 상태',
            'normal': '✅ 정상 실행 중',
        }.get(self.wait_type, '알 수 없음')

    def _send_to_claude(self, text: str):
        if not (self.process and self.process.poll() is None):
            send_telegram("⚠️ Claude 실행 중 아님")
            return
        try:
            self.process.stdin.write(text + "\n")
            self.process.stdin.flush()
            self.idle_notified    = False
            self.wait_type        = 'normal'
            self.last_output_time = time.time()
            send_telegram(f"✉️ Claude에 전달: <code>{text[:80]}</code>")
        except Exception as e:
            send_telegram(f"❌ 전달 실패: {e}")

    def _check_telegram(self):
        updates = get_updates(self.update_offset)
        for update in updates:
            self.update_offset = update["update_id"] + 1
            msg     = update.get("message", {})
            chat_id = str(msg.get("chat", {}).get("id", ""))
            if chat_id != CHAT_ID:
                continue
            text = msg.get("text", "").strip()
            if not text:
                continue

            logger.info(f"Telegram 수신: {text}")

            # 자유문장 확인 대기 중
            if self._pending_confirm:
                if text.lower() in ['y', 'yes', '예']:
                    self._pending_confirm = False
                    self._send_to_claude(self._pending_text)
                else:
                    self._pending_confirm = False
                    self._pending_text    = ""
                    send_telegram("❌ 전달 취소")
                continue

            cmd = text.strip()
            cl  = cmd.lower()

            # ── 슬래시 명령어 ──────────────────────────────
            if cmd in ["/help", "도움말"]:
                send_telegram(
                    "<b>📋 명령어 목록</b>\n"
                    "─────────────────────\n"
                    "<b>[Bridge 제어]</b>\n"
                    "  /help     전체 명령어\n"
                    "  /status   상태 + 진행률\n"
                    "  /progress 진행률 막대\n"
                    "  /log      최근 로그 10줄\n"
                    "  /error    오류 목록\n"
                    "  /restart  Claude 재시작\n"
                    "  /stop     전체 종료\n\n"
                    "<b>[응답]</b>\n"
                    "  y / n     예/아니오\n"
                    "  1/2/3     선택지\n"
                    "  자유문장  Claude에 직접 지시"
                )

            elif cmd in ["/status", "상태"]:
                elapsed = int((time.time() - self.start_time) / 60)
                p = get_progress(self.logs_dir)
                send_telegram(
                    f"<b>📊 상태</b> | {datetime.now().strftime('%H:%M:%S')}\n"
                    f"⏱️ 실행: {elapsed}분 | 오류: {self.error_count}회\n"
                    f"상태: {self._wait_label()}\n"
                    f"마지막 출력: {int(time.time()-self.last_output_time)}초 전\n\n"
                    + progress_msg(p) + "\n\n"
                    f"최근 10줄:\n<pre>{self._safe_lines(10)}</pre>"
                )

            elif cmd in ["/progress", "진행률"]:
                p = get_progress(self.logs_dir)
                send_telegram(progress_msg(p, "📈 진행률"))

            elif cmd in ["/log"]:
                send_telegram(f"<b>📝 최근 로그</b>\n<pre>{self._safe_lines(10)}</pre>")

            elif cmd in ["/error"]:
                if self.error_count == 0:
                    send_telegram("✅ 오류 없음")
                else:
                    send_telegram(
                        f"<b>🚨 오류 현황</b>\n총 {self.error_count}회\n\n"
                        f"<pre>{self._safe_output(500)}</pre>"
                    )

            elif cmd in ["/restart", "재시작"]:
                send_telegram("🔄 Claude 재시작 중...")
                if self.process and self.process.poll() is None:
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=10)
                    except subprocess.TimeoutExpired:
                        self.process.kill()
                time.sleep(2)
                self._start_claude()
                threading.Thread(
                    target=enqueue_output,
                    args=(self.process.stdout, self.output_queue),
                    daemon=True
                ).start()
                self.idle_notified    = False
                self.wait_type        = 'normal'
                self.last_output_time = time.time()

            elif cmd in ["/stop", "중지"]:
                send_telegram("⛔ 중지합니다.")
                self.running = False

            else:
                # 단순 응답 즉시 전달
                is_simple = cl in ['y','n','yes','no','1','2','3','진행','계속']
                if is_simple:
                    self._send_to_claude(cmd)
                else:
                    # 자유문장 — 확인 후 전달
                    idle_sec = int(time.time() - self.last_output_time)
                    send_telegram(
                        f"<b>📋 전달 확인</b>\n"
                        f"상태: {self._wait_label()} | {idle_sec}초 전\n\n"
                        f"<pre>{self._safe_lines(5)}</pre>\n\n"
                        f"전달 내용: <code>{cmd[:200]}</code>\n\n"
                        "y → 전달 | n → 취소"
                    )
                    self._pending_text    = cmd
                    self._pending_confirm = True


# ── 진입점 ────────────────────────────────────────────────
def main():
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # 커맨드라인으로 MASTER 경로 지정 가능
    if len(sys.argv) >= 2:
        arg = sys.argv[1]
        master_path = arg if os.path.isabs(arg) else os.path.join(project_dir, arg)
    else:
        # 자동 탐색
        candidates = ["MASTER.md", "MASTER_FINAL.md"]
        # MASTER_*.md 패턴도 검색
        import glob
        candidates += sorted(glob.glob(os.path.join(project_dir, "MASTER*.md")))
        master_path = None
        for c in candidates:
            p = c if os.path.isabs(c) else os.path.join(project_dir, c)
            if os.path.exists(p):
                master_path = p
                break

    if not master_path or not os.path.exists(master_path):
        print(f"ERROR: MASTER 파일 없음 (탐색 경로: {project_dir})")
        print("MASTER.md 파일을 프로젝트 루트에 만들거나:")
        print("  python scripts/telegram_bridge.py MASTER파일명.md")
        sys.exit(1)

    print(f"프로젝트: {project_dir}")
    print(f"MASTER:   {master_path}")
    bridge = TelegramBridge(master_path, project_dir)
    bridge.start()


if __name__ == "__main__":
    main()
