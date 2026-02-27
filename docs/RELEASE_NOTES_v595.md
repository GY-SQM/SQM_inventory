# SQM v5.9.5 Release Notes — Allocation UI 연동

**Release Date:** 2026-02-18  
**Phase:** Phase 4 — Allocation UI 연동

---

## 변경 요약

### P4-1: Allocation 출고 예약 다이얼로그

- `gui_app_modular/dialogs/allocation_dialog.py` **신규 생성**
- Allocation 엑셀 파일 업로드 → 파싱 → 미리보기 (트리뷰) → 예약 실행
- 미리보기 컬럼: LOT NO, SAP NO, PRODUCT, QTY(MT), CUSTOMER, SALE REF, OUTBOUND DATE, WH, STATUS

### P4-2: 예약(RESERVED) 실행 + 현황 화면

- "✅ 예약 실행" 버튼: `engine.reserve_from_allocation()` 호출 → 톤백 AVAILABLE → RESERVED
- "📊 예약 현황" 버튼: `allocation_plan` 테이블에서 현재 예약 현황 조회 (LOT별 그룹핑)

### P4-3: 출고 실행(PICKED) + 확정(SOLD) UI

- "📦 출고 실행" 버튼: RESERVED → PICKED 전환 (`engine.execute_reserved()`)
- "🔒 출고 확정" 버튼: PICKED → SOLD 확정 (`engine.confirm_outbound()`)
- "❌ 예약 취소" 버튼: RESERVED → AVAILABLE 복원 (`engine.cancel_reservation()`)

### P4-4: 반품 UI RESERVED/SOLD 연동

- v5.9.3에서 이미 구현 완료 (return_mixin.py에서 SOLD, RESERVED 반품 지원)

### 메뉴 연동

- `📤 출고` 메뉴에 "📋 Allocation 출고 예약" 항목 추가
- `outbound_handlers.py`에 `_on_allocation_dialog()` 핸들러 추가

---

## 변경된 파일 (5개)

| 파일 | 변경 유형 |
|------|---------|
| `gui_app_modular/dialogs/allocation_dialog.py` | **신규** |
| `gui_app_modular/handlers/outbound_handlers.py` | 수정 |
| `gui_app_modular/mixins/menu_mixin.py` | 수정 |
| `version.py`, `VERSION.txt`, `updates/latest.json` | 버전 업데이트 |
| `docs/RELEASE_NOTES_v595.md` | **신규** |

---

## Allocation 워크플로우

```
1. 📂 Allocation Excel 선택 + 🔍 파싱
   → 미리보기 트리뷰에 LOT별 데이터 표시

2. ✅ 예약 실행 (AVAILABLE → RESERVED)
   → allocation_plan 테이블에 기록
   → 톤백 상태 변경

3. 📦 출고 실행 (RESERVED → PICKED)
   → 재고 current_weight 감소
   → stock_movement 기록

4. 🔒 출고 확정 (PICKED → SOLD)
   → 최종 확정

5. ❌ 예약 취소 (RESERVED → AVAILABLE)
   → 예약 해제, allocation_plan 'CANCELLED'
```

---

## 테스트 체크리스트

- [ ] 메뉴: 📤 출고 → 📋 Allocation 출고 예약 클릭
- [ ] Allocation Excel 파일 선택 + 파싱
- [ ] 미리보기 트리뷰 데이터 확인
- [ ] 예약 실행 → 톤백 RESERVED 상태 확인
- [ ] 예약 현황 조회 팝업
- [ ] 출고 실행 → PICKED 상태 확인
- [ ] 출고 확정 → SOLD 상태 확인
- [ ] 예약 취소 → AVAILABLE 복원 확인

---

**(주) 지와이로지스 2026년 2월 18일**
