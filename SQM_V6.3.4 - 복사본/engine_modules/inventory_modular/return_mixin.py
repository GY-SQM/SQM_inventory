"""
SQM Inventory Engine - Return Mixin
===================================

v2.9.91 - Extracted from inventory.py

Return (반품) processing functions
"""

import json
import logging
import sqlite3
from datetime import date, datetime
from typing import Dict, List

logger = logging.getLogger(__name__)


class ReturnMixin:
    """
    Return processing mixin
    
    Methods for processing returns (PICKED -> AVAILABLE)
    """

    def get_returnable_tonbags(self, lot_no: str = None) -> List[Dict]:
        """
        Get tonbags that can be returned.
        
        Args:
            lot_no: Optional filter by LOT number
            
        Returns:
            List of returnable tonbags
        """
        query = """
            SELECT 
                t.lot_no, t.sub_lt, t.weight, t.location,
                t.status, t.outbound_date, t.picked_to, t.sale_ref,
                i.sap_no, i.bl_no, i.product
            FROM inventory_tonbag t
            LEFT JOIN inventory i ON t.lot_no = i.lot_no
            WHERE t.status IN ('PICKED', 'CONFIRMED', 'SHIPPED', 'SOLD', 'RESERVED')
        """
        params = []

        if lot_no:
            query += " AND t.lot_no = ?"
            params.append(lot_no)

        query += " ORDER BY t.lot_no, t.sub_lt"

        return self.db.fetchall(query, tuple(params))

    def get_return_history(self, lot_no: str = None, limit: int = 100) -> List[Dict]:
        """
        Get return history
        
        Args:
            lot_no: Optional filter by LOT number
            limit: Maximum records to return
            
        Returns:
            List of return records
        """
        query = """
            SELECT 
                r.id, r.lot_no, r.sub_lt, r.return_date,
                r.original_customer, r.original_sale_ref,
                r.reason, r.remark, r.created_at,
                i.sap_no, i.product
            FROM return_history r
            LEFT JOIN inventory i ON r.lot_no = i.lot_no
            WHERE 1=1
        """
        params = []

        if lot_no:
            query += " AND r.lot_no = ?"
            params.append(lot_no)

        query += f" ORDER BY r.created_at DESC LIMIT {limit}"

        return self.db.fetchall(query, tuple(params))

    def process_return(self, return_data: list,
                       source_type: str = '', source_file: str = '') -> Dict:
        """
        반품 처리 (v5.1.5: 정합성 게이트 + stock_movement 이력 + picked_date 초기화)
        
        Args:
            return_data: List of return items
                [{'lot_no': '...', 'sub_lt': 1, 'reason': '...', 'remark': '...'}, ...]
            source_type: 반품 출처 ('RETURN_SINGLE', 'RETURN_EXCEL', 'RETURN_PASTE')
            source_file: 원본 파일명 (감사 추적용)
            
        Returns:
            Processing result dict
        """
        result = {
            'success': False,
            'returned': 0,
            'skipped': 0,
            'errors': [],
            'details': [],
            'integrity': {},  # v5.1.5: LOT별 정합성 결과
        }

        if not return_data:
            result['errors'].append("No return data provided")
            return result

        try:
            with self.db.transaction("IMMEDIATE"):
                for item in return_data:
                    lot_no = str(item.get('lot_no') or '').strip()
                    sub_lt = item.get('sub_lt')
                    reason = item.get('reason', '')
                    remark = item.get('remark', '')

                    if not lot_no or sub_lt is None:
                        result['errors'].append(f"Invalid item: {item}")
                        result['skipped'] += 1
                        continue

                    # Get current tonbag info
                    tonbag = self.db.fetchone("""
                        SELECT lot_no, sub_lt, weight, status, picked_to, sale_ref, is_sample 
                        FROM inventory_tonbag 
                        WHERE lot_no = ? AND sub_lt = ?
                    """, (lot_no, sub_lt))

                    if not tonbag:
                        result['errors'].append(f"Tonbag not found: {lot_no}-{sub_lt}")
                        result['skipped'] += 1
                        continue

                    # v6.12.1: sqlite3.Row → dict 변환 (.get() 호환)
                    if not isinstance(tonbag, dict):
                        tonbag = dict(tonbag)

                    if tonbag['status'] not in ('PICKED', 'CONFIRMED', 'SHIPPED', 'SOLD', 'RESERVED'):
                        result['errors'].append(
                            f"Cannot return tonbag with status {tonbag['status']}: {lot_no}-{sub_lt}"
                        )
                        result['skipped'] += 1
                        continue

                    tb_weight = float(tonbag['weight'] or 0)

                    # Save return history
                    self.db.execute("""
                        INSERT INTO return_history 
                        (lot_no, sub_lt, return_date, original_customer, 
                         original_sale_ref, reason, remark, weight_kg)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        lot_no, sub_lt, date.today(),
                        tonbag['picked_to'], tonbag.get('sale_ref', ''),
                        reason, remark, tb_weight
                    ))

                    # v5.1.5: stock_movement 이력 추가 (반품)
                    # v6.12.1: source_type, source_file 추가
                    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    _src = source_type or 'RETURN_SINGLE'
                    self.db.execute("""
                        INSERT INTO stock_movement 
                        (lot_no, movement_type, qty_kg, remarks, source_type, source_file, created_at)
                        VALUES (?, 'RETURN', ?, ?, ?, ?, ?)
                    """, (lot_no, tb_weight,
                          f"sub_lt={sub_lt}, customer={tonbag.get('picked_to','')}, reason={reason}",
                          _src, source_file or '', now))

                    was_reserved = tonbag['status'] == 'RESERVED'
                    was_status = tonbag['status']  # v6.0.1: 반품 전 상태 보존

                    # v5.1.5: 톤백 상태 초기화 (picked_date도 포함)
                    self.db.execute("""
                        UPDATE inventory_tonbag 
                        SET status = 'AVAILABLE',
                            outbound_date = NULL,
                            picked_date = NULL,
                            picked_to = NULL,
                            sale_ref = NULL,
                            updated_at = ?
                        WHERE lot_no = ? AND sub_lt = ?
                    """, (now, lot_no, sub_lt))

                    # v5.9.3: RESERVED였으면 allocation_plan도 CANCELLED 처리
                    if was_reserved:
                        try:
                            self.db.execute("""
                                UPDATE allocation_plan SET status = 'CANCELLED', cancelled_at = ?
                                WHERE lot_no = ? AND sub_lt = ? AND status = 'RESERVED'
                            """, (now, lot_no, sub_lt))
                        except (sqlite3.OperationalError, ValueError, TypeError) as _e:
                            logger.debug(f"Suppressed: {_e}")
                    else:
                        # PICKED/SOLD: inventory current_weight 복구
                        self.db.execute("""
                            UPDATE inventory 
                            SET current_weight = current_weight + ?,
                                picked_weight = MAX(0, picked_weight - ?),
                                updated_at = ?
                            WHERE lot_no = ?
                        """, (tb_weight, tb_weight, now, lot_no))

                    # v6.0.1 패치: picking_table RETURNED
                    if was_status in ('PICKED', 'SOLD'):
                        try:
                            self.db.execute(
                                "UPDATE picking_table SET status='RETURNED', sold_date=? "
                                "WHERE lot_no=? AND sub_lt=? AND status IN ('ACTIVE','SOLD')",
                                (now, lot_no, sub_lt))
                        except (sqlite3.OperationalError, ValueError, TypeError) as _pe:
                            logger.debug(f"[v6.0.1] picking_table RETURNED 스킵: {_pe}")
                    # v6.0.1 패치: sold_table RETURNED
                    if was_status == 'SOLD':
                        try:
                            self.db.execute(
                                "UPDATE sold_table SET status='RETURNED', "
                                "remark=COALESCE(remark,'')||? "
                                "WHERE lot_no=? AND sub_lt=? AND status='SOLD'",
                                (f" | 반품:{now} 사유:{reason}", lot_no, sub_lt))
                        except (sqlite3.OperationalError, ValueError, TypeError) as _se:
                            logger.debug(f"[v6.0.1] sold_table RETURNED 스킵: {_se}")
                    # v6.2.2: 반품 후 문서 연계 점검용 감사 이력
                    self._log_return_doc_review_audit(
                        lot_no=lot_no,
                        sub_lt=sub_lt,
                        reason=reason,
                        source_type=_src,
                        source_file=source_file,
                    )

                    result['returned'] += 1
                    result['details'].append({
                        'lot_no': lot_no,
                        'sub_lt': sub_lt,
                        'weight': tb_weight,
                        'original_customer': tonbag.get('picked_to', '')
                    })

                    logger.info(f"Returned: {lot_no}-{sub_lt} ({tb_weight:.0f}kg)")

                # v5.2.0: 반품된 모든 LOT의 status 재계산 (래퍼 제거 → 직접 호출)
                returned_lots = set(d['lot_no'] for d in result['details'])
                for rlt in returned_lots:
                    self._recalc_lot_status(rlt)
                    logger.info(f"LOT status 재계산(반품): {rlt}")

                # v5.1.5: 정합성 검증 (트랜잭션 안에서)
                if hasattr(self, 'verify_lot_integrity') and returned_lots:
                    for rlt in returned_lots:
                        integrity = self.verify_lot_integrity(rlt)
                        result['integrity'][rlt] = integrity
                        if not integrity.get('valid', True):
                            raise ValueError(
                                f"반품 후 정합성 실패 ({rlt}): {integrity.get('errors', [])}"
                            )

                result['success'] = result['returned'] > 0

        except (ValueError, TypeError, AttributeError,
                sqlite3.OperationalError, sqlite3.IntegrityError) as e:
            result['errors'].append(f"Return processing error: {e}")
            logger.exception("Return processing error")

        return result

    def _log_return_doc_review_audit(
        self, lot_no: str, sub_lt: int, reason: str = "",
        source_type: str = "", source_file: str = ""
    ) -> None:
        """
        반품 시점의 문서 연계 정보 스냅샷을 stock_movement에 기록.
        - 자동 문서 수정은 하지 않고, 점검 필요 근거를 남긴다.
        """
        try:
            inv = self.db.fetchone(
                "SELECT sap_no, bl_no, salar_invoice_no FROM inventory WHERE lot_no = ? LIMIT 1",
                (lot_no,),
            ) or {}
            sold = self.db.fetchone(
                """
                SELECT id, picking_no, sales_order_no, sap_no, bl_no, customer, sold_date
                FROM sold_table
                WHERE lot_no = ? AND sub_lt = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (lot_no, sub_lt),
            ) or {}
            pick = self.db.fetchone(
                """
                SELECT id, picking_no, sales_order_no, outbound_id, customer, sold_date
                FROM picking_table
                WHERE lot_no = ? AND sub_lt = ?
                ORDER BY id DESC
                LIMIT 1
                """,
                (lot_no, sub_lt),
            ) or {}

            details = {
                "lot_no": lot_no,
                "sub_lt": int(sub_lt) if sub_lt is not None else None,
                "reason": reason or "",
                "inventory": {
                    "sap_no": str(inv.get("sap_no", "") or ""),
                    "bl_no": str(inv.get("bl_no", "") or ""),
                    "invoice_no": str(inv.get("salar_invoice_no", "") or ""),
                },
                "sold_table": {
                    "id": sold.get("id"),
                    "picking_no": str(sold.get("picking_no", "") or ""),
                    "sales_order_no": str(sold.get("sales_order_no", "") or ""),
                    "sap_no": str(sold.get("sap_no", "") or ""),
                    "bl_no": str(sold.get("bl_no", "") or ""),
                    "customer": str(sold.get("customer", "") or ""),
                    "sold_date": str(sold.get("sold_date", "") or ""),
                },
                "picking_table": {
                    "id": pick.get("id"),
                    "picking_no": str(pick.get("picking_no", "") or ""),
                    "sales_order_no": str(pick.get("sales_order_no", "") or ""),
                    "outbound_id": str(pick.get("outbound_id", "") or ""),
                    "customer": str(pick.get("customer", "") or ""),
                    "sold_date": str(pick.get("sold_date", "") or ""),
                },
                "action_required": "Review D/O, Invoice, B/L linkage after return",
            }
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            movement_type = 'RETURN_DOC_REVIEW'
            remarks = f"return doc linkage review required: lot={lot_no}, sub_lt={sub_lt}"
            ref_id = sold.get("id") or pick.get("id")
            ref_table = "sold_table" if sold.get("id") else ("picking_table" if pick.get("id") else "inventory")
            self.db.execute(
                """
                INSERT INTO stock_movement
                (lot_no, movement_type, qty_kg, remarks, source_type, source_file, ref_table, ref_id, details_json, created_at)
                VALUES (?, ?, 0, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    lot_no, movement_type, remarks, source_type or 'RETURN_SINGLE', source_file or '',
                    ref_table, ref_id, json.dumps(details, ensure_ascii=False), now,
                ),
            )
        except (sqlite3.OperationalError, ValueError, TypeError, KeyError, AttributeError) as e:
            logger.debug(f"[return-doc-audit] 스킵: {e}")

    def return_single_tonbag(self, lot_no: str, sub_lt: int,
                             reason: str = None, remark: str = None) -> Dict:
        """
        Return a single tonbag
        
        Args:
            lot_no: LOT number
            sub_lt: Sub LOT number
            reason: Return reason
            remark: Additional remarks
            
        Returns:
            Result dict
        """
        return self.process_return([{
            'lot_no': lot_no,
            'sub_lt': sub_lt,
            'reason': reason or '',
            'remark': remark or ''
        }])

    def bulk_return_by_lot(self, lot_no: str, reason: str = None) -> Dict:
        """
        Return all returnable tonbags for a LOT.
        
        Args:
            lot_no: LOT number
            reason: Return reason
            
        Returns:
            Result dict
        """
        # Get all returnable tonbags for this lot
        picked = self.db.fetchall("""
            SELECT lot_no, sub_lt FROM inventory_tonbag
            WHERE lot_no = ? AND status IN ('PICKED', 'CONFIRMED', 'SHIPPED', 'SOLD', 'RESERVED')
        """, (lot_no,))

        if not picked:
            return {
                'success': False,
                'returned': 0,
                'errors': [f"No returnable tonbags found for LOT: {lot_no}"]
            }

        return_data = [
            {'lot_no': row['lot_no'], 'sub_lt': row['sub_lt'], 'reason': reason or ''}
            for row in picked
        ]

        return self.process_return(
            return_data,
            source_type='RETURN_BULK',
            source_file=''
        )

    def get_return_statistics(self, start_date: str = '', end_date: str = '',
                              lot_no: str = '') -> Dict:
        """
        v6.12.1: 반품 사유 통계 리포트.

        Args:
            start_date: 시작일 (YYYY-MM-DD, 빈값=전체)
            end_date: 종료일 (YYYY-MM-DD, 빈값=전체)
            lot_no: LOT 필터 (빈값=전체)

        Returns:
            {
                'total_count': int,
                'total_weight_kg': float,
                'by_reason': [{'reason': str, 'count': int, 'weight_kg': float}, ...],
                'by_lot': [{'lot_no': str, 'count': int, 'weight_kg': float, 'reasons': str}, ...],
                'by_month': [{'month': str, 'count': int, 'weight_kg': float}, ...],
                'top_customers': [{'customer': str, 'count': int}, ...],
            }
        """
        result = {
            'total_count': 0,
            'total_weight_kg': 0.0,
            'by_reason': [],
            'by_lot': [],
            'by_month': [],
            'top_customers': [],
        }
        try:
            where_parts = ['1=1']
            params = []
            if start_date:
                where_parts.append("return_date >= ?")
                params.append(start_date)
            if end_date:
                where_parts.append("return_date <= ?")
                params.append(end_date)
            if lot_no:
                where_parts.append("lot_no = ?")
                params.append(lot_no)
            where = ' AND '.join(where_parts)

            # 전체 합계
            row = self.db.fetchone(
                f"SELECT COUNT(*) AS cnt, COALESCE(SUM(weight_kg), 0) AS total "
                f"FROM return_history WHERE {where}", tuple(params))
            if row:
                result['total_count'] = row['cnt'] if isinstance(row, dict) else row[0]
                result['total_weight_kg'] = float(row['total'] if isinstance(row, dict) else row[1])

            # 사유별 집계
            rows = self.db.fetchall(
                f"""SELECT COALESCE(reason, '미기재') AS reason,
                           COUNT(*) AS cnt,
                           COALESCE(SUM(weight_kg), 0) AS total
                    FROM return_history WHERE {where}
                    GROUP BY COALESCE(reason, '미기재')
                    ORDER BY cnt DESC""", tuple(params))
            result['by_reason'] = [
                {'reason': r['reason'], 'count': r['cnt'],
                 'weight_kg': float(r['total'])}
                for r in rows
            ]

            # LOT별 집계
            rows = self.db.fetchall(
                f"""SELECT lot_no, COUNT(*) AS cnt,
                           COALESCE(SUM(weight_kg), 0) AS total,
                           GROUP_CONCAT(DISTINCT reason) AS reasons
                    FROM return_history WHERE {where}
                    GROUP BY lot_no ORDER BY cnt DESC LIMIT 50""", tuple(params))
            result['by_lot'] = [
                {'lot_no': r['lot_no'], 'count': r['cnt'],
                 'weight_kg': float(r['total']),
                 'reasons': r['reasons'] or ''}
                for r in rows
            ]

            # 월별 추이
            rows = self.db.fetchall(
                f"""SELECT SUBSTR(return_date, 1, 7) AS month,
                           COUNT(*) AS cnt,
                           COALESCE(SUM(weight_kg), 0) AS total
                    FROM return_history WHERE {where}
                    GROUP BY SUBSTR(return_date, 1, 7)
                    ORDER BY month""", tuple(params))
            result['by_month'] = [
                {'month': r['month'] or '?', 'count': r['cnt'],
                 'weight_kg': float(r['total'])}
                for r in rows
            ]

            # 고객별 반품 건수 Top 10
            rows = self.db.fetchall(
                f"""SELECT COALESCE(original_customer, '미기재') AS customer,
                           COUNT(*) AS cnt
                    FROM return_history WHERE {where}
                    GROUP BY COALESCE(original_customer, '미기재')
                    ORDER BY cnt DESC LIMIT 10""", tuple(params))
            result['top_customers'] = [
                {'customer': r['customer'], 'count': r['cnt']}
                for r in rows
            ]

        except (sqlite3.OperationalError, ValueError, TypeError,
                AttributeError, KeyError) as e:
            logger.error(f"[get_return_statistics] 오류: {e}", exc_info=True)

        return result
