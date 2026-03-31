"""
SQM Inventory v3.5 - UI 통일성 상수 및 계산기
=============================================

UI 가시성 및 통일성을 위한 중앙 집중식 설정

사용법:
    from gui_app_modular.utils.ui_constants import (
        UICalculator, FontScale, Spacing, ColumnWidth,
        ThemeColors, DialogSize, center_dialog
    )
"""

import json
import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# 화물(톤백) 상태 표시명 — v7.2.0: OUTBOUND/RETURN 신규 상태 추가
STATUS_DISPLAY = {
    'AVAILABLE': '판매가능',
    'RESERVED': '판매배정',
    'PICKED': '판매화물 결정',
    'OUTBOUND': '출고완료',    # v7.2.0 신규
    'SOLD': '출고완료',        # 하위호환 (OUTBOUND와 동일 표시)
    'RETURN': '반품대기',      # v7.2.0 신규: 반품 입고 후 location 지정 전
    'SHIPPED': '선적',
    'DEPLETED': '소진',
    'RETURNED': '반품',
    'PARTIAL': '부분출고',
}

# 한글 표시명 → DB 값 (필터·다이얼로그 저장 시 사용)
STATUS_DISPLAY_TO_DB = {v: k for k, v in STATUS_DISPLAY.items()}


def get_status_display(status: str) -> str:
    """DB 상태값 → 화면 표시명. 없으면 원문 반환."""
    if not status:
        return ''
    return STATUS_DISPLAY.get(str(status).strip().upper(), str(status))


# ═══════════════════════════════════════════════════════════════
# Excel/데이터 입력 원칙 — 전체 프로그램 통일 (AGENTS.md Upload Principle)
# ═══════════════════════════════════════════════════════════════
# 형식은 프로그램 내장 → 사용자는 [데이터 붙여넣기] 또는 [파일 업로드] 중 하나 선택
UPLOAD_CHOICE_HEADER = "프로그램이 정한 형식은 내장되어 있습니다. 다음 중 하나를 선택하세요."
UPLOAD_CHOICE_PASTE = "① 데이터 붙여넣기: 프로그램 화면에 표가 열립니다. Excel 등에서 복사한 데이터를 붙여넣기(Ctrl+V) 한 뒤 반영합니다."
UPLOAD_CHOICE_UPLOAD = "② 파일 업로드: 이미 채운 엑셀 파일을 선택하여 업로드합니다."
UPLOAD_CHOICE_BTN_PASTE = "📋 데이터 붙여넣기"
UPLOAD_CHOICE_BTN_UPLOAD = "📤 파일 업로드"


# ═══════════════════════════════════════════════════════════════
# 1. 화면 해상도 기반 크기 계산
# ═══════════════════════════════════════════════════════════════

class UICalculator:
    """
    화면 해상도 및 DPI 기반 UI 크기 계산기
    
    사용법:
        calc = UICalculator(root)
        width = calc.scaled(100)  # DPI에 맞게 스케일링된 값
    """

    # 기준 해상도 (Full HD)
    BASE_WIDTH = 1920
    BASE_HEIGHT = 1080
    BASE_DPI = 96

    def __init__(self, root=None):
        if root:
            self.screen_width = root.winfo_screenwidth()
            self.screen_height = root.winfo_screenheight()
            try:
                self.dpi = root.winfo_fpixels('1i')
            except (RuntimeError, ValueError):
                self.dpi = self.BASE_DPI
        else:
            # 기본값
            self.screen_width = self.BASE_WIDTH
            self.screen_height = self.BASE_HEIGHT
            self.dpi = self.BASE_DPI

    @property
    def scale_factor(self) -> float:
        """화면 크기 기반 스케일 팩터"""
        width_scale = self.screen_width / self.BASE_WIDTH
        height_scale = self.screen_height / self.BASE_HEIGHT
        return min(width_scale, height_scale)

    @property
    def dpi_scale(self) -> float:
        """DPI 기반 스케일 팩터"""
        return self.dpi / self.BASE_DPI

    @property
    def combined_scale(self) -> float:
        """통합 스케일 팩터"""
        return max(1.0, self.dpi_scale)  # 최소 1.0 보장

    def scaled(self, value: int) -> int:
        """값을 DPI에 맞게 스케일링"""
        return int(value * self.combined_scale)

    def get_main_window_size(self) -> Tuple[int, int]:
        """메인 윈도우 권장 크기"""
        width = int(self.screen_width * 0.75)
        height = int(self.screen_height * 0.80)

        # 최소/최대 제한
        width = max(1000, min(width, 1800))
        height = max(700, min(height, 1200))

        return width, height

    def get_min_window_size(self) -> Tuple[int, int]:
        """최소 윈도우 크기"""
        return (
            max(1000, int(self.screen_width * 0.5)),
            max(700, int(self.screen_height * 0.5))
        )


# ═══════════════════════════════════════════════════════════════
# 2. 폰트 스케일링
# ═══════════════════════════════════════════════════════════════

