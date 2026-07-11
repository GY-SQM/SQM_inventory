# gui_app_modular(레거시 Tkinter) 탈결합 계획

작성일: 2026-07-11
대상 버전: v8.8.4
상태: 계획(미착수) — 방향 확정됨(`gui_app_modular` 폐기 방향)

---

## 배경 — "4,300줄 monolith 지금 리팩토링할까?" 에 대한 답

질문: `gui_app_modular/dialogs/onestop_inbound.py`(4,302줄 monolith)를 지금 리팩토링할지.

**결론: 리팩토링하지 않는다. 이 monolith는 분할 대상이 아니라 삭제 대상이다.**
대신 살아있는 스택이 레거시 Tkinter 계층에 걸어둔 **결합을 걷어내는 것**이 실제 가치 있는 작업이다.

---

## (가) 의존성 분석 — 근거

### 1. 출시 앱은 PyWebView 스택 하나
- 실행 경로: `run.bat → r1.vbs → pythonw main_webview.py` (단일). `SQM.vbs`도 `r1.vbs`로 위임.
- `main_webview.py`는 `backend.api` 앱만 로드하고 **tkinter를 직접 import하지 않음(0건)**.
- `gui_app_modular/`에는 `__main__.py`/`main_app.py`가 있어 `python -m gui_app_modular`로 띄울 수는 있으나,
  **어떤 출시 런처도 이를 가리키지 않음** → 레거시.

### 2. monolith는 순수 Tkinter 다이얼로그
- `onestop_inbound.py`: Tk 참조 92건. 클래스 `OneStopInboundDialog(InboundUploadMixin, InboundDialogBase)`,
  메서드 전부 `_build_*_frame` / `_create_dialog` / `_select_folder` 등 UI 조립.
- 이 파일을 import하는 곳은 **전부 레거시** `gui_app_modular/` 내부(`inbound_upload_mixin`, `inbound_processor`).

### 3. 기능은 이미 backend에 재구현됨
- `backend/api/inbound.py:535` 주석: `# v864-2 source: gui_app_modular/dialogs/onestop_inbound.py`
- backend는 자체 `onestop_inbound_upload`(682행)/`onestop_inbound_save`(1307행)를 보유 → Tkinter monolith를 import하지 않음.

→ **monolith 분할 = 곧 삭제될 코드에 공들이는 일. 하지 않는다.**

### 4. 진짜 부채: live 스택이 레거시 GUI에서 9개 모듈을 끌어옴

| gui_app_modular 모듈 | 성격 | 끌어가는 live 위치 |
|---|---|---|
| `utils.formatters` | 순수(숫자/무게 포맷) | `core/formatters.py` (20줄 re-export shim) |
| `utils.report_footer` | 순수(Tk 0건) | `engine_modules/inventory_modular/export_mixin.py` |
| `utils.safe_utils` | 순수 추정 | 다수 |
| `dialogs.product_master_helper` | 순수 로직(제품코드 자동감지) | `engine_modules/inventory_modular/inbound_mixin.py` |
| `dialogs.preparse_review_dialog` | 데이터 모델(ReviewItem/PreviewField) | `features/parsers/preview_review_bridge.py` |
| `utils.ui_constants` | 혼재(1643줄, Tk 51건 + `tc` 번역상수) | engine, features |
| `utils.custom_messagebox` | Tk GUI | `features/ai/gemini_chat_gui.py` |
| `mixins.keybindings_mixin` | Tk 핸들러 | `backend/api/controls.py` (브리지 shim, lazy import) |
| `mixins.toolbar_mixin` | Tk | `backend/api/controls.py` |

- 이 결합 때문에 **웹앱인데도 tkinter가 설치돼 있어야 실행됨** (CLAUDE.md "tkinter 필요"의 정체 = 순수 부채).

---

## (나) 점진적 탈결합 계획

목표: **live 스택이 `gui_app_modular`를 0건 import → tkinter 런타임 의존 제거 → 레거시 통째 삭제(그때 monolith도 함께 제거)**.

> **이 환경 적합성:** 탈결합 대상은 backend/engine/core = **헤드리스에서 399 테스트로 검증 가능**.
> 반대로 monolith 리팩토링은 GUI라 헤드리스에서 검증 불가. **옳은 작업이 마침 테스트 가능한 작업.**

| 단계 | 작업 | 위험/검증 |
|---|---|---|
| **P1** (안전, 먼저) | 순수 유틸을 중립 위치로 **이전**: `formatters`·`report_footer`·`safe_utils`·`product_master_helper`(로직) → `core/`·`utils/`. `core/formatters.py`가 이미 shim이라 **방향만 반전**. gui 쪽은 역-re-export로 호환 유지 | 낮음. 순수 함수. **399 테스트 즉시 검증** |
| **P2** (중간) | `ui_constants` **분리**: 비-Tk 상수/`tc` 번역 → `core/ui_text.py`(가칭), Tk 위젯만 gui 잔류. live import를 새 위치로 교체 | 중간. 1643줄 혼재 신중 분할 |
| **P3** (주의) | `backend/api/controls.py`의 keybinding/toolbar **브리지 shim**: 웹 API가 Tkinter 핸들러를 import하는 구조 → 웹에 필요한 동작만 네이티브 재구현 or 명시적 stub | 높음. 웹 UI 기대 동작 파악 필요 |
| **P4** (최종) | live의 gui_app_modular import 0건 확인 → **tkinter 런타임 의존 제거** 검증 → React 앱 기능 커버리지 확인 후 `gui_app_modular/` 삭제(monolith 포함) | 삭제 전 React 커버리지 확인 필수 |

### 공통 규칙
- 각 단계 = 작은 커밋 + 아래 명령으로 **399 passed** 그린 확인 + 롤백 가능. 빅뱅 금지.

```bash
python -m pytest tests/ -q \
  --ignore=tests/test_inbound_doc_detector_artifact_guard.py \
  --deselect tests/test_phase1_db_index.py::test_real_db_has_indexes
```

### 착수 지점
- **P1이 첫 삽.** 그중 `formatters`·`report_footer`가 순수 함수라 위험이 가장 낮고 효과가 즉시 보임.
