# 🤖 v864-3 포팅 작업 핸드오프 (2026-04-25 갱신본 v3)

> **다음 AI 또는 작업자에게**: 이 문서 하나만 읽으면 처음부터 모든 컨텍스트 파악 가능합니다.
> **현 시점**: 32개 커밋 완료. **Sprint 1 P0 100% + Sprint 2 P1 36%** 도달.
> **다음 단계**: Sprint 2 P1 잔여 14건 (예상 ~38일) + Sprint 3 P2 13건 (~20일).

---

## 1. 🎯 프로젝트 절대 원칙

> **"v864-2의 UI를 그대로, 하부 기능까지 전부 v864-3(WebView)에 재현"**
> **UI만 Tkinter→WebView로 변경, 로직은 100% 동일**

- v864-2: Tkinter + ttkbootstrap 데스크톱 (`gui_app_modular/`)
- v864-3: HTML/CSS/JS + Python FastAPI WebView
- v864-2가 **Golden Reference** — 모든 결정의 진실 기준
- v864-2 코드는 수정 금지, 참조만

### 사용자 핵심 통찰 (꼭 기억)
1. **"4 vs 1" 원칙** — 기능 깊이 일치
2. **"하부 조직" = 다이얼로그 내부 UI**
3. **답답함 누적**: 반쪽짜리 누적 시 큰 스트레스
4. **시각 비교 필수** — 스크린샷 교차검증
5. **순차 진행** — 한 기능 100% 완성 후 다음

---

## 2. 📁 작업 환경

### 디렉터리
```
D:/program/SQM_inventory/
├── Claude_SQM_v864_2/          # ⭐ Golden Reference (수정 금지)
├── Claude_SQM_v864_3/          # ⭐ 작업 대상 (모든 수정은 여기)
│   ├── frontend/
│   │   ├── index.html
│   │   ├── css/v864-layout.css        # 974 lines
│   │   └── js/sqm-inline.js           # ⭐ 7800+ lines (단일 번들)
│   ├── backend/api/
│   │   ├── inbound.py        # 938 lines (+470 from start)
│   │   ├── outbound_api.py   # 920 lines (+454)
│   │   ├── inventory_api.py  # 655 lines (+186)
│   │   ├── actions.py        # +160 (Sprint 1-4)
│   │   ├── queries.py        # +205 (Sprint 1-3-D, 2-C, 2-Q)
│   │   └── allocation_api.py
│   ├── parsers/              # ⭐ v864-2 그대로 활용
│   ├── data/proof_docs/      # Sprint 1-3-E 신규
│   ├── settings.ini          # ⚠️ gitignored
│   └── HANDOFF_SESSION_2026-04-25.md  # ⭐ 이 파일
└── v864_comparison/          # Phase 3 마스터 분석 (gap_report.md 등)
```

### Git
- **리포지토리**: https://github.com/kidongnam1/sqm_2
- **브랜치**: `claude/v864-3-sprint0`
- **시작점**: `ea9d0f0` (이번 세션 시작)
- **현재 HEAD**: `7e549b5` (Sprint 2-P 완료)

### 환경
- Windows 11 + PowerShell + Python 3.11
- 설치: `pip install -r requirements.txt && pip install uvicorn pywebview pyinstaller`
- 실행: `python main_webview.py`
- API key: `settings.ini`의 `[Gemini] api_key = AQ...`

---

## 3. ✅ 완료된 작업 — 32개 커밋 전체

### Sprint 0 (정리)
- **`369f0c3`** chore(sprint-0): menubar.py 삭제 + L1 메뉴 v864-2 순서 복원

