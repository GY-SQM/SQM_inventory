# GPT_SQM_P3_Patch3_통합MASTER.md
생성일: 2026-04-04 17:24 (Asia/Seoul)  
기준 원본: `Claude_SQM_v867.zip`  
기준 문서:
- `MASTER_FINAL_v867_통합완성본.md`
- `GPT_SQM_P2_to_Patch5_MASTER.md`
- `GPT_SQM_P2_Patch2_통합MASTER.md`
- `GPT_SQM_P0_최종_완료보고서_초안.md`

---

## [질문]
루비 권장 흐름대로 계속 진행해서 **P3 + Patch 3 통합 MASTER**를 작성

## [질문의도]
P3(운영 자동화/반복 실행 체계)와 Patch 3(DB 스키마 / migration / 로그 구조 정리)는
실제 운영 단계에서 강하게 연결되므로, 다음 세션에서 바로 실행 가능한 수준으로
목표 / 범위 / 순서 / 테스트 / 실패 대응을 하나의 통합 기준 문서로 묶는다.

---

# [응답]

# 1. 이 문서의 역할

이 문서는 **P3 + Patch 3 통합 기준서**다.

```text
1. P3 운영 자동화 범위를 정의
2. Patch 3 DB/로그 구조 정리 범위를 정의
3. 자동화와 DB/로그 구조를 하나의 운영 흐름으로 연결
4. Claude Code / Cursor / 수동 작업 공통 기준 제공
5. 다음 세션에서 바로 실행 가능한 상위 문서 역할 수행
```

---

# 2. 전제 조건

## 2-1. 선행 조건
```text
P0 전체 PASS 또는 최소 CONDITIONAL PASS
P2 + Patch 2 방향이 확정 또는 최소 설계 완료
```

## 2-2. 핵심 철학
```text
P3는 '반복 가능한 운영 자동화'
Patch 3는 '반복 가능한 DB/로그 구조 안정화'
자동화와 로그 구조는 분리되면 추적성과 복구력이 무너진다
```

---

# 3. 한 줄 목표

```text
단계 실행, 테스트, 판정, 로그, 결과 저장이 반복 가능한 구조를 만들고,
그 기반이 되는 audit_log / outbound_event_log / migration 구조를 안정화한다.
```

---

# 4. P3 + Patch 3 통합 범위

## 4-1. P3 범위
- run_all_p0.ps1 확장
- run_stage.ps1 고도화
- 테스트 결과 파일 표준화
- PASS/FAIL 판독 구조
- 로그 요약 자동화
- 단계별 중단/재시도 전략
- 운영자 개입 지점 최소화

## 4-2. Patch 3 범위
- audit_log 구조 정리
- outbound_event_log 구조 정리
- migration 초안 정리
- created_at/default/nullability 정리
- event/action/status naming 정리
- DB insert 실패 원인 제거
- 로그 구조와 실행 루프의 결합 안정화

---

# 5. 왜 통합해야 하는가

```text
자동화가 좋아도 로그 구조가 불안정하면 실패 원인 추적이 안 된다
DB 로그 구조가 좋아도 자동화가 없으면 반복 운영이 무너진다
따라서 P3와 Patch 3은 하나의 운영 체계로 다뤄야 한다
```

---

# 6. 핵심 운영 흐름

```text
단계 실행
→ 로그 기록
→ 테스트 결과 저장
→ PASS/FAIL 판정
→ FAIL 시 중단 + 원인 추적
→ 수정 후 재실행
```

이 흐름이 안정하려면 아래가 필요하다.

- audit_log 일관성
- outbound_event_log 일관성
- results 파일 구조
- logs 파일 구조
- 실행 단계별 상태 기록

---

# 7. 수정 대상 파일

## 7-1. 운영 자동화 대표 파일
```text
09_SCRIPTS/run_all_p0.ps1
09_SCRIPTS/run_stage.ps1
09_SCRIPTS/check_env.ps1
09_SCRIPTS/write_run_log.ps1
07_LOGS/*
08_RESULTS/*
06_REPORTS/*
```

## 7-2. DB / 로그 대표 파일
```text
react_api/services/action_service.py
react_api/schemas/actions.py
react_api/routes/actions.py
migration scripts (필요 시 신규)
data/db/sqm_inventory.db (직접 수정 금지, 구조 점검/마이그레이션 기준)
```

## 7-3. 참조 파일
```text
GPT_SQM_P0-1_DB스키마점검표.md
GPT_SQM_자동실행_PS1_실전예시.md
GPT_SQM_최종실행팩_구성체크리스트.md
```

---

# 8. 구현 순서

## Step 1. Recon
- 현재 로그 파일 구조 조사
- 현재 results 구조 조사
- audit_log / outbound_event_log 실제 컬럼 구조 재확인
- run_all_p0.ps1 / run_stage.ps1 현재 한계 확인

