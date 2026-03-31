# -*- coding: utf-8 -*-
"""
tests/fixtures/sqm_scenario_data.py
=====================================
SQM v7.0.0 — APL 3항차 전체 시나리오 데이터 생성기
=====================================================

구조:
  3 Vessel × 5 Container × 4 LOT × (10 톤백 × 500kg + 샘플 1kg)
  = LOT 60개 / 톤백 660개 / 총중량 300.1MT

일정:
  입고: 2026-03-01 ~ 04-15
  Allocation: 출고 10일 전
  PickingList: 출고  5일 전
  출고: 2026-05-01 ~ 06-30 (50%)
  반품: 출고+15~30일 (출고분의 20%)
  위치이동: 2026-05-15 ~ 06-15 (미출고의 30%)

고객사: CATL(12) · BYD(10) · LG Energy Solution(8)
"""
from __future__ import annotations
from engine_modules.constants import STATUS_AVAILABLE, STATUS_PICKED, STATUS_SOLD

import sqlite3
import random
from datetime import date, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Union


# ─── 시나리오 상수 ────────────────────────────────────────────────────────────
CARRIER       = "APL"
VESSEL_NAMES  = ["APL LION CITY", "APL SINGAPURA", "APL TEMASEK"]
VOYAGE_NOS    = ["APL-V001", "APL-V002", "APL-V003"]
PRODUCT       = "Lithium Carbonate"
SAP_PREFIX    = "20260301"

VESSELS_COUNT         = 3
CONTAINERS_PER_VESSEL = 5
LOTS_PER_CONTAINER    = 4
TONBAGS_PER_LOT       = 10
TONBAG_WEIGHT_KG      = 500.0
SAMPLE_WEIGHT_KG      = 1.0
LOT_TOTAL_WEIGHT_KG   = TONBAGS_PER_LOT * TONBAG_WEIGHT_KG + SAMPLE_WEIGHT_KG  # 5001.0

INBOUND_START  = date(2026, 3,  1)
INBOUND_END    = date(2026, 4, 15)
OUTBOUND_START = date(2026, 5,  1)
OUTBOUND_END   = date(2026, 6, 30)
MOVE_START     = date(2026, 5, 15)
MOVE_END       = date(2026, 6, 15)

CUSTOMERS = [
    {"name": "CATL",                "lots": 12},
    {"name": "BYD",                 "lots": 10},
    {"name": "LG Energy Solution",  "lots":  8},
]
TOTAL_OUTBOUND_LOTS = sum(c["lots"] for c in CUSTOMERS)  # 30
RETURN_COUNT        = 6    # 출고 30 × 20%
MOVE_COUNT          = 9    # 미출고 30 × 30%

WAREHOUSE_ZONES = ["A", "B"]


# ─── 헬퍼 ─────────────────────────────────────────────────────────────────────
def _rand_date(start: date, end: date) -> str:
    delta = (end - start).days
    return (start + timedelta(days=random.randint(0, delta))).strftime("%Y-%m-%d")


def _container_no(vessel_idx: int, container_idx: int) -> str:
    """APLU + 7자리 숫자 형식"""
    n = vessel_idx * 100 + container_idx
    return f"APLU{n:07d}"


def _lot_no(seq: int) -> str:
    """112 + 7자리 순번 → 10자리 LOT 번호"""
    return f"112{seq:07d}"


def _sap_no(seq: int) -> str:
    return f"2026{seq:06d}"


def _location(zone: Optional[str] = None) -> str:
    """A-00-00-00 형식 로케이션"""
    z = zone or random.choice(WAREHOUSE_ZONES)
    row  = random.randint(1, 20)
    col  = random.randint(1, 10)
    tier = random.randint(1, 5)
    return f"{z}-{row:02d}-{col:02d}-{tier:02d}"


def _bl_no(vessel_idx: int) -> str:
    return f"APLSIN{vessel_idx+1:04d}26"


