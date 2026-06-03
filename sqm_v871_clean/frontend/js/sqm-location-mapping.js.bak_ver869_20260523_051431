/* =======================================================================
   sqm-location-mapping.js  (v8.6.8)
   📍 위치 매핑 워크플로우 — 미배정 톤백 인라인 매핑

   동작:
     좌측: LOT 진행률 + 미배정 톤백 리스트
     우측: 선택된 톤백에 대한 위치 입력 (실시간 검증 + 셀 상태 미리보기)

   API:
     GET  /api/inventory/unallocated-tonbags
     POST /api/inventory/assign-location
     POST /api/inventory/assign-locations-bulk
     GET  /api/warehouse/cell-state?location=...

   호출:
     window.showLocationMappingModal();
   ======================================================================= */
(function () {
  'use strict';
  if (window.__SQM_LOC_MAPPING_INSTALLED__) return;
  window.__SQM_LOC_MAPPING_INSTALLED__ = true;

  function _api()         { return (typeof API !== 'undefined') ? API : ''; }
  function _toast(t, msg) { if (window.showToast) window.showToast(t, msg); }
  function _esc(s) {
    if (window.escapeHtml) return window.escapeHtml(s);
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  /* ── 클라이언트 위치 검증 (서버에서도 재검증) ── */
  var LOC_RE = /^G([56])-(\d{2})-(\d{2})-(\d{2})$/;
  var _rackLvMax = {};
  for (var r = 1; r <= 16; r++) {
    _rackLvMax[r] = (r >= 4 && r <= 13) ? 7 : 6;
  }
  function _validateLoc(loc) {
    var s = String(loc || '').trim().toUpperCase();
    var m = LOC_RE.exec(s);
    if (!m) return { ok: false, reason: '형식 오류 (예: G5-04-01-07)' };
    var rk = parseInt(m[2], 10);
    var co = parseInt(m[3], 10);
    var lv = parseInt(m[4], 10);
    if (rk < 1 || rk > 16) return { ok: false, reason: '랙 01~16' };
    if (co < 1 || co > 31) return { ok: false, reason: '열 01~31' };
    var maxLv = _rackLvMax[rk] || 0;
    if (lv < 1 || lv > maxLv) return { ok: false, reason: '랙 ' + rk + ' 최대 ' + maxLv + '층' };
    return { ok: true, dong: m[1], rack: rk, col: co, level: lv, normalized: s };
  }

  /* ── 셀 상태 배지 ── */
  var CELL_BADGES = {
    EMPTY:    { bg: '#37474f', fg: '#b0bec5', text: '⬜ 빈 셀',     ok: true  },
    OCCUPIED: { bg: '#1b5e20', fg: '#a5d6a7', text: '🟦 점유 (가득)', ok: false },
    HALF:     { bg: '#f57f17', fg: '#fff9c4', text: '🟨 반점유',    ok: true  },
    OVER:     { bg: '#b71c1c', fg: '#ffcdd2', text: '⚠ 초과',       ok: false },
    MIXED:    { bg: '#b71c1c', fg: '#ffcdd2', text: '⚠ 혼합',       ok: false },
    UNKNOWN:  { bg: '#212121', fg: '#9e9e9e', text: '? 알수없음',    ok: false },
  };

  /* ── 상태 ── */
  var _state = {
    tonbags:      [],   // 전체 미배정 톤백
    lotProgress:  [],   // LOT 진행률
    summary:      {},   // 전체 요약
    selectedLot:  null,
    selectedIds:  {},   // {tonbag_id: true}
    pendingMap:   {},   // {tonbag_id: location}  — 아직 적용 전 매핑 (배치)
  };

  /* ── 모달 생성 ── */
  var _modal = null;
  function _ensureModal() {
    if (_modal && document.body.contains(_modal)) {
      _modal.style.display = 'flex';
      return _modal;
    }
    var d = document.createElement('div');
    d.id = 'sqm-loc-mapping-modal';
    d.style.cssText = ''
      + 'position:fixed;top:40px;left:50%;transform:translateX(-50%);'
      + 'width:min(1500px,98vw);height:88vh;background:var(--bg-card);'
      + 'border:2px solid var(--accent,#4fc3f7);border-radius:10px;'
      + 'box-shadow:0 8px 40px rgba(0,0,0,.6);z-index:10070;'
      + 'display:flex;flex-direction:column;overflow:hidden;';
    d.innerHTML = ''
      + '<div id="loc-map-hdr" style="cursor:move;background:linear-gradient(90deg,#1565c0,#4fc3f7);'
      +     'color:#fff;padding:10px 16px;display:flex;align-items:center;gap:10px;flex-shrink:0;">'
      + '  <span style="font-size:16px;font-weight:700;">📍 위치 매핑 워크플로우</span>'
      + '  <span id="loc-map-summary" style="font-size:11px;opacity:.9;"></span>'
      + '  <button id="loc-map-excel" '
      +       'style="margin-left:auto;background:rgba(255,255,255,.15);color:#fff;'
      +             'border:1px solid rgba(255,255,255,.3);border-radius:6px;'
      +             'padding:4px 10px;cursor:pointer;font-size:11px;">📥 엑셀 업로드 (백업)</button>'
      + '  <button id="loc-map-refresh" '
      +       'style="background:rgba(255,255,255,.15);color:#fff;'
      +             'border:1px solid rgba(255,255,255,.3);border-radius:6px;'
      +             'padding:4px 10px;cursor:pointer;font-size:11px;">↻ 새로고침</button>'
      + '  <button id="loc-map-close" '
      +       'style="background:none;border:none;font-size:18px;cursor:pointer;color:#fff;padding:0 4px;">×</button>'
      + '</div>'
      + '<div style="flex:1;display:flex;overflow:hidden;">'
      + '  <div id="loc-map-left" style="width:42%;border-right:1px solid var(--panel-border);'
      +       'display:flex;flex-direction:column;overflow:hidden;"></div>'
      + '  <div id="loc-map-right" style="flex:1;display:flex;flex-direction:column;overflow:hidden;"></div>'
      + '</div>'
      + '<div style="padding:8px 16px;border-top:1px solid var(--panel-border);'
      +     'background:var(--bg-hover);display:flex;gap:8px;align-items:center;flex-shrink:0;">'
      + '  <span id="loc-map-pending-cnt" style="font-size:12px;color:var(--text-muted);"></span>'
      + '  <button id="loc-map-clear" class="btn" style="margin-left:auto;">초기화</button>'
      + '  <button id="loc-map-apply" class="btn btn-primary" disabled>✅ 일괄 적용</button>'
      + '</div>';
    document.body.appendChild(d);
    _modal = d;
    document.getElementById('loc-map-close').onclick   = function() { d.style.display = 'none'; };
    document.getElementById('loc-map-refresh').onclick = _load;
    document.getElementById('loc-map-excel').onclick   = function() {
      if (typeof window.showTonbagLocationUploadModal === 'function') {
        window.showTonbagLocationUploadModal();
      } else {
        _toast('warning', '엑셀 업로드 모달 없음');
      }
    };
    document.getElementById('loc-map-clear').onclick = function() {
      _state.pendingMap = {};
      _renderLeft();
      _renderRight();
      _updateFooter();
    };
    document.getElementById('loc-map-apply').onclick = _applyAll;
    if (typeof window._makeDraggableResizable === 'function') {
      window._makeDraggableResizable(d, document.getElementById('loc-map-hdr'));
    }
    return d;
  }

  /* ── 좌측 LOT 진행률 + 톤백 리스트 ── */
  function _renderLeft() {
    var box = document.getElementById('loc-map-left');
    if (!box) return;
    var lots = _state.lotProgress;
    var lotsHtml = lots.length === 0
      ? '<div style="padding:20px;color:var(--text-muted);">📭 LOT 없음</div>'
      : lots.map(function(p) {
          var pct = p.progress_pct || 0;
          var color = pct === 100 ? '#4caf50' : (pct > 0 ? '#ff9800' : '#f44336');
          var sel = (_state.selectedLot === p.lot_no) ? 'background:rgba(79,195,247,.15);' : '';
          return ''
            + '<div class="loc-map-lot" data-lot="' + _esc(p.lot_no) + '" '
            +     'onclick="window._locMapSelectLot(\'' + _esc(p.lot_no) + '\')" '
            +     'style="cursor:pointer;padding:8px 12px;border-bottom:1px solid var(--panel-border);'
            +           sel + '">'
            + '  <div style="display:flex;align-items:center;gap:8px;">'
            + '    <span style="font-family:Consolas,monospace;font-weight:700;color:var(--accent);">'
            +        _esc(p.lot_no) + '</span>'
            + '    <span style="font-size:11px;color:var(--text-muted);">' + _esc(p.product) + '</span>'
            + '    <span style="margin-left:auto;font-size:11px;color:' + color + ';font-weight:700;">'
            +        p.allocated + '/' + p.total_tonbags + ' (' + pct + '%)</span>'
            + '  </div>'
            + '  <div style="margin-top:4px;height:4px;background:var(--bg-hover);border-radius:2px;overflow:hidden;">'
            + '    <div style="height:100%;width:' + pct + '%;background:' + color + ';"></div>'
            + '  </div>'
            + '</div>';
        }).join('');

    // 선택된 LOT 의 톤백
    var tonbags = _state.selectedLot
      ? _state.tonbags.filter(function(t) { return t.lot_no === _state.selectedLot; })
      : _state.tonbags;

    var tbHtml = tonbags.length === 0
      ? '<div style="padding:20px;color:var(--text-muted);text-align:center;">📭 미배정 톤백 없음</div>'
      : tonbags.map(function(t) {
          var pend = _state.pendingMap[t.id];
          var sel  = _state.selectedIds[t.id];
          var rowBg = pend ? 'background:rgba(76,175,80,.1);'
                          : (sel ? 'background:rgba(79,195,247,.1);' : '');
          return ''
            + '<tr data-tonbag-id="' + t.id + '" '
            +     'onclick="window._locMapToggleTonbag(' + t.id + ', event)" '
            +     'style="cursor:pointer;' + rowBg + '">'
            + '  <td style="padding:4px 8px;text-align:center;width:30px;">'
            + '    <input type="checkbox" ' + (sel ? 'checked' : '') + ' '
            +          'onclick="event.stopPropagation();window._locMapToggleTonbag(' + t.id + ', event);">'
            + '  </td>'
            + '  <td style="padding:4px 8px;font-family:Consolas,monospace;">' + _esc(t.lot_no) + '</td>'
            + '  <td style="padding:4px 8px;text-align:right;">' + _esc(t.sub_lt) + '</td>'
            + '  <td style="padding:4px 8px;text-align:right;">' + (Number(t.weight_kg) || 0).toLocaleString() + '</td>'
            + '  <td style="padding:4px 8px;text-align:center;font-size:10px;">' + _esc(t.packing_type || '?') + '</td>'
            + '  <td style="padding:4px 8px;font-family:Consolas,monospace;font-size:11px;'
            +     (pend ? 'color:#4caf50;font-weight:700;' : 'color:var(--text-muted);') + '">'
            +     _esc(pend || '— 미배정')
            + '  </td>'
            + '</tr>';
        }).join('');

    box.innerHTML = ''
      + '<div style="padding:8px 10px;background:var(--bg-hover);border-bottom:1px solid var(--panel-border);'
      +     'font-size:12px;font-weight:700;flex-shrink:0;">📦 LOT 진행률 (클릭 → 필터)</div>'
      + '<div style="max-height:36%;overflow-y:auto;flex-shrink:0;">' + lotsHtml + '</div>'
      + '<div style="padding:8px 10px;background:var(--bg-hover);border-top:1px solid var(--panel-border);'
      +     'border-bottom:1px solid var(--panel-border);font-size:12px;font-weight:700;flex-shrink:0;'
      +     'display:flex;align-items:center;gap:8px;">'
      + '  <span>📋 미배정 톤백</span>'
      + '  <span style="font-size:10px;color:var(--text-muted);">'
      +     (_state.selectedLot ? '(' + _esc(_state.selectedLot) + ' 필터)' : '(전체)')
      + '  </span>'
      + '  <button onclick="window._locMapClearLotFilter()" '
      +     'style="margin-left:auto;background:none;border:1px solid var(--border);'
      +           'border-radius:4px;padding:1px 6px;font-size:10px;cursor:pointer;color:var(--text-muted);">'
      + '    필터 해제</button>'
      + '</div>'
      + '<div style="flex:1;overflow:auto;">'
      + '  <table style="width:100%;font-size:12px;border-collapse:collapse;">'
      + '    <thead><tr>'
      + '      <th style="padding:4px 8px;background:var(--bg-hover);position:sticky;top:0;">'
      + '        <input type="checkbox" onclick="window._locMapToggleAll(this.checked)">'
      + '      </th>'
      + '      <th style="padding:4px 8px;background:var(--bg-hover);position:sticky;top:0;text-align:left;">LOT</th>'
      + '      <th style="padding:4px 8px;background:var(--bg-hover);position:sticky;top:0;text-align:right;">Sub</th>'
      + '      <th style="padding:4px 8px;background:var(--bg-hover);position:sticky;top:0;text-align:right;">kg</th>'
      + '      <th style="padding:4px 8px;background:var(--bg-hover);position:sticky;top:0;text-align:center;">pack</th>'
      + '      <th style="padding:4px 8px;background:var(--bg-hover);position:sticky;top:0;text-align:left;">매핑 (대기)</th>'
      + '    </tr></thead>'
      + '    <tbody>' + tbHtml + '</tbody>'
      + '  </table>'
      + '</div>';
  }

  /* ── 우측 매핑 입력 영역 ── */
  function _renderRight() {
    var box = document.getElementById('loc-map-right');
    if (!box) return;
    var selIds = Object.keys(_state.selectedIds).filter(function(k){ return _state.selectedIds[k]; });
    var n = selIds.length;

    if (n === 0) {
      box.innerHTML = ''
        + '<div style="padding:30px;text-align:center;color:var(--text-muted);">'
        + '  👈 좌측에서 톤백을 선택하세요<br>'
        + '  <small style="font-size:11px;">체크박스 또는 행 클릭</small>'
        + '</div>';
      return;
    }

    // 선택된 톤백 요약
    var selTb = _state.tonbags.filter(function(t) { return _state.selectedIds[t.id]; });
    var rowsHtml = selTb.map(function(t) {
      var existing = _state.pendingMap[t.id] || '';
      return ''
        + '<tr data-row-tonbag="' + t.id + '">'
        + '  <td style="padding:4px 8px;font-family:Consolas,monospace;font-size:11px;">'
        +     _esc(t.lot_no) + '-' + _esc(t.sub_lt) + '</td>'
        + '  <td style="padding:4px 8px;text-align:right;font-size:11px;">'
        +     (Number(t.weight_kg) || 0).toLocaleString() + 'kg</td>'
        + '  <td style="padding:4px;">'
        + '    <input type="text" id="loc-inp-' + t.id + '" '
        +          'placeholder="G5-04-01-07" '
        +          'value="' + _esc(existing) + '" '
        +          'oninput="window._locMapValidateInput(' + t.id + ')" '
        +          'style="width:140px;padding:3px 6px;font-family:Consolas,monospace;'
        +                'background:var(--bg-hover);color:var(--fg);'
        +                'border:1px solid var(--border);border-radius:4px;font-size:11px;'
        +                'text-transform:uppercase;">'
        + '    <span id="loc-msg-' + t.id + '" style="font-size:10px;margin-left:6px;"></span>'
        + '  </td>'
        + '  <td style="padding:4px;">'
        + '    <span id="loc-cell-' + t.id + '" style="font-size:10px;"></span>'
        + '  </td>'
        + '</tr>';
    }).join('');

    box.innerHTML = ''
      + '<div style="padding:8px 12px;background:var(--bg-hover);border-bottom:1px solid var(--panel-border);'
      +     'font-size:12px;font-weight:700;flex-shrink:0;">'
      + '  📍 선택 톤백 매핑 — ' + n + '개'
      + '  <span style="margin-left:10px;font-size:10px;font-weight:400;color:var(--text-muted);">'
      + '    G5-04-01-07 형식 · 실시간 검증 + 셀 상태 미리보기'
      + '  </span>'
      + '</div>'
      + '<div style="padding:8px 12px;border-bottom:1px solid var(--panel-border);flex-shrink:0;'
      +     'display:flex;gap:6px;align-items:center;background:rgba(33,150,243,.05);">'
      + '  <span style="font-size:11px;color:var(--text-muted);">⚡ 일괄 입력 (선택 전체에 동일 위치 시작값):</span>'
      + '  <input id="loc-bulk-input" type="text" placeholder="G5-04-01-07" '
      +        'style="padding:4px 8px;font-family:Consolas,monospace;background:var(--bg-hover);'
      +              'color:var(--fg);border:1px solid var(--border);border-radius:4px;'
      +              'font-size:11px;width:140px;text-transform:uppercase;">'
      + '  <button class="btn btn-sm" onclick="window._locMapBulkFill()">↓ 채우기</button>'
      + '  <button class="btn btn-sm" onclick="window._locMapBulkAutoInc()" '
      +        'title="첫 위치 입력 후 열을 1씩 증가시켜 자동 채움">↓ 연속 채우기</button>'
      + '</div>'
      + '<div style="flex:1;overflow:auto;">'
      + '  <table style="width:100%;border-collapse:collapse;">'
      + '    <thead><tr>'
      + '      <th style="padding:4px 8px;background:var(--bg-hover);position:sticky;top:0;text-align:left;font-size:11px;">LOT-Sub</th>'
      + '      <th style="padding:4px 8px;background:var(--bg-hover);position:sticky;top:0;text-align:right;font-size:11px;">중량</th>'
      + '      <th style="padding:4px 8px;background:var(--bg-hover);position:sticky;top:0;text-align:left;font-size:11px;">위치 입력</th>'
      + '      <th style="padding:4px 8px;background:var(--bg-hover);position:sticky;top:0;text-align:left;font-size:11px;">셀 상태</th>'
      + '    </tr></thead>'
      + '    <tbody>' + rowsHtml + '</tbody>'
      + '  </table>'
      + '</div>';

    // 기존 pendingMap 값 있으면 즉시 검증 표시
    selTb.forEach(function(t) {
      if (_state.pendingMap[t.id]) {
        window._locMapValidateInput(t.id);
      }
    });
  }

  /* ── 푸터 진행률 ── */
  function _updateFooter() {
    var pend = Object.keys(_state.pendingMap).length;
    document.getElementById('loc-map-pending-cnt').textContent =
      pend > 0 ? '대기 중 ' + pend + '건 (적용 전)' : '';
    var btn = document.getElementById('loc-map-apply');
    btn.disabled = pend === 0;
  }

  /* ── 실시간 검증 + 셀 상태 미리보기 ── */
  var _cellStateCache = {};
  window._locMapValidateInput = function(tonbagId) {
    var inp = document.getElementById('loc-inp-' + tonbagId);
    var msg = document.getElementById('loc-msg-' + tonbagId);
    var cellSpan = document.getElementById('loc-cell-' + tonbagId);
    if (!inp) return;
    inp.value = inp.value.toUpperCase();
    var v = _validateLoc(inp.value);
    if (!inp.value) {
      msg.textContent = '';
      cellSpan.textContent = '';
      delete _state.pendingMap[tonbagId];
      inp.style.borderColor = 'var(--border)';
      _renderLeft();
      _updateFooter();
      return;
    }
    if (!v.ok) {
      msg.textContent = '✗ ' + v.reason;
      msg.style.color = '#f44336';
      cellSpan.textContent = '';
      inp.style.borderColor = '#f44336';
      delete _state.pendingMap[tonbagId];
      _renderLeft();
      _updateFooter();
      return;
    }
    msg.textContent = '✓';
    msg.style.color = '#4caf50';
    inp.style.borderColor = '#4caf50';
    _state.pendingMap[tonbagId] = v.normalized;

    // 셀 상태 미리보기 (캐시 + API)
    var loc = v.normalized;
    if (_cellStateCache[loc]) {
      _renderCellState(cellSpan, _cellStateCache[loc]);
    } else {
      cellSpan.textContent = '⏳';
      fetch(_api() + '/api/warehouse/cell-state?location=' + encodeURIComponent(loc))
        .then(function(r) { return r.json(); })
        .then(function(res) {
          if (res && res.ok && res.data) {
            _cellStateCache[loc] = res.data;
            _renderCellState(cellSpan, res.data);
          } else {
            cellSpan.textContent = '?';
          }
        })
        .catch(function() { cellSpan.textContent = '?'; });
    }
    _renderLeft();
    _updateFooter();
  };

  function _renderCellState(span, st) {
    var s = (st.state || 'UNKNOWN').toUpperCase();
    var b = CELL_BADGES[s] || CELL_BADGES.UNKNOWN;
    span.innerHTML = '<span style="display:inline-block;padding:1px 6px;border-radius:8px;'
      + 'background:' + b.bg + ';color:' + b.fg + ';font-weight:700;font-size:10px;">'
      + b.text + ' (' + st.active_count + '/' + st.capacity + ')</span>';
  }

  /* ── 일괄 입력 헬퍼 ── */
  window._locMapBulkFill = function() {
    var v = document.getElementById('loc-bulk-input').value;
    if (!v) return;
    var chk = _validateLoc(v);
    if (!chk.ok) { _toast('error', '형식 오류: ' + chk.reason); return; }
    var selIds = Object.keys(_state.selectedIds).filter(function(k){ return _state.selectedIds[k]; });
    selIds.forEach(function(id) {
      var inp = document.getElementById('loc-inp-' + id);
      if (inp) { inp.value = chk.normalized; window._locMapValidateInput(id); }
    });
  };

  window._locMapBulkAutoInc = function() {
    var v = document.getElementById('loc-bulk-input').value;
    if (!v) { _toast('warning', '시작 위치 입력 필요'); return; }
    var chk = _validateLoc(v);
    if (!chk.ok) { _toast('error', '형식 오류: ' + chk.reason); return; }
    var selIds = Object.keys(_state.selectedIds).filter(function(k){ return _state.selectedIds[k]; });
    var col = chk.col;
    selIds.forEach(function(id) {
      if (col > 31) return;
      var locStr = 'G' + chk.dong + '-' + String(chk.rack).padStart(2,'0')
        + '-' + String(col).padStart(2,'0') + '-' + String(chk.level).padStart(2,'0');
      var inp = document.getElementById('loc-inp-' + id);
      if (inp) { inp.value = locStr; window._locMapValidateInput(id); }
      col++;
    });
  };

  /* ── 톤백 선택 ── */
  window._locMapToggleTonbag = function(tonbagId, ev) {
    if (ev && ev.target && ev.target.tagName === 'INPUT' && ev.target.type === 'checkbox') {
      _state.selectedIds[tonbagId] = ev.target.checked;
    } else {
      _state.selectedIds[tonbagId] = !_state.selectedIds[tonbagId];
    }
    _renderLeft();
    _renderRight();
  };

  window._locMapToggleAll = function(checked) {
    var tonbags = _state.selectedLot
      ? _state.tonbags.filter(function(t) { return t.lot_no === _state.selectedLot; })
      : _state.tonbags;
    tonbags.forEach(function(t) { _state.selectedIds[t.id] = checked; });
    _renderLeft();
    _renderRight();
  };

  window._locMapSelectLot = function(lotNo) {
    _state.selectedLot = (_state.selectedLot === lotNo) ? null : lotNo;
    _renderLeft();
  };
  window._locMapClearLotFilter = function() {
    _state.selectedLot = null;
    _renderLeft();
  };

  /* ── 일괄 적용 ── */
  function _applyAll() {
    var entries = Object.keys(_state.pendingMap).map(function(id) {
      return { tonbag_id: parseInt(id, 10), location: _state.pendingMap[id] };
    });
    if (entries.length === 0) {
      _toast('info', '대기 매핑 없음');
      return;
    }
    var btn = document.getElementById('loc-map-apply');
    btn.disabled = true;
    btn.textContent = '⏳ 적용 중...';
    fetch(_api() + '/api/inventory/assign-locations-bulk', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({
        assignments: entries,
        operator:    'user',
        note:        'v8.6.8 위치 매핑 워크플로우',
      }),
    })
      .then(function(r) { return r.json(); })
      .then(function(res) {
        btn.disabled = false;
        btn.textContent = '✅ 일괄 적용';
        if (res && res.ok) {
          var d = res.data || {};
          _toast(d.fail_count ? 'warning' : 'success',
                 '성공 ' + d.success_count + '건 / 실패 ' + (d.fail_count || 0) + '건');
          if (d.errors && d.errors.length) {
            console.warn('[loc-map] 실패 항목:', d.errors);
            var msg = '실패 ' + d.fail_count + '건 — 콘솔에서 확인하세요\n\n';
            msg += d.errors.slice(0, 5).map(function(e){
              return '• tonbag ' + e.tonbag_id + ': ' + e.reason;
            }).join('\n');
            if (d.errors.length > 5) msg += '\n... (+' + (d.errors.length - 5) + '건)';
            alert(msg);
          }
          _state.pendingMap = {};
          _state.selectedIds = {};
          _load();   // 새로고침
        } else {
          _toast('error', '적용 실패: ' + (res && res.error || '알 수 없음'));
        }
      })
      .catch(function(e) {
        btn.disabled = false;
        btn.textContent = '✅ 일괄 적용';
        _toast('error', '요청 실패: ' + e.message);
      });
  }

  /* ── 로드 ── */
  function _load() {
    fetch(_api() + '/api/inventory/unallocated-tonbags')
      .then(function(r) { return r.json(); })
      .then(function(res) {
        if (!res || !res.ok) {
          _toast('error', '로딩 실패');
          return;
        }
        var d = res.data || {};
        _state.tonbags     = d.tonbags || [];
        _state.lotProgress = d.lot_progress || [];
        _state.summary     = d.summary || {};
        _state.selectedLot = null;
        _state.selectedIds = {};
        // pendingMap은 유지하지 않음 (적용 후 reset)

        var s = _state.summary;
        document.getElementById('loc-map-summary').textContent =
          '— LOT ' + (s.lot_count || 0) + '개 · '
          + '완료 ' + (s.lot_done || 0) + ' / 부분 ' + (s.lot_partial || 0) + ' / 미배정 ' + (s.lot_pending || 0)
          + ' · 톤백 ' + (s.allocated || 0) + '/' + (s.total || 0) + ' (' + (s.progress_pct || 0) + '%)';

        _renderLeft();
        _renderRight();
        _updateFooter();
      })
      .catch(function(e) {
        _toast('error', '요청 실패: ' + e.message);
      });
  }

  /* 공개 함수 */
  window.showLocationMappingModal = function() {
    _ensureModal();
    _load();
  };

})();
