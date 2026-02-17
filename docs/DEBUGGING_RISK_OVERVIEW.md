# SQM 전체 디버깅 리스크 총괄

> **목적**: 출고 로직 진입 전, 코드베이스 전반의 중복·혼용·데드코드·API 불일치를 한 문서에서 리스크 등급·정리 시점과 함께 정리.  
> **작성일**: 2026-02-16  
> **갱신**: v5.6.6 변수 통일(① 톤백 수, ② Invoice, ③ 무게 전달) 완료 반영.  
> **출처**: 업로드 분석(중복/혼용 8건, 데드코드, Ruby 의견) + 기존 REVIEW_DUPLICATES_AND_OUTBOUND_ENTRY.md 통합.  
> **코딩**: 본 문서는 검토·계획만 포함, 수정은 별도 진행.

---

## 1. 리스크 등급 정의

| 등급 | 의미 | 조치 |
|------|------|------|
| 🔴 **높음** | 출고/입고 경로에서 잘못 쓰이면 치명적(0개 생성, 롤백, 데이터 불일치). 방어 코드 누락 시 즉시 버그. | 출고 전 반드시 정리 권장 |
| 🟡 **중간** | 여러 이름이 같은 개념을 가리켜 디버깅·유지보수 비용 증가. 출고 시 “어느 변수를 읽어야 할지” 혼란. | 시점 정해져 정리(지금 vs 출고와 함께) |
| 🟢 **정상** | 의도적 구분이거나 이미 수정 완료. 변경 불필요. | 건드리지 않음 |
| ⬜ **보류** | 역할이 다르거나 DB/스키마 변경 리스크가 커서 현 상태 유지. | 건드리지 않음 |

---

## 2. 중복/혼용 변수 — 핵심 위험 8건

| 위험도 | 항목 | 혼용 내용 | 비고 |
|--------|------|-----------|------|
| 🟢 | **톤백 수** | ~~bag_count / tonbag_count~~ → **mxbg_pallet** 단일화 | **v5.6.6 완료**. inbound_mixin 로컬 변수명 유지, `packing.get('bag_count')` fallback 제거. dict 키는 mxbg_pallet로 통일(inbound_preview, export_mixin). |
| 🟢 | **Invoice 번호** | ~~invoice_no~~ → **salar_invoice_no** 단일화 | **v5.6.6 완료**. 파서 출력→엔진 입력 구간 salar_invoice_no만 사용. onestop packing_dict 중복 invoice_no 키 제거, inbound_mixin fallback 제거. |
| 🟡 | **톤백 번호** | `sub_lt` (INT) / `tonbag_no` (TEXT) / `tonbag_uid` (전역 식별) | 타입·스코프 다름. **보류** — 역할이 다르므로 현 상태 유지(Ruby 의견 반영) |
| 🟡 | **고객명** | `sold_to` / `picked_to` / `customer` (테이블마다 다름) | 출고 시 “어디에 기록할지” 불명확. DB 컬럼 변경 위험 있음. **v5.7.0 출고 로직과 함께 표준화** |
| 🟢 | **무게 전달** | ~~total_weight_kg~~ → **net_weight** 단일화 | **v5.6.6 완료**. 파서→엔진 구간 `packing.get('net_weight')`만 사용. `total_weight_kg`·gross_weight_kg fallback 제거. |
| 🟢 | **LOT 번호** | `lot_no` (고객) ≠ `lot_sqm` (SQM) | 의도적 구분. 정상. |
| 🟢 | **무게 3종** | `net_weight` ≠ `initial_weight` ≠ `current_weight` | 역할 다름(총입고/초기/잔량). 정상. |
| 🟢 | **v5.6.3 톤백 무게** | `t.weight` (개별) vs `i.net_weight` (LOT) | v5.6.3에서 수정 완료. 정상. |

---

## 3. 데드 코드