# ─── 메인 데이터 생성 ─────────────────────────────────────────────────────────
def build_scenario() -> Dict:
    random.seed(42)  # 항상 동일 데이터 보장 (멱등성)
    """
    전체 시나리오 데이터 딕셔너리 반환.

    Returns:
        {
            'vessels':    List[Dict]  — 3개
            'containers': List[Dict]  — 15개
            'lots':       List[Dict]  — 60개
            'tonbags':    List[Dict]  — 660개 (600 일반 + 60 샘플)
            'outbounds':  List[Dict]  — 30개
            'returns':    List[Dict]  — 6개
            'moves':      List[Dict]  — 9개
            'allocations':List[Dict]  — 30개 (출고 10일 전)
            'picking':    List[Dict]  — 30개 (출고 5일 전)
        }
    """
    vessels    = _build_vessels()
    containers = _build_containers(vessels)
    lots       = _build_lots(containers)
    tonbags    = _build_tonbags(lots)
    outbounds  = _build_outbounds(lots)
    returns    = _build_returns(outbounds)
    moves      = _build_moves(lots, outbounds)
    allocations= _build_allocations(outbounds)
    picking    = _build_picking(outbounds)

    return {
        'vessels':     vessels,
        'containers':  containers,
        'lots':        lots,
        'tonbags':     tonbags,
        'outbounds':   outbounds,
        'returns':     returns,
        'moves':       moves,
        'allocations': allocations,
        'picking':     picking,
    }


def _build_vessels() -> List[Dict]:
    vessels = []
    for i in range(VESSELS_COUNT):
        vessels.append({
            'vessel_id':   f"VSL{i+1:03d}",
            'carrier':     CARRIER,
            'vessel_name': VESSEL_NAMES[i],
            'voyage_no':   VOYAGE_NOS[i],
            'bl_no':       _bl_no(i),
            'etd':         (INBOUND_START + timedelta(days=i * 15)).strftime("%Y-%m-%d"),
            'eta':         (INBOUND_START + timedelta(days=i * 15 + 7)).strftime("%Y-%m-%d"),
        })
    return vessels


def _build_containers(vessels: List[Dict]) -> List[Dict]:
    containers = []
    seq = 1
    for v in vessels:
        for c in range(CONTAINERS_PER_VESSEL):
            containers.append({
                'container_id':  f"CTR{seq:03d}",
                'container_no':  _container_no(
                    int(v['vessel_id'][3:]) - 1, c
                ),
                'vessel_id':     v['vessel_id'],
                'voyage_no':     v['voyage_no'],
                'bl_no':         v['bl_no'],
                'seal_no':       f"SL{seq:06d}",
            })
            seq += 1
    return containers  # 15개


def _build_lots(containers: List[Dict]) -> List[Dict]:
    lots = []
    seq  = 1
    # 입고일 분산: 항차당 interval
    total_days = (INBOUND_END - INBOUND_START).days
    for i, ctr in enumerate(containers):
        for j in range(LOTS_PER_CONTAINER):
            # 입고일 균등 분산
            day_offset = (i * LOTS_PER_CONTAINER + j) * total_days // (len(containers) * LOTS_PER_CONTAINER)
            arrival = (INBOUND_START + timedelta(days=day_offset)).strftime("%Y-%m-%d")
            lots.append({
                'lot_seq':        seq,
                'lot_no':         _lot_no(seq),
                'sap_no':         _sap_no(seq),
                'container_id':   ctr['container_id'],
                'container_no':   ctr['container_no'],
                'vessel_id':      ctr['vessel_id'],
                'voyage_no':      ctr['voyage_no'],
                'bl_no':          ctr['bl_no'],
                'product':        PRODUCT,
                'total_weight_kg': LOT_TOTAL_WEIGHT_KG,
                'arrival_date':   arrival,
                'status':         STATUS_AVAILABLE,
                'location':       _location('A'),  # 초기 입고 → A존
            })
            seq += 1
    return lots  # 60개


def _build_tonbags(lots: List[Dict]) -> List[Dict]:
    tonbags = []
    for lot in lots:
        lot_no = lot['lot_no']
        loc    = lot['location']
        # 일반 톤백 10개 (001 ~ 010)
        for tb in range(1, TONBAGS_PER_LOT + 1):
            tonbags.append({
                'lot_no':      lot_no,
                'tonbag_no':   f"{tb:03d}",
                'tonbag_uid':  f"{lot_no}-{tb:03d}",
                'is_sample':   0,
                'weight_kg':   TONBAG_WEIGHT_KG,
                'qty_mt':      TONBAG_WEIGHT_KG / 1000,
                'location':    loc,
                'warehouse':   loc[0],  # A or B
                'status':      STATUS_AVAILABLE,
                'arrival_date': lot['arrival_date'],
            })
        # 샘플 1개 (S00)
        tonbags.append({
            'lot_no':      lot_no,
            'tonbag_no':   'S00',
            'tonbag_uid':  f"{lot_no}-S00",
            'is_sample':   1,
            'weight_kg':   SAMPLE_WEIGHT_KG,
            'qty_mt':      SAMPLE_WEIGHT_KG / 1000,
            'location':    loc,
            'warehouse':   loc[0],
            'status':      STATUS_AVAILABLE,
            'arrival_date': lot['arrival_date'],
        })
    return tonbags  # 660개


