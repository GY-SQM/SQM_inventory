# -*- coding: utf-8 -*-
"""
★★★ SQM v6.3.2 — Colorful UI Fix v4 (진짜 근본 원인 수정) ★★★
================================================================
날짜: 2026-03-04
작성: Ruby

★ v4 — 진짜 근본 원인 ★

  theme_preference.json = "cyborg" (다크 테마)
  self.current_theme = "flatly" (라이트 하드코딩)

  → 모든 is_dark_theme() 체크가 FALSE
  → 라이트 팔레트 색상이 다크 배경에 적용
  → 글씨/상태색/툴바 모두 안 보임

  v1~v3는 이 버그 때문에 아무리 색상을 바꿔도
  라이트 모드 색상이 적용되어 차이가 안 보였음

★ 수정 전략:
  1. self.current_theme 동기화 (THE FIX)
  2. 최종 오버라이드 모듈 생성 (ttkbootstrap 강제)
  3. 데이터 로드 후 상태색 자동 재적용 (monkey-patch)
  4. 이전 v3 수정 포함

적용법: SQM 폴더에 넣고 더블클릭
"""
import os
import re
import shutil
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def find_sqm_root():
    check = SCRIPT_DIR
    for _ in range(4):
        if os.path.isdir(os.path.join(check, 'gui_app_modular')):
            return check
        check = os.path.dirname(check)
    return None


def backup(filepath):
    if os.path.isfile(filepath):
        bak = filepath + f'.bak_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        shutil.copy2(filepath, bak)
        return os.path.basename(bak)
    return None


def safe_replace(content, old, new, label):
    if old in content:
        content = content.replace(old, new)
        print(f"  ✅ {label}")
        return content, True
    else:
        print(f"  ⚠️ {label} — 패턴 미발견")
        return content, False


# ═══════════════════════════════════════════
# FIX #1: ★★★★★ main_app.py — current_theme 동기화
#   THE ROOT CAUSE: self.current_theme = 'flatly' 하드코딩
# ═══════════════════════════════════════════
def fix1_current_theme(sqm_root):
    target = os.path.join(sqm_root, 'gui_app_modular', 'main_app.py')
    if not os.path.isfile(target):
        print("  ❌ main_app.py 없음")
        return False

    with open(target, 'r', encoding='utf-8') as f:
        content = f.read()
    bak = backup(target)
    if bak:
        print(f"  📋 백업: {bak}")

    changed = False

    # (A) ★★★ self.current_theme = 'flatly' → 실제 테마 감지
    OLD_THEME = "self.current_theme = 'flatly'  # v3.0: 고급스러운 기본 테마"
    NEW_THEME = """# ★ v6.3.2-fix: 실제 사용 중인 테마로 동기화 (flatly 하드코딩 제거)
        try:
            from tkinter import ttk as _ttk_detect
            self.current_theme = _ttk_detect.Style().theme_use() or 'darkly'
        except Exception:
            self.current_theme = 'darkly'"""

    if OLD_THEME in content:
        content = content.replace(OLD_THEME, NEW_THEME)
        print("  ✅ [★ROOT CAUSE] self.current_theme 실제 테마 동기화")
        changed = True
    elif "_ttk_detect" in content:
        print("  ℹ️ current_theme 이미 수정됨")
    else:
        # Fallback: 좀 더 넓은 패턴
        pat = re.compile(r"self\.current_theme\s*=\s*'flatly'")
        if pat.search(content):
            content = pat.sub(
                "# v6.3.2-fix: 실제 테마 동기화\n"
                "        try:\n"
                "            from tkinter import ttk as _ttk_detect\n"
                "            self.current_theme = _ttk_detect.Style().theme_use() or 'darkly'\n"
                "        except Exception:\n"
                "            self.current_theme = 'darkly'",
                content, count=1)
            print("  ✅ [★ROOT CAUSE] current_theme 동기화 (regex)")
            changed = True
        else:
            print("  ⚠️ current_theme 패턴 미발견")

    # (B) 최종 오버라이드 훅 추가 (after 1500ms)
    HOOK_MARKER = "theme_colorful_override"
    if HOOK_MARKER not in content:
        # after(1000, apply_styles_to_all_trees) 뒤에 추가
        HOOK_ANCHOR = "self.root.after(1000, lambda: apply_styles_to_all_trees(self.root))"
        HOOK_CODE = """self.root.after(1000, lambda: apply_styles_to_all_trees(self.root))
            # ★ v6.3.2-colorful: 최종 오버라이드 (ttkbootstrap 강제 + 상태색)
            try:
                from fixes.theme_colorful_override import apply_colorful_overrides
                self.root.after(1500, lambda: apply_colorful_overrides(self))
            except ImportError:
                pass"""

        if HOOK_ANCHOR in content:
            content = content.replace(HOOK_ANCHOR, HOOK_CODE)
            print("  ✅ 최종 오버라이드 훅 추가 (after 1500ms)")
            changed = True
        else:
            print("  ⚠️ 오버라이드 훅 앵커 미발견 (수동 추가 필요)")
    else:
        print("  ℹ️ 오버라이드 훅 이미 존재")

    if changed:
        with open(target, 'w', encoding='utf-8') as f:
            f.write(content)
    return changed