| 유형 | 대상 | 비고 |
|------|------|------|
| **테이블** | `picking_list_order`, `picking_list_detail`, `tonbag_mapping_history` | CREATE만 있고 참조 0회. 제거 또는 추후 출고 기능에서 사용 검토. |
| **파일** | `inbound_preview.py` (874줄) | v5.6.5에서 비활성화. 삭제 또는 복구 결정 필요. |
| **컬럼** | `inventory.eta_busan`, `inventory.stock_date`, `inventory.condition` | 사용처 없음. 마이그레이션/정리 시 제거 검토. |
| **컬럼** | `invoice_no` | `salar_invoice_no`와 100% 중복. Invoice 통일 시 제거 또는 deprecated 처리. |

---

## 4. 함수·모듈·API 리스크 (기존 검토 반영)

### 4.1 safe_* 함수 (🟡)

| 항목 | 내용 |
|------|------|
| **safe_int** | `utils/common.py`와 `gui_app_modular/utils/helpers.py`에 각각 구현. common이 더 보수적(쉼표/공백 처리). |
| **safe_date** | ① helpers: `→ Optional[date]` ② safe_utils: `→ str` (포맷 지정). 시그니처·반환 타입 상이. |
| **권장** | safe_int는 common 단일 소스로 통일; safe_date는 “객체용/문자열용” 구분 유지 또는 함수명 분리(safe_date_object / safe_date_str). |

### 4.2 버전·앱명·상수 (🟡)

| 항목 | 내용 |
|------|------|
| **버전** | `version.py`가 원천이나, fallback이 run, config, constants, engine_modules, parsers 등에 분산·값 상이(3.8.7~3.9.8). |
| **상수** | DEFAULT_WAREHOUSE, DEFAULT_TONBAG_COUNT 등이 engine_modules.constants와 gui_app_modular.utils.constants에 중복. |
| **권장** | 버전/앱명은 version.py만 참조; 비즈니스 상수는 engine_modules.constants를 단일 소스로 사용. |

### 4.3 메시지 박스 (🟡)

| 항목 | 내용 |
|------|------|
| **혼용** | CustomMessageBox(utils 구현 + dialogs re-export) vs tkinter.messagebox 직접 호출. |
| **권장** | 사용자 대면 메시지는 CustomMessageBox로 통일(AGENTS.md: 에러 시 show_detailed_error). |

### 4.4 출고 API — process_outbound (🟢)

| 항목 | 내용 |
|------|------|
| **정의** | 엔진은 `process_outbound(allocation_data)`만 존재. allocation_data = dict 또는 dict 리스트(lot_no, weight_kg, customer 등). |
| **v5.7.6 완료** | `import_handlers.py`가 allocation_data 형태로 호출하도록 수정. Excel에 무게 없으면 LOT의 current_weight 조회 후 전량 출고로 처리. |

---

## 5. 정리 시점·범위 (Ruby 의견 반영)

| 시점 | 항목 | 난이도 | 범위 | 비고 |
|------|------|--------|------|------|
| ~~**v5.6.6 지금 정리**~~ | ~~① 톤백 수~~ | ★★ | **완료** | packing.get('bag_count') fallback 제거, dict 키 mxbg_pallet 통일 |
| ~~**v5.6.6 지금 정리**~~ | ~~② Invoice~~ | ★ | **완료** | packing.get('invoice_no') fallback 제거, onestop 중복 키 제거 |
| ~~**v5.6.6 지금 정리**~~ | ~~③ 무게 전달~~ | ★ | **완료** | packing.get('total_weight_kg')·gross_weight_kg fallback 제거 |
| **v5.7.0 출고와 함께** | ④ 고객명 | ★★★ 높음 | sold_to / picked_to / customer 표준화. DB 컬럼 변경은 위험하므로 출고 로직 구현과 함께 처리. | |
| **보류** | ⑤ 톤백 번호 | — | sub_lt(DB 값), tonbag_no(표시용), tonbag_uid(전역) 역할이 다르므로 **건드리지 않음**. | tonbag_compat 헬퍼로 접근 유지 |

**v5.6.6 변수 통일** (v5.6.5 입고 경로 단일화 + v5.6.6 변수 통일 모두 포함)

