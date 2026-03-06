# SQM 재고관리 시스템 — CHANGELOG

> (주)지와이로지스 | 개발: Ruby (루비리)  
> 시스템: 광양 물류창고 재고관리 (탄산리튬 · 황산니켈 LOT 기반)

---

## v6.4.0 — 2026-03-07

### 🚀 BL 선사별 파싱 레지스트리 완전 통합

**신규 파일**
- `features/ai/bl_carrier_registry.py` (309줄) — 선사 자동 탐지 + 정규식 BL No 추출
  - MSC / Maersk / HMM / CMA CGM / ONE 5개 선사 템플릿 내장
  - 점수제 선사 탐지 (키워드 1점 + 정규식 2점)
  - 신규 선사 추가 = `CARRIER_TEMPLATES` 항목 1개만 추가
- `tools/bl_carrier_update_tool.py` (197줄) — BL PDF → 선사 패턴 자동 분석 도구
  - `python tools/bl_carrier_update_tool.py <BL.pdf> [선사ID]`
  - BL No 후보 목록 + 최적 정규식 추천 + 붙여넣기 코드 자동 생성
- `tests/test_bl_carrier_registry.py` (272줄) — pytest 회귀 테스트 20개
  - T01~T03: MSC 탐지 / T04~T06: Maersk 탐지
  - T07~T09: BL No 추출 / T10~T12: 오탐 방지
  - T13~T15: bl_equals_booking_no 플래그
  - T16~T17: 미탐 처리 / T18~T20: 실제 PDF 통합 테스트
  - **pytest 20/20 PASS** (MSC MEDUFP963996 · Maersk 263764814 실제 PDF 검증)

**수정 파일**
- `features/ai/gemini_parser.py` — `BLResult` 3개 필드 추가, `parse_bl()` 5단계 통합
  - `carrier_id`, `carrier_name`, `bl_equals_booking_no`
  - 정규식 1차 추출 → Gemini 보조 (불일치 시 WARNING)
- `parsers/cross_check_engine.py` — Maersk BL No == Booking No 정상 플래그 처리
  - `bl_equals_booking_no=True` 시 BL==Booking 크로스체크 경고 생략
- `gui_app_modular/dialogs/onestop_inbound.py` (2,486줄) — 선사 뱃지 위젯 UI
  - 서류 선택 행 아래 `_carrier_label` 실제 위젯 배치
  - 선사별 색상: MSC=파랑, Maersk=초록, HMM=빨강, CMA=오렌지, ONE=핑크
  - 파싱 중 "⏳ 파싱 중..." → 완료 후 "[선사: XXX]" 뱃지 표시
- `gui_app_modular/dialogs/settings_dialog.py` — BL 선사 도구 다이얼로그 구현
  - `_on_bl_carrier_register()`: PDF 선택 → 분석 결과 ScrolledText 표시
  - `_on_bl_carrier_analyze()`: 등록 선사 목록 + 검증 상태 표시
- `gui_app_modular/menu_registry.py` — `FILE_MENU_AI_TOOLS_ITEMS` 추가
- `gui_app_modular/mixins/custom_menubar.py` — 🤖 AI 어시스턴트 서브메뉴 선사 도구 추가
- `gui_app_modular/mixins/toolbar_mixin.py` — BL 선사 도구 서브메뉴 + fallback 강화
- `version.py` — v6.4.0 릴리즈 노트 기록
- `pytest.ini` — `carrier` 마커 등록

### 🔥 핫픽스: 입고 메뉴 2개만 표시되는 버그

- **원인**: `custom_menubar.py` import 블록에서 `FILE_MENU_AI_TOOLS_ITEMS` 들여쓰기 4칸
  → 런타임 `ImportError` → `_build_inbound_menu` fallback → 2개만 표시
- **수정**: 들여쓰기 12칸으로 수정 + `except Exception`으로 확장 + fallback에 `⚡ 빠른 PDF 스캔` 추가

### ✅ 입고 메뉴 항목 (핫픽스 후 정상)
```
입고 ▼: 📄 PDF 스캔 입고 / ⚡ 빠른 PDF 스캔 (폴더) / 📊 엑셀 수동 입고
        📋 D/O 후속 연결 / 📂 반품 입고 / 🔄 반품(재입고) + 6개
```

---

## v6.3.5 — 2026-02-xx

### 🛡️ LOT 파싱 BUG 1~6 수정 + 단위 테스트 62개