class FontStyle(Enum):
    """폰트 스타일 열거형"""
    TITLE = 'title'
    SUBTITLE = 'subtitle'
    HEADING = 'heading'
    BODY = 'body'
    SMALL = 'small'
    TINY = 'tiny'
    MONO = 'mono'


class FontScale:
    """
    DPI 인식 폰트 크기 관리
    
    사용법:
        fonts = FontScale(dpi=120)
        title_font = fonts.get_font(FontStyle.TITLE, 'bold')
        # ('맑은 고딕', 20, 'bold')
    """

    # 기준 폰트 크기 (96 DPI 기준) — v3.8.7: 30% 확대
    BASE_SIZES = {
        FontStyle.TITLE:    21,   # 16 → 21
        FontStyle.SUBTITLE: 18,   # 14 → 18
        FontStyle.HEADING:  16,   # 12 → 16
        FontStyle.BODY:     13,   # 10 → 13
        FontStyle.SMALL:    12,   #  9 → 12
        FontStyle.TINY:     10,   #  8 → 10
        FontStyle.MONO:     13,   # 10 → 13
    }

    # 폰트 패밀리
    FONT_FAMILY = '맑은 고딕'
    MONO_FAMILY = 'Consolas'

    def __init__(self, dpi: float = 96):
        self.dpi = dpi
        self.scale = max(1.0, dpi / 96)

    def get_size(self, style: FontStyle) -> int:
        """스케일링된 폰트 크기 반환"""
        base = self.BASE_SIZES.get(style, 10)
        scaled = int(base * self.scale)
        return max(scaled, 8)  # 최소 8pt

    def get_font(self, style: FontStyle, weight: str = 'normal') -> Tuple[str, int, str]:
        """tkinter 폰트 튜플 반환"""
        size = self.get_size(style)
        family = self.MONO_FAMILY if style == FontStyle.MONO else self.FONT_FAMILY
        return (family, size, weight)

    # 편의 메서드
    def title(self, bold: bool = True) -> Tuple[str, int, str]:
        return self.get_font(FontStyle.TITLE, 'bold' if bold else 'normal')

    def subtitle(self, bold: bool = False) -> Tuple[str, int, str]:
        return self.get_font(FontStyle.SUBTITLE, 'bold' if bold else 'normal')

    def heading(self, bold: bool = True) -> Tuple[str, int, str]:
        return self.get_font(FontStyle.HEADING, 'bold' if bold else 'normal')

    def body(self, bold: bool = False) -> Tuple[str, int, str]:
        return self.get_font(FontStyle.BODY, 'bold' if bold else 'normal')

    def small(self) -> Tuple[str, int, str]:
        return self.get_font(FontStyle.SMALL)

    def mono(self) -> Tuple[str, int, str]:
        return self.get_font(FontStyle.MONO)


# ═══════════════════════════════════════════════════════════════
# 3. 간격 시스템 (8px 그리드)
# ═══════════════════════════════════════════════════════════════

class Spacing:
    """
    8px 그리드 기반 간격 시스템
    
    사용법:
        frame = ttk.Frame(parent, padding=Spacing.MD)
        btn.pack(padx=Spacing.SM, pady=Spacing.XS)
    """

    # 기본 단위
    UNIT = 8

    # 스케일
    XS = UNIT // 2      # 4px
    SM = UNIT           # 8px
    MD = UNIT * 2       # 16px
    LG = UNIT * 3       # 24px
    XL = UNIT * 4       # 32px
    XXL = UNIT * 6      # 48px

    # 용도별 권장값
    class Padding:
        DIALOG = 16         # 다이얼로그 내부
        FRAME = 8           # 일반 프레임
        LABELFRAME = 16     # LabelFrame 내부
        BUTTON_GROUP = 8    # 버튼 사이
        SECTION = 24        # 섹션 사이



# ═══════════════════════════════════════════════════════════════
# 4. 다이얼로그 크기
# ═══════════════════════════════════════════════════════════════

@dataclass
class DialogSizeConfig:
    """다이얼로그 크기 설정"""
    width_ratio: float
    height_ratio: float
    min_size: Tuple[int, int]
    max_size: Tuple[int, int]


class DialogSize:
    """
    다이얼로그 크기 계산
    
    사용법:
        width, height = DialogSize.calculate(parent, 'medium')
    """

    CONFIGS = {
        'small': DialogSizeConfig(0.25, 0.20, (350, 200), (500, 350)),
        'medium': DialogSizeConfig(0.40, 0.50, (500, 400), (800, 600)),
        'large': DialogSizeConfig(0.60, 0.70, (700, 500), (1200, 900)),
        'full': DialogSizeConfig(0.85, 0.85, (1000, 700), (1600, 1000)),
    }

    @classmethod
    def calculate(cls, parent, size_type: str = 'medium') -> Tuple[int, int]:
        """부모 창 기준 다이얼로그 크기 계산"""
        config = cls.CONFIGS.get(size_type, cls.CONFIGS['medium'])

        try:
            parent_width = parent.winfo_width()
            parent_height = parent.winfo_height()
        except (RuntimeError, ValueError):
            parent_width = 1200
            parent_height = 800

        width = int(parent_width * config.width_ratio)
        height = int(parent_height * config.height_ratio)

        # 최소/최대 제한
        width = max(config.min_size[0], min(width, config.max_size[0]))
        height = max(config.min_size[1], min(height, config.max_size[1]))

        return width, height

    @classmethod
    def get_geometry(cls, parent, size_type: str = 'medium') -> str:
        """geometry 문자열 반환"""
        width, height = cls.calculate(parent, size_type)
        return f"{width}x{height}"


