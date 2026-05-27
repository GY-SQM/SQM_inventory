/* ── Allocation Page Module ── */
'use strict';

const AllocationPage = (() => {
  const API = window.SQM_API_BASE || window.location.origin || '';
  let data = [];
  let selected = new Set();

  async function load() {
    try {
      const res = await fetch(API + '/api/allocation');
      if (res.ok) { const j = await res.json(); data = j.data || []; }
    } catch { data = []; }
    render();
  }

  function render() {
    const tbody = document.getElementById('allocation-tbody');
    if (!tbody) return;
    tbody.innerHTML = data.length ? data.map(row => `
      <tr>
        <td><input type="checkbox" onchange="AllocationPage.toggle('${row.lot}', this.checked)"></td>
        <td class="mono-cell" style="color:var(--accent)">${row.lot}</td>
        <td><span class="tag">${row.product}</span></td>
        <td>${row.customer || '-'}</td>
        <td class="mono-cell">${row.sale_ref || '-'}</td>
        <td class="mono-cell" style="color:var(--accent)">${(row.balance||0).toLocaleString()}</td>
        <td class="mono-cell">${row.bags || '-'}</td>
        <td class="mono-cell">${row.ship_date || '-'}</td>
        <td>${window.STATUS_BADGE?.['RESERVED'] || 'RESERVED'}</td>
        <td><button class="btn btn-ghost btn-xs" onclick="AllocationPage.cancel('${row.lot}')">취소</button></td>
      </tr>
    `).join('') : `<tr><td colspan="10" style="text-align:center;padding:40px;color:var(--text-muted)">배정 데이터 없음</td></tr>`;
    _renderAllocFooter();
  }

  function toggle(lot, checked) {
    checked ? selected.add(lot) : selected.delete(lot);
  }

  async function cancel(lot) {
    if (!confirm(`${lot} 배정을 취소하시겠습니까?`)) return;
    try {
      const res = await fetch(`${API}/api/allocation/${lot}/cancel`, { method: 'POST' });
      if (res.ok) { window.showToast?.('success', `${lot} 배정 취소 완료`); await load(); }
      else window.showToast?.('error', '배정 취소 실패');
    } catch { window.showToast?.('error', '서버 연결 오류'); }
  }

  async function cancelBulk() {
    if (!selected.size) { window.showToast?.('warning', '선택된 항목 없음'); return; }
    for (const lot of selected) await cancel(lot);
    selected.clear();
  }


  function _renderAllocFooter() {
    var foot = document.getElementById('allocation-footer');
    if (!foot) {
      var tb = document.getElementById('allocation-tbody');
      if (!tb) return;
      var tbl = tb.closest ? tb.closest('table') : tb.parentElement;
      if (!tbl || !tbl.parentNode) return;
      foot = document.createElement('div');
      foot.id = 'allocation-footer';
      foot.style.cssText = 'padding:5px 12px;background:var(--bg-hover);border-top:1px solid var(--panel-border);font-size:12px;flex-shrink:0;';
      tbl.parentNode.insertBefore(foot, tbl.nextSibling);
    }
    var s = 'display:inline-block;padding:2px 14px;margin-right:8px;background:rgba(79,195,247,0.13);border-radius:6px;font-size:12px;color:var(--accent,#4fc3f7);font-weight:700;';
    var totBal  = data.reduce(function(a,r){return a+Number(r.balance||0);}, 0);
    var totBags = data.reduce(function(a,r){return a+Number(r.bags||0);}, 0);
    foot.innerHTML =
        '<span style="' + s + '">📋 배정 ' + data.length.toLocaleString('ko-KR') + ' LOT</span>'
      + '<span style="' + s + '">⚖ ' + totBal.toLocaleString('ko-KR', {maximumFractionDigits:3}) + ' MT</span>'
      + (totBags > 0 ? '<span style="' + s + '">톤백 ' + totBags.toLocaleString('ko-KR') + ' 개</span>' : '');
  }

  return { load, render, toggle, cancel, cancelBulk };
})();
