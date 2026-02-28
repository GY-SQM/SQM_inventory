# -*- coding: utf-8 -*-
"""
SQM 재고관리 - 일괄 업로드 Mixin
=================================
v3.8.4 - advanced_features_mixin에서 분리

기능:
- 입고현황 일괄 업로드
- 톤백 일괄 업로드
"""

import logging
from ..utils.ui_constants import CustomMessageBox

logger = logging.getLogger(__name__)


class BulkImportMixin:
    """입고/톤백 일괄 업로드 Mixin"""

    def _bulk_import_inventory(self) -> None:
        """
        v6.2.2 성능 보완: 입고현황 조회 다이얼로그 오픈
        """
        try:
            from ..dialogs.inbound_history_dialog import InboundHistoryDialog
            dialog = InboundHistoryDialog(
                parent=self.root,
                engine=self.engine,
                log_fn=self._log,
                app=self
            )
            dialog.show()
        except (ImportError, ModuleNotFoundError) as e:
            logger.error(f"입고현황 조회 오류: {e}", exc_info=True)
            CustomMessageBox.showerror(self.root, "오류", f"입고현황 조회 오류:\n{e}")
    
    def _bulk_import_tonbags(self) -> None:
        """
        톤백 상세 일괄 업로드
        
        톤백 정보를 Excel에서 일괄 가져오기
        """
        from ..utils.constants import filedialog, pd, HAS_PANDAS
        
        if not HAS_PANDAS:
            CustomMessageBox.showerror(self.root, "오류", "pandas가 설치되지 않았습니다.")
            return
        
        file_path = filedialog.askopenfilename(
            title="톤백 상세 Excel 선택",
            filetypes=[
                ("Excel files", "*.xlsx *.xls"),
                ("All files", "*.*")
            ]
        )
        
        if not file_path:
            return
        
        try:
            df = pd.read_excel(file_path)
            
            if df.empty:
                CustomMessageBox.showwarning(self.root, "경고", "빈 Excel 파일입니다.")
                return
            
            # 톤백 관련 컬럼 확인
            tonbag_keywords = ['tonbag', 'sub_lot', 'bag', 'weight', 'lot']
            columns_lower = [str(c).lower() for c in df.columns]
            
            matches = sum(1 for kw in tonbag_keywords if any(kw in c for c in columns_lower))
            if matches < 2:
                CustomMessageBox.showwarning(self.root, "경고",
                    "톤백 관련 컬럼을 찾을 수 없습니다.\n\n"
                    f"현재 컬럼: {', '.join(df.columns.tolist())}")
                return
            
            # 확인
            if CustomMessageBox.askyesno(self.root, "확인",
                f"{len(df)}건의 톤백 데이터를 가져옵니다.\n\n계속하시겠습니까?"):
                
                self._log(f"📦 톤백 일괄 업로드 시작: {len(df)}건")
                CustomMessageBox.showinfo(self.root, "안내",
                    f"톤백 데이터 확인 완료: {len(df)}건\n\n"
                    "이 기능은 추후 업데이트 예정입니다.")
                
        except (RuntimeError, ValueError) as e:
            logger.error(f"톤백 일괄 업로드 오류: {e}")
            CustomMessageBox.showerror(self.root, "오류", f"처리 오류:\n{e}")
    
    # ═══════════════════════════════════════════════════════════════
    # DB 무결성 및 체크섬
    # ═══════════════════════════════════════════════════════════════
