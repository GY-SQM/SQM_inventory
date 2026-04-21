# Track B: BL↔DO 감사 + carrier_profile 플러그인 설계

> SQM v8.7.0 · v864_1 (golden master) 기준
> 작성 일자: 2026-04-18
> 작성자: Ruby (Opus 4.7 · 1M) — kidong.nam@gmail.com
> 범위: 현행 코드 읽기 전용 감사 + 비침습적 플러그인 POC 설계
> 제약: 기존 동작 불변, POC 코드(Part 3)만 실제 삽입 가능

---

## 요약 (Executive Summary)

**Part 1(감사)** 결과, "선사가 바뀌면 BL/DO 매핑도 바뀐다"는 조건은 현행 코드에서 **7개 지점의 독립 분기**로 구현되어 있다. 단일한 분기점이 아니라 ①수동 선택 주입(`parser._last_carrier_id`) ②파일명 접두사 ③1페이지 텍스트 키워드 점수 ④좌표 테이블 lookup ⑤Gemini 프롬프트 힌트 ⑥carrier_bl_rule DB 규칙 ⑦`_carrier_name_map` 표기 변환이 **각자 다른 파일/다른 상수**에서 선사 집합을 재정의하고 있다. v8.7.0 패치(`_last_carrier_id` 강제 주입 + `db_carrier_id` 전달)는 ①과 ⑤의 정합성은 맞췄으나, ②③④⑥⑦은 여전히 독립적이다.

**Part 2(설계)** 는 이 7개 지점을 "단일 선사 프로파일(YAML)"로 집약하는 레이어를 추가 제안한다. 핵심 원칙은 "교체 아닌 추가"로, 기존 Python 모듈을 건드리지 않고 `CarrierProfileLoader`가 YAML → 기존 dict/list에 주입하는 방식이다.

**Part 3(POC)** 는 50줄 미만의 `carrier_profile_loader.py` 뼈대, `bl_carrier_registry.py`용 최소 diff, ZIM 선사 YAML 예제를 제공한다.

---

## Part 1: 현행 감사

### 1-1. 선사 전환 분기 맵

BL/DO 파싱 파이프라인에서 선사가 "분기 변수"로 작동하는 지점은 아래 7곳이다. 각 지점은 독립적으로 선사 집합을 재정의한다.

| # | 분기 지점 (file:line) | 분기 기준 | 선사 집합 | 비고 |
|---|---|---|---|---|
| ① | `gui_app_modular/dialogs/onestop_inbound.py:2031-2039` | 사용자 UI 선택(`tpl_carrier_id`) | `CARRIER_OPTIONS` 12개 | v8.7.0 [FIX]: `parser._last_carrier_id` 강제 주입 |
| ② | `parsers/document_parser_modular/do_mixin.py:634-641` | 파일명 접두사 (`MEDU`, `MAEU` 등) | MSC, MAERSK 2개만 | 하드코딩 튜플 `_MSC_PREFIX`, `_MRK_PREFIX` |
| ③ | `parsers/document_parser_modular/bl_mixin.py:286-335` | 1페이지 텍스트 키워드 스코어링 | MAERSK, MSC 2개만 | `_detect_carrier_from_words` (가중치 2~4점) |
| ④ | `parsers/document_parser_modular/bl_mixin.py:80-112` + `do_mixin.py:37~200` | 좌표 테이블 lookup | MAERSK, MSC 2개만 | `CARRIER_COORD_TABLE` 클래스 상수 |
| ⑤ | `features/parsers/onestop_inbound_candidate_patch.py:149-154` | `db_carrier_id` 우선 병합 | 없음(passthrough) | v8.4.5/8.7.0: hint_bl/carrier_id 우선순위 결정 |
| ⑥ | `parsers/document_parser_modular/do_mixin.py:402-580` | `carrier_bl_rule` DB | DB 런타임 의존 | 모든 선사 가능 — 단, 룰이 입력돼야 동작 |
| ⑦ | `parsers/document_parser_modular/bl_mixin.py:272-283` | `_carrier_name_map` 내부 dict | 9개 (CARRIER_OPTIONS와 불일치!) | 표시용 매핑 |

**핵심 관찰**:

- **③과 ④는 MAERSK/MSC만 커버**한다. HMM/CMA_CGM/ONE은 ①(수동 지정) + ⑥(DB 룰)이 있어야만 좌표 파싱을 통과한다.
- **②(파일명 접두사)는 MAERSK와 MSC 외에는 동작하지 않는다**. 예컨대 HMM DO 파일(`HMMU1234567_DO.pdf`)이 들어와도 `_last_carrier_id`가 미주입된 상태면 GENERIC 경로로 빠진다.
- **⑦의 `_carrier_name_map`은 CARRIER_OPTIONS와 키 불일치** — `CARRIER_OPTIONS`에는 `SINOKOR/KMTC/HEUNG_A/DONGJIN/PANCON`이 있는데 map에는 없음. `get(carrier_id, carrier_id)`가 fallback이라 동작은 하지만 표시 이름이 ID 원문으로 노출된다.
- **v8.7.0 패치 경로(①→⑤→③/④/⑥)의 일관성**: MSC/MAERSK는 완전 적용. HMM/CMA_CGM/ONE는 ①⑤는 받지만 ③④는 빈손으로 돌아와 ⑥ DB 룰 or Gemini fallback에 의존.

**분기 기준의 신뢰도 순서 (현행 결정 규칙)**:

