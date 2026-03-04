# SQM 출고 로직 변경: 스캔 파일 도입에 따른 설계

## 1. 현실 전제 (요약)

- **스캔 파일 오기 전**: 어느 **롯트에서 몇 톤/몇 개** 나가는지만 알 수 있음. **어느 톤백이 나갈지는 특정 불가.**
- **스캔 파일 도착 후**: 현장 직원이 바코드 스캔한 **톤백·로케이션 매칭 파일**이 들어와야 비로소 **어떤 톤백이 어디서 나갔는지** 확정 가능.
- 따라서 **Reserved / Picked 단계에서는 “특정 톤백 지정”을 하지 않고**, **롯트·수량 단위로만** 예약/픽을 관리하다가, **스캔 파일 수신 시점에 톤백·로케이션을 확정**하는 구조로 바꿔야 함.

---

## 2. 현재 로직 (FIFO 방식) — 변경 대상

| 단계 | 현재 동작 | 문제 |
|------|-----------|------|
| **예약(Reserve)** | 해당 롯트에서 AVAILABLE 톤백을 `sub_lt DESC`로 골라 **특정 톤백을 RESERVED**로 지정하고, `allocation_plan`에 **tonbag_id** 저장. | 현장에서 아직 어떤 톤백 나갈지 모르는데, 프로그램이 미리 “이 톤백들 나간다”고 고정해 버림. |
| **픽(Execute)** | `allocation_plan`의 **tonbag_id** 기준으로 해당 톤백을 PICKED로 전환하고, `picking_table`에 **tonbag_id** 기록. | 위와 동일 — 스캔 전에 특정 톤백을 “나감”으로 확정하는 것은 현실과 불일치. |
| **확정(Confirm)** | PICKED 톤백을 SOLD로 전환, `sold_table`에 **tonbag_id** 기록. | 스캔 파일 없이도 “어느 톤백이 나갔는지” 시스템이 정해 버림. |

즉, **지금은 “예약 시점에 FIFO로 톤백을 정해 두고, 그걸 출고·확정까지 이어가는 구조”**라서, **“스캔 전에는 개수/중량만 알고, 스캔 후에 톤백·로케이션 확정”**이라는 요구와 맞지 않음.

---

## 3. 목표 로직 (스캔 기반 확정)

- **예약(Reserve)**  
  - **롯트 + 수량(MT/개)** 만 기록.  
  - **특정 톤백(tonbag_id) 지정 없음.**  
  - 필요 시 롯트 단위 “예약 수량”만 관리 (예: `inventory.reserved_weight_kg` 또는 allocation_plan만으로 집계).

- **픽(Execute)**  
  - “이 출고 건에 대해 이 롯트에서 이만큼 픽했다”는 **수량/건수만** 기록.  
  - **어느 톤백이 나갔는지는 여전히 모름** → `picking_table`은 **tonbag_id NULL 허용** (롯트·sale_ref·picked_qty_kg만 저장).

- **스캔 파일 수신**  
  - 현장에서 올라온 **스캔 파일**(바코드 → 톤백 식별, 로케이션)을 업로드.  
  - 시스템이 **미확정 출고 건(롯트·sale_ref·수량)** 과 매칭하여,  
    “이 톤백들이 이 출고 건으로 나갔다”고 **그 시점에 확정**.  
  - 이때 **톤백 상태(PICKED/SOLD)·로케이션·picking_table/sold_table의 tonbag_id** 를 채움.

- **확정(Confirm)**  
  - 옵션 A: 스캔 파일이 “출고 확정 + 로케이션” 역할을 하므로, **스캔 수신 = 확정**으로 간주할 수 있음.  
  - 옵션 B: 스캔 없이 “수량만 확정”하는 버튼은 유지하되, **톤백·로케이션은 스캔 파일 올 때만 채움.**

---

## 4. 데이터 구조 제안

### 4.1 allocation_plan (예약 계획)

- **역할**: “이 롯트에서 이 고객/ sale_ref 로 이만큼(MT/개) 나갈 예정”만 저장. **톤백 지정 없음.**
- **변경**:
  - `tonbag_id`, `sub_lt`는 **NULL 허용** (이미 스키마상 nullable 가능).
  - 예약 시 **INSERT만** 하고, `inventory_tonbag`는 건드리지 않음 (RESERVED로 찍지 않음).
  - 필요 시 `qty_kg` 또는 `tonbag_count` 컬럼으로 “몇 톤/몇 개” 예약인지 명확히.

### 4.2 롯트 단위 “예약 수량” (가용량 계산용)

- **목적**: “이 롯트에서 이미 예약된 수량”만 알면, **가용 수량 = current_weight − reserved_weight_kg** 로 계산 가능.
- **방법**:
  - **A안**: `inventory` 테이블에 `reserved_weight_kg` 컬럼 추가. 예약 시 +, 취소/스캔 반영 시 −.
  - **B안**: `allocation_plan`에서 `status='RESERVED'`인 행만 SUM해서 reserved_weight_kg 계산 (컬럼 없이 뷰/쿼리로 처리).

