/* =======================================================================
   sqm-popout.js — SQM v8.7.1 메인 창의 "팝아웃" 기능
   =======================================================================
   외부 노출
   --------
   - window.sqmPopOut(panelId, opts)      : 패널을 OS 분리 창으로 팝아웃
   - window.sqmAddPopOutBtn(panel, header, opts) : 패널 헤더에 🪟 버튼 자동 추가
   - window.sqmPopOutBroadcast(key, ev)   : 분리 창에 이벤트 푸시 (라이브 업데이트)
   - window.sqmPopOutIsActive(key)        : 해당 key 가 현재 분리 창으로 활성인지

   opts (선택)
   -----------
   - key       : 채널 key (default: panelId)
   - title     : OS 창 제목 (default: header text)
   - width/height
   - liveSync  : true 면 메인 패널을 숨기고 라이브 업데이트만 (parse-log 용)
                 false 면 메인 패널도 그대로 두고 단순 복제 (read-only 분리 창)
   - onClose   : 분리 창 닫혔을 때 호출 (예: 메인 패널 다시 보이기)

   요구사항
   --------
   - 백엔드 /api/popout/* 라우터 동작 중
   - pywebview.api.open_detached_window 가능 (PyWebView 환경)
   - 일반 브라우저 환경에서는 window.open() 으로 폴백
   ======================================================================= */
