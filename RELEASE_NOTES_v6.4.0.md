# SQM 재고관리 시스템 v6.4.0 — 릴리즈 노트

**릴리즈 일자**: 2026-03-07  
**버전**: 6.4.0 (v6.4.1·v6.4.2 핫픽스 통합)

---

## 요약

BL 선사별 파싱 레지스트리 통합, 빠른 PDF 스캔 탐지 수정, 입고 메뉴/UI 보강, 창 크기 저장(persistence), 입고 미리보기 열 순서 통일을 포함한 통합 릴리즈입니다.

---

## 주요 변경 사항

### 1. BL 선사별 파싱 (v6.4.0)

- **bl_carrier_registry.py** 신규
  - MSC / Maersk / HMM / CMA CGM / ONE 5개 선사 템플릿
  - 점수제 선사 탐지, 선사별 정규식 BL No 추출
  - 신규 선사 추가 시 `CARRIER_TEMPLATES` 항목 1개만 추가
- **gemini_parser.py**: `BLResult`에 `carrier_id`, `carrier_name`, `bl_equals_booking_no` 추가, `parse_bl()` 5단계 통합
- **cross_check_engine.py**: Maersk BL No == Booking No인 경우 크로스체크 경고 생략 (`bl_equals_booking_no=True`)
- **원스톱 입고 다이얼로그**: 파싱 후 [선사: MSC/Maersk/...] 뱃지 표시 (선사별 색상)
- **설정 다이얼로그**: BL 선사 등록/분석 도구 메뉴 추가
- **pytest**: `carrier` 마커 및 test_bl_carrier_registry 20개 테스트
- **tools/bl_carrier_update_tool.py**: BL PDF → 선사 패턴 분석 도구

### 2. 핫픽스: 입고 메뉴 (v6.4.0)

- **원인**: `FILE_MENU_AI_TOOLS_ITEMS` import 오류로 fallback 시 입고 메뉴 2개만 표시
- **조치**: custom_menubar import 정리, fallback에 "⚡ 빠른 PDF 스캔" 포함

### 3. 빠른 PDF 스캔 탐지 (v6.4.1)

- **원인**: `2200034276_BL.pdf` 등 파일명에서 `_` → 공백 치환 후 기존 키워드(`_bl`, `bl_`) 미매칭
- **조치**: `key_name` 앞뒤 공백 추가, 키워드를 공백 경계(` bl ` 등)로 통일, 구분자에 마침표 추가

### 4. v6.4.2 FINAL 통합

- 빠른 입고 시 원스톱 창 강제 전환 fallback 제거
- 상위 폴더 선택 시 하위 자동 탐색(`_collect_candidate_files`) 반영

### 5. UI/UX

- **입고 미리보기**: 열 순서를 종전 4개 파일 입고(재고 탭)와 동일하게 통일  
  (NO → LOT NO → SAP NO → BL NO → PRODUCT → STATUS → …)
- **창 크기·위치 저장**: 원스톱 입고 다이얼로그, 검색 팝업에 geometry persistence 적용
- **split_panel**: Python 3.14 `ttk.PanedWindow` minsize 오류 수정 (pane 분리 호출)

---

## 적용·빌드

- Python 3.10+ (3.12 권장, 3.14 호환)
- 의존성: `requirements.txt` 기준 설치 후 실행
- pytest: `pytest tests/ -m "not slow and not api and not gui"` (선사 테스트: `-m carrier`)

---

## 파일 요약

| 구분 | 내용 |
|------|------|
| 신규 | features/ai/bl_carrier_registry.py, tools/bl_carrier_update_tool.py, tests/test_bl_carrier_registry.py, .github/workflows/pytest.yml |
| 수정 | CHANGELOG.md, version.py, pytest.ini, gemini_parser.py, cross_check_engine.py, onestop_inbound.py, settings_dialog.py, menu_registry.py, custom_menubar.py, menu_mixin.py, toolbar_mixin.py, inbound_processor.py, split_panel.py, 기타 다이얼로그/핸들러/탭 |

---

*(주) 지와이로지스 | SQM 재고관리 시스템*
