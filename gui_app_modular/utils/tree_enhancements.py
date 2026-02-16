# -*- coding: utf-8 -*-
"""
SQM v5.5.3 — Treeview 향상: 줄무늬, 필터, 합계
=================================================
v5.5.3 patch_03: tk→ttk 전환으로 테마 자동 대응

재고 리스트 / 톤백 리스트에 공통 적용:
- 줄무늬 행 (striped rows)
- 헤더 필터 Combobox
- 하단 합계 바
"""

import calendar
import logging
from datetime import date, datetime
from typing import List, Tuple, Callable, Optional
from .ui_constants import ThemeColors

logger = logging.getLogger(__name__)


def _parse_date_for_calendar(value: Optional[str]) -> date:
    """기간 입력값(YYYY-MM-DD 등)을 date로. 실패 시 오늘."""
    if not value or not str(value).strip():
        return date.today()
    try:
        s = str(value).strip()
        if len(s) >= 10:
            return datetime.strptime(s[:10], "%Y-%m-%d").date()
        return date.today()
    except Exception:
        return date.today()


def show_date_calendar(parent, initial_value: Optional[str], on_choose: Callable[[str], None]) -> None:
    """
    클릭으로 날짜를 선택하는 캘린더 팝업.
    on_choose(ymd_str) 호출 후 팝업 종료. ymd_str 형식: YYYY-MM-DD.
    """
    import tkinter as tk
    from tkinter import ttk

    d = _parse_date_for_calendar(initial_value)
    year, month = d.year, d.month

    win = tk.Toplevel(parent)
    win.title("날짜 선택")
    win.transient(parent)
    win.grab_set()
    win.resizable(False, False)

    # 상단: 년월 + 이전/다음
    nav = ttk.Frame(win, padding=(8, 6))
    nav.pack(fill=tk.X)

    def _apply():
        for w in body.winfo_children():
            w.destroy()
        # 요일 헤더 (일요일 시작)
        for i, wd in enumerate(["일", "월", "화", "수", "목", "금", "토"]):
            ttk.Label(body, text=wd, font=("맑은 고딕", 9, "bold")).grid(row=0, column=i, padx=2, pady=2)
        # calendar: 일요일이 첫 열이 되도록
        cal = calendar.Calendar(calendar.SUNDAY)
        weeks = cal.monthdayscalendar(year, month)
        for r, week in enumerate(weeks, start=1):
            for c, day in enumerate(week):
                if day == 0:
                    continue
                btn = ttk.Button(
                    body, text=str(day), width=3,
                    command=lambda y=year, m=month, d=day: _on_day(y, m, d)
                )
                btn.grid(row=r, column=c, padx=2, pady=2)

    def _on_day(y: int, m: int, day: int):
        ymd = f"{y:04d}-{m:02d}-{day:02d}"
        try:
            on_choose(ymd)
        except Exception as e:
            logger.debug("날짜 선택 콜백 오류: %s", e)
        win.destroy()

    def _prev():
        nonlocal year, month
        if month == 1:
            year, month = year - 1, 12
        else:
            month -= 1
        _label_var.set(f"{year}년 {month}월")
        _apply()

    def _next():
        nonlocal year, month
        if month == 12:
            year, month = year + 1, 1
        else:
            month += 1
        _label_var.set(f"{year}년 {month}월")
        _apply()

    _label_var = tk.StringVar(value=f"{year}년 {month}월")
    ttk.Button(nav, text="◀", width=3, command=_prev).pack(side=tk.LEFT, padx=2)
    ttk.Label(nav, textvariable=_label_var, font=("맑은 고딕", 10, "bold")).pack(side=tk.LEFT, padx=8)
    ttk.Button(nav, text="▶", width=3, command=_next).pack(side=tk.LEFT, padx=2)

    body = ttk.Frame(win, padding=(8, 4))
    body.pack(fill=tk.BOTH, expand=True)
    _apply()

    win.update_idletasks()
    win.geometry(f"+{parent.winfo_rootx() + 50}+{parent.winfo_rooty() + 80}")
    try:
        win.focus_set()
    except Exception as e:
        logger.debug(f"Suppressed: {e}")


def apply_striped_rows(tree, is_dark: bool = False) -> None:
    """
    Treeview에 줄무늬 행 적용 (홀수/짝수 교대 배경)

    v5.5.3 patch_03: ThemeColors 참조로 테마 자동 대응
    """
    even_bg = ThemeColors.get('bg_card', is_dark)
    odd_bg = ThemeColors.get('bg_secondary', is_dark) if not is_dark else '#2a2a2a'

    tree.tag_configure('even_row', background=even_bg)
    tree.tag_configure('odd_row', background=odd_bg)

    for idx, item_id in enumerate(tree.get_children('')):
        tag = 'even_row' if idx % 2 == 0 else 'odd_row'
        existing_tags = list(tree.item(item_id, 'tags') or ())
        existing_tags = [t for t in existing_tags if t not in ('even_row', 'odd_row')]
        existing_tags.append(tag)
        tree.item(item_id, tags=tuple(existing_tags))


