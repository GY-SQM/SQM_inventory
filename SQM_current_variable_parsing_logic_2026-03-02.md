# SQM 현재 적용(루비안 기준) 변수별 파싱 로직 상세 정리
- 질문/요청 시각: 2026-03-02 21:48:12 (KST)
- 작성 시각: 2026-03-02 21:48:12 (KST)
- 대상 문서(이번 세션 기준): **D/O, Packing List, B/L(Sea Waybill), Invoice(FA), Picking List**
- 핵심 원칙:
  - **위치 고정**: ROI(비율 좌표) 기반 추출이 1차
  - **형식 가변**(BL No 등): 정규식 하나로 고정하지 않고 **라벨 게이팅 + 후보 점수화 + 하드스톱**
  - **스캔/텍스트 혼재**: Text-layer 우선 → ROI OCR → Anchor OCR(라벨로 자동 보정)
  - **조용한 실패 금지**: 무결성 위반/미검출은 **하드스톱 + debug 자동저장**

> 주의(정확성 선언)  
> 이 문서는 “SQM에 **현재 적용하도록 설계된(루비안)** 표준 로직”을 변수별로 풀어서 정리한 것입니다.  
> (실제 프로젝트 코드의 함수명/파일명은 버전별로 다를 수 있어 **역할(진입점/파서/검증/팝업)** 기준으로 설명합니다.)

---

## 0) 공통 파이프라인(모든 변수 공통)
1) **문서 타입 판별**(파일명+헤더 키워드 점수)  
2) **텍스트형 vs 스캔형 판별**  
   - `get_text()` 길이 < 임계치(예: 300) → 스캔형으로 판단  
3) **1차 추출: Text-layer 라벨 파싱**(가능한 경우)  
4) **2차 추출: 고정 ROI OCR**(비율 좌표)  
5) **3차 추출: Anchor OCR**(라벨 토큰 위치로 ROI 자동 보정 후 재시도)  
6) **정규화(표준화)**: 날짜/숫자/코드/공백/하이픈/대소문자  
7) **교차검증(무결성)**: 문서 간 합의(일치) / 불일치 하드스톱  
8) **Debug 자동저장**: 실패 원인 재현 가능하게 증거 저장

---

## 1) 변수 목록(스키마) — 무엇을 “변수”로 본다
아래는 이번 5종 서류를 한 번에 통합하기 위한 canonical schema(권장)입니다.

### 1.1 식별(Identifiers)
- `bl_no_raw` (원문 그대로)
- `do_no`
- `invoice_no`, `invoice_date`
- `our_order_sap` (예: 2200…)
- `customer_order` (예: 4500…)
- `folio` (PL 번호)
- `picking_sales_order`, `picking_requisition`, `customer_reference`

### 1.2 당사자(Parties)
- `shipper_name`, `consignee_name`, `notify_party_name`
- (선택) `consignee_email`, `tax_id`

### 1.3 항차/항만(Routing)
- `vessel`, `voyage`
- `pol_name`, `pod_name`
- (코드형) `pol_code`, `pod_code`, `final_destination_code`

