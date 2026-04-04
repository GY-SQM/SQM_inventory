# GPT_SQM_실행팩_ZIP_포장기준.md
생성일: 2026-04-04 16:46 (Asia/Seoul)

---

## [질문]
실행팩 ZIP 포장 기준 작성

## [질문의도]
실행팩을 압축하여 배포할 때
구조 깨짐 없이 전달하기 위한 기준 정의

---

# [응답]

# 1. ZIP 기본 원칙

```text
폴더 구조 그대로 유지
상대경로 유지
불필요 파일 제거
```

---

# 2. 포함 필수

- MASTER
- P0-1~4 문서
- prompts
- scripts
- autorun 문서
- reports 템플릿

---

# 3. 제외 항목

- 임시파일
- 중복파일
- 캐시파일
- 대용량 로그 (필요 시 일부만)

---

# 4. 압축 방법 (권장)

## 방법 A (GUI)
- 폴더 우클릭 → 압축

## 방법 B (PowerShell)
```powershell
Compress-Archive -Path SQM_P0_EXEC_PACK -DestinationPath SQM_P0_EXEC_PACK.zip
```

---

# 5. 압축 후 검증

- 다른 폴더에 풀기
- 구조 유지 확인
- scripts 실행 테스트
- prompt 경로 정상 확인

---

# 6. 배포 시 주의

- .env 제외 또는 별도 전달
- 경로 의존성 제거
- 버전명 명확히 표시

---

# 7. 루비 핵심

```text
ZIP은 전달이 아니라
"재현 가능한 실행 환경 전달"이어야 한다
```
