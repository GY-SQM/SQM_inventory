# -*- coding: utf-8 -*-
"""
Telegram Bridge v5
==================
기능:
  1. 5분마다 정기 상태 알림 (진행률 포함)
  2. yes/no 유형 대기 감지 + 사용자 응답
  3. 1/2/3 선택 유형 대기 감지 + 사용자 응답
  4. 자유 문장 지시 입력 → Claude 전달
  5. 무응답/idle 상태 감지 + 상세 알림
  6. 오류 메시지 감지 + Telegram 전파
  7. Phase 진행 자동 감지 + 기록
  8. 재시작 / 중지 명령 지원
  9. 단계 완료 즉시 알림 (완료N/전체49 진행률 바)
  10. completed_steps.txt 파싱으로 실시간 진행률 계산
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

# ── 전체 단계 정의 (49단계) ──────────────────────────────
TOTAL_STEPS = 49
ALL_STEPS = [
    "P0-S1","P0-S2","P0-S3","P0-S4","P0-S5","P0-S6","P0-S7","P0-S8",
    "P0-S9","P0-S10","P0-S11","P0-S12","P0-S13","P0-S14","P0-S15",
    "P1-S1","P1-S2","P1-S3","P1-S4","P1-S5","P1-S6","P1-S7","P1-S8",
    "P1-S9","P1-S10","P1-S11","P1-S12",
    "P2-S1","P2-S2","P2-S3","P2-S4","P2-S5","P2-S6",
    "P3-S1","P3-S2","P3-S3","P3-S4","P3-S5","P3-S6","P3-S7",
    "P4-S1","P4-S2","P4-S3","P4-S4","P4-S5","P4-S6","P4-S7","P4-S8","P4-S9",
]

def get_progress(logs_dir: str) -> dict:
    """completed_steps.txt 파싱 → 진행률 계산"""
    done_file = os.path.join(logs_dir, "completed_steps.txt")
    completed = []
    failed    = []
    current   = ""

    if os.path.exists(done_file):
        with open(done_file, encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                # 형식: P0-S2_구조준비_PASS_날짜_시간
                # 유연하게 인식: PASS 포함이면 완료
                for step in ALL_STEPS:
                    if line.startswith(step + "_") or line.startswith(step + " "):
                        line_upper = line.upper()
                        if "PASS" in line_upper or "완료" in line or "✅" in line:
                            if step not in completed:
                                completed.append(step)
                            current = step
                        elif "FAIL" in line_upper or "실패" in line:
                            if step not in failed:
                                failed.append(step)
                        break
                    # P4-S2 형식 없이 그냥 "P4-S2" 만 있는 경우도 인식
                    elif line.strip() == step:
                        if step not in completed:
                            completed.append(step)
                        current = step
                        break

    done_count = len(completed)
    pct        = int(done_count / TOTAL_STEPS * 100)
    filled     = pct // 5
    bar        = "█" * filled + "░" * (20 - filled)

    # 다음 단계
    next_step = ""
    for s in ALL_STEPS:
        if s not in completed and s not in failed:
            next_step = s
            break

    return {
        "completed":   completed,
        "failed":      failed,
        "done_count":  done_count,
        "total":       TOTAL_STEPS,
        "pct":         pct,
        "bar":         bar,
        "current":     current,
        "next_step":   next_step,
    }

def progress_msg(p: dict, title: str = "📊 진행 현황") -> str:
    """진행률 메시지 생성"""
    done  = p["done_count"]
    total = p["total"]
    pct   = p["pct"]
    bar   = p["bar"]

    lines = [
        f"<b>{title}</b>",
        f"─────────────────────",
        f"📈 진행률: {done}/{total}단계 ({pct}%)",
        f"[{bar}]",
    ]

    if p["current"]:
        lines.append(f"✅ 마지막 완료: {p['current']}")
    if p["next_step"]:
        lines.append(f"▶️ 다음 단계: {p['next_step']}")
    if p["failed"]:
        lines.append(f"❌ 실패: {', '.join(p['failed'][-3:])}")

    # 최근 완료 5개
    if p["completed"]:
        recent = p["completed"][-5:]
        lines.append(f"\n✅ 최근 완료:\n" + "\n".join(f"  {s}" for s in recent))

    return "\n".join(lines)

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



# ── SQM DB 직접 조회 함수 ─────────────────────────────────
import sqlite3

def _get_db_path(project_dir: str) -> str:
    """DB 경로 찾기 — config.py 참조 또는 기본 경로"""
    candidates = [
        os.path.join(project_dir, "data", "db", "sqm_inventory.db"),
        os.path.join(project_dir, "sqm_inventory.db"),
        os.path.join(project_dir, "core", "sqm_inventory.db"),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    # config.py에서 DB_PATH 읽기 시도
    try:
        import sys
        sys.path.insert(0, project_dir)
        from core.config import DB_PATH
        return DB_PATH
    except Exception:
        pass
    return ""

def sqm_dashboard(project_dir: str) -> str:
    """재고 현황 요약"""
    db_path = _get_db_path(project_dir)
    if not db_path:
        return "❌ DB 경로를 찾을 수 없습니다"
    try:
        conn = sqlite3.connect(db_path)
        cur  = conn.cursor()
        cur.execute("""
            SELECT status, COUNT(*) as cnt, ROUND(SUM(current_weight),1) as kg
            FROM inventory
            WHERE status NOT IN ('OUTBOUND', 'SOLD')
            GROUP BY status
            ORDER BY cnt DESC
        """)
        rows = cur.fetchall()
        conn.close()
        if not rows:
            return "재고 데이터 없음"
        lines = ["<b>📦 재고 현황 요약</b>", "─────────────────────"]
        total_cnt = total_kg = 0
        for status, cnt, kg in rows:
            kg = kg or 0
            lines.append(f"  {status}: {cnt}건 / {kg:,.1f}kg")
            total_cnt += cnt
            total_kg  += kg
        lines.append("─────────────────────")
        lines.append(f"  합계: {total_cnt}건 / {total_kg:,.1f}kg")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ DB 조회 오류: {e}"

def sqm_available(project_dir: str) -> str:
    """가용 재고 목록 (AVAILABLE 상태)"""
    db_path = _get_db_path(project_dir)
    if not db_path:
        return "❌ DB 경로를 찾을 수 없습니다"
    try:
        conn = sqlite3.connect(db_path)
        cur  = conn.cursor()
        cur.execute("""
            SELECT lot_no, product_name,
                   COUNT(*) as bags,
                   ROUND(SUM(current_weight),1) as kg
            FROM inventory
            WHERE status = 'AVAILABLE'
            GROUP BY lot_no, product_name
            ORDER BY lot_no DESC
            LIMIT 15
        """)
        rows = cur.fetchall()
        conn.close()
        if not rows:
            return "가용 재고 없음"
        lines = ["<b>✅ 가용 재고 (AVAILABLE)</b>", "─────────────────────"]
        for lot, prod, bags, kg in rows:
            prod = (prod or "")[:12]
            lines.append(f"  {lot} | {prod} | {bags}개/{kg:,.0f}kg")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ DB 조회 오류: {e}"

def sqm_inventory_by_product(project_dir: str) -> str:
    """제품별 재고 현황"""
    db_path = _get_db_path(project_dir)
    if not db_path:
        return "❌ DB 경로를 찾을 수 없습니다"
    try:
        conn = sqlite3.connect(db_path)
        cur  = conn.cursor()
        cur.execute("""
            SELECT product_name,
                   SUM(CASE WHEN status='AVAILABLE' THEN 1 ELSE 0 END) as avail,
                   SUM(CASE WHEN status='RESERVED'  THEN 1 ELSE 0 END) as resv,
                   SUM(CASE WHEN status='PICKED'    THEN 1 ELSE 0 END) as pick,
                   COUNT(*) as total,
                   ROUND(SUM(current_weight),1) as kg
            FROM inventory
            WHERE status NOT IN ('OUTBOUND','SOLD')
            GROUP BY product_name
            ORDER BY total DESC
            LIMIT 10
        """)
        rows = cur.fetchall()
        conn.close()
        if not rows:
            return "재고 없음"
        lines = ["<b>📋 제품별 재고 현황</b>",
                 "제품명 | 가용/예약/피킹 | 합계(kg)"]
        lines.append("─────────────────────")
        for prod, avail, resv, pick, total, kg in rows:
            prod = (prod or "미지정")[:14]
            lines.append(
                f"{prod}\n"
                f"  ✅{avail} 🔒{resv} 📦{pick} | {kg:,.0f}kg"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"❌ DB 조회 오류: {e}"

def sqm_lot_detail(project_dir: str, lot_no: str) -> str:
    """LOT 상세 조회"""
    db_path = _get_db_path(project_dir)
    if not db_path:
        return "❌ DB 경로를 찾을 수 없습니다"
    try:
        conn = sqlite3.connect(db_path)
        cur  = conn.cursor()
        # LOT 기본 정보
        cur.execute("""
            SELECT lot_no, product_name, status,
                   COUNT(*) as bags,
                   ROUND(SUM(current_weight),1) as kg,
                   ROUND(SUM(initial_weight),1) as init_kg,
                   MIN(location) as loc
            FROM inventory
            WHERE lot_no = ?
            GROUP BY lot_no, product_name, status
        """, (lot_no,))
        rows = cur.fetchall()
        conn.close()
        if not rows:
            return f"❌ LOT {lot_no} 없음"
        lines = [f"<b>🔍 LOT {lot_no}</b>", "─────────────────────"]
        for lot, prod, status, bags, kg, init_kg, loc in rows:
            lines.append(
                f"제품: {prod or '?'}\n"
                f"상태: {status} | {bags}개 | {kg:,.1f}kg\n"
                f"초기중량: {init_kg:,.1f}kg | 위치: {loc or '?'}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"❌ DB 조회 오류: {e}"

def sqm_api_status(project_dir: str) -> str:
    """FastAPI 서버 상태 확인"""
    try:
        import urllib.request
        urls = ["http://localhost:8000/docs", "http://localhost:8000/api/health"]
        for url in urls:
            try:
                req = urllib.request.urlopen(url, timeout=3)
                if req.status == 200:
                    return f"✅ FastAPI 서버 정상 ({url})"
            except Exception:
                continue
        return "❌ FastAPI 서버 응답 없음 (localhost:8000)"
    except Exception as e:
        return f"❌ API 상태 확인 오류: {e}"


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
        self.logs_dir         = os.path.join(project_dir, 'logs')
        self.last_done_count  = 0   # 이전 완료 단계 수 (즉시 알림용)

    def start(self):
        logger.info("=" * 50)
        logger.info("Telegram Bridge v4 시작")

        p = get_progress(self.logs_dir)
        send_telegram(
            "<b>🚀 SQM Telegram Bridge v5 시작</b>\n"
            f"시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"MASTER: {os.path.basename(self.master_path)}\n"
            f"전체 {TOTAL_STEPS}단계 | 5분 정기 보고\n\n"
            "<b>📋 주요 명령어:</b>\n"
            "  /help    전체 명령어 목록\n"
            "  /status  현재 상태 + 진행률\n"
            "  /phase   Phase 진행 현황\n"
            "  /progress 진행률 막대\n"
            "  /dash    재고 현황 요약\n"
            "  /lot 번호 LOT 상세 조회\n"
            "  /restart Claude 재시작\n"
            "  /stop    전체 종료\n\n"
            "<b>⚡ 자동 알림:</b>\n"
            "  단계 완료 즉시 알림\n"
            "  5분마다 진행률 보고\n"
            "  오류 발생 즉시 알림\n"
            "  무응답 2분 → 알림"
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
                    p_final = get_progress(self.logs_dir)
                    send_telegram(
                        f"<b>{'✅ Claude 완료!' if exit_code == 0 else '❌ 비정상 종료'}</b>\n"
                        f"종료 코드: {exit_code}\n"
                        f"총 실행: {elapsed_min}분\n"
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
                            f"<b>오류 내용:</b>\n"
                            f"<pre>{self._safe_output(600)}</pre>\n\n"
                            "진행 → 무시하고 계속\n"
                            "재시작 → Claude 재시작\n"
                            "중지 → 전체 종료"
                        )

                    else:
                        self.wait_type = 'normal'

                self._check_telegram()

                # 5분 정기 알림 (진행률 포함)
                if time.time() - self.last_status_time >= STATUS_INTERVAL:
                    elapsed_min = int((time.time() - self.start_time) / 60)
                    idle_sec    = int(time.time() - self.last_output_time)
                    p = get_progress(self.logs_dir)
                    send_telegram(
                        f"<b>📊 5분 정기 보고</b> | {datetime.now().strftime('%H:%M:%S')}\n"
                        f"─────────────────────\n"
                        f"⏱️ 총 실행: {elapsed_min}분 | 오류: {self.error_count}회\n"
                        f"현재 상태: {self._wait_type_label()}\n\n"
                        + progress_msg(p) + "\n\n"
                        f"최근 출력:\n<pre>{self._safe_output(300)}</pre>"
                    )
                    self.last_status_time = time.time()

                # 단계 완료 즉시 알림 (completed_steps.txt 변화 감지)
                p_now = get_progress(self.logs_dir)
                if p_now["done_count"] > self.last_done_count:
                    self.last_done_count = p_now["done_count"]
                    send_telegram(
                        f"<b>✅ 단계 완료!</b>\n"
                        + progress_msg(p_now, "📈 현재 진행률")
                    )

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

                try:
                    time.sleep(POLL_INTERVAL)
                except (EOFError, StopIteration):
                    logger.warning("sleep 중 EOF — 무시")
                    continue

        except KeyboardInterrupt:
            logger.info("Ctrl+C 감지 — 종료 확인 중...")
            send_telegram("⚠️ Ctrl+C 감지\n정말 종료하시겠습니까?\ny → 종료 | n → 계속")
            # 10초 대기 후 Telegram 응답 확인
            for _ in range(5):
                time.sleep(2)
                updates = get_telegram_updates(self.update_offset)
                for update in updates:
                    self.update_offset = update["update_id"] + 1
                    msg_text = update.get("message", {}).get("text", "").strip().lower()
                    if msg_text in ['y', 'yes']:
                        send_telegram("⛔ 종료 확인. Bridge 종료합니다.")
                        self.running = False
                        return
                    elif msg_text in ['n', 'no']:
                        send_telegram("✅ 종료 취소. 계속 진행합니다.")
                        # 재시작
                        self._start_claude()
                        reader_thread = threading.Thread(
                            target=enqueue_output,
                            args=(self.process.stdout, self.output_queue),
                            daemon=True
                        )
                        reader_thread.start()
                        return
            send_telegram("⛔ 응답 없음. 자동 종료합니다.")
        except (EOFError, StopIteration):
            # 엔터 두 번 등 stdin EOF 무시 — 계속 실행
            logger.warning("EOF 감지 — 무시하고 계속 실행")
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
            self.master_content = f.read()

        # 새 창으로 실행 — 기동님이 화면에서 직접 확인 가능
        # Bridge는 별도 프로세스로 claude 출력을 모니터링
        CLAUDE = r"C:\Users\남기동\.local\bin\claude.exe"
        cmd = [CLAUDE, "--dangerously-skip-permissions"]
        logger.info(f"Claude 새 창 시작: MASTER {len(self.master_content)}자 전달 예정")
        try:
            import platform
            if platform.system() == "Windows":
                # Windows: cmd.exe 통해 새 창으로 실행
                CLAUDE = r"C:\Users\남기동\.local\bin\claude.exe"
                cmd = [
                    "cmd.exe", "/c", "start", "Claude Code",
                    "cmd.exe", "/k",
                    CLAUDE + " --dangerously-skip-permissions"
                ]
                # Bridge용 프로세스는 별도로 stdin PIPE 연결
                bridge_cmd = [CLAUDE, "--dangerously-skip-permissions"]
                self.process = subprocess.Popen(
                    bridge_cmd, cwd=self.project_dir,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    encoding='utf-8',
                    errors='replace',
                )
                # 화면 표시용 새 cmd 창 실행
                subprocess.Popen(cmd, cwd=self.project_dir)
            else:
                self.process = subprocess.Popen(
                    cmd, cwd=self.project_dir,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    encoding='utf-8',
                    errors='replace',
                )
            # MASTER 내용 전달
            time.sleep(2)
            try:
                self.process.stdin.write(self.master_content + "\n")
                self.process.stdin.flush()
                logger.info("MASTER 내용 전달 완료")
            except Exception as e:
                logger.error(f"MASTER 전달 실패: {e}")
            send_telegram(
                f"✅ Claude 새 창으로 시작!\n"
                f"PID: {self.process.pid}\n"
                f"화면에서 Claude Code 창을 확인하세요"
            )
        except FileNotFoundError:
            send_telegram(f"❌ claude.exe 없음: {CLAUDE}")
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
        """Claude stdin 에 직접 전달 (대화형 모드 — 컨텍스트 유지)."""
        if not (self.process and self.process.poll() is None):
            send_telegram("⚠️ Claude 실행 중 아님")
            return
        try:
            self.process.stdin.write(text + "\n")
            self.process.stdin.flush()
            self.idle_notified = False
            self.wait_type = 'normal'
            self.last_output_time = time.time()
            send_telegram(f"✉️ Claude 전달 완료: <code>{text[:80]}</code>")
        except Exception as e:
            send_telegram(f"❌ 전달 실패: {e}")

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

            cmd = text.strip()
            cmd_lower = cmd.lower()

            # ── Level 1: Bridge 제어 명령 ──────────────────────
            if cmd in ["/help", "도움말"]:
                send_telegram(
                    "<b>📋 전체 명령어 목록</b>\n"
                    "─────────────────────\n"
                    "<b>[Level 1] Bridge 제어</b>\n"
                    "  /help    전체 명령어 목록\n"
                    "  /status  현재 상태 + 진행률\n"
                    "  /log     최근 로그 10줄\n"
                    "  /error   오류 목록\n"
                    "  /phase   Phase 진행 현황\n"
                    "  /progress 진행률 막대\n"
                    "  /restart Claude 재시작\n"
                    "  /stop    전체 종료\n\n"
                    "<b>[Level 2] SQM 업무 조회</b>\n"
                    "  /dash    Dashboard 재고 요약\n"
                    "  /inv     제품별 재고 현황\n"
                    "  /avail   가용 재고 목록\n"
                    "  /lot 번호 LOT 상세 조회\n"
                    "  /api     API 서버 상태\n\n"
                    "<b>[응답 명령]</b>\n"
                    "  y / n    확인/취소\n"
                    "  1/2/3    선택\n"
                    "  자유문장 → Claude 에 직접 전달"
                )

            elif cmd in ["/status", "상태"]:
                elapsed_min = int((time.time() - self.start_time) / 60)
                p = get_progress(self.logs_dir)
                send_telegram(
                    f"<b>📊 상태 조회</b> | {datetime.now().strftime('%H:%M:%S')}\n"
                    f"⏱️ 총 실행: {elapsed_min}분 | 오류: {self.error_count}회\n"
                    f"현재 상태: {self._wait_type_label()}\n"
                    f"마지막 출력: {int(time.time()-self.last_output_time)}초 전\n\n"
                    + progress_msg(p) + "\n\n"
                    f"최근 10줄:\n<pre>{self._safe_lines(10)}</pre>"
                )

            elif cmd in ["/log"]:
                send_telegram(
                    f"<b>📝 최근 로그 10줄</b>\n"
                    f"<pre>{self._safe_lines(10)}</pre>"
                )

            elif cmd in ["/error"]:
                if self.error_count == 0:
                    send_telegram("✅ 오류 없음")
                else:
                    send_telegram(
                        f"<b>🚨 오류 현황</b>\n"
                        f"총 {self.error_count}회 발생\n\n"
                        f"최근 출력:\n<pre>{self._safe_output(500)}</pre>"
                    )

            elif cmd in ["/phase"]:
                p = get_progress(self.logs_dir)
                phase_counts = {"P0":0,"P1":0,"P2":0,"P3":0,"P4":0}
                phase_total  = {"P0":15,"P1":12,"P2":6,"P3":7,"P4":9}
                for s in p["completed"]:
                    ph = s[:2]
                    if ph in phase_counts:
                        phase_counts[ph] += 1
                lines = ["<b>📌 Phase 진행 현황</b>","─────────────────────"]
                for ph in ["P0","P1","P2","P3","P4"]:
                    done  = phase_counts[ph]
                    total = phase_total[ph]
                    icon  = "✅" if done == total else ("🔄" if done > 0 else "⬜")
                    lines.append(f"  {icon} {ph}: {done}/{total}단계")
                send_telegram("\n".join(lines))

            elif cmd in ["/progress"]:
                p = get_progress(self.logs_dir)
                send_telegram(progress_msg(p, "📈 전체 진행률"))

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
                reader_thread = threading.Thread(
                    target=enqueue_output,
                    args=(self.process.stdout, self.output_queue),
                    daemon=True
                )
                reader_thread.start()
                self.idle_notified = False
                self.wait_type = 'normal'
                self.last_output_time = time.time()

            elif cmd in ["/stop", "중지"]:
                send_telegram("⛔ 중지 요청. 종료합니다.")
                self.running = False

            # ── Level 2: SQM 업무 조회 명령 ────────────────────
            elif cmd in ["/dash"]:
                send_telegram(sqm_dashboard(self.project_dir))

            elif cmd in ["/inv"]:
                send_telegram(sqm_inventory_by_product(self.project_dir))

            elif cmd in ["/avail"]:
                send_telegram(sqm_available(self.project_dir))

            elif cmd_lower.startswith("/lot "):
                lot_no = cmd[5:].strip()
                if lot_no:
                    send_telegram(sqm_lot_detail(self.project_dir, lot_no))
                else:
                    send_telegram("사용법: /lot LOT번호\n예) /lot 250401001")

            elif cmd in ["/api"]:
                send_telegram(sqm_api_status(self.project_dir))

            # ── 응답 명령 (y/n, 1/2/3, 자유문장) ───────────────
            else:
                is_simple = cmd_lower in [
                    'y', 'n', 'yes', 'no',
                    '1', '2', '3',
                    '진행', '계속'
                ]

                if not is_simple:
                    idle_sec = int(time.time() - self.last_output_time)
                    send_telegram(
                        f"<b>📋 전달 전 현재 상태</b>\n"
                        f"현재 상태: {self._wait_type_label()}\n"
                        f"마지막 출력: {idle_sec}초 전\n\n"
                        f"<b>최근 출력:</b>\n"
                        f"<pre>{self._safe_lines(5)}</pre>\n\n"
                        f"<b>전달할 내용:</b>\n"
                        f"<code>{cmd[:200]}</code>\n\n"
                        f"y → 전달 | n → 취소"
                    )
                    self._pending_text = cmd
                    self._pending_confirm = True
                    continue

                self._send_to_claude(cmd)


def main():
    # project_dir: scripts/ 의 한 단계 위 = 프로젝트 루트
    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # 커맨드라인 인자로 MASTER 파일 경로 직접 지정 가능
    # 예: python scripts\telegram_bridge.py MASTER_FINAL_v868_통합완성본.md
    if len(sys.argv) >= 2:
        arg_path = sys.argv[1]
        # 절대경로 or 루트 기준 상대경로
        if os.path.isabs(arg_path):
            master_path = arg_path
        else:
            master_path = os.path.join(project_dir, arg_path)
        if not os.path.exists(master_path):
            print(f"ERROR: 지정한 MASTER 파일 없음: {master_path}")
            sys.exit(1)
    else:
        # 자동 탐색 순서
        candidates = [
            "MASTER_FINAL_v868_통합완성본.md",
            "SQM_무중단_작업지시서.md",
            "MASTER_FINAL_v867_통합완성본.md",
        ]
        master_path = None
        for name in candidates:
            path = os.path.join(project_dir, name)
            if os.path.exists(path):
                master_path = path
                break
        if not master_path:
            print(f"ERROR: MASTER 파일 없음")
            print(f"탐색 경로: {project_dir}")
            print(f"찾은 파일: {os.listdir(project_dir)[:10]}")
            sys.exit(1)

    print(f"프로젝트 루트: {project_dir}")
    print(f"MASTER 파일:  {master_path}")
    bridge = TelegramBridge(master_path, project_dir)
    bridge.start()


if __name__ == "__main__":
    main()