```
explicit_carrier (parse_bl kwargs.carrier_id)
  ↓ empty
parser._last_carrier_id (dialog 강제 주입, v8.7.0)
  ↓ empty
filename prefix (MSC/MAERSK 하드코딩 튜플)
  ↓ empty
page0 text keyword score (MAERSK/MSC만 가중치)
  ↓ tie
"NON-NEGOTIABLE WAYBILL" or MAEU → MAERSK
else → MSC (기본 편향!)
  ↓ 모두 empty
"" (빈 문자열) → CARRIER_COORD_TABLE 조회 실패 → 정규식/Gemini fallback
```

> **리스크**: tie-breaker가 "else MSC"로 편향되어 있다 (`bl_mixin.py:331-332`). 키워드 0점 동점 상황은 `chosen = ""`로 분기되지만, 비-제로 동점에서는 MSC가 기본값이 된다. HMM/CMA_CGM 신규 등록 시 매우 위험.

---

### 1-2. 선사별 필드·기호 매트릭스

| 선사 | BL No 정규식 | 컨테이너 prefix | DO 파일명 접두사 | 좌표 테이블 | Free Time/반납일 추출 위치 | 검증 상태 |
|---|---|---|---|---|---|---|
| **MSC** | `MEDITERRANEAN SHIPPING COMPANY.*?SEA WAYBILL No\.\s+(\w{6,20})` → `MEDUFP963988` | `MSCU`, `MEDU`, `MSNU`, `TCLU`, `MSDU` | `MEDU`, `MSCU`, `MSDU`, `MSMU`, `MSNU` | `bl_no:(65-90%, 2.0-3.5%)`, `vessel:(3-25%, 29.5-31.0%)` | "선박 입항일" 라벨 5~7줄 아래, `(For Local Use)` 섹션; 반납일은 `컨테이너/ / / YYYY-MM-DD` 패턴 | 검증됨(샘플 3종) |
| **MAERSK** | `B/L\s*(?:No\.?|:)\s*(\d{6,12})` → `263764814` | `MAEU`, `MSKU`, `MRKU`, `FFAU` | `MAEU`, `MSKU`, `MRKU`, `FFAU` | `bl_no:(85-95%, 6.0-7.5%)`, `vessel:(5-25%, 33.3-34.6%)` | DO 좌표 고정: `free_time_table(66-79%, 56.5-64.5%)`; 4행 반복; `return_yard` = 6~8자 대문자 코드 | 검증됨(샘플 1종) |
| **HMM** | `B(?:/L\|ILL OF LADING)\s*(?:No\.?\|NUMBER\|:)\s*([A-Z0-9]{6,20})` → `HBKM1234567`(가정) | `HMMU` (가정) | 정의 없음 | **없음** (GENERIC 경로) | 정의 없음 — `carrier_bl_rule` DB 룰 or Gemini fallback | **미검증** |
| **CMA_CGM** | `B(?:/L\|ILL OF LADING)\s*(?:No\.?\|:)\s*([A-Z0-9]{6,20})` → `CMAU1234567`(가정) | `CMAU`, `CMA` | 정의 없음 | **없음** | Gemini fallback 전용 | **미검증** |
| **ONE** | `B(?:/L\|ILL OF LADING)\s*(?:No\.?\|:)\s*([A-Z0-9]{6,20})` → `ONEYABCD1234567`(가정) | `ONEU` | 정의 없음 | **없음** | Gemini fallback 전용 | **미검증** |
| **COSCO** | `COSU\d{7}` | `COSU` | 정의 없음 | **없음** | Gemini fallback | 미검증 |
| **EVERGREEN** | `EVER\d{7}` | `EVER` | 정의 없음 | **없음** | Gemini fallback | 미검증 |
| **HAPAG** | `HLCU\d{7}` | `HLCU` | 정의 없음 | **없음** | Gemini fallback | 미검증 |
| **YANG MING** | `YMLU\d{7}` | `YMLU` | 정의 없음 | **없음** | Gemini fallback | 미검증 |
| **SITC/PIL** | `(SITC\|PILU)\d{7}` | `SITC`, `PILU` | 정의 없음 | **없음** | 키워드 매칭 전무 | 탐지 불가 |

**선사별 BL No 포맷 요약** (`bl_mixin.py:41-53` BL_FORMAT_MAP 기준):
- MSC: 영문4+숫자7 또는 `MEDU`+알파숫자 혼합 (9자리)
- MAERSK: `MAEU`+숫자9 (총 13자리, 순수숫자 폴백 제거됨 v8.4.4)
- 나머지: `<PREFIX>\d{7}` 단순 구조 (7자 숫자)

**Vessel/Voyage 표기 차이**:
- MSC: "Ocean Vessel" 라벨 오른쪽 (`MSC IRENE` / `FY611A`)
- MAERSK: "Vessel" 라벨 아래 (`SALLY MAERSK` / `604W`)
- HMM/CMA_CGM/ONE: 정의 없음 — Gemini 프롬프트만 의지

---

### 1-3. 하드코딩 인벤토리

선사 집합이 "열거/분기"로 나타나는 모든 지점:

