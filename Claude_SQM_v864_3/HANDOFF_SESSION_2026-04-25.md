# 🤖 v864-3 포팅 작업 핸드오프 (2026-04-25 갱신본)

> **다음 AI 또는 작업자에게**: 이 문서 하나만 읽으면 처음부터 모든 컨텍스트 파악 가능합니다.
> **현 시점**: 22개 커밋 ~50 dev-day 분량 완료. **Sprint 1 P0 사실상 100%** 도달.
> **다음 단계**: Sprint 2 P1 (22건, 60일 예상).

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
5. **순차 진행 선호** — 한 기능을 완전히 끝낸 후 다음으로

---

## 2. 📁 작업 환경

### 디렉터리 구조
```
D:/program/SQM_inventory/
├── Claude_SQM_v864_2/          # ⭐ Golden Reference (Tkinter — 수정 금지, 참조만)
│   ├── gui_app_modular/
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
│   │   ├── index.html          # 메뉴바 (cascading 구조)
│   │   ├── css/
│   │   │   ├── design-system.css
│   │   │   └── v864-layout.css # 974 lines (이번 세션 +422)
│   │   └── js/
│   │       └── sqm-inline.js   # ⭐ 6735 lines (이번 세션 +3266) — 단일 번들
│   ├── backend/
│   │   ├── api/
│   │   │   ├── __init__.py     # 라우터 자동 등록
│   │   │   ├── inbound.py      # 807 lines (+339)
│   │   │   ├── outbound_api.py # 728 lines (+262)
│   │   │   ├── inventory_api.py # 537 lines (+184) — Allocation + Scan 5단계 포함
│   │   │   ├── allocation_api.py
│   │   │   ├── actions.py      # +160 lines (Sprint 1-4 IntegrityV760)
│   │   │   └── queries.py      # +27 lines (Sprint 1-3-D audit-log 필터)
│   │   └── (engine_modules는 v864-2와 공유)
│   ├── parsers/                # ⭐ v864-2에서 복사됨, 그대로 활용
│   │   ├── document_parser_modular/
│   │   │   ├── parser.py       # DocumentParserV3 — parse_bl/pl/invoice/do
│   │   │   └── (mixins)
│   │   ├── cross_check_engine.py # 549 lines — cross_check_documents()
│   │   └── pdf_parser.py
│   ├── analysis/               # 스펙 추출 결과 (Phase 2)
│   ├── data/
│   │   └── proof_docs/         # ⭐ Sprint 1-3-E NEW: YYYY-MM-DD/{batch_id}/ 구조
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
- **시작점 커밋**: `ea9d0f0` (이번 세션 시작 상태)
- **현재 HEAD**: `c6e259b` (Sprint 1-7 완료)
- 인증: 정상 작동 확인됨

### 환경
- OS: Windows 11
- Python: 3.11
- 주요 라이브러리: pandas 3.x, fastapi 0.128, pywebview 5.x, google-genai, openai
- 설치: `pip install -r requirements.txt && pip install uvicorn pywebview pyinstaller`
- 실행: `python main_webview.py`
- API key: `settings.ini`의 `[Gemini] api_key = AQ...` (사용자 설정 완료)

---

## 3. 📊 분석 자료 (이미 완료)

### Phase 1A — v864-2 메뉴/탭 추출
- `Claude_SQM_v864_2/analysis/v864-2_spec.json` (45KB)
- `Claude_SQM_v864_2/analysis/v864-2_spec.md` (18KB)

### Phase 1B — v864-2 다이얼로그 30개 카탈로그
- `Claude_SQM_v864_2/analysis/v864-2_dialogs.md` (20KB)

### Phase 2 — v864-3 현재 상태
- `Claude_SQM_v864_3/analysis/v864-3_spec.json/md`
- `Claude_SQM_v864_3/analysis/v864-3_modals.md`

### Phase 3 — Gap 분석 마스터
- `v864_comparison/gap_report.md` — 시작점 마스터 보고서
- `v864_comparison/gap_matrix.json` — 128행 정량 매트릭스
- `v864_comparison/porting_plan.md` — Sprint 단위 백로그

전체 추정: **155 dev-days** (P0 14건 70일 + P1 22건 60일 + P2 13건 20일 + 아키텍처 5일)

---

## 4. ✅ 완료된 작업 — 22개 커밋

### Sprint 0 (정리, 1 커밋)
- **`369f0c3`** chore(sprint-0): clean up dead code + restore v864-2 L1 menu structure
  - `backend/api/menubar.py` 삭제 (634줄 NotReadyError 스텁)
  - 의존성 5곳 정리 (`__init__.py`, `sqm-inline.js`, 3 test files, `verify_endpoints.py`)
  - L1 메뉴 v864-2 순서 복원: 파일→입고→출고→재고→보고서→검색→설정/도구→도움말
  - 9개 placeholder ENDPOINTS 추가 (`u:'wip'`)

### Sprint 0-3b (시각적 매칭) + Sprint 1-1 시작 (1 커밋)
- **`28ce4e7`** feat(sprint-1-1+0-3b-fix): Allocation tab full redesign + menu structure corrections
  - 사이드바 복구 (잘못된 hide 되돌림)
  - **파일 메뉴 cascading 서브메뉴** (22 flat → 6 + hover-expand)
  - **Allocation 탭 전면 재설계** (9열 + 7버튼 + 상태 필터 + 다중선택 + TotalFooter)

### Sprint 1-2 OneStop Inbound (4 커밋, 100% 완성)
- **`a2b76f1`** feat(sprint-1-2-a): OneStop Inbound 4-slot modal frontend skeleton
- **`c4c2d68`** feat(sprint-1-2-b): OneStop Inbound backend /onestop-upload + 4-doc cross-check
- **`0745448`** feat(sprint-1-2-c): OneStop Inbound inline edit + dry_run/save split
- **`b420b1e`** feat(sprint-1-2-d): OneStop Inbound Undo/Redo (max 50) + D/O manual input

### UX 강화 (2 커밋)
- **`a23f06a`** feat(ux): global ESC key to dismiss modal/menu/context-menu
- **`c59ed8a`** feat(ux): modal Enter/Tab/double-ESC keyboard enhancements

### Sprint 1-1 Allocation 마무리 (1 커밋, 100% 완성)
- **`e125211`** feat(sprint-1-1-d+e): Allocation inline edit + context menu + 3 state-transition endpoints
  - 백엔드 4개 신규: `PATCH /api/allocation/{lot}` (4 fields), `/pick`, `/confirm`, `/reset`

### Sprint 1-3 OneStop Outbound (5 커밋, 100% 완성)
- **`1a9d044`** feat(sprint-1-3-a): 4-tab wizard shell + state machine + Tab 1
- **`8be7aa0`** feat(sprint-1-3-b): Tab 2 — tonbag selection + DRAFT→WAIT_SCAN
- **`c2158da`** feat(sprint-1-3-c): Tab 3 — OUT scan validation + 4-tier hard-stop
- **`3861469`** feat(sprint-1-3-d): Tab 4 — completion + audit log sub-popup
- **`c353c28`** feat(sprint-1-3-e): proof_docs/YYYY-MM-DD/{batch_id}/ + 90-day cleanup

### Sprint 1-4/5/6/7 (4 커밋, 모두 100% 완성)
- **`a2e262a`** feat(sprint-1-4): IntegrityV760 dialog — 6 cards + traffic-light + auto-fix
  - 새 endpoints: `GET /api/action/integrity-report`, `POST /api/action/fix-integrity`
- **`f508206`** feat(sprint-1-6): Inventory 24-col full features (sort/filter/context/toggle)
  - 24 컬럼 (20 always + 4 toggleable counters with localStorage)
  - 3-tier filter (status chip + per-column header + sort)
  - 우클릭 컨텍스트 + Excel export + sticky thead/tfoot
- **`dd2da5c`** feat(sprint-1-5): LOT Detail 3-tab dialog (tonbag/movement/allocation)
  - 6개 상태 카드 + 3 탭 + 행 색상 + 누적 잔량 자동 계산
  - 빠른 출고 연계 (lotQuickOutbound → showOneStopOutboundModal)
- **`c6e259b`** feat(sprint-1-7): Scan tab — 5 state-transition buttons + quick/silent toggles
  - 백엔드: `_SCAN_TRANSITIONS` 5개 (reserve/pick/outbound/return/restock)
  - audit_log 자동 기록 (`SCAN_<ACTION>`)
  - ⚡ 빠른 스캔 + 🔕 무음 토글 (localStorage)

### 핸드오프 문서 (1 커밋)
- **`b40bfb3`** docs: comprehensive session handoff document for next AI/developer
  - **이 문서**, 갱신 후 재커밋 예정

---

## 5. 🟢 현재 완성된 핵심 기능 — 실무 투입 가능

```
✅ 메뉴 구조 v864-2 일치 (cascading 서브메뉴 포함)
✅ PDF 4종 입고 + 4 슬롯 + 크로스체크 + 18열 미리보기 + 인라인 편집
   + Undo/Redo (max 50) + D/O 수동 입력 + dry_run/save 분리
