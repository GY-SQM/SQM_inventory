# Ship Date / Arrival Date / Free Time — 가이드 vs 현재 구현 비교

> **목적**: 이전에 에러 없이 동작하던 파싱·알고리즘 가이드와 현재 코드베이스를 비교해 차이를 표로 정리합니다.  
> **작성일**: 2026-02-16

---

## 1. 전체 흐름 비교

| 단계 | 가이드 (이전/설계) | 현재 구현 | 비고 |
|------|-------------------|-----------|------|
| **진입** | `document_parser_v2.py` → `parse()` / 문서 유형 감지 | `DocumentParserV2` → **DocumentParserV3**(Modular) 위임 → 파일명/유형별 `parse_*` | V2는 래퍼, 실제는 V3 |
| **B/L 파싱** | `parse_bl()` + **정규식** `_extract_ship_date()`, `_normalize_date()` | **Gemini API** (`features/ai/gemini_parser.parse_bl`) → JSON에서 `shipped_date`/`ship_date` 추출 | 정규식 없음, API 응답에 의존 |
| **D/O 파싱** | `parse_do()` + **정규식** `_extract_arrival_date()`, `_extract_free_time()` | **Gemini API** (`gemini_parser.parse_do`) → JSON에서 `arrival_date`, `containers[].free_time`(반납일) | Free Time = 반납일(con_return) − 입항일(일수) |
| **날짜 정규화** | `_normalize_date()`, `_parse_korean_date()`, `_parse_english_date()` | Gemini에 "YYYY-MM-DD" 요청 + `engine_modules/.../base.py` `_safe_parse_date()` | 로컬 정규식 정규화 없음 |
| **DB 저장** | **shipment** 테이블: `ship_date`, `arrival_date`, `free_days`, `stock_date` | **inventory** 테이블: `ship_date`, `arrival_date`, `free_time`(정수 일수). **shipment** 테이블은 현재 원스톱 입고 경로에서 미사용 | 저장 위치·컬럼명 상이 |

---

## 2. B/L — Ship Date

| 항목 | 가이드 | 현재 구현 | 차이/에러 가능 원인 |
|------|--------|-----------|----------------------|
| **파싱 방식** | 정규식: `SHIPPED ON BOARD`, `ON BOARD DATE`, `DATE OF SHIPMENT`, `LADEN ON BOARD` 등 | Gemini 프롬프트: `"shipped_date": "선적일 YYYY-MM-DD (문서 왼쪽 하단/날짜 필드)"` | 가이드의 **키워드**가 프롬프트에 없음 → 모델이 해당 필드를 놓칠 수 있음 |
| **날짜 형식** | DD/MM/YYYY, YYYY-MM-DD, MAR 15 2025, 한글 등 `_normalize_date()`로 통일 | API가 YYYY-MM-DD 반환 기대, 실패 시 `_safe_parse_date()` | API가 다른 형식 반환 시 파싱 실패 가능 |
| **결과 필드** | `BLData.ship_date` | `BLResult.ship_date` / `shipped_date` (gemini_parser) | 호출부는 `bl.ship_date` 사용, 매핑 추가됨 |
| **실제 사용 경로** | parse_bl() → bl_data → engine | V3 `parse_bl()` → Gemini → **do_mixin에서 arrival_date만 매핑**, BL 결과는 bl_mixin → onestop에서 `bl.ship_date`/`bl.shipped_date` 참조 | BL → onestop → packing_dict → inbound_mixin까지 ship_date 전달됨 |

---

## 3. D/O — Arrival Date

| 항목 | 가이드 | 현재 구현 | 차이/에러 가능 원인 |
|------|--------|-----------|----------------------|
| **파싱 방식** | 정규식: `ETA`, `ATA`, `ARRIVAL DATE`, `입항예정일` 등 | Gemini 프롬프트: `"선박 입항일(arrival_date)", "(For Local Use)"` 등 | 가이드의 **ETA/ATA/ARRIVAL DATE** 키워드가 프롬프트에 명시돼 있음 |
| **결과 전달** | `DOData.arrival_date` | Gemini `DOResult.arrival_date` → **do_mixin에서 DOData.arrival_date로 복사** (추가 반영됨) | 이전에 do_mixin에서 arrival_date 미매핑 → 수정됨 |
| **None/빈값** | — | `str(None)` → `"None"` 전달 시 파싱 실패 → `_safe_parse_date`에서 `"None"` 문자열 무시, do_dict에서 `''` 처리 | 이전 에러 원인 중 하나였음 |

