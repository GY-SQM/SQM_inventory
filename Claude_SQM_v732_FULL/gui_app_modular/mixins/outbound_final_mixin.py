# -*- coding: utf-8 -*-
"""
SQM v7.3.2.1 — 출고 확정 (PICKED->SOLD) 최종 처리 Mixin
=======================================================
Preflight 검증 → CONFIRM 다이얼로그 → 원자적 트랜잭션 실행.
"""
import logging
from ..utils.constants import tk
from datetime import datetime

from ..utils.ui_constants import ThemeColors
from ..utils.db_helper import fetchone, fetchall, get_conn

logger = logging.getLogger(__name__)


class OutboundFinalMixin:
    """PICKED -> SOLD 출고 확정 최종 처리."""

    def _on_outbound_finalize(self) -> None:
        """출고 확정 메인 진입: 선택 LOT -> 사전검증 -> 확인 -> 실행."""
        try:
            lot_no, tb_count = self._get_selected_lot_info()
            if not lot_no:
                from ..utils.constants import messagebox
                messagebox.showwarning(
                    "출고 확정",
                    "출고 확정할 LOT를 선택하세요.",
                    parent=getattr(self, 'root', None))
                return

            # 사전 검증
            ok, msg = self._preflight_check(lot_no, tb_count)
            if not ok:
                from ..utils.constants import messagebox
                messagebox.showerror(
                    "사전 검증 실패",
                    f"출고 확정 불가:\n{msg}",
                    parent=getattr(self, 'root', None))
                return

            # 추가 정보 조회
            info = fetchone(self,
                """SELECT customer, SUM(COALESCE(qty_kg, 0)) AS total_kg
                   FROM picking_table
                   WHERE lot_no = ? AND status = 'ACTIVE'
                   GROUP BY lot_no""",
                (lot_no,))
            customer = str(info.get('customer', '')) if info else ''
            weight = float(info.get('total_kg', 0) or 0) / 1000 if info else 0

            # CONFIRM 다이얼로그
            confirmed = False
            if hasattr(self, '_open_outbound_confirm'):
                confirmed = self._open_outbound_confirm(
                    lot_no=lot_no,
                    tonbag_cnt=tb_count,
                    weight_mt=weight,
                    customer=customer,
                    callback=None)
            else:
                from ..utils.constants import messagebox
                confirmed = messagebox.askyesno(
                    "출고 확정",
                    f"LOT {lot_no}를 출고 확정하시겠습니까?\n"
                    f"톤백 {tb_count}개, {weight:.1f} MT",
                    parent=getattr(self, 'root', None))

            if not confirmed:
                return

            # 실행
            result = self._execute_outbound_finalize(lot_no)
            if result.get('success'):
                from ..utils.constants import messagebox
                messagebox.showinfo(
                    "출고 확정 완료",
                    f"LOT {lot_no} 출고 확정 완료.\n"
                    f"처리 톤백: {result.get('count', 0)}개",
                    parent=getattr(self, 'root', None))

                # 탭 새로고침
                for fn in ('_refresh_picked', '_refresh_sold',
                           '_refresh_inventory', '_refresh_main_tabs'):
                    if hasattr(self, fn):
                        try:
                            getattr(self, fn)()
                        except Exception:
                            pass
            else:
                from ..utils.constants import messagebox
                messagebox.showerror(
                    "출고 확정 실패",
                    f"처리 중 오류:\n{result.get('error', '알 수 없는 오류')}",
                    parent=getattr(self, 'root', None))

        except Exception as e:
            logger.error(f"_on_outbound_finalize 오류: {e}")

    def _preflight_check(self, lot_no, tb_count) -> tuple:
        """4단계 사전 검증. (bool, msg) 반환."""
        try:
            # 1단계: LOT 존재
            lot_row = fetchone(self,
                "SELECT lot_no FROM picking_table WHERE lot_no = ? AND status = 'ACTIVE' LIMIT 1",
                (lot_no,))
            if not lot_row:
                return False, f"LOT {lot_no}의 ACTIVE 피킹 레코드가 없습니다."

            # 2단계: 톤백 수 확인
            cnt_row = fetchone(self,
                "SELECT COUNT(*) AS cnt FROM picking_table WHERE lot_no = ? AND status = 'ACTIVE'",
                (lot_no,))
            actual_cnt = int(cnt_row['cnt']) if cnt_row else 0
            if actual_cnt == 0:
                return False, "출고 대상 톤백이 0개입니다."

            # 3단계: 톤백 상태 확인 (inventory_tonbag)
            bad_row = fetchone(self,
                """SELECT COUNT(*) AS cnt FROM inventory_tonbag
                   WHERE lot_no = ? AND status NOT IN ('PICKED', 'RESERVED', 'AVAILABLE')""",
                (lot_no,))
            bad_cnt = int(bad_row['cnt']) if bad_row else 0
            if bad_cnt > 0:
                return False, f"출고 불가 상태 톤백 {bad_cnt}개 존재. 상태를 확인하세요."

            # 4단계: 중복 출고 방지
            sold_row = fetchone(self,
                """SELECT COUNT(*) AS cnt FROM picking_table
                   WHERE lot_no = ? AND status = 'SOLD'""",
                (lot_no,))
            sold_cnt = int(sold_row['cnt']) if sold_row else 0
            if sold_cnt > 0:
                return False, f"이미 출고 완료된 레코드가 {sold_cnt}건 있습니다."

            return True, "OK"

        except Exception as e:
            logger.error(f"_preflight_check 오류: {e}")
            return False, f"검증 중 오류: {e}"

    def _execute_outbound_finalize(self, lot_no) -> dict:
        """원자적 트랜잭션: PICKED -> SOLD."""
        try:
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            count = 0

            with get_conn(self) as conn:
                try:
                    conn.execute("BEGIN")

                    # picking_table: ACTIVE -> SOLD
                    cursor = conn.execute(
                        """UPDATE picking_table
                           SET status = 'SOLD', sold_date = ?
                           WHERE lot_no = ? AND status = 'ACTIVE'""",
                        (now, lot_no))
                    count = cursor.rowcount

                    # inventory_tonbag: PICKED -> SOLD
                    conn.execute(
                        """UPDATE inventory_tonbag
                           SET status = 'SOLD'
                           WHERE lot_no = ? AND status IN ('PICKED', 'RESERVED')""",
                        (lot_no,))

                    # inventory: 상태 업데이트
                    conn.execute(
                        """UPDATE inventory
                           SET status = 'SOLD'
                           WHERE lot_no = ? AND status IN ('PICKED', 'RESERVED')""",
                        (lot_no,))

                    # audit_log
                    conn.execute(
                        """INSERT INTO audit_log
                           (action_type, event_type, lot_no, detail)
                           VALUES (?, ?, ?, ?)""",
                        ('OUTBOUND_FINALIZE', 'PICKED_TO_SOLD', lot_no,
                         f"톤백 {count}개 출고 확정 ({now})"))

                    conn.commit()
                    logger.info(f"출고 확정 완료: LOT={lot_no}, 톤백={count}개")
                    return {'success': True, 'count': count}

                except Exception as e:
                    conn.rollback()
                    logger.error(f"출고 확정 트랜잭션 실패: {e}")
                    return {'success': False, 'error': str(e)}

        except Exception as e:
            logger.error(f"_execute_outbound_finalize 오류: {e}")
            return {'success': False, 'error': str(e)}

    def _get_selected_lot_info(self) -> tuple:
        """tree_picked에서 선택된 LOT 정보 반환. (lot_no, tb_count)."""
        try:
            tree = getattr(self, 'tree_picked', None)
            if not tree:
                return ('', 0)

            sel = tree.selection()
            if not sel:
                return ('', 0)

            item = tree.item(sel[0])
            vals = item.get('values', [])
            # PICKED_LOT_COLUMNS: row_num, lot_no, picking_no, customer, tonbag_count, total_kg, picking_date
            if len(vals) >= 5:
                lot_no = str(vals[1]).strip()
                try:
                    tb_count = int(str(vals[4]).replace(',', ''))
                except (ValueError, IndexError):
                    tb_count = 0
                return (lot_no, tb_count)

            return ('', 0)

        except Exception as e:
            logger.debug(f"_get_selected_lot_info: {e}")
            return ('', 0)
