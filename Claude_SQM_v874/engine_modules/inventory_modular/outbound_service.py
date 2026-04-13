# -*- coding: utf-8 -*-
"""
P2 Batch B — OutboundService
출고 비즈니스 파이프라인 오케스트레이션.
OutboundQueryRepository + OutboundWriteRepository + OutboundStateRules 조합.
outbound_mixin.py에서 위임받는 서비스 레이어.
"""
import logging

from engine_modules.inventory_modular.outbound_query import OutboundQueryRepository
from engine_modules.inventory_modular.outbound_repository import OutboundWriteRepository
from engine_modules.inventory_modular.outbound_state_rules import OutboundStateRules

logger = logging.getLogger(__name__)


class OutboundService:
    """출고 비즈니스 로직 파이프라인."""

    def __init__(self, db):
        """
        Args:
            db: SQMDatabase 인스턴스 (self.db)
        """
        self.db = db
        self.query = OutboundQueryRepository(db.conn if hasattr(db, 'conn') else db)
        self.writer = OutboundWriteRepository(db.conn if hasattr(db, 'conn') else db)
        self.rules = OutboundStateRules()

    # ── 위임 메서드: 조회 ─────────────────────────────────────────

    def table_exists(self, table_name: str) -> bool:
        return self.query.table_exists(table_name)

    def get_outbound_event_log(self, limit: int = 50) -> list:
        return self.query.get_outbound_event_log(limit)

    def get_outbound_status(self, outbound_no: str) -> str:
        return self.query.get_outbound_status(outbound_no)

    def get_alloc_plan_cols(self) -> set:
        return self.query.get_alloc_plan_cols()

    def has_source_fingerprint_column(self) -> bool:
        return self.query.has_source_fingerprint_column()

    def load_reserved_plans(self, lot_no=None, target_date=None) -> list:
        return self.query.load_reserved_plans(lot_no, target_date)

    def load_picked_tonbags(self, lot_no=None) -> list:
        return self.query.load_picked_tonbags(lot_no)

    def preflight_alloc_cols(self) -> dict:
        return self.query.preflight_alloc_cols()

    # ── 위임 메서드: 상태 규칙 ────────────────────────────────────

    def allocation_risk_flags(self, qty_kg, available_kg):
        return self.rules.allocation_risk_flags(qty_kg, available_kg)

    def allocation_requires_approval(self, qty_kg, available_kg):
        return self.rules.allocation_requires_approval(qty_kg, available_kg)

    def normalize_outbound_date(self, raw_date):
        return self.rules.normalize_outbound_date(raw_date)

    def get_allocation_random_mode(self):
        return self.rules.get_allocation_random_mode()

    def get_allocation_strict_mode(self):
        return self.rules.get_allocation_strict_mode()

    def get_allocation_reservation_mode(self, override=''):
        return self.rules.get_allocation_reservation_mode(override)

    def compute_lot_status(self, cnt_map, current_weight=0):
        return self.rules.compute_lot_status(cnt_map, current_weight)

    def build_allocation_seed(self, **kwargs):
        return self.rules.build_allocation_seed(**kwargs)

    def compute_source_fingerprint(self, rows, source_file=''):
        return self.rules.compute_allocation_source_fingerprint(rows, source_file)

    # ── 위임 메서드: 쓰기 ────────────────────────────────────────

    def ensure_outbound_txn_tables(self):
        self.writer.ensure_outbound_txn_tables()

    def update_lot_after_pick(self, lot_no, weight_kg):
        self.writer.update_lot_after_pick(lot_no, weight_kg)

    def insert_plan_row(self, payload, alloc_plan_cols):
        return self.writer.insert_plan_row(payload, alloc_plan_cols)
