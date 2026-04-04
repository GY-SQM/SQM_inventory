# GPT_SQM_P0-3_입고출고_WriteLoop_테스트체크리스트.md
생성일: 2026-04-04 15:42 (Asia/Seoul)  
기준 원본: `Claude_SQM_v867.zip`  
참조 문서:
- `MASTER_FINAL_v867_통합완성본.md`
- `GPT_SQM_P0-3_입고출고_WriteLoop_초상세_작업지시서.md`
- `GPT_SQM_P0_통합체크리스트_v2.md`
- `GPT_SQM_P0-1_DB스키마점검표.md`

---

## [질문]
계속 진행해서 **P0-3 입고출고 write loop 테스트체크리스트**를 작성해 달라는 요청

## [질문의도]
P0-3 구현 후,
`files/upload → preview → inbound/create → outbound/execute → outbound/cancel → rollback/logging`
전체 흐름이 실제로 동작하는지 검증할 수 있도록
실행형 테스트 체크리스트를 만든다.

---

# [응답]

# 1. 문서 목적

이 문서는 P0-3에서 구현한 write loop가
단순 API 추가 수준이 아니라 **실제 업무 처리 루프**로 동작하는지 검증하기 위한 테스트 기준서다.

이번 테스트의 목적은 아래와 같다.

```text
1. 파일 업로드와 parser preview가 실제로 동작하는지 검증
2. inbound/create가 실제 engine 로직과 연결되는지 검증
3. outbound/execute / cancel이 실제 engine 로직과 연결되는지 검증
4. rollback / audit_log / outbound_event_log가 실제로 작동하는지 검증
5. P0-4 진입 전 write 동작 안정성을 확보
```

---

# 2. 테스트 범위

## 포함
- `POST /files/upload`
- parser preview
- `POST /inbound/create`
- `POST /outbound/execute`
- `PUT /outbound/cancel`
- InboundParseModal 실동작
- OutboundExecuteModal 실동작
- transaction / rollback
- audit_log / outbound_event_log 기록 확인

## 제외
- `PUT /location/update`
- run_react.bat 최종 통합 실행
- Tkinter 병행 실행 최종 충돌 테스트
- 전체 운영 자동화

즉, 이번 문서는 **P0-3 write loop 전용**이다.

---

# 3. 사전 준비 체크

## 테스트 데이터 준비
- [ ] 정상 PDF 샘플 확보
- [ ] 정상 Excel 샘플 확보
- [ ] 손상 PDF 또는 잘못된 파일 샘플 확보
- [ ] 지원 불가 형식 샘플 확보
- [ ] 입고 가능한 테스트 데이터 확보
- [ ] 출고 가능한 테스트 대상 LOT/톤백 확보
- [ ] 취소 가능한 출고 대상 확보

## 환경 준비
- [ ] React 프론트 실행 가능
- [ ] FastAPI 서버 실행 가능
- [ ] DB 접근 가능
- [ ] parser 호출 가능
- [ ] 로그 테이블 조회 가능
- [ ] 테스트는 가능하면 복제 DB 또는 안전한 샘플 환경에서 수행

## 기준 문서 확인
- [ ] P0-3 초상세 작업지시서 확인
- [ ] DB스키마점검표 확인
- [ ] rollback 검증 항목 확인

---

# 4. 업로드 / preview 테스트

# 4-1. PDF 업로드 테스트
- [ ] PDF 파일 선택 가능
- [ ] `/files/upload` 호출 발생
- [ ] parser가 실제 실행됨
- [ ] preview JSON 반환
- [ ] InboundParseModal에 preview 표시
- [ ] summary 표시
- [ ] warnings 표시(있으면)
- [ ] create용 payload가 준비됨

## 판정표
| 항목 | 결과(PASS/FAIL) | 비고 |
|---|---|---|
| PDF 선택 |  |  |
| upload 호출 |  |  |
| parser 실행 |  |  |
| preview 반환 |  |  |
| preview 표시 |  |  |
| summary 표시 |  |  |
| warnings 표시 |  |  |

---

