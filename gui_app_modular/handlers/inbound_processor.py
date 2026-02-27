# -*- coding: utf-8 -*-
"""
SQM 재고관리 - 입고 처리 Mixin (v5.6.5)
========================================

v5.6.5: 입고 경로 단일화
  - 모든 PDF 입고 → OneStopInboundDialog (유일한 경로)
  - Excel 입고 → import_handlers._bulk_import_inventory_simple
  - 서류별 개별 입고(Invoice/BL/DO 단독) 제거 → 원스톱으로 통합
  - 기존 6개 진입점 → 하위호환 래퍼로 _on_pdf_inbound 단일 호출
"""

import logging

logger = logging.getLogger(__name__)


class InboundProcessorMixin:
    """입고 처리 Mixin — v5.6.5 단일 경로"""

    # ══════════════════════════════════════════════════════════
    # 유일한 PDF 입고 진입점
    # ══════════════════════════════════════════════════════════

    def _on_pdf_inbound(self, initial_files: dict = None) -> None:
        """v5.6.5: PDF 입고 — OneStopInboundDialog

        FA + PL + BL 필수 (Gate-1), DO 선택.
        initial_files: {'DO': 경로} 등 드래그앤드롭/캡처 이미지 사전 지정.
        """
        self._log("")
        self._log(f"{'=' * 50}")
        self._log("📥 PDF 입고 (원스톱)")
        self._log(f"{'=' * 50}")

        try:
            from ..dialogs.onestop_inbound import OneStopInboundDialog
            dialog = OneStopInboundDialog(
                parent=self.root,
                engine=self.engine,
                log_fn=self._log,
                app=self
            )
            dialog.show(initial_files=initial_files or {})
        except (ImportError, ModuleNotFoundError) as e:
            self._log(f"❌ 원스톱 입고 오류: {e}")
            logger.error(f"원스톱 입고 오류: {e}", exc_info=True)

    # ══════════════════════════════════════════════════════════
    # 하위 호환 래퍼 — 기존 코드(메뉴/단축키/D&D)에서 호출 유지
    # ══════════════════════════════════════════════════════════

    def _on_onestop_inbound(self) -> None:
        """[하위호환] → _on_pdf_inbound"""
        self._on_pdf_inbound()

    def _on_sequential_inbound(self) -> None:
        """[하위호환] → _on_pdf_inbound"""
        self._on_pdf_inbound()

    def _on_inbound_by_type(self, doc_type: str = '') -> None:
        """[하위호환] 서류별 개별 입고 → 원스톱 통합"""
        self._on_pdf_inbound()

    def _process_inbound(self, pdf_path: str) -> None:
        """[하위호환] 단일 파일 D&D/키보드 → 원스톱"""
        self._on_pdf_inbound()

    # ══════════════════════════════════════════════════════════
    # D/O 후속 연결 (v5.6.6)
    # ══════════════════════════════════════════════════════════

    def _on_do_update(self) -> None:
        """v5.6.6: D/O 후속 연결 — 기존 LOT에 도착일/Free Time UPDATE"""
        self._log("")
        self._log("📋 D/O 후속 연결")

        try:
            from ..dialogs.do_update_dialog import DOUpdateDialog
            dialog = DOUpdateDialog(
                parent=self.root,
                engine=self.engine,
                log_fn=self._log,
                app=self
            )
            dialog.show()
        except (ImportError, ModuleNotFoundError) as e:
            self._log(f"❌ D/O 후속 연결 오류: {e}")
            logger.error(f"D/O 후속 연결 오류: {e}", exc_info=True)
