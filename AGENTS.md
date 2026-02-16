# AGENTS.md — SQM Code Review Guidelines

> **자동 코드 리뷰 에이전트 및 개발자가 따르는 규칙**

---

## Code Style

- **Python 3.10+** 기준
- **snake_case**: 변수, 함수, 모듈
- **PascalCase**: 클래스
- **UPPER_SNAKE**: 상수
- `bare except:` 사용 금지 → `except Exception as e:` + logging
- `except + pass` 사용 금지 → `logger.debug(f'Suppressed: {e}')` 사용
- 한 파일 최대 800줄 (초과 시 Mixin 분할)
- 한 함수 최대 50줄
- DB 컬럼은 snake_case, GUI 헤더는 Title Case/UPPER

## Naming Convention

| 종류 | 규칙 | 예시 |
|------|------|------|
| 이벤트 핸들러 | `_on_` 접두어 | `_on_drop()`, `_on_save()` |
| UI 초기화 | `_setup_` 접두어 | `_setup_toolbar()` |
| 데이터 처리 | `_process_` 접두어 | `_process_inbound()` |
| 검증 | `_validate_` 접두어 | `_validate_lot_no()` |
| DB 마이그레이션 | `_migrate_` 접두어 | `_migrate_v396()` |
| UI 표시 | `_show_` 접두어 | `_show_lot_history()` |
| 파일 생성 | `_generate_` 접두어 | `_generate_daily_pdf()` |
| 내보내기 | `_export_` 접두어 | `_export_to_excel()` |

## Architecture Rules

- **Mixin 패턴**: 기능별 분리, MRO를 통한 합성
- **All-or-Nothing**: 입고/출고 트랜잭션은 Preflight 검증 후 커밋
- **Preflight**: Phase 1 (읽기 전용 검증) → Phase 2 (실행)
- **Single Source of Truth**: version.py가 유일한 버전 소스

## Database Rules

- SQLite WAL 모드 필수
- 모든 테이블 변경은 마이그레이션 Mixin 경유
- ALTER TABLE 실패는 무시 (이미 존재 허용)
- 검색 인덱스 필수 (lot_no, sap_no, bl_no, status, product, ship_date)

## Security Rules

- API 키 평문 저장 금지 → 3단계: ENV → keyring → INI
- DB 체크섬 검증 활성화
- 자동 백업 설정 필수

## Testing Rules

- 신규 Mixin마다 `tests/test_*.py` 추가
- 최소 5개 테스트 / Mixin
- E2E 테스트: 입고 → 출고 → 보고서 사이클 검증
- 파괴적 테스트: 의도적 에러 주입으로 All-or-Nothing 확인

## PR Rules

- 제목: `<타입>: <설명>` (feat/fix/refactor/test/docs)
- 컴파일 100% 통과 확인
- Exception+pass 0건 확인
- 변경된 파일 수 명시
- 영향 범위 설명 (1~2문장)

## Error Handling

- `CustomMessageBox.show_detailed_error()` 사용
- 에러 팝업에 포함: 위치(파일:줄), 원인, 해결책
- 자동 해결책 매핑 (FileNotFoundError → "파일 경로 확인", PermissionError → "다른 프로그램에서 열림" 등)

## Excel/Report Rules

- 모든 헤더: 영문 첫글자 대문자 (Balance(Kg), Inbound(Kg))
- 모든 보고서 하단: `(주) 지와이로지스    년  월  일`
- 타이틀행 삽입: Row 1 제목, Row 2 간격, Row 3 스타일 헤더

---

*최종 수정: 2026-02-09 | SQM v4.0.3*
