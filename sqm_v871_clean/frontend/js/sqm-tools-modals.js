(function () {
  'use strict';

  var apiGet = window.apiGet;
  var extractRows = window.extractRows;
  var escapeHtml = window.escapeHtml;
  var showDataModal = window.showDataModal;
  var showToast = window.showToast;
  var dispatchAction = window.dispatchAction;
  var _sqmSyncModalHeaderFromContent = window._sqmSyncModalHeaderFromContent;

  /* ===================================================
     8r. 대량 이동 승인 — 승인 대기 중인 이동 건 목록
     =================================================== */
  function showMoveApprovalQueueModal() {
    showDataModal('✅ 대량 이동 승인','<div style="padding:20px;text-align:center">⏳ 로딩 중...</div>');
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
      _sqmSyncModalHeaderFromContent();
    }).catch(function(e){
      document.getElementById('sqm-modal-content').innerHTML = '<h2>대량 이동 승인</h2><div class="empty">조회 실패</div>';
      _sqmSyncModalHeaderFromContent();
    });
  }
  window.showMoveApprovalQueueModal = showMoveApprovalQueueModal;
  /* ===================================================
     8s. 문서 변환 (OCR/PDF → Excel/Word)
     =================================================== */
  function showDocConvertModal() {
    var html = [
      '<div style="max-width:560px">',
      '  <h2 style="margin:0 0 12px 0">📷 문서 변환 (OCR/PDF)</h2>',
      '  <p style="color:var(--text-muted);margin:0 0 12px 0;font-size:.88rem">v864 도구 메뉴와 동일하게 세부 단계를 구분합니다. 서버 OCR·배치 변환은 데스크톱 빌드(Phase 6)에서 연동합니다.</p>',
      '  <div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:14px">',
      '    <button type="button" class="btn btn-ghost" id="dc-xlsx">📊 PDF → Excel</button>',
      '    <button type="button" class="btn btn-ghost" id="dc-docx">📝 PDF → Word</button>',
      '    <button type="button" class="btn btn-ghost" id="dc-batch">📁 일괄 변환</button>',
      '    <button type="button" class="btn btn-ghost" id="dc-analyze">🔍 문서 분석</button>',
      '    <button type="button" class="btn btn-ghost" id="dc-ocr">📷 OCR (스캔 PDF)</button>',
      '  </div>',
      '  <div style="display:grid;grid-template-columns:100px 1fr;gap:10px;align-items:center;margin-bottom:16px">',
      '    <label style="font-weight:600">변환 형식</label>',
      '    <select id="dc-format" style="padding:8px;background:var(--bg-hover);color:var(--text);border:1px solid var(--border);border-radius:6px">',
      '      <option value="excel">→ Excel (.xlsx)</option>',
      '      <option value="word">→ Word (.docx)</option>',
      '    </select>',
      '  </div>',
      '  <div id="dc-drop" style="border:2px dashed var(--border);border-radius:8px;padding:28px 16px;text-align:center;background:var(--bg-hover);cursor:pointer;margin-bottom:12px">',
      '    <div style="font-size:2.2rem;margin-bottom:8px">📄</div>',
      '    <div id="dc-name" style="color:var(--text-muted);font-size:.9rem">클릭 또는 PDF/이미지를 드롭하세요</div>',
      '  </div>',
      '  <input type="file" id="dc-file" accept=".pdf,.png,.jpg,.jpeg,.tiff,.bmp" style="display:none">',
      '  <div style="padding:12px;background:var(--bg-hover);border-radius:6px;margin-bottom:14px;font-size:.82rem;color:var(--warning)">',
      '    💡 Tesseract 등 OCR 미설치 시 스캔 PDF는 텍스트 추출이 제한됩니다. 입고용 PDF는 메뉴 <strong>PDF 스캔 입고</strong>를 사용하세요.',
      '  </div>',
      '  <div style="display:flex;gap:8px;justify-content:flex-end">',
      '    <button onclick="document.getElementById(\'sqm-modal\').style.display=\'none\'" class="btn btn-ghost">닫기</button>',
      '    <button id="dc-submit" class="btn btn-primary" disabled>선택 파일 변환</button>',
      '  </div>',
      '</div>'
    ].join('\n');
    showDataModal('', html);
    function stub(msg) { showToast('info', msg); }
    document.getElementById('dc-xlsx').addEventListener('click', function(){ document.getElementById('dc-format').value='excel'; stub('Excel 변환 파이프라인은 Phase 6(OCR 서버) 연동 후 사용 가능합니다.'); });
    document.getElementById('dc-docx').addEventListener('click', function(){ document.getElementById('dc-format').value='word'; stub('Word 변환 파이프라인은 Phase 6 연동 후 사용 가능합니다.'); });
    document.getElementById('dc-batch').addEventListener('click', function(){ stub('일괄 변환은 서버 배치 작업으로 Phase 6에서 제공 예정입니다.'); });
    document.getElementById('dc-analyze').addEventListener('click', function(){ stub('문서 분석(메타/표 추출)은 동일 단계에서 Gemini·로컬 OCR과 함께 연계합니다.'); });
    document.getElementById('dc-ocr').addEventListener('click', function(){ stub('스캔 PDF OCR은 Tesseract 설치 및 Phase 6 파이프라인이 필요합니다.'); });
    var drop = document.getElementById('dc-drop');
    var fi = document.getElementById('dc-file');
    var nm = document.getElementById('dc-name');
    var sub = document.getElementById('dc-submit');
    function setF(f){
      if (!f) return;
      nm.innerHTML = '✅ <strong>'+escapeHtml(f.name)+'</strong> ('+Math.round(f.size/1024)+' KB)';
      sub.disabled = false;
    }
    drop.addEventListener('click', function(){ fi.click(); });
    fi.addEventListener('change', function(e){ if(e.target.files&&e.target.files[0]) setF(e.target.files[0]); });
    drop.addEventListener('dragover', function(e){ e.preventDefault(); });
    drop.addEventListener('drop', function(e){ e.preventDefault(); if(e.dataTransfer.files&&e.dataTransfer.files[0]) setF(e.dataTransfer.files[0]); });
    sub.addEventListener('click', function(){
      showToast('info', '선택 파일 변환은 Phase 6에서 OCR 엔진 연동 후 지원됩니다');
    });
  }
  window.showDocConvertModal = showDocConvertModal;
  function showReturnStatisticsModal() {
    showDataModal('📊 반품 사유 통계', '<div style="padding:20px;text-align:center">⏳ 로딩 중...</div>');
    apiGet('/api/q2/return-stats').then(function(res){
      var d = res.data || res || {};
      var byReason = d.by_reason || [];
      var monthly = d.monthly_trend || [];
      var total = d.total || {};
      var tbl1 = '<table class="data-table"><thead><tr><th>사유</th><th>건수</th><th>중량(MT)</th></tr></thead><tbody>';
      if (!byReason.length) tbl1 += '<tr><td colspan="3" class="empty">사유별 데이터 없음</td></tr>';
      byReason.forEach(function(r){
        tbl1 += '<tr><td>'+escapeHtml(String(r.reason||'-'))+'</td><td>'+(r.cnt!=null?r.cnt:0)+'</td><td class="mono-cell">'+(r.total_mt!=null?r.total_mt:'-')+'</td></tr>';
      });
      tbl1 += '</tbody></table>';
      var tbl2 = '<table class="data-table"><thead><tr><th>월</th><th>건수</th><th>중량(MT)</th></tr></thead><tbody>';
      if (!monthly.length) tbl2 += '<tr><td colspan="3" class="empty">월별 데이터 없음</td></tr>';
      monthly.forEach(function(r){
        tbl2 += '<tr><td>'+escapeHtml(String(r.month||'-'))+'</td><td>'+(r.cnt!=null?r.cnt:0)+'</td><td class="mono-cell">'+(r.total_mt!=null?r.total_mt:'-')+'</td></tr>';
      });
      tbl2 += '</tbody></table>';
      var sum = '<p style="color:var(--text-muted);font-size:.9rem;margin-bottom:10px">전체 <strong>'+(total.cnt!=null?total.cnt:0)+'</strong>건 · '
        + '<strong>'+(total.total_mt!=null?total.total_mt:'0')+'</strong> MT (return_history)</p>';
      document.getElementById('sqm-modal-content').innerHTML = [
        '<h2 style="margin-bottom:8px">📊 반품 사유 통계</h2>',
        sum,
        '<h3 style="margin:14px 0 8px;font-size:1rem">사유별</h3>', tbl1,
        '<h3 style="margin:14px 0 8px;font-size:1rem">월별 추이 (최근 12개월)</h3>', tbl2
      ].join('');
      _sqmSyncModalHeaderFromContent();
    }).catch(function(e){
      document.getElementById('sqm-modal-content').innerHTML = '<h2>반품 통계</h2><div class="empty">'+escapeHtml(e.message||String(e))+'</div>';
      _sqmSyncModalHeaderFromContent();
    });
  }
  window.showReturnStatisticsModal = showReturnStatisticsModal;
  function showAdvancedToolsHubModal() {
    var h = [
      '<div style="max-width:440px">',
      '  <h2 style="margin:0 0 12px 0">🔧 고급 도구</h2>',
      '  <p style="color:var(--text-muted);font-size:.86rem;margin-bottom:14px">v864 「고급」에 해당하는 진단·유지보수로 이동합니다.</p>',
      '  <div style="display:flex;flex-direction:column;gap:8px">',
      '    <button type="button" class="btn btn-primary" id="adv-int">🩺 정합성 검증 (시각화)</button>',
      '    <button type="button" class="btn btn-ghost" id="adv-opt">🔧 DB 최적화</button>',
      '    <button type="button" class="btn btn-ghost" id="adv-log">📋 로그 정리</button>',
      '    <button type="button" class="btn btn-ghost" id="adv-testdb">🗑️ 테스트 DB 초기화</button>',
      '  </div>',
      '  <div style="margin-top:14px;text-align:right"><button type="button" class="btn btn-ghost" onclick="document.getElementById(\'sqm-modal\').style.display=\'none\'">닫기</button></div>',
      '</div>'
    ].join('\n');
    showDataModal('', h);
    document.getElementById('adv-int').addEventListener('click', function(){
      document.getElementById('sqm-modal').style.display='none';
      window.renderInfoModal('정합성 검증 (시각화)', '/api/action/integrity-report');
    });
    document.getElementById('adv-opt').addEventListener('click', function(){
      document.getElementById('sqm-modal').style.display='none';
      dispatchAction('onOptimizeDb');
    });
    document.getElementById('adv-log').addEventListener('click', function(){
      document.getElementById('sqm-modal').style.display='none';
      dispatchAction('onCleanupLogs');
    });
    document.getElementById('adv-testdb').addEventListener('click', function(){
      document.getElementById('sqm-modal').style.display='none';
      dispatchAction('onTestDbReset');
    });
  }
  window.showAdvancedToolsHubModal = showAdvancedToolsHubModal;

})();
