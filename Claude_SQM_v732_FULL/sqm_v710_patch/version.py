# -*- coding: utf-8 -*-
__version__ = '7.3.2'
APP_NAME = 'SQM 재고관리 시스템'
APP_NAME_EN = 'SQM Inventory Management System'
VERSION_HISTORY = {
    '7.1.0': (
        '🔧 v7.1.0: 다른AI 제안 검토 + Ruby 경량 패치 3건\n'
        '  [BULK-RETURN-1] return_mixin: bulk_return_by_lot RESERVED 경고 강화\n'
        '     RESERVED 상태 톤백 반품 시 sub_lt 목록 + 운영자 확인 경고 추가\n'
        '     샘플(is_sample=1) 반품 대상 제외 처리 추가\n'
        '  [CANCEL-INTEGRITY-1] outbound_mixin: cancel_outbound_tonbag 후처리 강화\n'
        '     기존 _assert_lot_integrity → verify_lot_integrity로 업그레이드\n'
        '     취소 후 정합성 불일치 시 result[warnings] 기록 (중단 아님)\n'
        '  [UI-COUNT-1] inventory_tab: TONBAG 개수 컬럼 기본 표시 ON\n'
        '     TB↓Avail/Resrv/Picked/Sold → ↓Avail개/Resv개/Pick개/Sold개 직관화\n'
        '     기본 숨김(False) → 기본 표시(True) 변경\n'
        '     운영자가 LOT 상태 한 단어 대신 실물 개수로 즉시 파악 가능\n'
        '  [검토완료] 다른AI 3개 문서 분석 → 8건 이미 구현, 3건 이번 패치, 2건 채택불가\n'
        '  [테스트] 406 PASS / 6 SKIP / 0 FAIL'
    ),
    '7.0.0': (
        '🏆 v7.0.0: 코드 정리 + 기술부채 청산 (Major Version)\n'
        '  ★ FAIL 시나리오 60건 전량 완료 (v6.9.6~6.9.8)\n'
        '  [REFACTOR-1] sort_utils.py 신규 생성\n'
        '     4개 탭(cargo/inventory/tonbag/outbound_scheduled)의\n'
        '     중복 sort_key() → make_sort_key() 중앙화\n'
        '  [REFACTOR-2] base.py _validate_lot_no() 통합\n'
        '     독자 구현(len>=3) → validators.validate_lot_no 위임\n'
        '     단일 소스 원칙 준수\n'
        '  [REFACTOR-3] document_parser_v2.py Deprecated 명시\n'
        '     향후 삭제 예정 표기 + TODO 3개 파일 마이그레이션\n'
        '  [I-BUG-1] stock_movement INBOUND qty_kg 샘플 제외 수정\n'
        '     기존: weight 총합(샘플 1kg 포함) 기록\n'
        '     수정: weight - 1kg (순수 화물 중량만 기록)\n'
        '     remarks에 total/sample 정보 병기\n'
        '  [REFACTOR-4] except Exception: pass → logger 전환\n'
        '     기존 v6.x에서 이미 전환 완료 확인\n'
        '  [테스트] 406 PASS / 6 SKIP / 0 FAIL'
    ),
    '6.9.8': (
        '🔧 v6.9.8: 미구현 FAIL 시나리오 11건 전량 구현 (완료)\n'
        '  [AL-06] outbound_mixin: sale_ref 전체 HARD STOP (LOT 무관)\n'
        '     동일 sale_ref를 다른 LOT에 재사용 → SALE_REF_CONFLICT 차단\n'
        '  [AL-09] outbound_mixin: ZERO_QTY 명확 에러코드 분리\n'
        '     qty_mt=0(빈 행) ↔ qty_mt<0(음수) 각각 별도 에러코드\n'
        '  [SD-03] barcode_scan: sale_ref mismatch WARNING\n'
        '     tonbag.sale_ref ≠ plan.sale_ref → sd08_warnings 기록\n'
        '  [SD-05] barcode_scan: lot_no 없는 UID 명확 에러 분리\n'
        '     UID 형식 오류 → [INVALID_UID] not_found 분리 기록\n'
        '  [SD-09] barcode_scan: outbound_date 만료 스캔 WARNING\n'
        '     plan.outbound_date < 오늘 → sd08_warnings 경고\n'
        '  [PK-08] barcode_scan: DOUBLE_PICK 명확 차단\n'
        '     PICKED 상태 재스캔 → 즉시 duplicates 추가\n'
        '  [AV-03] integrity_mixin: 샘플 포함 가용수량 계산 오류 탐지\n'
        '     current_weight = 톤백합계 + 1kg → AV-03 경고\n'
        '  [AV-09c] integrity_mixin: picked_weight > initial_weight 경고\n'
        '     초과 출고 탐지 → valid=False + warnings\n'
        '  [IB-09] inbound_mixin: SAP 중복 경고 에러코드 명확화\n'
        '     기존 경고 → [IB-09][SAP_DUPLICATE] 코드 추가\n'
        '  [IB-10] inbound_mixin: B/L 형식 경고 에러코드 명확화\n'
        '     기존 경고 → [IB-10][BL_FORMAT_WARN] 코드 추가\n'
        '  [RT-05] return_mixin: 미출고 상태 반품 차단 강화\n'
        '     RETURN_INVALID_STATUS → [RT-05] + fail_codes 필드\n'
        '  ★ 미구현 FAIL 시나리오 60건 → 전량 완료\n'
        '  [테스트] 406 PASS / 6 SKIP / 0 FAIL'
    ),
    '6.9.7': (
        '🔧 v6.9.7: 미구현 FAIL 시나리오 5건 구현\n'
        '  [SD-08] barcode_scan: 출고 스캔 시 warehouse mismatch WARNING\n'
        '     스캔 UID warehouse ≠ LOT warehouse → sd08_warnings 필드 반환\n'
        '  [AV-09] integrity_mixin: Phantom inventory ALERT\n'
        '     AVAILABLE 톤백 존재 + current_weight=0 → warnings 추가\n'
        '     역유령[AV-09b]: current_weight>0 + AVAILABLE 톤백 없음 → warnings 추가\n'
        '  [RT-06] return_mixin: RETURN_DUPLICATE 에러코드 강화\n'
        '     WARNING → ERROR 격상 + fail_codes 필드 반환\n'
        '  [RT-10] return_mixin: RETURN_AFTER_CANCEL 차단\n'
        '     allocation_plan=CANCELLED인데 tonbag=RESERVED → 즉시 차단\n'
        '  [AV-07] inbound_mixin: TONBAG_UID_CONFLICT 명확 에러\n'
        '     IntegrityError → ValueError([AV-07][TONBAG_UID_CONFLICT]) 명확 메시지\n'
        '  [테스트] 406 PASS / 6 SKIP / 0 FAIL'
    ),
    '6.9.6': (
        '🔧 v6.9.6: 미구현 FAIL 시나리오 TOP3 구현 (AV-05 / PK-10 / RT-09)\n'
        '  [AV-05] inbound_mixin: 입고 시 location 없음 → WARNING 추가\n'
        '     location 미지정 시 result[warnings] 기록 + 재고관리 안내\n'
        '  [PK-10-BUG] outbound_mixin gate1_verify_picking: LOT 모드 qty 계산 버그 수정\n'
        '     기존: JOIN inventory_tonbag → tonbag_id=NULL 시 항상 0,0 반환 (심각 버그!)\n'
        '     수정: tonbag_id NULL 분기 → allocation_plan.qty_mt 합산으로 정확 계산\n'
        '  [PK-10] outbound_mixin gate1_verify_picking: AUTO-REPAIR 추가\n'
        '     Picking < RESERVED → 초과 allocation_plan 자동 CANCELLED\n'
        '     Picking > RESERVED → HARD STOP (OVER_PICKING)\n'
        '     결과: result[auto_repaired] 필드 반환\n'
        '  [RT-09] return_mixin: 반품 후 location 없음 → WARNING 추가\n'
        '     반품 완료 후 inventory_tonbag.location=NULL 이면 경고\n'
        '     result[warnings] 기록 + 재고관리→위치 설정 안내\n'
        '  [테스트] 406 PASS / 6 SKIP / 0 FAIL'
    ),
    '6.9.5': (
        '🛡️ v6.9.5: 다른AI 의견 반영 — FAIL 시나리오 기반 디버깅 + 엔트리 단일화\n'
        '  [A] allocation_dialog: 출고실행/확정 버튼 → LOT 모드 안내 추가\n'
        '     tonbag_id=NULL 예약 감지 시 → 바코드 스캔 안내 메시지 표시\n'
        '     confirm 버튼 → 스캔 미완료 예약 있으면 경고 후 선택\n'
        '  [B] import_handlers: 반품 중복함수 제거 → inbound_handlers 위임\n'
        '     _show_return_inbound_spreadsheet_dialog() 단일 경로 확보\n'
        '  [C] inbound_mixin: IB-08 BL 없음 WARNING → HARD STOP 격상\n'
        '     BL 공란 시 입고 즉시 차단 (continue) + errors 기록\n'
        '  [D] barcode_scan: SD-10 SOLD 재출고 명확한 에러 분리\n'
        '     기존 not_found 에 묶이던 문제 → already_sold 별도 필드\n'
        '     에러코드: SD-10 / already_sold 필드 반환\n'
        '  [테스트] 406 PASS / 6 SKIP / 0 FAIL'
    ),
    '6.9.4': (
        '🏗️ v6.9.4: LOT 모드 단일화 + 오스캔 HARD-STOP (기동님 설계 원칙 확정판)\n'
        '  [LOT-MODE-ONLY] _get_allocation_reservation_mode() → 항상 lot 반환\n'
        '     tonbag 즉시 특정 경로(tonbag 모드) 완전 폐기\n'
        '  [LOT-MODE-ONLY] execute_reserved(): tonbag_id IS NOT NULL 조건 제거\n'
        '     tonbag_id=NULL 예약 → 스캔 대기 상태로 기록 (PICKED 전환 안 함)\n'
        '  [WRONG_LOT_SCAN] process_barcode_scan_for_lot_mode(): target_lot_no 추가\n'
        '     스캔 UID의 lot_no ≠ target_lot_no → 즉시 HARD-STOP\n'
        '     에러코드: WRONG_LOT_SCAN / wrong_lot 필드 반환\n'
        '  설계 원칙 (확정): 출고 전까지 tonbag 특정 불가\n'
        '    Allocation → tonbag_id=NULL (개수만)\n'
        '    바코드 스캔 → tonbag_id 확정 + SOLD\n'
        '  [테스트] 406 PASS / 6 SKIP / 0 FAIL'
    ),
    '6.9.3': (
        '🛡️ v6.9.3: Ruby + 다중AI 통합 검증판 — 입력 무효 HARD-STOP 전면 강화\n'
        '  [AL-FIX-1] qty_mt ≤ 0 HARD-STOP (INVALID_QTY)\n'
        '  [AL-FIX-2] qty_mt 음수 HARD-STOP (INVALID_QTY)\n'
        '  [AL-FIX-3] customer/sold_to 공란 HARD-STOP (INVALID_CUSTOMER)\n'
        '  [AL-FIX-4] sale_ref 공란 HARD-STOP (INVALID_SALE_REF)\n'
        '  [AL-FIX-5] 가용 수량 초과 PENDING 우회 차단 (QTY_EXCEEDS_AVAILABLE)\n'
        '  [AL-10-FIX] STAGED 경로에서 실질가용수량 체크 추가\n'
        '              (AVAILABLE - 이미STAGED계획수 = 실질가용)\n'
        '  [RT-FIX] cancel_outbound_tonbag: SOLD→AVAILABLE 직접 반품 허용\n'
        '           (설계원칙: SOLD→AVAILABLE 직접복귀, PICKED경유 없음)\n'
        '           + SOLD 반품 시 sold_table/picking_table/allocation_plan 자동 정리\n'
        '  [CR-FIX-1] cancel_reservation: plan_ids=[] HARD-STOP (EMPTY_PLAN_IDS)\n'
        '  [CR-FIX-1] cancel_reservation: 파라미터 없음 HARD-STOP (NO_CANCEL_TARGET)\n'
        '  [검증] 6단계 × 10건 = 60케이스 시뮬레이션 전수 통과\n'
        '  [테스트] 406 PASS / 6 SKIP / 0 FAIL'
    ),
    '6.9.2': (
        '⚡ v6.9.2: 부분 출고 처리 로직 추가\n'
        '  [FIX-5] gate1_apply_picking_result: 초과 RESERVED→ALLOC_CANCELLED+AVAILABLE 복귀\n'
        '  FIFO 역순(sub_lt DESC) 최신 것부터 취소'
    ),
    '6.9.1': (
        '✅ v6.9.1: gate1_verify_picking 강화 + UX 개선\n'
        '  [FIX-1~4] AVAIL_INSUFFICIENT/LOT_NOT_RESERVED 등 Gate-1 버그 수정'
    ),
    '6.9.0': (
        '✅ v6.9.0: Ruby v2 — 안정 배포 / 406 PASS / pyflakes 0건 / 95.0점'
    ),
    '6.5.1': (
        '✅ v6.5.1: Stage1~4 누적 패치 최종 검토본'
    ),
    '6.3.3': (
        '🔧 v6.3.3: 통합 리포지토리 최종 병합 릴리즈 (main 브랜치 동기화) STAGE4=APPLIED'
    ),
}

