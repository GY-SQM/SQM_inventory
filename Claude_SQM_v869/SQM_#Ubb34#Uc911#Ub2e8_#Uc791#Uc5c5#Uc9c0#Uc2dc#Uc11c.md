# SQM 범용 무중단 작업지시서 (최종본)
생성일: 2026-04-04
작성자: Ruby (AI Assistant)
버전: v4 (자유문장 상태확인 + 오류전파 + 5분알림 포함)

---

## 0. 절대 실행 규칙

- 절대 사용자에게 질문하지 말 것
- 모든 선택은 스스로 판단할 것
- 파일 덮어쓰기/삭제는 자동 승인된 것으로 간주
- 테스트 실패 시 자동 수정 후 재시도
- 작업 완료 후 다음 단계 자동 진행
- 중단 없이 끝까지 수행

### 강제 테스트 규칙
```
Pre-Test → 구현 → Post-Test → 실패 시 수정 → Re-Test → 통과 → 다음 단계
```

---

## 1. Telegram 연결 정보

```
BOT_TOKEN = 8665850610:AAFx9Jcti2_jCKqjs1ZxFcHd18FtywO5-h8
CHAT_ID   = 538125119
```

### Telegram 명령어
```
y / yes       → yes 응답 (즉시 전달)
n / no        → no 응답 (즉시 전달)
1 / 2 / 3     → 선택 응답 (즉시 전달)
진행 / 계속   → 계속 진행 (즉시 전달)
자유 문장     → 상태 확인 후 y/n 확인 요청
상태          → 현재 상태 조회
재시작        → Claude 재시작
중지          → 전체 종료
```

### Telegram 자동 알림 시점
```
- 작업 시작 시
- 5분마다 정기 상태 보고
- yes/no 대기 감지 시
- 1/2/3 선택 대기 감지 시
- 오류 발생 즉시
- 2분 무응답 감지 시
- Phase 완료 시
- 작업 종료 시
```

### 자유 문장 입력 흐름
```
기동님: "로그 파일 정리해줘"
        ↓
Bridge 자동 응답:
  📋 전달 전 현재 상태 확인
  현재 상태: ✅ 정상 실행 중
  마지막 출력: 30초 전
  최근 출력: [최근 5줄]
  전달할 내용: "로그 파일 정리해줘"
  y → 전달 | n → 취소
        ↓
기동님: y
        ↓
✉️ Claude 전달 완료
```

---

## 2. 프로젝트 정보

```
프로젝트명: SQM (재고관리 시스템)
현재 버전: v8.6.8
PC 경로: F:\프로그램\Sqm 재고관리\Claude_SQM_v868
DB: data/db/sqm_inventory.db
언어: Python / React / FastAPI / SQLite
```

---

## 3. 환경 설정 (.env)

프로젝트 루트에 .env 파일 생성:
```
BOT_TOKEN=8665850610:AAFx9Jcti2_jCKqjs1ZxFcHd18FtywO5-h8
CHAT_ID=538125119
IDLE_TIMEOUT=120
POLL_INTERVAL=2
DB_PATH=data/db/sqm_inventory.db
ADMIN_TOKEN=sqm_admin_2026
API_HOST=127.0.0.1
API_PORT=8000
REACT_PORT=5173
```

---

## 4. 스크립트 파일 코드

### 4-1. scripts/test_telegram_connection.py

```python
# -*- coding: utf-8 -*-
"""Telegram Bot 연결 테스트 스크립트."""
import os
import sys

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
if os.path.exists(env_path):
    with open(env_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                os.environ.setdefault(key.strip(), val.strip())

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")

def main():
    if not BOT_TOKEN or not CHAT_ID:
        print("ERROR: BOT_TOKEN or CHAT_ID missing")
        sys.exit(1)
    print(f"BOT_TOKEN: {BOT_TOKEN[:10]}...{BOT_TOKEN[-4:]}")
    print(f"CHAT_ID: {CHAT_ID}")
    print("Sending test message...")
    try:
        import requests
    except ImportError:
        print("ERROR: pip install requests")
        sys.exit(1)
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    res = requests.post(url, json={
        "chat_id": CHAT_ID,
        "text": "SQM Telegram 연결 테스트 성공!"
    }, timeout=10)
    if res.status_code == 200:
        print("SUCCESS: Telegram message sent!")
    else:
        print(f"FAIL: {res.status_code} - {res.text}")
        sys.exit(1)

if __name__ == "__main__":
    main()

```

---

### 4-2. scripts/telegram_notify.py

```python
# -*- coding: utf-8 -*-
"""Telegram 진행 알림 유틸리티."""
import os
import sys
import json

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
if os.path.exists(env_path):
    with open(env_path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, val = line.split('=', 1)
                os.environ.setdefault(key.strip(), val.strip())

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
CHAT_ID = os.getenv("CHAT_ID", "")
PROGRESS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.progress.json'
)

def send(message: str):
    if not BOT_TOKEN or not CHAT_ID:
        return False
    try:
        import requests
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        res = requests.post(url, json={
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "HTML"
        }, timeout=10)
        return res.status_code == 200
    except Exception as e:
        print(f"Telegram send error: {e}")
        return False

def update_progress(phase: str, detail: str, percent: int):
    data = {"phase": phase, "detail": detail, "percent": percent}
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)
    bar = "█" * (percent // 5) + "░" * (20 - percent // 5)
    msg = (
        f"<b>SQM v868 진행 알림</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📍 <b>{phase}</b>\n"
        f"📝 {detail}\n"
        f"📊 [{bar}] {percent}%\n"
        f"━━━━━━━━━━━━━━━━━━"
    )
    return send(msg)

if __name__ == "__main__":
    if len(sys.argv) >= 4:
        update_progress(sys.argv[1], sys.argv[2], int(sys.argv[3]))
    elif len(sys.argv) >= 2:
        send(sys.argv[1])
    else:
        print("Usage: python telegram_notify.py <phase> <detail> <percent>")
        print("   or: python telegram_notify.py <message>")

```

