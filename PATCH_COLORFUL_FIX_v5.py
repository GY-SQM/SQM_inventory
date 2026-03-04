# -*- coding: utf-8 -*-
"""
★★★ SQM v6.3.2 — Colorful UI Fix v5 (핵감 솔루션) ★★★
=======================================================
날짜: 2026-03-04
작성: Ruby (세계 최고의 프로그래머 + 슈퍼 양자 컴퓨터)

v1~v4가 실패한 이유:
  ttkbootstrap는 STANDARD_THEMES 딕셔너리에서 primary 색상을
  읽어서 모든 위젯(Heading, Tab, Button, Checkbox, Scrollbar...)에
  Tcl element_create로 적용함.
  
  개별 style.configure/style.map으로는 이 element를 덮어쓸 수 없음.
  (일부만 부분적으로 적용 → v4에서 보라색이 "좀" 보인 이유)

v5 핵감 솔루션:
  STANDARD_THEMES['cyborg']['colors']['primary']를
  Window 생성 전에 직접 수정.
  → ttkbootstrap가 테마를 빌드할 때 수정된 색상 사용
  → 모든 위젯에 자동 적용 (개별 패치 불필요)
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


# ═══════════════════════════════════════════
# GY 커스텀 테마 색상
# ═══════════════════════════════════════════
GY_COLORS = {
    'primary':   '#7c3aed',   # 바이올렛 (cyborg #2a9fd6 파랑 대체)
    'secondary': '#64748b',   # 슬레이트 그레이
    'success':   '#10b981',   # 에메랄드 그린
    'info':      '#06b6d4',   # 시안
    'warning':   '#f59e0b',   # 앰버
    'danger':    '#ef4444',   # 레드
    'light':     '#cbd5e1',   # 라이트 슬레이트
    'dark':      '#1e1b4b',   # 딥 퍼플
    'bg':        '#0a0a1a',   # 퍼플 틴트 블랙
    'fg':        '#e2e8f0',   # 밝은 슬레이트 화이트
    'selectbg':  '#5b21b6',   # 다크 바이올렛 (선택)
    'selectfg':  '#ffffff',
    'border':    '#2a2a4a',   # 퍼플 보더
    'inputfg':   '#ffffff',
    'inputbg':   '#12121e',   # 퍼플 틴트 입력 배경
    'active':    '#2a2a4a',
}

# 상태별 색상
STATUS_COLORS = {
    'available': {'bg': '#065f46', 'fg': '#6ee7b7'},  # 에메랄드
    'reserved':  {'bg': '#92400e', 'fg': '#fcd34d'},  # 골드
    'picked':    {'bg': '#5b21b6', 'fg': '#c4b5fd'},  # 라벤더
    'shipped':   {'bg': '#1e3a5f', 'fg': '#93c5fd'},  # 스카이블루
    'depleted':  {'bg': '#1a1a2a', 'fg': '#6b7280'},  # 뮤트 그레이
}


# ═══════════════════════════════════════════
# FIX #1: ★★★★★ main_app.py — 핵감 수정
#   (A) STANDARD_THEMES 직접 수정 (Window 생성 전)
#   (B) current_theme 동기화
#   (C) 최종 오버라이드 훅
# ═══════════════════════════════════════════
def fix1_main_app(sqm_root):
    target = os.path.join(sqm_root, 'gui_app_modular', 'main_app.py')
    if not os.path.isfile(target):
        print("  ❌ main_app.py 없음")
        return False

    with open(target, 'r', encoding='utf-8') as f:
        content = f.read()
    bak = backup(target)
    if bak:
        print(f"  📋 백업: {bak}")

    changed = 0

    # ═══ (A) Window 생성 전에 STANDARD_THEMES 수정 ═══
    # 이전 v4 패치가 있을 수 있으므로, 여러 패턴 대응

    # 현재 Window 생성 코드 패턴들
    PATTERNS = [
        # v4 패치된 상태 (theme_colorful_override 훅 포함)
        (r'(                import ttkbootstrap as ttk_bs\n'
         r'                theme = self\._load_theme_preference\(\)\n)'
         r'(                self\.root = ttk_bs\.Window\(themename=theme\))'),
        # 원본 상태
        (r'(            import ttkbootstrap as ttk_bs\n'
         r'                theme = self\._load_theme_preference\(\)\n)'
         r'(                self\.root = ttk_bs\.Window\(themename=theme\))'),
    ]

    # 단순 문자열 교체 방식 (가장 안전)
    OLD_WINDOW = """                import ttkbootstrap as ttk_bs
                theme = self._load_theme_preference()
                self.root = ttk_bs.Window(themename=theme)"""

    NEW_WINDOW = """                import ttkbootstrap as ttk_bs
                theme = self._load_theme_preference()
                # ★ v6.3.2-v5: ttkbootstrap primary 색상 소스 수정
                # Window 생성 전에 STANDARD_THEMES를 수정하면
                # 모든 위젯에 자동으로 새 색상이 적용됨
                try:
                    from ttkbootstrap.themes.standard import STANDARD_THEMES
                    _gy_colors = {
                        'primary':   '#7c3aed',
                        'secondary': '#64748b',
                        'success':   '#10b981',
                        'info':      '#06b6d4',
                        'warning':   '#f59e0b',
                        'danger':    '#ef4444',
                        'light':     '#cbd5e1',
                        'dark':      '#1e1b4b',
                        'bg':        '#0a0a1a',
                        'fg':        '#e2e8f0',
                        'selectbg':  '#5b21b6',
                        'selectfg':  '#ffffff',
                        'border':    '#2a2a4a',
                        'inputfg':   '#ffffff',
                        'inputbg':   '#12121e',
                        'active':    '#2a2a4a',
                    }
                    if theme in STANDARD_THEMES:
                        STANDARD_THEMES[theme]['colors'].update(_gy_colors)
                except Exception as _e:
                    import logging
                    logging.getLogger(__name__).debug(f"Theme color override: {_e}")
                self.root = ttk_bs.Window(themename=theme)"""

    if OLD_WINDOW in content:
        content = content.replace(OLD_WINDOW, NEW_WINDOW)
        changed += 1
        print("  ✅ [★핵감] STANDARD_THEMES 직접 수정 (Window 생성 전)")
    elif 'STANDARD_THEMES' in content:
        print("  ℹ️ STANDARD_THEMES 이미 수정됨")
    else:
        print("  ⚠️ Window 생성 패턴 미발견")

    # ═══ (B) current_theme 동기화 ═══
    OLD_CT = "self.current_theme = 'flatly'  # v3.0: 고급스러운 기본 테마"
    NEW_CT = """# ★ v6.3.2-v5: 실제 테마 동기화
        try:
            from tkinter import ttk as _ttk_detect
            self.current_theme = _ttk_detect.Style().theme_use() or 'darkly'
        except Exception:
            self.current_theme = 'darkly'"""

    if OLD_CT in content:
        content = content.replace(OLD_CT, NEW_CT)
        changed += 1
        print("  ✅ current_theme 실제 테마 동기화")
    elif "_ttk_detect" in content:
        print("  ℹ️ current_theme 이미 수정됨")

    # ═══ (C) 최종 오버라이드 훅 (Treeview Heading + 상태색) ═══
    HOOK_MARKER = "theme_colorful_override"
    if HOOK_MARKER not in content:
        # auto_style_applier after(1000) 뒤에 추가
        HOOK_ANCHOR = "self.root.after(1000, lambda: apply_styles_to_all_trees(self.root))"
        HOOK_CODE = """self.root.after(1000, lambda: apply_styles_to_all_trees(self.root))
            # ★ v6.3.2-v5: 최종 Treeview 오버라이드
            try:
                from fixes.theme_colorful_override import apply_colorful_overrides
                self.root.after(1500, lambda: apply_colorful_overrides(self))
            except ImportError:
                pass"""

        if HOOK_ANCHOR in content:
            content = content.replace(HOOK_ANCHOR, HOOK_CODE)
            changed += 1
            print("  ✅ 최종 오버라이드 훅 추가")
        else:
            print("  ⚠️ 오버라이드 훅 앵커 미발견")
    else:
        print("  ℹ️ 오버라이드 훅 이미 존재")

    if changed > 0:
        with open(target, 'w', encoding='utf-8') as f:
            f.write(content)
    return changed > 0


# ═══════════════════════════════════════════
# FIX #2: theme_colorful_override.py (재작성)
#   Treeview Heading 강제 + 상태색 + monkey-patch
# ═══════════════════════════════════════════
def fix2_override_module(sqm_root):
    target = os.path.join(sqm_root, 'fixes', 'theme_colorful_override.py')
    os.makedirs(os.path.join(sqm_root, 'fixes'), exist_ok=True)

    code = r'''# -*- coding: utf-8 -*-
"""
SQM v6.3.2-v5 — 최종 Treeview 오버라이드
==========================================
main_app.py after(1500)에서 호출.
STANDARD_THEMES 수정으로 대부분의 위젯은 자동 처리되지만,
Treeview Heading과 상태 태그는 추가 오버라이드 필요.
"""
import logging
from tkinter import ttk

logger = logging.getLogger(__name__)

STATUS_TAGS = frozenset({'available', 'picked', 'reserved', 'shipped', 'depleted'})

# Treeview Heading (v5: STANDARD_THEMES 수정으로 대부분 처리되나, 안전장치)
HEAD = {'bg': '#2d2b55', 'fg': '#ffffff', 'hover': '#3d3a6e'}

# 상태별 색상
S_DARK = {
    'available': ('#065f46', '#6ee7b7'),
    'reserved':  ('#92400e', '#fcd34d'),
    'picked':    ('#5b21b6', '#c4b5fd'),
    'shipped':   ('#1e3a5f', '#93c5fd'),
    'depleted':  ('#1a1a2a', '#6b7280'),
    'stripe':    ('#111122', '#c0c0d0'),
    'odd':       ('#111122', '#c0c0d0'),
    'even':      ('#0a0a1a', '#c0c0d0'),
}

S_LIGHT = {
    'available': ('#d1fae5', '#064e3b'),
    'reserved':  ('#fef3c7', '#78350f'),
    'picked':    ('#ede9fe', '#4c1d95'),
    'shipped':   ('#dbeafe', '#1e3a5f'),
    'depleted':  ('#f0f0f0', '#aaaaaa'),
    'stripe':    ('#F8F9FA', '#1a1a1a'),
    'odd':       ('#F8F9FA', '#1a1a1a'),
    'even':      ('#FFFFFF', '#1a1a1a'),
}


def _is_dark(theme=None):
    if theme is None:
        try:
            theme = ttk.Style().theme_use() or ''
        except Exception:
            theme = ''
    return theme.lower() in ('darkly', 'cyborg', 'superhero', 'solar', 'vapor')


def apply_colorful_overrides(app):
    """최종 오버라이드 — Treeview Heading + 상태색 + monkey-patch"""
    try:
        style = ttk.Style()
        actual = style.theme_use() or 'darkly'
        dark = _is_dark(actual)

        # 1. current_theme 동기화
        if hasattr(app, 'current_theme'):
            app.current_theme = actual

        # 2. Treeview Heading 강화 (STANDARD_THEMES가 적용 안 되는 경우 대비)
        style.configure('Treeview.Heading',
            background=HEAD['bg'], foreground=HEAD['fg'],
            font=('맑은 고딕', 10, 'bold'))
        style.map('Treeview.Heading',
            background=[('active', HEAD['hover']), ('!disabled', HEAD['bg'])],
            foreground=[('active', HEAD['fg']), ('!disabled', HEAD['fg'])])

        # 3. Treeview 기본 스타일
        if dark:
            style.configure('Treeview',
                fieldbackground='#0a0a1a', background='#0a0a1a',
                foreground='#e2e8f0', rowheight=30)
            style.map('Treeview',
                background=[('selected', '#5b21b6')],
                foreground=[('selected', '#ffffff'), ('!selected', '#e2e8f0')])

        # 4. 모든 Treeview에 상태 태그 적용
        _apply_all(app, dark)

        # 5. monkey-patch (데이터 로드 후 상태색 유지)
        _install_hooks(app, dark)

        logger.info(f"✅ v5 override done (theme={actual}, dark={dark})")
    except Exception as e:
        logger.error(f"Override error: {e}")
        import traceback; traceback.print_exc()


def _apply_tags(tree, dark):
    """Treeview에 상태 태그 색상 적용"""
    palette = S_DARK if dark else S_LIGHT
    for tag, (bg, fg) in palette.items():
        tree.tag_configure(tag, background=bg, foreground=fg)


def _apply_all(app, dark):
    """모든 주요 Treeview에 적용"""
    count = 0
    for attr in ['tree_inventory', 'tree_sublot', 'tree_allocation',
                 'tree_picked', 'tree_sold', 'tree_overview']:
        tree = getattr(app, attr, None)
        if tree:
            try:
                _apply_tags(tree, dark)
                count += 1
            except Exception:
                pass
    logger.info(f"✅ Status tags: {count} trees")


def _install_hooks(app, dark):
    """_refresh_inventory 등 monkey-patch"""
    if getattr(app, '_v5_hooked', False):
        return

    for method, tree_attr in [
        ('_refresh_inventory', 'tree_inventory'),
        ('_refresh_sublot_list', 'tree_sublot'),
    ]:
        orig = getattr(app, method, None)
        tree = getattr(app, tree_attr, None)
        if not orig or not tree:
            continue

        def make_hook(fn, tw, dk):
            def hooked(*a, **kw):
                r = fn(*a, **kw)
                try:
                    _apply_tags(tw, dk)
                except Exception:
                    pass
                return r
            return hooked

        setattr(app, method, make_hook(orig, tree, dark))
        logger.info(f"✅ Hook: {method}")

    app._v5_hooked = True
'''

    with open(target, 'w', encoding='utf-8') as f:
        f.write(code)
    print("  ✅ fixes/theme_colorful_override.py 생성 (v5)")
    return True


# ═══════════════════════════════════════════
# FIX #3: global_tree_style.py — status 보존
# ═══════════════════════════════════════════
def fix3_global_tree_style(sqm_root):
    target = os.path.join(sqm_root, 'fixes', 'global_tree_style.py')
    if not os.path.isfile(target):
        return True

    with open(target, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'STATUS_TAGS' in content and 'preserved' in content:
        print("  ℹ️ 이미 status 보존 적용됨")
        return True

    bak = backup(target)
    if bak:
        print(f"  📋 백업: {bak}")

    # apply_to_tree_immediately → status 보존
    OLD = """    # 기존 데이터에 줄무늬 적용
    for i, item in enumerate(tree.get_children()):
        tag = 'odd' if i % 2 else 'even'
        tree.item(item, tags=(tag,))"""

    NEW = """    # ★ v5: status 태그 보존하면서 줄무늬
    STATUS_TAGS = frozenset({'available','picked','reserved','shipped','depleted'})
    for i, item in enumerate(tree.get_children()):
        existing = set(tree.item(item, 'tags') or ())
        preserved = existing & STATUS_TAGS
        if preserved:
            new_tags = tuple(preserved)
        else:
            new_tags = ('odd' if i % 2 else 'even',)
        tree.item(item, tags=new_tags)"""

    if OLD in content:
        content = content.replace(OLD, NEW)
        with open(target, 'w', encoding='utf-8') as f:
            f.write(content)
        print("  ✅ apply_to_tree_immediately → status 보존")
    else:
        print("  ℹ️ 이미 수정됨 또는 패턴 불일치")
    return True


# ═══════════════════════════════════════════
# FIX #4: ui_constants.py 최소 수정
# ═══════════════════════════════════════════
def fix4_ui_constants(sqm_root):
    target = os.path.join(sqm_root, 'gui_app_modular', 'utils', 'ui_constants.py')
    if not os.path.isfile(target):
        return False

    with open(target, 'r', encoding='utf-8') as f:
        content = f.read()
    bak = backup(target)
    if bak:
        print(f"  📋 백업: {bak}")

    changed = 0
    # cls.DARK_THEMES → 인라인 튜플
    old = "return theme_name.lower() in cls.DARK_THEMES"
    new = "return theme_name.lower() in ('darkly', 'cyborg', 'superhero', 'solar', 'vapor')"
    if old in content:
        content = content.replace(old, new)
        changed += 1
        print("  ✅ is_dark_theme() 수정")
    elif "('darkly', 'cyborg'" in content:
        print("  ℹ️ is_dark_theme() 이미 수정됨")

    # 스크롤바 반전
    for o, n in [
        ("trough = '#f2f2f2' if is_dark else '#111111'",
         "trough = '#111111' if is_dark else '#f2f2f2'"),
        ("thumb = '#111111' if is_dark else '#f2f2f2'",
         "thumb = '#f2f2f2' if is_dark else '#111111'"),
    ]:
        if o in content:
            content = content.replace(o, n)
            changed += 1

    if changed > 0:
        with open(target, 'w', encoding='utf-8') as f:
            f.write(content)
    print(f"  ✅ ui_constants.py — {changed}건 수정")
    return True


def main():
    print()
    print("=" * 64)
    print("  🎨 SQM v6.3.2 — Colorful UI Fix v5 (핵감 솔루션)")
    print(f"  실행: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("  ★ v5 전략: ttkbootstrap 색상 소스 직접 수정")
    print("  ★ STANDARD_THEMES['cyborg']['colors'] 딕셔너리를")
    print("  ★ Window 생성 전에 GY 커스텀 색상으로 교체")
    print("  ★ → 모든 위젯에 자동 cascade (개별 패치 불필요)")
    print("=" * 64)
    print()

    sqm_root = find_sqm_root()
    if not sqm_root:
        print("  ❌ SQM 폴더 미발견")
        input("\n  Enter...")
        return

    print(f"  📂 SQM 루트: {sqm_root}")
    print()

    print("── [1/4] ★ main_app.py (핵감: STANDARD_THEMES 수정) ──")
    fix1_main_app(sqm_root)
    print()

    print("── [2/4] theme_colorful_override.py (Treeview + 상태색) ──")
    fix2_override_module(sqm_root)
    print()

    print("── [3/4] global_tree_style.py (status 보존) ──")
    fix3_global_tree_style(sqm_root)
    print()

    print("── [4/4] ui_constants.py (is_dark + 스크롤바) ──")
    fix4_ui_constants(sqm_root)
    print()

    print("=" * 64)
    print("  ✅ Colorful UI Fix v5 완료!")
    print()
    print("  GY 커스텀 테마 색상:")
    print("   🟣 Primary:  #7c3aed (바이올렛)")
    print("   🟦 Info:     #06b6d4 (시안)")
    print("   🟢 Success:  #10b981 (에메랄드)")
    print("   🟡 Warning:  #f59e0b (앰버)")
    print("   🔴 Danger:   #ef4444 (레드)")
    print("   🌑 BG:       #0a0a1a (퍼플 블랙)")
    print()
    print("  상태별 행 색상 (다크 모드):")
    print("   🟢 판매가능: BG #065f46 / FG #6ee7b7")
    print("   🟡 판매배정: BG #92400e / FG #fcd34d")
    print("   🟣 판매화물: BG #5b21b6 / FG #c4b5fd")
    print("   🔵 출고:    BG #1e3a5f / FG #93c5fd")
    print()
    print("  SQM을 재시작하면 적용됩니다.")
    print("=" * 64)
    input("\n  Enter...")


if __name__ == '__main__':
    main()