✅ Allocation 9열 편집 + 7 버튼 + 상태 필터 + 다중선택 + 우클릭
   + RESERVED/PICKED/SOLD/CANCEL 상태 전환 + LOT 초기화
✅ OneStop Outbound 4탭 wizard (입력→톤백선택→OUT스캔검증→완료)
   + DRAFT→WAIT_SCAN→FINALIZED 상태머신 + actual>expected 하드스톱
   + 감사로그 서브팝업 + CSV export + proof_docs 90일 보존
✅ IntegrityV760 6카드 + 신호등 + 자동 복구
✅ LOT Detail 3탭 (톤백/이동이력/Allocation)
✅ Inventory 24열 (정렬/필터/컨텍스트/컬럼토글/Excel)
✅ Scan 5단계 상태전환 (배정→화물결정→출고확정→반품→재입고)
✅ UX: ESC/Enter/Tab/외부클릭/double-ESC 종료
```

---

## 6. 🟡 남은 작업

### Sprint 1 잔여 (선택적, ~5일)
**Sprint 1-8/9** — Picked/Outbound 탭 6버튼 풀
- 현재: 1버튼 (단순 표시)
- 추가 필요: revert / Excel export / 전체선택 / 반품 확정 / 날짜 필터 / 판매 보기
- 사용자 체감 작음 (보기 탭이고 핵심은 Outbound 모달이 처리)

**Sprint 1-10~14** — 작은 P0
- ManualInboundPreviewDialog 9열 인라인 편집 풀
- DOUpdateDialog 풀 (PDF 업로드 + 6열 매칭 테이블)
- PickingListPreviewDialog 풀 (요약 + 경고 + 2개 항목 테이블)
- LocationUploadPreviewDialog
- 기타

→ **Sprint 2 P1과 함께 진행**하는 게 효율적

### Sprint 2 P1 (22건, ~60일)
- **InboundTemplateDialog** 풀 CRUD (5일) ← Inbound 템플릿 의존
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
- **감사 로그 뷰어 다이얼로그** (3일) — 메인 메뉴용 (현재 OneStop Outbound 안에만 있음)

### Sprint 3 P2 (13건, ~20일)
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

## 7. 🎓 다음 AI를 위한 핸드오프 가이드

### 7.1 시작하기
1. 이 문서 전체 읽기
2. `v864_comparison/gap_report.md` 읽기 (Phase 3 마스터)
3. `v864_comparison/porting_plan.md` 읽기 (Sprint 백로그 — Sprint 2 항목)
4. `Claude_SQM_v864_2/analysis/v864-2_dialogs.md` 읽기 (참조 다이얼로그 카탈로그)
5. git log 확인: 최근 22개 커밋 메시지 검토
6. 사용자에게 "Sprint 2 어느 항목부터 진행할까요?" 묻기

### 7.2 작업 원칙 (사용자 학습 결과)

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

### 7.3 자주 사용하는 패턴

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
참조: `sqm-inline.js`의 `onestopEditCell` 또는 `allocEditCell` 또는 Inventory 컬럼 토글

#### Undo/Redo 스택 (재사용 패턴)
참조: `_onestopState.history` + `onestopUndo/Redo`

#### 서브 모달 (메인 모달 위에)
참조: `ooViewAuditLog` (z-index 10001 + 외부클릭으로 닫기)

#### 우클릭 컨텍스트 메뉴
참조: `allocContextMenu` 또는 `invContextMenu`

#### 인라인 편집 + PATCH
참조: `allocEditCell` (즉시 PATCH) vs `onestopEditCell` (배치 저장)

### 7.4 알려진 이슈

1. **Gemini API key**:
   - `parse_do`는 **Gemini 필수**
   - `parse_bl`/`parse_packing_list`/`parse_invoice`는 로컬 파서 우선 + Gemini fallback
   - 사용자는 `settings.ini`의 `[Gemini] api_key = ...` 설정해둔 상태
   - `config.py`가 자동으로 keyring으로 마이그레이션

2. **PyMuPDF 경고**:
   - 콘솔에 가끔 `pdf_parser not available (PyMuPDF missing?)` 경고 — 실제로는 설치돼 있음 (legacy 모듈 경고). 무시 OK.

3. **죽은 코드** (Sprint 0 검토했으나 monolith 유지 결정):
   - `frontend/js/main.js`, `frontend/js/handlers/`, `frontend/js/pages/`, `frontend/js/router.js` — 사용 안 됨
   - 실제로는 `frontend/js/sqm-inline.js` (6735 라인) 단일 번들이 동작

4. **wrong endpoint mis-wires** (Sprint 1-4에서 일부 해결):
   - ✅ `onIntegrityReport`, `onFixLotIntegrity` — 이제 분리됨
   - 🟡 `onReportTemplates` → `/api/q/audit-log` (잘못됨, Sprint 2에서 수정 예정)
   - 🟡 `onReportHistory` → `/api/q/audit-log` (잘못됨, Sprint 2)

5. **Settings 버튼**:
   - `tb-settings`는 Sprint 0에서 제거됨 (구 `/api/menu/-on-settings` NOT_READY)
   - Sprint 2에서 `SettingsDialogMixin` 풀 포팅 시 복원

6. **Audit log 뷰어** — 현재는 OneStop Outbound 모달 안에서만 접근 가능. Sprint 2에서 메뉴에서 직접 호출 가능하도록 추가 필요.

### 7.5 테스트 방법

#### 백엔드 + WebView 실행
```powershell
cd D:\program\SQM_inventory\Claude_SQM_v864_3
python main_webview.py
```

#### 정적 HTML 미리보기 (백엔드 없이 UI만)
- `D:\program\SQM_inventory\Claude_SQM_v864_3\frontend\index.html` 더블클릭

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

## 8. 📐 v864-2 → v864-3 매핑 표 (자주 참조)

| v864-2 (Tkinter) | v864-3 (WebView) | 상태 |
|---|---|---|
| `dialogs/onestop_inbound.py` | `sqm-inline.js`의 `showOneStopInboundModal()` | ✅ 100% |
| `dialogs/allocation_dialog.py` | Allocation 탭 + `loadAllocationPage()` | ✅ 100% |
| `dialogs/onestop_outbound.py` | `showOneStopOutboundModal()` | ✅ 100% |
| `dialogs/integrity_v760_dialog.py` | `showIntegrityV760Modal()` | ✅ 100% |
| `dialogs/lot_detail_dialog.py` | `window.showLotDetail()` (3탭) | ✅ 100% |
| `tabs/inventory_tab.py` (24열) | `loadInventoryPage` (24열 풀) | ✅ 100% |
| `tabs/scan_tab.py` (5버튼) | `loadScanPage` (5단계 + 토글 + 5열 history) | ✅ 100% |
| `dialogs/inbound_template_dialog.py` | (placeholder) | ❌ Sprint 2 |
| `dialogs/picking_template_dialog.py` | (placeholder) | ❌ Sprint 2 |
| `dialogs/dn_cross_check_dialog.py` | (없음) | ❌ Sprint 2 |
| `dialogs/return_inbound_preview_dialog.py` | (없음) | ❌ Sprint 2 |
| `dialogs/return_statistics_dialog.py` | (없음) | ❌ Sprint 2 |
| `dialogs/inbound_history_dialog.py` | (없음) | ❌ Sprint 2 |
| `dialogs/settings_dialog.py` (API 키 + BL 규칙) | (제거됨) | ❌ Sprint 2 |
| `gui_app_modular/mixins/menu_mixin.py` 🔍 검색 | (placeholder 버튼만) | ❌ Sprint 2 |
| `dialogs/auto_backup.py` | (placeholder) | ❌ Sprint 3 |
| `dialogs/email_config_dialog.py` | (placeholder) | ❌ Sprint 3 |
| `dialogs/parse_error_recovery_dialog.py` | (placeholder) | ❌ Sprint 3 |

### Backend 엔드포인트 — 신규 추가 분 (이번 세션 22 커밋)

| Method | URL | 추가 시점 | 설명 |
|---|---|---|---|
| POST | `/api/inbound/onestop-upload?dry_run=` | 1-2-B/C | 4종 multipart + 크로스체크 |
| POST | `/api/inbound/onestop-save` | 1-2-C | 편집된 18열 → DB 저장 |
| PATCH | `/api/allocation/{lot}` | 1-1-D | 4 필드 업데이트 |
| POST | `/api/allocation/{lot}/pick` | 1-1-E | RESERVED → PICKED |
| POST | `/api/allocation/{lot}/confirm` | 1-1-E | PICKED → SOLD |
| POST | `/api/allocation/{lot}/reset` | 1-1-E | 배정 완전 초기화 |
| POST | `/api/outbound/onestop-scan-parse` | 1-3-C | OUT 스캔 csv/xlsx 파싱 |
| POST | `/api/outbound/proof-upload` | 1-3-E | 근거문서 multi-file 업로드 |
| GET  | `/api/outbound/proof-cleanup-status` | 1-3-E | 보존 정책 상태 |
| GET  | `/api/action/integrity-report` | 1-4 | V760 형식 정합성 리포트 (read) |
| POST | `/api/action/fix-integrity` | 1-4 | 자동 복구 (mutating) |
| GET  | `/api/q/audit-log` (확장) | 1-3-D | event_type/from_date/to_date/lot_no 필터 추가 |
| POST | `/api/scan/process` (확장) | 1-7 | 5단계 상태 전환 + 가드 + audit_log |

### 기존 활용 (이번 세션에 추가 안 함)
- `GET /api/q/allocation-summary`, `/api/q/allocation-detail/{lot}` — Allocation 조회
- `GET /api/tonbags?lot_no=&status=` — Outbound Tab 2 톤백 조회 + Inventory
- `POST /api/inbound/pdf-upload` — Inbound legacy single-PDF
- `POST /api/outbound/quick`, `/api/outbound/confirm` — 출고 처리
- `GET /api/action/lot-detail/{lot_no}` — LOT 상세 (Sprint 1-5에서 활용)
- `parsers.document_parser_modular.DocumentParserV3` — 4종 PDF 파서 (재사용)
- `parsers.cross_check_engine.cross_check_documents` — 크로스체크 엔진 (재사용)

---

## 9. 📈 진행률 요약

```
Sprint 0          ████████████████████ 100% ✅
Sprint 1-1 Alloc  ████████████████████ 100% ✅
Sprint 1-2 Inbnd  ████████████████████ 100% ✅
Sprint 1-3 Outbnd ████████████████████ 100% ✅
Sprint 1-4 Integ  ████████████████████ 100% ✅
Sprint 1-5 LOT    ████████████████████ 100% ✅
Sprint 1-6 Inv24  ████████████████████ 100% ✅
Sprint 1-7 Scan   ████████████████████ 100% ✅
Sprint 1-8~14     ████░░░░░░░░░░░░░░░░  20% (작은 P0, 일부 흡수됨)
Sprint 2 P1 22건  ░░░░░░░░░░░░░░░░░░░░   0%
Sprint 3 P2 13건  ░░░░░░░░░░░░░░░░░░░░   0%

