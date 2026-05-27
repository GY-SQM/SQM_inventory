/* ── Tonbag & Move Page Module ── */
'use strict';

const TonbagPage = (() => {
  const API = window.SQM_API_BASE || window.location.origin || '';
  let data = [];
  let filters = { lot: '', sap: '', bl: '', container: '', product: '', status: '' };

  async function load() {
    try {
      const params = new URLSearchParams();
      if (filters.lot) params.set('lot_no', filters.lot);
      if (filters.status) params.set('status', filters.status);
      const res = await fetch(`${API}/api/tonbags?${params}`);
      data = res.ok ? await res.json() : [];
    } catch { data = []; }
    render();
  }

  function render() {
    const tbody = document.getElementById('tonbag-tbody');
    if (!tbody) return;
    const filtered = data.filter(r => {
      return (!filters.product || r.product === filters.product) &&
             (!filters.container || r.container?.includes(filters.container));
    });
    tbody.innerHTML = filtered.length ? filtered.map(r => `
      <tr>
        <td class="mono-cell">${r.sub_lt || r.tonbag_id || '-'}</td>
        <td class="mono-cell" style="color:var(--accent)">${r.lot_no || '-'}</td>
        <td><span class="tag">${r.product || '-'}</span></td>
        <td>${window.STATUS_BADGE?.[r.status] || r.status || '-'}</td>
        <td class="mono-cell">${(r.weight || 0).toLocaleString()}</td>
        <td class="mono-cell">${r.location || '-'}</td>
        <td class="mono-cell">${r.container || '-'}</td>
        <td><button class="btn btn-ghost btn-xs">상세</button></td>
      </tr>
    `).join('') : `<tr><td colspan="8" style="text-align:center;padding:40px;color:var(--text-muted)">데이터 없음</td></tr>`;
    _renderTonbagPageFooter(filtered);
  }

  function _doRenderFooter() {
    var filtered = data.filter(function(r) {
      return (!filters.product || r.product === filters.product) &&
             (!filters.container || (r.container && r.container.indexOf(filters.container) >= 0));
    });
    _renderTonbagPageFooter(filtered);
  }
  function setFilter(key, value) { filters[key] = value; render(); _doRenderFooter(); }


  function _renderTonbagPageFooter(rows) {
    var foot = document.getElementById('tonbag-page-footer');
    if (!foot) {
      var tb = document.getElementById('tonbag-tbody');
      if (!tb) return;
      var tbl = tb.closest ? tb.closest('table') : tb.parentElement;
      if (!tbl || !tbl.parentNode) return;
      foot = document.createElement('div');
      foot.id = 'tonbag-page-footer';
      foot.style.cssText = 'padding:5px 12px;background:var(--bg-hover);border-top:1px solid var(--panel-border);font-size:12px;flex-shrink:0;';
      tbl.parentNode.insertBefore(foot, tbl.nextSibling);
    }
    var s = 'display:inline-block;padding:2px 14px;margin-right:8px;background:rgba(79,195,247,0.13);border-radius:6px;font-size:12px;color:var(--accent,#4fc3f7);font-weight:700;';
    var totW = rows.reduce(function(a,r){return a+Number(r.weight||0);},0);
    foot.innerHTML =
        '<span style="' + s + '">톤백 ' + rows.length.toLocaleString('ko-KR') + ' 건</span>'
      + '<span style="' + s + '">⚖ 수량 ' + totW.toLocaleString('ko-KR', {maximumFractionDigits:2}) + ' kg</span>';
  }

  return { load, render, setFilter };
})();

const MovePage = (() => {
  const API = window.SQM_API_BASE || window.location.origin || '';
  let moveHistory = [];

  async function executeMove(barcode, destination) {
    if (!barcode || !destination) {
      window.showToast?.('warning', '바코드와 목적지를 입력하세요'); return;
    }
    try {
      const res = await fetch(API + '/api/move', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ barcode, destination }),
      });
      const data = await res.json();
      window.showToast?.(data.success ? 'success' : 'error', data.message || '이동 처리');
      if (data.success) await loadHistory();
    } catch { window.showToast?.('error', '서버 연결 오류'); }
  }

  async function loadHistory() {
    try {
      const res = await fetch(API + '/api/move/history');
      moveHistory = res.ok ? await res.json() : [];
      renderHistory();
    } catch {}
  }

  function renderHistory() {
    const tbody = document.getElementById('move-history-tbody');
    if (!tbody) return;
    tbody.innerHTML = moveHistory.slice(0, 50).map(h => `
      <tr>
        <td class="mono-cell">${h.moved_at || '-'}</td>
        <td class="mono-cell">${h.sub_lt || '-'}</td>
        <td class="mono-cell">${h.from_location || '-'}</td>
        <td class="mono-cell" style="color:var(--accent)">${h.to_location || '-'}</td>
        <td>${h.moved_by || 'system'}</td>
      </tr>
    `).join('') || `<tr><td colspan="5" style="text-align:center;padding:20px;color:var(--text-muted)">이동 이력 없음</td></tr>`;
  }


  function _renderMoveFooter(rows) {
    var foot = document.getElementById('move-history-footer');
    if (!foot) {
      var tb = document.getElementById('move-history-tbody');
      if (!tb) return;
      var tbl = tb.closest ? tb.closest('table') : tb.parentElement;
      if (!tbl || !tbl.parentNode) return;
      foot = document.createElement('div');
      foot.id = 'move-history-footer';
      foot.style.cssText = 'padding:5px 12px;background:var(--bg-hover);border-top:1px solid var(--panel-border);font-size:12px;flex-shrink:0;';
      tbl.parentNode.insertBefore(foot, tbl.nextSibling);
    }
    var s = 'display:inline-block;padding:2px 14px;margin-right:8px;background:rgba(79,195,247,0.13);border-radius:6px;font-size:12px;color:var(--accent,#4fc3f7);font-weight:700;';
    foot.innerHTML = '<span style="' + s + '">이동 이력 ' + rows.length.toLocaleString('ko-KR') + ' 건</span>';
    _renderMoveFooter(moveHistory);
  }

  return { executeMove, loadHistory, renderHistory };
})();
