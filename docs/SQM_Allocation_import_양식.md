# Allocation import 엑셀 양식 (업로드2/템플릿 매칭)

**작성일:** 2026-02-21

---

## 요약

- **import 시 사용하는 엑셀 양식**은 **출고 Allocation Table 템플릿(다운로드)**과 동일한 컬럼을 사용합니다.
- 화주 원본 양식(1행 합계만, 2행 헤더)도 파서에서 지원합니다.

---

## 지원 컬럼 (템플릿 = 업로드2 = import 양식)

| 엑셀 헤더       | 파서 필드     | 비고 |
|-----------------|---------------|------|
| Product         | product       | |
| SAP NO          | sap_no        | |
| ETA BUSAN       | eta_busan     | |
| Date in stock   | date_in_stock | |
| QTY (MT)        | qty_mt        | |
| Lot No          | lot_no        | 8~11자리 숫자 |
| WH              | warehouse     | |
| Customs         | customs       | |
| GW              | gw            | |
| SALE REF        | sale_ref      | |

동일한 의미의 다른 표기(예: LOT NO, QTY(MT), DATE IN STOCK 등)도 alias로 인식됩니다.

---

## 지원 파일 구조

- **1행**: 타이틀 (Allocation - 고객 - 기간 / 목적지 - 수량MT of 제품)
- **2행**: 무시 (합계 QTY 등, 파서에서 헤더로 사용하지 않음)
- **3행**: 헤더 열 (Product, SAP NO, ETA BUSAN, Date in stock, QTY (MT), Lot No, WH, Customs, GW, SALE REF)
- **4행~**: 데이터

| 구분        | 1행        | 2행   | 3행   | 4행~   |
|-------------|------------|-------|-------|--------|
| **화주 원본** | 합계(숫자만) | (없음) | 헤더  | 데이터 |
| **템플릿**   | 타이틀     | 무시  | 헤더  | 데이터 |

둘 다 `parsers/allocation_parser.py`에서 자동 감지합니다.

---

**(주) 지와이로지스 2026-02-21**
