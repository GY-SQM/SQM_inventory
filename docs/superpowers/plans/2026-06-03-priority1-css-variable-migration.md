# Priority 1: CSS HEX → CSS Variable Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** index.html, detached 파일들의 하드코딩 HEX 색상을 design-system.css CSS 변수로 전면 교체하여 테마 일관성 확보.

**Architecture:** Codex 스캔 → 매핑표 → design-system.css 신규 변수 추가 → 파일별 교체 → QA 게이트. 단계별 커밋. 로직·JS 코드 무수정.

**Tech Stack:** 순수 CSS Custom Properties, PowerShell grep, 수동 Edit. 프레임워크 없음.

---

## 파일 범위

| 파일 | 역할 | 예상 변경 수 |
|---|---|---|
| `frontend/css/design-system.css` | 신규 `--sqm-*` 변수 블록 추가 (하단) | +12줄 추가만 |
| `frontend/index.html` | 스플래시·배지·모달 HEX 교체 | ~40개 |
| `frontend/detached/ai_chat.html` | 깨진 CSS 링크 수정 + 변수명 정렬 | ~8개 |
| `frontend/detached/integrity.html` | 깨진 CSS 링크 수정 + 배지 HEX 교체 | ~10개 |
| `frontend/popout.html` | HEX 교체 (있을 경우) | ~3개 |

**수정 제외:** `frontend/css/v864-layout.css` (별도 단계), JS 파일 내 색상 문자열

---

## 색상 매핑 기준표

| 하드코딩 HEX | → CSS 변수 | 비고 |
|---|---|---|
| `#070e1a` | `var(--bg-root)` | 최외곽 배경 (exact match) |
| `#4fc3f7` | `var(--sqm-loading-highlight)` | 신규 — 스플래시 전용 |
| `#546e7a` | `var(--sqm-splash-muted)` | 신규 — 버전 텍스트 |
| `#1e3a5f` | `var(--sqm-loading-bar-bg)` | 신규 — 로딩바 트랙 |
| `#1565c0` | `var(--sqm-loading-grad-start)` | 신규 — 그러데이션 시작 |
| `#d97706`, `#f59e0b`, `#f39c12`, `#e8943a` | `var(--warning)` | 경고 계열 |
| `#94a3b8` | `var(--status-outbound)` | 사이드바 배지 (exact match) |
| `#22c55e`, `#27ae60`, `#2ecc71`, `#82c995` | `var(--success)` | 성공 계열 |
| `#3b82f6`, `#3498db`, `#2980b9` | `var(--accent)` | 강조 계열 |
| `#f59e0b`, `#fbbf24` | `var(--status-picked)` | Picked 배지 |
| `#8b5cf6` | `var(--tab-move)` | Return 배지 보라색 |
| `#3b82f6` | `var(--accent)` | Allocation 배지 |
| `#e74c3c`, `#e06868`, `#dc2626`, `#f87171` | `var(--danger)` | 위험/오류 계열 |
| `#1e2a38`, `#16213e` | `var(--bg-modal)` | 모달 배경 |
| `#2c3e50`, `#1e293b` | `var(--bg-input)` | 입력창 배경 |
| `#34495e`, `#334155` | `var(--border-default)` | 구분선 |
| `#ecf0f1`, `#e2e8f0` | `var(--text-primary)` | 밝은 텍스트 |
| `#95a5a6`, `#7f8c8d`, `#94a3b8` | `var(--text-secondary)` | 보조 텍스트 |
| `#7fb3d3` | `var(--info)` | 레이블 하늘색 |
| `#555` | `var(--bg-card-hover)` | 비활성 버튼 배경 |
| `#999` | `var(--text-muted)` | 비활성 버튼 텍스트 |
| `#4ade80`, `#16a34a` | `var(--success)` | integrity 배지 |
| `#fb923c`, `#d97706` | `var(--warning)` | integrity 배지 |
| `#f87171`, `#dc2626` | `var(--danger)` | integrity 배지 |

---

## Task 1: Git 백업 커밋

**Files:** (변경 없음 — 스냅샷만)

- [ ] **Step 1: 현재 상태 커밋**

