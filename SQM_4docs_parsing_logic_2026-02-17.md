# 4개 서류 파싱 변수별 로직 정리 (최종본)
- 작성일시: 2026-02-17 21:57:11 (KST)
- 대상 서류: D/O, Packing List, B/L(Waybill), Invoice(FA)
- 목표: **“눈 감고도 파싱 구현 가능”** 수준으로 변수별 추출/정규화/검증/폴백 전략을 고정

---

## 0) 전체 파이프라인(표준)
아래 순서로 가면 실패율이 가장 낮습니다.

1. **문서 타입 분류**
   - 파일명 힌트 + 본문(또는 OCR 텍스트) 키워드 기반 점수화
   - DO: `D/O`, `FREE TIME`, `MRN`, `MSN`
   - PL: `PACKING LIST`, `LOT N°`, `DEL N°`, `AL N°`
   - BL: `WAYBILL`, `B/L`, `Shipped on Board`, `Freight & Charges`
   - INV: `INVOICE`, `FACTURA`, `Incoterm`, `PAYABLE AT`

2. **텍스트형 vs 스캔형 판별**
   - PDF 텍스트 추출량이 매우 적으면(거의 0에 가까우면) 스캔형으로 보고 **OCR/Vision(ROI)로 전환**

3. **문서별 파싱**
   - 텍스트형: 라벨 기반 정규식 + 테이블 행 파서(PL/BL/INV)
   - 스캔형(DO): ROI(영역) 고정 OCR(템플릿) + 정규식

4. **공통 정규화**
   - 컨테이너/Seal: 공백·하이픈 제거, 대문자화, OCR `O↔0` 보정
   - 숫자(유럽식): `5.131,250 → 5131.250`, `9.272,00 → 9272.00`
   - 날짜: `YYYY-MM-DD`, `DD.MM.YYYY`, `DD/MM/YYYY`, `영문월` 모두 표준화

5. **교차검증 & 교차보완**
   - 동일 변수(예: BL No, Vessel, Gross Weight)는 여러 문서에서 추출되므로
     - **Best Source 우선**
     - 불일치면 경고 + 하드스톱/소프트스톱 정책 선택

---

## 1) 공통 정규화 규칙(필수)

### 1.1 컨테이너 번호 정규화
- 원문 예: `FFAU535500-6`, `MRKU371493-6`
- 정규화: 하이픈/공백 제거 → `FFAU5355006`, `MRKU3714936`

**정규식**
- 컨테이너: `[A-Z]4\d7`

**규칙**
- `upper()`
- `replace('-', '')`, `re.sub(r'\s+', '', s)`

### 1.2 Seal 번호 정규화(OCR 보정 포함)
- 원문 예: `ML-CL0501799`
- 정규화: 접두 제거 + O→0 치환 → `CL0501799`

**정규식**
- Seal: `CL\d7`

**OCR 보정 규칙**
- `O → 0`, `I → 1` (필요 시)
- `CL0` 패턴이 깨지면(예: `CLO`) `CLO → CL0` 치환

### 1.3 유럽식 숫자(점/쉼표) 정규화
- `9.272,00` → `9272.00`
- `927.385,44` → `927385.44`
- `5.131,250` → `5131.250`

**규칙**
- 점 `.`과 쉼표 `,`가 함께 있으면:
  - `.`는 천단위 제거
  - `,`는 소수점으로 치환
- 쉼표만 있으면 문맥에 따라 소수점으로 치환(Invoice/PL/BL에서 대부분 유럽식)

### 1.4 날짜 정규화
지원 포맷(권장):
- `YYYY-MM-DD`
- `DD.MM.YYYY`
- `DD/MM/YYYY`
- `YYYY.MM.DD`
- `15 SEP 2025` / `SEP 15, 2025`
- `2025년 10월 17일`

---

## 2) 변수 × 서류 매트릭스 (O=추출 대상)
열: **DO / PL / BL / INV**

