# SQM Claude Code 마스터 프롬프트
# 작성: Ruby (2026-03-22 updated v2)
# 용도: 버그수정 + UI개선 + 메뉴단일화 + 창크기저장 + NiceGUI 마이그레이션 완전 자동화

---

## ⚡ 실행 명령어 (이것만 치면 됩니다)

```bash
# 기본 — 중단 없이 완전 자동 실행
cd C:\sqm
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

Project: SQM v8.1.4 — LOT-based tonbag logistics system
         Lithium carbonate warehouse management (Gwangyang, Korea)
Tech:    Python 3.12 / tkinter / ttkbootstrap / SQLite / pytest / NiceGUI

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
         pip install nicegui plotly --break-system-packages -q
RULE-4.  DB path → always from config.DB_PATH. Never hardcode.
RULE-5.  Port conflicts → auto-increment (8080→8081→8082→8090).
RULE-6.  Async DB calls → always use run_in_executor pattern.
RULE-7.  Test failures during migration → log + continue.
         Engine tests must stay passing. UI tests may fail.
RULE-8.  Never modify: engine_modules/ features/ parsers/ tests/ config.py
RULE-9.  Never delete: data/sqm_inventory.db

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[SYSTEM OVERVIEW]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Core workflow:
  Inbound → Inventory → Allocation → Picking → Outbound → Return → Move

Key files:
  gui_app_modular/utils/ui_constants.py      (1,186 silent fails)
  gui_app_modular/main_app.py                (main window)
  gui_app_modular/tabs/inventory_tab.py      (1,584 lines)
  gui_app_modular/dialogs/onestop_inbound.py (3,520 lines)
  gui_app_modular/mixins/toolbar_mixin.py    (실제 화면 메뉴바 — 7개 버튼)
  gui_app_modular/mixins/custom_menubar.py   (대체 메뉴바)
  gui_app_modular/menu_registry.py           (메뉴 단일 소스)
  gui_app_modular/window_config.json         (창 크기/위치 저장 파일)
  engine_modules/inventory_modular/          (engines — DO NOT TOUCH)
  features/parsers/                          (parsers — DO NOT TOUCH)
  parsers/document_parser_modular/bl_mixin.py
  parsers/document_parser_modular/do_mixin.py
  features/parsers/onestop_inbound_candidate_patch.py
  config.py                                  (DB_PATH defined here)
  tests/samples/                             (7 PDFs embedded)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[DATA INTEGRITY — NEVER VIOLATE]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. HIERARCHY: BL_NO > LOT_NO > TONBAG_NO (sub_lt)
   Sample: sub_lt=0, tonbag_no='S00' — never allocate/pick/sell

2. WEIGHT LAW: initial_weight == current_weight + picked_weight (±1.0kg)

3. STATUS FLOW: AVAILABLE→RESERVED→PICKED→OUTBOUND
   STATUS_SOLD = deprecated read-only. All writes → STATUS_OUTBOUND

4. STOCK: CURRENT = AVAILABLE + RESERVED + PICKED + RETURN

5. HARD STOP: LOT missing / weight=0 / status reversal / partial commit

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[PHASE 0: FULL PROCESS LOGIC AUDIT — RUN FIRST]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Before any fix or migration, audit the entire business logic.
Run ALL checks below. Log every issue found.
Fix critical issues (P1) before moving to Phase 1.

── AUDIT-0: VERSION UNIFICATION — DO THIS FIRST ──────

  Before any other work, unify version to v8.1.4:

  STEP A: Update version.py
    Set:
      __version__ = "8.1.4"
      VERSION = "8.1.4"
      VERSION_TUPLE = (8, 1, 4)
      RELEASE_DATE = "2026-03-21"

  STEP B: Update all version strings in code
    grep -rn "8\.1\.3\|v8\.1\.3\|v811\|v812\|v813" . \
      --include="*.py" --include="*.md" --include="*.txt" | \
      grep -v "__pycache__\|.git"
    Replace ALL occurrences with 8.1.4 / v8.1.4

  STEP C: Verify
    python3 -c "from version import __version__; print(__version__)"
    → must print: 8.1.4

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
  onestop_inbound.py
    → selected_carrier_id extracted ✓
    → parse_bl_with_candidate() called
      → carrier_id=selected_carrier_id PASSED? ← check
        → parse_bl() receives it
          → CARRIER_COORD_TABLE lookup works

  Also verify: bl_mixin.py result.voyage (not result.voyage_no)

── AUDIT-10: PYTEST FULL RUN ─────────────────────────

  python -m pytest tests/ -v --tb=short 2>&1 | tee /tmp/audit_test.log

  Categorize every failure:
  - Data integrity failure → P1 fix immediately
  - Logic error → P1 fix immediately
  - UI test failure → P2 (acceptable during migration)
  - Missing coverage → P3 add test

── PHASE 0 COMPLETE WHEN ─────────────────────────────

  ✅ Version unified: python3 -c "from version import __version__; assert __version__=='8.1.4'"
  ✅ All 10 audits complete with findings logged
  ✅ P1 issues (data corruption risk) all fixed
  ✅ Audit report written to /tmp/sqm_audit_report.txt
  ✅ pytest passes all engine tests

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[PHASE 1: BUG FIXES + UI IMPROVEMENTS (tkinter)]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Run iterative cycles until ALL bugs fixed and UI improved.

── BUG FIXES ─────────────────────────────────────────

BUG-1 [P1] Fix failing test:
  tests/test_v660_new_methods.py::TestCreateDialogSplit::test_create_dialog_is_short

BUG-2 [P1] carrier_id not passed to parse_bl():
  File: features/parsers/onestop_inbound_candidate_patch.py
  Fix:  add carrier_id=selected_carrier_id to parser.parse_bl() call

BUG-3 [P1] BL 선사 감지 동점 버그 — MSC 문서가 MAERSK로 오감지됨:
  File: parsers/document_parser_modular/bl_mixin.py
  Problem: _detect_carrier_from_words() 에서 "WAYBILL" 키워드가
           MAERSK 점수에 포함 → MSC 문서에서 MAERSK 2점 / MSC 2점 동점
           → max() 딕셔너리 순서상 MAERSK 선택 → BL 번호 추출 실패
  Fix:
    def _detect_carrier_from_words(self, words, full_text="", explicit=""):
        if explicit:
            if explicit in ("MAEU", "MERSK"):
                return "MAERSK"
            return explicit
        page0_words = [w for w in words if int(w.get("page", 0)) == 0]
        page0_text = " ".join(str(w.get("text","")) for w in page0_words).upper()
        if not page0_text:
            page0_text = (full_text or "").upper()
        score = {"MAERSK": 0, "MSC": 0}
        # ★ "WAYBILL" 제거 — MSC 문서에도 있어서 동점 유발
        if any(k in page0_text for k in ("MAERSK", "MAEU", "NON-NEGOTIABLE WAYBILL")):
            score["MAERSK"] += 2
        if re.search(r"\bMAEU\b", page0_text):
            score["MAERSK"] += 2
        # ★ MEDITERRANEAN에 +3 (가장 고유한 키워드)
        if "MEDITERRANEAN" in page0_text:
            score["MSC"] += 3
        if any(k in page0_text for k in ("MSC.COM", "MSC CHILE", "MSC KOREA")):
            score["MSC"] += 2
        if re.search(r"\b(?:MSCU|MEDU)\b", page0_text):
            score["MSC"] += 2
        if re.search(r"\bMEDU[A-Z0-9]+", page0_text):
            score["MSC"] += 2
        winner = max(score, key=score.get)
        logger.debug(f"[BL] carrier score: {score} → {winner}")
        return winner if score[winner] > 0 else ""

  Also fix CARRIER_COORD_TABLE MSC ship_date range:
    "ship_date": (15.0, 55.0, 86.0, 95.0)   # 확장: 29-Jan-2026 포착

BUG-4 [P1] PL packing_mixin LOT_SQM 6자리 → 7자리 버그:
  File: parsers/document_parser_modular/packing_mixin.py
  Problem: _parse_packing_list_coord() 에서
           re.match(r"^\d{6}$", ...) 으로 LOT_SQM 추출
           실제 값은 7자리 (예: 1015616) → 항상 미추출
  Fix:
    lot_sqm = next(
        (ww["text"] for ww in row
         if 25 <= ww["x0"]/page_w*100 <= 36
         and re.match(r"^\d{6,7}$", ww["text"])), ""  # ★ 6→6,7자리
    )

BUG-5 [P1] MSC D/O 파싱 — Gemini 폴백 문제:
  File: parsers/document_parser_modular/do_mixin.py
  Problem: parse_do() 0단계에 MAERSK 좌표 파서만 있고 MSC 없음
           → MSC D/O가 항상 Gemini로 폴백
  Fix A: _parse_do_msc_coord() 메서드 신규 추가:
    def _parse_do_msc_coord(self, pdf_path):
        import fitz, re as _re
        doc = fitz.open(pdf_path)
        page = doc[0]; W=page.rect.width; H=page.rect.height
        words_raw = page.get_text("words"); doc.close()
        words = [{"text":w[4],"x0":float(w[0]),"x1":float(w[2]),
                  "top":float(w[1]),"bottom":float(w[3])} for w in words_raw]
        def by_xy(x1,x2,y1,y2):
            hits = sorted([w for w in words
                if x1<=w["x0"]/W*100<=x2 and y1<=w["top"]/H*100<=y2],
                key=lambda x:x["x0"])
            return " ".join(w["text"] for w in hits).strip()
        bl_raw = by_xy(57.0,90.0,2.0,4.5)
        m = _re.compile(r"\b((?:MEDU|MSCU)[A-Z0-9]{6,10})\b").search(bl_raw)
        bl_no = m.group(1) if m else ""
        vessel = by_xy(3.0,23.0,28.0,31.5)
        voyage = by_xy(11.0,22.0,28.0,31.5)
        pol    = by_xy(30.0,58.0,28.0,31.5)
        pod    = by_xy(30.0,58.0,31.0,34.5)
        ship_raw = by_xy(15.0,55.0,86.0,95.0)
        ship_date = ""
        for pat in [_re.compile(r"\d{1,2}-[A-Za-z]{3}-\d{4}"),
                    _re.compile(r"\d{4}-\d{2}-\d{2}")]:
            dm = pat.search(ship_raw)
            if dm: ship_date=dm.group(0); break
        try:
            doc2 = fitz.open(pdf_path)
            all_text = " ".join(doc2[i].get_text("text")
                for i in range(min(3,len(doc2))))
            doc2.close()
        except Exception: all_text = bl_raw
        CT_RE = _re.compile(r"\b([A-Z]{4}\d{7})\b")
        containers = list(dict.fromkeys(CT_RE.findall(all_text)))
        SEAL_RE = _re.compile(r"\b(ML-CL\d{7}|FX\d{8})\b")
        seals = list(dict.fromkeys(SEAL_RE.findall(all_text)))
        from ..document_models import DOData, ContainerInfo
        result = DOData()
        result.source_file=pdf_path; result.bl_no=bl_no
        result.vessel=vessel; result.voyage_no=voyage
        result.port_of_loading=pol; result.port_of_discharge=pod
        result.ship_date=ship_date; result.carrier_id="MSC"
        for i,ct in enumerate(containers):
            ci=ContainerInfo(); ci.container_no=ct
            ci.seal_no=seals[i] if i<len(seals) else ""
            if hasattr(result,"containers"): result.containers.append(ci)
        result.success = bool(result.bl_no)
        logger.info(f"[DO-MSC] bl={bl_no} ct={len(containers)}개")
        return result

  Fix B: parse_do() 0단계에 MSC 분기 삽입 (MAERSK 블록 바로 아래):
    # [B-MSC] MSC → 좌표 파싱 (Gemini 없이)
    if _carrier in ('MSC', 'MEDU', 'MSCU'):
        try:
            _r = self._parse_do_msc_coord(pdf_path)
            if _r and _r.success:
                logger.info("[DO] MSC 좌표 파싱 성공")
                return _r
            logger.debug("[DO] MSC 좌표 실패 → carrier_rule 시도")
        except Exception as _e:
            logger.debug(f"[DO] MSC 좌표 예외: {_e}")

BUG-6 [P2] voyage field mismatch in bl_mixin.py:
  Fix: result.voyage_no = ... → result.voyage = ...

BUG-7 [P2] STATUS_SOLD written in new code:
  Fix: replace write paths with STATUS_OUTBOUND

BUG-8 [P3] bl_mixin.py 15+ unused legacy functions:
  Fix: grep to confirm unused → remove → 827 lines → ~300 lines

── UI IMPROVEMENTS ────────────────────────────────────

UI-1 [P1] Fix 1,186 silent failures in gui_app_modular/:
  Replace every: except: pass / except Exception: pass
  With:          except Exception as e: logger.warning(f"[UI] {context}: {e}")

UI-2 [P1] Theme unification:
  config.py default theme = 'darkly'
  Remove all hardcoded colors (#333, white, black)

UI-3 [P2] Sidebar navigation (replace 8 tabs):
  Left sidebar 60px: 📦재고 📋배정 🚛피킹 ✅출고 📊통계 📝로그 📷스캔

UI-4 [P2] Status badge pills in all tables:
  AVAILABLE→green RESERVED→blue PICKED→amber OUTBOUND→gray RETURN→coral

UI-5 [P2] Detail panel: start_collapsed=True in all 3 tabs

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[PHASE 1-A: 메뉴 단일화 — menu_registry.py 확장]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

현재 상황:
  - 메뉴 정의가 toolbar_mixin.py / custom_menubar.py / menu_registry.py
    3개 파일에 분산되어 있음
  - toolbar와 custom_menubar 간 21개 항목 불일치 (10개 toolbar 누락,
    11개 custom 누락)
  - 이름 불일치: "🤖 Gemini (API)" vs "🤖 AI 어시스턴트" 등

목표:
  - menu_registry.py를 단일 소스로 확장
  - toolbar_mixin.py / custom_menubar.py 모두 registry에서 읽도록 변경

── STEP-M1: menu_registry.py에 누락 섹션 추가 ─────────

  # gui_app_modular/menu_registry.py 에 아래 섹션 추가

  # ── 재고 메뉴 (toolbar [4] 📊 재고 ▼) ──────────────────────
  MENU_STOCK_ITEMS = [
      ("📊 LOT 리스트 Excel",  "_on_export_click",  False, {"option": 3}),
      ("🎒 톤백리스트 Excel",  "_on_export_click",  False, {"option": 4}),
      None,
      ("📋 출고 현황 조회",    "_show_outbound_history",  True),
      ("📊 재고 추이 차트",    "_show_snapshot_chart",    True),
  ]

  # ── 보고서 메뉴 (toolbar [5] 📝 보고서 ▼) ────────────────────
  MENU_REPORT_ITEMS = [
      ("📄 거래명세서 생성",    "_generate_outbound_invoice"),
      None,
      ("📝 고객 보고서 생성",   "_generate_customer_report",  True),
      ("📂 보고서 양식 관리",   "_manage_report_templates",   True),
      None,
      ("📋 보고서 이력 조회",   "_show_report_history",       True),
      ("📦 재고 현황 보고서",   "_generate_inventory_pdf_report"),
      ("📈 입출고 내역",        "_generate_transaction_pdf"),
      ("📅 월간 실적 PDF",      "_generate_monthly_pdf_v398", True),
      ("📊 일일 현황 PDF",      "_generate_daily_pdf_v398",   True),
      ("🔖 LOT 상세",           "_generate_lot_detail_pdf"),
  ]

  # ── 설정/도구 메뉴 (toolbar [6] 🔧 설정/도구 ▼) ──────────────
  MENU_SETTINGS_ITEMS = [
      ("🔄 새로고침 (F5)",          "_refresh_all_data"),
      ("💾 현재 창 크기 저장",      "_on_save_window_size"),
      ("↩️ 기본 창 크기 초기화",    "_on_reset_window_size"),
      None,
      ("📦 제품 마스터 관리",       "_show_product_master"),
      ("📊 제품별 재고 현황",       "_show_product_inventory_report"),
      ("📋 D/O 후속 연결",          "_on_do_update"),
      None,
      ("🩺 데이터 정합성 검사",     "_run_integrity_check"),
      ("🔍 정합성 검사/복구",       "_on_integrity_check"),
      ("🔧 DB 최적화",              "_on_optimize_db"),
      ("📋 로그 정리",              "_on_cleanup_logs"),
      ("ℹ️ DB 정보",                "_show_db_info"),
  ]

  # ── 도움말 메뉴 (toolbar [7] ❓ 도움말 ▼) ────────────────────
  MENU_HELP_ITEMS = [
      ("📖 사용법",                 "_show_help"),
      ("⌨️ 단축키 안내",            "_show_shortcuts"),
      None,
      ("📊 STATUS 상태값 안내",     "_show_status_guide",    True),
      ("💾 DB 백업/복구 가이드",    "_show_backup_guide",    True),
      None,
      ("ℹ️ 시스템 정보",            "_show_system_info",     True),
      ("📝 버전 정보",              "_show_about"),
  ]

── STEP-M2: toolbar_mixin.py 빌더를 registry 참조로 교체 ──

  교체 대상 메서드:
    _build_report_menu()          → MENU_STOCK_ITEMS
    _build_customer_report_menu() → MENU_REPORT_ITEMS
    _build_help_menu()            → MENU_HELP_ITEMS

  표준 패턴 (이 패턴으로 모든 빌더 교체):
    def _build_XXX_menu(self) -> 'tk.Menu':
        m = self._create_menu()
        from ..menu_registry import MENU_XXX_ITEMS
        for entry in MENU_XXX_ITEMS:
            if entry is None:
                m.add_separator(); continue
            label = entry[0]; method_name = entry[1]
            optional = entry[2] if len(entry) > 2 else False
            kwargs = entry[3] if len(entry) > 3 else {}
            if optional and not callable(getattr(self, method_name, None)):
                continue
            m.add_command(
                label=f"  {label}",
                command=lambda mn=method_name, kw=kwargs:
                    self._safe_call(mn, **kw) if not kw
                    else getattr(self, mn)(**kw)
            )
        return m

  _build_settings_menu()는 테마/글꼴 서브메뉴가 동적이므로
  MENU_SETTINGS_ITEMS 항목을 섹션별로 삽입하는 방식으로 수정:
    - 화면 섹션: 새로고침, 창크기 저장/초기화 → registry에서
    - 테마/글꼴 서브메뉴: 기존 코드 유지
    - 도구 섹션: D/O, 제품마스터, DB도구 → registry에서

── STEP-M3: custom_menubar.py도 동일 registry 참조 ────────

  교체 대상:
    _create_report_menu()  → MENU_REPORT_ITEMS
    _create_help_menu()    → MENU_HELP_ITEMS

  표준 패턴:
    def _create_XXX_menu(self) -> None:
        from ..menu_registry import MENU_XXX_ITEMS
        menu = self._add_menu("레이블")
        for entry in MENU_XXX_ITEMS:
            if entry is None:
                self._add_separator(menu); continue
            label = entry[0]; method_name = entry[1]
            optional = entry[2] if len(entry) > 2 else False
            cb = getattr(self.app, method_name, None)
            if optional and not callable(cb): continue
            if callable(cb):
                self._add_command(menu, label, cb)

── STEP-M4: 이름 불일치 통일 ───────────────────────────────

  toolbar "🤖 Gemini (API)"  ←→  custom "🤖 AI 어시스턴트"
  → 두 파일 모두 "🤖 Gemini AI" 로 통일

  toolbar "🔍 정합성 검사/복구"  ←→  custom "🩺 데이터 정합성 검사"
  → 두 파일 모두 "🔍 정합성 검사/복구" 로 통일

  toolbar "📝 버전 정보 (vX.X)"  ←→  custom "ℹ️ 정보"
  → MENU_HELP_ITEMS의 "📝 버전 정보" 로 통일

── STEP-M5: toolbar 누락 항목 추가 ─────────────────────────

  _build_settings_menu() 에 추가 (MENU_SETTINGS_ITEMS 통해):
    - 📦 제품 마스터 관리     (_show_product_master)
    - 📋 D/O 후속 연결        (_on_do_update)
    - 🛡️ DB 보호 서브메뉴    (HAS_DB_PROTECTION 조건부)
    - ✨ 고급 서브메뉴         (HAS_FEATURES 조건부)

── PHASE 1-A COMPLETE WHEN ─────────────────────────────────

  ✅ menu_registry.py에 4개 섹션 추가
  ✅ toolbar_mixin.py 빌더 3개 registry 참조로 교체
  ✅ custom_menubar.py 빌더 2개 registry 참조로 교체
  ✅ 이름 불일치 3건 통일
  ✅ 누락 항목 21개 동기화

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[PHASE 1-B: 창 크기 저장/복원 완전 수정]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

현재 문제:
  - 창 크기를 변경해도 프로그램 재시작 시 이전 크기로 돌아옴
  - window_config.json이 있지만 저장/불러오기가 제대로 작동 안 함

── STEP-W1: window_config.json 구조 확인 ──────────────────

  파일 위치: gui_app_modular/window_config.json
  현재 내용 확인:
    cat gui_app_modular/window_config.json

  올바른 구조:
    {
      "width": 1500,
      "height": 900,
      "x": 100,
      "y": 100,
      "maximized": false,
      "saved_at": "2026-03-21T14:00:00"
    }

── STEP-W2: _save_window_config() 수정 ───────────────────

  File: gui_app_modular/mixins/window_mixin.py (또는 main_app.py)
  찾기: _save_window_config 또는 창 크기 저장 함수

  올바른 구현:
    def _save_window_config(self) -> None:
        try:
            import json, os
            from datetime import datetime
            self.root.update_idletasks()
            w = self.root.winfo_width()
            h = self.root.winfo_height()
            x = self.root.winfo_x()
            y = self.root.winfo_y()
            maximized = bool(self.root.state() == 'zoomed')
            cfg = {
                "width": w, "height": h,
                "x": x, "y": y,
                "maximized": maximized,
                "saved_at": datetime.now().isoformat()
            }
            config_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                '..', 'window_config.json'
            )
            with open(os.path.normpath(config_path), 'w', encoding='utf-8') as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
            logger.info(f"[WIN] 창 크기 저장: {w}x{h} @ ({x},{y})")
        except Exception as e:
            logger.warning(f"[WIN] 창 크기 저장 실패: {e}")

── STEP-W3: _load_window_config() 수정 ───────────────────

  올바른 구현:
    def _load_window_config(self) -> dict:
        import json, os
        DEFAULT = {"width": 1500, "height": 900, "x": 100, "y": 100,
                   "maximized": False}
        try:
            config_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                '..', 'window_config.json'
            )
            config_path = os.path.normpath(config_path)
            if not os.path.exists(config_path):
                return DEFAULT
            with open(config_path, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
            # 유효성 검사
            w = max(800,  min(int(cfg.get("width",  1500)), 3840))
            h = max(600,  min(int(cfg.get("height",  900)), 2160))
            x = max(0,    min(int(cfg.get("x",       100)), 3000))
            y = max(0,    min(int(cfg.get("y",       100)), 2000))
            return {"width": w, "height": h, "x": x, "y": y,
                    "maximized": bool(cfg.get("maximized", False))}
        except Exception as e:
            logger.warning(f"[WIN] 창 크기 불러오기 실패: {e}")
            return DEFAULT

── STEP-W4: 앱 시작 시 창 크기 적용 ──────────────────────

  File: gui_app_modular/main_app.py
  __init__ 또는 _setup_window() 에서 아래 코드 실행:

    def _apply_window_config(self) -> None:
        try:
            cfg = self._load_window_config()
            if cfg.get("maximized"):
                self.root.state('zoomed')
            else:
                w, h = cfg["width"], cfg["height"]
                x, y = cfg["x"], cfg["y"]
                # 화면 벗어남 방지
                sw = self.root.winfo_screenwidth()
                sh = self.root.winfo_screenheight()
                x = min(x, sw - 200)
                y = min(y, sh - 200)
                self.root.geometry(f"{w}x{h}+{x}+{y}")
            logger.info(f"[WIN] 창 크기 복원: {cfg}")
        except Exception as e:
            logger.warning(f"[WIN] 창 크기 복원 실패: {e}")
            self.root.geometry("1500x900")

  호출 시점: root 생성 직후, 위젯 생성 전
    self.root = tk.Tk()
    self._apply_window_config()   # ← 여기서 호출
    # ... 나머지 위젯 생성

── STEP-W5: 창 크기 변경 감지 → 자동 저장 ───────────────

  창 크기가 바뀔 때 자동으로 저장 (3초 debounce):

    def _setup_window_autosave(self) -> None:
        self._win_save_timer = None
        def _on_configure(event):
            if event.widget != self.root:
                return
            # 3초 debounce — 사이즈 조정 중에는 저장 안 함
            if self._win_save_timer:
                self.root.after_cancel(self._win_save_timer)
            self._win_save_timer = self.root.after(
                3000, self._save_window_config
            )
        self.root.bind('<Configure>', _on_configure)

  호출 위치: _setup_toolbar() 또는 __init__ 마지막 부분

── STEP-W6: 설정/도구 메뉴 "창 크기 저장" 버튼 수정 ─────

  기존 _on_save_window_size() 는 이미 있음.
  _save_window_config() 호출 여부 확인 후 연결:
    def _on_save_window_size(self) -> None:
        self._save_window_config()
        CustomMessageBox.showinfo(
            self.root, "창 크기 저장",
            f"✅ 현재 창 크기가 저장되었습니다.\n\n"
            f"크기: {self.root.winfo_width()} × {self.root.winfo_height()} px"
        )

── PHASE 1-B COMPLETE WHEN ─────────────────────────────────

  ✅ 프로그램 종료 → 재시작 시 마지막 창 크기 유지
  ✅ 최대화 상태도 저장/복원
  ✅ 창이 화면 밖으로 벗어나지 않음
  ✅ _on_save_window_size() 버튼 정상 작동

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[PHASE 1-C: 창 크기 조절 가능 — 모든 다이얼로그]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

현재 문제:
  - 메인 창은 resizable하지만 일부 다이얼로그가 고정 크기
  - 창 크기 변경 시 내부 위젯이 따라 늘어나지 않는 경우 있음

── STEP-R1: 메인 창 resizable 확인 ────────────────────────

  main_app.py에서:
    self.root.resizable(True, True)   # 반드시 True, True

  Notebook과 내부 탭이 창 크기에 따라 늘어나도록:
    self.notebook.pack(fill=BOTH, expand=YES)   # expand=YES 필수

── STEP-R2: 모든 Toplevel 다이얼로그 resizable 적용 ──────

  Find all Toplevel creations:
    grep -rn "Toplevel\|toplevel\|resizable" gui_app_modular/dialogs/ \
      --include="*.py"

  모든 다이얼로그에 적용:
    dlg = tk.Toplevel(self.root)  # 또는 create_themed_toplevel
    dlg.resizable(True, True)     # ← 반드시 추가
    dlg.minsize(600, 400)         # ← 최소 크기 설정

  내부 위젯들도 fill+expand 확인:
    main_frame.pack(fill=BOTH, expand=True)
    scrollbar_frame.pack(fill=BOTH, expand=True)
    treeview.pack(fill=BOTH, expand=True)
    text_widget.pack(fill=BOTH, expand=True)

── STEP-R3: Grid 레이아웃인 경우 weight 설정 ──────────────

  grid 사용 시 행/열에 weight 설정 필요:
    frame.grid_rowconfigure(0, weight=1)
    frame.grid_columnconfigure(0, weight=1)
    frame.grid_columnconfigure(1, weight=1)

── STEP-R4: 자동 스캔 및 일괄 수정 ───────────────────────

  Find dialogs without resizable:
    grep -rn "Toplevel\|Tk()" gui_app_modular/ --include="*.py" -l | \
    xargs grep -L "resizable(True"

  Find frames without expand:
    grep -rn "\.pack(" gui_app_modular/ --include="*.py" | \
    grep -v "expand=True\|fill=BOTH" | grep "Frame\|frame"

  Fix all found cases automatically.

── PHASE 1-C COMPLETE WHEN ─────────────────────────────────

  ✅ 메인 창 좌우상하 크기 조절 가능
  ✅ 모든 다이얼로그 resizable=True
  ✅ 창 크기 변경 시 내부 위젯 따라서 늘어남
  ✅ 최소 크기 제한으로 UI 깨짐 방지

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[PHASE 1-D: UI 글씨/메뉴 크기 및 폭 반복 최적화]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

현재 문제:
  - 탭 레이블, 메뉴 버튼 글씨 크기가 화면 해상도에 따라 부적합
  - 메뉴 폭이 너무 좁거나 넓어 항목이 잘리는 경우 있음
  - 각 탭 내부 컬럼 폭이 내용에 맞지 않음

── STEP-F1: 폰트 스케일 자동 감지 ────────────────────────

  File: gui_app_modular/mixins/toolbar_mixin.py
  FontScale 클래스가 있으면 활용, 없으면 아래 추가:

    def _auto_detect_font_scale(self) -> float:
        """화면 DPI 기반 폰트 배율 자동 감지"""
        try:
            dpi = self.root.winfo_fpixels('1i')
            if dpi >= 192:   return 1.5   # 4K/HiDPI
            elif dpi >= 144: return 1.25  # 2K
            elif dpi >= 96:  return 1.0   # FHD
            else:            return 0.9   # 낮은 해상도
        except Exception:
            return 1.0

  툴바 메뉴 버튼 기본 폰트 크기를 DPI 연동:
    base_size = int(13 * self._auto_detect_font_scale())
    self._tb_font_main = ('맑은 고딕', base_size, 'bold')

── STEP-F2: 메뉴 버튼 균등 배치 및 폭 최적화 ─────────────

  각 메뉴 버튼 레이블 길이 기준 최소 폭 보장:
    - "📁 파일 ▼"     : padx=12
    - "📥 입고 ▼"     : padx=12
    - "📤 출고 ▼"     : padx=12
    - "📊 재고 ▼"     : padx=12
    - "📝 보고서 ▼"   : padx=10
    - "🔧 설정/도구 ▼": padx=8   (길어서 줄임)
    - "❓ 도움말 ▼"   : padx=10

  반복 검증: 창을 1024px, 1366px, 1920px 너비로 변경하며
  모든 버튼이 잘리지 않고 표시되는지 확인.
  잘리면 레이블 단축 (설정/도구 → 설정) 또는 폰트 축소.

── STEP-F3: 탭 내부 Treeview 컬럼 폭 최적화 ──────────────

  각 탭의 Treeview 컬럼 폭을 내용에 맞게:

  판매가능 탭 (inventory_tab.py):
    "LOT NO"      : width=120, minwidth=100
    "SAP NO"      : width=110, minwidth=90
    "BL NO"       : width=130, minwidth=110
    "컨테이너"     : width=130, minwidth=110
    "상태"         : width=90,  minwidth=80
    "현재중량(kg)" : width=110, minwidth=90
    "톤백수"       : width=70,  minwidth=60
    "도착일"       : width=100, minwidth=90
    나머지 컬럼   : stretch=True (남은 공간 균등 배분)

  창 크기 변경 시 컬럼 폭도 비례 조정되도록:
    tree.column("#0", stretch=False)  # 첫 컬럼 고정
    tree.column("LOT NO", stretch=False)
    tree.column("메모", stretch=True)  # 마지막 컬럼만 늘어남

── STEP-F4: 다이얼로그 크기 최적화 ───────────────────────

  모든 다이얼로그 기준:
    최소: 600x400
    기본: 800x600 (입고/출고 등 주요 다이얼로그)
    큰 것: 1000x700 (원스톱 입고 등)
    최대: 1200x900 (초과 방지)

  dlg.minsize(600, 400)
  dlg.maxsize(1400, 1000)

── STEP-F5: 반복 검증 루프 ────────────────────────────────

  이 루프를 최소 3회 반복 실행:
    1. python run.py 실행 (또는 python -m gui_app_modular)
    2. 각 탭 클릭하여 글씨 크기/배치 확인
    3. 창 크기를 1024x768, 1366x768, 1920x1080으로 변경
    4. 메뉴 버튼 모두 클릭하여 폭/항목 확인
    5. 문제 발견 시 즉시 수정
    6. 다음 반복으로 진행

  각 반복 후 로그:
    # UI-ITER-N: [발견 문제] → [수정 내용]

── PHASE 1-D COMPLETE WHEN ─────────────────────────────────

  ✅ 1024px 이상 화면에서 메뉴 버튼 전부 표시됨
  ✅ 각 탭 컬럼 내용이 잘리지 않음
  ✅ 다이얼로그가 화면을 벗어나지 않음
  ✅ 3회 이상 반복 검증 완료

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[PHASE 1-E: 색상 밝기 개선 — Light/Bright 테마]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

현재 문제:
  - 전반적으로 어두운 톤 (darkly 테마 기반)
  - 업무용 앱으로는 눈이 피로함
  - 메뉴바/툴바 색상이 너무 어두워 가독성 낮음

참고 UI (아래 앱의 디자인을 직접 연구하고 적용):
  Linear       → 밝고 깔끔한 사이드바, 적절한 회색 계열
  Notion       → 흰 배경 + 회색 보조 색상, 넓은 여백
  Retool       → 데이터 테이블 밝은 배경, 파란색 액센트
  Vercel       → 흰/밝은 회색 + 강한 대비 텍스트
  Stripe       → 카드형 레이아웃, 연한 배경
  GitHub       → 밝은 회색 계열, 파란 링크
  Figma        → 밝은 툴바, 회색 패널
  Slack        → 보라/남색 사이드바 + 흰 메인 영역

── STEP-C1: 메뉴바 색상 밝게 변경 ────────────────────────

  File: gui_app_modular/mixins/toolbar_mixin.py
  File: gui_app_modular/mixins/custom_menubar.py

  현재 (너무 어두움):
    MENUBAR_BG = '#1a1d27' or '#0f1117'  (거의 검은색)

  개선안 (밝은 남색 → Notion/Linear 스타일):
    # 라이트 모드용
    MENUBAR_BG_LIGHT = '#f0f2f5'         # 밝은 회색
    MENUBAR_FG_LIGHT = '#1a1a2e'         # 진한 남색 텍스트

    # 다크 모드용 (완전 검정 → 회색으로)
    MENUBAR_BG_DARK  = '#2d3250'         # 남색 계열 (Figma 스타일)
    MENUBAR_FG_DARK  = '#e8eaf6'         # 밝은 텍스트

  ThemeColors에서 현재 테마 감지 후 적용:
    _is_dark = is_dark()
    MENUBAR_BG = MENUBAR_BG_DARK if _is_dark else MENUBAR_BG_LIGHT
    MENUBAR_FG = MENUBAR_FG_DARK if _is_dark else MENUBAR_FG_LIGHT

── STEP-C2: 기본 테마 'cosmo' 또는 'litera'로 변경 ────────

  현재: darkly (매우 어두움)

  config.py 또는 테마 초기화 코드에서:
    DEFAULT_THEME = 'cosmo'    # 밝고 깔끔한 파란 액센트

  'cosmo' 테마 특징: 흰 배경 + 파란 액센트 + 깔끔한 서체
  'litera' 테마 특징: 더 밝고 가독성 높음

  단, 기존 darkly 선호 사용자를 위해 설정에서 변경 가능하도록 유지.
  settings.ini [ui] theme = cosmo  (기본값)

── STEP-C3: 상태 배지 색상 개선 ──────────────────────────

  현재 (어두운 배경에서만 잘 보임):
    AVAILABLE: bg=#064e3b, text=#34d399

  개선 (밝은 배경에서도 잘 보임):
    AVAILABLE: bg=#d1fae5, text=#065f46, border=#059669  (초록)
    RESERVED:  bg=#dbeafe, text=#1e40af, border=#3b82f6  (파랑)
    PICKED:    bg=#fef3c7, text=#92400e, border=#f59e0b  (황색)
    OUTBOUND:  bg=#f3f4f6, text=#374151, border=#9ca3af  (회색)
    RETURN:    bg=#fee2e2, text=#991b1b, border=#ef4444  (빨강)

  Treeview에서 배지 표시:
    tag_configure('AVAILABLE', background='#d1fae5', foreground='#065f46')
    tag_configure('RESERVED',  background='#dbeafe', foreground='#1e40af')
    tag_configure('PICKED',    background='#fef3c7', foreground='#92400e')
    tag_configure('OUTBOUND',  background='#f3f4f6', foreground='#374151')
    tag_configure('RETURN',    background='#fee2e2', foreground='#991b1b')

── STEP-C4: 카드/프레임 배경 밝게 ────────────────────────

  KPI 카드, 요약 패널, 하단 상태바:
    배경: #ffffff 또는 #f8fafc (밝은 흰색)
    테두리: #e2e8f0 (연한 회색)
    제목 텍스트: #1e293b (진한 슬레이트)
    수치: #0f172a (매우 진한)
    부제: #64748b (중간 회색)

── STEP-C5: ThemeColors 팔레트 추가 ──────────────────────

  File: gui_app_modular/utils/ui_constants.py

  LIGHT_PALETTE 추가 (Linear/Notion 스타일):
    LIGHT_PALETTE = {
        'bg_primary':       '#ffffff',
        'bg_secondary':     '#f8fafc',
        'bg_tertiary':      '#f1f5f9',
        'bg_card':          '#ffffff',
        'border':           '#e2e8f0',
        'text_primary':     '#0f172a',
        'text_secondary':   '#475569',
        'text_muted':       '#94a3b8',
        'accent':           '#3b82f6',   # 파랑 (Retool/Linear)
        'success':          '#10b981',
        'warning':          '#f59e0b',
        'danger':           '#ef4444',
        'info':             '#6366f1',
        'statusbar_bg':     '#f0f2f5',
        'statusbar_fg':     '#1e293b',
    }

── STEP-C6: 색상 변경 반복 검증 ──────────────────────────

  각 화면에서 다음을 확인하며 최소 3회 반복:
  1. 툴바/메뉴바가 밝고 가독성 있는지
  2. 테이블 배경이 눈에 편한지
  3. 상태 배지가 밝은 배경에서도 잘 구분되는지
  4. 다이얼로그가 전체적으로 밝고 깔끔한지
  5. 다크모드 ↔ 라이트모드 전환 시 색상 깨짐 없는지

  "밝게 수정 → 실행 → 확인 → 재수정" 루프를 만족할 때까지 반복.

── PHASE 1-E COMPLETE WHEN ─────────────────────────────────

  ✅ 기본 테마 'cosmo'로 변경
  ✅ 메뉴바 배경이 밝은 계열 (#f0f2f5 또는 #2d3250)
  ✅ 상태 배지가 밝은 배경에서도 구분 가능
  ✅ 전체 UI 톤이 Linear/Notion 수준으로 밝아짐
  ✅ 3회 이상 반복 검증 완료


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[PHASE 1-F: 대시보드 UI 개선 — 2026-03-22 신규]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

── BUG-9 [P1] AL-06 SALE_REF_CONFLICT — 같은 파일 내 동일 SALE REF 차단 버그 ──

  File: engine_modules/inventory_modular/outbound_mixin.py
  Problem: AL-06 규칙이 같은 Allocation 파일 내 88개 LOT이 동일 SALE REF 사용 시
           첫 번째 LOT 예약 후 나머지 87개를 전부 HARD STOP으로 차단
           실제 업무: 파일 1개 = 88개 LOT이 모두 같은 SALE REF 공유가 정상
  Fix: SQL에 source_fingerprint 조건 추가 (같은 파일 내 동일 SALE REF 허용)

  현재 코드 (1467~1488행):
    _al06_dup = self.db.fetchone(
        """SELECT id, lot_no, customer FROM allocation_plan
           WHERE sale_ref = ?
             AND status IN ('RESERVED','PENDING_APPROVAL','STAGED')
             AND lot_no != ?
           LIMIT 1""",
        (sale_ref, lot_no)
    )

  수정 코드:
    # ★ 같은 파일(source_fingerprint)에서 온 배치는 동일 sale_ref 허용
    _al06_dup = self.db.fetchone(
        """SELECT id, lot_no, customer FROM allocation_plan
           WHERE sale_ref = ?
             AND status IN ('RESERVED','PENDING_APPROVAL','STAGED')
             AND lot_no != ?
             AND (source_fingerprint != ? OR source_fingerprint IS NULL OR source_fingerprint = '')
           LIMIT 1""",
        (sale_ref, lot_no, source_fingerprint or '')
    )

── BUG-10 [P1] 총괄재고 판매배정 카운트 0 — LOT모드 RESERVED 미반영 ──────────

  File: engine_modules/inventory_modular/query_mixin.py
  Problem: get_cargo_overview_counts()에서 RESERVED 카운트를
           allocation_plan JOIN inventory_tonbag ON tonbag_id 로 조회
           → LOT 모드 예약 시 tonbag_id = NULL → JOIN 실패 → 카운트 0
           fallback도 inventory_tonbag.status='RESERVED' 인데
           LOT모드에서 톤백 상태는 여전히 AVAILABLE → 역시 0
  Fix: allocation_plan 직접 조회로 변경

  현재 코드 (447~457행):
    res = self.db.fetchone(
        """SELECT COUNT(DISTINCT t.lot_no) AS c FROM allocation_plan ap
           JOIN inventory_tonbag t ON ap.tonbag_id = t.id
           WHERE ap.status = 'RESERVED'""")

  수정 코드:
    # ★ LOT 모드(tonbag_id=NULL) + 톤백 모드 모두 포함
    res = self.db.fetchone(
        """SELECT COUNT(DISTINCT lot_no) AS c
           FROM allocation_plan
           WHERE status = 'RESERVED'""")

── BUG-11 [P2] SALE REF 입력창 글씨 안 보임 — askstring 테마 미적용 ──────────

  File: gui_app_modular/tabs/allocation_tab.py
  Problem: tkinter.simpledialog.askstring()이 ttkbootstrap 테마 미적용
           darkly 테마 주황색 배경에 기본 텍스트 색상이 보이지 않음
  Fix: create_themed_toplevel + ttkbootstrap Entry로 교체

  현재 코드 (642~647행):
    import tkinter.simpledialog as sd
    sale_ref = sd.askstring(
        "SALE REF 일괄 취소",
        "취소할 SALE REF(판매참조번호)를 입력하세요.\n예: 1955",
        parent=root
    )

  수정 코드:
    import tkinter as _tk
    from gui_app_modular.utils.ui_constants import create_themed_toplevel
    import ttkbootstrap as _ttk
    _dlg = create_themed_toplevel(root)
    _dlg.title("🔢 SALE REF 일괄 취소")
    _dlg.geometry("360x160")
    _dlg.resizable(False, False)
    _dlg.grab_set()
    _ttk.Label(_dlg, text="취소할 SALE REF를 입력하세요.",
               font=("맑은 고딕", 10)).pack(pady=(18,4), padx=20, anchor='w')
    _ttk.Label(_dlg, text="예: 3352", font=("맑은 고딕", 9),
               bootstyle="secondary").pack(padx=20, anchor='w')
    _var = _tk.StringVar()
    _entry = _ttk.Entry(_dlg, textvariable=_var, font=("맑은 고딕", 12), width=20)
    _entry.pack(pady=8, padx=20)
    _entry.focus_set()
    _result = [None]
    def _ok(e=None): _result[0]=_var.get().strip(); _dlg.destroy()
    def _cancel(e=None): _dlg.destroy()
    _entry.bind('<Return>', _ok); _entry.bind('<Escape>', _cancel)
    _bf = _ttk.Frame(_dlg); _bf.pack(pady=4)
    _ttk.Button(_bf, text="확인", bootstyle="warning", command=_ok, width=8).pack(side='left', padx=6)
    _ttk.Button(_bf, text="취소", bootstyle="secondary-outline", command=_cancel, width=8).pack(side='left', padx=6)
    _dlg.wait_window()
    sale_ref = _result[0]

  NOTE: askstring 패턴이 다른 곳에도 있을 수 있음
    grep -rn "askstring\|simpledialog" gui_app_modular/ --include="*.py"
    → 전부 create_themed_toplevel 방식으로 교체

── BUG-12 [P2] 대시보드 판매배정 0개 — LOT모드 RESERVED 미반영 ────────────────

  File A: gui_app_modular/tabs/dashboard_data_mixin.py
  Problem: _get_status_four_phase_stats()가 inventory_tonbag.status='RESERVED'로 집계
           LOT 모드 예약 시 톤백 상태는 여전히 AVAILABLE → reserved_cnt=0
  Fix A: reserved_cnt/kg을 allocation_plan 기준으로 별도 조회

  수정 코드 (dashboard_data_mixin.py _get_status_four_phase_stats 내):
    # 기존 쿼리에서 reserved_cnt/kg 제거 후 아래 추가
    res_row = self.engine.db.fetchone("""
        SELECT
            COUNT(DISTINCT lot_no)        AS reserved_lot_cnt,
            COUNT(*)                      AS reserved_plan_cnt,
            COALESCE(SUM(qty_mt)*1000, 0) AS reserved_kg
        FROM allocation_plan
        WHERE status = 'RESERVED'
    """)
    r_lot  = int((res_row or {}).get('reserved_lot_cnt',  0) or 0)
    r_plan = int((res_row or {}).get('reserved_plan_cnt', 0) or 0)
    r_kg   = float((res_row or {}).get('reserved_kg',     0) or 0)
    # return dict에 추가:
    'reserved_lot_cnt': r_lot,
    'reserved_plan_cnt': r_plan,
    'reserved_cnt': r_plan,   # 기존 키 유지 (하위호환)
    'reserved_kg': r_kg,

  File B: gui_app_modular/tabs/dashboard_tab.py
  Fix B-1: 워크플로 배지행(badge_row) 삭제

    삭제 대상 (184~200행):
      badge_row = tk.Frame(hero, bg=hero_bg)
      badge_row.pack(fill='x', padx=16, pady=(0, 12))
      STAGES = [('📦 판매가능',...), ('📋 판매배정',...), ...]
      for idx, (lbl, color) in enumerate(STAGES): ...

  Fix B-2: 카드 3단 표시 (톤백수/MT/LOT수) — _refresh_dash_cards()

    현재:
      def _set_card(key, cnt, kg):
          card.value_label.config(text=f"{cnt}개")
          card.sub_label.config(text=f"{kg/1000:,.1f} MT")

    수정:
      def _set_card(key, cnt, kg, lot_cnt=0, suffix='개', sub2=''):
          card.value_label.config(text=f"{cnt:,}{suffix}")
          card.sub_label.config(text=f"{kg/1000:,.1f} MT")
          if hasattr(card, 'sub2_label'):
              card.sub2_label.config(text=sub2 or f"{lot_cnt} LOT")

      # 판매배정 카드 호출:
      _set_card('status_reserved', r_plan, r_kg, suffix='행',
                sub2=f"{r_lot} LOT · {int(r_kg/500)}톤백")

  결과 표시 예시:
    판매가능:   880개  / 440.0 MT  / 88 LOT
    판매배정:    88행  / 120.0 MT  / 88 LOT · 240톤백
    판매화물 결정: 0개 /   0.0 MT  / 0 LOT
    출고완료:     0개  /   0.0 MT  / 0 LOT
    반품대기:     0개  /   0.0 MT  / 0 LOT

── PHASE 1-F COMPLETE WHEN ──────────────────────────────────────────────

  ✅ BUG-9: AL-06 수정 → 88개 LOT 동일 SALE REF 예약 성공
  ✅ BUG-10: 총괄재고 판매배정 (88) 정상 표시
  ✅ BUG-11: SALE REF 입력창 글씨 정상 표시
  ✅ BUG-12: 대시보드 판매배정 카드 3단 표시 (행수/MT/LOT·톤백)
  ✅ 대시보드 워크플로 배지행 삭제
  ✅ 모든 askstring → create_themed_toplevel 교체


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[PHASE 1-G: LOT별 통합 현황 뷰 + 샘플 처리 — 2026-03-22 신규]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

배경:
  - 현재 판매배정 예약 현황 창은 allocation_plan 행 단위 (264행)로 표시
  - LOT 단위 통합 현황 (AVAILABLE→RESERVED→PICKED→OUTBOUND 흐름) 이 없음
  - 샘플(tonbag_no=S00, is_sample=1, weight=1kg)이 일반 톤백과 섞여 집계됨
  - LOT당 샘플 1개(1kg) 고정 → 인라인 컬럼으로 처리하는 것이 최적

샘플 구조 (DB 확인):
  - inventory_tonbag WHERE is_sample=1
  - sub_lt=0, tonbag_no='S00', weight=1.0kg
  - LOT당 1개 고정, 88 LOT = 88개 샘플 / 88kg
  - 일반 톤백: 880개 / 440,000kg (500kg × 10개)

── FEATURE-G1 [P2] LOT별 통합 현황 팝업 ─────────────────────

  추가 위치: gui_app_modular/tabs/allocation_tab.py
  트리거: 판매배정 탭 → 📊 예약 현황 버튼 (기존 버튼 기능 확장)

  신규 쿼리 (LotStatusDialog에서 사용):
    SELECT
        i.lot_no, i.sap_no,
        COUNT(CASE WHEN COALESCE(t.is_sample,0)=0 THEN 1 END) AS tot_tb,
        COUNT(CASE WHEN t.status='AVAILABLE' AND COALESCE(t.is_sample,0)=0 THEN 1 END) AS avail_tb,
        COALESCE((SELECT CAST(SUM(ap.qty_mt/0.5) AS INT)
                  FROM allocation_plan ap
                  WHERE ap.lot_no=i.lot_no AND ap.status='RESERVED'), 0) AS rsv_tb,
        COALESCE((SELECT SUM(ap.qty_mt)
                  FROM allocation_plan ap
                  WHERE ap.lot_no=i.lot_no AND ap.status='RESERVED'), 0) AS rsv_mt,
        COALESCE((SELECT GROUP_CONCAT(DISTINCT ap.sale_ref)
                  FROM allocation_plan ap
                  WHERE ap.lot_no=i.lot_no AND ap.status='RESERVED'), '') AS sale_refs,
        COUNT(CASE WHEN t.status='PICKED'   AND COALESCE(t.is_sample,0)=0 THEN 1 END) AS pick_tb,
        COUNT(CASE WHEN t.status IN ('OUTBOUND','SOLD')
                    AND COALESCE(t.is_sample,0)=0 THEN 1 END) AS out_tb,
        -- 샘플 인라인
        MAX(CASE WHEN COALESCE(t.is_sample,0)=1 THEN t.status END) AS samp_status,
        COUNT(CASE WHEN COALESCE(t.is_sample,0)=1 THEN 1 END) AS samp_cnt
    FROM inventory i
    LEFT JOIN inventory_tonbag t ON t.lot_no=i.lot_no
    GROUP BY i.lot_no
    ORDER BY i.lot_no

  팝업 컬럼 구성 (LotStatusDialog Treeview):
    LOT NO / SAP NO / 총톤백 / AVAILABLE / RESERVED(톤백·MT) /
    PICKED / OUTBOUND / 샘플(1kg) / 배정비율(%) / SALE REF

  LOT 상태 자동 계산:
    if out_tb >= tot_tb:       → OUTBOUND
    elif pick_tb > 0:          → PICKED
    elif rsv_tb >= tot_tb:     → FULL_RESERVED
    elif rsv_tb > 0:           → PARTIAL
    else:                      → AVAILABLE

  배정비율 표시:
    pct = int((rsv_tb + pick_tb + out_tb) / tot_tb * 100)
    Progress bar + 숫자 % 병행 표시

  샘플 컬럼 표시:
    samp_cnt > 0 → f"{samp_cnt}개 · {samp_status}"  (주황 배지)
    samp_cnt == 0 → "-"

  구현 파일:
    신규: gui_app_modular/dialogs/lot_status_dialog.py
    수정: gui_app_modular/tabs/allocation_tab.py
          _on_allocation_status() 메서드에서 LotStatusDialog 호출

── FEATURE-G2 [P2] Allocation 파일 샘플 포함 옵션 ───────────────

  현재: 샘플 행 포함/제외가 파일 생성 시 고정
  변경: "샘플 포함" 체크박스 옵션 추가

  적용 위치: Allocation 파일 생성 다이얼로그 (allocation_dialog.py)
    self._include_sample_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(frame, text="샘플 행 포함 (MIC9000 Sample / 0.001MT)",
                    variable=self._include_sample_var).pack(...)

  샘플 포함 시 파일 구조:
    행1: LITHIUM CARBONATE  / LOT=1126010634 / QTY=1.500 (일반 3톤백)
    행2: LITHIUM CARBONATE sample / LOT=1126010634 / QTY=0.001 (샘플 1kg)

  파싱 시: qty_mt < 0.01 → is_sample=True 자동 감지 (기존 로직 유지)

  포함 기준:
    - 고객(PT LBM 등)이 요청하는 경우: 포함
    - 내부 재고 배정: 생략 권장
    - 기본값: False (미포함)

── FEATURE-G3 [P2] LOT별 현황 Excel 내보내기 ────────────────────

  추가 위치: gui_app_modular/tabs/allocation_tab.py 또는 LotStatusDialog
  트리거: LOT 현황 팝업 → "📥 Excel 저장" 버튼

  Excel 구조 (2시트):

  시트1: "LOT별 현황"
    컬럼: LOT NO / SAP NO / 총톤백 / AVAILABLE / RESERVED(톤백) /
          RESERVED(MT) / PICKED / OUTBOUND / 샘플상태 / 배정% / SALE REF
    조건부 서식:
      - RESERVED > 0 행: 파란 배경 (#dbeafe)
      - PICKED > 0 행: 황색 배경 (#fef3c7)
      - 배정% 컬럼: DataBar (파란색)
    헤더: 진한 배경 (#1e3a5f), 흰 글씨, bold

  시트2: "샘플 현황"
    컬럼: LOT NO / 샘플NO(S00) / 중량(kg) / 상태 / 입고일 / SALE REF
    is_sample=1 톤백만 별도 조회
    상태별 색상: AVAILABLE=초록, RESERVED=파랑, PICKED=황색

  저장 경로: config.EXPORT_DIR / f"SQM_LOT현황_{datetime:%Y%m%d_%H%M}.xlsx"
  저장 후: os.startfile() 로 자동 열기

  구현:
    def _on_export_lot_status_excel(self) -> None:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
        from openpyxl.formatting.rule import DataBarRule
        wb = openpyxl.Workbook()
        # 시트1: LOT별 현황
        ws1 = wb.active; ws1.title = "LOT별 현황"
        headers1 = ['LOT NO','SAP NO','총톤백','AVAILABLE',
                    'RESERVED(톤백)','RESERVED(MT)','PICKED','OUTBOUND',
                    '샘플상태','배정%','SALE REF']
        # ... 헤더 스타일 + 데이터 + 조건부 서식
        # 시트2: 샘플 현황
        ws2 = wb.create_sheet("샘플 현황")
        headers2 = ['LOT NO','샘플NO','중량(kg)','상태','입고일','SALE REF']
        # ... is_sample=1 데이터
        fname = f"SQM_LOT현황_{datetime.now():%Y%m%d_%H%M}.xlsx"
        path = Path(getattr(config, 'EXPORT_DIR', '.')) / fname
        wb.save(str(path))
        try: os.startfile(str(path))
        except Exception: pass

── PHASE 1-G COMPLETE WHEN ──────────────────────────────────────

  ✅ LotStatusDialog 신규 생성 (lot_status_dialog.py)
  ✅ 판매배정 탭 예약 현황 버튼 → LOT 통합 팝업 표시
  ✅ 팝업에 샘플 인라인 컬럼 포함 (samp_cnt · samp_status)
  ✅ LOT 상태 자동 계산 (AVAILABLE/PARTIAL/FULL_RESERVED/PICKED/OUTBOUND)
  ✅ 배정비율 Progress bar 표시
  ✅ Allocation 파일 생성 시 "샘플 포함" 체크박스 옵션 추가
  ✅ LOT 현황 Excel 내보내기 (2시트: LOT별 + 샘플 현황)
  ✅ 조건부 서식: RESERVED/PICKED 행 색상 + 배정% DataBar


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[PHASE 1-H: 스캔→출고→SalesOrder 로직 보완 — 2026-03-22 신규]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

배경 및 설계 원칙:
  - LOT 모드 예약: allocation_plan.tonbag_id = NULL (어떤 톤백인지 스캔 전까지 미확정)
  - 바코드 스캔 순간: 처음으로 "LOT X의 Y번 톤백이 나간다" 확정
  - picking_table: 스캔 시 LOT + tonbag_uid + picking_no + customer INSERT
  - sold_table: 출고확정(OUTBOUND) 시 Sales Order 최종 기록

전체 흐름 (5단계):
  STEP1: 피킹리스트 PDF 수신 → 파싱 → LOT 목록 추출 (톤백 미확정)
  STEP2: Gate-1 검증 → allocation_plan RESERVED 교차 확인 (tonbag 상태 변경 없음)
  STEP3: 현장 바코드 스캔 → AVAILABLE→PICKED + picking_table INSERT (톤백 확정)
  STEP4: 출고확정 스캔 → PICKED→OUTBOUND + sold_table INSERT
  STEP5: Sales Order 완성 (picking_table + sold_table 합산)

스캔 후 채워지는 테이블:
  inventory_tonbag: status AVAILABLE→PICKED, updated_at=스캔시각
  picking_table:    lot_no, tonbag_id, tonbag_uid(바코드), picking_no,
                    customer, sale_ref, qty_kg, picking_date INSERT
  allocation_plan:  tonbag_id 확정, status=EXECUTED, executed_at
  sold_table:       lot_no, tonbag_uid, sales_order_no, picking_id,
                    sold_qty_mt, sold_qty_kg, bl_no, sap_no, sold_date INSERT

── BUG-13 [P1] 출고확정 스캔 시 sold_table 미연결 ─────────────────

  File: gui_app_modular/tabs/scan_tab.py
  Problem: _on_quick_outbound() 에서
           inventory_tonbag.status = 'OUTBOUND' 만 변경하고
           sold_table INSERT가 자동으로 수행되지 않음
           → confirm_outbound()를 별도 호출해야만 sold_table에 기록됨
           → 호출 누락 시 sold_table 공백 → Sales Order 기록 불완전

  현재 코드 (_on_quick_outbound):
    self.db.execute(
        "UPDATE inventory_tonbag SET status='OUTBOUND', updated_at=? WHERE tonbag_uid=?",
        (now, uid)
    )
    # ← sold_table INSERT 없음 (누락)

  수정 코드:
    # PICKED → OUTBOUND 전환
    self.db.execute(
        "UPDATE inventory_tonbag SET status='OUTBOUND', updated_at=? WHERE tonbag_uid=?",
        (now, uid)
    )
    # ★ sold_table INSERT 추가
    try:
        tb_full = self.db.fetchone(
            "SELECT id, lot_no, sub_lt, tonbag_uid, weight "
            "FROM inventory_tonbag WHERE tonbag_uid=?", (uid,)
        )
        plan = self.db.fetchone(
            "SELECT customer, sale_ref, outbound_date "
            "FROM allocation_plan "
            "WHERE lot_no=? AND status IN ('RESERVED','EXECUTED') "
            "ORDER BY id DESC LIMIT 1",
            (tb_full['lot_no'],)
        )
        pick_row = self.db.fetchone(
            "SELECT id, picking_no, sales_order_no FROM picking_table "
            "WHERE tonbag_uid=? AND status='ACTIVE' LIMIT 1", (uid,)
        )
        inv = self.db.fetchone(
            "SELECT sap_no, bl_no FROM inventory WHERE lot_no=?",
            (tb_full['lot_no'],)
        )
        qty_kg = float(tb_full['weight'] or 0)
        self.db.execute(
            """INSERT OR IGNORE INTO sold_table
            (lot_no, tonbag_id, sub_lt, tonbag_uid, picking_id,
             sales_order_no, picking_no, sap_no, bl_no,
             customer, sold_qty_mt, sold_qty_kg,
             status, sold_date, created_by, remark)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,'CONFIRMED',?,'system',?)""",
            (
                tb_full['lot_no'],
                tb_full['id'],
                tb_full['sub_lt'],
                uid,
                pick_row['id'] if pick_row else None,
                pick_row['sales_order_no'] if pick_row else (plan['sale_ref'] if plan else ''),
                pick_row['picking_no'] if pick_row else '',
                inv['sap_no'] if inv else '',
                inv['bl_no'] if inv else '',
                plan['customer'] if plan else '',
                round(qty_kg / 1000, 4),
                qty_kg,
                now,
                f"scan_출고확정 uid={uid}"
            )
        )
        logger.info(f"[scan_outbound] sold_table INSERT: {uid} lot={tb_full['lot_no']}")
    except Exception as _se:
        logger.warning(f"[scan_outbound] sold_table INSERT 실패: {_se}")

── BUG-14 [P2] picking_table 생성 시 allocation_plan 연결 누락 ────────

  File: gui_app_modular/tabs/scan_tab.py (_on_quick_pick)
  Problem: picking_table INSERT 시 outbound_id, sales_order_no 필드가
           allocation_plan 또는 picking_list_order 에서 조회되지 않아 공백
  Fix:
    # allocation_plan에서 outbound_id 추가 조회
    plan_full = self.db.fetchone(
        "SELECT customer, sale_ref, outbound_date, outbound_id "
        "FROM allocation_plan "
        "WHERE lot_no=? AND status IN ('RESERVED','PICKED') "
        "ORDER BY id DESC LIMIT 1", (lot_no,)
    )
    # picking_list_order에서 sales_order_no 조회
    plo = self.db.fetchone(
        "SELECT sales_order FROM picking_list_order "
        "WHERE lot_no=? ORDER BY id DESC LIMIT 1", (lot_no,)
    ) if self._table_exists('picking_list_order') else None

── FEATURE-H1 [P2] Picking List 파서 이슈 3개 수정 ─────────────────────

  File: parsers/picking_list_parser.py

  이슈1: 자재코드 30000008 하드코딩 → config 분리
    # 현재 (하드코딩):
    main = next(it for it in doc.items if it.material_code == "30000008")

    # 수정: config에서 읽기
    from config import PICKING_MAIN_MATERIAL_CODE   # 기본값: "30000008"
    main = next(it for it in doc.items
                if it.material_code == PICKING_MAIN_MATERIAL_CODE and it.total_unit == "MT")

    # config.py에 추가:
    PICKING_MAIN_MATERIAL_CODE   = "30000008"   # 리튬카보네이트 본품
    PICKING_SAMPLE_MATERIAL_CODE = "30000010"   # 리튬카보네이트 샘플

  이슈2: 샘플 감지를 description 기준으로만 판단 → 자재코드 추가
    # 현재: "SAMPLE" in description.upper()
    # 수정:
    samp = next(
        (it for it in doc.items
         if it.material_code == PICKING_SAMPLE_MATERIAL_CODE
         or "SAMPLE" in (it.description or "").upper()),
        None
    )

  이슈3: 컨테이너 수 기본값 15 하드코딩 → 경고 + 사용자 입력
    # 현재: containers = 15 (파싱 실패 시 자동)
    # 수정: 파싱 실패 시 경고 + 사용자 입력 또는 config 기본값
    from config import PICKING_DEFAULT_CONTAINERS   # 기본값: 15
    if containers is None or containers < 1:
        logger.warning("[picking] 컨테이너 수 파싱 실패 → 기본값 사용: %d", PICKING_DEFAULT_CONTAINERS)
        containers = PICKING_DEFAULT_CONTAINERS

── 자재코드 체계 정리 (참고) ───────────────────────────────────────────

  피킹리스트 자재코드 (SQM 내부 8자리):
    30000008 → LITHIUM CARBONATE BATTERY GRADE (본품, 단위: MT)
    30000010 → LITHIUM CARBONATE SAMPLE        (샘플, 단위: KG)

  SQM DB SAP NO (출하 문서번호 10자리):
    2200034273 → 선적 건별 발번 (BL/PL/FA 기준)
    2200034274 → 동일 선박 다른 B/L
    → 두 코드는 완전히 다른 체계 (혼동 금지)

  Batch number (피킹리스트) = lot_no (SQM DB)
    피킹리스트의 "Batch number: 1126010634"
    = SQM inventory.lot_no = "1126010634"
    → Gate-1에서 allocation_plan.lot_no와 교차 검증

── PHASE 1-H COMPLETE WHEN ─────────────────────────────────────────────

  ✅ BUG-13: 출고확정 스캔 시 sold_table 자동 INSERT 연결
  ✅ BUG-14: picking_table 생성 시 sales_order_no + outbound_id 연결
  ✅ FEATURE-H1: 피킹리스트 파서 이슈 3개 수정
  ✅ config.py에 PICKING_MAIN_MATERIAL_CODE = "30000008" 추가
  ✅ 출고확정 → sold_table 자동 완성 → Sales Order 기록 온전화


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[PHASE 1-H: v815 세션 추가 버그 수정 — 2026-03-22 신규]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

배경:
  LOT 단위 예약(톤백 미지정)과 일반 톤백 집계가 섞이거나 누락되어
  숫자·UI가 어긋나는 문제가 다수 발견됨.
  판매배정·총괄·대시보드에서 LOT별 흐름을 일관되게 보여주도록 전면 수정.

── BUG-13 [P1] SALE REF 일괄 취소 — 반응 없음처럼 보임 ──────────

  File: gui_app_modular/utils/custom_messagebox.py
        gui_app_modular/tabs/allocation_tab.py

  Problem: askstring에서 parent가 비정상일 때
           winfo_fpixels → AttributeError 로 콜백 전체 실패
           모달이 메인 창 뒤에 깔려 사용자가 인식 못함
           빈 값 확인 후 안내 없이 조용히 return

  Fix (custom_messagebox.py — CustomMessageBox.askstring):
    1. 부모 보정: parent가 없으면 _default_root 사용
    2. transient() 실패 시 예외 무시 (try/except)
    3. DPI 예외 범위 확대 (winfo_fpixels AttributeError 포함)
    4. dlg.lift() + dlg.focus_force() 추가 → 창이 앞에 뜨도록 보장

  Fix (allocation_tab.py — _on_allocation_cancel_by_sale_ref):
    5. askstring 예외 시 CustomMessageBox.showerror 표시
    6. 빈 값 입력 시 "SALE REF를 입력하세요" 경고 표시

  수정 코드 핵심:
    def askstring(cls, parent, title, prompt, **kw):
        try:
            root = parent or cls._default_root or tk._default_root
            dlg = create_themed_toplevel(root)
            dlg.transient(root) if root else None
            dlg.lift()
            dlg.focus_force()
            # ... Entry + 확인/취소 버튼
        except AttributeError:
            # DPI/winfo 예외 → fallback
            import tkinter.simpledialog as sd
            return sd.askstring(title, prompt, parent=parent)

── BUG-14 [P2] 전체 배정 보기 ↔ LOT 리스트 상단 복귀 버튼 ─────────

  File: gui_app_modular/tabs/allocation_tab.py

  Problem: "← LOT 리스트로" 복귀 버튼이 상단에 안 보이거나
           전환 반복 시 레이아웃 이상 발생

  Fix: 전체 배정 보기 진입 시 상단 복귀 버튼을
       pack_forget() 후 before=새로고침버튼 위치로 다시 pack

  수정 코드:
    def _show_allocation_detail_view(self):
        # 기존 복귀 버튼 제거 후 재배치
        if hasattr(self, '_btn_back_to_lot'):
            self._btn_back_to_lot.pack_forget()
        self._btn_back_to_lot.pack(
            side=LEFT, padx=4,
            before=self._btn_refresh   # 새로고침 버튼 앞에 배치
        )

── BUG-15 [P1] RESERVED 집계 0 — LOT 모드 + 톤백 UNION 누락 ────────

  File: engine_modules/inventory_modular/query_mixin.py
  Functions: get_cargo_overview_counts(), get_cargo_overview_lots()

  Problem: allocation_plan.tonbag_id IS NULL인 LOT 예약은
           inventory_tonbag INNER JOIN 시 완전히 누락
           fallback이 inventory_tonbag.status='RESERVED'만 보면
           LOT 모드에서 톤백은 여전히 AVAILABLE → 또 0

  Fix: RESERVED LOT = allocation_plan(RESERVED) DISTINCT lot_no
       UNION inventory_tonbag.status='RESERVED' (비샘플)

  수정 코드 (get_cargo_overview_counts):
    # ★ LOT 모드 + 톤백 모드 UNION
    res = self.db.fetchone("""
        SELECT COUNT(DISTINCT lot_no) AS c FROM (
            SELECT lot_no FROM allocation_plan
            WHERE status = 'RESERVED'
            UNION
            SELECT lot_no FROM inventory_tonbag
            WHERE status = 'RESERVED'
              AND COALESCE(is_sample, 0) = 0
        )
    """)

  수정 코드 (get_cargo_overview_lots — RESERVED 필터):
    # status_filter = 'RESERVED' 일 때:
    WHERE i.lot_no IN (
        SELECT lot_no FROM allocation_plan WHERE status='RESERVED'
        UNION
        SELECT lot_no FROM inventory_tonbag
        WHERE status='RESERVED' AND COALESCE(is_sample,0)=0
    )

── BUG-16 [P1] 출고예정 할당 kg — LOT 모드 0 누락 ──────────────────

  File: engine_modules/inventory_modular/query_mixin.py
  Function: get_inventory_outbound_scheduled()

  Problem: tonbag_id가 NULL인 LOT 모드 예약은 할당 kg가 0으로 집계됨

  Fix: tonbag_id 유무에 따라 분기
    CASE
      WHEN ap.tonbag_id IS NOT NULL THEN t.weight
      ELSE ap.qty_mt * 1000
    END AS allocated_kg
    -- 샘플 톤백 제외 조건 추가
    AND COALESCE(t.is_sample, 0) = 0

  수정 코드:
    SELECT
        ap.lot_no, ap.sale_ref, ap.customer,
        ap.qty_mt,
        CASE
            WHEN ap.tonbag_id IS NOT NULL
            THEN COALESCE(t.weight, ap.qty_mt * 1000)
            ELSE ap.qty_mt * 1000
        END AS allocated_kg
    FROM allocation_plan ap
    LEFT JOIN inventory_tonbag t
        ON t.id = ap.tonbag_id
        AND COALESCE(t.is_sample, 0) = 0
    WHERE ap.status = 'RESERVED'

── BUG-17 [P2] 대시보드 판매배정 카드 — 3단 지표 ────────────────────

  File: gui_app_modular/tabs/dashboard_data_mixin.py
        gui_app_modular/tabs/dashboard_tab.py

  Problem: 카드가 톤백 RESERVED만 세서 LOT 모드와 불일치
           N LOT / MT / 톤백수 3단 표시가 없음

  Fix (dashboard_data_mixin.py):
    # allocation_plan 기준 + 비연결 RESERVED 톤백 보완
    res_row = self.engine.db.fetchone("""
        SELECT
            COUNT(DISTINCT lot_no)        AS reserved_lot_cnt,
            COUNT(*)                      AS reserved_plan_cnt,
            COALESCE(SUM(qty_mt)*1000, 0) AS reserved_kg
        FROM allocation_plan
        WHERE status = 'RESERVED'
    """)
    # 비연결 RESERVED 톤백(tonbag 직접 RESERVED) 보완
    tb_row = self.engine.db.fetchone("""
        SELECT COUNT(*) AS cnt, COALESCE(SUM(weight),0) AS kg
        FROM inventory_tonbag
        WHERE status='RESERVED' AND COALESCE(is_sample,0)=0
          AND id NOT IN (
              SELECT tonbag_id FROM allocation_plan
              WHERE tonbag_id IS NOT NULL AND status='RESERVED'
          )
    """)
    reserved_tonbag_cnt = r_plan + int((tb_row or {}).get('cnt', 0))
    reserved_kg = r_kg + float((tb_row or {}).get('kg', 0))

  Fix (dashboard_tab.py — _set_card):
    # 판매배정 카드: N행 / MT / LOT수·톤백수
    _set_card('status_reserved',
              r_plan, reserved_kg, suffix='행',
              sub2=f"{r_lot} LOT · {reserved_tonbag_cnt}톤백")

── FEATURE-H1 [P2] allocation_lot_overview_mixin.py 신규 ────────────

  신규 파일: gui_app_modular/tabs/allocation_lot_overview_mixin.py
  진입: 판매배정 탭 → 📊 LOT 현황 버튼 → Toplevel 그리드 창

  핵심 설계:

  1) 샘플 집계 4단계 검증:
    samp_cnt == 0    → "없음"
    samp_cnt == 1    → "1개 · {samp_status}"  (주황 배지)
    samp_cnt >= 2    → "⚠ {samp_cnt}개?"      (경고)
    samp_cnt != expected → "⚠ 불일치"

  2) 상태 약어 표기:
    AVAILABLE → AVAIL
    RESERVED  → RSV
    PICKED    → PICK
    OUTBOUND  → OUT

  3) 배정 비율 계산 (샘플 제외):
    분모: 일반 톤백 총중량 (is_sample=0)
    분자: 일반 RESERVED kg
          + 일반 PICKED kg
          + 출고 kg
          + LOT 모드 plan SUM(qty_mt) * 1000
    pct = min(100, int(분자 / 분모 * 100))

  4) 샘플 컬럼 토글:
    "샘플 포함" 체크박스 → tree['displaycolumns'] 동적 변경
    show_sample=True  → 모든 컬럼 표시
    show_sample=False → "샘플(1kg)" 컬럼만 제외

  5) 검색·필터:
    LOT 번호 검색 (부분 일치)
    상태 필터: 전체 / AVAIL / RSV(배정있음) / PARTIAL / PICKED / OUT

  6) 하단 산식 안내:
    "배정% = (RESERVED+PICKED+OUT kg) ÷ 일반톤백 총중량 × 100 (샘플 제외)"

  메인 쿼리:
    SELECT
        i.lot_no, i.sap_no,
        COUNT(CASE WHEN COALESCE(t.is_sample,0)=0 THEN 1 END) AS tot_tb,
        COUNT(CASE WHEN t.status='AVAILABLE' AND COALESCE(t.is_sample,0)=0 THEN 1 END) AS avail_tb,
        COALESCE((SELECT CAST(SUM(ap.qty_mt/0.5) AS INT)
                  FROM allocation_plan ap
                  WHERE ap.lot_no=i.lot_no AND ap.status='RESERVED'), 0) AS rsv_tb,
        COALESCE((SELECT SUM(ap.qty_mt)
                  FROM allocation_plan ap
                  WHERE ap.lot_no=i.lot_no AND ap.status='RESERVED'), 0.0) AS rsv_mt,
        COALESCE((SELECT GROUP_CONCAT(DISTINCT ap.sale_ref)
                  FROM allocation_plan ap
                  WHERE ap.lot_no=i.lot_no AND ap.status='RESERVED'), '') AS sale_refs,
        COUNT(CASE WHEN t.status='PICKED' AND COALESCE(t.is_sample,0)=0 THEN 1 END) AS pick_tb,
        COUNT(CASE WHEN t.status IN ('OUTBOUND','SOLD')
                    AND COALESCE(t.is_sample,0)=0 THEN 1 END) AS out_tb,
        MAX(CASE WHEN COALESCE(t.is_sample,0)=1 THEN t.status END) AS samp_status,
        COUNT(CASE WHEN COALESCE(t.is_sample,0)=1 THEN 1 END) AS samp_cnt
    FROM inventory i
    LEFT JOIN inventory_tonbag t ON t.lot_no=i.lot_no
    GROUP BY i.lot_no
    ORDER BY i.lot_no

  결합:
    main_app.py: AllocationLotOverviewMixin 상속 추가
    tabs/__init__.py: 모듈 export 추가

── FEATURE-H2 [P2] 단위 테스트 신규 ────────────────────────────────

  신규 파일: tests/test_allocation_lot_overview_mixin.py

  테스트 케이스 7개:
    1. LOT 상태 계산 — AVAILABLE
    2. LOT 상태 계산 — PARTIAL (일부 배정)
    3. LOT 상태 계산 — FULL_RESERVED
    4. LOT 상태 계산 — PICKED
    5. LOT 상태 계산 — OUTBOUND
    6. 배정 비율 계산 — 일반/샘플 분리
    7. 샘플 집계 4단계 검증 (0건/1건/2건+/불일치)

  실행:
    python -m pytest tests/test_allocation_lot_overview_mixin.py -v

── PHASE 1-H COMPLETE WHEN ──────────────────────────────────────────

  ✅ BUG-13: SALE REF 취소창 앞에 표시 + 빈값 경고
  ✅ BUG-14: 복귀 버튼 pack_forget → before= 재배치
  ✅ BUG-15: RESERVED UNION 집계 (LOT모드 + 톤백모드)
  ✅ BUG-16: 출고예정 할당 kg — tonbag_id NULL 분기
  ✅ BUG-17: 대시보드 판매배정 카드 3단 (행수/MT/LOT·톤백)
  ✅ allocation_lot_overview_mixin.py 신규 생성
  ✅ 샘플 집계 4단계 검증 + displaycolumns 토글
  ✅ 배정비율 산식 샘플 제외 적용
  ✅ tests/test_allocation_lot_overview_mixin.py 7케이스 통과
  ✅ main_app.py + tabs/__init__.py Mixin 결합


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[PHASE 1-I: 재고탭 필터·레이아웃·버튼 수정 — 2026-03-22 신규]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

── BUG-18 [P1] 재고 탭 필터 콤보 목록이 안 나오던 문제 ─────────────

  File: gui_app_modular/tabs/inventory_tab.py

  Problem:
    재고 새로고침 과정에서 DB로 채운 LOT/SAP/BL 등 목록이
    이후 _update_inv_filter_values(inventory) 가
    현재 그리드 데이터만 기준으로 다시 덮어쓰면서
    콤보 목록이 비거나 줄어들었음

  Fix:
    1) _update_inv_filter_values(): STATUS만 갱신 ("전체 (n)" 등)
       LOT/SAP/BL/CONTAINER/PRODUCT 목록은 건드리지 않음

    2) _populate_filter_dropdowns(): LOT/SAP/BL/CONTAINER/PRODUCT
       목록은 이 함수에서만 채움
       - DB DISTINCT 쿼리로 전체 목록 조회
       - 빈값/TRIM 처리로 목록 품질 정리
       - 호출 순서: 재고 조회 성공 후 맨 끝에서 호출

    3) 호출 순서 수정:
       기존: _update_inv_filter_values() → _populate_filter_dropdowns()
             (덮어쓰기 순서 문제)
       수정: _populate_filter_dropdowns() → _update_inv_filter_values()
             (STATUS만 마지막에 갱신)

  수정 코드 핵심:

    def _update_inv_filter_values(self, inventory) -> None:
        """STATUS 콤보만 갱신 — LOT/SAP/BL 목록은 건드리지 않음"""
        status_set = sorted({str(r.get('status','')) for r in inventory if r.get('status')})
        total = len(inventory)
        values = [f"전체 ({total})"] + status_set
        self._filter_status_combo['values'] = values
        # ★ LOT/SAP/BL/CONTAINER/PRODUCT 콤보는 여기서 갱신하지 않음

    def _populate_filter_dropdowns(self) -> None:
        """LOT/SAP/BL/CONTAINER/PRODUCT 콤보 목록 — DB DISTINCT 기준"""
        try:
            for col, combo in [
                ('lot_no',       self._filter_lot_combo),
                ('sap_no',       self._filter_sap_combo),
                ('bl_no',        self._filter_bl_combo),
                ('container_no', self._filter_container_combo),
                ('product',      self._filter_product_combo),
            ]:
                rows = self.engine.db.fetchall(
                    f"SELECT DISTINCT TRIM({col}) AS v FROM inventory "
                    f"WHERE {col} IS NOT NULL AND TRIM({col}) != '' "
                    f"ORDER BY {col}"
                )
                vals = ['전체'] + [r['v'] for r in (rows or []) if r.get('v')]
                combo['values'] = vals
        except Exception as e:
            logger.warning(f"[INV] 필터 목록 갱신 실패: {e}")

    # 재고 조회 성공 후 호출 순서:
    def _refresh_inventory(self) -> None:
        inventory = self.engine.get_inventory(...)
        self._fill_inventory_tree(inventory)
        self._populate_filter_dropdowns()      # ① LOT/SAP/BL 먼저
        self._update_inv_filter_values(inventory)  # ② STATUS만 마지막

── BUG-19 [P2] 필터줄 + 기간줄 레이아웃 개선 ───────────────────────

  Files: gui_app_modular/utils/tree_enhancements.py
         gui_app_modular/tabs/inventory_tab.py

  Problem:
    "업로드 2"(기간·달력·컨테이너 구분·초기화)가 필터 아래 별도 줄에 있어
    세로로 공간을 많이 차지하고, 기간 입력칸이 좁아 날짜가 잘림

  Fix (tree_enhancements.py — HeaderSortFilterRow):

    opt_row_side 파라미터 추가 ("below" / "right", 기본="below"):

    class HeaderSortFilterRow:
        def __init__(self, ..., opt_row_side: str = "below"):
            self._opt_row_side = opt_row_side
            ...

        def _build_layout(self):
            if self._opt_row_side == "right":
                # 한 줄: 왼쪽=필터 콤보, 오른쪽=기간·옵션
                filter_frame = ttk.Frame(self._container)
                filter_frame.pack(side=LEFT, fill=X, expand=YES)
                opt_frame = ttk.Frame(self._container)
                opt_frame.pack(side=RIGHT, fill=X)
                self._build_filter_widgets(filter_frame)
                self._build_option_widgets(opt_frame)
            else:
                # 기존: 위=필터, 아래=기간·옵션 (기본 동작 유지)
                self._build_filter_widgets(self._container)
                opt_row = ttk.Frame(self._container)
                opt_row.pack(fill=X)
                self._build_option_widgets(opt_row)

    기간 Entry 폭 확대:
      기존: width=10 (날짜 잘림)
      수정: width=14  (YYYY-MM-DD + 여유)
      padx=4 로 좌우 간격 조정

    필터 콤보 폭 자동 조정:
      기존: 고정 width
      수정: width = max(width // 5, 16)
            (창 크기에 비례, 최소 16자)

  Fix (inventory_tab.py):
    재고 탭에서 opt_row_side="right" 로 연결:

    self._filter_row = HeaderSortFilterRow(
        ...,
        opt_row_side="right",   # ← 기간줄을 필터 오른쪽에
    )

── BUG-20 [P2] 원스톱 입고 D/O 버튼 글자 잘림 ──────────────────────

  File: gui_app_modular/dialogs/onestop_inbound.py

  Problem:
    "📋 D/O 나중에" 버튼에 width=12만 줘서
    이모지 + 한글 조합에서 레이블이 잘림

  Fix:
    기존: ttk.Button(..., text="📋 D/O 나중에", width=12)
    수정: ttk.Button(..., text="📋 D/O 나중에", width=20)

  Note: 이모지는 일반 문자보다 2배 폭을 차지하므로
        한글+이모지 버튼은 width를 넉넉히 설정 필요
        유사 패턴 전수 점검:
          grep -n "width=[0-9]\+" gui_app_modular/dialogs/onestop_inbound.py |
          grep -v "^#" | head -30
        → width < 16 이고 이모지+한글 조합인 버튼 전부 width=20 이상으로 수정

── PHASE 1-I COMPLETE WHEN ──────────────────────────────────────────

  ✅ BUG-18: 재고 탭 필터 콤보 LOT/SAP/BL 목록 정상 표시
  ✅ BUG-18: _populate_filter_dropdowns() 호출 순서 수정
  ✅ BUG-18: DISTINCT + TRIM 처리로 목록 품질 정리
  ✅ BUG-19: HeaderSortFilterRow opt_row_side="right" 분기 추가
  ✅ BUG-19: 기간 Entry width=14, 필터 콤보 max(width//5, 16)
  ✅ BUG-19: 재고 탭 opt_row_side="right" 연결
  ✅ BUG-20: D/O 버튼 width=12 → width=20
  ✅ BUG-20: onestop_inbound 이모지+한글 버튼 전수 점검

  검증 방법:
    1) 재고 탭 → 필터 드롭다운 클릭 → LOT/SAP/BL 목록이 꽉 차는지 확인
    2) 재고 탭 → 기간 줄이 필터 오른쪽에 붙어 한 줄로 표시되는지 확인
    3) 원스톱 입고 → D/O 나중에 버튼 문구가 잘리지 않는지 확인

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[PHASE 1 CYCLE PROCESS]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Each full cycle:
  1. python -m pytest tests/ -q --tb=short  (record counts)
  2. Fix BUG-1 → BUG-8 in order
  3. Apply UI-1 → UI-5 in order
  4. Apply Phase 1-A (메뉴 단일화)
  5. Apply Phase 1-B (창 크기 저장)
  6. Apply Phase 1-C (창 크기 조절)
  7. Apply Phase 1-D (글씨/폭 반복 최적화 × 3회)
  8. Apply Phase 1-E (색상 밝기 개선 × 3회)
  9. python -m pytest tests/ -q → verify
  10. Repeat until all complete

── PHASE 1 COMPLETE WHEN ──────────────────────────────

  ✅ 406+ tests pass / 0 failures
  ✅ 0 silent exception handlers
  ✅ BUG-1~8 all fixed
  ✅ carrier_id passed to parse_bl() (BUG-2, BUG-3)
  ✅ MSC carrier 정확 감지 (BUG-3)
  ✅ PL LOT_SQM 7자리 정상 추출 (BUG-4)
  ✅ MSC D/O 좌표 파싱 (BUG-5)
  ✅ 메뉴 3파일 → registry 단일화 (Phase 1-A)
  ✅ 창 크기 저장/복원 정상 작동 (Phase 1-B)
  ✅ 모든 창 resizable (Phase 1-C)
  ✅ 글씨/폭 3회 이상 반복 최적화 (Phase 1-D)
  ✅ UI 전체 밝기 개선 완료 (Phase 1-E)
  ✅ Single theme (cosmo default, darkly optional)
  ✅ Sidebar navigation working
  ✅ Status badges in all tables


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[PHASE 1-G: LOT별 현황 뷰 + 샘플 표시 + Excel 내보내기 — 2026-03-22 신규]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

배경:
  현재 "판매배정 예약 현황" 창은 allocation_plan 행 단위로 표시
  → LOT별 통합 현황 (초기재고 / 배정수 / 피킹수 / 샘플 상태) 뷰 없음
  → 아래 3가지를 신규 추가

── FEATURE-1: LOT별 현황 팝업 — 판매배정 탭 "예약 현황" 버튼 연동 ──────────

  File: gui_app_modular/tabs/allocation_tab.py
  기존 btn_summary(예약 현황) 클릭 시 호출되는 함수에 추가

  추가 위치: _on_show_summary() 또는 _on_allocation_show_status() 함수 내
  (기존 창이 있으면 탭 추가, 없으면 별도 팝업)

  새 다이얼로그 클래스: LotStatusDialog
  File: gui_app_modular/dialogs/lot_status_dialog.py (신규 생성)

  class LotStatusDialog:
    """LOT별 통합 현황 — AVAILABLE / RESERVED / PICKED / OUTBOUND / 샘플"""

    COLUMNS = [
        ('lot_no',       'LOT NO',      120, 'center'),
        ('sap_no',       'SAP NO',       95, 'center'),
        ('total_tb',     '총톤백',        55, 'center'),
        ('avail_tb',     'AVAILABLE',    75, 'center'),
        ('reserved_tb',  'RESERVED',     85, 'center'),
        ('reserved_mt',  'RSV(MT)',       70, 'center'),
        ('picked_tb',    'PICKED',        65, 'center'),
        ('out_tb',       'OUTBOUND',      70, 'center'),
        ('sample_stat',  '샘플(1kg)',     80, 'center'),  # ← 샘플 인라인 컬럼
        ('rsv_pct',      '배정%',         55, 'center'),
        ('sale_refs',    'SALE REF',      80, 'center'),
        ('lot_status',   '상태',          80, 'center'),
    ]

    쿼리 (engine.db.fetchall):
      SELECT
          i.lot_no,
          i.sap_no,
          -- 일반 톤백 (샘플 제외)
          SUM(CASE WHEN COALESCE(t.is_sample,0)=0 THEN 1 ELSE 0 END) AS total_tb,
          SUM(CASE WHEN COALESCE(t.is_sample,0)=0 AND t.status='AVAILABLE'
              THEN 1 ELSE 0 END) AS avail_tb,
          SUM(CASE WHEN COALESCE(t.is_sample,0)=0 AND t.status='PICKED'
              THEN 1 ELSE 0 END) AS picked_tb,
          SUM(CASE WHEN COALESCE(t.is_sample,0)=0
              AND t.status IN ('OUTBOUND','SOLD') THEN 1 ELSE 0 END) AS out_tb,
          -- RESERVED: allocation_plan 기준 (LOT모드 tonbag_id=NULL 포함)
          COALESCE((SELECT SUM(ap.qty_mt/0.5)
              FROM allocation_plan ap
              WHERE ap.lot_no=i.lot_no AND ap.status='RESERVED'), 0) AS reserved_tb,
          COALESCE((SELECT SUM(ap.qty_mt)
              FROM allocation_plan ap
              WHERE ap.lot_no=i.lot_no AND ap.status='RESERVED'), 0) AS reserved_mt,
          COALESCE((SELECT GROUP_CONCAT(DISTINCT ap.sale_ref)
              FROM allocation_plan ap
              WHERE ap.lot_no=i.lot_no AND ap.status='RESERVED'), '') AS sale_refs,
          -- 샘플 (is_sample=1, tonbag_no='S00')
          MAX(CASE WHEN t.is_sample=1 THEN t.status ELSE NULL END) AS sample_status,
          SUM(CASE WHEN t.is_sample=1 THEN 1 ELSE 0 END) AS sample_cnt
      FROM inventory i
      LEFT JOIN inventory_tonbag t ON t.lot_no = i.lot_no
      GROUP BY i.lot_no
      ORDER BY i.lot_no

    LOT 상태 계산 (Python):
      def _calc_lot_status(row) -> str:
          if row['out_tb'] > 0 and row['out_tb'] >= row['total_tb']:
              return 'OUTBOUND'
          if row['picked_tb'] > 0:
              return 'PICKED'
          if row['reserved_tb'] > 0 and row['reserved_tb'] < row['total_tb']:
              return 'PARTIAL'
          if row['reserved_tb'] >= row['total_tb'] and row['total_tb'] > 0:
              return 'FULL_RSV'
          if row['reserved_tb'] > 0:
              return 'PARTIAL'
          return 'AVAILABLE'

    샘플 컬럼 표시:
      sample_stat = f"{row['sample_cnt']}개 {row['sample_status'] or '-'}"
      # 예: "1개 AVAILABLE" / "1개 RESERVED" / "0개 -"
      # 색상: AVAILABLE→초록, RESERVED→파랑, PICKED→주황

    하단 요약바:
      총 LOT: N개  |  미배정: N개  |  배정완료: N개  |  PARTIAL: N개
      총 샘플: N개  |  샘플 배정: N개

    버튼:
      [🔄 새로고침]  [🔍 LOT 검색]  [📥 Excel 내보내기]  [✕ 닫기]

  판매배정 탭에 버튼 추가:
    btn_lot_status = ttk.Button(
        btn_frame,
        text="📊 LOT별 현황",
        command=self._on_show_lot_status
    )
    btn_lot_status.pack(side=LEFT, padx=Spacing.XS)
    apply_tooltip(btn_lot_status, "LOT별 배정현황 — 초기재고/배정수/피킹/샘플 통합 조회")

    def _on_show_lot_status(self) -> None:
        from ..dialogs.lot_status_dialog import LotStatusDialog
        dlg = LotStatusDialog(self.root, self.engine)
        dlg.show()

── FEATURE-2: 샘플 배정 현황 — Allocation 파일 포함 정책 ────────────────────

  원칙:
    샘플(MIC9000 Sample / 0.001MT)은 고객 요청 기준으로 포함/제외 선택
    현재 파일에 이미 포함 가능 (파서가 is_sample=True로 자동 분류)

  Allocation 파일 내 샘플 행 형식:
    Product=MIC9000 Sample / QTY=0.001 / Lot No=동일 LOT / 나머지 동일

  파서 처리 (allocation_parser.py):
    is_sample_req = bool(_alloc_val(alloc, 'is_sample', False))
    # qty_mt < 0.01 이면 자동으로 is_sample=True (기존 로직 유지)

  LotStatusDialog에 샘플 포함/제외 토글 추가:
    ☑ 샘플 포함  (체크 시 샘플 행도 테이블에 표시)

── FEATURE-3: LOT별 현황 Excel 내보내기 ─────────────────────────────────────

  File: gui_app_modular/dialogs/lot_status_dialog.py 내 _export_excel() 메서드

  def _export_excel(self) -> None:
      import openpyxl
      from openpyxl.styles import (Font, PatternFill, Alignment,
                                   Border, Side)
      from openpyxl.utils import get_column_letter
      from tkinter import filedialog
      from datetime import datetime

      path = filedialog.asksaveasfilename(
          parent=self.dialog,
          title="LOT별 현황 Excel 저장",
          defaultextension=".xlsx",
          initialfile=f"LOT_Status_{datetime.now():%Y%m%d_%H%M}.xlsx",
          filetypes=[("Excel", "*.xlsx")]
      )
      if not path: return

      wb = openpyxl.Workbook()
      ws = wb.active; ws.title = "LOT별현황"

      # 헤더 스타일
      hdr_fill = PatternFill('solid', start_color='1F3864')
      hdr_font = Font(bold=True, color='FFFFFF', size=10, name='맑은 고딕')
      smp_fill = PatternFill('solid', start_color='FFF2CC')  # 샘플 컬럼 강조

      HEADERS = [
          ('LOT NO', 14), ('SAP NO', 13), ('총톤백', 7), ('AVAILABLE', 10),
          ('RESERVED(개)', 12), ('RESERVED(MT)', 12), ('PICKED', 8),
          ('OUTBOUND', 9), ('샘플수', 7), ('샘플상태', 10),
          ('배정%', 7), ('SALE REF', 10), ('LOT 상태', 11),
      ]

      for c, (h, w) in enumerate(HEADERS, 1):
          cell = ws.cell(row=1, column=c, value=h)
          cell.font = hdr_font
          # 샘플 컬럼 (9, 10번) 노란 배경
          cell.fill = smp_fill if c in (9, 10) else hdr_fill
          cell.alignment = Alignment(horizontal='center', vertical='center')
          ws.column_dimensions[get_column_letter(c)].width = w

      # 데이터 행
      for ri, row in enumerate(self._rows, 2):
          data = [
              row['lot_no'], row['sap_no'],
              row['total_tb'], row['avail_tb'],
              int(row['reserved_tb'] or 0),
              round(row['reserved_mt'] or 0, 3),
              row['picked_tb'], row['out_tb'],
              row['sample_cnt'],
              row['sample_status'] or '-',
              f"{int((row['reserved_tb'] or 0) / max(row['total_tb'],1) * 100)}%",
              row['sale_refs'] or '',
              self._calc_lot_status(row),
          ]
          bg = 'FFFFFF' if ri % 2 == 0 else 'F2F2F2'
          for c, v in enumerate(data, 1):
              cell = ws.cell(row=ri, column=c, value=v)
              cell.alignment = Alignment(horizontal='center', vertical='center')
              cell.fill = PatternFill('solid', start_color=bg)

      # 합계 행
      last = len(self._rows) + 2
      ws.cell(row=last, column=1, value='합계').font = Font(bold=True)
      ws.cell(row=last, column=3,
              value=f'=SUM(C2:C{last-1})').font = Font(bold=True)
      ws.cell(row=last, column=5,
              value=f'=SUM(E2:E{last-1})').font = Font(bold=True)
      ws.cell(row=last, column=6,
              value=f'=SUM(F2:F{last-1})').font = Font(bold=True)

      ws.freeze_panes = 'A2'
      wb.save(path)

      from ..utils.ui_constants import CustomMessageBox
      CustomMessageBox.showinfo(
          self.dialog, "저장 완료",
          f"✅ LOT별 현황 Excel 저장 완료\n{path}"
      )

── PHASE 1-G COMPLETE WHEN ──────────────────────────────────────────────

  ✅ lot_status_dialog.py 신규 생성
  ✅ 판매배정 탭에 "📊 LOT별 현황" 버튼 추가
  ✅ LOT별 현황 테이블: 총톤백/AVAILABLE/RESERVED/PICKED/OUTBOUND + 샘플 인라인
  ✅ 샘플 컬럼: 개수 + 상태 (AVAILABLE/RESERVED/PICKED) 색상 표시
  ✅ Excel 내보내기: 샘플/일반 구분 컬럼 포함
  ✅ 하단 요약: 총 LOT / 미배정 / 배정완료 / PARTIAL / 샘플 배정 수

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[PHASE 2: NICEGUI MIGRATION]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Start immediately after Phase 1 is complete.
DO NOT modify engine files. Only create new sqm_web/ folder.

── WIDGET MAPPING (apply automatically) ───────────────

  ttk.Frame/tk.Frame  → with ui.card() / ui.column() / ui.row()
  ttk.Label           → ui.label()
  ttk.Button          → ui.button()
  ttk.Entry           → ui.input()
  ttk.Combobox        → ui.select()
  ttk.Treeview        → ui.table()
  ttk.Notebook        → with ui.tabs()
  StringVar           → plain variable + @ui.refreshable
  after(ms, fn)       → ui.timer(ms/1000, fn)
  messagebox.showinfo → ui.notify()
  messagebox.showerror→ ui.notify(type='negative')
  Toplevel dialog     → with ui.dialog() as d: d.open()
  filedialog          → ui.upload()
  winfo_exists()      → remove (not needed)
  mainloop()          → ui.run()

── STATUS BADGE COLORS ────────────────────────────────

  AVAILABLE → ui.badge('AVAILABLE', color='green')
  RESERVED  → ui.badge('RESERVED',  color='blue')
  PICKED    → ui.badge('PICKED',    color='amber')
  OUTBOUND  → ui.badge('OUTBOUND',  color='grey')
  RETURN    → ui.badge('RETURN',    color='orange')

── ASYNC PATTERN (use for ALL engine calls) ───────────

  import asyncio
  from concurrent.futures import ThreadPoolExecutor
  _executor = ThreadPoolExecutor(max_workers=4)

  async def db_query(fn, *args):
      loop = asyncio.get_event_loop()
      return await loop.run_in_executor(_executor, fn, *args)

── DIRECTORY STRUCTURE TO CREATE ──────────────────────

  sqm_web/
    main.py
    bridge/
      engine_bridge.py       ← create first
    pages/
      inventory_page.py
      allocation_page.py
      picking_page.py
      outbound_page.py
      return_page.py
      dashboard_page.py
      inbound_dialog.py
    components/
      sidebar.py
      status_badge.py
      kpi_cards.py
      data_table.py

── ENGINE BRIDGE ───────────────────────────────────────

  # sqm_web/bridge/engine_bridge.py
  import sys, asyncio
  from concurrent.futures import ThreadPoolExecutor
  from pathlib import Path
  sys.path.insert(0, str(Path(__file__).parent.parent.parent))
  from config import DB_PATH
  from engine_modules.sqm_engine import SQMEngine

  _executor = ThreadPoolExecutor(max_workers=4)
  _engine = None

  def get_engine():
      global _engine
      if _engine is None:
          _engine = SQMEngine()
      return _engine

  async def async_query(fn, *args):
      loop = asyncio.get_event_loop()
      return await loop.run_in_executor(_executor, lambda: fn(*args))

  async def get_inventory():
      e = get_engine()
      return await async_query(e.db.fetchall,
          "SELECT lot_no, sap_no, bl_no, product, status, "
          "current_weight, net_weight, container_no, mxbg_pallet, "
          "arrival_date FROM inventory ORDER BY created_at DESC")

── MAIN ENTRY POINT ───────────────────────────────────

  # sqm_web/main.py
  from nicegui import ui
  from pages.inventory_page import inventory_page
  from pages.allocation_page import allocation_page
  from components.sidebar import create_sidebar

  @ui.page('/')
  async def index():
      ui.dark_mode().enable()
      with ui.row().classes('w-full h-screen no-wrap'):
          create_sidebar()
          with ui.column().classes('flex-1 overflow-auto p-4'):
              await inventory_page()

  ui.run(title='SQM v8.1.4', port=8080, reload=False,
         dark=True, favicon='⚡')

── UI DESIGN STANDARD — WORLD CLASS QUALITY ───────────

  Reference companies (study these designs carefully):
    Linear       → spacing, sidebar, table row density
    Notion       → typography, section padding, hierarchy
    Retool       → data table, filter bar, action buttons
    Vercel       → dark theme, monospace, clean layout
    Stripe       → card layout, status badges, micro-spacing
    GitHub       → code/data density, muted colors, icons
    Figma        → sidebar icon+label, panel proportions
    Tailwind UI  → component consistency, border radius

  LAYOUT & SPACING:
    - Sidebar width: exactly 64px (icon) or 200px (icon+label)
    - Content padding: 24px outer, 16px inner sections
    - Card padding: 16px all sides
    - Gap between cards: 12px
    - Table row height: 44px
    - Table cell padding: 10px vertical, 12px horizontal
    - Button padding: 8px vertical, 16px horizontal
    - Input height: 36px
    - Dialog min-width: 600px, max-width: 900px

  TYPOGRAPHY:
    - Korean font: 'Pretendard' or '맑은 고딕'
    - Base font size: 14px
    - Table data: 13px
    - Label/header: 12px, font-weight 600
    - Title: 18px, font-weight 700

  COLORS (light theme — cosmo 기준):
    - Background primary:   #ffffff
    - Background secondary: #f8fafc
    - Background card:      #ffffff
    - Border:               #e2e8f0
    - Text primary:         #0f172a
    - Text muted:           #64748b
    - Accent:               #3b82f6
    - Success:              #10b981
    - Warning:              #f59e0b
    - Danger:               #ef4444

  ITERATION RULE:
    Do NOT stop at first attempt.
    Render → review → improve → repeat.
    Minimum 3 iterations per page.
    Ask yourself each iteration:
      "Would a Linear or Stripe designer approve this?"
    If NO → iterate again.

── PHASE 2 EXECUTION STEPS ────────────────────────────

  STEP-1: pip install nicegui plotly --break-system-packages -q
  STEP-2: mkdir -p sqm_web/pages sqm_web/components sqm_web/bridge
  STEP-3: Create engine_bridge.py → verify DB connection
  STEP-4: Create components/ (sidebar, badge, kpi_cards, data_table)
  STEP-5: Create inventory_page.py → test with main.py
  STEP-6: Create remaining pages one by one
  STEP-7: Add all routes to main.py
  STEP-8: python -m pytest tests/ -q → engine tests must pass
  STEP-9: python sqm_web/main.py → verify browser opens

── PHASE 2 COMPLETE WHEN ──────────────────────────────

  ✅ sqm_web/main.py runs without error
  ✅ Browser opens at http://localhost:8080
  ✅ Inventory table shows real DB data with status badges
  ✅ All pages reachable via sidebar
  ✅ Engine tests still passing (406+)
  ✅ UI passes world-class design check
  ✅ Minimum 3 iterations per page completed

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[CYCLE REPORT FORMAT — AFTER EVERY STEP]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ── PHASE N / STEP N ──────────────────────
  Tests:   X passed / Y failed
  Done:    [BUG-3] MSC carrier 감지 수정 (score: MSC 7 > MAERSK 0)
           [BUG-4] PL LOT_SQM 7자리 수정
           [1-B]   window_config.json 저장/복원 구현
           [1-D]   UI 폰트/폭 3회 반복 최적화
           [1-E]   테마 cosmo 적용, 배지 밝은 색상
  Skipped: none
  Next:    [1-A] menu_registry 단일화
  ─────────────────────────────────────────

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[NEVER DO THESE]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  - Never delete sub_lt column
  - Never change DB schema without migration
  - Never write partial commits
  - Never use bare except: pass
  - Never break passing engine tests
  - Never modify test files
  - Never write STATUS_SOLD in new code
  - Never touch: engine_modules/ features/ parsers/ tests/ config.py
  - Never delete: data/sqm_inventory.db
  - Never wait more than 60 seconds for user input
  - Never hardcode window size without checking window_config.json first
  - Never set resizable(False) on any window or dialog

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BEGIN NOW.

PHASE 0 first command:
  python -m pytest tests/ -v --tb=short 2>&1 | tee /tmp/audit_test.log

Then run AUDIT-0 through AUDIT-10 in order.
When Phase 0 complete → start Phase 1 automatically.
  Phase 1 order: BUG-1~8 → UI-1~5 → 1-A → 1-B → 1-C → 1-D → 1-E
When Phase 1 complete → start Phase 2 automatically.
Do not stop. Do not ask. Auto-decide everything.
Report after every phase and every step.
```

