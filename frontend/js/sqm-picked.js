/* SQM Inventory v8.7.0 — sqm-picked.js (Picked — 출고예정) */
(function () {
  'use strict';
  /* ─── sqm-core.js 공유 함수 로컬 앨리어스 ─────────────────────────
     sqm-core.js 가 먼저 로드된 뒤 window.* 에 할당된 함수들을
     this IIFE 내부 변수로 re-bind. 직접 호출 패턴 유지. */
  var showToast     = function() { return window.showToast.apply(window, arguments); };
  var apiCall       = function() { return window.apiCall.apply(window, arguments); };
  var apiGet        = function() { return window.apiGet.apply(window, arguments); };
  var apiPost       = function() { return window.apiPost.apply(window, arguments); };
  var renderPage    = function() { return window.renderPage.apply(window, arguments); };
  var closeAllMenus = function() { return window.closeAllMenus.apply(window, arguments); };
  var getStore      = function() { return window.getStore.apply(window, arguments); };
  var escapeHtml    = function() { return window.escapeHtml.apply(window, arguments); };
  var dbgLog        = function() { return window.dbgLog.apply(window, arguments); };
  var extractRows               = function() { return window.extractRows.apply(window, arguments); };
  var fmtN                      = function() { return window.fmtN.apply(window, arguments); };
  /* ──────────────────────────────────────────────────────────────── */

  function pickedStatusPalette(status) {
    var st = String(status || '').toUpperCase();
    if (st === 'AVAILABLE') return { bg: 'rgba(34,197,94,0.18)', fg: '#22c55e' };
    if (st === 'RESERVED' || st === 'ALLOCATED') return { bg: 'rgba(245,158,11,0.22)', fg: '#f59e0b' };
    if (st === 'PICKED') return { bg: 'rgba(59,130,246,0.22)', fg: '#3b82f6' };
    if (st === 'SOLD' || st === 'SHIPPED' || st === 'CONFIRMED') return { bg: 'rgba(239,68,68,0.2)', fg: '#ef4444' };
    if (st === 'RETURN' || st === 'RETURNED') return { bg: 'rgba(168,85,247,0.2)', fg: '#a855f7' };
    if (st === 'INBOUND') return { bg: 'rgba(59,130,246,0.22)', fg: '#3b82f6' };
    if (st === 'HOLD') return { bg: 'rgba(148,163,184,0.2)', fg: '#94a3b8' };
    return { bg: 'rgba(148,163,184,0.2)', fg: '#94a3b8' };
  }

  // v868 fix (2026-05-16): Picked 탭 Excel 내보내기 헬퍼
  window.exportPickedExcel = function() {
    var tbl = document.getElementById('picked-table');
    if (!tbl) { if (window.showToast) showToast('warning', '내보낼 테이블이 없습니다'); return; }
    var ts = new Date().toISOString().slice(0,10);
    if (window.exportTableToExcel) {
      window.exportTableToExcel(tbl, 'picked_' + ts + '.xlsx');
    } else {
      alert('Excel 내보내기 함수를 찾을 수 없습니다 (exportTableToExcel)');
    }
  };

  // v868 fix (2026-05-16): Picked 그룹화 헬퍼 — Pending 패턴 차용
  window._renderPickedGroup = function(rows, mode) {
    var groups = {};
    function keyOf(r) {
      if (mode === 'customer') return (r.customer || r.picked_to || '(고객사 미지정)');
      if (mode === 'date') {
        var d = r.inbound_date || r.picking_date || '';
        d = String(d).slice(0, 10);
        return d || '(입고일 미지정)';
      }
      return r.lot_no || '(LOT 미지정)';
    }
    rows.forEach(function(r, _i) {
      var k = keyOf(r);
      if (!groups[k]) groups[k] = [];
      groups[k].push(r);
    });
    var keys = Object.keys(groups).sort(function(a, b) {
      if (a.indexOf('미지정') >= 0) return 1;
      if (b.indexOf('미지정') >= 0) return -1;
      // 날짜 모드는 최신순(내림차순)
      if (mode === 'date') return b.localeCompare(a);
      return a.localeCompare(b);
    });
    var labelPrefix = (mode === 'customer') ? '고객사: ' : (mode === 'date' ? '입고일: ' : 'LOT: ');
    var html = '';
    keys.forEach(function(k, idx) {
      var lots = groups[k];
      var sumBags = 0, sumKg = 0, sumAvail = 0, sumReserved = 0, sumPacked = 0;
      lots.forEach(function(r) {
        sumBags     += Number(r.tonbag_count || 0) || 0;
        sumKg       += Number(r.total_kg     || 0) || 0;
        sumAvail    += Number(r.tb_available || 0) || 0;
        sumReserved += Number(r.tb_reserved  || 0) || 0;
        sumPacked   += Number(r.tb_picked    || 0) || 0;
      });
      var groupId = 'pickg-' + idx;
      html += '<div style="margin-bottom:12px;border:1px solid var(--border,#334155);border-radius:8px;overflow:hidden">'
        + '<div style="display:flex;align-items:center;gap:10px;padding:10px 14px;background:var(--surface,#1e293b);cursor:pointer;flex-wrap:wrap" '
        + 'onclick="window._togglePickedGroup(\'' + groupId + '\')">'
        + '<strong style="color:#3b82f6;font-family:monospace">' + escapeHtml(labelPrefix + k) + '</strong>'
        + '<span style="display:inline-block;padding:3px 14px;margin-right:6px;background:#FFD600;border-radius:6px;font-size:13px;color:#222;font-weight:800;box-shadow:0 1px 3px rgba(0,0,0,.2);">'
        + lots.length + ' LOT · ' + sumBags + ' Bags · ' + fmtN(sumKg) + ' kg</span>'
        + '<span style="font-size:11px;color:var(--text-muted);margin-left:auto">'
        + '<span style="color:#22c55e;font-weight:700">A ' + sumAvail + '</span> · '
        + '<span style="color:#3b82f6;font-weight:700">R ' + sumReserved + '</span> · '
        + '<span style="color:#f59e0b;font-weight:700">P ' + sumPacked + '</span>'
        + '</span>'
        + '</div>'
        + '<div id="' + groupId + '" style="display:block">'
        + _renderPickedLotTableOnly(lots)
        + '</div>'
        + '</div>';
    });
    return html;
  };

  window._togglePickedGroup = function(id) {
    var el = document.getElementById(id);
    if (!el) return;
    el.style.display = el.style.display === 'none' ? 'block' : 'none';
  };

  // 그룹 내부용 LOT 표 (헤더 포함, 컴팩트)
  function _renderPickedLotTableOnly(rows) {
    var html = '<div style="overflow-x:auto"><table class="data-table" style="margin:0;font-size:12px"><thead><tr>'
      + '<th style="color:var(--text-muted);text-align:center;width:32px">#</th>'
      + '<th style="text-align:center">LOT No</th>'
      + '<th>피킹No</th><th>고객사</th>'
      + '<th style="text-align:right">톤백수</th><th style="text-align:right">중량(kg)</th>'
      + '<th title="총 톤백 개수 (MAXI BAG)" style="text-align:center">MXBG</th>'
      + '<th title="가용 톤백 수(개) — 바로 배분 가능한 톤백" style="text-align:center">Available</th>'
      + '<th title="예약 톤백 수(개) — 배정 잡힌 톤백" style="text-align:center">Reserved</th>'
      + '<th title="피킹/포장된 톤백 수(개)" style="text-align:center">Packed</th>'
      + '<th>Title Transfer</th>'
      + '<th style="width:32px;text-align:center">⋯</th>'
      + '</tr></thead><tbody>';
    rows.forEach(function(r, _i) {
      var lot = escapeHtml(r.lot_no || '');
      var availBags = Number(r.tb_available || 0) || 0;
      var reservedBags = Number(r.tb_reserved || 0) || 0;
      var packedBags = Number(r.tb_picked || 0) || 0;
      html += '<tr class="picked-summary-row" data-lot="' + lot + '" style="cursor:pointer" onclick="window.togglePickedDetail(\'' + lot + '\')">'
        + '<td class="mono-cell" style="color:var(--text-muted);text-align:center">' + (_i+1) + '</td>'
        + '<td class="mono-cell" style="color:var(--accent);font-weight:600">' + lot + '</td>'
        + '<td class="mono-cell">' + escapeHtml(r.picking_no || '') + '</td>'
        + '<td>' + escapeHtml(r.customer || r.picked_to || '') + '</td>'
        + '<td class="mono-cell" style="text-align:right">' + (r.tonbag_count || 0) + '</td>'
        + '<td class="mono-cell" style="text-align:right">' + (r.total_kg != null ? fmtN(r.total_kg) : '-') + '</td>'
        + '<td title="총 톤백 개수 (MAXI BAG)" class="mono-cell" style="text-align:center">' + (r.mxbg_pallet != null ? r.mxbg_pallet : '-') + '</td>'
        + '<td title="가용 톤백 수(개) — 바로 배분 가능한 톤백" class="mono-cell" style="text-align:center;color:#22c55e;font-weight:700">' + availBags + '</td>'
        + '<td title="예약 톤백 수(개) — 배정 잡힌 톤백" class="mono-cell" style="text-align:center;color:#3b82f6;font-weight:700">' + reservedBags + '</td>'
        + '<td title="피킹/포장된 톤백 수(개)" class="mono-cell" style="text-align:center;color:#f59e0b;font-weight:700">' + packedBags + '</td>'
        + '<td class="mono-cell">' + escapeHtml(r.picking_date || '') + '</td>'
        + '<td style="text-align:center;padding:3px 4px"><button class="btn btn-ghost btn-xs" data-lot="' + lot + '" onclick="event.stopPropagation();window.showPickedActionMenu(this)" style="font-size:15px;padding:0 4px;letter-spacing:1px" title="추가기능">⋯</button></td>'
        + '</tr>';
    });
    return html + '</tbody></table></div>';
  }

  function loadPickedPage() {
    var route = window.getCurrentRoute();
    var c = document.getElementById('page-container');
    if (!c) return;
    // v868 fix (2026-05-16): Picked 그룹화 모드 (LOT/고객사/입고일)
    var pickedMode = window._pickedViewMode || 'lot';
    function _pickedModeBtnHtml(val, label, cur) {
      var act = val === cur
        ? 'background:var(--accent,#3b82f6);color:#fff;border:1px solid var(--accent,#3b82f6);border-radius:4px;'
        : 'background:var(--surface,#1e293b);color:var(--text-muted);border:1px solid var(--border,#334155);border-radius:4px;';
      return '<button class="btn" style="font-size:12px;padding:3px 10px;cursor:pointer;' + act + '" '
        + 'onclick="window._pickedViewMode=\'' + val + '\';window.loadPickedPage()">' + label + '</button>';
    }
    c.innerHTML = [
      '<section class="page sqm-page-wrap" data-page="picked">',
      /* ── 페이지 헤더 (B형) ── */
      '<div class="sqm-page-hd">',
      '  <div class="sqm-page-hd-title">🚛 PICKED</div>',
      '  <span id="picked-count" class="sqm-page-hd-count"></span>',
      '  <div class="sqm-page-hd-actions">',
      '    <span style="font-size:11px;color:var(--text-muted)">그룹:</span>',
      '    ' + _pickedModeBtnHtml('lot', 'LOT별', pickedMode),
      '    ' + _pickedModeBtnHtml('customer', '고객사별', pickedMode),
      '    ' + _pickedModeBtnHtml('date', '입고일별', pickedMode),
      '    <button class="btn" style="font-size:11px;background:rgba(239,68,68,0.15);color:#ef4444;border:1px solid #ef444455;border-radius:4px;padding:3px 8px" onclick="window.allocRevertStep(\'PICKED\')" title="PICKED→RESERVED">↩ PICKED→RESERVED</button>',
      '    <button class="btn btn-ghost" style="font-size:11px" onclick="window.exportPickedExcel()">📊 Excel</button>',
      '    <button class="btn btn-ghost" style="font-size:11px" onclick="renderPage(\'picked\')">🔁</button>',
      '  </div>',
      '</div>',
      /* ── 필터바 (B형) ── */
      '<div class="sqm-filter-bar">',
      '  <label>검색</label>',
      '  <input id="picked-q" type="text" placeholder="LOT · BL · 고객사" style="width:180px" oninput="window._pickedFilter()">',
      '  <label>날짜</label>',
      '  <input id="picked-df" type="date" onchange="window._pickedFilter()">',
      '  <span style="color:var(--text-muted)">~</span>',
      '  <input id="picked-dt" type="date" onchange="window._pickedFilter()">',
      '  <button class="btn btn-ghost" style="font-size:11px" onclick="window._pickedFilterReset()">✕ 초기화</button>',
      '</div>',
      '<div id="picked-loading" style="padding:40px;text-align:center;color:var(--text-muted)">⏳ 데이터 로딩 중...</div>',
      '<div class="sqm-b-table-wrap">',
      '  <table class="data-table" id="picked-table" style="display:none">',
      '  <thead><tr><th style="color:var(--text-muted);text-align:center;width:32px">#</th><th></th><th style="text-align:center">LOT No</th><th style="width:32px;text-align:center">+</th><th>피킹No</th><th>고객사</th><th>톤백수</th><th>중량(kg)</th><th title="총 톤백 개수 (MAXI BAG)">MXBG</th><th title="가용 톤백 수(개) — 바로 배분 가능한 톤백">Available</th><th title="예약 톤백 수(개) — 배정 잡힌 톤백">Reserved</th><th title="피킹/포장된 톤백 수(개)">Packed</th><th title="전체 톤백 수(개)">Total Bags</th><th title="남은 톤백 수 = 전체 − 가용 − 예약 − 피킹">Remain Bags</th><th title="가용 중량 AV (Available MT) — 아직 배정 안 된, 바로 배분 가능한 물량">AV</th><th title="예약 중량 VR (Reserved MT) — RESERVED 상태로 배정 잡힌 물량">VR</th><th title="피킹 중량 AR (Picked MT) — 출고 작업 중(PICKED)인 물량">AR</th><th>Title Transfer Date</th></tr></thead>',
      '  <tbody id="picked-tbody"></tbody>',
      '  </table>',
      '</div>',
      '<div class="empty" id="picked-empty" style="display:none;padding:60px;text-align:center">📭 피킹 데이터 없음</div>',
      '<div id="picked-detail-panel" style="display:none;margin-top:16px;border-top:2px solid var(--border);padding-top:16px">',
      '  <h3 id="picked-detail-title" style="margin:0 0 12px 0">톤백 상세</h3>',
      '  <div id="picked-detail-content"></div>',
      '</div>',
      '</section>'
    ].join('');

    apiGet('/api/q/picked-list').then(function(res){
      if (window.getCurrentRoute() !== route) return;
      var rows = extractRows(res);
      document.getElementById('picked-loading').style.display = 'none';
      if (!rows.length) { document.getElementById('picked-empty').style.display='block'; return; }
      // v868 fix (2026-05-16): 그룹화 모드 분기 — 고객사별/입고일별이면 별도 렌더 후 return
      if (pickedMode === 'customer' || pickedMode === 'date') {
        var tblEl = document.getElementById('picked-table');
        if (tblEl) tblEl.style.display = 'none';
        var hostEl = document.getElementById('picked-empty');
        if (hostEl) { hostEl.style.display = 'none'; }
        var pageEl = document.querySelector('section[data-page="picked"]');
        var oldGrp = document.getElementById('picked-group-host');
        if (oldGrp) oldGrp.parentNode.removeChild(oldGrp);
        var grpHost = document.createElement('div');
        grpHost.id = 'picked-group-host';
        grpHost.style.marginTop = '8px';
        if (pageEl) pageEl.insertBefore(grpHost, document.getElementById('picked-detail-panel'));
        grpHost.innerHTML = window._renderPickedGroup(rows, pickedMode);
        return;
      }
      var tbody = document.getElementById('picked-tbody');
      if (tbody) tbody.innerHTML = rows.map(function(r, _i){
        var lot = escapeHtml(r.lot_no||'');
        var availBags = Number(r.tb_available || 0) || 0;
        var reservedBags = Number(r.tb_reserved || 0) || 0;
        var packedBags = Number(r.tb_picked || 0) || 0;
        var totalBags = Number(r.total_bags != null ? r.total_bags : (r.mxbg_pallet || 0)) || 0;
        var remainBags = Math.max(totalBags - availBags - reservedBags - packedBags, 0);
        var availMt = Number(r.avail_mt || 0) || 0;
        var reservedMt = Number(r.reserved_mt || 0) || 0;
        var pickedMt = Number(r.picked_mt || 0) || 0;
        return '<tr class="picked-summary-row" data-lot="'+lot+'" style="cursor:pointer" onclick="window.togglePickedDetail(\''+lot+'\')">' +
          '<td class="mono-cell" style="color:var(--text-muted);text-align:center">'+(_i+1)+'</td>' +
          '<td style="width:24px;text-align:center"><span class="picked-expand-icon">▶</span></td>' +
          '<td class="mono-cell cell-left" style="color:var(--accent);font-weight:600">'+lot+'</td>' +
          '<td style="text-align:center;padding:3px 4px;width:32px">'+'<button class="btn btn-ghost btn-xs" data-lot="'+lot+'" onclick="event.stopPropagation();window.showPickedActionMenu(this)" style="font-size:15px;padding:0 4px;letter-spacing:1px" title="추가기능">⋯</button>'+'</td>' +
          '<td class="mono-cell">'+escapeHtml(r.picking_no||'')+'</td>' +
          '<td>'+escapeHtml(r.customer||r.picked_to||'')+'</td>' +
          '<td class="mono-cell" style="text-align:right">'+(r.tonbag_count||0)+'</td>' +
          '<td class="mono-cell" style="text-align:right">'+(r.total_kg!=null?fmtN(r.total_kg):'-')+'</td>' +
          '<td title="총 톤백 개수 (MAXI BAG)" class="mono-cell" style="text-align:center">'+(r.mxbg_pallet!=null?r.mxbg_pallet:'-')+'</td>' +
          '<td title="가용 톤백 수(개) — 바로 배분 가능한 톤백" class="mono-cell" style="text-align:center;color:#22c55e;font-weight:700">'+availBags+'</td>' +
          '<td title="예약 톤백 수(개) — 배정 잡힌 톤백" class="mono-cell" style="text-align:center;color:#3b82f6;font-weight:700">'+reservedBags+'</td>' +
          '<td title="피킹/포장된 톤백 수(개)" class="mono-cell" style="text-align:center;color:#f59e0b;font-weight:700">'+packedBags+'</td>' +
          '<td title="전체 톤백 수(개)" class="mono-cell" style="text-align:center">'+totalBags+'</td>' +
          '<td title="남은 톤백 수 = 전체 − 가용 − 예약 − 피킹" class="mono-cell" style="text-align:center;font-weight:700">'+remainBags+'</td>' +
          '<td title="가용 중량 AV (Available MT) — 아직 배정 안 된, 바로 배분 가능한 물량" class="mono-cell" style="text-align:right;color:#22c55e;font-weight:700">'+(availMt ? availMt.toFixed(3) : '0')+'</td>' +
          '<td title="예약 중량 VR (Reserved MT) — RESERVED 상태로 배정 잡힌 물량" class="mono-cell" style="text-align:right;color:#3b82f6;font-weight:700">'+(reservedMt ? reservedMt.toFixed(3) : '0')+'</td>' +
          '<td title="피킹 중량 AR (Picked MT) — 출고 작업 중(PICKED)인 물량" class="mono-cell" style="text-align:right;color:#f59e0b;font-weight:700">'+(pickedMt ? pickedMt.toFixed(3) : '0')+'</td>' +
          '<td class="mono-cell">'+escapeHtml(r.picking_date||'')+'</td>' +
          '</tr>';
      }).join('');
      // v8.7.0 노란 tfoot 합계
      (function() {
        var _sumTb = 0, _sumKg = 0, _sumAv = 0, _sumRv = 0, _sumPk = 0;
        rows.forEach(function(r) {
          _sumTb += Number(r.tonbag_count || 0);
          _sumKg += Number(r.total_kg     || 0);
          _sumAv += Number(r.tb_available || 0);
          _sumRv += Number(r.tb_reserved  || 0);
          _sumPk += Number(r.tb_picked    || 0);
        });
        var _tbl = document.getElementById('picked-table');
        if (_tbl && !_tbl.querySelector('tfoot')) {
          var _tf = document.createElement('tfoot');
          _tf.innerHTML =
            '<tr style="background:#FFD600;font-weight:800;color:#222;font-size:19px">'
            + '<td colspan="6" style="text-align:right;padding:6px 10px">'
            + '합계 ' + rows.length + ' LOT</td>'
            + '<td class="mono-cell" style="text-align:right;padding:6px 8px">'
            + _sumTb.toLocaleString('ko-KR') + '</td>'
            + '<td class="mono-cell" style="text-align:right;padding:6px 8px">'
            + (typeof fmtN === 'function' ? fmtN(_sumKg) : _sumKg.toFixed(0)) + '</td>'
            + '<td></td>'
            + '<td class="mono-cell" style="text-align:center;color:#22c55e">'
            + _sumAv + '</td>'
            + '<td class="mono-cell" style="text-align:center;color:#3b82f6">'
            + _sumRv + '</td>'
            + '<td class="mono-cell" style="text-align:center;color:#f59e0b">'
            + _sumPk + '</td>'
            + '<td colspan="5"></td>'
            + '</tr>';
          _tbl.appendChild(_tf);
        }
      })();
      document.getElementById('picked-table').style.display = '';
    }).catch(function(e){
      if (window.getCurrentRoute() !== route) return;
      document.getElementById('picked-loading').style.display = 'none';
      var el = document.getElementById('picked-empty');
      if (el) { el.textContent = 'Load failed: '+(e.message||String(e)); el.style.display='block'; }
    });
  }

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
        var p = pickedStatusPalette(r.status);
        return '<tr><td>'+(i+1)+'</td><td class="mono-cell">'+escapeHtml(r.sub_lt||r.tonbag_id||'-')+'</td><td class="mono-cell" style="text-align:right">'+(r.weight!=null?Number(r.weight).toLocaleString():'-')+'</td><td>'+escapeHtml(r.location||'-')+'</td><td><span class="tag" style="background:'+p.bg+';color:'+p.fg+';font-weight:700">'+escapeHtml(r.status||'-')+'</span></td><td>'+escapeHtml(r.picked_date||r.updated_at||'-')+'</td></tr>';
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

  window._pickedFilter = function() {
    var mode = window._pickedViewMode || 'lot';
    if (mode !== 'lot') return; // 그룹 모드에서는 필터 미적용
    var q  = ((document.getElementById('picked-q') ||{}).value||'').toLowerCase().trim();
    var df = (document.getElementById('picked-df')||{}).value||'';
    var dt = (document.getElementById('picked-dt')||{}).value||'';
    var tbody = document.getElementById('picked-tbody');
    var countEl = document.getElementById('picked-count');
    if (!tbody) return;
    var trs = tbody.querySelectorAll('tr');
    var vis = 0, total = 0;
    trs.forEach(function(row) {
      var txt = row.textContent.toLowerCase();
      var textOk = !q || txt.indexOf(q) !== -1;
      var cells = row.cells;
      var dateStr = cells && cells.length > 17 ? cells[17].textContent.trim() : '';
      var dMatch = dateStr.match(/(\d{4}-\d{2}-\d{2})/);
      var d = dMatch ? dMatch[1] : '';
      var dateOk = (!df || !d || d >= df) && (!dt || !d || d <= dt);
      var show = textOk && dateOk;
      row.style.display = show ? '' : 'none';
      total++; if (show) vis++;
    });
    if (countEl) countEl.textContent = vis + '/' + total + '건';
  };

  window._pickedFilterReset = function() {
    var el;
    el = document.getElementById('picked-q');  if (el) el.value = '';
    el = document.getElementById('picked-df'); if (el) el.value = '';
    el = document.getElementById('picked-dt'); if (el) el.value = '';
    el = document.getElementById('picked-count'); if (el) el.textContent = '';
    window._pickedFilter();
  };

  window.showPickedActionMenu = function(btn) {
    var lot = btn.dataset.lot || '';
    window._openContextMenu(btn, [
      { icon:'📋', label:'LOT 상세 보기',  kbd:'Enter',  fn:function(){ if(window.showLotDetail) window.showLotDetail(lot); } },
      { icon:'📄', label:'LOT 번호 복사',  kbd:'Ctrl+C', fn:function(){ navigator.clipboard&&navigator.clipboard.writeText(lot); showToast('info','LOT 복사: '+lot); } },
      '-',
      { icon:'▶',  label:'피킹 상세 열기', kbd:'Space',  color:'#f59e0b', fn:function(){ window.togglePickedDetail(lot); } },
      // v868 fix (2026-05-16): 취소 기능 추가 — PICKED → RESERVED 되돌리기
      '-',
      { icon:'↩',  label:'PICKED → RESERVED 되돌리기', color:'#ef4444', fn:async function(){
          if (!(await window.sqmConfirmAsync('↩ ' + lot + '\nPICKED → RESERVED로 되돌리시겠습니까?'))) return;
          if (window.allocRevertStep) {
            window.allocRevertStep('PICKED');
          } else {
            alert('되돌리기 함수를 찾을 수 없습니다 (allocRevertStep)');
          }
      } },
    ]);
  };
  window.loadPickedPage = loadPickedPage;
})();
