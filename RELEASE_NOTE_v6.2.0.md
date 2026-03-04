# SQM v6.2.0 Release Notes

## 핵심 변경
- 안정화 2단계 반영
  - `parsers/__init__.py` 문서 감지기 중복 import 정리
  - `features/pdf_parser/gemini_parser.py`를 compatibility shim으로 전환 (SSOT: `features/ai/gemini_parser.py`)
  - `except Exception: pass` 제거/로깅 전환
    - `engine_modules/inventory_modular/outbound_mixin.py`
    - `core/barcode_scan_engine.py`
    - `core/barcode_label_generator.py`
- PC 보안 허용 목록 보강
  - `대흥남기동2025`의 `MachineGuid` 반영
- 대시보드 호환성 핫픽스
  - `dashboard_tab.py` LabelFrame `padding` 옵션 호환 이슈 수정 (`_tkinter.TclError: unknown option "-padding"`)

## 점검 결과
- `python run.py --check` 통과 (에러 없음)
- 앱 실행/대시보드 진입 정상 확인

## 후속 안정화 패치 (menu consistency)
- 메뉴 단일 소스 정리 강화 (`menu_registry` 중심)
  - `FILE_MENU_INBOUND_RETURN_SUB_ITEMS` 추가 적용
  - `FILE_MENU_EXPORT_ITEMS`, `FILE_MENU_BACKUP_ITEMS` 추가
- 메뉴 빌더 일괄 정렬
  - `toolbar_mixin.py`
  - `custom_menubar.py`
  - `menu_mixin.py`
- 출고/업로드 메뉴에서 구분선(`None`) 처리 누락 보완
- 반품(재입고) 소량/다량 서브메뉴를 공통 registry 기반으로 통일

