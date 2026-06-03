# AI 채팅 수정 모드 — 보안 PIN + 롤백 설계 스펙

**날짜:** 2026-06-03
**작성:** Claude (brainstorming 기반)
**범위:** AI 채팅에서 PIN 인증 후 데이터 수정 허용 + ai_edit_log 롤백

---

## 1. 목표

AI 채팅창에서 보안 PIN 인증 후 SQLite 데이터 수정(UPDATE)을 허용한다.
모든 변경은 `ai_edit_log` 테이블에 기록되어 자연어 명령으로 롤백 가능하다.

---

## 2. 전체 아키텍처

```
[AI 채팅 헤더] 🔒 버튼
      ↓ 클릭
[PIN 입력 팝업] ── 틀리면 → 오류 메시지 (3회 실패 → 30초 차단)
      ↓ 맞으면
[Backend] PIN bcrypt 검증 → write_session 토큰 발급 (10분 TTL)
      ↓
[AI 쿼리 엔진] write_mode=True → UPDATE SQL 생성 허용
      ↓ 실행 전
[ai_edit_log] 변경 전 값 스냅샷 저장
      ↓
[SQLite] UPDATE 실행
      ↓
[채팅 응답] "입고일이 2026-06-01로 변경됐습니다. (취소: '방금 변경 취소해줘')"
```

---

## 3. 허용 / 차단 범위

| 구분 | 내용 |
|---|---|
| **수정 허용 (PIN 필요)** | 모든 테이블 모든 필드 UPDATE |
| **항상 차단** | DELETE, DROP, ALTER, INSERT(신규 레코드), 구조 변경 |
| **PIN 없이 허용** | SELECT 조회, 롤백 명령 |

---

## 4. 데이터베이스 — ai_edit_log 테이블

```sql
CREATE TABLE IF NOT EXISTS ai_edit_log (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  table_name  TEXT    NOT NULL,
  record_id   INTEGER NOT NULL,
  field_name  TEXT    NOT NULL,
  old_value   TEXT,
  new_value   TEXT,
  sql_used    TEXT,
  changed_at  TEXT    NOT NULL,   -- ISO 8601
  rolled_back INTEGER DEFAULT 0   -- 0: 유효, 1: 롤백됨
);
```

---

## 5. 롤백 자연어 명령

| 사용자 입력 | 동작 |
|---|---|
| `방금 변경 취소해줘` | 최신 1건 롤백 |
| `마지막 3건 취소` | 최근 3건 롤백 |
| `오늘 변경한 거 전부 롤백` | 오늘 날짜 전체 롤백 |
| `변경 이력 보여줘` | ai_edit_log 최근 20건 조회 표시 |
| `2026-06-03 변경분 취소` | 특정 날짜 롤백 |

**롤백 규칙:**
- 롤백은 PIN 없이 실행 가능 (실수 복구 우선)
- `rolled_back=1` 항목은 재롤백 불가
- 롤백 실행 자체도 ai_edit_log에 별도 row 기록

---

## 6. UI 컴포넌트

### 6-1. 잠금 버튼 (AI 채팅 헤더 우측)

| 상태 | 표시 | 색상 |
|---|---|---|
| 잠김 | `🔒 수정 잠김` | 회색 |
| 해제됨 | `🔓 N분 남음` | 녹색 |
| 만료 1분 전 | `🔓 1분 남음` | 주황색 |

- 잠김 상태 클릭 → PIN 팝업
- 해제 상태 클릭 → 즉시 재잠금

### 6-2. PIN 입력 팝업 (채팅 오버레이)

```
┌─────────────────────────┐
│  🔐 수정 모드 잠금 해제  │
│                         │
│       [ • • • • ]       │  ← type="password"
│                         │
│    [취소]    [확인]      │
│                         │
│  ⚠ 3회 실패 시 30초 잠금 │
└─────────────────────────┘
```

- 4~6자리 숫자
- Enter 키 확인 지원
- ESC 키 취소

### 6-3. PIN 설정 (기존 ⚙️ 설정 모달에 섹션 추가)

```
── AI 수정 PIN ──────────────────
현재 PIN: [••••]
새 PIN:   [    ]
확인:     [    ]
          [PIN 변경]
※ 기본값 0000 — 최초 변경 권장
```

---

## 7. 세션 관리

| 상황 | 처리 |
|---|---|
| 10분 경과 | 자동 잠금 + 채팅에 만료 안내 메시지 |
| PIN 3회 실패 | 30초 입력 차단 (카운트다운 표시) |
| 사용자 수동 잠금 | 즉시 세션 무효화 |
| 앱 재시작 | 항상 잠긴 상태로 초기화 |
| 탭/창 닫기 | 세션 유지 안 함 |

---

## 8. config.json 저장 형식

```json
{
  "ai_write_pin_hash": "$2b$12$xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
  "ai_write_session_minutes": 10
}
```

- PIN은 bcrypt 해시로만 저장 (평문 저장 금지)
- 기본 PIN `0000`은 앱 첫 실행 시 자동 해시화하여 저장
- `ai_write_session_minutes`: 1~60 사이, 기본 10

---

## 9. 백엔드 API 변경

### 신규 엔드포인트

| 메서드 | 경로 | 설명 |
|---|---|---|
| `POST` | `/api/ai/write-unlock` | PIN 검증 + 세션 토큰 발급 |
| `POST` | `/api/ai/write-lock` | 수동 잠금 |
| `GET` | `/api/ai/write-status` | 현재 세션 상태 조회 |

### 기존 변경

- `POST /api/ai/chat` — 요청에 `write_session_token` 포함 시 write_mode=True로 처리

---

## 10. 쿼리 엔진 변경 (gemini_chat_query.py)

- `write_mode=False`(기본): SELECT/WITH만 허용 (기존 동작 유지)
- `write_mode=True`: UPDATE 허용, 실행 전 `ai_edit_log`에 old_value 기록 후 실행
- UPDATE 생성 프롬프트에 추가 규칙:
  - "반드시 WHERE 절 포함 (전체 UPDATE 금지)"
  - "1개의 UPDATE 문만 생성"
  - "DELETE/DROP/ALTER/INSERT 절대 금지"

---

## 11. 변경 파일 목록

| 파일 | 변경 유형 |
|---|---|
| `frontend/detached/ai_chat.html` | 잠금 버튼 + PIN 팝업 UI 추가 |
| `backend/api/ai_gemini.py` | write_mode 처리 + 신규 엔드포인트 3개 |
| `features/ai/gemini_chat_query.py` | write_mode 분기 + ai_edit_log 기록 |
| `backend/database.py` (또는 init) | ai_edit_log 테이블 생성 마이그레이션 |
| `config.json` | ai_write_pin_hash, ai_write_session_minutes 필드 추가 |
| `frontend/js/sqm-tools-modals.js` | 설정 모달 PIN 변경 섹션 추가 |
