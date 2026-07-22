## SQM v9.0.5 — Central Allowlist audit_log 자동 정리

릴리즈일: 2026-07-22
대상: v9.0.4 → v9.0.5
대분류: minor (운영 부담 ↓)

### v9.0.5 Step 1: audit_log 자동 정리
- core/db_allowed.py
  - `cleanup_audit(days=30)`: N일 이전 row 삭제
  - days <= 0 → no-op (안전)
  - DB 없거나 실패 시 0 반환
  - logger.info로 삭제 row 수 기록
- backend/api/db_allowed_stats.py (확장)
  - `POST /api/admin/db-allowed/audit/cleanup?days=30`
  - days: 1~365 (default 30)
  - 응답: `{ ok, data: { deleted, days } }`
- tests/test_db_allowed.py
  - TestAuditCleanup (T40~T42, 3 tests)
  - 기본 cleanup (오래된 row 삭제 + 최근 row 유지)
  - days=0/-1 → no-op
  - DB 없으면 0 반환
- tests/test_db_allowed_stats_endpoint.py
  - E07: cleanup endpoint 검증

### 회귀
- 622 passed (v9.0.4 618 + 신규 4)

### 운영 효과
- 운영 DB 부담 ↓ (audit_log 자동 정리)
- 기본 30일 보관, 1~365일 설정 가능
- silent failure (모니터링은 critical 아님)
- 윈도우 스케줄러에 등록 가능 (예: 매주 일요일 cleanup)

### 다음 (v9.0.6+)
- dynamic set → 명시적 allowlist 변환 (queries3.py L644/653/891)
- SQL context lint (broad → narrow)
- audit_log 자동 정리 스케줄러 등록
- Phase 3 (새 시즌)
