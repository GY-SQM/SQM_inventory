# GPT_SQM_P0-1_DB스키마점검표.md
생성일: 2026-04-04 15:12 (Asia/Seoul)  
기준 원본: `Claude_SQM_v867.zip`  
참조 문서: `MASTER_FINAL_v867_통합완성본.md`, `GPT_SQM_P0-1_초상세_작업지시서.md`, `GPT_SQM_P0-1_수정대상파일표.md`

---

## [질문]
다음 단계로 `P0-1_DB스키마점검표.md`를 작성해 달라는 요청

## [질문의도]
P0-3에서 write API를 붙이기 전에,  
DB 스키마 때문에 중간에 실패하지 않도록 **사전 점검 기준표**를 만든다.

이번 문서의 목적은 아래와 같다.

```text
1. audit_log / outbound_event_log 구조를 먼저 점검한다
2. write API가 요구하는 최소 컬럼을 정리한다
3. 누락/불일치 시 migration 필요 여부를 판정한다
4. P0-3에서 rollback/logging 단계가 DB 때문에 깨지지 않게 한다
```

---

# [응답]

# 1. 이번 점검표의 위치

이 문서는 **실제 DB를 바로 수정하는 문서가 아니다.**  
먼저 아래를 판정하는 문서다.

- 테이블이 있는가
- 필요한 컬럼이 있는가
- 타입/nullable/default가 맞는가
- migration이 필요한가
- 지금 단계에서 즉시 수정해야 하는가, 다음 단계로 넘겨도 되는가

즉, 이번 문서는 **“DB 위험 사전 감지표”**다.

---

# 2. 점검 원칙

## 2-1. 절대 원칙
```text
- 실DB를 먼저 직접 변경하지 않는다
- 먼저 schema를 조회하고 비교표를 만든다
- write API에서 실제 필요한 최소 컬럼부터 본다
- 없어도 당장 치명적이지 않은 컬럼과 반드시 필요한 컬럼을 구분한다
- migration은 필요 판정 후 별도 적용한다
```

## 2-2. 이번 단계에서 우선 보는 테이블
```text
1. audit_log
2. outbound_event_log
```

## 2-3. 보조적으로 같이 봐야 할 항목
```text
- outbound / outbound_item 계열 참조 가능성
- tonbag / lot / inventory 식별 컬럼명 일관성
- created_at / updated_at / timestamp 계열 표기 방식
```

---

# 3. 왜 이 점검이 필요한가

P0 설계 기준상, 앞으로 아래 write API들이 추가된다.

- `POST /files/upload`
- `POST /inbound/create`
- `POST /outbound/execute`
- `PUT /outbound/cancel`
- `PUT /location/update`

그리고 마스터 문서는 아래를 요구한다.

- 모든 write API는 트랜잭션 보호
- 실패 시 rollback
- 성공/실패 로그 남기기
- 기존 `engine_modules` 로직 재사용  
fileciteturn10file0 fileciteturn10file1

따라서 `audit_log`나 `outbound_event_log`가 맞지 않으면 아래 문제가 생긴다.

```text
- API는 성공했는데 로그 저장에서 실패
- rollback 도중 로그 테이블 mismatch 발생
- 취소/실행 이력을 남기려는데 컬럼이 없어 예외 발생
- timestamp/default 문제로 insert 실패
```

---

# 4. 점검 대상 테이블 정의

| 테이블 | 목적 | 중요도 | 이번 단계 처리 |
|---|---|---|---|
| `audit_log` | 공통 감사 로그 | 매우 높음 | 필수 점검 |
| `outbound_event_log` | 출고 실행/취소 이벤트 로그 | 매우 높음 | 필수 점검 |

---

# 5. 점검 절차

## Step 1. 테이블 존재 확인
- [ ] `audit_log` 존재 여부 확인
- [ ] `outbound_event_log` 존재 여부 확인

## Step 2. 컬럼 목록 추출
- [ ] 각 테이블의 전체 컬럼명 추출
- [ ] PK/타입/null/default 추출
- [ ] 인덱스 존재 여부 확인

