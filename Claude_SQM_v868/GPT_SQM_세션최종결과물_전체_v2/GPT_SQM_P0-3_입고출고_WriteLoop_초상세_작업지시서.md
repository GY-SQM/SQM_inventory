# GPT_SQM_P0-3_입고출고_WriteLoop_초상세_작업지시서.md
생성일: 2026-04-04 15:38 (Asia/Seoul)  
기준 원본: `Claude_SQM_v867.zip`  
참조 문서:  
- `MASTER_FINAL_v867_통합완성본.md`
- `GPT_SQM_P0_통합체크리스트_v2.md`
- `GPT_SQM_P0-1_완료보고서.md`
- `GPT_SQM_P0-2_LOT상세모달_초상세_작업지시서.md`
- `GPT_SQM_P0-2_LOT상세모달_테스트체크리스트.md`

---

## [질문]
다음 단계로 **P0-3 입고/출고 write loop 초상세 작업지시서**를 작성해 달라는 요청

## [질문의도]
P0-2에서 React의 첫 read 동작을 정리한 다음,  
이제 P0-3에서 실제 업무 핵심인 **입고/출고 write loop**를 구현할 수 있도록  
파일, API, parser, engine adapter, rollback, 테스트 게이트까지 포함한 실행 기준서를 만든다.

---

# [응답]

# 1. P0-3의 목표

P0-3은 이번 전환 작업의 핵심 단계다.  
이번 단계의 본질은 아래와 같다.

```text
1. 파일 업로드부터 입고 생성까지 실제로 돈다
2. 출고 실행과 출고 취소가 실제 engine 로직과 연결된다
3. 모든 write 동작이 transaction + rollback 구조를 따른다
4. parser → preview → confirm → create/execute/cancel 흐름이 React/FastAPI에서 실제 동작한다
```

---

# 2. P0-3 완료 정의

아래 조건이 모두 만족되면 P0-3 완료로 본다.

- [ ] `POST /files/upload`가 실제 parser와 연결된다
- [ ] PDF 업로드 preview가 실제로 생성된다
- [ ] Excel 업로드 preview가 실제로 생성된다
- [ ] `POST /inbound/create`가 실제 `process_inbound()` 또는 동등 로직과 연결된다
- [ ] `POST /outbound/execute`가 실제 `process_outbound()` 또는 동등 로직과 연결된다
- [ ] `PUT /outbound/cancel`이 실제 `cancel_outbound_tonbag()` 또는 동등 로직과 연결된다
- [ ] 실패 시 rollback이 실제로 검증된다
- [ ] 성공/실패 로그가 저장된다
- [ ] React 모달에서 preview → confirm 흐름이 동작한다

---

# 3. 이번 단계의 직접 근거

마스터 문서는 쓰기 API 추가 대상으로 아래를 명시한다.

- `POST /inbound/create`
- `POST /outbound/execute`
- `PUT /outbound/cancel`
- `PUT /location/update`
- `POST /files/upload`

또한 아래 원칙을 요구한다.

- 기존 `engine_modules` 핵심 로직 재사용
- FastAPI에 완전 신규 업무 로직 생성 금지
- 모든 write API는 트랜잭션 보호
- 실패 시 rollback
- 성공/실패 로그 남기기  
fileciteturn10file0 fileciteturn10file1

따라서 P0-3은 단순 API 추가가 아니라  
**실제 engine 연결 + parser 연결 + rollback 검증 단계**로 봐야 한다.

---

# 4. P0-3 범위

## 포함
- `POST /files/upload`
- `POST /inbound/create`
- `POST /outbound/execute`
- `PUT /outbound/cancel`
- InboundParseModal 실제 흐름
- OutboundExecuteModal 실제 흐름
- parser 연결
- engine adapter 연결
- transaction / rollback / audit/event log
- preview → confirm → write 흐름

## 제외
- `PUT /location/update` (P0-4)
- 전체 통합 실행(bat/env/tkinter 동시 실행) 최종 완성 (P0-4)
- 보안 고도화
- 성능 최적화 고도화
- 고급 대시보드

---

# 5. 수정 대상 파일

