# -*- coding: utf-8 -*-
"""
SQM v7.3.2 — ProButton Widget
==============================
계층화된 버튼 시스템 (Primary / Secondary / Danger / Ghost 등)
- hover 시 배경색 전환
- 계층별 명확한 시각 구분
- 아이콘 + 텍스트 조합 지원
- 클릭 피드백 (press 효과)
- 라이트/다크 테마 자동 대응

사용법:
  from gui_app_modular.utils.pro_button import ProButton, make_button_row

  btn = ProButton(parent, text="입고등록", variant="inbound", icon="📥", command=fn)

  make_button_row(parent, [
      {"text": "입고", "variant": "inbound",  "icon": "📥", "command": fn1},
      {"text": "출고", "variant": "outbound", "icon": "📤", "command": fn2},
  ])
"""
import tkinter as tk
from typing import Optional, Callable


class ProButton(tk.Button):
    """
    SQM Pro 스타일 버튼 — 라이트/다크 자동 대응.

    variant:
        'primary'   — 블루 주요 액션
        'secondary' — 슬레이트 보조 액션
        'success'   — 그린 완료/확인
        'danger'    — 레드 삭제/취소
        'ghost'     — 투명 배경 (텍스트만)
        'inbound'   — 녹색 입고 전용
        'outbound'  — 블루 출고 전용
        'report'    — 바이올렛 리포트 전용
    """

    # variant: (bg, fg, hover_bg, hover_fg, press_bg)
    VARIANTS_DARK = {
        "primary":   ("#2563eb", "#ffffff", "#1d4ed8", "#ffffff", "#1e40af"),
        "secondary": ("#475569", "#e2e8f0", "#334155", "#e2e8f0", "#1e293b"),
        "success":   ("#16a34a", "#ffffff", "#15803d", "#ffffff", "#166534"),
        "danger":    ("#dc2626", "#ffffff", "#b91c1c", "#ffffff", "#991b1b"),
        "ghost":     ("#1e293b", "#94a3b8", "#334155", "#e2e8f0", "#1e293b"),
        "inbound":   ("#16a34a", "#ffffff", "#15803d", "#ffffff", "#166534"),
        "outbound":  ("#2563eb", "#ffffff", "#1d4ed8", "#ffffff", "#1e40af"),
        "report":    ("#7c3aed", "#ffffff", "#6d28d9", "#ffffff", "#5b21b6"),
        "amber":     ("#d97706", "#ffffff", "#b45309", "#ffffff", "#92400e"),
    }

    VARIANTS_LIGHT = {
        "primary":   ("#2563eb", "#ffffff", "#1d4ed8", "#ffffff", "#1e40af"),
        "secondary": ("#e2e8f0", "#334155", "#cbd5e1", "#1e293b", "#94a3b8"),
        "success":   ("#059669", "#ffffff", "#047857", "#ffffff", "#065f46"),
        "danger":    ("#dc2626", "#ffffff", "#b91c1c", "#ffffff", "#991b1b"),
        "ghost":     ("#f8fafc", "#64748b", "#e2e8f0", "#334155", "#cbd5e1"),
        "inbound":   ("#059669", "#ffffff", "#047857", "#ffffff", "#065f46"),
        "outbound":  ("#2563eb", "#ffffff", "#1d4ed8", "#ffffff", "#1e40af"),
        "report":    ("#7c3aed", "#ffffff", "#6d28d9", "#ffffff", "#5b21b6"),
        "amber":     ("#d97706", "#ffffff", "#b45309", "#ffffff", "#92400e"),
    }

    def __init__(
        self,
        parent,
        text: str = "",
        variant: str = "secondary",
        icon: str = "",
        command: Optional[Callable] = None,
        width: int = 0,
        font_size: int = 9,
        bold: bool = False,
        padding: tuple = (12, 6),
        is_dark: bool = None,
        **kwargs
    ):
        # 자동 테마 감지
        if is_dark is None:
            try:
                from .theme_aware import ThemeAware
                is_dark = ThemeAware.is_dark()
            except (ImportError, Exception):
                is_dark = False

        variants = self.VARIANTS_DARK if is_dark else self.VARIANTS_LIGHT
        fallback = self.VARIANTS_DARK if is_dark else self.VARIANTS_LIGHT
        bg, fg, hover_bg, hover_fg, press_bg = variants.get(
            variant, fallback["secondary"]
        )
        self._bg       = bg
        self._fg       = fg
        self._hover_bg = hover_bg
        self._hover_fg = hover_fg
        self._press_bg = press_bg

        label = f"{icon} {text}".strip() if icon else text
        font_weight = "bold" if bold else "normal"
        font_spec   = ("맑은 고딕", font_size, font_weight)

        # kwargs 충돌 방지
        filtered = {k: v for k, v in kwargs.items()
                    if k not in ("bg", "fg", "relief", "bd", "cursor",
                                 "activebackground", "activeforeground", "font")}

        super().__init__(
            parent,
            text=label,
            bg=bg, fg=fg,
            font=font_spec,
            relief="flat", bd=0,
            padx=padding[0], pady=padding[1],
            cursor="hand2",
            activebackground=hover_bg,
            activeforeground=hover_fg,
            command=command,
            **filtered
        )
        if width:
            self.config(width=width)

        # hover / press 이벤트
        self.bind("<Enter>",          self._on_enter)
        self.bind("<Leave>",          self._on_leave)
        self.bind("<ButtonPress-1>",  self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    def _on_enter(self, _event=None):
        self.config(bg=self._hover_bg, fg=self._hover_fg)

    def _on_leave(self, _event=None):
        self.config(bg=self._bg, fg=self._fg)

    def _on_press(self, _event=None):
        self.config(bg=self._press_bg)

    def _on_release(self, _event=None):
        self.config(bg=self._hover_bg)


def make_button_row(parent, buttons: list, gap: int = 6, is_dark: bool = None) -> list:
    """
    버튼 목록을 한 줄로 배치.

    buttons: [
        {"text": "📥 입고", "variant": "inbound",  "command": fn},
        {"text": "📤 출고", "variant": "outbound", "command": fn},
        ...
    ]
    반환: ProButton 목록
    """
    result = []
    for spec in buttons:
        btn = ProButton(
            parent,
            text=spec.get("text", ""),
            variant=spec.get("variant", "secondary"),
            icon=spec.get("icon", ""),
            command=spec.get("command"),
            bold=spec.get("bold", False),
            padding=spec.get("padding", (12, 6)),
            is_dark=is_dark,
        )
        btn.pack(side="left", padx=(0, gap))
        result.append(btn)
    return result
