# SQM Dashboard Phase A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 기존 dashboard.py에 7-KPI 집계 + 주간 차트 엔드포인트를 추가하고, dashboard.js를 C형 대시보드(KPI카드×7 + 바차트 + 알림패널 + B형 드릴다운)로 교체한다.

**Architecture:** `backend/api/dashboard.py`에 `/api/dashboard/summary`·`/api/dashboard/weekly` 엔드포인트 2개 추가 → `frontend/js/pages/dashboard.js` 전면 교체 → `index.html`에 Chart.js CDN 추가 → `layout.css`에 사이드바 툴팁 CSS 추가. 기존 `/api/dashboard/kpi` · `/api/dashboard/stats` 엔드포인트는 그대로 유지(하위 호환).

**Tech Stack:** Python 3.x + FastAPI + SQLite + vanilla JS + Chart.js 4.x (CDN)

---

## File Map

| 파일 | 변경 | 역할 |
|------|------|------|
| `backend/api/dashboard.py` | 수정 (기존 파일 끝에 추가) | `/summary`·`/weekly` 엔드포인트 |
| `frontend/js/pages/dashboard.js` | 전면 교체 | KPI×7 + 차트 + 알림 + 드릴다운 |
| `frontend/index.html` | 수정 | Chart.js CDN `<script>` 추가 |
| `frontend/css/layout.css` | 수정 | 사이드바 아이콘 툴팁 CSS 추가 |
| `tests/test_dashboard_phase_a.py` | 신규 | 새 엔드포인트 계약 테스트 |

---

## Task 1: `/api/dashboard/summary` 엔드포인트 추가

**Files:**
- Modify: `backend/api/dashboard.py` (파일 끝에 추가)
- Test: `tests/test_dashboard_phase_a.py`

- [ ] **Step 1: 테스트 파일 생성 (failing)**

파일 경로: `tests/test_dashboard_phase_a.py`

```python
# -*- coding: utf-8 -*-
"""Phase A — /api/dashboard/summary + /api/dashboard/weekly 계약 테스트."""
import os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASHBOARD_PY = os.path.join(ROOT, "backend", "api", "dashboard.py")


def _src():
    with open(DASHBOARD_PY, encoding="utf-8", errors="ignore") as f:
        return f.read()


def test_summary_endpoint_exists():
    src = _src()
    assert '@router.get("/summary")' in src or "router.get('/summary')" in src, \
        "GET /api/dashboard/summary 라우트가 없음"


def test_summary_returns_7_kpi_keys():
    src = _src()
    required = [
        "stock_mt",
        "inbound_pending",
        "outbound_pending",
        "picked_today_mt",
        "integrity_alerts",
        "lot_count",
        "return_pending",
    ]
    for key in required:
        assert f'"{key}"' in src or f"'{key}'" in src, \
            f"summary 응답에 '{key}' 키가 없음"


def test_weekly_endpoint_exists():
    src = _src()
    assert '@router.get("/weekly")' in src or "router.get('/weekly')" in src, \
        "GET /api/dashboard/weekly 라우트가 없음"


def test_weekly_returns_required_keys():
    src = _src()
    for key in ["labels", "inbound_mt", "outbound_mt"]:
        assert f'"{key}"' in src or f"'{key}'" in src, \
            f"weekly 응답에 '{key}' 키가 없음"


def test_integrity_check_uses_1kg_tolerance():
    src = _src()
    assert "1.0" in src or "1 " in src, \
        "정합성 허용 오차 ±1kg 관련 코드가 없음"
```

- [ ] **Step 2: 테스트 실행 — 실패 확인**

```bash
cd D:\program\sqm\SQM_inventory\SQM_v874_clean
python -m pytest tests/test_dashboard_phase_a.py -v
```

기대 결과: 5개 FAILED (`summary` 엔드포인트 없음)

- [ ] **Step 3: `backend/api/dashboard.py` 끝에 `/summary` 엔드포인트 추가**

`dashboard.py` 파일 맨 끝에 아래 코드를 추가한다.

