# GPT_SQM_Patch3_초상세_작업지시서.md
생성일: 2026-04-04 17:24 (Asia/Seoul)

[질문] Patch 3 초상세 작업지시서 작성  
[질문의도] DB 스키마 / migration / 로그 구조 정리를 실제 구현 가능한 수준으로 정리

# [응답]

## 1. Patch 3 목표

```text
audit_log / outbound_event_log / migration 구조를 정리해서
write loop와 자동실행 체계가 안정적으로 로그를 남기게 만든다
```

## 2. 세부 목표
- audit_log 최소 필수 컬럼 정의
- outbound_event_log 최소 필수 컬럼 정의
- created_at/default/nullability 정리
- action_type/event_type/status naming 정리
- migration 필요 여부 판단
- migration 초안 작성

## 3. 수정 대상
- react_api/services/action_service.py
- react_api/schemas/actions.py
- react_api/routes/actions.py
- migration scripts (필요 시 신규)
- DB 점검 문서 / 로그 구조 메모

## 4. 구현 순서
1. 현재 테이블 구조 재점검
2. 최소 필수 컬럼 대비 비교표 작성
3. migration 필요 여부 판정
4. logging insert 포맷 정리
5. success/fail 시나리오별 기록 방식 정리
6. 자동실행 results/logs와 연결 기준 정리

## 5. 완료 기준
- 로그 insert 구조가 명확
- success/fail 기록 가능
- migration 필요 여부 확정
- 자동화와 연결 가능한 로그 구조 확보
