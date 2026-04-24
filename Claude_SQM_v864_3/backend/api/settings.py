# -*- coding: utf-8 -*-
"""
[Sprint 2-B] Settings + Carrier Rules
- API key management (read source / save to keyring)
- Carrier BL/DO rules CRUD
v864-2 source: dialogs/settings_dialog.py (869 lines, SettingsDialogMixin)
"""
import os
import sqlite3
import logging
from typing import Optional, Dict, Any

from fastapi import APIRouter, HTTPException, Body

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/settings", tags=["settings"])


def _db():
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(os.path.dirname(here))
    db_path = os.path.join(root, "data", "db", "sqm_inventory.db")
    con = sqlite3.connect(db_path, timeout=5, check_same_thread=False)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    return con


# ==============================================================
# API Key Management
# ==============================================================
@router.get("/api-keys", summary="API 키 상태 조회 [Sprint 2-B]")
def get_api_keys_status():
    """
    환경변수 / keyring / settings.ini 에서 API 키 출처 확인.
    실제 키 값은 마스킹 처리.
    """
    try:
        # config.py의 _load_settings 활용
        try:
            from config import _load_settings
            settings = _load_settings()
        except Exception:
            settings = {}

        def mask(v):
            if not v:
                return ""
            v = str(v)
            if len(v) <= 8:
                return "***"
            return v[:4] + "***" + v[-4:]

        gemini_key = settings.get("api_key", "")
        gemini_source = settings.get("api_key_source", None)
        openai_key = settings.get("openai_api_key", "")

        # 환경변수 직접 확인 (현재 프로세스 기준)
        env_keys = {
            "GEMINI_API_KEY": bool(os.environ.get("GEMINI_API_KEY")),
            "OPENAI_API_KEY": bool(os.environ.get("OPENAI_API_KEY")),
            "ANTHROPIC_API_KEY": bool(os.environ.get("ANTHROPIC_API_KEY")),
        }

        # keyring 확인
        keyring_available = False
        keyring_keys = {}
        try:
            import keyring
            keyring_available = True
            for k in ("GEMINI_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
                v = keyring.get_password("SQM_Inventory", k)
                keyring_keys[k] = bool(v)
        except Exception:
            pass

        return {
            "ok": True,
            "data": {
                "gemini": {
                    "configured": bool(gemini_key),
                    "source":     gemini_source,
                    "masked":     mask(gemini_key),
                    "model":      settings.get("model", "gemini-2.5-flash"),
                },
                "openai": {
                    "configured": bool(openai_key),
                    "masked":     mask(openai_key),
                    "model":      settings.get("openai_model", "gpt-4o"),
                },
                "env_present":     env_keys,
                "keyring_present": keyring_keys,
                "keyring_available": keyring_available,
                "settings_ini_path": "settings.ini",
                "use_gemini":        settings.get("use_gemini", True),
                "save_raw_response": settings.get("save_raw_gemini_response", False),
            },
        }
    except Exception as e:
        logger.error(f"get_api_keys_status error: {e}")
        raise HTTPException(500, str(e))


@router.post("/api-keys", summary="API 키 저장 (keyring) [Sprint 2-B]")
def save_api_key(payload: Dict[str, Any] = Body(...)):
    """
    Body: { service: 'gemini'|'openai'|'anthropic', api_key: '...' }
    keyring 에 저장 (환경변수보다 안전).
    """
    service = (payload or {}).get("service", "").lower()
    key = (payload or {}).get("api_key", "")
    if service not in ("gemini", "openai", "anthropic"):
        raise HTTPException(400, "service: gemini|openai|anthropic")
    if not key or not str(key).strip():
        raise HTTPException(400, "api_key 빈값")
    try:
        import keyring
        kr_key = {
            "gemini":    "GEMINI_API_KEY",
            "openai":    "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
        }[service]
        keyring.set_password("SQM_Inventory", kr_key, str(key).strip())
        return {"ok": True, "message": f"{service} API key 저장됨 (keyring)"}
    except ImportError:
        raise HTTPException(500, "keyring 미설치")
    except Exception as e:
        raise HTTPException(500, str(e))


@router.delete("/api-keys/{service}", summary="API 키 삭제 (keyring) [Sprint 2-B]")
def delete_api_key(service: str):
    if service.lower() not in ("gemini", "openai", "anthropic"):
        raise HTTPException(400, "service: gemini|openai|anthropic")
    try:
        import keyring
        kr_key = {
            "gemini":    "GEMINI_API_KEY",
            "openai":    "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
        }[service.lower()]
        try:
            keyring.delete_password("SQM_Inventory", kr_key)
        except Exception:
            pass
        return {"ok": True, "message": f"{service} API key 삭제됨"}
    except Exception as e:
        raise HTTPException(500, str(e))


# ==============================================================
# Carrier Rules (BL/DO patterns)
# ==============================================================
@router.get("/carrier-rules", summary="🚢 선사 BL/DO 규칙 목록 [Sprint 2-B]")
def list_carrier_rules(carrier_id: Optional[str] = None, doc_type: Optional[str] = None):
    try:
        con = _db()
        sql = "SELECT * FROM carrier_rules WHERE 1=1"
        params = []
        if carrier_id:
            sql += " AND carrier_id = ?"
            params.append(carrier_id)
        if doc_type:
            sql += " AND doc_type = ?"
            params.append(doc_type)
        sql += " ORDER BY carrier_id, doc_type, rule_name"
        rows = con.execute(sql, params).fetchall()
        # 사용 가능한 선사 목록 (distinct)
        carriers = con.execute("SELECT DISTINCT carrier_id FROM carrier_rules ORDER BY carrier_id").fetchall()
        con.close()
        return {
            "ok": True,
            "data": {
                "items": [dict(r) for r in rows],
                "total": len(rows),
                "available_carriers": [r[0] for r in carriers],
            },
        }
    except Exception as e:
        logger.error(f"list_carrier_rules error: {e}")
        raise HTTPException(500, str(e))


@router.post("/carrier-rules", summary="🚢 선사 규칙 생성 [Sprint 2-B]")
def create_carrier_rule(payload: Dict[str, Any] = Body(...)):
    carrier = (payload or {}).get("carrier_id", "").strip()
    doc_type = (payload or {}).get("doc_type", "").strip().upper()
    rule_name = (payload or {}).get("rule_name", "").strip()
    if not carrier or not doc_type or not rule_name:
        raise HTTPException(400, "carrier_id + doc_type + rule_name 필수")
    if doc_type not in ("BL", "DO", "PL", "INVOICE"):
        raise HTTPException(400, "doc_type: BL|DO|PL|INVOICE")
    fields = {
        "carrier_id":   carrier,
        "doc_type":     doc_type,
        "rule_name":    rule_name,
        "pattern":      payload.get("pattern", ""),
        "description":  payload.get("description", ""),
        "sample_value": payload.get("sample_value", ""),
        "is_active":    1 if payload.get("is_active", True) else 0,
    }
    try:
        con = _db()
        cur = con.execute(
            "INSERT INTO carrier_rules (carrier_id, doc_type, rule_name, pattern, description, sample_value, is_active) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            list(fields.values()),
        )
        new_id = cur.lastrowid
        con.commit(); con.close()
        return {"ok": True, "data": {**fields, "id": new_id}, "message": "규칙 생성됨"}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.patch("/carrier-rules/{rule_id}", summary="🚢 선사 규칙 수정 [Sprint 2-B]")
def update_carrier_rule(rule_id: int, updates: Dict[str, Any] = Body(...)):
    allowed = {"carrier_id", "doc_type", "rule_name", "pattern", "description", "sample_value", "is_active"}
    fields = {k: v for k, v in (updates or {}).items() if k in allowed}
    if not fields:
        raise HTTPException(400, "수정 가능 필드 없음")
    if "is_active" in fields:
        fields["is_active"] = 1 if fields["is_active"] else 0
    if "doc_type" in fields:
        fields["doc_type"] = str(fields["doc_type"]).upper()
        if fields["doc_type"] not in ("BL", "DO", "PL", "INVOICE"):
            raise HTTPException(400, "doc_type 잘못됨")
    sets = ", ".join(f"{k}=?" for k in fields.keys())
    values = list(fields.values()) + [rule_id]
    try:
        con = _db()
        cur = con.execute(
            f"UPDATE carrier_rules SET {sets}, updated_at=datetime('now') WHERE id=?",
            values,
        )
        if cur.rowcount == 0:
            con.close()
            raise HTTPException(404, f"rule {rule_id} 없음")
        con.commit(); con.close()
        return {"ok": True, "data": {"id": rule_id, "updated": list(fields.keys())}}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@router.delete("/carrier-rules/{rule_id}", summary="🚢 선사 규칙 삭제 [Sprint 2-B]")
def delete_carrier_rule(rule_id: int):
    try:
        con = _db()
        cur = con.execute("DELETE FROM carrier_rules WHERE id=?", (rule_id,))
        if cur.rowcount == 0:
            con.close()
            raise HTTPException(404, f"rule {rule_id} 없음")
        con.commit(); con.close()
        return {"ok": True, "message": f"rule {rule_id} 삭제됨"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))