## 5-1. Frontend 직접 수정 파일
| 파일 | 역할 | P0-3 작업 |
|---|---|---|
| `web/src/components/modals/InboundParseModal.jsx` | 입고 파싱 모달 | upload / preview / confirm 실동작 |
| `web/src/components/modals/OutboundExecuteModal.jsx` | 출고 실행 모달 | execute / cancel 실동작 |
| `web/src/api/actionApi.js` | write API 래퍼 | upload/create/execute/cancel 함수 구현 |
| `web/src/App.jsx` | 모달 mount/state 보조 | 필요 시 연결 |
| 관련 page 파일 | 모달 진입점 | 입고/출고 메뉴 또는 버튼 연결 |

## 5-2. Backend 직접 수정 파일
| 파일 | 역할 | P0-3 작업 |
|---|---|---|
| `react_api/routes/actions.py` | write API route | 실제 엔드포인트 구현 |
| `react_api/schemas/actions.py` | request/response schema | 실 요청 필드 확정 |
| `react_api/services/action_service.py` | service layer | parser/transaction/logging 흐름 구현 |
| `react_api/services/engine_adapter.py` | engine bridge | 실제 engine wrapper 구현 |
| `react_api/main.py` | router 등록 | 이미 되었으면 점검만 |

## 5-3. 참조/재사용 파일
| 파일 | 목적 |
|---|---|
| `engine_modules/inventory_modular/inbound_mixin.py` | 입고 처리 함수 확인 |
| `engine_modules/inventory_modular/outbound_mixin.py` | 출고/취소 함수 확인 |
| `engine_modules/inventory_modular/query_mixin.py` | 미리보기/보조 조회 참조 |
| `parsers/` 관련 파일 | PDF/Excel parser 재사용 |
| `data/db/sqm_inventory.db` | rollback/로그 검증 참고 |

---

# 6. 핵심 흐름 설계

## 6-1. 입고 흐름
```text
파일 선택
→ /files/upload
→ parser 실행
→ preview JSON 반환
→ InboundParseModal 미리보기 표시
→ 사용자 confirm
→ /inbound/create
→ engine_adapter.process_inbound(...)
→ commit 또는 rollback
→ 결과 표시
```

## 6-2. 출고 흐름
```text
대상 선택
→ 출고 수량/출고처 입력
→ /outbound/execute
→ engine_adapter.process_outbound(...)
→ commit 또는 rollback
→ 결과 표시
```

## 6-3. 출고 취소 흐름
```text
취소 대상 선택
→ /outbound/cancel
→ engine_adapter.cancel_outbound_tonbag(...)
→ commit 또는 rollback
→ 결과 표시
```

---

# 7. parser 연동 설계

## 7-1. 원칙
- 기존 parser가 있으면 반드시 재사용
- PDF와 Excel은 가능하면 같은 업로드 엔드포인트를 사용
- 업로드 엔드포인트 내부에서 파일 유형을 판별
- 반환은 preview 중심 JSON으로 표준화

## 7-2. `/files/upload` 최소 응답 구조
```json
{
  "success": true,
  "message": "Preview generated",
  "data": {
    "file_type": "pdf",
    "parser_type": "inbound",
    "preview": {},
    "summary": {},
    "warnings": []
  }
}
```

## 7-3. preview 최소 포함 항목
- [ ] 생성 예정 LOT 목록
- [ ] 품목/수량 요약
- [ ] 경고/누락 항목
- [ ] parser가 추정한 핵심 식별값
- [ ] 실제 create에 필요한 최소 payload

## 7-4. 파일 유형 판별 기준
- [ ] PDF
- [ ] Excel(xlsx/xls)
- [ ] 지원 불가 형식
- [ ] 손상 파일
- [ ] 빈 파일

---

# 8. engine adapter 설계

## 8-1. 절대 원칙
FastAPI/service 층에서 신규 업무 로직을 만들지 않는다.  
기존 `engine_modules`를 감싸는 wrapper만 둔다.

## 8-2. 최소 wrapper 후보
- [ ] `process_inbound(...)`
- [ ] `process_outbound(...)`
- [ ] `cancel_outbound_tonbag(...)`

## 8-3. adapter 책임
- [ ] engine 인스턴스 확보
- [ ] 인자 shape 맞추기
- [ ] 호출 전 최소 검증
- [ ] 예외를 service에 전달
- [ ] 결과를 공통 response에 맞게 변환

