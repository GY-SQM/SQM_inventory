# BARCODE Scan QA Checklist (v6.2.3)

## 1) 사전 준비

- DB에 `PICKED` 상태 데이터가 존재해야 함
- 가능하면 `sale_ref`가 2개 이상인 샘플을 준비해 `sale_ref` 단일 선택 검증
- 스캔 파일 3종 준비
  - PASS 케이스 파일
  - FAIL 케이스 파일(누락/초과 포함)
  - PASS_SWAP 케이스 파일(같은 LOT 내부 스왑)

## 2) 기본 동작 검증

### T1. 스캔 파일 1회 읽기

- 메뉴: 출고 > 바코드 스캔 업로드
- 파일 선택 후 검증/실행까지 진행
- 기대 결과
  - 파일 재선택 요구 없음
  - 처리 시간 중 불필요한 지연 없음

### T2. sale_ref 단일 선택

- `PICKED` 데이터에 서로 다른 `sale_ref`가 2개 이상인 상태에서 실행
- 기대 결과
  - `SALE REF 선택` 입력창 노출
  - 목록 외 값 입력 시 오류 팝업 후 중단
  - 유효한 값 1개 입력 시 다음 단계 진행

### T3. 재검증(TOCTOU 방지)

- 첫 검증 통과 후 실행 직전, 다른 세션에서 `PICKED` 상태를 임의 변경
- 기대 결과
  - 재검증 실패 팝업
  - SOLD 전환 미실행

## 3) 결과 케이스 검증

### T4. PASS

- `PICKED`와 스캔 UID가 정확히 일치하도록 파일 준비
- 기대 결과
  - `UID 대조 통과` 메시지
  - 실행 후 `sold` 수량 = 스캔 수량
  - `remaining_picked`가 sale_ref 기준으로 감소

### T5. FAIL (누락/초과/중복)

- 누락 UID, 초과 UID, 중복 UID를 각각 포함한 파일로 테스트
- 기대 결과
  - FAIL 팝업으로 출고 중단
  - 누락/초과 상위 목록 표시
  - 중복은 하드스톱

### T6. PASS_SWAP (LOT 내부 스왑)

- 같은 LOT에서만 expected/scanned UID가 교차되도록 준비
- 기대 결과
  - `PASS_SWAP` 조건부 통과 메시지
  - 실행 시 swap_count 증가
  - `uid_swap_history` 기록 생성

## 4) 포맷/정규화 검증

### T7. 인코딩 폴백

- TXT/CSV 파일을 각각 `utf-8`, `cp949`로 생성해 테스트
- 기대 결과
  - 디코딩 에러 없이 UID 읽기

### T8. 헤더/공백/특수문자 정리

- 첫 줄에 `UID` 또는 `BARCODE` 헤더 포함
- UID 앞뒤 공백, BOM/제로폭 문자를 포함한 데이터 준비
- 기대 결과
  - 헤더 행 자동 제외
  - UID 정규화 후 정상 매칭

### T9. sub_lt 숫자 정규화

- DB `sub_lt=1`, 스캔값 `001` 형태로 테스트
- 기대 결과
  - 동일 값으로 인식되어 매칭 성공

## 5) DB 확인 포인트

### T10. 이력/상태 검증

- 실행 후 아래 테이블 확인
  - `inventory_tonbag` 상태: `PICKED -> SOLD`
  - `sold_table` 삽입 건수
  - `picking_table` 상태 반영(`ACTIVE -> SOLD`)
  - `stock_movement` SOLD 이벤트 기록
  - `uid_verify_history` 기록 (`sale_ref` 포함)

## 6) 회귀 리스크 확인

- LOT 단위 예약 모드(`PICKED` 없음 + `allocation_plan RESERVED tonbag_id NULL`)에서 기존 동작 유지 확인
- `sale_ref`가 1개일 때는 선택창 없이 바로 진행되는지 확인
- `sale_ref`가 없는 데이터에서도 정상 처리되는지 확인

## 7) 완료 기준

- T1~T10 모두 통과
- FAIL 케이스에서 데이터 변경(상태 전이) 없음
- PASS/PASS_SWAP에서만 SOLD 전환 발생
- 운영자 관점에서 메시지가 원인 파악 가능 수준인지 확인
