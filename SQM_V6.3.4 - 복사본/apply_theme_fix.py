# -*- coding: utf-8 -*-
"""
★★★ SQM 테마 가시성 근본 수정 — 자동 패치 ★★★
==================================================
사용법: SQM 폴더에 복사 후 더블클릭

자동 처리:
  1. theme_aware.py 유틸리티 추가 (신규)
  2. theme_refresh.py에 ttk.Label 처리 패치
  3. 기존 파일 자동 백업 (.bak)
"""
import os
import sys
import re
import shutil
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def find_sqm_root():
    check = SCRIPT_DIR
    if os.path.isdir(os.path.join(check, 'gui_app_modular')):
        return check
    for _ in range(3):
        check = os.path.dirname(check)
        if os.path.isdir(os.path.join(check, 'gui_app_modular')):
            return check
    return None


def backup(filepath):
    if os.path.isfile(filepath):
        bak = filepath + f'.bak_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        shutil.copy2(filepath, bak)
        return bak
    return None


def patch_1_copy_theme_aware(sqm_root):
    """theme_aware.py → gui_app_modular/utils/ 에 복사"""
    src = os.path.join(SCRIPT_DIR, 'theme_aware.py')
    dst = os.path.join(sqm_root, 'gui_app_modular', 'utils', 'theme_aware.py')

    if not os.path.isfile(src):
        print(f"  ❌ theme_aware.py 없음: {src}")
        return False

    shutil.copy2(src, dst)
    lines = sum(1 for _ in open(dst, encoding='utf-8'))
    print(f"  ✅ theme_aware.py 복사 완료 ({lines}행)")
    return True


def patch_2_theme_refresh(sqm_root):
    """theme_refresh.py에 ttk.Label 처리 추가"""
    target = os.path.join(sqm_root, 'gui_app_modular', 'utils', 'theme_refresh.py')

    if not os.path.isfile(target):
        print(f"  ❌ theme_refresh.py 없음")
        return False

    with open(target, 'r', encoding='utf-8') as f:
        content = f.read()

    # 이미 패치됨?
    if '_refresh_ttk_label' in content:
        print("  ℹ️ theme_refresh.py 이미 패치됨, 건너뜀")
        return True

    bak = backup(target)
    if bak:
        print(f"  📋 백업: {os.path.basename(bak)}")

    # ── 패치 A: _refresh_ttk_label 함수 추가 ──
    new_func = '''

def _refresh_ttk_label(widget, colors: dict) -> None:
    """v6.3.1: ttk.Label hardcoded foreground → 테마 안전색 변환"""
    is_dark = colors['is_dark']
    theme_fg = colors['fg']

    DARK_SAFE = {
        '#dc2626': '#f87171', 'red': '#f87171', 'darkred': '#f87171',
        '#d97706': '#fbbf24', 'orange': '#fbbf24',
        '#059669': '#34d399', 'green': '#34d399', 'darkgreen': '#34d399',
        '#6366f1': '#818cf8', 'purple': '#a78bfa',
        '#ea580c': '#fb923c',
        '#2563eb': '#60a5fa', 'blue': '#60a5fa', 'darkblue': '#93c5fd',
        'gray': '#9ca3af', 'grey': '#9ca3af',
        '#000000': '#e5e7eb', 'black': '#e5e7eb',
    }
    LIGHT_SAFE = {
        '#f87171': '#dc2626', '#fbbf24': '#d97706', '#34d399': '#059669',
        '#818cf8': '#6366f1', '#fb923c': '#ea580c', '#60a5fa': '#2563eb',
        '#9ca3af': '#6b7280', '#e5e7eb': '#1f2937',
        'white': '#1f2937', '#ffffff': '#1f2937',
    }

    try:
        current_fg = str(widget.cget('foreground')).strip().lower()
        if not current_fg or current_fg == theme_fg.strip().lower():
            return

        if is_dark:
            safe = DARK_SAFE.get(current_fg)
            if safe:
                widget.configure(foreground=safe)
        else:
            safe = LIGHT_SAFE.get(current_fg)
            if safe:
                widget.configure(foreground=safe)
    except (tk.TclError, RuntimeError, ValueError) as e:
        logger.debug(f"[_refresh_ttk_label] Suppressed: {e}")

'''

    # _refresh_native_widget 함수 끝 찾기
    marker = 'def refresh_all_widgets_for_theme'
    idx = content.find(marker)
    if idx == -1:
        print("  ❌ refresh_all_widgets_for_theme 함수를 찾을 수 없음")
        return False

    content = content[:idx] + new_func + '\n' + content[idx:]

    # ── 패치 B: ttk.Label 분기 추가 ──
    # 기존:  elif isinstance(w, tk.Label) and not isinstance(w, ttk.Label):
    # 뒤에:  elif isinstance(w, ttk.Label): ...
    old_pattern = "elif isinstance(w, tk.Label) and not isinstance(w, ttk.Label):\n                _refresh_native_widget(w, colors)\n                stats['native_widgets'] += 1"
    new_pattern = old_pattern + """
            # ★ v6.3.1: ttk.Label hardcoded foreground 수정
            elif isinstance(w, ttk.Label):
                _refresh_ttk_label(w, colors)
                stats['native_widgets'] += 1"""

    if old_pattern in content:
        content = content.replace(old_pattern, new_pattern)
        print("  ✅ ttk.Label 분기 추가 완료")
    else:
        print("  ⚠️ ttk.Label 분기 삽입 위치 못 찾음 (수동 확인 필요)")

    with open(target, 'w', encoding='utf-8') as f:
        f.write(content)

    lines = sum(1 for _ in open(target, encoding='utf-8'))
    print(f"  ✅ theme_refresh.py 패치 완료 ({lines}행)")
    return True


