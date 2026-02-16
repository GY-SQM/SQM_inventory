# SQM v5.6.3 — 톤백리스트 정합성 수정 (GitHub 메모)

## 개요
톤백 리스트에서 MXBG 제거 및 NET/Balance/Inbound 무게를 **톤백 개별 무게** 기준으로 통일하여, 재고 리스트(LOT)와 톤백 리스트 간 **정합성**을 맞춘 버전입니다.

---

## 주요 수정 사항

### 1. 톤백 리스트 UI (tonbag_tab.py)
- **MXBG 컬럼 삭제**  
  - LOT 단위 정보(MXBG)는 톤백 리스트에서 제거 (재고 리스트에만 유지)  
  - 컬럼 수: 21열 → 20열
- **NET(Kg)**  
  - 기존: LOT 총무게(5,001kg)가 모든 행에 표시되던 버그  
  - 수정: 톤백 개별 무게 사용 (샘플 1kg, 일반 톤백 500kg)
- **Balance(Kg)**  
  - 톤백 개별 잔량 (출고된 톤백은 0)
- **Inbound(Kg)**  
  - 톤백 개별 입고 무게 (NET과 동일 로직)

### 2. 입고 시 톤백 무게 계산 (inbound_mixin.py)
- **per_bag 계산식 수정**  
  - 기존: `total_w / bag_count` → 샘플 1kg 포함 시 500.1kg 등 오차  
  - 수정: `(total_w - 1.0) / bag_count` (샘플 1kg 차감 후 톤백 수로 나눔)  
  - 결과: 일반 톤백 500kg × 10개 + 샘플 1kg = 5,001kg (LOT NET과 일치)

### 3. 톤백 조회 쿼리 보강 (query_mixin.py)
- **get_tonbags_with_inventory**  
  - `tonbag_weight` (기존): 톤백 개별 무게  
  - **추가** `tonbag_initial_weight`: 톤백 입고 무게 (= t.weight)  
  - **추가** `tonbag_current_weight`: 톤백 잔량 (출고 상태면 0, 아니면 t.weight)  
  - 톤백 탭/Excel에서 위 필드 우선 사용 가능

### 4. 톤백 리스트 Excel 내보내기 (export_mixin.py)
- **MXBG 컬럼 제거** (화면과 동일 20열)
- **NET(Kg), Balance(Kg), Inbound(Kg)**  
  - 모두 톤백 개별 무게(tonbag_weight) 기반으로 계산  
  - Balance: 출고 상태(PICKED/SOLD 등)면 0

### 5. 톤백 탭 동작 보정 (tonbag_tab.py)
- **일괄 출고 / 출고 취소**  
  - MXBG 제거로 컬럼 인덱스 변경에 따라, TONBAG NO를 **index 2**에서 읽도록 수정  
  - 샘플 표기 "S00" → 숫자 0으로 변환 후 엔진 전달

---

## 정합성 검증 (대원칙)

| 구분 | NET(Kg) | Balance(Kg) | Inbound(Kg) |
|------|---------|-------------|-------------|
| **재고 리스트 (LOT)** | 5,001 (LOT 총무게) | 5,001 (LOT 잔량) | 5,001 (LOT 입고량) |
| **톤백 리스트 (행별)** | 샘플 1 / 톤백 500 | 개별 잔량 (출고 시 0) | 샘플 1 / 톤백 500 |
| **톤백 리스트 합계** | 5,001 | 5,001 | 5,001 |

- 톤백 리스트 합계 = 재고 리스트 NET(Kg) 와 일치하도록 통일됨.

---

## 변경된 파일 (요약)

| 파일 | 변경 내용 |
|------|-----------|
| `engine_modules/inventory_modular/inbound_mixin.py` | per_bag 샘플 1kg 차감 (기존 반영 확인) |
| `engine_modules/inventory_modular/query_mixin.py` | tonbag_initial_weight, tonbag_current_weight 추가 |
| `engine_modules/inventory_modular/export_mixin.py` | 톤백 Excel: MXBG 제거, 개별 무게 로직 |
| `gui_app_modular/tabs/tonbag_tab.py` | MXBG 제거, NET/Balance/Inbound 개별 무게, TONBAG NO 인덱스 수정 |

---

*작성일: 2026-02-16 | SQM v5.6.3 톤백 정합성*
