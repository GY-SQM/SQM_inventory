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
        
        # 다이얼로그 생성
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("📍 톤백 위치 업로드 미리보기")
        self.dialog.geometry("900x600")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self._create_ui()
        
        # 화면 중앙 배치
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (900 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (600 // 2)
        self.dialog.geometry(f"+{x}+{y}")
    
    def _create_ui(self):
        """UI 생성"""
        # ========================================
        # 상단: 요약 정보
        # ========================================
        summary_frame = tk.Frame(self.dialog, bg='#f0f0f0', pady=10)
        summary_frame.pack(fill=tk.X, padx=10, pady=(10, 5))
        
        total = self.result['total']
        success = self.result['success_count']
        fail = self.result['fail_count']
        
        # 통계
        stats_text = f"📊 총 {total}개 | ✅ 성공 {success}개 | ❌ 실패 {fail}개"
        tk.Label(
            summary_frame,
            text=stats_text,
            font=('맑은 고딕', 12, 'bold'),
            bg='#f0f0f0',
            fg='#2c3e50'
        ).pack()
        
        # 경고 메시지
        if fail > 0:
            tk.Label(
                summary_frame,
                text=f"⚠️ {fail}개 톤백의 UID를 찾을 수 없습니다",
                font=('맑은 고딕', 10),
                bg='#f0f0f0',
                fg='#e74c3c'
            ).pack()
        
        # ========================================
        # 중앙: 탭 (매칭 성공 / 실패)
        # ========================================
        tab_frame = ttk.Notebook(self.dialog)
        tab_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # 탭 1: 매칭 성공
        matched_tab = tk.Frame(tab_frame)
        tab_frame.add(matched_tab, text=f"✅ 매칭 성공 ({success})")
        self._create_matched_table(matched_tab)
        
        # 탭 2: 매칭 실패
        if fail > 0:
            failed_tab = tk.Frame(tab_frame)
            tab_frame.add(failed_tab, text=f"❌ 매칭 실패 ({fail})")
            self._create_failed_table(failed_tab)
        
        # ========================================
        # 하단: 버튼
        # ========================================
        button_frame = tk.Frame(self.dialog, bg='white', pady=10)
        button_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        # 확인 버튼
        if success > 0:
            confirm_btn = tk.Button(
                button_frame,
                text=f"✅ 업로드 ({success}개)",
                font=('맑은 고딕', 11, 'bold'),
                bg='#27ae60',
                fg='white',
                padx=20,
                pady=10,
                command=self._on_confirm_click
            )
            confirm_btn.pack(side=tk.RIGHT, padx=10)
        
        # 취소 버튼
        cancel_btn = tk.Button(
            button_frame,
            text="❌ 취소",
            font=('맑은 고딕', 11),
            bg='#95a5a6',
            fg='white',
            padx=20,
            pady=10,
            command=self._on_cancel_click
        )
        cancel_btn.pack(side=tk.RIGHT, padx=5)
    
    def _create_matched_table(self, parent):
        """매칭 성공 테이블"""
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
        
        # 태그 색상
        tree.tag_configure('new', background='#e8f8f5')
        tree.tag_configure('changed', background='#fef5e7')
        tree.tag_configure('same', background='#f8f9fa')
        
        self.matched_tree = tree
    
    def _create_failed_table(self, parent):
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
        tree.configure(yscrollcommand=v_scroll.set)
        
        # 배치
        tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        v_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 데이터 입력
        for item in self.result['not_found']:
            values = (
                item['row_num'],
                item['uid'],
                item['location'],
                item['reason']
            )
            tree.insert('', 'end', values=values, tags=('error',))
        
        # 태그 색상
        tree.tag_configure('error', background='#fadbd8', foreground='#e74c3c')
        
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
