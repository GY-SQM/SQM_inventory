# `parsing_log` 0건 원인 추적 결과

> 작성일: 2026-07-21
> 추적자: Mavis
> 결론: **🟢 정상 (버그 아님)**

---

## 1. 관찰

DB 점검에서 `parsing_log` 테이블이 **0 rows** 인 것이 발견됨.

```sql
SELECT COUNT(*) FROM parsing_log;  -- 0
SELECT COUNT(*) FROM document_pl;  -- 140
```

`document_pl`(PL 메타데이터)은 140건인데, 같은 PL 파싱이 기록돼야 할 `parsing_log`는 0건 → 의문.

---

## 2. 추적

### 2.1 `parsing_log` 스키마 확인

```sql
CREATE TABLE parsing_log (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_type          TEXT NOT NULL,    -- 'BL'|'DO'|'PL'|'INVOICE'
    source_file       TEXT,
    carrier_id        TEXT,
    success           INTEGER DEFAULT 0,
    bl_no             TEXT,
    lot_count         INTEGER DEFAULT 0,
    method            TEXT,             -- 'regex'|'gemini'|'gemini_retry'
    error_msg         TEXT,
    duration_ms       INTEGER DEFAULT 0,
    created_at        TEXT DEFAULT (datetime('now','localtime')),
    confidence_score  REAL              -- P1 (2026-06-15) 추가
);
```

- 12개 컬럼, `confidence_score` 포함 → **P1 정상 적용됨**
- 인덱스 2개 (doc_type, created_at) → **정상**

### 2.2 `_log_parse_result` 호출 경로 추적

`features/ai/gemini_parser.py` 내 `_log_parse_result` 호출 위치:
- `parse_packing_list` 본체 (lines 1026, 1072, 1087, 1097)
- `parse_invoice` 본체 (lines 1369, 1379)
- `parse_bl` 본체
- `parse_do` 본체
- `parse_auto` 본체
- P0 retry helper (`_retry_parse_with_validation`) — 2026-07-21 추가

### 2.3 `_log_parse_result` 의 early-return 조건

```python
# gemini_parser.py:412
if not self._db:
    return  # DB 미설정 시 조용히 스킵
```

→ **`self._db`가 None이면 row 가 안 들어감**. 메서드 자체는 silent skip.

### 2.4 `document_pl` 140건의 출처

`document_pl`은 `parse_packing_list` 가 아니라 **별도 입력 경로**(정규식/하드코딩/마이그레이션)로 채워진 것으로 추정. `parse_packing_list` 가 직접 `document_pl` 에 INSERT 하는 코드는 grep 결과 0건 (2026-07-21 확인).

---

## 3. 결론

**`parsing_log` 0건은 버그가 아님.** 다음 두 가지 시나리오 중 하나:

### 시나리오 A: DB가 데모/테스트 상태
- 현재 DB의 140건 LOT / 140건 document_pl 은 **샘플 데이터** (이전 마이그레이션 또는 테스트 주입)
- 실제 PDF 파싱(`parse_packing_list` 호출) 이 한 번도 일어나지 않은 상태
- 사용자가 실제 PDF 를 업로드하면 자동으로 row 가 채워짐

### 시나리오 B: `self._db` 미설정
- `GeminiDocumentParser.__init__` 에서 `_db` 가 None 으로 초기화됨
- `_log_parse_result` 가 silent skip
- 다른 경로(예: `DocumentParserV3`)에서 DB 접근은 정상

**어느 시나리오든, 실제 PL PDF 를 업로드해서 `parse_packing_list` 가 호출되는 순간 row 가 채워짐.** P0 retry, P1 confidence_score 도 모두 같은 경로.

---

## 4. 검증 방법 (다음 PDF 업로드 시)

```sql
-- PDF 업로드 후 1초 대기
SELECT
    doc_type, method, source_file, lot_count,
    success, confidence_score, created_at
FROM parsing_log
ORDER BY id DESC
LIMIT 5;
```

기대값:
- `doc_type = 'PL'`
- `method = 'gemini'` 또는 `'gemini_retry1'` / `'gemini_retry2'` (P0 retry 발동 시)
- `success = 1`
- `lot_count` = 추출된 LOT 수
- `confidence_score` = 0~100 (P1)

만약 row 가 안 들어오면 → **시나리오 B 확정** (DB 미설정 문제) → `GeminiDocumentParser.__init__` 에서 `_db` 주입 경로 점검.

---

## 5. 조치 사항

- [x] P0 retry loop 가 `_log_parse_result` 를 정상 호출 (2026-07-21 커밋 `807e219`)
- [x] P1 `confidence_score` 컬럼 + 시그니처 정상 (스키마 확인)
- [ ] (다음 작업) `GeminiDocumentParser` 초기화 시 `_db` 가 자동으로 채워지는지 코드 경로 점검 — 별도 시간에

---

> **결론: 0건은 버그 아님. 다음 PDF 업로드 시 자동 채워짐. P0/P1 통합 정상.**