# ═══════════════════════════════════════════
# FIX #2: 최종 오버라이드 모듈 생성 (새 파일)
#   ttkbootstrap Heading/Notebook/Tab 강제 오버라이드
#   + 상태 태그 최종 적용
# ═══════════════════════════════════════════
def fix2_create_override_module(sqm_root):
    target = os.path.join(sqm_root, 'fixes', 'theme_colorful_override.py')
    os.makedirs(os.path.join(sqm_root, 'fixes'), exist_ok=True)

    MODULE_CODE = r'''# -*- coding: utf-8 -*-
"""
SQM v6.3.2-colorful — 최종 테마 오버라이드 모듈
=================================================
모든 초기화가 끝난 후 마지막으로 실행되어
ttkbootstrap의 하드코딩 색상을 강제 오버라이드.

main_app.py에서 root.after(1500)으로 호출됨.
"""
import logging
from tkinter import ttk

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════
# 색상 정의
# ═══════════════════════════════════════════
DARK_HEADING = {
    'bg':    '#2d2b55',    # 다크 퍼플 (파랑 탈피)
    'fg':    '#ffffff',
    'hover': '#3d3a6e',
}
DARK_NOTEBOOK = {
    'selected':   '#2d2b55',
    'unselected': '#1a1a2e',
    'fg':         '#ffffff',
    'fg_inactive': '#a0a0b8',
}
STATUS_FG_DARK = {
    'available': '#6ee7b7',
    'reserved':  '#fcd34d',
    'picked':    '#c4b5fd',
    'shipped':   '#93c5fd',
}
STATUS_BG_DARK = {
    'available': '#065f46',
    'reserved':  '#92400e',
    'picked':    '#5b21b6',
    'shipped':   '#1e3a5f',
}
STATUS_FG_LIGHT = {
    'available': '#064e3b',
    'reserved':  '#78350f',
    'picked':    '#4c1d95',
    'shipped':   '#1e3a5f',
}
STATUS_BG_LIGHT = {
    'available': '#d1fae5',
    'reserved':  '#fef3c7',
    'picked':    '#ede9fe',
    'shipped':   '#dbeafe',
}
STATUS_TAGS = frozenset({'available', 'picked', 'reserved', 'shipped', 'depleted'})


def _is_dark(theme_name=None):
    """다크 테마 여부"""
    if theme_name is None:
        try:
            theme_name = ttk.Style().theme_use() or ''
        except Exception:
            theme_name = ''
    return theme_name.lower() in ('darkly', 'cyborg', 'superhero', 'solar', 'vapor')


def apply_colorful_overrides(app):
    """
    ★ 최종 오버라이드 — main_app.py의 after(1500)에서 호출
    
    1. current_theme 재동기화
    2. Treeview Heading 강제 오버라이드 (ttkbootstrap 무력화)
    3. Notebook Tab 색상 오버라이드
    4. 모든 Treeview에 상태 태그 색상 재적용
    5. monkey-patch _refresh_inventory로 지속적 상태색 보장
    """
    try:
        style = ttk.Style()
        actual_theme = style.theme_use() or 'darkly'
        is_dark = _is_dark(actual_theme)

        # 1. current_theme 재동기화
        if hasattr(app, 'current_theme'):
            app.current_theme = actual_theme
            logger.info(f"✅ current_theme 동기화: {actual_theme} (dark={is_dark})")

        # 2. ★ Treeview Heading — ttkbootstrap 강제 오버라이드
        if is_dark:
            h = DARK_HEADING
            style.configure('Treeview.Heading',
                background=h['bg'], foreground=h['fg'],
                font=('맑은 고딕', 10, 'bold'))
            # ★ style.map의 !disabled로 ttkbootstrap element 덮어쓰기
            style.map('Treeview.Heading',
                background=[('active', h['hover']), ('!disabled', h['bg'])],
                foreground=[('active', h['fg']), ('!disabled', h['fg'])])
            logger.info(f"✅ Heading 색상: {h['bg']} (ttkbootstrap 강제)")

        # 3. Notebook Tab 색상
        if is_dark:
            n = DARK_NOTEBOOK
            style.map('TNotebook.Tab',
                background=[('selected', n['selected']), ('!selected', n['unselected'])],
                foreground=[('selected', n['fg']), ('!selected', n['fg_inactive'])])
            logger.info(f"✅ Notebook Tab: selected={n['selected']}")

        # 4. 모든 Treeview에 상태 태그 재적용
        _apply_status_to_all_trees(app, is_dark)

        # 5. monkey-patch _refresh_inventory
        _install_refresh_hook(app, is_dark)

        logger.info("✅ v6.3.2-colorful: 최종 오버라이드 완료")

    except Exception as e:
        logger.error(f"Theme override error: {e}")
        import traceback
        traceback.print_exc()


def _apply_status_tags(tree, is_dark):
    """개별 Treeview에 상태 태그 색상 적용"""
    sfg = STATUS_FG_DARK if is_dark else STATUS_FG_LIGHT
    sbg = STATUS_BG_DARK if is_dark else STATUS_BG_LIGHT
    fg = '#f0f0f0' if is_dark else '#1a1a1a'

    for status in ['available', 'picked', 'reserved', 'shipped']:
        tree.tag_configure(status,
            background=sbg.get(status, ''),
            foreground=sfg.get(status, fg))

    tree.tag_configure('depleted',
        background='#2a2a2a' if is_dark else '#f0f0f0',
        foreground='#888888' if is_dark else '#aaaaaa')

    tree.tag_configure('stripe',
        background='#282840' if is_dark else '#F8F9FA',
        foreground=fg)

    tree.tag_configure('odd',
        background='#282840' if is_dark else '#F8F9FA',
        foreground=fg)

    tree.tag_configure('even',
        background='#1e1e2e' if is_dark else '#FFFFFF',
        foreground=fg)


def _apply_status_to_all_trees(app, is_dark):
    """앱의 모든 주요 Treeview에 상태색 적용"""
    count = 0
    for attr in ['tree_inventory', 'tree_sublot', 'tree_allocation',
                 'tree_picked', 'tree_sold', 'tree_overview']:
        tree = getattr(app, attr, None)
        if tree is not None:
            try:
                _apply_status_tags(tree, is_dark)
                count += 1
            except Exception as e:
                logger.debug(f"Status tag apply failed for {attr}: {e}")
    logger.info(f"✅ 상태 태그 적용: {count}개 Treeview")


def _install_refresh_hook(app, is_dark):
    """
    ★ monkey-patch: _refresh_inventory 래핑
    데이터 로드 후 상태색이 _text_color(단일색)로 덮어써지는 문제 해결.
    원본 함수 실행 후 상태색을 다시 적용.
    """
    hooked_attr = '_colorful_refresh_hooked'
    if getattr(app, hooked_attr, False):
        return  # 이미 훅 설치됨

    for method_name, tree_attr in [
        ('_refresh_inventory', 'tree_inventory'),
        ('_refresh_sublot_list', 'tree_sublot'),
    ]:
        original = getattr(app, method_name, None)
        if original is None:
            continue

        tree = getattr(app, tree_attr, None)
        if tree is None:
            continue

        def make_wrapper(orig_fn, tree_widget, dark):
            def wrapper(*args, **kwargs):
                result = orig_fn(*args, **kwargs)
                try:
                    _apply_status_tags(tree_widget, dark)
                except Exception:
                    pass
                return result
            return wrapper

        setattr(app, method_name, make_wrapper(original, tree, is_dark))
        logger.info(f"✅ {method_name} monkey-patch 설치")

    setattr(app, hooked_attr, True)
'''

    with open(target, 'w', encoding='utf-8') as f:
        f.write(MODULE_CODE)
    print("  ✅ fixes/theme_colorful_override.py 생성")
    print("     ★ Heading style.map(!disabled) 강제 오버라이드")
    print("     ★ Notebook Tab 색상")
    print("     ★ _refresh_inventory monkey-patch (상태색 지속)")
    return True