def _build_outbounds(lots: List[Dict]) -> List[Dict]:
    outbounds = []
    seq = 1
    # 고객별 LOT 할당
    lot_pool = list(range(len(lots)))
    random.shuffle(lot_pool)
    idx = 0
    for cust in CUSTOMERS:
        for _ in range(cust['lots']):
            lot = lots[lot_pool[idx]]
            ship_date = _rand_date(OUTBOUND_START, OUTBOUND_END)
            outbounds.append({
                'outbound_id':   f"OUT{seq:04d}",
                'lot_no':        lot['lot_no'],
                'lot_idx':       lot_pool[idx],
                'customer':      cust['name'],
                'ship_date':     ship_date,
                'weight_kg':     LOT_TOTAL_WEIGHT_KG,
                'qty_mt':        LOT_TOTAL_WEIGHT_KG / 1000,
                'status':        STATUS_SOLD,
            })
            seq += 1
            idx += 1
    return outbounds  # 30개


def _build_returns(outbounds: List[Dict]) -> List[Dict]:
    """
    RETURN_AS_REINBOUND 정책 기반 반품 데이터 생성.

    - processed_as = 'REINBOUND'  : 재고 엔진은 재입고처럼 처리
    - new_location  : PDA 재스캔으로 새로 배정된 위치 (B존)
    - outbound_id   : 원출고와의 연결 유지 (감사 추적)
    """
    returns = []
    return_pool = outbounds[:RETURN_COUNT]  # 처음 6개
    for i, ob in enumerate(return_pool):
        base = date.fromisoformat(ob['ship_date'])
        return_date = (base + timedelta(days=random.randint(15, 30))).strftime("%Y-%m-%d")
        # 반품 시 PDA 재스캔 → B존 새 위치 배정
        new_loc = f"B-{(i+1):02d}-{(i%5+1):02d}-{(i%4+1):02d}"
        returns.append({
            'return_id':    f"RET{i+1:04d}",
            'outbound_id':  ob['outbound_id'],
            'lot_no':       ob['lot_no'],
            'customer':     ob['customer'],
            'return_date':  return_date,
            'reason':       random.choice(["품질 이슈", "계약 변경", "물류 오류"]),
            'weight_kg':    LOT_TOTAL_WEIGHT_KG,
            'processed_as': 'REINBOUND',
            'new_location': new_loc,
            'operator_id':  'SYSTEM',
        })
    return returns  # 6개


def _build_moves(lots: List[Dict], outbounds: List[Dict]) -> List[Dict]:
    outbound_lot_nos = {ob['lot_no'] for ob in outbounds}
    remaining = [l for l in lots if l['lot_no'] not in outbound_lot_nos]
    move_targets = remaining[:MOVE_COUNT]  # 9개
    moves = []
    for i, lot in enumerate(move_targets):
        move_date = _rand_date(MOVE_START, MOVE_END)
        new_loc   = _location('B')  # B존으로 이동
        moves.append({
            'move_id':      f"MOV{i+1:04d}",
            'lot_no':       lot['lot_no'],
            'from_location': lot['location'],
            'to_location':  new_loc,
            'move_date':    move_date,
            'reason':       '재배치',
        })
    return moves  # 9개


def _build_allocations(outbounds: List[Dict]) -> List[Dict]:
    allocations = []
    for i, ob in enumerate(outbounds):
        ship = date.fromisoformat(ob['ship_date'])
        alloc_date = (ship - timedelta(days=10)).strftime("%Y-%m-%d")
        allocations.append({
            'alloc_id':       f"ALLOC{i+1:04d}",
            'lot_no':         ob['lot_no'],
            'customer':       ob['customer'],
            'ship_date':      ob['ship_date'],
            'alloc_date':     alloc_date,
            'qty_mt':         ob['qty_mt'],
            'status':         'APPROVED',
            'export_type':    'D',
            'source':         'SCENARIO',
            'workflow_status': 'APPROVED',
        })
    return allocations  # 30개