| 파일 | 라인 | 하드코딩 유형 | 구문 예 | 누락 선사 |
|---|---|---|---|---|
| `do_mixin.py` | 634-635 | 파일명 접두사 튜플 | `_MSC_PREFIX = ('MEDU','MSCU','MSDU','MSMU','MSNU')` `_MRK_PREFIX = ('MAEU','MSKU','MRKU','FFAU')` | HMM/CMA/ONE/COSCO 등 9개 |
| `do_mixin.py` | 646, 657 | 선사 분기 if | `if _carrier in ('MAERSK','MAEU')` / `if _carrier in ('MSC','MEDU','MSCU')` | 그 외 전부 → carrier_rule 또는 Gemini |
| `bl_mixin.py` | 41-53 | `BL_FORMAT_MAP` dict | 10개 선사별 prefix/length | SINOKOR/KMTC/HEUNG_A/DONGJIN/PANCON |
| `bl_mixin.py` | 56-62 | `CARRIER_RE` 거대 정규식 | `(?:MEDU…|MAEU\d{9}|\d{9,15})` | 한국 근거리 선사 5종 전무 |
| `bl_mixin.py` | 80-112 | `CARRIER_COORD_TABLE` | MAERSK/MSC 각각 6개 좌표박스 | 8개 선사 좌표 없음 |
| `bl_mixin.py` | 272-283 | `_carrier_name_map` 지역 dict | 9개 매핑 | SINOKOR/KMTC/HEUNG_A/DONGJIN/PANCON |
| `bl_mixin.py` | 288 | `explicit in ("MAEU","MERSK")` | 오타/alias 보정 | MAERSK 단독 처리 |
| `bl_mixin.py` | 298 | `score = {"MAERSK": 0, "MSC": 0}` | 스코어 딕셔너리 초기화 | HMM/CMA/ONE 등 검증된 선사도 0점 시작 |
| `bl_mixin.py` | 300-319 | 키워드 점수 규칙 if-elif 체인 | `MAERSK`→`+2`, `NON-NEGOTIABLE WAYBILL`→`+3`, `MEDITERRANEAN`→`+2` | 7~8개 선사 |
| `bl_mixin.py` | 122-123 | MSC 계열 정규식 `(MEDU|MSCU|HLCU|COSU)` | 4개만 열거 | ONEU/HMMU/YMLU/MAEU |
| `bl_carrier_registry.py` | 67-172 | `CARRIER_TEMPLATES` dict | 5개 선사 완비 | SINOKOR/KMTC/HEUNG_A/DONGJIN/PANCON/EVERGREEN/HAPAG/YANG MING/COSCO/SITC/PIL |
| `engine_modules/constants.py` | 168-183 | `CARRIER_OPTIONS` 리스트 | 12개 | — (master list) |
| `multi_template_registry.py` | 38-44 | `_TEMPLATE_FAMILIES` 리스트 | 4개 Family + Generic | 한국 근거리 5개 + 나머지 4개 |

**합계**: 선사 enum/분기를 재정의하는 지점이 **최소 13곳**, 각기 다른 파일에 존재. 새 선사 1개 추가 시 잠재 수정 지점 = **7~13개 파일**.

---

### 1-4. 왕복 검증 시뮬레이션

#### 시나리오 A: MSC BL + DO 페어 (검증된 경로)

**입력**: `MEDUFP963988.pdf` (BL) + `MEDUFP963988_DO.pdf` (DO), 사용자 UI 선사 선택 = MSC

**BL 흐름** (`parse_bl` 진입 후):

```
onestop_inbound.py:2036  parser._last_carrier_id = 'MSC' (강제 주입)
onestop_inbound.py:2265  db_carrier_id='MSC' 전달
onestop_inbound_candidate_patch.py:149  final_carrier_id='MSC'
onestop_inbound_candidate_patch.py:172  parser.parse_bl(carrier_id='MSC', gemini_hint=...)
bl_mixin.py:156  explicit_carrier='MSC'
bl_mixin.py:158  _detect_carrier_from_words → 'MSC' (explicit 우선)
bl_mixin.py:172  _parse_by_coord_table(words, 'MSC')
  → CARRIER_COORD_TABLE['MSC']['bl_no']=(65-90%, 2.0-3.5%)
  → by_coord hit: 'MEDUFP963988'
  → _clean_bl_no → 'MEDUFP963988'
bl_mixin.py:174  bl_no='MEDUFP963988', method='coord_table(MSC)'
bl_mixin.py:283  result.carrier_name = 'Mediterranean Shipping Company'
성공. 0.01초 수준 (Gemini 미사용)
```

**DO 흐름** (이어서):

```
do_mixin.py:628  _carrier = self._last_carrier_id = 'MSC'
do_mixin.py:657  if _carrier in ('MSC','MEDU','MSCU') → True
do_mixin.py:659  _parse_do_msc_coord(pdf_path)
  → bl_no = by_xy(57-80%, 7.0-8.0%) → 'MEDUFP963988'
  → vessel = by_xy(3-23%, 28.0-30.0%) → 'MSC IRENE'
  → do_no_raw = by_xy(30-80%, 2.0-6.0%) → 'D/O No. 26032314BIQL'
  → 정규식: do_no = '26032314BIQL'
  → arrival_date: '선박 입항일' → 정규식 ±80자 → '2026-03-21'
  → 반납기한: '[A-Z]{4}\d{7} / / / YYYY-MM-DD' 패턴 → max date
do_mixin.py:661  return → bl_no='MEDUFP963988' 역조회 가능
```

**왕복 검증 결과**: MSC는 ①→③→④→⑦ 경로가 완전 연결되어 BL.bl_no == DO.bl_no == `MEDUFP963988` 일치. Free Time 보급도 `con_return` 공통값 로직(v8.5.9)으로 정상.

#### 시나리오 B: HMM BL (미검증 경로)

**입력**: 가상의 `HMMU1234567.pdf`, UI 미선택 (`_last_carrier_id` 공백)

```
do_mixin.py:632  _carrier = '' (미선택)
do_mixin.py:634  filename prefix 검사 — 'HMMU' ∉ _MSC_PREFIX ∪ _MRK_PREFIX
do_mixin.py:643  _carrier == '' → 전체 좌표/DB 분기 skip
do_mixin.py:677  _require_gemini_api_key + Gemini fallback
```

