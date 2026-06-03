/* =======================================================================
   sqm-case3-dialog.js  (v8.6.8)
   CASE 3 — 500kg 2pack 부분 출고 후 잔여 톤백 처리 다이얼로그

   호출 방법:
     // 출고 확정 응답 처리 시
     if (res.data && res.data.half_cells && res.data.half_cells.length) {
       window.showCase3Dialog(res.data.half_cells);
     }

     // 누적된 HALF 셀 전체 처리 (메뉴에서)
     window.showCase3Queue();   // GET /api/warehouse/half-cells 호출

   동작:
     - half_cells[i].remaining[*] 각 톤백에 대해 STAY 또는 MOVE 선택
     - STAY: 원위치 유지 (audit_log 만)
     - MOVE: 새 location 입력 (G5-04-01-07 형식 검증) → 이동 + stock_movement
     - 나중에 처리: 다이얼로그 닫고 HALF 상태 유지 (다음에 메뉴에서 처리 가능)

   API:
     POST /api/warehouse/case3-resolve
     GET  /api/warehouse/half-cells
   ======================================================================= */
(function () {
  'use strict';
  if (window.__SQM_CASE3_DIALOG_INSTALLED__) return;
  window.__SQM_CASE3_DIALOG_INSTALLED__ = true;

  function _api()         { return (typeof API !== 'undefined') ? API : ''; }
  function _toast(t, msg) { if (window.showToast) window.showToast(t, msg); }
  function _esc(s) {
    if (window.escapeHtml) return window.escapeHtml(s);
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  /* ── 모달 생성 ── */
  var _modal = null;
  function _ensureModal() {
    if (_modal && document.body.contains(_modal)) {
      _modal.style.display = 'flex';
      return _modal;
    }
    var d = document.createElement('div');
    d.id = 'sqm-case3-dialog';
    d.style.cssText = ''
      + 'position:fixed;top:60px;left:50%;transform:translateX(-50%);'
      + 'width:min(1100px,94vw);max-height:84vh;background:var(--bg-card);'
      + 'border:2px solid #f57f17;border-radius:10px;'
      + 'box-shadow:0 8px 40px rgba(0,0,0,.6);z-index:10060;'
      + 'display:flex;flex-direction:column;overflow:hidden;';
    d.innerHTML = ''
      + '<div id="case3-hdr" style="cursor:move;background:linear-gradient(90deg,#f57f17,#ff9800);'
      +     'color:#fff;padding:10px 16px;display:flex;align-items:center;gap:10px;'
      +     'flex-shrink:0;">'
      + '  <span style="font-size:16px;font-weight:700;">🟨 CASE 3 잔여 톤백 처리</span>'
      + '  <span id="case3-summary" style="font-size:11px;opacity:.9;"></span>'
      + '  <button id="case3-close" '
      +       'style="margin-left:auto;background:none;border:none;font-size:18px;'
      +             'cursor:pointer;color:#fff;padding:0 4px;">×</button>'
      + '</div>'
      + '<div style="padding:10px 16px;background:rgba(245,127,23,.08);'
      +     'font-size:12px;color:var(--fg);border-bottom:1px solid var(--panel-border);">'
      + '  💡 500kg 2pack 중 1pack 만 출고되어 셀에 잔여 톤백이 있습니다.<br>'
      + '  각 잔여 톤백에 대해 <b>STAY(원위치 유지)</b> 또는 <b>MOVE(다른 셀로 이동)</b> 를 선택하세요.<br>'
      + '  처리하지 않으면 HALF 상태로 누적되며, 메뉴 [HALF 셀 보기]에서 나중에 처리 가능.'
      + '</div>'
      + '<div id="case3-body" style="flex:1;overflow:auto;padding:10px 16px;"></div>'
      + '<div style="padding:10px 16px;border-top:1px solid var(--panel-border);'
      +     'background:var(--bg-hover);display:flex;gap:8px;justify-content:flex-end;'
      +     'flex-shrink:0;">'
      + '  <button id="case3-defer" class="btn">⏳ 나중에 처리</button>'
      + '  <button id="case3-apply" class="btn btn-primary">✅ 선택 적용</button>'
      + '</div>';
    document.body.appendChild(d);
    _modal = d;
    document.getElementById('case3-close').onclick = function() { d.style.display = 'none'; };
    document.getElementById('case3-defer').onclick = function() {
      d.style.display = 'none';
      _toast('info', '잔여 톤백 ' + _currentCount() + '건이 HALF 상태로 누적됨 — 메뉴에서 나중에 처리 가능');
    };
    document.getElementById('case3-apply').onclick = _applyAll;
    if (typeof window._makeDraggableResizable === 'function') {
      window._makeDraggableResizable(d, document.getElementById('case3-hdr'));
    }
    return d;
  }

  /* ── 행 렌더 ── */
  function _renderRow(cellIdx, cell, tbIdx, tb) {
    var rowId = 'case3-row-' + cellIdx + '-' + tbIdx;
    var inpId = 'case3-loc-' + cellIdx + '-' + tbIdx;
    return ''
      + '<div id="' + rowId + '" class="case3-row" '
      +     'data-tonbag-id="' + tb.id + '" '
      +     'data-from-loc="' + _esc(cell.location) + '" '
      +     'style="border:1px solid var(--panel-border);border-radius:6px;'
      +           'padding:10px 12px;margin-bottom:8px;background:var(--bg);">'
      + '  <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap;">'
      + '    <div style="min-width:140px;">'
      + '      <div style="font-size:11px;color:var(--text-muted);">셀 위치 (현재)</div>'
      + '      <div style="font-family:Consolas,monospace;font-weight:700;color:var(--accent);">'
      +          _esc(cell.location) + '</div>'
      + '    </div>'
      + '    <div style="min-width:140px;">'
      + '      <div style="font-size:11px;color:var(--text-muted);">LOT / SubLT</div>'
      + '      <div style="font-family:Consolas,monospace;">'
      +          _esc(tb.lot_no) + ' / ' + _esc(tb.sub_lt) + '</div>'
      + '    </div>'
      + '    <div>'
      + '      <div style="font-size:11px;color:var(--text-muted);">중량</div>'
      + '      <div>' + (Number(tb.weight_kg) || 0).toLocaleString('ko-KR') + ' kg</div>'
      + '    </div>'
      + '    <div style="margin-left:auto;display:flex;gap:6px;align-items:center;">'
      + '      <label style="display:flex;align-items:center;gap:4px;cursor:pointer;">'
      + '        <input type="radio" name="' + rowId + '-r" value="STAY" checked '
      +              'onchange="window._case3OnModeChange(\'' + rowId + '\', \'STAY\')"> '
      + '        <span style="font-weight:700;color:#4caf50;">STAY (원위치)</span>'
      + '      </label>'
      + '      <label style="display:flex;align-items:center;gap:4px;cursor:pointer;">'
      + '        <input type="radio" name="' + rowId + '-r" value="MOVE" '
      +              'onchange="window._case3OnModeChange(\'' + rowId + '\', \'MOVE\')"> '
      + '        <span style="font-weight:700;color:#2196f3;">MOVE (이동)</span>'
      + '      </label>'
      + '    </div>'
      + '  </div>'
      + '  <div class="case3-move-input" data-row="' + rowId + '" '
      +       'style="margin-top:8px;display:none;align-items:center;gap:8px;">'
      + '    <label style="font-size:12px;color:var(--text-muted);">→ 새 위치:</label>'
      + '    <input id="' + inpId + '" type="text" placeholder="G5-04-01-07" '
      +          'style="padding:4px 10px;background:var(--bg-hover);color:var(--fg);'
      +                'border:1px solid var(--border);border-radius:4px;font-size:12px;'
      +                'width:160px;font-family:Consolas,monospace;text-transform:uppercase;" '
      +          'oninput="window._case3ValidateLoc(\'' + inpId + '\')">'
      + '    <span id="' + inpId + '-msg" style="font-size:11px;"></span>'
      + '  </div>'
      + '  <div class="case3-result" data-row="' + rowId + '" '
      +       'style="margin-top:6px;font-size:11px;display:none;"></div>'
      + '</div>';
  }

  /* ── 위치 형식 검증 (클라이언트단 — 최종 검증은 백엔드) ── */
  var LOC_RE = /^G([56])-(\d{2})-(\d{2})-(\d{2})$/;
  var _rackLevelMax = {};
  for (var r = 1; r <= 16; r++) {
    _rackLevelMax[r] = (r >= 4 && r <= 13) ? 7 : 6;
  }
  function _validateLocClient(loc) {
    var s = String(loc || '').trim().toUpperCase();
    var m = LOC_RE.exec(s);
    if (!m) return { ok: false, reason: '형식 오류 (예: G5-04-01-07)' };
    var rack = parseInt(m[2], 10);
    var col  = parseInt(m[3], 10);
    var lv   = parseInt(m[4], 10);
    if (rack < 1 || rack > 16)   return { ok: false, reason: '랙은 01~16' };
    if (col  < 1 || col  > 31)   return { ok: false, reason: '열은 01~31' };
    var maxLv = _rackLevelMax[rack] || 0;
    if (lv < 1 || lv > maxLv)    return { ok: false, reason: '랙 ' + rack + '번 최대 ' + maxLv + '층' };
    return { ok: true };
  }

  window._case3ValidateLoc = function(inputId) {
    var inp = document.getElementById(inputId);
    if (!inp) return;
    inp.value = inp.value.toUpperCase();
    var msg = document.getElementById(inputId + '-msg');
    if (!inp.value) {
      if (msg) { msg.textContent = ''; }
      inp.style.borderColor = 'var(--border)';
      return;
    }
    var r = _validateLocClient(inp.value);
    if (r.ok) {
      inp.style.borderColor = '#4caf50';
      if (msg) { msg.textContent = '✓'; msg.style.color = '#4caf50'; }
    } else {
      inp.style.borderColor = '#f44336';
      if (msg) { msg.textContent = '✗ ' + r.reason; msg.style.color = '#f44336'; }
    }
  };

  window._case3OnModeChange = function(rowId, mode) {
    var box = document.querySelector('.case3-move-input[data-row="' + rowId + '"]');
    if (box) box.style.display = (mode === 'MOVE') ? 'flex' : 'none';
  };

  /* ── 본 처리 ── */
  var _state = { halfCells: [], onDone: null };

  function _currentCount() {
    var total = 0;
    _state.halfCells.forEach(function(c) { total += (c.remaining || []).length; });
    return total;
  }

  function _renderBody() {
    var body = document.getElementById('case3-body');
    var sm   = document.getElementById('case3-summary');
    sm.textContent = '— 잔여 ' + _currentCount() + '톤백 (' + _state.halfCells.length + '셀)';
    if (!_state.halfCells.length) {
      body.innerHTML = '<div style="text-align:center;color:var(--text-muted);padding:40px;">📭 처리할 잔여 톤백 없음</div>';
      return;
    }
    body.innerHTML = _state.halfCells.map(function(cell, ci) {
      return (cell.remaining || []).map(function(tb, ti) {
        return _renderRow(ci, cell, ti, tb);
      }).join('');
    }).join('');
  }

  function _applyAll() {
    var rows = document.querySelectorAll('.case3-row');
    var jobs = [];
    var errs = [];
    rows.forEach(function(rowEl) {
      var rowId = rowEl.id;
      var tonbagId = rowEl.getAttribute('data-tonbag-id');
      var fromLoc  = rowEl.getAttribute('data-from-loc');
      var mode = (document.querySelector('input[name="' + rowId + '-r"]:checked') || {}).value || 'STAY';
      var job = { tonbag_id: parseInt(tonbagId, 10), resolution: mode };
      if (mode === 'MOVE') {
        var inp = document.getElementById('case3-loc-' + rowId.replace('case3-row-', ''));
        var loc = inp ? String(inp.value || '').trim().toUpperCase() : '';
        var v   = _validateLocClient(loc);
        if (!v.ok) {
          errs.push('• 톤백 ' + tonbagId + ' (' + fromLoc + '): ' + v.reason);
          return;
        }
        if (loc === fromLoc) {
          errs.push('• 톤백 ' + tonbagId + ': 현재 위치(' + fromLoc + ')와 같음 — STAY 권장');
          return;
        }
        job.to_location = loc;
      }
      jobs.push({ job: job, rowEl: rowEl });
    });

    if (errs.length) {
      alert('⚠️ 입력 오류:\n\n' + errs.join('\n'));
      return;
    }
    if (!jobs.length) {
      _toast('info', '처리할 항목 없음');
      return;
    }

    var btn = document.getElementById('case3-apply');
    btn.disabled = true;
    btn.textContent = '⏳ 처리 중...';

    var done = 0, failed = 0;
    var resultMsgs = [];
    function _next(i) {
      if (i >= jobs.length) {
        btn.disabled = false;
        btn.textContent = '✅ 선택 적용';
        var msg = '처리 완료: 성공 ' + done + '건, 실패 ' + failed + '건';
        _toast(failed ? 'warning' : 'success', msg);
        if (resultMsgs.length) {
          console.info('[CASE3 결과]\n' + resultMsgs.join('\n'));
        }
        if (typeof _state.onDone === 'function') _state.onDone({ done: done, failed: failed });
        if (!failed) {
          setTimeout(function() {
            document.getElementById('sqm-case3-dialog').style.display = 'none';
          }, 700);
        }
        return;
      }
      var entry = jobs[i];
      fetch(_api() + '/api/warehouse/case3-resolve', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(entry.job),
      })
        .then(function(r) { return r.json(); })
        .then(function(res) {
          var ok = res && res.ok;
          var resDiv = entry.rowEl.querySelector('.case3-result');
          if (resDiv) {
            resDiv.style.display = 'block';
            if (ok) {
              resDiv.style.color = '#4caf50';
              resDiv.textContent = '✓ ' + (res.data && res.data.message || '처리 완료');
            } else {
              resDiv.style.color = '#f44336';
              resDiv.textContent = '✗ ' + (res.error || res.message || '실패');
            }
          }
          if (ok) { done++; } else { failed++; }
          resultMsgs.push('  tonbag=' + entry.job.tonbag_id + ' ' + entry.job.resolution
                          + ' → ' + (ok ? 'OK' : ('FAIL: ' + (res.error || ''))));
          _next(i + 1);
        })
        .catch(function(e) {
          failed++;
          resultMsgs.push('  tonbag=' + entry.job.tonbag_id + ' EXCEPTION: ' + e);
          _next(i + 1);
        });
    }
    _next(0);
  }

  /* ─────────────────────────────────────────────────────────────────────
     공개 함수: 출고 응답으로 받은 half_cells 즉시 처리
     ───────────────────────────────────────────────────────────────────── */
  window.showCase3Dialog = function(halfCells, onDone) {
    if (!halfCells || !halfCells.length) return;
    _state.halfCells = halfCells.slice();
    _state.onDone    = onDone || null;
    var d = _ensureModal();
    d.style.display = 'flex';
    _renderBody();
  };

  /* 공개 함수: 누적된 HALF 셀 전체 불러와서 처리 */
  window.showCase3Queue = function() {
    fetch(_api() + '/api/warehouse/half-cells')
      .then(function(r) { return r.json(); })
      .then(function(res) {
        var arr = (res && res.data && res.data.half_cells) || [];
        if (!arr.length) {
          _toast('success', '🎉 처리할 HALF 셀이 없습니다');
          return;
        }
        window.showCase3Dialog(arr);
      })
      .catch(function(e) {
        _toast('error', 'HALF 셀 조회 실패: ' + e);
      });
  };

})();
