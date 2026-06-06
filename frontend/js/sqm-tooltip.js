/* =======================================================================
   SQM Inventory - sqm-tooltip.js
   Extracted from sqm-inline.js (Phase B-S1) — 2026-05-23
   Original: 2026-04-21 Ruby
   Source: sqm-inline.js line 11-142 (Custom Dark Tooltip System)
   ======================================================================= */
(function () {
  'use strict';
  if (window.__SQM_TOOLTIP_INSTALLED__) return;
  window.__SQM_TOOLTIP_INSTALLED__ = true;

  /* ===================================================
     CUSTOM TOOLTIP SYSTEM (SQM Dark Theme)
     title= 속성을 모두 data-sqm-tip= 으로 전환,
     OS 기본 툴팁 대신 커스텀 다크 스타일 툴팁 표시
     =================================================== */
  (function initSqmTooltip() {
    // ── 툴팁 DOM 요소 생성 ──
    var _tip = document.createElement('div');
    _tip.id = 'sqm-tooltip';
    _tip.style.cssText = [
      'position:fixed',
      'z-index:999999',
      'display:none',
      'max-width:320px',
      'padding:7px 12px',
      'background:linear-gradient(135deg,#0d1b2a 0%,#0a1628 100%)',
      'color:#c9e8f8',
      'border:1px solid #1e4a7a',
      'border-radius:7px',
      'font-size:12px',
      'font-family:"Malgun Gothic","\ub9d1\uc740 \uace0\ub515",Segoe UI,sans-serif',
      'line-height:1.5',
      'pointer-events:none',
      'box-shadow:0 4px 18px rgba(0,0,0,0.7),0 0 0 1px rgba(79,195,247,0.08)',
      'white-space:pre-wrap',
      'word-break:keep-all',
    ].join(';');
    document.body.appendChild(_tip);

    // ── title → data-sqm-tip 일괄 전환 ──
    function convertTitles(root) {
      (root || document).querySelectorAll('[title]').forEach(function(el) {
        var t = el.getAttribute('title');
        if (t) {
          el.setAttribute('data-sqm-tip', t);
          el.removeAttribute('title');
        }
      });
    }

    if (document.readyState === 'loading') {
      document.addEventListener('DOMContentLoaded', function() { convertTitles(); });
    } else {
      convertTitles();
    }

    // ── MutationObserver: 동적 추가 요소 처리 ──
    var _observer = new MutationObserver(function(mutations) {
      mutations.forEach(function(m) {
        m.addedNodes.forEach(function(node) {
          if (node.nodeType !== 1) return;
          if (node.hasAttribute && node.hasAttribute('title')) {
            node.setAttribute('data-sqm-tip', node.getAttribute('title'));
            node.removeAttribute('title');
          }
          convertTitles(node);
        });
        if (m.type === 'attributes' && m.attributeName === 'title' && m.target) {
          var t = m.target.getAttribute('title');
          if (t) {
            m.target.setAttribute('data-sqm-tip', t);
            m.target.removeAttribute('title');
          }
        }
      });
    });
    _observer.observe(document.documentElement, {
      subtree: true,
      childList: true,
      attributes: true,
      attributeFilter: ['title']
    });

    // ── 위치 계산 ──
    function _pos(e) {
      var mx = e.clientX, my = e.clientY;
      var tw = _tip.offsetWidth  || 220;
      var th = _tip.offsetHeight || 36;
      var vw = window.innerWidth, vh = window.innerHeight;
      var gap = 14;
      var x = mx + gap;
      var y = my + gap;
      if (x + tw + 4 > vw) x = mx - tw - gap;
      if (y + th + 4 > vh) y = my - th - gap;
      if (x < 4) x = 4;
      if (y < 4) y = 4;
      _tip.style.left = x + 'px';
      _tip.style.top  = y + 'px';
    }

    var _active = null;
    var _showTimer = null;

    function _show(el, e) {
      var txt = el.getAttribute('data-sqm-tip');
      if (!txt) return;
      _active = el;
      clearTimeout(_showTimer);
      _showTimer = setTimeout(function() {
        _tip.textContent = txt;
        _tip.style.display = 'block';
        _pos(e);
      }, 180);
    }

    function _hide() {
      _active = null;
      clearTimeout(_showTimer);
      _tip.style.display = 'none';
    }

    document.addEventListener('mouseover', function(e) {
      var el = e.target && e.target.closest && e.target.closest('[data-sqm-tip]');
      if (el && el !== _active) _show(el, e);
      else if (!el) _hide();
    }, true);

    document.addEventListener('mouseout', function(e) {
      var rel = e.relatedTarget;
      if (!rel || !rel.closest || !rel.closest('[data-sqm-tip]')) _hide();
    }, true);

    document.addEventListener('mousemove', function(e) {
      if (_tip.style.display !== 'none') _pos(e);
    }, true);

    document.addEventListener('mousedown', _hide, true);
    document.addEventListener('click', _hide, true);
    document.addEventListener('keydown', _hide, true);

    console.log('[SQM Tooltip] custom dark tooltip ready');
  })();
})();
