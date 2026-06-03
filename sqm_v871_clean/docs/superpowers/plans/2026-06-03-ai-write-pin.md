# AI 채팅 수정 모드 PIN + 롤백 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** AI 채팅에서 PIN 인증 후 SQLite UPDATE 실행을 허용하고, 모든 변경을 ai_edit_log에 기록해 자연어 롤백을 지원한다.

**Architecture:** 백엔드에 인메모리 세션 + PIN 해시 파일을 추가하고, GeminiChatQuery에 write_mode 분기를 추가한다. 프론트엔드 ai_chat.html에 🔒 버튼과 PIN 팝업을 추가한다.

**Tech Stack:** FastAPI, SQLite, Python hashlib(pbkdf2_hmac), 순수 HTML/CSS/JS

---

## 파일 구조

| 파일 | 역할 |
|---|---|
| `backend/api/ai_write_session.py` | **신규** — PIN 검증, 세션 토큰 관리, ai_edit_log 초기화 |
| `backend/api/ai_gemini.py` | **수정** — 신규 엔드포인트 4개 추가, /chat에 write_session_token 처리 |
| `features/ai/gemini_chat_query.py` | **수정** — write_mode 분기, UPDATE SQL 생성, ai_edit_log 기록, 롤백 처리 |
| `frontend/detached/ai_chat.html` | **수정** — 🔒 버튼, PIN 팝업, 세션 카운트다운, write_session_token 전송 |
| `data/ai_write_config.json` | **신규** — PIN 해시 + 세션 시간 설정 (앱 첫 실행 시 자동 생성) |

---

## Task 1: ai_write_session.py — PIN + 세션 모듈 생성

**Files:**
- Create: `backend/api/ai_write_session.py`

- [ ] **Step 1: 파일 생성**

```python
"""
AI 수정 모드 — PIN 검증 + 인메모리 세션 관리
"""
import os
import json
import hashlib
import secrets
import time
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ── 경로 설정 ──────────────────────────────────────────────────
def _project_root() -> Path:
    here = Path(__file__).resolve().parent
    return here.parent.parent

def _config_path() -> Path:
    return _project_root() / "data" / "ai_write_config.json"

def _db_path() -> str:
    return str(_project_root() / "data" / "db" / "sqm_inventory.db")

# ── 기본 PIN = "0000" ─────────────────────────────────────────
DEFAULT_PIN = "0000"

# ── 인메모리 세션 ─────────────────────────────────────────────
_sessions: dict[str, float] = {}   # token → 만료 timestamp
_fail_count: int = 0               # 연속 실패 횟수
_fail_lockout_until: float = 0     # 잠금 해제 timestamp


# ── config 로드/저장 ──────────────────────────────────────────
def _load_config() -> dict:
    path = _config_path()
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    # 기본값으로 초기화
    cfg = {
        "pin_hash": _hash_pin(DEFAULT_PIN),
        "session_minutes": 10
    }
    _save_config(cfg)
    return cfg

def _save_config(cfg: dict) -> None:
    path = _config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")


# ── PIN 해시 (pbkdf2_hmac, 표준 라이브러리) ───────────────────
def _hash_pin(pin: str) -> str:
    """PIN → 'salt$hash' 형식 문자열 반환."""
    salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", pin.encode(), salt.encode(), 200_000)
    return f"{salt}${h.hex()}"

def _verify_pin(pin: str, stored: str) -> bool:
    """저장된 'salt$hash' 형식과 비교."""
    try:
        salt, h_hex = stored.split("$", 1)
        h = hashlib.pbkdf2_hmac("sha256", pin.encode(), salt.encode(), 200_000)
        return h.hex() == h_hex
    except Exception:
        return False


# ── 공개 인터페이스 ───────────────────────────────────────────
def check_pin(pin: str) -> tuple[bool, str]:
    """
    PIN 검증.
    Returns: (success, message)
    실패 3회 → 30초 잠금.
    """
    global _fail_count, _fail_lockout_until

    # 잠금 확인
    if time.time() < _fail_lockout_until:
        remaining = int(_fail_lockout_until - time.time())
        return False, f"너무 많이 실패했습니다. {remaining}초 후 다시 시도하세요."

    cfg = _load_config()
    if _verify_pin(pin, cfg["pin_hash"]):
        _fail_count = 0
        return True, "인증 성공"
    else:
        _fail_count += 1
        if _fail_count >= 3:
            _fail_lockout_until = time.time() + 30
            _fail_count = 0
            return False, "PIN이 3회 틀렸습니다. 30초 후 다시 시도하세요."
        return False, f"PIN이 올바르지 않습니다. ({_fail_count}/3)"


def create_session() -> str:
    """세션 토큰 발급. 기존 세션은 무효화."""
    global _sessions
    cfg = _load_config()
    minutes = cfg.get("session_minutes", 10)
    token = secrets.token_urlsafe(32)
    # 기존 세션 전부 만료 (동시 세션 1개만)
    _sessions.clear()
    _sessions[token] = time.time() + (minutes * 60)
    return token


def validate_session(token: str) -> bool:
    """토큰이 유효하고 만료되지 않았으면 True."""
    if not token or token not in _sessions:
        return False
    if time.time() > _sessions[token]:
        del _sessions[token]
        return False
    return True


def revoke_session(token: str) -> None:
    """세션 즉시 무효화."""
    _sessions.pop(token, None)


def get_session_remaining(token: str) -> int:
    """남은 초 반환. 유효하지 않으면 0."""
    if token not in _sessions:
        return 0
    remaining = int(_sessions[token] - time.time())
    return max(0, remaining)


def change_pin(current_pin: str, new_pin: str) -> tuple[bool, str]:
    """PIN 변경. current_pin 검증 후 new_pin 저장."""
    success, msg = check_pin(current_pin)
    if not success:
        return False, msg
    if not new_pin or len(new_pin) < 4:
        return False, "새 PIN은 4자리 이상이어야 합니다."
    cfg = _load_config()
    cfg["pin_hash"] = _hash_pin(new_pin)
    _save_config(cfg)
    return True, "PIN이 변경됐습니다."


# ── ai_edit_log 테이블 초기화 ─────────────────────────────────
def ensure_edit_log_table() -> None:
    """ai_edit_log 테이블이 없으면 생성."""
    import sqlite3
    try:
        con = sqlite3.connect(_db_path())
        con.execute("""
            CREATE TABLE IF NOT EXISTS ai_edit_log (
              id          INTEGER PRIMARY KEY AUTOINCREMENT,
              table_name  TEXT    NOT NULL,
              record_id   INTEGER NOT NULL,
              field_name  TEXT    NOT NULL,
              old_value   TEXT,
              new_value   TEXT,
              sql_used    TEXT,
              changed_at  TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
              rolled_back INTEGER DEFAULT 0
            )
        """)
        con.commit()
        con.close()
    except Exception as e:
        logger.warning(f"ai_edit_log 테이블 생성 실패: {e}")
```

