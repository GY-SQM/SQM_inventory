# -*- coding: utf-8 -*-
"""
SQM v7.0.0-alpha — FastAPI REST API 프로토타입
================================================
기존 엔진(SQMInventoryEngineV3)을 REST API로 래핑.

실행:
    cd <project_root>
    uvicorn api.main:app --reload --port 8000

엔드포인트:
    GET  /api/v1/dashboard          — 대시보드 요약 (4단계 카드 + 반품률)
    GET  /api/v1/dashboard/alerts   — 알림 목록
    GET  /api/v1/inventory          — 재고 목록 (LOT 단위)
    GET  /api/v1/inventory/{lot_no} — LOT 상세 (톤백 포함)
    GET  /api/v1/returns/stats      — 반품 통계
    GET  /api/v1/returns/history    — 반품 이력
    GET  /api/v1/health             — 헬스 체크
"""

import logging
import os
import sys
from datetime import date, datetime
from typing import Dict, List, Optional

from fastapi import FastAPI, Query, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# 인증 의존성 (Optional — 없으면 인증 없이 운영)
try:
    from api.auth import get_current_user, require_role
    _auth_available = True
except ImportError:
    _auth_available = False
    def get_current_user(): return {}
    def require_role(r='viewer'): return lambda: {}

# 프로젝트 루트를 path에 추가
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════
# 엔진 초기화 (Lazy Singleton)
# ═══════════════════════════════════════════

_engine = None


def get_engine():
    """엔진 싱글턴 반환."""
    global _engine
    if _engine is None:
        try:
            from engine_modules.inventory_modular import SQMInventoryEngineV3
            db_path = os.path.join(_project_root, 'data', 'db', 'sqm_inventory.db')
            _engine = SQMInventoryEngineV3(db_path)
            logger.info(f"[API] 엔진 초기화: {db_path}")
        except Exception as e:
            logger.error(f"[API] 엔진 초기화 실패: {e}")
            raise HTTPException(status_code=500, detail=f"Engine init failed: {e}")
    return _engine


# ═══════════════════════════════════════════
# FastAPI 앱
# ═══════════════════════════════════════════

app = FastAPI(
    title="SQM 재고관리 API",
    description="SQM Inventory Management System REST API (v7.0.0-alpha)",
    version="7.0.0-alpha",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS (개발용 - 프로덕션에서는 도메인 제한)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# JWT 인증 라우터
try:
    from api.auth import router as auth_router
    app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
except ImportError:
    logger.debug("[API] auth 모듈 로드 실패 (인증 없이 운영)")

# Rate Limiting
try:
    from api.rate_limit import limiter, rate_limit_exceeded_handler, DEFAULT_RATE, WRITE_RATE
    from slowapi.errors import RateLimitExceeded
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)
    _rate_limit_enabled = True
    logger.info(f"[API] Rate limiting 활성화: {DEFAULT_RATE}")
except ImportError:
    _rate_limit_enabled = False
    logger.debug("[API] slowapi 미설치 (Rate limiting 비활성화)")

# 감사 로깅 미들웨어
try:
    from api.audit_middleware import AuditLogMiddleware
    _audit_db = None
    try:
        engine = get_engine()
        _audit_db = engine.db
    except Exception:
        pass
    app.add_middleware(AuditLogMiddleware, db=_audit_db)
    _audit_enabled = True
    logger.info("[API] 감사 로깅 활성화")
except ImportError:
    _audit_enabled = False
    logger.debug("[API] 감사 미들웨어 로드 실패")


# ═══════════════════════════════════════════
# Pydantic 모델
# ═══════════════════════════════════════════

class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: str
    db_connected: bool


class DashboardCard(BaseModel):
    status: str
    count: int
    weight_kg: float
    weight_mt: float


class ReturnRateSummary(BaseModel):
    return_count: int
    outbound_count: int
    return_rate: float
    return_weight_kg: float
    top_reasons: List[Dict]


class DashboardResponse(BaseModel):
    cards: Dict[str, DashboardCard]
    total_count: int
    total_kg: float
    total_mt: float
    return_rate: Optional[ReturnRateSummary] = None


