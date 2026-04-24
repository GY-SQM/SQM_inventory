# 🤖 v864-3 포팅 작업 핸드오프 (2026-04-24~25 세션)

> **다음 AI 또는 작업자에게**: 이 문서 하나만 읽으면 처음부터 모든 컨텍스트 파악 가능합니다. 13개 커밋 ~22 dev-day 분량의 실제 구현이 끝난 상태입니다.

---

## 1. 🎯 프로젝트 절대 원칙 (사용자 요구사항)

> **"v864-2의 UI를 그대로, 하부 기능까지 전부 v864-3(WebView)에 재현"**
>
> **UI만 Tkinter→WebView로 변경, 로직은 100% 동일하게 포팅**

- v864-2: Tkinter + ttkbootstrap **데스크톱** 앱 (`gui_app_modular/`)
- v864-3: HTML/CSS/JS + Python FastAPI **WebView** 앱
- 두 버전이 **데이터·동작·결과가 완전히 동일**해야 함
- v864-2는 "Golden Reference" — 모든 결정의 진실 기준

### 사용자 핵심 통찰 (꼭 기억)

1. **"4 vs 1" 원칙** — v864-2는 PDF 입고에 4슬롯(BL/PL/Invoice/DO), v864-3은 1슬롯만 있던 게 가장 큰 불만. 모든 "축소된 기능"이 동일한 패턴.
2. **"하부 조직" = 다이얼로그 내부 UI** — 메뉴 클릭 후 뜨는 다이얼로그의 깊이까지 일치해야 함
3. **답답함 누적**: 반쪽짜리 기능이 누적되면 큰 스트레스. **하나라도 100% 완성**을 선호.
4. **시각 비교 필수** — 서브에이전트 추출 결과를 스크린샷 교차검증해야 함 (Phase 1A에서 has_sidebar:false로 잘못 판정한 사례 있음)

---

## 2. 📁 작업 환경

### 디렉터리 구조
```
D:/program/SQM_inventory/
├── Claude_SQM_v864_2/          # ⭐ Golden Reference (Tkinter — 수정 금지, 참조만)
│   ├── gui_app_modular/        # Python GUI 코드
│   │   ├── menu_registry.py    # 메뉴 단일 정의
│   │   ├── main_app.py         # 탭 등 (1435 lines)
│   │   ├── tabs/               # 9 tab files
│   │   ├── dialogs/            # 30+ dialog files
│   │   └── mixins/             # ToolbarMixin, MenuMixin, ...
│   ├── parsers/                # 4종 PDF 파서 + 크로스체크
│   └── analysis/               # 스펙 추출 결과 (Phase 1A/1B)
│
├── Claude_SQM_v864_3/          # ⭐ 작업 대상 (WebView — 모든 수정은 여기)
│   ├── frontend/
│   │   ├── index.html          # 메뉴바 (이번에 cascading 재구성)
│   │   ├── css/
│   │   │   ├── design-system.css
│   │   │   └── v864-layout.css # 974 lines (이번에 +422 추가)
│   │   └── js/
│   │       └── sqm-inline.js   # 5485 lines (이번에 +2106 추가) — 단일 번들
│   ├── backend/
│   │   ├── api/
│   │   │   ├── __init__.py     # 라우터 등록
│   │   │   ├── inbound.py      # 807 lines (이번에 +339 추가)
│   │   │   ├── outbound_api.py # 572 lines (이번에 +106 추가)
│   │   │   ├── inventory_api.py # 469 lines (이번에 +124 추가) — Allocation 포함
│   │   │   └── allocation_api.py
│   │   └── (engine_modules는 v864-2와 공유)
│   ├── parsers/                # ⭐ v864-2에서 복사됨, 그대로 활용
│   │   ├── document_parser_modular/
│   │   │   ├── parser.py       # DocumentParserV3 — parse_bl/pl/invoice/do
│   │   │   ├── bl_mixin.py
│   │   │   ├── packing_mixin.py
│   │   │   ├── invoice_mixin.py
│   │   │   └── do_mixin.py     # ⚠️ Gemini API key 필수
│   │   ├── cross_check_engine.py # 549 lines — cross_check_documents()
│   │   └── pdf_parser.py
│   ├── analysis/               # 스펙 추출 결과 (Phase 2)
│   ├── settings.ini            # ⚠️ gitignored — API key 저장
│   ├── main_webview.py         # 앱 실행 진입점
│   └── HANDOFF_SESSION_2026-04-25.md  # ⭐ 이 파일
│
└── v864_comparison/            # ⭐ Phase 3 Gap 분석 마스터 자료
    ├── gap_report.md           # 21KB — 마스터 보고서
    ├── gap_matrix.json         # 72KB — 128행 매트릭스
    └── porting_plan.md         # 18KB — Sprint 계획
```