---

## 4. Free Time / 무료장치기간

| 항목 | 가이드 | 현재 구현 | 차이/에러 가능 원인 |
|------|--------|-----------|----------------------|
| **의미** | **free_days**(일수) + `free_time_end = arrival_date + free_days` | D/O의 **Free_Time 컬럼 = 컨테이너 반납일(con_return)** → **free_time = (con_return − arrival_date) 일수** | 가이드: “일수” 중심 / 현재: “반납일” 중심 계산 |
| **파싱** | 정규식: `FREE TIME: 14 DAYS`, `DETENTION FREE`, `무료장치기간` 등, **기본값 14일** | Gemini: 컨테이너별 `free_time`(날짜) → `free_time_info[].free_time_date`(con_return) | 가이드처럼 “14 DAYS” 형태가 아닌 “날짜”만 추출 |
| **저장** | `shipment.free_days` (정수) | `inventory.free_time` (정수, con_return − arrival 일수) | 컬럼명·의미 일치함(일수). shipment vs inventory만 다름 |
| **경고 로직** | `remaining_days = free_time_end - today`, 빨강/노랑/녹색 | 현재 리스트는 **free_time(일수)**만 표시, remaining_days 경고는 별도 구현 여부 확인 필요 | 가이드의 “남은 일수” 경고가 동일하게 있는지 코드에서 확인 필요 |

---

## 5. DB 저장 위치

| 항목 | 가이드 | 현재 구현 | 비고 |
|------|--------|-----------|------|
| **테이블** | **shipment**: ship_date, arrival_date, free_days, stock_date | **inventory**: ship_date, arrival_date, free_time | shipment 테이블은 DB에 존재하나 **원스톱 입고 경로에서는 미사용** |
| **stock_date** | arrival_date 또는 오늘 | 가이드와 달리 **arrival 미상 시 오늘 사용 금지** (비움 처리) | 의도적 차이 |

---

## 6. 파싱 진입점·파일 위치

| 역할 | 가이드 (파일/함수) | 현재 구현 (파일/함수) |
|------|---------------------|-------------------------|
| **메인 파서** | `parsers/document_parser_v2.py` — `DocumentParserV2`, `parse_bl()` / `parse_do()` | `parsers/document_parser_v2.py`(래퍼) → `document_parser_modular/parser.py` **DocumentParserV3** → `bl_mixin.parse_bl`, `do_mixin.parse_do` |
| **B/L Ship Date** | `_extract_ship_date()`, `_normalize_date()` (정규식) | `features/ai/gemini_parser.py` **parse_bl()** — JSON `shipped_date`/`ship_date` |
| **D/O Arrival** | `_extract_arrival_date()` (정규식) | `gemini_parser.parse_do()` + **do_mixin**에서 `result.arrival_date` 매핑 |
| **D/O Free Time** | `_extract_free_time()` (정규식, 기본 14일) | `gemini_parser` containers[].free_time(날짜) → do_mixin `free_time_info[].free_time_date` → **일수 = con_return − arrival** |
| **날짜 정규화** | `_normalize_date()` (다양한 형식) | `engine_modules/inventory_modular/base.py` **`_safe_parse_date()`** (문자열 → date) |
| **입고 처리** | `engine.py` `process_inbound_safe()`, bl_data/do_data 사용 | `engine_modules/inventory_modular/inbound_mixin.py` **process_inbound()**, packing_dict / bl_data / do_data |

---

## 7. 에러 가능 원인 요약 (가이드 대비)

