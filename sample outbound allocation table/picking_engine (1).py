# -*- coding: utf-8 -*-
"""
SQM v6.0.0 — Picking List 처리 엔진
======================================

Picking List PDF 파싱 결과를 받아
inventory_tonbag 상태를 RESERVED → PICKED 로 전환하고
picking_table에 이력을 기록한다.

비즈니스 규칙:
    - LOT 단위 처리 (Batch number = lot_no)
    - RESERVED 상태인 톤백만 PICKED 전환 대상
    - qty_kg 기준으로 필요한 개수만큼만 PICKED
      나머지는 RESERVED 자동 유지
    - 샘플 톤백(is_sample=1)은 별도 처리
    - All-or-Nothing 트랜잭션 (실패 시 전체 롤백)
    - 동일 picking_no 중복 업로드 → 경고 후 사용자 선택

사용 예:
    engine = PickingEngine(db)
    result = engine.process(parsed_result, source_file="picking.pdf")
    # result["picked"]   → 성공 처리 톤백 수
    # result["warnings"] → 경고 메시지 목록
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# 톤백 1개 표준 중량 (kg)
TONBAG_WEIGHT_KG = 500.0
SAMPLE_WEIGHT_KG = 1.0


class PickingEngine:
    """
    Picking List 파싱 결과 → DB 반영 엔진
    SQMDatabase 인스턴스를 주입받아 사용
    """

    def __init__(self, db):
        """
        Args:
            db: SQMDatabase 인스턴스 (execute/fetchall/fetchone/commit/rollback)
        """
        self.db = db

    # ─────────────────────────────────────────
    # 메인: 중복 체크 → 처리
    # ─────────────────────────────────────────
    def check_duplicate(self, picking_no: str) -> dict:
        """
        동일 picking_no가 이미 처리됐는지 확인
        Returns:
            {"exists": bool, "count": int, "first_date": str}
        """
        rows = self.db.fetchall(
            """
            SELECT COUNT(*) as cnt,
                   MIN(picking_date) as first_date
            FROM picking_table
            WHERE picking_no = ?
            """,
            (picking_no,)
        )
        row = rows[0] if rows else {}
        cnt = row.get("cnt", 0) or 0
        return {
            "exists"    : cnt > 0,
            "count"     : cnt,
            "first_date": row.get("first_date"),
        }

    def process(self, parsed: dict, source_file: str = "") -> dict:
        """
        Picking List 파싱 결과 → picking_table INSERT + tonbag PICKED 전환

        Args:
            parsed    : PickingListParser.parse() 반환값
            source_file: 원본 PDF 파일명

        Returns:
            {
                "success"          : bool,
                "picked"           : int,   # PICKED 전환된 톤백 수
                "sample_picked"    : int,   # 샘플 PICKED 수
                "skipped_lots"     : list,  # 매칭 실패 LOT 목록
                "partial_lots"     : list,  # 부분 처리된 LOT 목록
                "warnings"         : list,
                "picking_no"       : str,
            }
        """
        result = {
            "success"      : False,
            "picked"       : 0,
            "sample_picked": 0,
            "skipped_lots" : [],
            "partial_lots" : [],
            "warnings"     : list(parsed.get("warnings", [])),
            "picking_no"   : parsed.get("picking_no"),
        }

        if not parsed.get("parse_ok"):
            result["warnings"].append("❌ PDF 파싱 실패 — 처리 중단")
            return result

        items     = parsed.get("items", [])
        picking_no     = parsed.get("picking_no", "")
        sales_order_no = parsed.get("sales_order_no", "")
        outbound_id    = parsed.get("outbound_id", "")
        customer       = parsed.get("customer", "")
        plan_loading   = parsed.get("plan_loading_date", "")
        creation_date  = parsed.get("creation_date", "")

        try:
            # ── All-or-Nothing 트랜잭션 시작 ──
            for item in items:
                lot_no    = item["lot_no"]
                qty_kg    = item["qty_kg"]
                is_sample = item["is_sample"]

                if is_sample:
                    # 샘플 톤백 처리
                    n = self._process_sample(
                        lot_no, qty_kg, picking_no,
                        sales_order_no, outbound_id,
                        customer, plan_loading, creation_date,
                        source_file
                    )
                    result["sample_picked"] += n
                else:
                    # 일반 톤백 처리
                    n, partial, skipped = self._process_normal(
                        lot_no, qty_kg, picking_no,
                        sales_order_no, outbound_id,
                        customer, plan_loading, creation_date,
                        source_file
                    )
                    result["picked"] += n
                    if skipped:
                        result["skipped_lots"].append(lot_no)
                        result["warnings"].append(
                            f"⚠️ {lot_no}: RESERVED 톤백 없음 — 스킵"
                        )
                    elif partial:
                        result["partial_lots"].append(lot_no)
                        result["warnings"].append(
                            f"ℹ️ {lot_no}: {n}개 PICKED, "
                            f"잔여 {partial}개 RESERVED 유지"
                        )

            self.db.commit()
            result["success"] = True
            logger.info(
                f"[PickingEngine] 완료 — PICKED:{result['picked']} "
                f"샘플:{result['sample_picked']} "
                f"스킵:{len(result['skipped_lots'])}개"
            )

        except Exception as e:
            self.db.rollback()
            result["success"] = False
            result["warnings"].append(f"❌ 처리 중 오류 발생 (롤백): {e}")
            logger.error(f"[PickingEngine] 오류 → 롤백: {e}")

        return result

    # ─────────────────────────────────────────
    # 일반 톤백 처리 (MT 단위)
    # ─────────────────────────────────────────
    def _process_normal(
        self, lot_no: str, qty_kg: float,
        picking_no: str, sales_order_no: str,
        outbound_id: str, customer: str,
        plan_loading: str, creation_date: str,
        source_file: str
    ):
        """
        RESERVED 톤백 중 qty_kg 만큼 PICKED 전환

        Returns:
            (picked_count, remaining_reserved, is_skipped)
        """
        # RESERVED 톤백 조회 (sub_lt 오름차순)
        tonbags = self.db.fetchall(
            """
            SELECT id, lot_no, sub_lt, weight, tonbag_uid
            FROM inventory_tonbag
            WHERE lot_no = ? AND status = 'RESERVED'
            ORDER BY sub_lt ASC
            """,
            (lot_no,)
        )

        if not tonbags:
            return 0, 0, True  # 스킵

        remaining_kg  = qty_kg
        picked_count  = 0

        for tb in tonbags:
            if remaining_kg <= 0:
                break

            tb_weight = tb.get("weight") or TONBAG_WEIGHT_KG

            # inventory_tonbag → PICKED 전환
            self.db.execute(
                """
                UPDATE inventory_tonbag
                SET status      = 'PICKED',
                    picked_date  = datetime('now'),
                    pick_ref     = ?,
                    picking_no   = ?,
                    updated_at   = datetime('now')
                WHERE id = ?
                """,
                (picking_no, picking_no, tb["id"])
            )

            # picking_table INSERT
            self.db.execute(
                """
                INSERT INTO picking_table (
                    lot_no, tonbag_id, sub_lt, tonbag_uid,
                    picking_no, sales_order_no, outbound_id,
                    customer, plan_loading, creation_date,
                    source_file, qty_mt, qty_kg, unit,
                    is_sample, storage_location,
                    status, picking_date
                ) VALUES (
                    ?, ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?,
                    ?, ?, ?, ?,
                    ?, ?,
                    'ACTIVE', datetime('now')
                )
                """,
                (
                    lot_no, tb["id"], tb.get("sub_lt"), tb.get("tonbag_uid"),
                    picking_no, sales_order_no, outbound_id,
                    customer, plan_loading, creation_date,
                    source_file,
                    round(tb_weight / 1000.0, 4), tb_weight,
                    "MT", 0, "1001 GY logistics",
                )
            )

            remaining_kg -= tb_weight
            picked_count += 1

        # 잔여 RESERVED 수
        remaining_reserved = len(tonbags) - picked_count
        return picked_count, remaining_reserved, False

    # ─────────────────────────────────────────
    # 샘플 톤백 처리 (KG 단위)
    # ─────────────────────────────────────────
    def _process_sample(
        self, lot_no: str, qty_kg: float,
        picking_no: str, sales_order_no: str,
        outbound_id: str, customer: str,
        plan_loading: str, creation_date: str,
        source_file: str
    ) -> int:
        """
        샘플 톤백(is_sample=1) RESERVED → PICKED 전환
        샘플은 lot당 1개만 존재
        """
        tonbags = self.db.fetchall(
            """
            SELECT id, lot_no, sub_lt, weight, tonbag_uid
            FROM inventory_tonbag
            WHERE lot_no = ? AND status = 'RESERVED'
              AND (is_sample = 1 OR sub_lt = 0)
            LIMIT 1
            """,
            (lot_no,)
        )

        if not tonbags:
            logger.debug(f"[PickingEngine] 샘플 없음: {lot_no}")
            return 0

        tb = tonbags[0]

        # PICKED 전환
        self.db.execute(
            """
            UPDATE inventory_tonbag
            SET status     = 'PICKED',
                picked_date = datetime('now'),
                pick_ref    = ?,
                picking_no  = ?,
                updated_at  = datetime('now')
            WHERE id = ?
            """,
            (picking_no, picking_no, tb["id"])
        )

        # picking_table INSERT (샘플)
        self.db.execute(
            """
            INSERT INTO picking_table (
                lot_no, tonbag_id, sub_lt, tonbag_uid,
                picking_no, sales_order_no, outbound_id,
                customer, plan_loading, creation_date,
                source_file, qty_mt, qty_kg, unit,
                is_sample, storage_location,
                status, picking_date
            ) VALUES (
                ?, ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?,
                ?, ?, ?, ?,
                ?, ?,
                'ACTIVE', datetime('now')
            )
            """,
            (
                lot_no, tb["id"], tb.get("sub_lt"), tb.get("tonbag_uid"),
                picking_no, sales_order_no, outbound_id,
                customer, plan_loading, creation_date,
                source_file,
                round(qty_kg / 1000.0, 6), qty_kg,
                "KG", 1, "1001 GY logistics",
            )
        )
        return 1
