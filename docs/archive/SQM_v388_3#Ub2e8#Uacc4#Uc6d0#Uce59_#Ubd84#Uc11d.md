# SQM v3.8.8 — 3단계 원칙 기준 분석

> 📅 2026-02-08 | Ruby 종합 분석

---

## Level 1: Core Principles (절대 규칙)

> 위반 시 데이터 손실, 크래시, 보안 사고 발생. 반드시 준수해야 함.

---

### CP-1. 데이터 무결성 — 무게 정합성

**규칙**: `initial_weight = current_weight + picked_weight` (항상)

| 검사 항목 | 현재 상태 | 판정 |
|-----------|----------|------|
| 입고 시 initial = current 설정 | `inbound_mixin.py:211-212` — `initial_weight: weight, current_weight: weight` | ✅ 준수 |
| 출고 시 current 감소 + picked 증가 | `outbound_mixin.py:266-267` — `MAX(0, current-?), picked+?` | ✅ 준수 |
| 반품 시 current 복원 + picked 감소 | `return_mixin.py:163-165` — `current+?, MAX(0, picked-?)` | ✅ 준수 |
| 음수 방지 (CHECK 제약) | `database.py:709-711` — `CHECK(current_weight >= 0)` | ✅ 준수 |
| SQL MAX(0) 보호 | 출고 4곳, 반품 1곳 모두 `MAX(0, ...)` 사용 | ✅ 준수 |
| 자동 정합성 검증 | `integrity_mixin.py:31` — 출고/반품 후 자동 호출 | ✅ 준수 |

**Ruby 평가**: ✅ **완벽 준수.** 무게 정합성은 이 프로그램에서 가장 잘 구현된 부분.

---

### CP-2. 트랜잭션 원자성 (All-or-Nothing)

**규칙**: LOT + 톤백 10개가 반드시 함께 성공하거나 함께 실패해야 함

| 검사 항목 | 현재 상태 | 판정 |
|-----------|----------|------|
| 입고: `with self.db.transaction()` | `inbound_mixin.py:96` — LOT INSERT + 톤백 INSERT가 한 트랜잭션 | ✅ 준수 |
| 출고: `with self.db.transaction()` | `outbound_mixin.py:207` — 톤백 UPDATE + LOT UPDATE가 한 트랜잭션 | ✅ 준수 |
| 반품: `with self.db.transaction("IMMEDIATE")` | `return_mixin.py:109` — 톤백 복원 + LOT 복원이 한 트랜잭션 | ✅ 준수 |
| 원스톱 입고 다이얼로그 | `onestop_inbound.py:708-710` — 외부에서 `begin_transaction` 시도 | ⚠️ 이중 트랜잭션 위험 |

**⚠️ 문제 발견**: `_save_to_db()`에서 `self.engine.db.begin_transaction()` (708행) + 각 LOT마다 `engine.process_inbound()` 내부의 `with self.db.transaction()` (96행) = **이중 트랜잭션**. SQLite는 중첩 트랜잭션을 지원하지 않으므로, 외부 begin_transaction이 무시되거나 내부 트랜잭션이 개별 커밋됨.

**실제 동작**: 20 LOT 중 15번째에서 에러 → 1~14번은 이미 커밋됨 → All-or-Nothing 위반 가능

---

### CP-3. NOT NULL 필수 필드 보호

**규칙**: `lot_no`는 절대 NULL/빈값이면 안 됨 (DB UNIQUE NOT NULL)

| 검사 항목 | 현재 상태 | 판정 |
|-----------|----------|------|
| DB 제약 | `database.py:691` — `lot_no TEXT NOT NULL UNIQUE` | ✅ |
| 입고 검증 | `inbound_mixin.py:71` — `if not packing.get('lot_no'): return error` | ✅ |
| PackingData 래핑 제거 | `inbound_mixin.py:50-66` — v3.8.8에서 dict 직접 사용 | ✅ 수정됨 |
| 중복 체크 | `inbound_mixin.py:91` — `_check_lot_exists(lot_no)` | ✅ |
| 원스톱 중복 체크 | `onestop_inbound.py:610-628` — 업로드 전 DB 조회 | ✅ 추가됨 |

**Ruby 평가**: ✅ **수정 후 준수.** v3.8.8 이전에는 PackingData 래핑으로 lot_no 누락이 발생했으나 현재 해결됨.

