# -*- coding: utf-8 -*-
"""
SQM v6.0.0 — Sales Order Excel 처리 엔진 (4단계)
===================================================

Sales Order Excel 파일을 파싱하고
picking_table에서 매칭된 톤백을 SOLD 처리한다.

비즈니스 규칙:
    - 매칭 기준: LOT NO + Picking No (둘 다 일치)
    - 개수 기준: CT/PLT 우선, 없으면 NW ÷ 500 역산
    - BL NO → sold_table에만 저장 (inventory 덮어쓰기 금지)
    - 중복 Sales Order → 경고 후 사용자 선택
    - 미매칭 LOT → sold_table에 PENDING 상태로 보관
    - 잔여 PICKED 존재 시 → 경고 반환 (GUI에서 팝업 표시)
    - All-or-Nothing 트랜잭션

사용 예:
    engine = SalesOrderEngine(db)

    # 중복 체크 먼저
    dup = engine.check_duplicate("3266")
    if dup["exists"]:
        # GUI에서 사용자에게 물어봄
        pass

    result = engine.process("Sales_order_3266.xlsx")
    # result["sold"]             → SOLD 처리 수
    # result["pending"]          → PENDING 보관 수
    # result["remaining_picked"] → 잔여 PICKED 수 (경고용)
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

TONBAG_WEIGHT_KG = 500.0  # 톤백 1개 기준 중량


# ─────────────────────────────────────────
# Sales Order Excel 파서
# ─────────────────────────────────────────

class SalesOrderParser:
    """
    Sales Order Excel 파일 파싱

    파일 구조:
        Row 0     : 빈 행
        Row 1     : "Sales order No : 3266"
        Row 2     : 날짜
        Row 3     : 합계 정보
        Row 4     : 컬럼 헤더
                    [Destination, Delivery Date, LOT NO, SAP NO,
                     BL NO, Sales order No, Picking No, SKU, NW, GW, CT/PLT]
        Row 5~    : 데이터

    반환:
    {
        "sales_order_no" : "3266",
        "parse_ok"       : True,
        "items": [
            {
                "lot_no"         : "1125072340",
                "picking_no"     : "LBM-LC20250901",
                "sap_no"         : "2200032685",
                "bl_no"          : "MAEU256915844",
                "customer"       : "LBM NEW ENERGY (AP)",
                "sku"            : "MIC9000",
                "delivery_date"  : "2026-02-09",
                "nw_kg"          : 5000.0,
                "ct_plt"         : 5,
                "is_sample"      : False,
            },
            ...
        ]
    }
    """

    def parse(self, file_path: str) -> dict:
        import pandas as pd
        result = {"sales_order_no": None, "parse_ok": False,
                  "items": [], "warnings": []}
        try:
            df = pd.read_excel(file_path, header=None, dtype=str)

            # Sales Order No 추출 (Row 1, Col 0)
            so_no = self._extract_so_no(df)
            result["sales_order_no"] = so_no

            # 헤더 행 찾기 (LOT NO 컬럼이 있는 행)
            header_row = self._find_header_row(df)
            if header_row is None:
                result["warnings"].append("❌ 헤더 행을 찾을 수 없음")
                return result

            # 헤더 기준으로 컬럼 매핑
            headers = [str(v).strip() if v and str(v) != 'nan' else ''
                       for v in df.iloc[header_row]]
            col = self._map_columns(headers)
            if not col:
                result["warnings"].append("❌ 필수 컬럼(LOT NO) 없음")
                return result

            # 데이터 파싱
            for idx in range(header_row + 1, len(df)):
                row = df.iloc[idx]
                lot_no = self._safe_str(row, col.get("LOT NO"))
                if not lot_no or not re.match(r"^\d{10,}$", lot_no):
                    continue  # 빈 행 또는 비정형 스킵

                picking_no    = self._safe_str(row, col.get("Picking No"))
                sap_no        = self._safe_str(row, col.get("SAP NO"))
                bl_no         = self._safe_str(row, col.get("BL NO"))
                customer      = self._safe_str(row, col.get("Destination"))
                sku           = self._safe_str(row, col.get("SKU"))
                delivery_date = self._safe_date(row, col.get("Delibery Date")
                                                or col.get("Delivery Date"))
                nw_kg         = self._safe_float(row, col.get("NW"))
                ct_plt        = self._safe_int(row, col.get("CT/PLT"))
                is_sample     = "(SP)" in (sku or "")

                result["items"].append({
                    "lot_no"        : lot_no,
                    "picking_no"    : picking_no,
                    "sap_no"        : sap_no,
                    "bl_no"         : bl_no,
                    "customer"      : customer,
                    "sku"           : sku,
                    "delivery_date" : delivery_date,
                    "nw_kg"         : nw_kg or 0.0,
                    "ct_plt"        : ct_plt or 0,
                    "is_sample"     : is_sample,
                })

            result["parse_ok"] = len(result["items"]) > 0
            logger.info(
                f"[SalesOrderParser] SO#{so_no} 파싱완료: "
                f"{len(result['items'])}행"
            )
        except Exception as e:
            result["warnings"].append(f"❌ 파싱 오류: {e}")
            logger.error(f"[SalesOrderParser] 오류: {e}")

        return result

    def _extract_so_no(self, df) -> Optional[str]:
        """Row 1에서 Sales Order No 추출"""
        try:
            cell = str(df.iloc[1, 0])
            m = re.search(r"(\d+)\s*$", cell)
            return m.group(1) if m else None
        except Exception:
            return None

    def _find_header_row(self, df) -> Optional[int]:
        """LOT NO 컬럼이 있는 헤더 행 번호 반환"""
        for i in range(min(10, len(df))):
            row_vals = [str(v).strip() for v in df.iloc[i]]
            if "LOT NO" in row_vals or "Lot No" in row_vals:
                return i
        return None

    def _map_columns(self, headers: list) -> dict:
        """헤더 목록 → 컬럼명:인덱스 매핑"""
        mapping = {}
        for i, h in enumerate(headers):
            mapping[h] = i
        return mapping

    def _safe_str(self, row, col_idx) -> Optional[str]:
        if col_idx is None:
            return None
        try:
            v = str(row.iloc[col_idx]).strip()
            return None if v in ("nan", "", "None") else v
        except Exception:
            return None

    def _safe_float(self, row, col_idx) -> Optional[float]:
        v = self._safe_str(row, col_idx)
        if v is None:
            return None
        try:
            return float(v.replace(",", ""))
        except ValueError:
            return None

    def _safe_int(self, row, col_idx) -> Optional[int]:
        v = self._safe_float(row, col_idx)
        return int(v) if v is not None else None

    def _safe_date(self, row, col_idx) -> Optional[str]:
        v = self._safe_str(row, col_idx)
        if not v:
            return None
        # "2026-02-09 00:00:00" → "2026-02-09"
        return v[:10] if len(v) >= 10 else v


# ─────────────────────────────────────────
# Sales Order 처리 엔진 (4·5단계)
# ─────────────────────────────────────────

class SalesOrderEngine:
    """
    Sales Order Excel → picking_table 매칭 → SOLD/PENDING 처리

    Returns:
    {
        "success"          : bool,
        "sales_order_no"   : str,
        "sold"             : int,     # SOLD 처리된 톤백 수
        "pending"          : int,     # PENDING 보관된 LOT 수
        "remaining_picked" : int,     # 처리 후 잔여 PICKED 수 (경고용)
        "skipped"          : list,    # 매칭 실패 상세 목록
        "warnings"         : list,
    }
    """

    def __init__(self, db):
        self.db = db

    # ── 중복 체크 ──
    def check_duplicate(self, sales_order_no: str) -> dict:
        """
        동일 Sales Order No가 이미 처리됐는지 확인
        Returns: {"exists": bool, "sold_count": int, "first_date": str}
        """
        rows = self.db.fetchall(
            """
            SELECT COUNT(*) as cnt, MIN(created_at) as first_date
            FROM sold_table
            WHERE sales_order_no = ? AND status != 'PENDING'
            """,
            (sales_order_no,)
        )
        row = rows[0] if rows else {}
        cnt = row.get("cnt", 0) or 0
        return {
            "exists"    : cnt > 0,
            "sold_count": cnt,
            "first_date": row.get("first_date"),
        }

    # ── 메인 처리 ──
    def process(self, file_path: str,
                sales_order_file: str = "") -> dict:
        """
        Sales Order Excel 파일 → SOLD/PENDING 처리

        Args:
            file_path        : Excel 파일 경로
            sales_order_file : 원본 파일명 (표시용)
        """
        import os
        if not sales_order_file:
            sales_order_file = os.path.basename(file_path)

        result = {
            "success"         : False,
            "sales_order_no"  : None,
            "sold"            : 0,
            "pending"         : 0,
            "remaining_picked": 0,
            "skipped"         : [],
            "warnings"        : [],
        }

        # ── 1. 파싱 ──
        parser = SalesOrderParser()
        parsed = parser.parse(file_path)

        if not parsed["parse_ok"]:
            result["warnings"].extend(parsed.get("warnings", []))
            result["warnings"].append("❌ Sales Order 파싱 실패")
            return result

        so_no  = parsed["sales_order_no"]
        items  = parsed["items"]
        result["sales_order_no"] = so_no
        result["warnings"].extend(parsed.get("warnings", []))

        # ── 2. 트랜잭션 처리 ──
        try:
            for item in items:
                self._process_item(
                    item, so_no, sales_order_file, result
                )

            self.db.commit()
            result["success"] = True

            # ── 3. 잔여 PICKED 집계 (5단계 경고용) ──
            result["remaining_picked"] = self._count_remaining_picked()

            logger.info(
                f"[SalesOrderEngine] SO#{so_no} 완료 — "
                f"SOLD:{result['sold']} "
                f"PENDING:{result['pending']} "
                f"잔여PICKED:{result['remaining_picked']}"
            )

        except Exception as e:
            self.db.rollback()
            result["success"]  = False
            result["warnings"].append(f"❌ 처리 오류 (롤백): {e}")
            logger.error(f"[SalesOrderEngine] 오류 → 롤백: {e}")

        return result

    def _process_item(self, item: dict, so_no: str,
                      so_file: str, result: dict) -> None:
        """
        LOT 1개 처리:
        picking_table 매칭 → SOLD 또는 PENDING
        """
        lot_no     = item["lot_no"]
        picking_no = item["picking_no"] or ""
        ct_plt     = item["ct_plt"]
        nw_kg      = item["nw_kg"]
        is_sample  = item["is_sample"]

        # ── 개수 산출 (CT/PLT 우선, 없으면 NW 역산) ──
        if ct_plt and ct_plt > 0:
            need_count = ct_plt
        elif nw_kg and nw_kg > 0:
            unit_w = 1.0 if is_sample else TONBAG_WEIGHT_KG
            need_count = max(1, round(nw_kg / unit_w))
        else:
            need_count = 1

        # ── picking_table에서 ACTIVE 톤백 조회 ──
        # 매칭 기준: lot_no + picking_no 둘 다 일치
        picking_rows = self.db.fetchall(
            """
            SELECT id, lot_no, tonbag_id, sub_lt, tonbag_uid,
                   qty_kg, is_sample
            FROM picking_table
            WHERE lot_no     = ?
              AND picking_no = ?
              AND status     = 'ACTIVE'
            ORDER BY id ASC
            LIMIT ?
            """,
            (lot_no, picking_no, need_count)
        )

        if not picking_rows:
            # ── PENDING 보관 ──
            self._insert_sold_pending(
                item, so_no, so_file, need_count
            )
            result["pending"] += 1
            result["skipped"].append({
                "lot_no"    : lot_no,
                "picking_no": picking_no,
                "reason"    : "picking_table 매칭 없음 (PENDING 보관)",
            })
            result["warnings"].append(
                f"⚠️ {lot_no} (PK:{picking_no}): "
                f"PICKED 없음 → PENDING 보관"
            )
            return

        # ── SOLD 처리 ──
        for pk_row in picking_rows:
            # picking_table → SOLD
            self.db.execute(
                """
                UPDATE picking_table
                SET status    = 'SOLD',
                    sold_date = datetime('now')
                WHERE id = ?
                """,
                (pk_row["id"],)
            )

            # inventory_tonbag → SOLD
            if pk_row.get("tonbag_id"):
                self.db.execute(
                    """
                    UPDATE inventory_tonbag
                    SET status       = 'SOLD',
                        outbound_date = datetime('now'),
                        sale_ref      = ?,
                        updated_at    = datetime('now')
                    WHERE id = ?
                    """,
                    (so_no, pk_row["tonbag_id"])
                )
                # inventory current_weight 차감
                qty_kg = pk_row.get("qty_kg") or TONBAG_WEIGHT_KG
                self.db.execute(
                    """
                    UPDATE inventory
                    SET current_weight = MAX(0, current_weight - ?),
                        updated_at     = datetime('now')
                    WHERE lot_no = ?
                    """,
                    (qty_kg, lot_no)
                )

            # sold_table INSERT (SOLD)
            self._insert_sold_record(
                item, so_no, so_file,
                pk_row["id"], pk_row.get("tonbag_id"),
                pk_row.get("sub_lt"), pk_row.get("tonbag_uid"),
                status="SOLD"
            )

            # stock_movement 기록
            self._insert_movement(lot_no, pk_row.get("qty_kg", 0), so_no)

            result["sold"] += 1

    def _insert_sold_pending(self, item: dict, so_no: str,
                             so_file: str, need_count: int) -> None:
        """PENDING 상태 sold_table 레코드 삽입"""
        self.db.execute(
            """
            INSERT INTO sold_table (
                lot_no, sales_order_no, sales_order_file,
                picking_no, sap_no, bl_no, customer, sku,
                delivery_date, sold_qty_mt, sold_qty_kg, ct_plt,
                status, created_at, created_by
            ) VALUES (
                ?, ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?,
                'PENDING', datetime('now'), 'system'
            )
            """,
            (
                item["lot_no"], so_no, so_file,
                item["picking_no"], item["sap_no"], item["bl_no"],
                item["customer"], item["sku"],
                item["delivery_date"],
                round((item["nw_kg"] or 0) / 1000.0, 4),
                item["nw_kg"] or 0,
                need_count,
            )
        )

    def _insert_sold_record(
        self, item: dict, so_no: str, so_file: str,
        picking_id: int, tonbag_id: Optional[int],
        sub_lt: Optional[int], tonbag_uid: Optional[str],
        status: str = "SOLD"
    ) -> None:
        """SOLD 상태 sold_table 레코드 삽입"""
        self.db.execute(
            """
            INSERT INTO sold_table (
                lot_no, tonbag_id, sub_lt, tonbag_uid, picking_id,
                sales_order_no, sales_order_file,
                picking_no, sap_no, bl_no, customer, sku,
                delivery_date, sold_qty_mt, sold_qty_kg, ct_plt,
                status, sold_date, created_at, created_by
            ) VALUES (
                ?, ?, ?, ?, ?,
                ?, ?,
                ?, ?, ?, ?, ?,
                ?, ?, ?, ?,
                ?, datetime('now'), datetime('now'), 'system'
            )
            """,
            (
                item["lot_no"], tonbag_id, sub_lt, tonbag_uid, picking_id,
                so_no, so_file,
                item["picking_no"], item["sap_no"], item["bl_no"],
                item["customer"], item["sku"],
                item["delivery_date"],
                round((item["nw_kg"] or 0) / 1000.0, 4),
                item["nw_kg"] or 0,
                item["ct_plt"] or 0,
                status,
            )
        )

    def _insert_movement(self, lot_no: str, qty_kg: float,
                         so_no: str) -> None:
        """stock_movement 출고 이력 기록"""
        try:
            self.db.execute(
                """
                INSERT INTO stock_movement
                    (lot_no, movement_type, qty_kg,
                     remarks, movement_date, created_at)
                VALUES (?, 'SOLD', ?, ?, datetime('now'), datetime('now'))
                """,
                (lot_no, qty_kg, f"SO#{so_no}")
            )
        except Exception as e:
            # stock_movement 없어도 메인 처리 중단 안 함
            logger.debug(f"[SalesOrderEngine] movement 기록 스킵: {e}")

    def _count_remaining_picked(self) -> int:
        """처리 후 잔여 PICKED 톤백 수 (5단계 경고용)"""
        try:
            rows = self.db.fetchall(
                "SELECT COUNT(*) as cnt FROM inventory_tonbag "
                "WHERE status = 'PICKED'"
            )
            return rows[0].get("cnt", 0) if rows else 0
        except Exception:
            return 0

    # ── PENDING 재처리 ──
    def retry_pending(self, sales_order_no: str) -> dict:
        """
        PENDING 상태 LOT를 다시 picking_table 매칭 시도
        Picking List가 뒤늦게 도착한 경우 사용
        """
        result = {"retried": 0, "newly_sold": 0, "still_pending": 0,
                  "warnings": []}
        try:
            pending_rows = self.db.fetchall(
                """
                SELECT id, lot_no, picking_no, sap_no, bl_no,
                       customer, sku, delivery_date,
                       sold_qty_kg, ct_plt,
                       sales_order_no, sales_order_file
                FROM sold_table
                WHERE sales_order_no = ? AND status = 'PENDING'
                """,
                (sales_order_no,)
            )

            for pr in pending_rows:
                result["retried"] += 1
                lot_no     = pr["lot_no"]
                picking_no = pr["picking_no"] or ""
                need_count = pr["ct_plt"] or 1

                picking_rows = self.db.fetchall(
                    """
                    SELECT id, tonbag_id, sub_lt, tonbag_uid, qty_kg
                    FROM picking_table
                    WHERE lot_no = ? AND picking_no = ?
                      AND status = 'ACTIVE'
                    ORDER BY id ASC LIMIT ?
                    """,
                    (lot_no, picking_no, need_count)
                )

                if picking_rows:
                    # PENDING → SOLD 전환
                    self.db.execute(
                        "UPDATE sold_table SET status='SOLD', "
                        "sold_date=datetime('now') WHERE id=?",
                        (pr["id"],)
                    )
                    for pk in picking_rows:
                        self.db.execute(
                            "UPDATE picking_table SET status='SOLD', "
                            "sold_date=datetime('now') WHERE id=?",
                            (pk["id"],)
                        )
                        if pk.get("tonbag_id"):
                            self.db.execute(
                                "UPDATE inventory_tonbag SET status='SOLD', "
                                "outbound_date=datetime('now') WHERE id=?",
                                (pk["tonbag_id"],)
                            )
                    result["newly_sold"] += 1
                else:
                    result["still_pending"] += 1

            self.db.commit()
            logger.info(
                f"[SalesOrderEngine] retry_pending SO#{sales_order_no}: "
                f"신규SOLD={result['newly_sold']} "
                f"여전히PENDING={result['still_pending']}"
            )
        except Exception as e:
            self.db.rollback()
            result["warnings"].append(f"❌ 재처리 오류: {e}")
            logger.error(f"[SalesOrderEngine] retry_pending 오류: {e}")

        return result