class HeaderFilterBar:
    """
    Treeview 위에 컬럼별 필터 Combobox 바

    v5.5.3 patch_03: ttk 위젯 사용 → 테마 자동 대응
    
    Usage:
        filter_bar = HeaderFilterBar(parent, tree, columns, on_filter_callback)
        filter_bar.pack(fill='x')
    """

    def __init__(self, parent, tree, filter_columns: List[Tuple[str, str, int]],
                 on_filter: Callable, is_dark: bool = False,
                 date_from_var=None, date_to_var=None):
        """
        Args:
            parent: 부모 위젯
            tree: Treeview 위젯
            filter_columns: [(col_id, label, width), ...]
            on_filter: 필터 변경 시 콜백
            is_dark: 하위 호환 (사용하지 않음, ttk가 자동 처리)
            date_from_var: (선택) 기간 시작일 StringVar — 있으면 STATUS와 초기화 사이에 기간 입력 추가
            date_to_var: (선택) 기간 종료일 StringVar
        """
        import tkinter as tk
        from tkinter import ttk

        self.tree = tree
        self.on_filter = on_filter
        self.filter_vars = {}
        self.filter_combos = {}
        self._date_from_var = date_from_var
        self._date_to_var = date_to_var

        # ttk.Frame — 테마 색상 자동 적용
        self.frame = ttk.Frame(parent, padding=(5, 2))

        # "필터:" 라벨 (ttk)
        _lbl_filter = ttk.Label(self.frame, text="🔽 필터:",
                                font=('맑은 고딕', 10, 'bold'))
        _lbl_filter.pack(side='left', padx=(0, 8))
        self._apply_tooltip_safe(_lbl_filter, "컬럼별 조건을 선택하면 목록이 자동으로 필터됩니다. 빈 조건은 적용되지 않습니다.")

        for col_id, label, width in filter_columns:
            _lbl = ttk.Label(self.frame, text=f"{label}:", font=('맑은 고딕', 9))
            _lbl.pack(side='left', padx=(0, 2))
            self._apply_tooltip_safe(_lbl, self._get_column_tooltip(col_id, label))

            var = tk.StringVar(value="전체")
            combo = ttk.Combobox(self.frame, textvariable=var,
                                 values=["전체"], state="readonly",
                                 width=max(width // 10, 8))
            combo.pack(side='left', padx=(0, 8))
            combo.bind('<<ComboboxSelected>>', lambda e: self.on_filter())
            self._apply_tooltip_safe(combo, f"{label} 값으로 목록 필터. '전체'는 조건 없음.")

            self.filter_vars[col_id] = var
            self.filter_combos[col_id] = combo

        # v5.7.5: 기간(날짜 범위) — STATUS와 초기화 사이 한 줄에 배치 + 클릭 시 캘린더
        if date_from_var is not None and date_to_var is not None:
            _lbl_period = ttk.Label(self.frame, text="기간:", font=('맑은 고딕', 9))
            _lbl_period.pack(side='left', padx=(8, 4))
            self._apply_tooltip_safe(_lbl_period, "입력한 기간(시작일~종료일) 안의 데이터만 표시. 비우면 기간 조건 없음. 형식: YYYY-MM-DD")
            _e_from = ttk.Entry(self.frame, textvariable=date_from_var, width=12)
            _e_from.pack(side='left', padx=2)
            self._apply_tooltip_safe(_e_from, "시작일 (YYYY-MM-DD). 클릭하면 캘린더에서 선택. 비우면 제한 없음.")
            _btn_cal_from = ttk.Button(self.frame, text="📅", width=2,
                                       command=lambda: show_date_calendar(
                                           self.frame.winfo_toplevel(),
                                           date_from_var.get(),
                                           lambda ymd: (date_from_var.set(ymd), self.on_filter())))
            _btn_cal_from.pack(side='left', padx=(0, 2))
            self._apply_tooltip_safe(_btn_cal_from, "캘린더에서 시작일 선택")
            ttk.Label(self.frame, text=" ~ ").pack(side='left')
            _e_to = ttk.Entry(self.frame, textvariable=date_to_var, width=12)
            _e_to.pack(side='left', padx=2)
            self._apply_tooltip_safe(_e_to, "종료일 (YYYY-MM-DD). 클릭하면 캘린더에서 선택. 비우면 제한 없음.")
            _btn_cal_to = ttk.Button(self.frame, text="📅", width=2,
                                     command=lambda: show_date_calendar(
                                         self.frame.winfo_toplevel(),
                                         date_to_var.get(),
                                         lambda ymd: (date_to_var.set(ymd), self.on_filter())))
            _btn_cal_to.pack(side='left', padx=(0, 2))
            self._apply_tooltip_safe(_btn_cal_to, "캘린더에서 종료일 선택")
            ttk.Label(self.frame, text=" (YYYY-MM-DD)", font=('맑은 고딕', 9)).pack(side='left', padx=(0, 8))
            # 입력란 클릭 시에도 캘린더 열기
            def _open_cal_from(_e=None):
                show_date_calendar(
                    self.frame.winfo_toplevel(),
                    date_from_var.get(),
                    lambda ymd: (date_from_var.set(ymd), self.on_filter()))
            def _open_cal_to(_e=None):
                show_date_calendar(
                    self.frame.winfo_toplevel(),
                    date_to_var.get(),
                    lambda ymd: (date_to_var.set(ymd), self.on_filter()))
            _e_from.bind('<Button-1>', _open_cal_from)
            _e_to.bind('<Button-1>', _open_cal_to)
            for _w in (_e_from, _e_to):
                _w.bind('<FocusOut>', lambda e: self.on_filter())
                _w.bind('<Return>', lambda e: self.on_filter())

        # 초기화 버튼
        _btn_reset = ttk.Button(self.frame, text="✖ 초기화", width=8,
                                command=self._reset_filters)
        _btn_reset.pack(side='left', padx=5)
        self._apply_tooltip_safe(_btn_reset, "모든 필터(컬럼 조건·기간)를 '전체'/비움으로 되돌리고 목록을 다시 불러옵니다.")

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)

    def _reset_filters(self):
        for var in self.filter_vars.values():
            var.set("전체")
        if getattr(self, '_date_from_var', None) is not None:
            self._date_from_var.set("")
        if getattr(self, '_date_to_var', None) is not None:
            self._date_to_var.set("")
        self.on_filter()

    def _apply_tooltip_safe(self, widget, text: str) -> None:
        """툴팁 적용 (ui_constants.apply_tooltip 있으면 사용, 없으면 무시)"""
        try:
            from .ui_constants import apply_tooltip
            apply_tooltip(widget, text)
        except Exception as e:
            logger.debug(f"Suppressed: {e}")

    def _get_column_tooltip(self, col_id: str, label: str) -> str:
        """컬럼별 툴팁 문구"""
        _tips = {
            'lot_no': 'LOT 번호로 필터. 해당 LOT만 표시.',
            'sap_no': 'SAP 번호로 필터.',
            'bl_no': 'B/L 번호로 필터.',
            'container_no': '컨테이너 번호로 필터.',
            'product': '제품명으로 필터.',
            'status': '전체 / Available(판매 가능) / Sold(출고 완료) 중 선택. 옆 숫자는 해당 개수.',
            'tonbag_status': '전체 / Available / Sold 중 선택. 옆 숫자는 해당 톤백 개수.',
        }
        return _tips.get(col_id, f"{label} 값으로 목록을 제한합니다.")

    def get_filters(self) -> dict:
        """현재 필터 값 → {'col_id': 'value', ...}. '전체'는 제외."""
        result = {}
        for col_id, var in self.filter_vars.items():
            val = var.get()
            if val and val != "전체":
                result[col_id] = val
        return result

    def update_filter_values(self, col_id: str, values: List[str]) -> None:
        """특정 컬럼의 필터 드롭다운 값 업데이트"""
        if col_id in self.filter_combos:
            seen = set()
            str_vals = []
            for v in values:
                if v is None:
                    continue
                v_str = str(v).strip()
                if v_str and v_str not in seen:
                    seen.add(v_str)
                    str_vals.append(v_str)
            all_values = ["전체"] + sorted(str_vals)
            self.filter_combos[col_id]['values'] = all_values


class FooterTotalBar:
    """
    Treeview 하단 합계 바

    v5.5.3 patch_03: ttk 위젯 사용 → 테마 자동 대응.
    숫자 강조는 bold체로 표현 (배경색 대신).
    
    Usage:
        footer = FooterTotalBar(parent)
        footer.pack(fill='x')
        footer.update({'net_kg': 100000, 'balance_kg': 95000, 'rows': 200})
    """

    def __init__(self, parent, is_dark: bool = False):
        """
        Args:
            parent: 부모 위젯
            is_dark: 하위 호환 (사용하지 않음, ttk가 자동 처리)
        """
        from tkinter import ttk

        self.frame = ttk.Frame(parent, padding=(5, 4))
        self._labels = {}

        fields = [
            ('rows', '📊 행수:', '0'),
            ('net_kg', '📦 NET(Kg):', '0'),
            ('balance_kg', '💰 Balance(Kg):', '0'),
        ]

        for key, label_text, default in fields:
            ttk.Label(self.frame, text=label_text,
                      font=('맑은 고딕', 11, 'bold')).pack(side='left', padx=(10, 2))
            lbl = ttk.Label(self.frame, text=default,
                            font=('맑은 고딕', 12, 'bold'))
            lbl.pack(side='left', padx=(0, 15))
            self._labels[key] = lbl

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)

    def update(self, data: dict) -> None:
        """합계 업데이트. data keys: rows, net_kg, balance_kg"""
        for key, lbl in self._labels.items():
            val = data.get(key, 0)
            if isinstance(val, (int, float)):
                lbl.config(text=f"{val:,.0f}")
            else:
                lbl.config(text=str(val))
