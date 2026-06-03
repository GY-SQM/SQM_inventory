/* SQM v8.7.0 — Page Summary Helper
 * 6개 페이지(Pending / Available / Allocation / Picked / Return / Sold) 공통 합계 표시.
 *
 * 제공 함수 (window 전역):
 *   - SQMSummary.compute(rows, opts)        → {lotCount, tonbagCount, tonbagMt, sampleCount, sampleMt, totalMt}
 *   - SQMSummary.buildHeaderHTML(stats)     → 타이틀 옆에 붙일 inline HTML (badge 스타일)
 *   - SQMSummary.buildFooterHTML(stats, opts) → tfoot 노란색 합계 HTML (colspan 자동)
 *   - SQMSummary.buildPeriodFilterHTML(state, onChangeJs) → Sold 전용 기간 필터 UI
 *   - SQMSummary.filterByPeriod(rows, state, dateField) → 기간 조건으로 rows 필터링
 *   - SQMSummary.todayKST()                 → 'YYYY-MM-DD'
 *
 * 통일 단위: 모든 무게는 MT (소수 4자리 표시)
 * 색상: 다른 페이지와 일관된 #FFD600 노란색 푸터
 * 샘플 판정: 1행당 qty < 0.01 MT (10kg) 미만 → 샘플로 간주
 */