| 변수(필드) | DO | PL | BL | INV |
|---|:--:|:--:|:--:|:--:|
| doc_type | O | O | O | O |
| sap_no (예: 2200033057) | O |  | O | O |
| do_no | O |  |  |  |
| bl_no (예: 258468669 / MAEU…) | O |  | O | O |
| booking_no |  |  | O |  |
| invoice_no |  |  |  | O |
| invoice_date |  |  |  | O |
| folio (PL No) |  | O |  |  |
| customer_order (Your Order) |  |  |  | O |
| incoterm |  |  |  | O |
| currency |  |  | O | O |
| payment_term |  |  |  | O |
| shipper | O |  | O |  |
| consignee | O | O | O | O |
| notify_party | O |  | O |  |
| vessel | O | O | O | O |
| voyage | O | O | O |  |
| port_of_loading | O |  | O | O |
| port_of_discharge | O |  | O | O |
| final_destination | O | O | O | O |
| shipped_on_board_date |  |  | O |  |
| issue_date_waybill |  |  | O |  |
| arrival_date (입항일) | O |  |  |  |
| do_issue_date | O |  |  |  |
| free_time_date | O |  |  |  |
| warehouse_code / terminal_code | O |  |  |  |
| warehouse_name / terminal_name | O |  |  |  |
| mrn / msn | O |  |  |  |
| product_code |  | O |  | O |
| product_name / goods_desc | O | O | O | O |
| packing_spec |  | O |  | O |
| net_weight_total_kg |  | O | O | O |
| gross_weight_total_kg | O | O | O | O |
| cbm_total | O |  | O |  |
| container_list[] | O | O | O |  |
| seal_list[] | O |  | O |  |
| lot_list[] |  | O |  | O |
| lot_to_container_map |  | O |  |  |
| free_time_info[] | O |  |  |  |
| charges[] (운임/부대비) |  |  | O |  |

---

## 3) Best Source(최적 출처) 규칙
동일 변수가 여러 문서에 존재할 때, 아래 우선순위로 선택합니다.

### 3.1 문서별 강점
- **DO 1순위**: Free Time / MRN·MSN / 터미널코드 / 입항일 / D/O No / 반납지
- **PL 1순위**: LOT 원장(LOT↔컨테이너 연결) / LOT별 NET·GROSS / DEL~AL 범위 / 포장 상세
- **BL 1순위**: Vessel/Voyage / Shipped on Board / 당사자(Shipper/Notify) / 운임·부대비 / 컨테이너별 Packages·CBM
- **INV 1순위**: Invoice No/Date / Incoterm / 통화 / 결제조건 / 단가·총액 / 은행정보 / 고객발주·내부오더

### 3.2 추천 우선순위(핵심 변수)
- `invoice_no`, `invoice_date`, `unit_price`, `amount`, `incoterm`, `payment_term` → **INV**
- `lot_to_container_map`, `del_no/al_no`, `lot_net/gross` → **PL**
- `vessel`, `voyage`, `shipped_on_board_date`, `charges`, `packages_per_container` → **BL**
- `do_no`, `arrival_date`, `free_time_date`, `warehouse_code`, `mrn/msn` → **DO**
- `bl_no`, `sap_no` → **INV/DO 우선 + BL 교차확인**

---

## 4) 변수별 파싱 로직(초정밀)

아래는 각 변수에 대해 **(1) 추출 대상 라벨/패턴 (2) 정규화 (3) 검증 (4) 폴백**을 고정한 것입니다.

---

### 4.1 공통 키 변수

#### A) `sap_no` (예: 2200033057)
- **추출(1차)**: INV에서 `Our Order` 라벨 뒤 숫자
- **정규식**: `Our\s*Order\s*[:\s]*([0-9]10)`
- **정규화**: 숫자만 보관
- **검증**: 10자리인지 확인(업무 규칙으로 시작자리도 추가 가능)
- **폴백**: DO/BL에서 동일 패턴 탐색 후 최빈값 적용

