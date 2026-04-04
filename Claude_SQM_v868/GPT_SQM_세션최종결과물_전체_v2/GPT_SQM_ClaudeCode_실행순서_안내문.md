# GPT_SQM_ClaudeCode_실행순서_안내문.md
생성일: 2026-04-04 16:08 (Asia/Seoul)

---

## [질문]
Claude Code 실행 순서 안내문 작성

## [질문의도]
지금까지 만든 P0 문서들을 실제로 Claude Code에 투입할 때  
혼선 없이 순서대로 실행할 수 있도록 **실전 실행 가이드**를 만든다.

---

# [응답]

# 1. 이 문서의 목적

이 문서는 아래를 해결하기 위한 것이다.

```text
1. Claude Code에 어떤 문서를 어떤 순서로 넣어야 하는지
2. 어디서 멈추고 테스트해야 하는지
3. 실패 시 어떻게 돌아가야 하는지
4. 자동 실행 vs 수동 개입 기준
```

---

# 2. 전체 실행 전략

Claude Code 실행은 반드시 **단계별로 끊어서 진행**해야 한다.

```text
P0-2 → P0-3 → P0-4
(각 단계마다 테스트 통과 후 다음 단계 진행)
```

절대 한 번에 전부 실행하지 않는다.

---

# 3. 실행 준비

## 3-1 필수 준비 파일

```text
MASTER_FINAL_v867_통합완성본.md
GPT_SQM_P0_통합체크리스트_v2.md
GPT_SQM_P0_통합인덱스_마스터팩.md
```

## 3-2 환경

- Claude Code CLI 설치 완료
- 프로젝트 폴더 준비
- Python 실행 가능
- DB 접근 가능

---

# 4. 실행 단계

# STEP 1: P0-2 실행

## 입력
```text
SYSTEM PROMPT:
MASTER_FINAL_v867
+ GPT_SQM_P0_통합체크리스트_v2

USER PROMPT:
GPT_ClaudeCode_P0-2_실행프롬프트.md
```

## 목표
- LOT 상세 모달 구현
- 조회 API 연결

## 실행 후 반드시 할 것
- P0-2 테스트체크리스트 실행
- Tkinter와 비교 검증

## 통과 기준
- PASS 또는 CONDITIONAL PASS

---

# STEP 2: P0-3 실행

## 입력
```text
SYSTEM PROMPT:
MASTER + 통합체크리스트 유지

USER PROMPT:
GPT_ClaudeCode_P0-3_실행프롬프트.md
```

## 목표
```text
upload → preview → inbound/create → outbound/execute → cancel
+ rollback + logging
```

## 실행 후 반드시 할 것
- P0-3 테스트체크리스트 실행
- rollback 실제 검증

## 통과 기준
- write loop 완전 동작

---

# STEP 3: P0-4 실행

## 입력
```text
SYSTEM PROMPT:
동일 유지

USER PROMPT:
GPT_ClaudeCode_P0-4_실행프롬프트.md
```

## 목표
- location/update
- 실행 파일 정리
- env 구조 정리
- 회귀 테스트

## 실행 후 반드시 할 것
- P0-4 테스트체크리스트 실행
- P0-2/P0-3 회귀 확인

---

# 5. 테스트 게이트 규칙

모든 단계는 반드시 아래 규칙을 따른다.

```text
1. 구현
2. 테스트
3. 실패 → 수정
4. 재테스트
5. 통과 → 다음 단계
```

---

# 6. 실패 시 대응 전략

## 유형 A: API 연결 실패
→ engine_adapter 확인

## 유형 B: 데이터 mismatch
→ normalize 추가

## 유형 C: rollback 실패
→ transaction 범위 수정

## 유형 D: UI만 동작
→ 실제 API 연결 여부 확인

---

# 7. 실행 금지 사항

```text
- 모든 단계 한 번에 실행 금지
- 테스트 없이 다음 단계 진행 금지
- mock 상태에서 완료 처리 금지
- engine 로직 직접 수정 금지
```

---

# 8. 최종 완료 흐름

```text
P0-2 PASS
→ P0-3 PASS
→ P0-4 PASS
→ 최종 완료보고서 작성
```

---

# 9. 루비 최종 판단

```text
Claude Code는 강력하지만,
단계별 테스트 게이트 없이 사용하면 반드시 실패한다.
```

즉,

```text
“단계 실행 + 테스트 + 통과” 이 3개가 핵심이다.
```