```powershell
cd D:\program\SQM_inventory
git add sqm_v871_clean/frontend/
git commit -m "chore: Priority1 CSS 마이그레이션 작업 전 백업"
```

Expected: `1 file changed` 또는 `nothing to commit` (이미 깨끗하면 OK)

---

## Task 2: 전수 HEX 스캔 확인

**Files:** 읽기 전용 (grep 확인)

- [ ] **Step 1: 대상 파일 HEX 전수 스캔**

```powershell
# 각 파일별 HEX 색상 위치 목록 생성
Select-String -Path "D:\program\SQM_inventory\sqm_v871_clean\frontend\index.html" `
  -Pattern '#[0-9a-fA-F]{3,8}(?![0-9a-fA-F])' | Select-Object LineNumber, Line | Format-Table -Wrap
```

Expected: 40~55줄 출력. 이 목록이 이후 교체의 기준이 됨.

- [ ] **Step 2: detached 파일 스캔**

```powershell
Select-String -Path "D:\program\SQM_inventory\sqm_v871_clean\frontend\detached\*.html" `
  -Pattern '#[0-9a-fA-F]{3,8}(?![0-9a-fA-F])' | Select-Object Filename, LineNumber, Line
```

Expected: ai_chat.html 약 8줄, integrity.html 약 10줄 출력.

- [ ] **Step 3: 스캔 결과와 매핑표 대조**

위 매핑 기준표에 없는 HEX가 나오면 적절한 기존 변수에 매핑하거나 `--sqm-*` 신규 변수로 추가. 확인 후 Task 3으로 진행.

---

## Task 3: design-system.css — 신규 --sqm-* 변수 블록 추가

**Files:**
- Modify: `frontend/css/design-system.css` (파일 끝에 추가)

- [ ] **Step 1: design-system.css 마지막 줄 확인 후 블록 추가**

`design-system.css` 파일 맨 끝에 다음을 추가:

```css
/* ── SQM 프로젝트 전용 변수 (테마 무관 — 스플래시/로딩) ── */
:root {
  --sqm-loading-highlight:  #4fc3f7;   /* 로딩바 하이라이트, 스플래시 강조 텍스트 */
  --sqm-splash-muted:       #546e7a;   /* 스플래시 버전 텍스트 */
  --sqm-loading-bar-bg:     #1e3a5f;   /* 로딩바 트랙 배경 */
  --sqm-loading-grad-start: #1565c0;   /* 로딩바 그러데이션 시작색 */
}
```

- [ ] **Step 2: 변수 적용 확인 (오타 검사)**

```powershell
Select-String -Path "D:\program\SQM_inventory\sqm_v871_clean\frontend\css\design-system.css" `
  -Pattern '--sqm-'