# 4-2. Excel 업로드 테스트
- [ ] Excel 파일 선택 가능
- [ ] `/files/upload` 호출 발생
- [ ] parser가 실제 실행됨
- [ ] preview JSON 반환
- [ ] InboundParseModal에 preview 표시
- [ ] summary 표시
- [ ] warnings 표시(있으면)
- [ ] create용 payload가 준비됨

## 판정표
| 항목 | 결과(PASS/FAIL) | 비고 |
|---|---|---|
| Excel 선택 |  |  |
| upload 호출 |  |  |
| parser 실행 |  |  |
| preview 반환 |  |  |
| preview 표시 |  |  |
| summary 표시 |  |  |
| warnings 표시 |  |  |

---

# 4-3. 업로드 예외 테스트
- [ ] 지원 불가 파일 형식 처리
- [ ] 손상 파일 처리
- [ ] 빈 파일 처리
- [ ] parser 실패 처리
- [ ] 사용자에게 오류 메시지 표시
- [ ] 콘솔에만 오류가 남고 UI는 멈추지 않는지 확인

## 판정표
| 케이스 | 결과(PASS/FAIL) | 비고 |
|---|---|---|
| 지원 불가 형식 |  |  |
| 손상 파일 |  |  |
| 빈 파일 |  |  |
| parser 실패 |  |  |
| 오류 메시지 표시 |  |  |

---

# 5. inbound/create 테스트

# 5-1. 정상 생성 테스트
- [ ] preview 이후 confirm 버튼 가능
- [ ] `POST /inbound/create` 호출 발생
- [ ] `process_inbound()` 또는 동등 로직 실제 호출
- [ ] DB 반영 성공
- [ ] 생성 결과 요약 표시
- [ ] LOT 생성 결과 확인 가능
- [ ] success 응답이 실제 DB 결과와 일치

## 판정표
| 항목 | 결과(PASS/FAIL) | 비고 |
|---|---|---|
| confirm 버튼 |  |  |
| API 호출 |  |  |
| engine 호출 |  |  |
| DB 반영 |  |  |
| 결과 요약 표시 |  |  |
| LOT 생성 확인 |  |  |

---

# 5-2. 생성 실패 / rollback 테스트
- [ ] 잘못된 payload로 create 시도
- [ ] engine validation 실패 유도
- [ ] DB insert 중 실패 시나리오 확인
- [ ] rollback 발생 확인
- [ ] 중간 데이터가 남지 않는지 확인
- [ ] audit_log에 실패 기록 확인
- [ ] 사용자 응답이 실패로 표기되는지 확인

## 판정표
| 항목 | 결과(PASS/FAIL) | 비고 |
|---|---|---|
| validation 실패 처리 |  |  |
| rollback 발생 |  |  |
| 중간 데이터 미잔존 |  |  |
| audit_log 기록 |  |  |
| 사용자 실패 응답 |  |  |

---

# 6. outbound/execute 테스트

# 6-1. 정상 출고 테스트
- [ ] 출고 대상 선택 가능
- [ ] 수량 입력 가능
- [ ] destination 입력 가능
- [ ] `POST /outbound/execute` 호출 발생
- [ ] `process_outbound()` 또는 동등 로직 실제 호출
- [ ] 상태 변화 확인
- [ ] 결과 메시지 표시
- [ ] event log 기록 확인

## 판정표
| 항목 | 결과(PASS/FAIL) | 비고 |
|---|---|---|
| 대상 선택 |  |  |
| 수량 입력 |  |  |
| destination 입력 |  |  |
| API 호출 |  |  |
| engine 호출 |  |  |
| 상태 변화 |  |  |
| 결과 메시지 |  |  |
| event log 기록 |  |  |

---

# 6-2. 출고 실패 / rollback 테스트
- [ ] 존재하지 않는 대상 출고
- [ ] 잘못된 수량 출고
- [ ] engine validation 실패
- [ ] rollback 발생
- [ ] 중간 상태 변경이 남지 않는지 확인
- [ ] audit/event log에 실패 기록 확인
- [ ] 사용자 응답이 실패로 표시되는지 확인

