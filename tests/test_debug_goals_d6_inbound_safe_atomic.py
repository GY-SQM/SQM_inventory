# -*- coding: utf-8 -*-
"""D6 회귀 테스트 — 복수 LOT 입고 시 하나라도 실패하면 전체 롤백한다 (All-or-Nothing)."""
import sqlite3
import pytest
from engine_modules.inventory_modular.engine import SQMInventoryEngineV3
from parsers.document_models import PackingListData, LOTInfo

@pytest.fixture
def engine(tmp_path):
    db_path = str(tmp_path / "test_sqm_d6.db")
    engine = SQMInventoryEngineV3(db_path)
    return engine

def test_process_inbound_safe_rollbacks_everything_on_partial_failure(engine):
    # 2개의 LOT 준비
    lot1 = LOTInfo(list_no=1, lot_no='LOT-D6-1', net_weight_kg=1001.0, mxbg_pallet=2, container_no='C1')
    lot2 = LOTInfo(list_no=2, lot_no='LOT-D6-2', net_weight_kg=1001.0, mxbg_pallet=0, container_no='C2') # mxbg=0 이면 process_inbound에서 실패함 ([ZERO_BAGCOUNT])
    
    packing = PackingListData(
        lots=[lot1, lot2],
        sap_no='1234567890',
        product='LITHIUM CARBONATE'
    )
    # bl_no는 별도 데이터로 전달
    bl_data = {'bl_no': 'BL-D6'}
    
    # process_inbound_safe 호출
    # [BUG] 현재는 각 LOT에 대해 process_inbound를 호출하면서 개별 트랜잭션을 사용하거나 
    # 루프 중간에 실패해도 이전 LOT이 커밋되어 있을 수 있음 (또는 루프 자체가 없을 수도 있음 - 확인 필요)
    
    result = engine.process_inbound_safe(packing, bl_data=bl_data)
    
    assert result['success'] is False
    assert len(result['errors']) > 0
        
    # 검증: LOT-D6-1도 DB에 없어야 함 (전체 롤백)
    row = engine.db.fetchone("SELECT COUNT(*) as cnt FROM inventory WHERE lot_no='LOT-D6-1'")
    assert row['cnt'] == 0, "하나라도 실패하면 이전 성공 건도 롤백되어야 함 (All-or-Nothing)"

def test_process_inbound_safe_processes_all_lots_in_packing_data(engine):
    # 2개의 정상 LOT
    lot1 = LOTInfo(list_no=1, lot_no='LOT-D6-3', net_weight_kg=1001.0, mxbg_pallet=2, container_no='C3')
    lot2 = LOTInfo(list_no=2, lot_no='LOT-D6-4', net_weight_kg=1001.0, mxbg_pallet=2, container_no='C4')
    
    packing = PackingListData(
        lots=[lot1, lot2],
        sap_no='1234567890',
        product='LITHIUM CARBONATE'
    )
    bl_data = {'bl_no': 'BL-D6-OK'}
    
    result = engine.process_inbound_safe(packing, bl_data=bl_data)
    
    # [BUG 확인 필요] 현재 process_inbound_safe가 packing.lots 루프를 도는지 아니면 
    # packing_data 전체를 process_inbound에 던지는지 (보통 process_inbound는 단일 LOT 처리로 보임)
    
    assert result['success'] is True
    assert result['lots_created'] == 2, "PackingListData에 있는 모든 LOT이 생성되어야 함"
    
    # DB 확인
    assert engine.db.fetchone("SELECT COUNT(*) as cnt FROM inventory WHERE lot_no='LOT-D6-3'")['cnt'] == 1
    assert engine.db.fetchone("SELECT COUNT(*) as cnt FROM inventory WHERE lot_no='LOT-D6-4'")['cnt'] == 1
