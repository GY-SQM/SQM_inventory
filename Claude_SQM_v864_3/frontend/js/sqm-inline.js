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
  function loadInventoryPage() {
    var route = _currentRoute;
    var c = document.getElementById('page-container');
    if (!c) return;
    c.innerHTML = '<div style="padding:40px;text-align:center">Loading inventory...</div>';
    apiGet('/api/inventory').then(function(res){
      if (_currentRoute !== route) return;
      var rows = extractRows(res);
      if (!rows.length) {
        c.innerHTML = '<div class="empty" style="padding:60px;text-align:center">No inventory data</div>';
        return;
      }
      var html = '<section class="page" data-page="inventory">' +
        '<div style="display:flex;align-items:center;gap:12px;padding:4px 0 10px">' +
        '<h2 style="margin:0">📦 재고 목록 (Inventory)</h2>' +
        '<span style="font-size:12px;color:var(--text-muted)">'+rows.length+' LOTs</span>' +
        '<button class="btn btn-secondary" onclick="renderPage(\'inventory\')" style="margin-left:auto">🔁 새로고침</button>' +
        '</div>' +
        '<div style="overflow-x:auto"><table class="data-table"><thead><tr>' +
        '<th>#</th><th>LOT</th><th>SAP</th><th>BL</th><th>Product</th>' +
        '<th>Status</th><th>Balance(MT)</th><th>NET(MT)</th><th>Container</th>' +
        '<th>MXBG</th><th>Avail</th><th>Invoice</th>' +
        '<th>Ship</th><th>Arrival</th><th>Con Return</th><th>Free</th>' +
        '<th>WH</th><th>Customs</th><th>Inbound(MT)</th><th>Outbound(MT)</th><th>Location</th><th></th>' +
        '</tr></thead><tbody>';
      html += rows.map(function(r, i){
        return '<tr>' +
          '<td class="mono-cell" style="color:var(--text-muted)">'+(i+1)+'</td>' +
          '<td class="mono-cell" style="color:var(--accent);font-weight:600">'+escapeHtml(r.lot||'')+'</td>' +
          '<td class="mono-cell">'+escapeHtml(r.sap||'')+'</td>' +
          '<td class="mono-cell">'+escapeHtml(r.bl||'')+'</td>' +
          '<td><span class="tag">'+escapeHtml(r.product||'')+'</span></td>' +
          '<td>'+escapeHtml(r.status||'')+'</td>' +
          '<td class="mono-cell" style="text-align:right">'+(r.balance!=null?fmtN(r.balance):'-')+'</td>' +
          '<td class="mono-cell" style="text-align:right">'+(r.net!=null?fmtN(r.net):'-')+'</td>' +
          '<td class="mono-cell">'+escapeHtml(r.container||'')+'</td>' +
          '<td class="mono-cell" style="text-align:center">'+(r.mxbg_pallet||'-')+'</td>' +
          '<td class="mono-cell" style="text-align:center">'+(r.avail_bags!=null?r.avail_bags:'-')+'</td>' +
          '<td class="mono-cell">'+escapeHtml(r.invoice_no||'')+'</td>' +
          '<td class="mono-cell">'+escapeHtml((r.ship_date||'').slice(0,10))+'</td>' +
          '<td class="mono-cell">'+escapeHtml((r.arrival_date||'').slice(0,10))+'</td>' +
          '<td class="mono-cell">'+escapeHtml((r.con_return||'').slice(0,10))+'</td>' +
          '<td class="mono-cell" style="text-align:center">'+(r.free_time||'-')+'</td>' +
          '<td class="mono-cell">'+escapeHtml(r.wh||'')+'</td>' +
          '<td class="mono-cell">'+escapeHtml(r.customs||'')+'</td>' +
          '<td class="mono-cell" style="text-align:right">'+(r.initial_weight!=null?fmtN(r.initial_weight):'-')+'</td>' +
          '<td class="mono-cell" style="text-align:right">'+(r.outbound_weight!=null?fmtN(r.outbound_weight):'-')+'</td>' +
          '<td><span class="tag">'+escapeHtml(r.location||'-')+'</span></td>' +
          '<td><button class="btn btn-ghost btn-xs" onclick="window.showLotDetail(\''+escapeHtml(r.lot||'')+'\')">Detail</button></td>' +
          '</tr>';
      }).join('');
      html += '</tbody></table></div></section>';
      c.innerHTML = html;
    }).catch(function(e){
      if (_currentRoute !== route) return;
      c.innerHTML = '<div class="empty" style="padding:40px;text-align:center">Load failed: '+escapeHtml(e.message||String(e))+'</div>';
      showToast('error', 'Inventory load failed');
    });
  }

  /* ===================================================
     7b. PAGE: Allocation
     =================================================== */
  function loadAllocationPage() {
    var route = _currentRoute;
    var c = document.getElementById('page-container');
    if (!c) return;
    c.innerHTML = '<div style="padding:40px;text-align:center">Loading allocation...</div>';
    apiGet('/api/allocation').then(function(res){
      if (_currentRoute !== route) return;
      var rows = extractRows(res);
      if (!rows.length) {
        c.innerHTML = '<div class="empty" style="padding:60px;text-align:center">No allocation data</div>';
        return;
      }
      var html = '<div style="overflow-x:auto"><table class="data-table"><thead><tr>' +
        '<th>LOT</th><th>Product</th><th>Customer</th><th>Sale Ref</th>' +
        '<th>Balance</th><th>Bags</th><th>Ship Date</th><th>Status</th><th>Cancel</th>' +
        '</tr></thead><tbody>';
      html += rows.map(function(r){
        return '<tr>' +
          '<td class="mono-cell" style="color:var(--accent)">'+escapeHtml(r.lot||'')+'</td>' +
          '<td><span class="tag">'+escapeHtml(r.product||'')+'</span></td>' +
          '<td>'+escapeHtml(r.customer||'-')+'</td>' +
          '<td class="mono-cell">'+escapeHtml(r.sale_ref||'-')+'</td>' +
          '<td class="mono-cell" style="color:var(--accent)">'+(r.balance!=null?Number(r.balance).toLocaleString():'-')+'</td>' +
          '<td class="mono-cell">'+(r.bags||'-')+'</td>' +
          '<td class="mono-cell">'+escapeHtml(r.ship_date||'-')+'</td>' +
          '<td>RESERVED</td>' +
          '<td><button class="btn btn-ghost btn-xs" onclick="window.cancelAllocation(\''+escapeHtml(r.lot||'')+'\')">Cancel</button></td>' +
          '</tr>';
      }).join('');
      html += '</tbody></table></div>';
      c.innerHTML = html;
    }).catch(function(e){
      if (_currentRoute !== route) return;
      c.innerHTML = '<div class="empty" style="padding:40px;text-align:center">Load failed: '+escapeHtml(e.message||String(e))+'</div>';
      showToast('error', 'Allocation load failed');
    });
  }

  window.cancelAllocation = function(lot) {
    if (!confirm(lot + ': cancel allocation?')) return;
    apiPost('/api/allocation/' + encodeURIComponent(lot) + '/cancel', {})
      .then(function(){ showToast('success', lot + ' allocation cancelled'); loadAllocationPage(); })
      .catch(function(e){ showToast('error', 'Cancel failed: ' + (e.message||String(e))); });
  };

  /* ===================================================
     7c. PAGE: Picked
     =================================================== */
  function loadPickedPage() {
    var route = _currentRoute;
    var c = document.getElementById('page-container');
    if (!c) return;
    c.innerHTML = [
      '<section class="page" data-page="picked">',
      '<h2>Picked - 피킹 완료 (화물 결정)</h2>',
      '<div class="toolbar-mini"><button class="btn btn-secondary" onclick="renderPage(\'picked\')">🔁 새로고침</button></div>',
      '<div id="picked-loading" style="padding:40px;text-align:center;color:var(--text-muted)">⏳ 데이터 로딩 중...</div>',
      '<table class="data-table" id="picked-table" style="display:none">',
      '<thead><tr><th>LOT No</th><th>피킹No</th><th>고객사</th><th>톤백수</th><th>중량(kg)</th><th>피킹일</th></tr></thead>',
      '<tbody id="picked-tbody"></tbody></table>',
      '<div class="empty" id="picked-empty" style="display:none">No data</div>',
      '</section>'
    ].join('');
    apiGet('/api/q/picked-list').then(function(res){
      if (_currentRoute !== route) return;
      var rows = extractRows(res);
      document.getElementById('picked-loading').style.display = 'none';
      if (!rows.length) { document.getElementById('picked-empty').style.display='block'; return; }
      var tbody = document.getElementById('picked-tbody');
      if (tbody) tbody.innerHTML = rows.map(function(r){
        return '<tr>' +
          '<td class="mono-cell" style="color:var(--accent)">'+escapeHtml(r.lot_no||'')+'</td>' +
          '<td class="mono-cell">'+escapeHtml(r.picking_no||'')+'</td>' +
          '<td>'+escapeHtml(r.customer||'')+'</td>' +
          '<td class="mono-cell" style="text-align:right">'+(r.tonbag_count||0)+'</td>' +
          '<td class="mono-cell" style="text-align:right">'+(r.total_kg!=null?fmtN(r.total_kg):'-')+'</td>' +
          '<td class="mono-cell">'+escapeHtml(r.picking_date||'')+'</td>' +
          '</tr>';
      }).join('');
      document.getElementById('picked-table').style.display = '';
    }).catch(function(e){
      if (_currentRoute !== route) return;
      document.getElementById('picked-loading').style.display = 'none';
      var el = document.getElementById('picked-empty');
      if (el) { el.textContent = 'Load failed: '+(e.message||String(e)); el.style.display='block'; }
      if (e.status !== 501) showToast('error', 'Picked load failed');
    });
  }

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
  function loadOutboundPage() {
    var route = _currentRoute;
    var c = document.getElementById('page-container');
    if (!c) return;
    c.innerHTML = [
      '<section class="page" data-page="outbound">',
      '<div style="display:flex;align-items:center;gap:12px;padding:8px 0 12px">',
      '<h2 style="margin:0">📤 출고 완료 (Sold / Outbound)</h2>',
      '<button class="btn btn-secondary" onclick="renderPage(\'outbound\')" style="margin-left:auto">🔁 새로고침</button>',
      '</div>',
      '<div id="outbound-loading" style="padding:40px;text-align:center;color:var(--text-muted)">⏳ 데이터 로딩 중...</div>',
      '<div style="overflow-x:auto">',
      '<table class="data-table" id="outbound-table" style="display:none">',
      '<thead><tr>',
      '<th>#</th><th>LOT No</th><th>판매주문No</th><th>고객사</th>',
      '<th>톤백수</th><th>중량(kg)</th><th>판매일</th>',
      '</tr></thead>',
      '<tbody id="outbound-tbody"></tbody>',
      '</table>',
      '</div>',
      '<div class="empty" id="outbound-empty" style="display:none;padding:60px;text-align:center;color:var(--text-muted)">📭 출고 데이터 없음</div>',
      '</section>'
    ].join('');

    apiGet('/api/q/sold-list').then(function(res){
      if (_currentRoute !== route) return;
      var rows = extractRows(res);
      document.getElementById('outbound-loading').style.display = 'none';
      if (!rows.length) {
        document.getElementById('outbound-empty').style.display = 'block';
        return;
      }
      var tbody = document.getElementById('outbound-tbody');
      if (tbody) tbody.innerHTML = rows.map(function(r, i){
        return '<tr>' +
          '<td class="mono-cell" style="color:var(--text-muted)">'+(i+1)+'</td>' +
          '<td class="mono-cell" style="color:var(--accent);font-weight:600">'+escapeHtml(r.lot_no||'')+'</td>' +
          '<td class="mono-cell">'+escapeHtml(r.sales_order_no||'-')+'</td>' +
          '<td>'+escapeHtml(r.customer||'-')+'</td>' +
          '<td class="mono-cell" style="text-align:right">'+(r.tonbag_count||0)+'</td>' +
          '<td class="mono-cell" style="text-align:right">'+(r.total_kg!=null?fmtN(r.total_kg):'-')+'</td>' +
          '<td class="mono-cell">'+escapeHtml(r.sold_date||'-')+'</td>' +
          '</tr>';
      }).join('');
      document.getElementById('outbound-table').style.display = '';
      dbgLog('📤','outbound-page','rows='+rows.length,'#4caf50');
    }).catch(function(e){
      if (_currentRoute !== route) return;
      document.getElementById('outbound-loading').style.display = 'none';
      var el = document.getElementById('outbound-empty');
      if (el) { el.textContent = '❌ 로드 실패: '+(e.message||String(e)); el.style.display = 'block'; }
      showToast('error', '출고 현황 로드 실패');
      dbgLog('❌','outbound-page',String(e),'#f44336');
    });
  }

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
  function loadScanPage() {
    var c = document.getElementById('page-container');
    if (!c) return;
    c.innerHTML = [
      '<section class="page" data-page="scan">',
      '<h2>Scan - Barcode / PDF Inbound</h2>',
      '<div style="display:grid;grid-template-columns:1fr 1fr;gap:16px">',

      '<!-- Barcode Panel -->',
      '<div class="card" style="padding:20px">',
      '<h3 style="margin-bottom:12px">Barcode Scan</h3>',
      '<input id="scan-input" class="input" placeholder="Scan or type barcode + Enter" style="width:100%;margin-bottom:12px">',
      '<div style="display:flex;gap:8px;margin-bottom:16px">',
      '<button class="btn btn-primary btn-sm" onclick="window.ScanActions.quickAction(\'inbound\')">Inbound</button>',
      '<button class="btn btn-warning btn-sm" onclick="window.ScanActions.quickAction(\'outbound\')">Outbound</button>',
      '<button class="btn btn-secondary btn-sm" onclick="window.ScanActions.quickAction(\'move\')">Move</button>',
      '</div>',
      '<table class="data-table"><thead><tr><th>Time</th><th>Barcode</th><th>Action</th><th>Result</th></tr></thead>',
      '<tbody id="scan-history-tbody"><tr><td colspan="4" style="text-align:center;padding:20px;color:var(--text-muted)">No scan history</td></tr></tbody></table>',
      '</div>',

      '<!-- PDF Panel -->',
      '<div class="card" style="padding:20px">',
      '<h3 style="margin-bottom:12px">PDF Inbound</h3>',
      '<div id="pdf-drop-zone" style="border:2px dashed var(--border);border-radius:8px;padding:40px;text-align:center;cursor:pointer;color:var(--text-muted)" onclick="document.getElementById(\'pdf-file-input\').click()" ondragover="event.preventDefault();this.style.borderColor=\'var(--accent)\'" ondragleave="this.style.borderColor=\'var(--border)\'" ondrop="window.PdfInbound.handleDrop(event)">',
      '<div style="font-size:2rem">&#x1F4C4;</div>',
      '<div style="margin-top:8px">Drag PDF here or click to select</div>',
      '<div style="font-size:0.8rem;margin-top:4px;color:var(--text-muted)">Picking List / BL / Inbound PDF</div>',
      '</div>',
      '<input type="file" id="pdf-file-input" accept=".pdf" style="display:none" onchange="window.PdfInbound.handleFile(this.files[0])">',
      '<div id="pdf-status" style="margin-top:12px;color:var(--text-muted);font-size:0.9rem"></div>',
      '<button class="btn btn-primary" id="pdf-upload-btn" style="display:none;margin-top:8px" onclick="window.PdfInbound.upload()">Upload &amp; Process</button>',
      '</div>',

      '</div></section>'
    ].join('');

    var inp = document.getElementById('scan-input');
    if (inp) {
      inp.addEventListener('keydown', function(e){
        if (e.key==='Enter') {
          e.preventDefault();
          window.ScanActions.processBarcode(inp.value.trim());
          inp.value='';
        }
      });
      inp.focus();
    }
  }

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

  /* F001 PDF 스캔 입고 (Packing List) */
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

  window.showLotDetail = function(lotNo) {
    if (!lotNo) return;
    showDataModal('LOT Detail: '+lotNo,'<div style="padding:20px;text-align:center">Loading...</div>');
    apiGet('/api/action/lot-detail/'+encodeURIComponent(lotNo)).then(function(res){
      var d=res.data||res||{};
      var html='<table class="data-table"><tbody>'+Object.entries(d).map(function(kv){
        return '<tr><td style="font-weight:600;width:40%">'+escapeHtml(kv[0])+'</td><td>'+escapeHtml(String(kv[1]))+'</td></tr>';
      }).join('')+'</tbody></table>';
      document.getElementById('sqm-modal-content').innerHTML='<h2 style="margin-bottom:16px">LOT Detail: '+escapeHtml(lotNo)+'</h2>'+html;
    }).catch(function(e){
      document.getElementById('sqm-modal-content').innerHTML='<h2>LOT Detail: '+escapeHtml(lotNo)+'</h2><div class="empty">Load failed: '+escapeHtml(e.message||String(e))+'</div>';
    });
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
    'onReturnDialog':    {m:'JS',   u:'return',                                  lbl:'반품 (재입고)'},
    /* v864.3 Phase 4-B: 반품 입고 — 네이티브 Excel 업로드 모달 */
    'onReturnInboundUpload': {m:'JS', u:'return-upload', lbl:'반품 입고 Excel'},
    'onReturnStatistics': {m:'GET', u:'/api/q2/return-stats',                   lbl:'반품 사유 통계'},
    'onRecentFiles':     {m:'GET',  u:'/api/q2/recent-files',                   lbl:'최근 파일'},
    'onExit':            {m:'JS',   u:'exit',                                    lbl:'종료'},

    /* ── 입고 메뉴 ── */
    /* v864.3 Phase 4-B: PDF 스캔 입고 네이티브 모달 (기존 scan 탭 대신) */
    'onOnPdfInbound':    {m:'JS', u:'pdf-inbound-upload', lbl:'PDF 스캔 입고'},
    /* v864.3 Phase 4-B: 수동 입고는 네이티브 모달로 처리 (tkinter filedialog 대체) */
    'onInboundManual':   {m:'JS', u:'inbound-upload', lbl:'수동 입고'},
    'onInboundList':     {m:'JS',   u:'inbound',                                  lbl:'입고 목록'},
    'onInboundCancel':   {m:'JS',   u:'wip',                                     lbl:'입고 취소'},

    /* ── 출고 메뉴 ── */
    /* v864.3 Phase 4-B: 즉시 출고 네이티브 폼 */
    'onOnQuickOutbound': {m:'JS', u:'quick-outbound', lbl:'즉시 출고'},
    /* v864.3 Phase 4-B: 빠른 출고 (붙여넣기) — 여러 LOT 일괄 */
    'onQuickOutboundPaste': {m:'JS', u:'quick-outbound-paste', lbl:'빠른 출고 (붙여넣기)'},
    /* v864.3 Phase 4-B: Picking List PDF 업로드 */
    'onPickingListUpload':  {m:'JS', u:'picking-list-pdf', lbl:'Picking List 업로드 (PDF)'},
    'onOutboundScheduled': {m:'JS', u:'wip',                                     lbl:'출고 예정'},
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
    'onReportCustom':    {m:'POST', u:'/api/menu/-generate-customer-report',      lbl:'맞춤 보고서'},
    'onInvoiceGenerate': {m:'GET',  u:'/api/action3/export-invoice-excel',         lbl:'거래명세서 생성'},
    'onDetailOfOutbound': {m:'GET', u:'/api/q2/detail-outbound',                 lbl:'Detail of Outbound'},
    'onSalesOrderDN':    {m:'GET',  u:'/api/q3/sales-order-dn',                  lbl:'Sales Order DN'},
    'onDnCrossCheck':    {m:'GET',  u:'/api/q3/dn-cross-check',                  lbl:'DN 교차검증'},
    'onLotDetailPdf':    {m:'GET',  u:'/api/action/lot-detail',                  lbl:'LOT 상세'},
    'onLotListExcel':    {m:'GET',  u:'/api/action/export-lot-excel',             lbl:'LOT 리스트 Excel'},
    'onTonbagListExcel': {m:'GET',  u:'/api/action2/export-tonbag-excel',          lbl:'톤백리스트 Excel'},
    'onReportExport':    {m:'GET',  u:'/api/action2/export-tonbag-excel',          lbl:'Excel 내보내기'},
    'onMovementHistory': {m:'GET',  u:'/api/q/movement-history',                  lbl:'입출고 내역'},
    'onAuditLog':        {m:'GET',  u:'/api/q/audit-log',                         lbl:'감사 로그'},

    /* ── 설정/도구 메뉴 ── */
    'onSettings':        {m:'POST', u:'/api/menu/-on-settings',                   lbl:'환경 설정'},
    'onProductMaster':   {m:'GET',  u:'/api/info/system-info',                    lbl:'제품 마스터'},
    'onProductInventoryReport': {m:'GET', u:'/api/q/product-inventory',           lbl:'제품별 재고 현황'},
    'onIntegrityRepair': {m:'GET',  u:'/api/action/integrity-check',                     lbl:'정합성 검사/복구'},
    'onOptimizeDb':      {m:'POST', u:'/api/action3/optimize-db',                 lbl:'DB 최적화'},
    'onCleanupLogs':     {m:'POST', u:'/api/action3/cleanup-logs',                lbl:'로그 정리'},
    'onDbInfo':          {m:'GET',  u:'/api/info/system-info',                    lbl:'DB 정보'},
    'onOnBackup':        {m:'POST', u:'/api/action/backup-create',                lbl:'백업 생성'},
    'onBackupList':      {m:'GET',  u:'/api/q/backup-list',                       lbl:'백업 목록'},
    'onRestore':         {m:'POST', u:'/api/menu/-on-restore-click',              lbl:'복원'},
    'onAiTools':         {m:'JS',   u:'wip',                                      lbl:'AI 도구'},
    'onSaveWindowSize':  {m:'POST', u:'/api/menu/-on-save-window-size',           lbl:'창 크기 저장'},
    'onResetWindowSize': {m:'POST', u:'/api/menu/-on-reset-window-size',          lbl:'창 크기 초기화'},

    /* ── 도움말 메뉴 ── */
    'onHelp':            {m:'GET',  u:'/api/info/usage',                          lbl:'사용자 매뉴얼'},
    'onShortcuts':       {m:'GET',  u:'/api/info/shortcuts',                      lbl:'단축키'},
    'onStatusGuide':     {m:'GET',  u:'/api/info/status-guide',                   lbl:'STATUS 안내'},
    'onBackupGuide':     {m:'GET',  u:'/api/info/backup-guide',                   lbl:'백업/복구 가이드'},
    'onAbout':           {m:'GET',  u:'/api/info/version',                        lbl:'정보'},

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
    'tb-settings':       {m:'POST', u:'/api/menu/-on-settings',                   lbl:'설정'},

    /* ── v864.2 신규 액션 (메뉴 구조 동기화) ── */
    'onBarcodeScanUpload': {m:'JS', u:'wip',                                      lbl:'바코드 스캔 업로드'},
    'onApprovalQueue':   {m:'JS',   u:'wip',                                      lbl:'승인 대기'},
    'onApplyApproved':   {m:'POST', u:'/api/allocation/apply-approved',            lbl:'예약 반영 (승인분)'},
    'onPickingTemplateManage': {m:'JS', u:'wip',                                  lbl:'피킹 템플릿 관리'},
    'onMoveApprovalQueue': {m:'JS', u:'wip',                                      lbl:'대량 이동 승인'},
    'onInboundTemplateManage': {m:'JS', u:'wip',                                  lbl:'입고 파싱 템플릿'},
    'onEmailConfig':     {m:'JS',   u:'wip',                                      lbl:'이메일 설정'},
    'onIntegrityReport': {m:'GET',  u:'/api/action/integrity-check',              lbl:'정합성 검증 (시각화)'},
    'onFixLotIntegrity': {m:'GET',  u:'/api/action/integrity-check',              lbl:'LOT 상태 정합성 복구'},
    'onExportCustoms':   {m:'GET',  u:'/api/action/export-lot-excel',             lbl:'통관요청 양식'},
    'onExportRubyli':    {m:'GET',  u:'/api/action/export-lot-excel',             lbl:'루비리 양식'},
    'onExportTonbag':    {m:'GET',  u:'/api/action2/export-tonbag-excel',          lbl:'톤백 현황'},
    'onExportIntegrated': {m:'GET', u:'/api/action/export-lot-excel',             lbl:'통합 현황'},
    'onAutoBackupSettings': {m:'JS', u:'wip',                                     lbl:'자동 백업 설정'},
    'onReportTemplates': {m:'JS',   u:'wip',                                      lbl:'보고서 양식 관리'},
    'onReportHistory':   {m:'JS',   u:'wip',                                      lbl:'보고서 이력 조회'},
    'onLotAllocationAudit': {m:'JS', u:'wip',                                     lbl:'LOT Allocation 톤백 현황'},
    'onDocConvert':      {m:'JS',   u:'wip',                                      lbl:'문서 변환 (OCR/PDF)'},
    'onTestDbReset':     {m:'JS',   u:'wip',                                      lbl:'테스트 DB 초기화'},
    'onSystemInfo':      {m:'GET',  u:'/api/action/system-info',                  lbl:'시스템 정보'},
    'onProductSummary':  {m:'GET',  u:'/api/q/product-inventory',                 lbl:'품목별 재고 요약'},
    'onProductLotLookup': {m:'GET', u:'/api/q/product-inventory',                 lbl:'품목별 LOT 조회'},
    'onProductMovement': {m:'GET',  u:'/api/q/movement-history',                  lbl:'품목별 입출고 현황'},
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
        showQuickOutboundModal();
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
        showPdfInboundUploadModal();
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
      if (conf.u === 'wip') {
        dbgLog('🟡','WIP: '+conf.lbl,'준비 중 (아직 미구현)','#ffa726');
        showToast('info', conf.lbl + ': 준비 중');
        return;
      }
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