class AlertItem(BaseModel):
    icon: str
    message: str
    severity: str
    lot_no: Optional[str] = None


class InventoryItem(BaseModel):
    lot_no: str
    sap_no: Optional[str] = None
    bl_no: Optional[str] = None
    product: Optional[str] = None
    status: Optional[str] = None
    net_weight: Optional[float] = None
    current_weight: Optional[float] = None
    tonbag_count: Optional[int] = None


class TonbagItem(BaseModel):
    sub_lt: int
    weight: float
    status: str
    is_sample: bool
    picked_to: Optional[str] = None


class LotDetailResponse(BaseModel):
    lot: InventoryItem
    tonbags: List[TonbagItem]
    movements: List[Dict]


# ═══════════════════════════════════════════
# 엔드포인트
# ═══════════════════════════════════════════

@app.get("/api/v1/health", response_model=HealthResponse)
def health_check():
    """헬스 체크 (인증 불요)."""
    db_ok = False
    try:
        engine = get_engine()
        engine.db.fetchone("SELECT 1")
        db_ok = True
    except Exception:
        pass
    return HealthResponse(
        status="ok" if db_ok else "degraded",
        version="7.0.0-alpha",
        timestamp=datetime.now().isoformat(),
        db_connected=db_ok,
    )


@app.get("/api/v1/dashboard", response_model=DashboardResponse)
def get_dashboard(user: dict = Depends(require_role('viewer'))):
    """대시보드 요약 (4단계 카드 + 반품률). 🔒 viewer 이상."""
    engine = get_engine()
    try:
        row = engine.db.fetchone("""
            SELECT
                SUM(CASE WHEN status='AVAILABLE' THEN 1 ELSE 0 END) AS available_cnt,
                SUM(CASE WHEN status='RESERVED'  THEN 1 ELSE 0 END) AS reserved_cnt,
                SUM(CASE WHEN status='PICKED'    THEN 1 ELSE 0 END) AS picked_cnt,
                SUM(CASE WHEN status='SOLD'      THEN 1 ELSE 0 END) AS sold_cnt,
                COUNT(*) AS total_cnt,
                COALESCE(SUM(CASE WHEN status='AVAILABLE' THEN weight ELSE 0 END),0) AS available_kg,
                COALESCE(SUM(CASE WHEN status='RESERVED'  THEN weight ELSE 0 END),0) AS reserved_kg,
                COALESCE(SUM(CASE WHEN status='PICKED'    THEN weight ELSE 0 END),0) AS picked_kg,
                COALESCE(SUM(CASE WHEN status='SOLD'      THEN weight ELSE 0 END),0) AS sold_kg,
                COALESCE(SUM(weight),0) AS total_kg
            FROM inventory_tonbag
        """)
        if not row:
            raise HTTPException(500, "No data")
        r = dict(row) if isinstance(row, dict) else {
            'available_cnt': row[0], 'reserved_cnt': row[1], 'picked_cnt': row[2],
            'sold_cnt': row[3], 'total_cnt': row[4], 'available_kg': row[5],
            'reserved_kg': row[6], 'picked_kg': row[7], 'sold_kg': row[8], 'total_kg': row[9]
        }

        cards = {}
        for status in ['available', 'reserved', 'picked', 'sold']:
            cnt = r.get(f'{status}_cnt', 0) or 0
            kg = float(r.get(f'{status}_kg', 0) or 0)
            cards[status] = DashboardCard(
                status=status.upper(), count=cnt, weight_kg=kg, weight_mt=kg / 1000)

        # 반품률
        return_rate = None
        try:
            rr = engine.db.fetchone("""
                SELECT COUNT(*) AS cnt, COALESCE(SUM(weight_kg),0) AS total
                FROM return_history WHERE return_date >= date('now','-30 days')
            """)
            out_row = engine.db.fetchone("""
                SELECT COUNT(*) AS cnt FROM stock_movement
                WHERE movement_type IN ('PICKED','SOLD','OUTBOUND')
                AND created_at >= date('now','-30 days')
            """)
            rc = (rr['cnt'] if isinstance(rr, dict) else rr[0]) if rr else 0
            rw = float((rr['total'] if isinstance(rr, dict) else rr[1]) if rr else 0)
            oc = (out_row['cnt'] if isinstance(out_row, dict) else out_row[0]) if out_row else 0
            rate = rc / max(oc, 1) * 100
            return_rate = ReturnRateSummary(
                return_count=rc, outbound_count=oc, return_rate=round(rate, 1),
                return_weight_kg=rw, top_reasons=[])
        except Exception:
            pass

        total_cnt = r.get('total_cnt', 0) or 0
        total_kg = float(r.get('total_kg', 0) or 0)
        return DashboardResponse(
            cards=cards, total_count=total_cnt,
            total_kg=total_kg, total_mt=total_kg / 1000,
            return_rate=return_rate,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/v1/dashboard/alerts", response_model=List[AlertItem])
def get_alerts(user: dict = Depends(require_role('viewer'))):
    """알림 목록. 🔒 viewer 이상."""
    engine = get_engine()
    alerts = []
    try:
        # 반품 알림
        from engine_modules.constants import RETURN_ALERT_THRESHOLD
        rows = engine.db.fetchall(f"""
            SELECT lot_no, COUNT(*) AS cnt FROM return_history
            GROUP BY lot_no HAVING COUNT(*) >= {RETURN_ALERT_THRESHOLD}
            ORDER BY cnt DESC LIMIT 10
        """)
        for r in (rows or []):
            lot = r['lot_no'] if isinstance(r, dict) else r[0]
            cnt = r['cnt'] if isinstance(r, dict) else r[1]
            alerts.append(AlertItem(
                icon='🔄', message=f"{lot}: 반품 {cnt}회 — 품질 점검 필요",
                severity='warning', lot_no=lot))
    except Exception as e:
        logger.debug(f"[API] alert error: {e}")
    return alerts


@app.get("/api/v1/inventory", response_model=List[InventoryItem])
def get_inventory(
    status: Optional[str] = Query(None, description="필터: AVAILABLE/RESERVED/PICKED/SOLD"),
    product: Optional[str] = Query(None, description="제품명 필터"),
    limit: int = Query(100, ge=1, le=1000),
    user: dict = Depends(require_role('viewer')),
):
    """재고 목록 (LOT 단위). 🔒 viewer 이상."""
    engine = get_engine()
    where = ["1=1"]
    params = []
    if status:
        where.append("i.status = ?")
        params.append(status.upper())
    if product:
        where.append("i.product LIKE ?")
        params.append(f"%{product}%")
    where_sql = " AND ".join(where)
    rows = engine.db.fetchall(f"""
        SELECT i.lot_no, i.sap_no, i.bl_no, i.product, i.status,
               i.net_weight, i.current_weight,
               (SELECT COUNT(*) FROM inventory_tonbag t
                WHERE t.lot_no = i.lot_no AND COALESCE(t.is_sample,0)=0) AS tonbag_count
        FROM inventory i WHERE {where_sql}
        ORDER BY i.lot_no LIMIT {limit}
    """, tuple(params))
    return [InventoryItem(**dict(r) if isinstance(r, dict) else {
        'lot_no': r[0], 'sap_no': r[1], 'bl_no': r[2], 'product': r[3],
        'status': r[4], 'net_weight': r[5], 'current_weight': r[6], 'tonbag_count': r[7]
    }) for r in (rows or [])]


@app.get("/api/v1/inventory/{lot_no}", response_model=LotDetailResponse)
def get_lot_detail(lot_no: str, user: dict = Depends(require_role('viewer'))):
    """LOT 상세 (톤백 + 이력). 🔒 viewer 이상."""
    engine = get_engine()
    lot_row = engine.db.fetchone(
        "SELECT lot_no, sap_no, bl_no, product, status, net_weight, current_weight "
        "FROM inventory WHERE lot_no = ?", (lot_no,))
    if not lot_row:
        raise HTTPException(404, f"LOT not found: {lot_no}")
    lot_d = dict(lot_row) if isinstance(lot_row, dict) else {
        'lot_no': lot_row[0], 'sap_no': lot_row[1], 'bl_no': lot_row[2],
        'product': lot_row[3], 'status': lot_row[4], 'net_weight': lot_row[5],
        'current_weight': lot_row[6]}

    tonbags = engine.db.fetchall(
        "SELECT sub_lt, weight, status, COALESCE(is_sample,0) AS is_sample, picked_to "
        "FROM inventory_tonbag WHERE lot_no = ? ORDER BY sub_lt", (lot_no,))
    tb_list = [TonbagItem(
        sub_lt=t['sub_lt'] if isinstance(t, dict) else t[0],
        weight=float(t['weight'] if isinstance(t, dict) else t[1]),
        status=t['status'] if isinstance(t, dict) else t[2],
        is_sample=bool(t['is_sample'] if isinstance(t, dict) else t[3]),
        picked_to=t.get('picked_to') if isinstance(t, dict) else t[4],
    ) for t in (tonbags or [])]

    movements = engine.db.fetchall(
        "SELECT movement_type, qty_kg, remarks, source_type, created_at "
        "FROM stock_movement WHERE lot_no = ? ORDER BY created_at", (lot_no,))
    mv_list = [dict(m) if isinstance(m, dict) else {
        'movement_type': m[0], 'qty_kg': m[1], 'remarks': m[2],
        'source_type': m[3], 'created_at': m[4]
    } for m in (movements or [])]

    return LotDetailResponse(lot=InventoryItem(**lot_d), tonbags=tb_list, movements=mv_list)


@app.get("/api/v1/returns/stats")
def get_return_stats(
    start_date: Optional[str] = Query(None, description="시작일 YYYY-MM-DD"),
    end_date: Optional[str] = Query(None, description="종료일 YYYY-MM-DD"),
    user: dict = Depends(require_role('viewer')),
):
    """반품 통계. 🔒 viewer 이상."""
    engine = get_engine()
    if hasattr(engine, 'get_return_statistics'):
        return engine.get_return_statistics(
            start_date=start_date or '', end_date=end_date or '')
    raise HTTPException(501, "get_return_statistics not available")


@app.get("/api/v1/returns/history")
def get_return_history(
    lot_no: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    user: dict = Depends(require_role('viewer')),
):
    """반품 이력. 🔒 viewer 이상."""
    engine = get_engine()
    where = ["1=1"]
    params = []
    if lot_no:
        where.append("r.lot_no = ?")
        params.append(lot_no)
    rows = engine.db.fetchall(f"""
        SELECT r.lot_no, r.sub_lt, r.return_date, r.original_customer,
               r.reason, r.remark, r.weight_kg, r.created_at
        FROM return_history r WHERE {" AND ".join(where)}
        ORDER BY r.created_at DESC LIMIT {limit}
    """, tuple(params))
    return [dict(r) if isinstance(r, dict) else {
        'lot_no': r[0], 'sub_lt': r[1], 'return_date': r[2],
        'original_customer': r[3], 'reason': r[4], 'remark': r[5],
        'weight_kg': r[6], 'created_at': r[7]
    } for r in (rows or [])]

# ═══════════════════════════════════════════
# POST 엔드포인트 (입고/출고/반품)
# ═══════════════════════════════════════════

class InboundRequest(BaseModel):
    """입고 요청."""
    lot_no: str
    sap_no: Optional[str] = ''
    bl_no: Optional[str] = ''
    product: str = 'Lithium Carbonate'
    net_weight: float  # 총 중량 (kg) — 1 LOT = N tonbags + 1 sample
    tonbag_count: int  # 톤백 수 (샘플 제외)
    tonbag_weight: float = 500.0  # 톤백 단가 (500 or 1000)
    container_no: Optional[str] = ''
    warehouse: Optional[str] = 'GY'
    source_type: str = 'API'
    source_file: str = ''


class OutboundRequest(BaseModel):
    """출고 요청."""
    lot_no: str
    customer: str
    sales_order: Optional[str] = ''
    picking_no: Optional[str] = ''
    tonbag_count: int  # 출고할 톤백 수
    stop_at_picked: bool = False  # True → PICKED까지만


class ReturnRequest(BaseModel):
    """반품 요청."""
    lot_no: str
    sub_lt: int
    reason: str = ''
    remark: str = ''


class OperationResult(BaseModel):
    """처리 결과."""
    success: bool
    message: str
    details: Optional[Dict] = None


@app.post("/api/v1/inventory/inbound", response_model=OperationResult)
def api_inbound(req: InboundRequest, user: dict = Depends(require_role('operator'))):
    """
    입고 처리. 🔒 operator 이상.

    1 LOT = N tonbags + 1 sample (1kg)
    net_weight = tonbag_count × tonbag_weight + 1
    """
    engine = get_engine()

    # SQM 원칙 검증: net_weight == tonbag_count × tonbag_weight + 1
    expected = req.tonbag_count * req.tonbag_weight + 1.0
    if abs(req.net_weight - expected) > 0.5:
        raise HTTPException(400,
            f"중량 불일치: net_weight={req.net_weight} ≠ "
            f"tonbag_count({req.tonbag_count}) × tonbag_weight({req.tonbag_weight}) + 1kg(sample) = {expected}")

    # 톤백 구성
    tonbags = []
    for i in range(1, req.tonbag_count + 1):
        tonbags.append({'sub_lt': i, 'weight': req.tonbag_weight, 'is_sample': False})
    tonbags.append({'sub_lt': req.tonbag_count + 1, 'weight': 1.0, 'is_sample': True})

    packing_data = {
        'lot_no': req.lot_no,
        'sap_no': req.sap_no,
        'bl_no': req.bl_no,
        'product': req.product,
        'net_weight': req.net_weight,
        'container_no': req.container_no,
        'warehouse': req.warehouse,
        'tonbags': tonbags,
    }

    try:
        result = engine.process_inbound(
            packing_data,
            source_type=req.source_type or 'API',
            source_file=req.source_file or f'API:{user.get("sub", "unknown")}',
        )
        return OperationResult(
            success=result.get('success', False),
            message=result.get('message', ''),
            details={
                'lot_no': result.get('lot_no'),
                'created_lots': result.get('created_lots', []),
                'created_tonbags': result.get('created_tonbags', 0),
                'warnings': result.get('warnings', []),
            }
        )
    except Exception as e:
        raise HTTPException(500, f"입고 처리 오류: {e}")


@app.post("/api/v1/inventory/outbound", response_model=OperationResult)
def api_outbound(req: OutboundRequest, user: dict = Depends(require_role('operator'))):
    """
    출고 처리. 🔒 operator 이상.

    AVAILABLE → RESERVED → PICKED (→ SOLD)
    """
    engine = get_engine()

    allocation_data = {
        'lot_no': req.lot_no,
        'customer': req.customer,
        'sales_order': req.sales_order,
        'picking_no': req.picking_no,
        'tonbag_count': req.tonbag_count,
    }

    try:
        result = engine.process_outbound(
            allocation_data,
            source=f'API:{user.get("sub", "unknown")}',
            stop_at_picked=req.stop_at_picked,
        )
        return OperationResult(
            success=result.get('success', False),
            message=result.get('message', ''),
            details={
                'processed': result.get('processed', 0),
                'total_weight_kg': result.get('total_weight_kg', 0),
                'total_picked': result.get('total_picked', 0),
                'warnings': result.get('warnings', []),
            }
        )
    except Exception as e:
        raise HTTPException(500, f"출고 처리 오류: {e}")


@app.post("/api/v1/returns/process", response_model=OperationResult)
def api_return(req: ReturnRequest, user: dict = Depends(require_role('operator'))):
    """
    반품 처리. 🔒 operator 이상.

    SOLD/PICKED/RESERVED → AVAILABLE
    """
    engine = get_engine()

    try:
        if hasattr(engine, 'process_return'):
            result = engine.process_return(
                lot_no=req.lot_no,
                sub_lt=req.sub_lt,
                reason=req.reason,
                remark=req.remark,
                source_type='RETURN_API',
            )
            return OperationResult(
                success=result.get('success', False),
                message=result.get('message', ''),
                details=result,
            )
        else:
            raise HTTPException(501, "process_return not available")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"반품 처리 오류: {e}")


