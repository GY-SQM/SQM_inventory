/* ==========================================================================
   sqm-modal-manager.js  (v8.7.0-r6)
   전역 모달/팝업 창 관리자
   ─────────────────────────────────────────────────────────────────────────
   ■ 기능
     1. 모든 창 자유 이동 — 부모/viewport 경계 제한 없음
     2. 모든 창 자유 크기 조절 — 8방향 리사이즈 핸들
     3. 크기·위치 자동 저장 — localStorage, 창 ID 기준
     4. 다음 열릴 때 저장된 크기/위치로 자동 복원
     5. MutationObserver — 동적으로 추가되는 창도 자동 감지·적용

   ■ 적용 대상 (자동 감지)
     · sqm-modal-inner       (공통 모달)
     · wh-dong-lot-popup     (LOT 테이블 팝업)
     · wh-embed-dong-lot-popup
     · wh-lot-detail-panel   (LOT 상세 슬라이드)
     · wh-embed-rack-detail  (랙 그리드)
     · 앞으로 추가될 모든 .sqm-managed-window 클래스

   ■ 원칙
     · sqm-inline.js / sqm-core.js 미수정 (ABSOLUTE EDIT BAN 준수)
     · 오버레이(backdrop) div는 그대로 — 클릭 차단만 제거
     · sub_lt 삭제 금지 원칙 미적용 대상 (UI 레이어만)
   ==========================================================================*/

