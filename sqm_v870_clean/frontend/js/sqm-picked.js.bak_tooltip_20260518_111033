/* SQM Inventory v8.6.6 — sqm-picked.js (Picked — 출고예정) */
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
        + '<span style="font-size:12px;color:var(--text-muted)">' + lots.length + ' LOT · ' + sumBags + ' Bags · ' + fmtN(sumKg) + ' kg</span>'
        + '<span style="font-size:11px;color:var(--text-muted);margin-left:auto">'
        + '<span style="color:#22c55e">A ' + sumAvail + '</span> · '
        + '<span style="color:#3b82f6">R ' + sumReserved + '</span> · '
        + '<span style="color:#f59e0b">P ' + sumPacked + '</span>'
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
      + '<th style="text-align:center">MXBG</th>'
      + '<th style="text-align:center">Available</th>'
      + '<th style="text-align:center">Reserved</th>'
      + '<th style="text-align:center">Packed</th>'
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
        + '<td class="mono-cell cell-left" style="color:var(--accent);font-weight:600">' + lot + '</td>'
        + '<td class="mono-cell">' + escapeHtml(r.picking_no || '') + '</td>'
        + '<td>' + escapeHtml(r.customer || r.picked_to || '') + '</td>'
        + '<td class="mono-cell" style="text-align:right">' + (r.tonbag_count || 0) + '</td>'
        + '<td class="mono-cell" style="text-align:right">' + (r.total_kg != null ? fmtN(r.total_kg) : '-') + '</td>'
        + '<td class="mono-cell" style="text-align:center">' + (r.mxbg_pallet != null ? r.mxbg_pallet : '-') + '</td>'
        + '<td class="mono-cell" style="text-align:center;color:#22c55e;font-weight:700">' + availBags + '</td>'
        + '<td class="mono-cell" style="text-align:center;color:#3b82f6;font-weight:700">' + reservedBags + '</td>'
        + '<td class="mono-cell" style="text-align:center;color:#f59e0b;font-weight:700">' + packedBags + '</td>'
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
        ? 'background:var(--accent,#3b82f6);color:#fff;border-color:var(--accent,#3b82f6);'
        : 'background:var(--surface,#1e293b);color:var(--text-muted);border-color:var(--border,#334155);';
      return '<button class="btn" style="font-size:12px;padding:4px 10px;' + act + '" '
        + 'onclick="window._pickedViewMode=\'' + val + '\';window.loadPickedPage()">' + label + '</button>';
    }
    c.innerHTML = [
      '<section class="page" data-page="picked">',
      '<div style="display:flex;align-items:center;gap:12px;padding:8px 0 12px;flex-wrap:wrap">',
      '  <h2 style="margin:0">🚛 Picked - 피킹 완료 (화물 결정)</h2>',
      '  <div style="display:flex;gap:4px;margin-left:8px">',
      '    ' + _pickedModeBtnHtml('lot', 'LOT별', pickedMode),
      '    ' + _pickedModeBtnHtml('customer', '고객사별', pickedMode),
      '    ' + _pickedModeBtnHtml('date', '입고일별', pickedMode),
      '  </div>',
      '  <div style="margin-left:auto;display:flex;gap:8px;align-items:center">',
      '    <button class="btn" onclick="window.allocRevertStep(\'PICKED\')" style="font-size:12px" title="PICKED 상태를 RESERVED로 되돌립니다">↩ PICKED &rarr; RESERVED</button>',
      '    <button class="btn btn-secondary" onclick="window.exportPickedExcel()" style="font-size:12px" title="현재 Picked 데이터를 Excel로 내보냅니다">📊 Excel 내보내기</button>',
      '    <button class="btn btn-secondary" onclick="renderPage(\'picked\')">🔁 새로고침</button>',
      '  </div>',
      '</div>',
      '<div id="picked-loading" style="padding:40px;text-align:center;color:var(--text-muted)">⏳ 데이터 로딩 중...</div>',
      '<div style="overflow-x:auto">',
      '  <table class="data-table" id="picked-table" style="display:none">',
      '  <thead><tr><th style="color:var(--text-muted);text-align:center;width:32px">#</th><th></th><th style="text-align:center">LOT No</th><th style="width:32px;text-align:center">+</th><th>피킹No</th><th>고객사</th><th>톤백수</th><th>중량(kg)</th><th>MXBG</th><th>Available</th><th>Reserved</th><th>Packed</th><th>Total Bags</th><th>Remain Bags</th><th>AV</th><th>VR</th><th>AR</th><th>Title Transfer Date</th></tr></thead>',
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
          '<td class="mono-cell" style="text-align:center">'+(r.mxbg_pallet!=null?r.mxbg_pallet:'-')+'</td>' +
          '<td class="mono-cell" style="text-align:center;color:#22c55e;font-weight:700">'+availBags+'</td>' +
          '<td class="mono-cell" style="text-align:center;color:#3b82f6;font-weight:700">'+reservedBags+'</td>' +
          '<td class="mono-cell" style="text-align:center;color:#f59e0b;font-weight:700">'+packedBags+'</td>' +
          '<td class="mono-cell" style="text-align:center">'+totalBags+'</td>' +
          '<td class="mono-cell" style="text-align:center;font-weight:700">'+remainBags+'</td>' +
          '<td class="mono-cell" style="text-align:right;color:#22c55e;font-weight:700">'+(availMt ? availMt.toFixed(3) : '0')+'</td>' +
          '<td class="mono-cell" style="text-align:right;color:#3b82f6;font-weight:700">'+(reservedMt ? reservedMt.toFixed(3) : '0')+'</td>' +
          '<td class="mono-cell" style="text-align:right;color:#f59e0b;font-weight:700">'+(pickedMt ? pickedMt.toFixed(3) : '0')+'</td>' +
          '<td class="mono-cell">'+escapeHtml(r.picking_date||'')+'</td>' +
          '</tr>';
      }).join('');
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

  window.showPickedActionMenu = function(btn) {
    var lot = btn.dataset.lot || '';
    window._openContextMenu(btn, [
      { icon:'📋', label:'LOT 상세 보기',  kbd:'Enter',  fn:function(){ if(window.showLotDetail) window.showLotDetail(lot); } },
      { icon:'📄', label:'LOT 번호 복사',  kbd:'Ctrl+C', fn:function(){ navigator.clipboard&&navigator.clipboard.writeText(lot); showToast('info','LOT 복사: '+lot); } },
      '-',
      { icon:'▶',  label:'피킹 상세 열기', kbd:'Space',  color:'#f59e0b', fn:function(){ window.togglePickedDetail(lot); } },
      // v868 fix (2026-05-16): 취소 기능 추가 — PICKED → RESERVED 되돌리기
      '-',
      { icon:'↩',  label:'PICKED → RESERVED 되돌리기', color:'#ef4444', fn:function(){
          if (!sqmConfirm('↩ ' + lot + '\nPICKED → RESERVED로 되돌리시겠습니까?')) return;
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
