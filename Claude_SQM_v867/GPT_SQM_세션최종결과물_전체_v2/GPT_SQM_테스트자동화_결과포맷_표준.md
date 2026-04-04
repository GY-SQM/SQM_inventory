# GPT_SQM_테스트자동화_결과포맷_표준.md
생성일: 2026-04-04 18:26 (Asia/Seoul)

[질문] 테스트 자동화 결과 포맷 표준 작성  
[질문의도] 단계별 테스트 결과를 일관된 형식으로 저장하기 위한 기준 정의

---

# [응답]

# 1. 파일명 규칙

```text
[stage]_result.json
예:
p0_2_result.json
p0_3_result.json
patch2_result.json
```

---

# 2. 필수 필드

- stage
- status
- started_at
- ended_at
- log_file
- checks
- notes

---

# 3. status 허용값

- PASS
- CONDITIONAL_PASS
- FAIL

---

# 4. checks 배열 예시

```json
[
  {"name": "log_exists", "status": "PASS"},
  {"name": "result_file_exists", "status": "PASS"},
  {"name": "fatal_error_scan", "status": "FAIL"},
  {"name": "warning_scan", "status": "PASS"}
]
```

---

# 5. notes 예시

```json
[
  "warning 2건 발견",
  "manual UI check required"
]
```

---

# 6. 루비 원칙

```text
결과 파일은 사람이 읽기 쉬워야 하고,
스크립트가 읽기 쉬워야 한다.
```