- **BUG-1**: Invoice LOT Hallucination 필터 (28→24개 오파싱 차단)
- **BUG-2**: PL LOT Hallucination 필터
- **BUG-3**: LOT 불일치 PL list_no 순서 정렬 + 순번 표시
- **BUG-4**: PL 25개 오파싱 방지 (`lot_no` 1차 방어선)
- **BUG-5**: 거짓 중복 경고 (`is_retry` 파라미터)
- **BUG-6**: 재시도 조건 과민 (`_RETRY_THRESHOLD=3` 완화)
- pytest 62/62 PASS (`gemini_parser` 31 + `cross_check` 13 + `onestop_inbound` 18)

---

## v6.3.4 — 2026-02-xx

### 🔧 코드베이스 품질 감사 + WinError 32 완전 수정

- **품질 감사**: 64/100점 → 개선 로드맵 3단계 수립
- **WinError 32 완전 수정** (5개 파일):
  - `auto_backup.py`: WAL checkpoint PASSIVE 모드
  - `window_mixin.py` + `engine.py`: 앱 종료 시 `close_all()` 호출
  - `database.py`: `gc.collect()` + `os.remove` 재시도 로직
  - `keybindings_mixin.py`: 종료 시퀀스 안전화
- **Python 3.14 TclError 수정**: `split_panel.py` `ttk.PanedWindow minsize` 분리 호출
- **PL 파싱 누락 분석**: Gemini skip 원인 3가지 규명
  (페이지 경계 / LOT 유사성 / 토큰 한계)

---

## v6.3.2 — 2026-01-xx

### 🏗️ 모듈화 GUI 아키텍처 안정화

- `main_app.py` + mixin 파일 분리 완료
- `menu_registry.py` 단일 소스 메뉴 정의 (custom_menubar · toolbar 공용)
- One-Stop 입고 다이얼로그 (`onestop_inbound.py`) v22 패치
  - 4단계 워크플로우: AVAILABLE → RESERVED → PICKED → SOLD
  - 3-way 스캔 검증: actual == expected → FINALIZED
  - actual < expected → REVIEW_REQUIRED
  - actual > expected → 하드스톱 ERROR (확정 차단)
- 증빙 문서 첨부 SHA-256 중복 방지 + 90일 자동 정리
- 교차 배치 톤백 중복 방지 + 전체 감사 추적 `audit_log` DB 기록

---

## v6.3.0 — 2025-12-xx

### 🧹 대규모 코드 정리 (Dead Code 제거)

- 죽은 코드 ~4,600줄 제거
- 미사용 함수 52개 제거
- SQL 보안 강화 (파라미터 바인딩 통일)
- Python 3.12 호환성 수정

---

## v5.x 계열 주요 변경

| 버전 | 핵심 변경 |
|------|-----------|
| v5.9.x | 컨테이너 구분 필터바 이동, 인라인 진행바 |
| v5.7.x | Invoice/FA 통합, Bill of Loading 파싱 강화 |
| v5.6.5 | PDF 입고 진입점 OneStop 단일화 (6개→1개) |
| v5.5.3 | Gemini API + PDF 변환 메뉴 재배치 |
| v5.4.x | 드롭다운 메뉴 색상 다크/라이트 고정 |
| v5.x   | 7탭 네비게이션 (판매가능/배정/화물결정/출고/재고/통계/로그) |

---

## v4.x 계열 주요 변경

| 버전 | 핵심 변경 |
|------|-----------|
| v4.1.x | Gemini Vision API 통합 (Google Vision → Gemini 전환) |
| v4.0.x | LOT 기반 재고 추적 기반 설계 |

---

## 시스템 핵심 원칙

```
SQM Core Principle (최우선 불변):
  1 LOT = 톤백 N개 (500kg 또는 1000kg) + 샘플 1개 (1kg)
  LOT 총무게 = (톤백수 × 단가) + 1kg
  → 가용 중량 계산 시 샘플 1kg 반드시 제외
```

**All-or-Nothing 트랜잭션**: 프리플라이트 검증 0오류 완료 후에만 DB 커밋  
**중량 무결성**: 샘플 1kg 제외 처리는 시스템 최고 우선순위 불변 조건  
**감사 추적**: 모든 입출고 변경 `audit_log` 테이블 전체 기록  

---

*생성: Ruby (SQM AI 파트너) | 최종 업데이트: 2026-03-07*
