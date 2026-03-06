# -*- coding: utf-8 -*-
"""
★★★ SQM v6.3.2 — Colorful UI Fix Patch v2 (통합) ★★★
======================================================
날짜: 2026-03-04
작성: Ruby

v1 대비 변경사항:
  - HOTFIX #1 통합: ThemeColors.DARK_THEMES → 인라인 튜플
  - HOTFIX #2 통합: configure_tags() 내 fg 변수 복원

문제: UI가 코드상 colorful하게 되어 있지만 실제로는 파란색으로만 보임
원인 4가지:
  1. 툴바/메뉴 색상이 테마 무관 블루 하드코딩
  2. DARK 상태 배경색이 너무 어두워 파랑과 구별 불가
  3. 스크롤바 다크/라이트 색상 반전 버그
  4. 테이블 헤더·교대행 블루 기조

적용법:
  ★ 이전 핫픽스(HOTFIX_DARK_THEMES, HOTFIX_FG_UNDEFINED) 적용 여부와 무관하게
    이 파일 하나만 실행하면 됩니다. (.bak 백업 자동 생성)

  1. SQM 폴더에 이 파일 복사
  2. 더블클릭 (또는 python PATCH_COLORFUL_FIX_v2.py)
  3. SQM 재시작
"""
import os
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
# FIX #1: ui_constants.py
#   - DARK 상태 배경색 밝게
#   - configure_tags() 상태별 고유 전경색 + fg 변수 유지
#   - is_dark_theme() cls.DARK_THEMES → 인라인 튜플
#   - 스크롤바 반전 수정
# ═══════════════════════════════════════════
def fix1_ui_constants(sqm_root):
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

    # ── (A) DARK 상태 배경색 교체 ──
    dark_color_map = {
        "'available': '#0f766e'": "'available': '#065f46'",
        "'reserved':  '#b45309'": "'reserved':  '#92400e'",
        "'picked':    '#7c3aed'": "'picked':    '#5b21b6'",
        "'shipped':   '#1d4ed8'": "'shipped':   '#1e3a5f'",
    }
    for old, new in dark_color_map.items():
        if old in content:
            content = content.replace(old, new)
            changed += 1

    # ── (B) configure_tags() — 2가지 패턴 대응 ──
    #   패턴1: v1 패치 적용됨 (fg 변수 없음) → fg 추가
    #   패턴2: 원본 (fg 있고 status_fg 없음) → 전체 교체

    NEW_CONFIGURE_TAGS = '''    @classmethod
    def configure_tags(cls, tree, is_dark: bool = False):
        """트리뷰 상태 태그 설정 (v6.3.2-colorful: 상태별 고유 전경색)"""
        p = cls.DARK if is_dark else cls.LIGHT
        fg = '#f0f0f0' if is_dark else '#1a1a1a'
        if is_dark:
            # ★ v6.3.2: 다크 모드 — 상태별 고유 밝은 전경색 (colorful)
            status_fg = {
                'available': '#6ee7b7',   # 밝은 에메랄드
                'reserved':  '#fcd34d',   # 밝은 골드
                'picked':    '#c4b5fd',   # 밝은 라벤더
                'shipped':   '#93c5fd',   # 밝은 스카이블루
            }
        else:
            status_fg = {
                'available': '#064e3b',
                'reserved':  '#78350f',
                'picked':    '#4c1d95',
                'shipped':   '#1e3a5f',
            }
        for status in ['available', 'picked', 'reserved', 'shipped']:
            tree.tag_configure(status, background=p[status],
                               foreground=status_fg.get(status, fg))
        # U9: depleted 태그
        tree.tag_configure('depleted', background='#f0f0f0' if not is_dark else '#2a2a2a',
                          foreground='#aaaaaa' if not is_dark else '#888888')
        # v3.6.2: 줄무늬 태그
        tree.tag_configure('stripe', background=p['tree_stripe'], foreground=fg)'''

    # 시작/끝 마커로 기존 함수 전체를 찾아서 교체
    import re
    pattern = re.compile(
        r'(    @classmethod\n    def configure_tags\(cls, tree, is_dark.*?\n)'
        r'(.*?)'
        r"(        tree\.tag_configure\('stripe'.*?\n)",
        re.DOTALL,
    )
    match = pattern.search(content)
    if match:
        content = content[:match.start()] + NEW_CONFIGURE_TAGS + '\n' + content[match.end():]
        changed += 1
        print("  ✅ configure_tags() 전체 교체 (fg 변수 + 상태별 고유색)")
    else:
        print("  ⚠️ configure_tags() 패턴 불일치 (수동 확인 필요)")

    # ── (C) is_dark_theme() — cls.DARK_THEMES → 인라인 튜플 ──
    old_dark_themes = "return theme_name.lower() in cls.DARK_THEMES"
    new_dark_themes = "return theme_name.lower() in ('darkly', 'cyborg', 'superhero', 'solar', 'vapor')"
    if old_dark_themes in content:
        content = content.replace(old_dark_themes, new_dark_themes)
        changed += 1
        print("  ✅ is_dark_theme() DARK_THEMES → 인라인 튜플")
    elif "('darkly', 'cyborg'" in content:
        print("  ℹ️ is_dark_theme() 이미 수정됨")
    else:
        print("  ⚠️ is_dark_theme() 패턴 미발견")

    # ── (D) 스크롤바 반전 수정 ──
    scroll_fixes = [
        ("trough = '#f2f2f2' if is_dark else '#111111'",
         "trough = '#111111' if is_dark else '#f2f2f2'  # v6.3.2-fix: 반전 수정"),
        ("thumb = '#111111' if is_dark else '#f2f2f2'",
         "thumb = '#f2f2f2' if is_dark else '#111111'  # v6.3.2-fix: 반전 수정"),
        ("active = '#000000' if is_dark else '#ffffff'",
         "active = '#ffffff' if is_dark else '#000000'  # v6.3.2-fix: 반전 수정"),
    ]
    for old, new in scroll_fixes:
        if old in content:
            content = content.replace(old, new)
            changed += 1

    if changed > 0:
        with open(target, 'w', encoding='utf-8') as f:
            f.write(content)
    print(f"  ✅ ui_constants.py — {changed}건 수정")
    return changed > 0


