"""Inbound date dialog mixin extracted from onestop_inbound."""

import logging
import tkinter as tk
from tkinter import ttk
from datetime import timedelta, date as _date_type

from gui_app_modular.utils.ui_constants import create_themed_toplevel
from .inbound_utils import amd_validate_date, amd_calc_dates
from ..utils.ui_constants import ThemeColors, DialogSize, apply_modal_window_options, center_dialog, is_dark
from ..utils.gui_bootstrap import DateEntry, HAS_DATEENTRY


logger = logging.getLogger(__name__)


class InboundDateDialogMixin:
    """날짜 다이얼로그 Mixin"""

    def _ask_missing_dates(self, prefilled_ship: str = '', do_result=None) -> dict:
        """누락된 입항/반납일/프리타임을 입력받는다."""
        result_holder = [None]

        def _build_popup():
            win = None
            try:
                win = create_themed_toplevel(self.dialog)

                if not do_result:
                    win.title("📋 D/O 미첨부 — 날짜 정보 입력")
                    msg_text = "D/O가 없습니다. 입항일 등을 직접 입력하거나,\n나중에 D/O를 추가할 수 있습니다."
                else:
                    win.title("📋 D/O 파싱 실패 — 날짜 정보 입력")
                    msg_text = "D/O에서 날짜를 읽지 못했습니다.\n직접 입력하거나 나중에 D/O를 다시 첨부할 수 있습니다."

                win.geometry(DialogSize.get_geometry(self.dialog, 'medium'))
                apply_modal_window_options(win)
                win.transient(self.dialog)
                win.grab_set()
                center_dialog(win, self.dialog)

                frame = ttk.Frame(win, padding=20)
                frame.pack(fill=tk.BOTH, expand=True)

                ttk.Label(frame, text=msg_text, font=('맑은 고딕', 11, 'bold'), wraplength=460).pack(anchor='w', pady=(0, 12))

                class _FieldRef:
                    def __init__(self, get_fn, widget, set_fn):
                        self.get = get_fn
                        self.widget = widget
                        self.set = set_fn

                def _make_date_field(parent, label, hint, prefill='', required=False):
                    _cal_dark = is_dark()
                    lf = ttk.LabelFrame(parent, text=f"{'★ ' if required else ''}{label}{' — 필수' if required else ''}", padding=8)
                    lf.pack(fill=tk.X, pady=(0, 8))
                    var = tk.StringVar(value=prefill)

                    if HAS_DATEENTRY and DateEntry is not None:
                        startdate = None
                        if prefill:
                            try:
                                parts = prefill.split('-')
                                startdate = _date_type(int(parts[0]), int(parts[1]), int(parts[2]))
                            except (ValueError, IndexError):
                                logger.debug("[SUPPRESSED] exception in inbound_date_dialog.py")
                        de = DateEntry(lf, dateformat='%Y-%m-%d', startdate=startdate, bootstyle='info', width=16)
                        de.pack(side=tk.LEFT, padx=(0, 8))
                        ttk.Label(lf, text=hint, font=('맑은 고딕', 9), foreground=ThemeColors.get('text_muted', _cal_dark)).pack(side=tk.LEFT)

                        def _get():
                            return (de.entry.get() or '').strip() if de and de.winfo_exists() else ''

                        def _set(v):
                            if de and de.winfo_exists():
                                try:
                                    parts = str(v).strip().split('-')
                                    if len(parts) == 3:
                                        d = _date_type(int(parts[0]), int(parts[1]), int(parts[2]))
                                        de.configure(startdate=d)
                                        de.entry.delete(0, tk.END)
                                        de.entry.insert(0, d.strftime('%Y-%m-%d'))
                                    else:
                                        de.entry.delete(0, tk.END)
                                        de.entry.insert(0, str(v))
                                except (ValueError, IndexError, TypeError):
                                    de.entry.delete(0, tk.END)
                                    de.entry.insert(0, str(v))

                        return _FieldRef(_get, de, _set)

                    entry = ttk.Entry(lf, textvariable=var, font=('맑은 고딕', 11), width=16)
                    entry.pack(side=tk.LEFT, padx=(0, 8))
                    ttk.Label(lf, text=hint, font=('맑은 고딕', 9), foreground=ThemeColors.get('text_muted', _cal_dark)).pack(side=tk.LEFT)
                    return _FieldRef(lambda: (var.get() or '').strip(), entry, var.set)

                ship_var = None
                arrival_var = _make_date_field(frame, "입항일 (Arrival Date)", "YYYY-MM-DD (예: 2025-10-17)", required=True)
                con_return_ref = _make_date_field(frame, "컨테이너 반납기한 (con_return)", "반납일 YYYY-MM-DD (비우면 Free time 일수로)")

                _ft_dark = is_dark()
                lf_ft = ttk.LabelFrame(frame, text="Free time (일수)", padding=8)
                lf_ft.pack(fill=tk.X, pady=(0, 8))
                ft_var = tk.StringVar(value='')
                ft_entry = ttk.Entry(lf_ft, textvariable=ft_var, font=('맑은 고딕', 11), width=10)
                ft_entry.pack(side=tk.LEFT, padx=(0, 8))
                ttk.Label(lf_ft, text="반납일-입항일=Free time (둘 중 하나만 입력 시 나머지 자동 계산·자동 입력 시 상대 필드 비활성화)", font=('맑은 고딕', 9), foreground=ThemeColors.get('text_muted', _ft_dark)).pack(side=tk.LEFT)
                ft_ref = _FieldRef(lambda: (ft_var.get() or '').strip(), ft_entry, ft_var.set)

                err_var = tk.StringVar()
                _err_dark = is_dark()
                ttk.Label(frame, textvariable=err_var, font=('맑은 고딕', 10), foreground=ThemeColors.get('danger', _err_dark)).pack(anchor='w', pady=(4, 0))

                _updating_silently = {'v': False}

                def _sync_from_con_return(*_):
                    if _updating_silently['v']:
                        return
                    arr = (arrival_var.get() or '').strip()
                    cr = (con_return_ref.get() or '').strip()
                    if not arr or not cr or not amd_validate_date(arr) or not amd_validate_date(cr):
                        return
                    try:
                        arr_d = _date_type(*[int(x) for x in arr.split('-')])
                        cr_d = _date_type(*[int(x) for x in cr.split('-')])
                        ft_days = max(0, (cr_d - arr_d).days)
                        _updating_silently['v'] = True
                        ft_ref.set(str(ft_days))
                        ft_entry.config(state='disabled')
                    except (ValueError, IndexError, TypeError):
                        logger.debug("[SUPPRESSED] exception in inbound_date_dialog.py")
                    finally:
                        _updating_silently['v'] = False

                def _sync_from_ft(*_):
                    if _updating_silently['v']:
                        return
                    arr = (arrival_var.get() or '').strip()
                    ft_raw = (ft_ref.get() or '').strip()
                    if not arr or not ft_raw or not amd_validate_date(arr):
                        return
                    if not ft_raw.isdigit() or int(ft_raw) < 0:
                        return
                    try:
                        arr_d = _date_type(*[int(x) for x in arr.split('-')])
                        cr_d = arr_d + timedelta(days=int(ft_raw))
                        cr_str = cr_d.strftime('%Y-%m-%d')
                        _updating_silently['v'] = True
                        con_return_ref.set(cr_str)
                        w = con_return_ref.widget
                        if hasattr(w, 'entry'):
                            w.entry.config(state='disabled')
                        else:
                            w.config(state='disabled')
                    except (ValueError, IndexError, TypeError):
                        logger.debug("[SUPPRESSED] exception in inbound_date_dialog.py")
                    finally:
                        _updating_silently['v'] = False

                def _enable_both():
                    _updating_silently['v'] = True
                    try:
                        ft_entry.config(state='normal')
                        w = con_return_ref.widget
                        if hasattr(w, 'entry'):
                            w.entry.config(state='normal')
                        else:
                            w.config(state='normal')
                    finally:
                        _updating_silently['v'] = False

                if hasattr(con_return_ref.widget, 'entry'):
                    con_return_ref.widget.entry.bind('<FocusOut>', _sync_from_con_return)
                else:
                    con_return_ref.widget.bind('<FocusOut>', _sync_from_con_return)
                ft_entry.bind('<FocusOut>', _sync_from_ft)

                def _on_ok():
                    err_var.set('')
                    try:
                        arr = (arrival_var.get() or '').strip()
                        if not arr:
                            err_var.set("⚠️ 입항일은 필수입니다!")
                            return
                        if not amd_validate_date(arr):
                            err_var.set("⚠️ 입항일 형식 오류 (YYYY-MM-DD)")
                            return
                        arr_d = _date_type(*[int(x) for x in arr.split('-')])
                    except (ValueError, IndexError, TypeError) as e:
                        err_var.set("⚠️ 입항일 파싱 오류 (YYYY-MM-DD)")
                        logger.debug(f"[_ask_missing_dates] 입항일 파싱: {e}")
                        return

                    if prefilled_ship and amd_validate_date(prefilled_ship.strip()):
                        try:
                            ship_d = _date_type(*[int(x) for x in prefilled_ship.strip().split('-')])
                            if arr_d <= ship_d:
                                err_var.set("⚠️ 입항일은 선적일보다 이후여야 합니다.")
                                return
                        except (ValueError, IndexError, TypeError):
                            logger.debug("[SUPPRESSED] exception in inbound_date_dialog.py")

                    ship = ''
                    if ship_var is not None:
                        ship = (ship_var.get() or '').strip()
                        if ship and not amd_validate_date(ship):
                            err_var.set("⚠️ 선적일 형식 오류 (YYYY-MM-DD)")
                            return

                    con_return_str = (con_return_ref.get() or '').strip()
                    ft_raw = (ft_var.get() or '').strip()
                    if con_return_str and not amd_validate_date(con_return_str):
                        err_var.set("⚠️ 반납기한(con_return): YYYY-MM-DD 형식")
                        return

                    con_return_str, free_time_str, _calc_err = amd_calc_dates(arr, con_return_str, ft_raw)
                    if _calc_err:
                        err_var.set(_calc_err)
                        return

                    from ..utils.custom_messagebox import CustomMessageBox
                    confirmed = CustomMessageBox._create_dialog(
                        win,
                        "입력 확인",
                        f"Free time {free_time_str}일, 컨테이너 반납일은 {con_return_str} 입니다.\n\n맞습니까?",
                        'question',
                        [('맞음', True), ('다시 입력', False)],
                        default_button=0,
                    )
                    if not confirmed:
                        return

                    result_holder[0] = {
                        'ship_date': ship,
                        'arrival_date': arr,
                        'con_return': con_return_str,
                        'free_time': free_time_str,
                    }
                    win.destroy()

                def _on_defer():
                    result_holder[0] = {'deferred': True}
                    win.destroy()

                def _on_cancel():
                    result_holder[0] = None
                    win.destroy()

                btn_frame = ttk.Frame(frame)
                btn_frame.pack(fill=tk.X, pady=(12, 0))
                ttk.Button(btn_frame, text="✅ 확인", command=_on_ok, width=10).pack(side=tk.LEFT, padx=(0, 8))
                ttk.Button(btn_frame, text="✏️ 수정", command=_enable_both, width=10).pack(side=tk.LEFT, padx=(0, 8))
                ttk.Button(btn_frame, text="📋 D/O 추후 첨부", command=_on_defer, width=16).pack(side=tk.LEFT, padx=(0, 8))
                ttk.Button(btn_frame, text="❌ 취소", command=_on_cancel, width=10).pack(side=tk.LEFT)
                win.protocol("WM_DELETE_WINDOW", _on_cancel)
                return win
            except Exception as e:
                logger.error(f"[_ask_missing_dates] 팝업 오류: {e}", exc_info=True)
                return None

        if not self.dialog or not self.dialog.winfo_exists():
            return None

        win = _build_popup()
        if win and win.winfo_exists():
            win.wait_window(win)
        return result_holder[0]
