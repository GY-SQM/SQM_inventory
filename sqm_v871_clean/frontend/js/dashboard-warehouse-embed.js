// dashboard-warehouse-embed.js  (v8.7.0-r3)
// =============================================================
// 대시보드 인라인 창고 히트맵 — 풀 기능판
//
// [r3 추가]
//   ① 온도맵/LOT 모드 토글  (점유율 히트 ↔ LOT 색상)
//   ② 미배정 톤백 경고 배너 (API 응답 unassigned_count > 0)
//   ③ LOT 검색창 + 해당 랙 깜빡임
//   ④ 오늘 입고 LOT 랙 빛나는 테두리 (today_inbound_lots)
//   ⑤ 동(棟) 90% 초과 시 KPI 카드 상단 빨간 배지
//
// [r2 유지]
//   - 랙별 가동률 % 텍스트
//   - 랙 클릭 → 오른쪽 LOT 상세 슬라이드 패널
//   - 셀 클릭 → 툴팁 + LOT 패널
//
// ABSOLUTE EDIT BAN: sqm-inline.js / sqm-core.js 미수정
// =============================================================
(function () {
  'use strict';
  if (window.__SQM_WH_EMBED__) return;
  window.__SQM_WH_EMBED__ = true;

  var API_BASE  = '';
  var REFRESH_MS = 60000;

  // ── LOT 색상 팔레트 ──────────────────────────────────────────
  var LOT_PALETTE = [
    '#1565c0','#6a1b9a','#00695c','#e65100','#558b2f',
    '#ad1457','#0277bd','#4527a0','#2e7d32','#c62828',
    '#37474f','#4e342e','#00838f','#ef6c00','#5c6bc0',
    '#7b1fa2','#0288d1','#388e3c','#d84315','#1976d2',
  ];
  var _lotColorMap = {}, _colorIdx = 0;
  function _lotColor(lot) {
    if (!lot) return '#263238';
    if (!_lotColorMap[lot]) { _lotColorMap[lot] = LOT_PALETTE[_colorIdx % LOT_PALETTE.length]; _colorIdx++; }
    return _lotColorMap[lot];
  }

  // ── 온도맵 색상 (점유율 0~100 → 파랑→초록→주황→빨강) ─────────
  function _heatColor(pct) {
    if (pct === 0)       return '#1a237e';   // 완전 비어있음 (짙은 남색)
    if (pct < 25)        return '#1565c0';   // 파랑
    if (pct < 50)        return '#00838f';   // 청록
    if (pct < 75)        return '#2e7d32';   // 초록
    if (pct < 90)        return '#e65100';   // 주황
    return '#b71c1c';                        // 빨강 (위험)
  }

  // ── 상태 ─────────────────────────────────────────────────────
  var _heatMode   = false;   // false=LOT색, true=온도맵
  var _searchLot  = '';
  var _blinkTimer = null;
  var _lastData   = null;    // 마지막 API 응답 전체 캐시

  function _el(id) { return document.getElementById(id); }
  function _esc(s) {
    return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;')
                        .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }
  function _get(url, cb) {
    fetch(API_BASE + url)
      .then(function(r){ return r.json(); })
      .then(function(d){ cb(null, d); })
      .catch(function(e){ cb(e, null); });
  }

  // ══════════════════════════════════════════════════════════════
  // ① 온도맵/LOT 토글 버튼
  // ══════════════════════════════════════════════════════════════
  function _renderToggle(parent) {
    var existing = document.getElementById('wh-mode-toggle');
    if (existing) return;
    var btn = document.createElement('button');
    btn.id = 'wh-mode-toggle';
    btn.textContent = '🌡 온도맵';
    btn.style.cssText = [
      'background:rgba(255,255,255,.08)',
      'border:1px solid var(--panel-border,#37474f)',
      'border-radius:4px',
      'color:var(--text-muted,#90a4ae)',
      'font-size:11px',
      'cursor:pointer',
      'padding:2px 10px',
      'transition:all .15s',
    ].join(';');
    btn.onclick = function() {
      _heatMode = !_heatMode;
      btn.textContent = _heatMode ? '🎨 LOT 색상' : '🌡 온도맵';
      btn.style.background = _heatMode ? 'rgba(229,115,115,.25)' : 'rgba(255,255,255,.08)';
      btn.style.color       = _heatMode ? '#ef9a9a'              : 'var(--text-muted,#90a4ae)';
      if (_lastData) _renderHeatmap(_lastData);
    };
    parent && parent.appendChild(btn);
  }

  // ══════════════════════════════════════════════════════════════
  // ② 미배정 배너
  // ══════════════════════════════════════════════════════════════
  function _updateUnassignedBanner(count) {
    var id  = 'wh-unassigned-banner';
    var sec = _el('wh-embed-section');
    if (!sec) return;
    var existing = document.getElementById(id);
    if (count > 0) {
      if (!existing) {
        var d = document.createElement('div');
        d.id = id;
        d.style.cssText = [
          'display:flex',
          'align-items:center',
          'gap:8px',
          'background:rgba(183,28,28,.18)',
          'border:1px solid #e53935',
          'border-radius:5px',
          'padding:6px 12px',
          'margin-bottom:8px',
          'font-size:12px',
          'color:#ef9a9a',
          'cursor:pointer',
        ].join(';');
        d.innerHTML = '<span style="font-size:15px;">⚠️</span>'
          + '<span id="wh-unassigned-banner-txt"></span>'
          + '<span style="margin-left:auto;font-size:10px;color:rgba(239,154,154,.6);">클릭하여 미배정 목록 보기 →</span>';
        d.onclick = function() {
          // 미배정 섹션으로 이동하거나 경고만 표시
          if (window.showToast) window.showToast('warning', '미배정 톤백 ' + count + '개 — 위치 배정이 필요합니다.');
        };
        // 히트맵 섹션 맨 위에 삽입
        sec.insertBefore(d, sec.firstChild);
      }
      var txt = document.getElementById('wh-unassigned-banner-txt');
      if (txt) txt.textContent = '미배정 톤백 ' + count + '개 — 창고 위치 배정 필요';
    } else {
      if (existing) existing.remove();
    }
  }

  // ══════════════════════════════════════════════════════════════
  // ③ LOT 검색창
  // ══════════════════════════════════════════════════════════════
  function _renderSearchBox(parent) {
    var existing = document.getElementById('wh-lot-search-wrap');
    if (existing) return;
    var wrap = document.createElement('div');
    wrap.id = 'wh-lot-search-wrap';
    wrap.style.cssText = 'display:flex;align-items:center;gap:4px;';
    wrap.innerHTML = ''
      + '<input id="wh-lot-search-input" type="text" placeholder="LOT NO 검색..." '
      +   'style="background:var(--bg,#13191f);border:1px solid var(--panel-border,#37474f);'
      +   'border-radius:4px;color:var(--text,#eceff1);font-size:11px;padding:2px 8px;width:150px;'
      +   'outline:none;" />'
      + '<button id="wh-lot-search-btn" '
      +   'style="background:rgba(79,195,247,.15);border:1px solid var(--accent,#4fc3f7);'
      +   'border-radius:4px;color:var(--accent,#4fc3f7);font-size:11px;cursor:pointer;padding:2px 8px;">'
      +   '🔍</button>'
      + '<button id="wh-lot-search-clear" '
      +   'style="background:none;border:1px solid var(--panel-border,#37474f);'
      +   'border-radius:4px;color:var(--text-muted,#90a4ae);font-size:11px;cursor:pointer;padding:2px 6px;display:none;">'
      +   '✕</button>';
    parent && parent.appendChild(wrap);

    function _doSearch() {
      var val = (_el('wh-lot-search-input') || {}).value || '';
      _searchLot = val.trim().toUpperCase();
      var clearBtn = _el('wh-lot-search-clear');
      if (clearBtn) clearBtn.style.display = _searchLot ? 'inline-block' : 'none';
      _applySearchHighlight();
    }
    setTimeout(function() {
      var inp = _el('wh-lot-search-input');
      var btn = _el('wh-lot-search-btn');
      var clr = _el('wh-lot-search-clear');
      if (inp) {
        inp.addEventListener('keydown', function(e){ if (e.key === 'Enter') _doSearch(); });
        inp.addEventListener('input',   function(){
          if (!this.value) { _searchLot=''; if (clr) clr.style.display='none'; _applySearchHighlight(); }
        });
      }
      if (btn) btn.onclick = _doSearch;
      if (clr) clr.onclick = function() {
        _searchLot = '';
        var inp2 = _el('wh-lot-search-input');
        if (inp2) inp2.value = '';
        clr.style.display = 'none';
        _applySearchHighlight();
      };
    }, 100);
  }

  // 검색 결과 → 해당 랙 깜빡임 적용
  function _applySearchHighlight() {
    if (_blinkTimer) { clearInterval(_blinkTimer); _blinkTimer = null; }
    var blocks = document.querySelectorAll('.wh-rack-block');
    // 모든 블록 깜빡임 초기화
    blocks.forEach(function(b) {
      b.style.animation  = '';
      b.style.outline    = '';
      b.style.outlineOffset = '';
    });
    if (!_searchLot || !_lastData) return;

    // 검색어 포함 LOT이 있는 랙 찾기
    var matchDongRacks = {};
    (_lastData.racks || []).forEach(function(r) {
      var hit = (r.lots || []).some(function(l) {
        return l && l.toUpperCase().indexOf(_searchLot) >= 0;
      });
      if (hit) matchDongRacks[r.dong + '-' + r.rack] = true;
    });

    if (Object.keys(matchDongRacks).length === 0) {
      if (window.showToast) window.showToast('warning', '"' + _searchLot + '" LOT를 찾을 수 없습니다.');
      return;
    }

    // 일치 블록에 CSS 깜빡임 적용
    var _blink = true;
    _blinkTimer = setInterval(function() {
      _blink = !_blink;
      blocks.forEach(function(b) {
        var key = b.dataset.dong + '-' + b.dataset.rack;
        if (matchDongRacks[key]) {
          b.style.outline       = _blink ? '2px solid #fff176' : '2px solid transparent';
          b.style.outlineOffset = '2px';
          b.style.boxShadow     = _blink ? '0 0 10px #fff176' : '';
        }
      });
    }, 500);

    // 10초 후 자동 해제
    setTimeout(function() {
      if (_blinkTimer) { clearInterval(_blinkTimer); _blinkTimer = null; }
      blocks.forEach(function(b) {
        if (matchDongRacks[b.dataset.dong + '-' + b.dataset.rack]) {
          b.style.outline = '';
          b.style.outlineOffset = '';
          b.style.boxShadow = '';
        }
      });
    }, 10000);
  }

  // ══════════════════════════════════════════════════════════════
  // ⑤ 동 90% 초과 → KPI 카드 상단 빨간 배지
  // ══════════════════════════════════════════════════════════════
  function _updateOccupancyAlert(dongSummary) {
    var alertId = 'wh-occupancy-alert-badge';
    var existing = document.getElementById(alertId);
    // KPI row 앞에 삽입
    var kpiRow = _el('kpi-row');
    if (!kpiRow) return;

    var alerts = [];
    Object.keys(dongSummary || {}).forEach(function(dk) {
      var s = dongSummary[dk];
      if (s && s.alert_90) {
        alerts.push(dk + '동 ' + s.occupancy_pct + '%');
      }
    });

    if (alerts.length > 0) {
      if (!existing) {
        var badge = document.createElement('div');
        badge.id = alertId;
        badge.style.cssText = [
          'background:rgba(183,28,28,.22)',
          'border:1px solid #e53935',
          'border-radius:5px',
          'padding:5px 14px',
          'margin-bottom:8px',
          'font-size:12px',
          'font-weight:700',
          'color:#ef9a9a',
          'display:flex',
          'align-items:center',
          'gap:8px',
        ].join(';');
        kpiRow.parentNode && kpiRow.parentNode.insertBefore(badge, kpiRow);
        existing = badge;
      }
      existing.innerHTML = '<span style="font-size:16px;">🚨</span>'
        + '<span>창고 점유율 90% 초과: <b>' + alerts.join(' / ') + '</b></span>';
      existing.style.display = 'flex';
    } else {
      if (existing) existing.style.display = 'none';
    }
  }

  // ══════════════════════════════════════════════════════════════
  // 툴팁
  // ══════════════════════════════════════════════════════════════
  var _tip = null;
  function _showTip(ev, cell) {
    _hideTip();
    var t = document.createElement('div');
    t.id = 'wh-embed-tip';
    t.innerHTML =
      '<div style="font-size:11px;font-weight:700;color:var(--accent,#4fc3f7);margin-bottom:4px;">📍 ' + _esc(cell.location) + '</div>'
    + '<div style="font-size:11px;margin-bottom:2px;"><span style="color:var(--text-muted,#90a4ae);">LOT&nbsp;&nbsp;&nbsp;&nbsp;:</span> <b>' + _esc(cell.lot_no||'—') + '</b></div>'
    + '<div style="font-size:11px;margin-bottom:2px;"><span style="color:var(--text-muted,#90a4ae);">Sub-LOT :</span> <b>' + (cell.sub_lt!=null?_esc(String(cell.sub_lt)):'—') + '</b></div>'
    + '<div style="font-size:11px;margin-bottom:2px;"><span style="color:var(--text-muted,#90a4ae);">상태&nbsp;&nbsp;&nbsp;&nbsp;:</span> ' + _esc(cell.state||'—') + '</div>'
    + '<div style="font-size:11px;"><span style="color:var(--text-muted,#90a4ae);">점유&nbsp;&nbsp;&nbsp;&nbsp;:</span> ' + (cell.active_count!=null?cell.active_count:'—') + ' / ' + (cell.capacity!=null?cell.capacity:'—') + '</div>';
    t.style.cssText = 'position:fixed;z-index:9999;background:var(--bg-card,#1e272e);'
      + 'border:1px solid var(--accent,#4fc3f7);border-radius:6px;padding:8px 12px;'
      + 'box-shadow:0 4px 16px rgba(0,0,0,.5);pointer-events:none;min-width:170px;';
    document.body.appendChild(t);
    _tip = t;
    var x = ev.clientX+12, y = ev.clientY+12;
    if (x+190 > window.innerWidth)  x = ev.clientX-198;
    if (y+120 > window.innerHeight) y = ev.clientY-128;
    t.style.left = x+'px'; t.style.top = y+'px';
  }
  function _hideTip() { if (_tip) { _tip.remove(); _tip=null; } }
  document.addEventListener('click', function(ev){ if (_tip && !_tip.contains(ev.target)) _hideTip(); });

  function _cellBg(cell) {
    var s = cell.state||'UNKNOWN';
    if (s==='EMPTY'||s==='UNKNOWN') return 'transparent';
    if (s==='OVER')  return '#b71c1c';
    if (s==='MIXED') return '#7b1fa2';
    return _lotColor(cell.lot_no||'');
  }

  // ══════════════════════════════════════════════════════════════
  // LOT 상세 슬라이드 패널 (오른쪽)
  // ══════════════════════════════════════════════════════════════
  var _lotPanel = null;
  function _ensureLotPanel() {
    if (_lotPanel && document.body.contains(_lotPanel)) return _lotPanel;
    var p = document.createElement('div');
    p.id = 'wh-lot-detail-panel';
    p.style.cssText = 'position:fixed;top:0;right:-420px;width:400px;height:100vh;'
      + 'background:var(--bg-card,#1e272e);border-left:2px solid var(--accent,#4fc3f7);'
      + 'box-shadow:-6px 0 24px rgba(0,0,0,.6);z-index:10100;display:flex;flex-direction:column;'
      + 'transition:right .25s cubic-bezier(.4,0,.2,1);overflow:hidden;';
    p.innerHTML = ''
      + '<div style="background:linear-gradient(90deg,#0d47a1,#1565c0);color:#fff;'
      +   'padding:10px 14px;display:flex;align-items:center;gap:8px;flex-shrink:0;">'
      +   '<span style="font-size:14px;font-weight:700;">📦 LOT 상세</span>'
      +   '<span id="wlp-lot-no" style="font-size:11px;opacity:.85;margin-left:4px;"></span>'
      +   '<button id="wlp-close" style="margin-left:auto;background:none;border:none;'
      +     'font-size:18px;cursor:pointer;color:#fff;padding:0 4px;line-height:1;">×</button>'
      + '</div>'
      + '<div id="wlp-body" style="flex:1;overflow-y:auto;padding:12px;font-size:12px;">'
      +   '<div style="color:var(--text-muted,#90a4ae);padding:20px;text-align:center;">'
      +     '← 랙 또는 셀을 클릭하면 LOT 정보가 표시됩니다</div>'
      + '</div>';
    document.body.appendChild(p);
    _lotPanel = p;
    document.getElementById('wlp-close').onclick = _closeLotPanel;
    return p;
  }
  function _openLotPanel()  { var p=_ensureLotPanel(); requestAnimationFrame(function(){ p.style.right='0px'; }); }
  function _closeLotPanel() { if (_lotPanel) _lotPanel.style.right='-420px'; }

  function _loadLotDetail(lotNo) {
    if (!lotNo) return;
    var p=_ensureLotPanel(), body=_el('wlp-body'), noEl=_el('wlp-lot-no');
    if (noEl) noEl.textContent = lotNo;
    if (body) body.innerHTML = '<div style="padding:20px;text-align:center;color:var(--text-muted,#90a4ae);">⏳ 로딩중...</div>';
    _openLotPanel();
    _get('/api/actions/lot-detail/'+encodeURIComponent(lotNo), function(err,res){
      if (err||!res||!res.ok) {
        if (body) body.innerHTML = '<div style="padding:12px;color:#e57373;">❌ 로드 실패</div>';
        return;
      }
      _renderLotPanel(res.data);
    });
  }

  var STATUS_KR = {AVAILABLE:'출고가능',RESERVED:'배정됨',PICKED:'출고작업중',SOLD:'출고완료',PENDING:'입항대기',RETURN:'반품'};
  function _statusBadge(s) {
    var label=STATUS_KR[s]||s;
    var colors={AVAILABLE:'#2e7d32',RESERVED:'#1565c0',PICKED:'#e65100',SOLD:'#424242',PENDING:'#6a1b9a',RETURN:'#c62828'};
    return '<span style="background:'+(colors[s]||'#37474f')+';color:#fff;padding:2px 7px;border-radius:10px;font-size:10px;font-weight:700;">'+_esc(label)+'</span>';
  }
  function _section(title,content){
    return '<div style="margin-bottom:12px;">'
      +'<div style="font-size:11px;font-weight:700;color:var(--text-muted,#90a4ae);padding:4px 0;border-bottom:1px solid var(--panel-border,#37474f);margin-bottom:6px;">'+_esc(title)+'</div>'
      +content+'</div>';
  }
  function _row(label,value){
    return '<div style="display:flex;gap:6px;margin-bottom:4px;font-size:11px;">'
      +'<span style="color:var(--text-muted,#90a4ae);min-width:72px;flex-shrink:0;">'+_esc(label)+'</span>'
      +'<span style="word-break:break-all;">'+(value!=null?value:'—')+'</span></div>';
  }
  function _fmtMt(kg){ return kg==null?'—':(Number(kg)/1000).toFixed(2)+' MT'; }

  function _renderLotPanel(data){
    var body=_el('wlp-body'); if(!body)return;
    var lot=data.lot||{}, tbs=data.tonbags||[], stats=data.tb_stats||[], bl=data.bl_doc, mvs=data.movements||[];
    var html='';
    html+=_section('📋 LOT 기본 정보',
      _row('LOT NO',lot.lot_no)+_row('제품',lot.product)+_row('상태',_statusBadge(lot.status))
      +_row('총중량',_fmtMt(lot.initial_weight))+_row('현재중량',_fmtMt(lot.current_weight))
      +_row('입고일',lot.inbound_date||lot.arrival_date||'—'));
    var statsHtml='<div style="display:flex;flex-wrap:wrap;gap:4px;margin-top:4px;">';
    stats.forEach(function(s){
      statsHtml+='<div style="background:var(--bg,#13191f);border:1px solid var(--panel-border,#37474f);'
        +'border-radius:5px;padding:5px 10px;min-width:80px;text-align:center;">'
        +'<div style="font-size:10px;color:var(--text-muted,#90a4ae);">'+_esc(s.status)+'</div>'
        +'<div style="font-size:14px;font-weight:700;">'+s.cnt+'개</div>'
        +'<div style="font-size:10px;color:var(--text-muted,#90a4ae);">'+(s.mt?(s.mt+' MT'):'—')+'</div>'
        +'</div>';
    });
    statsHtml+='</div>';
    html+=_section('📊 톤백 현황',statsHtml);
    var tbHtml='<table style="width:100%;border-collapse:collapse;font-size:11px;">'
      +'<tr style="color:var(--text-muted,#90a4ae);border-bottom:1px solid var(--panel-border,#37474f);">'
      +'<th style="text-align:left;padding:3px 4px;">Sub</th><th style="text-align:left;padding:3px 4px;">위치</th>'
      +'<th style="text-align:right;padding:3px 4px;">중량</th><th style="text-align:center;padding:3px 4px;">상태</th></tr>';
    tbs.slice(0,20).forEach(function(tb){
      tbHtml+='<tr style="border-bottom:1px solid rgba(255,255,255,.05);">'
        +'<td style="padding:3px 4px;color:var(--accent,#4fc3f7);">'+_esc(String(tb.sub_lt!=null?tb.sub_lt:'—'))+'</td>'
        +'<td style="padding:3px 4px;font-family:monospace;font-size:10px;">'+_esc(tb.location||'미배정')+'</td>'
        +'<td style="padding:3px 4px;text-align:right;">'+(tb.weight?(tb.weight/1000).toFixed(2)+' MT':'—')+'</td>'
        +'<td style="padding:3px 4px;text-align:center;">'+_statusBadge(tb.status)+'</td></tr>';
    });
    if(tbs.length>20) tbHtml+='<tr><td colspan="4" style="padding:4px;text-align:center;color:var(--text-muted,#90a4ae);font-size:10px;">외 '+(tbs.length-20)+'개...</td></tr>';
    tbHtml+='</table>';
    html+=_section('🎒 톤백 목록 ('+tbs.length+'개)',tbHtml);
    if(bl){ html+=_section('🚢 선박 정보',_row('BL NO',bl.bl_no)+_row('선박',bl.vessel)+_row('항차',bl.voyage)+_row('출항일',bl.ship_date)+_row('양하항',bl.port_of_discharge)+_row('선사',bl.carrier_name)); }
    if(mvs.length){
      var mvHtml='<div style="font-size:11px;">';
      mvs.slice(0,3).forEach(function(m){
        var color=m.movement_type==='INBOUND'?'#4caf50':'#ef9a9a';
        mvHtml+='<div style="padding:4px 0;border-bottom:1px solid rgba(255,255,255,.05);">'
          +'<span style="color:'+color+';font-weight:700;">'+_esc(m.movement_type)+'</span>'
          +' <span style="color:var(--text-muted,#90a4ae);">'+_esc(m.movement_date||'')+'</span>'
          +(m.qty_kg?' <b>'+(m.qty_kg/1000).toFixed(2)+' MT</b>':'')+'</div>';
      });
      mvHtml+='</div>';
      html+=_section('📜 최근 이력',mvHtml);
    }
    body.innerHTML=html;
  }

  // ══════════════════════════════════════════════════════════════
  // 1단계: 히트맵 렌더 (온도맵/LOT 토글 + ④ 오늘입고 하이라이트)
  // ══════════════════════════════════════════════════════════════
  var _lastHeatmap = null;

  function _renderHeatmap(data) {
    var racks = data.racks || [];
    _lastHeatmap = racks;
    _lastData    = data;

    var todayLots     = {};
    (data.today_inbound_lots || []).forEach(function(l){ todayLots[l] = true; });
    var unassigned    = data.unassigned_count || 0;
    var dongSummary   = data.dong_summary     || {};

    // ── LOT 색상 미리 배정 ──
    var allLots = [];
    racks.forEach(function(r){
      (r.lots||[]).forEach(function(l){ if(l&&allLots.indexOf(l)<0) allLots.push(l); });
    });
    allLots.forEach(function(l){ _lotColor(l); });

    // ── ② 미배정 배너 갱신 ──
    _updateUnassignedBanner(unassigned);

    // ── ⑤ 90% 초과 배지 갱신 ──
    _updateOccupancyAlert(dongSummary);

    var container = _el('wh-embed-heatmap');
    if (!container) return;

    var dongs = [5,6];
    var html = '';
    dongs.forEach(function(dong){
      var dongRacks = racks.filter(function(r){ return r.dong===dong; });
      var ds = dongSummary[String(dong)] || {};
      var dongPct = ds.occupancy_pct || 0;
      var dongBarColor = dongPct>=90?'#e53935': dongPct>=80?'#fb8c00': dongPct>=50?'#fdd835':'#43a047';

      html += '<div style="margin-bottom:14px;">';
      // 동 헤더: 한 줄, 크게, 클릭 가능 → LOT 테이블 팝업
      html += '<div style="display:flex;align-items:center;gap:8px;margin-bottom:8px;cursor:pointer;padding:4px 0;" '
            + 'onclick="window._whEmbedDongLotTable('+dong+')" '
            + 'title="'+dong+'동 전체 LOT 목록 보기">'
            + '<div style="font-size:16px;font-weight:900;color:var(--text,#eceff1);">'
            +   dong+'동'
            +   (dongPct>=90?' <span style="color:#e53935;font-size:11px;"> ⚠ 포화</span>':'')
            + '</div>'
            + '<div style="flex:1;height:7px;background:rgba(255,255,255,.08);border-radius:4px;overflow:hidden;">'
            +   '<div style="height:100%;width:'+dongPct+'%;background:'+dongBarColor+';border-radius:4px;transition:width .4s;"></div>'
            + '</div>'
            + '<div style="font-size:14px;font-weight:900;color:'+dongBarColor+';min-width:44px;text-align:right;">'+dongPct+'%</div>'
            + '<div style="font-size:10px;color:var(--text-muted,#90a4ae);white-space:nowrap;">▶ LOT 전체</div>'
            + '</div>';

      html += '<div style="display:flex;gap:4px;flex-wrap:nowrap;align-items:flex-end;">';
      dongRacks.forEach(function(r){
        var pct = r.total>0 ? Math.round(r.occupied/r.total*100) : 0;

        // ── 색상: 온도맵 or LOT 색상 ──
        var bg, border, opacity;
        if (_heatMode) {
          bg      = pct===0 ? 'rgba(26,35,126,.3)' : _heatColor(pct);
          border  = '1px solid rgba(255,255,255,.15)';
          opacity = pct===0 ? '0.3' : '1';
        } else {
          bg      = r.dominant_lot ? _lotColor(r.dominant_lot) : 'transparent';
          border  = r.dominant_lot ? '1px solid rgba(255,255,255,.25)' : '1px solid #37474f';
          opacity = r.occupied>0 ? (0.4+pct/100*0.6).toFixed(2) : '0.15';
        }

        // ④ 오늘 입고 LOT가 포함된 랙 → 황금 테두리 빛남
        var isToday = (r.lots||[]).some(function(l){ return todayLots[l]; });
        var todayStyle = isToday
          ? 'box-shadow:0 0 8px 2px #ffd54f,0 0 0 2px #ffd54f;border:2px solid #ffd54f!important;'
          : '';

        var pctColor = pct>=80?'#ef9a9a': pct>=50?'#ffcc80': pct>0?'#a5d6a7':'rgba(255,255,255,.25)';

        html += '<div style="display:flex;flex-direction:column;align-items:center;gap:1px;">';
        // 가동률 텍스트 (크게)
        html += '<div style="font-size:11px;font-weight:800;color:'+pctColor+';line-height:1.1;min-height:13px;">'
              + (pct>0?pct+'%':'') + '</div>';
        // 랙 블록 (크게)
        html += '<div class="wh-rack-block"'
              + ' data-dong="'+r.dong+'" data-rack="'+r.rack+'"'
              + ' title="'+r.dong+'동 '+r.rack_label+'랙 | LOT: '+_esc(r.dominant_lot||'빈 랙')
              +           ' | 점유: '+r.occupied+'/'+r.total+' ('+pct+'%)"'
              + ' style="width:36px;height:52px;border-radius:4px;cursor:pointer;'
              +         'background:'+bg+';border:'+border+';opacity:'+opacity+';'
              +         'display:flex;flex-direction:column;align-items:center;justify-content:flex-end;'
              +         'padding-bottom:4px;transition:transform .1s,box-shadow .1s;'+todayStyle+'"'
              + ' onmouseover="this.style.transform=\'scale(1.12)\';"'
              + ' onmouseout="this.style.transform=\'\';"'
              + ' onclick="window._whEmbedOpenRack('+r.dong+','+r.rack+')">'
              + '<span style="font-size:11px;font-weight:700;color:rgba(255,255,255,.9);">'+r.rack_label+'</span>'
              + '</div>';
        // 오늘 입고 마커
        if (isToday) {
          html += '<div style="font-size:9px;color:#ffd54f;line-height:1;" title="오늘 입고">✨</div>';
        } else {
          html += '<div style="font-size:9px;height:11px;"></div>';
        }
        html += '</div>';
      });
      html += '</div></div>';
    });

    // 범례
    html += '<div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:4px;padding-top:6px;border-top:1px solid var(--panel-border,#37474f);align-items:center;">';
    if (_heatMode) {
      html += '<span style="font-size:10px;color:var(--text-muted,#90a4ae);">온도맵:</span>'
            + '<span style="font-size:10px;"><span style="display:inline-block;width:10px;height:10px;background:#1565c0;border-radius:2px;vertical-align:middle;"></span> 비어있음</span>'
            + '<span style="font-size:10px;"><span style="display:inline-block;width:10px;height:10px;background:#2e7d32;border-radius:2px;vertical-align:middle;"></span> 50~74%</span>'
            + '<span style="font-size:10px;"><span style="display:inline-block;width:10px;height:10px;background:#e65100;border-radius:2px;vertical-align:middle;"></span> 75~89%</span>'
            + '<span style="font-size:10px;"><span style="display:inline-block;width:10px;height:10px;background:#b71c1c;border-radius:2px;vertical-align:middle;"></span> 90%+</span>';
    } else {
      html += '<span style="font-size:10px;color:var(--text-muted,#90a4ae);">가동률:</span>'
            + '<span style="font-size:10px;color:#a5d6a7;">● &lt;50%</span>'
            + '<span style="font-size:10px;color:#ffcc80;">● 50~79%</span>'
            + '<span style="font-size:10px;color:#ef9a9a;">● 80%+</span>'
            + '<span style="font-size:10px;color:var(--text-muted,#90a4ae);margin-left:4px;">LOT:</span>';
      allLots.slice(0,10).forEach(function(l){
        html += '<span style="display:inline-flex;align-items:center;gap:3px;font-size:10px;color:var(--text-muted,#90a4ae);">'
              + '<span style="display:inline-block;width:10px;height:10px;border-radius:2px;background:'+_lotColor(l)+';"></span>'
              + _esc(l)+'</span>';
      });
      if (allLots.length>10) html+='<span style="font-size:10px;color:var(--text-muted,#90a4ae);">외 '+(allLots.length-10)+'개</span>';
    }
    if ((data.today_inbound_lots||[]).length>0){
      html += '<span style="font-size:10px;color:#ffd54f;margin-left:4px;">✨ 오늘 입고</span>';
    }
    html += '</div>';

    container.innerHTML = html;

    // ③ 검색어가 남아있으면 다시 깜빡임 적용
    if (_searchLot) _applySearchHighlight();
  }

  // ══════════════════════════════════════════════════════════════
  // 2단계: 랙 확대 뷰
  // ══════════════════════════════════════════════════════════════
  var _currentRack = null;

  window._whEmbedOpenRack = function(dong, rack) {
    _currentRack = {dong:dong, rack:rack};
    var box = _el('wh-embed-rack-detail');
    if (!box) return;
    box.innerHTML = '<div style="padding:16px;color:var(--text-muted,#90a4ae);font-size:12px;">⏳ 로딩중...</div>';
    box.style.display = 'block';
    _get('/api/warehouse/cell-grid?dong='+dong+'&rack='+rack, function(err,res){
      if (err||!res||!res.ok){ box.innerHTML='<div style="padding:12px;color:#e57373;font-size:12px;">❌ 로드 실패</div>'; return; }
      _renderRackGrid(res.data, box);
      var heatRack = _lastHeatmap && _lastHeatmap.filter(function(r){ return r.dong===dong&&r.rack===rack; })[0];
      if (heatRack && heatRack.dominant_lot) _loadLotDetail(heatRack.dominant_lot);
    });
  };

  function _renderRackGrid(data, box){
    var cells=data.cells||[], maxLv=data.max_level||1, dong=data.dong, rack=data.rack;
    var byCol={};
    cells.forEach(function(c){ if(!byCol[c.col])byCol[c.col]={}; byCol[c.col][c.level]=c; });
    var cols=Object.keys(byCol).map(Number).sort(function(a,b){return a-b;});
    var rackLots=[];
    cells.forEach(function(c){ if(c.lot_no&&rackLots.indexOf(c.lot_no)<0) rackLots.push(c.lot_no); });

    var html='<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px;padding:0 2px;">'
      +'<span style="font-size:12px;font-weight:700;color:var(--accent,#4fc3f7);">📦 '+dong+'동 '+String(rack).padStart(2,'0')+'번 랙</span>'
      +'<div style="display:flex;align-items:center;gap:6px;">';
    rackLots.slice(0,5).forEach(function(l){
      html+='<button onclick="window._whEmbedShowLot(\''+_esc(l)+'\')" '
           +'style="background:'+_lotColor(l)+';color:#fff;border:none;border-radius:4px;'
           +'padding:3px 8px;font-size:10px;cursor:pointer;font-weight:700;">'+_esc(l)+'</button>';
    });
    html+='<button onclick="window._whEmbedCloseRack()" style="background:none;border:none;cursor:pointer;color:var(--text-muted,#90a4ae);font-size:16px;padding:0 4px;">×</button>'
        +'</div></div>';
    html+='<div style="overflow-x:auto;"><table style="border-collapse:collapse;font-size:9px;">';
    html+='<tr><th style="width:24px;color:var(--text-muted,#90a4ae);padding:1px 3px;">층↓열→</th>';
    cols.forEach(function(col){ html+='<th style="width:18px;text-align:center;color:var(--text-muted,#90a4ae);padding:1px;">'+String(col).padStart(2,'0')+'</th>'; });
    html+='</tr>';
    for(var lv=maxLv;lv>=1;lv--){
      html+='<tr><td style="text-align:right;color:var(--text-muted,#90a4ae);padding:1px 4px 1px 2px;font-weight:700;">L'+String(lv).padStart(2,'0')+'</td>';
      cols.forEach(function(col){
        var cell=(byCol[col]||{})[lv];
        if(!cell){ html+='<td style="width:18px;height:18px;"></td>'; return; }
        var isEmpty=(cell.state==='EMPTY'||cell.state==='UNKNOWN');
        var bg=_cellBg(cell), border=isEmpty?'none':'1px solid rgba(255,255,255,.2)';
        var cellJson=JSON.stringify({location:cell.location,lot_no:cell.lot_no||'',sub_lt:cell.sub_lt,state:cell.state,active_count:cell.active_count,capacity:cell.capacity}).replace(/'/g,'&#39;');
        html+='<td onclick="window._whEmbedCellClick(event,\''+cellJson.replace(/"/g,'&quot;')+'\')"'
             +' style="width:18px;height:18px;background:'+bg+';border:'+border+';'
             +'cursor:'+(isEmpty?'default':'pointer')+';border-radius:'+(isEmpty?'0':'2px')+';"></td>';
      });
      html+='</tr>';
    }
    html+='</table></div>';
    box.innerHTML=html;
  }

  window._whEmbedCloseRack = function(){
    var box=_el('wh-embed-rack-detail');
    if(box){ box.style.display='none'; box.innerHTML=''; }
    _currentRack=null; _hideTip(); _closeLotPanel();
  };

  window._whEmbedCellClick = function(ev, cellJsonStr){
    ev.stopPropagation();
    try{
      var cell=JSON.parse(cellJsonStr.replace(/&quot;/g,'"').replace(/&#39;/g,"'"));
      if(cell.state==='EMPTY'){ _hideTip(); return; }
      _showTip(ev,cell);
      if(cell.lot_no) _loadLotDetail(cell.lot_no);
    }catch(e){}
  };

  window._whEmbedShowLot = function(lotNo){ _loadLotDetail(lotNo); };

  // ══════════════════════════════════════════════════════════════
  // 컨트롤 바 (토글 + 검색창 + 새로고침)
  // ══════════════════════════════════════════════════════════════
  function _initControlBar() {
    // wh-embed-section 헤더 행 찾기 → 버튼 주입
    var sec = _el('wh-embed-section');
    if (!sec) return;
    // 기존 헤더 div (첫번째 자식 div)
    var headerDiv = sec.querySelector('div');
    if (!headerDiv) return;

    // 이미 초기화됐으면 스킵
    if (document.getElementById('wh-mode-toggle')) return;

    // 토글 버튼 삽입 (새로고침 버튼 앞)
    var refreshBtn = headerDiv.querySelector('button');
    _renderToggle(null); // 생성만
    var toggleBtn = document.getElementById('wh-mode-toggle');
    if (!toggleBtn) {
      var tb = document.createElement('button');
      tb.id = 'wh-mode-toggle';
      tb.textContent = '🌡 온도맵';
      tb.style.cssText = 'background:rgba(255,255,255,.08);border:1px solid var(--panel-border,#37474f);'
        +'border-radius:4px;color:var(--text-muted,#90a4ae);font-size:11px;cursor:pointer;padding:2px 10px;transition:all .15s;';
      tb.onclick = function(){
        _heatMode = !_heatMode;
        tb.textContent = _heatMode ? '🎨 LOT 색상' : '🌡 온도맵';
        tb.style.background = _heatMode ? 'rgba(229,115,115,.25)' : 'rgba(255,255,255,.08)';
        tb.style.color       = _heatMode ? '#ef9a9a' : 'var(--text-muted,#90a4ae)';
        if (_lastData) _renderHeatmap(_lastData);
      };
      if (refreshBtn) headerDiv.insertBefore(tb, refreshBtn);
      else headerDiv.appendChild(tb);
    }

    // 검색창 삽입
    _renderSearchBox(null);
    var searchWrap = document.getElementById('wh-lot-search-wrap');
    if (!searchWrap) {
      var sw = document.createElement('div');
      sw.id = 'wh-lot-search-wrap';
      sw.style.cssText = 'display:flex;align-items:center;gap:4px;';
      sw.innerHTML = ''
        + '<input id="wh-lot-search-input" type="text" placeholder="LOT 검색..." '
        +   'style="background:var(--bg,#13191f);border:1px solid var(--panel-border,#37474f);'
        +   'border-radius:4px;color:var(--text,#eceff1);font-size:11px;padding:2px 8px;width:130px;outline:none;" />'
        + '<button id="wh-lot-search-btn" '
        +   'style="background:rgba(79,195,247,.15);border:1px solid var(--accent,#4fc3f7);'
        +   'border-radius:4px;color:var(--accent,#4fc3f7);font-size:11px;cursor:pointer;padding:2px 8px;">🔍</button>'
        + '<button id="wh-lot-search-clear" '
        +   'style="background:none;border:1px solid var(--panel-border,#37474f);'
        +   'border-radius:4px;color:var(--text-muted,#90a4ae);font-size:11px;cursor:pointer;padding:2px 6px;display:none;">✕</button>';
      if (refreshBtn) headerDiv.insertBefore(sw, refreshBtn);
      else headerDiv.appendChild(sw);

      setTimeout(function(){
        var inp=_el('wh-lot-search-input'), btn=_el('wh-lot-search-btn'), clr=_el('wh-lot-search-clear');
        function _doSearch(){
          var val=(inp||{}).value||'';
          _searchLot=val.trim().toUpperCase();
          if(clr) clr.style.display=_searchLot?'inline-block':'none';
          _applySearchHighlight();
        }
        if(inp){
          inp.addEventListener('keydown',function(e){if(e.key==='Enter')_doSearch();});
          inp.addEventListener('input',function(){if(!this.value){_searchLot='';if(clr)clr.style.display='none';_applySearchHighlight();}});
        }
        if(btn) btn.onclick=_doSearch;
        if(clr) clr.onclick=function(){_searchLot='';if(inp)inp.value='';clr.style.display='none';_applySearchHighlight();};
      },200);
    }
  }

  // ══════════════════════════════════════════════════════════════
  // 동 클릭 → LOT 전체 테이블 팝업 (메인 대시보드용)
  // ══════════════════════════════════════════════════════════════
  window._whEmbedDongLotTable = function(dong) {
    var popId = 'wh-embed-dong-lot-popup';
    var existing = document.getElementById(popId);
    if (existing) existing.remove();

    var pop = document.createElement('div');
    pop.id = popId;
    pop.style.cssText = [
      'position:fixed','top:50%','left:50%',
      'transform:translate(-50%,-50%)',
      'width:min(960px,92vw)','max-height:82vh',
      'background:var(--bg-card,#1e272e)',
      'border:2px solid var(--accent,#4fc3f7)',
      'border-radius:10px','box-shadow:0 8px 40px rgba(0,0,0,.7)',
      'z-index:10200','display:flex','flex-direction:column','overflow:hidden',
    ].join(';');

    pop.innerHTML = ''
      + '<div style="background:linear-gradient(90deg,#0d47a1,#1565c0);color:#fff;'
      +   'padding:10px 16px;display:flex;align-items:center;gap:8px;flex-shrink:0;">'
      +   '<span style="font-size:15px;font-weight:800;">🏭 ' + dong + '동 — 전체 LOT 현황</span>'
      +   '<span id="wh-edlp-count" style="font-size:12px;opacity:.8;"></span>'
      +   '<button id="wh-edlp-xlsx" '
      +     'style="margin-left:auto;background:rgba(76,175,80,.25);border:1px solid #4caf50;'
      +     'border-radius:5px;color:#a5d6a7;font-size:12px;font-weight:700;cursor:pointer;padding:4px 12px;">'
      +     '📥 엑셀 저장</button>'
      +   '<button onclick="document.getElementById(\''+popId+'\').remove()" '
      +     'style="background:none;border:none;font-size:20px;cursor:pointer;color:#fff;margin-left:8px;">×</button>'
      + '</div>'
      + '<div style="font-size:11px;color:var(--text-muted,#90a4ae);padding:5px 16px;background:var(--bg-hover,#1a2027);flex-shrink:0;">'
      +   '💡 LOT NO 클릭 → 오른쪽 상세 패널에서 톤백/선박/이력 확인 가능'
      + '</div>'
      + '<div id="wh-edlp-body" style="flex:1;overflow:auto;padding:12px;">'
      +   '<div style="text-align:center;padding:30px;color:var(--text-muted,#90a4ae);">⏳ 로딩중...</div>'
      + '</div>';
    document.body.appendChild(pop);

    var _escKbd = function(e){
      if(e.key==='Escape'){ var p=document.getElementById(popId); if(p) p.remove(); document.removeEventListener('keydown',_escKbd); }
    };
    document.addEventListener('keydown', _escKbd);

    // 이 동에 있는 LOT 목록 수집
    var dongLots = {};
    (_lastHeatmap || []).forEach(function(r){
      if (r.dong === dong) {
        (r.lots||[]).forEach(function(l){ if(l) dongLots[l]=true; });
      }
    });
    var lotList = Object.keys(dongLots);

    var body    = document.getElementById('wh-edlp-body');
    var countEl = document.getElementById('wh-edlp-count');

    if (lotList.length === 0) {
      if (body) body.innerHTML = '<div style="text-align:center;padding:30px;color:var(--text-muted,#90a4ae);">이 동에 배치된 LOT 없음</div>';
      return;
    }

    var STATUS_KR3    = {AVAILABLE:'출고가능',RESERVED:'배정됨',PICKED:'출고중',SOLD:'출고완료',PENDING:'대기',RETURN:'반품'};
    var STATUS_COLOR3 = {AVAILABLE:'#2e7d32',RESERVED:'#1565c0',PICKED:'#e65100',SOLD:'#424242',PENDING:'#6a1b9a',RETURN:'#c62828'};

    var _tableRows = [];   // 엑셀 내보내기용 캐시

    var promises = lotList.map(function(lotNo){
      return _get_promise('/api/actions/lot-detail/' + encodeURIComponent(lotNo));
    });

    Promise.all(promises).then(function(results){
      var rows = [];
      results.forEach(function(res){
        if (!res || !res.ok || !res.data) return;
        var lot  = res.data.lot  || {};
        var tbs  = res.data.tonbags || [];
        var alive = tbs.filter(function(t){ return t.status!=='SOLD'&&t.status!=='RETURNED'&&t.status!=='PENDING'; });
        var totalWt = alive.reduce(function(s,t){ return s+(Number(t.weight)||0); }, 0);
        rows.push({
          lot_no:    lot.lot_no   || '',
          product:   lot.product  || '—',
          status:    lot.status   || '—',
          bags:      alive.length,
          weight_mt: (totalWt/1000).toFixed(2),
          inbound:   lot.inbound_date || lot.arrival_date || '—',
        });
      });
      rows.sort(function(a,b){ return a.lot_no.localeCompare(b.lot_no); });
      _tableRows = rows;

      var totalBags = rows.reduce(function(s,r){ return s+r.bags; }, 0);
      var totalMt   = rows.reduce(function(s,r){ return s+parseFloat(r.weight_mt||0); }, 0);
      if (countEl) countEl.textContent = '(' + rows.length + '개 LOT · 톤백 ' + totalBags + '개 · ' + totalMt.toFixed(2) + ' MT)';

      // ── 엑셀 버튼 이벤트 연결 ──
      var xlsxBtn = document.getElementById('wh-edlp-xlsx');
      if (xlsxBtn) {
        xlsxBtn.onclick = function(){
          _exportExcel(_tableRows, dong + '동_LOT현황');
        };
      }

      // ── 테이블 HTML ──
      var tableHtml = '<table id="wh-edlp-table" style="width:100%;border-collapse:collapse;font-size:13px;">'
        + '<thead><tr style="background:var(--bg-hover,#1a2027);position:sticky;top:0;">'
        + '<th style="text-align:left;padding:9px 12px;color:var(--text-muted);font-weight:700;border-bottom:2px solid var(--accent);">LOT NO</th>'
        + '<th style="text-align:left;padding:9px 8px;color:var(--text-muted);font-weight:700;border-bottom:2px solid var(--accent);">제품</th>'
        + '<th style="text-align:center;padding:9px 8px;color:var(--text-muted);font-weight:700;border-bottom:2px solid var(--accent);">상태</th>'
        + '<th style="text-align:right;padding:9px 10px;color:var(--text-muted);font-weight:700;border-bottom:2px solid var(--accent);">톤백</th>'
        + '<th style="text-align:right;padding:9px 10px;color:var(--text-muted);font-weight:700;border-bottom:2px solid var(--accent);">중량(MT)</th>'
        + '<th style="text-align:center;padding:9px 8px;color:var(--text-muted);font-weight:700;border-bottom:2px solid var(--accent);">입고일</th>'
        + '</tr></thead><tbody>';

      rows.forEach(function(r, i){
        var bg2 = i%2===0 ? 'var(--bg,#13191f)' : 'var(--bg-hover,#1a2027)';
        var sc  = STATUS_COLOR3[r.status] || '#37474f';
        var sk  = STATUS_KR3[r.status]    || r.status;
        // LOT NO 셀: 클릭 시 상세 패널 오픈
        tableHtml += '<tr style="background:'+bg2+';border-bottom:1px solid rgba(255,255,255,.04);">'
          + '<td style="padding:8px 12px;font-family:monospace;font-weight:700;font-size:14px;">'
          +   '<span style="color:var(--accent,#4fc3f7);cursor:pointer;text-decoration:underline;text-underline-offset:2px;" '
          +     'onclick="window._whEmbedShowLot(\''+_esc(r.lot_no)+'\')" '
          +     'title="클릭하면 오른쪽에 상세 정보가 열립니다">'+_esc(r.lot_no)+'</span>'
          + '</td>'
          + '<td style="padding:8px 8px;">'+_esc(r.product)+'</td>'
          + '<td style="padding:8px 8px;text-align:center;"><span style="background:'+sc+';color:#fff;padding:3px 9px;border-radius:10px;font-size:11px;font-weight:700;">'+_esc(sk)+'</span></td>'
          + '<td style="padding:8px 10px;text-align:right;font-weight:700;font-size:14px;">'+r.bags+'개</td>'
          + '<td style="padding:8px 10px;text-align:right;font-weight:700;font-size:14px;color:var(--accent,#4fc3f7);">'+r.weight_mt+' MT</td>'
          + '<td style="padding:8px 8px;text-align:center;font-size:12px;color:var(--text-muted);">'+_esc(r.inbound)+'</td>'
          + '</tr>';
      });

      // 합계 행
      tableHtml += '<tr style="background:rgba(79,195,247,.08);border-top:2px solid var(--accent,#4fc3f7);">'
        + '<td colspan="3" style="padding:8px 12px;font-weight:800;color:var(--accent,#4fc3f7);">합계</td>'
        + '<td style="padding:8px 10px;text-align:right;font-weight:800;font-size:14px;">'+totalBags+'개</td>'
        + '<td style="padding:8px 10px;text-align:right;font-weight:800;font-size:14px;color:var(--accent,#4fc3f7);">'+totalMt.toFixed(2)+' MT</td>'
        + '<td></td>'
        + '</tr>';

      tableHtml += '</tbody></table>';
      if (body) body.innerHTML = tableHtml;
    });
  };

  // ── 엑셀(CSV) 내보내기 공통 함수 ──────────────────────────────
  function _exportExcel(rows, filename) {
    if (!rows || rows.length === 0) {
      if (window.showToast) window.showToast('warning', '내보낼 데이터가 없습니다.');
      return;
    }
    // BOM + CSV (Excel에서 한글 깨짐 방지)
    var BOM = '\uFEFF';
    var header = ['LOT NO', '제품', '상태', '톤백(개)', '중량(MT)', '입고일'];
    var lines  = [header.join(',')];
    rows.forEach(function(r){
      lines.push([
        '"' + (r.lot_no   ||'').replace(/"/g,'""') + '"',
        '"' + (r.product  ||'').replace(/"/g,'""') + '"',
        '"' + (r.status   ||'').replace(/"/g,'""') + '"',
        r.bags,
        r.weight_mt,
        '"' + (r.inbound  ||'').replace(/"/g,'""') + '"',
      ].join(','));
    });
    var csv  = BOM + lines.join('\r\n');
    var blob = new Blob([csv], {type: 'text/csv;charset=utf-8;'});
    var url  = URL.createObjectURL(blob);
    var a    = document.createElement('a');
    var now  = new Date();
    var ymd  = now.getFullYear() + ('0'+(now.getMonth()+1)).slice(-2) + ('0'+now.getDate()).slice(-2);
    a.href     = url;
    a.download = filename + '_' + ymd + '.csv';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    if (window.showToast) window.showToast('success', filename + '_' + ymd + '.csv 저장 완료');
  }

  // Promise 버전 fetch 헬퍼
  function _get_promise(url) {
    return fetch(API_BASE + url)
      .then(function(r){ return r.json(); })
      .catch(function(){ return null; });
  }

  // ══════════════════════════════════════════════════════════════
  // 초기화 + 갱신
  // ══════════════════════════════════════════════════════════════
  function _load(){
    _get('/api/warehouse/rack-heatmap', function(err,res){
      if(err||!res||!res.ok) return;
      _renderHeatmap(res.data);
    });
  }

  var _timer=null;
  function _startAutoRefresh(){ if(_timer) clearInterval(_timer); _timer=setInterval(_load,REFRESH_MS); }

  window.initWarehouseEmbed = function(){
    _ensureLotPanel();
    _initControlBar();
    _load();
    _startAutoRefresh();
  };

  window._whEmbedRefresh = function(){
    _load();
    if(_currentRack) window._whEmbedOpenRack(_currentRack.dong, _currentRack.rack);
  };

})();
