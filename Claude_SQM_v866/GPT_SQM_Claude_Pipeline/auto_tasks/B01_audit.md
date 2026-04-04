Read COMMON_RULES.md and follow it strictly.

BATCH ID: B01
PURPOSE:
Audit the codebase without applying risky business changes.

DO NOT FIX LARGE THINGS YET.
This batch is primarily discovery + reporting.

TASKS:
1. Search and report all status write-paths.
2. Search and report:
   - except: pass
   - except Exception: pass
   - except Exception: continue
3. Search and report potential SOLD write-paths.
4. Search and report .after( calls across GUI modules.
5. Search and report likely N+1 patterns:
   - DB execute/fetch inside loops
6. Search and report functions longer than 100 lines.
7. Produce these ranked lists:
   - Top 20 risk files
   - Top 20 risk functions
   - Top 10 integrity-risk areas
8. Create a structured audit report:
   - system flow understanding
   - symptom / direct cause / structural cause
   - SAFE ZONE / DANGER ZONE
   - recommended P0 / P1 / P2 targets

FILES TO INSPECT FIRST:
- engine_modules/inventory_modular/outbound_mixin.py
- gui_app_modular/handlers/outbound_handlers.py
- gui_app_modular/dialogs/onestop_inbound.py
- gui_app_modular/mixins/advanced_dialogs_mixin.py
- engine_modules/database.py
- engine_modules/inventory_modular/query_mixin.py
- gui_app_modular/main_app.py
- gui_app_modular/tabs/dashboard_tab.py
- features/ai/gemini_parser.py

TESTS TO RUN:
- no major code modification required
- py_compile only if any tiny helper/report script is created

SUCCESS CRITERIA:
- reports/claude_runs/B01/audit_report.md created
- risk lists created
- no uncontrolled code changes

WRITE OR UPDATE:
- reports/claude_runs/B01/audit_report.md
- reports/claude_runs/B01/summary.md
- reports/claude_runs/B01/test_results.txt
- reports/claude_runs/B01/status.txt