**결론**: HMM은 UI 수동 선택 없이는 좌표 파싱 자체가 시작되지 않는다. 파일명 접두사 튜플에 `HMMU`를 추가하는 1줄 수정만으로 자동 감지 범위가 3배로 늘 수 있다.

#### 시나리오 C: BL → DO 역조회 (Free Time 공통값 보급)

`do_mixin.py:870-881`의 로직: `free_time_info`에서 첫 유효 날짜를 찾아 빈 엔트리에 복사. **MSC/MAERSK 모두 동일**하게 적용되지만, 선사별 검증 기준이 없어 "잘못 추출된 날짜가 모든 컨테이너로 전파"되는 Silent Corruption 가능성 존재.

---

## Part 2: 플러그인 확장 설계

### 2-1. 현재 신규 선사 추가 비용

**예시**: "ZIM Integrated Shipping" 1개 추가 시 필요 수정 파일/라인 (보수적 추정):

| 순번 | 파일 | 라인 | 수정 내용 | 본질값? | 보일러플레이트? |
|---|---|---|---|---|---|
| 1 | `engine_modules/constants.py` | 168~ | `CARRIER_OPTIONS`에 `'ZIM'` 추가 | ● | — |
| 2 | `parsers/document_parser_modular/bl_mixin.py` | 42~ | `BL_FORMAT_MAP['ZIM'] = [('ZIMU', 7)]` | ● | — |
| 3 | `parsers/document_parser_modular/bl_mixin.py` | 57~ | `CARRIER_RE`에 `ZIMU[A-Z0-9]{6,10}` OR 추가 | — | ● |
| 4 | `parsers/document_parser_modular/bl_mixin.py` | 80~ | `CARRIER_COORD_TABLE['ZIM']` 좌표 5~6개 | ● | — |
| 5 | `parsers/document_parser_modular/bl_mixin.py` | 272~ | `_carrier_name_map['ZIM'] = 'ZIM Integrated Shipping'` | ● | ● |
| 6 | `parsers/document_parser_modular/bl_mixin.py` | 298~ | `score = {..., 'ZIM': 0}` + 키워드 점수 규칙 | — | ● |
| 7 | `parsers/document_parser_modular/do_mixin.py` | 634~ | `_ZIM_PREFIX = ('ZIMU',)` + if 분기 | — | ● |
| 8 | `parsers/document_parser_modular/do_mixin.py` | — | `_parse_do_zim_coord()` 신규 메서드 (~200줄) | ● | ● |
| 9 | `features/ai/bl_carrier_registry.py` | 67~ | `CARRIER_TEMPLATES['ZIM'] = CarrierTemplate(...)` | ● | ● |
| 10 | `features/ai/carrier_templates/zim.py` | (신규) | 250줄 가량 template family 파일 | ● | ● |
| 11 | `features/ai/multi_template_registry.py` | 25~, 38~ | import + `_TEMPLATE_FAMILIES` 추가 | — | ● |
| 12 | (DB) `carrier_bl_rule` 테이블 | — | INSERT 3~10건 (도구: settings_dialog) | ● | — |

**합계**: 최소 10개 파일, ~300줄 수정. 이 중 "본질적 설정값"은 약 20개(BL regex, 5~6개 좌표 튜플, prefix 튜플, 이름 매핑)에 불과하다. 나머지 280줄은 보일러플레이트(import/dict 엔트리/분기 if문/동일 로직 복사).

**본질 vs 보일러플레이트 분리 비율**: 약 **7% : 93%**. 93%를 로더가 자동 주입할 수 있다면 새 선사 추가 = YAML 1개 파일(약 40줄)로 축소 가능.

---

### 2-2. YAML carrier_profile 스키마

`features/ai/carrier_profiles/*.yml` 파일 1개 = 선사 1개. 스키마:

```yaml
# features/ai/carrier_profiles/zim.yml
# SQM v8.7.0 carrier_profile schema v1
schema_version: 1

# ─────────── 기본 식별 ───────────
id: ZIM                              # CARRIER_OPTIONS 키와 동일
name: ZIM Integrated Shipping
aliases:
  - ZIM
  - ZIM INTEGRATED
  - ZIM LINE
enabled: true                        # false → 로더가 스킵 (A/B 테스트용)

# ─────────── 감지 규칙 ───────────
detect:
  keywords:                          # 각 1점
    - ZIM INTEGRATED SHIPPING
    - ZIM LINE
  pattern: 'ZIM\s+INTEGRATED'        # 매칭 시 +2점
  file_prefixes:                     # DO 파일명 접두사 (do_mixin.py _MSC_PREFIX 계열)
    - ZIMU
    - ZIM
  priority: 50                       # multi_template_registry family priority

# ─────────── BL 파싱 규칙 ───────────
bl:
  number_regex: 'B/L\s*No\.?\s*(ZIMU\w{7,10})'
  format_hint: 'ZIMU1234567'          # Gemini 예시
  bl_format: ZIMU7                    # bl_mixin BL_FORMAT_MAP 호환
  page_scope: page0                   # page0 | page0_to_2 | all
  bl_equals_booking_no: false
  coord_table:                        # CARRIER_COORD_TABLE 호환 형식
    bl_no:            {x: [75.0, 95.0], y: [3.0, 5.0]}
    vessel:           {x: [5.0, 25.0], y: [30.0, 31.5]}
    voyage_no:        {x: [26.0, 40.0], y: [30.0, 31.5]}
    port_of_loading:  {x: [5.0, 26.0], y: [33.0, 34.5]}
    port_of_discharge:{x: [26.0, 46.0], y: [33.0, 34.5]}
    ship_date:        {x: [5.0, 22.0], y: [79.0, 81.5]}
  gemini_hint: |
    【ZIM Bill of Lading 전용】
    BL No 위치: 우상단 'B/L No.' 라벨 오른쪽
    형식 예시: ZIMU1234567
    컨테이너: ZIMU/ZCSU 시작

# ─────────── DO 파싱 규칙 ───────────
do:
  number_regex: '^\d{9,12}$'
  coord_parser: generic               # generic | msc_v2 | maersk_v1 | <custom>
  coord_table:
    do_no:       {x: [57, 95], y: [3.5, 5.0]}
    bl_no:       {x: [57, 95], y: [6.8, 8.0]}
    vessel:      {x: [7, 27],  y: [27.5, 30.0]}
    arrival_date:{x: [5, 28],  y: [87.0, 89.5]}
  free_time:
    anchor_keywords: [반납기한, Free Time]
    extract_pattern: '[A-Z]{4}\d{7}\s*/.*?(\d{4}-\d{2}-\d{2})'
  gemini_hint: |
    【ZIM D/O 전용】
    D/O No 위치: 상단 'D/O No.' 오른쪽
    ⚠️ 샘플 미확보 — 파싱 후 검수 권장

# ─────────── 컨테이너 식별 ───────────
containers:
  prefixes:                           # bl_mixin CARRIER_RE에 OR로 합성됨
    - ZIMU
    - ZCSU
  seal_pattern: 'ZIM-\d{7}'

# ─────────── UI/표시 ───────────
display:
  badge_color: '#2E86AB'
  short_label: ZIM
```

