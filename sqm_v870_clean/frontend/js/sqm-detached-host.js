/* =======================================================================
   sqm-detached-host.js — SQM v8.7.1 분리 창 (popout.html) 호스트 스크립트
   =======================================================================
   역할
   ----
   1. URL ?key=<popout-key> 를 읽어 백엔드에서 초기 snapshot HTML fetch
   2. snapshot 을 #popout-content 에 주입 (script 태그는 무시)
   3. /api/popout/m2d/{key}/stream SSE 구독 — 메인에서 보내는 라이브 업데이트 처리
        - event.type === 'append'  → 지정 selector 에 innerHTML 추가
        - event.type === 'replace' → 지정 selector 의 innerHTML 교체
        - event.type === 'remove'  → 분리 창 닫기 (메인에서 강제 회수)
        - event.type === 'refresh' → snapshot 재로드
   4. 분리 창 안의 모든 클릭 이벤트를 가로채:
        - data-popout-action 또는 inline onclick="window.foo(...)" 호출 시
        - POST /api/popout/d2m/{key}  {type:'action', expr:'foo(...)'} 로 메인에 전송
        - 메인은 d2m SSE 구독 중이며 expr 을 자신의 컨텍스트에서 실행
   5. window 종료(beforeunload) 시 POST /api/popout/d2m/{key} {type:'close'}

   이 페이지는 메인 앱의 거대한 JS 번들을 로드하지 않으므로
   onclick="window.foo()" 의 foo 가 정의되어 있지 않다.
   따라서 모든 액션은 메인으로 라우팅한다.
   ======================================================================= */
(function () {
  'use strict';
  const params = new URLSearchParams(location.search);
  const KEY = (params.get('key') || '').trim();
  const TITLE = (params.get('title') || 'SQM Popout');
  document.title = TITLE + ' — 분리 창';

  const $status = document.getElementById('popout-status-text');
  const $bar    = document.getElementById('popout-statusbar');
  const $label  = document.getElementById('popout-key-label');
  const $body   = document.getElementById('popout-content');

  if ($label) $label.textContent = 'key=' + KEY;

  function setStatus(text, connected) {
    if ($status) $status.textContent = text;
    if ($bar) $bar.classList.toggle('connected', !!connected);
  }

  if (!KEY) {
    setStatus('❌ key 파라미터 없음', false);
    return;
  }

  /* ── 1) snapshot fetch + inject ─────────────────────────────────── */
  function fetchSnapshot() {
    setStatus('스냅샷 로드 중...', false);
    return fetch('/api/popout/snapshot/' + encodeURIComponent(KEY), {cache:'no-store'})
      .then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.json();
      })
      .then(function (d) {
        if (!d || !d.ok || !d.html) throw new Error('빈 snapshot');
        injectSnapshot(d.html);
        setStatus('연결됨 — 메인에서 라이브 업데이트 수신 중', true);
      })
      .catch(function (err) {
        console.error('[popout] snapshot 실패', err);
        setStatus('❌ 스냅샷 로드 실패: ' + (err.message || err), false);
      });
  }

  function injectSnapshot(html) {
    /* script 태그는 보안상 무시 (분리 창은 inert 표시 목적) */
    const safe = String(html).replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '');
    $body.innerHTML = safe;
    /* 헤더의 X 버튼 등 메인 전용 컨트롤 숨김 (data-popout-hide 속성) */
    $body.querySelectorAll('[data-popout-hide="1"]').forEach(function (el) {
      el.classList.add('sqm-popout-hide-in-detached');
    });
  }

  /* ── 2) action 라우팅 — inline onclick 등을 메인으로 dispatch ───── */
  // 인라인 onclick="..." 속성을 가로채기: capture phase 에서 잡고
  // 호출을 가로채 메인으로 전송. 단, native form/input 키 입력 등은 그대로 둔다.
  function handleClick(ev) {
    let el = ev.target;
    // closest 로 onclick 보유 조상 찾기 (button 안의 span 클릭 보정)
    while (el && el !== $body) {
      if (el.tagName === 'BUTTON' || el.tagName === 'A'
          || el.hasAttribute('onclick') || el.hasAttribute('data-popout-action')) {
        const action = el.getAttribute('data-popout-action')
                    || el.getAttribute('onclick');
        if (action && action.trim()) {
          ev.preventDefault();
          ev.stopPropagation();
          dispatchAction(action);
          return;
        }
      }
      el = el.parentElement;
    }
  }

  function handleInput(ev) {
    const el = ev.target;
    if (!el) return;
    const action = el.getAttribute('data-popout-input')
                || el.getAttribute('oninput')
                || el.getAttribute('onchange');
    if (!action) return;
    /* value 를 같이 보냄 — 메인에서 같은 id 의 element value 를 갱신해서 실행 */
    dispatchAction(action, {
      el_id: el.id || '',
      value: el.value,
    });
  }

  function dispatchAction(expr, extra) {
    const payload = Object.assign({type:'action', expr:expr}, extra || {});
    fetch('/api/popout/d2m/' + encodeURIComponent(KEY), {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload),
      keepalive: true,
    }).catch(function(_){});
  }

  $body.addEventListener('click', handleClick, true);
  $body.addEventListener('input', handleInput, true);
  $body.addEventListener('change', handleInput, true);

  /* ── 3) m2d SSE 구독 — 메인의 라이브 업데이트 처리 ──────────────── */
  let _es = null;
  function connectSSE() {
    try {
      if (_es) { try { _es.close(); } catch(_){} }
      _es = new EventSource('/api/popout/m2d/' + encodeURIComponent(KEY) + '/stream');
      _es.addEventListener('ready', function (e) {
        // 연결 ack
      });
      _es.addEventListener('message', function (e) {
        let ev;
        try { ev = JSON.parse(e.data); } catch (_) { return; }
        applyEvent(ev);
      });
      _es.onerror = function () {
        setStatus('재연결 중...', false);
        // EventSource 자체 재연결 메커니즘에 위임
      };
    } catch (err) {
      console.error('[popout] SSE 실패', err);
    }
  }

  function applyEvent(ev) {
    if (!ev || typeof ev !== 'object') return;
    switch (ev.type) {
      case 'append': {
        const el = ev.selector ? $body.querySelector(ev.selector) : $body;
        if (!el) return;
        el.insertAdjacentHTML('beforeend', ev.html || '');
        if (ev.scroll === 'bottom') el.scrollTop = el.scrollHeight;
        break;
      }
      case 'replace': {
        const el = ev.selector ? $body.querySelector(ev.selector) : $body;
        if (!el) return;
        el.innerHTML = ev.html || '';
        break;
      }
      case 'set-attr': {
        const el = ev.selector ? $body.querySelector(ev.selector) : null;
        if (!el || !ev.attr) return;
        if (ev.value === null) el.removeAttribute(ev.attr);
        else el.setAttribute(ev.attr, String(ev.value));
        break;
      }
      case 'refresh':
        fetchSnapshot();
        break;
      case 'close':
        try { window.close(); } catch (_) {}
        break;
      default:
        /* 미지원 type 무시 */
    }
  }

  /* ── 4) 종료 시 메인에 알림 ──────────────────────────────────────── */
  window.addEventListener('beforeunload', function () {
    try {
      navigator.sendBeacon(
        '/api/popout/d2m/' + encodeURIComponent(KEY),
        new Blob([JSON.stringify({type:'close'})], {type:'application/json'})
      );
    } catch (_) {}
  });

  /* ── 시작 ─────────────────────────────────────────────────────────── */
  fetchSnapshot().then(connectSSE);
})();
