# SQM v7.1.2 — P0/P1 패치 로드맵 + Bug6 감사 보고서

작성: Ruby (Claude) | 기준버전: SQM v7.1.2 | 작성일: 2026-03-10

---

## 📋 현황 요약

| 항목 | 내용 |
|------|------|
| 현재 버전 | SQM v7.1.2 |
| 테스트 결과 | 406 PASS / 0 FAIL / 6 SKIPPED ✅ |
| 7-Gate 부합 | 7/7 완전 부합 ✅ |
| FAIL 60건 | 전량 구현 완료 ✅ |
| Bug6 감사 | continue 16건 전수조사 — 실제위험 0건 ✅ |

---

## ✅ 이미 해결된 항목 (P0 전량 완료)

### P0-1: 동일 LOT 다중 Allocation 누적 초과
- **해결 버전**: v7.1.2
- **패치**: `[G5-BATCH-SUM]` — `reserve_from_allocation()` L1256~L1303
- **동작**: 배치 진입 전 `_batch_lot_qty` 딕셔너리로 동일 LOT 합산
  → 합산 > cargo + 0.5kg → G5-HARD-STOP 전체 배치 즉시 차단
- **상태**: ✅ 완료

### P0-2: selectable pool 부족 미검출
- **해결 버전**: v6.9.x (기존 구현)
- **동작**: `len(tonbags) < pick_count` → NO_AVAILABLE_TONBAG Hard Stop
- **상태**: ✅ 완료

### P0-3: 샘플 1kg Allocation 포함 오류
- **해결 버전**: v7.1.1
- **패치**: `[SAMPLE-SCAN-1]` — `is_sample=1` 또는 `sub_lt=0` → SAMPLE_SCAN_BLOCKED
- **상태**: ✅ 완료

### P0-4: LOT 정규화 불일치
- **해결 버전**: 기존 구현 (v6.x)
- **동작**: `core/types.py` `normalize_lot()` — 전체 루프에 적용
- **상태**: ✅ 완료

### P0-5: RESERVED/STAGED 충돌
- **해결 버전**: 기존 구현 (v6.7.1)
- **동작**: STAGED + PENDING_APPROVAL 만료 건 자동 REJECTED
  tonbags 조회 시 WHERE `status = AVAILABLE` 만 대상
- **상태**: ✅ 완료

### P0-6: 조기 return/continue 로 Gate 스킵 (Bug6)
- **해결 버전**: v7.1.2 감사 완료
- **판정**: 아래 Bug6 감사 보고서 참조
- **상태**: ✅ 실제 위험 없음 확인

---

## ✅ 이미 해결된 항목 (P1 전량 완료)

### P1-1: TONBAG 수 계산 불일치
- **동작**: `sublot_count` vs `qty_mt ÷ unit_weight` 교차검증
- **상태**: ✅ 완료

### P1-2: 랜덤 선택 로그 부족
- **해결 버전**: v7.1.2
- **패치**: `[G7-RANDOM-LOG]` — audit_log `ALLOC_RANDOM_LOG` JSON 저장
- **필드**: random_seed / candidate_bag_list / selected_bag_list / excluded_bag_list / excluded_reason / selection_timestamp
- **상태**: ✅ 완료

### P1-3: 상태값 전이 불일치
- **동작**: 전체 `IMMEDIATE` 트랜잭션 — All-or-Nothing 보장
- **상태**: ✅ 완료

### P1-4: 취소/반품 복구 오류
- **해결 버전**: v7.1.0
- **패치**: `[CANCEL-INTEGRITY-1]` — 취소 후 `verify_lot_integrity()` 자동 실행
- **상태**: ✅ 완료

---

## 🔍 Bug6 감사 보고서 (v7.1.2 확정)

### 감사 대상
- 함수: `reserve_from_allocation()` (L1122~L1988, 866줄)
- 조사 항목: `continue` 전수조사 + `return result` 전수조사

### continue 16건 전수조사 결과

