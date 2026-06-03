(function () {
  'use strict';

  var API = window.API;
  var escapeHtml = window.escapeHtml;
  var showDataModal = window.showDataModal;
  var showToast = window.showToast;
  var dbgLog = window.dbgLog;

  function currentRoute() {
    return typeof window.getCurrentRoute === 'function' ? window.getCurrentRoute() : null;
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
          if (currentRoute() === 'inventory' && typeof window.loadInventoryPage === 'function') window.loadInventoryPage();
          if (typeof window.loadKpi === 'function') window.loadKpi();
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
        // ── validation_summary 경고 배너 ──────────────────
        var vs = d.validation_summary || {};
        var vsHtml = '';
        var vsItems = [];
        if (vs.skipped_no_lot > 0)
          vsItems.push('LOT NO 없음: <b>' + vs.skipped_no_lot + '행</b> 건너뜀');
        if (vs.warn_no_qty && vs.warn_no_qty.length)
          vsItems.push('QTY(MT) 0 이하: <b>' + vs.warn_no_qty.length + '건</b> (' + vs.warn_no_qty.slice(0,5).join(', ') + (vs.warn_no_qty.length>5?'…':'') + ')');
        if (vs.warn_no_sold_to && vs.warn_no_sold_to.length)
          vsItems.push('SOLD TO 없음: <b>' + vs.warn_no_sold_to.length + '건</b> (' + vs.warn_no_sold_to.slice(0,5).join(', ') + (vs.warn_no_sold_to.length>5?'…':'') + ')');
        if (vsItems.length) {
          vsHtml = '<div style="background:rgba(255,193,7,.1);border:1px solid #ffc107;border-radius:6px;padding:8px 12px;margin-top:8px;font-size:.83rem">' +
            '<b style="color:#ffc107">⚠️ 데이터 검증 알림</b><br>' +
            vsItems.map(function(s){ return '&nbsp;• ' + s; }).join('<br>') +
            '<br><span style="color:var(--text-muted);font-size:.79rem">예약은 완료됐습니다. 위 항목은 실무 확인이 필요합니다.</span>' +
            '</div>';
        }
        // ── 기존 에러/경고 ─────────────────────────────────
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
        var aiBadge = d.mapping_source === 'AI폴백'
          ? ' <span style="background:#7c3aed;color:#fff;font-size:.75rem;padding:1px 6px;border-radius:10px">🤖 AI 매핑</span>'
          : '';
        return '<div style="color:var(--text-muted);font-size:.85rem">파일: ' + escapeHtml(d.filename||'-') +
               ' · <strong style="color:var(--accent)">' + (d.reserved||0) + '건</strong> 예약 / 총 ' + (d.total_rows||0) + '행' + aiBadge + ' · 매핑: ' + ((d.matched_columns||[]).join(', ')) +
               '</div>' + vsHtml + warnHtml + detailHtml;
      }
    });
  }
  window.showAllocationUploadModal = showAllocationUploadModal;

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
          if (currentRoute() === 'inventory' && typeof window.loadInventoryPage === 'function') window.loadInventoryPage();
          if (typeof window.loadKpi === 'function') window.loadKpi();
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

  /* D/O PDF 업로드 */
  function showDoUploadModal() {
    _showPdfUploadModal({
      title: '📋 D/O PDF 업로드',
      subtitle: 'D/O PDF 파일을 선택하세요. 해당 LOT에 D/O 정보를 업데이트합니다.',
      endpoint: '/api/inbound/do',
      onSuccess: function(d) {
        return '<div style="color:var(--text-muted);font-size:.85rem">파일: '
          + escapeHtml(d.filename||'-') + ' · LOT: ' + escapeHtml(d.lot_no||'-')
          + ' · <strong style="color:var(--accent)">D/O 등록 완료</strong></div>';
      }
    });
  }
  window.showDoUploadModal = showDoUploadModal;

  /* Sales Order Excel 업로드 */
  function showSalesOrderUploadModal() {
    _showExcelUploadModal({
      title: '📊 Sales Order Excel 업로드',
      subtitle: 'Sales Order Excel 파일(.xlsx/.xls)을 선택하세요.',
      endpoint: '/api/action2/sales-order-upload',
      onSuccess: function(d) {
        return '<div style="color:var(--text-muted);font-size:.85rem">파일: '
          + escapeHtml(d.filename||'-') + ' · 처리 ' + (d.count||0) + '건</div>';
      }
    });
  }
  window.showSalesOrderUploadModal = showSalesOrderUploadModal;

  /* OneStop Inbound module -> sqm-onestop-inbound.js */
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

  window._showExcelUploadModal = _showExcelUploadModal;
  window._showPdfUploadModal = _showPdfUploadModal;
})();