def _build_picking(outbounds: List[Dict]) -> List[Dict]:
    picking = []
    for i, ob in enumerate(outbounds):
        ship  = date.fromisoformat(ob['ship_date'])
        pick_date = (ship - timedelta(days=5)).strftime("%Y-%m-%d")
        picking.append({
            'pick_id':    f"PICK{i+1:04d}",
            'lot_no':     ob['lot_no'],
            'customer':   ob['customer'],
            'pick_date':  pick_date,
            'ship_date':  ob['ship_date'],
            'tonbag_count': TONBAGS_PER_LOT,
            'status':     STATUS_PICKED,
        })
    return picking  # 30개


# ─── SQLite 헬퍼 ──────────────────────────────────────────────────────────────
def create_scenario_db(
    db_path: Union[str, "Path"] = ":memory:",
    verbose: bool = False,
) -> sqlite3.Connection:
    """
    시나리오 전용 SQLite DB 생성 + 전체 데이터 INSERT.

    Args:
        db_path: ':memory:' 또는 파일 경로 (str / pathlib.Path 모두 허용)
                 Windows/Linux 경로 구분자 자동 처리.
                 예) 'data/test_apl_scenario.db'
                     Path('data') / 'test_apl_scenario.db'
        verbose: True면 INSERT 통계 출력
    """
    import time as _time
    _is_memory = (str(db_path) == ':memory:')
    if not _is_memory:
        db_path = Path(db_path)          # str → Path (Windows '\' 자동 처리)
        db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA cache_size=-32000")  # 32MB 캐시

    _create_tables(conn)
    _t0 = _time.perf_counter()  # 성능 측정 예약 변수
    scenario = build_scenario()
    _insert_all(conn, scenario)
    elapsed = _time.perf_counter() - _t0

    if verbose:
        lot_cnt = conn.execute("SELECT COUNT(*) FROM inventory").fetchone()[0]
        tb_cnt  = conn.execute("SELECT COUNT(*) FROM inventory_tonbag").fetchone()[0]
        print(f"[create_scenario_db] {db_path}")
        print(f"  LOT: {lot_cnt}개 / 톤백: {tb_cnt}개 / {elapsed:.3f}s")
        if not _is_memory:
            size_kb = Path(db_path).stat().st_size / 1024
            print(f"  파일 크기: {size_kb:.1f} KB")
    return conn


def save_scenario_to_file(
    db_path: Union[str, "Path"] = "data/test_apl_scenario.db",
    verbose: bool = True,
) -> str:
    """
    시나리오 데이터를 파일 DB에 저장하고 경로를 반환합니다.
    기존 파일이 있으면 삭제 후 재생성합니다.
    Windows/Linux 경로 구분자 모두 지원 (pathlib.Path 기반).

    Args:
        db_path: 저장 경로 str 또는 Path
                 (기본: data/test_apl_scenario.db)
        verbose: 저장 통계 출력 여부

    Returns:
        저장된 DB 파일의 절대경로 문자열
    """
    p = Path(db_path).resolve()          # 절대경로 변환 (플랫폼 독립)
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        p.unlink()                        # 기존 파일 삭제
    conn = create_scenario_db(db_path=p, verbose=verbose)
    conn.close()
    return str(p)


