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
from collections.abc import Callable
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple

from .ui_constants import ThemeColors, apply_modal_window_options

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
    except (ValueError, TypeError) as e:
        logger.debug(f"Suppressed: {e}")
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
    apply_modal_window_options(win)

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
                 date_from_var=None, date_to_var=None,
                 container_suffix_var=None, on_container_suffix_toggle=None):
        """
        Args:
            parent: 부모 위젯
            tree: Treeview 위젯
            filter_columns: [(col_id, label, width), ...]
            on_filter: 필터 변경 시 콜백
            is_dark: 하위 호환 (사용하지 않음, ttk가 자동 처리)
            date_from_var: (선택) 기간 시작일 StringVar — 있으면 STATUS와 초기화 사이에 기간 입력 추가
            date_to_var: (선택) 기간 종료일 StringVar
            container_suffix_var: (선택) 컨테이너 접미사 표시 BooleanVar
            on_container_suffix_toggle: (선택) 접미사 토글 콜백
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

        # 컨테이너 접미사(-1,-2) 표시 체크박스
        if container_suffix_var is not None:
            _cb_suffix = ttk.Checkbutton(
                self.frame, text="📦 컨테이너 구분(-1,-2)",
                variable=container_suffix_var,
                command=on_container_suffix_toggle,
            )
            _cb_suffix.pack(side='left', padx=(10, 0))
            self._apply_tooltip_safe(_cb_suffix, "CONTAINER 열의 -1, -2 접미사 표시/숨김")

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
            'status': '전체 / 판매가능 / 판매배정 / 판매화물 결정 / 출고 중 선택. 옆 숫자는 해당 개수.',
            'tonbag_status': '전체 / 판매가능 / 판매배정 / 판매화물 결정 / 출고 중 선택. 옆 숫자는 해당 톤백 개수.',
            'avail_bags': 'Avail = 현재 판매가능 톤백 개수. 출고 시 감소, 반품 시 증가.',
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


class HeaderSortFilterRow:
    """
    차트(트리) 헤더 열마다 정렬(오름/내림) + 리스트 목록 상자(콤보)를 넣은 한 줄.
    상단 필터 메뉴 없이, 헤더에 통합.

    - 각 열: 컬럼명 + 정렬 표시(▲/▼) + 콤보(전체/값 목록)
    - 헤더 클릭 시 정렬, 콤보 선택 시 필터 적용
    - get_filters(), update_filter_values(), filter_vars, filter_combos — HeaderFilterBar와 호환
    """

    def __init__(self, parent, tree, columns: List[Tuple[str, str, int]],
                 on_filter: Callable, on_sort: Callable[[str], None],
                 is_dark: bool = False,
                 date_from_var=None, date_to_var=None,
                 container_suffix_var=None, on_container_suffix_toggle=None,
                 show_opt_row: bool = True):
        """
        Args:
            parent: 부모 위젯
            tree: Treeview (컬럼 폭 참조용)
            columns: [(col_id, label, width), ...] — 필터/정렬할 컬럼들
            on_filter: 필터 변경 시 콜백
            on_sort: 헤더 클릭 시 콜백 on_sort(col_id)
            date_from_var, date_to_var, container_suffix_var, on_container_suffix_toggle: 선택
            show_opt_row: False면 기간/초기화 행 미표시 (헤더 열+목록상자만)
        """
        import tkinter as tk
        from tkinter import ttk

        self.tree = tree
        self.on_filter = on_filter
        self.on_sort = on_sort
        self.filter_vars = {}
        self.filter_combos = {}
        self._sort_labels = {}
        self._sort_column = None
        self._sort_reverse = False
        self._date_from_var = date_from_var
        self._date_to_var = date_to_var

        self.frame = ttk.Frame(parent, padding=(2, 2))
        self._cells_frame = ttk.Frame(self.frame)
        self._cells_frame.pack(fill=tk.X)

        for col_id, label, width in columns:
            cell = ttk.Frame(self._cells_frame)
            cell.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 2))

            # 컬럼명 + 클릭 시 정렬
            lbl = ttk.Label(cell, text=label, font=('맑은 고딕', 9, 'bold'))
            lbl.pack(side=tk.LEFT, padx=(2, 0))
            lbl.bind('<Button-1>', lambda e, c=col_id: self._on_header_click(c))
            try:
                from .ui_constants import apply_tooltip
                apply_tooltip(lbl, "클릭: 오름차순/내림차순 정렬")
            except Exception:
                pass

            sort_lbl = ttk.Label(cell, text="", font=('맑은 고딕', 9), width=2)
            sort_lbl.pack(side=tk.LEFT)
            sort_lbl.bind('<Button-1>', lambda e, c=col_id: self._on_header_click(c))
            self._sort_labels[col_id] = sort_lbl

            var = tk.StringVar(value="전체")
            combo = ttk.Combobox(
                cell, textvariable=var, values=["전체"], state="readonly",
                width=max(width // 6, 14)
            )
            combo.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(2, 0))
            combo.bind('<<ComboboxSelected>>', lambda e: self.on_filter())
            self.filter_vars[col_id] = var
            self.filter_combos[col_id] = combo
            try:
                from .ui_constants import apply_tooltip
                apply_tooltip(combo, f"목록에서 선택해 {label} 필터")
            except Exception:
                pass

        # 하위호환: lot_combo, sap_combo 등 별칭
        self.lot_combo = self.filter_combos.get('lot_no')
        self.sap_combo = self.filter_combos.get('sap_no')
        self.bl_combo = self.filter_combos.get('bl_no')
        self.container_combo = self.filter_combos.get('container_no')
        self.product_combo = self.filter_combos.get('product')

        # 기간·컨테이너 구분 (선택) — show_opt_row=False면 미표시
        self._opt_frame = ttk.Frame(self.frame)
        if show_opt_row:
            self._opt_frame.pack(fill=tk.X, pady=(4, 0))
        if show_opt_row and date_from_var is not None and date_to_var is not None:
            ttk.Label(self._opt_frame, text="기간:").pack(side=tk.LEFT, padx=(0, 2))
            ttk.Entry(self._opt_frame, textvariable=date_from_var, width=11).pack(side=tk.LEFT, padx=2)
            _btn_cal_from = ttk.Button(self._opt_frame, text="📅", width=2,
                command=lambda: show_date_calendar(
                    self.frame.winfo_toplevel(), date_from_var.get(),
                    lambda ymd: (date_from_var.set(ymd), self.on_filter())))
            _btn_cal_from.pack(side=tk.LEFT, padx=(0, 4))
            ttk.Label(self._opt_frame, text=" ~ ").pack(side=tk.LEFT)
            ttk.Entry(self._opt_frame, textvariable=date_to_var, width=11).pack(side=tk.LEFT, padx=2)
            _btn_cal_to = ttk.Button(self._opt_frame, text="📅", width=2,
                command=lambda: show_date_calendar(
                    self.frame.winfo_toplevel(), date_to_var.get(),
                    lambda ymd: (date_to_var.set(ymd), self.on_filter())))
            _btn_cal_to.pack(side=tk.LEFT, padx=(0, 8))
        if show_opt_row and container_suffix_var is not None and on_container_suffix_toggle is not None:
            ttk.Checkbutton(
                self._opt_frame, text="📦 컨테이너 구분(-1,-2)",
                variable=container_suffix_var, command=on_container_suffix_toggle
            ).pack(side=tk.LEFT, padx=(0, 4))
        if show_opt_row:
            ttk.Button(self._opt_frame, text="✖ 초기화", width=8, command=self._reset_filters).pack(side=tk.LEFT, padx=4)

    def _on_header_click(self, col_id: str) -> None:
        prev = self._sort_column
        self._sort_column = col_id
        self._sort_reverse = not self._sort_reverse if prev == col_id else False
        self._update_sort_indicators()
        if self.on_sort:
            self.on_sort(col_id)

    def _update_sort_indicators(self) -> None:
        for cid, lbl in self._sort_labels.items():
            if cid == self._sort_column:
                lbl.config(text="▼" if self._sort_reverse else "▲")
            else:
                lbl.config(text="")

    def set_sort(self, col_id: str, reverse: bool) -> None:
        """외부에서 정렬 상태 동기화 시 호출."""
        self._sort_column = col_id
        self._sort_reverse = bool(reverse)
        self._update_sort_indicators()

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)

    def pack_forget(self):
        self.frame.pack_forget()

    def _reset_filters(self) -> None:
        for var in self.filter_vars.values():
            var.set("전체")
        if getattr(self, '_date_from_var', None) is not None:
            self._date_from_var.set("")
        if getattr(self, '_date_to_var', None) is not None:
            self._date_to_var.set("")
        self.on_filter()

    def get_filters(self) -> dict:
        result = {}
        for col_id, var in self.filter_vars.items():
            val = var.get()
            if val and val != "전체":
                result[col_id] = val
        return result

    def update_filter_values(self, col_id: str, values: List[str]) -> None:
        if col_id not in self.filter_combos:
            return
        seen = set()
        str_vals = []
        for v in values:
            if v is None:
                continue
            v_str = str(v).strip()
            if v_str and v_str not in seen:
                seen.add(v_str)
                str_vals.append(v_str)
        self.filter_combos[col_id]['values'] = ["전체"] + sorted(str_vals)


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


def _safe_float(val) -> float:
    """문자열에서 숫자만 추출해 float으로. 콤마·공백 제거."""
    if val is None:
        return 0.0
    s = str(val).strip().replace(",", "").replace(" ", "")
    if not s:
        return 0.0
    try:
        return float(s)
    except (ValueError, TypeError):
        return 0.0


class TreeviewTotalFooter:
    """
    Treeview 하단 총합 바 — 합계 가능한 숫자 컬럼만 하단에 표시.
    문자열 등 합계 불가 컬럼은 제외.

    Usage:
        footer = TreeviewTotalFooter(parent, tree, summable_column_ids=['current_weight','net_weight',...])
        footer.pack(fill='x')
        # 데이터 로드 후
        footer.update_totals()
    """

    def __init__(self, parent, tree, summable_column_ids: List[str],
                 column_display_names: Optional[dict] = None,
                 column_formats: Optional[Dict[str, str]] = None):
        """
        Args:
            parent: 부모 위젯 (tree와 형제로 pack될 frame)
            tree: ttk.Treeview
            summable_column_ids: 합계할 컬럼 id 목록 (tree의 columns와 동일한 id)
            column_display_names: {col_id: "표시명"} — 없으면 tree.heading(col_id) 사용
            column_formats: {col_id: "포맷"} — 합계 표시 포맷 (예: {'qty_mt': ',.3f'}). 없으면 ',.0f'
        """
        from tkinter import ttk

        self.tree = tree
        self.summable_column_ids = [c for c in summable_column_ids if c]
        self.column_display_names = column_display_names or {}
        self.column_formats = column_formats or {}
        self.frame = ttk.Frame(parent, padding=(6, 4))
        self._label_var = None
        lbl = ttk.Label(
            self.frame,
            text="",
            font=("맑은 고딕", 10, "bold"),
        )
        lbl.pack(anchor="w")
        self._label_var = lbl

    def pack(self, **kwargs):
        self.frame.pack(**kwargs)

    def update_totals(self) -> None:
        """Tree 내용을 읽어 건수 + 합계 가능 컬럼 합산 후 하단 라벨 갱신. 필터 적용된 행만 반영."""
        if not self._label_var:
            return
        children = self.tree.get_children("")
        count = len(children)
        parts = [f"건수: {count}"]
        if not self.summable_column_ids:
            self._label_var.config(text="  |  ".join(parts))
            return
        cols = list(self.tree["columns"])
        if not cols:
            self._label_var.config(text="  |  ".join(parts))
            return
        col_index = {c: i for i, c in enumerate(cols)}
        sums = {c: 0.0 for c in self.summable_column_ids if c in col_index}
        for item_id in children:
            try:
                vals = self.tree.item(item_id, "values")
                if not vals:
                    continue
                for c in sums:
                    idx = col_index[c]
                    if idx < len(vals):
                        sums[c] += _safe_float(vals[idx])
            except (TypeError, IndexError, Exception):
                continue
        for c in self.summable_column_ids:
            if c not in sums:
                continue
            name = self.column_display_names.get(c) or (self.tree.heading(c, "text") if c in cols else c)
            fmt = self.column_formats.get(c, ",.0f")
            parts.append(f"{name}: {sums[c]:{fmt}}")
        self._label_var.config(text="  |  ".join(parts))


# ═══════════════════════════════════════════════════════════════
# v7.3.4: TreeHoverEngine — 선택 우선순위 + 헤더 정렬 (GPT v7.2.0 기반 개선)
# ═══════════════════════════════════════════════════════════════

class TreeHoverEngine:
    """
    Treeview 행 hover 효과 + 선택 우선순위 처리.

    기존 enable_row_hover 대비 개선:
    - 선택된 행에서는 호버 태그 미적용 (선택 스타일 우선)
    - 태그 추가/제거 방식 (기존 태그 보존, _hover만 토글)
    - winfo_exists 체크로 위젯 파괴 후 크래시 방지

    사용법:
        engine = TreeHoverEngine(tree)
        engine.attach()
    """

    def __init__(self, tree):
        self.tree = tree
        self._hover_item = None

        # 테마 자동 감지
        try:
            from .theme_aware import ThemeAware
            is_dark = ThemeAware.is_dark()
        except (ImportError, Exception):
            is_dark = False

        try:
            p = ThemeColors.get_palette(is_dark)
        except Exception:
            p = {}
        self.hover_bg  = p.get("bg_hover",       "#334155" if is_dark else "#e2e8f0")
        self.hover_fg  = p.get("text_primary",    "#e2e8f0" if is_dark else "#1e293b")

    def attach(self) -> None:
        """Treeview에 hover 이벤트 바인딩."""
        self.tree.tag_configure(
            "_hover",
            background=self.hover_bg,
            foreground=self.hover_fg,
        )
        self.tree.bind("<Motion>",             self._on_motion,  add="+")
        self.tree.bind("<Leave>",              self._on_leave,   add="+")
        self.tree.bind("<<TreeviewSelect>>",   self._on_select,  add="+")

    def _on_motion(self, event) -> None:
        """마우스 이동 시 hover 행 업데이트."""
        try:
            item = self.tree.identify_row(event.y)
            if item == self._hover_item:
                return
            # 이전 hover 제거
            if self._hover_item:
                try:
                    tags = list(self.tree.item(self._hover_item, "tags"))
                    if "_hover" in tags:
                        tags.remove("_hover")
                        self.tree.item(self._hover_item, tags=tags)
                except Exception:
                    pass
            # 새 hover 적용 (선택된 행 제외)
            if item and item not in self.tree.selection():
                tags = list(self.tree.item(item, "tags"))
                if "_hover" not in tags:
                    tags.append("_hover")
                    self.tree.item(item, tags=tags)
            self._hover_item = item
        except Exception:
            pass

    def _on_leave(self, event) -> None:
        """마우스가 Treeview 벗어날 때 hover 해제."""
        try:
            if self._hover_item:
                tags = list(self.tree.item(self._hover_item, "tags"))
                if "_hover" in tags:
                    tags.remove("_hover")
                    self.tree.item(self._hover_item, tags=tags)
            self._hover_item = None
        except Exception:
            pass

    def _on_select(self, event) -> None:
        """선택 시 hover 태그 제거 (선택 스타일 우선)."""
        try:
            if self._hover_item and self._hover_item in self.tree.selection():
                tags = list(self.tree.item(self._hover_item, "tags"))
                if "_hover" in tags:
                    tags.remove("_hover")
                    self.tree.item(self._hover_item, tags=tags)
        except Exception:
            pass


def enable_row_hover(tree, hover_bg_light='#e2e8f0', hover_bg_dark='#1e293b'):
    """하위 호환 래퍼 — TreeHoverEngine 사용."""
    engine = TreeHoverEngine(tree)
    engine.attach()
    return engine


def style_treeview_header(tree):
    """
    v7.3.4: Treeview 헤더 클릭 정렬 (▲/▼) 설정.
    각 컬럼 헤딩 클릭 시 오름/내림 정렬 + 화살표 표시.
    """
    sort_state = {}

    for col in tree["columns"]:
        sort_state[col] = True  # 기본: 오름차순

        def _sort(c=col):
            asc = sort_state.get(c, True)
            try:
                data = [(tree.set(item, c), item)
                        for item in tree.get_children("")]
                # 숫자 시도
                def sort_key(x):
                    try:
                        return float(x[0].replace(",", "").replace(" ", ""))
                    except (ValueError, AttributeError):
                        return x[0].lower() if isinstance(x[0], str) else x[0]
                data.sort(reverse=not asc, key=sort_key)
                for idx, (_, item) in enumerate(data):
                    tree.move(item, "", idx)
                # 헤딩 텍스트에 화살표 추가
                arrow = " ▲" if asc else " ▼"
                for c2 in tree["columns"]:
                    orig = tree.heading(c2, "text").rstrip(" ▲▼")
                    tree.heading(c2, text=orig)
                orig = tree.heading(c, "text").rstrip(" ▲▼")
                tree.heading(c, text=orig + arrow)
                sort_state[c] = not asc
            except Exception:
                pass

        tree.heading(col, command=_sort)