## Step 2. Patch 3 (DB/로그 구조 정리)
- audit_log 최소 필수 컬럼 재정의
- outbound_event_log 최소 필수 컬럼 재정의
- naming / default / timestamp 정책 정리
- migration 필요 여부 판단
- migration 초안 작성

## Step 3. P3 (운영 자동화 고도화)
- 단계별 PASS/FAIL 파일 구조 정의
- run_stage.ps1 결과 파일 저장 기능 보강
- run_all_p0.ps1 단계 판독 구조 보강
- 로그 요약 파일 구조 정의
- 실패 즉시 중단 + 기록 구조 보강

## Step 4. 연결 검증
- 실행 실패 → audit/event/logs/results 일관성 검증
- PASS/FAIL 판독 → 다음 단계 게이트 일관성 검증

## Step 5. 테스트
- Patch 3 테스트
- P3 테스트
- P0 실행 체계 회귀 검증

---

# 9. DB/로그 구조 기준

## 9-1. audit_log 최소 필수
- id
- action_type
- status
- message
- payload_json
- error_message
- source_module
- created_at

## 9-2. outbound_event_log 최소 필수
- id
- outbound_id 또는 동등 식별값
- lot_no
- tonbag_no
- event_type
- status
- message
- payload_json
- created_at

## 9-3. 기본 원칙
- timestamp default 존재
- success/fail 둘 다 기록 가능
- partial failure도 기록 가능
- insert 시 필수 컬럼 부족으로 실패하지 않게 설계

---

# 10. 자동화 구조 기준

## 10-1. results 구조 예시
```text
08_RESULTS/
 ├─ stage_status.json
 ├─ p0_2_result.txt
 ├─ p0_3_result.txt
 ├─ p0_4_result.txt
 ├─ p2_result.txt
 └─ p3_result.txt
```

## 10-2. logs 구조 예시
```text
07_LOGS/
 ├─ run_status.log
 ├─ p0_2_run.log
 ├─ p0_3_run.log
 ├─ p0_4_run.log
 ├─ p3_run.log
 └─ final_summary.log
```

## 10-3. 자동화 원칙
- 단계별 결과 파일 분리
- 로그 파일 분리
- 실패 단계 즉시 중단
- 사람이 확인할 최소 포인트 유지

---

# 11. 테스트 게이트 공통 규칙

```text
Pre-Test
→ 구현
→ Post-Test
→ 실패 시 수정
→ Re-Test
→ PASS
→ 다음 단계
```

---

# 12. P3 완료 기준

- [ ] 단계별 실행 로그 구조 안정
- [ ] PASS/FAIL 저장 구조 안정
- [ ] 반자동/준자동 운영 가능
- [ ] 실패 단계 식별이 즉시 가능

---

# 13. Patch 3 완료 기준

- [ ] audit_log 구조 정리 완료
- [ ] outbound_event_log 구조 정리 완료
- [ ] migration 필요 여부 확정
- [ ] insert/logging 실패 위험 감소

---

# 14. 통합 완료 기준

- [ ] 실행 자동화와 DB/로그 구조가 함께 안정
- [ ] 단계 실패 시 추적 가능
- [ ] 다음 세션/다른 PC에서도 재현 가능
- [ ] P0 실행 체계 회귀 없음

---

# 15. 실패 유형별 공통 조치

## 유형 A. 자동화는 되지만 로그가 불완전
- Patch 3 우선
- audit/event 구조 먼저 안정화

## 유형 B. 로그는 좋지만 자동화가 끊김
- P3 우선
- run_all / run_stage 상태 판독 구조 보강

## 유형 C. migration 없이는 insert 실패
- Patch 3에서 migration 초안 우선 작성
- 직접 실DB 적용은 별도 승인/테스트 후

## 유형 D. 결과 파일과 로그 파일이 불일치
- 실행 단계 상태 기록 위치 통일
- results / logs / reports 책임 분리

---

# 16. 권장 산출물

- `GPT_SQM_Patch3_초상세_작업지시서.md`
- `GPT_SQM_Patch3_테스트체크리스트.md`
- `GPT_ClaudeCode_P3_Patch3_통합실행프롬프트.md`
- migration 초안 메모
- 로그 구조 표준 메모
- results 파일 규격 메모

---

# 17. 루비 최종 판단

```text
P3와 Patch 3는 눈에 보이는 기능보다
'반복 가능한 운영 체계'의 품질을 결정하는 단계다.
자동화와 로그 구조는 반드시 같이 잡아야 한다.
```

---

# 18. 다음 단계 권장

```text
1. Patch 3 초상세 작업지시서
2. Patch 3 테스트체크리스트
3. Claude Code용 P3+Patch3 통합 실행프롬프트
```
