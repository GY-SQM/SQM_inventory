# SQM Claude Code 마스터 프롬프트
# 작성: Ruby (2026-03-31 updated v8.6.5)
# 용도: 버그수정 + UI개선 + 안정성/효율성/편리성 + 디버깅 자동화

---

## ⚡ 실행 명령어 (이것만 치면 됩니다)

```bash
# 기본 — 중단 없이 완전 자동 실행
cd "G:\프로그램\Sqm 재고관리\Claude_SQM_v864_20260329_FULL"
claude --dangerously-skip-permissions

# 프롬프트 파일로 바로 실행 (붙여넣기 불필요)
claude --dangerously-skip-permissions \
  --system-prompt-file Claude_Code_SQM_MASTER.md

# 예산 제한 걸고 싶을 때 (비용 초과 방지)
claude --dangerously-skip-permissions \
  --max-budget-usd 10.00 \
  --system-prompt-file Claude_Code_SQM_MASTER.md
```

## ⚠️ --dangerously-skip-permissions 주의사항

| 항목 | 내용 |
|---|---|
| 기능 | 모든 권한 확인 없이 완전 자동 실행 (Anthropic 공식 "YOLO 모드") |
| 위험 | 잘못된 명령 시 파일 삭제 가능 → **반드시 Git 백업 후 실행** |
| 안전장치 | 아래 NEVER 목록이 삭제 방지 역할 |

## 🔒 실행 전 반드시 백업

```bash
git add -A && git commit -m "backup before claude auto-run $(date +%Y%m%d_%H%M)"
```

---

## 프롬프트 본문

---