# ═══════════════════════════════════════════
# FIX #3: global_tree_style.py — status 태그 보존 + 헤더
# ═══════════════════════════════════════════
def fix3_global_tree_style(sqm_root):
    target = os.path.join(sqm_root, 'fixes', 'global_tree_style.py')
    if not os.path.isfile(target):
        print("  ⚠️ global_tree_style.py 없음")
        return True

    bak = backup(target)
    if bak:
        print(f"  📋 백업: {bak}")

    with open(target, 'r', encoding='utf-8') as f:
        content = f.read()

    # apply_to_tree_immediately가 status 태그를 보존하는지 확인
    if 'STATUS_TAGS' in content and 'preserved' in content:
        print("  ℹ️ v3 패치 이미 적용됨 (status 보존)")
        return True

    # apply_to_tree_immediately를 status-safe로 교체
    OLD_APPLY = """def apply_to_tree_immediately(tree, columns=None):
    \"\"\"
    v5.0.0: 기존 Treeview에 즉시 스타일 적용
    
    이미 생성된 Treeview 위젯에 스타일을 소급 적용
    
    Args:
        tree: ttk.Treeview 위젯
        columns: 컬럼 목록 (None이면 자동 감지)
    \"\"\"
    if columns is None:
        columns = tree['columns']

    configure_tree_grid(tree, columns)

    # 기존 데이터에 줄무늬 적용
    for i, item in enumerate(tree.get_children()):
        tag = 'odd' if i % 2 else 'even'
        tree.item(item, tags=(tag,))"""

    NEW_APPLY = """STATUS_TAGS = frozenset({'available', 'picked', 'reserved', 'shipped', 'depleted'})

def apply_to_tree_immediately(tree, columns=None):
    \"\"\"v6.3.2: 기존 Treeview에 스타일 적용 (★ status 태그 보존)\"\"\"
    if columns is None:
        columns = tree['columns']
    configure_tree_grid(tree, columns)
    for i, item in enumerate(tree.get_children()):
        existing = set(tree.item(item, 'tags') or ())
        preserved = existing & STATUS_TAGS
        if preserved:
            new_tags = tuple(preserved)
        else:
            new_tags = ('odd' if i % 2 else 'even',)
        tree.item(item, tags=new_tags)

# 하위 호환성
apply_to_tree_safely = apply_to_tree_immediately"""

    content, ok = safe_replace(content, OLD_APPLY, NEW_APPLY,
        "apply_to_tree_immediately → status 보존")

    # configure_tree_grid 하드코딩 수정
    OLD_GRID = """    if is_dark:
        odd_bg = '#333333'
        even_bg = '#2b2b2b'
        fg_color = '#e0e0e0'"""
    NEW_GRID = """    if is_dark:
        odd_bg = '#282840'         # v6.3.2: 보라 기조
        even_bg = '#1e1e2e'
        fg_color = '#e0e0e0'"""
    content, _ = safe_replace(content, OLD_GRID, NEW_GRID,
        "configure_tree_grid 색상 동기화")

    with open(target, 'w', encoding='utf-8') as f:
        f.write(content)
    return True