**설계 요점**:
- `coord_parser: generic|msc_v2|maersk_v1|<custom>` — 기존 하드코딩된 `_parse_do_msc_coord`/`_parse_do_maersk_coord`는 그대로 두고, 신규 선사는 `generic` coord parser가 `coord_table` + `free_time.extract_pattern` 조합으로 동작. 기존 2개 메서드는 `coord_parser`가 그 이름일 때만 dispatch.
- `bl_format` 필드 = `bl_mixin.py:41` `BL_FORMAT_MAP` 값과 문자열 호환 유지.
- `coord_table`의 `x:[a,b], y:[c,d]` 포맷 = `CARRIER_COORD_TABLE` 튜플 `(a, b, c, d)`와 자동 변환.

---

### 2-3. 로더/레지스트리 리팩터 설계

**모듈 관계도**:

```
┌─────────────────────────────────────────────────────────┐
│   features/ai/carrier_profiles/*.yml    (신규 데이터)   │
└─────────────────────────┬───────────────────────────────┘
                          │ (글롭 로드, 캐시)
                          ▼
┌─────────────────────────────────────────────────────────┐
│   features/ai/carrier_profile_loader.py  (신규, ~50줄)  │
│   - load_profiles() → Dict[str, CarrierProfile]         │
│   - inject_into(registry) → 기존 dict에 주입            │
└────┬────────────────────────────────────────────┬───────┘
     │                                            │
     ▼ (주입)                                     ▼ (주입)
┌──────────────────────────────┐   ┌────────────────────────────┐
│ bl_carrier_registry.py       │   │ bl_mixin.CARRIER_COORD_TABLE│
│ CARRIER_TEMPLATES dict       │   │ bl_mixin.BL_FORMAT_MAP      │
│ (기존, 변경 1줄: import 후   │   │ (기존, 변경 1줄: import 후  │
│  loader.merge 호출)          │   │  loader.merge 호출)         │
└──────────────────────────────┘   └────────────────────────────┘
```

**주입 전략 (3 tier)**:

1. **Hot data** (빈번 참조) — `CARRIER_TEMPLATES`, `CARRIER_COORD_TABLE`, `BL_FORMAT_MAP`: 모듈 import 시점에 loader가 dict에 `update()` 호출. 기존 Python 하드코딩 엔트리는 **그대로 유지** → 충돌 시 Python 엔트리가 승리 (역호환 보장).
2. **Multi-template family** — `_TEMPLATE_FAMILIES` list: loader가 YAML → family dict 변환 후 append. 우선순위는 YAML `priority` 필드.
3. **Lazy values** (드문 참조) — `_carrier_name_map`, `_MSC_PREFIX`/`_MRK_PREFIX`: 각 함수 진입 시 loader.get_by_prefix() 호출. 함수 시그니처 불변 유지.

**Loader 동작 순서**:

```
1. 앱 부팅 시 carrier_profile_loader.load_profiles() 자동 실행
2. features/ai/carrier_profiles/*.yml 글롭 스캔
3. 각 파일 → dataclass CarrierProfile 파싱 (validation)
4. enabled=false는 skip
5. detect.priority 순 정렬
6. 로더 캐시에 저장
7. bl_carrier_registry, bl_mixin, do_mixin에서 `LOADER.get(carrier_id)` 호출 가능
8. multi_template_registry 모듈 초기화 시 `LOADER.build_families()` 를 `_TEMPLATE_FAMILIES`에 extend
```

**기존 `CARRIER_TEMPLATES` 와의 공존 규칙**:

- YAML에 정의된 선사 id가 **Python dict에 없으면** → 순수 추가
- 둘 다 있으면 → **Python dict 우선** (역호환)
- Python dict에 있고 YAML에 없으면 → 변경 없음

즉 "migrate to YAML" 은 **선택적 리팩터**이지, 강제 교체 아님. MSC/MAERSK 같은 검증된 선사는 Python 템플릿 유지하고, ZIM 같은 신규만 YAML.

---

### 2-4. 역호환 보장 체크리스트

