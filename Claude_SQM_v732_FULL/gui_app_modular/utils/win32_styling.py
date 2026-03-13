# -*- coding: utf-8 -*-
"""
SQM v7.3.2 — Windows 11 DWM 스타일링
=====================================
- 둥근 모서리 (DwmSetWindowAttribute DWMWA_WINDOW_CORNER_PREFERENCE)
- 다크 타이틀바 (DWMWA_USE_IMMERSIVE_DARK_MODE)

Windows 11 Build 22000+ 에서만 동작. 이전 버전에서는 조용히 무시.
"""
import logging
import sys

logger = logging.getLogger(__name__)

# DWM 상수
DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWCP_ROUND = 2       # 둥근 모서리
DWMWCP_ROUNDSMALL = 3  # 작은 둥근 모서리


def apply_win11_style(window, rounded: bool = True, dark_titlebar: bool = True) -> None:
    """Windows 11 네이티브 창 스타일 적용 (둥근 모서리 + 다크 타이틀바).

    Args:
        window: tkinter root 또는 Toplevel 창
        rounded: True면 둥근 모서리 적용
        dark_titlebar: True면 다크 모드 타이틀바
    """
    if sys.platform != 'win32':
        return

    try:
        import ctypes as ct

        window.update()
        hwnd = ct.windll.user32.GetParent(window.winfo_id())
        if not hwnd:
            return

        if rounded:
            val = ct.c_int(DWMWCP_ROUND)
            ct.windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_WINDOW_CORNER_PREFERENCE,
                ct.byref(val),
                ct.sizeof(val),
            )

        if dark_titlebar:
            val = ct.c_int(2)
            ct.windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                DWMWA_USE_IMMERSIVE_DARK_MODE,
                ct.byref(val),
                ct.sizeof(val),
            )

        logger.debug(f"[DWM] 스타일 적용 (rounded={rounded}, dark={dark_titlebar})")

    except Exception as e:
        # Windows 10 이하 또는 DWM 미지원 환경 — 조용히 무시
        logger.debug(f"[DWM] 스타일 적용 건너뜀: {e}")
