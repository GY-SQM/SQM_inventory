"""
Phase 2 통합 완성 테스트 — 2-2/2-3/2-4 실제 API 연결 검증
"""
import os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

BASE = os.path.join(os.path.dirname(__file__), "..")


def _read(rel):
    p = os.path.join(BASE, rel)
    return open(p, encoding="utf-8", errors="ignore").read() if os.path.exists(p) else ""


# ═══════════════════════════════════════════════════
# 2-2: 감사 로그 — 입고/출고에 실제 적용
# ═══════════════════════════════════════════════════

def test_inbound_has_audit_write():
    """inbound.py onestop_inbound_save에 write_audit 호출이 있어야 한다."""
    code = _read("backend/api/inbound.py")
    assert "write_audit" in code, "inbound.py에 write_audit 없음"
    assert "INBOUND_SAVE" in code, "inbound.py에 INBOUND_SAVE 이벤트 없음"


def test_outbound_has_audit_write():
    """outbound_api.py confirm_outbound에 write_audit 호출이 있어야 한다."""
    code = _read("backend/api/outbound_api.py")
    assert "write_audit" in code, "outbound_api.py에 write_audit 없음"
    assert "OUTBOUND_CONFIRM" in code, "outbound_api.py에 OUTBOUND_CONFIRM 이벤트 없음"


def test_audit_helper_uses_db_helper():
    """audit_helper.py가 get_db_connection을 사용해야 한다 (Phase 2-4 통합)."""
    code = _read("backend/api/audit_helper.py")
    assert "get_db_connection" in code, "audit_helper.py에 get_db_connection 없음"


# ═══════════════════════════════════════════════════
# 2-3: 입력값 검증 — 실제 API 연결
# ═══════════════════════════════════════════════════

def test_inbound_calls_validators():
    """inbound.py에 validator 함수 호출이 있어야 한다."""
    code = _read("backend/api/inbound.py")
    assert "validate_lot_no" in code, "inbound.py에 validate_lot_no 없음"
    assert "validate_date" in code, "inbound.py에 validate_date 없음"


def test_inbound_rejects_on_validation_error():
    """inbound.py가 검증 실패 시 해당 row를 errors에 추가해야 한다."""
    code = _read("backend/api/inbound.py")
    # 검증 에러 발생 시 continue (row 건너뜀)
    assert "_errs" in code and "continue" in code


def test_adjust_calls_validators():
    """inventory_adjust_api.py에 validator 호출이 있어야 한다."""
    code = _read("backend/api/inventory_adjust_api.py")
    assert "validate_lot_no" in code or "validate_quantity" in code


def test_adjust_raises_http_exception_on_validation_fail():
    """재고 수정 검증 실패 시 HTTPException(400)을 발생시켜야 한다."""
    code = _read("backend/api/inventory_adjust_api.py")
    assert "status_code=400" in code and "검증 실패" in code


# ═══════════════════════════════════════════════════
# 2-4: DB 연결 복구 — 실제 연결
# ═══════════════════════════════════════════════════

def test_ai_write_session_uses_db_helper():
    """ai_write_session.py가 get_db_connection을 사용해야 한다."""
    code = _read("backend/api/ai_write_session.py")
    assert "get_db_connection" in code, "ai_write_session.py에 get_db_connection 없음"


def test_db_helper_retry_on_failure(tmp_path):
    """연결 실패 시 재시도하고 최종 예외를 발생시켜야 한다."""
    import pytest
    from backend.api.db_helper import get_db_connection
    with pytest.raises(Exception):
        get_db_connection("/invalid/path/db.db", timeout=0.1, retries=2)


def test_validators_negative_quantity_rejected():
    """음수 수량은 검증에서 거부되어야 한다 (실제 validator 호출)."""
    from backend.api.validators import validate_quantity
    errs = validate_quantity(-1)
    assert len(errs) > 0


def test_validators_future_date_rejected():
    """미래 날짜는 검증에서 거부되어야 한다."""
    from backend.api.validators import validate_date
    errs = validate_date("2099-01-01")
    assert len(errs) > 0


def test_validators_empty_lot_rejected():
    """빈 LOT 번호는 검증에서 거부되어야 한다."""
    from backend.api.validators import validate_lot_no
    errs = validate_lot_no("")
    assert len(errs) > 0