# ═══════════════════════════════════════════════════════════════
# 5. 컬럼 너비 계산
# ═══════════════════════════════════════════════════════════════

class ColumnWidth:
    """
    테이블 컬럼 너비 계산
    
    사용법:
        width = ColumnWidth.get('lot_no')
        anchor = ColumnWidth.get_anchor('weight')
    """

    # 문자 타입별 평균 너비 (픽셀)
    CHAR_WIDTH = {
        'number': 8,
        'letter': 7,
        'korean': 14,
        'mixed': 10,
    }

    # 필드별 설정
    SPECS = {
        'lot_no': {'type': 'mixed', 'chars': 15, 'min': 120, 'max': 150, 'anchor': 'center'},
        'sap_no': {'type': 'number', 'chars': 12, 'min': 100, 'max': 130, 'anchor': 'center'},
        'bl_no': {'type': 'mixed', 'chars': 12, 'min': 100, 'max': 130, 'anchor': 'center'},
        'weight': {'type': 'number', 'chars': 10, 'min': 80, 'max': 110, 'anchor': 'e'},
        'quantity': {'type': 'number', 'chars': 5, 'min': 50, 'max': 80, 'anchor': 'center'},
        'product': {'type': 'korean', 'chars': 12, 'min': 100, 'max': 200, 'anchor': 'center'},
        'customer': {'type': 'korean', 'chars': 15, 'min': 120, 'max': 250, 'anchor': 'center'},
        'date': {'type': 'number', 'chars': 10, 'min': 85, 'max': 100, 'anchor': 'center'},
        'status': {'type': 'letter', 'chars': 10, 'min': 70, 'max': 100, 'anchor': 'center'},
        'sub_lt': {'type': 'number', 'chars': 3, 'min': 50, 'max': 70, 'anchor': 'center'},
        'location': {'type': 'mixed', 'chars': 8, 'min': 60, 'max': 100, 'anchor': 'center'},
    }

    @classmethod
    def get(cls, field: str, font_size: int = 10) -> int:
        """필드별 권장 너비 계산"""
        spec = cls.SPECS.get(field)
        if not spec:
            return 100

        font_scale = font_size / 10
        char_width = cls.CHAR_WIDTH[spec['type']] * font_scale
        width = int(spec['chars'] * char_width) + 20

        return max(spec['min'], min(width, spec['max']))

    @classmethod
    def get_anchor(cls, field: str) -> str:
        """필드별 정렬 방향"""
        spec = cls.SPECS.get(field, {})
        return spec.get('anchor', 'center')

    @classmethod
    def configure_column(cls, tree, field: str, heading: str, font_size: int = 10):
        """트리뷰 컬럼 설정"""
        width = cls.get(field, font_size)
        anchor = cls.get_anchor(field)
        tree.heading(field, text=heading)
        tree.column(field, width=width, anchor=anchor)


# ═══════════════════════════════════════════════════════════════
# 6. 테마 인식 색상
# ═══════════════════════════════════════════════════════════════