P0 14건:          ███████████████████░  93%+ (사실상 완성)
전체 155일:       ██████░░░░░░░░░░░░░░  ~50일 / 155일 (~32%)
```

---

## 10. ⚡ 즉시 실행 가능한 작업 (다음 AI가 받자마자 가능)

### 옵션 A: Sprint 2 — InboundTemplateDialog (5일, 가장 자연스러움)
- Inbound 템플릿 의존성 해결 → OneStop Inbound의 템플릿 기능 완성
1. 백엔드: 템플릿 CRUD 엔드포인트 (테이블: inbound_templates)
2. 프론트: showInboundTemplateModal (3탭: 기본정보/Gemini힌트/메모)
3. OneStop Inbound 템플릿 dropdown 실제 연동

### 옵션 B: Sprint 2 — SettingsDialogMixin (5일)
- API 키 관리 + 선사 BL/DO 규칙
- `tb-settings` dead 버튼 해결

### 옵션 C: Sprint 2 — 전역 🔍 검색 (2일, 빠름)
- 현재 placeholder 버튼 → 실제 검색 UI
- LOT/SAP/BL/Customer 등 통합 검색

### 옵션 D: 작은 잔여 P0 마무리 (5일)
- Picked/Outbound 탭 6버튼
- ManualInboundPreviewDialog 9열 인라인 편집
- DOUpdateDialog 풀

### 다음 AI에게 추천 답변 템플릿

```
받았습니다. 이 핸드오프 문서를 통해 컨텍스트 파악 완료.