```

Expected: 4줄 출력 (`--sqm-loading-highlight`, `--sqm-splash-muted`, `--sqm-loading-bar-bg`, `--sqm-loading-grad-start`)

- [ ] **Step 3: 커밋**

```powershell
git add sqm_v871_clean/frontend/css/design-system.css
git commit -m "feat(css): --sqm-* 스플래시 전용 변수 블록 추가"
```

---

## Task 4: index.html — 스플래시 섹션 HEX 교체 (14~26번째 줄)

**Files:**
- Modify: `frontend/index.html` (lines 14–26)

- [ ] **Step 1: 스플래시 배경 교체**

Old:
```html
<div id="sqm-splash" style="position:fixed;top:0;left:0;width:100%;height:100%;background:#070e1a;z-index:99999;
```
New:
```html
<div id="sqm-splash" style="position:fixed;top:0;left:0;width:100%;height:100%;background:var(--bg-root);z-index:99999;
```

- [ ] **Step 2: 스플래시 텍스트 색상 2곳 교체**

Old (line 18):
```html
<div style="color:#4fc3f7;font-size:13px;letter-spacing:4px;margin-top:6px;opacity:0.8;">GY LOGISTICS CO., LTD.</div>
```
New:
```html
<div style="color:var(--sqm-loading-highlight);font-size:13px;letter-spacing:4px;margin-top:6px;opacity:0.8;">GY LOGISTICS CO., LTD.</div>
```

Old (line 23):
```html
<div style="color:#4fc3f7;font-size:20px;font-weight:700;letter-spacing:2px;">S.I.M.S</div>
```
New:
```html
<div style="color:var(--sqm-loading-highlight);font-size:20px;font-weight:700;letter-spacing:2px;">S.I.M.S</div>
```

- [ ] **Step 3: 버전 텍스트 + 로딩바 교체**

Old (line 24):
```html
<div style="color:#546e7a;font-size:13px;margin-top:8px;">v8.7.0 — 초기화 중...</div>
```
New:
```html
<div style="color:var(--sqm-splash-muted);font-size:13px;margin-top:8px;">v8.7.0 — 초기화 중...</div>
```

Old (line 25):
```html
<div style="margin-top:22px;width:240px;height:4px;background:#1e3a5f;border-radius:2px;overflow:hidden;">
```
New:
```html
<div style="margin-top:22px;width:240px;height:4px;background:var(--sqm-loading-bar-bg);border-radius:2px;overflow:hidden;">
```

Old (line 26):
```html
<div style="height:100%;background:linear-gradient(90deg,#1565c0,#4fc3f7);border-radius:2px;animation:sqm-bar 1.8s ease-in-out infinite;"></div>
```
New:
```html
<div style="height:100%;background:linear-gradient(90deg,var(--sqm-loading-grad-start),var(--sqm-loading-highlight));border-radius:2px;animation:sqm-bar 1.8s ease-in-out infinite;"></div>
```

- [ ] **Step 4: 교체 확인**

```powershell
Select-String -Path "D:\program\SQM_inventory\sqm_v871_clean\frontend\index.html" `
  -Pattern '#070e1a|#4fc3f7|#546e7a|#1e3a5f|#1565c0' | Select-Object LineNumber, Line
```

Expected: 0줄 출력 (스플래시 HEX 전부 제거됨)

- [ ] **Step 5: 커밋**

```powershell
git add sqm_v871_clean/frontend/index.html
git commit -m "fix(ui): 스플래시 화면 HEX 색상 → CSS 변수 교체"
```

---

## Task 5: index.html — 사이드바 배지 및 인라인 색상 교체

**Files:**
- Modify: `frontend/index.html` (lines 305, 330–338)

- [ ] **Step 1: Picked 배지 (line 305) 교체**

Old:
```html
<span id="weight-picked-badge" style="display:none;background:#d97706;color:#fff;border-radius:4px;padding:1px 6px;font-size:11px;font-weight:700;margin-left:2px">
```
New:
```html
<span id="weight-picked-badge" style="display:none;background:var(--warning);color:#fff;border-radius:4px;padding:1px 6px;font-size:11px;font-weight:700;margin-left:2px">
```

- [ ] **Step 2: 사이드바 배지 색상 4곳 교체 (lines 330–333)**

Old:
```html
<span class="side-child-badge" id="badge-pending" style="color:#94a3b8"></span>
<span class="side-child-badge" id="badge-available" style="color:#22c55e"></span>
<span class="side-child-badge" id="badge-allocation" style="color:#3b82f6"></span>
<span class="side-child-badge" id="badge-picked" style="color:#f59e0b"></span>
```
New:
```html
<span class="side-child-badge" id="badge-pending" style="color:var(--status-outbound)"></span>
<span class="side-child-badge" id="badge-available" style="color:var(--status-available)"></span>
<span class="side-child-badge" id="badge-allocation" style="color:var(--accent)"></span>
<span class="side-child-badge" id="badge-picked" style="color:var(--status-picked)"></span>
```

- [ ] **Step 3: 사이드바 Sold/Return/Move 배지 3곳 교체 (lines 336–338)**

Old:
```html
<span class="side-child-badge" id="badge-sold" style="color:#f59e0b"></span>
<span class="side-child-badge" id="badge-return" style="color:#8b5cf6"></span>
<span class="side-child-badge" id="badge-move" style="color:#94a3b8"></span>
```
New:
```html
<span class="side-child-badge" id="badge-sold" style="color:var(--status-picked)"></span>
<span class="side-child-badge" id="badge-return" style="color:var(--tab-move)"></span>
<span class="side-child-badge" id="badge-move" style="color:var(--status-outbound)"></span>
```