class ThemeColors:
    """
    다크모드 대응 색상 시스템 (v3.6.2: 가독성 대폭 개선)
    
    사용법:
        color = ThemeColors.get('available', is_dark=True)
    """

    LIGHT = {
        # Semantic
        'success': '#059669',    # Emerald 600
        'warning': '#D97706',    # Amber 600
        'danger':  '#DC2626',    # Red 600
        'info':    '#2563EB',    # Blue accent (mockup)
        'primary': '#1E40AF',    # Blue 800

        # Status
        'available': '#D1FAE5',
        'picked':    '#EDE9FE',
        'reserved':  '#FEF3C7',
        'shipped':   '#DBEAFE',

        # Text
        'text_primary':   '#0F172A',  # Slate 900 (mockup)
        'text_secondary': '#475569',  # Slate 600
        'text_muted':     '#94A3B8',  # Slate 400

        # Background
        'bg_primary':   '#F8FAFC',  # Slate 50 (mockup bg)
        'bg_secondary': '#F1F5F9',  # Slate 100
        'bg_hover':     '#E2E8F0',  # Slate 200
        'bg_toolbar':   '#F1F5F9',
        'bg_card':      '#FFFFFF',  # Pure white (mockup)

        # Border
        'border':       '#E2E8F0',  # Slate 200
        'border_focus': '#2563EB',  # Blue accent

        # Buttons
        'btn_inbound':        '#059669',
        'btn_inbound_hover':  '#34D399',
        'btn_outbound':       '#D97706',
        'btn_outbound_hover': '#FBBF24',
        'btn_report':         '#2563EB',
        'btn_report_hover':   '#60A5FA',
        'btn_neutral':        '#64748B',
        'btn_neutral_hover':  '#94A3B8',

        # Treeview
        'tree_select_bg':  '#DBEAFE',  # Blue 100
        'tree_select_fg':  '#1E3A5F',
        'tree_stripe':     '#F8FAFC',

        # Charts
        'chart_bg':   '#FFFFFF',
        'chart_grid': '#E2E8F0',

        # Search
        'search_bg':          '#FFFFFF',
        'search_fg':          '#0F172A',
        'search_border':      '#E2E8F0',
        'search_placeholder': '#94A3B8',
        'search_cursor':      '#0F172A',

        # Statusbar
        'statusbar_bg':       '#1E293B',
        'statusbar_fg':       '#FFFFFF',
        'statusbar_icon_ok':  '#059669',
        'statusbar_icon_warn':'#D97706',
        'statusbar_icon_err': '#DC2626',
        'statusbar_progress': '#2563EB',
        'statusbar_progress_done': '#059669',
        'statusbar_track':    '#334155',

        # Badges
        'badge_db':           '#059669',
        'badge_version':      '#2563EB',
        'badge_text':         '#FFFFFF',

        # Misc
        'arrow_separator':    '#CBD5E1',
        'shortcut_text':      '#94A3B8',
        'shortcut_text_dim':  '#CBD5E1',
        'canvas_highlight':   '#0F172A',
    }

    DARK = {
        # Semantic
        'success': '#34D399',    # Emerald 400
        'warning': '#FBBF24',    # Amber 400
        'danger':  '#F87171',    # Red 400
        'info':    '#22C5D6',    # Teal accent (mockup)
        'primary': '#2563EB',    # Blue 600

        # Status (Treeview rows)
        'available': '#064E3B',  # Emerald 900 bg
        'reserved':  '#78350F',  # Amber 900 bg
        'picked':    '#4C1D95',  # Violet 900 bg
        'shipped':   '#1E3A5F',  # Blue 900 bg

        # Text
        'text_primary':   '#E5E7EB',  # Gray 200 (mockup)
        'text_secondary': '#9CA3AF',  # Gray 400
        'text_muted':     '#6B7280',  # Gray 500

        # Background
        'bg_primary':   '#0B1220',  # Deep navy (mockup bg)
        'bg_secondary': '#111B2E',  # Slightly lighter
        'bg_hover':     '#1E293B',  # Slate 800
        'bg_toolbar':   '#0F1729',  # Toolbar
        'bg_card':      '#162033',  # Card (mockup)

        # Border
        'border':       '#1E293B',  # Slate 800
        'border_focus': '#22C5D6',  # Teal accent

        # Buttons
        'btn_inbound':        '#059669',  # Emerald 600
        'btn_inbound_hover':  '#34D399',
        'btn_outbound':       '#D97706',  # Amber 600
        'btn_outbound_hover': '#FBBF24',
        'btn_report':         '#2563EB',  # Blue 600
        'btn_report_hover':   '#60A5FA',
        'btn_neutral':        '#475569',  # Slate 600
        'btn_neutral_hover':  '#64748B',

        # Treeview
        'tree_select_bg':  '#2563EB',
        'tree_select_fg':  '#FFD700',  # Gold
        'tree_stripe':     '#111B2E',

        # Charts
        'chart_bg':   '#0B1220',
        'chart_grid': '#1E293B',

        # Search
        'search_bg':          '#162033',
        'search_fg':          '#E5E7EB',
        'search_border':      '#1E293B',
        'search_placeholder': '#6B7280',
        'search_cursor':      '#E5E7EB',

        # Statusbar
        'statusbar_bg':       '#0F1729',
        'statusbar_fg':       '#E5E7EB',
        'statusbar_icon_ok':  '#34D399',
        'statusbar_icon_warn':'#FBBF24',
        'statusbar_icon_err': '#F87171',
        'statusbar_progress': '#22C5D6',
        'statusbar_progress_done': '#34D399',
        'statusbar_track':    '#1E293B',

        # Badges
        'badge_db':           '#34D399',
        'badge_version':      '#22C5D6',
        'badge_text':         '#FFFFFF',

        # Misc
        'arrow_separator':    '#475569',
        'shortcut_text':      '#9CA3AF',
        'shortcut_text_dim':  '#6B7280',
        'canvas_highlight':   '#E5E7EB',
    }


    @classmethod
    def is_dark_theme(cls, theme_name: str) -> bool:
        """다크 테마 여부 확인"""
        return theme_name.lower() in ('darkly',)

    @classmethod
    def get(cls, key: str, is_dark: bool = False) -> str:
        """현재 테마에 맞는 색상 반환"""
        palette = cls.DARK if is_dark else cls.LIGHT
        return palette.get(key, '#000000')

    @classmethod
    def get_palette(cls, is_dark: bool = False) -> dict:
        """전체 팔레트 반환"""
        return cls.DARK.copy() if is_dark else cls.LIGHT.copy()

    @classmethod
    def configure_tags(cls, tree, is_dark: bool = False):
        """트리뷰 상태 태그 설정 (v7.7.0: 프리미엄 팔레트)"""
        p = cls.DARK if is_dark else cls.LIGHT
        fg = p['text_primary']
        if is_dark:
            status_fg = {
                'available': '#6EE7B7',
                'reserved':  '#FCD34D',
                'picked':    '#C4B5FD',
                'shipped':   '#93C5FD',
            }
        else:
            status_fg = {
                'available': '#064E3B',
                'reserved':  '#78350F',
                'picked':    '#4C1D95',
                'shipped':   '#1E3A5F',
            }
        for status in ['available', 'picked', 'reserved', 'shipped']:
            tree.tag_configure(status, background=p[status],
                               foreground=status_fg.get(status, fg))
        tree.tag_configure('depleted',
                          background='#F1F5F9' if not is_dark else '#111B2E',
                          foreground='#94A3B8' if not is_dark else '#6B7280')
        tree.tag_configure('stripe', background=p['tree_stripe'], foreground=fg)


