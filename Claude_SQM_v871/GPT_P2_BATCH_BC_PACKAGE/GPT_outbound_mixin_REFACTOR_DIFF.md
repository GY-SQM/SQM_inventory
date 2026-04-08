# GPT_outbound_mixin_REFACTOR_DIFF.md
작성일: 2026-04-07

## 목적
`outbound_mixin.py`를 **실전적으로** 어떻게 줄여야 하는지,
기존 구조와 목표 구조를 diff 형태로 설명한다.

---

## 1. 리팩토링 목표

### 기존
- UI 이벤트
- 상태검증
- SELECT
- UPDATE
- INSERT
- COMMIT
- 메시지 표시
- refresh

가 한 함수에 섞여 있음

### 목표
- mixin: UI adapter
- query repo: 조회
- write repo: 쓰기
- service: 상태전이 및 업무 규칙
- state_rules: 정책 정의

---

## 2. BEFORE 예시

```python
def on_scan_submit(self, tonbag_no):
    cur = self.conn.cursor()
    row = cur.execute(
        "SELECT tonbag_no, status FROM inventory_tonbag WHERE tonbag_no=?",
        (tonbag_no,)
    ).fetchone()

    if not row:
        self.show_error("톤백 없음")
        return

    if row[1] != "PICKED":
        self.show_error("상태 오류")
        return

    cur.execute(
        "UPDATE inventory_tonbag SET status='SOLD' WHERE tonbag_no=?",
        (tonbag_no,)
    )
    cur.execute(
        "UPDATE outbound_item SET status='SOLD' WHERE tonbag_no=?",
        (tonbag_no,)
    )
    cur.execute(
        "INSERT INTO stock_movement (tonbag_no, action) VALUES (?, ?)",
        (tonbag_no, "SCAN_SOLD")
    )
    self.conn.commit()
    self.refresh_outbound()
    self.show_info("출고 완료")
```

---

## 3. AFTER 예시

```python
from engine_modules.inventory_modular.outbound_query import OutboundQueryRepository
from engine_modules.inventory_modular.outbound_repository import OutboundWriteRepository
from engine_modules.inventory_modular.outbound_service import OutboundService

def on_scan_submit(self, tonbag_no):
    query_repo = OutboundQueryRepository(self.conn)
    write_repo = OutboundWriteRepository(self.conn)
    service = OutboundService(query_repo, write_repo)

    result = service.confirm_scan_and_mark_sold(tonbag_no)

    if result.success:
        self.refresh_outbound()
        self.show_info(result.message)
    else:
        self.show_error(result.message)
```

---

## 4. 실전 diff 포인트

### 4-1. 조회 제거

```diff
- row = cur.execute("SELECT tonbag_no, status FROM inventory_tonbag WHERE tonbag_no=?", (tonbag_no,)).fetchone()
+ tonbag = query_repo.get_tonbag_by_no(tonbag_no)
```

### 4-2. 상태전이 판단 제거

```diff
- if row[1] != "PICKED":
-     self.show_error("상태 오류")
-     return
+ result = service.confirm_scan_and_mark_sold(tonbag_no)
```

### 4-3. 직접 UPDATE 제거

```diff
- cur.execute("UPDATE inventory_tonbag SET status='SOLD' WHERE tonbag_no=?", (tonbag_no,))
- cur.execute("UPDATE outbound_item SET status='SOLD' WHERE tonbag_no=?", (tonbag_no,))
- cur.execute("INSERT INTO stock_movement (tonbag_no, action) VALUES (?, ?)", (tonbag_no, "SCAN_SOLD"))
- self.conn.commit()
+ # service 내부 transaction에서 처리
```

### 4-4. UI는 결과 처리만

```diff
- self.conn.commit()
- self.refresh_outbound()
- self.show_info("출고 완료")
+ if result.success:
+     self.refresh_outbound()
+     self.show_info(result.message)
+ else:
+     self.show_error(result.message)
```

---

## 5. 반드시 제거해야 할 흔적

아래 문자열이 `outbound_mixin.py`에 남아 있으면 분해가 불완전한 것임.

```text
SELECT 
UPDATE inventory_tonbag
UPDATE outbound_item
INSERT INTO stock_movement
self.conn.commit(
cursor().execute(
```

---

## 6. 리팩토링 완료 판정 기준

- mixin 내부의 SQL이 UI 조회용 극소량만 남거나 완전히 제거됨
- scan 정책은 service에서만 결정
- transaction은 write repo/service 경계에서만 처리
- UI는 result.success/result.message만 소비

---

## 7. 결론

`outbound_mixin.py`는 **업무 엔진**이 아니라
**UI adapter**로 축소되어야 한다.

즉, “코드를 줄이는 것”보다
“책임을 밖으로 밀어내는 것”이 리팩토링의 본질이다.