## Step 3. 최소 필요 컬럼과 비교
- [ ] write API 최소 컬럼 기준표와 비교
- [ ] 누락 컬럼 표시
- [ ] 이름은 다르지만 의미상 대응 가능한 컬럼 표시

## Step 4. 판정
- [ ] 즉시 migration 필요
- [ ] 추후 보강 가능
- [ ] 현재 스키마로도 P0 진행 가능
중 하나로 판정

---

# 6. audit_log 최소 필요 컬럼 기준

## 6-1. 목적
공통 write API 성공/실패/rollback/예외 흐름을 기록할 수 있어야 한다.

## 6-2. 최소 필요 컬럼(권장 기준)
| 컬럼명 | 의미 | 필수 여부 | 허용 대체명 예시 | 비고 |
|---|---|---|---|---|
| `id` | PK | 필수 | - | INTEGER PK 권장 |
| `action_type` | 동작 종류 | 필수 | `action`, `event_type` | 예: inbound_create, outbound_execute |
| `status` | 결과 상태 | 권장 | `result`, `state` | success / failed / rolled_back |
| `message` | 요약 메시지 | 권장 | `detail`, `summary` | 사용자/개발자 확인용 |
| `payload_json` | 원요청/핵심 파라미터 | 권장 | `data`, `payload`, `raw_json` | JSON text 가능 |
| `error_message` | 오류 내용 | 권장 | `error`, `exception_message` | 실패 시 중요 |
| `source_module` | 호출 모듈 | 권장 | `module`, `source` | react_api/actions 등 |
| `created_at` | 생성 시각 | 필수 | `timestamp`, `logged_at` | DEFAULT CURRENT_TIMESTAMP 권장 |

## 6-3. 추가로 있으면 좋은 컬럼
| 컬럼명 | 의미 |
|---|---|
| `user_id` | 사용자 식별 |
| `lot_no` | 관련 LOT |
| `tonbag_no` | 관련 톤백 |
| `request_id` | 요청 추적 |
| `trace_id` | 장애 추적 |

## 6-4. audit_log 점검표
| 점검 항목 | 확인 결과 | 판정 | 비고 |
|---|---|---|---|
| 테이블 존재 |  |  |  |
| PK 존재 |  |  |  |
| `action_type` 또는 대체 컬럼 존재 |  |  |  |
| `status` 또는 대체 컬럼 존재 |  |  |  |
| `message` 또는 대체 컬럼 존재 |  |  |  |
| `payload_json` 또는 대체 컬럼 존재 |  |  |  |
| `error_message` 또는 대체 컬럼 존재 |  |  |  |
| `source_module` 또는 대체 컬럼 존재 |  |  |  |
| `created_at` 또는 대체 컬럼 존재 |  |  |  |
| timestamp default 존재 |  |  |  |
| NOT NULL 제약이 과도하지 않은지 |  |  |  |

---

# 7. outbound_event_log 최소 필요 컬럼 기준

## 7-1. 목적
출고 실행/취소/실패/재시도 등 이벤트 흐름을 남길 수 있어야 한다.

## 7-2. 최소 필요 컬럼(권장 기준)
| 컬럼명 | 의미 | 필수 여부 | 허용 대체명 예시 | 비고 |
|---|---|---|---|---|
| `id` | PK | 필수 | - | INTEGER PK 권장 |
| `outbound_id` | 출고 레코드 식별 | 권장 | `out_id`, `shipment_id` | 없으면 최소 event 단위 기록만 가능 |
| `lot_no` | LOT 식별 | 권장 | `lot` | 핵심 추적용 |
| `tonbag_no` | 톤백 식별 | 권장 | `tonbag_id`, `bag_no` | 취소/실행 추적 중요 |
| `event_type` | 이벤트 종류 | 필수 | `action_type`, `event` | execute / cancel / fail |
| `status` | 이벤트 결과 | 권장 | `result`, `state` | success / failed / rolled_back |
| `quantity` | 관련 수량 | 선택 | `qty`, `amount` | 출고량 기록용 |
| `destination` | 출고처 | 선택 | `ship_to`, `customer` | 실무상 유용 |
| `message` | 요약 메시지 | 권장 | `detail` | |
| `payload_json` | 원요청/핵심 파라미터 | 권장 | `data`, `payload` | |
| `created_at` | 기록 시각 | 필수 | `timestamp`, `event_time` | DEFAULT CURRENT_TIMESTAMP 권장 |

