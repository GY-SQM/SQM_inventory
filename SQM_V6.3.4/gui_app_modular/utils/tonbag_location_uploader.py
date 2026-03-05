"""
SQM 재고관리 시스템 - 톤백 위치 업로드 유틸리티
===============================================

v4.2.3: 바코드 스캔 Excel → 톤백 위치 자동 업데이트
v5.9.8: 로케이션 4파트 지원 — 약식 A-01-01-10 (구역-열-층-칸)

작성자: Ruby
"""

import logging
from typing import Dict, List, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


class TonbagLocationUploader:
    """톤백 위치 Excel 업로드 처리"""

    def __init__(self, db_engine):
        """
        Args:
            db_engine: SQMDatabase 인스턴스 또는 SQMInventoryEngineV3(엔진 전달 시 .db 사용)
        """
        # 엔진이 전달되면 engine.db, DB가 전달되면 그대로 사용
        self.db = getattr(db_engine, 'db', db_engine)
        if self.db is None:
            raise ValueError("db_engine에 DB가 없습니다 (engine.db가 None)")

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
        현장(입고/출고)은 UID를 모름 — LOT NO + 톤백 NO + LOCATION만 전달, 프로그램이 UID 자동 매칭
        ┌────────┬────────┬────────┬──────────┬───────────┬──────────────┬──────────┐
        │ 순번   │ 입고일 │ BL No  │ lot_no   │ tonbag_no│ uid (선택)   │ location │
        ├────────┼────────┼────────┼──────────┼───────────┼──────────────┼──────────┤
        │ (자동) │ 선택   │ 선택   │ 필수     │ 필수     │ 선택         │ 필수     │
        │ 1      │ 2025-01│ B/L123 │ 112508.. │ 3         │ 1125081447-03│ A-01-01  │
        └────────┴────────┴────────┴──────────┴───────────┴──────────────┴──────────┘
        로케이션 약식: 3파트 A-01-01 (구역-열-층) 또는 4파트 A-01-01-10 (구역-열-층-칸)
        """
        try:
            # 매핑 파일 형식: 1행=타이틀, 2행=요약(선택), 3행=헤더, 4행~=데이터
            peek = pd.read_excel(file_path, header=None, nrows=4)
            first_cell = str(peek.iloc[0, 0]) if peek.size else ""
            header_row = 2 if ("SQM" in first_cell and "로케이션" in first_cell) else 0
            df = pd.read_excel(file_path, header=header_row)
            # 빈 행 제거(제목/요약만 있는 파일 시)
            df = df.dropna(how='all').reset_index(drop=True)

            from core.column_registry import normalize_header
            df.columns = [normalize_header(c) for c in df.columns]

            # 3행=헤더로 읽었는데 필수 컬럼이 없으면 2행을 헤더로 재시도 (1행 타이틀만 있는 경우)
            # 톤백번호: column_registry가 TONBAG NO → sub_lt 로 정규화하므로 sub_lt도 후보에 포함
            if header_row == 2:
                required = {'lot_no', 'tonbag_no', 'location'}
                has_required = (
                    any(c in df.columns for c in ('lot_no', 'lot', 'lotno')) and
                    any(c in df.columns for c in ('tonbag_no', 'tonbag', 'tb_no', 'sub_lt')) and
                    any(c in df.columns for c in ('location', '위치'))
                )
                if not has_required and len(peek) > 1:
                    df2 = pd.read_excel(file_path, header=1)
                    df2 = df2.dropna(how='all').reset_index(drop=True)
                    df2.columns = [normalize_header(c) for c in df2.columns]
                    if any(c in df2.columns for c in ('lot_no', 'lot', 'lotno')) and any(c in df2.columns for c in ('location', '위치')):
                        df = df2
                        header_row = 1

            # v5.6.1: 양식 자동 감지
            # 양식 1: UID + 위치 (기존)
            # 양식 2: lot_no + tonbag_no + location (신규)
            # TONBAG NO 헤더는 column_registry에서 sub_lt로 정규화되므로 sub_lt도 톤백번호 후보
            has_uid = 'uid' in df.columns or 'tonbag_uid' in df.columns
            has_lot = any(c in df.columns for c in ('lot_no', 'lot', 'lotno'))
            has_tb = any(c in df.columns for c in ('tonbag_no', 'tonbag', 'tb_no', 'sub_lt'))
            has_loc = any(c in df.columns for c in ('location', '위치'))

            if has_lot and has_tb and has_loc:
                # 양식 2: lot_no + tonbag_no + location (입고일, BL No 선택 컬럼 무시)
                ok, msg, data = self._parse_lot_tonbag_format(df)
                if ok and data and header_row > 0:
                    for item in data:
                        item['row_num'] += header_row
                return ok, msg, data
            elif has_uid and has_loc:
                # 양식 1: UID + 위치 (기존)
                ok, msg, data = self._parse_uid_format(df)
                if ok and data and header_row > 0:
                    for item in data:
                        item['row_num'] += header_row
                return ok, msg, data
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

    def parse_pasted_text(self, text: str) -> Tuple[bool, str, List[Dict]]:
        """
        붙여넣은 텍스트(TSV/CSV) 파싱. 헤더 포함 시 첫 줄을 컬럼명으로 사용.
        양식: lot_no, tonbag_no, uid(선택), location 또는 uid, 위치
        """
        try:
            from core.column_registry import normalize_header
            lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
            if not lines:
                return False, "❌ 붙여넣은 데이터가 비어 있습니다.", []
            # 구분자: 탭 우선, 없으면 쉼표
            first = lines[0]
            delim = "\t" if "\t" in first else ","
            parts_list = [ln.split(delim) for ln in lines]
            max_cols = max(len(p) for p in parts_list)
            # 컬럼 수 맞추기
            for p in parts_list:
                while len(p) < max_cols:
                    p.append("")
            # 첫 줄이 헤더인지 판단 (lot_no, uid, location 등 키워드 포함)
            first_row = [str(x).strip() for x in parts_list[0]]
            normalized_first = [normalize_header(c) for c in first_row]
            has_lot = any(c in normalized_first for c in ("lot_no", "lot", "lotno"))
            has_tb = any(c in normalized_first for c in ("tonbag_no", "tonbag", "tb_no", "sub_lt"))
            has_loc = any(c in normalized_first for c in ("location", "위치"))
            has_uid = any(c in normalized_first for c in ("uid", "tonbag_uid"))
            if has_lot and has_tb and has_loc:
                header_row = normalized_first
                data_start = 1
            elif has_uid and has_loc:
                header_row = normalized_first
                data_start = 1
            else:
                # 헤더 없음: 2열 = uid, location / 3열 = lot_no, tonbag_no, location / 4열 = + uid
                if max_cols >= 4:
                    header_row = ["lot_no", "tonbag_no", "uid", "location"][:max_cols]
                elif max_cols >= 3:
                    header_row = ["lot_no", "tonbag_no", "location"][:max_cols]
                else:
                    header_row = ["uid", "location"]
                data_start = 0
            # DataFrame 생성
            import pandas as pd
            col_count = min(len(header_row), max_cols)
            header_row = header_row[:col_count]
            data_rows = []
            for i in range(data_start, len(parts_list)):
                row = parts_list[i][:col_count]
                data_rows.append(row)
            if not data_rows:
                return False, "❌ 데이터 행이 없습니다.", []
            df = pd.DataFrame(data_rows, columns=header_row)
            df.columns = [normalize_header(c) for c in df.columns]
            has_lot = any(c in df.columns for c in ("lot_no", "lot", "lotno"))
            has_tb = any(c in df.columns for c in ("tonbag_no", "tonbag", "tb_no", "sub_lt"))
            has_loc = any(c in df.columns for c in ("location", "위치"))
            has_uid = any(c in df.columns for c in ("uid", "tonbag_uid"))
            if has_lot and has_tb and has_loc:
                return self._parse_lot_tonbag_format(df)
            if has_uid and has_loc:
                return self._parse_uid_format(df)
            return False, (
                "❌ 지원하는 양식이 아닙니다. 헤더: lot_no, tonbag_no, location 또는 uid, 위치"
            ), []
        except Exception as e:
            logger.error(f"붙여넣기 파싱 실패: {e}")
            return False, f"❌ 파싱 실패: {e}", []

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
        """양식 2: (LOT 번호, 톤백 번호) 한 쌍 + location. 현장 업로드 = 이 쌍으로 재고와 일치시킨 뒤 로케이션 반영."""
        # 컬럼명 정규화 (입고일, BL No, uid 등 선택 컬럼 포함)
        # TONBAG NO → sub_lt 로 정규화되므로 sub_lt도 톤백번호 컬럼으로 인정
        col_map = {}
        for c in df.columns:
            c_lower = c.lower().strip()
            if c_lower in ('lot_no', 'lot', 'lotno'):
                col_map['lot_no'] = c
            elif c_lower in ('tonbag_no', 'tonbag', 'tb_no', 'sub_lt'):
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

        def _norm_lot(s):
            s = str(s).strip()
            if s.lower() == 'nan' or not s:
                return s
            try:
                if '.' in s and s.endswith('.0'):
                    return str(int(float(s)))
            except (ValueError, TypeError) as e:
                logger.warning(f"[_norm_lot] Suppressed: {e}")
            return s

        data = []
        for idx, row in df.iterrows():
            lot_no = _norm_lot(row[lot_col])
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
            # v5.6.9/v5.9.8: 로케이션 형식 검증 (3파트 A-01-01 또는 4파트 A-01-01-10)
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
        # 3행=헤더인데 첫 행이 헤더 문자열로 들어온 경우 한 행만 제거 (헤더가 데이터로 포함된 경우)
        if len(data) > 0:
            r0 = data[0]
            lot0 = str(r0.get('lot_no', '')).strip().lower()
            tb0 = str(r0.get('tonbag_no', '')).strip().lower()
            if (lot0 in ('lot_no', 'lot', 'lotno', 'lot no') and
                    tb0 in ('tonbag_no', 'tonbag', 'tb_no', 'tonbag no', 'sub_lt')):
                data = data[1:]
        if len(data) == 0:
            return False, "❌ 유효한 데이터가 없습니다 (헤더만 있음)", []
        return True, f"✅ {len(data)}개 데이터 파싱 완료 (LOT+톤백 양식)", data

    def validate_and_match(self, data: List[Dict]) -> Dict:
        """
        톤백 리스트(inventory_tonbag) 전용. 재고 리스트(LOT 리스트) DB는 사용하지 않음.
        매칭 키: (LOT 번호, 톤백 번호) 한 쌍 — 현장 (LOT, 톤백번호)와 톤백 리스트 (lot_no, sub_lt) 일치 후
        해당 톤백 행의 location 컬럼에 업로드한 로케이션 반영.
        
        Returns:
            matched, not_found, total, success_count, fail_count
        """
        result = {
            'matched': [],
            'not_found': [],
            'total': len(data),
            'success_count': 0,
            'fail_count': 0
        }

        def _norm_lot_no(val):
            if val is None:
                return ''
            s = str(val).strip()
            if not s or s.lower() == 'nan':
                return ''
            try:
                f = float(s)
                if f == int(f):
                    return str(int(f))
            except (ValueError, TypeError) as e:
                logger.warning(f"[_norm_lot_no] Suppressed: {e}")
            return s

        for item in data:
            raw_lot = item.get('lot_no')
            lot_no = _norm_lot_no(raw_lot)
            tonbag_no = item.get('tonbag_no', '')
            location = item['location']
            row_num = item['row_num']
            uid = item.get('uid', '')
            tb_str = str(tonbag_no).strip()
            tonbag = None

            # UID가 있으면 LOT/톤백번호보다 먼저 매칭 시도 (현장 업로드 안정성 향상)
            if uid and str(uid).strip().lower() != 'nan':
                tonbag = self.db.fetchone("""
                    SELECT t.id, t.tonbag_uid, t.lot_no, t.sub_lt,
                           t.location AS current_location, i.product
                    FROM inventory_tonbag t
                    LEFT JOIN inventory i ON t.inventory_id = i.id
                    WHERE t.tonbag_uid = ?
                """, (uid,))

            # UID 매칭 실패 시 기존 (LOT, 톤백번호) 매칭 시도
            sub_lt_val = None
            if tonbag is None and tb_str not in ('', 'nan'):
                tb_upper = tb_str.upper()
                if tb_upper in ('S00', 'S0'):
                    sub_lt_val = 0
                elif tb_upper.startswith('S') and len(tb_upper) > 1 and tb_upper[1:].strip().isdigit():
                    try:
                        sub_lt_val = int(tb_upper[1:].strip())
                    except (ValueError, TypeError):
                        sub_lt_val = 0
                else:
                    try:
                        sub_lt_val = int(float(tb_str))
                    except (ValueError, TypeError):
                        sub_lt_val = None

                if sub_lt_val is not None and lot_no:
                    tonbag = self.db.fetchone("""
                        SELECT t.id, t.tonbag_uid, t.lot_no, t.sub_lt,
                               t.location AS current_location, i.product
                        FROM inventory_tonbag t
                        LEFT JOIN inventory i ON t.inventory_id = i.id
                        WHERE t.lot_no = ? AND t.sub_lt = ?
                    """, (lot_no, sub_lt_val))
                    # DB에 공백/숫자형 차이 있을 수 있어 fallback: trim(lot_no), sub_lt 문자 비교
                    if tonbag is None:
                        tonbag = self.db.fetchone("""
                            SELECT t.id, t.tonbag_uid, t.lot_no, t.sub_lt,
                                   t.location AS current_location, i.product
                            FROM inventory_tonbag t
                            LEFT JOIN inventory i ON t.inventory_id = i.id
                            WHERE trim(cast(t.lot_no as text)) = ? AND (t.sub_lt = ? OR cast(t.sub_lt as text) = ?)
                        """, (lot_no, sub_lt_val, str(sub_lt_val)))

            if tonbag is None:
                if uid and str(uid).strip().lower() != 'nan':
                    reason = f'UID 톤백 리스트에 없음: {uid}'
                elif tb_str in ('', 'nan'):
                    reason = f'톤백 번호 없음 (LOT: {lot_no})'
                elif sub_lt_val is None:
                    reason = f'톤백 번호 형식 오류: {tonbag_no}'
                else:
                    reason = f'(LOT·톤백번호 쌍) 톤백 리스트에 없음: LOT {lot_no} / 톤백 {sub_lt_val}'
                result['not_found'].append({
                    'uid': uid, 'location': location, 'row_num': row_num,
                    'reason': reason
                })
                result['fail_count'] += 1
                continue

            result['matched'].append({
                'uid': tonbag.get('tonbag_uid') or uid,
                'location': location,
                'target_location': location,
                'row_num': row_num,
                'tonbag_id': tonbag['id'],
                'lot_no': tonbag['lot_no'],
                'sub_lt': tonbag['sub_lt'],
                'product': tonbag['product'] or '',
                # 최초 매핑(기존 위치 없음)에서는 업로드 위치를 현재 위치로 표시
                'db_current_location': tonbag['current_location'] or '',
                'current_location': (tonbag['current_location'] or '').strip() or location,
                'move_1': '',
                'move_2': '',
                'move_3': '',
                'location_changed': (tonbag['current_location'] or '') != location
            })
            result['success_count'] += 1

        # 최근 이동 이력(최대 3회) 채우기
        for item in result['matched']:
            moves = self._get_recent_move_locations(item.get('lot_no', ''), item.get('sub_lt', 0))
            item['move_1'] = moves[0] if len(moves) > 0 else ''
            item['move_2'] = moves[1] if len(moves) > 1 else ''
            item['move_3'] = moves[2] if len(moves) > 2 else ''

        return result

    def update_locations(self, matched_data: List[Dict]) -> Tuple[bool, str]:
        """
        매칭된 톤백의 위치 업데이트 (v7.0.1: stock_movement 이력 기록)
        
        Args:
            matched_data: 매칭 성공한 데이터 리스트
            
        Returns:
            (성공여부, 메시지)
        """
        if not matched_data:
            return False, "❌ 업데이트할 데이터가 없습니다"

        try:
            from datetime import datetime
            updated = 0
            relocated = 0
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            with self.db.transaction():
                for item in matched_data:
                    tonbag_id = item['tonbag_id']
                    from_loc = (item.get('db_current_location') or '').strip()
                    display_current = (item.get('current_location') or '').strip()
                    lot_no = item.get('lot_no', '')
                    sub_lt = item.get('sub_lt', 0)
                    move_1 = (item.get('move_1') or '').strip()
                    move_2 = (item.get('move_2') or '').strip()
                    move_3 = (item.get('move_3') or '').strip()

                    # 이동 경로 구성:
                    # - move_1~3 입력이 있으면 순차 이동
                    # - 없으면 target/location/current 기준 단일 반영
                    move_targets = [v for v in (move_1, move_2, move_3) if v and v != '-']
                    if move_targets:
                        route_targets = move_targets
                    else:
                        fallback_target = (
                            (item.get('target_location') or '').strip() or
                            (item.get('location') or '').strip() or
                            display_current
                        )
                        route_targets = [fallback_target] if fallback_target else []

                    # 실제 시작 위치: DB 현재 위치 우선, 없으면 화면 현재 위치 사용
                    route_from = from_loc or display_current

                    # 톤백 리스트(inventory_tonbag)만 갱신 — 재고 리스트(inventory)는 건드리지 않음
                    # location_updated_at, updated_at 함께 갱신 (v4.2.3 마이그레이션 컬럼)
                    final_location = route_from
                    for target in route_targets:
                        if not target:
                            continue
                        if final_location == target:
                            continue
                        # 최초 매핑(DB 기존 위치 없음)에서 첫 배치는 이동 이력으로 보지 않음
                        is_initial_set = (not from_loc) and (final_location == display_current)
                        if not is_initial_set:
                            # 톤백 weight 조회
                            tb_row = self.db.fetchone(
                                "SELECT weight FROM inventory_tonbag WHERE id = ?", (tonbag_id,)
                            )
                            tb_weight = (tb_row.get('weight') or 0) if tb_row else 0
                            self.db.execute("""
                                INSERT INTO stock_movement 
                                (lot_no, movement_type, qty_kg, from_location, to_location, remarks, created_at)
                                VALUES (?, 'RELOCATE', ?, ?, ?, ?, ?)
                            """, (lot_no, tb_weight, final_location, target,
                                  f"sub_lt={sub_lt}, source=EXCEL_UPLOAD", now))
                            relocated += 1
                        final_location = target

                    self.db.execute("""
                        UPDATE inventory_tonbag
                        SET location = ?,
                            location_updated_at = ?,
                            updated_at = ?
                        WHERE id = ?
                    """, (final_location, now, now, tonbag_id))

                    updated += 1

            msg = f"✅ {updated}개 톤백 위치 업데이트 완료"
            if relocated > 0:
                msg += f" (이동 이력 {relocated}건 기록)"
            return True, msg

        except (ValueError, TypeError, KeyError, OSError) as e:
            # with 블록에서 자동 롤백 완료
            logger.error(f"위치 업데이트 실패: {e}")
            return False, f"❌ 업데이트 실패: {e}"

    def _get_recent_move_locations(self, lot_no: str, sub_lt: int) -> List[str]:
        """해당 톤백의 최근 RELOCATE 도착 위치를 최대 3건 반환."""
        if not lot_no and sub_lt is None:
            return []
        try:
            rows = self.db.fetchall("""
                SELECT to_location
                FROM stock_movement
                WHERE movement_type = 'RELOCATE'
                  AND lot_no = ?
                  AND remarks LIKE ?
                  AND COALESCE(to_location, '') <> ''
                ORDER BY created_at DESC, id DESC
                LIMIT 3
            """, (str(lot_no), f"%sub_lt={sub_lt}%"))
            return [str(r.get('to_location', '')).strip() for r in rows if str(r.get('to_location', '')).strip()]
        except (ValueError, TypeError, KeyError, OSError):
            return []

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
                    SUM(weight) AS total_weight
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
    위치 형식 검증 (3파트 또는 4파트)
    
    허용 형식:
      - 3파트: A-01-01 (구역-열-층)
      - 4파트: A-01-01-10 (구역-열-층-칸) — 로케이션 약식 기본
    
    Args:
        location: 위치 문자열 (예: A-01-01 또는 A-01-01-10)
        
    Returns:
        (유효여부, 메시지)
    """
    if not location or not isinstance(location, str):
        return False, "위치가 비어있습니다"

    location = location.strip()

    if len(location) > 50:
        return False, "위치가 너무 깁니다 (최대 50자)"

    parts = location.split('-')
    if len(parts) not in (3, 4):
        return False, "형식이 올바르지 않습니다 (예: A-01-01 또는 A-01-01-10)"

    zone, row, level = parts[0], parts[1], parts[2]

    # 구역: 영문 1자
    if not zone.isalpha() or len(zone) != 1:
        return False, "구역은 영문 1자여야 합니다 (예: A)"
    # 열: 숫자
    if not row.isdigit():
        return False, "열은 숫자여야 합니다 (예: 01)"
    # 층: 숫자
    if not level.isdigit():
        return False, "층은 숫자여야 합니다 (예: 01)"
    # 4파트 시 칸(베이): 숫자
    if len(parts) == 4:
        if not parts[3].isdigit():
            return False, "칸(4번째)은 숫자여야 합니다 (예: A-01-01-10)"

    return True, "OK"


# 테스트
if __name__ == '__main__':
    test_cases = [
        ("A-1-3", True),
        ("A-01-01", True),
        ("A-01-01-10", True),   # 4파트 약식
        ("C-02-01-15", True),
        ("B-2-5", True),
        ("A-10-1", True),
        ("AA-1-3", False),
        ("A-B-3", False),
        ("A-1", False),
        ("A-1-2-3-4", False),   # 5파트 차단
        ("A-01-03-AB", False),  # 4번째 문자 차단
        ("", False),
    ]
    for location, expected in test_cases:
        valid, msg = validate_location_format(location)
        status = "✅" if valid == expected else "❌"
        logger.debug(f"{status} '{location}': {valid} - {msg}")