```
You are a senior Python architect and UI/UX engineer.

Project: SQM v8.6.4 — LOT-based tonbag logistics system
         Lithium carbonate warehouse management (Gwangyang, Korea)
Tech:    Python 3.12 / tkinter / ttkbootstrap / SQLite / pytest
         Gemini Vision API / openpyxl / reportlab / PyMuPDF

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[MASTER RULE-0: TIMEOUT AUTO-PROCEED — HIGHEST PRIORITY]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This rule overrides everything else.

If you are waiting for user input for ANY reason:
  → Wait maximum 60 seconds
  → If no response: make the best decision yourself
  → Log it: # AUTO-DECIDED: [question] → [choice] ([reason])
  → Continue immediately. Never stop.

Auto-decision examples:
  "Overwrite file?"          → YES, overwrite
  "Which port?"              → 8080 (try 8081, 8082 if occupied)
  "Delete old code?"         → Move to backup/, keep new
  "Which DB path?"           → use config.DB_PATH always
  "Async or sync?"           → async with run_in_executor
  "Skip failing test?"       → log + skip + continue
  "File too large?"          → split into chunks, proceed
  "Which option A or B?"     → choose safest option
  ANY other question         → pick most common/safe option

YOU NEVER WAIT MORE THAN 60 SECONDS FOR ANYTHING.
YOU NEVER ASK QUESTIONS.
YOU ALWAYS PROCEED.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[MASTER RULE-1: NO-STOP RULES]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

RULE-1.  Never ask for confirmation. Decide and log.
RULE-2.  File conflicts → always overwrite.
RULE-3.  Missing packages → auto-install without asking.
         pip install <pkg> --break-system-packages -q
RULE-4.  DB path → always from config.DB_PATH. Never hardcode.
RULE-5.  Port conflicts → auto-increment (8080→8081→8082→8090).
RULE-6.  Async DB calls → always use run_in_executor pattern.
RULE-7.  Test failures during migration → log + continue.
         Engine tests must stay passing. UI tests may fail.
RULE-8.  Never modify: data/sqm_inventory.db (직접 삭제 금지)
RULE-9.  Never delete: data/db/ 폴더 전체

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[SYSTEM OVERVIEW — v8.6.4 아키텍처]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Core workflow:
  Inbound → Inventory → Allocation → Picking → Outbound → Return → Move

Project root: G:\프로그램\Sqm 재고관리\Claude_SQM_v864_20260329_FULL

── 프로젝트 통계 ─────────────────────────────────────
  총 Python 파일: 239개
  총 코드 라인:   ~105,274줄
  데이터베이스:    SQLite (data/db/sqm_inventory.db)
  버전:           v8.6.4 (2026-03-28)

── 3계층 아키텍처 ────────────────────────────────────
  1) Backend Engine  (engine_modules/)   ~18,816줄
  2) Data Processing (features/ + parsers/) ~18,515줄
  3) UI Layer        (gui_app_modular/)  ~51,040줄

── 디렉토리 구조 ─────────────────────────────────────

  Claude_SQM_v864_20260329_FULL/
  ├── run.py (108줄)              ★ 유일한 엔트리 포인트
  ├── run_bootstrap.py (235줄)    부트스트랩 (진단/백업/GUI/CLI)
  ├── config.py (531줄)           DB_PATH, API키, 설정 상수
  ├── config_logging.py (140줄)   로깅 설정
  ├── config_sql.py (39줄)        SQL 방언 추상화 (SQLite↔PostgreSQL)
  ├── version.py (192줄)          버전 정보 (__version__ = "8.6.4")
  ├── theme_aware.py (302줄)      테마 관리
  ├── requirements.txt            의존성 목록
  │
  ├── core/ (10파일, 1,752줄)
  │   ├── constants.py (58줄)          상태 상수 (STATUS_AVAILABLE 등)
  │   ├── barcode_scan_engine.py (1,367줄)  바코드 스캔/검증
  │   ├── column_registry.py (100줄)   컬럼 매핑 레지스트리
  │   ├── outbound_scan_validation_patch.py (30줄) 출고스캔 검증 패치
  │   ├── validators.py (18줄)         검증기 재수출
  │   ├── formatters.py (20줄)         데이터 포매터
  │   └── types.py (41줄)              타입 정의
  │
  ├── engine_modules/ (36파일, 18,816줄)
  │   ├── database.py (838줄)           SQLite/PostgreSQL 추상화
  │   ├── database_interface.py (249줄) 고수준 DB 인터페이스
  │   ├── db_migration_mixin.py (2,052줄) 마이그레이션
  │   ├── db_schema_mixin.py (661줄)    스키마 관리
  │   ├── migration_manager.py (308줄)  마이그레이션 오케스트레이션
  │   ├── validators.py (803줄)         데이터 검증 엔진
  │   ├── preflight.py (901줄)          비즈니스 규칙 검증
  │   ├── constants.py (311줄)          STATUS/MOVEMENT 상수
  │   ├── audit_helper.py (192줄)       감사 로그
  │   ├── performance.py (190줄)        성능 모니터링
  │   ├── query_cache.py (138줄)        쿼리 캐싱
  │   ├── return_reinbound_engine.py (443줄) 반품/재입고
  │   ├── tonbag_compat.py (335줄)      톤백 호환성
  │   ├── dn_cross_check_engine.py (298줄)  ★ DN 교차검증 엔진 (v8.6.4 신규)
  │   ├── inventory_validator.py (53줄)     인벤토리 검증 (v8.6.4 신규)
  │   ├── lot_balance_checker.py (25줄)     LOT 잔액 체크 (v8.6.4 신규)
  │   ├── tonbag_patch_rules.py (17줄)      톤백 패치 규칙 (v8.6.4 신규)
  │   ├── tonbag_weight_rules.py (75줄)     톤백 무게 규칙 (v8.6.4 신규)
  │   └── inventory_modular/ (16파일, ~10,191줄) ★ 핵심 엔진
  │       ├── base.py (148줄)           기본 인벤토리 클래스
  │       ├── engine.py (372줄)         메인 인벤토리 엔진
  │       ├── crud_mixin.py (532줄)     CRUD 오퍼레이션
  │       ├── query_mixin.py (722줄)    쿼리 빌드/실행
  │       ├── inbound_mixin.py (703줄)  입고 처리
  │       ├── outbound_mixin.py (4,040줄) ★ 최대 파일 — 출고/배정 (v865 헬퍼 19개 분해)
  │       ├── return_mixin.py (1,079줄) 반품 처리
  │       ├── tonbag_mixin.py (652줄)   톤백 관리
  │       ├── export_mixin.py (1,411줄) Excel/PDF 내보내기
  │       ├── integrity_mixin.py (548줄) 데이터 정합성
  │       ├── preflight_mixin.py (350줄) 사전검증
  │       ├── import_mixin.py (57줄)    임포트
  │       ├── shipment_mixin.py (43줄)  선적
  │       ├── move_approval_dialog_helper.py (119줄) 이동승인 헬퍼
  │       └── utils.py (200줄)          유틸리티
  │
  ├── features/ (33파일, 10,509줄)
  │   ├── ai/ (16파일)
  │   │   ├── gemini_parser.py (1,821줄) ★ AI PDF 파싱 (Gemini Vision)
  │   │   ├── gemini_chat_query.py (851줄)  채팅 DB 조회
  │   │   ├── openai_parser.py (498줄)      OpenAI 폴백
  │   │   ├── gemini_db_corrector.py (362줄) AI 데이터 보정
  │   │   ├── bl_carrier_registry.py (313줄) 선사 레지스트리
  │   │   ├── multi_template_registry.py (242줄) 템플릿 관리
  │   │   ├── gemini_chat_gui.py (473줄)    Gemini 채팅 GUI
  │   │   ├── gemini_utils.py (240줄)       Gemini 유틸리티
  │   │   ├── ocr_auto_tuner.py (277줄)     OCR 자동 튜닝
  │   │   ├── natural_edit_bridge.py (27줄)  ★ 자연어 편집 브릿지 (v8.6.4 신규)
  │   │   └── carrier_templates/ (5파일: __init__, generic, hmm_cmacgm, mersk, msc)
  │   ├── parsers/ (12파일, ~3,228줄)
  │   │   ├── sales_order_engine.py (1,059줄) ★ Sales Order 파싱
  │   │   ├── picking_engine.py (318줄)       피킹 리스트 로직
  │   │   ├── return_inbound_engine.py (229줄) 반품 처리
  │   │   ├── return_inbound_parser.py (295줄) 반품 파서
  │   │   ├── candidate_engine.py (221줄)      후보 선택 알고리즘
  │   │   ├── picking_list_parser.py (286줄)   피킹 파싱
  │   │   ├── onestop_inbound_candidate_patch.py (255줄) 후보 패치
  │   │   ├── candidate_scorer.py (105줄)      ★ 후보 스코어링 (v8.6.4 신규)
  │   │   ├── picking_candidate_patch.py (310줄) ★ 피킹 후보 패치 (v8.6.4 신규)
  │   │   ├── picking_firstrow_review.py (35줄)  ★ 피킹 첫행 리뷰 (v8.6.4 신규)
  │   │   └── preview_review_bridge.py (72줄)    ★ 프리뷰-리뷰 브릿지 (v8.6.4 신규)
  │   ├── reports/ (2파일)
  │   │   ├── integrity_report.py (393줄)     정합성 보고서
  │   │   └── return_report_pdf.py (240줄)    반품 PDF
  │   └── notifications/
  │       └── return_alert_email.py (216줄)   이메일 알림
  │
  ├── gui_app_modular/ (122파일, ~51,040줄) ★ GUI 메인 레이어
  │   ├── main_app.py (1,375줄)     메인 앱 클래스 (18개 Mixin 결합)
  │   ├── menu_registry.py (165줄)  메뉴 항목 중앙 정의
  │   ├── preparse_review_dialog.py (333줄) 파싱 전 리뷰
  │   ├── mixins/ (18파일, 9,559줄)
  │   │   ├── toolbar_mixin.py (1,903줄) ★ 메인 툴바
  │   │   ├── advanced_dialogs_mixin.py (2,282줄)  고급 다이얼로그
  │   │   ├── custom_menubar.py (849줄)  커스텀 메뉴바
  │   │   ├── context_menu_mixin.py (718줄) 우클릭 컨텍스트 메뉴
  │   │   ├── menu_mixin.py (486줄)      네이티브 메뉴바
  │   │   ├── keybindings_mixin.py (550줄) 키보드 단축키
  │   │   ├── statusbar_mixin.py (503줄) 상태바
  │   │   ├── theme_mixin.py (393줄)     테마 전환
  │   │   ├── drag_drop_mixin.py (302줄) 드래그&드롭
  │   │   ├── diagnostics_mixin.py (378줄) 진단 도구
  │   │   ├── window_mixin.py (285줄)    창 크기/위치 관리
  │   │   ├── features_v2_mixin.py (413줄) 확장 기능
  │   │   ├── validation_mixin.py (172줄) 폼 검증
  │   │   ├── refresh_mixin.py (164줄)   새로고침
  │   │   ├── database_mixin.py (63줄)   DB 연결
  │   │   └── bulk_import_mixin.py (37줄) 대량 임포트
  │   ├── dialogs/ (41파일, 21,223줄)
  │   │   ├── onestop_inbound.py (4,175줄)   ★ 원스톱 입고
  │   │   ├── onestop_outbound.py (2,303줄)  ★ 원스톱 출고
  │   │   ├── allocation_dialog.py (1,616줄) 배정 다이얼로그
  │   │   ├── allocation_approval_dialog.py (471줄) 승인 워크플로우
  │   │   ├── allocation_preview.py (285줄)  배정 미리보기
  │   │   ├── allocation_template_dialog.py (640줄) 배정 템플릿
  │   │   ├── settings_dialog.py (869줄)     설정
  │   │   ├── help_dialogs.py (729줄)        도움말
  │   │   ├── do_update_dialog.py (546줄)    D/O 후속 연결
  │   │   ├── inbound_upload_mixin.py (538줄) 업로드
  │   │   ├── auto_backup.py (445줄)         자동 백업
  │   │   ├── lot_status_dialog.py (407줄)   LOT 현황
  │   │   ├── lot_detail_dialog.py (357줄)   LOT 상세
  │   │   ├── review_center.py (385줄)       리뷰 센터
  │   │   ├── return_statistics_dialog.py (481줄) 반품 통계
  │   │   ├── return_dialog.py (401줄)       반품 다이얼로그
  │   │   ├── integrity_v760_dialog.py (387줄) 정합성 시각화
  │   │   ├── product_inventory_report.py (203줄) 제품 재고
  │   │   ├── product_master_dialog.py (364줄) 제품 마스터
  │   │   ├── product_master_helper.py (234줄) 제품 마스터 헬퍼
  │   │   ├── picking_template_dialog.py (447줄) 피킹 템플릿
  │   │   ├── picking_list_preview_dialog.py (221줄) 피킹 미리보기
  │   │   ├── inbound_template_dialog.py (461줄) 입고 템플릿
  │   │   ├── inbound_history_dialog.py (339줄)  입고 이력
  │   │   ├── inbound_preview_dialog.py (236줄)  입고 미리보기
  │   │   ├── inbound_dialog_base.py (59줄)  입고 기본 클래스
  │   │   ├── column_mapper_dialog.py (206줄) 컬럼 매퍼
  │   │   ├── location_upload_preview.py (422줄) 위치 업로드 미리보기
  │   │   ├── outbound_preview_dialog.py (255줄) 출고 미리보기
  │   │   ├── tonbag_location_upload.py (324줄)  톤백 위치 업로드
  │   │   ├── Claude_allocation_stress_test_dialog_v712.py (492줄) 스트레스 테스트
  │   │   ├── test_runner_dialog.py (166줄)  테스트 러너
  │   │   ├── info_dialogs.py (25줄)         정보 다이얼로그
  │   │   ├── custom_messagebox.py           커스텀 메시지박스
  │   │   ├── lot_allocation_audit_mixin.py (312줄) ★ 배정 감사 (v8.6.4 신규)
  │   │   ├── dn_cross_check_dialog.py (192줄)     ★ DN 교차검증 (v8.6.4 신규)
  │   │   ├── email_config_dialog.py (157줄)        ★ 이메일 설정 (v8.6.4 신규)
  │   │   ├── parse_error_recovery_dialog.py (304줄) ★ 파싱 에러 복구 (v8.6.4 신규)
  │   │   ├── parse_preview_confirm_dialog.py (347줄) ★ 파싱 미리보기 확인 (v8.6.4 신규)
  │   │   └── preparse_select_dialog.py (407줄)      ★ 파싱 전 선택 (v8.6.4 신규)
  │   ├── handlers/ (16파일, 8,111줄)
  │   │   ├── outbound_handlers.py (2,868줄) ★ 출고 핸들러
  │   │   ├── inbound_handlers.py (1,105줄)  입고 핸들러
  │   │   ├── import_handlers.py (946줄)     임포트 로직
  │   │   ├── pdf_handlers.py (643줄)        PDF 처리
  │   │   ├── backup_handlers.py (457줄)     백업/복구
  │   │   ├── product_handlers.py (305줄)    제품 관리
  │   │   ├── export_handlers.py (186줄)     내보내기
  │   │   ├── status_import_handlers.py (334줄) 상태 임포트
  │   │   ├── inbound_doc_detector.py (278줄) 서류 자동 감지
  │   │   ├── pdf_report_handler.py (233줄)  보고서
  │   │   ├── outbound_template_mixin.py (275줄) 출고 템플릿
  │   │   ├── inbound_processor.py (167줄)   입고 처리기
  │   │   ├── inbound_update_mixin.py (55줄) 입고 업데이트 믹스인
  │   │   ├── simple_excel_outbound.py (218줄) 간편 엑셀 출고
  │   │   └── simple_outbound_handler.py (20줄) 간편 출고 핸들러
  │   ├── tabs/ (15파일, 10,694줄)
  │   │   ├── inventory_tab.py (1,569줄)    ★ 메인 재고 탭
  │   │   ├── tonbag_tab.py (1,522줄)       ★ 톤백 관리 탭
  │   │   ├── dashboard_tab.py (1,229줄)    대시보드
  │   │   ├── dashboard_data_mixin.py (1,376줄) 대시보드 데이터
  │   │   ├── allocation_tab.py (1,039줄)   판매배정 탭
  │   │   ├── scan_tab.py (805줄)           바코드 스캔 탭
  │   │   ├── outbound_scheduled_tab.py (604줄) 출고예정 탭
  │   │   ├── cargo_overview_tab.py (525줄) 총괄재고 탭
  │   │   ├── sold_tab.py (391줄)           출고완료 탭
  │   │   ├── picked_tab.py (437줄)         피킹완료 탭
  │   │   ├── move_tab.py (364줄)           이동 탭
  │   │   ├── log_tab.py (266줄)            로그 탭
  │   │   ├── summary_tab.py (138줄)        요약 탭
  │   │   └── allocation_lot_overview_mixin.py (394줄) LOT 현황
  │   └── utils/ (28파일, 9,701줄)
  │       ├── ui_constants.py (1,549줄)     ★ UI 색상/크기 상수
  │       ├── tree_enhancements.py (1,293줄) TreeView 강화
  │       ├── tonbag_location_uploader.py (877줄) 위치 업로드
  │       ├── pdf_report_gen.py (665줄)     PDF 보고서 생성
  │       ├── ui_ops_helper.py (659줄)      UI 작업 헬퍼
  │       ├── custom_messagebox.py (450줄)  커스텀 메시지박스
  │       ├── theme_refresh.py (435줄)      테마 새로고침
  │       ├── table_styler.py (420줄)       테이블 스타일링
  │       ├── paste_table_dialog.py (350줄) 테이블 붙여넣기
  │       ├── gui_bootstrap.py (325줄)      GUI 부트스트랩
  │       ├── upload_error_template.py (321줄) 업로드 에러 템플릿
  │       ├── upload_error_dialog.py (288줄)  업로드 에러 다이얼로그
  │       ├── helpers.py (241줄)            헬퍼 함수
  │       ├── global_editable_tree.py (231줄) 인라인 편집
  │       ├── auto_tooltip.py (219줄)       자동 툴팁
  │       ├── menu_tab_tooltips.py (198줄)  메뉴/탭 툴팁
  │       ├── safe_utils.py (142줄)         안전 유틸리티
  │       ├── split_panel.py (138줄)        분할 패널
  │       ├── excel_file_helper.py (149줄)  엑셀 처리
  │       ├── column_toggle.py (135줄)      컬럼 토글
  │       ├── global_row_number_tree.py (129줄) 행번호 트리
  │       ├── constants.py (91줄)           상수
  │       ├── duplicate_cleanup.py (83줄)   중복 정리
  │       ├── report_footer.py (83줄)       보고서 푸터
  │       ├── duplicate_guard.py (94줄)     중복 방지
  │       ├── formatters.py (54줄)          포매터
  │       ├── sort_utils.py (35줄)          정렬
  │       └── win32_styling.py              Win32 스타일링
  │
  ├── parsers/ (17파일, 8,006줄)
  │   ├── pdf_parser.py (1,041줄)          ★ PDF 텍스트/테이블 추출
  │   ├── allocation_parser.py (714줄)     배정 데이터 파싱
  │   ├── picking_list_parser.py (526줄)   피킹 리스트
  │   ├── document_detector.py (381줄)     서류 유형 감지
  │   ├── document_models.py (744줄)       데이터 모델
  │   ├── cross_check_engine.py (549줄)    교차 검증
  │   ├── do_free_time_ocr.py (305줄)      D/O Free Time OCR
  │   ├── base.py (41줄)                   기본 파서
  │   └── document_parser_modular/ (8파일, 모듈러 파서)
  │       ├── parser.py (233줄)            메인 오케스트레이터
  │       ├── base.py (307줄)              기본 파싱 로직
  │       ├── bl_mixin.py (611줄)          선하증권(BL) 파싱
  │       ├── do_mixin.py (961줄)          ★ 화물인도지시서(DO) 파싱
  │       ├── invoice_mixin.py (271줄)     인보이스 파싱
  │       ├── packing_mixin.py (554줄)     패킹리스트 파싱
  │       └── picking_mixin.py (482줄)     피킹문서 파싱
  │
  ├── utils/ (11파일, 3,286줄)
  │   ├── backup.py (351줄)              백업
  │   ├── backup_validator.py (280줄)    백업 검증
  │   ├── daily_report.py (333줄)        일일 보고서
  │   ├── date_utils.py (359줄)          날짜 유틸
  │   ├── error_notifier.py (255줄)      에러 알림
  │   ├── common.py (244줄)              공통 유틸
  │   ├── file_utils.py (155줄)          파일 유틸
  │   ├── integrity_check.py (426줄)     정합성 검사
  │   ├── pdf_converter.py (794줄)       PDF 변환
  │   ├── path_utils.py (52줄)           경로 유틸
  │   └── ui_debug.py (37줄)             UI 디버그
  │
  ├── data/
  │   └── db/
  │       ├── sqm_inventory.db             ★ 메인 SQLite DB
  │       └── backups/                     DB 백업
  ├── logs/                                앱 로그
  ├── output/                              내보내기 출력
  ├── backup/                              파일 백업
  ├── temp/                                임시 파일
  └── resources/                           정적 리소스

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[KEY FILES — 빈도순 핵심 파일 목록]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  gui_app_modular/utils/ui_constants.py      (1,549줄) 전체 UI 상수
  gui_app_modular/main_app.py                (1,382줄) 메인 윈도우 + 41개 Mixin
  gui_app_modular/tabs/inventory_tab.py      (1,569줄) 재고 탭
  gui_app_modular/dialogs/onestop_inbound.py (4,175줄) 원스톱 입고 (v865: _create_dialog 530→20줄 분해)
  gui_app_modular/mixins/toolbar_mixin.py    (1,903줄) 메인 툴바 (메뉴 버튼 7개)
  gui_app_modular/mixins/custom_menubar.py   커스텀 메뉴바
  gui_app_modular/menu_registry.py           (165줄) 메뉴 단일 소스
  engine_modules/inventory_modular/outbound_mixin.py (4,040줄) 출고/배정 엔진 (v865: 핵심 3함수 헬퍼 19개 분해)
  engine_modules/inventory_modular/query_mixin.py (722줄) 쿼리 빌더
  engine_modules/constants.py                (265줄) STATUS/MOVEMENT 상수
  parsers/document_parser_modular/bl_mixin.py     BL 파싱
  parsers/document_parser_modular/do_mixin.py     DO 파싱
  parsers/document_parser_modular/packing_mixin.py PL 파싱
  features/ai/gemini_parser.py               (1,821줄) AI PDF 파싱
  config.py                                  (531줄) DB_PATH + 전역 설정

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[CONFIG.PY — 핵심 설정값]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  DB_PATH:           data/db/sqm_inventory.db
  DB_TYPE:           'sqlite' (SQM_DB_TYPE 환경변수로 postgresql 가능)
  DB_TIMEOUT:        30.0초
  DB_WAL_MODE:       True (Write-Ahead Logging)

  PICKING_MAIN_MATERIAL_CODES:  ["30000008", "30000036"]  (리튬카보네이트 본품)
  PICKING_SAMPLE_MATERIAL_CODES: ["30000010", "30000027"] (리튬카보네이트 샘플)
  ★ 자재코드는 SQM 본사 SAP 시스템 발번으로 고객/제품별 상이할 수 있음
  ★ 파서에서 리스트로 비교해야 함 (단일 코드 비교 금지)
  PICKING_DEFAULT_CONTAINERS:   15

  BACKUP_ENABLED:       True
  BACKUP_MAX_COUNT:     5
  BACKUP_INTERVAL_HOURS: 24

  GEMINI_API_KEY:       환경변수 > keyring > settings.ini
  UI_THEME:             "darkly" (ttkbootstrap)
  WINDOW_SIZE:          "1200x800"
  OUTBOUND_MODE:        "random_scan_confirm"
  OUTBOUND_WEIGHT_TOL_PCT: 0.001 (±0.1%)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[STATUS CONSTANTS — engine_modules/constants.py]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  STATUS_AVAILABLE   = 'AVAILABLE'
  STATUS_RESERVED    = 'RESERVED'
  STATUS_PICKED      = 'PICKED'
  STATUS_SOLD        = 'SOLD'        (deprecated, read-only — v865: 전체 write-path OUTBOUND로 전환 완료)
  STATUS_DEPLETED    = 'DEPLETED'
  STATUS_RETURNED    = 'RETURNED'

  OUTBOUND_PENDING   = 'PENDING'
  OUTBOUND_CONFIRMED = 'CONFIRMED'
  OUTBOUND_CANCELLED = 'CANCELLED'

  MOVEMENT_INBOUND   = 'INBOUND'
  MOVEMENT_OUTBOUND  = 'OUTBOUND'
  MOVEMENT_RETURN    = 'RETURN'
  MOVEMENT_ADJUSTMENT= 'ADJUSTMENT'

  WAREHOUSE_CODE     = 'GYL_WH01'
  SAMPLE_WEIGHT_KG   = 0.5
  TONBAG_WEIGHT_500  = 500
  TONBAG_WEIGHT_1000 = 1000
  DATE_FORMAT        = '%Y-%m-%d'
  DATETIME_FORMAT    = '%Y-%m-%d %H:%M:%S'

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[DATA INTEGRITY — NEVER VIOLATE]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. HIERARCHY: BL_NO > LOT_NO > TONBAG_NO (sub_lt)
   Sample: sub_lt=0, tonbag_no='S00', is_sample=1 — never allocate/pick/sell

2. WEIGHT LAW: initial_weight == current_weight + picked_weight (±1.0kg)

3. STATUS FLOW: AVAILABLE→RESERVED→PICKED→OUTBOUND
   STATUS_SOLD = deprecated read-only. All writes → STATUS_OUTBOUND
   ★ v865: SOLD write-path 0건 달성 (barcode_scan_engine, sales_order_engine, outbound_mixin 전부 OUTBOUND)
   ★ read-path는 하위호환 유지 (WHERE status IN ('OUTBOUND','SOLD'))

4. STOCK: CURRENT = AVAILABLE + RESERVED + PICKED + RETURN

5. HARD STOP: LOT missing / weight=0 / status reversal / partial commit

6. LOT 모드 예약: allocation_plan.tonbag_id = NULL (스캔 전까지 톤백 미확정)
   스캔 시 tonbag_id 확정 → status AVAILABLE→PICKED

7. 샘플 정책: sub_lt=0, tonbag_no='S00', is_sample=1, weight=1kg
   LOT당 1개 고정. 일반 톤백과 별도 집계.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[MENU SYSTEM — menu_registry.py 중앙 정의]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  파일 > 입고 (6섹션):
    PDF 스캔 입고, 엑셀 수동 입고, D/O 후속 연결,
    톤백 위치 매핑, 대량 이동 승인, 반품 재입고,
    입고 현황, 파싱 템플릿, 제품 마스터, 이메일 설정,
    정합성 검증, LOT 상태 복구

  파일 > 출고 (4섹션):
    즉시 출고(원스톱), 빠른 출고(붙여넣기),
    Picking List, 바코드 스캔, Allocation,
    승인 대기, 예약 반영, 출고 현황,
    Sales Order, Swap 리포트

  보고서 (10+옵션):
    거래명세서, Detail of Outbound, Sales Order DN,
    재고 현황, 입출고 내역, 월간/일일 PDF, LOT 상세

  설정/도구:
    새로고침, 창 크기, DB 최적화, 로그 정리,
    정합성 검사, DB 정보, 시스템/버전 정보

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[DOCUMENT PARSING PIPELINE — 선사별 파서 체계]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  입고 문서 4종: BL(선하증권) → PL(패킹리스트) → FA(인보이스) → DO(화물인도지시서)

  파싱 우선순위:
    1단계: 좌표 기반 파서 (carrier_templates/ — MSC, MAERSK, HMM/CMA CGM)
    2단계: carrier_rule 좌표 파서 (DB 등록 템플릿)
    3단계: Gemini Vision AI 폴백 (gemini_parser.py)

  선사 자동 감지:
    BL 텍스트 기반 스코어링 (bl_mixin.py → _detect_carrier_from_words)
    MEDU*/MSCU* → MSC, MAEU*/MRKU* → MAERSK

  서류 유형 자동 감지:
    InboundDocDetector (inbound_doc_detector.py)
    파일명 + 텍스트 키워드 기반 BL/PL/FA/DO 분류
    감지 실패 시 선택 순서 fallback (BL→PL→FA→DO)

  교차 검증:
    cross_check_engine.py — BL↔PL↔FA↔DO 간 필드 비교
    BL No, Vessel, Container 번호/수 교차 검증

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[ALLOCATION EXCEL 양식 — Song / Woo 2종]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ── Song 양식 (단일 시트 'Allocation', 헤더 2행) ────────
    Row 1: 타이틀 "Allocation - CATL KOREA CO., LTD - July 2026"
    Row 2: 컬럼 헤더
    Row 3+: 데이터 (본품 + 샘플 혼재)

    컬럼: Product | SAP NO | Date in stock | QTY (MT) | Lot No |
          WH | Customs | SOLD TO | SALE REF | GW

    본품: Product=LITHIUM CARBONATE, QTY=0.5~5 MT
    샘플: Product=LITHIUM CARBONATE sample, QTY=0.001 MT
    ★ 모든 LOT에 샘플이 붙는 것은 아님 (고객 요청분만)

  ── Woo 양식 (단일 시트 'Sheet1', 헤더 6행) ────────────
    Row 1: 타이틀 "Allocation - PT LBM JAKARTA - June 2026"
    Row 2~5: 빈 행 (Woo 양식 특성)
    Row 6: 컬럼 헤더
    Row 7+: 데이터

    컬럼: Product | SAP NO | Date in stock | QTY (MT) | Lot No |
          WH | Customs | Export | SOLD TO | SALE REF | Balance | GW | Remark

    Export 컬럼: '반송' / '일반수출' (Woo 양식 전용)

  ── 샘플 배정 정책 ────────────────────────────────────────
    샘플은 LOT당 1개(1kg) 총 88개 고정이지만,
    출고 시 모든 LOT에 샘플이 같이 나가는 게 아님.
    고객이 요청한 LOT만 샘플 행이 붙고, 나머지는 본품(톤백)만 출고.
    → Song 88LOT 중 17개만 샘플, Woo 88LOT 중 20개만 샘플 = 정상

  ── 파서: parsers/allocation_parser.py ────────────────────
    AllocationParser.parse(excel_path) → AllocationData
    양식 자동 감지: _select_best_sheet() (다중 시트 → 최적 시트 선택)
    헤더 자동 탐색: LOT+PRODUCT 컬럼 기반 헤더 행 감지
    샘플 자동 분류: qty_mt < 0.01 → AllocationRow.is_sample=True
    Balance fallback: QTY(MT) 없으면 Balance 컬럼 사용 (Woo 양식)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[PICKING LIST EXCEL 양식 — SQM 본사 발행]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  시트명: 'Picking List'
  구조 (row 기준):
    Row 1:  SQM 로고 + "PICKING LIST"
    Row 5:  Outbound ID: 80003001    Invoice account: PT LBM JAKARTA
    Row 6:  Sales order: WOO-810     Enterprise number: 5068101452
    Row 8:  Customer reference: PF_WOO202601
    Row 10: Creation Date: 05.08.2026  Delivery address: GY Logistics
    Row 14: Plan Loading Date: 05.08.2026
    Row 20: ── 자재 섹션 1: 샘플 ──
            Material=30000027  Description=LHT-B SAMPLE 1 kg/N/A
            Quantity=7 KG  (= 이 피킹에서 샘플 나가는 LOT 7개)
    Row 22~28: "Quantity: 1.00  KG      Batch number: 1126010xxx"
               (LOT별 1행, 1kg씩)
    Row 29~31: Packing/Weight 요약 (Net=7.00 KG, Gross=7.35 KG)
    Row 33: ── 자재 섹션 2: 본품 ──
            Material=30000036  Description=LHT-B LHTB-B450/CL-P900PL
            Quantity=33.5 MT
    Row 35~75: "Quantity: 0.50~2.50  MT      Batch number: 1126010xxx"
               (LOT별 1행, 배정된 MT만큼)
    Row 76~78: Packing/Weight 요약 (Net=33,500 KG, big bags 67개)
    Row 83~85: SOQUIMICH LLC. 푸터

  ★ 자재코드는 SQM 본사 SAP 발번으로 고객/제품별 상이:
    30000027 = LHT-B SAMPLE (샘플, KG)      ← 현재 피킹리스트
    30000036 = LHT-B (본품, MT)             ← 현재 피킹리스트
    30000008 = LITHIUM CARBONATE (본품, MT)  ← 기존 config
    30000010 = LITHIUM CARBONATE SAMPLE     ← 기존 config
    → 파서에서 리스트로 비교해야 함

  ── 테스트 데이터 파일 (6개) ──────────────────────────────
    outbound/PickingList_Woo_20260805_1of3.xlsx  (Woo 1차, 33.5MT)
    outbound/PickingList_Woo_20260815_2of3.xlsx  (Woo 2차)
    outbound/PickingList_Woo_20260825_3of3.xlsx  (Woo 3차)
    outbound/PickingList_Song_20260905_1of3.xlsx (Song 1차)
    outbound/PickingList_Song_20260915_2of3.xlsx (Song 2차)
    outbound/PickingList_Song_20260925_3of3.xlsx (Song 3차)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[SALES ORDER DN 양식 — 출고 확정 후 생성]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  시트명: 'DN'
  구조:
    Row 2: ■ DN
    Row 3: ■ Sales order No : MSO-260318
    Row 4: 합계 (NW MT, GW MT, CT/PLT) — col K,L,M
    Row 5: 컬럼 헤더
    Row 6+: 본품 행 (MIC9000)
    Row N+: 샘플 행 (MIC9000 Sample) — 본품 뒤에 모아서 배치

  컬럼: (col B~M, A열은 빈칸)
    Destination | Delivery Date | LOT NO | SAP NO | BL NO |
    Sales order No | Picking No | SKU | Description |
    NW(MT) | GW(MT) | CT/PLT

  본품 행 예시:
    JAKARTA TRIAL | 2026-03-24 | 1125082734 | 2200033062 | MAEU258469048 |
    JAKARTA TRIAL (2026-03) MSO-260318 | Jakarta Trial |
    MIC9000 | LITHIUM CARBONATE | 5 | 5.13 | 5

  샘플 행 예시:
    ... | MIC9000 Sample | LITHIUM CARBONATE (샘플) | 0.001 | 0.00125 | 1

  ★ CT/PLT: 본품=톤백수(500kg 기준), 샘플=1 고정
  ★ GW = NW × 1.026 (포장 중량 비율)

  참조 파일: 박아름_Sales order No (26.03.24) - MSO-260318.xlsx

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[DETAIL OF OUTBOUND 양식 — 출고 보고서]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  시트명: 'Outbound'
  구조: Sales Order DN과 동일 레이아웃
    Row 2: ■ Outbound report
    Row 3: ■ Date : 2026-03-24
    Row 4: 합계 (NW MT, GW MT, CT/PLT)
    Row 5: 컬럼 헤더 (Sales Order DN과 동일)
    Row 6+: 본품 + 샘플 데이터

  차이점 (Sales Order DN vs Outbound Report):
    - 타이틀: "■ DN" vs "■ Outbound report"
    - Row 3: "Sales order No" vs "Date"
    - Sales order No 컬럼: 약식 vs 전체 (MSO-260318 포함)
    - 나머지 데이터 동일

  참조 파일: 박아름-Detail of Outbound (26.03.24) - MSO-260318.xlsx

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[보고서 생성 로직 — v8.6.4 핵심 규칙]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ── Detail of Outbound: 출고될 때마다, 일별로 작성 ──────

    출고 발생 → delivery_date 기준 날짜별 시트 자동 생성
    예) 3번 출고 시:
      시트 1: 20260805  (1차 출고)
      시트 2: 20260815  (2차 출고)
      시트 3: 20260825  (3차 출고)
      시트 0: ALL       (전체 요약, 2일 이상인 경우)

    구현: export_mixin.py → _export_outbound_report()
      defaultdict(list) 로 delivery_date별 그룹핑
      날짜별 wb.create_sheet(title=safe_name)
      각 시트마다 _write_outbound_sheet() 호출

  ── Sales Order DN: 전체 출고 완료 시 1회만 작성 ────────

    DN 생성 요청
      ↓
    _check_sales_order_completion(sale_ref)
      ↓
    allocation_plan의 전체 LOT ←→ sold_table 완료 LOT 비교
      ↓
    미완료 → INCOMPLETE:{out_cnt}/{total_cnt} 반환
      → 팝업: "Sales Order 'XXX' 미완료 (출고 67/200 LOT)"
      → 파일 미생성
      ↓
    완료 → DN 보고서 1회 생성 (Excel + PDF)

    구현:
      export_mixin.py → _check_sales_order_completion()
      export_mixin.py → _export_sales_order_dn_report()
      advanced_dialogs_mixin.py → INCOMPLETE: 감지 후 경고 팝업

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[ALLOCATION & OUTBOUND FLOW — 6단계 프로세스]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  STEP1: Allocation Excel 업로드 → allocation_plan INSERT (RESERVED)
         allocation_plan.tonbag_id = NULL (LOT 모드, 톤백 미확정)
  STEP2: Picking List Excel 업로드 → 파싱 → picking_table INSERT (ACTIVE)
         피킹 단계에서는 톤백 상태 변경 안 함 (RUBI-PHASE2)
  STEP3: 현장 바코드 스캔 → tonbag_id 확정 + AVAILABLE→PICKED
         (스캔 없이도 tonbag_uid=NULL로 진행 가능)
  STEP4: Sales Order Excel 업로드 → picking_table 매칭 → sold_table INSERT
         매칭 기준: (lot_no, picking_no, is_sample) 튜플
  STEP5: 출고확정 → PICKED→OUTBOUND + sold_table.status='OUTBOUND'
  STEP6: 보고서 생성 → Detail of Outbound (Excel+PDF) + Sales Order DN

  스캔 후 테이블 업데이트:
    inventory_tonbag: status AVAILABLE→PICKED→OUTBOUND
    picking_table:    lot_no, tonbag_uid, picking_no, customer INSERT
    allocation_plan:  tonbag_id 확정, status=EXECUTED
    sold_table:       lot_no, tonbag_uid, sales_order_no INSERT (20필드)

  자재코드 체계 (SQM 본사 SAP 발번, 고객/제품별 상이):
    30000008 / 30000036 → 본품 (LITHIUM CARBONATE / LHT-B, 단위: MT)
    30000010 / 30000027 → 샘플 (LITHIUM CARBONATE SAMPLE / LHT-B SAMPLE, 단위: KG)
    ★ 파서에서 리스트로 비교 (config.PICKING_MAIN_MATERIAL_CODES)

  SQM DB SAP NO (출하 문서번호 10자리):
    2200034273 → 선적 건별 발번 (자재코드와 혼동 금지)

  ── 프로그래밍 자동화 가능 여부 ────────────────────────────
    ✅ Allocation 업로드 → allocation_plan INSERT
    ✅ Picking List 파싱 → picking_table INSERT
    ⚠️ 바코드 스캔 → 스킵 가능 (tonbag_uid=NULL)
    ✅ Sales Order 업로드 → sold_table INSERT
    ✅ Outbound Report 생성 → Excel/PDF
    → 바코드 스캔 제외하면 중단 없이 자동 처리 가능

  ── Allocation 지원 양식 6종 ────────────────────────────────
    A) Song    양식: 다중시트, Sheet1(요약)+데이터시트 자동선택
    B) Woo     양식: 단일시트, 1~5행헤더, Balance/Export/Remark, 피벗우측혼재
    C) 기존    양식: 1행타이틀, 2행무시, 3행헤더, 4행~데이터
    D) 화주원본: 1행=합계숫자, 2행=헤더, 3행~데이터
    E) Easpring양식: 1~10행=피벗, 14행=헤더(SC RCVD 추가), 15행~데이터
       → sc_rcvd(수령확인일) allocation_plan.sc_rcvd에 저장
       → date_in_stock 엑셀 시리얼 자동 변환 (45952→2025-10-22)
    F) Jakarta 양식: 1행=타이틀, 3행=컬럼+피벗혼재, 4행~데이터
       → 'Cleared' → customs 자동 매핑
       → 'Uncleaared' → 'uncleared' 오타 자동 정규화

  ── 테스트 데이터 파일 위치 ────────────────────────────────
    입고: inbounnd/SQM-Inventory-2026_03_26.xlsx (88 LOT)
          inbounnd/SQM-SubLOT-2026_03_26.xlsx (968 톤백)
    배정: inbounnd/Allocation_Song_202607.xlsx (Song 88 LOT)
          inbounnd/Allocation_Woo_202606.xlsx (Woo 88 LOT)
    피킹: outbound/PickingList_Woo_2026080x_Nof3.xlsx (3개)
          outbound/PickingList_Song_2026090x_Nof3.xlsx (3개)
    참조: 박아름_Sales order No (26.03.24) - MSO-260318.xlsx
          박아름-Detail of Outbound (26.03.24) - MSO-260318.xlsx

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[v8.5.9~v8.6.4 주요 변경 이력]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

v8.6.4 (2026-03-28):
  [코드 품질] Full audit: 빈 except 27건 + _log 중복 수정
  [Dead code] 7개 파일(207줄) 제거
  [리팩토링] 서브메서드 12개 추가: inbound/return/cancel/G1/do/scan 분해
  [DB 인덱스] 3개 신규: tb_status_is_sample / sold_delivery / mv_lot_type
  [파서] v2.7.1: E/F 양식 + 엑셀시리얼 변환 + customs 정규화 + SC_RCVD
  [신규 엔진] dn_cross_check_engine.py — DN 교차검증 엔진 (298줄)
  [신규 엔진] inventory_validator.py — 인벤토리 검증 (53줄)
  [신규 엔진] lot_balance_checker.py — LOT 잔액 체크 (25줄)
  [신규 엔진] tonbag_patch_rules.py — 톤백 패치 규칙 (17줄)
  [신규 엔진] tonbag_weight_rules.py — 톤백 무게 규칙 (75줄)
  [신규 다이얼로그] lot_allocation_audit_mixin.py — 배정 감사 (312줄)
  [신규 다이얼로그] dn_cross_check_dialog.py — DN 교차검증 UI (192줄)
  [신규 다이얼로그] email_config_dialog.py — 이메일 설정 (157줄)
  [신규 다이얼로그] parse_error_recovery_dialog.py — 파싱 에러 복구 (304줄)
  [신규 다이얼로그] parse_preview_confirm_dialog.py — 파싱 미리보기 확인 (347줄)
  [신규 다이얼로그] preparse_select_dialog.py — 파싱 전 선택 (407줄)
  [신규 파서] candidate_scorer.py — 후보 스코어링 (105줄)
  [신규 파서] picking_candidate_patch.py — 피킹 후보 패치 (310줄)
  [신규 파서] picking_firstrow_review.py — 피킹 첫행 리뷰 (35줄)
  [신규 파서] preview_review_bridge.py — 프리뷰-리뷰 브릿지 (72줄)
  [신규 AI] natural_edit_bridge.py — 자연어 편집 브릿지 (27줄)

v8.6.3 (2026-03-27):
  [초기화면] main_app.py: 시작 탭 tab_inventory → tab_dashboard
             after(0) 즉시 선택 + after(800) 데이터 새로고침 + 사이드바 키 dashboard
  [Allocation 파서] allocation_parser.py v2.7.1:
             ① rows.sort(is_sample, lot_no) — 본품 전체 → 샘플 처리 순서 보장
             ② E) Easpring 양식 지원: 1~10행=피벗, 14행=헤더, 탐색범위 30행
                F) Jakarta  양식 지원: 'Cleared' → customs 매핑, 피벗 우측 무시
             ③ date_in_stock 엑셀 시리얼 숫자 → YYYY-MM-DD 자동 변환
             ④ customs 자동 정규화: 'Uncleaared'→'uncleared', 'CLEARED'→'cleared'
             ⑤ AllocationRow.sc_rcvd 필드 추가 (수령확인일, Easpring SC RCVD 컬럼)
             ⑥ alias_patterns: 'SC RCVD', 'Cleared', 'Received Date' 등 추가
  [DB 마이그레이션] db_migration_mixin.py v2.7.1:
             allocation_plan.sc_rcvd TEXT 컬럼 추가
             _migrate_v271_allocation_sc_rcvd() 자동 실행
  [outbound_mixin] sc_rcvd_val 추출 + has_sc_rcvd_col 플래그 + payload 3곳 저장
  [LOT 현황] lot_status_dialog.py: 샘플 표시 개선
             본품 미완료 시 → '1개 (본품 출고 후)' 표시
             본품 전량 완료 후 → '1개 AVAIL/RSV/DONE' 표시
  [날짜 UI 통일] tree_enhancements.py: make_date_range_bar() 공통함수 신규 생성
             표준 UI: [시작일] 📅 ~ [종료일] 📅 [🔍조회] [✕초기화]
             적용 13개 메뉴: Outbound탭/화물총괄/입고이력/Allocation/반품통계/
                              툴바/원스톱출고/PDF보고서/보고서(Outbound+DN)
  [캘린더 팝업] show_date_calendar() 전면 개선
             - 연도/월 Combobox 직접 선택 (±5년)
             - 오늘 날짜 Cyan-400 하이라이트
             - 토=파란색(Blue-400) / 일=빨간색(Red-400)
             - 호버 효과, 오늘/이 달로/✕닫기 버튼
  [보고서] export_mixin.py:
             Detail of Outbound → delivery_date별 날짜 시트 자동 분리
             Sales Order DN → _check_sales_order_completion() 완료 체크
               미완료 시 INCOMPLETE:{N}/{M} 반환 → 경고 팝업, 파일 미생성

v8.6.2 (2026-03-26):
  [G5] N+1 제거: 루프 전 IN절 일괄 조회 (LOT N개→fetchall 2회)
  [G5/G2/LOT모드] COUNT*500→SUM(qty_mt*1000) 하드코딩 제거
  [G5/G2] STAGED/PENDING_APPROVAL 예약 점유량 포함
  [allocation_dialog] qty_mt=0 행 차단 (tree sync)

v8.6.0 (2026-03-26):
  MXBG 검증 로직 개선

v8.5.9 (2026-03-26):
  멀티 파일 선택: Ctrl+클릭으로 BL/PL/FA/DO 한번에 선택
  InboundDocDetector 파일명/텍스트 기반 서류 유형 자동 감지
  선사 순서 자유화: BL 파싱 시 선사 자동 감지 → 템플릿 자동 매칭
  DO 좌표파서 free_time_info 누락 버그 수정
  Allocation 중복 LOT 오판 버그 수정
  INVALID_SALE_REF 차단 → 경고로 완화
  MXBG 초과 오판 수정 (샘플 is_sample 포함)
  샘플 행 STAGED 충돌 수정

v8.5.7 (2026-03-26):
  파싱 통합: CON RETURN/FREE TIME, MSC FA 좌표, BL GW 보강
  출고 보고서: sold_table INSERT 20필드 보강 + 마이그레이션
  Detail of Outbound (Excel+PDF) + Sales Order DN (Excel+PDF)

v8.5.5 (2026-03-25):
  코드베이스 정리: 사문 파일 삭제 (~13,800줄 제거)

v8.4.0 (2026-03-24):
  Phase 8 웹 계획 + 시스템 감사 Phase 9~11
  N+1 쿼리 최적화 7곳, Dead code 27개 제거
  PRO DARK 테마, audit_helper, migration_manager

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[PHASE 0: FULL PROCESS LOGIC AUDIT — RUN FIRST]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Before any fix or migration, audit the entire business logic.
Run ALL checks below. Log every issue found.
Fix critical issues (P1) before moving to Phase 1.

── AUDIT-1: STATUS FLOW VIOLATIONS ───────────────────

  Check every status write path in engine_modules/:
  grep -rn "UPDATE.*status.*=" engine_modules/ --include="*.py"

  Verify each write uses correct status:
  - New writes: must use STATUS_OUTBOUND (never 'SOLD')
  - AVAILABLE → RESERVED → PICKED → OUTBOUND only
  - No reverse transitions (OUTBOUND → PICKED is illegal)

── AUDIT-2: WEIGHT CONSERVATION LAW ──────────────────

  For every inbound, outbound, return operation, verify:
  initial_weight == current_weight + picked_weight  (±1.0kg)

── AUDIT-3: SAMPLE POLICY ENFORCEMENT ────────────────

  Sample rule: sub_lt=0, tonbag_no='S00', is_sample=1
  Must NEVER appear in: allocation, picking, outbound
  (qty_mt < 0.01 → is_sample=True 자동 분류)

── AUDIT-4: ALL-OR-NOTHING TRANSACTIONS ──────────────

  Every multi-step operation must be wrapped in:
    try:
        db.execute("BEGIN")
        ... all operations ...
        db.execute("COMMIT")
    except Exception:
        db.execute("ROLLBACK")
        raise

── AUDIT-5~8: (기존 감사 항목 동일하게 유지) ─────────

  AUDIT-5: HARD STOP VALIDATION
  AUDIT-6: RETURN LOGIC INTEGRITY
  AUDIT-7: MOVE LOCATION ONLY
  AUDIT-8: SILENT FAIL IN ENGINE
    grep -rn "except.*pass\|except Exception:$" \
      engine_modules/ --include="*.py" | grep -v "#"
    Replace ALL with: logger.error() + raise

── AUDIT-9: CARRIER_ID CHAIN VERIFICATION ────────────

  Verify carrier_id flows correctly:
  onestop_inbound.py → parse_bl_with_candidate() → parse_bl()
    → CARRIER_COORD_TABLE lookup
    → _auto_match_template_by_carrier (v8.5.9 추가)

── AUDIT-10: PYTEST FULL RUN ─────────────────────────

  python -m pytest tests/ -v --tb=short 2>&1

  Categorize every failure:
  - Data integrity failure → P1 fix immediately
  - Logic error → P1 fix immediately
  - UI test failure → P2 (acceptable during migration)
  - Missing coverage → P3 add test

── PHASE 0 COMPLETE WHEN ─────────────────────────────

  ✅ All 10 audits complete with findings logged
  ✅ P1 issues (data corruption risk) all fixed
  ✅ pytest passes all engine tests

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[PHASE 1: BUG FIXES + UI IMPROVEMENTS]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Run iterative cycles until ALL bugs fixed and UI improved.

── BUG FIXES (v8.6.4 기준 확인 필요) ─────────────────

BUG-FIX-1 [P1] 출고확정 스캔 시 sold_table 자동 INSERT 확인:
  File: gui_app_modular/tabs/scan_tab.py
  확인: _on_quick_outbound()에서 OUTBOUND + sold_table 동시 처리

BUG-FIX-2 [P1] RESERVED UNION 집계 (LOT모드+톤백모드):
  File: engine_modules/inventory_modular/query_mixin.py
  확인: get_cargo_overview_counts() LOT모드 누락 없음

BUG-FIX-3 [P1] Allocation MXBG 검증 N+1 쿼리 제거 (v8.6.2):
  File: engine_modules/inventory_modular/outbound_mixin.py
  확인: IN절 일괄 조회, STAGED/PENDING_APPROVAL 포함

BUG-FIX-4 [P1] 출고예정 할당 kg — tonbag_id NULL 분기:
  File: engine_modules/inventory_modular/query_mixin.py
  확인: tonbag_id IS NULL → qty_mt × 1000

BUG-FIX-5 [P2] 대시보드 판매배정 카드 3단 표시:
  File: gui_app_modular/tabs/dashboard_data_mixin.py
  확인: allocation_plan 기준 reserved_lot_cnt 정상

── UI IMPROVEMENTS ────────────────────────────────────

UI-1 [P1] Fix silent failures in gui_app_modular/:
  Replace every: except: pass / except Exception: pass
  With:          except Exception as e: logger.warning(f"[UI] {context}: {e}")

UI-2 [P1] Theme unification:
  PRO DARK 테마 (v8.3.3 이후) 확인
  Slate-900 배경 + Cyan-400 강조 + 색맹 대응

UI-3 [P2] Status badge pills in all tables:
  AVAILABLE→green RESERVED→blue PICKED→amber OUTBOUND→gray RETURN→coral

── v8.6.3 완료된 UI 작업 ────────────────────────────

UI-DONE-1 [완료] 초기화면 대시보드:
  main_app.py L441: notebook.select(self.tab_dashboard) + after(800, _refresh_dashboard)

UI-DONE-2 [완료] 날짜 입력 UI 통일 (13개 메뉴):
  tree_enhancements.py: make_date_range_bar() 공통함수
  적용: sold_tab / cargo_overview_tab / inbound_history_dialog /
        advanced_dialogs_mixin / allocation_dialog /
        return_statistics_dialog / toolbar_mixin /
        onestop_outbound / pdf_handlers

UI-DONE-3 [완료] 캘린더 팝업 개선:
  show_date_calendar(): Combobox 연월 / 오늘 하이라이트 / 토일 색상 / 호버 / 버튼 3개

UI-DONE-4 [완료] LOT 현황 샘플 표시 개선:
  lot_status_dialog.py: 본품 미완료 = '1개 (본품 출고 후)'

UI-DONE-5 [완료] Allocation 파서 순서 보장:
  allocation_parser.py: rows.sort(key=lambda r: (r.is_sample, r.lot_no))

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[UI EXCELLENCE DIRECTIVE — MANDATORY]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

You must pursue the BEST possible UI through iterative refinement.
This is not optional — premium look and feel is a core requirement.

DESIGN GOAL: Professional, premium logistics management software.
             Think Bloomberg Terminal × SAP Fiori — not a basic tkinter app.

── UI ITERATION PROTOCOL ─────────────────────────────

  STEP 1: Implement current UI improvement
  STEP 2: Take a mental screenshot — ask yourself:
            "Would a Fortune 500 logistics manager find this
             impressive and intuitive?"
  STEP 3: If answer is NO → iterate immediately
  STEP 4: Try minimum 3 different approaches per component
  STEP 5: Pick the most polished result → apply
  STEP 6: Log: # UI-ITER: [component] v1→v2→v3 → chose v[N] ([reason])

  Keep iterating until the answer to STEP 2 is YES.

── PREMIUM UI STANDARDS ──────────────────────────────

  Visual hierarchy:
    - Primary actions: Large, colored CTA buttons (Cyan-400 on Dark)
    - Secondary: Outlined or ghost buttons
    - Destructive: Red-500, requires confirmation
    - Disabled: 40% opacity, not hidden

  Typography & Spacing:
    - Font: 맑은 고딕 / Segoe UI (Windows), size 9~11pt data, 13pt+ headers
    - Consistent padding: 8px / 12px / 16px grid
    - Table row height: min 26px, hover highlight
    - Section headers: uppercase + letter-spacing + subtle separator line

  Color palette (PRO DARK):
    - Background:   #0F172A (Slate-900)
    - Surface:      #1E293B (Slate-800)
    - Border:       #334155 (Slate-700)
    - Text primary: #F1F5F9 (Slate-100)
    - Text muted:   #94A3B8 (Slate-400)
    - Accent:       #22D3EE (Cyan-400)   ← primary action color
    - Success:      #4ADE80 (Green-400)  ← AVAILABLE
    - Warning:      #FBBF24 (Amber-400)  ← PICKED / warning
    - Error:        #F87171 (Red-400)    ← error / OUTBOUND
    - Info:         #60A5FA (Blue-400)   ← RESERVED

  Component standards:
    - Every dialog: rounded corners (4px), subtle drop shadow
    - Tables: alternating row colors (#0F172A / #1E293B), sticky header
    - Buttons: min-width 80px, 6px padding, hover + active states
    - Input fields: focus ring (Cyan-400, 2px), placeholder text
    - Scrollbars: slim (8px), styled to match theme
    - Loading states: spinner or progress bar — never frozen UI
    - Empty states: icon + message (not blank table)
    - Tooltips: on all icon-only buttons and truncated text

  Micro-interactions:
    - Button click: brief color shift feedback
    - Table row select: smooth highlight transition
    - Dialog open: fade-in (100ms)
    - Status change: badge color transition

── COMPONENTS TO ITERATE ─────────────────────────────

  Priority order (highest → lowest):
  1. Main toolbar (toolbar_mixin.py)          ← most visible
  2. Dashboard cards (dashboard_data_mixin.py) ← first impression
  3. Inventory table (inventory_tab.py)        ← most used
  4. Allocation dialog (allocation_dialog.py)  ← most complex
  5. Onestop inbound dialog                   ← daily workflow
  6. Sidebar / navigation (if present)
  7. All other dialogs

── ITERATION LOG FORMAT ──────────────────────────────

  After each UI component is finalized, append to report:

  UI-RESULT: [component]
    Approach tried: [v1 description] → [v2 description] → [v3 description]
    Chosen:         [vN] — reason: [why this is most premium]
    Screenshot ref: [description of final look]

── NEVER DO (UI) ─────────────────────────────────────

  - Never leave a component "good enough" without trying alternatives
  - Never use default tkinter gray (#F0F0F0) anywhere
  - Never use Times New Roman or default system font for data
  - Never place buttons without hover/active state
  - Never show raw error tracebacks to users
  - Never use MessageBox.showinfo for success — use subtle status bar update
  - Never let table columns be unresizable

── PHASE 1 COMPLETE WHEN ─────────────────────────────

  ✅ All P1 bugs verified fixed
  ✅ Silent exception handlers eliminated
  ✅ pytest passes all engine tests

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[PHASE 2: STABILITY + EFFICIENCY + USABILITY — v8.6.5]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Phase 2는 안정성/효율성/편리성 3축 개선. Phase 1 완료 후 자동 시작.
각 항목별로 수정 → 테스트 → 로그 확인 → 다음 항목.

── PHASE 2-A: 즉시 수정 (1~5줄 변경, P0~P2) ──────────

STAB-1 [P0] process_outbound DB 잠금 크래시 방지:
  File: engine_modules/inventory_modular/outbound_mixin.py
  Line: ~671 (except 절)
  현재: except (ValueError, TypeError, AttributeError) as e:
  수정: except (ValueError, TypeError, AttributeError,
               sqlite3.OperationalError, sqlite3.IntegrityError, OSError) as e:
  이유: DB 잠금/디스크 오류 시 unhandled exception으로 크래시

STAB-2 [P2] transaction() rollback 범위 확대:
  File: engine_modules/database.py
  Line: ~266-279 (transaction context manager __exit__)
  현재: except (sqlite3.OperationalError, sqlite3.IntegrityError, ValueError, OSError):
  수정: except Exception:  (rollback 후 re-raise)
  이유: TypeError/KeyError 등 발생 시 rollback 안 되어 부분 커밋

STAB-3 [P2] confirm_outbound double-SOLD 체크 실패 시 중단:
  File: engine_modules/inventory_modular/outbound_mixin.py
  Line: ~2605-2624
  현재: except → logger.debug → 계속 진행
  수정: except → logger.error → result['errors'].append → return result
  이유: safety guard 실패를 무시하면 중복 출고 가능

PERF-1 [P2] Treeview 일괄 삭제 (전 탭 공통):
  대상: gui_app_modular/tabs/*.py 의 모든 Treeview 새로고침 함수
  현재: for item in tree.get_children(): tree.delete(item)
  수정: tree.delete(*tree.get_children())
  이유: 아이템별 삭제 → 단일 호출, 500행 기준 3배 빨라짐

CLEAN-1 [P3] inbound_mixin.py re 중복 import 제거:
  File: engine_modules/inventory_modular/inbound_mixin.py
  Line: ~88
  현재: import re as _re (함수 내부, 모듈 레벨에도 import re 있음)
  수정: 내부 import 삭제, 모듈 레벨 re 사용

── PHASE 2-B: 핵심 구조 개선 (P1, 15~50줄) ────────────

PERF-2 [P1] Lazy Tab Refresh (dirty flag 시스템):
  대상: gui_app_modular/mixins/refresh_mixin.py + main_app.py
  현재: _safe_refresh() → 8개 탭 전체 새로고침 (1~3초 UI 멈춤)
  수정:
    1) main_app.__init__에 self._dirty_tabs = set() 추가
    2) _mark_tabs_dirty(*tab_names) 메서드 추가
    3) _safe_refresh() → 현재 탭 + dirty 탭만 새로고침
    4) <<NotebookTabChanged>> 핸들러에서 dirty면 새로고침
    5) 각 handler에서 _safe_refresh() 대신 _mark_tabs_dirty('inventory', 'dashboard') 등 호출
  효과: DB 쿼리 70% 감소, UI 멈춤 제거

PERF-3 [P1] 대시보드 백그라운드 새로고침:
  File: gui_app_modular/tabs/dashboard_tab.py
  현재: _refresh_dashboard() → 7개 DB 쿼리 순차 실행 (메인 스레드)
  수정:
    1) threading.Thread(target=_fetch_dashboard_data) 로 DB 조회
    2) _fetch_dashboard_data() 안에서 1~2개 통합 쿼리로 전체 통계 수집
    3) self.root.after(0, lambda: _apply_dashboard_data(data)) 로 UI 업데이트
  효과: 대시보드 진입 시 UI 멈춤 완전 제거

STAB-4 [P1] fix_lot_status_integrity N+1 제거 + 트랜잭션:
  File: engine_modules/inventory_modular/outbound_mixin.py
  Lines: ~277-295
  현재: for loop 안에서 개별 fetchone (N+1) + 트랜잭션 없음
  수정:
    1) 초기 GROUP BY에 SOLD/OUTBOUND 카운트 포함:
       SELECT lot_no,
         SUM(CASE WHEN status IN ('AVAILABLE','RESERVED') THEN 1 ELSE 0 END) as avail_cnt,
         SUM(CASE WHEN status IN ('SOLD','OUTBOUND') THEN 1 ELSE 0 END) as sold_cnt
       FROM inventory_tonbag GROUP BY lot_no
    2) with self.db.transaction("IMMEDIATE"): 로 감싸기
  효과: N+1 쿼리 제거, 부분 수정 방지

PERF-4 [P1] 시작 시 deferred tasks 통합:
  File: gui_app_modular/main_app.py
  Lines: ~199-220, 457-458, 543-549, 700-713
  현재: 12개 root.after() 콜백이 4초 내 중복 데이터 로드
  수정:
    Phase A (0~500ms): UI 렌더링만
    Phase B (800ms): 단일 DB 스냅샷 로드 (inventory + tonbag + allocation)
    Phase C (1500ms): 스냅샷 기반 대시보드/통계/정합성 체크
    Phase D (2500ms): 중복 감지 + 백업 체크
  효과: DB 조회 횟수 절반, 시작 시간 0.5~1초 단축

── PHASE 2-C: UX 개선 (P2~P3) ─────────────────────────

UX-1 [P2] busy cursor (긴 작업 시 대기 표시):
  대상: gui_app_modular/mixins/refresh_mixin.py
  수정: _safe_refresh() 앞뒤에:
    self.root.config(cursor='wait')
    self.root.update_idletasks()
    ... (작업) ...
    self.root.config(cursor='')
  추가: _set_status("데이터 로딩 중...") / _set_status("완료")

UX-2 [P2] silent exception 정리 (17개 파일):
  대상: grep -rn "except.*Exception.*pass" gui_app_modular/ engine_modules/
  수정: except Exception: pass → except Exception as e: logger.debug(f"[context]: {e}")
  ★ 특히 dashboard_tab.py (3곳), outbound_mixin.py (1곳) 우선

UX-3 [P2] _refresh_inventory 이중 쿼리 제거:
  File: gui_app_modular/tabs/inventory_tab.py
  Lines: ~1085-1112, ~1391
  현재: get_all_inventory() + 별도 GROUP BY 쿼리 2회
  수정: JOIN으로 1회 통합 쿼리
  추가: _refresh_inventory_async 결과를 직접 전달 (재조회 방지)

UX-4 [P2] 반품 처리 벌크 UPDATE:
  File: engine_modules/inventory_modular/return_mixin.py
  Lines: ~140-153
  현재: 톤백당 3회 UPDATE (벌크 반품 20개 = 60회)
  수정: lot_no IN (...) + OR 조건으로 1~2회 UPDATE

UX-5 [P3] Ctrl+Z 최근 작업 복구 단축키:
  File: gui_app_modular/mixins/keybindings_mixin.py
  수정: Ctrl+Z → "마지막 자동 백업 복원" 확인 다이얼로그 연결
  연관: gui_app_modular/dialogs/auto_backup.py

── PHASE 2 COMPLETE WHEN ───────────────────────────────

  ✅ STAB-1~4 안정성 수정 완료 (크래시/부분커밋 방지)
  ✅ PERF-1~4 효율성 수정 완료 (lazy refresh + 백그라운드 대시보드)
  ✅ UX-1~5 편리성 수정 완료 (busy cursor + silent exception 정리)
  ✅ pytest passes all engine tests
  ✅ 프로그램 시작 → 경고 0건 확인
  ✅ 탭 전환 시 UI 멈춤 없음 확인

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[CYCLE REPORT FORMAT — AFTER EVERY STEP]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ── PHASE N / STEP N ──────────────────────
  Tests:   X passed / Y failed
  Done:    [BUG-FIX-N] 설명
  Skipped: none
  Next:    [다음 작업]
  ─────────────────────────────────────────

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[NEVER DO THESE]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  - Never delete sub_lt column
  - Never change DB schema without migration
  - Never write partial commits
  - Never use bare except: pass
  - Never break passing engine tests
  - Never write STATUS_SOLD in new code
  - Never delete: data/db/sqm_inventory.db
  - Never wait more than 60 seconds for user input
  - Never hardcode window size without checking window_config.json first
  - Never set resizable(False) on any window or dialog
  - Never hardcode DB path — always use config.DB_PATH
  - Never modify test data without backup


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[PHASE 2: FULL SYSTEM AUDIT — DEBUGGING + REFACTORING + PERFORMANCE]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Run Phase 2 AFTER Phase 0 + Phase 1 are complete.
This phase is a deep, comprehensive pass over the entire codebase.
Auto-decide everything. Never stop. Report after every step.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[P2-STEP-1: DEAD CODE ELIMINATION]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Scan every .py file for dead code. Fix or delete each item found.

  1-A. Unreferenced functions / methods:
       grep -rn "def " --include="*.py" → cross-check with all callers
       Delete any function with ZERO external references
       Exception: test helpers, abstract base methods, __dunder__

  1-B. Unreferenced imports:
       Run: python -m pyflakes . 2>&1 | grep "imported but unused"
       Remove every unused import line

  1-C. Commented-out code blocks (≥ 3 lines):
       grep -rn "^    #.*=\|^    # [a-z]" --include="*.py"
       Delete blocks that are clearly obsolete (older than v8.4.0)
       Keep: TODO/FIXME/NOTE comments that explain WHY

  1-D. Duplicate function definitions:
       grep -rn "^def \|^    def " --include="*.py" | sort | uniq -d
       Consolidate duplicates into single canonical location

  1-E. Empty except blocks:
       grep -rn "except.*:\s*$\|except.*pass" --include="*.py"
       Replace ALL with: except Exception as e: logger.warning(...)

  REPORT FORMAT:
    P2-DEAD: [file] — [item] — [action taken]
    Example: P2-DEAD: parsers/old_parser.py — _legacy_parse() — DELETED (0 callers)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[P2-STEP-2: DEBUGGING — SILENT FAILURES & EDGE CASES]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  2-A. Silent exception audit:
       Find every: except: pass / except Exception: pass / except Exception: continue
       File: grep -rn "except.*:\s*\(pass\|continue\)" --include="*.py"
       Fix: Add logger.warning(f"[MODULE] context: {e}") before pass

  2-B. None / null dereference risks:
       Find patterns: .get() without default on critical fields
       Find: row['field'] without .get() fallback on DB rows
       Fix: Use row.get('field') or COALESCE in SQL

  2-C. Type coercion bugs:
       Find: float(x) / int(x) without try-except around DB values
       Fix: Wrap with safe_float() / safe_int() from safe_utils.py

  2-D. Race conditions in GUI:
       Find: self.engine calls inside tkinter callbacks without thread guard
       Fix: Use self.root.after() or run_in_executor for long ops

  2-E. Weight conservation violations:
       Run: SELECT lot_no, initial_weight, current_weight + picked_weight AS actual
            FROM inventory WHERE ABS(initial_weight - actual) > 1.0
       Fix any violations found

  2-F. Status flow violations:
       Verify: AVAILABLE → RESERVED → PICKED → OUTBOUND only
       Find any reverse transitions or direct AVAILABLE→OUTBOUND skips

  REPORT FORMAT:
    P2-BUG: [file:line] — [issue] — [fix applied]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[P2-STEP-3: REFACTORING — CODE QUALITY & ARCHITECTURE]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  3-A. God method decomposition:
       Find any method > 100 lines:
         grep -rn "def " --include="*.py" → measure line spans
       Target files (known large):
         outbound_mixin.py (4,040줄) → v865 완료: 핵심 3함수 헬퍼 19개 분해
           confirm_outbound: 263→82줄 (_co_* 7개)
           execute_reserved: 202→88줄 (_er_* 6개)
           reserve_from_allocation: 665→466줄 (_ra_* 7개 추가, 기존 10개 유지)
         onestop_inbound.py (4,175줄) → v865 완료: _create_dialog 530→20줄
           _cd_setup_window(36줄), _cd_build_step_indicator(66줄)
           _cd_build_doc_file_section(141줄), _cd_build_parse_action_buttons(76줄)
           _cd_build_carrier_and_progress(125줄), _cd_build_preview_table(77줄)
           _amd_validate_date(16줄), _amd_calc_dates(37줄)
         gemini_parser.py (1,821줄) → split _build_prompt() (미착수)
       Rule: Each method ≤ 80 lines. Extract sub-methods with clear names.

  3-B. Magic number elimination:
       grep -rn "[0-9]\{3,\}" --include="*.py" | grep -v "test_\|#\|string"
       Replace with named constants in engine_modules/constants.py:
         500 → DEFAULT_TONBAG_WEIGHT_KG (already done — verify complete)
         1000 → TONBAG_HEAVY_WEIGHT_KG
         0.001 → SAMPLE_QTY_MT
         Any other hardcoded weights or thresholds

  3-C. SRP violations (Single Responsibility Principle):
       Flag any class doing more than ONE of: DB access, business logic, UI
       Priority targets:
         outbound_mixin.py → separate DB queries from business logic
         toolbar_mixin.py → separate search logic from UI building
         advanced_dialogs_mixin.py → split report generation from dialog UI
       Action: Extract inner logic to engine layer, keep mixin as thin UI wrapper

  3-D. Duplicate SQL queries:
       grep -rn "SELECT.*FROM inventory\|SELECT.*FROM allocation_plan" --include="*.py"
       Find queries repeated ≥ 3 times across files
       Consolidate into query_mixin.py named methods

  3-E. Import hygiene:
       Ensure all gui_app_modular imports use relative paths (from ..utils import)
       Replace any sys.path hacks with proper package imports
       Verify __init__.py exports are consistent

  3-F. Logging standardization:
       All loggers must use: logger = logging.getLogger(__name__)
       Replace any: print(), sys.stderr.write(), bare logging.warning()
       Log levels: DEBUG for suppressed errors, INFO for operations, WARNING for recoverable errors

  REPORT FORMAT:
    P2-REFACTOR: [file] — [issue] — [action]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[P2-STEP-4: PERFORMANCE OPTIMIZATION]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  4-A. N+1 query elimination:
       Find any DB call inside a Python loop:
         grep -B5 -A2 "fetchall\|fetchone\|execute" --include="*.py" -rn            | grep -B5 "for.*in\|while"
       Convert to: single IN() query + dict lookup
       Known remaining targets after v8.6.2 fixes:
         Search all mixins for remaining loop+query patterns

  4-B. Query caching:
       Add @lru_cache or query_cache.py memoization to:
         - get_distinct_customers() — changes rarely
         - get_sap_no_list() — changes rarely
         - get_carrier_list() — static reference data
       TTL: 60 seconds for dynamic data, 3600 for static

  4-C. Treeview rendering performance:
       Find any Treeview.insert() in a loop > 200 items
       Replace with: batch delete → batch insert pattern
       Add: tree.config(selectmode='browse') for large tables

  4-D. SQLite index audit:
       Run: SELECT name, tbl_name FROM sqlite_master WHERE type='index'
       Verify indexes exist for ALL frequently filtered columns:
         inventory_tonbag: (lot_no, status), (status, is_sample)
         allocation_plan: (sale_ref), (status, lot_no)
         sold_table: (sales_order_no, status), (delivery_date)
       Add missing indexes via migration

  4-E. Startup time optimization:
       Profile: python -c "import cProfile; cProfile.run('import run')"
       Find any heavy import at module level (pandas, PIL, etc.)
       Move heavy imports inside functions (lazy import pattern)
       Target: startup < 3 seconds on Windows

  4-F. Memory leak prevention:
       Find: tk.PhotoImage / PIL.Image objects not stored as instance variables
       Fix: self._images = [] pattern to prevent GC collection
       Find: after() callbacks that are never cancelled
       Fix: store after IDs and cancel on window close

  REPORT FORMAT:
    P2-PERF: [file:line] — [issue] — [before/after] — [fix applied]
    Example: P2-PERF: inventory_tab.py:445 — N+1 query in loop (88 LOT × 1 query)
                      → IN() batch query — 88 queries → 1 query

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[P2-STEP-5: ARCHITECTURE IMPROVEMENT]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  5-A. Constants centralization:
       Single source of truth check:
         STATUS_* constants → engine_modules/constants.py ONLY
         DEFAULT_TONBAG_WEIGHT → engine_modules/constants.py ONLY
         SAMPLE_MT_THRESHOLD → engine_modules/constants.py ONLY
       Find duplicates: grep -rn "AVAILABLE\|RESERVED\|PICKED\|OUTBOUND"          --include="*.py" | grep "= '" | grep -v "import\|#"
       Remove all duplicates, keep only imports from canonical location

  5-B. Error handling hierarchy:
       Define custom exceptions in core/exceptions.py (create if missing):
         class SQMValidationError(Exception): pass
         class SQMIntegrityError(Exception): pass
         class SQMWeightError(SQMIntegrityError): pass
         class SQMStatusError(SQMIntegrityError): pass
       Replace generic RuntimeError raises with specific SQM exceptions
       Update except clauses to catch specific exception types

  5-C. Configuration centralization:
       Verify ALL config values come from config.py:
         DB_PATH, API keys, timeouts, thresholds
       Find any hardcoded paths or keys outside config.py:
         grep -rn "\.db\|API_KEY\|api_key\|gemini" --include="*.py"            | grep -v "config\|import\|#\|test_"
       Move to config.py with os.environ fallback

  5-D. Test coverage improvement:
       Run: python -m pytest tests/ --cov=. --cov-report=term-missing -q
       Find files with < 20% coverage
       Add tests for:
         - Weight conservation law (all inbound/outbound/return paths)
         - Status transition guards (illegal transitions must raise)
         - Allocation preflight (all 10 AL- error codes)
         - Sample policy (sample cannot be allocated/picked alone)

  5-E. Documentation:
       Add module-level docstring to any .py file missing one:
         grep -rL "^"""" --include="*.py" .
       Add type hints to all public engine methods lacking them:
         grep -rn "def [a-z]" engine_modules/ --include="*.py"            | grep -v "-> \|: str\|: int\|: bool\|: list\|: dict"

  REPORT FORMAT:
    P2-ARCH: [file] — [issue] — [action]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[P2-STEP-6: FINAL VALIDATION]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  After all P2 steps complete:

  6-A. Full test suite:
       python -m pytest tests/ -v --tb=short 2>&1
       REQUIRED: 0 engine test failures
       ACCEPTABLE: UI test failures (P3)

  6-B. Syntax check all files:
       python -m py_compile $(find . -name "*.py" | grep -v __pycache__)
       REQUIRED: 0 syntax errors

  6-C. Import check:
       python -c "import run" 2>&1
       REQUIRED: No ImportError or ModuleNotFoundError

  6-D. Startup smoke test:
       python run.py --check 2>&1
       REQUIRED: Exits 0

  6-E. Weight conservation final check:
       Run DB query from AUDIT-2
       REQUIRED: 0 violations

  6-F. Version bump:
       Update version.py: VERSION = "8.6.5"
       Update CHANGELOG with P2 summary

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[P2 COMPLETE WHEN]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ✅ P2-STEP-1: Dead code report generated + all items actioned
  ✅ P2-STEP-2: All silent failures fixed, 0 bare except:pass remaining
  ✅ P2-STEP-3: No method > 100 lines, no duplicate SQL, imports clean
  ✅ P2-STEP-4: N+1 queries eliminated, indexes verified, startup < 3s
  ✅ P2-STEP-5: Constants centralized, custom exceptions defined
  ✅ P2-STEP-6: pytest passes, py_compile passes, startup smoke test passes
  ✅ version.py updated to v8.6.5

  P2 SUMMARY REPORT FORMAT:
  ══════════════════════════════════════
  P2 COMPLETE — SQM v8.6.5
  Dead code removed:   N items (M lines)
  Bugs fixed:          N items
  Refactors:           N items
  Performance wins:    N items (key: X queries → 1, startup Xs → Ys)
  Architecture:        N items
  Tests:               X passed / Y failed
  ══════════════════════════════════════

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[DEPENDENCIES — requirements.txt]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Core:
    pandas (2.2+), openpyxl (3.1+), reportlab (4.2+)
    Pillow (10.0+), ttkbootstrap (1.10+)
    PyMuPDF (1.23+), pdfplumber (0.11+)
    python-barcode (0.15+), keyring (25.0+)

  AI/ML:
    google-generativeai (0.5+)  ← Gemini Vision API

  Optional:
    fastapi (0.110+), httpx (0.27+), bcrypt (4.0+)
    tkinterdnd2, pytesseract, opencv-python, qrcode

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BEGIN NOW.

EXECUTION ORDER:
  1. PHASE 0: python -m pytest tests/ -v --tb=short 2>&1
              → AUDIT-1 through AUDIT-10 in order
  2. PHASE 1: All P1 bug fixes + UI improvements
  3. PHASE 2: Full audit — dead code → debugging → refactoring
              → performance → architecture → final validation
              → version bump to v8.6.5

When each phase completes → start next phase automatically.
Do not stop between phases. Do not ask. Auto-decide everything.
Report after every phase AND every step within each phase.
```