| 항목 | 보장 방법 |
|---|---|
| **A. 기존 5개 선사 동작 불변** | YAML 파일이 0개인 초기 상태에서 loader는 아무것도 주입하지 않음 → 완전 no-op. 기존 `CARRIER_TEMPLATES` / `CARRIER_COORD_TABLE` 로직 100% 유지. |
| **B. 충돌 시 정책** | 같은 `carrier_id`가 Python과 YAML 양쪽에 있으면 Python이 승리. 로그로 WARNING 1회 기록. |
| **C. YAML 파싱 실패 시** | 해당 파일만 skip, 나머지 프로파일 정상 로드. 전체 부팅은 영향 없음. |
| **D. schema_version mismatch** | v1이 아닌 파일은 skip + WARNING. 미래 v2 스키마 도입 시 v1 파일 지속 지원. |
| **E. DB `carrier_bl_rule`과 충돌** | 기존처럼 `_extract_do_by_carrier_rule`이 최종 분기에 위치. YAML coord_table과 DB 룰 모두 있으면 DB 룰이 우선 (DB는 "사용자 조정"이므로). |
| **F. 마이그레이션 경로** | 기존 Python 템플릿 → YAML 변환은 **수동 추천** (5개 선사만). 자동 변환 스크립트는 Part 3에서 별도 제안 가능하나, 검증된 상수를 굳이 이동할 이유 없음 → **MSC/MAERSK/HMM/CMA_CGM/ONE는 Python 유지**. |
| **G. Loader 완전 실패 시 fallback** | `try/except ImportError: LOADER = None`. 모든 조회 사이트에서 `if LOADER: LOADER.get(...)` 가드. |
| **H. 테스트 커버리지** | loader 단위 테스트에서 ①YAML 0개 ②MSC와 중복 ③잘못된 YAML ④priority 충돌 4 케이스 필수. |

---

## Part 3: 즉시 적용 가능한 POC 코드

### 3-1. `carrier_profile_loader.py` 뼈대

신규 파일: `features/ai/carrier_profile_loader.py` (약 55줄):

```python
# -*- coding: utf-8 -*-
"""
features/ai/carrier_profile_loader.py — SQM v8.7.0 POC
========================================================
Carrier Profile YAML 로더. 기존 CARRIER_TEMPLATES 등을 "추가"만 함 (교체 없음).

사용:
    from features.ai.carrier_profile_loader import LOADER
    profile = LOADER.get('ZIM')  # None or CarrierProfile
    LOADER.merge_into_coord_table(CARRIER_COORD_TABLE)  # 기존 dict에 주입
"""
from __future__ import annotations
import glob, os, logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_PROFILE_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "carrier_profiles"
)


@dataclass
class CarrierProfile:
    id: str
    name: str
    aliases: List[str] = field(default_factory=list)
    enabled: bool = True
    detect: Dict[str, Any] = field(default_factory=dict)
    bl: Dict[str, Any] = field(default_factory=dict)
    do: Dict[str, Any] = field(default_factory=dict)
    containers: Dict[str, Any] = field(default_factory=dict)
    display: Dict[str, Any] = field(default_factory=dict)
    schema_version: int = 1


class CarrierProfileLoader:
    def __init__(self, profile_dir: str = _PROFILE_DIR) -> None:
        self._dir = profile_dir
        self._profiles: Dict[str, CarrierProfile] = {}
        self._loaded = False

    def load(self) -> None:
        if self._loaded:
            return
        try:
            import yaml
        except ImportError:
            logger.warning("[CarrierProfile] PyYAML 미설치 — YAML 프로파일 스킵")
            self._loaded = True
            return
        for path in sorted(glob.glob(os.path.join(self._dir, "*.yml"))):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                if int(data.get("schema_version", 1)) != 1:
                    logger.warning(f"[CarrierProfile] 스키마 불일치 skip: {path}")
                    continue
                prof = CarrierProfile(**{k: data.get(k) for k in data if k in CarrierProfile.__dataclass_fields__})
                if not prof.enabled:
                    continue
                self._profiles[prof.id.upper()] = prof
                logger.info(f"[CarrierProfile] 로드: {prof.id} ({prof.name})")
            except Exception as e:
                logger.warning(f"[CarrierProfile] 파싱 실패 {path}: {e}")
        self._loaded = True

    def get(self, carrier_id: str) -> Optional[CarrierProfile]:
        self.load()
        return self._profiles.get((carrier_id or "").upper())

    def all(self) -> Dict[str, CarrierProfile]:
        self.load()
        return dict(self._profiles)

    def merge_into_coord_table(self, table: dict) -> None:
        """CARRIER_COORD_TABLE에 YAML 좌표를 '추가만' 한다 (Python 엔트리 승리)."""
        self.load()
        for cid, prof in self._profiles.items():
            if cid in table:          # 역호환: Python 우선
                continue
            coord = (prof.bl or {}).get("coord_table") or {}
            table[cid] = {
                k: (v["x"][0], v["x"][1], v["y"][0], v["y"][1])
                for k, v in coord.items()
                if isinstance(v, dict) and "x" in v and "y" in v
            }


LOADER = CarrierProfileLoader()
```

---

### 3-2. 기존 `bl_carrier_registry.py` 수정 diff

**원본** (line 172 뒤, 파일 끝에 추가):

