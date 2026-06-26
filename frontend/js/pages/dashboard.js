// SQM Phase A — C+B 하이브리드 대시보드
// KPI ×7 카드 + 주간 바차트 + 실시간 알림 + B형 드릴다운 테이블
import { apiGet } from '../api-client.js';
import { showToast } from '../toast.js';

let _pollHandle = null;

const KPI_DEFS = [
  { key: 'stock_mt',         label: '현재 재고량',  unit: 'MT', cls: 'kpi-blue',   icon: '📦', fmt: 'mt'  },
  { key: 'inbound_pending',  label: '입고 대기',    unit: '건', cls: 'kpi-green',  icon: '📥', fmt: 'int' },
  { key: 'outbound_pending', label: '출고 대기',    unit: '건', cls: 'kpi-orange', icon: '📤', fmt: 'int' },
  { key: 'picked_today_mt',  label: '피킹 완료',    unit: 'MT', cls: 'kpi-teal',   icon: '🏷️', fmt: 'mt'  },
  { key: 'integrity_alerts', label: '정합성 알림',  unit: '건', cls: 'kpi-red',    icon: '⚠️', fmt: 'int' },
  { key: 'lot_count',        label: 'LOT 총 수량',  unit: '개', cls: 'kpi-purple', icon: '🗂️', fmt: 'int' },
  { key: 'return_pending',   label: '반품 대기',    unit: '건', cls: 'kpi-coral',  icon: '↩️', fmt: 'int' },
];

function fmtMt(v)  { return typeof v === 'number' ? v.toLocaleString('ko-KR', { minimumFractionDigits: 1, maximumFractionDigits: 1 }) : '—'; }
function fmtInt(v) { return typeof v === 'number' ? v.toLocaleString('ko-KR') : '—'; }
function fmt(v, type) { return type === 'mt' ? fmtMt(v) : fmtInt(v); }

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

