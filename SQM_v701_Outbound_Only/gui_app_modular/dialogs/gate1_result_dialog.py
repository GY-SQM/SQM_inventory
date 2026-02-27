# -*- coding: utf-8 -*-
"""
SQM v6.12.1 — Gate-1 교차검증 결과 다이얼로그
===============================================
피킹리스트 vs Allocation Plan LOT/수량 비교 결과를
테이블 형태로 시각화합니다.
"""

import logging
import tkinter as tk
from tkinter import ttk
from tkinter.constants import BOTH, LEFT, RIGHT, X, Y, END, VERTICAL

logger = logging.getLogger(__name__)

try:
    from gui_app_modular.utils.gui_bootstrap import (
        DialogSize, center_dialog, apply_modal_window_options
    )
    from gui_app_modular.utils.custom_messagebox import CustomMessageBox
except ImportError:
    DialogSize = None
    center_dialog = None
    apply_modal_window_options = None
    CustomMessageBox = None

try:
    from gui_app_modular.utils.theme_colors import ThemeColors
except ImportError:
    ThemeColors = None


class Gate1ResultDialog:
    """
    Gate-1 교차검증 결과를 테이블 팝업으로 표시.

    Args:
        parent: 부모 윈도우
        gate1_result: gate1_verify_picking() 반환값
        picking_no: 피킹리스트 번호
        on_proceed: '진행' 버튼 클릭 시 콜백 (None이면 버튼 미표시)
    """

    def __init__(self, parent, gate1_result: dict, picking_no: str = '',
                 on_proceed=None, current_theme: str = 'flatly'):
        self.parent = parent
        self.result = gate1_result
        self.picking_no = picking_no
        self.on_proceed = on_proceed
        self.proceed_confirmed = False

        # 테마
        is_dark = ThemeColors.is_dark_theme(current_theme) if ThemeColors else False
        bg = ThemeColors.get('bg_card', is_dark) if ThemeColors else '#FFFFFF'
        fg = ThemeColors.get('text_primary', is_dark) if ThemeColors else '#000000'
        header_bg = ThemeColors.get('statusbar_bg', is_dark) if ThemeColors else '#2C3E50'
        header_fg = '#FFFFFF' if is_dark or header_bg.startswith('#2') or header_bg.startswith('#3') else '#FFFFFF'

        self.popup = tk.Toplevel(parent)
        self.popup.title(f"Gate-1 교차검증 — {picking_no}")
        if DialogSize:
            self.popup.geometry(DialogSize.get_geometry(parent, 'large'))
        else:
            self.popup.geometry("900x600")
        if apply_modal_window_options:
            apply_modal_window_options(self.popup)
        self.popup.transient(parent)
        self.popup.grab_set()
        if center_dialog:
            center_dialog(self.popup, parent)
        self.popup.configure(bg=bg)

        passed = gate1_result.get('passed', False)
        qty_mismatches = gate1_result.get('qty_mismatches', [])

        # ═══ 헤더 ═══
        header = tk.Frame(self.popup, bg=header_bg, padx=15, pady=10)
        header.pack(fill=X)

        picking_lots = gate1_result.get('picking_lots', set())
        reserved_lots = gate1_result.get('reserved_lots', set())
        matched = gate1_result.get('matched_lots', set())
        only_picking = gate1_result.get('only_in_picking', set())

        if passed and not qty_mismatches:
            icon = "✅"
            title = "Gate-1 완전 통과"
            title_color = '#28A745'
        elif passed and qty_mismatches:
            icon = "⚠️"
            title = "Gate-1 조건부 통과 (수량 불일치 있음)"
            title_color = '#FFC107'
        else:
            icon = "🚫"
            title = "Gate-1 실패"
            title_color = '#DC3545'

        tk.Label(header, text=f"{icon} {title}",
                 font=('맑은 고딕', 14, 'bold'), bg=header_bg, fg=header_fg).pack(anchor='w')
        tk.Label(header,
                 text=f"피킹 LOT: {len(picking_lots)}개 | RESERVED: {len(reserved_lots)}개 | "
                      f"매칭: {len(matched)}개 | 미매칭: {len(only_picking)}개",
                 font=('맑은 고딕', 10), bg=header_bg, fg=header_fg).pack(anchor='w', pady=(3, 0))

        # ═══ 본문 Notebook ═══
        nb = ttk.Notebook(self.popup)
        nb.pack(fill=BOTH, expand=True, padx=10, pady=5)

        # --- TAB 1: LOT 비교 테이블 ---
        tab_lot = tk.Frame(nb, bg=bg)
        nb.add(tab_lot, text=f"  📊 LOT 비교 ({len(matched)}건)  ")

        cols = ('no', 'lot_no', 'pick_kg', 'res_kg', 'diff_kg', 'status')
        headers = ('#', 'LOT NO', '피킹 요청(kg)', 'RESERVED(kg)', '차이(kg)', '판정')
        widths = (40, 120, 110, 110, 100, 100)

        tree = ttk.Treeview(tab_lot, columns=cols, show='headings', height=15)
        for cid, txt, w in zip(cols, headers, widths):
            tree.heading(cid, text=txt)
            anchor = 'center' if cid in ('no', 'status') else ('e' if 'kg' in cid else 'center')
            tree.column(cid, width=w, anchor=anchor)

        sb = ttk.Scrollbar(tab_lot, orient=VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side=LEFT, fill=BOTH, expand=True)
        sb.pack(side=RIGHT, fill=Y)

        lot_details = gate1_result.get('lot_details', [])
        for idx, d in enumerate(lot_details, 1):
            diff = d['picking_kg'] - d['reserved_kg']
            if d['kg_match']:
                status = '✅ 일치'
                tag = 'ok'
            else:
                status = '⚠️ 불일치'
                tag = 'mismatch'

            tree.insert('', END, values=(
                idx,
                d['lot_no'],
                f"{d['picking_kg']:,.0f}",
                f"{d['reserved_kg']:,.0f}",
                f"{diff:+,.0f}",
                status,
            ), tags=(tag,))

        tree.tag_configure('ok', foreground='#28A745')
        tree.tag_configure('mismatch', foreground='#DC3545', background='#FFF3CD')

        # 미매칭 LOT 추가
        for lot in sorted(only_picking):
            tree.insert('', END, values=(
                '', lot, '-', '(미등록)', '-', '❌ RESERVED 없음'
            ), tags=('missing',))
        tree.tag_configure('missing', foreground='#DC3545', background='#F8D7DA')

        # --- TAB 2: 텍스트 리포트 ---
        tab_report = tk.Frame(nb, bg=bg)
        nb.add(tab_report, text="  📋 상세 리포트  ")

        txt_widget = tk.Text(tab_report, wrap='word', font=('Consolas', 10),
                             bg=bg, fg=fg, padx=10, pady=10)
        txt_widget.insert('1.0', gate1_result.get('error_report', '(리포트 없음)'))
        txt_widget.configure(state='disabled')
        txt_widget.pack(fill=BOTH, expand=True)

        # ═══ 하단 버튼 ═══
        btn_bar = tk.Frame(self.popup, bg=bg, pady=8)
        btn_bar.pack(fill=X, padx=10)

        # 요약 라벨
        ok_count = sum(1 for d in lot_details if d['kg_match'])
        summary_text = f"수량 검증: {ok_count}/{len(lot_details)} 일치"
        if qty_mismatches:
            summary_text += f" | ⚠️ {len(qty_mismatches)}건 불일치"
        tk.Label(btn_bar, text=summary_text, font=('맑은 고딕', 9),
                 bg=bg, fg=fg).pack(side=LEFT)

        ttk.Button(btn_bar, text="닫기", command=self.popup.destroy).pack(side=RIGHT, padx=5)

        if passed and on_proceed:
            def _on_proceed():
                self.proceed_confirmed = True
                self.popup.destroy()
                on_proceed()

            btn_text = "⚡ 진행 (판매화물 결정)" if not qty_mismatches else "⚠️ 경고 무시하고 진행"
            ttk.Button(btn_bar, text=btn_text, command=_on_proceed).pack(side=RIGHT, padx=5)

        self.popup.wait_window()
