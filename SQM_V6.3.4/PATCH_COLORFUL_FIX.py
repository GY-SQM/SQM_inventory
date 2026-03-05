# -*- coding: utf-8 -*-
"""
★★★ SQM v6.3.2 — Colorful UI Fix Patch ★★★
=============================================
날짜: 2026-03-04
작성: Ruby

문제: UI가 코드상 colorful하게 되어 있지만 실제로는 파란색으로만 보임
원인: 4가지 (하드코딩 블루 팔레트, 어두운 DARK 상태색, 스크롤바 반전, 메뉴 블루 고정)

적용법:
  1. SQM 폴더에 이 파일 복사
  2. python PATCH_COLORFUL_FIX.py 실행
  3. SQM 재시작
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
        return bak
    return None


# ═══════════════════════════════════════════
# FIX #1: DARK 팔레트 상태색 — 배경용 밝은 색으로 교체
# ═══════════════════════════════════════════
def fix1_dark_status_colors(sqm_root):
    """ui_constants.py — DARK 상태 배경색을 밝고 구별되는 색으로 변경"""
    target = os.path.join(sqm_root, 'gui_app_modular', 'utils', 'ui_constants.py')
    if not os.path.isfile(target):
        print("  ❌ ui_constants.py 없음")
        return False

    with open(target, 'r', encoding='utf-8') as f:
        content = f.read()
    backup(target)

    # --- 상태 배경색 (너무 어두운 → 반투명 밝은 톤) ---
    replacements = [
        # available: 어두운 틸 → 밝은 에메랄드
        ("'available': '#0f766e'", "'available': '#065f46'"),
        # reserved: 어두운 앰버 → 밝은 골드
        ("'reserved':  '#b45309'", "'reserved':  '#92400e'"),
        # picked: 어두운 보라 → 밝은 바이올렛
        ("'picked':    '#7c3aed'", "'picked':    '#5b21b6'"),
        # shipped: 파랑 → 스틸블루 (파란색과 차별화)
        ("'shipped':   '#1d4ed8'", "'shipped':   '#1e3a5f'"),
    ]

    changed = 0
    for old, new in replacements:
        if old in content:
            content = content.replace(old, new)
            changed += 1

    # --- 상태 배경색을 밝게 수정했으니 foreground도 명시적 밝은색으로 ---
    # configure_tags()에서 fg를 각 상태별로 다르게
    old_configure_tags = """    @classmethod
    def configure_tags(cls, tree, is_dark: bool = False):
        \"\"\"트리뷰 상태 태그 설정 (v3.8.4: 상태별 색상 + v5.6.9: 다크 테마 행 텍스트 밝은색)\"\"\"
        p = cls.DARK if is_dark else cls.LIGHT
        fg = '#f0f0f0' if is_dark else '#1a1a1a'
        for status in ['available', 'picked', 'reserved', 'shipped']:
            tree.tag_configure(status, background=p[status], foreground=fg)"""

    new_configure_tags = """    @classmethod
    def configure_tags(cls, tree, is_dark: bool = False):
        \"\"\"트리뷰 상태 태그 설정 (v6.3.2-colorful: 상태별 고유 전경색)\"\"\"
        p = cls.DARK if is_dark else cls.LIGHT
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
                               foreground=status_fg.get(status, '#f0f0f0' if is_dark else '#1a1a1a'))"""

    if old_configure_tags in content:
        content = content.replace(old_configure_tags, new_configure_tags)
        changed += 1
        print(f"  ✅ configure_tags() 상태별 고유색 적용")
    else:
        print(f"  ⚠️ configure_tags() 패턴 불일치 (수동 확인 필요)")

    # --- 스크롤바 반전 수정 ---
    old_scroll = "trough = '#f2f2f2' if is_dark else '#111111'"
    new_scroll = "trough = '#111111' if is_dark else '#f2f2f2'  # v6.3.2-fix: 반전 수정"
    if old_scroll in content:
        content = content.replace(old_scroll, new_scroll)
        changed += 1
        print(f"  ✅ 스크롤바 trough 반전 수정")

    old_thumb = "thumb = '#111111' if is_dark else '#f2f2f2'"
    new_thumb = "thumb = '#f2f2f2' if is_dark else '#111111'  # v6.3.2-fix: 반전 수정"
    if old_thumb in content:
        content = content.replace(old_thumb, new_thumb)
        changed += 1
        print(f"  ✅ 스크롤바 thumb 반전 수정")

    old_active = "active = '#000000' if is_dark else '#ffffff'"
    new_active = "active = '#ffffff' if is_dark else '#000000'  # v6.3.2-fix: 반전 수정"
    if old_active in content:
        content = content.replace(old_active, new_active)
        changed += 1

    with open(target, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"  ✅ ui_constants.py — {changed}건 수정")
    return changed > 0


# ═══════════════════════════════════════════
# FIX #2: 툴바 하드코딩 블루 → 테마 반응형
# ═══════════════════════════════════════════
def fix2_toolbar_colors(sqm_root):
    """toolbar_mixin.py — _load_toolbar_colors를 테마 반응형으로 변경"""
    target = os.path.join(sqm_root, 'gui_app_modular', 'mixins', 'toolbar_mixin.py')
    if not os.path.isfile(target):
        print("  ❌ toolbar_mixin.py 없음")
        return False

    with open(target, 'r', encoding='utf-8') as f:
        content = f.read()
    backup(target)

    old_load = """    def _load_toolbar_colors(self) -> None:
        \"\"\"컬러풀 고정 팔레트 (테마와 무관하게 유지).\"\"\"
        self._tb_bg = '#0f172a'          # 진한 네이비
        self._tb_sep = '#334155'         # 구분선
        self._tb_fg_normal = '#cbd5e1'   # 비활성 텍스트
        self._tb_fg_active = '#ffffff'   # 활성 텍스트
        self._tb_fg_hover = '#93c5fd'    # 호버 텍스트
        self._tb_hover_bg = '#1e293b'    # 호버 배경
        self._tb_underline_color = '#3b82f6'  # 강조 파랑"""

    new_load = """    def _load_toolbar_colors(self) -> None:
        \"\"\"v6.3.2-colorful: 다크/라이트 반응형 컬러풀 팔레트.\"\"\"
        is_dark = ThemeColors.is_dark_theme(getattr(self, 'current_theme', 'darkly'))
        if is_dark:
            self._tb_bg = '#1a1a2e'          # 딥 다크 퍼플 (네이비 탈피)
            self._tb_sep = '#3d3d5c'         # 보라 구분선
            self._tb_fg_normal = '#c0c0d0'   # 밝은 라벤더 그레이
            self._tb_fg_active = '#ffffff'   # 활성 텍스트
            self._tb_fg_hover = '#e0b0ff'    # 호버: 밝은 보라 (파랑 탈피!)
            self._tb_hover_bg = '#2a2a4a'    # 호버 배경
            self._tb_underline_color = '#a78bfa'  # 밝은 바이올렛 강조
        else:
            self._tb_bg = '#1f2937'          # 다크 그레이
            self._tb_sep = '#4b5563'         # 구분선
            self._tb_fg_normal = '#d1d5db'   # 밝은 그레이
            self._tb_fg_active = '#ffffff'   # 활성 텍스트
            self._tb_fg_hover = '#fbbf24'    # 호버: 골드! (파랑 탈피)
            self._tb_hover_bg = '#374151'    # 호버 배경
            self._tb_underline_color = '#f59e0b'  # 앰버 강조"""

    if old_load in content:
        content = content.replace(old_load, new_load)
        print(f"  ✅ _load_toolbar_colors() 테마 반응형으로 변경")
    else:
        print(f"  ⚠️ _load_toolbar_colors() 패턴 불일치")

    # --- 드롭다운 메뉴 색상도 테마 반응형으로 ---
    old_menu = """        menu_bg = '#0b1220'
        menu_fg = '#e2e8f0'
        menu_abg = '#1d4ed8'
        menu_afg = '#ffffff'
        menu_dis = '#64748b'"""

    new_menu = """        # v6.3.2-colorful: 메뉴 색상 테마 반응형
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

    if old_menu in content:
        content = content.replace(old_menu, new_menu)
        print(f"  ✅ _create_menu() 드롭다운 색상 테마 반응형")
    else:
        print(f"  ⚠️ _create_menu() 패턴 불일치")

    # --- 탭 밑줄 색상도 탭별로 다르게 (이미 tab_colors는 있지만 기본 underline은 파랑 고정) ---

    with open(target, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"  ✅ toolbar_mixin.py 패치 완료")
    return True


# ═══════════════════════════════════════════
# FIX #3: table_styler.py DARK 헤더색 블루 → 다크 톤
# ═══════════════════════════════════════════
def fix3_table_styler(sqm_root):
    """table_styler.py — DARK 헤더 배경 블루 → 중립 다크"""
    target = os.path.join(sqm_root, 'gui_app_modular', 'utils', 'table_styler.py')
    if not os.path.isfile(target):
        print("  ❌ table_styler.py 없음")
        return False

    with open(target, 'r', encoding='utf-8') as f:
        content = f.read()
    backup(target)

    # LIGHT 헤더는 파란색인데 DARK도 유사하면 다 파란색으로 보임
    # LIGHT: 'header_bg': '#1976d2' → 이건 괜찮음 (라이트모드에서 눈에 띔)
    # DARK: 'header_bg': '#333333' → 너무 무채색, 약간 컬러 가미

    # DARK 헤더 약간 보라 기조 추가
    old_dark_header = "'header_bg': '#333333',"
    new_dark_header = "'header_bg': '#2d2b55',  # v6.3.2: 다크 퍼플 헤더"
    if old_dark_header in content:
        content = content.replace(old_dark_header, new_dark_header)
        print(f"  ✅ DARK 헤더 색상 변경")

    with open(target, 'w', encoding='utf-8') as f:
        f.write(content)

    return True


# ═══════════════════════════════════════════
# FIX #4: global_tree_style.py DARK 교대행 — 파랑 기조 탈피
# ═══════════════════════════════════════════
def fix4_global_tree_style(sqm_root):
    """global_tree_style.py — DARK 교대행 배경색 중립화"""
    target = os.path.join(sqm_root, 'fixes', 'global_tree_style.py')
    if not os.path.isfile(target):
        print("  ⚠️ global_tree_style.py 없음 (건너뜀)")
        return True

    with open(target, 'r', encoding='utf-8') as f:
        content = f.read()
    backup(target)

    # 교대행이 파랑 기조 → 중립 다크로
    old_dark_block = """    if is_dark:
        bg_color = '#2b2b2b'
        fg_color = '#e0e0e0'
        field_bg = '#2b2b2b'
        odd_bg = '#333333'
        even_bg = '#2b2b2b'"""

    new_dark_block = """    if is_dark:
        bg_color = '#1e1e2e'       # v6.3.2: 약간 보라 기조 (파랑 탈피)
        fg_color = '#e0e0e0'
        field_bg = '#1e1e2e'
        odd_bg = '#282840'         # v6.3.2: 약간 보라 기조
        even_bg = '#1e1e2e'"""

    if old_dark_block in content:
        content = content.replace(old_dark_block, new_dark_block)
        print(f"  ✅ global_tree_style DARK 교대행 색상 수정")

    with open(target, 'w', encoding='utf-8') as f:
        f.write(content)

    return True


def main():
    print()
    print("=" * 60)
    print("  🎨 SQM v6.3.2 — Colorful UI Fix Patch")
    print(f"  실행: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()

    sqm_root = find_sqm_root()
    if not sqm_root:
        print("  ❌ SQM 프로젝트를 찾을 수 없습니다.")
        input("\n  Enter 키를 누르면 종료...")
        return

    print(f"  📂 SQM 루트: {sqm_root}")
    print()

    print("── [1/4] DARK 상태색 + 스크롤바 반전 수정 (ui_constants.py) ──")
    fix1_dark_status_colors(sqm_root)
    print()

    print("── [2/4] 툴바 블루 하드코딩 → 테마 반응형 (toolbar_mixin.py) ──")
    fix2_toolbar_colors(sqm_root)
    print()

    print("── [3/4] 테이블 헤더 색상 (table_styler.py) ──")
    fix3_table_styler(sqm_root)
    print()

    print("── [4/4] 전역 트리 교대행 색상 (global_tree_style.py) ──")
    fix4_global_tree_style(sqm_root)
    print()

    print("=" * 60)
    print("  ✅ Colorful UI Fix 완료!")
    print()
    print("  수정 요약:")
    print("   🔵→🟢 DARK 상태색: 어두운 블루 계열 → 에메랄드/골드/바이올렛/스틸블루")
    print("   🔵→🟣 툴바: 네이비 고정 → 다크 퍼플 기조 (테마 반응형)")
    print("   🔵→🟡 드롭다운 메뉴: 블루 고정 → 보라/앰버 활성색")
    print("   🔄   스크롤바: 다크/라이트 반전 버그 수정")
    print("   🎨   테이블 헤더·교대행: 중립 다크 퍼플 기조")
    print()
    print("  SQM 앱을 재시작하면 적용됩니다.")
    print("=" * 60)

    input("\n  Enter 키를 누르면 종료...")


if __name__ == '__main__':
    main()
