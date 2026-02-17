# SQM v5.8.6.B 패치 — Ship Date / Arrival Date / Free Time 파싱 개선

## 패치 일시: 2026-02-17
## 작성자: Ruby

---

## 변경 요약

| # | 파일 | 변경 내용 |
|---|------|----------|
| 1 | `utils/date_utils.py` | 🆕 신규 — normalize_date() + 정규식 폴백 + Free Time 계산 |
| 2 | `features/ai/gemini_parser.py` | BL/DO 프롬프트 개선 + 키 매핑 수정 |
| 3 | `parsers/document_parser_modular/bl_mixin.py` | ship_date 매핑 + 정규식 폴백 |
| 4 | `parsers/document_parser_modular/do_mixin.py` | arrival_date 매핑 + 정규식 폴백 + Free Time 계산 |

## 적용 방법

1. `utils/date_utils.py` → `utils/` 폴더에 복사
2. `gemini_parser.py` → `features/ai/gemini_parser.py` 덮어쓰기 (백업 먼저!)
3. `bl_mixin.py` → `parsers/document_parser_modular/bl_mixin.py` 덮어쓰기
4. `do_mixin.py` → `parsers/document_parser_modular/do_mixin.py` 덮어쓰기

## 핵심 변경 3가지

### 1. Ship Date (B/L)
- 프롬프트: `shipped_date` + `ship_date` 2개 → `shipped_on_board_date` 1개로 통일
- 매핑: 3개 키 순차 확인 (`shipped_on_board_date` → `shipped_date` → `ship_date`)
- 폴백: Gemini 실패 시 정규식으로 "SHIPPED ON BOARD" 뒤 날짜 검색

### 2. Arrival Date (D/O)
- 프롬프트: STEP 1→2→3 단계별 검색 지시 + 혼동 금지 목록 + NOT_FOUND 강제
- 매핑: normalize_date() 적용 (6가지 날짜 형식 지원)
- 폴백: Gemini 실패 → 정규식 → all_dates_found 추정 (3단계)

### 3. Free Time 계산
- calculate_free_time_status() 함수 복원 (문서 1에서 이식)
- arrival_date 있을 때만 계산 (연쇄 실패 방지)
- 상태: NORMAL / WARNING / URGENT / EXPIRED