| 라인 | 직전 조건 | 판정 | 근거 |
|------|----------|------|------|
| L1273 | `_bqt_sum <= 0` | ✅ 의도적 | G5 사전필터: qty=0인 LOT 무시 |
| L1334 | `INVALID_LOT` | ✅ 정상 | 입력오류 → 해당 행 스킵 |
| L1344 | `ZERO_QTY` | ✅ 정상 | qty=0 → 해당 행 스킵 |
| L1352 | `INVALID_QTY` | ✅ 정상 | 음수/비정상 qty → 해당 행 스킵 |
| L1360 | `INVALID_CUSTOMER` | ✅ 정상 | 고객명 오류 → 해당 행 스킵 |
| L1368 | `INVALID_SALE_REF` | ✅ 정상 | sale_ref 오류 → 해당 행 스킵 |
| L1423 | `SALE_REF_CONFLICT` | ✅ 정상 | 기존 sale_ref 충돌 → 해당 행 스킵 |
| L1442 | `LOT_MODE_DUP` | ✅ 정상 | LOT 모드 중복 → 해당 행 스킵 |
| L1475 | `LOT_NOT_FOUND` | ✅ 정상 | LOT DB 없음 → 해당 행 스킵 |
| L1504 | `G2_CARGO_EXCEED` | ✅ 정상 | cargo 초과 → 해당 행 스킵 |
| L1517 | `LOT_STATUS_MISMATCH` | ✅ 정상 | LOT 상태 불일치 → 해당 행 스킵 |
| L1608 | `NO_AVAILABLE_TONBAG` | ✅ 정상 | 가용 톤백 없음 → 해당 행 스킵 |
| L1656 | `INVALID_OUTBOUND_DATE` | ✅ 정상 | 출고일 오류 → 해당 행 스킵 |
| L1670 | `QTY_EXCEEDS_AVAILABLE` | ✅ 정상 | 수량 초과 → 해당 행 스킵 |
| L1700 | `QTY_EXCEEDS_AVAILABLE` | ✅ 정상 | 수량 초과(세부) → 해당 행 스킵 |
| L1759 | STAGED 승인대기 완료 | ✅ 의도적 | allocation_plan 적재 후 다음 LOT 진행 |

**continue 판정 요약**: 정상차단 14건 + 의도적 설계 2건 = **실제 위험 0건**

### return result 2건 전수조사 결과

| 라인 | 직전 조건 | 판정 | 근거 |
|------|----------|------|------|
| L1303 | G5-HARD-STOP | ✅ 의도적 | 전체 배치 즉시 차단 — 설계상 정상 |
| L1986 | 함수 종료 | ✅ 정상 | 최종 result 반환 |

### 최종 판정

```
Bug6 실제 위험: 0건
→ P0 위험 해소 완료 (v7.1.2)
```

---

## 📅 다음 세션 예약 (v7.2.0~)

### v7.2.0 즉시
```python
# menu_registry.py FILE_MENU_OUTBOUND_ITEMS 추가 (1줄)
("📟 실시간 바코드 스캔 (USB 스캐너)", "_on_barcode_live_scan"),
("🧪 Allocation 7-Gate Stress Test",   "_on_allocation_stress_test"),

# outbound_handlers.py 추가
def _on_allocation_stress_test(self):
    from gui_app_modular.dialogs.Claude_allocation_stress_test_v712 import AllocationStressTestDialog
    AllocationStressTestDialog(self, self.engine)
```

### v7.2.x
- `document_parser_v2.py` 참조 파일 3개 마이그레이션 후 삭제
  - onestop_inbound.py / do_update_dialog.py / gui_bootstrap.py
- SMTP 이메일 알림 완성

---

## 🗂️ 산출물 파일 목록 (v7.1.2 TestKit)

| 파일 | 위치 | 용도 |
|------|------|------|
| `Claude_sqm_testdata_gen_v712.py` | `tools/` | Allocation 테스트 데이터 생성기 (7시나리오) |
| `Claude_allocation_stress_test_v712.py` | `gui_app_modular/dialogs/` | 7-Gate + Bug6 Stress Test 다이얼로그 |
| `Claude_sqm_p0p1_roadmap_v712.md` | `docs/` | 본 문서 |

---

## GitHub Push 명령 (기동님 직접 실행)

```bash
cd C:\SQM\sqm_v700
git add -A
git commit -m "v7.1.2 TestKit: testdata_gen + stress_test_dialog + p0p1_roadmap + Bug6감사"
git push origin main
```