### Git
- **리포지토리**: https://github.com/kidongnam1/sqm_2
- **브랜치**: `claude/v864-3-sprint0`
- **시작점 커밋**: `ea9d0f0` (Upload Claude_SQM_v864_3 — 이번 세션 시작 상태)
- **현재 HEAD**: `c2158da` (Sprint 1-3-C 완료)
- 인증: 정상 작동 확인됨

### 환경
- OS: Windows 11
- Python: 3.11
- 주요 라이브러리: pandas 3.x, fastapi 0.128, pywebview 5.x, google-genai, openai
- 설치 명령: `pip install -r requirements.txt && pip install uvicorn pywebview pyinstaller`
- 실행: `python main_webview.py`
- API key: `settings.ini`의 `[Gemini] api_key = AQ...` (사용자 설정)

---

## 3. 📊 분석 자료 (이미 완료, 그대로 활용)

### Phase 1A — v864-2 메뉴/탭 추출
- `Claude_SQM_v864_2/analysis/v864-2_spec.json` (45KB)
- `Claude_SQM_v864_2/analysis/v864-2_spec.md` (18KB)
- 결과: 7개 탑레벨 메뉴, 9개 탭, 14개 P0 갭 식별

### Phase 1B — v864-2 다이얼로그 30개 카탈로그
- `Claude_SQM_v864_2/analysis/v864-2_dialogs.md` (20KB)
- Tier-A 12개 핵심 다이얼로그 상세
- Tier-B 30개 보조 다이얼로그 요약
- ⭐ **OneStopInboundDialog 4슬롯 검증 완료**

### Phase 2 — v864-3 현재 상태
- `Claude_SQM_v864_3/analysis/v864-3_spec.json` (44KB)
- `Claude_SQM_v864_3/analysis/v864-3_spec.md` (8KB)
- `Claude_SQM_v864_3/analysis/v864-3_modals.md` (7KB)
- 핵심 발견:
  - `frontend/js/sqm-inline.js`가 **단일 번들** (3469줄, 모듈 코드는 죽은 코드)
  - `backend/api/menubar.py`는 634줄 NotReadyError 스텁 (사용 안 됨)
  - PDF 입고 슬롯: v864-2 = 4, v864-3 = 1 (확정)

### Phase 3 — Gap 분석 마스터
- `v864_comparison/gap_report.md` — **시작점 마스터 보고서**
- `v864_comparison/gap_matrix.json` — 128행 정량 매트릭스
- `v864_comparison/porting_plan.md` — Sprint 단위 백로그

전체 추정: **155 dev-days** (P0 14건 70일 + P1 22건 60일 + P2 13건 20일 + 아키텍처 5일)

---

## 4. ✅ 완료된 작업 — 13개 커밋

### Sprint 0 (정리)
- **`369f0c3`** chore(sprint-0): clean up dead code + restore v864-2 L1 menu structure
  - `backend/api/menubar.py` 삭제 (634줄 NotReadyError 스텁)
  - 의존성 5곳 정리 (`__init__.py`, `sqm-inline.js`, 3 test files, `verify_endpoints.py`)
  - L1 메뉴 v864-2 순서 복원: 파일→입고→출고→재고→보고서→검색→설정/도구→도움말
  - 9개 placeholder ENDPOINTS 추가 (`u:'wip'`)

### Sprint 0-3b (시각적 매칭) + Sprint 1-1 시작
- **`28ce4e7`** feat(sprint-1-1+0-3b-fix): Allocation tab full redesign + menu structure corrections
  - 사이드바 복구 (이전 잘못된 hide 되돌림)
  - **파일 메뉴 cascading 서브메뉴** (22 flat → 6 + hover-expand: 내보내기▶, 백업▶, BL 선사 도구▶, Gemini AI▶)
  - **Allocation 탭 전면 재설계**:
    - 9열 테이블 (LOT/SAP/PRODUCT/QTY/CUSTOMER/SALE REF/OUTBOUND/WH/STATUS)
    - 7버튼 액션 툴바
    - 상태 필터 (전체/RESERVED/PICKED/SOLD)
    - 다중선택 + 일괄 취소
    - TotalFooter