function buildSkeleton() {
  const cards = KPI_DEFS.map(d => `
    <div class="sqm-kpi-card ${d.cls}" data-kpi="${d.key}">
      <div class="sqm-kpi-icon">${d.icon}</div>
      <div class="sqm-kpi-label">${d.label}</div>
      <div class="sqm-kpi-value" id="kpi-${d.key}">—</div>
      <div class="sqm-kpi-unit">${d.unit}</div>
    </div>`).join('');

  return `
    <div class="sqm-dashboard-wrap">
      <div class="sqm-kpi-row">${cards}</div>
      <div class="sqm-dash-mid">
        <div class="sqm-dash-panel sqm-chart-panel">
          <div class="sqm-panel-header"><span class="sqm-panel-title">📈 주간 입출고 추이</span></div>
          <canvas id="sqm-weekly-chart" height="120"></canvas>
        </div>
        <div class="sqm-dash-panel sqm-alert-panel">
          <div class="sqm-panel-header"><span class="sqm-panel-title">🔔 실시간 알림</span></div>
          <div id="sqm-alerts-list"><div class="sqm-empty-msg">로딩 중...</div></div>
        </div>
      </div>
      <div id="sqm-drilldown" class="sqm-dash-panel" style="display:none">
        <div class="sqm-panel-header">
          <span class="sqm-panel-title" id="sqm-drill-title">상세 보기</span>
          <button class="sqm-drill-close" onclick="document.getElementById('sqm-drilldown').style.display='none'">✕ 닫기</button>
        </div>
        <div id="sqm-drill-content"><div class="sqm-empty-msg">항목을 선택하세요.</div></div>
      </div>
    </div>

    <style>
    .sqm-dashboard-wrap{display:flex;flex-direction:column;gap:14px;padding:16px;height:100%;overflow-y:auto}
    .sqm-kpi-row{display:grid;grid-template-columns:repeat(7,1fr);gap:10px}
    .sqm-kpi-card{background:var(--panel,#161b26);border:1px solid var(--panel-border,#21293a);border-radius:10px;padding:12px 14px;cursor:pointer;transition:all 0.2s;position:relative;overflow:hidden}
    .sqm-kpi-card::before{content:'';position:absolute;top:0;left:0;right:0;height:3px}
    .kpi-blue::before{background:#4fc3f7}.kpi-blue .sqm-kpi-value{color:#4fc3f7}
    .kpi-green::before{background:#66bb6a}.kpi-green .sqm-kpi-value{color:#66bb6a}
    .kpi-orange::before{background:#ffa726}.kpi-orange .sqm-kpi-value{color:#ffa726}
    .kpi-teal::before{background:#26c6da}.kpi-teal .sqm-kpi-value{color:#26c6da}
    .kpi-red::before{background:#ef5350}.kpi-red .sqm-kpi-value{color:#ef5350}
    .kpi-purple::before{background:#ab47bc}.kpi-purple .sqm-kpi-value{color:#ab47bc}
    .kpi-coral::before{background:#ff7043}.kpi-coral .sqm-kpi-value{color:#ff7043}
    .sqm-kpi-card:hover{border-color:#4fc3f7;transform:translateY(-1px)}
    .sqm-kpi-icon{font-size:16px;margin-bottom:4px}
    .sqm-kpi-label{font-size:10px;color:var(--muted,#6b7c93);text-transform:uppercase;letter-spacing:.5px;margin-bottom:6px}
    .sqm-kpi-value{font-size:24px;font-weight:800;line-height:1}
    .sqm-kpi-unit{font-size:10px;color:var(--muted,#6b7c93);margin-top:2px}
    .sqm-dash-mid{display:grid;grid-template-columns:1fr 300px;gap:14px}
    .sqm-dash-panel{background:var(--panel,#161b26);border:1px solid var(--panel-border,#21293a);border-radius:10px;padding:14px}
    .sqm-panel-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px}
    .sqm-panel-title{font-size:12px;font-weight:700;color:var(--fg,#c8d6e8)}
    .sqm-alert-item{display:flex;gap:8px;padding:8px 10px;border-radius:7px;cursor:pointer;margin-bottom:6px;border-left:3px solid}
    .sqm-alert-item.err{background:rgba(239,83,80,.08);border-color:#ef5350}
    .sqm-alert-item.warn{background:rgba(255,167,38,.08);border-color:#ffa726}
    .sqm-alert-item.info{background:rgba(79,195,247,.08);border-color:#4fc3f7}
    .sqm-alert-item.ok{background:rgba(102,187,106,.08);border-color:#66bb6a}
    .sqm-alert-title{font-size:11px;font-weight:600;color:var(--fg,#c8d6e8)}
    .sqm-alert-desc{font-size:10px;color:var(--muted,#6b7c93);margin-top:1px}
    .sqm-drill-close{background:none;border:1px solid var(--panel-border,#21293a);color:var(--fg,#c8d6e8);border-radius:5px;padding:3px 10px;cursor:pointer;font-size:11px}
    .sqm-empty-msg{color:var(--muted,#6b7c93);font-size:12px;padding:12px 0;text-align:center}
    .sqm-drill-table{width:100%;border-collapse:collapse;font-size:11px}
    .sqm-drill-table th{background:var(--bg,#1a2030);color:var(--muted,#6b7c93);text-align:left;padding:7px 9px;font-size:10px;text-transform:uppercase;letter-spacing:.5px;border-bottom:1px solid var(--panel-border,#21293a)}
    .sqm-drill-table td{padding:7px 9px;border-bottom:1px solid var(--panel-border,#21293a);color:var(--fg,#c8d6e8)}
    .sqm-drill-table tr:hover td{background:var(--bg,#1a2030)}
    .sqm-badge{display:inline-block;padding:2px 7px;border-radius:20px;font-size:10px;font-weight:700}
    .sq-b-avail{background:rgba(102,187,106,.15);color:#66bb6a}
    .sq-b-res{background:rgba(255,167,38,.15);color:#ffa726}
    .sq-b-pick{background:rgba(171,71,188,.15);color:#ab47bc}
    .sq-b-return{background:rgba(255,112,67,.15);color:#ff7043}
    </style>`;
}

function startPolling() {
  if (_pollHandle) { clearInterval(_pollHandle); _pollHandle = null; }
  _pollHandle = setInterval(loadSummary, 30_000);
}

// ── 하위 호환 — A6 회귀 테스트가 요구하는 loadAll / normalizeDashboardStats ──
function normalizeDashboardStats(res) {
  const payload = res?.data || res || {};
  if (payload.ok === false || payload.success === false) {
    throw new Error(payload.message || payload.error || 'dashboard response failed');
  }
  return {
    products: Array.isArray(payload.products) ? payload.products : [],
    lots: Array.isArray(payload.lots) ? payload.lots : [],
  };
}

async function loadAll() {
  try {
    const res = await apiGet('/api/dashboard/stats');
    if (res?.ok === false || res?.success === false) throw new Error(res.message || res.error || 'dashboard response failed');
    const data = normalizeDashboardStats(res);
    const products = Array.isArray(data.products) ? data.products : [];
    const lots     = Array.isArray(data.lots)     ? data.lots     : [];
    return { products, lots };
  } catch (e) {
    console.error('[dashboard] loadAll 로드 실패', e);
    showToast?.('error', '대시보드 데이터 로드 실패');
    return null;
  }
}