## 8-4. service 책임
- [ ] request schema 검증 이후 adapter 호출
- [ ] transaction begin/commit/rollback
- [ ] audit_log / outbound_event_log 기록
- [ ] preview/create/execute/cancel 흐름 제어

---

# 9. API 설계 기준

# 9-1. `POST /files/upload`
## 입력
- [ ] 업로드 파일
- [ ] parser_mode 또는 추정 모드(선택)
- [ ] 필요 시 source_type

## 출력
- [ ] preview
- [ ] summary
- [ ] warnings
- [ ] create용 최소 payload

## 실패 케이스
- [ ] 지원 안 되는 형식
- [ ] parser 실패
- [ ] 빈 파일
- [ ] 손상 파일

---

# 9-2. `POST /inbound/create`
## 입력
- [ ] preview에서 확정된 payload
- [ ] 사용자 확인 여부
- [ ] 필요 시 옵션 값

## 출력
- [ ] success/fail
- [ ] 생성된 LOT 요약
- [ ] 생성 건수
- [ ] warnings / message

## 실패 케이스
- [ ] payload 누락
- [ ] engine validation 실패
- [ ] DB insert 실패
- [ ] rollback 발생

---

# 9-3. `POST /outbound/execute`
## 입력
- [ ] 대상 lot/tonbag 식별값
- [ ] quantity
- [ ] destination / ship_to
- [ ] reference / sales order(있으면)

## 출력
- [ ] success/fail
- [ ] 처리된 대상 요약
- [ ] 남은 수량/상태 요약(가능한 범위)

## 실패 케이스
- [ ] 대상 없음
- [ ] 수량 오류
- [ ] engine validation 실패
- [ ] rollback 발생

---

# 9-4. `PUT /outbound/cancel`
## 입력
- [ ] 취소 대상 식별값
- [ ] reason(선택)
- [ ] 사용자/요청 메타(선택)

## 출력
- [ ] success/fail
- [ ] 복구된 대상 요약
- [ ] 상태 변경 결과

## 실패 케이스
- [ ] 취소 대상 없음
- [ ] 이미 취소됨
- [ ] engine validation 실패
- [ ] rollback 발생

---

# 10. Frontend 모달 설계 기준

# 10-1. `InboundParseModal.jsx`
- [ ] 파일 선택 UI
- [ ] 업로드 실행 버튼
- [ ] loading 표시
- [ ] preview 요약 표시
- [ ] LOT 생성 예정 목록 표시
- [ ] warnings 표시
- [ ] confirm create 버튼
- [ ] 성공/실패 결과 표시

## 상태
- [ ] selectedFile
- [ ] uploadLoading
- [ ] previewData
- [ ] createLoading
- [ ] error
- [ ] warnings

---

# 10-2. `OutboundExecuteModal.jsx`
- [ ] 대상 선택/표시
- [ ] quantity 입력
- [ ] destination 입력
- [ ] execute 버튼
- [ ] cancel 대상이 있으면 cancel 버튼 또는 별도 액션
- [ ] 결과 표시
- [ ] 에러 표시

## 상태
- [ ] selection
- [ ] quantity
- [ ] destination
- [ ] executeLoading
- [ ] cancelLoading
- [ ] result
- [ ] error

---

# 11. rollback 설계 기준

## 11-1. rollback이 반드시 필요한 경우
- [ ] parser 결과는 정상인데 create 단계 DB 반영 실패
- [ ] outbound execute 중 중간 DB 갱신 후 후속 단계 실패
- [ ] cancel 처리 중 일부 상태만 복구되고 예외 발생
- [ ] log 기록 단계에서 예외 발생

## 11-2. 검증해야 할 것
- [ ] 실패 후 DB가 원상복구되는지
- [ ] 중간 side effect가 남지 않는지
- [ ] audit/event log가 실패 사실을 남기는지
- [ ] 사용자 응답이 success로 잘못 표기되지 않는지

---

# 12. 테스트 지시서

# 12-1. Pre-Test
- [ ] parser 단독 실행 가능 여부
- [ ] 정상 PDF 샘플 확보
- [ ] 정상 Excel 샘플 확보
- [ ] 손상/잘못된 파일 샘플 확보
- [ ] 입고/출고 대상 테스트 데이터 확보
- [ ] 로그 테이블 스키마 확인 완료
- [ ] frontend/backend import 오류 없음