- [ ] **Step 4: 확인**

```powershell
Select-String -Path "D:\program\SQM_inventory\sqm_v871_clean\frontend\index.html" `
  -Pattern '#d97706|#22c55e|#3b82f6|#f59e0b|#8b5cf6|#94a3b8' | Select-Object LineNumber, Line
```

Expected: 0줄 (해당 HEX 전부 제거됨)

- [ ] **Step 5: 커밋**

```powershell
git add sqm_v871_clean/frontend/index.html
git commit -m "fix(ui): 사이드바 배지 인라인 HEX → CSS 변수 교체"
```

---

## Task 6: index.html — 모달 영역 HEX 교체 (lines 420~534+)

**Files:**
- Modify: `frontend/index.html` (모달 HTML 구조 내 인라인 스타일)

- [ ] **Step 1: AI 템플릿 모달 배경/테두리 교체 (lines 420–421)**

Old:
```html
<div style="background:#1e2a38;border-radius:10px;padding:28px;width:520px;max-height:88vh;
    overflow-y:auto;border:1px solid #2980b9;box-shadow:0 10px 40px rgba(0,0,0,0.6);">
```
New:
```html
<div style="background:var(--bg-modal);border-radius:10px;padding:28px;width:520px;max-height:88vh;
    overflow-y:auto;border:1px solid var(--border-strong);box-shadow:var(--shadow-modal);">
```

- [ ] **Step 2: 모달 텍스트 색상 교체 (lines 425–426)**

Old:
```html
<span style="color:#ecf0f1;font-size:17px;font-weight:bold">🤖 AI 선사 템플릿 자동 생성</span>
<button onclick="closeTplAiModal()" style="background:none;border:none;color:#95a5a6;
```
New:
```html
<span style="color:var(--text-primary);font-size:17px;font-weight:bold">🤖 AI 선사 템플릿 자동 생성</span>
<button onclick="closeTplAiModal()" style="background:none;border:none;color:var(--text-secondary);
```

- [ ] **Step 3: 업로드 영역 테두리 교체 (lines 437, 450)**

Old (BL 업로드 영역):
```html
style="border:2px dashed #2980b9;border-radius:8px;padding:18px;text-align:center;
```
New:
```html
style="border:2px dashed var(--border-strong);border-radius:8px;padding:18px;text-align:center;
```

Old (D/O 업로드 영역):
```html
style="border:2px dashed #27ae60;border-radius:8px;padding:18px;text-align:center;
```
New:
```html
style="border:2px dashed var(--success);border-radius:8px;padding:18px;text-align:center;
```

- [ ] **Step 4: 업로드 레이블 색상 교체 (lines 441–442, 454–455)**

Old:
```html
<div id="tpl-bl-label" style="color:#7fb3d3;font-size:13px">
    📄 BL (선하증권) PDF — 클릭하여 업로드 <span style="color:#e74c3c">*필수</span>
```
New:
```html
<div id="tpl-bl-label" style="color:var(--info);font-size:13px">
    📄 BL (선하증권) PDF — 클릭하여 업로드 <span style="color:var(--danger)">*필수</span>
```

Old:
```html
<div id="tpl-do-label" style="color:#82c995;font-size:13px">
    📄 D/O (화물인도지시서) PDF — 클릭하여 업로드 <span style="color:#95a5a6">(선택)</span>
```
New:
```html
<div id="tpl-do-label" style="color:var(--success);font-size:13px">
    📄 D/O (화물인도지시서) PDF — 클릭하여 업로드 <span style="color:var(--text-secondary)">(선택)</span>