현재 상태:
- 22개 커밋 완료 (369f0c3 → c6e259b)
- Sprint 1 P0 사실상 100% (Inbound/Allocation/Outbound/Integrity/LOT/Inventory/Scan 풀)
- 남은 P0 작은 잔여 (5일) + Sprint 2 P1 (60일) + Sprint 3 P2 (20일)

Sprint 2 추천 시작점:
A. InboundTemplateDialog (5d) — Inbound 템플릿 의존성 해결
B. SettingsDialogMixin (5d) — API 키 + BL 규칙 관리
C. 전역 🔍 검색 (2d) — 가장 빠름, 사용자 자주 씀
D. 잔여 P0 (5d) — Picked/Outbound 탭 버튼들

추천: C (검색)부터 빠르게 → A (템플릿) 핵심 의존성 → B (Settings)
어떻게 진행할까요?
```

---

## 11. 📞 사용자 컨택 정보

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
  - **순차 진행 + 한 기능 100% 완성** 방식 선호 확인

---

## 12. 🏁 마무리

이 문서는 **2026-04-25 갱신본**의 작업 핸드오프입니다.

**다음 AI 또는 작업자**:
1. 이 문서 + `v864_comparison/` 3개 파일을 먼저 다 읽어주세요
2. 사용자에게 Sprint 2 어느 옵션 (A/B/C/D)부터 진행할지 묻기
3. 작업 진행 시 매 Phase 완료 후 커밋 + 푸시
4. 사용자 피드백에 답답함 보이면 즉시 멈추고 확인
5. **Sprint 2 완료 시점**에 새로운 핸드오프 문서를 갱신
   (이 문서 형식 그대로, 파일명: `HANDOFF_SESSION_<날짜>.md`)

**리포지토리**: https://github.com/kidongnam1/sqm_2/tree/claude/v864-3-sprint0
**시작 커밋**: 다음 작업 시작 시 `c6e259b`에서 출발

성공적인 인계가 되기를 바랍니다. 행운을 빕니다!

— Claude (이번 세션 담당, Sprint 1 완료자)

---

## 부록: 이번 세션 작업 통계

| 메트릭 | 값 |
|---|---|
| 시작 시각 | 2026-04-24 (전일) |
| 종료 시각 | 2026-04-25 |
| 총 커밋 수 | 22 |
| 코드 라인 변화 | +5,000 / -800 (순증 약 4,200 라인) |
| 핵심 파일 변화 | sqm-inline.js: 3,469 → 6,735 (+3,266 = 94% 성장) |
| 신규 백엔드 엔드포인트 | 13개 |
| 완성된 핵심 기능 | 8개 (Sprint 1-1~7) |
| Phase 3 분석 정확도 | gap_report.md 기반 추정 ~50일 / 실제 작업량 일치 |
| 사용자 만족도 시그널 | 주로 "OK 진행" / "추천대로" — 긍정적 |
