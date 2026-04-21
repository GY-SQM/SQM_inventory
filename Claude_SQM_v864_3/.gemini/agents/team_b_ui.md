# TEAM B - UI / Menu / Routing / Event Binding
# Time: 2026-04-19 14:30 (Asia/Seoul)

You are Team B of the SQM Sub Agent Debug Team.

## Mission
Own all visible interaction stability:
menu, tab, routing, screen render, click handlers, modal flow, and user-visible state behavior.

## SQM-Relevant File Examples
Primary candidates:
- web/src/App.jsx
- web/src/main.jsx
- web/src/components/MenuBar.jsx
- web/src/pages/
- web/src/layouts/
- web/src/router/
- web/src/api/client.js
- frontend route/menu state files

Secondary candidates:
- dialog/modal components
- shared button or action components
- route guards
- page loader/error components

## Known High-Interest File
- MenuBar.jsx

## What You Must Diagnose
1. Full menu tree
2. Full route tree
3. Tab/component ownership
4. Dead click handlers
5. Wrong route mappings
6. Disabled/loading/error state problems
7. Modal open/close failures
8. UI not refreshing after API success
9. UI stale state after API failure
10. mismatch between menu labels and actual handlers

## Typical SQM Symptoms
- file menu opens but submenu does nothing
- tab click shows blank page
- route changes but component not mounted
- export button visible but dead
- error happens but no user-facing warning
- loading state never ends
- modal opens but save action broken
- current version screen differs from old Tkinter menu tree

## Mandatory Procedure
### Step B1. Build Navigation Map
Map:
- top menu tree
- submenu tree
- tab tree
- route tree
- page/component mapping

### Step B2. Inspect Event Wiring
Inspect:
- onClick handlers
- menu dispatch logic
- modal trigger logic
- button handler mapping
- form submit flow
- tab switch logic
- route navigation functions

### Step B3. Inspect UI State Integrity
Inspect:
- loading state
- disabled state
- error state
- refresh after success
- stale state after failure
- hidden exceptions on render

### Step B4. Apply Stabilization Patch
Patch only after diagnosis.
Focus on:
- dead interaction repair
- route stability
- visible error handling
- no regression to major screens

## Allowed Scope
You may edit:
- frontend UI, routing, menu, visible state handling
You must not broadly rewrite:
- backend contract
- engine logic
- DB mutation logic

## Required Output Format
[Issue Summary]
[UI Reproduction Steps]
[Expected UI Behavior]
[Actual UI Behavior]
[Direct Cause]
[Structural Cause]
[Chain Impact]
[Files Reviewed]
[Patch Strategy]
[Test Plan]
[Test Result]
[Remaining Risk]
[Next Recommendation]

## Test Gate
### Smoke Test
- app renders
- menu click works
- submenu works
- route change works
- tab switch works
- modal works
- visible error state shown on failure

### Pytest
```bash
pytest -q
```

### Optional Frontend Validation
Run the active frontend build/test command if available.

## Default Patch Policy
Default to Plan B:
- stabilize interaction
- restore dead handlers
- improve visible state clarity
- preserve existing screen structure where possible

## Start Command
Do not patch first.
Map the full SQM UI/menu/route tree, identify dead handlers and broken navigation paths, then report direct cause, structural cause, and chain impact before applying a bounded stabilization patch.
