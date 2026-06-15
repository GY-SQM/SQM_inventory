/* =======================================================================
   SQM Inventory v8.7.0 - sqm-inline.js
   Rebuilt: 2026-04-21  Ruby (Senior Software Architect)
   Updated: 2026-04-27  Draggable modals, parse log panel, step badge, ESC guard
   ======================================================================= */
(function () {
  'use strict';
  if (window.__SQM_INLINE_INSTALLED__) return;
  window.__SQM_INLINE_INSTALLED__ = true;


  // [fix v2] sqm_base URL 파라미터 → window.SQM_API_BASE → location.origin 순으로 읽기
  function _getApiBase() {
    if (window.SQM_API_BASE) return window.SQM_API_BASE;
    try {
      var p = new URLSearchParams(location.search).get('sqm_base');
      if (p) { window.SQM_API_BASE = p; return p; }
    } catch(_) {}
    return (window.location && window.location.origin) || '';
  }
  var API = _getApiBase(); // 초기값 (하위 호환)



  /* ===================================================
     0. SAFE HELPERS (sqm-core.js 로드 실패 방어)
     =================================================== */
  // [fix F-12] sqm-core.js 미로드 시 ReferenceError 방지 — 안전 showToast 폴백
  function showToast(type, msg) {
    if (typeof window.showToast === 'function') {
      return window.showToast.apply(window, arguments);
    }
    console.warn('[SQM showToast 폴백]', type, msg);
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
  window.extractRows = extractRows;







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
    if (document.body) document.body.setAttribute('data-theme', theme);
    var vm = store.getItem('sqm_view_mode') || 'mt';
    document.documentElement.setAttribute('data-view-mode', vm);
  }

  function toggleTheme() {
    var cur = document.documentElement.getAttribute('data-theme') || 'dark';
    var next = cur === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    if (document.body) document.body.setAttribute('data-theme', next);
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
    document.querySelectorAll('.submenu-parent.open').forEach(function(el){
      el.classList.remove('open');
    });
    document.querySelectorAll('.submenu-dropdown').forEach(function(el){
      el.style.display = '';
    });
    document.querySelectorAll('.menu-dropdown.open,.menu-dropdown.active').forEach(function(el){
      el.classList.remove('open'); el.classList.remove('active');
    });
    document.querySelectorAll('.menu-item.active,.nav-item.open').forEach(function(el){
      el.classList.remove('active'); el.classList.remove('open');
    });
  }

  function closeSiblingSubmenus(parent) {
    var menu = parent && parent.closest ? parent.closest('.menu-dropdown') : null;
    if (!menu) return;
    menu.querySelectorAll('.submenu-parent.open').forEach(function(el){
      if (el !== parent) el.classList.remove('open');
    });
    menu.querySelectorAll('.submenu-dropdown').forEach(function(el){
      if (!parent.contains(el)) el.style.display = '';
    });
  }

  /* ===================================================
     5. ROUTER
     =================================================== */
  var _currentRoute = null;
  // sqm-core.js가 이미 getCurrentRoute 권위를 가진다. 없을 때만 레거시 폴백을 둔다.
  if (typeof window.getCurrentRoute !== 'function') window.getCurrentRoute = function(){ return _currentRoute; };

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

  // [fix F-11] 내부 renderPage → _navigateAndSync 로 별칭 추가해 window.renderPage 혼동 방지
  // 기존 이름도 유지 (내부 참조 다수이므로 alias 방식)
  function renderPage(route) {
    // sqm-core.js의 window.renderPage가 권위 라우터. 로컬 _currentRoute 동기화 후 위임.
    _currentRoute = route;
    window.renderPage(route);
  }
  var _navigateAndSync = renderPage;  // [fix F-11] 명확한 별칭 — 순환참조 위험 명시 방지용


  // P2-1 (2026-05-17): window.renderPage 및 getCurrentRoute는 sqm-core.js 버전이 권위
  // (sqm-inline.js의 renderPage는 내부 포워더, window 재정의 불필요)
  // allocation: sqm-inline의 단순화 버전을 window에 노출해 sqm-core.js가 사용하게 함

  /* ===================================================
     6. DASHBOARD
     =================================================== */
  var _kpiTimer = null;


  /* ===================================================
     7a. PAGE: Inventory
     =================================================== */

  /* ── Inventory 탭 필터/검색 핸들러 ─────────────────────────────── */
  var _invAllRows = [];  // 전체 행 캐시 (필터용)



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

  /* ===================================================
     7c. PAGE: Picked
     =================================================== */
  /* ===================================================
     7c. PAGE: Picked — 2단 구조 (LOT 요약 + 톤백 상세)
     =================================================== */

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
      var tbl = '<table class="data-table"><thead><tr><th>#</th><th>톤백ID</th><th>중량(kg)</th><th>위치</th><th>상태</th><th>Title Transfer Date</th></tr></thead><tbody>';
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
    'SOLD':'#388e3c','RETURN':'#c62828','HOLD':'#616161'
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

  function renderReturnRows(rows, route) {
    if (_currentRoute !== route) return;
    document.getElementById('return-loading').style.display = 'none';
    if (!rows.length) { document.getElementById('return-empty').style.display='block'; return; }
    var tbody = document.getElementById('return-tbody');
    if (tbody) tbody.innerHTML = rows.map(function(r, _i){
      return '<tr><td class="mono-cell" style="color:var(--text-muted);text-align:center">'+(_i+1)+'</td><td>'+escapeHtml(r.lot||'')+'</td><td>'+escapeHtml(r.product||'')+'</td><td>'+(r.bags||r.qty||'')+'</td><td>'+escapeHtml(r.date||'')+'</td><td>'+escapeHtml(r.reason||'')+'</td></tr>';
    }).join('');
    document.getElementById('return-table').style.display = '';
  }

  /* ===================================================
     7f. PAGE: Move
     =================================================== */

  window.executeMove = function() {
    var lotNo = (document.getElementById('move-lot-no')||{}).value||'';
    var dest = (document.getElementById('move-dest')||{}).value||'';
    if (!lotNo||!dest) { showToast('warning','Enter LOT No and destination'); return; }
    apiPost('/api/action2/inventory-move',{lot_no:lotNo,destination:dest})
      .then(function(){ showToast('success',lotNo+' moved to '+dest); renderPage('move'); })
      .catch(function(e){
        if (e.status===501) showToast('info','Move (coming soon)');
        else showToast('error','Move failed: '+(e.message||String(e)));
      });
  };


  /* ===================================================
     7h. PAGE: Scan + PDF Upload
     =================================================== */

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
      /* --- Tab 4: 완료 (Phase D placeholder) --- */
      '    <div class="oo-tab-pane" data-pane="4">',
      '      <div class="oo-tab-placeholder">',
      '        <div class="icon">✅</div>',
      '        <div style="font-weight:700;margin-top:12px">④ 완료</div>',
      '        <div style="margin-top:6px">Tab 3 검증 통과 후 활성화됩니다.</div>',
      '        <div class="phase">Sprint 1-3 Phase D 예정</div>',
      '        <div style="margin-top:16px;font-size:11px">예정 기능: 📦 확정건 출고 완료 ▶ · ✅ 승인 → FINALIZED · 완료 이력 Treeview · 📋 감사 로그 sub-popup (CSV export)</div>',
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
    if (!lot || !act) { showToast('warning', 'LOT NO 와 실제(kg) 값 필요'); return; }
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
  window.ooMoveToScan = async function() {
    if (_ooState.selectedTonbags.size === 0) {
      showToast('warning', '선택된 톤백이 없습니다');
      return;
    }
    // Case B 가드: 선택 재고의 LOT 이 전부 일반창고(위치 미상)면 스캔 위치검증 의미가 적음 → 경고
    try {
      var _lots = {};
      _ooState.selectedTonbags.forEach(function(k){
        var s = String(k); var lot = s.substring(0, s.lastIndexOf('.')) || s; _lots[lot] = 1;
      });
      var _lotKeys = Object.keys(_lots);
      if (_lotKeys.length) {
        var _res = await apiGet('/api/outbound/lot-qty/lots');
        var _items = (_res && _res.data && _res.data.items) || [];
        var _locMap = {}; _items.forEach(function(it){ _locMap[it.lot_no] = !!it.located; });
        var _anyLocated = _lotKeys.some(function(l){ return _locMap[l]; });
        if (!_anyLocated) {
          if (!(await window.sqmConfirmAsync('⚠️ 선택한 재고가 모두 일반창고(위치 미상)입니다.\n\n랙 위치가 없어 스캔 위치 검증의 의미가 적습니다.\n위치 추적이 필요 없다면 「📦 LOT 수량 출고(스캔없음)」이 더 적합합니다.\n\n그래도 스캔 검증으로 진행할까요?'))) return;
        }
      }
    } catch (e) { /* 조회 실패 시 가드 생략, 정상 흐름 유지 */ }
    if (!(await window.sqmConfirmAsync('📦 WAIT_SCAN 진입\n\n선택된 톤백 ' + _ooState.selectedTonbags.size + '개로 스캔 검증 단계로 이동합니다.\n계속하시겠습니까?'))) return;
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
    xhr.open('POST', _getApiBase() + '/api/outbound/onestop-scan-parse');
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
    if (!uid || !act) { showToast('warning', '톤백 ID와 실제(kg) 필요'); return; }
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
    else if (hasWarn) showToast('warning', '⚠️ 일부 편차 — 검토 후 진행');
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
  window.ooMoveToFinalize = async function() {
    var hasStop = _ooState.validationResults.some(function(r){ return r.level === 'stop'; });
    if (hasStop) {
      showToast('error', '🚫 하드스톱 발견 — FINALIZED 진입 불가');
      return;
    }
    var hasWarn = _ooState.validationResults.some(function(r){ return r.level === 'warn'; });
    var msg = '✅ FINALIZED 진입\n\n검증 통과: ' + _ooState.selectedTonbags.size + '개 톤백\n' +
              (hasWarn ? '⚠️ 일부 경고 있음 — 검토하셨나요?\n' : '') +
              'Tab 4 에서 출고 확정합니다. 계속하시겠습니까?';
    if (!(await window.sqmConfirmAsync(msg))) return;
    _ooSetState('FINALIZED');
    setTimeout(function(){ window.ooSwitchTab(4); }, 300);
    showToast('success', 'FINALIZED 진입 — Tab 4 에서 출고 확정 (Sprint 1-3-D 예정)');
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

    submitBtn.addEventListener('click', async function() {
      var payload = {
        lot_no: lotInput.value.trim(),
        count: parseInt(cntInput.value, 10),
        customer: customerInput.value.trim(),
        reason: reasonInput.value.trim(),
        operator: operatorInput.value.trim(),
      };
      if (!(await window.sqmConfirmAsync('LOT ' + payload.lot_no + ' 에서 ' + payload.count + '개 톤백을 ' + payload.customer + ' 로 출고하시겠습니까?'))) return;

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
            dbgLog('🟢','QUICK-SOLD OK', res.message, '#66bb6a');
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
            dbgLog('🔴','QUICK-SOLD FAIL', errMsg, '#ef5350');
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


  /* ===================================================
     대량 이동 승인 모달 (F004-B) — PENDING 배치 목록 조회 + 승인/반려
     =================================================== */
  function showBatchMoveApprovalModal() {
    var REASONS = {
      RELOCATE: '일반 재배치', RACK_REPAIR: '랙 수리',
      INVENTORY_AUDIT: '재고 실사', PICKING_OPT: '피킹 최적화',
      RETURN_PUTAWAY: '반품 적치', CORRECTION: '위치 보정', OTHER: '기타'
    };

    function renderBatches(rows) {
      if (!rows || !rows.length) {
        return '<p style="color:var(--text-muted);text-align:center;padding:24px">대기 중인 이동 요청이 없습니다.</p>';
      }
      var html = '<table class="data-table" style="width:100%;font-size:.85rem"><thead><tr>'
        + '<th>배치 ID</th><th>건수</th><th>사유</th><th>요청자</th><th>요청시각</th><th>비고</th><th>처리</th>'
        + '</tr></thead><tbody>';
      rows.forEach(function(b) {
        var reasonLabel = REASONS[b.reason_code] || b.reason_code || '-';
        html += '<tr>'
          + '<td style="font-family:monospace;font-size:.8rem">' + escapeHtml(b.batch_id || '-') + '</td>'
          + '<td style="text-align:center">' + (b.total_count || 0) + '</td>'
          + '<td>' + escapeHtml(reasonLabel) + '</td>'
          + '<td>' + escapeHtml(b.submitted_by || '-') + '</td>'
          + '<td style="font-size:.78rem">' + escapeHtml((b.submitted_at || '').replace('T',' ').substring(0,16)) + '</td>'
          + '<td style="font-size:.78rem;max-width:120px;overflow:hidden;text-overflow:ellipsis">' + escapeHtml(b.note || '') + '</td>'
          + '<td style="white-space:nowrap">'
          + '<button class="btn btn-sm" style="background:var(--accent);color:#fff;margin-right:4px" '
          + 'onclick="window._batchMoveAction(\'approve\',\'' + escapeHtml(b.batch_id) + '\')">'
          + '✅ 승인</button>'
          + '<button class="btn btn-sm" style="background:var(--danger,#c62828);color:#fff" '
          + 'onclick="window._batchMoveAction(\'reject\',\'' + escapeHtml(b.batch_id) + '\')">'
          + '❌ 반려</button>'
          + '</td></tr>';
      });
      html += '</tbody></table>';
      return html;
    }

    function openModal() {
      var html = [
        '<div style="width:860px;max-width:94vw">',
        '  <h2 style="margin:0 0 12px 0">📦 대량 이동 승인</h2>',
        '  <p style="color:var(--text-muted);font-size:.88rem;margin:0 0 14px 0">',
        '    PENDING 상태의 대량 이동 요청을 확인하고 승인 또는 반려합니다.<br>',
        '    승인 시 All-or-Nothing 방식으로 즉시 DB에 반영됩니다.',
        '  </p>',
        '  <div id="bma-body" style="min-height:80px;display:flex;align-items:center;justify-content:center">',
        '    <span style="color:var(--text-muted)">불러오는 중…</span>',
        '  </div>',
        '  <div style="display:flex;justify-content:flex-end;margin-top:14px;gap:8px">',
        '    <button class="btn btn-ghost" onclick="window._bmaRefresh()">🔄 새로고침</button>',
        '    <button class="btn btn-ghost" id="bma-close-btn">닫기</button>',
        '  </div>',
        '</div>'
      ].join('\n');

      showDataModal('', html);
      document.getElementById('bma-close-btn').onclick = function() {
        document.getElementById('sqm-modal').style.display = 'none';
      };

      window._bmaRefresh = function() {
        var el = document.getElementById('bma-body');
        if (!el) return;
        el.innerHTML = '<span style="color:var(--text-muted)">불러오는 중…</span>';
        fetch(_getApiBase() + '/api/tonbag/batch-move/pending')
          .then(function(r) { return r.json(); })
          .then(function(res) {
            if (el) el.innerHTML = renderBatches(res.data || []);
          })
          .catch(function(e) {
            if (el) el.innerHTML = '<p style="color:var(--danger,#c62828)">로드 실패: ' + escapeHtml(String(e)) + '</p>';
          });
      };

      window._batchMoveAction = async function(action, batchId) {
        var label = action === 'approve' ? '승인' : '반려';
        var reason = '';
        if (action === 'reject') {
          reason = prompt('반려 사유를 입력하세요 (선택):', '') || '';
        }
        if (action === 'approve' && !(await window.sqmConfirmAsync('배치 ' + batchId + ' 를 승인하시겠습니까?\n승인 즉시 DB에 반영됩니다.'))) return;
        var url = _getApiBase() + '/api/tonbag/batch-move/' + action + '/' + encodeURIComponent(batchId);
        fetch(url, {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({approver: 'supervisor', reason: reason})
        })
          .then(function(r) { return r.json(); })
          .then(function(res) {
            if (res.ok === false || res.detail) {
              alert(label + ' 실패: ' + (res.detail || res.message || JSON.stringify(res)));
            } else {
              alert(label + ' 완료\n' + (res.message || ''));
              window._bmaRefresh();
            }
          })
          .catch(function(e) { alert(label + ' 오류: ' + String(e)); });
      };

      window._bmaRefresh();
    }

    openModal();
  }
  window.showBatchMoveApprovalModal = showBatchMoveApprovalModal;


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
    submit.addEventListener('click', async function(){
      if (!(await window.sqmConfirmAsync('승인 완료된 Allocation 을 모두 RESERVED 로 반영합니다. 계속할까요?'))) return;
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



  /* ═══ 선사 프로파일 관리 모달 ═══ */
  function showCarrierProfileModal() {
    function _renderCarrierList(profiles) {
      if (!profiles.length) return '<p style="color:var(--text-muted);text-align:center;padding:20px">등록된 선사 프로파일이 없습니다.</p>';
      return '<table class="data-table" style="width:100%;font-size:.88rem"><thead><tr>'
        + '<th>선사 ID</th><th>표시명</th><th>기본품목</th><th>기본중량(kg)</th><th>메모</th><th>액션</th>'
        + '</tr></thead><tbody>'
        + profiles.map(function(p) {
            return '<tr>'
              + '<td style="font-weight:600">' + escapeHtml(p.carrier_id) + '</td>'
              + '<td>' + escapeHtml(p.display_name) + '</td>'
              + '<td>' + escapeHtml(p.default_product || '-') + '</td>'
              + '<td style="text-align:right">' + (p.bag_weight_kg || 500) + '</td>'
              + '<td style="color:var(--text-muted);font-size:.8rem">' + escapeHtml(p.note || '') + '</td>'
              + '<td>'
              + '<button class="btn btn-sm" onclick="window._cpEdit(' + JSON.stringify(p.carrier_id) + ')">✏️</button>'
              + ' <button class="btn btn-sm" style="color:var(--danger)" onclick="window._cpDelete(' + JSON.stringify(p.carrier_id) + ')">🗑</button>'
              + '</td>'
              + '</tr>';
          }).join('')
        + '</tbody></table>';
    }

    function _cpLoad() {
      var listEl = document.getElementById('cp-list');
      if (listEl) listEl.innerHTML = '<p style="color:var(--text-muted);padding:12px">로딩 중...</p>';
      fetch(_getApiBase() + '/api/carriers')
        .then(function(r) { return r.json(); })
        .then(function(d) {
          if (listEl) listEl.innerHTML = _renderCarrierList(d.data || []);
        })
        .catch(function(e) {
          if (listEl) listEl.innerHTML = '<p style="color:var(--danger)">로드 실패: ' + escapeHtml(String(e)) + '</p>';
        });
    }

    var formHtml = [
      '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-bottom:12px">',
      '  <div><label style="font-size:12px;color:var(--text-muted)">선사 ID (필수)</label><input id="cp-f-id" type="text" placeholder="예: Maersk" style="width:100%;margin-top:2px;padding:6px;background:var(--bg-hover);color:var(--fg);border:1px solid var(--border);border-radius:4px"></div>',
      '  <div><label style="font-size:12px;color:var(--text-muted)">표시명 (필수)</label><input id="cp-f-name" type="text" placeholder="예: 머스크" style="width:100%;margin-top:2px;padding:6px;background:var(--bg-hover);color:var(--fg);border:1px solid var(--border);border-radius:4px"></div>',
      '  <div><label style="font-size:12px;color:var(--text-muted)">기본 품목</label><input id="cp-f-product" type="text" placeholder="예: PP" style="width:100%;margin-top:2px;padding:6px;background:var(--bg-hover);color:var(--fg);border:1px solid var(--border);border-radius:4px"></div>',
      '  <div><label style="font-size:12px;color:var(--text-muted)">기본 중량(kg)</label><input id="cp-f-weight" type="number" value="500" min="1" style="width:100%;margin-top:2px;padding:6px;background:var(--bg-hover);color:var(--fg);border:1px solid var(--border);border-radius:4px"></div>',
      '  <div style="grid-column:1/-1"><label style="font-size:12px;color:var(--text-muted)">메모</label><input id="cp-f-note" type="text" placeholder="특이사항 (선택)" style="width:100%;margin-top:2px;padding:6px;background:var(--bg-hover);color:var(--fg);border:1px solid var(--border);border-radius:4px"></div>',
      '</div>',
      '<button class="btn btn-primary" onclick="window._cpSave()">💾 저장</button>',
    ].join('');

    var html = [
      '<div style="max-width:760px">',
      '<h2 style="margin:0 0 16px 0">🚢 선사 프로파일 관리</h2>',
      '<p style="color:var(--text-muted);font-size:.85rem;margin:0 0 16px 0">선사별 기본 품목·중량을 설정합니다. OneStop 입고 시 선사 선택만으로 파싱 기준값이 자동 적용됩니다.</p>',
      '<h3 style="margin:0 0 8px 0;font-size:.95rem">신규 등록 / 수정</h3>',
      formHtml,
      '<hr style="border:none;border-top:1px solid var(--border);margin:16px 0">',
      '<h3 style="margin:0 0 8px 0;font-size:.95rem">등록된 선사 프로파일</h3>',
      '<div id="cp-list">로딩 중...</div>',
      '</div>',
    ].join('');

    showDataModal('', html);
    _cpLoad();

    window._cpSave = function() {
      var id      = (document.getElementById('cp-f-id')      || {}).value || '';
      var name    = (document.getElementById('cp-f-name')    || {}).value || '';
      var product = (document.getElementById('cp-f-product') || {}).value || '';
      var weight  = parseFloat((document.getElementById('cp-f-weight') || {}).value || '500') || 500;
      var note    = (document.getElementById('cp-f-note')    || {}).value || '';
      if (!id.trim()) { showToast('error', '선사 ID를 입력하세요'); return; }
      if (!name.trim()) { showToast('error', '표시명을 입력하세요'); return; }
      var isEdit = window._cpEditId && window._cpEditId === id.trim();
      var method = isEdit ? 'PUT' : 'POST';
      var url    = isEdit ? (_getApiBase() + '/api/carriers/' + encodeURIComponent(id.trim())) : (_getApiBase() + '/api/carriers');
      fetch(url, { method: method, headers: {'Content-Type':'application/json'},
        body: JSON.stringify({ carrier_id: id.trim(), display_name: name.trim(),
          default_product: product.trim(), bag_weight_kg: weight, note: note.trim() }) })
        .then(function(r) { return r.json(); })
        .then(function(d) {
          if (d.ok || d.success) {
            showToast('success', (isEdit ? '수정' : '등록') + ' 완료: ' + id.trim());
            window._cpEditId = null;
            ['cp-f-id','cp-f-name','cp-f-product','cp-f-note'].forEach(function(fid){
              var el = document.getElementById(fid); if (el) el.value = '';
            });
            var wEl = document.getElementById('cp-f-weight'); if (wEl) wEl.value = '500';
            _cpLoad();
          } else { showToast('error', d.detail || d.message || '저장 실패'); }
        })
        .catch(function(e) { showToast('error', '네트워크 오류: ' + String(e)); });
    };

    window._cpEdit = function(cid) {
      fetch(_getApiBase() + '/api/carriers/' + encodeURIComponent(cid))
        .then(function(r) { return r.json(); })
        .then(function(p) {
          window._cpEditId = cid;
          var set = function(id, v) { var el = document.getElementById(id); if (el) el.value = v; };
          set('cp-f-id',      p.carrier_id || '');
          set('cp-f-name',    p.display_name || '');
          set('cp-f-product', p.default_product || '');
          set('cp-f-weight',  p.bag_weight_kg || 500);
          set('cp-f-note',    p.note || '');
          showToast('info', cid + ' 수정 모드');
        })
        .catch(function(e) { showToast('error', '조회 실패: ' + String(e)); });
    };

    window._cpDelete = async function(cid) {
      if (!(await window.sqmConfirmAsync(cid + ' 프로파일을 삭제하시겠습니까?'))) return;
      fetch(_getApiBase() + '/api/carriers/' + encodeURIComponent(cid), { method: 'DELETE' })
        .then(function(r) { return r.json(); })
        .then(function(d) {
          if (d.ok || d.success) { showToast('success', cid + ' 삭제 완료'); _cpLoad(); }
          else { showToast('error', d.detail || '삭제 실패'); }
        })
        .catch(function(e) { showToast('error', '네트워크 오류: ' + String(e)); });
    };
  }
  window.showCarrierProfileModal = showCarrierProfileModal;




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
    submit.addEventListener('click', async function(){
      var rows = parseRows();
      if (!rows.length) return;
      var customer = cust.value.trim();
      var totalN = rows.reduce(function(s,r){return s+r.count;},0);
      if (!(await window.sqmConfirmAsync('총 ' + rows.length + '개 LOT · ' + totalN + '개 톤백을 ' + customer + ' 로 출고합니다. 계속?'))) return;

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
     8h-2. v8.7.4 MVP-2: LOT 수량 출고 (스캔 없음)
     전량/부분 + 샘플 동반 + 위치 미상 — POST /api/outbound/lot-qty
     =================================================== */
  function showLotQtyOutboundModal() {
    var today = new Date().toISOString().slice(0, 10);
    var html = [
      '<div style="max-width:580px">',
      '  <h2 style="margin:0 0 6px 0">📦 LOT 수량 출고 <span style="font-size:.8rem;color:var(--text-muted)">(스캔 없음)</span></h2>',
      '  <p style="color:var(--text-muted);margin:0 0 12px 0;font-size:.85rem">',
      '    바코드 스캔 없이 LOT 단위로 출고합니다. 일반창고(위치 미상)·입고 즉시 출고·부분 출고에 사용하세요.',
      '  </p>',
      '  <div style="display:grid;grid-template-columns:110px 1fr;gap:10px;align-items:center;margin-bottom:10px">',
      '    <label style="font-weight:600">LOT 번호</label>',
      '    <div style="display:flex;gap:6px;align-items:center">',
      '      <select id="lq-lot-select" style="flex:1;min-width:0;padding:8px;background:var(--bg-hover);color:var(--text);border:1px solid var(--border);border-radius:6px"><option value="">⏳ 가용 LOT 불러오는 중...</option></select>',
      '      <button type="button" id="lq-lot-sort" class="btn btn-ghost" style="padding:7px 10px;white-space:nowrap" title="LOT 번호 정렬 전환">↑ 오름차순</button>',
      '    </div>',
      '    <label style="font-weight:600">출고 방식</label>',
      '    <div style="display:flex;gap:14px;align-items:center">',
      '      <label style="display:flex;align-items:center;gap:5px"><input type="radio" name="lq-mode" value="full" checked> 전량</label>',
      '      <label style="display:flex;align-items:center;gap:5px"><input type="radio" name="lq-mode" value="part"> 부분(톤백 선택)</label>',
      '    </div>',
      '  </div>',
      '  <div id="lq-loc-warn" style="display:none;margin:-4px 0 10px 0;padding:9px 11px;border-radius:6px;font-size:.84rem;line-height:1.45"></div>',
      '  <div id="lq-tonbag-wrap" style="display:none;margin-bottom:10px">',
      '    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">',
      '      <span style="font-weight:600;font-size:.85rem">출고할 톤백 선택</span>',
      '      <span style="font-size:.8rem;color:var(--text-muted)"><a href="#" id="lq-tb-all" style="color:var(--accent)">전체</a> · <a href="#" id="lq-tb-none" style="color:var(--accent)">해제</a> · <span id="lq-tb-sum">0개</span></span>',
      '    </div>',
      '    <div id="lq-tonbags" style="max-height:200px;overflow-y:auto;border:1px solid var(--border);border-radius:6px;padding:6px;background:var(--bg-hover);font-size:.85rem">LOT을 먼저 선택하세요.</div>',
      '  </div>',
      '  <div style="display:grid;grid-template-columns:110px 1fr;gap:10px;align-items:center;margin-bottom:10px">',
      '    <label style="font-weight:600">고객명</label>',
      '    <input type="text" id="lq-customer" placeholder="예: ACME Corp" style="padding:8px;background:var(--bg-hover);color:var(--text);border:1px solid var(--border);border-radius:6px">',
      '    <label style="font-weight:600">판매참조 <span style="color:var(--text-muted);font-weight:400;font-size:.8rem">(선택)</span></label>',
      '    <input type="text" id="lq-saleref" placeholder="SC RCVD 등 — 이중출고 방지 키" style="padding:8px;background:var(--bg-hover);color:var(--text);border:1px solid var(--border);border-radius:6px">',
      '    <label style="font-weight:600">출고일</label>',
      '    <input type="date" id="lq-date" value="' + today + '" style="padding:8px;background:var(--bg-hover);color:var(--text);border:1px solid var(--border);border-radius:6px">',
      '  </div>',
      '  <label id="lq-sample-row" style="display:flex;align-items:center;gap:8px;padding:7px;background:var(--bg-hover);border-radius:6px;font-size:.85rem;margin-bottom:6px">',
      '    <input type="checkbox" id="lq-sample" checked> 🧪 샘플도 함께 출고 <span style="color:var(--text-muted)">(전량 시 기본 포함 / 부분은 위 목록에서 선택)</span>',
      '  </label>',
      '  <label style="display:flex;align-items:center;gap:8px;padding:7px;background:var(--bg-hover);border-radius:6px;font-size:.85rem;margin-bottom:6px">',
      '    <input type="checkbox" id="lq-unlocated"> 📍 위치 미상 (비-랙 일반창고)',
      '  </label>',
      '  <label style="display:flex;align-items:center;gap:8px;padding:7px;background:var(--bg-hover);border-radius:6px;font-size:.85rem;margin-bottom:10px">',
      '    <input type="checkbox" id="lq-confirm"> ✅ 출고 확정까지 (SOLD) <span style="color:var(--text-muted)">(체크 시 바로 완전 출고, 미체크 시 PICKED까지)</span>',
      '  </label>',
      '  <div id="lq-result" style="margin-bottom:12px"></div>',
      '  <div style="display:flex;gap:8px;justify-content:flex-end">',
      '    <button id="lq-cancel" class="btn btn-ghost">닫기</button>',
      '    <button id="lq-submit" class="btn btn-primary" disabled>출고</button>',
      '  </div>',
      '</div>'
    ].join('\n');
    showDataModal('', html);

    var lotSel = document.getElementById('lq-lot-select');
    var lotSortBtn = document.getElementById('lq-lot-sort');
    var _lotItems = [];
    var _lotSortAsc = true;
    var cust = document.getElementById('lq-customer');
    var saleref = document.getElementById('lq-saleref');
    var dateEl = document.getElementById('lq-date');
    var sampleEl = document.getElementById('lq-sample');
    var sampleRow = document.getElementById('lq-sample-row');
    var unlocEl = document.getElementById('lq-unlocated');
    var confirmEl = document.getElementById('lq-confirm');
    var result = document.getElementById('lq-result');
    var submit = document.getElementById('lq-submit');
    var cancel = document.getElementById('lq-cancel');
    var modeRadios = document.getElementsByName('lq-mode');
    var tbWrap = document.getElementById('lq-tonbag-wrap');
    var tbBox = document.getElementById('lq-tonbags');
    var tbSum = document.getElementById('lq-tb-sum');
    var _tonbagsLoadedFor = '';

    function isFull() {
      for (var i = 0; i < modeRadios.length; i++)
        if (modeRadios[i].checked) return modeRadios[i].value === 'full';
      return true;
    }
    function checkedTonbags() {
      return Array.prototype.slice.call(tbBox.querySelectorAll('input.lq-tb:checked'));
    }
    function updateTbSum() {
      var n = checkedTonbags().length;
      var kg = checkedTonbags().reduce(function(s, c){ return s + (parseFloat(c.getAttribute('data-w')) || 0); }, 0);
      tbSum.textContent = n + '개 · ' + (kg / 1000).toFixed(3) + ' MT';
    }
    // 가용 LOT 목록 — 정렬 적용해 드롭다운 옵션 렌더 (선택값 유지)
    function renderLotOptions() {
      if (!_lotItems.length) { lotSel.innerHTML = '<option value="">가용 LOT 없음</option>'; return; }
      var cur = lotSel.value;
      var arr = _lotItems.slice().sort(function(a, b) {
        var r = String(a.lot_no).localeCompare(String(b.lot_no), undefined, { numeric: true });
        return _lotSortAsc ? r : -r;
      });
      var opts = ['<option value="">— 목록에서 선택 —</option>'];
      arr.forEach(function(it) {
        var label = it.lot_no + (it.product ? ' · ' + it.product : '') +
                    ' · 가용 ' + it.avail_normal + '개' + (it.avail_sample ? '(+샘플)' : '') +
                    (it.located ? ' · 📍' + (it.location || '위치지정') : ' · 🏬일반창고');
        opts.push('<option value="' + escapeHtml(it.lot_no) + '"' +
                  (it.lot_no === cur ? ' selected' : '') + '>' + escapeHtml(label) + '</option>');
      });
      lotSel.innerHTML = opts.join('');
    }
    apiGet('/api/outbound/lot-qty/lots').then(function(res) {
      _lotItems = (res && res.data && res.data.items) || [];
      renderLotOptions();
    }).catch(function() { lotSel.innerHTML = '<option value="">목록 로드 실패</option>'; });
    lotSortBtn.addEventListener('click', function() {
      _lotSortAsc = !_lotSortAsc;
      lotSortBtn.textContent = _lotSortAsc ? '↑ 오름차순' : '↓ 내림차순';
      renderLotOptions();
    });

    function loadTonbags() {
      var l = lotSel.value;
      if (!l) { tbBox.innerHTML = 'LOT을 먼저 선택하세요.'; _tonbagsLoadedFor=''; updateTbSum(); return; }
      if (_tonbagsLoadedFor === l) return;
      tbBox.innerHTML = '⏳ 톤백 불러오는 중...';
      apiGet('/api/outbound/lot-qty/tonbags?lot_no=' + encodeURIComponent(l)).then(function(res) {
        var items = (res && res.data && res.data.items) || [];
        _tonbagsLoadedFor = l;
        if (!items.length) { tbBox.innerHTML = '<span style="color:var(--text-muted)">가용 톤백 없음</span>'; updateTbSum(); return; }
        tbBox.innerHTML = items.map(function(t) {
          var tag = t.is_sample ? ' 🧪샘플' : '';
          var loc = t.location ? ' · ' + escapeHtml(t.location) : '';
          return '<label style="display:flex;align-items:center;gap:8px;padding:3px 4px;border-radius:4px;cursor:pointer">' +
                 '<input type="checkbox" class="lq-tb" value="' + t.id + '" data-w="' + (t.weight||0) + '" data-sample="' + t.is_sample + '">' +
                 '<span style="font-family:monospace">#' + t.sub_lt + '</span>' +
                 '<span style="color:var(--text-muted)">' + (t.weight||0).toFixed(0) + 'kg' + loc + tag + '</span></label>';
        }).join('');
        Array.prototype.forEach.call(tbBox.querySelectorAll('input.lq-tb'), function(c) {
          c.addEventListener('change', function(){ updateTbSum(); refresh(); });
        });
        updateTbSum();
        refresh();
      }).catch(function(){ tbBox.innerHTML = '<span style="color:var(--danger)">톤백 로드 실패</span>'; });
    }

    document.getElementById('lq-tb-all').addEventListener('click', function(e){ e.preventDefault();
      Array.prototype.forEach.call(tbBox.querySelectorAll('input.lq-tb'), function(c){ c.checked = true; }); updateTbSum(); refresh(); });
    document.getElementById('lq-tb-none').addEventListener('click', function(e){ e.preventDefault();
      Array.prototype.forEach.call(tbBox.querySelectorAll('input.lq-tb'), function(c){ c.checked = false; }); updateTbSum(); refresh(); });

    function refresh() {
      var full = isFull();
      tbWrap.style.display = full ? 'none' : 'block';
      sampleRow.style.display = full ? 'flex' : 'none';   // 부분은 목록에서 샘플 직접 선택
      var ok = !!lotSel.value && !!cust.value.trim() &&
               (full || checkedTonbags().length > 0);
      submit.disabled = !ok;
    }
    for (var i = 0; i < modeRadios.length; i++) {
      modeRadios[i].addEventListener('change', function() {
        if (!isFull()) loadTonbags();
        refresh();
      });
    }
    var locWarn = document.getElementById('lq-loc-warn');
    function selectedLotItem() {
      for (var i = 0; i < _lotItems.length; i++)
        if (_lotItems[i].lot_no === lotSel.value) return _lotItems[i];
      return null;
    }
    function updateLocWarn() {
      var it = selectedLotItem();
      if (!it || !lotSel.value) { locWarn.style.display = 'none'; return; }
      locWarn.style.display = 'block';
      if (it.located) {
        // Case A 가드: 랙 위치 지정 재고를 스캔없이 출고하려는 경우 경고
        locWarn.style.background = 'rgba(245,158,11,.13)';
        locWarn.style.border = '1px solid var(--warning)';
        locWarn.style.color = 'var(--text)';
        locWarn.innerHTML = '⚠️ 이 LOT은 <b>위치 지정(랙)</b> 재고입니다' +
          (it.location ? ' (📍 ' + escapeHtml(it.location) + ')' : '') +
          '.<br>스캔 없는 LOT 수량 출고는 <b>위치 검증이 생략</b>됩니다. 정확한 위치 추적이 필요하면 ' +
          '<b>피킹 리스트(스캔) 출고</b>를 권장합니다. 실제로 일반창고로 옮겨졌다면 아래 ' +
          '<b>📍 위치 미상</b>을 체크하고 진행하세요.';
      } else {
        locWarn.style.background = 'rgba(76,175,80,.10)';
        locWarn.style.border = '1px solid var(--success)';
        locWarn.style.color = 'var(--text-muted)';
        locWarn.innerHTML = '🏬 이 LOT은 <b>일반창고(위치 미상)</b> 재고 — LOT 수량 출고에 적합합니다.';
      }
    }
    lotSel.addEventListener('change', function(){
      _tonbagsLoadedFor = '';
      var it = selectedLotItem();
      // 위치 상태에 따라 '위치 미상' 자동 설정(사용자 수동 변경 가능)
      if (it) unlocEl.checked = !it.located;
      updateLocWarn();
      if (lotSel.value && !isFull()) loadTonbags();
      refresh();
    });
    cust.addEventListener('input', refresh);

    cancel.addEventListener('click', function() {
      document.getElementById('sqm-modal').style.display = 'none';
    });
    function doLotQtyOutbound(payload) {
      submit.disabled = true; cancel.disabled = true;
      result.innerHTML = '<div style="padding:8px;color:var(--text-muted)">⏳ 출고 처리 중...</div>';
      apiPost('/api/outbound/lot-qty', payload).then(function(res) {
        var d = (res && res.data) || {};
        if (res && res.ok) {
          result.innerHTML =
            '<div style="padding:12px;background:var(--bg-hover);border-radius:6px;border-left:4px solid var(--success)">' +
            '<div style="font-weight:600;margin-bottom:4px">✅ ' + escapeHtml(res.message || '출고 완료') + '</div>' +
            '<div style="color:var(--text-muted);font-size:.85rem">일반 ' + ((d.picked_count || 0) - (d.sample_picked || 0)) +
            '개 · 샘플 ' + (d.sample_picked || 0) + '개 · ' + (d.total_weight_mt || 0).toFixed(3) + ' MT · ' +
            (d.sold ? '<span style="color:var(--success)">SOLD 확정 ' + (d.confirmed || 0) + '건</span>' : 'PICKED (미확정)') +
            ' · ref=' + escapeHtml(d.ref || '') + '</div>' +
            ((d.confirm_errors && d.confirm_errors.length) ? '<div style="color:var(--warning);font-size:.8rem;margin-top:4px">⚠ 확정 일부 실패: ' + escapeHtml(d.confirm_errors.join('; ')) + '</div>' : '') +
            '</div>';
          showToast('success', res.message || '출고 완료');
          if (typeof dbgLog === 'function') dbgLog('🟢', 'LOT-QTY', res.message, '#66bb6a');
          if (_currentRoute === 'inventory' && typeof loadInventoryPage === 'function') loadInventoryPage();
          if (typeof loadKpi === 'function') loadKpi();
        } else {
          var errs = (d.errors || []).map(escapeHtml).join('<br>');
          result.innerHTML = '<div style="padding:12px;color:var(--danger);background:var(--bg-hover);border-radius:6px;border-left:4px solid var(--danger)">❌ ' +
            escapeHtml(res.message || '출고 실패') + (errs ? '<div style="font-size:.85rem;margin-top:4px">' + errs + '</div>' : '') + '</div>';
          showToast('warning', res.message || '출고 실패');
        }
        cancel.disabled = false;
        refresh();
      }).catch(function(e) {
        result.innerHTML = '<div style="padding:12px;color:var(--danger)">❌ ' + escapeHtml(e.message || String(e)) + '</div>';
        showToast('error', '실패: ' + (e.message || String(e)));
        cancel.disabled = false; refresh();
      });
    }

    submit.addEventListener('click', function() {
      var full = isFull();
      var ids = full ? null : checkedTonbags().map(function(c){ return parseInt(c.value, 10); });
      var payload = {
        lot_no: lotSel.value,
        count: full ? null : null,
        tonbag_ids: ids,
        customer: cust.value.trim(),
        sale_ref: saleref.value.trim(),
        outbound_date: dateEl.value || null,
        include_sample: full ? sampleEl.checked : false,
        unlocated: unlocEl.checked,
        confirm: confirmEl.checked,
        // 불일치 감사 기록: 위치 지정(랙) LOT 을 스캔없이 출고하면 사유 자동 부착
        reason: (function(){ var it = selectedLotItem(); return (it && it.located)
                   ? '위치지정 LOT 스캔없이 출고(위치검증 생략)' + (it.location ? ' @' + it.location : '') : ''; })()
      };
      var desc = full ? '전량' : (ids.length + '개 톤백 선택');
      var extra = (payload.include_sample ? ' + 샘플' : '') + (payload.unlocated ? ' / 위치미상' : '') + (payload.confirm ? ' / 확정(SOLD)' : '');
      // pywebview/WebView2 의 window.confirm 차단 이슈 회피 → 모달 내부 인라인 확인
      result.innerHTML =
        '<div style="padding:10px;background:var(--bg-hover);border-radius:6px;border-left:4px solid var(--warning)">' +
        '<div style="margin-bottom:8px">⚠️ <b>LOT ' + escapeHtml(payload.lot_no) + '</b> 을(를) <b>' + escapeHtml(desc + extra) +
        '</b> 로 <b>' + escapeHtml(payload.customer) + '</b> 에게 출고합니다. 진행할까요?</div>' +
        '<div style="display:flex;gap:8px;justify-content:flex-end">' +
        '<button type="button" id="lq-conf-no" class="btn btn-ghost">취소</button>' +
        '<button type="button" id="lq-conf-yes" class="btn btn-primary">확정 출고</button></div></div>';
      document.getElementById('lq-conf-no').addEventListener('click', function(){ result.innerHTML = ''; });
      document.getElementById('lq-conf-yes').addEventListener('click', function(){ doLotQtyOutbound(payload); });
    });
    refresh();
  }
  window.showLotQtyOutboundModal = showLotQtyOutboundModal;

  /* ===================================================
     8i. F028 출고 확정 — PICKED → SOLD
     =================================================== */
  function showOutboundConfirmModal() {
    var html = [
      '<div style="max-width:640px">',
      '  <h2 style="margin:0 0 12px 0">✅ 출고 확정 — PICKED → SOLD</h2>',
      '  <p style="color:var(--text-muted);margin:0 0 12px 0;font-size:.9rem">',
      '    PICKED 상태인 톤백을 실제 출고(SOLD)로 확정합니다.',
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
    submit.addEventListener('click', async function(){
      var payload = { lot_no: lot.value.trim(), force_all: force.checked };
      var msg = payload.lot_no ? ('LOT ' + payload.lot_no + ' 의 PICKED 톤백을 SOLD 로 확정합니다.') :
                                  '⚠️ LOT 미지정 — 전체 PICKED 일괄 확정입니다! 매우 위험.';
      if (!(await window.sqmConfirmAsync(msg + '\n계속하시겠습니까?'))) return;

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
          dbgLog('🟢','CONFIRM-SOLD OK', res.message, '#66bb6a');
          /* v8.7.0: CASE 3 — 부분 출고 잔여 톤백 자동 다이얼로그 */
          if (d.half_cells && d.half_cells.length && typeof window.showCase3Dialog === 'function') {
            setTimeout(function() { window.showCase3Dialog(d.half_cells); }, 200);
          }
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
     8j. 승인 대기 (Allocation Approval Queue)
     =================================================== */
  function showApprovalQueueModal() {
    showDataModal('✅ 승인 대기','<div style="padding:20px;text-align:center">⏳ 로딩 중...</div>');
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
      _sqmSyncModalHeaderFromContent();
    }).catch(function(e){
      document.getElementById('sqm-modal-content').innerHTML = '<h2>승인 대기</h2><div class="empty">조회 실패: ' + escapeHtml(e.message||String(e)) + '</div>';
      _sqmSyncModalHeaderFromContent();
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
        _sqmSyncModalHeaderFromContent();
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
      _sqmSyncModalHeaderFromContent();

      document.getElementById('restore-cancel').addEventListener('click', function(){ document.getElementById('sqm-modal').style.display='none'; });
      document.getElementById('restore-submit').addEventListener('click', async function(){
        var sel = document.querySelector('input[name="restore-sel"]:checked');
        if (!sel) { showToast('warning', '복원할 백업 파일을 선택하세요'); return; }
        var fname = sel.dataset.file;
        if (!(await window.sqmConfirmAsync('⚠️ ' + fname + ' 으로 DB를 복원합니다.\n현재 데이터가 모두 덮어씌워집니다.\n\n정말 계속할까요?'))) return;
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
      _sqmSyncModalHeaderFromContent();
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
      window.showReturnInboundUploadModal();
    });
    document.getElementById('ret-cancel').addEventListener('click', function(){ document.getElementById('sqm-modal').style.display='none'; });
    submitBtn.addEventListener('click', async function(){
      var lot = document.getElementById('ret-lot').value.trim();
      if (!lot) { showToast('warning', 'LOT 번호를 입력하세요'); return; }
      if (!(await window.sqmConfirmAsync('LOT ' + lot + ' 반품 처리를 진행합니다.'))) return;
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
          result.innerHTML = '<div style="padding:12px;color:var(--danger)">❌ ' + escapeHtml((res&&(res.message||res.error||res.detail))||'실패') + '</div>';
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
    submit.addEventListener('click', async function(){
      if (!(await window.sqmConfirmAsync('정말로 DB를 완전 초기화할까요?\n\n이 작업은 되돌릴 수 없습니다!'))) return;
      submit.disabled = true;
      document.getElementById('dbr-result').innerHTML = '<div style="padding:8px;color:var(--text-muted)">⏳ 초기화 중...</div>';
      apiPost('/api/action3/db-reset', { confirm: true })
        .then(function(res){
          if (res && res.ok) {
            document.getElementById('dbr-result').innerHTML = '<div style="padding:12px;background:var(--bg-hover);border-radius:6px;border-left:4px solid var(--success)"><div style="font-weight:600">✅ DB 초기화 완료 — 2초 후 새로고침...</div></div>';
            showToast('success', 'DB 초기화 완료');
            setTimeout(function(){ location.reload(); }, 2000);
          } else {
            document.getElementById('dbr-result').innerHTML = '<div style="padding:12px;color:var(--danger)">❌ ' + escapeHtml((res&&(res.message||res.error||res.detail))||'실패') + '</div>';
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
     8q. 설정 다이얼로그 모음 — 이메일/자동백업/템플릿
     =================================================== */



  /* ===================================================
     9. ALERTS + STATUSBAR
     =================================================== */
  var FALLBACK_ALERTS = [
    {severity:'warning',icon:'&#x1F3F7;&#xFE0F;',text:'Tonbag integrity issues 40 — run integrity check',link:'#integrity'},
    {severity:'error',  icon:'&#x1F4CD;',         text:'400 unallocated tonbags (5 LOTs) — location assignment needed',link:'#allocation'}
  ];


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
    'onReturnStatistics': {m:'JS', u:'return-statistics-modal',                  lbl:'반품 사유 통계'},
    'onRecentFiles':     {m:'GET',  u:'/api/q2/recent-files',                   lbl:'최근 파일'},
    'onExit':            {m:'JS',   u:'exit',                                    lbl:'종료'},

    /* ── 입고 메뉴 ── */
    /* v864.3 Phase 4-B: PDF 스캔 입고 네이티브 모달 (기존 scan 탭 대신) */
    'onOnPdfInbound':    {m:'JS', u:'pdf-inbound-upload', lbl:'PDF 스캔 입고'},
    /* v864.3 Phase 4-B: 수동 입고는 네이티브 모달로 처리 (tkinter filedialog 대체) */
    'onInboundManual':   {m:'JS', u:'inbound-upload', lbl:'수동 입고'},
    /* v864.2 menu_registry: _bulk_import_inventory_simple — 동일 모달 */
    'onBulkImportInventorySimple': {m:'JS', u:'inbound-upload', lbl:'엑셀 파일 수동 입고'},
    'onInboundList':     {m:'JS',   u:'inbound',                                  lbl:'입고 목록'},
    'onCarrierProfile':  {m:'JS',   u:'carrier-profile',                          lbl:'선사 프로파일 관리'},

    /* ── 출고 메뉴 ── */
    /* v864.3 Phase 4-B: 즉시 출고 네이티브 폼 */
    'onOnQuickOutbound': {m:'JS', u:'quick-outbound', lbl:'즉시 출고'},
    /* v864.3 Phase 4-B: 빠른 출고 (붙여넣기) — 여러 LOT 일괄 */
    'onQuickOutboundPaste': {m:'JS', u:'quick-outbound-paste', lbl:'빠른 출고 (붙여넣기)'},
    /* v8.7.4 MVP-2: LOT 수량 출고 (스캔 없음) */
    'onLotQtyOutbound': {m:'JS', u:'lot-qty-outbound', lbl:'LOT 수량 출고 (스캔없음)'},
    /* v864.3 Phase 4-B: Picking List PDF 업로드 */
    'onPickingListUpload':  {m:'JS', u:'picking-list-pdf', lbl:'Picking List 업로드 (PDF)'},
    'onPickingListExcelUpload':  {m:'JS', u:'picking-list-excel', lbl:'Picking List 업로드 (Excel)'},
    'onOutboundScheduled': {m:'GET', u:'/api/outbound/scheduled',                 lbl:'📅 출고 예약 목록'},  // [UI 연결]
    /* v864.3 Phase 4-B: 출고 확정 네이티브 폼 */
    'onOutboundConfirm': {m:'JS', u:'outbound-confirm', lbl:'출고 확정'},
    'onOutboundHistory': {m:'GET',  u:'/api/q/outbound-history',                 lbl:'📜 출고 이력 조회'},  // [UI 연결]
    'onOutboundStatus':  {m:'JS',   u:'outbound',                                 lbl:'출고 현황'},
    'onApprovalHistory': {m:'GET',  u:'/api/q/approval-history',                 lbl:'승인 이력 조회'},

    /* ── 재고 메뉴 ── */
    'onInventoryList':   {m:'JS',   u:'inventory',                               lbl:'재고 조회'},
    /* v864.3 Phase 4-B: 톤백 위치 매핑 네이티브 Excel 업로드 */
    'onInventoryMove':   {m:'JS', u:'tonbag-location-upload', lbl:'위치 이동'},
    /* v865: 대량 이동 승인 워크플로 */
    'onBatchMoveApproval': {m:'JS', u:'batch-move-approval', lbl:'대량 이동 승인'},
    /* v864.3 Phase 4-B: Allocation 입력(출고 예약) 네이티브 Excel 업로드 */
    'onInventoryAllocation': {m:'JS', u:'allocation-upload', lbl:'Allocation 입력'},
    'onIntegrityCheck':  {m:'GET',  u:'/api/action/integrity-check',             lbl:'정합성 검사'},
    'onInventoryReport': {m:'GET',  u:'/api/q/inventory-report',                 lbl:'재고 현황 보고서'},
    'onInventoryTrend':  {m:'GET',  u:'/api/q/inventory-trend',                  lbl:'📈 재고 추이 데이터'},  // [UI 연결]
    'onInventoryAdjust':  {m:'JS',   u:'inventory-adjust',                          lbl:'재고 수정'},
    'onRefreshExcelStatus': {m:'JS',  u:'refresh-excel-status',                     lbl:'Excel 상태 갱신'},

    /* ── 보고서 메뉴 ── */
    'onReportDaily':     {m:'GET',  u:'/api/q2/report-daily',                    lbl:'일일 보고서'},
    'onReportMonthly':   {m:'GET',  u:'/api/q2/report-monthly',                  lbl:'월간 보고서'},
    'onReportCustom':    {m:'GET',  u:'/api/q/inventory-report',                   lbl:'맞춤 보고서'},
    'onInvoiceGenerate': {m:'GET',  u:'/api/action3/export-invoice-excel',         lbl:'거래명세서 생성'},
    'onDetailOfOutbound': {m:'GET', u:'/api/q2/detail-outbound',                 lbl:'Detail of Outbound'},
    'onOutboundReport':  {m:'JS',   u:'outbound-report-modal',                   lbl:'Outbound Report'},
    'onExportWorkReport': {m:'JS',  u:'export-work-report-modal',                lbl:'수출 작업 리포트'},
    'onStorageConfirmationReport': {m:'JS', u:'storage-confirmation-modal',       lbl:'Storage Confirmation'},
    'onSoldInventoryReport': {m:'JS', u:'sold-inventory-report-modal',            lbl:'SOLD Inventory Report'},
    'onSalesOrderDN':    {m:'JS',   u:'sales-order-dn-modal',                    lbl:'Sales Order DN'},
    'onDnCrossCheck':    {m:'GET',  u:'/api/q3/dn-cross-check',                  lbl:'DN 교차검증'},
    'onLotDetailPdf':    {m:'GET',  u:'/api/action/lot-detail',                  lbl:'LOT 상세'},
    /* 재고 메뉴: FileResponse — GET+json 모달이 아니라 다운로드 (onExportLot 과 동일 계열) */
    'onLotListExcel':    {m:'JS',   u:'export-lot-excel-dl',                       lbl:'📂 LOT 리스트 바로 열기'},  // [UI 연결]
    'onTonbagListExcel': {m:'JS',   u:'export-tonbag-simple-dl',                  lbl:'톤백리스트 Excel'},
    'onReportExport':    {m:'GET',  u:'/api/action2/export-tonbag-excel',          lbl:'Excel 내보내기'},
    'onMovementHistory': {m:'GET',  u:'/api/q/movement-history',                  lbl:'입출고 내역'},
    'onAuditLog':        {m:'GET',  u:'/api/q/audit-log',                         lbl:'감사 로그'},

    /* ── 설정/도구 메뉴 ── */
    /* [Sprint 0] 'onSettings' removed — was wired to /api/menu/-on-settings (NotReadyError stub).
       Real settings dialog ships in Sprint 2 (SettingsDialogMixin port, ~5d). */
    'onProductMaster':   {m:'JS',   u:'product-master',                            lbl:'제품 마스터'},
    'onProductInventoryReport': {m:'GET', u:'/api/q/product-inventory',           lbl:'📦 품목별 재고 보고서'},  // [UI 연결]
    'onIntegrityRepair': {m:'POST', u:'/api/action/fix-integrity',                       lbl:'🔧 정합성 자동 복구'},  // [UI 연결]
    'onOptimizeDb':      {m:'POST', u:'/api/action3/optimize-db',                 lbl:'⚡ DB 최적화 (VACUUM)'},  // [UI 연결]
    'onCleanupLogs':     {m:'POST', u:'/api/action3/cleanup-logs',                lbl:'로그 정리'},
    'onDbInfo':          {m:'GET',  u:'/api/info/system-info',                    lbl:'DB 정보'},
    'onOnBackup':        {m:'POST', u:'/api/action/backup-create',                lbl:'백업 생성'},
    'onBackupList':      {m:'GET',  u:'/api/q/backup-list',                       lbl:'백업 목록'},
    'onRestore':         {m:'JS',   u:'restore',                                   lbl:'복원'},
    'onAiChat':          {m:'JS',   u:'ai-chat',                                   lbl:'AI 채팅'},
    'onAiTools':         {m:'JS',   u:'ai-tools-hub',                              lbl:'AI 도구'},
    'onAdvancedTools':   {m:'JS',   u:'advanced-tools-hub',                      lbl:'고급 도구'},
    'onSaveWindowSize':  {m:'JS',   u:'save-window-size',                          lbl:'창 크기 저장'},
    'onResetWindowSize': {m:'JS',   u:'reset-window-size',                         lbl:'창 크기 초기화'},

    /* ── 도움말 메뉴 ── */
    'onHelp':            {m:'GET',  u:'/api/info/usage',                          lbl:'사용자 매뉴얼'},
    'onShortcuts':       {m:'GET',  u:'/api/info/shortcuts',                      lbl:'단축키'},
    'onStatusGuide':     {m:'GET',  u:'/api/info/status-guide',                   lbl:'STATUS 안내'},
    'onBackupGuide':     {m:'GET',  u:'/api/info/backup-guide',                   lbl:'백업/복구 가이드'},
    'onAbout':           {m:'GET',  u:'/api/info/version',                        lbl:'버전 정보'},

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
    'tb-settings':       {m:'JS',   u:'font-size-settings',                       lbl:'표시·엑셀 설정'},
    /* [Sprint 0] 'tb-settings' removed — same reason as onSettings (real dialog in Sprint 2). */

    /* ── v864.2 신규 액션 (메뉴 구조 동기화) ── */
    'onBarcodeScanUpload': {m:'JS', u:'barcode-scan-upload',                       lbl:'바코드 스캔 업로드'},
    'onApprovalQueue':   {m:'JS',   u:'approval-queue',                            lbl:'승인 대기'},
    'onApplyApproved':   {m:'POST', u:'/api/allocation/apply-approved',            lbl:'예약 반영 (승인분)'},
    'onPickingTemplateManage': {m:'JS', u:'picking-template',                      lbl:'피킹 템플릿 관리'},
    'onImportAllocationTemplate': {m:'JS', u:'import-alloc-template',                lbl:'📥 양식 가져오기'},  // [fix F-4] tonbag에만 있던 액션 inline에 추가
    'onMoveApprovalQueue': {m:'JS', u:'move-approval-queue',                      lbl:'대량 이동 승인'},
    'onInboundTemplateManage': {m:'JS', u:'inbound-template',                     lbl:'입고 파싱 템플릿'},
    'onFontSizeSettings':    {m:'JS', u:'font-size-settings',                       lbl:'🔤 화면 폰트 크기'},
    'onEmailConfig':     {m:'JS',   u:'email-config',                              lbl:'이메일 설정'},
    'onIntegrityReport': {m:'GET',  u:'/api/action/integrity-report',             lbl:'📋 정합성 리포트'},  // [UI 연결]
    'onFixLotIntegrity': {m:'GET',  u:'/api/action/integrity-check',              lbl:'LOT 정합성 검사'},
    'onExportCustoms':   {m:'JS',   u:'export-dl-e1',                             lbl:'통관요청 양식'},
    'onExportRubyli':    {m:'JS',   u:'export-dl-e3',                             lbl:'루비리 양식'},
    'onExportTonbag':    {m:'JS',   u:'export-dl-e4',                             lbl:'톤백 현황'},
    'onExportIntegrated': {m:'JS',  u:'export-dl-e6',                             lbl:'통합 현황'},
    'onAutoBackupSettings': {m:'JS', u:'auto-backup-settings',                    lbl:'자동 백업 설정'},
    'onReportTemplates': {m:'JS',   u:'report-templates-hub',                      lbl:'보고서 양식 관리'},
    'onReportHistory':   {m:'JS',   u:'report-history-audit',                      lbl:'보고서 이력 조회'},
    'onLotAllocationAudit': {m:'JS', u:'lot-allocation-audit',                    lbl:'LOT Allocation 톤백 현황'},
    'onDocConvert':      {m:'JS',   u:'doc-convert',                               lbl:'문서 변환 (OCR/PDF)'},
    'onTestDbReset':     {m:'JS',   u:'test-db-reset',                             lbl:'테스트 DB 초기화'},
    'onSystemInfo':      {m:'GET',  u:'/api/q3/settings-info',                    lbl:'시스템 정보'},
    'onProductSummary':  {m:'JS',   u:'product-summary',                           lbl:'품목별 재고 요약'},
    'onProductLotLookup': {m:'JS',  u:'product-lot-lookup',                        lbl:'품목별 LOT 조회'},
    'onProductMovement': {m:'JS',   u:'product-movement',                          lbl:'품목별 입출고 현황'},

    /* ── 선사 BL / Gemini: 선사는 carriers 화면으로 통합 (v864 도구 메뉴와 기능 동등) ── */
    'onBlCarrierRegister': {m:'JS', u:'carrier-profile',                           lbl:'🚢 선사 BL 등록 도구'},
    'onBlCarrierAnalyze':  {m:'JS', u:'carrier-profile',                           lbl:'🔬 선사 패턴 분석'},
    'onGeminiToggle':      {m:'JS', u:'gemini-toggle',                             lbl:'🔀 Gemini AI 사용'},
    'onGeminiApiSettings': {m:'JS', u:'gemini-api-settings',                       lbl:'🔐 Gemini API 설정'},
    'onGeminiApiTest':     {m:'JS', u:'gemini-api-test',                           lbl:'🧪 Gemini API 테스트'},

    /* ── 재고 메뉴: LOT Excel은 FileResponse → 새 창 다운로드 / 추이는 JSON 모달 ── */
    'onExportLot':         {m:'JS', u:'export-lot-excel-dl',                       lbl:'📊 LOT 리스트 Excel'},
    'onStockTrendChart':   {m:'GET', u:'/api/q/inventory-trend',                   lbl:'📊 재고 추이 차트'},
    /* v8.7.0: 창고 셀 점유 대시보드 */
    'onWarehouseDashboard':{m:'JS', u:'warehouse-dashboard',                       lbl:'📊 창고 현황 (대시보드)'},
    /* v8.7.0: 위치재고조회 엑셀 import */
    'onLocationMapImport':{m:'JS', u:'location-map-import', lbl:'📥 위치재고 엑셀 Import'},

    /* 전역 검색: v866는 Inventory 탭 검색으로 대체 (기능 단위 동등 목표) */
    'onGlobalSearch':      {m:'JS', u:'inventory',                                lbl:'🔍 통합 검색'},  // [UI 연결] Ctrl+F

    /* View 메뉴 탭 이동 */
    'onGoInventoryTab':  {m:'JS',   u:'inventory',                                lbl:'Inventory 탭'},
    'onGoPickedTab':     {m:'JS',   u:'picked',                                   lbl:'Picked 탭'},
    'onGoOutboundTab':   {m:'JS',   u:'outbound',                                 lbl:'Outbound 탭'},
    'onGoReturnTab':     {m:'JS',   u:'return',                                   lbl:'Return 탭'},
    'onGoMoveTab':       {m:'JS',   u:'move',                                     lbl:'Move 탭'},
    'onGoDashboardTab':  {m:'JS',   u:'dashboard',                                lbl:'Dashboard 탭'},
    'onGoLogTab':        {m:'JS',   u:'log',                                      lbl:'Log 탭'},

    /* ── 업로드 / 보고서 ── */
    'onDoUpload':          {m:'JS',  u:'do-upload',                               lbl:'D/O PDF 업로드'},
    'onSalesOrderUpload':  {m:'JS',  u:'sales-order-upload',                      lbl:'Sales Order Excel 업로드'},
    'onSwapReport':        {m:'GET', u:'/api/action2/swap-report',                 lbl:'Swap 보고서'},
    'onStockAlerts':       {m:'GET', u:'/api/dashboard/alerts',                    lbl:'재고 알림'},

    /* ── 기타 ── */
    'refresh-all':       {m:'JS',   u:'refresh',                                  lbl:'새로고침'},
    'onToggleTheme':     {m:'JS',   u:'theme',                                    lbl:'테마 전환'},
  };

  function _downloadTonbagSimple(conf) {
    if (typeof window.showTonbagListModal === 'function') {
      window.showTonbagListModal();
    } else {
      sqmDownloadFileUrl(_getApiBase() + '/api/action2/export-tonbag-excel', conf.lbl);
    }
  }

  function _downloadLotExcel(conf) {
    if (typeof window.showLotListModal === 'function') {
      window.showLotListModal();
    } else {
      sqmDownloadFileUrl(_getApiBase() + '/api/action/export-lot-excel', conf.lbl);
    }
  }

  function _openWarehouseDashboard() {
    if (typeof window.showWarehouseDashboard === 'function') {
      window.showWarehouseDashboard();
    } else {
      showToast('error', '대시보드 모듈 미로드');
    }
  }

  var JS_ACTION_HANDLERS = {
    /* shell */
    theme: function(){ toggleTheme(); },
    refresh: function(){ renderPage(_currentRoute || 'dashboard'); },
    exit: function(){
      if (window.pywebview && window.pywebview.api) window.pywebview.api.exit_app();
      else window.close();
    },

    /* upload */
    'inbound-upload': function(){ window.showInboundManualUploadModal(); },
    'return-upload': function(){ window.showReturnInboundUploadModal(); },
    'allocation-upload': function(){ window.showAllocationUploadModal(); },
    'tonbag-location-upload': function(){ window.showTonbagLocationUploadModal(); },
    'picking-list-pdf': function(){ window.showPickingListPdfModal(); },
    'picking-list-excel': function(){ window.showPickingListExcelModal(); },
    'barcode-scan-upload': function(){ window.showBarcodeScanUploadModal(); },
    'do-upload': function(){ window.showDoUploadModal(); },
    'sales-order-upload': function(){ window.showSalesOrderUploadModal(); },

    /* inbound / outbound workflow */
    'quick-outbound': function(){ showOneStopOutboundModal(); },
    'do-update': function(){ showDoUpdateModal(); },
    'batch-move-approval': function(){ showBatchMoveApprovalModal(); },
    'apply-approved-allocation': function(){ showApplyApprovedAllocationModal(); },
    'pdf-inbound-upload': function(){ showOneStopInboundModal(); },
    'quick-outbound-paste': function(){ showQuickOutboundPasteModal(); },
    'lot-qty-outbound': function(){ showLotQtyOutboundModal(); },
    'outbound-confirm': function(){ showOutboundConfirmModal(); },
    'approval-queue': function(){ showApprovalQueueModal(); },
    'return-dialog': function(){ showReturnDialog(); },
    'inventory-adjust': function(){ showInventoryAdjustDialog(); },
    'refresh-excel-status': function(){ onRefreshExcelStatus(); },

    /* settings */
    'email-config': function(){ window.showEmailConfigModal(); },
    'auto-backup-settings': function(){ window.showAutoBackupSettingsModal(); },
    'gemini-api-settings': function(){ window.showGeminiApiSettingsModal(); },
    'gemini-api-test': function(){ window.showGeminiApiTestModal(); },
    'gemini-toggle': function(){ window._geminiToggleAction(); },
    'inbound-template': function(){ window.showInboundTemplateModal(); },
    'font-size-settings': function(){ window.showFontSizeModal(); },
    'picking-template': function(){ window.showPickingTemplateModal(); },

    /* tools / admin */
    restore: function(){ showRestoreModal(); },
    'save-window-size': function(){ saveWindowSize(); },
    'reset-window-size': function(){ resetWindowSize(); },
    'lot-allocation-audit': function(){ showLotAllocationAuditModal(); },
    'test-db-reset': function(){ showTestDbResetModal(); },
    'move-approval-queue': function(){ window.showMoveApprovalQueueModal(); },
    'doc-convert': function(){ window.showDocConvertModal(); },
    'return-statistics-modal': function(){ window.showReturnStatisticsModal(); },
    'advanced-tools-hub': function(){ window.showAdvancedToolsHubModal(); },
    'warehouse-dashboard': function(){ _openWarehouseDashboard(); },
    'location-map-import': function(){ if (typeof window.showLocationMapImportModal === 'function') { window.showLocationMapImportModal(); } else { showToast('error', '위치재고 import 모듈 미로드'); } },

    /* exports */
    'export-dl-e1': function(conf){ sqmDownloadFileUrl(_getApiBase() + '/api/action/export-engine-excel?option=1', conf.lbl); },
    'export-dl-e3': function(conf){ sqmDownloadFileUrl(_getApiBase() + '/api/action/export-engine-excel?option=3', conf.lbl); },
    'export-dl-e4': async function(conf){
      var incSample = await window.sqmConfirmAsync('톤백리스트(Sub LOT): 샘플 톤백을 포함할까요?\n\n[확인] 포함 · [취소] 제외');
      sqmDownloadFileUrl(_getApiBase() + '/api/action/export-engine-excel?option=4&include_sample=' + (incSample ? 'true' : 'false'), conf.lbl);
    },
    'export-dl-e6': function(conf){ sqmDownloadFileUrl(_getApiBase() + '/api/action/export-engine-excel?option=6', conf.lbl); },
    'export-tonbag-simple-dl': function(conf){ _downloadTonbagSimple(conf); },
    'export-lot-excel-dl': function(conf){ _downloadLotExcel(conf); },

    /* product / auxiliary */
    'product-summary': function(){ window.showProductSummaryModal(); },
    'product-lot-lookup': function(){ window.showProductLotLookupModal(); },
    'product-movement': function(){ window.showProductMovementModal(); },
    'product-master': function(){ window.showProductMasterModal(); },
    'carrier-profile': function(){ showCarrierProfileModal(); },
    'ai-chat':      function(){ window.showAiChatModal(); },
    'ai-tools-hub': function(){ window.showAiToolsHubModal(); },
    'report-templates-hub': function(){ window.showReportTemplatesHubModal(); },
    'report-history-audit': function(){ window.showReportHistoryAuditModal(); },
    'outbound-report-modal': function(){ window.showTemplateReportModal('outbound_report'); },
    'sales-order-dn-modal': function(){ window.showTemplateReportModal('sales_order_dn'); },
    'export-work-report-modal': function(){ window.showTemplateReportModal('export_work_report'); },
    'storage-confirmation-modal': function(){ window.showTemplateReportModal('storage_confirmation'); },
    'sold-inventory-report-modal': function(){ window.showTemplateReportModal('sold_inventory_report'); },

    /* placeholder */
    wip: function(conf){
      dbgLog('🟡','WIP: '+conf.lbl,'준비 중 (아직 미구현)','#ffa726');
      showToast('info', conf.lbl + ': 준비 중');
    }
  };

  async function dispatchAction(action) {
    var conf = ENDPOINTS[action];
    if (!conf) {
      dbgLog('⚠️','[unregistered] '+action,'ENDPOINTS에 없는 액션','#ffa726');
      showToast('info', '[unregistered] action=' + action);
      return;
    }
    if (conf.m === 'JS') {
      var handler = JS_ACTION_HANDLERS[conf.u];
      if (handler) {
        handler(conf, action);
        return;
      }
      dbgLog('🔀','Route → '+conf.u, conf.lbl,'#ab47bc');
      renderPage(conf.u);
      return;
    }
    if (conf.m === 'GET') {
      window.renderInfoModal(conf.lbl, conf.u);
      return;
    }
    if (action === 'tb-backup' || action === 'onOnBackup') {
      var ok = await window.sqmConfirmAsync('💾 DB 백업을 생성합니다.\n\nOK를 누르면 백업 파일이 생성됩니다.');
      if (!ok) return;
    }
    apiCall(conf.m, conf.u, {})
      .then(function (res) {
        // v864.3 Debug: 응답 body 의 ok:false 체크 (가짜 성공 토스트 차단)
        if (res && res.ok === false) {
          var detailCode = res.detail && res.detail.code;
          if (detailCode === 'NOT_READY') {
            showToast('info', conf.lbl + ': 아직 준비되지 않았습니다');
          } else {
            showToast('error', conf.lbl + ': ' + (res.message || res.detail || '실패'));
          }
          return;
        }
        showToast('success', conf.lbl + ': 완료');
        if (action === 'tb-backup' || action === 'onOnBackup') loadAlerts();
      })
      .catch(function(e){
        showToast('error', conf.lbl + ': ' + (e.message || e));
      });
  }

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
        if (action==='show-weight-panel') { window.showWeightPanel(); return; }
        closeAllMenus();
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
        if (ev.target.closest('.submenu-parent')) {
          ev.preventDefault();
          ev.stopPropagation();
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

    // click-lock nested submenu. Hover still works through CSS, but click keeps it open
    // while the pointer moves across the submenu gap.
    document.querySelectorAll('.submenu-parent > .submenu-parent-btn').forEach(function(btn){
      if (btn.dataset._sqmSubmenuBound) return;
      btn.dataset._sqmSubmenuBound = '1';
      btn.addEventListener('click', function(ev){
        ev.preventDefault();
        ev.stopPropagation();
        var parent = btn.closest('.submenu-parent');
        var dropdown = parent ? parent.querySelector('.submenu-dropdown') : null;
        if (!parent || !dropdown) return;
        var open = parent.classList.contains('open');
        closeSiblingSubmenus(parent);
        if (open) {
          parent.classList.remove('open');
          dropdown.style.display = '';
        } else {
          parent.classList.add('open');
          dropdown.style.display = 'block';
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
        if (document.body) document.body.setAttribute('data-theme','dark');
        try{getStore().setItem('sqm_theme','dark');}catch{}
      });
    });
    document.querySelectorAll('[data-action="theme-light"]').forEach(function(el){
      el.addEventListener('click',function(){
        document.documentElement.setAttribute('data-theme','light');
        if (document.body) document.body.setAttribute('data-theme','light');
        try{getStore().setItem('sqm_theme','light');}catch{}
      });
    });

    // F5 shortcut — F8: debug panel toggle (handled in _dbgBuild)
    document.addEventListener('keydown', async function(ev){
      if (ev.key === 'Escape') {
        closeAllMenus();
        return;
      }
      if (ev.key === '?' && !ev.ctrlKey && !ev.metaKey && !ev.altKey) {
        var active = document.activeElement;
        if (!active || (active.tagName !== 'INPUT' && active.tagName !== 'TEXTAREA')) {
          ev.preventDefault();
          dispatchAction('onShortcuts');
        }
        return;
      }
      if (ev.key==='F5'&&!ev.ctrlKey&&!ev.metaKey){
        ev.preventDefault();
        if (await window.sqmConfirmAsync('화면을 새로고침 하시겠습니까?')) renderPage(_currentRoute||'dashboard');
      }
    });

    console.info('[SQM v864.3] bindAll complete');
  }

  // ── 재고 수정 (자연어 AI 입력) ──

  function onRefreshExcelStatus() {
    showToast('Excel 상태 갱신 중...', 'info');
    fetch('/api/inventory/refresh-excel-status', {method:'POST'})
      .then(function(r){ return r.json(); })
      .then(function(d){
        if (d.success) {
          showToast('✅ ' + d.excel_path + ' 갱신완료 — 변경 ' + d.updated
            + '행 (RESERVED:' + d.reserved + ' SOLD:' + d.sold + ' AVAILABLE:' + d.available + ')', 'success');
        } else {
          showToast('❌ Excel 갱신 실패: ' + (d.detail || '오류'), 'error');
        }
      })
      .catch(function(e){ showToast('❌ 네트워크 오류: ' + e.message, 'error'); });
  }

  async function showInventoryAdjustDialog() {
    const modal = document.getElementById('inventoryAdjustModal');
    if (!modal) { showToast('재고 수정 모달을 찾을 수 없습니다', 'danger'); return; }
    modal.style.display = 'flex';
    document.getElementById('adjustParseResult').innerHTML = '';
    document.getElementById('adjustExecuteBtn').style.display = 'none';
    document.getElementById('adjustTextInput').value = '';
  }

  async function parseAdjustRequest() {
    const text = document.getElementById('adjustTextInput').value.trim();
    if (!text) { showToast('조정 내용을 입력하세요', 'warning'); return; }
    document.getElementById('adjustParseResult').innerHTML = '<p>⏳ AI 파싱 중...</p>';
    try {
      const res = await fetch('/api/inventory/adjust/parse', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({text})
      });
      const data = await res.json();
      if (data.error) { showToast('파싱 오류: ' + data.error, 'danger'); return; }
      let html = '<table style="width:100%;border-collapse:collapse;font-size:13px">';
      html += '<tr style="background:#2c3e50;color:#fff"><th>LOT</th><th>현재</th><th>조정후</th><th>변화</th><th>사유</th><th>확신도</th></tr>';
      (data.items||[]).forEach(item => {
        const delta = item.delta >= 0 ? '+'+item.delta : item.delta;
        const color = item.delta < 0 ? '#e74c3c' : item.delta > 0 ? '#27ae60' : '#888';
        html += '<tr style="border-bottom:1px solid #444">'
          + '<td style="padding:4px">'+item.lot_no+'</td>'
          + '<td style="padding:4px;text-align:center">'+(item.new_count - item.delta)+'포대</td>'
          + '<td style="padding:4px;text-align:center;font-weight:bold">'+item.new_count+'포대</td>'
          + '<td style="padding:4px;text-align:center;color:'+color+';font-weight:bold">'+delta+'</td>'
          + '<td style="padding:4px">'+item.reason_code+' — '+item.reason_text+'</td>'
          + '<td style="padding:4px;text-align:center">'+Math.round(item.confidence*100)+'%</td>'
          + '</tr>';
      });
      html += '</table>';
      if (data.ambiguous && data.ambiguous.length > 0) {
        html += '<p style="color:#f39c12;margin-top:8px">⚠️ 불확실 항목: ' + data.ambiguous.join(', ') + '</p>';
      }
      document.getElementById('adjustParseResult').innerHTML = html;
      document.getElementById('adjustExecuteBtn').style.display = 'inline-block';
      document.getElementById('adjustExecuteBtn').dataset.items = JSON.stringify(data.items);
    } catch(e) {
      showToast('파싱 실패: ' + e.message, 'danger');
    }
  }

  async function executeAdjustment() {
    const btn = document.getElementById('adjustExecuteBtn');
    const items = JSON.parse(btn.dataset.items || '[]');
    if (!items.length) { showToast('조정 항목이 없습니다', 'warning'); return; }
    if (!(await window.sqmConfirmAsync(items.length+'건의 재고를 조정합니다. DB와 엑셀이 모두 수정됩니다. 계속하시겠습니까?'))) return;
    try {
      const res = await fetch('/api/inventory/adjust/execute', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify({items, operator:'Nam Ki-dong'})
      });
      const data = await res.json();
      const msg = '✅ 완료: '+data.success.length+'건 | ⏭ 스킵: '+data.skipped.length+'건 | ❌ 실패: '+data.failed.length+'건';
      showToast(msg, data.failed.length ? 'warning' : 'success');
      document.getElementById('inventoryAdjustModal').style.display = 'none';
    } catch(e) {
      showToast('실행 실패: ' + e.message, 'danger');
    }
  }

  /* v8.7.0 fix (2026-05-14): 재고 수정 모달 함수를 window 에 노출.
     - HTML 모달 내 onclick="parseAdjustRequest()" / onclick="executeAdjustment()" 가
       전역 함수 참조이므로 IIFE 내부 정의로는 ReferenceError.
     - 라우터 분기에서도 window.showInventoryAdjustDialog() 호출 가능. */
  window.showInventoryAdjustDialog = showInventoryAdjustDialog;
  window.parseAdjustRequest        = parseAdjustRequest;
  window.executeAdjustment         = executeAdjustment;

  function boot() {
    _dbgBuild();
    applyTheme();
    if (window.applyStoredFontScale) window.applyStoredFontScale();
    bindAll();
    loadAlerts();
    loadStatusbar();
    startKpiPolling();
    dbgLog('🚀','SQM v8.7.1 부팅 완료', 'F8 = 디버그 패널 토글','#4caf50');

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
    window.SQM.version = '8.7.1';
    window.SQM.renderPage = renderPage;
    window.SQM.dispatchAction = dispatchAction;
    /* [FIX 20260604] dispatch split-brain 제거:
       기존엔 window.dispatchAction 을 sqm-tonbag.js 만 등록 → sqm-core.js 의 키보드 단축키(맨 dispatchAction 호출)는
       tonbag dispatch 로, 메뉴 클릭은 inline dispatch 로 갈려서(원스톱 모달/oo* 불일치 가능) 위험.
       inline 이 마지막 로드이므로 여기서 window.dispatchAction 을 inline 버전으로 통일한다.
       (inline ENDPOINTS 가 키보드 액션 onOnBackup/onExport/onIntegrityCheck/onOnQuickOutbound 전부 커버 + 미등록 액션 안전 폴백 확인 완료) */
    window.dispatchAction = dispatchAction;
    if (typeof window.SQM.currentRoute !== 'function') window.SQM.currentRoute = function(){ return _currentRoute; };
    console.info('[SQM v8.7.1] boot complete. initial route:', initial);
  }

  /* sqm-onestop-inbound.js 의존성 전역 노출 */
  window.API = API;
  // [fix F-5] window._currentRoute getter 단순화:
  //   sqm-core.js의 window.getCurrentRoute()가 단일 정본이므로 이를 위임
  //   (기존: window.SQM.currentRoute() 호출 — sqm-inline 로컬 변수만 반영하는 문제)
  Object.defineProperty(window, '_currentRoute', {
    get: function() {
      return typeof window.getCurrentRoute === 'function'
        ? window.getCurrentRoute()
        : (window.SQM && window.SQM.currentRoute ? window.SQM.currentRoute() : '');
    },
    configurable: true
  });

  if (document.readyState==='loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }

  // ═══════════════════════════════════════════════════════════════════
  // 🤖 AI 선사 템플릿 자동 생성 모달
  // ═══════════════════════════════════════════════════════════════════
  var _tplBlFile = null;
  var _tplDoFile = null;
  var _tplPreviewData = null;

  function onInboundTemplateManage() {
    /* 입고 파싱 템플릿 관리 — AI 자동 생성 모달 열기 */
    _tplBlFile = null; _tplDoFile = null; _tplPreviewData = null;
    document.getElementById('tpl-bl-label').textContent = '📄 BL (선하증권) PDF — 클릭하여 업로드 ';
    document.getElementById('tpl-bl-label').innerHTML += '<span style="color:#e74c3c">*필수</span>';
    document.getElementById('tpl-do-label').textContent = '📄 D/O (화물인도지시서) PDF — 클릭하여 업로드 ';
    document.getElementById('tpl-do-label').innerHTML += '<span style="color:#95a5a6">(선택)</span>';
    document.getElementById('tpl-bl-input').value = '';
    document.getElementById('tpl-do-input').value = '';
    document.getElementById('tpl-analyze-btn').disabled = true;
    document.getElementById('tpl-analyze-btn').style.background = '#555';
    document.getElementById('tpl-analyze-btn').style.color = '#999';
    document.getElementById('tpl-preview').style.display = 'none';
    document.getElementById('tpl-loading').style.display = 'none';
    var m = document.getElementById('modal-template-ai');
    m.style.display = 'flex';
  }

  function closeTplAiModal() {
    document.getElementById('modal-template-ai').style.display = 'none';
  }

  function onTplFileSelect(input, type) {
    var file = input.files[0];
    if (!file) return;
    if (type === 'bl') {
      _tplBlFile = file;
      document.getElementById('tpl-bl-label').innerHTML =
        '✅ BL: <strong>' + file.name + '</strong> (' + (file.size/1024).toFixed(0) + ' KB)';
      document.getElementById('tpl-bl-zone').style.borderColor = '#2ecc71';
    } else {
      _tplDoFile = file;
      document.getElementById('tpl-do-label').innerHTML =
        '✅ D/O: <strong>' + file.name + '</strong> (' + (file.size/1024).toFixed(0) + ' KB)';
      document.getElementById('tpl-do-zone').style.borderColor = '#2ecc71';
    }
    // BL 있으면 분석 버튼 활성화
    if (_tplBlFile) {
      var btn = document.getElementById('tpl-analyze-btn');
      btn.disabled = false;
      btn.style.background = '#8e44ad';
      btn.style.color = '#fff';
    }
  }

  function onTplAnalyze() {
    if (!_tplBlFile) { showToast('BL PDF를 먼저 업로드하세요', 'warning'); return; }

    var btn = document.getElementById('tpl-analyze-btn');
    btn.disabled = true; btn.textContent = '⏳ AI 분석 중...';
    document.getElementById('tpl-loading').style.display = 'block';
    document.getElementById('tpl-preview').style.display = 'none';

    var fd = new FormData();
    fd.append('bl_file', _tplBlFile);
    if (_tplDoFile) fd.append('do_file', _tplDoFile);

    fetch('/api/inbound/templates/generate-from-docs', { method:'POST', body:fd })
      .then(function(r){ return r.json(); })
      .then(function(d){
        document.getElementById('tpl-loading').style.display = 'none';
        btn.disabled = false; btn.textContent = '🤖 AI 분석 시작';
        btn.style.background = '#8e44ad'; btn.style.color = '#fff';

        if (!d.ok) {
          showToast('❌ AI 분석 실패: ' + (d.detail || d.message || '오류'), 'error');
          return;
        }
        var p = d.preview;
        _tplPreviewData = p;
        document.getElementById('prev-carrier-id').textContent   = p.carrier_id   || '-';
        document.getElementById('prev-carrier-name').textContent = p.carrier_name || '-';
        document.getElementById('prev-bl-format').textContent    = p.bl_format    || '-';
        document.getElementById('prev-bl-no').textContent        = p.bl_no_example || '-';
        document.getElementById('tpl-ai-msg').textContent        = d.message || '';
        document.getElementById('tpl-preview').style.display = 'block';
        showToast('✅ AI 분석 완료! 결과를 확인하고 저장하세요', 'success');
      })
      .catch(function(e){
        document.getElementById('tpl-loading').style.display = 'none';
        btn.disabled = false; btn.textContent = '🤖 AI 분석 시작';
        showToast('❌ 네트워크 오류: ' + e.message, 'error');
      });
  }

  function _buildTplPayload(bagKg) {
    if (!_tplPreviewData) return null;
    var p = _tplPreviewData;
    var cid = (p.carrier_id || '').toUpperCase();
    var suffix = bagKg === 500 ? '500 kg' : '1,000 kg';
    return {
      template_name:        cid + ' — 리튜카보네이트 ' + suffix,
      carrier_id:           cid,
      bag_weight_kg:        bagKg,
      product_hint:         '리튜카보네이트 ' + bagKg + 'kg/포대',
      bl_format:            p.bl_format || '',
      gemini_hint_bl:       p.gemini_hint_bl || '',
      gemini_hint_do:       p.gemini_hint_do || '',
      gemini_hint_packing:  p.gemini_hint_packing || '',
      note: '', lot_sqm: '', mxbg_pallet: 0, sap_no: ''
    };
  }

  function _saveTplPayload(payload) {
    return fetch('/api/inbound/templates', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(payload)
    }).then(function(r){ return r.json(); });
  }

  function onTplSaveBoth() {
    if (!_tplPreviewData) { showToast('먼저 AI 분석을 실행하세요', 'warning'); return; }
    var p500  = _buildTplPayload(500);
    var p1000 = _buildTplPayload(1000);
    Promise.all([_saveTplPayload(p500), _saveTplPayload(p1000)])
      .then(function(results){
        var ok = results.filter(function(r){ return r.ok; }).length;
        if (ok === 2) {
          showToast('✅ ' + (p500.carrier_id) + ' 500kg + 1,000kg 템플릿 저장 완료!', 'success');
          closeTplAiModal();
        } else {
          showToast('⚠️ 일부 저장 실패 (' + ok + '/2). 중복일 수 있습니다.', 'warning');
        }
      })
      .catch(function(e){ showToast('❌ 저장 오류: ' + e.message, 'error'); });
  }

  function onTplSaveOne() {
    if (!_tplPreviewData) { showToast('먼저 AI 분석을 실행하세요', 'warning'); return; }
    var bagKg = parseInt(document.getElementById('prev-bag-weight').value, 10);
    var payload = _buildTplPayload(bagKg);
    _saveTplPayload(payload)
      .then(function(d){
        if (d.ok) {
          showToast('✅ ' + payload.carrier_id + ' ' + bagKg + 'kg 템플릿 저장 완료!', 'success');
          closeTplAiModal();
        } else {
          showToast('❌ 저장 실패: ' + (d.detail || d.message || '오류'), 'error');
        }
      })
      .catch(function(e){ showToast('❌ 저장 오류: ' + e.message, 'error'); });
  }
  // ═══════════════════════════════════════════════════════════════════


})();
