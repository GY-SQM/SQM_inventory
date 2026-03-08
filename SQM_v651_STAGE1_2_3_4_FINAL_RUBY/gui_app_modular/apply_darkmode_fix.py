# -*- coding: utf-8 -*-
"""
★ SQM 다크모드 글자 안 보임 — 근본 수정 ★
==========================================
사용법: SQM 폴더에 복사 후 더블클릭

근본 원인: table_styler.py의 줄무늬 태그에
  background만 설정하고 foreground를 안 넣음
  → 다크 배경 + 검정 글자 = 안 보임

수정 6건:
  1. apply_striped_rows: foreground 추가
  2. apply_grid_lines: !selected foreground 추가
  3. update_grid_style_for_theme: !selected foreground 추가
  4. refresh_striped_rows: 테마 감지 + foreground 동기화
  5. apply_table_style: is_dark 파라미터 전달
  6. update_grid_style_for_theme: 줄무늬 태그 fg 갱신
"""
import os
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


def main():
    print()
    print("=" * 60)
    print("  🎨 SQM 다크모드 글자 안 보임 — 근본 수정")
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

    target = os.path.join(sqm_root, 'gui_app_modular', 'utils', 'table_styler.py')
    new_file = os.path.join(SCRIPT_DIR, 'table_styler.py')

    if not os.path.isfile(target):
        print(f"  ❌ table_styler.py 없음: {target}")
        input("\n  Enter 키를 누르면 종료...")
        return

    if not os.path.isfile(new_file):
        print(f"  ❌ 패치 파일 없음: {new_file}")
        input("\n  Enter 키를 누르면 종료...")
        return

    # 백업
    bak = target + f'.bak_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
    shutil.copy2(target, bak)
    old_lines = sum(1 for _ in open(target, encoding='utf-8'))
    print(f"  📋 백업: {os.path.basename(bak)} ({old_lines}행)")

    # 교체
    shutil.copy2(new_file, target)
    new_lines = sum(1 for _ in open(target, encoding='utf-8'))
    print(f"  ✅ 교체: table_styler.py ({new_lines}행)")

    print()
    print("=" * 60)
    print("  ✅ 수정 완료!")
    print()
    print("  수정 내용 (6건):")
    print("   1. 줄무늬 태그에 foreground 필수 설정")
    print("   2. Grid 스타일 !selected foreground 추가")
    print("   3. 테마 갱신 시 !selected foreground 추가")
    print("   4. 줄무늬 새로고침 시 다크모드 자동 감지")
    print("   5. apply_table_style에 is_dark 전달")
    print("   6. 테마 전환 시 줄무늬 태그 fg도 갱신")
    print()
    print("  SQM 앱을 재시작하면 적용됩니다.")
    print("=" * 60)

    input("\n  Enter 키를 누르면 종료...")


if __name__ == '__main__':
    main()
