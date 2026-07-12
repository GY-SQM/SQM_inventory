# -*- coding: utf-8 -*-
"""[감사 raw-SQL / 방침 (A)] raw-SQL 우회 엔드포인트 무게 불변식 복구 헬퍼.

일부 엔드포인트는 재고 상태를 raw-SQL 로 직접 바꾸면서 무게 재계산을 빠뜨려
`initial_weight = current_weight + picked_weight` 불변식이 깨진 채 커밋됐다
(무게가 사라지거나 어긋남 → LOT wedge).

방침 (A): **화면 동작(상태 전이)은 그대로 두고**, 작업 커밋 직후 엔진의
`_recalc_current_weight` 를 호출해 톤백 실제 상태 기준으로 무게만 다시 맞춘다.
상태 문자열(SOLD/OUTBOUND 등 표시값)은 건드리지 않는다(_recalc_lot_status 는
호출하지 않음 — 그것은 표시 상태를 바꿔 (A) 위배).

주의: 엔드포인트가 자체 sqlite 연결로 커밋·close 한 '뒤에' 호출할 것.
      (엔진은 별도 연결이라 커밋된 데이터를 읽어 재계산한다.)
"""
import logging

logger = logging.getLogger(__name__)


def repair_weight_invariant(*lot_nos, reason: str = "RAWSQL_A_REPAIR") -> None:
    """주어진 LOT 들의 current/picked 무게를 톤백 실제값 기준으로 재계산(불변식 복구).

    엔진이 없거나 재계산에 실패해도 조용히 넘어간다(엔드포인트 본 응답은 이미 성공).
    """
    try:
        from backend.api import engine, ENGINE_AVAILABLE
    except Exception as e:  # pragma: no cover - import 보호
        logger.debug(f"[INVARIANT] engine import 실패: {e}")
        return
    if not ENGINE_AVAILABLE or engine is None or not hasattr(engine, "_recalc_current_weight"):
        return
    seen = set()
    for lot in lot_nos:
        lot = lot.strip() if isinstance(lot, str) else lot
        if not lot or lot in seen:
            continue
        seen.add(lot)
        try:
            engine._recalc_current_weight(lot, reason=reason)
        except Exception as e:
            logger.warning(f"[INVARIANT] LOT={lot} 무게 재계산 실패: {e}")