# ═══════════════════════════════════════════
# FIX #4: ui_constants.py (v3 수정 + is_dark_theme)
# ═══════════════════════════════════════════
def fix4_ui_constants(sqm_root):
    target = os.path.join(sqm_root, 'gui_app_modular', 'utils', 'ui_constants.py')
    if not os.path.isfile(target):
        print("  ❌ ui_constants.py 없음")
        return False

    with open(target, 'r', encoding='utf-8') as f:
        content = f.read()
    bak = backup(target)
    if bak:
        print(f"  📋 백업: {bak}")

    changed = 0

    # DARK 상태색
    for old, new in [
        ("'available': '#0f766e'", "'available': '#065f46'"),
        ("'reserved':  '#b45309'", "'reserved':  '#92400e'"),
        ("'picked':    '#7c3aed'", "'picked':    '#5b21b6'"),
        ("'shipped':   '#1d4ed8'", "'shipped':   '#1e3a5f'"),
    ]:
        if old in content:
            content = content.replace(old, new)
            changed += 1

    # is_dark_theme
    old_dt = "return theme_name.lower() in cls.DARK_THEMES"
    new_dt = "return theme_name.lower() in ('darkly', 'cyborg', 'superhero', 'solar', 'vapor')"
    if old_dt in content:
        content = content.replace(old_dt, new_dt)
        changed += 1
        print("  ✅ is_dark_theme() cls.DARK_THEMES → 인라인 튜플")
    elif "('darkly', 'cyborg'" in content:
        print("  ℹ️ is_dark_theme() 이미 수정됨")

    # configure_tags fg 변수 확인/추가
    if "def configure_tags" in content:
        # fg 변수가 있는지 확인
        ct_match = re.search(
            r'def configure_tags.*?(?=\n    @|\n    def |\nclass |\Z)',
            content, re.DOTALL)
        if ct_match:
            ct_body = ct_match.group()
            if "fg = " not in ct_body and "status_fg" not in ct_body:
                # 원본 configure_tags — 전체 교체
                NEW_CT = '''    @classmethod
    def configure_tags(cls, tree, is_dark: bool = False):
        """v6.3.2-colorful: 상태별 고유 전경색"""
        p = cls.DARK if is_dark else cls.LIGHT
        fg = '#f0f0f0' if is_dark else '#1a1a1a'
        sfg = {
            'available': '#6ee7b7' if is_dark else '#064e3b',
            'reserved':  '#fcd34d' if is_dark else '#78350f',
            'picked':    '#c4b5fd' if is_dark else '#4c1d95',
            'shipped':   '#93c5fd' if is_dark else '#1e3a5f',
        }
        for status in ['available', 'picked', 'reserved', 'shipped']:
            tree.tag_configure(status, background=p.get(status, ''),
                               foreground=sfg.get(status, fg))
        tree.tag_configure('depleted', background='#2a2a2a' if is_dark else '#f0f0f0',
                          foreground='#888888' if is_dark else '#aaaaaa')
        tree.tag_configure('stripe', background=p.get('tree_stripe', ''), foreground=fg)\n'''
                content = content[:ct_match.start()] + NEW_CT + content[ct_match.end():]
                changed += 1
                print("  ✅ configure_tags() 전체 교체")
            elif "fg = " in ct_body:
                print("  ℹ️ configure_tags() 이미 fg 변수 있음")
            else:
                print("  ℹ️ configure_tags() 이미 status_fg 있음")

    # 스크롤바 반전
    for old, new in [
        ("trough = '#f2f2f2' if is_dark else '#111111'",
         "trough = '#111111' if is_dark else '#f2f2f2'  # v6.3.2-fix"),
        ("thumb = '#111111' if is_dark else '#f2f2f2'",
         "thumb = '#f2f2f2' if is_dark else '#111111'  # v6.3.2-fix"),
        ("active = '#000000' if is_dark else '#ffffff'",
         "active = '#ffffff' if is_dark else '#000000'  # v6.3.2-fix"),
    ]:
        if old in content:
            content = content.replace(old, new)
            changed += 1

    if changed > 0:
        with open(target, 'w', encoding='utf-8') as f:
            f.write(content)
    print(f"  ✅ ui_constants.py — {changed}건 수정")
    return True


