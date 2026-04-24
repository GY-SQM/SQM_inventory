/* =======================================================================
   SQM Inventory v864.3 - sqm-inline.js (Phase 5 + Hotfix: menu click + debug panel)
   Rebuilt: 2026-04-21  Ruby (Senior Software Architect)
   Hotfix:  2026-04-22  menu dropdown .menu-btn selector fix + on-screen debug log
   ======================================================================= */
(function () {
  'use strict';

  var API = 'http://127.0.0.1:8765';

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

  /* ===================================================
     1. UTILITIES
     =================================================== */

  /** 범용 데이터 추출 — 모든 API 응답 패턴 대응
   *  {data: {items:[]}}  → items
   *  {data: {rows:[]}}   → rows
   *  {data: []}           → data
   *  []                   → 그대로
   *  그 외                → []
   */
  function extractRows(res) {
    if (Array.isArray(res)) return res;
    if (!res) return [];
    var d = res.data;
    if (Array.isArray(d)) return d;
    if (d && Array.isArray(d.items)) return d.items;
    if (d && Array.isArray(d.rows)) return d.rows;
    return [];
  }

  /* ===================================================
     1a. TABLE SORT — 컬럼 헤더 클릭으로 정렬 (v864.2 동일)
     사용법: <th> 에 자동 바인딩, 숫자/문자/날짜 자동 감지
     =================================================== */
  function enableTableSort(tableEl) {
    if (!tableEl || tableEl.dataset._sortBound) return;
    tableEl.dataset._sortBound = '1';
    var headers = tableEl.querySelectorAll('thead th');
    headers.forEach(function(th, colIdx) {
      th.style.cursor = 'pointer';
      th.style.userSelect = 'none';
      th.title = 'Click to sort';
      th.addEventListener('click', function() {
        var tbody = tableEl.querySelector('tbody');
        if (!tbody) return;
        var rows = Array.prototype.slice.call(tbody.querySelectorAll('tr'));
        var asc = th.dataset._sortDir !== 'asc';
        // 모든 th 리셋
        headers.forEach(function(h){ h.dataset._sortDir=''; h.textContent=h.textContent.replace(/ [▲▼]/g,''); });
        th.dataset._sortDir = asc ? 'asc' : 'desc';
        th.textContent = th.textContent + (asc ? ' ▲' : ' ▼');
        rows.sort(function(a, b) {
          var ca = (a.children[colIdx]||{}).textContent||'';
          var cb = (b.children[colIdx]||{}).textContent||'';
          // 숫자 감지
          var na = parseFloat(ca.replace(/,/g,'')), nb = parseFloat(cb.replace(/,/g,''));
          if (!isNaN(na) && !isNaN(nb)) return asc ? na-nb : nb-na;
          return asc ? ca.localeCompare(cb) : cb.localeCompare(ca);
        });
        rows.forEach(function(r){ tbody.appendChild(r); });
      });
    });
  }

  /* 페이지 렌더링 후 자동으로 테이블 정렬 바인딩 */
  var _sortObserver = new MutationObserver(function() {
    document.querySelectorAll('.data-table').forEach(enableTableSort);
  });
  _sortObserver.observe(document.documentElement, {childList:true, subtree:true});

  /* ===================================================
     1b. KEYBOARD SHORTCUTS (v864.2 동일)
     =================================================== */

  /* ── [UX] ESC = 현재 열린 창 닫기 (전역)
     우선순위: 컨텍스트 메뉴 → 모달 → 최상위 메뉴 드롭다운 → 입력 포커스
     input/textarea/select 안에서도 작동 (모달 닫기 우선).
     최상위 스코프에서 ESC 두 번(1.5초 이내) = 앱 종료 확인 다이얼로그. ── */
  var _escLastAt = 0;
  var EXIT_DOUBLE_ESC_WINDOW_MS = 1500;
  document.addEventListener('keydown', function(e){
    if (e.key !== 'Escape' && e.key !== 'Esc') return;

    /* 1순위: 컨텍스트 메뉴 (우클릭 팝업) */
    var ctx = document.querySelector('.ctx-menu');
    if (ctx) { ctx.remove(); e.preventDefault(); _escLastAt = 0; return; }

    /* 2순위: 모달 (데이터 모달 / 정보 모달) */
    var modal = document.getElementById('sqm-modal');
    if (modal && modal.style.display !== 'none' && modal.style.display !== '') {
      modal.style.display = 'none';
      e.preventDefault();
      _escLastAt = 0;
      return;
    }

    /* 3순위: 열린 상단 메뉴 드롭다운 (.menu-btn.open) */
    var openMenus = document.querySelectorAll('.menu-btn.open');
    if (openMenus.length) {
      openMenus.forEach(function(m){ m.classList.remove('open'); });
      if (document.activeElement && document.activeElement.blur) {
        try { document.activeElement.blur(); } catch(err) {}
      }
      e.preventDefault();
      _escLastAt = 0;
      return;
    }

    /* 4순위: 활성 input/textarea 포커스 해제 (편집 중단) */
    var ae = document.activeElement;
    if (ae && (ae.tagName === 'INPUT' || ae.tagName === 'TEXTAREA' || ae.isContentEditable)) {
      try { ae.blur(); } catch(err) {}
      _escLastAt = 0;
      return;
    }

    /* 5순위: 아무것도 열려있지 않음 — 더블 ESC 감지 → 앱 종료 확인 */
    var now = Date.now();
    if ((now - _escLastAt) < EXIT_DOUBLE_ESC_WINDOW_MS) {
      _escLastAt = 0;
      e.preventDefault();
      if (confirm('앱을 종료하시겠습니까?')) {
        if (window.pywebview && window.pywebview.api && window.pywebview.api.exit_app) {
          window.pywebview.api.exit_app();
        } else {
          window.close();
        }
      }
    } else {
      _escLastAt = now;
      if (typeof showToast === 'function') {
        showToast('info', 'ESC 한 번 더 = 앱 종료', 1500);
      }
    }
  });

  /* ── [UX] 모달 Enter = primary 버튼 클릭 & Tab = 모달 내부 포커스 순환 ── */
  document.addEventListener('keydown', function(e){
    var modal = document.getElementById('sqm-modal');
    if (!modal || modal.style.display === 'none' || modal.style.display === '') return;

    /* Enter — primary 버튼 자동 클릭 (단, textarea 안에서는 줄바꿈 허용) */
    if (e.key === 'Enter' && !e.shiftKey && !e.ctrlKey && !e.altKey) {
      if (e.target && e.target.tagName === 'TEXTAREA') return;         /* 줄바꿈 */
      if (e.target && e.target.tagName === 'BUTTON') return;           /* 브라우저 기본 */
      if (e.target && e.target.tagName === 'SELECT') return;           /* 선택 확정 */
      /* 우선 순위: .btn-primary > .btn[type=submit] > 모달 내 첫 번째 활성 버튼 */
      var primary =
        modal.querySelector('.btn-primary:not([disabled])') ||
        modal.querySelector('button[type="submit"]:not([disabled])');
      if (primary) {
        e.preventDefault();
        primary.click();
      }
      return;
    }

    /* [Sprint 1-2-D] Ctrl+Z / Ctrl+Y — 모달 안 편집 Undo/Redo
       OneStop Inbound 미리보기가 렌더된 상태에서만 작동 */
    if (e.ctrlKey && !e.altKey && typeof _onestopState !== 'undefined' && _onestopState.parsed) {
      /* input 안에서는 기본 undo 동작 허용 */
      if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA')) {
        /* Ctrl+Z 는 input 자체 undo 가 우선, Ctrl+Shift+Z 만 커스텀 redo */
        if (e.key === 'z' && e.shiftKey && typeof window.onestopRedo === 'function') {
          e.preventDefault();
          window.onestopRedo();
        }
        return;
      }
      if (e.key === 'z' && !e.shiftKey && typeof window.onestopUndo === 'function') {
        e.preventDefault();
        window.onestopUndo();
        return;
      }
      if ((e.key === 'y' || (e.key === 'z' && e.shiftKey)) && typeof window.onestopRedo === 'function') {
        e.preventDefault();
        window.onestopRedo();
        return;
      }
    }

    /* Tab — 모달 내부 포커스 트랩 (마지막 → 첫 번째, Shift+Tab 시 반대) */
    if (e.key === 'Tab') {
      var focusables = modal.querySelectorAll(
        'button:not([disabled]), input:not([disabled]):not([type="hidden"]), ' +
        'select:not([disabled]), textarea:not([disabled]), a[href], ' +
        '[tabindex]:not([tabindex="-1"])'
      );
      if (focusables.length === 0) return;
      var first = focusables[0];
      var last  = focusables[focusables.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
  });

  document.addEventListener('keydown', function(e) {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') return;
    var key = (e.ctrlKey?'C-':'') + (e.shiftKey?'S-':'') + (e.altKey?'A-':'') + e.key;
    switch(key) {
      case 'C-r': case 'F5': e.preventDefault(); renderPage(_currentRoute||'dashboard'); break;
      case 'C-1': e.preventDefault(); renderPage('inventory'); break;
      case 'C-2': e.preventDefault(); renderPage('allocation'); break;
      case 'C-3': e.preventDefault(); renderPage('picked'); break;
      case 'C-4': e.preventDefault(); renderPage('outbound'); break;
      case 'C-5': e.preventDefault(); renderPage('return'); break;
      case 'C-6': e.preventDefault(); renderPage('move'); break;
      case 'C-7': e.preventDefault(); renderPage('dashboard'); break;
      case 'C-8': e.preventDefault(); renderPage('log'); break;
      case 'C-9': e.preventDefault(); renderPage('scan'); break;
      case 'C-b': e.preventDefault(); dispatchAction('onOnBackup'); break;
      case 'C-e': e.preventDefault(); dispatchAction('onExport'); break;
      case 'C-i': e.preventDefault(); dispatchAction('onIntegrityCheck'); break;
    }
  });

  /* ===================================================
     1c. CONTEXT MENU — 테이블 행 우클릭 (v864.2 동일)
     =================================================== */
  var _ctxMenu = null;
  function showContextMenu(e, items) {
    e.preventDefault();
    hideContextMenu();
    var m = document.createElement('div');
    m.className = 'ctx-menu';
    m.style.cssText = 'position:fixed;z-index:9999;background:var(--panel-bg);border:1px solid var(--panel-border);border-radius:6px;padding:4px 0;min-width:160px;box-shadow:0 4px 16px rgba(0,0,0,.4);font-size:13px;';
    m.style.left = e.clientX+'px';
    m.style.top = e.clientY+'px';
    items.forEach(function(it){
      if (it === '---') { var hr=document.createElement('hr'); hr.style.cssText='margin:4px 8px;border:0;border-top:1px solid var(--panel-border)'; m.appendChild(hr); return; }
      var d = document.createElement('div');
      d.style.cssText = 'padding:6px 16px;cursor:pointer;color:var(--fg);white-space:nowrap;';
      d.textContent = it.label;
      d.addEventListener('mouseenter', function(){ d.style.background='var(--btn-hover)'; });
      d.addEventListener('mouseleave', function(){ d.style.background=''; });
      d.addEventListener('click', function(){ hideContextMenu(); if(it.action) it.action(); });
      m.appendChild(d);
    });
    document.body.appendChild(m);
    _ctxMenu = m;
    // 화면 밖으로 넘어가면 보정
    var r=m.getBoundingClientRect();
    if(r.right>window.innerWidth) m.style.left=(window.innerWidth-r.width-4)+'px';
    if(r.bottom>window.innerHeight) m.style.top=(window.innerHeight-r.height-4)+'px';
  }
  function hideContextMenu(){ if(_ctxMenu){ _ctxMenu.remove(); _ctxMenu=null; } }
  document.addEventListener('click', hideContextMenu);
  document.addEventListener('contextmenu', function(e){
    var tr = e.target.closest('.data-table tbody tr');
    if (!tr) return;
    var cells = tr.querySelectorAll('td');
    var lotCell = tr.querySelector('td:nth-child(1)') || {};
    var lot = (lotCell.textContent||'').trim();
    showContextMenu(e, [
      {label:'📋 LOT 상세 보기', action:function(){ if(window.showLotDetail) window.showLotDetail(lot); else showToast('info','LOT: '+lot); }},
      {label:'📤 Excel 내보내기', action:function(){ dispatchAction('onExport'); }},
      '---',
      {label:'📊 재고 현황', action:function(){ renderPage('inventory'); }},
      {label:'🔄 새로고침', action:function(){ renderPage(_currentRoute||'dashboard'); }},
    ]);
  });

  function escapeHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (m) {
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m];
    });
  }

  function ensureToastContainer() {
    var c = document.getElementById('toast-container');
    if (!c) {
      c = document.createElement('div');
      c.id = 'toast-container';
      document.body.appendChild(c);
    }
    return c;
  }

  var TOAST_ICONS = {success:'&#x2705;', info:'&#x2139;&#xFE0F;', warning:'&#x26A0;&#xFE0F;', error:'&#x274C;'};

  function showToast(type, message, duration) {
    if (!['success','info','warning','error'].includes(type)) type = 'info';
    duration = duration || 3000;
    var c = ensureToastContainer();
    var t = document.createElement('div');
    t.className = 'toast ' + type;
    t.innerHTML = '<span>' + (TOAST_ICONS[type]||'') + '</span><span>' + escapeHtml(message) + '</span>';
    c.appendChild(t);
    setTimeout(function () {
      t.style.opacity = '0';
      t.style.transition = 'opacity 300ms';
      setTimeout(function () { if (t.parentNode) t.parentNode.removeChild(t); }, 300);
    }, duration);
  }
  window.showToast = showToast;

  /* ===================================================
     2. API CLIENT
     =================================================== */
  var DEFAULT_TIMEOUT = 8000;

  function apiCall(method, path, body, opts) {
    opts = opts || {};
    var timeout = opts.timeout || DEFAULT_TIMEOUT;
    var retries = (opts.retries !== undefined) ? opts.retries : 2;
    var url = (path.indexOf('http') === 0) ? path : API + path;
    var fetchOpts = {
      method: method.toUpperCase(),
      headers: {'Content-Type':'application/json'}
    };
    if (body !== null && body !== undefined &&
        ['POST','PUT','DELETE'].includes(fetchOpts.method)) {
      fetchOpts.body = JSON.stringify(body);
    }
    // Debug log: request
    dbgLog('🔵', method.toUpperCase()+' '+path, null, '#64b5f6');
    function attempt(n) {
      var timer;
      var timeoutP = new Promise(function(_, rej) {
        timer = setTimeout(function(){ var e = new Error('timeout'); e.status=0; rej(e); }, timeout);
      });
      return Promise.race([fetch(url, fetchOpts), timeoutP])
        .then(function(res) {
          clearTimeout(timer);
          if (!res.ok) {
            return res.json().catch(function(){return null;}).then(function(detail){
              var e = new Error('HTTP ' + res.status);
              e.status = res.status; e.detail = detail;
              // Debug log: HTTP error
              var msg = (detail && (detail.detail||detail.message)) ? (detail.detail||detail.message) : '';
              dbgLog(res.status===501?'🟡':'🔴', 'HTTP '+res.status+' '+path, msg||'', res.status===501?'#ffa726':'#ef5350');
              throw e;
            });
          }
          // Debug log: success
          dbgLog('🟢', 'OK '+path, null, '#66bb6a');
          return res.json().catch(function(){return {};});
        })
        .catch(function(e) {
          clearTimeout(timer);
          if (e.status === 0) dbgLog('🔴','TIMEOUT '+path,'백엔드 응답 없음 (8초)','#ef5350');
          if (e.status === 501 || e.status === 404) throw e;
          if (n < retries) {
            return new Promise(function(r){ setTimeout(r, 500 * Math.pow(2,n)); })
              .then(function(){ return attempt(n+1); });
          }
          throw e;
        });
    }
    return attempt(0);
  }

  function apiGet(path, opts) { return apiCall('GET', path, null, opts); }
  function apiPost(path, body, opts) { return apiCall('POST', path, body, opts); }

  window.apiCall = apiCall;
  window.apiGet  = apiGet;
  window.apiPost = apiPost;

  /* ===================================================
     3. STATE / THEME
     =================================================== */
  function getStore() {
    try {
      localStorage.setItem('__probe__','1');
      localStorage.removeItem('__probe__');
      return localStorage;
    } catch {}
    try { return sessionStorage; } catch {}
    var m = {};
    return { getItem:function(k){return m[k]||null;},
             setItem:function(k,v){m[k]=String(v);},
             removeItem:function(k){delete m[k];} };
  }

  function applyTheme() {
    var store = getStore();
    var theme = store.getItem('sqm_theme') || 'dark';
    document.documentElement.setAttribute('data-theme', theme);
    var vm = store.getItem('sqm_view_mode') || 'mt';
    document.documentElement.setAttribute('data-view-mode', vm);
  }

  function toggleTheme() {
    var cur = document.documentElement.getAttribute('data-theme') || 'dark';
    var next = cur === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    try { getStore().setItem('sqm_theme', next); } catch {}
    showToast('info', (next === 'dark' ? '&#x1F319; Dark' : '&#x2600;&#xFE0F; Light') + ' theme');
  }

  /* ===================================================
     4. MENU CLOSE
     =================================================== */
  var _menuJustOpened = false;  // PyWebView/WebView2: stopPropagation 우회 방지 플래그

  function closeAllMenus() {
    // Fix: HTML uses .menu-btn[data-menu], not .menu-item — add both for safety
    document.querySelectorAll('.menu-btn.open').forEach(function(el){
      el.classList.remove('open');
    });
    document.querySelectorAll('.menu-dropdown.open,.menu-dropdown.active').forEach(function(el){
      el.classList.remove('open'); el.classList.remove('active');
    });
    document.querySelectorAll('.menu-item.active,.nav-item.open').forEach(function(el){
      el.classList.remove('active'); el.classList.remove('open');
    });
  }

  /* ===================================================
     5. ROUTER
     =================================================== */
  var _currentRoute = null;

  function showPage(route) {
    var dash = document.getElementById('dashboard-container');
    var page = document.getElementById('page-container');
    if (route === 'dashboard') {
      if (dash) { dash.style.display = 'block'; dash.style.removeProperty('display'); }
      if (page) page.style.display = 'none';
    } else {
      if (dash) dash.style.display = 'none';
      /* PyWebView/WebView2: style.display='' 이 inline none을 못 제거하는 경우 있음 → block 명시 */
      if (page) {
        page.style.removeProperty('display');
        page.style.display = 'block';
      }
    }
    /* 치수 측정 — height 0이면 flex 레이아웃 문제 */
    setTimeout(function(){
      var r1 = page ? page.getBoundingClientRect() : null;
      var r2 = page && page.parentElement ? page.parentElement.getBoundingClientRect() : null;
      dbgLog('📐','page-container rect',
        'W='+Math.round(r1?r1.width:0)+' H='+Math.round(r1?r1.height:0)+
        ' | wrapper H='+Math.round(r2?r2.height:0), '#ff9800');
    }, 300);
    dbgLog('🖥️','showPage', 'route='+route+
      ' dash='+(dash?dash.style.display:'?')+
      ' page='+(page?page.style.display:'?'), '#ab47bc');
    document.querySelectorAll('[data-route]').forEach(function(el){
      el.classList.toggle('active', el.dataset.route === route);
    });
  }

  function renderPage(route) {
    _currentRoute = route;
    closeAllMenus();
    showPage(route);
    try { getStore().setItem('sqm_last_tab', route); } catch {}
    if (history.replaceState) history.replaceState(null,'','#' + route);
    switch (route) {
      case 'dashboard':  loadDashboard();     break;
      case 'inventory':  loadInventoryPage();  break;
      case 'allocation': loadAllocationPage(); break;
      case 'picked':     loadPickedPage();     break;
      case 'inbound':    loadInboundPage();    break;
      case 'outbound':   loadOutboundPage();   break;
      case 'return':     loadReturnPage();     break;
      case 'move':       loadMovePage();       break;
      case 'log':        loadLogPage();        break;
      case 'scan':       loadScanPage();       break;
      case 'tonbag':     loadTonbagPage();     break;
      default:           loadStubPage(route);  break;
    }
  }

  function loadStubPage(route) {
    var c = document.getElementById('page-container');
    if (c) c.innerHTML = '<div class="empty" style="padding:60px;text-align:center;color:var(--text-muted)">Preparing: ' + escapeHtml(route) + '</div>';
  }

  window.renderPage = renderPage;

  /* ===================================================
     6. DASHBOARD
     =================================================== */
  var _kpiTimer = null;

  function loadDashboard() {
    loadKpi();
    loadDashboardTables();
  }

  function loadKpi() {
    apiGet('/api/dashboard/kpi').then(function(res) {
      var d = res.data || res || {};
      function sv(id, v) {
        var el = document.getElementById(id);
        if (el) el.textContent = (v === null || v === undefined) ? '-' : String(v);
      }
      sv('kpi-inbound-val',        d.inbound_today   !== undefined ? d.inbound_today   : (d.inbound   || '-'));
      sv('kpi-outbound-today-val', d.outbound_today  !== undefined ? d.outbound_today  : (d.outbound  || '-'));
      sv('kpi-stock-lots-val',     d.stock_lots       !== undefined ? d.stock_lots      : (d.lots      || '-'));
      sv('kpi-unassigned-val',     d.unassigned_bags  !== undefined ? d.unassigned_bags : (d.unassigned|| '-'));
    }).catch(function(){});
  }

  function startKpiPolling() {
    if (_kpiTimer) clearInterval(_kpiTimer);
    _kpiTimer = setInterval(function(){
      if (_currentRoute === 'dashboard' && document.visibilityState !== 'hidden') loadKpi();
    }, 5000);
  }

  function loadDashboardTables() {
    apiGet('/api/dashboard/stats').then(function(res){
      var d = res.data || res || {};
      renderStatusCards(d.status_summary || {});
      renderProductMatrix(d.product_matrix || []);
      renderIntegrity(d.integrity || {});
    }).catch(function(){
      renderStatusCards({});
      renderProductMatrix([]);
      renderIntegrity({});
    });
  }

  function fmtN(v) {
    if (typeof v !== 'number') return (v == null ? '-' : v);
    return v.toLocaleString('ko-KR',{minimumFractionDigits:1,maximumFractionDigits:1});
  }
  function fmtW(kg) {
    if (typeof kg !== 'number') return '-';
    return (kg / 1000).toLocaleString('ko-KR',{minimumFractionDigits:2,maximumFractionDigits:2}) + ' MT';
  }

  /* -- 5단계 재고 상태 카드 -- */
  var STATUS_CARD_META = [
    {key:'available', label:'Available (판매가능)', icon:'\u2705', color:'#22c55e'},
    {key:'reserved',  label:'Reserved (배정)',      icon:'\uD83D\uDCCB', color:'#3b82f6'},
    {key:'picked',    label:'Picked (피킹)',        icon:'\uD83D\uDCE6', color:'#f59e0b'},
    {key:'outbound',  label:'Outbound (출고)',      icon:'\uD83D\uDE9A', color:'#ef4444'},
    {key:'return',    label:'Return (반품)',         icon:'\uD83D\uDD04', color:'#8b5cf6'}
  ];

  function renderStatusCards(summary) {
    var el = document.getElementById('dashboard-detail');
    if (!el) return;
    var html = '<div style="margin-bottom:16px"><h3 style="margin:0 0 8px 0;font-size:15px;color:var(--text-primary,#e0e0e0)">';
    html += '5\uB2E8\uACC4 \uC7AC\uACE0 \uD604\uD669</h3>';
    html += '<div style="display:flex;gap:10px;flex-wrap:wrap">';
    STATUS_CARD_META.forEach(function(m){
      var s = summary[m.key] || {lots:0, tonbags:0, weight_kg:0};
      html += '<div style="flex:1;min-width:160px;background:var(--bg-card,#1e1e2e);border-left:4px solid '+m.color+';border-radius:8px;padding:12px 14px">';
      html += '<div style="font-size:13px;color:'+m.color+';font-weight:700;margin-bottom:6px">'+m.icon+' '+m.label+'</div>';
      html += '<div style="font-size:22px;font-weight:700;color:var(--text-primary,#e0e0e0)">'+s.tonbags+'<span style="font-size:12px;font-weight:400;color:var(--text-muted,#888)"> \uD1A4\uBC31</span></div>';
      html += '<div style="font-size:12px;color:var(--text-muted,#888);margin-top:2px">'+s.lots+' LOT \u00B7 '+fmtW(s.weight_kg)+'</div>';
      html += '</div>';
    });
    html += '</div></div>';
    html += '<div id="dash-matrix-area"></div>';
    html += '<div id="dash-integrity-area"></div>';
    el.innerHTML = html;
  }

  /* -- 제품x상태 매트릭스 테이블 -- */
  function renderProductMatrix(rows) {
    var el = document.getElementById('dash-matrix-area');
    if (!el) return;
    if (!rows.length) {
      el.innerHTML = '<p style="color:var(--text-muted,#888);font-size:13px">\uC81C\uD488\uBCC4 \uB370\uC774\uD130 \uC5C6\uC74C</p>';
      return;
    }
    var totals = {available:0, reserved:0, picked:0, outbound:0, return_cnt:0, total:0};
    rows.forEach(function(r){
      totals.available += (r.available||0);
      totals.reserved  += (r.reserved||0);
      totals.picked    += (r.picked||0);
      totals.outbound  += (r.outbound||0);
      totals.return_cnt+= (r['return']||0);
      totals.total     += (r.total||0);
    });
    var html = '<h3 style="margin:16px 0 8px 0;font-size:15px;color:var(--text-primary,#e0e0e0)">';
    html += '\uC81C\uD488\u00D7\uC0C1\uD0DC \uB9E4\uD2B8\uB9AD\uC2A4 (\uD1A4\uBC31 \uC218)</h3>';
    html += '<div style="overflow-x:auto"><table class="sqm-table" style="width:100%;font-size:13px;border-collapse:collapse">';
    html += '<thead><tr style="background:var(--bg-header,#2a2a3e)">';
    html += '<th style="text-align:left;padding:6px 10px">\uC81C\uD488</th>';
    html += '<th style="padding:6px 8px;color:#22c55e">Available</th>';
    html += '<th style="padding:6px 8px;color:#3b82f6">Reserved</th>';
    html += '<th style="padding:6px 8px;color:#f59e0b">Picked</th>';
    html += '<th style="padding:6px 8px;color:#ef4444">Outbound</th>';
    html += '<th style="padding:6px 8px;color:#8b5cf6">Return</th>';
    html += '<th style="padding:6px 8px;font-weight:700">Total</th>';
    html += '</tr></thead><tbody>';
    rows.forEach(function(r){
      html += '<tr>';
      html += '<td style="text-align:left;padding:5px 10px;font-weight:600">'+escapeHtml(r.product)+'</td>';
      html += '<td style="text-align:right;padding:5px 8px">'+(r.available||0)+'</td>';
      html += '<td style="text-align:right;padding:5px 8px">'+(r.reserved||0)+'</td>';
      html += '<td style="text-align:right;padding:5px 8px">'+(r.picked||0)+'</td>';
      html += '<td style="text-align:right;padding:5px 8px">'+(r.outbound||0)+'</td>';
      html += '<td style="text-align:right;padding:5px 8px">'+(r['return']||0)+'</td>';
      html += '<td style="text-align:right;padding:5px 8px;font-weight:700">'+(r.total||0)+'</td>';
      html += '</tr>';
    });
    html += '<tr style="border-top:2px solid var(--border-color,#444);font-weight:700">';
    html += '<td style="text-align:left;padding:5px 10px">Total</td>';
    html += '<td style="text-align:right;padding:5px 8px">'+totals.available+'</td>';
    html += '<td style="text-align:right;padding:5px 8px">'+totals.reserved+'</td>';
    html += '<td style="text-align:right;padding:5px 8px">'+totals.picked+'</td>';
    html += '<td style="text-align:right;padding:5px 8px">'+totals.outbound+'</td>';
    html += '<td style="text-align:right;padding:5px 8px">'+totals.return_cnt+'</td>';
    html += '<td style="text-align:right;padding:5px 8px">'+totals.total+'</td>';
    html += '</tr></tbody></table></div>';
    el.innerHTML = html;
  }

  /* -- 정합성 요약 -- */
  function renderIntegrity(data) {
    var el = document.getElementById('dash-integrity-area');
    if (!el) return;
    if (!data || data.total_inbound_kg === undefined) {
      el.innerHTML = '';
      return;
    }
    var ok = data.ok;
    var color = ok ? '#22c55e' : '#ef4444';
    var icon  = ok ? '\u2705' : '\u26A0\uFE0F';
    var label = ok ? '\uC815\uD569\uC131 OK' : '\uBD88\uC77C\uCE58 \uAC10\uC9C0';
    var html = '<div style="margin-top:16px;padding:12px 16px;background:var(--bg-card,#1e1e2e);border-left:4px solid '+color+';border-radius:8px">';
    html += '<h3 style="margin:0 0 8px 0;font-size:15px;color:'+color+'">'+icon+' \uC815\uD569\uC131 \uAC80\uC99D \u2014 '+label+'</h3>';
    html += '<div style="display:flex;gap:24px;flex-wrap:wrap;font-size:13px;color:var(--text-primary,#e0e0e0)">';
    html += '<div>\uCD1D\uC785\uACE0: <b>'+fmtW(data.total_inbound_kg)+'</b></div>';
    html += '<div>\uD604\uC7AC\uC7AC\uACE0: <b>'+fmtW(data.current_stock_kg)+'</b></div>';
    html += '<div>\uCD9C\uACE0\uB204\uACC4: <b>'+fmtW(data.outbound_total_kg)+'</b></div>';
    html += '<div>\uCC28\uC774: <b style="color:'+color+'">'+fmtN(data.diff_kg)+' kg</b></div>';
    html += '</div></div>';
    el.innerHTML = html;
  }

  /* ===================================================
     7a. PAGE: Inventory
     =================================================== */
  /* =====================================================================
     [Sprint 1-6] Inventory 24열 풀 — v864-2 inventory_tab.py 매칭
     ─────────────────────────────────────────────────────────────────────
     INVENTORY_COLUMNS: 24개
       Always-on (20): No, LOT, SAP, BL, Product, Status, Balance, NET,
         Container, MXBG, Avail, Invoice, Ship, Arrival, ConReturn,
         Free, WH, Customs, Inbound, Outbound, Location
       Toggle (4): ↓Avail개, ↓Resv개, ↓Pick개, ↓Sold개 (default OFF)

     Features:
       ✅ Per-header 정렬 ▲▼
       ✅ Per-column 헤더 필터 row
       ✅ 상태 필터 chip row (전체/AVAILABLE/RESERVED/PICKED/SOLD/RETURN)
       ✅ 우클릭 컨텍스트 메뉴 (LOT 복사/Excel/Detail)
       ✅ ⚙️ 컬럼 토글 (4개 카운터 컬럼) + localStorage 영구화
       ✅ TotalFooter (Balance/NET/Inbound/Outbound MT 합계)
     ===================================================================== */
  var INV_COLUMNS = [
    { key: 'no',           label: '#',          align: 'right', mono: true,  type: 'num',  always: true },
    { key: 'lot',          label: 'LOT',        align: 'left',  mono: true,  type: 'str',  always: true,  accent: true },
    { key: 'sap',          label: 'SAP',        align: 'left',  mono: true,  type: 'str',  always: true },
    { key: 'bl',           label: 'BL',         align: 'left',  mono: true,  type: 'str',  always: true },
    { key: 'product',      label: 'Product',    align: 'left',  mono: false, type: 'str',  always: true,  tag: true },
    { key: 'status',       label: 'Status',     align: 'left',  mono: false, type: 'str',  always: true,  status: true },
    { key: 'balance',      label: 'Balance(MT)',align: 'right', mono: true,  type: 'num',  always: true,  fmt: 'mt', total: true },
    { key: 'net',          label: 'NET(MT)',    align: 'right', mono: true,  type: 'num',  always: true,  fmt: 'mt', total: true },
    { key: 'container',    label: 'Container',  align: 'left',  mono: true,  type: 'str',  always: true },
    { key: 'mxbg_pallet',  label: 'MXBG',       align: 'center',mono: true,  type: 'num',  always: true },
    { key: 'avail_bags',   label: 'Avail',      align: 'center',mono: true,  type: 'num',  always: true },
    /* 4 toggleable counters (default off, default key prefixed with `_count`) */
    { key: 'avail_count',  label: '↓Avail개',   align: 'right', mono: true,  type: 'num',  toggle: true,  defaultOn: false },
    { key: 'resv_count',   label: '↓Resv개',    align: 'right', mono: true,  type: 'num',  toggle: true,  defaultOn: false },
    { key: 'pick_count',   label: '↓Pick개',    align: 'right', mono: true,  type: 'num',  toggle: true,  defaultOn: false },
    { key: 'sold_count',   label: '↓Sold개',    align: 'right', mono: true,  type: 'num',  toggle: true,  defaultOn: false },
    { key: 'invoice_no',   label: 'Invoice',    align: 'left',  mono: true,  type: 'str',  always: true },
    { key: 'ship_date',    label: 'Ship',       align: 'left',  mono: true,  type: 'date', always: true },
    { key: 'arrival_date', label: 'Arrival',    align: 'left',  mono: true,  type: 'date', always: true },
    { key: 'con_return',   label: 'ConReturn',  align: 'left',  mono: true,  type: 'date', always: true },
    { key: 'free_time',    label: 'Free',       align: 'center',mono: true,  type: 'num',  always: true },
    { key: 'wh',           label: 'WH',         align: 'left',  mono: true,  type: 'str',  always: true },
    { key: 'customs',      label: 'Customs',    align: 'left',  mono: true,  type: 'str',  always: true },
    { key: 'initial_weight',label:'Inbound(MT)',align: 'right', mono: true,  type: 'num',  always: true,  fmt: 'mt', total: true },
    { key: 'outbound_weight',label:'Outbound(MT)',align:'right',mono: true,  type: 'num',  always: true,  fmt: 'mt', total: true },
    { key: 'location',     label: 'Location',   align: 'left',  mono: false, type: 'str',  always: true,  tag: true },
    { key: '_actions',     label: '',           align: 'center',mono: false, type: '_skip',always: true },
  ];

  var _invState = {
    rawRows:        [],
    statusFilter:   'all',
    headerFilters:  {},   /* { columnKey: 'filterText' } */
    sortKey:        null,
    sortAsc:        true,
    visibleToggles: null, /* Set<columnKey> for toggleable cols */
  };

  function _invLoadToggles() {
    try {
      var raw = localStorage.getItem('sqm.inv.toggles');
      if (raw) _invState.visibleToggles = new Set(JSON.parse(raw));
    } catch (e) {}
    if (!_invState.visibleToggles) _invState.visibleToggles = new Set();
  }
  function _invSaveToggles() {
    try {
      localStorage.setItem('sqm.inv.toggles', JSON.stringify(Array.from(_invState.visibleToggles)));
    } catch (e) {}
  }

  function _invVisibleColumns() {
    return INV_COLUMNS.filter(function(c){
      return c.always || (c.toggle && _invState.visibleToggles.has(c.key));
    });
  }

  function _invFilteredSortedRows() {
    var rows = _invState.rawRows.slice();
    /* status filter */
    if (_invState.statusFilter !== 'all') {
      var sf = _invState.statusFilter;
      rows = rows.filter(function(r){ return (r.status || '').toUpperCase() === sf; });
    }
    /* header filters (case-insensitive contains) */
    Object.keys(_invState.headerFilters).forEach(function(k){
      var v = (_invState.headerFilters[k] || '').toLowerCase().trim();
      if (!v) return;
      rows = rows.filter(function(r){
        var cell = r[k];
        if (cell == null) return false;
        return String(cell).toLowerCase().indexOf(v) !== -1;
      });
    });
    /* sort */
    if (_invState.sortKey) {
      var col = INV_COLUMNS.find(function(c){ return c.key === _invState.sortKey; });
      var dir = _invState.sortAsc ? 1 : -1;
      rows.sort(function(a, b){
        var va = a[_invState.sortKey], vb = b[_invState.sortKey];
        if (va == null && vb == null) return 0;
        if (va == null) return 1;
        if (vb == null) return -1;
        if (col && col.type === 'num') return (Number(va) - Number(vb)) * dir;
        return String(va).localeCompare(String(vb), 'ko') * dir;
      });
    }
    return rows;
  }

  function loadInventoryPage() {
    var route = _currentRoute;
    var c = document.getElementById('page-container');
    if (!c) return;
    _invLoadToggles();
    c.innerHTML = '<div style="padding:40px;text-align:center">⏳ 재고 로딩 중...</div>';
    apiGet('/api/inventory').then(function(res){
      if (_currentRoute !== route) return;
      _invState.rawRows = extractRows(res);
      /* No 컬럼 부여 */
      _invState.rawRows.forEach(function(r, i){ r.no = i + 1; });
      _invRenderInventoryPage();
    }).catch(function(e){
      if (_currentRoute !== route) return;
      c.innerHTML = '<div class="empty" style="padding:40px;text-align:center">Load failed: ' + escapeHtml(e.message || String(e)) + '</div>';
      showToast('error', 'Inventory load failed');
    });
  }

  function _invRenderInventoryPage() {
    var c = document.getElementById('page-container');
    if (!c) return;
    var rows = _invFilteredSortedRows();
    var totalRows = _invState.rawRows.length;

    /* status chips */
    var STATUSES = ['all', 'AVAILABLE', 'RESERVED', 'PICKED', 'SOLD', 'OUTBOUND', 'RETURN'];
    var chipsHtml = STATUSES.map(function(s){
      var label = s === 'all' ? '전체' : s;
      var count = s === 'all' ? totalRows : _invState.rawRows.filter(function(r){ return (r.status || '').toUpperCase() === s; }).length;
      var active = _invState.statusFilter === s;
      return '<button class="alloc-filter-btn ' + (active ? 'active' : '') + '" onclick="window.invSetStatus(\'' + s + '\')">' +
             escapeHtml(label) + ' <span style="opacity:.7">' + count + '</span></button>';
    }).join('');

    /* 컬럼 토글 메뉴 */
    var toggleHtml = INV_COLUMNS.filter(function(col){ return col.toggle; }).map(function(col){
      var checked = _invState.visibleToggles.has(col.key) ? 'checked' : '';
      return '<label style="display:block;padding:4px 12px;cursor:pointer;font-size:12px"><input type="checkbox" ' + checked +
             ' onchange="window.invToggleColumn(\'' + col.key + '\', this.checked)"> ' + escapeHtml(col.label) + '</label>';
    }).join('');

    var visCols = _invVisibleColumns();

    /* Header row + filter row */
    var headerHtml = visCols.map(function(col){
      if (col.key === '_actions') return '<th style="width:60px"></th>';
      var sortIcon = '';
      if (_invState.sortKey === col.key) sortIcon = _invState.sortAsc ? ' ▲' : ' ▼';
      return '<th style="cursor:pointer;text-align:' + col.align + '" onclick="window.invSort(\'' + col.key + '\')" title="클릭으로 정렬">' +
             escapeHtml(col.label) + sortIcon + '</th>';
    }).join('');

    var filterHtml = visCols.map(function(col){
      if (col.key === '_actions' || col.key === 'no') return '<th></th>';
      var v = _invState.headerFilters[col.key] || '';
      return '<th style="padding:2px 4px"><input type="text" value="' + escapeHtml(v) +
             '" placeholder="🔍" oninput="window.invHeaderFilter(\'' + col.key + '\', this.value)"' +
             ' style="width:100%;padding:2px 4px;background:var(--bg-hover);border:1px solid var(--panel-border);border-radius:3px;font-size:10px"></th>';
    }).join('');

    /* Body rows */
    var bodyHtml = rows.map(function(r, i){
      var lot = String(r.lot || '');
      var cellsHtml = visCols.map(function(col){
        if (col.key === '_actions') {
          return '<td style="text-align:center"><button class="btn btn-ghost btn-xs" onclick="event.stopPropagation();window.showLotDetail(\'' + escapeHtml(lot) + '\')">Detail</button></td>';
        }
        var v = r[col.key];
        var display = '';
        if (v == null) {
          display = '-';
        } else if (col.type === 'num' && col.fmt === 'mt') {
          display = (typeof fmtN === 'function') ? fmtN(v) : Number(v).toFixed(3);
        } else if (col.type === 'date') {
          display = String(v).slice(0, 10);
        } else {
          display = String(v);
        }
        var cls = col.mono ? 'mono-cell' : '';
        var style = 'text-align:' + col.align;
        if (col.accent) style += ';color:var(--accent);font-weight:600';
        var cell;
        if (col.tag) cell = '<span class="tag">' + escapeHtml(display) + '</span>';
        else if (col.status) {
          var st = String(r.status || '').toUpperCase();
          var stColor = st === 'AVAILABLE' ? '#66bb6a' : st === 'RESERVED' ? '#ffa726' : st === 'PICKED' ? '#42a5f5' : (st === 'SOLD' || st === 'OUTBOUND') ? '#ec407a' : '#9e9e9e';
          cell = '<span class="tag" style="background:' + stColor + ';color:#fff">' + escapeHtml(display) + '</span>';
        }
        else cell = escapeHtml(display);
        return '<td class="' + cls + '" style="' + style + '">' + cell + '</td>';
      }).join('');
      return '<tr oncontextmenu="window.invContextMenu(event, \'' + escapeHtml(lot) + '\'); return false;" ondblclick="window.showLotDetail(\'' + escapeHtml(lot) + '\')">' +
             cellsHtml + '</tr>';
    }).join('');

    /* Footer 합계 (filtered rows) */
    var totals = {};
    visCols.forEach(function(col){ if (col.total) totals[col.key] = 0; });
    rows.forEach(function(r){
      Object.keys(totals).forEach(function(k){
        var v = Number(r[k]);
        if (!isNaN(v)) totals[k] += v;
      });
    });
    var footerHtml = visCols.map(function(col){
      if (col.total) return '<td class="mono-cell" style="text-align:right;font-weight:700">' + totals[col.key].toFixed(3) + '</td>';
      if (col.key === 'no') return '<td style="text-align:right;font-weight:700">합계 (' + rows.length + ')</td>';
      return '<td></td>';
    }).join('');

    c.innerHTML =
      '<section class="page" data-page="inventory">' +
      /* 상단 헤더 */
      '<div style="display:flex;align-items:center;gap:12px;padding:4px 0 8px">' +
      '  <h2 style="margin:0">📦 재고 목록 (Inventory)</h2>' +
      '  <span style="font-size:12px;color:var(--text-muted)">' + rows.length + ' / ' + totalRows + ' LOTs</span>' +
      '  <span style="margin-left:auto;display:flex;gap:6px;align-items:center">' +
      '    <div style="position:relative;display:inline-block">' +
      '      <button class="btn btn-secondary" onclick="window.invToggleColumnMenu()">⚙️ 컬럼</button>' +
      '      <div id="inv-column-menu" style="display:none;position:absolute;right:0;top:100%;margin-top:4px;background:var(--panel);border:1px solid var(--panel-border);border-radius:4px;padding:4px 0;box-shadow:0 4px 12px rgba(0,0,0,.3);z-index:100;min-width:140px">' + toggleHtml + '</div>' +
      '    </div>' +
      '    <button class="btn" onclick="window.invExportCsv()">📥 Excel 저장</button>' +
      '    <button class="btn btn-secondary" onclick="renderPage(\'inventory\')">🔁 새로고침</button>' +
      '  </span>' +
      '</div>' +
      /* 상태 chip filter */
      '<div style="display:flex;gap:4px;margin-bottom:6px;flex-wrap:wrap">' + chipsHtml + '</div>' +
      /* Table */
      '<div style="overflow-x:auto;max-height:calc(100vh - 260px);overflow-y:auto">' +
      '  <table class="data-table" style="font-size:11px">' +
      '    <thead style="position:sticky;top:0;background:var(--panel);z-index:1">' +
      '      <tr>' + headerHtml + '</tr>' +
      '      <tr>' + filterHtml + '</tr>' +
      '    </thead>' +
      '    <tbody>' + (rows.length ? bodyHtml : '<tr><td colspan="' + visCols.length + '" style="padding:40px;text-align:center;color:var(--text-muted)">📭 조건에 맞는 재고 없음</td></tr>') + '</tbody>' +
      (rows.length ? '<tfoot style="position:sticky;bottom:0;background:var(--panel)"><tr>' + footerHtml + '</tr></tfoot>' : '') +
      '  </table>' +
      '</div>' +
      '</section>';
  }

  /* 핸들러 */
  window.invSetStatus = function(s) {
    _invState.statusFilter = s;
    _invRenderInventoryPage();
  };
  window.invSort = function(key) {
    if (_invState.sortKey === key) _invState.sortAsc = !_invState.sortAsc;
    else { _invState.sortKey = key; _invState.sortAsc = true; }
    _invRenderInventoryPage();
  };
  window.invHeaderFilter = function(key, val) {
    _invState.headerFilters[key] = val;
    /* debounce 없이 즉시 — 작은 데이터셋이라 OK */
    var sel = document.activeElement;
    var selStart = sel && sel.selectionStart;
    _invRenderInventoryPage();
    /* focus 복구 */
    var inp = document.querySelector('input[oninput*="' + key + '"]');
    if (inp) {
      inp.focus();
      if (selStart != null) try { inp.setSelectionRange(selStart, selStart); } catch(e){}
    }
  };
  window.invToggleColumn = function(key, checked) {
    if (checked) _invState.visibleToggles.add(key);
    else _invState.visibleToggles.delete(key);
    _invSaveToggles();
    _invRenderInventoryPage();
  };
  window.invToggleColumnMenu = function() {
    var m = document.getElementById('inv-column-menu');
    if (!m) return;
    var open = m.style.display !== 'none';
    m.style.display = open ? 'none' : 'block';
    if (!open) {
      /* 외부 클릭 시 닫기 */
      setTimeout(function(){
        var handler = function(e){
          if (!m.contains(e.target)) {
            m.style.display = 'none';
            document.removeEventListener('click', handler);
          }
        };
        document.addEventListener('click', handler);
      }, 10);
    }
  };
  window.invContextMenu = function(e, lot) {
    e.preventDefault();
    var old = document.querySelector('.ctx-menu');
    if (old) old.remove();
    var m = document.createElement('div');
    m.className = 'ctx-menu';
    m.style.cssText = 'position:fixed;z-index:9999;background:var(--panel);border:1px solid var(--panel-border);border-radius:6px;padding:4px 0;min-width:180px;box-shadow:0 4px 16px rgba(0,0,0,.4);font-size:13px;';
    m.style.left = e.clientX + 'px';
    m.style.top = e.clientY + 'px';
    function mi(label, onClick) {
      var b = document.createElement('button');
      b.textContent = label;
      b.style.cssText = 'display:block;width:100%;text-align:left;padding:6px 14px;background:transparent;border:none;color:var(--fg);cursor:pointer;font-size:13px';
      b.addEventListener('mouseover', function(){ b.style.background = 'var(--btn-hover)'; });
      b.addEventListener('mouseout', function(){ b.style.background = 'transparent'; });
      b.addEventListener('click', function(){ m.remove(); onClick(); });
      m.appendChild(b);
    }
    mi('📋 LOT 번호 복사', function(){
      if (navigator.clipboard) navigator.clipboard.writeText(lot).then(function(){ showToast('success', 'LOT NO 복사됨'); });
      else prompt('수동 복사:', lot);
    });
    mi('🔍 LOT 상세 보기', function(){ window.showLotDetail(lot); });
    mi('📥 행 데이터 CSV 복사', function(){
      var r = _invState.rawRows.find(function(x){ return String(x.lot || '') === lot; });
      if (!r) return;
      var keys = INV_COLUMNS.filter(function(c){ return c.key !== '_actions'; }).map(function(c){ return c.key; });
      var line = keys.map(function(k){
        var v = r[k] == null ? '' : String(r[k]);
        if (/[,"\n]/.test(v)) v = '"' + v.replace(/"/g, '""') + '"';
        return v;
      }).join(',');
      var text = keys.join(',') + '\n' + line;
      if (navigator.clipboard) navigator.clipboard.writeText(text).then(function(){ showToast('success', '행 CSV 복사됨'); });
      else prompt('수동 복사:', text);
    });
    document.body.appendChild(m);
    setTimeout(function(){
      var handler = function(ev){ if (!m.contains(ev.target)) { m.remove(); document.removeEventListener('click', handler); } };
      document.addEventListener('click', handler);
    }, 10);
  };
  window.invExportCsv = function() {
    var rows = _invFilteredSortedRows();
    if (!rows.length) { showToast('warn', '내보낼 데이터 없음'); return; }
    var visCols = _invVisibleColumns().filter(function(c){ return c.key !== '_actions'; });
    var headers = visCols.map(function(c){ return c.label; }).join(',');
    function csvEsc(v){ var s = String(v == null ? '' : v); if (/[,"\n]/.test(s)) s = '"' + s.replace(/"/g,'""') + '"'; return s; }
    var lines = [headers];
    rows.forEach(function(r){
      lines.push(visCols.map(function(c){ return csvEsc(r[c.key]); }).join(','));
    });
    var blob = new Blob(['\ufeff' + lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    var ts = new Date();
    a.download = 'inventory_' + ts.getFullYear() + String(ts.getMonth()+1).padStart(2,'0') + String(ts.getDate()).padStart(2,'0') + '_' + String(ts.getHours()).padStart(2,'0') + String(ts.getMinutes()).padStart(2,'0') + '.csv';
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast('success', '📥 ' + a.download + ' (' + rows.length + ' LOTs)');
  };

  /* ===================================================
     7b. PAGE: Allocation
     =================================================== */
  /* ===================================================
     7b. PAGE: Allocation — 2단 구조 (LOT 요약 + Detail)
     상단: LOT 단위 집계 (클릭 시 하단 확장)
     하단: 해당 LOT의 톤백 상세 목록
     =================================================== */
  /* ===================================================================
     [Sprint 1-1] Allocation 탭 — v864-2 AllocationDialog (1616줄) 포팅
     ──────────────────────────────────────────────────────────────────
     v864-2 source: gui_app_modular/dialogs/allocation_dialog.py
     v864-3 target: 이 함수 (탭 페이지) + 3개 기존 모달 재활용

     이 Phase(1-B+1-C)에서 구현:
       ✅ 9열 테이블 (ALLOC_PREVIEW_COLUMNS 매칭)
       ✅ 상단 액션 툴바 (4개 작동 + 3개 placeholder)
       ✅ 상태 필터 (전체/RESERVED/PICKED/SOLD)
       ✅ 다중 선택 체크박스 + 일괄 취소
       ✅ 합계 푸터 (qty_mt, 4 decimals)
       ✅ LOT 확장/축소 (기존 패턴 유지)

     다음 Phase(1-1-D~E)에서 추가:
       🟡 인라인 편집 (PATCH API 필요)
       🟡 PICKED/SOLD 상태 전환 (백엔드 엔드포인트 필요)
       🟡 LOT 예약 초기화 (백엔드 엔드포인트 필요)
       🟡 우클릭 컨텍스트 메뉴 (행 삭제/복사)
     =================================================================== */
  var _allocState = { currentFilter: 'all', rows: [], selectedLots: new Set() };
  /* [Sprint 1-1-D] 편집 가능 필드 (백엔드 _ALLOC_EDITABLE_FIELDS 와 일치 필요) */
  var ALLOC_EDITABLE_FIELDS = new Set(['customer', 'sale_ref', 'qty_mt', 'outbound_date']);

  function loadAllocationPage() {
    var route = _currentRoute;
    var c = document.getElementById('page-container');
    if (!c) return;
    _allocState.selectedLots.clear();
    c.innerHTML = [
      '<section class="page" data-page="allocation">',
      /* ── 헤더 ── */
      '<div class="alloc-header" style="display:flex;align-items:center;gap:12px;padding:8px 0 8px">',
      '  <h2 style="margin:0">📋 판매 배정 (Allocation)</h2>',
      '  <span id="alloc-summary-label" style="color:var(--text-muted);font-size:.9rem"></span>',
      '  <button class="btn btn-secondary" onclick="renderPage(\'allocation\')" style="margin-left:auto">🔁 새로고침</button>',
      '</div>',
      /* ── 액션 툴바 (v864-2 AllocationDialog primary_buttons 매핑) ── */
      '<div class="alloc-toolbar" style="display:flex;flex-wrap:wrap;align-items:center;gap:6px;padding:8px 10px;background:var(--panel);border:1px solid var(--panel-border);border-radius:6px;margin-bottom:8px">',
      '  <button class="btn btn-primary" onclick="window.allocUploadExcel()">📂 Excel 업로드</button>',
      '  <button class="btn" onclick="window.allocApplyApproved()">📌 승인분 반영</button>',
      '  <button class="btn" onclick="window.allocShowApprovalQueue()">✅ 승인 대기</button>',
      '  <span style="width:1px;height:22px;background:var(--panel-border);margin:0 4px"></span>',
      '  <button class="btn btn-danger" onclick="window.allocCancelSelected()">❌ 선택 배정 취소</button>',
      '  <span style="width:1px;height:22px;background:var(--panel-border);margin:0 4px"></span>',
      /* 백엔드 엔드포인트 미구현 — Sprint 1-1-E에서 연결 */
      '  <button class="btn" onclick="window.allocPickSelected()" title="RESERVED → PICKED">📦 출고 실행 (PICKED)</button>',
      '  <button class="btn" onclick="window.allocConfirmSelected()" title="PICKED → SOLD">🔒 출고 확정 (SOLD)</button>',
      '  <button class="btn" onclick="window.allocResetSelected()" title="LOT 배정 완전 삭제">🧹 LOT 초기화</button>',
      '</div>',
      /* ── 상태 필터 ── */
      '<div class="alloc-filter" style="display:flex;gap:4px;margin-bottom:8px">',
      '  <button class="alloc-filter-btn active" data-filter="all" onclick="window.allocFilterBy(\'all\')">전체</button>',
      '  <button class="alloc-filter-btn" data-filter="RESERVED" onclick="window.allocFilterBy(\'RESERVED\')">RESERVED</button>',
      '  <button class="alloc-filter-btn" data-filter="PICKED" onclick="window.allocFilterBy(\'PICKED\')">PICKED</button>',
      '  <button class="alloc-filter-btn" data-filter="SOLD" onclick="window.allocFilterBy(\'SOLD\')">SOLD</button>',
      '</div>',
      /* ── 로딩 / 빈 상태 ── */
      '<div id="alloc-loading" style="padding:40px;text-align:center;color:var(--text-muted)">⏳ 데이터 로딩 중...</div>',
      '<div class="empty" id="alloc-empty" style="display:none;padding:60px;text-align:center">📭 배정 데이터 없음</div>',
      /* ── 테이블 (v864-2 ALLOC_PREVIEW_COLUMNS: LOT/SAP/PRODUCT/QTY/CUSTOMER/SALE REF/OUTBOUND DATE/WH/STATUS) ── */
      '<div style="overflow-x:auto">',
      '  <table class="data-table" id="alloc-summary-table" style="display:none;width:100%">',
      '  <thead><tr>',
      '    <th style="width:32px"><input type="checkbox" id="alloc-select-all" onclick="window.allocToggleAll(this.checked)"></th>',
      '    <th style="width:40px">No.</th>',
      '    <th>LOT NO</th>',
      '    <th>SAP NO</th>',
      '    <th>PRODUCT</th>',
      '    <th style="text-align:right">QTY (MT)</th>',
      '    <th>CUSTOMER</th>',
      '    <th>SALE REF</th>',
      '    <th>OUTBOUND DATE</th>',
      '    <th>WH</th>',
      '    <th>STATUS</th>',
      '  </tr></thead>',
      '  <tbody id="alloc-summary-tbody"></tbody>',
      '  <tfoot id="alloc-summary-tfoot"></tfoot>',
      '  </table>',
      '</div>',
      /* ── 상세 패널 (기존 기능 유지) ── */
      '<div id="alloc-detail-panel" style="display:none;margin-top:16px;border-top:2px solid var(--panel-border);padding-top:16px">',
      '  <h3 id="alloc-detail-title" style="margin:0 0 12px 0">톤백 상세</h3>',
      '  <div id="alloc-detail-content"></div>',
      '</div>',
      '</section>'
    ].join('');

    apiGet('/api/q/allocation-summary').then(function(res){
      if (_currentRoute !== route) return;
      _allocState.rows = extractRows(res);
      document.getElementById('alloc-loading').style.display = 'none';
      if (!_allocState.rows.length) {
        document.getElementById('alloc-empty').style.display = 'block';
        var lbl = document.getElementById('alloc-summary-label');
        if (lbl) lbl.textContent = '(0건)';
        return;
      }
      _renderAllocTable();
    }).catch(function(e){
      if (_currentRoute !== route) return;
      document.getElementById('alloc-loading').style.display = 'none';
      document.getElementById('alloc-empty').textContent = 'Load failed: ' + (e.message||'');
      document.getElementById('alloc-empty').style.display = 'block';
    });
  }

  /* ── 테이블 렌더 (필터 적용) ────────────────────────────────────── */
  function _renderAllocTable() {
    var filter = _allocState.currentFilter;
    var rows = _allocState.rows.filter(function(r){
      if (filter === 'all') return true;
      return (r.status || 'RESERVED').toUpperCase() === filter;
    });
    var tbody = document.getElementById('alloc-summary-tbody');
    var tfoot = document.getElementById('alloc-summary-tfoot');
    var table = document.getElementById('alloc-summary-table');
    var empty = document.getElementById('alloc-empty');
    var lbl = document.getElementById('alloc-summary-label');

    if (!rows.length) {
      if (tbody) tbody.innerHTML = '';
      if (tfoot) tfoot.innerHTML = '';
      if (table) table.style.display = 'none';
      if (empty) { empty.textContent = '📭 (' + filter + ') 배정 데이터 없음'; empty.style.display = 'block'; }
      if (lbl) lbl.textContent = '(0/' + _allocState.rows.length + '건)';
      return;
    }
    if (empty) empty.style.display = 'none';
    if (table) table.style.display = '';
    if (lbl) lbl.textContent = '(' + rows.length + '/' + _allocState.rows.length + '건)';

    var totalMt = 0;
    /* [Sprint 1-1-D] 편집 가능 셀에 data-lot/data-field + ondblclick + oncontextmenu */
    tbody.innerHTML = rows.map(function(r, i){
      var lot = escapeHtml(r.lot_no || '');
      var qtyMt = (r.total_mt != null) ? Number(r.total_mt) : (r.qty_mt != null ? Number(r.qty_mt) : 0);
      if (!isNaN(qtyMt)) totalMt += qtyMt;
      var status = (r.status || 'RESERVED').toUpperCase();
      var statusColor = status === 'SOLD' ? '#66bb6a' : status === 'PICKED' ? '#42a5f5' : 'var(--warning)';
      var statusFg = status === 'RESERVED' ? '#000' : '#fff';
      var checked = _allocState.selectedLots.has(lot) ? 'checked' : '';

      /* 편집 가능 셀 attrs 헬퍼 */
      function editTd(field, display, extraClass, extraStyle) {
        var attrs = 'class="' + (extraClass || '') + ' alloc-editable" ' +
          'data-lot="' + lot + '" data-field="' + field + '"' +
          (extraStyle ? ' style="' + extraStyle + '"' : '') +
          ' ondblclick="window.allocEditCell(this)" title="더블클릭으로 편집";';
        return '<td ' + attrs + '>' + display + '</td>';
      }

      return '<tr class="alloc-summary-row" data-lot="' + lot + '" data-status="' + status + '" oncontextmenu="window.allocContextMenu(event, \'' + lot + '\'); return false;">' +
        '<td style="text-align:center"><input type="checkbox" ' + checked + ' onclick="event.stopPropagation();window.allocToggleRow(\'' + lot + '\',this.checked)"></td>' +
        '<td class="mono-cell" style="text-align:right">' + (i + 1) + '</td>' +
        '<td class="mono-cell" style="color:var(--accent);font-weight:600;cursor:pointer" onclick="window.toggleAllocDetail(\'' + lot + '\')">' +
          '<span class="alloc-expand-icon">▶</span> ' + lot + '</td>' +
        '<td class="mono-cell">' + escapeHtml(r.sap_no || '-') + '</td>' +
        '<td>' + escapeHtml(r.product || '-') + '</td>' +
        editTd('qty_mt', (qtyMt ? qtyMt.toFixed(4) : '-'), 'mono-cell', 'text-align:right') +
        editTd('customer', escapeHtml(r.customer || r.sold_to || '-'), '', '') +
        editTd('sale_ref', escapeHtml(r.sale_ref || '-'), 'mono-cell', '') +
        editTd('outbound_date', escapeHtml(r.outbound_date || r.ship_date || '-'), 'mono-cell', '') +
        '<td>' + escapeHtml(r.warehouse || r.wh || '-') + '</td>' +
        '<td><span class="tag" style="background:' + statusColor + ';color:' + statusFg + '">' + status + '</span></td>' +
        '</tr>';
    }).join('');

    /* Footer 합계 (v864-2 TreeviewTotalFooter 매칭) */
    tfoot.innerHTML =
      '<tr style="background:var(--panel);font-weight:700">' +
      '<td colspan="5" style="text-align:right">합계:</td>' +
      '<td class="mono-cell" style="text-align:right">' + totalMt.toFixed(4) + ' MT</td>' +
      '<td colspan="5"></td>' +
      '</tr>';
  }

  /* ── 버튼 핸들러 ─────────────────────────────────────────────────── */
  window.allocUploadExcel = function() {
    if (typeof showAllocationUploadModal === 'function') { showAllocationUploadModal(); }
    else { showToast('error', 'Upload modal 미초기화'); }
  };
  window.allocApplyApproved = function() {
    if (typeof showApplyApprovedAllocationModal === 'function') { showApplyApprovedAllocationModal(); }
    else { showToast('error', 'Apply modal 미초기화'); }
  };
  window.allocShowApprovalQueue = function() {
    if (typeof showApprovalQueueModal === 'function') { showApprovalQueueModal(); }
    else { showToast('error', 'Approval queue 미초기화'); }
  };
  window.allocWipToast = function(featureName) {
    showToast('info', featureName + ': 준비 중 (Sprint 1-1-E 예정 — 백엔드 엔드포인트 구현 후 연결)');
  };
  window.allocFilterBy = function(filter) {
    _allocState.currentFilter = filter;
    document.querySelectorAll('.alloc-filter-btn').forEach(function(b){
      b.classList.toggle('active', b.dataset.filter === filter);
    });
    _renderAllocTable();
  };
  window.allocToggleAll = function(checked) {
    var visibleFilter = _allocState.currentFilter;
    _allocState.rows.forEach(function(r){
      var status = (r.status || 'RESERVED').toUpperCase();
      if (visibleFilter !== 'all' && status !== visibleFilter) return;
      var lot = r.lot_no || '';
      if (checked) _allocState.selectedLots.add(lot);
      else _allocState.selectedLots.delete(lot);
    });
    _renderAllocTable();
  };
  window.allocToggleRow = function(lot, checked) {
    if (checked) _allocState.selectedLots.add(lot);
    else _allocState.selectedLots.delete(lot);
  };
  window.allocCancelSelected = function() {
    _allocBulkAction({
      url_suffix:   '/cancel',
      method:       'POST',
      label:        '배정 취소',
      icon:         '❌',
      confirmMsg:   '건 배정 취소?',
    });
  };

  /* ── [Sprint 1-1-E] 상태 전환 버튼 핸들러 ──────────────────────────── */
  window.allocPickSelected = function() {
    _allocBulkAction({
      url_suffix:   '/pick',
      method:       'POST',
      label:        '출고 실행 (PICKED)',
      icon:         '📦',
      confirmMsg:   '건을 PICKED 상태로 변경?\n(RESERVED → PICKED)',
    });
  };
  window.allocConfirmSelected = function() {
    _allocBulkAction({
      url_suffix:   '/confirm',
      method:       'POST',
      label:        '출고 확정 (SOLD)',
      icon:         '🔒',
      confirmMsg:   '건을 SOLD 상태로 확정?\n(PICKED → SOLD — 되돌릴 수 없음)',
    });
  };
  window.allocResetSelected = function() {
    _allocBulkAction({
      url_suffix:   '/reset',
      method:       'POST',
      label:        'LOT 배정 초기화',
      icon:         '🧹',
      confirmMsg:   '건 배정 완전 초기화?\nallocation_plan 에서 삭제 + inventory AVAILABLE 원복\n(SOLD 는 보호됨)',
    });
  };

  /* 공통 다중 선택 액션 헬퍼 */
  function _allocBulkAction(opts) {
    var selected = Array.from(_allocState.selectedLots);
    if (!selected.length) { showToast('warn', opts.label + ': 대상을 먼저 선택하세요'); return; }
    var preview = selected.slice(0, 5).join(', ') + (selected.length > 5 ? ' …외 ' + (selected.length - 5) + '건' : '');
    if (!confirm(opts.icon + ' ' + opts.label + '\n\n' + selected.length + opts.confirmMsg + '\n\n' + preview)) return;

    var okCount = 0, errors = [];
    var promises = selected.map(function(lot){
      return apiPost('/api/allocation/' + encodeURIComponent(lot) + opts.url_suffix, {})
        .then(function(){ okCount++; })
        .catch(function(e){ errors.push({ lot: lot, reason: (e && e.message) || String(e) }); });
    });
    Promise.all(promises).then(function(){
      var errCount = errors.length;
      if (errCount === 0) {
        showToast('success', opts.icon + ' ' + opts.label + ': ' + okCount + '건 성공');
      } else {
        var errSample = errors.slice(0, 3).map(function(e){ return e.lot + ' (' + e.reason + ')'; }).join(', ');
        showToast('warn', opts.label + ': 성공 ' + okCount + ' / 실패 ' + errCount + ' (' + errSample + ')');
      }
      _allocState.selectedLots.clear();
      loadAllocationPage();
    });
  }

  /* ── [Sprint 1-1-D] 인라인 편집 — 셀 더블클릭 → PATCH ─────────────── */
  window.allocEditCell = function(td) {
    if (!td || td.querySelector('input')) return;
    var lot = td.dataset.lot;
    var field = td.dataset.field;
    if (!lot || !field || !ALLOC_EDITABLE_FIELDS.has(field)) return;

    /* 현재 값 추출 (display 에서 HTML tag 제거) */
    var curDisplay = td.textContent.trim();
    var curVal = curDisplay === '-' ? '' : curDisplay;

    /* qty_mt 는 number input */
    var input = document.createElement('input');
    input.type = (field === 'qty_mt') ? 'number' : (field === 'outbound_date' ? 'date' : 'text');
    if (field === 'qty_mt') input.step = '0.0001';
    input.value = curVal;
    input.className = 'alloc-edit-input';
    input.style.cssText = 'width:100%;padding:2px 4px;background:var(--bg);color:var(--fg);border:1px solid var(--accent);border-radius:3px;font-size:11px;font-family:inherit';

    td.innerHTML = '';
    td.appendChild(input);
    input.focus();
    input.select && input.select();

    var committed = false;
    function cancel() {
      if (committed) return;
      committed = true;
      _renderAllocTable();  /* 원복 */
    }
    function commit() {
      if (committed) return;
      committed = true;
      var newVal = input.value;
      if (String(newVal).trim() === String(curVal).trim()) {
        _renderAllocTable();
        return;
      }
      /* PATCH /api/allocation/{lot} */
      td.innerHTML = '<span style="color:var(--text-muted);font-size:11px">⏳ 저장 중...</span>';
      var payload = {};
      payload[field] = newVal;
      fetch(API + '/api/allocation/' + encodeURIComponent(lot), {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
        .then(function(r){ return r.json().then(function(b){ return { ok: r.ok, body: b }; }); })
        .then(function(res){
          if (!res.ok || !res.body.success) {
            throw new Error((res.body && (res.body.detail || res.body.message)) || 'PATCH 실패');
          }
          /* 로컬 rows 업데이트 */
          var row = _allocState.rows.find(function(r){ return (r.lot_no || '') === lot; });
          if (row) {
            row[field] = (field === 'qty_mt') ? Number(newVal) : newVal;
            if (field === 'customer') row.sold_to = newVal;
          }
          showToast('success', '💾 ' + lot + '.' + field + ' 저장됨');
          _renderAllocTable();
        })
        .catch(function(e){
          showToast('error', '편집 실패: ' + (e.message || String(e)));
          _renderAllocTable();
        });
    }
    input.addEventListener('blur', commit);
    input.addEventListener('keydown', function(e){
      if (e.key === 'Enter') { e.preventDefault(); input.blur(); }
      else if (e.key === 'Escape') {
        e.preventDefault();
        input.removeEventListener('blur', commit);
        cancel();
      }
    });
  };

  /* ── [Sprint 1-1-D] 우클릭 컨텍스트 메뉴 — 행 삭제/복사 ─────────────── */
  window.allocContextMenu = function(e, lot) {
    e.preventDefault();
    /* 기존 컨텍스트 메뉴 제거 */
    var old = document.querySelector('.ctx-menu');
    if (old) old.remove();

    var row = _allocState.rows.find(function(r){ return (r.lot_no || '') === lot; });
    if (!row) return;

    var m = document.createElement('div');
    m.className = 'ctx-menu';
    m.style.cssText = 'position:fixed;z-index:9999;background:var(--panel);border:1px solid var(--panel-border);border-radius:6px;padding:4px 0;min-width:160px;box-shadow:0 4px 16px rgba(0,0,0,.4);font-size:13px;';
    m.style.left = e.clientX + 'px';
    m.style.top = e.clientY + 'px';

    function mi(label, onClick, danger) {
      var b = document.createElement('button');
      b.textContent = label;
      b.style.cssText = 'display:block;width:100%;text-align:left;padding:6px 14px;background:transparent;border:none;color:' + (danger ? 'var(--danger)' : 'var(--fg)') + ';cursor:pointer;font-size:13px';
      b.addEventListener('mouseover', function(){ b.style.background = 'var(--btn-hover)'; });
      b.addEventListener('mouseout', function(){ b.style.background = 'transparent'; });
      b.addEventListener('click', function(){ m.remove(); onClick(); });
      m.appendChild(b);
    }

    mi('📋 행 복사 (CSV)', function(){
      var cols = ['lot_no', 'sap_no', 'product', 'qty_mt', 'customer', 'sale_ref', 'outbound_date', 'warehouse', 'status'];
      var header = cols.join(',');
      var values = cols.map(function(c){ return String(row[c] != null ? row[c] : (c === 'customer' ? (row.sold_to || '') : '')); }).join(',');
      var text = header + '\n' + values;
      if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(function(){
          showToast('success', '📋 클립보드에 복사됨');
        }).catch(function(){
          prompt('수동 복사:', text);
        });
      } else {
        prompt('수동 복사:', text);
      }
    });

    mi('❌ 이 행 배정 취소', function(){
      if (!confirm('❌ ' + lot + '\n배정 취소하시겠습니까?')) return;
      apiPost('/api/allocation/' + encodeURIComponent(lot) + '/cancel', {})
        .then(function(){ showToast('success', lot + ' 취소됨'); loadAllocationPage(); })
        .catch(function(err){ showToast('error', '취소 실패: ' + (err.message || err)); });
    }, false);

    mi('🧹 이 행 초기화 (삭제)', function(){
      if (!confirm('🧹 ' + lot + '\nallocation 기록 삭제 + inventory AVAILABLE 원복\n(SOLD 는 보호됨)\n계속하시겠습니까?')) return;
      apiPost('/api/allocation/' + encodeURIComponent(lot) + '/reset', {})
        .then(function(res){ showToast('success', (res.data && res.data.message) || (lot + ' 초기화됨')); loadAllocationPage(); })
        .catch(function(err){ showToast('error', '초기화 실패: ' + (err.message || err)); });
    }, true);

    document.body.appendChild(m);
    /* 다음 클릭 또는 ESC 로 자동 닫기 */
    var closeHandler = function(ev){
      if (!m.contains(ev.target)) { m.remove(); document.removeEventListener('click', closeHandler); }
    };
    setTimeout(function(){ document.addEventListener('click', closeHandler); }, 10);
  };

  var _allocExpandedLot = null;
  window.toggleAllocDetail = function(lotNo) {
    var panel = document.getElementById('alloc-detail-panel');
    var content = document.getElementById('alloc-detail-content');
    var title = document.getElementById('alloc-detail-title');

    // 같은 LOT 클릭 시 닫기
    if (_allocExpandedLot === lotNo) {
      panel.style.display = 'none';
      _allocExpandedLot = null;
      document.querySelectorAll('.alloc-summary-row').forEach(function(r){ r.style.background=''; });
      document.querySelectorAll('.alloc-expand-icon').forEach(function(i){ i.textContent='▶'; });
      return;
    }

    _allocExpandedLot = lotNo;
    document.querySelectorAll('.alloc-summary-row').forEach(function(r){
      if (r.dataset.lot === lotNo) {
        r.style.background = 'var(--bg-active)';
        r.querySelector('.alloc-expand-icon').textContent = '▼';
      } else {
        r.style.background = '';
        r.querySelector('.alloc-expand-icon').textContent = '▶';
      }
    });

    panel.style.display = 'block';
    title.textContent = '📋 ' + lotNo + ' 톤백 상세';
    content.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text-muted)">⏳ 로딩...</div>';

    apiGet('/api/q/allocation-detail/' + encodeURIComponent(lotNo)).then(function(res){
      var rows = extractRows(res);
      if (!rows.length) { content.innerHTML = '<div class="empty">상세 데이터 없음</div>'; return; }
      var tbl = '<table class="data-table"><thead><tr><th>#</th><th>톤백ID</th><th>중량(kg)</th><th>위치</th><th>상태</th><th>배정일</th></tr></thead><tbody>';
      tbl += rows.map(function(r, i){
        return '<tr><td>'+(i+1)+'</td><td class="mono-cell">'+escapeHtml(r.tonbag_id||r.sub_lt||'-')+'</td><td class="mono-cell" style="text-align:right">'+(r.weight!=null?Number(r.weight).toLocaleString():'-')+'</td><td>'+escapeHtml(r.location||'-')+'</td><td><span class="tag">'+escapeHtml(r.status||'-')+'</span></td><td>'+escapeHtml(r.plan_date||r.allocated_date||'-')+'</td></tr>';
      }).join('');
      tbl += '</tbody></table>';
      content.innerHTML = '<p style="color:var(--text-muted);font-size:.85rem;margin-bottom:8px">' + rows.length + '개 톤백</p>' + tbl;
    }).catch(function(e){
      content.innerHTML = '<div class="empty">상세 로드 실패: '+escapeHtml(e.message||'')+'</div>';
    });
  };

  window.cancelAllocation = function(lot) {
    if (!confirm(lot + ': cancel allocation?')) return;
    apiPost('/api/allocation/' + encodeURIComponent(lot) + '/cancel', {})
      .then(function(){ showToast('success', lot + ' allocation cancelled'); loadAllocationPage(); })
      .catch(function(e){ showToast('error', 'Cancel failed: ' + (e.message||String(e))); });
  };

  /* ===================================================
     7c. PAGE: Picked
     =================================================== */
  /* ===================================================
     7c. PAGE: Picked — 2단 구조 (LOT 요약 + 톤백 상세)
     =================================================== */
  /* [Sprint 2-D] Picked 탭 풀 — 체크박스 다중선택 + 6 버튼 액션 */
  var _pickedState = { rows: [], selectedLots: null };

  function loadPickedPage() {
    var route = _currentRoute;
    var c = document.getElementById('page-container');
    if (!c) return;
    if (!_pickedState.selectedLots) _pickedState.selectedLots = new Set();
    _pickedState.selectedLots.clear();

    c.innerHTML = [
      '<section class="page" data-page="picked">',
      '<div style="display:flex;align-items:center;gap:12px;padding:4px 0 8px">',
      '  <h2 style="margin:0">🚛 Picked — 피킹 완료 (화물 결정)</h2>',
      '  <span id="picked-count" style="font-size:12px;color:var(--text-muted)"></span>',
      '  <button class="btn btn-secondary" onclick="renderPage(\'picked\')" style="margin-left:auto">🔁 새로고침</button>',
      '</div>',
      /* 액션 툴바 */
      '<div style="display:flex;flex-wrap:wrap;align-items:center;gap:6px;padding:8px 10px;background:var(--panel);border:1px solid var(--panel-border);border-radius:6px;margin-bottom:8px">',
      '  <button class="btn btn-primary" onclick="window.pickedConfirmSelected()" title="PICKED → OUTBOUND">✅ 출고 확정</button>',
      '  <button class="btn" onclick="window.pickedRevertSelected()" title="PICKED → RESERVED 되돌림">↩️ Reserved 되돌림</button>',
      '  <span style="width:1px;height:20px;background:var(--panel-border);margin:0 4px"></span>',
      '  <button class="btn" onclick="window.pickedExportCsv()">📥 Excel 내보내기</button>',
      '  <button class="btn" onclick="window.pickedSelectAll(true)">☑ 전체 선택</button>',
      '  <button class="btn" onclick="window.pickedSelectAll(false)">☐ 해제</button>',
      '  <button class="btn" onclick="renderPage(\'inventory\')" style="margin-left:auto">📋 LOT 리스트로</button>',
      '</div>',
      '<div id="picked-loading" style="padding:40px;text-align:center;color:var(--text-muted)">⏳ 데이터 로딩 중...</div>',
      '<div style="overflow-x:auto">',
      '  <table class="data-table" id="picked-table" style="display:none">',
      '  <thead><tr>',
      '    <th style="width:32px"><input type="checkbox" id="picked-select-all" onclick="window.pickedSelectAll(this.checked)"></th>',
      '    <th></th><th>LOT No</th><th>피킹No</th><th>고객사</th><th style="text-align:right">톤백수</th><th style="text-align:right">중량(kg)</th><th>피킹일</th>',
      '  </tr></thead>',
      '  <tbody id="picked-tbody"></tbody>',
      '  </table>',
      '</div>',
      '<div class="empty" id="picked-empty" style="display:none;padding:60px;text-align:center">📭 피킹 데이터 없음</div>',
      '<div id="picked-detail-panel" style="display:none;margin-top:16px;border-top:2px solid var(--panel-border);padding-top:16px">',
      '  <h3 id="picked-detail-title" style="margin:0 0 12px 0">톤백 상세</h3>',
      '  <div id="picked-detail-content"></div>',
      '</div>',
      '</section>'
    ].join('');

    apiGet('/api/q/picked-list').then(function(res){
      if (_currentRoute !== route) return;
      _pickedState.rows = extractRows(res);
      document.getElementById('picked-loading').style.display = 'none';
      if (!_pickedState.rows.length) { document.getElementById('picked-empty').style.display='block'; return; }
      _renderPickedTable();
    }).catch(function(e){
      if (_currentRoute !== route) return;
      document.getElementById('picked-loading').style.display = 'none';
      var el = document.getElementById('picked-empty');
      if (el) { el.textContent = 'Load failed: '+(e.message||String(e)); el.style.display='block'; }
    });
  }

  /* [Sprint 2-D] Picked 테이블 렌더 + 핸들러 */
  function _renderPickedTable() {
    var tbody = document.getElementById('picked-tbody');
    var tbl = document.getElementById('picked-table');
    var cnt = document.getElementById('picked-count');
    var rows = _pickedState.rows;
    if (cnt) cnt.textContent = '(' + rows.length + ' LOTs)';
    if (!tbody || !tbl) return;
    tbl.style.display = '';
    tbody.innerHTML = rows.map(function(r){
      var lot = String(r.lot_no || '');
      var checked = _pickedState.selectedLots.has(lot) ? 'checked' : '';
      return '<tr class="picked-summary-row" data-lot="' + escapeHtml(lot) + '">' +
        '<td style="text-align:center"><input type="checkbox" ' + checked + ' onclick="event.stopPropagation();window.pickedToggleRow(\'' + escapeHtml(lot) + '\',this.checked)"></td>' +
        '<td style="width:24px;text-align:center;cursor:pointer" onclick="window.togglePickedDetail(\'' + escapeHtml(lot) + '\')"><span class="picked-expand-icon">▶</span></td>' +
        '<td class="mono-cell" style="color:var(--accent);font-weight:600;cursor:pointer" onclick="window.togglePickedDetail(\'' + escapeHtml(lot) + '\')">' + escapeHtml(lot) + '</td>' +
        '<td class="mono-cell">' + escapeHtml(r.picking_no || '') + '</td>' +
        '<td>' + escapeHtml(r.customer || r.picked_to || '') + '</td>' +
        '<td class="mono-cell" style="text-align:right">' + (r.tonbag_count || 0) + '</td>' +
        '<td class="mono-cell" style="text-align:right">' + (r.total_kg != null ? fmtN(r.total_kg) : '-') + '</td>' +
        '<td class="mono-cell">' + escapeHtml(r.picking_date || '') + '</td>' +
        '</tr>';
    }).join('');
  }

  window.pickedToggleRow = function(lot, checked) {
    if (checked) _pickedState.selectedLots.add(lot);
    else _pickedState.selectedLots.delete(lot);
  };
  window.pickedSelectAll = function(checked) {
    _pickedState.rows.forEach(function(r){
      var lot = String(r.lot_no || '');
      if (checked) _pickedState.selectedLots.add(lot);
      else _pickedState.selectedLots.delete(lot);
    });
    _renderPickedTable();
    var hdr = document.getElementById('picked-select-all');
    if (hdr) hdr.checked = checked;
  };
  function _pickedBulkAction(opts) {
    var lots = Array.from(_pickedState.selectedLots);
    if (!lots.length) { showToast('warn', opts.label + ': 선택된 LOT 없음'); return; }
    var preview = lots.slice(0, 5).join(', ') + (lots.length > 5 ? ' …외 ' + (lots.length - 5) : '');
    if (!confirm(opts.icon + ' ' + opts.label + '\n\n' + lots.length + '건 처리?\n' + preview)) return;
    var ok = 0, errs = [];
    Promise.all(lots.map(function(lot){
      return apiPost('/api/allocation/' + encodeURIComponent(lot) + opts.suffix, {})
        .then(function(res){ if (res && res.success) ok++; else errs.push({lot:lot, reason: res.message}); })
        .catch(function(e){ errs.push({lot:lot, reason: e.message || String(e)}); });
    })).then(function(){
      showToast(errs.length ? 'warn' : 'success', opts.label + ': ' + ok + '건 성공' + (errs.length ? ', ' + errs.length + '건 실패' : ''));
      _pickedState.selectedLots.clear();
      loadPickedPage();
    });
  }
  window.pickedConfirmSelected = function() {
    _pickedBulkAction({ icon: '✅', label: '출고 확정', suffix: '/confirm-outbound' });
  };
  window.pickedRevertSelected = function() {
    _pickedBulkAction({ icon: '↩️', label: 'Reserved 되돌림', suffix: '/revert-picked' });
  };
  window.pickedExportCsv = function() {
    var rows = _pickedState.rows;
    if (!rows.length) { showToast('warn', '내보낼 데이터 없음'); return; }
    var headers = ['lot_no','picking_no','customer','tonbag_count','total_kg','picking_date'];
    function csvEsc(v){ var s = String(v == null ? '' : v); if (/[,"\n]/.test(s)) s = '"' + s.replace(/"/g,'""') + '"'; return s; }
    var lines = [headers.join(',')];
    rows.forEach(function(r){
      lines.push(headers.map(function(h){ return csvEsc(r[h]); }).join(','));
    });
    var blob = new Blob(['\ufeff' + lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a'); a.href = url;
    var ts = new Date();
    a.download = 'picked_' + ts.getFullYear() + String(ts.getMonth()+1).padStart(2,'0') + String(ts.getDate()).padStart(2,'0') + '_' + String(ts.getHours()).padStart(2,'0') + String(ts.getMinutes()).padStart(2,'0') + '.csv';
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast('success', '📥 ' + a.download);
  };

  var _pickedExpandedLot = null;
  window.togglePickedDetail = function(lotNo) {
    var panel = document.getElementById('picked-detail-panel');
    var content = document.getElementById('picked-detail-content');
    var title = document.getElementById('picked-detail-title');

    if (_pickedExpandedLot === lotNo) {
      panel.style.display = 'none';
      _pickedExpandedLot = null;
      document.querySelectorAll('.picked-summary-row').forEach(function(r){ r.style.background=''; });
      document.querySelectorAll('.picked-expand-icon').forEach(function(i){ i.textContent='▶'; });
      return;
    }

    _pickedExpandedLot = lotNo;
    document.querySelectorAll('.picked-summary-row').forEach(function(r){
      if (r.dataset.lot === lotNo) {
        r.style.background = 'var(--bg-active)';
        r.querySelector('.picked-expand-icon').textContent = '▼';
      } else {
        r.style.background = '';
        r.querySelector('.picked-expand-icon').textContent = '▶';
      }
    });

    panel.style.display = 'block';
    title.textContent = '🚛 ' + lotNo + ' 톤백 상세';
    content.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text-muted)">⏳ 로딩...</div>';

    apiGet('/api/tonbags?lot_no=' + encodeURIComponent(lotNo)).then(function(res){
      var rows = extractRows(res);
      if (!rows.length) { content.innerHTML = '<div class="empty">톤백 데이터 없음</div>'; return; }
      var tbl = '<table class="data-table"><thead><tr><th>#</th><th>톤백ID</th><th>중량(kg)</th><th>위치</th><th>상태</th><th>피킹일</th></tr></thead><tbody>';
      tbl += rows.map(function(r, i){
        return '<tr><td>'+(i+1)+'</td><td class="mono-cell">'+escapeHtml(r.sub_lt||r.tonbag_id||'-')+'</td><td class="mono-cell" style="text-align:right">'+(r.weight!=null?Number(r.weight).toLocaleString():'-')+'</td><td>'+escapeHtml(r.location||'-')+'</td><td><span class="tag">'+escapeHtml(r.status||'-')+'</span></td><td>'+escapeHtml(r.picked_date||r.updated_at||'-')+'</td></tr>';
      }).join('');
      tbl += '</tbody></table>';
      content.innerHTML = '<p style="color:var(--text-muted);font-size:.85rem;margin-bottom:8px">' + rows.length + '개 톤백</p>' + tbl;
    }).catch(function(e){
      content.innerHTML = '<div class="empty">톤백 로드 실패: '+escapeHtml(e.message||'')+'</div>';
    });
  };

  /* ===================================================
     7c-2. PAGE: Inbound (입고 목록 — F009)
     /api/q/inbound-status → res.data.items
     columns: lot_no, lot_sqm, sap_no, bl_no, product,
              net_weight, current_weight, tonbag_count,
              status, inbound_date, arrival_date, warehouse, vessel
     =================================================== */
  /* _inboundAllRows: 전체 행 캐시 (필터용) */
  var _inboundAllRows = [];

  var STATUS_COLOR = {
    'INBOUND':'#1976d2','ALLOCATED':'#7b1fa2','PICKED':'#f57c00',
    'OUTBOUND':'#388e3c','RETURN':'#c62828','HOLD':'#616161'
  };

  function _renderInboundRows(rows) {
    var tbody = document.getElementById('inbound-tbody');
    var empty = document.getElementById('inbound-empty');
    var tbl   = document.getElementById('inbound-table');
    if (!tbody) return;
    if (!rows.length) {
      if (tbl)   tbl.style.display   = 'none';
      if (empty) { empty.textContent = '📭 해당 상태의 데이터 없음'; empty.style.display = 'block'; }
      return;
    }
    if (empty) empty.style.display = 'none';
    tbody.innerHTML = rows.map(function(r, i){
      var sc     = STATUS_COLOR[r.status] || '#888';
      var netMT  = r.net_weight     != null ? fmtN(r.net_weight     / 1000) : '-';
      var curMT  = r.current_weight != null ? fmtN(r.current_weight / 1000) : '-';
      return '<tr>' +
        '<td class="mono-cell" style="color:var(--text-muted)">'+(i+1)+'</td>' +
        '<td class="mono-cell" style="color:var(--accent);font-weight:600">'+escapeHtml(r.lot_no||'')+'</td>' +
        '<td class="mono-cell">'+escapeHtml(r.lot_sqm||'-')+'</td>' +
        '<td class="mono-cell">'+escapeHtml(r.sap_no||'-')+'</td>' +
        '<td class="mono-cell">'+escapeHtml(r.bl_no||'-')+'</td>' +
        '<td><span class="tag">'+escapeHtml(r.product||'-')+'</span></td>' +
        '<td class="mono-cell" style="text-align:right">'+netMT+'</td>' +
        '<td class="mono-cell" style="text-align:right">'+curMT+'</td>' +
        '<td class="mono-cell" style="text-align:center">'+(r.tonbag_count||0)+'</td>' +
        '<td><span style="color:'+sc+';font-weight:600;font-size:11px">'+escapeHtml(r.status||'-')+'</span></td>' +
        '<td class="mono-cell">'+escapeHtml((r.inbound_date||'').slice(0,10)||'-')+'</td>' +
        '<td class="mono-cell">'+escapeHtml((r.arrival_date||'').slice(0,10)||'-')+'</td>' +
        '<td><span class="tag">'+escapeHtml(r.warehouse||'-')+'</span></td>' +
        '<td>'+escapeHtml(r.vessel||'-')+'</td>' +
        '</tr>';
    }).join('');
    if (tbl) tbl.style.display = '';
    dbgLog('📋','inbound-table shown', 'rows='+rows.length+' tbl='+(tbl?tbl.style.display:'?'), '#4caf50');
  }

  function _inboundFilter(status) {
    /* 필터 버튼 active 상태 갱신 */
    document.querySelectorAll('.inbound-filter-btn').forEach(function(b){
      b.style.fontWeight = (b.dataset.status === status) ? '700' : '400';
      b.style.opacity    = (b.dataset.status === status) ? '1'   : '0.55';
    });
    var filtered = status === 'ALL'
      ? _inboundAllRows
      : _inboundAllRows.filter(function(r){ return r.status === status; });
    var count = document.getElementById('inbound-count');
    if (count) count.textContent = filtered.length + ' / ' + _inboundAllRows.length + '건';
    _renderInboundRows(filtered);
  }
  window._inboundFilter = _inboundFilter;   /* HTML onclick에서 호출 */

  function loadInboundPage() {
    var route = _currentRoute;
    var c = document.getElementById('page-container');
    if (!c) return;
    _inboundAllRows = [];

    var FILTERS = ['ALL','INBOUND','ALLOCATED','PICKED','OUTBOUND','RETURN','HOLD'];
    var filterBtns = FILTERS.map(function(s){
      var col = STATUS_COLOR[s] || '#555';
      return '<button class="inbound-filter-btn" data-status="'+s+'" '+
        'onclick="_inboundFilter(\''+s+'\')" '+
        'style="border:1px solid '+col+';color:'+col+';background:transparent;'+
        'border-radius:4px;padding:3px 10px;cursor:pointer;font-size:12px;font-weight:400;opacity:0.55">'+s+'</button>';
    }).join('');

    c.innerHTML = [
      '<section class="page" data-page="inbound">',
      '<div style="display:flex;align-items:center;gap:12px;padding:8px 0 10px;flex-wrap:wrap">',
      '<h2 style="margin:0;white-space:nowrap">📥 입고 목록</h2>',
      '<div style="display:flex;gap:6px;flex-wrap:wrap">'+filterBtns+'</div>',
      '<span id="inbound-count" style="margin-left:auto;font-size:12px;color:var(--text-muted)">--</span>',
      '<button class="btn btn-secondary" onclick="renderPage(\'inbound\')" style="white-space:nowrap">🔁 새로고침</button>',
      '</div>',
      '<div id="inbound-loading" style="padding:40px;text-align:center;color:var(--text-muted)">⏳ 데이터 로딩 중...</div>',
      '<div style="overflow-x:auto">',
      '<table class="data-table" id="inbound-table" style="display:none">',
      '<thead><tr>',
      '<th>#</th><th>LOT No</th><th>SQM LOT</th><th>SAP No</th><th>BL No</th>',
      '<th>제품</th><th>순중량(MT)</th><th>현재중량(MT)</th><th>톤백수</th>',
      '<th>상태</th><th>입고일자</th><th>도착일자</th><th>창고</th><th>선박</th>',
      '</tr></thead>',
      '<tbody id="inbound-tbody"></tbody>',
      '</table>',
      '</div>',
      '<div class="empty" id="inbound-empty" style="display:none;padding:60px;text-align:center;color:var(--text-muted)">📭 입고 데이터 없음</div>',
      '</section>'
    ].join('');

    apiGet('/api/q/inbound-status').then(function(res){
      if (_currentRoute !== route) return;
      _inboundAllRows = (res.data && res.data.items) || [];
      var total = _inboundAllRows.length;
      document.getElementById('inbound-loading').style.display = 'none';
      if (!total) {
        document.getElementById('inbound-empty').style.display = 'block';
        return;
      }
      _inboundFilter('ALL');   /* ALL 버튼 active + 전체 렌더 */
      dbgLog('📥','inbound-page','total='+total,'#4caf50');
    }).catch(function(e){
      if (_currentRoute !== route) return;
      document.getElementById('inbound-loading').style.display = 'none';
      var el = document.getElementById('inbound-empty');
      if (el) { el.textContent = '❌ 로드 실패: '+(e.message||String(e)); el.style.display = 'block'; }
      showToast('error', '입고 목록 로드 실패');
      dbgLog('❌','inbound-page',String(e),'#f44336');
    });
  }

  /* ===================================================
     7d. PAGE: Outbound (출고 현황 — F025/F037)
     /api/q/outbound-status → res.data.items
     columns: lot_no, movement_type, qty_kg, customer,
              from_location, to_location, movement_date,
              source_type, actor, remarks
     =================================================== */
  /* ===================================================
     7d. PAGE: Outbound/Sold — 2단 구조 (LOT 요약 + 톤백 상세)
     =================================================== */
  function loadOutboundPage() {
    var route = _currentRoute;
    var c = document.getElementById('page-container');
    if (!c) return;
    if (!_outboundState.selectedLots) _outboundState.selectedLots = new Set();
    _outboundState.selectedLots.clear();
    c.innerHTML = [
      '<section class="page" data-page="outbound">',
      '<div style="display:flex;align-items:center;gap:12px;padding:4px 0 8px">',
      '  <h2 style="margin:0">📤 출고 완료 (Sold / Outbound)</h2>',
      '  <span id="outbound-count" style="font-size:12px;color:var(--text-muted)"></span>',
      '  <button class="btn btn-secondary" onclick="renderPage(\'outbound\')" style="margin-left:auto">🔁 새로고침</button>',
      '</div>',
      /* 액션 툴바 */
      '<div style="display:flex;flex-wrap:wrap;align-items:center;gap:6px;padding:8px 10px;background:var(--panel);border:1px solid var(--panel-border);border-radius:6px;margin-bottom:8px">',
      '  <button class="btn btn-danger" onclick="window.outboundReturnSelected()" title="OUTBOUND → RETURN">🔄 반품 확정</button>',
      '  <button class="btn" onclick="window.outboundRevertSelected()" title="OUTBOUND → PICKED 되돌림">↩️ Picked 되돌림</button>',
      '  <span style="width:1px;height:20px;background:var(--panel-border);margin:0 4px"></span>',
      '  <label style="font-size:12px">📅 From:</label><input type="date" id="outbound-from" onchange="window.outboundDateFilter()" style="padding:3px 6px;background:var(--bg-hover);border:1px solid var(--panel-border);border-radius:3px;font-size:12px">',
      '  <label style="font-size:12px">To:</label><input type="date" id="outbound-to" onchange="window.outboundDateFilter()" style="padding:3px 6px;background:var(--bg-hover);border:1px solid var(--panel-border);border-radius:3px;font-size:12px">',
      '  <button class="btn" onclick="window.outboundClearFilter()">✖ 필터 해제</button>',
      '  <span style="width:1px;height:20px;background:var(--panel-border);margin:0 4px"></span>',
      '  <button class="btn" onclick="window.outboundExportCsv()">📥 Excel 내보내기</button>',
      '  <button class="btn" onclick="window.outboundSelectAll(true)">☑ 전체 선택</button>',
      '  <button class="btn" onclick="window.outboundSelectAll(false)">☐ 해제</button>',
      '</div>',
      '<div id="outbound-loading" style="padding:40px;text-align:center;color:var(--text-muted)">⏳ 데이터 로딩 중...</div>',
      '<div style="overflow-x:auto">',
      '  <table class="data-table" id="outbound-table" style="display:none">',
      '  <thead><tr>',
      '    <th style="width:32px"><input type="checkbox" id="outbound-select-all" onclick="window.outboundSelectAll(this.checked)"></th>',
      '    <th></th><th>#</th><th>LOT No</th><th>판매주문No</th><th>고객사</th><th style="text-align:right">톤백수</th><th style="text-align:right">중량(kg)</th><th>출고일</th>',
      '  </tr></thead>',
      '  <tbody id="outbound-tbody"></tbody>',
      '  </table>',
      '</div>',
      '<div class="empty" id="outbound-empty" style="display:none;padding:60px;text-align:center;color:var(--text-muted)">📭 출고 데이터 없음</div>',
      '<div id="outbound-detail-panel" style="display:none;margin-top:16px;border-top:2px solid var(--panel-border);padding-top:16px">',
      '  <h3 id="outbound-detail-title" style="margin:0 0 12px 0">톤백 상세</h3>',
      '  <div id="outbound-detail-content"></div>',
      '</div>',
      '</section>'
    ].join('');

    apiGet('/api/q/sold-list').then(function(res){
      if (_currentRoute !== route) return;
      _outboundState.rows = extractRows(res);
      document.getElementById('outbound-loading').style.display = 'none';
      if (!_outboundState.rows.length) {
        document.getElementById('outbound-empty').style.display = 'block';
        return;
      }
      _renderOutboundTable();
      dbgLog('📤','outbound-page','rows=' + _outboundState.rows.length,'#4caf50');
    }).catch(function(e){
      if (_currentRoute !== route) return;
      document.getElementById('outbound-loading').style.display = 'none';
      var el = document.getElementById('outbound-empty');
      if (el) { el.textContent = '❌ 로드 실패: '+(e.message||String(e)); el.style.display = 'block'; }
      showToast('error', '출고 현황 로드 실패');
    });
  }

  /* [Sprint 2-D] Outbound 상태 + 핸들러 */
  var _outboundState = { rows: [], selectedLots: null, dateFrom: '', dateTo: '' };

  function _renderOutboundTable() {
    var tbody = document.getElementById('outbound-tbody');
    var tbl = document.getElementById('outbound-table');
    var cnt = document.getElementById('outbound-count');
    var rows = _outboundState.rows.slice();
    if (_outboundState.dateFrom) rows = rows.filter(function(r){ return (r.sold_date || '') >= _outboundState.dateFrom; });
    if (_outboundState.dateTo)   rows = rows.filter(function(r){ return (r.sold_date || '') <= _outboundState.dateTo; });
    if (cnt) cnt.textContent = '(' + rows.length + ' / ' + _outboundState.rows.length + ' LOTs)';
    if (!tbody || !tbl) return;
    tbl.style.display = '';
    tbody.innerHTML = rows.map(function(r, i){
      var lot = String(r.lot_no || '');
      var checked = _outboundState.selectedLots.has(lot) ? 'checked' : '';
      return '<tr class="outbound-summary-row" data-lot="' + escapeHtml(lot) + '">' +
        '<td style="text-align:center"><input type="checkbox" ' + checked + ' onclick="event.stopPropagation();window.outboundToggleRow(\'' + escapeHtml(lot) + '\',this.checked)"></td>' +
        '<td style="width:24px;text-align:center;cursor:pointer" onclick="window.toggleOutboundDetail(\'' + escapeHtml(lot) + '\')"><span class="outbound-expand-icon">▶</span></td>' +
        '<td class="mono-cell" style="color:var(--text-muted)">' + (i + 1) + '</td>' +
        '<td class="mono-cell" style="color:var(--accent);font-weight:600;cursor:pointer" onclick="window.toggleOutboundDetail(\'' + escapeHtml(lot) + '\')">' + escapeHtml(lot) + '</td>' +
        '<td class="mono-cell">' + escapeHtml(r.sales_order_no || '-') + '</td>' +
        '<td>' + escapeHtml(r.customer || '-') + '</td>' +
        '<td class="mono-cell" style="text-align:right">' + (r.tonbag_count || 0) + '</td>' +
        '<td class="mono-cell" style="text-align:right">' + (r.total_kg != null ? fmtN(r.total_kg) : '-') + '</td>' +
        '<td class="mono-cell">' + escapeHtml(r.sold_date || '-') + '</td>' +
        '</tr>';
    }).join('');
  }

  window.outboundToggleRow = function(lot, checked) {
    if (checked) _outboundState.selectedLots.add(lot);
    else _outboundState.selectedLots.delete(lot);
  };
  window.outboundSelectAll = function(checked) {
    _outboundState.rows.forEach(function(r){
      var lot = String(r.lot_no || '');
      if (checked) _outboundState.selectedLots.add(lot);
      else _outboundState.selectedLots.delete(lot);
    });
    _renderOutboundTable();
    var hdr = document.getElementById('outbound-select-all');
    if (hdr) hdr.checked = checked;
  };
  window.outboundDateFilter = function() {
    _outboundState.dateFrom = (document.getElementById('outbound-from') || {}).value || '';
    _outboundState.dateTo = (document.getElementById('outbound-to') || {}).value || '';
    _renderOutboundTable();
  };
  window.outboundClearFilter = function() {
    _outboundState.dateFrom = ''; _outboundState.dateTo = '';
    var f = document.getElementById('outbound-from'); if (f) f.value = '';
    var t = document.getElementById('outbound-to'); if (t) t.value = '';
    _renderOutboundTable();
  };
  function _outboundBulkAction(opts) {
    var lots = Array.from(_outboundState.selectedLots);
    if (!lots.length) { showToast('warn', opts.label + ': 선택된 LOT 없음'); return; }
    var preview = lots.slice(0, 5).join(', ') + (lots.length > 5 ? ' …외 ' + (lots.length - 5) : '');
    if (!confirm(opts.icon + ' ' + opts.label + '\n\n' + lots.length + '건 처리?\n' + preview)) return;
    var ok = 0, errs = [];
    Promise.all(lots.map(function(lot){
      return apiPost('/api/allocation/' + encodeURIComponent(lot) + opts.suffix, {})
        .then(function(res){ if (res && res.success) ok++; else errs.push({lot:lot, reason: res.message}); })
        .catch(function(e){ errs.push({lot:lot, reason: e.message || String(e)}); });
    })).then(function(){
      showToast(errs.length ? 'warn' : 'success', opts.label + ': ' + ok + '건 성공' + (errs.length ? ', ' + errs.length + '건 실패' : ''));
      _outboundState.selectedLots.clear();
      loadOutboundPage();
    });
  }
  window.outboundReturnSelected = function() {
    _outboundBulkAction({ icon: '🔄', label: '반품 확정', suffix: '/return-outbound' });
  };
  window.outboundRevertSelected = function() {
    _outboundBulkAction({ icon: '↩️', label: 'Picked 되돌림', suffix: '/revert-outbound' });
  };
  window.outboundExportCsv = function() {
    var rows = _outboundState.rows;
    if (_outboundState.dateFrom) rows = rows.filter(function(r){ return (r.sold_date || '') >= _outboundState.dateFrom; });
    if (_outboundState.dateTo)   rows = rows.filter(function(r){ return (r.sold_date || '') <= _outboundState.dateTo; });
    if (!rows.length) { showToast('warn', '내보낼 데이터 없음'); return; }
    var headers = ['lot_no','sales_order_no','customer','tonbag_count','total_kg','sold_date'];
    function csvEsc(v){ var s = String(v == null ? '' : v); if (/[,"\n]/.test(s)) s = '"' + s.replace(/"/g,'""') + '"'; return s; }
    var lines = [headers.join(',')];
    rows.forEach(function(r){
      lines.push(headers.map(function(h){ return csvEsc(r[h]); }).join(','));
    });
    var blob = new Blob(['\ufeff' + lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a'); a.href = url;
    var ts = new Date();
    a.download = 'outbound_' + ts.getFullYear() + String(ts.getMonth()+1).padStart(2,'0') + String(ts.getDate()).padStart(2,'0') + '_' + String(ts.getHours()).padStart(2,'0') + String(ts.getMinutes()).padStart(2,'0') + '.csv';
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast('success', '📥 ' + a.download);
  };

  var _outboundExpandedLot = null;
  window.toggleOutboundDetail = function(lotNo) {
    var panel = document.getElementById('outbound-detail-panel');
    var content = document.getElementById('outbound-detail-content');
    var title = document.getElementById('outbound-detail-title');

    if (_outboundExpandedLot === lotNo) {
      panel.style.display = 'none';
      _outboundExpandedLot = null;
      document.querySelectorAll('.outbound-summary-row').forEach(function(r){ r.style.background=''; });
      document.querySelectorAll('.outbound-expand-icon').forEach(function(i){ i.textContent='▶'; });
      return;
    }

    _outboundExpandedLot = lotNo;
    document.querySelectorAll('.outbound-summary-row').forEach(function(r){
      if (r.dataset.lot === lotNo) {
        r.style.background = 'var(--bg-active)';
        r.querySelector('.outbound-expand-icon').textContent = '▼';
      } else {
        r.style.background = '';
        r.querySelector('.outbound-expand-icon').textContent = '▶';
      }
    });

    panel.style.display = 'block';
    title.textContent = '📤 ' + lotNo + ' 톤백 상세';
    content.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text-muted)">⏳ 로딩...</div>';

    apiGet('/api/tonbags?lot_no=' + encodeURIComponent(lotNo)).then(function(res){
      var rows = extractRows(res);
      if (!rows.length) { content.innerHTML = '<div class="empty">톤백 데이터 없음</div>'; return; }
      var tbl = '<table class="data-table"><thead><tr><th>#</th><th>톤백ID</th><th>중량(kg)</th><th>위치</th><th>상태</th><th>출고일</th></tr></thead><tbody>';
      tbl += rows.map(function(r, i){
        return '<tr><td>'+(i+1)+'</td><td class="mono-cell">'+escapeHtml(r.sub_lt||r.tonbag_id||'-')+'</td><td class="mono-cell" style="text-align:right">'+(r.weight!=null?Number(r.weight).toLocaleString():'-')+'</td><td>'+escapeHtml(r.location||'-')+'</td><td><span class="tag">'+escapeHtml(r.status||'-')+'</span></td><td>'+escapeHtml(r.sold_date||r.updated_at||'-')+'</td></tr>';
      }).join('');
      tbl += '</tbody></table>';
      content.innerHTML = '<p style="color:var(--text-muted);font-size:.85rem;margin-bottom:8px">' + rows.length + '개 톤백</p>' + tbl;
    }).catch(function(e){
      content.innerHTML = '<div class="empty">톤백 로드 실패: '+escapeHtml(e.message||'')+'</div>';
    });
  };

  /* ===================================================
     7e. PAGE: Return
     =================================================== */
  function loadReturnPage() {
    var route = _currentRoute;
    var c = document.getElementById('page-container');
    if (!c) return;
    c.innerHTML = [
      '<section class="page" data-page="return">',
      '<h2>Return - Re-inbound</h2>',
      '<div class="toolbar-mini"><button class="btn btn-secondary" onclick="renderPage(\'return\')">Refresh</button></div>',
      '<div id="return-loading" style="padding:40px;text-align:center">Loading...</div>',
      '<table class="data-table" id="return-table" style="display:none">',
      '<thead><tr><th>LOT</th><th>Product</th><th>Qty</th><th>Date</th><th>Reason</th></tr></thead>',
      '<tbody id="return-tbody"></tbody></table>',
      '<div class="empty" id="return-empty" style="display:none">No return data</div>',
      '</section>'
    ].join('');
    /* return-stats는 통계 구조(by_reason/monthly_trend)라 items 없음 → inventory?status=RETURN 직접 조회 */
    apiGet('/api/inventory?status=RETURN').then(function(res){
      if (_currentRoute !== route) return;
      var rows = extractRows(res);
      renderReturnRows(rows, route);
    }).catch(function(){
      if (_currentRoute !== route) return;
      document.getElementById('return-loading').style.display = 'none';
      document.getElementById('return-empty').style.display = 'block';
    });
  }

  function renderReturnRows(rows, route) {
    if (_currentRoute !== route) return;
    document.getElementById('return-loading').style.display = 'none';
    if (!rows.length) { document.getElementById('return-empty').style.display='block'; return; }
    var tbody = document.getElementById('return-tbody');
    if (tbody) tbody.innerHTML = rows.map(function(r){
      return '<tr><td>'+escapeHtml(r.lot||'')+'</td><td>'+escapeHtml(r.product||'')+'</td><td>'+(r.bags||r.qty||'')+'</td><td>'+escapeHtml(r.date||'')+'</td><td>'+escapeHtml(r.reason||'')+'</td></tr>';
    }).join('');
    document.getElementById('return-table').style.display = '';
  }

  /* ===================================================
     7f. PAGE: Move
     =================================================== */
  function loadMovePage() {
    var route = _currentRoute;
    var c = document.getElementById('page-container');
    if (!c) return;
    c.innerHTML = [
      '<section class="page" data-page="move">',
      '<h2>Move - Inventory Relocation</h2>',
      '<div class="card" style="padding:20px;margin-bottom:16px">',
      '<h3 style="margin-bottom:12px">Execute Move</h3>',
      '<div style="display:flex;gap:12px;flex-wrap:wrap;align-items:center">',
      '<input id="move-barcode" class="input" placeholder="Tonbag barcode" style="width:200px">',
      '<input id="move-dest" class="input" placeholder="Destination (e.g. A-3-2)" style="width:200px">',
      '<button class="btn btn-primary" onclick="window.executeMove()">Execute Move</button>',
      '</div></div>',
      '<div id="move-loading" style="padding:20px;text-align:center">Loading history...</div>',
      '<table class="data-table" id="move-table" style="display:none">',
      '<thead><tr><th>Date</th><th>LOT No</th><th>Type</th><th>Qty(MT)</th><th>From</th><th>To</th><th>By</th></tr></thead>',
      '<tbody id="move-tbody"></tbody></table>',
      '<div class="empty" id="move-empty" style="display:none">No movement history</div>',
      '</section>'
    ].join('');
    apiGet('/api/q/movement-history').then(function(res){
      if (_currentRoute !== route) return;
      var rows = extractRows(res);
      document.getElementById('move-loading').style.display = 'none';
      if (!rows.length) { document.getElementById('move-empty').style.display='block'; return; }
      var tbody = document.getElementById('move-tbody');
      if (tbody) tbody.innerHTML = rows.map(function(r){
        var qtyMT = r.qty_mt != null ? fmtN(r.qty_mt) : (r.qty_kg != null ? fmtN(r.qty_kg/1000) : '-');
        return '<tr>' +
          '<td class="mono-cell">'+escapeHtml(r.movement_date||r.moved_at||r.date||'')+'</td>' +
          '<td class="mono-cell" style="color:var(--accent)">'+escapeHtml(r.lot_no||r.sub_lt||r.barcode||'')+'</td>' +
          '<td>'+escapeHtml(r.movement_type||'')+'</td>' +
          '<td class="mono-cell" style="text-align:right">'+qtyMT+'</td>' +
          '<td class="mono-cell">'+escapeHtml(r.from_location||'-')+'</td>' +
          '<td class="mono-cell" style="color:var(--accent)">'+escapeHtml(r.to_location||'-')+'</td>' +
          '<td>'+escapeHtml(r.actor||r.moved_by||'system')+'</td></tr>';
      }).join('');
      document.getElementById('move-table').style.display = '';
    }).catch(function(){
      if (_currentRoute !== route) return;
      document.getElementById('move-loading').style.display = 'none';
      document.getElementById('move-empty').style.display = 'block';
    });
  }

  window.executeMove = function() {
    var barcode = (document.getElementById('move-barcode')||{}).value||'';
    var dest = (document.getElementById('move-dest')||{}).value||'';
    if (!barcode||!dest) { showToast('warning','Enter barcode and destination'); return; }
    apiPost('/api/action/inventory-move',{barcode:barcode,destination:dest})
      .then(function(){ showToast('success',barcode+' moved to '+dest); renderPage('move'); })
      .catch(function(e){
        if (e.status===501) showToast('info','Move (coming soon)');
        else showToast('error','Move failed: '+(e.message||String(e)));
      });
  };

  /* ===================================================
     7g. PAGE: Log
     =================================================== */
  function loadLogPage() {
    var route = _currentRoute;
    var c = document.getElementById('page-container');
    if (!c) return;
    c.innerHTML = [
      '<section class="page" data-page="log">',
      '<h2>Log - Activity Log</h2>',
      '<div class="toolbar-mini">',
      '<button class="btn btn-secondary" onclick="renderPage(\'log\')">Refresh</button>',
      '<select id="log-limit" class="select" style="margin-left:8px" onchange="renderPage(\'log\')">',
      '<option value="100">Last 100</option>',
      '<option value="500">Last 500</option>',
      '<option value="1000">Last 1000</option>',
      '</select></div>',
      '<div id="log-loading" style="padding:40px;text-align:center">Loading...</div>',
      '<table class="data-table" id="log-table" style="display:none">',
      '<thead><tr><th>Time</th><th>Type</th><th>LOT</th><th>Detail</th></tr></thead>',
      '<tbody id="log-tbody"></tbody></table>',
      '<div class="empty" id="log-empty" style="display:none">No logs</div>',
      '</section>'
    ].join('');
    var limit = 100;
    try { var el=document.getElementById('log-limit'); if(el) limit=parseInt(el.value)||100; } catch {}
    apiGet('/api/q/audit-log?limit='+limit).then(function(res){
      if (_currentRoute !== route) return;
      var rows = extractRows(res);
      document.getElementById('log-loading').style.display = 'none';
      if (!rows.length) { document.getElementById('log-empty').style.display='block'; return; }
      var tbody = document.getElementById('log-tbody');
      if (tbody) tbody.innerHTML = rows.map(function(r){
        return '<tr>' +
          '<td class="mono-cell">'+escapeHtml(r.created_at||r.time||r.timestamp||'')+'</td>' +
          '<td>'+escapeHtml(r.event_type||r.type||r.action||'')+'</td>' +
          '<td class="mono-cell">'+escapeHtml(r.lot_no||r.lot||r.tonbag_id||'')+'</td>' +
          '<td>'+escapeHtml(r.event_data||r.user_note||r.note||r.memo||r.detail||'')+'</td></tr>';
      }).join('');
      document.getElementById('log-table').style.display = '';
    }).catch(function(e){
      if (_currentRoute !== route) return;
      document.getElementById('log-loading').style.display = 'none';
      var el=document.getElementById('log-empty');
      if (el) { el.textContent='Load failed: '+(e.message||String(e)); el.style.display='block'; }
    });
  }

  /* ===================================================
     7h. PAGE: Scan + PDF Upload
     =================================================== */
  /* =====================================================================
     [Sprint 1-7] Scan 탭 — 5단계 상태 전환 + 빠른스캔 + 무음 + 5열 history
     v864-2 source: tabs/scan_tab.py (805줄)
     ===================================================================== */
  var _scanState = {
    quickMode:  false,   /* ⚡ 빠른 스캔: 다이얼로그/팝업 스킵, 자동 처리 */
    silentMode: false,   /* 🔕 무음: 에러 토스트 억제 (오디오는 향후) */
    lastAction: 'lookup',
  };

  function loadScanPage() {
    var c = document.getElementById('page-container');
    if (!c) return;
    /* localStorage 복원 */
    try {
      _scanState.quickMode = localStorage.getItem('sqm.scan.quick') === '1';
      _scanState.silentMode = localStorage.getItem('sqm.scan.silent') === '1';
    } catch (e) {}

    c.innerHTML = [
      '<section class="page" data-page="scan">',
      '<div style="display:flex;align-items:center;gap:12px;padding:4px 0 10px">',
      '  <h2 style="margin:0">📷 Scan — 바코드 상태 전환</h2>',
      '  <span style="font-size:11px;color:var(--text-muted)">5단계 워크플로우: AVAILABLE → RESERVED → PICKED → OUTBOUND → RETURN → AVAILABLE</span>',
      '</div>',
      /* 입력 + 토글 */
      '<div style="display:flex;gap:8px;align-items:center;background:var(--panel);padding:10px;border-radius:6px;margin-bottom:8px;flex-wrap:wrap">',
      '  <input id="scan-input" placeholder="🔍 바코드 스캔 또는 입력 + Enter" autocomplete="off" autofocus',
      '    style="flex:1;min-width:200px;padding:8px 12px;background:var(--bg);color:var(--fg);border:1px solid var(--panel-border);border-radius:4px;font-family:Consolas,monospace;font-size:14px">',
      '  <label style="display:flex;align-items:center;gap:4px;font-size:12px;cursor:pointer" title="활성 시 액션 버튼 클릭으로 즉시 처리, 비활성 시 스캔 → 액션 선택">',
      '    <input type="checkbox" id="scan-quick" ' + (_scanState.quickMode ? 'checked' : '') + ' onchange="window.scanToggleMode(\'quick\', this.checked)"> ⚡ 빠른 스캔',
      '  </label>',
      '  <label style="display:flex;align-items:center;gap:4px;font-size:12px;cursor:pointer" title="활성 시 에러 토스트 표시 안 함">',
      '    <input type="checkbox" id="scan-silent" ' + (_scanState.silentMode ? 'checked' : '') + ' onchange="window.scanToggleMode(\'silent\', this.checked)"> 🔕 무음',
      '  </label>',
      '  <button class="btn" onclick="window.scanClearHist()">🧹 이력 초기화</button>',
      '</div>',
      /* 5단계 액션 버튼 */
      '<div style="display:grid;grid-template-columns:repeat(5,1fr);gap:6px;margin-bottom:12px">',
      '  <button class="btn" style="background:#66bb6a;color:#fff;font-weight:700;padding:12px 8px" onclick="window.scanAction(\'reserve\')" title="AVAILABLE → RESERVED">📌 배정 등록</button>',
      '  <button class="btn" style="background:#ffa726;color:#000;font-weight:700;padding:12px 8px" onclick="window.scanAction(\'pick\')" title="RESERVED → PICKED">🚛 화물 결정</button>',
      '  <button class="btn" style="background:#42a5f5;color:#fff;font-weight:700;padding:12px 8px" onclick="window.scanAction(\'outbound\')" title="PICKED → OUTBOUND">📤 출고 확정</button>',
      '  <button class="btn" style="background:#ec407a;color:#fff;font-weight:700;padding:12px 8px" onclick="window.scanAction(\'return\')" title="OUTBOUND → RETURN">🔄 반품 등록</button>',
      '  <button class="btn" style="background:#9e9e9e;color:#fff;font-weight:700;padding:12px 8px" onclick="window.scanAction(\'restock\')" title="RETURN → AVAILABLE">♻️ 재입고</button>',
      '</div>',
      /* 마지막 결과 */
      '<div id="scan-last-result" style="margin-bottom:8px"></div>',
      /* 5열 history */
      '<div style="background:var(--panel);border:1px solid var(--panel-border);border-radius:6px;padding:10px">',
      '  <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">',
      '    <strong style="font-size:13px">📋 스캔 이력</strong>',
      '    <span id="scan-hist-count" style="font-size:11px;color:var(--text-muted)">(0건)</span>',
      '    <span style="margin-left:auto;font-size:11px;color:var(--text-muted)">최신 50건</span>',
      '  </div>',
      '  <div style="max-height:340px;overflow-y:auto">',
      '    <table class="data-table" style="font-size:11px"><thead><tr>',
      '      <th>시간</th><th>바코드</th><th>액션</th><th>결과</th><th>상세</th>',
      '    </tr></thead>',
      '    <tbody id="scan-history-tbody">',
      '      <tr><td colspan="5" style="padding:30px;text-align:center;color:var(--text-muted)">스캔 이력 없음</td></tr>',
      '    </tbody></table>',
      '  </div>',
      '</div>',
      '</section>'
    ].join('');

    /* Enter → 빠른 스캔이면 lastAction 적용, 아니면 lookup */
    var inp = document.getElementById('scan-input');
    if (inp) {
      inp.addEventListener('keydown', function(e){
        if (e.key === 'Enter') {
          e.preventDefault();
          var bc = inp.value.trim();
          if (!bc) return;
          var act = _scanState.quickMode ? _scanState.lastAction : 'lookup';
          window.scanProcess(bc, act);
          inp.value = '';
        }
      });
      setTimeout(function(){ inp.focus(); }, 100);
    }
    _scanRenderHistory();
  }

  /* 토글 */
  window.scanToggleMode = function(mode, checked) {
    if (mode === 'quick')  { _scanState.quickMode = checked; try { localStorage.setItem('sqm.scan.quick', checked ? '1' : '0'); } catch(e){} }
    if (mode === 'silent') { _scanState.silentMode = checked; try { localStorage.setItem('sqm.scan.silent', checked ? '1' : '0'); } catch(e){} }
    showToast('info', (mode === 'quick' ? '⚡ 빠른 스캔' : '🔕 무음') + ' ' + (checked ? 'ON' : 'OFF'));
  };

  /* 액션 버튼 클릭 — 입력값 또는 최근 바코드 사용 */
  window.scanAction = function(action) {
    var inp = document.getElementById('scan-input');
    var bc = (inp ? inp.value.trim() : '');
    if (!bc) {
      /* lastBarcode 사용 (history 첫 항목) */
      bc = (_scanHistory[0] && _scanHistory[0].barcode) || '';
    }
    if (!bc) {
      showToast('warn', '바코드를 먼저 스캔/입력하세요');
      if (inp) inp.focus();
      return;
    }
    _scanState.lastAction = action;
    window.scanProcess(bc, action);
    if (inp) { inp.value = ''; inp.focus(); }
  };

  window.scanProcess = function(barcode, action) {
    if (!barcode) return;
    apiPost('/api/scan/process', { barcode: barcode, action: action })
      .then(function(res){
        var ok = res && res.success;
        var level = res.level || (ok ? 'ok' : 'fail');
        var msg = res.message || (ok ? '완료' : '실패');
        _scanAddHist({ barcode: barcode, action: action, level: level, message: msg, data: res.data });
        _scanRenderLastResult(barcode, action, level, msg);
        if (ok) showToast('success', msg);
        else if (!_scanState.silentMode) showToast(level === 'warn' ? 'warn' : 'error', msg);
      })
      .catch(function(e){
        _scanAddHist({ barcode: barcode, action: action, level: 'fail', message: e.message || String(e) });
        if (!_scanState.silentMode) showToast('error', '스캔 오류: ' + (e.message || String(e)));
      });
  };

  function _scanAddHist(entry) {
    var now = new Date();
    entry.time = [now.getHours(), now.getMinutes(), now.getSeconds()].map(function(n){ return String(n).padStart(2,'0'); }).join(':');
    _scanHistory.unshift(entry);
    if (_scanHistory.length > 50) _scanHistory.pop();
    _scanRenderHistory();
  }

  function _scanRenderHistory() {
    var tbody = document.getElementById('scan-history-tbody');
    var cnt = document.getElementById('scan-hist-count');
    if (cnt) cnt.textContent = '(' + _scanHistory.length + '건)';
    if (!tbody) return;
    if (!_scanHistory.length) {
      tbody.innerHTML = '<tr><td colspan="5" style="padding:30px;text-align:center;color:var(--text-muted)">스캔 이력 없음</td></tr>';
      return;
    }
    var actLabels = {
      lookup:   '🔍 조회',
      reserve:  '📌 배정 등록',
      pick:     '🚛 화물 결정',
      outbound: '📤 출고 확정',
      return:   '🔄 반품 등록',
      restock:  '♻️ 재입고',
    };
    var levelStyle = {
      ok:   'background:rgba(102,187,106,.1);color:var(--success)',
      warn: 'background:rgba(255,167,38,.15);color:var(--warning)',
      fail: 'background:rgba(244,67,54,.15);color:var(--danger)',
    };
    var levelIcon = { ok: '✅', warn: '⚠️', fail: '❌' };

    tbody.innerHTML = _scanHistory.map(function(h){
      var stl = levelStyle[h.level] || '';
      return '<tr style="' + stl + '">' +
        '<td class="mono-cell" style="width:80px">' + h.time + '</td>' +
        '<td class="mono-cell" style="font-weight:600">' + escapeHtml(h.barcode) + '</td>' +
        '<td>' + (actLabels[h.action] || escapeHtml(h.action)) + '</td>' +
        '<td style="text-align:center">' + (levelIcon[h.level] || '') + '</td>' +
        '<td style="font-size:11px">' + escapeHtml(h.message || '') + '</td>' +
        '</tr>';
    }).join('');
  }

  function _scanRenderLastResult(barcode, action, level, msg) {
    var el = document.getElementById('scan-last-result');
    if (!el) return;
    var color = level === 'ok' ? 'var(--success)' : level === 'warn' ? 'var(--warning)' : 'var(--danger)';
    var bg    = level === 'ok' ? 'rgba(102,187,106,.1)' : level === 'warn' ? 'rgba(255,167,38,.12)' : 'rgba(244,67,54,.12)';
    var icon  = level === 'ok' ? '✅' : level === 'warn' ? '⚠️' : '❌';
    el.innerHTML =
      '<div style="padding:8px 12px;background:' + bg + ';border-left:3px solid ' + color + ';border-radius:4px;font-size:12px">' +
      '<strong style="color:' + color + '">' + icon + ' ' + escapeHtml(barcode) + '</strong> · ' + escapeHtml(msg) + '</div>';
  }

  window.scanClearHist = function() {
    if (!_scanHistory.length) { showToast('info', '이력 없음'); return; }
    if (!confirm('스캔 이력 초기화 (' + _scanHistory.length + '건)?')) return;
    _scanHistory = [];
    _scanRenderHistory();
    var lr = document.getElementById('scan-last-result');
    if (lr) lr.innerHTML = '';
    showToast('success', '이력 초기화됨');
  };

  var _scanHistory = [];
  window.ScanActions = {
    _lastBarcode: '',
    processBarcode: function(barcode, action) {
      if (!barcode) return;
      window.ScanActions._lastBarcode = barcode;
      if (!action) { showToast('info','Scanned: '+barcode+' - select action button'); return; }
      apiPost('/api/scan/process',{barcode:barcode,action:action})
        .then(function(res){
          var ok = res.success !== false;
          showToast(ok?'success':'error', res.message||(ok?'Done':'Failed'));
          window.ScanActions._addHist(barcode, action, ok);
        })
        .catch(function(e){
          if (e.status===501) showToast('info','Scan (coming soon)');
          else showToast('error','Scan error: '+(e.message||String(e)));
          window.ScanActions._addHist(barcode, action, false);
        });
    },
    quickAction: function(action) {
      var inp = document.getElementById('scan-input');
      var bc = (inp?inp.value.trim():'')||window.ScanActions._lastBarcode;
      if (!bc) { showToast('warning','Scan barcode first'); return; }
      window.ScanActions.processBarcode(bc, action);
      if (inp) inp.value='';
    },
    _addHist: function(barcode, action, ok) {
      var now = new Date();
      var t = [now.getHours(),now.getMinutes(),now.getSeconds()].map(function(n){return String(n).padStart(2,'0');}).join(':');
      _scanHistory.unshift({time:t,barcode:barcode,action:action,ok:ok});
      if (_scanHistory.length>100) _scanHistory.pop();
      var tbody = document.getElementById('scan-history-tbody');
      if (tbody) tbody.innerHTML = _scanHistory.slice(0,20).map(function(h){
        return '<tr><td class="mono-cell">'+h.time+'</td><td class="mono-cell">'+escapeHtml(h.barcode)+'</td><td>'+escapeHtml(h.action)+'</td><td>'+(h.ok?'<span style="color:var(--status-available)">OK</span>':'<span style="color:var(--status-return)">FAIL</span>')+'</td></tr>';
      }).join('');
    }
  };

  var _pdfFile=null, _pdfB64=null;
  window.PdfInbound = {
    handleDrop: function(e) {
      e.preventDefault();
      var dz = document.getElementById('pdf-drop-zone');
      if (dz) dz.style.borderColor='var(--border)';
      var f = e.dataTransfer.files[0];
      if (f) window.PdfInbound.handleFile(f);
    },
    handleFile: function(f) {
      if (!f||!f.name.toLowerCase().endsWith('.pdf')) { showToast('error','PDF files only'); return; }
      _pdfFile = f;
      var status=document.getElementById('pdf-status');
      var btn=document.getElementById('pdf-upload-btn');
      if (status) status.textContent='Selected: '+f.name+' ('+(f.size/1024).toFixed(1)+' KB)';
      var reader=new FileReader();
      reader.onload=function(ev){ _pdfB64=ev.target.result.split(',')[1]; if(btn) btn.style.display=''; };
      reader.readAsDataURL(f);
    },
    upload: function() {
      if (!_pdfB64) { showToast('warning','Select a PDF first'); return; }
      var status=document.getElementById('pdf-status');
      var btn=document.getElementById('pdf-upload-btn');
      if (status) status.textContent='Uploading...';
      if (btn) btn.disabled=true;
      apiPost('/api/inbound/pdf',{pdf_base64:_pdfB64,filename:(_pdfFile?_pdfFile.name:'upload.pdf')})
        .then(function(res){
          showToast('success','PDF inbound done: '+(res.message||'OK'));
          if (status) status.textContent='Done: '+(res.message||'Success');
          if (btn) { btn.style.display='none'; btn.disabled=false; }
          _pdfB64=null; _pdfFile=null;
        })
        .catch(function(e){
          if (e.status===501) showToast('info','PDF inbound (coming soon)');
          else showToast('error','Upload failed: '+(e.message||String(e)));
          if (status) status.textContent='Failed: '+(e.message||String(e));
          if (btn) btn.disabled=false;
        });
    }
  };

  /* ===================================================
     7i. PAGE: Tonbag
     =================================================== */
  function loadTonbagPage() {
    var route = _currentRoute;
    var c = document.getElementById('page-container');
    if (!c) return;
    c.innerHTML = [
      '<section class="page" data-page="tonbag">',
      '<h2>Tonbag List</h2>',
      '<div class="toolbar-mini"><button class="btn btn-secondary" onclick="renderPage(\'tonbag\')">Refresh</button></div>',
      '<div id="tonbag-loading" style="padding:40px;text-align:center">Loading...</div>',
      '<table class="data-table" id="tonbag-table" style="display:none">',
      '<thead><tr><th>Tonbag ID</th><th>LOT</th><th>Product</th><th>Status</th><th>Weight(MT)</th><th>Location</th><th>Container</th><th></th></tr></thead>',
      '<tbody id="tonbag-tbody"></tbody></table>',
      '<div class="empty" id="tonbag-empty" style="display:none">No tonbag data</div>',
      '</section>'
    ].join('');
    apiGet('/api/tonbags').then(function(res){
      if (_currentRoute !== route) return;
      var rows = extractRows(res);
      document.getElementById('tonbag-loading').style.display='none';
      if (!rows.length) { document.getElementById('tonbag-empty').style.display='block'; return; }
      var tbody=document.getElementById('tonbag-tbody');
      if (tbody) tbody.innerHTML=rows.map(function(r){
        return '<tr>' +
          '<td class="mono-cell">'+escapeHtml(r.sub_lt||r.tonbag_id||'-')+'</td>' +
          '<td class="mono-cell" style="color:var(--accent)">'+escapeHtml(r.lot_no||'-')+'</td>' +
          '<td><span class="tag">'+escapeHtml(r.product||'-')+'</span></td>' +
          '<td>'+escapeHtml(r.status||'-')+'</td>' +
          '<td class="mono-cell">'+(r.weight!=null?Number(r.weight).toLocaleString():'-')+'</td>' +
          '<td class="mono-cell">'+escapeHtml(r.location||'-')+'</td>' +
          '<td class="mono-cell">'+escapeHtml(r.container||'-')+'</td>' +
          '<td><button class="btn btn-ghost btn-xs">Detail</button></td></tr>';
      }).join('');
      document.getElementById('tonbag-table').style.display='';
    }).catch(function(){
      if (_currentRoute !== route) return;
      document.getElementById('tonbag-loading').style.display='none';
      document.getElementById('tonbag-empty').style.display='block';
    });
  }

  /* ===================================================
     8. MODAL
     =================================================== */
  function ensureModal() {
    var m=document.getElementById('sqm-modal');
    if (m) return m;
    m=document.createElement('div');
    m.id='sqm-modal';
    m.style.cssText='display:none;position:fixed;inset:0;background:rgba(0,0,0,.6);z-index:9999;overflow:auto;padding:40px';
    m.innerHTML='<div id="sqm-modal-inner" style="background:var(--bg-card);border-radius:8px;max-width:900px;margin:0 auto;padding:24px;position:relative"><button onclick="document.getElementById(\'sqm-modal\').style.display=\'none\'" style="position:absolute;top:12px;right:16px;background:none;border:none;font-size:1.4rem;cursor:pointer;color:var(--text-muted)">&#x2715;</button><div id="sqm-modal-content"></div></div>';
    document.body.appendChild(m);
    m.addEventListener('click',function(e){ if(e.target===m) m.style.display='none'; });
    return m;
  }

  function showDataModal(title, html) {
    ensureModal().style.display='block';
    document.getElementById('sqm-modal-content').innerHTML='<h2 style="margin-bottom:16px">'+escapeHtml(title)+'</h2>'+html;
  }

  /* ===================================================
     8b. Excel 업로드 모달 — Phase 4-B 공통 유틸
     (수동 입고 / 반품 입고 공용 — endpoint + title 만 다름)
     =================================================== */
  function _showExcelUploadModal(opts) {
    // opts: { title, subtitle, endpoint, onSuccess(data), columnsHint }
    var html = [
      '<div style="max-width:640px">',
      '  <h2 style="margin:0 0 12px 0">' + escapeHtml(opts.title) + '</h2>',
      '  <p style="color:var(--text-muted);margin:0 0 16px 0;font-size:.9rem">',
      '    ' + opts.subtitle,
      '  </p>',
      '  <div id="xls-drop-zone" style="border:2px dashed var(--border);border-radius:8px;padding:32px 16px;text-align:center;background:var(--bg-hover);cursor:pointer;margin-bottom:16px">',
      '    <div style="font-size:2.5rem;margin-bottom:8px">📁</div>',
      '    <div id="xls-file-name" style="color:var(--text-muted)">클릭 또는 파일을 여기에 드롭하세요</div>',
      '  </div>',
      '  <input type="file" id="xls-file-input" accept=".xlsx,.xls" style="display:none">',
      '  <div id="xls-progress" style="display:none;margin-bottom:16px">',
      '    <div style="background:var(--bg-hover);border-radius:4px;height:8px;overflow:hidden">',
      '      <div id="xls-progress-bar" style="background:var(--accent);height:100%;width:0%;transition:width .3s"></div>',
      '    </div>',
      '    <div id="xls-progress-text" style="font-size:.85rem;color:var(--text-muted);margin-top:4px">준비 중...</div>',
      '  </div>',
      '  <div id="xls-result" style="margin-bottom:16px"></div>',
      '  <div style="display:flex;gap:8px;justify-content:flex-end">',
      '    <button id="xls-cancel-btn" class="btn btn-ghost">닫기</button>',
      '    <button id="xls-upload-btn" class="btn btn-primary" disabled>업로드</button>',
      '  </div>',
      '</div>'
    ].join('\n');

    showDataModal('', html);

    var fileInput = document.getElementById('xls-file-input');
    var dropZone  = document.getElementById('xls-drop-zone');
    var fileName  = document.getElementById('xls-file-name');
    var uploadBtn = document.getElementById('xls-upload-btn');
    var cancelBtn = document.getElementById('xls-cancel-btn');
    var progress  = document.getElementById('xls-progress');
    var progressBar = document.getElementById('xls-progress-bar');
    var progressText = document.getElementById('xls-progress-text');
    var resultBox = document.getElementById('xls-result');
    var selectedFile = null;

    function setFile(f) {
      if (!f) return;
      if (!/\.(xlsx|xls)$/i.test(f.name)) {
        showToast('error', 'Excel 파일(.xlsx/.xls)만 가능합니다: ' + f.name);
        return;
      }
      selectedFile = f;
      fileName.innerHTML = '✅ <strong>' + escapeHtml(f.name) + '</strong> (' + Math.round(f.size/1024) + ' KB)';
      uploadBtn.disabled = false;
    }

    dropZone.addEventListener('click', function(){ fileInput.click(); });
    fileInput.addEventListener('change', function(e){
      if (e.target.files && e.target.files[0]) setFile(e.target.files[0]);
    });
    dropZone.addEventListener('dragover', function(e){ e.preventDefault(); dropZone.style.background='var(--bg-active)'; });
    dropZone.addEventListener('dragleave', function(){ dropZone.style.background='var(--bg-hover)'; });
    dropZone.addEventListener('drop', function(e){
      e.preventDefault();
      dropZone.style.background='var(--bg-hover)';
      if (e.dataTransfer.files && e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]);
    });
    cancelBtn.addEventListener('click', function(){
      document.getElementById('sqm-modal').style.display = 'none';
    });

    uploadBtn.addEventListener('click', function(){
      if (!selectedFile) return;
      uploadBtn.disabled = true;
      cancelBtn.disabled = true;
      progress.style.display = 'block';
      progressBar.style.width = '10%';
      progressText.textContent = '업로드 중...';
      resultBox.innerHTML = '';

      var form = new FormData();
      form.append('file', selectedFile, selectedFile.name);

      var xhr = new XMLHttpRequest();
      xhr.open('POST', API + opts.endpoint);
      xhr.upload.onprogress = function(e){
        if (e.lengthComputable) {
          var pct = Math.round((e.loaded / e.total) * 70) + 10;
          progressBar.style.width = pct + '%';
          progressText.textContent = '업로드 중... ' + pct + '%';
        }
      };
      xhr.onload = function(){
        progressBar.style.width = '100%';
        cancelBtn.disabled = false;
        var body;
        try { body = JSON.parse(xhr.responseText); } catch(e){ body = null; }
        if (xhr.status >= 200 && xhr.status < 300 && body && body.ok) {
          progressText.textContent = body.message || '완료';
          var extraHtml = opts.onSuccess ? opts.onSuccess(body.data || {}) : '';
          resultBox.innerHTML =
            '<div style="padding:12px;background:var(--bg-hover);border-radius:6px;border-left:4px solid var(--success)">' +
            '<div style="font-weight:600;margin-bottom:4px">✅ ' + escapeHtml(body.message||'완료') + '</div>' +
            (extraHtml || '') +
            '</div>';
          showToast('success', body.message || '완료');
          dbgLog('🟢','XLS-UPLOAD OK', opts.endpoint + ' — ' + (body.message||''), '#66bb6a');
          if (_currentRoute === 'inventory' && typeof loadInventoryPage === 'function') loadInventoryPage();
          if (typeof loadKpi === 'function') loadKpi();
        } else {
          var errMsg = (body && (body.detail || body.error || body.message)) || ('HTTP ' + xhr.status);
          if (typeof errMsg === 'object') errMsg = JSON.stringify(errMsg);
          progressText.textContent = '실패';
          progressBar.style.background = 'var(--danger)';
          var errExtra = '';
          if (body && body.data && body.data.errors) {
            errExtra = '<details style="margin-top:8px"><summary style="cursor:pointer;color:var(--warning)">⚠️ 실패 상세</summary><pre style="white-space:pre-wrap;font-size:.85rem;margin-top:8px">' +
              escapeHtml(JSON.stringify(body.data.errors, null, 2)) + '</pre></details>';
          }
          resultBox.innerHTML =
            '<div style="padding:12px;background:var(--bg-hover);border-radius:6px;border-left:4px solid var(--danger)">' +
            '<div style="font-weight:600">❌ 업로드 실패</div>' +
            '<div style="color:var(--text-muted);font-size:.85rem;margin-top:4px">' + escapeHtml(String(errMsg)) + '</div>' +
            errExtra +
            '</div>';
          showToast('error', '실패: ' + errMsg);
          dbgLog('🔴','XLS-UPLOAD FAIL', opts.endpoint + ' — ' + String(errMsg), '#ef5350');
          uploadBtn.disabled = false;
        }
      };
      xhr.onerror = function(){
        progressText.textContent = '네트워크 에러';
        progressBar.style.background = 'var(--danger)';
        resultBox.innerHTML = '<div style="padding:12px;color:var(--danger)">네트워크 에러 — API 서버를 확인하세요</div>';
        showToast('error', '네트워크 에러');
        uploadBtn.disabled = false;
        cancelBtn.disabled = false;
      };
      xhr.send(form);
    });
  }

  /* 수동 입고 (F002) */
  function showInboundManualUploadModal() {
    _showExcelUploadModal({
      title: '📊 수동 입고 — Excel 업로드',
      subtitle: '엑셀 파일(.xlsx/.xls)을 선택하세요. 컬럼: <code>lot_no, sap_no, bl_no, container_no, product, net_weight, stock_date</code> 등',
      endpoint: '/api/inbound/bulk-import-excel',
      onSuccess: function(d) {
        var errHtml = '';
        if (d.errors && d.errors.length) {
          errHtml = '<details style="margin-top:8px"><summary style="cursor:pointer;color:var(--warning)">⚠️ ' + d.errors.length + '건 실패 상세</summary><table class="data-table" style="margin-top:8px;font-size:.85rem"><thead><tr><th>행</th><th>LOT</th><th>사유</th></tr></thead><tbody>' +
            d.errors.map(function(er){
              return '<tr><td>'+er.row+'</td><td>'+escapeHtml(er.lot_no||'-')+'</td><td>'+escapeHtml(er.reason||'')+'</td></tr>';
            }).join('') + '</tbody></table></details>';
        }
        return '<div style="color:var(--text-muted);font-size:.85rem">파일: ' + escapeHtml(d.filename||'-') +
               ' · 성공 ' + (d.success_count||0) + ' / 실패 ' + (d.fail_count||0) + ' / 총 ' + (d.total||0) +
               ' · 매핑: ' + ((d.matched_columns||[]).join(', ')) + '</div>' + errHtml;
      }
    });
  }
  window.showInboundManualUploadModal = showInboundManualUploadModal;

  /* 반품 입고 (F007) */
  function showReturnInboundUploadModal() {
    _showExcelUploadModal({
      title: '🔄 반품 입고 — Excel 업로드',
      subtitle: '반품 Excel 파일을 선택하세요. 기존 PICKING 데이터와 자동 매칭되어 재고로 복구됩니다.',
      endpoint: '/api/inbound/return-excel',
      onSuccess: function(d) {
        var detailHtml = '';
        if (d.details && d.details.length) {
          detailHtml = '<details style="margin-top:8px"><summary style="cursor:pointer;color:var(--text-muted)">📋 처리 상세 (' + d.details.length + '건)</summary><pre style="white-space:pre-wrap;font-size:.8rem;margin-top:8px;max-height:240px;overflow:auto">' +
            escapeHtml(JSON.stringify(d.details.slice(0,50), null, 2)) + '</pre></details>';
        }
        return '<div style="color:var(--text-muted);font-size:.85rem">파일: ' + escapeHtml(d.filename||'-') +
               ' · <strong style="color:var(--accent)">' + (d.returned||0) + '건</strong> 반품 복구</div>' + detailHtml;
      }
    });
  }
  window.showReturnInboundUploadModal = showReturnInboundUploadModal;

  /* Allocation 입력 (F014) — 출고 예약 Excel 업로드 */
  function showAllocationUploadModal() {
    _showExcelUploadModal({
      title: '📍 Allocation 입력 — Excel 업로드',
      subtitle: 'Allocation Excel 파일을 선택하세요. 컬럼: <code>lot_no, sold_to, sale_ref, qty_mt, outbound_date, sublot_count</code>',
      endpoint: '/api/allocation/bulk-import-excel',
      onSuccess: function(d) {
        var warnHtml = '';
        if (d.errors && d.errors.length) {
          warnHtml = '<details style="margin-top:8px"><summary style="cursor:pointer;color:var(--warning)">⚠️ 경고 ' + d.errors.length + '건</summary><pre style="white-space:pre-wrap;font-size:.8rem;margin-top:8px;max-height:200px;overflow:auto">' +
            escapeHtml(d.errors.join('\n')) + '</pre></details>';
        }
        var detailHtml = '';
        if (d.error_details && d.error_details.length) {
          detailHtml = '<details style="margin-top:4px"><summary style="cursor:pointer;color:var(--text-muted)">상세 (' + d.error_details.length + '건)</summary><pre style="white-space:pre-wrap;font-size:.8rem;margin-top:8px;max-height:200px;overflow:auto">' +
            escapeHtml(JSON.stringify(d.error_details, null, 2)) + '</pre></details>';
        }
        return '<div style="color:var(--text-muted);font-size:.85rem">파일: ' + escapeHtml(d.filename||'-') +
               ' · <strong style="color:var(--accent)">' + (d.reserved||0) + '건</strong> 예약 / 총 ' + (d.total_rows||0) + '행 · 매핑: ' + ((d.matched_columns||[]).join(', ')) +
               '</div>' + warnHtml + detailHtml;
      }
    });
  }
  window.showAllocationUploadModal = showAllocationUploadModal;

  /* ===================================================
     8c. 즉시 출고 (F015) — 폼 기반 네이티브 구현
     엔진 quick_outbound(lot_no, count, customer, reason, operator) 직접 호출
     =================================================== */
  /* =====================================================================
     [Sprint 1-3] OneStop Outbound Dialog — 4탭 state machine
     ─────────────────────────────────────────────────────────────────────
     v864-2 source: gui_app_modular/dialogs/onestop_outbound.py (2304 lines)
     State machine: DRAFT → WAIT_SCAN → (FINALIZED | REVIEW | ERROR)

     Phase A (this commit): 4탭 UI 뼈대 + Tab 1 입력 + 상태바 + 파싱 DRAFT 전환
     Phase B: Tab 2 톤백 선택 (nested per-LOT Treeview)
     Phase C: Tab 3 스캔 검증 (OUT 스캔 upload + 검증 엔진)
     Phase D: Tab 4 완료 + 감사 로그 sub-popup
     Phase E: proof docs 저장소 + 90일 자동 정리
     ===================================================================== */
  var _ooState = {
    state: 'DRAFT',         /* DRAFT | WAIT_SCAN | FINALIZED | REVIEW | ERROR */
    currentTab: 1,          /* 1 ~ 4 */
    proofDocs: [],          /* 근거문서 multi-file */
    customer: '',
    saleRef: '',
    lotNo: '',
    pasteText: '',
    manualActuals: {},      /* {lot_no: {expected_kg, actual_kg}} */
    parsedItems: [],        /* 파싱된 출고 아이템 */
    /* [Sprint 1-3-B] Tab 2 톤백 선택 */
    lotsWithTonbags: {},    /* { lot_no: [{sub_lt, weight, status, location, ...}, ...] } */
    selectedTonbags: null,  /* Set<"lot.sub_lt"> */
    expandedLots: null,     /* Set<lot_no> */
    /* [Sprint 1-3-C] Tab 3 OUT 스캔 검증 */
    scanFile: null,         /* 업로드한 파일 객체 */
    scanRows: [],           /* [{tonbag_uid, actual_kg}, ...] - 백엔드 파싱 결과 */
    manualScans: [],        /* 수동 입력 [{tonbag_uid, actual_kg}, ...] */
    validationResults: [],  /* [{tonbag_uid, lot_no, expected_kg, actual_kg, diff_pct, level: ok|warn|stop, message}] */
    completedItems: [],
  };

  function _ooReset() {
    _ooState.state = 'DRAFT';
    _ooState.currentTab = 1;
    _ooState.proofDocs = [];
    _ooState.customer = '';
    _ooState.saleRef = '';
    _ooState.lotNo = '';
    _ooState.pasteText = '';
    _ooState.manualActuals = {};
    _ooState.parsedItems = [];
    _ooState.lotsWithTonbags = {};
    _ooState.selectedTonbags = new Set();
    _ooState.expandedLots = new Set();
    _ooState.scanFile = null;
    _ooState.scanRows = [];
    _ooState.manualScans = [];
    _ooState.validationResults = [];
    _ooState.completedItems = [];
  }

  function showOneStopOutboundModal() {
    _ooReset();

    var html = [
      '<div class="oo-modal">',
      '  <h2>🚀 S1 원스톱 출고 <span style="font-size:12px;font-weight:400;color:var(--text-muted)">— v864.3 (Sprint 1-3)</span></h2>',
      /* 상태바 */
      '  <div class="oo-statusbar">',
      '    <span style="font-weight:700;color:var(--text-muted);font-size:12px">상태:</span>',
      '    <span id="oo-status-badge" class="oo-status-badge draft">● DRAFT</span>',
      '    <div class="oo-status-progress">',
      '      <span id="oo-dot-draft"  class="oo-status-dot active"></span><span>DRAFT</span>',
      '      <span>→</span>',
      '      <span id="oo-dot-scan"   class="oo-status-dot"></span><span>WAIT_SCAN</span>',
      '      <span>→</span>',
      '      <span id="oo-dot-final"  class="oo-status-dot"></span><span>FINALIZED</span>',
      '    </div>',
      '    <span id="oo-status-hint" style="font-size:11px;color:var(--text-muted)">Tab 1 에서 입력 후 ▶ 파싱</span>',
      '  </div>',
      /* 탭 헤더 */
      '  <div class="oo-tab-headers">',
      '    <button class="oo-tab-header active" data-tab="1" onclick="window.ooSwitchTab(1)">',
      '      <span class="oo-tab-header-num">①</span><span>입력 (붙여넣기)</span>',
      '    </button>',
      '    <button class="oo-tab-header" data-tab="2" onclick="window.ooSwitchTab(2)" disabled title="DRAFT 상태에서 활성화">',
      '      <span class="oo-tab-header-num">②</span><span>톤백 선택</span>',
      '    </button>',
      '    <button class="oo-tab-header" data-tab="3" onclick="window.ooSwitchTab(3)" disabled title="WAIT_SCAN 상태에서 활성화">',
      '      <span class="oo-tab-header-num">③</span><span>스캔 검증</span>',
      '    </button>',
      '    <button class="oo-tab-header" data-tab="4" onclick="window.ooSwitchTab(4)" disabled title="완료 시 활성화">',
      '      <span class="oo-tab-header-num">④</span><span>완료</span>',
      '    </button>',
      '  </div>',
      /* 탭 본문 */
      '  <div class="oo-tab-body">',
      /* --- Tab 1: 입력 --- */
      '    <div class="oo-tab-pane active" data-pane="1">',
      /* 근거문서 섹션 */
      '      <div class="oo-section">',
      '        <div class="oo-section-title">📎 근거문서 (Proof Documents)</div>',
      '        <input type="file" id="oo-proof-input" multiple style="display:none" onchange="window.ooAddProofFiles(this.files)">',
      '        <button class="btn" onclick="document.getElementById(\'oo-proof-input\').click()">+ 파일 첨부</button>',
      '        <div id="oo-proof-files" class="oo-files-list"></div>',
      '        <div style="font-size:11px;color:var(--text-muted);margin-top:6px">💡 출고 근거 서류(PDF/이미지/Excel). 완료 후 data/proof_docs/YYYY-MM-DD/ 에 저장 예정 (Phase E)</div>',
      '      </div>',
      /* 고객사/Sale Ref/LOT */
      '      <div class="oo-section">',
      '        <div class="oo-section-title">🏢 고객사 · Sale Ref · LOT</div>',
      '        <div class="oo-input-grid">',
      '          <label>고객사:</label><input type="text" id="oo-customer" placeholder="예: ACME Corp" onchange="_ooState.customer=this.value">',
      '          <label>Sale Ref:</label><input type="text" id="oo-sale-ref" placeholder="예: SO-2026-0420" onchange="_ooState.saleRef=this.value">',
      '          <label>LOT NO:</label><input type="text" id="oo-lot" placeholder="예: 1126013063" style="font-family:Consolas,monospace" onchange="_ooState.lotNo=this.value">',
      '          <label>출고일:</label><input type="date" id="oo-date">',
      '        </div>',
      '        <div style="font-size:11px;color:var(--text-muted);margin-top:4px">빠른 선택 단축키 (Sprint 2): 🔄 고객사 목록 새로고침</div>',
      '      </div>',
      /* 수동 실제수량 */
      '      <div class="oo-section">',
      '        <div class="oo-section-title">✏️ 수동 실제수량 입력 (선택)</div>',
      '        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;font-size:12px">',
      '          <label>LOT:</label><input type="text" id="oo-manual-lot" placeholder="LOT NO" style="padding:4px 8px;background:var(--bg-hover);border:1px solid var(--panel-border);border-radius:3px;font-family:Consolas,monospace">',
      '          <label>실제(kg):</label><input type="number" id="oo-manual-actual" step="0.01" placeholder="예: 5001.25" style="padding:4px 8px;background:var(--bg-hover);border:1px solid var(--panel-border);border-radius:3px;width:100px">',
      '          <button class="btn" onclick="window.ooAddManualActual()">적용</button>',
      '          <span id="oo-manual-list" style="color:var(--text-muted);font-size:11px"></span>',
      '        </div>',
      '        <div style="font-size:11px;color:var(--text-muted);margin-top:4px">💡 계측 오차 있는 LOT 은 수동 값으로 덮어씀. actual &gt; expected 는 ⛔ 하드스톱</div>',
      '      </div>',
      /* Paste 영역 */
      '      <div class="oo-section">',
      '        <div class="oo-section-title">📋 붙여넣기 입력</div>',
      '        <textarea id="oo-paste" class="oo-paste-textarea" placeholder="Excel/CSV 에서 복사한 LOT 정보를 여기에 붙여넣으세요\n예:&#10;LOT_NO\tSAP_NO\tQTY(kg)\tCUSTOMER\tSALE_REF\n1126013063\t2200034449\t5000\tACME\tSO-2026-0420"></textarea>',
      '        <div style="display:flex;gap:8px;margin-top:8px">',
      '          <button class="btn" onclick="window.ooInsertSample()">📝 샘플 삽입</button>',
      '          <button class="btn btn-primary" id="oo-parse-btn" onclick="window.ooParseDraft()">🔄 파싱 → DRAFT ▶</button>',
      '          <button class="btn" onclick="window.ooClearPaste()">🧹 지우기</button>',
      '          <span id="oo-parse-hint" style="margin-left:auto;color:var(--text-muted);font-size:11px;align-self:center">고객사 + LOT 또는 붙여넣기 내용 필요</span>',
      '        </div>',
      '      </div>',
      /* 파싱 결과 */
      '      <div id="oo-draft-result" style="margin-top:10px"></div>',
      '    </div>',
      /* --- Tab 2: 톤백 선택 (Sprint 1-3-B 실구현) --- */
      '    <div class="oo-tab-pane" data-pane="2">',
      /* 통계 */
      '      <div class="oo-section">',
      '        <div class="oo-section-title">📊 선택 요약</div>',
      '        <div id="oo-t2-stats" style="font-size:13px;color:var(--text-muted)">DRAFT 진입 전 — Tab 1 에서 ▶ 파싱을 먼저 실행하세요</div>',
      '      </div>',
      /* 액션 버튼 */
      '      <div class="oo-section">',
      '        <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center">',
      '          <button class="btn" onclick="window.ooRandomSelect()" title="가용 톤백 중 무작위 선택">🎲 랜덤 선택</button>',
      '          <button class="btn" onclick="window.ooSelectAllLots()">✅ 전체 LOT 전체</button>',
      '          <button class="btn" onclick="window.ooDeselectAll()">☐ 전체 해제</button>',
      '          <button class="btn" onclick="window.ooExpandAll(true)">▼ 모두 펼침</button>',
      '          <button class="btn" onclick="window.ooExpandAll(false)">▶ 모두 접기</button>',
      '          <button class="btn btn-primary" id="oo-goto-scan-btn" onclick="window.ooMoveToScan()" disabled style="margin-left:auto" title="DRAFT → WAIT_SCAN">DRAFT → WAIT_SCAN ▶</button>',
      '        </div>',
      '      </div>',
      /* 톤백 리스트 */
      '      <div class="oo-section">',
      '        <div class="oo-section-title">📦 LOT별 가용 톤백</div>',
      '        <div id="oo-tonbags-body" style="max-height:360px;overflow-y:auto">',
      '          <div style="padding:30px;text-align:center;color:var(--text-muted);font-size:12px">⏳ DRAFT 진입 시 자동 로드됩니다</div>',
      '        </div>',
      '      </div>',
      '    </div>',
      /* --- Tab 3: 스캔 검증 (Sprint 1-3-C 실구현) --- */
      '    <div class="oo-tab-pane" data-pane="3">',
      /* 통계 */
      '      <div class="oo-section">',
      '        <div class="oo-section-title">📊 검증 요약</div>',
      '        <div id="oo-t3-stats" style="font-size:13px;color:var(--text-muted)">Tab 2 에서 톤백을 선택해야 검증 가능</div>',
      '      </div>',
      /* 파일 업로드 + 수동 입력 */
      '      <div class="oo-section">',
      '        <div class="oo-section-title">📊 OUT 스캔 파일 업로드</div>',
      '        <input type="file" id="oo-scan-input" accept=".csv,.xlsx,.xls" style="display:none" onchange="window.ooHandleScanFile(this.files[0])">',
      '        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">',
      '          <button class="btn btn-primary" onclick="document.getElementById(\'oo-scan-input\').click()">📂 파일 선택 (csv/xlsx)</button>',
      '          <span id="oo-scan-filename" style="font-family:Consolas,monospace;font-size:11px;color:var(--text-muted)">선택된 파일 없음</span>',
      '          <button class="btn" onclick="window.ooClearScan()" style="margin-left:auto">🧹 초기화</button>',
      '        </div>',
      '        <div style="margin-top:6px;font-size:11px;color:var(--text-muted)">💡 컬럼 자동 인식: <code>tonbag_uid</code>(또는 sub_lt/id) + <code>actual_kg</code>(또는 weight/net_kg)</div>',
      '      </div>',
      /* 수동 입력 */
      '      <div class="oo-section">',
      '        <div class="oo-section-title">✏️ 수동 입력 (선택)</div>',
      '        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;font-size:12px">',
      '          <label>톤백 ID:</label><input type="text" id="oo-scan-uid" placeholder="T-1234" style="padding:4px 8px;background:var(--bg-hover);border:1px solid var(--panel-border);border-radius:3px;font-family:Consolas,monospace">',
      '          <label>실제(kg):</label><input type="number" id="oo-scan-actual" step="0.01" placeholder="1001.25" style="padding:4px 8px;background:var(--bg-hover);border:1px solid var(--panel-border);border-radius:3px;width:110px">',
      '          <button class="btn" onclick="window.ooAddManualScan()">➕ 추가</button>',
      '        </div>',
      '      </div>',
      /* 검증 실행 */
      '      <div class="oo-section">',
      '        <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">',
      '          <button class="btn btn-primary" onclick="window.ooRunValidation()">⚡ 전체 검증 실행</button>',
      '          <span id="oo-validation-hint" style="color:var(--text-muted);font-size:11px">스캔 데이터를 먼저 업로드/입력</span>',
      '          <button class="btn btn-primary" id="oo-goto-finalize-btn" onclick="window.ooMoveToFinalize()" disabled style="margin-left:auto" title="WAIT_SCAN → FINALIZED">WAIT_SCAN → FINALIZED ▶</button>',
      '        </div>',
      '      </div>',
      /* 검증 결과 */
      '      <div class="oo-section">',
      '        <div class="oo-section-title">📋 검증 결과</div>',
      '        <div id="oo-validation-results" style="max-height:280px;overflow-y:auto">',
      '          <div style="padding:20px;text-align:center;color:var(--text-muted);font-size:12px">⚡ "전체 검증 실행" 버튼을 눌러 결과를 확인하세요</div>',
      '        </div>',
      '      </div>',
      '    </div>',
      /* --- Tab 4: 완료 (Sprint 1-3-D 실구현) --- */
      '    <div class="oo-tab-pane" data-pane="4">',
      /* 완료 요약 */
      '      <div class="oo-section">',
      '        <div class="oo-section-title">📊 완료 요약</div>',
      '        <div id="oo-t4-stats" style="font-size:13px;color:var(--text-muted)">FINALIZED 상태 대기 중 — Tab 3 검증 통과 후 진입</div>',
      '      </div>',
      /* 액션 */
      '      <div class="oo-section">',
      '        <div style="display:flex;gap:6px;flex-wrap:wrap">',
      '          <button class="btn btn-primary" id="oo-confirm-btn" onclick="window.ooConfirmOutbound()" disabled title="선택된 톤백 → 출고 처리 (PICKED → OUTBOUND)">📦 확정건 출고 완료 ▶</button>',
      '          <button class="btn" onclick="window.ooViewAuditLog()" title="감사 로그 sub-popup (CSV export)">📋 감사 로그 보기</button>',
      '          <button class="btn" onclick="window.ooStartNew()" style="margin-left:auto" title="모든 상태 초기화 후 새 출고 시작">📋 새 출고 시작</button>',
      '          <button class="btn btn-ghost" onclick="document.getElementById(\'sqm-modal\').style.display=\'none\'">❌ 닫기</button>',
      '        </div>',
      '      </div>',
      /* 완료 이력 */
      '      <div class="oo-section">',
      '        <div class="oo-section-title">📋 완료 이력</div>',
      '        <div id="oo-t4-history" style="max-height:240px;overflow-y:auto">',
      '          <div style="padding:20px;text-align:center;color:var(--text-muted);font-size:12px">아직 완료된 항목이 없습니다</div>',
      '        </div>',
      '      </div>',
      '    </div>',
      '  </div>',  /* /oo-tab-body */
      /* 하단 버튼 */
      '  <div style="display:flex;gap:8px;justify-content:flex-end">',
      '    <button class="btn btn-ghost" onclick="document.getElementById(\'sqm-modal\').style.display=\'none\'">❌ 닫기</button>',
      '    <button class="btn" onclick="window.ooViewAuditLog()">📋 감사 로그 보기</button>',
      '    <button class="btn btn-wip" id="oo-final-btn" onclick="window.ooFinalize()" disabled title="Sprint 1-3 Phase D 예정">📦 확정건 출고 완료 ▶</button>',
      '  </div>',
      '</div>'
    ].join('\n');

    showDataModal('', html);

    /* 기본 출고일 = 오늘 */
    var dateInput = document.getElementById('oo-date');
    if (dateInput) {
      var d = new Date();
      dateInput.value = d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
    }
  }
  window.showOneStopOutboundModal = showOneStopOutboundModal;

  /* ─── Tab 전환 ─────────────────────────────────────────────────────── */
  window.ooSwitchTab = function(tab) {
    _ooState.currentTab = tab;
    document.querySelectorAll('.oo-tab-header').forEach(function(h){
      h.classList.toggle('active', parseInt(h.dataset.tab, 10) === tab);
    });
    document.querySelectorAll('.oo-tab-pane').forEach(function(p){
      p.classList.toggle('active', parseInt(p.dataset.pane, 10) === tab);
    });
  };

  /* ─── 상태 업데이트 ─────────────────────────────────────────────────── */
  function _ooSetState(newState) {
    _ooState.state = newState;
    var badge = document.getElementById('oo-status-badge');
    if (!badge) return;
    badge.className = 'oo-status-badge ' + newState.toLowerCase();
    var map = { DRAFT: '● DRAFT', WAIT_SCAN: '● WAIT_SCAN', FINALIZED: '● FINALIZED', REVIEW: '● REVIEW', ERROR: '● ERROR' };
    badge.textContent = map[newState] || ('● ' + newState);

    /* progress dots */
    var draft = document.getElementById('oo-dot-draft');
    var scan  = document.getElementById('oo-dot-scan');
    var final = document.getElementById('oo-dot-final');
    [draft, scan, final].forEach(function(d){ if (d) d.className = 'oo-status-dot'; });
    if (newState === 'DRAFT')         { if(draft) draft.className = 'oo-status-dot active'; }
    else if (newState === 'WAIT_SCAN'){ if(draft) draft.className = 'oo-status-dot done'; if(scan) scan.className = 'oo-status-dot active'; }
    else if (newState === 'FINALIZED'){ if(draft) draft.className = 'oo-status-dot done'; if(scan) scan.className = 'oo-status-dot done'; if(final) final.className = 'oo-status-dot active'; }

    /* 탭 활성화 */
    var tab2 = document.querySelector('.oo-tab-header[data-tab="2"]');
    var tab3 = document.querySelector('.oo-tab-header[data-tab="3"]');
    var tab4 = document.querySelector('.oo-tab-header[data-tab="4"]');
    if (tab2) tab2.disabled = !(newState === 'DRAFT' || newState === 'WAIT_SCAN' || newState === 'FINALIZED');
    if (tab3) tab3.disabled = !(newState === 'WAIT_SCAN' || newState === 'FINALIZED');
    if (tab4) tab4.disabled = !(newState === 'FINALIZED' || newState === 'REVIEW');

    var hint = document.getElementById('oo-status-hint');
    if (hint) {
      var hintMap = {
        DRAFT:     '📋 Tab 2 에서 톤백 선택 → DRAFT → WAIT_SCAN',
        WAIT_SCAN: '📊 Tab 3 에서 OUT 스캔 검증',
        FINALIZED: '✅ 완료 — Tab 4 에서 출고 확정',
        REVIEW:    '🔍 검토 필요 (불일치 발견)',
        ERROR:     '🚫 에러 — actual > expected',
      };
      hint.textContent = hintMap[newState] || '';
    }
  }

  /* ─── 근거문서 파일 관리 ────────────────────────────────────────────── */
  window.ooAddProofFiles = function(fileList) {
    if (!fileList) return;
    Array.from(fileList).forEach(function(f){ _ooState.proofDocs.push(f); });
    _ooRenderProofFiles();
  };
  window.ooRemoveProofFile = function(idx) {
    _ooState.proofDocs.splice(idx, 1);
    _ooRenderProofFiles();
  };
  function _ooRenderProofFiles() {
    var el = document.getElementById('oo-proof-files');
    if (!el) return;
    if (!_ooState.proofDocs.length) { el.innerHTML = '<span style="color:var(--text-muted);font-size:11px">첨부된 파일 없음</span>'; return; }
    el.innerHTML = _ooState.proofDocs.map(function(f, i){
      return '<span class="oo-file-chip">📄 ' + escapeHtml(f.name) + ' <span class="remove" onclick="window.ooRemoveProofFile(' + i + ')">✕</span></span>';
    }).join('');
  }

  /* ─── 수동 실제수량 ─────────────────────────────────────────────────── */
  window.ooAddManualActual = function() {
    var lot = (document.getElementById('oo-manual-lot') || {}).value || '';
    var act = (document.getElementById('oo-manual-actual') || {}).value || '';
    lot = String(lot).trim();
    if (!lot || !act) { showToast('warn', 'LOT NO 와 실제(kg) 값 필요'); return; }
    _ooState.manualActuals[lot] = { actual_kg: parseFloat(act) };
    document.getElementById('oo-manual-lot').value = '';
    document.getElementById('oo-manual-actual').value = '';
    var list = document.getElementById('oo-manual-list');
    if (list) {
      var items = Object.keys(_ooState.manualActuals).map(function(k){
        return k + '=' + _ooState.manualActuals[k].actual_kg + 'kg';
      });
      list.textContent = items.length ? '(' + items.length + '건: ' + items.slice(0, 3).join(', ') + (items.length > 3 ? '…' : '') + ')' : '';
    }
    showToast('success', '수동값 ' + lot + ' = ' + act + 'kg 저장됨');
  };

  /* ─── Paste / Sample / Clear ───────────────────────────────────────── */
  window.ooInsertSample = function() {
    var ta = document.getElementById('oo-paste');
    if (!ta) return;
    ta.value = 'LOT_NO\tSAP_NO\tQTY(kg)\tCUSTOMER\tSALE_REF\n' +
               '1126013063\t2200034449\t5001.25\tACME Corp\tSO-2026-0420\n' +
               '1126013064\t2200034449\t5000.50\tACME Corp\tSO-2026-0420\n' +
               '1126013065\t2200034449\t4998.75\tACME Corp\tSO-2026-0420';
    showToast('info', '샘플 3행 삽입됨 — 파싱해 보세요');
  };
  window.ooClearPaste = function() {
    var ta = document.getElementById('oo-paste');
    if (ta) ta.value = '';
    var rb = document.getElementById('oo-draft-result');
    if (rb) rb.innerHTML = '';
  };

  /* ─── 파싱 → DRAFT 전환 ────────────────────────────────────────────── */
  window.ooParseDraft = function() {
    var customer = (document.getElementById('oo-customer') || {}).value || '';
    var saleRef  = (document.getElementById('oo-sale-ref') || {}).value || '';
    var lotNo    = (document.getElementById('oo-lot') || {}).value || '';
    var paste    = (document.getElementById('oo-paste') || {}).value || '';
    customer = customer.trim(); saleRef = saleRef.trim(); lotNo = lotNo.trim(); paste = paste.trim();

    if (!customer && !paste) { showToast('error', '고객사 또는 붙여넣기 내용 필요'); return; }

    _ooState.customer = customer;
    _ooState.saleRef = saleRef;
    _ooState.lotNo = lotNo;
    _ooState.pasteText = paste;

    /* paste 파싱 — TSV/CSV 구분 + 헤더 자동 인식 */
    var items = [];
    if (paste) {
      var lines = paste.split(/\r?\n/).filter(function(l){ return l.trim(); });
      if (lines.length >= 2) {
        /* 헤더 감지 */
        var headers = lines[0].split(/\t|,/).map(function(s){ return s.trim().toLowerCase(); });
        var iLot  = headers.findIndex(function(h){ return /lot[_ ]?no|lot/.test(h); });
        var iSap  = headers.findIndex(function(h){ return /sap/.test(h); });
        var iQty  = headers.findIndex(function(h){ return /qty|weight|net/.test(h); });
        var iCust = headers.findIndex(function(h){ return /customer|고객/.test(h); });
        var iRef  = headers.findIndex(function(h){ return /sale[_ ]?ref|sale/.test(h); });
        /* 데이터 행 */
        for (var i = 1; i < lines.length; i++) {
          var cols = lines[i].split(/\t|,/).map(function(s){ return s.trim(); });
          if (!cols.length) continue;
          items.push({
            lot_no:     iLot  >= 0 ? cols[iLot]  : cols[0] || '',
            sap_no:     iSap  >= 0 ? cols[iSap]  : '',
            qty_kg:     iQty  >= 0 ? parseFloat(cols[iQty] || 0) : 0,
            customer:   iCust >= 0 ? cols[iCust] : customer,
            sale_ref:   iRef  >= 0 ? cols[iRef]  : saleRef,
          });
        }
      } else {
        /* 단일 행 텍스트 → LOT NO 만 추출 */
        items.push({ lot_no: paste, sap_no: '', qty_kg: 0, customer: customer, sale_ref: saleRef });
      }
    } else if (lotNo) {
      items.push({ lot_no: lotNo, sap_no: '', qty_kg: 0, customer: customer, sale_ref: saleRef });
    }

    if (!items.length) { showToast('error', '파싱 결과가 비어있습니다'); return; }

    _ooState.parsedItems = items;
    _ooSetState('DRAFT');

    var rb = document.getElementById('oo-draft-result');
    if (rb) {
      rb.innerHTML =
        '<div style="padding:10px;background:rgba(102,187,106,.1);border-left:3px solid var(--success);border-radius:4px">' +
        '<div style="font-weight:700;color:var(--success)">✅ DRAFT 생성 완료 — ' + items.length + '건</div>' +
        '<div style="font-size:11px;color:var(--text-muted);margin-top:4px">' +
        '고객사: ' + escapeHtml(customer || '(paste 기반)') + ' · Sale Ref: ' + escapeHtml(saleRef || '-') +
        ' · 근거문서: ' + _ooState.proofDocs.length + '건' +
        ' · 수동값: ' + Object.keys(_ooState.manualActuals).length + '건</div>' +
        '<details style="margin-top:6px"><summary style="cursor:pointer;font-size:12px">파싱된 LOT 목록</summary>' +
        '<table class="data-table" style="margin-top:6px;font-size:11px"><thead><tr><th>#</th><th>LOT</th><th>SAP</th><th>QTY(kg)</th><th>고객</th><th>Ref</th></tr></thead><tbody>' +
        items.map(function(it, i){
          return '<tr><td>' + (i+1) + '</td><td class="mono-cell">' + escapeHtml(it.lot_no||'-') + '</td><td class="mono-cell">' + escapeHtml(it.sap_no||'-') + '</td><td class="mono-cell" style="text-align:right">' + (it.qty_kg || 0) + '</td><td>' + escapeHtml(it.customer||'-') + '</td><td class="mono-cell">' + escapeHtml(it.sale_ref||'-') + '</td></tr>';
        }).join('') + '</tbody></table></details>' +
        '<div style="margin-top:8px;font-size:11px;color:var(--info, #42a5f5)">💡 다음 단계: 상단 <strong>② 톤백 선택</strong> 탭으로 이동 중...</div>' +
        '</div>';
    }
    showToast('success', 'DRAFT 생성: ' + items.length + '건 — 톤백 로드 중...');
    /* [Sprint 1-3-B] Tab 2 로 자동 이동 + 톤백 로드 */
    _ooLoadTonbagsForLots();
    setTimeout(function(){ window.ooSwitchTab(2); }, 600);
  };

  /* =====================================================================
     [Sprint 1-3-B] Tab 2 — 톤백 선택 로직
     ===================================================================== */
  function _ooLoadTonbagsForLots() {
    var lots = _ooState.parsedItems.map(function(it){ return it.lot_no; }).filter(Boolean);
    if (!lots.length) return;
    _ooState.lotsWithTonbags = {};
    _ooState.selectedTonbags.clear();
    _ooState.expandedLots.clear();

    var body = document.getElementById('oo-tonbags-body');
    if (body) body.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text-muted);font-size:12px">⏳ ' + lots.length + ' LOT 톤백 조회 중...</div>';

    /* 각 LOT에 대해 GET /api/tonbags?lot_no=<lot>&status=AVAILABLE */
    var promises = lots.map(function(lot){
      return apiGet('/api/tonbags?lot_no=' + encodeURIComponent(lot) + '&status=AVAILABLE')
        .then(function(res){ return { lot: lot, rows: extractRows(res) }; })
        .catch(function(){ return { lot: lot, rows: [] }; });
    });

    Promise.all(promises).then(function(results){
      results.forEach(function(r){
        _ooState.lotsWithTonbags[r.lot] = r.rows.filter(function(t){
          /* LOT NO 정확 매치 (LIKE 는 여러 LOT 잡을 수 있음) */
          return (t.lot_no || '') === r.lot;
        });
        /* 기본 확장 */
        _ooState.expandedLots.add(r.lot);
      });
      _ooRenderTonbags();
      _ooUpdateT2Stats();
    });
  }

  function _ooRenderTonbags() {
    var body = document.getElementById('oo-tonbags-body');
    if (!body) return;
    var lots = _ooState.parsedItems.map(function(it){ return it.lot_no; }).filter(Boolean);
    if (!lots.length) { body.innerHTML = '<div style="padding:30px;text-align:center;color:var(--text-muted)">LOT 없음</div>'; return; }

    var html = lots.map(function(lot){
      var tonbags = _ooState.lotsWithTonbags[lot] || [];
      var selectedInLot = tonbags.filter(function(t){
        return _ooState.selectedTonbags.has(lot + '.' + (t.sub_lt || t.tonbag_id));
      });
      var expanded = _ooState.expandedLots.has(lot);
      var totalKg = tonbags.reduce(function(s, t){ return s + (Number(t.weight) || 0); }, 0);
      var selKg   = selectedInLot.reduce(function(s, t){ return s + (Number(t.weight) || 0); }, 0);

      var header =
        '<div class="oo-lot-header" style="display:flex;align-items:center;gap:8px;padding:8px 10px;background:var(--bg-hover);border:1px solid var(--panel-border);border-radius:4px;cursor:pointer;margin-top:4px;font-size:12px" onclick="window.ooToggleLotExpand(\'' + escapeHtml(lot) + '\')">' +
        '<span style="font-size:12px;color:var(--text-muted)">' + (expanded ? '▼' : '▶') + '</span>' +
        '<strong style="color:var(--accent);font-family:Consolas,monospace">' + escapeHtml(lot) + '</strong>' +
        '<span style="color:var(--text-muted)">· 가용 ' + tonbags.length + '개 · ' + totalKg.toFixed(2) + 'kg</span>' +
        (selectedInLot.length > 0 ? '<span style="color:var(--success);font-weight:700">· 선택 ' + selectedInLot.length + '개 (' + selKg.toFixed(2) + 'kg)</span>' : '') +
        '<span style="margin-left:auto;display:flex;gap:4px" onclick="event.stopPropagation()">' +
        '<button class="btn" style="padding:2px 8px;font-size:11px" onclick="window.ooSelectAllForLot(\'' + escapeHtml(lot) + '\')">✅ LOT 전체</button>' +
        '<button class="btn" style="padding:2px 8px;font-size:11px" onclick="window.ooDeselectForLot(\'' + escapeHtml(lot) + '\')">☐ 해제</button>' +
        '</span>' +
        '</div>';

      if (!expanded) return header;

      if (!tonbags.length) {
        return header + '<div style="padding:10px 20px;color:var(--text-muted);font-size:11px">📭 가용 톤백 없음</div>';
      }

      var rows = tonbags.map(function(t){
        var key = lot + '.' + (t.sub_lt || t.tonbag_id);
        var checked = _ooState.selectedTonbags.has(key) ? 'checked' : '';
        return '<tr style="font-size:11px">' +
          '<td style="width:28px;text-align:center"><input type="checkbox" ' + checked + ' onchange="window.ooToggleTonbag(\'' + escapeHtml(lot) + '\',\'' + escapeHtml(t.sub_lt || t.tonbag_id) + '\',this.checked)"></td>' +
          '<td class="mono-cell">' + escapeHtml(t.sub_lt || t.tonbag_id || '-') + '</td>' +
          '<td class="mono-cell" style="text-align:right">' + (Number(t.weight) || 0).toFixed(2) + '</td>' +
          '<td>' + escapeHtml(t.status || '-') + '</td>' +
          '<td>' + escapeHtml(t.location || '-') + '</td>' +
          '<td class="mono-cell">' + escapeHtml(t.container || '-') + '</td>' +
          '</tr>';
      }).join('');

      return header +
        '<table class="data-table" style="margin-top:2px;font-size:11px"><thead><tr><th></th><th>톤백 ID</th><th style="text-align:right">중량(kg)</th><th>상태</th><th>위치</th><th>컨테이너</th></tr></thead><tbody>' + rows + '</tbody></table>';
    }).join('');

    body.innerHTML = html;
  }

  function _ooUpdateT2Stats() {
    var el = document.getElementById('oo-t2-stats');
    var btn = document.getElementById('oo-goto-scan-btn');
    if (!el) return;
    var lots = _ooState.parsedItems.map(function(it){ return it.lot_no; }).filter(Boolean);
    var totalTonbags = 0, totalKg = 0, selectedCount = _ooState.selectedTonbags.size, selectedKg = 0;

    lots.forEach(function(lot){
      var arr = _ooState.lotsWithTonbags[lot] || [];
      arr.forEach(function(t){
        totalTonbags++;
        totalKg += Number(t.weight) || 0;
        var key = lot + '.' + (t.sub_lt || t.tonbag_id);
        if (_ooState.selectedTonbags.has(key)) selectedKg += Number(t.weight) || 0;
      });
    });

    el.innerHTML =
      '<div>📦 파싱 LOT <strong>' + lots.length + '개</strong> · 전체 가용 톤백 <strong>' + totalTonbags + '개</strong> (' + (totalKg / 1000).toFixed(3) + ' MT)</div>' +
      '<div style="margin-top:4px">✅ 선택됨: <strong style="color:' + (selectedCount > 0 ? 'var(--success)' : 'var(--text-muted)') + '">' + selectedCount + '개</strong> (' + (selectedKg / 1000).toFixed(3) + ' MT)</div>';

    if (btn) btn.disabled = selectedCount === 0;
  }

  /* 개별/일괄 토글 */
  window.ooToggleLotExpand = function(lot) {
    if (_ooState.expandedLots.has(lot)) _ooState.expandedLots.delete(lot);
    else _ooState.expandedLots.add(lot);
    _ooRenderTonbags();
  };
  window.ooToggleTonbag = function(lot, subLt, checked) {
    var key = lot + '.' + subLt;
    if (checked) _ooState.selectedTonbags.add(key);
    else _ooState.selectedTonbags.delete(key);
    _ooUpdateT2Stats();
    /* 헤더 요약 갱신을 위해 재렌더 (가벼운 구현 — 필요하면 부분 업데이트 최적화) */
    _ooRenderTonbags();
  };
  window.ooSelectAllForLot = function(lot) {
    var arr = _ooState.lotsWithTonbags[lot] || [];
    arr.forEach(function(t){ _ooState.selectedTonbags.add(lot + '.' + (t.sub_lt || t.tonbag_id)); });
    _ooRenderTonbags();
    _ooUpdateT2Stats();
  };
  window.ooDeselectForLot = function(lot) {
    var arr = _ooState.lotsWithTonbags[lot] || [];
    arr.forEach(function(t){ _ooState.selectedTonbags.delete(lot + '.' + (t.sub_lt || t.tonbag_id)); });
    _ooRenderTonbags();
    _ooUpdateT2Stats();
  };
  window.ooSelectAllLots = function() {
    Object.keys(_ooState.lotsWithTonbags).forEach(function(lot){
      (_ooState.lotsWithTonbags[lot] || []).forEach(function(t){
        _ooState.selectedTonbags.add(lot + '.' + (t.sub_lt || t.tonbag_id));
      });
    });
    _ooRenderTonbags();
    _ooUpdateT2Stats();
  };
  window.ooDeselectAll = function() {
    _ooState.selectedTonbags.clear();
    _ooRenderTonbags();
    _ooUpdateT2Stats();
  };
  window.ooExpandAll = function(expand) {
    _ooState.expandedLots.clear();
    if (expand) {
      Object.keys(_ooState.lotsWithTonbags).forEach(function(lot){ _ooState.expandedLots.add(lot); });
    }
    _ooRenderTonbags();
  };

  /* 🎲 랜덤 선택 — 각 LOT에서 parsedItems.qty_kg 에 가장 가까운 조합 선택
     단순 heuristic: qty_kg를 톤백 평균으로 나눈 개수만큼 선택 */
  window.ooRandomSelect = function() {
    _ooState.selectedTonbags.clear();
    _ooState.parsedItems.forEach(function(item){
      var arr = (_ooState.lotsWithTonbags[item.lot_no] || []).slice();
      if (!arr.length) return;
      var avgKg = arr.reduce(function(s, t){ return s + (Number(t.weight) || 0); }, 0) / arr.length;
      var needCount = item.qty_kg > 0 && avgKg > 0 ? Math.max(1, Math.round(item.qty_kg / avgKg)) : 1;
      needCount = Math.min(needCount, arr.length);
      /* Fisher-Yates shuffle */
      for (var i = arr.length - 1; i > 0; i--) {
        var j = Math.floor(Math.random() * (i + 1));
        var tmp = arr[i]; arr[i] = arr[j]; arr[j] = tmp;
      }
      for (var k = 0; k < needCount; k++) {
        _ooState.selectedTonbags.add(item.lot_no + '.' + (arr[k].sub_lt || arr[k].tonbag_id));
      }
    });
    _ooRenderTonbags();
    _ooUpdateT2Stats();
    showToast('success', '🎲 랜덤 선택: ' + _ooState.selectedTonbags.size + '개');
  };

  /* DRAFT → WAIT_SCAN 전환 */
  window.ooMoveToScan = function() {
    if (_ooState.selectedTonbags.size === 0) {
      showToast('warn', '선택된 톤백이 없습니다');
      return;
    }
    if (!confirm('📦 WAIT_SCAN 진입\n\n선택된 톤백 ' + _ooState.selectedTonbags.size + '개로 스캔 검증 단계로 이동합니다.\n계속하시겠습니까?')) return;
    _ooSetState('WAIT_SCAN');
    _ooUpdateT3Stats();
    setTimeout(function(){ window.ooSwitchTab(3); }, 300);
    showToast('success', 'WAIT_SCAN 진입 — Tab 3 에서 OUT 스캔 검증');
  };

  /* =====================================================================
     [Sprint 1-3-C] Tab 3 — OUT 스캔 검증 + 하드스톱
     ─────────────────────────────────────────────────────────────────────
     검증 룰 (v864-2 매칭):
       |diff_pct| <= 0.5%     → ✅ OK
       0.5% < |diff_pct| ≤ 5% → ⚠️ Warning (REVIEW)
       |diff_pct| > 5%        → 🚫 STOP (ERROR — FINALIZED 차단)
       actual > expected      → 🚫 즉시 하드스톱
     ===================================================================== */
  function _ooUpdateT3Stats() {
    var el = document.getElementById('oo-t3-stats');
    if (!el) return;
    var selCount = _ooState.selectedTonbags.size;
    var selKg = 0;
    Object.keys(_ooState.lotsWithTonbags).forEach(function(lot){
      (_ooState.lotsWithTonbags[lot] || []).forEach(function(t){
        var key = lot + '.' + (t.sub_lt || t.tonbag_id);
        if (_ooState.selectedTonbags.has(key)) selKg += Number(t.weight) || 0;
      });
    });
    var scanned = _ooState.scanRows.length + _ooState.manualScans.length;
    var ok = _ooState.validationResults.filter(function(r){ return r.level === 'ok'; }).length;
    var warn = _ooState.validationResults.filter(function(r){ return r.level === 'warn'; }).length;
    var stop = _ooState.validationResults.filter(function(r){ return r.level === 'stop'; }).length;

    el.innerHTML =
      '<div>📦 검증 대상: <strong>' + selCount + '개 톤백</strong> (' + (selKg / 1000).toFixed(3) + ' MT)</div>' +
      '<div style="margin-top:4px">📊 스캔된 항목: <strong>' + scanned + '건</strong>' +
      (_ooState.validationResults.length ?
        ' · ✅ 통과 <strong style="color:var(--success)">' + ok + '</strong>' +
        ' · ⚠️ 경고 <strong style="color:var(--warning)">' + warn + '</strong>' +
        ' · 🚫 하드스톱 <strong style="color:var(--danger)">' + stop + '</strong>' : '') + '</div>';
  }

  /* CSV/xlsx 업로드 → 백엔드 파싱 */
  window.ooHandleScanFile = function(file) {
    if (!file) return;
    _ooState.scanFile = file;
    var fnEl = document.getElementById('oo-scan-filename');
    if (fnEl) fnEl.textContent = '⏳ 파싱 중: ' + file.name + ' (' + Math.round(file.size / 1024) + ' KB)';

    var form = new FormData();
    form.append('file', file, file.name);
    var xhr = new XMLHttpRequest();
    xhr.open('POST', API + '/api/outbound/onestop-scan-parse');
    xhr.onload = function(){
      var body; try { body = JSON.parse(xhr.responseText); } catch(e){ body = null; }
      if (xhr.status >= 200 && xhr.status < 300 && body && body.ok) {
        var d = body.data || {};
        _ooState.scanRows = d.rows || [];
        if (fnEl) fnEl.innerHTML = '✅ <strong>' + escapeHtml(d.filename) + '</strong> · ' + d.row_count + '행 (UID ' + d.uid_count + ' / actual ' + d.actual_count + ')';
        showToast('success', 'OUT 스캔 파싱: ' + d.row_count + '행');
        _ooUpdateT3Stats();
        var hint = document.getElementById('oo-validation-hint');
        if (hint) hint.textContent = '⚡ 전체 검증 실행 준비 완료';
      } else {
        var msg = (body && (body.detail || body.error || body.message)) || ('HTTP ' + xhr.status);
        if (typeof msg === 'object') msg = JSON.stringify(msg);
        if (fnEl) fnEl.innerHTML = '❌ 파싱 실패: ' + escapeHtml(String(msg));
        showToast('error', '파싱 실패: ' + msg);
        _ooState.scanFile = null;
        _ooState.scanRows = [];
      }
    };
    xhr.onerror = function(){
      if (fnEl) fnEl.textContent = '❌ 네트워크 에러';
      showToast('error', '네트워크 에러');
    };
    xhr.send(form);
  };

  window.ooClearScan = function() {
    _ooState.scanFile = null;
    _ooState.scanRows = [];
    _ooState.manualScans = [];
    _ooState.validationResults = [];
    var fnEl = document.getElementById('oo-scan-filename');
    if (fnEl) fnEl.textContent = '선택된 파일 없음';
    var input = document.getElementById('oo-scan-input');
    if (input) input.value = '';
    var resBody = document.getElementById('oo-validation-results');
    if (resBody) resBody.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text-muted);font-size:12px">⚡ "전체 검증 실행" 버튼을 눌러 결과를 확인하세요</div>';
    var goBtn = document.getElementById('oo-goto-finalize-btn');
    if (goBtn) goBtn.disabled = true;
    var hint = document.getElementById('oo-validation-hint');
    if (hint) hint.textContent = '스캔 데이터를 먼저 업로드/입력';
    _ooUpdateT3Stats();
  };

  window.ooAddManualScan = function() {
    var uid = (document.getElementById('oo-scan-uid') || {}).value || '';
    var act = (document.getElementById('oo-scan-actual') || {}).value || '';
    uid = String(uid).trim();
    if (!uid || !act) { showToast('warn', '톤백 ID와 실제(kg) 필요'); return; }
    var actNum = parseFloat(act);
    if (isNaN(actNum)) { showToast('error', 'actual_kg 가 숫자 아님'); return; }
    _ooState.manualScans.push({ tonbag_uid: uid, actual_kg: actNum });
    document.getElementById('oo-scan-uid').value = '';
    document.getElementById('oo-scan-actual').value = '';
    showToast('success', '수동 추가: ' + uid + ' = ' + actNum + 'kg (총 ' + _ooState.manualScans.length + '건)');
    _ooUpdateT3Stats();
  };

  /* ⚡ 전체 검증 실행 — 선택된 톤백 vs 스캔된 actual */
  window.ooRunValidation = function() {
    if (_ooState.selectedTonbags.size === 0) {
      showToast('error', 'Tab 2에서 톤백을 먼저 선택하세요');
      return;
    }
    var allScans = (_ooState.scanRows || []).concat(_ooState.manualScans || []);
    if (!allScans.length) {
      showToast('error', 'OUT 스캔 데이터를 먼저 업로드/입력하세요');
      return;
    }

    /* 선택된 톤백 → expected map */
    var expectedMap = {};  /* tonbag_uid → {lot_no, expected_kg, weight} */
    Object.keys(_ooState.lotsWithTonbags).forEach(function(lot){
      (_ooState.lotsWithTonbags[lot] || []).forEach(function(t){
        var uid = t.sub_lt || t.tonbag_id;
        var key = lot + '.' + uid;
        if (_ooState.selectedTonbags.has(key)) {
          expectedMap[uid] = {
            lot_no:      lot,
            expected_kg: Number(t.weight) || 0,
            tonbag_no:   t.tonbag_no || '',
            location:    t.location || '',
          };
        }
      });
    });

    /* actual map (덮어쓰기 — 마지막 값 우선) */
    var actualMap = {};
    allScans.forEach(function(s){
      if (s.tonbag_uid && s.actual_kg != null) actualMap[s.tonbag_uid] = Number(s.actual_kg);
    });

    /* 결과 조립 */
    var results = [];
    Object.keys(expectedMap).forEach(function(uid){
      var exp = expectedMap[uid];
      var actual = actualMap[uid];
      var level, message, diffPct = null;
      if (actual == null) {
        level = 'missing'; message = '🔍 스캔 데이터 없음';
      } else {
        diffPct = exp.expected_kg > 0 ? ((actual - exp.expected_kg) / exp.expected_kg) * 100 : 0;
        var absDiff = Math.abs(diffPct);
        if (actual > exp.expected_kg) {
          level = 'stop'; message = '🚫 actual > expected (하드스톱)';
        } else if (absDiff > 5) {
          level = 'stop'; message = '🚫 ' + absDiff.toFixed(2) + '% 편차 (>5% 하드스톱)';
        } else if (absDiff > 0.5) {
          level = 'warn'; message = '⚠️ ' + absDiff.toFixed(2) + '% 편차 (검토 필요)';
        } else {
          level = 'ok'; message = '✅ 통과 (' + absDiff.toFixed(2) + '% 편차)';
        }
      }
      results.push({
        tonbag_uid:  uid,
        lot_no:      exp.lot_no,
        expected_kg: exp.expected_kg,
        actual_kg:   actual,
        diff_pct:    diffPct,
        level:       level,
        message:     message,
      });
    });

    /* 스캔에 있는데 선택 안 된 항목도 표시 (extra) */
    Object.keys(actualMap).forEach(function(uid){
      if (!expectedMap[uid]) {
        results.push({
          tonbag_uid: uid,
          lot_no:     '(미선택)',
          expected_kg: 0,
          actual_kg:   actualMap[uid],
          diff_pct:    null,
          level:       'extra',
          message:     '⚠️ 선택되지 않은 톤백 (스캔만 존재)',
        });
      }
    });

    _ooState.validationResults = results;

    /* 상태 결정 */
    var hasStop = results.some(function(r){ return r.level === 'stop'; });
    var hasWarn = results.some(function(r){ return r.level === 'warn'; });
    if (hasStop) _ooSetState('ERROR');
    else if (hasWarn) _ooSetState('REVIEW');
    /* WAIT_SCAN 유지 (FINALIZED 는 명시적 클릭) */

    _ooRenderValidationResults();
    _ooUpdateT3Stats();

    var goBtn = document.getElementById('oo-goto-finalize-btn');
    if (goBtn) {
      goBtn.disabled = hasStop;
      if (hasStop) goBtn.title = '🚫 하드스톱 발견 — FINALIZED 진입 불가';
      else if (hasWarn) goBtn.title = '⚠️ 경고 있음 — 검토 후 FINALIZED 진입 가능';
      else goBtn.title = '✅ 모두 통과 — FINALIZED 진입 가능';
    }
    var hint = document.getElementById('oo-validation-hint');
    if (hint) {
      var summary = '✅ ' + results.filter(function(r){return r.level==='ok';}).length +
                    ' · ⚠️ ' + results.filter(function(r){return r.level==='warn';}).length +
                    ' · 🚫 ' + results.filter(function(r){return r.level==='stop';}).length;
      hint.textContent = '검증 완료: ' + summary;
    }
    if (hasStop) showToast('error', '🚫 하드스톱 발견 — 파일 확인 후 재검증');
    else if (hasWarn) showToast('warn', '⚠️ 일부 편차 — 검토 후 진행');
    else showToast('success', '✅ 모든 톤백 통과 — FINALIZED 진입 가능');
  };

  function _ooRenderValidationResults() {
    var body = document.getElementById('oo-validation-results');
    if (!body) return;
    var results = _ooState.validationResults;
    if (!results.length) { body.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text-muted)">검증 결과 없음</div>'; return; }

    var levelStyle = {
      ok:      'background:rgba(102,187,106,.1)',
      warn:    'background:rgba(255,167,38,.15)',
      stop:    'background:rgba(244,67,54,.18)',
      missing: 'background:rgba(158,158,158,.1)',
      extra:   'background:rgba(66,165,245,.1)',
    };

    var rows = results.map(function(r, i){
      var style = levelStyle[r.level] || '';
      var diff = (r.diff_pct == null) ? '-' : (r.diff_pct >= 0 ? '+' : '') + r.diff_pct.toFixed(2) + '%';
      return '<tr style="' + style + '">' +
        '<td style="text-align:right">' + (i+1) + '</td>' +
        '<td class="mono-cell">' + escapeHtml(r.tonbag_uid) + '</td>' +
        '<td class="mono-cell" style="color:var(--accent)">' + escapeHtml(r.lot_no) + '</td>' +
        '<td class="mono-cell" style="text-align:right">' + (r.expected_kg ? r.expected_kg.toFixed(2) : '-') + '</td>' +
        '<td class="mono-cell" style="text-align:right">' + (r.actual_kg != null ? r.actual_kg.toFixed(2) : '-') + '</td>' +
        '<td class="mono-cell" style="text-align:right">' + diff + '</td>' +
        '<td>' + escapeHtml(r.message) + '</td>' +
        '</tr>';
    }).join('');

    body.innerHTML =
      '<table class="data-table" style="font-size:11px"><thead><tr>' +
      '<th>#</th><th>톤백 UID</th><th>LOT</th><th style="text-align:right">Expected (kg)</th><th style="text-align:right">Actual (kg)</th><th style="text-align:right">Diff %</th><th>상태</th>' +
      '</tr></thead><tbody>' + rows + '</tbody></table>';
  }

  /* WAIT_SCAN → FINALIZED 전환 */
  window.ooMoveToFinalize = function() {
    var hasStop = _ooState.validationResults.some(function(r){ return r.level === 'stop'; });
    if (hasStop) {
      showToast('error', '🚫 하드스톱 발견 — FINALIZED 진입 불가');
      return;
    }
    var hasWarn = _ooState.validationResults.some(function(r){ return r.level === 'warn'; });
    var msg = '✅ FINALIZED 진입\n\n검증 통과: ' + _ooState.selectedTonbags.size + '개 톤백\n' +
              (hasWarn ? '⚠️ 일부 경고 있음 — 검토하셨나요?\n' : '') +
              'Tab 4 에서 출고 확정합니다. 계속하시겠습니까?';
    if (!confirm(msg)) return;
    _ooSetState('FINALIZED');
    _ooUpdateT4Stats();
    var confirmBtn = document.getElementById('oo-confirm-btn');
    if (confirmBtn) confirmBtn.disabled = false;
    setTimeout(function(){ window.ooSwitchTab(4); }, 300);
    showToast('success', 'FINALIZED 진입 — Tab 4 에서 출고 확정');
  };

  /* =====================================================================
     [Sprint 1-3-D] Tab 4 — 완료 + 감사 로그 sub-popup
     ===================================================================== */
  function _ooUpdateT4Stats() {
    var el = document.getElementById('oo-t4-stats');
    if (!el) return;
    var selCount = _ooState.selectedTonbags.size;
    var selKg = 0;
    Object.keys(_ooState.lotsWithTonbags).forEach(function(lot){
      (_ooState.lotsWithTonbags[lot] || []).forEach(function(t){
        var key = lot + '.' + (t.sub_lt || t.tonbag_id);
        if (_ooState.selectedTonbags.has(key)) selKg += Number(t.weight) || 0;
      });
    });
    var doneCount = _ooState.completedItems.length;
    el.innerHTML =
      '<div>✅ FINALIZED 진입 — <strong>' + selCount + '개 톤백</strong> (' + (selKg / 1000).toFixed(3) + ' MT)</div>' +
      '<div style="margin-top:4px">📦 출고 완료: <strong style="color:' + (doneCount > 0 ? 'var(--success)' : 'var(--text-muted)') + '">' + doneCount + '건</strong> · 대기: ' + (selCount - doneCount) + '건</div>';
  }

  /* 📦 확정건 출고 완료 — 선택된 톤백을 PICKED → OUTBOUND 전환 */
  window.ooConfirmOutbound = function() {
    if (_ooState.state !== 'FINALIZED') {
      showToast('warn', 'FINALIZED 상태가 아닙니다 — Tab 3 검증 후 ▶ 진행');
      return;
    }
    if (_ooState.selectedTonbags.size === 0) {
      showToast('error', '확정할 톤백 없음');
      return;
    }
    /* LOT별 카운트 집계 */
    var lotCounts = {};
    _ooState.selectedTonbags.forEach(function(key){
      var lot = key.split('.')[0];
      lotCounts[lot] = (lotCounts[lot] || 0) + 1;
    });
    var summary = Object.keys(lotCounts).map(function(lot){
      return lot + ' (' + lotCounts[lot] + '개)';
    }).join(', ');
    if (!confirm('📦 출고 확정\n\n총 ' + _ooState.selectedTonbags.size + '개 톤백을 OUTBOUND 처리합니다.\n' + summary + '\n\n계속하시겠습니까?')) return;

    var btn = document.getElementById('oo-confirm-btn');
    if (btn) { btn.disabled = true; btn.textContent = '⏳ 처리 중...'; }

    /* LOT별로 /api/outbound/confirm 호출 (count 단위) */
    var promises = Object.keys(lotCounts).map(function(lot){
      return apiPost('/api/outbound/confirm', {
        lot_no:   lot,
        count:    lotCounts[lot],
        customer: _ooState.customer || (_ooState.parsedItems[0] || {}).customer || '',
        sale_ref: _ooState.saleRef  || (_ooState.parsedItems[0] || {}).sale_ref || '',
        operator: 'onestop_outbound',
      })
        .then(function(res){
          var ok = res && (res.ok !== false) && !(res.detail && res.detail.code === 'CONFIRM_FAILED');
          var data = (res && res.data) || {};
          return {
            lot:       lot,
            ok:        ok,
            confirmed: data.confirmed || 0,
            count:     lotCounts[lot],
            message:   res.message || (ok ? '확정' : '실패'),
          };
        })
        .catch(function(e){
          return { lot: lot, ok: false, confirmed: 0, count: lotCounts[lot], message: (e && e.message) || String(e) };
        });
    });

    Promise.all(promises).then(function(results){
      var totalOk = results.reduce(function(s, r){ return s + (r.ok ? r.confirmed : 0); }, 0);
      var totalFail = results.filter(function(r){ return !r.ok; }).length;
      var batchId = 'oo_' + Date.now().toString(36);
      var record = {
        timestamp:  new Date().toISOString(),
        batch_id:   batchId,
        results:    results,
        total_ok:   totalOk,
        total_fail: totalFail,
        customer:   _ooState.customer,
        sale_ref:   _ooState.saleRef,
        proof_dir:  null,  /* proof-upload 후 채워짐 */
      };
      _ooState.completedItems.push(record);
      _ooUpdateT4Stats();
      _ooRenderT4History();

      /* [Sprint 1-3-E] 출고 성공 시 근거문서 업로드 */
      if (totalFail === 0 && _ooState.proofDocs.length > 0) {
        var pForm = new FormData();
        pForm.append('batch_id', batchId);
        _ooState.proofDocs.forEach(function(f){ pForm.append('files', f, f.name); });
        var pXhr = new XMLHttpRequest();
        pXhr.open('POST', API + '/api/outbound/proof-upload');
        pXhr.onload = function(){
          var pBody; try { pBody = JSON.parse(pXhr.responseText); } catch(e){ pBody = null; }
          if (pXhr.status >= 200 && pXhr.status < 300 && pBody && pBody.ok) {
            var pd = pBody.data || {};
            record.proof_dir = pd.directory;
            _ooRenderT4History();
            showToast('success', '📎 근거문서 ' + pd.saved_count + '개 저장됨 (' + pd.date + '/' + batchId + ')');
          } else {
            showToast('warn', '근거문서 저장 실패 (출고는 완료됨) — ' + ((pBody && pBody.detail) || pXhr.status));
          }
        };
        pXhr.onerror = function(){ showToast('warn', '근거문서 저장 네트워크 에러'); };
        pXhr.send(pForm);
      }

      if (btn) {
        btn.textContent = totalFail === 0 ? '✅ 출고 완료 (' + totalOk + '개)' : '⚠️ 부분 실패 (' + totalOk + '/' + (totalOk + totalFail) + ')';
      }
      if (totalFail === 0) {
        showToast('success', '✅ 출고 확정: ' + totalOk + '개 OUTBOUND 처리됨');
        if (typeof loadKpi === 'function') loadKpi();
      } else {
        showToast('warn', '⚠️ 부분 실패: ' + totalFail + '건 — 이력 확인');
        if (btn) btn.disabled = false;
      }
    });
  };

  function _ooRenderT4History() {
    var el = document.getElementById('oo-t4-history');
    if (!el) return;
    var items = _ooState.completedItems;
    if (!items.length) {
      el.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text-muted);font-size:12px">아직 완료된 항목이 없습니다</div>';
      return;
    }
    var rows = items.map(function(item, i){
      var t = new Date(item.timestamp);
      var timeStr = [t.getHours(), t.getMinutes(), t.getSeconds()].map(function(n){ return String(n).padStart(2, '0'); }).join(':');
      var lotsSummary = item.results.map(function(r){
        return '<span style="color:' + (r.ok ? 'var(--success)' : 'var(--danger)') + '">' + escapeHtml(r.lot) + '×' + r.count + (r.ok ? '' : ' ❌') + '</span>';
      }).join(', ');
      var proofBadge = item.proof_dir
        ? ' <span class="tag" style="background:rgba(66,165,245,.2);color:#42a5f5;font-size:9px" title="' + escapeHtml(item.proof_dir) + '">📎 ' + (item.proof_dir.split('/').pop() || 'docs') + '</span>'
        : '';
      return '<tr>' +
        '<td style="text-align:right">' + (i+1) + '</td>' +
        '<td class="mono-cell">' + timeStr + '</td>' +
        '<td>' + lotsSummary + '</td>' +
        '<td class="mono-cell" style="text-align:right">' + (item.total_ok + item.total_fail) + '</td>' +
        '<td>' + escapeHtml(item.customer || '-') + '</td>' +
        '<td class="mono-cell">' + escapeHtml(item.sale_ref || '-') + '</td>' +
        '<td>' + (item.total_fail === 0 ? '<span style="color:var(--success)">✅ OK</span>' : '<span style="color:var(--warning)">⚠️ ' + item.total_fail + ' 실패</span>') + proofBadge + '</td>' +
        '</tr>';
    }).join('');
    el.innerHTML =
      '<table class="data-table" style="font-size:11px"><thead><tr>' +
      '<th>#</th><th>시간</th><th>LOT (개수)</th><th style="text-align:right">총수</th><th>고객</th><th>Sale Ref</th><th>상태</th>' +
      '</tr></thead><tbody>' + rows + '</tbody></table>';
  }

  /* 📋 감사 로그 보기 — sub-popup (메인 모달 위에 z-index 10001) */
  window.ooViewAuditLog = function() {
    /* 기존 sub-popup 제거 */
    var old = document.getElementById('oo-audit-popup');
    if (old) old.remove();

    var html =
      '<div id="oo-audit-popup-inner" style="background:var(--bg-card);border-radius:8px;width:90%;max-width:900px;max-height:80vh;display:flex;flex-direction:column;padding:20px;position:relative">' +
      '<button onclick="document.getElementById(\'oo-audit-popup\').remove()" style="position:absolute;top:10px;right:14px;background:none;border:none;font-size:1.4rem;cursor:pointer;color:var(--text-muted)">&times;</button>' +
      '<h3 style="margin:0 0 12px 0">📋 감사 로그 (audit_log)</h3>' +
      /* 필터 */
      '<div style="display:flex;gap:6px;align-items:center;flex-wrap:wrap;padding:8px 10px;background:var(--panel);border:1px solid var(--panel-border);border-radius:6px;margin-bottom:8px;font-size:12px">' +
      '  <label>이벤트:</label><select id="oo-audit-event" style="padding:3px 6px;background:var(--bg-hover);border:1px solid var(--panel-border);border-radius:3px"><option value="">전체</option></select>' +
      '  <label>From:</label><input type="date" id="oo-audit-from" style="padding:3px 6px;background:var(--bg-hover);border:1px solid var(--panel-border);border-radius:3px">' +
      '  <label>To:</label><input type="date" id="oo-audit-to" style="padding:3px 6px;background:var(--bg-hover);border:1px solid var(--panel-border);border-radius:3px">' +
      '  <label>LOT:</label><input type="text" id="oo-audit-lot" placeholder="LOT NO" style="padding:3px 6px;background:var(--bg-hover);border:1px solid var(--panel-border);border-radius:3px;width:120px;font-family:Consolas,monospace">' +
      '  <button class="btn" onclick="window.ooLoadAuditLog()">🔄 조회</button>' +
      '  <button class="btn" onclick="window.ooExportAuditCsv()" style="margin-left:auto">📥 CSV 내보내기</button>' +
      '</div>' +
      /* 테이블 */
      '<div id="oo-audit-body" style="flex:1;overflow-y:auto;border:1px solid var(--panel-border);border-radius:6px;padding:8px">' +
      '<div style="padding:30px;text-align:center;color:var(--text-muted)">⏳ 로딩 중...</div>' +
      '</div>' +
      '</div>';

    var popup = document.createElement('div');
    popup.id = 'oo-audit-popup';
    popup.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:10001;display:flex;align-items:center;justify-content:center;padding:20px';
    popup.innerHTML = html;
    /* 외부 클릭으로 닫기 */
    popup.addEventListener('click', function(e){ if (e.target === popup) popup.remove(); });
    document.body.appendChild(popup);

    /* 기본 7일 범위 */
    var today = new Date();
    var weekAgo = new Date(today.getTime() - 7 * 86400000);
    var fmt = function(d){ return d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0') + '-' + String(d.getDate()).padStart(2,'0'); };
    document.getElementById('oo-audit-from').value = fmt(weekAgo);
    document.getElementById('oo-audit-to').value = fmt(today);

    window.ooLoadAuditLog();
  };

  /* 감사 로그 조회 */
  window._ooLastAuditRows = [];
  window.ooLoadAuditLog = function() {
    var ev   = (document.getElementById('oo-audit-event') || {}).value || '';
    var from = (document.getElementById('oo-audit-from')  || {}).value || '';
    var to   = (document.getElementById('oo-audit-to')    || {}).value || '';
    var lot  = (document.getElementById('oo-audit-lot')   || {}).value || '';
    var qs = ['limit=500'];
    if (ev)   qs.push('event_type=' + encodeURIComponent(ev));
    if (from) qs.push('from_date='  + encodeURIComponent(from));
    if (to)   qs.push('to_date='    + encodeURIComponent(to));
    if (lot)  qs.push('lot_no='     + encodeURIComponent(lot));

    var body = document.getElementById('oo-audit-body');
    if (body) body.innerHTML = '<div style="padding:30px;text-align:center;color:var(--text-muted)">⏳ 조회 중...</div>';

    apiGet('/api/q/audit-log?' + qs.join('&'))
      .then(function(res){
        var d = (res && res.data) || {};
        var rows = d.items || [];
        window._ooLastAuditRows = rows;

        /* 이벤트 타입 드롭다운 채우기 */
        var sel = document.getElementById('oo-audit-event');
        if (sel && d.available_event_types) {
          var current = sel.value;
          var opts = '<option value="">전체</option>' +
            d.available_event_types.map(function(et){
              return '<option value="' + escapeHtml(et) + '"' + (et === current ? ' selected' : '') + '>' + escapeHtml(et) + '</option>';
            }).join('');
          sel.innerHTML = opts;
        }

        if (!body) return;
        if (!rows.length) {
          body.innerHTML = '<div style="padding:30px;text-align:center;color:var(--text-muted)">📭 조건에 맞는 로그 없음</div>';
          return;
        }
        var trs = rows.map(function(r){
          var t = r.created_at ? new Date(r.created_at).toLocaleString('ko-KR') : '';
          return '<tr>' +
            '<td class="mono-cell" style="font-size:10px">' + escapeHtml(String(r.id)) + '</td>' +
            '<td><span class="tag" style="font-size:10px">' + escapeHtml(r.event_type || '-') + '</span></td>' +
            '<td class="mono-cell" style="font-size:10px">' + escapeHtml(t) + '</td>' +
            '<td class="mono-cell" style="font-size:10px">' + escapeHtml(r.batch_id || '-') + '</td>' +
            '<td class="mono-cell" style="font-size:10px">' + escapeHtml(r.tonbag_id || '-') + '</td>' +
            '<td style="font-size:10px;max-width:240px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="' + escapeHtml(r.event_data || '') + '">' + escapeHtml(r.event_data || '-') + '</td>' +
            '<td class="mono-cell" style="font-size:10px">' + escapeHtml(r.created_by || '-') + '</td>' +
            '</tr>';
        }).join('');
        body.innerHTML =
          '<table class="data-table" style="font-size:11px"><thead><tr>' +
          '<th>ID</th><th>이벤트</th><th>시간</th><th>Batch</th><th>Tonbag</th><th>상세 데이터</th><th>By</th>' +
          '</tr></thead><tbody>' + trs + '</tbody></table>' +
          '<div style="text-align:right;margin-top:6px;font-size:11px;color:var(--text-muted)">총 ' + rows.length + '건</div>';
      })
      .catch(function(e){
        if (body) body.innerHTML = '<div style="padding:30px;color:var(--danger);text-align:center">조회 실패: ' + escapeHtml(e.message || String(e)) + '</div>';
      });
  };

  /* CSV 내보내기 */
  window.ooExportAuditCsv = function() {
    var rows = window._ooLastAuditRows || [];
    if (!rows.length) { showToast('warn', '내보낼 로그 없음 — 먼저 조회하세요'); return; }
    var headers = ['id', 'event_type', 'created_at', 'batch_id', 'tonbag_id', 'event_data', 'user_note', 'created_by'];
    var csvLines = [headers.join(',')];
    rows.forEach(function(r){
      var line = headers.map(function(h){
        var v = r[h] == null ? '' : String(r[h]);
        /* CSV 이스케이프: 쉼표/줄바꿈/따옴표 포함 시 따옴표 감싸기 */
        if (/[,"\n]/.test(v)) v = '"' + v.replace(/"/g, '""') + '"';
        return v;
      }).join(',');
      csvLines.push(line);
    });
    var csv = csvLines.join('\n');
    /* BOM 포함 (Excel 한글 호환) */
    var blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    var ts = new Date();
    var name = 'audit_log_' + ts.getFullYear() + String(ts.getMonth()+1).padStart(2,'0') + String(ts.getDate()).padStart(2,'0') + '_' + String(ts.getHours()).padStart(2,'0') + String(ts.getMinutes()).padStart(2,'0') + '.csv';
    a.download = name;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast('success', '📥 ' + name + ' 다운로드됨 (' + rows.length + '건)');
  };

  /* 📋 새 출고 시작 */
  window.ooStartNew = function() {
    if (!confirm('📋 새 출고 시작\n\n현재 진행 상태(파싱/선택/검증/완료 이력)가 모두 초기화됩니다.\n계속하시겠습니까?')) return;
    _ooReset();
    /* UI 초기화 */
    var resetIds = ['oo-customer', 'oo-sale-ref', 'oo-lot', 'oo-paste',
                    'oo-manual-lot', 'oo-manual-actual',
                    'oo-scan-uid', 'oo-scan-actual'];
    resetIds.forEach(function(id){
      var el = document.getElementById(id);
      if (el) el.value = '';
    });
    var fnEl = document.getElementById('oo-scan-filename');
    if (fnEl) fnEl.textContent = '선택된 파일 없음';
    var manList = document.getElementById('oo-manual-list');
    if (manList) manList.textContent = '';
    var proofEl = document.getElementById('oo-proof-files');
    if (proofEl) proofEl.innerHTML = '';
    var draftRes = document.getElementById('oo-draft-result');
    if (draftRes) draftRes.innerHTML = '';
    var tonbagBody = document.getElementById('oo-tonbags-body');
    if (tonbagBody) tonbagBody.innerHTML = '<div style="padding:30px;text-align:center;color:var(--text-muted);font-size:12px">⏳ DRAFT 진입 시 자동 로드됩니다</div>';
    var validRes = document.getElementById('oo-validation-results');
    if (validRes) validRes.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text-muted);font-size:12px">⚡ "전체 검증 실행" 버튼을 눌러 결과를 확인하세요</div>';
    var historyEl = document.getElementById('oo-t4-history');
    if (historyEl) historyEl.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text-muted);font-size:12px">아직 완료된 항목이 없습니다</div>';
    var confirmBtn = document.getElementById('oo-confirm-btn');
    if (confirmBtn) { confirmBtn.disabled = true; confirmBtn.textContent = '📦 확정건 출고 완료 ▶'; }
    /* 상태 초기화 + Tab 1로 */
    _ooSetState('DRAFT');
    _ooUpdateT2Stats();
    _ooUpdateT3Stats();
    _ooUpdateT4Stats();
    window.ooSwitchTab(1);
    /* 출고일 다시 오늘 */
    var dateInput = document.getElementById('oo-date');
    if (dateInput) {
      var d = new Date();
      dateInput.value = d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0') + '-' + String(d.getDate()).padStart(2,'0');
    }
    showToast('info', '📋 새 출고 시작 — Tab 1로 이동');
  };

  /* ooFinalize 는 이전에 placeholder. 이제 ooConfirmOutbound 로 대체됨 — 호환성 위해 유지 */
  window.ooFinalize = function() { window.ooConfirmOutbound(); };

  /* =====================================================================
     [Sprint 1-4] IntegrityV760Dialog — v864-2 integrity_v760_dialog.py 매칭
     6 카드 + LOT 신호등 테이블 + 상세 패널 + 자동 복구
     ===================================================================== */
  var _intState = { data: null, selectedLot: null };

  function showIntegrityV760Modal(autoFix) {
    var cardsHtml =
      '<div style="display:grid;grid-template-columns:repeat(6,1fr);gap:8px;margin-bottom:12px">' +
      ['total_lots:전체 LOT:#42a5f5',
       'error_lots:🔴 오류:#f44336',
       'warning_lots:🟡 경고:#ffa726',
       'ok_lots:✅ 정상:#66bb6a',
       'partial_lots:⚠️ 부분 출고:#ab47bc',
       'alloc_issues:📊 Alloc 이상:#ec407a'].map(function(spec){
        var p = spec.split(':');
        return '<div style="background:var(--panel);border:1px solid var(--panel-border);border-left:4px solid ' + p[2] + ';border-radius:6px;padding:10px 12px">' +
          '<div style="font-size:11px;color:var(--text-muted);font-weight:600">' + p[1] + '</div>' +
          '<div id="int-card-' + p[0] + '" style="font-size:22px;font-weight:700;color:' + p[2] + ';margin-top:2px">--</div>' +
          '</div>';
      }).join('') + '</div>';

    var html = [
      '<div style="max-width:1100px">',
      '  <h2 style="margin:0 0 8px 0">📋 정합성 검증 리포트 v7.7.0 <span style="font-size:11px;color:var(--text-muted);font-weight:400" id="int-status-line">— 로딩 중...</span></h2>',
      cardsHtml,
      /* 좌: LOT 테이블 / 우: 상세 패널 */
      '  <div style="display:grid;grid-template-columns:1.2fr 1fr;gap:12px;margin-bottom:10px">',
      '    <div style="background:var(--panel);border:1px solid var(--panel-border);border-radius:6px;padding:10px">',
      '      <div style="font-weight:700;margin-bottom:6px;font-size:13px">📋 LOT 정합성 상세</div>',
      '      <div id="int-lots-body" style="max-height:340px;overflow-y:auto">',
      '        <div style="padding:30px;text-align:center;color:var(--text-muted);font-size:12px">⏳ 로딩 중...</div>',
      '      </div>',
      '    </div>',
      '    <div style="background:var(--panel);border:1px solid var(--panel-border);border-radius:6px;padding:10px">',
      '      <div style="font-weight:700;margin-bottom:6px;font-size:13px">🔍 선택 LOT 상세</div>',
      '      <div id="int-detail-body" style="height:340px;overflow-y:auto;font-family:Consolas,monospace;font-size:11px;background:var(--bg);border:1px solid var(--panel-border);border-radius:4px;padding:10px;white-space:pre-wrap;color:var(--fg)">LOT 행을 클릭하면 상세 정보가 표시됩니다.</div>',
      '    </div>',
      '  </div>',
      /* Alloc 이상 (있으면) */
      '  <div id="int-alloc-issues-section" style="display:none;background:rgba(236,64,122,.1);border-left:3px solid #ec407a;padding:10px;border-radius:4px;margin-bottom:10px">',
      '    <div style="font-weight:700;color:#ec407a;font-size:12px;margin-bottom:4px">📊 Allocation 이상 (inventory 없음)</div>',
      '    <div id="int-alloc-issues-body" style="font-size:11px;color:var(--text-muted)"></div>',
      '  </div>',
      /* 액션 */
      '  <div style="display:flex;gap:8px;justify-content:flex-end;align-items:center">',
      '    <span id="int-checked-at" style="margin-right:auto;color:var(--text-muted);font-size:11px"></span>',
      '    <button class="btn" onclick="window.intRefresh()">🔄 새로고침</button>',
      '    <button class="btn" onclick="window.intExportCsv()">📥 Excel 저장</button>',
      '    <button class="btn btn-primary" onclick="window.intRunFix()" id="int-fix-btn" disabled>🛠️ 자동 복구</button>',
      '    <button class="btn btn-ghost" onclick="document.getElementById(\'sqm-modal\').style.display=\'none\'">닫기</button>',
      '  </div>',
      '</div>'
    ].join('');
    showDataModal('', html);
    window.intRefresh(autoFix);
  }
  window.showIntegrityV760Modal = showIntegrityV760Modal;

  window.intRefresh = function(autoFixAfterLoad) {
    _intState.data = null;
    _intState.selectedLot = null;
    apiGet('/api/action/integrity-report')
      .then(function(res){
        if (!res || !res.ok) throw new Error((res && res.error) || '정합성 조회 실패');
        var d = res.data || {};
        _intState.data = d;
        /* 카드 채우기 */
        ['total_lots','error_lots','warning_lots','ok_lots','partial_lots','alloc_issues'].forEach(function(k){
          var el = document.getElementById('int-card-' + k);
          if (el) el.textContent = (d.cards && d.cards[k] != null) ? d.cards[k] : '0';
        });
        /* 상태 라인 */
        var statusEl = document.getElementById('int-status-line');
        if (statusEl) {
          var lvl = d.overall_level || 'unknown';
          var txt = lvl === 'ok' ? '✅ 통과' : (lvl === 'warning' ? '⚠️ 경고 있음' : '🔴 오류 있음');
          var color = lvl === 'ok' ? 'var(--success)' : (lvl === 'warning' ? 'var(--warning)' : 'var(--danger)');
          statusEl.innerHTML = '— <span style="color:' + color + '">' + txt + '</span>';
        }
        /* LOT 테이블 */
        _intRenderLots(d.lots || []);
        /* Alloc 이상 */
        var allocSec = document.getElementById('int-alloc-issues-section');
        var allocBody = document.getElementById('int-alloc-issues-body');
        if (d.alloc_issues && d.alloc_issues.length) {
          if (allocSec) allocSec.style.display = '';
          if (allocBody) allocBody.innerHTML = d.alloc_issues.map(function(a){
            return '• <strong>' + escapeHtml(a.lot_no) + '</strong> (' + (a.qty_mt || 0).toFixed(3) + ' MT, alloc_status=' + escapeHtml(a.alloc_status || '-') + ')';
          }).join('<br>');
        } else {
          if (allocSec) allocSec.style.display = 'none';
        }
        /* 검사 시간 */
        var atEl = document.getElementById('int-checked-at');
        if (atEl && d.checked_at) atEl.textContent = '검사 시각: ' + d.checked_at;
        /* 자동 복구 버튼 활성화 */
        var fixBtn = document.getElementById('int-fix-btn');
        var canFix = (d.cards && (d.cards.error_lots > 0 || d.cards.orphan_tonbags > 0));
        if (fixBtn) fixBtn.disabled = !canFix;

        if (autoFixAfterLoad && canFix) {
          /* 메뉴에서 "🛠️ LOT 상태 정합성 복구"로 진입한 경우 자동 확인 */
          setTimeout(function(){ window.intRunFix(); }, 200);
        }
      })
      .catch(function(e){
        var body = document.getElementById('int-lots-body');
        if (body) body.innerHTML = '<div style="padding:30px;color:var(--danger);text-align:center">조회 실패: ' + escapeHtml(e.message || String(e)) + '</div>';
      });
  };

  function _intRenderLots(lots) {
    var body = document.getElementById('int-lots-body');
    if (!body) return;
    if (!lots.length) {
      body.innerHTML = '<div style="padding:20px;text-align:center;color:var(--success);font-weight:700">✅ 모든 LOT 정합성 통과</div>';
      return;
    }
    var levelColor = {
      error:   'rgba(244,67,54,.18)',
      warning: 'rgba(255,167,38,.15)',
      ok:      'transparent',
    };
    var rows = lots.map(function(l){
      var bg = levelColor[l.level] || '';
      var icon = l.level === 'error' ? '🔴' : (l.level === 'warning' ? '🟡' : '✅');
      var sample = l.errors.length ? l.errors[0].message : (l.warnings.length ? l.warnings[0].message : (l.partial ? '부분 출고 ' + l.partial.shipped + '/' + l.partial.total : '-'));
      return '<tr style="background:' + bg + ';cursor:pointer" onclick="window.intSelectLot(\'' + escapeHtml(l.lot_no) + '\')">' +
        '<td>' + icon + '</td>' +
        '<td class="mono-cell" style="color:var(--accent)">' + escapeHtml(l.lot_no) + '</td>' +
        '<td>' + (l.partial ? '⚠️ ' + l.partial.shipped + '/' + l.partial.total : '-') + '</td>' +
        '<td>' + (l.in_allocation ? '📊' : '-') + '</td>' +
        '<td style="text-align:right">' + l.errors.length + '</td>' +
        '<td style="text-align:right">' + l.warnings.length + '</td>' +
        '</tr>';
    }).join('');
    body.innerHTML =
      '<table class="data-table" style="font-size:11px"><thead><tr>' +
      '<th></th><th>LOT NO</th><th>부분 출고</th><th>Alloc</th><th style="text-align:right">오류</th><th style="text-align:right">경고</th>' +
      '</tr></thead><tbody>' + rows + '</tbody></table>';
  }

  window.intSelectLot = function(lot) {
    _intState.selectedLot = lot;
    var detail = document.getElementById('int-detail-body');
    if (!detail || !_intState.data) return;
    var l = (_intState.data.lots || []).find(function(x){ return x.lot_no === lot; });
    if (!l) { detail.textContent = '선택 정보 없음'; return; }
    var lines = [];
    lines.push('LOT NO: ' + lot);
    lines.push('상태:   ' + l.level);
    lines.push('');
    if (l.errors.length) {
      lines.push('━━ 오류 (' + l.errors.length + '건) ━━');
      l.errors.forEach(function(e){ lines.push('🔴 [' + e.code + '] ' + e.message); });
      lines.push('');
    }
    if (l.warnings.length) {
      lines.push('━━ 경고 (' + l.warnings.length + '건) ━━');
      l.warnings.forEach(function(e){ lines.push('🟡 [' + e.code + '] ' + e.message); });
      lines.push('');
    }
    if (l.partial) {
      lines.push('━━ 부분 출고 ━━');
      lines.push('⚠️ 출고 ' + l.partial.shipped + ' / 전체 ' + l.partial.total + ' 톤백');
      lines.push('');
    }
    if (l.in_allocation) {
      lines.push('━━ Allocation ━━');
      lines.push('📊 Allocation 이상 리스트에 포함됨 (하단 참조)');
      lines.push('');
    }
    if (!l.errors.length && !l.warnings.length && !l.partial && !l.in_allocation) {
      lines.push('✅ 이 LOT는 정상입니다.');
    }
    detail.textContent = lines.join('\n');
  };

  window.intExportCsv = function() {
    if (!_intState.data || !_intState.data.lots) { showToast('warn', '데이터 없음'); return; }
    var lots = _intState.data.lots;
    var lines = ['lot_no,level,errors,warnings,partial_shipped,partial_total,in_allocation,error_msgs,warning_msgs'];
    lots.forEach(function(l){
      var errMsgs = l.errors.map(function(e){ return e.code + ':' + e.message; }).join(';');
      var warnMsgs = l.warnings.map(function(e){ return e.code + ':' + e.message; }).join(';');
      function csvEsc(v){ var s = String(v == null ? '' : v); if (/[,"\n]/.test(s)) s = '"' + s.replace(/"/g,'""') + '"'; return s; }
      lines.push([
        csvEsc(l.lot_no), csvEsc(l.level),
        l.errors.length, l.warnings.length,
        l.partial ? l.partial.shipped : '',
        l.partial ? l.partial.total : '',
        l.in_allocation ? 'Y' : 'N',
        csvEsc(errMsgs), csvEsc(warnMsgs)
      ].join(','));
    });
    var blob = new Blob(['\ufeff' + lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url;
    var ts = new Date();
    a.download = 'integrity_v760_' + ts.getFullYear() + String(ts.getMonth()+1).padStart(2,'0') + String(ts.getDate()).padStart(2,'0') + '_' + String(ts.getHours()).padStart(2,'0') + String(ts.getMinutes()).padStart(2,'0') + '.csv';
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast('success', '📥 ' + a.download + ' 다운로드됨 (' + lots.length + 'LOT)');
  };

  window.intRunFix = function() {
    if (!confirm('🛠️ 정합성 자동 복구\n\n다음을 자동 처리:\n  - tonbag_count 동기화\n  - 고아(orphan) 톤백 삭제\n\n상태 혼재는 수동 처리 필요.\n계속하시겠습니까?')) return;
    var btn = document.getElementById('int-fix-btn');
    if (btn) { btn.disabled = true; btn.textContent = '⏳ 복구 중...'; }
    apiPost('/api/action/fix-integrity', {})
      .then(function(res){
        if (!res || !res.ok) throw new Error((res && res.error) || '복구 실패');
        var d = res.data || {};
        var msg = '복구 완료 — ' + (d.fix_count || 0) + '건 처리';
        if (d.fixes && d.fixes.length) {
          msg += '\n' + d.fixes.map(function(f){ return '  ' + f.action + ': ' + f.affected_rows + '건'; }).join('\n');
        } else {
          msg = '복구할 항목 없음 (이미 정상)';
        }
        alert(msg);
        if (btn) btn.textContent = '🛠️ 자동 복구';
        window.intRefresh();
      })
      .catch(function(e){
        showToast('error', '복구 실패: ' + (e.message || String(e)));
        if (btn) { btn.disabled = false; btn.textContent = '🛠️ 자동 복구 재시도'; }
      });
  };

  /* ─── 플레이스홀더 ──────────────────────────────────────────────────── */
  window.ooFinalize = function() {
    showToast('info', '출고 확정: Sprint 1-3 Phase D (Tab 4 완료) 에서 구현 예정');
  };
  window.ooViewAuditLog = function() {
    showToast('info', '감사 로그 sub-popup: Sprint 1-3 Phase D 에서 구현 (오늘은 기존 📋 감사 로그 조회 메뉴 사용)');
  };

  /* 기존 showQuickOutboundModal (레거시 — 단순 즉시 출고) */
  function showQuickOutboundModal() {
    var html = [
      '<div style="max-width:560px">',
      '  <h2 style="margin:0 0 12px 0">🚀 즉시 출고 (원스톱)</h2>',
      '  <p style="color:var(--text-muted);margin:0 0 16px 0;font-size:.9rem">',
      '    Allocation 없이 소량 톤백을 바로 출고합니다. (AVAILABLE → PICKED)',
      '  </p>',
      '  <div style="display:grid;grid-template-columns:110px 1fr;gap:10px;align-items:center;margin-bottom:12px">',
      '    <label style="font-weight:600">LOT 번호</label>',
      '    <input type="text" id="qo-lot" placeholder="예: 1126013063" style="padding:8px;background:var(--bg-hover);color:var(--text);border:1px solid var(--border);border-radius:6px;font-family:monospace">',
      '    <label style="font-weight:600">톤백 수</label>',
      '    <input type="number" id="qo-count" min="1" value="1" style="padding:8px;background:var(--bg-hover);color:var(--text);border:1px solid var(--border);border-radius:6px;width:120px">',
      '    <label style="font-weight:600">고객명</label>',
      '    <input type="text" id="qo-customer" placeholder="예: ACME Corp" style="padding:8px;background:var(--bg-hover);color:var(--text);border:1px solid var(--border);border-radius:6px">',
      '    <label style="font-weight:600">사유 <span style="color:var(--text-muted);font-weight:400;font-size:.8rem">(선택)</span></label>',
      '    <input type="text" id="qo-reason" placeholder="" style="padding:8px;background:var(--bg-hover);color:var(--text);border:1px solid var(--border);border-radius:6px">',
      '    <label style="font-weight:600">작업자 <span style="color:var(--text-muted);font-weight:400;font-size:.8rem">(선택)</span></label>',
      '    <input type="text" id="qo-operator" placeholder="" style="padding:8px;background:var(--bg-hover);color:var(--text);border:1px solid var(--border);border-radius:6px">',
      '  </div>',
      '  <div id="qo-info" style="padding:10px;background:var(--bg-hover);border-radius:6px;font-size:.85rem;color:var(--text-muted);margin-bottom:12px;min-height:38px">',
      '    LOT 번호를 입력하면 가용 톤백 정보가 표시됩니다',
      '  </div>',
      '  <div id="qo-result" style="margin-bottom:12px"></div>',
      '  <div style="display:flex;gap:8px;justify-content:flex-end">',
      '    <button id="qo-cancel-btn" class="btn btn-ghost">닫기</button>',
      '    <button id="qo-submit-btn" class="btn btn-primary" disabled>출고 확정</button>',
      '  </div>',
      '</div>'
    ].join('\n');

    showDataModal('', html);

    var lotInput = document.getElementById('qo-lot');
    var countInput = document.getElementById('qo-customer');
    var cntInput = document.getElementById('qo-count');
    var customerInput = document.getElementById('qo-customer');
    var reasonInput = document.getElementById('qo-reason');
    var operatorInput = document.getElementById('qo-operator');
    var infoBox  = document.getElementById('qo-info');
    var resultBox = document.getElementById('qo-result');
    var submitBtn = document.getElementById('qo-submit-btn');
    var cancelBtn = document.getElementById('qo-cancel-btn');

    function validate() {
      var ok = !!(lotInput.value.trim() && customerInput.value.trim() && parseInt(cntInput.value, 10) > 0);
      submitBtn.disabled = !ok;
    }

    var _lotDebounce = null;
    function fetchLotInfo() {
      var lot = lotInput.value.trim();
      if (!lot) {
        infoBox.innerHTML = 'LOT 번호를 입력하면 가용 톤백 정보가 표시됩니다';
        infoBox.style.borderLeft = 'none';
        return;
      }
      infoBox.innerHTML = '⏳ 조회 중...';
      infoBox.style.borderLeft = 'none';
      apiGet('/api/outbound/quick/info?lot_no=' + encodeURIComponent(lot))
        .then(function(res) {
          if (!res || !res.ok) {
            infoBox.innerHTML = '❌ 조회 실패';
            return;
          }
          var d = res.data || {};
          var color = d.available_count > 0 ? 'var(--success)' : 'var(--warning)';
          infoBox.innerHTML =
            '<span style="color:' + color + ';font-weight:600">LOT ' + escapeHtml(lot) + '</span> · ' +
            '가용 톤백 <strong>' + d.available_count + '개</strong> (' + (d.total_weight_mt||0).toFixed(3) + ' MT) · ' +
            '최대 ' + d.max_count + '개';
          infoBox.style.borderLeft = '4px solid ' + color;
          infoBox.style.paddingLeft = '10px';
          // 톤백 수 max 조정
          cntInput.max = Math.min(d.available_count, d.max_count);
          if (parseInt(cntInput.value, 10) > cntInput.max) cntInput.value = cntInput.max;
        })
        .catch(function(e) {
          infoBox.innerHTML = '❌ 조회 실패: ' + escapeHtml(e.message || String(e));
        });
    }

    lotInput.addEventListener('input', function() {
      validate();
      if (_lotDebounce) clearTimeout(_lotDebounce);
      _lotDebounce = setTimeout(fetchLotInfo, 400);
    });
    cntInput.addEventListener('input', validate);
    customerInput.addEventListener('input', validate);

    cancelBtn.addEventListener('click', function() {
      document.getElementById('sqm-modal').style.display = 'none';
    });

    submitBtn.addEventListener('click', function() {
      var payload = {
        lot_no: lotInput.value.trim(),
        count: parseInt(cntInput.value, 10),
        customer: customerInput.value.trim(),
        reason: reasonInput.value.trim(),
        operator: operatorInput.value.trim(),
      };
      if (!confirm('LOT ' + payload.lot_no + ' 에서 ' + payload.count + '개 톤백을 ' + payload.customer + ' 로 출고하시겠습니까?')) return;

      submitBtn.disabled = true;
      cancelBtn.disabled = true;
      resultBox.innerHTML = '<div style="padding:8px;color:var(--text-muted)">⏳ 출고 처리 중...</div>';

      apiPost('/api/outbound/quick', payload)
        .then(function(res) {
          if (res && res.ok) {
            var d = res.data || {};
            resultBox.innerHTML =
              '<div style="padding:12px;background:var(--bg-hover);border-radius:6px;border-left:4px solid var(--success)">' +
              '<div style="font-weight:600;margin-bottom:4px">✅ ' + escapeHtml(res.message||'출고 완료') + '</div>' +
              '<div style="color:var(--text-muted);font-size:.85rem">LOT ' + escapeHtml(d.lot_no||'-') + ' · ' + (d.picked_count||0) + '개 톤백 · ' + (d.total_weight_mt||0).toFixed(3) + ' MT · ' + escapeHtml(d.customer||'-') + '</div>' +
              '</div>';
            showToast('success', res.message || '출고 완료');
            dbgLog('🟢','QUICK-OUTBOUND OK', res.message, '#66bb6a');
            // refresh
            if (_currentRoute === 'inventory' && typeof loadInventoryPage === 'function') loadInventoryPage();
            if (typeof loadKpi === 'function') loadKpi();
          } else {
            var errs = (res && res.data && res.data.errors) || [];
            var errMsg = (res && (res.message || res.error)) || '출고 실패';
            resultBox.innerHTML =
              '<div style="padding:12px;background:var(--bg-hover);border-radius:6px;border-left:4px solid var(--danger)">' +
              '<div style="font-weight:600">❌ ' + escapeHtml(errMsg) + '</div>' +
              (errs.length ? '<ul style="margin:8px 0 0 18px;color:var(--text-muted);font-size:.85rem">' + errs.map(function(e){return '<li>'+escapeHtml(e)+'</li>';}).join('') + '</ul>' : '') +
              '</div>';
            showToast('error', errMsg);
            dbgLog('🔴','QUICK-OUTBOUND FAIL', errMsg, '#ef5350');
            submitBtn.disabled = false;
            cancelBtn.disabled = false;
          }
        })
        .catch(function(e) {
          resultBox.innerHTML =
            '<div style="padding:12px;background:var(--bg-hover);border-radius:6px;border-left:4px solid var(--danger)">' +
            '<div style="font-weight:600">❌ 요청 실패</div>' +
            '<div style="color:var(--text-muted);font-size:.85rem;margin-top:4px">' + escapeHtml(e.message || String(e)) + '</div>' +
            '</div>';
          showToast('error', '출고 실패: ' + (e.message || String(e)));
          submitBtn.disabled = false;
          cancelBtn.disabled = false;
        });
    });
  }
  window.showQuickOutboundModal = showQuickOutboundModal;

  /* ===================================================
     8d. 톤백 위치 매핑 (F004) — Excel 업로드 공통 유틸 재사용
     =================================================== */
  function showTonbagLocationUploadModal() {
    _showExcelUploadModal({
      title: '📍 톤백 위치 매핑 — Excel 업로드',
      subtitle: 'Excel 컬럼: <code>lot_no, sub_lt, location, reason(선택), note(선택)</code>',
      endpoint: '/api/tonbag/location-upload',
      onSuccess: function(d) {
        var errHtml = '';
        if (d.errors && d.errors.length) {
          errHtml = '<details style="margin-top:8px"><summary style="cursor:pointer;color:var(--warning)">⚠️ ' + d.errors.length + '건 실패 상세</summary><table class="data-table" style="margin-top:8px;font-size:.85rem"><thead><tr><th>행</th><th>LOT</th><th>sub_lt</th><th>사유</th></tr></thead><tbody>' +
            d.errors.map(function(er){
              return '<tr><td>'+er.row+'</td><td>'+escapeHtml(er.lot_no||'-')+'</td><td>'+(er.sub_lt||'-')+'</td><td>'+escapeHtml(er.reason||'')+'</td></tr>';
            }).join('') + '</tbody></table></details>';
        }
        return '<div style="color:var(--text-muted);font-size:.85rem">파일: ' + escapeHtml(d.filename||'-') +
               ' · 성공 <strong style="color:var(--accent)">' + (d.success_count||0) + '건</strong> / 실패 ' + (d.fail_count||0) +
               ' / 총 ' + (d.total||0) + '</div>' + errHtml;
      }
    });
  }
  window.showTonbagLocationUploadModal = showTonbagLocationUploadModal;

  /* ===================================================
     8e. D/O 후속 연결 (F003) — 단건 필드 업데이트 폼
     =================================================== */
  function showDoUpdateModal() {
    var ALLOWED_FIELDS = [
      ['free_time',         'Free Time'],
      ['con_return',        'Container Return 일자'],
      ['warehouse_name',    '창고명'],
      ['warehouse_code',    '창고 코드'],
      ['arrival_date',      '도착일'],
      ['stock_date',        '입고일'],
      ['place_of_delivery', 'Place of Delivery'],
      ['final_destination', 'Final Destination'],
    ];
    var fieldOpts = ALLOWED_FIELDS.map(function(f){
      return '<option value="' + f[0] + '">' + f[1] + ' (' + f[0] + ')</option>';
    }).join('');

    var html = [
      '<div style="max-width:520px">',
      '  <h2 style="margin:0 0 12px 0">📋 D/O 후속 연결</h2>',
      '  <p style="color:var(--text-muted);margin:0 0 16px 0;font-size:.9rem">',
      '    특정 LOT 의 D/O 필드 값을 수정합니다.',
      '  </p>',
      '  <div style="display:grid;grid-template-columns:110px 1fr;gap:10px;align-items:center;margin-bottom:14px">',
      '    <label style="font-weight:600">LOT 번호</label>',
      '    <input type="text" id="do-lot" placeholder="예: 1126013063" style="padding:8px;background:var(--bg-hover);color:var(--text);border:1px solid var(--border);border-radius:6px;font-family:monospace">',
      '    <label style="font-weight:600">필드</label>',
      '    <select id="do-field" style="padding:8px;background:var(--bg-hover);color:var(--text);border:1px solid var(--border);border-radius:6px">' + fieldOpts + '</select>',
      '    <label style="font-weight:600">값</label>',
      '    <input type="text" id="do-value" placeholder="" style="padding:8px;background:var(--bg-hover);color:var(--text);border:1px solid var(--border);border-radius:6px">',
      '  </div>',
      '  <div id="do-result" style="margin-bottom:12px"></div>',
      '  <div style="display:flex;gap:8px;justify-content:flex-end">',
      '    <button id="do-cancel-btn" class="btn btn-ghost">닫기</button>',
      '    <button id="do-submit-btn" class="btn btn-primary" disabled>업데이트</button>',
      '  </div>',
      '</div>'
    ].join('\n');
    showDataModal('', html);

    var lot = document.getElementById('do-lot');
    var fld = document.getElementById('do-field');
    var val = document.getElementById('do-value');
    var result = document.getElementById('do-result');
    var submit = document.getElementById('do-submit-btn');
    var cancel = document.getElementById('do-cancel-btn');

    function validate() { submit.disabled = !(lot.value.trim() && fld.value && val.value !== ''); }
    lot.addEventListener('input', validate); val.addEventListener('input', validate); fld.addEventListener('change', validate);

    cancel.addEventListener('click', function(){ document.getElementById('sqm-modal').style.display='none'; });
    submit.addEventListener('click', function(){
      var payload = { lot_no: lot.value.trim(), field: fld.value, value: val.value };
      submit.disabled = true; cancel.disabled = true;
      result.innerHTML = '<div style="padding:8px;color:var(--text-muted)">⏳ 업데이트 중...</div>';
      apiPost('/api/action3/do-update', payload)
        .then(function(res){
          if (res && res.ok !== false) {
            result.innerHTML = '<div style="padding:12px;background:var(--bg-hover);border-radius:6px;border-left:4px solid var(--success)"><div style="font-weight:600">✅ ' + escapeHtml((res.data && res.data.message) || '업데이트 완료') + '</div></div>';
            showToast('success', 'D/O 업데이트 완료');
            dbgLog('🟢','DO-UPDATE OK', payload.lot_no + ' · ' + payload.field, '#66bb6a');
            if (_currentRoute === 'inventory' && typeof loadInventoryPage === 'function') loadInventoryPage();
          } else {
            var msg = (res && (res.error || res.message)) || '실패';
            result.innerHTML = '<div style="padding:12px;background:var(--bg-hover);border-radius:6px;border-left:4px solid var(--danger)"><div style="font-weight:600">❌ ' + escapeHtml(msg) + '</div></div>';
            showToast('error', msg);
            submit.disabled = false; cancel.disabled = false;
          }
        })
        .catch(function(e){
          result.innerHTML = '<div style="padding:12px;color:var(--danger)">❌ ' + escapeHtml(e.message||String(e)) + '</div>';
          showToast('error', '실패: ' + (e.message||String(e)));
          submit.disabled = false; cancel.disabled = false;
        });
    });
  }
  window.showDoUpdateModal = showDoUpdateModal;

  /* ===================================================
     8f. 예약 반영 (승인분) — F022 (단순 확정 모달)
     =================================================== */
  function showApplyApprovedAllocationModal() {
    var html = [
      '<div style="max-width:480px">',
      '  <h2 style="margin:0 0 12px 0">📌 예약 반영 — 승인분 실행</h2>',
      '  <p style="color:var(--text-muted);margin:0 0 16px 0;font-size:.9rem">',
      '    workflow_status = APPROVED 인 Allocation 계획을 톤백 RESERVED 로 실제 반영합니다.',
      '  </p>',
      '  <div id="aa-result" style="margin-bottom:12px;min-height:24px"></div>',
      '  <div style="display:flex;gap:8px;justify-content:flex-end">',
      '    <button id="aa-cancel-btn" class="btn btn-ghost">닫기</button>',
      '    <button id="aa-submit-btn" class="btn btn-primary">지금 반영</button>',
      '  </div>',
      '</div>'
    ].join('\n');
    showDataModal('', html);

    var cancel = document.getElementById('aa-cancel-btn');
    var submit = document.getElementById('aa-submit-btn');
    var result = document.getElementById('aa-result');
    cancel.addEventListener('click', function(){ document.getElementById('sqm-modal').style.display='none'; });
    submit.addEventListener('click', function(){
      if (!confirm('승인 완료된 Allocation 을 모두 RESERVED 로 반영합니다. 계속할까요?')) return;
      submit.disabled = true; cancel.disabled = true;
      result.innerHTML = '<div style="padding:8px;color:var(--text-muted)">⏳ 처리 중...</div>';
      apiPost('/api/allocation/apply-approved', {})
        .then(function(res){
          if (res && res.ok) {
            var d = res.data || {};
            result.innerHTML = '<div style="padding:12px;background:var(--bg-hover);border-radius:6px;border-left:4px solid var(--success)"><div style="font-weight:600">✅ ' + escapeHtml(res.message||'완료') + '</div><div style="color:var(--text-muted);font-size:.85rem;margin-top:4px">반영 건수: <strong>' + (d.applied||0) + '</strong></div></div>';
            showToast('success', res.message || '반영 완료');
          } else {
            var errs = (res && res.data && res.data.errors) || [];
            var msg = (res && (res.message || res.error)) || '실패';
            result.innerHTML = '<div style="padding:12px;background:var(--bg-hover);border-radius:6px;border-left:4px solid var(--danger)"><div style="font-weight:600">❌ ' + escapeHtml(msg) + '</div>' + (errs.length ? '<ul style="margin:8px 0 0 18px;color:var(--text-muted);font-size:.85rem">' + errs.map(function(e){return '<li>'+escapeHtml(e)+'</li>';}).join('') + '</ul>' : '') + '</div>';
            showToast('error', msg);
            submit.disabled = false; cancel.disabled = false;
          }
        })
        .catch(function(e){
          result.innerHTML = '<div style="padding:12px;color:var(--danger)">❌ ' + escapeHtml(e.message||String(e)) + '</div>';
          showToast('error', e.message || String(e));
          submit.disabled = false; cancel.disabled = false;
        });
    });
  }
  window.showApplyApprovedAllocationModal = showApplyApprovedAllocationModal;

  /* ===================================================
     8g. 공통 PDF 업로드 모달 (F001, F017 공용)
     =================================================== */
  function _showPdfUploadModal(opts) {
    // opts: {title, subtitle, endpoint, onSuccess(data) → HTML}
    var html = [
      '<div style="max-width:640px">',
      '  <h2 style="margin:0 0 12px 0">' + escapeHtml(opts.title) + '</h2>',
      '  <p style="color:var(--text-muted);margin:0 0 16px 0;font-size:.9rem">',
      '    ' + opts.subtitle,
      '  </p>',
      '  <div id="pdf-drop2-zone" style="border:2px dashed var(--border);border-radius:8px;padding:32px 16px;text-align:center;background:var(--bg-hover);cursor:pointer;margin-bottom:16px">',
      '    <div style="font-size:2.5rem;margin-bottom:8px">📄</div>',
      '    <div id="pdf-drop2-name" style="color:var(--text-muted)">클릭 또는 PDF 파일을 여기에 드롭하세요</div>',
      '  </div>',
      '  <input type="file" id="pdf-drop2-input" accept=".pdf" style="display:none">',
      '  <div id="pdf-drop2-progress" style="display:none;margin-bottom:16px">',
      '    <div style="background:var(--bg-hover);border-radius:4px;height:8px;overflow:hidden">',
      '      <div id="pdf-drop2-bar" style="background:var(--accent);height:100%;width:0%;transition:width .3s"></div>',
      '    </div>',
      '    <div id="pdf-drop2-text" style="font-size:.85rem;color:var(--text-muted);margin-top:4px">준비 중...</div>',
      '  </div>',
      '  <div id="pdf-drop2-result" style="margin-bottom:16px"></div>',
      '  <div style="display:flex;gap:8px;justify-content:flex-end">',
      '    <button id="pdf-drop2-cancel" class="btn btn-ghost">닫기</button>',
      '    <button id="pdf-drop2-upload" class="btn btn-primary" disabled>업로드</button>',
      '  </div>',
      '</div>'
    ].join('\n');
    showDataModal('', html);

    var dz = document.getElementById('pdf-drop2-zone');
    var fi = document.getElementById('pdf-drop2-input');
    var nm = document.getElementById('pdf-drop2-name');
    var ub = document.getElementById('pdf-drop2-upload');
    var cb = document.getElementById('pdf-drop2-cancel');
    var pg = document.getElementById('pdf-drop2-progress');
    var bar = document.getElementById('pdf-drop2-bar');
    var tx = document.getElementById('pdf-drop2-text');
    var rb = document.getElementById('pdf-drop2-result');
    var f = null;

    function setFile(x) {
      if (!x) return;
      if (!/\.pdf$/i.test(x.name)) { showToast('error', 'PDF 파일만 가능: ' + x.name); return; }
      f = x;
      nm.innerHTML = '✅ <strong>' + escapeHtml(x.name) + '</strong> (' + Math.round(x.size/1024) + ' KB)';
      ub.disabled = false;
    }
    dz.addEventListener('click', function(){ fi.click(); });
    fi.addEventListener('change', function(e){ if (e.target.files && e.target.files[0]) setFile(e.target.files[0]); });
    dz.addEventListener('dragover', function(e){ e.preventDefault(); dz.style.background='var(--bg-active)'; });
    dz.addEventListener('dragleave', function(){ dz.style.background='var(--bg-hover)'; });
    dz.addEventListener('drop', function(e){ e.preventDefault(); dz.style.background='var(--bg-hover)'; if (e.dataTransfer.files && e.dataTransfer.files[0]) setFile(e.dataTransfer.files[0]); });
    cb.addEventListener('click', function(){ document.getElementById('sqm-modal').style.display='none'; });

    ub.addEventListener('click', function(){
      if (!f) return;
      ub.disabled = true; cb.disabled = true;
      pg.style.display = 'block'; bar.style.width = '10%'; tx.textContent = '업로드 중...';
      rb.innerHTML = '';

      var form = new FormData();
      form.append('file', f, f.name);
      var xhr = new XMLHttpRequest();
      xhr.open('POST', API + opts.endpoint);
      xhr.upload.onprogress = function(e){
        if (e.lengthComputable) {
          var pct = Math.round((e.loaded/e.total)*70)+10;
          bar.style.width = pct+'%'; tx.textContent = '업로드 중... '+pct+'%';
        }
      };
      xhr.onload = function(){
        bar.style.width='100%'; cb.disabled = false;
        var body; try { body = JSON.parse(xhr.responseText); } catch(e){ body = null; }
        if (xhr.status >= 200 && xhr.status < 300 && body && body.ok) {
          tx.textContent = body.message || '완료';
          var extra = opts.onSuccess ? opts.onSuccess(body.data||{}) : '';
          rb.innerHTML = '<div style="padding:12px;background:var(--bg-hover);border-radius:6px;border-left:4px solid var(--success)"><div style="font-weight:600;margin-bottom:4px">✅ '+escapeHtml(body.message||'완료')+'</div>'+(extra||'')+'</div>';
          showToast('success', body.message || '완료');
          dbgLog('🟢','PDF-UPLOAD OK', opts.endpoint, '#66bb6a');
          if (_currentRoute === 'inventory' && typeof loadInventoryPage === 'function') loadInventoryPage();
          if (typeof loadKpi === 'function') loadKpi();
        } else {
          var errMsg = (body && (body.detail || body.error || body.message)) || ('HTTP '+xhr.status);
          if (typeof errMsg === 'object') errMsg = JSON.stringify(errMsg);
          tx.textContent = '실패'; bar.style.background = 'var(--danger)';
          var errExtra = '';
          if (body && body.data && body.data.errors) {
            errExtra = '<details style="margin-top:8px"><summary style="cursor:pointer;color:var(--warning)">⚠️ 상세</summary><pre style="white-space:pre-wrap;font-size:.8rem;margin-top:8px;max-height:240px;overflow:auto">'+escapeHtml(JSON.stringify(body.data.errors, null, 2))+'</pre></details>';
          }
          rb.innerHTML = '<div style="padding:12px;background:var(--bg-hover);border-radius:6px;border-left:4px solid var(--danger)"><div style="font-weight:600">❌ 실패</div><div style="color:var(--text-muted);font-size:.85rem;margin-top:4px">'+escapeHtml(String(errMsg))+'</div>'+errExtra+'</div>';
          showToast('error', '실패: '+errMsg);
          ub.disabled = false;
        }
      };
      xhr.onerror = function(){
        tx.textContent = '네트워크 에러'; bar.style.background = 'var(--danger)';
        rb.innerHTML = '<div style="padding:12px;color:var(--danger)">네트워크 에러</div>';
        showToast('error', '네트워크 에러');
        ub.disabled = false; cb.disabled = false;
      };
      xhr.send(form);
    });
  }

  /* F001 PDF 스캔 입고 (Packing List) — 레거시 단일 PDF 업로드 (Sprint 1-2 이후 showOneStopInboundModal로 대체) */
  function showPdfInboundUploadModal() {
    _showPdfUploadModal({
      title: '📄 PDF 스캔 입고 (Packing List)',
      subtitle: 'Packing List PDF 파일을 선택하세요. 자동 파싱 후 재고에 등록합니다.',
      endpoint: '/api/inbound/pdf-upload',
      onSuccess: function(d) {
        var errHtml = '';
        if (d.errors && d.errors.length) {
          errHtml = '<details style="margin-top:8px"><summary style="cursor:pointer;color:var(--warning)">⚠️ 실패 ' + d.errors.length + '건</summary><pre style="white-space:pre-wrap;font-size:.8rem;margin-top:8px;max-height:200px;overflow:auto">' + escapeHtml(JSON.stringify(d.errors, null, 2)) + '</pre></details>';
        }
        return '<div style="color:var(--text-muted);font-size:.85rem">파일: ' + escapeHtml(d.filename||'-') +
               ' · Folio: ' + escapeHtml(d.folio||'-') +
               ' · 제품: ' + escapeHtml(d.product||'-') +
               ' · LOT 총 ' + (d.lots_total||0) + '개' +
               ' · <strong style="color:var(--accent)">저장 ' + (d.saved_count||0) + '건</strong>' +
               '</div>' + errHtml;
      }
    });
  }
  window.showPdfInboundUploadModal = showPdfInboundUploadModal;

  /* =====================================================================
     [Sprint 1-2-A] OneStop Inbound — 4슬롯 wizard 모달
     ─────────────────────────────────────────────────────────────────────
     v864-2 source : gui_app_modular/dialogs/onestop_inbound.py (4302줄)
     v864-2 DOC_TYPES: [BL 필수, PACKING_LIST 필수, INVOICE 필수, DO 선택]

     이 Phase(A)에서 구현:
       ✅ 4단계 Wizard 스텝 표시
       ✅ 템플릿/선사 Combobox (placeholder — Sprint 2에서 CRUD 연결)
       ✅ 4 업로드 슬롯 (BL/PL/Invoice/DO) + 파일 선택 + 상태 표시
       ✅ 파싱 시작 / 다시 파싱 / 멀티 선택 / D/O 나중에 버튼
       ✅ 진행 상태 영역
       ✅ 필터 바 + 18열 미리보기 테이블 (뼈대)
       ✅ BL PDF 1장만 기존 /api/inbound/pdf-upload 로 파싱 (fallback)

     다음 Phase(B)에서 추가:
       🟡 백엔드 /api/inbound/onestop-upload (4종 multipart)
       🟡 4종 크로스체크 검증 (5 weight 소수 일치 등)
       🟡 18열 실데이터 미리보기
       🟡 인라인 편집 + Undo/Redo + 서브팝업 4개
     ===================================================================== */
  var _onestopState = {
    files: { BL: null, PACKING_LIST: null, INVOICE: null, DO: null },
    template: null,
    carrier: '',
    step: 1,
    /* [Sprint 1-2-C] 편집 상태 */
    previewRows: [],        /* 현재 미리보기 rows (편집 반영됨) */
    originalRows: [],       /* 원본 백업 — 편집 롤백용 */
    editedCells: {},        /* { "rowIdx.field": true } — 편집된 셀 표시용 */
    parsed: false,          /* 파싱 완료 여부 (true면 DB 업로드 가능) */
    /* [Sprint 1-2-D] Undo/Redo + D/O 수동 정보 */
    history: [],            /* [{rowIdx, field, oldVal, newVal}, ...] max 50 */
    historyIdx: -1,         /* 현재 위치 (stack pointer) */
    manualDo: null,         /* D/O 미첨부 시 수동 입력 정보 {free_time, warehouse, arrival_date} */
  };
  var ONESTOP_MAX_HISTORY = 50;
  /* [Sprint 1-2-C] 편집 가능 컬럼 (18열 중 — v864-2 EDITABLE_COLS 참고) */
  var ONESTOP_EDITABLE_FIELDS = new Set([
    'lot_no', 'sap_no', 'bl_no', 'product', 'container', 'code',
    'lot_sqm', 'mxbg', 'net_kg', 'gross_kg',
    'invoice_no', 'ship_date', 'arrival', 'con_return', 'free_time', 'wh'
  ]);
  /* 읽기 전용: no (순번), status (NEW 고정) */
  var ONESTOP_DOC_TYPES = [
    { key: 'BL',           icon: '🚢', seq: '①', name: 'Bill of Loading',  required: true  },
    { key: 'PACKING_LIST', icon: '📦', seq: '②', name: 'Packing List',     required: true  },
    { key: 'INVOICE',      icon: '📄', seq: '③', name: 'Invoice, FA',      required: true  },
    { key: 'DO',           icon: '📋', seq: '④', name: 'Delivery Order',   required: false },
  ];
  var ONESTOP_PREVIEW_COLS = [
    'NO','LOT NO','SAP NO','BL NO','PRODUCT','STATUS','CONTAINER','CODE',
    'LOT SQM','MXBG','NET(Kg)','GROSS(kg)','INVOICE NO','SHIP DATE','ARRIVAL',
    'CON RETURN','FREE TIME','WH'
  ];

  function showOneStopInboundModal() {
    /* 상태 초기화 */
    _onestopState.files = { BL: null, PACKING_LIST: null, INVOICE: null, DO: null };
    _onestopState.step = 1;

    var slotsHtml = ONESTOP_DOC_TYPES.map(function(dt){
      return (
        '<div class="upload-slot" id="onestop-slot-' + dt.key + '">' +
          '<div class="upload-slot-icon">' + dt.icon + '</div>' +
          '<div class="upload-slot-label">' + dt.seq + ' ' + escapeHtml(dt.name) +
            ' <span class="upload-slot-req ' + (dt.required ? 'required' : 'optional') + '">' +
            (dt.required ? '필수' : '선택') + '</span>' +
            '<small class="upload-slot-filename" id="onestop-filename-' + dt.key + '"></small>' +
          '</div>' +
          '<button class="upload-slot-pick-btn" onclick="window.onestopPickFile(\'' + dt.key + '\')">📂 파일 선택</button>' +
          '<input type="file" id="onestop-input-' + dt.key + '" accept=".pdf" style="display:none" onchange="window.onestopOnFileChange(\'' + dt.key + '\', this)">' +
          '<span class="upload-slot-status" id="onestop-status-' + dt.key + '">○</span>' +
        '</div>'
      );
    }).join('');

    var filterHtml = ['SAP','BL','CONTAINER','PRODUCT','STATUS'].map(function(f){
      return '<label>' + f + ':</label><input type="text" id="onestop-filter-' + f.toLowerCase() + '" placeholder=" ">';
    }).join('');

    var previewHeader = ONESTOP_PREVIEW_COLS.map(function(c){ return '<th>' + c + '</th>'; }).join('');

    var html = [
      '<div class="onestop-modal">',
      '  <h2>📥 입고 — SQM v8.6.4.3 (OneStop)</h2>',
      /* 4단계 Wizard */
      '  <div class="wizard-steps">',
      '    <div class="step active" data-step="1"><span class="step-num">①</span><span class="step-label">서류 선택<small>파일 업로드</small></span></div>',
      '    <div class="step-arrow">›</div>',
      '    <div class="step" data-step="2"><span class="step-num">②</span><span class="step-label">파싱 실행<small>AI 분석</small></span></div>',
      '    <div class="step-arrow">›</div>',
      '    <div class="step" data-step="3"><span class="step-num">③</span><span class="step-label">결과 확인<small>미리보기</small></span></div>',
      '    <div class="step-arrow">›</div>',
      '    <div class="step" data-step="4"><span class="step-num">④</span><span class="step-label">DB 저장<small>입고 완료</small></span></div>',
      '  </div>',
      /* 템플릿 줄 */
      '  <div class="onestop-row">',
      '    <label>적용 템플릿:</label>',
      '    <select id="onestop-template" disabled><option>MAERSK — 리튬카보네이트 500 kg (500kg BL:숫자9)</option></select>',
      '    <span class="chip">Sprint 2 예정</span>',
      '    <button class="btn" style="margin-left:auto" onclick="window.onestopSkipDo()">📋 D/O 나중에</button>',
      '  </div>',
      /* 선사 줄 */
      '  <div class="onestop-row">',
      '    <label>🚢 선사:</label>',
      '    <input type="text" id="onestop-carrier" placeholder="Maersk / ONE / Evergreen ...">',
      '    <span class="chip">[선사: Maersk] (템플릿)</span>',
      '    <button class="btn" onclick="window.onestopReparseCarrier()" disabled>🚢 선사 재파싱</button>',
      '  </div>',
      /* 4 업로드 슬롯 */
      '  <div class="upload-slots">' + slotsHtml + '</div>',
      /* 액션 버튼 */
      '  <div class="onestop-actions">',
      '    <button class="btn" onclick="window.onestopMultiPick()">📁 멀티 선택</button>',
      '    <button class="btn btn-primary" id="onestop-parse-btn" onclick="window.onestopParseStart()" disabled>▶ 파싱 시작</button>',
      '    <button class="btn" id="onestop-reparse-btn" onclick="window.onestopParseRedo()" disabled>↻ 다시 파싱</button>',
      '    <span class="hint" id="onestop-hint">💡 최소 Packing List를 선택하세요</span>',
      '  </div>',
      /* 진행 상태 */
      '  <div class="onestop-progress">',
      '    <div class="onestop-progress-title">📊 진행 상태</div>',
      '    <div id="onestop-progress-body" class="onestop-progress-empty">파싱을 시작하면 진행 상황이 여기에 표시됩니다.</div>',
      '  </div>',
      /* [Sprint 1-2-D] 편집 툴바 (Undo/Redo + 템플릿 + 힌트) */
      '  <div class="onestop-edit-toolbar" style="display:flex;align-items:center;gap:6px;padding:6px 10px;background:var(--panel);border:1px solid var(--panel-border);border-radius:6px;margin-bottom:6px;flex-wrap:wrap">',
      '    <span style="font-weight:700;color:var(--text-muted);font-size:12px">✏️ 편집:</span>',
      '    <button class="btn" id="onestop-undo-btn" onclick="window.onestopUndo()" disabled title="되돌리기 (Ctrl+Z)">↶ 되돌리기</button>',
      '    <button class="btn" id="onestop-redo-btn" onclick="window.onestopRedo()" disabled title="다시 실행 (Ctrl+Y)">↷ 다시 실행</button>',
      '    <button class="btn" id="onestop-reset-btn" onclick="window.onestopResetAll()" disabled title="모든 편집 되돌림">⟲ 원본 초기화</button>',
      '    <span style="width:1px;height:20px;background:var(--panel-border);margin:0 2px"></span>',
      '    <button class="btn btn-wip" onclick="window.onestopTemplateSave()" title="Sprint 2 예정">📋 템플릿 저장</button>',
      '    <button class="btn btn-wip" onclick="window.onestopTemplateLoad()" title="Sprint 2 예정">📋 템플릿 선택</button>',
      '    <span class="hint" style="margin-left:auto;color:var(--text-muted);font-size:11px">셀 더블클릭 → Enter 저장 · Esc 취소</span>',
      '  </div>',
      /* 필터 바 */
      '  <div class="onestop-filter-bar">',
      '    <span style="font-weight:700">▼ 필터:</span>' + filterHtml,
      '    <button class="btn" onclick="window.onestopResetFilter()" style="margin-left:auto">✖ 초기화</button>',
      '  </div>',
      /* 미리보기 */
      '  <div style="overflow-x:auto;max-height:320px;overflow-y:auto">',
      '    <table class="onestop-preview-table"><thead><tr>' + previewHeader + '</tr></thead>',
      '      <tbody id="onestop-preview-body"><tr><td colspan="' + ONESTOP_PREVIEW_COLS.length + '" class="onestop-preview-empty">📭 파싱 결과가 없습니다. 파일 선택 후 ▶ 파싱 시작을 눌러주세요.</td></tr></tbody>',
      '    </table>',
      '  </div>',
      /* 하단 버튼 */
      '  <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:14px">',
      '    <button class="btn btn-ghost" onclick="document.getElementById(\'sqm-modal\').style.display=\'none\'">❌ 취소</button>',
      '    <button class="btn btn-primary" id="onestop-save-btn" onclick="window.onestopSaveDb()" disabled>📤 DB 업로드</button>',
      '  </div>',
      '</div>'
    ].join('\n');

    showDataModal('', html);
  }
  window.showOneStopInboundModal = showOneStopInboundModal;

  /* ── 슬롯 핸들러 ─────────────────────────────────────────────────── */
  window.onestopPickFile = function(docKey) {
    var input = document.getElementById('onestop-input-' + docKey);
    if (input) input.click();
  };
  window.onestopOnFileChange = function(docKey, inputEl) {
    if (!inputEl.files || !inputEl.files[0]) return;
    var f = inputEl.files[0];
    if (!/\.pdf$/i.test(f.name)) { showToast('error', 'PDF 파일만 가능: ' + f.name); return; }
    _onestopState.files[docKey] = f;
    var slot = document.getElementById('onestop-slot-' + docKey);
    var nameEl = document.getElementById('onestop-filename-' + docKey);
    var statusEl = document.getElementById('onestop-status-' + docKey);
    if (slot) slot.classList.add('filled');
    if (nameEl) nameEl.textContent = f.name + ' (' + Math.round(f.size/1024) + ' KB)';
    if (statusEl) statusEl.textContent = '✓';
    _onestopUpdateEnableState();
  };
  function _onestopUpdateEnableState() {
    var s = _onestopState.files;
    /* 최소 Packing List 필수 */
    var canParse = !!s.PACKING_LIST;
    var parseBtn = document.getElementById('onestop-parse-btn');
    var hint = document.getElementById('onestop-hint');
    if (parseBtn) parseBtn.disabled = !canParse;
    if (hint) {
      if (!s.PACKING_LIST) hint.textContent = '💡 최소 Packing List(PL)를 선택하세요';
      else if (!s.BL || !s.INVOICE) hint.textContent = '⚠️ BL/Invoice 없음 — 크로스체크 제한 (파싱은 가능)';
      else if (!s.DO) hint.textContent = 'ℹ️ D/O 선택 — 나중에 첨부 가능';
      else hint.textContent = '✅ 4종 준비 완료 — 크로스체크 실행 가능';
    }
  }
  window.onestopMultiPick = function() {
    showToast('info', '멀티 선택은 Sprint 2에서 자동 분류와 함께 구현됩니다 (임시: 각 슬롯 개별 선택)');
  };

  /* [Sprint 1-2-D] D/O 나중에 — 수동 정보 입력 프롬프트 체인 */
  window.onestopSkipDo = function() {
    var cur = _onestopState.manualDo || {};
    var ft = prompt('📋 D/O 수동 입력 (1/3) — Free Time (일수)\n\n예: 7\n(취소 → 전체 입력 취소)', cur.free_time || '');
    if (ft === null) return;
    ft = String(ft || '').trim();
    var wh = prompt('📋 D/O 수동 입력 (2/3) — 창고명\n\n예: 광양창고\n(빈값 허용)', cur.warehouse || '');
    if (wh === null) return;
    wh = String(wh || '').trim();
    var ar = prompt('📋 D/O 수동 입력 (3/3) — 도착일 (YYYY-MM-DD)\n\n예: 2026-04-20\n(빈값 허용)', cur.arrival_date || '');
    if (ar === null) return;
    ar = String(ar || '').trim();
    /* 도착일 형식 검증 (빈값 OK, 입력된 경우 YYYY-MM-DD) */
    if (ar && !/^\d{4}-\d{2}-\d{2}$/.test(ar)) {
      if (!confirm('도착일 형식이 YYYY-MM-DD가 아닙니다: "' + ar + '"\n그래도 저장하시겠습니까?')) return;
    }
    _onestopState.manualDo = { free_time: ft, warehouse: wh, arrival_date: ar };
    /* 파싱된 rows 가 있으면 DO 누락 필드에 수동 값 채우기 */
    if (_onestopState.parsed && _onestopState.previewRows.length) {
      _onestopState.previewRows.forEach(function(r, i){
        if (!r) return;
        if (ft && !r.free_time)  { r.free_time = ft;  _onestopState.editedCells[i + '.free_time'] = true; }
        if (wh && !r.wh)          { r.wh = wh;         _onestopState.editedCells[i + '.wh'] = true; }
        if (ar && !r.arrival)     { r.arrival = ar;    _onestopState.editedCells[i + '.arrival'] = true; }
      });
      _onestopRenderPreview(_onestopState.previewRows);
    }
    showToast('success',
      'D/O 수동 정보 저장됨 — Free Time=' + (ft || '-') +
      ' / 창고=' + (wh || '-') +
      ' / 도착=' + (ar || '-') +
      (_onestopState.parsed ? ' · 미리보기 반영됨' : ' (파싱 후 적용)')
    );
  };

  window.onestopReparseCarrier = function() {
    showToast('info', '선사 재파싱은 Sprint 2 (선사별 템플릿 재적용) 이후 연결됩니다');
  };

  /* [Sprint 1-2-D] Undo / Redo — 편집 이력 50-stack */
  window.onestopUndo = function() {
    if (_onestopState.historyIdx < 0) { showToast('info', '되돌릴 작업이 없습니다'); return; }
    var entry = _onestopState.history[_onestopState.historyIdx];
    if (!_onestopState.previewRows[entry.rowIdx]) _onestopState.previewRows[entry.rowIdx] = {};
    _onestopState.previewRows[entry.rowIdx][entry.field] = entry.oldVal;
    /* editedCells 재계산 */
    var origVal = (_onestopState.originalRows[entry.rowIdx] || {})[entry.field];
    var cellKey = entry.rowIdx + '.' + entry.field;
    if (String(entry.oldVal) !== String(origVal == null ? '' : origVal)) {
      _onestopState.editedCells[cellKey] = true;
    } else {
      delete _onestopState.editedCells[cellKey];
    }
    _onestopState.historyIdx--;
    _onestopRenderPreview(_onestopState.previewRows);
    _onestopUpdateHistoryButtons();
    showToast('info', '↶ 되돌림: ' + entry.field + ' · row ' + (entry.rowIdx + 1));
  };

  window.onestopRedo = function() {
    if (_onestopState.historyIdx >= _onestopState.history.length - 1) {
      showToast('info', '다시 실행할 작업이 없습니다');
      return;
    }
    _onestopState.historyIdx++;
    var entry = _onestopState.history[_onestopState.historyIdx];
    if (!_onestopState.previewRows[entry.rowIdx]) _onestopState.previewRows[entry.rowIdx] = {};
    _onestopState.previewRows[entry.rowIdx][entry.field] = entry.newVal;
    var origVal = (_onestopState.originalRows[entry.rowIdx] || {})[entry.field];
    var cellKey = entry.rowIdx + '.' + entry.field;
    if (String(entry.newVal) !== String(origVal == null ? '' : origVal)) {
      _onestopState.editedCells[cellKey] = true;
    } else {
      delete _onestopState.editedCells[cellKey];
    }
    _onestopRenderPreview(_onestopState.previewRows);
    _onestopUpdateHistoryButtons();
    showToast('info', '↷ 다시 실행: ' + entry.field + ' · row ' + (entry.rowIdx + 1));
  };

  window.onestopResetAll = function() {
    if (!_onestopState.history.length) { showToast('info', '편집 내역이 없습니다'); return; }
    if (!confirm('⟲ 원본 초기화\n\n모든 편집 내용을 파싱 직후 상태로 되돌립니다. 계속하시겠습니까?')) return;
    _onestopState.previewRows = JSON.parse(JSON.stringify(_onestopState.originalRows));
    _onestopState.editedCells = {};
    _onestopState.history = [];
    _onestopState.historyIdx = -1;
    _onestopRenderPreview(_onestopState.previewRows);
    _onestopUpdateHistoryButtons();
    showToast('success', '원본 상태로 초기화되었습니다');
  };

  /* [Sprint 2-A] Inbound Template CRUD 연동 — 풀 다이얼로그 */
  window.onestopTemplateSave = function() {
    showInboundTemplateModal({ mode: 'create-from-current' });
  };
  window.onestopTemplateLoad = function() {
    showInboundTemplateModal({ mode: 'select' });
  };
  window.onestopParseErrorRecovery = function(docType, errorCode) {
    showToast('info', (docType || 'PDF') + ' 파싱 오류 복구 (9 ERROR_CODES): Sprint 2 (ParseErrorRecoveryDialog) 이후 활성화');
  };

  /* Undo/Redo 버튼 상태 갱신 */
  function _onestopUpdateHistoryButtons() {
    var undoBtn = document.getElementById('onestop-undo-btn');
    var redoBtn = document.getElementById('onestop-redo-btn');
    var resetBtn = document.getElementById('onestop-reset-btn');
    var canUndo = _onestopState.historyIdx >= 0;
    var canRedo = _onestopState.historyIdx < _onestopState.history.length - 1;
    var hasHistory = _onestopState.history.length > 0;
    if (undoBtn)  undoBtn.disabled  = !canUndo;
    if (redoBtn)  redoBtn.disabled  = !canRedo;
    if (resetBtn) resetBtn.disabled = !hasHistory;
    /* 카운터 표시 */
    if (undoBtn) undoBtn.title = '되돌리기 (Ctrl+Z) · 이력 ' + (_onestopState.historyIdx + 1) + '/' + _onestopState.history.length;
    if (redoBtn) redoBtn.title = '다시 실행 (Ctrl+Y) · ' + Math.max(0, _onestopState.history.length - _onestopState.historyIdx - 1) + '단계 남음';
  }
  window.onestopResetFilter = function() {
    ['sap','bl','container','product','status'].forEach(function(k){
      var el = document.getElementById('onestop-filter-' + k);
      if (el) el.value = '';
    });
  };

  /* ── 파싱 실행 (Sprint 1-2-B: /api/inbound/onestop-upload 4종 multipart + 크로스체크) ── */
  window.onestopParseStart = function() {
    var s = _onestopState.files;
    if (!s.PACKING_LIST) { showToast('error', 'Packing List(PL) 먼저 선택하세요'); return; }

    _onestopSetStep(2);
    var pb = document.getElementById('onestop-progress-body');
    if (pb) {
      var filesSummary = [];
      if (s.BL)           filesSummary.push('🚢 BL');
      if (s.PACKING_LIST) filesSummary.push('📦 PL');
      if (s.INVOICE)      filesSummary.push('📄 INV');
      if (s.DO)           filesSummary.push('📋 DO');
      pb.innerHTML = '<div style="padding:4px;color:var(--fg)">⏳ 파싱 + 크로스체크 진행 중... <strong>' + filesSummary.join(' · ') + '</strong></div>';
    }

    var form = new FormData();
    /* FastAPI: pl 필수, bl/invoice/do_file 선택 */
    form.append('pl', s.PACKING_LIST, s.PACKING_LIST.name);
    if (s.BL)      form.append('bl',      s.BL,      s.BL.name);
    if (s.INVOICE) form.append('invoice', s.INVOICE, s.INVOICE.name);
    if (s.DO)      form.append('do_file', s.DO,      s.DO.name);

    var xhr = new XMLHttpRequest();
    /* [Sprint 1-2-C] dry_run=true 로 DB 저장 없이 파싱만 실행 */
    xhr.open('POST', API + '/api/inbound/onestop-upload?dry_run=true');
    xhr.onload = function(){
      var body; try { body = JSON.parse(xhr.responseText); } catch(e){ body = null; }
      if (xhr.status >= 200 && xhr.status < 300 && body && body.ok) {
        var d = body.data || {};
        var xc = d.cross_check || {};
        var docs = d.parsed_docs || {};

        /* 진행 상태 패널 업데이트 */
        var xcColor = xc.has_critical ? 'var(--danger)' : (xc.warning > 0 ? 'var(--warning)' : 'var(--success)');
        var xcIcon = xc.has_critical ? '🚫' : (xc.warning > 0 ? '⚠️' : '✅');
        var docsBadges = [
          (docs.bl_loaded      ? '🚢 BL ✓'  : '🚢 BL ✗'),
          (docs.pl_loaded      ? '📦 PL ✓'  : '📦 PL ✗'),
          (docs.invoice_loaded ? '📄 INV ✓' : '📄 INV ✗'),
          (docs.do_loaded      ? '📋 DO ✓'  : '📋 DO ✗'),
        ].join('  ');

        var xcItemsHtml = '';
        if (xc.items && xc.items.length) {
          xcItemsHtml = '<details style="margin-top:8px"><summary style="cursor:pointer;font-size:12px;color:var(--text-muted)">⚠️ ' + xc.items.length + '건 상세</summary>' +
            '<ul style="font-size:11px;margin:6px 0 0 20px;padding:0">' +
            xc.items.map(function(it){
              var lc = it.level === 3 ? 'var(--danger)' : (it.level === 2 ? 'var(--warning)' : 'var(--text-muted)');
              return '<li style="color:' + lc + ';margin-bottom:2px">' + escapeHtml(it.icon) + ' <strong>[' + escapeHtml(it.field) + ']</strong> ' + escapeHtml(it.message) + '</li>';
            }).join('') +
            '</ul></details>';
        }

        if (pb) pb.innerHTML =
          '<div style="color:var(--success);font-weight:700">✅ ' + escapeHtml(body.message || '파싱 완료') + ' <span style="font-size:11px;color:var(--text-muted);font-weight:400">(미리보기 단계 — DB 저장 전)</span></div>' +
          '<div style="color:var(--text-muted);font-size:12px;margin-top:6px">📑 서류: ' + docsBadges + '</div>' +
          '<div style="color:' + xcColor + ';font-size:13px;font-weight:600;margin-top:6px">' + xcIcon + ' ' + escapeHtml(xc.summary || '') + '</div>' +
          xcItemsHtml +
          (xc.has_critical ? '<div style="color:var(--danger);font-size:11px;margin-top:6px;font-weight:600">🚫 심각 불일치 감지 — 파일 확인 후 다시 파싱 권장</div>' : '') +
          '<div style="color:var(--info, #42a5f5);font-size:11px;margin-top:8px">💡 셀 더블클릭으로 편집 가능 · 완료 후 하단 "📤 DB 업로드" 버튼 클릭</div>';

        /* 18열 미리보기 테이블 채우기 + 편집 상태 초기화 */
        var rows = d.preview_rows || [];
        _onestopState.previewRows = rows.slice();  /* 편집 대상 */
        _onestopState.originalRows = JSON.parse(JSON.stringify(rows));  /* deep copy */
        _onestopState.editedCells = {};
        _onestopState.parsed = rows.length > 0;
        /* [Sprint 1-2-D] 새 파싱 → Undo 히스토리 리셋 */
        _onestopState.history = [];
        _onestopState.historyIdx = -1;
        /* D/O 수동 정보가 있고 DO 파일이 없었다면 새 rows 에 적용 */
        if (_onestopState.manualDo && !_onestopState.files.DO) {
          var md = _onestopState.manualDo;
          _onestopState.previewRows.forEach(function(r, i){
            if (!r) return;
            if (md.free_time && !r.free_time)   { r.free_time = md.free_time; _onestopState.editedCells[i + '.free_time'] = true; }
            if (md.warehouse && !r.wh)           { r.wh = md.warehouse;        _onestopState.editedCells[i + '.wh'] = true; }
            if (md.arrival_date && !r.arrival)  { r.arrival = md.arrival_date; _onestopState.editedCells[i + '.arrival'] = true; }
          });
        }
        _onestopRenderPreview(_onestopState.previewRows);
        _onestopUpdateHistoryButtons();

        _onestopSetStep(3);
        if (rows.length > 0) {
          var saveBtn = document.getElementById('onestop-save-btn');
          if (saveBtn) { saveBtn.disabled = false; saveBtn.textContent = '📤 DB 업로드 (' + rows.length + '건)'; }
        }
        showToast('success', '파싱 완료: ' + rows.length + ' LOT — 편집 후 DB 업로드');
      } else {
        var errMsg = (body && (body.detail || body.error || body.message)) || ('HTTP ' + xhr.status);
        if (typeof errMsg === 'object') errMsg = JSON.stringify(errMsg);
        if (pb) pb.innerHTML = '<div style="color:var(--danger);font-weight:700">❌ 파싱 실패</div><div style="color:var(--text-muted);font-size:12px;margin-top:4px">' + escapeHtml(String(errMsg)) + '</div>';
        showToast('error', '파싱 실패: ' + errMsg);
        _onestopSetStep(1);
      }
    };
    xhr.onerror = function(){
      if (pb) pb.innerHTML = '<div style="color:var(--danger)">❌ 네트워크 에러</div>';
      showToast('error', '네트워크 에러');
      _onestopSetStep(1);
    };
    xhr.send(form);

    var reparseBtn = document.getElementById('onestop-reparse-btn');
    if (reparseBtn) reparseBtn.disabled = false;
  };

  /* 18열 미리보기 렌더 — preview_rows (백엔드 응답) → Table body
     [Sprint 1-2-C] 각 셀에 data-row / data-field 부여, 더블클릭 편집 지원 */
  function _onestopRenderPreview(rows) {
    var tbody = document.getElementById('onestop-preview-body');
    if (!tbody) return;
    if (!rows || !rows.length) {
      tbody.innerHTML = '<tr><td colspan="' + ONESTOP_PREVIEW_COLS.length + '" class="onestop-preview-empty">📭 파싱 결과 0행</td></tr>';
      return;
    }
    /* xc_tag 에 따른 행 색상 */
    function tagColor(tag) {
      if (tag === 'xc_critical') return 'background:rgba(244,67,54,.15)';
      if (tag === 'xc_warning')  return 'background:rgba(255,167,38,.12)';
      if (tag === 'xc_info')     return 'background:rgba(66,165,245,.08)';
      return '';
    }
    /* field 키 → 컬럼 정의 (편집가능 여부 + 정렬 스타일) */
    var fields = [
      { key: 'no',          align: 'right',  accent: false },
      { key: 'lot_no',      align: 'left',   accent: true  },
      { key: 'sap_no',      align: 'left',   accent: false },
      { key: 'bl_no',       align: 'left',   accent: false },
      { key: 'product',     align: 'left',   accent: false, mono: false },
      { key: 'status',      align: 'left',   accent: false, tag: true },
      { key: 'container',   align: 'left',   accent: false },
      { key: 'code',        align: 'left',   accent: false },
      { key: 'lot_sqm',     align: 'left',   accent: false },
      { key: 'mxbg',        align: 'right',  accent: false },
      { key: 'net_kg',      align: 'right',  accent: false },
      { key: 'gross_kg',    align: 'right',  accent: false },
      { key: 'invoice_no',  align: 'left',   accent: false },
      { key: 'ship_date',   align: 'left',   accent: false },
      { key: 'arrival',     align: 'left',   accent: false },
      { key: 'con_return',  align: 'left',   accent: false },
      { key: 'free_time',   align: 'left',   accent: false },
      { key: 'wh',          align: 'left',   accent: false, mono: false },
    ];

    tbody.innerHTML = rows.map(function(r, rowIdx){
      var style = tagColor(r.xc_tag);
      var cellsHtml = fields.map(function(f){
        var val = r[f.key];
        var text = (val == null ? '' : String(val));
        var editable = ONESTOP_EDITABLE_FIELDS.has(f.key);
        var edited = _onestopState.editedCells[rowIdx + '.' + f.key];
        var cellClass = [
          (f.mono !== false ? 'mono-cell' : ''),
          (editable ? 'onestop-editable' : ''),
          (edited ? 'onestop-edited' : ''),
        ].filter(Boolean).join(' ');
        var cellStyle = [
          'text-align:' + f.align,
          (f.accent ? 'color:var(--accent);font-weight:600' : ''),
        ].filter(Boolean).join(';');
        var attrs = 'class="' + cellClass + '"' +
                    (cellStyle ? ' style="' + cellStyle + '"' : '') +
                    ' data-row="' + rowIdx + '" data-field="' + f.key + '"' +
                    (editable ? ' ondblclick="window.onestopEditCell(this)" title="더블클릭으로 편집"' : '');
        var rendered = f.tag ? '<span class="tag">' + escapeHtml(text) + '</span>' : escapeHtml(text);
        return '<td ' + attrs + '>' + rendered + '</td>';
      }).join('');
      return '<tr' + (style ? ' style="' + style + '"' : '') + '>' + cellsHtml + '</tr>';
    }).join('');
  }

  /* 셀 더블클릭 → input 으로 교체, blur/Enter 로 커밋, Escape 로 취소 */
  window.onestopEditCell = function(td) {
    if (!td || td.querySelector('input')) return;  /* 이미 편집 중 */
    var rowIdx = parseInt(td.dataset.row, 10);
    var field  = td.dataset.field;
    if (isNaN(rowIdx) || !field) return;
    var curVal = (_onestopState.previewRows[rowIdx] || {})[field];
    curVal = (curVal == null ? '' : String(curVal));

    var input = document.createElement('input');
    input.type = 'text';
    input.value = curVal;
    input.className = 'onestop-edit-input';
    input.style.cssText = 'width:100%;padding:2px 4px;background:var(--bg);color:var(--fg);border:1px solid var(--accent);border-radius:3px;font-size:11px;font-family:inherit';

    td.innerHTML = '';
    td.appendChild(input);
    input.focus();
    input.select();

    function commit() {
      var newVal = input.value;
      /* 값 변화 없으면 history 기록 생략 */
      if (String(newVal) === String(curVal)) {
        _onestopRenderPreview(_onestopState.previewRows);
        return;
      }
      /* [Sprint 1-2-D] Undo 스택에 push (현재 위치 이후 redo 엔트리 제거) */
      _onestopState.history = _onestopState.history.slice(0, _onestopState.historyIdx + 1);
      _onestopState.history.push({ rowIdx: rowIdx, field: field, oldVal: curVal, newVal: newVal });
      if (_onestopState.history.length > ONESTOP_MAX_HISTORY) {
        _onestopState.history.shift();
      }
      _onestopState.historyIdx = _onestopState.history.length - 1;

      /* 상태 업데이트 */
      if (!_onestopState.previewRows[rowIdx]) _onestopState.previewRows[rowIdx] = {};
      _onestopState.previewRows[rowIdx][field] = newVal;
      var origVal = (_onestopState.originalRows[rowIdx] || {})[field];
      var cellKey = rowIdx + '.' + field;
      if (String(newVal) !== String(origVal == null ? '' : origVal)) {
        _onestopState.editedCells[cellKey] = true;
      } else {
        delete _onestopState.editedCells[cellKey];
      }
      _onestopRenderPreview(_onestopState.previewRows);
      _onestopUpdateHistoryButtons();
    }
    function cancel() {
      _onestopRenderPreview(_onestopState.previewRows);
    }
    input.addEventListener('blur', commit);
    input.addEventListener('keydown', function(e){
      if (e.key === 'Enter') { e.preventDefault(); input.blur(); }
      else if (e.key === 'Escape') { e.preventDefault(); input.removeEventListener('blur', commit); cancel(); }
      /* Tab 은 기본 동작 허용 (포커스 이동) + blur 로 commit 됨 */
    });
  };
  window.onestopParseRedo = function() {
    _onestopState.step = 1;
    _onestopSetStep(1);
    window.onestopParseStart();
  };
  /* [Sprint 1-2-C] 편집된 미리보기 rows → /onestop-save POST → DB 저장 */
  window.onestopSaveDb = function() {
    if (!_onestopState.parsed || !_onestopState.previewRows.length) {
      showToast('warn', '파싱된 데이터가 없습니다. ▶ 파싱 시작을 먼저 실행하세요');
      return;
    }
    var editedCount = Object.keys(_onestopState.editedCells).length;
    var rowCount = _onestopState.previewRows.length;
    var confirmMsg = '💾 DB 저장 확인\n\n' +
      '총 ' + rowCount + ' LOT (편집된 셀 ' + editedCount + '개)\n' +
      '실제 재고 DB에 등록됩니다. 계속하시겠습니까?';
    if (!confirm(confirmMsg)) return;

    var saveBtn = document.getElementById('onestop-save-btn');
    if (saveBtn) { saveBtn.disabled = true; saveBtn.textContent = '⏳ 저장 중...'; }

    apiPost('/api/inbound/onestop-save', { rows: _onestopState.previewRows })
      .then(function(res){
        var d = (res && res.data) || {};
        if (res && res.ok) {
          _onestopSetStep(4);
          if (saveBtn) { saveBtn.disabled = true; saveBtn.textContent = '✅ 저장 완료 (' + (d.success_count || 0) + '건)'; }
          var pb = document.getElementById('onestop-progress-body');
          var errHtml = '';
          if (d.errors && d.errors.length) {
            errHtml = '<details style="margin-top:6px"><summary style="cursor:pointer;font-size:12px;color:var(--warning)">⚠️ 실패 ' + d.errors.length + '건 상세</summary>' +
              '<ul style="font-size:11px;margin:4px 0 0 20px">' +
              d.errors.map(function(er){
                return '<li>row ' + er.row + ' — ' + escapeHtml(er.lot_no || '-') + ': ' + escapeHtml(er.reason || '') + '</li>';
              }).join('') + '</ul></details>';
          }
          if (pb) pb.innerHTML +=
            '<div style="margin-top:10px;padding:8px;background:rgba(102,187,106,.1);border-left:3px solid var(--success);border-radius:4px">' +
            '<div style="color:var(--success);font-weight:700">💾 DB 저장 완료 — 성공 ' + (d.success_count || 0) + '건 / 실패 ' + (d.fail_count || 0) + '건</div>' +
            errHtml + '</div>';
          showToast(d.fail_count ? 'warn' : 'success', 'DB 저장: 성공 ' + d.success_count + '건 / 실패 ' + d.fail_count + '건');
          if (_currentRoute === 'inventory' && typeof loadInventoryPage === 'function') loadInventoryPage();
          if (typeof loadKpi === 'function') loadKpi();
        } else {
          var msg = (res && (res.message || res.error)) || 'DB 저장 실패';
          showToast('error', msg);
          if (saveBtn) { saveBtn.disabled = false; saveBtn.textContent = '📤 DB 업로드 재시도'; }
        }
      })
      .catch(function(e){
        showToast('error', 'DB 저장 오류: ' + (e.message || String(e)));
        if (saveBtn) { saveBtn.disabled = false; saveBtn.textContent = '📤 DB 업로드 재시도'; }
      });
  };
  function _onestopSetStep(step) {
    _onestopState.step = step;
    document.querySelectorAll('.wizard-steps .step').forEach(function(el){
      var n = parseInt(el.dataset.step, 10);
      el.classList.toggle('active', n === step);
      el.classList.toggle('done', n < step);
    });
  }

  /* F017 Picking List PDF 업로드 */
  function showPickingListPdfModal() {
    _showPdfUploadModal({
      title: '📋 Picking List PDF 업로드',
      subtitle: 'Picking List PDF 를 업로드하면 자동 파싱하여 picking_table 에 반영합니다.',
      endpoint: '/api/outbound/picking-list-pdf',
      onSuccess: function(d) {
        var warnHtml = '';
        if (d.warnings && d.warnings.length) {
          warnHtml = '<details style="margin-top:8px"><summary style="cursor:pointer;color:var(--warning)">⚠️ 경고 ' + d.warnings.length + '건</summary><pre style="white-space:pre-wrap;font-size:.8rem;margin-top:8px">' + escapeHtml(d.warnings.join('\n')) + '</pre></details>';
        }
        return '<div style="color:var(--text-muted);font-size:.85rem">파일: ' + escapeHtml(d.filename||'-') +
               ' · 방법: ' + escapeHtml(d.parse_method||'-') +
               ' · LOT ' + (d.total_lots||0) + '개 · 일반 ' + (d.total_normal_mt||0) + ' MT · 샘플 ' + (d.total_sample_kg||0) + ' KG' +
               ' · <strong style="color:var(--accent)">반영 ' + (d.applied||0) + '건</strong>' +
               '</div>' + warnHtml;
      }
    });
  }
  window.showPickingListPdfModal = showPickingListPdfModal;

  /* ===================================================
     8h. F016 빠른 출고 (붙여넣기) — 여러 LOT 일괄
     =================================================== */
  function showQuickOutboundPasteModal() {
    var html = [
      '<div style="max-width:640px">',
      '  <h2 style="margin:0 0 12px 0">📤 빠른 출고 (붙여넣기)</h2>',
      '  <p style="color:var(--text-muted);margin:0 0 12px 0;font-size:.9rem">',
      '    아래에 LOT별 수량을 붙여넣으세요. 형식: <code>LOT_NO [TAB/공백/쉼표] 개수</code> (한 줄에 1 LOT)',
      '  </p>',
      '  <textarea id="qop-text" placeholder="1126013063\\t3&#10;1126013107,2&#10;1126013108 1" style="width:100%;height:140px;padding:10px;background:var(--bg-hover);color:var(--text);border:1px solid var(--border);border-radius:6px;font-family:monospace;font-size:.9rem;margin-bottom:10px"></textarea>',
      '  <div style="display:grid;grid-template-columns:110px 1fr;gap:10px;align-items:center;margin-bottom:10px">',
      '    <label style="font-weight:600">고객명</label>',
      '    <input type="text" id="qop-customer" placeholder="예: ACME Corp" style="padding:8px;background:var(--bg-hover);color:var(--text);border:1px solid var(--border);border-radius:6px">',
      '    <label style="font-weight:600">사유 <span style="color:var(--text-muted);font-weight:400;font-size:.8rem">(선택)</span></label>',
      '    <input type="text" id="qop-reason" style="padding:8px;background:var(--bg-hover);color:var(--text);border:1px solid var(--border);border-radius:6px">',
      '    <label style="font-weight:600">작업자 <span style="color:var(--text-muted);font-weight:400;font-size:.8rem">(선택)</span></label>',
      '    <input type="text" id="qop-operator" style="padding:8px;background:var(--bg-hover);color:var(--text);border:1px solid var(--border);border-radius:6px">',
      '  </div>',
      '  <div id="qop-preview" style="padding:8px;background:var(--bg-hover);border-radius:6px;font-size:.85rem;color:var(--text-muted);margin-bottom:12px;min-height:32px">텍스트를 입력하면 파싱 결과가 여기에 표시됩니다</div>',
      '  <div id="qop-result" style="margin-bottom:12px"></div>',
      '  <div style="display:flex;gap:8px;justify-content:flex-end">',
      '    <button id="qop-cancel" class="btn btn-ghost">닫기</button>',
      '    <button id="qop-submit" class="btn btn-primary" disabled>일괄 출고</button>',
      '  </div>',
      '</div>'
    ].join('\n');
    showDataModal('', html);

    var txt = document.getElementById('qop-text');
    var cust = document.getElementById('qop-customer');
    var reason = document.getElementById('qop-reason');
    var op = document.getElementById('qop-operator');
    var preview = document.getElementById('qop-preview');
    var result = document.getElementById('qop-result');
    var submit = document.getElementById('qop-submit');
    var cancel = document.getElementById('qop-cancel');

    function parseRows() {
      var rows = [];
      var lines = (txt.value || '').split(/\r?\n/);
      for (var i = 0; i < lines.length; i++) {
        var line = lines[i].trim();
        if (!line) continue;
        var parts = line.split(/[\s,\t]+/).filter(Boolean);
        if (parts.length < 2) continue;
        var lot = parts[0];
        var n = parseInt(parts[1], 10);
        if (!lot || isNaN(n) || n <= 0) continue;
        rows.push({ lot_no: lot, count: n });
      }
      return rows;
    }

    function updatePreview() {
      var rows = parseRows();
      if (rows.length === 0) {
        preview.innerHTML = '텍스트를 입력하면 파싱 결과가 여기에 표시됩니다';
        submit.disabled = true;
        return;
      }
      var total = rows.reduce(function(s, r){ return s + r.count; }, 0);
      preview.innerHTML = '✅ <strong>' + rows.length + '개 LOT</strong> · 총 ' + total + ' 톤백 예정';
      submit.disabled = !cust.value.trim();
    }
    txt.addEventListener('input', updatePreview);
    cust.addEventListener('input', updatePreview);

    cancel.addEventListener('click', function(){ document.getElementById('sqm-modal').style.display='none'; });
    submit.addEventListener('click', function(){
      var rows = parseRows();
      if (!rows.length) return;
      var customer = cust.value.trim();
      var totalN = rows.reduce(function(s,r){return s+r.count;},0);
      if (!confirm('총 ' + rows.length + '개 LOT · ' + totalN + '개 톤백을 ' + customer + ' 로 출고합니다. 계속?')) return;

      submit.disabled = true; cancel.disabled = true;
      result.innerHTML = '<div style="padding:8px;color:var(--text-muted)">⏳ 일괄 출고 중...</div>';

      apiPost('/api/outbound/quick-paste', {
        rows: rows, customer: customer,
        reason: reason.value.trim(), operator: op.value.trim()
      }).then(function(res) {
        var d = res && res.data || {};
        var color = (d.fail_count||0) === 0 ? 'var(--success)' : 'var(--warning)';
        var resultsHtml = (d.results||[]).map(function(r){
          var icon = r.ok ? '✅' : '❌';
          var info = r.ok ? (r.picked_count + '개 · ' + (r.total_weight_kg||0).toFixed(1) + ' kg') : escapeHtml(r.reason||'');
          return '<tr><td>' + r.row + '</td><td>' + icon + '</td><td class="mono-cell">' + escapeHtml(r.lot_no) + '</td><td>' + info + '</td></tr>';
        }).join('');
        result.innerHTML =
          '<div style="padding:12px;background:var(--bg-hover);border-radius:6px;border-left:4px solid '+color+'">' +
          '<div style="font-weight:600;margin-bottom:4px">' + ((d.fail_count||0)===0 ? '✅' : '⚠️') + ' ' + escapeHtml(res.message||'완료') + '</div>' +
          '<div style="color:var(--text-muted);font-size:.85rem">총 ' + (d.total||0) + '건 · 성공 ' + (d.success_count||0) + ' · 실패 ' + (d.fail_count||0) + ' · ' + (d.total_weight_mt||0).toFixed(3) + ' MT</div>' +
          '<table class="data-table" style="margin-top:8px;font-size:.85rem"><thead><tr><th>행</th><th></th><th>LOT</th><th>상세</th></tr></thead><tbody>' + resultsHtml + '</tbody></table>' +
          '</div>';
        showToast(res.ok ? 'success' : 'warning', res.message || '완료');
        dbgLog('🟢','QUICK-PASTE', res.message, '#66bb6a');
        if (_currentRoute === 'inventory' && typeof loadInventoryPage === 'function') loadInventoryPage();
        if (typeof loadKpi === 'function') loadKpi();
        cancel.disabled = false;
        submit.disabled = false;
      }).catch(function(e) {
        result.innerHTML = '<div style="padding:12px;color:var(--danger)">❌ ' + escapeHtml(e.message||String(e)) + '</div>';
        showToast('error', '실패: ' + (e.message||String(e)));
        submit.disabled = false; cancel.disabled = false;
      });
    });
  }
  window.showQuickOutboundPasteModal = showQuickOutboundPasteModal;

  /* ===================================================
     8i. F028 출고 확정 — PICKED → OUTBOUND
     =================================================== */
  function showOutboundConfirmModal() {
    var html = [
      '<div style="max-width:640px">',
      '  <h2 style="margin:0 0 12px 0">✅ 출고 확정 — PICKED → OUTBOUND</h2>',
      '  <p style="color:var(--text-muted);margin:0 0 12px 0;font-size:.9rem">',
      '    PICKED 상태인 톤백을 실제 출고(OUTBOUND)로 확정합니다.',
      '  </p>',
      '  <div style="display:grid;grid-template-columns:110px 1fr;gap:10px;align-items:center;margin-bottom:10px">',
      '    <label style="font-weight:600">LOT 번호</label>',
      '    <input type="text" id="oc-lot" placeholder="비워두면 전체 — force_all 필수" style="padding:8px;background:var(--bg-hover);color:var(--text);border:1px solid var(--border);border-radius:6px;font-family:monospace">',
      '  </div>',
      '  <label style="display:flex;align-items:center;gap:8px;padding:8px;background:var(--bg-hover);border-radius:6px;font-size:.85rem;margin-bottom:10px;color:var(--warning)">',
      '    <input type="checkbox" id="oc-force-all"> ⚠️ <strong>force_all</strong> — LOT 번호 없이 <u>전체 PICKED 일괄 확정</u> (위험)',
      '  </label>',
      '  <div id="oc-preview" style="padding:8px;background:var(--bg-hover);border-radius:6px;font-size:.85rem;color:var(--text-muted);margin-bottom:12px;min-height:40px">',
      '    LOT 번호 입력 또는 force_all 체크 시 PICKED 톤백 요약이 표시됩니다',
      '  </div>',
      '  <div id="oc-result" style="margin-bottom:12px"></div>',
      '  <div style="display:flex;gap:8px;justify-content:flex-end">',
      '    <button id="oc-cancel" class="btn btn-ghost">닫기</button>',
      '    <button id="oc-submit" class="btn btn-primary" disabled>출고 확정</button>',
      '  </div>',
      '</div>'
    ].join('\n');
    showDataModal('', html);

    var lot = document.getElementById('oc-lot');
    var force = document.getElementById('oc-force-all');
    var preview = document.getElementById('oc-preview');
    var result = document.getElementById('oc-result');
    var submit = document.getElementById('oc-submit');
    var cancel = document.getElementById('oc-cancel');

    var _deb = null;
    function loadSummary() {
      var q = lot.value.trim();
      preview.innerHTML = '⏳ 조회 중...';
      var url = '/api/outbound/picked-summary' + (q ? ('?lot_no=' + encodeURIComponent(q)) : '');
      apiGet(url).then(function(res){
        if (!res || !res.ok) { preview.innerHTML = '❌ 조회 실패'; submit.disabled = true; return; }
        var d = res.data || {};
        if ((d.total_count||0) === 0) {
          preview.innerHTML = '<span style="color:var(--warning)">⚠️ PICKED 상태 톤백이 없습니다 — 확정할 대상 없음</span>';
          submit.disabled = true;
          return;
        }
        var items = (d.items||[]).slice(0, 5).map(function(it){
          return '<tr><td class="mono-cell" style="color:var(--accent)">'+escapeHtml(it.lot_no)+'</td><td>'+it.count+'</td><td>'+(it.total_weight_mt||0).toFixed(3)+'</td><td>'+escapeHtml(it.picked_to||'-')+'</td><td class="mono-cell">'+escapeHtml(it.sale_ref||'-')+'</td></tr>';
        }).join('');
        var more = (d.items||[]).length > 5 ? '<tr><td colspan="5" style="text-align:center;color:var(--text-muted)">...외 '+((d.items||[]).length-5)+'개 LOT</td></tr>' : '';
        preview.innerHTML =
          '<div style="font-weight:600;margin-bottom:6px;color:var(--accent)">대상: ' + (d.total_lots||0) + ' LOT · ' + (d.total_count||0) + '개 톤백 · ' + (d.total_weight_mt||0).toFixed(3) + ' MT</div>' +
          '<table class="data-table" style="font-size:.85rem"><thead><tr><th>LOT</th><th>개수</th><th>MT</th><th>고객</th><th>sale_ref</th></tr></thead><tbody>' + items + more + '</tbody></table>';
        // submit enable 조건: lot_no 있거나 force_all true
        submit.disabled = !(q || force.checked);
      }).catch(function(e){
        preview.innerHTML = '❌ 조회 실패: ' + escapeHtml(e.message||String(e));
        submit.disabled = true;
      });
    }
    function scheduleSummary() {
      if (_deb) clearTimeout(_deb);
      _deb = setTimeout(loadSummary, 300);
    }
    lot.addEventListener('input', scheduleSummary);
    force.addEventListener('change', loadSummary);
    // 초기 로드 — 전체 PICKED
    loadSummary();

    cancel.addEventListener('click', function(){ document.getElementById('sqm-modal').style.display='none'; });
    submit.addEventListener('click', function(){
      var payload = { lot_no: lot.value.trim(), force_all: force.checked };
      var msg = payload.lot_no ? ('LOT ' + payload.lot_no + ' 의 PICKED 톤백을 OUTBOUND 로 확정합니다.') :
                                  '⚠️ LOT 미지정 — 전체 PICKED 일괄 확정입니다! 매우 위험.';
      if (!confirm(msg + '\n계속하시겠습니까?')) return;

      submit.disabled = true; cancel.disabled = true;
      result.innerHTML = '<div style="padding:8px;color:var(--text-muted)">⏳ 확정 중...</div>';

      apiPost('/api/outbound/confirm', payload).then(function(res){
        if (res && res.ok) {
          var d = res.data || {};
          result.innerHTML =
            '<div style="padding:12px;background:var(--bg-hover);border-radius:6px;border-left:4px solid var(--success)">' +
            '<div style="font-weight:600">✅ ' + escapeHtml(res.message||'확정 완료') + '</div>' +
            '<div style="color:var(--text-muted);font-size:.85rem;margin-top:4px">LOT: ' + escapeHtml(d.lot_no||'-') + ' · 확정 <strong>' + (d.confirmed||0) + '</strong>개</div>' +
            '</div>';
          showToast('success', res.message || '확정 완료');
          dbgLog('🟢','CONFIRM-OUTBOUND OK', res.message, '#66bb6a');
          if (_currentRoute === 'inventory' && typeof loadInventoryPage === 'function') loadInventoryPage();
          if (typeof loadKpi === 'function') loadKpi();
          loadSummary();
          cancel.disabled = false;
        } else {
          var errs = (res && res.data && res.data.errors) || [];
          var msg2 = (res && (res.message || res.error)) || '실패';
          result.innerHTML =
            '<div style="padding:12px;background:var(--bg-hover);border-radius:6px;border-left:4px solid var(--danger)">' +
            '<div style="font-weight:600">❌ ' + escapeHtml(msg2) + '</div>' +
            (errs.length ? '<ul style="margin:8px 0 0 18px;color:var(--text-muted);font-size:.85rem">' + errs.map(function(e){return '<li>'+escapeHtml(e)+'</li>';}).join('') + '</ul>' : '') +
            '</div>';
          showToast('error', msg2);
          submit.disabled = false; cancel.disabled = false;
        }
      }).catch(function(e){
        result.innerHTML = '<div style="padding:12px;color:var(--danger)">❌ ' + escapeHtml(e.message||String(e)) + '</div>';
        showToast('error', '실패: ' + (e.message||String(e)));
        submit.disabled = false; cancel.disabled = false;
      });
    });
  }
  window.showOutboundConfirmModal = showOutboundConfirmModal;

  /* ===================================================
     8i. 입고 취소 — LOT 선택 → POST /api/action2/inbound-cancel
     =================================================== */
  function showInboundCancelModal() {
    var html = [
      '<div style="max-width:480px">',
      '  <h2 style="margin:0 0 12px 0">↩️ 입고 취소</h2>',
      '  <p style="color:var(--text-muted);margin:0 0 16px 0;font-size:.9rem">',
      '    입고된 LOT를 취소(CANCELLED)합니다. 톤백 포함 원복됩니다.',
      '  </p>',
      '  <div style="display:grid;grid-template-columns:100px 1fr;gap:10px;align-items:center;margin-bottom:16px">',
      '    <label style="font-weight:600">LOT 번호</label>',
      '    <input type="text" id="ic-lot" placeholder="예: L240101-001" style="padding:8px;background:var(--bg-hover);color:var(--text);border:1px solid var(--border);border-radius:6px;font-family:monospace">',
      '    <label style="font-weight:600">사유</label>',
      '    <input type="text" id="ic-reason" placeholder="취소 사유 (선택)" style="padding:8px;background:var(--bg-hover);color:var(--text);border:1px solid var(--border);border-radius:6px">',
      '  </div>',
      '  <div id="ic-result" style="margin-bottom:12px;min-height:24px"></div>',
      '  <div style="display:flex;gap:8px;justify-content:flex-end">',
      '    <button id="ic-cancel" class="btn btn-ghost">닫기</button>',
      '    <button id="ic-submit" class="btn btn-primary">입고 취소</button>',
      '  </div>',
      '</div>'
    ].join('\n');
    showDataModal('', html);
    var cancel = document.getElementById('ic-cancel');
    var submit = document.getElementById('ic-submit');
    var result = document.getElementById('ic-result');
    cancel.addEventListener('click', function(){ document.getElementById('sqm-modal').style.display='none'; });
    submit.addEventListener('click', function(){
      var lot = document.getElementById('ic-lot').value.trim();
      if (!lot) { showToast('warning', 'LOT 번호를 입력하세요'); return; }
      if (!confirm('LOT ' + lot + ' 입고를 취소합니다. 계속할까요?')) return;
      submit.disabled = true; cancel.disabled = true;
      result.innerHTML = '<div style="padding:8px;color:var(--text-muted)">⏳ 처리 중...</div>';
      apiPost('/api/action2/inbound-cancel', { lot_no: lot, reason: document.getElementById('ic-reason').value.trim() })
        .then(function(res){
          if (res && res.ok) {
            result.innerHTML = '<div style="padding:12px;background:var(--bg-hover);border-radius:6px;border-left:4px solid var(--success)"><div style="font-weight:600">✅ ' + escapeHtml(res.message||'입고 취소 완료') + '</div></div>';
            showToast('success', res.message || '입고 취소 완료');
            if (typeof loadKpi === 'function') loadKpi();
          } else {
            result.innerHTML = '<div style="padding:12px;background:var(--bg-hover);border-radius:6px;border-left:4px solid var(--danger)"><div style="font-weight:600">❌ ' + escapeHtml((res&&res.message)||'실패') + '</div></div>';
            showToast('error', (res&&res.message)||'실패');
            submit.disabled = false; cancel.disabled = false;
          }
        })
        .catch(function(e){
          result.innerHTML = '<div style="padding:12px;color:var(--danger)">❌ ' + escapeHtml(e.message||String(e)) + '</div>';
          submit.disabled = false; cancel.disabled = false;
        });
    });
  }
  window.showInboundCancelModal = showInboundCancelModal;

  /* ===================================================
     8j. 승인 대기 (Allocation Approval Queue)
     =================================================== */
  function showApprovalQueueModal() {
    showDataModal('✅ 승인 대기','<div style="padding:20px;text-align:center">⏳ Loading...</div>');
    apiGet('/api/q/approval-history').then(function(res){
      var rows = extractRows(res);
      var pending = rows.filter(function(r){ return (r.approval_status||'').toUpperCase() === 'PENDING'; });
      var html;
      if (!pending.length && !rows.length) {
        html = '<div class="empty">승인 대기 건이 없습니다</div>';
      } else {
        var tgt = pending.length ? pending : rows;
        html = '<p style="color:var(--text-muted);font-size:.85rem;margin-bottom:12px">총 ' + tgt.length + '건' + (pending.length ? ' (PENDING)' : ' (전체 이력)') + '</p>';
        html += '<table class="data-table"><thead><tr><th>LOT</th><th>고객</th><th>수량</th><th>상태</th><th>요청일</th></tr></thead><tbody>';
        html += tgt.slice(0,50).map(function(r){
          return '<tr><td class="mono-cell">'+escapeHtml(r.lot_no||'-')+'</td><td>'+escapeHtml(r.sold_to||r.customer||'-')+'</td><td>'+(r.qty_mt!=null?Number(r.qty_mt).toFixed(3):'-')+'</td><td><span class="tag">'+escapeHtml(r.approval_status||r.status||'-')+'</span></td><td>'+escapeHtml(r.request_date||r.created_at||'-')+'</td></tr>';
        }).join('');
        html += '</tbody></table>';
      }
      document.getElementById('sqm-modal-content').innerHTML = '<h2 style="margin-bottom:16px">✅ 승인 대기 (Allocation)</h2>' + html;
    }).catch(function(e){
      document.getElementById('sqm-modal-content').innerHTML = '<h2>승인 대기</h2><div class="empty">조회 실패: ' + escapeHtml(e.message||String(e)) + '</div>';
    });
  }
  window.showApprovalQueueModal = showApprovalQueueModal;

  /* ===================================================
     8k. 백업 복원 — 목록 조회 → 선택 → 복원 실행
     =================================================== */
  function showRestoreModal() {
    showDataModal('🔄 백업 복원','<div style="padding:20px;text-align:center">⏳ 백업 목록 로딩...</div>');
    apiGet('/api/q/backup-list').then(function(res){
      var rows = extractRows(res);
      if (!rows.length) {
        document.getElementById('sqm-modal-content').innerHTML = '<h2>🔄 백업 복원</h2><div class="empty">사용 가능한 백업 파일이 없습니다</div>';
        return;
      }
      var html = '<h2 style="margin-bottom:12px">🔄 백업 복원</h2>';
      html += '<p style="color:var(--text-muted);font-size:.85rem;margin-bottom:12px">복원할 백업 파일을 선택하세요. <strong style="color:var(--warning)">⚠️ 현재 DB가 덮어씌워집니다!</strong></p>';
      html += '<div style="max-height:300px;overflow:auto"><table class="data-table"><thead><tr><th>선택</th><th>파일명</th><th>크기</th><th>생성일</th></tr></thead><tbody>';
      html += rows.map(function(r, i){
        return '<tr><td><input type="radio" name="restore-sel" value="'+i+'" data-file="'+escapeHtml(r.filename||r.name||'')+'"></td><td class="mono-cell">'+escapeHtml(r.filename||r.name||'-')+'</td><td>'+(r.size_mb!=null?r.size_mb.toFixed(2)+' MB':(r.size||'-'))+'</td><td>'+escapeHtml(r.modified||r.mtime||r.created||'-')+'</td></tr>';
      }).join('');
      html += '</tbody></table></div>';
      html += '<div id="restore-result" style="margin:12px 0;min-height:24px"></div>';
      html += '<div style="display:flex;gap:8px;justify-content:flex-end"><button id="restore-cancel" class="btn btn-ghost">닫기</button><button id="restore-submit" class="btn btn-primary">복원 실행</button></div>';
      document.getElementById('sqm-modal-content').innerHTML = html;

      document.getElementById('restore-cancel').addEventListener('click', function(){ document.getElementById('sqm-modal').style.display='none'; });
      document.getElementById('restore-submit').addEventListener('click', function(){
        var sel = document.querySelector('input[name="restore-sel"]:checked');
        if (!sel) { showToast('warning', '복원할 백업 파일을 선택하세요'); return; }
        var fname = sel.dataset.file;
        if (!confirm('⚠️ ' + fname + ' 으로 DB를 복원합니다.\n현재 데이터가 모두 덮어씌워집니다.\n\n정말 계속할까요?')) return;
        var btn = document.getElementById('restore-submit');
        btn.disabled = true;
        document.getElementById('restore-result').innerHTML = '<div style="padding:8px;color:var(--text-muted)">⏳ 복원 중...</div>';
        apiPost('/api/action/restore', { filename: fname })
          .then(function(res){
            if (res && res.ok) {
              document.getElementById('restore-result').innerHTML = '<div style="padding:12px;background:var(--bg-hover);border-radius:6px;border-left:4px solid var(--success)"><div style="font-weight:600">✅ ' + escapeHtml(res.message||'복원 완료') + '</div></div>';
              showToast('success', res.message || '복원 완료');
            } else {
              document.getElementById('restore-result').innerHTML = '<div style="padding:12px;color:var(--danger)">❌ ' + escapeHtml((res&&res.message)||'복원 실패') + '</div>';
              btn.disabled = false;
            }
          })
          .catch(function(e){
            document.getElementById('restore-result').innerHTML = '<div style="padding:12px;color:var(--danger)">❌ ' + escapeHtml(e.message||String(e)) + '</div>';
            btn.disabled = false;
          });
      });
    }).catch(function(e){
      document.getElementById('sqm-modal-content').innerHTML = '<h2>🔄 백업 복원</h2><div class="empty">백업 목록 조회 실패: ' + escapeHtml(e.message||String(e)) + '</div>';
    });
  }
  window.showRestoreModal = showRestoreModal;

  /* ===================================================
     8l. 창 크기 저장 / 초기화 — PyWebView API
     =================================================== */
  function saveWindowSize() {
    if (window.pywebview && window.pywebview.api && window.pywebview.api.save_window_size) {
      window.pywebview.api.save_window_size();
      showToast('success', '현재 창 크기가 저장되었습니다');
    } else {
      var w = window.innerWidth, h = window.innerHeight;
      try { getStore().setItem('sqm_window_size', w+'x'+h); } catch(e){}
      showToast('success', '창 크기 저장됨: ' + w + ' x ' + h);
    }
    dbgLog('💾','Window size saved', window.innerWidth + 'x' + window.innerHeight, '#4caf50');
  }
  function resetWindowSize() {
    if (window.pywebview && window.pywebview.api && window.pywebview.api.reset_window_size) {
      window.pywebview.api.reset_window_size();
    } else {
      try { window.resizeTo(1500, 900); } catch(e){}
      try { getStore().removeItem('sqm_window_size'); } catch(e){}
    }
    showToast('success', '기본 창 크기(1500x900)로 초기화되었습니다');
    dbgLog('↩️','Window size reset', '1500x900', '#4caf50');
  }

  /* ===================================================
     8m. 반품 다이얼로그 — 2탭: 소량(수동) + 다량(Excel)
     =================================================== */
  function showReturnDialog() {
    var html = [
      '<div style="max-width:600px">',
      '  <h2 style="margin:0 0 12px 0">🔄 반품 (재입고)</h2>',
      '  <div style="display:flex;gap:0;margin-bottom:16px">',
      '    <button id="ret-tab-manual" class="btn btn-ghost" style="flex:1;border-radius:6px 0 0 6px;border:1px solid var(--border);background:var(--accent);color:#fff">📝 소량 반품 (수동)</button>',
      '    <button id="ret-tab-excel" class="btn btn-ghost" style="flex:1;border-radius:0 6px 6px 0;border:1px solid var(--border)">📂 다량 반품 (Excel)</button>',
      '  </div>',
      '  <div id="ret-panel-manual">',
      '    <div style="display:grid;grid-template-columns:100px 1fr;gap:10px;align-items:center;margin-bottom:12px">',
      '      <label style="font-weight:600">LOT 번호</label>',
      '      <input type="text" id="ret-lot" placeholder="반품할 LOT" style="padding:8px;background:var(--bg-hover);color:var(--text);border:1px solid var(--border);border-radius:6px;font-family:monospace">',
      '      <label style="font-weight:600">톤백 수</label>',
      '      <input type="number" id="ret-count" placeholder="반품 톤백 수" min="1" value="1" style="padding:8px;background:var(--bg-hover);color:var(--text);border:1px solid var(--border);border-radius:6px">',
      '      <label style="font-weight:600">사유</label>',
      '      <select id="ret-reason" style="padding:8px;background:var(--bg-hover);color:var(--text);border:1px solid var(--border);border-radius:6px">',
      '        <option value="품질 불량">품질 불량</option>',
      '        <option value="수량 초과">수량 초과</option>',
      '        <option value="오배송">오배송</option>',
      '        <option value="고객 변심">고객 변심</option>',
      '        <option value="기타">기타</option>',
      '      </select>',
      '      <label style="font-weight:600">메모</label>',
      '      <input type="text" id="ret-memo" placeholder="추가 메모 (선택)" style="padding:8px;background:var(--bg-hover);color:var(--text);border:1px solid var(--border);border-radius:6px">',
      '    </div>',
      '  </div>',
      '  <div id="ret-panel-excel" style="display:none">',
      '    <p style="color:var(--text-muted);font-size:.9rem;margin-bottom:12px">다량 반품 Excel 파일을 업로드하세요.</p>',
      '    <button id="ret-excel-btn" class="btn btn-primary" style="width:100%">📂 반품 Excel 업로드 열기</button>',
      '  </div>',
      '  <div id="ret-result" style="margin:12px 0;min-height:24px"></div>',
      '  <div style="display:flex;gap:8px;justify-content:flex-end">',
      '    <button id="ret-cancel" class="btn btn-ghost">닫기</button>',
      '    <button id="ret-submit" class="btn btn-primary">반품 처리</button>',
      '  </div>',
      '</div>'
    ].join('\n');
    showDataModal('', html);

    var tabManual = document.getElementById('ret-tab-manual');
    var tabExcel = document.getElementById('ret-tab-excel');
    var panelManual = document.getElementById('ret-panel-manual');
    var panelExcel = document.getElementById('ret-panel-excel');
    var submitBtn = document.getElementById('ret-submit');

    tabManual.addEventListener('click', function(){
      panelManual.style.display=''; panelExcel.style.display='none';
      tabManual.style.background='var(--accent)'; tabManual.style.color='#fff';
      tabExcel.style.background=''; tabExcel.style.color='';
      submitBtn.style.display='';
    });
    tabExcel.addEventListener('click', function(){
      panelManual.style.display='none'; panelExcel.style.display='';
      tabExcel.style.background='var(--accent)'; tabExcel.style.color='#fff';
      tabManual.style.background=''; tabManual.style.color='';
      submitBtn.style.display='none';
    });
    document.getElementById('ret-excel-btn').addEventListener('click', function(){
      document.getElementById('sqm-modal').style.display='none';
      showReturnInboundUploadModal();
    });
    document.getElementById('ret-cancel').addEventListener('click', function(){ document.getElementById('sqm-modal').style.display='none'; });
    submitBtn.addEventListener('click', function(){
      var lot = document.getElementById('ret-lot').value.trim();
      if (!lot) { showToast('warning', 'LOT 번호를 입력하세요'); return; }
      if (!confirm('LOT ' + lot + ' 반품 처리를 진행합니다.')) return;
      submitBtn.disabled = true;
      var result = document.getElementById('ret-result');
      result.innerHTML = '<div style="padding:8px;color:var(--text-muted)">⏳ 처리 중...</div>';
      apiPost('/api/action3/return-create', {
        lot_no: lot,
        tonbag_count: parseInt(document.getElementById('ret-count').value)||1,
        reason: document.getElementById('ret-reason').value,
        memo: document.getElementById('ret-memo').value.trim()
      }).then(function(res){
        if (res && res.ok) {
          result.innerHTML = '<div style="padding:12px;background:var(--bg-hover);border-radius:6px;border-left:4px solid var(--success)"><div style="font-weight:600">✅ ' + escapeHtml(res.message||'반품 완료') + '</div></div>';
          showToast('success', res.message || '반품 완료');
        } else {
          result.innerHTML = '<div style="padding:12px;color:var(--danger)">❌ ' + escapeHtml((res&&res.message)||'실패') + '</div>';
          submitBtn.disabled = false;
        }
      }).catch(function(e){
        result.innerHTML = '<div style="padding:12px;color:var(--danger)">❌ ' + escapeHtml(e.message||String(e)) + '</div>';
        submitBtn.disabled = false;
      });
    });
  }
  window.showReturnDialog = showReturnDialog;

  /* ===================================================
     8n. LOT Allocation·톤백 현황 조회
     =================================================== */
  function showLotAllocationAuditModal() {
    var html = [
      '<div style="max-width:700px">',
      '  <h2 style="margin:0 0 12px 0">📊 LOT Allocation·톤백 현황</h2>',
      '  <div style="display:flex;gap:8px;margin-bottom:16px;align-items:center">',
      '    <input type="text" id="laa-lot" placeholder="LOT 번호 (비우면 전체)" style="flex:1;padding:8px;background:var(--bg-hover);color:var(--text);border:1px solid var(--border);border-radius:6px;font-family:monospace">',
      '    <button id="laa-search" class="btn btn-primary">조회</button>',
      '  </div>',
      '  <div id="laa-result" style="min-height:60px"><div class="empty">LOT 번호를 입력하고 조회를 클릭하세요</div></div>',
      '  <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:16px">',
      '    <button id="laa-close" class="btn btn-ghost">닫기</button>',
      '  </div>',
      '</div>'
    ].join('\n');
    showDataModal('', html);
    document.getElementById('laa-close').addEventListener('click', function(){ document.getElementById('sqm-modal').style.display='none'; });
    document.getElementById('laa-search').addEventListener('click', function(){
      var lot = document.getElementById('laa-lot').value.trim();
      var result = document.getElementById('laa-result');
      result.innerHTML = '<div style="padding:20px;text-align:center">⏳ 조회 중...</div>';
      var url = '/api/q/product-inventory' + (lot ? '?lot_no=' + encodeURIComponent(lot) : '');
      apiGet(url).then(function(res){
        var rows = extractRows(res);
        if (!rows.length) { result.innerHTML = '<div class="empty">데이터가 없습니다</div>'; return; }
        var tbl = '<table class="data-table"><thead><tr><th>LOT</th><th>제품</th><th>상태</th><th>톤백수</th><th>중량(MT)</th><th>위치</th></tr></thead><tbody>';
        tbl += rows.slice(0,100).map(function(r){
          return '<tr><td class="mono-cell" style="color:var(--accent)">'+escapeHtml(r.lot_no||'-')+'</td><td>'+escapeHtml(r.product||'-')+'</td><td><span class="tag">'+escapeHtml(r.status||'-')+'</span></td><td>'+(r.tonbag_count||r.total_tonbags||'-')+'</td><td>'+(r.net_weight!=null?Number(r.net_weight).toFixed(3):(r.total_weight||'-'))+'</td><td>'+escapeHtml(r.location||r.warehouse||'-')+'</td></tr>';
        }).join('');
        tbl += '</tbody></table>';
        result.innerHTML = '<p style="color:var(--text-muted);font-size:.85rem;margin-bottom:8px">총 ' + rows.length + '건</p>' + tbl;
      }).catch(function(e){
        result.innerHTML = '<div class="empty">조회 실패: ' + escapeHtml(e.message||String(e)) + '</div>';
      });
    });
  }
  window.showLotAllocationAuditModal = showLotAllocationAuditModal;

  /* ===================================================
     8o. 테스트 DB 초기화 (개발자 전용)
     =================================================== */
  function showTestDbResetModal() {
    var html = [
      '<div style="max-width:480px">',
      '  <h2 style="margin:0 0 12px 0;color:var(--danger)">🗑️ 테스트 DB 초기화</h2>',
      '  <div style="padding:16px;background:var(--bg-hover);border-radius:6px;border-left:4px solid var(--danger);margin-bottom:16px">',
      '    <div style="font-weight:600;color:var(--danger)">⚠️ 위험한 작업</div>',
      '    <div style="color:var(--text-muted);font-size:.9rem;margin-top:4px">모든 데이터가 삭제됩니다. 이 작업은 되돌릴 수 없습니다.</div>',
      '  </div>',
      '  <div style="margin-bottom:16px">',
      '    <label style="display:flex;align-items:center;gap:8px;color:var(--warning)">',
      '      <input type="checkbox" id="dbr-confirm"> 위 내용을 이해했으며 DB를 초기화합니다',
      '    </label>',
      '  </div>',
      '  <div id="dbr-result" style="margin-bottom:12px;min-height:24px"></div>',
      '  <div style="display:flex;gap:8px;justify-content:flex-end">',
      '    <button id="dbr-cancel" class="btn btn-ghost">닫기</button>',
      '    <button id="dbr-submit" class="btn btn-primary" disabled style="background:var(--danger)">초기화 실행</button>',
      '  </div>',
      '</div>'
    ].join('\n');
    showDataModal('', html);
    var chk = document.getElementById('dbr-confirm');
    var submit = document.getElementById('dbr-submit');
    chk.addEventListener('change', function(){ submit.disabled = !chk.checked; });
    document.getElementById('dbr-cancel').addEventListener('click', function(){ document.getElementById('sqm-modal').style.display='none'; });
    submit.addEventListener('click', function(){
      if (!confirm('정말로 DB를 완전 초기화할까요?\n\n이 작업은 되돌릴 수 없습니다!')) return;
      submit.disabled = true;
      document.getElementById('dbr-result').innerHTML = '<div style="padding:8px;color:var(--text-muted)">⏳ 초기화 중...</div>';
      apiPost('/api/action3/db-reset', { confirm: true })
        .then(function(res){
          if (res && res.ok) {
            document.getElementById('dbr-result').innerHTML = '<div style="padding:12px;background:var(--bg-hover);border-radius:6px;border-left:4px solid var(--success)"><div style="font-weight:600">✅ DB 초기화 완료</div></div>';
            showToast('success', 'DB 초기화 완료');
          } else {
            document.getElementById('dbr-result').innerHTML = '<div style="padding:12px;color:var(--danger)">❌ ' + escapeHtml((res&&res.message)||'실패') + '</div>';
            submit.disabled = false;
          }
        })
        .catch(function(e){
          document.getElementById('dbr-result').innerHTML = '<div style="padding:12px;color:var(--danger)">❌ ' + escapeHtml(e.message||String(e)) + '</div>';
          submit.disabled = false;
        });
    });
  }
  window.showTestDbResetModal = showTestDbResetModal;

  /* ===================================================
     8p. 바코드 스캔 업로드 — CSV/Excel 파일 업로드
     =================================================== */
  function showBarcodeScanUploadModal() {
    _showExcelUploadModal({
      title: '📊 바코드 스캔 업로드',
      subtitle: '바코드 스캔 결과 파일(Excel/CSV)을 선택하세요. 스캔된 UID와 LOT를 매칭하여 출고 처리합니다.',
      endpoint: '/api/inbound/bulk-import-excel',
      onSuccess: function(d) {
        return '<div style="color:var(--text-muted);font-size:.85rem">처리 결과: 성공 ' + (d.success_count||0) + ' / 실패 ' + (d.fail_count||0) + '</div>';
      }
    });
  }
  window.showBarcodeScanUploadModal = showBarcodeScanUploadModal;

  /* ===================================================
     8q. 설정 다이얼로그 모음 — 이메일/자동백업/템플릿
     =================================================== */
  function showSettingsDialog(title, icon, fields) {
    var html = '<div style="max-width:480px"><h2 style="margin:0 0 16px 0">' + icon + ' ' + escapeHtml(title) + '</h2>';
    html += '<div style="display:grid;grid-template-columns:130px 1fr;gap:10px;align-items:center;margin-bottom:16px">';
    fields.forEach(function(f){
      html += '<label style="font-weight:600">' + escapeHtml(f.label) + '</label>';
      if (f.type === 'select') {
        html += '<select id="sdlg-'+f.id+'" style="padding:8px;background:var(--bg-hover);color:var(--text);border:1px solid var(--border);border-radius:6px">';
        f.options.forEach(function(o){ html += '<option value="'+escapeHtml(o)+'">'+escapeHtml(o)+'</option>'; });
        html += '</select>';
      } else if (f.type === 'checkbox') {
        html += '<label style="display:flex;align-items:center;gap:6px"><input type="checkbox" id="sdlg-'+f.id+'"' + (f.checked ? ' checked' : '') + '> ' + escapeHtml(f.hint||'') + '</label>';
      } else {
        html += '<input type="'+(f.type||'text')+'" id="sdlg-'+f.id+'" placeholder="'+escapeHtml(f.hint||'')+'" value="'+escapeHtml(f.value||'')+'" style="padding:8px;background:var(--bg-hover);color:var(--text);border:1px solid var(--border);border-radius:6px">';
      }
    });
    html += '</div>';
    html += '<div style="padding:12px;background:var(--bg-hover);border-radius:6px;margin-bottom:16px;font-size:.85rem;color:var(--text-muted)">💡 설정은 현재 세션에만 적용됩니다. PyWebView 재시작 시 기본값으로 복원됩니다.</div>';
    html += '<div style="display:flex;gap:8px;justify-content:flex-end"><button onclick="document.getElementById(\'sqm-modal\').style.display=\'none\'" class="btn btn-ghost">닫기</button><button onclick="showToast(\'success\',\'설정 저장됨\');document.getElementById(\'sqm-modal\').style.display=\'none\'" class="btn btn-primary">저장</button></div>';
    html += '</div>';
    showDataModal('', html);
  }

  function showEmailConfigModal() {
    showSettingsDialog('이메일 설정', '⚙️', [
      { id:'host', label:'SMTP 서버', hint:'smtp.gmail.com', value:'smtp.gmail.com' },
      { id:'port', label:'포트', type:'number', hint:'587', value:'587' },
      { id:'user', label:'사용자', hint:'user@company.com' },
      { id:'pass', label:'비밀번호', type:'password', hint:'앱 비밀번호' },
      { id:'tls', label:'TLS 사용', type:'checkbox', checked:true, hint:'TLS 암호화' }
    ]);
  }
  window.showEmailConfigModal = showEmailConfigModal;

  function showAutoBackupSettingsModal() {
    showSettingsDialog('자동 백업 설정', '⏰', [
      { id:'enabled', label:'자동 백업', type:'checkbox', checked:false, hint:'활성화' },
      { id:'interval', label:'주기', type:'select', options:['30분','1시간','3시간','6시간','12시간','24시간'] },
      { id:'retention', label:'보존 개수', type:'number', hint:'최대 보존 백업 수', value:'10' },
      { id:'path', label:'저장 경로', hint:'backup/', value:'backup/' }
    ]);
  }
  window.showAutoBackupSettingsModal = showAutoBackupSettingsModal;

  function showInboundTemplateModal() {
    showSettingsDialog('입고 파싱 템플릿 관리', '📝', [
      { id:'name', label:'템플릿 이름', hint:'기본 Packing List' },
      { id:'format', label:'파싱 형식', type:'select', options:['SQM Standard','Custom Column','Auto-Detect'] },
      { id:'cols', label:'컬럼 매핑', hint:'lot_no,sap_no,bl_no,...' },
      { id:'skip', label:'건너뛸 행', type:'number', hint:'헤더 행 수', value:'1' }
    ]);
  }
  window.showInboundTemplateModal = showInboundTemplateModal;

  function showPickingTemplateModal() {
    showSettingsDialog('출고 피킹 템플릿 관리', '📦', [
      { id:'name', label:'템플릿 이름', hint:'기본 피킹 리스트' },
      { id:'format', label:'형식', type:'select', options:['Standard PDF','Custom Excel','Barcode List'] },
      { id:'cols', label:'출력 컬럼', hint:'lot_no,product,weight,...' },
      { id:'sort', label:'정렬 기준', type:'select', options:['LOT 번호','제품명','위치','날짜'] }
    ]);
  }
  window.showPickingTemplateModal = showPickingTemplateModal;

  /* ===================================================
     8r. 대량 이동 승인 — 승인 대기 중인 이동 건 목록
     =================================================== */
  function showMoveApprovalQueueModal() {
    showDataModal('✅ 대량 이동 승인','<div style="padding:20px;text-align:center">⏳ Loading...</div>');
    apiGet('/api/q/audit-log').then(function(res){
      var rows = extractRows(res);
      var moves = rows.filter(function(r){ return (r.event_type||'').indexOf('MOVE') >= 0; });
      var html;
      if (!moves.length) {
        html = '<div class="empty">승인 대기 중인 이동 건이 없습니다</div>';
      } else {
        html = '<p style="color:var(--text-muted);font-size:.85rem;margin-bottom:12px">' + moves.length + '건의 이동 기록</p>';
        html += '<table class="data-table"><thead><tr><th>일시</th><th>유형</th><th>상세</th></tr></thead><tbody>';
        html += moves.slice(0,30).map(function(r){
          return '<tr><td>'+escapeHtml(r.timestamp||r.created_at||'-')+'</td><td><span class="tag">'+escapeHtml(r.event_type||'-')+'</span></td><td style="max-width:300px;overflow:hidden;text-overflow:ellipsis">'+escapeHtml(r.event_data||r.detail||'-')+'</td></tr>';
        }).join('');
        html += '</tbody></table>';
      }
      document.getElementById('sqm-modal-content').innerHTML = '<h2 style="margin-bottom:16px">✅ 대량 이동 승인</h2>' + html;
    }).catch(function(e){
      document.getElementById('sqm-modal-content').innerHTML = '<h2>대량 이동 승인</h2><div class="empty">조회 실패</div>';
    });
  }
  window.showMoveApprovalQueueModal = showMoveApprovalQueueModal;

  /* ===================================================
     8s. 문서 변환 (OCR/PDF → Excel/Word)
     =================================================== */
  function showDocConvertModal() {
    var html = [
      '<div style="max-width:520px">',
      '  <h2 style="margin:0 0 12px 0">📷 문서 변환 (OCR/PDF)</h2>',
      '  <p style="color:var(--text-muted);margin:0 0 16px 0;font-size:.9rem">PDF/이미지를 Excel 또는 Word로 변환합니다.</p>',
      '  <div style="display:grid;grid-template-columns:100px 1fr;gap:10px;align-items:center;margin-bottom:16px">',
      '    <label style="font-weight:600">변환 형식</label>',
      '    <select id="dc-format" style="padding:8px;background:var(--bg-hover);color:var(--text);border:1px solid var(--border);border-radius:6px">',
      '      <option value="excel">→ Excel (.xlsx)</option>',
      '      <option value="word">→ Word (.docx)</option>',
      '    </select>',
      '  </div>',
      '  <div id="dc-drop" style="border:2px dashed var(--border);border-radius:8px;padding:32px 16px;text-align:center;background:var(--bg-hover);cursor:pointer;margin-bottom:16px">',
      '    <div style="font-size:2.5rem;margin-bottom:8px">📄</div>',
      '    <div id="dc-name" style="color:var(--text-muted)">클릭 또는 PDF/이미지를 드롭하세요</div>',
      '  </div>',
      '  <input type="file" id="dc-file" accept=".pdf,.png,.jpg,.jpeg,.tiff,.bmp" style="display:none">',
      '  <div style="padding:12px;background:var(--bg-hover);border-radius:6px;margin-bottom:16px;font-size:.85rem;color:var(--warning)">',
      '    💡 이 기능은 서버에 OCR 엔진(Tesseract)이 필요합니다. 미설치 시 텍스트 PDF만 변환 가능합니다.',
      '  </div>',
      '  <div style="display:flex;gap:8px;justify-content:flex-end">',
      '    <button onclick="document.getElementById(\'sqm-modal\').style.display=\'none\'" class="btn btn-ghost">닫기</button>',
      '    <button id="dc-submit" class="btn btn-primary" disabled>변환</button>',
      '  </div>',
      '</div>'
    ].join('\n');
    showDataModal('', html);
    var drop = document.getElementById('dc-drop');
    var fi = document.getElementById('dc-file');
    var nm = document.getElementById('dc-name');
    var sub = document.getElementById('dc-submit');
    var selFile = null;
    function setF(f){
      if (!f) return; selFile = f;
      nm.innerHTML = '✅ <strong>'+escapeHtml(f.name)+'</strong> ('+Math.round(f.size/1024)+' KB)';
      sub.disabled = false;
    }
    drop.addEventListener('click', function(){ fi.click(); });
    fi.addEventListener('change', function(e){ if(e.target.files&&e.target.files[0]) setF(e.target.files[0]); });
    drop.addEventListener('dragover', function(e){ e.preventDefault(); });
    drop.addEventListener('drop', function(e){ e.preventDefault(); if(e.dataTransfer.files&&e.dataTransfer.files[0]) setF(e.dataTransfer.files[0]); });
    sub.addEventListener('click', function(){
      showToast('info', '문서 변환은 Phase 6에서 OCR 엔진 연동 후 지원됩니다');
    });
  }
  window.showDocConvertModal = showDocConvertModal;

  /* ===================================================
     8t. 품목별 재고 요약 — 제품 기준 집계
     =================================================== */
  function showProductSummaryModal() {
    showDataModal('📋 품목별 재고 요약','<div style="padding:20px;text-align:center">⏳ Loading...</div>');
    apiGet('/api/q/product-inventory').then(function(res){
      var rows = extractRows(res);
      // Group by product
      var byProd = {};
      rows.forEach(function(r){
        var p = r.product || '(미지정)';
        if (!byProd[p]) byProd[p] = { lots:0, weight:0, tonbags:0 };
        byProd[p].lots++;
        byProd[p].weight += Number(r.net_weight||0);
        byProd[p].tonbags += Number(r.tonbag_count||r.total_tonbags||0);
      });
      var prods = Object.keys(byProd).sort();
      if (!prods.length) {
        document.getElementById('sqm-modal-content').innerHTML = '<h2>📋 품목별 재고 요약</h2><div class="empty">데이터가 없습니다</div>';
        return;
      }
      var tbl = '<table class="data-table"><thead><tr><th>제품</th><th>LOT 수</th><th>톤백 수</th><th>총 중량(MT)</th></tr></thead><tbody>';
      prods.forEach(function(p){
        var d = byProd[p];
        tbl += '<tr><td style="font-weight:600">'+escapeHtml(p)+'</td><td>'+d.lots+'</td><td>'+d.tonbags+'</td><td class="mono-cell">'+d.weight.toFixed(3)+'</td></tr>';
      });
      tbl += '</tbody></table>';
      document.getElementById('sqm-modal-content').innerHTML = '<h2 style="margin-bottom:16px">📋 품목별 재고 요약</h2><p style="color:var(--text-muted);font-size:.85rem;margin-bottom:12px">' + prods.length + '개 제품, ' + rows.length + '개 LOT</p>' + tbl;
    }).catch(function(e){
      document.getElementById('sqm-modal-content').innerHTML = '<h2>품목별 재고 요약</h2><div class="empty">조회 실패</div>';
    });
  }
  window.showProductSummaryModal = showProductSummaryModal;

  /* ===================================================
     8u. 품목별 LOT 조회 — 제품 선택 → LOT 목록
     =================================================== */
  function showProductLotLookupModal() {
    var html = [
      '<div style="max-width:700px">',
      '  <h2 style="margin:0 0 12px 0">🔍 품목별 LOT 조회</h2>',
      '  <div style="display:flex;gap:8px;margin-bottom:16px;align-items:center">',
      '    <input type="text" id="pll-product" placeholder="제품명 (비우면 전체)" style="flex:1;padding:8px;background:var(--bg-hover);color:var(--text);border:1px solid var(--border);border-radius:6px">',
      '    <button id="pll-search" class="btn btn-primary">조회</button>',
      '  </div>',
      '  <div id="pll-result" style="min-height:60px"><div class="empty">제품명을 입력하고 조회를 클릭하세요</div></div>',
      '  <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:16px">',
      '    <button onclick="document.getElementById(\'sqm-modal\').style.display=\'none\'" class="btn btn-ghost">닫기</button>',
      '  </div>',
      '</div>'
    ].join('\n');
    showDataModal('', html);
    document.getElementById('pll-search').addEventListener('click', function(){
      var prod = document.getElementById('pll-product').value.trim();
      var result = document.getElementById('pll-result');
      result.innerHTML = '<div style="padding:20px;text-align:center">⏳ 조회 중...</div>';
      apiGet('/api/q/product-inventory').then(function(res){
        var rows = extractRows(res);
        if (prod) rows = rows.filter(function(r){ return (r.product||'').toLowerCase().indexOf(prod.toLowerCase()) >= 0; });
        if (!rows.length) { result.innerHTML = '<div class="empty">해당 제품의 LOT가 없습니다</div>'; return; }
        var tbl = '<table class="data-table"><thead><tr><th>LOT</th><th>제품</th><th>상태</th><th>중량(MT)</th><th>톤백수</th><th>입고일</th></tr></thead><tbody>';
        tbl += rows.slice(0,100).map(function(r){
          return '<tr><td class="mono-cell" style="color:var(--accent);cursor:pointer" onclick="showLotDetail(\''+escapeHtml(r.lot_no||'')+'\')">'+escapeHtml(r.lot_no||'-')+'</td><td>'+escapeHtml(r.product||'-')+'</td><td><span class="tag">'+escapeHtml(r.status||'-')+'</span></td><td class="mono-cell">'+(r.net_weight!=null?Number(r.net_weight).toFixed(3):'-')+'</td><td>'+(r.tonbag_count||r.total_tonbags||'-')+'</td><td>'+escapeHtml(r.stock_date||r.inbound_date||'-')+'</td></tr>';
        }).join('');
        tbl += '</tbody></table>';
        result.innerHTML = '<p style="color:var(--text-muted);font-size:.85rem;margin-bottom:8px">' + rows.length + '건</p>' + tbl;
      }).catch(function(e){
        result.innerHTML = '<div class="empty">조회 실패</div>';
      });
    });
  }
  window.showProductLotLookupModal = showProductLotLookupModal;

  /* ===================================================
     8v. 품목별 입출고 현황
     =================================================== */
  function showProductMovementModal() {
    showDataModal('📊 품목별 입출고 현황','<div style="padding:20px;text-align:center">⏳ Loading...</div>');
    apiGet('/api/q/movement-history').then(function(res){
      var rows = extractRows(res);
      // Group by product
      var byProd = {};
      rows.forEach(function(r){
        var p = r.product || '(미지정)';
        if (!byProd[p]) byProd[p] = { inbound:0, outbound:0, return_count:0, move:0 };
        var t = (r.movement_type||'').toUpperCase();
        if (t === 'INBOUND') byProd[p].inbound += Number(r.quantity||r.weight||1);
        else if (t === 'OUTBOUND') byProd[p].outbound += Number(r.quantity||r.weight||1);
        else if (t === 'RETURN') byProd[p].return_count += Number(r.quantity||r.weight||1);
        else byProd[p].move += Number(r.quantity||r.weight||1);
      });
      var prods = Object.keys(byProd).sort();
      if (!prods.length) {
        document.getElementById('sqm-modal-content').innerHTML = '<h2>품목별 입출고</h2><div class="empty">데이터가 없습니다</div>';
        return;
      }
      var tbl = '<table class="data-table"><thead><tr><th>제품</th><th>입고</th><th>출고</th><th>반품</th><th>기타</th></tr></thead><tbody>';
      prods.forEach(function(p){
        var d = byProd[p];
        tbl += '<tr><td style="font-weight:600">'+escapeHtml(p)+'</td><td style="color:var(--success)">'+d.inbound+'</td><td style="color:var(--warning)">'+d.outbound+'</td><td>'+d.return_count+'</td><td>'+d.move+'</td></tr>';
      });
      tbl += '</tbody></table>';
      document.getElementById('sqm-modal-content').innerHTML = '<h2 style="margin-bottom:16px">📊 품목별 입출고 현황</h2>' + tbl;
    }).catch(function(e){
      document.getElementById('sqm-modal-content').innerHTML = '<h2>품목별 입출고</h2><div class="empty">조회 실패</div>';
    });
  }
  window.showProductMovementModal = showProductMovementModal;

  function renderInfoModal(title, endpoint) {
    showDataModal(title,'<div style="padding:20px;text-align:center">Loading...</div>');
    apiGet(endpoint).then(function(res){
      var d=res.data||res||{};
      var html;
      if (typeof d==='string') {
        html='<pre style="white-space:pre-wrap;font-size:.9rem">'+escapeHtml(d)+'</pre>';
      } else if (Array.isArray(d)) {
        html='<table class="data-table"><tbody>'+d.map(function(row){
          if (typeof row==='object'&&row!==null)
            return '<tr>'+Object.values(row).map(function(v){ return '<td>'+escapeHtml(String(v))+'</td>'; }).join('')+'</tr>';
          return '<tr><td>'+escapeHtml(String(row))+'</td></tr>';
        }).join('')+'</tbody></table>';
      } else {
        html='<table class="data-table"><tbody>'+Object.entries(d).map(function(kv){
          return '<tr><td style="font-weight:600;width:40%">'+escapeHtml(kv[0])+'</td><td>'+escapeHtml(String(kv[1]))+'</td></tr>';
        }).join('')+'</tbody></table>';
      }
      document.getElementById('sqm-modal-content').innerHTML='<h2 style="margin-bottom:16px">'+escapeHtml(title)+'</h2>'+html;
    }).catch(function(e){
      document.getElementById('sqm-modal-content').innerHTML='<h2>'+escapeHtml(title)+'</h2><div class="empty">Load failed: '+escapeHtml(e.message||String(e))+'</div>';
    });
  }

  /* =====================================================================
     [Sprint 1-5] LOT Detail 3탭 다이얼로그 — v864-2 lot_detail_dialog.py 매칭
     ───────────────────────────────────────────────────────────────────────
     Tab 1: 📦 톤백 현황 (9 cols)
     Tab 2: 📋 이동 이력 (8 cols, 유형 아이콘)
     Tab 3: 📊 Allocation·배정 (LOT Allocation audit)
     ===================================================================== */
  var _lotDetailState = { lotNo: null, currentTab: 1, data: null, allocations: [] };

  window.showLotDetail = function(lotNo) {
    if (!lotNo) return;
    _lotDetailState.lotNo = lotNo;
    _lotDetailState.currentTab = 1;
    showDataModal('', '<div style="padding:40px;text-align:center;color:var(--text-muted)">⏳ LOT 상세 로딩 중...</div>');

    /* 병렬 fetch: lot-detail + allocation-detail */
    Promise.all([
      apiGet('/api/action/lot-detail/' + encodeURIComponent(lotNo)).catch(function(e){ return { ok:false, error:String(e) }; }),
      apiGet('/api/q/allocation-detail/' + encodeURIComponent(lotNo)).catch(function(){ return { ok:false }; }),
    ]).then(function(results){
      var lotRes = results[0], allocRes = results[1];
      if (!lotRes || lotRes.ok === false) {
        document.getElementById('sqm-modal-content').innerHTML =
          '<h2>LOT Detail: ' + escapeHtml(lotNo) + '</h2>' +
          '<div class="empty" style="padding:30px">조회 실패: ' + escapeHtml(lotRes.error || '데이터 없음') + '</div>';
        return;
      }
      _lotDetailState.data = lotRes.data || {};
      _lotDetailState.allocations = (allocRes && allocRes.data && (allocRes.data.items || allocRes.data.rows)) || extractRows(allocRes) || [];
      _lotDetailRender();
    });
  };

  function _lotDetailRender() {
    var d = _lotDetailState.data || {};
    var lot = d.lot || {};
    var tonbags = d.tonbags || [];
    var movements = d.movements || [];
    var summary = d.summary || {};
    var stats = d.tb_stats || [];
    var lotNo = _lotDetailState.lotNo;

    /* 톤백 상태 집계 헤더 카드 */
    var statCards = ['AVAILABLE', 'RESERVED', 'PICKED', 'SOLD', 'OUTBOUND', 'RETURN'].map(function(s){
      var stat = stats.find(function(x){ return (x.status || '').toUpperCase() === s; });
      var cnt = stat ? stat.cnt : 0;
      var mt  = stat ? (stat.mt || 0) : 0;
      var color = s === 'AVAILABLE' ? '#66bb6a' : s === 'RESERVED' ? '#ffa726' : s === 'PICKED' ? '#42a5f5' : (s === 'SOLD' || s === 'OUTBOUND') ? '#ec407a' : '#9e9e9e';
      return '<div style="background:var(--panel);border:1px solid var(--panel-border);border-left:3px solid ' + color + ';border-radius:4px;padding:6px 10px;font-size:11px;min-width:90px">' +
             '<div style="color:' + color + ';font-weight:700">' + s + '</div>' +
             '<div style="color:var(--fg);font-size:14px;font-weight:700">' + cnt + '개</div>' +
             '<div style="color:var(--text-muted)">' + mt.toFixed(3) + ' MT</div>' +
             '</div>';
    }).join('');

    /* Tab 1: 톤백 현황 (9 cols) */
    var tab1Html = '';
    if (!tonbags.length) {
      tab1Html = '<div style="padding:40px;text-align:center;color:var(--text-muted)">📭 톤백 없음</div>';
    } else {
      var tonbagRows = tonbags.map(function(t, i){
        var st = (t.status || '').toUpperCase();
        var rowClass = st === 'AVAILABLE' ? 'oo-row-avail' :
                       st === 'PICKED' ? 'oo-row-picked' :
                       (st === 'SOLD' || st === 'OUTBOUND') ? 'oo-row-shipped' :
                       st === 'RESERVED' ? 'oo-row-reserved' : '';
        var rowStyle = rowClass === 'oo-row-avail' ? 'background:rgba(102,187,106,.06)' :
                       rowClass === 'oo-row-picked' ? 'background:rgba(66,165,245,.08)' :
                       rowClass === 'oo-row-shipped' ? 'background:rgba(236,64,122,.06)' :
                       rowClass === 'oo-row-reserved' ? 'background:rgba(255,167,38,.08)' : '';
        return '<tr style="' + rowStyle + '">' +
          '<td style="text-align:right">' + (i+1) + '</td>' +
          '<td class="mono-cell" style="color:var(--accent);font-weight:600">' + escapeHtml(t.sub_lt || t.tonbag_no || '-') + '</td>' +
          '<td class="mono-cell" style="text-align:right">' + (t.weight != null ? Number(t.weight).toFixed(2) : '-') + '</td>' +
          '<td><span class="tag">' + escapeHtml(t.status || '-') + '</span></td>' +
          '<td>' + escapeHtml(t.tonbag_no || '-') + '</td>' +
          '<td>' + escapeHtml(t.location || '-') + '</td>' +
          '<td>' + escapeHtml(t.picked_to || '-') + '</td>' +
          '<td class="mono-cell">' + escapeHtml((t.picked_date || '').slice(0, 10)) + '</td>' +
          '<td class="mono-cell">' + escapeHtml((t.outbound_date || '').slice(0, 10)) + '</td>' +
          '</tr>';
      }).join('');
      tab1Html =
        '<table class="data-table" style="font-size:11px"><thead><tr>' +
        '<th>No.</th><th>톤백#</th><th style="text-align:right">중량(kg)</th><th>상태</th><th>구분</th><th>위치</th><th>출고처</th><th>출고지정일</th><th>출고완료일</th>' +
        '</tr></thead><tbody>' + tonbagRows + '</tbody></table>';
    }

    /* Tab 2: 이동 이력 (8 cols, 유형 아이콘) */
    var tab2Html = '';
    if (!movements.length) {
      tab2Html = '<div style="padding:40px;text-align:center;color:var(--text-muted)">📭 이동 이력 없음</div>';
    } else {
      var mvIcon = function(t){
        var s = (t || '').toUpperCase();
        if (s.indexOf('INBOUND') !== -1)  return '📥';
        if (s.indexOf('OUTBOUND') !== -1) return '📤';
        if (s.indexOf('RETURN') !== -1)   return '🔄';
        if (s.indexOf('ADJUST') !== -1)   return '⚙️';
        if (s.indexOf('MOVE') !== -1)     return '🔀';
        if (s.indexOf('PICK') !== -1)     return '🚛';
        return '📋';
      };
      /* 이전/이후 잔량은 백엔드에 없으면 누적 계산 */
      var prevBalance = 0;
      var movementRows = movements.slice().reverse().map(function(m){
        var qty = Number(m.qty_kg) || 0;
        var sign = String(m.movement_type || '').indexOf('OUTBOUND') !== -1 || String(m.movement_type || '').indexOf('PICK') !== -1 ? -1 : 1;
        prevBalance += qty * sign;
        return Object.assign({}, m, { running_balance: prevBalance });
      }).reverse();
      var rows2 = movementRows.map(function(m, i){
        var dt = m.movement_date ? new Date(m.movement_date).toLocaleString('ko-KR') : '-';
        return '<tr>' +
          '<td style="text-align:right">' + (i+1) + '</td>' +
          '<td>' + mvIcon(m.movement_type) + ' ' + escapeHtml(m.movement_type || '-') + '</td>' +
          '<td class="mono-cell" style="font-size:10px">' + escapeHtml(dt) + '</td>' +
          '<td class="mono-cell" style="text-align:right">' + (m.qty_kg != null ? Number(m.qty_kg).toFixed(2) : '-') + '</td>' +
          '<td class="mono-cell" style="text-align:right;color:var(--text-muted)">-</td>' +  /* 이전잔량 */
          '<td class="mono-cell" style="text-align:right">' + Number(m.running_balance).toFixed(2) + '</td>' +
          '<td>' + escapeHtml(m.customer || m.actor || '-') + '</td>' +
          '<td>' + escapeHtml(m.remarks || '-') + '</td>' +
          '</tr>';
      }).join('');
      tab2Html =
        '<table class="data-table" style="font-size:11px"><thead><tr>' +
        '<th>No.</th><th>유형</th><th>일시</th><th style="text-align:right">수량(kg)</th><th style="text-align:right">이전잔량</th><th style="text-align:right">이후잔량</th><th>참조</th><th>비고</th>' +
        '</tr></thead><tbody>' + rows2 + '</tbody></table>';
    }

    /* Tab 3: Allocation·배정 */
    var tab3Html = '';
    var allocs = _lotDetailState.allocations || [];
    if (!allocs.length) {
      tab3Html = '<div style="padding:40px;text-align:center;color:var(--text-muted)">📭 Allocation 정보 없음</div>';
    } else {
      var rows3 = allocs.map(function(a, i){
        return '<tr>' +
          '<td style="text-align:right">' + (i+1) + '</td>' +
          '<td class="mono-cell">' + escapeHtml(a.tonbag_id || a.sub_lt || '-') + '</td>' +
          '<td class="mono-cell" style="text-align:right">' + (a.weight != null ? Number(a.weight).toFixed(2) : '-') + '</td>' +
          '<td>' + escapeHtml(a.location || '-') + '</td>' +
          '<td><span class="tag">' + escapeHtml(a.status || '-') + '</span></td>' +
          '<td class="mono-cell">' + escapeHtml(a.plan_date || a.allocated_date || a.outbound_date || '-') + '</td>' +
          '<td>' + escapeHtml(a.customer || a.sold_to || '-') + '</td>' +
          '<td class="mono-cell">' + escapeHtml(a.sale_ref || '-') + '</td>' +
          '</tr>';
      }).join('');
      tab3Html =
        '<table class="data-table" style="font-size:11px"><thead><tr>' +
        '<th>No.</th><th>톤백 ID</th><th style="text-align:right">중량(kg)</th><th>위치</th><th>상태</th><th>배정일</th><th>고객</th><th>Sale Ref</th>' +
        '</tr></thead><tbody>' + rows3 + '</tbody></table>';
    }

    /* 메인 HTML */
    var html =
      '<div style="max-width:1100px">' +
      '  <h2 style="margin:0 0 8px 0">🔖 LOT 상세 추적 — <span style="color:var(--accent);font-family:Consolas,monospace">' + escapeHtml(lotNo) + '</span></h2>' +
      /* 헤더 정보 */
      '  <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:8px;font-size:12px">' +
      '    <div><span style="color:var(--text-muted)">제품:</span> <strong>' + escapeHtml(lot.product || '-') + '</strong></div>' +
      '    <div><span style="color:var(--text-muted)">SAP:</span> <span class="mono-cell">' + escapeHtml(lot.sap_no || '-') + '</span></div>' +
      '    <div><span style="color:var(--text-muted)">BL:</span> <span class="mono-cell">' + escapeHtml(lot.bl_no || '-') + '</span></div>' +
      '    <div><span style="color:var(--text-muted)">컨테이너:</span> <span class="mono-cell">' + escapeHtml(lot.container_no || '-') + '</span></div>' +
      '    <div><span style="color:var(--text-muted)">상태:</span> <strong>' + escapeHtml(lot.status || '-') + '</strong></div>' +
      '    <div><span style="color:var(--text-muted)">잔량:</span> <strong>' + (lot.current_weight != null ? (lot.current_weight / 1000).toFixed(3) + ' MT' : '-') + '</strong></div>' +
      '    <div><span style="color:var(--text-muted)">입고일:</span> <span class="mono-cell">' + escapeHtml((lot.inbound_date || '').slice(0,10)) + '</span></div>' +
      '    <div><span style="color:var(--text-muted)">창고:</span> <strong>' + escapeHtml(lot.warehouse || '-') + '</strong></div>' +
      '  </div>' +
      /* 상태 집계 카드 */
      '  <div style="display:flex;gap:6px;margin-bottom:10px;flex-wrap:wrap">' + statCards + '</div>' +
      /* 탭 헤더 */
      '  <div style="display:flex;border-bottom:2px solid var(--panel-border);margin-bottom:8px">' +
      '    <button class="lot-tab-btn" data-tab="1" onclick="window.lotSwitchTab(1)" style="padding:8px 16px;background:none;border:none;border-bottom:3px solid transparent;cursor:pointer;color:var(--fg);font-weight:600;font-size:13px">📦 톤백 현황 (' + tonbags.length + '개)</button>' +
      '    <button class="lot-tab-btn" data-tab="2" onclick="window.lotSwitchTab(2)" style="padding:8px 16px;background:none;border:none;border-bottom:3px solid transparent;cursor:pointer;color:var(--fg);font-weight:600;font-size:13px">📋 이동 이력 (' + movements.length + '건)</button>' +
      '    <button class="lot-tab-btn" data-tab="3" onclick="window.lotSwitchTab(3)" style="padding:8px 16px;background:none;border:none;border-bottom:3px solid transparent;cursor:pointer;color:var(--fg);font-weight:600;font-size:13px">📊 Allocation·배정 (' + allocs.length + ')</button>' +
      '  </div>' +
      /* 탭 본문 */
      '  <div style="max-height:340px;overflow-y:auto">' +
      '    <div class="lot-tab-pane" data-pane="1">' + tab1Html + '</div>' +
      '    <div class="lot-tab-pane" data-pane="2" style="display:none">' + tab2Html + '</div>' +
      '    <div class="lot-tab-pane" data-pane="3" style="display:none">' + tab3Html + '</div>' +
      '  </div>' +
      /* 액션 */
      '  <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:12px">' +
      (tonbags.some(function(t){ return (t.status || '').toUpperCase() === 'AVAILABLE'; }) ?
        '    <button class="btn btn-primary" onclick="window.lotQuickOutbound(\'' + escapeHtml(lotNo) + '\')">📤 빠른 출고</button>' : '') +
      '    <button class="btn" onclick="window.lotExportPdf(\'' + escapeHtml(lotNo) + '\')">📋 PDF 출력</button>' +
      '    <button class="btn btn-ghost" onclick="document.getElementById(\'sqm-modal\').style.display=\'none\'">닫기</button>' +
      '  </div>' +
      '</div>';

    document.getElementById('sqm-modal-content').innerHTML = html;
    /* Tab 1 활성 표시 */
    window.lotSwitchTab(_lotDetailState.currentTab || 1);
  }

  window.lotSwitchTab = function(tab) {
    _lotDetailState.currentTab = tab;
    document.querySelectorAll('.lot-tab-btn').forEach(function(b){
      var n = parseInt(b.dataset.tab, 10);
      var active = n === tab;
      b.style.borderBottomColor = active ? 'var(--accent)' : 'transparent';
      b.style.color = active ? 'var(--accent)' : 'var(--fg)';
    });
    document.querySelectorAll('.lot-tab-pane').forEach(function(p){
      var n = parseInt(p.dataset.pane, 10);
      p.style.display = n === tab ? '' : 'none';
    });
  };

  window.lotQuickOutbound = function(lotNo) {
    document.getElementById('sqm-modal').style.display = 'none';
    setTimeout(function(){
      if (typeof showOneStopOutboundModal === 'function') {
        showOneStopOutboundModal();
        setTimeout(function(){
          var lotInput = document.getElementById('oo-lot');
          if (lotInput) lotInput.value = lotNo;
          _ooState.lotNo = lotNo;
          showToast('info', 'LOT ' + lotNo + ' 사전 입력됨 — 출고 정보 입력 후 ▶ 파싱');
        }, 200);
      } else {
        showToast('warn', 'OneStop Outbound 모달 미초기화');
      }
    }, 100);
  };

  window.lotExportPdf = function(lotNo) {
    showToast('info', 'LOT PDF 출력: 기존 보고서 메뉴의 🔖 LOT 상세 PDF 사용 권장 (Sprint 2 통합 예정)');
  };

  /* =====================================================================
     [Sprint 2-C] 전역 🔍 검색 — v864-2 menu_mixin.py 검색 액션 매칭
     모든 도메인 통합 (LOT / Tonbag / Allocation / Audit)
     ===================================================================== */
  var _gsState = { q: '', timer: null };

  function showGlobalSearchModal() {
    var html =
      '<div style="max-width:900px">' +
      '  <h2 style="margin:0 0 12px 0">🔍 전역 검색 — Global Search</h2>' +
      '  <p style="font-size:11px;color:var(--text-muted);margin:0 0 10px 0">검색 대상: LOT NO, SAP NO, BL, Container, Product, Customer, Tonbag UID, Sale Ref, Picking No, Audit 데이터 — 입력 시 실시간 조회</p>' +
      '  <div style="display:flex;gap:6px;margin-bottom:10px">' +
      '    <input type="text" id="gs-input" placeholder="🔍 검색어 입력 (최소 2자) — 예: 1126013063 / ACME / MAEU265083673" autofocus' +
      '      style="flex:1;padding:10px 14px;background:var(--bg);color:var(--fg);border:1px solid var(--accent);border-radius:6px;font-family:Consolas,monospace;font-size:13px">' +
      '    <button class="btn" onclick="window.gsClear()">🧹 초기화</button>' +
      '    <span id="gs-count" style="align-self:center;color:var(--text-muted);font-size:11px;min-width:80px;text-align:right"></span>' +
      '  </div>' +
      '  <div id="gs-results" style="max-height:480px;overflow-y:auto">' +
      '    <div style="padding:40px;text-align:center;color:var(--text-muted);font-size:12px">2글자 이상 입력하면 자동 검색됩니다</div>' +
      '  </div>' +
      '  <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:10px">' +
      '    <span style="margin-right:auto;color:var(--text-muted);font-size:11px">💡 결과 클릭 → 해당 항목으로 이동 / Esc 닫기</span>' +
      '    <button class="btn btn-ghost" onclick="document.getElementById(\'sqm-modal\').style.display=\'none\'">닫기</button>' +
      '  </div>' +
      '</div>';
    showDataModal('', html);

    var inp = document.getElementById('gs-input');
    if (inp) {
      inp.addEventListener('input', function(){
        if (_gsState.timer) clearTimeout(_gsState.timer);
        _gsState.timer = setTimeout(function(){ window.gsRunSearch(inp.value); }, 250);
      });
      inp.addEventListener('keydown', function(e){
        if (e.key === 'Enter') {
          e.preventDefault();
          if (_gsState.timer) clearTimeout(_gsState.timer);
          window.gsRunSearch(inp.value);
        }
      });
    }
  }
  window.showGlobalSearchModal = showGlobalSearchModal;

  window.gsClear = function() {
    var inp = document.getElementById('gs-input');
    if (inp) { inp.value = ''; inp.focus(); }
    _gsState.q = '';
    var cnt = document.getElementById('gs-count');
    if (cnt) cnt.textContent = '';
    var body = document.getElementById('gs-results');
    if (body) body.innerHTML = '<div style="padding:40px;text-align:center;color:var(--text-muted);font-size:12px">2글자 이상 입력하면 자동 검색됩니다</div>';
  };

  window.gsRunSearch = function(q) {
    q = (q || '').trim();
    _gsState.q = q;
    var body = document.getElementById('gs-results');
    var cnt = document.getElementById('gs-count');
    if (q.length < 2) {
      if (body) body.innerHTML = '<div style="padding:40px;text-align:center;color:var(--text-muted);font-size:12px">2글자 이상 입력하면 자동 검색됩니다</div>';
      if (cnt) cnt.textContent = '';
      return;
    }
    if (body) body.innerHTML = '<div style="padding:30px;text-align:center;color:var(--text-muted)">⏳ 검색 중... "' + escapeHtml(q) + '"</div>';

    apiGet('/api/q/global-search?q=' + encodeURIComponent(q) + '&limit=30')
      .then(function(res){
        if (_gsState.q !== q) return;  /* stale response */
        if (!res || !res.ok) throw new Error((res && res.error) || '검색 실패');
        var d = res.data || {};
        if (cnt) cnt.textContent = '총 ' + (d.total || 0) + '건';
        _gsRenderResults(d);
      })
      .catch(function(e){
        if (body) body.innerHTML = '<div style="padding:30px;color:var(--danger);text-align:center">검색 오류: ' + escapeHtml(e.message || String(e)) + '</div>';
      });
  };

  function _gsRenderResults(d) {
    var body = document.getElementById('gs-results');
    if (!body) return;
    var cats = d.categories || {};
    var sections = [];

    /* LOT */
    if (cats.lots && cats.lots.length) {
      var lotsRows = cats.lots.map(function(r){
        var st = (r.status || '').toUpperCase();
        var stColor = st === 'AVAILABLE' ? '#66bb6a' : st === 'RESERVED' ? '#ffa726' : st === 'PICKED' ? '#42a5f5' : '#9e9e9e';
        return '<tr style="cursor:pointer" onclick="window.gsGoLot(\'' + escapeHtml(r.lot_no) + '\')">' +
          '<td class="mono-cell" style="color:var(--accent);font-weight:600">' + escapeHtml(r.lot_no || '-') + '</td>' +
          '<td class="mono-cell">' + escapeHtml(r.sap_no || '-') + '</td>' +
          '<td class="mono-cell">' + escapeHtml(r.bl_no || '-') + '</td>' +
          '<td>' + escapeHtml(r.product || '-') + '</td>' +
          '<td>' + escapeHtml(r.customer || '-') + '</td>' +
          '<td><span class="tag" style="background:' + stColor + ';color:#fff;font-size:10px">' + escapeHtml(r.status || '-') + '</span></td>' +
          '<td class="mono-cell">' + escapeHtml((r.inbound_date || '').slice(0,10)) + '</td>' +
          '</tr>';
      }).join('');
      sections.push(
        '<div style="margin-bottom:12px">' +
        '  <h3 style="font-size:13px;color:var(--accent);margin:0 0 6px 0">📦 Inventory LOT (' + cats.lots.length + ')</h3>' +
        '  <table class="data-table" style="font-size:11px"><thead><tr>' +
        '    <th>LOT NO</th><th>SAP</th><th>BL</th><th>Product</th><th>Customer</th><th>Status</th><th>Inbound</th>' +
        '  </tr></thead><tbody>' + lotsRows + '</tbody></table>' +
        '</div>'
      );
    }

    /* Tonbag */
    if (cats.tonbags && cats.tonbags.length) {
      var tbRows = cats.tonbags.map(function(r){
        return '<tr style="cursor:pointer" onclick="window.gsGoLot(\'' + escapeHtml(r.lot_no) + '\')">' +
          '<td class="mono-cell" style="color:var(--accent)">' + escapeHtml(r.sub_lt || r.tonbag_uid || '-') + '</td>' +
          '<td class="mono-cell">' + escapeHtml(r.lot_no || '-') + '</td>' +
          '<td>' + escapeHtml(r.product || '-') + '</td>' +
          '<td class="mono-cell" style="text-align:right">' + (r.weight != null ? Number(r.weight).toFixed(2) : '-') + '</td>' +
          '<td>' + escapeHtml(r.status || '-') + '</td>' +
          '<td>' + escapeHtml(r.location || '-') + '</td>' +
          '</tr>';
      }).join('');
      sections.push(
        '<div style="margin-bottom:12px">' +
        '  <h3 style="font-size:13px;color:var(--accent);margin:0 0 6px 0">📦 Tonbag (' + cats.tonbags.length + ')</h3>' +
        '  <table class="data-table" style="font-size:11px"><thead><tr>' +
        '    <th>톤백 ID</th><th>LOT</th><th>Product</th><th style="text-align:right">중량(kg)</th><th>Status</th><th>위치</th>' +
        '  </tr></thead><tbody>' + tbRows + '</tbody></table>' +
        '</div>'
      );
    }

    /* Allocation */
    if (cats.allocations && cats.allocations.length) {
      var alRows = cats.allocations.map(function(r){
        return '<tr style="cursor:pointer" onclick="window.gsGoAllocation(\'' + escapeHtml(r.lot_no) + '\')">' +
          '<td class="mono-cell" style="color:var(--accent)">' + escapeHtml(r.lot_no || '-') + '</td>' +
          '<td>' + escapeHtml(r.customer || '-') + '</td>' +
          '<td class="mono-cell">' + escapeHtml(r.sale_ref || '-') + '</td>' +
          '<td class="mono-cell">' + escapeHtml(r.picking_no || '-') + '</td>' +
          '<td class="mono-cell" style="text-align:right">' + (r.qty_mt != null ? Number(r.qty_mt).toFixed(3) : '-') + '</td>' +
          '<td>' + escapeHtml(r.status || '-') + '</td>' +
          '</tr>';
      }).join('');
      sections.push(
        '<div style="margin-bottom:12px">' +
        '  <h3 style="font-size:13px;color:var(--accent);margin:0 0 6px 0">📋 Allocation (' + cats.allocations.length + ')</h3>' +
        '  <table class="data-table" style="font-size:11px"><thead><tr>' +
        '    <th>LOT</th><th>Customer</th><th>Sale Ref</th><th>Picking</th><th style="text-align:right">QTY(MT)</th><th>Status</th>' +
        '  </tr></thead><tbody>' + alRows + '</tbody></table>' +
        '</div>'
      );
    }

    /* Audit */
    if (cats.audits && cats.audits.length) {
      var auRows = cats.audits.map(function(r){
        var t = r.created_at ? new Date(r.created_at).toLocaleString('ko-KR') : '';
        return '<tr>' +
          '<td><span class="tag" style="font-size:10px">' + escapeHtml(r.event_type || '-') + '</span></td>' +
          '<td class="mono-cell" style="font-size:10px">' + escapeHtml(t) + '</td>' +
          '<td class="mono-cell" style="font-size:10px">' + escapeHtml(r.tonbag_id || '-') + '</td>' +
          '<td style="font-size:10px;max-width:280px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="' + escapeHtml(r.event_data || '') + '">' + escapeHtml(r.event_data || '-') + '</td>' +
          '</tr>';
      }).join('');
      sections.push(
        '<div style="margin-bottom:12px">' +
        '  <h3 style="font-size:13px;color:var(--accent);margin:0 0 6px 0">📋 Audit (' + cats.audits.length + ')</h3>' +
        '  <table class="data-table" style="font-size:11px"><thead><tr>' +
        '    <th>이벤트</th><th>시간</th><th>Tonbag</th><th>데이터</th>' +
        '  </tr></thead><tbody>' + auRows + '</tbody></table>' +
        '</div>'
      );
    }

    if (!sections.length) {
      body.innerHTML = '<div style="padding:40px;text-align:center;color:var(--text-muted)">📭 검색 결과 없음 (' + escapeHtml(d.q || '') + ')</div>';
    } else {
      body.innerHTML = sections.join('');
    }
  }

  /* 결과 클릭 → navigate */
  window.gsGoLot = function(lot) {
    if (!lot) return;
    document.getElementById('sqm-modal').style.display = 'none';
    setTimeout(function(){ window.showLotDetail(lot); }, 100);
  };
  window.gsGoAllocation = function(lot) {
    document.getElementById('sqm-modal').style.display = 'none';
    setTimeout(function(){
      renderPage('allocation');
      setTimeout(function(){ window.toggleAllocDetail && window.toggleAllocDetail(lot); }, 300);
    }, 100);
  };

  /* =====================================================================
     [Sprint 2-A] InboundTemplateDialog — v864-2 inbound_template_dialog.py 매칭
     PanedWindow: 좌측 템플릿 목록 + 우측 3-tab 편집 (기본정보/Gemini힌트/메모)
     opts.mode = 'manage' (default) | 'select' | 'create-from-current'
     ===================================================================== */
  var _itState = { mode: 'manage', templates: [], selectedId: null, currentTab: 1 };

  function showInboundTemplateModal(opts) {
    opts = opts || {};
    _itState.mode = opts.mode || 'manage';
    _itState.selectedId = null;
    _itState.currentTab = 1;
    showDataModal('', '<div style="padding:40px;text-align:center;color:var(--text-muted)">⏳ 템플릿 로딩 중...</div>');
    apiGet('/api/inbound/templates')
      .then(function(res){
        var d = (res && res.data) || {};
        _itState.templates = d.items || [];
        _itRender();
      })
      .catch(function(e){
        document.getElementById('sqm-modal-content').innerHTML = '<div class="empty">로드 실패: ' + escapeHtml(e.message || String(e)) + '</div>';
      });
  }
  window.showInboundTemplateModal = showInboundTemplateModal;

  function _itRender() {
    var sel = _itState.templates.find(function(t){ return t.template_id === _itState.selectedId; }) || null;
    var headerExtra = _itState.mode === 'select' ?
      ' <span style="font-size:11px;color:var(--accent)">선택 모드 — 더블클릭 또는 ✅ 적용</span>' :
      _itState.mode === 'create-from-current' ?
      ' <span style="font-size:11px;color:var(--warning)">현재 파싱 설정에서 새 템플릿 생성</span>' : '';

    var listHtml = _itState.templates.length === 0
      ? '<div style="padding:30px;text-align:center;color:var(--text-muted);font-size:12px">📭 템플릿 없음<br><button class="btn btn-primary" onclick="window.itNew()" style="margin-top:10px">➕ 첫 템플릿 만들기</button></div>'
      : _itState.templates.map(function(t){
          var active = t.template_id === _itState.selectedId;
          var bg = active ? 'background:var(--sidebar-active-bg);color:var(--sidebar-active-fg)' : '';
          var inactive = !t.is_active ? '<span style="font-size:9px;background:var(--bg-hover);color:var(--text-muted);padding:1px 4px;border-radius:6px;margin-left:4px">OFF</span>' : '';
          return '<div ondblclick="window.itDoubleClick(\'' + escapeHtml(t.template_id) + '\')" onclick="window.itSelect(\'' + escapeHtml(t.template_id) + '\')" style="padding:8px 10px;border-bottom:1px solid var(--panel-border);cursor:pointer;font-size:12px;' + bg + '">' +
            '<div style="font-weight:600">' + escapeHtml(t.template_name) + inactive + '</div>' +
            '<div style="font-size:10px;color:' + (active ? 'inherit' : 'var(--text-muted)') + '">🚢 ' + escapeHtml(t.carrier_id || '-') + ' · ' + (t.bag_weight_kg || 500) + 'kg · ' + escapeHtml(t.template_id) + '</div>' +
            '</div>';
        }).join('');

    var tab1Html = sel ? _itTab1Form(sel) : _itEmptyForm();
    var tab2Html = sel ? _itTab2Form(sel) : '<div style="padding:30px;text-align:center;color:var(--text-muted)">템플릿을 선택하세요</div>';
    var tab3Html = sel ? _itTab3Form(sel) : '<div style="padding:30px;text-align:center;color:var(--text-muted)">템플릿을 선택하세요</div>';

    var html =
      '<div style="max-width:1100px">' +
      '  <h2 style="margin:0 0 10px 0">📋 입고 파싱 템플릿 관리' + headerExtra + '</h2>' +
      '  <div style="display:grid;grid-template-columns:280px 1fr;gap:10px;height:480px">' +
      /* 좌: 목록 */
      '    <div style="background:var(--panel);border:1px solid var(--panel-border);border-radius:6px;display:flex;flex-direction:column">' +
      '      <div style="padding:6px;display:flex;gap:4px;border-bottom:1px solid var(--panel-border)">' +
      '        <strong style="flex:1;font-size:12px;align-self:center">템플릿 (' + _itState.templates.length + ')</strong>' +
      '        <button class="btn" onclick="window.itNew()" title="신규" style="padding:2px 8px;font-size:11px">➕ 신규</button>' +
      '      </div>' +
      '      <div style="flex:1;overflow-y:auto">' + listHtml + '</div>' +
      '    </div>' +
      /* 우: 편집 */
      '    <div style="background:var(--panel);border:1px solid var(--panel-border);border-radius:6px;display:flex;flex-direction:column">' +
      '      <div style="display:flex;border-bottom:2px solid var(--panel-border)">' +
      '        <button class="lot-tab-btn" data-tab="1" onclick="window.itSwitchTab(1)" style="padding:8px 16px;background:none;border:none;border-bottom:3px solid transparent;cursor:pointer;color:var(--fg);font-weight:600;font-size:13px">📌 기본정보</button>' +
      '        <button class="lot-tab-btn" data-tab="2" onclick="window.itSwitchTab(2)" style="padding:8px 16px;background:none;border:none;border-bottom:3px solid transparent;cursor:pointer;color:var(--fg);font-weight:600;font-size:13px">🤖 Gemini 힌트</button>' +
      '        <button class="lot-tab-btn" data-tab="3" onclick="window.itSwitchTab(3)" style="padding:8px 16px;background:none;border:none;border-bottom:3px solid transparent;cursor:pointer;color:var(--fg);font-weight:600;font-size:13px">📝 메모</button>' +
      '      </div>' +
      '      <div style="flex:1;overflow-y:auto;padding:12px">' +
      '        <div class="lot-tab-pane" data-pane="1">' + tab1Html + '</div>' +
      '        <div class="lot-tab-pane" data-pane="2" style="display:none">' + tab2Html + '</div>' +
      '        <div class="lot-tab-pane" data-pane="3" style="display:none">' + tab3Html + '</div>' +
      '      </div>' +
      '    </div>' +
      '  </div>' +
      /* 액션 */
      '  <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:10px">' +
      (sel ? '<button class="btn btn-danger" onclick="window.itDelete()">🗑️ 삭제</button>' : '') +
      (_itState.mode === 'select' && sel ? '<button class="btn btn-primary" onclick="window.itApply()">✅ 적용</button>' : '') +
      '    <button class="btn btn-primary" onclick="window.itSave()">💾 저장</button>' +
      '    <button class="btn btn-ghost" onclick="document.getElementById(\'sqm-modal\').style.display=\'none\'">닫기</button>' +
      '  </div>' +
      '</div>';

    document.getElementById('sqm-modal-content').innerHTML = html;
    window.lotSwitchTab(_itState.currentTab);  /* 재사용 (같은 패턴) */
  }

  function _itEmptyForm() {
    return '<div style="padding:30px;text-align:center;color:var(--text-muted)"><strong>📋 좌측에서 템플릿 선택</strong><br><br>또는 ➕ 신규 버튼으로 새 템플릿 만들기</div>';
  }

  function _itTab1Form(t) {
    return '<div style="display:grid;grid-template-columns:130px 1fr;gap:8px 10px;align-items:center;font-size:13px">' +
      '<label style="font-weight:600">템플릿 ID:</label>' +
      '<input type="text" id="it-tid" value="' + escapeHtml(t.template_id || '') + '"' + (t.template_id ? ' readonly' : '') + ' style="padding:6px;background:var(--bg-hover);border:1px solid var(--panel-border);border-radius:3px;font-family:Consolas,monospace">' +
      '<label style="font-weight:600">템플릿 이름 *:</label>' +
      '<input type="text" id="it-name" value="' + escapeHtml(t.template_name || '') + '" placeholder="예: MAERSK 리튬카보네이트 500kg" style="padding:6px;background:var(--bg-hover);border:1px solid var(--panel-border);border-radius:3px">' +
      '<label style="font-weight:600">🚢 선사:</label>' +
      '<select id="it-carrier" style="padding:6px;background:var(--bg-hover);border:1px solid var(--panel-border);border-radius:3px">' +
        ['UNKNOWN','MAERSK','MSC','CMA-CGM','EVERGREEN','HMM','ONE','HAPAG-LLOYD','COSCO'].map(function(c){
          return '<option value="' + c + '"' + ((t.carrier_id || 'UNKNOWN') === c ? ' selected' : '') + '>' + c + '</option>';
        }).join('') +
      '</select>' +
      '<label style="font-weight:600">톤백 단가(kg):</label>' +
      '<select id="it-bagweight" style="padding:6px;background:var(--bg-hover);border:1px solid var(--panel-border);border-radius:3px">' +
        '<option value="500"' + (t.bag_weight_kg === 500 ? ' selected' : '') + '>500 kg</option>' +
        '<option value="1000"' + (t.bag_weight_kg === 1000 ? ' selected' : '') + '>1000 kg</option>' +
      '</select>' +
      '<label style="font-weight:600">제품 힌트:</label>' +
      '<input type="text" id="it-product" value="' + escapeHtml(t.product_hint || '') + '" placeholder="예: LITHIUM CARBONATE" style="padding:6px;background:var(--bg-hover);border:1px solid var(--panel-border);border-radius:3px">' +
      '<label style="font-weight:600">중량 형식:</label>' +
      '<select id="it-wfmt" style="padding:6px;background:var(--bg-hover);border:1px solid var(--panel-border);border-radius:3px">' +
        '<option value="EURO"' + ((t.weight_format || 'EURO') === 'EURO' ? ' selected' : '') + '>EURO (1.234,56)</option>' +
        '<option value="US"' + (t.weight_format === 'US' ? ' selected' : '') + '>US (1,234.56)</option>' +
      '</select>' +
      '<label style="font-weight:600">사용 중:</label>' +
      '<label style="font-size:12px"><input type="checkbox" id="it-active"' + (t.is_active != 0 ? ' checked' : '') + '> 이 템플릿 활성화 (OneStop Inbound dropdown에 노출)</label>' +
      '<label style="font-weight:600">BL 형식:</label>' +
      '<input type="text" id="it-blfmt" value="' + escapeHtml(t.bl_format || '') + '" placeholder="예: 숫자9 / 영문3+숫자6" style="padding:6px;background:var(--bg-hover);border:1px solid var(--panel-border);border-radius:3px">' +
    '</div>';
  }

  function _itTab2Form(t) {
    function ta(id, label, val) {
      return '<div style="margin-bottom:10px">' +
        '<label style="font-weight:600;font-size:12px;display:block;margin-bottom:4px">' + label + '</label>' +
        '<textarea id="' + id + '" style="width:100%;min-height:60px;padding:6px;background:var(--bg-hover);color:var(--fg);border:1px solid var(--panel-border);border-radius:3px;font-family:Consolas,monospace;font-size:11px;resize:vertical">' + escapeHtml(val || '') + '</textarea>' +
        '</div>';
    }
    return '<p style="font-size:11px;color:var(--text-muted);margin:0 0 10px 0">💡 Gemini AI 파싱 시 이 힌트 텍스트가 함께 전달됩니다. 선사별 특이사항이나 컬럼 위치 단서를 자유 형식으로 작성하세요.</p>' +
      ta('it-hint-pl', '📦 Packing List 힌트', t.gemini_hint_packing) +
      ta('it-hint-inv', '📄 Invoice 힌트', t.gemini_hint_invoice) +
      ta('it-hint-bl', '🚢 BL 힌트', t.gemini_hint_bl);
  }

  function _itTab3Form(t) {
    return '<label style="font-weight:600;font-size:12px;display:block;margin-bottom:6px">📝 담당자 메모</label>' +
      '<textarea id="it-note" style="width:100%;min-height:240px;padding:8px;background:var(--bg-hover);color:var(--fg);border:1px solid var(--panel-border);border-radius:3px;font-size:12px;resize:vertical">' + escapeHtml(t.note || '') + '</textarea>' +
      '<p style="font-size:11px;color:var(--text-muted);margin-top:6px">자유 형식 메모 — 협력사 연락처, 특이사항, 변경 이력 등</p>';
  }

  /* 핸들러 */
  window.itSelect = function(tid) {
    _itState.selectedId = tid;
    _itRender();
  };
  window.itDoubleClick = function(tid) {
    _itState.selectedId = tid;
    if (_itState.mode === 'select') window.itApply();
    else _itRender();
  };
  window.itSwitchTab = function(tab) {
    _itState.currentTab = tab;
    window.lotSwitchTab(tab);  /* CSS 동일 */
  };
  window.itNew = function() {
    var newT = {
      template_id:   'TPL_' + Date.now().toString(36).toUpperCase(),
      template_name: '',
      carrier_id:    'UNKNOWN',
      bag_weight_kg: 500,
      product_hint:  '',
      weight_format: 'EURO',
      is_active:     1,
    };
    /* 임시로 list 에 prepend */
    _itState.templates.unshift(newT);
    _itState.selectedId = newT.template_id;
    _itRender();
  };
  window.itSave = function() {
    var tid = (document.getElementById('it-tid') || {}).value || '';
    var name = (document.getElementById('it-name') || {}).value || '';
    if (!tid || !name.trim()) { showToast('error', 'ID 와 이름 필수'); return; }
    var payload = {
      template_id:         tid,
      template_name:       name.trim(),
      carrier_id:          (document.getElementById('it-carrier') || {}).value || 'UNKNOWN',
      bag_weight_kg:       parseInt((document.getElementById('it-bagweight') || {}).value || 500, 10),
      product_hint:        (document.getElementById('it-product') || {}).value || '',
      weight_format:       (document.getElementById('it-wfmt') || {}).value || 'EURO',
      bl_format:           (document.getElementById('it-blfmt') || {}).value || '',
      is_active:           (document.getElementById('it-active') || {}).checked,
      gemini_hint_packing: (document.getElementById('it-hint-pl') || {}).value || '',
      gemini_hint_invoice: (document.getElementById('it-hint-inv') || {}).value || '',
      gemini_hint_bl:      (document.getElementById('it-hint-bl') || {}).value || '',
      note:                (document.getElementById('it-note') || {}).value || '',
    };
    /* 신규 vs 수정 — 서버에 같은 ID 가 있는지로 판단 */
    var existing = _itState.templates.find(function(t){ return t.template_id === tid && !t._isNewLocal; });
    /* 임시로 만든 것은 _isNewLocal 플래그 — 위 itNew 에서 처리 안 했으니 그냥 try POST → 409 면 PATCH */
    apiPost('/api/inbound/templates', payload)
      .then(function(res){
        if (res && res.ok) {
          showToast('success', '✅ 신규 저장: ' + payload.template_name);
          showInboundTemplateModal({ mode: _itState.mode });
        } else throw new Error((res && (res.detail || res.error)) || 'fail');
      })
      .catch(function(e){
        if (String(e.message || '').indexOf('409') !== -1 || String(e.message || '').indexOf('중복') !== -1) {
          /* PATCH */
          fetch(API + '/api/inbound/templates/' + encodeURIComponent(tid), {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
          }).then(function(r){ return r.json().then(function(b){ return { ok: r.ok, body: b }; }); })
            .then(function(res){
              if (res.ok && res.body.ok) {
                showToast('success', '💾 수정 저장: ' + payload.template_name);
                showInboundTemplateModal({ mode: _itState.mode });
              } else {
                showToast('error', '저장 실패: ' + JSON.stringify(res.body));
              }
            })
            .catch(function(err){ showToast('error', '저장 오류: ' + err.message); });
        } else {
          showToast('error', '저장 실패: ' + e.message);
        }
      });
  };
  window.itDelete = function() {
    var tid = _itState.selectedId;
    if (!tid) return;
    var t = _itState.templates.find(function(x){ return x.template_id === tid; });
    if (!confirm('🗑️ 템플릿 삭제\n\n' + (t ? t.template_name : tid) + '\n계속하시겠습니까?')) return;
    fetch(API + '/api/inbound/templates/' + encodeURIComponent(tid), { method: 'DELETE' })
      .then(function(r){ return r.json().then(function(b){ return { ok: r.ok, body: b }; }); })
      .then(function(res){
        if (res.ok && res.body.ok) {
          showToast('success', '삭제됨');
          showInboundTemplateModal({ mode: _itState.mode });
        } else {
          showToast('error', '삭제 실패: ' + JSON.stringify(res.body));
        }
      })
      .catch(function(e){ showToast('error', '삭제 오류: ' + e.message); });
  };
  window.itApply = function() {
    var tid = _itState.selectedId;
    if (!tid) return;
    var t = _itState.templates.find(function(x){ return x.template_id === tid; });
    if (!t) return;
    document.getElementById('sqm-modal').style.display = 'none';
    setTimeout(function(){
      /* OneStop Inbound modal 안에 적용 */
      _onestopState.template = t;
      var sel = document.getElementById('onestop-template');
      if (sel) {
        sel.innerHTML = '<option>' + t.carrier_id + ' — ' + t.template_name + ' (' + t.bag_weight_kg + 'kg)</option>';
      }
      var carrierInp = document.getElementById('onestop-carrier');
      if (carrierInp) carrierInp.value = t.carrier_id || '';
      showToast('success', '📋 템플릿 적용: ' + t.template_name);
    }, 100);
  };

  /* =====================================================================
     [Sprint 2] PickingTemplateDialog — v864-2 picking_template_dialog.py 매칭
     InboundTemplate 패턴 재사용 — 단순 단일 폼 (탭 없음, 한 화면 편집)
     ===================================================================== */
  var _ptState = { templates: [], selectedId: null };

  function showPickingTemplateModal() {
    showDataModal('', '<div style="padding:40px;text-align:center;color:var(--text-muted)">⏳ Picking 템플릿 로딩 중...</div>');
    apiGet('/api/outbound/templates')
      .then(function(res){
        var d = (res && res.data) || {};
        _ptState.templates = d.items || [];
        _ptState.selectedId = null;
        _ptRender();
      })
      .catch(function(e){
        document.getElementById('sqm-modal-content').innerHTML = '<div class="empty">로드 실패: ' + escapeHtml(e.message || String(e)) + '</div>';
      });
  }
  window.showPickingTemplateModal = showPickingTemplateModal;

  function _ptRender() {
    var sel = _ptState.templates.find(function(t){ return t.template_id === _ptState.selectedId; }) || null;
    var listHtml = _ptState.templates.length === 0
      ? '<div style="padding:30px;text-align:center;color:var(--text-muted);font-size:12px">📭 템플릿 없음<br><button class="btn btn-primary" onclick="window.ptNew()" style="margin-top:10px">➕ 첫 템플릿 만들기</button></div>'
      : _ptState.templates.map(function(t){
          var active = t.template_id === _ptState.selectedId;
          var bg = active ? 'background:var(--sidebar-active-bg);color:var(--sidebar-active-fg)' : '';
          var inactive = !t.is_active ? '<span style="font-size:9px;background:var(--bg-hover);color:var(--text-muted);padding:1px 4px;border-radius:6px;margin-left:4px">OFF</span>' : '';
          return '<div onclick="window.ptSelect(\'' + escapeHtml(t.template_id) + '\')" style="padding:8px 10px;border-bottom:1px solid var(--panel-border);cursor:pointer;font-size:12px;' + bg + '">' +
            '<div style="font-weight:600">' + escapeHtml(t.template_name) + inactive + '</div>' +
            '<div style="font-size:10px;color:' + (active ? 'inherit' : 'var(--text-muted)') + '">' + escapeHtml(t.customer || '-') + ' · ' + (t.bag_weight_kg || 500) + 'kg · ' + escapeHtml(t.template_id) + '</div>' +
            '</div>';
        }).join('');

    var formHtml = sel ? _ptForm(sel) :
      '<div style="padding:30px;text-align:center;color:var(--text-muted)"><strong>📦 좌측에서 템플릿 선택</strong><br><br>또는 ➕ 신규 버튼으로 새 템플릿 만들기</div>';

    var html =
      '<div style="max-width:1000px">' +
      '  <h2 style="margin:0 0 10px 0">📦 출고 피킹 템플릿 관리</h2>' +
      '  <div style="display:grid;grid-template-columns:280px 1fr;gap:10px;height:480px">' +
      '    <div style="background:var(--panel);border:1px solid var(--panel-border);border-radius:6px;display:flex;flex-direction:column">' +
      '      <div style="padding:6px;display:flex;gap:4px;border-bottom:1px solid var(--panel-border)">' +
      '        <strong style="flex:1;font-size:12px;align-self:center">템플릿 (' + _ptState.templates.length + ')</strong>' +
      '        <button class="btn" onclick="window.ptNew()" style="padding:2px 8px;font-size:11px">➕ 신규</button>' +
      '      </div>' +
      '      <div style="flex:1;overflow-y:auto">' + listHtml + '</div>' +
      '    </div>' +
      '    <div style="background:var(--panel);border:1px solid var(--panel-border);border-radius:6px;padding:14px;overflow-y:auto">' + formHtml + '</div>' +
      '  </div>' +
      '  <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:10px">' +
      (sel ? '<button class="btn btn-danger" onclick="window.ptDelete()">🗑️ 삭제</button>' : '') +
      '    <button class="btn btn-primary" onclick="window.ptSave()">💾 저장</button>' +
      '    <button class="btn btn-ghost" onclick="document.getElementById(\'sqm-modal\').style.display=\'none\'">닫기</button>' +
      '  </div>' +
      '</div>';
    document.getElementById('sqm-modal-content').innerHTML = html;
  }

  function _ptForm(t) {
    function row(label, id, type, val, opts) {
      opts = opts || {};
      if (type === 'textarea') {
        return '<div style="margin-bottom:8px"><label style="font-weight:600;font-size:12px;display:block;margin-bottom:3px">' + label + '</label>' +
          '<textarea id="' + id + '" style="width:100%;min-height:60px;padding:6px;background:var(--bg-hover);color:var(--fg);border:1px solid var(--panel-border);border-radius:3px;font-size:12px;resize:vertical">' + escapeHtml(val || '') + '</textarea></div>';
      }
      if (type === 'select') {
        var optsHtml = opts.options.map(function(o){
          return '<option value="' + escapeHtml(o) + '"' + (val === o ? ' selected' : '') + '>' + escapeHtml(o) + '</option>';
        }).join('');
        return '<div style="display:grid;grid-template-columns:130px 1fr;gap:8px;align-items:center;margin-bottom:6px"><label style="font-weight:600;font-size:12px">' + label + '</label>' +
          '<select id="' + id + '" style="padding:6px;background:var(--bg-hover);border:1px solid var(--panel-border);border-radius:3px">' + optsHtml + '</select></div>';
      }
      if (type === 'checkbox') {
        return '<div style="margin:8px 0"><label style="font-weight:600;font-size:12px"><input type="checkbox" id="' + id + '"' + (val ? ' checked' : '') + '> ' + label + '</label></div>';
      }
      return '<div style="display:grid;grid-template-columns:130px 1fr;gap:8px;align-items:center;margin-bottom:6px"><label style="font-weight:600;font-size:12px">' + label + '</label>' +
        '<input type="' + (type || 'text') + '" id="' + id + '" value="' + escapeHtml(val || '') + '"' + (opts.readonly ? ' readonly' : '') +
        ' placeholder="' + escapeHtml(opts.placeholder || '') + '" style="padding:6px;background:var(--bg-hover);border:1px solid var(--panel-border);border-radius:3px' + (opts.mono ? ';font-family:Consolas,monospace' : '') + '"></div>';
    }
    return row('템플릿 ID', 'pt-tid', 'text', t.template_id, { readonly: !!t.template_id, mono: true }) +
           row('템플릿 이름 *', 'pt-name', 'text', t.template_name, { placeholder: '예: ACME 표준 출고' }) +
           row('고객사 *', 'pt-customer', 'text', t.customer, { placeholder: '예: ACME Corp' }) +
           row('고객 코드', 'pt-cust-code', 'text', t.customer_code, { placeholder: 'C001', mono: true }) +
           row('출항지', 'pt-port-load', 'text', t.port_loading, { placeholder: 'GWANGYANG, SOUTH KOREA' }) +
           row('도착지', 'pt-port-disc', 'text', t.port_discharge, { placeholder: '예: SHANGHAI, CHINA' }) +
           row('Delivery Terms', 'pt-terms', 'select', t.delivery_terms || 'CIF', { options: ['CIF', 'FOB', 'CFR', 'EXW', 'DAP', 'DDP'] }) +
           row('담당자', 'pt-contact', 'text', t.contact_person, { placeholder: '홍길동' }) +
           row('담당자 이메일', 'pt-email', 'email', t.contact_email, { placeholder: 'gd.hong@acme.com' }) +
           row('톤백 단가(kg)', 'pt-bagweight', 'select', String(t.bag_weight_kg || 500), { options: ['500', '1000'] }) +
           row('보관 위치', 'pt-loc', 'text', t.storage_location, { placeholder: '1001 GY logistics' }) +
           row('메모', 'pt-note', 'textarea', t.note) +
           row('사용 중', 'pt-active', 'checkbox', t.is_active != 0);
  }

  /* 핸들러 */
  window.ptSelect = function(tid) { _ptState.selectedId = tid; _ptRender(); };
  window.ptNew = function() {
    var t = {
      template_id:   'PT_' + Date.now().toString(36).toUpperCase(),
      template_name: '',
      customer:      '',
      bag_weight_kg: 500,
      delivery_terms: 'CIF',
      port_loading: 'GWANGYANG, SOUTH KOREA',
      storage_location: '1001 GY logistics',
      is_active:     1,
    };
    _ptState.templates.unshift(t);
    _ptState.selectedId = t.template_id;
    _ptRender();
  };
  window.ptSave = function() {
    var tid = (document.getElementById('pt-tid') || {}).value || '';
    var name = (document.getElementById('pt-name') || {}).value || '';
    var customer = (document.getElementById('pt-customer') || {}).value || '';
    if (!tid || !name.trim() || !customer.trim()) { showToast('error', 'ID/이름/고객사 필수'); return; }
    var payload = {
      template_id:      tid,
      template_name:    name.trim(),
      customer:         customer.trim(),
      customer_code:    (document.getElementById('pt-cust-code') || {}).value || '',
      port_loading:     (document.getElementById('pt-port-load') || {}).value || 'GWANGYANG, SOUTH KOREA',
      port_discharge:   (document.getElementById('pt-port-disc') || {}).value || '',
      delivery_terms:   (document.getElementById('pt-terms') || {}).value || 'CIF',
      contact_person:   (document.getElementById('pt-contact') || {}).value || '',
      contact_email:    (document.getElementById('pt-email') || {}).value || '',
      bag_weight_kg:    parseInt((document.getElementById('pt-bagweight') || {}).value || 500, 10),
      storage_location: (document.getElementById('pt-loc') || {}).value || '1001 GY logistics',
      note:             (document.getElementById('pt-note') || {}).value || '',
      is_active:        (document.getElementById('pt-active') || {}).checked,
    };
    apiPost('/api/outbound/templates', payload)
      .then(function(res){
        if (res && res.ok) {
          showToast('success', '✅ 신규 저장: ' + payload.template_name);
          showPickingTemplateModal();
        } else throw new Error((res && (res.detail || res.error)) || 'fail');
      })
      .catch(function(e){
        if (String(e.message || '').indexOf('409') !== -1 || String(e.message || '').indexOf('중복') !== -1) {
          fetch(API + '/api/outbound/templates/' + encodeURIComponent(tid), {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
          }).then(function(r){ return r.json().then(function(b){ return { ok: r.ok, body: b }; }); })
            .then(function(res){
              if (res.ok && res.body.ok) { showToast('success', '💾 수정됨'); showPickingTemplateModal(); }
              else showToast('error', '저장 실패');
            }).catch(function(err){ showToast('error', err.message); });
        } else {
          showToast('error', '저장 실패: ' + e.message);
        }
      });
  };
  window.ptDelete = function() {
    var tid = _ptState.selectedId;
    if (!tid) return;
    var t = _ptState.templates.find(function(x){ return x.template_id === tid; });
    if (!confirm('🗑️ 삭제\n\n' + (t ? t.template_name : tid) + '\n계속?')) return;
    fetch(API + '/api/outbound/templates/' + encodeURIComponent(tid), { method: 'DELETE' })
      .then(function(r){ return r.json().then(function(b){ return { ok: r.ok, body: b }; }); })
      .then(function(res){
        if (res.ok && res.body.ok) { showToast('success', '삭제됨'); showPickingTemplateModal(); }
        else showToast('error', '삭제 실패');
      });
  };

  /* =====================================================================
     [Sprint 2-R] Sales Order Upload — 단순 multipart Excel/CSV 업로드
     매칭: lot_no → sold_table.sales_order_no UPDATE
     ===================================================================== */
  function showSalesOrderUploadModal() {
    var html =
      '<div style="max-width:700px">' +
      '  <h2 style="margin:0 0 10px 0">📊 Sales Order 업로드</h2>' +
      '  <p style="font-size:11px;color:var(--text-muted);margin:0 0 12px 0">Excel/CSV 업로드 → sold_table 의 매칭 LOT 에 sales_order_no 자동 반영. 컬럼 자동 인식: <code>lot_no</code> + <code>sales_order_no</code> (선택: customer, delivery_date)</p>' +
      '  <input type="file" id="so-input" accept=".xlsx,.xls,.csv" style="display:none" onchange="window.soHandleFile(this.files[0])">' +
      '  <div style="display:flex;gap:8px;margin-bottom:10px">' +
      '    <button class="btn btn-primary" onclick="document.getElementById(\'so-input\').click()">📂 파일 선택 (xlsx/xls/csv)</button>' +
      '    <span id="so-filename" style="align-self:center;color:var(--text-muted);font-size:11px;font-family:Consolas,monospace">선택된 파일 없음</span>' +
      '  </div>' +
      '  <div id="so-result" style="margin-top:10px"></div>' +
      '  <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:14px">' +
      '    <button class="btn btn-ghost" onclick="document.getElementById(\'sqm-modal\').style.display=\'none\'">닫기</button>' +
      '  </div>' +
      '</div>';
    showDataModal('', html);
  }
  window.showSalesOrderUploadModal = showSalesOrderUploadModal;

  /* =====================================================================
     [Sprint 2-Q] InboundHistoryDialog — 모달 형식 입고 이력 조회 + 필터 + Excel
     ===================================================================== */
  var _ihState = { rows: [], stats: null };

  function showInboundHistoryModal() {
    var today = new Date();
    var monthAgo = new Date(today.getTime() - 30 * 86400000);
    var fmt = function(d){ return d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0') + '-' + String(d.getDate()).padStart(2,'0'); };

    var html =
      '<div style="max-width:1100px">' +
      '  <h2 style="margin:0 0 10px 0">📋 입고 현황 조회 (Inbound History)</h2>' +
      /* 필터 */
      '  <div style="display:flex;gap:6px;flex-wrap:wrap;align-items:center;padding:8px 10px;background:var(--panel);border:1px solid var(--panel-border);border-radius:6px;margin-bottom:8px;font-size:12px">' +
      '    <label>From:</label><input type="date" id="ih-from" value="' + fmt(monthAgo) + '" style="padding:3px 6px;background:var(--bg-hover);border:1px solid var(--panel-border);border-radius:3px">' +
      '    <label>To:</label><input type="date" id="ih-to" value="' + fmt(today) + '" style="padding:3px 6px;background:var(--bg-hover);border:1px solid var(--panel-border);border-radius:3px">' +
      '    <label>LOT:</label><input type="text" id="ih-lot" placeholder="LOT NO" style="padding:3px 6px;background:var(--bg-hover);border:1px solid var(--panel-border);border-radius:3px;font-family:Consolas,monospace;width:130px">' +
      '    <label>Product:</label><input type="text" id="ih-product" placeholder="제품명" style="padding:3px 6px;background:var(--bg-hover);border:1px solid var(--panel-border);border-radius:3px;width:150px">' +
      '    <label>Customer:</label><input type="text" id="ih-customer" placeholder="고객사" style="padding:3px 6px;background:var(--bg-hover);border:1px solid var(--panel-border);border-radius:3px;width:120px">' +
      '    <button class="btn" onclick="window.ihSearch()">🔄 조회</button>' +
      '    <button class="btn" onclick="window.ihReset()">✖ 초기화</button>' +
      '    <button class="btn" onclick="window.ihExportCsv()" style="margin-left:auto">📥 Excel 저장</button>' +
      '  </div>' +
      /* 통계 카드 */
      '  <div id="ih-stats" style="font-size:12px;color:var(--text-muted);margin-bottom:8px"></div>' +
      /* 결과 테이블 */
      '  <div id="ih-results" style="max-height:420px;overflow-y:auto;border:1px solid var(--panel-border);border-radius:6px">' +
      '    <div style="padding:30px;text-align:center;color:var(--text-muted)">⏳ 로딩 중...</div>' +
      '  </div>' +
      '  <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:10px">' +
      '    <button class="btn btn-ghost" onclick="document.getElementById(\'sqm-modal\').style.display=\'none\'">닫기</button>' +
      '  </div>' +
      '</div>';
    showDataModal('', html);
    window.ihSearch();  /* 자동 조회 */
  }
  window.showInboundHistoryModal = showInboundHistoryModal;

  window.ihSearch = function() {
    var qs = ['limit=500'];
    var from = (document.getElementById('ih-from') || {}).value || '';
    var to = (document.getElementById('ih-to') || {}).value || '';
    var lot = (document.getElementById('ih-lot') || {}).value || '';
    var prod = (document.getElementById('ih-product') || {}).value || '';
    var cust = (document.getElementById('ih-customer') || {}).value || '';
    if (from) qs.push('from_date=' + encodeURIComponent(from));
    if (to)   qs.push('to_date='   + encodeURIComponent(to));
    if (lot.trim())  qs.push('lot_no='   + encodeURIComponent(lot.trim()));
    if (prod.trim()) qs.push('product='  + encodeURIComponent(prod.trim()));
    if (cust.trim()) qs.push('customer=' + encodeURIComponent(cust.trim()));

    var body = document.getElementById('ih-results');
    var stats = document.getElementById('ih-stats');
    if (body) body.innerHTML = '<div style="padding:30px;text-align:center;color:var(--text-muted)">⏳ 조회 중...</div>';

    apiGet('/api/q/inbound-status?' + qs.join('&'))
      .then(function(res){
        var d = (res && res.data) || {};
        _ihState.rows = d.items || [];
        _ihState.stats = d.stats || {};
        if (stats) {
          stats.innerHTML = '📊 <strong>' + (d.stats.total_lots || 0) + ' LOTs</strong> · ' +
            '현재 잔량 <strong>' + (d.stats.total_current_mt || 0).toFixed(3) + ' MT</strong> · ' +
            '초기 입고 <strong>' + (d.stats.total_initial_mt || 0).toFixed(3) + ' MT</strong>';
        }
        if (!_ihState.rows.length) {
          if (body) body.innerHTML = '<div style="padding:40px;text-align:center;color:var(--text-muted)">📭 조건에 맞는 입고 기록 없음</div>';
          return;
        }
        var rowsHtml = _ihState.rows.map(function(r, i){
          var st = (r.status || '').toUpperCase();
          var stColor = st === 'AVAILABLE' ? '#66bb6a' : st === 'RESERVED' ? '#ffa726' : st === 'PICKED' ? '#42a5f5' : (st === 'SOLD' || st === 'OUTBOUND') ? '#ec407a' : '#9e9e9e';
          return '<tr ondblclick="window.gsGoLot(\'' + escapeHtml(r.lot_no) + '\')" style="cursor:pointer">' +
            '<td style="text-align:right">' + (i + 1) + '</td>' +
            '<td class="mono-cell" style="color:var(--accent);font-weight:600">' + escapeHtml(r.lot_no || '') + '</td>' +
            '<td class="mono-cell">' + escapeHtml(r.sap_no || '-') + '</td>' +
            '<td class="mono-cell">' + escapeHtml(r.bl_no || '-') + '</td>' +
            '<td class="mono-cell">' + escapeHtml(r.container_no || '-') + '</td>' +
            '<td>' + escapeHtml(r.product || '-') + '</td>' +
            '<td>' + escapeHtml(r.customer || '-') + '</td>' +
            '<td class="mono-cell" style="text-align:right">' + ((r.net_weight || 0) / 1000).toFixed(3) + '</td>' +
            '<td class="mono-cell" style="text-align:right">' + ((r.current_weight || 0) / 1000).toFixed(3) + '</td>' +
            '<td class="mono-cell" style="text-align:right">' + (r.tonbag_count || 0) + '</td>' +
            '<td><span class="tag" style="background:' + stColor + ';color:#fff;font-size:10px">' + escapeHtml(r.status || '-') + '</span></td>' +
            '<td class="mono-cell">' + escapeHtml((r.inbound_date || '').slice(0,10)) + '</td>' +
            '<td class="mono-cell">' + escapeHtml((r.arrival_date || '').slice(0,10)) + '</td>' +
            '<td>' + escapeHtml(r.warehouse || '-') + '</td>' +
            '<td>' + escapeHtml(r.vessel || '-') + '</td>' +
            '</tr>';
        }).join('');
        if (body) body.innerHTML =
          '<table class="data-table" style="font-size:11px"><thead style="position:sticky;top:0;background:var(--panel)"><tr>' +
          '<th>#</th><th>LOT NO</th><th>SAP</th><th>BL</th><th>Container</th><th>Product</th><th>Customer</th>' +
          '<th style="text-align:right">초기(MT)</th><th style="text-align:right">잔량(MT)</th><th style="text-align:right">톤백</th>' +
          '<th>Status</th><th>입고일</th><th>도착일</th><th>창고</th><th>Vessel</th>' +
          '</tr></thead><tbody>' + rowsHtml + '</tbody></table>' +
          '<div style="text-align:right;padding:6px 10px;font-size:11px;color:var(--text-muted)">💡 더블클릭 → LOT 상세</div>';
      })
      .catch(function(e){
        if (body) body.innerHTML = '<div style="padding:30px;color:var(--danger);text-align:center">조회 실패: ' + escapeHtml(e.message || String(e)) + '</div>';
      });
  };

  window.ihReset = function() {
    var today = new Date();
    var monthAgo = new Date(today.getTime() - 30 * 86400000);
    var fmt = function(d){ return d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0') + '-' + String(d.getDate()).padStart(2,'0'); };
    var ids = { 'ih-from': fmt(monthAgo), 'ih-to': fmt(today), 'ih-lot': '', 'ih-product': '', 'ih-customer': '' };
    Object.keys(ids).forEach(function(k){ var el = document.getElementById(k); if (el) el.value = ids[k]; });
    window.ihSearch();
  };

  window.ihExportCsv = function() {
    if (!_ihState.rows.length) { showToast('warn', '내보낼 데이터 없음'); return; }
    var headers = ['lot_no','sap_no','bl_no','container_no','product','customer','net_weight_kg','current_weight_kg','tonbag_count','status','inbound_date','arrival_date','warehouse','vessel'];
    function csvEsc(v){ var s = String(v == null ? '' : v); if (/[,"\n]/.test(s)) s = '"' + s.replace(/"/g,'""') + '"'; return s; }
    var lines = [headers.join(',')];
    _ihState.rows.forEach(function(r){
      lines.push(headers.map(function(h){
        var key = h.replace('_kg', '');  /* net_weight_kg → net_weight */
        return csvEsc(r[key]);
      }).join(','));
    });
    var blob = new Blob(['\ufeff' + lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a'); a.href = url;
    var ts = new Date();
    a.download = 'inbound_history_' + ts.getFullYear() + String(ts.getMonth()+1).padStart(2,'0') + String(ts.getDate()).padStart(2,'0') + '_' + String(ts.getHours()).padStart(2,'0') + String(ts.getMinutes()).padStart(2,'0') + '.csv';
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast('success', '📥 ' + a.download + ' (' + _ihState.rows.length + ' LOTs)');
  };

  /* =====================================================================
     [Sprint 2-O] DNCheckDialog — DN 교차검증 (Sales Order vs SQM DB)
     v864-2: dialogs/dn_cross_check_dialog.py (192 lines)
     백엔드 reuse: GET /api/q3/dn-cross-check
     ===================================================================== */
  function showDnCrossCheckModal() {
    showDataModal('', '<div style="padding:40px;text-align:center;color:var(--text-muted)">⏳ DN 교차검증 조회 중...</div>');
    apiGet('/api/q3/dn-cross-check')
      .then(function(res){
        if (!res || !res.ok) throw new Error((res && res.error) || '조회 실패');
        var d = res.data || {};
        var doNoInv = d.do_without_inventory || [];
        var invNoDo = d.inventory_without_do || [];
        var matched = d.matched_count || 0;
        var issues = d.issues_count || 0;

        /* 좌측: DO있음/재고없음 */
        var leftRows = doNoInv.length === 0
          ? '<tr><td colspan="6" style="padding:20px;text-align:center;color:var(--success)">✅ 없음</td></tr>'
          : doNoInv.map(function(r){
              return '<tr style="background:rgba(244,67,54,.08)">' +
                '<td class="mono-cell" style="color:var(--accent)">' + escapeHtml(r.lot_no || '-') + '</td>' +
                '<td class="mono-cell">' + escapeHtml(r.do_no || '-') + '</td>' +
                '<td class="mono-cell">' + escapeHtml(r.bl_no || '-') + '</td>' +
                '<td>' + escapeHtml(r.vessel || '-') + '</td>' +
                '<td class="mono-cell">' + escapeHtml((r.arrival_date || '').slice(0,10)) + '</td>' +
                '<td class="mono-cell" style="text-align:right">' + ((r.gross_weight_kg || 0) / 1000).toFixed(3) + '</td>' +
                '</tr>';
            }).join('');

        /* 우측: 재고있음/DO없음 */
        var rightRows = invNoDo.length === 0
          ? '<tr><td colspan="6" style="padding:20px;text-align:center;color:var(--success)">✅ 없음</td></tr>'
          : invNoDo.map(function(r){
              return '<tr style="background:rgba(255,167,38,.1);cursor:pointer" ondblclick="window.gsGoLot(\'' + escapeHtml(r.lot_no) + '\')">' +
                '<td class="mono-cell" style="color:var(--accent)">' + escapeHtml(r.lot_no || '-') + '</td>' +
                '<td class="mono-cell">' + escapeHtml(r.sap_no || '-') + '</td>' +
                '<td class="mono-cell">' + escapeHtml(r.bl_no || '-') + '</td>' +
                '<td>' + escapeHtml(r.product || '-') + '</td>' +
                '<td><span class="tag">' + escapeHtml(r.status || '-') + '</span></td>' +
                '<td class="mono-cell" style="text-align:right">' + ((r.current_weight || 0) / 1000).toFixed(3) + '</td>' +
                '</tr>';
            }).join('');

        var statusIcon = issues === 0 ? '✅' : '⚠️';
        var statusColor = issues === 0 ? 'var(--success)' : 'var(--warning)';
        var statusText = issues === 0 ? '교차검증 통과 — 불일치 없음' : '⚠️ 불일치 ' + issues + '건 발견';

        var html =
          '<div style="max-width:1200px">' +
          '  <h2 style="margin:0 0 8px 0">🔁 DN 교차검증 (Sales Order vs SQM DB)</h2>' +
          /* 통계 카드 */
          '  <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:8px;margin-bottom:10px">' +
          '    <div style="background:var(--panel);border-left:4px solid var(--success);padding:10px 12px;border-radius:4px">' +
          '      <div style="font-size:11px;color:var(--text-muted);font-weight:600">✅ 매칭 (정상)</div>' +
          '      <div style="font-size:22px;font-weight:700;color:var(--success);margin-top:2px">' + matched + ' LOTs</div>' +
          '    </div>' +
          '    <div style="background:var(--panel);border-left:4px solid var(--danger);padding:10px 12px;border-radius:4px">' +
          '      <div style="font-size:11px;color:var(--text-muted);font-weight:600">🔴 DO 있음 / 재고 없음</div>' +
          '      <div style="font-size:22px;font-weight:700;color:var(--danger);margin-top:2px">' + doNoInv.length + ' LOTs</div>' +
          '    </div>' +
          '    <div style="background:var(--panel);border-left:4px solid var(--warning);padding:10px 12px;border-radius:4px">' +
          '      <div style="font-size:11px;color:var(--text-muted);font-weight:600">🟡 재고 있음 / DO 없음</div>' +
          '      <div style="font-size:22px;font-weight:700;color:var(--warning);margin-top:2px">' + invNoDo.length + ' LOTs</div>' +
          '    </div>' +
          '  </div>' +
          /* 상태 메시지 */
          '  <div style="padding:8px 12px;background:rgba(' + (issues === 0 ? '102,187,106' : '255,167,38') + ',.1);border-left:3px solid ' + statusColor + ';border-radius:4px;margin-bottom:10px;font-size:13px">' +
          statusIcon + ' <strong style="color:' + statusColor + '">' + statusText + '</strong>' +
          '  </div>' +
          /* 사이드-바이-사이드 테이블 */
          '  <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">' +
          '    <div style="background:var(--panel);border:1px solid var(--panel-border);border-radius:6px">' +
          '      <div style="padding:8px 10px;background:rgba(244,67,54,.1);font-weight:700;font-size:12px;color:var(--danger)">🔴 DO 있는데 재고 없는 LOT (' + doNoInv.length + ')</div>' +
          '      <div style="max-height:340px;overflow-y:auto">' +
          '        <table class="data-table" style="font-size:11px"><thead><tr>' +
          '          <th>LOT</th><th>DO</th><th>BL</th><th>Vessel</th><th>도착일</th><th style="text-align:right">중량(MT)</th>' +
          '        </tr></thead><tbody>' + leftRows + '</tbody></table>' +
          '      </div>' +
          '    </div>' +
          '    <div style="background:var(--panel);border:1px solid var(--panel-border);border-radius:6px">' +
          '      <div style="padding:8px 10px;background:rgba(255,167,38,.1);font-weight:700;font-size:12px;color:var(--warning)">🟡 재고 있는데 DO 없는 LOT (' + invNoDo.length + ') — 더블클릭 LOT 상세</div>' +
          '      <div style="max-height:340px;overflow-y:auto">' +
          '        <table class="data-table" style="font-size:11px"><thead><tr>' +
          '          <th>LOT</th><th>SAP</th><th>BL</th><th>Product</th><th>상태</th><th style="text-align:right">잔량(MT)</th>' +
          '        </tr></thead><tbody>' + rightRows + '</tbody></table>' +
          '      </div>' +
          '    </div>' +
          '  </div>' +
          /* 액션 */
          '  <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:10px">' +
          '    <button class="btn" onclick="window.dnRefresh()">🔄 새로고침</button>' +
          '    <button class="btn" onclick="window.dnExportCsv()">📥 Excel 저장</button>' +
          '    <button class="btn btn-ghost" onclick="document.getElementById(\'sqm-modal\').style.display=\'none\'">닫기</button>' +
          '  </div>' +
          '</div>';
        document.getElementById('sqm-modal-content').innerHTML = html;
        window._dnLastResult = d;
      })
      .catch(function(e){
        document.getElementById('sqm-modal-content').innerHTML = '<div class="empty" style="padding:30px">조회 실패: ' + escapeHtml(e.message || String(e)) + '</div>';
      });
  }
  window.showDnCrossCheckModal = showDnCrossCheckModal;
  window.dnRefresh = function() { showDnCrossCheckModal(); };
  /* =====================================================================
     [Sprint 2-P] ReturnStatisticsDialog — 반품 사유 통계 + 월별 추이
     v864-2: dialogs/return_statistics_dialog.py (481 lines)
     백엔드 reuse: GET /api/q2/return-stats
     ===================================================================== */
  function showReturnStatsModal() {
    showDataModal('', '<div style="padding:40px;text-align:center;color:var(--text-muted)">⏳ 반품 통계 조회 중...</div>');
    apiGet('/api/q2/return-stats')
      .then(function(res){
        if (!res || !res.ok) throw new Error((res && res.error) || '조회 실패');
        var d = res.data || {};
        var byReason = d.by_reason || [];
        var monthly = d.monthly_trend || [];
        var total = d.total || { cnt: 0, total_mt: 0 };

        /* 사유별 막대 그래프 (CSS bars) */
        var maxCnt = byReason.reduce(function(m, r){ return Math.max(m, r.cnt || 0); }, 1);
        var reasonBars = byReason.length === 0
          ? '<div style="padding:30px;text-align:center;color:var(--text-muted)">📭 반품 이력 없음</div>'
          : byReason.map(function(r, i){
              var pct = (r.cnt / maxCnt) * 100;
              var hue = (i * 50) % 360;
              return '<div style="margin-bottom:8px">' +
                '<div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:2px">' +
                '<strong>' + escapeHtml(r.reason) + '</strong>' +
                '<span>' + r.cnt + '건 · ' + (r.total_mt || 0).toFixed(3) + ' MT</span>' +
                '</div>' +
                '<div style="background:var(--bg-hover);border-radius:3px;height:18px;overflow:hidden">' +
                '<div style="background:hsl(' + hue + ',60%,55%);height:100%;width:' + pct + '%;transition:width .3s"></div>' +
                '</div>' +
                '</div>';
            }).join('');

        /* 월별 추이 — 간단한 막대 차트 */
        var maxMonthCnt = monthly.reduce(function(m, r){ return Math.max(m, r.cnt || 0); }, 1);
        var monthlyHtml = monthly.length === 0
          ? '<div style="padding:30px;text-align:center;color:var(--text-muted)">월별 데이터 없음</div>'
          : '<div style="display:flex;align-items:flex-end;gap:6px;height:180px;padding:10px;background:var(--bg-hover);border-radius:4px">' +
            monthly.slice().reverse().map(function(m){
              var hpct = (m.cnt / maxMonthCnt) * 100;
              return '<div style="flex:1;display:flex;flex-direction:column;align-items:center;font-size:10px" title="' + escapeHtml(m.month) + ': ' + m.cnt + '건 / ' + (m.total_mt || 0).toFixed(3) + ' MT">' +
                '<div style="background:var(--accent);width:80%;height:' + hpct + '%;min-height:2px;border-radius:2px 2px 0 0"></div>' +
                '<div style="margin-top:3px;color:var(--text-muted);font-family:Consolas,monospace">' + escapeHtml(m.month) + '</div>' +
                '<div style="font-weight:700">' + m.cnt + '</div>' +
                '</div>';
            }).join('') +
            '</div>';

        var html =
          '<div style="max-width:1000px">' +
          '  <h2 style="margin:0 0 8px 0">📊 반품 사유 통계 (Return Statistics)</h2>' +
          /* 전체 요약 */
          '  <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px">' +
          '    <div style="background:var(--panel);border-left:4px solid var(--warning);padding:10px 12px;border-radius:4px">' +
          '      <div style="font-size:11px;color:var(--text-muted);font-weight:600">📦 총 반품 건수</div>' +
          '      <div style="font-size:22px;font-weight:700;color:var(--warning);margin-top:2px">' + (total.cnt || 0) + '건</div>' +
          '    </div>' +
          '    <div style="background:var(--panel);border-left:4px solid #ec407a;padding:10px 12px;border-radius:4px">' +
          '      <div style="font-size:11px;color:var(--text-muted);font-weight:600">⚖️ 총 반품 중량</div>' +
          '      <div style="font-size:22px;font-weight:700;color:#ec407a;margin-top:2px">' + (total.total_mt || 0).toFixed(3) + ' MT</div>' +
          '    </div>' +
          '  </div>' +
          /* 좌우 분할: 사유별 / 월별 */
          '  <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">' +
          '    <div style="background:var(--panel);border:1px solid var(--panel-border);border-radius:6px;padding:12px">' +
          '      <h3 style="font-size:13px;margin:0 0 8px 0">📋 사유별 분포 (' + byReason.length + ')</h3>' +
          '      <div style="max-height:280px;overflow-y:auto">' + reasonBars + '</div>' +
          '    </div>' +
          '    <div style="background:var(--panel);border:1px solid var(--panel-border);border-radius:6px;padding:12px">' +
          '      <h3 style="font-size:13px;margin:0 0 8px 0">📅 월별 추이 (최근 12개월)</h3>' +
          monthlyHtml +
          '    </div>' +
          '  </div>' +
          /* 액션 */
          '  <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:12px">' +
          '    <button class="btn" onclick="window.rsRefresh()">🔄 새로고침</button>' +
          '    <button class="btn" onclick="window.rsExportCsv()">📥 Excel 저장</button>' +
          '    <button class="btn btn-ghost" onclick="document.getElementById(\'sqm-modal\').style.display=\'none\'">닫기</button>' +
          '  </div>' +
          '</div>';
        document.getElementById('sqm-modal-content').innerHTML = html;
        window._rsLastResult = d;
      })
      .catch(function(e){
        document.getElementById('sqm-modal-content').innerHTML = '<div class="empty" style="padding:30px">조회 실패: ' + escapeHtml(e.message || String(e)) + '</div>';
      });
  }
  window.showReturnStatsModal = showReturnStatsModal;
  window.rsRefresh = function() { showReturnStatsModal(); };
  window.rsExportCsv = function() {
    var d = window._rsLastResult || {};
    var lines = ['# 반품 통계 — Total: ' + (d.total ? d.total.cnt + '건 / ' + (d.total.total_mt || 0).toFixed(3) + ' MT' : '0')];
    lines.push('');
    lines.push('## 사유별');
    lines.push('reason,cnt,total_mt');
    function csvEsc(v){ var s = String(v == null ? '' : v); if (/[,"\n]/.test(s)) s = '"' + s.replace(/"/g,'""') + '"'; return s; }
    (d.by_reason || []).forEach(function(r){
      lines.push([csvEsc(r.reason), r.cnt, r.total_mt].join(','));
    });
    lines.push('');
    lines.push('## 월별 추이');
    lines.push('month,cnt,total_mt');
    (d.monthly_trend || []).forEach(function(r){
      lines.push([csvEsc(r.month), r.cnt, r.total_mt].join(','));
    });
    var blob = new Blob(['\ufeff' + lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a'); a.href = url;
    var ts = new Date();
    a.download = 'return_stats_' + ts.getFullYear() + String(ts.getMonth()+1).padStart(2,'0') + String(ts.getDate()).padStart(2,'0') + '.csv';
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast('success', '📥 ' + a.download);
  };

  /* =====================================================================
     [Sprint 2 batch] 작은 다이얼로그들 — placeholder 일괄 활성화
     ===================================================================== */

  /* PDF/이미지 변환 (onDocConvert) — 기존 기능 안내 */
  window.showDocConvertModal = function() {
    showDataModal('', '<div style="max-width:600px;padding:14px">' +
      '<h2>📷 PDF/이미지 변환</h2>' +
      '<p style="font-size:12px">PDF·이미지 파일을 OCR/리사이즈/병합합니다.</p>' +
      '<p style="font-size:11px;color:var(--text-muted)">현재는 PDF 입고/Picking List 업로드 메뉴를 통해 자동 처리됩니다. 별도 변환 도구는 Phase 2에서 추가 예정.</p>' +
      '<div style="display:flex;gap:8px;justify-content:flex-end;margin-top:12px">' +
      '<button class="btn" onclick="window.showOneStopInboundModal()">📥 PDF 스캔 입고로 이동</button>' +
      '<button class="btn btn-ghost" onclick="document.getElementById(\'sqm-modal\').style.display=\'none\'">닫기</button>' +
      '</div></div>');
  };

  /* 제품 마스터 관리 — 기존 기능 안내 + product master 데이터 표시 */
  window.showProductMasterModal = function() {
    showDataModal('', '<div style="padding:30px;text-align:center;color:var(--text-muted)">⏳ 제품 마스터 로딩...</div>');
    apiGet('/api/info/system-info').catch(function(){ return null; }).then(function(){
      apiGet('/api/q/inbound-status?limit=200').catch(function(){ return null; }).then(function(res){
        var rows = ((res && res.data && res.data.items) || []);
        // group by product
        var products = {};
        rows.forEach(function(r){
          if (!r.product) return;
          if (!products[r.product]) products[r.product] = { count: 0, total_kg: 0 };
          products[r.product].count++;
          products[r.product].total_kg += (r.current_weight || 0);
        });
        var rowsHtml = Object.keys(products).sort().map(function(p, i){
          var p2 = products[p];
          return '<tr><td>' + (i+1) + '</td><td><strong>' + escapeHtml(p) + '</strong></td><td style="text-align:right">' + p2.count + ' LOT</td><td class="mono-cell" style="text-align:right">' + (p2.total_kg/1000).toFixed(3) + ' MT</td></tr>';
        }).join('');
        document.getElementById('sqm-modal-content').innerHTML =
          '<div style="max-width:700px"><h2>📦 제품 마스터 관리</h2>' +
          '<p style="font-size:11px;color:var(--text-muted)">현재 inventory 에 존재하는 제품 목록 (집계). 신규 제품 등록은 PDF 입고 시 자동 등록됩니다.</p>' +
          '<table class="data-table" style="font-size:12px"><thead><tr><th>#</th><th>제품명</th><th style="text-align:right">LOT 수</th><th style="text-align:right">총 잔량</th></tr></thead>' +
          '<tbody>' + (rowsHtml || '<tr><td colspan="4" style="padding:30px;text-align:center;color:var(--text-muted)">📭 제품 데이터 없음</td></tr>') + '</tbody></table>' +
          '<div style="display:flex;gap:8px;justify-content:flex-end;margin-top:10px">' +
          '<button class="btn btn-ghost" onclick="document.getElementById(\'sqm-modal\').style.display=\'none\'">닫기</button>' +
          '</div></div>';
      });
    });
  };

  /* 이메일 설정 — Sprint 3 시작 */
  window.showEmailConfigModal = function() {
    var html = '<div style="max-width:600px"><h2>⚙️ 이메일 알림 설정</h2>' +
      '<p style="font-size:11px;color:var(--text-muted)">Gmail SMTP 기준 — 출고/반품 발생 시 자동 이메일 발송. 실제 적용은 백엔드 SMTP 설정 후.</p>' +
      '<div style="display:grid;grid-template-columns:130px 1fr;gap:8px;align-items:center">' +
      '<label><input type="checkbox" id="em-enable"> 이메일 알림 활성화</label><span></span>' +
      '<label>SMTP 서버:</label><input type="text" id="em-smtp" value="smtp.gmail.com" style="padding:6px;background:var(--bg-hover);border:1px solid var(--panel-border);border-radius:3px">' +
      '<label>포트:</label><input type="number" id="em-port" value="587" style="padding:6px;background:var(--bg-hover);border:1px solid var(--panel-border);border-radius:3px">' +
      '<label>Gmail 계정:</label><input type="email" id="em-account" placeholder="user@gmail.com" style="padding:6px;background:var(--bg-hover);border:1px solid var(--panel-border);border-radius:3px">' +
      '<label>앱 비밀번호:</label><input type="password" id="em-pass" placeholder="16자리" style="padding:6px;background:var(--bg-hover);border:1px solid var(--panel-border);border-radius:3px;font-family:Consolas,monospace">' +
      '<label>발신자:</label><input type="email" id="em-from" placeholder="alerts@company.com" style="padding:6px;background:var(--bg-hover);border:1px solid var(--panel-border);border-radius:3px">' +
      '<label>수신자:</label><input type="text" id="em-to" placeholder="kidong@..., admin@..." style="padding:6px;background:var(--bg-hover);border:1px solid var(--panel-border);border-radius:3px">' +
      '<label>회사명:</label><input type="text" id="em-company" value="(주)지와이로지스" style="padding:6px;background:var(--bg-hover);border:1px solid var(--panel-border);border-radius:3px">' +
      '<label>창고명:</label><input type="text" id="em-wh" value="광양 창고" style="padding:6px;background:var(--bg-hover);border:1px solid var(--panel-border);border-radius:3px">' +
      '<label>반품 임계:</label><input type="number" id="em-thresh" value="3" style="padding:6px;background:var(--bg-hover);border:1px solid var(--panel-border);border-radius:3px">' +
      '<label>조회 기간(일):</label><input type="number" id="em-period" value="30" style="padding:6px;background:var(--bg-hover);border:1px solid var(--panel-border);border-radius:3px">' +
      '</div>' +
      '<p style="font-size:10px;color:var(--text-muted);margin-top:10px">💡 Gmail 앱 비밀번호: Google 계정 → 보안 → 앱 비밀번호</p>' +
      '<div style="display:flex;gap:8px;justify-content:flex-end;margin-top:10px">' +
      '<button class="btn" onclick="showToast(\'info\', \'테스트 발송: 백엔드 SMTP 설정 후 활성화 예정\')">📧 테스트 발송</button>' +
      '<button class="btn btn-primary" onclick="showToast(\'info\', \'설정 저장: 백엔드 settings 엔드포인트 확장 후 동작 예정 (현재는 UI만)\')">💾 저장</button>' +
      '<button class="btn btn-ghost" onclick="document.getElementById(\'sqm-modal\').style.display=\'none\'">닫기</button>' +
      '</div></div>';
    showDataModal('', html);
  };

  /* 자동 백업 설정 */
  window.showAutoBackupModal = function() {
    showDataModal('', '<div style="max-width:550px"><h2>⏰ 자동 백업 설정</h2>' +
      '<p style="font-size:11px;color:var(--text-muted)">백업 주기와 보존 기간 설정.</p>' +
      '<div style="display:grid;grid-template-columns:140px 1fr;gap:8px;align-items:center">' +
      '<label><input type="checkbox" id="ab-enable" checked> 자동 백업 활성화</label><span></span>' +
      '<label>백업 주기:</label><select id="ab-interval" style="padding:6px;background:var(--bg-hover);border:1px solid var(--panel-border);border-radius:3px"><option value="hourly">매 시간</option><option value="daily" selected>매일</option><option value="weekly">매주</option></select>' +
      '<label>백업 시각:</label><input type="time" id="ab-time" value="03:00" style="padding:6px;background:var(--bg-hover);border:1px solid var(--panel-border);border-radius:3px">' +
      '<label>보존 기간(일):</label><input type="number" id="ab-keep" value="30" style="padding:6px;background:var(--bg-hover);border:1px solid var(--panel-border);border-radius:3px">' +
      '<label>백업 위치:</label><input type="text" value="data/backups/" readonly style="padding:6px;background:var(--bg-hover);border:1px solid var(--panel-border);border-radius:3px;font-family:Consolas,monospace">' +
      '</div>' +
      '<p style="font-size:10px;color:var(--text-muted);margin-top:10px">💡 즉시 백업: 메뉴 → 파일 → 백업 → 💾 백업 생성</p>' +
      '<div style="display:flex;gap:8px;justify-content:flex-end;margin-top:10px">' +
      '<button class="btn" onclick="dispatchAction(\'onOnBackup\')">💾 즉시 백업 실행</button>' +
      '<button class="btn btn-primary" onclick="showToast(\'info\', \'자동 백업 스케줄러: Phase 2 cron 통합\')">💾 저장</button>' +
      '<button class="btn btn-ghost" onclick="document.getElementById(\'sqm-modal\').style.display=\'none\'">닫기</button>' +
      '</div></div>');
  };

  /* 단축키 가이드 */
  window.showShortcutsModal = function() {
    showDataModal('', '<div style="max-width:600px"><h2>⌨️ 단축키 안내</h2>' +
      '<table class="data-table" style="font-size:12px"><thead><tr><th>키</th><th>동작</th></tr></thead><tbody>' +
      [
        ['Ctrl+R / F5', '현재 페이지 새로고침'],
        ['Ctrl+1', 'Inventory 탭'],
        ['Ctrl+2', 'Allocation 탭'],
        ['Ctrl+3', 'Picked 탭'],
        ['Ctrl+4', 'Outbound 탭'],
        ['Ctrl+5', 'Return 탭'],
        ['Ctrl+6', 'Move 탭'],
        ['Ctrl+7', 'Dashboard'],
        ['Ctrl+8', 'Log 탭'],
        ['Ctrl+9', 'Scan 탭'],
        ['Ctrl+B', '백업 생성'],
        ['Ctrl+E', 'Excel 내보내기'],
        ['Ctrl+I', '정합성 검사'],
        ['Esc', '모달/메뉴 닫기'],
        ['Esc Esc (1.5초내)', '앱 종료 확인'],
        ['Enter (모달 안)', 'Primary 버튼 클릭'],
        ['Tab (모달 안)', '포커스 순환'],
        ['더블클릭 (셀)', '인라인 편집'],
        ['우클릭 (행)', '컨텍스트 메뉴'],
        ['Ctrl+Z (편집 중)', 'Undo (max 50)'],
        ['Ctrl+Y / Ctrl+Shift+Z', 'Redo'],
      ].map(function(r){ return '<tr><td class="mono-cell"><kbd>' + escapeHtml(r[0]) + '</kbd></td><td>' + escapeHtml(r[1]) + '</td></tr>'; }).join('') +
      '</tbody></table>' +
      '<div style="display:flex;justify-content:flex-end;margin-top:10px">' +
      '<button class="btn btn-ghost" onclick="document.getElementById(\'sqm-modal\').style.display=\'none\'">닫기</button></div></div>');
  };

  /* STATUS 가이드 */
  window.showStatusGuideModal = function() {
    showDataModal('', '<div style="max-width:700px"><h2>📊 STATUS 상태값 안내</h2>' +
      '<table class="data-table" style="font-size:12px"><thead><tr><th>상태</th><th>의미</th><th>다음 단계</th></tr></thead><tbody>' +
      [
        ['<span class="tag" style="background:#66bb6a;color:#fff">AVAILABLE</span>', '판매 가능 (입고 완료, 미배정)', '→ RESERVED (배정 등록)'],
        ['<span class="tag" style="background:#ffa726">RESERVED</span>', '판매 배정됨 (예약)', '→ PICKED (화물 결정) / → AVAILABLE (취소)'],
        ['<span class="tag" style="background:#42a5f5;color:#fff">PICKED</span>', '피킹 완료 (출고 준비)', '→ OUTBOUND (출고 확정) / → RESERVED (되돌림)'],
        ['<span class="tag" style="background:#ec407a;color:#fff">OUTBOUND</span>', '출고 진행 중', '→ SOLD (확정) / → RETURN (반품)'],
        ['<span class="tag" style="background:#ec407a;color:#fff">SOLD</span>', '판매 완료 (확정)', '→ RETURN (반품 시)'],
        ['<span class="tag" style="background:#9e9e9e;color:#fff">RETURN</span>', '반품 처리 중', '→ AVAILABLE (재입고)'],
      ].map(function(r){ return '<tr><td>' + r[0] + '</td><td>' + escapeHtml(r[1]) + '</td><td style="font-size:11px">' + escapeHtml(r[2]) + '</td></tr>'; }).join('') +
      '</tbody></table>' +
      '<p style="font-size:11px;color:var(--text-muted);margin-top:10px">📷 Scan 탭의 5개 버튼을 통해 상태 전환 가능. 잘못된 source state시 ⛔ 가드.</p>' +
      '<div style="display:flex;justify-content:flex-end;margin-top:10px">' +
      '<button class="btn btn-ghost" onclick="document.getElementById(\'sqm-modal\').style.display=\'none\'">닫기</button></div></div>');
  };

  /* 도움말 / About */
  window.showHelpModal = function() {
    showDataModal('', '<div style="max-width:700px"><h2>📖 SQM 재고관리 시스템 사용법</h2>' +
      '<h3 style="font-size:13px;margin-top:14px">🎯 주요 워크플로우</h3>' +
      '<ol style="font-size:12px;padding-left:18px;line-height:1.6">' +
      '<li><strong>📥 입고</strong>: 메뉴 → 입고 → 📄 PDF 스캔 입고 → 4종 PDF (BL/PL/Invoice/DO) 업로드 → 18열 미리보기 편집 → 📤 DB 업로드</li>' +
      '<li><strong>📋 배정</strong>: Allocation 탭에서 LOT별 9열 편집 + 7버튼 (예약 실행/취소/PICKED 전환/SOLD 확정 등)</li>' +
      '<li><strong>🚀 출고</strong>: 메뉴 → 출고 → 🚀 즉시 출고 (원스톱) → 4탭 wizard (입력 → 톤백 선택 → OUT 스캔 검증 → 완료)</li>' +
      '<li><strong>📷 바코드 스캔</strong>: Scan 탭 5단계 상태 전환 + ⚡ 빠른 스캔 + 🔕 무음 모드</li>' +
      '<li><strong>📊 정합성</strong>: 메뉴 → 입고 → 🔍 정합성 검증 → 6 카드 + 신호등 + 자동 복구</li>' +
      '</ol>' +
      '<h3 style="font-size:13px;margin-top:14px">🔍 자주 쓰는 메뉴</h3>' +
      '<ul style="font-size:12px;padding-left:18px;line-height:1.6">' +
      '<li>🔍 <strong>전역 검색</strong>: 메뉴바의 🔍 버튼 — 4 도메인 통합 검색</li>' +
      '<li>📋 <strong>입고 현황</strong>: 메뉴 → 입고 → 📋 입고 현황 조회</li>' +
      '<li>🔁 <strong>DN 교차검증</strong>: 메뉴 → 보고서 → 🔍 DN 교차검증</li>' +
      '<li>📊 <strong>반품 통계</strong>: 메뉴 → 입고 → 📊 반품 사유 통계</li>' +
      '</ul>' +
      '<div style="display:flex;gap:8px;justify-content:flex-end;margin-top:14px">' +
      '<button class="btn" onclick="window.showShortcutsModal()">⌨️ 단축키</button>' +
      '<button class="btn" onclick="window.showStatusGuideModal()">📊 STATUS 가이드</button>' +
      '<button class="btn btn-ghost" onclick="document.getElementById(\'sqm-modal\').style.display=\'none\'">닫기</button></div></div>');
  };

  window.showAboutModal = function() {
    showDataModal('', '<div style="max-width:500px;text-align:center;padding:20px"><h2>📦 SQM 재고관리 시스템</h2>' +
      '<p style="font-size:24px;font-weight:700;color:var(--accent);margin:20px 0">v8.6.4.3</p>' +
      '<p style="font-size:12px;color:var(--text-muted)">WebView Edition (FastAPI + pywebview)</p>' +
      '<hr style="border:0;border-top:1px solid var(--panel-border);margin:20px 0">' +
      '<p style="font-size:11px">v864-2 (Tkinter) 의 모든 기능을 WebView 로 포팅한 버전입니다.</p>' +
      '<p style="font-size:10px;color:var(--text-muted);margin-top:10px">Powered by Claude Code · 한국어 지원 · Windows/Mac 호환</p>' +
      '<div style="display:flex;justify-content:center;margin-top:20px">' +
      '<button class="btn btn-primary" onclick="document.getElementById(\'sqm-modal\').style.display=\'none\'">확인</button></div></div>');
  };

  window.showSystemInfoModal = function() {
    apiGet('/api/info/system-info').catch(function(){ return null; }).then(function(res){
      var d = (res && res.data) || res || {};
      var rows = Object.entries(d).map(function(kv){
        return '<tr><td style="font-weight:600">' + escapeHtml(kv[0]) + '</td><td class="mono-cell" style="font-size:11px">' + escapeHtml(String(kv[1])) + '</td></tr>';
      }).join('');
      showDataModal('', '<div style="max-width:600px"><h2>ℹ️ 시스템 정보</h2>' +
        '<table class="data-table" style="font-size:11px"><tbody>' + rows + '</tbody></table>' +
        '<div style="display:flex;justify-content:flex-end;margin-top:10px">' +
        '<button class="btn btn-ghost" onclick="document.getElementById(\'sqm-modal\').style.display=\'none\'">닫기</button></div></div>');
    });
  };

  /* =====================================================================
     [Sprint 2-B] Settings + Carrier Rules — v864-2 SettingsDialogMixin (869줄)
     ===================================================================== */
  var _settingsState = { tab: 'api', apiKeys: null, rules: [] };

  function showSettingsModal(initialTab) {
    _settingsState.tab = initialTab === 'carrier' ? 'carrier' : 'api';
    showDataModal('', '<div style="padding:40px;text-align:center;color:var(--text-muted)">⏳ 설정 로딩 중...</div>');
    Promise.all([
      apiGet('/api/settings/api-keys').catch(function(){ return null; }),
      apiGet('/api/settings/carrier-rules').catch(function(){ return null; }),
    ]).then(function(results){
      _settingsState.apiKeys = (results[0] && results[0].data) || null;
      _settingsState.rules = ((results[1] && results[1].data && results[1].data.items) || []);
      _settingsRender();
    });
  }
  window.showSettingsModal = showSettingsModal;

  function _settingsRender() {
    var t = _settingsState.tab;
    var html =
      '<div style="max-width:1000px">' +
      '  <h2 style="margin:0 0 8px 0">⚙️ 설정 (Settings)</h2>' +
      '  <div style="display:flex;border-bottom:2px solid var(--panel-border);margin-bottom:10px">' +
      '    <button onclick="window.settingsTab(\'api\')" style="padding:8px 16px;background:none;border:none;border-bottom:3px solid ' + (t==='api'?'var(--accent)':'transparent') + ';cursor:pointer;color:' + (t==='api'?'var(--accent)':'var(--fg)') + ';font-weight:600;font-size:13px">🔐 API 키</button>' +
      '    <button onclick="window.settingsTab(\'carrier\')" style="padding:8px 16px;background:none;border:none;border-bottom:3px solid ' + (t==='carrier'?'var(--accent)':'transparent') + ';cursor:pointer;color:' + (t==='carrier'?'var(--accent)':'var(--fg)') + ';font-weight:600;font-size:13px">🚢 선사 BL/DO 규칙</button>' +
      '  </div>' +
      '  <div style="max-height:500px;overflow-y:auto">' +
      (t === 'api' ? _settingsRenderApiKeys() : _settingsRenderCarrierRules()) +
      '  </div>' +
      '  <div style="display:flex;justify-content:flex-end;margin-top:10px">' +
      '    <button class="btn btn-ghost" onclick="document.getElementById(\'sqm-modal\').style.display=\'none\'">닫기</button>' +
      '  </div>' +
      '</div>';
    document.getElementById('sqm-modal-content').innerHTML = html;
  }

  function _settingsRenderApiKeys() {
    var d = _settingsState.apiKeys || {};
    function row(svc, info, displayName) {
      var src = info.source || (info.configured ? 'KEYRING' : '(없음)');
      var srcColor = src === 'ENV' ? 'var(--success)' : src === 'KEYRING' ? 'var(--info, #42a5f5)' : src === 'INI' ? 'var(--warning)' : 'var(--text-muted)';
      return '<div style="background:var(--panel);border:1px solid var(--panel-border);border-radius:6px;padding:12px;margin-bottom:8px">' +
        '<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px">' +
        '<strong style="font-size:14px">' + displayName + '</strong>' +
        '<span style="font-size:11px;color:' + srcColor + ';font-weight:700">📍 ' + src + '</span>' +
        '<span style="font-size:11px;color:var(--text-muted);font-family:Consolas,monospace">' + (info.masked || '-') + '</span>' +
        '<span style="margin-left:auto;font-size:10px;color:var(--text-muted)">model: ' + (info.model || '-') + '</span>' +
        '</div>' +
        '<div style="display:flex;gap:6px;align-items:center">' +
        '<input type="password" id="set-key-' + svc + '" placeholder="새 API 키 입력 (keyring에 안전 저장)" style="flex:1;padding:6px 8px;background:var(--bg-hover);border:1px solid var(--panel-border);border-radius:3px;font-size:12px;font-family:Consolas,monospace">' +
        '<button class="btn" onclick="window.settingsSaveKey(\'' + svc + '\')">💾 저장</button>' +
        (info.configured ? '<button class="btn btn-danger" onclick="window.settingsDeleteKey(\'' + svc + '\')">🗑️ 삭제</button>' : '') +
        '</div>' +
        '</div>';
    }
    return '<p style="font-size:11px;color:var(--text-muted)">💡 우선순위: 환경변수(ENV) > keyring > settings.ini. keyring 사용 권장 (OS 자격증명 보관소).</p>' +
      row('gemini', d.gemini || {}, '🤖 Google Gemini') +
      row('openai', d.openai || {}, '🔵 OpenAI') +
      '<div style="background:var(--panel);border:1px solid var(--panel-border);border-radius:6px;padding:12px;margin-bottom:8px">' +
        '<strong>🔌 Anthropic Claude</strong> ' +
        '<span style="font-size:11px;color:var(--text-muted)">(현재 미사용 — Phase 2 예정)</span>' +
      '</div>';
  }

  function _settingsRenderCarrierRules() {
    var rules = _settingsState.rules;
    var byCarrier = {};
    rules.forEach(function(r){
      if (!byCarrier[r.carrier_id]) byCarrier[r.carrier_id] = [];
      byCarrier[r.carrier_id].push(r);
    });
    var carriers = Object.keys(byCarrier).sort();

    var groupsHtml = '';
    if (carriers.length === 0) {
      groupsHtml = '<div style="padding:30px;text-align:center;color:var(--text-muted)">📭 등록된 규칙 없음</div>';
    } else {
      groupsHtml = carriers.map(function(c){
        var rs = byCarrier[c];
        var rows = rs.map(function(r){
          var dtColor = r.doc_type === 'BL' ? '#42a5f5' : r.doc_type === 'DO' ? '#66bb6a' : r.doc_type === 'PL' ? '#ffa726' : '#ec407a';
          return '<tr' + (r.is_active ? '' : ' style="opacity:.5"') + '>' +
            '<td><span class="tag" style="background:' + dtColor + ';color:#fff;font-size:10px">' + escapeHtml(r.doc_type) + '</span></td>' +
            '<td><strong>' + escapeHtml(r.rule_name) + '</strong></td>' +
            '<td class="mono-cell" style="font-size:10px">' + escapeHtml(r.pattern || '-') + '</td>' +
            '<td style="font-size:10px;color:var(--text-muted)">' + escapeHtml(r.description || '-') + '</td>' +
            '<td class="mono-cell" style="font-size:10px">' + escapeHtml(r.sample_value || '-') + '</td>' +
            '<td style="text-align:center"><button class="btn" style="padding:2px 6px;font-size:10px" onclick="window.crEdit(' + r.id + ')">✏️</button> <button class="btn btn-danger" style="padding:2px 6px;font-size:10px" onclick="window.crDelete(' + r.id + ')">🗑️</button></td>' +
            '</tr>';
        }).join('');
        return '<div style="margin-bottom:10px"><h3 style="font-size:13px;margin:0 0 4px 0">🚢 ' + escapeHtml(c) + ' (' + rs.length + ')</h3>' +
          '<table class="data-table" style="font-size:11px"><thead><tr><th>Doc</th><th>이름</th><th>패턴</th><th>설명</th><th>예시</th><th>작업</th></tr></thead><tbody>' + rows + '</tbody></table></div>';
      }).join('');
    }

    return '<div style="margin-bottom:10px"><button class="btn btn-primary" onclick="window.crNew()">➕ 규칙 추가</button></div>' + groupsHtml;
  }

  window.settingsTab = function(t) { _settingsState.tab = t; _settingsRender(); };
  window.settingsSaveKey = function(svc) {
    var inp = document.getElementById('set-key-' + svc);
    if (!inp || !inp.value.trim()) { showToast('warn', 'API 키 입력하세요'); return; }
    apiPost('/api/settings/api-keys', { service: svc, api_key: inp.value.trim() })
      .then(function(){ showToast('success', svc + ' 키 저장됨 (keyring) — 앱 재시작 시 적용'); inp.value=''; showSettingsModal('api'); })
      .catch(function(e){ showToast('error', '저장 실패: ' + (e.message||String(e))); });
  };
  window.settingsDeleteKey = function(svc) {
    if (!confirm(svc + ' API 키 삭제?')) return;
    fetch(API + '/api/settings/api-keys/' + svc, { method: 'DELETE' })
      .then(function(r){ return r.json(); })
      .then(function(res){ if (res.ok) { showToast('success', '삭제됨'); showSettingsModal('api'); } else showToast('error', '실패'); });
  };
  window.crNew = function() {
    var carrier = prompt('선사 ID (예: MAERSK)'); if (!carrier) return;
    var doc = prompt('Doc Type (BL/DO/PL/INVOICE)'); if (!doc) return;
    var name = prompt('규칙 이름 (예: BL 번호 9자리)'); if (!name) return;
    var pattern = prompt('패턴 (regex 또는 자유 텍스트, 선택)') || '';
    var desc = prompt('설명 (선택)') || '';
    var sample = prompt('예시 값 (선택)') || '';
    apiPost('/api/settings/carrier-rules', {
      carrier_id: carrier, doc_type: doc, rule_name: name,
      pattern: pattern, description: desc, sample_value: sample,
    })
      .then(function(){ showToast('success', '규칙 생성됨'); showSettingsModal('carrier'); })
      .catch(function(e){ showToast('error', '실패: ' + e.message); });
  };
  window.crEdit = function(id) {
    var r = _settingsState.rules.find(function(x){ return x.id === id; });
    if (!r) return;
    var name = prompt('규칙 이름', r.rule_name); if (name === null) return;
    var pattern = prompt('패턴', r.pattern || ''); if (pattern === null) return;
    var desc = prompt('설명', r.description || ''); if (desc === null) return;
    fetch(API + '/api/settings/carrier-rules/' + id, {
      method: 'PATCH',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify({ rule_name: name, pattern: pattern, description: desc }),
    }).then(function(rr){ return rr.json(); })
      .then(function(res){ if (res.ok) { showToast('success', '수정됨'); showSettingsModal('carrier'); } else showToast('error', '실패'); });
  };
  window.crDelete = function(id) {
    if (!confirm('이 규칙 삭제?')) return;
    fetch(API + '/api/settings/carrier-rules/' + id, { method: 'DELETE' })
      .then(function(r){ return r.json(); })
      .then(function(res){ if (res.ok) { showToast('success', '삭제됨'); showSettingsModal('carrier'); } else showToast('error', '실패'); });
  };

  /* =====================================================================
     [Sprint 2] Swap 리포트 — 출고 swap 이력 간단 조회
     ===================================================================== */
  function showSwapReportModal() {
    showDataModal('', '<div style="padding:40px;text-align:center;color:var(--text-muted)">⏳ Swap 이력 조회 중...</div>');
    apiGet('/api/q/audit-log?event_type=SWAP&limit=200').catch(function(){ return null; })
      .then(function(res){
        var items = ((res && res.data && res.data.items) || []);
        var rows = items.length === 0
          ? '<tr><td colspan="5" style="padding:30px;text-align:center;color:var(--text-muted)">📭 Swap 이력 없음</td></tr>'
          : items.map(function(it){
              return '<tr><td class="mono-cell" style="font-size:10px">' + escapeHtml((it.created_at || '').slice(0, 19)) + '</td>' +
                '<td class="mono-cell">' + escapeHtml(it.tonbag_id || '-') + '</td>' +
                '<td>' + escapeHtml(it.event_type || '-') + '</td>' +
                '<td style="font-size:10px">' + escapeHtml(it.event_data || '-') + '</td>' +
                '<td>' + escapeHtml(it.created_by || '-') + '</td></tr>';
            }).join('');
        document.getElementById('sqm-modal-content').innerHTML =
          '<div style="max-width:900px"><h2>🔁 Swap 리포트</h2>' +
          '<p style="font-size:11px;color:var(--text-muted)">audit_log 의 SWAP 이벤트 — Sprint 2 정식 SwapReport 다이얼로그는 향후 별도 구현 예정. 임시로 audit 기반 표시.</p>' +
          '<table class="data-table" style="font-size:11px"><thead><tr><th>시간</th><th>Tonbag</th><th>이벤트</th><th>데이터</th><th>By</th></tr></thead><tbody>' + rows + '</tbody></table>' +
          '<div style="display:flex;gap:8px;justify-content:flex-end;margin-top:10px">' +
          '<button class="btn" onclick="window.ooViewAuditLog()">📋 풀 감사 로그</button>' +
          '<button class="btn btn-ghost" onclick="document.getElementById(\'sqm-modal\').style.display=\'none\'">닫기</button>' +
          '</div></div>';
      });
  }
  window.showSwapReportModal = showSwapReportModal;

  /* =====================================================================
     [Sprint 2] 재고 알림 조회 — 로우 스톡, 장기 재고, 유통 기한
     ===================================================================== */
  function showStockAlertsModal() {
    showDataModal('', '<div style="padding:40px;text-align:center;color:var(--text-muted)">⏳ 재고 알림 조회 중...</div>');
    apiGet('/api/dashboard/alerts').catch(function(){ return null; })
      .then(function(res){
        var items = (res && (res.data || res.alerts)) || [];
        if (!Array.isArray(items)) items = [];
        var rows = items.length === 0
          ? '<div style="padding:30px;text-align:center;color:var(--success);font-weight:700">✅ 알림 없음 — 재고 상태 정상</div>'
          : '<ul style="margin:0;padding:0;list-style:none">' +
            items.map(function(a){
              var sev = (a.severity || 'info').toLowerCase();
              var color = sev === 'error' ? 'var(--danger)' : sev === 'warning' ? 'var(--warning)' : 'var(--info, #42a5f5)';
              return '<li style="padding:8px 12px;background:rgba(' + (sev==='error'?'244,67,54':sev==='warning'?'255,167,38':'66,165,245') + ',.1);border-left:3px solid ' + color + ';border-radius:4px;margin-bottom:6px;display:flex;gap:10px;align-items:center">' +
                '<span style="font-size:18px">' + (a.icon ? '' : (sev==='error'?'🚫':sev==='warning'?'⚠️':'ℹ️')) + (a.icon || '') + '</span>' +
                '<span style="flex:1;font-size:12px">' + escapeHtml(a.text || a.message || '') + '</span>' +
                (a.link ? '<a href="' + escapeHtml(a.link) + '" style="color:' + color + ';font-size:11px;font-weight:700">Go →</a>' : '') +
                '</li>';
            }).join('') + '</ul>';
        document.getElementById('sqm-modal-content').innerHTML =
          '<div style="max-width:700px"><h2>🔔 재고 알림 조회</h2>' +
          '<p style="font-size:11px;color:var(--text-muted)">로우 스톡 / 장기 재고 / 유통기한 / 정합성 이슈 등을 통합 표시.</p>' +
          rows +
          '<div style="display:flex;gap:8px;justify-content:flex-end;margin-top:10px">' +
          '<button class="btn" onclick="window.showStockAlertsModal()">🔄 새로고침</button>' +
          '<button class="btn" onclick="window.showIntegrityV760Modal()">🩺 정합성 검증</button>' +
          '<button class="btn btn-ghost" onclick="document.getElementById(\'sqm-modal\').style.display=\'none\'">닫기</button>' +
          '</div></div>';
      });
  }
  window.showStockAlertsModal = showStockAlertsModal;

  window.dnExportCsv = function() {
    var d = window._dnLastResult || {};
    var headers = ['type','lot_no','do_no','bl_no','sap_no','product','vessel','status','arrival_or_inbound','weight_kg'];
    function csvEsc(v){ var s = String(v == null ? '' : v); if (/[,"\n]/.test(s)) s = '"' + s.replace(/"/g,'""') + '"'; return s; }
    var lines = [headers.join(',')];
    (d.do_without_inventory || []).forEach(function(r){
      lines.push([
        'DO있음_재고없음', csvEsc(r.lot_no), csvEsc(r.do_no), csvEsc(r.bl_no), '', '', csvEsc(r.vessel),
        '', csvEsc(r.arrival_date), csvEsc(r.gross_weight_kg)
      ].join(','));
    });
    (d.inventory_without_do || []).forEach(function(r){
      lines.push([
        '재고있음_DO없음', csvEsc(r.lot_no), '', csvEsc(r.bl_no), csvEsc(r.sap_no), csvEsc(r.product), '',
        csvEsc(r.status), csvEsc(r.inbound_date), csvEsc(r.current_weight)
      ].join(','));
    });
    var blob = new Blob(['\ufeff' + lines.join('\n')], { type: 'text/csv;charset=utf-8;' });
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a'); a.href = url;
    var ts = new Date();
    a.download = 'dn_cross_check_' + ts.getFullYear() + String(ts.getMonth()+1).padStart(2,'0') + String(ts.getDate()).padStart(2,'0') + '_' + String(ts.getHours()).padStart(2,'0') + String(ts.getMinutes()).padStart(2,'0') + '.csv';
    document.body.appendChild(a); a.click(); document.body.removeChild(a);
    URL.revokeObjectURL(url);
    showToast('success', '📥 ' + a.download);
  };

  window.soHandleFile = function(file) {
    if (!file) return;
    var fnEl = document.getElementById('so-filename');
    var resEl = document.getElementById('so-result');
    if (fnEl) fnEl.textContent = '⏳ 업로드/매칭 중: ' + file.name + ' (' + Math.round(file.size / 1024) + ' KB)';
    if (resEl) resEl.innerHTML = '';

    var form = new FormData();
    form.append('file', file, file.name);
    var xhr = new XMLHttpRequest();
    xhr.open('POST', API + '/api/outbound/sales-order-upload');
    xhr.onload = function(){
      var body; try { body = JSON.parse(xhr.responseText); } catch(e){ body = null; }
      if (xhr.status >= 200 && xhr.status < 300 && body && body.ok) {
        var d = body.data || {};
        if (fnEl) fnEl.innerHTML = '✅ <strong>' + escapeHtml(d.filename) + '</strong> (' + d.total_rows + ' rows)';
        var unmatchedHtml = '';
        if (d.unmatched_count) {
          unmatchedHtml = '<details style="margin-top:6px"><summary style="cursor:pointer;color:var(--warning);font-size:11px">⚠️ 미매칭 ' + d.unmatched_count + '건 상세</summary>' +
            '<ul style="font-size:10px;margin:4px 0 0 20px">' +
            d.unmatched.map(function(u){ return '<li>' + escapeHtml(u.lot_no) + ' → ' + escapeHtml(u.sales_order_no) + ' (' + escapeHtml(u.reason) + ')</li>'; }).join('') +
            '</ul></details>';
        }
        var errorsHtml = '';
        if (d.error_count) {
          errorsHtml = '<details style="margin-top:6px"><summary style="cursor:pointer;color:var(--danger);font-size:11px">❌ 에러 ' + d.error_count + '건</summary>' +
            '<ul style="font-size:10px;margin:4px 0 0 20px">' +
            d.errors.map(function(er){ return '<li>row ' + er.row + ': ' + escapeHtml(er.reason) + '</li>'; }).join('') +
            '</ul></details>';
        }
        if (resEl) resEl.innerHTML =
          '<div style="padding:10px;background:rgba(102,187,106,.1);border-left:3px solid var(--success);border-radius:4px">' +
          '<div style="font-weight:700;color:var(--success)">✅ ' + escapeHtml(body.message) + '</div>' +
          '<div style="font-size:11px;color:var(--text-muted);margin-top:4px">' +
            '✅ 매칭 ' + d.matched_count + ' · ⚠️ 미매칭 ' + d.unmatched_count + ' · ❌ 에러 ' + d.error_count +
          '</div>' +
          '<div style="font-size:10px;color:var(--text-muted);margin-top:6px">감지된 컬럼: lot=' + escapeHtml(d.columns_detected.lot || '?') + ' · so=' + escapeHtml(d.columns_detected.sales_order_no || '?') + (d.columns_detected.customer ? ' · customer=' + escapeHtml(d.columns_detected.customer) : '') + (d.columns_detected.delivery_date ? ' · date=' + escapeHtml(d.columns_detected.delivery_date) : '') + '</div>' +
          unmatchedHtml + errorsHtml +
          '</div>';
        showToast(d.matched_count > 0 ? 'success' : 'warn', body.message);
        if (typeof loadKpi === 'function') loadKpi();
      } else {
        var msg = (body && (body.detail || body.error || body.message)) || ('HTTP ' + xhr.status);
        if (typeof msg === 'object') msg = JSON.stringify(msg);
        if (fnEl) fnEl.innerHTML = '❌ 실패';
        if (resEl) resEl.innerHTML = '<div style="padding:10px;color:var(--danger);background:rgba(244,67,54,.1);border-radius:4px">❌ ' + escapeHtml(String(msg)) + '</div>';
        showToast('error', '업로드 실패: ' + msg);
      }
    };
    xhr.onerror = function(){
      if (fnEl) fnEl.textContent = '❌ 네트워크 에러';
      showToast('error', '네트워크 에러');
    };
    xhr.send(form);
  };

  /* ===================================================
     9. ALERTS + STATUSBAR
     =================================================== */
  var FALLBACK_ALERTS = [
    {severity:'warning',icon:'&#x1F3F7;&#xFE0F;',text:'Tonbag integrity issues 40 — run integrity check',link:'#integrity'},
    {severity:'error',  icon:'&#x1F4CD;',         text:'400 unallocated tonbags (5 LOTs) — location assignment needed',link:'#allocation'}
  ];

  function loadAlerts() {
    var c=document.getElementById('alerts-container');
    if (!c) return;
    apiGet('/api/dashboard/alerts')
      .then(function(res){ renderAlerts(c, res.data||res.alerts||FALLBACK_ALERTS); })
      .catch(function(){ renderAlerts(c, FALLBACK_ALERTS); });
  }

  function renderAlerts(c, alerts) {
    c.innerHTML='<div class="alerts-header"><span class="alerts-title">&#x26A0;&#xFE0F; ALERTS</span><span class="alerts-counter">'+(alerts.length?'&#x1F534; '+alerts.length:'')+'</span></div>' +
      '<ul class="alerts-list">'+alerts.map(function(a){
        return '<li class="alert alert-'+escapeHtml(a.severity)+'"><span class="alert-icon">'+(a.icon||'')+'</span><span class="alert-text">'+escapeHtml(a.text)+'</span>'+(a.link?'<a class="alert-link" href="'+escapeHtml(a.link)+'">Go</a>':'')+'</li>';
      }).join('')+'</ul>';
  }

  function loadStatusbar() {
    var c=document.getElementById('statusbar-container');
    if (!c) return;
    if (!c.querySelector('.statusbar')) {
      c.innerHTML='<div class="statusbar"><span id="sb-modules">Modules: -/-</span><span class="sb-sep">|</span><span id="sb-unallocated">Unallocated -</span><span class="sb-sep">|</span><span id="sb-scan-fail">Scan fail -</span><span class="sb-sep">|</span><span id="sb-lot-age">LOT avg age -</span><span style="flex:1"></span><span id="sb-last-refresh">Last refresh: -</span><label style="margin-left:12px"><input type="checkbox" id="sb-auto-refresh" checked> Auto-refresh</label></div>';
    }
    refreshStatusbar();
  }

  function refreshStatusbar() {
    function st(id,txt){ var el=document.getElementById(id); if(el) el.textContent=txt; }
    apiGet('/api/dashboard/stats').then(function(res){
      var d=res.data||res||{};
      st('sb-unallocated','LOT '+( d.total_lots||0)+' / Tonbag '+(d.total_tbags||0));
      st('sb-scan-fail','Stock '+(d.total_weight_mt!=null?fmtN(d.total_weight_mt):'0')+' MT');
      st('sb-lot-age','Available '+(d.available_mt!=null?fmtN(d.available_mt):'0')+' MT');
    }).catch(function(){});
    apiGet('/api/health').then(function(res){
      var h=res.data||res||{};
      var ok = h.status==='ok';
      st('sb-modules','Engine: '+(ok?'OK':'ERR')+' ('+( h.lots||0)+' LOTs)');
    }).catch(function(){ st('sb-modules','Engine: offline'); });
    st('sb-last-refresh','Last refresh: '+new Date().toLocaleTimeString());
  }

  /* =====================================================
     10. ENDPOINTS  (key = HTML data-action name exactly)
     ===================================================== */
  var ENDPOINTS = {
    /* ── 파일 메뉴 ── */
    'onOpen':            {m:'GET',  u:'/api/q2/recent-files',                   lbl:'최근 파일'},
    'onSave':            {m:'GET',  u:'/api/action/export-lot-excel',            lbl:'내보내기'},
    'onExport':          {m:'GET',  u:'/api/action/export-lot-excel',            lbl:'Excel 내보내기'},
    /* v864.3 Phase 4-B: D/O 후속 연결 네이티브 폼 */
    'onDoUpdate':        {m:'JS', u:'do-update', lbl:'D/O 후속 연결'},
    'onReturnDialog':    {m:'JS',   u:'return-dialog',                             lbl:'반품 (재입고)'},
    /* v864.3 Phase 4-B: 반품 입고 — 네이티브 Excel 업로드 모달 */
    'onReturnInboundUpload': {m:'JS', u:'return-upload', lbl:'반품 입고 Excel'},
    'onReturnStatistics': {m:'JS',  u:'return-stats',                            lbl:'반품 사유 통계'},  /* [Sprint 2-P] */
    'onRecentFiles':     {m:'GET',  u:'/api/q2/recent-files',                   lbl:'최근 파일'},
    'onExit':            {m:'JS',   u:'exit',                                    lbl:'종료'},

    /* ── 입고 메뉴 ── */
    /* v864.3 Phase 4-B: PDF 스캔 입고 네이티브 모달 (기존 scan 탭 대신) */
    'onOnPdfInbound':    {m:'JS', u:'pdf-inbound-upload', lbl:'PDF 스캔 입고'},
    /* v864.3 Phase 4-B: 수동 입고는 네이티브 모달로 처리 (tkinter filedialog 대체) */
    'onInboundManual':   {m:'JS', u:'inbound-upload', lbl:'수동 입고'},
    /* [Sprint 2-Q] InboundHistoryDialog — 모달 형식 (Inbound 탭과 별개 — v864-2 _bulk_import_inventory) */
    'onInboundList':     {m:'JS',   u:'inbound-history',                          lbl:'입고 현황 조회'},
    'onInboundCancel':   {m:'JS',   u:'inbound-cancel',                            lbl:'입고 취소'},

    /* ── 출고 메뉴 ── */
    /* v864.3 Phase 4-B: 즉시 출고 네이티브 폼 */
    'onOnQuickOutbound': {m:'JS', u:'quick-outbound', lbl:'즉시 출고'},
    /* v864.3 Phase 4-B: 빠른 출고 (붙여넣기) — 여러 LOT 일괄 */
    'onQuickOutboundPaste': {m:'JS', u:'quick-outbound-paste', lbl:'빠른 출고 (붙여넣기)'},
    /* v864.3 Phase 4-B: Picking List PDF 업로드 */
    'onPickingListUpload':  {m:'JS', u:'picking-list-pdf', lbl:'Picking List 업로드 (PDF)'},
    'onOutboundScheduled': {m:'JS', u:'outbound',                                 lbl:'출고 예정'},
    /* v864.3 Phase 4-B: 출고 확정 네이티브 폼 */
    'onOutboundConfirm': {m:'JS', u:'outbound-confirm', lbl:'출고 확정'},
    'onOutboundHistory': {m:'GET',  u:'/api/q/outbound-status',                  lbl:'출고 이력'},
    'onOutboundStatus':  {m:'JS',   u:'outbound',                                 lbl:'출고 현황'},
    'onApprovalHistory': {m:'GET',  u:'/api/q/approval-history',                 lbl:'승인 이력 조회'},

    /* ── 재고 메뉴 ── */
    'onInventoryList':   {m:'JS',   u:'inventory',                               lbl:'재고 조회'},
    /* v864.3 Phase 4-B: 톤백 위치 매핑 네이티브 Excel 업로드 */
    'onInventoryMove':   {m:'JS', u:'tonbag-location-upload', lbl:'위치 이동'},
    /* v864.3 Phase 4-B: Allocation 입력(출고 예약) 네이티브 Excel 업로드 */
    'onInventoryAllocation': {m:'JS', u:'allocation-upload', lbl:'Allocation 입력'},
    'onIntegrityCheck':  {m:'GET',  u:'/api/action/integrity-check',             lbl:'정합성 검사'},
    'onInventoryReport': {m:'GET',  u:'/api/q/inventory-report',                 lbl:'재고 현황 보고서'},
    'onInventoryTrend':  {m:'GET',  u:'/api/q/inventory-trend',                  lbl:'재고 추이 차트'},

    /* ── 보고서 메뉴 ── */
    'onReportDaily':     {m:'GET',  u:'/api/q2/report-daily',                    lbl:'일일 보고서'},
    'onReportMonthly':   {m:'GET',  u:'/api/q2/report-monthly',                  lbl:'월간 보고서'},
    'onReportCustom':    {m:'GET',  u:'/api/q/inventory-report',                   lbl:'맞춤 보고서'},
    'onInvoiceGenerate': {m:'GET',  u:'/api/action3/export-invoice-excel',         lbl:'거래명세서 생성'},
    'onDetailOfOutbound': {m:'GET', u:'/api/q2/detail-outbound',                 lbl:'Detail of Outbound'},
    'onSalesOrderDN':    {m:'GET',  u:'/api/q3/sales-order-dn',                  lbl:'Sales Order DN'},
    'onDnCrossCheck':    {m:'JS',   u:'dn-cross-check',                         lbl:'DN 교차검증'},  /* [Sprint 2-O] */
    'onLotDetailPdf':    {m:'GET',  u:'/api/action/lot-detail',                  lbl:'LOT 상세'},
    'onLotListExcel':    {m:'GET',  u:'/api/action/export-lot-excel',             lbl:'LOT 리스트 Excel'},
    'onTonbagListExcel': {m:'GET',  u:'/api/action2/export-tonbag-excel',          lbl:'톤백리스트 Excel'},
    'onReportExport':    {m:'GET',  u:'/api/action2/export-tonbag-excel',          lbl:'Excel 내보내기'},
    'onMovementHistory': {m:'GET',  u:'/api/q/movement-history',                  lbl:'입출고 내역'},
    'onAuditLog':        {m:'GET',  u:'/api/q/audit-log',                         lbl:'감사 로그'},

    /* ── 설정/도구 메뉴 ── */
    /* [Sprint 0] 'onSettings' removed — was wired to /api/menu/-on-settings (NotReadyError stub).
       Real settings dialog ships in Sprint 2 (SettingsDialogMixin port, ~5d). */
    'onProductMaster':   {m:'JS',   u:'product-master',                           lbl:'제품 마스터 관리'},  /* [Sprint 2/3] */
    'onProductInventoryReport': {m:'GET', u:'/api/q/product-inventory',           lbl:'제품별 재고 현황'},
    /* [Sprint 1-4] integrity 분리: report (read-only) vs fix (mutating) */
    'onIntegrityReport':   {m:'JS',  u:'integrity-report',                                lbl:'정합성 검증 (V760)'},
    'onFixLotIntegrity':   {m:'JS',  u:'integrity-fix',                                   lbl:'LOT 정합성 복구'},
    'onIntegrityRepair':   {m:'JS',  u:'integrity-report',                                lbl:'정합성 검사/복구'},
    'onOptimizeDb':      {m:'POST', u:'/api/action3/optimize-db',                 lbl:'DB 최적화'},
    'onCleanupLogs':     {m:'POST', u:'/api/action3/cleanup-logs',                lbl:'로그 정리'},
    'onDbInfo':          {m:'GET',  u:'/api/info/system-info',                    lbl:'DB 정보'},
    'onOnBackup':        {m:'POST', u:'/api/action/backup-create',                lbl:'백업 생성'},
    'onBackupList':      {m:'GET',  u:'/api/q/backup-list',                       lbl:'백업 목록'},
    'onRestore':         {m:'JS',   u:'restore',                                   lbl:'복원'},
    'onAiTools':         {m:'GET',  u:'/api/info/version',                         lbl:'AI 도구'},
    'onSaveWindowSize':  {m:'JS',   u:'save-window-size',                          lbl:'창 크기 저장'},
    'onResetWindowSize': {m:'JS',   u:'reset-window-size',                         lbl:'창 크기 초기화'},

    /* ── 도움말 메뉴 ── */
    /* [Sprint 3] 도움말 다이얼로그들 — 풀 모달 (이전 raw JSON → 사용자 친화 다이얼로그) */
    'onHelp':            {m:'JS',   u:'help',                                     lbl:'사용법'},
    'onShortcuts':       {m:'JS',   u:'shortcuts',                                lbl:'단축키 안내'},
    'onStatusGuide':     {m:'JS',   u:'status-guide',                             lbl:'STATUS 가이드'},
    'onBackupGuide':     {m:'GET',  u:'/api/info/backup-guide',                   lbl:'백업/복구 가이드'},
    'onAbout':           {m:'JS',   u:'about',                                    lbl:'버전 정보'},

    /* ── 탭 이동 ── */
    'onGoScanTab':       {m:'JS',   u:'scan',                                     lbl:'스캔 탭'},
    'onGoAllocationTab': {m:'JS',   u:'allocation',                               lbl:'배정 탭'},

    /* ── 툴바 ── */
    /* v864.3 Phase 4-B: 툴바 PDF 입고 — 네이티브 모달 */
    'tb-pdf-inbound':    {m:'JS', u:'pdf-inbound-upload', lbl:'PDF 입고'},
    /* 툴바 '즉시 출고' 도 네이티브 폼으로 */
    'tb-quick-outbound': {m:'JS', u:'quick-outbound', lbl:'즉시 출고'},
    'tb-return':         {m:'JS',   u:'return',                                   lbl:'반품'},
    'tb-inventory':      {m:'JS',   u:'inventory',                                lbl:'재고 조회'},
    'tb-integrity':      {m:'GET',  u:'/api/action/integrity-check',              lbl:'정합성'},
    'tb-backup':         {m:'POST', u:'/api/action/backup-create',                lbl:'백업'},
    /* [Sprint 0] 'tb-settings' removed — same reason as onSettings (real dialog in Sprint 2). */

    /* ── v864.2 신규 액션 (메뉴 구조 동기화) ── */
    'onBarcodeScanUpload': {m:'JS', u:'barcode-scan-upload',                       lbl:'바코드 스캔 업로드'},
    'onApprovalQueue':   {m:'JS',   u:'approval-queue',                            lbl:'승인 대기'},
    'onApplyApproved':   {m:'POST', u:'/api/allocation/apply-approved',            lbl:'예약 반영 (승인분)'},
    'onPickingTemplateManage': {m:'JS', u:'picking-template',                      lbl:'피킹 템플릿 관리'},
    'onMoveApprovalQueue': {m:'JS', u:'move-approval-queue',                      lbl:'대량 이동 승인'},
    'onInboundTemplateManage': {m:'JS', u:'inbound-template',                     lbl:'입고 파싱 템플릿'},
    'onEmailConfig':     {m:'JS',   u:'email-config',                              lbl:'이메일 설정'},
    'onIntegrityReport': {m:'GET',  u:'/api/action/integrity-check',              lbl:'정합성 검증 (시각화)'},
    'onFixLotIntegrity': {m:'GET',  u:'/api/action/integrity-check',              lbl:'LOT 상태 정합성 복구'},
    'onExportCustoms':   {m:'GET',  u:'/api/action/export-lot-excel',             lbl:'통관요청 양식'},
    'onExportRubyli':    {m:'GET',  u:'/api/action/export-lot-excel',             lbl:'루비리 양식'},
    'onExportTonbag':    {m:'GET',  u:'/api/action2/export-tonbag-excel',          lbl:'톤백 현황'},
    'onExportIntegrated': {m:'GET', u:'/api/action/export-lot-excel',             lbl:'통합 현황'},
    'onAutoBackupSettings': {m:'JS', u:'auto-backup-settings',                    lbl:'자동 백업 설정'},
    /* [Sprint 2-R] Sales Order Upload */
    'onSalesOrderUpload': {m:'JS', u:'sales-order-upload',                         lbl:'Sales Order 업로드'},
    /* [Sprint 2] Swap report — placeholder Sprint 2 다음 phase */
    'onSwapReportDialog': {m:'JS', u:'wip',                                        lbl:'Swap 리포트'},
    /* [Sprint 2] 보고서 양식/이력 mis-wire 수정 — Sprint 1-3-D 감사 로그 sub-popup 재활용 */
    'onReportTemplates': {m:'JS',   u:'audit-viewer',                              lbl:'보고서 양식 관리'},
    'onReportHistory':   {m:'JS',   u:'audit-viewer',                              lbl:'보고서 이력 조회'},
    'onAuditLog':        {m:'JS',   u:'audit-viewer',                              lbl:'감사 로그 조회'},
    /* [Sprint 2] 작은 다이얼로그들 */
    'onSwapReportDialog': {m:'JS',  u:'swap-report',                               lbl:'Swap 리포트'},
    'onStockAlerts':     {m:'JS',   u:'stock-alerts',                              lbl:'재고 알림 조회'},
    'onLotAllocationAudit': {m:'JS', u:'lot-allocation-audit',                    lbl:'LOT Allocation 톤백 현황'},
    'onDocConvert':      {m:'JS',   u:'doc-convert',                               lbl:'문서 변환 (OCR/PDF)'},
    'onTestDbReset':     {m:'JS',   u:'test-db-reset',                             lbl:'테스트 DB 초기화'},
    'onSystemInfo':      {m:'JS',   u:'system-info',                              lbl:'시스템 정보'},  /* [Sprint 3] */
    'onProductSummary':  {m:'JS',   u:'product-summary',                           lbl:'품목별 재고 요약'},
    'onProductLotLookup': {m:'JS',  u:'product-lot-lookup',                        lbl:'품목별 LOT 조회'},
    'onProductMovement': {m:'JS',   u:'product-movement',                          lbl:'품목별 입출고 현황'},

    /* ── [Sprint 2-B] v864-2 SettingsDialogMixin + BL 도구 — 실구현 ── */
    'onBlCarrierRegister': {m:'JS', u:'carrier-rules',                             lbl:'🚢 선사 BL 등록 도구'},
    'onBlCarrierAnalyze':  {m:'JS', u:'carrier-rules',                             lbl:'🔬 선사 패턴 분석'},
    'onSettings':          {m:'JS', u:'settings',                                  lbl:'⚙️ 설정 (API + BL 규칙)'},
    'onGeminiToggle':      {m:'JS', u:'settings',                                  lbl:'🔀 Gemini AI 사용'},
    'onGeminiApiSettings': {m:'JS', u:'settings',                                  lbl:'🔐 API 키 설정'},
    'onGeminiApiTest':     {m:'JS', u:'settings',                                  lbl:'🧪 API 연결 테스트'},
    /* ── [Sprint 0-3 → Sprint 2/3 활성화] 재고 메뉴 슬롯 ── */
    'onExportLot':         {m:'GET', u:'/api/action/export-lot-excel',             lbl:'📊 LOT 리스트 Excel'},
    'onStockTrendChart':   {m:'GET', u:'/api/q/inventory-trend',                   lbl:'📊 재고 추이 차트'},

    /* ── [Sprint 2-C] 🔍 전역 검색 버튼 — 실구현 ── */
    'onGlobalSearch':      {m:'JS', u:'global-search',                             lbl:'🔍 전역 검색'},

    /* View 메뉴 탭 이동 */
    'onGoInventoryTab':  {m:'JS',   u:'inventory',                                lbl:'Inventory 탭'},
    'onGoPickedTab':     {m:'JS',   u:'picked',                                   lbl:'Picked 탭'},
    'onGoOutboundTab':   {m:'JS',   u:'outbound',                                 lbl:'Outbound 탭'},
    'onGoReturnTab':     {m:'JS',   u:'return',                                   lbl:'Return 탭'},
    'onGoMoveTab':       {m:'JS',   u:'move',                                     lbl:'Move 탭'},
    'onGoDashboardTab':  {m:'JS',   u:'dashboard',                                lbl:'Dashboard 탭'},
    'onGoLogTab':        {m:'JS',   u:'log',                                      lbl:'Log 탭'},

    /* ── 기타 ── */
    'refresh-all':       {m:'JS',   u:'refresh',                                  lbl:'새로고침'},
    'onToggleTheme':     {m:'JS',   u:'theme',                                    lbl:'테마 전환'},
  };

  function dispatchAction(action) {
    var conf = ENDPOINTS[action];
    if (!conf) {
      dbgLog('⚠️','[unregistered] '+action,'ENDPOINTS에 없는 액션','#ffa726');
      showToast('info', '[unregistered] action=' + action);
      return;
    }
    if (conf.m === 'JS') {
      if (conf.u === 'theme')   { toggleTheme(); return; }
      if (conf.u === 'refresh') { renderPage(_currentRoute || 'dashboard'); return; }
      if (conf.u === 'exit') {
        if (window.pywebview && window.pywebview.api) window.pywebview.api.exit_app();
        else window.close();
        return;
      }
      /* v864.3 Phase 4-B: 네이티브 모달 액션 */
      if (conf.u === 'inbound-upload') {
        showInboundManualUploadModal();
        return;
      }
      if (conf.u === 'return-upload') {
        showReturnInboundUploadModal();
        return;
      }
      if (conf.u === 'allocation-upload') {
        showAllocationUploadModal();
        return;
      }
      if (conf.u === 'quick-outbound') {
        /* [Sprint 1-3] OneStop 4탭 wizard 모달로 전환 */
        showOneStopOutboundModal();
        return;
      }
      if (conf.u === 'do-update') {
        showDoUpdateModal();
        return;
      }
      if (conf.u === 'tonbag-location-upload') {
        showTonbagLocationUploadModal();
        return;
      }
      if (conf.u === 'apply-approved-allocation') {
        showApplyApprovedAllocationModal();
        return;
      }
      if (conf.u === 'pdf-inbound-upload') {
        /* [Sprint 1-2] OneStop 4슬롯 wizard 모달 (v864-2 OneStopInboundDialog 매칭) */
        showOneStopInboundModal();
        return;
      }
      if (conf.u === 'picking-list-pdf') {
        showPickingListPdfModal();
        return;
      }
      if (conf.u === 'quick-outbound-paste') {
        showQuickOutboundPasteModal();
        return;
      }
      if (conf.u === 'outbound-confirm') {
        showOutboundConfirmModal();
        return;
      }
      if (conf.u === 'inbound-cancel') {
        showInboundCancelModal();
        return;
      }
      if (conf.u === 'approval-queue') {
        showApprovalQueueModal();
        return;
      }
      if (conf.u === 'restore') {
        showRestoreModal();
        return;
      }
      if (conf.u === 'save-window-size') {
        saveWindowSize();
        return;
      }
      if (conf.u === 'reset-window-size') {
        resetWindowSize();
        return;
      }
      if (conf.u === 'return-dialog') {
        showReturnDialog();
        return;
      }
      if (conf.u === 'lot-allocation-audit') {
        showLotAllocationAuditModal();
        return;
      }
      if (conf.u === 'test-db-reset') {
        showTestDbResetModal();
        return;
      }
      if (conf.u === 'barcode-scan-upload') {
        showBarcodeScanUploadModal();
        return;
      }
      if (conf.u === 'email-config') {
        showEmailConfigModal();
        return;
      }
      if (conf.u === 'auto-backup-settings') {
        showAutoBackupSettingsModal();
        return;
      }
      if (conf.u === 'inbound-template') {
        showInboundTemplateModal();
        return;
      }
      if (conf.u === 'picking-template') {
        showPickingTemplateModal();
        return;
      }
      if (conf.u === 'move-approval-queue') {
        showMoveApprovalQueueModal();
        return;
      }
      if (conf.u === 'doc-convert') {
        showDocConvertModal();
        return;
      }
      if (conf.u === 'product-summary') {
        showProductSummaryModal();
        return;
      }
      if (conf.u === 'product-lot-lookup') {
        showProductLotLookupModal();
        return;
      }
      if (conf.u === 'product-movement') {
        showProductMovementModal();
        return;
      }
      if (conf.u === 'wip') {
        dbgLog('🟡','WIP: '+conf.lbl,'준비 중 (아직 미구현)','#ffa726');
        showToast('info', conf.lbl + ': 준비 중');
        return;
      }
      /* [Sprint 1-4] integrity 분리 */
      if (conf.u === 'integrity-report') { showIntegrityV760Modal(); return; }
      if (conf.u === 'integrity-fix') { showIntegrityV760Modal(true); return; }
      /* [Sprint 2-C] 전역 검색 */
      if (conf.u === 'global-search') { showGlobalSearchModal(); return; }
      /* [Sprint 2-A] Inbound Template */
      if (conf.u === 'inbound-template') { showInboundTemplateModal(); return; }
      /* [Sprint 2] Picking Template */
      if (conf.u === 'picking-template') { showPickingTemplateModal(); return; }
      /* [Sprint 2-R] Sales Order Upload */
      if (conf.u === 'sales-order-upload') { showSalesOrderUploadModal(); return; }
      /* [Sprint 2-Q] Inbound History */
      if (conf.u === 'inbound-history') { showInboundHistoryModal(); return; }
      /* [Sprint 2-O] DN Cross Check */
      if (conf.u === 'dn-cross-check') { showDnCrossCheckModal(); return; }
      /* [Sprint 2-P] Return Statistics */
      if (conf.u === 'return-stats') { showReturnStatsModal(); return; }
      /* [Sprint 2-B] Settings + Carrier rules */
      if (conf.u === 'settings') { showSettingsModal(); return; }
      if (conf.u === 'carrier-rules') { showSettingsModal('carrier'); return; }
      /* [Sprint 2] 보고서 양식/이력 mis-wire 수정 → audit viewer 재활용 */
      if (conf.u === 'audit-viewer') { window.ooViewAuditLog(); return; }
      /* [Sprint 2] 작은 모달들 */
      if (conf.u === 'swap-report') { showSwapReportModal(); return; }
      if (conf.u === 'stock-alerts') { showStockAlertsModal(); return; }
      /* [Sprint 2/3] 작은 다이얼로그 batch */
      if (conf.u === 'doc-convert') { showDocConvertModal(); return; }
      if (conf.u === 'product-master') { showProductMasterModal(); return; }
      if (conf.u === 'email-config') { showEmailConfigModal(); return; }
      if (conf.u === 'auto-backup-settings') { showAutoBackupModal(); return; }
      if (conf.u === 'shortcuts') { showShortcutsModal(); return; }
      if (conf.u === 'status-guide') { showStatusGuideModal(); return; }
      if (conf.u === 'help') { showHelpModal(); return; }
      if (conf.u === 'about') { showAboutModal(); return; }
      if (conf.u === 'system-info') { showSystemInfoModal(); return; }
      dbgLog('🔀','Route → '+conf.u, conf.lbl,'#ab47bc');
      renderPage(conf.u);
      return;
    }
    if (conf.m === 'GET') {
      renderInfoModal(conf.lbl, conf.u);
      return;
    }
    apiCall(conf.m, conf.u, {})
      .then(function (res) {
        // v864.3 Debug: 응답 body 의 ok:false 체크 (가짜 성공 토스트 차단)
        if (res && res.ok === false) {
          var detailCode = res.detail && res.detail.code;
          if (detailCode === 'NOT_READY') {
            showToast('info', '⚠️ ' + conf.lbl + ' — 준비 중 (Phase 4-B)');
            dbgLog('🟡','NOT_READY', conf.lbl + ' (' + conf.u + ')','#ffa726');
          } else {
            showToast('warning', conf.lbl + ' — ' + (res.error || res.message || '실패'));
            dbgLog('🟡','ok:false', conf.lbl + ' — ' + (res.error || ''),'#ffa726');
          }
          return;
        }
        // 진짜 성공: data 가 의미있는지 간단 체크
        var d = res ? (res.data !== undefined ? res.data : res) : null;
        var hasData = d && (typeof d !== 'object' || Object.keys(d).length > 0 || (Array.isArray(d) && d.length > 0));
        if (!hasData && res && res.ok === true) {
          // 200 OK + ok:true 지만 data 없음 → 의심
          showToast('info', conf.lbl + ' 요청 전송됨 (UI 미구현)');
          dbgLog('🟠','EMPTY OK', conf.lbl + ' — 응답은 성공인데 data 없음','#ff9800');
          return;
        }
        showToast('success', conf.lbl + ' 완료');
      })
      .catch(function (e) {
        if (e.status === 501) showToast('info', conf.lbl + ' (coming soon)');
        else showToast('error', conf.lbl + ' 실패: ' + (e.message || String(e)));
      });
  }

  window.dispatchAction = dispatchAction;

  /* ===================================================
     11. BIND ALL + BOOT
     =================================================== */
  function bindAll() {
    // data-action elements
    document.querySelectorAll('[data-action]').forEach(function(el){
      if (el.dataset._sqmBound) return;
      el.dataset._sqmBound='1';
      el.addEventListener('click', function(ev){
        ev.preventDefault();
        ev.stopPropagation();
        var action = el.dataset.action;
        if (action==='toggle-theme'||action==='theme-toggle') { toggleTheme(); return; }
        if (action==='refresh-all') { renderPage(_currentRoute||'dashboard'); return; }
        dispatchAction(action);
      });
    });

    // data-route elements
    document.querySelectorAll('[data-route]').forEach(function(el){
      if (el.dataset._sqmBound) return;
      el.dataset._sqmBound='1';
      el.addEventListener('click', function(ev){
        ev.preventDefault();
        renderPage(el.dataset.route);
      });
    });

    // top-level menu toggle
    document.querySelectorAll('.menu-btn[data-menu]').forEach(function(el){
      if (el.dataset._sqmBound) return;
      el.dataset._sqmBound='1';
      el.addEventListener('click', function(ev){
        var menuName = el.dataset.menu || '?';
        console.log('[SQM MENU CLICK]', menuName, '| target:', ev.target.tagName, '| hasAction:', !!ev.target.closest('[data-action]'));
        dbgLog('🖱️','MENU CLICK', menuName + ' | target=' + ev.target.tagName + ' | hasAction=' + (!!ev.target.closest('[data-action]')), '#00e5ff');
        if (ev.target.closest('[data-action]')) {
          dbgLog('⚡','MENU → action', ev.target.dataset.action, '#ffeb3b');
          return;
        }
        ev.preventDefault();
        ev.stopPropagation();
        var open = el.classList.contains('open');
        closeAllMenus();
        if (!open) {
          el.classList.add('open');
          _menuJustOpened = true;
          setTimeout(function(){ _menuJustOpened = false; }, 200);
          console.log('[SQM MENU OPEN]', menuName, '| .open class added:', el.classList.contains('open'));
          dbgLog('📂','MENU OPEN', menuName + ' | .open 추가됨', '#4caf50');
        } else {
          console.log('[SQM MENU CLOSE]', menuName);
          dbgLog('📁','MENU CLOSE', menuName, '#ff9800');
        }
      });
    });

    // close on outside click
    document.addEventListener('click', function(ev){
      if (_menuJustOpened) {
        console.log('[SQM] document click 차단됨 (_menuJustOpened=true)');
        return;
      }
      if (!ev.target.closest('.menu-btn,.menu-dropdown')) {
        console.log('[SQM] outside click → closeAllMenus');
        closeAllMenus();
      }
    });

    // theme buttons
    document.querySelectorAll('[data-action="theme-dark"]').forEach(function(el){
      el.addEventListener('click',function(){
        document.documentElement.setAttribute('data-theme','dark');
        try{getStore().setItem('sqm_theme','dark');}catch{}
      });
    });
    document.querySelectorAll('[data-action="theme-light"]').forEach(function(el){
      el.addEventListener('click',function(){
        document.documentElement.setAttribute('data-theme','light');
        try{getStore().setItem('sqm_theme','light');}catch{}
      });
    });

    // F5 shortcut — F8: debug panel toggle (handled in _dbgBuild)
    document.addEventListener('keydown', function(ev){
      if (ev.key==='F5'&&!ev.ctrlKey&&!ev.metaKey){
        ev.preventDefault();
        renderPage(_currentRoute||'dashboard');
      }
    });

    console.info('[SQM v864.3] bindAll complete');
  }

  function boot() {
    _dbgBuild();
    applyTheme();
    bindAll();
    loadAlerts();
    loadStatusbar();
    startKpiPolling();
    dbgLog('🚀','SQM v864.3 부팅 완료', 'F8 = 디버그 패널 토글','#4caf50');

    var hash = location.hash.slice(1);
    var lastTab = null;
    try { lastTab = getStore().getItem('sqm_last_tab'); } catch {}
    var initial = hash || lastTab || 'dashboard';
    renderPage(initial);

    window.addEventListener('hashchange', function(){
      var id = location.hash.slice(1);
      if (id && id !== _currentRoute) renderPage(id);
    });

    setInterval(function(){
      var auto = document.getElementById('sb-auto-refresh');
      if (auto && auto.checked && document.visibilityState !== 'hidden') {
        loadAlerts();
        refreshStatusbar();
        if (_currentRoute==='dashboard') loadKpi();
      }
    }, 30000);

    window.SQM = window.SQM || {};
    window.SQM.version = '864.3-phase5';
    window.SQM.renderPage = renderPage;
    window.SQM.dispatchAction = dispatchAction;
    window.SQM.currentRoute = function(){ return _currentRoute; };
    console.info('[SQM v864.3] boot complete. initial route:', initial);
  }

  if (document.readyState==='loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }

})();
