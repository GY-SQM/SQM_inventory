# -*- coding: utf-8 -*-
"""
★ HOTFIX: ThemeColors.DARK_THEMES AttributeError 수정
=====================================================
날짜: 2026-03-04
증상: AttributeError: type object 'ThemeColors' has no attribute 'DARK_THEMES'
원인: is_dark_theme()이 cls.DARK_THEMES 참조하나 해당 속성 미존재
수정: 인라인 튜플로 교체

사용법: SQM 폴더에 복사 후 더블클릭 (또는 python HOTFIX_DARK_THEMES.py)
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


def main():
    print()
    print("=" * 55)
    print("  🔧 HOTFIX: DARK_THEMES AttributeError")
    print("=" * 55)

    sqm_root = find_sqm_root()
    if not sqm_root:
        print("  ❌ SQM 폴더를 찾을 수 없습니다.")
        input("\n  Enter...")
        return

    target = os.path.join(sqm_root, 'gui_app_modular', 'utils', 'ui_constants.py')
    if not os.path.isfile(target):
        print(f"  ❌ {target} 없음")
        input("\n  Enter...")
        return

    with open(target, 'r', encoding='utf-8') as f:
        content = f.read()

    # 백업
    bak = target + f'.bak_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
    shutil.copy2(target, bak)
    print(f"  📋 백업: {os.path.basename(bak)}")

    old = "return theme_name.lower() in cls.DARK_THEMES"
    new = "return theme_name.lower() in ('darkly', 'cyborg', 'superhero', 'solar', 'vapor')"

    if old in content:
        content = content.replace(old, new)
        with open(target, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"  ✅ 수정 완료!")
    else:
        print(f"  ⚠️ 패턴 미발견 (이미 수정되었거나 다른 형태)")

    print()
    print("  SQM을 다시 실행하세요.")
    print("=" * 55)
    input("\n  Enter...")


if __name__ == '__main__':
    main()
