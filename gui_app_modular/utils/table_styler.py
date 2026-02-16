# -*- coding: utf-8 -*-
"""
SQM 재고관리 시스템 - 테이블 스타일 유틸리티
============================================

v4.2.2: 그리드 라인, 줄무늬, 가독성 개선

작성자: Ruby
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)


class TableStyler:
    """테이블 스타일 관리 클래스"""
    
    # 색상 테마
    COLORS = {
        # 그리드 라인
        'grid_line': '#e0e0e0',
        'grid_line_strong': '#bdbdbd',
        
        # 줄무늬 (Striped rows)
        'row_even': '#ffffff',
        'row_odd': '#f5f5f5',
        'row_even_selected': '#e3f2fd',
        'row_odd_selected': '#bbdefb',
        
        # 헤더
        'header_bg': '#1976d2',
        'header_fg': '#ffffff',
        
        # 테두리
        'border': '#9e9e9e',
    }
    
    # 행 높이
    ROW_HEIGHT = {
        'compact': 24,
        'normal': 28,
        'comfortable': 32,
    }
    
    @classmethod
    def apply_grid_lines(
        cls,
        treeview: ttk.Treeview,
        show_vertical: bool = True,
        show_horizontal: bool = True
    ) -> None:
        """
        Treeview에 그리드 라인 스타일 적용
        
        Args:
            treeview: 대상 Treeview 위젯
            show_vertical: 세로 그리드 라인 표시
            show_horizontal: 가로 그리드 라인 표시
        """
        style = ttk.Style()
        
        # 스타일 이름 생성 (위젯별 고유)
        style_name = f"Grid.{id(treeview)}.Treeview"
        
        # 기본 스타일 복사
        style.configure(
            style_name,
            background=cls.COLORS['row_even'],
            foreground='#000000',
            fieldbackground=cls.COLORS['row_even'],
            borderwidth=1,
            relief='solid'
        )
        
        # 줄무늬 적용
        style.map(
            style_name,
            background=[
                ('selected', cls.COLORS['row_even_selected']),
                ('!selected', cls.COLORS['row_odd'])
            ]
        )
        
        # Treeview에 스타일 적용
        treeview.configure(style=style_name)
        
        # 그리드 라인 효과를 위한 설정
        if show_vertical or show_horizontal:
            # 헤더 스타일
            style.configure(
                f"{style_name}.Heading",
                background=cls.COLORS['header_bg'],
                foreground=cls.COLORS['header_fg'],
                relief='raised',
                borderwidth=1
            )
    
    @classmethod
    def apply_striped_rows(
        cls,
        treeview: ttk.Treeview,
        tag_even: str = 'evenrow',
        tag_odd: str = 'oddrow'
    ) -> None:
        """
        Treeview에 줄무늬(striped rows) 적용
        
        Args:
            treeview: 대상 Treeview
            tag_even: 짝수 행 태그
            tag_odd: 홀수 행 태그
        """
        # 태그 색상 정의
        treeview.tag_configure(tag_even, background=cls.COLORS['row_even'])
        treeview.tag_configure(tag_odd, background=cls.COLORS['row_odd'])
        
        # 기존 아이템에 태그 적용
        for idx, item in enumerate(treeview.get_children()):
            tag = tag_even if idx % 2 == 0 else tag_odd
            treeview.item(item, tags=(tag,))
    
    @classmethod
    def set_row_height(
        cls,
        treeview: ttk.Treeview,
        mode: str = 'normal'
    ) -> None:
        """
        행 높이 설정
        
        Args:
            treeview: 대상 Treeview
            mode: 'compact', 'normal', 'comfortable'
        """
        height = cls.ROW_HEIGHT.get(mode, cls.ROW_HEIGHT['normal'])
        
        style = ttk.Style()
        style_name = f"RowHeight.{id(treeview)}.Treeview"
        
        style.configure(
            style_name,
            rowheight=height
        )
        
        treeview.configure(style=style_name)
    
    @classmethod
    def toggle_column(
        cls,
        treeview: ttk.Treeview,
        column_id: str,
        visible: bool
    ) -> None:
        """
        컬럼 표시/숨김 토글
        
        Args:
            treeview: 대상 Treeview
            column_id: 컬럼 ID
            visible: True=표시, False=숨김
        """
        # NoneType 체크
        if treeview is None:
            logger.warning(f"toggle_column: treeview가 None입니다 (column_id={column_id})")
            return
        
        if visible:
            # 컬럼 너비 복원 (기본값 또는 저장된 값)
            width = getattr(treeview, f'_{column_id}_width', 100)
            treeview.column(column_id, width=width, minwidth=50)
        else:
            # 현재 너비 저장
            current_width = treeview.column(column_id, 'width')
            setattr(treeview, f'_{column_id}_width', current_width)
            # 너비 0으로 설정 (숨김)
            treeview.column(column_id, width=0, minwidth=0)
    
    @classmethod
    def create_style_toolbar(
        cls,
        parent: tk.Widget,
        treeview: ttk.Treeview,
        toggleable_columns: Optional[List[tuple]] = None
    ) -> tk.Frame:
        """
        스타일 조정 툴바 생성
        
        Args:
            parent: 부모 위젯
            treeview: 대상 Treeview
            toggleable_columns: [(컬럼ID, 표시명), ...]
            
        Returns:
            툴바 프레임
        """
        toolbar = tk.Frame(parent, bg='#f0f0f0', pady=5)
        
        # 왼쪽: 컬럼 토글
        if toggleable_columns:
            tk.Label(
                toolbar,
                text="표시 컬럼:",
                bg='#f0f0f0',
                font=('맑은 고딕', 9)
            ).pack(side=tk.LEFT, padx=(10, 5))
            
            for col_id, col_name in toggleable_columns:
                var = tk.BooleanVar(value=True)
                
                def make_toggle(cid, v):
                    def toggle():
                        cls.toggle_column(treeview, cid, v.get())
                    return toggle
                
                cb = tk.Checkbutton(
                    toolbar,
                    text=col_name,
                    variable=var,
                    command=make_toggle(col_id, var),
                    bg='#f0f0f0',
                    font=('맑은 고딕', 9)
                )
                cb.pack(side=tk.LEFT, padx=2)
        
        # 구분선
        ttk.Separator(toolbar, orient='vertical').pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # 오른쪽: 표시 모드
        tk.Label(
            toolbar,
            text="표시 모드:",
            bg='#f0f0f0',
            font=('맑은 고딕', 9)
        ).pack(side=tk.LEFT, padx=5)
        
        mode_var = tk.StringVar(value='normal')
        
        for mode, label in [('compact', '컴팩트'), ('normal', '보통'), ('comfortable', '넓게')]:
            rb = tk.Radiobutton(
                toolbar,
                text=label,
                variable=mode_var,
                value=mode,
                command=lambda m=mode: cls.set_row_height(treeview, m),
                bg='#f0f0f0',
                font=('맑은 고딕', 9)
            )
            rb.pack(side=tk.LEFT, padx=2)
        
        return toolbar
    
    @classmethod
    def refresh_striped_rows(
        cls,
        treeview: ttk.Treeview,
        tag_even: str = 'evenrow',
        tag_odd: str = 'oddrow'
    ) -> None:
        """
        줄무늬 새로고침 (데이터 변경 후 호출)
        
        Args:
            treeview: 대상 Treeview
            tag_even: 짝수 행 태그
            tag_odd: 홀수 행 태그
        """
        for idx, item in enumerate(treeview.get_children()):
            tag = tag_even if idx % 2 == 0 else tag_odd
            treeview.item(item, tags=(tag,))


# 간편 함수
def apply_table_style(
    treeview: ttk.Treeview,
    grid_lines: bool = True,
    striped_rows: bool = True,
    row_height: str = 'normal'
) -> None:
    """
    테이블에 스타일 일괄 적용 (간편 함수)
    
    Args:
        treeview: 대상 Treeview
        grid_lines: 그리드 라인 표시
        striped_rows: 줄무늬 표시
        row_height: 행 높이 ('compact', 'normal', 'comfortable')
    """
    if grid_lines:
        TableStyler.apply_grid_lines(treeview)
    
    if striped_rows:
        TableStyler.apply_striped_rows(treeview)
    
    TableStyler.set_row_height(treeview, row_height)


# 테스트
if __name__ == '__main__':
    root = tk.Tk()
    root.title("Table Style Test")
    root.geometry("800x400")
    
    # 테스트 Treeview
    columns = ('col1', 'col2', 'col3', 'col4')
    tree = ttk.Treeview(root, columns=columns, show='headings', height=15)
    
    for col in columns:
        tree.heading(col, text=col.upper())
        tree.column(col, width=150)
    
    # 테스트 데이터
    for i in range(20):
        tree.insert('', 'end', values=(f'Data {i}-1', f'Data {i}-2', f'Data {i}-3', f'Data {i}-4'))
    
    tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    # 스타일 적용
    apply_table_style(tree, grid_lines=True, striped_rows=True, row_height='normal')
    
    # 툴바 생성
    toolbar = TableStyler.create_style_toolbar(
        root,
        tree,
        toggleable_columns=[('col2', 'COL2'), ('col3', 'COL3')]
    )
    toolbar.pack(side=tk.BOTTOM, fill=tk.X)
    
    root.mainloop()
