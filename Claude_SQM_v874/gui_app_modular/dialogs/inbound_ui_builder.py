"""
P3-S1 Refactor: InboundUIBuilder — UI 생성 전담
gui_app_modular/dialogs/inbound_ui_builder.py

선택 책임: OneStopInboundDialog의 모든 UI 빌드 메서드를 담당
"""


class InboundUIBuilder:
    """UI 생성 전담 클래스 — Mixin"""
    
    def __init__(self, parent_dialog):
        self._parent = parent_dialog
    
    def _cd_setup_window(self):
        """윈도우 초기 설정"""
        pass
    
    def _cd_build_step_indicator(self):
        """단계 표시 바"""
        pass
    
    def _cd_build_doc_file_section(self):
        """서류 파일 선택 섹션"""
        pass
    
    def _cd_build_parse_action_buttons(self):
        """파싱 버튼 그룹"""
        pass
    
    def _cd_build_carrier_and_progress(self):
        """캐리어 + 진행도"""
        pass
    
    def _cd_build_preview_table(self):
        """미리보기 테이블"""
        pass
    
    def _cd_build_doc_frame(self):
        """서류 프레임"""
        pass
    
    def _cd_build_parse_action_buttons(self):
        """파싱 액션 버튼"""
        pass
    
    def _build_inbound_action_buttons(self):
        """입고 액션 버튼"""
        pass
    
    def _build_inbound_doc_frame(self):
        """입고 문서 프레임"""
        pass
    
    def _build_inbound_doc_frame_impl(self):
        """입고 문서 프레임 구현"""
        pass
    
    def _build_inbound_preview_frame_impl(self):
        """입고 미리보기 프레임 구현"""
        pass
    
    def _build_inbound_button_frame(self):
        """입고 버튼 프레임"""
        pass
    
    def _build_inbound_button_frame_impl(self):
        """입고 버튼 프레임 구현"""
        pass
    
    def _attach_doc_tooltip(self):
        """서류 툴팁 부착"""
        pass
    
    def _select_folder(self):
        """폴더 선택"""
        pass
    
    def _select_file(self):
        """파일 선택"""
        pass
    
    def _create_product_combobox(self):
        """제품 콤보박스 생성"""
        pass
    
    def _build_upload_summary_message(self):
        """업로드 요약 메시지 생성"""
        pass