## 7-3. 추가로 있으면 좋은 컬럼
| 컬럼명 | 의미 |
|---|---|
| `error_message` | 실패 이유 |
| `source_module` | 호출 모듈 |
| `request_id` | 추적 |
| `sales_order_no` | 영업 주문 연계 |
| `allocation_id` | 배정 연계 |

## 7-4. outbound_event_log 점검표
| 점검 항목 | 확인 결과 | 판정 | 비고 |
|---|---|---|---|
| 테이블 존재 |  |  |  |
| PK 존재 |  |  |  |
| `event_type` 또는 대체 컬럼 존재 |  |  |  |
| `status` 또는 대체 컬럼 존재 |  |  |  |
| `lot_no` 또는 대체 컬럼 존재 |  |  |  |
| `tonbag_no` 또는 대체 컬럼 존재 |  |  |  |
| `message` 또는 대체 컬럼 존재 |  |  |  |
| `payload_json` 또는 대체 컬럼 존재 |  |  |  |
| `created_at` 또는 대체 컬럼 존재 |  |  |  |
| timestamp default 존재 |  |  |  |
| 출고 취소 이벤트 기록 가능 구조인지 |  |  |  |

---

# 8. 타입 / 제약조건 점검표

## 8-1. 타입 기준
| 항목 | 권장 타입 | 이유 |
|---|---|---|
| PK | INTEGER | SQLite 친화적 |
| JSON payload | TEXT | SQLite JSON text 저장 |
| message/error | TEXT | 길이 유연성 |
| created_at | TEXT 또는 DATETIME | CURRENT_TIMESTAMP 호환 |
| status/event_type | TEXT | 확장 용이 |

## 8-2. 제약조건 점검
| 항목 | 권장 기준 | 판정 질문 |
|---|---|---|
| `created_at` | DEFAULT CURRENT_TIMESTAMP | insert 시 값 누락돼도 저장 가능한가 |
| `message` | NULL 허용 가능 | 실패 로그에서 비어도 저장 가능한가 |
| `payload_json` | NULL 허용 가능 | 일부 단순 이벤트도 저장 가능한가 |
| `error_message` | NULL 허용 가능 | 성공 이벤트 insert 가능한가 |
| `status` | NULL보다 NOT NULL 권장 | 기본값 없으면 insert 실패 위험은 없는가 |

---

# 9. 인덱스 점검 기준

로그 테이블은 과도한 인덱스가 꼭 필요하진 않지만, 아래는 있으면 좋다.

## 9-1. audit_log 권장 인덱스
- [ ] `created_at`
- [ ] `action_type`
- [ ] `status`

## 9-2. outbound_event_log 권장 인덱스
- [ ] `created_at`
- [ ] `event_type`
- [ ] `lot_no`
- [ ] `tonbag_no`

## 9-3. 판정표
| 테이블 | 인덱스 컬럼 | 존재 | 필요도 | 비고 |
|---|---|---|---|---|
| audit_log | created_at |  |  |  |
| audit_log | action_type |  |  |  |
| audit_log | status |  |  |  |
| outbound_event_log | created_at |  |  |  |
| outbound_event_log | event_type |  |  |  |
| outbound_event_log | lot_no |  |  |  |
| outbound_event_log | tonbag_no |  |  |  |

---

# 10. Migration 필요 여부 판정 기준

## 즉시 migration 필요
아래 중 하나라도 해당하면 즉시 migration 필요로 본다.

