/* ── Outbound Pages Module (출고예정 / 판매화물결정 / 출고완료) ── */
'use strict';

const OutboundPage = (() => {
  const API = window.SQM_API_BASE || window.location.origin || '';

  async function fetchJsonChecked(url, opts) {
    const res = await fetch(url, opts);
    const text = await res.text();
    if (!res.ok) throw new Error('HTTP ' + res.status);
    if (!text || text.trim() === '') throw new Error('empty outbound response');
    const data = JSON.parse(text);
    if (data?.ok === false || data?.success === false) {
      throw new Error(data.message || data.error || 'outbound response failed');
    }
    return data;
  }

  function showOutboundRetry(lotNo, action, message) {
    const id = `outbound-retry-${action}-${String(lotNo || '').replace(/[^a-zA-Z0-9_-]/g, '_')}`;
    let box = document.getElementById(id);
    if (!box) {
      box = document.createElement('div');
      box.id = id;
      box.className = 'empty outbound-retry';
      box.style.cssText = 'margin:10px 0;padding:12px;border:1px solid var(--status-error);border-radius:8px;color:var(--status-error);';
      const target = document.getElementById('page-container') || document.body;
      target.prepend(box);
    }
    box.innerHTML = `
      <div>${message || '출고 처리 실패'} — LOT ${lotNo}</div>
      <button type="button" class="btn btn-sm" data-outbound-retry="${action}">다시 시도</button>
    `;
    box.querySelector('[data-outbound-retry]')?.addEventListener('click', () => {
      if (action === 'confirm') confirmOutbound(lotNo);
      else if (action === 'cancel') cancelOutbound(lotNo);
    });
  }

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
      const data = await fetchJsonChecked(`${API}/api/outbound/${lotNo}/confirm`, { method: 'POST' });
      window.showToast?.(data.success ? 'success' : 'error', data.message || '처리 완료');
    } catch (err) {
      window.showToast?.('error', err.message || '서버 연결 오류');
      showOutboundRetry(lotNo, 'confirm', err.message || '출고확정 실패');
    }
  }

  async function cancelOutbound(lotNo) {
    if (!confirm(`${lotNo} 출고를 취소하시겠습니까?`)) return;
    try {
      const data = await fetchJsonChecked(`${API}/api/outbound/${lotNo}/cancel`, { method: 'POST' });
      window.showToast?.(data.success ? 'success' : 'error', data.message || '취소 완료');
    } catch (err) {
      window.showToast?.('error', err.message || '서버 연결 오류');
      showOutboundRetry(lotNo, 'cancel', err.message || '출고취소 실패');
    }
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
    var s = 'display:inline-block;padding:4px 18px;margin-right:10px;background:#FFD600;border-radius:8px;font-size:14px;color:#222;font-weight:800;box-shadow:0 1px 4px rgba(0,0,0,.25);';
    var total = 0;
    rows.forEach(function(r) { total += Number(r.balance || r.net || r.balance_kg || 0); });
    foot.innerHTML =
        '<span style="' + s + '">📋 ' + rows.length.toLocaleString('ko-KR') + ' 건</span>'
      + (total > 0 ? '<span style="' + s + '">⚖ ' + total.toLocaleString('ko-KR', {maximumFractionDigits:3}) + ' MT</span>' : '');
  }

  return { loadScheduled, loadHistory, renderTable, confirmOutbound, cancelOutbound };
})();