---

## 기동님 실행 방법

```bash
# 1. SQM v865 폴더로 이동
cd "F:\프로그램\Sqm 재고관리\Claude_SQM_v865"

# 2. Claude Code 실행 (자동 모드)
claude --dangerously-skip-permissions \
  --system-prompt-file Claude_Code_SQM_MASTER.md

#    → 자리 비우기 (3~6시간)
#    → 돌아오면 결과 확인
```

---

## 야간 자동 실행 — P2 리팩토링 (v865)

```
YOU ARE CONTINUING the v865 refactoring session.
All P0 and P1 tasks are DONE. Now execute P2 tasks below.

Working directory: F:\프로그램\Sqm 재고관리\Claude_SQM_v865
Git root (for commit/push): F:\프로그램\Sqm 재고관리

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[ABSOLUTE RULES — NEVER VIOLATE]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- NO DB schema change
- NO business policy change
- NO public method signature change
- NO cross-file interface change
- NO new SOLD write-path (all writes must use OUTBOUND)
- SOLD read-path: keep WHERE status IN ('OUTBOUND','SOLD') for backward compat
- Always run: python -m py_compile <file> after EVERY edit
- If py_compile fails → fix immediately before moving on
- If a change feels risky → skip it and log as DEFERRED
- Backup each file before modifying: cp file.py file.py.bak_auto

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[TASK 1] outbound_handlers.py 분해 (2,868줄)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

File: gui_app_modular/handlers/outbound_handlers.py

1. Read the entire file and identify all methods > 80 lines
2. For each large method, extract helper methods with _oh_ prefix
3. Keep public signatures unchanged
4. Separate business logic from UI callback wiring where possible
5. py_compile verify after each method split

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[TASK 2] advanced_dialogs_mixin.py 분해 (2,283줄)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

File: gui_app_modular/mixins/advanced_dialogs_mixin.py

1. Read the entire file and identify all methods > 80 lines
2. Extract helpers with _adm_ prefix
3. Separate report generation logic from dialog UI
4. py_compile verify

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[TASK 3] except Exception 나머지 정리 (onestop_inbound.py)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

File: gui_app_modular/dialogs/onestop_inbound.py

Already done: 7 data-path exceptions standardized.
Remaining: ~53 UI-related except Exception.

Rules:
- File I/O: except Exception → except (OSError, IOError, PermissionError)
- JSON: except Exception → except (json.JSONDecodeError, KeyError, ValueError)
- tkinter widget ops (winfo_exists, config, pack, grid): KEEP except Exception
  (tkinter raises TclError, RuntimeError, etc unpredictably)
- Template load/save: except Exception → except (OSError, json.JSONDecodeError, KeyError)
- Add logger.warning where only logger.debug exists on recoverable errors

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[TASK 4] 중복 SQL 쿼리 통합
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Search for repeated SQL patterns across *.py:
   grep -rn "SELECT.*FROM inventory_tonbag.*WHERE.*status" --include="*.py"
   grep -rn "SELECT.*FROM allocation_plan.*WHERE.*status" --include="*.py"
2. Find queries repeated >= 3 times across different files
3. Create named methods in engine_modules/inventory_modular/query_mixin.py
4. Replace duplicates with method calls
5. py_compile verify all changed files

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[TASK 5] after() 호출 정리
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. Search: grep -rn "\.after(" --include="*.py" | grep -v test
2. Identify unnecessary/duplicate refresh calls
3. Consolidate where possible (multiple after() → single deferred refresh)
4. Do NOT remove after() calls in critical UI update paths
5. py_compile verify

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[EXECUTION ORDER]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Execute TASK 1 → TASK 2 → TASK 3 → TASK 4 → TASK 5 in order.
Do not stop between tasks. Do not ask. Auto-decide everything.
If a task has ambiguity that could alter DB semantics → skip and log as DEFERRED.

After EACH task, output:
  TASK N COMPLETE:
  - files modified: [list]
  - methods extracted: [count]
  - py_compile: PASS/FAIL
  - deferred items: [list or none]

After ALL tasks, output:
  ══════════════════════════════════════
  P2 SESSION COMPLETE — SQM v865
  Task 1 (outbound_handlers): [summary]
  Task 2 (advanced_dialogs): [summary]
  Task 3 (except cleanup): [summary]
  Task 4 (SQL consolidation): [summary]
  Task 5 (after cleanup): [summary]
  Total files modified: N
  Total helpers extracted: N
  Deferred: [list]
  ══════════════════════════════════════
```