---

## 기동님 실행 방법 (3단계)

```bash
# 1. SQM 프로젝트 폴더로 이동
cd C:\sqm

# 2. Git 백업 (필수!)
git add -A && git commit -m "backup before claude auto-run"

# 3. Claude Code 실행
claude --dangerously-skip-permissions \
  --system-prompt-file Claude_Code_SQM_MASTER.md

#    → 자리 비우기 (6~10시간)
#    → 돌아오면 결과 확인
```

## 이번 실행에서 추가된 작업

| 우선순위 | 작업 | 설명 |
|---|---|---|
| P1 | BUG-3 MSC carrier 감지 수정 | 동점 → MAERSK 오감지 버그 |
| P1 | BUG-4 PL LOT_SQM 7자리 | 6→6,7자리로 수정 |
| P1 | BUG-5 MSC D/O 좌표 파서 | Gemini 폴백 없이 직접 파싱 |
| P1 | BUG-9 AL-06 SALE_REF_CONFLICT | 같은 파일 내 동일 SALE REF 허용 |
| P1 | BUG-10 총괄재고 판매배정 카운트 0 | LOT모드 RESERVED 카운트 오류 수정 |
| P1 | BUG-11 SALE REF 입력창 글씨 안보임 | askstring → 커스텀 다이얼로그 교체 |
| P1 | BUG-12 대시보드 판매배정 0개 | allocation_plan 기준 조회로 수정 |
| P2 | Phase 1-A 메뉴 단일화 | 3파일 → menu_registry 단일 소스 |
| P2 | Phase 1-B 창 크기 저장 | 재시작 시 마지막 크기 복원 |
| P2 | Phase 1-C 창 조절 가능 | 모든 창/다이얼로그 resizable=True |
| P2 | Phase 1-D 글씨/폭 최적화 | 반복 3회 이상 검증 |
| P2 | Phase 1-E 색상 밝기 개선 | cosmo 테마 + 밝은 색상 팔레트 |
| P2 | Phase 1-F 대시보드 UI 개선 | 워크플로 배지 삭제 + 카드 3단 표시 |
| P2 | Phase 1-G LOT별 현황 뷰 | 예약현황 팝업 + 샘플 인라인 + Excel 내보내기 |
| P1 | BUG-13 SALE REF 취소창 | askstring 모달 안정화 (lift+focus_force) |
| P1 | BUG-14 복귀 버튼 레이아웃 | pack_forget → before= 재배치 |
| P1 | BUG-15 RESERVED UNION 집계 | LOT모드+톤백모드 UNION |
| P1 | BUG-16 출고예정 할당 kg | tonbag_id NULL → qty_mt×1000 분기 |
| P2 | BUG-17 대시보드 판매배정 카드 | 3단 표시 + 비연결 톤백 보완 |
| P2 | Phase 1-H allocation_lot_overview | 샘플 4단계·displaycolumns·배정비율 |
| P1 | BUG-18 재고탭 필터 콤보 목록 | _populate_filter_dropdowns 호출순서 수정 |
| P2 | BUG-19 필터+기간줄 레이아웃 | opt_row_side="right" + Entry width=14 |
| P2 | BUG-20 D/O 버튼 글자 잘림 | width=12 → width=20 |
| P1 | BUG-13 출고확정 sold_table 미연결 | 스캔→OUTBOUND 시 sold_table 자동 INSERT |
| P1 | BUG-14 picking_table 연결 누락 | sales_order_no + outbound_id 연결 |
| P2 | Phase 1-H 피킹 파서 이슈 3개 | 자재코드 config 분리 + 샘플감지 + 컨테이너수 |
| P2 | Phase 1-G LOT별 현황 뷰 | 판매배정 탭 팝업 + 샘플 인라인 + Excel |

## 예상 결과

| 단계 | 결과 | 예상 시간 |
|---|---|---|
| Phase 0 | 감사 완료 + P1 수정 | 1~2시간 |
| Phase 1 | 버그 수정 + UI 전면 개선 | 3~4시간 |
| Phase 2 | NiceGUI 브라우저 앱 | 4~6시간 |
| 전체 완료 | 모든 기능 + 밝은 UI | 8~12시간 |

## 실행 후 확인

```bash
# Phase 1 결과
python -m pytest tests/ -q          # 406개 전부 통과

# 창 크기 저장 확인
cat gui_app_modular/window_config.json

# Phase 2 결과
python sqm_web/main.py              # 브라우저 자동 열림
# http://localhost:8080 에서 SQM NiceGUI 확인
```
