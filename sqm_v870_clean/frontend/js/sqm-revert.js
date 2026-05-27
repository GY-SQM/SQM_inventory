/* sqm-revert.js — AVAILABLE→PENDING 되돌리기 패치 (v20260512) */
(function patchRevert() {
  'use strict';
  if (window.__SQM_REVERT_PATCHED__) return;
  window.__SQM_REVERT_PATCHED__ = true;

  /* ── revertToPending 확인 모달 ─────────────────────────────── */
  window.revertToPending = function(lot) {
    if (!lot) return;
    var ov = document.createElement('div');
    ov.id = 'revert-pending-overlay';
    ov.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:10000;display:flex;align-items:center;justify-content:center';
    var box = document.createElement('div');
    box.style.cssText = 'background:var(--surface,#1e293b);border:1px solid var(--border,#334155);border-radius:12px;padding:24px;min-width:320px;max-width:400px';
    var h3 = document.createElement('h3');
    h3.style.cssText = 'margin:0 0 12px;font-size:15px;color:var(--text)';
    h3.textContent = '↩️ PENDING으로 되돌리기';
    var desc = document.createElement('p');
    desc.style.cssText = 'margin:0 0 16px;font-size:13px;color:var(--text-muted)';
    var strong = document.createElement('strong');
    strong.style.cssText = 'color:var(--text);font-family:monospace';
    strong.textContent = lot;
    desc.appendChild(document.createTextNode('입고 취소: '));
    desc.appendChild(strong);
    desc.appendChild(document.createTextNode(' → PENDING 복구 (inbound_date 초기화)'));
    var btnRow = document.createElement('div');
    btnRow.style.cssText = 'display:flex;gap:8px;justify-content:flex-end';
    var cancelBtn = document.createElement('button');
    cancelBtn.className = 'btn btn-ghost';
    cancelBtn.textContent = '취소';
    cancelBtn.onclick = function() { ov.remove(); };
    var confirmBtn = document.createElement('button');
    confirmBtn.className = 'btn btn-primary';
    confirmBtn.style.background = '#f59e0b';
    confirmBtn.textContent = '확인 — PENDING 복구';
    confirmBtn.dataset.lot = lot;
    confirmBtn.onclick = function() {
      var l = this.dataset.lot;
      ov.remove();
      window.apiPost('/api/inbound/revert/' + encodeURIComponent(l), {})
        .then(function() {
          window.showToast('success', '↩️ ' + l + ' → PENDING 복구 완료');
          if (window.renderPage) window.renderPage('available');
        })
        .catch(function(e) { window.showToast('error', '실패: ' + (e.message || e)); });
    };
    btnRow.appendChild(cancelBtn);
    btnRow.appendChild(confirmBtn);
    box.appendChild(h3);
    box.appendChild(desc);
    box.appendChild(btnRow);
    ov.appendChild(box);
    document.body.appendChild(ov);
    setTimeout(function() { cancelBtn.focus(); }, 50); // Enter 실수 방지
  };

  /* ── showInvActionMenu 패치: available 라우트에서만 항목 추가 ── */
  window.showInvActionMenu = function(btn) {
    var lot = btn.dataset.lot || '';
    var route = window.getCurrentRoute ? window.getCurrentRoute() : '';
    var items = [
      { icon: '📋', label: 'LOT 상세 보기',  kbd: 'Enter',         fn: function() { window.showLotDetail(lot); } },
      { icon: '📄', label: 'LOT 번호 복사',  kbd: 'Ctrl+C',        fn: function() { window.invCopyLot(lot); } },
      { icon: '📑', label: '행 전체 복사',   kbd: 'Ctrl+Shift+C',  fn: function() { window.invCopyLot(lot); } },
      '-',
      { icon: '🚀', label: '즉시 출고 진입', kbd: 'O', color: '#42a5f5', fn: function() { window.invQuickOutbound(lot); } },
      { icon: '🔄', label: '반품 진입',      kbd: 'R', color: '#ef5350', fn: function() { window.invQuickReturn(lot); } },
      { icon: '📊', label: 'LOT 이력 보기', kbd: 'H', color: '#66bb6a', fn: function() { window.invShowLotHistory(lot); } }
    ];
    if (route === 'available') {
      items.push('-');
      items.push({ icon: '↩️', label: 'PENDING으로 되돌리기', color: '#f59e0b', fn: function() { window.revertToPending(lot); } });
    }
    window._openContextMenu(btn, items);
  };

  console.log('[SQM] sqm-revert.js patch OK — route-aware menu active');

  if (!window.__SQM_STATUS_REVERT_LOADER__) {
    window.__SQM_STATUS_REVERT_LOADER__ = true;
    var sr = document.createElement('script');
    sr.src = 'js/sqm-status-revert.js?v=20260525a';
    sr.defer = true;
    document.head.appendChild(sr);
  }
})();
