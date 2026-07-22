## SQM v9.0.4 — Central Allowlist audit_log 조회 endpoint

릴리즈일: 2026-07-22
대상: v9.0.3 → v9.0.4
대분류: minor (모니터링 가시성 +1)

### v9.0.4 Step 1: audit_log 조회 endpoint
- backend/api/db_allowed_stats.py (확장)
  - `GET /api/admin/db-allowed/audit` 추가
  - 쿼리 파라미터:
    - `since`: YYYY-MM-DD (시작일)
    - `kind`: table/status/area/scope_type/lot_field/file_ext
    - `blocked_only`: True면 차단 시도만 (result=0)
    - `limit`: 1~1000 (default 100)
  - 응답: `{ ok, data: { rows: [{ts, area, kind, result, value}, ...], count, limit } }`
  - DB 경로 없으면 graceful fail (ok=False)
  - monkeypatch 호환: `core.db_allowed._get_default_db_path()` 모듈 attribute 직접 호출
- tests/test_db_allowed_stats_endpoint.py (확장)
  - E04~E06: 3 tests (DB 경로 없음, 기본 조회, kind 필터)

### 회귀
- 618 passed (v9.0.3 615 + 신규 3)

### 운영 효과
- 운영자가 시간대별/유형별 차단 시도 분석 가능
- `?since=2026-07-22` 로 일별 통계
- `?blocked_only=true` 로 차단 시도만
- `?kind=table` 로 특정 kind 필터
- 시간순 정렬 (최근 100건)

### 다음 (v9.0.5+)
- dynamic set → 명시적 allowlist 변환 (queries3.py L644/653/891)
- SQL context lint (broad → narrow)
- audit_log 자동 정리 (예: 30일 지난 row 삭제)
- Phase 3 (새 시즌)