| # | 원인 | 권장 조치 |
|---|------|-----------|
| 1 | **B/L Ship Date**: 프롬프트에 "SHIPPED ON BOARD DATE", "ON BOARD DATE" 등 **가이드 키워드 없음** | Gemini BL 프롬프트에 가이드와 동일한 필드 설명 추가 (예: "SHIPPED ON BOARD DATE, ON BOARD DATE, DATE OF SHIPMENT, LADEN ON BOARD 중 선적일을 YYYY-MM-DD로") |
| 2 | **전부 API 의존**: 정규식 폴백 없음. API가 필드를 비우면 곧바로 빈값 | (선택) 이미지/텍스트 추출 후 `parsers/pdf_parser.py`의 정규식 로직을 **폴백**으로 호출하는 경로 검토 |
| 3 | **DO arrival_date**: do_mixin 매핑 추가로 해결됨. 다만 API가 "선박 입항일"을 빈값으로 주면 여전히 빈칸 | 프롬프트에 "ETA, ATA, ARRIVAL DATE, 입항예정일, (For Local Use) 선박 입항일" 등 **가이드 키워드** 명시해 두기 |
| 4 | **shipment 테이블 미사용**: 가이드는 shipment 저장, 현재는 inventory만 저장 | 기능 요구사항에 따라 shipment에도 동기화할지 결정 후, 필요 시 process_inbound 쪽에서 shipment INSERT 추가 |

---

## 8. 요약 표 (한 줄)

| 항목 | 파싱 소스 | 가이드 위치 | 현재 위치 |
|------|------------|-------------|-----------|
| **Ship Date** | B/L | document_parser_v2 → _extract_ship_date (정규식) | gemini_parser.parse_bl (JSON) + bl_mixin |
| **Arrival Date** | D/O | document_parser_v2 → _extract_arrival_date (정규식) | gemini_parser.parse_do + **do_mixin arrival_date 매핑** |
| **Free Time** | D/O | _extract_free_time (일수, 기본 14) | DO Free_Time 컬럼 → con_return → (con_return − arrival) 일수 |
| **저장** | — | shipment 테이블 | **inventory** 테이블 (ship_date, arrival_date, free_time) |

---

## 9. 재고 리스트 디버깅 (ARRIVAL/SHIP DATE/FREE TIME)

| 현상 | 원인 | 조치 (v5.8.8 반영) |
|------|------|---------------------|
| **ARRIVAL에 "광양"** | D/O·Gemini가 입항일 대신 항구/창고명(warehouse)을 `arrival_date`로 반환한 경우 | Gemini 결과에 **날짜 검증** 적용: `normalize_date()`로 파싱 가능한 값만 사용, 그 외(예: '광양')는 빈값. onestop_inbound·_fill_do에서도 YYYY-MM-DD 형태가 아니면 저장하지 않음. |
| **SHIP DATE 빈값** | B/L에서 선적일 미추출, 또는 packing에 `ship_date` 미전달 | B/L 파서(Gemini)에서 `shipped_date`/`ship_date` 추출 확인. 입고 시 packing_dict의 `ship_date`는 bl.ship_date 또는 invoice.invoice_date에서 채움. 파싱 불가 시 `_prepare_lot_data`에서 빈 문자열로 통일. |
| **FREE TIME 빈값** | D/O에서 **컨테이너 반납일(con_return_date)** 미추출 → 일수 계산 불가 | D/O 문서의 Free_Time(반납일) 컬럼을 Gemini가 `containers[].con_return_date` 또는 `free_time_date`로 추출하는지 확인. do_mixin `free_time_info[].free_time_date` → inbound_mixin에서 (반납일 − 입항일) 일수로 계산. con_return 미추출 시 디버그 로그 출력. |

**변수 구분 (혼동 방지):**  
- `arrival_date` = 입항일(날짜 YYYY-MM-DD)  
- `warehouse` = 창고(예: 광양) — ARRIVAL 컬럼에 넣지 않음  
- `free_time_date` / `con_return` = 컨테이너 반납일  
- `free_time` = 일수(반납일 − 입항일)

---

*작성일: 2026-02-16 | v5.8.8: 재고 리스트 디버깅 섹션 추가*
