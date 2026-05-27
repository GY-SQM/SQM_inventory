/* =======================================================================
   SQM Inventory - sqm-util-modal.js — 모달 인프라 (드래그/리사이즈)
   Extracted from sqm-inline.js (Phase B-S8) — 2026-05-23
   Source: sqm-inline.js line 2083-2217 (135줄) + line 4812-4813 잔재

   주요 함수:
   - _bringToFront, _makeDraggableResizable: 모달 z-index/드래그/리사이즈
   - ensureModal, showDataModal: 모달 표시
   - _sqmSetModalTitleBar 등: 타이틀바 동기화

   외부 공유: window._sqmZ (다른 JS 파일도 사용)
   외부 노출: showDataModal/_makeDraggableResizable/_bringToFront/_sqmSetModalTitleBar
   ======================================================================= */
(function () {
  'use strict';
  if (window.__SQM_UTIL_MODAL_INSTALLED__) return;
  window.__SQM_UTIL_MODAL_INSTALLED__ = true;

  /* ===================================================
     8. MODAL — 드래그/리사이즈 지원 (2026-04-27)
     =================================================== */
  window._sqmZ = window._sqmZ || 10100;
  var _zFloatTop = window._sqmZ;  // IIFE 내부에서도 사용 가능하도록 유지
  function _bringToFront(el) { el.style.zIndex = ++(window._sqmZ); _zFloatTop = window._sqmZ; }
  // 전역 노출 (인라인 이벤트에서 접근 가능)
  window._bringToFront = _bringToFront;

  function _makeDraggableResizable(el, dragBar) {
    var drag = {on:false, sx:0, sy:0, ox:0, oy:0};
    dragBar.style.cursor = 'move';
    el.addEventListener('mousedown', function(){ _bringToFront(el); });
    dragBar.addEventListener('mousedown', function(e){
      if (e.target.tagName === 'BUTTON') return;
      drag.on = true;
      drag.sx = e.clientX; drag.sy = e.clientY;
      var r = el.getBoundingClientRect();
      drag.ox = r.left; drag.oy = r.top;
      el.style.transform = 'none';
      el.style.left = drag.ox + 'px'; el.style.top = drag.oy + 'px';
      e.preventDefault();
    });
    document.addEventListener('mousemove', function(e){
      if (!drag.on) return;
      el.style.left = Math.max(0, drag.ox + (e.clientX - drag.sx)) + 'px';
      el.style.top  = Math.max(0, drag.oy + (e.clientY - drag.sy)) + 'px';
    });
    document.addEventListener('mouseup', function(){ drag.on = false; });
    ['n','s','e','w','ne','nw','se','sw'].forEach(function(d){
      var h = document.createElement('div');
      h.className = 'sqm-rh sqm-rh-' + d;
      el.appendChild(h);
      var res = {on:false, sx:0, sy:0, ow:0, oh:0, ox:0, oy:0};
      h.addEventListener('mousedown', function(e){
        res.on=true; res.sx=e.clientX; res.sy=e.clientY;
        var r=el.getBoundingClientRect();
        res.ow=r.width; res.oh=r.height; res.ox=r.left; res.oy=r.top;
        el.style.transform='none';
        el.style.left=res.ox+'px'; el.style.top=res.oy+'px';
        e.preventDefault(); e.stopPropagation();
      });
      document.addEventListener('mousemove', function(e){
        if (!res.on) return;
        var dx=e.clientX-res.sx, dy=e.clientY-res.sy;
        var nw=res.ow, nh=res.oh, nx=res.ox, ny=res.oy;
        if (d.indexOf('e')!==-1)  nw=Math.max(400,res.ow+dx);
        if (d.indexOf('s')!==-1)  nh=Math.max(200,res.oh+dy);
        if (d.indexOf('w')!==-1){ nw=Math.max(400,res.ow-dx); nx=res.ox+(res.ow-nw); }
        if (d.indexOf('n')!==-1){ nh=Math.max(200,res.oh-dy); ny=res.oy+(res.oh-nh); }
        el.style.width=nw+'px'; el.style.height=nh+'px';
        el.style.left=nx+'px';  el.style.top=ny+'px';
      });
      document.addEventListener('mouseup', function(){ res.on=false; });
    });
  }

  function _sqmExtractModalHeadingText(html) {
    if (!html || typeof html !== 'string') return '';
    var m = html.match(/<h([123])[^>]*>([\s\S]*?)<\/h\1>/i);
    if (!m) return '';
    var tmp = document.createElement('div');
    tmp.innerHTML = m[2];
    var txt = (tmp.textContent || '').replace(/\s+/g, ' ').trim();
    if (txt.length > 72) txt = txt.slice(0, 69) + '…';
    return txt;
  }
  function _sqmSyncModalHeaderFromContent() {
    var c = document.getElementById('sqm-modal-content');
    var t = document.getElementById('sqm-modal-title');
    if (!c || !t) return;
    var ex = _sqmExtractModalHeadingText(c.innerHTML);
    t.textContent = ex || 'SQM';
  }
  window._sqmSyncModalHeaderFromContent = _sqmSyncModalHeaderFromContent;
  window._sqmSetModalTitleBar = function(text) {
    var el = document.getElementById('sqm-modal-title');
    if (!el || text == null) return;
    var s = String(text).trim();
    if (!s) return;
    el.textContent = s.length > 80 ? s.slice(0, 77) + '…' : s;
  };

  function ensureModal() {
    var m=document.getElementById('sqm-modal');
    if (m) {
      if (!document.getElementById('sqm-modal-title')) {
        var hdr = document.getElementById('sqm-modal-header');
        if (hdr) {
          hdr.innerHTML =
            '<span id="sqm-modal-title">SQM</span>'
            + '<span id="sqm-modal-drag-hint" title="이 줄을 드래그하면 창 이동, 바깥 모서리를 잡으면 크기 조절">⋮⋮ 이동 · 크기</span>'
            + '<button type="button" onclick="document.getElementById(\'sqm-modal\').style.display=\'none\'" style="position:absolute;top:3px;right:10px;background:none;border:none;font-size:1.4rem;cursor:pointer;color:var(--text-muted);">&#x2715;</button>';
        }
      }
      return m;
    }
    m=document.createElement('div');
    m.id='sqm-modal';
    m.style.cssText='display:none;position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:9999;';
    m.innerHTML='<div id="sqm-modal-inner" style="background:var(--bg-card);border-radius:8px;width:min(1280px,92vw);max-width:92vw;min-height:200px;max-height:88vh;position:fixed;top:65px;left:50%;transform:translateX(-50%);overflow:visible;display:flex;flex-direction:column;">'
      +'<div id="sqm-modal-header" onmousedown="(function(){var mi=document.getElementById(\'sqm-modal-inner\');if(mi)mi.style.zIndex=++(window._sqmZ);})()" style="flex-shrink:0;cursor:move;user-select:none;background:var(--bg-hover,rgba(0,0,0,.06));border-radius:8px 8px 0 0;border-bottom:1px solid var(--panel-border);padding:5px 48px 5px 12px;display:flex;align-items:center;gap:8px;min-height:28px;position:relative;">'
      +'<span id="sqm-modal-title">SQM</span>'
      +'<span id="sqm-modal-drag-hint" title="이 줄을 드래그하면 창 이동, 바깥 모서리를 잡으면 크기 조절">⋮⋮ 이동 · 크기</span>'
      +'<button type="button" onclick="document.getElementById(\'sqm-modal\').style.display=\'none\'" style="position:absolute;top:3px;right:10px;background:none;border:none;font-size:1.4rem;cursor:pointer;color:var(--text-muted);">&#x2715;</button>'
      +'</div>'
      +'<div id="sqm-modal-content" style="flex:1 1 auto;overflow:auto;padding:16px 20px;min-height:100px;"></div>'
      +'</div>';
    document.body.appendChild(m);
    _makeDraggableResizable(
      document.getElementById('sqm-modal-inner'),
      document.getElementById('sqm-modal-header')
    );
    return m;
  }

  function showDataModal(title, html) {
    if (html === undefined && typeof title === 'string') {
      html = title;
      title = '';
    }
    html = html == null ? '' : String(html);
    var explicit = (title != null && String(title).trim()) ? String(title).trim() : '';
    ensureModal().style.display = 'block';
    document.getElementById('sqm-modal-content').innerHTML = html;
    var barEl = document.getElementById('sqm-modal-title');
    if (barEl) {
      if (explicit) {
        barEl.textContent = explicit.length > 80 ? explicit.slice(0, 77) + '…' : explicit;
      } else {
        _sqmSyncModalHeaderFromContent();
      }
    }
    return document.getElementById('sqm-modal');
  }

  // 글로벌 노출 (sqm-inline.js 기존 호출 호환 + 다른 파일 의존성)
  window.showDataModal = showDataModal;
  window._makeDraggableResizable = _makeDraggableResizable;
})();
