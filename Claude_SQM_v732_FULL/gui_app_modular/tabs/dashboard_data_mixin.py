# -*- coding: utf-8 -*-
"""
SQM v4.0.1 — 대시보드 데이터/차트 Mixin
==========================================

dashboard_tab.py에서 분리:
- 알림 수집
- 통계 조회
- 차트 그리기 (바차트)
- 자동 갱신
"""
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List

logger = logging.getLogger(__name__)


class DashboardDataMixin:
    """대시보드 데이터 수집 및 차트 Mixin"""

    def _get_return_doc_review_pending_count(self, days: int = 30) -> int:
        """
        반품 후 문서 연계 점검 필요 건수 집계.
        RETURN_DOC_REVIEW movement를 기준으로 최근 N일 건수를 조회한다.
        """
        try:
            row = self.engine.db.fetchone(
                """
                SELECT COUNT(*) AS cnt
                FROM stock_movement
                WHERE movement_type = 'RETURN_DOC_REVIEW'
                  AND DATE(created_at) >= DATE('now', ?)
                """,
                (f"-{int(days)} days",),
            )
            return int((row.get('cnt') if isinstance(row, dict) else row[0]) or 0) if row else 0
        except (sqlite3.OperationalError, sqlite3.IntegrityError, ValueError, TypeError, KeyError, OSError) as e:
            logger.debug(f"반품 문서점검 대기건 조회 오류: {e}")
            return 0

    def _collect_alerts(self) -> List[Dict]:
        """알림 수집"""
        alerts = []
        
        try:
            # 1. 재고 부족 알림
            low_stock = self._get_low_stock_lots()
            for lot in low_stock[:5]:
                alerts.append({
                    'icon': '📉',
                    'message': f"{lot['lot_no']}: 재고 부족 ({lot['weight']:.0f}kg)",
                    'severity': 'warning',
                    'lot_no': lot['lot_no']
                })
            
            # 2. 장기 체류 LOT 경고 — 삭제됨 (사장님 지시)
            # 3. 톤백 무결성 경고
            integrity_issues = self._check_tonbag_integrity_quick()
            if integrity_issues > 0:
                alerts.append({
                    'icon': '🔧',
                    'message': f"톤백 무결성 이슈 {integrity_issues}건",
                    'severity': 'error'
                })

            # 4. v6.12.1: 반품 알림 — LOT N회 이상 반품 시 경고
            try:
                from engine_modules.constants import RETURN_ALERT_THRESHOLD
                _threshold = RETURN_ALERT_THRESHOLD
            except ImportError:
                _threshold = 3
            try:
                repeat_lots = self.engine.db.fetchall(f"""
                    WITH combined AS (
                        SELECT lot_no FROM return_log
                        UNION ALL
                        SELECT lot_no FROM return_history
                    )
                    SELECT lot_no, COUNT(*) AS cnt
                    FROM combined
                    GROUP BY lot_no
                    HAVING COUNT(*) >= {_threshold}
                    ORDER BY cnt DESC LIMIT 5
                """)
                for rl in (repeat_lots or []):
                    _lot = rl['lot_no'] if isinstance(rl, dict) else rl[0]
                    _cnt = rl['cnt'] if isinstance(rl, dict) else rl[1]
                    alerts.append({
                        'icon': '🔄',
                        'message': f"{_lot}: 반품 {_cnt}회 — 품질 점검 필요",
                        'severity': 'warning',
                        'lot_no': _lot
                    })
            except Exception as _re:
                logger.debug(f"반품 알림 수집 오류: {_re}")

            # 5. 반품 후 문서 연계 점검 대기 알림
            pending_review = self._get_return_doc_review_pending_count(30)
            if pending_review > 0:
                alerts.append({
                    'icon': '📄',
                    'message': f"반품 문서점검 대기 {pending_review}건 (최근 30일)",
                    'severity': 'error' if pending_review >= 5 else 'warning'
                })

            # ★ v7.7.0 — 6. 부분 출고 잔류 감지 (검증 11)
            try:
                _partial_rows = self.engine.db.fetchall("""
                    SELECT lot_no,
                           SUM(CASE WHEN status='SOLD'      AND COALESCE(is_sample,0)=0 THEN 1 ELSE 0 END) AS sold_n,
                           SUM(CASE WHEN status='AVAILABLE' AND COALESCE(is_sample,0)=0 THEN 1 ELSE 0 END) AS avail_n
                    FROM inventory_tonbag
                    GROUP BY lot_no
                    HAVING sold_n > 0 AND avail_n > 0
                    ORDER BY lot_no
                    LIMIT 5
                """)
                for _pr in (_partial_rows or []):
                    _lot   = _pr['lot_no'] if isinstance(_pr, dict) else _pr[0]
                    _sold  = _pr['sold_n']  if isinstance(_pr, dict) else _pr[1]
                    _avail = _pr['avail_n'] if isinstance(_pr, dict) else _pr[2]
                    alerts.append({
                        'icon': '⚠️',
                        'message': (f"{_lot}: 부분 출고 잔류 "
                                    f"(SOLD={_sold} / AVAILABLE={_avail}) — allocation 확인"),
                        'severity': 'warning',
                        'lot_no': _lot,
                    })
            except Exception as _p7e:
                logger.debug(f"[v7.7.0] 부분 출고 잔류 알림 오류: {_p7e}")

            # ★ v7.7.0 — 7. allocation 초과 감지 (검증 12 ERROR)
            try:
                _alloc_err_rows = self.engine.db.fetchall("""
                    SELECT ap.lot_no,
                           ROUND(SUM(ap.qty_mt), 3)             AS alloc_mt,
                           ROUND((iv.initial_weight - 1.0)/1000.0, 3) AS net_mt
                    FROM allocation_plan ap
                    JOIN inventory iv ON iv.lot_no = ap.lot_no
                    WHERE ap.status NOT IN ('CANCELLED', 'REJECTED')
                    GROUP BY ap.lot_no
                    HAVING alloc_mt > net_mt + 0.001
                    ORDER BY ap.lot_no
                    LIMIT 5
                """)
                for _ar in (_alloc_err_rows or []):
                    _lot      = _ar['lot_no']  if isinstance(_ar, dict) else _ar[0]
                    _alloc_mt = _ar['alloc_mt'] if isinstance(_ar, dict) else _ar[1]
                    _net_mt   = _ar['net_mt']   if isinstance(_ar, dict) else _ar[2]
                    alerts.append({
                        'icon': '🔴',
                        'message': (f"{_lot}: allocation 초과 "
                                    f"({_alloc_mt:.3f}MT > 순중량 {_net_mt:.3f}MT)"),
                        'severity': 'error',
                        'lot_no': _lot,
                    })
            except Exception as _a7e:
                logger.debug(f"[v7.7.0] allocation 초과 알림 오류: {_a7e}")

            # [D] v6.8.3: lot_mode 예약 만료 임박 알림 (3일 이내)
            try:
                from datetime import datetime, timedelta
                _d_cutoff = (
                    datetime.now() - timedelta(days=4)
                ).strftime('%Y-%m-%d %H:%M:%S')
                _expiring = self.engine.db.fetchall("""
                    SELECT lot_no, customer, created_at
                    FROM allocation_plan
                    WHERE tonbag_id IS NULL
                      AND status = 'RESERVED'
                      AND created_at < ?
                    ORDER BY created_at ASC LIMIT 5
                """, (_d_cutoff,))
                if _expiring:
                    _exp_cnt = len(_expiring)
                    _exp_lot = (_expiring[0].get('lot_no') if isinstance(_expiring[0], dict)
                                else _expiring[0][0])
                    alerts.append({
                        'icon': '⏰',
                        'message': (
                            f"LOT 단위 예약 만료 임박 {_exp_cnt}건 (3일 이내 자동 취소) "
                            f"— 대표: {_exp_lot} / 바코드 스캔 필요"
                        ),
                        'severity': 'warning',
                        'lot_no': _exp_lot,
                    })
            except Exception as _de:
                logger.debug(f"[D 만료임박 알림] {_de}")

            # ② v6.8.2: 위치 미배정 알림 — 입고 후 배치가 안 된 톤백 자동 감지
            try:
                _ul_data = self._get_unassigned_location_data()
                _ul_total = _ul_data.get('total', 0)
                if _ul_total > 0:
                    _ul_lots = _ul_data.get('lot_count', 0)
                    alerts.append({
                        'icon': '📍',
                        'message': (
                            f"위치 미배정 톤백 {_ul_total}개 ({_ul_lots} LOT) "
                            f"— [재고관리→위치배정] 필요"
                        ),
                        'severity': 'error' if _ul_total >= 10 else 'warning',
                    })
            except Exception as _ule:
                logger.debug(f"[② 위치미배정 알림] {_ule}")

        except (ValueError, TypeError, AttributeError) as e:
            logger.error(f"알림 수집 오류: {e}")

        return alerts


    def _get_status_four_phase_stats(self) -> Dict:
        """
        v7.3.0: 5단계 현황 (AVAILABLE/RESERVED/PICKED/OUTBOUND+SOLD/RETURN) — 대시보드 카드용.
        inventory_tonbag 기준 건수·중량 집계.
        """
        try:
            row = self.engine.db.fetchone("""
                SELECT
                    SUM(CASE WHEN status = 'AVAILABLE' THEN 1 ELSE 0 END) AS available_cnt,
                    SUM(CASE WHEN status = 'RESERVED'  THEN 1 ELSE 0 END) AS reserved_cnt,
                    SUM(CASE WHEN status = 'PICKED'    THEN 1 ELSE 0 END) AS picked_cnt,
                    SUM(CASE WHEN status IN ('OUTBOUND','SOLD') THEN 1 ELSE 0 END) AS outbound_cnt,
                    SUM(CASE WHEN status = 'SOLD'      THEN 1 ELSE 0 END) AS sold_cnt,
                    SUM(CASE WHEN status = 'RETURN'    THEN 1 ELSE 0 END) AS return_cnt,
                    COUNT(*) AS total_cnt,
                    COALESCE(SUM(CASE WHEN status = 'AVAILABLE' THEN weight ELSE 0 END), 0) AS available_kg,
                    COALESCE(SUM(CASE WHEN status = 'RESERVED'  THEN weight ELSE 0 END), 0) AS reserved_kg,
                    COALESCE(SUM(CASE WHEN status = 'PICKED'    THEN weight ELSE 0 END), 0) AS picked_kg,
                    COALESCE(SUM(CASE WHEN status IN ('OUTBOUND','SOLD') THEN weight ELSE 0 END), 0) AS outbound_kg,
                    COALESCE(SUM(CASE WHEN status = 'SOLD'      THEN weight ELSE 0 END), 0) AS sold_kg,
                    COALESCE(SUM(CASE WHEN status = 'RETURN'    THEN weight ELSE 0 END), 0) AS return_kg,
                    COALESCE(SUM(weight), 0) AS total_kg
                FROM inventory_tonbag
            """, use_cache=True, cache_ttl=30)
            if not row:
                return {
                    'available_cnt': 0, 'reserved_cnt': 0, 'picked_cnt': 0,
                    'outbound_cnt': 0, 'sold_cnt': 0, 'return_cnt': 0, 'total_cnt': 0,
                    'available_kg': 0, 'reserved_kg': 0, 'picked_kg': 0,
                    'outbound_kg': 0, 'sold_kg': 0, 'return_kg': 0, 'total_kg': 0,
                }
            return {
                'available_cnt': row['available_cnt'] or 0,
                'reserved_cnt':  row['reserved_cnt']  or 0,
                'picked_cnt':    row['picked_cnt']    or 0,
                'outbound_cnt':  row['outbound_cnt']  or 0,
                'sold_cnt':      row['sold_cnt']      or 0,
                'return_cnt':    row['return_cnt']    or 0,
                'total_cnt':     row['total_cnt']     or 0,
                'available_kg':  row['available_kg']  or 0,
                'reserved_kg':   row['reserved_kg']   or 0,
                'picked_kg':     row['picked_kg']     or 0,
                'outbound_kg':   row['outbound_kg']   or 0,
                'sold_kg':       row['sold_kg']       or 0,
                'return_kg':     row['return_kg']     or 0,
                'total_kg':      row['total_kg']      or 0,
            }
        except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
            logger.debug(f"5단계 통계 오류: {e}")
            return {
                'available_cnt': 0, 'reserved_cnt': 0, 'picked_cnt': 0,
                'outbound_cnt': 0, 'sold_cnt': 0, 'return_cnt': 0, 'total_cnt': 0,
                'available_kg': 0, 'reserved_kg': 0, 'picked_kg': 0,
                'outbound_kg': 0, 'sold_kg': 0, 'return_kg': 0, 'total_kg': 0,
            }

    def _get_product_tonbag_sample_breakdown(self) -> List[Dict]:
        """
        v4.1.8: 제품별 톤백/샘플 구분 통계
        
        변경사항:
        - 샘플 제품명: [SAMPLE] → _sample 형식으로 변경
        - lot_count 변수 NameError 버그 수정
        """
        try:
            rows = self.engine.db.fetchall("""
                SELECT
                    i.product,
                    COALESCE(t.is_sample, 0) AS is_sample,
                    COUNT(DISTINCT i.lot_no) AS lot_count,
                    SUM(CASE WHEN t.status='AVAILABLE' THEN t.weight ELSE 0 END) AS tonbag_kg,
                    SUM(CASE WHEN t.status='AVAILABLE' THEN 1 ELSE 0 END) AS tonbag_cnt,
                    COALESCE(SUM(CASE WHEN t.status='AVAILABLE' THEN t.weight ELSE 0 END), 0) AS total_kg,
                    SUM(CASE WHEN t.status='AVAILABLE' THEN 1 ELSE 0 END) AS total_cnt
                FROM inventory i
                LEFT JOIN inventory_tonbag t ON i.lot_no = t.lot_no
                GROUP BY i.product, COALESCE(t.is_sample, 0)
                ORDER BY i.product, COALESCE(t.is_sample, 0) DESC
            """)
            result = []
            for r in rows:
                product = r['product'] or 'Unknown'
                is_sample = r['is_sample'] or 0
                r_lot_count = r['lot_count'] or 0  # ✅ v4.1.8: NameError 방지
                
                # ✅ v4.1.8: 샘플 제품명 표기 개선
                if is_sample:
                    if product and not str(product).endswith('_sample'):
                        product = f"{product}_sample"
                    r_lot_count = 0  # 샘플은 LOT 수 0으로 표시
                
                tb_kg = r['tonbag_kg'] or 0
                tb_cnt = r['tonbag_cnt'] or 0
                
                # 샘플 행: tonbag=0, sample=전부 / 일반 행: tonbag=전부, sample=0
                if is_sample:
                    result.append({
                        'product': product, 
                        'lot_count': r_lot_count,  # ✅ 수정
                        'tonbag_kg': 0, 'tonbag_cnt': 0,
                        'sample_kg': tb_kg, 'sample_cnt': tb_cnt,
                        'total_kg': r['total_kg'] or 0, 'total_cnt': r['total_cnt'] or 0,
                    })
                else:
                    result.append({
                        'product': product, 
                        'lot_count': r_lot_count,  # ✅ 수정
                        'tonbag_kg': tb_kg, 'tonbag_cnt': tb_cnt,
                        'sample_kg': 0, 'sample_cnt': 0,
                        'total_kg': r['total_kg'] or 0, 'total_cnt': r['total_cnt'] or 0,
                    })
            return result
        except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
            logger.debug(f"제품별 톤백/샘플 통계 오류: {e}")
            return []


    def _get_low_stock_lots(self, threshold: float = 1000) -> List[Dict]:
        """재고 부족 LOT 조회"""
        try:
            cursor = None
            conn = self.engine.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT lot_no, current_weight 
                FROM inventory 
                WHERE status = 'AVAILABLE' AND current_weight > 0 AND current_weight < ?
                ORDER BY current_weight ASC
                LIMIT 10
            ''', (threshold,))
            
            return [{'lot_no': row[0], 'weight': row[1]} for row in cursor.fetchall()]
            
        except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
            logger.error(f"재고 부족 조회 오류: {e}")
            return []
    
        finally:
            if cursor:
                try:
                    cursor.close()
                except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as _e:
                    logger.debug(f"{type(_e).__name__}: {_e}")
                except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as _e:
                    logger.debug(f"dashboard_tab: {_e}")
    def _check_tonbag_integrity_quick(self) -> int:
        """톤백 무결성 빠른 검사"""
        try:
            cursor = None
            conn = self.engine.get_connection()
            cursor = conn.cursor()
            
            # current_weight != SUM(AVAILABLE tonbag) 인 LOT 수
            cursor.execute('''
                SELECT COUNT(*) FROM (
                    SELECT i.lot_no
                    FROM inventory i
                    LEFT JOIN (
                        SELECT lot_no, COALESCE(SUM(weight), 0) as tonbag_sum
                        FROM inventory_tonbag
                        WHERE status = 'AVAILABLE'
                        GROUP BY lot_no
                    ) t ON i.lot_no = t.lot_no
                    WHERE ABS(i.current_weight - COALESCE(t.tonbag_sum, 0)) > 0.01
                      AND i.status = 'AVAILABLE'
                )
            ''')
            
            return cursor.fetchone()[0] or 0
            
        except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
            logger.error(f"무결성 검사 오류: {e}")
            return 0
    
        finally:
            if cursor:
                try:
                    cursor.close()
                except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as _e:
                    logger.debug(f"{type(_e).__name__}: {_e}")
                except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as _e:
                    logger.debug(f"dashboard_tab: {_e}")
    
    # =========================================================
    # 빠른 액션 핸들러
    # =========================================================
    
    def _quick_pdf_inbound(self) -> None:
        """빠른 PDF 입고"""
        if hasattr(self, '_handle_pdf_import'):
            self._handle_pdf_import()
        else:
            self._log("PDF 입고 기능 준비 중...")
    
    def _quick_outbound(self) -> None:
        """빠른 출고"""
        # 재고 탭으로 이동
        if hasattr(self, 'notebook'):
            self.notebook.select(1)  # 재고 탭 (인덱스 1)
    
    def _quick_search(self) -> None:
        """빠른 검색"""
        if hasattr(self, 'notebook'):
            self.notebook.select(1)  # 재고 탭 (검색 통합)
    
    def _quick_report(self) -> None:
        """빠른 보고서"""
        if hasattr(self, '_generate_summary_report'):
            self._generate_summary_report()
    
    def _quick_backup(self) -> None:
        """빠른 백업"""
        if hasattr(self, '_handle_backup'):
            self._handle_backup()
        else:
            self._log("백업 기능 준비 중...")
    
    def _on_alert_double_click(self, event) -> None:
        """알림 더블클릭 시 해당 LOT로 이동"""
        selection = self.alert_listbox.curselection()
        if not selection:
            return
        
        text = self.alert_listbox.get(selection[0])

        # 반품 문서점검 대기 알림은 반품 통계 화면으로 이동
        if "반품 문서점검 대기" in text and hasattr(self, "_show_return_statistics"):
            self._show_return_statistics()
            return

        # LOT 번호 추출 시도
        # 예: "📉 LOT-001: 재고 부족 (500kg)"
        if ':' in text:
            lot_part = text.split(':')[0]
            lot_no = lot_part.split()[-1] if lot_part else None
            
            if lot_no and hasattr(self, '_search_lot'):
                self._search_lot(lot_no)
    
    # =========================================================
    # 자동 새로고침
    # =========================================================
    
    def _start_auto_refresh(self) -> None:
        """자동 새로고침 시작"""
        if self.auto_refresh_var.get():
            try:
                self._refresh_dashboard()
            except (ValueError, TypeError, KeyError) as _e:
                logger.debug(f"{type(_e).__name__}: {_e}")
            except (ValueError, TypeError, AttributeError) as _e:
                logger.debug(f"Auto-refresh error: {_e}")
            # v3.6.2: 에러 발생해도 타이머는 계속 동작
            self._auto_refresh_job = self.root.after(30000, self._start_auto_refresh)
    
    def _toggle_auto_refresh(self) -> None:
        """자동 새로고침 토글"""
        if self.auto_refresh_var.get():
            self._start_auto_refresh()
        else:
            if self._auto_refresh_job:
                self.root.after_cancel(self._auto_refresh_job)
                self._auto_refresh_job = None
    
    def _stop_auto_refresh(self) -> None:
        """자동 새로고침 중지"""
        if self._auto_refresh_job:
            self.root.after_cancel(self._auto_refresh_job)
            self._auto_refresh_job = None
    
    # =========================================================
    # 차트 (v3.6.0 추가)
    # =========================================================
    
    def _refresh_dashboard_chart(self) -> None:
        """입출고 추이 차트 새로고침"""
        if not hasattr(self, 'chart_canvas'):
            return
        
        try:
            # 캔버스 초기화
            self.chart_canvas.delete('all')
            
            # 캔버스 크기
            self.chart_canvas.update_idletasks()
            width = self.chart_canvas.winfo_width() or 250
            height = self.chart_canvas.winfo_height() or 180
            
            # 여백
            margin_left = 50
            margin_right = 20
            margin_top = 20
            margin_bottom = 40
            
            chart_width = width - margin_left - margin_right
            chart_height = height - margin_top - margin_bottom
            
            # 최근 7일 데이터 가져오기
            data = self._get_weekly_io_data()
            
            if not data:
                # 데이터 없음 표시
                self.chart_canvas.create_text(
                    width // 2, height // 2,
                    text="데이터 없음",
                    fill='#999',
                    font=('맑은 고딕', 13)
                )
                return
            
            # 최대값 계산
            max_value = max(
                max(d.get('inbound', 0) for d in data),
                max(d.get('outbound', 0) for d in data),
                1  # 0 방지
            )
            
            # 막대 너비
            bar_width = chart_width // (len(data) * 3)
            gap = bar_width // 2
            
            # Y축 그리드
            for i in range(5):
                y = margin_top + (chart_height * i // 4)
                self.chart_canvas.create_line(
                    margin_left, y, width - margin_right, y,
                    fill='#eee', dash=(2, 2)
                )
                # Y축 레이블
                value = max_value * (4 - i) // 4
                self.chart_canvas.create_text(
                    margin_left - 5, y,
                    text=f"{value/1000:.0f}t",
                    anchor='e',
                    fill='#999',
                    font=('', 13)
                )
            
            # 막대 그래프
            for i, day_data in enumerate(data):
                x_base = margin_left + (i * (bar_width * 3 + gap))
                
                inbound = day_data.get('inbound', 0)
                outbound = day_data.get('outbound', 0)
                date_str = day_data.get('date', '')[-5:]  # MM-DD
                
                # 입고 막대 (녹색)
                in_height = (inbound / max_value) * chart_height if max_value > 0 else 0
                self.chart_canvas.create_rectangle(
                    x_base, margin_top + chart_height - in_height,
                    x_base + bar_width, margin_top + chart_height,
                    fill='#27ae60', outline='#1e8449'
                )
                
                # 출고 막대 (주황)
                out_height = (outbound / max_value) * chart_height if max_value > 0 else 0
                self.chart_canvas.create_rectangle(
                    x_base + bar_width + 2, margin_top + chart_height - out_height,
                    x_base + bar_width * 2 + 2, margin_top + chart_height,
                    fill='#e67e22', outline='#d35400'
                )
                
                # X축 레이블 (날짜)
                self.chart_canvas.create_text(
                    x_base + bar_width, margin_top + chart_height + 15,
                    text=date_str,
                    fill='#666',
                    font=('', 13)
                )
            
        except (AttributeError, RuntimeError) as e:
            logger.error(f"차트 새로고침 오류: {e}")
    
    def _get_weekly_io_data(self) -> List[Dict]:
        """최근 7일 입출고 데이터 조회"""
        try:
            cursor = None
            conn = self.engine.get_connection()
            cursor = conn.cursor()
            
            result = []
            for i in range(6, -1, -1):
                date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
                
                # 입고
                cursor.execute('''
                    SELECT COALESCE(SUM(initial_weight), 0) 
                    FROM inventory 
                    WHERE DATE(arrival_date) = DATE(?)
                ''', (date,))
                row = cursor.fetchone()
                inbound = (row[0] or 0) if row else 0
                
                # 출고 — created_at 사용 (movement_date 컬럼 없어도 동작)
                cursor.execute('''
                    SELECT COALESCE(SUM(qty_kg), 0) 
                    FROM stock_movement 
                    WHERE movement_type = 'OUTBOUND' AND DATE(created_at) = DATE(?)
                ''', (date,))
                row = cursor.fetchone()
                outbound = (row[0] or 0) if row else 0
                
                result.append({
                    'date': date,
                    'inbound': inbound,
                    'outbound': outbound
                })
            
            return result
            
        except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
            logger.error(f"주간 데이터 조회 오류: {e}")
            return []

        finally:
            if cursor:
                try:
                    cursor.close()
                except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as _e:
                    logger.debug(f"{type(_e).__name__}: {_e}")
                except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as _e:
                    logger.debug(f"dashboard_tab: {_e}")

    # =========================================================
    # v6.12.1: 반품률 대시보드 위젯
    # =========================================================


    # =========================================================
    # v6.7.2: 스캔 실패율 KPI
    # =========================================================

    def _get_scan_fail_rate_data(self) -> dict:
        """
        v6.7.2: 스캔 실패율 데이터.
        stock_movement의 SCAN_FAIL + audit_log 기반 집계.
        데이터 없으면 graceful N/A 반환.
        """
        result = {
            'total_scans': 0, 'fail_scans': 0,
            'fail_rate': 0.0, 'period_days': 30,
        }
        try:
            db = self.engine.db

            # 전체 스캔 (OUTBOUND 이동 = 출고 스캔)
            row = db.fetchone("""
                SELECT COUNT(*) AS cnt
                FROM stock_movement
                WHERE movement_type IN ('OUTBOUND','SOLD','PICKED')
                  AND created_at >= date('now', '-30 days')
            """)
            total = int(row['cnt'] if isinstance(row, dict) else (row[0] if row else 0))

            # SCAN_FAIL 이벤트 (audit_log 우선, stock_movement 보조)
            fail = 0
            try:
                r2 = db.fetchone("""
                    SELECT COUNT(*) AS cnt FROM audit_log
                    WHERE event_type LIKE '%SCAN_FAIL%'
                      AND created_at >= date('now', '-30 days')
                """)
                fail = int(r2['cnt'] if isinstance(r2, dict) else (r2[0] if r2 else 0))
            except Exception:
                pass
            if fail == 0:
                try:
                    r3 = db.fetchone("""
                        SELECT COUNT(*) AS cnt FROM stock_movement
                        WHERE movement_type = 'SCAN_FAIL'
                          AND created_at >= date('now', '-30 days')
                    """)
                    fail = int(r3['cnt'] if isinstance(r3, dict) else (r3[0] if r3 else 0))
                except Exception:
                    pass

            result['total_scans'] = total
            result['fail_scans']  = fail
            result['fail_rate']   = (fail / total * 100) if total > 0 else 0.0
        except Exception as e:
            logger.debug(f"[scan_fail_rate] {e}")
        return result

    def _refresh_dashboard_scan_fail(self) -> None:
        """v6.7.2: 스캔 실패율 카드 갱신."""
        if not hasattr(self, '_scan_fail_text'):
            return
        d = self._get_scan_fail_rate_data()
        rate    = d['fail_rate']
        total   = d['total_scans']
        fail    = d['fail_scans']
        period  = d['period_days']

        if total == 0:
            body = "최근 30일 스캔 데이터 없음"
            color = 'gray'
        else:
            color = '#e74c3c' if rate >= 5 else ('#e67e22' if rate >= 2 else '#27ae60')
            body = "\n".join([
                "실패율: {:.1f}%".format(rate),
                "전체: {:,}건  실패: {:,}건".format(total, fail),
                "기간: 최근 {}일".format(period),
            ])

        try:
            self._scan_fail_text.config(state='normal')
            self._scan_fail_text.delete('1.0', 'end')
            self._scan_fail_text.insert('end', body)
            self._scan_fail_text.config(
                state='disabled',
                fg=color
            )
        except Exception as e:
            logger.debug(f"[scan_fail_ui] {e}")

    # =========================================================
    # v6.7.3: LOT 평균 재고기간 KPI
    # =========================================================

    def _get_avg_lot_days_data(self) -> dict:
        """
        v6.7.3: LOT 평균 재고기간.
        입고일(arrival_date / stock_date) ~ 출고일(sold 이동) 기준.
        AVAILABLE LOT은 오늘 기준 현재 체류일 표시.
        """
        result = {
            'avg_days_sold': 0.0,
            'avg_days_available': 0.0,
            'max_days': 0,
            'long_lot': '',
            'available_lots': 0,
        }
        try:
            db = self.engine.db

            # 출고 완료 LOT 평균 재고기간
            row = db.fetchone("""
                SELECT AVG(julianday(sm.created_at) -
                           julianday(COALESCE(inv.stock_date, inv.arrival_date, inv.created_at))) AS avg_d
                FROM inventory inv
                JOIN stock_movement sm ON sm.lot_no = inv.lot_no
                WHERE sm.movement_type IN ('SOLD','OUTBOUND')
                  AND COALESCE(inv.stock_date, inv.arrival_date) IS NOT NULL
                  AND sm.created_at >= date('now', '-180 days')
            """)
            if row:
                v = row['avg_d'] if isinstance(row, dict) else row[0]
                result['avg_days_sold'] = round(float(v or 0), 1)

            # 현재 AVAILABLE LOT 체류일 평균 + 최장 LOT
            row2 = db.fetchone("""
                SELECT AVG(julianday('now') -
                           julianday(COALESCE(stock_date, arrival_date, created_at))) AS avg_d,
                       MAX(julianday('now') -
                           julianday(COALESCE(stock_date, arrival_date, created_at))) AS max_d,
                       COUNT(*) AS cnt
                FROM inventory
                WHERE status = 'AVAILABLE'
                  AND COALESCE(stock_date, arrival_date) IS NOT NULL
            """)
            if row2:
                avg2 = row2['avg_d'] if isinstance(row2, dict) else row2[0]
                max2 = row2['max_d'] if isinstance(row2, dict) else row2[1]
                cnt2 = row2['cnt']  if isinstance(row2, dict) else row2[2]
                result['avg_days_available'] = round(float(avg2 or 0), 1)
                result['max_days']           = int(float(max2 or 0))
                result['available_lots']     = int(cnt2 or 0)

            # 가장 오래 체류 중인 LOT
            row3 = db.fetchone("""
                SELECT lot_no,
                       CAST(julianday('now') -
                            julianday(COALESCE(stock_date, arrival_date, created_at)) AS INTEGER) AS days
                FROM inventory
                WHERE status = 'AVAILABLE'
                  AND COALESCE(stock_date, arrival_date) IS NOT NULL
                ORDER BY days DESC LIMIT 1
            """)
            if row3:
                lot  = row3['lot_no'] if isinstance(row3, dict) else row3[0]
                days = row3['days']   if isinstance(row3, dict) else row3[1]
                result['long_lot'] = f"{lot} ({days}일)"
        except Exception as e:
            logger.debug(f"[avg_lot_days] {e}")
        return result

    def _refresh_dashboard_avg_lot_days(self) -> None:
        """v6.7.3: LOT 평균 재고기간 카드 갱신."""
        if not hasattr(self, '_avg_lot_days_text'):
            return
        d = self._get_avg_lot_days_data()

        avg_s = d['avg_days_sold']
        avg_a = d['avg_days_available']
        max_d = d['max_days']
        long  = d['long_lot']
        cnt   = d['available_lots']

        if cnt == 0 and avg_s == 0:
            body  = "재고기간 데이터 없음"
            color = 'gray'
        else:
            color = ('#e74c3c' if max_d >= 180
                     else '#e67e22' if max_d >= 90
                     else '#27ae60')
            body = "\n".join([
                "입고→출고 평균: {}일".format(int(avg_s)),
                "현 재고 평균:  {}일 ({}LOT)".format(int(avg_a), cnt),
                "최장 체류: {}".format(long or '-'),
            ])
        try:
            self._avg_lot_days_text.config(state='normal')
            self._avg_lot_days_text.delete('1.0', 'end')
            self._avg_lot_days_text.insert('end', body)
            self._avg_lot_days_text.config(state='disabled', fg=color)
        except Exception as e:
            logger.debug(f"[avg_lot_days_ui] {e}")

    # =========================================================
    # [P1] v6.8.1: 위치 미배정 톤백 KPI
    # =========================================================

    def _get_unassigned_location_data(self) -> dict:
        """입고 후 location=NULL/공백인 AVAILABLE 톤백 집계."""
        result = {'total': 0, 'lots': [], 'lot_count': 0}
        try:
            db = self.engine.db
            row = db.fetchone("""
                SELECT COUNT(*) AS cnt
                FROM inventory_tonbag
                WHERE status = 'AVAILABLE'
                  AND COALESCE(is_sample, 0) = 0
                  AND (location IS NULL OR TRIM(location) = '')
            """)
            total = int((row['cnt'] if isinstance(row, dict) else row[0]) or 0) if row else 0
            result['total'] = total
            if total > 0:
                rows = db.fetchall("""
                    SELECT lot_no, COUNT(*) AS cnt
                    FROM inventory_tonbag
                    WHERE status = 'AVAILABLE'
                      AND COALESCE(is_sample, 0) = 0
                      AND (location IS NULL OR TRIM(location) = '')
                    GROUP BY lot_no ORDER BY cnt DESC LIMIT 5
                """)
                result['lots'] = [
                    (r['lot_no'] if isinstance(r, dict) else r[0],
                     int(r['cnt']  if isinstance(r, dict) else r[1]))
                    for r in (rows or [])
                ]
                result['lot_count'] = len(result['lots'])
        except Exception as e:
            logger.debug(f"[unassigned_loc] {e}")
        return result

    def _navigate_to_unassigned_location(self, event=None) -> None:
        """① v6.8.2: 위치 미배정 KPI 카드 클릭 → 판매가능 탭 이동
        search_var에 '위치미배정' 키워드 설정하여 필터 적용.
        """
        try:
            # 판매가능 탭(index 0)으로 전환
            if hasattr(self, 'notebook'):
                self.notebook.select(0)
            # 위치 미배정 필터 적용 — inventory_tab의 search_var 활용
            # _unassigned_loc_filter 플래그로 inventory_tab 측에서 감지
            if hasattr(self, '_unassigned_loc_filter_var'):
                self._unassigned_loc_filter_var.set(True)
            elif hasattr(self, 'search_var'):
                self.search_var.set('')  # 기존 검색 초기화
            # 재고 탭 갱신 트리거
            if hasattr(self, '_refresh_inventory'):
                self._refresh_inventory()
            logger.info("[① 드릴다운] 위치 미배정 → 판매가능 탭 이동")
        except Exception as e:
            logger.debug(f"[드릴다운] {e}")

    def _refresh_dashboard_unassigned_location(self) -> None:
        """[P1] v6.8.1: 위치 미배정 톤백 KPI 카드 갱신."""
        if not hasattr(self, '_unassigned_loc_text'):
            return
        d = self._get_unassigned_location_data()
        total = d['total']
        if total == 0:
            body  = "✅ 위치 미배정 없음"
            color = '#27ae60'
        else:
            lines = [f"⚠ 클릭하여 목록 보기 → {total}개 미배정"]
            for lot_no, cnt in d['lots'][:3]:
                lines.append(f"  {lot_no}: {cnt}개")
            if d['lot_count'] > 3:
                lines.append(f"  … 외 {d['lot_count']-3} LOT")
            body  = "\n".join(lines)
            color = '#e74c3c' if total >= 10 else '#e67e22'
        try:
            self._unassigned_loc_text.config(state='normal')
            self._unassigned_loc_text.delete('1.0', 'end')
            self._unassigned_loc_text.insert('end', body)
            self._unassigned_loc_text.config(state='disabled', fg=color)
            # ① 드릴다운 클릭 바인딩 (최초 1회)
            if not getattr(self, '_unassigned_drilldown_bound', False):
                self._unassigned_loc_text.bind('<Button-1>',
                    self._navigate_to_unassigned_location)
                self._unassigned_loc_text.config(cursor='hand2')
                self._unassigned_drilldown_bound = True
        except Exception as e:
            logger.debug(f"[unassigned_loc_ui] {e}")

    def _get_return_rate_data(self) -> Dict:
        """반품률 데이터 수집 (최근 30일 기준)."""
        result = {
            'return_count': 0,
            'outbound_count': 0,
            'return_rate': 0.0,
            'return_weight_kg': 0.0,
            'top_reasons': [],
        }
        try:
            # v7.1.0: return_log(REINBOUND) + return_history(레거시) UNION
            row = self.engine.db.fetchone("""
                WITH combined AS (
                    SELECT weight_kg, return_date, reason FROM return_log
                    UNION ALL
                    SELECT weight_kg, return_date, reason FROM return_history
                )
                SELECT COUNT(*) AS cnt, COALESCE(SUM(weight_kg), 0) AS total
                FROM combined
                WHERE return_date >= date('now', '-30 days')
            """)
            if row:
                result['return_count'] = row['cnt'] if isinstance(row, dict) else row[0]
                result['return_weight_kg'] = float(row['total'] if isinstance(row, dict) else row[1])

            row2 = self.engine.db.fetchone("""
                SELECT COUNT(*) AS cnt FROM stock_movement
                WHERE movement_type IN ('PICKED', 'SOLD', 'OUTBOUND')
                AND created_at >= date('now', '-30 days')
            """)
            if row2:
                result['outbound_count'] = row2['cnt'] if isinstance(row2, dict) else row2[0]

            total_out = result['outbound_count'] or 1
            result['return_rate'] = result['return_count'] / total_out * 100

            rows = self.engine.db.fetchall("""
                WITH combined AS (
                    SELECT reason, return_date FROM return_log
                    UNION ALL
                    SELECT reason, return_date FROM return_history
                )
                SELECT COALESCE(reason, '미기재') AS reason, COUNT(*) AS cnt
                FROM combined
                WHERE return_date >= date('now', '-30 days')
                GROUP BY COALESCE(reason, '미기재')
                ORDER BY cnt DESC LIMIT 3
            """)
            result['top_reasons'] = [
                {'reason': r['reason'] if isinstance(r, dict) else r[0],
                 'count': r['cnt'] if isinstance(r, dict) else r[1]}
                for r in rows
            ]
        except Exception as e:
            logger.debug(f"[return_rate] data error: {e}")
        return result

    def _refresh_dashboard_return_rate(self) -> None:
        """반품률 위젯 새로고침."""
        if not hasattr(self, '_return_info_text'):
            return
        try:
            data = self._get_return_rate_data()
            lines = [
                "📊 최근 30일 반품 현황",
                "",
                f"  반품: {data['return_count']}건 ({data['return_weight_kg']:,.0f}kg)",
                f"  출고: {data['outbound_count']}건",
            ]
            rate = data['return_rate']
            rate_icon = '🟢' if rate < 3 else ('🟡' if rate < 10 else '🔴')
            lines.append(f"  반품률: {rate_icon} {rate:.1f}%")
            pending_review = self._get_return_doc_review_pending_count(30)
            review_icon = '🟢' if pending_review == 0 else ('🟡' if pending_review < 5 else '🔴')
            lines.append(f"  문서점검 대기: {review_icon} {pending_review}건")
            lines.append("")
            if data['top_reasons']:
                lines.append("  상위 사유:")
                for r in data['top_reasons']:
                    lines.append(f"    • {r['reason']} ({r['count']}건)")

            self._return_info_text.config(state='normal')
            self._return_info_text.delete('1.0', 'end')
            self._return_info_text.insert('1.0', '\n'.join(lines))
            self._return_info_text.config(state='disabled')
        except Exception as e:
            logger.debug(f"[return_rate] widget error: {e}")

    # ══════════════════════════════════════════════════════════
    # v7.0.1: 위치별 재고 현황 (구역 통계)
    # ══════════════════════════════════════════════════════════

    def _get_location_zone_stats(self) -> Dict:
        """
        구역별 톤백 수량/중량 통계
        
        위치 형식: G5-01-02-03 → 첫 파트(G5)가 구역
        
        Returns:
            {
                'zones': [{'zone': 'A', 'count': 50, 'weight': 25000}, ...],
                'no_location': {'count': 10, 'weight': 5000},
                'total_locations': 150,
                'total_zones': 5
            }
        """
        try:
            # 구역별 집계 (위치 첫 파트 = 구역)
            rows = self.engine.db.fetchall("""
                SELECT 
                    CASE 
                        WHEN location IS NULL OR location = '' THEN '(미지정)'
                        WHEN INSTR(location, '-') > 0 THEN SUBSTR(location, 1, INSTR(location, '-') - 1)
                        ELSE location
                    END AS zone,
                    COUNT(*) AS count,
                    SUM(weight) AS total_weight
                FROM inventory_tonbag
                WHERE status = 'AVAILABLE'
                  AND COALESCE(is_sample, 0) = 0
                GROUP BY zone
                ORDER BY zone
            """)
            
            zones = []
            no_location = {'count': 0, 'weight': 0}
            
            for row in rows:
                zone = row['zone'] or '(미지정)'
                count = row['count'] or 0
                weight = row['total_weight'] or 0
                
                if zone == '(미지정)':
                    no_location = {'count': count, 'weight': weight}
                else:
                    zones.append({
                        'zone': zone,
                        'count': count,
                        'weight': weight
                    })
            
            return {
                'zones': sorted(zones, key=lambda x: x['zone']),
                'no_location': no_location,
                'total_locations': sum(z['count'] for z in zones),
                'total_zones': len(zones)
            }
            
        except Exception as e:
            logger.debug(f"location zone stats error: {e}")
            return {'zones': [], 'no_location': {'count': 0, 'weight': 0},
                    'total_locations': 0, 'total_zones': 0}

    # ═══════════════════════════════════════════════════════════════════
    # v7.3.2 Phase3 포팅: 스캔/입고/출고 활동 이벤트 조회
    # ═══════════════════════════════════════════════════════════════════

    def get_inbound_activity_summary(self, days: int = 3) -> Dict:
        """최근 입고 activity / alert event 요약."""
        try:
            rows = self.engine.db.fetchall(
                """
                SELECT movement_type, lot_no, remarks, created_at
                FROM stock_movement
                WHERE movement_type IN ('INBOUND_SUCCESS','INBOUND_FAILED','INBOUND_CANCELLED','INBOUND_ROLLBACK','ALERT_EVENT')
                  AND DATE(created_at) >= DATE('now', ?)
                ORDER BY created_at DESC
                LIMIT 50
                """,
                (f"-{max(1, int(days or 3))-1} days",)
            ) or []
            return {'success': True, 'rows': rows}
        except Exception as e:
            logger.debug(f"inbound activity summary 조회 오류: {e}")
            return {'success': False, 'rows': []}

    def get_recent_inbound_alert_events(self, limit: int = 8) -> List[Dict]:
        """ALERT_EVENT / INBOUND_* 이벤트를 Dashboard UI 표시용으로 변환."""
        try:
            rows = self.engine.db.fetchall(
                """
                SELECT movement_type, lot_no, remarks, created_at
                FROM stock_movement
                WHERE movement_type IN ('INBOUND_SUCCESS','INBOUND_FAILED','INBOUND_CANCELLED','INBOUND_ROLLBACK','ALERT_EVENT')
                ORDER BY datetime(created_at) DESC
                LIMIT ?
                """,
                (int(limit),)
            ) or []
        except Exception as e:
            logger.debug(f"recent inbound alert events 조회 오류: {e}")
            return []

        result = []
        for r in rows:
            ts = (r.get('created_at') if isinstance(r, dict) else '') or ''
            if len(ts) >= 16:
                ts = ts[11:16]
            mtype = (r.get('movement_type') if isinstance(r, dict) else '') or ''
            remarks = (r.get('remarks') if isinstance(r, dict) else '') or ''
            lot_no = (r.get('lot_no') if isinstance(r, dict) else '') or ''
            code = ''
            severity = 'info'

            if mtype == 'ALERT_EVENT':
                parts = [p.strip() for p in remarks.split('|', 2)]
                if parts:
                    code = parts[0]
                if len(parts) > 1:
                    severity = parts[1].lower()
                if len(parts) > 2:
                    remarks = parts[2]
            elif mtype in ('INBOUND_FAILED', 'INBOUND_ROLLBACK'):
                severity = 'error'
                code = mtype
            elif mtype == 'INBOUND_CANCELLED':
                severity = 'warning'
                code = mtype
            else:
                severity = 'info'
                code = mtype

            result.append({
                'time': ts or '--:--',
                'movement_type': mtype,
                'lot_no': lot_no,
                'code': code,
                'severity': severity,
                'message': remarks,
            })
        return result

    def get_recent_scan_activity_events(self, limit: int = 10) -> List[Dict]:
        """최근 scan 관련 activity / alert event 조회."""
        try:
            rows = self.engine.db.fetchall(
                """
                SELECT movement_type, lot_no, remarks, created_at
                FROM stock_movement
                WHERE movement_type IN ('SCAN_RESERVED_BIND','SCAN_PICKED','ALERT_EVENT')
                  AND (
                        movement_type != 'ALERT_EVENT'
                        OR COALESCE(remarks, '') LIKE 'SCAN_%'
                        OR COALESCE(remarks, '') LIKE '%% | scan | %%'
                      )
                ORDER BY datetime(created_at) DESC
                LIMIT ?
                """,
                (int(limit),)
            ) or []
        except Exception as e:
            logger.debug(f"recent scan activity 조회 오류: {e}")
            return []

        result = []
        for r in rows:
            ts = (r.get('created_at') if isinstance(r, dict) else '') or ''
            if len(ts) >= 16:
                ts = ts[11:16]
            mtype = (r.get('movement_type') if isinstance(r, dict) else '') or ''
            remarks = (r.get('remarks') if isinstance(r, dict) else '') or ''
            lot_no = (r.get('lot_no') if isinstance(r, dict) else '') or ''
            code = ''
            severity = 'info'

            if mtype == 'ALERT_EVENT':
                parts = [p.strip() for p in remarks.split('|', 2)]
                if parts:
                    code = parts[0]
                severity = 'warning'
                if len(parts) > 2:
                    remarks = parts[2]
            elif mtype == 'SCAN_PICKED':
                code = 'SCAN_PICKED'
                severity = 'info'
            else:
                code = 'SCAN_RESERVED_BIND'
                severity = 'info'

            result.append({
                'time': ts or '--:--',
                'movement_type': mtype,
                'lot_no': lot_no,
                'code': code,
                'severity': severity,
                'message': remarks,
            })
        return result

    def get_recent_ops_activity_events(self, limit: int = 12) -> List[Dict]:
        """inbound + scan + outbound 운영 이벤트를 통합 조회."""
        rows: List[Dict] = []
        try:
            if hasattr(self, 'get_recent_inbound_alert_events'):
                rows.extend(list(self.get_recent_inbound_alert_events(limit=limit) or []))
        except Exception as e:
            logger.debug(f"get_recent_inbound_alert_events 오류: {e}")

        try:
            if hasattr(self, 'get_recent_scan_activity_events'):
                rows.extend(list(self.get_recent_scan_activity_events(limit=limit) or []))
        except Exception as e:
            logger.debug(f"get_recent_scan_activity_events 오류: {e}")

        try:
            if hasattr(self, 'get_recent_outbound_final_events'):
                rows.extend(list(self.get_recent_outbound_final_events(limit=limit) or []))
        except Exception as e:
            logger.debug(f"get_recent_outbound_final_events 오류: {e}")

        seen: set = set()
        merged: List[Dict] = []
        for r in rows:
            key = (
                str(r.get('time', '')),
                str(r.get('movement_type', '')),
                str(r.get('lot_no', '')),
                str(r.get('code', '')),
                str(r.get('message', '')),
            )
            if key in seen:
                continue
            seen.add(key)
            merged.append(dict(r))

        def sort_key(x):
            return (str(x.get('time', '')), str(x.get('movement_type', '')), str(x.get('lot_no', '')))

        merged.sort(key=sort_key, reverse=True)
        return merged[:int(limit or 12)]

    def get_recent_outbound_final_events(self, limit: int = 10) -> List[Dict]:
        """최근 PICKED/SOLD/OUTBOUND 운영 이벤트 조회."""
        try:
            rows = self.engine.db.fetchall(
                """
                SELECT movement_type, lot_no, remarks, created_at
                FROM stock_movement
                WHERE movement_type IN ('SCAN_PICKED','SCAN_SOLD','OUTBOUND_FINAL')
                ORDER BY datetime(created_at) DESC
                LIMIT ?
                """,
                (int(limit),)
            ) or []
        except Exception as e:
            logger.debug(f"recent outbound final events 조회 오류: {e}")
            return []

        result = []
        for r in rows:
            ts = (r.get('created_at') if isinstance(r, dict) else '') or ''
            if len(ts) >= 16:
                ts = ts[11:16]
            mtype = (r.get('movement_type') if isinstance(r, dict) else '') or ''
            lot_no = (r.get('lot_no') if isinstance(r, dict) else '') or ''
            remarks = (r.get('remarks') if isinstance(r, dict) else '') or ''
            severity = 'info'
            code = mtype
            if mtype == 'SCAN_SOLD':
                severity = 'warning'
            elif mtype == 'OUTBOUND_FINAL':
                severity = 'info'
            result.append({
                'time': ts or '--:--',
                'movement_type': mtype,
                'lot_no': lot_no,
                'code': code,
                'severity': severity,
                'message': remarks,
            })
        return result