def _create_tables(conn: sqlite3.Connection) -> None:
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS vessel_master (
        vessel_id   TEXT PRIMARY KEY,
        carrier     TEXT,
        vessel_name TEXT,
        voyage_no   TEXT,
        bl_no       TEXT,
        etd         TEXT,
        eta         TEXT
    );
    CREATE TABLE IF NOT EXISTS container_master (
        container_id  TEXT PRIMARY KEY,
        container_no  TEXT UNIQUE,
        vessel_id     TEXT REFERENCES vessel_master(vessel_id),
        voyage_no     TEXT,
        bl_no         TEXT,
        seal_no       TEXT
    );
    CREATE TABLE IF NOT EXISTS inventory (
        lot_no          TEXT PRIMARY KEY,
        sap_no          TEXT,
        container_id    TEXT REFERENCES container_master(container_id),
        container_no    TEXT,
        vessel_id       TEXT,
        voyage_no       TEXT,
        bl_no           TEXT,
        product         TEXT,
        total_weight_kg REAL,
        arrival_date    TEXT,
        ship_date       TEXT,
        status          TEXT DEFAULT 'AVAILABLE',
        location        TEXT,
        current_weight  REAL
    );
    CREATE TABLE IF NOT EXISTS inventory_tonbag (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        lot_no      TEXT REFERENCES inventory(lot_no),
        tonbag_no   TEXT,
        tonbag_uid  TEXT UNIQUE,
        is_sample   INTEGER DEFAULT 0,
        weight_kg   REAL,
        qty_mt      REAL,
        location    TEXT,
        warehouse   TEXT,
        status      TEXT DEFAULT 'AVAILABLE',
        arrival_date TEXT
    );
    CREATE TABLE IF NOT EXISTS outbound_log (
        outbound_id TEXT PRIMARY KEY,
        lot_no      TEXT REFERENCES inventory(lot_no),
        customer    TEXT,
        ship_date   TEXT,
        weight_kg   REAL,
        qty_mt      REAL,
        status      TEXT DEFAULT 'SOLD'
    );
    CREATE TABLE IF NOT EXISTS return_log (
        return_id       TEXT PRIMARY KEY,
        outbound_id     TEXT,
        lot_no          TEXT,
        customer        TEXT,
        return_date     TEXT,
        reason          TEXT,
        weight_kg       REAL,
        processed_as    TEXT DEFAULT 'REINBOUND',
        new_location    TEXT,
        operator_id     TEXT DEFAULT 'SYSTEM'
    );
    -- v6.6.0: location_move_log 폐지 → stock_movement.RELOCATE 통합
    -- 하위호환 빈 테이블만 유지 (참조 코드 오류 방지)
    CREATE TABLE IF NOT EXISTS location_move_log (
        move_id       TEXT PRIMARY KEY,
        lot_no        TEXT,
        from_location TEXT,
        to_location   TEXT,
        move_date     TEXT,
        reason        TEXT
    );
    CREATE TABLE IF NOT EXISTS stock_movement (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        lot_no         TEXT NOT NULL,
        sub_lt         INTEGER,
        movement_type  TEXT NOT NULL,
        qty_kg         REAL DEFAULT 0,
        from_location  TEXT,
        to_location    TEXT,
        customer       TEXT,
        reason_code    TEXT,
        operator       TEXT DEFAULT 'system',
        remarks        TEXT,
        created_at     TEXT DEFAULT (datetime('now'))
    );
    CREATE TABLE IF NOT EXISTS move_batch (
        batch_id      TEXT PRIMARY KEY,
        status        TEXT NOT NULL DEFAULT 'PENDING',
        total_count   INTEGER DEFAULT 0,
        reason_code   TEXT DEFAULT 'RELOCATE',
        submitted_by  TEXT DEFAULT 'system',
        submitted_at  TEXT NOT NULL,
        approved_by   TEXT,
        approved_at   TEXT,
        items_json    TEXT,
        note          TEXT
    );
    CREATE TABLE IF NOT EXISTS allocation_plan (
        alloc_id    TEXT PRIMARY KEY,
        lot_no      TEXT,
        customer    TEXT,
        ship_date   TEXT,
        alloc_date  TEXT,
        qty_mt      REAL,
        status      TEXT DEFAULT 'APPROVED',
        export_type TEXT DEFAULT 'D',
        source      TEXT DEFAULT 'SCENARIO',
        line_no     INTEGER,
        workflow_status TEXT DEFAULT 'APPROVED',
        fail_code   TEXT
    );
    CREATE TABLE IF NOT EXISTS picking_list (
        pick_id     TEXT PRIMARY KEY,
        lot_no      TEXT,
        customer    TEXT,
        pick_date   TEXT,
        ship_date   TEXT,
        tonbag_count INTEGER,
        status      TEXT DEFAULT 'PICKED'
    );
    """)
    # ── 인덱스 (15,000 LOT 규모 대응) ────────────────────────────────────
    conn.executescript("""
    CREATE INDEX IF NOT EXISTS idx_tonbag_lot_no
        ON inventory_tonbag(lot_no);
    CREATE INDEX IF NOT EXISTS idx_tonbag_status
        ON inventory_tonbag(status);
    CREATE INDEX IF NOT EXISTS idx_tonbag_sample
        ON inventory_tonbag(is_sample);
    CREATE INDEX IF NOT EXISTS idx_inventory_status
        ON inventory(status);
    CREATE INDEX IF NOT EXISTS idx_inventory_arrival
        ON inventory(arrival_date);
    CREATE INDEX IF NOT EXISTS idx_allocation_lot
        ON allocation_plan(lot_no);
    CREATE INDEX IF NOT EXISTS idx_allocation_customer
        ON allocation_plan(customer);
    CREATE INDEX IF NOT EXISTS idx_outbound_lot
        ON outbound_log(lot_no);
    CREATE INDEX IF NOT EXISTS idx_outbound_customer
        ON outbound_log(customer);
    CREATE INDEX IF NOT EXISTS idx_picking_lot
        ON picking_list(lot_no);
    """)
    conn.commit()


def _insert_all(conn: sqlite3.Connection, scenario: Dict) -> None:
    conn.executemany(
        "INSERT OR REPLACE INTO vessel_master VALUES "
        "(:vessel_id,:carrier,:vessel_name,:voyage_no,:bl_no,:etd,:eta)",
        scenario['vessels']
    )
    conn.executemany(
        "INSERT OR REPLACE INTO container_master VALUES "
        "(:container_id,:container_no,:vessel_id,:voyage_no,:bl_no,:seal_no)",
        scenario['containers']
    )
    for lot in scenario['lots']:
        conn.execute(
            "INSERT OR REPLACE INTO inventory "
            "(lot_no,sap_no,container_id,container_no,vessel_id,voyage_no,bl_no,"
            "product,total_weight_kg,arrival_date,status,location,current_weight) VALUES "
            "(:lot_no,:sap_no,:container_id,:container_no,:vessel_id,:voyage_no,:bl_no,"
            ":product,:total_weight_kg,:arrival_date,:status,:location,:total_weight_kg)",
            lot
        )
    conn.executemany(
        "INSERT OR REPLACE INTO inventory_tonbag "
        "(lot_no,tonbag_no,tonbag_uid,is_sample,weight_kg,qty_mt,location,warehouse,status,arrival_date) VALUES "
        "(:lot_no,:tonbag_no,:tonbag_uid,:is_sample,:weight_kg,:qty_mt,:location,:warehouse,:status,:arrival_date)",
        scenario['tonbags']
    )
    conn.executemany(
        "INSERT OR REPLACE INTO outbound_log VALUES "
        "(:outbound_id,:lot_no,:customer,:ship_date,:weight_kg,:qty_mt,:status)",
        scenario['outbounds']
    )
    conn.executemany(
        "INSERT OR REPLACE INTO return_log VALUES "
        "(:return_id,:outbound_id,:lot_no,:customer,:return_date,:reason,:weight_kg,"
        ":processed_as,:new_location,:operator_id)",
        scenario['returns']
    )
    # v6.6.0: location_move_log → stock_movement.RELOCATE 통합
    conn.executemany(
        "INSERT INTO stock_movement "
        "(lot_no, movement_type, qty_kg, from_location, to_location, "
        " reason_code, remarks, created_at) "
        "VALUES (:lot_no,'RELOCATE',0,:from_location,:to_location,"
        "        :reason,:reason,:move_date)",
        scenario['moves']
    )
    for i, a in enumerate(scenario['allocations'], 1):
        a['line_no'] = i
        conn.execute(
            "INSERT OR REPLACE INTO allocation_plan "
            "(alloc_id,lot_no,customer,ship_date,alloc_date,qty_mt,status,export_type,source,line_no,workflow_status) VALUES "
            "(:alloc_id,:lot_no,:customer,:ship_date,:alloc_date,:qty_mt,:status,:export_type,:source,:line_no,:workflow_status)",
            a
        )
    conn.executemany(
        "INSERT OR REPLACE INTO picking_list VALUES "
        "(:pick_id,:lot_no,:customer,:pick_date,:ship_date,:tonbag_count,:status)",
        scenario['picking']
    )
    conn.commit()


# ─── 대규모 성능 테스트용 데이터 생성 ────────────────────────────────────────
def build_large_scenario(target_lots: int = 15000) -> sqlite3.Connection:
    """
    연간 15,000 LOT 규모 성능 테스트용 DB 생성 (in-memory).

    APL 3항차 시나리오를 기반으로 target_lots개 LOT 생성.
    톤백: target_lots × 11 레코드 (10개 + 샘플 1개)

    Args:
        target_lots: 목표 LOT 수 (기본 15,000)

    Returns:
        sqlite3.Connection (in-memory, WAL, 인덱스 포함)
    """
    import time as _time
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=OFF")   # 성능 우선 (메모리 DB)
    conn.execute("PRAGMA cache_size=-64000") # 64MB
    conn.execute("PRAGMA temp_store=MEMORY")
    _create_tables(conn)

    # 배치 INSERT (1000 LOT 단위)
    BATCH = 1000

    lot_rows  = []
    tb_rows   = []

    for seq in range(1, target_lots + 1):
        lot_no  = f"112{seq:07d}"
        loc     = f"A-{(seq%20+1):02d}-{(seq%10+1):02d}-{(seq%5+1):02d}"
        arrival = f"2026-{((seq-1)//1250+1):02d}-{((seq-1)%28+1):02d}"
        if len(arrival) < 10:
            arrival = f"2026-01-{((seq-1)%28+1):02d}"

        lot_rows.append((
            lot_no, f"2026{seq:06d}", f"CTR{(seq%15+1):03d}",
            f"APLU{(seq%15):07d}", f"VSL{(seq%3+1):03d}",
            f"APL-V{(seq%3+1):03d}", f"APLSIN{(seq%3+1):04d}26",
            PRODUCT, LOT_TOTAL_WEIGHT_KG, arrival,
            'AVAILABLE', loc, LOT_TOTAL_WEIGHT_KG
        ))

        for tb in range(1, TONBAGS_PER_LOT + 1):
            tb_rows.append((
                lot_no, f"{tb:03d}", f"{lot_no}-{tb:03d}",
                0, TONBAG_WEIGHT_KG, TONBAG_WEIGHT_KG / 1000,
                loc, loc[0], 'AVAILABLE', arrival
            ))
        tb_rows.append((
            lot_no, 'S00', f"{lot_no}-S00",
            1, SAMPLE_WEIGHT_KG, SAMPLE_WEIGHT_KG / 1000,
            loc, loc[0], 'AVAILABLE', arrival
        ))

        # 배치 flush
        if seq % BATCH == 0 or seq == target_lots:
            conn.executemany(
                "INSERT OR REPLACE INTO inventory "
                "(lot_no,sap_no,container_id,container_no,vessel_id,voyage_no,bl_no,"
                "product,total_weight_kg,arrival_date,status,location,current_weight) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                lot_rows
            )
            conn.executemany(
                "INSERT OR REPLACE INTO inventory_tonbag "
                "(lot_no,tonbag_no,tonbag_uid,is_sample,weight_kg,qty_mt,"
                "location,warehouse,status,arrival_date) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                tb_rows
            )
            conn.commit()
            lot_rows.clear()
            tb_rows.clear()

    return conn


# ─── 운영 DB 마이그레이션 (ALTER TABLE) ─────────────────────────────────────
def migrate_return_log(conn: sqlite3.Connection) -> dict:
    """
    기존 운영 DB의 return_log 테이블에 RETURN_AS_REINBOUND 정책 컬럼 추가.

    추가 컬럼:
      - processed_as  TEXT DEFAULT 'REINBOUND'
      - new_location  TEXT
      - operator_id   TEXT DEFAULT 'SYSTEM'

    이미 컬럼이 있으면 건너뜀 (멱등성 보장).

    Returns:
        {'added': [...], 'skipped': [...], 'ok': True}
    """
    existing = {
        row[1] for row in conn.execute("PRAGMA table_info(return_log)").fetchall()
    }
    new_cols = [
        ("processed_as", "TEXT DEFAULT 'REINBOUND'"),
        ("new_location",  "TEXT"),
        ("operator_id",   "TEXT DEFAULT 'SYSTEM'"),
    ]
    added, skipped = [], []
    for col_name, col_def in new_cols:
        if col_name in existing:
            skipped.append(col_name)
        else:
            conn.execute(
                f"ALTER TABLE return_log ADD COLUMN {col_name} {col_def}"
            )
            added.append(col_name)
    # 기존 row에 기본값 채우기
    if added:
        conn.execute(
            "UPDATE return_log SET processed_as='REINBOUND' "
            "WHERE processed_as IS NULL"
        )
        conn.execute(
            "UPDATE return_log SET operator_id='SYSTEM' "
            "WHERE operator_id IS NULL"
        )
        conn.commit()
    return {'added': added, 'skipped': skipped, 'ok': True}
