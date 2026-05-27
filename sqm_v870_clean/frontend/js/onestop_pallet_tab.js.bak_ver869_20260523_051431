/* =======================================================================
   onestop_pallet_tab.js  (v8.6.8)
   파싱 결과창 — [📦 팔레트/셀] 탭 모듈

   목적:
     입고 서류(PL/BL/Invoice/DO) 파싱 시 LOT 별 팔레트 구성
     (1pack / 2pack)을 자동 판별하고, 사용자가 확인·수정하여
     셀 점유 수량을 사전 확정하는 UI.

   확정 시점:
     이 탭에서 사용자가 [▼] 드롭다운으로 확인한 packing_type 이
     [📤 DB 업로드] 클릭 시 inventory.packing_type 으로 저장됨.

   ───────────────────────────────────────────────────────────────────────
   강화 기능 (v8.6.8):
     ① 자동 판별 결과 시각화 — 초록(자동) / 노랑(수정) / 빨강(미확정)
     ② 컨테이너 요약 카드    — 총 컨테이너 수, 총 셀, 적재 가능 여부
     ③ 500kg LOT 강제 확인   — 드롭다운 1회 클릭 전에는 DB 업로드 차단

   의존:
     window._onestopState.previewRows  (sqm-onestop-inbound.js 가 채움)
     window.escapeHtml, window.showToast
   ======================================================================= */
