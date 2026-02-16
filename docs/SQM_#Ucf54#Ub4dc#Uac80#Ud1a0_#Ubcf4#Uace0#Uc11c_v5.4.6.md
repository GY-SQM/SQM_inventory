# SQM 재고관리 시스템 — 코드 검토 보고서 (v5.4.6 계획서 반영)

> **검토일**: 2026-02-13  
> **기준 문서**: `SQM_개발계획서_v5.4.6.md`  
> **목표**: 디버깅, 안정성·효율성·편리성, 데드코드 제거 및 코드 품질 향상

---

## 1. 적용한 수정 사항

### 1.1 run_app.py (진입점)

| 항목 | 내용 |
|------|------|
| **check_dependencies() 버그 수정** | `try: pass except ImportError`로 인해 pandas, openpyxl, tkinter가 실제로 검사되지 않던 문제 수정. `__import__("pandas")` 등 실제 import로 변경. |
| **--version / --check 옵션 구현** | docstring에만 있던 `--version`, `--check`를 main()에서 처리하도록 추가. `--check` 시 `run_self_diagnostic()` 실행 후 종료. |
| **filelock 점검 로직 수정** | 공유폴더 감지 시 filelock을 import하지 않고 append만 하던 부분을 `__import__("filelock")` 후 메시지 추가로 수정. |
| **AGENTS.md 준수** | Windows drive type 확인 실패 시 `except ... pass` → `logger.debug(f"Suppressed: ... {e}")` 로 변경. `logging` 및 `logger` 추가. |

### 1.2 config.py

- keyring 예외 처리: `except ... pass` → `logger.debug(f"Suppressed: keyring ... {e}")` 로 변경.
- `import logging`, `logger = logging.getLogger(__name__)` 추가.

### 1.3 utils/path_utils.py

- `get_app_base_dir()` 내 두 곳의 `except Exception: pass` → `logger.debug(f"Suppressed: ... {e}")` 로 변경.
- `import logging`, `logger` 추가.

---

## 2. 데드코드 제거 권장

다음 파일/코드는 **어디서도 import되거나 호출되지 않음**. 제거 시 동작 영향 없음.

| 구분 | 경로 | 설명 |
|------|------|------|
| **중복 모듈** | `engine_modules/query_mixin.py` | `engine_modules/inventory_modular/query_mixin.py`와 역할 중복. 앱은 inventory_modular 쪽만 사용. **삭제 권장.** |
| **중복 모듈** | 루트 `toolbar_mixin.py` | `gui_app_modular/mixins/toolbar_mixin.py`와 동일. mixins는 `gui_app_modular.mixins`에서만 import. **삭제 권장.** |

**삭제 시 권장 절차**

1. `engine_modules/query_mixin.py` 삭제 후: `python run_app.py --check` 및 GUI 실행으로 정상 동작 확인.
2. 루트 `toolbar_mixin.py` 삭제 후: 동일하게 실행·탭 동작 확인.

---

## 3. except + pass 잔여 (코드 품질)

AGENTS.md: *"except + pass 사용 금지 → logger.debug(f'Suppressed: {e}') 사용"*

### 3.1 이미 수정한 파일

- `run_app.py`, `config.py`, `utils/path_utils.py` (위 1.1~1.3 반영)

### 3.2 추가 수정 권장 (프로덕션 코드)

테스트(`tests/`) 제외, 실제 앱에서 쓰이는 모듈 중 `except ... pass` 가 있는 곳만 정리.