# ═══════════════════════════════════════════
# WebSocket 실시간 대시보드
# ═══════════════════════════════════════════

from fastapi import WebSocket, WebSocketDisconnect
import asyncio
import json as _json


class ConnectionManager:
    """WebSocket 연결 관리."""

    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)
        logger.info(f"[WS] 연결: {len(self.active)}명")

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)
        logger.info(f"[WS] 해제: {len(self.active)}명")

    async def broadcast(self, data: dict):
        disconnected = []
        for ws in self.active:
            try:
                await ws.send_json(data)
            except Exception:
                disconnected.append(ws)
        for ws in disconnected:
            self.disconnect(ws)


ws_manager = ConnectionManager()


def _get_dashboard_snapshot() -> dict:
    """대시보드 스냅샷 (동기)."""
    try:
        engine = get_engine()
        row = engine.db.fetchone("""
            SELECT
                SUM(CASE WHEN status='AVAILABLE' THEN 1 ELSE 0 END) AS available_cnt,
                SUM(CASE WHEN status='RESERVED'  THEN 1 ELSE 0 END) AS reserved_cnt,
                SUM(CASE WHEN status='PICKED'    THEN 1 ELSE 0 END) AS picked_cnt,
                SUM(CASE WHEN status='SOLD'      THEN 1 ELSE 0 END) AS sold_cnt,
                COUNT(*) AS total_cnt,
                COALESCE(SUM(weight),0) AS total_kg
            FROM inventory_tonbag
        """)
        if not row:
            return {'type': 'dashboard', 'error': 'no data'}
        r = dict(row) if isinstance(row, dict) else {
            'available_cnt': row[0], 'reserved_cnt': row[1], 'picked_cnt': row[2],
            'sold_cnt': row[3], 'total_cnt': row[4], 'total_kg': row[5]
        }
        return {
            'type': 'dashboard',
            'cards': {
                'available': {'count': r['available_cnt'] or 0, 'weight_mt': (r.get('available_cnt', 0) or 0) * 0.5},
                'reserved': {'count': r['reserved_cnt'] or 0},
                'picked': {'count': r['picked_cnt'] or 0},
                'sold': {'count': r['sold_cnt'] or 0},
            },
            'total_count': r['total_cnt'] or 0,
            'total_mt': float(r['total_kg'] or 0) / 1000,
            'timestamp': datetime.now().isoformat(),
        }
    except Exception as e:
        return {'type': 'dashboard', 'error': str(e)}


