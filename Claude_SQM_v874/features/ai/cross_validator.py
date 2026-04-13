# -*- coding: utf-8 -*-
"""P2-3: CrossValidator — 서류 간 교차검증"""
import logging

logger = logging.getLogger(__name__)

class CrossValidator:
    """BL + PL + FA 서류 간 교차 검증"""

    def validate(self, bl_data, pl_data=None, fa_data=None):
        """교차검증 실행 — 6항목"""
        results = []

        if pl_data:
            results.append(self._check_lot_match(bl_data, pl_data))
            results.append(self._check_weight_match(bl_data, pl_data))
            results.append(self._check_container_match(bl_data, pl_data))

        if fa_data:
            results.append(self._check_vessel_match(bl_data, fa_data))

        results.append(self._check_date_logic(bl_data))
        results.append(self._check_tonbag_weight(bl_data))

        passed = sum(1 for r in results if r['status'] == 'PASS')
        total = len(results)

        return {
            'passed': passed,
            'total': total,
            'all_pass': passed == total,
            'results': results,
        }

    def _check_lot_match(self, bl, pl):
        """LOT번호 일치 확인"""
        bl_lot = (bl.get('lot_no') or '').strip().upper()
        pl_lot = (pl.get('lot_no') or '').strip().upper()
        if not bl_lot or not pl_lot:
            return {'name': 'LOT 번호', 'status': 'SKIP', 'message': '데이터 없음'}
        ok = bl_lot == pl_lot
        return {'name': 'LOT 번호', 'status': 'PASS' if ok else 'FAIL',
                'message': f'BL: {bl_lot} / PL: {pl_lot}'}

    def _check_weight_match(self, bl, pl):
        """수량/중량 일치 (±1kg)"""
        bl_w = self._to_float(bl.get('net_weight'))
        pl_w = self._to_float(pl.get('net_weight'))
        if bl_w is None or pl_w is None:
            return {'name': '중량', 'status': 'SKIP', 'message': '데이터 없음'}
        diff = abs(bl_w - pl_w)
        ok = diff <= 1.0
        return {'name': '중량', 'status': 'PASS' if ok else 'FAIL',
                'message': f'BL: {bl_w}kg / PL: {pl_w}kg (차이: {diff:.1f}kg)'}

    def _check_container_match(self, bl, pl):
        """컨테이너 번호 일치"""
        bl_c = (bl.get('container_no') or '').strip().upper()
        pl_c = (pl.get('container_no') or '').strip().upper()
        if not bl_c or not pl_c:
            return {'name': '컨테이너', 'status': 'SKIP', 'message': '데이터 없음'}
        ok = bl_c == pl_c
        return {'name': '컨테이너', 'status': 'PASS' if ok else 'FAIL',
                'message': f'BL: {bl_c} / PL: {pl_c}'}

    def _check_vessel_match(self, bl, fa):
        """선박명 일치"""
        bl_v = (bl.get('vessel') or '').strip().upper()
        fa_v = (fa.get('vessel') or '').strip().upper()
        if not bl_v or not fa_v:
            return {'name': '선박명', 'status': 'SKIP', 'message': '데이터 없음'}
        ok = bl_v in fa_v or fa_v in bl_v
        return {'name': '선박명', 'status': 'PASS' if ok else 'FAIL',
                'message': f'BL: {bl_v} / FA: {fa_v}'}

    def _check_date_logic(self, data):
        """날짜 논리: 선적일 < 도착일"""
        ship = data.get('ship_date', '')
        arrival = data.get('arrival_date', '')
        if not ship or not arrival:
            return {'name': '날짜 논리', 'status': 'SKIP', 'message': '데이터 없음'}
        ok = ship <= arrival
        return {'name': '날짜 논리', 'status': 'PASS' if ok else 'FAIL',
                'message': f'선적: {ship} / 도착: {arrival}'}

    def _check_tonbag_weight(self, data):
        """톤백수 x 단가 = 총중량"""
        count = self._to_float(data.get('tonbag_count'))
        weight = self._to_float(data.get('tonbag_weight'))
        total = self._to_float(data.get('net_weight'))
        if count is None or weight is None or total is None:
            return {'name': '톤백x중량', 'status': 'SKIP', 'message': '데이터 없음'}
        calc = count * weight
        diff = abs(calc - total)
        ok = diff <= 1.0
        return {'name': '톤백x중량', 'status': 'PASS' if ok else 'FAIL',
                'message': f'{int(count)}x{weight}={calc:.1f} vs 총{total:.1f} (차이: {diff:.1f})'}

    def _to_float(self, v):
        if v is None:
            return None
        try:
            return float(str(v).replace(',', ''))
        except (ValueError, TypeError):
            return None