- [ ] **Step 2: 테이블 생성 확인**

```powershell
cd D:\program\SQM_inventory\sqm_v871_clean
python -c "
import sys; sys.path.insert(0,'.')
from backend.api.ai_write_session import ensure_edit_log_table
ensure_edit_log_table()
print('OK')
"
```

Expected: `OK`

- [ ] **Step 3: PIN 검증 확인**

```powershell
python -c "
import sys; sys.path.insert(0,'.')
from backend.api.ai_write_session import check_pin, create_session, validate_session
ok, msg = check_pin('0000')
print('PIN check:', ok, msg)
tok = create_session()
print('session valid:', validate_session(tok))
print('invalid token:', validate_session('bad'))
"
```

Expected:
```
PIN check: True 인증 성공
session valid: True
invalid token: False
```

- [ ] **Step 4: 커밋**

```powershell
cd D:\program\SQM_inventory
git add sqm_v871_clean/backend/api/ai_write_session.py
git commit -m "feat(ai): PIN + 세션 관리 모듈 추가"
```

---

## Task 2: ai_gemini.py — 신규 엔드포인트 4개 추가

**Files:**
- Modify: `backend/api/ai_gemini.py` (301번 줄 이후에 추가)

- [ ] **Step 1: ChatPayload 스키마에 write_session_token 필드 추가**

파일 `backend/api/ai_gemini.py` 에서 `class ChatPayload` 블록을 찾아 교체:

Old:
```python
class ChatPayload(BaseModel):
    message: str
```

New:
```python
class ChatPayload(BaseModel):
    message: str
    write_session_token: str = ""
```

- [ ] **Step 2: 신규 스키마 추가 (ChatPayload 아래)**

`class TogglePayload` 바로 위에 추가:

```python
class PinUnlockPayload(BaseModel):
    pin: str

class PinChangePayload(BaseModel):
    current_pin: str
    new_pin: str
```

- [ ] **Step 3: 신규 엔드포인트 4개 추가 (파일 맨 끝에 추가)**