async function loadSummary() {
  try {
    const res = await apiGet('/api/dashboard/summary');
    const d = res?.data || {};
    KPI_DEFS.forEach(({ key, fmt: ftype }) => {
      const el = document.getElementById(`kpi-${key}`);
      if (el) el.textContent = fmt(d[key], ftype);
    });
    const alertCard = document.querySelector('[data-kpi="integrity_alerts"]');
    if (alertCard) {
      alertCard.style.boxShadow = (d.integrity_alerts > 0) ? '0 0 0 2px #ef5350' : '';
    }
  } catch (e) {
    console.error('[dashboard] summary load failed', e);
    showToast?.('error', 'KPI 로드 실패');
  }
}

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
          { label: '입고 (MT)', data: res.inbound_mt || [],  backgroundColor: 'rgba(79,195,247,0.7)', borderRadius: 3 },
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
      const safeMsg = (a.message || a.title || '알림').replace(/"/g, '&quot;');
      return `
        <div class="sqm-alert-item ${cls}" data-alert-msg="${safeMsg}">
          <span>${icon}</span>
          <div>
            <div class="sqm-alert-title">${a.message || a.title || '알림'}</div>
            ${a.desc ? `<div class="sqm-alert-desc">${a.desc}</div>` : ''}
          </div>
        </div>`;
    }).join('');

    listEl.querySelectorAll('.sqm-alert-item').forEach(el => {
      el.addEventListener('click', () => showDrilldown(el.dataset.alertMsg));
    });
  } catch (e) {
    console.error('[dashboard] alerts load failed', e);
    if (listEl) listEl.innerHTML = '<div class="sqm-empty-msg">알림 로드 실패</div>';
  }
}

// Module-to-global bridge: legacy sqm-core.js router가 mount/unmount 호출 가능하도록
if (typeof window !== 'undefined') {
  window._sqmDashMount   = mount;
  window._sqmDashUnmount = unmount;
}

async function showDrilldown(title) {
  const panel   = document.getElementById('sqm-drilldown');
  const titleEl = document.getElementById('sqm-drill-title');
  const content = document.getElementById('sqm-drill-content');
  if (!panel || !titleEl || !content) return;

  titleEl.textContent = `📋 ${title}`;
  content.innerHTML = '<div class="sqm-empty-msg">데이터 로딩 중...</div>';
  panel.style.display = 'block';
  panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

  try {
    const statsRes = await apiGet('/api/dashboard/stats');
    const integrity = statsRes?.integrity || {};
    const diff = Math.abs(integrity.diff_kg || 0);

    if (diff <= 1.0) {
      content.innerHTML = '<div class="sqm-empty-msg">정합성 위반 없음 ✓</div>';
      return;
    }

    content.innerHTML = `
      <table class="sqm-drill-table">
        <thead><tr>
          <th>항목</th><th>값 (kg)</th><th>값 (MT)</th>
        </tr></thead>
        <tbody>
          <tr><td>총 입고량</td><td>${(integrity.total_inbound_kg||0).toLocaleString('ko-KR',{minimumFractionDigits:1})}</td><td>${((integrity.total_inbound_kg||0)/1000).toFixed(3)}</td></tr>
          <tr><td>PENDING 대기</td><td>${(integrity.pending_kg||0).toLocaleString('ko-KR',{minimumFractionDigits:1})}</td><td>${((integrity.pending_kg||0)/1000).toFixed(3)}</td></tr>
          <tr><td>현재 재고</td><td>${(integrity.current_stock_kg||0).toLocaleString('ko-KR',{minimumFractionDigits:1})}</td><td>${((integrity.current_stock_kg||0)/1000).toFixed(3)}</td></tr>
          <tr><td>PICKED 작업 중</td><td>${(integrity.picked_kg||0).toLocaleString('ko-KR',{minimumFractionDigits:1})}</td><td>${((integrity.picked_kg||0)/1000).toFixed(3)}</td></tr>
          <tr><td>출고 누계</td><td>${(integrity.outbound_total_kg||0).toLocaleString('ko-KR',{minimumFractionDigits:1})}</td><td>${((integrity.outbound_total_kg||0)/1000).toFixed(3)}</td></tr>
          <tr style="color:${Math.abs(integrity.diff_kg||0)>1?'#ef5350':'#66bb6a'}"><td><b>차이 (오차)</b></td><td><b>${(integrity.diff_kg||0).toFixed(1)}</b></td><td><b>${((integrity.diff_kg||0)/1000).toFixed(3)}</b></td></tr>
        </tbody>
      </table>
      <div style="margin-top:8px;font-size:10px;color:var(--muted,#6b7c93)">
        불변식: 총입고 = PENDING + 현재재고 + PICKED + 출고누계 (허용 오차 ±1kg)
      </div>`;
  } catch (e) {
    console.error('[dashboard] drilldown failed', e);
    if (content) content.innerHTML = '<div class="sqm-empty-msg">드릴다운 로드 실패</div>';
  }
}
