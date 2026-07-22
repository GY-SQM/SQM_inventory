## SQM v9.0.2 — Central Allowlist 모니터링 (GET endpoint)

릴리즈일: 2026-07-22
대상: v9.0.1 → v9.0.2
대분류: minor (모니터링 가시성)

### v9.0.2 Step 1: GET endpoint
- backend/api/db_allowed_stats.py (NEW, 1.2 KB)
  - `GET /api/admin/db-allowed/stats`
  - `core.db_allowed.stats_detailed()` 노출
  - raw_counts (디버깅용): (area|kind|result) → count
  - prefix: `/api/admin`, tag: `admin`
- tests/test_db_allowed_stats_endpoint.py (NEW, 2.2 KB, 4 tests)
  - E01: 기본 (빈 카운터, 200 OK)
  - E02: validate() 후 통계 반영
  - E03: raw_counts 형식 검증
  - FastAPI TestClient 사용 (in-memory app)

### 회귀
- 612 passed (v9.0.1 608 + 신규 4)

### 다음 (v9.0.3+)
- audit_log 영속화 (in-memory → DB)
- dynamic set → 명시적 allowlist 변환 (queries3.py L644/653/891)
- SQL context lint (broad → narrow)
- Phase 3 (새 시즌)
