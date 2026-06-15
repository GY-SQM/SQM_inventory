(function () {
  'use strict';

  // [fix F-3] window.API 즉시캡처 제거 → fetch 시점에 실시간 읽기
  function _api() { return window.SQM_API_BASE || (window.location && window.location.origin) || ''; }
  var apiGet = window.apiGet;
  var apiPost = window.apiPost;
  var extractRows = window.extractRows;
  var escapeHtml = window.escapeHtml;
  var showDataModal = window.showDataModal;
  var showToast = window.showToast;
  var _sqmSyncModalHeaderFromContent = window._sqmSyncModalHeaderFromContent;

  /* ── AI 채팅 모달 ─────────────────────────────────────── */
  function showAiChatModal() {
    var panelId = 'sqm-ai-chat-panel';
    if (document.getElementById(panelId)) {
      document.getElementById(panelId).style.display = 'flex';
      return;
    }
    var examples = ['전체 재고 현황', '제품별 재고', '저재고 LOT', '리튬카보네이트 재고', 'SAP별 현황'];
    var exBtns = examples.map(function(q) {
      return '<button type="button" class="btn btn-ghost" style="font-size:.78rem;padding:3px 8px" onclick="window._aiChatSend('+JSON.stringify(q)+')">' + escapeHtml(q) + '</button>';
    }).join('');

    var panel = document.createElement('div');
    panel.id = panelId;
    var _vw = window.innerWidth, _vh = window.innerHeight;
    panel.style.cssText = 'position:fixed;width:420px;height:520px;'
      + 'left:' + Math.max(10, _vw - 440) + 'px;top:' + Math.max(10, _vh - 540) + 'px;'
      + 'background:var(--bg-card,#1a2233);border:1px solid var(--border,#2a3a5c);border-radius:12px;'
      + 'box-shadow:0 8px 32px rgba(0,0,0,.5);display:flex;flex-direction:column;z-index:9999;overflow:hidden';
    panel.innerHTML =
      '<div style="background:var(--primary,#2563eb);padding:10px 14px;display:flex;justify-content:space-between;align-items:center">'
      + '<span style="font-weight:700;color:#fff">🤖 AI 재고 조회</span>'
      + '<div style="display:flex;gap:4px;align-items:center">'
      + '<button id="ai-detach-btn" style="background:transparent;border:1px solid rgba(255,255,255,.35);color:#fff;border-radius:4px;padding:2px 8px;cursor:pointer;font-size:13px" onclick="window._sqmDetachAiChat()" title="별도 창으로 분리">&#x29C9;</button>'
      + '<button onclick="window._aiChatClear()" style="background:transparent;border:1px solid rgba(255,255,255,.35);color:#fff;border-radius:4px;padding:2px 8px;cursor:pointer;font-size:12px" title="대화 초기화">🗑</button>'
      + '<button onclick="document.getElementById(\''+panelId+'\').style.display=\'none\'" style="background:none;border:none;color:#fff;font-size:1.2rem;cursor:pointer;line-height:1">×</button>'
      + '</div>'
      + '</div>'
      + '<div id="ai-chat-history" style="flex:1;overflow-y:auto;padding:12px;display:flex;flex-direction:column;gap:8px;min-height:200px">'
      + '<div style="color:var(--text-muted);font-size:.84rem">안녕하세요! 재고를 자연어로 질문해보세요.</div>'
      + '</div>'
      + '<div style="padding:6px 10px;border-top:1px solid var(--border,#2a3a5c);display:flex;flex-wrap:wrap;gap:4px">' + exBtns + '</div>'
      + '<div style="padding:10px;border-top:1px solid var(--border,#2a3a5c);display:flex;gap:8px">'
      + '<input id="ai-chat-input" type="text" placeholder="질문을 입력하세요..." autocomplete="off"'
      + ' style="flex:1;padding:8px 10px;background:var(--bg-hover,#0d1b2e);color:var(--text,#e2e8f0);border:1px solid var(--border,#2a3a5c);border-radius:6px;font-size:.9rem">'
      + '<button onclick="window._aiChatSend()" class="btn btn-primary" style="padding:8px 14px">전송</button>'
      + '</div>';
    document.body.appendChild(panel);

    document.getElementById('ai-chat-input').addEventListener('keydown', function(e) {
      if (e.key === 'Enter') window._aiChatSend();
    });
  }
  window.showAiChatModal = showAiChatModal;

  window._aiChatClear = function() {
    var hist = document.getElementById('ai-chat-history');
    if (hist) {
      hist.innerHTML = '<div style="color:var(--text-muted);font-size:.84rem">대화가 초기화되었습니다.</div>';
    }
    apiPost('/api/ai/chat/clear', {}).catch(function(){});
  };

  window._aiChatSend = function(preset) {
    var inp = document.getElementById('ai-chat-input');
    var msg = preset || (inp ? inp.value.trim() : '');
    if (!msg) return;
    if (inp && !preset) inp.value = '';

    var hist = document.getElementById('ai-chat-history');
    if (!hist) return;

    // 사용자 말풍선
    var uDiv = document.createElement('div');
    uDiv.style.cssText = 'align-self:flex-end;background:var(--primary,#2563eb);color:#fff;padding:7px 12px;border-radius:10px 10px 2px 10px;max-width:85%;font-size:.88rem';
    uDiv.textContent = msg;
    hist.appendChild(uDiv);

    // 로딩
    var aDiv = document.createElement('div');
    aDiv.style.cssText = 'align-self:flex-start;background:var(--bg-hover,#0d1b2e);color:var(--text,#e2e8f0);padding:7px 12px;border-radius:10px 10px 10px 2px;max-width:85%;font-size:.88rem';
    aDiv.textContent = '⏳ 조회 중…';
    hist.appendChild(aDiv);
    hist.scrollTop = hist.scrollHeight;

    apiPost('/api/ai/chat', { message: msg }).then(function(res) {
      aDiv.innerHTML = '';
      var answer = (res && res.answer) ? res.answer : '응답 없음';
      // 줄바꿈 처리
      answer.split('\n').forEach(function(line, i) {
        if (i > 0) aDiv.appendChild(document.createElement('br'));
        aDiv.appendChild(document.createTextNode(line));
      });
      if (res && res.row_count > 0) {
        var meta = document.createElement('div');
        meta.style.cssText = 'margin-top:5px;font-size:.75rem;color:var(--text-muted)';
        meta.textContent = '📊 ' + res.row_count + '건 · ' + (res.elapsed_ms||0) + 'ms';
        aDiv.appendChild(meta);
      }
      hist.scrollTop = hist.scrollHeight;
    }).catch(function(e) {
      aDiv.style.color = 'var(--danger,#f87171)';
      aDiv.textContent = '❌ 오류: ' + (e.message || String(e));
      hist.scrollTop = hist.scrollHeight;
    });
  };

  function showAiToolsHubModal() {
    var h = [
      '<div style="max-width:420px;padding:4px 0">',
      '  <h2 style="margin:0 0 12px 0">🤖 AI / 선사 도구</h2>',
      '  <p style="color:var(--text-muted);font-size:.86rem;margin-bottom:16px">자주 쓰는 항목을 모았습니다.</p>',
      '  <div style="display:flex;flex-direction:column;gap:10px">',
      '    <button type="button" class="btn btn-primary" id="aihub-chat">💬 AI 재고 채팅</button>',
      '    <button type="button" class="btn btn-primary" id="aihub-carrier">🚢 선사 프로파일 (BL 등록)</button>',
      '    <button type="button" class="btn btn-primary" id="aihub-gemini-set">🔐 Gemini API 설정</button>',
      '    <button type="button" class="btn btn-ghost" id="aihub-gemini-test">🧪 Gemini 연결 테스트</button>',
      '  </div>',
      '  <div style="margin-top:16px;text-align:right"><button type="button" class="btn btn-ghost" onclick="document.getElementById(\'sqm-modal\').style.display=\'none\'">닫기</button></div>',
      '</div>'
    ].join('\n');
    showDataModal('', h);
    document.getElementById('aihub-chat').addEventListener('click', function(){ document.getElementById('sqm-modal').style.display='none'; window.showAiChatModal(); });
    document.getElementById('aihub-carrier').addEventListener('click', function(){ document.getElementById('sqm-modal').style.display='none'; window.showCarrierProfileModal(); });
    document.getElementById('aihub-gemini-set').addEventListener('click', function(){ document.getElementById('sqm-modal').style.display='none'; window.showGeminiApiSettingsModal(); });
    document.getElementById('aihub-gemini-test').addEventListener('click', function(){ document.getElementById('sqm-modal').style.display='none'; window.showGeminiApiTestModal(); });
  }
  window.showAiToolsHubModal = showAiToolsHubModal;

  function showReportTemplatesHubModal() {
    function renderFiles(items) {
      var box = document.getElementById('rt-file-list');
      if (!box) return;
      if (!items || !items.length) {
        box.innerHTML = '<div class="empty" style="padding:12px">업로드된 양식 파일이 없습니다 (.xlsx · .pdf 등)</div>';
        return;
      }
      var tbl = '<table class="data-table"><thead><tr><th>파일명</th><th>크기</th><th>수정일</th><th></th></tr></thead><tbody>';
      items.forEach(function(it){
        var nm = it.name || '';
        tbl += '<tr><td style="font-weight:600;word-break:break-all">'+escapeHtml(nm)+'</td><td class="mono-cell">'+(it.size_bytes!=null?Math.round(it.size_bytes/1024)+' KB':'-')+'</td><td style="font-size:.82rem">'+escapeHtml(it.modified_at||'-')+'</td>'
          + '<td><button type="button" class="btn btn-ghost rt-del" style="padding:4px 8px;font-size:.8rem;color:var(--danger,#c62828)" data-enc="'+encodeURIComponent(nm)+'">삭제</button></td></tr>';
      });
      tbl += '</tbody></table>';
      box.innerHTML = tbl;
      box.querySelectorAll('.rt-del').forEach(function(btn){
        btn.addEventListener('click', async function(){
          var enc = btn.getAttribute('data-enc');
          var name = enc ? decodeURIComponent(enc) : '';
          if (!name || !(await window.sqmConfirmAsync('파일을 삭제할까요?'))) return;
          fetch(_api() + '/api/report-templates/file?name=' + encodeURIComponent(name), { method: 'DELETE' })
            .then(function(r){ return r.json(); })
            .then(function(res){
              if (res && res.ok === false) { showToast('error', res.error || '삭제 실패'); return; }
              showToast('success', '삭제됨');
              refreshList();
            }).catch(function(e){ showToast('error', String(e.message||e)); });
        });
      });
    }

    function refreshList() {
      apiGet('/api/report-templates/list').then(function(res){
        var d = res.data || res || {};
        renderFiles(d.items || []);
      }).catch(function(){
        var box = document.getElementById('rt-file-list');
        if (box) box.innerHTML = '<div class="empty">목록 조회 실패</div>';
      });
    }

    var h = [
      '<div style="max-width:520px;padding:4px 0">',
      '  <h2 style="margin:0 0 10px 0">📂 보고서 양식 · 데이터</h2>',
      '  <p style="color:var(--text-muted);font-size:.86rem;margin-bottom:12px">',
      '    <code>data/report_templates/</code> 에 보관되는 업로드 양식입니다. 일·월·재고 집계는 아래 버튼으로 확인합니다.',
      '  </p>',
      '  <div style="margin-bottom:14px;padding:12px;background:var(--bg-hover);border-radius:8px;border:1px solid var(--border)">',
      '    <div style="font-weight:600;margin-bottom:8px">양식 파일 업로드</div>',
      '    <input type="file" id="rt-file" accept=".xlsx,.xls,.pdf,.docx,.csv,.html" style="margin-bottom:8px"/>',
      '    <button type="button" class="btn btn-primary" id="rt-upload">업로드</button>',
      '  </div>',
      '  <h3 style="font-size:1rem;margin:0 0 8px">저장된 양식</h3>',
      '  <div id="rt-file-list" style="max-height:220px;overflow:auto;border:1px solid var(--border);border-radius:8px;margin-bottom:14px"><div class="empty" style="padding:12px">⏳ 로딩 중...</div></div>',
      '  <div style="display:flex;flex-direction:column;gap:8px">',
      '    <button type="button" class="btn btn-primary" id="rt-daily">📊 일일 현황 데이터</button>',
      '    <button type="button" class="btn btn-primary" id="rt-monthly">📅 월간 실적 데이터</button>',
      '    <button type="button" class="btn btn-ghost" id="rt-inv">📦 재고 현황 보고서(집계)</button>',
      '  </div>',
      '  <div style="margin-top:16px;text-align:right"><button type="button" class="btn btn-ghost" onclick="document.getElementById(\'sqm-modal\').style.display=\'none\'">닫기</button></div>',
      '</div>'
    ].join('\n');
    showDataModal('', h);
    document.getElementById('rt-daily').addEventListener('click', function(){ document.getElementById('sqm-modal').style.display='none'; window.renderInfoModal('일일 보고서', '/api/q2/report-daily'); });
    document.getElementById('rt-monthly').addEventListener('click', function(){ document.getElementById('sqm-modal').style.display='none'; window.renderInfoModal('월간 보고서', '/api/q2/report-monthly'); });
    document.getElementById('rt-inv').addEventListener('click', function(){ document.getElementById('sqm-modal').style.display='none'; window.renderInfoModal('재고 현황 보고서', '/api/q/inventory-report'); });
    document.getElementById('rt-upload').addEventListener('click', function(){
      var fi = document.getElementById('rt-file');
      if (!fi || !fi.files || !fi.files[0]) { showToast('warning', '파일을 선택하세요'); return; }
      var fd = new FormData();
      fd.append('file', fi.files[0]);
      fetch(_api() + '/api/report-templates/upload', { method: 'POST', body: fd })
        .then(function(r){ return r.json(); })
        .then(function(res){
          if (res && res.ok === false) { showToast('error', res.error || '업로드 실패'); return; }
          showToast('success', res.message || '업로드 완료');
          fi.value = '';
          refreshList();
        }).catch(function(e){ showToast('error', String(e.message||e)); });
    });
    refreshList();
  }
  window.showReportTemplatesHubModal = showReportTemplatesHubModal;

  function showTemplateReportModal(reportType) {
    var meta = {
      outbound_report: {
        title: '📤 Outbound Report',
        desc: 'SOLD 데이터를 Outbound Report Excel 양식에 채워 생성합니다.',
        endpoint: '/api/q3/outbound-report-excel'
      },
      sales_order_dn: {
        title: '📋 Sales Order DN',
        desc: 'Sales Order DN 데이터를 템플릿 Excel 양식에 채워 생성합니다.',
        endpoint: '/api/q3/sales-order-dn-report-excel'
      },
      export_work_report: {
        title: '🚢 수출 작업 리포트',
        desc: '컨테이너별 LOT/샘플 작업 리스트를 Excel 양식에 채워 생성합니다.',
        endpoint: '/api/q3/export-work-report-excel'
      },
      storage_confirmation: {
        title: '🏷️ Storage Confirmation',
        desc: '재고/컨테이너 데이터를 Storage Confirmation Excel 양식에 채워 생성합니다.',
        endpoint: '/api/q3/storage-confirmation-excel'
      },
      sold_inventory_report: {
        title: '📦 SOLD Inventory Report',
        desc: 'SOLD 재고 데이터를 재고관리파일 SOLD 양식에 채워 생성합니다.',
        endpoint: '/api/q3/sold-inventory-report-excel'
      }
    }[reportType];
    if (!meta) {
      showToast('error', '알 수 없는 보고서 유형');
      return;
    }
    var columnState = [];
    var fieldOptions = [];
    var hasDateRange = reportType === 'outbound_report' || reportType === 'sales_order_dn' || reportType === 'storage_confirmation' || reportType === 'sold_inventory_report';
    var selectedContainers = [];

    function queryParams() {
      var sel = document.getElementById('tr-template');
      var ft = document.getElementById('tr-filter-type');
      var fv = document.getElementById('tr-filter-select');
      var sd = document.getElementById('tr-start-date');
      var ed = document.getElementById('tr-end-date');
      var p = 'template=' + encodeURIComponent(sel && sel.value ? sel.value : 'template_1')
        + '&filter_type=' + encodeURIComponent(ft && ft.value ? ft.value : 'all')
        + '&filter_value=' + encodeURIComponent(fv && fv.value ? fv.value : '');
      if (ft && ft.value === 'container_no' && selectedContainers.length) {
        p += '&filter_values=' + encodeURIComponent(selectedContainers.join(','));
      }
      if (hasDateRange) {
        p += '&start_date=' + encodeURIComponent(sd && sd.value ? sd.value : '')
          + '&end_date=' + encodeURIComponent(ed && ed.value ? ed.value : '');
      }
      return p;
    }

    function setGenerateNeedsPreview() {
      var btn = document.getElementById('tr-generate');
      if (btn) btn.disabled = true;
      var box = document.getElementById('tr-preview-box');
      if (box) box.textContent = '미리보기 후 Excel 생성이 가능합니다.';
    }

    function fieldLabel(field) {
      var hit = fieldOptions.find(function(f) { return f.field === field; });
      return hit ? hit.label : field;
    }

    function saveColumns() {
      var sel = document.getElementById('tr-template');
      var tmpl = sel && sel.value ? sel.value : 'template_1';
      return fetch(_api() + '/api/q3/report-template-columns?report_type=' + encodeURIComponent(reportType) + '&template=' + encodeURIComponent(tmpl), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ columns: columnState })
      }).then(function(r) { return r.json(); }).then(function(res) {
        if (res && res.ok === false) throw new Error(res.error || '컬럼 저장 실패');
        setGenerateNeedsPreview();
        return res;
      });
    }

    function renderHeaders(info) {
      var box = document.getElementById('tr-header-map');
      if (!box) return;
      fieldOptions = (info && info.available_fields) || [];
      columnState = ((info && info.columns) || []).map(function(c) {
        return { header: c.header || fieldLabel(c.field), field: c.field || '', enabled: c.enabled !== false };
      });
      if (!columnState.length) {
        box.innerHTML = '<div class="empty" style="padding:10px">컬럼 정보를 찾지 못했습니다.</div>';
        return;
      }
      var options = fieldOptions.map(function(f) {
        return '<option value="' + escapeHtml(f.field) + '">' + escapeHtml(f.label || f.field) + '</option>';
      }).join('');
      var html = '<div style="padding:10px;display:flex;gap:8px;align-items:center;flex-wrap:wrap;border-bottom:1px solid var(--border)">'
        + '<select id="tr-add-field" style="min-width:220px;padding:6px;background:var(--panel);color:var(--text);border:1px solid var(--border);border-radius:6px">' + options + '</select>'
        + '<button class="btn" id="tr-add-column">컬럼 추가</button>'
        + '<span style="font-size:12px;color:var(--text-muted)">체크 해제는 출력 제외, 위/아래 버튼은 위치 변경입니다.</span>'
        + '</div>';
      html += '<table class="data-table"><thead><tr><th>사용</th><th>출력 헤더명</th><th>DB 입력값</th><th>위치</th><th>삭제</th></tr></thead><tbody>';
      columnState.forEach(function(c, idx) {
        var rowOptions = fieldOptions.map(function(f) {
          return '<option value="' + escapeHtml(f.field) + '"' + (f.field === c.field ? ' selected' : '') + '>' + escapeHtml(f.label || f.field) + '</option>';
        }).join('');
        html += '<tr data-idx="' + idx + '" draggable="true" style="cursor:move">'
          + '<td><input type="checkbox" class="tr-col-enabled" ' + (c.enabled ? 'checked' : '') + '></td>'
          + '<td><input class="tr-col-header" value="' + escapeHtml(c.header || '') + '" style="width:100%;box-sizing:border-box;padding:5px;background:var(--panel);color:var(--text);border:1px solid var(--border);border-radius:5px"></td>'
          + '<td><select class="tr-col-field" style="width:100%;padding:5px;background:var(--panel);color:var(--text);border:1px solid var(--border);border-radius:5px">' + rowOptions + '</select></td>'
          + '<td style="white-space:nowrap"><button class="btn btn-small tr-col-up" ' + (idx === 0 ? 'disabled' : '') + '>↑</button> <button class="btn btn-small tr-col-down" ' + (idx === columnState.length - 1 ? 'disabled' : '') + '>↓</button></td>'
          + '<td><button class="btn btn-small tr-col-remove">삭제</button></td>'
          + '</tr>';
      });
      html += '</tbody></table>';
      if (info.block_title_mapping) {
        html += '<div style="font-size:12px;color:var(--text-muted);margin-top:8px">블록 제목: 컨테이너번호 / Seal No / Size Type(없으면 20FT)</div>';
      }
      box.innerHTML = html;
      bindColumnEditor();
    }

    function bindColumnEditor() {
      var box = document.getElementById('tr-header-map');
      if (!box) return;
      box.querySelectorAll('tbody tr').forEach(function(row) {
        var idx = Number(row.getAttribute('data-idx'));
        row.addEventListener('dragstart', function(e) {
          e.dataTransfer.setData('text/plain', String(idx));
        });
        row.addEventListener('dragover', function(e) {
          e.preventDefault();
        });
        row.addEventListener('drop', function(e) {
          e.preventDefault();
          var from = Number(e.dataTransfer.getData('text/plain'));
          var to = Number(row.getAttribute('data-idx'));
          if (!Number.isFinite(from) || !Number.isFinite(to) || from === to) return;
          var moved = columnState.splice(from, 1)[0];
          columnState.splice(to, 0, moved);
          saveColumns().then(analyzeTemplate).catch(function(err) { showToast('error', err.message || String(err)); });
        });
        var enabled = row.querySelector('.tr-col-enabled');
        var header = row.querySelector('.tr-col-header');
        var field = row.querySelector('.tr-col-field');
        if (enabled) enabled.addEventListener('change', function() {
          columnState[idx].enabled = enabled.checked;
          saveColumns().catch(function(e) { showToast('error', e.message || String(e)); });
        });
        if (header) header.addEventListener('change', function() {
          columnState[idx].header = header.value;
          saveColumns().catch(function(e) { showToast('error', e.message || String(e)); });
        });
        if (field) field.addEventListener('change', function() {
          columnState[idx].field = field.value;
          if (!columnState[idx].header) columnState[idx].header = fieldLabel(field.value);
          saveColumns().then(analyzeTemplate).catch(function(e) { showToast('error', e.message || String(e)); });
        });
        var up = row.querySelector('.tr-col-up');
        var down = row.querySelector('.tr-col-down');
        var remove = row.querySelector('.tr-col-remove');
        if (up) up.addEventListener('click', function() {
          if (idx <= 0) return;
          var t = columnState[idx - 1];
          columnState[idx - 1] = columnState[idx];
          columnState[idx] = t;
          saveColumns().then(analyzeTemplate).catch(function(e) { showToast('error', e.message || String(e)); });
        });
        if (down) down.addEventListener('click', function() {
          if (idx >= columnState.length - 1) return;
          var t = columnState[idx + 1];
          columnState[idx + 1] = columnState[idx];
          columnState[idx] = t;
          saveColumns().then(analyzeTemplate).catch(function(e) { showToast('error', e.message || String(e)); });
        });
        if (remove) remove.addEventListener('click', function() {
          columnState.splice(idx, 1);
          saveColumns().then(analyzeTemplate).catch(function(e) { showToast('error', e.message || String(e)); });
        });
      });
      var add = document.getElementById('tr-add-column');
      if (add) add.addEventListener('click', function() {
        var sel = document.getElementById('tr-add-field');
        var field = sel && sel.value ? sel.value : '';
        if (!field) return;
        columnState.push({ header: fieldLabel(field), field: field, enabled: true });
        saveColumns().then(analyzeTemplate).catch(function(e) { showToast('error', e.message || String(e)); });
      });
    }

    function loadFilterValues() {
      var type = document.getElementById('tr-filter-type');
      var sel = document.getElementById('tr-filter-select');
      if (!type || !sel) return;
      sel.innerHTML = '<option value="">목록 불러오는 중...</option>';
      apiGet('/api/q3/report-filter-values?report_type=' + encodeURIComponent(reportType) + '&filter_type=' + encodeURIComponent(type.value || 'all'), { noCache: true })
        .then(function(res) {
          var d = res.data || res || {};
          var values = d.values || d.items || [];
          sel.innerHTML = '<option value="">전체</option>' + values.map(function(v) {
            return '<option value="' + escapeHtml(v) + '">' + escapeHtml(v) + '</option>';
          }).join('');
        }).catch(function() {
          sel.innerHTML = '<option value="">목록 조회 실패</option>';
        });
    }

    function syncContainerPickerVisibility() {
      var type = document.getElementById('tr-filter-type');
      var box = document.getElementById('tr-container-picker');
      if (!type || !box) return;
      box.style.display = type.value === 'container_no' ? 'block' : 'none';
    }

    function renderSelectedContainers() {
      var box = document.getElementById('tr-container-list');
      if (!box) return;
      if (!selectedContainers.length) {
        box.innerHTML = '<div class="empty" style="padding:8px">선택된 컨테이너가 없습니다.</div>';
        return;
      }
      box.innerHTML = '<table class="data-table" style="font-size:12px"><thead><tr><th>순번</th><th>컨테이너 No</th><th>조작</th></tr></thead><tbody>'
        + selectedContainers.map(function(v, idx) {
          return '<tr data-idx="' + idx + '"><td>' + (idx + 1) + '</td><td class="mono-cell">' + escapeHtml(v) + '</td>'
            + '<td><button class="btn btn-small tr-container-up" ' + (idx === 0 ? 'disabled' : '') + '>↑</button> '
            + '<button class="btn btn-small tr-container-down" ' + (idx === selectedContainers.length - 1 ? 'disabled' : '') + '>↓</button> '
            + '<button class="btn btn-small tr-container-remove">삭제</button></td></tr>';
        }).join('') + '</tbody></table>';
      box.querySelectorAll('tbody tr').forEach(function(row) {
        var idx = Number(row.getAttribute('data-idx'));
        var up = row.querySelector('.tr-container-up');
        var down = row.querySelector('.tr-container-down');
        var remove = row.querySelector('.tr-container-remove');
        if (up) up.addEventListener('click', function() {
          if (idx <= 0) return;
          var t = selectedContainers[idx - 1];
          selectedContainers[idx - 1] = selectedContainers[idx];
          selectedContainers[idx] = t;
          setGenerateNeedsPreview();
          renderSelectedContainers();
        });
        if (down) down.addEventListener('click', function() {
          if (idx >= selectedContainers.length - 1) return;
          var t = selectedContainers[idx + 1];
          selectedContainers[idx + 1] = selectedContainers[idx];
          selectedContainers[idx] = t;
          setGenerateNeedsPreview();
          renderSelectedContainers();
        });
        if (remove) remove.addEventListener('click', function() {
          selectedContainers.splice(idx, 1);
          setGenerateNeedsPreview();
          renderSelectedContainers();
        });
      });
    }

    function renderAllocationValidation(v) {
      if (!v || !v.issues || !v.issues.length) return '';
      var level = v.level || 'ok';
      var color = level === 'error' ? 'var(--danger)' : (level === 'warning' ? 'var(--warning)' : 'var(--success,#22c55e)');
      var title = level === 'ok' ? 'Allocation 매칭 정상' : 'Allocation 매칭 확인 필요';
      return '<details open style="margin-top:8px;border:1px solid ' + color + ';border-radius:6px;padding:8px 10px;background:var(--bg-hover)">'
        + '<summary style="cursor:pointer;font-weight:700;color:' + color + '">' + escapeHtml(title) + ' (' + v.issues.length + '건)</summary>'
        + '<ul style="margin:8px 0 0 18px;padding:0;font-size:12px;color:var(--text-muted)">'
        + v.issues.slice(0, 20).map(function(it) { return '<li>' + escapeHtml(it.message || it.code || '') + '</li>'; }).join('')
        + '</ul></details>';
    }

    function analyzeTemplate() {
      var sel = document.getElementById('tr-template');
      var tmpl = sel && sel.value ? sel.value : 'template_1';
      apiGet('/api/q3/report-template-analyze?report_type=' + encodeURIComponent(reportType) + '&template=' + encodeURIComponent(tmpl), { noCache: true })
        .then(function(res) {
          var d = res.data || res || {};
          renderHeaders(d);
        }).catch(function() {
          var box = document.getElementById('tr-header-map');
          if (box) box.innerHTML = '<div class="empty">템플릿 분석 실패</div>';
        });
    }

    function previewTemplateFile() {
      var sel = document.getElementById('tr-template');
      var tmpl = sel && sel.value ? sel.value : 'template_1';
      var box = document.getElementById('tr-template-preview-box');
      if (!box) return;
      box.innerHTML = '<div class="empty" style="padding:10px">템플릿 미리보기 로딩 중...</div>';
      apiGet('/api/q3/report-template-preview?report_type=' + encodeURIComponent(reportType) + '&template=' + encodeURIComponent(tmpl), { noCache: true })
        .then(function(res) {
          var d = res.data || res || {};
          var rows = d.rows || [];
          if (!rows.length) {
            box.innerHTML = '<div class="empty" style="padding:10px">미리볼 셀이 없습니다.</div>';
            return;
          }
          var html = '<div style="padding:8px;font-size:12px;color:var(--text-muted);border-bottom:1px solid var(--border)">'
            + escapeHtml(d.display_name || tmpl) + ' · Sheet: ' + escapeHtml(d.sheet || '-') + '</div>';
          html += '<div style="overflow:auto;max-height:240px"><table class="data-table" style="font-size:12px"><tbody>';
          rows.forEach(function(row) {
            html += '<tr>' + row.map(function(v) {
              return '<td style="min-width:80px;max-width:220px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">' + escapeHtml(v || '') + '</td>';
            }).join('') + '</tr>';
          });
          html += '</tbody></table></div>';
          box.innerHTML = html;
        }).catch(function(e) {
          box.innerHTML = '<div class="empty" style="padding:10px">템플릿 미리보기 실패: ' + escapeHtml(e.message || String(e)) + '</div>';
        });
    }

    function refreshTemplates() {
      apiGet('/api/q3/report-templates?report_type=' + encodeURIComponent(reportType), { noCache: true }).then(function(res) {
        var d = res.data || res || {};
        var items = d.items || [];
        var sel = document.getElementById('tr-template');
        var list = document.getElementById('tr-template-list');
        if (!sel || !list) return;
        if (!items.length) {
          sel.innerHTML = '<option value="">저장된 템플릿 없음</option>';
          list.innerHTML = '<div class="empty" style="padding:10px">저장된 템플릿이 없습니다.</div>';
          return;
        }
        sel.innerHTML = items.map(function(it) {
          return '<option value="' + escapeHtml(it.name) + '">' + escapeHtml(it.display_name || it.name) + ' (' + escapeHtml(it.name) + ')</option>';
        }).join('');
        list.innerHTML = '<table class="data-table"><thead><tr><th>템플릿</th><th>크기</th><th>수정일</th></tr></thead><tbody>'
          + items.map(function(it) {
            return '<tr><td><b>' + escapeHtml(it.display_name || it.name) + '</b><br><span class="mono-cell" style="font-size:11px;color:var(--text-muted)">' + escapeHtml(it.name) + '</span></td><td>' + Math.round((it.size_bytes || 0) / 1024) + ' KB</td><td>' + escapeHtml(it.modified_at || '-') + '</td></tr>';
          }).join('')
          + '</tbody></table>';
        analyzeTemplate();
      }).catch(function(e) {
        var list = document.getElementById('tr-template-list');
        if (list) list.innerHTML = '<div class="empty">템플릿 목록 조회 실패</div>';
      });
    }

    var h = [
      '<div style="max-width:780px;padding:4px 0">',
      '  <h2 style="margin:0 0 8px 0">' + meta.title + '</h2>',
      '  <p style="color:var(--text-muted);font-size:.86rem;margin-bottom:12px">' + meta.desc + '</p>',
      '  <div style="display:flex;gap:8px;align-items:center;margin-bottom:10px;flex-wrap:wrap">',
      '    <label style="font-size:12px;color:var(--text-muted)">템플릿</label>',
      '    <select id="tr-template" style="min-width:260px;padding:6px;background:var(--bg-hover);color:var(--text);border:1px solid var(--border);border-radius:6px"></select>',
      '    <button class="btn" id="tr-template-preview">템플릿 미리보기</button>',
      '    <button class="btn" id="tr-template-open">원본 Excel 열기</button>',
      '    <button class="btn" id="tr-delete-template">템플릿 삭제</button>',
      '  </div>',
      '  <div id="tr-template-preview-box" style="display:none;max-height:280px;overflow:auto;border:1px solid var(--border);border-radius:8px;margin-bottom:12px"></div>',
      '  <div id="tr-header-map" style="max-height:190px;overflow:auto;border:1px solid var(--border);border-radius:8px;margin-bottom:12px"><div class="empty" style="padding:10px">템플릿 분석 중...</div></div>',
      '  <div style="border:1px solid var(--border);border-radius:8px;padding:12px;margin-bottom:12px;background:var(--bg-hover)">',
      '    <div style="font-weight:600;margin-bottom:8px">데이터 범위 선택</div>',
      '    <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:8px">',
      '      <select id="tr-filter-type" style="padding:6px;background:var(--panel);color:var(--text);border:1px solid var(--border);border-radius:6px">',
      '        <option value="all">전체</option>',
      (reportType === 'storage_confirmation'
        ? '        <option value="sap_no">SAP NO</option><option value="lot_no">LOT NO</option><option value="container_no">CONT NO</option><option value="bl_no">BL NO</option><option value="part_no">PART NO</option>'
        : reportType === 'sold_inventory_report'
        ? '        <option value="sap_no">SAP NO</option><option value="lot_no">Lot No</option><option value="sold_to">SOLD TO</option><option value="sale_ref">SALE REF</option><option value="salar_invoice_no">Salar Invoice no.</option><option value="product">Product</option>'
        : hasDateRange
        ? '        <option value="sales_order_no">Sales Order No</option><option value="customer">고객사</option><option value="bl_no">BL No</option><option value="container_no">컨테이너 No</option><option value="lot_no">LOT No</option><option value="picking_no">Picking No</option>'
        : '        <option value="container_no">컨테이너 No</option><option value="lot_no">LOT No</option><option value="seal_no">Seal No</option><option value="size_type">컨테이너 Size</option>'),
      '      </select>',
      '      <select id="tr-filter-select" style="min-width:220px;padding:6px;background:var(--panel);color:var(--text);border:1px solid var(--border);border-radius:6px"><option value="">목록 불러오는 중...</option></select>',
      (hasDateRange
        ? '      <input type="date" id="tr-start-date" style="padding:6px;background:var(--panel);color:var(--text);border:1px solid var(--border);border-radius:6px"><span>~</span><input type="date" id="tr-end-date" style="padding:6px;background:var(--panel);color:var(--text);border:1px solid var(--border);border-radius:6px">'
        : '      <input type="hidden" id="tr-start-date"><input type="hidden" id="tr-end-date">'),
      '    </div>',
      '    <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">',
      '      <button class="btn" id="tr-preview">미리보기</button>',
      '      <button class="btn btn-primary" id="tr-generate" disabled>Excel 생성</button>',
      '    </div>',
      '    <div id="tr-container-picker" style="display:none;margin-top:8px;border-top:1px solid var(--border);padding-top:8px">',
      '      <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:8px">',
      '        <button class="btn" id="tr-add-container">선택 컨테이너 추가</button>',
      '        <button class="btn" id="tr-clear-containers">선택 목록 비우기</button>',
      '        <span style="font-size:12px;color:var(--text-muted)">아래 순번대로 보고서에 출력됩니다.</span>',
      '      </div>',
      '      <div id="tr-container-list"><div class="empty" style="padding:8px">선택된 컨테이너가 없습니다.</div></div>',
      '    </div>',
      '    <div id="tr-preview-box" style="margin-top:10px;font-size:12px;color:var(--text-muted)">미리보기 후 Excel 생성이 가능합니다.</div>',
      '  </div>',
      '  <div style="border:1px solid var(--border);border-radius:8px;padding:12px;margin-bottom:12px;background:var(--bg-hover)">',
      '    <div style="font-weight:600;margin-bottom:8px">템플릿 업로드</div>',
      '    <select id="tr-upload-mode" style="display:block;width:100%;box-sizing:border-box;margin-bottom:8px;padding:6px;background:var(--panel);color:var(--text);border:1px solid var(--border);border-radius:6px">',
      '      <option value="add">새 템플릿으로 추가</option>',
      '      <option value="update_current">현재 선택한 템플릿 업데이트</option>',
      '      <option value="update_default">기본 템플릿 업데이트</option>',
      '    </select>',
      '    <input id="tr-template-name" placeholder="사용자 템플릿 이름" style="display:block;width:100%;box-sizing:border-box;margin-bottom:8px;padding:6px;background:var(--panel);color:var(--text);border:1px solid var(--border);border-radius:6px">',
      '    <input type="file" id="tr-file" accept=".xlsx" style="margin-bottom:8px">',
      '    <button class="btn" id="tr-upload">업로드 후 저장</button>',
      '  </div>',
      '  <div id="tr-template-list" style="max-height:210px;overflow:auto;border:1px solid var(--border);border-radius:8px"><div class="empty" style="padding:10px">로딩 중...</div></div>',
      '  <div style="margin-top:16px;text-align:right"><button type="button" class="btn btn-ghost" onclick="document.getElementById(\'sqm-modal\').style.display=\'none\'">닫기</button></div>',
      '</div>'
    ].join('\n');
    showDataModal('', h);

    document.getElementById('tr-template').addEventListener('change', function(){
      setGenerateNeedsPreview();
      var pv = document.getElementById('tr-template-preview-box');
      if (pv) {
        pv.style.display = 'none';
        pv.innerHTML = '';
      }
      analyzeTemplate();
    });
    document.getElementById('tr-template-preview').addEventListener('click', function(){
      var pv = document.getElementById('tr-template-preview-box');
      if (!pv) return;
      if (pv.style.display === 'none' || !pv.style.display) {
        pv.style.display = 'block';
        previewTemplateFile();
      } else {
        pv.style.display = 'none';
      }
    });
    document.getElementById('tr-template-open').addEventListener('click', function(){
      var sel = document.getElementById('tr-template');
      var tmpl = sel && sel.value ? sel.value : 'template_1';
      fetch(_api() + '/api/q3/report-template-open?report_type=' + encodeURIComponent(reportType) + '&template=' + encodeURIComponent(tmpl), { method: 'POST' })
        .then(function(r) { return r.json(); })
        .then(function(res) {
          if (res && res.ok === false) {
            showToast('error', res.error || res.message || '원본 Excel 열기 실패');
            return;
          }
          showToast('success', (res && res.message) || '원본 Excel 파일을 열었습니다');
        }).catch(function(e) {
          showToast('error', String(e.message || e));
        });
    });
    document.getElementById('tr-filter-type').addEventListener('change', function() {
      selectedContainers = [];
      renderSelectedContainers();
      syncContainerPickerVisibility();
      setGenerateNeedsPreview();
      loadFilterValues();
    });
    document.getElementById('tr-filter-select').addEventListener('change', function() {
      setGenerateNeedsPreview();
    });
    document.getElementById('tr-add-container').addEventListener('click', function() {
      var sel = document.getElementById('tr-filter-select');
      var val = sel && sel.value ? sel.value : '';
      if (!val) {
        showToast('warning', '추가할 컨테이너를 선택하세요');
        return;
      }
      if (selectedContainers.indexOf(val) >= 0) {
        showToast('info', '이미 선택된 컨테이너입니다');
        return;
      }
      selectedContainers.push(val);
      setGenerateNeedsPreview();
      renderSelectedContainers();
    });
    document.getElementById('tr-clear-containers').addEventListener('click', function() {
      selectedContainers = [];
      setGenerateNeedsPreview();
      renderSelectedContainers();
    });
    document.getElementById('tr-delete-template').addEventListener('click', async function() {
      var sel = document.getElementById('tr-template');
      var tmpl = sel && sel.value ? sel.value : '';
      if (!tmpl) {
        showToast('warning', '삭제할 템플릿이 없습니다');
        return;
      }
      var deleteMsg = tmpl === 'template_1'
        ? '기본 템플릿입니다. 삭제하면 기본 양식을 다시 쓰려면 파일을 다시 업로드해야 합니다. 삭제할까요?'
        : '현재 선택한 템플릿을 삭제할까요?';
      if (!await window.sqmConfirmAsync(deleteMsg)) return;
      fetch(_api() + '/api/q3/report-template?report_type=' + encodeURIComponent(reportType) + '&template=' + encodeURIComponent(tmpl), { method: 'DELETE' })
        .then(function(r) { return r.json(); })
        .then(function(res) {
          if (res && res.ok === false) {
            showToast('error', res.error || '템플릿 삭제 실패');
            return;
          }
          showToast('success', res.message || '템플릿 삭제 완료');
          refreshTemplates();
        }).catch(function(e) { showToast('error', String(e.message || e)); });
    });
    document.getElementById('tr-preview').addEventListener('click', function() {
      var url = '/api/q3/report-preview?report_type=' + encodeURIComponent(reportType)
        + '&filter_type=' + encodeURIComponent(document.getElementById('tr-filter-type').value || 'all')
        + '&filter_value=' + encodeURIComponent(document.getElementById('tr-filter-select').value || '')
        + '&filter_values=' + encodeURIComponent((document.getElementById('tr-filter-type').value === 'container_no' && selectedContainers.length) ? selectedContainers.join(',') : '')
        + '&start_date=' + encodeURIComponent(document.getElementById('tr-start-date').value || '')
        + '&end_date=' + encodeURIComponent(document.getElementById('tr-end-date').value || '');
      apiGet(url, { noCache: true }).then(function(res) {
        var d = res.data || res || {};
        var s = d.summary || {};
        var msg = (reportType === 'storage_confirmation' || reportType === 'sold_inventory_report')
          ? ('대상 ' + (s.rows||0) + '행 · LOT ' + (s.lots||0) + '개 · QTY ' + (s.qty_mt||0) + ' MT · Picked ' + (s.picked_up_qty_mt||0) + ' MT')
          : hasDateRange
          ? ('대상 ' + (s.rows||0) + '행 · LOT ' + (s.lots||0) + '개 · 본품 ' + (s.normal_rows||0) + '행 · 샘플 ' + (s.sample_rows||0) + '행 · NW ' + (s.nw_mt||0) + ' MT · GW ' + (s.gw_mt||0) + ' MT')
          : ('컨테이너 ' + (s.containers||0) + '개 · LOT ' + (s.lots||0) + '개 · 본품 ' + (s.normal_qty||0) + '개 · 샘플 ' + (s.sample_qty||0) + '개 · NW ' + (s.nw_mt||0) + ' MT · GW ' + (s.gw_mt||0) + ' MT');
        document.getElementById('tr-preview-box').innerHTML = '<b style="color:var(--success,#22c55e)">' + escapeHtml(msg) + '</b>' + renderAllocationValidation(d.allocation_validation);
        document.getElementById('tr-generate').disabled = false;
      }).catch(function(e) {
        document.getElementById('tr-preview-box').textContent = '미리보기 실패: ' + (e.message || String(e));
        document.getElementById('tr-generate').disabled = true;
      });
    });
    document.getElementById('tr-generate').addEventListener('click', function() {
      window.sqmDownloadFileUrl(API + meta.endpoint + '?' + queryParams(), meta.title);
    });
    document.getElementById('tr-upload').addEventListener('click', async function() {
      var fi = document.getElementById('tr-file');
      if (!fi || !fi.files || !fi.files[0]) {
        showToast('warning', 'xlsx 파일을 선택하세요');
        return;
      }
      var name = document.getElementById('tr-template-name');
      var mode = document.getElementById('tr-upload-mode');
      var tmpl = document.getElementById('tr-template');
      var modeVal = mode && mode.value ? mode.value : 'add';
      var tmplVal = tmpl && tmpl.value ? tmpl.value : '';
      if (modeVal === 'update_current' && !tmplVal) {
        showToast('warning', '업데이트할 현재 템플릿을 선택하세요');
        return;
      }
      if (modeVal === 'update_current' && !await window.sqmConfirmAsync('현재 선택한 템플릿을 새 파일로 업데이트할까요? 기존 템플릿 파일 내용은 교체됩니다.')) return;
      if (modeVal === 'update_default' && !await window.sqmConfirmAsync('기본 템플릿(template_1)을 새 파일로 업데이트할까요? 기존 기본 양식 파일 내용은 교체됩니다.')) return;
      var fd = new FormData();
      fd.append('file', fi.files[0]);
      fetch(_api() + '/api/q3/report-template-upload?report_type=' + encodeURIComponent(reportType)
          + '&display_name=' + encodeURIComponent(name && name.value ? name.value : '')
          + '&mode=' + encodeURIComponent(modeVal)
          + '&template=' + encodeURIComponent(tmplVal), { method: 'POST', body: fd })
        .then(function(r) { return r.json(); })
        .then(function(res) {
          if (res && res.ok === false) {
            showToast('error', res.error || '업로드 실패');
            return;
          }
          showToast('success', res.message || '템플릿 저장 완료');
          fi.value = '';
          if (name) name.value = '';
          refreshTemplates();
        }).catch(function(e) { showToast('error', String(e.message || e)); });
    });
    refreshTemplates();
    loadFilterValues();
    syncContainerPickerVisibility();
    renderSelectedContainers();
  }
  window.showTemplateReportModal = showTemplateReportModal;

  function showReportHistoryAuditModal() {
    showDataModal('📋 보고서·작업 이력', '<div style="padding:20px;text-align:center">⏳ 로딩 중...</div>');
    apiGet('/api/q/audit-log?limit=150').then(function(res){
      var rows = extractRows(res);
      if (!rows.length) {
        document.getElementById('sqm-modal-content').innerHTML = '<h2>📋 보고서·작업 이력</h2><div class="empty">감사 로그가 없습니다</div>';
        _sqmSyncModalHeaderFromContent();
        return;
      }
      var prefer = rows.filter(function(r){
        var t = ((r.event_type || '') + ' ' + (String(r.event_data || ''))).toUpperCase();
        return t.indexOf('PDF') >= 0 || t.indexOf('REPORT') >= 0 || t.indexOf('SOLD') >= 0 || t.indexOf('INBOUND') >= 0;
      });
      var show = prefer.length ? prefer.slice(0, 80) : rows.slice(0, 80);
      var tbl = '<table class="data-table"><thead><tr><th>시간</th><th>유형</th><th>요약</th></tr></thead><tbody>';
      show.forEach(function(r){
        var ts = escapeHtml(r.created_at || r.ts || '-');
        var et = escapeHtml(r.event_type || '-');
        var ed = r.event_data != null ? String(r.event_data) : '';
        if (ed.length > 120) ed = ed.slice(0, 117) + '…';
        tbl += '<tr><td style="white-space:nowrap;font-size:.82rem">' + ts + '</td><td><span class="tag">' + et + '</span></td><td style="font-size:.82rem;max-width:280px;word-break:break-all">' + escapeHtml(ed) + '</td></tr>';
      });
      tbl += '</tbody></table>';
      document.getElementById('sqm-modal-content').innerHTML = [
        '<h2 style="margin-bottom:8px">📋 보고서·작업 이력</h2>',
        '<p style="color:var(--text-muted);font-size:.85rem;margin-bottom:10px">audit_log 기준 최근 ' + show.length + '건 (PDF·보고서·입출고 관련 우선 표시)</p>',
        tbl
      ].join('');
      _sqmSyncModalHeaderFromContent();
    }).catch(function(e){
      document.getElementById('sqm-modal-content').innerHTML = '<h2>이력</h2><div class="empty">조회 실패</div>';
      _sqmSyncModalHeaderFromContent();
    });
  }
  window.showReportHistoryAuditModal = showReportHistoryAuditModal;

  function renderInfoModal(title, endpoint) {
    showDataModal(title,'<div style="padding:20px;text-align:center">⏳ 로딩 중...</div>');
    apiGet(endpoint).then(function(res){
      var d=res.data||res||{};
      var html;
      if (endpoint === '/api/info/version') {
        var note = d.build_note ? String(d.build_note).split('\n').slice(0, 18).join('\n') : '';
        html = ''
          + '<div class="metrics-grid" style="grid-template-columns:repeat(2,minmax(180px,1fr));margin-bottom:14px">'
          + '<div class="metric-card"><div class="metric-label">프로그램</div><div class="metric-value" style="font-size:1.15rem">' + escapeHtml(d.app_name || 'SQM 재고관리 시스템') + '</div></div>'
          + '<div class="metric-card"><div class="metric-label">버전</div><div class="metric-value" style="font-size:1.4rem">v' + escapeHtml(d.version || '-') + '</div></div>'
          + '<div class="metric-card"><div class="metric-label">릴리즈 날짜</div><div class="metric-value" style="font-size:1rem">' + escapeHtml(d.release_date || '-') + '</div></div>'
          + '<div class="metric-card"><div class="metric-label">빌드 날짜</div><div class="metric-value" style="font-size:1rem">' + escapeHtml(d.build_date || '-') + '</div></div>'
          + '</div>';
        if (note) {
          html += '<h3 style="margin:10px 0 8px">변경 요약</h3><pre style="white-space:pre-wrap;max-height:260px;overflow:auto;background:var(--bg-muted,#f6f8fa);border:1px solid var(--panel-border);border-radius:8px;padding:12px;font-size:.86rem;line-height:1.5">' + escapeHtml(note) + '</pre>';
        }
      } else if (typeof d==='string') {
        html='<pre style="white-space:pre-wrap;font-size:.9rem">'+escapeHtml(d)+'</pre>';
      } else if (Array.isArray(d)) {
        html='<table class="data-table"><tbody>'+d.map(function(row){
          if (typeof row==='object'&&row!==null)
            return '<tr>'+Object.values(row).map(function(v){ return '<td>'+escapeHtml(String(v))+'</td>'; }).join('')+'</tr>';
          return '<tr><td>'+escapeHtml(String(row))+'</td></tr>';
        }).join('')+'</tbody></table>';
      } else {
        // v868 fix (2026-05-15): 객체/배열을 [object Object]로 표시하던 버그 수정
        // issues(배열), stats(객체) 등 중첩 데이터를 보기 좋게 포맷
        var _fmtVal = function(v) {
          if (v === null || v === undefined) return '-';
          if (Array.isArray(v)) {
            if (v.length === 0) return '(빈 배열)';
            // 배열 안이 객체면 nested table, 원시값이면 콤마 join
            if (typeof v[0] === 'object' && v[0] !== null) {
              var keys = Object.keys(v[0]);
              var head = '<thead><tr>'+keys.map(function(k){return '<th style="font-size:.8rem;padding:4px 8px">'+escapeHtml(k)+'</th>';}).join('')+'</tr></thead>';
              var body = '<tbody>'+v.map(function(row){
                return '<tr>'+keys.map(function(k){
                  var cell = row[k];
                  return '<td style="font-size:.8rem;padding:4px 8px">'+escapeHtml(cell === null || cell === undefined ? '-' : (typeof cell === 'object' ? JSON.stringify(cell) : String(cell)))+'</td>';
                }).join('')+'</tr>';
              }).join('')+'</tbody>';
              return '<table class="data-table" style="margin:0;font-size:.85rem">'+head+body+'</table>';
            }
            return v.map(function(x){return String(x);}).join(', ');
          }
          if (typeof v === 'object') {
            return '<table class="data-table" style="margin:0;font-size:.85rem"><tbody>'+Object.entries(v).map(function(kv2){
              return '<tr><td style="font-weight:600;padding:3px 8px">'+escapeHtml(kv2[0])+'</td><td style="padding:3px 8px">'+escapeHtml(String(kv2[1]))+'</td></tr>';
            }).join('')+'</tbody></table>';
          }
          return escapeHtml(String(v));
        };
        html='<table class="data-table"><tbody>'+Object.entries(d).map(function(kv){
          return '<tr><td style="font-weight:600;width:40%;vertical-align:top">'+escapeHtml(kv[0])+'</td><td>'+_fmtVal(kv[1])+'</td></tr>';
        }).join('')+'</tbody></table>';
      }
      document.getElementById('sqm-modal-content').innerHTML='<h2 style="margin-bottom:16px">'+escapeHtml(title)+'</h2>'+html;
      _sqmSyncModalHeaderFromContent();
    }).catch(function(e){
      document.getElementById('sqm-modal-content').innerHTML='<h2>'+escapeHtml(title)+'</h2><div class="empty">Load failed: '+escapeHtml(e.message||String(e))+'</div>';
      _sqmSyncModalHeaderFromContent();
    });
  }
  window.renderInfoModal = renderInfoModal;

  window.showLotDetail = function(lotNo) {
    if (!lotNo) return;
    showDataModal('LOT Detail: '+lotNo,'<div style="padding:20px;text-align:center">⏳ 로딩 중...</div>');
    apiGet('/api/action/lot-detail/'+encodeURIComponent(lotNo)).then(function(res){
      var d=res.data||res||{};
      var html='<table class="data-table"><tbody>'+Object.entries(d).map(function(kv){
        return '<tr><td style="font-weight:600;width:40%">'+escapeHtml(kv[0])+'</td><td>'+escapeHtml(String(kv[1]))+'</td></tr>';
      }).join('')+'</tbody></table>';
      document.getElementById('sqm-modal-content').innerHTML='<h2 style="margin-bottom:16px">LOT Detail: '+escapeHtml(lotNo)+'</h2>'+html;
      _sqmSyncModalHeaderFromContent();
    }).catch(function(e){
      document.getElementById('sqm-modal-content').innerHTML='<h2>LOT Detail: '+escapeHtml(lotNo)+'</h2><div class="empty">Load failed: '+escapeHtml(e.message||String(e))+'</div>';
      _sqmSyncModalHeaderFromContent();
    });
  };

})();
