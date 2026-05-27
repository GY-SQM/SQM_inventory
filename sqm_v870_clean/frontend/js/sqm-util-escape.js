/* =======================================================================
   SQM Inventory - sqm-util-escape.js — escapeHtml 글로벌 유틸
   Extracted from sqm-inline.js (Phase B-S2) — 2026-05-23
   Source: sqm-inline.js (현 line 469-473) + window 노출 line 5333
   ======================================================================= */
(function () {
  'use strict';
  if (window.__SQM_UTIL_ESCAPE_INSTALLED__) return;
  window.__SQM_UTIL_ESCAPE_INSTALLED__ = true;

  function escapeHtml(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, function (m) {
      return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m];
    });
  }

  // 글로벌 노출 (sqm-inline.js 의 기존 호출 호환)
  window.escapeHtml = escapeHtml;
})();
