# SQM 범용 무중단 작업지시서
생성일: 2026-04-04
작성자: Ruby (AI Assistant)
대상: Claude Code 자율 실행 표준 문서
특징: 이 파일 하나로 어느 PC에서나 무중단 작업 가능

---

## 0. 절대 실행 규칙

### 자율 실행 규칙
- 절대 사용자에게 질문하지 말 것
- 모든 선택은 스스로 판단할 것
- 파일 덮어쓰기 / 삭제는 자동 승인된 것으로 간주할 것
- 테스트 실패 시 자동 수정 후 재시도할 것
- 작업 완료 후 다음 단계 자동 진행
- 중단 없이 끝까지 수행할 것

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

### Telegram 명령어 (작업 중 폰에서 입력)
```
y        → 예
n        → 아니오
1/2/3    → 선택
진행     → 계속 진행
상태     → 현재 상태 조회
재시작   → Claude 재시작
중지     → 전체 종료
```

### Telegram 자동 알림 시점
```
- 작업 시작 시
- 5분마다 정기 상태 보고
- 2분 이상 무응답 감지 시
- Phase 완료 시
- 오류 발생 시
- 작업 완료 시
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
        print(f"  .env path: {env_path}")
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
        "text": "✅ SQM Telegram 연결 테스트 성공!"
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
    """Send a message to Telegram."""
    if not BOT_TOKEN or not CHAT_ID:
        print("ERROR: BOT_TOKEN or CHAT_ID missing")
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
    """Update progress file and send Telegram message."""
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

### 4-3. scripts/telegram_bridge.py

```python
# -*- coding: utf-8 -*-
"""
Telegram Bridge v3
- 5분마다 정기 상태 알림
- 2분 무응답 시 상세 상황 알림
- 사용자 명령으로 Claude 제어
- Phase 진행 자동 감지 및 기록
"""
import os
import sys
import time
import subprocess
import threading
import queue
import logging
from datetime import datetime

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
    print("ERROR: pip install requests")
    sys.exit(1)

BOT_TOKEN     = os.getenv("BOT_TOKEN", "")
CHAT_ID       = os.getenv("CHAT_ID", "")
IDLE_TIMEOUT  = int(os.getenv("IDLE_TIMEOUT", "120"))
POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "2"))
STATUS_INTERVAL = 300  # 5분마다 정기 알림

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