- [ ] 테이블 자체가 없다
- [ ] `created_at` 계열이 없다
- [ ] `event_type`/`action_type` 계열이 없다
- [ ] insert 시 필수인데 nullable/default가 맞지 않아 저장이 불가능하다
- [ ] 출고 취소 이벤트를 남길 최소 컬럼이 없다

## 추후 보강 가능
아래는 P0 진행은 가능하나 나중 보강 대상이다.

- [ ] `payload_json`이 없다
- [ ] `source_module`이 없다
- [ ] 인덱스가 부족하다
- [ ] `status`가 없어도 message 기반 임시 기록은 가능하다

## 현재 진행 가능
아래면 P0-3까지 진행 가능하다.

- [ ] 테이블 존재
- [ ] 최소 핵심 컬럼 존재
- [ ] insert 실패를 일으킬 치명 제약이 없음
- [ ] timestamp/default가 동작함

---

# 11. 실제 점검 출력 양식

## 11-1. audit_log 실제 기록표
| 컬럼명 | 타입 | NOT NULL | DEFAULT | 필요도 | 상태(있음/없음/대체) | 비고 |
|---|---|---|---|---|---|---|

## 11-2. outbound_event_log 실제 기록표
| 컬럼명 | 타입 | NOT NULL | DEFAULT | 필요도 | 상태(있음/없음/대체) | 비고 |
|---|---|---|---|---|---|---|

## 11-3. 최종 판정표
| 테이블 | 판정 | 이유 | 다음 조치 |
|---|---|---|---|
| audit_log |  |  |  |
| outbound_event_log |  |  |  |

---

# 12. SQL 점검 예시

아래 SQL은 구조 확인용 예시다.

```sql
PRAGMA table_info(audit_log);
PRAGMA table_info(outbound_event_log);

SELECT name, sql
FROM sqlite_master
WHERE type='table'
  AND name IN ('audit_log', 'outbound_event_log');

SELECT name, tbl_name, sql
FROM sqlite_master
WHERE type='index'
  AND tbl_name IN ('audit_log', 'outbound_event_log');
```

---

# 13. 실패/위험 시 조치 기준

## 위험 1. 테이블 없음
- [ ] 즉시 migration 초안 작성
- [ ] P0-3 진입 보류 여부 판단
- [ ] 임시 fallback logging 허용 여부 검토

## 위험 2. 컬럼명 불일치
- [ ] 대체 컬럼으로 맵핑 가능한지 판단
- [ ] adapter/service 레이어에서 alias 처리 가능한지 검토
- [ ] 아니면 migration 필요 판정

## 위험 3. DEFAULT/NULL 제약 문제
- [ ] API insert 예시와 함께 재점검
- [ ] 최소 insert payload로 저장 가능한지 확인
- [ ] 저장 불가면 우선 migration 또는 insert 로직 보정 필요

## 위험 4. 인덱스 없음
- [ ] P0 즉시 차단 사유는 아님
- [ ] 성능 이슈 가능성만 메모
- [ ] 후속 patch로 분리 가능

---

# 14. P0-1 완료 기준(이 문서 기준)

- [ ] `audit_log` 실제 점검표 작성 완료
- [ ] `outbound_event_log` 실제 점검표 작성 완료
- [ ] migration 필요 여부 판정 완료
- [ ] write API 전 위험 요소 목록 작성 완료

---

# 15. 루비 최종 판단

이번 문서의 핵심은 아래다.

```text
P0-1에서 DB를 먼저 뜯어고치는 것이 목적이 아니다.
write API와 rollback/logging이 실패하지 않도록,
어디가 위험한지 먼저 정확히 발견하고 판정하는 것이 목적이다.
```

즉, 이번 단계는 **스키마 수리**가 아니라 **스키마 판정**이다.

---

# 16. 다음 단계 권장

다음으로 가장 자연스럽게 이어질 문서는 아래다.

1. `P0-1_실행파일연동점검표.md`

루비 권장:
```text
이제 DB 축이 정리됐으니, 다음은 run.py / run_bootstrap.py / run_react.bat / .env 축을 정리하는 것이 맞다.
```