| 파일 | 대략 위치/용도 | 권장 조치 |
|------|----------------|-----------|
| `utils/backup.py` | 파일명 파싱 실패 | `logger.debug("...", exc_info=True)` 또는 동일 패턴으로 로그 후 진행 |
| `utils/integrity_check.py` | 컬럼 없음 스킵 | `logger.debug("컬럼 없음 스킵: ...")` |
| `utils/ui_debug.py` | 예외 시 | `logger.debug(...)` |
| `parsers/pdf_parser.py` | 예외 무시 다수 | 각각 `logger.debug(f"Suppressed: ... {e}")` 로 치환 |
| `parsers/document_parser_modular/base.py` | 파싱 중 예외 | 로그 추가 후 재발생 또는 스킵 |
| `parsers/allocation_parser.py` | 예외 무시 | `logger.debug(...)` |
| `gui_app_modular/utils/custom_messagebox.py` | 예외 시 | `logger.debug(...)` |
| `gui_app_modular/mixins/theme_mixin.py` | 테마 적용 실패 | `logger.debug(...)` |
| `gui_app_modular/mixins/window_mixin.py` | Optional 모듈 등 | `logger.debug(...)` |
| `gui_app_modular/mixins/toolbar_mixin.py` | UI 복구/위젯 파괴 등 다수 | 의도된 “무시”인 경우만 `logger.debug(...)` 로 통일 |
| `gui_app_modular/main_app.py` | 스타일/엔진 초기화 등 | 동일하게 로그로 대체 |
| `engine_modules/database.py` | 락/마이그레이션 등 | `logger.debug(...)` (이미 로거 있음) |
| `engine_modules/db_migration_mixin.py` | 마이그레이션 스킵 | `logger.debug(...)` |
| `features/ai/gemini_parser.py` | config 없음 등 | `logger.debug(...)` |

테스트 코드(`tests/`) 내 `except ... pass` 는 의도된 예외 무시가 많으므로, 필요 시에만 `logger.debug` 또는 주석으로 “의도”를 남기는 정도로 정리하면 됩니다.

---

## 4. 계획서(SQM_개발계획서_v5.4.6) 대비 검증 요약

| 계획서 항목 | 현재 코드 상태 | 비고 |
|-------------|----------------|------|
| **진입점** | `run_app.py` 단일 진입점, `--version`/`--check`/`--backup`/`--cli` 지원 | 수정으로 --version/--check 동작 확정 |
| **재고 리스트 18컬럼** | `gui_app_modular/tabs/inventory_tab.py` 의 `INVENTORY_COLUMNS` 18개 일치 | 계획서와 일치 |
| **톤백 리스트** | 톤백 전용 탭/리스트 존재 (tonbag_tab 등) | 계획서 21컬럼 개념과 매핑 가능 |
| **DB 스키마** | inventory, inventory_tonbag, outbound 등 계획서 구조와 유사 | 마이그레이션으로 컬럼 추가 반영됨 |
| **All-or-Nothing / Preflight** | PreflightMixin, 트랜잭션 롤백 등 적용 | 계획서 원칙 유지 |
| **무게 공식** | 톤백 개별 = (NET - 1) / mxbg, 샘플 1kg | 계획서와 동일 |
| **테마/설정** | ui_constants, theme_mixin, config (API 키 3단계) | 계획서 Phase 8 방향과 부합 |

전반적으로 계획서 v5.4.6의 구조·용어·Phase 구분과 일치하며, 진입점과 의존성 검사만 위 1.1에서 보강되었습니다.

---

## 5. 안정성·효율성·편리성 — 추가 기능 제안

### 5.1 안정성

- **시작 시 DB/스키마 검증**: `run_self_check()` 또는 `run_self_diagnostic()`에 “필수 테이블/컬럼 존재 여부” 한 번 더 점검하면, 손상된 DB로 진입하는 경우를 줄일 수 있음.
- **트랜잭션 타임아웃 명시**: SQLite `timeout`은 config에 있으나, 장시간 락 시 사용자 메시지(예: “다른 작업이 DB를 사용 중입니다. 잠시 후 다시 시도하세요.”)를 보여주면 좋음.
- **로그 레벨 설정**: `settings.ini`에 `[Logging] level=DEBUG` 등으로 실행 중 로그 레벨을 바꿀 수 있게 하면, 현장 디버깅 시 유리함.

### 5.2 효율성

- **대량 조회 시 LIMIT/페이지**: 재고/톤백 수가 많을 때 Treeview에 한 번에 다 넣지 않고, 스크롤 또는 “더 보기” 시 추가 로드하면 메모리·UI 반응 개선.
- **필터/정렬 시 쿼리 푸시다운**: 가능한 경우 “DB에서 필터/정렬된 결과만 가져오기”로 바꾸면, 클라이언트 메모리와 연산이 줄어듦.
- **엑셀 내보내기 스트리밍**: 대용량일 때 한 번에 메모리에 올리지 않고 행 단위로 쓰면 메모리 사용이 안정적임.