### 1.4 컨테이너/Seal/장비(Equipment)
- `container_list[]` (정규화된 컨테이너번호)
- `seal_list[]` (정규화된 seal: CL\d{7})
- `equip_type[]` (45G1 / 40 DRY 9'6 등)

### 1.5 중량/부피/포장(Weights/Volume/Packing)
- `net_kg`, `gross_kg`, `cbm_total`
- `packages_total`, `packages_per_container`
- `maxibag_count`, `pallet_count`, `plastic_jar_count`

### 1.6 LOT/Batch 원장(Lots/Batches)
- `lots[]`(Invoice의 “존재 확인용”)
- `pl_lots[]`(Packing List 원장)
- `lot_to_container_map`(PL 전용, 핵심)
- `picking_batches_main[]`, `picking_batches_sample[]`

### 1.7 DO 전용(Local Use / FreeTime)
- `arrival_date`, `do_issue_date`
- `free_time_map[container] = date`
- `return_depot_code`
- `terminal_code`, `terminal_name`
- `mrn`, `msn`

### 1.8 운임/금융(Financial)
- `charges[]`(BL)
- (Invoice) `unit_price`, `amount_total`, `currency`, `incoterm`, `payment_term`

---

## 2) 변수별 우선순위(1/2/3순위)
> 우선순위 원칙:  
> **라벨이 명확 + 텍스트 레이어 안정** > **고정 ROI OCR 안정** > **복잡한 페이지(오탐 위험)**

| 변수 | 1순위 | 2순위 | 3순위 | 비고(정책) |
|---|---|---|---|---|
| bl_no_raw | Invoice(FA) | D/O | B/L(첫 페이지) | **원문 그대로 저장**, 불일치 하드스톱 |
| do_no | D/O | - | - | DO 전용 |
| invoice_no / invoice_date | Invoice(FA) | - | - | INV 전용 |
| our_order_sap | Invoice(FA) | B/L(참조) | - | 숫자 10자리 |
| vessel / voyage | B/L | D/O | PL/INV | 교차검증 |
| pol/pod | B/L | INV | DO(코드) | DO는 코드 매핑 필요 |
| container_list | B/L(컨테이너 라인) | D/O | PL | “집합 동일성” 검증 |
| seal_list | B/L | D/O | - | ML- 접두 정규화 후 비교 |
| net_kg | Invoice(FA) | PL | B/L | kg 표준 |
| gross_kg | PL | B/L | INV | DO는 현장확인용 |
| cbm_total | B/L | D/O | - | ±0.01 허용 |
| lot_to_container_map | Packing List | - | - | PL 전용 원장(하드스톱) |
| free_time_map | D/O | - | - | DO 전용(하드스톱) |
| charges[] | B/L | - | - | BL 전용 |
| picking_batches | Picking List | - | - | 피킹 원장 |

---

## 3) 변수별 파싱 로직(상세)
아래는 “어떤 방식으로 읽고, 어떻게 실패를 막는지”를 변수 단위로 정리합니다.

---

# A. bl_no_raw (가변 포맷, 위치 고정) — 오탐 0에 가깝게
## A1) 절대 금지 규칙(오탐 방지 핵심)
- `\d+`로 **숫자만** 뽑아 BL로 확정하지 않는다.  
  → `MEDUFP963988`이 `963988`로 잘리는 사고 방지
- 문서 **전체 페이지**에서 무차별 검색하지 않는다.  
  → Rider page/약관 페이지의 컨테이너/페이지번호 오탐 방지
- **1페이지 상단**만 처리(우상단 고정 위치 조건 최대 활용)

## A2) 추출 알고리즘(3중 방어)
1) **Text-layer + 라벨 근처 탐색(1순위)**  
   - INV: `BL-AWB-CRT Number` 오른쪽/아래 “200자 윈도우”에서 후보 추출  
   - BL: `SEA WAYBILL No.` 오른쪽/아래 “200자 윈도우”에서 후보 추출
2) 실패 또는 스캔형 → **고정 ROI OCR(2순위)**  
   - ROI#1(헤더, 라벨 포함) : 앵커 찾기용  
   - ROI#2(번호만) : `No.` 토큰 오른쪽을 재크롭(라벨 제외)
   - OCR: `psm=7` + whitelist `A-Z0-9-`
3) ROI 흔들림(1~3%) → **Anchor OCR(3순위)**  
   - 헤더 ROI에서 `SEA`, `WAYBILL`, `NO` 토큰 bbox를 찾고 우측을 다시 크롭

## A3) 후보 생성/점수화(포맷 변화 대응)
- 후보 패턴은 넓게:
  - `\b[A-Z]{2,12}[A-Z0-9\-]{4,24}\b`
- 후보 점수:
  - 길이 8~16 가점, 너무 짧은 숫자 단독(<=7)은 강한 감점
  - 라벨 오른쪽/우상단에 가까울수록 가점(거리)
  - 컨테이너 패턴(`^[A-Z]{4}\d{7}$`)이면 즉시 폐기
- 최종: 점수 1등 1개를 **원문 그대로(raw)** 확정

