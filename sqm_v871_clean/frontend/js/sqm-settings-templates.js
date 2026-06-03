/* sqm-settings-templates.js — sqm-inline.js 2단계 분리: 설정 + 템플릿 관리 */
(function () {
  'use strict';
  var apiGet = function() { return window.apiGet.apply(window, arguments); };
  var apiPost = function() { return window.apiPost.apply(window, arguments); };
  var showToast = function() { return window.showToast.apply(window, arguments); };
  var escapeHtml = function() { return window.escapeHtml.apply(window, arguments); };
  var getStore = function() { return window.getStore.apply(window, arguments); };
  var sqmConfirm = function() { return window.sqmConfirm.apply(window, arguments); };
  var showDataModal = function() { return window.showDataModal.apply(window, arguments); };
  var sqmShouldOpenXlsxAfterSave = function() { return window.sqmShouldOpenXlsxAfterSave.apply(window, arguments); };
  var API = window.API || window.SQM_API_BASE || window.location.origin || '';
  function showSettingsDialog(title, icon, fields) {
    var html = '<div style="max-width:480px"><h2 style="margin:0 0 16px 0">' + icon + ' ' + escapeHtml(title) + '</h2>';
    html += '<div style="display:grid;grid-template-columns:130px 1fr;gap:10px;align-items:center;margin-bottom:16px">';
    fields.forEach(function(f){
      html += '<label style="font-weight:600">' + escapeHtml(f.label) + '</label>';
      if (f.type === 'select') {
        html += '<select id="sdlg-'+f.id+'" style="padding:8px;background:var(--bg-hover);color:var(--text);border:1px solid var(--border);border-radius:6px">';
        f.options.forEach(function(o){ html += '<option value="'+escapeHtml(o)+'">'+escapeHtml(o)+'</option>'; });
        html += '</select>';
      } else if (f.type === 'checkbox') {
        html += '<label style="display:flex;align-items:center;gap:6px"><input type="checkbox" id="sdlg-'+f.id+'"' + (f.checked ? ' checked' : '') + '> ' + escapeHtml(f.hint||'') + '</label>';
      } else {
        html += '<input type="'+(f.type||'text')+'" id="sdlg-'+f.id+'" placeholder="'+escapeHtml(f.hint||'')+'" value="'+escapeHtml(f.value||'')+'" style="padding:8px;background:var(--bg-hover);color:var(--text);border:1px solid var(--border);border-radius:6px">';
      }
    });
    html += '</div>';
    html += '<div style="padding:12px;background:var(--bg-hover);border-radius:6px;margin-bottom:16px;font-size:.85rem;color:var(--text-muted)">💡 설정은 현재 세션에만 적용됩니다. PyWebView 재시작 시 기본값으로 복원됩니다.</div>';
    html += '<div style="display:flex;gap:8px;justify-content:flex-end"><button onclick="document.getElementById(\'sqm-modal\').style.display=\'none\'" class="btn btn-ghost">닫기</button><button onclick="showToast(\'success\',\'설정 저장됨\');document.getElementById(\'sqm-modal\').style.display=\'none\'" class="btn btn-primary">저장</button></div>';
    html += '</div>';
    showDataModal('', html);
  }

  function showEmailConfigModal() {
    apiGet('/api/settings/email').then(function(res) {
      var cfg = (res && res.data) || {};
      var inp = 'padding:8px;background:var(--bg-hover);color:var(--text);border:1px solid var(--border);border-radius:6px;width:100%';
      var html = '<div style="max-width:500px">'
        + '<h2 style="margin:0 0 16px 0">⚙️ 이메일 설정</h2>'
        + '<div style="display:grid;grid-template-columns:120px 1fr;gap:10px 12px;align-items:center;margin-bottom:16px">'
        + '<label style="font-weight:600">SMTP 서버</label><input type="text" id="em-host" value="' + escapeHtml(cfg.smtp_host||'smtp.gmail.com') + '" style="' + inp + '">'
        + '<label style="font-weight:600">포트</label><input type="number" id="em-port" value="' + (cfg.smtp_port||587) + '" style="' + inp + '">'
        + '<label style="font-weight:600">사용자</label><input type="text" id="em-user" value="' + escapeHtml(cfg.smtp_user||'') + '" placeholder="user@company.com" style="' + inp + '">'
        + '<label style="font-weight:600">비밀번호</label><input type="password" id="em-pass" value="' + escapeHtml(cfg.smtp_pass||'') + '" placeholder="앱 비밀번호" style="' + inp + '">'
        + '<label style="font-weight:600">발신 주소</label><input type="text" id="em-from" value="' + escapeHtml(cfg.from_addr||'') + '" placeholder="noreply@company.com" style="' + inp + '">'
        + '<label style="font-weight:600">수신자</label><input type="text" id="em-recipients" value="' + escapeHtml(cfg.recipients||'') + '" placeholder="admin@company.com, ..." style="' + inp + '">'
        + '<label style="font-weight:600">TLS 사용</label><label style="display:flex;align-items:center;gap:6px"><input type="checkbox" id="em-tls"' + (cfg.tls !== false ? ' checked' : '') + '> TLS 암호화</label>'
        + '<label style="font-weight:600">활성화</label><label style="display:flex;align-items:center;gap:6px"><input type="checkbox" id="em-enabled"' + (cfg.enabled ? ' checked' : '') + '> 이메일 기능 사용</label>'
        + '</div>'
        + '<div style="display:flex;gap:8px;justify-content:flex-end">'
        + '<button onclick="document.getElementById(\'sqm-modal\').style.display=\'none\'" class="btn btn-ghost">닫기</button>'
        + '<button onclick="window._saveEmailConfig()" class="btn btn-primary">저장</button>'
        + '</div></div>';
      showDataModal('', html);
    }).catch(function() {
      showToast('error', '이메일 설정 불러오기 실패');
    });
  }
  window._saveEmailConfig = function() {
    var payload = {
      smtp_host: (document.getElementById('em-host')||{}).value||'',
      smtp_port: parseInt((document.getElementById('em-port')||{}).value||'587', 10),
      smtp_user: (document.getElementById('em-user')||{}).value||'',
      smtp_pass: (document.getElementById('em-pass')||{}).value||'',
      from_addr: (document.getElementById('em-from')||{}).value||'',
      recipients: (document.getElementById('em-recipients')||{}).value||'',
      tls:      !!(document.getElementById('em-tls')||{}).checked,
      enabled:  !!(document.getElementById('em-enabled')||{}).checked
    };
    apiPost('/api/settings/email', payload).then(function() {
      showToast('success', '이메일 설정 저장 완료');
      document.getElementById('sqm-modal').style.display = 'none';
    }).catch(function(e) {
      showToast('error', '저장 실패: ' + (e.message || String(e)));
    });
  };
  window.showEmailConfigModal = showEmailConfigModal;

  function showAutoBackupSettingsModal() {
    var INTERVAL_VALUES = [30, 60, 180, 360, 720, 1440];
    var INTERVAL_LABELS = ['30분', '1시간', '3시간', '6시간', '12시간', '24시간'];
    var inp = 'padding:8px;background:var(--bg-hover);color:var(--text);border:1px solid var(--border);border-radius:6px';
    apiGet('/api/settings/backup').then(function(res) {
      var cfg = (res && res.data) || {};
      var selOpts = INTERVAL_VALUES.map(function(v, i) {
        return '<option value="' + v + '"' + (cfg.interval_min === v ? ' selected' : '') + '>' + INTERVAL_LABELS[i] + '</option>';
      }).join('');
      var lastBackup = cfg.last_backup ? '<div style="margin-bottom:10px;font-size:.82rem;color:var(--text-muted)">최근 백업: ' + escapeHtml(cfg.last_backup) + '</div>' : '';
      var html = '<div style="max-width:460px">'
        + '<h2 style="margin:0 0 16px 0">⏰ 자동 백업 설정</h2>'
        + '<div style="display:grid;grid-template-columns:100px 1fr;gap:10px 12px;align-items:center;margin-bottom:16px">'
        + '<label style="font-weight:600">자동 백업</label><label style="display:flex;align-items:center;gap:6px"><input type="checkbox" id="bk-enabled"' + (cfg.enabled ? ' checked' : '') + '> 활성화</label>'
        + '<label style="font-weight:600">주기</label><select id="bk-interval" style="' + inp + '">' + selOpts + '</select>'
        + '<label style="font-weight:600">보존 개수</label><input type="number" id="bk-retention" value="' + (cfg.retention||10) + '" min="1" max="100" style="' + inp + '">'
        + '<label style="font-weight:600">저장 경로</label><input type="text" id="bk-path" value="' + escapeHtml(cfg.path||'backup/') + '" style="' + inp + '">'
        + '</div>'
        + lastBackup
        + '<div style="display:flex;gap:8px;justify-content:flex-end">'
        + '<button onclick="document.getElementById(\'sqm-modal\').style.display=\'none\'" class="btn btn-ghost">닫기</button>'
        + '<button onclick="window._saveBackupConfig()" class="btn btn-primary">저장</button>'
        + '</div></div>';
      showDataModal('', html);
    }).catch(function() {
      showToast('error', '백업 설정 불러오기 실패');
    });
  }
  window._saveBackupConfig = function() {
    var payload = {
      enabled:      !!(document.getElementById('bk-enabled')||{}).checked,
      interval_min: parseInt((document.getElementById('bk-interval')||{}).value||'60', 10),
      retention:    parseInt((document.getElementById('bk-retention')||{}).value||'10', 10),
      path:         (document.getElementById('bk-path')||{}).value||'backup/'
    };
    apiPost('/api/settings/backup', payload).then(function() {
      showToast('success', '자동 백업 설정 저장 완료');
      document.getElementById('sqm-modal').style.display = 'none';
    }).catch(function(e) {
      showToast('error', '저장 실패: ' + (e.message || String(e)));
    });
  };
  window.showAutoBackupSettingsModal = showAutoBackupSettingsModal;

  /* ── Gemini AI 설정/테스트/토글 ─────────────────────────────── */
  function showGeminiApiSettingsModal() {
    apiGet('/api/ai/settings').then(function(res) {
      var cfg = res || {};
      var inp = 'padding:8px;background:var(--bg-hover);color:var(--text);border:1px solid var(--border);border-radius:6px;width:100%';
      var statusHtml = cfg.has_key
        ? '<span style="color:var(--success)">✅ 키 등록됨</span> <span style="color:var(--text-muted);font-size:.8rem">(' + escapeHtml(cfg.key_source||'') + ')</span>'
        : '<span style="color:var(--warning)">⚠️ 키 없음</span>';
      var html = '<div style="max-width:480px">'
        + '<h2 style="margin:0 0 14px 0">🔐 Gemini API 설정</h2>'
        + '<div style="margin-bottom:12px">' + statusHtml + '</div>'
        + '<div style="display:grid;grid-template-columns:90px 1fr;gap:10px 12px;align-items:center;margin-bottom:14px">'
        + '<label style="font-weight:600">API 키</label><input type="password" id="gm-key" placeholder="새 키 입력 (변경 시만)" style="' + inp + '">'
        + '<label style="font-weight:600">모델</label><input type="text" id="gm-model" value="' + escapeHtml(cfg.model||'gemini-1.5-flash') + '" style="' + inp + '">'
        + '<label style="font-weight:600">사용</label><label style="display:flex;align-items:center;gap:6px"><input type="checkbox" id="gm-enabled"' + (cfg.enabled !== false ? ' checked' : '') + '> Gemini AI 활성화</label>'
        + '</div>'
        + '<div style="padding:9px;background:var(--bg-hover);border-radius:6px;margin-bottom:12px;font-size:.82rem;color:var(--text-muted)">키를 비워두면 기존 키가 유지됩니다.</div>'
        + '<div style="display:flex;gap:8px;justify-content:flex-end">'
        + '<button onclick="document.getElementById(\'sqm-modal\').style.display=\'none\'" class="btn btn-ghost">닫기</button>'
        + '<button onclick="window._saveGeminiSettings()" class="btn btn-primary">저장</button>'
        + '</div></div>';
      showDataModal('', html);
    }).catch(function() {
      showToast('error', 'Gemini 설정 불러오기 실패');
    });
  }
  window.showGeminiApiSettingsModal = showGeminiApiSettingsModal;
  window._saveGeminiSettings = function() {
    var key   = (document.getElementById('gm-key')||{}).value||'';
    var model = (document.getElementById('gm-model')||{}).value||'gemini-1.5-flash';
    var enabled = !!(document.getElementById('gm-enabled')||{}).checked;
    var p1 = key.trim()
      ? apiPost('/api/ai/settings', { api_key: key.trim(), model: model })
      : Promise.resolve(null);
    p1.then(function() {
      return apiPost('/api/ai/toggle', { enabled: enabled });
    }).then(function() {
      showToast('success', 'Gemini 설정 저장 완료');
      document.getElementById('sqm-modal').style.display = 'none';
    }).catch(function(e) {
      showToast('error', '저장 실패: ' + (e.message || String(e)));
    });
  };

  function showGeminiApiTestModal() {
    showDataModal('', '<div style="max-width:440px"><h3 style="margin:0 0 12px">🧪 Gemini API 연결 테스트</h3><div id="gm-test-body" style="color:var(--text-muted)">테스트 중…</div></div>');
    apiGet('/api/ai/test').then(function(res) {
      var body = document.getElementById('gm-test-body');
      if (!body) return;
      var ok = res && res.success;
      body.innerHTML = ok
        ? '<div style="color:var(--success);font-size:1.1rem">✅ 연결 성공</div><div style="margin-top:8px;font-size:.85rem;color:var(--text-muted)">' + escapeHtml((res.message||'') + (res.model ? ' / 모델: ' + res.model : '')) + '</div>'
        : '<div style="color:var(--danger);font-size:1.1rem">❌ 연결 실패</div><div style="margin-top:8px;font-size:.85rem;color:var(--text-muted)">' + escapeHtml((res && res.message) || '알 수 없는 오류') + '</div>';
    }).catch(function(e) {
      var body = document.getElementById('gm-test-body');
      if (body) body.innerHTML = '<div style="color:var(--danger)">❌ 오류: ' + escapeHtml(e.message||String(e)) + '</div>';
    });
  }
  window.showGeminiApiTestModal = showGeminiApiTestModal;

  window._geminiToggleAction = function() {
    apiGet('/api/ai/settings').then(function(res) {
      var next = !(res && res.enabled !== false);
      return apiPost('/api/ai/toggle', { enabled: next }).then(function(r) {
        showToast('success', (r && r.message) || ('Gemini AI ' + (next ? 'ON' : 'OFF')));
      });
    }).catch(function(e) {
      showToast('error', 'Gemini 토글 실패: ' + (e.message || String(e)));
    });
  };

  /* 폰트 크기 전역 설정 */
  function normalizeFontScale(pct) {
    pct = parseInt(pct, 10);
    if (isNaN(pct)) pct = 100;
    pct = Math.max(100, Math.min(160, pct));
    return Math.round(pct / 10) * 10;
  }

  function applyFontScale(pct, notify) {
    pct = normalizeFontScale(pct);
    document.body.style.zoom = String(pct / 100);
    document.documentElement.setAttribute('data-font-scale', String(pct));
    window._sqmFontScale = pct;
    try { getStore().setItem('sqm_font_scale', String(pct)); } catch {}
    if (notify) showToast('success', '폰트 크기: ' + pct + '%');
  }

  window.sqmSetFontScale = function(pct) {
    applyFontScale(pct, true);
  };

  function applyStoredFontScale() {
    var stored = null;
    try { stored = getStore().getItem('sqm_font_scale'); } catch {}
    applyFontScale(stored || 100, false);
  }
  window.applyStoredFontScale = applyStoredFontScale;

  function showFontSizeModal() {
    var cur = window._sqmFontScale || 100;
    var html = '<div style="max-width:420px">'
      + '<h2 style="margin:0 0 14px 0">⚙️ 표시 · 엑셀</h2>'
      + '<p style="color:var(--text-muted);font-size:.9rem;margin-bottom:16px">'
      + '화면 확대와 엑셀 내보내기 동작을 설정합니다.</p>'
      + '<h3 style="margin:0 0 10px 0;font-size:1rem">🔤 화면 폰트 크기</h3>'
      + '<p style="color:var(--text-muted);font-size:.85rem;margin-bottom:12px">'
      + '전체 UI 폰트를 일괄 확대합니다. 100% = 기본값.</p>'
      + '<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:20px">';
    [100,110,120,130,140,150,160].forEach(function(p) {
      html += '<button class="btn' + (cur === p ? ' btn-primary' : '') + '"'
        + ' onclick="window.sqmSetFontScale(' + p + ');'
        + 'document.getElementById(\'sqm-modal\').style.display=\'none\'"'
        + ' style="min-width:66px;font-size:14px">' + p + '%</button>';
    });
    html += '</div>'
      + '<div style="margin-top:8px;padding-top:16px;border-top:1px solid var(--panel-border,#1e4a7a)">'
      + '<h3 style="margin:0 0 8px 0;font-size:1rem">📊 엑셀 내보내기</h3>'
      + '<label style="display:flex;align-items:flex-start;gap:10px;cursor:pointer">'
      + '<input type="checkbox" id="sqm-open-xlsx-after-save" style="margin-top:3px" '
      + (sqmShouldOpenXlsxAfterSave() ? 'checked ' : '')
      + 'onchange="window.sqmSetOpenXlsxAfterSave(this.checked)">'
      + '<span style="line-height:1.45">저장한 엑셀 파일을 <b>기본 프로그램(Excel)</b>으로 바로 열기'
      + '<br><span style="color:var(--text-muted);font-size:.85rem">'
      + 'PyWebView(본 프로그램)에서 “다른 이름으로 저장”으로 내보낼 때 적용됩니다.</span></span>'
      + '</label></div>'
      + '<div style="display:flex;gap:8px;justify-content:flex-end;margin-top:16px">'
      + '<button class="btn btn-ghost" onclick="window.sqmSetFontScale(100);'
      + 'document.getElementById(\'sqm-modal\').style.display=\'none\'">초기화 (100%)</button>'
      + '<button class="btn btn-ghost" onclick="document.getElementById(\'sqm-modal\').style.display=\'none\'">닫기</button>'
      + '</div></div>';
    showDataModal('', html);
  }
  window.showFontSizeModal = showFontSizeModal;

    /* ═══════════════════════════════════════════════════════════
     입고 파싱 템플릿 관리 (풀 CRUD)
     6컬럼: 순번 | 선사 | 템플릿이름 | 제품이름 | 톤백무게 | BL형식
     생성: 수동입력 / PDF파싱추출 / Excel업로드
     ═══════════════════════════════════════════════════════════ */
  var _tplMid = 'sqm-inbound-tpl-mgr';
  var _tplEditId = null;  // null=신규, string=수정 중인 template_id

    /* ══ 입고 파싱 템플릿 관리 (풀 CRUD) ══ */
  var _tplMid = 'sqm-inbound-tpl-mgr';
  var _tplEditId = null;

  function showInboundTemplateModal() {
    var ex = document.getElementById(_tplMid);
    if (ex) { ex.remove(); }
    var m = document.createElement('div');
    m.id = _tplMid;
    m.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.65);z-index:99980;display:flex;align-items:flex-start;justify-content:center;overflow-y:auto;padding:24px 0';
    m.innerHTML = _tplShell();
    document.body.appendChild(m);
    m.addEventListener('click', function(e){ if (e.target === m) m.remove(); });
    _tplLoadList();
  }
  window.showInboundTemplateModal = showInboundTemplateModal;

  function _tplClose() {
    var m = document.getElementById(_tplMid);
    if (m) m.remove();
  }

  function _tplShell() {
    return [
      '<div id="sqm-tpl-inner" style="background:var(--panel,#12233a);border:1px solid',
      ' var(--panel-border,#1e4a7a);border-radius:10px;padding:24px 28px;',
      'width:880px;max-width:96vw;color:var(--fg)">',
      /* 헤더 */
      '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px">',
      '<span style="font-size:16px;font-weight:700">📋 입고 파싱 템플릿 관리</span>',
      '<button class="btn" onclick="window._tplClose()">✕ 닫기</button>',
      '</div>',
      /* 툴바 */
      '<div style="display:flex;gap:8px;margin-bottom:14px">',
      '<button class="btn btn-primary" onclick="window._tplShowForm(null)">➕ 수동 추가</button>',
      '<label class="btn" style="cursor:pointer;margin:0">',
      '📄 PDF에서 추출',
      '<input type="file" accept=".pdf" style="display:none" onchange="window._tplFromPdf(this)">',
      '</label>',
      '<label class="btn" style="cursor:pointer;margin:0">',
      '📊 Excel 일괄등록',
      '<input type="file" accept=".xlsx,.xls,.csv" style="display:none" onchange="window._tplFromExcel(this)">',
      '</label>',
      '<button class="btn" onclick="window._tplLoadList()" style="margin-left:auto">🔄 새로고침</button>',
      '</div>',
      '<div id="sqm-tpl-form-area" style="display:none"></div>',
      '<div id="sqm-tpl-table-area"><div style="color:var(--text-muted);padding:20px;text-align:center">',
      '⏳ 로딩 중...</div></div>',
      '</div>'
    ].join('');
  }

  window._tplClose = _tplClose;

  window._tplLoadList = function() { _tplLoadList(); };

  function _tplLoadList() {
    var area = document.getElementById('sqm-tpl-table-area');
    if (!area) return;
    area.innerHTML = '<div style="color:var(--text-muted);padding:16px;text-align:center">⏳ 로딩 중...</div>';
    fetch(API + '/api/inbound/templates')
      .then(function(r) { return r.json(); })
      .then(function(d) {
        if (!area) return;
        if (!d.ok) {
          area.innerHTML = '<div style="color:var(--danger)">❌ ' + escapeHtml(d.error || '로드 실패') + '</div>';
          return;
        }
        var rows = d.templates || [];
        if (rows.length === 0) {
          area.innerHTML = '<div style="color:var(--text-muted);padding:20px;text-align:center">📭 등록된 템플릿이 없습니다.<br><small>위 버튼으로 추가하세요</small></div>';
          return;
        }
        var TH = '<th style="padding:8px 6px;text-align:left;color:var(--text-muted);border-bottom:2px solid var(--border)">';
        var html = '<table style="width:100%;border-collapse:collapse;font-size:13px"><thead><tr>'
          + TH + '순번</th>'
          + TH + '선사</th>'
          + TH + '템플릿 이름</th>'
          + TH + '제품 이름</th>'
          + '<th style="padding:8px 6px;text-align:center;color:var(--text-muted);border-bottom:2px solid var(--border);width:80px">톬백무게</th>'
          + TH + 'BL 형식</th>'
          + '<th style="padding:8px 6px;text-align:center;color:var(--text-muted);border-bottom:2px solid var(--border);width:80px">작업</th>'
          + '</tr></thead><tbody>';
        var _tplRowsCache = {};
        rows.forEach(function(t, i) {
          _tplRowsCache[String(t.template_id)] = t;
          var bg = i % 2 === 0 ? 'transparent' : 'rgba(255,255,255,0.03)';
          var bw = t.bag_weight_kg || 500;
          var tidSafe   = escapeHtml(String(t.template_id));
          var tnameSafe = escapeHtml(t.template_name || '');
          html += '<tr style="border-bottom:1px solid var(--border);background:' + bg + '">'
            + '<td style="padding:8px 6px;color:var(--text-muted)">' + (i+1) + '</td>'
            + '<td style="padding:8px 6px;font-weight:600">' + escapeHtml(t.carrier_id || '') + '</td>'
            + '<td style="padding:8px 6px">' + escapeHtml(t.template_name || '') + '</td>'
            + '<td style="padding:8px 6px;color:var(--text-muted)">' + escapeHtml(t.product_hint || '') + '</td>'
            + '<td style="padding:8px 6px;text-align:center"><span style="background:var(--info,#1565c0);color:#fff;border-radius:4px;padding:2px 7px;font-size:11px">' + bw + 'kg</span></td>'
            + '<td style="padding:8px 6px;font-family:monospace;font-size:12px">' + escapeHtml(t.bl_format || '') + '</td>'
            + '<td style="padding:8px 6px;text-align:center">'
            + '<button class="btn btn-sm tpl-edit-btn" data-tid="' + tidSafe + '" style="margin-right:4px">✏️</button>'
            + '<button class="btn btn-sm tpl-del-btn"  data-tid="' + tidSafe + '" data-tname="' + tnameSafe + '" style="background:rgba(244,67,54,0.12);color:var(--danger,#f44336)">🗑️</button>'
            + '</td></tr>';
        });
        html += '</tbody></table>';
        area.innerHTML = html;
        /* click handler: data-* attr -> safe call */
        area.addEventListener('click', function(e) {
          var editBtn = e.target.closest('.tpl-edit-btn');
          var delBtn  = e.target.closest('.tpl-del-btn');
          if (editBtn) {
            var tid = editBtn.getAttribute('data-tid');
            window._tplShowForm(_tplRowsCache[tid] || null);
          }
          if (delBtn) {
            var tid2  = delBtn.getAttribute('data-tid');
            var tname = delBtn.getAttribute('data-tname');
            window._tplDelete(tid2, tname);
          }
        });
      })
      .catch(function(e) {
        if (area) area.innerHTML = '<div style="color:var(--danger)">❌ ' + escapeHtml(String(e)) + '</div>';
      });
  }

  function _tplFld(id, label, val, type, hint) {
    return '<label style="display:flex;flex-direction:column;gap:4px">'
      + '<span style="font-size:12px;color:var(--text-muted)">' + escapeHtml(label) + '</span>'
      + '<input id="' + id + '" type="' + type + '" value="' + escapeHtml(String(val||'')) + '"'
      + ' placeholder="' + escapeHtml(hint) + '"'
      + ' style="padding:7px 10px;background:var(--bg-hover);color:var(--fg);border:1px solid var(--border);border-radius:6px"></label>';
  }

  window._tplShowForm = function(tObj) {
    _tplEditId = tObj && tObj.template_id ? tObj.template_id : null;
    var t = tObj || {};
    var bw = t.bag_weight_kg || 500;
    var area = document.getElementById('sqm-tpl-form-area');
    if (!area) return;
    var title = _tplEditId ? '✏️ 템플릿 수정' : '➕ 새 템플릿 추가';
    var wOpts = [500, 450, 600, 1000].map(function(w) {
      return '<option value="' + w + '"' + (bw === w ? ' selected' : '') + '>' + w + ' kg</option>';
    }).join('');
    var _banner = t._warnBanner || '';
    area.innerHTML = _banner
      + '<div style="background:rgba(30,74,122,0.18);border:1px solid var(--border);border-radius:8px;padding:16px 18px;margin-bottom:14px">'
      + '<div style="font-weight:700;margin-bottom:12px">' + title + '</div>'
      + '<div style="display:grid;grid-template-columns:1fr 1fr;gap:10px 16px">'
      + _tplFld('tpl-f-carrier', '선사', t.carrier_id||'', 'text', '예: Maersk, ONE, MSC')
      + _tplFld('tpl-f-name', '템플릿 이름 *', t.template_name||'', 'text', '예: Maersk SQM 500kg 표준')
      + _tplFld('tpl-f-product', '제품 이름', t.product_hint||'', 'text', '예: SQM Potassium Nitrate')
      + _tplFld('tpl-f-bl', 'BL 형식', t.bl_format||'', 'text', '예: MEDUXXXX')
      + '<label style="display:flex;flex-direction:column;gap:4px"><span style="font-size:12px;color:var(--text-muted)">톬백 무게 (kg)</span>'
      + '<select id="tpl-f-weight" style="padding:7px 10px;background:var(--bg-hover);color:var(--fg);border:1px solid var(--border);border-radius:6px">' + wOpts + '</select></label>'
      + _tplFld('tpl-f-hint', 'Gemini 파싱 힌트', t.gemini_hint_packing||'', 'text', '예: 3행부터 데이터, 열 순서 주의')
      + _tplFld('tpl-f-note', '메모', t.note||'', 'text', '자유 입력')
      + '</div>'
      + '<div style="display:flex;gap:8px;margin-top:14px">'
      + '<button class="btn btn-primary" onclick="window._tplSave()">💾 저장</button>'
      + '<button class="btn" onclick="window._tplCancelForm()">취소</button>'
      + '</div></div>';
    area.style.display = '';
    var el = document.getElementById('tpl-f-carrier');
    if (el) el.focus();
  };

  window._tplCancelForm = function() {
    _tplEditId = null;
    var area = document.getElementById('sqm-tpl-form-area');
    if (area) { area.innerHTML = ''; area.style.display = 'none'; }
  };

  window._tplSave = function() {
    var carrier = (document.getElementById('tpl-f-carrier') || {}).value || '';
    var name    = (document.getElementById('tpl-f-name')    || {}).value || '';
    var product = (document.getElementById('tpl-f-product') || {}).value || '';
    var bl      = (document.getElementById('tpl-f-bl')      || {}).value || '';
    var weight  = parseInt((document.getElementById('tpl-f-weight') || {}).value || '500', 10);
    var hint    = (document.getElementById('tpl-f-hint')    || {}).value || '';
    var note    = (document.getElementById('tpl-f-note')    || {}).value || '';
    if (!name.trim()) { showToast('error', '템플릿 이름은 필수입니다'); return; }
    var lotSqm  = (document.getElementById('tpl-f-lotsqm')  || {}).value || '';
    var mxbg    = parseInt((document.getElementById('tpl-f-mxbg') || {}).value || '0', 10) || 0;
    var sapNo   = (document.getElementById('tpl-f-sap')      || {}).value || '';
    var body = {
      carrier_id: carrier.trim(),
      template_name: name.trim(),
      product_hint: product.trim(),
      bag_weight_kg: weight,
      bl_format: bl.trim(),
      gemini_hint_packing: hint.trim(),
      note: note.trim(),
      lot_sqm: lotSqm.trim(),
      mxbg_pallet: mxbg,
      sap_no: sapNo.trim()
    };
    var url    = API + '/api/inbound/templates' + (_tplEditId ? '/' + encodeURIComponent(_tplEditId) : '');
    var method = _tplEditId ? 'PUT' : 'POST';
    fetch(url, { method: method, headers: {'Content-Type':'application/json'}, body: JSON.stringify(body) })
      .then(function(r) { return r.json(); })
      .then(function(d) {
        if (d.ok) {
          showToast('success', _tplEditId ? '수정 완료' : '템플릿 추가 완료');
          window._tplCancelForm();
          _tplLoadList();
        } else {
          showToast('error', '저장 실패: ' + escapeHtml(String(d.detail || d.error || d.message || '')));
        }
      })
      .catch(function(e) { showToast('error', '오류: ' + String(e)); });
  };

  window._tplDelete = function(tid, name) {
    if (!sqmConfirm(name + ' 템플릿을 삭제하시겠습니까?')) return;
    fetch(API + '/api/inbound/templates/' + encodeURIComponent(tid), { method: 'DELETE' })
      .then(function(r) { return r.json(); })
      .then(function(d) {
        if (d.ok) { showToast('success', '삭제 완료: ' + escapeHtml(name)); _tplLoadList(); }
        else      { showToast('error', '삭제 실패: ' + escapeHtml(String(d.detail || d.error || ''))); }
      })
      .catch(function(e) { showToast('error', '오류: ' + String(e)); });
  };

  window._tplFromPdf = function(input) {
    var file = input.files && input.files[0];
    if (!file) return;
    input.value = '';
    showToast('info', '📄 PDF 파싱 중... 잠시 기다려 주세요');
    var fd = new FormData();
    fd.append('file', file, file.name);
    fetch(API + '/api/inbound/templates/from-pdf', { method: 'POST', body: fd })
      .then(function(r) { return r.json(); })
      .then(function(d) {
        if (!d.ok) { showToast('error', 'PDF 추출 실패: ' + escapeHtml(String(d.detail || d.error || ''))); return; }
        var ex = d.extracted || {};
        var warnings = d.parse_warnings || [];

        // ── PARSE_FAILED → 에러 Toast + 상세 모달, 폼 열지 않음
        var fatal = warnings.filter(function(w){ return w.reason_code === 'PARSE_FAILED'; });
        if (fatal.length) {
          showToast('error', '❌ PDF 파싱 실패 — 파일을 확인하세요');
          var msg = fatal.map(function(w){
            return '<div style="margin-bottom:10px">' +
              '<b style="color:var(--danger)">❌ ' + escapeHtml(w.title) + '</b><br>' +
              '<pre style="white-space:pre-wrap;font-size:.83rem;margin:4px 0 0 0;color:var(--text-muted)">' +
              escapeHtml(w.message) + '</pre></div>';
          }).join('');
          showDataModal('PDF 파싱 실패', msg);
          return;
        }

        // ── 경고(PRODUCT_UNKNOWN / CARRIER_UNKNOWN) → Toast + 폼 상단 배너
        var warnBanner = '';
        var nonFatal = warnings.filter(function(w){ return w.reason_code !== 'PARSE_FAILED'; });
        if (nonFatal.length) {
          nonFatal.forEach(function(w){
            showToast('warning', '⚠️ ' + w.title + ' — 저장 전 확인 필요');
          });
          warnBanner = nonFatal.map(function(w){
            return '<div style="background:rgba(255,193,7,.1);border:1px solid #ffc107;border-radius:6px;' +
              'padding:8px 12px;margin-bottom:10px;font-size:.85rem">' +
              '<b style="color:#ffc107">⚠️ ' + escapeHtml(w.title) + '</b><br>' +
              '<pre style="white-space:pre-wrap;font-size:.81rem;margin:4px 0 0 0;color:var(--text-muted)">' +
              escapeHtml(w.message) + '</pre></div>';
          }).join('');
        }

        showToast('success', warnings.length ? 'PDF 추출 완료 — 경고 항목을 확인하세요' : 'PDF 추출 완료 — 내용을 확인하고 저장하세요');
        window._tplShowForm({
          template_id:         null,
          carrier_id:          ex.carrier_id    || '',
          template_name:       ex.suggested_name || '',
          product_hint:        ex.product_hint  || '',
          bag_weight_kg:       ex.bag_weight_kg || 500,
          bl_format:           ex.bl_format     || '',
          gemini_hint_packing: '',
          note: 'PDF 추출: ' + (ex.source_file || file.name),
          lot_sqm: ex.lot_sqm || '',
          mxbg_pallet: ex.mxbg_pallet || 0,
          sap_no: ex.sap_no || '',
          _warnBanner: warnBanner,
        });
      })
      .catch(function(e) { showToast('error', 'PDF 오류: ' + String(e)); });
  };

  window._tplFromExcel = function(input) {
    var file = input.files && input.files[0];
    if (!file) return;
    input.value = '';
    showToast('info', '📊 Excel 처리 중...');
    var fd = new FormData();
    fd.append('file', file, file.name);
    fetch(API + '/api/inbound/templates/from-excel', { method: 'POST', body: fd })
      .then(function(r) { return r.json(); })
      .then(function(d) {
        if (!d.ok) { showToast('error', 'Excel 실패: ' + escapeHtml(String(d.detail || d.error || ''))); return; }
        showToast('success', d.message || 'Excel 등록 완료');
        _tplLoadList();
      })
      .catch(function(e) { showToast('error', 'Excel 오류: ' + String(e)); });
  };



  function showPickingTemplateModal() {
    showSettingsDialog('출고 피킹 템플릿 관리', '📦', [
      { id:'name', label:'템플릿 이름', hint:'기본 피킹 리스트' },
      { id:'format', label:'형식', type:'select', options:['Standard PDF','Custom Excel','Barcode List'] },
      { id:'cols', label:'출력 컬럼', hint:'lot_no,product,weight,...' },
      { id:'sort', label:'정렬 기준', type:'select', options:['LOT 번호','제품명','위치','날짜'] }
    ]);
  }
  window.showPickingTemplateModal = showPickingTemplateModal;

})();
