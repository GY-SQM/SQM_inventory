/* sqm-status-revert.js — scoped status revert center */
(function statusRevertModule() {
  'use strict';
  if (window.__SQM_STATUS_REVERT__) return;
  window.__SQM_STATUS_REVERT__ = true;

  var STATUS_CONFIG = {
    available:  { from: 'AVAILABLE', to: 'PENDING',  title: 'Available',  danger: false },
    allocation: { from: 'RESERVED',  to: 'AVAILABLE', title: 'Allocation', danger: false },
    picked:     { from: 'PICKED',    to: 'RESERVED', title: 'Picked',     danger: false },
    outbound:   { from: 'SOLD',      to: 'PICKED',   title: 'Sold',       danger: true  },
    return:     { from: 'RETURN',    to: 'AVAILABLE', title: 'Return',    danger: false }
  };

  var EXTRA_SCOPES = {
    RESERVED: ['sale_ref', 'customer'],
    PICKED: ['sale_ref', 'customer', 'picking_no'],
    SOLD: ['sale_ref', 'customer', 'picking_no', 'outbound_date'],
    RETURN: ['customer', 'return_reason']
  };

  var SCOPE_LABEL = {
    container_no: '컨테이너 기준',
    bl_no: 'B/L 기준',
    lot_nos: 'LOT 기준',
    inbound_date: '입고일 기준',
    sale_ref: 'SALE REF 기준',
    customer: '고객사 기준',
    picking_no: '피킹번호 기준',
    outbound_date: '출고일 기준',
    return_reason: '반품 사유 기준',
    selected_lots: '현재 선택 LOT',
    current_filter: '현재 필터 결과',
    all_status: '전체 상태'
  };

  function esc(v) {
    if (window.escapeHtml) return window.escapeHtml(v == null ? '' : String(v));
    return String(v == null ? '' : v).replace(/[&<>"']/g, function(c) {
      return ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'})[c];
    });
  }

  function toast(type, msg) {
    if (window.showToast) window.showToast(type, msg);
    else alert(msg);
  }

  function post(path, body) {
    if (!window.apiPost) return Promise.reject(new Error('apiPost 없음'));
    return window.apiPost(path, body || {});
  }

  function get(path) {
    if (!window.apiGet) return Promise.reject(new Error('apiGet 없음'));
    return window.apiGet(path);
  }

  function currentRoute() {
    return window.getCurrentRoute ? window.getCurrentRoute() : '';
  }

  function configForRoute(route) {
    return STATUS_CONFIG[route || currentRoute()] || null;
  }

  function configForStatus(fromStatus) {
    var from = String(fromStatus || '').toUpperCase();
    var keys = Object.keys(STATUS_CONFIG);
    for (var i = 0; i < keys.length; i++) {
      if (STATUS_CONFIG[keys[i]].from === from) return STATUS_CONFIG[keys[i]];
    }
    return null;
  }

  function selectedLots(route) {
    var lots = [];
    if (route === 'available') {
      lots = Array.from(document.querySelectorAll('.avail-cb:checked')).map(function(cb) { return cb.dataset.lot; });
    } else if (route === 'allocation' && window._allocState && window._allocState.selectedLots) {
      lots = Array.from(window._allocState.selectedLots);
    } else {
      lots = Array.from(document.querySelectorAll('[data-lot].selected,[data-lot][aria-selected="true"]')).map(function(el) {
        return el.dataset.lot;
      });
    }
    return Array.from(new Set(lots.filter(Boolean)));
  }

  function routeFromStatus(from) {
    if (from === 'AVAILABLE') return 'available';
    if (from === 'RESERVED') return 'allocation';
    if (from === 'PICKED') return 'picked';
    if (from === 'SOLD') return 'outbound';
    if (from === 'RETURN') return 'return';
    return currentRoute();
  }

  function buildScopeList(cfg) {
    var scopes = ['container_no', 'bl_no', 'lot_nos', 'inbound_date'];
    (EXTRA_SCOPES[cfg.from] || []).forEach(function(s) {
      if (scopes.indexOf(s) < 0) scopes.push(s);
    });
    scopes.push('selected_lots');
    scopes.push('current_filter');
    scopes.push('all_status');
    return scopes;
  }

  function optionTags(values) {
    return (values || []).map(function(v) {
      return '<option value="' + esc(v) + '">' + esc(v) + '</option>';
    }).join('');
  }

  function readModalPayload(cfg, route) {
    var scope = (document.querySelector('input[name="sr-scope"]:checked') || {}).value || '';
    var value = '';
    var filters = {};

    if (scope === 'lot_nos') {
      value = (document.getElementById('sr-lot-text') || {}).value || '';
    } else if (scope === 'selected_lots') {
      value = selectedLots(route);
    } else if (scope !== 'current_filter' && scope !== 'all_status') {
      value = (document.getElementById('sr-value-' + scope) || {}).value || '';
    }

    Array.from(document.querySelectorAll('.sr-filter')).forEach(function(el) {
      if (el.value) filters[el.dataset.key] = el.value;
    });

    return {
      from_status: cfg.from,
      to_status: cfg.to,
      scope_type: scope,
      scope_value: value,
      filters: filters,
      actor: 'ui'
    };
  }

  function formatPreview(res) {
    var lots = res.lots || [];
    var blocked = res.blocked || [];
    var html = '<div style="font-weight:800;margin-bottom:6px;color:var(--text)">대상 미리보기</div>'
      + '<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:8px">'
      + '<span>LOT <strong>' + (res.target_lot_count || 0) + '</strong>개</span>'
      + '<span>톤백 <strong>' + (res.target_tonbag_count || 0) + '</strong>개</span>'
      + '<span>중량 <strong>' + Number(res.target_weight_mt || 0).toFixed(4) + '</strong> MT</span>'
      + '</div>';
    if (lots.length) {
      html += '<div style="font-size:12px;color:var(--text-muted);line-height:1.5">LOT: '
        + esc(lots.slice(0, 12).join(', '))
        + (lots.length > 12 ? ' ... 외 ' + (lots.length - 12) + '개' : '')
        + '</div>';
    }
    if (blocked.length) {
      html += '<div style="margin-top:8px;color:#ef4444;font-size:12px">차단: '
        + esc(blocked.slice(0, 5).map(function(b) { return b.lot_no + ' ' + b.status + ' ' + b.count + '건'; }).join(', '))
        + '</div>';
    }
    return html;
  }

  function renderModal(cfg, route, options, preset) {
    var old = document.getElementById('status-revert-overlay');
    if (old) old.remove();
    var scopes = buildScopeList(cfg);
    var opts = (options && options.options) || {};
    var selected = (preset && preset.scope_type) || (preset && preset.lot ? 'lot_nos' : 'container_no');
    var selectedLotText = preset && preset.lot ? preset.lot : '';

    var scopeHtml = scopes.map(function(scope) {
      var checked = scope === selected ? ' checked' : '';
      var input = '';
      if (scope === 'lot_nos') {
        input = '<textarea id="sr-lot-text" rows="3" placeholder="LOT 번호를 쉼표 또는 줄바꿈으로 입력" style="display:none;width:100%;margin-top:6px;padding:8px;background:var(--bg,#0f172a);color:var(--text);border:1px solid var(--border,#334155);border-radius:6px">' + esc(selectedLotText) + '</textarea>';
      } else if (scope !== 'selected_lots' && scope !== 'current_filter' && scope !== 'all_status') {
        input = '<select id="sr-value-' + scope + '" style="display:none;width:100%;margin-top:6px;padding:8px;background:var(--bg,#0f172a);color:var(--text);border:1px solid var(--border,#334155);border-radius:6px">'
          + '<option value="">선택</option>' + optionTags(opts[scope] || []) + '</select>';
      }
      return '<label class="sr-scope-row" style="display:block;padding:8px 10px;border:1px solid var(--border,#334155);border-radius:6px;margin-bottom:6px;cursor:pointer">'
        + '<input type="radio" name="sr-scope" value="' + scope + '"' + checked + '> '
        + '<strong>' + esc(SCOPE_LABEL[scope] || scope) + '</strong>'
        + input
        + '</label>';
    }).join('');

    var filterScopes = ['container_no', 'bl_no', 'inbound_date', 'sale_ref', 'customer', 'picking_no', 'outbound_date', 'return_reason'];
    var filterHtml = filterScopes.filter(function(s) { return (opts[s] || []).length; }).map(function(s) {
      return '<label style="display:flex;align-items:center;gap:6px;font-size:12px">'
        + '<span style="min-width:70px;color:var(--text-muted)">' + esc((SCOPE_LABEL[s] || s).replace(' 기준', '')) + '</span>'
        + '<select class="sr-filter" data-key="' + s + '" style="flex:1;padding:6px;background:var(--bg,#0f172a);color:var(--text);border:1px solid var(--border,#334155);border-radius:6px">'
        + '<option value="">보조 필터 없음</option>' + optionTags(opts[s] || []) + '</select>'
        + '</label>';
    }).join('');

    var ov = document.createElement('div');
    ov.id = 'status-revert-overlay';
    ov.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,.64);z-index:10020;display:flex;align-items:center;justify-content:center;padding:20px';
    ov.innerHTML = ''
      + '<div style="width:min(760px,96vw);max-height:90vh;overflow:auto;background:var(--surface,#1e293b);border:1px solid var(--border,#334155);border-radius:10px;box-shadow:0 20px 50px rgba(0,0,0,.45)">'
      + '<div style="display:flex;align-items:center;justify-content:space-between;padding:14px 16px;border-bottom:1px solid var(--border,#334155)">'
      + '<div><h2 style="margin:0;font-size:18px">이전 상태로 되돌리기</h2>'
      + '<div style="margin-top:4px;color:var(--text-muted);font-size:13px">' + esc(cfg.title) + ' · <strong>' + cfg.from + ' → ' + cfg.to + '</strong></div></div>'
      + '<button class="btn btn-ghost" id="sr-close" style="font-size:18px">×</button>'
      + '</div>'
      + '<div style="padding:16px;display:grid;grid-template-columns:minmax(260px,1fr) minmax(260px,1fr);gap:14px">'
      + '<div><div style="font-weight:800;margin-bottom:8px">대상 기준 선택</div>' + scopeHtml + '</div>'
      + '<div><div style="font-weight:800;margin-bottom:8px">보조 필터</div>'
      + (filterHtml || '<div style="color:var(--text-muted);font-size:13px">사용 가능한 보조 필터가 없습니다.</div>')
      + '<div id="sr-preview" style="margin-top:14px;padding:12px;border:1px dashed var(--border,#334155);border-radius:8px;color:var(--text-muted);font-size:13px">미리보기를 먼저 실행하세요.</div>'
      + (cfg.danger ? '<div style="margin-top:10px;color:#ef4444;font-size:12px">SOLD 되돌리기는 출고 이력에 영향을 줍니다. 실행 전 미리보기 확인이 필수입니다.</div>' : '')
      + '</div></div>'
      + '<div style="display:flex;gap:8px;justify-content:flex-end;padding:14px 16px;border-top:1px solid var(--border,#334155)">'
      + '<button class="btn btn-ghost" id="sr-cancel">취소</button>'
      + '<button class="btn btn-secondary" id="sr-preview-btn">미리보기</button>'
      + '<button class="btn btn-primary" id="sr-execute-btn" disabled>' + esc(cfg.to) + '로 되돌리기</button>'
      + '</div></div>';
    document.body.appendChild(ov);

    function syncInputs() {
      var val = (document.querySelector('input[name="sr-scope"]:checked') || {}).value;
      Array.from(ov.querySelectorAll('select[id^="sr-value-"], textarea[id^="sr-lot"]')).forEach(function(el) { el.style.display = 'none'; });
      var target = val === 'lot_nos' ? document.getElementById('sr-lot-text') : document.getElementById('sr-value-' + val);
      if (target) target.style.display = 'block';
      document.getElementById('sr-execute-btn').disabled = true;
      document.getElementById('sr-preview').innerHTML = '미리보기를 먼저 실행하세요.';
    }
    Array.from(ov.querySelectorAll('input[name="sr-scope"]')).forEach(function(r) { r.addEventListener('change', syncInputs); });
    syncInputs();

    document.getElementById('sr-close').onclick = function() { ov.remove(); };
    document.getElementById('sr-cancel').onclick = function() { ov.remove(); };
    ov.addEventListener('click', function(e) { if (e.target === ov) ov.remove(); });

    var lastPayload = null;
    document.getElementById('sr-preview-btn').onclick = function() {
      var payload = readModalPayload(cfg, route);
      if (payload.scope_type === 'selected_lots' && !(payload.scope_value || []).length) {
        toast('warning', '선택된 LOT가 없습니다');
        return;
      }
      lastPayload = payload;
      post('/api/status-revert/preview', payload).then(function(res) {
        document.getElementById('sr-preview').innerHTML = formatPreview(res);
        document.getElementById('sr-execute-btn').disabled = !!((res.blocked || []).length) || !(res.lots || []).length;
      }).catch(function(e) {
        document.getElementById('sr-preview').innerHTML = '<span style="color:#ef4444">미리보기 실패: ' + esc(e.message || e) + '</span>';
      });
    };

    document.getElementById('sr-execute-btn').onclick = function() {
      if (!lastPayload) return;
      var msg = cfg.from + ' → ' + cfg.to + ' 되돌리기를 실행합니다.\n미리보기 대상만 반영됩니다. 계속하시겠습니까?';
      if (!window.sqmConfirm ? !confirm(msg) : !window.sqmConfirm(msg)) return;
      post('/api/status-revert/execute', lastPayload).then(function(res) {
        toast(res.ok === false ? 'warning' : 'success', res.message || '되돌리기 완료');
        ov.remove();
        refreshRoute(route);
      }).catch(function(e) {
        toast('error', '되돌리기 실패: ' + (e.message || e));
      });
    };
  }

  function openModalByConfig(cfg, preset) {
    if (!cfg) {
      toast('warning', '현재 화면에는 되돌리기 단계가 없습니다');
      return;
    }
    var route = routeFromStatus(cfg.from);
    get('/api/status-revert/options?from_status=' + encodeURIComponent(cfg.from)).then(function(options) {
      renderModal(cfg, route, options, preset || {});
    }).catch(function() {
      renderModal(cfg, route, {options:{}}, preset || {});
    });
  }

  function refreshRoute(route) {
    if (route === 'available' && window.loadAvailablePage) window.loadAvailablePage();
    else if (route === 'allocation' && window.loadAllocationPage) window.loadAllocationPage();
    else if (route === 'picked' && window.loadPickedPage) window.loadPickedPage();
    else if (route === 'outbound' && window.loadOutboundPage) window.loadOutboundPage();
    else if (route === 'return' && window.loadReturnPage) window.loadReturnPage();
    else if (window.renderPage) window.renderPage(route || currentRoute());
    setTimeout(injectPanel, 250);
  }

  function injectPanel() {
    var route = currentRoute();
    if (route === 'outbound' || route === 'available' || route === 'allocation' || route === 'picked') return;
    var cfg = configForRoute(route);
    var c = document.getElementById('page-container');
    if (!cfg || !c) return;
    if (document.getElementById('status-revert-panel')) return;
    var anchor = c.querySelector('section') || c.firstElementChild || c;
    var panel = document.createElement('div');
    panel.id = 'status-revert-panel';
    panel.style.cssText = 'display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin:0 0 8px 0;padding:8px 12px;background:var(--surface,#1e293b);border:1px solid var(--border,#334155);border-radius:8px';
    panel.innerHTML = '<strong style="font-size:13px">이전 상태</strong>'
      + '<span style="font-size:12px;color:var(--text-muted)">' + cfg.from + ' → ' + cfg.to + '</span>'
      + '<button class="btn" style="font-size:12px;padding:4px 10px;background:rgba(239,68,68,.15);color:#ef4444;border:1px solid #ef444455">범위 선택 후 되돌리기</button>'
      + '<span style="font-size:11px;color:var(--text-muted)">B/L · 컨테이너 · LOT · 입고일 중 선택</span>';
    panel.querySelector('button').onclick = function() { openModalByConfig(cfg); };
    if (anchor === c) c.insertBefore(panel, c.firstChild);
    else anchor.insertBefore(panel, anchor.firstChild);
  }

  function wrapLoader(name) {
    var original = window[name];
    if (typeof original !== 'function' || original.__srWrapped) return;
    var wrapped = function() {
      var ret = original.apply(this, arguments);
      setTimeout(injectPanel, 250);
      setTimeout(injectPanel, 800);
      return ret;
    };
    wrapped.__srWrapped = true;
    window[name] = wrapped;
  }

  window.openStatusRevertModal = function(fromStatus, preset) {
    openModalByConfig(configForStatus(fromStatus), preset || {});
  };

  window.allocRevertStep = function(fromStatus, preset) {
    window.openStatusRevertModal(fromStatus, preset || {});
  };

  window.revertToPending = function(lot) {
    window.openStatusRevertModal('AVAILABLE', { scope_type: 'lot_nos', lot: lot || '' });
  };

  window.availCancelSelected = function() {
    window.openStatusRevertModal('AVAILABLE', { scope_type: 'selected_lots' });
  };

  ['loadAvailablePage', 'loadAllocationPage', 'loadPickedPage', 'loadOutboundPage', 'loadReturnPage'].forEach(wrapLoader);
  document.addEventListener('click', function() { setTimeout(injectPanel, 120); }, true);
  document.addEventListener('DOMContentLoaded', function() {
    setTimeout(injectPanel, 500);
    setTimeout(function() {
      ['loadAvailablePage', 'loadAllocationPage', 'loadPickedPage', 'loadOutboundPage', 'loadReturnPage'].forEach(wrapLoader);
    }, 500);
  });
  setTimeout(injectPanel, 600);
})();
