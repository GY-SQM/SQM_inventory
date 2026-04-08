# GPT_P2_BATCH_C_ALL_IN_ONE_EXPANDED.md
작성일: 2026-04-07  
목적: Repository Pattern을 SQM 전체 DB 접근에 점진 도입하고, Batch C를 자동 실행 가능한 형태로 표준화한다.

---

# 0. 절대 규칙

- Batch C 동안 business rule 동시 변경 금지
- DB schema 전면 개편 금지
- 모든 DB 접근은 단계적으로 repository 경유로 치환
- 기존 운영 기능 삭제 금지
- commit/rollback 정책은 단일 기준으로 통일
- Batch C는 반드시 Pilot → 확장 순서로 진행

---

# 1. 단계 구성

- P2-C-01 : DB 접근 전수조사
- P2-C-02 : BaseRepository / DB helper 도입
- P2-C-03 : Inventory 조회 Pilot 전환
- P2-C-04 : Inbound repository 정식 전환
- P2-C-05 : Outbound repository 정식 전환
- P2-C-06 : commit/rollback/예외 정책 통일

---

# 2. 산출물

```text
repositories/base_repository.py
repositories/inventory_repository.py
repositories/inbound_repository.py
repositories/outbound_repository.py
scripts/verify_batch_c.py
tests/test_inventory_repository.py
tests/test_base_repository.py
docs/p2/maps/db_access_map.md
docs/p2/reports/batch_c_report.md
docs/p2/reports/db_repository_migration_checklist.md
run_batch_c.bat
```

---

# 3. P2-C-01 DB 접근 전수조사

## 목적
프로젝트 전체에서 DB 접근이 어디서 직접 발생하는지 찾는다.

## 조사 대상 패턴
```text
.cursor().execute(
self.conn.execute(
sqlite3.connect(
commit(
rollback(
```

## 산출물 예시
`docs/p2/maps/db_access_map.md`

```md
# db_access_map.md

| 파일 | DB 접근 유형 | 대상 테이블 | 전환 우선순위 |
|---|---|---|---|
| outbound_mixin.py | SELECT/UPDATE/INSERT | inventory_tonbag/outbound_item | 높음 |
| onestop_inbound.py | INSERT/SELECT | inventory_detail | 높음 |
| inventory_view.py | SELECT | inventory_detail | 중간 |
```

---

# 4. P2-C-02 BaseRepository / DB helper 도입

## 파일
`repositories/base_repository.py`

## 코드

```python
# -*- coding: utf-8 -*-
from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterable, Optional


class BaseRepository:
    def __init__(self, conn):
        self.conn = conn

    def execute(self, sql: str, params: Optional[Iterable[Any]] = None):
        cur = self.conn.cursor()
        cur.execute(sql, tuple(params or ()))
        return cur

    def fetchone(self, sql: str, params: Optional[Iterable[Any]] = None):
        return self.execute(sql, params).fetchone()

    def fetchall(self, sql: str, params: Optional[Iterable[Any]] = None):
        return self.execute(sql, params).fetchall()

    @contextmanager
    def transaction(self):
        try:
            yield self
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
```

---

# 5. P2-C-03 Inventory 조회 Pilot 전환

## 파일
`repositories/inventory_repository.py`

## 코드

```python
# -*- coding: utf-8 -*-
from __future__ import annotations

from repositories.base_repository import BaseRepository


class InventoryRepository(BaseRepository):
    def get_inventory_summary(self):
        return self.fetchall(
            '''
            SELECT product, COUNT(*) AS item_count, SUM(qty) AS total_qty
            FROM inventory_detail
            GROUP BY product
            ORDER BY product
            '''
        )
```

## 치환 예시

```python
# 기존
cur = self.conn.cursor()
rows = cur.execute("SELECT product, COUNT(*), SUM(qty) FROM inventory_detail GROUP BY product").fetchall()

# 변경
repo = InventoryRepository(self.conn)
rows = repo.get_inventory_summary()
```