@app.websocket("/ws/dashboard")
async def websocket_dashboard(ws: WebSocket):
    """
    WebSocket 대시보드 실시간 스트리밍.

    연결 후 5초 간격으로 대시보드 스냅샷 전송.
    클라이언트에서 {"command": "refresh"} 전송 시 즉시 전송.
    """
    await ws_manager.connect(ws)
    try:
        # 최초 즉시 전송
        snapshot = _get_dashboard_snapshot()
        await ws.send_json(snapshot)

        while True:
            try:
                # 클라이언트 메시지 수신 (5초 타임아웃)
                data = await asyncio.wait_for(ws.receive_text(), timeout=5.0)
                try:
                    msg = _json.loads(data)
                    if msg.get('command') == 'refresh':
                        snapshot = _get_dashboard_snapshot()
                        await ws.send_json(snapshot)
                except _json.JSONDecodeError:
                    pass
            except asyncio.TimeoutError:
                # 5초마다 자동 전송
                snapshot = _get_dashboard_snapshot()
                await ws.send_json(snapshot)
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)
    except Exception:
        ws_manager.disconnect(ws)


# ═══════════════════════════════════════════
# 감사 로그 조회 (admin 전용)
# ═══════════════════════════════════════════

@app.get("/api/v1/audit/logs")
def api_get_audit_logs(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    username: Optional[str] = Query(None),
    method: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    user: dict = Depends(require_role('admin')),
):
    """감사 로그 조회. 🔒 admin 전용."""
    engine = get_engine()
    try:
        from api.audit_middleware import get_audit_logs
        return get_audit_logs(
            engine.db,
            start_date=start_date or '',
            end_date=end_date or '',
            username=username or '',
            method=method or '',
            limit=limit,
        )
    except ImportError:
        raise HTTPException(501, "감사 모듈 미설치")
    except Exception as e:
        raise HTTPException(500, str(e))