---

### CP-4. SQL 인젝션 방지

**규칙**: 사용자 입력은 반드시 파라미터 바인딩 (?) 사용

| 검사 항목 | 현재 상태 | 판정 |
|-----------|----------|------|
| 재고 조회 | `query_mixin.py:44-64` — 파라미터 바인딩 사용 | ✅ |
| LOT INSERT | `inbound_mixin.py:273` — `f"INSERT INTO inventory ({columns})"` | ⚠️ 주의 |
| 검색 필터 | `toolbar_mixin.py:437` — `f"SELECT DISTINCT {field}"` | ⚠️ 주의 |

**⚠️ 부분 위험**: `_insert_lot`에서 `columns`는 lot_data.keys()에서 온 것이므로 사용자 입력이 아님. 하지만 `toolbar_mixin.py:437`의 `{field}`는 코드 내부 상수이므로 실제 인젝션 위험은 낮음. **단, 코드 리뷰 관점에서 화이트리스트 검증이 없음.**

---

### CP-5. 에러 시 크래시 방지

**규칙**: 어떤 에러가 발생해도 프로그램이 죽으면 안 됨

| 검사 항목 | 현재 상태 | 판정 |
|-----------|----------|------|
| bare except 사용 | 0건 — 모든 except가 구체적 예외 타입 지정 | ✅ |
| 위젯 파괴 후 접근 | `onestop_inbound.py` — `winfo_exists()` 체크 추가 | ✅ 수정됨 |
| 누락 모듈 import | `custom_messagebox.py` — v3.8.8에서 생성 | ✅ 수정됨 |
| 파서 객체 속성 미존재 | `getattr()` 전환 — **부분 완료** | ⚠️ 미완 |

**⚠️ 남은 위험**: `onestop_inbound.py`의 `_merge_results` (459행)에서 아직 `pl.lots`, `invoice.lot_numbers`, `bl.ship_date`, `do.bl_no` 등이 **getattr 없이 직접 접근** 중. 파서 결과가 예상과 다른 구조일 때 `AttributeError` 크래시 가능.

---

## Level 2: Best Practices (권장 규칙)

> 위반해도 당장 크래시는 안 나지만, 유지보수와 안정성에 영향.

---

### BP-1. import 경로 통일

**현재 상태**: `CustomMessageBox` import가 3가지 경로 혼재

```
경로 A: from ..utils.custom_messagebox import CustomMessageBox    (7곳)
경로 B: from gui_app_modular.dialogs.custom_messagebox import ...  (6곳)
경로 C: from .utils.custom_messagebox import ...                   (1곳)
경로 D: from gui_app_modular.utils.custom_messagebox import ...    (1곳)
```

**권장**: 하나의 정규 경로만 사용. `from ..utils.custom_messagebox import CustomMessageBox`로 통일 권장.

**현재 동작**: 양쪽에 파일이 있으므로 **모두 동작하지만**, 새 기능 추가 시 어느 경로를 써야 하는지 혼란 발생.

---

### BP-2. 로깅 일관성

| 패턴 | 사용 빈도 | 평가 |
|------|----------|------|
| `logger.info(...)` | 엔진 모듈 전체 | ✅ 표준 |
| `logger.error(..., exc_info=True)` | 중요 에러에 사용 | ✅ 스택트레이스 포함 |
| `self._log_safe(...)` | onestop_inbound UI 로그 | ✅ UI 표시용 |
| `except Exception: pass` | 3곳 (inbound_mixin:262, integrity:316,344) | ❌ 에러 무시 |

**❌ 문제**: `inbound_mixin.py:262`에서 `except (ValueError, TypeError): pass` — free_time 계산 실패를 조용히 무시. 디버깅 시 왜 free_time이 0인지 알 수 없음.

**권장**: 최소한 `logger.debug(f"free_time 계산 실패: {e}")` 추가.

---

### BP-3. 함수 크기 제한

| 파일 | 함수 | 줄 수 | 평가 |
|------|------|-------|------|
| `onestop_inbound.py` | `_save_to_db` | ~160줄 | ❌ 너무 김 |
| `onestop_inbound.py` | `_merge_results` | ~110줄 | ⚠️ 분리 권장 |
| `inbound_processor.py` | 전체 | 1,155줄 | ❌ 모듈 분리 필요 |
| `toolbar_mixin.py` | `_show_search_popup` | ~100줄 | ⚠️ 별도 다이얼로그 권장 |

