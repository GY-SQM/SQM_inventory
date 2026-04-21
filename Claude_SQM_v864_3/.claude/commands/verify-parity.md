---
description: v864.2와 v864.3의 UI/기능 일치도를 검증합니다
argument-hint: <scope> (tier1 | tier2 | F001 등 특정 기능)
---

# /verify-parity

사용법:
- `/verify-parity tier1` — Tier 1 전체 Smoke Test
- `/verify-parity tier2` — Tier 2 완료된 모든 기능 회귀 테스트
- `/verify-parity F001` — 특정 기능만 검증

## 수행할 작업

### Scope = tier1

1. `backend/main.py` 실행 (백그라운드)
2. PyWebView 창 스크린샷 캡처 → `docs/verify/tier1_actual.png`
3. v864.2 참조 스크린샷과 SSIM 비교
4. TIER1_PLAN.md의 Smoke Test 체크리스트 자동 실행 가능한 항목 수행:
   - 7개 메뉴 클릭 테스트
   - 9개 사이드바 탭 전환
   - 테마 토글
   - FastAPI `/docs` 접근

### Scope = F### (개별 기능)

1. `docs/handoff/feature_matrix.json`에서 해당 ID 정보 로딩
2. v864.2 원본에서 같은 입력으로 실행한 결과 확인 (기록된 것)
3. v864.3에서 동일 입력으로 fetch 호출
4. 결과 비교:
   - JSON 응답 diff
   - 에러 처리 방식
   - UI 표시 방식

### Scope = tier2

1. feature_matrix.json에서 `"tier2_status": "completed"` 필터링
2. 각 기능 개별 검증 (위 Scope = F### 방식 반복)
3. 요약 리포트 `docs/verify/tier2_report.md` 생성

## 출력 형식

```markdown
# Parity Verification Report

**Scope:** tier1
**Date:** 2026-04-XX
**Result:** ✅ PASS (SSIM 0.89)

## UI Comparison
- v864.2 vs v864.3: SSIM 0.89 (목표 0.85 이상)
- Layout differences: 없음

## Functional Tests
| 항목 | 결과 |
|---|---|
| 7개 메뉴 드롭다운 | ✅ |
| 9개 탭 전환 | ✅ |
| 테마 토글 | ✅ |
```

## 실패 시 동작

- SSIM < 0.85 → 에러 발생, 사장님께 차이점 스크린샷 보고
- 기능 불일치 → 해당 기능 커밋 `git revert`로 즉시 롤백 제안
- 전체 실패율 > 20% → Tier 자체 재설계 권고
