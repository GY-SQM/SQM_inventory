Claude_SQM_v806_INVOICE_PATCH
빌드: 2026-03-17

오류: InvoiceMixin.parse_invoice() got an unexpected keyword argument 'gemini_hint'
원인: parse_invoice() 함수에 gemini_hint 파라미터가 없었음
수정: invoice_mixin.py — gemini_hint: str = '' 파라미터 추가

설치:
parsers/document_parser_modular/invoice_mixin.py 덮어쓰기
