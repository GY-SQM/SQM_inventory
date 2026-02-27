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
        입고현황 일괄 업로드 (고급)
        
        기존 재고 데이터를 Excel에서 일괄 가져오기
        """
        from ..utils.constants import filedialog, pd, HAS_PANDAS
        
        if not HAS_PANDAS:
            CustomMessageBox.showerror(self.root, "오류", "pandas가 설치되지 않았습니다.")
            return
        
        file_path = filedialog.askopenfilename(
            title="입고현황 Excel 선택 (고급)",
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
            
            from core.column_registry import normalize_header
            df.columns = [normalize_header(c) for c in df.columns]

            required_cols = ['lot_no', 'sap_no', 'product']
            columns_lower = list(df.columns)

            missing = [c for c in required_cols if c not in columns_lower]
            if missing:
                # v4.2.1: 상세 오류 팝업 표시
                try:
                    from ..utils.upload_error_dialog import show_upload_error_dialog
                    from ..utils.upload_error_template import UploadErrorTemplate
                    
                    error_msg = UploadErrorTemplate.format_multiple_errors(
                        errors=[{
                            'type': 'column_header',
                            'rows': [
                                {'row': 1, 'value': f"누락: {', '.join(missing)}", 'column': '컬럼명'}
                            ]
                        }],
                        total_rows=len(df)
                    )
                    
                    show_upload_error_dialog(
                        self.root,
                        "Excel 컬럼 오류",
                        error_msg
                    )
                except (ImportError, Exception):
                    # 팝업 실패 시 기존 방식
                    CustomMessageBox.showerror(self.root, "오류", 
                        f"필수 컬럼 누락: {', '.join(missing)}\n\n"
                        f"현재 컬럼: {', '.join(df.columns.tolist())}")
                return
            
            # 확인 후 처리
            if CustomMessageBox.askyesno(self.root, "확인",
                f"{len(df)}건의 데이터를 가져옵니다.\n\n계속하시겠습니까?"):
                
                self._log(f"📥 입고현황 일괄 업로드 시작: {len(df)}건")
                
                # 실제 처리는 _import_inbound_excel_auto 활용
                if hasattr(self, '_import_inbound_excel_auto'):
                    self._import_inbound_excel_auto(file_path)
                else:
                    CustomMessageBox.showinfo(self.root, "안내", 
                        f"데이터 확인 완료: {len(df)}건\n\n"
                        "상세 처리는 '입고(Excel)' 메뉴를 사용하세요.")
                    
        except (RuntimeError, ValueError) as e:
            logger.error(f"입고현황 일괄 업로드 오류: {e}")
            
            # v4.2.1: 상세 오류 팝업 표시
            try:
                from ..utils.upload_error_dialog import show_upload_error_dialog
                from ..utils.upload_error_template import UploadErrorTemplate
                
                # 오류 타입 판단
                error_type = 'file_format' if 'read_excel' in str(e) else 'invalid_number'
                
                error_msg = UploadErrorTemplate.format_multiple_errors(
                    errors=[{
                        'type': error_type,
                        'rows': [{'row': '?', 'value': str(e), 'column': ''}]
                    }],
                    total_rows=0
                )
                
                show_upload_error_dialog(
                    self.root,
                    "입고현황 업로드 오류",
                    error_msg
                )
            except (ImportError, Exception):
                # 팝업 실패 시 기존 방식
                CustomMessageBox.showerror(self.root, "오류", f"처리 오류:\n{e}")
    
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