# ═══════════════════════════════════════════
# FIX #5: toolbar_mixin.py (v3)
# ═══════════════════════════════════════════
def fix5_toolbar(sqm_root):
    target = os.path.join(sqm_root, 'gui_app_modular', 'mixins', 'toolbar_mixin.py')
    if not os.path.isfile(target):
        print("  ❌ toolbar_mixin.py 없음")
        return False

    with open(target, 'r', encoding='utf-8') as f:
        content = f.read()
    bak = backup(target)
    if bak:
        print(f"  📋 백업: {bak}")

    changed = 0

    OLD_LOAD = """    def _load_toolbar_colors(self) -> None:
        \"\"\"컬러풀 고정 팔레트 (테마와 무관하게 유지).\"\"\"
        self._tb_bg = '#0f172a'          # 진한 네이비
        self._tb_sep = '#334155'         # 구분선
        self._tb_fg_normal = '#cbd5e1'   # 비활성 텍스트
        self._tb_fg_active = '#ffffff'   # 활성 텍스트
        self._tb_fg_hover = '#93c5fd'    # 호버 텍스트
        self._tb_hover_bg = '#1e293b'    # 호버 배경
        self._tb_underline_color = '#3b82f6'  # 강조 파랑"""

    NEW_LOAD = """    def _load_toolbar_colors(self) -> None:
        \"\"\"v6.3.2-colorful: 다크/라이트 반응형 팔레트.\"\"\"
        is_dark = ThemeColors.is_dark_theme(getattr(self, 'current_theme', 'darkly'))
        if is_dark:
            self._tb_bg = '#1a1a2e'
            self._tb_sep = '#3d3d5c'
            self._tb_fg_normal = '#c0c0d0'
            self._tb_fg_active = '#ffffff'
            self._tb_fg_hover = '#e0b0ff'
            self._tb_hover_bg = '#2a2a4a'
            self._tb_underline_color = '#a78bfa'
        else:
            self._tb_bg = '#1f2937'
            self._tb_sep = '#4b5563'
            self._tb_fg_normal = '#d1d5db'
            self._tb_fg_active = '#ffffff'
            self._tb_fg_hover = '#fbbf24'
            self._tb_hover_bg = '#374151'
            self._tb_underline_color = '#f59e0b'"""

    if OLD_LOAD in content:
        content = content.replace(OLD_LOAD, NEW_LOAD)
        changed += 1
        print("  ✅ _load_toolbar_colors → 테마 반응형")
    elif 'v6.3.2-colorful' in content:
        print("  ℹ️ _load_toolbar_colors 이미 패치됨")

    OLD_MENU = """        menu_bg = '#0b1220'
        menu_fg = '#e2e8f0'
        menu_abg = '#1d4ed8'
        menu_afg = '#ffffff'
        menu_dis = '#64748b'"""

    NEW_MENU = """        is_dark = ThemeColors.is_dark_theme(getattr(self, 'current_theme', 'darkly'))
        if is_dark:
            menu_bg = '#1a1a2e'
            menu_fg = '#e2e8f0'
            menu_abg = '#7c3aed'
            menu_afg = '#ffffff'
            menu_dis = '#64748b'
        else:
            menu_bg = '#1f2937'
            menu_fg = '#f3f4f6'
            menu_abg = '#d97706'
            menu_afg = '#ffffff'
            menu_dis = '#9ca3af'"""

    if OLD_MENU in content:
        content = content.replace(OLD_MENU, NEW_MENU)
        changed += 1
        print("  ✅ _create_menu → 테마 반응형")
    elif 'is_dark:' in content and 'menu_abg' in content:
        print("  ℹ️ _create_menu 이미 패치됨")

    if changed > 0:
        with open(target, 'w', encoding='utf-8') as f:
            f.write(content)
    print(f"  ✅ toolbar_mixin.py — {changed}건 수정")
    return True