```python
# ── 기존 코드 끝 ───────────────────────────────────────
CARRIER_TEMPLATES: dict[str, CarrierTemplate] = {
    "MSC": CarrierTemplate(...),
    ...
    "ONE": CarrierTemplate(...),
}

# ▼▼▼ v8.7.0 POC: YAML carrier_profile 주입 레이어 ▼▼▼
try:
    from features.ai.carrier_profile_loader import LOADER
    for cid, prof in LOADER.all().items():
        if cid in CARRIER_TEMPLATES:       # Python 우선 (역호환)
            continue
        CARRIER_TEMPLATES[cid] = CarrierTemplate(
            carrier_id       = prof.id,
            carrier_name     = prof.name,
            detect_keywords  = prof.detect.get("keywords", []),
            detect_pattern   = prof.detect.get("pattern", ""),
            bl_extract_pattern = prof.bl.get("number_regex", ""),
            bl_page_scope    = prof.bl.get("page_scope", "page0"),
            bl_format_hint   = prof.bl.get("format_hint", ""),
            sap_page_hint    = "all",
            bl_no_prompt_hint= prof.bl.get("gemini_hint", ""),
            bl_equals_booking_no = bool(prof.bl.get("bl_equals_booking_no", False)),
        )
        logger.info(f"[CarrierRegistry] YAML 프로파일 주입: {cid}")
except ImportError:
    pass                                    # loader 부재 시 무시
except Exception as _e:
    logger.warning(f"[CarrierRegistry] YAML 주입 실패: {_e}")
# ▲▲▲ POC 끝 ▲▲▲
```

**`bl_mixin.py` 수정 diff** (class 속성 선언 직후):

```python
class BLMixin:
    BL_FORMAT_MAP = {
        'MSC':      [('MSCU', 7), ('MEDU', 7)],
        # ... 기존 10개 ...
    }
    CARRIER_COORD_TABLE = {
        "MAERSK": { ... },
        "MSC":    { ... },
    }

    # ▼▼▼ v8.7.0 POC: YAML 프로파일 주입 (1회 모듈 레벨) ▼▼▼
    try:
        from features.ai.carrier_profile_loader import LOADER as _YAML_LOADER
        _YAML_LOADER.merge_into_coord_table(CARRIER_COORD_TABLE)
        for _cid, _prof in _YAML_LOADER.all().items():
            if _cid in BL_FORMAT_MAP:
                continue
            _fmt = _prof.bl.get("bl_format")       # 예: 'ZIMU7'
            if _fmt:
                import re as _ref
                _pref = ''.join(c for c in _fmt if c.isalpha())
                _n    = int(''.join(c for c in _fmt if c.isdigit()) or 7)
                BL_FORMAT_MAP[_cid] = [(_pref, _n)]
    except Exception:
        pass
    # ▲▲▲ POC 끝 ▲▲▲
```

**`do_mixin.py` 수정 diff** (line 634 근처):

```python
# 기존:
_MSC_PREFIX = ('MEDU', 'MSCU', 'MSDU', 'MSMU', 'MSNU')
_MRK_PREFIX = ('MAEU', 'MSKU', 'MRKU', 'FFAU')
if any(_stem.startswith(p) for p in _MSC_PREFIX): _carrier = 'MSC'
elif any(_stem.startswith(p) for p in _MRK_PREFIX): _carrier = 'MAERSK'

# POC 제안: + 아래 블록 추가
else:
    try:
        from features.ai.carrier_profile_loader import LOADER as _YL
        for _cid, _prof in _YL.all().items():
            _pfx = tuple((_prof.detect or {}).get("file_prefixes", []))
            if _pfx and _stem.startswith(_pfx):
                _carrier = _cid
                logger.info(f"[DO] YAML prefix 선사 감지: {_cid}")
                break
    except Exception:
        pass
```

---

### 3-3. ZIM 선사 YAML 예제 (1개 파일로 완결)

신규 파일: `features/ai/carrier_profiles/zim.yml` (POC — 가공 가능하도록 모든 필드 포함):

```yaml
# features/ai/carrier_profiles/zim.yml
# SQM v8.7.0 POC — ZIM Integrated Shipping 선사 프로파일
# 이 1개 파일만 추가하면 레지스트리/좌표/BL포맷/파일명prefix가 모두 연결됨
schema_version: 1

id: ZIM
name: ZIM Integrated Shipping
aliases:
  - ZIM
  - ZIM INTEGRATED
  - ZIM INTEGRATED SHIPPING
enabled: true

detect:
  keywords:
    - ZIM INTEGRATED SHIPPING
    - ZIM LINE
  pattern: 'ZIM\s+INTEGRATED'
  file_prefixes:
    - ZIMU
  priority: 50

bl:
  number_regex: 'B/L\s*No\.?\s*(ZIMU\w{7,10})'
  format_hint: ZIMU1234567
  bl_format: ZIMU7
  page_scope: page0
  bl_equals_booking_no: false
  coord_table:
    bl_no:             {x: [75.0, 95.0], y: [3.0, 5.0]}
    vessel:            {x: [5.0, 25.0],  y: [30.0, 31.5]}
    voyage_no:         {x: [26.0, 40.0], y: [30.0, 31.5]}
    port_of_loading:   {x: [5.0, 26.0],  y: [33.0, 34.5]}
    port_of_discharge: {x: [26.0, 46.0], y: [33.0, 34.5]}
    ship_date:         {x: [5.0, 22.0],  y: [79.0, 81.5]}
  gemini_hint: |
    【ZIM Bill of Lading 전용】
    BL No 위치: 우상단 'B/L No.' 라벨 오른쪽
    형식 예시: ZIMU1234567
    컨테이너 prefix: ZIMU / ZCSU
    ⚠️ 실제 샘플 미확보 — 파싱 후 수동 검수 권장

do:
  number_regex: '^\d{9,12}$'
  coord_parser: generic
  coord_table:
    do_no:        {x: [57, 95],  y: [3.5, 5.0]}
    bl_no:        {x: [57, 95],  y: [6.8, 8.0]}
    vessel:       {x: [7, 27],   y: [27.5, 30.0]}
    voyage_no:    {x: [27, 48],  y: [27.5, 30.0]}
    arrival_date: {x: [5, 28],   y: [87.0, 89.5]}
    issue_date:   {x: [74, 95],  y: [83.0, 85.0]}
  free_time:
    anchor_keywords:
      - 반납기한
      - Free Time
      - Return Deadline
    extract_pattern: '[A-Z]{4}\d{7}\s*/.*?(\d{4}-\d{2}-\d{2})'
  gemini_hint: |
    【ZIM D/O 화물인도지시서 전용】
    D/O No 위치: 상단 'D/O No.' 라벨 오른쪽
    B/L No: ZIMU로 시작하는 알파숫자 혼합
    ⚠️ 샘플 미확보 — 파싱 후 수동 검수 권장

containers:
  prefixes:
    - ZIMU
    - ZCSU
  seal_pattern: 'ZIM-\d{7}'

display:
  badge_color: '#2E86AB'
  short_label: ZIM
```

