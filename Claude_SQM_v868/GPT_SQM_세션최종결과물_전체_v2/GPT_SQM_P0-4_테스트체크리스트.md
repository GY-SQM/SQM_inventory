# GPT_SQM_P0-4_테스트체크리스트.md
생성일: 2026-04-04 15:58 (Asia/Seoul)  
기준 원본: `Claude_SQM_v867.zip`  
참조 문서:
- `MASTER_FINAL_v867_통합완성본.md`
- `GPT_SQM_P0-4_위치업데이트_통합실행_초상세_작업지시서.md`
- `GPT_SQM_P0-3_입고출고_WriteLoop_테스트체크리스트.md`
- `GPT_SQM_P0-2_LOT상세모달_테스트체크리스트.md`

---

## [질문]
다음 단계로 **P0-4 테스트체크리스트**를 작성

## [질문의도]
P0-4에서 구현한
`location/update`, 실행 파일 정리, `.env` 구조, 통합 실행, 회귀 테스트를
실제로 검증할 수 있도록 실행형 테스트 기준을 만든다.

---

# [응답]

# 1. 테스트 목적

이번 문서는 P0 마지막 단계의 검증용이다.

```text
1. location/update 실동작 검증
2. 실행 파일(run.py/run_bootstrap.py/run_react_api.py/run_react.bat) 검증
3. .env 로드 구조 검증
4. P0-2/P0-3 회귀 검증
5. P0 전체 완료 게이트 통과 여부 판정
```

---

# 2. 테스트 범위

## 포함
- `PUT /location/update`
- 위치 변경 UI/액션
- rollback / audit_log
- API + Frontend 기본 통합 실행
- run_react_api.py / run_react.bat 실행 검증
- .env 키/로드 위치 점검
- P0-2 read 회귀
- P0-3 write 회귀

## 제외
- Telegram bridge 자동화
- Security 고도화
- 대규모 성능 튜닝
- P1 이상 UX 고도화

---

# 3. 사전 준비 체크

- [ ] 위치 변경 가능한 테스트 대상 확보
- [ ] 정상 위치 값 준비
- [ ] 잘못된 위치 값 준비
- [ ] API 서버 실행 가능
- [ ] Frontend 실행 가능
- [ ] DB 접근 가능
- [ ] audit_log 조회 가능
- [ ] P0-2 / P0-3 테스트용 샘플 데이터 준비
- [ ] .env 파일 확인 가능

---

# 4. location/update 테스트

## 4-1. 성공 테스트
- [ ] 대상 선택 가능
- [ ] 새 위치 입력 가능
- [ ] `PUT /location/update` 호출 발생
- [ ] 실제 engine 위치 변경 함수 호출
- [ ] DB 반영 성공
- [ ] 결과 메시지 표시
- [ ] 재조회 시 새 위치 반영
- [ ] audit_log success 기록 확인

## 4-2. 실패/rollback 테스트
- [ ] 없는 대상 처리
- [ ] 잘못된 위치 처리
- [ ] validation 실패 처리
- [ ] rollback 발생
- [ ] 중간 상태 미잔존 확인
- [ ] audit_log fail 기록 확인
- [ ] 사용자 응답 실패 표시

## 판정표
| 항목 | 결과(PASS/FAIL) | 비고 |
|---|---|---|
| 성공 호출 |  |  |
| engine 호출 |  |  |
| DB 반영 |  |  |
| 결과 메시지 |  |  |
| 재조회 반영 |  |  |
| 실패 rollback |  |  |
| audit_log success |  |  |
| audit_log fail |  |  |

---

# 5. 실행 파일 테스트

## 5-1. run_react_api.py
- [ ] 단독 기동 가능
- [ ] host/port 정상
- [ ] .env 또는 설정값 정상 반영
- [ ] 실행 실패 시 로그 식별 가능

## 5-2. run_react.bat
- [ ] API 기동 포함
- [ ] Frontend 기동 포함
- [ ] 순서 안정적
- [ ] 창이 즉시 닫히지 않음
- [ ] 오류 시 로그/콘솔 확인 가능

## 5-3. run.py / run_bootstrap.py
- [ ] Tkinter 진입점 정상
- [ ] bootstrap 흐름 정상
- [ ] API/Frontend와 역할 충돌 없음
- [ ] 직접 수정이 있었다면 회귀 없음

## 판정표
| 파일 | 결과(PASS/FAIL) | 비고 |
|---|---|---|
| run_react_api.py |  |  |
| run_react.bat |  |  |
| run.py |  |  |
| run_bootstrap.py |  |  |

