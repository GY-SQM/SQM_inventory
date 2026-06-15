# CLAUDE.md — SQM 재고관리 시스템

> 새 세션이 탐색 없이 바로 작업을 이어가기 위한 안내서.
> 디버깅 목표·진행상황은 **`DEBUG_GOALS.md`** 에 골(goal) 형식으로 관리한다.

## 한 줄 요약
SQM Inventory Management System — 입고/출고/LOT 재고관리 데스크톱 앱.
PyWebView(데스크톱 창) + FastAPI(로컬 백엔드) + Web UI(frontend). 현재 v8.7.x.

## 빠른 시작 (이 리눅스 세션에서)
```bash
# 테스트 의존성 설치 (SessionStart 훅이 자동 수행)
pip install -r requirements-test.txt

# 전체 테스트 — GUI(tkinter)·실DB 의존 테스트는 제외하고 실행 (headless 기준)
python -m pytest tests/ -q \
  --ignore=tests/test_inbound_doc_detector_artifact_guard.py \
  --deselect tests/test_phase1_db_index.py::test_real_db_has_indexes
```
- **앱 실제 실행은 Windows 전용**(`r1.vbs` / `SQM.vbs`, tkinter+PyWebView 필요)이라
  이 리눅스 세션에서는 GUI 구동 불가. 검증은 **pytest + 엔진/백엔드 로직** 으로 한다.

## 구조 (핵심만)
| 경로 | 역할 |
|---|---|
| `main_webview.py` | PyWebView 진입점. 로컬 FastAPI(127.0.0.1:8765~8799) 띄우고 창 로드 |
| `engine_modules/inventory_modular/` | **핵심 재고 엔진** `SQMInventoryEngineV3` (mixin 조합: inbound/outbound/shipment/return/integrity/query/crud...) |
| `engine_modules/` | DB 스키마·마이그레이션·검증·LOT 잔량 체커 등 엔진 보조 |
| `backend/api/` | FastAPI 라우터들 (inventory/outbound/inbound/allocation/scan/integrity 등) |
| `frontend/` | Web UI (HTML/JS) |
| `core/` | 바코드/PDF/검증/포매터 등 공용 |
| `features/` | AI 파서·리포트·알림 등 부가 기능 |
| `tests/` | pytest 회귀 테스트 (단계별 `test_stageN_*`, `test_v87x_*`) |
| `version.py` | 버전·릴리즈 노트 |
| `data/db/sqm_inventory.db` | SQLite(WAL 모드). **gitignore 대상** — 커밋 안 됨 |

## 도메인 규칙 (디버깅 시 반드시 지킬 불변식)
- **재고 상태 흐름:** `PENDING → AVAILABLE → PICKED → SOLD` (입고확정→가용→피킹→출고확정).
- **LOT 무결성:** `initial_weight = current_weight + picked_weight` 항상 성립해야 함.
  SOLD 전환 후 무게가 어디에도 없어 깨지는 류의 버그를 특히 조심.
- **출고 확정** `confirm_outbound`(PICKED→SOLD)은 stock_movement / sold_table 기록과
  무게 재계산이 한 트랜잭션으로 정합해야 함 (v8.7.4 회귀 테스트 참고).

## 작업 규칙 (커밋/안전)
- 기존 기능은 **삭제 금지 — 추가/개선만**.
- **각 단계마다 git commit** (롤백 가능하게). 커밋 메시지는 한국어, `feat:`/`fix:`/`chore:` 접두.
- 사용자 향(릴리즈) 변경은 `version.py` 와 `RELEASE_NOTES_*.md` 갱신 고려.
- 작업 브랜치: `claude/debugging-session-optimization-t3ayma` (지정된 브랜치에만 push).
- 푸시 전 위 pytest 명령으로 **225 passed** 그린 확인.

## 테스트 주의
- `tests/test_inbound_doc_detector_artifact_guard.py` → tkinter 필요, 서버에서 **collection 에러**(정상). 제외하고 실행.
- `test_phase1_db_index.py::test_real_db_has_indexes` → 실제 DB 파일 의존. 신규 클론에선 skip,
  한 세션 내 다른 테스트가 DB를 만들면 실패할 수 있어 **deselect** 권장.