## A4) 하드스톱/디버그
- 후보 점수가 임계값 미만이면 하드스톱
- debug 저장:
  - `page0.png`, `header_roi.png`, `code_roi.png`
  - `roi_ocr.txt`, `anchor_ocr.txt`, `candidates.json`, `meta.json`

## A5) 숫자-only 오탐 차단(필수 정책)
- BL 후보는 반드시 **영문 1개 이상 + 숫자 1개 이상** 포함해야 한다.
- 아래 패턴은 BL 후보에서 기본 제외:
  - 컨테이너: `^[A-Z]{4}\d{7}$`
  - SAP류(오탐): `^22\d{8}$`
  - 단순 숫자열: `^\d{6,}$` (6/9자리 오탐 다수 구간)
- `Booking No`, 페이지 번호, 금액 칼럼 숫자는 BL 후보로 승격하지 않는다.

### A5-1) 구현 예시(Python)
```python
import re

CONTAINER_RE = re.compile(r"^[A-Z]{4}\d{7}$")
SAP_RE = re.compile(r"^22\d{8}$")
NUMERIC_ONLY_RE = re.compile(r"^\d{6,}$")

def normalize_bl(token: str) -> str:
    return re.sub(r"[^A-Z0-9]", "", (token or "").upper())

def is_valid_bl_candidate(token: str) -> bool:
    t = normalize_bl(token)
    if len(t) < 8:
        return False
    if CONTAINER_RE.match(t):
        return False
    if SAP_RE.match(t):
        return False
    if NUMERIC_ONLY_RE.match(t):
        return False
    if not re.search(r"[A-Z]", t):
        return False
    if not re.search(r"\d", t):
        return False
    return True
```

## A6) 테스트 케이스(운영 검증용)
- 통과(정상 BL):
  - `MEDUFP963996`
  - `OOLU3A123456`
  - `MSCU-AB1234567` (정규화 후 평가)
- 차단(오탐):
  - `963988` (숫자-only)
  - `258468669` (숫자-only 9자리)
  - `TCLU1234567` (컨테이너 번호)
  - `2200123456` (SAP형 숫자)

---

# B. do_no (D/O No) — 고정 ROI OCR
## B1) 추출
- 스캔형 비중이 높으므로 **고정 ROI OCR**이 1순위
- OCR: psm=7(한 줄), whitelist 숫자
- 정규식: `D/O\s*No\.?\s*[:\s]*([0-9]{6,})`

## B2) 정규화/검증
- 숫자만 저장, 길이 6 이상
- 실패 시 하드스톱(입고/출고 흐름 키)

---

# C. free_time_map (D/O Free Time) — “컨테이너 마스터 + 날짜 강추출”
## C1) 실패가 잦은 이유
- 표 형태 + OCR 오탈자(컨테이너가 A/4, O/0로 깨짐)
- 날짜는 잘 읽히는데 “컨테이너 매칭”이 깨져 전체 실패로 이어짐

## C2) 최고 안정 전략
1) **컨테이너 마스터**를 먼저 추출(좌측 컨테이너 표 ROI)  
2) FreeTime 표 ROI에서 **날짜만** 강하게 추출  
3) 매칭:
   - 정확 매칭 → 퍼지 매칭 → (최후) 날짜가 모두 동일하면 모드 날짜로 보정  
   - 단, 모드 보정은 `errors[]`에 “추정” 기록

## C3) 날짜 패턴
- `(\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\d{1,2}[-/.]\d{1,2}[-/.]\d{4})`

## C4) 하드스톱
- 컨테이너 5대 중 FreeTime이 0개면 하드스톱(운영상 치명)
- debug: `free_table_roi.png`, `free_rows_ocr.txt`, `mapping.json`

---

# D. container_list / seal_list — 문서 간 “집합 동일성”이 핵심
## D1) 추출
- B/L: 컨테이너 라인(표)에서 1순위
- D/O: 컨테이너 표에서 2순위
- PL: 보조(하이픈 포함 가능)