## v8.6.5 리팩토링 이력 (2026-04-02~03, Claude Code 세션)

| 커밋 | 파일 | 내용 |
|------|------|------|
| def7b5e | outbound_mixin.py | 핵심 3함수 헬퍼 19개 분해 (confirm_outbound 263→82줄, execute_reserved 202→88줄, reserve_from_allocation 665→466줄) |
| eb03ae1 | barcode_scan_engine.py, sales_order_engine.py, lot_detail_dialog.py | SOLD write-path 전면 제거 → OUTBOUND 통일 (14→0건) |
| ca71921 | onestop_inbound.py | _create_dialog 530줄 → 20줄 오케스트레이터 + 6개 _cd_* 헬퍼 |
| 74d86ad | onestop_inbound.py | 파싱버튼 76줄 분리 + 날짜 검증/계산 53줄 static 메서드 추출 |
| 9a4c03d | onestop_inbound.py | 데이터 경로 except Exception 7건 → 특정 타입 표준화 |

### 변경 원칙
- DB schema 변경 없음
- business policy 변경 없음
- public method signature 변경 없음
- SOLD는 read-path에서 하위호환 유지 (WHERE status IN ('OUTBOUND','SOLD'))

### 41개 Mixin 분류 (SQMInventoryAppFull)
| 그룹 | 수 | 포함 |
|------|---|------|
| UI 프레임 | 5 | Menu, Toolbar, StatusBar, Window, Theme |
| 기능/단축키 | 4 | KeyBindings, ContextMenu, DragDrop, FeaturesV2 |
| 데이터/검증 | 3 | Database, Validation, Refresh |
| 탭 | 14 | Dashboard(2), Inventory, Allocation(2), Outbound, Picked, Sold, Scan, Tonbag, Log, Summary, Cargo, Return, Move |
| 핸들러 | 12 | Import, Outbound(3), Backup, PDF(2), Export, Inbound(2), StatusImport, Product, SimpleExcel |
| 대화상자 | 5 | LotAllocationAudit, LotDetail, Settings, Info, OutboundPreview |
| 고급 | 1 | AdvancedFeatures |

