# -*- coding: utf-8 -*-
"""
★★★ SQM v6.3.2 — Colorful UI FINAL Patch v5 ★★★
====================================================
날짜: 2026-03-04
작성: Ruby

★ 이전 패치(v1~v4, 다른AI 패치) 적용 여부와 무관하게
★ 어떤 상태에서든 안전하게 실행됩니다.

핵감 전략:
  ttkbootstrap는 STANDARD_THEMES 딕셔너리에서 색상을 읽어
  모든 위젯(Heading, Tab, Button, Scrollbar...)에 Tcl element로 적용.
  → 개별 style.configure로는 변경 불가
  → STANDARD_THEMES를 Window 생성 전에 수정하면 전체 적용

수정 내용:
  [1] main_app.py — STANDARD_THEMES 소스 수정 + current_theme 동기화
  [2] fixes/theme_colorful_override.py — Treeview 상태색 + monkey-patch
  [3] fixes/global_tree_style.py — status 태그 보존
  [4] gui_app_modular/utils/ui_constants.py — is_dark_theme + 스크롤바
"""
import os
import re
import shutil
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def find_sqm_root():
    """SQM 루트 폴더 탐색"""
    check = SCRIPT_DIR
    for _ in range(4):
        if os.path.isdir(os.path.join(check, 'gui_app_modular')):
            return check
        check = os.path.dirname(check)
    return None


def backup(filepath):
    """안전 백업 (.bak_날짜시간)"""
    if os.path.isfile(filepath):
        bak = filepath + f'.bak_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        shutil.copy2(filepath, bak)
        return os.path.basename(bak)
    return None


# ═══════════════════════════════════════════
# GY Logistics 커스텀 테마 색상
# ═══════════════════════════════════════════
GY_THEME_COLORS_CODE = """\
                    _gy_colors = {
                        'primary':   '#7c3aed',   # 바이올렛
                        'secondary': '#64748b',   # 슬레이트
                        'success':   '#10b981',   # 에메랄드
                        'info':      '#06b6d4',   # 시안
                        'warning':   '#f59e0b',   # 앰버
                        'danger':    '#ef4444',   # 레드
                        'light':     '#cbd5e1',
                        'dark':      '#1e1b4b',
                        'bg':        '#0a0a1a',   # 퍼플 블랙
                        'fg':        '#e2e8f0',   # 밝은 슬레이트
                        'selectbg':  '#5b21b6',   # 다크 바이올렛
                        'selectfg':  '#ffffff',
                        'border':    '#2a2a4a',
                        'inputfg':   '#ffffff',
                        'inputbg':   '#12121e',
                        'active':    '#2a2a4a',
                    }"""