```python
# ── AI 수정 모드 PIN 관리 ───────────────────────────────────────
@router.post("/write-unlock", summary="🔐 수정 모드 잠금 해제")
def write_unlock(payload: PinUnlockPayload):
    from backend.api.ai_write_session import check_pin, create_session, ensure_edit_log_table
    ensure_edit_log_table()
    success, msg = check_pin(payload.pin)
    if not success:
        raise HTTPException(401, msg)
    token = create_session()
    return {"success": True, "token": token, "message": "수정 모드가 활성화됐습니다."}


@router.post("/write-lock", summary="🔒 수정 모드 잠금")
def write_lock(payload: dict = {}):
    from backend.api.ai_write_session import _sessions
    _sessions.clear()
    return {"success": True, "message": "수정 모드가 잠겼습니다."}


@router.get("/write-status", summary="🔓 수정 모드 상태 조회")
def write_status(token: str = ""):
    from backend.api.ai_write_session import validate_session, get_session_remaining
    valid = validate_session(token)
    remaining = get_session_remaining(token) if valid else 0
    return {"active": valid, "remaining_seconds": remaining}


@router.post("/pin/change", summary="🔑 PIN 변경")
def change_pin_endpoint(payload: PinChangePayload):
    from backend.api.ai_write_session import change_pin
    success, msg = change_pin(payload.current_pin, payload.new_pin)
    if not success:
        raise HTTPException(400, msg)
    return {"success": True, "message": msg}
```

- [ ] **Step 4: /chat 엔드포인트에 write_mode 처리 추가**

`chat_message` 함수 내 `chat = _get_chat_singleton(...)` 줄 아래에 추가:

Old:
```python
    try:
        chat = _get_chat_singleton(db_path, key or "")
        result = chat.ask(payload.message.strip())
```

New:
```python
    try:
        from backend.api.ai_write_session import validate_session
        write_mode = validate_session(payload.write_session_token or "")
        chat = _get_chat_singleton(db_path, key or "")
        result = chat.ask(payload.message.strip(), write_mode=write_mode)
```

- [ ] **Step 5: 백엔드 재시작 후 엔드포인트 확인**

```powershell
# 백엔드 포트 확인 (보통 8000)
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/ai/write-status?token=bad" -Method GET
```

Expected: `{"active":false,"remaining_seconds":0}`

- [ ] **Step 6: 커밋**

```powershell
cd D:\program\SQM_inventory
git add sqm_v871_clean/backend/api/ai_gemini.py
git commit -m "feat(ai): 수정 모드 엔드포인트 4개 추가 + /chat write_mode 연결"
```

---

## Task 3: gemini_chat_query.py — write_mode + 롤백 지원

**Files:**
- Modify: `features/ai/gemini_chat_query.py`

- [ ] **Step 1: ask() 메서드에 write_mode 파라미터 추가**

`def ask(self, question: str)` → `def ask(self, question: str, write_mode: bool = False):`

해당 줄을 찾아 교체:

Old:
```python
    def ask(self, question: str) -> dict:
```

New:
```python
    def ask(self, question: str, write_mode: bool = False) -> dict:
```

- [ ] **Step 2: ask() 내부에 write_mode 분기 추가**

`result = self._execute_query(intent, question)` 줄 앞에 추가:

Old:
```python
        # 2. SQL 생성 및 실행
        result = self._execute_query(intent, question)
```

New:
```python
        # 2. SQL 생성 및 실행
        if write_mode and self._is_write_intent(question):
            result = self._execute_write_command(question)
        elif write_mode and self._is_rollback_intent(question):
            result = self._execute_rollback(question)
        else:
            result = self._execute_query(intent, question)
```

- [ ] **Step 3: 롤백 의도 감지 메서드 추가**

클래스 맨 끝에 추가:

```python
    @staticmethod
    def _is_write_intent(question: str) -> bool:
        """UPDATE 의도 키워드 감지."""
        keywords = ["변경", "수정", "바꿔", "바꿔줘", "업데이트", "고쳐", "변경해줘",
                    "수정해줘", "바꿔주세요", "변경해주세요", "수정해주세요"]
        q = question.strip()
        return any(kw in q for kw in keywords)

    @staticmethod
    def _is_rollback_intent(question: str) -> bool:
        """롤백/취소 의도 키워드 감지."""
        keywords = ["취소", "롤백", "되돌려", "원래대로", "취소해줘", "롤백해줘",
                    "변경 이력", "수정 이력", "이력 보여줘"]
        q = question.strip()
        return any(kw in q for kw in keywords)
```

