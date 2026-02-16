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
            
        except (ValueError, TypeError, AttributeError) as e:
            logger.error(f"알림 수집 오류: {e}")
        
        return alerts

    def _get_tonbag_sample_breakdown(self) -> Dict:
        """v4.0.5 Phase3: 톤백/샘플 구분 통계"""
        try:
            row = self.engine.db.fetchone("""
                SELECT
                    SUM(CASE WHEN COALESCE(is_sample,0)=0 THEN weight ELSE 0 END) AS tonbag_kg,
                    SUM(CASE WHEN COALESCE(is_sample,0)=0 THEN 1 ELSE 0 END) AS tonbag_cnt,
                    SUM(CASE WHEN COALESCE(is_sample,0)=1 THEN weight ELSE 0 END) AS sample_kg,
                    SUM(CASE WHEN COALESCE(is_sample,0)=1 THEN 1 ELSE 0 END) AS sample_cnt,
                    COALESCE(SUM(weight), 0) AS total_kg,
                    COUNT(*) AS total_cnt
                FROM inventory_tonbag
                WHERE status = 'AVAILABLE'
            """)
            if not row:
                return {'tonbag_kg': 0, 'tonbag_cnt': 0, 'sample_kg': 0,
                        'sample_cnt': 0, 'total_kg': 0, 'total_cnt': 0}
            return {k: (row[k] or 0) for k in
                    ['tonbag_kg', 'tonbag_cnt', 'sample_kg', 'sample_cnt', 'total_kg', 'total_cnt']}
        except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
            logger.debug(f"톤백/샘플 통계 오류: {e}")
            return {'tonbag_kg': 0, 'tonbag_cnt': 0, 'sample_kg': 0,
                    'sample_cnt': 0, 'total_kg': 0, 'total_cnt': 0}

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

    def _get_today_tonbag_sample_stats(self, today: str) -> Dict:
        """
        v5.0.3: 금일 입출고 톤백/샘플 구분 통계 (캐싱 적용)
        
        변경사항:
        - created_at 기준 (등록 기준)
        - arrival_date 기준 (입항 기준) 추가
        - sqlite3.Row 객체 직접 접근
        - v5.0.3: 60초 캐싱 적용
        """
        try:
            # v5.0.3: 캐시 확인
            try:
                from engine_modules.query_cache import cache
                cache_key = f"today_stats:{today}"
                cached_data = cache.get(cache_key, ())
                if cached_data is not None:
                    logger.debug(f"📊 대시보드 통계 캐시 HIT")
                    return cached_data
            except ImportError as _e:
                logger.debug(f"Suppressed: {_e}")
            
            # 금일 입고 - 등록 기준 (created_at) ✅ v4.1.8
            inb_created = self.engine.db.fetchone("""
                SELECT
                    SUM(CASE WHEN COALESCE(t.is_sample,0)=0 THEN t.weight ELSE 0 END) AS tonbag_kg,
                    SUM(CASE WHEN COALESCE(t.is_sample,0)=0 THEN 1 ELSE 0 END) AS tonbag_cnt,
                    SUM(CASE WHEN COALESCE(t.is_sample,0)=1 THEN t.weight ELSE 0 END) AS sample_kg,
                    SUM(CASE WHEN COALESCE(t.is_sample,0)=1 THEN 1 ELSE 0 END) AS sample_cnt
                FROM inventory i
                JOIN inventory_tonbag t ON i.lot_no = t.lot_no
                WHERE DATE(i.created_at) = DATE(?)
            """, (today,))
            
            # 금일 입고 - 입항 기준 (arrival_date) ✅ v4.1.9 추가
            inb_arrival = self.engine.db.fetchone("""
                SELECT
                    SUM(CASE WHEN COALESCE(t.is_sample,0)=0 THEN t.weight ELSE 0 END) AS tonbag_kg,
                    SUM(CASE WHEN COALESCE(t.is_sample,0)=0 THEN 1 ELSE 0 END) AS tonbag_cnt,
                    SUM(CASE WHEN COALESCE(t.is_sample,0)=1 THEN t.weight ELSE 0 END) AS sample_kg,
                    SUM(CASE WHEN COALESCE(t.is_sample,0)=1 THEN 1 ELSE 0 END) AS sample_cnt
                FROM inventory i
                JOIN inventory_tonbag t ON i.lot_no = t.lot_no
                WHERE DATE(i.arrival_date) = DATE(?)
            """, (today,))
            
            # ✅ v4.1.9: Row 객체 안전 접근
            inbound_created = {
                'tonbag_kg': (inb_created['tonbag_kg'] or 0) if inb_created else 0,
                'tonbag_cnt': (inb_created['tonbag_cnt'] or 0) if inb_created else 0,
                'sample_kg': (inb_created['sample_kg'] or 0) if inb_created else 0,
                'sample_cnt': (inb_created['sample_cnt'] or 0) if inb_created else 0
            }
            
            inbound_arrival = {
                'tonbag_kg': (inb_arrival['tonbag_kg'] or 0) if inb_arrival else 0,
                'tonbag_cnt': (inb_arrival['tonbag_cnt'] or 0) if inb_arrival else 0,
                'sample_kg': (inb_arrival['sample_kg'] or 0) if inb_arrival else 0,
                'sample_cnt': (inb_arrival['sample_cnt'] or 0) if inb_arrival else 0
            }

            # 금일 출고 (stock_movement 기준)
            out = self.engine.db.fetchone("""
                SELECT COALESCE(SUM(qty_kg), 0) AS total_kg,
                       COUNT(*) AS total_cnt
                FROM stock_movement
                WHERE movement_type = 'OUTBOUND' AND DATE(movement_date) = DATE(?)
            """, (today,))
            
            # ✅ v4.1.8: Row 객체 안전 접근
            outbound = {
                'total_kg': (out['total_kg'] or 0) if out else 0,
                'total_cnt': (out['total_cnt'] or 0) if out else 0
            }

            result = {
                'inbound_created': inbound_created,  # ✅ v4.1.9: 등록 기준
                'inbound_arrival': inbound_arrival,  # ✅ v4.1.9: 입항 기준
                'outbound': outbound
            }
            
            # v5.0.3: 결과 캐싱 (60초)
            try:
                from engine_modules.query_cache import cache
                cache.set(f"today_stats:{today}", (), result)
            except ImportError as _e:
                logger.debug(f"Suppressed: {_e}")
            
            return result
        except (sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
            logger.debug(f"금일 톤백/샘플 통계 오류: {e}")
            return {
                'inbound_created': {'tonbag_kg': 0, 'tonbag_cnt': 0, 'sample_kg': 0, 'sample_cnt': 0},
                'inbound_arrival': {'tonbag_kg': 0, 'tonbag_cnt': 0, 'sample_kg': 0, 'sample_cnt': 0},
                'outbound': {'total_kg': 0, 'total_cnt': 0}
            }
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
        
        # LOT 번호 추출 시도
        text = self.alert_listbox.get(selection[0])
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
                
                # 출고
                cursor.execute('''
                    SELECT COALESCE(SUM(qty_kg), 0) 
                    FROM stock_movement 
                    WHERE movement_type = 'OUTBOUND' AND DATE(movement_date) = DATE(?)
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