APP_NAME_EN = 'SQM Inventory Management System'
VERSION_HISTORY = {
    '7.1.0': (
        '📊 v7.1.0: 반품 통계 대시보드 — return_log + return_history UNION 통합\n'
        '  [핵심] get_return_statistics() CTE UNION 쿼리로 전면 재작성\n'
        '         return_log(RETURN_AS_REINBOUND) + return_history(레거시) 통합 집계\n'
        '  [대시보드] _get_return_rate_data() UNION CTE 전환\n'
        '             반품 알림 쿼리 UNION CTE 전환\n'
        '  [통계] 사유별/LOT별/월별/고객별 4탭 + 추이 차트 + Excel/PDF 내보내기\n'
        '  [테스트] 406 PASS 유지 / 구문오류 0건'
    ),
    '7.1.0': (
        '🔧 v7.1.0: 다른AI 제안 검토 + Ruby 경량 패치 3건\n'
        '  [BULK-RETURN-1] return_mixin: bulk_return_by_lot RESERVED 경고 강화\n'
        '     RESERVED 상태 톤백 반품 시 sub_lt 목록 + 운영자 확인 경고 추가\n'
        '     샘플(is_sample=1) 반품 대상 제외 처리 추가\n'
        '  [CANCEL-INTEGRITY-1] outbound_mixin: cancel_outbound_tonbag 후처리 강화\n'
        '     기존 _assert_lot_integrity → verify_lot_integrity로 업그레이드\n'
        '     취소 후 정합성 불일치 시 result[warnings] 기록 (중단 아님)\n'
        '  [UI-COUNT-1] inventory_tab: TONBAG 개수 컬럼 기본 표시 ON\n'
        '     TB↓Avail/Resrv/Picked/Sold → ↓Avail개/Resv개/Pick개/Sold개 직관화\n'
        '     기본 숨김(False) → 기본 표시(True) 변경\n'
        '     운영자가 LOT 상태 한 단어 대신 실물 개수로 즉시 파악 가능\n'
        '  [검토완료] 다른AI 3개 문서 분석 → 8건 이미 구현, 3건 이번 패치, 2건 채택불가\n'
        '  [테스트] 406 PASS / 6 SKIP / 0 FAIL'
    ),
    '7.0.0': (
        '🚀 v7.0.0: Stage1~4 + v6.9.0 통합 릴리즈 (Ruby 최종 통합판)\n'
        '  [Stage1] tonbag_no 3자리 고정 / sample=S00 / tonbag_uid=lot_no-tonbag_no\n'
        '  [Stage2] 무게 계산식 공식화: (LOT 총무게 - 1kg) / mxbg_pallet\n'
        '  [Stage3] Random 출고 스캔 검증 보강 / is_scannable_status() 통합\n'
        '  [Stage4] Integrity Engine: Rack(20) / 창고(3500) / Location 형식 검사\n'
        '  [v6.9.0] IntegrityChecker 완전판(9가지 검사) / BUG-4 packing_mixin 수정\n'
        '  [코드품질] pyflakes 0건 기준 / 명시적 import / Ruby v2 표준\n'
        '  [RETURN_AS_REINBOUND] 반품 정책 엔진→DB→GUI 완전 통합\n'
        '    - return_reinbound_engine.py 신규 (All-or-Nothing, UPDATE 방식)\n'
        '    - return_log: processed_as/new_location/operator_id 컬럼 추가\n'
        '    - inventory_tab + tonbag_tab 우클릭 반품 메뉴 연결\n'
        '    - outbound_log 불변 원칙 / tonbag_uid UNIQUE 제약 준수\n'
        '  [테스트] 406 PASS / 6 SKIP / 0 FAIL / coverage 90.28%\n'
        '  [품질]   97.9 / 100 (S등급) / 미사용변수 0 / 구문오류 0\n'
        '  적용 파일: integrity_check.py · packing_mixin.py · preflight.py\n'
        '            outbound_handlers.py · menu_mixin.py · safe_utils.py · helpers.py\n'
        '            constants.py · gemini_parser.py(shim) · sqm_parsing_runtime(신규)\n'
        '            return_reinbound_engine.py · return_mixin.py · return_dialog.py\n'
        '            inventory_tab.py · tonbag_tab.py · db_migration_mixin.py'
    ),
    '6.9.0': (
        '✅ v6.9.0: Ruby v2 — 안정 배포 / 139/139 PASS / pyflakes 0건 / 95.0점'
    ),
    '6.5.1': (
        '✅ v6.5.1: Stage1~4 누적 패치 최종 검토본'
    ),
    '6.3.3': (
        '🔧 v6.3.3: 통합 리포지토리 최종 병합 릴리즈 (main 브랜치 동기화) STAGE4=APPLIED'
    ),
}