# ═══════════════════════════════════════════
# FIX #2: toolbar_mixin.py
#   - 툴바 블루 하드코딩 → 테마 반응형
#   - 드롭다운 메뉴 블루 → 보라/앰버
# ═══════════════════════════════════════════
def fix2_toolbar(sqm_root):
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

    # ── (A) _load_toolbar_colors ──
    #   패턴1: 원본 (하드코딩)
    #   패턴2: v1 패치 이미 적용됨
    OLD_LOAD_ORIGINAL = """    def _load_toolbar_colors(self) -> None:
        \"\"\"컬러풀 고정 팔레트 (테마와 무관하게 유지).\"\"\"
        self._tb_bg = '#0f172a'          # 진한 네이비
        self._tb_sep = '#334155'         # 구분선
        self._tb_fg_normal = '#cbd5e1'   # 비활성 텍스트
        self._tb_fg_active = '#ffffff'   # 활성 텍스트
        self._tb_fg_hover = '#93c5fd'    # 호버 텍스트
        self._tb_hover_bg = '#1e293b'    # 호버 배경
        self._tb_underline_color = '#3b82f6'  # 강조 파랑"""

    NEW_LOAD = """    def _load_toolbar_colors(self) -> None:
        \"\"\"v6.3.2-colorful: 다크/라이트 반응형 컬러풀 팔레트.\"\"\"
        is_dark = ThemeColors.is_dark_theme(getattr(self, 'current_theme', 'darkly'))
        if is_dark:
            self._tb_bg = '#1a1a2e'          # 딥 다크 퍼플 (네이비 탈피)
            self._tb_sep = '#3d3d5c'         # 보라 구분선
            self._tb_fg_normal = '#c0c0d0'   # 밝은 라벤더 그레이
            self._tb_fg_active = '#ffffff'   # 활성 텍스트
            self._tb_fg_hover = '#e0b0ff'    # 호버: 밝은 보라 (파랑 탈피)
            self._tb_hover_bg = '#2a2a4a'    # 호버 배경
            self._tb_underline_color = '#a78bfa'  # 밝은 바이올렛 강조
        else:
            self._tb_bg = '#1f2937'          # 다크 그레이
            self._tb_sep = '#4b5563'         # 구분선
            self._tb_fg_normal = '#d1d5db'   # 밝은 그레이
            self._tb_fg_active = '#ffffff'   # 활성 텍스트
            self._tb_fg_hover = '#fbbf24'    # 호버: 골드 (파랑 탈피)
            self._tb_hover_bg = '#374151'    # 호버 배경
            self._tb_underline_color = '#f59e0b'  # 앰버 강조"""

    if OLD_LOAD_ORIGINAL in content:
        content = content.replace(OLD_LOAD_ORIGINAL, NEW_LOAD)
        changed += 1
        print("  ✅ _load_toolbar_colors() 원본 → 테마 반응형")
    elif 'v6.3.2-colorful' in content:
        print("  ℹ️ _load_toolbar_colors() 이미 패치됨")
    else:
        print("  ⚠️ _load_toolbar_colors() 패턴 불일치")

    # ── (B) _create_menu 드롭다운 색상 ──
    OLD_MENU = """        menu_bg = '#0b1220'
        menu_fg = '#e2e8f0'
        menu_abg = '#1d4ed8'
        menu_afg = '#ffffff'
        menu_dis = '#64748b'"""

    NEW_MENU = """        # v6.3.2-colorful: 메뉴 색상 테마 반응형
        is_dark = ThemeColors.is_dark_theme(getattr(self, 'current_theme', 'darkly'))
        if is_dark:
            menu_bg = '#1a1a2e'       # 딥 다크 퍼플
            menu_fg = '#e2e8f0'
            menu_abg = '#7c3aed'      # 보라 활성배경 (파랑 탈피)
            menu_afg = '#ffffff'
            menu_dis = '#64748b'
        else:
            menu_bg = '#1f2937'
            menu_fg = '#f3f4f6'
            menu_abg = '#d97706'      # 앰버 활성배경
            menu_afg = '#ffffff'
            menu_dis = '#9ca3af'"""

    if OLD_MENU in content:
        content = content.replace(OLD_MENU, NEW_MENU)
        changed += 1
        print("  ✅ _create_menu() 드롭다운 색상 테마 반응형")
    elif 'v6.3.2-colorful: 메뉴' in content:
        print("  ℹ️ _create_menu() 이미 패치됨")
    else:
        print("  ⚠️ _create_menu() 패턴 불일치")

    if changed > 0:
        with open(target, 'w', encoding='utf-8') as f:
            f.write(content)
    print(f"  ✅ toolbar_mixin.py — {changed}건 수정")
    return changed > 0