---

### 4-3. scripts/telegram_bridge.py (v4 최종)

```python
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
        self._pending_text    = ""
        self._pending_confirm = False

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
        cmd = ["claude", "--dangerously-skip-permissions",
               "--file", self.master_path]
        logger.info(f"Claude 실행: --file {self.master_path}")
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

    def _send_to_claude(self, text: str):
        """Claude stdin 에 전달."""
        if self.process and self.process.poll() is None and self.process.stdin:
            try:
                self.process.stdin.write(text + "\n")
                self.process.stdin.flush()
                self.idle_notified = False
                self.wait_type = 'normal'
                self.last_output_time = time.time()
                send_telegram(f"✉️ Claude 전달 완료: <code>{text[:80]}</code>")
            except Exception as e:
                send_telegram(f"❌ 전달 실패: {e}")
        else:
            send_telegram("⚠️ Claude 실행 중 아님")

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

            # 자유 문장 전달 확인 대기 중
            if getattr(self, '_pending_confirm', False):
                if text.lower() in ['y', 'yes', '예']:
                    self._pending_confirm = False
                    self._send_to_claude(self._pending_text)
                else:
                    self._pending_confirm = False
                    self._pending_text = ""
                    send_telegram("❌ 전달 취소됨")
                continue

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
                # yes/no, 1/2/3 → 즉시 전달
                # 자유 문장 → 상태 확인 후 확인 요청
                is_simple = text.lower() in [
                    'y', 'n', 'yes', 'no',
                    '1', '2', '3',
                    '진행', '계속'
                ]

                if not is_simple:
                    # 자유 문장: 상태 먼저 보여주고 확인 요청
                    idle_sec = int(time.time() - self.last_output_time)
                    send_telegram(
                        f"<b>📋 전달 전 현재 상태 확인</b>\n"
                        f"현재 상태: {self._wait_type_label()}\n"
                        f"마지막 출력: {idle_sec}초 전\n\n"
                        f"<b>최근 출력:</b>\n"
                        f"<pre>{self._safe_lines(5)}</pre>\n\n"
                        f"<b>전달할 내용:</b>\n"
                        f"<code>{text[:200]}</code>\n\n"
                        f"y → 전달 | n → 취소"
                    )
                    # 확인 대기 저장
                    self._pending_text = text
                    self._pending_confirm = True
                    continue

                # 단순 응답 즉시 전달
                self._send_to_claude(text)


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

```

---

## 5. 설치 방법

```
1. scripts/ 폴더 생성
2. 위 4-1, 4-2, 4-3 코드를 각각 파일로 저장
3. .env 파일 생성 (섹션 3 참조)
4. 연결 테스트:
   python scripts/test_telegram_connection.py
```

---

## 6. 실행 방법

### Windows PC
```
run_master.bat 더블클릭
→ 1번 선택 (Telegram Bridge)
```

### Android Termux
```bash
cd ~/sqm
bash run_sqm_nonstop.sh
```

---

## 7. 절대 금지 사항

```
- fitz 직접 import 금지 → core/pdf_engine 경유
- engine_modules 직접 수정 금지
- FastAPI 신규 업무 로직 작성 금지
- rollback 없는 쓰기 API 구현 금지
- DB 경로 하드코딩 금지
- 테스트 생략 금지
- 사용자 질문 발생 금지
```

---

## 8. 현재 구현 완료 현황

```
Recon Phase : ✅ 완료
Phase 1~7   : ✅ 완료
Phase 8     : 🔄 진행 중
```

---

## 9. Claude Code 실행 프롬프트

```
현재 작업 기준 원본은 Claude_SQM_v868 이다.
이 MASTER 파일을 기준으로 작업한다.

BOT_TOKEN = 8665850610:AAFx9Jcti2_jCKqjs1ZxFcHd18FtywO5-h8
CHAT_ID   = 538125119

[현재 상태]
Phase 1~7: 완료 / Phase 8: 진행 중

[이번 작업 목표]
1. pytest tests/ -v 전체 통과 확인
2. Phase 8 완료
3. 누락 탭 5개 구현 (Move/Scan/Log/Summary/CargoOverview)
4. npm run build 성공 확인

[강제 원칙]
- 각 Phase 완료 시 Telegram 알림 필수
- 5분마다 상태 보고
- 질문 없이 끝까지 진행
- fitz 직접 import 금지
- engine_modules 직접 수정 금지
```

---

## 10. 중간 재시작 방법

```
현재 작업 기준은 Claude_SQM_v868 이다.
Phase [N] 까지 완료됐고 Phase [N+1] 부터 이어서 진행한다.
BOT_TOKEN=8665850610:AAFx9Jcti2_jCKqjs1ZxFcHd18FtywO5-h8
CHAT_ID=538125119 으로 상태 보고하며 진행한다.
질문 없이 끝까지 수행한다.
```

---

## 11. 오류 대응표

| 오류 | 해결 |
|---|---|
| ModuleNotFoundError: react_api | F: 전환 후 cd 실행 |
| pdf_engine 로드 실패 | core/pdf_engine.py 확인 |
| Telegram 알림 없음 | .env BOT_TOKEN/CHAT_ID 확인 |
| FastAPI 502 | 포트 8000 FastAPI 실행 확인 |
| React 연결 거부 | npm run dev 실행 확인 |
| stdin no data | --file 옵션 사용 확인 |