```

- [ ] **Step 5: 비활성 버튼 + 로딩/프리뷰 영역 교체 (lines 464–476)**

Old (비활성 버튼):
```html
font-weight:bold;cursor:pointer;background:#555;color:#999;transition:all 0.2s">
```
New:
```html
font-weight:bold;cursor:pointer;background:var(--bg-card-hover);color:var(--text-muted);transition:all 0.2s">
```

Old (로딩 텍스트):
```html
<div id="tpl-loading" style="display:none;text-align:center;padding:20px;color:#95a5a6;font-size:13px">
```
New:
```html
<div id="tpl-loading" style="display:none;text-align:center;padding:20px;color:var(--text-secondary);font-size:13px">
```

Old (프리뷰 영역):
```html
<div id="tpl-preview" style="display:none;margin-top:18px;background:#16213e;
    border-radius:8px;padding:16px;border:1px solid #2c3e50">
    <div style="color:#ecf0f1;font-weight:bold;margin-bottom:12px;font-size:14px">
```
New:
```html
<div id="tpl-preview" style="display:none;margin-top:18px;background:var(--bg-card);
    border-radius:8px;padding:16px;border:1px solid var(--border-default)">
    <div style="color:var(--text-primary);font-weight:bold;margin-bottom:12px;font-size:14px">
```

- [ ] **Step 6: 프리뷰 테이블 셀 색상 교체 (lines 481–499)**

각 `color:#95a5a6` → `color:var(--text-secondary)` 로 교체 (5곳):
```html
<!-- 교체 패턴: style="color:#95a5a6;padding:5px 0" 형태 전부 -->
<td style="color:var(--text-secondary);padding:5px 0;width:38%">선사 코드</td>
<td style="color:var(--text-secondary);padding:5px 0">선사명</td>
<td style="color:var(--text-secondary);padding:5px 0">BL 번호 형식</td>
<td style="color:var(--text-secondary);padding:5px 0">BL 번호 예시</td>
<td style="color:var(--text-secondary);padding:5px 0">포대 중량</td>
```

값 셀 색상 교체:
```html
<!-- #3498db → accent -->
<span id="prev-carrier-id" style="color:var(--accent);font-weight:bold">-</span>
<!-- #ecf0f1 → text-primary -->
<span id="prev-carrier-name" style="color:var(--text-primary)">-</span>
<!-- #2ecc71 → success -->
<span id="prev-bl-format" style="color:var(--success);font-family:monospace">-</span>
<!-- #f39c12 → warning -->
<span id="prev-bl-no" style="color:var(--warning);font-family:monospace;font-size:12px">-</span>
```

Select 입력창 배경:
```html
<!-- background:#2c3e50;color:#ecf0f1;border:1px solid #34495e → -->
<select id="prev-bag-weight" style="background:var(--bg-input);color:var(--text-primary);border:1px solid var(--border-default);
```

- [ ] **Step 7: 모달 하단 버튼 + 두 번째 모달 교체 (lines 507–534)**

Old:
```html
<div id="tpl-ai-msg" style="margin-top:10px;font-size:12px;color:#7f8c8d;line-height:1.5"></div>
```
New:
```html
<div id="tpl-ai-msg" style="margin-top:10px;font-size:12px;color:var(--text-secondary);line-height:1.5"></div>
```

저장 버튼:
```html
<!-- border:none;border-radius:6px;background:#27ae60;color:#fff → -->
border:none;border-radius:6px;background:var(--success);color:#fff;
```

불러오기 버튼:
```html
<!-- border:none;border-radius:6px;background:#2980b9;color:#fff → -->
border:none;border-radius:6px;background:var(--accent);color:#fff;
```

두 번째 모달 (재고 수정, lines 527–534):
Old:
```html
<div style="background:#1e2a38;border-radius:8px;padding:24px;width:680px;max-height:80vh;overflow-y:auto;
    border:1px solid #34495e;box-shadow:0 8px 32px rgba(0,0,0,0.5);">
    <h3 style="color:#ecf0f1;margin:0 0 16px">✏️ 재고 수정</h3>
    <p style="color:#95a5a6;font-size:13px;margin-bottom:12px">
```
```html
<textarea id="adjustTextInput" rows="4" style="width:100%;background:#2c3e50;color:#ecf0f1;
    border:1px solid #34495e;border-radius:4px;padding:10px;font-size:14px;resize:vertical;"
```
New:
```html
<div style="background:var(--bg-modal);border-radius:8px;padding:24px;width:680px;max-height:80vh;overflow-y:auto;
    border:1px solid var(--border-default);box-shadow:var(--shadow-modal);">
    <h3 style="color:var(--text-primary);margin:0 0 16px">✏️ 재고 수정</h3>
    <p style="color:var(--text-secondary);font-size:13px;margin-bottom:12px">
```
```html
<textarea id="adjustTextInput" rows="4" style="width:100%;background:var(--bg-input);color:var(--text-primary);
    border:1px solid var(--border-default);border-radius:4px;padding:10px;font-size:14px;resize:vertical;"
```