### Sprint 1 P0 (14건 — 사실상 100%)
- **`28ce4e7`** Sprint 0-3b + 1-1: Allocation 탭 재설계 + cascading 메뉴
- **`a2b76f1`** Sprint 1-2-A: OneStop Inbound 4슬롯 wizard (UI)
- **`c4c2d68`** Sprint 1-2-B: 백엔드 /onestop-upload + 4종 크로스체크
- **`a23f06a`** UX: 전역 ESC
- **`c59ed8a`** UX: Enter/Tab/double-ESC
- **`0745448`** Sprint 1-2-C: 인라인 편집 + dry_run/save 분리
- **`b420b1e`** Sprint 1-2-D: Undo/Redo (max 50) + D/O 수동 입력
- **`e125211`** Sprint 1-1-D+E: Allocation 인라인 편집 + 3 상태전환 엔드포인트
- **`1a9d044`** Sprint 1-3-A: OneStop Outbound 4탭 wizard + 상태머신
- **`8be7aa0`** Sprint 1-3-B: Tab 2 톤백 선택 + DRAFT→WAIT_SCAN
- **`c2158da`** Sprint 1-3-C: Tab 3 OUT 스캔 검증 + 4-tier 하드스톱
- **`b40bfb3`** docs: 핸드오프 v1
- **`3861469`** Sprint 1-3-D: Tab 4 완료 + 감사 로그 sub-popup
- **`c353c28`** Sprint 1-3-E: proof_docs 저장 + 90일 자동 정리 [Outbound 100%]
- **`a2e262a`** Sprint 1-4: IntegrityV760 (6 카드 + 신호등 + 자동복구)
- **`f508206`** Sprint 1-6: Inventory 24열 풀 (정렬/필터/컨텍스트/토글)
- **`dd2da5c`** Sprint 1-5: LOT Detail 3탭 (톤백/이동이력/Allocation)
- **`c6e259b`** Sprint 1-7: Scan 5단계 상태 전환 + ⚡빠른스캔/🔕무음 토글

### 핸드오프 v2
- **`7db7d9c`** docs: 핸드오프 갱신 (22커밋 시점)

### Sprint 2 P1 (8건 / 22건, ~36%)
- **`3593cba`** Sprint 2-C: 전역 🔍 검색 (LOT/Tonbag/Allocation/Audit 통합)
- **`be2907c`** Sprint 2-A: InboundTemplate 풀 CRUD (3탭) + OneStop 연동
- **`d645234`** Sprint 2-D: Picked + Outbound 탭 6버튼 풀 (일괄/Excel/날짜필터)
- **`07284a3`** Sprint 2: PickingTemplate 풀 CRUD
- **`910aef0`** Sprint 2-R: Sales Order Upload (Excel→sold_table 매칭)
- **`69e1c56`** Sprint 2-Q: InboundHistoryDialog (필터+통계+Excel)
- **`341302c`** Sprint 2-O: DN Cross-Check (사이드-바이-사이드)
- **`7e549b5`** Sprint 2-P: ReturnStatisticsDialog (CSS bar chart + 월별)

---

## 4. 🟢 현재 완성된 핵심 기능 — 실무 투입 가능

### Sprint 1 (100%)
```
✅ 메뉴 구조 v864-2 일치 (cascading 서브메뉴)
✅ PDF 4종 입고 + 4슬롯 + 크로스체크 + 18열 미리보기 + 인라인 편집
✅ Allocation 9열 편집 + 7버튼 + 우클릭 + 상태 전환 4단계
✅ OneStop Outbound 4탭 wizard + 상태머신 + 하드스톱 + 감사로그 + proof_docs
✅ IntegrityV760 6카드 + 신호등 + 자동 복구
✅ LOT Detail 3탭 (톤백/이동이력/Allocation)
✅ Inventory 24열 (정렬/필터/컨텍스트/컬럼토글/Excel)
✅ Scan 5단계 상태전환 (배정→화물결정→출고확정→반품→재입고)
✅ UX: ESC/Enter/Tab/외부클릭/double-ESC 종료
```

