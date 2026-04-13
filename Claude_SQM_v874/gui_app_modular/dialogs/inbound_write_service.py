"""
P3-S1 Refactor: InboundWriteService — 데이터 저장/완료/정리
gui_app_modular/dialogs/inbound_write_service.py

책임: DB 업로드 전후 처리, 성공 표시, 완료 후 정리, D/O 후속 연결
"""

import logging
import sqlite3

from core.types import safe_float
from features.validators.inbound_validator import InboundValidator

logger = logging.getLogger(__name__)


# onestop_inbound.py의 DOC_TYPES 참조용
DOC_TYPES = [
    ('BL',           '① Bill of Loading (선하증권)', True),
    ('PACKING_LIST', '② Packing List (포장명세서)', True),
    ('INVOICE',      '③ Invoice, FA (송장)',        True),
    ('DO',           '④ Delivery Order (인도지시서) (선택사항)', False),
]


class InboundWriteService:
    """저장/완료 서비스 전담 클래스 — Mixin

    OneStopInboundDialog의 MRO에 합성되어
    self.preview_data / self.dialog / self.engine 등에 접근한다.
    """

    def _has_required_docs(self) -> bool:
        """필수 서류 3종 확인 — InboundValidator 위임."""
        return InboundValidator.has_required_docs(self.file_paths, DOC_TYPES)

    def _show_success_and_close(self, count: int):
        """DB 저장 완료 후 성공 표시 및 닫기."""
        try:
            self._activate_step(3)
        except (sqlite3.Error, ValueError, TypeError, RuntimeError) as e:
            logger.warning(f'[UI] onestop_inbound _show_success_and_close: {e}')

        def _close():
            if self.dialog and self.dialog.winfo_exists():
                _app = self.app if self.app else None
                _ask_more_inbound = False
                if getattr(self, '_ask_excel_after_upload', False):
                    self._ask_excel_after_upload = False
                    try:
                        from ..utils.custom_messagebox import CustomMessageBox
                        if CustomMessageBox.askyesno(self.dialog, "엑셀 내보내기",
                                "DB 업로드가 완료되었습니다.\n엑셀 내보내기도 하시겠습니까?\n"
                                "(아니오를 누르면 여기서 종료합니다.)"):
                            self._export_to_excel()
                    except (ImportError, ModuleNotFoundError):
                        pass
                _msg = self._build_upload_summary_message(count)
                try:
                    from ..utils.custom_messagebox import CustomMessageBox
                    CustomMessageBox.showinfo(self.dialog, "업데이트 완료 요약", _msg)
                except (ImportError, ModuleNotFoundError):
                    pass

                self._reset_after_upload_success()

                try:
                    from ..utils.custom_messagebox import CustomMessageBox
                    _ask_more_inbound = CustomMessageBox.askyesno(
                        self.dialog,
                        "추가 입고 선택 (예=추가 입고 / 아니오=종료)",
                        "추가로 입고 작업을 하시겠습니까?\n\n"
                        "예: 추가 입고 화면을 다시 엽니다.\n"
                        "아니오: 이번 입고 프로세스를 종료합니다."
                    )
                except (ImportError, ModuleNotFoundError):
                    from tkinter import messagebox as msgbox
                    _ask_more_inbound = msgbox.askyesno(
                        "추가 입고 선택 (예=추가 입고 / 아니오=종료)",
                        "추가로 입고 작업을 하시겠습니까?\n\n"
                        "예: 추가 입고 화면을 다시 엽니다.\n"
                        "아니오: 이번 입고 프로세스를 종료합니다."
                    )

                self.dialog.destroy()

                if _app:
                    try:
                        _root = getattr(_app, 'root', None)
                        if _root:
                            if hasattr(_app, 'notebook') and hasattr(_app, 'tab_inventory'):
                                _root.after(200, lambda: _app.notebook.select(_app.tab_inventory))
                            _app._safe_refresh()
                            logger.info("[onestop] 전체 탭 새로고침 완료")
                            if _ask_more_inbound and hasattr(_app, '_on_onestop_inbound'):
                                if hasattr(_app, '_reset_inventory_view_for_new_inbound'):
                                    _root.after(300, _app._reset_inventory_view_for_new_inbound)
                                _root.after(700, _app._on_onestop_inbound)
                                logger.info("[onestop] 추가 입고 요청으로 원스톱 입고 재오픈")
                            elif not _ask_more_inbound:
                                logger.info("[onestop] 추가 입고 없음 — 입고 프로세스 종료")
                    except (RuntimeError, ValueError) as e:
                        logger.debug(f"재고 새로고침 호출 실패: {e}")

        if self.dialog and self.dialog.winfo_exists():
            self.dialog.after(100, _close)

    def _build_upload_summary_message(self, count: int) -> str:
        """업로드 완료 요약 문자열 생성."""
        rows = list(getattr(self, 'preview_data', []) or [])
        edited_cnt = len(getattr(self, '_edited_rows', set()) or set())
        sap_set = {str(r.get('sap_no', '') or '').strip() for r in rows
                   if str(r.get('sap_no', '') or '').strip()}
        bl_set = {str(r.get('bl_no', '') or '').strip() for r in rows
                  if str(r.get('bl_no', '') or '').strip()}
        cont_set = {str(r.get('container_no', '') or '').strip() for r in rows
                    if str(r.get('container_no', '') or '').strip()}
        total_net = 0.0
        for r in rows:
            try:
                total_net += safe_float(r.get('net_weight', 0) or 0)
            except (ValueError, TypeError):
                pass
        return (
            f"✅ {count}개 LOT 저장 완료\n\n"
            f"- 수정된 행: {edited_cnt}건\n"
            f"- SAP NO: {len(sap_set)}종\n"
            f"- BL NO: {len(bl_set)}종\n"
            f"- 컨테이너: {len(cont_set)}개\n"
            f"- 총 NET: {total_net:,.0f} kg"
        )

    def _reset_after_upload_success(self) -> None:
        """업로드 성공 후 로컬/메인 미리보기 데이터 정리."""
        try:
            self.preview_data = []
            self.parsed_results = {}
            self._original_preview_data = []
            self._cross_check_result = None
            self._edited_rows = set()
            self._undo_stack = []
            self._redo_stack = []
            self._view_indices = []
            if hasattr(self, '_update_summary'):
                self._update_summary()
            if hasattr(self, '_update_undo_redo_buttons'):
                self._update_undo_redo_buttons()
        except (RuntimeError, ValueError, TypeError, AttributeError) as e:
            logger.debug(f"업로드 후 로컬 미리보기 정리 실패: {e}")
        self._clear_preview_from_main()

    def _enable_buttons(self) -> None:
        """업로드/엑셀 버튼 활성화."""
        def _u():
            try:
                if self.btn_upload and self.btn_upload.winfo_exists():
                    self.btn_upload.config(state='normal')
                if self.btn_excel and self.btn_excel.winfo_exists():
                    self.btn_excel.config(state='normal')
            except (RuntimeError, ValueError):
                pass
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.after(0, _u)

    def _on_add_do_later(self) -> None:
        """D/O 나중에 추가 — do_update_dialog로 연결."""
        try:
            from ..dialogs.do_update_dialog import DoUpdateDialog
            current_theme = getattr(self.parent, 'current_theme', 'darkly')
            DoUpdateDialog(self.dialog, self.engine, current_theme=current_theme)
            self._log_safe("📋 D/O 후속 연결 다이얼로그 열림")
        except Exception as e:
            logger.error(f"D/O 나중에 추가 오류: {e}")
            try:
                from ..utils.custom_messagebox import CustomMessageBox
                CustomMessageBox.showerror(
                    self.dialog, "오류",
                    f"D/O 다이얼로그를 열 수 없습니다.\n{e}\n\n"
                    f"메뉴 → 입고 → [D/O 후속 연결] 을 사용하세요."
                )
            except Exception:
                pass