- [ ] **Step 4: _execute_write_command() 메서드 추가**

```python
    def _execute_write_command(self, question: str) -> "QueryResult":
        """Gemini로 UPDATE SQL 생성 후 ai_edit_log에 기록하고 실행."""
        import sqlite3
        from datetime import datetime

        schema = self._build_full_schema()
        prompt = (
            "당신은 SQLite 데이터 수정 전문가입니다. 아래 [스키마]에 존재하는 테이블/컬럼만 사용해 "
            "[질문]에 맞는 UPDATE 문 1개를 작성하세요.\n"
            "규칙:\n"
            "- 반드시 UPDATE 문 1개만. SELECT/INSERT/DELETE/DROP/ALTER 절대 금지.\n"
            "- 반드시 WHERE 절 포함 (WHERE 없는 전체 UPDATE 금지).\n"
            "- 스키마에 없는 테이블/컬럼 사용 금지.\n"
            "- 설명/주석/코드펜스 없이 SQL 본문만 출력.\n\n"
            f"[스키마]\n{schema}\n\n[질문]\n{question}\n\n[UPDATE SQL]"
        )
        try:
            from features.ai.gemini_utils import call_gemini_safe
            resp = call_gemini_safe(self.client, self.model_name, prompt, timeout=30)
            sql_text = resp.text if resp else None
        except Exception as e:
            return QueryResult(False, "AI_수정", "", [], [], 0,
                               f"SQL 생성 실패: {e}", "write_gen_failed")

        if not sql_text:
            return QueryResult(False, "AI_수정", "", [], [], 0,
                               "수정 SQL을 생성하지 못했습니다. 더 구체적으로 입력해 주세요.",
                               "write_gen_empty")

        # UPDATE 문인지 검증
        sql_clean = sql_text.strip().strip("```").strip()
        if not sql_clean.upper().startswith("UPDATE"):
            return QueryResult(False, "AI_수정", "", [], [], 0,
                               f"안전하지 않은 SQL이 생성됐습니다: {sql_clean[:80]}",
                               "write_unsafe")

        # WHERE 절 필수 검증
        if " WHERE " not in sql_clean.upper():
            return QueryResult(False, "AI_수정", "", [], [], 0,
                               "WHERE 조건이 없는 전체 수정은 허용되지 않습니다.",
                               "write_no_where")

        try:
            con = sqlite3.connect(self.db_path)
            con.row_factory = sqlite3.Row

            # 변경 전 값 조회 (롤백용)
            self._log_before_update(con, sql_clean, question)

            cur = con.execute(sql_clean)
            affected = cur.rowcount
            con.commit()
            con.close()

            return QueryResult(True, "AI_수정", sql_clean, [], [], affected,
                               f"✅ {affected}건이 수정됐습니다.\n"
                               f"취소하려면: '방금 변경 취소해줘'",
                               None)
        except Exception as e:
            return QueryResult(False, "AI_수정", sql_clean, [], [], 0,
                               f"수정 실패: {e}", "write_exec_failed")
