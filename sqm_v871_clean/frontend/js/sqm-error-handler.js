/* ==========================================================
   sqm-error-handler.js — 전역 JS 에러 핸들러 (Phase 1-3)
   처리되지 않은 에러·프로미스 거부를 토스트로 사용자에게 표시.
   콘솔 로그도 병행하여 디버깅 지원.
   ========================================================== */
(function () {
  'use strict';
  if (window.__SQM_ERROR_HANDLER__) return;
  window.__SQM_ERROR_HANDLER__ = true;

  // 토스트가 준비될 때까지 대기 후 표시
  function _toast(msg, type) {
    function _try(attempt) {
      if (typeof window.showToast === 'function') {
        window.showToast(type || 'error', msg);
      } else if (attempt < 10) {
        setTimeout(function () { _try(attempt + 1); }, 300);
      }
      // 10회 시도 후에도 없으면 무시 (콘솔에는 이미 기록됨)
    }
    _try(0);
  }

  // ── 동기 JS 에러 ──────────────────────────────────────────
  window.addEventListener('error', function (e) {
    var src  = (e.filename || '').replace(/.*\//, '');  // 파일명만
    var line = e.lineno  || '';
    var msg  = e.message || '알 수 없는 오류';

    // 외부 라이브러리 에러는 콘솔만 (토스트 남용 방지)
    var isInternal = src && (
      src.indexOf('sqm-') === 0 ||
      src.indexOf('index') === 0 ||
      src === ''
    );

    console.error('[SQM ERROR]', src, line, msg);

    if (isInternal) {
      _toast('⚠️ 오류: ' + msg + (src ? ' (' + src + ':' + line + ')' : ''), 'error');
    }
  });

  // ── 비동기 Promise 에러 ───────────────────────────────────
  window.addEventListener('unhandledrejection', function (e) {
    var reason = e.reason;
    var msg;

    if (reason && reason.message) {
      msg = reason.message;
    } else if (typeof reason === 'string') {
      msg = reason;
    } else {
      msg = 'API 오류';
    }

    // AbortError(타임아웃/취소)는 토스트 없이 콘솔만
    if (reason && reason.name === 'AbortError') {
      console.warn('[SQM ABORT]', msg);
      return;
    }

    console.error('[SQM PROMISE]', reason);
    _toast('🔴 처리 중 오류: ' + msg, 'error');
  });

  console.info('[sqm-error-handler] 전역 에러 핸들러 로드됨');
})();