# ═══════════════════════════════════════════
# [1/4] main_app.py — 핵감 수정
# ═══════════════════════════════════════════
def fix_main_app(sqm_root):
    target = os.path.join(sqm_root, 'gui_app_modular', 'main_app.py')
    if not os.path.isfile(target):
        print("  ❌ main_app.py 없음")
        return False

    with open(target, 'r', encoding='utf-8') as f:
        content = f.read()
    original = content
    bak = backup(target)
    if bak:
        print(f"  📋 백업: {bak}")

    # ─── (A) STANDARD_THEMES 수정 삽입 ───
    if 'STANDARD_THEMES' not in content:
        # Window 생성 직전에 삽입 (모든 상태 대응: regex)
        pat = re.compile(
            r'([ \t]+)(import ttkbootstrap as ttk_bs\n'
            r'[ \t]+theme = self\._load_theme_preference\(\)\n)'
            r'([ \t]+self\.root = ttk_bs\.Window\(themename=theme\))'
        )
        match = pat.search(content)
        if match:
            indent = match.group(1)
            NEW_BLOCK = (
                f"{match.group(1)}import ttkbootstrap as ttk_bs\n"
                f"{indent}theme = self._load_theme_preference()\n"
                f"{indent}# ★ v5-FINAL: ttkbootstrap 색상 소스 직접 수정\n"
                f"{indent}try:\n"
                f"{indent}    from ttkbootstrap.themes.standard import STANDARD_THEMES\n"
                f"{GY_THEME_COLORS_CODE}\n"
                f"{indent}    if theme in STANDARD_THEMES:\n"
                f"{indent}        STANDARD_THEMES[theme]['colors'].update(_gy_colors)\n"
                f"{indent}except Exception as _e:\n"
                f"{indent}    import logging as _log\n"
                f"{indent}    _log.getLogger(__name__).debug(f'Theme override: {{_e}}')\n"
                f"{indent}self.root = ttk_bs.Window(themename=theme)"
            )
            content = content[:match.start()] + NEW_BLOCK + content[match.end():]
            print("  ✅ [핵감] STANDARD_THEMES 직접 수정 삽입")
        else:
            print("  ⚠️ Window 생성 패턴 미발견 — 수동 확인 필요")
    else:
        # 이미 있으면 _gy_colors 값만 업데이트
        old_primary = re.search(r"'primary':\s*'[^']*'", content)
        if old_primary and '#7c3aed' not in old_primary.group():
            content = re.sub(
                r"('primary':\s*)'[^']*'",
                r"\1'#7c3aed'",
                content, count=1)
            print("  ✅ STANDARD_THEMES primary 색상 업데이트")
        else:
            print("  ℹ️ STANDARD_THEMES 이미 적용됨")

    # ─── (B) current_theme 동기화 ───
    # 패턴1: flatly/darkly/cosmo 등 어떤 테마든 하드코딩
    # 패턴2: _ttk_detect (v4 패치) — 이미 자동 감지
    CT_REPLACEMENT = (
        "# ★ v5-FINAL: 실제 테마 자동 감지\n"
        "        try:\n"
        "            from tkinter import ttk as _ttk_detect\n"
        "            self.current_theme = _ttk_detect.Style().theme_use() or 'darkly'\n"
        "        except Exception:\n"
        "            self.current_theme = 'darkly'"
    )

    if '_ttk_detect' in content and 'v5-FINAL' in content:
        print("  ℹ️ current_theme 이미 v5 자동 감지 적용됨")
    elif '_ttk_detect' in content:
        print("  ℹ️ current_theme 이미 자동 감지 적용됨 (v4)")
    else:
        # 하드코딩된 current_theme 찾기 (flatly, darkly, cosmo 등 모든 테마)
        hardcode_pat = re.compile(
            r"        self\.current_theme\s*=\s*'[a-z]+'[^\n]*\n")
        match_ct = hardcode_pat.search(content)
        if match_ct:
            old_line = match_ct.group().strip()
            content = content[:match_ct.start()] + f"        {CT_REPLACEMENT}\n" + content[match_ct.end():]
            print(f"  ✅ current_theme: '{old_line}' → 자동 감지")

    # ─── (C) 최종 오버라이드 훅 ───
    HOOK_MARKER = "theme_colorful_override"
    if HOOK_MARKER not in content:
        # after(1000) 앵커 찾기 (여러 변형 대응)
        anchor_pat = re.compile(
            r"(self\.root\.after\(1000,\s*lambda:\s*apply_styles_to_all_trees\(self\.root\)\))")
        match = anchor_pat.search(content)
        if match:
            HOOK = (
                f"{match.group(1)}\n"
                f"            # ★ v5-FINAL: 최종 Treeview 오버라이드\n"
                f"            try:\n"
                f"                from fixes.theme_colorful_override import apply_colorful_overrides\n"
                f"                self.root.after(1500, lambda: apply_colorful_overrides(self))\n"
                f"            except ImportError:\n"
                f"                pass"
            )
            content = content.replace(match.group(1), HOOK)
            print("  ✅ 최종 오버라이드 훅 추가 (after 1500ms)")
        else:
            # 앵커 없으면 _load_initial_data 끝에 추가
            load_pat = re.search(r'(def _load_initial_data.*?\n)', content)
            if load_pat:
                print("  ⚠️ auto_style_applier 앵커 미발견 — 수동 확인 필요")
    else:
        print("  ℹ️ 오버라이드 훅 이미 존재")

    if content != original:
        with open(target, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False


# ═══════════════════════════════════════════
# [2/4] theme_colorful_override.py (새 파일)
# ═══════════════════════════════════════════
def fix_override_module(sqm_root):
    target = os.path.join(sqm_root, 'fixes', 'theme_colorful_override.py')
    os.makedirs(os.path.join(sqm_root, 'fixes'), exist_ok=True)

    code = r'''# -*- coding: utf-8 -*-
"""
SQM v6.3.2 v5-FINAL — 최종 Treeview 오버라이드
=================================================
main_app.py after(1500)에서 호출.
STANDARD_THEMES 수정으로 대부분의 위젯 색상은 자동 처리.
이 모듈은 Treeview 특화 추가 작업만 담당:
  1. Heading 이중 안전장치
  2. 상태별 행 색상 (available/picked/reserved/shipped)
  3. _refresh_inventory monkey-patch (데이터 로드 후 상태색 유지)
"""
import logging
from tkinter import ttk

logger = logging.getLogger(__name__)

STATUS_TAGS = frozenset({'available', 'picked', 'reserved', 'shipped', 'depleted'})

# Treeview Heading (STANDARD_THEMES + 이중 보험)
HEAD = {'bg': '#2d2b55', 'fg': '#ffffff', 'hover': '#3d3a6e'}

# 상태별 색상 (다크/라이트)
S_DARK = {
    'available': ('#065f46', '#6ee7b7'),   # 에메랄드
    'reserved':  ('#92400e', '#fcd34d'),   # 골드
    'picked':    ('#5b21b6', '#c4b5fd'),   # 라벤더
    'shipped':   ('#1e3a5f', '#93c5fd'),   # 스카이블루
    'depleted':  ('#1a1a2a', '#6b7280'),   # 뮤트
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
    """최종 오버라이드 (after 1500ms에서 호출)"""
    try:
        style = ttk.Style()
        actual = style.theme_use() or 'darkly'
        dark = _is_dark(actual)

        # 1. current_theme 재동기화
        if hasattr(app, 'current_theme'):
            app.current_theme = actual

        # 2. Heading 이중 보험 (STANDARD_THEMES가 커버 못하는 경우)
        style.configure('Treeview.Heading',
            background=HEAD['bg'], foreground=HEAD['fg'],
            font=('맑은 고딕', 10, 'bold'))
        style.map('Treeview.Heading',
            background=[('active', HEAD['hover']), ('!disabled', HEAD['bg'])],
            foreground=[('active', HEAD['fg']), ('!disabled', HEAD['fg'])])

        # 3. Treeview 본문
        if dark:
            style.configure('Treeview',
                fieldbackground='#0a0a1a', background='#0a0a1a',
                foreground='#e2e8f0', rowheight=30,
                font=('맑은 고딕', 9))
            style.map('Treeview',
                background=[('selected', '#5b21b6')],
                foreground=[('selected', '#ffffff'), ('!selected', '#e2e8f0')])

        # 4. 모든 Treeview 상태색 적용
        _apply_all(app, dark)

        # 5. monkey-patch (_refresh 후 상태색 유지)
        _install_hooks(app, dark)

        logger.info(f"[v5-FINAL] override OK (theme={actual}, dark={dark})")
    except Exception as e:
        logger.error(f"[v5-FINAL] override error: {e}")
        import traceback; traceback.print_exc()


def _apply_tags(tree, dark):
    """Treeview 상태 태그 색상"""
    palette = S_DARK if dark else S_LIGHT
    for tag, (bg, fg) in palette.items():
        tree.tag_configure(tag, background=bg, foreground=fg)


def _apply_all(app, dark):
    """모든 주요 Treeview에 적용"""
    n = 0
    for attr in ['tree_inventory', 'tree_sublot', 'tree_allocation',
                 'tree_picked', 'tree_sold', 'tree_overview']:
        tree = getattr(app, attr, None)
        if tree:
            try:
                _apply_tags(tree, dark)
                n += 1
            except Exception:
                pass
    logger.info(f"[v5-FINAL] status tags → {n} trees")


def _install_hooks(app, dark):
    """_refresh_inventory monkey-patch (상태색 덮어쓰기 방지)"""
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
        logger.info(f"[v5-FINAL] hook → {method}")

    app._v5_hooked = True
'''

    with open(target, 'w', encoding='utf-8') as f:
        f.write(code)
    print("  ✅ fixes/theme_colorful_override.py 생성")
    return True


# ═══════════════════════════════════════════
# [3/4] global_tree_style.py — status 태그 보존
# ═══════════════════════════════════════════
def fix_global_tree_style(sqm_root):
    target = os.path.join(sqm_root, 'fixes', 'global_tree_style.py')
    if not os.path.isfile(target):
        print("  ⚠️ global_tree_style.py 없음 (건너뜀)")
        return True

    with open(target, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'STATUS_TAGS' in content and 'preserved' in content:
        print("  ℹ️ status 보존 이미 적용됨")
        return True

    bak = backup(target)
    if bak:
        print(f"  📋 백업: {bak}")

    # 태그 파괴 코드 교체 (다양한 패턴 대응)
    OLD_PAT = re.compile(
        r'(    # 기존 데이터에 줄무늬 적용\n)?'
        r'    for i, item in enumerate\(tree\.get_children\(\)\):\n'
        r'        tag = \'odd\' if i % 2 else \'even\'\n'
        r'        tree\.item\(item, tags=\(tag,\)\)'
    )

    NEW_CODE = (
        "    # ★ v5-FINAL: status 태그 보존하면서 줄무늬\n"
        "    _STATUS = frozenset({'available','picked','reserved','shipped','depleted'})\n"
        "    for i, item in enumerate(tree.get_children()):\n"
        "        existing = set(tree.item(item, 'tags') or ())\n"
        "        preserved = existing & _STATUS\n"
        "        if preserved:\n"
        "            new_tags = tuple(preserved)\n"
        "        else:\n"
        "            new_tags = ('odd' if i % 2 else 'even',)\n"
        "        tree.item(item, tags=new_tags)"
    )

    match = OLD_PAT.search(content)
    if match:
        content = content[:match.start()] + NEW_CODE + content[match.end():]
        with open(target, 'w', encoding='utf-8') as f:
            f.write(content)
        print("  ✅ apply_to_tree_immediately → status 보존")
    else:
        print("  ⚠️ 줄무늬 패턴 미발견 (이미 수정됨 또는 구조 다름)")
    return True


# ═══════════════════════════════════════════
# [4/4] ui_constants.py — is_dark_theme + 스크롤바
# ═══════════════════════════════════════════
def fix_ui_constants(sqm_root):
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

    # is_dark_theme: cls.DARK_THEMES → 인라인 튜플
    old = "return theme_name.lower() in cls.DARK_THEMES"
    new = "return theme_name.lower() in ('darkly', 'cyborg', 'superhero', 'solar', 'vapor')"
    if old in content:
        content = content.replace(old, new)
        changed += 1
        print("  ✅ is_dark_theme() → 인라인 튜플")
    elif "('darkly', 'cyborg'" in content:
        print("  ℹ️ is_dark_theme() 이미 수정됨")

    # 스크롤바 반전 수정
    scroll_fixes = [
        ("trough = '#f2f2f2' if is_dark else '#111111'",
         "trough = '#111111' if is_dark else '#f2f2f2'"),
        ("thumb = '#111111' if is_dark else '#f2f2f2'",
         "thumb = '#f2f2f2' if is_dark else '#111111'"),
        ("active = '#000000' if is_dark else '#ffffff'",
         "active = '#ffffff' if is_dark else '#000000'"),
    ]
    for old_s, new_s in scroll_fixes:
        if old_s in content:
            content = content.replace(old_s, new_s)
            changed += 1

    if changed > 0:
        with open(target, 'w', encoding='utf-8') as f:
            f.write(content)
    print(f"  ✅ ui_constants.py — {changed}건 수정")
    return True


# ═══════════════════════════════════════════
# 보너스: theme_preference.json 확인/복원
# ═══════════════════════════════════════════
def check_theme_pref(sqm_root):
    import json
    pref_file = os.path.join(sqm_root, 'theme_preference.json')
    if os.path.isfile(pref_file):
        try:
            with open(pref_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            theme = data.get('theme', '')
            print(f"  현재 테마: {theme}")
            if theme not in ('darkly', 'cyborg', 'superhero', 'solar', 'vapor'):
                print(f"  ⚠️ 라이트 테마({theme})가 설정되어 있음 → cyborg로 변경")
                data['theme'] = 'cyborg'
                with open(pref_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f)
                print("  ✅ theme_preference.json → cyborg")
        except Exception as e:
            print(f"  ⚠️ 읽기 실패: {e}")
    else:
        print("  ℹ️ theme_preference.json 없음 (기본값 darkly 사용)")


def main():
    print()
    print("=" * 64)
    print("  🎨 SQM v6.3.2 — Colorful UI FINAL Patch v5")
    print(f"  실행: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("  핵감 전략: ttkbootstrap STANDARD_THEMES 소스 수정")
    print("  → Window 생성 전에 색상을 바꿔서 모든 위젯에 cascade")
    print()
    print("  ★ v1~v4, 다른AI 패치 적용 여부 무관 안전 실행 ★")
    print("=" * 64)
    print()

    sqm_root = find_sqm_root()
    if not sqm_root:
        print("  ❌ SQM 폴더 미발견")
        print("     이 파일을 SQM 폴더(run.py와 같은 위치)에 넣고 실행하세요.")
        input("\n  Enter...")
        return

    print(f"  📂 SQM 루트: {sqm_root}")
    print()

    print("── [0] theme_preference.json 확인 ──")
    check_theme_pref(sqm_root)
    print()

    print("── [1/4] ★ main_app.py (핵감: STANDARD_THEMES + 동기화) ──")
    fix_main_app(sqm_root)
    print()

    print("── [2/4] theme_colorful_override.py (Treeview 상태색) ──")
    fix_override_module(sqm_root)
    print()

    print("── [3/4] global_tree_style.py (status 태그 보존) ──")
    fix_global_tree_style(sqm_root)
    print()

    print("── [4/4] ui_constants.py (is_dark + 스크롤바) ──")
    fix_ui_constants(sqm_root)
    print()

    print("=" * 64)
    print("  ✅ Colorful UI FINAL v5 완료!")
    print()
    print("  적용된 GY 커스텀 색상:")
    print("   🟣 Primary:  #7c3aed (바이올렛) → 헤더/탭/버튼/스크롤바 전체")
    print("   🟦 Info:     #06b6d4 (시안)")
    print("   🟢 Success:  #10b981 (에메랄드)")
    print("   🟡 Warning:  #f59e0b (앰버)")
    print("   🔴 Danger:   #ef4444 (레드)")
    print("   🌑 BG:       #0a0a1a (퍼플 블랙)")
    print()
    print("  상태별 행 색상:")
    print("   🟢 판매가능: 에메랄드  (#065f46 / #6ee7b7)")
    print("   🟡 판매배정: 골드      (#92400e / #fcd34d)")
    print("   🟣 판매화물: 라벤더    (#5b21b6 / #c4b5fd)")
    print("   🔵 출고:    스카이블루 (#1e3a5f / #93c5fd)")
    print()
    print("  ➡️ SQM을 재시작하세요.")
    print("=" * 64)
    input("\n  Enter...")


if __name__ == '__main__':
    main()
