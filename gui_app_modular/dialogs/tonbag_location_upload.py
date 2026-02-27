# -*- coding: utf-8 -*-
"""
SQM 재고관리 시스템 - 톤백 위치 업로드 다이얼로그
=================================================

v4.2.3: Excel 파일 선택 → 미리보기 → 업로드
v5.9.x: 데이터 붙여넣기 / 파일 열기 선택 후 진행

작성자: Ruby
"""

import tkinter as tk
from tkinter import filedialog, ttk
import logging
from typing import Optional, Callable

logger = logging.getLogger(__name__)


def _run_with_data(parent, engine, data, callback: Optional[Callable] = None):
    """파싱된 데이터로 매칭 → 미리보기 → 업로드 실행."""
    from ..utils.tonbag_location_uploader import TonbagLocationUploader
    from .location_upload_preview import LocationUploadPreviewDialog
    from ..utils.custom_messagebox import CustomMessageBox

    uploader = TonbagLocationUploader(engine)
    result = uploader.validate_and_match(data)

    def on_confirm(matched_data):
        success, message = uploader.update_locations(matched_data)
        if success:
            CustomMessageBox.showinfo(parent, "완료", message)
            if callback:
                callback()
        else:
            CustomMessageBox.showerror(parent, "실패", message)

    LocationUploadPreviewDialog(parent, result, on_confirm=on_confirm)


def run_location_upload_with_file(parent, engine, file_path: str, callback: Optional[Callable] = None):
    """지정한 Excel 파일로 로케이션 업로드 플로우 실행 (드래그앤드롭 등에서 호출)."""
    from ..utils.tonbag_location_uploader import TonbagLocationUploader
    from ..utils.custom_messagebox import CustomMessageBox

    uploader = TonbagLocationUploader(engine)
    success, message, data = uploader.parse_excel(file_path)
    if not success or not data:
        CustomMessageBox.showerror(parent, "파싱 실패", message or "데이터가 없습니다.")
        return
    _run_with_data(parent, engine, data, callback=callback)


