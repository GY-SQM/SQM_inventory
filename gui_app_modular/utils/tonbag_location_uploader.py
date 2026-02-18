# -*- coding: utf-8 -*-
"""
SQM 재고관리 시스템 - 톤백 위치 업로드 유틸리티
===============================================

v4.2.3: 바코드 스캔 Excel → 톤백 위치 자동 업데이트

작성자: Ruby
"""

import pandas as pd
import logging
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)


class TonbagLocationUploader:
    """톤백 위치 Excel 업로드 처리"""
    
    def __init__(self, db_engine):
        """
        Args:
            db_engine: SQMDatabase 인스턴스
        """
        self.db = db_engine
    
    def parse_excel(self, file_path: str) -> Tuple[bool, str, List[Dict]]:
        """
        Excel 파일 파싱
        
        Args:
            file_path: Excel 파일 경로
            
        Returns:
            (성공여부, 메시지, 데이터 리스트)
            
        Expected Excel Format:
        ┌──────────────────┬────────┐
        │ UID              │ 위치   │
        ├──────────────────┼────────┤
        │ 1125072340-01    │ A-1-3  │
        │ 1125072340-02    │ A-1-4  │
        └──────────────────┴────────┘
        
        v5.6.1: lot_no + tonbag_no + location 양식도 지원
        v5.6.9: 로케이션 엑셀 양식 확정
        v5.8.x: 양식2에 uid 컬럼 선택 포함 가능 (있으면 해당 값으로 매칭)
        ┌────────┬────────┬────────┬──────────┬───────────┬──────────────┬──────────┐
        │ 순번   │ 입고일 │ BL No  │ lot_no   │ tonbag_no│ uid (선택)   │ location │
        ├────────┼────────┼────────┼──────────┼───────────┼──────────────┼──────────┤
        │ (자동) │ 선택   │ 선택   │ 필수     │ 필수     │ 선택         │ 필수     │
        │ 1      │ 2025-01│ B/L123 │ 112508.. │ 3         │ 1125081447-03│ A-01-01  │
        └────────┴────────┴────────┴──────────┴───────────┴──────────────┴──────────┘
        로케이션 체계: 영문-숫자-숫자 (예: A-01-01)
        """
        try:
            # Excel 읽기
            df = pd.read_excel(file_path)
            
            from core.column_registry import normalize_header
            df.columns = [normalize_header(c) for c in df.columns]
            
            # v5.6.1: 양식 자동 감지
            # 양식 1: UID + 위치 (기존)
            # 양식 2: lot_no + tonbag_no + location (신규)
            
            has_uid = 'uid' in df.columns or 'tonbag_uid' in df.columns
            has_lot = any(c in df.columns for c in ('lot_no', 'lot', 'lotno'))
            has_tb = any(c in df.columns for c in ('tonbag_no', 'tonbag', 'tb_no'))
            has_loc = any(c in df.columns for c in ('location', '위치'))
            
            if has_lot and has_tb and has_loc:
                # 양식 2: lot_no + tonbag_no + location (입고일, BL No 선택 컬럼 무시)
                return self._parse_lot_tonbag_format(df)
            elif has_uid and has_loc:
                # 양식 1: UID + 위치 (기존)
                return self._parse_uid_format(df)
            else:
                return False, (
                    "❌ 지원하는 양식이 아닙니다.\n\n"
                    "양식1: uid + 위치\n"
                    "양식2: lot_no + tonbag_no + location\n\n"
                    f"발견된 컬럼: {list(df.columns)}"
                ), []
            
        except (ValueError, TypeError, KeyError, OSError) as e:
            logger.error(f"Excel 파싱 실패: {e}")
            return False, f"❌ Excel 파싱 실패: {e}", []
    
    def _parse_uid_format(self, df) -> Tuple[bool, str, List[Dict]]:
        """양식 1: UID + 위치"""
        if 'uid' not in df.columns:
            if 'tonbag_uid' in df.columns:
                df.rename(columns={'tonbag_uid': 'uid'}, inplace=True)
            else:
                return False, "❌ 'UID' 컬럼을 찾을 수 없습니다", []
        
        if '위치' not in df.columns:
            if 'location' in df.columns:
                df.rename(columns={'location': '위치'}, inplace=True)
            else:
                return False, "❌ '위치' 컬럼을 찾을 수 없습니다", []
        
        df = df.dropna(subset=['uid', '위치'])
        if len(df) == 0:
            return False, "❌ 유효한 데이터가 없습니다", []
        
        data = []
        for idx, row in df.iterrows():
            uid = str(row['uid']).strip()
            location = str(row['위치']).strip()
            if not uid or uid.lower() == 'nan':
                continue
            if not location or location.lower() == 'nan':
                continue
            data.append({
                'uid': uid,
                'location': location,
                'row_num': idx + 2
            })
        
        if len(data) == 0:
            return False, "❌ 유효한 데이터가 없습니다", []
        return True, f"✅ {len(data)}개 데이터 파싱 완료 (UID 양식)", data
    
    def _parse_lot_tonbag_format(self, df) -> Tuple[bool, str, List[Dict]]:
        """양식 2: lot_no + tonbag_no + location (v5.6.9). uid 컬럼 있으면 해당 값으로 매칭 (선택)."""
        # 컬럼명 정규화 (입고일, BL No, uid 등 선택 컬럼 포함)
        col_map = {}
        for c in df.columns:
            c_lower = c.lower().strip()
            if c_lower in ('lot_no', 'lot', 'lotno'):
                col_map['lot_no'] = c
            elif c_lower in ('tonbag_no', 'tonbag', 'tb_no'):
                col_map['tonbag_no'] = c
            elif c_lower in ('location', '위치'):
                col_map['location'] = c
            elif c_lower in ('uid', 'tonbag_uid'):
                col_map['uid'] = c
        
        lot_col = col_map.get('lot_no')
        tb_col = col_map.get('tonbag_no')
        loc_col = col_map.get('location')
        uid_col = col_map.get('uid')
        
        if not lot_col or not tb_col or not loc_col:
            return False, "❌ 필수 컬럼 필요: lot_no, tonbag_no, location", []
        
        df = df.dropna(subset=[lot_col, tb_col, loc_col])
        if len(df) == 0:
            return False, "❌ 유효한 데이터가 없습니다", []
        
        data = []
        for idx, row in df.iterrows():
            lot_no = str(row[lot_col]).strip()
            tonbag_no = str(row[tb_col]).strip()
            location = str(row[loc_col]).strip()
            excel_uid = ''
            if uid_col and uid_col in row.index:
                v = row[uid_col]
                if pd.notna(v) and str(v).strip() and str(v).lower() != 'nan':
                    excel_uid = str(v).strip()
            if excel_uid and excel_uid.lower() == 'nan':
                excel_uid = ''
            
            if not lot_no or lot_no.lower() == 'nan':
                continue
            if not location or location.lower() == 'nan':
                continue
            # v5.6.9: 로케이션 형식 검증 (영문-숫자-숫자, 예: A-01-01)
            valid, msg = validate_location_format(location)
            if not valid:
                logger.warning(f"행 {idx + 2}: location '{location}' — {msg}")
            
            # UID: 엑셀에 uid(또는 tonbag_uid) 값이 있으면 사용, 없으면 lot_no+tonbag_no로 조회/생성
            if excel_uid:
                uid = excel_uid
            else:
                try:
                    tb_num = int(float(tonbag_no))
                    tonbag = self.db.fetchone(
                        "SELECT tonbag_uid FROM inventory_tonbag WHERE lot_no = ? AND sub_lt = ?",
                        (lot_no, tb_num))
                    if tonbag:
                        uid = tonbag['tonbag_uid'] if isinstance(tonbag, dict) else tonbag[0]
                    else:
                        uid = f"{lot_no}-{tb_num:02d}"
                        logger.warning(f"톤백 미발견: {lot_no}/sub_lt={tb_num}, UID 추정: {uid}")
                except (ValueError, TypeError):
                    uid = f"{lot_no}-{tonbag_no}"
            
            data.append({
                'uid': uid,
                'location': location,
                'lot_no': lot_no,
                'tonbag_no': tonbag_no,
                'row_num': idx + 2
            })
        
        if len(data) == 0:
            return False, "❌ 유효한 데이터가 없습니다", []
        return True, f"✅ {len(data)}개 데이터 파싱 완료 (LOT+톤백 양식)", data
    
    def validate_and_match(self, data: List[Dict]) -> Dict:
        """
        UID 매칭 및 유효성 검증
        
        Args:
            data: 파싱된 데이터 리스트
            
        Returns:
            {
                'matched': [...],    # 매칭 성공
                'not_found': [...],  # UID 없음
                'total': int,
                'success_count': int,
                'fail_count': int
            }
        """
        result = {
            'matched': [],
            'not_found': [],
            'total': len(data),
            'success_count': 0,
            'fail_count': 0
        }
        
        for item in data:
            uid = item['uid']
            location = item['location']
            row_num = item['row_num']
            
            # DB에서 UID로 톤백 조회
            tonbag = self.db.fetchone("""
                SELECT 
                    t.id,
                    t.tonbag_uid,
                    t.lot_no,
                    t.sub_lt,
                    t.location AS current_location,
                    i.product
                FROM inventory_tonbag t
                LEFT JOIN inventory i ON t.inventory_id = i.id
                WHERE t.tonbag_uid = ?
            """, (uid,))
            
            if tonbag:
                # 매칭 성공
                result['matched'].append({
                    'uid': uid,
                    'location': location,
                    'row_num': row_num,
                    'tonbag_id': tonbag['id'],
                    'lot_no': tonbag['lot_no'],
                    'sub_lt': tonbag['sub_lt'],
                    'product': tonbag['product'] or '',
                    'current_location': tonbag['current_location'] or '',
                    'location_changed': tonbag['current_location'] != location
                })
                result['success_count'] += 1
            else:
                # UID 없음
                result['not_found'].append({
                    'uid': uid,
                    'location': location,
                    'row_num': row_num,
                    'reason': 'UID를 찾을 수 없습니다'
                })
                result['fail_count'] += 1
        
        return result
    
    def update_locations(self, matched_data: List[Dict]) -> Tuple[bool, str]:
        """
        매칭된 톤백의 위치 업데이트
        
        Args:
            matched_data: 매칭 성공한 데이터 리스트
            
        Returns:
            (성공여부, 메시지)
        """
        if not matched_data:
            return False, "❌ 업데이트할 데이터가 없습니다"
        
        try:
            updated = 0
            
            with self.db.transaction():
                for item in matched_data:
                    tonbag_id = item['tonbag_id']
                    location = item['location']
                    
                    # 위치 업데이트
                    self.db.execute("""
                        UPDATE inventory_tonbag
                        SET location = ?
                        WHERE id = ?
                    """, (location, tonbag_id))
                    
                    updated += 1
            
            return True, f"✅ {updated}개 톤백 위치 업데이트 완료"
            
        except (ValueError, TypeError, KeyError, OSError) as e:
            # with 블록에서 자동 롤백 완료
            logger.error(f"위치 업데이트 실패: {e}")
            return False, f"❌ 업데이트 실패: {e}"
    
    def get_location_summary(self) -> Dict:
        """
        위치별 톤백 통계
        
        Returns:
            {
                'A-1-3': {'count': 5, 'total_weight': 125000},
                'A-1-4': {'count': 3, 'total_weight': 75000},
                ...
            }
        """
        try:
            rows = self.db.fetchall("""
                SELECT 
                    location,
                    COUNT(*) AS count,
                    SUM(current_weight) AS total_weight
                FROM inventory_tonbag
                WHERE location IS NOT NULL
                  AND location != ''
                  AND status = 'AVAILABLE'
                GROUP BY location
                ORDER BY location
            """)
            
            summary = {}
            for row in rows:
                summary[row['location']] = {
                    'count': row['count'],
                    'total_weight': row['total_weight'] or 0
                }
            
            return summary
            
        except (ValueError, TypeError, KeyError, OSError) as e:
            logger.error(f"위치 통계 조회 실패: {e}")
            return {}