## D2) 정규화
- 컨테이너: 공백/하이픈 제거, 대문자, 정규식 `[A-Z]{4}\d{7}`
- Seal: `ML-` 제거 후 `CL\d{7}`만 저장, OCR에서 `O→0`

## D3) 검증(하드스톱/경고)
- `set(BL.containers) == set(DO.containers)` 아니면 경고 또는 하드스톱(정책)
- Seal도 동일 방식(접두 제거 후 비교)

---

# E. weights/net/gross/cbm — 합계는 “교차검증”으로 확정
## E1) 추출 우선순위
- net_kg: INV → PL → BL
- gross_kg: PL → BL → INV
- cbm_total: BL → DO

## E2) 정규화(유럽식 포함)
- `102.625,000` 같은 표기 대응:
  - 점/쉼표 둘 다 있으면 `.` 제거 + `,`를 소수점으로
- 내부 표준: kg 정수(100020, 102625)

## E3) 검증(하드스톱)
- net/gross가 문서 간 불일치면 하드스톱
- cbm 합계 오차는 ±0.01 허용(그 이상은 경고/하드스톱)

---

# F. lot_to_container_map / pl_lots (Packing List 원장) — “상태머신 행 파서”
## F1) 왜 상태머신이 필요한가
- PDF 표는 줄바꿈이 깨져서 “행이 찢어짐”
- 고정 헤더보다 “컨테이너 패턴”을 행 시작 신호로 쓰는 것이 안정적

## F2) 알고리즘
1) 컨테이너 패턴 발견 → 현재 컨테이너 컨텍스트 설정
2) 같은/인접 줄에서 LOT N°, DEL/AL, SQM, NET/GROSS 캡처
3) 누적(ACCUMULATED)은 검증용(없으면 합산)

## F3) 하드스톱
- LOT 개수/컨테이너당 LOT 규칙이 깨지면 하드스톱
- lot_to_container_map은 PL이 유일한 원장

---

# G. invoice 금액/단가/수량 — “유럽식 정규화 + 검산”
## G1) 추출
- 라벨 기반(텍스트형이면 1순위)
- 스캔형이면 ROI OCR

## G2) 정규화
- `9.272,00 → 9272.00`, `927.385,44 → 927385.44`

## G3) 하드스톱 검증
- `qty * unit_price == amount_total` (허용오차 매우 작게)

---

# H. Picking List — “라벨-라인 상태머신 + 배치 합 검증”
## H1) 추출
- Header: customer ref / requisition / sales order / creation date / ports / container plan
- Item block: 자재코드(8자리) 라인으로 시작
- Batch line: `Quantity: ... Batch number: ... Storage location: ...`
- Summary: net/gross/bag/pallet

## H2) 하드스톱
- 본품 배치 합 == 본품 총량(MT)
- 샘플 배치 합 == 샘플 총량(KG)
- 포장요약(500kg×600=300,000kg 등) 일치

---

## 4) 공통 무결성(하드스톱) 규칙 10개(운영 기본)
1) BL No 미검출 = 하드스톱 + debug 저장  
2) INV/DO/BL BL No 불일치 = 하드스톱  
3) 컨테이너 집합(BL vs DO) 불일치 = 경고/하드스톱(정책)  
4) Seal 집합(BL vs DO) 불일치 = 경고(정규화 후)  
5) Gross(PL/BL/INV) 불일치 = 하드스톱  
6) Net(INV/PL/BL) 불일치 = 하드스톱  
7) CBM 합계 오차 초과 = 경고/하드스톱  
8) PL LOT 원장 불완전 = 하드스톱  
9) INV 금액 검산 실패 = 하드스톱  
10) Picking 배치 합 불일치 = 하드스톱

---

## 5) 운영 개선(루비 제안)
- 변수마다 `source`, `method`, `roi_id`, `confidence`를 함께 저장  
  예) `bl_no_raw="MEDUFP963996", source="BL", method="ANCHOR_OCR", roi_id="bl_topright_v1", confidence=0.91`  
- 실패 시 자동 저장되는 debug를 “팝업에서 바로 열기”로 연결(조치시간 단축)

