# Claude Code 최종 실행 프롬프트 v1

작성일시: 2026-04-02 21:38 (Asia/Seoul)  
인코딩: UTF-8

---

## 개요

이 문서는 `engine_modules/inventory_modular/outbound_mixin.py` 파일만을 대상으로 하는 **보수적 1차 리팩토링 실행 프롬프트**입니다.

핵심 목표는 다음과 같습니다.

- 비즈니스 정책 변경 금지
- DB 스키마 변경 금지
- 아키텍처 재설계 금지
- 로직 유지형 helper 분해
- `SOLD` / `OUTBOUND` 표현 정리
- 핵심 상태 전이 / 트랜잭션 / 예외 가시성 강화

---

## Claude Code 최종 실행 프롬프트 v1

```text
You are a world-class senior Python architect, debugging expert, and conservative refactoring specialist.

Project context:
This is a production-sensitive logistics / inventory / outbound system.
Operational stability, transaction safety, data integrity, and safe incremental refactoring are more important than aggressive cleanup or elegant redesign.

Target file only:
engine_modules/inventory_modular/outbound_mixin.py

Primary mission:
Apply a minimal-safe first-pass refactor to outbound_mixin.py only.

Core goal:
Do NOT redesign business logic.
Do NOT change schema.
Do NOT rewrite architecture.
Only make the file safer to maintain by:
1) extracting local private helpers,
2) clarifying critical state / transaction paths,
3) cleaning up SOLD vs OUTBOUND wording,
4) strengthening logging / exception visibility around critical write paths.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[CRITICAL FILE CONTEXT]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This file is one of the highest-risk files in the project.
It contains dense outbound domain logic and mixes:
- state transition logic
- DB update logic
- validation logic
- business rules
- reservation/execution/confirmation orchestration
- audit / movement / downstream trace writes

The project state-flow baseline is:

AVAILABLE → RESERVED → PICKED → OUTBOUND

SOLD is deprecated / legacy compatibility wording and should not be reintroduced as the primary current write-state wording.

LOT-mode reservation semantics must remain intact.
Do not redesign the meaning of:
- allocation_plan
- sold_table
- picking_table
- lot-mode reservation
- approval-required reservation paths

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[SCOPE]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Modify only:
engine_modules/inventory_modular/outbound_mixin.py

Do not modify other files unless absolutely required for:
- import safety
- syntax safety
- minimal logging/type import completion

If any cross-file change seems required beyond that, STOP.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[PRIMARY TARGET FUNCTIONS]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Refactor these three functions only in this pass:

1) confirm_outbound()
2) execute_reserved()
3) reserve_from_allocation()

Important:
For domain understanding, recognize the business flow:
reserve_from_allocation → execute_reserved → confirm_outbound

But for implementation safety, you may refactor in this order:
1. confirm_outbound()
2. execute_reserved()
3. reserve_from_allocation()

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[ALLOWED CHANGES]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Allowed:
- local private helper extraction inside outbound_mixin.py
- docstring cleanup
- comment cleanup
- result-message wording cleanup
- same-file repeated snippet extraction
- clearer separation between critical writes and auxiliary writes
- stronger context-rich logging
- conservative exception severity clarification
- readability improvements that do not change behavior

Examples of allowed helper extraction:
- query loading helpers
- validation helpers
- state transition helpers
- payload builder helpers
- audit/movement wrapper helpers
- result builder helpers

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[NOT ALLOWED]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Do NOT do any of the following:

- no DB schema change
- no migration change
- no table/column meaning change
- no business policy rewrite
- no LOT-mode redesign
- no TONBAG-mode redesign
- no approval policy rewrite
- no sample policy rewrite
- no sold_table semantic rewrite
- no picking_table semantic rewrite
- no report/export flow rewrite
- no transaction architecture redesign
- no cross-file interface change
- no public method signature change
- no new state-machine framework
- no service/repository architecture rewrite
- no broad “cleanup everything” edits

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[STATE RULES]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Use OUTBOUND as the primary current write-state wording.

Treat SOLD only as:
- deprecated
- legacy wording
- backward compatibility read-path terminology

Do not remove SOLD compatibility reads if they already exist.
Do not create new SOLD-primary write paths.
Do not rename project-wide states outside this file.

Allowed:
- update docstrings/comments/messages so they reflect OUTBOUND as the active write-state
- add a short compatibility note where SOLD still appears

Examples:
Bad:
- “PICKED → SOLD” as the primary current wording

Good:
- “PICKED → OUTBOUND (SOLD is legacy compatibility wording)”

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[TRANSACTION / DB SAFETY RULES]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Preserve existing transaction boundaries unless a tiny local adjustment is absolutely required for correctness.
Prefer keeping existing:
with self.db.transaction("IMMEDIATE")

Do not redesign transaction architecture.

Within code structure, make the following distinction clearer:

Critical writes:
- inventory_tonbag state transition
- inventory weight/current/picked updates
- allocation_plan core status updates

Auxiliary writes:
- stock_movement
- audit_log
- picking_table
- sold_table

Important:
Do NOT automatically downgrade sold_table or picking_table failures to harmless warnings.
Their operational importance may be high.
If current behavior must be preserved, keep behavior but add:
- stronger logging
- explicit NOTE/TODO comments where policy ambiguity remains

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[EXCEPTION HANDLING RULES]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Critical failures must not fail open.

Do not silently continue after:
- invalid transition
- duplicate outbound safety failure
- inventory weight update failure
- core state update failure
- allocation_plan core status failure

Broad rule:
If a failure can create partial commit risk or false operational truth, it should hard-stop or be clearly escalated.

Warning-only is acceptable only for clearly auxiliary behavior, such as:
- audit logging
- optional metadata
- non-critical note formatting
- compatibility-side trace writing
and only when behavior preservation requires it

When preserving legacy behavior for ambiguous cases, do both:
1) keep current behavior
2) add explicit NOTE/TODO with context

All warning/error logs should be context-rich where possible, including:
- action name
- line_no (if applicable)
- lot_no
- tonbag_id or tonbag_uid
- plan_id
- sale_ref
- current_status
- target_status
- error details

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[FUNCTION-SPECIFIC INSTRUCTIONS]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

──────────────────────────────────────
A. confirm_outbound()
──────────────────────────────────────

Goal:
Refactor confirm_outbound() into a clear outbound-confirm orchestration flow.

Target structure:

def confirm_outbound(...):
    now = datetime.now().strftime(DATETIME_FORMAT)

    tonbags = self._co_load_target_tonbags(...)
    self._co_validate_confirm_scope(tonbags, force_all=force_all)
    self._co_guard_against_double_outbound(tonbags)
    self._co_validate_customer_sale_ref_consistency(tonbags)

    with self.db.transaction("IMMEDIATE"):
        touched_lots = self._co_mark_tonbags_outbound(tonbags, now)
        self._co_insert_sold_rows(tonbags, now)
        self._co_insert_outbound_movements(tonbags, now)
        self._co_recalc_lot_statuses(touched_lots)

    self._co_run_post_checks(touched_lots)
    return self._co_build_confirm_result(tonbags, touched_lots)

Candidate helper names:
- _co_load_target_tonbags
- _co_validate_confirm_scope
- _co_guard_against_double_outbound
- _co_validate_customer_sale_ref_consistency
- _co_mark_tonbags_outbound
- _co_insert_sold_rows
- _co_insert_outbound_movements
- _co_recalc_lot_statuses
- _co_run_post_checks
- _co_build_confirm_result

Additional rules:
- use OUTBOUND wording in docstrings/comments/result messages
- do not let double-outbound guard fail open
- if sold_table failure policy is ambiguous, preserve behavior conservatively but leave strong logging and an explicit NOTE/TODO

──────────────────────────────────────
B. execute_reserved()
──────────────────────────────────────

Goal:
Refactor execute_reserved() into a clear reservation-execution orchestration flow.

Target structure:

def execute_reserved(...):
    now = datetime.now().strftime(DATETIME_FORMAT)

    plans = self._er_load_reserved_plans(...)
    self._er_warn_stale_plans(plans)

    executed_count = 0
    skipped_count = 0
    touched_lots = set()

    with self.db.transaction("IMMEDIATE"):
        for plan in plans:
            ctx = self._er_build_execution_context(plan)
            self._er_validate_reserved_target(ctx)
            self._er_apply_pick_transition(ctx, now)
            self._er_update_inventory_pick_weights(ctx)
            self._er_mark_plan_executed(ctx, now)
            self._er_insert_picking_row(ctx, now)
            self._er_record_pick_movement(ctx, now)

            if ctx.get("lot_no"):
                touched_lots.add(str(ctx["lot_no"]))
            executed_count += 1

    self._er_finalize_lot_status_updates(touched_lots)
    return self._er_build_execute_result(...)

Candidate helper names:
- _er_load_reserved_plans
- _er_warn_stale_plans
- _er_build_execution_context
- _er_validate_reserved_target
- _er_apply_pick_transition
- _er_update_inventory_pick_weights
- _er_mark_plan_executed
- _er_insert_picking_row
- _er_record_pick_movement
- _er_finalize_lot_status_updates
- _er_build_execute_result

Additional rules:
- preserve lot-mode/null-tonbag behavior
- do not redesign placeholder semantics
- inventory weight update failures are critical
- picking_table failure handling may be ambiguous:
  preserve legacy behavior if needed, but make the ambiguity visible via logging + NOTE/TODO

──────────────────────────────────────
C. reserve_from_allocation()
──────────────────────────────────────

[EXISTING HELPER PROTECTION]
Before refactoring reserve_from_allocation(), first inspect existing _ra_* helpers.
Do not create duplicate helper layers if equivalent helpers already exist.
Prefer reusing, merging, or slightly extending existing _ra_* helpers over introducing parallel ones.

Goal:
Refactor reserve_from_allocation() into a clear reservation-creation orchestration flow without changing policy.

Target structure:

def reserve_from_allocation(...):
    now = datetime.now().strftime(DATETIME_FORMAT)
    result = self._ra_init_reservation_context(...)
    self._ra_precheck_duplicate_source(...)
    import_batch_id = self._ra_create_import_batch(...)

    with self.db.transaction("IMMEDIATE"):
        self._ra_preflight_batch(allocation_rows, result)

        for line_no, alloc in enumerate(allocation_rows, start=1):
            line_ctx = self._ra_parse_allocation_line(alloc, line_no)
            self._ra_validate_allocation_line(line_ctx)
            decision = self._ra_prepare_and_decide_reservation(line_ctx)
            self._ra_apply_reservation(decision, now, result)
            self._ra_write_reservation_audit(decision, now, result)

    return self._ra_finalize_reservation_result(result)

Candidate helper names:
- _ra_init_reservation_context
- _ra_precheck_duplicate_source
- _ra_create_import_batch
- _ra_preflight_batch
- _ra_parse_allocation_line
- _ra_validate_allocation_line
- _ra_prepare_and_decide_reservation
- _ra_apply_reservation
- _ra_write_reservation_audit
- _ra_finalize_reservation_result

Optional sub-helpers if useful:
- _ra_load_available_targets
- _ra_resolve_requested_pick_count
- _ra_decide_approval_requirement
- _ra_is_lot_mode_path
- _ra_apply_pending_approval_reservation
- _ra_apply_lot_mode_reservation
- _ra_apply_tonbag_mode_reservation

Additional rules:
- do not change approval semantics
- do not change lot-mode meaning
- do not change tonbag selection logic
- do not change qty/MXBG interpretation
- do not reinterpret sample policy
- if sample handling appears internally inconsistent, preserve behavior and leave explicit NOTE/TODO instead of policy rewriting

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[IMPLEMENTATION STYLE RULES]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- Prefer small private helpers over deep nested inline blocks
- Prefer behavior-preserving extraction over logic rewriting
- Preserve existing return shapes as much as possible
- Preserve public signatures exactly
- Preserve SQL semantics as much as possible
- Keep edits localized and conservative
- Add short comments only where they clarify critical intent
- Avoid cosmetic churn unrelated to the three target functions

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[STOP CONDITIONS]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Do not stop for minor local ambiguity if behavior can be preserved.
Stop only when ambiguity would alter persisted data semantics, state meaning, or cross-file interface contracts.

Specific STOP triggers:

1) a public method signature would need to change
2) a DB schema change seems required
3) cross-file modifications are needed beyond minimal import safety
4) existing return shape cannot be preserved safely
5) a change would alter what gets written to DB (column values, row semantics, transaction scope)

If stopping, output exactly:

STOP-REASON:
- function:
- exact issue:
- why unsafe:
- proposed next action:

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[REQUIRED OUTPUT AFTER CHANGES]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

After making changes, output:

1) touched functions
2) extracted helpers
3) wording changes
4) exception/logging changes
5) deferred ambiguities
6) confirmation that the following were NOT changed:
   - DB schema
   - business policy
   - LOT-mode semantics
   - sample-policy semantics
   - public signatures
   - cross-file interfaces

Also provide a concise diff summary like:

confirm_outbound:
- extracted X helpers
- standardized OUTBOUND wording
- strengthened logging around critical confirm paths

execute_reserved:
- extracted X helpers
- separated critical transition path from auxiliary record path
- clarified ambiguous picking_table handling with NOTE/TODO

reserve_from_allocation:
- extracted X helpers
- isolated parse / validate / decide / apply / audit phases
- preserved approval and lot-mode behavior

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[FINAL DECISION PRINCIPLE]
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

When in doubt:
- choose smaller change
- preserve behavior
- avoid policy interpretation
- surface ambiguity explicitly
- prioritize operational truth and data integrity over elegance
```

---

## 사용 메모

### 권장 사용 순서
1. SQM 프로젝트 전체 Git 백업
2. 대상 파일 백업
3. Claude Code에 본 프롬프트 입력
4. 수정 결과 diff 확인
5. 테스트 실행
6. 필요 시 Cursor로 후속 미세 조정

### 주의
- 이 문서는 **최소 안전 1차 패치용**입니다.
- 구조 재설계 문서가 아닙니다.
- 정책이 애매한 경우에는 STOP-REASON 형식으로 중단하도록 설계되어 있습니다.

---

## 파일 목적 요약

이 문서는 다음 3개 함수에 대해서만 1차 안전 분해를 지시합니다.

- `confirm_outbound()`
- `execute_reserved()`
- `reserve_from_allocation()`

핵심 원칙:

- 동작 보존
- 범위 제한
- 상태 표현 정리
- 핵심/보조 write 구분
- 예외 가시성 강화