(function(){
  'use strict';

  var SAMPLE_MT_THRESHOLD = 0.01;  // 10 kg 미만 = 샘플

  function _num(v){ var n = Number(v); return isFinite(n) ? n : 0; }
  function _fmtMt(v){ return (Math.round(_num(v) * 10000) / 10000).toFixed(4); }
  function _fmtInt(v){ return Math.round(_num(v)).toLocaleString('ko-KR'); }

  function todayKST(){
    var d = new Date();
    var ms = d.getTime() + (9*60 - d.getTimezoneOffset()) * 60 * 1000;
    return new Date(ms).toISOString().slice(0,10);
  }

  /**
   * 행 배열에서 톤백/샘플 분리 합계 계산.
   * @param {Array} rows
   * @param {Object} opts
   *   - qtyField: qty(MT) 필드명 또는 함수(r) (기본: 'qty_mt' → 없으면 net_weight/1000)
   *   - tonbagCountField: 톤백 개수 필드명 또는 함수 (기본: 'sub_lt' → 없으면 1)
   *   - isSampleField: 샘플 판정 필드 또는 함수 (기본: qty < 0.01 또는 is_sample === 1)
   *   - lotField: LOT 필드명 (기본: 'lot_no')
   * @returns {Object} stats
   */
  function compute(rows, opts){
    rows = Array.isArray(rows) ? rows : [];
    opts = opts || {};
    var qtyField = opts.qtyField || 'qty_mt';
    var tonbagCountField = opts.tonbagCountField || 'sub_lt';
    var lotField = opts.lotField || 'lot_no';

    var lotSet = {};
    var tonbagCount = 0, tonbagMt = 0;
    var sampleCount = 0, sampleMt = 0;

    rows.forEach(function(r){
      if (!r) return;
      // qty_mt 추출 (qty_mt 없으면 net_weight kg → MT 변환)
      var qty;
      if (typeof qtyField === 'function') qty = _num(qtyField(r));
      else {
        qty = _num(r[qtyField]);
        if (qty === 0 && r.net_weight != null) qty = _num(r.net_weight) / 1000;
      }

      // 톤백 개수
      var bags;
      if (typeof tonbagCountField === 'function') bags = _num(tonbagCountField(r));
      else {
        bags = _num(r[tonbagCountField]);
        if (bags === 0) bags = _num(r.bag_count) || _num(r.bags) || 0;
      }

      // 샘플 판정
      var isSample;
      if (typeof opts.isSampleField === 'function') isSample = !!opts.isSampleField(r);
      else if (r.is_sample != null) isSample = !!_num(r.is_sample);
      else isSample = qty > 0 && qty < SAMPLE_MT_THRESHOLD;

      // LOT 카운트
      var lot = r[lotField];
      if (lot) lotSet[lot] = 1;

      if (isSample) {
        sampleCount += (bags || 1);
        sampleMt += qty;
      } else {
        tonbagCount += bags;
        tonbagMt += qty;
      }
    });

    var lotCount = Object.keys(lotSet).length;
    var totalMt = tonbagMt + sampleMt;

    // v8.7.0 임시 디버그 (브라우저 콘솔에 첫 row 샘플 출력)
    if (window._SQM_DEBUG_SUMMARY !== false && rows.length > 0) {
      try {
        console.log('[SQMSummary] rows=' + rows.length + ' tonbag=' + tonbagCount + '/' + tonbagMt.toFixed(4) + 'MT sample=' + sampleCount + '/' + sampleMt.toFixed(4) + 'MT lot=' + lotCount,
          'first row:', rows[0]);
      } catch(_e) {}
    }

    return {
      lotCount: lotCount,
      rowCount: rows.length,
      tonbagCount: tonbagCount,
      tonbagMt: tonbagMt,
      sampleCount: sampleCount,
      sampleMt: sampleMt,
      totalMt: totalMt
    };
  }

  /**
   * 타이틀 옆 inline 헤더 HTML.
   * 예: 📦 톤백 47개 · 23.500 MT  🧪 샘플 5개 · 0.005 MT  합계 23.505 MT
   */
  function buildHeaderHTML(stats){
    if (!stats) return '';
    // 빈 데이터(전부 0)면 헤더 박스 숨김 — 의미 없는 "0개 0.0000 MT" 방지
    if ((stats.tonbagCount||0) === 0 && (stats.sampleCount||0) === 0 && (stats.totalMt||0) === 0) return '';
    var s = 'display:inline-block;padding:3px 10px;margin-left:6px;background:rgba(255,214,0,0.15);'
          + 'border:1px solid rgba(255,214,0,0.5);border-radius:6px;font-size:12px;color:var(--text,#e2e8f0);'
          + 'font-family:monospace;white-space:nowrap;';
    var html = '<span style="' + s + '" title="톤백 합계">📦 톤백 ' + _fmtInt(stats.tonbagCount) + '개 · ' + _fmtMt(stats.tonbagMt) + ' MT</span>';
    if (stats.sampleCount > 0 || stats.sampleMt > 0) {
      html += '<span style="' + s + '" title="샘플 합계">🧪 샘플 ' + _fmtInt(stats.sampleCount) + '개 · ' + _fmtMt(stats.sampleMt) + ' MT</span>';
    }
    var sTot = s.replace('rgba(255,214,0,0.15)', 'rgba(255,214,0,0.35)').replace('rgba(255,214,0,0.5)', '#FFD600');
    html += '<span style="' + sTot + 'font-weight:700" title="총합">합계 ' + _fmtMt(stats.totalMt) + ' MT</span>';
    return html;
  }

  /**
   * 노란색 tfoot 합계 HTML.
   * @param {Object} stats
   * @param {Object} opts
   *   - colspan: 테이블 컬럼 수 (필수)
   *   - extra: 추가 표시 텍스트 (옵션)
   */
  function buildFooterHTML(stats, opts){
    if (!stats) return '';
    opts = opts || {};
    var col = opts.colspan || 1;
    var extra = opts.extra ? (' · ' + opts.extra) : '';
    var html = '<tfoot><tr style="background:#FFD600;font-weight:800;color:#222">'
             + '<td colspan="' + col + '" style="text-align:right;padding:8px 12px;font-size:13px">'
             + '합계 (' + _fmtInt(stats.lotCount) + ' LOT) · '
             + '📦 톤백 ' + _fmtInt(stats.tonbagCount) + '개 ' + _fmtMt(stats.tonbagMt) + ' MT';
    if (stats.sampleCount > 0 || stats.sampleMt > 0) {
      html += ' · 🧪 샘플 ' + _fmtInt(stats.sampleCount) + '개 ' + _fmtMt(stats.sampleMt) + ' MT';
    }
    html += ' · 총 ' + _fmtMt(stats.totalMt) + ' MT' + extra
          + '</td></tr></tfoot>';
    return html;
  }

  /**
   * Sold 기간 필터 UI.
   * @param {Object} state - {from:'YYYY-MM-DD', to:'YYYY-MM-DD'} (기본=오늘)
   * @param {String} onChangeJs - 날짜 변경 시 실행할 JS 코드 (예: 'window.loadOutboundPage()')
   */
  function buildPeriodFilterHTML(state, onChangeJs){
    state = state || {};
    var today = todayKST();
    var from = state.from || today;
    var to = state.to || today;
    var cb = onChangeJs || 'window.loadOutboundPage && window.loadOutboundPage()';
    var ds = 'padding:4px 8px;background:var(--bg,#0f172a);border:1px solid var(--border,#334155);border-radius:4px;color:var(--text,#e2e8f0);font-size:12px;font-family:monospace;';
    var bs = 'padding:4px 10px;background:var(--surface,#1e293b);border:1px solid var(--border,#334155);border-radius:4px;color:var(--text,#e2e8f0);font-size:12px;cursor:pointer;';
    var html = '<div style="display:inline-flex;align-items:center;gap:6px;margin-left:8px;flex-wrap:wrap" id="sold-period-filter">'
      + '<span style="font-size:12px;color:var(--text-muted)">📅</span>'
      + '<input type="date" id="sold-period-from" value="' + from + '" max="' + today + '" style="' + ds + '" '
      + 'onchange="window.SQMSummary._setPeriod({from:this.value,to:document.getElementById(\'sold-period-to\').value});' + cb + '">'
      + '<span style="color:var(--text-muted)">~</span>'
      + '<input type="date" id="sold-period-to" value="' + to + '" max="' + today + '" style="' + ds + '" '
      + 'onchange="window.SQMSummary._setPeriod({from:document.getElementById(\'sold-period-from\').value,to:this.value});' + cb + '">'
      + '<button style="' + bs + '" onclick="window.SQMSummary._presetPeriod(\'today\');' + cb + '" title="당일">당일</button>'
      + '<button style="' + bs + '" onclick="window.SQMSummary._presetPeriod(\'month\');' + cb + '" title="이번 달 1일부터 오늘까지">이번 달</button>'
      + '<button style="' + bs + '" onclick="window.SQMSummary._presetPeriod(\'recent30\');' + cb + '" title="최근 30일">최근 30일</button>'
      + '<button style="' + bs + '" onclick="window.SQMSummary._presetPeriod(\'all\');' + cb + '" title="전체 기간">전체</button>'
      + '</div>';
    return html;
  }

  /** 기간 필터로 rows 걸러내기 */
  function filterByPeriod(rows, state, dateField){
    if (!Array.isArray(rows)) return [];
    if (!state || (!state.from && !state.to)) return rows;
    var df = dateField || 'sold_date';
    return rows.filter(function(r){
      var d = r && r[df];
      if (!d) return false;
      var dd = String(d).slice(0,10);
      if (state.from && dd < state.from) return false;
      if (state.to && dd > state.to) return false;
      return true;
    });
  }

  // ── 기간 state 관리 (window 전역) ──
  function _setPeriod(s){
    window._soldPeriodState = window._soldPeriodState || {};
    if (s && s.from) window._soldPeriodState.from = s.from;
    if (s && s.to)   window._soldPeriodState.to   = s.to;
  }
  function _presetPeriod(mode){
    var today = todayKST();
    var d = new Date(today + 'T00:00:00Z');
    var from = today, to = today;
    if (mode === 'today')   { from = today; to = today; }
    else if (mode === 'month') {
      from = today.slice(0,7) + '-01';
      to = today;
    }
    else if (mode === 'recent30') {
      var d30 = new Date(d.getTime() - 30*86400000);
      from = d30.toISOString().slice(0,10);
      to = today;
    }
    else if (mode === 'all') {
      from = '2000-01-01';
      to = today;
    }
    window._soldPeriodState = { from: from, to: to };
  }

  // export
  window.SQMSummary = {
    SAMPLE_MT_THRESHOLD: SAMPLE_MT_THRESHOLD,
    compute: compute,
    buildHeaderHTML: buildHeaderHTML,
    buildFooterHTML: buildFooterHTML,
    buildPeriodFilterHTML: buildPeriodFilterHTML,
    filterByPeriod: filterByPeriod,
    todayKST: todayKST,
    _setPeriod: _setPeriod,
    _presetPeriod: _presetPeriod
  };
})();
