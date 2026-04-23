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

  var SAMPLE_PRODUCTS = [{
    name:'LITHIUM CARBONATE', sellable:200, reserved:0, committed:0,
    outbound_done:0, return_wait:0, total:200, sample:40
  }];
  var SAMPLE_LOTS = [{opening:200, inbound:0, outbound:0, ending:200, status:'OK'}];

  function loadDashboardTables() {
    apiGet('/api/dashboard/stats').then(function(res){
      var d = res.data || res || {};
      renderDashProducts(d.products || SAMPLE_PRODUCTS);
      renderDashLots(d.lots || SAMPLE_LOTS);
    }).catch(function(){
      renderDashProducts(SAMPLE_PRODUCTS);
      renderDashLots(SAMPLE_LOTS);
    });
  }

  function fmtN(v) {
    if (typeof v !== 'number') return (v == null ? '-' : v);
    return v.toLocaleString('ko-KR',{minimumFractionDigits:1,maximumFractionDigits:1});
  }

  function renderDashProducts(rows) {
    var tbody = document.getElementById('dash-products');
    if (!tbody) return;
    var tot = rows.reduce(function(a,r){
      return {sellable:a.sellable+(r.sellable||0),reserved:a.reserved+(r.reserved||0),
              committed:a.committed+(r.committed||0),outbound_done:a.outbound_done+(r.outbound_done||0),
              return_wait:a.return_wait+(r.return_wait||0),total:a.total+(r.total||0),sample:a.sample+(r.sample||0)};
    },{sellable:0,reserved:0,committed:0,outbound_done:0,return_wait:0,total:0,sample:0});
    tbody.innerHTML = rows.map(function(r,i){
      return '<tr><td>'+(i+1)+'</td><td style="text-align:left">'+escapeHtml(r.name)+'</td><td>'+fmtN(r.sellable)+'</td><td>'+fmtN(r.reserved)+'</td><td>'+fmtN(r.committed)+'</td><td>'+fmtN(r.outbound_done)+'</td><td>'+fmtN(r.return_wait)+'</td><td><b>'+fmtN(r.total)+'</b></td><td>'+(r.sample!=null?r.sample:'-')+'</td></tr>';
    }).join('') +
    '<tr class="total-row"><td></td><td style="text-align:left"><b>Total</b></td><td>'+fmtN(tot.sellable)+'</td><td>'+fmtN(tot.reserved)+'</td><td>'+fmtN(tot.committed)+'</td><td>'+fmtN(tot.outbound_done)+'</td><td>'+fmtN(tot.return_wait)+'</td><td>'+fmtN(tot.total)+'</td><td>'+tot.sample+'</td></tr>';
  }

  function renderDashLots(rows) {
    var tbody = document.getElementById('dash-lots');
    if (!tbody) return;
    tbody.innerHTML = rows.map(function(r,i){
      return '<tr><td>'+(i+1)+'</td><td>'+fmtN(r.opening)+'</td><td>'+fmtN(r.inbound)+'</td><td>'+fmtN(r.outbound)+'</td><td>'+fmtN(r.ending)+'</td><td><span style="color:#2e7d32;font-weight:700">'+escapeHtml(r.status||'OK')+'</span></td></tr>';
    }).join('');
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
      var rows = Array.isArray(res) ? res : (res.data || res.rows || []);
      if (!rows.length) {
        c.innerHTML = '<div class="empty" style="padding:60px;text-align:center">No inventory data</div>';
        return;
      }
      var html = '<div style="overflow-x:auto"><table class="data-table"><thead><tr>' +
        '<th>LOT</th><th>SAP</th><th>BL</th><th>Container</th><th>Product</th>' +
        '<th>Status</th><th>Net(MT)</th><th>Balance</th><th>Bags</th><th>Date</th><th>Location</th><th></th>' +
        '</tr></thead><tbody>';
      html += rows.map(function(r){
        return '<tr>' +
          '<td class="mono-cell" style="color:var(--accent)">'+escapeHtml(r.lot||'')+'</td>' +
          '<td class="mono-cell">'+escapeHtml(r.sap||'')+'</td>' +
          '<td class="mono-cell">'+escapeHtml(r.bl||'')+'</td>' +
          '<td class="mono-cell">'+escapeHtml(r.container||'')+'</td>' +
          '<td><span class="tag">'+escapeHtml(r.product||'')+'</span></td>' +
          '<td>'+escapeHtml(r.status||'')+'</td>' +
          '<td class="mono-cell">'+(r.net!=null?Number(r.net).toLocaleString():'-')+'</td>' +
          '<td class="mono-cell">'+(r.balance!=null?Number(r.balance).toLocaleString():'-')+'</td>' +
          '<td class="mono-cell">'+(r.bags||'-')+'</td>' +
          '<td class="mono-cell">'+escapeHtml(r.date||'')+'</td>' +
          '<td><span class="tag">'+escapeHtml(r.location||'-')+'</span></td>' +
          '<td><button class="btn btn-ghost btn-xs" onclick="window.showLotDetail(\''+escapeHtml(r.lot||'')+'\')">Detail</button></td>' +
          '</tr>';
      }).join('');
      html += '</tbody></table></div>';
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
      var rows = res.data || res.rows || (Array.isArray(res)?res:[]);
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
      '<h2>Picked - Outbound Queue</h2>',
      '<div class="toolbar-mini"><button class="btn btn-secondary" onclick="renderPage(\'picked\')">Refresh</button></div>',
      '<div id="picked-loading" style="padding:40px;text-align:center">Loading...</div>',
      '<table class="data-table" id="picked-table" style="display:none">',
      '<thead><tr><th>LOT</th><th>Product</th><th>Qty</th><th>Date</th><th>Location</th></tr></thead>',
      '<tbody id="picked-tbody"></tbody></table>',
      '<div class="empty" id="picked-empty" style="display:none">No data</div>',
      '</section>'
    ].join('');
    apiGet('/api/q2/outbound-confirm-list').then(function(res){
      if (_currentRoute !== route) return;
      var rows = res.data || res.rows || (Array.isArray(res)?res:[]);
      document.getElementById('picked-loading').style.display = 'none';
      if (!rows.length) { document.getElementById('picked-empty').style.display='block'; return; }
      var tbody = document.getElementById('picked-tbody');
      if (tbody) tbody.innerHTML = rows.map(function(r){
        return '<tr><td>'+escapeHtml(r.lot||'')+'</td><td>'+escapeHtml(r.product||'')+'</td><td>'+(r.qty||r.bags||'')+'</td><td>'+escapeHtml(r.date||'')+'</td><td>'+escapeHtml(r.location||'')+'</td></tr>';
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
      '<h2 style="margin:0">📤 출고 현황 (Outbound Status)</h2>',
      '<button class="btn btn-secondary" onclick="renderPage(\'outbound\')" style="margin-left:auto">🔁 새로고침</button>',
      '</div>',
      '<div id="outbound-loading" style="padding:40px;text-align:center;color:var(--text-muted)">⏳ 데이터 로딩 중...</div>',
      '<div style="overflow-x:auto">',
      '<table class="data-table" id="outbound-table" style="display:none">',
      '<thead><tr>',
      '<th>#</th><th>LOT No</th><th>고객사</th><th>출고량(MT)</th>',
      '<th>출발지</th><th>도착지</th><th>출고일자</th><th>유형</th><th>담당자</th><th>비고</th>',
      '</tr></thead>',
      '<tbody id="outbound-tbody"></tbody>',
      '</table>',
      '</div>',
      '<div class="empty" id="outbound-empty" style="display:none;padding:60px;text-align:center;color:var(--text-muted)">📭 출고 데이터 없음</div>',
      '</section>'
    ].join('');

    apiGet('/api/q/outbound-status').then(function(res){
      if (_currentRoute !== route) return;
      var rows = (res.data && res.data.items) || [];
      var total = (res.data && res.data.total) || rows.length;
      document.getElementById('outbound-loading').style.display = 'none';
      if (!rows.length) {
        document.getElementById('outbound-empty').style.display = 'block';
        return;
      }
      var tbody = document.getElementById('outbound-tbody');
      if (tbody) tbody.innerHTML = rows.map(function(r, i){
        var qtyMT = r.qty_kg != null ? fmtN(r.qty_kg / 1000) : '-';
        var date  = (r.movement_date||'').slice(0,10) || '-';
        return '<tr>' +
          '<td class="mono-cell" style="color:var(--text-muted)">'+(i+1)+'</td>' +
          '<td class="mono-cell" style="color:var(--accent);font-weight:600">'+escapeHtml(r.lot_no||'')+'</td>' +
          '<td>'+escapeHtml(r.customer||'-')+'</td>' +
          '<td class="mono-cell" style="text-align:right">'+qtyMT+'</td>' +
          '<td class="mono-cell">'+escapeHtml(r.from_location||'-')+'</td>' +
          '<td class="mono-cell">'+escapeHtml(r.to_location||'-')+'</td>' +
          '<td class="mono-cell">'+escapeHtml(date)+'</td>' +
          '<td><span class="tag">'+escapeHtml(r.source_type||'-')+'</span></td>' +
          '<td>'+escapeHtml(r.actor||'-')+'</td>' +
          '<td style="font-size:11px;color:var(--text-muted)">'+escapeHtml((r.remarks||'').slice(0,40))+'</td>' +
          '</tr>';
      }).join('');
      document.getElementById('outbound-table').style.display = '';
      dbgLog('📤','outbound-page','total='+total+' rows='+rows.length,'#4caf50');
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
    apiGet('/api/q2/return-stats').then(function(res){
      if (_currentRoute !== route) return;
      var rows = res.data || res.rows || res.items || (Array.isArray(res)?res:[]);
      renderReturnRows(rows, route);
    }).catch(function(){
      if (_currentRoute !== route) return;
      // fallback to inventory?status=RETURN
      apiGet('/api/inventory?status=RETURN').then(function(res2){
        if (_currentRoute !== route) return;
        renderReturnRows(res2.data || (Array.isArray(res2)?res2:[]), route);
      }).catch(function(){
        if (_currentRoute !== route) return;
        document.getElementById('return-loading').style.display = 'none';
        document.getElementById('return-empty').style.display = 'block';
      });
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
      '<thead><tr><th>Time</th><th>Tonbag ID</th><th>From</th><th>To</th><th>By</th></tr></thead>',
      '<tbody id="move-tbody"></tbody></table>',
      '<div class="empty" id="move-empty" style="display:none">No movement history</div>',
      '</section>'
    ].join('');
    apiGet('/api/q/movement-history').then(function(res){
      if (_currentRoute !== route) return;
      var rows = res.data || res.rows || (Array.isArray(res)?res:[]);
      document.getElementById('move-loading').style.display = 'none';
      if (!rows.length) { document.getElementById('move-empty').style.display='block'; return; }
      var tbody = document.getElementById('move-tbody');
      if (tbody) tbody.innerHTML = rows.map(function(r){
        return '<tr>' +
          '<td class="mono-cell">'+escapeHtml(r.moved_at||r.date||'')+'</td>' +
          '<td class="mono-cell">'+escapeHtml(r.sub_lt||r.barcode||'')+'</td>' +
          '<td class="mono-cell">'+escapeHtml(r.from_location||'')+'</td>' +
          '<td class="mono-cell" style="color:var(--accent)">'+escapeHtml(r.to_location||'')+'</td>' +
          '<td>'+escapeHtml(r.moved_by||'system')+'</td></tr>';
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
      var rows = Array.isArray(res)?res:(res.data||res.rows||[]);
      document.getElementById('log-loading').style.display = 'none';
      if (!rows.length) { document.getElementById('log-empty').style.display='block'; return; }
      var tbody = document.getElementById('log-tbody');
      if (tbody) tbody.innerHTML = rows.map(function(r){
        return '<tr>' +
          '<td class="mono-cell">'+escapeHtml(r.time||r.timestamp||'')+'</td>' +
          '<td>'+escapeHtml(r.type||r.action||'')+'</td>' +
          '<td class="mono-cell">'+escapeHtml(r.lot||'')+'</td>' +
          '<td>'+escapeHtml(r.note||r.memo||r.detail||'')+'</td></tr>';
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
      var rows = Array.isArray(res)?res:(res.data||res.rows||[]);
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
     8b. 수동 입고 (Excel 업로드) — Phase 4-B 네이티브 구현
     =================================================== */
  function showInboundManualUploadModal() {
    var html = [
      '<div style="max-width:640px">',
      '  <h2 style="margin:0 0 12px 0">📊 수동 입고 — Excel 업로드</h2>',
      '  <p style="color:var(--text-muted);margin:0 0 16px 0;font-size:.9rem">',
      '    엑셀 파일(.xlsx/.xls)을 선택하세요. 컬럼: <code>lot_no, sap_no, bl_no, container_no, product, net_weight, stock_date</code> 등',
      '  </p>',
      '  <div id="inb-drop-zone" style="border:2px dashed var(--border);border-radius:8px;padding:32px 16px;text-align:center;background:var(--bg-hover);cursor:pointer;margin-bottom:16px">',
      '    <div style="font-size:2.5rem;margin-bottom:8px">📁</div>',
      '    <div id="inb-file-name" style="color:var(--text-muted)">클릭 또는 파일을 여기에 드롭하세요</div>',
      '  </div>',
      '  <input type="file" id="inb-file-input" accept=".xlsx,.xls" style="display:none">',
      '  <div id="inb-progress" style="display:none;margin-bottom:16px">',
      '    <div style="background:var(--bg-hover);border-radius:4px;height:8px;overflow:hidden">',
      '      <div id="inb-progress-bar" style="background:var(--accent);height:100%;width:0%;transition:width .3s"></div>',
      '    </div>',
      '    <div id="inb-progress-text" style="font-size:.85rem;color:var(--text-muted);margin-top:4px">준비 중...</div>',
      '  </div>',
      '  <div id="inb-result" style="margin-bottom:16px"></div>',
      '  <div style="display:flex;gap:8px;justify-content:flex-end">',
      '    <button id="inb-cancel-btn" class="btn btn-ghost">닫기</button>',
      '    <button id="inb-upload-btn" class="btn btn-primary" disabled>업로드</button>',
      '  </div>',
      '</div>'
    ].join('\n');

    showDataModal('', html);

    var fileInput = document.getElementById('inb-file-input');
    var dropZone  = document.getElementById('inb-drop-zone');
    var fileName  = document.getElementById('inb-file-name');
    var uploadBtn = document.getElementById('inb-upload-btn');
    var cancelBtn = document.getElementById('inb-cancel-btn');
    var progress  = document.getElementById('inb-progress');
    var progressBar = document.getElementById('inb-progress-bar');
    var progressText = document.getElementById('inb-progress-text');
    var resultBox = document.getElementById('inb-result');

    var selectedFile = null;

    function setFile(f) {
      if (!f) return;
      var okExt = /\.(xlsx|xls)$/i.test(f.name);
      if (!okExt) {
        showToast('error', 'Excel 파일(.xlsx/.xls)만 가능합니다. 받은 파일: ' + f.name);
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
    dropZone.addEventListener('dragleave', function(e){ dropZone.style.background='var(--bg-hover)'; });
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
      xhr.open('POST', API + '/api/inbound/bulk-import-excel');
      xhr.upload.onprogress = function(e){
        if (e.lengthComputable) {
          var pct = Math.round((e.loaded / e.total) * 70) + 10;  // 10~80%
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
          var d = body.data || {};
          progressText.textContent = '완료: 성공 ' + (d.success_count||0) + ' / 실패 ' + (d.fail_count||0) + ' / 총 ' + (d.total||0);
          var errHtml = '';
          if (d.errors && d.errors.length) {
            errHtml = '<details style="margin-top:8px"><summary style="cursor:pointer;color:var(--warning)">⚠️ ' + d.errors.length + '건 실패 상세</summary><table class="data-table" style="margin-top:8px;font-size:.85rem"><thead><tr><th>행</th><th>LOT</th><th>사유</th></tr></thead><tbody>' +
              d.errors.map(function(er){
                return '<tr><td>'+er.row+'</td><td>'+escapeHtml(er.lot_no||'-')+'</td><td>'+escapeHtml(er.reason||'')+'</td></tr>';
              }).join('') + '</tbody></table></details>';
          }
          resultBox.innerHTML =
            '<div style="padding:12px;background:var(--bg-hover);border-radius:6px;border-left:4px solid var(--success)">' +
            '<div style="font-weight:600;margin-bottom:4px">✅ ' + escapeHtml(body.message||'완료') + '</div>' +
            '<div style="color:var(--text-muted);font-size:.85rem">파일: ' + escapeHtml(d.filename||'-') + ' · 헤더 행: ' + (d.header_row!=null?d.header_row+1:'?') + ' · 매핑 컬럼: ' + ((d.matched_columns||[]).join(', ')) + '</div>' +
            errHtml +
            '</div>';
          showToast('success', body.message || '입고 완료');
          dbgLog('🟢','BULK-IMPORT OK', body.message, '#66bb6a');
          // inventory 페이지 새로고침
          if (_currentRoute === 'inventory' && typeof loadInventoryPage === 'function') loadInventoryPage();
          if (typeof loadKpi === 'function') loadKpi();
        } else {
          var errMsg = (body && (body.detail || body.error || body.message)) || ('HTTP ' + xhr.status);
          progressText.textContent = '실패';
          progressBar.style.background = 'var(--danger)';
          resultBox.innerHTML =
            '<div style="padding:12px;background:var(--bg-hover);border-radius:6px;border-left:4px solid var(--danger)">' +
            '<div style="font-weight:600">❌ 업로드 실패</div>' +
            '<div style="color:var(--text-muted);font-size:.85rem;margin-top:4px">' + escapeHtml(String(errMsg)) + '</div>' +
            '</div>';
          showToast('error', '업로드 실패: ' + errMsg);
          dbgLog('🔴','BULK-IMPORT FAIL', String(errMsg), '#ef5350');
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
  window.showInboundManualUploadModal = showInboundManualUploadModal;

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
      st('sb-unallocated','Unallocated '+(d.unallocated_bags||d.position_missing||400));
      st('sb-scan-fail','Scan fail '+(d.scan_failure_rate||'-'));
      st('sb-lot-age','LOT avg age '+(d.lot_avg_age_days||6.2)+'d');
    }).catch(function(){});
    apiGet('/api/health').then(function(res){
      var h=res.data||res||{};
      st('sb-modules','Modules: '+(h.modules_loaded!==undefined?h.modules_loaded:(h.engine_available?7:0))+'/'+(h.modules_total||8));
    }).catch(function(){ st('sb-modules','Modules: ?/?'); });
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
    'onDoUpdate':        {m:'POST', u:'/api/action3/do-update',                   lbl:'D/O 후속 연결'},
    'onReturnDialog':    {m:'POST', u:'/api/menu/-show-return-dialog',           lbl:'반품 (재입고)'},
    'onReturnInboundUpload': {m:'POST', u:'/api/menu/-on-return-inbound-upload', lbl:'반품 입고 Excel'},
    'onReturnStatistics': {m:'GET', u:'/api/q2/return-stats',                   lbl:'반품 사유 통계'},
    'onRecentFiles':     {m:'GET',  u:'/api/q2/recent-files',                   lbl:'최근 파일'},
    'onExit':            {m:'JS',   u:'exit',                                    lbl:'종료'},

    /* ── 입고 메뉴 ── */
    'onOnPdfInbound':    {m:'JS',   u:'scan',                                    lbl:'PDF 스캔 입고'},
    /* v864.3 Phase 4-B: 수동 입고는 네이티브 모달로 처리 (tkinter filedialog 대체) */
    'onInboundManual':   {m:'JS', u:'inbound-upload', lbl:'수동 입고'},
    'onInboundList':     {m:'JS',   u:'inbound',                                  lbl:'입고 목록'},
    'onInboundCancel':   {m:'JS',   u:'wip',                                     lbl:'입고 취소'},

    /* ── 출고 메뉴 ── */
    'onOnQuickOutbound': {m:'POST', u:'/api/menu/-on-s1-onestop-outbound',       lbl:'즉시 출고'},
    'onOutboundScheduled': {m:'JS', u:'wip',                                     lbl:'출고 예정'},
    'onOutboundConfirm': {m:'JS',   u:'wip',                                     lbl:'출고 확정'},
    'onOutboundHistory': {m:'GET',  u:'/api/q/outbound-status',                  lbl:'출고 이력'},
    'onOutboundStatus':  {m:'JS',   u:'outbound',                                 lbl:'출고 현황'},
    'onApprovalHistory': {m:'GET',  u:'/api/q/approval-history',                 lbl:'승인 이력 조회'},

    /* ── 재고 메뉴 ── */
    'onInventoryList':   {m:'JS',   u:'inventory',                               lbl:'재고 조회'},
    'onInventoryMove':   {m:'POST', u:'/api/menu/-on-tonbag-location-upload',    lbl:'위치 이동'},
    'onInventoryAllocation': {m:'POST', u:'/api/menu/-on-allocation-input-unified', lbl:'위치 배정'},
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
    'tb-pdf-inbound':    {m:'JS',   u:'scan',                                     lbl:'PDF 입고'},
    'tb-quick-outbound': {m:'POST', u:'/api/menu/-on-s1-onestop-outbound',        lbl:'즉시 출고'},
    'tb-return':         {m:'JS',   u:'return',                                   lbl:'반품'},
    'tb-inventory':      {m:'JS',   u:'inventory',                                lbl:'재고 조회'},
    'tb-integrity':      {m:'GET',  u:'/api/action/integrity-check',              lbl:'정합성'},
    'tb-backup':         {m:'POST', u:'/api/action/backup-create',                lbl:'백업'},
    'tb-settings':       {m:'POST', u:'/api/menu/-on-settings',                   lbl:'설정'},

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
