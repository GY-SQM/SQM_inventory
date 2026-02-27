# SQM v6.0 설계 확정 요약

**기준일:** 2026-02-20 (루비안 확정)

---

## 1. UI 확정

| 항목 | 확정 내용 |
|------|-----------|
| **대시보드** | 4단계 카드(AVAILABLE·RESERVED·PICKED·SOLD) → **기존 대시보드 상단에 추가** |
| **미처리(PENDING)** | **재고 탭에 "PENDING만 보기" 필터 버튼** 추가 (별도 탭 없음) |
| **메뉴** | **Picking List 업로드**, **Sales Order 업로드** → **출고 계열 아래** (Picking List → 출고 아래, Sales Order → 출고 맨 아래) |

---

## 2. Picking List PDF 파서 확정

- **정규식 기반** (Gemini OCR 보조)
- **Batch number = lot_no**
- **5MT = 일반 톤백, 1KG = 샘플** 자동 구분 (`unit == "KG"` and `qty <= 1.0` → `is_sample=True`)
- **customer_ref = Picking No** (picking_table 매칭용)
- **sales_order = sale_ref** (sold_table 연결)

### 톤백 라인 패턴

```
Quantity: 5.00 MT  Batch number: 1125070606  Storage location: 1001 GY logistics  → 일반 (qty_kg=5000, is_sample=0)
Quantity: 1.00 KG  Batch number: 1125070606  Storage location: 1001 GY logistics  → 샘플 (qty_kg=1, is_sample=1)
```

### Material 구분

- **30000008** → 일반 톤백 섹션 (5MT)
- **30000026** → 샘플 톤백 섹션 (1KG)

---

## 3. Sales Order Excel 구조 (실제 파일 기준)

**파일 예:** `Sales order No (26.02.09)-3266.xlsx`  
**시트:** `Sales order No`

### 헤더 (Row 5)

| 컬럼 | 설계 매핑 | 비고 |
|------|------------|------|
| Destination | 고객/출고처 | |
| Delibery Date | 출고일 | |
| LOT NO | lot_no | picking_table·sold 매칭 |
| SAP NO | sap_no | |
| BL NO | bl_no | **sold_table에만 저장** (inventory 덮어쓰지 않음) |
| Sales order No | sale_ref | |
| Picking No | picking_list_no / customer_ref | **LOT NO + Picking No 둘 다 일치**로 매칭 |
| SKU | product | |
| NW | net weight (kg) | CT/PLT 없을 때 톤백 개수 역산: NW÷500 |
| GW | gross weight | |
| CT/PLT | **톤백 개수** | **우선 사용**, 없으면 NW÷500 역산 |

### 처리 규칙 (확정)

- **LOT NO + Picking No** 둘 다 일치해야 picking_table 매칭 (동일 LOT 다른 Picking 중복 방지)
- **CT/PLT 우선**, 없으면 **NW÷500** 역산
- **BL NO** → sold_table에만 저장
- 미처리 → **PENDING** 보관, 재고 탭 필터로 관리

---

## 4. DB 구조 (B안 확정)

- allocation_plan 확장
- **picking_table** 신규 (RESERVED→PICKED 이력, picking_list_no, sale_ref 등)
- **sold_table** 신규 (PENDING/SOLD/RETURNED, bl_no, sale_ref 등)

---

## 5. 상태 표시명 통일 (적용 완료)

- AVAILABLE → **판매가능**
- RESERVED → **판매배정**
- PICKED → **판매화물 결정**
- SOLD → **출고**

---

*문서 버전: 1.0 | SQM v6.0*
