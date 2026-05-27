/* ── Scan Page Module ── */
'use strict';

const ScanPage = (() => {
  const API = window.SQM_API_BASE || window.location.origin || '';
  let history = [];
  let lastBarcode = '';

  function init() {
    const inp = document.getElementById('scan-input');
    if (!inp) return;
    inp.addEventListener('keydown', e => {
      if (e.key === 'Enter') { e.preventDefault(); processBarcode(inp.value.trim()); inp.value = ''; }
    });
    inp.focus();
  }

  async function processBarcode(barcode, action) {
    if (!barcode) return;
    lastBarcode = barcode;
    if (!action) { window.showToast?.('info', `스캔: ${barcode} — 처리 유형을 선택하세요`); return; }
    try {
      const res = await fetch(API + '/api/scan/process', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ barcode, action }),
      });
      const data = await res.json();
      const ok = data.success;
      window.showToast?.(ok ? 'success' : 'error', data.message || (ok ? '처리 완료' : '처리 실패'));
      addHistory(barcode, action, ok);
    } catch {
      window.showToast?.('error', '서버 연결 오류');
      addHistory(barcode, action, false);
    }
  }

  function addHistory(barcode, action, success) {
    const now = new Date();
    const time = `${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}:${String(now.getSeconds()).padStart(2,'0')}`;
    history.unshift({ time, barcode, action, success });
    if (history.length > 100) history.pop();
    renderHistory();
  }

  function renderHistory() {
    const tbody = document.getElementById('scan-history-tbody');
    if (!tbody) return;
    tbody.innerHTML = history.slice(0, 20).map(h => `
      <tr>
        <td class="mono-cell">${h.time}</td>
        <td class="mono-cell">${h.barcode}</td>
        <td>${h.action}</td>
        <td>${h.success
          ? '<span class="badge badge-available">성공</span>'
          : '<span class="badge badge-return">실패</span>'}</td>
      </tr>
    `).join('') || '<tr><td colspan="4" style="text-align:center;padding:20px;color:var(--text-muted)">스캔 이력 없음</td></tr>';
    _renderScanFooter(history);
  }

  function quickAction(action) {
    const inp = document.getElementById('scan-input');
    const barcode = inp?.value.trim() || lastBarcode;
    if (!barcode) { window.showToast?.('warning', '바코드를 먼저 스캔하세요'); return; }
    processBarcode(barcode, action);
    if (inp) inp.value = '';
  }


  function _renderScanFooter(hist) {
    var foot = document.getElementById('scan-history-footer');
    if (!foot) {
      var tb = document.getElementById('scan-history-tbody');
      if (!tb) return;
      var tbl = tb.closest ? tb.closest('table') : tb.parentElement;
      if (!tbl || !tbl.parentNode) return;
      foot = document.createElement('div');
      foot.id = 'scan-history-footer';
      foot.style.cssText = 'padding:5px 12px;background:var(--bg-hover);border-top:1px solid var(--panel-border);font-size:12px;flex-shrink:0;';
      tbl.parentNode.insertBefore(foot, tbl.nextSibling);
    }
    var s = 'display:inline-block;padding:2px 14px;margin-right:8px;background:rgba(79,195,247,0.13);border-radius:6px;font-size:12px;color:var(--accent,#4fc3f7);font-weight:700;';
    var shown = hist.slice(0, 20);
    var ok  = shown.filter(function(h){return h.success;}).length;
    var ng  = shown.length - ok;
    var _sg = 'display:inline-block;padding:2px 10px;margin-right:6px;border-radius:6px;font-size:12px;font-weight:700;';
    foot.innerHTML =
        '<span style="' + s + '">스캔 ' + shown.length + '건 / 전체 ' + hist.length + '건</span>'
      + '<span style="' + _sg + 'background:rgba(34,197,94,0.2);color:#22c55e;">✅ 성공 ' + ok + '</span>'
      + (ng > 0 ? '<span style="' + _sg + 'background:rgba(244,67,54,0.2);color:#f44336;">❌ 실패 ' + ng + '</span>' : '');
  }

  return { init, processBarcode, quickAction, renderHistory };
})();
