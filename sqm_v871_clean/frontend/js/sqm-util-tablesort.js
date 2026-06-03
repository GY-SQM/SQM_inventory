/* =======================================================================
   SQM Inventory - sqm-util-tablesort.js — 테이블 헤더 클릭 정렬
   v8.7.0 개선 (2026-05-24):
     - 초기 ⇅ 표시 (정렬 가능 컬럼 시각 표시)
     - #, +, ⋯, 빈 칸 컬럼 제외 (비정렬 컬럼 스킵)
     - 화살표를 span 으로 분리 → textContent 덮어쓰기 버그 제거
     - 한국어 localeCompare('ko') 적용
   ======================================================================= */
(function () {
  'use strict';
  if (window.__SQM_UTIL_TABLESORT_INSTALLED__) return;
  window.__SQM_UTIL_TABLESORT_INSTALLED__ = true;

  /* 정렬 제외 컬럼 텍스트 (공백 제거 후 비교) */
  var SKIP = { '#': true, '+': true, '⋯': true, '': true };

  /* 화살표 span 을 th 에 추가 (최초 1회) */
  function _addArrow(th) {
    if (th.querySelector('.sqm-sort-arrow')) return;
    var sp = document.createElement('span');
    sp.className = 'sqm-sort-arrow';
    sp.style.cssText = 'font-size:9px;margin-left:3px;color:rgba(255,255,255,.35);pointer-events:none';
    sp.textContent = '⇅';
    th.appendChild(sp);
  }

  /* 활성 화살표 갱신 */
  function _updateArrows(headers, activeIdx, asc) {
    headers.forEach(function(h, i) {
      var sp = h.querySelector('.sqm-sort-arrow');
      if (!sp) return;
      if (i === activeIdx) {
        sp.textContent = asc ? '▲' : '▼';
        sp.style.color  = '#FFD700';
      } else {
        sp.textContent = '⇅';
        sp.style.color  = 'rgba(255,255,255,.35)';
      }
    });
  }

  /* ===================================================
     enableTableSort — .data-table 에 클릭 정렬 바인딩
     사용법: enableTableSort(tableEl)
     숫자·날짜·문자 자동 감지, 한국어 정렬 지원
     =================================================== */
  function enableTableSort(tableEl) {
    if (!tableEl || tableEl.dataset._sortBound) return;
    tableEl.dataset._sortBound = '1';

    var headers = Array.prototype.slice.call(
      tableEl.querySelectorAll('thead th')
    );

    /* 정렬 가능 컬럼에만 화살표 + 커서 추가 */
    headers.forEach(function(th) {
      var txt = th.textContent.trim().replace(/[▲▼⇅]/g, '').trim();
      if (SKIP[txt]) return;
      _addArrow(th);
      th.style.cursor     = 'pointer';
      th.style.userSelect = 'none';
      th.title            = '클릭: 오름차순 / 재클릭: 내림차순';
    });

    /* 헤더 클릭 이벤트 */
    headers.forEach(function(th, colIdx) {
      var txt = th.textContent.trim().replace(/[▲▼⇅]/g, '').trim();
      if (SKIP[txt]) return;

      var asc = true;
      th.addEventListener('click', function() {
        var tbody = tableEl.querySelector('tbody');
        if (!tbody) return;
        var rows = Array.prototype.slice.call(tbody.querySelectorAll('tr'));

        rows.sort(function(a, b) {
          var ca = ((a.cells[colIdx] || {}).textContent || '').trim();
          var cb = ((b.cells[colIdx] || {}).textContent || '').trim();
          var na = parseFloat(ca.replace(/,/g, ''));
          var nb = parseFloat(cb.replace(/,/g, ''));
          if (!isNaN(na) && !isNaN(nb)) return asc ? na - nb : nb - na;
          return asc ? ca.localeCompare(cb, 'ko') : cb.localeCompare(ca, 'ko');
        });

        rows.forEach(function(r) { tbody.appendChild(r); });
        _updateArrows(headers, colIdx, asc);
        asc = !asc;
      });
    });
  }

  window.enableTableSort = enableTableSort;

  /* 자동 바인딩 — MutationObserver로 .data-table 탐지 */
  var _sortObserver = new MutationObserver(function() {
    document.querySelectorAll('table.data-table').forEach(function(t) {
      enableTableSort(t);
    });
  });
  _sortObserver.observe(document.documentElement, { childList: true, subtree: true });

})();