### 남은 P2 작업
- UI refresh / after() 104회 정리
- 서비스 계층 분리 (outbound/allocation/picking)
- 41개 mixin 축소
- gemini_parser.py _build_prompt() 분해

---

## v8.6.4 업데이트 사항 (v8.6.3 대비)

| 항목 | v8.6.3 | v8.6.4 |
|---|---|---|
| 총 Python 파일 | 233개 | 239개 (+6) |
| 총 코드 라인 | ~103,000줄 | ~105,274줄 (+2,274) |
| 빈 except 블록 | 27건 존재 | 전량 수정 (logger.warning 교체) |
| Dead code | 존재 | 7개 파일(207줄) 제거 |
| 대형 메서드 | 미분해 | 서브메서드 12개 추가 (inb/ret/co/g1/do/scan) |
| DB 인덱스 | 기존만 | +3개 (tb_status_is_sample/sold_delivery/mv_lot_type) |
| DN 교차검증 | 미구현 | dn_cross_check_engine + dialog 신규 |
| 파싱 에러 복구 | 미구현 | parse_error_recovery_dialog 신규 |
| 파싱 미리보기 | 미구현 | parse_preview_confirm_dialog 신규 |
| 배정 감사 | 미구현 | lot_allocation_audit_mixin 신규 |
| 이메일 설정 | 미구현 | email_config_dialog 신규 |
| 피킹 후보 패치 | 미구현 | candidate_scorer + picking_candidate_patch 신규 |
| 자연어 편집 | 미구현 | natural_edit_bridge 신규 |

