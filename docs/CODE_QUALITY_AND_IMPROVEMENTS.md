# SQM 코드 품질·안정성·개선 제안 종합 보고서

> **목적**: 데드코드 제거·코드품질 향상 중심의 전수 검토 + 안정성·효율성·편리성·추가 기능 제안.  
> **작성일**: 2026-02-16  
> **범위**: DO 후속 연결 메뉴 추가, except+pass 정리, 데드코드·대형 파일·품질 개선 제안.

---

## 1. 적용 완료 사항

### 1.1 DO 후속 연결 메뉴 추가
- **파일**: `gui_app_modular/mixins/custom_menubar.py`, `gui_app_modular/mixins/menu_mixin.py`
- **내용**: "📋 D/O 후속 연결"을 **도구 메뉴**에도 추가. 기존에는 파일 → 입고 서브메뉴에만 있었음.
- **결과**: 사용자가 **파일 → 입고 → D/O 후속 연결** 또는 **도구 → D/O 후속 연결** 두 경로로 접근 가능.

### 1.2 except + pass → logger.debug 변환 (AGENTS.md 준수)
- **onestop_inbound.py**: 진행 팝업 destroy 시 `Exception` / TclError → `logger.debug(f"Suppressed: {e}")`
- **column_toggle.py**: 툴팁 적용 실패 시 `Exception` → `logger.debug(f"Suppressed: {e}")`
- **tree_enhancements.py**: focus_set 실패, apply_tooltip 실패 시 동일 처리
- **theme_mixin.py**: TableStyler 적용 실패 시 (ImportError, Exception) → `logger.debug(f"Suppressed: {e}")`
- **mac_guard.py**: GUI 경고/에러 팝업 표시 실패 시 `Exception` → `logger.debug(f"Suppressed: {e}")`

**유지한 pass**: docstring 예제(`... pass`), 의도적 no-op(theme_mixin의 `try: pass` 구조), database.py 마이그레이션 "이미 존재하면 무시", config 테스트용 `pass`, gemini_chat_query TimeoutError fallback — 변경하지 않음.

### 1.3 두 검토안 총괄 디버깅 (DB 미접촉)

| 항목 | 적용 내용 |
|------|-----------|
| **버전 fallback 단일화** | run_app, gui_app_modular/utils/constants, config, parsers/document_parser_modular/__init__, engine_modules/inventory_modular/__init__, engine_modules/inventory.py — import 실패 시 `__version__ = "0.0.0"`, APP_NAME 통일. version.py 단일 소스 참조. |
| **safe_int 중복 제거** | gui_app_modular/utils/helpers.py — 로컬 safe_int 구현 삭제, `from utils.common import safe_int` re-export. |
| **unused import** | engine_modules/db_migration_mixin.py — `import configparser` 제거 (미사용). |
| **safe_date 용도별 정리** | helpers: docstring + 별칭 `safe_date_to_date = safe_date` (날짜 객체). safe_utils: docstring + 별칭 `safe_date_str = safe_date` (문자열). 서로 docstring으로 상호 참조. |
| **메시지박스 통일** | messagebox 직접 호출 → CustomMessageBox로 교체: onestop_inbound(1), auto_backup(3), gemini_chat_gui(1), ui_ops_helper(1), mac_guard(2). custom_messagebox.py 내부 폴백용 messagebox 호출은 유지. |

---

## 2. 데드코드 현황 및 제안

### 2.1 테이블 (CREATE만 있고 비즈니스 로직 참조 0)

| 테이블 | 위치 | 비고 |
|--------|------|------|
| `picking_list_order` | db_migration_mixin.py | CREATE + 인덱스만. backup_handlers에서 테이블 목록으로만 언급. |
| `picking_list_detail` | 동일 | picking_list_order FK. 실제 INSERT/SELECT 없음. |
| `tonbag_mapping_history` | db_migration_mixin.py | CREATE + 1회 INSERT 코드 있으나, 호출 경로 없음(데드). |

**제안**  
- 출고 기능에서 **피킹 리스트**를 도입할 계획이 있으면: 테이블 유지, 추후 채움.  
- 계획이 없으면: 마이그레이션에서 CREATE 제거 또는 `_DEPRECATED_` 주석 + 문서화.  
- `tonbag_mapping_history`: 호출하는 코드가 없으면 INSERT 블록 제거 또는 "미사용" 주석 처리.

### 2.2 파일
- **inbound_preview.py**: v5.6.5에서 비활성화. 프로젝트 내 파일 없음(이미 제거된 버전으로 추정).  
- **제안**: 다른 브랜치/배포에 있다면 삭제 또는 `_DEPRECATED_` 표시 후 제거.

### 2.3 컬럼 (inventory)
- **eta_busan**: DB 스키마·allocation_parser·import_mixin·query_mixin·utils 등에서 **사용 중**. 데드 아님.  
- **stock_date**: query_mixin, crud_mixin, database, import, pdf_handlers, column_mapper 등에서 **사용 중**. 데드 아님.  
- **condition**: DB 스키마(database.py), crud_mixin 컬럼 목록, import_mixin 별칭에만 등장. **실제 조회/필터/업데이트에서 미사용**일 가능성 있음.  