# ═══════════════════════════════════════════
# FIX #3: table_styler.py — DARK 헤더 블루 → 퍼플
# ═══════════════════════════════════════════
def fix3_table_styler(sqm_root):
    target = os.path.join(sqm_root, 'gui_app_modular', 'utils', 'table_styler.py')
    if not os.path.isfile(target):
        print("  ❌ table_styler.py 없음")
        return False

    with open(target, 'r', encoding='utf-8') as f:
        content = f.read()
    bak = backup(target)
    if bak:
        print(f"  📋 백업: {bak}")

    old = "'header_bg': '#333333',"
    new = "'header_bg': '#2d2b55',  # v6.3.2: 다크 퍼플 헤더"
    if old in content:
        content = content.replace(old, new)
        with open(target, 'w', encoding='utf-8') as f:
            f.write(content)
        print("  ✅ DARK 헤더 색상 변경")
        return True
    elif '#2d2b55' in content:
        print("  ℹ️ 이미 패치됨")
    else:
        print("  ⚠️ 패턴 불일치")
    return False


# ═══════════════════════════════════════════
# FIX #4: global_tree_style.py — DARK 교대행 퍼플 기조
# ═══════════════════════════════════════════
def fix4_global_tree_style(sqm_root):
    target = os.path.join(sqm_root, 'fixes', 'global_tree_style.py')
    if not os.path.isfile(target):
        print("  ⚠️ global_tree_style.py 없음 (건너뜀)")
        return True

    with open(target, 'r', encoding='utf-8') as f:
        content = f.read()
    bak = backup(target)
    if bak:
        print(f"  📋 백업: {bak}")

    old = """    if is_dark:
        bg_color = '#2b2b2b'
        fg_color = '#e0e0e0'
        field_bg = '#2b2b2b'
        odd_bg = '#333333'
        even_bg = '#2b2b2b'"""

    new = """    if is_dark:
        bg_color = '#1e1e2e'       # v6.3.2: 약간 보라 기조
        fg_color = '#e0e0e0'
        field_bg = '#1e1e2e'
        odd_bg = '#282840'         # v6.3.2: 약간 보라 기조
        even_bg = '#1e1e2e'"""

    if old in content:
        content = content.replace(old, new)
        with open(target, 'w', encoding='utf-8') as f:
            f.write(content)
        print("  ✅ DARK 교대행 색상 수정")
        return True
    elif '#1e1e2e' in content:
        print("  ℹ️ 이미 패치됨")
    else:
        print("  ⚠️ 패턴 불일치")
    return False


