# -*- coding: utf-8 -*-
"""
SQM 재고관리 시스템 - 톤백 위치 업로드 다이얼로그
=================================================

v4.2.3: Excel 파일 선택 → 미리보기 → 업로드

작성자: Ruby
"""

import tkinter as tk
from tkinter import filedialog, ttk
import logging
from typing import Optional, Callable

logger = logging.getLogger(__name__)


def show_tonbag_location_upload_dialog(
    parent,
    engine,
    callback: Optional[Callable] = None
):
    """
    톤백 위치 업로드 다이얼로그 표시
    
    Args:
        parent: 부모 위젯
        engine: SQMDatabase 인스턴스
        callback: 업로드 완료 후 호출할 콜백
    """
    from ..utils.tonbag_location_uploader import TonbagLocationUploader
    from .location_upload_preview import LocationUploadPreviewDialog
    from ..utils.custom_messagebox import CustomMessageBox
    
    # 파일 선택
    file_path = filedialog.askopenfilename(
        parent=parent,
        title="📍 톤백 위치 Excel 파일 선택",
        filetypes=[
            ("Excel 파일", "*.xlsx *.xls"),
            ("모든 파일", "*.*")
        ]
    )
    
    if not file_path:
        return
    
    # 로딩 다이얼로그
    loading_dialog = tk.Toplevel(parent)
    loading_dialog.title("처리 중...")
    loading_dialog.geometry("300x100")
    loading_dialog.transient(parent)
    loading_dialog.grab_set()
    
    # 화면 중앙
    loading_dialog.update_idletasks()
    x = (loading_dialog.winfo_screenwidth() // 2) - 150
    y = (loading_dialog.winfo_screenheight() // 2) - 50
    loading_dialog.geometry(f"+{x}+{y}")
    
    tk.Label(
        loading_dialog,
        text="📂 Excel 파일을 분석 중입니다...",
        font=('맑은 고딕', 11),
        pady=20
    ).pack()
    
    progress = ttk.Progressbar(loading_dialog, mode='indeterminate')
    progress.pack(fill=tk.X, padx=20, pady=10)
    progress.start()
    
    loading_dialog.update()
    
    try:
        # 업로더 생성
        uploader = TonbagLocationUploader(engine)
        
        # Excel 파싱
        success, message, data = uploader.parse_excel(file_path)
        
        if not success:
            loading_dialog.destroy()
            CustomMessageBox.showerror(parent, "파싱 실패", message)
            return
        
        # UID 매칭 및 검증
        result = uploader.validate_and_match(data)
        
        loading_dialog.destroy()
        
        # 미리보기 다이얼로그
        def on_confirm(matched_data):
            # 업로드 실행
            success, message = uploader.update_locations(matched_data)
            
            if success:
                CustomMessageBox.showinfo(parent, "완료", message)
                if callback:
                    callback()
            else:
                CustomMessageBox.showerror(parent, "실패", message)
        
        LocationUploadPreviewDialog(
            parent,
            result,
            on_confirm=on_confirm
        )
        
    except (ValueError, TypeError, OSError) as e:
        loading_dialog.destroy()
        logger.error(f"위치 업로드 처리 실패: {e}")
        CustomMessageBox.showerror(
            parent,
            "오류",
            f"처리 중 오류 발생:\n{e}"
        )


# 테스트
if __name__ == '__main__':
    # 간단한 테스트
    logger.debug("톤백 위치 업로드 다이얼로그 모듈")
    logger.debug("show_tonbag_location_upload_dialog() 함수를 메인 앱에서 호출하세요")
