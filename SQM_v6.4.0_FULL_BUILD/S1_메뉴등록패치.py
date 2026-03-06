# -*- coding: utf-8 -*-
"""
★ S1 원스톱 출고 — 메뉴 등록 패치 ★
=====================================
사용법: SQM 폴더에 복사 후 더블클릭

자동 처리:
  1. menu_registry.py에 S1 메뉴 항목 추가
  2. outbound_handlers.py에 핸들러 메서드 추가
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


def backup(filepath):
    if os.path.isfile(filepath):
        bak = filepath + f'.bak_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        shutil.copy2(filepath, bak)
        return os.path.basename(bak)
    return None


def patch_menu_registry(sqm_root):
    """menu_registry.py에 S1 메뉴 항목 추가"""
    target = os.path.join(sqm_root, 'gui_app_modular', 'menu_registry.py')
    if not os.path.isfile(target):
        print(f"  ❌ menu_registry.py 없음")
        return False

    with open(target, 'r', encoding='utf-8') as f:
        content = f.read()

    if '_on_s1_onestop_outbound' in content:
        print("  ℹ️ menu_registry.py 이미 등록됨, 건너뜀")
        return True

    bak = backup(target)
    if bak:
        print(f"  📋 백업: {bak}")

    # "빠른 출고" 다음에 S1 추가
    old = '("📤 빠른 출고 (붙여넣기)", "_on_quick_outbound_paste")'
    new = old + ',\n    ("🚀 S1 원스톱 출고", "_on_s1_onestop_outbound")'

    if old in content:
        content = content.replace(old, new)
        with open(target, 'w', encoding='utf-8') as f:
            f.write(content)
        print("  ✅ menu_registry.py에 S1 메뉴 추가 완료")
        return True

    # 대안: 빠른 출고 변형 찾기
    for variant in [
        '("📤 빠른 출고 (붙여넣기)", "_on_quick_outbound_paste"),',
        '("빠른 출고 (붙여넣기)", "_on_quick_outbound_paste")',
    ]:
        if variant in content:
            content = content.replace(
                variant,
                variant + '\n    ("🚀 S1 원스톱 출고", "_on_s1_onestop_outbound"),'
            )
            with open(target, 'w', encoding='utf-8') as f:
                f.write(content)
            print("  ✅ menu_registry.py에 S1 메뉴 추가 완료 (대안)")
            return True

    # 최후 수단: 판매 배정 탭 전에 삽입
    for marker in [
        '"_on_go_allocation_tab"',
        '판매 배정 탭으로 이동',
    ]:
        if marker in content:
            idx = content.find(marker)
            # 해당 줄의 시작 찾기
            line_start = content.rfind('\n', 0, idx) + 1
            insert_text = '    ("🚀 S1 원스톱 출고", "_on_s1_onestop_outbound"),\n'
            content = content[:line_start] + insert_text + content[line_start:]
            with open(target, 'w', encoding='utf-8') as f:
                f.write(content)
            print("  ✅ menu_registry.py에 S1 메뉴 추가 완료 (판매배정 전)")
            return True

    print("  ⚠️ 삽입 위치를 찾지 못함 — 수동으로 추가 필요")
    return False


def patch_outbound_handlers(sqm_root):
    """outbound_handlers.py에 핸들러 메서드 추가"""
    target = os.path.join(sqm_root, 'gui_app_modular', 'handlers', 'outbound_handlers.py')
    if not os.path.isfile(target):
        print(f"  ❌ outbound_handlers.py 없음")
        return False

    with open(target, 'r', encoding='utf-8') as f:
        content = f.read()

    if '_on_s1_onestop_outbound' in content:
        print("  ℹ️ outbound_handlers.py 이미 등록됨, 건너뜀")
        return True

    bak = backup(target)
    if bak:
        print(f"  📋 백업: {bak}")

    handler_code = '''
    def _on_s1_onestop_outbound(self) -> None:
        """S1 원스톱 출고: 4단계 워크플로우 (v6.3.1)
        입력(붙여넣기) → 톤백선택(LOT일괄/랜덤/수동) → 스캔검증(하드스톱) → 확정
        """
        try:
            from ..dialogs.onestop_outbound import S1OneStopOutboundDialog
            dlg = S1OneStopOutboundDialog(self, self.engine)
            dlg.show()
        except (ImportError, AttributeError) as e:
            logger.error(f"S1 원스톱 출고 오류: {e}", exc_info=True)
            from ..utils.ui_constants import CustomMessageBox
            CustomMessageBox.showerror(self.root, "오류", f"S1 원스톱 출고 열기 실패:\\n{e}")
'''

    # 파일 끝에 추가 (클래스 내부)
    # 마지막 메서드 찾기
    last_def = content.rfind('\n    def ')
    if last_def == -1:
        print("  ⚠️ 클래스 구조를 찾지 못함")
        return False

    # 해당 메서드의 끝 (다음 def 또는 파일 끝) 찾기
    next_def = content.find('\n    def ', last_def + 10)
    if next_def == -1:
        # 파일 끝에 추가
        content = content.rstrip() + '\n' + handler_code + '\n'
    else:
        content = content[:next_def] + '\n' + handler_code + content[next_def:]

    with open(target, 'w', encoding='utf-8') as f:
        f.write(content)
    print("  ✅ outbound_handlers.py에 핸들러 추가 완료")
    return True


def main():
    print()
    print("=" * 60)
    print("  🚀 S1 원스톱 출고 — 메뉴 등록 패치")
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

    print("── [1/2] menu_registry.py ──")
    patch_menu_registry(sqm_root)
    print()

    print("── [2/2] outbound_handlers.py ──")
    patch_outbound_handlers(sqm_root)
    print()

    print("=" * 60)
    print("  ✅ 메뉴 등록 완료!")
    print()
    print("  출고 ▼ 메뉴에 '🚀 S1 원스톱 출고' 추가됨")
    print("  SQM 앱을 재시작하면 적용됩니다.")
    print("=" * 60)

    input("\n  Enter 키를 누르면 종료...")


if __name__ == '__main__':
    main()
