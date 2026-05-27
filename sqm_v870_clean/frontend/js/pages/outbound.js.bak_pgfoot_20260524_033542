/* ── Outbound Pages Module (출고예정 / 판매화물결정 / 출고완료) ── */
'use strict';

const OutboundPage = (() => {
  const API = window.SQM_API_BASE || window.location.origin || '';
  async function loadScheduled() {
    try {
      const res = await fetch(API + '/api/outbound/scheduled');
      return res.ok ? await res.json() : [];
    } catch { return []; }
  }

  async function loadHistory(dateFrom, dateTo) {
    let url = API + '/api/outbound/history';
    const params = new URLSearchParams();
    if (dateFrom) params.set('date_from', dateFrom);
    if (dateTo)   params.set('date_to', dateTo);
    if ([...params].length) url += '?' + params.toString();
    try {
      const res = await fetch(url);
      return res.ok ? await res.json() : [];
    } catch { return []; }
  }

  function renderTable(tbodyId, rows, columns) {
    const tbody = document.getElementById(tbodyId);
    if (!tbody) return;
    tbody.innerHTML = rows.length ? rows.map(row =>
      '<tr>' + columns.map(col => {
        if (col === 'status') return `<td>${window.STATUS_BADGE?.[row[col]] || row[col]}</td>`;
        if (col === 'product') return `<td><span class="tag">${row[col]||'-'}</span></td>`;
        if (['net','balance','balance_kg'].includes(col))
          return `<td class="mono-cell" style="color:var(--accent)">${(row[col]||0).toLocaleString()}</td>`;
        return `<td class="mono-cell">${row[col]||'-'}</td>`;
      }).join('') + '</tr>'
    ).join('') : `<tr><td colspan="${columns.length}" style="text-align:center;padding:40px;color:var(--text-muted)">데이터 없음</td></tr>`;
    _renderOutboundFooter(tbodyId, rows);
  }

  async function confirmOutbound(lotNo) {
    if (!confirm(`${lotNo} 출고를 확정하시겠습니까?`)) return;
    try {
      const res = await fetch(`${API}/api/outbound/${lotNo}/confirm`, { method: 'POST' });
      const data = await res.json();
      window.showToast?.(data.success ? 'success' : 'error', data.message || '처리 완료');
    } catch { window.showToast?.('error', '서버 연결 오류'); }
  }

  async function cancelOutbound(lotNo) {
    if (!confirm(`${lotNo} 출고를 취소하시겠습니까?`)) return;
    try {
      const res = await fetch(`${API}/api/outbound/${lotNo}/cancel`, { method: 'POST' });
      const data = await res.json();
      window.showToast?.(data.success ? 'success' : 'error', data.message || '취소 완료');
    } catch { window.showToast?.('error', '서버 연결 오류'); }
  }


  function _renderOutboundFooter(tbodyId, rows) {
    var footId = tbodyId.replace(/-tbody$/, '-footer');
    var foot = document.getElementById(footId);
    if (!foot) {
      var tb = document.getElementById(tbodyId);
      if (!tb) return;
      var tbl = tb.closest ? tb.closest('table') : tb.parentElement;
      if (!tbl || !tbl.parentNode) return;
      foot = document.createElement('div');
      foot.id = footId;
      foot.style.cssText = 'padding:5px 12px;background:var(--bg-hover);border-top:1px solid var(--panel-border);font-size:12px;flex-shrink:0;';
      tbl.parentNode.insertBefore(foot, tbl.nextSibling);
    }
    var s = 'display:inline-block;padding:2px 14px;margin-right:8px;background:rgba(79,195,247,0.13);border-radius:6px;font-size:12px;color:var(--accent,#4fc3f7);font-weight:700;';
    var total = 0;
    rows.forEach(function(r) { total += Number(r.balance || r.net || r.balance_kg || 0); });
    foot.innerHTML =
        '<span style="' + s + '">📋 ' + rows.length.toLocaleString('ko-KR') + ' 건</span>'
      + (total > 0 ? '<span style="' + s + '">⚖ ' + total.toLocaleString('ko-KR', {maximumFractionDigits:3}) + ' MT</span>' : '');
  }

  return { loadScheduled, loadHistory, renderTable, confirmOutbound, cancelOutbound };
})();