(function () {
  'use strict';
  if (window.__SQM_MODAL_MANAGER__) return;
  window.__SQM_MODAL_MANAGER__ = true;

  // 디버그 모드 — localStorage.sqm_modal_debug='1' 또는 ?modaldbg=1 로 켜기
  var DBG = false;
  try {
    DBG = (localStorage.getItem('sqm_modal_debug') === '1') ||
          /[?&]modaldbg=1/.test(location.search || '');
  } catch (e) {}
  function _log() {
    if (!DBG) return;
    try { console.info.apply(console, ['[sqm-modal-mgr]'].concat([].slice.call(arguments))); }
    catch (e) {}
  }
  // 시작 로그는 항상 출력 (사용자가 로드 여부 확인 가능)
  try { console.info('[sqm-modal-mgr] v8.7.0-r12-jitterfix loaded'); } catch (e) {}

  /* ── 상수 ─────────────────────────────────────────────────────────────── */
  var STORAGE_KEY = 'sqm_win_prefs';   // localStorage 키
  var MIN_W = 320, MIN_H = 180;        // 최소 창 크기
  var HANDLE_SIZE = 8;                 // 리사이즈 핸들 두께(px)

  /* ── 자동 감지 대상 ID / 클래스 ──────────────────────────────────────── */
  var TARGET_IDS = [
    // ── 공통 모달 ──
    'sqm-modal-inner',
    // ── 창고 대시보드 ──
    'wh-dong-lot-popup',
    'wh-embed-dong-lot-popup',
    'wh-lot-detail-panel',
    'wh-embed-rack-detail',
    'sqm-warehouse-dashboard',     // 입고 메뉴 창고 대시보드 메인창
    // ── 원스톱 입고 ──
    'sqm-parse-result',            // 파싱 결과 창
    'sqm-parse-log',               // 파싱 로그
    'sqm-onestop-parse-stream',    // 파싱 실시간 스트림 (SSE)
    'sqm-gemini-compare',          // Gemini 비교 창
    // ── 기타 기능 창 ──
    'sqm-case3-dialog',            // Case3 다이얼로그
    'sqm-listview-modal',          // 리스트뷰 모달
    'sqm-loc-mapping-modal',       // 위치 매핑 모달
    'sqm-locmap-import-modal',     // 위치맵 임포트 모달
    'sqm-weight-panel',            // 무게 현황 패널
    'sqm-tonbag-picker',
    'tonbag-modal',                // 톤백 보기 모달
    'status-revert-panel',         // 상태 되돌리기 패널
    'sqm-debug-panel',             // 디버그 패널
    'sqm-ai-chat-panel',           // AI 재고 조회 패널
  ];
  var TARGET_CLASS = 'sqm-managed-window';

  // 자동 감지 제외 (위젯/토스트/툴팁/배너 등 — 리사이즈 의미 없음)
  var EXCLUDE_IDS = {
    'sqm-tooltip': 1,
    'toast-container': 1,
    'sqm-offline-banner': 1,
    'wh-mode-toggle': 1,
    'wh-lot-search-wrap': 1,
    'wh-embed-tip': 1,
    'allocation-footer': 1,
    'scan-history-footer': 1,
    'tonbag-page-footer': 1,
    'move-history-footer': 1,
    'pending-ctx-menu': 1,
    // 확인용 작은 오버레이는 자동 감지하되 사이즈가 작아 의미 미미
  };

  /* ── localStorage ─────────────────────────────────────────────────────── */
  function _loadPrefs() {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}'); }
    catch(e) { return {}; }
  }
  function _savePrefs(prefs) {
    try { localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs)); }
    catch(e) { /* quota 초과 무시 */ }
  }
  function _savePref(id, data) {
    var p = _loadPrefs(); p[id] = data; _savePrefs(p);
  }
  function _getPref(id) {
    return (_loadPrefs())[id] || null;
  }

  /* ── 이미 처리된 엘리먼트 추적 ──────────────────────────────────────── */
  var _processed = new WeakSet();

  /* ── 드래그 핸들 찾기 (헤더 역할을 하는 첫 번째 자식 div) ─────────── */
  function _findDragHandle(el) {
    // 1) 명시적 드래그바 속성/클래스
    var h = el.querySelector('.sqm-drag-handle,.modal-drag-handle,[data-drag-handle]');
    if (h) return h;
    // 2) 알려진 헤더 ID — el 안에 있는 것만
    var ids = ['sqm-modal-header','wh-dlp-header','wlp-header','wh-dash-header'];
    for (var i=0; i<ids.length; i++) {
      h = document.getElementById(ids[i]);
      if (h && el.contains(h)) return h;
    }
    // 3) el의 직계 자식 div 중 첫번째 (헤더 패턴) — flex-shrink:0 이거나 배경색이 있는 것 우선
    var children = el.children;
    for (var j=0; j<children.length; j++) {
      if (children[j].tagName === 'DIV') {
        var cs = window.getComputedStyle(children[j]);
        // 스크롤 컨테이너는 헤더가 아님
        if (cs.overflow === 'auto' || cs.overflow === 'scroll') continue;
        return children[j];
      }
    }
    // 4) 최후 수단: el 자신
    return el;
  }

  /* ── 창 자유화: 오버레이 안에 갇혀 있으면 body로 꺼냄 ──────────────── */
  function _liberate(el) {
    // 이미 body 직속이어도 transform 센터링 제거 + 절대 위치 고정 필요
    var parent = el.parentElement;

    // body 직속인 경우: transform:translate(-50%,-50%) 패턴 해제
    if (parent === document.body) {
      var cs = window.getComputedStyle(el);
      // transform이 none이 아니면 (translate 센터링) → 실좌표로 변환
      if (cs.transform && cs.transform !== 'none' && cs.transform !== '') {
        var rect = el.getBoundingClientRect();
        el.style.transform = 'none';
        el.style.top    = rect.top  + 'px';
        el.style.left   = rect.left + 'px';
        el.style.width  = rect.width  + 'px';
        el.style.height = rect.height + 'px';
        el.style.margin = '0';
        el.style.maxWidth  = 'none';
        el.style.maxHeight = 'none';
      }
      return;  // body 직속은 오버레이 탈출 불필요
    }

    if (!parent) return;

    // 오버레이 (inset:0, display:flex, align-items:center 패턴) 감지
    var ps = window.getComputedStyle(parent);
    var isOverlay = (ps.position === 'fixed' &&
      (ps.inset === '0px' || (ps.top==='0px'&&ps.left==='0px'&&ps.right==='0px'&&ps.bottom==='0px')));
    if (!isOverlay) return;

    // 현재 화면 위치 계산 후 body에 재삽입
    var rect2 = el.getBoundingClientRect();
    document.body.appendChild(el);
    el.style.position  = 'fixed';
    el.style.top       = rect2.top  + 'px';
    el.style.left      = rect2.left + 'px';
    el.style.width     = rect2.width  + 'px';
    el.style.height    = rect2.height + 'px';
    el.style.transform = 'none';
    el.style.margin    = '0';
    el.style.maxWidth  = 'none';
    el.style.maxHeight = 'none';

    // ★ FIX: 분리된 inner와 원본 overlay를 양방향 참조로 묶는다.
    //   - X 버튼이 overlay.style.display='none' 만 해도 inner 함께 숨김
    //   - overlay.remove() / DOM 제거 시 inner도 제거
    //   - 다시 보일 때 inner도 복원
    el._sqmOverlay   = parent;
    parent._sqmInner = el;

    // 오버레이는 포인터 이벤트만 패스스루 (클릭 시 닫기 유지)
    parent.style.pointerEvents = 'none';
    el.style.pointerEvents = 'all';

    // 오버레이 display 감시
    _watchOverlayDisplay(parent, el);
    // 백드롭(검은 영역) 클릭 시 닫기 동작 복원
    _wireBackdropClose(parent, el);
  }

  /* ── 오버레이 display 변화 → inner 동기화 ────────────────────────────── */
  function _watchOverlayDisplay(overlay, inner) {
    if (overlay._sqmDisplayWatched) return;
    overlay._sqmDisplayWatched = true;
    function _sync() {
      var cs = window.getComputedStyle(overlay);
      var hiddenByStyle = (overlay.style.display === 'none' ||
                          overlay.style.visibility === 'hidden');
      var hiddenByComputed = (cs.display === 'none' || cs.visibility === 'hidden');
      var detached = !document.body.contains(overlay);
      if (detached) {
        // overlay가 DOM에서 사라졌다 → inner도 제거
        if (document.body.contains(inner)) inner.remove();
        return;
      }
      if (hiddenByStyle || hiddenByComputed) {
        if (inner.style.display !== 'none') {
          inner._sqmPrevDisplay = inner.style.display || '';
          inner.style.display = 'none';
        }
      } else {
        if (inner.style.display === 'none') {
          inner.style.display = inner._sqmPrevDisplay || '';
        }
      }
    }
    var obs = new MutationObserver(_sync);
    obs.observe(overlay, { attributes: true, attributeFilter: ['style', 'class', 'hidden'] });
    // 부모 변경(=overlay 자체가 DOM에서 떨어질 때) 감시
    if (overlay.parentNode) {
      var parentObs = new MutationObserver(function() { _sync(); });
      parentObs.observe(overlay.parentNode, { childList: true });
    }
  }

  /* ── 백드롭(검은 영역) 클릭으로 창 닫기 복원 ─────────────────────────── */
  function _wireBackdropClose(overlay, inner) {
    if (overlay._sqmBackdropWired) return;
    overlay._sqmBackdropWired = true;
    // overlay 본체는 pointer-events:none 이므로 클릭이 안 잡힘.
    // 대신 body에 캡처 단계 핸들러 1회 등록해서 좌표로 판정한다.
    if (!document.body._sqmBackdropDelegated) {
      document.body._sqmBackdropDelegated = true;
      document.addEventListener('mousedown', function(e) {
        // 백드롭 후보: 보이는 overlay 중에서 점이 overlay 영역이고 inner 영역 밖인 경우
        var overlays = document.querySelectorAll('[data-sqm-overlay], #sqm-modal');
        for (var i = 0; i < overlays.length; i++) {
          var ov = overlays[i];
          if (!ov || !ov._sqmInner) continue;
          var cs = window.getComputedStyle(ov);
          if (cs.display === 'none' || cs.visibility === 'hidden') continue;
          var innerEl = ov._sqmInner;
          // 클릭 대상이 inner 내부거나, inner의 자손 모달 핸들/버튼이면 스킵
          if (innerEl.contains(e.target)) continue;
          // 좌표가 overlay 영역 안에 있는지 (전체 화면 백드롭은 대부분 inset:0)
          var or = ov.getBoundingClientRect();
          if (e.clientX < or.left || e.clientX > or.right) continue;
          if (e.clientY < or.top  || e.clientY > or.bottom) continue;
          // inner 영역 안이면 skip (이미 위에서 contains 처리됨)
          // 닫기 실행: overlay 숨김 → _watchOverlayDisplay가 inner도 숨김
          ov.style.display = 'none';
          e.stopPropagation();
          break;
        }
      }, true);
    }
    overlay.setAttribute('data-sqm-overlay', '1');
  }

  /* ── ★ 박스를 현재 메인창(뷰포트) 안으로 맞춤 ─────────────────────────
     크기가 창보다 크면 줄이고, 밖으로 나가면 안으로 끌어당긴 {w,h,x,y} 반환.
     순수 계산 함수 — 호출할 때마다 같은 입력엔 같은 출력 ⇒ 떨림(루프) 불가. */
  function _fitBox(w, h, x, y) {
    var M = 6;                                   // 가장자리 여백(px)
    var KEEP = 140;                              // 최소 이만큼은 화면에 남겨 잡을 수 있게
    var vw = window.innerWidth, vh = window.innerHeight;
    // ★ r11: 크기는 사용자가 정한 값을 존중 — 메인창보다 커도 강제 축소하지 않음.
    //   (단일 OS창이라 넘치는 부분은 내부 스크롤로, 진짜 창 확장은 popout 사용)
    //   최소 크기만 보장 → 같은 입력엔 항상 같은 출력(멱등) ⇒ 떨림 루프 불가.
    if (w < MIN_W) w = MIN_W;
    if (h < MIN_H) h = MIN_H;
    if (x == null) x = Math.round((vw - w) / 2);  // 위치 없으면 가운데
    if (y == null) y = Math.round((vh - h) / 2);
    // 위치만 보정: 제목줄/드래그 핸들이 항상 화면에 남도록(닫기·이동 가능 보장)
    if (x > vw - KEEP) x = vw - KEEP;             // 오른쪽으로 너무 나감 방지
    if (y > vh - 40)   y = vh - 40;               // 아래로 너무 내려감 방지
    if (x < M) x = M;
    if (y < M) y = M;
    return { w: Math.round(w), h: Math.round(h), x: Math.round(x), y: Math.round(y) };
  }

  /* ── 위치/크기 복원 (★ 항상 뷰포트 안으로 맞춰 적용 → 잘림 방지) ────────── */
  function _restorePref(el, id) {
    var pref = _getPref(id);
    if (!pref) return;
    el.style.transform = 'none';
    el.style.margin    = '0';
    // !important 까지 덮어 max-* / min-* 강제 해제
    el.style.setProperty('max-width',  'none', 'important');
    el.style.setProperty('max-height', 'none', 'important');
    el.style.setProperty('min-width',  '0',    'important');
    el.style.setProperty('min-height', '0',    'important');
    // 저장값을 현재 메인창 크기에 맞춰 축소·수납한 값으로 적용
    var r0  = el.getBoundingClientRect();
    var box = _fitBox(pref.w || r0.width, pref.h || r0.height,
                      (pref.x != null ? pref.x : null),
                      (pref.y != null ? pref.y : null));
    el.style.setProperty('width',  box.w + 'px', 'important');
    el.style.setProperty('height', box.h + 'px', 'important');
    el.style.left = box.x + 'px';
    el.style.top  = box.y + 'px';
    // ★ r11: GPU 레이어로 분리해 소수점 렌더링 떨림(jitter) 억제
    el.style.setProperty('will-change', 'transform');
    el.style.setProperty('backface-visibility', 'hidden');
    _log('restorePref(fit)', id, box);
  }

  /* ── ★ 글로벌 강제 닫기 위임 ──────────────────────────────────────────
     원칙: 사용자가 X/닫기를 누르면 무조건 그 창이 닫혀야 함.
     기존 onclick은 그대로 두고(중복 처리 OK), capture+bubble 양쪽에서
     "닫기성 요소" 클릭을 감지해 가장 가까운 모달 컨테이너를 강제로 닫음. */

  function _isCloseLike(el) {
    if (!el || el.nodeType !== 1) return false;
    if (el.disabled) return false;
    var tag = el.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return false;

    // ── 1순위(강한 신호): id 패턴 — *-close, *-cancel, *-dismiss
    var id = (el.id || '').toLowerCase();
    if (id && /(^|[-_])(close|cancel|dismiss)([-_]|$)/.test(id)) return true;

    // ── 2순위(강한 신호): class 패턴
    var cls = '';
    if (el.classList && el.classList.length) {
      cls = ' ' + Array.prototype.join.call(el.classList, ' ').toLowerCase() + ' ';
    }
    if (/\s(modal-close|btn-close|close-btn|sqm-close)\s/.test(cls)) return true;

    // ── 3순위(강한 신호): aria-label / title
    var al = '';
    if (el.getAttribute) {
      al = ((el.getAttribute('aria-label') || '') + ' ' + (el.getAttribute('title') || '')).toLowerCase();
    }
    if (al && /(\bclose\b|\bcancel\b|닫기|취소)/.test(al)) return true;

    // ── 4순위(텍스트 휴리스틱) — 짧은 X 글리프 또는 "닫기/취소" 단독
    var txt = '';
    if (tag === 'BUTTON' || tag === 'A' || tag === 'SPAN' || tag === 'I' || tag === 'DIV') {
      txt = (el.textContent || '').replace(/\s+/g, ' ').trim();
    }
    if (txt && txt.length <= 14) {
      if (/^[×✕❌✖✗⨯✘]\s*$/u.test(txt)) return true;           // × ✕ ❌ ✖
      if (/^X$/.test(txt)) return true;                              // 단독 'X' (대문자)
      if (/^(닫기|취소|Close|Cancel)$/i.test(txt)) return true;       // 짧은 라벨
      if (/^[❌✕×✖]\s*(닫기|Close)$/iu.test(txt)) return true;       // ❌ 닫기
      if (/^(닫기|Close)\s*[❌✕×✖]$/iu.test(txt)) return true;       // 닫기 ❌
    }

    // ── 5순위(보조 신호): onclick 안에 display='none' 또는 .remove()
    //   ⚠️ 토글 패턴(none↔block, ===비교)이면 close 아님
    var oc = '';
    if (el.getAttribute) oc = (el.getAttribute('onclick') || '').toLowerCase();
    if (oc) {
      var hasToggleBlock = /\.display\s*=\s*['"](block|flex|grid|inline)/.test(oc);
      var hasToggleCmp   = /\.display\s*===?\s*['"]none['"]/.test(oc);
      if (hasToggleBlock || hasToggleCmp) return false;  // 토글 — 무시
      // 텍스트가 매우 짧을 때만 close 로 인정 (UI 버튼 라벨이 길면 토글일 가능성 높음)
      if (txt.length > 0 && txt.length <= 8) {
        if (/style\.display\s*=\s*['"]none['"]/.test(oc)) return true;
        if (/\.remove\(\)/.test(oc)) return true;
      }
    }
    return false;
  }

  // 클릭된 노드부터 3단계까지 (텍스트 노드 → span → button) 탐색
  function _findCloseAncestor(node) {
    var depth = 0;
    while (node && node.nodeType === 1 && depth < 4) {
      if (_isCloseLike(node)) return node;
      node = node.parentElement;
      depth++;
    }
    return null;
  }

  function _findEnclosingModal(btn) {
    var TARGET_SET = {};
    TARGET_IDS.forEach(function(id) { TARGET_SET[id] = 1; });
    var el = btn;
    var fallback = null;
    while (el && el !== document.body && el.parentElement) {
      // 1순위: 명시적 모달 식별자
      if (el.id && TARGET_SET[el.id]) return el;
      if (el.classList && el.classList.contains(TARGET_CLASS)) return el;
      if (el.hasAttribute && el.hasAttribute('data-sqm-overlay')) return el;
      // 2순위: position:fixed + 높은 z-index + body 직속에 가까움 (fallback)
      var cs = window.getComputedStyle(el);
      if (cs.position === 'fixed') {
        var z = parseInt(cs.zIndex, 10) || 0;
        if (z >= 100 || cs.inset === '0px' ||
            (cs.top === '0px' && cs.left === '0px' && cs.right === '0px' && cs.bottom === '0px')) {
          fallback = el; // 더 위쪽 fixed 가 있을 수 있으니 계속 탐색
        }
      }
      el = el.parentElement;
    }
    return fallback;
  }

  function _hardClose(modal) {
    if (!modal) return;
    // 양방향 참조로 묶인 짝 함께 닫기
    var overlay = modal._sqmOverlay || null;
    var inner   = modal._sqmInner   || null;
    var targets = [modal];
    if (overlay && targets.indexOf(overlay) === -1) targets.push(overlay);
    if (inner   && targets.indexOf(inner)   === -1) targets.push(inner);

    // ★ 추가 안전망: ID가 알려진 outer/inner 짝이면 양쪽 모두 추가
    //   #sqm-modal ↔ #sqm-modal-inner
    var PAIRS = {
      'sqm-modal':       'sqm-modal-inner',
      'sqm-modal-inner': 'sqm-modal',
    };
    if (modal.id && PAIRS[modal.id]) {
      var mate = document.getElementById(PAIRS[modal.id]);
      if (mate && targets.indexOf(mate) === -1) targets.push(mate);
    }
    targets.forEach(function(t) {
      if (!t || !document.body.contains(t)) return;
      try {
        // 원래 onclick 이 .remove() 였다면 이미 사라졌을 수 있음 — 안전
        t.style.setProperty('display', 'none', 'important');
      } catch (err) {}
    });
  }

  function _installGlobalCloseDelegation() {
    if (window._sqmCloseDelInstalled) return;
    window._sqmCloseDelInstalled = true;
    // bubble 단계: onclick 이 먼저 실행된 뒤 보조로 닫힘 정리 (idempotent)
    document.addEventListener('click', function(e) {
      var btn = _findCloseAncestor(e.target);
      if (!btn) {
        _log('click no-close', e.target && e.target.tagName, e.target && e.target.id, (e.target && e.target.textContent || '').trim().slice(0,20));
        return;
      }
      var modal = _findEnclosingModal(btn);
      _log('close-btn detected', btn.id || btn.className || btn.tagName,
           'modal=', modal && (modal.id || modal.className));
      if (!modal) return;
      setTimeout(function() { _hardClose(modal); }, 0);
    }, false);
    // capture 단계: 50ms 후에도 모달이 살아있으면 강제 닫음
    document.addEventListener('click', function(e) {
      var btn = _findCloseAncestor(e.target);
      if (!btn) return;
      var modal = _findEnclosingModal(btn);
      if (!modal) return;
      setTimeout(function() {
        if (!modal || !document.body.contains(modal)) return;
        var cs = window.getComputedStyle(modal);
        if (cs.display !== 'none' && cs.visibility !== 'hidden') {
          _log('FORCE close (50ms 후에도 살아있음)', modal.id || modal.className);
          _hardClose(modal);
        }
      }, 50);
    }, true);
    try { console.info('[sqm-modal-mgr] global close delegation installed'); } catch (e) {}
  }

  /* ── ESC 키: 최상위 보이는 창 닫기 ───────────────────────────────────── */
  function _installEscClose() {
    if (window._sqmEscInstalled) return;
    window._sqmEscInstalled = true;
    document.addEventListener('keydown', function(e) {
      if (e.key !== 'Escape' && e.keyCode !== 27) return;
      // input/textarea 편집 중에는 무시 (IME 조합 중 포함)
      var ae = document.activeElement;
      if (ae && (ae.tagName === 'INPUT' || ae.tagName === 'TEXTAREA' || ae.isContentEditable)) {
        // 단, 닫기 키 우선순위 — Esc 누른 직후 모달은 닫고 싶을 수 있으므로
        // 검색창 등 사용 중이라면 한번은 blur만 시키고 닫지 않는다.
        try { ae.blur(); } catch (err) {}
        return;
      }
      // 가장 z-index 큰 보이는 managed window 찾기
      var topWin = null, topZ = -1;
      var candidates = [];
      TARGET_IDS.forEach(function(id) {
        var n = document.getElementById(id);
        if (n) candidates.push(n);
      });
      Array.prototype.push.apply(candidates,
        Array.prototype.slice.call(document.querySelectorAll('.' + TARGET_CLASS)));
      // 외부 overlay-style 모달도 후보 (status-revert-overlay 등)
      Array.prototype.push.apply(candidates,
        Array.prototype.slice.call(document.querySelectorAll('[data-sqm-overlay]')));
      // ★ 관리되지 않는 fullscreen overlay 자동 인식 (position:fixed + inset:0 + 반투명 배경)
      var bodyChildren = document.body.children;
      for (var i = 0; i < bodyChildren.length; i++) {
        var ch = bodyChildren[i];
        if (ch.nodeType !== 1) continue;
        if (candidates.indexOf(ch) !== -1) continue;
        var ccs = window.getComputedStyle(ch);
        if (ccs.position !== 'fixed') continue;
        if (ccs.display === 'none' || ccs.visibility === 'hidden') continue;
        var isInsetZero = (ccs.inset === '0px' ||
          (ccs.top==='0px' && ccs.left==='0px' && ccs.right==='0px' && ccs.bottom==='0px'));
        if (!isInsetZero) continue;
        // 반투명 배경 패턴(rgba alpha<1) 이거나 z-index가 높으면 overlay 후보
        var bg = ccs.backgroundColor || '';
        var isBackdrop = /rgba?\([^)]+,\s*0?\.[0-9]+\s*\)/.test(bg) ||
                         (parseInt(ccs.zIndex, 10) || 0) >= 1000;
        if (isBackdrop) candidates.push(ch);
      }
      candidates.forEach(function(el) {
        if (!el) return;
        var cs = window.getComputedStyle(el);
        if (cs.display === 'none' || cs.visibility === 'hidden') return;
        var z = parseInt(cs.zIndex, 10) || 0;
        if (z >= topZ) { topZ = z; topWin = el; }
      });
      if (!topWin) return;
      // overlay 가 있으면 overlay 숨김(→ inner sync), 없으면 자신 숨김
      var ov = topWin._sqmOverlay;
      if (ov && document.body.contains(ov)) {
        ov.style.display = 'none';
      } else if (topWin.id === 'sqm-modal') {
        // sqm-modal 자체가 overlay
        topWin.style.display = 'none';
      } else {
        topWin.style.display = 'none';
      }
      e.stopPropagation();
    }, true);
  }

  /* ── display:none 창 감시: 닫힐 때 transform 복원 처리 ──────────────── */
  /* display:none 방식 창들은 숨겨질 때 sqm-modal-manager가 변환한
     실좌표(left:700px 등)가 남아있다. 다음 열릴 때 transform없이
     열리므로 화면 밖으로 나가는 문제 발생.
     MutationObserver로 display:none 감지 → 저장된 pref 삭제하여
     다음 열릴 때 초기 center 위치로 복원. */
  function _watchDisplayNone(el, id) {
    if (!el || el._watchingDisplay) return;
    el._watchingDisplay = true;
    // 현재 표시 상태를 기록해 둔다 — style 변경이 '표시↔숨김 전환'일 때만 반응하기 위함.
    el._sqmWasHidden = (el.style.display === 'none' || el.style.visibility === 'hidden');
    var obs = new MutationObserver(function() {
      // ★ JITTER FIX (좌우 떨림 근본 차단):
      //   매니저가 left/top/width/height 를 쓰면 style 속성이 바뀌지만 표시 상태는 그대로다.
      //   예전 코드는 그때마다 _restorePref 를 다시 호출 → (쓰기→감지→쓰기) 무한 루프 = 떨림.
      //   이제는 '실제로 숨김↔표시가 바뀐 순간'에만 동작하고, 위치/크기만 바뀐 변경은 무시한다.
      var hidden = (el.style.display === 'none' || el.style.visibility === 'hidden');
      if (hidden === el._sqmWasHidden) return;   // 전환 아님(위치/크기 변경뿐) → 무시 → 루프 차단
      el._sqmWasHidden = hidden;

      if (hidden) {
        // ★ inner가 직접 숨겨졌는데 overlay가 살아 있으면 overlay도 같이 숨김
        if (el._sqmOverlay && document.body.contains(el._sqmOverlay)) {
          if (window.getComputedStyle(el._sqmOverlay).display !== 'none') {
            el._sqmOverlay.style.display = 'none';
          }
        }
        // 실좌표 → transform 방식으로 초기화 (다음 열릴 때 센터링). 저장된 크기는 그대로 유지.
        el.style.left      = '50%';
        el.style.top       = '50%';
        el.style.transform = 'translate(-50%, -50%)';
        el.style.margin    = '0';
      } else {
        // 다시 표시될 때 → _liberate + 저장된 위치/크기 복원 (max-* 잠금 해제 후 1회만)
        setTimeout(function() {
          _liberate(el);
          el.style.setProperty('max-width',  'none', 'important');
          el.style.setProperty('max-height', 'none', 'important');
          el.style.setProperty('min-width',  '0',    'important');
          el.style.setProperty('min-height', '0',    'important');
          _restorePref(el, id);
        }, 10);
      }
    });
    obs.observe(el, { attributes: true, attributeFilter: ['style'] });
  }

  /* ── 리사이즈 핸들 CSS 삽입 (1회만) ─────────────────────────────────── */
  var _cssInjected = false;
  function _injectCSS() {
    if (_cssInjected) return;
    _cssInjected = true;
    var s = document.createElement('style');
    s.textContent = [
      /* 리사이즈 핸들 기본 */
      '.sqm-rh{position:absolute;z-index:10;}',
      '.sqm-rh-n {top:0;left:'+HANDLE_SIZE+'px;right:'+HANDLE_SIZE+'px;height:'+HANDLE_SIZE+'px;cursor:n-resize;}',
      '.sqm-rh-s {bottom:0;left:'+HANDLE_SIZE+'px;right:'+HANDLE_SIZE+'px;height:'+HANDLE_SIZE+'px;cursor:s-resize;}',
      '.sqm-rh-e {top:'+HANDLE_SIZE+'px;right:0;bottom:'+HANDLE_SIZE+'px;width:'+HANDLE_SIZE+'px;cursor:e-resize;}',
      '.sqm-rh-w {top:'+HANDLE_SIZE+'px;left:0;bottom:'+HANDLE_SIZE+'px;width:'+HANDLE_SIZE+'px;cursor:w-resize;}',
      '.sqm-rh-ne{top:0;right:0;width:'+(HANDLE_SIZE*2)+'px;height:'+(HANDLE_SIZE*2)+'px;cursor:ne-resize;}',
      '.sqm-rh-nw{top:0;left:0;width:'+(HANDLE_SIZE*2)+'px;height:'+(HANDLE_SIZE*2)+'px;cursor:nw-resize;}',
      '.sqm-rh-se{bottom:0;right:0;width:'+(HANDLE_SIZE*2)+'px;height:'+(HANDLE_SIZE*2)+'px;cursor:se-resize;background:rgba(79,195,247,.18);border-radius:0 0 4px 0;}',
      '.sqm-rh-sw{bottom:0;left:0;width:'+(HANDLE_SIZE*2)+'px;height:'+(HANDLE_SIZE*2)+'px;cursor:sw-resize;}',
      /* 드래그 힌트 강화 */
      '.sqm-drag-active{outline:1px dashed rgba(79,195,247,.4)!important;}',
      /* 창 포커스 시 미세 하이라이트 */
      '.sqm-win-focused{box-shadow:0 0 0 2px rgba(79,195,247,.35),0 12px 40px rgba(0,0,0,.6)!important;}',
      /* ★ X 닫기 버튼이 리사이즈 핸들보다 위에 오도록 */
      '.sqm-managed-window button[onclick*="display"][onclick*="none"],'
      + '.sqm-managed-window button[onclick*="remove"],'
      + '#sqm-listview-close,#loc-map-close,#lmi-close,'
      + '#wh-dash-close,#case3-close,#sr-close,'
      + '#wlp-close,#wh-embed-rack-close,'
      + '[id$="-close"],[id$="-cancel"]'
      + '{position:relative!important;z-index:20!important;}',
    ].join('');
    document.head.appendChild(s);
  }

  /* ── 핵심: 드래그 + 8방향 리사이즈 + 저장 적용 ─────────────────────── */
  function _applyManager(el, id) {
    if (_processed.has(el)) return;
    _processed.add(el);
    _injectCSS();

    // 자유화 (오버레이에서 body로)
    _liberate(el);

    // position:fixed 보장 + 인라인 max-* 강제 해제 (!important 까지 덮음)
    el.style.setProperty('position', 'fixed', 'important');
    el.style.transform = 'none';
    el.style.setProperty('max-width',  'none', 'important');
    el.style.setProperty('max-height', 'none', 'important');
    el.style.setProperty('min-width',  '0',    'important');
    el.style.setProperty('min-height', '0',    'important');
    // overflow:hidden → 리사이즈 핸들이 잘리지 않도록 visible로
    el.style.overflow  = 'visible';
    // 내부 스크롤 컨테이너(body 역할 div)는 그대로 — 첫번째 flex 자식 중 overflow:auto인 것
    // (wh-dlp-body 같은 내부 스크롤 div는 건드리지 않음)

    // display:none 방식 창 감시 (닫힐 때 transform 초기화)
    _watchDisplayNone(el, id);

    // 저장된 위치/크기 복원
    _restorePref(el, id);

    // ★ 저장값 없던 창도 최초 1회 메인창 안으로 수납 (내용 렌더 후 1회만)
    //   수납한 값을 곧바로 저장 → 이후 복원과 값이 일치하므로 떨림(루프) 없음
    if (!_getPref(id)) {
      setTimeout(function () {
        try {
          if (!document.body.contains(el)) return;
          var cs = window.getComputedStyle(el);
          if (cs.display === 'none' || cs.visibility === 'hidden') return;
          var M = 6, vw = window.innerWidth, vh = window.innerHeight;
          var r = el.getBoundingClientRect();
          var over = (r.width  > vw - M * 2) || (r.height > vh - M * 2) ||
                     (r.right  > vw - M) || (r.bottom > vh - M) ||
                     (r.left   < M)      || (r.top    < M);
          if (!over) return;                         // 이미 안에 들어옴 → 손대지 않음
          var box = _fitBox(r.width, r.height, r.left, r.top);
          el.style.setProperty('position', 'fixed', 'important');
          el.style.transform = 'none';
          el.style.setProperty('width',  box.w + 'px', 'important');
          el.style.setProperty('height', box.h + 'px', 'important');
          el.style.left = box.x + 'px';
          el.style.top  = box.y + 'px';
          _persist(el, id);                          // 저장 → 복원과 일치
          _log('initial fit', id, box);
        } catch (e) { _log('initial fit 오류', e); }
      }, 90);
    }

    var dragHandle = _findDragHandle(el);

    /* ── 🪟 별도 OS 창 분리(popout) 버튼 자동 부착 ──────────────────────
       관리 대상 모든 창에 "메인 창 밖으로 빼는" 탈출구를 보장한다.
       - sqmAddPopOutBtn 내부에서 .sqm-popout-btn 중복은 자동 방지
       - 헤더가 곧 dragHandle (관리창 공통). 실패해도 매니저 동작에 영향 없음 */
    try {
      if (typeof window.sqmAddPopOutBtn === 'function' &&
          dragHandle && dragHandle !== el) {
        window.sqmAddPopOutBtn(el, dragHandle, {});
        _log('popout 버튼 자동 부착', id);
      }
    } catch (e) { _log('popout 버튼 부착 실패', id, e); }

    /* ── 드래그 이동 ── */
    var drag = { on:false, sx:0, sy:0, ox:0, oy:0 };
    dragHandle.style.cursor     = 'move';
    dragHandle.style.userSelect = 'none';

    dragHandle.addEventListener('mousedown', function(e) {
      if (e.target.tagName === 'BUTTON' || e.target.tagName === 'INPUT') return;
      drag.on = true;
      drag.sx = e.clientX; drag.sy = e.clientY;
      var r    = el.getBoundingClientRect();
      drag.ox  = r.left; drag.oy = r.top;
      el.style.left = drag.ox + 'px'; el.style.top = drag.oy + 'px';
      el.style.transform = 'none';
      el.classList.add('sqm-drag-active');
      _focus(el);
      e.preventDefault();
    });

    document.addEventListener('mousemove', function(e) {
      if (!drag.on) return;
      // viewport 제한 없음 — 자유 이동
      el.style.left = (drag.ox + (e.clientX - drag.sx)) + 'px';
      el.style.top  = (drag.oy + (e.clientY - drag.sy)) + 'px';
    });

    document.addEventListener('mouseup', function() {
      if (!drag.on) return;
      drag.on = false;
      el.classList.remove('sqm-drag-active');
      _persist(el, id);
    });

    /* ── 8방향 리사이즈 ── */
    ['n','s','e','w','ne','nw','se','sw'].forEach(function(dir) {
      // 기존 핸들 제거(sqm-util-modal._makeDraggableResizable 등이 만든 것) — 저장 기능 없는 옛 핸들러 교체
      var existing = el.querySelectorAll('.sqm-rh-' + dir);
      Array.prototype.forEach.call(existing, function(old) { try { old.remove(); } catch (e) {} });
      var h   = document.createElement('div');
      h.className = 'sqm-rh sqm-rh-' + dir;
      el.appendChild(h);
      var res = { on:false, sx:0, sy:0, ow:0, oh:0, ox:0, oy:0 };
      h.addEventListener('mousedown', function(e) {
        res.on=true; res.sx=e.clientX; res.sy=e.clientY;
        var r=el.getBoundingClientRect();
        res.ow=r.width; res.oh=r.height; res.ox=r.left; res.oy=r.top;
        el.style.transform='none';
        el.style.left=res.ox+'px'; el.style.top=res.oy+'px';
        _focus(el);
        e.preventDefault(); e.stopPropagation();
      });
      document.addEventListener('mousemove', function(e) {
        if (!res.on) return;
        var dx=e.clientX-res.sx, dy=e.clientY-res.sy;
        var nw=res.ow, nh=res.oh, nx=res.ox, ny=res.oy;
        if (dir.indexOf('e')!==-1)  nw=Math.max(MIN_W, res.ow+dx);
        if (dir.indexOf('s')!==-1)  nh=Math.max(MIN_H, res.oh+dy);
        if (dir.indexOf('w')!==-1){ nw=Math.max(MIN_W, res.ow-dx); nx=res.ox+(res.ow-nw); }
        if (dir.indexOf('n')!==-1){ nh=Math.max(MIN_H, res.oh-dy); ny=res.oy+(res.oh-nh); }
        el.style.width =nw+'px'; el.style.height=nh+'px';
        el.style.left  =nx+'px'; el.style.top   =ny+'px';
        el.style.maxWidth='none'; el.style.maxHeight='none';
      });
      document.addEventListener('mouseup', function() {
        if (!res.on) return;
        res.on=false;
        _persist(el, id);
      });
    });

    /* ── 클릭 시 최상위로 ── */
    el.addEventListener('mousedown', function() { _focus(el); });

    // Touch 지원 (모바일/태블릿)
    _addTouch(el, dragHandle, drag, id);
  }

  /* ── z-index 포커스 ──────────────────────────────────────────────────── */
  function _focus(el) {
    window._sqmZ = (window._sqmZ || 10100) + 1;
    el.style.zIndex = window._sqmZ;
    document.querySelectorAll('.sqm-win-focused').forEach(function(w){ w.classList.remove('sqm-win-focused'); });
    el.classList.add('sqm-win-focused');
  }

  /* ── localStorage 저장 ──────────────────────────────────────────────── */
  function _persist(el, id) {
    var r = el.getBoundingClientRect();
    _savePref(id, { x:Math.round(r.left), y:Math.round(r.top), w:Math.round(r.width), h:Math.round(r.height) });
  }

  /* ── 터치 드래그 지원 ────────────────────────────────────────────────── */
  function _addTouch(el, dragHandle, drag, id) {
    var t0 = null;
    dragHandle.addEventListener('touchstart', function(e) {
      if (e.touches.length !== 1) return;
      var t  = e.touches[0];
      t0     = {cx:t.clientX, cy:t.clientY};
      var r  = el.getBoundingClientRect();
      drag.ox=r.left; drag.oy=r.top;
      el.style.transform='none';
      el.style.left=r.left+'px'; el.style.top=r.top+'px';
    }, {passive:true});
    dragHandle.addEventListener('touchmove', function(e) {
      if (!t0||e.touches.length!==1) return;
      var t=e.touches[0];
      el.style.left=(drag.ox+(t.clientX-t0.cx))+'px';
      el.style.top =(drag.oy+(t.clientY-t0.cy))+'px';
      e.preventDefault();
    }, {passive:false});
    dragHandle.addEventListener('touchend', function() {
      if (!t0) return;
      t0=null; _persist(el, id);
    });
  }

  /* ── 대상 탐지 + 적용 ────────────────────────────────────────────────── */
  function _scan(root) {
    root = root || document;
    // ID 기반
    TARGET_IDS.forEach(function(id) {
      var el = document.getElementById(id);
      if (el) _applyManager(el, id);
    });
    // 클래스 기반
    var nodes = root.querySelectorAll ? root.querySelectorAll('.'+TARGET_CLASS) : [];
    Array.prototype.forEach.call(nodes, function(el) {
      var id = el.id || ('sqm-win-'+Math.random().toString(36).slice(2,7));
      if (!el.id) el.id = id;
      _applyManager(el, id);
    });
    // ★ 자동 감지 — body 직속 + position:fixed + 일정 크기 이상 + 닫기 버튼 보유
    _autoDetect();
  }

  /* ── ★ 자동 감지: 등록 안 된 모달도 일반 휴리스틱으로 잡아 관리 ──────── */
  function _autoDetect() {
    var children = document.body.children;
    for (var i = 0; i < children.length; i++) {
      var el = children[i];
      if (el.nodeType !== 1) continue;
      if (_processed.has(el)) continue;
      if (el.id && EXCLUDE_IDS[el.id]) continue;
      if (el.hasAttribute && el.hasAttribute('data-sqm-no-manage')) continue;
      var cs = window.getComputedStyle(el);
      if (cs.position !== 'fixed') continue;
      // 화면 전체 backdrop overlay는 _liberate가 inner를 옮기는 케이스 — 제외
      // (inset:0인 백드롭의 inner는 별도로 처리됨)
      var insetZero = (cs.inset === '0px' ||
        (cs.top === '0px' && cs.left === '0px' && cs.right === '0px' && cs.bottom === '0px'));
      if (insetZero) continue;  // backdrop overlay 자체는 리사이즈 불필요
      // 크기 휴리스틱 — 충분히 큰 패널/모달만
      var r = el.getBoundingClientRect();
      if (r.width < 280 || r.height < 160) continue;
      // 닫기 버튼이 있는가? (모달/패널의 가장 강한 신호)
      var hasClose = el.querySelector(
        '[id$="-close"],[id$="-cancel"],.modal-close,.btn-close,.close-btn,.sqm-close,'
        + 'button[onclick*="display"][onclick*="none"],button[onclick*=".remove("]'
      );
      // 또는 z-index가 충분히 높으면 모달성
      var z = parseInt(cs.zIndex, 10) || 0;
      if (!hasClose && z < 1000) continue;
      // 등록!
      var id = el.id || ('sqm-auto-' + Math.random().toString(36).slice(2, 7));
      if (!el.id) el.id = id;
      _log('autoDetect attach', id, 'w=' + Math.round(r.width), 'h=' + Math.round(r.height), 'z=' + z);
      _applyManager(el, id);
    }
  }

  /* ── MutationObserver: 동적 생성 창 자동 감지 ───────────────────────── */
  var _obs = new MutationObserver(function(mutations) {
    mutations.forEach(function(m) {
      m.addedNodes.forEach(function(node) {
        if (node.nodeType !== 1) return;
        // 직접 추가된 노드
        var nid = node.id;
        if (nid && TARGET_IDS.indexOf(nid) >= 0) {
          setTimeout(function(){ _applyManager(node, nid); }, 30);
          return;
        }
        if (node.classList && node.classList.contains(TARGET_CLASS)) {
          var wid = node.id || ('sqm-win-'+Math.random().toString(36).slice(2,7));
          if (!node.id) node.id = wid;
          setTimeout(function(){ _applyManager(node, wid); }, 30);
          return;
        }
        // ★ body 직속 동적 모달도 자동 감지
        if (node.parentElement === document.body) {
          setTimeout(_autoDetect, 50);
        }
        // 자손 중 대상 탐색
        TARGET_IDS.forEach(function(id) {
          var child = node.querySelector ? node.querySelector('#'+id) : null;
          if (child) setTimeout(function(){ _applyManager(child, id); }, 30);
        });
        if (node.querySelector) {
          Array.prototype.forEach.call(
            node.querySelectorAll('.'+TARGET_CLASS),
            function(child) {
              var wid = child.id || ('sqm-win-'+Math.random().toString(36).slice(2,7));
              if (!child.id) child.id = wid;
              setTimeout(function(){ _applyManager(child, wid); }, 30);
            }
          );
        }
      });
    });
  });

  /* ── 초기화 ──────────────────────────────────────────────────────────── */
  function _init() {
    _injectCSS();
    _scan();
    _installEscClose();
    _installGlobalCloseDelegation();
    _obs.observe(document.body, { childList:true, subtree:true });
    // 공개 API
    window.sqmModalManager = {
      apply:   _applyManager,
      scan:    _scan,
      prefs:   _loadPrefs,
      clear:   function() { localStorage.removeItem(STORAGE_KEY); },
      closeTop: function() {
        // 외부에서 호출 가능한 헬퍼
        var ev = new KeyboardEvent('keydown', { key: 'Escape', keyCode: 27 });
        document.dispatchEvent(ev);
      },
      version: 'v8.7.0-r11',
      // 진단/리셋 헬퍼
      resetPrefs: function() { localStorage.removeItem(STORAGE_KEY); _log('all prefs cleared'); },
      autoDetect: _autoDetect,
    };
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', _init);
  } else {
    _init();
  }

})();
