# -*- coding: utf-8 -*-
"""
pytest 공통 fixture — :memory: SQLite DB 기반 격리 테스트
"""
import sys
import os
import pytest

# 프로젝트 루트를 sys.path에 추가
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from engine_modules.database import SQMDatabase


@pytest.fixture
def db():
    """격리된 :memory: DB 인스턴스를 제공한다.

    SQMDatabase(':memory:')는 init 시 _init_database()를 호출하므로
    모든 테이블·인덱스가 자동 생성된다.
    """
    database = SQMDatabase(':memory:')
    yield database
    # :memory: DB는 객체 소멸 시 자동 해제


@pytest.fixture
def seed_lot(db):
    """inventory + inventory_tonbag 기본 시드 데이터를 삽입하는 헬퍼를 제공."""

    def _seed(lot_no='1120000001', weight=500.0, status='AVAILABLE',
              sub_lt=1, tb_status=None):
        """
        Args:
            lot_no:    LOT 번호
            weight:    톤백 중량 (kg)
            status:    inventory 테이블 status
            sub_lt:    톤백 sub_lt
            tb_status: 톤백 status (None이면 inventory status와 동일)
        """
        tb_status = tb_status or status

        db.execute(
            "INSERT OR IGNORE INTO inventory "
            "(lot_no, product, net_weight, current_weight, status) "
            "VALUES (?, 'LITHIUM CARBONATE', ?, ?, ?)",
            (lot_no, weight, weight, status)
        )
        db.execute(
            "INSERT OR IGNORE INTO inventory_tonbag "
            "(lot_no, sub_lt, weight, status, is_sample) "
            "VALUES (?, ?, ?, ?, 0)",
            (lot_no, sub_lt, weight, tb_status)
        )
        db.conn.commit()
        return lot_no

    return _seed
