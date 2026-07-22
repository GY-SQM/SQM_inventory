## SQM v8.8.5 — Database Optimization & Audit Hardening

릴리즈일: 2026-07-22
대상: v8.8.4 → v8.8.5 (14개 커밋)

### 데이터베이스 유지보수 및 디스크 최적화
- sqm_inventory.db 무결성 검증 / REINDEX / VACUUM
- audit_log 58개 과거 이력 아카이브 / DB 슬림화
- 윈도우 스케줄러 자동 디스크 청소 (월/수/금 11:00)
- pip 캐시 3.42 GB 정리

### 전수 감사 🟡 4건 해결 — 모든 권고 반영 완료
- 🟡 #1: PG_PASSWORD 기본값 'postgres' → ''로 정리
- 🟡 #2: f-string SQL 11건 안전성 인벤토리 (위험 0, 보호 메커니즘 5종)
- 🟡 #3: STRIDE I/D 공통 인프라 (error_helpers, upload_limits)
  - STRIDE I migration 65건 (backend/api 8개 파일 일괄)
- 🟡 #4: main_webview.py debug 로그 회전 정책

### AI 오케스트레이션 P0/P1/P2 완료
- P0: 검증기반 프롬프트 교정 재파싱 루프
- P1: PL 파싱 신뢰도 DB 영속화
- P2: 프롬프트 핑거프린트 DB 영속화

### 회귀 테스트
- 552 passed (베이스라인 527 + 신규 25)

### 출고 가능
- 사내 배포: 즉시 가능
- 외부 거래처·GitHub 공개: 모든 권고 반영 완료, 즉시 출고 가능