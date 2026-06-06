/* =======================================================================
   SQM Inventory - sqm-util-toast.js — 토스트 알림 시스템
   Extracted from sqm-inline.js (Phase B-S6a) — 2026-05-23
   Source: sqm-inline.js line 247-273 (ensureToastContainer + showToast)

   외부 의존: window.escapeHtml (sqm-util-escape.js, S2)
   외부 노출: window.showToast (다른 10+ 파일에서 사용)
   ======================================================================= */
(function () {
  'use strict';
  if (window.__SQM_UTIL_TOAST_INSTALLED__) return;
  window.__SQM_UTIL_TOAST_INSTALLED__ = true;

  function ensureToastContainer() {
    var c = document.getElementById('toast-container');
    if (!c) {
      c = document.createElement('div');
      c.id = 'toast-container';
      document.body.appendChild(c);
    }
    return c;
  }

  var TOAST_ICONS = {success:'&#x2705;', info:'&#x2139;&#xFE0F;', warning:'&#x26A0;&#xFE0F;', error:'&#x274C;'};

  function showToast(type, message, duration) {
    if (!['success','info','warning','error'].includes(type)) type = 'info';
    duration = duration || 3000;
    var c = ensureToastContainer();
    var t = document.createElement('div');
    t.className = 'toast ' + type;
    t.innerHTML = '<span>' + (TOAST_ICONS[type]||'') + '</span><span>' + escapeHtml(message) + '</span>';
    c.appendChild(t);
    setTimeout(function () {
      t.style.opacity = '0';
      t.style.transition = 'opacity 300ms';
      setTimeout(function () { if (t.parentNode) t.parentNode.removeChild(t); }, 300);
    }, duration);
  }
  window.showToast = showToast;
})();