# ═══════════════════════════════════════════════════════════════
# 6-2. 글로벌 가독성 스타일 (v3.6.2 신규)
# ═══════════════════════════════════════════════════════════════

class ReadableStyle:
    """
    v3.6.2: 전체 앱에 가독성 좋은 스타일을 일괄 적용
    
    - Treeview: 행 높이 28→32px, 교대 줄무늬, 부드러운 선택색
    - Notebook 탭: 패딩 확대, 폰트 개선
    - LabelFrame: 테두리 부드러운 색상
    - Entry/Combobox: 패딩, 포커스 색상
    
    사용법:
        from gui_app_modular.utils.ui_constants import ReadableStyle
        ReadableStyle.apply(root, theme_name='flatly')
    """

    # Treeview 행 높이 (v8.7.0 Phase1: 36px로 가독성 개선)
    ROW_HEIGHT = 36

    # 기본 폰트 — v3.8.7: 30% 확대
    FONT_FAMILY = '맑은 고딕'
    FONT_SIZE = 13       # 10 → 13
    HEADING_SIZE = 13    # 10 → 13

    @classmethod
    def apply(cls, root, theme_name: str = 'flatly'):
        """전체 가독성 스타일 적용"""
        try:
            is_dark = ThemeColors.is_dark_theme(theme_name)
            p = ThemeColors.get_palette(is_dark)

            style = None
            try:
                style = root.style  # ttkbootstrap
            except AttributeError:
                try:
                    import tkinter.ttk as _ttk
                    style = _ttk.Style()
                except (RuntimeError, ValueError) as e:
                    logger.debug(f"{type(e).__name__}: {e}")

            if not style:
                logger.warning("Style 객체 없음 - 가독성 스타일 건너뜀")
                return

            # ─── Root Window Background ───
            try:
                root.configure(background=p['bg_primary'])
            except Exception:
                pass

            # ─── ttkbootstrap Colors Override (CRITICAL) ───
            if hasattr(style, 'colors'):
                try:
                    # ttkbootstrap의 색상 정의 자체를 변경하여 모든 위젯에 전파되도록 함
                    style.colors.bg = p['bg_primary']
                    style.colors.fg = p['text_primary']
                    style.colors.selectbg = p['tree_select_bg']
                    style.colors.selectfg = p['tree_select_fg']
                    style.colors.border = p['border']
                    style.colors.inputbg = p['bg_secondary']
                    style.colors.inputfg = p['text_primary']
                    
                    # Primary/Secondary 등 주요 색상도 매핑
                    style.colors.primary = p['primary'] 
                    style.colors.secondary = p['bg_secondary']
                    style.colors.success = p['success']
                    style.colors.info = p['info']
                    style.colors.warning = p['warning']
                    style.colors.danger = p['danger']
                    style.colors.light = p['text_primary']
                    style.colors.dark = p['bg_primary']
                    
                    logger.info("✅ ttkbootstrap.style.colors 오버라이드 완료")
                except Exception as _ce:
                    logger.warning(f"ttkbootstrap colors 오버라이드 실패: {_ce}")

            # ─── Treeview ─── (v6.1.1: foreground/background 명시, !selected 추가)
            style.configure(
                'Treeview',
                rowheight=cls.ROW_HEIGHT,
                font=(cls.FONT_FAMILY, cls.FONT_SIZE),
                borderwidth=0,
                relief='flat',
                foreground=p['text_primary'],
                background=p['bg_card'],
                fieldbackground=p['bg_card'],
            )
            style.configure(
                'Treeview.Heading',
                font=(cls.FONT_FAMILY, cls.HEADING_SIZE, 'bold'),
                padding=(8, 6),
                relief='flat',
                foreground=p['text_primary'],
                background=p['bg_secondary'],
            )
            style.map(
                'Treeview',
                background=[('selected', p['tree_select_bg'])],
                foreground=[
                    ('selected', p['tree_select_fg']),
                    ('!selected', p['text_primary']),
                ],
            )

            # ─── Frame & Label (Global Background Override) ───
            # 기본 프레임과 라벨도 테마 색상을 따르도록 강제
            style.configure('.', background=p['bg_primary'], foreground=p['text_primary']) # 모든 위젯 기본 배경/글자색
            style.configure('TFrame', background=p['bg_primary'])
            style.configure('TLabel', background=p['bg_primary'], foreground=p['text_primary'])
            style.configure('TLabelframe', background=p['bg_primary'], foreground=p['text_primary'], bordercolor=p['border'])
            style.configure('TLabelframe.Label', background=p['bg_primary'], foreground=p['text_primary'])
            
            # ─── Button (Global Override) ───
            style.configure('TButton', font=(cls.FONT_FAMILY, cls.FONT_SIZE))

            # ─── Notebook 탭 ───
            style.configure(
                'TNotebook',
                background=p['bg_primary'],
                borderwidth=0
            )
            style.configure(
                'TNotebook.Tab',
                padding=(16, 8),
                font=(cls.FONT_FAMILY, cls.FONT_SIZE),
                background=p['bg_secondary'],
                foreground=p['text_muted']
            )
            style.map(
                'TNotebook.Tab',
                background=[('selected', p['bg_primary'])],
                foreground=[('selected', p['text_primary'])],
                expand=[('selected', [1, 1, 1, 0])]
            )

            # ─── LabelFrame ───
            style.configure(
                'TLabelframe',
                borderwidth=1,
                relief='solid',
            )
            style.configure(
                'TLabelframe.Label',
                font=(cls.FONT_FAMILY, cls.FONT_SIZE, 'bold'),
            )

            # ─── Entry ───
            style.configure(
                'TEntry',
                padding=(6, 4),
            )

            # ─── Combobox ───
            style.configure(
                'TCombobox',
                padding=(6, 4),
            )

            # ─── Separator ───
            style.configure(
                'TSeparator',
                background=p['border'],
            )

            logger.info(f"[v3.6.2] ReadableStyle 적용 완료 (theme={theme_name}, dark={is_dark})")

        except (ValueError, TypeError, AttributeError) as e:
            logger.warning(f"ReadableStyle 적용 실패: {e}")

    @classmethod
    def get_toolbar_colors(cls, is_dark: bool = False) -> dict:
        """v3.6.2: 눈이 편안한 툴바 색상 팔레트 반환
        
        ⚠ DEPRECATED (v5.5.3 patch_01): toolbar_mixin이 style.colors를 직접 사용.
        하위 호환성을 위해 유지하나, 새 코드에서는 사용하지 마세요.
        """
        p = ThemeColors.get_palette(is_dark)
        return {
            'inbound':  {
                'bg': p['btn_inbound'], 'hover': p['btn_inbound_hover'],
                'text': '#ffffff', 'icon': '📥'
            },
            'outbound': {
                'bg': p['btn_outbound'], 'hover': p['btn_outbound_hover'],
                'text': '#ffffff', 'icon': '📤'
            },
            'report':   {
                'bg': p['btn_report'], 'hover': p['btn_report_hover'],
                'text': '#ffffff', 'icon': '📊'
            },
            'neutral':  {
                'bg': p['btn_neutral'], 'hover': p['btn_neutral_hover'],
                'text': '#ffffff'
            },
            'toolbar_bg':   p['bg_toolbar'],
            'statusbar_bg': p.get('bg_primary', '#1E293B') if is_dark else '#1E293B',
        }