#### B) `bl_no` (예: 258468669 / MAEU258468669)
- **추출(1차)**: BL에서 `B/L:` 또는 `Booking/Waybill` 블록
- **정규식(후보)**:
  - `\bB/L\s*:?\s*(\d(6,))`
  - `BL-?AWB-?CRT\s*Number\s*:?\s*(\d(6,))` (INV)
- **정규화**: `bl_no_raw`(원문) + `bl_no_norm`(공백/하이픈 제거)
- **검증**: 최소 6자리 이상 숫자
- **폴백**: INV/DO에서 추출 후 교차확인(둘 이상 일치 시 확정)

#### C) `doc_type`
- **추출**: 파일명/헤더 키워드 점수화
- **검증**: 1개 타입만 확정되면 진행
- **폴백**: 2개 이상 비슷하면 “강한 키워드” 우선(DO: MRN/MSN, PL: LOT N°, BL: WAYBILL, INV: FACTURA/INVOICE)

---

### 4.2 DO 전용(스캔형 최적)

#### D) `do_no`
- **추출**: 상단 `D/O No` 박스(ROI OCR)
- **정규식**: `D/O\s*No\.?\s*[:\s]*([0-9](6,))`
- **정규화**: 숫자만
- **검증**: 6자리 이상
- **폴백**: OCR 전체 텍스트에서 `\b\d9\b` 후보 중 상단 근처 우선

#### E) `arrival_date` (입항일)
- **추출**: `선박 입항일` / `ETA` 라벨(ROI OCR)
- **정규식 후보**:
  - `선박\s*입항일\s*[:\s]*([0-9]4[-/.][0-9](1, 2)[-/.][0-9](1, 2))`
  - `ETA\s*[:\s]*([0-9]4[-/.][0-9](1, 2)[-/.][0-9](1, 2))`
- **정규화**: date 표준화
- **검증**: 발행일(do_issue_date)보다 빠르거나 비슷한 범위인지(업무 규칙)
- **폴백**: 문서 내 날짜 후보들 중 “발행일 제외” 후 가장 그럴듯한 값 선택(소프트)

#### F) `free_time_date`
- **추출**: Free Time 표(컨테이너별 날짜) ROI OCR
- **정규화**: date 표준화
- **검증**: 컨테이너 수(5개)만큼 free_time 레코드가 존재하는지
- **폴백**: 일부만 나오면, 나온 것만 저장 + 누락 컨테이너 경고

#### G) `warehouse_code / terminal_code` (예: 06277057)
- **추출**: For Local Use 박스 ROI OCR
- **정규식**: `\b0\d7\b`
- **정규화**: 숫자만
- **검증**: 8자리 & 0으로 시작
- **폴백**: OCR 전체 텍스트에서 동일 패턴 탐색

#### H) `mrn`, `msn`
- **추출**: For Local Use 박스에서 라벨 기반(ROI OCR)
- **정규식**:
  - `MRN\s*[:\s]*([A-Z0-9-](10,))`
  - `MSN\s*[:\s]*([0-9](4,))`
- **정규화**: 공백 제거, 대문자화
- **검증**: 길이/패턴
- **폴백**: OCR 전체 텍스트

---

### 4.3 Packing List(PL) 전용(LOT 원장)

#### I) `folio`
- **추출**: 상단 `Folio`/문서번호 근처 7자리
- **정규식**: `\b\d7\b`
- **검증**: 상단 근처 첫 후보
- **폴백**: 파일명/헤더 라인에서 재탐색

#### J) `lot_to_container_map` (가장 중요)
- **추출**: PL 테이블 행 파서로 `container_no` + `lot_no`를 같은 행에서 동시 캡처
- **정규식(행 인식 핵심)**:
  - 컨테이너: `([A-Z]4\d6-?\d)`
  - LOT N°: `(112\d(7, 8))` (샘플 기준)
- **정규화**: 컨테이너번호 끊김 복원 + 대문자화
- **검증(샘플 케이스)**:
  - LOT 수 = 20
  - 컨테이너 수 = 5
  - 컨테이너당 LOT ≈ 4
- **폴백**:
  - 행이 깨지면 “컨테이너 발견 → 그 아래/옆 라인에서 LOT 4개 탐색”으로 재구성