```

- [ ] **Step 5: _log_before_update() 메서드 추가**

```python
    def _log_before_update(self, con, update_sql: str, question: str) -> None:
        """UPDATE 실행 전 변경 대상 레코드의 현재 값을 ai_edit_log에 기록."""
        import re
        from datetime import datetime

        # UPDATE table_name SET col=val WHERE ...  → table, where절 파싱
        m = re.match(
            r"UPDATE\s+(\w+)\s+SET\s+(.+?)\s+WHERE\s+(.+)",
            update_sql.strip(), re.IGNORECASE | re.DOTALL
        )
        if not m:
            return

        table_name = m.group(1)
        set_clause = m.group(2)
        where_clause = m.group(3).split(";")[0]

        # SET 절에서 컬럼명 추출
        set_pairs = [p.strip() for p in re.split(r",(?![^()]*\))", set_clause)]
        field_names = [p.split("=")[0].strip() for p in set_pairs if "=" in p]

        try:
            # 변경 전 값 조회
            select_sql = f"SELECT rowid, {', '.join(field_names)} FROM {table_name} WHERE {where_clause}"
            rows = con.execute(select_sql).fetchall()
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            for row in rows:
                record_id = row[0]
                for i, field in enumerate(field_names):
                    old_val = str(row[i + 1]) if row[i + 1] is not None else None
                    # 새 값 파싱
                    new_val = None
                    for pair in set_pairs:
                        parts = pair.split("=", 1)
                        if parts[0].strip().lower() == field.lower() and len(parts) > 1:
                            new_val = parts[1].strip().strip("'\"")
                    con.execute("""
                        INSERT INTO ai_edit_log
                          (table_name, record_id, field_name, old_value, new_value, sql_used, changed_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (table_name, record_id, field, old_val, new_val, update_sql, now))
        except Exception as e:
            logger.warning(f"ai_edit_log 기록 실패 (무시): {e}")
```

- [ ] **Step 6: _execute_rollback() 메서드 추가**

```python
    def _execute_rollback(self, question: str) -> "QueryResult":
        """ai_edit_log 기반 롤백 실행."""
        import sqlite3, re
        from datetime import datetime

        con = sqlite3.connect(self.db_path)

        # "이력 보여줘" 처리
        if any(kw in question for kw in ["이력", "목록", "보여줘", "조회"]):
            rows = con.execute("""
                SELECT id, table_name, field_name, old_value, new_value, changed_at, rolled_back
                FROM ai_edit_log ORDER BY id DESC LIMIT 20
            """).fetchall()
            con.close()
            if not rows:
                return QueryResult(True, "AI_이력조회", "", [], [], 0, "변경 이력이 없습니다.", None)
            lines = ["변경 이력 (최근 20건):"]
            for r in rows:
                status = "↩️ 롤백됨" if r[6] else "✅ 유효"
                lines.append(f"#{r[0]} [{r[5]}] {r[1]}.{r[2]}: {r[3]} → {r[4]} {status}")
            return QueryResult(True, "AI_이력조회", "", [], [], len(rows), "\n".join(lines), None)

        # 롤백 건수 파싱 (기본 1건)
        count = 1
        m = re.search(r"(\d+)\s*건", question)
        if m:
            count = min(int(m.group(1)), 50)

        # 날짜 기준 롤백
        date_m = re.search(r"(\d{4}-\d{2}-\d{2})", question)
        if date_m:
            target_date = date_m.group(1)
            rows = con.execute("""
                SELECT id, table_name, record_id, field_name, old_value, sql_used
                FROM ai_edit_log
                WHERE rolled_back=0 AND changed_at LIKE ?
                ORDER BY id DESC
            """, (f"{target_date}%",)).fetchall()
        else:
            rows = con.execute("""
                SELECT id, table_name, record_id, field_name, old_value, sql_used
                FROM ai_edit_log
                WHERE rolled_back=0
                ORDER BY id DESC LIMIT ?
            """, (count,)).fetchall()

        if not rows:
            con.close()
            return QueryResult(True, "AI_롤백", "", [], [], 0,
                               "롤백할 변경 이력이 없습니다.", None)

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        rolled = 0
        msgs = []
        for row in rows:
            log_id, tbl, rec_id, field, old_val, _ = row
            try:
                rollback_sql = f"UPDATE {tbl} SET {field}=? WHERE rowid=?"
                con.execute(rollback_sql, (old_val, rec_id))
                con.execute("UPDATE ai_edit_log SET rolled_back=1 WHERE id=?", (log_id,))
                # 롤백 자체도 로그
                con.execute("""
                    INSERT INTO ai_edit_log
                      (table_name, record_id, field_name, old_value, new_value, sql_used, changed_at)
                    VALUES (?, ?, ?, '[ROLLBACK]', ?, ?, ?)
                """, (tbl, rec_id, field, old_val, rollback_sql, now))
                msgs.append(f"#{log_id} {tbl}.{field} → '{old_val}' 복원")
                rolled += 1
            except Exception as e:
                msgs.append(f"#{log_id} 롤백 실패: {e}")

        con.commit()
        con.close()
        summary = f"↩️ {rolled}건 롤백 완료:\n" + "\n".join(msgs)
        return QueryResult(True, "AI_롤백", "", [], [], rolled, summary, None)
```

- [ ] **Step 7: 커밋**

```powershell
cd D:\program\SQM_inventory
git add sqm_v871_clean/features/ai/gemini_chat_query.py
git commit -m "feat(ai): write_mode 분기 + ai_edit_log 기록 + 롤백 처리 추가"
```

---

## Task 4: ai_chat.html — 🔒 버튼 + PIN 팝업 + 세션 타이머

**Files:**
- Modify: `frontend/detached/ai_chat.html`

- [ ] **Step 1: CSS 추가 (style 블록 끝에 삽입)**

`.send-btn:hover { opacity: 0.85; }` 바로 아래에 추가:

```css
/* ── 수정 모드 잠금 버튼 ── */
.lock-btn { background: transparent; border: 1px solid var(--border-default);
  border-radius: 6px; padding: 4px 10px; font-size: 12px; cursor: pointer;
  color: var(--text-muted); transition: all 0.2s; }
.lock-btn.unlocked { color: var(--success); border-color: var(--success); }
.lock-btn.warn { color: var(--warning); border-color: var(--warning); }

/* ── PIN 팝업 오버레이 ── */
.pin-overlay { display: none; position: fixed; inset: 0;
  background: rgba(0,0,0,0.6); z-index: 999;
  align-items: center; justify-content: center; }
.pin-overlay.show { display: flex; }
.pin-box { background: var(--bg-card); border: 1px solid var(--border-default);
  border-radius: 12px; padding: 28px 32px; width: 300px; text-align: center; }
.pin-box h2 { font-size: 15px; margin-bottom: 18px; color: var(--text-primary); }
.pin-input { width: 100%; padding: 10px; font-size: 20px; letter-spacing: 8px;
  text-align: center; background: var(--bg-root); color: var(--text-primary);
  border: 1px solid var(--border-default); border-radius: 8px; outline: none;
  margin-bottom: 14px; }
.pin-error { color: var(--danger); font-size: 12px; margin-bottom: 12px;
  min-height: 18px; }
.pin-btns { display: flex; gap: 8px; justify-content: center; }
.pin-btns button { flex: 1; padding: 8px; border-radius: 8px; border: none;
  cursor: pointer; font-size: 13px; }
.pin-cancel { background: var(--bg-card-hover); color: var(--text-primary); }
.pin-confirm { background: var(--accent); color: #fff; }
```

- [ ] **Step 2: HTML 구조 수정**

헤더에 🔒 버튼 추가:

Old:
```html
<div class="header">
  <span>&#x1F916;</span>
  <h1>SQM AI Assistant</h1>
  <button class="dock-btn" onclick="dockBack()">&#x1F4CC; 도킹</button>
</div>
```

New:
```html
<div class="pin-overlay" id="pin-overlay">
  <div class="pin-box">
    <h2>🔐 수정 모드 잠금 해제</h2>
    <input class="pin-input" type="password" id="pin-input"
           maxlength="6" placeholder="••••" autocomplete="off">
    <div class="pin-error" id="pin-error"></div>
    <div class="pin-btns">
      <button class="pin-cancel" onclick="closePinModal()">취소</button>
      <button class="pin-confirm" onclick="submitPin()">확인</button>
    </div>
  </div>
</div>
<div class="header">
  <span>&#x1F916;</span>
  <h1>SQM AI Assistant</h1>
  <button class="lock-btn" id="lock-btn" onclick="onLockClick()">🔒 수정 잠김</button>
  <button class="dock-btn" onclick="dockBack()">&#x1F4CC; 도킹</button>
</div>
```

- [ ] **Step 3: JavaScript 추가 (script 태그 상단에 추가)**

`var API_BASE = ...` 줄 아래에 추가:

```javascript
// ── 수정 모드 세션 ──────────────────────────────────────────
var writeToken = '';
var sessionTimer = null;

function onLockClick() {
  if (writeToken) {
    // 해제 상태 → 즉시 잠금
    lockWrite();
  } else {
    // 잠긴 상태 → PIN 팝업
    openPinModal();
  }
}

function openPinModal() {
  document.getElementById('pin-overlay').classList.add('show');
  document.getElementById('pin-input').value = '';
  document.getElementById('pin-error').textContent = '';
  setTimeout(function() { document.getElementById('pin-input').focus(); }, 100);
}

function closePinModal() {
  document.getElementById('pin-overlay').classList.remove('show');
}

function submitPin() {
  var pin = document.getElementById('pin-input').value.trim();
  if (!pin) return;
  fetch(API_BASE + '/api/ai/write-unlock', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ pin: pin })
  }).then(function(r) { return r.json(); }).then(function(res) {
    if (res.success) {
      writeToken = res.token;
      closePinModal();
      startSessionTimer();
    } else {
      document.getElementById('pin-error').textContent = res.detail || '인증 실패';
    }
  }).catch(function(e) {
    document.getElementById('pin-error').textContent = '서버 오류: ' + e.message;
  });
}

function lockWrite() {
  fetch(API_BASE + '/api/ai/write-lock', { method: 'POST',
    headers: { 'Content-Type': 'application/json' }, body: '{}' });
  writeToken = '';
  clearInterval(sessionTimer);
  sessionTimer = null;
  updateLockBtn(false, 0);
}

function startSessionTimer() {
  updateLockBtn(true, 600); // 초기 표시
  sessionTimer = setInterval(function() {
    fetch(API_BASE + '/api/ai/write-status?token=' + writeToken)
      .then(function(r) { return r.json(); })
      .then(function(res) {
        if (!res.active) {
          writeToken = '';
          clearInterval(sessionTimer);
          sessionTimer = null;
          updateLockBtn(false, 0);
          appendMsg('ai', '⏰ 수정 세션이 만료됐습니다. 다시 인증해 주세요.');
        } else {
          updateLockBtn(true, res.remaining_seconds);
        }
      });
  }, 15000); // 15초마다 체크
}

function updateLockBtn(unlocked, seconds) {
  var btn = document.getElementById('lock-btn');
  if (!unlocked) {
    btn.textContent = '🔒 수정 잠김';
    btn.className = 'lock-btn';
  } else {
    var mins = Math.ceil(seconds / 60);
    btn.textContent = '🔓 ' + mins + '분 남음';
    btn.className = 'lock-btn' + (seconds < 90 ? ' warn' : ' unlocked');
  }
}

// PIN 팝업 ESC/Enter 키
document.addEventListener('keydown', function(e) {
  var overlay = document.getElementById('pin-overlay');
  if (!overlay.classList.contains('show')) return;
  if (e.key === 'Escape') closePinModal();
  if (e.key === 'Enter') submitPin();
});
```

- [ ] **Step 4: sendMsg에 write_session_token 포함**

Old:
```javascript
    body: JSON.stringify({ message: msg })
```

New:
```javascript
    body: JSON.stringify({ message: msg, write_session_token: writeToken })
```

- [ ] **Step 5: 커밋**

```powershell
cd D:\program\SQM_inventory
git add sqm_v871_clean/frontend/detached/ai_chat.html
git commit -m "feat(ui): AI 채팅 수정 모드 잠금 버튼 + PIN 팝업 추가"
```

---

## Task 5: 설정 모달 PIN 변경 섹션

**Files:**
- Modify: `frontend/js/sqm-settings-templates.js` (showGeminiApiSettingsModal 함수, 약 125번 줄)

- [ ] **Step 1: PIN 변경 HTML 생성 함수 추가**

`sqm-settings-templates.js` 파일 상단 IIFE 안에 추가 (window.showGeminiApiSettingsModal 선언 아래):

```javascript
// ── AI 수정 PIN 변경 섹션 HTML ──────────────────────────────
function buildPinChangeSection() {
  return `
  <div style="margin-top:20px;padding-top:16px;border-top:1px solid var(--border-default)">
    <div style="font-size:13px;font-weight:600;color:var(--text-primary);margin-bottom:12px">
      🔑 AI 수정 PIN 변경
    </div>
    <div style="display:flex;flex-direction:column;gap:8px">
      <input type="password" id="pin-curr" placeholder="현재 PIN" maxlength="6"
        style="padding:8px;background:var(--bg-input);color:var(--text-primary);
          border:1px solid var(--border-default);border-radius:8px;font-size:13px;outline:none">
      <input type="password" id="pin-new" placeholder="새 PIN (4자리 이상)" maxlength="6"
        style="padding:8px;background:var(--bg-input);color:var(--text-primary);
          border:1px solid var(--border-default);border-radius:8px;font-size:13px;outline:none">
      <input type="password" id="pin-confirm" placeholder="새 PIN 확인" maxlength="6"
        style="padding:8px;background:var(--bg-input);color:var(--text-primary);
          border:1px solid var(--border-default);border-radius:8px;font-size:13px;outline:none">
      <div id="pin-change-msg" style="font-size:12px;min-height:16px;color:var(--danger)"></div>
      <button onclick="submitPinChange()"
        style="padding:8px 16px;background:var(--accent);color:#fff;border:none;
          border-radius:8px;cursor:pointer;font-size:13px;align-self:flex-start">
        PIN 변경
      </button>
    </div>
    <div style="margin-top:8px;font-size:11px;color:var(--text-muted)">
      ※ 기본 PIN은 <b>0000</b>입니다. 최초 변경을 권장합니다.
    </div>
  </div>`;
}

function submitPinChange() {
  var curr = (document.getElementById('pin-curr') || {}).value || '';
  var newPin = (document.getElementById('pin-new') || {}).value || '';
  var confirm = (document.getElementById('pin-confirm') || {}).value || '';
  var msgEl = document.getElementById('pin-change-msg');

  if (!curr || !newPin || !confirm) {
    msgEl.textContent = '모든 필드를 입력해 주세요.';
    return;
  }
  if (newPin !== confirm) {
    msgEl.textContent = '새 PIN이 일치하지 않습니다.';
    return;
  }
  if (newPin.length < 4) {
    msgEl.textContent = 'PIN은 4자리 이상이어야 합니다.';
    return;
  }

  var base = (window.SQM_API_BASE || window.location.origin || '');
  fetch(base + '/api/ai/pin/change', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ current_pin: curr, new_pin: newPin })
  }).then(function(r) { return r.json(); }).then(function(res) {
    if (res.success) {
      msgEl.style.color = 'var(--success)';
      msgEl.textContent = '✅ ' + res.message;
      ['pin-curr','pin-new','pin-confirm'].forEach(function(id) {
        var el = document.getElementById(id);
        if (el) el.value = '';
      });
    } else {
      msgEl.style.color = 'var(--danger)';
      msgEl.textContent = res.detail || '변경 실패';
    }
  }).catch(function(e) {
    msgEl.style.color = 'var(--danger)';
    msgEl.textContent = '오류: ' + e.message;
  });
}
```

- [ ] **Step 2: showGeminiApiSettingsModal 함수에 PIN 섹션 삽입**

`sqm-settings-templates.js` 약 144번 줄에서 다음 패턴을 찾아 교체:

Old (저장 버튼 뒤 닫는 div들):
```javascript
        + '<button onclick="window._saveGeminiSettings()" class="btn btn-primary">저장</button>'
        + '</div></div>';
      showDataModal('', html);
```

New (PIN 섹션 추가):
```javascript
        + '<button onclick="window._saveGeminiSettings()" class="btn btn-primary">저장</button>'
        + '</div>'
        + buildPinChangeSection()
        + '</div>';
      showDataModal('', html);
```

- [ ] **Step 3: 커밋**

```powershell
cd D:\program\SQM_inventory
git add sqm_v871_clean/frontend/js/sqm-settings-templates.js
git commit -m "feat(ui): Gemini 설정 모달에 AI 수정 PIN 변경 섹션 추가"
```

---

## Task 6: 통합 테스트

**Files:** 읽기 전용 (수동 테스트)

- [ ] **Step 1: 앱 재시작**

```powershell
cd D:\program\SQM_inventory\sqm_v871_clean
python main.py
```

- [ ] **Step 2: PIN 잠금 해제 테스트**

```
□ AI 채팅 창 열기
□ 헤더에 "🔒 수정 잠김" 버튼 확인
□ 버튼 클릭 → PIN 팝업 표시 확인
□ 틀린 PIN 입력 → 오류 메시지 확인
□ "0000" 입력 → "🔓 10분 남음" 버튼으로 변경 확인
```

- [ ] **Step 3: 데이터 수정 테스트**

```
□ "LOT 번호 XXX의 입고일을 2026-06-01로 변경해줘" 입력
□ "✅ 1건이 수정됐습니다." 응답 확인
□ DB에서 변경 확인: SELECT inbound_date FROM inventory WHERE lot_no='XXX'
□ ai_edit_log에 기록 확인: SELECT * FROM ai_edit_log ORDER BY id DESC LIMIT 1
```

- [ ] **Step 4: 롤백 테스트**

```
□ "방금 변경 취소해줘" 입력
□ "↩️ 1건 롤백 완료" 응답 확인
□ DB에서 원래 값 복원 확인
□ ai_edit_log에서 rolled_back=1 확인
```

- [ ] **Step 5: 세션 만료 테스트**

```
□ PIN 해제 후 10분 대기 (또는 config에서 session_minutes=1로 임시 변경 후 테스트)
□ 만료 시 "🔒 수정 잠김"으로 자동 복귀 확인
□ 만료 후 수정 명령 → 일반 조회로 처리됨 확인
```

- [ ] **Step 6: PIN 변경 테스트**

```
□ ⚙️ 설정 모달 열기
□ "AI 수정 PIN 변경" 섹션 확인
□ 현재 PIN "0000", 새 PIN "1234", 확인 "1234" 입력
□ "✅ PIN이 변경됐습니다." 확인
□ 새 PIN "1234"로 잠금 해제 확인
```

- [ ] **Step 7: 최종 커밋**

```powershell
cd D:\program\SQM_inventory
git add sqm_v871_clean/
git commit -m "feat(ai): AI 수정 모드 PIN + 롤백 기능 완성"
```
