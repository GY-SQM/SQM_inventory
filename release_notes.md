# SQM v5.9.0 — PDF/이미지 변환 통합

> 2026-02-18 | 22 files changed, +1,736 / -576

---

## 신규 기능

### 📄 캡처 이미지 → Excel/Word 변환
기존 PDF 전용이었던 변환 기능을 **캡처 이미지(PNG/JPG/BMP/TIFF)**까지 확장했습니다.

- **메뉴**: `📄 PDF/이미지 변환` → Excel / → Word
- 파일 선택 시 PDF뿐 아니라 **이미지 파일도 바로 선택** 가능
- OCR(pytesseract)로 텍스트 추출 → 테이블 감지 → Excel/Word 자동 생성
- **일괄 변환**: 폴더 내 PDF + 이미지 모두 한 번에 Excel 변환

### 🚢 D/O 파싱 강화 (v5.8.6.B)
- **Arrival Date 하이브리드 추출**: Gemini 응답 + PDF 텍스트 정규식 병행
- **Free Time 계산 복원**: con_return 기반 반납일 자동 산출
- **캡처 이미지 D/O 파싱**: `parse_do_from_image()` — 파일 없이 PNG/JPG 바이트로 직접 파싱

### 🤖 Gemini 2.5-flash thinking model 대응
- `response.text`가 빈 경우 `candidates[0].content.parts`에서 직접 추출
- API 타임아웃 60초로 확장 (PDF 이미지 파싱용)

---

## 개선 사항

| 영역 | 내용 |
|------|------|
| 입고 엔진 | `inbound_mixin` 안정성 개선 |
| import_handlers | 대폭 리팩토링 — 출고/입고 로직 정리 |
| 원스톱 입고 | 다이얼로그 UI 개선, 프로그레스 표시 강화 |
| 드래그앤드롭 | 이미지 파일(.png/.jpg) 드롭 시 D/O로 자동 인식 |
| 테마 | theme_mixin 다크/라이트 가시성 개선 |
| 키바인딩 | Ctrl+O 파일 열기에 이미지 확장자 추가 |
| 툴바 | 메뉴 구조 개선, 테스트 DB 초기화 메뉴 추가 |

---

## 신규 파일

| 파일 | 설명 |
|------|------|
| `parsers/do_free_time_ocr.py` | D/O Free Time OCR 전용 파서 (pytesseract+OpenCV) |
| `docs/MENU_REFERENCE.md` | 메뉴 구조 레퍼런스 문서 |
| `docs/REVIEW_EXCEL_INOUT_TEMPLATE_AND_ENGINE.md` | 엑셀 입출고 템플릿·엔진 리뷰 문서 |

---

## 변경 파일 (22개)

```
 engine_modules/inventory_modular/inbound_mixin.py
 features/ai/gemini_parser.py
 gui_app_modular/dialogs/onestop_inbound.py
 gui_app_modular/handlers/import_handlers.py
 gui_app_modular/handlers/inbound_processor.py
 gui_app_modular/handlers/pdf_handlers.py
 gui_app_modular/mixins/advanced_dialogs_mixin.py
 gui_app_modular/mixins/custom_menubar.py
 gui_app_modular/mixins/drag_drop_mixin.py
 gui_app_modular/mixins/keybindings_mixin.py
 gui_app_modular/mixins/menu_mixin.py
 gui_app_modular/mixins/theme_mixin.py
 gui_app_modular/mixins/toolbar_mixin.py
 gui_app_modular/tabs/inventory_tab.py
 gui_app_modular/window_config.json
 parsers/document_parser_modular/do_mixin.py
 parsers/do_free_time_ocr.py (신규)
 utils/pdf_converter.py
 version.py
 theme_preference.json
 docs/MENU_REFERENCE.md (신규)
 docs/REVIEW_EXCEL_INOUT_TEMPLATE_AND_ENGINE.md (신규)
```

---

## 의존성

| 패키지 | 용도 | 필수 |
|--------|------|------|
| PyMuPDF (fitz) | PDF → 이미지 렌더링 | 필수 |
| openpyxl | Excel 생성 | 필수 |
| python-docx | Word 생성 | Word 변환 시 |
| pytesseract + Pillow | 이미지 OCR | 이미지 변환 시 |

---

**(주) 지와이로지스 2026년 02월 18일**
