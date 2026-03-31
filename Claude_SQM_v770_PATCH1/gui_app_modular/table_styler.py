# -*- coding: utf-8 -*-
"""
gui_app_modular/table_styler.py
================================
v6.5.4: 레거시 경로 → utils/table_styler 리다이렉트 shim.
실제 구현은 gui_app_modular/utils/table_styler.py 에 있습니다.
이 파일을 직접 수정하지 마세요.
"""
from gui_app_modular.utils.table_styler import (  # noqa: F401
    TableStyler,
    apply_table_style,
)

__all__ = ['TableStyler', 'apply_table_style']