**제안**  
- `condition`: 사용처가 정말 없으면 마이그레이션에서 deprecated 표시 후 장기적으로 제거 검토.  
- eta_busan, stock_date: 유지.

### 2.4 invoice_no 컬럼
- **salar_invoice_no**와 중복. v5.6.6에서 파서→엔진은 salar_invoice_no만 사용.  
- **제안**: DB 컬럼은 하위 호환용 유지 가능. 신규 코드는 salar_invoice_no만 사용. 필요 시 마이그레이션에서 invoice_no deprecated 주석.

---

## 3. 코드 품질 — 파일 크기 (AGENTS.md: 한 파일 최대 800줄)

| 파일 | 줄 수 | 제안 |
|------|--------|------|
| onestop_inbound.py | ~1348 | 800줄 초과. **입고 UI / 파싱 / 업로드 / 미리보기** 등 기능별 Mixin 또는 모듈 분리 권장. |
| tonbag_tab.py | ~1050 | 800줄 초과. **테이블 구성 / 출고·취소·복사 / 필터·검색** 등 역할별 분리 권장. |
| database.py | ~1317 | 800줄 초과. **마이그레이션 / 스키마 정의 / 연결·트랜잭션** 등 블록별 분리 또는 서브 모듈 권장. |
| pdf_parser.py | ~888 | 800줄 초과. **파싱 단계별** 또는 문서 타입별 모듈 분리 권장. |

**우선순위**: onestop_inbound, tonbag_tab이 UI 변경이 잦으므로 분리 시 유지보수·테스트에 유리.

---

## 4. 안정성·효율성·편리성 제안

### 4.1 안정성
- **트랜잭션**: 입고/출고는 이미 All-or-Nothing·Preflight 적용. 유지.  
- **에러 노출**: CustomMessageBox.show_detailed_error() 사용처 확대(AGENTS.md).  
- **로깅**: except 처리 시 logger.debug/warning/error 명시 — 이번에 일부 반영됨.  
- **타입 힌트**: 핵심 엔진·출고 경로에 인자/반환 타입 보강 시 리팩터 시 안정성 향상.

### 4.2 효율성
- **DB 쿼리**: 자주 쓰는 목록 조회에 인덱스 확인(idx_inventory_*, idx_tonbag_* 등). 이미 다수 존재.  
- **대량 Excel**: 행 수가 많을 때 청크 단위 처리 또는 progress 콜백으로 UI 멈춤 완화 검토.  
- **캐시**: 대시보드/통계 등은 기존 캐시 정책 유지.

### 4.3 편리성
- **D/O 후속 연결**: 도구 메뉴 추가로 진입점 2곳으로 확대 완료.  
- **단축키**: D/O 후속 연결에 단축키(예: Ctrl+Shift+D) 부여 시 편의성 향상.  
- **출고 Excel**: 컬럼 매핑 기본값(lot_no, destination/customer) 저장/불러오기 시 재사용 편의.

---

## 5. 추가 기능 제안 (참고)

| 구분 | 제안 | 비고 |
|------|------|------|
| 출고 | 피킹 리스트 UI | picking_list_* 테이블 활용 시 출고 지시서·피킹 순서 관리. |
| 출고 | LOT 전량 출고 단축 버튼 | 현재 엔진/import_handlers 지원. 톤백 탭 등에서 "선택 LOT 전량 출고" 버튼 노출. |
| 입고 | D/O 없이 입고 후 "D/O 후속 연결" 안내 툴팁 | 원스톱에서 DO 없이 업로드 시, 메뉴 위치 안내 문구. (이미 문구 있음: "나중에 [📋 D/O 후속 연결] 메뉴로 보충할 수 있습니다.") |
| 공통 | 설정에서 버전/상수 단일 소스 표시 | version.py 한 곳만 참조하도록 fallback 정리 후 "이 프로그램 버전" 표시. |
| 품질 | 테스트 커버리지 | 출고·입고·정합성 검사 경로에 단위/통합 테스트 추가. |

---

## 6. 요약 체크리스트

- [x] DO 후속 연결 메뉴 — 도구 메뉴에 추가
- [x] except+pass — onestop_inbound, column_toggle, tree_enhancements, theme_mixin, mac_guard에서 logger.debug로 변환
- [ ] 데드 테이블 — picking_list_*, tonbag_mapping_history: 출고 설계에 따라 유지 또는 제거/주석
- [ ] 대형 파일 — onestop_inbound, tonbag_tab, database, pdf_parser 800줄 이상: 기능별 분리 검토
- [ ] condition 컬럼 — 사용처 확인 후 미사용이면 deprecated 표시
- [ ] 버전/상수 단일 소스 — fallback 정리(기존 DEBUGGING_RISK_OVERVIEW 참고)

이 문서는 **CODE_QUALITY_AND_IMPROVEMENTS**로, 데드코드 제거·코드품질 향상·안정성·효율성·편리성 개선 시 참고용으로 사용할 수 있습니다.