| # | 변경 | 수정 파일 | 내용 |
|---|------|-----------|------|
| ① | bag_count → mxbg_pallet | inbound_mixin.py | packing.get('bag_count') or fallback 5곳 제거 |
| ① | | inbound_preview.py | dict 키 bag_count → mxbg_pallet |
| ① | | export_mixin.py | dict 키 bag_count → mxbg_pallet |
| ② | invoice_no → salar_invoice_no | inbound_mixin.py | fallback 2곳 제거, key 목록에서 삭제 |
| ② | | onestop_inbound.py | 중복 invoice_no 키 삭제 |
| ② | | document_models.py | 주석 명시 |
| ③ | total_weight_kg → net_weight | inbound_mixin.py | or packing.get('total_weight_kg') 4곳 제거, gross_weight_kg fallback도 함께 제거 |

**제거된 fallback 코드 예시 (v5.6.3 → v5.6.6)**

```python
# 수정 전 (v5.6.3)
bag_count = packing.get('bag_count') or packing.get('mxbg_pallet')
weight = packing.get('net_weight') or packing.get('total_weight_kg')
invoice = packing.get('salar_invoice_no') or packing.get('invoice_no', '')

# 수정 후 (v5.6.6)
bag_count = packing.get('mxbg_pallet')
weight = packing.get('net_weight')
invoice = packing.get('salar_invoice_no', '')
```

**추가(기존 검토)**  
- ~~**출고 전**: import_handlers process_outbound 시그니처 수정~~ → **v5.7.6 완료**.  
- ~~**적절한 시점**: safe_int common 단일 소스~~ → **적용 완료** (helpers에서 common re-export).  
- ~~**버전 fallback**~~ → **적용 완료** (전체 fallback 0.0.0 + APP_NAME 통일).  
- ~~**safe_date 용도별 정리**~~ → **적용 완료** (helpers.safe_date_to_date, safe_utils.safe_date_str 별칭·docstring).  
- ~~**메시지박스 통일**~~ → **적용 완료** (직접 messagebox 호출 8곳 → CustomMessageBox).

**v5.7.8 출고 전 필수 정리**  
- ~~**샘플 1kg 정합성**~~ → crud_mixin에서 `SAMPLE_WEIGHT_KG` 상수 단일 사용.  
- ~~**상태 체계**~~ → outbound_mixin에서 `STATUS_AVAILABLE`/`STATUS_PICKED`/`STATUS_DEPLETED` 상수 사용, constants에 출고 흐름 주석.  
- ~~**constants 통합**~~ → GUI constants에서 DEFAULT_WAREHOUSE/DEFAULT_TONBAG_COUNT를 engine re-export.  
- ~~**config 분할**~~ → SQL 호환 함수를 `config_sql.py`로 분리.  
- ~~**safe_float 통합**~~ → onestop_inbound 로컬 `_safe_float` 제거, `utils.common.safe_float` 사용.  
- **validate_lot 출처**: 출고/엔진 코드에서는 `engine_modules.validators.validate_lot_no` 사용 권장 (helpers.validate_lot_no는 GUI 간단 검증용).

---

## 6. 전체 디버깅 리스크 요약표

| 구분 | 항목 수 | 대표 리스크 |
|------|--------|-------------|
| 🔴 높음 | 0 | — |
| 🟡 중간 | 5 | 톤백 번호(보류), 고객명(v5.7.0), safe_*/버전·상수·메시지박스 |
| 🟢 정상 | 7 | LOT, 무게 3종, v5.6.3 톤백 무게, **v5.6.6 톤백 수·Invoice·무게 전달 통일**, **v5.7.6 process_outbound 시그니처 수정(import_handlers)** |
| ⬜ 보류 | 1 | 톤백 번호(sub_lt vs tonbag_no vs tonbag_uid) |
| 데드코드 | 테이블 3, 파일 1, 컬럼 4 | picking_list_*, tonbag_mapping_history, inbound_preview.py, eta_busan 등 |

---