def main():
    print()
    print("=" * 60)
    print("  🎨 SQM v6.3.2 — Colorful UI Fix v2 (통합)")
    print(f"  실행: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    print("  ★ 이전 HOTFIX #1, #2를 모두 포함합니다.")
    print("    기존 패치 적용 여부와 무관하게 안전 실행됩니다.")
    print("=" * 60)
    print()

    sqm_root = find_sqm_root()
    if not sqm_root:
        print("  ❌ SQM 프로젝트를 찾을 수 없습니다.")
        print("     이 파일을 SQM 폴더(run.py와 같은 위치)에 넣고 실행하세요.")
        input("\n  Enter 키를 누르면 종료...")
        return

    print(f"  📂 SQM 루트: {sqm_root}")
    print()

    results = []

    print("── [1/4] ui_constants.py (상태색 + 스크롤바 + DARK_THEMES) ──")
    results.append(fix1_ui_constants(sqm_root))
    print()

    print("── [2/4] toolbar_mixin.py (툴바 + 메뉴 색상) ──")
    results.append(fix2_toolbar(sqm_root))
    print()

    print("── [3/4] table_styler.py (테이블 헤더) ──")
    results.append(fix3_table_styler(sqm_root))
    print()

    print("── [4/4] global_tree_style.py (교대행) ──")
    results.append(fix4_global_tree_style(sqm_root))
    print()

    print("=" * 60)
    print("  ✅ Colorful UI Fix v2 완료!")
    print()
    print("  변경 요약:")
    print("   🟢 판매가능  : 어두운 블루 → 에메랄드 (BG #065f46 / FG #6ee7b7)")
    print("   🟡 판매배정  : 어두운 앰버 → 골드    (BG #92400e / FG #fcd34d)")
    print("   🟣 판매화물  : 어두운 보라 → 라벤더  (BG #5b21b6 / FG #c4b5fd)")
    print("   🔵 출고      : 진한 파랑  → 스틸블루 (BG #1e3a5f / FG #93c5fd)")
    print("   🟣 툴바      : 네이비 고정 → 다크 퍼플 (테마 반응형)")
    print("   🟡 메뉴 활성 : 파랑 고정  → 보라/앰버 (테마 반응형)")
    print("   🔄 스크롤바  : 다크/라이트 반전 버그 수정")
    print("   🔧 DARK_THEMES: AttributeError 수정")
    print("   🔧 fg 변수   : NameError 수정")
    print()
    print("  SQM을 재시작하면 적용됩니다.")
    print("=" * 60)

    input("\n  Enter 키를 누르면 종료...")


if __name__ == '__main__':
    main()
