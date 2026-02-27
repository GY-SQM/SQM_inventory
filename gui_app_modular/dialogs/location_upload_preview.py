# -*- coding: utf-8 -*-
"""
SQM 재고관리 시스템 - 톤백 위치 업로드 미리보기 다이얼로그
=========================================================

v4.2.3: Excel 업로드 → 미리보기 → 확인 → 업데이트

작성자: Ruby
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, List, Callable, Optional
import logging

from ..utils.ui_constants import ThemeColors, DialogSize, center_dialog, apply_modal_window_options

logger = logging.getLogger(__name__)


class LocationUploadPreviewDialog:
    """위치 업로드 미리보기 다이얼로그"""
    
    def __init__(
        self,
        parent,
        validation_result: Dict,
        on_confirm: Callable,
        on_cancel: Optional[Callable] = None
    ):
        """
        Args:
            parent: 부모 위젯
            validation_result: validate_and_match() 결과
            on_confirm: 확인 버튼 콜백
            on_cancel: 취소 버튼 콜백
        """
        self.parent = parent
        self.result = validation_result
        self.on_confirm = on_confirm
        self.on_cancel = on_cancel
        
        # 다이얼로그 생성 (Phase4: DialogSize)
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("📍 톤백 위치 업로드 미리보기")
        self.dialog.geometry(DialogSize.get_geometry(parent, 'large'))
        apply_modal_window_options(self.dialog)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        center_dialog(self.dialog, parent)
        # Esc·창 닫기(X)로도 닫히도록 (모달이 자동으로 사라지지 않아 불편함 해소)
        self.dialog.bind('<Escape>', lambda e: self._on_cancel_click())
        self.dialog.protocol('WM_DELETE_WINDOW', self._on_cancel_click)
        
        self._create_ui()
    
    def _create_ui(self):
        """UI 생성 (v5.8.7 Phase2: ThemeColors)"""
        _lum_dark = ThemeColors.is_dark_theme(getattr(self.parent, 'current_theme', 'flatly'))
        _bg_sec = ThemeColors.get('bg_secondary', _lum_dark)
        _fg_pri = ThemeColors.get('text_primary', _lum_dark)
        _danger = ThemeColors.get('danger', _lum_dark)
        _btn_fg = ThemeColors.get('badge_text', _lum_dark)
        _success = ThemeColors.get('success', _lum_dark)
        _neutral = ThemeColors.get('btn_neutral', _lum_dark)
        _bg_card = ThemeColors.get('bg_card', _lum_dark)

        # 상단: 요약 정보
        summary_frame = tk.Frame(self.dialog, bg=_bg_sec, pady=10)
        summary_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        total = self.result['total']
        success = self.result['success_count']
        fail = self.result['fail_count']
        
        stats_text = f"📊 총 {total}개 | ✅ 성공 {success}개 | ❌ 실패 {fail}개"
        tk.Label(summary_frame, text=stats_text, font=('맑은 고딕', 12, 'bold'),
                 bg=_bg_sec, fg=_fg_pri).pack()
        if fail > 0:
            first_reason = ""
            if self.result.get('not_found'):
                first_reason = (self.result['not_found'][0].get('reason') or "").strip()
            msg = first_reason if first_reason else f"LOT·톤백번호로 재고 리스트 매칭 실패 {fail}건"
            tk.Label(summary_frame, text=f"⚠️ {msg}",
                     font=('맑은 고딕', 10), bg=_bg_sec, fg=_danger, wraplength=500).pack()
        
        tab_frame = ttk.Notebook(self.dialog)
        tab_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        matched_tab = tk.Frame(tab_frame)
        tab_frame.add(matched_tab, text=f"✅ 매칭 성공 ({success})")
        self._create_matched_table(matched_tab, _lum_dark)
        
        if fail > 0:
            failed_tab = tk.Frame(tab_frame)
            tab_frame.add(failed_tab, text=f"❌ 매칭 실패 ({fail})")
            self._create_failed_table(failed_tab, _lum_dark)
        
        button_frame = tk.Frame(self.dialog, bg=_bg_card, pady=10)
        button_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        if success > 0:
            confirm_btn = tk.Button(
                button_frame, text=f"✅ 업로드 ({success}개)",
                font=('맑은 고딕', 11, 'bold'), bg=_success, fg=_btn_fg,
                padx=20, pady=10, command=self._on_confirm_click
            )
            confirm_btn.pack(side=tk.RIGHT, padx=10)
        
        cancel_btn = tk.Button(
            button_frame, text="❌ 취소", font=('맑은 고딕', 11),
            bg=_neutral, fg=_btn_fg, padx=20, pady=10, command=self._on_cancel_click
        )
        cancel_btn.pack(side=tk.RIGHT, padx=5)
    
    def _create_matched_table(self, parent, is_dark=False):
        """매칭 성공 테이블 (v5.8.7 Phase2: ThemeColors)"""
        # 컬럼 정의
        columns = [
            ('row_num', 'Excel 행', 60),
            ('uid', 'UID', 150),
            ('lot_no', 'LOT NO', 120),
            ('product', 'PRODUCT', 180),
            ('current_location', '현재 위치', 100),
            ('location', '새 위치', 100),
            ('status', '상태', 80),
        ]
        
        col_ids = [c[0] for c in columns]
        
        # Treeview
        tree = ttk.Treeview(
            parent,
            columns=col_ids,
            show='headings',
            height=15
        )
        
        # 헤더 설정
        for col_id, label, width in columns:
            tree.heading(col_id, text=label)
            tree.column(col_id, width=width, anchor='center')
        
        # 스크롤바
        v_scroll = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=tree.yview)
        h_scroll = ttk.Scrollbar(parent, orient=tk.HORIZONTAL, command=tree.xview)
        tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        # 배치
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 데이터 입력
        for item in self.result['matched']:
            # 상태 결정
            if item['location_changed']:
                if item['current_location']:
                    status = '🔄 변경'
                    tag = 'changed'
                else:
                    status = '🆕 신규'
                    tag = 'new'
            else:
                status = '✔️ 동일'
                tag = 'same'
            
            values = (
                item['row_num'],
                item['uid'],
                item['lot_no'],
                item['product'][:20] if item['product'] else '',
                item['current_location'] or '-',
                item['location'],
                status
            )
            
            tree.insert('', 'end', values=values, tags=(tag,))
        
        # 배경만 넣으면 테마에 따라 글자색이 배경과 비슷해져 안 보일 수 있음 → foreground 명시
        _fg = ThemeColors.get('text_primary', is_dark)
        tree.tag_configure('new', background=ThemeColors.get('available', is_dark), foreground=_fg)
        tree.tag_configure('changed', background=ThemeColors.get('reserved', is_dark), foreground=_fg)
        tree.tag_configure('same', background=ThemeColors.get('bg_secondary', is_dark), foreground=_fg)
        
        self.matched_tree = tree
    
    def _create_failed_table(self, parent, is_dark=False):
        """매칭 실패 테이블"""
        # 컬럼 정의
        columns = [
            ('row_num', 'Excel 행', 80),
            ('uid', 'UID', 200),
            ('location', '위치', 120),
            ('reason', '실패 원인', 300),
        ]
        
        col_ids = [c[0] for c in columns]
        
        # Treeview
        tree = ttk.Treeview(
            parent,
            columns=col_ids,
            show='headings',
            height=15
        )
        
        # 헤더 설정
        for col_id, label, width in columns:
            tree.heading(col_id, text=label)
            tree.column(col_id, width=width, anchor='center' if col_id != 'reason' else 'w')
        
        # 스크롤바
        v_scroll = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=tree.yview)
        h_scroll = ttk.Scrollbar(parent, orient=tk.HORIZONTAL, command=tree.xview)
        tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        # 배치
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        h_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 데이터 입력
        for item in self.result['not_found']:
            values = (
                item['row_num'],
                item['uid'],
                item['location'],
                item['reason']
            )
            tree.insert('', 'end', values=values, tags=('error',))
        
        # 실패 행도 글자 가독성: 배경(picked)과 대비되는 text_primary
        _err_fg = ThemeColors.get('text_primary', is_dark)
        tree.tag_configure('error', background=ThemeColors.get('picked', is_dark), foreground=_err_fg)
        
        self.failed_tree = tree
    
    def _on_confirm_click(self):
        """확인 버튼 클릭"""
        if self.on_confirm:
            self.on_confirm(self.result['matched'])
        self.dialog.destroy()
    
    def _on_cancel_click(self):
        """취소 버튼 클릭"""
        if self.on_cancel:
            self.on_cancel()
        self.dialog.destroy()


# 테스트
if __name__ == '__main__':
    # 테스트 데이터
    test_result = {
        'matched': [
            {
                'uid': '1125072340-01',
                'location': 'A-1-3',
                'row_num': 2,
                'tonbag_id': 1,
                'lot_no': '1125072340',
                'sub_lt': 1,
                'product': 'LITHIUM CARBONATE',
                'current_location': 'A-1-2',
                'location_changed': True
            },
            {
                'uid': '1125072340-02',
                'location': 'A-1-4',
                'row_num': 3,
                'tonbag_id': 2,
                'lot_no': '1125072340',
                'sub_lt': 2,
                'product': 'LITHIUM CARBONATE',
                'current_location': '',
                'location_changed': True
            },
        ],
        'not_found': [
            {
                'uid': '9999999999-99',
                'location': 'B-2-1',
                'row_num': 4,
                'reason': 'UID를 찾을 수 없습니다'
            }
        ],
        'total': 3,
        'success_count': 2,
        'fail_count': 1
    }
    
    root = tk.Tk()
    root.withdraw()
    
    def on_confirm(matched_data):
        logger.debug("✅ 업로드 확인!")
        for item in matched_data:
            logger.debug(f"  {item['uid']} → {item['location']}")
    
    dialog = LocationUploadPreviewDialog(
        root,
        test_result,
        on_confirm=on_confirm
    )
    
    root.mainloop()