def validate_location_format(location: str) -> Tuple[bool, str]:
    """
    위치 형식 검증
    
    Args:
        location: 위치 문자열 (예: A-1-3)
        
    Returns:
        (유효여부, 메시지)
    """
    if not location or not isinstance(location, str):
        return False, "위치가 비어있습니다"
    
    location = location.strip()
    
    # 길이 체크
    if len(location) > 50:
        return False, "위치가 너무 깁니다 (최대 50자)"
    
    # 기본 형식 체크 (A-1-3 형식)
    parts = location.split('-')
    if len(parts) != 3:
        return False, "형식이 올바르지 않습니다 (예: A-1-3)"
    
    zone, row, level = parts
    
    # 구역: 영문 1자
    if not zone.isalpha() or len(zone) != 1:
        return False, "구역은 영문 1자여야 합니다 (예: A)"
    
    # 열: 숫자
    if not row.isdigit():
        return False, "열은 숫자여야 합니다 (예: 1)"
    
    # 층: 숫자
    if not level.isdigit():
        return False, "층은 숫자여야 합니다 (예: 3)"
    
    return True, "OK"


# 테스트
if __name__ == '__main__':
    # 위치 형식 검증 테스트
    test_cases = [
        ("A-1-3", True),
        ("B-2-5", True),
        ("A-10-1", True),
        ("AA-1-3", False),  # 구역 2자
        ("A-B-3", False),   # 열이 문자
        ("A-1", False),     # 부족
        ("", False),        # 비어있음
    ]
    
    logger.debug("위치 형식 검증 테스트:")
    for location, expected in test_cases:
        valid, msg = validate_location_format(location)
        status = "✅" if valid == expected else "❌"
        logger.debug(f"{status} '{location}': {valid} - {msg}")