## v8.6.3 업데이트 사항 (v8.6.2 대비)

| 항목 | v8.6.2 | v8.6.3 |
|---|---|---|
| 초기화면 | Inventory 탭 | 대시보드 탭 자동 표시 |
| Allocation 파서 | 엑셀 순서 그대로 | 본품 먼저 → 샘플 나중 정렬 |
| LOT 현황 샘플 표시 | 1-AVAIL | 본품 미완료=대기 / 완료=상태표시 |
| 날짜 입력 UI | 제각각 (텍스트/DateEntry 혼용) | 13개 메뉴 make_date_range_bar 통일 |
| 캘린더 팝업 | 단순 버튼 그리드 | Combobox/하이라이트/색상/호버 개선 |
| Detail of Outbound | 단일 시트 | delivery_date별 시트 자동 분리 |
| Sales Order DN | 조건 없이 발행 | 전체 출고 완료 시에만 1회 발행 |
| Allocation 지원 양식 | 4종 (A~D) | 6종 (E=Easpring, F=Jakarta 추가) |
| date_in_stock | 문자열만 | 엑셀 시리얼 자동 변환 |
| customs 정규화 | 없음 | 오타 포함 자동 정규화 |
| SC RCVD 컬럼 | 미지원 | allocation_plan.sc_rcvd 저장 |
| 패치 파일 수 | - | 18개 파일 |

