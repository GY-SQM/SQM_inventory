# SQM Inventory v8.7.8 — 디버깅 백로그 B/C 안정화

**릴리즈 날짜**: 2026-06-15
**브랜치**: `claude/debugging-session-optimization-t3ayma`
**이전 버전**: v8.7.7
**테스트**: 299 passed, 1 deselected

---

## 🎯 개요

DEBUG_GOALS.md의 잔여 백로그 중 B3~B12와 C1~C4를 테스트 주도 방식으로 정리한 안정화 릴리즈입니다.

이번 릴리즈는 Allocation/입고/출고 스캔 흐름에서 “일부 실패 또는 선행조건 누락이 조용히 넘어가는” 문제를 줄이고, 사용자가 다음 조치를 알 수 있도록 오류 메시지와 회귀 테스트를 보강했습니다.

---

## ✅ 주요 수정

### B3~B12: 입고·Allocation 흐름 실패 사유 명시
- PDF 파싱 결과 LOT 0건일 때 성공처럼 보이지 않고 `PDF_PARSE_ZERO_LOTS`로 실패 처리
- Allocation 부분 성공/부분 실패 응답 분리 및 `PARTIAL_SUCCESS` 안내 추가
- 예약 직후 DB 재조회로 실제 `RESERVED` 수량을 재검증하고 불일치 시 `RESERVED_RECHECK_MISMATCH` 반환
- 승인 반영 중 일부 스킵/실패가 있으면 `APPLY_APPROVED_PARTIAL` 경고 반환
- Sales Order 검증 PASS 후에도 PICKED 전환이 별도 필요함을 `next_step`으로 안내
- 반품입고 Excel 매칭 실패 시 Excel 행 번호와 `RETURN_MATCH_NOT_FOUND` 사유 반환
- Allocation export 편집본 재업로드 시 DUPLICATE 충돌 원인을 `EDIT_EXPORT_DUPLICATE`로 안내
- 위치 후보 최신 batch가 없을 때 빈 결과 대신 “위치데이터 없음” 명시
- 입고 필수 검증에서 LOT 누락 early return을 제거하고 IB-01/IB-02/IB-08 오류를 일괄 반환
- Gemini AI 컬럼매핑 실패 시 `GEMINI_KEY_MISSING`, `GEMINI_UTILS_IMPORT_FAILED`, `AI_MAPPING_FAILED`를 사용자 응답에 포함

### C1~C4: 출고·피킹·바코드 스캔 흐름 보강
- PICKED→SOLD/OUTBOUND 확정 시 stock_movement 이력 기록이 기존 회귀 테스트로 보장됨을 확인하고 DEBUG_GOALS 상태 반영
- LOT 모드 스캔 STEP1(RESERVED→PICKED) 직후 상위 LOT 상태/무게 재계산 추가
- `stop_at_picked=True` 출고 경로에서 allocation_plan.source 컬럼이 없는 레거시 DB도 source 제외 fallback INSERT로 계획 기록 보장
- Allocation/배분 예약 계획이 없는 LOT 스캔 시 `LOT_SCAN_BLOCKED`만 반환하지 않고 다음을 포함:
  - 사용자 표시 `message`
  - `errors` 배열
  - `next_step.action = CREATE_ALLOCATION_PLAN`
  - “배분/예약 계획 생성 후 다시 스캔” 안내

---

## 🧪 신규/확인 회귀 테스트

추가 또는 확인된 테스트 파일:

- `tests/test_debug_goals_b3_pdf_zero_lots_fail.py`
- `tests/test_debug_goals_b4_allocation_partial_success.py`
- `tests/test_debug_goals_b5_reserved_recheck.py`
- `tests/test_debug_goals_b6_apply_approved_partial.py`
- `tests/test_debug_goals_b7_sales_order_next_step.py`
- `tests/test_debug_goals_b8_return_excel_row_errors.py`
- `tests/test_debug_goals_b9_allocation_export_edit_flag.py`
- `tests/test_debug_goals_b10_location_candidates_no_data.py`
- `tests/test_debug_goals_b11_inbound_collect_preflight.py`
- `tests/test_debug_goals_b12_allocation_ai_mapping_key_notice.py`
- `tests/test_v874_confirm_outbound_integrity.py`
- `tests/test_debug_goals_c2_barcode_step1_recalc.py`
- `tests/test_debug_goals_c3_stop_at_picked_allocation_plan.py`
- `tests/test_debug_goals_c4_lot_scan_blocked_reason.py`

---

## ✅ 검증 결과

실행 명령:

```bash
python -m pytest tests/test_debug_goals_c4_lot_scan_blocked_reason.py tests/test_debug_goals_c3_stop_at_picked_allocation_plan.py -q
python -m pytest tests/ -q --ignore=tests/test_inbound_doc_detector_artifact_guard.py --deselect tests/test_phase1_db_index.py::test_real_db_has_indexes
```

결과:

```text
4 passed in 0.05s
299 passed, 1 deselected in 9.91s
```

---

## 📌 커밋 범위

v8.7.7 이후 주요 커밋:

- `dd767f3` fix: 재고 페이지 응답 배열 정규화
- `cb84bad` fix: 페이지 응답 실패 상태 표시
- `9a234bf` fix: 라우터 초기화 실패 표시
- `e7dd1a6` fix: API 타임아웃 재시도 화면 추가
- `a874a80` fix: 출고 실패 재시도 버튼 추가
- `fe5ff65` fix: 승인 반영 SQL 상수 파라미터화
- `8c36e08` fix: PDF 입고 다음 단계 안내 추가
- `60dd517` fix: PDF 파싱 0건 실패 처리
- `8352f01` fix: Allocation 부분 처리 응답 분리
- `cc78314` fix: Allocation 예약 후 RESERVED 재검증
- `0371ade` fix: 승인 반영 부분 실패 표시
- `07994a0` fix: Sales Order 검증 후 다음 단계 안내
- `3521734` fix: 반품입고 행별 실패 사유 반환
- `eebb7a7` fix: Allocation export 편집 재업로드 충돌 안내
- `fd062f7` fix: 위치 후보 데이터 없음 명시
- `1d07ca7` fix: 입고 필수 검증 오류 일괄 반환
- `8c552c7` fix: Allocation AI 매핑 실패 사유 표시
- `f636ad8` test: 출고확정 이력 목표 검증 완료
- `d16154b` fix: LOT 스캔 STEP1 후 상태 재계산
- `e8801a1` fix: PICKED 경로 allocation plan 기록 보장
- `61cbcdb` fix: LOT 스캔 차단 사유 명시

---

## ⚠️ 참고

- 로컬 `.bkit/*` 상태 파일과 엑셀 임시 파일은 릴리즈 커밋에 포함하지 않습니다.
- GUI 실기동은 Windows/PyWebView 환경 의존이므로 이번 검증은 headless pytest와 정적 회귀 테스트 중심으로 수행했습니다.
- DEBUG_GOALS.md 기준 다음 잔여 항목은 C5부터입니다.
