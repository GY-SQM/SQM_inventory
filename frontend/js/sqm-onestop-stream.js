/* =======================================================================
   sqm-onestop-stream.js  (v8.7.0-r1)
   OneStop 파싱 진행 SSE 스트림 — 큰 새 창 + 실시간 줄단위 표시.

   설계
   ────
   - 기존 window.onestopParseStart 를 감싸서 (wrapper):
       1) job_id 생성 → window._onestopParseJobId 에 저장
       2) sqm-onestop-parse-stream 모달(큰 창) 띄움
       3) /api/onestop/parse-progress/register 호출
       4) EventSource 로 SSE 구독 → 줄 단위로 모달에 append
       5) 원본 onestopParseStart 실행 (= XHR 시작)
   - XHR.send monkey-patch — FormData 이면서 onestop-upload 호출이면
     job_id 자동 첨부 (sqm-onestop-inbound.js IIFE 미수정 원칙 준수)
   - 모달 ID 'sqm-onestop-parse-stream' 는 modal-manager TARGET_IDS 자동 감지
     로 잡혀 리사이즈/크기저장 가능
   ======================================================================= */
(function () {
  'use strict';
  if (window.__SQM_ONESTOP_STREAM__) return;
  window.__SQM_ONESTOP_STREAM__ = true;

  function _getApiBase() {
    return window.SQM_API_BASE || (window.location && window.location.origin) || '';
  }
  var API = _getApiBase(); // 초기값 (하위 호환)

  /* ── job_id 생성 ───────────────────────────────────────────────────── */
  function _newJobId() {
    return 'job-' + Date.now() + '-' + Math.random().toString(36).slice(2, 8);
  }

  /* ── 단계별 한글 라벨 매핑 ────────────────────────────────────────── */
  var STAGE_LABEL = {
    upload_received:   '📥 업로드 수신',
    pl_start:          '📦 Packing List 파싱 시작',
    pl_done:           '📦 Packing List 파싱 완료',
    bl_start:          '🚢 BL 파싱 시작',
    bl_done:           '🚢 BL 파싱 완료',
    invoice_start:     '📄 Invoice 파싱 시작',
    invoice_done:      '📄 Invoice 파싱 완료',
    do_start:          '📋 DO 파싱 시작',
    do_done:           '📋 DO 파싱 완료',
    alarm_check_start: '🔔 알람 검증 시작',
    alarm_check_done:  '🔔 알람 검증 완료',
    response_build:    '🧾 응답 조립',
  };

  /* ── 모달 생성/취득 ────────────────────────────────────────────────── */
  var _modal = null;
  var _bodyEl = null;
  var _summaryEl = null;
  var _closeBtn = null;

  function _ensureModal() {
    if (_modal && document.body.contains(_modal)) return _modal;
    var d = document.createElement('div');
    d.id = 'sqm-onestop-parse-stream';
    d.style.cssText = ''
      + 'position:fixed;top:60px;left:50%;transform:translateX(-50%);'
      + 'width:min(820px,94vw);height:min(620px,88vh);background:var(--bg-card,#1a2233);'
      + 'border:2px solid var(--accent,#4fc3f7);border-radius:10px;'
      + 'box-shadow:0 8px 40px rgba(0,0,0,.65);z-index:10080;'
      + 'display:flex;flex-direction:column;overflow:hidden;color:var(--fg,#e2e8f0);';
    d.innerHTML = ''
      + '<div id="sqm-osps-hdr" style="cursor:move;user-select:none;background:linear-gradient(90deg,#0ea5e9,#4fc3f7);'
      + '  color:#fff;padding:10px 14px;display:flex;align-items:center;gap:10px;flex-shrink:0">'
      + '  <span style="font-size:15px;font-weight:700;flex:1">📡 OneStop 파싱 실시간 스트림</span>'
      + '  <span id="sqm-osps-elapsed" style="font-size:11px;opacity:.92;font-variant-numeric:tabular-nums">0.0s</span>'
      + '  <button id="sqm-osps-close" '
      + '    style="background:rgba(255,255,255,.18);border:none;color:#fff;font-size:16px;'
      + '           cursor:pointer;padding:2px 10px;border-radius:6px;line-height:1.4">×</button>'
      + '</div>'
      + '<div id="sqm-osps-body" '
      + '  style="flex:1 1 auto;overflow:auto;padding:10px 14px;font-family:Consolas,Monaco,monospace;'
      + '         font-size:12.5px;line-height:1.55;background:var(--bg,#0f172a);display:flex;flex-direction:column;gap:3px"></div>'
      + '<div id="sqm-osps-summary" '
      + '  style="flex-shrink:0;padding:9px 14px;border-top:1px solid var(--panel-border,#334155);'
      + '         background:var(--bg-hover,#152136);font-size:12px;color:var(--text-muted,#94a3b8)">'
      + '대기 중…</div>';
    document.body.appendChild(d);
    _modal = d;
    _bodyEl = d.querySelector('#sqm-osps-body');
    _summaryEl = d.querySelector('#sqm-osps-summary');
    _closeBtn = d.querySelector('#sqm-osps-close');
    _closeBtn.onclick = function () { _modal.style.display = 'none'; };
    return d;
  }

  /* ── 줄 추가 ───────────────────────────────────────────────────────── */
  function _addLine(kind, label, detail) {
    if (!_bodyEl) return;
    var COLORS = {
      step:    '#4fc3f7',
      info:    'var(--text-muted,#94a3b8)',
      warn:    '#f59e0b',
      error:   '#ef4444',
      done:    '#10b981',
      summary: '#10b981',
    };
    var color = COLORS[kind] || 'var(--fg)';
    var icon = ({ step:'•', warn:'⚠', error:'✗', done:'✓', summary:'⇢', info:'·' })[kind] || '·';
    var now = new Date();
    var hh = String(now.getHours()).padStart(2,'0');
    var mm = String(now.getMinutes()).padStart(2,'0');
    var ss = String(now.getSeconds()).padStart(2,'0');
    var ts = hh + ':' + mm + ':' + ss;

    var row = document.createElement('div');
    row.style.cssText = 'display:flex;gap:8px;align-items:flex-start;color:' + color;
    var tsEl = document.createElement('span');
    tsEl.style.cssText = 'color:var(--text-muted,#94a3b8);font-size:11px;min-width:62px;flex-shrink:0';
    tsEl.textContent = ts;
    var iconEl = document.createElement('span');
    iconEl.style.cssText = 'min-width:14px;flex-shrink:0;font-weight:700';
    iconEl.textContent = icon;
    var labEl = document.createElement('span');
    labEl.style.cssText = 'flex:1';
    var text = label || '';
    if (detail && typeof detail === 'object' && Object.keys(detail).length) {
      var bits = [];
      for (var k in detail) {
        if (Object.prototype.hasOwnProperty.call(detail, k)) {
          if (k === 'stage') continue;
          var v = detail[k];
          if (v === null || v === undefined || v === '') continue;
          if (typeof v === 'object') v = JSON.stringify(v);
          bits.push(k + '=' + v);
        }
      }
      if (bits.length) text += '  ' + bits.join(' · ');
    }
    labEl.textContent = text;
    row.appendChild(tsEl);
    row.appendChild(iconEl);
    row.appendChild(labEl);
    _bodyEl.appendChild(row);
    _bodyEl.scrollTop = _bodyEl.scrollHeight;
  }

  /* ── 스트림 시작 ───────────────────────────────────────────────────── */
  var _es = null;
  var _startTs = 0;
  var _elapsedTimer = null;

  function _startStream(jobId) {
    var m = _ensureModal();
    m.style.display = 'flex';
    _bodyEl.innerHTML = '';
    _summaryEl.textContent = '연결 중…';
    _startTs = Date.now();
    if (_elapsedTimer) clearInterval(_elapsedTimer);
    _elapsedTimer = setInterval(function () {
      var elp = (Date.now() - _startTs) / 1000;
      var elapsedEl = m.querySelector('#sqm-osps-elapsed');
      if (elapsedEl) elapsedEl.textContent = elp.toFixed(1) + 's';
    }, 100);

    _addLine('info', '🚀 파싱 시작 — job_id=' + jobId);

    // 1) register
    try {
      fetch(_getApiBase() + '/api/onestop/parse-progress/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_id: jobId }),
      }).catch(function () { /* 무시 — 진행은 계속 */ });
    } catch (e) {}

    // 2) EventSource 연결
    if (_es) { try { _es.close(); } catch (_) {} _es = null; }
    try {
      _es = new EventSource(_getApiBase() + '/api/onestop/parse-stream/' + encodeURIComponent(jobId));
    } catch (e) {
      _addLine('error', 'EventSource 생성 실패: ' + (e && e.message || e));
      return;
    }
    _es.addEventListener('open', function () { _summaryEl.textContent = '⚡ 실시간 스트림 연결됨'; });
    _es.addEventListener('step', function (e) {
      var data; try { data = JSON.parse(e.data); } catch (_) { data = {}; }
      var stage = data.stage || '';
      var label = STAGE_LABEL[stage] || ('• ' + stage);
      _addLine('step', label, data);
    });
    _es.addEventListener('warn', function (e) {
      var d; try { d = JSON.parse(e.data); } catch (_) { d = {}; }
      _addLine('warn', d.message || '경고', d);
    });
    _es.addEventListener('error', function (e) {
      var d = {};
      if (e && e.data) { try { d = JSON.parse(e.data); } catch (_) {} }
      _addLine('error', d.message || d.msg || '오류 발생', d);
    });
    _es.addEventListener('summary', function (e) {
      var d; try { d = JSON.parse(e.data); } catch (_) { d = {}; }
      _addLine('summary', '✅ 요약', d);
      if (d.error) _summaryEl.textContent = '❌ 실패: ' + d.error;
      else _summaryEl.textContent = '✅ 완료 · ' +
        (d.rows != null ? ('LOT ' + d.rows + '개') : '') +
        (d.warnings ? (' · 경고 ' + d.warnings + '건') : '');
    });
    _es.addEventListener('done', function () {
      _addLine('done', '🏁 스트림 종료');
      _cleanupStream();
    });
    _es.onerror = function () {
      // 자동 재연결 멈춤 (서버가 닫으면 보통 done 이벤트 다음에 오므로 무시)
      // 단, register 전 끊김(404 등) 시 한 번 로그
      if (_es && _es.readyState === EventSource.CLOSED) {
        _addLine('info', '연결 종료');
      }
    };
  }

  function _cleanupStream() {
    if (_elapsedTimer) { clearInterval(_elapsedTimer); _elapsedTimer = null; }
    setTimeout(function () {
      if (_es) { try { _es.close(); } catch (_) {} _es = null; }
    }, 500);
  }

  /* ── XHR monkey-patch: onestop-upload 호출에 job_id 자동 첨부 ───────── */
  (function () {
    var origOpen = XMLHttpRequest.prototype.open;
    var origSend = XMLHttpRequest.prototype.send;
    XMLHttpRequest.prototype.open = function (method, url) {
      this.__sqm_url = url;
      return origOpen.apply(this, arguments);
    };
    XMLHttpRequest.prototype.send = function (body) {
      try {
        if (body && (typeof FormData !== 'undefined') && body instanceof FormData &&
            window._onestopParseJobId &&
            (this.__sqm_url || '').indexOf('/api/inbound/onestop-upload') !== -1) {
          // 이미 들어있으면 중복 추가 안 함
          var hasJob = false;
          if (typeof body.has === 'function') hasJob = body.has('job_id');
          if (!hasJob) body.append('job_id', window._onestopParseJobId);
        }
      } catch (_) {}
      return origSend.apply(this, arguments);
    };
  })();

  /* ── fetch monkey-patch (XHR 대신 fetch 쓸 경우 대비) ─────────────── */
  (function () {
    var origFetch = window.fetch;
    if (!origFetch) return;
    window.fetch = function (input, init) {
      try {
        var url = (typeof input === 'string') ? input :
          (input && input.url) ? input.url : '';
        if (url && url.indexOf('/api/inbound/onestop-upload') !== -1 &&
            init && init.body instanceof FormData && window._onestopParseJobId) {
          var has = false;
          if (typeof init.body.has === 'function') has = init.body.has('job_id');
          if (!has) init.body.append('job_id', window._onestopParseJobId);
        }
      } catch (_) {}
      return origFetch.apply(this, arguments);
    };
  })();

  /* ── onestopParseStart wrapping ────────────────────────────────────── */
  function _install() {
    var orig = window.onestopParseStart;
    if (typeof orig !== 'function') {
      // sqm-onestop-inbound.js 가 아직 로드 안 됨 — 재시도
      return false;
    }
    if (orig.__sqm_stream_wrapped) return true;

    var wrapped = function () {
      var jobId = _newJobId();
      window._onestopParseJobId = jobId;
      try { _startStream(jobId); } catch (e) {
        try { console.warn('[sqm-onestop-stream] _startStream 실패:', e); } catch (_) {}
      }
      return orig.apply(this, arguments);
    };
    wrapped.__sqm_stream_wrapped = true;
    window.onestopParseStart = wrapped;
    try { console.info('[sqm-onestop-stream] v8.7.0-r1 installed — onestopParseStart wrapped'); } catch (_) {}
    return true;
  }

  // 즉시 시도 + DOMContentLoaded + 200ms retry (sqm-onestop-inbound.js 가 늦게 로드돼도 잡음)
  if (!_install()) {
    var tries = 0;
    var iv = setInterval(function () {
      tries++;
      if (_install() || tries > 50) clearInterval(iv);
    }, 100);
  }

  // 공개 API
  window.sqmOnestopStream = {
    version: 'v8.7.0-r1',
    open: function () {
      var jobId = _newJobId();
      window._onestopParseJobId = jobId;
      _startStream(jobId);
      return jobId;
    },
    close: function () { if (_modal) _modal.style.display = 'none'; _cleanupStream(); },
  };
})();
