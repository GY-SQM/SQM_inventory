import logging

logger = logging.getLogger(__name__)
"""
SQM v6.3.2-colorful — 전역 Treeview 스타일
=============================================

v6.3.2 변경사항:
  - 다크 배경: 보라 기조 (#1e1e2e / #282840)
  - 헤더: ttkbootstrap 강제 오버라이드 (style.map + !disabled)
  - apply_to_tree_safely(): status 태그 보존하면서 odd/even 병합
  - configure_tree_grid(): 보라 기조 색상 동기화
"""

from tkinter import ttk


# ═══════════════════════════════════════════
# 색상 상수
# ═══════════════════════════════════════════
DARK_COLORS = {
    'bg':        '#0B1220',
    'fg':        '#E5E7EB',
    'odd_bg':    '#111B2E',
    'even_bg':   '#0B1220',
    'sel_bg':    '#2563EB',
    'sel_fg':    '#FFD700',  # Gold — 파란 배경 대비 가독성
    'head_bg':   '#162033',
    'head_fg':   '#E5E7EB',
    'head_hover': '#1E293B',
}

LIGHT_COLORS = {
    'bg':        '#FFFFFF',
    'fg':        '#0F172A',
    'odd_bg':    '#F8FAFC',
    'even_bg':   '#FFFFFF',
    'sel_bg':    '#DBEAFE',
    'sel_fg':    '#1E3A5F',
    'head_bg':   '#F1F5F9',
    'head_fg':   '#0F172A',
    'head_hover': '#E2E8F0',
}

STATUS_TAGS = frozenset({'available', 'picked', 'reserved', 'shipped', 'depleted'})


def _is_dark_theme():
    """현재 다크 테마 여부"""
    try:
        style = ttk.Style()
        theme = (style.theme_use() or '').lower()
        return theme == 'darkly'
    except Exception:
        return False


def apply_global_tree_style():
    """
    v6.3.2-colorful: 전역 Treeview 스타일 적용
    ★ ttkbootstrap Heading 강제 오버라이드 포함
    """
    style = ttk.Style()
    is_dark = _is_dark_theme()
    c = DARK_COLORS if is_dark else LIGHT_COLORS

    # ═══ Treeview 기본 스타일 ═══
    style.configure(
        "Treeview",
        rowheight=30,
        borderwidth=1,
        relief='solid',
        font=('맑은 고딕', 9),
        fieldbackground=c['bg'],
        background=c['bg'],
        foreground=c['fg']
    )

    # ═══ Heading 스타일 (configure) ═══
    style.configure(
        "Treeview.Heading",
        font=('맑은 고딕', 10, 'bold'),
        borderwidth=1,
        relief='raised',
        background=c['head_bg'],
        foreground=c['head_fg'],
        padding=6
    )

    # ═══ ★★★ ttkbootstrap 강제 오버라이드 ★★★ ═══
    # ttkbootstrap darkly 테마는 Tcl element_create로 헤더를 파랑(#375a7f)으로 고정.
    # style.configure만으로는 무시됨.
    # → style.map의 '!disabled' 상태로 강제 적용
    style.map(
        "Treeview.Heading",
        background=[
            ('active', c['head_hover']),
            ('!disabled', c['head_bg']),      # ★ 핵심: 비활성 상태에서 강제
        ],
        foreground=[
            ('active', 'white'),
            ('!disabled', c['head_fg']),       # ★ 핵심
        ]
    )

    # ═══ 행 선택·포커스 색상 ═══
    style.map(
        "Treeview",
        background=[
            ('selected', c['sel_bg']),
            ('focus', '#E3F2FD' if not is_dark else '#1a3a5c')
        ],
        foreground=[
            ('selected', c['sel_fg']),
            ('!selected', c['fg']),
            ('focus', 'black' if not is_dark else 'white')
        ]
    )

    # 전역 변수 저장
    apply_global_tree_style._is_dark = is_dark
    apply_global_tree_style._colors = c

    logger.debug(f"✅ v6.3.2 Treeview style ({'dark' if is_dark else 'light'})")


def configure_tree_grid(tree, columns):
    """
    v6.3.2-colorful: 개별 Treeview 그리드 + 정렬 + 줄무늬
    ★ DARK_COLORS/LIGHT_COLORS와 동기화 (하드코딩 제거)
    """
    is_dark = _is_dark_theme()
    c = DARK_COLORS if is_dark else LIGHT_COLORS

    tree.tag_configure('odd', background=c['odd_bg'], foreground=c['fg'])
    tree.tag_configure('even', background=c['even_bg'], foreground=c['fg'])

    for col in columns:
        tree.column(col, anchor='center')
        tree.heading(col, anchor='center')


def capitalize_headers(headers):
    """v5.0.0: 헤더 첫글자 대문자"""
    result = []
    for h in headers:
        h_lower = str(h).lower()
        if h_lower == 'id':
            result.append('ID')
        elif h_lower in ('sap_no', 'sap', 'sapno'):
            result.append('SAP_No')
        elif h_lower in ('bl_no', 'bl', 'blno'):
            result.append('BL_No')
        elif h_lower in ('uid', 'tonbag_uid'):
            result.append('UID')
        elif h_lower in ('lot_no', 'lotno'):
            result.append('Lot_No')
        elif h_lower in ('kg', 'mt', 'ton'):
            result.append(h_lower.upper())
        else:
            words = h_lower.split('_')
            result.append('_'.join(w.capitalize() for w in words))
    return result


def apply_to_tree_safely(tree, columns=None):
    """
    v6.3.2-colorful: 기존 Treeview에 즉시 스타일 적용
    ★★★ 핵심: status 태그를 보존하면서 odd/even 병합
    
    기존 apply_to_tree_immediately()는 tags=(tag,)로 교체하여
    status 태그를 삭제했음. 이 함수는 status 태그를 보존.
    """
    if columns is None:
        columns = tree['columns']

    configure_tree_grid(tree, columns)

    # ★ status 태그 보존하면서 odd/even 추가
    for i, item in enumerate(tree.get_children()):
        existing_tags = set(tree.item(item, 'tags') or ())
        # status 태그 보존
        preserved = existing_tags & STATUS_TAGS
        stripe_tag = 'odd' if i % 2 else 'even'
        # status 태그 없는 경우에만 odd/even 색상 적용
        if preserved:
            # status 태그가 있으면 status 태그만 유지 (odd/even 색상은 불필요)
            new_tags = tuple(preserved)
        else:
            new_tags = (stripe_tag,)
        tree.item(item, tags=new_tags)


# 하위 호환성: 구 함수명 유지
def apply_to_tree_immediately(tree, columns=None):
    """하위 호환성 래퍼 → apply_to_tree_safely 호출"""
    return apply_to_tree_safely(tree, columns)


if __name__ == '__main__':
    apply_global_tree_style()
    headers = ['id', 'lot_no', 'sap_no', 'bl_no', 'product', 'status', 'uid', 'weight_kg']
    logger.debug("Before:", headers)
    logger.debug("After:", capitalize_headers(headers))