### 5.3 편리성

- **단축키 안내**: F5(새로고침), Ctrl+S 등 자주 쓰는 단축키를 상태바 툴팁 또는 도움말 메뉴에 정리해 두면 사용성이 좋아짐.
- **마지막 필터/탭 기억**: 재고/톤백 필터 값·선택 탭을 설정에 저장해 다음 실행 시 복원하면 반복 작업이 줄어듦.
- **입고/출고 후 자동 새로고침**: 작업 완료 시 해당 탭만 선택적으로 갱신하면, 사용자가 수동으로 F5를 누를 필요가 줄어듦.

---

## 6. 코드 품질 향상 방법 (중점)

### 6.1 데드코드 제거 (이미 정리한 항목 포함)

- **중복 모듈 제거**: `engine_modules/query_mixin.py`, 루트 `toolbar_mixin.py` 삭제 권장 (섹션 2).
- **미사용 import 정리**: 각 파일 상단의 `from ... import` 중 사용하지 않는 것은 제거. (선택: `pyflakes`, `ruff` 등으로 일괄 검사.)
- **미호출 함수**: 레거시 유틸 등에서 “나중에 쓸 것”으로만 남아 있는 함수는 deprecated 주석 또는 삭제로 정리.

### 6.2 예외 처리 통일

- **bare except 금지**: `except:` → `except Exception as e:` + 로깅.
- **except + pass 제거**: 위 3.2 목록처럼 `logger.debug(f"Suppressed: ... {e}")` 로 치환.
- **에러 메시지 사용자 노출**: `CustomMessageBox.show_detailed_error()` 등으로 위치·원인·해결책을 일관되게 표시 (AGENTS.md 반영).

### 6.3 파일/함수 크기

- **한 파일 최대 800줄**: 초과 시 Mixin/모듈 분할 (예: toolbar_mixin, main_app 등).
- **한 함수 최대 50줄**: 초과 시 “설정/필터/테이블 구성” 등으로 잘라서 가독성 확보.

### 6.4 테스트·정합성

- **정합성 공식 자동 검사**: 계획서 12.2의  
  `initial_weight == current_weight + picked_weight`  
  등은 단위/통합 테스트에서 주기적으로 assert 하면 회귀 방지에 유리함.
- **E2E 한 사이클**: 입고 → 출고 → 보고서 생성까지 한 번 자동 실행하는 스크립트가 있으면, 리팩터링 시 안전망이 됨.

### 6.5 기타

- **타입 힌트**: 새로 추가하는 함수에는 `def fn(self, lot_no: str) -> Optional[Dict]:` 형태로 점진적 적용.
- **__pycache__ 정리**: 배포/패키징 시 `find . -name "__pycache__" -type d -exec rm -rf {} +` 등으로 캐시 제거 (계획서 13.3).

---

## 7. 요약

- **즉시 반영한 것**: run_app.py 의존성/옵션/점검/로깅, config·path_utils 의 예외 로깅.
- **권장 정리**: 데드코드 2개 파일 삭제, 프로덕션 코드의 남은 `except+pass` 를 `logger.debug` 로 단계적 교체.
- **계획서**: v5.4.6 계획서와 구조·스키마·Phase가 잘 맞으며, 진입점과 점검 로직만 위 수정으로 보강된 상태입니다.
- **추가 제안**: 안정성(DB/스키마 검증, 트랜잭션 메시지, 로그 레벨), 효율성(페이지네이션, 쿼리 푸시다운, 스트리밍 내보내기), 편리성(단축키 안내, 필터/탭 기억, 자동 새로고침)을 단계적으로 도입할 수 있습니다.

이 보고서를 기준으로 데드코드 삭제와 except+pass 정리를 이어가시면, 코드 품질과 유지보수성이 한 단계 더 올라갑니다.