(function () {
  'use strict';
  if (window.__SQM_POPOUT_INSTALLED__) return;
  window.__SQM_POPOUT_INSTALLED__ = true;

  // 활성 팝아웃 추적: key → {panelId, restorer, listener, eventSource, opts}
  const _active = Object.create(null);

  function _post(path, body) {
    return fetch(path, {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(body || {}),
      cache: 'no-store',
    }).then(function(r){ return r.json().catch(function(){return{};}); })
      .catch(function(){ return {}; });
  }

  /* ── 분리 창에 보낼 안전한 outerHTML 생성 ───────────────────────────── */
  function _serializePanel(panel) {
    /* clone 후 메인 전용 컨트롤(닫기 X 버튼)을 data-popout-hide=1 처리 */
    const c = panel.cloneNode(true);
    const panelId = panel.id || '';
    /* 이 패널 자체의 display='none' 을 시도하는 모든 버튼 = "닫기" → 분리 창에선 숨김
       (분리 창은 OS X 로 닫는다. 닫기 클릭이 메인에 라우팅되면 메인 패널만 숨고 OS 창은 살아있어 혼란) */
    const closePatterns = panelId
      ? [
          new RegExp("getElementById\\([\\\"']" + panelId.replace(/[-/\\^$*+?.()|[\]{}]/g, '\\$&') + "[\\\"']\\)\\.style\\.display\\s*=\\s*[\\\"']none[\\\"']"),
        ]
      : [];
    c.querySelectorAll('button').forEach(function (btn) {
      const inlOnclick = btn.getAttribute('onclick') || '';
      const txt = (btn.textContent || '').trim();
      let shouldHide = false;
      /* 1) 패턴 매치 */
      if (closePatterns.some(function(re){ return re.test(inlOnclick); })) shouldHide = true;
      /* 2) X 모양 텍스트 */
      if (!shouldHide && (txt === '×' || txt === '✕' || txt === '✖')
          && /display\s*=\s*['"]none['"]/.test(inlOnclick)) shouldHide = true;
      /* 3) 텍스트 + display none 콤보 (예: "❌ 닫기") */
      if (!shouldHide && /닫기|취소|close|cancel/i.test(txt)
          && /display\s*=\s*['"]none['"]/.test(inlOnclick)) shouldHide = true;
      if (shouldHide) btn.setAttribute('data-popout-hide', '1');
    });
    /* 자기 자신을 가리키는 popout 버튼은 숨김 */
    c.querySelectorAll('.sqm-popout-btn').forEach(function (b) {
      b.setAttribute('data-popout-hide', '1');
    });
    /* 리사이즈 핸들 div 제거 */
    c.querySelectorAll('.sqm-rh').forEach(function (h) { h.remove(); });
    /* 드래그 힌트 (분리 창에선 무의미) */
    c.querySelectorAll('#sqm-modal-drag-hint').forEach(function (h) {
      h.setAttribute('data-popout-hide', '1');
    });
    return c.outerHTML;
  }

  /* ── 분리 창 → 메인 d2m SSE 구독 (close/action 처리) ─────────────── */
  function _subscribeD2M(key) {
    let es;
    try {
      es = new EventSource('/api/popout/d2m/' + encodeURIComponent(key) + '/stream');
    } catch (err) {
      console.error('[popout] d2m subscribe 실패', err);
      return null;
    }
    es.addEventListener('message', function (e) {
      let ev;
      try { ev = JSON.parse(e.data); } catch(_){ return; }
      _handleD2M(key, ev);
    });
    es.onerror = function () { /* 자동 재연결에 위임 */ };
    return es;
  }

  function _handleD2M(key, ev) {
    if (!ev || typeof ev !== 'object') return;
    const ctx = _active[key];
    switch (ev.type) {
      case 'close':
        _closeLocal(key);
        break;
      case 'action':
        /* 분리 창에서 전달된 onclick expr 을 메인 컨텍스트에서 실행 */
        try {
          /* 분리 창에서 input 변경이면 같은 id 의 메인 element 값을 동기화한 뒤 실행 */
          if (ev.el_id) {
            const mainEl = document.getElementById(ev.el_id);
            if (mainEl && 'value' in mainEl && typeof ev.value !== 'undefined') {
              mainEl.value = ev.value;
            }
          }
          /* 인디렉트 eval(글로벌 스코프) — window.foo() 형태만 신뢰 */
          (0, eval)(String(ev.expr || ''));
        } catch (err) {
          console.warn('[popout] action eval 실패:', ev.expr, err);
        }
        break;
    }
  }

  function _closeLocal(key) {
    const ctx = _active[key];
    if (!ctx) return;
    try { if (ctx.eventSource) ctx.eventSource.close(); } catch(_){}
    /* 분리 창 OS 측 종료 명령 (pywebview) */
    try {
      if (window.pywebview && window.pywebview.api && window.pywebview.api.close_detached_window) {
        window.pywebview.api.close_detached_window(key);
      }
    } catch(_){}
    /* 메인 패널 복원 */
    try { if (typeof ctx.restorer === 'function') ctx.restorer(); } catch(_){}
    /* 채널 클리어 */
    _post('/api/popout/clear/' + encodeURIComponent(key), {});
    delete _active[key];
  }

  /* ── 메인 → 분리 창 라이브 이벤트 푸시 ────────────────────────────── */
  function broadcast(key, event) {
    if (!_active[key]) return;
    return _post('/api/popout/m2d/' + encodeURIComponent(key), event);
  }

  /* ── 핵심: 패널 팝아웃 ────────────────────────────────────────────── */
  function popOut(panelId, opts) {
    opts = opts || {};
    const panel = (typeof panelId === 'string') ? document.getElementById(panelId) : panelId;
    if (!panel) {
      console.warn('[popout] panel not found:', panelId);
      return;
    }
    const key = opts.key || panel.id || ('popout-' + Date.now());
    if (_active[key]) {
      /* 이미 열려있으면 포커스만 (pywebview show) */
      try {
        if (window.pywebview && window.pywebview.api && window.pywebview.api.open_detached_window) {
          /* 같은 key 로 재요청 = show */
          window.pywebview.api.open_detached_window(key, _active[key].title || key,
            _active[key].url || ('/popout.html?key='+encodeURIComponent(key)),
            opts.width || 900, opts.height || 700);
        }
      } catch(_){}
      return;
    }

    const title = opts.title || _detectTitle(panel) || ('SQM — ' + key);
    const html = _serializePanel(panel);
    const screenW = (window.screen && window.screen.availWidth) || window.innerWidth || 1400;
    const screenH = (window.screen && window.screen.availHeight) || window.innerHeight || 900;
    const w = opts.width  || Math.min(1500, Math.max(900, Math.round(screenW * 0.82)));
    const h = opts.height || Math.min(950,  Math.max(700, Math.round(screenH * 0.84)));

    /* 1) 스냅샷 저장 */
    _post('/api/popout/snapshot/' + encodeURIComponent(key), {html: html}).then(function () {
      /* 2) d2m 구독 (분리 창 close/action 수신) */
      const es = _subscribeD2M(key);
      /* 3) 메인 패널 처리 (liveSync 모드면 숨김) */
      let restorer = null;
      if (opts.liveSync !== false) {
        const oldDisplay = panel.style.display;
        panel.style.display = 'none';
        restorer = function () { panel.style.display = oldDisplay || 'flex'; };
      } else {
        /* read-only 모드 — 메인 패널 유지, 시각적 표시만 */
        panel.classList.add('sqm-popped-out');
        restorer = function () { panel.classList.remove('sqm-popped-out'); };
      }

      /* 4) 분리 창 열기 (PyWebView API 우선, 폴백: window.open) */
      /* PyWebView create_window 는 절대 URL 필요 — origin 또는 SQM_API_BASE 사용 */
      const base = (window.location && window.location.origin)
                || (window.SQM_API_BASE || '');
      const url = base + '/popout.html?key=' + encodeURIComponent(key)
                + '&title=' + encodeURIComponent(title);
      let openedViaPyWebView = false;
      try {
        if (window.pywebview && window.pywebview.api && window.pywebview.api.open_detached_window) {
          window.pywebview.api.open_detached_window(key, title, url, w, h);
          openedViaPyWebView = true;
        }
      } catch (err) {
        console.warn('[popout] pywebview open_detached_window 실패, 폴백', err);
      }
      let popupRef = null;
      if (!openedViaPyWebView) {
        try {
          popupRef = window.open(url, '_blank',
            'width=' + w + ',height=' + h + ',resizable=yes,toolbar=no,location=no');
        } catch (err) {
          console.error('[popout] window.open 실패', err);
        }
      }

      _active[key] = {
        panelId: panel.id,
        title: title,
        url: url,
        eventSource: es,
        restorer: restorer,
        popupRef: popupRef,
        opts: opts,
      };

      /* 5) onOpen 콜백 (liveSync 초기 데이터 푸시 등에 사용) */
      if (typeof opts.onOpen === 'function') {
        try { opts.onOpen(key); } catch(err){ console.warn('[popout] onOpen err', err); }
      }

      /* 토스트 */
      try {
        if (typeof window.showToast === 'function') {
          window.showToast('info', '🪟 ' + title + ' — 별도 창으로 이동');
        }
      } catch(_){}
    }).catch(function (err) {
      console.error('[popout] snapshot 저장 실패', err);
    });
  }

  function _detectTitle(panel) {
    /* 헤더 안의 첫 span/strong/h2 텍스트를 제목으로 */
    const hdr = panel.querySelector('[id$="-hdr"]') || panel.querySelector('header');
    if (hdr) {
      const cand = hdr.querySelector('span,strong,h1,h2,h3,h4');
      if (cand) {
        const t = (cand.textContent || '').trim();
        if (t) return t;
      }
      const t = (hdr.textContent || '').trim();
      if (t) return t.slice(0, 60);
    }
    return panel.id || '';
  }

  /* ── 헤더에 🪟 버튼 자동 추가 ─────────────────────────────────────── */
  function addPopOutBtn(panel, header, opts) {
    if (!panel || !header) return;
    if (header.querySelector('.sqm-popout-btn')) return; /* 중복 방지 */
    const btn = document.createElement('button');
    btn.className = 'sqm-popout-btn';
    btn.type = 'button';
    btn.title = '이 화면을 메인 창에 갇히지 않는 별도 창으로 띄웁니다 (크게 보거나 다른 모니터로 이동 가능)';
    // ★ 발견성 개선: 아이콘만 있던 버튼에 글자 라벨 + accent 강조 → 현장에서 바로 눈에 띄게
    btn.innerHTML = '🪟 크게 보기';
    btn.style.cssText =
      'background:rgba(79,195,247,.12);border:1px solid var(--accent,#4fc3f7);'
      + 'border-radius:5px;cursor:pointer;color:var(--accent,#4fc3f7);'
      + 'font-size:12px;font-weight:600;line-height:1;padding:4px 9px;margin-right:6px;'
      + 'white-space:nowrap;transition:all .12s;';
    btn.onmouseenter = function () {
      btn.style.background = 'var(--accent,#4fc3f7)';
      btn.style.color = '#04121f';
    };
    btn.onmouseleave = function () {
      btn.style.background = 'rgba(79,195,247,.12)';
      btn.style.color = 'var(--accent,#4fc3f7)';
    };
    btn.onclick = function (e) {
      e.stopPropagation();
      e.preventDefault();
      popOut(panel, opts || {});
    };
    /* 헤더에서 닫기 X 바로 앞에 삽입 (X 버튼이 마지막이라 가정) */
    const closeBtn = Array.prototype.slice.call(header.querySelectorAll('button')).find(function(b){
      const t = (b.textContent||'').trim();
      return t === '×' || t === '✕' || t === '✖';
    });
    if (closeBtn) header.insertBefore(btn, closeBtn);
    else header.appendChild(btn);
  }

  /* ── exports ──────────────────────────────────────────────────────── */
  window.sqmPopOut = popOut;
  window.sqmAddPopOutBtn = addPopOutBtn;
  window.sqmPopOutBroadcast = broadcast;
  window.sqmPopOutIsActive = function (key) { return !!_active[key]; };
  window.sqmPopOutCloseAll = function () {
    Object.keys(_active).forEach(_closeLocal);
  };
})();
