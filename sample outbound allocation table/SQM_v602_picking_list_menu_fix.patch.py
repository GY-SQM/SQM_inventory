# -*- coding: utf-8 -*-
"""
SQM v6.0.2 패치 — 출고 메뉴 Picking List 누락 수정
====================================================
파일: gui_app_modular/mixins/toolbar_mixin.py
날짜: 2026-02-22

[문제]
  toolbar_mixin.py의 _build_outbound_menu()에
  Picking List 업로드 메뉴 항목이 빠져 있어서
  📤 출고 ▼ 메뉴에 Picking List가 표시되지 않음.

[수정]
  _build_outbound_menu()에 '📋 Picking List 업로드 (PDF)' 항목 추가

[적용]
  SQM 루트 폴더에서:  python SQM_v602_picking_list_menu_fix.patch.py
"""
import os, shutil, sys

TARGET = os.path.join('gui_app_modular', 'mixins', 'toolbar_mixin.py')

OLD = """    def _build_outbound_menu(self) -> 'tk.Menu':
        m = self._create_menu()
        self._add_menu_items(m, [
            ('📋 Allocation 입력 (파일 / 붙여넣기)', lambda: self._safe_call('_on_allocation_input_unified')),
            ('📤 빠른 출고 (붙여넣기)', lambda: self._safe_call('_on_quick_outbound_paste')),
        ])
        return m"""

NEW = """    def _build_outbound_menu(self) -> 'tk.Menu':
        m = self._create_menu()
        self._add_menu_items(m, [
            ('📋 Allocation 입력 (파일 / 붙여넣기)', lambda: self._safe_call('_on_allocation_input_unified')),
            ('📋 Picking List 업로드 (PDF)', lambda: self._safe_call('_on_picking_list_upload')),
            None,
            ('📤 빠른 출고 (붙여넣기)', lambda: self._safe_call('_on_quick_outbound_paste')),
        ])
        return m"""

def apply_patch():
    if not os.path.exists(TARGET):
        print(f"❌ 파일 없음: {TARGET}"); sys.exit(1)
    shutil.copy2(TARGET, TARGET + '.bak_picking_fix')
    with open(TARGET, 'r', encoding='utf-8') as f:
        content = f.read()
    if OLD in content:
        content = content.replace(OLD, NEW, 1)
        with open(TARGET, 'w', encoding='utf-8') as f:
            f.write(content)
        print("✅ 출고 메뉴에 Picking List 업로드 추가 완료!")
        print("   앱 재시작 후 📤 출고 ▼ 메뉴에서 확인하세요.")
    else:
        print("⚠️ 원본 패턴 불일치 (이미 적용되었거나 변경됨)")

if __name__ == '__main__':
    apply_patch()