class TelegramBridge:
    def __init__(self, master_path: str, project_dir: str):
        self.master_path        = master_path
        self.project_dir        = project_dir
        self.process            = None
        self.last_output_time   = time.time()
        self.last_status_time   = time.time()
        self.last_output        = ""
        self.update_offset      = 0
        self.running            = False
        self.output_queue       = queue.Queue()
        self.idle_notified      = False
        self.start_time         = time.time()
        self.phase_log          = []

    def start(self):
        logger.info("=" * 50)
        logger.info("Telegram Bridge v3 시작")
        send_telegram(
            "<b>🚀 SQM Telegram Bridge v3 시작</b>\n"
            f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"MASTER: {os.path.basename(self.master_path)}\n"
            f"Idle 감지: {IDLE_TIMEOUT}초\n"
            f"정기 알림: 5분마다\n\n"
            "<b>명령어:</b>\n"
            "  y / n — 질문 응답\n"
            "  1 / 2 / 3 — 선택\n"
            "  진행 — 다음 단계\n"
            "  상태 — 현재 상태 조회\n"
            "  재시작 — Claude 재시작\n"
            "  중지 — Bridge 종료"
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
                        f"<b>{'✅ Claude 완료' if exit_code == 0 else '❌ Claude 비정상 종료'}</b>\n"
                        f"종료 코드: {exit_code}\n"
                        f"총 실행: {elapsed_min}분\n"
                        f"단계 기록:\n{self._phase_summary()}\n\n"
                        f"최근 출력:\n<pre>{self._safe_output(500)}</pre>"
                    )
                    break
                self._read_output()
                self._check_telegram()
                # 5분마다 정기 알림
                if time.time() - self.last_status_time >= STATUS_INTERVAL:
                    elapsed_min = int((time.time() - self.start_time) / 60)
                    idle_sec = int(time.time() - self.last_output_time)
                    send_telegram(
                        f"<b>📊 5분 정기 상태 보고</b>\n"
                        f"시간: {datetime.now().strftime('%H:%M:%S')}\n"
                        f"총 실행: {elapsed_min}분\n"
                        f"마지막 출력: {idle_sec}초 전\n\n"
                        f"진행 단계:\n{self._phase_summary()}\n\n"
                        f"최근 출력:\n<pre>{self._safe_output(400)}</pre>"
                    )
                    self.last_status_time = time.time()
                # idle 감지
                if time.time() - self.last_output_time > IDLE_TIMEOUT and not self.idle_notified:
                    elapsed_min = int((time.time() - self.start_time) / 60)
                    send_telegram(
                        f"<b>⚠️ Claude 멈춤 감지!</b>\n"
                        f"무응답: {int(time.time()-self.last_output_time)}초\n"
                        f"총 실행: {elapsed_min}분\n\n"
                        f"<b>최근 출력:</b>\n"
                        f"<pre>{self._safe_output(500)}</pre>\n\n"
                        f"명령: y/n/진행/재시작/상태"
                    )
                    self.idle_notified = True
                time.sleep(POLL_INTERVAL)
        except KeyboardInterrupt:
            send_telegram("⛔ Ctrl+C 중단")
        except Exception as e:
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
                f"총 실행: {int((time.time()-self.start_time)/60)}분"
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

    def _read_output(self):
        lines_read = 0
        while not self.output_queue.empty() and lines_read < 100:
            try:
                line = self.output_queue.get_nowait()
                if line:
                    self.last_output_time = time.time()
                    self.idle_notified = False
                    self.last_output += line
                    if len(self.last_output) > 3000:
                        self.last_output = self.last_output[-3000:]
                    if "Phase" in line or "완료" in line or "✅" in line:
                        self.phase_log.append(
                            f"{datetime.now().strftime('%H:%M:%S')} {line.rstrip()[:80]}"
                        )
                        if len(self.phase_log) > 50:
                            self.phase_log = self.phase_log[-50:]
                    logger.info(f"Claude: {line.rstrip()}")
                    lines_read += 1
            except queue.Empty:
                break

    def _drain_output(self):
        time.sleep(0.5)
        self._read_output()

    def _safe_output(self, chars=500):
        text = self.last_output[-chars:] if self.last_output else "(출력 없음)"
        return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    def _phase_summary(self):
        if not self.phase_log:
            return "  (기록 없음)"
        return "\n".join(f"  {p}" for p in self.phase_log[-10:])

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
            if text == "상태":
                elapsed_min = int((time.time() - self.start_time) / 60)
                send_telegram(
                    f"<b>📊 상태 조회</b>\n"
                    f"총 실행: {elapsed_min}분\n"
                    f"마지막 출력: {int(time.time()-self.last_output_time)}초 전\n\n"
                    f"단계 기록:\n{self._phase_summary()}\n\n"
                    f"최근 출력:\n<pre>{self._safe_output(500)}</pre>"
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
                self.last_output_time = time.time()
            elif text == "중지":
                send_telegram("⛔ 중지 요청")
                self.running = False
            else:
                if self.process and self.process.poll() is None and self.process.stdin:
                    try:
                        self.process.stdin.write(text + "\n")
                        self.process.stdin.flush()
                        self.idle_notified = False
                        self.last_output_time = time.time()
                        send_telegram(f"✉️ 전달: <code>{text[:80]}</code>")
                    except Exception as e:
                        send_telegram(f"❌ 전달 실패: {e}")
                else:
                    send_telegram("⚠️ Claude 실행 중 아님")


def main():
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    master_path = os.path.join(project_dir, "SQM_무중단_작업지시서.md")
    if not os.path.exists(master_path):
        master_path = os.path.join(project_dir, "MASTER_FINAL_v868_통합완성본.md")
    if not os.path.exists(master_path):
        master_path = os.path.join(project_dir, "MASTER_FINAL_v867_통합완성본.md")
    if not os.path.exists(master_path):
        print(f"ERROR: MASTER 파일 없음")
        sys.exit(1)
    print(f"MASTER: {master_path}")
    bridge = TelegramBridge(master_path, project_dir)
    bridge.start()


if __name__ == "__main__":
    main()
```

---

## 5. 스크립트 설치 방법

새 프로젝트에서 사용 시:
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
```cmd
F:
cd "프로그램\Sqm 재고관리\Claude_SQM_v868"
run_master.bat
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
- Phase 1~7: 완료
- Phase 8: 진행 중

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

## 10. 오류 대응표

| 오류 | 해결 |
|---|---|
| ModuleNotFoundError: react_api | F: 드라이브 전환 후 cd 실행 |
| pdf_engine 로드 실패 | core/pdf_engine.py 확인 |
| Telegram 알림 없음 | .env BOT_TOKEN/CHAT_ID 확인 |
| FastAPI 502 | 포트 8000 FastAPI 실행 확인 |
| React 연결 거부 | npm run dev 실행 확인 |
| bridge not found | scripts/telegram_bridge.py 확인 |
