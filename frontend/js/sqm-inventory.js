/* SQM Inventory v8.7.0 — sqm-inventory.js (Inventory — 재고목록·톤백모달) */
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
  var extractRows               = function() { return window.extractRows.apply(window, arguments); };
  var fmtN                      = function() { return window.fmtN.apply(window, arguments); };
  /* ──────────────────────────────────────────────────────────────── */

  function loadInventoryPage() {
    var route = window.getCurrentRoute();
    var c = document.getElementById('page-container');
    if (!c) return;
    c.innerHTML = '<div style="padding:40px;text-align:center">Loading inventory...</div>';
    apiGet('/api/inventory').then(function(res){
      if (window.getCurrentRoute() !== route) return;
      var rows = extractRows(res);
      if (!rows.length) {
        c.innerHTML = '<div class="empty" style="padding:60px;text-align:center">No inventory data</div>';
        return;
      }
      var sumBal = 0;
      var sumNet = 0;
      var sumIni = 0;
      var sumOb = 0;
      var sumUnsold = 0;
      var sumSold = 0;
      var sumAvailMt = 0;
      var sumRsvMt = 0;
      var sumPickedMt = 0;
      var sumAvailBags = 0;
      var sumReservedBags = 0;
      var sumPackedBags = 0;
      var sumTotalBags = 0;
      var sumRemainBags = 0;
      rows.forEach(function(r){
        var availBags = Number(r.tb_avail != null ? r.tb_avail : (r.avail_bags || 0)) || 0;
        var reservedBags = Number(r.tb_reserved || 0) || 0;
        var packedBags = Number(r.tb_picked || 0) || 0;
        var totalBags = Number(r.total_bags != null ? r.total_bags : (r.mxbg_pallet || 0)) || 0;
        var remainBags = Math.max(totalBags - availBags - reservedBags - packedBags, 0);
        sumAvailBags += availBags;
        sumReservedBags += reservedBags;
        sumPackedBags += packedBags;
        sumTotalBags += totalBags;
        sumRemainBags += remainBags;
        if (r.balance != null && !isNaN(Number(r.balance))) {
          var bal = Number(r.balance);
          sumBal += bal;
          var st = String(r.status || '').toUpperCase();
          if (st === 'SOLD' || st === 'SHIPPED' || st === 'CONFIRMED') sumSold += bal;
          else sumUnsold += bal;
        }
        if (r.net != null && !isNaN(Number(r.net))) sumNet += Number(r.net);
        if (r.initial_weight != null && !isNaN(Number(r.initial_weight))) sumIni += Number(r.initial_weight);
        if (r.outbound_weight != null && !isNaN(Number(r.outbound_weight))) sumOb += Number(r.outbound_weight);
        if (r.avail_mt != null && !isNaN(Number(r.avail_mt))) sumAvailMt += Number(r.avail_mt);
        if (r.reserved_mt != null && !isNaN(Number(r.reserved_mt))) sumRsvMt += Number(r.reserved_mt);
        if (r.picked_mt != null && !isNaN(Number(r.picked_mt))) sumPickedMt += Number(r.picked_mt);
      });
      var html = '<section class="page sqm-page-wrap" data-page="inventory">' +
        /* ── 페이지 헤더 (B형) ── */
        '<div class="sqm-page-hd">' +
        '<div class="sqm-page-hd-title">📦 재고 목록 <span style="font-size:12px;font-weight:400;color:var(--text-muted)">Inventory</span></div>' +
        '<span class="sqm-page-hd-count" id="inv-count-label">'+rows.length+' LOTs</span>' +
        '<div class="sqm-page-hd-actions">' +
        '<button class="btn btn-secondary" onclick="renderPage(\'inventory\')">🔁 새로고침</button>' +
        '</div>' +
        '</div>' +
        /* ── 요약 KPI 미니바 ── */
        '<div class="sqm-summary-bar">' +
        '<span class="sqm-summary-item"><span class="lbl">NET:</span><span class="val">'+fmtN(sumNet)+' MT</span></span>' +
        '<span class="sqm-summary-item"><span class="sep">|</span></span>' +
        '<span class="sqm-summary-item"><span class="lbl">Balance:</span><span class="val">'+fmtN(sumBal)+' MT</span></span>' +
        '<span class="sqm-summary-item"><span class="sep">|</span></span>' +
        '<span class="sqm-summary-item"><span class="lbl">미판매:</span><span class="val" style="color:#22c55e">'+fmtN(sumUnsold)+' MT</span></span>' +
        '<span class="sqm-summary-item"><span class="sep">|</span></span>' +
        '<span class="sqm-summary-item"><span class="lbl">판매완료:</span><span class="val" style="color:#ef4444">'+fmtN(sumSold)+' MT</span></span>' +
        '<span class="sqm-summary-item"><span class="sep">|</span></span>' +
        '<span class="sqm-summary-item"><span class="lbl">차이:</span><span class="val" style="color:#f59e0b">'+fmtN(sumNet - sumBal)+' MT</span></span>' +
        '</div>' +
        /* ── 필터 / 검색 바 (B형) ── */
        '<div class="sqm-filter-bar" id="inv-filter-bar">' +
        '<label>상태:</label>' +
        '<select id="inv-status-filter" onchange="window.invApplyFilter()">' +
        '  <option value="">전체</option>' +
        '  <option value="AVAILABLE">AVAILABLE</option>' +
        '  <option value="RESERVED">RESERVED</option>' +
        '  <option value="PICKED">PICKED</option>' +
        '  <option value="RETURN">RETURN</option>' +
        '</select>' +
        '<input id="inv-search-input" type="text" placeholder="LOT / SAP / BL / Product 검색..." oninput="window.invApplyFilter()">' +
        '<button class="btn btn-ghost" style="font-size:11px" onclick="window.invClearFilter()">✕ 초기화</button>' +
        '</div>' +
        /* ── B형 Wide 테이블 ── */
        '<div class="sqm-b-table-wrap"><table class="data-table sqm-b-table"><thead><tr>' +
        '<th>#</th><th style="text-align:center !important">LOT</th><th style="width:36px;text-align:center">+</th><th>SAP</th><th>BL</th><th>Product</th>' +
        '<th>Status</th><th>Balance(MT)</th><th>NET(MT)</th><th>Container</th>' +
        '<th title="총 톤백 개수 (MAXI BAG)">MXBG</th><th title="가용 톤백 수(개) — 바로 배분 가능한 톤백">Available</th><th title="예약 톤백 수(개) — 배정 잡힌 톤백">Reserved</th><th title="피킹/포장된 톤백 수(개)">Packed</th><th title="전체 톤백 수(개)">Total Bags</th><th title="남은 톤백 수 = 전체 − 가용 − 예약 − 피킹">Remain Bags</th><th title="가용 중량 AV (Available MT) — 아직 배정 안 된, 바로 배분 가능한 물량">AV</th><th title="예약 중량 VR (Reserved MT) — RESERVED 상태로 배정 잡힌 물량">VR</th><th title="피킹 중량 AR (Picked MT) — 출고 작업 중(PICKED)인 물량">AR</th><th>Invoice</th>' +
        '<th>Ship</th><th>Arrival</th><th>Con Return</th><th>Free</th>' +
        '<th>WH</th><th>Customs</th><th>Inbound(MT)</th><th>Outbound(MT)</th><th>Location</th><th></th>' +
        '</tr></thead><tbody>';
      html += rows.map(function(r, i){
        var lotKey = escapeHtml(r.lot||'');
        var parentContainer = escapeHtml(r.parent_container || r.container || '-');
        var hasSample = (r.sample_bags > 0);
        var availBags = Number(r.tb_avail != null ? r.tb_avail : (r.avail_bags || 0)) || 0;
        var reservedBags = Number(r.tb_reserved || 0) || 0;
        var packedBags = Number(r.tb_picked || 0) || 0;
        var totalBags = Number(r.total_bags != null ? r.total_bags : (r.mxbg_pallet || 0)) || 0;
        var remainBags = Math.max(totalBags - availBags - reservedBags - packedBags, 0);
        var sampleRow = '';
        if (hasSample) {
          sampleRow =
            '<tr style="background:rgba(234,179,8,0.08);border-left:3px solid #eab308">' +
            '<td class="mono-cell" style="color:#eab308;font-size:15px;text-align:center;padding:6px 10px;line-height:1.2">🔬</td>' +
            '<td class="mono-cell" style="color:#eab308;font-size:15px;font-weight:700;text-align:center;padding:6px 10px;line-height:1.2">'+lotKey+'(SP)</td>' +
            '<td class="mono-cell" style="color:#555">—</td>' +
            '<td class="mono-cell" style="color:#94a3b8;font-size:15px;padding:6px 10px;line-height:1.2">'+escapeHtml(r.sap||'')+'</td>' +
            '<td class="mono-cell" style="color:#94a3b8;font-size:15px;padding:6px 10px;line-height:1.2">'+escapeHtml(r.bl||'')+'</td>' +
            '<td><span class="tag" style="background:rgba(234,179,8,0.2);color:#eab308">'+escapeHtml(r.product||'')+'</span></td>' +
            '<td style="font-size:15px;color:#eab308;font-weight:600;padding:6px 10px;line-height:1.2">SP</td>' +
            '<td class="mono-cell" style="text-align:right;color:#eab308;font-weight:600;padding:6px 10px;line-height:1.2">'+fmtN(r.sample_weight_mt||0)+'</td>' +
            '<td class="mono-cell" style="text-align:right;color:#eab308;padding:6px 10px;line-height:1.2">'+fmtN(r.sample_weight_mt||0)+'</td>' +
            '<td class="mono-cell" style="font-size:15px;color:#94a3b8;padding:6px 10px;line-height:1.2">'+parentContainer+'</td>' +
            '<td class="mono-cell" style="text-align:center;color:#eab308;font-weight:700;padding:6px 10px;line-height:1.2">'+r.sample_bags+'</td>' +
            '<td class="mono-cell" style="text-align:center;color:#eab308;font-weight:700;padding:6px 10px;line-height:1.2">'+r.sample_bags+'</td>' +
            '<td class="mono-cell" style="text-align:center;color:#555">0</td>' +
            '<td class="mono-cell" style="text-align:center;color:#555">0</td>' +
            '<td class="mono-cell" style="text-align:center;color:#eab308;font-weight:700">'+r.sample_bags+'</td>' +
            '<td class="mono-cell" style="text-align:center;color:#555">0</td>' +
            '<td class="mono-cell" style="text-align:right;color:#eab308">'+fmtN(r.sample_weight_mt||0)+'</td>' +
            '<td class="mono-cell" style="text-align:right;color:#555">0</td>' +
            '<td class="mono-cell" style="text-align:right;color:#555">0</td>' +
            '<td class="mono-cell" style="font-size:15px;color:#94a3b8;padding:6px 10px;line-height:1.2">'+escapeHtml(r.invoice_no||'')+'</td>' +
            '<td class="mono-cell" style="font-size:15px;color:#94a3b8;padding:6px 10px;line-height:1.2">'+escapeHtml((r.ship_date||'').slice(0,10))+'</td>' +
            '<td class="mono-cell" style="font-size:15px;color:#94a3b8;padding:6px 10px;line-height:1.2">'+escapeHtml((r.arrival_date||'').slice(0,10))+'</td>' +
            '<td class="mono-cell" style="color:#555">—</td>' +
            '<td class="mono-cell" style="color:#555">—</td>' +
            '<td class="mono-cell" style="font-size:15px;color:#94a3b8;padding:6px 10px;line-height:1.2">'+escapeHtml(r.wh||'')+'</td>' +
            '<td class="mono-cell" style="color:#555">—</td>' +
            '<td class="mono-cell" style="color:#555">—</td>' +
            '<td class="mono-cell" style="color:#555">—</td>' +
            '<td><span class="tag" style="background:rgba(234,179,8,0.1);color:#94a3b8">'+escapeHtml(r.location||'-')+'</span></td>' +
            '<td></td>' +
            '</tr>';
        }
        var rawStatus = String(r.status || '').toUpperCase();
        var statusLabel = rawStatus || '-';
        var statusBadgeBg = (rawStatus === 'AVAILABLE') ? 'rgba(34,197,94,0.18)'
          : (rawStatus === 'RESERVED') ? 'rgba(245,158,11,0.22)'
          : (rawStatus === 'PICKED') ? 'rgba(59,130,246,0.22)'
          : (rawStatus === 'SOLD' || rawStatus === 'SHIPPED' || rawStatus === 'CONFIRMED') ? 'rgba(239,68,68,0.2)'
          : (rawStatus === 'RETURN' || rawStatus === 'RETURNED') ? 'rgba(168,85,247,0.2)'
          : 'rgba(148,163,184,0.2)';
        var statusBadgeColor = (rawStatus === 'AVAILABLE') ? '#22c55e'
          : (rawStatus === 'RESERVED') ? '#f59e0b'
          : (rawStatus === 'PICKED') ? '#3b82f6'
          : (rawStatus === 'SOLD' || rawStatus === 'SHIPPED' || rawStatus === 'CONFIRMED') ? '#ef4444'
          : (rawStatus === 'RETURN' || rawStatus === 'RETURNED') ? '#a855f7'
          : '#94a3b8';

        var mainRow =
          '<tr style="'+(hasSample ? 'border-left:3px solid #3b82f6' : '')+'">' +
          '<td class="mono-cell" style="color:var(--text-muted)">'+(i+1)+'</td>' +
          '<td class="mono-cell" style="color:var(--accent);font-weight:600;padding:6px 10px;line-height:1.2">'+lotKey+'</td>' +
          '<td style="text-align:center;padding:3px 4px;width:32px">'+'<button class="btn btn-ghost btn-xs" data-lot="'+lotKey+'" onclick="window.showInvActionMenu(this)"'+'  style="font-size:15px;padding:0 4px;letter-spacing:1px;line-height:1.2" title="추가기능">⋯</button>'+'</td>' +
          '<td class="mono-cell">'+escapeHtml(r.sap||'')+'</td>' +
          '<td class="mono-cell">'+escapeHtml(r.bl||'')+'</td>' +
          '<td><span class="tag">'+escapeHtml(r.product||'')+'</span></td>' +
          '<td><span class="tag" style="background:'+statusBadgeBg+';color:'+statusBadgeColor+';font-weight:700">'+escapeHtml(statusLabel)+'</span></td>' +
          '<td class="mono-cell" style="text-align:right">'+(r.balance!=null?fmtN(r.balance):'-')+'</td>' +
          '<td class="mono-cell" style="text-align:right">'+(r.net!=null?fmtN(r.net):'-')+'</td>' +
          '<td class="mono-cell">'+parentContainer+'</td>' +
          '<td title="총 톤백 개수 (MAXI BAG)" class="mono-cell" style="text-align:center;padding:6px 10px;line-height:1.2">' +
          (r.mxbg_pallet > 0
            ? '<button class="btn btn-ghost btn-xs" style="font-weight:700;color:var(--accent);padding:0 4px;line-height:1.1;min-height:18px" '
            + 'onclick="window.showTonbagModal(\'' + lotKey + '\')" title="톤백 세부 보기">'
            + r.mxbg_pallet + '</button>'
            : '-') +
          '</td>' +
          '<td title="가용 톤백 수(개) — 바로 배분 가능한 톤백" class="mono-cell" style="text-align:center;color:#22c55e;font-weight:700">'+availBags+'</td>' +
          '<td title="예약 톤백 수(개) — 배정 잡힌 톤백" class="mono-cell" style="text-align:center;color:#3b82f6;font-weight:700">'+reservedBags+'</td>' +
          '<td title="피킹/포장된 톤백 수(개)" class="mono-cell" style="text-align:center;color:#f59e0b;font-weight:700">'+packedBags+'</td>' +
          '<td title="전체 톤백 수(개)" class="mono-cell" style="text-align:center">'+totalBags+'</td>' +
          '<td title="남은 톤백 수 = 전체 − 가용 − 예약 − 피킹" class="mono-cell" style="text-align:center;font-weight:700">'+remainBags+'</td>' +
          '<td title="가용 중량 AV (Available MT) — 아직 배정 안 된, 바로 배분 가능한 물량" class="mono-cell" style="text-align:right;color:#22c55e;font-weight:700">'+(r.avail_mt!=null?fmtN(r.avail_mt):'-')+'</td>' +
          '<td title="예약 중량 VR (Reserved MT) — RESERVED 상태로 배정 잡힌 물량" class="mono-cell" style="text-align:right;color:#3b82f6;font-weight:700">'+(r.reserved_mt!=null?fmtN(r.reserved_mt):'-')+'</td>' +
          '<td title="피킹 중량 AR (Picked MT) — 출고 작업 중(PICKED)인 물량" class="mono-cell" style="text-align:right;color:#f59e0b;font-weight:700">'+(r.picked_mt!=null?fmtN(r.picked_mt):'-')+'</td>' +
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
'<td></td>' +
          '</tr>';
        return sampleRow + mainRow;
      }).join('');
      html += '</tbody><tfoot><tr style="background:#FFD600;font-weight:800;color:#222">';
      html += '<td colspan="7" style="text-align:right;padding:8px 10px">합계 ('+rows.length+' LOT) · 미판매 '+fmtN(sumUnsold)+' / <span style="color:#ef4444;font-weight:700">판매완료 '+fmtN(sumSold)+'</span></td>';
      html += '<td class="mono-cell" style="text-align:right">'+fmtN(sumBal)+'</td>';
      html += '<td class="mono-cell" style="text-align:right">'+fmtN(sumNet)+'</td>';
      html += '<td colspan="2"></td>';
      html += '<td class="mono-cell" style="text-align:center;color:#22c55e">'+sumAvailBags+'</td>';
      html += '<td class="mono-cell" style="text-align:center;color:#3b82f6">'+sumReservedBags+'</td>';
      html += '<td class="mono-cell" style="text-align:center;color:#f59e0b">'+sumPackedBags+'</td>';
      html += '<td class="mono-cell" style="text-align:center">'+sumTotalBags+'</td>';
      html += '<td class="mono-cell" style="text-align:center">'+sumRemainBags+'</td>';
      html += '<td class="mono-cell" style="text-align:right;color:#22c55e">'+fmtN(sumAvailMt)+'</td>';
      html += '<td class="mono-cell" style="text-align:right;color:#3b82f6">'+fmtN(sumRsvMt)+'</td>';
      html += '<td class="mono-cell" style="text-align:right;color:#f59e0b">'+fmtN(sumPickedMt)+'</td>';
      html += '<td colspan="7"></td>';
      html += '<td class="mono-cell" style="text-align:right">'+fmtN(sumIni)+'</td>';
      html += '<td class="mono-cell" style="text-align:right">'+fmtN(sumOb)+'</td>';
      html += '<td colspan="2"></td>';
      html += '</tr></tfoot></table></div></section>'; /* sqm-b-table-wrap 닫힘 */
      c.innerHTML = html;
    }).catch(function(e){
      if (window.getCurrentRoute() !== route) return;
      c.innerHTML = '<div class="empty" style="padding:40px;text-align:center">Load failed: '+escapeHtml(e.message||String(e))+'</div>';
      showToast('error', 'Inventory load failed: ' + (e&&e.message||String(e)));
    });
  }

  /* ── Inventory 탭 필터/검색 핸들러 ─────────────────────────────── */
  var _invAllRows = [];  // 전체 행 캐시 (필터용)

  window.invApplyFilter = function() {
    var statusEl = document.getElementById('inv-status-filter');
    var searchEl = document.getElementById('inv-search-input');
    var statusVal = statusEl ? statusEl.value : '';
    var searchVal = searchEl ? searchEl.value.trim().toLowerCase() : '';
    var tbody = document.querySelector('[data-page="inventory"] tbody');
    var tfoot = document.querySelector('[data-page="inventory"] tfoot');
    if (!tbody) return;

    var rows = Array.from(tbody.querySelectorAll('tr'));
    var visible = 0;
    rows.forEach(function(tr) {
      var cells = tr.querySelectorAll('td');
      if (!cells.length) return;
      var lot    = (cells[1] ? cells[1].textContent : '').toLowerCase();
      var sap    = (cells[3] ? cells[3].textContent : '').toLowerCase();
      var bl     = (cells[4] ? cells[4].textContent : '').toLowerCase();
      var prod   = (cells[5] ? cells[5].textContent : '').toLowerCase();
      var status = (cells[6] ? cells[6].textContent.trim() : '').toUpperCase();

      var matchStatus = !statusVal || status === statusVal;
      var matchSearch = !searchVal ||
        lot.includes(searchVal) || sap.includes(searchVal) ||
        bl.includes(searchVal)  || prod.includes(searchVal);

      if (matchStatus && matchSearch) {
        tr.style.display = '';
        visible++;
      } else {
        tr.style.display = 'none';
      }
    });
    var countEl = document.getElementById('inv-count-label');
    if (countEl) countEl.textContent = visible + ' / ' + rows.length + ' LOTs';
  };

  window.invClearFilter = function() {
    var statusEl = document.getElementById('inv-status-filter');
    var searchEl = document.getElementById('inv-search-input');
    if (statusEl) statusEl.value = '';
    if (searchEl) searchEl.value = '';
    window.invApplyFilter();
  };

  /* ─── 추가기능 드롭다운 (공용 _openContextMenu 사용) ──────────────── */
  window.showInvActionMenu = function(btn) {
    var lot = btn.dataset.lot || '';
    window._openContextMenu(btn, [
      { icon:'📋', label:'LOT 상세 보기',  kbd:'Enter',   fn:function(){ window.showLotDetail(lot); } },
      { icon:'📄', label:'LOT 번호 복사',  kbd:'Ctrl+C',  fn:function(){ window.invCopyLot(lot); } },
      { icon:'📑', label:'행 전체 복사',   kbd:'Ctrl+Shift+C', fn:function(){ var tr = document.querySelector('tr[data-lot="'+lot+'"]') || (document.querySelector('[data-lot="'+lot+'"]') && document.querySelector('[data-lot="'+lot+'"]').closest('tr')); if (window.invCopyRow && tr) window.invCopyRow({closest:function(){ return tr; }}); else window.invCopyLot(lot); } },
      '-',
      { icon:'🚀', label:'즉시 출고 진입', kbd:'O',       color:'#42a5f5', fn:function(){ window.invQuickOutbound(lot); } },
      { icon:'🔄', label:'반품 진입',      kbd:'R',       color:'#ef5350', fn:function(){ window.invQuickReturn(lot); } },
      { icon:'📊', label:'LOT 이력 보기', kbd:'H',       color:'#66bb6a', fn:function(){ window.invShowLotHistory(lot); } },
      '-',
      { icon:'↩️', label:'PENDING으로 되돌리기', color:'#f59e0b', fn:function(){ window.revertToPending(lot); } },
    ]);
  };

  if (!window.revertToPending) window.revertToPending = function(lot) {
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
    desc.style.cssText = 'margin:0 0 16px;font-size:13px;color:var(--text-muted);white-space:pre-line';
    var strong = document.createElement('strong');
    strong.style.cssText = 'color:var(--text);font-family:monospace';
    strong.textContent = lot;
    desc.appendChild(document.createTextNode('입고 취소: '));
    desc.appendChild(strong);
    desc.appendChild(document.createTextNode(' → PENDING 복구. inbound_date 초기화 / RESERVED·PICKED·SOLD 톤백 없어야 합니다.'));
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
      apiPost('/api/inbound/revert/' + encodeURIComponent(l), {})
        .then(function() {
          showToast('success', '↩️ ' + l + ' → PENDING 복구 완료');
          if (window.loadAvailablePage) window.loadAvailablePage();
        })
        .catch(function(e) { showToast('error', '실패: ' + (e.message || e)); });
    };
    btnRow.appendChild(cancelBtn);
    btnRow.appendChild(confirmBtn);
    box.appendChild(h3);
    box.appendChild(desc);
    box.appendChild(btnRow);
    ov.appendChild(box);
    document.body.appendChild(ov);
    cancelBtn.focus();
  };

  window.invCopyLot = function(lot) {
    if (!lot) return;
    if (navigator.clipboard) {
      navigator.clipboard.writeText(lot).then(function(){
        showToast('success', '📋 LOT 번호 복사됨: ' + lot);
      }).catch(function(){ prompt('수동 복사:', lot); });
    } else {
      prompt('수동 복사:', lot);
    }
  };

  window.invCopyRow = function(btn) {
    var tr = btn ? btn.closest('tr') : null;
    if (!tr) return;
    var cells = Array.from(tr.querySelectorAll('td'));
    var text = cells.slice(0, cells.length - 1).map(function(td){ return td.textContent.trim(); }).join('\t');
    if (navigator.clipboard) {
      navigator.clipboard.writeText(text).then(function(){
        showToast('success', '📑 행 복사됨');
      }).catch(function(){ prompt('수동 복사:', text); });
    } else {
      prompt('수동 복사:', text);
    }
  };

  window.invQuickOutbound = function(lot) {
    if (!lot) return;
    renderPage('outbound');
    showToast('info', '🚀 출고 탭으로 이동: ' + lot);
  };

  window.invQuickReturn = function(lot) {
    if (!lot) return;
    renderPage('return');
    showToast('info', '🔄 반품 탭으로 이동: ' + lot);
  };

  /* ── 톤백 세부 모달 ─────────────────────────────── */
  window.showTonbagModal = function(lotNo) {
    if (!lotNo) return;
    var modal = document.getElementById('tonbag-modal');
    if (!modal) {
      modal = document.createElement('div');
      modal.id = 'tonbag-modal';
      modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.7);z-index:9999;display:flex;align-items:center;justify-content:center';
      modal.innerHTML =
        '<div style="background:var(--card-bg,#1e293b);border:1px solid var(--border,#334155);border-radius:12px;'
        + 'width:min(900px,95vw);max-height:85vh;display:flex;flex-direction:column;padding:20px;gap:12px">'
        + '<div style="display:flex;align-items:center;justify-content:space-between">'
        + '<h3 id="tbm-title" style="margin:0;font-size:16px;font-weight:700">톤백 세부</h3>'
        + '<div style="display:flex;gap:8px;align-items:center">'
        + '<select id="tbm-filter" onchange="window._filterTonbagModal()" '
        + 'style="background:var(--input-bg,#0f172a);border:1px solid var(--border,#334155);border-radius:6px;padding:4px 8px;color:inherit;font-size:13px">'
        + '<option value="">전체 상태</option>'
        + '<option value="AVAILABLE">AVAILABLE</option>'
        + '<option value="RESERVED">RESERVED</option>'
        + '<option value="PICKED">PICKED</option>'
        + '<option value="RETURN">RETURN</option>'
        + '<option value="SOLD">SOLD</option>'
        + '</select>'
        + '<button onclick="document.getElementById(\'tonbag-modal\').remove()" '
        + 'style="background:none;border:none;color:var(--text-muted,#94a3b8);font-size:20px;cursor:pointer;line-height:1">✕</button>'
        + '</div></div>'
        + '<div style="overflow:auto;flex:1">'
        + '<table id="tbm-table" style="width:100%;border-collapse:collapse;font-size:13px">'
        + '<thead><tr style="background:var(--table-header,#0f172a);position:sticky;top:0">'
        + '<th style="padding:8px;text-align:right;white-space:nowrap">#</th>'
        + '<th style="padding:8px;text-align:left;white-space:nowrap">Sub-LT</th>'
        + '<th style="padding:8px;text-align:right;white-space:nowrap">무게(MT)</th>'
        + '<th style="padding:8px;text-align:center;white-space:nowrap">상태</th>'
        + '<th style="padding:8px;text-align:center;white-space:nowrap">구분</th>'
        + '<th style="padding:8px;text-align:left;white-space:nowrap">위치</th>'
        + '<th style="padding:8px;text-align:left;white-space:nowrap">컨테이너</th>'
        + '<th style="padding:8px;text-align:left;white-space:nowrap">입고일</th>'
        + '</tr></thead>'
        + '<tbody id="tbm-body"></tbody>'
        + '</table></div>'
        + '<div id="tbm-summary" style="font-size:12px;color:var(--text-muted,#94a3b8);text-align:right"></div>'
        + '</div>';
      document.body.appendChild(modal);
      modal.addEventListener('click', function(e){ if (e.target === modal) modal.remove(); });
    }
    var titleEl2 = document.getElementById('tbm-title'); if (titleEl2) titleEl2.textContent = '톤백 세부 — LOT ' + lotNo;
    var filterEl2 = document.getElementById('tbm-filter'); if (filterEl2) filterEl2.value = '';
    var bodyEl2 = document.getElementById('tbm-body'); if (bodyEl2) bodyEl2.innerHTML = '<tr><td colspan="8" style="text-align:center;padding:20px;color:#94a3b8">로딩 중...</td></tr>';
    var summaryEl2 = document.getElementById('tbm-summary'); if (summaryEl2) summaryEl2.textContent = '';
    modal.style.display = 'flex';
    modal._allRows = [];
    apiGet('/api/tonbags?lot_no=' + encodeURIComponent(lotNo) + '&limit=500')
      .then(function(res){
        var rows = Array.isArray(res) ? res : (res.data || res.items || []);
        modal._allRows = rows;
        window._filterTonbagModal();
      })
      .catch(function(e){ var body = document.getElementById('tbm-body'); if (body) body.innerHTML = '<tr><td colspan="8" style="text-align:center;padding:20px;color:#ef4444">로드 실패: ' + (window.escapeHtml ? window.escapeHtml(e&&e.message||String(e)) : (e&&e.message||String(e))) + '</td></tr>'; });
  };

  window._filterTonbagModal = function() {
    var modal = document.getElementById('tonbag-modal');
    if (!modal || !modal._allRows) return;
    var filterEl = document.getElementById('tbm-filter');
    var filter = filterEl ? filterEl.value : '';
    var rows = filter ? modal._allRows.filter(function(r){ return r.status === filter; }) : modal._allRows;
    var STATUS_COLOR = {
      AVAILABLE:'#22c55e', RESERVED:'#f59e0b', PICKED:'#3b82f6',
      RETURN:'#a855f7', SOLD:'#ef4444'
    };
    var html = '';
    rows.forEach(function(r, i){
      var isSample = r.is_sample == 1 || r.is_sample === true;
      var rowBg = isSample ? 'background:rgba(234,179,8,0.10)' : '';
      var sc = STATUS_COLOR[r.status] || '#94a3b8';
      html += '<tr style="border-bottom:1px solid var(--border,#334155);' + rowBg + '">'
        + '<td style="padding:6px 8px;text-align:right;color:#94a3b8">' + (i+1) + '</td>'
        + '<td style="padding:6px 8px;font-family:monospace">' + escapeHtml(r.sub_lt || r.tonbag_no || '') + '</td>'
        + '<td style="padding:6px 8px;text-align:right">' + ((r.weight != null && r.weight !== '') ? Number(r.weight).toFixed(3) : '-') + '</td>'
        + '<td style="padding:6px 8px;text-align:center"><span style="color:' + sc + ';font-weight:700">' + escapeHtml(r.status||'') + '</span></td>'
        + '<td style="padding:6px 8px;text-align:center">' + (isSample ? 'SP' : '📦 일반') + '</td>'
        + '<td style="padding:6px 8px;text-align:center">' + escapeHtml(r.location || '-') + '</td>'
        + '<td style="padding:6px 8px;font-family:monospace">' + escapeHtml(r.container || '-') + '</td>'
        + '<td style="padding:6px 8px;text-align:center">' + escapeHtml((r.inbound_date || '').slice(0,10)) + '</td>'
        + '</tr>';
    });
    var tbmBody = document.getElementById('tbm-body');
    if (tbmBody) tbmBody.innerHTML = html ||
      '<tr><td colspan="8" style="text-align:center;padding:20px;color:#94a3b8">데이터 없음</td></tr>';
    var totalMt = rows.reduce(function(s,r){ return s + (parseFloat(r.weight)||0); }, 0);
    var sampleCnt = rows.filter(function(r){ return r.is_sample==1||r.is_sample===true; }).length;
    var tbmSummary = document.getElementById('tbm-summary');
    if (tbmSummary) tbmSummary.textContent =
      '표시 ' + rows.length + '개 / 합계 ' + totalMt.toFixed(3) + ' MT'
      + (sampleCnt > 0 ? ' (SP ' + sampleCnt + '개 포함)' : '');
  };

  window.invShowLotHistory = function(lot) {
    if (!lot) return;
    apiGet('/api/action/lot-detail?lot_no=' + encodeURIComponent(lot)).then(function(res){
      var d = res && res.data ? res.data : res;
      var history = (d.history || d.audit_log || []);
      var lines = history.map(function(h){
        return '[' + (h.created_at||h.action_time||'').slice(0,16) + '] ' + (h.action||'') + ' — ' + (h.note||h.detail||'');
      });
      var msg = lines.length ? lines.join('\n') : '이력 없음';
      window.sqmAlert(msg, { title: '📊 LOT 이력: ' + lot, pre: true });
    }).catch(function(e){
      showToast('error', 'LOT 이력 조회 실패: ' + (e.message||e));
    });
  };



  /* ===================================================
     PENDING 입고 대기 목록 (참고용 — 재고 집계 제외)
     =================================================== */
  window._pendingViewMode = window._pendingViewMode || 'date';

  function _pendingModeBtn(val, label, current) {
    var active = val === current
      ? 'background:var(--accent,#3b82f6);color:#fff;border:1px solid var(--accent,#3b82f6);border-radius:4px;'
      : 'background:var(--surface,#1e293b);color:var(--text-muted);border:1px solid var(--border,#334155);border-radius:4px;';
    return '<button class="btn" style="font-size:12px;padding:3px 10px;cursor:pointer;' + active + '" '
      + 'onclick="window._pendingViewMode=\'' + val + '\';window.loadPendingPage()">' + label + '</button>';
  }

  function _pendingToday() {
    return new Date().toISOString().slice(0, 10);
  }

  function _pendingGroupId(prefix, idx) {
    return prefix + '-' + idx;
  }

  function _pendingGroupLotsAttr(lots) {
    return escapeHtml(JSON.stringify(lots.filter(Boolean)));
  }

  function _renderPendingLotRows(rows) {
    var html = '<div style="overflow-x:auto"><table class="data-table"><thead><tr>'
      + '<th style="width:28px;text-align:center"><input type="checkbox" id="pending-select-all" onchange="window.pendingToggleAll(this)" title="전체 선택"></th>'
      + '<th>#</th><th style="text-align:center">LOT</th><th style="width:36px;text-align:center">⋯</th>'
      + '<th>SAP</th><th>BL</th><th>Product</th>'
      + '<th>Container</th><th>Vessel</th><th>MXBG</th><th>NET(MT)</th>'
      + '<th>Status</th><th style="text-align:center;color:#22c55e" title="입고 확정 → AVAILABLE">✅</th>'
      + '<th title="선박/항구 도착일 (파싱 원본)">⚓ 입항일</th>'
      + '<th title="실제 창고 반입 예정일 (클릭하여 편집)">🏭 실제 입고일</th>'
      + '<th>WH</th>'
      + '</tr></thead><tbody id="pend-lot-tbody">';
    html += rows.map(function(r, i) {
      var lotSafe = escapeHtml(r.lot_no || '');
      var netMt = r.net_weight != null ? fmtN(r.net_weight / 1000) : '-';
      var ibDate = (r.inbound_date || '').slice(0, 10);
      return '<tr>'
        + '<td style="text-align:center;padding:3px 6px"><input type="checkbox" class="pending-cb" data-lot="' + lotSafe + '"></td>'
        + '<td class="mono-cell" style="color:var(--text-muted)">' + (i+1) + '</td>'
        + '<td class="mono-cell cell-left" style="color:#94a3b8;font-weight:600;padding:6px 10px">' + lotSafe + '</td>'
        + '<td style="text-align:center;padding:3px 4px;width:32px"><button class="btn btn-ghost btn-xs" style="font-size:15px;padding:0 4px;letter-spacing:1px" title="추가기능" '
        + 'onclick="window.showPendingActionMenu(event,\'' + lotSafe + '\')">\u29bf</button></td>'
        + '<td class="mono-cell">' + escapeHtml(r.sap_no || '-') + '</td>'
        + '<td class="mono-cell">' + escapeHtml(r.bl_no || '-') + '</td>'
        + '<td><span class="tag">' + escapeHtml(r.product || '-') + '</span></td>'
        + '<td class="mono-cell">' + escapeHtml(r.container_no || '-') + '</td>'
        + '<td class="mono-cell">' + escapeHtml(r.vessel || '-') + '</td>'
        + '<td class="mono-cell" style="text-align:center">' + (r.mxbg_pallet != null ? r.mxbg_pallet : '-') + '</td>'
        + '<td class="mono-cell" style="text-align:right">' + netMt + '</td>'
        + '<td><span class="tag" style="background:rgba(148,163,184,0.15);color:#94a3b8">\u23f3 PENDING</span></td>'
        + '<td style="text-align:center;padding:2px 4px"><button class="btn btn-ghost btn-xs" style="color:#22c55e;font-size:13px;padding:1px 5px;border:1px solid #22c55e55" '
        + 'onclick="window.showPendingConfirmModal(\'' + lotSafe + '\')" title="입고 확정 → AVAILABLE">\u2705</button></td>'
        + '<td class="mono-cell" style="color:#94a3b8">' + escapeHtml((r.arrival_date || '-').slice(0, 10)) + '</td>'
        + '<td class="mono-cell" style="padding:2px 4px">'
          + '<button class="btn btn-ghost btn-xs" style="font-size:12px;padding:2px 8px;width:100%;text-align:left;'
          + (ibDate ? 'color:#22c55e;font-weight:600' : 'color:var(--text-muted)') + '" '
          + 'onclick="window.pendingEditInboundDate(this,\'' + lotSafe + '\',\'' + ibDate + '\')" '
          + 'title="실제 입고일 편집 (클릭)">' + (ibDate || '\ud83d\udcc5 미지정') + '</button>'
        + '</td>'
        + '<td class="mono-cell">' + escapeHtml(r.warehouse || '-') + '</td>'
        + '</tr>';
    }).join('');
    return html + '</tbody></table></div>';
  }

  function _renderPendingGroupRows(rows, opts) {
    var groups = {};
    rows.forEach(function(r) {
      var key = opts.key(r);
      if (!groups[key]) groups[key] = [];
      groups[key].push(r);
    });

    var keys = Object.keys(groups).sort(function(a, b) {
      if (a.indexOf('미지정') >= 0) return 1;
      if (b.indexOf('미지정') >= 0) return -1;
      return a.localeCompare(b);
    });
    var today = _pendingToday();
    var html = '';

    keys.forEach(function(key, idx) {
      var lots = groups[key];
      var lotNos = lots.map(function(r){ return r.lot_no; });
      var groupId = _pendingGroupId(opts.prefix, idx);
      var inputId = 'date-' + groupId;
      var _arrivals = Array.from(new Set(lots.map(function(r){ return r.arrival_date; }).filter(Boolean))).sort();
      var arrivalRef = _arrivals.length ? _arrivals.slice(0, 3).join(', ') : '-';
      var summary = opts.summary ? opts.summary(key, lots) : '';

      html += '<div data-pend-grp="1" style="margin-bottom:12px;border:1px solid var(--border,#334155);border-radius:8px;overflow:hidden">'
        + '<div style="display:flex;align-items:center;gap:10px;padding:10px 14px;background:var(--surface,#1e293b);cursor:pointer;flex-wrap:wrap" '
        + 'onclick="window._togglePendingGroup(\'' + groupId + '\')">'
        + '<strong style="color:var(--text);font-family:monospace">' + escapeHtml(key) + '</strong>'
        + '<span style="font-size:12px;color:var(--text-muted)">' + lots.length + ' LOT</span>'
        + (summary ? '<span style="font-size:11px;color:var(--text-muted)">' + escapeHtml(summary) + '</span>' : '')
        + '<span style="font-size:11px;color:var(--text-muted);margin-left:auto;white-space:nowrap">📅 도착일: <strong style="color:var(--text)">' + escapeHtml(arrivalRef) + '</strong></span>'
        + '<span style="font-size:12px;color:var(--text-muted);white-space:nowrap">🏭 입고확정일:</span>'
        + '<input type="date" id="' + inputId + '" value="" max="' + today + '" '
        + 'style="padding:4px 8px;background:var(--bg,#0f172a);border:1px solid var(--accent,#3b82f6);border-radius:4px;color:var(--text);font-size:12px" '
        + 'onclick="event.stopPropagation()">'
        + '<button class="btn" style="background:#22c55e;color:#fff;font-size:12px;padding:4px 10px;white-space:nowrap" '
        + 'data-lots="' + _pendingGroupLotsAttr(lotNos) + '" data-date-input="' + inputId + '" '
        + 'onclick="event.stopPropagation();window.confirmPendingGroupFromButton(this)">✅ 전체 확정</button>'
        + '</div>'
        + '<div id="' + groupId + '" style="display:none">'
        + '<table class="data-table" style="margin:0"><thead><tr>'
        + '<th style="color:var(--text-muted);text-align:center;width:36px">#</th><th>LOT</th><th>Product</th><th>Qty</th><th>BL No</th><th>Container</th><th>Vessel</th><th>Arrival</th><th title="실제 창고 반입 예정일 (클릭하여 편집)">🏭 입고일</th><th style="width:50px">⚙️</th>'
        + '</tr></thead><tbody>';

      lots.forEach(function(r, _i) {
        html += '<tr style="background:rgba(148,163,184,0.04)">'
          + '<td class="mono-cell" style="color:var(--text-muted);text-align:center">' + (_i+1) + '</td>'
          + '<td class="mono-cell" style="color:#94a3b8;font-weight:600">' + escapeHtml(r.lot_no||'') + '</td>'
          + '<td><span class="tag">' + escapeHtml(r.product||'-') + '</span></td>'
          + '<td class="mono-cell" style="text-align:right">' + (r.quantity!=null?fmtN(r.quantity):(r.net_weight!=null?fmtN(r.net_weight):'-')) + '</td>'
          + '<td class="mono-cell">' + escapeHtml(r.bl_no||'-') + '</td>'
          + '<td class="mono-cell">' + escapeHtml(r.container_no||'-') + '</td>'
          + '<td class="mono-cell">' + escapeHtml(r.vessel||'-') + '</td>'
          + '<td class="mono-cell">' + escapeHtml(r.arrival_date||'-') + '</td>'
          + '<td class="mono-cell" style="padding:2px 4px">'
          + '<button class="btn btn-ghost btn-xs" style="font-size:12px;padding:2px 8px;width:100%;text-align:left;'
          + ((r.inbound_date||'').slice(0,10) ? 'color:#22c55e;font-weight:600' : 'color:var(--text-muted)') + '" '
          + 'onclick="window.pendingEditInboundDate(this,\'' + escapeHtml(r.lot_no||'') + '\',\'' + escapeHtml((r.inbound_date||'').slice(0,10)) + '\')" '
          + 'title="실제 입고일 편집 (클릭)">' + ((r.inbound_date||'').slice(0,10) || '📅 미지정') + '</button>'
          + '</td>'
          + '<td style="text-align:center"><button class="btn btn-ghost" style="padding:1px 8px;font-size:12px" '
          + 'onclick="window.showPendingActionMenu(event,\'' + escapeHtml(r.lot_no||'') + '\')">⋯</button></td>'
          + '</tr>';
      });

      html += '</tbody></table></div></div>';
    });

    return html;
  }

  function _renderPendingByContainer(rows) {
    return _renderPendingGroupRows(rows, {
      prefix: 'pc',
      key: function(r) { return r.container_no || '(컨테이너 미지정)'; },
      summary: function(key, lots) {
        var arrivals = Array.from(new Set(lots.map(function(r){ return r.arrival_date || '-'; }))).slice(0, 3);
        return '도착 ' + arrivals.join(', ');
      }
    });
  }

  function _renderPendingByDate(rows) {
    return _renderPendingGroupRows(rows, {
      prefix: 'pd',
      key: function(r) { return r.arrival_date || '(날짜 미지정)'; },
      defaultDate: function(key, lots, today) {
        return /^\d{4}-\d{2}-\d{2}$/.test(key) && key <= today ? key : today;
      },
      summary: function(key, lots) {
        return Array.from(new Set(lots.map(function(r){ return r.container_no || '?'; }))).slice(0, 5).join(', ');
      }
    });
  }

  function loadPendingPage() {
    var route = 'pending';
    if (window.getCurrentRoute() !== route) return;
    var c = document.getElementById('page-container');
    if (!c) return;
    c.innerHTML = '<div style="padding:40px;text-align:center;color:var(--text-muted)">⏳ Pending 로딩 중...</div>';

    apiGet('/api/inbound/pending').then(function(res) {
      if (window.getCurrentRoute() !== route) return;
      var rows = Array.isArray(res) ? res : (res.data || res.rows || []);
      var mode = window._pendingViewMode || 'lot';
      var html = '<section style="padding:12px 16px">'
        + '<div style="display:flex;align-items:center;gap:6px;padding:8px 0 10px;flex-wrap:wrap">'
        + '<h2 style="margin:0;font-size:14px;white-space:nowrap;flex-shrink:0">⏳ PENDING</h2>'
        + '<span style="font-size:11px;color:var(--text-muted);flex-shrink:0">그룹:</span>'
        + _pendingModeBtn('date', '도착일별', mode)
        + _pendingModeBtn('container', '컨테이너별', mode)
        + _pendingModeBtn('lot', 'LOT별', mode)
        + '<span style="flex:1"></span>'
        + '<button class="btn" style="font-size:12px;padding:3px 10px;background:var(--accent,#3b82f6);color:#fff;border:1px solid var(--accent,#3b82f6);border-radius:4px" onclick="window.bulkConfirmPending()">✅ 일괄확정</button>'
        + '<button class="btn" style="font-size:12px;padding:3px 10px;border-radius:4px" onclick="window.exportPendingExcel()">📊 Excel</button>'
        + '<button class="btn" style="font-size:12px;padding:3px 10px;border-radius:4px" onclick="window.loadPendingPage()">🔄 새로고침</button>'
        + '</div>';
      html += '<div style="display:flex;align-items:center;gap:6px;padding:6px 0 8px;flex-wrap:wrap;border-bottom:1px solid var(--border,#334155);margin-bottom:8px">'
        + '<span style="font-size:11px;color:var(--text-muted);flex-shrink:0">🔍 검색</span>'
        + '<input id="pend-q" type="text" placeholder="LOT · BL · 컨테이너 · 선박" style="font-size:12px;padding:3px 8px;background:var(--surface,#1e293b);border:1px solid var(--border,#334155);border-radius:4px;color:var(--text-primary);width:180px" oninput="window._pendingFilter()">'
        + '<span style="font-size:11px;color:var(--text-muted);flex-shrink:0">입항일</span>'
        + '<input id="pend-df" type="date" style="font-size:12px;padding:2px 6px;background:var(--surface,#1e293b);border:1px solid var(--border,#334155);border-radius:4px;color:var(--text-primary)" onchange="window._pendingFilter()">'
        + '<span style="font-size:11px;color:var(--text-muted)">~</span>'
        + '<input id="pend-dt" type="date" style="font-size:12px;padding:2px 6px;background:var(--surface,#1e293b);border:1px solid var(--border,#334155);border-radius:4px;color:var(--text-primary)" onchange="window._pendingFilter()">'
        + '<button class="btn" style="font-size:12px;padding:3px 10px;border-radius:4px" onclick="window._pendingFilterReset()">✕ 초기화</button>'
        + '<span id="pend-count" style="font-size:11px;color:var(--text-muted)"></span>'
        + '</div>';
      if (!rows.length) {
        html += '<div class="empty" style="padding:60px;text-align:center;color:var(--text-muted);font-size:3em;font-weight:600;line-height:1.4">⏳ 입고 대기 중인 화물 없음</div></section>';
        c.innerHTML = html;
        return;
      }
      if (mode === 'container') html += _renderPendingByContainer(rows);
      else if (mode === 'date') html += _renderPendingByDate(rows);
      else html += _renderPendingLotRows(rows);
      // ── v8.7.0: 하단 합계 (tfoot 대체 — 그룹 모드 호환) ──
      if (window.SQMSummary) {
        var _pStats = window.SQMSummary.compute(rows, {qtyField:function(r){return Number(r.net_weight||0)/1000;}, tonbagCountField:'mxbg_pallet'});
        html += '<div style="margin-top:12px;padding:10px 14px;background:#FFD600;color:#222;font-weight:800;border-radius:6px;font-size:19px;text-align:right">'
              + '⏳ Pending 합계 (' + _pStats.lotCount.toLocaleString('ko-KR') + ' LOT) · '
              + '📦 톤백 ' + Math.round(_pStats.tonbagCount).toLocaleString('ko-KR') + '개 ' + _pStats.tonbagMt.toFixed(4) + ' MT'
              + (_pStats.sampleCount > 0 ? ' · 🧪 샘플 ' + Math.round(_pStats.sampleCount).toLocaleString('ko-KR') + '개 ' + _pStats.sampleMt.toFixed(4) + ' MT' : '')
              + ' · 총 ' + _pStats.totalMt.toFixed(4) + ' MT'
              + '</div>';
      }
      html += '</section>';
      c.innerHTML = html;
      setTimeout(function(){ if(window.enhanceDataTables) enhanceDataTables(c); }, 0);
    }).catch(function(e) {
      c.innerHTML = '<div class="empty" style="padding:60px;text-align:center;color:var(--danger)">❌ Pending 조회 실패: ' + escapeHtml(e.message||String(e)) + '</div>';
    });
  }

  // 📅 PENDING 인라인 실제 입고일 편집
  window.pendingEditInboundDate = function(btn, lotNo, currentDate) {
    if (!btn || !lotNo) return;
    var td = btn.closest('td');
    if (!td) return;
    var today = new Date().toISOString().slice(0, 10);
    var inp = document.createElement('input');
    inp.type = 'date';
    inp.value = currentDate || '';
    inp.max = today;
    inp.style.cssText = 'width:130px;padding:2px 6px;background:var(--bg,#0f172a);border:1px solid var(--accent,#3b82f6);border-radius:4px;color:var(--text);font-size:12px';
    td.innerHTML = '';
    td.appendChild(inp);
    inp.focus();
    var saved = false;
    var save = function() {
      if (saved) return;
      saved = true;
      var val = inp.value.trim();
      apiCall('PATCH', '/api/inbound/pending/' + encodeURIComponent(lotNo) + '/inbound-date', { inbound_date: val })
        .then(function() {
          showToast('success', '📅 입고일 저장: ' + (val || '삭제'));
          window.loadPendingPage();
        })
        .catch(function(e) {
          showToast('error', '저장 실패: ' + (e.message || e));
          window.loadPendingPage();
        });
    };
    inp.addEventListener('change', save);
    inp.addEventListener('blur', function() { setTimeout(save, 200); });
  };

  window.loadPendingPage = loadPendingPage;

  window._pendingFilter = function() {
    var q = ((document.getElementById('pend-q')||{}).value||'').toLowerCase().trim();
    var df = (document.getElementById('pend-df')||{}).value||'';
    var dt = (document.getElementById('pend-dt')||{}).value||'';
    var countEl = document.getElementById('pend-count');
    var mode = window._pendingViewMode || 'lot';
    var vis = 0, total = 0;
    if (mode === 'lot') {
      var tbody = document.getElementById('pend-lot-tbody');
      if (!tbody) return;
      var trs = tbody.querySelectorAll('tr');
      trs.forEach(function(row) {
        var txt = row.textContent.toLowerCase();
        var textOk = !q || txt.indexOf(q) !== -1;
        var cells = row.cells;
        var dateStr = cells && cells.length > 13 ? cells[13].textContent.trim() : '';
        var dMatch = dateStr.match(/(\d{4}-\d{2}-\d{2})/);
        var d = dMatch ? dMatch[1] : '';
        var dateOk = (!df || !d || d >= df) && (!dt || !d || d <= dt);
        var show = textOk && dateOk;
        row.style.display = show ? '' : 'none';
        total++; if (show) vis++;
      });
    } else {
      var groups = document.querySelectorAll('[data-pend-grp]');
      groups.forEach(function(g) {
        var txt = g.textContent.toLowerCase();
        var textOk = !q || txt.indexOf(q) !== -1;
        var dateOk = true;
        if (df || dt) {
          var dates = txt.match(/\d{4}-\d{2}-\d{2}/g) || [];
          if (dates.length) { dateOk = dates.some(function(d){ return (!df||d>=df)&&(!dt||d<=dt); }); }
        }
        var show = textOk && dateOk;
        g.style.display = show ? '' : 'none';
        total++; if (show) vis++;
      });
    }
    if (countEl) countEl.textContent = vis + '/' + total + '건';
  };

  window._pendingFilterReset = function() {
    var el;
    el = document.getElementById('pend-q');  if (el) el.value = '';
    el = document.getElementById('pend-df'); if (el) el.value = '';
    el = document.getElementById('pend-dt'); if (el) el.value = '';
    el = document.getElementById('pend-count'); if (el) el.textContent = '';
    window._pendingFilter();
  };
  window._togglePendingGroup = function(id) {
    var el = document.getElementById(id);
    if (!el) return;
    el.style.display = el.style.display === 'none' ? 'block' : 'none';
  };

  window.confirmPendingGroupFromButton = async function(btn) {
    var lots = [];
    try {
      lots = JSON.parse(btn.getAttribute('data-lots') || '[]');
    } catch (e) {
      console.error('[confirmPendingGroupFromButton] data-lots JSON 파싱 실패:', e, btn.getAttribute('data-lots'));
      showToast('error', '선택 데이터 파싱 오류: ' + e.message);
      return;
    }
    var dateInputId = btn.getAttribute('data-date-input');
    var dateEl = dateInputId ? document.getElementById(dateInputId) : null;
    var inboundDate = dateEl ? dateEl.value : '';
    if (!lots.length) { showToast('warning', '확정할 LOT이 없습니다'); return; }
    if (!inboundDate || !/^\d{4}-\d{2}-\d{2}$/.test(inboundDate)) {
      showToast('error', '입고 날짜를 올바르게 입력해 주세요'); return;
    }
    if (inboundDate > _pendingToday()) {
      showToast('error', '미래 날짜는 입력할 수 없습니다'); return;
    }
    if (!(await window.sqmConfirmAsync('✅ ' + lots.length + '개 LOT를 AVAILABLE로 확정합니다.\n입고일: ' + inboundDate + '\n\n계속하시겠습니까?'))) return;
    btn.disabled = true;
    btn.textContent = '진행 중...';
    var done = 0, errs = [];
    function next(i) {
      if (i >= lots.length) {
        if (errs.length) showToast('warning', '완료 ' + done + '건 / 실패 ' + errs.length + '건: ' + errs.join(', '));
        else showToast('success', '✅ ' + done + '건 입고 확정 완료');
        window.loadPendingPage();
        return;
      }
      apiPost('/api/inbound/confirm/' + encodeURIComponent(lots[i]), { inbound_date: inboundDate })
        .then(function() { done++; next(i + 1); })
        .catch(function(e) { console.warn('[batch confirm] LOT 실패:', lots[i], e&&e.message); errs.push(lots[i]); next(i + 1); });
    }
    next(0);
  };


  // v868 fix (2026-05-16): Available 그룹화 헬퍼 — Pending 패턴 차용
  function _renderAvailableGroup(rows, keyFn, labelPrefix) {
    var groups = {};
    rows.forEach(function(r) {
      var k = keyFn(r) || '(미지정)';
      if (!groups[k]) groups[k] = [];
      groups[k].push(r);
    });
    var keys = Object.keys(groups).sort();
    var html = '';
    keys.forEach(function(k, idx) {
      var lots = groups[k];
      var sumNet = 0;
      lots.forEach(function(r){ if (r.net != null) sumNet += Number(r.net); });
      var groupId = 'avg-' + idx;
      html += '<div style="margin-bottom:12px;border:1px solid var(--border,#334155);border-radius:8px;overflow:hidden">'
        + '<div style="display:flex;align-items:center;gap:10px;padding:10px 14px;background:var(--surface,#1e293b);cursor:pointer" '
        + 'onclick="(function(el){var t=document.getElementById(\'' + groupId + '\');if(t)t.style.display=t.style.display===\'none\'?\'block\':\'none\';})(this)">'
        + '<strong style="color:#22c55e;font-family:monospace">' + escapeHtml(labelPrefix + k) + '</strong>'
        + '<span style="font-size:12px;color:var(--text-muted)">' + lots.length + ' LOT · ' + fmtN(sumNet) + ' MT</span>'
        + '</div>'
        + '<div id="' + groupId + '" style="display:block">'
        + _renderAvailLotTableOnly(lots)
        + '</div>'
        + '</div>';
    });
    return html;
  }

  // LOT별 모드의 테이블 body만 렌더 (그룹 내부용)
  function _renderAvailLotTableOnly(rows) {
    // 그룹 내부에서는 헤더 없이 행만 렌더링 — 기존 mainRow 로직 재사용 필요
    // 임시: 간단한 LOT 목록 표시
    var html = '<table class="data-table" style="margin:0;font-size:12px"><thead><tr>'
      + '<th style="color:var(--text-muted);text-align:center;width:36px">#</th><th>LOT</th><th>SAP</th><th>Product</th><th>Container</th><th>Vessel</th><th>NET(MT)</th><th>Arrival</th><th>WH</th>'
      + '</tr></thead><tbody>';
    rows.forEach(function(r, _i) {
      html += '<tr>'
        + '<td class="mono-cell" style="color:var(--text-muted);text-align:center">' + (_i+1) + '</td>'
        + '<td class="mono-cell" style="color:var(--accent);font-weight:600">' + escapeHtml(r.lot||'') + '</td>'
        + '<td class="mono-cell">' + escapeHtml(r.sap||'-') + '</td>'
        + '<td><span class="tag">' + escapeHtml(r.product||'-') + '</span></td>'
        + '<td class="mono-cell">' + escapeHtml(r.container||'-') + '</td>'
        + '<td class="mono-cell">' + escapeHtml(r.vessel||'-') + '</td>'
        + '<td class="mono-cell" style="text-align:right">' + (r.net!=null?fmtN(r.net):'-') + '</td>'
        + '<td class="mono-cell">' + escapeHtml((r.arrival_date||'').slice(0,10) || '-') + '</td>'
        + '<td class="mono-cell">' + escapeHtml(r.wh||'-') + '</td>'
        + '</tr>';
    });
    return html + '</tbody></table>';
  }

  /* ===================================================
     7a-2. PAGE: Available (AVAILABLE 톤백 필터 뷰) — v9.5
     =================================================== */
  window._availViewMode = window._availViewMode || 'lot';
  function _availModeBtn(val, label) {
    var cur = window._availViewMode || 'lot';
    var active = val === cur
      ? 'background:var(--accent,#3b82f6);color:#fff;border:1px solid var(--accent,#3b82f6);border-radius:4px;'
      : 'background:var(--surface,#1e293b);color:var(--text-muted);border:1px solid var(--border,#334155);border-radius:4px;';
    return '<button class="btn" style="font-size:12px;padding:3px 10px;cursor:pointer;' + active + '" '
      + 'onclick="window._availViewMode=\'' + val + '\';window.loadAvailablePage()">' + label + '</button>';
  }

  function loadAvailablePage() {
    var route = 'available';
    if (window.getCurrentRoute() !== route) return;
    var c = document.getElementById('page-container');
    if (!c) return;
    c.innerHTML = '<div class="loading-spinner" style="padding:40px;text-align:center;color:var(--text-muted)">⏳ Available 재고 로딩 중...</div>';

    apiGet('/api/inventory?status=AVAILABLE&limit=5000').then(function(res) {
      if (window.getCurrentRoute() !== route) return;
      var rows = Array.isArray(res) ? res : (res.data || res.rows || res.items || []);
      if (!rows.length) {
        c.innerHTML = '<section style="padding:12px 16px">'
          + '<div style="display:flex;align-items:center;gap:6px;padding:8px 0 10px;flex-wrap:wrap">'
          + '<h2 style="margin:0;font-size:14px;white-space:nowrap;flex-shrink:0">✅ AVAILABLE</h2>'
          + '<span style="font-size:11px;color:var(--text-muted);flex-shrink:0">그룹:</span>'
          + _availModeBtn('lot','LOT별') + _availModeBtn('container','컨테이너별') + _availModeBtn('date','입고일별')
          + '<span style="flex:1"></span>'
          + '<button class="btn" style="font-size:12px;padding:3px 10px;background:rgba(239,68,68,0.15);color:#ef4444;border:1px solid #ef444455;border-radius:4px" onclick="window.availCancelSelected()">↩️ →PENDING</button>'
          + '<button class="btn" style="font-size:12px;padding:3px 10px;border-radius:4px" onclick="window.loadAvailablePage()">🔄 새로고침</button>'
          + '</div>'
          + '<div class="empty" style="padding:60px;text-align:center;color:var(--text-muted,#888)">✅ Available 재고 없음 (전량 배분 또는 피킹 완료)</div></section>';
        return;
      }
      var mode = window._availViewMode || 'lot';
      if (mode === 'container') rows = rows.slice().sort(function(a,b){ return (a.container||'').localeCompare(b.container||''); });
      else if (mode === 'date') rows = rows.slice().sort(function(a,b){ return (a.arrival_date||a.inbound_date||'').localeCompare(b.arrival_date||b.inbound_date||''); });
      var sumBal = 0, sumNet = 0, sumIni = 0, sumOb = 0, sumSampleMt = 0;
      rows.forEach(function(r) {
        if (r.balance      != null && !isNaN(Number(r.balance)))      sumBal += Number(r.balance);
        if (r.net          != null && !isNaN(Number(r.net)))          sumNet += Number(r.net);
        if (r.initial_weight  != null) sumIni += Number(r.initial_weight);
        if (r.outbound_weight != null) sumOb  += Number(r.outbound_weight);
        if (r.sample_weight_mt != null && !isNaN(Number(r.sample_weight_mt))) sumSampleMt += Number(r.sample_weight_mt);
      });
      var html = '<section style="padding:12px 16px">'
        + '<div style="display:flex;align-items:center;gap:6px;padding:8px 0 10px;flex-wrap:wrap">'
        + '<h2 style="margin:0;font-size:14px;white-space:nowrap;flex-shrink:0">✅ AVAILABLE</h2>'
        + '<span style="font-size:11px;color:var(--text-muted);flex-shrink:0">그룹:</span>'
        + _availModeBtn('lot','LOT별') + _availModeBtn('container','컨테이너별') + _availModeBtn('date','입고일별')
        + '<span style="flex:1"></span>'
        + '<button class="btn" style="font-size:12px;padding:3px 10px;background:rgba(239,68,68,0.15);color:#ef4444;border:1px solid #ef444455;border-radius:4px" onclick="window.availCancelSelected()">↩️ →PENDING</button>'
        + '<button class="btn" style="font-size:12px;padding:3px 10px;border-radius:4px" onclick="window.loadAvailablePage()">🔄 새로고침</button>'
        + '</div>'
        + '<div style="display:flex;align-items:center;gap:6px;padding:6px 0 8px;flex-wrap:wrap;border-bottom:1px solid var(--border,#334155);margin-bottom:8px">'
        + '<span style="font-size:11px;color:var(--text-muted);flex-shrink:0">🔍 검색</span>'
        + '<input id="avail-q" type="text" placeholder="LOT · BL · 컨테이너 · Product" style="font-size:12px;padding:3px 8px;background:var(--surface,#1e293b);border:1px solid var(--border,#334155);border-radius:4px;color:var(--text-primary);width:180px" oninput="window._availFilter()">'
        + '<span style="font-size:11px;color:var(--text-muted);flex-shrink:0">입고일</span>'
        + '<input id="avail-df" type="date" style="font-size:12px;padding:2px 6px;background:var(--surface,#1e293b);border:1px solid var(--border,#334155);border-radius:4px;color:var(--text-primary)" onchange="window._availFilter()">'
        + '<span style="font-size:11px;color:var(--text-muted)">~</span>'
        + '<input id="avail-dt" type="date" style="font-size:12px;padding:2px 6px;background:var(--surface,#1e293b);border:1px solid var(--border,#334155);border-radius:4px;color:var(--text-primary)" onchange="window._availFilter()">'
        + '<button class="btn" style="font-size:12px;padding:3px 10px;border-radius:4px" onclick="window._availFilterReset()">✕ 초기화</button>'
        + '<span id="avail-count" style="font-size:11px;color:var(--text-muted)"></span>'
        + '</div>'
        + '<div style="overflow-x:auto"><table class="data-table"><thead><tr>'
        + '<th style="width:36px;text-align:center"><input type="checkbox" onclick="window.availToggleAll(this)"></th>'
        + '<th>#</th><th style="text-align:left !important">LOT</th><th>SAP</th><th>BL</th><th>Product</th>'
        + '<th>Status</th><th>Balance(MT)</th><th title="앞=가용 중량(MT, 바로 배분 가능) / 뒤=예약(RESERVED) 중량.  예: 3.000/▲2.000 → 총 5MT 중 2MT 예약·3MT 배분 가능">Avail/Rsv(MT)</th><th>NET(MT)</th><th>Container</th>'
        + '<th title="총 톤백 개수 (MAXI BAG)">MXBG</th><th title="가용 톤백 수(개) — 바로 배분 가능한 톤백">Avail</th><th>Invoice</th>'
        + '<th>Arrival</th><th title="실제 창고 반입일 (Inbound Date)" style="color:#4fc3f7">🏭 Inbound</th><th>Con Return</th><th>Free</th><th>WH</th>'
        + '<th>Inbound(MT)</th><th>Location</th><th></th>'
        + '</tr></thead><tbody id="avail-tbody">';
      html += rows.map(function(r, i) {
        var lotKey = escapeHtml(r.lot||'');
        var hasSample = (r.sample_bags > 0);
        var parentContainer = escapeHtml(r.container || '-');
        var sampleRow = '';
        if (hasSample) {
          sampleRow =
            '<tr style="background:rgba(234,179,8,0.08);border-left:3px solid #eab308">' +
            '<td></td>' +
            '<td class="mono-cell" style="color:#eab308;text-align:center;padding:6px 10px">\u{1F52C}</td>' +
            '<td class="mono-cell cell-left" style="color:#eab308;font-weight:700;padding:6px 10px">' + lotKey + '(SP)</td>' +
            '<td class="mono-cell" style="color:#94a3b8">' + escapeHtml(r.sap||'') + '</td>' +
            '<td class="mono-cell" style="color:#94a3b8">' + escapeHtml(r.bl||'') + '</td>' +
            '<td><span class="tag" style="background:rgba(234,179,8,0.2);color:#eab308">' + escapeHtml((r.product||'') + ' (SP)') + '</span></td>' +
            '<td><span class="tag" style="background:rgba(34,197,94,0.15);color:#22c55e;font-weight:700">✅ AVAILABLE</span></td>' +
            '<td class="mono-cell" style="text-align:right;color:#eab308;font-weight:600">' + fmtN(r.sample_weight_mt||0) + '</td>' +
            '<td class="mono-cell" style="text-align:right;color:#eab308">' + fmtN(r.sample_weight_mt||0) + '</td>' +
            '<td class="mono-cell" style="text-align:right;color:#eab308">' + fmtN(r.sample_weight_mt||0) + '</td>' +
            '<td class="mono-cell" style="color:#94a3b8">' + parentContainer + '</td>' +
            '<td class="mono-cell" style="text-align:center;color:#eab308;font-weight:700">' + r.sample_bags + '</td>' +
            '<td class="mono-cell" style="text-align:center;color:#eab308;font-weight:700">' + r.sample_bags + '</td>' +
            '<td class="mono-cell" style="color:#94a3b8">' + escapeHtml(r.invoice_no||'') + '</td>' +
            '<td class="mono-cell" style="color:#94a3b8">' + escapeHtml((r.arrival_date||'').slice(0,10)) + '</td>' +
            '<td class="mono-cell" style="color:#4fc3f7;font-weight:600">' + (escapeHtml((r.date||'').slice(0,10)) || '-') + '</td>' +
            '<td class="mono-cell" style="color:#94a3b8">' + escapeHtml((r.con_return||'').slice(0,10)) + '</td>' +
            '<td class="mono-cell" style="text-align:center;color:#94a3b8">' + (r.free_time!=null?r.free_time:'-') + '</td>' +
            '<td class="mono-cell" style="color:#94a3b8">' + escapeHtml(r.wh||'') + '</td>' +
            '<td class="mono-cell" style="text-align:right;color:#eab308">' + fmtN(r.sample_weight_mt||0) + '</td>' +
            '<td><span class="tag" style="background:rgba(234,179,8,0.1);color:#94a3b8">' + escapeHtml(r.location||'-') + '</span></td>' +
            '<td></td>' +
            '</tr>';
        }
        var lotSafe = (r.lot||'').replace(/\\/g,'\\\\').replace(/'/g,"\\'");
        var mainRow =
          '<tr style="' + (hasSample ? 'border-left:3px solid #22c55e' : '') + '">'
          + '<td style="text-align:center"><input class="avail-cb" type="checkbox" data-lot="' + lotKey + '" onclick="event.stopPropagation()"></td>'
          + '<td class="mono-cell" style="color:var(--text-muted)">' + (i+1) + '</td>'
          + '<td class="mono-cell cell-left" style="color:var(--accent);font-weight:600;padding:6px 10px">' + lotKey + '</td>'
          + '<td class="mono-cell">' + escapeHtml(r.sap||'') + '</td>'
          + '<td class="mono-cell">' + escapeHtml(r.bl||'') + '</td>'
          + '<td><span class="tag">' + escapeHtml(r.product||'') + '</span></td>'
          + '<td><span class="tag" style="background:rgba(34,197,94,0.15);color:#22c55e">✅ AVAILABLE</span></td>'
          + '<td class="mono-cell" style="text-align:right">' + (r.balance!=null?fmtN((r.balance||0)-(r.sample_weight_mt||0)):'-') + '</td>'
          + '<td title="앞=가용 중량(MT, 바로 배분 가능) / 뒤=예약(RESERVED) 중량.  예: 3.000/▲2.000 → 총 5MT 중 2MT 예약·3MT 배분 가능" class="mono-cell" style="text-align:right">'
            + '<span style="color:#22c55e;font-weight:700">' + (r.avail_mt!=null?fmtN(r.avail_mt):'-') + '</span>'
            + '<span style="color:#94a3b8;font-size:11px"> / </span>'
            + '<span style="color:#3b82f6">' + (r.reserved_mt!=null&&r.reserved_mt>0?'▲'+fmtN(r.reserved_mt):'0') + '</span>'
          + '</td>'
          + '<td class="mono-cell" style="text-align:right">' + (r.net!=null?fmtN(r.net):'-') + '</td>'
          + '<td class="mono-cell">' + escapeHtml(r.container||'') + '</td>'
          + '<td title="총 톤백 개수 (MAXI BAG)" class="mono-cell" style="text-align:center">'
            + (r.mxbg_pallet > 0
              ? '<button class="btn btn-ghost btn-xs" style="font-weight:700;color:var(--accent)" '
                + 'data-lot="' + lotKey + '" onclick="window.showTonbagModal(this.dataset.lot)" title="톤백 상세 보기">' + r.mxbg_pallet + '</button>'
              : '-')
          + '</td>'
          + '<td title="가용 톤백 수(개) — 바로 배분 가능한 톤백" class="mono-cell" style="text-align:center">' + (r.avail_bags!=null?r.avail_bags:'-') + '</td>'
          + '<td class="mono-cell">' + escapeHtml(r.invoice_no||'') + '</td>'
          + '<td class="mono-cell">' + escapeHtml((r.arrival_date||'').slice(0,10)) + '</td>'
          + '<td class="mono-cell" style="color:#4fc3f7;font-weight:600">' + (escapeHtml((r.date||'').slice(0,10)) || '-') + '</td>'
          + '<td class="mono-cell">' + escapeHtml((r.con_return||'').slice(0,10)) + '</td>'
          + '<td class="mono-cell" style="text-align:center">' + (r.free_time!=null?r.free_time:'-') + '</td>'
          + '<td class="mono-cell">' + escapeHtml(r.wh||'') + '</td>'
          + '<td class="mono-cell" style="text-align:right">' + (r.initial_weight!=null?fmtN(r.initial_weight):'-') + '</td>'
          + '<td><span class="tag">' + escapeHtml(r.location||'-') + '</span></td>'
          + '<td style="white-space:nowrap;padding:6px 10px">'
            + '<button class="btn btn-ghost btn-xs" data-lot="' + lotKey + '" onclick="window.showInvActionMenu(this)" style="font-size:15px;padding:0 4px" title="추가기능">⋯</button> '
            + '<button class="btn btn-ghost btn-xs" onclick="window.revertToPending(\'' + lotSafe + '\')" title="입고 취소 → PENDING" style="color:#f59e0b;font-size:13px;padding:1px 5px;border:1px solid #f59e0b55">↩️</button>'
          + '</td>'
          + '</tr>';
        return mainRow + sampleRow;
      }).join('');
      var sumRegBal = Math.max(0, (sumBal||0) - (sumSampleMt||0));
      html += '</tbody><tfoot>';
      html += '<tr style="background:#FFD600;font-weight:800;color:#222;font-size:19px">';
      html += '<td colspan="7" style="text-align:right;padding:8px 10px">📦 톤백 합계 (' + rows.length + ' LOT)</td>';
      html += '<td class="mono-cell" style="text-align:right">' + fmtN(sumRegBal) + '</td>';
      html += '<td></td>';
      html += '<td class="mono-cell" style="text-align:right">' + fmtN(sumNet) + '</td>';
      html += '<td colspan="9"></td>';
      html += '<td class="mono-cell" style="text-align:right">' + fmtN(sumIni) + '</td>';
      html += '<td colspan="2"></td>';
      html += '</tr>';
      if (sumSampleMt > 0) {
        html += '<tr style="background:#FFF9C4;font-weight:800;color:#92400e;font-size:19px">';
        html += '<td colspan="7" style="text-align:right;padding:6px 10px">🧪 샘플 합계</td>';
        html += '<td class="mono-cell" style="text-align:right">' + fmtN(sumSampleMt) + '</td>';
        html += '<td colspan="12"></td>';
        html += '</tr>';
      }
      html += '</tfoot></table></div></section>';
      c.innerHTML = html;
    }).catch(function(e) {
      if (window.getCurrentRoute() !== route) return;
      c.innerHTML = '<div class="empty" style="padding:40px;text-align:center">Load failed: ' + escapeHtml(e.message||String(e)) + '</div>';
      showToast('error', 'Available 로드 실패: ' + (e&&e.message||String(e)));
    });
  }

    window.loadAvailablePage = loadAvailablePage;

  window._availFilter = function() {
    var q = ((document.getElementById('avail-q')||{}).value||'').toLowerCase().trim();
    var df = (document.getElementById('avail-df')||{}).value||'';
    var dt = (document.getElementById('avail-dt')||{}).value||'';
    var tbody = document.getElementById('avail-tbody');
    var countEl = document.getElementById('avail-count');
    if (!tbody) return;
    var trs = tbody.querySelectorAll('tr');
    var vis = 0, total = 0;
    trs.forEach(function(row) {
      var txt = row.textContent.toLowerCase();
      var textOk = !q || txt.indexOf(q) !== -1;
      var cells = row.cells;
      var dateStr = cells && cells.length > 14 ? cells[14].textContent.trim() : '';
      var dMatch = dateStr.match(/(\d{4}-\d{2}-\d{2})/);
      var d = dMatch ? dMatch[1] : '';
      var dateOk = (!df || !d || d >= df) && (!dt || !d || d <= dt);
      var show = textOk && dateOk;
      row.style.display = show ? '' : 'none';
      total++; if (show) vis++;
    });
    if (countEl) countEl.textContent = vis + '/' + total + '건';
  };

  window._availFilterReset = function() {
    var el;
    el = document.getElementById('avail-q');  if (el) el.value = '';
    el = document.getElementById('avail-df'); if (el) el.value = '';
    el = document.getElementById('avail-dt'); if (el) el.value = '';
    el = document.getElementById('avail-count'); if (el) el.textContent = '';
    window._availFilter();
  };
  window.availToggleAll = function(masterCb) {
    var cbs = document.querySelectorAll('.avail-cb');
    cbs.forEach(function(cb) { cb.checked = masterCb.checked; });
  };

  window.availCancelSelected = async function() {
    var checked = Array.from(document.querySelectorAll('.avail-cb:checked'));
    if (!checked.length) { showToast('warning', '취소할 LOT를 선택하세요'); return; }
    var lots = Array.from(new Set(checked.map(function(cb) { return cb.dataset.lot; }).filter(Boolean)));
    if (!(await window.sqmConfirmAsync('⚠️ 선택 취소 (AVAILABLE → PENDING)\n\n' + lots.length + '개 LOT:\n' + lots.slice(0,20).join('\n') + (lots.length > 20 ? '\n... (외 ' + (lots.length-20) + '개)' : '') + '\n\n입고 확정을 취소합니다. 계속하시겠습니까?'))) return;
    var done = 0, failed = [];
    function next() {
      if (done + failed.length === lots.length) {
        if (failed.length) {
          console.error('[availCancelSelected] 실패 LOT:', failed);
          window.sqmAlert(failed.join('\n') + '\n\n이 LOT들은 AVAILABLE 상태로 남아 있거나\nRESERVED/PICKED 톤백이 있어 취소 불가합니다.\n취소 완료: ' + done + '건', { title: '⚠️ 취소 실패 LOT ' + failed.length + '건', pre: true });
        } else {
          showToast('success', '↩️ ' + done + '건 전량 → PENDING 복구 완료');
        }
        window.renderPage('available');
        return;
      }
      var lot = lots[done + failed.length];
      apiPost('/api/inbound/revert/' + encodeURIComponent(lot), {})
        .then(function() { done++; next(); })
        .catch(function(e) { failed.push(lot); next(); });
    }
    next();
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



  window.pendingToggleAll = function(cb) {
    document.querySelectorAll('.pending-cb').forEach(function(c){ c.checked = cb.checked; });
  };

  window.showPendingActionMenu = function(event, lotNo) {
    event.stopPropagation();
    var old = document.getElementById('pending-ctx-menu');
    if (old) old.remove();
    var menu = document.createElement('div');
    menu.id = 'pending-ctx-menu';
    menu.style.cssText = 'position:fixed;z-index:9999;background:var(--surface,#1e293b);'
      + 'border:1px solid var(--border,#334155);border-radius:8px;padding:4px 0;min-width:180px;'
      + 'box-shadow:0 4px 20px rgba(0,0,0,0.4);';
    menu.style.top = event.clientY + 'px';
    menu.style.left = (event.clientX - 180) + 'px';
    var item1 = document.createElement('div');
    item1.style.cssText = 'padding:8px 16px;cursor:pointer;font-size:13px;color:var(--text)';
    item1.dataset.lot = lotNo;
    item1.onmouseenter = function() { this.style.background = '#334155'; };
    item1.onmouseleave = function() { this.style.background = ''; };
    item1.onclick = function() {
      window.showPendingConfirmModal(this.dataset.lot);
      var m = document.getElementById('pending-ctx-menu'); if (m) m.remove();
    };
    item1.textContent = '\u2705 AVAILABLE \uc785\uace0 \ud655\uc815';
    var item2 = document.createElement('div');
    item2.style.cssText = 'padding:8px 16px;cursor:pointer;font-size:13px;color:var(--text-muted)';
    item2.dataset.lot = lotNo;
    item2.onmouseenter = function() { this.style.background = '#334155'; };
    item2.onmouseleave = function() { this.style.background = ''; };
    item2.onclick = function() {
      window.invShowLotHistory(this.dataset.lot);
      var m = document.getElementById('pending-ctx-menu'); if (m) m.remove();
    };
    item2.textContent = '\ud83d\udcca LOT \uc774\ub825 \ubcf4\uae30';
    menu.appendChild(item1);
    menu.appendChild(item2);
    document.body.appendChild(menu);
    setTimeout(function(){
      document.addEventListener('click', function rm(){ menu.remove(); document.removeEventListener('click', rm); });
    }, 0);
  };

  window.showPendingConfirmModal = function(lotNo) {
    var today = new Date().toISOString().slice(0, 10);
    var ov = document.createElement('div');
    ov.id = 'pending-confirm-overlay';
    ov.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:10000;display:flex;align-items:center;justify-content:center';
    var inner = document.createElement('div');
    inner.style.cssText = 'background:var(--surface,#1e293b);border:1px solid var(--border,#334155);border-radius:12px;padding:24px;min-width:320px;max-width:400px';
    var h3 = document.createElement('h3');
    h3.style.cssText = 'margin:0 0 16px;font-size:15px;color:var(--text)';
    h3.textContent = '\u2705 \uc785\uace0 \ud655\uc815';
    var lotInfo = document.createElement('div');
    lotInfo.style.cssText = 'margin-bottom:8px;font-size:13px;color:var(--text-muted)';
    var lotSpan = document.createElement('span');
    lotSpan.style.cssText = 'color:var(--text);font-family:monospace';
    lotSpan.textContent = lotNo;
    lotInfo.appendChild(document.createTextNode('LOT: '));
    lotInfo.appendChild(lotSpan);
    var label = document.createElement('label');
    // v868 fix (2026-05-16): 입고 확정일 강조 — 사용자가 명확히 인지
    label.style.cssText = 'font-size:14px;font-weight:600;color:#22c55e;display:block;margin-bottom:8px;padding:6px 8px;background:rgba(34,197,94,0.08);border-left:3px solid #22c55e;border-radius:4px';
    label.innerHTML = '\ud83d\udcc5 <strong>\uc785\uace0 \ud655\uc815\uc77c</strong> \u2014 \uc774 \ub0a0\uc9dc\ub85c \ucc3d\uace0 \ubc18\uc785 \ucc98\ub9ac\ub429\ub2c8\ub2e4 (YYYY-MM-DD)';
    var input = document.createElement('input');
    input.id = 'pending-confirm-date';
    input.type = 'date';
    input.value = today;
    input.max = today;
    input.style.cssText = 'width:100%;box-sizing:border-box;padding:8px;background:var(--bg,#0f172a);border:1px solid var(--border,#334155);border-radius:6px;color:var(--text);font-size:14px;margin-bottom:16px';
    var btnRow = document.createElement('div');
    btnRow.style.cssText = 'display:flex;gap:8px;justify-content:flex-end';
    var cancelBtn = document.createElement('button');
    cancelBtn.className = 'btn btn-ghost';
    cancelBtn.textContent = '\ucde8\uc18c';
    cancelBtn.onclick = function() { ov.remove(); };
    var confirmBtn = document.createElement('button');
    confirmBtn.className = 'btn btn-primary';
    confirmBtn.textContent = '\ud655\uc815';
    confirmBtn.dataset.lot = lotNo;
    confirmBtn.onclick = function() { window.executePendingConfirm(this.dataset.lot); };
    btnRow.appendChild(cancelBtn);
    btnRow.appendChild(confirmBtn);
    inner.appendChild(h3);
    inner.appendChild(lotInfo);
    inner.appendChild(label);
    inner.appendChild(input);
    inner.appendChild(btnRow);
    ov.appendChild(inner);
    document.body.appendChild(ov);
    setTimeout(function() { input.focus(); }, 50);
  };

  window.executePendingConfirm = function(lotNo) {
    var dateEl = document.getElementById('pending-confirm-date');
    var inboundDate = dateEl ? dateEl.value : '';
    if (!inboundDate || !/^\d{4}-\d{2}-\d{2}$/.test(inboundDate)) {
      showToast('error', '\ub0a0\uc9dc\ub97c \uc62c\ubc14\ub974\uac8c \uc785\ub825\ud574 \uc8fc\uc138\uc694 (YYYY-MM-DD)'); return;
    }
    if (inboundDate > new Date().toISOString().slice(0, 10)) {
      showToast('error', '\ubbf8\ub798 \ub0a0\uc9dc\ub294 \uc785\ub825\ud560 \uc218 \uc5c6\uc2b5\ub2c8\ub2e4'); return;
    }
    var ov = document.getElementById('pending-confirm-overlay');
    if (ov) ov.remove();
    apiPost('/api/inbound/confirm/' + encodeURIComponent(lotNo), { inbound_date: inboundDate })
      .then(function() {
        showToast('success', '\u2705 ' + lotNo + ' \uc785\uace0 \ud655\uc815 \uc644\ub8cc');
        window.loadPendingPage();
        setTimeout(function() { if (window.navigate && window.getCurrentRoute() === 'pending') window.navigate('available'); }, 3000);
      })
      .catch(function(e) { showToast('error', '\uc785\uace0 \ud655\uc815 \uc2e4\ud328: ' + (e.message || e)); });
  };

  /* [FIX] \uc911\ubcf5 bulkConfirmPending/\u200b_execBulkConfirm \uc81c\uac70 \u2014 \uc815\uc0c1 \uad6c\ud604\ub9cc \uc720\uc9c0 */

  window.bulkConfirmPending = function() {
    var checked = Array.from(document.querySelectorAll('.pending-cb:checked')).map(function(c) { return c.dataset.lot; });
    if (!checked.length) { showToast('warning', '\ud655\uc815\ud560 LOT\uc744 \uc120\ud0dd\ud558\uc138\uc694'); return; }
    var today = new Date().toISOString().slice(0, 10);
    var ov = document.createElement('div');
    ov.id = 'bulk-confirm-overlay';
    ov.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:10000;display:flex;align-items:center;justify-content:center';
    var inner = document.createElement('div');
    inner.style.cssText = 'background:var(--surface,#1e293b);border:1px solid var(--border,#334155);border-radius:12px;padding:24px;min-width:360px';
    var h3 = document.createElement('h3');
    h3.style.cssText = 'margin:0 0 12px;font-size:15px;color:var(--text)';
    h3.textContent = '\u2705 \uc77c\uad04 \uc785\uace0 \ud655\uc815 (' + checked.length + '\uac74)';
    var lotList = document.createElement('div');
    lotList.style.cssText = 'max-height:120px;overflow-y:auto;margin-bottom:12px;font-size:12px;color:var(--text-muted);font-family:monospace';
    lotList.textContent = checked.join(', ');
    var label = document.createElement('label');
    label.style.cssText = 'font-size:13px;color:var(--text-muted);display:block;margin-bottom:6px';
    label.textContent = '\uc77c\uad04 \ud655\uc815\uc77c';
    var input = document.createElement('input');
    input.id = 'bulk-confirm-date';
    input.type = 'date';
    input.value = today;
    input.max = today;
    input.style.cssText = 'width:100%;box-sizing:border-box;padding:8px;background:var(--bg,#0f172a);border:1px solid var(--border,#334155);border-radius:6px;color:var(--text);font-size:14px;margin-bottom:16px';
    var prog = document.createElement('div');
    prog.id = 'bulk-progress';
    prog.style.cssText = 'display:none;margin-bottom:12px;font-size:13px;color:var(--accent,#3b82f6)';
    var btnRow = document.createElement('div');
    btnRow.style.cssText = 'display:flex;gap:8px;justify-content:flex-end';
    var cancelBtn = document.createElement('button');
    cancelBtn.className = 'btn btn-ghost';
    cancelBtn.textContent = '\ucde8\uc18c';
    cancelBtn.onclick = function() { ov.remove(); };
    var execBtn = document.createElement('button');
    execBtn.id = 'bulk-confirm-btn';
    execBtn.className = 'btn btn-primary';
    execBtn.textContent = '\uc77c\uad04 \ud655\uc815';
    execBtn.dataset.lots = JSON.stringify(checked);
    execBtn.onclick = function() { window._execBulkConfirm(JSON.parse(this.dataset.lots)); };
    btnRow.appendChild(cancelBtn);
    btnRow.appendChild(execBtn);
    inner.appendChild(h3);
    inner.appendChild(lotList);
    inner.appendChild(label);
    inner.appendChild(input);
    inner.appendChild(prog);
    inner.appendChild(btnRow);
    ov.appendChild(inner);
    document.body.appendChild(ov);
  };

  window._execBulkConfirm = function(lots) {
    var dateEl = document.getElementById('bulk-confirm-date');
    var inboundDate = dateEl ? dateEl.value : '';
    if (!inboundDate || !/^\d{4}-\d{2}-\d{2}$/.test(inboundDate)) {
      showToast('error', '\ub0a0\uc9dc\ub97c \uc62c\ubc14\ub974\uac8c \uc785\ub825\ud574 \uc8fc\uc138\uc694'); return;
    }
    var btn = document.getElementById('bulk-confirm-btn');
    if (btn) btn.disabled = true;
    var prog = document.getElementById('bulk-progress');
    if (prog) prog.style.display = 'block';
    var done = 0, errs = [];
    function next(i) {
      if (i >= lots.length) {
        var ov = document.getElementById('bulk-confirm-overlay');
        if (ov) ov.remove();
        if (errs.length) {
          showToast('warning', '\uc644\ub8cc ' + done + '\uac74 / \uc2e4\ud328 ' + errs.length + '\uac74: ' + errs.join(', '));
        } else {
          showToast('success', '\u2705 ' + done + '\uac74 \uc77c\uad04 \ud655\uc815 \uc644\ub8cc');
          setTimeout(function() { if (window.navigate && window.getCurrentRoute() === 'pending') window.navigate('available'); }, 2000);
        }
        window.loadPendingPage(); return;
      }
      if (prog) prog.textContent = '\uc9c4\ud589 \uc911... ' + (i + 1) + '/' + lots.length + ' \u2014 ' + lots[i];
      apiPost('/api/inbound/confirm/' + encodeURIComponent(lots[i]), { inbound_date: inboundDate })
        .then(function() { done++; next(i + 1); })
        .catch(function(e) { console.warn('[batch confirm] LOT 실패:', lots[i], e&&e.message); errs.push(lots[i]); next(i + 1); });
    }
    next(0);
  };


  // v868 fix (2026-05-16): Pending/Available 탭 Excel 내보내기 헬퍼
  window.exportPendingExcel = function() {
    var tbl = document.querySelector('#page-container table.data-table');
    if (!tbl) { if (window.showToast) showToast('warning', '내보낼 테이블이 없습니다'); return; }
    var ts = new Date().toISOString().slice(0,10);
    if (window.exportTableToExcel) {
      window.exportTableToExcel(tbl, 'pending_' + ts + '.xlsx');
    } else {
      showToast('error', 'Excel 내보내기 함수를 찾을 수 없습니다 (exportTableToExcel)');
    }
  };
  window.exportAvailableExcel = function() {
    var tbl = document.querySelector('#page-container table.data-table');
    if (!tbl) { if (window.showToast) showToast('warning', '내보낼 테이블이 없습니다'); return; }
    var ts = new Date().toISOString().slice(0,10);
    if (window.exportTableToExcel) {
      window.exportTableToExcel(tbl, 'available_' + ts + '.xlsx');
    } else {
      showToast('error', 'Excel 내보내기 함수를 찾을 수 없습니다 (exportTableToExcel)');
    }
  };
  window.loadInventoryPage  = loadInventoryPage;
})();