### Sprint 1-2 OneStop Inbound (4-단계 완성)
- **`a2b76f1`** feat(sprint-1-2-a): OneStop Inbound 4-slot modal frontend skeleton
  - `showOneStopInboundModal()` 작성 (기존 `showPdfInboundUploadModal` 대체)
  - 4단계 wizard, 4 업로드 슬롯, 18열 미리보기 테이블 뼈대
- **`c4c2d68`** feat(sprint-1-2-b): OneStop Inbound backend /onestop-upload + 4-doc cross-check
  - `POST /api/inbound/onestop-upload` 신규
  - `parsers.cross_check_engine` 활용
  - 18열 preview_rows 조립 + 결과 표시
- **`0745448`** feat(sprint-1-2-c): OneStop Inbound inline edit + dry_run/save split
  - `dry_run=True` 추가 (DB 저장 분리)
  - `POST /api/inbound/onestop-save` 신규 (편집된 rows 저장)
  - 18열 더블클릭 인라인 편집 (16개 컬럼 편집 가능)
- **`b420b1e`** feat(sprint-1-2-d): OneStop Inbound Undo/Redo (max 50) + D/O manual input
  - **Undo/Redo 스택 max 50 + Ctrl+Z/Y 단축키**
  - 편집 툴바 (↶ 되돌리기, ↷ 다시실행, ⟲ 원본 초기화)
  - D/O 나중에 → 3-step prompt (Free Time / 창고 / 도착일)
  - 자동으로 빈 셀 채우기 + 편집 뱃지

### UX 강화
- **`a23f06a`** feat(ux): global ESC key to dismiss modal/menu/context-menu
  - 우선순위: 컨텍스트 메뉴 → 모달 → 메뉴 드롭다운 → input 포커스
- **`c59ed8a`** feat(ux): modal Enter/Tab/double-ESC keyboard enhancements
  - Enter → primary 버튼 자동 클릭 (textarea/select 제외)
  - Tab → 모달 내 포커스 트랩
  - 더블 ESC (1.5초 내) → 앱 종료 확인

### Sprint 1-1 Allocation 마무리
- **`e125211`** feat(sprint-1-1-d+e): Allocation inline edit + context menu + 3 state-transition endpoints
  - 백엔드 4개 신규: `PATCH /api/allocation/{lot}` (4 fields), `/pick`, `/confirm`, `/reset`
  - 프론트: 더블클릭 인라인 편집 (4 컬럼: customer/sale_ref/qty_mt/outbound_date)
  - 우클릭 컨텍스트 메뉴 (행 복사 CSV / 취소 / 초기화)
  - 3개 [준비중] 버튼 → 실제 엔드포인트 연결

### Sprint 1-3 OneStop Outbound (Phase A/B/C 완료, D/E 남음)
- **`1a9d044`** feat(sprint-1-3-a): OneStop Outbound 4-tab wizard shell + Tab 1 + state machine
  - 4탭 Notebook UI + 상태바 + 5단계 상태머신
  - State: DRAFT → WAIT_SCAN → (FINALIZED | REVIEW | ERROR)
  - Tab 1 완전 구현 (근거문서 multi-file / 고객사·Sale Ref·LOT / 수동 실제수량 / paste textarea / 샘플 삽입 / 파싱→DRAFT)
- **`8be7aa0`** feat(sprint-1-3-b): OneStop Outbound Tab 2 — tonbag selection + DRAFT→WAIT_SCAN
  - LOT별 펼침형 톤백 Treeview
  - 🎲 랜덤 선택 (Fisher-Yates + qty_kg target)
  - ✅ 전체 / ☐ 해제 / ▼ 모두 펼침 / ▶ 모두 접기
  - DRAFT → WAIT_SCAN 전환
