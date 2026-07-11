"""
SQM — Excel/PDF 보고서 공통 푸터 유틸 (P1 탈결합: core.report_footer 로 이전됨)
==============================================================================
구현은 core.report_footer 로 이전됐다. 이 모듈은 레거시 GUI 호환을 위해
core.report_footer 를 역-re-export 한다. (신규 코드는 core.report_footer 직접 사용)
"""

from core.report_footer import (  # noqa: F401
    add_gy_logistics_footer,
    add_gy_logistics_footer_pdf,
)

__all__ = [
    'add_gy_logistics_footer',
    'add_gy_logistics_footer_pdf',
]
