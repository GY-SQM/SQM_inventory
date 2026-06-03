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
_sessions: dict = {}           # token → 만료 timestamp
_fail_count: int = 0           # 연속 실패 횟수
_fail_lockout_until: float = 0 # 잠금 해제 timestamp


# ── config 로드/저장 ──────────────────────────────────────────
def _load_config() -> dict:
    path = _config_path()
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
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
def check_pin(pin: str):
    """
    PIN 검증.
    Returns: (success: bool, message: str)
    실패 3회 → 30초 잠금.
    """
    global _fail_count, _fail_lockout_until

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


def change_pin(current_pin: str, new_pin: str):
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