### Sprint 2 (36%)
```
✅ 전역 🔍 검색 (4 도메인 통합)
✅ InboundTemplate CRUD (3탭) + OneStop 연동
✅ PickingTemplate CRUD
✅ Picked 탭 6버튼 (출고확정/되돌림/Excel/일괄선택)
✅ Outbound 탭 6버튼 (반품/되돌림/날짜필터/Excel)
✅ Sales Order 업로드 (Excel/CSV 매칭)
✅ Inbound 현황 조회 (필터+통계+Excel)
✅ DN 교차검증 (DO ↔ 재고 사이드바이사이드)
✅ 반품 통계 (CSS bar chart + 월별)
```

---

## 5. 🟡 남은 작업 — 정리

### Sprint 2 P1 잔여 14건 (~38일 예상)

| # | 작업 | 공수 | 우선순위 |
|---|---|---|---|
| 1 | **SettingsDialogMixin** (API 키 + BL 규칙 v9.0) | 5일 | 🔴 높음 (`tb-settings` dead button) |
| 2 | **🚢 BL 선사 도구** 서브메뉴 2개 (등록/분석) | 5일 | 🔴 높음 |
| 3 | **📋 보고서 양식/이력** (잘못된 endpoint 수정 + UI) | 6일 | 🔴 높음 |
| 4 | **감사 로그 뷰어** (메뉴 직접 접근) | 3일 | 🟡 중간 |
| 5 | **🔁 Swap 리포트** | 2일 | 🟡 중간 |
| 6 | **🔔 재고 알림 조회** | 2일 | 🟡 중간 |
| 7 | **ManualInboundPreviewDialog** 9열 인라인 편집 | 3일 | 🟡 중간 |
| 8 | **DOUpdateDialog** 풀 (PDF + 6열 매칭) | 3일 | 🟡 중간 |
| 9 | **PickingListPreviewDialog** 풀 | 3일 | 🟡 중간 |
| 10 | **LocationUploadPreviewDialog** | 3일 | 🟡 중간 |
| 11 | **ReturnInboundPreviewDialog** | 3일 | 🟡 중간 |
| 12 | **ParsePreviewConfirmDialog** | 3일 | 🟡 중간 |
| 13 | **Move 탭 보강** (Lookup/Clear/Approval) | 3일 | 🟢 낮음 |
| 14 | **Return Cargo Overview** 20열 | 3일 | 🟢 낮음 |

### Sprint 3 P2 13건 (~20일 예상)
- ShortcutGuideDialog (단축키 가이드, 2일)
- EmailConfigDialog 11필드 (2일)
- AutoBackupSettingsDialog (3일)
- 컬럼 가시성 토글 모든 탭 (1일)
- 테마 variants (1일)
- 창 크기 저장/초기화 (1일)
- 재고 추이 차트 `onStockTrendChart` (2일)
- Welcome/Feedback (1일)
- PDF 도구 4분할 (1일)
- ParseErrorRecovery 9 ERROR_CODES (3일)
- 종료 확인 다이얼로그 (0.5일)
- AllocationStressTestDialog (5일, defer 후보)
- ReviewCenterDialog (5일, defer 후보)

### Phase 2 (선택)
- Gemini AI 서브메뉴 전체 (~5~15일)

---

## 6. 📊 현재 진행률

```
Sprint 1 P0 14건  ████████████████████ 100% ✅
Sprint 2 P1 22건  ███████░░░░░░░░░░░░░  36% (8/22)
Sprint 3 P2 13건  ░░░░░░░░░░░░░░░░░░░░   0%
─────────────────────────────────────────
전체 P0+P1+P2 49건 ███████░░░░░░░░░░░░░  35% (22/49)
원래 추정 155일    ███████████░░░░░░░░░  47% (~73일 / 155일)
```

### 실제 시간 vs 추정
- Sprint 1 추정: 70일 / 실제: ~12-15시간 (5-7배 빠름)
- Sprint 2 8건 추정: 22일 / 실제: ~5-7시간 (3-4배 빠름)

### 남은 시간 추정 (실제)
- Sprint 2 잔여 14건: 추정 38일 → **실제 8~12시간** (1~2 세션)
- Sprint 3 P2 13건: 추정 20일 → **실제 4~6시간** (1 세션)
- **총 남은 작업: 12~18시간 (실제 시간)**

