---
description: 85개 기능 마이그레이션 진행 상황을 한눈에 보여줍니다
---

# /feature-status

## 수행할 작업

1. `docs/handoff/feature_matrix.json` 로드
2. 각 기능의 현재 상태 점검:
   - `backend/api/` 하위에 엔드포인트 존재 여부
   - `frontend/js/handlers/`에 핸들러 존재 여부
   - Git 커밋 로그에서 해당 기능 커밋 검색
3. 상태 요약 표 출력

## 출력 예시

```
📊 SQM v864.3 Migration Status

Total Features: 85
✅ Completed:    12 (14.1%)
🚧 In Progress:   3 (3.5%)
⏳ Pending:      70 (82.4%)

Tier 1 (Shell):     ✅ DONE
Tier 2 (Top 10):    🚧 3/10 in progress
Tier 3 (Rest 75):   ⏳ not started

Recent Completions:
  ✅ F001 - PDF 입고
  ✅ F002 - 즉시 출고
  ✅ F005 - 재고 조회

Currently Working On:
  🚧 F008 - 정합성 검사
  🚧 F012 - Dashboard 표시

Next Up:
  ⏳ F003 - 반품 처리
  ⏳ F004 - 백업
```

## 상태 판정 기준

| 상태 | 조건 |
|---|---|
| ✅ Completed | Backend + Frontend + Git 커밋 존재 AND verify-parity PASS |
| 🚧 In Progress | 일부만 구현됨 |
| ⏳ Pending | 시작 전 |
| ⚠️ Blocked | 외부 의존성 대기 |
