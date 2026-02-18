# SQM v5.8.7 통합 패치 — FINAL

📅 2026-02-17 (화)

## 패치 파일 목록 (7개)

| # | 파일 | 위치 | 성격 |
|---|------|------|------|
| 1 | `utils/date_utils.py` | `utils/` | 🆕 신규 |
| 2 | `features/ai/gemini_parser.py` | `features/ai/` | ✏️ 덮어쓰기 |
| 3 | `parsers/document_parser_modular/bl_mixin.py` | `parsers/document_parser_modular/` | ✏️ 덮어쓰기 |
| 4 | `parsers/document_parser_modular/do_mixin.py` | `parsers/document_parser_modular/` | ✏️ 덮어쓰기 |
| 5 | `gui_app_modular/dialogs/onestop_inbound.py` | `gui_app_modular/dialogs/` | ✏️ 덮어쓰기 |
| 6 | `requirements.txt` | 루트 | ✏️ 덮어쓰기 |
| 7 | `README_PATCH_v587_FINAL.md` | 루트 (참고용) | 📄 |

## 적용 전 필수 작업

```bash
# 1. 기존 파일 백업
mkdir backup_v586a
cp features/ai/gemini_parser.py backup_v586a/
cp parsers/document_parser_modular/bl_mixin.py backup_v586a/
cp parsers/document_parser_modular/do_mixin.py backup_v586a/
cp gui_app_modular/dialogs/onestop_inbound.py backup_v586a/
cp requirements.txt backup_v586a/

# 2. tkcalendar 설치 (DatePicker 달력 UI)
pip install tkcalendar
```

## 변경 내용 총정리

### [A] Ship Date (B/L) 파싱 개선
- Gemini 프롬프트: `shipped_on_board_date` 키 1개로 통일
- 위치 힌트: "SHIPPED ON BOARD" 라벨 근처
- NOT_FOUND 강제 (빈 문자열 금지)
- 다중 키 순차 확인: shipped_on_board_date → shipped_date → ship_date
- 정규식 폴백: 7개 패턴 (SHIPPED ON BOARD DATE, LADEN ON BOARD 등)

### [B] Arrival Date (D/O) 파싱 개선
- Gemini 프롬프트: STEP 1→2→3 단계별 검색 지시
- 혼동 금지 목록: Free Time, 발행일, 출력일시와 구분
- all_dates_found: 문서 내 모든 날짜 수집
- 정규식 폴백: 6개 패턴 (선박 입항일, ETA, ATA 등)
- 3차 폴백: all_dates_found에서 earliest 추정

### [C] Free Time 계산
- calculate_free_time_status() 함수 복원
- 상태: NORMAL(7일+) / WARNING(4-7일) / URGENT(1-3일) / EXPIRED(0일↓)

### [D] normalize_date (6가지 형식)
- ISO: 2025-10-17
- 슬래시: 2025/10/17
- 점: 2025.10.17
- 유럽식: 17/10/2025
- 영문월: SEP 15, 2025 / 15 SEP 2025 / September 15, 2025
- 한글: 2025년 10월 17일

### [E] _dt 버그 수정
- onestop_inbound.py 4곳: `_dt.strptime` → `datetime.strptime`

### [F] D/O 없을 때 사용자 입력 팝업
- Case 1: D/O 자체가 없음 → 팝업
- Case 2: D/O 파싱 실패 → 팝업
- Case 3: 정상 → 팝업 안 뜸

### [G] DatePicker 달력 UI
- tkcalendar.DateEntry 사용 (달력 클릭으로 날짜 선택)
- tkcalendar 미설치 시 텍스트 입력으로 자동 폴백
- 3개 필드: Ship Date, ★Arrival Date(필수), Free Time

### [H] D/O 추후 첨부 버튼
- 팝업에 "📋 D/O 추후 첨부" 3번째 버튼 추가
- arrival_date 없이 입고 진행 가능
- 성공 메시지에 "나중에 [D/O 후속 연결] 메뉴에서 업데이트" 안내

### [I] _save_to_db 사용자 입력값 반영
- D/O 없어도 preview_data에서 사용자가 입력한 arrival_date/free_time 사용

## 하이브리드 폴백 원칙

```
Gemini 결과가 있나?
      │
  ┌───┴───┐
  │       │
 있다   NOT_FOUND
  │       │
  ▼       ▼
Gemini  정규식 시도
채택    (Gemini 값 없을 때만)
        │
    ┌───┴───┐
    │       │
  찾았다  못 찾음
    │       │
    ▼       ▼
  정규식  None
  채택    (진짜 없음)

★ 핵심: Gemini와 정규식을 동시에 돌리지 않음
★ Gemini가 값을 줬으면 정규식은 실행하지 않음
```
