## SQM v9.0.3 — Central Allowlist audit_log 영속화

릴리즈일: 2026-07-22
대상: v9.0.2 → v9.0.3
대분류: minor (모니터링 영속화)

### v9.0.3 Step 1: audit_log DB 영속화
- core/db_allowed.py
  - import: sqlite3
  - `_init_audit_table(db_path)`: 자동 마이그레이션
    - `CREATE TABLE IF NOT EXISTS db_allowed_audit` (id, ts, area, kind, result, value)
    - 인덱스: ts, kind
  - `_get_default_db_path()`: config.DB_PATH 또는 None
  - `_write_audit(area, kind, result, value)`: silent insert
    - best-effort (DB 실패 시 in-memory만, 모니터링은 critical 아님)
  - validate() 모든 분기에 `_write_audit()` 호출 통합
- tests/test_db_allowed.py
  - TestAuditLog 클래스 (T37~T39, 3 tests)
  - idempotent: 두 번 호출해도 OK
  - INSERT 검증, INDEX 검증

### 회귀
- 615 passed (v9.0.2 612 + 신규 3)

### 운영 효과
- 운영 DB에 `db_allowed_audit` 테이블 자동 생성 (마이그레이션)
- validate() 호출이 DB에 영구 기록
- 차단 시도(allowed=False) 추적 가능
- 백엔드 운영자가 시간대별/유형별 분석 가능
- 기존 데이터/스키마 영향 없음 (테이블만 추가)

### 다음 (v9.0.4+)
- dynamic set → 명시적 allowlist 변환 (queries3.py L644/653/891)
- SQL context lint (broad → narrow)
- audit_log 조회 endpoint (`GET /api/admin/db-allowed/audit?since=...`)
- Phase 3 (새 시즌)