**권장**: 함수당 50줄 이하. `_save_to_db`는 "packing_dict 생성" + "DB 호출" + "결과 처리"로 3개 함수로 분리 권장.

---

### BP-4. 타입 힌트

| 모듈 | 타입 힌트 사용 | 평가 |
|------|---------------|------|
| `engine_modules/` | `-> Dict`, `-> List[Dict]`, `-> bool` 사용 | ✅ |
| `gui_app_modular/` | 대부분 없음 | ❌ |
| `parsers/` | dataclass 사용 (자동 타입) | ✅ |

**권장**: 최소한 `process_inbound`, `pick_tonbags`, `process_return` 같은 핵심 함수의 파라미터에 타입 힌트 추가.

---

### BP-5. 테스트 커버리지

| 모듈 | 테스트 | 평가 |
|------|--------|------|
| `engine_modules/` | 2,082개 테스트 | ✅ 우수 |
| `parsers/` | 파싱 테스트 존재 | ✅ |
| `gui_app_modular/` | GUI 테스트 없음 | ❌ 취약 |
| `onestop_inbound` 통합 테스트 | 없음 | ❌ 가장 위험 |

**❌ 핵심 문제**: `onestop_inbound.py` (983줄)는 **테스트 없이** 파싱 → 병합 → 미리보기 → DB 업로드 전체를 담당. 이 파일에서 발생한 에러가 v3.8.8 디버깅의 80%를 차지.

---

### BP-6. 설정값 하드코딩 방지

| 하드코딩 | 위치 | 권장 |
|----------|------|------|
| `'광양'` (기본 창고) | `inbound_mixin.py:217`, `onestop_inbound.py:766` | config.py로 이동 |
| `'LITHIUM CARBONATE'` (기본 제품) | `onestop_inbound.py:449,754` | 상수 정의 |
| `10` (기본 톤백 수) | `onestop_inbound.py:759` | 상수 정의 |
| `0.5` (무게 허용 오차 kg) | `integrity_mixin.py:70` | 상수 정의 |
| UI 색상 코드 | 여러 곳에 분산 | `ui_constants.py`로 통합 |

---

## Level 3: Project Conventions (SQM 프로젝트 전용 룰)

> SQM 프로그램 특유의 비즈니스 로직 규칙.

---

### PC-1. LOT 번호 형식

**규칙**: SQM LOT 번호는 `112xxxxxxx` 형태의 10자리 숫자

| 검사 항목 | 현재 상태 | 판정 |
|-----------|----------|------|
| 길이 검증 | `inbound_mixin.py:78` — `len(lot_no) > 30` 최대만 검사 | ⚠️ 느슨 |
| 형식 검증 | 없음 — 알파벳도 통과 | ❌ 미구현 |
| DB 제약 | `lot_no TEXT NOT NULL UNIQUE` — 텍스트 타입만 | ⚠️ 형식 미검증 |

**권장**: `re.match(r'^\d{10}$', lot_no)` 정규식 검증 추가. "1125081447" 형태만 허용.

---

### PC-2. 톤백 수량 = MXBG

**규칙**: 1 LOT = mxbg_pallet개 톤백 (보통 10개)

| 검사 항목 | 현재 상태 | 판정 |
|-----------|----------|------|
| 입고 시 톤백 생성 | `inbound_mixin.py:113` — `bag_count > 0` 이면 자동 생성 | ✅ |
| 톤백 수 검증 | `integrity_mixin.py:40` — `톤백 총수 = mxbg_pallet (경고)` | ✅ 경고만 |
| 톤백 무게 균등 배분 | `inbound_mixin.py:117` — `per_bag = total_w / bag_count` | ✅ |

**Ruby 평가**: ✅ 준수. 다만 실제 톤백 무게는 균등하지 않을 수 있음 (향후 개별 무게 입력 기능 검토).

---

### PC-3. 출고 3단계 (PICKED → CONFIRMED → SHIPPED)

**규칙**: 출고는 3단계 워크플로우

