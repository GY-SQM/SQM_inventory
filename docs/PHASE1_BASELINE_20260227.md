# SQM v621 Phase 1 Baseline (2026-02-27)

## 목표
- 완전 패치(2~4단계) 전에 현재 기준선을 고정한다.
- 회귀 여부를 판단할 기준(버전/보안/핵심 리스크)을 문서화한다.

## 현재 기준 정보
- 앱 버전: `6.1.8` (`version.py`)
- 워크스페이스 Python 파일 수: `319`개
  - 참고: 이 수치에는 `all_patches`, `SQM_v701_Outbound_Only` 같은 보관/참고 폴더도 포함됨

## PC 보안 기준(현재 반영 상태)
- 보안 게이트: `run.py`에서 `verify_pc()` 활성
- 우회 옵션: `--no-license`, `SQM_SKIP_LICENSE=1`
- 다중 PC 등록: 기본값으로 활성화됨 (`register_current_pc(replace=False)`)
- 허용 PC 목록(`security/allowed_pcs.json`):
  - `광양대흥남기동` (MAC 1, GUID 1)
  - `대흥남기동2025` (MAC 4, GUID 비어있음)

## 1차 핫픽스 반영 상태(완료)
- `outbound_scheduled_tab.py`: `END` 미정의 방지
- `inventory_tab.py`: `_TC` 미정의 제거
- `refresh_mixin.py`: `CustomMessageBox` import 보강
- `onestop_inbound.py`: `_show_warn()` 경로 import 보강
- `help_dialogs.py`: logger 선언 보강

## 잔여 리스크(2단계 대상)
- 중복/정리:
  - `parsers/__init__.py` 내 `document_detector` 중복 import 구간
  - `features/pdf_parser/gemini_parser.py` 중복 파일 정리 필요(SSOT 단일화)
- 무음 예외(`except Exception: pass`) 잔여:
  - `engine_modules/inventory_modular/outbound_mixin.py`
  - `core/barcode_scan_engine.py`
  - `core/barcode_label_generator.py`

## 백업 체크리스트(필수)
- 이 단계에서는 코드 기준선만 고정했다.
- 완전 패치 시작 전 아래 2개는 반드시 수동 수행:
  1. 프로젝트 폴더 백업(압축 또는 복사본)
  2. `data/db` 폴더 백업(특히 `sqm_inventory.db`)

## 2단계 진입 조건
- 앱 실행 확인: `python run.py`
- PC Guard가 차단 없이 통과(부분 인증 포함)
- 핵심 탭 진입 가능(판매가능/판매배정/판매화물 결정/출고)

