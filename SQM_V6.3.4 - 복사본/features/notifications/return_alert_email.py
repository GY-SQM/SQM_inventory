"""
SQM v6.2.7 — 반품 이메일 알림 모듈 (스텁)
============================================
반품 빈도 이상 감지 시 이메일 알림 발송.

현재: 스텁 구현 (기본 비활성)
향후: SMTP 연동, 알림 조건 설정 UI 추가 예정

테스트: tests/test_return_enhanced.py → TestReturnEmailAlert
"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════
# 설정
# ═══════════════════════════════════════════

_DEFAULT_CONFIG = {
    'enabled': False,
    'smtp_host': '',
    'smtp_port': 587,
    'smtp_user': '',
    'smtp_pass': '',
    'from_addr': '',
    'to_addrs': [],
    'threshold_count': 3,   # N건 이상 반품 시 알림
    'threshold_days': 30,   # 최근 N일 이내
}


def load_email_config() -> Dict:
    """이메일 알림 설정 로드.
    
    Returns:
        dict: 설정 (enabled, smtp_*, threshold_* 등)
    """
    # TODO: config.json 또는 DB에서 로드
    return dict(_DEFAULT_CONFIG)


# ═══════════════════════════════════════════
# 알림 감지
# ═══════════════════════════════════════════

def check_return_alerts(engine) -> List[Dict]:
    """반품 이상 감지 — threshold 초과 LOT 목록 반환.
    
    Args:
        engine: SQMInventoryEngineV3 인스턴스
        
    Returns:
        list[dict]: [{'lot_no': str, 'count': int, 'latest_date': str}, ...]
    """
    config = load_email_config()
    threshold = config.get('threshold_count', 3)
    days = config.get('threshold_days', 30)

    alerts = []
    try:
        rows = engine.db.fetchall(
            """SELECT lot_no, COUNT(*) as cnt, MAX(return_date) as latest
               FROM return_history
               WHERE return_date >= date('now', ? || ' days')
               GROUP BY lot_no
               HAVING COUNT(*) >= ?
               ORDER BY cnt DESC""",
            (f'-{days}', threshold)
        )
        for row in (rows or []):
            r = dict(row) if not isinstance(row, dict) else row
            alerts.append({
                'lot_no': r.get('lot_no', ''),
                'count': int(r.get('cnt', 0)),
                'latest_date': r.get('latest', ''),
            })
    except Exception as e:
        logger.warning(f"[반품알림] 조회 실패: {e}")

    return alerts


# ═══════════════════════════════════════════
# 이메일 발송
# ═══════════════════════════════════════════

def send_return_alert_email(engine) -> Dict:
    """반품 알림 이메일 발송.
    
    Returns:
        dict: {'sent': bool, 'count': int, 'message': str}
    """
    config = load_email_config()

    if not config.get('enabled', False):
        return {'sent': False, 'count': 0, 'message': '이메일 알림 비활성화', 'error': '이메일 알림 비활성화'}

    alerts = check_return_alerts(engine)
    if not alerts:
        return {'sent': False, 'count': 0, 'message': '알림 대상 없음', 'error': ''}

    # TODO: 실제 SMTP 발송 구현
    logger.info(f"[반품알림] {len(alerts)}건 알림 대상 감지 (발송 미구현)")
    return {
        'sent': False,
        'count': len(alerts),
        'message': f'{len(alerts)}건 감지 (SMTP 미설정)',
        'error': '',
    }