---

# 6. P2-C-04 Inbound repository 정식 전환

## 파일
`repositories/inbound_repository.py`

## 코드

```python
# -*- coding: utf-8 -*-
from __future__ import annotations

from repositories.base_repository import BaseRepository


class InboundRepository(BaseRepository):
    def save_parsed_inbound(self, parsed) -> int:
        created = 0
        with self.transaction():
            for row in parsed.get("items", []):
                self.execute(
                    '''
                    INSERT INTO inventory_detail (bl_no, lot_no, product, qty, inbound_date)
                    VALUES (?, ?, ?, ?, ?)
                    ''',
                    (
                        row.get("bl_no"),
                        row.get("lot_no"),
                        row.get("product"),
                        row.get("qty"),
                        row.get("inbound_date"),
                    ),
                )
                created += 1
        return created
```

---

# 7. P2-C-05 Outbound repository 정식 전환

## 파일
`repositories/outbound_repository.py`

## 코드

```python
# -*- coding: utf-8 -*-
from __future__ import annotations

from repositories.base_repository import BaseRepository


class OutboundRepository(BaseRepository):
    def get_tonbag(self, tonbag_no: str):
        row = self.fetchone(
            '''
            SELECT tonbag_no, status, lot_no, bl_no
            FROM inventory_tonbag
            WHERE tonbag_no = ?
            ''',
            (tonbag_no,),
        )
        if not row:
            return None
        keys = ["tonbag_no", "status", "lot_no", "bl_no"]
        return dict(zip(keys, row))

    def mark_sold(self, tonbag_no: str) -> int:
        cur = self.execute(
            '''
            UPDATE inventory_tonbag
            SET status = 'SOLD'
            WHERE tonbag_no = ?
            ''',
            (tonbag_no,),
        )
        return cur.rowcount
```

---

# 8. P2-C-06 commit/rollback/예외 정책 통일

## 원칙

```text
1) repository 외부에서 개별 commit 남발 금지
2) transaction은 BaseRepository.transaction으로 통일
3) 실패 시 rollback, 성공 시 commit
4) 예외는 숨기지 말고 상위로 전파
```

## 금지 예시

```python
cur.execute(...)
self.conn.commit()
cur.execute(...)
self.conn.commit()
```

## 허용 예시

```python
with repo.transaction():
    repo.execute(...)
    repo.execute(...)
```

---

# 9. 테스트 코드

## 9-1. tests/test_base_repository.py

```python
# -*- coding: utf-8 -*-
import sqlite3

from repositories.base_repository import BaseRepository


def test_transaction_commit():
    conn = sqlite3.connect(":memory:")
    conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, name TEXT)")
    repo = BaseRepository(conn)

    with repo.transaction():
        repo.execute("INSERT INTO t (name) VALUES (?)", ("A",))

    row = conn.execute("SELECT COUNT(*) FROM t").fetchone()
    assert row[0] == 1
```

## 9-2. tests/test_inventory_repository.py

```python
# -*- coding: utf-8 -*-
import sqlite3

from repositories.inventory_repository import InventoryRepository


def test_inventory_summary():
    conn = sqlite3.connect(":memory:")
    conn.execute(
        "CREATE TABLE inventory_detail (product TEXT, qty REAL)"
    )
    conn.execute("INSERT INTO inventory_detail (product, qty) VALUES ('P1', 10)")
    conn.execute("INSERT INTO inventory_detail (product, qty) VALUES ('P1', 20)")
    conn.commit()

    repo = InventoryRepository(conn)
    rows = repo.get_inventory_summary()

    assert len(rows) == 1
```

---

# 10. 검증 자동화 스크립트

## 파일
`scripts/verify_batch_c.py`

## 코드