### 4.3 picking_table (픽 이력)

- **역할**: “어느 출고 건(롯트·sale_ref)에서 몇 톤 픽했는지” 기록. 스캔 전에는 **톤백 미지정**.
- **변경**:
  - `tonbag_id` **NULL 허용** (스캔 전에는 NULL, 스캔 후 매칭 시 채움).
  - 스캔 전: (lot_no, sale_ref, picked_qty_kg, picking_date, reservation_id 등) 만 저장.
  - 스캔 후: 같은 출고 건에 대해 (tonbag_id, location 등) 업데이트 또는 별도 “스캔 매칭” 행 추가.

### 4.4 sold_table (출고 확정 이력)

- **역할**: 실제 나간 톤백·로케이션은 **스캔 파일 반영 후** 기록.
- **변경**:
  - `tonbag_id` NULL 허용 또는, 스캔 전에는 sold_table에 넣지 않고 **스캔 수신 시점에만 INSERT**하는 방식 선택 가능.
  - `scan_file`, `scan_code`, `location` 등은 스캔 파일에서 채움.

### 4.5 inventory_tonbag

- **예약/픽 단계**: 개별 톤백 상태를 RESERVED/PICKED로 **먼저 바꾸지 않음** (또는 “소프트 예약”만 표시할지 정책 결정).
- **스캔 반영 시**: 스캔에 포함된 톤백만 PICKED → SOLD, `location` 등 갱신.

### 4.6 UI 원칙: Reserved/Picked 톤백 리스트

- **이론적으로**: 스캔 전에는 “어느 톤백이 reserved/picked인지”를 모르므로, **reserved/picked 상태의 톤백 리스트**는 **available 톤백 리스트와 동일하게 보이거나, 아예 표시하지 않아야 함.**
- **적용**:
  - 예약·픽 단계에서 `inventory_tonbag`의 `status`를 RESERVED/PICKED로 바꾸지 않으면, 화면에서 조회하는 “톤백 리스트”는 당연히 **available과 동일** (같은 롯트 내 톤백이 모두 AVAILABLE로 보임).
  - 또는 reserved/picked 구간에서는 **톤백 단위 리스트를 숨기고**, “이 롯트 예약 N MT / 픽 N MT”처럼 **수량만 표시**하는 방식도 가능.
- **정리**: reserved·picked 단계에서 “이 톤백들이 예약됐다/픽됐다”는 **개별 톤백 리스트를 노출하면 안 됨** (available과 동일하거나 미표시).

---

## 5. 흐름 요약

1. **Allocation 예약**  
   → allocation_plan에 (lot_no, customer, sale_ref, qty_mt, …), **tonbag_id=NULL**.  
   → (선택) inventory.reserved_weight_kg 증가 또는 allocation_plan SUM으로 “예약 수량” 관리.

2. **출고 실행(픽)**  
   → “이 예약 건을 오늘 픽했다”는 의미로 picking_table에 (lot_no, sale_ref, picked_qty_kg, …), **tonbag_id=NULL**.  
   → allocation_plan 상태만 EXECUTED로 변경. inventory_tonbag는 그대로(또는 정책에 따라 “픽 예정” 표시만).

3. **스캔 파일 업로드**  
   → 파일에 (바코드/tonbag_uid, 로케이션 등) 존재.  
   → 미확정 픽 건(또는 sale_ref/날짜 기준)과 매칭.  
   → 매칭된 톤백에 대해: inventory_tonbag 상태·로케이션 갱신, picking_table/sold_table에 **tonbag_id·location** 기록.

4. **확정**  
   → 스캔이 확정을 대체하거나, 스캔 없이 “수량만 확정” 후 나중에 스캔으로 톤백·로케이션 보정.

---

## 6. FIFO 제거

- **기존**: 예약 시 AVAILABLE 톤백을 `sub_lt DESC` 등으로 골라 **그 톤백들을 RESERVED로 고정**.
- **변경**: 예약 시 **어떤 톤백도 고르지 않음**. 롯트별 예약 수량만 누적.  
  실제 “어느 톤백이 나갔는지”는 **스캔 파일이 들어온 뒤** 매칭 결과로만 확정.

---

## 7. 구현 시 유의사항

- 기존 **allocation_plan에 tonbag_id가 이미 있는 데이터**와의 호환:  
  “기존 예약은 그대로 두고, 신규 예약부터 tonbag_id=NULL” 또는 마이그레이션으로 기존 행 정리.
- **출고 예정/가용량** 집계: reserved는 “allocation_plan RESERVED SUM” 또는 `inventory.reserved_weight_kg` 기준으로 변경.
- **스캔 파일 포맷** 정의 필요: 컬럼(바코드, tonbag_uid, location, sale_ref 등), 인코딩, 필수값.
- **매칭 규칙**: sale_ref·롯트·날짜 등으로 “이 스캔 row는 이 picking/sold 건에 붙인다” 규칙 명확히.

---

*문서 버전: 1.0 | 스캔 기반 출고 확정 로직 설계*