def show_tonbag_location_upload_dialog(
    parent,
    engine,
    callback: Optional[Callable] = None
):
    """
    톤백 위치 업로드: [데이터 붙여넣기] vs [파일 열기] 선택 후 미리보기 → 업로드
    """
    from ..utils.tonbag_location_uploader import TonbagLocationUploader
    from .location_upload_preview import LocationUploadPreviewDialog
    from ..utils.custom_messagebox import CustomMessageBox

    # 1) 선택 다이얼로그 — Excel/데이터 입력 원칙 통일 (데이터 붙여넣기 / 파일 업로드)
    from ..utils.ui_constants import (
        UPLOAD_CHOICE_HEADER, UPLOAD_CHOICE_PASTE, UPLOAD_CHOICE_UPLOAD,
        UPLOAD_CHOICE_BTN_PASTE, UPLOAD_CHOICE_BTN_UPLOAD,
    )
    choice_win = tk.Toplevel(parent)
    choice_win.title("📍 톤백 위치 매핑")
    choice_win.transient(parent)
    choice_win.resizable(False, False)
    frm = ttk.Frame(choice_win, padding=20)
    frm.pack(fill=tk.BOTH, expand=True)
    ttk.Label(frm, text=UPLOAD_CHOICE_HEADER, font=("맑은 고딕", 10)).pack(pady=(0, 12))
    ttk.Label(frm, text=UPLOAD_CHOICE_PASTE, font=("맑은 고딕", 9), wraplength=380, justify=tk.LEFT).pack(anchor="w", pady=(0, 6))
    ttk.Label(frm, text=UPLOAD_CHOICE_UPLOAD, font=("맑은 고딕", 9), wraplength=380, justify=tk.LEFT).pack(anchor="w", pady=(0, 12))
    btn_frm = ttk.Frame(frm)
    btn_frm.pack(pady=4)
    chosen = {"value": None}

    def on_paste():
        chosen["value"] = "paste"
        choice_win.destroy()

    def on_file():
        chosen["value"] = "file"
        choice_win.destroy()

    def on_cancel():
        chosen["value"] = None
        choice_win.destroy()

    ttk.Button(btn_frm, text=UPLOAD_CHOICE_BTN_PASTE, command=on_paste).pack(side=tk.LEFT, padx=6)
    ttk.Button(btn_frm, text=UPLOAD_CHOICE_BTN_UPLOAD, command=on_file).pack(side=tk.LEFT, padx=6)
    ttk.Button(btn_frm, text="취소", command=on_cancel).pack(side=tk.LEFT, padx=6)
    choice_win.geometry("+%d+%d" % (parent.winfo_rootx() + 80, parent.winfo_rooty() + 80))
    choice_win.grab_set()
    choice_win.wait_window()
    choice = chosen.get("value")

    if choice == "file":
        file_path = filedialog.askopenfilename(
            parent=parent,
            title="📍 톤백 위치 Excel 파일 선택",
            filetypes=[("Excel 파일", "*.xlsx *.xls"), ("모든 파일", "*.*")]
        )
        if not file_path:
            return
        loading_dialog = tk.Toplevel(parent)
        loading_dialog.title("처리 중...")
        loading_dialog.geometry("300x100")
        loading_dialog.transient(parent)
        loading_dialog.grab_set()
        loading_dialog.update_idletasks()
        x = (loading_dialog.winfo_screenwidth() // 2) - 150
        y = (loading_dialog.winfo_screenheight() // 2) - 50
        loading_dialog.geometry(f"+{x}+{y}")
        tk.Label(loading_dialog, text="📂 Excel 파일을 분석 중입니다...", font=("맑은 고딕", 11), pady=20).pack()
        progress = ttk.Progressbar(loading_dialog, mode="indeterminate")
        progress.pack(fill=tk.X, padx=20, pady=10)
        progress.start()
        loading_dialog.update()
        try:
            uploader = TonbagLocationUploader(engine)
            success, message, data = uploader.parse_excel(file_path)
            loading_dialog.destroy()
            if not success:
                CustomMessageBox.showerror(parent, "파싱 실패", message)
                return
            _run_with_data(parent, engine, data, callback=callback)
        except (ValueError, TypeError, OSError) as e:
            loading_dialog.destroy()
            logger.error(f"위치 업로드 처리 실패: {e}")
            CustomMessageBox.showerror(parent, "오류", f"처리 중 오류 발생:\n{e}")
        return

    if choice == "paste":
        from ..utils.paste_table_dialog import show_paste_table_dialog

        # 업로드한 형식과 동일: lot_no, tonbag_no, uid, location (SQM 톤백 로케이션 매핑)
        location_columns = [
            ("lot_no", "lot_no", 120),
            ("tonbag_no", "tonbag_no", 100),
            ("uid", "uid", 140),
            ("location", "location", 120),
        ]

        def on_location_confirm(rows):
            if not rows:
                CustomMessageBox.showwarning(parent, "안내", "데이터가 없습니다.")
                return
            uploader = TonbagLocationUploader(engine)
            raw_lines = ["\t".join(["lot_no", "tonbag_no", "uid", "location"])]
            for r in rows:
                raw_lines.append("\t".join([
                    str(r.get("lot_no", "")),
                    str(r.get("tonbag_no", "")),
                    str(r.get("uid", "")),
                    str(r.get("location", "")),
                ]))
            raw = "\n".join(raw_lines)
            success, message, data = uploader.parse_pasted_text(raw)
            if not success:
                CustomMessageBox.showerror(parent, "파싱 실패", message)
                return
            _run_with_data(parent, engine, data, callback=callback)

        show_paste_table_dialog(
            parent,
            title="📍 SQM 톤백 로케이션 매핑 (붙여넣기)",
            columns=location_columns,
            instruction="아래 표에 lot_no, tonbag_no, uid, location 데이터를 붙여넣기(Ctrl+V) 한 뒤 [확인]을 누르면 DB에 반영됩니다. 형식: X-00-00-00 (구역-열-층-칸).",
            confirm_text="확인",
            cancel_text="취소",
            on_confirm=on_location_confirm,
            min_size=(560, 380),
        )
        return


# 테스트
if __name__ == '__main__':
    # 간단한 테스트
    logger.debug("톤백 위치 업로드 다이얼로그 모듈")
    logger.debug("show_tonbag_location_upload_dialog() 함수를 메인 앱에서 호출하세요")
