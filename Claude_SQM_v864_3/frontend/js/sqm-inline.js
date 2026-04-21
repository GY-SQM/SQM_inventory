/* SQM v864.3 — INLINE Handlers (ESM 의존 없는 fallback 보증판)
   type="module" 아닌 일반 script 로 로드 — IIFE, XHR, no import.
   2026-04-21 Ruby 수정: 클릭 기반 드롭다운 + 디버그 로그 + 엔드포인트 교정. */
(function(){
  'use strict';
  var VERSION = 'v864.3-inline-2026-04-21b';
  console.info('[SQM inline] 핸들러 바인딩 시작', VERSION);

  var API_BASE = (window && window.SQM_API_BASE) || 'http://127.0.0.1:8765';

  // ── Toast ──────────────────────────────────────────────────────────
  function toast(type, msg, dur){
    dur = dur || 3000;
    try {
      var c = document.getElementById('toast-container');
      if (!c) { c = document.createElement('div'); c.id='toast-container'; document.body.appendChild(c); }
      var el = document.createElement('div');
      el.className = 'toast ' + type;
      var icons = {success:'OK', info:'i', warning:'!', error:'X'};
      el.innerHTML = '<span>'+(icons[type]||'')+'</span><span>'+msg+'</span>';
      c.appendChild(el);
      setTimeout(function(){
        el.style.opacity='0';
        el.style.transition='opacity 300ms';
        setTimeout(function(){ try{ el.remove(); }catch(e){} }, 300);
      }, dur);
    } catch (e) {
      console.error('[SQM toast 실패]', e, type, msg);
    }
  }
  window.showToast = toast;

  // ── API call (XHR, no Promise 의존) ───────────────────────────────
  function apiCall(method, path, body, cb){
    try {
      var xhr = new XMLHttpRequest();
      xhr.open(method, API_BASE + path, true);
      xhr.setRequestHeader('Content-Type','application/json');
      xhr.timeout = 5000;
      xhr.onload  = function(){
        var data = null;
        try { data = JSON.parse(xhr.responseText); } catch(e) { data = xhr.responseText; }
        cb(null, data, xhr.status);
      };
      xhr.onerror   = function(){ cb(new Error('network')); };
      xhr.ontimeout = function(){ cb(new Error('timeout')); };
      xhr.send(body ? JSON.stringify(body) : null);
    } catch (e) {
      cb(e);
    }
  }

  // ══════════════════════════════════════════════════════════════════
  // 1) 메뉴 드롭다운: 클릭 기반 토글 (hover 만으로는 PyWebView/Chromium
  //    flex-container 에서 간헐적으로 hover 가 끊겨 submenu 클릭이
  //    등록되지 않는 버그가 재현됨 → 클릭 기반으로 전환).
  // ══════════════════════════════════════════════════════════════════
  function closeAllMenus(except){
    var opens = document.querySelectorAll('.menu-btn.open');
    for (var i=0;i<opens.length;i++){
      if (opens[i] !== except) opens[i].classList.remove('open');
    }
  }

  document.addEventListener('click', function(ev){
    // 1-A. 메뉴바 버튼 자체 클릭 (data-menu 있고 data-action 없음) → 드롭다운 토글
    var menuBtn = ev.target && ev.target.closest && ev.target.closest('.menu-btn[data-menu]');
    var actionEl = ev.target && ev.target.closest && ev.target.closest('[data-action]');

    if (menuBtn && !actionEl) {
      ev.preventDefault();
      ev.stopPropagation();
      var wasOpen = menuBtn.classList.contains('open');
      closeAllMenus();
      if (!wasOpen) menuBtn.classList.add('open');
      console.debug('[SQM menu] toggle', menuBtn.dataset.menu, 'open=', !wasOpen);
      return;
    }

    // 1-B. 메뉴 밖 클릭 → 전부 닫기
    if (!actionEl && !menuBtn) {
      closeAllMenus();
    }
  }, true); // capture-phase: 다른 스크립트가 stopPropagation 해도 작동

  // ESC 로 드롭다운 닫기
  document.addEventListener('keydown', function(ev){
    if (ev.key === 'Escape') closeAllMenus();
  });

  // ══════════════════════════════════════════════════════════════════
  // 2) data-action 핸들러 (메뉴 아이템 + 툴바 + topbar)
  // ══════════════════════════════════════════════════════════════════
  document.addEventListener('click', function(ev){
    var el = ev.target && ev.target.closest && ev.target.closest('[data-action]');
    if (!el) return;
    ev.preventDefault();

    var action = el.dataset.action;
    var label  = (el.textContent || '').trim() || action;
    console.debug('[SQM action]', action, '→', label);

    // 테마/새로고침 처리
    if (action === 'theme-dark') {
      document.documentElement.setAttribute('data-theme','dark');
      document.body.setAttribute('data-theme','dark');
      try { localStorage.setItem('sqm_theme','dark'); } catch(e){}
      toast('success','다크 모드'); closeAllMenus(); return;
    }
    if (action === 'theme-light') {
      document.documentElement.setAttribute('data-theme','light');
      document.body.setAttribute('data-theme','light');
      try { localStorage.setItem('sqm_theme','light'); } catch(e){}
      toast('success','라이트 모드'); closeAllMenus(); return;
    }
    if (action === 'refresh-all') {
      toast('info','새로고침 중...');
      loadDashboard(); loadAlerts(); loadStatusbar();
      closeAllMenus();
      return;
    }

    // 실제 엔드포인트가 있으면 호출, 없으면 안내 토스트
    // (backend/api/menubar.py 실존 경로에 맞춰 교정됨)
    var ENDPOINTS = {
      // Toolbar
      'tb-pdf-inbound':       {m:'POST', p:'/api/menu/-on-pdf-inbound'},
      'tb-quick-outbound':    {m:'POST', p:'/api/menu/-on-quick-outbound-paste'},
      'tb-return':            {m:'POST', p:'/api/menu/-show-return-dialog'},
      'tb-inventory':         {m:'GET',  p:'/api/inventory'},
      'tb-integrity':         {m:'GET',  p:'/api/integrity/quick'},
      'tb-backup':            {m:'POST', p:'/api/menu/-on-backup-click'},
      'tb-settings':          {m:'POST', p:'/api/menu/-show-email-config'},
      // File 메뉴
      'onExport':             {m:'POST', p:'/api/export/excel'},
      // File 메뉴 (Phase 1c 추가: v864.2 P0 복구)
      'onDoUpdate':           {m:'POST', p:'/api/menu/-on-do-update'},
      'onReturnDialog':       {m:'POST', p:'/api/menu/-show-return-dialog'},
      'onReturnInboundUpload':{m:'POST', p:'/api/menu/-on-return-inbound-upload'},
      'onReturnStatistics':   {m:'GET',  p:'/api/menu/-show-return-statistics'},
      // 입고
      'onOnPdfInbound':       {m:'POST', p:'/api/menu/-on-pdf-inbound'},
      // 출고
      'onOnQuickOutbound':    {m:'POST', p:'/api/menu/-on-quick-outbound-paste'},
      'onOutboundScheduled':  {m:'GET',  p:'/api/outbound/scheduled'},
      'onOutboundHistory':    {m:'GET',  p:'/api/outbound/history'},
      // 출고 (Phase 1c 추가: v864.2 재고메뉴 이전)
      'onOutboundStatus':     {m:'GET',  p:'/api/menu/-show-outbound-history'},
      // 재고
      'onInventoryList':      {m:'GET',  p:'/api/inventory'},
      'onIntegrityCheck':     {m:'GET',  p:'/api/integrity/quick'},
      // 보고서
      'onReportExport':       {m:'POST', p:'/api/export/excel'},
      // 보고서 (Phase 1c 추가: v864.2 P0 복구 + 재고메뉴 이전)
      'onInvoiceGenerate':    {m:'POST', p:'/api/menu/-generate-outbound-invoice'},
      'onDetailOfOutbound':   {m:'POST', p:'/api/menu/-on-detail-of-outbound-report'},
      'onSalesOrderDN':       {m:'POST', p:'/api/menu/-on-sales-order-dn-report'},
      'onDnCrossCheck':       {m:'POST', p:'/api/menu/-on-dn-cross-check'},
      'onLotDetailPdf':       {m:'POST', p:'/api/menu/-generate-lot-detail-pdf'},
      'onLotListExcel':       {m:'POST', p:'/api/export/excel?option=3'},
      'onTonbagListExcel':    {m:'POST', p:'/api/export/excel?option=4'},
      // 설정/도구
      'onOnBackup':           {m:'POST', p:'/api/menu/-on-backup-click'},
      'onRestore':            {m:'POST', p:'/api/menu/-on-restore-click'},
      'onSettings':           {m:'POST', p:'/api/menu/-show-email-config'},
      // 설정/도구 (Phase 1c 추가: v864.2 P0 복구)
      'onProductMaster':      {m:'POST', p:'/api/menu/-show-product-master'},
      'onProductInventoryReport': {m:'GET', p:'/api/menu/-show-product-inventory-report'},
      'onIntegrityRepair':    {m:'POST', p:'/api/menu/-on-integrity-check'},
      'onOptimizeDb':         {m:'POST', p:'/api/menu/-on-optimize-db'},
      'onCleanupLogs':        {m:'POST', p:'/api/menu/-on-cleanup-logs'},
      'onDbInfo':             {m:'GET',  p:'/api/menu/-show-db-info'}
    };

    var ep = ENDPOINTS[action];
    closeAllMenus();

    if (!ep) {
      toast('info', label + ' (엔진 연결 예정)');
      return;
    }

    // pending 토스트 → 결과 토스트
    toast('info', label + ' 요청 중…', 1200);
    apiCall(ep.m, ep.p, null, function(err, data, status){
      if (err) {
        console.warn('[SQM api 실패]', action, err);
        toast('error', label + ' — ' + err.message);
        return;
      }
      // v864.3 Phase 2 Step 3 — 새 계약: 200 + body.ok=false (NOT_READY soft-fail)
      var isNotReady = (data && data.ok === false &&
                        data.detail && data.detail.code === 'NOT_READY');
      if (isNotReady) {
        toast('info', label + ' — 준비 중 (아직 구현되지 않음)');
        return;
      }
      if (status >= 200 && status < 300) {
        if (data && data.ok === false) {
          toast('warning', label + ' — ' + (data.error || 'soft-fail'));
        } else {
          toast('success', label + ' 완료');
        }
      } else if (status === 404) {
        toast('warning', label + ' — 엔드포인트 없음 (' + ep.p + ')');
      } else if (status === 501) {
        // legacy path (should no longer trigger after Phase 2 Step 3)
        toast('info', label + ' — 엔진 메서드 준비 중');
      } else {
        toast('warning', label + ' — HTTP ' + status);
      }
    });
  });

  // ══════════════════════════════════════════════════════════════════
  // 3) 사이드바 라우터 (data-route)
  // ══════════════════════════════════════════════════════════════════
  function renderPage(route){
    var el = document.getElementById('page-container');
    if (!el) return;
    var labels = {
      dashboard:'Dashboard', inventory:'Inventory', allocation:'Allocation',
      picked:'Picked', outbound:'Outbound', return:'Return', move:'Move',
      log:'Log', scan:'Scan'
    };
    if (route === 'dashboard') { loadDashboard(); return; }
    el.innerHTML = '<div style="padding:20px"><h3>'+labels[route]+'</h3><div class="loading">데이터 로딩 중…</div></div>';
    var endpoints = {
      inventory: '/api/inventory',
      allocation: '/api/allocation',
      picked: '/api/outbound/scheduled',
      outbound: '/api/outbound/history',
      return: '/api/inventory?status=RETURN',
      move: '/api/move/history',
      log: '/api/log/activity?limit=100',
      scan: null
    };
    var p = endpoints[route];
    if (!p) {
      el.innerHTML = '<div style="padding:20px"><h3>'+labels[route]+'</h3><div class="empty">표시할 데이터가 없습니다</div></div>';
      return;
    }
    apiCall('GET', p, null, function(err, data, status){
      if (err) {
        el.innerHTML = '<div style="padding:20px"><h3>'+labels[route]+'</h3><div class="empty">로드 실패: '+err.message+'</div></div>';
        return;
      }
      var rows = (data && (data.data || data)) || [];
      if (!Array.isArray(rows)) rows = (rows && rows.data) || [];
      if (!rows.length) {
        el.innerHTML = '<div style="padding:20px"><h3>'+labels[route]+'</h3><div class="empty">데이터 없음</div></div>';
        return;
      }
      var keys = Object.keys(rows[0] || {});
      var thead = '<tr>' + keys.map(function(k){ return '<th>'+k+'</th>'; }).join('') + '</tr>';
      var tbody = rows.slice(0,100).map(function(r){
        return '<tr>' + keys.map(function(k){ return '<td>'+(r[k] == null ? '' : r[k])+'</td>'; }).join('') + '</tr>';
      }).join('');
      el.innerHTML = '<div style="padding:8px"><h3>'+labels[route]+' ('+rows.length+'건)</h3>'+
                     '<table class="data-table"><thead>'+thead+'</thead><tbody>'+tbody+'</tbody></table></div>';
    });
  }

  document.addEventListener('click', function(ev){
    var el = ev.target && ev.target.closest && ev.target.closest('[data-route]');
    if (!el) return;
    ev.preventDefault();
    console.debug('[SQM route]', el.dataset.route);
    var all = document.querySelectorAll('[data-route]');
    for (var i=0;i<all.length;i++) all[i].classList.remove('active');
    el.classList.add('active');
    renderPage(el.dataset.route);
  });

  document.addEventListener('change', function(ev){
    var el = ev.target && ev.target.closest && ev.target.closest('[data-view-mode]');
    if (!el) return;
    var mode = el.dataset.viewMode;
    document.documentElement.setAttribute('data-view-mode', mode);
    try { localStorage.setItem('sqm_view_mode', mode); } catch(e){}
    toast('info', '뷰 모드: ' + mode.toUpperCase());
  });

  // ══════════════════════════════════════════════════════════════════
  // 4) 대시보드 / 경고 / 상태바 로더
  // ══════════════════════════════════════════════════════════════════
  function fmt(v){
    return typeof v==='number'
      ? v.toLocaleString('ko-KR',{minimumFractionDigits:1, maximumFractionDigits:1})
      : (v == null ? '-' : v);
  }

  // Phase 3 Q1 — KPI 카드 HTML 생성 헬퍼
  function kpiCard(id, label, icon, unit){
    return '<div class="kpi-card" style="'+
      'background:var(--panel,#1e1e2e);border:1px solid var(--panel-border,#444);'+
      'border-radius:6px;padding:12px 16px;text-align:center;min-width:0">'+
      '<div style="font-size:1.4em;margin-bottom:4px">'+icon+'</div>'+
      '<div style="font-size:0.75em;color:var(--text-muted,#aaa);margin-bottom:6px">'+label+'</div>'+
      '<div id="'+id+'" style="font-size:1.6em;font-weight:700;color:var(--accent,#58a6ff)">—</div>'+
      '<div style="font-size:0.7em;color:var(--text-muted,#aaa);margin-top:2px">'+unit+'</div>'+
    '</div>';
  }

  // Phase 3 Q1 — KPI 숫자 카운트업 애니메이션 (300ms ease-out)
  function animateKpi(id, target){
    var el = document.getElementById(id);
    if (!el) return;
    var start = 0;
    var dur = 300;
    var t0 = performance.now();
    var isFloat = (target % 1 !== 0);
    function step(now){
      var p = Math.min((now - t0) / dur, 1);
      var ease = 1 - Math.pow(1 - p, 3);  // ease-out cubic
      var cur = start + (target - start) * ease;
      el.textContent = isFloat
        ? cur.toLocaleString('ko-KR',{minimumFractionDigits:1, maximumFractionDigits:1})
        : Math.round(cur).toLocaleString('ko-KR');
      if (p < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
  }

  // Phase 3 Q1 — KPI 폴링 (5초 interval, 전역 1개만 유지)
  var _kpiTimer = null;
  function startKpiPolling(){
    if (_kpiTimer) clearInterval(_kpiTimer);
    fetchKpi();                              // 즉시 1회
    _kpiTimer = setInterval(fetchKpi, 5000); // 5초마다
  }
  function stopKpiPolling(){
    if (_kpiTimer){ clearInterval(_kpiTimer); _kpiTimer = null; }
  }

  function fetchKpi(){
    // KPI 카드가 DOM 에 없으면 폴링 중단
    if (!document.getElementById('kpi-inbound')){ stopKpiPolling(); return; }
    fetch(API_BASE + '/api/dashboard/kpi')
      .then(function(r){ return r.ok ? r.json() : null; })
      .then(function(j){
        if (!j || !j.data) return;
        var d = j.data;
        var ok = (j.ok !== false);
        // ok=false → 회색 "—" 표시
        if (!ok){
          ['kpi-inbound','kpi-outbound','kpi-stock','kpi-unloc'].forEach(function(id){
            var el = document.getElementById(id);
            if (el){ el.textContent = '—'; el.style.color = 'var(--text-muted,#aaa)'; }
          });
          return;
        }
        animateKpi('kpi-inbound',  d.today_inbound_mt   || 0);
        animateKpi('kpi-outbound', d.today_outbound_mt  || 0);
        animateKpi('kpi-stock',    d.current_stock_lots  || 0);
        animateKpi('kpi-unloc',    d.unassigned_locations || 0);
        // 갱신 시각 표시
        var ts = document.getElementById('kpi-updated-at');
        if (ts && d.updated_at) ts.textContent = '최종 갱신: ' + d.updated_at.replace('T',' ').slice(0,19);
      })
      .catch(function(e){
        console.warn('[SQM kpi poll 실패]', e);
      });
  }

  function loadDashboard(){
    var el = document.getElementById('page-container');
    if (!el) return;

    // ── KPI 카드 4개 + 기존 테이블 레이아웃 ──────────────────────
    el.innerHTML =
      // KPI 카드 행
      '<div style="padding:8px 8px 0">'+
        '<div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:8px">'+
          kpiCard('kpi-inbound',  '오늘 입고',     '📥', 'MT') +
          kpiCard('kpi-outbound', '오늘 출고',     '📤', 'MT') +
          kpiCard('kpi-stock',    '현재 재고',     '📦', 'LOT') +
          kpiCard('kpi-unloc',    '위치 미배정',   '📍', '개') +
        '</div>'+
        '<div id="kpi-updated-at" style="font-size:0.7em;color:var(--text-muted,#aaa);text-align:right;margin-bottom:4px"></div>'+
      '</div>'+
      // 기존 제품별/LOT 테이블 (로딩 placeholder)
      '<div id="dash-tables" style="display:grid;grid-template-columns:1fr 1fr;gap:12px;padding:0 8px 8px;height:calc(100% - 130px)">'+
        '<div style="background:var(--panel);border:1px solid var(--panel-border);border-radius:4px;padding:8px;overflow:auto">'+
          '<div class="loading">재고 테이블 로딩 중…</div></div>'+
        '<div style="background:var(--panel);border:1px solid var(--panel-border);border-radius:4px;padding:8px;overflow:auto">'+
          '<div class="loading">LOT 테이블 로딩 중…</div></div>'+
      '</div>';

    // KPI 폴링 시작
    startKpiPolling();

    // 기존 테이블 데이터 로드
    apiCall('GET', '/api/dashboard/stats', null, function(err, data){
      var tables = document.getElementById('dash-tables');
      if (!tables) return;

      var products = [{name:'LITHIUM CARBONATE', sellable:200.0, reserved:0, committed:0, outbound_done:0, return_wait:0, total:200.0, sample:40}];
      var lots = [{opening:200.0, inbound:0, outbound:0, ending:200.0, status:'OK'}];
      if (!err && data) {
        if (data.products) products = data.products;
        if (data.lots)     lots     = data.lots;
      }

      var prodRows = products.map(function(r,i){
        return '<tr><td>'+(i+1)+'</td><td style="text-align:left">'+r.name+'</td>'+
          '<td>'+fmt(r.sellable)+'</td><td>'+fmt(r.reserved)+'</td><td>'+fmt(r.committed)+'</td>'+
          '<td>'+fmt(r.outbound_done)+'</td><td>'+fmt(r.return_wait)+'</td>'+
          '<td><b>'+fmt(r.total)+'</b></td><td>'+(r.sample||'-')+'</td></tr>';
      }).join('');
      var totalSum  = products.reduce(function(a,r){ return a+(r.total||0); }, 0);
      var sampleSum = products.reduce(function(a,r){ return a+(r.sample||0); }, 0);
      prodRows += '<tr class="total-row"><td></td><td style="text-align:left"><b>합계</b></td>'+
                  '<td>'+fmt(totalSum)+'</td><td>0.0</td><td>0.0</td><td>0.0</td><td>0.0</td>'+
                  '<td><b>'+fmt(totalSum)+'</b></td><td>'+sampleSum+'</td></tr>';

      var lotRows = lots.map(function(r,i){
        return '<tr><td>'+(i+1)+'</td><td>'+fmt(r.opening)+'</td><td>'+fmt(r.inbound)+'</td>'+
          '<td>'+fmt(r.outbound)+'</td><td>'+fmt(r.ending)+'</td>'+
          '<td><span style="color:#2e7d32;font-weight:700">'+(r.status||'OK')+'</span></td></tr>';
      }).join('');

      tables.innerHTML =
        '<div style="background:var(--panel);border:1px solid var(--panel-border);border-radius:4px;padding:8px;overflow:auto">'+
          '<table class="data-table"><thead><tr>'+
            '<th style="width:40px">순번</th><th style="text-align:left">Product</th>'+
            '<th>판매가능</th><th>판매배정</th><th>판매화물</th>'+
            '<th>출고완료</th><th>반품대기</th><th>합계</th><th>샘플</th>'+
          '</tr></thead><tbody>'+prodRows+'</tbody></table></div>'+
        '<div style="background:var(--panel);border:1px solid var(--panel-border);border-radius:4px;padding:8px;overflow:auto">'+
          '<table class="data-table"><thead><tr>'+
            '<th style="width:40px">순번</th><th>기초재고</th><th>입고</th><th>출고</th><th>기말재고</th><th>검증</th>'+
          '</tr></thead><tbody>'+lotRows+'</tbody></table></div>';
    });
  }

  function loadAlerts(){
    var el = document.getElementById('alerts-container');
    if (!el) return;
    var fb = [
      {sev:'warning', icon:'태그', text:'톤백 무결성 이슈 40건 — inventory.current_weight 불일치 LOT 감지. [재고관리 → 정합성 검사]에서 수동 보정 필요'},
      {sev:'error',   icon:'위치', text:'위치 미배정 톤백 400개 (5 LOT) — 입고 후 창고 위치 미지정. [재고관리 → 위치배정] 즉시 처리 필요'}
    ];
    var html = '<div class="alerts-header"><span>ALERTS 알림 및 경고</span><span class="alerts-counter">'+fb.length+'</span></div>'+
               '<ul class="alerts-list">'+fb.map(function(a){
                 return '<li class="alert alert-'+a.sev+'"><span class="alert-icon">'+a.icon+'</span><span class="alert-text">'+a.text+'</span></li>';
               }).join('')+'</ul>';
    el.innerHTML = html;
  }

  function loadStatusbar(){
    var el = document.getElementById('statusbar-container');
    if (!el) return;
    // 1단계: 기본 구조 즉시 렌더 (Modules 값은 '?/?' placeholder)
    el.innerHTML = '<div class="statusbar">'+
      '<span id="sb-modules" class="sb-modules" title="엔진 모듈 가용성">Modules: ?/?</span><span class="sb-sep">|</span>'+
      '<span>위치 미배정 400개</span><span class="sb-sep">|</span>'+
      '<span>스캔 실패율 -</span><span class="sb-sep">|</span>'+
      '<span>LOT 평균 재고기간 6.2일</span>'+
      '<span class="sb-flex"></span>'+
      '<span>마지막 경신: '+new Date().toLocaleString('ko-KR')+'</span>'+
      '<label class="sb-auto"><input type="checkbox" checked> 자동 새로고침 (30초)</label>'+
    '</div>';
    // 2단계: /api/health 비동기 조회 → Modules X/Y 갱신 (Phase 1c-B Q3-A)
    try {
      fetch(API_BASE + '/api/health').then(function(r){
        return r.ok ? r.json() : null;
      }).then(function(j){
        if (!j) return;
        var h = (j && j.data) ? j.data : (j || {});
        // engine_available(신) | engine(legacy) 양방향 지원 (Phase 1c-B hot-fix)
        var engineOk = (h.engine_available != null) ? h.engine_available : h.engine;
        var loaded = (h.modules_loaded != null) ? h.modules_loaded : (engineOk ? 8 : 0);
        var total = (h.modules_total != null) ? h.modules_total : 8;
        // Phase 3 Q2: 🟢/🔴 이모지 + "Engine X/Y" 형식
        var color = (loaded === total && total > 0) ? '🟢' : '🔴';
        var sb = document.getElementById('sb-modules');
        if (sb) sb.textContent = color + ' Engine ' + loaded + '/' + total;
      }).catch(function(){ /* 무시 — placeholder 유지 */ });
    } catch(e){ /* 무시 */ }
  }

  // ══════════════════════════════════════════════════════════════════
  // 5) 초기화 + 전역 디버그 헬퍼
  // ══════════════════════════════════════════════════════════════════
  function init(){
    try {
      var t = localStorage.getItem('sqm_theme') || 'light';
      document.documentElement.setAttribute('data-theme', t);
      document.body.setAttribute('data-theme', t);
    } catch(e){}
    loadDashboard();
    loadAlerts();
    loadStatusbar();
    setInterval(function(){
      if (document.visibilityState === 'visible') loadStatusbar();
    }, 30000);
    console.info('[SQM inline] 초기화 완료', VERSION);
    toast('success', 'v864.3 준비 완료 (' + VERSION + ')');
  }

  // 디버그 헬퍼 — 우클릭→검사→콘솔에서 SQM.test() 로 한 번에 점검
  window.SQM = window.SQM || {};
  window.SQM.version = VERSION;
  window.SQM.test = function(){
    var menus = document.querySelectorAll('.menu-btn[data-menu]').length;
    var actions = document.querySelectorAll('[data-action]').length;
    var routes = document.querySelectorAll('[data-route]').length;
    console.log('[SQM.test] menus=', menus, 'actions=', actions, 'routes=', routes);
    console.log('[SQM.test] API_BASE=', API_BASE);
    return { version: VERSION, menus: menus, actions: actions, routes: routes };
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
