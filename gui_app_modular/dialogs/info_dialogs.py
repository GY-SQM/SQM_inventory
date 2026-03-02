"""
SQM Inventory - Information Dialogs
===================================

v3.6.0 - 안정성/효율성/편의성 강화
- 다이얼로그 크기 표준화 (DialogSize)
- 간격 표준화 (Spacing)
- 폰트 스케일링 (FontScale)
- 컬럼 너비 표준화 (ColumnWidth)
- 중앙 배치 (center_dialog)
"""

import logging

from ..utils.ui_constants import CustomMessageBox

logger = logging.getLogger(__name__)


class InfoDialogsMixin:
    """
    Information dialogs mixin
    
    Mixed into SQMInventoryApp class
    """

    def _show_about_detail(self) -> None:
        """Show about dialog"""


        try:
            from version import __version__
            version = __version__
        except ImportError:
            version = "3.9.4"

        about_text = f"""SQM Inventory Management System

Version: {version}

Features:
- PDF/Excel inbound processing
- Tonbag-level inventory tracking
- Preflight validation (All-or-Nothing)
- Automatic backup scheduling
- Multi-format export
- API 키 검증 강화 (v3.5)
- 스마트 경로 자동 매핑 (v3.5)
- SQLite + PostgreSQL 지원 (v3.5)

(C) 2024-2026 SQM Logistics
"""
        CustomMessageBox.showinfo(self.parent, "About", about_text)