## 판정표
| 항목 | 결과(PASS/FAIL) | 비고 |
|---|---|---|
| 없는 대상 처리 |  |  |
| 잘못된 수량 처리 |  |  |
| validation 실패 |  |  |
| rollback 발생 |  |  |
| 상태 복구 확인 |  |  |
| 실패 로그 기록 |  |  |

---

# 7. outbound/cancel 테스트

# 7-1. 정상 취소 테스트
- [ ] 취소 대상 식별 가능
- [ ] `PUT /outbound/cancel` 호출 발생
- [ ] `cancel_outbound_tonbag()` 또는 동등 로직 실제 호출
- [ ] 상태 복구 확인
- [ ] 결과 메시지 표시
- [ ] outbound_event_log에 취소 이력 기록 확인

## 판정표
| 항목 | 결과(PASS/FAIL) | 비고 |
|---|---|---|
| 취소 대상 식별 |  |  |
| API 호출 |  |  |
| engine 호출 |  |  |
| 상태 복구 |  |  |
| 결과 메시지 |  |  |
| 취소 이력 기록 |  |  |

---

# 7-2. 취소 실패 / rollback 테스트
- [ ] 없는 취소 대상
- [ ] 이미 취소된 대상 재취소
- [ ] engine validation 실패
- [ ] rollback 발생
- [ ] 잘못된 상태 복구가 남지 않는지 확인
- [ ] 실패 로그 기록 확인

## 판정표
| 항목 | 결과(PASS/FAIL) | 비고 |
|---|---|---|
| 없는 대상 처리 |  |  |
| 재취소 처리 |  |  |
| validation 실패 |  |  |
| rollback 발생 |  |  |
| 상태 무결성 유지 |  |  |
| 실패 로그 기록 |  |  |

---

# 8. Frontend 모달 테스트

# 8-1. InboundParseModal
- [ ] 파일 선택 UI 동작
- [ ] uploadLoading 표시
- [ ] preview 표시
- [ ] warnings 표시
- [ ] confirm create 버튼 동작
- [ ] createLoading 표시
- [ ] 성공/실패 결과 표시
- [ ] 중복 클릭 방지

# 8-2. OutboundExecuteModal
- [ ] selection 표시/선택
- [ ] quantity 입력 검증
- [ ] destination 입력 검증
- [ ] executeLoading 표시
- [ ] cancelLoading 표시
- [ ] 성공/실패 결과 표시
- [ ] 중복 클릭 방지

---

# 9. 로그 테스트

## audit_log
- [ ] inbound/create 성공 기록
- [ ] inbound/create 실패 기록
- [ ] outbound/execute 성공 기록
- [ ] outbound/execute 실패 기록
- [ ] outbound/cancel 성공 기록
- [ ] outbound/cancel 실패 기록

## outbound_event_log
- [ ] execute 이벤트 기록
- [ ] cancel 이벤트 기록
- [ ] 실패 이벤트 또는 실패 근접 기록 확인
- [ ] created_at / event_type / 대상 식별값 확인

## 판정표
| 로그 항목 | 결과(PASS/FAIL) | 비고 |
|---|---|---|
| audit_log success |  |  |
| audit_log fail |  |  |
| event_log execute |  |  |
| event_log cancel |  |  |
| timestamp 기록 |  |  |
| 대상 식별값 기록 |  |  |

---

# 10. transaction / rollback 테스트

## 핵심 질문
- [ ] write 실패 후 DB가 원상복구되는가
- [ ] 중간 side effect가 남지 않는가
- [ ] 실패 응답이 success로 잘못 내려가지 않는가
- [ ] 로그는 실패 사실을 남기는가

## 테스트 시나리오
### 시나리오 A
- [ ] preview는 성공하지만 create에서 실패
- [ ] rollback 후 생성 데이터 미존재 확인

### 시나리오 B
- [ ] execute 중간 실패 유도
- [ ] 상태 partially changed 여부 확인

### 시나리오 C
- [ ] cancel 중간 실패 유도
- [ ] 복구 도중 불완전 상태가 남지 않는지 확인

## 판정표
| 시나리오 | rollback 성공 | side effect 없음 | 로그 남음 | 비고 |
|---|---|---|---|---|
| A |  |  |  |  |
| B |  |  |  |  |
| C |  |  |  |  |

