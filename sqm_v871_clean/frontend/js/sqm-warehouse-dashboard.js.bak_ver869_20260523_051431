/* =======================================================================
   sqm-warehouse-dashboard.js  (v8.6.8)
   📊 창고 셀 점유 대시보드 — 5동/6동 평면도

   동작:
     - 상단: 전체 요약 KPI (총 6,572셀, EMPTY/OCCUPIED/HALF/MIXED 카운트)
     - 좌측: 동(5/6) + 랙(1~16) 선택 트리
     - 중앙: 선택된 랙의 (열 × 층) 평면 그리드
              · EMPTY  → 회색
              · OCCUPIED → 초록
              · HALF   → 노랑
              · OVER/MIXED → 빨강
     - 우측: 셀 클릭 시 상세 (활성 톤백 + LOT)

   API:
     GET /api/warehouse/summary
     GET /api/warehouse/cell-grid?dong=5&rack=4
     GET /api/warehouse/cell-state?location=G5-04-01-07

   호출:
     window.showWarehouseDashboard();
   ======================================================================= */
(function () {
  'use strict';
  if (window.__SQM_WAREHOUSE_DASHBOARD_INSTALLED__) return;
  window.__SQM_WAREHOUSE_DASHBOARD_INSTALLED__ = true;

  function _api()         { return (typeof API !== 'undefined') ? API : ''; }
  function _toast(t, msg) { if (window.showToast) window.showToast(t, msg); }
  function _esc(s) {
    if (window.escapeHtml) return window.escapeHtml(s);
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  /* 셀 상태 → 색상 */
  var STATE_COLORS = {
    EMPTY:    { bg: '#37474f', border: '#546e7a', text: '⬜' },
    OCCUPIED: { bg: '#1b5e20', border: '#43a047', text: '🟦' },
    HALF:     { bg: '#f57f17', border: '#ff9800', text: '🟨' },
    OVER:     { bg: '#b71c1c', border: '#e53935', text: '⚠' },
    MIXED:    { bg: '#b71c1c', border: '#e53935', text: '⚠' },
    UNKNOWN:  { bg: '#212121', border: '#424242', text: '?' },
  };

  /* 랙별 최대 층 */
  var _rackLvMax = {};
  for (var r = 1; r <= 16; r++) {
    _rackLvMax[r] = (r >= 4 && r <= 13) ? 7 : 6;
  }

  var _state = {
    dong: 5,
    rack: 1,
    summary: null,
    grid: null,
    selectedCell: null,
  };

  /* ── 모달 ── */
  var _modal = null;
  function _ensureModal() {
    if (_modal && document.body.contains(_modal)) {
      _modal.style.display = 'flex';
      return _modal;
    }
    var d = document.createElement('div');
    d.id = 'sqm-warehouse-dashboard';
    d.style.cssText = ''
      + 'position:fixed;top:30px;left:50%;transform:translateX(-50%);'
      + 'width:min(1600px,98vw);height:92vh;background:var(--bg-card);'
      + 'border:2px solid var(--accent,#4fc3f7);border-radius:10px;'
      + 'box-shadow:0 8px 40px rgba(0,0,0,.6);z-index:10080;'
      + 'display:flex;flex-direction:column;overflow:hidden;';
    d.innerHTML = ''
      + '<div id="wh-dash-hdr" style="cursor:move;background:linear-gradient(90deg,#0d47a1,#1976d2);'
      +     'color:#fff;padding:10px 16px;display:flex;align-items:center;gap:10px;flex-shrink:0;">'
      + '  <span style="font-size:16px;font-weight:700;">📊 창고 셀 점유 대시보드</span>'
      + '  <span id="wh-dash-summary" style="font-size:11px;opacity:.9;"></span>'
      + '  <button id="wh-dash-refresh" '
      +       'style="margin-left:auto;background:rgba(255,255,255,.15);color:#fff;'
      +             'border:1px solid rgba(255,255,255,.3);border-radius:6px;'
      +             'padding:4px 10px;cursor:pointer;font-size:11px;">↻ 새로고침</button>'
      + '  <button id="wh-dash-close" '
      +       'style="background:none;border:none;font-size:18px;cursor:pointer;color:#fff;padding:0 4px;">×</button>'
      + '</div>'
      /* KPI 카드 */
      + '<div id="wh-dash-kpi" style="padding:10px 16px;border-bottom:1px solid var(--panel-border);'
      +     'background:var(--bg-hover);flex-shrink:0;display:flex;gap:8px;flex-wrap:wrap;"></div>'
      /* 본체 — 3분할 */
      + '<div style="flex:1;display:flex;overflow:hidden;">'
      + '  <div id="wh-dash-left" style="width:180px;border-right:1px solid var(--panel-border);'
      +       'overflow-y:auto;flex-shrink:0;background:var(--bg);"></div>'
      + '  <div id="wh-dash-grid" style="flex:1;overflow:auto;padding:12px;"></div>'
      + '  <div id="wh-dash-detail" style="width:300px;border-left:1px solid var(--panel-border);'
      +       'overflow-y:auto;flex-shrink:0;background:var(--bg);padding:10px;"></div>'
      + '</div>'
      /* 범례 */
      + '<div style="padding:6px 16px;border-top:1px solid var(--panel-border);'
      +     'background:var(--bg-hover);display:flex;gap:14px;font-size:11px;flex-shrink:0;align-items:center;">'
      + '  <span style="color:var(--text-muted);">범례:</span>'
      + _legendItem('EMPTY')
      + _legendItem('OCCUPIED')
      + _legendItem('HALF')
      + _legendItem('OVER')
      + _legendItem('MIXED')
      + '</div>';
    document.body.appendChild(d);
    _modal = d;
    document.getElementById('wh-dash-close').onclick = function() { d.style.display = 'none'; };
    document.getElementById('wh-dash-refresh').onclick = _loadAll;
    if (typeof window._makeDraggableResizable === 'function') {
      window._makeDraggableResizable(d, document.getElementById('wh-dash-hdr'));
    }
    return d;
  }

  function _legendItem(state) {
    var c = STATE_COLORS[state];
    return '<span style="display:inline-flex;align-items:center;gap:4px;">'
      + '<span style="display:inline-block;width:14px;height:14px;border-radius:3px;'
      +       'background:' + c.bg + ';border:1px solid ' + c.border + ';"></span>'
      + state + '</span>';
  }

  /* ── 상단 KPI 카드 ── */
  function _renderKpi() {
    var s = _state.summary || {};
    var bd = s.by_dong || {};
    function card(label, value, color) {
      return ''
        + '<div style="background:var(--bg-card);border:1px solid var(--panel-border);'
        +     'border-radius:6px;padding:6px 12px;min-width:110px;">'
        + '<div style="font-size:10px;color:var(--text-muted);">' + label + '</div>'
        + '<div style="font-size:15px;font-weight:700;' + (color ? 'color:' + color + ';' : '') + '">'
        +     value + '</div>'
        + '</div>';
    }
    var html = ''
      + card('총 셀',         (s.total_cells || 0).toLocaleString())
      + card('EMPTY',         (s.empty_cells || 0).toLocaleString(),  '#b0bec5')
      + card('OCCUPIED',      (s.occupied_cells || 0).toLocaleString(), '#4caf50')
      + card('HALF',          (s.half_cells || 0).toLocaleString(),    '#f57f17')
      + card('OVER',          (s.over_cells || 0).toLocaleString(),    '#f44336')
      + card('MIXED',         (s.mixed_cells || 0).toLocaleString(),   '#f44336')
      + card('점유율',        (s.occupancy_rate || 0) + '%')
      + card('활성 톤백',     (s.active_tonbags || 0).toLocaleString())
      + card('총 중량',       ((s.total_weight_kg || 0) / 1000).toFixed(1) + ' t');

    // 동별 미니 카드
    [5, 6].forEach(function(dong) {
      var v = bd[dong] || {};
      var sum = (v.occupied || 0) + (v.half || 0) + (v.over || 0) + (v.mixed || 0);
      html += '<div style="background:var(--bg-card);border:1px solid var(--panel-border);'
        + 'border-radius:6px;padding:6px 12px;min-width:140px;">'
        + '<div style="font-size:10px;color:var(--text-muted);">' + dong + '동 점유</div>'
        + '<div style="font-size:13px;">'
        + '<span style="color:#4caf50;">🟦' + (v.occupied || 0) + '</span> · '
        + '<span style="color:#f57f17;">🟨' + (v.half || 0) + '</span> · '
        + '<span style="color:#f44336;">⚠' + ((v.over || 0) + (v.mixed || 0)) + '</span>'
        + '</div></div>';
    });
    document.getElementById('wh-dash-kpi').innerHTML = html;
    document.getElementById('wh-dash-summary').textContent =
      '— 점유 ' + (s.occupancy_rate || 0) + '% / 활성 ' + (s.active_tonbags || 0) + '톤백';
  }

  /* ── 좌측 동·랙 선택 ── */
  function _renderLeftNav() {
    var box = document.getElementById('wh-dash-left');
    var html = '';
    [5, 6].forEach(function(dong) {
      var sel = (_state.dong === dong);
      html += '<div style="padding:8px 12px;font-weight:700;background:' + (sel ? 'rgba(33,150,243,.2)' : 'var(--bg-hover)')
        + ';border-bottom:1px solid var(--panel-border);cursor:pointer;" '
        + 'onclick="window._whDashSelectDong(' + dong + ')">'
        + '🏭 ' + dong + '동'
        + '</div>';
      if (sel) {
        for (var r = 1; r <= 16; r++) {
          var rSel = (_state.rack === r);
          var maxLv = _rackLvMax[r];
          html += '<div style="padding:4px 12px 4px 24px;font-size:11px;cursor:pointer;'
            + (rSel ? 'background:rgba(33,150,243,.15);color:var(--accent);font-weight:700;' : '')
            + '" onclick="window._whDashSelectRack(' + r + ')">'
            + '🗄 랙 ' + String(r).padStart(2,'0') + ' '
            + '<span style="font-size:10px;color:var(--text-muted);">(31×' + maxLv + ')</span>'
            + '</div>';
        }
      }
    });
    box.innerHTML = html;
  }

  /* ── 중앙 그리드 ── */
  function _renderGrid() {
    var box = document.getElementById('wh-dash-grid');
    if (!_state.grid) {
      box.innerHTML = '<div style="text-align:center;padding:40px;color:var(--text-muted);">⏳ 그리드 로딩...</div>';
      return;
    }
    var g = _state.grid;
    var cells = g.cells || [];
    var maxLv = g.max_level || 7;

    // 셀을 (col, level) 로 인덱싱
    var byCoord = {};
    cells.forEach(function(c) { byCoord[c.col + '_' + c.level] = c; });

    var html = ''
      + '<h3 style="margin:0 0 12px;font-size:14px;color:var(--accent);">'
      + '🗺 ' + _state.dong + '동 ' + String(_state.rack).padStart(2,'0') + '번 랙 평면도 '
      + '<small style="color:var(--text-muted);font-size:11px;font-weight:400;">'
      + '— 31열 × ' + maxLv + '층 (총 ' + (31 * maxLv) + '셀)</small></h3>';

    // 테이블 형태로 — 행=층(위에서 아래), 열=열 번호 (1~31)
    html += '<table style="border-collapse:collapse;font-size:10px;">';
    html += '<thead><tr><th style="padding:2px 4px;color:var(--text-muted);font-weight:400;">층\\열</th>';
    for (var col = 1; col <= 31; col++) {
      html += '<th style="padding:2px;color:var(--text-muted);font-weight:400;width:26px;text-align:center;">'
        + String(col).padStart(2,'0') + '</th>';
    }
    html += '</tr></thead><tbody>';

    for (var lv = maxLv; lv >= 1; lv--) {
      html += '<tr>';
      html += '<td style="padding:2px 6px;color:var(--text-muted);text-align:right;font-weight:700;">'
        + 'L' + String(lv).padStart(2,'0') + '</td>';
      for (var col2 = 1; col2 <= 31; col2++) {
        var c = byCoord[col2 + '_' + lv];
        if (!c) {
          html += '<td style="width:26px;height:22px;border:1px dashed #444;"></td>';
          continue;
        }
        var st = STATE_COLORS[c.state] || STATE_COLORS.UNKNOWN;
        var isSel = (_state.selectedCell && _state.selectedCell.location === c.location);
        html += '<td onclick="window._whDashSelectCell(\'' + _esc(c.location) + '\')" '
          + 'title="' + _esc(c.location) + ' / ' + c.state + ' (' + c.active_count + '/' + c.capacity + ')" '
          + 'style="width:26px;height:22px;border:1px solid ' + st.border + ';'
          + 'background:' + st.bg + ';color:#fff;text-align:center;cursor:pointer;font-size:9px;'
          + (isSel ? 'outline:3px solid #4fc3f7;outline-offset:-1px;' : '')
          + '">'
          + (c.state === 'EMPTY' ? '' : c.active_count)
          + '</td>';
      }
      html += '</tr>';
    }
    html += '</tbody></table>';

    // 랙 점유 미니 통계
    var rackStats = { EMPTY: 0, OCCUPIED: 0, HALF: 0, OVER: 0, MIXED: 0 };
    cells.forEach(function(c) { rackStats[c.state] = (rackStats[c.state] || 0) + 1; });
    html += '<div style="margin-top:12px;font-size:11px;color:var(--text-muted);">'
      + '이 랙: '
      + '<span style="color:#b0bec5;">EMPTY ' + (rackStats.EMPTY || 0) + '</span> · '
      + '<span style="color:#4caf50;">OCCUPIED ' + (rackStats.OCCUPIED || 0) + '</span> · '
      + '<span style="color:#f57f17;">HALF ' + (rackStats.HALF || 0) + '</span> · '
      + '<span style="color:#f44336;">OVER/MIXED ' + ((rackStats.OVER || 0) + (rackStats.MIXED || 0)) + '</span>'
      + '</div>';

    box.innerHTML = html;
  }

  /* ── 우측 셀 상세 ── */
  function _renderDetail() {
    var box = document.getElementById('wh-dash-detail');
    if (!_state.selectedCell) {
      box.innerHTML = '<div style="color:var(--text-muted);font-size:12px;text-align:center;padding:20px;">'
        + '🖱 셀을 클릭하면<br>여기에 상세 정보 표시'
        + '</div>';
      return;
    }
    var st = _state.selectedCell;
    var rep = STATE_COLORS[st.state] || STATE_COLORS.UNKNOWN;
    var html = ''
      + '<div style="font-family:Consolas,monospace;font-size:14px;font-weight:700;color:var(--accent);'
      +     'padding:6px 8px;background:var(--bg-hover);border-radius:6px;margin-bottom:8px;">'
      + '  📍 ' + _esc(st.location)
      + '</div>'
      + '<div style="display:inline-block;padding:3px 10px;border-radius:10px;'
      +     'background:' + rep.bg + ';color:#fff;font-weight:700;font-size:11px;margin-bottom:8px;">'
      + rep.text + ' ' + _esc(st.state) + ' (' + st.active_count + '/' + st.capacity + ')'
      + '</div>'
      + '<div style="font-size:11px;color:var(--text-muted);margin-bottom:8px;">'
      + 'packing_type: <b>' + _esc(st.packing_type || '?') + '</b>'
      + '</div>';

    var tbs = st.tonbags || [];
    if (tbs.length === 0) {
      html += '<div style="padding:10px;text-align:center;color:var(--text-muted);font-size:11px;">'
        + '비어있음'
        + '</div>';
    } else {
      html += '<div style="font-size:11px;font-weight:700;color:var(--text-muted);margin:4px 0 4px;">'
        + '활성 톤백 (' + tbs.length + '개)</div>';
      tbs.forEach(function(t) {
        html += '<div style="background:var(--bg-card);border:1px solid var(--panel-border);'
          + 'border-radius:4px;padding:6px 8px;margin-bottom:4px;font-size:11px;">'
          + '<div style="font-family:Consolas,monospace;color:var(--accent);">'
          + _esc(t.lot_no) + '-' + _esc(t.sub_lt)
          + '</div>'
          + '<div style="color:var(--text-muted);">'
          + (Number(t.weight_kg) || 0).toLocaleString() + 'kg · ' + _esc(t.status)
          + '</div>'
          + '</div>';
      });
    }
    if (st.validation && !st.validation.ok) {
      html += '<div style="color:#f44336;font-size:11px;margin-top:8px;">'
        + '⚠ ' + _esc(st.validation.reason || '') + '</div>';
    }
    box.innerHTML = html;
  }

  /* ── 셀 선택 → 상세 로드 ── */
  window._whDashSelectCell = function(loc) {
    fetch(_api() + '/api/warehouse/cell-state?location=' + encodeURIComponent(loc))
      .then(function(r) { return r.json(); })
      .then(function(res) {
        if (res && res.ok && res.data) {
          _state.selectedCell = res.data;
          _renderDetail();
          _renderGrid();   // outline 갱신
        }
      })
      .catch(function(e) { _toast('error', '셀 조회 실패'); });
  };

  window._whDashSelectDong = function(dong) {
    _state.dong = dong;
    _state.rack = 1;
    _renderLeftNav();
    _loadGrid();
  };

  window._whDashSelectRack = function(rack) {
    _state.rack = rack;
    _renderLeftNav();
    _loadGrid();
  };

  /* ── 데이터 로드 ── */
  function _loadSummary() {
    return fetch(_api() + '/api/warehouse/summary')
      .then(function(r) { return r.json(); })
      .then(function(res) {
        if (res && res.ok) {
          _state.summary = res.data;
          _renderKpi();
        }
      });
  }
  function _loadGrid() {
    document.getElementById('wh-dash-grid').innerHTML =
      '<div style="text-align:center;padding:40px;color:var(--text-muted);">⏳ 로딩...</div>';
    return fetch(_api() + '/api/warehouse/cell-grid?dong=' + _state.dong + '&rack=' + _state.rack)
      .then(function(r) { return r.json(); })
      .then(function(res) {
        if (res && res.ok) {
          _state.grid = res.data;
          _state.selectedCell = null;
          _renderGrid();
          _renderDetail();
        } else {
          document.getElementById('wh-dash-grid').innerHTML =
            '<div style="text-align:center;padding:40px;color:var(--danger);">로딩 실패</div>';
        }
      })
      .catch(function() {
        document.getElementById('wh-dash-grid').innerHTML =
          '<div style="text-align:center;padding:40px;color:var(--danger);">요청 실패</div>';
      });
  }
  function _loadAll() {
    _loadSummary();
    _loadGrid();
  }

  /* 공개 함수 */
  window.showWarehouseDashboard = function() {
    _ensureModal();
    _renderLeftNav();
    _renderDetail();
    _loadAll();
  };

})();
