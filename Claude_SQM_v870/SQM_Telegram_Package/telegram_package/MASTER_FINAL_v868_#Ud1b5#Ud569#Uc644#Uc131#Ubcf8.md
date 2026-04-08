# SQM MASTER FINAL v868 (Claude Code Execution Standard)
생성일: 2026-04-04 (루비 세션 업데이트)
기준: Claude_SQM_v868 실제 구현 상태 100% 반영

---

## 0. 절대 실행 규칙

### 자율 실행 규칙
- 절대 사용자에게 질문하지 말 것
- 모든 선택은 스스로 판단할 것
- 파일 덮어쓰기 / 삭제는 자동 승인된 것으로 간주할 것
- 테스트 실패 시 자동 수정 후 재시도할 것
- 작업 완료 후 다음 단계 자동 진행
- 중단 없이 끝까지 수행할 것

### 강제 테스트 규칙
```text
Pre-Test → 구현 → Post-Test → 실패 시 수정 → Re-Test → 통과 → 다음 단계
```
테스트 실패 상태에서 다음 단계 진행 금지.

---

## 1. 기준 원본

기준 원본은 `Claude_SQM_v868` 이다.

### 확인된 상위 구조
```text
core/
  pdf_engine.py              ← PC/Android 공통 PDF 엔진 ✅
data/
  db/sqm_inventory.db
engine_modules/
  inventory_modular/
    inbound_mixin.py
    outbound_mixin.py
    query_mixin.py
features/
gui_app_modular/
parsers/
react_api/
  middleware/
    security.py              ← Phase 5 보안 미들웨어 ✅
  routes/
    dashboard.py             ✅
    inventory.py             ✅
    tabs.py                  ✅
    inbound.py               ← Phase 4 쓰기 API ✅
    outbound_write.py        ← Phase 4 쓰기 API ✅
    location.py              ← Phase 4 쓰기 API ✅
    files.py                 ← Phase 4 쓰기 API ✅
    search.py                ← Phase 6 검색 ✅
    tools.py                 ← Phase 6 도구 ✅
    advanced.py              ← Phase 6 Advanced ✅
    ai_dashboard.py          ← Phase 7 AI ✅
  services/
    inbound_write_service.py ← Phase 3 ✅
    outbound_write_service.py← Phase 3 ✅
  schemas/
    write_models.py          ← Phase 1 ✅
scripts/
  telegram_bridge.py         ← Phase 8 ✅
  telegram_notify.py         ← Phase 8 ✅
tests/
  stage_gates/               ← 기존 12개 + 신규 1개 ✅
web/src/
  components/
    MenuBar.jsx              ← Phase 4 메뉴바 ✅
    LotDetailModal.jsx       ← Phase 4 모달 ✅
    InboundModal.jsx         ← Phase 4 모달 ✅
    OutboundModal.jsx        ← Phase 4 모달 ✅
    SearchModal.jsx          ← Phase 4 검색 모달 ✅
    Modal.jsx                ← 공통 모달 ✅
  pages/                     ← 7개 페이지 ✅
docs/
  RECON_V867_WEB_MIGRATION_MAP.md ← Recon 완료 ✅
```

---

## 2. 현재 구현 완료 현황

### Phase 완료 현황
```text
Recon Phase : ✅ 완료
Phase 1     : ✅ 완료 (공통 응답 스키마, write_models)
Phase 2     : ✅ 완료 (테스트 13개)
Phase 3     : ✅ 완료 (서비스 레이어 2개)
Phase 4     : ✅ 완료 (메뉴바 + 모달 4종 + 쓰기 API 5종)
Phase 5     : ✅ 완료 (security 미들웨어)
Phase 6     : ✅ 완료 (search + tools + advanced)
Phase 7     : ✅ 완료 (ai_dashboard)
Phase 8     : 🔄 진행 중 (telegram_bridge + telegram_notify 있음)
```

### API 현황 (전체)
```text
GET  /api/dashboard/summary
GET  /api/dashboard/by-product
GET  /api/dashboard/location-summary
GET  /api/inventory/filters
GET  /api/inventory/search
GET  /api/inventory/lot/{lot_no}
GET  /api/tabs/tonbag
GET  /api/tabs/allocation
GET  /api/tabs/picked
GET  /api/tabs/sold
GET  /api/tabs/outbound
POST /api/inbound/create          ← 쓰기 API
POST /api/outbound/execute        ← 쓰기 API
PUT  /api/outbound/cancel         ← 쓰기 API
PUT  /api/location/update         ← 쓰기 API
POST /api/files/upload            ← 쓰기 API
GET  /api/search/unified
GET  /api/tools/export/csv
GET  /api/tools/integrity-check
GET  /api/advanced/outbound-history
```

