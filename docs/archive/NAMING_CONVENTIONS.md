# SQM v4.0.4 — 변수명 생성 규칙 (Naming Conventions)

> **(주) 지와이로지스 | 2026-02-09 | Ruby 작성**

---

## 1. 기본 규칙

| 대상 | 규칙 | 예시 |
|------|------|------|
| **변수/함수** | snake_case | `lot_no`, `net_weight`, `parse_invoice()` |
| **클래스** | PascalCase | `InboundMixin`, `DocumentParserV3` |
| **상수** | UPPER_SNAKE | `MAX_WEIGHT_KG`, `DB_PATH` |
| **private 메서드** | _prefix | `_init_database()`, `_validate_lot()` |
| **이벤트 핸들러** | _on_ prefix | `_on_simple_outbound()`, `_on_cancel()` |
| **UI 셋업** | _setup_ prefix | `_setup_dashboard_tab()`, `_setup_toolbar()` |
| **처리 함수** | _process_ prefix | `_process_inbound()`, `_process_return()` |
| **검증 함수** | _validate_ prefix | `_validate_lot_no()`, `_validate_weight()` |
| **마이그레이션** | _migrate_ prefix | `_migrate_v243()` |
| **UI 표시** | _show_ prefix | `_show_return_dialog()`, `_show_lot_detail()` |
| **생성 함수** | _generate_/_export_ | `_generate_report()`, `_export_excel()` |
| **boolean** | is_/has_/can_ | `is_valid`, `has_tonbag`, `can_export` |

## 2. 금지 패턴

| 금지 | 이유 | 대안 |
|------|------|------|
| camelCase 변수 | Python 관례 위반 | snake_case 사용 |
| 단일 문자 변수 (i,j 제외) | 가독성 저하 | 의미 있는 이름 |
| `data`, `info`, `tmp` | 모호함 | 구체적 이름 |
| `process()` (동사만) | 무엇을? | `process_inbound()` |
| `handle()` 단독 | 무엇을? | `handle_outbound_click()` |

## 3. 도메인 변수 표준 (혼동 방지)

### weight 계열

| 변수명 | 의미 | 단위 | 사용처 |
|--------|------|------|--------|
| `net_weight` | 순 중량 (입고 시 기록) | kg | inventory 테이블 |
| `gross_weight` | 총 중량 (포장 포함) | kg | inventory 테이블 |
| `initial_weight` | LOT 초기 입고량 | kg | inventory 테이블 |
| `current_weight` | LOT 현재 잔량 | kg | inventory 테이블 |
| `picked_weight` | 출고 배정된 중량 | kg | 계산값 |
| `available_weight` | 출고 가능 중량 | kg | 계산값 |
| `weight_mt` | MT 단위 표시용 | MT | 화면 표시 |
| `total_weight_kg` | 합산 중량 | kg | 대시보드 |

### date 계열

| 변수명 | 의미 | 비고 |
|--------|------|------|
| `arrival_date` | 입항일 (CY 입고일) | **기준 날짜** |
| `stock_date` | arrival_date 동의어 | DB 호환용 |
| `inbound_date` | arrival_date 동의어 | UI 표시용 |
| `ship_date` | 선적일 | |
| `eta_date` | 도착 예정일 | |
| `outbound_date` | 출고일 | |
| `picked_date` | 피킹일 (출고 배정일) | |
| `return_date` | 반품일 | |

### no (번호) 계열

| 변수명 | 의미 | 형식 |
|--------|------|------|
| `lot_no` | LOT 번호 | 10자리 숫자 |
| `sap_no` | SAP 번호 | 10자리 숫자 |
| `bl_no` | B/L 번호 | 영문숫자 |
| `do_no` | D/O 번호 | 영문숫자 |
| `salar_invoice_no` | SQM Invoice 번호 | |
| `container_no` | 컨테이너 번호 | XXXX0000000 |
| `sub_lt` | 톤백 번호 | 정수 |
| `outbound_no` | 출고 번호 | 자동 생성 |

## 4. 파일명 규칙

| 대상 | 규칙 | 예시 |
|------|------|------|
| Mixin | *_mixin.py | `inbound_mixin.py` |
| Tab | *_tab.py | `dashboard_tab.py` |
| Handler | *_handler.py / *_handlers.py | `outbound_handlers.py` |
| Dialog | *_dialog.py | `settings_dialog.py` |
| 테스트 | test_*.py | `test_inbound.py` |
| 유틸리티 | 단수 명사 | `helpers.py`, `constants.py` |