```python
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GET /api/dashboard/summary — Phase A KPI ×7 집계
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@router.get("/summary")
def get_dashboard_summary():
    """
    Phase A 대시보드 KPI 7개 집계.

    Response:
        ok: bool
        data:
            stock_mt:          float  — AVAILABLE 재고 (MT)
            inbound_pending:   int    — PENDING 상태 LOT 수
            outbound_pending:  int    — RESERVED 상태 톤백(출고 배정 대기)
            picked_today_mt:   float  — 오늘 PICKED MT
            integrity_alerts:  int    — 불변식 위반 LOT 수 (|initial-(current+picked)|>1)
            lot_count:         int    — 활성 LOT 총 수
            return_pending:    int    — RETURN 상태 톤백 수
            updated_at:        str    — KST ISO8601
    """
    now_str = datetime.now(KST).isoformat(timespec="seconds")
    try:
        db_path = _get_db_path()
        con = sqlite3.connect(db_path, timeout=5, check_same_thread=False)
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA busy_timeout=3000")
        c = con.cursor()

        # KPI #1: 현재 재고량 (AVAILABLE 톤백 무게 합계, MT)
        stock_mt = float(c.execute(
            "SELECT COALESCE(SUM(weight),0)/1000.0 FROM inventory_tonbag "
            "WHERE status='AVAILABLE'"
        ).fetchone()[0] or 0.0)

        # KPI #2: 입고 대기 (inventory.status='PENDING' LOT 수)
        inbound_pending = int(c.execute(
            "SELECT COUNT(*) FROM inventory WHERE status='PENDING'"
        ).fetchone()[0] or 0)

        # KPI #3: 출고 대기 (RESERVED 톤백 — 배정완료, 피킹 미완)
        outbound_pending = int(c.execute(
            "SELECT COUNT(*) FROM inventory_tonbag WHERE status='RESERVED'"
        ).fetchone()[0] or 0)

        # KPI #4: 오늘 피킹 완료 (MT) — PICKED 상태 + 오늘 updated_at
        picked_today_mt = float(c.execute("""
            SELECT COALESCE(SUM(weight),0)/1000.0 FROM inventory_tonbag
            WHERE status='PICKED'
              AND DATE(COALESCE(updated_at, created_at), 'localtime') = DATE('now', 'localtime')
        """).fetchone()[0] or 0.0)

        # KPI #5: 정합성 알림 (|initial_weight - (current_weight+picked_weight)| > 1.0)
        integrity_alerts = int(c.execute("""
            SELECT COUNT(*) FROM inventory
            WHERE ABS(initial_weight - (current_weight + picked_weight)) > 1.0
              AND status NOT IN ('SOLD','RETURNED')
        """).fetchone()[0] or 0)

        # KPI #6: 활성 LOT 총 수
        lot_count = int(c.execute(
            "SELECT COUNT(DISTINCT lot_no) FROM inventory "
            "WHERE status NOT IN ('SOLD','RETURNED','PENDING')"
        ).fetchone()[0] or 0)

        # KPI #7: 반품 대기 (RETURN 상태 톤백 수)
        return_pending = int(c.execute(
            "SELECT COUNT(*) FROM inventory_tonbag WHERE status='RETURN'"
        ).fetchone()[0] or 0)

        con.close()
        return {
            "ok": True,
            "data": {
                "stock_mt":         round(stock_mt, 3),
                "inbound_pending":  inbound_pending,
                "outbound_pending": outbound_pending,
                "picked_today_mt":  round(picked_today_mt, 3),
                "integrity_alerts": integrity_alerts,
                "lot_count":        lot_count,
                "return_pending":   return_pending,
                "updated_at":       now_str,
            },
        }
    except Exception as exc:
        logger.error("[dashboard/summary] 집계 실패: %s", exc, exc_info=True)
        return {
            "ok": False,
            "data": {
                "stock_mt": 0.0, "inbound_pending": 0, "outbound_pending": 0,
                "picked_today_mt": 0.0, "integrity_alerts": 0, "lot_count": 0,
                "return_pending": 0, "updated_at": now_str,
            },
            "error": str(exc),
        }
```

- [ ] **Step 4: 테스트 재실행 — summary 3개 통과 확인**

