# RELEASE NOTES — SQM v7.3.2

📅 릴리즈: 2026-03-13  
🔧 버전: 7.3.2 (버그 수정 통합본)

---

## 개요

v7.3.2는 **버그 수정 및 UI/상수 통일**을 담은 안정화 릴리즈입니다.  
전체 앱·API·모듈 버전 표기를 **7.3.2**로 통일했습니다.

---

## 변경 사항

### [HERO-COLOR]
- Hero 배경 **진한 네이비 고정** (current_theme 속성명 수정)

### [SQL-LITERAL]
- **ALLOC_CANCELLED** / **WF_REJECTED** SQL 리터럴 수정

### [STATUS-BAR]
- **\_refresh_move_pending_badge** 메서드 추가 (이동 대기 배지 갱신)

### [CONSTANTS]
- **tkinter 상수 30개** re-export 완전판 (constants.py)

### 테스트
- **406 passed** ✅

---

## 버전 통일 범위

| 구분 | 내용 |
|------|------|
| `version.py` | __version__ = "7.3.2" (Single Source of Truth) |
| API (FastAPI) | version="7.3.2", HealthResponse 동일 |
| 메뉴/타이틀 fallback | 7.3.2 |
| 모듈 docstring | SQM v7.3.2 — … 로 통일 |
| sqm_v710_patch | 7.3.2 |

---

## 빌드 정보

- **BUILD_DATE**: 2026-03-12  
- **APP_NAME**: SQM 재고관리 시스템  

---

*최종 수정: 2026-03-13*
