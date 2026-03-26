# SQM v8.1.3 — Claude Code 통합 자동 개선 프롬프트
# 작성: Ruby (2026-03-20)
# 내용: 파싱 안정화 + UI 전면 개선 통합본
# 사용법: Claude Code 실행 → 아래 ``` 안 전체 복사 붙여넣기 → Enter

---

```
You are a senior Python architect and UI/UX engineer.

Project: SQM v8.1.3 — LOT-based tonbag logistics system
         Lithium carbonate warehouse management (Gwangyang, Korea)
Tech:    Python 3.12 / tkinter / ttkbootstrap / SQLite / pytest

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[SYSTEM OVERVIEW]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Core workflow:
  Inbound → Inventory → Allocation(Reserve) → Picking → Outbound → Return → Move

Key files:
  run_bootstrap.py                                    (235 lines)
  gui_app_modular/main_app.py                         (main window)
  gui_app_modular/utils/ui_constants.py               (1,186 silent fails!)
  gui_app_modular/utils/split_panel.py                (detail panel)
  gui_app_modular/tabs/inventory_tab.py               (main table)
  gui_app_modular/tabs/outbound_scheduled_tab.py
  gui_app_modular/tabs/tonbag_tab.py
  gui_app_modular/dialogs/onestop_inbound.py          (3,520 lines)
  gui_app_modular/dialogs/onestop_outbound.py         (2,068 lines)
  gui_app_modular/dialogs/allocation_dialog.py        (1,394 lines)
  engine_modules/inventory_modular/inbound_mixin.py   (590 lines)
  engine_modules/inventory_modular/outbound_mixin.py  (3,646 lines)
  engine_modules/inventory_modular/return_mixin.py    (892 lines)
  features/parsers/sales_order_engine.py              (1,059 lines)
  features/parsers/picking_engine.py                  (314 lines)
  parsers/document_parser_modular/bl_mixin.py         (827 lines)
  features/parsers/onestop_inbound_candidate_patch.py (carrier_id bug)
  config.py                                           (default theme)
  engine_modules/constants.py                         (status values)
  tests/samples/                                      (7 PDFs embedded)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[PART 1: DATA INTEGRITY — NEVER VIOLATE]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. HIERARCHY: BL_NO > LOT_NO > TONBAG_NO (sub_lt)
   - 1 LOT = N tonbags (500kg or 1000kg) + 1 sample (1kg)
   - Sample: sub_lt=0, tonbag_no='S00', is_sample=1
   - Sample must NEVER be allocated, picked, or sold

2. WEIGHT LAW: initial_weight == current_weight + picked_weight (±1.0kg)

3. STATUS FLOW (one-direction only):
   AVAILABLE → RESERVED → PICKED → OUTBOUND
   OUTBOUND → RETURN → AVAILABLE (return flow)
   STATUS_SOLD = DEPRECATED (read-only backward compat only)
   All new writes must use STATUS_OUTBOUND

4. STOCK FORMULA: CURRENT = AVAILABLE + RESERVED + PICKED + RETURN

5. HARD STOP (must raise RuntimeError, never silent):
   - LOT_NO missing / net_weight == 0 / tonbag count mismatch
   - Sample in allocation/picking / status reversal
   - Weight law violated > ±1.0kg / partial commit

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[PART 2: KNOWN BUGS — FIX IN ORDER]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BUG-1 [P1] Failing test:
  tests/test_v660_new_methods.py::TestCreateDialogSplit::test_create_dialog_is_short
  → Find root cause and fix. Do not modify test file.

BUG-2 [P1] carrier_id not passed to parse_bl():
  File: features/parsers/onestop_inbound_candidate_patch.py
  Problem: selected_carrier_id extracted but NOT passed to parser.parse_bl()
  Fix:
    bl_result = parser.parse_bl(
        file_path,
        gemini_hint=final_hint,
        bl_format=bl_format,
        carrier_id=selected_carrier_id,  # ADD THIS
    )

BUG-3 [P2] voyage field mismatch:
  File: parsers/document_parser_modular/bl_mixin.py
  Problem: writes result.voyage_no but BLData field is result.voyage
  Fix: result.voyage_no = ... → result.voyage = ...

BUG-4 [P2] STATUS_SOLD written in new code:
  Search: grep -rn "= 'SOLD'" engine_modules/ --include="*.py"
  Fix: Replace write paths with STATUS_OUTBOUND (keep reads for compat)

BUG-5 [P3] bl_mixin.py 15+ unused legacy functions:
  _extract_by_waybill_line, _extract_by_keyword_anchor,
  _extract_by_carrier_rule, _extract_bl_extra_fields,
  _extract_by_scac_pattern (+ 10 more)
  Fix: grep to confirm unused → remove → 827 lines → ~300 lines

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[PART 3: UI IMPROVEMENTS — IN ORDER]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Design reference: Linear + Retool + Notion (professional dark internal tool)

UI-1 [P1 CRITICAL] Fix 1,186 silent failures:
  Search: grep -rn "except.*pass\|except Exception.*pass" gui_app_modular/
  Fix every one:
    except Exception as e:
        logger.warning(f"[UI] {context}: {e}")
  Rule: user must see every error. Never silent.
  Priority files: gui_app_modular/utils/ui_constants.py

UI-2 [P1] Theme unification:
  Target: single theme 'darkly' (dark professional)
  - config.py: default theme = 'darkly'
  - Remove all hardcoded colors: #333, white, black, gray
  - Use only ttkbootstrap CSS variables
  - All dialogs must inherit theme from root

UI-3 [P2] Sidebar navigation (replace 8 tabs):
  Current: 8 horizontal tabs (confusing, Korean/English mixed)
  Target: left sidebar 60px wide, icon + label:
    📦 재고    → inventory (AVAILABLE)
    📋 배정    → allocation (RESERVED)
    🚛 피킹    → picking (PICKED)
    ✅ 출고    → outbound (OUTBOUND)
    📊 통계    → dashboard
    📝 로그    → log
    📷 스캔    → scan
  Implementation:
    - Sidebar buttons highlight active
    - Notebook hidden (sidebar drives navigation)
    - Remove 총괄재고 tab (merge into 재고)

UI-4 [P2] Status badge pills in all tables:
  Current: plain text status column
  Target: colored pill badges:
    AVAILABLE → green  (#EAF3DE / #3B6D11)
    RESERVED  → blue   (#E6F1FB / #185FA5)
    PICKED    → amber  (#FAEEDA / #633806)
    OUTBOUND  → gray   (#F1EFE8 / #5F5E5A)
    RETURN    → coral  (#FAECE7 / #993C1D)
  Apply to: inventory_tab, outbound_scheduled_tab, tonbag_tab

UI-5 [P2] Detail panel behavior:
  - Default: collapsed (start_collapsed=True)
  - Already done in split_panel.py — verify all 3 tabs use it
  - Auto-expand on row select (already in _on_inv_selection_change)
  - Verify outbound_scheduled_tab and tonbag_tab also auto-expand

UI-6 [P3] Table improvements:
  - Bold column headers with subtle background
  - Zebra striping: alternating row color (2% opacity)
  - Row hover highlight effect
  - Sortable columns: ▲▼ arrow in header
  - Empty state: centered Korean guidance message

UI-7 [P3] Dialog standards:
  - Minimum width: 600px, centered on screen
  - Progress bars: percentage text overlay
  - Errors: red banner at top (not popup)
  - Success: green banner, auto-dismiss 3s
  - Buttons: [취소] [확인] always bottom-right
  - Parsing failure: open ParseResultEditor dialog

UI-8 [P3] Typography:
  - Korean font: 맑은 고딕, minimum 10pt
  - Consistent padding: 8px inner, 12px between sections
  - Button labels: icon + Korean (example: "📥 입고")

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[ITERATION PROCESS — REPEAT UNTIL DONE]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Each cycle:

  STEP 1: python -m pytest tests/ -q --tb=short
          Record pass/fail. Must never decrease pass count.

  STEP 2: Fix bugs (Part 2) in BUG-1 → BUG-5 order
          Re-run pytest after each fix.

  STEP 3: Fix UI (Part 3) in UI-1 → UI-8 order
          UI-1 (silent fails) MUST come before any visual changes.
          Re-run pytest after each change.

  STEP 4: python -m pytest tests/test_bl_parsing.py tests/test_4doc_parsing.py -v
          All 22 parsing tests must pass.

  STEP 5: Repeat from STEP 1.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[NEVER DO THESE]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- Never delete sub_lt column
- Never change DB schema without migration
- Never write partial commits
- Never use bare except: pass
- Never break passing tests
- Never modify test files artificially
- Never write STATUS_SOLD in new code
- Never hardcode colors

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[CYCLE REPORT FORMAT]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  CYCLE N
  Tests: X passed / Y failed
  Fixed:
    [BUG-2] carrier_id added to parse_bl() call
    [UI-1] 47 silent fails → logger.warning
    [UI-4] status badges added to inventory_tab
  Remaining: BUG-3, UI-3, UI-6
  Next: voyage field fix (BUG-3)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[FINAL GOALS — SQM v8.1.4]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STABILITY:
  ✅ 406+ tests pass / 0 failures
  ✅ Zero silent exception handlers
  ✅ No partial commits

PARSING:
  ✅ Maersk BL 7/7 fields correct
  ✅ MSC BL 7/7 fields correct
  ✅ carrier_id passed through full chain

UI:
  ✅ Single dark theme (darkly)
  ✅ Sidebar navigation (7 items)
  ✅ Status badge pills in all tables
  ✅ Detail panel: collapsed by default
  ✅ Empty states: helpful messages
  ✅ Dialogs: consistent + proper errors

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

BEGIN NOW.

First command:
  python -m pytest tests/ -q --tb=short

Then fix BUG-1, then BUG-2, then UI-1.
Do not stop until all goals achieved.
Report after every cycle.
```

---

## 현재 상태 (2026-03-20)

| 항목 | 현황 | 목표 |
|---|---|---|
| pytest | 405 passed / 1 failed | 406 passed / 0 failed |
| carrier_id 전달 | ❌ BUG-2 | ✅ |
| voyage 필드 | ❌ BUG-3 | ✅ |
| UI silent fail | ❌ 1,186개 | ✅ 0개 |
| 테마 | ❌ 혼재 | ✅ darkly 통일 |
| 사이드바 | ❌ 탭 8개 | ✅ 사이드바 7개 |
| 상태 배지 | ❌ 플레인 텍스트 | ✅ 컬러 배지 |

## Claude Code 사용법

```bash
cd C:\sqm          # SQM 프로젝트 폴더
claude             # Claude Code 실행
# 위 프롬프트 전체 붙여넣기 → Enter → 자리 비우기
```