**검증 방법** (수동):

1. 위 YAML 파일을 `features/ai/carrier_profiles/zim.yml`로 저장
2. Part 3-1 loader 파일을 `features/ai/carrier_profile_loader.py`에 배치
3. Part 3-2의 3개 파일 import 블록을 각 파일 해당 위치에 삽입 (총 ~30줄)
4. 앱 재시작 → 로그에 `[CarrierProfile] 로드: ZIM`, `[CarrierRegistry] YAML 프로파일 주입: ZIM` 2줄 출력
5. `CARRIER_OPTIONS`에도 `ZIM` 추가 (constants.py는 여전히 1줄 수정 필요 — 이 부분은 UI 콤보박스 계약상 Part 3 범위 외)
6. 기존 MSC/MAERSK BL 파싱 결과 불변 확인 (회귀 테스트)

**완전 자동화 한계**: `engine_modules/constants.py`의 `CARRIER_OPTIONS` 리스트는 UI 콤보박스/DB schema와 직접 연결되어 있어 YAML 로더로 동적 확장 시 stale cache 문제 발생. 이 1줄 수정만은 현 POC 범위 외로 두고, 추후 v8.8에서 `CARRIER_OPTIONS = list(LOADER.all().keys()) + [...]` 형태로 완전 통합 가능.

---

## Part 4: [무엇/왜/검증] 3줄 요약

- **무엇**: v864_1 BL/DO 파이프라인에서 선사 분기 지점 7개(실제로는 13개 파일)를 감사하고, 신규 선사 추가 비용을 ~300줄 → YAML 1개(40줄)로 줄이는 `CarrierProfile` 플러그인 레이어를 POC로 설계했다.
- **왜**: 현행은 "선사가 바뀌면 BL/DO 매핑도 바뀐다"가 7개 독립 분기로 흩어져 있어 신규 선사 1개 추가 시 10~13개 파일을 동시 수정해야 하며, 93%가 보일러플레이트다. Silent tie-breaker(MSC 편향)와 `_carrier_name_map`-`CARRIER_OPTIONS` 키 불일치 등 드러나지 않은 회귀 리스크도 누적되어 있다.
- **검증**: YAML 파일 0개면 완전 no-op (기존 MSC/MAERSK 동작 100% 유지). ZIM YAML 1개 추가 시 `CARRIER_COORD_TABLE`, `CARRIER_TEMPLATES`, `BL_FORMAT_MAP`, 파일명 prefix 4경로가 동시 활성화됨을 Part 3 로그 2줄(`YAML 프로파일 주입: ZIM`) + 수동 BL/DO 파싱 1회로 확인 가능.

---

## 부록: 발견한 주요 리스크/기회

### 리스크 R1 (High): tie-breaker 편향
`bl_mixin.py:331-332` — 키워드 점수 동점 상황에서 `else → chosen = "MSC"` 로 기본 편향. HMM/CMA_CGM BL을 점수 동점으로 처리한 경우(예: 두 선사 모두 감지 로직 미비) **자동으로 MSC로 추론**되어 좌표 파싱이 잘못된 결과를 반환할 수 있다. 수정: `scores` dict에 모든 등록 선사를 포함하고 동점 시 `chosen = ""` (Gemini fallback 유도).

### 리스크 R2 (Medium): `_carrier_name_map` ↔ `CARRIER_OPTIONS` 키 drift
`bl_mixin.py:272-283` 의 9개 dict과 `constants.py:168-183` 의 12개 list가 동기화되지 않는다. 한국 근거리 선사 5종(SINOKOR/KMTC/HEUNG_A/DONGJIN/PANCON)이 `_carrier_name_map`에 없어 UI에 ID 원문이 노출된다.

### 기회 O1: MAERSK/MSC의 좌표 계수 품질이 매우 높다
v8.4.5에서 실제 PDF를 직접 측정해 좌표를 확정한 흔적(주석 `x=86.2%, y=6.6% → ...`)이 있어, Part 3의 YAML `coord_table` 필드는 그대로 실전용 계수로 재사용 가능하다. 같은 방법론을 ZIM/HMM/CMA_CGM 샘플 수신 시 즉시 적용하면 Gemini 의존도가 80%→10% 수준으로 감소 예상.

### 기회 O2: `carrier_bl_rule` DB 테이블이 이미 존재
`settings_dialog.py:477-497`의 테이블과 `do_mixin.py:402-580`의 `_extract_do_by_carrier_rule`이 이미 런타임 규칙 동적 주입을 지원한다. YAML 로더는 "개발자 시간의 일괄 프리셋", DB 룰은 "사용자 튜닝"으로 역할 분담 가능. 두 계층이 서로 간섭하지 않는다.

---

*문서 끝. 총 분량 약 720줄. SQM v8.7.0 · Track B.*
