# GPT_P2_BATCH_B_DEBUG_ANALYSIS.md
작성일: 2026-04-07

## 목적
Batch B 진행 중 발생할 수 있는 오류를 **최대한 세분화**하여 원인별로 분리하고,
`outbound_mixin.py` 분해 과정에서 어디서부터 점검해야 하는지 실전 기준으로 정리한다.

---

## 1. 최우선 위험 구간

### B-DBG-01. scan → SOLD 정책 붕괴
증상:
- 스캔 전인데 SOLD 상태로 반영됨
- RESERVED / AVAILABLE 상태도 scan 처리됨
- outbound_item만 SOLD, inventory_tonbag는 미반영

원인 후보:
1. 상태 검증 로직이 Service가 아니라 UI 또는 mixin 잔여 코드에 남아 있음
2. `ALLOWED_SCAN_SOURCE_STATES`가 잘못 정의됨
3. `outbound_mixin.py` 기존 코드가 Service 호출 후에도 추가 UPDATE 수행

확인 포인트:
- `OutboundService.confirm_scan_and_mark_sold()` 내부의 source state 검증
- `outbound_mixin.py` 안에 `status='SOLD'` 직접 SQL 존재 여부
- `tests/test_outbound_scan_policy.py` 결과

즉시 조치:
- SOLD 관련 SQL을 전수검색
- `outbound_mixin.py`에서 직접 UPDATE 제거
- Service만 상태전이 결정하도록 고정

---

### B-DBG-02. transaction 붕괴
증상:
- inventory_tonbag만 SOLD 됨
- stock_movement INSERT 누락
- outbound_item status 미변경
- 중간 예외 후 일부만 반영

원인 후보:
1. `with transaction()` 바깥에서 UPDATE 수행
2. repo 내부에서 commit()이 흩어져 있음
3. 예외 발생 후 rollback 누락

확인 포인트:
- `OutboundWriteRepository.transaction()` 사용 여부
- `self.conn.commit()` 직접 호출 위치
- `mark_tonbag_sold`, `update_outbound_item_status`, `insert_stock_movement`가 같은 블록 안에 있는지

즉시 조치:
- transaction boundary를 Service 1곳 또는 WriteRepo 1곳으로 통일
- repo 내부 개별 commit 제거
- 실패 테스트 추가

---

### B-DBG-03. Query/Write 분리 실패
증상:
- `outbound_query.py`, `outbound_repository.py`를 만들었는데도 `outbound_mixin.py`에 SQL이 여전히 많음
- 구조는 분리됐지만 실제로는 기존 코드가 그대로 작동

원인 후보:
1. 신규 repo 파일만 만들고 기존 호출부 치환 미완료
2. 일부 helper 함수가 여전히 mixin 내부 SQL을 사용
3. UI adapter가 아니라 실제 업무 로직이 mixin에 잔존

확인 포인트:
- `SELECT `, `UPDATE `, `INSERT ` 문자열이 `outbound_mixin.py`에 남아있는지
- `.cursor().execute(` 호출 잔존 여부
- `self.conn.execute(` 잔존 여부

즉시 조치:
- 정규식/grep으로 SQL 흔적 전수 검색
- mixin은 입력 수집 + 메시지 표시만 남기기
- 업무 로직은 Service로 이동

---

### B-DBG-04. UI 성공 / DB 실패 불일치
증상:
- 화면에는 출고 완료 메시지
- 실제 DB는 반영 안 됨
- refresh 후 상태가 되돌아감

원인 후보:
1. result.success 판정 전에 UI success 메시지 출력
2. 예외가 내부에서 삼켜짐
3. refresh 함수가 stale state를 보여줌

확인 포인트:
- `result.success` 체크 후 메시지 순서
- `try/except`에서 예외 재전파 여부
- UI refresh 시 DB 재조회 여부

즉시 조치:
- success toast/message는 `result.success is True` 이후만 허용
- 예외 숨기지 말고 로그 남기기
- refresh는 query repo 재호출로 고정

---

### B-DBG-05. 테스트는 PASS인데 운영이 FAIL
증상:
- 단위테스트는 통과
- 실제 프로젝트에서는 실패

원인 후보:
1. 메모리 SQLite와 실제 스키마 차이
2. 실제 status 값 표준화 미흡
3. 실제 테이블 컬럼 차이
4. 실제 UI에서 tonbag_no 전처리 문제

확인 포인트:
- 실제 DB schema와 테스트 schema 비교
- status 값 목록 확인
- tonbag_no 문자열 전처리 확인

즉시 조치:
- smoke test를 실제 DB 복사본 기준으로 추가
- schema assertion 추가
- 실제 샘플 tonbag_no 케이스 테스트

---

## 2. 디버깅 우선순위

1. `outbound_mixin.py`에 SQL 잔존 여부 확인
2. transaction 범위 확인
3. scan source state 규칙 확인
4. 단위테스트 + 실제 DB smoke test 분리 확인
5. UI success/refresh 순서 확인

---

## 3. 실패 유형별 빠른 판단표

| 증상 | 가장 의심할 위치 | 1차 조치 |
|---|---|---|
| PICKED 아닌데 SOLD 됨 | state_rules / service / mixin 잔여 SQL | source state 검증 및 mixin SQL 제거 |
| 일부 테이블만 반영 | transaction boundary | commit/rollback 통일 |
| 테스트는 PASS, 운영 FAIL | schema / 실제 status / 전처리 | 실제 DB smoke test 추가 |
| 화면은 성공인데 DB 미반영 | UI adapter / success 메시지 순서 | result.success 이후 표시 |
| repo 분리했는데 코드가 복잡 | mixin 호출부 치환 미완 | SQL 전수검색 후 제거 |

---

## 4. 반드시 추가할 로그

```python
logger.info("[OUTBOUND][SCAN] start tonbag=%s", tonbag_no)
logger.info("[OUTBOUND][SCAN] source_status=%s", current_status)
logger.info("[OUTBOUND][SCAN] mark_sold affected=%s", affected_tonbag)
logger.info("[OUTBOUND][SCAN] outbound_item updated")
logger.info("[OUTBOUND][SCAN] stock_movement inserted")
logger.info("[OUTBOUND][SCAN] success")
```

예외 로그:
```python
logger.exception("[OUTBOUND][SCAN] failed tonbag=%s", tonbag_no)
```

---

## 5. 결론

Batch B에서 가장 중요한 것은
- `정책 보존`
- `transaction 보존`
- `mixin의 SQL 제거`
이다.

즉, 구조를 예쁘게 만드는 것보다
**scan → SOLD 정책이 정확히 유지되는지**를 먼저 검증해야 한다.