| 검사 항목 | 현재 상태 | 판정 |
|-----------|----------|------|
| PICKED 상태 전이 | `outbound_mixin.py:231` — `status='PICKED'` | ✅ |
| CONFIRMED 상태 전이 | 코드에서 CONFIRMED 사용 확인 | ✅ |
| SHIPPED 상태 전이 | `integrity_mixin.py:81` — `SHIPPED` 포함 집계 | ✅ |
| 역방향 전이 금지 | `return_mixin.py:132` — `PICKED`만 반품 가능 | ✅ |

---

### PC-4. B/L 번호 형식

**규칙**: B/L 번호에서 "MAEU" 등 선사 코드 포함, 공백 제거

| 검사 항목 | 현재 상태 | 판정 |
|-----------|----------|------|
| `_format_bl()` | `onestop_inbound.py` — 공백/줄바꿈 제거 | ✅ |
| 표시 형식 | `MAEU258468669` 형태 유지 | ✅ |

---

### PC-5. ship_date 우선순위

**규칙**: B/L의 "Shipped on Board Date" > Invoice의 "FECHA"

| 검사 항목 | 현재 상태 | 판정 |
|-----------|----------|------|
| `_merge_results` | B/L ship_date 우선, Invoice fallback | ✅ v3.8.8 수정 |
| `_save_to_db` | B/L 우선 적용 | ✅ |

---

### PC-6. Free Time 계산

**규칙**: `free_time = free_time_date - arrival_date` (일수)

| 검사 항목 | 현재 상태 | 판정 |
|-----------|----------|------|
| D/O에서 추출 | `onestop_inbound.py:718-743` — `free_time_date - arrival` | ✅ |
| 음수 방지 | `if _free_time < 0: _free_time = 0` | ✅ |
| 엔진에서도 계산 | `inbound_mixin.py:246-264` — 이중 계산 | ⚠️ 중복 |

**⚠️ 주의**: free_time이 `_save_to_db`에서 한번 계산되고, `_prepare_lot_data`에서 또 계산됨. 우선순위가 불명확할 수 있음.

---

### PC-7. 한국어 UI + UTF-8

**규칙**: 모든 텍스트 한국어, 파일 인코딩 UTF-8

| 검사 항목 | 현재 상태 | 판정 |
|-----------|----------|------|
| GUI 텍스트 | 한국어 + 이모지 | ✅ |
| 폰트 | `맑은 고딕` 기본 | ✅ |
| 파일 인코딩 | `# -*- coding: utf-8 -*-` 일부 파일에만 | ⚠️ 불완전 |
| 배치 파일 | `chcp 65001` (UTF-8) | ✅ |

---

## 종합 점수표

| 카테고리 | 항목 수 | ✅ 준수 | ⚠️ 부분 | ❌ 미준수 |
|----------|---------|---------|---------|----------|
| **Core Principles** | 5 | 3 | 2 | 0 |
| **Best Practices** | 6 | 2 | 1 | 3 |
| **Project Conventions** | 7 | 5 | 2 | 0 |
| **합계** | **18** | **10** | **5** | **3** |

---

## 우선순위별 조치 사항

### 🔴 즉시 수정 (Core Principle 위반)

1. **CP-2 이중 트랜잭션**: `onestop_inbound.py:708`의 `begin_transaction()` 제거. `process_inbound` 내부 트랜잭션에 위임.
2. **CP-5 getattr 미완**: `_merge_results`의 `pl.lots`, `invoice.lot_numbers`, `bl.ship_date`, `do.bl_no`를 모두 `getattr()` 변환.

### 🟡 조기 수정 (Best Practice 위반)

3. **BP-2**: `except: pass` 3곳에 `logger.debug` 추가.
4. **BP-1**: import 경로 `..utils.custom_messagebox`로 통일.
5. **BP-6**: `'광양'`, `'LITHIUM CARBONATE'`, `10` 등 하드코딩을 상수로 정의.

### 🟢 점진 개선 (Convention 개선)

6. **PC-1**: LOT 번호 10자리 정규식 검증 추가.
7. **PC-6**: free_time 계산 중복 제거 (엔진 측에서만 계산).
8. **BP-3**: `_save_to_db`를 3개 함수로 분리.
9. **BP-5**: `onestop_inbound.py` 통합 테스트 작성.