# ═══════════════════════════════════════════════════════════════
# 7. 다이얼로그 위치 유틸리티
# ═══════════════════════════════════════════════════════════════

def center_dialog(dialog, parent=None):
    """
    다이얼로그를 부모 창 중앙에 배치
    
    사용법:
        dialog = tk.Toplevel(root)
        dialog.geometry("600x400")
        center_dialog(dialog, root)
    """
    dialog.update_idletasks()

    dialog_width = dialog.winfo_width()
    dialog_height = dialog.winfo_height()

    if parent:
        # 부모 창 중앙
        parent_x = parent.winfo_x()
        parent_y = parent.winfo_y()
        parent_width = parent.winfo_width()
        parent_height = parent.winfo_height()

        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
    else:
        # 화면 중앙
        screen_width = dialog.winfo_screenwidth()
        screen_height = dialog.winfo_screenheight()

        x = (screen_width - dialog_width) // 2
        y = (screen_height - dialog_height) // 2

    # 화면 범위 내 유지
    screen_width = dialog.winfo_screenwidth()
    screen_height = dialog.winfo_screenheight()

    x = max(0, min(x, screen_width - dialog_width))
    y = max(0, min(y, screen_height - dialog_height))

    dialog.geometry(f"+{x}+{y}")


def apply_tooltip(widget, text: str, delay: int = 250):
    """
    위젯에 ttkbootstrap ToolTip 적용 (v3.6.5)
    
    ttkbootstrap 미설치 시 자동 무시 (안전 fallback).
    
    사용법:
        apply_tooltip(my_button, '이 버튼은 데이터를 저장합니다')
    """
    # 전역 정책: 툴팁 120자 이내
    if text is None:
        text = ""
    text = str(text).strip()
    if len(text) > 120:
        text = text[:117].rstrip() + "..."
    try:
        from .constants import HAS_TOOLTIP, ToolTip
        if HAS_TOOLTIP and ToolTip:
            ToolTip(widget, text=text, delay=delay)
    except (ImportError, ModuleNotFoundError) as e:
        logger.debug(f"{type(e).__name__}: {e}")