### React 컴포넌트 현황
```text
MenuBar.jsx        ← 검색/도구/입고/출고 드롭다운 ✅
LotDetailModal.jsx ← LOT 상세 팝업 ✅
InboundModal.jsx   ← 입고 파싱 모달 ✅
OutboundModal.jsx  ← 출고 처리 모달 ✅
SearchModal.jsx    ← 통합 검색 모달 ✅
```

---

## 3. 작업 전략

### 절대 금지
- 예전 가정 구조만 믿고 수정하지 말 것
- 실제 v868 구조 조사 없이 패치 먼저 적용하지 말 것
- FastAPI에서 완전 신규 업무 로직 작성 금지
- rollback 없는 쓰기 API 구현 금지
- fitz 직접 import 금지 → core/pdf_engine 경유
- engine_modules 직접 수정 금지

### 필수 원칙
1. 기존 engine_modules 로직 재사용
2. 단계별 테스트 게이트 통과 후만 다음 단계 진행
3. 모든 쓰기 API 트랜잭션 보호
4. core/pdf_engine.py 통해서만 PDF 처리

---

## 4. 남은 작업 (Phase 8 완료)

### Phase 8: 통합 실행 완료 기준

#### 8-1. Telegram Bridge 완성
```text
파일: scripts/telegram_bridge.py (존재 ✅)
확인 필요:
  - y/n/1/2/3 응답 처리 동작 확인
  - idle timeout 감지 동작 확인
  - Claude Code 출력 300~500자 전송 확인
```

#### 8-2. run_master.bat 완성
```text
파일: run_master.bat (존재 ✅)
확인 필요:
  - .env 존재 확인
  - pytest 통과 확인
  - FastAPI 정상 기동 확인
  - web/dist 빌드 확인
  - Telegram bridge 연결 확인
```

#### 8-3. run_master.ps1 완성
```text
파일: run_master.ps1 (존재 ✅)
확인 필요:
  - run_master.bat 과 동일 기능 PowerShell 버전
```

#### 8-4. 누락 탭 5개 구현
```text
현재: 7개 페이지만 존재
누락:
  MovePage.jsx        ← 위치 이동
  ScanPage.jsx        ← 스캔
  LogPage.jsx         ← 로그
  SummaryPage.jsx     ← 요약
  CargoOverviewPage.jsx ← 화물 현황
```

#### 8-5. pytest 전체 통과 확인
```text
cd F:\프로그램\Sqm 재고관리\Claude_SQM_v868
pytest tests/ -v
→ 전체 통과 확인
```

---

## 5. 실행 방법

### PC 실행
```cmd
F:
cd "프로그램\Sqm 재고관리\Claude_SQM_v868"
python -m uvicorn react_api.main:app --host 127.0.0.1 --port 8000
```
```cmd
F:
cd "프로그램\Sqm 재고관리\Claude_SQM_v868\web"
npm run dev
```

### Android Termux 실행
```bash
cd ~/sqm
uvicorn react_api.main:app --host 0.0.0.0 --port 8000
```

### 브라우저 접속
```
http://127.0.0.1:8000/docs  ← FastAPI
http://localhost:5173        ← React
```

---

## 6. 다음 세션 Claude Code 실행 프롬프트

```
현재 작업 기준 원본은 Claude_SQM_v868 이다.
MASTER_FINAL_v868_통합완성본.md 를 기준으로 작업한다.

[현재 상태]
- Phase 1~7: 완료
- Phase 8: 진행 중 (telegram_bridge, run_master.bat 존재)

[이번 작업 목표]
1. pytest tests/ -v 전체 통과 확인
2. Phase 8 완료:
   - Telegram bridge y/n 응답 처리 확인
   - run_master.bat 사전 테스트 동작 확인
   - run_master.ps1 동작 확인
3. 누락 탭 5개 구현:
   - MovePage.jsx / ScanPage.jsx / LogPage.jsx
   - SummaryPage.jsx / CargoOverviewPage.jsx
4. App.jsx 라우팅에 5개 추가
5. 전체 npm run build 성공 확인

[강제 원칙]
- 각 작업 완료 후 pytest 통과 확인 필수
- 질문 없이 끝까지 진행
- fitz 직접 import 금지
- engine_modules 직접 수정 금지
```

---

## 7. 금지 사항
- 테스트 생략
- 사용자 질문 발생
- 부분 완료 상태 종료
- rollback 없는 쓰기 API 구현
- fitz 직접 import
- engine_modules 직접 수정

---

## 8. 최종 목표
```text
1. Phase 8 완전 완료
2. 누락 탭 5개 구현
3. pytest 전체 통과
4. Telegram 원격 제어 가능
5. 무중단 밤샘 실행 가능
6. PC/Android 동일 코드 실행 가능
```
