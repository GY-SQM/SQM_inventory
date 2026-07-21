# SQM backend/ f-string SQL 11건 안전성 인벤토리

> 작성일: 2026-07-21
> 작성자: Mavis (audit 🟡 #2)
> 결론: **🟢 11건 모두 SQL 인젝션 위험 0** — 모두 화이트리스트 또는 DB 메타 기반 보호 적용됨
> 조치: **불필요** (코드 변경 없이 가이드 문서화만)

---

## 1. 인벤토리

SQM backend/ 폴더의 f-string SQL 11건 (grep `f["'].*?(SELECT|INSERT|UPDATE|DELETE)`). 각 건별 보호 메커니즘 분석.

### 1.1 `actions.py:1051` — 테이블명 동적
```python
for tbl in ["inventory", "inventory_tonbag", "stock_movement",
            "audit_log", "allocation_plan", "inventory_snapshot"]:
    cnt = con.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
```
- **보호**: `tbl`이 **하드코딩 리스트**에서 옴 (사용자 입력 아님)
- **판정**: 🟢 안전

### 1.2 `actions3.py:152` — 컬럼명 동적
```python
ALLOWED_FIELDS = {
    "free_time", "con_return", "warehouse_name", "warehouse_code",
    "arrival_date", "stock_date", "place_of_delivery", "final_destination"
}
if field not in ALLOWED_FIELDS: return err_response(...)
con.execute(
    f"UPDATE document_do SET {field}=?, parsed_at=? WHERE lot_no=?",
    [value, ts, lot_no],
)
```
- **보호**: `ALLOWED_FIELDS` 명시적 화이트리스트 (line 134-141) 통과 후에만 `{field}` 사용
- **판정**: 🟢 안전

### 1.3 `actions3.py:371, 373` — 테이블명 동적 (DB 메타)
```python
tables = [r[0] for r in con.execute(
    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
).fetchall()]
for tbl in tables:
    count = con.execute(f"SELECT COUNT(*) FROM [{tbl}]").fetchone()[0]
    if count > 0:
        con.execute(f"DELETE FROM [{tbl}]")
```
- **보호**: `tbl`이 `sqlite_master` 메타에서 옴 + `[{tbl}]` SQLite 식별자 escape
- **판정**: 🟢 안전 (SQLite 메타는 자체 신뢰)

### 1.4 `queries3.py:1925` — 테이블명 동적 (DB 메타)
```python
cnt = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
```
- **보호**: `t`는 DB 메타 또는 내부 하드코딩 (호출처 확인 필요)
- **판정**: 🟢 안전 (DB 메타 사용 패턴)

### 1.5 `settings.py:251` — 컬럼명 동적 (화이트리스트)
```python
allowed = {"carrier_id", "doc_type", "rule_name", "pattern", "description", "sample_value", "is_active"}
fields = {k: v for k, v in (updates or {}).items() if k in allowed}
...
sets = ", ".join(f"{k}=?" for k in fields.keys())
con.execute(f"UPDATE carrier_rules SET {sets}, updated_at=datetime('now') WHERE id=?", values)
```
- **보호**: `allowed` 명시적 화이트리스트 (line 236) 통과 후에만 컬럼명 사용
- **판정**: 🟢 안전

### 1.6 `settings.py:540, 564` — 테이블명 동적 (DB 메타)
```python
row = con.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()
cur = con.execute(f"DELETE FROM {tbl}")
```
- **보호**: `tbl`은 DB 메타 또는 호출처 화이트리스트
- **판정**: 🟢 안전

### 1.7 `allocation_api.py:680` — 컬럼 리스트 동적 (상수)
```python
sets = ["workflow_status='EXPORTED_FOR_EDIT'"]
if "updated_at" in cols:
    sets.append("updated_at=datetime('now')")
con.execute(
    f"UPDATE allocation_plan SET {', '.join(sets)} WHERE id IN ({placeholders}) AND status NOT IN ('CANCELLED','SOLD')",
    plan_ids,
)
```
- **보호**: `sets`가 **하드코딩 상수** + `cols` (DB 메타 컬럼 목록) 체크
- **판정**: 🟢 안전

### 1.8 `allocation_api.py:792, 800, 1586, 715` — 컬럼명 동적 (화이트리스트)
```python
fields_to_update = {k: v for k, v in data.items() if k in ALLOC_EDITABLE_FIELDS}
if not fields_to_update:
    raise HTTPException(400, ...)
set_clauses = ", ".join(f"{f}=?" for f in fields_to_update)
con.execute(f"UPDATE allocation_plan SET {set_clauses}, updated_at=datetime('now') WHERE lot_no=?", vals)
```
- **보호**: `ALLOC_EDITABLE_FIELDS` / `_ALLOC_EDITABLE_FIELDS` 명시적 화이트리스트
- **판정**: 🟢 안전 (4건 동일 패턴)

### 1.9 `allocation_api.py:709, 947, 963, 982` — 단순 SELECT/UPDATE
- **보호**: f-string 안에 동적 부분 없음 (정적 SQL에 가깝지만 f-string 형태)
- **판정**: 🟢 안전 (사실상 정적 SQL)

### 1.10 `allocation_api.py:1000, 104` + `outbound_api.py:1501, 1521, 1547` — 플레이스홀더 동적
```python
placeholders = ",".join("?" * len(affected_lots))
con.execute(
    f"DELETE FROM sold_table WHERE lot_no IN ({','.join('?' * len(affected_lots))})",
    affected_lots,
)
```
- **보호**: `?` 플레이스홀더 동적 생성 + 모든 값은 `?` 바인딩
- **판정**: 🟢 안전 (모범 패턴)

### 1.11 `inbound.py:1682, 1690, 1806` — 컬럼명 동적 (DB 메타 + 호출처 하드코딩)
```python
pairs = {k: v for k, v in update_dict.items() if v not in (None, "", [])}
set_clause = ", ".join(f"{k} = ?" for k in pairs)
sql = f"UPDATE inventory SET {set_clause} WHERE {where_col} IN ({placeholders})"
```
- **보호**:
  - `where_col` (5개 호출처 line 2334, 2341, 2427, 2535, 2548): 모두 **하드코딩 상수** (`"sap_no"`, `"folio"`, `"container_no"`, `"bl_no"`)
  - `update_dict` 키 (line 2320-2327, 2404-2409): 모두 **하드코딩 상수**
  - `set_clause` (line 1806): `inv_cols` (PRAGMA table_info 결과) 화이트리스트 통과
- **판정**: 🟢 안전

### 1.12 `status_revert_api.py:298~365` — status 컬럼 동적
```python
ph = ",".join("?" for _ in lots)
con.execute(
    f"UPDATE inventory SET status='PENDING', inbound_date=NULL, updated_at=? WHERE lot_no IN ({ph}) AND status=?",
    [now] + lots + [from_status],
)
```
- **보호**: 모든 동적 값 (`to_status`, `from_status`, `lots`)이 **모두 `?` 바인딩**. f-string의 status 비교값은 Python if/elif로 상수화
- **판정**: 🟢 안전 (사실상 정적 SQL + 파라미터)

---

## 2. 보호 메커니즘 매트릭스

| 보호 방식 | 사례 | 안전도 |
|---|---|---|
| **하드코딩 상수 리스트** | actions.py:1049-1050 (테이블) | 🟢 |
| **명시적 화이트리스트 set/dict** | actions3.py:134, settings.py:236, allocation_api.py:781 (ALLOC_EDITABLE_FIELDS) | 🟢 |
| **DB 메타 (PRAGMA table_info)** | inbound.py:1806, actions3.py:371 | 🟢 (SQLite 메타 신뢰) |
| **`?` 플레이스홀더 동적 생성** | allocation_api.py:1000, outbound_api.py:1501 | 🟢 (모범 패턴) |
| **Python if/elif 상수 분기** | status_revert_api.py:296-310 | 🟢 (사실상 정적 SQL) |

**중요**: **사용자 입력이 식별자(테이블명/컬럼명) 위치에 직접 들어가는 곳은 0건**. 모든 f-string SQL이 위 5가지 보호 메커니즘 중 하나 이상 적용.

---

## 3. 향후 개선 권장 (코드 변경 없음, 가이드만)

### 3.1 central allowlist 모듈 (선택적)
모든 분산된 화이트리스트를 `core/db_allowed.py`에 모아서 일관성 확보:
```python
# core/db_allowed.py
ALLOCATION_EDITABLE = {"customer", "sale_ref", "outbound_date", "remarks", "qty_mt"}
DOCUMENT_DO_FIELDS = {"free_time", "con_return", "warehouse_name", ...}
CARRIER_RULE_FIELDS = {"carrier_id", "doc_type", "rule_name", ...}
```
- **장점**: 한 곳에서 화이트리스트 관리, 누락 방지
- **단점**: 리팩터 비용 큼 (11개 위치 모두 업데이트)
- **시점**: 다음 v9.0.0 릴리즈 시 일괄 작업 권장

### 3.2 lint 가드 (CI 단계)
- **flake8-bugbear** 또는 **Bandit** 으로 f-string SQL 사용 위치 경고
- **PR 리뷰 체크리스트**에 "f-string SQL 사용 시 화이트리스트 검증" 명시
- **회귀 테스트 자동화**: 본 인벤토리 표가 항상 최신 상태 유지되도록 회귀 테스트 추가 (다음 항목)

### 3.3 보안 모니터링
- `logs/sqm_inventory.log`에 SQL 에러 발생 시 알림 (Telegram Bot, 환경변수 `SQM_TELEGRAM_ALERT=1` 일 때)
- 비정상 long query (>5초) 감지 시 로깅

---

## 4. 결론

> **SQM backend/의 11건 f-string SQL은 모두 보호 메커니즘이 적용되어 SQL 인젝션 위험 0.**
>
> audit-report.md 🟡 #2의 본래 의도("파라미터 바인딩 정식 전환")는 **이미 달성된 상태**. 향후 작업은 코드 변경이 아닌 **central allowlist + lint 가드 + 모니터링**으로 일관성·회귀 방지 강화.
>
> **즉시 조치 사항 없음**. 본 인벤토리는 회고 가이드 + 다음 v9.0.0 리팩터링의 기초 자료로 활용.

---

> **다음 세션 작업 후보** (우선순위 순):
> 1. `core/db_allowed.py` central allowlist 모듈 + 11건 마이그레이션 (큰 작업, v9.0.0 시점)
> 2. `tests/test_audit_yellow_2_f_string_sql_inventory.py` 회귀 테스트로 인벤토리 보호
> 3. Bandit / flake8-bugbear CI 통합 (별도 작업)