---

# 11. 콘솔 / 서버 로그 테스트

- [ ] 프론트 콘솔 치명 오류 없음
- [ ] 백엔드 traceback이 사용자 성공 응답과 같이 나타나지 않음
- [ ] parser 에러가 적절한 메시지로 변환됨
- [ ] validation 에러가 적절한 4xx로 내려감
- [ ] 서버 로그에 핵심 실패 원인이 식별 가능

---

# 12. 완료 판정 기준

## P0-3 테스트 통과로 인정
- [ ] PDF/Excel upload preview 성공
- [ ] inbound/create 성공 및 실패 rollback 검증
- [ ] outbound/execute 성공 및 실패 rollback 검증
- [ ] outbound/cancel 성공 및 실패 rollback 검증
- [ ] audit_log / outbound_event_log 기록 확인
- [ ] 모달 UX가 실사용 가능한 수준

## 통과로 인정하지 않음
- [ ] preview만 되고 create가 mock
- [ ] execute/cancel가 실제 engine 호출이 아님
- [ ] rollback 검증이 없음
- [ ] 로그가 남지 않음
- [ ] 실패 후 DB 상태가 어정쩡하게 남음

---

# 13. 테스트 결과 기록표

## 종합 결과
| 항목 | 결과(PASS/FAIL) | 비고 |
|---|---|---|
| PDF upload preview |  |  |
| Excel upload preview |  |  |
| inbound/create success |  |  |
| inbound/create rollback |  |  |
| outbound/execute success |  |  |
| outbound/execute rollback |  |  |
| outbound/cancel success |  |  |
| outbound/cancel rollback |  |  |
| audit_log 기록 |  |  |
| event_log 기록 |  |  |
| 모달 UX |  |  |

## 최종 판정
- [ ] PASS → P0-4 진입 가능
- [ ] CONDITIONAL PASS → 보완 메모 후 P0-4 가능
- [ ] FAIL → P0-3 수정 후 재테스트

---

# 14. 실패 시 조치 가이드

## 유형 A. parser는 되는데 create payload가 안 맞음
- [ ] preview JSON 표준화
- [ ] create payload builder 보강
- [ ] schema 재정렬

## 유형 B. engine 호출 인자 mismatch
- [ ] adapter 인자 매핑 수정
- [ ] service에서 직접 로직 만들지 말고 adapter로 흡수

## 유형 C. rollback 불안정
- [ ] transaction 범위 재조정
- [ ] DB side effect 지점 추적
- [ ] logging 위치 재검토

## 유형 D. 로그 기록 불완전
- [ ] audit_log 필수 컬럼 재확인
- [ ] outbound_event_log event_type/target 식별값 재확인

## 유형 E. 모달 UX 문제
- [ ] loading / result / error 상태 분리 강화
- [ ] 중복 클릭 방지 강화
- [ ] 성공 후 화면 재조회 정책 추가

---

# 15. P0-4 진입 게이트

아래를 모두 만족하면 P0-4로 넘어갈 수 있다.

- [ ] write loop 실동작 검증 완료
- [ ] rollback 실검증 완료
- [ ] 로그 기록 검증 완료
- [ ] React/FastAPI의 핵심 write 루프 안정성 확보
- [ ] 남은 범위가 location/update + 실행 통합 단계로 정리됨

---

# 16. 루비 최종 판단

이번 테스트체크리스트의 핵심은 아래다.

```text
P0-3는 "API가 생겼다"가 아니라
"실제 업무 쓰기 루프가 안전하게 돈다"를 증명해야 통과다.
```

즉, 이번 단계의 통과 기준은 **write 버튼 존재**가 아니라
**실제 parser/engine/rollback/logging까지 검증된 업무 흐름**이다.

---

# 17. 다음 단계 권장

이번 문서 다음으로 가장 효율적인 작업은 아래 2개 중 하나다.

1. `Claude Code용 P0-3 실행 프롬프트`
2. `P0-4 위치업데이트+통합실행 초상세 작업지시서`

루비 권장 순서는 아래다.

```text
1) Claude Code용 P0-3 실행 프롬프트
2) P0-4 초상세 작업지시서
```
