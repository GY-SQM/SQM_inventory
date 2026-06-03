/* =======================================================================
   sqm-location-map-import.js  (v8.7.0)
   📥 위치재고조회 엑셀 import — 신형식 G{동}-{칸}-{열}-{층} [N]

   동작:
     1) 엑셀 업로드 → POST /api/location-map/preview (검증 + 직전 batch diff)
     2) 검증결과 / diff / 입고누락 경고 화면 표시
     3) [위치재고 스냅샷 저장] → POST /api/location-map/commit
        - 치명적 에러 → 차단
        - 입고 누락(신규 LOT 10개 미만) → '강제 저장' 체크 시 force=true

   호출: window.showLocationMapImportModal();
   ======================================================================= */
(function () {
  'use strict';
  if (window.__SQM_LOCMAP_IMPORT_INSTALLED__) return;
  window.__SQM_LOCMAP_IMPORT_INSTALLED__ = true;

  function _api()  { return (typeof API !== 'undefined') ? API : ''; }
  function _toast(t, m) { if (window.showToast) window.showToast(t, m); else alert(m); }
  function _esc(s) {
    if (window.escapeHtml) return window.escapeHtml(s);
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  var _state = { file: null, report: null, busy: false };
  var _modal = null;

  /* ── 모달 생성 ── */
  function _ensureModal() {
    if (_modal && document.body.contains(_modal)) {
      _modal.style.display = 'flex';
      return _modal;
    }
    var d = document.createElement('div');
    d.id = 'sqm-locmap-import-modal';
    d.style.cssText = ''
      + 'position:fixed;top:40px;left:50%;transform:translateX(-50%);'
      + 'width:min(1100px,96vw);height:86vh;background:var(--bg-card,#1e2a38);'
      + 'border:2px solid var(--accent,#4fc3f7);border-radius:10px;'
      + 'box-shadow:0 8px 40px rgba(0,0,0,.6);z-index:10075;'
      + 'display:flex;flex-direction:column;overflow:hidden;';
    d.innerHTML = ''
      + '<div id="lmi-hdr" style="cursor:move;background:linear-gradient(90deg,#1565c0,#4fc3f7);'
      +     'color:#fff;padding:10px 16px;display:flex;align-items:center;gap:10px;flex-shrink:0;">'
      + '  <span style="font-size:16px;font-weight:700;">📥 위치재고조회 엑셀 Import</span>'
      + '  <span style="font-size:11px;opacity:.9;">신형식 G{동}-{칸}-{열}-{층} [N]</span>'
      + '  <button id="lmi-close" style="margin-left:auto;background:none;border:none;'
      +     'font-size:18px;cursor:pointer;color:#fff;padding:0 4px;">×</button>'
      + '</div>'
      + '<div style="padding:12px 16px;border-bottom:1px solid var(--panel-border,#2c3e50);'
      +     'flex-shrink:0;display:flex;gap:10px;align-items:center;flex-wrap:wrap;">'
      + '  <button id="lmi-pick" class="btn btn-primary">📁 엑셀 파일 선택</button>'
      + '  <input type="file" id="lmi-file" accept=".xlsx,.xls" style="display:none;">'
      + '  <span id="lmi-fname" style="font-size:12px;color:var(--text-muted,#95a5a6);">'
      +     '선택된 파일 없음</span>'
      + '  <label style="margin-left:auto;font-size:11px;color:var(--text-muted,#95a5a6);'
      +     'display:none;align-items:center;gap:4px;" id="lmi-force-wrap">'
      + '    <input type="checkbox" id="lmi-force"> 입고 누락 무시하고 강제 저장'
      + '  </label>'
      + '  <button id="lmi-rollback" class="btn" '
      +     'style="background:#c0392b;color:#fff;" '
      +     'title="최신 import batch 삭제 + (선택) 톤백 위치 초기화">🗑️ 최신 배치 롤백</button>'
      + '  <button id="lmi-commit" class="btn" disabled '
      +     'style="background:#27ae60;color:#fff;">💾 위치 후보 저장</button>'
      + '</div>'
      + '<div id="lmi-body" style="flex:1;overflow:auto;padding:14px 16px;">'
      + '  <div style="color:var(--text-muted,#95a5a6);text-align:center;padding:40px;">'
      + '    엑셀 파일을 선택하면 검증 결과와 직전 import 대비 변경점(diff)을 보여줍니다.<br>'
      + '    톤백별 위치는 출고 바코드 스캔 시점에 확정됩니다.'
      + '  </div>'
      + '</div>';
    document.body.appendChild(d);
    _modal = d;

    document.getElementById('lmi-close').onclick = function () {
      d.style.display = 'none';
    };
    document.getElementById('lmi-pick').onclick = function () {
      document.getElementById('lmi-file').click();
    };
    document.getElementById('lmi-file').onchange = function (ev) {
      var f = ev.target.files && ev.target.files[0];
      if (f) _doPreview(f);
    };
    document.getElementById('lmi-commit').onclick = _doCommit;
    document.getElementById('lmi-rollback').onclick = _doRollback;

    if (typeof window._makeDraggableResizable === 'function') {
      window._makeDraggableResizable(d, document.getElementById('lmi-hdr'));
    }
    /* v8.7.1: 🪟 별도 OS 창 분리 버튼 */
    if (typeof window.sqmAddPopOutBtn === 'function') {
      window.sqmAddPopOutBtn(d, document.getElementById('lmi-hdr'), {
        key: 'location-map-import',
        title: '📥 위치재고 엑셀 임포트',
        width: 1100, height: 780,
      });
    }
    return d;
  }

  /* ── preview 요청 ── */
  function _doPreview(file) {
    if (_state.busy) return;
    _state.busy = true;
    _state.file = file;
    _state.report = null;
    document.getElementById('lmi-fname').textContent = file.name;
    document.getElementById('lmi-commit').disabled = true;
    document.getElementById('lmi-force-wrap').style.display = 'none';
    document.getElementById('lmi-body').innerHTML =
      '<div style="text-align:center;padding:40px;color:var(--text-muted,#95a5a6);">⏳ 분석 중...</div>';

    var fd = new FormData();
    fd.append('file', file);
    fetch(_api() + '/api/location-map/preview', { method: 'POST', body: fd })
      .then(function (r) { return r.json(); })
      .then(function (res) {
        _state.busy = false;
        if (!res || !res.ok) {
          document.getElementById('lmi-body').innerHTML = _apiErrorHtml(res, '미리보기 실패');
          return;
        }
        _state.report = res.data;
        _renderReport(res.data);
      })
      .catch(function (e) {
        _state.busy = false;
        document.getElementById('lmi-body').innerHTML =
          _box('rgba(244,67,54,.10)', '#f44336',
            '<div style="color:#ff8a80;font-weight:700;margin-bottom:8px;">❌ 서버 연결 실패</div>'
            + '<div><b>원인</b><ul style="margin:6px 0 0 18px;padding:0;">'
            + '<li>백엔드 서버가 실행 중이 아니거나 일시적으로 응답하지 않습니다.</li>'
            + '<li>파일 업로드 중 연결이 끊겼을 수 있습니다.</li>'
            + '</ul></div>'
            + '<div style="margin-top:10px;"><b>해결 방법</b><ul style="margin:6px 0 0 18px;padding:0;">'
            + '<li>프로그램을 새로고침하거나 재실행한 뒤 다시 업로드하세요.</li>'
            + '<li>문제가 반복되면 아래 메시지를 관리자에게 전달하세요.</li>'
            + '</ul></div>'
            + '<pre style="white-space:pre-wrap;font-size:11px;margin-top:10px;">' + _esc(e.message) + '</pre>');
      });
  }

  /* ── 리포트 렌더 ── */
  function _sectionTitle(t) {
    return '<div style="font-size:13px;font-weight:700;margin:14px 0 6px;'
      + 'color:var(--fg,#ecf0f1);">' + t + '</div>';
  }
  function _box(bg, border, html) {
    return '<div style="background:' + bg + ';border:1px solid ' + border + ';'
      + 'border-radius:6px;padding:8px 12px;font-size:12px;line-height:1.7;">' + html + '</div>';
  }
  function _list(items) {
    items = items || [];
    if (!items.length) return '';
    return '<ul style="margin:6px 0 0 18px;padding:0;">'
      + items.map(function (x) { return '<li>' + _esc(x) + '</li>'; }).join('')
      + '</ul>';
  }
  function _apiErrorHtml(res, fallback) {
    var d = (res && res.detail) || {};
    var html = '<div style="color:#ff8a80;font-weight:700;margin-bottom:8px;">❌ '
      + _esc((res && res.error) || fallback || '요청 실패') + '</div>';
    if (d.causes && d.causes.length) {
      html += '<div style="margin-top:8px;"><b>원인</b>' + _list(d.causes) + '</div>';
    }
    if (d.actions && d.actions.length) {
      html += '<div style="margin-top:10px;"><b>해결 방법</b>' + _list(d.actions) + '</div>';
    }
    if (d.details && d.details.length) {
      html += '<details style="margin-top:10px;"><summary style="cursor:pointer;color:var(--text-muted,#95a5a6);">상세 오류 '
        + d.details.length + '건</summary><pre style="white-space:pre-wrap;font-size:11px;max-height:180px;overflow:auto;margin-top:6px;">'
        + _esc(d.details.join('\n')) + '</pre></details>';
    }
    if (res && res.data && res.data.errors && res.data.errors.length) {
      html += '<details style="margin-top:10px;"><summary style="cursor:pointer;color:#ffab91;">검증 오류 '
        + res.data.errors.length + '건</summary><pre style="white-space:pre-wrap;font-size:11px;max-height:180px;overflow:auto;margin-top:6px;">'
        + _esc(res.data.errors.slice(0, 80).join('\n')) + '</pre></details>';
    }
    if (res && res.data && res.data.inbound_short && res.data.inbound_short.length) {
      html += '<details style="margin-top:10px;"><summary style="cursor:pointer;color:#ffcc80;">입고 누락 의심 '
        + res.data.inbound_short.length + '건</summary><pre style="white-space:pre-wrap;font-size:11px;max-height:180px;overflow:auto;margin-top:6px;">'
        + _esc(JSON.stringify(res.data.inbound_short.slice(0, 30), null, 2)) + '</pre></details>';
    }
    return _box('rgba(244,67,54,.10)', '#f44336', html);
  }

  function _renderReport(rep) {
    var st = rep.stats || {};
    var h = '';

    // 요약
    h += _sectionTitle('📊 요약');
    h += _box('rgba(33,150,243,.08)', '#2980b9',
      'LOT <b>' + (st.total_lots || 0) + '</b>개 · '
      + '셀 <b>' + (st.total_cells || 0) + '</b>개 · '
      + '톤백 <b>' + (st.total_tonbags || 0) + '</b>개 · '
      + '파일: ' + _esc(rep.source_file || ''));

    // 치명적 에러
    var errs = rep.errors || [];
    if (errs.length) {
      h += _sectionTitle('❌ 치명적 에러 — ' + errs.length + '건 (저장 불가)');
      h += _box('rgba(244,67,54,.1)', '#f44336',
        errs.map(function (e) { return '• ' + _esc(e); }).join('<br>'));
    }

    // 입고 누락
    var shorts = rep.inbound_short || [];
    if (shorts.length) {
      h += _sectionTitle('⚠️ 입고 누락 의심 — ' + shorts.length
        + '건 (신규 LOT인데 톤백 10개 미만 = 바코드 스캔 누락 가능)');
      var sh = shorts.map(function (s) {
        var mc = (s.missing_cells || []).map(function (m) {
          return '<b style="color:#ffb74d;">' + _esc(m.location) + '</b>('
            + m.tonbag_count + '개, ' + m.shortage + '개 부족)';
        }).join(', ');
        return '• LOT <b>' + _esc(s.lot_no) + '</b> (행 ' + s.row_num + '): 톤백 '
          + s.tonbag_sum + '/' + s.expected + ' → 누락 셀: ' + (mc || '-')
          + '<br>&nbsp;&nbsp;→ 현장에서 누락 바코드를 확인·스캔하세요.';
      }).join('<br>');
      h += _box('rgba(255,152,0,.1)', '#ff9800', sh);
    }

    // diff
    var df = rep.diff || {};
    h += _sectionTitle('🔁 직전 import 대비 변경점'
      + (df.prev_batch_id ? ' (batch #' + df.prev_batch_id + ' 기준)' : ' (최초 import)'));
    var diffRows = ''
      + '신규 LOT <b style="color:#4caf50;">' + (df.new_lots || []).length + '</b> · '
      + '삭제 <b style="color:#f44336;">' + (df.removed_lots || []).length + '</b> · '
      + '위치변경 <b style="color:#ff9800;">' + (df.location_changed || []).length + '</b> · '
      + '수량변경 <b style="color:#ffb74d;">' + (df.count_changed || []).length + '</b> · '
      + '동일 <b>' + (df.unchanged_count || 0) + '</b>';
    if ((df.removed_lots || []).length) {
      diffRows += '<br><span style="color:#ef9a9a;">삭제: '
        + df.removed_lots.map(_esc).join(', ') + '</span>';
    }
    if ((df.location_changed || []).length) {
      diffRows += '<br><span style="color:#ffcc80;">위치변경: '
        + df.location_changed.map(function (c) { return _esc(c.lot_no); }).join(', ') + '</span>';
    }
    if ((df.count_changed || []).length) {
      diffRows += '<br><span style="color:#ffe0b2;">수량변경(출고 등): '
        + df.count_changed.map(function (c) { return _esc(c.lot_no); }).join(', ') + '</span>';
    }
    h += _box('rgba(255,255,255,.04)', 'var(--panel-border,#2c3e50)', diffRows);

    // 비치명 경고
    var warns = rep.warnings || [];
    if (warns.length) {
      h += _sectionTitle('ℹ️ 경고 — ' + warns.length + '건');
      h += _box('rgba(255,193,7,.07)', '#ffc107',
        warns.slice(0, 30).map(function (w) { return '• ' + _esc(w); }).join('<br>')
        + (warns.length > 30 ? '<br>... (+' + (warns.length - 30) + '건)' : ''));
    }

    // 결론
    h += '<div style="margin-top:14px;padding:8px 12px;border-radius:6px;font-size:12px;'
      + (rep.can_commit
          ? 'background:rgba(76,175,80,.12);border:1px solid #4caf50;color:#a5d6a7;'
          : 'background:rgba(244,67,54,.12);border:1px solid #f44336;color:#ef9a9a;') + '">'
      + (rep.can_commit
          ? '✅ 검증 통과 — LOT 위치 후보 저장 가능'
            + (rep.has_inbound_short
                ? ' (단, 입고 누락 의심 건이 있어 강제 저장 체크 필요)' : '')
          : '❌ 치명적 에러로 저장 불가 — 엑셀을 수정 후 다시 업로드하세요')
      + '<div style="margin-top:4px;color:var(--text-muted,#95a5a6);">'
      + '이 저장은 LOT 단위 위치 스냅샷입니다. inventory_tonbag의 톤백별 실제 위치는 변경하지 않습니다.'
      + '</div>'
      + '</div>';

    document.getElementById('lmi-body').innerHTML = h;

    // commit 버튼 / force 토글
    var commitBtn = document.getElementById('lmi-commit');
    var forceWrap = document.getElementById('lmi-force-wrap');
    commitBtn.disabled = !rep.can_commit;
    forceWrap.style.display = (rep.can_commit && rep.has_inbound_short) ? 'flex' : 'none';
    document.getElementById('lmi-force').checked = false;
  }

  /* ── commit 요청 ── */
  function _doCommit() {
    if (_state.busy || !_state.file || !_state.report) return;
    var rep = _state.report;
    var force = document.getElementById('lmi-force').checked;
    if (rep.has_inbound_short && !force) {
      _toast('warning', '입고 누락 의심 건이 있습니다 — 현장 확인 후 "강제 저장"을 체크하거나 엑셀을 수정하세요');
      return;
    }
    if (!window.sqmConfirm('이 엑셀을 LOT 위치 후보 스냅샷으로 저장합니다.\n\n톤백별 실제 위치는 변경하지 않고, 출고 바코드 스캔 시점에 확정됩니다. 계속할까요?')) {
      return;
    }
    _state.busy = true;
    var btn = document.getElementById('lmi-commit');
    btn.disabled = true;
    btn.textContent = '⏳ 저장 중...';

    var fd = new FormData();
    fd.append('file', _state.file);
    var url = _api() + '/api/location-map/commit' + (force ? '?force=true' : '');
    fetch(url, { method: 'POST', body: fd })
      .then(function (r) { return r.json(); })
      .then(function (res) {
        _state.busy = false;
        btn.textContent = '💾 위치 후보 저장';
        if (res && res.ok) {
          var d = res.data || {};
          _toast('success', (res.message || '위치 후보 저장 완료')
            + ' (batch #' + d.batch_id + ', ' + d.committed_rows + '행)');
          btn.disabled = true;
        } else {
          btn.disabled = false;
          var code = res && res.error_code;
          _toast(code === 'INBOUND_SHORT' ? 'warning' : 'error',
            (res && res.error) || '저장 실패');
          document.getElementById('lmi-body').innerHTML = _apiErrorHtml(res, '저장 실패');
        }
      })
      .catch(function (e) {
        _state.busy = false;
        btn.disabled = false;
        btn.textContent = '💾 위치 후보 저장';
        _toast('error', '요청 실패: ' + e.message);
        document.getElementById('lmi-body').innerHTML =
          _box('rgba(244,67,54,.10)', '#f44336',
            '<div style="color:#ff8a80;font-weight:700;margin-bottom:8px;">❌ 저장 요청 실패</div>'
            + '<div><b>해결 방법</b><ul style="margin:6px 0 0 18px;padding:0;">'
            + '<li>프로그램을 새로고침한 뒤 다시 저장하세요.</li>'
            + '<li>백엔드 서버가 실행 중인지 확인하세요.</li>'
            + '<li>반복되면 아래 메시지를 관리자에게 전달하세요.</li>'
            + '</ul></div>'
            + '<pre style="white-space:pre-wrap;font-size:11px;margin-top:10px;">' + _esc(e.message) + '</pre>');
      });
  }

  /* ── 롤백: 최신 batch 삭제 + (선택) 톤백 위치 초기화 ── */
  function _doRollback() {
    if (_state.busy) return;
    // ① 최신 batch 정보 조회
    fetch(_api() + '/api/location-map/latest')
      .then(function (r) { return r.json(); })
      .then(function (res) {
        if (!res || !res.ok) {
          _toast('error', '배치 정보 조회 실패: ' + (res && res.error || '알 수 없음'));
          return;
        }
        var d = res.data || {};
        var batchId = d.batch_id;
        if (!batchId) {
          _toast('warning', '삭제할 import 배치가 없습니다');
          return;
        }
        var lotCount = d.count || 0;
        var msg = '⚠️ 최신 배치 #' + batchId + ' 를 삭제합니다.\n'
          + 'LOT ' + lotCount + '개의 위치 후보(매핑 데이터)가 제거됩니다.\n\n'
          + '계속할까요?';
        if (!window.sqmConfirm(msg)) return;
        // ② batch 삭제 API 호출
        _state.busy = true;
        fetch(_api() + '/api/location-map/batch/' + batchId, { method: 'DELETE' })
          .then(function (r) { return r.json(); })
          .then(function (res2) {
            _state.busy = false;
            if (!res2 || !res2.ok) {
              _toast('error', '배치 삭제 실패: ' + (res2 && res2.error || '알 수 없음'));
              return;
            }
            var d2 = res2.data || {};
            var lotNos = d2.lot_nos || [];
            _toast('success', d2.message || '배치 삭제 완료');
            // ③ 위치 초기화(B) 여부 추가 확인
            if (lotNos.length > 0) {
              var msg2 = '배치가 삭제되었습니다.\n\n'
                + '추가로 해당 LOT ' + lotNos.length + '개의\n'
                + '톤백 실제 위치(inventory_tonbag.location)도\n'
                + '초기화(NULL)할까요?\n\n'
                + '※ 위치 후보만 지우고 실제 위치는 유지하려면 [취소]';
              if (window.sqmConfirm(msg2)) {
                fetch(_api() + '/api/inventory/clear-lot-locations', {
                  method: 'POST',
                  headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ lot_nos: lotNos }),
                })
                  .then(function (r) { return r.json(); })
                  .then(function (res3) {
                    if (res3 && res3.ok) {
                      _toast('success', '위치 초기화 완료 — 톤백 ' + (res3.tonbag_cleared || 0) + '개');
                    } else {
                      _toast('error', '위치 초기화 실패: ' + (res3 && res3.error || '알 수 없음'));
                    }
                  })
                  .catch(function (e) { _toast('error', '위치 초기화 요청 실패: ' + e.message); });
              }
            }
            // 모달 body 초기화
            document.getElementById('lmi-body').innerHTML =
              '<div style="text-align:center;padding:40px;color:#a5d6a7;">'
              + '✅ 배치 #' + batchId + ' 삭제 완료 — 새 엑셀을 다시 업로드하세요.</div>';
            document.getElementById('lmi-commit').disabled = true;
            document.getElementById('lmi-force-wrap').style.display = 'none';
            _state.report = null;
          })
          .catch(function (e) {
            _state.busy = false;
            _toast('error', '배치 삭제 요청 실패: ' + e.message);
          });
      })
      .catch(function (e) { _toast('error', '배치 정보 조회 실패: ' + e.message); });
  }

  /* 공개 함수 */
  window.showLocationMapImportModal = function () {
    _ensureModal();
  };

})();
