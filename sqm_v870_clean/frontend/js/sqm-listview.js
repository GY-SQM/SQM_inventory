/* =======================================================================
   sqm-listview.js  (v8.7.0)
   재고 메뉴 — LOT / 톤백 리스트 화면 모달

   기존 동작:
     [LOT 리스트 Excel] 클릭 → 엑셀 파일 바로 다운로드
     [톤백리스트 Excel] 클릭 → 엑셀 파일 바로 다운로드

   변경 동작:
     클릭 → 화면 안에 테이블 표시 + 우측 상단 [📥 엑셀 다운로드] 버튼
     사용자가 데이터 확인 후 필요하면 엑셀로 내보내기

   API:
     GET /api/action/lot-list-json
     GET /api/action2/tonbag-list-json?lot_no=...
   ======================================================================= */
(function () {
  'use strict';
  if (window.__SQM_LISTVIEW_INSTALLED__) return;
  window.__SQM_LISTVIEW_INSTALLED__ = true;

  /* ── 의존성 폴백 (sqm-inline.js 에서 제공) ── */
  function _api()         { return (typeof API !== 'undefined') ? API : ''; }
  function _toast(t, msg) { if (window.showToast) window.showToast(t, msg); }
  function _esc(s) {
    if (window.escapeHtml) return window.escapeHtml(s);
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }
  function _dlUrl(url, label) {
    if (typeof window.sqmDownloadFileUrl === 'function') {
      window.sqmDownloadFileUrl(url, label);
    } else {
      window.open(url, '_blank');
    }
  }

  /* ── 컬럼 정의 ── */
  var LOT_COLS = [
    { k: 'sap_no',        h: 'SAP NO',     w: 110, align: 'center' },
    { k: 'bl_no',         h: 'BL NO',      w: 130, align: 'center' },
    { k: 'container_no',  h: 'Container',  w: 130, align: 'center' },
    { k: 'product',       h: '제품명',     w: 200 },
    { k: 'lot_no',        h: 'LOT NO',     w: 130, mono: true, bold: true, align: 'center' },
    { k: 'net_weight',    h: '순중량(kg)',  w: 100, align: 'right', num: true },
    { k: 'current_weight',h: '현재(kg)',    w: 100, align: 'right', num: true },
    { k: 'tonbag_count',  h: '톤백수',      w: 70,  align: 'right' },
    { k: 'status',        h: '상태',        w: 90,  align: 'center', badge: 'status' },
    { k: 'inbound_date',  h: '입고일',      w: 100, align: 'center' },
    { k: 'arrival_date',  h: '도착일',      w: 100, align: 'center' },
    { k: 'warehouse',     h: '창고',        w: 60,  align: 'center' },
    { k: 'vessel',        h: '선박',        w: 130, align: 'center' },
    { k: 'do_no',         h: 'D/O NO',     w: 120, align: 'center' },
    { k: 'remarks',       h: '비고',       w: 160 },
    { k: 'rack_location_candidate_check', h: '랙 후보', w: 70, align: 'center' },
  ];

  var TONBAG_COLS = [
    { k: 'sap_no',       h: 'SAP NO',     w: 110, align: 'center' },
    { k: 'bl_no',        h: 'BL NO',      w: 130, align: 'center' },
    { k: 'container_no', h: 'Container',  w: 130, align: 'center' },
    { k: 'product',      h: '제품명',     w: 200 },
    { k: 'tonbag_uid',   h: '톤백 UID',    w: 160, mono: true, align: 'center' },
    { k: 'sub_lt',       h: 'Sub LT',     w: 70,  align: 'right' },
    { k: 'tonbag_no',    h: '톤백 번호',   w: 90,  align: 'center' },
    { k: 'weight_kg',    h: '중량(kg)',    w: 90,  align: 'right', num: true },
    { k: 'status',       h: '상태',        w: 90,  align: 'center', badge: 'status' },
    { k: 'location',     h: '실제 위치',    w: 130, mono: true, align: 'center' },
    { k: 'rack_location_candidate', h: '랙 위치 후보', w: 130, mono: true, align: 'center' },
    { k: 'cell_state',   h: '셀 상태',     w: 110, align: 'center', badge: 'cell' },
    { k: 'inbound_date', h: '입고일',      w: 100, align: 'center' },
    { k: 'arrival_date', h: '도착일',      w: 100, align: 'center' },
    { k: 'sold_to',      h: '출고대상',    w: 130, align: 'center' },
    { k: 'sale_ref',     h: 'Sale Ref',   w: 130, align: 'center' },
    { k: 'remarks',      h: '비고',       w: 160 },
    { k: 'warehouse',    h: '창고',        w: 60,  align: 'center' },
  ];

  /* ── 상태 배지 색상 ── */
  var STATUS_COLORS = {
    AVAILABLE: { bg: '#1b5e20', fg: '#a5d6a7' },
    RESERVED:  { bg: '#0d47a1', fg: '#90caf9' },
    PICKED:    { bg: '#f57f17', fg: '#fff9c4' },
    SOLD:      { bg: '#424242', fg: '#e0e0e0' },
    PENDING:   { bg: '#1565c0', fg: '#bbdefb' },
    RETURN:    { bg: '#b71c1c', fg: '#ffcdd2' },
    DEPLETED:  { bg: '#37474f', fg: '#cfd8dc' },
    SHIPPED:   { bg: '#212121', fg: '#9e9e9e' },
  };
  /* v8.7.0: 셀 상태 배지 */
  var CELL_STATE_COLORS = {
    EMPTY:    { bg: '#37474f', fg: '#b0bec5', icon: '⬜' },
    OCCUPIED: { bg: '#1b5e20', fg: '#a5d6a7', icon: '🟦' },
    HALF:     { bg: '#f57f17', fg: '#fff9c4', icon: '🟨' },
    OVER:     { bg: '#b71c1c', fg: '#ffcdd2', icon: '⚠' },
    MIXED:    { bg: '#b71c1c', fg: '#ffcdd2', icon: '⚠' },
    UNKNOWN:  { bg: '#212121', fg: '#9e9e9e', icon: '?' },
  };

  function _formatCell(val, col) {
    if (val == null || val === '') return '';
    if (col.num) {
      var n = Number(val);
      if (!isNaN(n)) return n.toLocaleString('ko-KR', { maximumFractionDigits: 2 });
    }
    if (col.badge === 'status') {
      var c = STATUS_COLORS[String(val).toUpperCase()] || { bg: '#37474f', fg: '#cfd8dc' };
      return '<span style="display:inline-block;padding:1px 8px;border-radius:10px;'
        + 'background:' + c.bg + ';color:' + c.fg + ';font-size:10px;font-weight:700;">'
        + _esc(val) + '</span>';
    }
    if (col.badge === 'cell') {
      var c2 = CELL_STATE_COLORS[String(val).toUpperCase()] || CELL_STATE_COLORS.UNKNOWN;
      return '<span style="display:inline-block;padding:1px 8px;border-radius:10px;'
        + 'background:' + c2.bg + ';color:' + c2.fg + ';font-size:10px;font-weight:700;">'
        + c2.icon + ' ' + _esc(val) + '</span>';
    }
    return _esc(val);
  }

  /* ── sort 상태 (모듈 레벨) ── */
  var _lvAllRows   = [];   // 현재 모달의 전체 행 캐시
  var _lvCols      = [];   // 현재 컬럼 정의
  var _lvOnClick   = null; // 행 클릭 핸들러
  var _lvSortKey   = '';   // 현재 정렬 컬럼 key
  var _lvSortDir   = 1;    // 1=오름, -1=내림
  var _lvFootFn    = null; // 현재 footer 렌더 함수
  var _lvFootEl    = null; // footer DOM 요소

  /* ── 공통 모달 ── */
  var _modalEl = null;
  function _ensureModal() {
    if (_modalEl && document.body.contains(_modalEl)) {
      _modalEl.style.display = 'flex';
      return _modalEl;
    }
    var d = document.createElement('div');
    d.id = 'sqm-listview-modal';
    d.style.cssText = ''
      + 'position:fixed;top:50px;left:50%;transform:translateX(-50%);'
      + 'width:min(1400px,96vw);height:84vh;background:var(--bg-card);'
      + 'border:2px solid var(--accent,#4fc3f7);border-radius:10px;'
      + 'box-shadow:0 8px 40px rgba(0,0,0,.6);z-index:10040;'
      + 'display:flex;flex-direction:column;overflow:hidden;';
    d.innerHTML = ''
      + '<div id="sqm-listview-hdr" style="cursor:move;background:var(--bg-hover);'
      +     'border-radius:10px 10px 0 0;padding:8px 14px;display:flex;'
      +     'align-items:center;gap:10px;flex-shrink:0;border-bottom:1px solid var(--panel-border);">'
      + '  <span id="sqm-listview-title" style="font-size:15px;font-weight:700;color:var(--accent);">📋 리스트</span>'
      + '  <span id="sqm-listview-count" style="font-size:11px;color:var(--text-muted);"></span>'
      + '  <input id="sqm-listview-filter" type="text" placeholder="🔎 빠른 검색 (LOT/제품/SAP/BL...)" '
      +       'style="margin-left:auto;padding:4px 10px;background:var(--bg);color:var(--fg);'
      +             'border:1px solid var(--border);border-radius:6px;font-size:12px;width:240px;">'
      + '  <button id="sqm-listview-half" class="btn" '
      +       'style="padding:4px 10px;font-size:12px;background:#f57f17;color:#fff;border:none;'
      +             'border-radius:6px;display:none;font-weight:700;">🟨 HALF 셀 처리</button>'
      + '  <button id="sqm-listview-excel" class="btn btn-primary" '
      +       'style="padding:4px 12px;font-size:12px;">📥 엑셀 다운로드</button>'
      + '  <button id="sqm-listview-refresh" class="btn" style="padding:4px 10px;font-size:12px;">↻ 새로고침</button>'
      + '  <button id="sqm-listview-close" '
      +       'style="background:none;border:none;font-size:18px;cursor:pointer;'
      +             'color:var(--text-muted);padding:0 4px;">×</button>'
      + '</div>'
      + '<div id="sqm-listview-body" style="flex:1 1 auto;overflow:auto;padding:10px 14px;">'
      + '  <div style="text-align:center;color:var(--text-muted);padding:40px;">⏳ 로딩 중...</div>'
      + '</div>'
      + '<div id="sqm-listview-foot" style="padding:6px 14px;border-top:1px solid var(--panel-border);'
      +     'background:var(--bg-hover);font-size:11px;color:var(--text-muted);flex-shrink:0;">'
      + '</div>';
    document.body.appendChild(d);
    _modalEl = d;
    /* 닫기 */
    document.getElementById('sqm-listview-close').onclick = function() { d.style.display = 'none'; };
    /* 드래그 (있으면 사용) */
    if (typeof window._makeDraggableResizable === 'function') {
      window._makeDraggableResizable(d, document.getElementById('sqm-listview-hdr'));
    }
    return d;
  }

  /* ── 렌더 ──
     v8.7.0: onRowClick 옵션 추가 — 행 클릭 drilldown (LOT → 톤백) 용 */
  /* v8.7.0: sort helper */
  function _sortRows(rows, key, dir) {
    return rows.slice().sort(function(a, b) {
      var va = a[key], vb = b[key];
      if (va == null) va = '';
      if (vb == null) vb = '';
      var na = Number(va), nb = Number(vb);
      if (!isNaN(na) && !isNaN(nb)) return (na - nb) * dir;
      return String(va).localeCompare(String(vb), 'ko') * dir;
    });
  }

  function _renderTable(cols, rows, container, onRowClick) {
    /* v8.7.0: 모듈 레벨 캐시 갱신 */
    _lvCols    = cols;
    _lvOnClick = onRowClick || null;
    if (!rows || rows.length === 0) {
      container.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:40px;">📭 데이터가 없습니다.</div>';
      return;
    }
    /* v8.7.0: 정렬 적용 */
    var displayRows = (_lvSortKey)
      ? _sortRows(rows, _lvSortKey, _lvSortDir)
      : rows;
    var thead = cols.map(function(c) {
      var align = c.align ? 'text-align:' + c.align + ';' : '';
      var isActive = (c.k === _lvSortKey);
      var arrow = isActive ? (_lvSortDir === 1 ? ' ▲' : ' ▼') : ' ⇅';
      var arrowColor = isActive ? 'color:#FFD700;' : 'color:rgba(255,255,255,0.3);';
      return '<th data-sort-key="' + _esc(c.k) + '" '
        + 'style="padding:6px 8px;background:var(--bg-hover);color:var(--accent);'
        + 'font-size:11px;font-weight:700;border-bottom:2px solid var(--accent);'
        + 'position:sticky;top:0;z-index:1;white-space:nowrap;cursor:pointer;'
        + 'user-select:none;' + align
        + (c.w ? 'min-width:' + c.w + 'px;' : '') + '">'
        + _esc(c.h)
        + '<span style="font-size:9px;margin-left:2px;' + arrowColor + '">' + arrow + '</span>'
        + '</th>';
    }).join('');
    var clickable = (typeof onRowClick === 'function');
    var tbody = displayRows.map(function(r, ri) {
      var tds = cols.map(function(c) {
        var _cv = r[c.k];
        /* v8.7.0: sub_lt=0 sample row — show product suffix as " SP". */
        if (c.k === 'product' && (r.is_sample || Number(r.sub_lt) === 0)) {
          _cv = (_cv || '') + ' SP';
        }
        var v = _formatCell(_cv, c);
        var style = 'padding:4px 8px;border-bottom:1px solid var(--panel-border);'
          + 'font-size:12px;white-space:nowrap;';
        if (c.align)  style += 'text-align:' + c.align + ';';
        if (c.mono)   style += 'font-family:Consolas,monospace;';
        if (c.bold)   style += 'font-weight:700;';
        return '<td style="' + style + '">' + v + '</td>';
      }).join('');
      var rowBg = ri % 2 === 0 ? '' : 'background:rgba(255,255,255,.02);';
      var cur = clickable ? 'cursor:pointer;' : '';
      var title = clickable ? ' title="클릭하여 톤백 상세 보기"' : '';
      return '<tr data-row-idx="' + ri + '" style="' + rowBg + cur + '"' + title + '>' + tds + '</tr>';
    }).join('');
    container.innerHTML = ''
      + '<table style="width:100%;border-collapse:collapse;">'
      + '<thead><tr>' + thead + '</tr></thead>'
      + '<tbody>' + tbody + '</tbody>'
      + '</table>';
    /* v8.7.0: 헤더 클릭 → 정렬 */
    container.querySelectorAll('thead th[data-sort-key]').forEach(function(th) {
      th.addEventListener('click', function() {
        var key = th.dataset.sortKey;
        if (_lvSortKey === key) {
          _lvSortDir = _lvSortDir * -1;
        } else {
          _lvSortKey = key;
          _lvSortDir = 1;
        }
        /* 현재 컨테이너의 allRows 는 부모 스코프에 없으므로
           container 에 저장된 전체 행 캐시를 재활용 */
        var body = document.getElementById('sqm-listview-body');
        var foot = document.getElementById('sqm-listview-foot');
        _renderTable(_lvCols, _lvAllRows, body, _lvOnClick);
        if (_lvFootFn && foot) _lvFootFn(foot, _lvAllRows);
      });
    });
    /* v8.7.0: 행 클릭 핸들러 (drilldown) */
    if (clickable) {
      container.querySelectorAll('tbody tr').forEach(function(tr) {
        tr.addEventListener('mouseenter', function() {
          tr.style.background = 'rgba(79,195,247,0.18)';
        });
        tr.addEventListener('mouseleave', function() {
          var idx = parseInt(tr.dataset.rowIdx, 10);
          tr.style.background = idx % 2 === 0 ? '' : 'rgba(255,255,255,.02)';
        });
        tr.addEventListener('click', function() {
          var idx = parseInt(tr.dataset.rowIdx, 10);
          onRowClick(displayRows[idx]);
        });
      });
    }
  }


  /* -- LOT footer totals bar (v8.7.0: 노란배경·큰폰트·톤백/샘플 분리) -- */
  function _renderLotFooter(foot, rows) {
    /* v8.7.0: 모듈 레벨 캐시에 footer 함수 등록 */
    _lvFootFn = _renderLotFooter;
    _lvFootEl = foot;
    var totalNet = 0, totalCur = 0, totalReg = 0, totalSmp = 0;
    rows.forEach(function(r) {
      totalNet += Number(r.net_weight     || 0);
      totalCur += Number(r.current_weight || 0);
      totalReg += Number(r.regular_bags   || 0);
      totalSmp += Number(r.sample_bags    || 0);
    });
    /* 노란 배경 강조 스타일 */
    var s = 'display:inline-block;padding:4px 18px;margin-right:10px;'
          + 'background:#FFD600;border-radius:8px;'
          + 'font-size:14px;color:#222;font-weight:800;'
          + 'box-shadow:0 1px 4px rgba(0,0,0,.25);';
    var hint = 'font-size:11px;color:var(--text-muted);margin-left:4px;';
    /* 톤백 분리: regular + sample */
    var tbStr = totalReg > 0 || totalSmp > 0
      ? totalReg.toLocaleString('ko-KR') + '개 + SP ' + totalSmp.toLocaleString('ko-KR') + '개'
      : (totalReg + totalSmp).toLocaleString('ko-KR') + '개';
    foot.innerHTML =
        '<span style="' + s + '">📦 LOT ' + rows.length.toLocaleString('ko-KR') + ' 건</span>'
      + '<span style="' + s + '">⚖ 순중량 ' + totalNet.toLocaleString('ko-KR', {maximumFractionDigits:2}) + ' kg</span>'
      + '<span style="' + s + '">📊 현재 ' + totalCur.toLocaleString('ko-KR', {maximumFractionDigits:2}) + ' kg</span>'
      + '<span style="' + s + '">🧱 톤백 ' + tbStr + '</span>'
      + '<span style="' + hint + '">※ 행 클릭 → 톤백 상세 보기 · 엑셀 다운로드는 우상단 버튼</span>';
  }

  /* -- Tonbag footer totals bar (v8.7.0: 노란배경) ----------------- */
  function _renderTonbagFooter(foot, rows) {
    var totalWeight = 0, totalSample = 0, totalRegular = 0;
    rows.forEach(function(r) {
      totalWeight  += Number(r.weight_kg  || 0);
      if (r.is_sample) totalSample++;  else totalRegular++;
    });
    var s = 'display:inline-block;padding:4px 18px;margin-right:10px;'
          + 'background:#FFD600;border-radius:8px;'
          + 'font-size:14px;color:#222;font-weight:800;'
          + 'box-shadow:0 1px 4px rgba(0,0,0,.25);';
    var hint = 'font-size:11px;color:var(--text-muted);margin-left:4px;';
    var tbStr = (totalSample > 0)
      ? '🧱 ' + totalRegular + '개 + SP ' + totalSample + '개'
      : rows.length.toLocaleString('ko-KR') + ' 건';
    foot.innerHTML =
        '<span style="' + s + '">🎒 톤백 ' + tbStr + '</span>'
      + '<span style="' + s + '">⚖ 총 중량 ' + totalWeight.toLocaleString('ko-KR', {maximumFractionDigits:2}) + ' kg</span>'
      + '<span style="' + hint + '">※ 엑셀 다운로드는 우상단 버튼 사용</span>';
  }

  function _applyFilter(rows, q) {
    var qq = String(q || '').trim().toLowerCase();
    if (!qq) return rows;
    return rows.filter(function(r) {
      for (var k in r) {
        if (r[k] != null && String(r[k]).toLowerCase().indexOf(qq) >= 0) return true;
      }
      return false;
    });
  }

  /* ─────────────────────────────────────────────────────────────────────
     공개 함수: LOT 리스트 모달
     ───────────────────────────────────────────────────────────────────── */
  window.showLotListModal = function() {
    var m = _ensureModal();
    m.style.display = 'flex';
    document.getElementById('sqm-listview-title').textContent = '📊 LOT 리스트';
    var body = document.getElementById('sqm-listview-body');
    var foot = document.getElementById('sqm-listview-foot');
    var cnt  = document.getElementById('sqm-listview-count');
    var halfBtn = document.getElementById('sqm-listview-half');
    if (halfBtn) halfBtn.style.display = 'none';
    body.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:40px;">⏳ 로딩 중...</div>';
    cnt.textContent = '';
    foot.textContent = '';

    var url = _api() + '/api/action/lot-list-json';
    var allRows = [];

    function _load() {
      body.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:40px;">⏳ 로딩 중...</div>';
      fetch(url).then(function(r) { return r.json(); })
        .then(function(res) {
          var rows = (res && res.data && res.data.rows) || res.rows || [];
          allRows = rows;
          _lvAllRows  = rows;   /* v8.7.0: sort 캐시 */
          _lvSortKey  = '';     /* sort 초기화 */
          _lvSortDir  = 1;
          cnt.textContent = '— ' + rows.length + ' 건';
          _renderTable(LOT_COLS, rows, body, _onLotRowClick);
          _renderLotFooter(foot, rows);
        })
        .catch(function(e) {
          body.innerHTML = '<div style="text-align:center;color:var(--danger,#f44336);padding:40px;">'
            + '❌ 로딩 실패: ' + _esc(e.message || e) + '</div>';
          _toast('error', 'LOT 리스트 로딩 실패');
        });
    }

    document.getElementById('sqm-listview-excel').onclick = function() {
      _dlUrl(_api() + '/api/action/export-lot-excel', 'LOT 리스트 Excel');
    };
    document.getElementById('sqm-listview-refresh').onclick = _load;
    var fInp = document.getElementById('sqm-listview-filter');
    fInp.value = '';
    fInp.oninput = function() {
      var _lotFiltered = _applyFilter(allRows, this.value);
      _lvAllRows = _lotFiltered;  /* v8.7.0: 필터 후 sort 캐시 갱신 */
      _lvSortKey = '';            /* 필터 변경 시 sort 초기화 */
      _renderTable(LOT_COLS, _lotFiltered, body, _onLotRowClick);
      _renderLotFooter(foot, _lotFiltered);
    };

    /* v8.7.0: LOT 행 클릭 → 해당 LOT 의 톤백 모달로 drilldown */
    function _onLotRowClick(row) {
      if (!row || !row.lot_no) { _toast('warning', 'LOT 번호가 없습니다'); return; }
      if (typeof window.showTonbagListModal === 'function') {
        window.showTonbagListModal(row.lot_no);
      } else {
        _toast('error', '톤백 모달 모듈 미로드');
      }
    }

    _load();
  };

  /* ─────────────────────────────────────────────────────────────────────
     공개 함수: 톤백 리스트 모달
     ───────────────────────────────────────────────────────────────────── */
  window.showTonbagListModal = function(lotNo) {
    var m = _ensureModal();
    m.style.display = 'flex';
    /* v8.7.0: LOT drilldown 진입 시 → 제목에 LOT 번호 + 돌아가기 hint */
    var ttl = '🎒 톤백 리스트';
    if (lotNo) ttl += ' — LOT ' + lotNo + '  (← 더블클릭하면 LOT 리스트로)';
    document.getElementById('sqm-listview-title').textContent = ttl;
    /* 제목 더블클릭 → LOT 리스트로 돌아가기 */
    if (lotNo) {
      var titleEl = document.getElementById('sqm-listview-title');
      titleEl.style.cursor = 'pointer';
      titleEl.ondblclick = function() {
        if (typeof window.showLotListModal === 'function') window.showLotListModal();
      };
    }
    var body = document.getElementById('sqm-listview-body');
    var foot = document.getElementById('sqm-listview-foot');
    var cnt  = document.getElementById('sqm-listview-count');
    body.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:40px;">⏳ 로딩 중...</div>';
    cnt.textContent = '';
    foot.textContent = '';

    var url = _api() + '/api/action2/tonbag-list-json' + (lotNo ? '?lot_no=' + encodeURIComponent(lotNo) : '');
    var allRows = [];

    function _load() {
      body.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:40px;">⏳ 로딩 중...</div>';
      fetch(url).then(function(r) { return r.json(); })
        .then(function(res) {
          var rows = (res && res.data && res.data.rows) || res.rows || [];
          allRows = rows;
          /* v8.7.0: HALF 셀 톤백 카운트 → 버튼 활성화 */
          var halfTb = rows.filter(function(r) {
            return String(r.cell_state || '').toUpperCase() === 'HALF';
          }).length;
          var halfBtn = document.getElementById('sqm-listview-half');
          if (halfBtn) {
            if (halfTb > 0) {
              halfBtn.style.display = 'inline-block';
              halfBtn.textContent = '🟨 HALF 셀 처리 (' + halfTb + ')';
              halfBtn.onclick = function() {
                if (typeof window.showCase3Queue === 'function') window.showCase3Queue();
              };
            } else {
              halfBtn.style.display = 'none';
            }
          }
          cnt.textContent = '— ' + rows.length + ' 건' + (halfTb ? ' · HALF ' + halfTb + '톤백' : '');
          _renderTable(TONBAG_COLS, rows, body);
          _renderTonbagFooter(foot, rows);
        })
        .catch(function(e) {
          body.innerHTML = '<div style="text-align:center;color:var(--danger,#f44336);padding:40px;">'
            + '❌ 로딩 실패: ' + _esc(e.message || e) + '</div>';
          _toast('error', '톤백 리스트 로딩 실패');
        });
    }

    document.getElementById('sqm-listview-excel').onclick = function() {
      var dlUrl = _api() + '/api/action2/export-tonbag-excel' + (lotNo ? '?lot_no=' + encodeURIComponent(lotNo) : '');
      _dlUrl(dlUrl, '톤백리스트 Excel');
    };
    document.getElementById('sqm-listview-refresh').onclick = _load;
    var fInp = document.getElementById('sqm-listview-filter');
    fInp.value = '';
    fInp.oninput = function() {
      var _tbFiltered = _applyFilter(allRows, this.value);
      _renderTable(TONBAG_COLS, _tbFiltered, body);
      _renderTonbagFooter(foot, _tbFiltered);
    };

    _load();
  };

})();
