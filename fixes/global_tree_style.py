import logging

logger = logging.getLogger(__name__)
"""
SQM v5.0.0 - 전역 Treeview 스타일
==================================

모든 표에 통일된 스타일 적용:
- 가는 실선 그리드
- 가운데 정렬
- 줄무늬 배경 (홀수/짝수)
- 헤더 진한 배경 + 흰색 글자
- 첫글자 대문자 통일

사용법:
import logging
    from fixes.global_tree_style import apply_global_tree_style
    
    # 앱 초기화 시 호출
    apply_global_tree_style()
"""

import tkinter as tk  # v6.1.1: tk.TclError 사용
from tkinter import ttk


def apply_global_tree_style():
    """
    v5.5.3: 전역 Treeview 스타일 적용 (다크/라이트 자동 대응)
    """

    style = ttk.Style()

    # ═══════════════════════════════════════════
    # 다크 테마 감지
    # ═══════════════════════════════════════════
    is_dark = False
    try:
        theme_name = style.theme_use() or ''
        dark_themes = ['darkly', 'cyborg', 'vapor', 'solar', 'superhero']
        is_dark = any(d in theme_name.lower() for d in dark_themes)
    except (ValueError, TypeError, AttributeError, tk.TclError) as _e:
        logger.debug(f"[global_tree_style] 무시: {_e}")

    if is_dark:
        bg_color = '#2b2b2b'
        fg_color = '#e0e0e0'
        field_bg = '#2b2b2b'
        odd_bg = '#333333'
        even_bg = '#2b2b2b'
        sel_bg = '#0078D7'
        sel_fg = 'white'
        head_bg = '#1a1a2e'
        head_fg = 'white'
        head_hover = '#16213e'
    else:
        bg_color = 'white'
        fg_color = 'black'
        field_bg = 'white'
        odd_bg = '#F8F9FA'
        even_bg = '#FFFFFF'
        sel_bg = '#0078D7'
        sel_fg = 'white'
        head_bg = '#34495E'
        head_fg = 'white'
        head_hover = '#2C3E50'

    # ═══════════════════════════════════════════
    # Treeview 기본 스타일
    # ═══════════════════════════════════════════
    style.configure(
        "Treeview",
        rowheight=30,
        borderwidth=1,
        relief='solid',
        font=('맑은 고딕', 9),
        fieldbackground=field_bg,
        background=bg_color,
        foreground=fg_color
    )

    # ═══════════════════════════════════════════
    # 헤더 스타일
    # ═══════════════════════════════════════════
    style.configure(
        "Treeview.Heading",
        font=('맑은 고딕', 10, 'bold'),
        borderwidth=1,
        relief='raised',
        background=head_bg,
        foreground=head_fg,
        padding=6
    )

    # ═══════════════════════════════════════════
    # 선택 및 포커스 색상
    # ═══════════════════════════════════════════
    style.map(
        "Treeview",
        background=[
            ('selected', sel_bg),
            ('focus', '#E3F2FD' if not is_dark else '#1a3a5c')
        ],
        foreground=[
            ('selected', sel_fg),
            ('focus', 'black' if not is_dark else 'white')
        ]
    )

    # ═══════════════════════════════════════════
    # 헤더 hover 효과
    # ═══════════════════════════════════════════
    style.map(
        "Treeview.Heading",
        background=[('active', head_hover)],
        foreground=[('active', 'white')]
    )

    # 전역 변수로 저장 (tag_configure에서 사용)
    apply_global_tree_style._is_dark = is_dark
    apply_global_tree_style._odd_bg = odd_bg
    apply_global_tree_style._even_bg = even_bg
    apply_global_tree_style._fg_color = fg_color

    logger.debug(f"✅ v5.5.3 Treeview style ({'dark' if is_dark else 'light'})")


def configure_tree_grid(tree, columns):
    """
    v5.5.3: 개별 Treeview에 그리드 + 정렬 + 줄무늬 (다크/라이트 자동)
    """
    # 전역 스타일에서 색상 가져오기
    odd_bg = getattr(apply_global_tree_style, '_odd_bg', '#F8F9FA')
    even_bg = getattr(apply_global_tree_style, '_even_bg', '#FFFFFF')
    fg_color = getattr(apply_global_tree_style, '_fg_color', 'black')

    tree.tag_configure('odd', background=odd_bg, foreground=fg_color)
    tree.tag_configure('even', background=even_bg, foreground=fg_color)

    # 모든 컬럼 가운데 정렬
    for col in columns:
        tree.column(col, anchor='center')
        tree.heading(col, anchor='center')


def capitalize_headers(headers):
    """
    v5.0.0: 헤더 첫글자 대문자 변환 (통일)
    
    Args:
        headers: 리스트 또는 튜플
    
    Returns:
        list: 변환된 헤더
    
    Examples:
        >>> capitalize_headers(['id', 'lot_no', 'sap_no'])
        ['ID', 'Lot_No', 'SAP_No']
        
        >>> capitalize_headers(['product', 'status', 'weight_kg'])
        ['Product', 'Status', 'Weight_Kg']
    """
    result = []
    for h in headers:
        h_lower = str(h).lower()

        # ═══════════════════════════════════════════
        # 특수 케이스 (고유 명사, 약어)
        # ═══════════════════════════════════════════
        if h_lower == 'id':
            result.append('ID')
        elif h_lower in ['sap_no', 'sap', 'sapno']:
            result.append('SAP_No')
        elif h_lower in ['bl_no', 'bl', 'blno']:
            result.append('BL_No')
        elif h_lower in ['uid', 'tonbag_uid']:
            result.append('UID')
        elif h_lower in ['lot_no', 'lotno']:
            result.append('Lot_No')
        elif h_lower in ['kg', 'mt', 'ton']:
            result.append(h_lower.upper())

        # ═══════════════════════════════════════════
        # 일반 케이스 (단어별 첫글자 대문자)
        # ═══════════════════════════════════════════
        else:
            words = h_lower.split('_')
            capitalized = [w.capitalize() for w in words]
            result.append('_'.join(capitalized))

    return result


def apply_to_tree_immediately(tree, columns=None):
    """
    v5.0.0: 기존 Treeview에 즉시 스타일 적용
    
    이미 생성된 Treeview 위젯에 스타일을 소급 적용
    
    Args:
        tree: ttk.Treeview 위젯
        columns: 컬럼 목록 (None이면 자동 감지)
    """
    if columns is None:
        columns = tree['columns']

    configure_tree_grid(tree, columns)

    # 기존 데이터에 줄무늬 적용
    for i, item in enumerate(tree.get_children()):
        tag = 'odd' if i % 2 else 'even'
        tree.item(item, tags=(tag,))


# ═══════════════════════════════════════════
# 전역 적용 예시
# ═══════════════════════════════════════════
if __name__ == '__main__':
    apply_global_tree_style()

    # 테스트
    headers = ['id', 'lot_no', 'sap_no', 'bl_no', 'product', 'status', 'uid', 'weight_kg']
    logger.debug("Before:", headers)
    logger.debug("After:", capitalize_headers(headers))