## 7. 출고 로직 진입 전 통합 체크리스트

- [x] **변수 단일화 (v5.6.6) — 완료**  
  - 톤백 수: packing.get('mxbg_pallet')만 사용, bag_count fallback 제거.  
  - Invoice: salar_invoice_no만 사용, invoice_no fallback·중복 키 제거.  
  - 무게 전달: packing.get('net_weight')만 사용, total_weight_kg·gross_weight_kg fallback 제거.
- [x] **출고 API (v5.7.6) — 완료**  
  - import_handlers: process_outbound(allocation_data) 형태로 수정. LOT 전량 출고 시 current_weight 조회 후 allocation_data 구성.
- [ ] **출고와 함께 (v5.7.0)**  
  - 고객명(sold_to/picked_to/customer) 표준화.
- [x] **함수/모듈 (적절한 시점) — 완료**  
  - safe_int common 단일 소스; safe_date 용도별 구분(safe_date_to_date / safe_date_str).  
  - 버전 fallback·상수 단일 소스(version.py, engine re-export); 메시지박스 CustomMessageBox 통일.  
  - onestop_inbound: core.types.safe_float 사용(로컬 _safe_float 없음). GUI 상수: core.constants re-export만 사용.
- [ ] **데드코드**  
  - picking_list_*, tonbag_mapping_history, inbound_preview.py, 미사용 컬럼에 대해 제거/복구/ deprecated 결정.

---

## 8. 최종 종합 검토 (출고 전 현재 상태)

아래는 **현재 코드베이스 기준** 재검색 결과입니다. 출고 로직 진입 전 마지막 점검용으로 참고하세요.

### 8.1 이미 정리된 항목 (추가 변경 불필요)

| 항목 | 확인 내용 |
|------|------------|
| **톤백 수 / Invoice / 무게 전달** | `packing.get('bag_count')`, `packing.get('invoice_no')`, `packing.get('total_weight_kg')` **전역 0건** — v5.6.6 반영 유지. |
| **출고 API** | import_handlers는 `process_outbound(allocation_data)` 호출, current_weight 조회 후 allocation_data 구성 — v5.7.6 반영 유지. |
| **safe_int** | utils/common(core.types) 단일 소스, helpers는 re-export 또는 common 사용으로 통일. |
| **safe_date** | 용도별 구분(safe_date_to_date / safe_date_str) 적용 완료. |
| **safe_float** | onestop_inbound는 `core.types.safe_float` 사용. 로컬 _safe_float 없음. |
| **버전/앱명** | version.py 단일 소스, fallback 통일 완료. |
| **상수 DEFAULT_WAREHOUSE 등** | gui_bootstrap은 core.constants에서만 re-export(로컬 fallback 제거). 단일 소스 유지. |
| **메시지 박스** | CustomMessageBox 통일 적용. (내부에서 messagebox 호출하는 것은 설계상 정상.) |

### 8.2 참고만 할 항목 (의도적 구분·별도 정리)

| 구분 | 내용 | 위치/비고 |
|------|------|------------|
| **용어(참고)** | **lot_no / lot_number / lotno** | DB·엔진은 lot_no. `lot_numbers`는 Invoice 등에서 "LOT 번호 리스트" 의미로 사용(의도적). 컬럼 매핑/엑셀에서 lotno 별칭 사용. |

### 8.3 출고 로직 시 권장

- **변수/키**: 출고 경로에서는 `lot_no`, `weight_kg`/`qty_mt`, `customer`/`sale_ref`, 톤백은 `sub_lt` + `tonbag_compat` 헬퍼 사용 — 기존 문서와 동일.
- **엔진 호출**: `process_outbound(allocation_data)` 또는 `process_outbound_safe(allocation_data)`만 사용.

이 문서는 **DEBUGGING_RISK_OVERVIEW**로, 출고 로직 코딩 전 우선순위와 범위 결정용으로 사용할 수 있습니다. 상세 내용은 `REVIEW_DUPLICATES_AND_OUTBOUND_ENTRY.md`를 참고하면 됩니다.
