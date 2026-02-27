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

