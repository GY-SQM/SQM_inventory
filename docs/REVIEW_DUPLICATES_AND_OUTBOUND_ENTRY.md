# 출고 로직 전 중복·혼용 종합 검토

> **목적**: 출고 로직 수정/추가 전, 변수·함수·모듈의 중복·혼용을 정리하여 단일 소스(SSOT) 및 호출 규칙을 명확히 함.  
> **작성일**: 2026-02-16  
> **코딩**: 검토만 수행, 수정은 별도 진행 예정.

---

## 1. 요약 (Executive Summary)

| 구분 | 내용 |
|------|------|
| **safe_*** | `safe_int` 2곳, `safe_date` 2곳(반환 타입·시그니처 상이) |
| **버전/앱명** | `version.py`가 원천이나, fallback이 여러 파일에 분산·값 상이 |
| **상수** | `DEFAULT_WAREHOUSE`, `DEFAULT_TONBAG_COUNT` 등이 engine_modules.constants와 gui constants에 중복 |
| **메시지박스** | CustomMessageBox(utils) vs tkinter.messagebox 혼용; CustomMessageBox 파일 2개(실구현 1 + re-export 1) |
| **출고 API** | `process_outbound(allocation_data)`만 정의됨. `import_handlers`는 `process_outbound(lot_no, destination)` 호출 → **시그니처 불일치(버그)** |
| **용어** | LOT(lot_no/lot_number/lotno), 톤백(sub_lt/tonbag_no/tonbag_no_print), 무게(weight/current_weight/balance 등) 혼용 |

---

## 2. 함수 중복·혼용

### 2.1 safe_* 함수

| 함수 | 위치 | 비고 |
|------|------|------|
| **safe_float** | `utils/common.py` | 단일 소스. parsers, safe_utils, helpers에서 사용/재export |
| **safe_str** | `utils/common.py` | 단일 소스 |
| **safe_int** | `utils/common.py` | **중복**: `gui_app_modular/utils/helpers.py`에 별도 구현 (int(float(value)) 방식). common은 쉼표/공백/하이픈 처리 등 더 보수적 |
| **safe_date** | **2곳, 시그니처·반환 타입 다름** | ① `helpers.py`: `(value, default=None) -> Optional[date]` (date 객체 반환) ② `safe_utils.py`: `(val, default='', output_format='%Y-%m-%d') -> str` (포맷 문자열 반환). 호출부에 따라 “날짜 객체 필요” vs “문자열 필요” 구분 필요 |

**권장**:  
- `safe_int`: 전역적으로 `utils.common.safe_int`만 사용하고, helpers의 `safe_int`는 제거 또는 common 재사용으로 통일.  
- `safe_date`:  
  - 날짜 **객체**가 필요하면 `helpers.safe_date` (또는 공통 모듈 하나로 통합 시 `safe_date_to_object`).  
  - **문자열**이 필요하면 `safe_utils.safe_date` (또는 통합 시 `safe_date_to_str`).  
  - 장기적으로 한 모듈에서 `safe_date_object` / `safe_date_str` 두 함수로 나누고, 기존 두 곳은 이를 쓰도록 정리 권장.

---

## 3. 버전·앱명·상수

### 3.1 버전 / 앱명

- **단일 소스**: `version.py` (`__version__`, `APP_NAME`, `APP_NAME_EN`).
- **Fallback 분산**:  
  - `run_app.py`, `config.py`, `gui_app_modular/utils/constants.py`, `engine_modules/__init__.py`, `parsers/__init__.py` 등에서 import 실패 시 각각 다른 fallback 값 사용 (예: 3.8.7, 3.9.2, 3.9.4, 3.9.8 등).
- **권장**:  
  - 버전/앱명은 `version.py`만 참조.  
  - Fallback이 꼭 필요하면 한 곳(예: `config.py` 또는 `version.py` 내부)에서만 정의하고 나머지는 그곳을 import.

### 3.2 비즈니스 상수 (DEFAULT_WAREHOUSE 등)

| 상수 | engine_modules.constants | gui_app_modular.utils.constants |
|------|---------------------------|----------------------------------|
| DEFAULT_WAREHOUSE | ✅ '광양' | ✅ '광양' (중복) |
| DEFAULT_TONBAG_COUNT | ✅ 10 | ✅ 10 (중복) |
| SAMPLE_WEIGHT_KG | ✅ 1.0 | (없음) |
| STATUS_AVAILABLE 등 | ✅ | (없음) |
| WEIGHT_TOLERANCE_KG | (없음) | ✅ 0.5 |
| DEFAULT_PRODUCT | (없음) | ✅ 'LITHIUM CARBONATE' |

