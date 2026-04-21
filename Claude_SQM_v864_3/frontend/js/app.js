/* ============================================================
   SQM Inventory — App Core (PyWebView Edition)
   ============================================================ */

'use strict';

// ── State ────────────────────────────────────────────────────
const state = {
  currentPage: 'dashboard',
  sidebarExpanded: false,
  data: { inventory: [], allocation: [], scanHistory: [] }
};

// ── Page Labels ──────────────────────────────────────────────
const PAGE_LABELS = {
  dashboard: '대시보드', inbound: '원스톱 입고', inventory: '재고 현황',
  cargo: '총괄 화물', tonbag: '톤백 리스트', move: '이동 관리',
  allocation: '판매 배정', outbound: '출고 예정', picked: '판매화물 결정',
  sold: '출고 완료', scan: '스캔', summary: '요약', log: '활동 로그',
  settings: '설정'
};

// ── Navigation ───────────────────────────────────────────────
function navigateTo(page) {
  // Hide all pages
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));

  // Show target
  const pageEl = document.getElementById(`page-${page}`);
  if (pageEl) pageEl.classList.add('active');

  // Highlight nav
  const navEl = document.querySelector(`.nav-item[data-page="${page}"]`);
  if (navEl) navEl.classList.add('active');

  // Update breadcrumb
  const bc = document.getElementById('breadcrumb-current');
  if (bc) bc.textContent = PAGE_LABELS[page] || page;

  state.currentPage = page;

  // Page-specific init
  if (page === 'inventory') renderInventoryTable();
  if (page === 'scan') focusScanInput();
}

// ── Sidebar Toggle ───────────────────────────────────────────
document.getElementById('sidebar-toggle').addEventListener('click', () => {
  state.sidebarExpanded = !state.sidebarExpanded;
  document.getElementById('app').classList.toggle('sidebar-expanded', state.sidebarExpanded);
});

// ── Nav Click ────────────────────────────────────────────────
document.querySelectorAll('.nav-item[data-page]').forEach(item => {
  item.addEventListener('click', e => {
    e.preventDefault();
    navigateTo(item.dataset.page);
  });
});

// ── Inventory Sample Data ────────────────────────────────────
const SAMPLE_INVENTORY = [
  { lot: 'SQM-2026-0421', sap: '1000421001', bl: 'COAU2604210', container: 'CRXU1234567', product: 'PP', status: 'AVAILABLE', net: 500000, balance: 500000, bags: 1000, date: '2026-04-21', location: 'A-01' },
  { lot: 'SQM-2026-0420', sap: '1000420001', bl: 'COAU2604200', container: 'TEMU8765432', product: 'PE', status: 'RESERVED',  net: 250000, balance: 250000, bags: 500,  date: '2026-04-20', location: 'B-03' },
  { lot: 'SQM-2026-0418', sap: '1000418001', bl: 'COAU2604180', container: 'MSCU3456789', product: 'PET', status: 'AVAILABLE', net: 400000, balance: 380000, bags: 760,  date: '2026-04-18', location: 'A-05' },
  { lot: 'SQM-2026-0415', sap: '1000415001', bl: 'COAU2604150', container: 'HLXU9876543', product: 'PS', status: 'PICKED',    net: 300000, balance: 300000, bags: 600,  date: '2026-04-15', location: 'C-02' },
  { lot: 'SQM-2026-0412', sap: '1000412001', bl: 'COAU2604120', container: 'OOLU2345678', product: 'ABS', status: 'OUTBOUND', net: 200000, balance: 0,      bags: 400,  date: '2026-04-12', location: '-' },
  { lot: 'SQM-2026-0410', sap: '1000410001', bl: 'COAU2604100', container: 'CRXU5678901', product: 'PP', status: 'AVAILABLE', net: 500000, balance: 480000, bags: 960,  date: '2026-04-10', location: 'A-02' },
  { lot: 'SQM-2026-0408', sap: '1000408001', bl: 'COAU2604080', container: 'TEMU1234560', product: 'PE', status: 'RETURN',    net: 100000, balance: 100000, bags: 200,  date: '2026-04-08', location: 'D-01' },
];

const STATUS_BADGE = {
  AVAILABLE: '<span class="badge badge-available"><span class="badge-dot"></span>가용</span>',
  RESERVED:  '<span class="badge badge-reserved"><span class="badge-dot"></span>배정</span>',
  PICKED:    '<span class="badge badge-picked"><span class="badge-dot"></span>결정</span>',
  OUTBOUND:  '<span class="badge badge-outbound"><span class="badge-dot"></span>출고</span>',
  RETURN:    '<span class="badge badge-return"><span class="badge-dot"></span>반품</span>',
  DEPLETED:  '<span class="badge badge-depleted"><span class="badge-dot"></span>소진</span>',
};