- **`c2158da`** feat(sprint-1-3-c): OneStop Outbound Tab 3 — OUT scan validation + hard-stop
  - 백엔드: `POST /api/outbound/onestop-scan-parse` (csv/xlsx multipart)
  - 자동 인코딩 (utf-8-sig + cp949)
  - 자동 컬럼 매핑 (tonbag_uid/sub_lt/id, actual_kg/weight)
  - 4단계 검증 룰:
    - `actual > expected` → 🚫 즉시 하드스톱
    - `|편차| > 5%` → 🚫 STOP
    - `0.5% < |편차| ≤ 5%` → ⚠️ WARN
    - `|편차| ≤ 0.5%` → ✅ OK
  - 7열 결과 테이블 (색상 구분)
  - WAIT_SCAN → FINALIZED ▶ (하드스톱 시 disabled)

---

## 5. 🟡 남은 작업

### Sprint 1-3 잔여 (Outbound 마무리, 3일)

#### Sprint 1-3-D — Tab 4 완료 + 감사 로그 sub-popup (2일)
**필요 작업**:
- Tab 4 placeholder 교체:
  - 📦 확정건 출고 완료 ▶ — 실제 출고 처리 (engine.confirm_outbound 호출)
  - ✅ 승인 → FINALIZED 버튼
  - 완료 이력 Treeview (5+ cols: 시간/LOT/톤백수/고객/상태)
  - 📋 감사 로그 sub-popup
- v864-2 onestop_outbound.py 라인 ~2200~2300 부근 참조
- 백엔드:
  - 기존 `/api/outbound/confirm` 활용 가능
  - 새 `/api/outbound/audit-log?from=&to=&type=` 추가 필요
  - audit_log 테이블에서 조회

#### Sprint 1-3-E — Proof docs 저장소 (1일)
- 근거문서 (Tab 1에서 첨부한 multi-file) → `data/proof_docs/YYYY-MM-DD/` 저장
- 90일 자동 정리 cron 또는 시작 시 1회 cleanup
- 새 백엔드: `POST /api/outbound/proof-upload` (multi-file)

### Sprint 1-4 ~ 1-14 (P0 5건, ~30일)

#### Sprint 1-4 — IntegrityV760 다이얼로그 (5일)
- v864-2 source: `dialogs/integrity_v760_dialog.py` (387줄, geometry 1060×660)
- 6개 요약 카드 (전체 LOT / 🔴오류 / 🟡경고 / ✅정상 / ⚠️부분출고 / 📊Alloc 이상)
- 6열 LOT 테이블 (신호등 색상 — error red / warning yellow / ok green)
- 선택 LOT 상세 패널 (read-only Text)
- 새 백엔드: `GET /api/action/integrity-report` (별도 엔드포인트, 현재 `/integrity-check`만 있음)
- 새 백엔드: `POST /api/action/fix-integrity` (자동 복구)
- 현재 v864-3에서 `onIntegrityReport`와 `onFixLotIntegrity`가 같은 endpoint를 가리킴 — **분리 필요**

