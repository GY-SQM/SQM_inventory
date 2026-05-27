/* =======================================================================
   sqm-warehouse-dashboard.js  (v8.7.0)
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
    EMPTY:    { bg: 'transparent', border: 'transparent', text: '' },
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
      + '  <div style="flex:1;display:flex;flex-direction:column;overflow:hidden;">'
      + '    <div id="wh-dash-grid" style="overflow:auto;padding:12px;flex:0 0 auto;"></div>'
      + '    <div id="wh-rack-lot-table" style="flex:1;overflow:auto;padding:0 12px 12px;border-top:1px solid var(--panel-border,#37474f);"></div>'
      + '  </div>'
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
  // 랙별 점유율 캐시
  var _rackPctCache = {};

  function _refreshRackPct(cb) {
    fetch(_api() + '/api/warehouse/rack-heatmap')
      .then(function(r){ return r.json(); })
      .then(function(res){
        if (res && res.ok) {
          _rackPctCache = {};
          (res.data.racks || []).forEach(function(r){
            _rackPctCache[r.dong+'_'+r.rack] = r.total>0 ? Math.round(r.occupied/r.total*100) : 0;
          });
          _rackPctCache.__dong_summary = res.data.dong_summary || {};
          _rackPctCache.__lots_by_dong_rack = {};
          (res.data.racks || []).forEach(function(r){
            _rackPctCache.__lots_by_dong_rack[r.dong+'_'+r.rack] = r.lots || [];
          });
        }
        if (cb) cb();
      })
      .catch(function(){ if(cb) cb(); });
  }

  function _renderLeftNav() {
    var box = document.getElementById('wh-dash-left');
    var html = '';
    [5, 6].forEach(function(dong) {
      var sel = (_state.dong === dong);
      var ds  = (_rackPctCache.__dong_summary || {})[String(dong)] || {};
      var dPct = ds.occupancy_pct != null ? ds.occupancy_pct : '';
      var dColor = ds.alert_90 ? '#e53935' : (ds.occupancy_pct>=80 ? '#fb8c00' : '#4fc3f7');
      html += '<div style="padding:10px 12px;font-size:15px;font-weight:800;'
        + 'background:' + (sel ? 'rgba(33,150,243,.22)' : 'var(--bg-hover)') + ';'
        + 'border-bottom:2px solid var(--panel-border);cursor:pointer;'
        + 'display:flex;align-items:center;gap:6px;" '
        + 'onclick="window._whDashSelectDong(' + dong + ')" '
        + 'title="' + dong + '동 전체 LOT 목록 보기">'
        + '🏭 ' + dong + '동'
        + (dPct !== '' ? '<span style="margin-left:auto;font-size:13px;font-weight:800;color:' + dColor + ';">' + dPct + '%</span>' : '')
        + '</div>';
      if (sel) {
        for (var r = 1; r <= 16; r++) {
          var rSel = (_state.rack === r);
          var maxLv = _rackLvMax[r];
          var rPct  = _rackPctCache[dong+'_'+r];
          var rPctTxt = (rPct != null) ? rPct + '%' : '—';
          var rColor  = rPct>=80 ? '#ef9a9a' : rPct>=50 ? '#ffcc80' : rPct>0 ? '#a5d6a7' : '#546e7a';
          html += '<div style="padding:5px 12px 5px 20px;font-size:12px;cursor:pointer;'
            + 'display:flex;align-items:center;gap:4px;'
            + (rSel ? 'background:rgba(33,150,243,.15);color:var(--accent);font-weight:700;' : 'color:var(--text);')
            + 'border-bottom:1px solid rgba(255,255,255,.04);" '
            + 'onclick="window._whDashSelectRack(' + r + ')">'
            + '<span>🗄 랙 ' + String(r).padStart(2,'0') + '</span>'
            + '<span style="font-size:10px;color:var(--text-muted);">(31×' + maxLv + ')</span>'
            + '<span style="margin-left:auto;font-size:11px;font-weight:700;color:' + rColor + ';">' + rPctTxt + '</span>'
            + '</div>';
        }
      }
    });
    box.innerHTML = html;
  }

  /* ── 중앙 그리드 ── */
  /* LOT 색상 팔레트 */
  var _WD_LOT_PALETTE = [
    '#1565c0','#6a1b9a','#00695c','#e65100','#558b2f',
    '#ad1457','#0277bd','#4527a0','#2e7d32','#c62828',
    '#37474f','#4e342e','#00838f','#ef6c00','#5c6bc0',
    '#7b1fa2','#0288d1','#388e3c','#d84315','#1976d2',
  ];
  var _wdLotColorMap = {}, _wdColorIdx = 0;
  function _wdLotColor(lot) {
    if (!lot) return STATE_COLORS.OCCUPIED.bg;
    if (!_wdLotColorMap[lot]) { _wdLotColorMap[lot] = _WD_LOT_PALETTE[_wdColorIdx % _WD_LOT_PALETTE.length]; _wdColorIdx++; }
    return _wdLotColorMap[lot];
  }

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
          html += '<td style="width:26px;height:22px;"></td>';
          continue;
        }
        var st = STATE_COLORS[c.state] || STATE_COLORS.UNKNOWN;
        var cellBg = ((c.state==='OCCUPIED'||c.state==='HALF') && c.lot_no) ? _wdLotColor(c.lot_no) : st.bg;
        var cellBd = ((c.state==='OCCUPIED'||c.state==='HALF') && c.lot_no) ? cellBg : st.border;
        var isSel = (_state.selectedCell && _state.selectedCell.location === c.location);
        html += '<td onclick="window._whDashSelectCell(\'' + _esc(c.location) + '\')" '
          + 'title="' + _esc(c.location) + ' / ' + c.state + ' [' + _esc(c.lot_no||'') + '] (' + c.active_count + '/' + c.capacity + ')" '
          + 'style="width:26px;height:22px;border:1px solid ' + cellBd + ';'
          + 'background:' + cellBg + ';text-align:center;cursor:' + (c.state === 'EMPTY' ? 'default' : 'pointer') + ';font-size:9px;'
          + (isSel ? 'outline:3px solid #4fc3f7;outline-offset:-1px;' : '')
          + '">'
          + ''
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
    _state.rack = null;   // 랙 선택 없음
    _renderLeftNav();
    _showDongRackSummary(dong);   // 메인 영역에 랙 요약 테이블
  };

  window._whDashSelectRack = function(rack) {
    _state.rack = rack;
    _renderLeftNav();
    _loadGrid();
    _showRackLotTable(_state.dong, rack);
  };

  /* ═══════════════════════════════════════════════════════════════════
     동 클릭 → 메인 영역에 랙 요약 테이블
     컬럼: 순번 | 랙번호 | 품목(제품) | LOT 개수 | 점유율
     ═══════════════════════════════════════════════════════════════════ */
  function _showDongRackSummary(dong) {
    // 그리드/LOT 테이블 초기화
    var grid = document.getElementById('wh-dash-grid');
    var lotBox = document.getElementById('wh-rack-lot-table');
    if (grid)   grid.innerHTML = '';
    if (lotBox) lotBox.innerHTML = '';

    // 메인 영역을 요약 테이블로 사용 (wh-dash-grid에 출력)
    if (!grid) return;
    grid.innerHTML = '<div style="padding:12px;text-align:center;color:var(--text-muted);font-size:12px;">⏳ 로딩중...</div>';

    function _render(racks) {
      // 이 동의 랙들만 필터
      var dongRacks = racks.filter(function(r){ return r.dong === dong; });
      if (dongRacks.length === 0) {
        grid.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text-muted);">데이터 없음</div>';
        return;
      }

      // 각 랙에서 대표 품목 추출 (dominant_lot 기반 lot-detail API)
      // 우선 랙 기본 데이터로 테이블 렌더 후 품목을 비동기 업데이트
      var html = '<div style="padding:8px 0 10px;font-size:13px;font-weight:800;color:var(--accent,#4fc3f7);">'
        + '🏭 ' + dong + '동 — 랙별 현황 (1~16번 랙)'
        + '</div>';

      html += '<table style="width:100%;border-collapse:collapse;font-size:13px;">'
        + '<thead><tr style="background:var(--bg-hover,#1a2027);position:sticky;top:0;z-index:2;">'
        + '<th style="text-align:center;padding:8px 8px;color:var(--text-muted);font-weight:700;border-bottom:2px solid var(--accent);width:46px;">순번</th>'
        + '<th style="text-align:center;padding:8px 8px;color:var(--text-muted);font-weight:700;border-bottom:2px solid var(--accent);width:70px;">랙 번호</th>'
        + '<th style="text-align:left;padding:8px 12px;color:var(--text-muted);font-weight:700;border-bottom:2px solid var(--accent);">품목(제품)</th>'
        + '<th style="text-align:right;padding:8px 10px;color:var(--text-muted);font-weight:700;border-bottom:2px solid var(--accent);width:80px;">LOT 수</th>'
        + '<th style="text-align:right;padding:8px 10px;color:var(--text-muted);font-weight:700;border-bottom:2px solid var(--accent);width:80px;">점유율</th>'
        + '</tr></thead><tbody id="wh-dong-rack-tbody">';

      dongRacks.forEach(function(r, i) {
        var pct      = r.total>0 ? Math.round(r.occupied/r.total*100) : 0;
        var pctColor = pct>=80 ? '#ef9a9a' : pct>=50 ? '#ffcc80' : pct>0 ? '#a5d6a7' : 'var(--text-muted,#90a4ae)';
        var barW     = pct;
        var bg       = i%2===0 ? 'var(--bg,#13191f)' : 'var(--bg-hover,#1a2027)';
        var lotCount = (r.lots||[]).length;

        html += '<tr id="rack-row-'+r.rack+'" style="background:'+bg+';border-bottom:1px solid rgba(255,255,255,.05);cursor:pointer;" '
          + 'onclick="window._whDashSelectRack('+r.rack+')" >'
          + '<td style="padding:8px 8px;text-align:center;font-size:12px;color:var(--text-muted);">'+(i+1)+'</td>'
          + '<td style="padding:8px 8px;text-align:center;font-weight:800;font-size:14px;color:var(--accent,#4fc3f7);">'
          +   String(r.rack).padStart(2,'0')+'번</td>'
          + '<td id="rack-product-'+r.rack+'" style="padding:8px 12px;font-size:12px;color:var(--text-muted);">'
          +   (r.dominant_lot ? '<span style="font-size:10px;color:var(--text-muted);">로딩중...</span>' : '—')+'</td>'
          + '<td style="padding:8px 10px;text-align:right;font-weight:700;font-size:13px;">'+lotCount+'개</td>'
          + '<td style="padding:8px 10px;text-align:right;">'
          +   '<div style="display:flex;align-items:center;gap:6px;justify-content:flex-end;">'
          +   '<div style="width:60px;height:6px;background:rgba(255,255,255,.08);border-radius:3px;overflow:hidden;">'
          +     '<div style="width:'+barW+'%;height:100%;background:'+pctColor+';border-radius:3px;"></div>'
          +   '</div>'
          +   '<span style="font-weight:800;font-size:13px;color:'+pctColor+';min-width:36px;text-align:right;">'+pct+'%</span>'
          +   '</div>'
          + '</td>'
          + '</tr>';
      });
      html += '</tbody></table>';
      html += '<div style="padding:8px 0 4px;font-size:11px;color:var(--text-muted);">💡 랙 행을 클릭하면 해당 랙의 셀 평면도와 LOT 목록이 표시됩니다</div>';

      grid.innerHTML = html;

      // 비동기로 품목(제품) 정보 업데이트
      dongRacks.forEach(function(r) {
        if (!r.dominant_lot) return;
        var cell = document.getElementById('rack-product-'+r.rack);
        if (!cell) return;
        fetch(_api()+'/api/actions/lot-detail/'+encodeURIComponent(r.dominant_lot))
          .then(function(res){return res.json();})
          .then(function(res2){
            if(res2&&res2.ok&&res2.data&&res2.data.lot&&cell) {
              var prod = res2.data.lot.product || '—';
              var otherLots = (r.lots||[]).length > 1 ? ' <span style="font-size:10px;color:var(--text-muted);">외 '+((r.lots.length-1))+'종</span>' : '';
              cell.innerHTML = '<span style="font-size:12px;">'+_esc(prod)+'</span>' + otherLots;
            }
          }).catch(function(){});
      });
    }

    // rack-heatmap API 호출
    var cached = _rackPctCache && Object.keys(_rackPctCache).length > 2;
    if (cached && _rackPctCache.__raw_racks) {
      _render(_rackPctCache.__raw_racks);
    } else {
      fetch(_api()+'/api/warehouse/rack-heatmap')
        .then(function(r){return r.json();})
        .then(function(res){
          if(res&&res.ok) {
            _rackPctCache.__raw_racks = res.data.racks || [];
            _render(_rackPctCache.__raw_racks);
          } else {
            grid.innerHTML = '<div style="padding:20px;text-align:center;color:#e57373;">❌ 로드 실패</div>';
          }
        }).catch(function(){
          grid.innerHTML = '<div style="padding:20px;text-align:center;color:#e57373;">❌ 로드 실패</div>';
        });
    }
  }


  /* ── 랙 클릭 → 그리드 아래 LOT 목록 테이블 ── */
  function _showRackLotTable(dong, rack) {
    var box = document.getElementById('wh-rack-lot-table');
    if (!box) return;

    if (!box._delegated) {
      box._delegated = true;
      box.addEventListener('click', function(e) {
        var t = e.target.closest('[data-lot-detail]');
        if (t) window._whDashOpenLotDetail(t.getAttribute('data-lot-detail'));
      });
    }
    box.innerHTML = '<div style="padding:12px;text-align:center;color:var(--text-muted);font-size:12px;">⏳ 로딩중...</div>';

    var SKR = {AVAILABLE:'출고가능',RESERVED:'배정됨',PICKED:'출고중',SOLD:'출고완료',PENDING:'대기',RETURN:'반품'};
    var SC  = {AVAILABLE:'#2e7d32',RESERVED:'#1565c0',PICKED:'#e65100',SOLD:'#424242',PENDING:'#6a1b9a',RETURN:'#c62828'};

    // cell-grid API에서 직접 lot_no 추출 (평면도와 동일한 소스)
    fetch(_api()+'/api/warehouse/cell-grid?dong='+dong+'&rack='+rack)
      .then(function(r){ return r.json(); })
      .then(function(res){
        if (!res||!res.ok||!res.data) {
          box.innerHTML = '<div style="padding:12px;text-align:center;color:#e57373;">❌ 데이터 로드 실패</div>';
          return;
        }
        var cells = res.data.cells || [];

        // lot_no 별로 집계 (셀에서 직접)
        var lotMap = {};   // {lot_no: {cells:[], sub_lts:[]}}
        cells.forEach(function(c){
          if (!c.lot_no || c.state==='EMPTY' || c.state==='UNKNOWN') return;
          if (!lotMap[c.lot_no]) lotMap[c.lot_no] = {cells:[], sub_lts:[]};
          lotMap[c.lot_no].cells.push(c);
          if (c.sub_lt != null && lotMap[c.lot_no].sub_lts.indexOf(c.sub_lt) < 0) {
            lotMap[c.lot_no].sub_lts.push(c.sub_lt);
          }
        });

        var lotNos = Object.keys(lotMap).sort();

        if (lotNos.length === 0) {
          box.innerHTML = '<div style="padding:16px;text-align:center;color:var(--text-muted);font-size:12px;">이 랙에 배치된 LOT 없음</div>';
          return;
        }

        // 각 LOT 상세 병렬 로드 (제품명/상태/중량)
        var promises = lotNos.map(function(lotNo){
          return fetch(_api()+'/api/actions/lot-detail/'+encodeURIComponent(lotNo))
            .then(function(r){return r.json();}).catch(function(){return null;});
        });

        Promise.all(promises).then(function(results){
          var detailMap = {};
          results.forEach(function(res2){
            if(!res2||!res2.ok||!res2.data) return;
            var lot = res2.data.lot||{}, tbs = res2.data.tonbags||[];
            var alive = tbs.filter(function(t){return t.status!=='SOLD'&&t.status!=='RETURNED'&&t.status!=='PENDING';});
            var wt = alive.reduce(function(s,t){return s+(Number(t.weight)||0);},0);
            detailMap[lot.lot_no] = {
              product:   lot.product||'—',
              status:    lot.status||'—',
              bags:      alive.length,
              weight_mt: (wt/1000).toFixed(2),
              inbound:   lot.inbound_date||lot.arrival_date||'—',
            };
          });

          var totalBags = 0, totalMt = 0;
          var th = '<div style="padding:8px 0 6px;display:flex;align-items:center;gap:8px;">'
            + '<span style="font-size:12px;font-weight:800;color:var(--accent,#4fc3f7);">📋 '
            + dong+'동 '+String(rack).padStart(2,'0')+'번 랙 — LOT 목록</span>'
            + '<span id="wh-rlt-count" style="font-size:11px;color:var(--text-muted);"></span>'
            + '</div>';

          th += '<table style="width:100%;border-collapse:collapse;font-size:12px;">'
            + '<thead><tr style="background:var(--bg-hover,#1a2027);">'
            + '<th style="text-align:center;padding:7px 8px;color:var(--text-muted);font-weight:700;border-bottom:1px solid var(--accent);width:40px;">순번</th>'
            + '<th style="text-align:left;padding:7px 10px;color:var(--text-muted);font-weight:700;border-bottom:1px solid var(--accent);">LOT NO</th>'
            + '<th style="text-align:left;padding:7px 8px;color:var(--text-muted);font-weight:700;border-bottom:1px solid var(--accent);">품목(제품)</th>'
            + '<th style="text-align:center;padding:7px 6px;color:var(--text-muted);font-weight:700;border-bottom:1px solid var(--accent);">상태</th>'
            + '<th style="text-align:right;padding:7px 8px;color:var(--text-muted);font-weight:700;border-bottom:1px solid var(--accent);">톤백(개)</th>'
            + '<th style="text-align:right;padding:7px 8px;color:var(--text-muted);font-weight:700;border-bottom:1px solid var(--accent);">중량(MT)</th>'
            + '<th style="text-align:center;padding:7px 6px;color:var(--text-muted);font-weight:700;border-bottom:1px solid var(--accent);">입고일</th>'
            + '</tr></thead><tbody>';

          lotNos.forEach(function(lotNo, i){
            var d  = detailMap[lotNo] || {product:'—',status:'—',bags:0,weight_mt:'0.00',inbound:'—'};
            var bg = i%2===0 ? 'var(--bg,#13191f)' : 'var(--bg-hover,#1a2027)';
            var sc = SC[d.status]||'#37474f';
            var sk = SKR[d.status]||d.status;
            totalBags += d.bags;
            totalMt   += parseFloat(d.weight_mt||0);

            th += '<tr style="background:'+bg+';border-bottom:1px solid rgba(255,255,255,.04);">'
              + '<td style="padding:6px 8px;text-align:center;font-size:11px;color:var(--text-muted);font-weight:700;">'+(i+1)+'</td>'
              + '<td style="padding:6px 10px;font-family:monospace;font-weight:700;font-size:13px;">'
              +   '<span data-lot-detail="'+_esc(lotNo)+'" '
              +   'style="color:var(--accent,#4fc3f7);cursor:pointer;text-decoration:underline;text-underline-offset:2px;" '
              +   'title="클릭→우측 상세">'+_esc(lotNo)+'</span></td>'
              + '<td style="padding:6px 8px;font-size:12px;">'+_esc(d.product)+'</td>'
              + '<td style="padding:6px 6px;text-align:center;">'
              +   '<span style="background:'+sc+';color:#fff;padding:2px 7px;border-radius:10px;font-size:10px;font-weight:700;">'+_esc(sk)+'</span></td>'
              + '<td style="padding:6px 8px;text-align:right;font-weight:700;font-size:13px;">'+d.bags+'</td>'
              + '<td style="padding:6px 8px;text-align:right;font-weight:700;font-size:13px;color:var(--accent,#4fc3f7);">'+d.weight_mt+' MT</td>'
              + '<td style="padding:6px 6px;text-align:center;font-size:11px;color:var(--text-muted);">'+_esc(d.inbound)+'</td>'
              + '</tr>';
          });

          th += '<tr style="background:rgba(79,195,247,.08);border-top:1px solid var(--accent,#4fc3f7);">'
            + '<td colspan="4" style="padding:7px 10px;font-weight:800;color:var(--accent,#4fc3f7);">합계</td>'
            + '<td style="padding:7px 8px;text-align:right;font-weight:800;">'+totalBags+'</td>'
            + '<td style="padding:7px 8px;text-align:right;font-weight:800;color:var(--accent,#4fc3f7);">'+totalMt.toFixed(2)+' MT</td>'
            + '<td></td></tr>';
          th += '</tbody></table>';

          var cnt = document.getElementById('wh-rlt-count');
          if(cnt) cnt.textContent = '('+lotNos.length+'개 LOT · 톤백 '+totalBags+'개 · '+totalMt.toFixed(2)+' MT)';
          box.innerHTML = th;

          // 이벤트 재위임 (innerHTML 교체 후)
          box.addEventListener('click', function(e) {
            var t = e.target.closest('[data-lot-detail]');
            if (t) window._whDashOpenLotDetail(t.getAttribute('data-lot-detail'));
          });

        }).catch(function(){
          box.innerHTML = '<div style="padding:12px;color:#e57373;">❌ 로드 실패</div>';
        });
      })
      .catch(function(){
        box.innerHTML = '<div style="padding:12px;color:#e57373;">❌ cell-grid 로드 실패</div>';
      });
  }


  /* ── 동 클릭 → 랙별 LOT 현황 테이블 팝업 ── */
  function _showDongLotTable(dong) {
    var popId = 'wh-dong-lot-popup';
    var ex = document.getElementById(popId);
    if (ex) ex.remove();

    var pop = document.createElement('div');
    pop.id = popId;
    pop.style.cssText = 'position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);'
      + 'width:min(980px,94vw);max-height:84vh;background:var(--bg-card,#1e272e);'
      + 'border:2px solid var(--accent,#4fc3f7);border-radius:10px;'
      + 'box-shadow:0 8px 40px rgba(0,0,0,.7);z-index:10200;'
      + 'display:flex;flex-direction:column;overflow:hidden;';
    pop.innerHTML = ''
      + '<div id="wh-dlp-hdr" style="background:linear-gradient(90deg,#0d47a1,#1565c0);color:#fff;'
      +   'padding:10px 16px;display:flex;align-items:center;gap:8px;flex-shrink:0;">'
      +   '<span style="font-size:15px;font-weight:800;">🏭 ' + dong + '동 — 랙별 LOT 현황</span>'
      +   '<span id="wh-dlp-count" style="font-size:12px;opacity:.8;"></span>'
      +   '<button id="wh-dlp-xlsx" style="margin-left:auto;background:rgba(76,175,80,.25);border:1px solid #4caf50;'
      +     'border-radius:5px;color:#a5d6a7;font-size:12px;font-weight:700;cursor:pointer;padding:4px 12px;">'
      +     '📥 엑셀 저장</button>'
      +   '<button onclick="document.getElementById(\'wh-dong-lot-popup\').remove()" '
      +     'style="background:none;border:none;font-size:20px;cursor:pointer;color:#fff;margin-left:8px;">&times;</button>'
      + '</div>'
      + '<div style="font-size:11px;color:var(--text-muted,#90a4ae);padding:5px 16px;'
      +   'background:var(--bg-hover,#1a2027);flex-shrink:0;">'
      +   '💡 LOT NO 클릭 → 오른쪽 패널에서 상세 확인'
      + '</div>'
      + '<div id="wh-dlp-body" style="flex:1;overflow:auto;padding:12px;">'
      +   '<div style="text-align:center;padding:30px;color:var(--text-muted,#90a4ae);">⏳ 로딩중...</div>'
      + '</div>';
    document.body.appendChild(pop);

    var _esc2 = function(e){ if(e.key==='Escape'){ var p=document.getElementById(popId); if(p) p.remove(); document.removeEventListener('keydown',_esc2); }};
    document.addEventListener('keydown', _esc2);

    var body    = document.getElementById('wh-dlp-body');
    var countEl = document.getElementById('wh-dlp-count');
    var SKR2    = {AVAILABLE:'출고가능',RESERVED:'배정됨',PICKED:'출고중',SOLD:'출고완료',PENDING:'대기',RETURN:'반품'};
    var SC2     = {AVAILABLE:'#2e7d32',RESERVED:'#1565c0',PICKED:'#e65100',SOLD:'#424242',PENDING:'#6a1b9a',RETURN:'#c62828'};
    var _cr2    = [];

    /* 1단계: 이 동의 랙별 LOT 목록 수집 */
    function _getRackLotMap(cb) {
      var cached = _rackPctCache.__lots_by_dong_rack;
      if (cached && Object.keys(cached).length > 0) {
        var rackMap = {};
        for (var r = 1; r <= 16; r++) {
          var lots = cached[dong+'_'+r];
          if (lots && lots.length > 0) rackMap[r] = lots.slice();
        }
        if (Object.keys(rackMap).length > 0) return cb(rackMap);
      }
      fetch(_api()+'/api/warehouse/rack-heatmap')
        .then(function(r){ return r.json(); })
        .then(function(res){
          var rm = {};
          if(res&&res.ok) (res.data.racks||[]).forEach(function(r){ if(r.dong===dong&&r.lots&&r.lots.length>0) rm[r.rack]=r.lots; });
          cb(rm);
        }).catch(function(){ cb({}); });
    }

    /* 2단계: 각 LOT 상세 병렬 조회 후 랙별 테이블 */
    _getRackLotMap(function(rackLotMap) {
      var allLots = [];
      Object.keys(rackLotMap).forEach(function(rack){
        rackLotMap[rack].forEach(function(l){ if(allLots.indexOf(l)<0) allLots.push(l); });
      });

      if (allLots.length === 0) {
        if(body) body.innerHTML = '<div style="text-align:center;padding:30px;color:var(--text-muted);">'
          + '이 동에 배치된 LOT 없음'
          + '<br><small style="font-size:11px;">위치 데이터(inventory_tonbag.location)가 입력되지 않았을 수 있습니다.</small></div>';
        return;
      }

      var promises = allLots.map(function(lotNo){
        return fetch(_api()+'/api/actions/lot-detail/'+encodeURIComponent(lotNo))
          .then(function(r){ return r.json(); }).catch(function(){ return null; });
      });

      Promise.all(promises).then(function(results){
        var lotDetail = {};
        results.forEach(function(res2){
          if(!res2||!res2.ok||!res2.data) return;
          var lot = res2.data.lot||{}, tbs = res2.data.tonbags||[];
          var alive = tbs.filter(function(t){ return t.status!=='SOLD'&&t.status!=='RETURNED'&&t.status!=='PENDING'; });
          var wt = alive.reduce(function(s,t){ return s+(Number(t.weight)||0); }, 0);
          lotDetail[lot.lot_no] = {
            product:   lot.product||'—',
            status:    lot.status||'—',
            bags:      alive.length,
            weight_mt: (wt/1000).toFixed(2),
            inbound:   lot.inbound_date||lot.arrival_date||'—',
          };
        });

        var excelRows = [], totalBags = 0, totalMt = 0;
        var rackNums  = Object.keys(rackLotMap).map(Number).sort(function(a,b){return a-b;});

        var th = '<table style="width:100%;border-collapse:collapse;font-size:12px;">'
          + '<thead><tr style="background:var(--bg-hover,#1a2027);position:sticky;top:0;">'
          + '<th style="text-align:center;padding:8px 8px;color:var(--text-muted);font-weight:700;border-bottom:2px solid var(--accent);width:60px;">랙</th>'
          + '<th style="text-align:left;padding:8px 10px;color:var(--text-muted);font-weight:700;border-bottom:2px solid var(--accent);">LOT NO</th>'
          + '<th style="text-align:left;padding:8px 8px;color:var(--text-muted);font-weight:700;border-bottom:2px solid var(--accent);">품목(제품)</th>'
          + '<th style="text-align:center;padding:8px 6px;color:var(--text-muted);font-weight:700;border-bottom:2px solid var(--accent);">상태</th>'
          + '<th style="text-align:right;padding:8px 8px;color:var(--text-muted);font-weight:700;border-bottom:2px solid var(--accent);">톤백(개)</th>'
          + '<th style="text-align:right;padding:8px 8px;color:var(--text-muted);font-weight:700;border-bottom:2px solid var(--accent);">중량(MT)</th>'
          + '<th style="text-align:center;padding:8px 6px;color:var(--text-muted);font-weight:700;border-bottom:2px solid var(--accent);">입고일</th>'
          + '</tr></thead><tbody>';

        rackNums.forEach(function(rack) {
          var lots = rackLotMap[rack] || [];
          var rackBags = 0, rackMt = 0;

          /* 랙 구분 헤더 행 */
          th += '<tr style="background:rgba(79,195,247,.07);border-top:1px solid rgba(79,195,247,.25);">'
            + '<td colspan="7" style="padding:5px 10px;font-size:12px;font-weight:800;color:var(--accent,#4fc3f7);">'
            + '🗄 ' + dong + '동 ' + String(rack).padStart(2,'0') + '번 랙'
            + '<span style="font-weight:400;color:var(--text-muted);margin-left:8px;font-size:11px;">(' + lots.length + ' LOT)</span>'
            + '</td></tr>';

          lots.forEach(function(lotNo, idx) {
            var d  = lotDetail[lotNo] || {product:'—',status:'—',bags:0,weight_mt:'0.00',inbound:'—'};
            var bg = idx%2===0 ? 'var(--bg,#13191f)' : 'var(--bg-hover,#1a2027)';
            var sc = SC2[d.status]||'#37474f';
            var sk = SKR2[d.status]||d.status;
            rackBags  += d.bags;
            rackMt    += parseFloat(d.weight_mt||0);
            totalBags += d.bags;
            totalMt   += parseFloat(d.weight_mt||0);
            excelRows.push({rack:rack, lot_no:lotNo, product:d.product, status:d.status, bags:d.bags, weight_mt:d.weight_mt, inbound:d.inbound});

            th += '<tr style="background:'+bg+';border-bottom:1px solid rgba(255,255,255,.04);">'
              + '<td style="padding:6px 8px;text-align:center;font-size:11px;color:var(--text-muted);">' + String(rack).padStart(2,'0') + '</td>'
              + '<td style="padding:6px 10px;font-family:monospace;font-weight:700;font-size:13px;">'
              +   '<span style="color:var(--accent,#4fc3f7);cursor:pointer;text-decoration:underline;text-underline-offset:2px;" '
              +   'onclick="window._whDashOpenLotDetail(\''+_esc(lotNo)+'\')" title="상세 보기">'+_esc(lotNo)+'</span></td>'
              + '<td style="padding:6px 8px;font-size:12px;">'+_esc(d.product)+'</td>'
              + '<td style="padding:6px 6px;text-align:center;"><span style="background:'+sc+';color:#fff;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:700;">'+_esc(sk)+'</span></td>'
              + '<td style="padding:6px 8px;text-align:right;font-weight:700;font-size:13px;">'+d.bags+'</td>'
              + '<td style="padding:6px 8px;text-align:right;font-weight:700;font-size:13px;color:var(--accent,#4fc3f7);">'+d.weight_mt+' MT</td>'
              + '<td style="padding:6px 6px;text-align:center;font-size:11px;color:var(--text-muted);">'+_esc(d.inbound)+'</td>'
              + '</tr>';
          });

          /* 랙 소계 (LOT 2개 이상일 때만) */
          if (lots.length > 1) {
            th += '<tr style="background:rgba(255,255,255,.04);border-bottom:1px solid rgba(255,255,255,.1);">'
              + '<td colspan="4" style="padding:4px 10px;font-size:11px;color:var(--text-muted);text-align:right;">랙 소계</td>'
              + '<td style="padding:4px 8px;text-align:right;font-weight:700;font-size:12px;">'+rackBags+'</td>'
              + '<td style="padding:4px 8px;text-align:right;font-weight:700;font-size:12px;color:var(--accent,#4fc3f7);">'+rackMt.toFixed(2)+' MT</td>'
              + '<td></td></tr>';
          }
        });

        /* 전체 합계 */
        th += '<tr style="background:rgba(79,195,247,.1);border-top:2px solid var(--accent,#4fc3f7);">'
          + '<td colspan="4" style="padding:8px 10px;font-weight:800;color:var(--accent,#4fc3f7);">전체 합계</td>'
          + '<td style="padding:8px 8px;text-align:right;font-weight:800;font-size:14px;">'+totalBags+'</td>'
          + '<td style="padding:8px 8px;text-align:right;font-weight:800;font-size:14px;color:var(--accent,#4fc3f7);">'+totalMt.toFixed(2)+' MT</td>'
          + '<td></td></tr>';
        th += '</tbody></table>';

        _cr2 = excelRows;
        if(countEl) countEl.textContent = '('+rackNums.length+'개 랙 · LOT '+allLots.length+'개 · 톤백 '+totalBags+'개 · '+totalMt.toFixed(2)+' MT)';

        var xb = document.getElementById('wh-dlp-xlsx');
        if(xb) xb.onclick = function(){ _exportExcelDash(_cr2, dong+'동_랙별LOT현황'); };

        if(body) body.innerHTML = th;
      }).catch(function(){
        var b = document.getElementById('wh-dlp-body');
        if(b) b.innerHTML = '<div style="padding:20px;color:#e57373;">❌ 로드 실패</div>';
      });
    });
  }


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
  /* 공개 함수 추가 */
  window._whDashOpenLotDetail = function(lotNo) {
    var db = document.getElementById('wh-dash-detail'); if(!db) return;
    db.innerHTML='<div style="padding:20px;text-align:center;color:var(--text-muted);font-size:12px;">⏳ '+_esc(lotNo)+' 로딩중...</div>';
    fetch(_api()+'/api/actions/lot-detail/'+encodeURIComponent(lotNo)).then(function(r){return r.json();}).then(function(res){
      if(!res||!res.ok||!res.data){db.innerHTML='<div style="padding:12px;color:#e57373;">❌ 로드 실패</div>';return;}
      var lot=res.data.lot||{},tbs=res.data.tonbags||[],stats=res.data.tb_stats||[],bl=res.data.bl_doc;
      var SKD={AVAILABLE:'출고가능',RESERVED:'배정됨',PICKED:'출고중',SOLD:'출고완료',PENDING:'대기',RETURN:'반품'};
      var SCD={AVAILABLE:'#2e7d32',RESERVED:'#1565c0',PICKED:'#e65100',SOLD:'#424242',PENDING:'#6a1b9a',RETURN:'#c62828'};
      function _b(s){return '<span style="background:'+(SCD[s]||'#37474f')+';color:#fff;padding:2px 7px;border-radius:10px;font-size:10px;font-weight:700;">'+(SKD[s]||s)+'</span>';}
      function _r(l,v){return '<div style="display:flex;gap:5px;margin-bottom:3px;font-size:11px;"><span style="color:var(--text-muted);min-width:64px;flex-shrink:0;">'+_esc(l)+'</span><span style="word-break:break-all;">'+(v!=null?v:'—')+'</span></div>';}
      function _s(t,c){return '<div style="margin-bottom:9px;"><div style="font-size:11px;font-weight:700;color:var(--text-muted);padding:3px 0;border-bottom:1px solid var(--panel-border);margin-bottom:4px;">'+_esc(t)+'</div>'+c+'</div>';}
      var html=_s('📋 LOT 기본 정보',_r('LOT NO',lot.lot_no)+_r('제품',lot.product)+_r('상태',_b(lot.status))+_r('총중량',(lot.initial_weight?(Number(lot.initial_weight)/1000).toFixed(2)+' MT':'—'))+_r('현재중량',(lot.current_weight?(Number(lot.current_weight)/1000).toFixed(2)+' MT':'—'))+_r('입고일',lot.inbound_date||lot.arrival_date||'—'));
      var sh='<div style="display:flex;flex-wrap:wrap;gap:3px;margin-top:3px;">';
      stats.forEach(function(s){sh+='<div style="background:var(--bg);border:1px solid var(--panel-border);border-radius:4px;padding:3px 7px;min-width:65px;text-align:center;"><div style="font-size:9px;color:var(--text-muted);">'+_esc(s.status)+'</div><div style="font-size:13px;font-weight:700;">'+s.cnt+'개</div></div>';});
      sh+='</div>'; html+=_s('📊 톤백 현황',sh);
      var tbH='<table style="width:100%;border-collapse:collapse;font-size:10px;"><tr style="color:var(--text-muted);"><th style="padding:2px 3px;text-align:left;">Sub</th><th style="text-align:left;padding:2px 3px;">위치</th><th style="text-align:right;padding:2px 3px;">중량</th><th style="text-align:center;padding:2px 3px;">상태</th></tr>';
      tbs.slice(0,12).forEach(function(tb){tbH+='<tr style="border-bottom:1px solid rgba(255,255,255,.04);"><td style="padding:2px 3px;color:var(--accent);">'+(tb.sub_lt!=null?tb.sub_lt:'—')+'</td><td style="padding:2px 3px;font-size:9px;font-family:monospace;">'+_esc(tb.location||'미배정')+'</td><td style="padding:2px 3px;text-align:right;">'+(tb.weight?(tb.weight/1000).toFixed(2)+'MT':'—')+'</td><td style="padding:2px 3px;text-align:center;">'+_b(tb.status)+'</td></tr>';});
      if(tbs.length>12)tbH+='<tr><td colspan="4" style="text-align:center;padding:2px;font-size:9px;color:var(--text-muted);">외 '+(tbs.length-12)+'개...</td></tr>';
      tbH+='</table>'; html+=_s('🎒 톤백 목록 ('+tbs.length+'개)',tbH);
      if(bl) html+=_s('🚢 선박 정보',_r('BL NO',bl.bl_no)+_r('선박',bl.vessel)+_r('항차',bl.voyage)+_r('출항일',bl.ship_date)+_r('선사',bl.carrier_name));
      db.innerHTML=html;
    }).catch(function(){db.innerHTML='<div style="padding:12px;color:#e57373;">❌ 로드 실패</div>';});
  };

  function _exportExcelDash(rows, filename) {
    if(!rows||rows.length===0){_toast('warning','내보낼 데이터가 없습니다.');return;}
    var BOM='﻿', h=['랙','LOT NO','제품','상태','톤백(개)','중량(MT)','입고일'];
    var lines=[h.join(',')];
    rows.forEach(function(r){
      lines.push([
        (r.rack||''),'"'+(r.lot_no||'').replace(/"/g,'""')+'"',
        '"'+(r.product||'').replace(/"/g,'""')+'"',
        '"'+(r.status||'').replace(/"/g,'""')+'"',
        (r.bags||0),(r.weight_mt||0),
        '"'+(r.inbound||'').replace(/"/g,'""')+'"'
      ].join(','));
    });
    var csv=BOM+lines.join('\r\n'),blob=new Blob([csv],{type:'text/csv;charset=utf-8;'}),url=URL.createObjectURL(blob),a=document.createElement('a');
    var now=new Date(),ymd=now.getFullYear()+('0'+(now.getMonth()+1)).slice(-2)+('0'+now.getDate()).slice(-2);
    a.href=url;a.download=filename+'_'+ymd+'.csv';
    document.body.appendChild(a);a.click();document.body.removeChild(a);URL.revokeObjectURL(url);
    _toast('success',filename+'_'+ymd+'.csv 저장 완료');
  }

  window.showWarehouseDashboard = function() {
    _ensureModal();
    _refreshRackPct(function(){
      _renderLeftNav();
      _renderDetail();
      _loadAll();
    });
  };

})();
