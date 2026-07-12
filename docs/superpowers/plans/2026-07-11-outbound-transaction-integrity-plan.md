# 출고/배정 상태전이 정합성 수정 계획 (감사 #3)

작성일: 2026-07-11
대상 버전: v8.8.4
근거: 세션 심층 감사(다단계 트랜잭션 정합성 축) 결과
상태: 착수 — Tier 1 F 부터

---

## 근본 원인

엔진(`SQMInventoryEngineV3`)은 **단일 트랜잭션 + 트랜잭션 내 무결성 검증**으로 상태전이를
안전하게 처리한다(`process_outbound`, `execute_reserved`, `cancel_reservation` 등 정식 경로).
그런데 일부 API 엔드포인트(`allocation_api.py`, `status_revert_api.py`)가 **엔진을 우회해
raw-SQL** 로 상태만 바꿔 정합성이 깨진다. 이 우회 경로가 대부분 심각 이슈의 근원이다.

## 전략

1. 모든 상태전이를 **엔진의 검증된 경로로 통일**.
2. 동시요청 가드를 **트랜잭션 안**으로 + UPDATE에 status 가드.
3. 에러 조용히 삼킴 제거, 사후검증을 커밋 전으로.
4. **각 수정마다 재현 회귀 테스트 먼저** (데이터 무결성 버그이므로 필수).

## 불변식 (지켜야 함)

- 재고 상태 흐름: `PENDING → AVAILABLE → PICKED → SOLD`
- LOT 무결성: `initial_weight = current_weight + picked_weight` 항상 성립
- 출고/입고 트랜잭션은 All-or-Nothing

---

## 항목별 계획 (심각도/위치)

### Tier 1 — 명확·상대적 저위험 (먼저)

| # | 위치 | 문제 | 수정 방향 | 재현 테스트 |
|---|---|---|---|---|
| **F** | `engine_modules/inventory_modular/outbound_mixin.py:3156-3190` | 이중출고 가드가 트랜잭션 밖에서 검사 + 실행 UPDATE에 status 가드 없음 → 동시/더블클릭 시 이중 SOLD | 톤백 UPDATE에 `WHERE ... status='PICKED'` 가드 + 가드 검사를 트랜잭션 안으로 | 동시 confirm 2회 → sold_table 1행, 무게 보존 |
| **D** | `backend/api/status_revert_api.py:296-323, 371-406` | AVAILABLE→PENDING 되돌리기 후 recalc 버킷에 PENDING 없어 무게 소멸 → 무결성 붕괴 | recalc 버킷에 PENDING 반영 or 되돌리기 시 무게 보존 | 되돌린 뒤 `initial=current+picked` 성립 |
| **M3** | `backend/api/allocation_api.py:718-773, 1528-1622` | 우회 엔드포인트 오류경로에서 열린 트랜잭션/연결 누수 → 락 | `try/finally` 로 rollback+close 보장 | 오류 주입 후 다음 요청 미잠금 |

### Tier 2 — 신중 (핵심 경로 재구성)

| # | 위치 | 문제 | 수정 방향 |
|---|---|---|---|
| **C** | `backend/api/allocation_api.py:1584-1601` | confirm 이 UPDATE 2개만 → 톤백/sold_table/movement/무게 누락 → LOT wedge | 엔진 `confirm_outbound()` 호출로 대체 |
| **M4** | `allocation_api.py:1528-1539` | cancel 이 톤백/무게 미복원 → 고아 예약 | 엔진 `cancel_reservation()` 로 대체 |
| **M1** | `outbound_mixin.py:3024-3059` | sold_table INSERT 실패 조용히 삼킴 | 삼킴 제거 / 사후 존재검증 |
| **M2** | `outbound_mixin.py:3196-3235` | 사후검증이 커밋 후 실행 → 롤백 불가 | 검증을 커밋 전(트랜잭션 안)으로 |

### Tier 3 — 분리창 SSE 멱등성 (별개 성격)

| # | 위치 | 문제 | 수정 방향 |
|---|---|---|---|
| **E** | `backend/api/popout.py:166-167`, `frontend/js/sqm-popout.js:97` | d2m 재생 + 자동재연결 → 부수효과 액션 중복 실행 | Last-Event-ID/dedup, 부수효과 액션 재생 금지 |

---

## 실행 순서

Tier 1(F→D→M3) → Tier 2(C→M4→M1→M2) → Tier 3(E). 각 항목: **재현 테스트 추가 → 수정 →
(399 + 신규) 그린 → PR → 확인·머지**. Tier 2 C는 응답 형태·입력 호환성 먼저 확인.

## 참고

엔진 정식 경로는 이미 단일 IMMEDIATE 트랜잭션 + 무결성 검증으로 보호됨. 본 작업은
**그것을 우회하는 지름길들을 정식 경로로 되돌리는** 것이 핵심이다.