#### K) `lots[]` (LOT 상세)
- **추출**: 각 행에서 `SQM`, `NET`, `GROSS`, `DEL~AL`, `ACC` 동시 캡처
- **정규화**:
  - NET/GROSS 유럽식 숫자 변환
  - DEL/AL은 문자열 유지
- **검증**:
  - 누적 마지막 값이 totals와 일치(허용오차 정책)
- **폴백**:
  - 누적값이 없으면 lots[] 합산으로 totals 생성

---

### 4.4 B/L(Waybill) 전용

#### L) `vessel`, `voyage`
- **추출**: 라벨 기반 텍스트 파서
- **정규식 후보**:
  - `Vessel\s*\n(.+?)\n`
  - `Voyage\s*No\.?\s*\n?\s*([A-Z0-9]+)`
- **정규화**: 공백 정리
- **검증**: 비어있지 않음
- **폴백**: INV/DO에서 보조 추출

#### M) `shipped_on_board_date`, `issue_date_waybill`
- **추출**: 라벨 기반 + 다중 패턴 폴백
- **정규식 후보**:
  - `Shipped\s*on\s*Board\s*Date.*?(\d4-\d2-\d2)`
  - `Date\s*Issue\s*of\s*Waybill.*?(\d4-\d2-\d2)`
- **정규화**: date 변환
- **검증**: ship_date <= issue_date(일반 기대)
- **폴백**: 날짜 후보군 중 라벨 근접값 우선

#### N) `containers[]` (BL 컨테이너 라인)
- **추출**: 한 줄에서 `container + seal + packages + gross + cbm` 캡처
- **정규식 예시**:
  - `([A-Z]4\d7)\s+ML-(CL\d7).*?\s(\d+)\s+Package\s+([\d.]+)\s+KGS\s+([\d.]+)\s+CBM`
- **정규화**:
  - container/seal 정규화
  - gross/cbm float 변환
- **검증**:
  - 컨테이너 5개
  - gross 합계, cbm 합계가 totals와 일치(허용오차)
- **폴백**: DO 컨테이너 목록으로 보완

#### O) `charges[]` (운임/부대비)
- **추출**: Charges 섹션에서 항목명/단가/단위/통화/합계
- **정규화**: 통화별 합계 분리(USD/KRW)
- **검증**: USD 항목 합계 = 문서 표시 합계
- **폴백**: 누락 시 “Freight Prepaid/Collect”만이라도 저장

---

## 5) 교차검증(하드스톱 추천 8개)
1) 컨테이너 수 = 5 (DO/BL/PL 교차)
2) 컨테이너 집합 동일성: DO == BL == PL(가능 범위)
3) Seal 집합 동일성: DO == BL (가능 범위)
4) CBM 합계: 20.004 × 5 = 100.020 (±0.01)
5) 중량 합계: Net=100,020 / Gross=102,625 (INV/BL/PL 교차)
6) LOT 수 = 20 (INV/PL 교차)
7) LOT↔컨테이너 맵 완전성: 20개 모두 매핑됨(PL 기준)
8) (INV) 금액 검산: qty×unit_price==amount

---

## 6) 운영 추천(효율/비용/정확도)
- 텍스트 PDF(PL/BL/INV)는 **정규식 1차 → 실패 필드만 Vision 호출**로 비용↓/속도↑
- DO는 **ROI 템플릿(json)**로 좌표를 분리하면 스캔 해상도 변화에도 강함
- 각 변수에 **confidence 점수**를 붙이면, UI에서 “확인 필요한 값”을 자동 표시 가능

---

## 7) 리오님 확인 질문(깊게 3개)
1) BL 번호 내부키는 `MAEU+번호`로 고정할까요, 아니면 숫자만 고정할까요?
2) 표준 단위는 kg(정수)로 고정하고, t(소수)는 표시용으로만 둘까요?
3) 검증 실패 시 정책은 하드스톱(All-or-Nothing)으로 고정할까요, 경고 후 진행(소프트)으로 둘까요?