---

## 7. 🎓 다음 AI를 위한 핸드오프 가이드

### 7.1 시작하기
1. 이 문서 전체 읽기
2. `v864_comparison/gap_report.md` 읽기
3. git log 확인: 최근 32개 커밋
4. 사용자에게 "Sprint 2 어느 항목부터?" 묻기

### 7.2 작업 원칙 (학습된 사용자 선호)
- **v864-2 코드 수정 금지** — 참조만
- **로직 100% 동일** — UI 형태만 다르게
- **순차 진행** — 한 기능 완성 후 다음
- **반쪽짜리 누적 금지**
- **placeholder는 명시적으로** ("Sprint X 예정" 토스트)
- **커밋은 logical unit 별로**
- **추천안 + 이유** 같이 제시
- **한국어 응답**

### 7.3 자주 사용하는 패턴 (재사용 가능)

#### 새 모달
```javascript
function showXxxModal() {
  showDataModal('', '<div>...HTML...</div>');
}
window.showXxxModal = showXxxModal;
```

#### 새 ENDPOINTS
```javascript
'onXxx': {m:'JS',  u:'wip', lbl:'준비 중'},  // placeholder
'onXxx': {m:'JS',  u:'xxx-action', lbl:'...'},  // dispatch
// dispatchAction에 'if (conf.u === xxx-action) { showXxxModal(); return; }'
```

#### 백엔드 새 엔드포인트
```python
from typing import Dict, Any
from fastapi import Body
@router.post("/...")
def handler(payload: Dict[str, Any] = Body(...)):
    return {"ok": True, "data": {...}}
```

#### CSV Export (재사용 패턴)
```javascript
function csvEsc(v){ var s = String(v == null ? '' : v); if (/[,"\n]/.test(s)) s = '"' + s.replace(/"/g,'""') + '"'; return s; }
var blob = new Blob(['\ufeff' + lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
var url = URL.createObjectURL(blob);
var a = document.createElement('a'); a.href = url;
a.download = 'name_YYYYMMDD_HHMM.csv';
document.body.appendChild(a); a.click(); document.body.removeChild(a);
URL.revokeObjectURL(url);
```

#### 인라인 셀 편집 — `onestopEditCell`, `allocEditCell` 참조
#### 우클릭 메뉴 — `allocContextMenu`, `invContextMenu` 참조
#### Sub-popup (z-index 10001) — `ooViewAuditLog` 참조
#### 다중 선택 일괄 액션 — `_allocBulkAction`, `_pickedBulkAction`, `_outboundBulkAction` 참조
#### 사이드-바이-사이드 비교 — `showDnCrossCheckModal` 참조
#### CSS bar chart — `showReturnStatsModal` 참조

### 7.4 알려진 이슈

