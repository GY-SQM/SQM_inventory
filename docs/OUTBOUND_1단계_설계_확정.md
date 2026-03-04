# process_outbound() 1단계 설계 확정 (Ruby 권장안 반영)

**기준일:** 2026-02-21  
**목적:** 1단계 구현 시 혼선 방지를 위한 설계 확정 사항 정리.

---

## 1. PICKED에서 멈출지, SOLD까지 갈지

| 구분 | 동작 | Ruby 권장 |
|------|------|-----------|
| **빠른 출고** (간편 출고, Ctrl+O) | RESERVED → PICKED에서 **멈춤** (이후 Picking List 등으로 확정) | ✅ **빠른 출고만 PICKED 멈춤** |
| **그 외 4곳** (배정표 출고, Excel 간편, 배치 출고, 톤백수 템플릿 출고) | 기존처럼 **SOLD까지 자동** | ✅ **나머지는 SOLD까지 자동** |

**정리:**  
- `process_outbound()` 내부에서 **호출 출처**를 구분할 수 있어야 함 (예: 인자에 `stop_at_picked: bool` 또는 `source_kind: str`).  
- **빠른 출고**만 `stop_at_picked=True`(또는 `source_kind='QUICK'`)로 두고 PICKED에서 멈추고,  
- 나머지는 기존처럼 PICKED → SOLD까지 한 번에 처리.

---

## 2. allocation_plan에 source 컬럼 추가

| 항목 | 내용 | Ruby 권장 |
|------|------|-----------|
| **현재** | allocation_plan 테이블에 `source_file`(파일 경로)만 있음, **source**(출처 유형) 없음 | — |
| **추가** | `source` 컬럼 추가 (예: `'ALLOCATION'`, `'AUTO'`, `'PICKING_LIST'`) | ✅ **지금 추가** (1단계 마이그레이션에 포함) |

**정리:**  
- **마이그레이션**에서 `ALTER TABLE allocation_plan ADD COLUMN source TEXT DEFAULT 'AUTO'` (또는 NOT NULL이 필요하면 기존 행 업데이트 후 추가).  
- `reserve_from_allocation()` 및 `process_outbound()` 내부에서 allocation_plan INSERT/UPDATE 시 **source** 값을 넣어 주기.  
  - Allocation 파일 → `'ALLOCATION'`  
  - process_outbound() 자동 예약 → `'AUTO'`  
  - (3단계 이후) Picking List → `'PICKING_LIST'` 등.

---

## 3. Excel 배정표 출고(_on_outbound_click) 경로 전환

| 항목 | 내용 | Ruby 권장 |
|------|------|-----------|
| **현재** | `_on_outbound_click` → 파일 선택 → 파싱 → 미리보기 → **process_outbound_safe / process_outbound** 직접 호출 | — |
| **목표** | **reserve_from_allocation** → (미리보기/확정) → **execute_reserved** 경로로 통일 | ✅ **Yes, 이게 원래 올바른 경로** |

**정리:**  
- Excel 배정표 출고는 “Allocation 파일을 읽는 기능”이므로,  
  - 파싱 결과로 `reserve_from_allocation(rows, source_file=path)` 호출하고  
  - 사용자 확인 후 `execute_reserved()` 호출하도록 변경.  
- 즉, **Allocation 다이얼로그**와 동일한 흐름(reserve → execute)으로 맞추면 됨.  
- `outbound_handlers._execute_outbound()`에서 `process_outbound` 대신  
  `reserve_from_allocation(…)` + `execute_reserved(…)` 호출하도록 수정.

---

## 4. 1단계 구현 시 체크리스트

- [ ] **마이그레이션:** allocation_plan에 `source` 컬럼 추가 (기존 행은 `'AUTO'` 또는 `'ALLOCATION'` 등으로 보정 가능하면 보정).
- [ ] **process_outbound() 내부:**  
  - reserve → execute 순차 처리 (allocation_plan 자동 기록, source='AUTO').  
  - **빠른 출고**만 PICKED에서 멈춤, 나머지 4곳은 SOLD까지 자동.
- [ ] **호출처 구분:** 빠른 출고 호출 시에만 PICKED 멈춤 플래그 전달 (예: `process_outbound(data, stop_at_picked=True)` 또는 allocation_data에 `_source_kind='QUICK'` 등).
- [ ] **_on_outbound_click / _execute_outbound:**  
  - 배정표 Excel 확인 후 `reserve_from_allocation(rows, source_file=path)` → `execute_reserved()` 로 전환.  
  - reserve 시 allocation_plan.source = `'ALLOCATION'` 등으로 기록.
- [ ] **기존 5개 호출처** 동작 확인: 간편 출고(Ctrl+O), 배정표 출고, Excel 간편, 배치 출고, 톤백수 템플릿 출고 모두 기대대로 동작하는지 테스트.

---

이 문서는 1단계 코딩 시 “Ruby 권장안”을 한곳에서 참고하기 위한 확정 요약입니다.
