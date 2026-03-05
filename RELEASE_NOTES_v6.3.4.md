# SQM 재고관리 시스템 v6.3.4

**릴리즈 일자:** 2026-03-05

## 요약

Phase A·B 패치 통합, Invoice/PL 24개 LOT 검증 통일, 검수센터(드래그·캡처 OCR·규칙 저장), 원스톱 입고 진행률 메시지 구체화.

---

## 변경 사항

### Phase A (LOT 파서·검증)

- **Invoice LOT**: `parsers/lot_parser_fix.reconcile_invoice_lots_from_pdf` 연동 — PDF 텍스트 우선 추출, 실패 시 Gemini + 중복 제거
- **PL 24개 검증**: `parsers/pl_lot_parser.validate_pl_lots` 호출로 개수·중복 검증, 루비 인라인 진단 로직 제거
- **Invoice vs PL 검증**: 패치 쪽 로직으로 통일 (`invoice_lot_parser`, `pl_lot_parser`, `lot_parser_fix`)

### Phase B1/B2 (검수센터)

- **검수센터 다이얼로그**: 원스톱 입고 파싱 완료 후 **🧪 검수센터** 버튼으로 실행
- **기능**: PDF 보기(PyMuPDF), 드래그 ROI 텍스트 추출, **캡처 붙여넣기(OCR)**(pytesseract), **규칙 저장**(SQLite `review_rules`)
- 적용 시 미리보기 데이터 즉시 반영 및 QC 재검증(크로스체크·Gate 검증) 콜백 호출

### 원스톱 입고 UX

- **진행률 메시지 구체화**:  
  - 시작: "📄 4종 서류(PL/Invoice/BL/DO) 파싱을 시작합니다..."  
  - 3%: "🔌 API 연결 및 파서 준비 중..."  
  - 8%: "📂 서류 N개 확인됨 — PDF 파싱을 시작합니다..."  
  - 파일별: "📦 Packing List 파싱 중 — 파일명.pdf" 등
- **진행률 바**: `_update_progress` 호출 시 퍼센트·경과 시간 즉시 반영

### 기타

- `version.py` 단일 소스로 버전 관리
- AGENTS.md 규칙 준수 (예외 처리·네이밍·Excel 원칙 등)

---

## 의존성

- **검수센터 PDF/이미지**: PyMuPDF(fitz), Pillow  
- **검수센터 OCR**: pytesseract + 시스템 Tesseract 엔진(선택)

---

## 업그레이드

- v6.3.3 기준 저장소를 pull 한 뒤 `version.py` 및 변경된 파일이 반영된 상태입니다.
- 검수센터 규칙 저장 시 `engine.db` 사용; DB 래퍼가 `execute()`를 지원해야 합니다.