def patch_3_toplevel_hook(sqm_root):
    """theme_mixin.py에 Toplevel 자동 테마 적용 후크 추가"""
    target = os.path.join(sqm_root, 'gui_app_modular', 'mixins', 'theme_mixin.py')

    if not os.path.isfile(target):
        print("  ⚠️ theme_mixin.py 없음, 건너뜀")
        return True

    with open(target, 'r', encoding='utf-8') as f:
        content = f.read()

    if 'theme_aware' in content:
        print("  ℹ️ theme_mixin.py 이미 패치됨, 건너뜀")
        return True

    bak = backup(target)
    if bak:
        print(f"  📋 백업: {os.path.basename(bak)}")

    # _change_theme() 끝의 self._log 앞에 ThemeAware 전파 추가
    old_log = "            self._log(f\"Theme changed: {theme_name}\")"
    new_log = """            # ★ v6.3.1: 열린 Toplevel 다이얼로그에도 테마 전파
            try:
                from ..utils.theme_aware import ThemeAware
                for w in self.root.winfo_children():
                    if isinstance(w, tk.Toplevel):
                        ThemeAware.apply_to_toplevel_now(w)
            except Exception as _te:
                logger.debug(f"Toplevel 테마 전파 무시: {_te}")

            self._log(f"Theme changed: {theme_name}")"""

    if old_log in content:
        content = content.replace(old_log, new_log)
        # tk import 확인
        if 'import tkinter as tk' not in content:
            content = content.replace(
                "import logging",
                "import logging\nimport tkinter as tk"
            )
        print("  ✅ Toplevel 테마 전파 후크 추가 완료")
    else:
        print("  ⚠️ _log 위치 못 찾음 (수동 확인 필요)")

    with open(target, 'w', encoding='utf-8') as f:
        f.write(content)

    return True


def main():
    print()
    print("=" * 60)
    print("  🎨 SQM 테마 가시성 근본 수정")
    print(f"  실행: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    print()

    sqm_root = find_sqm_root()
    if not sqm_root:
        print("  ❌ SQM 프로젝트를 찾을 수 없습니다.")
        print("     이 파일을 SQM 폴더 안에 넣고 실행해주세요.")
        input("\n  Enter 키를 누르면 종료...")
        return

    print(f"  📂 SQM 루트: {sqm_root}")
    print()

    # 패치 1: theme_aware.py 추가
    print("── [1/3] theme_aware.py 유틸리티 추가 ──")
    patch_1_copy_theme_aware(sqm_root)
    print()

    # 패치 2: theme_refresh.py 수정
    print("── [2/3] theme_refresh.py ttk.Label 패치 ──")
    patch_2_theme_refresh(sqm_root)
    print()

    # 패치 3: theme_mixin.py Toplevel 후크
    print("── [3/3] theme_mixin.py Toplevel 전파 후크 ──")
    patch_3_toplevel_hook(sqm_root)
    print()

    print("=" * 60)
    print("  ✅ 테마 가시성 근본 수정 완료!")
    print()
    print("  수정 내용:")
    print("   • theme_aware.py: 테마 안전 색상 API (신규)")
    print("   • theme_refresh.py: ttk.Label 하드코딩 색상 자동 변환")
    print("   • theme_mixin.py: 테마 변경 시 Toplevel에도 자동 전파")
    print()
    print("  영향 범위:")
    print("   • 다크 모드 전환 시 글자 안 보이는 문제 해결")
    print("   • 라이트 모드 전환 시 흰 글자 문제 해결")
    print("   • 모든 다이얼로그(Toplevel) 테마 자동 적용")
    print()
    print("  SQM 앱을 재시작하면 적용됩니다.")
    print("=" * 60)

    input("\n  Enter 키를 누르면 종료...")


if __name__ == '__main__':
    main()
