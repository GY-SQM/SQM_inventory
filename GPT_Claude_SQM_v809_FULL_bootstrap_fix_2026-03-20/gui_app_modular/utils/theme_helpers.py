# -*- coding: utf-8 -*-
"""Theme helper utilities for resilient dark-mode lookup."""

from __future__ import annotations

import logging
from typing import Any, Dict

from .ui_constants import ThemeColors

logger = logging.getLogger(__name__)


def safe_is_dark(app: Any = None) -> bool:
    """Return dark-mode flag without raising."""
    try:
        from .ui_constants import is_dark as _ui_is_dark

        return bool(_ui_is_dark())
    except Exception as e:
        logger.debug(f"[theme_helpers] ui_constants.is_dark 실패: {e}")

    try:
        if app is not None and hasattr(ThemeColors, "is_dark_theme"):
            theme_name = getattr(app, "current_theme", None)
            if theme_name:
                return bool(ThemeColors.is_dark_theme(theme_name))
    except Exception as e:
        logger.debug(f"[theme_helpers] current_theme 기반 판별 실패: {e}")

    try:
        if app is not None and hasattr(app, "style") and hasattr(ThemeColors, "is_dark_theme"):
            theme_name = app.style.theme_use()
            if theme_name:
                return bool(ThemeColors.is_dark_theme(theme_name))
    except Exception as e:
        logger.debug(f"[theme_helpers] style.theme_use 기반 판별 실패: {e}")

    return False


def safe_palette(app: Any = None) -> Dict[str, str]:
    """Return theme palette with hard fallback."""
    try:
        return ThemeColors.get_palette(safe_is_dark(app))
    except Exception as e:
        logger.debug(f"[theme_helpers] ThemeColors.get_palette 실패: {e}")
        return {
            "success": "#27ae60",
            "warning": "#f39c12",
            "danger": "#e74c3c",
            "text_secondary": "#7f8c8d",
            "text_primary": "#2c3e50",
            "statusbar_icon_ok": "#2ecc71",
            "statusbar_icon_warn": "#f39c12",
            "statusbar_icon_err": "#e74c3c",
        }