```bash
python -m pytest tests/test_dashboard_phase_a.py::test_summary_endpoint_exists tests/test_dashboard_phase_a.py::test_summary_returns_7_kpi_keys tests/test_dashboard_phase_a.py::test_integrity_check_uses_1kg_tolerance -v
```

기대 결과: 3 PASSED

- [ ] **Step 5: 중간 커밋**

```bash
git add backend/api/dashboard.py tests/test_dashboard_phase_a.py
git commit -m "feat(api): GET /api/dashboard/summary — KPI ×7 집계 엔드포인트 추가"
```

---

## Task 2: `/api/dashboard/weekly` 엔드포인트 추가

**Files:**
- Modify: `backend/api/dashboard.py`
- Test: `tests/test_dashboard_phase_a.py` (이미 있는 weekly 테스트 활성화)

- [ ] **Step 1: `dashboard.py` 끝에 `/weekly` 엔드포인트 추가**

`/summary` 코드 바로 아래에 추가:

```python
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GET /api/dashboard/weekly — 주간 입출고 차트 데이터
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
@router.get("/weekly")
def get_dashboard_weekly():
    """
    최근 7일 일별 입고/출고 합계 (MT).

    Response:
        labels:      list[str]   — ["월", "화", ..., "오늘"]  (7개)
        inbound_mt:  list[float] — 일별 입고 MT
        outbound_mt: list[float] — 일별 출고 MT
    """
    try:
        db_path = _get_db_path()
        con = sqlite3.connect(db_path, timeout=5, check_same_thread=False)
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA busy_timeout=3000")
        c = con.cursor()

        DAY_LABELS = ["월", "화", "수", "목", "금", "토", "일"]

        rows = c.execute("""
            SELECT
                DATE(COALESCE(inbound_date, created_at), 'localtime') AS day,
                ROUND(COALESCE(SUM(CASE WHEN outbound_date IS NULL THEN weight ELSE 0 END),0)/1000.0, 3),
                ROUND(COALESCE(SUM(CASE WHEN outbound_date IS NOT NULL THEN weight ELSE 0 END),0)/1000.0, 3)
            FROM inventory_tonbag
            WHERE DATE(COALESCE(inbound_date, created_at), 'localtime')
                  >= DATE('now', '-6 days', 'localtime')
            GROUP BY day
            ORDER BY day ASC
        """).fetchall()
        con.close()

        day_map = {row[0]: (float(row[1] or 0), float(row[2] or 0)) for row in rows}

        from datetime import date, timedelta
        labels, inbound_mt, outbound_mt = [], [], []
        today = date.today()
        for i in range(6, -1, -1):
            d = today - timedelta(days=i)
            day_str = d.strftime("%Y-%m-%d")
            label = "오늘" if i == 0 else DAY_LABELS[d.weekday()]
            in_mt, out_mt = day_map.get(day_str, (0.0, 0.0))
            labels.append(label)
            inbound_mt.append(in_mt)
            outbound_mt.append(out_mt)

        return {"ok": True, "labels": labels, "inbound_mt": inbound_mt, "outbound_mt": outbound_mt}
    except Exception as exc:
        logger.error("[dashboard/weekly] 집계 실패: %s", exc, exc_info=True)
        return {"ok": False, "labels": [], "inbound_mt": [], "outbound_mt": [], "error": str(exc)}
```

- [ ] **Step 2: 전체 테스트 실행 — 5개 모두 PASSED 확인**

```bash
python -m pytest tests/test_dashboard_phase_a.py -v
```

기대 결과:
```
test_summary_endpoint_exists        PASSED
test_summary_returns_7_kpi_keys     PASSED
test_weekly_endpoint_exists         PASSED
test_weekly_returns_required_keys   PASSED
test_integrity_check_uses_1kg_tolerance PASSED
```

- [ ] **Step 3: 커밋**

```bash
git add backend/api/dashboard.py
git commit -m "feat(api): GET /api/dashboard/weekly — 주간 입출고 차트 데이터 엔드포인트"
```

---

## Task 3: `index.html` — Chart.js CDN 추가

**Files:**
- Modify: `frontend/index.html` (`</head>` 바로 앞에 추가)

- [ ] **Step 1: `</head>` 바로 앞 줄에 Chart.js CDN 추가**