1. **Gemini API key**: `parse_do`만 필수. settings.ini에 사용자 설정 완료
2. **PyMuPDF 경고**: 무시 OK (legacy 모듈)
3. **죽은 코드**: `frontend/js/{main.js, handlers/, pages/, router.js}` 사용 안 됨
4. **mis-wired endpoints** (남음):
   - `onReportTemplates` → `/api/q/audit-log` (잘못됨, Sprint 2-#3에서 수정 예정)
   - `onReportHistory` → `/api/q/audit-log` (잘못됨)
   - **이것들은 현재 임시 동작은 하지만 의미적으로 틀림**
5. **Settings 버튼**: `tb-settings` 제거됨, Sprint 2-#1에서 복원

### 7.5 테스트 방법
```powershell
# 백엔드 + WebView
cd D:\program\SQM_inventory\Claude_SQM_v864_3
python main_webview.py

# 구문 검증
node -e "const fs=require('fs'); new Function(fs.readFileSync('frontend/js/sqm-inline.js','utf8')); console.log('JS OK')"
python -c "import ast; ast.parse(open('backend/api/inbound.py',encoding='utf-8').read()); print('Python OK')"

# Git
git add <specific-files>  # ⚠️ 절대 git add . 사용 금지 (M 파일 섞임)
git commit -m "feat(sprint-X-Y): ..."
git push
```

---

## 8. 📐 v864-2 → v864-3 매핑 표

### 100% 완성 (✅)
| v864-2 | v864-3 |
|---|---|
| `dialogs/onestop_inbound.py` (4302줄) | `showOneStopInboundModal()` |
| `dialogs/allocation_dialog.py` (1616줄) | Allocation 탭 + `loadAllocationPage` |
| `dialogs/onestop_outbound.py` (2304줄) | `showOneStopOutboundModal()` |
| `dialogs/integrity_v760_dialog.py` (387줄) | `showIntegrityV760Modal()` |
| `dialogs/lot_detail_dialog.py` (359줄) | `window.showLotDetail` (3탭) |
| `tabs/inventory_tab.py` (24열) | `loadInventoryPage` (24열 풀) |
| `tabs/scan_tab.py` (5버튼) | `loadScanPage` (5단계 + 토글) |
| `dialogs/inbound_template_dialog.py` (461줄) | `showInboundTemplateModal` |
| `dialogs/picking_template_dialog.py` (447줄) | `showPickingTemplateModal` |
| `dialogs/dn_cross_check_dialog.py` (192줄) | `showDnCrossCheckModal` |
| `dialogs/return_statistics_dialog.py` (481줄) | `showReturnStatsModal` |
| `dialogs/inbound_history_dialog.py` (339줄) | `showInboundHistoryModal` |
| (Sales Order 핸들러) | `showSalesOrderUploadModal` |
| (메뉴 🔍 검색) | `showGlobalSearchModal` |
| `tabs/picked_tab.py` (6버튼) | `loadPickedPage` (6버튼 풀) |
| `tabs/sold_tab.py` (6버튼) | `loadOutboundPage` (6버튼 + 날짜필터) |

### Sprint 2/3 남은 (❌)
| v864-2 | v864-3 | 우선순위 |
|---|---|---|
| `dialogs/settings_dialog.py` (869줄) | (제거됨) | 🔴 |
| `mixins/menu_mixin.py` BL 도구 | (placeholder) | 🔴 |
| 보고서 양식/이력 | (mis-wired) | 🔴 |
| `dialogs/auto_backup.py` (445줄) | (placeholder) | 🟡 |
| `dialogs/manual_inbound_preview.py` | (없음) | 🟡 |
| `dialogs/do_update_dialog.py` (551줄) | 부분만 | 🟡 |
| `dialogs/picking_list_preview_dialog.py` (221줄) | 부분만 | 🟡 |
| `dialogs/email_config_dialog.py` (157줄) | (placeholder) | 🟢 |
| `dialogs/parse_error_recovery_dialog.py` (317줄) | (placeholder) | 🟢 |

### 백엔드 신규 엔드포인트 (이번 세션 — 22개)

| Method | URL | Sprint |
|---|---|---|
| POST | `/api/inbound/onestop-upload?dry_run=` | 1-2-B/C |
| POST | `/api/inbound/onestop-save` | 1-2-C |
| GET/POST/PATCH/DELETE | `/api/inbound/templates*` | 2-A |
| PATCH | `/api/allocation/{lot}` | 1-1-D |
| POST | `/api/allocation/{lot}/pick` | 1-1-E |
| POST | `/api/allocation/{lot}/confirm` | 1-1-E |
| POST | `/api/allocation/{lot}/reset` | 1-1-E |
| POST | `/api/allocation/{lot}/confirm-outbound` | 2-D |
| POST | `/api/allocation/{lot}/revert-picked` | 2-D |
| POST | `/api/allocation/{lot}/return-outbound` | 2-D |
| POST | `/api/allocation/{lot}/revert-outbound` | 2-D |
| GET/POST/PATCH/DELETE | `/api/outbound/templates*` | 2 |
| POST | `/api/outbound/onestop-scan-parse` | 1-3-C |
| POST | `/api/outbound/proof-upload` | 1-3-E |
| POST | `/api/outbound/sales-order-upload` | 2-R |
| GET | `/api/outbound/proof-cleanup-status` | 1-3-E |
| GET | `/api/action/integrity-report` | 1-4 |
| POST | `/api/action/fix-integrity` | 1-4 |
| GET | `/api/q/audit-log` (필터 추가) | 1-3-D |
| GET | `/api/q/inbound-status` (필터 추가) | 2-Q |
| GET | `/api/q/global-search` | 2-C |
| POST | `/api/scan/process` (5단계 확장) | 1-7 |

---

## 9. ⚡ 즉시 시작 가능한 다음 작업 (우선순위순)

### 🔴 1순위 (가장 큰 가치)
**SettingsDialogMixin 풀 포팅 (5일 → 실제 1~2시간)**
- API 키 관리 (Gemini/OpenAI/Claude)
- 선사 BL/DO 규칙 CRUD
- `tb-settings` dead button 해결
- 새 테이블: `carrier_rules` (생성 필요)

### 🔴 2순위
**🚢 BL 선사 도구 (5일 → 1~2시간)**
- 선사 BL 등록 도구
- 선사 패턴 분석
- Settings의 carrier_rules 활용

### 🔴 3순위
**보고서 양식/이력 mis-wire 수정 (6일 → 1~2시간)**
- 잘못된 endpoint 수정
- 보고서 템플릿 CRUD
- 보고서 이력 조회

### 🟡 4-6순위 (작은 다이얼로그들, 같이 묶어서)
- 감사 로그 뷰어 (메뉴 직접) (3일 → 30분, OneStop Outbound 코드 재사용)
- Swap 리포트 (2일 → 1시간)
- 재고 알림 조회 (2일 → 1시간)

### 다음 AI 답변 템플릿
```
받았습니다. 32개 커밋 컨텍스트 파악 완료.
- Sprint 1 P0 100% / Sprint 2 P1 36% (8/22)
- 남은 작업: Sprint 2 P1 14건 + Sprint 3 P2 13건

추천 1순위: SettingsDialogMixin (5일 추정 → 실제 1~2시간)
- API 키 관리 + 선사 규칙 CRUD
- tb-settings dead button 해결

진행할까요? 다른 항목 원하시면 말씀해주세요.
```

---

## 10. 📞 사용자 컨택

- 이름: 남기동 (Nam Kidong)
- 이메일: kidong.nam@gmail.com
- 모국어: 한국어 / Windows 11
- 특성:
  - 비기술자 (코드 직접 안 씀)
  - 결정 빠름 ("OK", "진행해" 식)
  - 답답함 표현 명확
  - 시각 비교 좋아함
  - 추천안 + 이유 같이 제시받는 걸 선호
  - 순차 진행 + 100% 완성 방식 선호

---

## 11. 🏁 마무리

**다음 AI 또는 작업자**:
1. 이 문서 + `v864_comparison/` 3개 파일 먼저 읽기
2. 사용자에게 Sprint 2 우선순위 옵션 제시
3. Phase 완료 후 매번 커밋 + 푸시
4. **남은 작업 ~12-18시간** 분량 (실제 시간)
5. 새 핸드오프 갱신은 10커밋마다 권장

**리포지토리**: https://github.com/kidongnam1/sqm_2/tree/claude/v864-3-sprint0
**시작 커밋**: `7e549b5` 에서 출발

---

## 12. 부록: 세션 통계

| 메트릭 | 값 |
|---|---|
| 시작/종료 | 2026-04-24 / 2026-04-25 |
| 총 커밋 | 32개 |
| 코드 라인 추가 | +8,000줄 (전체 누적) |
| sqm-inline.js | 3,469 → 7,800+ (+125% 성장) |
| 신규 백엔드 엔드포인트 | 22개 |
| 완성된 핵심 기능 | 17개 (Sprint 1 9개 + Sprint 2 8개) |
| 사용자 만족 시그널 | 매우 긍정적 (지속적 "진행해", "계속") |
