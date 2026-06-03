(function () {
  'use strict';

  var apiGet = window.apiGet;
  var apiPost = window.apiPost;
  var apiCall = window.apiCall;
  var extractRows = window.extractRows;
  var escapeHtml = window.escapeHtml;
  var showDataModal = window.showDataModal;
  var showToast = window.showToast;
  var _sqmSyncModalHeaderFromContent = window._sqmSyncModalHeaderFromContent;

  /* ===================================================
     8t. 품목별 재고 요약 — 제품 기준 집계
     =================================================== */
  function showProductSummaryModal() {
    showDataModal('📋 품목별 재고 요약','<div style="padding:20px;text-align:center">⏳ 로딩 중...</div>');
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
        _sqmSyncModalHeaderFromContent();
        return;
      }
      var tbl = '<table class="data-table"><thead><tr><th>제품</th><th>LOT 수</th><th>톤백 수</th><th>총 중량(MT)</th></tr></thead><tbody>';
      prods.forEach(function(p){
        var d = byProd[p];
        tbl += '<tr><td style="font-weight:600">'+escapeHtml(p)+'</td><td>'+d.lots+'</td><td>'+d.tonbags+'</td><td class="mono-cell">'+d.weight.toFixed(3)+'</td></tr>';
      });
      tbl += '</tbody></table>';
      document.getElementById('sqm-modal-content').innerHTML = '<h2 style="margin-bottom:16px">📋 품목별 재고 요약</h2><p style="color:var(--text-muted);font-size:.85rem;margin-bottom:12px">' + prods.length + '개 제품, ' + rows.length + '개 LOT</p>' + tbl;
      _sqmSyncModalHeaderFromContent();
    }).catch(function(e){
      document.getElementById('sqm-modal-content').innerHTML = '<h2>품목별 재고 요약</h2><div class="empty">조회 실패</div>';
      _sqmSyncModalHeaderFromContent();
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
    showDataModal('📊 품목별 입출고 현황','<div style="padding:20px;text-align:center">⏳ 로딩 중...</div>');
    apiGet('/api/q/movement-history').then(function(res){
      var rows = extractRows(res);
      // Group by product
      var byProd = {};
      rows.forEach(function(r){
        var p = r.product || '(미지정)';
        if (!byProd[p]) byProd[p] = { inbound:0, outbound:0, return_count:0, move:0 };
        var t = (r.movement_type||'').toUpperCase();
        if (t === 'INBOUND') byProd[p].inbound += Number(r.quantity||r.weight||1);
        else if (t === 'SOLD') byProd[p].outbound += Number(r.quantity||r.weight||1);
        else if (t === 'RETURN') byProd[p].return_count += Number(r.quantity||r.weight||1);
        else byProd[p].move += Number(r.quantity||r.weight||1);
      });
      var prods = Object.keys(byProd).sort();
      if (!prods.length) {
        document.getElementById('sqm-modal-content').innerHTML = '<h2>품목별 입출고</h2><div class="empty">데이터가 없습니다</div>';
        _sqmSyncModalHeaderFromContent();
        return;
      }
      var tbl = '<table class="data-table"><thead><tr><th>제품</th><th>입고</th><th>출고</th><th>반품</th><th>기타</th></tr></thead><tbody>';
      prods.forEach(function(p){
        var d = byProd[p];
        tbl += '<tr><td style="font-weight:600">'+escapeHtml(p)+'</td><td style="color:var(--success)">'+d.inbound+'</td><td style="color:var(--warning)">'+d.outbound+'</td><td>'+d.return_count+'</td><td>'+d.move+'</td></tr>';
      });
      tbl += '</tbody></table>';
      document.getElementById('sqm-modal-content').innerHTML = '<h2 style="margin-bottom:16px">📊 품목별 입출고 현황</h2>' + tbl;
      _sqmSyncModalHeaderFromContent();
    }).catch(function(e){
      document.getElementById('sqm-modal-content').innerHTML = '<h2>품목별 입출고</h2><div class="empty">조회 실패</div>';
      _sqmSyncModalHeaderFromContent();
    });
  }
  window.showProductMovementModal = showProductMovementModal;

  /* ===================================================
     8w. 제품 마스터 — product_master 테이블 CRUD + inventory 동기화
     =================================================== */
  function showProductMasterModal() {
    var selectedId = null;
    var cacheItems = [];

    function bindPmHandlers() {
      var syncBtn = document.getElementById('pm-sync');
      var saveBtn = document.getElementById('pm-save');
      var newBtn = document.getElementById('pm-new');
      var nameEl = document.getElementById('pm-name');
      var sapEl = document.getElementById('pm-sap');
      var specEl = document.getElementById('pm-spec');
      var unitEl = document.getElementById('pm-unit');
      var remEl = document.getElementById('pm-remarks');
      if (!nameEl || !saveBtn) return;
      if (syncBtn) syncBtn.addEventListener('click', function(){
        apiPost('/api/product-master/sync-from-inventory', {}).then(function(res){
          if (res && res.ok === false) { showToast('error', res.error || '실패'); return; }
          showToast('success', res.message || '동기화 완료');
          loadPm();
        }).catch(function(e){ showToast('error', String(e.message||e)); });
      });
      if (newBtn) newBtn.addEventListener('click', function(){
        selectedId = null;
        nameEl.value = ''; sapEl.value = ''; specEl.value = ''; unitEl.value = ''; remEl.value = '';
      });
      saveBtn.addEventListener('click', function(){
        var body = {
          product_name: nameEl.value.trim(),
          sap_no: sapEl.value.trim(),
          spec: specEl.value.trim(),
          unit: unitEl.value.trim(),
          remarks: remEl.value.trim()
        };
        if (!body.product_name) { showToast('warning', '제품명을 입력하세요'); return; }
        var req = selectedId
          ? apiCall('PUT', '/api/product-master/' + selectedId, body)
          : apiPost('/api/product-master/create', body);
        req.then(function(res){
          if (res && res.ok === false) { showToast('error', res.error || '실패'); return; }
          showToast('success', res.message || '저장됨');
          selectedId = null;
          nameEl.value = ''; sapEl.value = ''; specEl.value = ''; unitEl.value = ''; remEl.value = '';
          loadPm();
        }).catch(function(e){ showToast('error', String(e.message||e)); });
      });
      document.querySelectorAll('.pm-edit').forEach(function(btn){
        btn.addEventListener('click', function(){
          var id = parseInt(btn.getAttribute('data-id'), 10);
          var r = cacheItems.filter(function(x){ return Number(x.id) === id; })[0];
          if (!r) return;
          selectedId = id;
          nameEl.value = r.product_name || '';
          sapEl.value = r.sap_no || '';
          specEl.value = r.spec || '';
          unitEl.value = r.unit || '';
          remEl.value = r.remarks || '';
        });
      });
      document.querySelectorAll('.pm-del').forEach(function(btn){
        btn.addEventListener('click', function(){
          var id = parseInt(btn.getAttribute('data-id'), 10);
          if (!window.sqmConfirm('이 품목 마스터 행을 삭제할까요?')) return;
          apiCall('DELETE', '/api/product-master/' + id, null).then(function(res){
            if (res && res.ok === false) { showToast('error', res.error || '실패'); return; }
            showToast('success', '삭제됨');
            loadPm();
          }).catch(function(e){ showToast('error', String(e.message||e)); });
        });
      });
    }

    function renderPm(data) {
      var items = (data && data.items) ? data.items : [];
      cacheItems = items.slice();
      var rows = items.map(function(r){
        return '<tr>'
          + '<td style="font-weight:600">' + escapeHtml(r.product_name || '') + '</td>'
          + '<td class="mono-cell">' + escapeHtml(r.sap_no || '') + '</td>'
          + '<td>' + escapeHtml(r.spec || '') + '</td>'
          + '<td>' + escapeHtml(r.unit || '') + '</td>'
          + '<td style="white-space:nowrap">'
          + '<button type="button" class="btn btn-ghost pm-edit" style="padding:4px 8px;font-size:.8rem" data-id="'+r.id+'">수정</button> '
          + '<button type="button" class="btn btn-ghost pm-del" style="padding:4px 8px;font-size:.8rem;color:var(--danger,#c62828)" data-id="'+r.id+'">삭제</button>'
          + '</td></tr>';
      }).join('');
      var tbody = rows || '<tr><td colspan="5" class="empty">등록 없음 — 상단에서 inventory 동기화 또는 신규 저장</td></tr>';
      var html = [
        '<div style="max-width:720px">',
        '  <h2 style="margin:0 0 10px 0">📦 제품 마스터</h2>',
        '  <p style="color:var(--text-muted);font-size:.85rem;margin-bottom:12px">표준 품목·SAP·규격 (inventory LOT와 별도 테이블).</p>',
        '  <div style="margin-bottom:12px;display:flex;gap:8px;flex-wrap:wrap">',
        '    <button type="button" class="btn btn-primary" id="pm-sync">📥 inventory에서 일괄 가져오기</button>',
        '  </div>',
        '  <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:12px">',
        '    <label>제품명 *<input id="pm-name" type="text" style="width:100%;padding:8px;margin-top:4px;background:var(--bg-hover);color:var(--text);border:1px solid var(--border);border-radius:6px"/></label>',
        '    <label>SAP<input id="pm-sap" type="text" style="width:100%;padding:8px;margin-top:4px;background:var(--bg-hover);color:var(--text);border:1px solid var(--border);border-radius:6px"/></label>',
        '    <label>규격<input id="pm-spec" type="text" style="width:100%;padding:8px;margin-top:4px;background:var(--bg-hover);color:var(--text);border:1px solid var(--border);border-radius:6px"/></label>',
        '    <label>단위<input id="pm-unit" type="text" style="width:100%;padding:8px;margin-top:4px;background:var(--bg-hover);color:var(--text);border:1px solid var(--border);border-radius:6px"/></label>',
        '    <label style="grid-column:1/-1">비고<input id="pm-remarks" type="text" style="width:100%;padding:8px;margin-top:4px;background:var(--bg-hover);color:var(--text);border:1px solid var(--border);border-radius:6px"/></label>',
        '  </div>',
        '  <div style="display:flex;gap:8px;margin-bottom:14px">',
        '    <button type="button" class="btn btn-primary" id="pm-save">저장 (신규/수정)</button>',
        '    <button type="button" class="btn btn-ghost" id="pm-new">폼 비우기</button>',
        '  </div>',
        '  <div style="max-height:320px;overflow:auto;border:1px solid var(--border);border-radius:8px">',
        '    <table class="data-table"><thead><tr><th>제품명</th><th>SAP</th><th>규격</th><th>단위</th><th></th></tr></thead><tbody>',
        tbody,
        '    </tbody></table>',
        '  </div>',
        '  <div style="margin-top:14px;text-align:right"><button type="button" class="btn btn-ghost" onclick="document.getElementById(\'sqm-modal\').style.display=\'none\'">닫기</button></div>',
        '</div>'
      ].join('\n');
      document.getElementById('sqm-modal-content').innerHTML = html;
      _sqmSyncModalHeaderFromContent();
      bindPmHandlers();
    }

    function loadPm() {
      apiGet('/api/product-master/list').then(function(res){
        var d = res.data || res || {};
        renderPm(d);
      }).catch(function(e){
        document.getElementById('sqm-modal-content').innerHTML = '<h2>제품 마스터</h2><div class="empty">'+escapeHtml(e.message||String(e))+'</div>';
        _sqmSyncModalHeaderFromContent();
      });
    }

    showDataModal('', '<div style="padding:20px;text-align:center">⏳ 로딩 중...</div>');
    loadPm();
  }
  window.showProductMasterModal = showProductMasterModal;

})();