# ═══════════════════════════════════════════
# FIX #6: table_styler.py
# ═══════════════════════════════════════════
def fix6_table_styler(sqm_root):
    target = os.path.join(sqm_root, 'gui_app_modular', 'utils', 'table_styler.py')
    if not os.path.isfile(target):
        print("  ⚠️ table_styler.py 없음")
        return True

    with open(target, 'r', encoding='utf-8') as f:
        content = f.read()

    old = "'header_bg': '#333333',"
    new = "'header_bg': '#2d2b55',  # v6.3.2: 다크 퍼플"
    if old in content:
        bak = backup(target)
        if bak:
            print(f"  📋 백업: {bak}")
        content = content.replace(old, new)
        with open(target, 'w', encoding='utf-8') as f:
            f.write(content)
        print("  ✅ DARK 헤더 → #2d2b55")
    elif '#2d2b55' in content:
        print("  ℹ️ 이미 패치됨")
    return True


def main():
    print()
    print("=" * 64)
    print("  🎨 SQM v6.3.2 — Colorful UI Fix v4")
    print(f"  실행: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("  ★★★ 진짜 근본 원인 수정 ★★★")
    print("  theme_preference.json = cyborg (다크)")
    print("  self.current_theme = flatly (라이트 하드코딩)")
    print("  → 모든 is_dark 판정이 FALSE → 라이트 색상 적용")
    print("=" * 64)
    print()

    sqm_root = find_sqm_root()
    if not sqm_root:
        print("  ❌ SQM 폴더 미발견")
        input("\n  Enter...")
        return

    print(f"  📂 SQM 루트: {sqm_root}")
    print()

    print("── [1/6] ★ main_app.py (current_theme 동기화 + 오버라이드 훅) ──")
    fix1_current_theme(sqm_root)
    print()

    print("── [2/6] ★ theme_colorful_override.py (새 파일 생성) ──")
    fix2_create_override_module(sqm_root)
    print()

    print("── [3/6] global_tree_style.py (status 보존 + 색상) ──")
    fix3_global_tree_style(sqm_root)
    print()

    print("── [4/6] ui_constants.py (상태색 + DARK_THEMES + 스크롤바) ──")
    fix4_ui_constants(sqm_root)
    print()

    print("── [5/6] toolbar_mixin.py (툴바 + 메뉴) ──")
    fix5_toolbar(sqm_root)
    print()

    print("── [6/6] table_styler.py (헤더) ──")
    fix6_table_styler(sqm_root)
    print()

    print("=" * 64)
    print("  ✅ Colorful UI Fix v4 완료!")
    print()
    print("  ★ 진짜 근본 원인:")
    print("    self.current_theme = 'flatly' → 실제 테마 자동 감지")
    print("    (cyborg/darkly 등 다크 테마가 정상 인식됨)")
    print()
    print("  ★ 추가 수정:")
    print("    ✅ ttkbootstrap Heading → 다크 퍼플 #2d2b55 강제")
    print("    ✅ Notebook Tab → 퍼플 테마")
    print("    ✅ _refresh_inventory monkey-patch (상태색 지속)")
    print("    ✅ status 태그 보존 (auto_style_applier)")
    print()
    print("  SQM을 재시작하면 적용됩니다.")
    print("=" * 64)
    input("\n  Enter...")


if __name__ == '__main__':
    main()
