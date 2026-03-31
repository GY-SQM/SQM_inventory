============================================================
  Claude_SQM_v855_PATCH (P1: 사문 파일 삭제)
  기준: v8.5.4
  생성: 2026-03-25
  버전: v8.5.5
============================================================

[개요]
  패치를 반복하면서 누적된 사문 파일(참조 0건)을 일괄 삭제합니다.
  코드 수정은 version.py 1개뿐이며, 나머지는 모두 삭제입니다.
  총 ~40개 파일/폴더 삭제, 약 13,800줄 제거.

[적용 순서]
  ① DELETE_P1.bat를 SQM 루트 폴더에 복사
  ② DELETE_P1.bat 더블클릭 실행 (사문 파일 자동 삭제)
  ③ version.py를 SQM 루트에 덮어쓰기
  ④ python -m pytest 실행 → 기존 통과 수 유지 확인
  ⑤ 프로그램 실행 테스트

[패치 구성 — 3개 파일]
  DELETE_P1.bat                     삭제 스크립트 (SQM 루트에서 실행)
  version.py                        v8.5.5 버전 정보
  tests/test_v660_new_methods.py    sqm_parsing_runtime import 제거 (2줄)

[삭제 대상 상세 — 총 ~40개]

  ── 루트 잔류 파일 (6개) ──
  auto_tooltip.py                   gui_app_modular/utils/ 와 100% 동일
  ui_constants.py                   gui_app_modular/utils/ 와 100% 동일
  onestop_inbound.py                dialogs/ 버전이 최신 (루트=구버전)
  onestop_inbound_candidate_patch.py features/ 버전이 최신 (루트=구버전)
  sqm_audit_report.txt              v8.1.4 기준 보고서 (현재 v8.5.4)
  PATCH_README.txt                  v8.4.5 기준 패치 안내

  ── 참조 0건 모듈 (7개) ──
  core/barcode_label_generator.py          참조 0건
  parsers/msc_do_parser.py                 참조 0건 (do_mixin 이관 완료)
  parsers/maersk_do_parser.py              참조 0건 (do_mixin 이관 완료)
  parsers/do_dispatcher.py                 참조 0건
  engine_modules/integrity_engine.py       참조 0건
  features/pdf_parser/pdf_field_extractor.py  참조 0건
  gui_app_modular/dialogs/Claude_allocation_stress_test_v712.py  참조 0건

  ── 폴더 전체 삭제 (2개) ──
  sqm_parsing_runtime/    운영 코드에서 참조 0건 (테스트 로드확인 1건만)
  files/                  구버전 패치 백업 (outbound_mixin_patch 등)

  ── 비코드 파일 (~12개) ──
  Snipaste_*.png (5개)           스크린샷
  스크린샷*.png (1개)            스크린샷
  debug-934e53.log               디버그 로그
  logs/sqm_inventory.log         운영 로그 (자동 재생성됨)
  parsers/document_parser_modular/PATCH_README.txt  패치 안내 잔류

[교차검증]
  ① SQL 오염: 해당없음 (삭제만)           ✅
  ② status 방향: 해당없음                 ✅
  ③ 예외처리: 해당없음                    ✅
  ④ py_compile version.py: 통과 확인 필요
  ⑤ 미채택 항목: 해당없음                 ✅

[다음 단계]
  P2 (v8.5.6): 참조 0 shim + deprecated 파일 제거
============================================================
