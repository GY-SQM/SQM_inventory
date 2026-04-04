# SQM v866 Safe Fix - Handoff Document
- Date: 2026-04-03
- Author: Claude Code (Opus 4.6)
- Guideline: Claude Code 지시서 v2

---

## 1. 작업 요약

v866 코드베이스에 대해 **안전 우선 점진 수정**을 7라운드에 걸쳐 수행했습니다.

### 수치 요약
| 항목 | 수량 |
|------|------|
| 수정 파일 | 26개 |
| 신규 파일 | 6개 |
| 삭제 중복 폴더 | 2개 |
| 장함수 분해 | 4건 → 18개 메서드 |
| 침묵 except 로깅 추가 | ~20건 (핵심 경로) |
| DB 연결 누수 수정 | 4곳 (Draft/Runnable/react_api) |
| 라우트 에러 핸들링 | 24개 엔드포인트 |
| SQL injection 위험 | 0건 |
| except pass (핵심 모듈) | 0건 |
| 테스트 | 72/72 PASS (7라운드 연속 0 회귀) |
| 모듈 import 검증 | 35/35 PASS |

---

## 2. 실행 방법

### tkinter GUI 앱 (기존)
```bash
cd "F:\프로그램\Sqm 재고관리\Claude_SQM_v866"
python run.py
```

### React API 서버
```bash
# 구조화된 react_api/ 패키지 (권장)
python run_react_api.py

# Draft 버전
python run_react_api.py --draft
```

### React 프론트엔드
```bash
# web/ 루트 (완성된 빌드 포함)
cd web
npm install && npm run dev

# 또는 Draft 스캐폴드
cd GPT_SQM_React_Phase1_Draft/web
npm install && npm run dev
```

### 테스트
```bash
python -m pytest tests/ -v
```

---

## 3. 수정 파일 전체 목록

### Python (19개)
```
# React API (Draft)
GPT_SQM_React_Phase1_Draft/api/main.py
GPT_SQM_React_Phase1_Draft/api/dashboard_read_service.py

# React API (Runnable Set)
GPT_SQM_React_Phase1_Runnable_Set/api/main.py
GPT_SQM_React_Phase1_Runnable_Set/api/dashboard_read_service.py

# React API (Structured)
react_api/utils/db.py
react_api/routes/dashboard.py
react_api/routes/inventory.py
react_api/services/inventory_read_service.py

# Engine Modules
engine_modules/database.py
engine_modules/validators.py
engine_modules/inventory_modular/outbound_mixin.py
engine_modules/migration_manager.py

# GUI
gui_app_modular/dialogs/onestop_outbound.py
gui_app_modular/dialogs/lot_detail_dialog.py
gui_app_modular/tabs/tonbag_tab.py
gui_app_modular/tabs/dashboard_tab.py
gui_app_modular/tabs/inventory_tab.py

# Parsers
parsers/allocation_parser.py
parsers/document_parser_modular/packing_mixin.py
```

### JavaScript/JSX (6개)
```
GPT_SQM_React_Phase1_Draft/web/src/pages/InventoryPage.jsx
GPT_SQM_React_Phase1_Runnable_Set/web/src/api/client.js
GPT_SQM_React_Phase1_Runnable_Set/web/src/pages/DashboardPage.jsx
GPT_SQM_React_Phase1_Runnable_Set/web/src/pages/InventoryPage.jsx
web/src/api/client.js
web/src/pages/DashboardPage.jsx
web/src/pages/InventoryPage.jsx
```

### 신규 생성 (6개)
```
run_react_api.py                              # API 실행 스크립트
GPT_SQM_React_Phase1_Draft/web/package.json   # React 의존성
GPT_SQM_React_Phase1_Draft/web/vite.config.js # Vite 설정 (API proxy)
GPT_SQM_React_Phase1_Draft/web/index.html     # SPA 진입점
GPT_SQM_React_Phase1_Draft/web/src/main.jsx   # React DOM 렌더
GPT_SQM_React_Phase1_Draft/web/src/App.jsx    # 라우팅
```

---

## 4. 수정 유형별 분류

### A. DB 연결 누수 수정 (BUG FIX)
- `get_db()` → `@contextmanager` + `finally: db.close()`
- 적용 위치: Draft, Runnable, react_api (3세트)

### B. 라우트 에러 핸들링 (EXCEPTION)
- `try/except` + `logger.error()` + `HTTPException(500)`
- `HTTPException` (404 등) re-raise 보존
- 적용 위치: 3세트 × 6~8 라우트 = 24개 엔드포인트

### C. 침묵 except 로깅 추가 (EXCEPTION)
- `except Exception: pass` → `except Exception as exc: logger.debug/warning()`
- 핵심 데이터 경로만 선별 (DB, 출고, 검증, 마이그레이션, 파서)

### D. 장함수 안전 분해 (REFACTOR)
| 파일 | 원래 줄수 | 분해 결과 |
|------|---------|----------|
| tonbag_tab.py | 336 | 5개 메서드 |
| dashboard_tab.py | 239 | 4개 메서드 |
| inventory_tab.py | 277 | 5개 메서드 |
| lot_detail_dialog.py | 305 | 4개 메서드 |

### E. React 에러 처리 (BUG FIX)
- `AbortController` + `useEffect` cleanup
- 네트워크 에러 → 사용자 친화적 메시지
- `loadFilterOptions` 침묵 실패 제거
- 적용 위치: Draft, Runnable, web/ (3세트)

---

## 5. 남은 작업 (권장)

### 우선순위 높음
1. **실제 GUI 기동 테스트** — `python run.py` 로 전체 앱 정상 작동 확인
2. **React API 기동 테스트** — `python run_react_api.py` 후 `/docs` 접속

### 우선순위 중간
3. **장함수 분해 계속** — 아래 비즈니스 로직 함수 (1개씩 별도 세션)
   - `reserve_from_allocation` (466줄) — 출고 배정 핵심
   - `verify_lot_integrity` (385줄) — 정합성 검증
   - `process_return` (335줄) — 반품 처리
4. **React Router 추가** — Dashboard ↔ Inventory 전환

### 우선순위 낮음
5. **CORS 환경변수화** — 배포 시 `.env` 기반
6. **나머지 ~120건 GUI except 로깅** — 점진적 개선
7. **기존 코드 미사용 import 정리** (3건 — database.py, validators.py, migration_manager.py)

---

## 6. 보안 검증 결과

| 항목 | 결과 |
|------|------|
| SQL injection (f-string SQL) | 0건 — 모든 사용자 입력이 `?` 파라미터화 |
| SQL injection (.format()) | 0건 |
| except pass (핵심 모듈) | 0건 |
| DB 연결 누수 | 수정 완료 |
| React fetch 취소 | AbortController 적용 완료 |

---

## 7. 테스트 이력

| 라운드 | 테스트 | 결과 | 시간 |
|--------|--------|------|------|
| 1차 (초기) | 72 tests | 72 PASS | 0.79s |
| 2차 (엔진) | 72 tests | 72 PASS | 0.70s |
| 3차 (react_api) | 72 tests | 72 PASS | 0.68s |
| 4차 (tonbag분해) | 72 tests | 72 PASS | 0.68s |
| 5차 (dashboard분해) | 72 tests | 72 PASS | 0.70s |
| 6차 (inventory분해) | 72 tests | 72 PASS | 0.69s |
| 7차 (lot_detail분해) | 72 tests | 72 PASS | 0.68s |
| 최종 (import 35개) | 35 modules | 35 PASS | - |