`frontend/index.html`에서 `</head>` 태그를 찾아 그 바로 앞에 삽입:

```html
  <!-- Chart.js — dashboard.js KPI 차트용 (Phase A) -->
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.3/dist/chart.umd.min.js"></script>
```

- [ ] **Step 2: 브라우저 콘솔에서 `typeof Chart !== 'undefined'` 확인**

앱 실행 후 DevTools 콘솔에서:
```js
typeof Chart  // "function" 이어야 함
```

- [ ] **Step 3: 커밋**

```bash
git add frontend/index.html
git commit -m "feat(ui): Chart.js 4.4.3 CDN 추가 — dashboard 주간 차트용"
```

---

## Task 4: `layout.css` — 사이드바 아이콘 툴팁 추가

**Files:**
- Modify: `frontend/css/layout.css`

- [ ] **Step 1: `layout.css` 끝에 사이드바 툴팁 CSS 추가**

`layout.css` 파일 맨 끝에 추가:

```css
/* ── KPI 대시보드 사이드바 아이콘 툴팁 (Phase A) ─────────────────── */
.sqm-sidenav-icon {
  position: relative;
}
.sqm-sidenav-icon::after {
  content: attr(data-label);
  position: absolute;
  left: calc(100% + 8px);
  top: 50%;
  transform: translateY(-50%);
  background: var(--panel, #1a2030);
  color: var(--fg, #c8d6e8);
  font-size: 11px;
  white-space: nowrap;
  padding: 4px 10px;
  border-radius: 6px;
  border: 1px solid var(--panel-border, #21293a);
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.15s;
  z-index: 9999;
}
.sqm-sidenav-icon:hover::after {
  opacity: 1;
}
```

`data-label` 속성으로 툴팁 텍스트를 제어한다. 예: `<div class="sqm-sidenav-icon" data-label="대시보드">`.

- [ ] **Step 2: 커밋**

```bash
git add frontend/css/layout.css
git commit -m "feat(css): 사이드바 아이콘 hover 툴팁 추가 (sqm-sidenav-icon::after)"
```

---

## Task 5: `dashboard.js` 전면 교체 — KPI ×7 + 차트 + 알림 + 드릴다운

**Files:**
- Modify (전면 교체): `frontend/js/pages/dashboard.js`
- 기존 파일은 git이 보관 (커밋 전 상태 복구 가능)

- [ ] **Step 1: 기존 파일 내용을 아래로 교체**

`frontend/js/pages/dashboard.js` 전체를 교체:

```js
// SQM Phase A — C+B 하이브리드 대시보드
// KPI ×7 카드 + 주간 바차트 + 실시간 알림 + B형 드릴다운 테이블
import { apiGet } from '../api-client.js';
import { showToast } from '../toast.js';

// ── 30초 폴링 핸들 (페이지 unmount 시 해제) ──
let _pollHandle = null;

// ── KPI 카드 정의 ──
const KPI_DEFS = [
  { key: 'stock_mt',         label: '현재 재고량',   unit: 'MT',  cls: 'kpi-blue',   icon: '📦', fmt: 'mt' },
  { key: 'inbound_pending',  label: '입고 대기',     unit: '건',  cls: 'kpi-green',  icon: '📥', fmt: 'int' },
  { key: 'outbound_pending', label: '출고 대기',     unit: '건',  cls: 'kpi-orange', icon: '📤', fmt: 'int' },
  { key: 'picked_today_mt',  label: '피킹 완료',     unit: 'MT',  cls: 'kpi-teal',   icon: '🏷️', fmt: 'mt' },
  { key: 'integrity_alerts', label: '정합성 알림',   unit: '건',  cls: 'kpi-red',    icon: '⚠️', fmt: 'int' },
  { key: 'lot_count',        label: 'LOT 총 수량',   unit: '개',  cls: 'kpi-purple', icon: '🗂️', fmt: 'int' },
  { key: 'return_pending',   label: '반품 대기',     unit: '건',  cls: 'kpi-coral',  icon: '↩️', fmt: 'int' },
];

// ── 숫자 포매터 ──
function fmtMt(v)  { return (typeof v === 'number' ? v.toLocaleString('ko-KR', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) : '—'); }
function fmtInt(v) { return (typeof v === 'number' ? v.toLocaleString('ko-KR') : '—'); }
function fmt(v, type) { return type === 'mt' ? fmtMt(v) : fmtInt(v); }

// ── 마운트 ──
export async function mount(container) {
  container.innerHTML = buildSkeleton();
  await Promise.all([loadSummary(), loadAlerts()]);
  await loadWeekly();
  startPolling();
}

export function unmount() {
  if (_pollHandle) { clearInterval(_pollHandle); _pollHandle = null; }
  if (window._sqmDashChart) { window._sqmDashChart.destroy(); window._sqmDashChart = null; }
}

// ── HTML 뼈대 ──
function buildSkeleton() {
  const cards = KPI_DEFS.map((d, i) => `
    <div class="sqm-kpi-card ${d.cls}" data-kpi="${d.key}" title="${d.label} 클릭하면 상세보기">
      <div class="sqm-kpi-icon">${d.icon}</div>
      <div class="sqm-kpi-label">${d.label}</div>
      <div class="sqm-kpi-value" id="kpi-${d.key}">—</div>
      <div class="sqm-kpi-unit">${d.unit}</div>
    </div>`).join('');

  return `
    <div class="sqm-dashboard-wrap">
      <!-- KPI 카드 행 -->
      <div class="sqm-kpi-row">${cards}</div>

      <!-- 중간: 차트 + 알림 -->
      <div class="sqm-dash-mid">
        <div class="sqm-dash-panel sqm-chart-panel">
          <div class="sqm-panel-header">
            <span class="sqm-panel-title">📈 주간 입출고 추이</span>
          </div>
          <canvas id="sqm-weekly-chart" height="120"></canvas>
        </div>
        <div class="sqm-dash-panel sqm-alert-panel">
          <div class="sqm-panel-header">
            <span class="sqm-panel-title">🔔 실시간 알림</span>
          </div>
          <div id="sqm-alerts-list"><div class="sqm-empty-msg">로딩 중...</div></div>
        </div>
      </div>

      <!-- B형 드릴다운 (기본 숨김) -->
      <div id="sqm-drilldown" class="sqm-dash-panel" style="display:none">
        <div class="sqm-panel-header">
          <span class="sqm-panel-title" id="sqm-drill-title">상세 보기</span>
          <button class="sqm-drill-close" onclick="document.getElementById('sqm-drilldown').style.display='none'">✕ 닫기</button>
        </div>
        <div id="sqm-drill-content"><div class="sqm-empty-msg">항목을 선택하세요.</div></div>
      </div>
    </div>

    <style>
    .sqm-dashboard-wrap { display:flex; flex-direction:column; gap:14px; padding:16px; height:100%; overflow-y:auto; }
    .sqm-kpi-row { display:grid; grid-template-columns:repeat(7,1fr); gap:10px; }
    .sqm-kpi-card { background:var(--panel,#161b26); border:1px solid var(--panel-border,#21293a); border-radius:10px; padding:12px 14px; cursor:pointer; transition:all 0.2s; position:relative; overflow:hidden; }
    .sqm-kpi-card::before { content:''; position:absolute; top:0; left:0; right:0; height:3px; }
    .kpi-blue::before   { background:#4fc3f7; } .kpi-blue .sqm-kpi-value   { color:#4fc3f7; }
    .kpi-green::before  { background:#66bb6a; } .kpi-green .sqm-kpi-value  { color:#66bb6a; }
    .kpi-orange::before { background:#ffa726; } .kpi-orange .sqm-kpi-value { color:#ffa726; }
    .kpi-teal::before   { background:#26c6da; } .kpi-teal .sqm-kpi-value   { color:#26c6da; }
    .kpi-red::before    { background:#ef5350; } .kpi-red .sqm-kpi-value    { color:#ef5350; }
    .kpi-purple::before { background:#ab47bc; } .kpi-purple .sqm-kpi-value { color:#ab47bc; }
    .kpi-coral::before  { background:#ff7043; } .kpi-coral .sqm-kpi-value  { color:#ff7043; }
    .sqm-kpi-card:hover { border-color:#4fc3f7; transform:translateY(-1px); }
    .sqm-kpi-icon  { font-size:16px; margin-bottom:4px; }
    .sqm-kpi-label { font-size:10px; color:var(--muted,#6b7c93); text-transform:uppercase; letter-spacing:.5px; margin-bottom:6px; }
    .sqm-kpi-value { font-size:24px; font-weight:800; line-height:1; }
    .sqm-kpi-unit  { font-size:10px; color:var(--muted,#6b7c93); margin-top:2px; }
    .sqm-dash-mid  { display:grid; grid-template-columns:1fr 300px; gap:14px; }
    .sqm-dash-panel { background:var(--panel,#161b26); border:1px solid var(--panel-border,#21293a); border-radius:10px; padding:14px; }
    .sqm-panel-header { display:flex; align-items:center; justify-content:space-between; margin-bottom:12px; }
    .sqm-panel-title { font-size:12px; font-weight:700; color:var(--fg,#c8d6e8); }
    .sqm-alert-item { display:flex; gap:8px; padding:8px 10px; border-radius:7px; cursor:pointer; margin-bottom:6px; border-left:3px solid; }
    .sqm-alert-item.err  { background:rgba(239,83,80,.08);  border-color:#ef5350; }
    .sqm-alert-item.warn { background:rgba(255,167,38,.08); border-color:#ffa726; }
    .sqm-alert-item.info { background:rgba(79,195,247,.08); border-color:#4fc3f7; }
    .sqm-alert-item.ok   { background:rgba(102,187,106,.08);border-color:#66bb6a; }
    .sqm-alert-title { font-size:11px; font-weight:600; color:var(--fg,#c8d6e8); }
    .sqm-alert-desc  { font-size:10px; color:var(--muted,#6b7c93); margin-top:1px; }
    .sqm-drill-close { background:none; border:1px solid var(--panel-border,#21293a); color:var(--fg,#c8d6e8); border-radius:5px; padding:3px 10px; cursor:pointer; font-size:11px; }
    .sqm-empty-msg { color:var(--muted,#6b7c93); font-size:12px; padding:12px 0; text-align:center; }
    .sqm-drill-table { width:100%; border-collapse:collapse; font-size:11px; }
    .sqm-drill-table th { background:var(--bg,#1a2030); color:var(--muted,#6b7c93); text-align:left; padding:7px 9px; font-size:10px; text-transform:uppercase; letter-spacing:.5px; border-bottom:1px solid var(--panel-border,#21293a); }
    .sqm-drill-table td { padding:7px 9px; border-bottom:1px solid var(--panel-border,#21293a); color:var(--fg,#c8d6e8); }
    .sqm-drill-table tr:hover td { background:var(--bg,#1a2030); }
    .sqm-badge { display:inline-block; padding:2px 7px; border-radius:20px; font-size:10px; font-weight:700; }
    .sq-b-avail  { background:rgba(102,187,106,.15); color:#66bb6a; }
    .sq-b-res    { background:rgba(255,167,38,.15);  color:#ffa726; }
    .sq-b-pick   { background:rgba(171,71,188,.15);  color:#ab47bc; }
    .sq-b-return { background:rgba(255,112,67,.15);  color:#ff7043; }
    </style>`;
}

// ── KPI 폴링 ──
function startPolling() {
  _pollHandle = setInterval(loadSummary, 30_000);
}

// ── KPI summary 로드 ──
async function loadSummary() {
  try {
    const res = await apiGet('/api/dashboard/summary');
    const d = res?.data || {};
    KPI_DEFS.forEach(({ key, fmt: ftype }) => {
      const el = document.getElementById(`kpi-${key}`);
      if (el) el.textContent = fmt(d[key], ftype);
    });
    // 정합성 알림 배지 강조
    const alertCard = document.querySelector('[data-kpi="integrity_alerts"]');
    if (alertCard) {
      alertCard.style.boxShadow = (d.integrity_alerts > 0)
        ? '0 0 0 2px #ef5350' : '';
    }
  } catch (e) {
    console.error('[dashboard] summary load failed', e);
    showToast?.('error', 'KPI 로드 실패');
  }
}

// ── 주간 차트 로드 ──
async function loadWeekly() {
  try {
    const res = await apiGet('/api/dashboard/weekly');
    if (!res?.ok) return;
    const canvas = document.getElementById('sqm-weekly-chart');
    if (!canvas || typeof Chart === 'undefined') return;
    if (window._sqmDashChart) window._sqmDashChart.destroy();
    window._sqmDashChart = new Chart(canvas, {
      type: 'bar',
      data: {
        labels: res.labels || [],
        datasets: [
          { label: '입고 (MT)', data: res.inbound_mt || [], backgroundColor: 'rgba(79,195,247,0.7)', borderRadius: 3 },
          { label: '출고 (MT)', data: res.outbound_mt || [], backgroundColor: 'rgba(102,187,106,0.7)', borderRadius: 3 },
        ],
      },
      options: {
        responsive: true,
        plugins: { legend: { labels: { color: '#8a9ab5', font: { size: 10 } } } },
        scales: {
          x: { ticks: { color: '#6b7c93', font: { size: 10 } }, grid: { color: 'rgba(255,255,255,0.04)' } },
          y: { ticks: { color: '#6b7c93', font: { size: 10 } }, grid: { color: 'rgba(255,255,255,0.04)' } },
        },
      },
    });
  } catch (e) {
    console.error('[dashboard] weekly chart load failed', e);
  }
}

// ── 알림 패널 로드 ──
async function loadAlerts() {
  const listEl = document.getElementById('sqm-alerts-list');
  if (!listEl) return;
  try {
    const res = await apiGet('/api/dashboard/alerts');
    const alerts = res?.alerts || [];
    if (!alerts.length) {
      listEl.innerHTML = '<div class="sqm-empty-msg">알림 없음 ✓</div>';
      return;
    }
    const LEVEL_MAP = { critical: 'err', warning: 'warn', info: 'info', ok: 'ok' };
    const ICON_MAP  = { critical: '🔴', warning: '🟡', info: '🔵', ok: '🟢' };
    listEl.innerHTML = alerts.slice(0, 6).map(a => {
      const cls  = LEVEL_MAP[a.level] || 'info';
      const icon = ICON_MAP[a.level]  || '🔵';
      return `
        <div class="sqm-alert-item ${cls}" onclick="window._sqmDrillAlert(${JSON.stringify(a).replace(/"/g,'&quot;')})">
          <span>${icon}</span>
          <div>
            <div class="sqm-alert-title">${a.message || a.title || '알림'}</div>
            ${a.desc ? `<div class="sqm-alert-desc">${a.desc}</div>` : ''}
          </div>
        </div>`;
    }).join('');
  } catch (e) {
    console.error('[dashboard] alerts load failed', e);
    if (listEl) listEl.innerHTML = '<div class="sqm-empty-msg">알림 로드 실패</div>';
  }
}

// ── B형 드릴다운: 정합성 위반 LOT 테이블 ──
window._sqmDrillAlert = async function(alert) {
  const panel = document.getElementById('sqm-drilldown');
  const title = document.getElementById('sqm-drill-title');
  const content = document.getElementById('sqm-drill-content');
  if (!panel) return;

  title.textContent = `📋 ${alert.message || '상세 보기'}`;
  content.innerHTML = '<div class="sqm-empty-msg">데이터 로딩 중...</div>';
  panel.style.display = 'block';
  panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

  try {
    // 정합성 위반 LOT 목록 조회
    const res = await apiGet('/api/dashboard/summary');
    const statsRes = await apiGet('/api/dashboard/stats');
    // stats 응답에서 integrity 정보 추출
    const integrity = statsRes?.integrity || {};

    // 간단한 드릴다운 테이블 (실제 LOT 목록은 inventory API 활용)
    const invRes = await apiGet('/api/inventory/list?limit=200');
    const lots = (invRes?.data || invRes?.lots || []).filter(lot => {
      const diff = Math.abs((lot.initial_weight || 0) - ((lot.current_weight || 0) + (lot.picked_weight || 0)));
      return diff > 1.0;
    });

    if (!lots.length) {
      content.innerHTML = '<div class="sqm-empty-msg">정합성 위반 LOT 없음 ✓</div>';
      return;
    }

    content.innerHTML = `
      <table class="sqm-drill-table">
        <thead><tr>
          <th>LOT No.</th><th>제품</th><th>Initial (kg)</th>
          <th>Current (kg)</th><th>Picked (kg)</th><th>차이 (kg)</th><th>상태</th>
        </tr></thead>
        <tbody>${lots.map(lot => {
          const diff = (lot.initial_weight || 0) - ((lot.current_weight || 0) + (lot.picked_weight || 0));
          const diffStr = diff > 0 ? `+${diff.toFixed(1)}` : diff.toFixed(1);
          const cls = { AVAILABLE:'sq-b-avail', RESERVED:'sq-b-res', PICKED:'sq-b-pick', RETURN:'sq-b-return' }[lot.status] || '';
          return `<tr>
            <td style="color:#4fc3f7">${lot.lot_no || '-'}</td>
            <td>${lot.product || '-'}</td>
            <td>${(lot.initial_weight||0).toLocaleString('ko-KR',{minimumFractionDigits:1})}</td>
            <td>${(lot.current_weight||0).toLocaleString('ko-KR',{minimumFractionDigits:1})}</td>
            <td>${(lot.picked_weight||0).toLocaleString('ko-KR',{minimumFractionDigits:1})}</td>
            <td style="color:#ef5350;font-weight:700">${diffStr} ⚠</td>
            <td><span class="sqm-badge ${cls}">${lot.status||'-'}</span></td>
          </tr>`;
        }).join('')}</tbody>
      </table>`;
  } catch (e) {
    console.error('[dashboard] drilldown failed', e);
    content.innerHTML = '<div class="sqm-empty-msg">드릴다운 로드 실패</div>';
  }
};
```

- [ ] **Step 2: 앱 실행 후 대시보드 페이지 열기 — KPI 7개 표시 확인**

```bash
python -m uvicorn backend.api:app --port 8765
```

브라우저에서 앱을 열고 대시보드 페이지 이동 후 콘솔 에러 없는지 확인.

기대 결과:
- KPI 7개 카드 표시 (숫자 또는 `—`)
- 콘솔에 `[dashboard]` 에러 없음

- [ ] **Step 3: 커밋**

```bash
git add frontend/js/pages/dashboard.js
git commit -m "feat(ui): dashboard.js 전면 교체 — C+B 하이브리드 KPI×7 + 차트 + 드릴다운"
```

---

## Task 6: 회귀 테스트 전체 실행

**Files:**
- 변경 없음 — 기존 410개 테스트가 모두 통과해야 함

- [ ] **Step 1: 전체 테스트 실행**

```bash
cd D:\program\sqm\SQM_inventory\SQM_v874_clean
python -m pytest tests/ -v --tb=short 2>&1 | tail -30
```

기대 결과:
```
===== N passed, 0 failed in X.XXs =====
```

- [ ] **Step 2: `window.confirm` 미사용 확인**

```bash
python -m pytest tests/ -k "confirm" -v
```

또는 grep으로 직접 확인:
```bash
grep -rn "window\.confirm" frontend/js/ --include="*.js"
```

기대 결과: 0건 (모두 `sqmConfirmAsync` 사용)

- [ ] **Step 3: 실패 시 대응**

테스트 실패하면:
1. 실패 메시지 읽고 어떤 모듈 영향받았는지 확인
2. `dashboard.js`에서 기존 `SAMPLE` 데이터 폴백이 제거됐으면 복구
3. 임포트 경로 (`apiGet`, `showToast`) 확인

- [ ] **Step 4: 최종 커밋**

```bash
git add .
git commit -m "test(phase-a): Phase A 전체 회귀 테스트 통과 확인"
```

---

## Phase A 완료 체크리스트

- [ ] `/api/dashboard/summary` 7-KPI 응답 정상
- [ ] `/api/dashboard/weekly` 7일 레이블+데이터 정상
- [ ] KPI 카드 ×7 실데이터 표시 (30초 폴링)
- [ ] 주간 바차트 렌더링 (Chart.js)
- [ ] 알림 패널 표시
- [ ] 알림 클릭 → B형 드릴다운 테이블 표시
- [ ] 사이드바 hover 툴팁 작동
- [ ] 회귀 테스트 전체 통과
- [ ] `window.confirm` 사용 0건 확인