function renderInventoryTable() {
  const tbody = document.getElementById('inventory-tbody');
  if (!tbody) return;
  tbody.innerHTML = SAMPLE_INVENTORY.map(row => `
    <tr>
      <td><input type="checkbox"></td>
      <td class="mono-cell" style="color:var(--accent); font-weight:500;">${row.lot}</td>
      <td class="mono-cell">${row.sap}</td>
      <td class="mono-cell">${row.bl}</td>
      <td class="mono-cell">${row.container}</td>
      <td><span class="tag">${row.product}</span></td>
      <td>${STATUS_BADGE[row.status] || row.status}</td>
      <td class="mono-cell">${row.net.toLocaleString()}</td>
      <td class="mono-cell" style="color:${row.balance > 0 ? 'var(--status-available)' : 'var(--text-muted)'};">${row.balance.toLocaleString()}</td>
      <td class="mono-cell">${row.bags}</td>
      <td class="mono-cell">${row.date}</td>
      <td><span class="tag">${row.location}</span></td>
      <td><button class="btn btn-ghost btn-xs">상세</button></td>
    </tr>
  `).join('');
}

// ── Scan Input Focus ─────────────────────────────────────────
function focusScanInput() {
  const inp = document.getElementById('scan-input');
  if (inp) { setTimeout(() => inp.focus(), 100); }
}

// ── Global Search ────────────────────────────────────────────
document.getElementById('global-search').addEventListener('keydown', e => {
  if (e.key === 'Enter') {
    const q = e.target.value.trim();
    if (q) { navigateTo('inventory'); showToast('info', `"${q}" 검색 중...`); }
  }
});

// ── Refresh ──────────────────────────────────────────────────
document.getElementById('refresh-btn').addEventListener('click', () => {
  showToast('success', '데이터 새로고침 완료');
});

// ── Toast ────────────────────────────────────────────────────
function showToast(type, message, duration = 3000) {
  const icons = { success: '✅', error: '❌', warning: '⚠️', info: 'ℹ️' };
  const container = document.getElementById('toast-container');
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${icons[type] || 'ℹ️'}</span><span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => { toast.style.opacity = '0'; toast.style.transition = 'opacity 300ms'; setTimeout(() => toast.remove(), 300); }, duration);
}

// ── PyWebView Bridge ─────────────────────────────────────────
// pywebview가 준비되면 백엔드 API 연결
window.addEventListener('pywebviewready', () => {
  console.log('[SQM] PyWebView 연결됨');
  loadInventoryFromBackend();
});

async function loadInventoryFromBackend() {
  try {
    // FastAPI 백엔드 호출 (T7에서 구현)
    const res = await fetch('http://localhost:8765/api/inventory');
    if (res.ok) {
      const data = await res.json();
      state.data.inventory = data;
      if (state.currentPage === 'inventory') renderInventoryTable();
    }
  } catch (e) {
    // 백엔드 미연결 시 샘플 데이터 사용
    console.log('[SQM] 백엔드 미연결 — 샘플 데이터 사용');
  }
}

// ── Keyboard Shortcuts ───────────────────────────────────────
document.addEventListener('keydown', e => {
  if (e.altKey) {
    const shortcuts = {
      '1': 'dashboard', '2': 'inventory', '3': 'allocation',
      '4': 'outbound', '5': 'picked', '6': 'sold',
      '7': 'scan', '8': 'tonbag', '9': 'summary'
    };
    if (shortcuts[e.key]) { e.preventDefault(); navigateTo(shortcuts[e.key]); }
  }
  // F5 새로고침
  if (e.key === 'F5') { e.preventDefault(); showToast('success', '새로고침 완료'); }
});

// ── Theme Toggle ─────────────────────────────────────────────
const THEME_KEY = 'sqm_theme';

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  const btn = document.getElementById('theme-toggle');
  if (btn) btn.textContent = theme === 'light' ? '☀️' : '🌙';
}

function toggleTheme() {
  const current = document.documentElement.getAttribute('data-theme') || 'dark';
  const next = current === 'dark' ? 'light' : 'dark';
  applyTheme(next);
  try { localStorage.setItem(THEME_KEY, next); } catch (_) {}
  showToast('info', next === 'light' ? '라이트 모드' : '다크 모드');
}

document.getElementById('theme-toggle').addEventListener('click', toggleTheme);

// ── Init ─────────────────────────────────────────────────────
(function init() {
  // 저장된 테마 복원
  let saved = 'dark';
  try { saved = localStorage.getItem(THEME_KEY) || 'dark'; } catch (_) {}
  applyTheme(saved);

  navigateTo('dashboard');
  // 사이드바 기본 상태: 접힘 (icon-only)
  document.getElementById('app').classList.remove('sidebar-expanded');
})();
