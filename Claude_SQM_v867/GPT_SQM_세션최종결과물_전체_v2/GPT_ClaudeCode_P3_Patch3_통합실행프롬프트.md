# GPT_ClaudeCode_P3_Patch3_통합실행프롬프트.md
생성일: 2026-04-04 17:24 (Asia/Seoul)

현재 작업은 SQM 시스템의 **P3 + Patch 3 통합 단계**다.

목표:
1. 운영 자동화 구조를 강화한다
2. audit_log / outbound_event_log / migration 구조를 안정화한다
3. 단계별 실행/결과/로그가 반복 가능하게 만든다

절대 금지:
- 로그 없이 자동화 진행 금지
- migration 필요성을 무시하고 임시 땜질만 하는 것 금지
- service 층에서 DB 로그 규칙을 제각각 구현하는 것 금지
- 테스트 실패 상태에서 다음 단계 진행 금지

핵심 작업:
1. 현재 로그 테이블 구조 재점검
2. 최소 필수 컬럼 기준 확정
3. logging insert 규칙 정리
4. run_all_p0 / run_stage 결과 기록 구조 강화
5. results / logs / reports 연결 구조 정리

완료 기준:
- 성공/실패 로그 구조 안정
- 자동화 단계 상태 추적 가능
- migration 필요 여부 명확
- P0 실행 체계 회귀 없음

반드시 남길 것:
- 수정 파일 목록
- DB/로그 구조 변경 요약
- migration 필요 여부
- 테스트 결과
- 남은 이슈
