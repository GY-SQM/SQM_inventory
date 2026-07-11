# gui_app_modular 탈결합 — 설계/요구사항(PRD)

작성일: 2026-07-11
대상 버전: v8.8.4
짝 문서(plan): `docs/superpowers/plans/2026-07-11-gui-app-modular-decoupling-plan.md`
상태: 승인 대기 — **본 문서 승인 전 코드 변경 금지**

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

### P1 — 순수 유틸 이전
- [ ] `formatters`, `report_footer`, `safe_utils`, `product_master_helper`(로직)이 `core/`·`utils/`에 존재.
- [ ] live 스택(backend/engine/features/core)이 이 유틸을 **새 위치에서** import.
- [ ] `gui_app_modular.utils.*` 기존 경로는 역-re-export로 **여전히 동작**(레거시 호환).
- [ ] 399 passed, 회귀 0.

### P2 — ui_constants 분리
- [ ] 비-Tk 상수/`tc` 번역이 중립 모듈(예: `core/ui_text.py`)로 분리.
- [ ] live import가 새 모듈 사용. Tk 위젯 부분은 gui에 잔류.
- [ ] 399 passed, 회귀 0.

### P3 — controls.py 브리지 정리
- [ ] `backend/api/controls.py`가 `gui_app_modular.mixins.*`를 import하지 않음.
- [ ] 웹에서 필요한 동작은 네이티브 구현 or 명시적 stub로 대체(동작 동일/명세됨).
- [ ] 399 passed, 회귀 0.

### P4 — 삭제 준비 (별도 승인 필수)
- [ ] `git grep gui_app_modular -- backend/ engine_modules/ features/ core/ utils/ main_webview.py` → **0건**.
- [ ] tkinter 미설치 환경에서 `backend.api` import 성공(런타임 의존 제거 검증).
- [ ] React 앱이 monolith 기능을 커버함을 확인.
- [ ] (승인 후) `gui_app_modular/` 삭제.

## 5. 위험 & 롤백
- **위험:** 순수 유틸로 보였으나 Tk/전역 상태에 숨은 의존 → 이전 시 import 에러.
  - **완화:** 이전 후 즉시 검증 명령 실행. 실패 시 해당 커밋만 `git revert`.
- **위험:** 역-re-export 누락으로 레거시 GUI import 깨짐(헤드리스에선 안 잡힘).
  - **완화:** 이전한 심볼 전부를 기존 경로에서 재노출. `git grep`으로 참조처 전수 확인.
- **롤백 단위:** 각 P는 독립 커밋. 문제 시 단일 커밋 revert로 원복.

## 6. Definition of Done (이번 이니셔티브)
- P1~P3 완료, 각 단계 그린.
- live 스택의 `gui_app_modular` import가 P4 검증 기준(0건)에 도달.
- P4(실삭제)는 **본 문서와 별도로** React 커버리지 확인 후 승인받아 진행.