## v8.6.2 업데이트 사항 (v8.5.9 대비)

| 항목 | v8.5.9 | v8.6.2 |
|---|---|---|
| 프로젝트 버전 | v8.1.4~v8.5.9 혼재 | v8.6.2 통일 |
| 파일 수 | ~220개 | 233개 |
| 코드 라인 | ~95,000줄 | ~103,000줄 |
| 디렉토리 구조 | 상세 기술 | 전체 트리 + 라인 수 포함 |
| 버전 통일 작업 | AUDIT-0 포함 | 제거 (이미 통일됨) |
| NiceGUI Phase 2 | 포함 | 제거 (별도 계획) |
| MXBG 검증 | 미언급 | N+1 제거, STAGED 포함 |
| 서류 자동 감지 | 미포함 | InboundDocDetector 기술 |
| 선사 자동 매칭 | BUG-3 수정 필요 | 수정 완료, 매칭 로직 기술 |
| DO free_time_info | 미언급 | 생성 로직 3곳 추가 기술 |
| 샘플 STAGED 충돌 | BUG로 기술 | 수정 완료 상태 기술 |
| CONFIG 상수 | 일부만 | 전체 상수 목록 |
| STATUS 상수 | 일부만 | engine_modules/constants.py 전체 |
| Allocation 5단계 | Phase 1-H | 정규 섹션으로 격상 |
| 자재코드 체계 | 참고 수준 | 정규 섹션으로 정리 |
| 출고 보고서 | 미포함 | Detail of Outbound + Sales Order DN |

## 실행 후 확인

```bash
# Phase 0 감사 결과
python -m pytest tests/ -q

# 프로그램 실행 테스트
python run.py --check
python run.py
```
