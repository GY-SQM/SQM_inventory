/* =======================================================================
   SQM Inventory - sqm-util-dbg.js — 화면 우측 하단 디버그 로그 패널 (F8 토글)
   Extracted from sqm-inline.js (Phase B-S4) — 2026-05-23
   Source: sqm-inline.js (현 line 133-198) + window 노출 line 210
   ======================================================================= */
(function () {
  'use strict';
  if (window.__SQM_UTIL_DBG_INSTALLED__) return;
  window.__SQM_UTIL_DBG_INSTALLED__ = true;

  /* ===================================================
     0. ON-SCREEN DEBUG LOG PANEL
     F12 없이 화면 우측 하단에서 직접 확인
     F8 토글 / 기본: 숨김 (Ctrl+Shift+D → 알캡처 충돌로 F8 변경)
     =================================================== */
  var _dbgLogs = [];
  var _dbgMax  = 30;
  var _dbgEl   = null;

  function dbgLog(icon, label, detail, color) {
    var ts = new Date().toTimeString().slice(0,8);
    _dbgLogs.push({ts:ts, icon:icon, label:label, detail:detail, color:color||'#aaa'});
    if (_dbgLogs.length > _dbgMax) _dbgLogs.shift();
    _dbgRefresh();
  }

  function _dbgRefresh() {
    if (!_dbgEl || !_dbgEl.__body) return;
    _dbgEl.__body.innerHTML = _dbgLogs.slice().reverse().map(function(r){
      return '<div style="padding:2px 0;border-bottom:1px solid #222;color:'+r.color+'">'+
        '<span style="opacity:.6;font-size:10px">'+r.ts+'</span> '+
        r.icon+' <b>'+escapeHtml(r.label)+'</b>'+
        (r.detail ? '<div style="font-size:10px;color:#888;padding-left:8px">'+escapeHtml(String(r.detail).slice(0,120))+'</div>' : '')+
        '</div>';
    }).join('');
  }

  function _dbgBuild() {
    var wrap = document.createElement('div');
    wrap.id = 'sqm-debug-panel';
    wrap.style.cssText = [
      'position:fixed','bottom:8px','right:8px','width:340px','z-index:99999',
      'font-family:monospace','font-size:11px','border-radius:6px',
      'box-shadow:0 2px 12px rgba(0,0,0,.6)','display:none'
    ].join(';');

    var hdr = document.createElement('div');
    hdr.style.cssText = 'background:#1a1a2e;color:#00e5ff;padding:4px 8px;border-radius:6px 6px 0 0;display:flex;align-items:center;gap:6px;cursor:pointer;user-select:none';
    hdr.innerHTML = '<span>🔍 SQM Debug Log</span><span style="font-size:10px;opacity:.6">(F8 토글)</span><button id="sqm-dbg-clear" style="margin-left:auto;background:#c00;color:#fff;border:none;border-radius:3px;padding:0 6px;cursor:pointer;font-size:10px">Clear</button>';

    var body = document.createElement('div');
    body.style.cssText = 'background:#0d0d1a;color:#ccc;padding:6px;max-height:260px;overflow-y:auto;border-radius:0 0 6px 6px';

    wrap.appendChild(hdr);
    wrap.appendChild(body);
    document.body.appendChild(wrap);

    wrap.__body = body;
    _dbgEl = wrap;

    hdr.querySelector('#sqm-dbg-clear').addEventListener('click', function(e){
      e.stopPropagation();
      _dbgLogs = [];
      _dbgRefresh();
    });

    // F8 토글 (Ctrl+Shift+D 는 알캡처 전역 단축키 충돌)
    document.addEventListener('keydown', function(e){
      if (e.key==='F8') {
        wrap.style.display = (wrap.style.display==='none') ? 'block' : 'none';
      }
    });

    dbgLog('🟢','Debug panel ready','F8 키로 토글 (Ctrl+Shift+D 알캡처 충돌 → F8 변경)','#4caf50');
  }

  // 글로벌 노출 (sqm-inline.js 의 기존 호출 호환)
  window.dbgLog = dbgLog;
})();