```python
# -*- coding: utf-8 -*-
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


CHECK_FILES = [
    "repositories/base_repository.py",
    "repositories/inventory_repository.py",
    "repositories/inbound_repository.py",
    "repositories/outbound_repository.py",
    "tests/test_base_repository.py",
    "tests/test_inventory_repository.py",
]


def check_exists():
    missing = [p for p in CHECK_FILES if not Path(p).exists()]
    if missing:
        print("[FAIL] missing files")
        for m in missing:
            print(" -", m)
        return False
    print("[PASS] files exist")
    return True


def run_py_compile():
    cmd = [sys.executable, "-m", "py_compile"] + CHECK_FILES[:4]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("[FAIL] py_compile")
        print(result.stdout)
        print(result.stderr)
        return False
    print("[PASS] py_compile")
    return True


def run_pytest():
    cmd = [sys.executable, "-m", "pytest", "tests/test_base_repository.py", "tests/test_inventory_repository.py", "-q"]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("[FAIL] pytest")
        print(result.stdout)
        print(result.stderr)
        return False
    print("[PASS] pytest")
    print(result.stdout)
    return True


def main():
    ok = True
    ok = check_exists() and ok
    ok = run_py_compile() and ok
    ok = run_pytest() and ok

    if ok:
        print("[FINAL] BATCH C verification PASS")
        sys.exit(0)
    print("[FINAL] BATCH C verification FAIL")
    sys.exit(1)


if __name__ == "__main__":
    main()
```

---

# 11. Batch C 완전 자동 실행 .bat

## 파일
`run_batch_c.bat`

## 코드

```bat
@echo off
setlocal

echo ========================================
echo [BATCH C] Repository Migration Auto Run
echo ========================================

echo [1/4] py_compile
python -m py_compile repositories/base_repository.py repositories/inventory_repository.py repositories/inbound_repository.py repositories/outbound_repository.py
if errorlevel 1 goto :fail

echo [2/4] pytest
python -m pytest tests/test_base_repository.py tests/test_inventory_repository.py -q
if errorlevel 1 goto :fail

echo [3/4] verify_batch_c
python scripts/verify_batch_c.py
if errorlevel 1 goto :fail

echo [4/4] DONE
echo BATCH C PASS
goto :end

:fail
echo BATCH C FAIL
exit /b 1

:end
endlocal
pause
```

---

# 12. Claude Code 실행 지시문

```text
Claude_SQM_v871 기준으로 P2 Batch C를 수행하라.
목표는 Repository Pattern을 프로젝트 DB 접근에 점진 도입하고, BaseRepository 기준으로 commit/rollback 정책을 통일하는 것이다.
다음 파일을 생성 또는 갱신하라:
- repositories/base_repository.py
- repositories/inventory_repository.py
- repositories/inbound_repository.py
- repositories/outbound_repository.py
- tests/test_base_repository.py
- tests/test_inventory_repository.py
- scripts/verify_batch_c.py
- docs/p2/maps/db_access_map.md
- docs/p2/reports/batch_c_report.md
- docs/p2/reports/db_repository_migration_checklist.md
- run_batch_c.bat

Pilot은 inventory read부터 시작하고, inbound/outbound 순으로 확장하라.
business rule 변경은 금지하고, DB 접근 경로만 정리하라.
각 단계 후 py_compile, pytest, verify_batch_c.py를 실행하고 결과를 보고서에 기록하라.
```

---

# 13. 완료 기준

- [ ] BaseRepository 도입 완료
- [ ] Inventory repository pilot 완료
- [ ] Inbound repository 전환 완료
- [ ] Outbound repository 전환 완료
- [ ] commit/rollback 정책 통일 완료
- [ ] verify_batch_c.py PASS
- [ ] run_batch_c.bat PASS

---

# 14. 결론

Batch C의 본질은 “패턴 도입”이 아니라
**DB 접근을 한 줄기 규칙으로 정리하는 것**이다.

즉, Business Rule보다 먼저
DB 접근 방식의 일관성을 확보하는 단계다.