---

# 6. .env / 설정 테스트

- [ ] `.env` 존재 확인
- [ ] 공통 키 인식 확인
- [ ] API 키 인식 확인
- [ ] Frontend 관련 키 인식 확인
- [ ] 잘못된 키/누락 키에서 오류 메시지 확인 가능
- [ ] 기본값 전략 문서화 가능

## 판정표
| 항목 | 결과(PASS/FAIL) | 비고 |
|---|---|---|
| .env 존재 |  |  |
| API 로드 |  |  |
| Frontend 로드 |  |  |
| 공통 키 |  |  |
| 누락 키 처리 |  |  |

---

# 7. 충돌 테스트

## 7-1. 포트 충돌
- [ ] API 포트 충돌 없음
- [ ] Frontend 포트 충돌 없음

## 7-2. DB lock 충돌
- [ ] API write 중 치명 lock 없음
- [ ] Tkinter 병행 시 즉시 장애 없음
- [ ] WAL/timeout 정책상 실무 사용 가능 수준인지 메모

## 7-3. 경로 충돌
- [ ] upload/temp/log 경로 충돌 없음
- [ ] batch 실행 경로 안정적

## 7-4. env 해석 충돌
- [ ] API/Tkinter env 해석 차이 없음
- [ ] dev/prod 혼선 없음

## 판정표
| 충돌 유형 | 결과(PASS/FAIL) | 비고 |
|---|---|---|
| 포트 |  |  |
| DB lock |  |  |
| 경로 |  |  |
| env 해석 |  |  |

---

# 8. P0-2 회귀 테스트

- [ ] LOT 클릭 → 모달 오픈
- [ ] LOT 조회 API 호출
- [ ] 기본정보 표시
- [ ] 톤백 목록 표시
- [ ] 이력 표시
- [ ] 배정 상태 표시
- [ ] loading/error/재조회 동작

## 판정표
| 항목 | 결과(PASS/FAIL) | 비고 |
|---|---|---|
| 모달 오픈 |  |  |
| 조회 API |  |  |
| 기본정보 |  |  |
| 톤백목록 |  |  |
| 이력 |  |  |
| 배정상태 |  |  |
| 상태 처리 |  |  |

---

# 9. P0-3 회귀 테스트

- [ ] PDF upload preview
- [ ] Excel upload preview
- [ ] inbound/create success
- [ ] inbound/create rollback
- [ ] outbound/execute success
- [ ] outbound/execute rollback
- [ ] outbound/cancel success
- [ ] outbound/cancel rollback
- [ ] audit_log / outbound_event_log 기록

## 판정표
| 항목 | 결과(PASS/FAIL) | 비고 |
|---|---|---|
| PDF preview |  |  |
| Excel preview |  |  |
| inbound success |  |  |
| inbound rollback |  |  |
| execute success |  |  |
| execute rollback |  |  |
| cancel success |  |  |
| cancel rollback |  |  |
| 로그 기록 |  |  |

---

# 10. 최종 완료 판정 기준

## PASS
- [ ] location/update 성공/실패 검증 완료
- [ ] 실행 파일 검증 완료
- [ ] .env 구조 검증 완료
- [ ] P0-2 회귀 통과
- [ ] P0-3 회귀 통과
- [ ] P0 전체 완료보고서 작성 가능

## CONDITIONAL PASS
- [ ] 핵심 기능은 통과
- [ ] 경미한 실행 스크립트 보완만 남음
- [ ] P1으로 넘길 수 있는 사소한 항목만 남음

## FAIL
- [ ] location/update 불안정
- [ ] rollback 불안정
- [ ] 실행 스크립트 재현 불가
- [ ] P0-2/P0-3 회귀 깨짐
- [ ] 포트/DB/env 충돌 미정리

---

# 11. 최종 결과 기록표

| 항목 | 결과(PASS/FAIL) | 비고 |
|---|---|---|
| location/update |  |  |
| rollback |  |  |
| audit_log |  |  |
| run_react_api.py |  |  |
| run_react.bat |  |  |
| .env 구조 |  |  |
| P0-2 회귀 |  |  |
| P0-3 회귀 |  |  |

최종 판정:
- [ ] PASS
- [ ] CONDITIONAL PASS
- [ ] FAIL

---

# 12. 루비 최종 판단

```text
P0-4 통과 기준은 새 기능 추가가 아니라,
지금까지 만든 read/write/location/update/실행체계를 하나로 묶어
재현 가능하고 안정적인 상태인지 증명하는 것이다.
```
