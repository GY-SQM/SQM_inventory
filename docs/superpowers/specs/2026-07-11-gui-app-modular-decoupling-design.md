# gui_app_modular 탈결합 — 설계/요구사항(PRD)

작성일: 2026-07-11
대상 버전: v8.8.4
짝 문서(plan): `docs/superpowers/plans/2026-07-11-gui-app-modular-decoupling-plan.md`
상태: **승인·실행 완료 (P1~P3, 2026-07-11)** — live 스택 gui 결합 0 달성. P4(실삭제)만 별도 대기.

---

## 1. 목적

살아있는 스택(backend/engine/features/core)이 레거시 Tkinter 계층 `gui_app_modular`에서
끌어오는 결합을 걷어내, 최종적으로 **웹앱의 tkinter 런타임 의존을 제거**하고
`gui_app_modular`(4,302줄 monolith 포함)를 안전하게 삭제 가능한 상태로 만든다.

> 근거·의존성 분석은 plan 문서 참조. 본 문서는 "무엇을/어디까지/무엇이 통과인지"만 정의한다.

## 2. 범위 (Scope)

### In scope
- live 스택이 import하는 **순수(비-GUI) 유틸**을 중립 위치(`core/`·`utils/`)로 이전.
- `ui_constants`의 **비-Tk 상수/번역(`tc`)**을 분리.
- `backend/api/controls.py`의 Tkinter 브리지 shim 정리.

### Out of scope (이번에 하지 않는다 — 범위 확장 방지)
- ❌ `onestop_inbound.py` 등 **Tkinter 다이얼로그 내부 리팩토링** (곧 삭제 대상).
- ❌ `gui_app_modular` **실제 삭제** (P4는 별도 승인 — React 커버리지 확인 후).
- ❌ backend/engine의 **기능·API 동작 변경** (순수 이전/재배치만, 로직 불변).
- ❌ 프론트엔드(`frontend/`) 변경.
- ❌ 새 의존성 추가, 버전(`version.py`) 변경.

## 3. 불변식 / 가드레일 (절대 깨지면 안 됨)

1. **테스트 그린 유지:** 각 커밋 후 아래 명령이 **399 passed**(또는 그 이상, 회귀 0).
2. **로직 불변:** 함수 이전 시 시그니처·동작 동일. import 경로만 바뀜.
3. **하위호환:** 이전한 유틸은 기존 위치(`gui_app_modular.utils.*`)에서 **역-re-export**로 계속 import 가능.
   (레거시 GUI 코드가 아직 참조 중이므로 즉시 깨면 안 됨.)
4. **GUI 미검증 구간 회피:** 헤드리스에서 검증 불가한 Tk 위젯 코드는 이번에 건드리지 않음.
5. **CLAUDE.md 규칙 준수:** 기능 삭제 금지(추가/개선만), 각 단계 커밋, 지정 브랜치에만 push.

### 검증 명령 (매 커밋)
```bash
python -m pytest tests/ -q \
  --ignore=tests/test_inbound_doc_detector_artifact_guard.py \
  --deselect tests/test_phase1_db_index.py::test_real_db_has_indexes
```

## 4. 단계별 수용 기준 (Acceptance Criteria)

### P1 — 순수 유틸 이전 ✅ 완료 (커밋 1fc0ea8, 07018c8, 60c5ab6)
- [x] `formatters`→`core.formatters`, `report_footer`→`core.report_footer`, `product_master_helper` 로직→`core.product_master` 이전.
  - `safe_utils`는 **건너뜀**: live 스택 참조 0건(전부 레거시 gui 내부)으로 결합이 아님을 확인.
- [x] live 스택(engine `export_mixin`/`inbound_mixin`)이 **새 위치에서** import.
- [x] 기존 gui 경로는 역-re-export로 **여전히 동작**(레거시 호환).
- [x] 399 passed, 회귀 0.

### P2 — ui_constants 결합 해소 ✅ 완료 (커밋 4c1e908, c4b5823) — 원안 대비 접근 변경(승인됨)
> **원안(ui_constants 분리)은 폐기.** 분석 결과 출시 앱(`backend.api`)은 ui_constants/tkinter를
> 이미 전혀 당기지 않았고, `ui_constants`를 끌어오던 것은 engine/features에 **잘못 놓인 GUI 파일 2개**뿐이었다.
> 1,643줄(게다가 기존 SyntaxError로 깨진) `ui_constants`를 분리하는 것보다, 그 GUI 파일을 제자리로 옮기는 편이 저위험·고효과.
- [x] `move_approval_dialog_helper.py`(engine), `gemini_chat_gui.py`(features/ai) → `gui_app_modular/dialogs/`로 이동 → **engine_modules/ gui 참조 0**.
- [x] 사전검수 순수 dataclass(`ReviewItem`/`PreviewField`) → `features/parsers/review_models.py` 추출 (덤: `preview_review_bridge`의 기존 깨진 import 정상화).
- [x] 399 passed, 회귀 0.

### P3 — controls.py 브리지 정리 ✅ 완료 (커밋 8d363ec)
- [x] `backend/api/controls.py`가 `gui_app_modular.mixins.*`를 import하지 않음 → **backend/ gui import 0**.
- [x] keyboard/toolbar 엔드포인트 14개를 F085식 `NotReadyError` 스텁으로 통일(프론트 미사용·서버 미동작 확인, API 표면·기능ID 보존).
- [x] 399 passed, 회귀 0.

### P4 — 삭제 준비 (별도 승인 필수) — 감사 통과, 실삭제만 대기
- [x] `git grep gui_app_modular -- backend/ engine_modules/ features/ core/ utils/ main_webview.py` → **0건 달성** (커밋 10a0230 포함).
- [x] `backend.api` + engine 로드 시 tkinter 미로드 검증(import-time 독립 확인).
- [ ] React 앱이 monolith 기능을 커버함을 확인. **(미완 — 헤드리스 검증 불가, 별도 필요)**
- [ ] (승인 후) `gui_app_modular/` 삭제.

## 5. 위험 & 롤백
- **위험:** 순수 유틸로 보였으나 Tk/전역 상태에 숨은 의존 → 이전 시 import 에러.
  - **완화:** 이전 후 즉시 검증 명령 실행. 실패 시 해당 커밋만 `git revert`.
- **위험:** 역-re-export 누락으로 레거시 GUI import 깨짐(헤드리스에선 안 잡힘).
  - **완화:** 이전한 심볼 전부를 기존 경로에서 재노출. `git grep`으로 참조처 전수 확인.
- **롤백 단위:** 각 P는 독립 커밋. 문제 시 단일 커밋 revert로 원복.

## 6. Definition of Done (이번 이니셔티브)
- [x] P1~P3 완료, 각 단계 399 passed 그린.
- [x] live 스택의 `gui_app_modular` 참조(import·주석·도크스트링) **0건** 달성 = P4 감사 기준 충족.
- [x] 출시 스택 tkinter 비의존 검증 + CLAUDE.md 반영(커밋 4c04bbf).
- P4(실삭제)는 **본 문서와 별도로** React 커버리지 확인 후 승인받아 진행. ← **유일한 잔여**.
