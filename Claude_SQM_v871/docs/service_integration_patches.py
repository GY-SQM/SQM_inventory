# -*- coding: utf-8 -*-
"""
운영 연결 통합 패치 — 3개 패치
1. outbound_write_service.py → OutboundService 교체
2. react_api/utils/db.py → InventoryRepository 연결
3. SQMDatabase.__init__ → run_db_optimize() 연결
생성일: 2026-04-08 | SQM v8.7.1
"""

# ================================================================
# PATCH A: outbound_write_service.py
# execute_outbound() 함수를 OutboundService로 교체
# 파일: react_api/services/outbound_write_service.py
# ================================================================

PATCH_A = '''
# ── execute_outbound 교체 ──────────────────────────────────────
# 기존: engine.process_outbound() 직접 호출
# 변경: OutboundService.execute_reserved() + confirm_outbound()

def execute_outbound_v2(engine, req):
    """
    POST /api/outbound/execute v2
    OutboundService 기반으로 교체
    """
    from features.services.outbound_service import OutboundService
    svc = OutboundService(engine.db)

    if req.stop_at_picked:
        # RESERVED → PICKED 단계
        result = svc.execute_reserved(
            lot_no=req.items[0].lot_no if req.items else None
        )
        return {
            "success": result["success"],
            "message": f"피킹 완료: {result['executed']}건",
            "data": {
                "processed":       result["executed"],
                "lots_processed":  result["executed"],
                "total_weight_kg": 0,
                "total_picked":    result["executed"],
                "warnings":        result.get("warnings", []),
                "errors":          result.get("errors", []),
            }
        }
    else:
        # RESERVED → PICKED → OUTBOUND 전체
        r1 = svc.execute_reserved(lot_no=req.items[0].lot_no if req.items else None)
        r2 = svc.confirm_outbound(lot_no=req.items[0].lot_no if req.items else None)
        return {
            "success": r2["success"],
            "message": f"출고 완료: {r2['confirmed']}건",
            "data": {
                "processed":       r2["confirmed"],
                "lots_processed":  r2["confirmed"],
                "total_weight_kg": 0,
                "total_picked":    r1["executed"],
                "warnings":        r2.get("warnings", []),
                "errors":          r2.get("errors", []),
            }
        }
'''

# ================================================================
# PATCH B: react_api/utils/db.py
# InventoryRepository 헬퍼 함수 추가
# ================================================================

PATCH_B = '''
# ── db.py 하단에 추가 ──────────────────────────────────────────

def get_inventory_repo():
    """
    InventoryRepository 싱글톤 반환
    기존 engine 직접 호출 대신 사용
    """
    from features.repositories.inventory_repository import InventoryRepository
    return InventoryRepository(_get_shared_db())

# 사용 예시 (라우터에서):
# from react_api.utils.db import get_inventory_repo
# repo = get_inventory_repo()
# summary = repo.get_inventory_summary()
# lots = repo.get_inventory(status="AVAILABLE")
'''

# ================================================================
# PATCH C: engine_modules/database.py
# SQMDatabase.__init__ 마지막에 run_db_optimize() 추가
# ================================================================

PATCH_C = '''
# ── database.py의 SQMDatabase.__init__ 마지막에 추가 ───────────

# 기존 __init__ 마지막 부분 찾아서 아래 추가:
try:
    from engine_modules.db_optimize import run_db_optimize
    result = run_db_optimize(self)
    if result["indexes_added"] > 0:
        import logging as _lg
        _lg.getLogger(__name__).info(
            f"DB 최적화: 복합 인덱스 {result['indexes_added']}개 추가"
        )
except Exception as _opt_e:
    import logging as _lg
    _lg.getLogger(__name__).debug(f"DB 최적화 스킵: {_opt_e}")
'''

if __name__ == "__main__":
    print("=== 운영 연결 패치 내용 ===")
    print("\n[PATCH A] outbound_write_service.py → OutboundService")
    print(PATCH_A[:200], "...")
    print("\n[PATCH B] db.py → InventoryRepository 헬퍼")
    print(PATCH_B[:200], "...")
    print("\n[PATCH C] database.py → run_db_optimize() 자동 실행")
    print(PATCH_C[:200], "...")