#### Sprint 1-5 — LOT Detail 3탭 다이얼로그 (5일)
- v864-2 source: `dialogs/lot_detail_dialog.py` (359줄) + `lot_allocation_audit_mixin.py` (312줄)
- 3개 Notebook 탭: 📦 톤백 현황, 📋 이동 이력, 📊 Allocation·배정
- 톤백 9 cols (No./톤백#/중량/상태/구분/위치/출고처/출고지정일/출고완료일)
- 이동 이력 8 cols (No./유형/일시/수량/이전잔량/이후잔량/참조번호/비고)
- 행 색상 태그 (available/picked/shipped/depleted/sample)
- Inventory 테이블 더블클릭으로 진입 (Sprint 1-6과 함께)

#### Sprint 1-6 — Inventory 24열 풀 기능 (7일)
- 현재 v864-3 Inventory 22 cols flat (정렬/필터/컨텍스트 없음)
- v864-2 24 cols + 정렬 ▲▼ + 헤더 필터 + 상태 필터 + 컨텍스트 메뉴 + 컬럼 토글
- 4 토글 가능 톤백 카운터 (↓Avail개 / ↓Resv개 / ↓Pick개 / ↓Sold개)
- ⚙️ 열 선택 토글 (localStorage 영구화)

#### Sprint 1-7 — Scan 5버튼 상태 전환 (3일)
- 현재 v864-3 3버튼 (Inbound/Outbound/Move)
- v864-2 5버튼:
  - 배정 등록 (AVAILABLE→RESERVED)
  - 화물 결정 (RESERVED→PICKED)
  - 출고확정 (PICKED→OUTBOUND)
  - 반품등록 (OUTBOUND→RETURN)
  - 재입고 (RETURN→AVAILABLE)
- ⚡ 빠른 스캔 toggle, 🔕 무음 toggle, auto-complete

#### Sprint 1-8 — Picked 탭 6버튼 (2일)
- 현재 1버튼만 있음
- 추가: revert RESERVED, Excel export, 전체 선택, LOT 리스트로

#### Sprint 1-9 — Outbound 탭 6버튼 (2일)
- 현재 1버튼만 있음
- 추가: revert PICKED, 반품 확정, Excel export, 판매 보기, 날짜 필터

#### Sprint 1-10~14 — 작은 P0 (각 1~2일, 총 10일)
- ManualInboundPreviewDialog 풀 (9 cols + 인라인 편집)
- DOUpdateDialog 풀 (PDF 업로드 + 6열 테이블)
- PickingListPreviewDialog 풀 (요약 + 경고 + 2개 항목 테이블)
- LocationUploadPreviewDialog
- 기타

### Sprint 2 (P1, 22건, 60일)
- **InboundTemplateDialog** 풀 CRUD (5일) ← **OneStop Inbound 템플릿 의존**
- **PickingTemplateDialog** CRUD (5일)
- **DNCheckDialog** 사이드-바이-사이드 비교 (3일)
- **ReturnInboundPreviewDialog** (3일)
- **ReturnStatisticsDialog** 차트 + 필터 (3일)
- **InboundHistoryDialog** (3일)
- **SettingsDialogMixin** API 키 + 선사 BL/DO 규칙 (5일) ← `tb-settings` dead 버튼 해결
- **전역 🔍 검색** 구현 (2일) ← 현재 placeholder
- **🚢 BL 선사 도구** 서브메뉴 2개 (5일)
- **Sales Order 업로드** (2일)
- **Swap 리포트** (2일)
- **재고 알림 조회** (2일)
- **📋 보고서 양식/이력** (잘못된 endpoint 수정 + UI, 6일)
- **Move 탭 보강** (Lookup/Clear/Approval, 3일)
- **Return Cargo Overview** 20열 (3일)
- **감사 로그 뷰어 다이얼로그** (3일)

### Sprint 3 (P2, 13건, 20일)
- ShortcutGuideDialog (2일)
- EmailConfigDialog 11필드 (2일)
- AutoBackupSettingsDialog (3일)
- 컬럼 가시성 토글 모든 탭 (1일)
- 테마 variants (1일)
- 창 크기 저장/초기화 (1일)
- 재고 추이 차트 `onStockTrendChart` (2일)
- Welcome/Feedback (1일)
- PDF 도구 4분할 (1일)
- 파싱 오류 복구 9 ERROR_CODES (3일)
- 종료 확인 다이얼로그 (0.5일)
- 기타 polish

### Phase 2 (선택적, 5~15일)
- Gemini AI 서브메뉴 전체 (현재 placeholder)
- 또는 모바일 반응형, 클라우드 배포 등

---

## 6. 🎓 다음 AI를 위한 핸드오프 가이드

### 6.1 시작하기
1. 이 문서 전체 읽기
2. `v864_comparison/gap_report.md` 읽기 (Phase 3 마스터)
3. `v864_comparison/porting_plan.md` 읽기 (Sprint 백로그)
4. `Claude_SQM_v864_2/analysis/v864-2_dialogs.md` 읽기 (참조 다이얼로그 카탈로그)
5. git log 확인: 최근 13개 커밋 메시지 검토
6. 사용자에게 "어느 작업부터 진행할까요?" 묻기

### 6.2 작업 원칙 (사용자 학습 결과)

#### 절대 원칙
- **v864-2 코드는 수정 금지** — 참조만, 모든 변경은 v864-3 안에서
- **로직 100% 동일** — UI 형태만 다르게, 결과는 같게
- 수정 전 **항상 v864-2 원본 확인** (해당 다이얼로그/탭 코드)
- 서브에이전트 추출 결과는 **반드시 사용자 스크린샷으로 교차검증**

#### 작업 순서 권장
1. **순차 진행** (사용자 선호) — 한 기능 100% 완성 후 다음
2. **반쪽짜리 누적 금지** — 사용자가 답답해함
3. **placeholder는 명시적으로** — "Sprint X 예정" 토스트로 경계 분명히
4. **커밋은 logical unit 별로** — 한 Sprint phase = 한 커밋

#### 코드 스타일
- **JS**: ES5 호환 (var/function — 화살표 함수 X) 유지 — 기존 sqm-inline.js 패턴
- **CSS**: 기존 var(--xxx) 토큰 사용
- **Python**: type hints 사용 (Optional, Dict, List)
- **커밋 메시지**: feat(sprint-X-Y): ... 형식 + Co-Authored-By 끝에

#### 사용자 의사소통
- **답답함 신호**: "이상해", "안돼", "차이 나" → 즉시 사과 + 확인 + 수정
- **추천안 같이 제시** — "어떻게 할까요?" 보다 "추천: A. 이유: ..."
- **진행 상황 명확히** — 매 단계 완료/대기 표시
- **솔직한 한계 인정** — 모르는 건 "확인 필요" 표현
- 한국어로 응답 (사용자 모국어)

### 6.3 자주 사용하는 패턴

#### 새 모달 만들기
```javascript
function showXxxModal() {
  var html = ['<div style="max-width:...">', '...HTML...', '</div>'].join('');
  showDataModal('', html);
  // 이벤트 핸들러 등록
}
window.showXxxModal = showXxxModal;
```

#### 새 ENDPOINTS 추가
```javascript
// sqm-inline.js의 ENDPOINTS 객체에 추가:
'onXxx': {m:'JS', u:'wip', lbl:'준비 중'},  // placeholder
'onXxx': {m:'GET', u:'/api/...', lbl:'...'},  // 실제
'onXxx': {m:'POST', u:'/api/...', lbl:'...'},
```

#### 백엔드 새 엔드포인트
```python
# backend/api/<file>.py
from fastapi import APIRouter, Body
from typing import Dict, Any

@router.post("/new-endpoint")
def new_endpoint(payload: Dict[str, Any] = Body(...)):
    # ...
    return {"ok": True, "data": {...}}
```
include는 자동 (`__init__.py`가 router 자동 로드)

#### 인라인 셀 편집 (재사용 패턴)
참조: `sqm-inline.js`의 `onestopEditCell` 또는 `allocEditCell`

#### Undo/Redo 스택 (재사용 패턴)
참조: `_onestopState.history` + `onestopUndo/Redo`

### 6.4 알려진 이슈

1. **Gemini API key**:
   - `parse_do`는 **Gemini 필수**
   - `parse_bl`/`parse_packing_list`/`parse_invoice`는 로컬 파서 우선 + Gemini fallback
   - 사용자는 `settings.ini`의 `[Gemini] api_key = ...` 설정해둔 상태
   - `config.py`가 자동으로 keyring으로 마이그레이션

2. **PyMuPDF 경고**: 
   - 콘솔에 가끔 `pdf_parser not available (PyMuPDF missing?)` 경고 — 실제로는 설치돼 있음 (legacy 모듈 경고). 무시 OK.

3. **죽은 코드**:
   - `frontend/js/main.js`, `frontend/js/handlers/`, `frontend/js/pages/`, `frontend/js/router.js` — 사용 안 됨
   - 실제로는 `frontend/js/sqm-inline.js` 단일 번들이 동작
   - Sprint 0에서 정리 검토했으나, 모듈 분리는 미루고 monolith 유지 결정 (사용자 선호)

4. **wrong endpoint mis-wires** (Phase 3에서 발견, 아직 미수정):
   - `onReportTemplates` → `/api/q/audit-log` (잘못됨)
   - `onReportHistory` → `/api/q/audit-log` (잘못됨)
   - `onIntegrityReport`와 `onFixLotIntegrity`가 같은 endpoint
   - Sprint 2에서 수정 예정

5. **Settings 버튼**:
   - `tb-settings`는 Sprint 0에서 제거됨 (구 `/api/menu/-on-settings` NOT_READY)
   - Sprint 2에서 `SettingsDialogMixin` 풀 포팅 시 복원

### 6.5 테스트 방법

#### 백엔드 + WebView 실행
```powershell
cd D:\program\SQM_inventory\Claude_SQM_v864_3
python main_webview.py
```
- 데스크톱 창 실행
- 백엔드는 자동으로 localhost:?(랜덤 포트)
- 콘솔에 INFO 로그 흐름

#### 정적 HTML 미리보기 (백엔드 없이 UI만)
- `D:\program\SQM_inventory\Claude_SQM_v864_3\frontend\index.html` 더블클릭
- 메뉴/모달 UI 확인 가능 (API 호출은 실패)

#### 환경변수 설정 확인
```powershell
echo $env:GEMINI_API_KEY
```
없으면 settings.ini fallback 사용됨

#### 구문 검증 (커밋 전)
```powershell
cd D:\program\SQM_inventory\Claude_SQM_v864_3
node -e "const fs=require('fs'); new Function(fs.readFileSync('frontend/js/sqm-inline.js','utf8')); console.log('JS OK')"
python -c "import ast; ast.parse(open('backend/api/inbound.py',encoding='utf-8').read()); print('Python OK')"
```

#### Git 워크플로우
```powershell
# 변경 파일만 명시적 추가 (다른 폴더 M 파일 섞이지 않게)
git add frontend/js/sqm-inline.js backend/api/...

# 커밋 메시지 형식
git commit -m "feat(sprint-X-Y): ..."

# 푸시
git push
```

---

## 7. 📐 v864-2 → v864-3 매핑 표 (자주 참조)

| v864-2 (Tkinter) | v864-3 (WebView) | 상태 |
|---|---|---|
| `dialogs/onestop_inbound.py` | `sqm-inline.js`의 `showOneStopInboundModal()` | ✅ 100% |
| `dialogs/allocation_dialog.py` | Allocation 탭 + `loadAllocationPage()` | ✅ 100% |
| `dialogs/onestop_outbound.py` | `showOneStopOutboundModal()` | 🟡 60% (Phase A/B/C 완료, D/E 남음) |
| `dialogs/integrity_v760_dialog.py` | (없음) | ❌ Sprint 1-4 |
| `dialogs/lot_detail_dialog.py` | (없음, Inventory 행 Detail 버튼만) | ❌ Sprint 1-5 |
| `tabs/inventory_tab.py` (24열) | `loadInventoryPage` (22열, no sort/filter) | ❌ Sprint 1-6 |
| `tabs/scan_tab.py` (5버튼) | `loadScanPage` (3버튼) | ❌ Sprint 1-7 |
| `dialogs/inbound_template_dialog.py` | (placeholder) | ❌ Sprint 2 |
| `dialogs/picking_template_dialog.py` | (placeholder) | ❌ Sprint 2 |
| `dialogs/dn_cross_check_dialog.py` | (없음) | ❌ Sprint 2 |
| `dialogs/return_inbound_preview_dialog.py` | (없음) | ❌ Sprint 2 |
| `dialogs/return_statistics_dialog.py` | (없음) | ❌ Sprint 2 |
| `dialogs/inbound_history_dialog.py` | (없음) | ❌ Sprint 2 |
| `dialogs/settings_dialog.py` (API 키 + BL 규칙) | (제거됨) | ❌ Sprint 2 |
| `gui_app_modular/mixins/menu_mixin.py` 🔍 검색 | (placeholder 버튼만) | ❌ Sprint 2 |

### Backend 엔드포인트 — 신규 추가 분 (이번 세션)

| Method | URL | 추가 시점 | 설명 |
|---|---|---|---|
| POST | `/api/inbound/onestop-upload?dry_run=` | 1-2-B/C | 4종 multipart + 크로스체크 |
| POST | `/api/inbound/onestop-save` | 1-2-C | 편집된 18열 → DB 저장 |
| PATCH | `/api/allocation/{lot}` | 1-1-D | 4 필드 업데이트 |
| POST | `/api/allocation/{lot}/pick` | 1-1-E | RESERVED → PICKED |
| POST | `/api/allocation/{lot}/confirm` | 1-1-E | PICKED → SOLD |
| POST | `/api/allocation/{lot}/reset` | 1-1-E | 배정 완전 초기화 |
| POST | `/api/outbound/onestop-scan-parse` | 1-3-C | OUT 스캔 csv/xlsx 파싱 |

### 기존 활용 (이번 세션에 추가 안 함)
- `GET /api/q/allocation-summary`, `/api/q/allocation-detail/{lot}` — Allocation 조회
- `GET /api/tonbags?lot_no=&status=` — Outbound Tab 2 톤백 조회
- `POST /api/inbound/pdf-upload` — Inbound legacy single-PDF
- `POST /api/outbound/quick`, `/api/outbound/confirm` — 기존 출고
- `parsers.document_parser_modular.DocumentParserV3` — 4종 PDF 파서 (재사용)
- `parsers.cross_check_engine.cross_check_documents` — 크로스체크 엔진 (재사용)

---

## 8. 📈 진행률 요약

```
P0 14건:     █████████░░░░░  64% (9건 완료 / 14건)
  Sprint 1-1 Allocation:    ████████████ 100% ✅
  Sprint 1-2 OneStop Inbound: ████████████ 100% ✅
  Sprint 1-3 OneStop Outbound: ████████░░░░  60% (A/B/C 완료, D/E 남음)
  Sprint 1-4~14:              ░░░░░░░░░░░░   0%

P1 22건:     ░░░░░░░░░░░░░░   0%
P2 13건:     ░░░░░░░░░░░░░░   0%

전체 155일:  ███░░░░░░░░░░░  ~22일 완료 / 155일 (14%)
```

---

## 9. ⚡ 즉시 실행 가능한 작업 (다음 AI가 받자마자 가능)

### 옵션 A: Sprint 1-3-D (가장 자연스러움, 2일)
Tab 4 완료 — Outbound 거의 완성
1. v864-2 `onestop_outbound.py` Tab 4 부분 읽기
2. 현재 placeholder를 실제 UI로 교체
3. `/api/outbound/confirm` 활용
4. 새 `/api/outbound/audit-log` 추가
5. 감사 로그 sub-popup 구현

### 옵션 B: Sprint 1-4 IntegrityV760 (다른 P0, 5일)
6 카드 + 신호등 + 6열 다이얼로그
1. v864-2 `integrity_v760_dialog.py` (387줄) 분석
2. 새 `showIntegrityV760Modal` 작성
3. `onIntegrityReport`와 `onFixLotIntegrity` endpoint 분리
4. 새 `/api/action/integrity-report` (read-only)
5. 새 `/api/action/fix-integrity` (mutating)

### 옵션 C: Sprint 1-6 Inventory 24열 (가장 큰 P0, 7일)
사용자가 가장 많이 보는 탭 풀 기능
1. `loadInventoryPage` 재작성
2. 24 cols + 정렬 ▲▼ + 헤더 필터
3. 컨텍스트 메뉴 + 컬럼 토글 + 상태 필터
4. localStorage 영구화

### 다음 AI에게 추천 답변 템플릿

```
받았습니다. 이 핸드오프 문서를 통해 컨텍스트 파악 완료.

현재 상태:
- 13개 커밋 완료 (369f0c3 → c2158da)
- Inbound 100% / Allocation 100% / Outbound 60%
- 남은 P0 5.5건 + P1 22건 + P2 13건

다음 작업 옵션:
A. Sprint 1-3-D Tab 4 완료 (2일) — Outbound 마무리
B. Sprint 1-4 IntegrityV760 (5일)
C. Sprint 1-6 Inventory 24열 (7일)

추천: A — Outbound가 거의 완성이라 그대로 마무리하는 게 깔끔.
어떻게 진행할까요?
```

---

## 10. 📞 사용자 컨택 정보

- 이름: 남기동 (Nam Kidong)
- 이메일: kidong.nam@gmail.com
- 모국어: 한국어
- 위치: Windows 11 + PowerShell 환경
- 특성:
  - 비기술자 또는 초급 (코드 직접 안 씀)
  - 결정 빠름 ("OK", "진행해" 식)
  - 답답함 표현 명확 (도움 요청 신호)
  - 시각 비교 좋아함 (스크린샷 많이 공유)
  - 추천안 + 이유 같이 제시받는 걸 선호

---

## 11. 🏁 마무리

이 문서는 **2026-04-25 시점**의 작업 핸드오프입니다.

**다음 AI 또는 작업자**:
1. 이 문서 + `v864_comparison/` 3개 파일을 먼저 다 읽어주세요
2. 사용자에게 "Sprint 1-3-D 진행" 여부 묻기
3. 작업 진행 시 매 Phase 완료 후 커밋 + 푸시
4. 사용자 피드백에 답답함 보이면 즉시 멈추고 확인
5. 새로운 핸드오프 문서를 정기적으로 갱신 (이 문서 형식 그대로)

**리포지토리**: https://github.com/kidongnam1/sqm_2/tree/claude/v864-3-sprint0
**시작 커밋**: 다음 작업 시작 시 `c2158da`에서 출발

성공적인 인계가 되기를 바랍니다. 행운을 빕니다!

— Claude (이번 세션 담당)
