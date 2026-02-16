# -*- coding: utf-8 -*-
__version__ = '5.7.7'
APP_NAME = 'SQM 재고관리 시스템'
APP_NAME_EN = 'SQM Inventory Management System'
VERSION_HISTORY = {
    '5.7.7': '🔖 v5.7.7: 릴리스 태그',
    '5.7.6': '🐛 v5.7.6: 출고 API 디버깅 — import_handlers process_outbound(allocation_data) 시그니처 통일, LOT 전량 출고 시 current_weight 조회',
    '5.7.5': '🎨 v5.7.5: UI·원스톱 입고 개선 — 폰트 위계, 기간 캘린더, 진행 팝업, Invoice/FA·Bill of Lading·Delivery Order, UID 표시, 스탯바 None 수정',
    '5.7.4': '🐛 v5.7.4: 표시 컬럼 체크 해제 시 Invalid column index #all 수정 — 재고/톤백 리스트 공통 (displaycolumns #all 정규화)',
    '5.7.3': '🐛 v5.7.3: Excel 입고 — add_inventory_from_dict 추가 (CRUDMixin), GUI tonbags 호환',
    '5.7.2': '🔧 v5.7.2: 크로스 검증 샘플 포함 합산 — 정합성 경고 0건 (5001=500×10+1)',
    '5.7.1': '🐛 v5.7.1: 톤백 무게 정합성 — per_bag=(총무게-1)/톤백수 주석 강화, NET/Balance/Inbound 톤백 개별 무게만 사용',
    '5.7.0': '📥 v5.7.0: 입고 Gate-1 강화 — PL+FA+BL 필수 3종 없으면 DB 업로드 차단, D/O 후속 연결 정책 명확화',
    '5.6.9': '🎨 v5.6.9: 로케이션 엑셀 양식 확정, 다크 테마 가시성, LOT 상세/하단 요약 스타일 통일, Avail 동적 로직 명시',
    '5.6.8': '🏗️ v5.6.8: 상수파일 분리 + 핵심 테스트 11개 + 데드테이블 마킹 + 타입힌트 보강',
    '5.6.7': '🧹 v5.6.7: DO 후속 연결 + 데드코드 제거(inbound_preview/PG/picking_parser/-1,583줄) + unused import 정리 + 루트 md 정리',
    '5.6.6': '🔧 v5.6.6: 변수 통일 — bag_count→mxbg_pallet, invoice_no→salar_invoice_no, total_weight_kg→net_weight + 입고경로 단일화',
    '5.6.0': '🔴 v5.6.0: R1~R6완료 — 대원칙정합성, SQL보안, MAC잠금, except→0, print→logger, messagebox통일, 잔여톤백Avail컬럼, 심플엑셀출고',
    '5.5.5': '🔧 v5.5.5: 코드감사(-9,244줄/15.8%), 죽은코드 대량제거, except→logger.debug(43건), 샘플S00통일, 보고서메뉴, DB문서화',
    '5.5.3': '🔧 v5.5.3: UI간소화(tk→ttk), Excel 6옵션, 죽은코드 -5,474줄, 메뉴재배치, 샘플S00통일, 📝보고서메뉴, DB문서화',
    '5.5.2': '🔧 v5.5.2: PL 디버깅 강화 — 원문 저장 토글, JSON 추출/검증 로그, 프롬프트 강제 스키마, OpenAI 폴백 옵션',
    '5.5.1': '🔒 v5.5.1: 모든 문서 파싱을 Gemini API로 강제(폴백 제거) + API Key 미설정 시 하드스톱',
    '5.5.0': '🧩 v5.5.0: (적용본) UI/로직 개선 누적 반영',
    '5.4.2': '🔧 v5.4.2: 탭색상 테마동기화 + API메뉴 복원 + Excel 18컬럼 + Treeview 글씨색 + 통계합계 수정',
    '5.4.1': '🔧 v5.4.1: 드롭다운 메뉴 테마 동기화',
    '5.2.0': '🏗️ v5.2.0 재구축: 샘플 하드스톱 + tonbag_no TEXT + (BL,LOT,tonbag_no) 유니크 + 데드코드 정리',
    '5.1.5': '🛡️ 반품/분할/병합 강화 (이전 빌드)',
    '5.1.4': '🛡️ 입출고 정합성 게이트: 트랜잭션 안에서 즉시 검증 → 불일치 시 자동 롤백',
    '5.1.3': '🔄 트랜잭션 컨텍스트 매니저 적용: 입고/위치업로드/문서업데이트 5곳 전환',
    '5.1.2': '🔁 트랜잭션 재시도 강화: BEGIN IMMEDIATE 재시도 + with db.transaction() 컨텍스트 매니저',
    '5.1.1': '🔍 에러 로깅 강화: 침묵 except+pass 37건 → logger.debug/warning 변환',
    '5.1.0': '🔄 용어 통일: sub_lt→tonbag_no, sold_to→customer, mxbg_pallet→tonbag_count 호환 레이어',
    '5.0.9': '🔧 메뉴 색상 복구 수정 + 출고 샘플/톤백 정확한 구분 + 미리보기 레이아웃 개선',
    '5.0.8': '✅ 톤백 리스트 완전 통일: 재고 리스트와 동일한 포맷',
    '5.0.7': '🎨 대시보드 콤팩트화: 폰트/패딩/높이 축소로 깔끔하게',
    '5.0.6': '🔧 긴급 수정: 컬럼 ID 불일치, StatusBar, tk_popup 방식',
    '5.0.5': '🔧 메뉴 버튼 색상 문제 근본 해결 + import 오류 수정',
    '5.0.4': '🐛 핫픽스: SyntaxError 완전 수정',
    '5.0.3': '🔧 자동 백업 강화 + 성능 최적화: 백업 검증, 자동 복구, 쿼리 캐싱',
    '5.0.2': '🎯 사용성 개선: 메뉴 간소화 + 버튼 색상 수정 (Phase 1 완료)',
    '5.0.1': '🔧 긴급 수정: sqlite3.Row.get() 에러 완전 해결',
    '5.0.0': '🎯 완전 통일 버전: 모든 UI 100% 통일',
}
def get_version(): return __version__
def get_version_info(): return f"SQM v{__version__}"
__all__ = ['__version__', 'APP_NAME', 'APP_NAME_EN', 'VERSION_HISTORY', 'get_version', 'get_version_info']