- **권장**:  
  - 재고/출고/입고 엔진 쪽은 `engine_modules.constants`를 단일 소스로 사용 (이미 inbound_mixin 등이 사용).  
  - GUI 기본값만 필요하면 `gui_app_modular.utils.constants`는 “GUI용 기본값”으로 두되, 가능하면 engine constants를 re-export하거나, 최소한 DEFAULT_WAREHOUSE 등은 engine에서만 정의하고 GUI는 거기서만 가져오도록 정리.

---

## 4. 메시지 박스

- **CustomMessageBox**  
  - **실구현**: `gui_app_modular/utils/custom_messagebox.py`  
  - **re-export**: `gui_app_modular/dialogs/custom_messagebox.py` → `from gui_app_modular.utils.custom_messagebox import CustomMessageBox`  
  - **노출**: `gui_app_modular/utils/ui_constants.py`에서 lazy import로 `CustomMessageBox` 제공 (이름으로 접근 시 .custom_messagebox에서 로드)
- **혼용**:  
  - 일부 코드는 `CustomMessageBox.showinfo/showwarning/...` 사용.  
  - 일부는 `tkinter.messagebox.showwarning`, `askyesno` 등 직접 사용.
- **AGENTS.md**: 에러 시 `CustomMessageBox.show_detailed_error()` 사용 권장.
- **권장**:  
  - 사용자 대면 메시지는 가능한 한 `CustomMessageBox`로 통일 (폰트·간격·테마 일관성).  
  - dialogs/custom_messagebox.py는 호환용 re-export로 유지해도 되나, 새 코드는 `utils.custom_messagebox` 또는 `ui_constants` 경로로 통일.

---

## 5. 출고 관련 API·진입점 (중요)

### 5.1 process_outbound 시그니처

- **엔진 정의**  
  - `engine_modules/inventory_modular/outbound_mixin.py`:  
    - `process_outbound(self, allocation_data) -> Dict`  
  - `allocation_data`: dict 1건 또는 dict 리스트. 각 dict는 최소 `lot_no`, `weight_kg`(또는 `qty_mt`), 선택 `customer`/`sold_to`, `sale_ref` 등.
- **Preflight**  
  - `process_outbound_safe(self, allocation_data, strict=True)`: 동일한 allocation_data 형식.

### 5.2 호출부 정리

| 호출 위치 | 호출 방식 | 비고 |
|-----------|-----------|------|
| outbound_handlers.py | `process_outbound(allocation_items)` 리스트 전달 | ✅ 올바름 |
| outbound_handlers.py | `process_outbound(alloc)` 단일 dict | ✅ 올바름 (내부에서 list화) |
| features_v2_mixin.py | `process_outbound(batch_items)` | ✅ 올바름 |
| simple_excel_outbound.py | `process_outbound({ lot_no, weight_kg, customer, sale_ref })` | ✅ 올바름 |
| **import_handlers.py** | **`process_outbound(lot_no, destination)`** | ❌ **시그니처 불일치** |

- **import_handlers 문제**:  
  - `process_outbound(lot_no, destination)`로 호출하고 있으나, 엔진은 `(allocation_data)` 하나만 받음.  
  - 이렇게 넘기면 `allocation_data = lot_no`(문자열)가 되어, `list(allocation_data)`는 문자의 리스트가 되고, `alloc.get('lot_no')` 등에서 예외 또는 잘못된 동작 발생.  
- **권장**:  
  - “Excel에서 lot_no + destination(고객)만 있는 출고”를 처리하려면,  
    - `weight_kg`를 정책에 따라 결정(예: LOT 전량 출고 시 current_weight 사용)한 뒤,  
    - `process_outbound([{'lot_no': lot_no, 'weight_kg': weight_kg, 'customer': destination}])` 형태로 호출하도록 수정 필요.  
  - 또는 엔진에 “lot_no + destination만 받는” 편의 API를 하나 두고, 그 API가 내부에서 allocation_data를 만들어 `process_outbound`/`process_outbound_safe`를 호출하도록 할 수 있음.

### 5.3 출고 UI/진입점 분포