(function () {
  'use strict';
  if (window.__SQM_ONESTOP_PALLET_TAB_INSTALLED__) return;
  window.__SQM_ONESTOP_PALLET_TAB_INSTALLED__ = true;

  /* ─────────────────────────────────────────────────────────────────────
     1. 상수
     ───────────────────────────────────────────────────────────────────── */
  var PACKING_TYPES = {
    A: { code: 'A', label: '1,000kg 1pack',        cellPerPack: 1, unitKg: 1000 },
    B: { code: 'B', label: '500kg 1pack (특수)',   cellPerPack: 1, unitKg: 500  },
    C: { code: 'C', label: '500kg 2pack',          cellPerPack: 2, unitKg: 500  }
  };

  /* 컨테이너 1대 최대 무게 (20ft / 40ft 공통) */
  var CONTAINER_MAX_KG = 20000;

  /* 자동 판별 허용 오차 (단위 kg 계산 시) */
  var UNIT_KG_TOLERANCE = 50;   /* ±50kg */

  /* 배지 색상 (강화 ①) */
  var BADGE = {
    AUTO:     { bg: '#1b5e20', fg: '#a5d6a7', icon: '✓', text: '자동감지' },
    MODIFIED: { bg: '#f57f17', fg: '#fff9c4', icon: '✎', text: '사용자수정' },
    UNCONFIRMED: { bg: '#b71c1c', fg: '#ffcdd2', icon: '!', text: '미확정' }
  };

  /* 사용자 확인 상태 추적 (강화 ③) */
  /* key: lot_no, value: { type: 'A|B|C', source: 'auto|user', confirmed: bool } */
  var _palletState = {};

  /* ─────────────────────────────────────────────────────────────────────
     2. 자동 판별 — net_weight / mxbg → packing_type
     ───────────────────────────────────────────────────────────────────── */
  function determinePackingType(netKg, mxbg) {
    var nk = Number(netKg) || 0;
    var mb = Number(mxbg)  || 0;
    if (nk <= 0 || mb <= 0) return { type: null, unitKg: 0, confidence: 'unknown' };

    var unitKg = nk / mb;

    /* TYPE A : 약 1,000kg */
    if (Math.abs(unitKg - 1000) <= UNIT_KG_TOLERANCE) {
      return { type: 'A', unitKg: unitKg, confidence: 'high' };
    }
    /* TYPE C 추정 : 약 500kg (기본 2pack 가정) */
    if (Math.abs(unitKg - 500) <= UNIT_KG_TOLERANCE) {
      /* 500kg 짜리는 1pack/2pack 자동 판별 불가능 → 강화 ③ 대상 */
      return { type: 'C', unitKg: unitKg, confidence: 'low' };
    }
    /* 그 외 — 알 수 없음 */
    return { type: null, unitKg: unitKg, confidence: 'unknown' };
  }

  /* ─────────────────────────────────────────────────────────────────────
     3. 셀 점유 계산
     ───────────────────────────────────────────────────────────────────── */
  function calcCellOccupancy(packingType, mxbg) {
    var pt = PACKING_TYPES[packingType];
    var mb = Number(mxbg) || 0;
    if (!pt || mb <= 0) return { cells: 0, pallets: 0 };
    var cells = Math.ceil(mb / pt.cellPerPack);
    return { cells: cells, pallets: cells };
  }

  function calcContainerCount(packingType, mxbg, lotCount) {
    var pt = PACKING_TYPES[packingType];
    var mb = Number(mxbg) || 0;
    if (!pt || mb <= 0) return 0;
    var lotWeight = mb * pt.unitKg;
    var lotPerContainer = Math.floor(CONTAINER_MAX_KG / lotWeight);
    if (lotPerContainer <= 0) return lotCount;
    return Math.ceil(lotCount / lotPerContainer);
  }

  /* ─────────────────────────────────────────────────────────────────────
     4. 배지 HTML (강화 ①)
     ───────────────────────────────────────────────────────────────────── */
  function buildBadge(state) {
    var b;
    if (!state || !state.type) {
      b = BADGE.UNCONFIRMED;
    } else if (state.source === 'user') {
      b = BADGE.MODIFIED;
    } else if (state.confirmed) {
      b = BADGE.AUTO;
    } else {
      b = BADGE.UNCONFIRMED;
    }
    return '<span style="display:inline-block;padding:1px 6px;border-radius:10px;'
      + 'background:' + b.bg + ';color:' + b.fg + ';font-size:10px;font-weight:700;'
      + 'margin-left:4px;white-space:nowrap;">' + b.icon + ' ' + b.text + '</span>';
  }

  /* ─────────────────────────────────────────────────────────────────────
     5. 컨테이너 요약 카드 (강화 ②)
     ───────────────────────────────────────────────────────────────────── */
  function buildSummaryCard(rows) {
    var totalLots     = 0;
    var totalCells    = 0;
    var totalPallets  = 0;
    var totalWeight   = 0;
    var totalContainers = 0;
    var unconfirmed   = 0;

    rows.forEach(function(r) {
      if (!r || !r.lot_no) return;
      totalLots++;
      var st = _palletState[r.lot_no];
      if (!st || !st.type || !st.confirmed) unconfirmed++;
      var pt = st && st.type;
      if (pt) {
        var occ = calcCellOccupancy(pt, r.mxbg);
        totalCells   += occ.cells;
        totalPallets += occ.pallets;
        var unitKg = (PACKING_TYPES[pt] || {}).unitKg || 0;
        totalWeight += unitKg * (Number(r.mxbg) || 0);
      }
    });

    totalContainers = Math.ceil(totalWeight / CONTAINER_MAX_KG) || 0;

    /* 창고 가용률 — 광양 GY Logis 6,572셀 기준 (v8.6.8 랙 이름 규칙 확정)
       5동·6동 동일: 1~3랙(6층) + 4~13랙(7층) + 14~16랙(6층), 각 31열
       동당 = 3×31×6 + 10×31×7 + 3×31×6 = 3,286 셀, ×2동 = 6,572 셀 */
    var WAREHOUSE_TOTAL = 6572;
    var occupancyPct = totalCells > 0
      ? ((totalCells / WAREHOUSE_TOTAL) * 100).toFixed(1)
      : '0.0';

    var loadableColor = unconfirmed === 0 ? '#4caf50' : '#ff9800';
    var loadableText  = unconfirmed === 0
      ? '✅ 적재 준비 완료'
      : '⚠️ 미확정 LOT ' + unconfirmed + '건';

    var card = ''
      + '<div style="display:flex;gap:8px;flex-wrap:wrap;padding:8px 10px;'
      +   'background:var(--bg-hover);border:1px solid var(--panel-border);'
      +   'border-radius:6px;margin-bottom:8px;">'
      + _kpi('총 LOT',       totalLots + ' 건')
      + _kpi('총 셀 점유',   totalCells + ' 셀')
      + _kpi('총 팔레트',    totalPallets + ' 개')
      + _kpi('총 중량',      (totalWeight / 1000).toFixed(1) + ' 톤')
      + _kpi('컨테이너 수',  totalContainers + ' 대 (20ft)')
      + _kpi('창고 점유율',  occupancyPct + ' %')
      + '<div style="flex:1;text-align:right;align-self:center;'
      +   'color:' + loadableColor + ';font-weight:700;font-size:13px;">'
      +   loadableText
      + '</div>'
      + '</div>';
    return card;
  }
  function _kpi(label, value) {
    return '<div style="background:var(--bg-card);border:1px solid var(--panel-border);'
      + 'border-radius:4px;padding:4px 10px;min-width:90px;">'
      + '<div style="font-size:10px;color:var(--text-muted);">' + label + '</div>'
      + '<div style="font-size:13px;font-weight:700;color:var(--fg);">' + value + '</div>'
      + '</div>';
  }

  /* ─────────────────────────────────────────────────────────────────────
     6. LOT 행 렌더
     ───────────────────────────────────────────────────────────────────── */
  function buildLotRow(idx, r) {
    var lotNo = String(r.lot_no || '').trim();
    if (!lotNo) return '';

    /* 자동 판별 */
    var det = determinePackingType(r.net_kg, r.mxbg);

    /* 현재 상태 조회 (없으면 자동 판별값으로 초기화) */
    var st = _palletState[lotNo];
    if (!st) {
      st = {
        type:      det.type,
        source:    'auto',
        /* 500kg(confidence=low)은 사용자 확인 필요 — 강화 ③ */
        confirmed: det.confidence === 'high',
        unitKg:    det.unitKg
      };
      _palletState[lotNo] = st;
    }

    var occ = st.type ? calcCellOccupancy(st.type, r.mxbg) : { cells: 0, pallets: 0 };
    var unitKg = st.type ? PACKING_TYPES[st.type].unitKg : (det.unitKg || 0);
    var needsConfirm = !st.confirmed && Math.abs((det.unitKg || 0) - 500) <= UNIT_KG_TOLERANCE;

    /* 드롭다운 */
    var options = Object.keys(PACKING_TYPES).map(function(k) {
      var pt = PACKING_TYPES[k];
      var sel = (st.type === k) ? 'selected' : '';
      return '<option value="' + k + '" ' + sel + '>'
        + k + ': ' + pt.label + '</option>';
    }).join('');

    /* 행 배경색 — 미확정이면 빨간 톤 */
    var rowBg = needsConfirm ? 'background:rgba(244,67,54,.08);' : '';

    return ''
      + '<tr data-lot="' + escapeHtml(lotNo) + '" style="' + rowBg + '">'
      + '  <td style="text-align:right;color:var(--text-muted);">' + (idx + 1) + '</td>'
      + '  <td style="font-family:monospace;font-weight:700;">' + escapeHtml(lotNo) + '</td>'
      + '  <td>' + escapeHtml(r.product || '') + '</td>'
      + '  <td style="text-align:right;">' + (Number(r.net_kg) || 0).toLocaleString('ko-KR') + ' kg</td>'
      + '  <td style="text-align:right;">' + (Number(r.mxbg) || 0) + ' 개</td>'
      + '  <td style="text-align:right;">' + Math.round(unitKg).toLocaleString('ko-KR') + ' kg</td>'
      + '  <td>'
      + '    <select class="onestop-pallet-select" data-lot="' + escapeHtml(lotNo) + '" '
      +        'onchange="window.onestopPalletChange(this)" '
      +        'style="padding:2px 4px;background:var(--bg-hover);color:var(--fg);'
      +              'border:1px solid var(--border);border-radius:4px;font-size:12px;'
      +              'min-width:170px;' + (needsConfirm ? 'border-color:#f44336;' : '') + '">'
      + options
      + '    </select>'
      + buildBadge(st)
      + '  </td>'
      + '  <td style="text-align:right;font-weight:700;color:var(--accent);">' + occ.cells + ' 셀</td>'
      + '  <td style="text-align:center;">'
      +   (needsConfirm
            ? '<span style="color:#f44336;font-size:11px;font-weight:700;">⚠ 확인 필요</span>'
            : '<span style="color:#4caf50;font-size:11px;">OK</span>')
      + '  </td>'
      + '</tr>';
  }

  /* ─────────────────────────────────────────────────────────────────────
     7. 탭 버튼 / 패널 HTML
     ───────────────────────────────────────────────────────────────────── */
  function getPalletTabButtonHtml() {
    return ''
      + '<button class="btn btn-tab" id="onestop-pallet-tab-btn" '
      +   'onclick="window.onestopShowPalletTab()" '
      +   'style="margin-left:8px;padding:4px 10px;background:var(--accent);'
      +         'color:#fff;border:none;border-radius:6px;font-size:12px;'
      +         'font-weight:700;cursor:pointer;">'
      + '📦 팔레트/셀'
      + '<span id="onestop-pallet-tab-warn" style="display:none;margin-left:4px;'
      +       'background:#f44336;color:#fff;border-radius:10px;padding:0 5px;'
      +       'font-size:10px;">!</span>'
      + '</button>';
  }

  function getPalletTabPanelHtml() {
    return ''
      + '<div id="onestop-pallet-tab-panel" '
      +     'style="display:none;position:absolute;top:42px;left:14px;right:14px;'
      +           'bottom:14px;background:var(--bg-card);border:2px solid var(--accent);'
      +           'border-radius:8px;padding:10px;z-index:10;overflow-y:auto;'
      +           'box-shadow:0 4px 20px rgba(0,0,0,.4);">'
      + '  <div style="display:flex;align-items:center;margin-bottom:8px;">'
      + '    <h3 style="margin:0;font-size:14px;color:var(--accent);">📦 팔레트 구성 / 셀 점유</h3>'
      + '    <span style="font-size:11px;color:var(--text-muted);margin-left:10px;">'
      +       '서류 파싱 결과 기반 자동 판별 — 500kg LOT는 사용자 확인 필요'
      + '    </span>'
      + '    <button onclick="window.onestopHidePalletTab()" '
      +       'style="margin-left:auto;background:none;border:none;font-size:18px;'
      +             'cursor:pointer;color:var(--text-muted);">×</button>'
      + '  </div>'
      + '  <div id="onestop-pallet-summary"></div>'
      + '  <table class="data-table" style="width:100%;font-size:12px;">'
      + '    <thead><tr>'
      + '      <th style="width:40px;">#</th>'
      + '      <th>LOT 번호</th>'
      + '      <th>제품</th>'
      + '      <th style="width:90px;text-align:right;">순중량</th>'
      + '      <th style="width:60px;text-align:right;">톤백수</th>'
      + '      <th style="width:80px;text-align:right;">단위kg</th>'
      + '      <th style="width:230px;">팔레트 구성</th>'
      + '      <th style="width:70px;text-align:right;">셀 점유</th>'
      + '      <th style="width:90px;text-align:center;">상태</th>'
      + '    </tr></thead>'
      + '    <tbody id="onestop-pallet-tbody"></tbody>'
      + '  </table>'
      + '  <div style="margin-top:8px;padding:6px 10px;background:var(--bg-hover);'
      +         'border-left:3px solid var(--accent);border-radius:4px;'
      +         'font-size:11px;color:var(--text-muted);">'
      + '    💡 <b>500kg LOT 안내</b>: 500kg는 서류만으로 1pack/2pack을 자동 판별할 수 없습니다. '
      +       '드롭다운에서 직접 선택하셔야 [📤 DB 업로드]가 활성화됩니다.'
      + '  </div>'
      + '</div>';
  }

  /* ─────────────────────────────────────────────────────────────────────
     8. 렌더 & 이벤트
     ───────────────────────────────────────────────────────────────────── */
  function renderPalletTab() {
    var rows = (window._onestopState && window._onestopState.previewRows) || [];
    var tbody   = document.getElementById('onestop-pallet-tbody');
    var summary = document.getElementById('onestop-pallet-summary');
    if (!tbody || !summary) return;

    /* 본문 */
    if (rows.length === 0) {
      tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;color:var(--text-muted);'
        + 'padding:20px;">📭 파싱된 LOT 가 없습니다.</td></tr>';
    } else {
      tbody.innerHTML = rows.map(function(r, i) { return buildLotRow(i, r); }).join('');
    }

    /* 요약 카드 (강화 ②) */
    summary.innerHTML = buildSummaryCard(rows);

    /* DB 업로드 버튼 활성화 여부 (강화 ③) */
    updateDbUploadGate(rows);
  }

  /* 강화 ③ — 500kg LOT 강제 확인 */
  function updateDbUploadGate(rows) {
    rows = rows || (window._onestopState && window._onestopState.previewRows) || [];
    var unconfirmed = 0;
    rows.forEach(function(r) {
      if (!r || !r.lot_no) return;
      var st = _palletState[r.lot_no];
      if (!st || !st.type || !st.confirmed) unconfirmed++;
    });

    var btn  = document.getElementById('onestop-save-btn');
    var warn = document.getElementById('onestop-pallet-tab-warn');

    if (btn) {
      if (unconfirmed > 0) {
        btn.setAttribute('data-pallet-block', '1');
        btn.disabled = true;
        btn.title = '미확정 LOT ' + unconfirmed + '건 — 팔레트/셀 탭에서 확인하세요';
      } else {
        btn.removeAttribute('data-pallet-block');
        /* 파싱 완료 상태이면 다시 활성화 */
        if (window._onestopState && window._onestopState.parsed) btn.disabled = false;
        btn.title = '';
      }
    }
    if (warn) {
      warn.style.display = unconfirmed > 0 ? 'inline-block' : 'none';
      warn.textContent = unconfirmed > 0 ? String(unconfirmed) : '';
    }
  }

  /* ─────────────────────────────────────────────────────────────────────
     9. window 공개 API
     ───────────────────────────────────────────────────────────────────── */
  window.onestopShowPalletTab = function() {
    var p = document.getElementById('onestop-pallet-tab-panel');
    if (!p) return;
    p.style.display = 'block';
    renderPalletTab();
  };
  window.onestopHidePalletTab = function() {
    var p = document.getElementById('onestop-pallet-tab-panel');
    if (p) p.style.display = 'none';
  };

  window.onestopPalletChange = function(selectEl) {
    if (!selectEl) return;
    var lotNo  = selectEl.getAttribute('data-lot');
    var newVal = selectEl.value;
    if (!lotNo || !PACKING_TYPES[newVal]) return;

    var st = _palletState[lotNo] || {};
    st.type      = newVal;
    st.source    = 'user';     /* 사용자가 선택 → 노랑 배지 */
    st.confirmed = true;        /* 강화 ③ — 클릭하면 확정 */
    _palletState[lotNo] = st;

    /* previewRows 에도 반영 → DB 업로드 시 같이 전송 */
    var rows = (window._onestopState && window._onestopState.previewRows) || [];
    rows.forEach(function(r) {
      if (r && r.lot_no === lotNo) r.packing_type = newVal;
    });

    renderPalletTab();
  };

  /* 외부(파싱 완료 시점)에서 호출 — packing_type 초기화 + 자동 적용
     v8.6.8 Hybrid: 사용자가 사전 결정한 defaultPacking 우선 적용 */
  window.onestopPalletInitFromRows = function() {
    _palletState = {};   /* 새 파싱이면 리셋 */
    var rows = (window._onestopState && window._onestopState.previewRows) || [];
    /* 사용자 사전 결정값 읽기 — sqm-onestop-inbound.js 에서 노출 */
    var pre = (typeof window.onestopGetDefaultPacking === 'function')
              ? window.onestopGetDefaultPacking() : 'C';
    var isForced = (pre === 'A' || pre === 'B' || pre === 'C');
    var isManual = (pre === 'manual');

    rows.forEach(function(r) {
      if (!r || !r.lot_no) return;

      if (isForced) {
        /* A/B/C 강제 — 모든 LOT 에 일괄 적용, 🟢 사용자결정 표시 */
        _palletState[r.lot_no] = {
          type:      pre,
          source:    'user',
          confirmed: true,
          unitKg:    (pre === 'A' ? 1000 : 500)
        };
        r.packing_type = pre;
      } else if (isManual) {
        /* 강제 미확정 — 사용자가 [📦 팔레트/셀] 탭에서 LOT 별 클릭 */
        _palletState[r.lot_no] = {
          type:      '',
          source:    'pending',
          confirmed: false,
          unitKg:    0
        };
        r.packing_type = '';
      } else {
        /* 'auto' — 기존 자동 판별 로직 */
        var det = determinePackingType(r.net_kg, r.mxbg);
        _palletState[r.lot_no] = {
          type:      det.type,
          source:    'auto',
          confirmed: det.confidence === 'high',  /* 500kg 은 false */
          unitKg:    det.unitKg
        };
        r.packing_type = det.type || '';
      }
    });
    updateDbUploadGate(rows);
  };

  /* HTML 조각 export — 부모(sqm-onestop-inbound.js) 가 주입할 때 사용 */
  window.getPalletTabButtonHtml = getPalletTabButtonHtml;
  window.getPalletTabPanelHtml  = getPalletTabPanelHtml;

  /* 외부에서 강제로 게이트만 갱신할 때 */
  window.onestopPalletUpdateGate = function() { updateDbUploadGate(); };

  /* ─────────────────────────────────────────────────────────────────────
    랙 위치(Cell) 검증 — v8.6.8 광양 GY Logis 규칙 확정
    형식: G{동}-{칸}-{열}-{층}
      동:   5 | 6
      칸:   01~16 (랙 번호)
      열:   01~31
      층:   01~07 (랙별 가변)
            ┌─ 1~3랙   → 최대 06층
            ├─ 4~13랙  → 최대 07층
            └─ 14~16랙 → 최대 06층
    예: G5-04-01-07 = 5동 4번랙 1열 7층
        G5-16-31-06 = 5동 16번랙 31열 6층
    ───────────────────────────────────────────────────────────────────── */
  var CELL_RE = /^G([56])-(\d{2})-(\d{2})-(\d{2})$/;
  function maxLevelForRack(rackNo) {
    if (rackNo >= 1 && rackNo <= 3)   return 6;
    if (rackNo >= 4 && rackNo <= 13)  return 7;
    if (rackNo >= 14 && rackNo <= 16) return 6;
    return 0;
  }
  function validateCellLocation(loc) {
    var s = String(loc || '').trim().toUpperCase();
    var m = CELL_RE.exec(s);
    if (!m) return { ok: false, reason: '형식 오류 (예: G5-04-01-07)' };
    var dong  = Number(m[1]);
    var rack  = Number(m[2]);
    var col   = Number(m[3]);
    var level = Number(m[4]);
    if (dong !== 5 && dong !== 6)        return { ok: false, reason: '동은 5 또는 6만 허용' };
    if (rack  < 1 || rack  > 16)          return { ok: false, reason: '칸(랙)은 01~16' };
    if (col   < 1 || col   > 31)          return { ok: false, reason: '열은 01~31' };
    var maxLv = maxLevelForRack(rack);
    if (level < 1 || level > maxLv)       return { ok: false, reason: '층은 01~' + String(maxLv).padStart(2,'0') + ' (랙 ' + rack + '번 기준)' };
    return { ok: true, dong: dong, rack: rack, col: col, level: level };
  }
  window.validateCellLocation = validateCellLocation;
  window.maxLevelForRack      = maxLevelForRack;

  /* ─────────────────────────────────────────────────────────────────────
    유틸 — escapeHtml 가 없으면 폴백
    ───────────────────────────────────────────────────────────────────── */
  function escapeHtml(s) {
    if (window.escapeHtml) return window.escapeHtml(s);
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

})();