# 12-2. 입고 테스트
- [ ] PDF 업로드 → preview 생성
- [ ] Excel 업로드 → preview 생성
- [ ] preview 내용 화면 표시
- [ ] confirm → inbound/create 성공
- [ ] 생성 결과 요약 표시
- [ ] 실패 케이스 rollback 확인

# 12-3. 출고 테스트
- [ ] execute 요청 성공
- [ ] 상태 변화 확인
- [ ] 결과 메시지 확인
- [ ] 잘못된 수량/대상 오류 처리 확인
- [ ] rollback 확인

# 12-4. 출고 취소 테스트
- [ ] cancel 요청 성공
- [ ] 상태 복구 확인
- [ ] 이벤트 로그 기록 확인
- [ ] 실패 케이스 rollback 확인

# 12-5. 예외 테스트
- [ ] 잘못된 파일 형식
- [ ] parser 실패
- [ ] 빈 preview
- [ ] 없는 대상 출고
- [ ] 이미 취소된 출고 재취소
- [ ] API 500 처리

---

# 13. 완료 기준

## 완료로 인정
- [ ] upload → preview → create 실동작
- [ ] outbound execute 실동작
- [ ] outbound cancel 실동작
- [ ] transaction/rollback 검증 완료
- [ ] audit/event log 기록 확인
- [ ] 사용자 피드백 메시지 정상

## 완료로 인정하지 않음
- [ ] parser는 되지만 create가 mock임
- [ ] execute는 되지만 engine 실제 호출이 아님
- [ ] cancel은 버튼만 있고 실제 상태 복구가 없음
- [ ] rollback 검증이 없음
- [ ] 실패 시 DB side effect가 남음

---

# 14. 실패 유형별 조치

## 유형 A. parser 결과와 create payload 형식 불일치
- [ ] preview JSON 표준화
- [ ] create payload builder 추가
- [ ] parser adapter 보강

## 유형 B. engine 함수 인자 mismatch
- [ ] adapter에서 인자 재매핑
- [ ] 직접 engine 로직 수정 금지
- [ ] wrapper 함수로 해결

## 유형 C. rollback 실패
- [ ] transaction 범위 재설정
- [ ] logging을 트랜잭션 밖/안 어디에 둘지 재판정
- [ ] side effect 지점 재점검

## 유형 D. 모달 UX 불안정
- [ ] loading/error/result 상태 분리
- [ ] confirm 중복 클릭 방지
- [ ] 성공 후 화면 refresh 정책 정리

---

# 15. 산출물 목록

- [ ] `InboundParseModal.jsx` 실구현본
- [ ] `OutboundExecuteModal.jsx` 실구현본
- [ ] `actionApi.js` write 함수 구현본
- [ ] `actions.py` 실구현본
- [ ] `schemas/actions.py` 실구현본
- [ ] `action_service.py` 실구현본
- [ ] `engine_adapter.py` 실구현본
- [ ] parser 연결 메모
- [ ] rollback 테스트 결과 메모

---

# 16. P0-3 → P0-4 진입 게이트

아래를 모두 만족하면 P0-4로 넘어갈 수 있다.

- [ ] files/upload 실연결 완료
- [ ] inbound/create 실연결 완료
- [ ] outbound/execute 실연결 완료
- [ ] outbound/cancel 실연결 완료
- [ ] rollback 검증 완료
- [ ] 로그 기록 검증 완료

---

# 17. 루비 최종 권장안

이번 단계의 핵심은 아래 한 줄이다.

```text
P0-3은 API를 만드는 단계가 아니라,
실제 업무 쓰기 루프를 React/FastAPI에서 안전하게 재생시키는 단계다.
```

따라서 권장 구현 순서는 아래다.

```text
1. files/upload + preview
2. inbound/create
3. outbound/execute
4. outbound/cancel
5. rollback/logging 검증
```

---

# 18. 다음 단계 권장

이번 문서 다음으로 가장 효율적인 작업은 아래 2개 중 하나다.

1. `P0-3 입고출고 write loop 테스트체크리스트`
2. `Claude Code용 P0-3 실행 프롬프트`

루비 권장 순서는 아래다.

```text
1) P0-3 테스트체크리스트
2) Claude Code용 P0-3 실행 프롬프트
```