- **톤백 탭**: `tonbag_tab.py` — “출고 처리” 버튼 → `do_outbound()` (대화상자에서 출고처 입력 후 엔진 호출).
- **드래그드롭**: `drag_drop_mixin.py` — “출고 (톤백 PICK)” → `do_outbound()`.
- **핸들러**:  
  - `outbound_handlers.py`: Allocation 기반 출고, `process_outbound_safe` 우선 시도 후 `process_outbound` fallback.  
  - `simple_excel_outbound.py`: Excel 기반 출고 실행.  
  - `import_handlers.py`: Excel 가져오기 중 “출고” 처리 (위 시그니처 버그 있음).
- **미리보기/다이얼로그**: `outbound_preview_dialog.py`, `allocation_preview.py` 등.

출고 로직 코딩 시 위 진입점들이 모두 동일한 allocation_data 형식과 `process_outbound`/`process_outbound_safe` 규칙을 따르도록 맞추는 것이 안전함.

---

## 6. 용어·변수 혼용 (출고 시 기준으로 정리할 것)

### 6.1 LOT

- **표기**: `lot_no`, `lot_number`, `lotno` 등이 여러 파일에 혼재.
- **권장**: DB·엔진·출고 로직은 **`lot_no`**를 기준 키로 사용 (이미 outbound_mixin, DB 스키마가 lot_no 사용). 신규 코드는 `lot_no`만 사용하고, 파서/Excel 등에서 `lot_number`/`lotno`는 입구에서만 `lot_no`로 매핑.

### 6.2 톤백 번호

- **표기**: `sub_lt`, `tonbag_no`, `tonbag_no_print` (표시용).
- **정리**:  
  - `engine_modules/tonbag_compat.py`: `get_tonbag_display_no(row)`, `get_tonbag_uid(row)`에서 `tonbag_no` / `sub_lt` / `tonbag_no_print`를 함께 처리.  
  - DB/엔진은 `sub_lt`(숫자), 표시/Excel은 `tonbag_no`/`tonbag_no_print`와 매핑.
- **권장**:  
  - 내부 처리·출고 로직은 `sub_lt`(또는 엔진이 정한 하나의 키)를 기준으로 하고,  
  - 대외 표시/Excel 헤더는 `tonbag_no_print` 또는 `get_tonbag_display_no()` 결과를 사용하도록 문서화.

### 6.3 무게·잔량

- **표기**: `weight`, `net_weight`, `current_weight`, `balance`, `weight_kg`, `qty_mt` 등.
- **권장**:  
  - 출고 단위는 **kg** 기준이면 `weight_kg`, **MT**면 `qty_mt`로 통일 (outbound_mixin이 둘 다 받아 변환).  
  - 재고 “잔량”은 엔진/DB 컬럼명(`current_weight` 등)을 그대로 쓰되, 한 모듈 내에서는 한 가지 이름만 사용하도록 주의.

---

## 7. 기타 모듈·역할

- **document_parser_v2 / document_parser_modular**:  
  - document_parser_v2가 V3 모듈의 래퍼. 입고 문서 파싱은 V3 모듈을 사용하도록 일원화되어 있음.  
- **allocation_parser**:  
  - 출고/Allocation Excel 파싱. outbound_handlers 등에서 사용.  
- **CustomMessageBox**:  
  - 구현 1곳(utils), re-export 1곳(dialogs). 위 4절 참고.

---

## 8. 출고 로직 작업 시 체크리스트

- [ ] **process_outbound**  
  - 모든 호출이 `(allocation_data)` 한 인자만 사용하는지 확인.  
  - **import_handlers**의 `(lot_no, destination)` 호출을 allocation_data 리스트/딕셔너리로 변경.
- [ ] **safe_date**  
  - 날짜 객체 필요 시 helpers, 문자열 필요 시 safe_utils 사용 구분 확인 후, 필요 시 함수명/모듈 통합 검토.
- [ ] **safe_int**  
  - helpers 중복 제거 또는 utils.common만 사용하도록 통일.
- [ ] **상수**  
  - 출고/재고 관련 상수는 `engine_modules.constants`에서만 가져오기.
- [ ] **용어**  
  - 출고 경로에서는 `lot_no`, `weight_kg`/`qty_mt`, `customer`/`sale_ref`, 톤백은 `sub_lt`/tonbag_compat 헬퍼 사용으로 통일.
- [ ] **메시지**  
  - 사용자 대면 메시지는 CustomMessageBox로 통일 (특히 에러는 show_detailed_error 권장).

이 문서를 기준으로 출고 로직 코딩 시 SSOT와 호출 규칙을 맞추면, 중복·혼용으로 인한 버그를 줄일 수 있습니다.
