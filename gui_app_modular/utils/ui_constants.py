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

# 화물(톤백) 상태 표시명 — 전체 / 판매가능 / 판매배정 / 판매화물 결정 / 출고 (v6.0.4 2단계 한글화)
STATUS_DISPLAY = {
    'AVAILABLE': '판매가능',
    'RESERVED': '판매배정',
    'PICKED': '판매화물 결정',
    'SOLD': '출고',
    'SHIPPED': '선적',
    'DEPLETED': '소진',
    'RETURNED': '반품',
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
        # 시맨틱 색상 (v3.6.2: 부드러운 톤)
        'success': '#2e7d4f',    # 깊은 녹색 (기존 #28a745)
        'warning': '#d4a017',    # 골드 (기존 #ffc107)
        'danger':  '#c0392b',    # 차분한 레드 (기존 #dc3545)
        'info':    '#2980b9',    # 딥 블루 (기존 #17a2b8)
        'primary': '#34495e',    # 네이비 그레이 (기존 #007bff)

        # 상태 색상 (Treeview 행 배경 - 부드러운 파스텔)
        'available': '#e8f5e9',   # 연한 민트 (기존 #C6EFCE)
        'picked':   '#fce4ec',   # 연한 핑크 (기존 #FFC7CE)
        'reserved': '#fff8e1',   # 연한 크림 (기존 #FFEB9C)
        'shipped':  '#e3f2fd',   # 연한 스카이 (기존 #DDEBF7)

        # 텍스트
        'text_primary':   '#2c3e50',   # 진한 네이비 (순수 검정 X)
        'text_secondary': '#7f8c8d',   # 부드러운 그레이
        'text_muted':     '#b0bec5',   # 비활성 텍스트

        # 배경 (v3.6.2: 순백색 대신 약간 따뜻한 톤)
        'bg_primary':   '#fafbfc',   # 살짝 따뜻한 화이트
        'bg_secondary': '#f0f3f5',   # 연한 그레이
        'bg_hover':     '#e8ecef',   # 호버 배경
        'bg_toolbar':   '#f0f3f5',   # 툴바 배경
        'bg_card':      '#ffffff',   # 카드/패널 배경

        # 테두리
        'border':       '#dce1e5',   # 연한 테두리
        'border_focus': '#5dade2',   # 포커스 테두리

        # 액션 버튼 (v3.6.2: 채도 낮춘 부드러운 팔레트)
        'btn_inbound':       '#2e7d4f',   # 입고: 딥 그린
        'btn_inbound_hover': '#3a9e64',
        'btn_outbound':       '#c77c2a',   # 출고: 앰버
        'btn_outbound_hover': '#d49545',
        'btn_report':         '#2c6fbb',   # 보고서: 스틸 블루
        'btn_report_hover':   '#4a8fd4',
        'btn_neutral':        '#6c7a89',   # 중립: 슬레이트
        'btn_neutral_hover':  '#8395a7',

        # Treeview
        'tree_select_bg':  '#d6eaf8',   # 선택 행 배경
        'tree_select_fg':  '#1a5276',   # 선택 행 텍스트
        'tree_stripe':     '#f7f9fa',   # 줄무늬 배경 (짝수행)

        # 차트
        'chart_bg':   '#ffffff',
        'chart_grid': '#ecf0f1',

        # v3.6.3: 검색바
        'search_bg':          '#fafbfc',
        'search_fg':          '#2c3e50',
        'search_border':      '#dce1e5',
        'search_placeholder': '#b0bec5',
        'search_cursor':      '#2c3e50',

        # v3.6.3: 상태바
        'statusbar_bg':       '#2c3e50',
        'statusbar_fg':       '#ffffff',
        'statusbar_icon_ok':  '#2ecc71',
        'statusbar_icon_warn':'#f39c12',
        'statusbar_icon_err': '#e74c3c',
        'statusbar_progress': '#3498db',
        'statusbar_progress_done': '#2ecc71',
        'statusbar_track':    '#34495e',

        # v3.6.3: 배지
        'badge_db':           '#27ae60',
        'badge_version':      '#3498db',
        'badge_text':         '#ffffff',

        # v3.6.3: 기타 UI
        'arrow_separator':    '#bdc3c7',
        'shortcut_text':      '#cccccc',
        'shortcut_text_dim':  '#dddddd',
        'canvas_highlight':   '#000000',
    }

    DARK = {
        'success': '#27ae60',
        'warning': '#f39c12',
        'danger':  '#e74c3c',
        'info':    '#3498db',
        'primary': '#5dade2',

        'available': '#1a3a2a',
        'picked':   '#3a1a1a',
        'reserved': '#3a3a1a',
        'shipped':  '#1a2a3a',

        'text_primary':   '#ecf0f1',
        'text_secondary': '#95a5a6',
        'text_muted':     '#7f8c8d',

        'bg_primary':   '#1e2a35',
        'bg_secondary': '#253545',
        'bg_hover':     '#34495e',
        'bg_toolbar':   '#1e2a35',
        'bg_card':      '#2c3e50',

        'border':       '#34495e',
        'border_focus': '#3498db',

        'btn_inbound':       '#27ae60',
        'btn_inbound_hover': '#2ecc71',
        'btn_outbound':       '#d68910',
        'btn_outbound_hover': '#f39c12',
        'btn_report':         '#2980b9',
        'btn_report_hover':   '#3498db',
        'btn_neutral':        '#5d6d7e',
        'btn_neutral_hover':  '#7f8c8d',

        'tree_select_bg':  '#2471a3',
        'tree_select_fg':  '#ffffff',
        'tree_stripe':     '#253545',

        'chart_bg':   '#2c3e50',
        'chart_grid': '#34495e',

        # v3.6.3: 검색바
        'search_bg':          '#253545',
        'search_fg':          '#ecf0f1',
        'search_border':      '#34495e',
        'search_placeholder': '#7f8c8d',
        'search_cursor':      '#ecf0f1',

        # v3.6.3: 상태바
        'statusbar_bg':       '#1a2530',
        'statusbar_fg':       '#ecf0f1',
        'statusbar_icon_ok':  '#2ecc71',
        'statusbar_icon_warn':'#f39c12',
        'statusbar_icon_err': '#e74c3c',
        'statusbar_progress': '#3498db',
        'statusbar_progress_done': '#2ecc71',
        'statusbar_track':    '#253545',

        # v3.6.3: 배지
        'badge_db':           '#1e8449',
        'badge_version':      '#2471a3',
        'badge_text':         '#ffffff',

        # v3.6.3: 기타 UI
        'arrow_separator':    '#5d6d7e',
        'shortcut_text':      '#95a5a6',
        'shortcut_text_dim':  '#7f8c8d',
        'canvas_highlight':   '#ecf0f1',
    }

    DARK_THEMES = ['darkly', 'cyborg', 'superhero', 'solar', 'vapor']

    @classmethod
    def is_dark_theme(cls, theme_name: str) -> bool:
        """다크 테마 여부 확인"""
        return theme_name.lower() in cls.DARK_THEMES

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
        """트리뷰 상태 태그 설정 (v3.8.4: 상태별 색상 + v5.6.9: 다크 테마 행 텍스트 밝은색)"""
        p = cls.DARK if is_dark else cls.LIGHT
        fg = '#f0f0f0' if is_dark else '#1a1a1a'
        for status in ['available', 'picked', 'reserved', 'shipped']:
            tree.tag_configure(status, background=p[status], foreground=fg)
        # U9: depleted 태그 (연한 회색 + 취소선 효과)
        tree.tag_configure('depleted', background='#f0f0f0' if not is_dark else '#2a2a2a',
                          foreground='#aaaaaa' if not is_dark else '#888888')
        # v3.6.2: 줄무늬 태그
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

            # ─── Notebook 탭 ───
            style.configure(
                'TNotebook.Tab',
                padding=(16, 8),
                font=(cls.FONT_FAMILY, cls.FONT_SIZE),
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
            'statusbar_bg': p.get('bg_primary', '#2c3e50') if is_dark else '#2c3e50',
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


def apply_tooltip(widget, text: str, delay: int = 500):
    """
    위젯에 ttkbootstrap ToolTip 적용 (v3.6.5)
    
    ttkbootstrap 미설치 시 자동 무시 (안전 fallback).
    
    사용법:
        apply_tooltip(my_button, '이 버튼은 데이터를 저장합니다')
    """
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
    return Path(__file__).resolve().parent.parent.parent / "window_config.json"


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
        except (RuntimeError, Exception) as e:
            logger.debug(f"[_on_save_geometry] Suppressed: {e}")

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
