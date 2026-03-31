============================================================
  SQM v8.5.6  PATCH 1+2+3+4 통합본
  기준: Claude_SQM_v854.zip (v8.5.4)
  생성: 2026-03-25
============================================================

[설치]
v8.5.4 기준 폴더에 아래 7개 파일을 덮어쓰기

[수정 파일 목록 — 7개]
  gui_app_modular/dialogs/
    onestop_inbound.py                    [패치 1]

  engine_modules/inventory_modular/
    inbound_mixin.py                      [패치 2]

  parsers/document_parser_modular/
    do_mixin.py                           [패치 2 + 패치 3]
    invoice_mixin.py                      [패치 3]
    bl_mixin.py                           [패치 3]
    packing_mixin.py                      [패치 4]

  parsers/
    picking_list_parser.py                [패치 3]

  version.py                              [8.5.4 → 8.5.6]

============================================================
[패치 1] onestop_inbound.py — 파일 선택 UX 개선
  - 📁 폴더 선택 버튼: 기존 순서대로 4회 열기
    → Ctrl 다중선택 1회 다이얼로그로 변경
  - 자동 분류 금지: 드롭다운으로 사용자가 직접 지정
    (BL / PL / FA / DO 각각 지정)
  - DO 미선택 시: 기존 달력 위젯으로 입항일 직접 입력
    (수동 입항일 → _manual_arrival_date 속성 보관)

[패치 2] do_mixin.py + inbound_mixin.py — CON RETURN / FREE TIME 버그 수정
  do_mixin.py (MSC _parse_do_msc_coord):
    기존: r'반납기한.{0,30}?(\d{4}...)' → 정규식 실패 (30자 제한 초과)
    수정: r'[A-Z]{4}\d{7}\s*/\s*/\s*/\s*(\d{4}-\d{2}-\d{2})'
          컨테이너별 직접 추출 → max(dates) 대표값 사용
          ContainerInfo.free_time_date 키 추가
  do_mixin.py (MAERSK _parse_do_maersk_coord):
    ContainerInfo.free_time_date 키 추가
    _max_ft_date (가장 늦은 반납일) 대표값 적용
  inbound_mixin.py (_prepare_lot_data):
    기존: do_data.get('free_time_date') → 키 불일치로 빈값
    수정: _extract_do_con_return() 다중 경로 참조
          containers[].free_time → free_time → con_return 순 탐색

  결과 (MEDUFP963970 기준):
    ARRIVAL    : 2026-03-21 ✅
    CON RETURN : 2026-04-04 ✅ (기존 공백)
    FREE TIME  : 14일        ✅ (기존 0)

[패치 3] 파싱 버그 4건 수정
  BUG-1: do_mixin.py — MSC DO Vessel 좌표 실패 폴백
    좌표 by_xy() 결과가 빈 문자열인 경우
    텍스트 정규식으로 재시도 (MSC \w+, HMM \w+ 등)

  BUG-2: invoice_mixin.py — MSC FA 핵심 숫자 필드 좌표 수정
    Qty:       y=49% → y=47~51%, 정규식으로 헤더 텍스트 제거
    NetWeight: 좌표 → r'Netos/Net\s*KG\s*(\d[\d.,]+)' 정규식 교체
    GrossWt:   좌표 → r'Bruto/KG\s*Gross\s*(\d[\d.,]+)' 정규식 교체
    PackageCnt: r'Number\s*of\s*Packaging\s*(\d+)' 정규식
    결과: 0.0 → 120,024kg / 123,150kg ✅

  BUG-3: bl_mixin.py — Total Containers / Gross Weight 집계 보강
    패턴: r'(\d+)\s+(?:cntrs|containers?)' 추가
    패턴: r'Total\s*Gross\s*Weight\s*[:\s]*([\d,.]+)' 추가

  BUG-4: picking_list_parser.py — Outbound ID(SPO No) 자동 파싱
    OUTBOUND_ID_RE = r'Outbound\s+ID\s+(?P<no>\d{5,12})'
    Sales Order 최소자리수 6→3 수정 (1783 같은 짧은 번호 대응)
    dict 반환에 "outbound_id" 키 추가

[패치 4] packing_mixin.py — PL 좌표 파서 안정화
  import os 추가 (NameError 방지)
  SAP No 파일명 추출 try-except 안전화
  좌표 파싱 예외 시 RuntimeError → None 반환
  (Gemini 폴백으로 자연스럽게 이어지도록)

============================================================
[패치 후 전체 파싱 현황]
  MSC BL        : ✅ (Total Containers 보강)
  MSC FA        : ✅ (Qty/중량 정상화)
  MSC PL        : △ (운영환경 Gemini 폴백 정상)
  MSC DO        : ✅ (Vessel 폴백 + CON RETURN 수정)
  MAERSK BL     : ✅ (Total Containers 보강)
  MAERSK FA     : ✅ (기존부터 정상)
  MAERSK PL     : △ (운영환경 Gemini 폴백 정상)
  MAERSK DO     : ✅ (CON RETURN/FREE TIME 수정)
  Picking List  : ✅ (Outbound ID 자동 파싱)

  ※ PL은 운영환경(Gemini API Key 있음)에서 정상 처리됨
============================================================