- [ ] **Step 8: 이후 추가 모달 HEX 교체**

Task 2에서 스캔한 목록을 기준으로 line 534 이후 남은 모든 HEX에 동일 패턴 적용:
- `#1e2a38`, `#16213e` → `var(--bg-modal)`
- `#2c3e50` → `var(--bg-input)`
- `#34495e`, `#2c3e50 border` → `var(--border-default)`
- `#ecf0f1`, `#e0e0e0` → `var(--text-primary)`
- `#95a5a6`, `#7f8c8d`, `#b0bec5` → `var(--text-secondary)`
- `#27ae60`, `#2ecc71` → `var(--success)`
- `#2980b9`, `#3498db` → `var(--accent)`
- `#e74c3c` → `var(--danger)`
- `#f39c12`, `#d97706` → `var(--warning)`

- [ ] **Step 9: 잔존 HEX 확인**

```powershell
Select-String -Path "D:\program\SQM_inventory\sqm_v871_clean\frontend\index.html" `
  -Pattern '#[0-9a-fA-F]{3,8}(?![0-9a-fA-F])' | Select-Object LineNumber, Line
```

Expected: JS 문자열 비교용 HEX만 남고 인라인 style 속성의 HEX는 0건.

- [ ] **Step 10: 커밋**

```powershell
git add sqm_v871_clean/frontend/index.html
git commit -m "fix(ui): 모달 인라인 HEX → CSS 변수 교체"
```

---

## Task 7: detached 파일 — 깨진 CSS 링크 수정 + 변수명 정렬

**Files:**
- Modify: `frontend/detached/ai_chat.html`
- Modify: `frontend/detached/integrity.html`

> **배경:** 두 파일 모두 존재하지 않는 `../css/design-tokens.css`를 링크하고 있어 CSS 변수가 전혀 적용되지 않는 상태. `var(--bg, #0f172a)` 형식의 fallback HEX가 항상 사용됨.

- [ ] **Step 1: ai_chat.html — CSS 링크 수정**

Old (line 6):
```html
<link rel="stylesheet" href="../css/design-tokens.css">
```
New:
```html
<link rel="stylesheet" href="../css/design-system.css">
```

- [ ] **Step 2: ai_chat.html — 변수명 정렬 (style 블록 전체)**

Old (lines 9–21 style 블록의 var() 이름 변경):
```css
body { background: var(--bg, #0f172a); color: var(--text, #e2e8f0); ... }
.header { background: var(--surface, #1e293b); border-bottom: 1px solid var(--border, #334155); ... }
.header h1 { ... color: var(--text, #e2e8f0); }
.dock-btn { ... border: 1px solid var(--border, #334155); color: var(--text-muted, #94a3b8); ... }
.dock-btn:hover { background: var(--border, #334155); }
.msg.user { background: var(--accent, #3b82f6); ... }
.msg.ai { background: var(--surface, #1e293b); border: 1px solid var(--border, #334155); ... }
.input-row { ... border-top: 1px solid var(--border, #334155); ... }
.input-row input { ... background: var(--surface, #1e293b); border: 1px solid var(--border, #334155); ... color: var(--text, #e2e8f0); ... }
.send-btn { background: var(--accent, #3b82f6); ... }
```
New (fallback 제거, 변수명 design-system.css 기준으로 통일):
```css
body { background: var(--bg-root); color: var(--text-primary); ... }
.header { background: var(--bg-card); border-bottom: 1px solid var(--border-default); ... }
.header h1 { ... color: var(--text-primary); }
.dock-btn { ... border: 1px solid var(--border-default); color: var(--text-secondary); ... }
.dock-btn:hover { background: var(--bg-card-hover); }
.msg.user { background: var(--accent); ... }
.msg.ai { background: var(--bg-card); border: 1px solid var(--border-default); ... }
.input-row { ... border-top: 1px solid var(--border-default); ... }
.input-row input { ... background: var(--bg-card); border: 1px solid var(--border-default); color: var(--text-primary); ... }
.send-btn { background: var(--accent); ... }
```

- [ ] **Step 3: integrity.html — CSS 링크 수정**

Old (line 6):
```html
<link rel="stylesheet" href="../css/design-tokens.css">
```
New:
```html
<link rel="stylesheet" href="../css/design-system.css">
```

- [ ] **Step 4: integrity.html — 변수명 정렬 (ai_chat.html과 동일 패턴)**

`var(--bg, ...)` → `var(--bg-root)`, `var(--surface, ...)` → `var(--bg-card)`, `var(--border, ...)` → `var(--border-default)`, `var(--text, ...)` → `var(--text-primary)` 로 전체 교체.

- [ ] **Step 5: integrity.html — 배지 HEX 교체**

Old (lines 17–19):
```css
.badge-ok   { background: rgba(22,163,74,.15);  color: #4ade80; border: 1px solid #16a34a; }
.badge-warn { background: rgba(217,119,6,.15);  color: #fb923c; border: 1px solid #d97706; }
.badge-err  { background: rgba(220,38,38,.15);  color: #f87171; border: 1px solid #dc2626; }
```
New:
```css
.badge-ok   { background: rgba(82,200,126,.12);  color: var(--success); border: 1px solid var(--success); }
.badge-warn { background: rgba(232,148,58,.12);  color: var(--warning); border: 1px solid var(--warning); }
.badge-err  { background: rgba(224,104,104,.12); color: var(--danger);  border: 1px solid var(--danger);  }
```

- [ ] **Step 6: integrity.html — JS 인라인 색상 교체 (lines 63, 100)**

Old:
```javascript
el.innerHTML = '<p style="color:#4ade80;padding:20px 0;font-size:14px">✅ 정합성 이상 없음</p>';
...
document.getElementById('result').innerHTML = '<p style="color:#f87171">❌ 오류: ' + ...
```
New:
```javascript
el.innerHTML = '<p style="color:var(--success);padding:20px 0;font-size:14px">✅ 정합성 이상 없음</p>';
...
document.getElementById('result').innerHTML = '<p style="color:var(--danger)">❌ 오류: ' + ...
```

- [ ] **Step 7: 커밋**

```powershell
git add sqm_v871_clean/frontend/detached/
git commit -m "fix(ui): detached 파일 CSS 링크 수정 + HEX → 변수 정렬"
```

---

## Task 8: 코드 레벨 QA — HEX 잔존 검증

**Files:** 읽기 전용

- [ ] **Step 1: 전체 HEX 잔존 검사**

```powershell
# index.html
Write-Host "=== index.html ==="
Select-String -Path "D:\program\SQM_inventory\sqm_v871_clean\frontend\index.html" `
  -Pattern 'style="[^"]*#[0-9a-fA-F]{3,8}' | Select-Object LineNumber, Line

# detached 파일
Write-Host "=== detached ==="
Select-String -Path "D:\program\SQM_inventory\sqm_v871_clean\frontend\detached\*.html" `
  -Pattern '#[0-9a-fA-F]{3,8}(?![0-9a-fA-F])' | Select-Object Filename, LineNumber, Line
```

Expected: 허용 제외 목록(JS 문자열 비교) 외 0건.  
잔존 HEX가 있으면 해당 줄을 매핑표 기준으로 추가 교체 후 재확인.

- [ ] **Step 2: CSS 변수 오타 검사**

```powershell
# 정의되지 않은 변수명 참조 여부 확인 (var(--xxx) 에서 xxx가 design-system에 없는 것)
Select-String -Path "D:\program\SQM_inventory\sqm_v871_clean\frontend\index.html" `
  -Pattern 'var\(--[a-zA-Z0-9-]+\)' -AllMatches | 
  ForEach-Object { $_.Matches } | 
  ForEach-Object { $_.Value } | 
  Sort-Object -Unique
```

출력된 변수명들이 design-system.css에 정의된 것인지 수동 확인.

- [ ] **Step 3: 신규 --sqm-* 변수 정의 확인**

```powershell
Select-String -Path "D:\program\SQM_inventory\sqm_v871_clean\frontend\css\design-system.css" `
  -Pattern '--sqm-'
```

Expected: 4줄 출력 (Task 3에서 추가한 변수들)

---

## Task 9: 시각 QA — 앱 실행 후 13섹션 전수검사

**Files:** 읽기 전용 (앱 실행 확인)

- [ ] **Step 1: 앱 실행**

```powershell
cd D:\program\SQM_inventory\sqm_v871_clean
python main.py
```

- [ ] **Step 2: 다크 모드 13섹션 체크 (앱 실행 상태에서 수동 확인)**

```
□ 1. 스플래시 화면 — 배경 그러데이션, 로딩바, 텍스트 표시 정상
□ 2. 타이틀바 — 배경색, 텍스트, 아이콘 정상
□ 3. 메뉴바 — 배경, 드롭다운, hover 상태 정상
□ 4. 액션 툴바 — 버튼 7개 색상·hover 정상
□ 5. 사이드바(접힘) — 아이콘, 활성 메뉴 강조, 배지 색상 정상
□ 6. 사이드바(펼침) — 텍스트, 하위 메뉴 정상
□ 7. KPI 카드 5개 — 배경, 수치, 구분선 정상
□ 8. 인벤토리 테이블 — 헤더, 줄무늬, 셀 텍스트, 정렬 정상
□ 9. 모달(AI 템플릿) — 배경, 테두리, 버튼 색상 정상
□ 10. 토스트 알림 — success/warning/danger 색상 정상
□ 11. 팝아웃 창 — 별도 창 색상 정상
□ 12. AI 채팅(detached) — 전체 색상 정상
□ 13. 정합성 검사(detached) — 배지·텍스트 색상 정상
```

- [ ] **Step 3: 라이트 모드 전환 후 동일 체크**

메뉴바 ☀️ Light 버튼 클릭 → 위 13개 항목 재확인

- [ ] **Step 4: 다크 모드 복귀 확인**

🌙 Dark 클릭 → 원래 색상으로 정상 복귀

---

## Task 10: 기능 QA + 최종 커밋

**Files:** 읽기 전용 QA

- [ ] **Step 1: 기능 체크**

```
□ 다크/라이트 전환 시 전체 화면 색상 즉시 반영 (깜빡임 없음)
□ 페이지 새로고침 후 테마 유지 (localStorage 확인)
□ 사이드바 접기/펼치기 색상 정상
□ 드롭다운 메뉴 열기/닫기 색상 정상
□ 테이블 hover 행 강조 동작
□ 모달 열기/닫기 시 오버레이 색상 정상
□ 버튼 hover/active 상태 정상
```

- [ ] **Step 2: QA 통과 판정**

| 레벨 | 기준 | 결과 |
|---|---|---|
| 코드 | HEX 잔존 0건, CSS 오타 0건 | □ Pass / □ Fail |
| 시각 | 13섹션 × 다크/라이트 전부 통과 | □ Pass / □ Fail |
| 기능 | 7개 항목 전부 통과 | □ Pass / □ Fail |

모두 Pass이면 최종 커밋. Fail 항목은 원인 파악 후 해당 Task 재실행.

- [ ] **Step 3: 최종 커밋**

```powershell
git add sqm_v871_clean/frontend/
git commit -m "feat(ui): Priority1 완료 — CSS HEX 전면 변수화 (QA 통과)"
```

- [ ] **Step 4: Priority 2 준비**

QA 전 항목 Pass 확인 완료 시 Priority 2(폰트 통일) 진행.
Fail 항목 있으면 Priority 2 진행 금지 — 해당 태스크로 돌아가 수정.
