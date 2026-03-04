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
import os
import re
from tkinter import filedialog

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

    def _on_pdf_inbound_quick_folder(self) -> None:
        """빠른 PDF 스캔(폴더): 폴더 1회 선택으로 4종 서류 자동 탐지 후 즉시 파싱."""
        folder = filedialog.askdirectory(parent=self.root, title="빠른 PDF 스캔 폴더 선택")
        if not folder:
            return

        try:
            file_names = os.listdir(folder)
        except Exception as e:
            self._log(f"❌ 폴더 읽기 실패: {e}")
            logger.error("빠른 PDF 스캔 폴더 읽기 실패: %s", e, exc_info=True)
            return

        if not file_names:
            self._log("⚠️ 선택한 폴더가 비어 있습니다.")
            return

        detected = self._detect_inbound_docs_from_folder(folder, file_names)
        required = ("PACKING_LIST", "INVOICE", "BL")
        missing_required = [k for k in required if k not in detected]
        if missing_required:
            kor = {
                "PACKING_LIST": "Packing List",
                "INVOICE": "Invoice, FA",
                "BL": "Bill of Loading",
                "DO": "Delivery Order",
            }
            miss = ", ".join(kor.get(k, k) for k in missing_required)
            self._log(f"⚠️ 빠른 스캔 중단 — 필수 서류 누락: {miss}")
            self._on_pdf_inbound(initial_files=detected or {})
            return

        summary = ", ".join(f"{k}={os.path.basename(v)}" for k, v in detected.items())
        self._log(f"⚡ 빠른 PDF 스캔 자동탐지: {summary}")
        try:
            from ..dialogs.onestop_inbound import OneStopInboundDialog
            dialog = OneStopInboundDialog(
                parent=self.root,
                engine=self.engine,
                log_fn=self._log,
                app=self
            )
            dialog.show(
                initial_files=detected,
                auto_start_parse=True,
                skip_parse_confirm=True,
            )
        except (ImportError, ModuleNotFoundError) as e:
            self._log(f"❌ 원스톱 입고 오류: {e}")
            logger.error(f"원스톱 입고 오류: {e}", exc_info=True)

    def _detect_inbound_docs_from_folder(self, folder: str, file_names: list[str]) -> dict:
        """파일명 키워드 기반 서류 자동 매칭(PL/INV/BL/DO)."""
        keyword_map = {
            "PACKING_LIST": ["packing", "pl", "포장", "명세서"],
            "INVOICE": ["invoice", "fa", "송장"],
            "BL": ["seawaybill", "sea waybill", "billoflading", "bill of lading", "b/l", "bl", "선하"],
            "DO": ["delivery", "d/o", "do", "인도"],
        }
        ext_allow = {".pdf", ".png", ".jpg", ".jpeg"}
        bucket = {k: [] for k in keyword_map}

        for name in file_names:
            path = os.path.join(folder, name)
            if not os.path.isfile(path):
                continue
            ext = os.path.splitext(name)[1].lower()
            if ext not in ext_allow:
                continue
            key_name = re.sub(r"[\s_\-]+", " ", name.lower())
            for doc_type, keys in keyword_map.items():
                if any(k in key_name for k in keys):
                    score = os.path.getmtime(path)
                    bucket[doc_type].append((score, path))

        detected = {}
        for doc_type, candidates in bucket.items():
            if not candidates:
                continue
            candidates.sort(key=lambda x: x[0], reverse=True)
            detected[doc_type] = candidates[0][1]
        return detected

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