def apply_modal_window_options(dialog) -> None:
    """
    모달 창에 크기 조절 + 최소/최대 버튼 적용.
    resizable(True,True) 및 toolwindow=False(Windows 표준 창 장식).
    """
    try:
        dialog.resizable(True, True)
        try:
            dialog.attributes('-toolwindow', 0)
        except (Exception, AttributeError) as e:
            logger.debug(f"[apply_modal_window_options] Suppressed: {e}")
    except (Exception, AttributeError) as e:
        logger.debug(f"[apply_modal_window_options] Suppressed: {e}")


def apply_contrast_scrollbar_style(root, theme_name: str = 'flatly') -> None:
    """전역 Scrollbar 대비색/두께 적용 (tk.Scrollbar 기준)."""
    try:
        is_dark = ThemeColors.is_dark_theme(theme_name)
        trough = '#0B1220' if is_dark else '#F1F5F9'
        thumb = '#475569' if is_dark else '#94A3B8'
        active = '#64748B' if is_dark else '#64748B'
        width = 16

        # 이후 생성되는 Scrollbar 기본값
        root.option_add('*Scrollbar.width', width)
        root.option_add('*Scrollbar.troughColor', trough)
        root.option_add('*Scrollbar.background', thumb)
        root.option_add('*Scrollbar.activeBackground', active)
        root.option_add('*Scrollbar.relief', 'solid')
        root.option_add('*Scrollbar.borderWidth', 1)
        root.option_add('*Scrollbar.highlightThickness', 0)

        # 이미 생성된 Scrollbar에도 즉시 적용
        def _walk(widget):
            try:
                children = widget.winfo_children()
            except Exception:
                children = []
            for child in children:
                if child.winfo_class() == 'Scrollbar':
                    try:
                        child.configure(
                            width=width,
                            troughcolor=trough,
                            bg=thumb,
                            activebackground=active,
                            relief='solid',
                            bd=1,
                            highlightthickness=0,
                        )
                    except Exception:
                        pass
                _walk(child)

        _walk(root)
    except Exception as e:
        logger.debug(f"[apply_contrast_scrollbar_style] Suppressed: {e}")


# ═══════════════════════════════════════════════════════════════
# 창 크기 저장/복원 (메인 + 하위/팝업 공통)
# ═══════════════════════════════════════════════════════════════

def _geometry_config_path():
    """window_config.json 경로 (메인 창과 동일)."""
    from pathlib import Path
    try:
        from .constants import WINDOW_CONFIG_FILE
        if WINDOW_CONFIG_FILE:
            return Path(WINDOW_CONFIG_FILE)
    except (ImportError, AttributeError) as e:
        logger.debug(f"[_geometry_config_path] Suppressed: {e}")
    return Path(__file__).resolve().parent.parent / "window_config.json"


def load_all_geometry() -> dict:
    """저장된 창 설정 전체 로드. {'width','height','x','y', 'dialogs': {key: 'WxH+x+y'}}."""
    path = _geometry_config_path()
    try:
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        logger.debug(f"Geometry config load: {e}")
    return {}


def save_geometry_config(config: dict) -> None:
    """창 설정 전체 저장. config에 dialogs 등 기존 키 유지."""
    path = _geometry_config_path()
    try:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    except OSError as e:
        logger.debug(f"Geometry config save: {e}")


def load_dialog_geometry(key: str) -> Optional[str]:
    """다이얼로그용 저장된 geometry 문자열. 없으면 None."""
    data = load_all_geometry()
    dialogs = data.get('dialogs') or {}
    return dialogs.get(key)


def save_dialog_geometry(key: str, geometry: str) -> None:
    """다이얼로그 크기/위치 저장. 기존 메인 창 설정은 유지."""
    config = load_all_geometry()
    if 'dialogs' not in config or not isinstance(config['dialogs'], dict):
        config['dialogs'] = {}
    config['dialogs'][key] = geometry
    save_geometry_config(config)


