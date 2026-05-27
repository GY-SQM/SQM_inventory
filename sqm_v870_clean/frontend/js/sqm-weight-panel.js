/* sqm-weight-panel.js — sqm-inline.js 2단계 분리: 무게 패널 + 분리창 헬퍼 */
(function () {
  'use strict';
  var apiGet = function() { return window.apiGet.apply(window, arguments); };
  /* ── 분리 창 헬퍼 ───────────────────────────────────────────────── */
  /* ── ⚖️ 무게 패널: 재고 가치(current) + PICKED 포함 토글 ── */
  var _weightCache = { availMT: 0, pickedMT: 0, inclPicked: false };

  function _updateWeightBadge() {
    Promise.all([
      apiGet('/api/dashboard/stats').catch(function(){ return {}; }),
      apiGet('/api/outbound/picked-summary').catch(function(){ return []; })
    ]).then(function(results) {
      var stats = results[0];
      var pickedRows = Array.isArray(results[1]) ? results[1] : (results[1].data || []);
      var d = stats.data || stats || {};
      // total_weight_mt = 전체 재고 (PENDING 제외, PICKED 포함)
      var totalMT = parseFloat(d.total_weight_mt || 0);
      var pickedKg = pickedRows.reduce(function(s, r) { return s + (parseFloat(r.total_kg) || 0); }, 0);
      var pickedMT = Math.round(pickedKg) / 1000;
      var availMT = Math.round((totalMT - pickedMT) * 1000) / 1000;
      _weightCache.availMT = availMT;
      _weightCache.pickedMT = pickedMT;
      var label = document.getElementById('weight-nav-label');
      var badge = document.getElementById('weight-picked-badge');
      var pickedNav = document.getElementById('weight-picked-nav');
      if (label) label.textContent = (_weightCache.inclPicked ? totalMT : availMT).toFixed(3) + ' MT';
      if (badge) badge.style.display = pickedMT > 0 ? 'inline' : 'none';
      if (pickedNav) pickedNav.textContent = pickedMT.toFixed(3);
    }).catch(function() {});
  }

  window.showWeightPanel = function() {
    var old = document.getElementById('sqm-weight-panel');
    if (old) { old.remove(); return; }
    var panel = document.createElement('div');
    panel.id = 'sqm-weight-panel';
    panel.style.cssText = 'position:fixed;top:50px;right:16px;z-index:8000;background:var(--surface,#1e293b);'
      + 'border:1px solid var(--border,#334155);border-radius:10px;padding:16px 20px;min-width:260px;'
      + 'box-shadow:0 4px 24px rgba(0,0,0,0.5);';
    var availMT = _weightCache.availMT;
    var pickedMT = _weightCache.pickedMT;
    var inclPicked = _weightCache.inclPicked;
    var header = document.createElement('div');
    header.style.cssText = 'display:flex;align-items:center;gap:8px;margin-bottom:14px';
    var title = document.createElement('span');
    title.style.cssText = 'font-size:14px;font-weight:700;color:var(--text);flex:1';
    title.textContent = '\u2696\ufe0f \ubb34\uac8c \ud604\ud669';
    var closeBtn = document.createElement('button');
    closeBtn.style.cssText = 'background:transparent;border:none;color:var(--text-muted);cursor:pointer;font-size:16px;line-height:1;padding:0';
    closeBtn.textContent = '\u00d7';
    closeBtn.onclick = function() { panel.remove(); };
    header.appendChild(title);
    header.appendChild(closeBtn);
    var row1 = document.createElement('div');
    row1.style.cssText = 'margin-bottom:8px;font-size:13px;color:var(--text-muted)';
    row1.innerHTML = '\uc7ac\uace0 \uac00\uce58 (AVAILABLE+RESERVED): <b style="color:var(--text);font-size:15px">'
      + availMT.toFixed(3) + ' MT</b>';
    var row2 = document.createElement('div');
    row2.style.cssText = 'margin-bottom:12px;font-size:13px;color:var(--text-muted)';
    row2.innerHTML = 'PICKED (\ucc3d\uace0 \ub0b4 \ub300\uae30): <b style="color:#fb923c;font-size:15px">'
      + pickedMT.toFixed(3) + ' MT</b>';
    var cbRow = document.createElement('label');
    cbRow.style.cssText = 'display:flex;align-items:center;gap:8px;cursor:pointer;font-size:13px;color:var(--text-muted);'
      + 'padding:8px 10px;background:var(--bg,#0f172a);border-radius:6px;border:1px solid var(--border,#334155);margin-bottom:10px';
    var cb = document.createElement('input');
    cb.type = 'checkbox';
    cb.checked = inclPicked;
    cb.onchange = function() {
      _weightCache.inclPicked = cb.checked;
      _updateWeightBadge();
      var navLabel = document.getElementById('weight-nav-label');
      if (navLabel) {
        var disp = cb.checked ? (_weightCache.availMT + _weightCache.pickedMT) : _weightCache.availMT;
        navLabel.textContent = disp.toFixed(3) + ' MT';
      }
      total.textContent = (cb.checked ? availMT + pickedMT : availMT).toFixed(3) + ' MT';
    };
    cbRow.appendChild(cb);
    cbRow.appendChild(document.createTextNode('PICKED \ud3ec\ud568 (\ucc3d\uace0 \uc2e4\ubb3c \uc810\uac80\uc6a9)'));
    var totalLabel = document.createElement('div');
    totalLabel.style.cssText = 'font-size:11px;color:var(--text-muted);padding-top:8px;border-top:1px solid var(--border,#334155)';
    totalLabel.textContent = '\ud569\uacc4: ';
    var total = document.createElement('b');
    total.style.color = 'var(--text)';
    total.textContent = (inclPicked ? availMT + pickedMT : availMT).toFixed(3) + ' MT';
    totalLabel.appendChild(total);
    panel.appendChild(header);
    panel.appendChild(row1);
    panel.appendChild(row2);
    panel.appendChild(cbRow);
    panel.appendChild(totalLabel);
    document.body.appendChild(panel);
    _updateWeightBadge();
    setTimeout(function() {
      document.addEventListener('click', function rm(e) {
        if (!panel.contains(e.target) && e.target.id !== 'weight-panel-btn') {
          panel.remove();
          document.removeEventListener('click', rm);
        }
      });
    }, 50);
  };

  window._updateWeightBadge = _updateWeightBadge;

  window._sqmDetachAiChat = function() {
    var API = window.SQM_API_BASE || window.location.origin || '';
    var url = API + '/frontend/detached/ai_chat.html';
    if (window.pywebview && window.pywebview.api && window.pywebview.api.open_detached_window) {
      window.pywebview.api.open_detached_window('ai_chat', 'SQM AI Chat', url, 900, 650);
    } else {
      window.open(url, 'sqm_ai_chat', 'width=900,height=650');
    }
    var panel = document.getElementById('sqm-ai-chat-panel');
    if (panel) panel.style.display = 'none';
  };

  window._sqmDetachIntegrity = function() {
    var API = window.SQM_API_BASE || window.location.origin || '';
    var url = API + '/frontend/detached/integrity.html';
    if (window.pywebview && window.pywebview.api && window.pywebview.api.open_detached_window) {
      window.pywebview.api.open_detached_window('integrity', '정합성 검사', url, 1000, 700);
    } else {
      window.open(url, 'sqm_integrity', 'width=1000,height=700');
    }
  };

})();