def setup_dialog_geometry_persistence(
    dialog,
    key: str,
    parent,
    default_size_type: str = 'large',
) -> None:
    """
    다이얼로그에 직전 사용 크기 복원 + 닫을 때 저장.
    - key: 창 구분용 (예: 'allocation_dialog', 'picking_preview')
    - default_size_type: 저장값 없을 때 사용할 크기 ('large' 권장)
    """
    apply_modal_window_options(dialog)
    saved = load_dialog_geometry(key)
    if saved and re.match(r'^\d+x\d+(\+-?\d+\+-?\d+)?$', saved.strip()):
        try:
            dialog.geometry(saved)
        except Exception as _ge:
            logging.getLogger(__name__).debug(f"[UI] 다이얼로그 geometry 복원 실패: {_ge}")
    if not saved or not dialog.winfo_geometry().strip():
        w, h = DialogSize.calculate(parent, default_size_type)
        dialog.geometry(f"{w}x{h}")
        center_dialog(dialog, parent)
    dialog.update_idletasks()

    def _on_save_geometry(e=None):
        try:
            g = dialog.winfo_geometry()
            if g and re.match(r'^\d+x\d+', g):
                save_dialog_geometry(key, g)
        except (RuntimeError, Exception) as _e:
            logger.debug(f"[_on_save_geometry] Suppressed: {_e}")

    dialog.bind('<Destroy>', _on_save_geometry, add='+')


def setup_dialog_defaults(dialog, parent, title: str, size_type: str = 'medium'):
    """
    다이얼로그 기본 설정 (크기, 위치, 동작)
    - 크기 조절 가능, 최소/최대 버튼 표시
    """
    # 제목
    dialog.title(title)

    # 크기
    geometry = DialogSize.get_geometry(parent, size_type)
    dialog.geometry(geometry)

    # 크기 조절 + 최소/최대 버튼
    apply_modal_window_options(dialog)

    # 부모 연결
    dialog.transient(parent)
    dialog.grab_set()

    # 중앙 배치
    center_dialog(dialog, parent)

    # ESC로 닫기
    dialog.bind('<Escape>', lambda e: dialog.destroy())

    return dialog


# ═══════════════════════════════════════════════════════════════
# 8. 반응형 레이아웃
# ═══════════════════════════════════════════════════════════════


# ═══════════════════════════════════════════════════════════════
# 전역 인스턴스 (편의용)
# ═══════════════════════════════════════════════════════════════

_ui_calculator: Optional[UICalculator] = None
_font_scale: Optional[FontScale] = None


def init_ui_system(root):
    """UI 시스템 초기화"""
    global _ui_calculator, _font_scale

    _ui_calculator = UICalculator(root)
    _font_scale = FontScale(_ui_calculator.dpi)

    logger.info(f"UI 시스템 초기화: DPI={_ui_calculator.dpi:.0f}, "
                f"Scale={_ui_calculator.combined_scale:.2f}")


def get_ui_calculator() -> UICalculator:
    """UI 계산기 인스턴스"""
    return _ui_calculator or UICalculator()


def get_font_scale() -> FontScale:
    """폰트 스케일 인스턴스"""
    return _font_scale or FontScale()


# ═══════════════════════════════════════════════════════════════
# 8. 커스텀 메시지박스 (간격 조절 가능) — 하위 호환용 지연 로드
# ═══════════════════════════════════════════════════════════════
# v4.0.2: custom_messagebox.py에서 정의. 순환 import 방지를 위해 __getattr__ 로 지연 로드.


def __getattr__(name: str):
    if name == "CustomMessageBox":
        from .custom_messagebox import CustomMessageBox
        return CustomMessageBox
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


# ═══════════════════════════════════════════════════════════
# v7.6.0 — 공통 탭 헤더 헬퍼 (심플 레이아웃)
# ═══════════════════════════════════════════════════════════

def make_tab_header(parent, title: str, status_color: str = '#3b82f6',
                    count_var=None, is_dark: bool = False):
    """탭 상단 심플 헤더 바.

    Args:
        parent:       탭 프레임
        title:        탭 제목 (예: "📋 판매배정")
        status_color: 왼쪽 컬러 바 색상
        count_var:    tk.StringVar — 건수 실시간 표시 (옵션)
        is_dark:      다크 모드 여부

    Returns:
        header_frame (ttk.Frame)
    """
    import tkinter as tk

    bg = '#0B1220' if is_dark else '#F8FAFC'
    fg = '#E5E7EB' if is_dark else '#0F172A'
    border = '#1E293B' if is_dark else '#E2E8F0'

    outer = tk.Frame(parent, bg=border, height=38)
    outer.pack(fill='x', padx=0, pady=(0, 4))
    outer.pack_propagate(False)

    # 왼쪽 컬러 바
    tk.Frame(outer, bg=status_color, width=5).pack(side='left', fill='y')

    inner = tk.Frame(outer, bg=bg)
    inner.pack(side='left', fill='both', expand=True)

    tk.Label(inner, text=title, bg=bg, fg=fg,
             font=('맑은 고딕', 12, 'bold')).pack(side='left', padx=10)

    if count_var is not None:
        tk.Label(inner, textvariable=count_var, bg=bg, fg=status_color,
                 font=('맑은 고딕', 11, 'bold')).pack(side='right', padx=10)

    return outer
