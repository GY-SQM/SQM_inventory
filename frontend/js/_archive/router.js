// SQM v8.7.0
// 9개 사이드바 탭 전환 로직. 이전 페이지 unmount → 다음 mount

const PAGE_LOADERS = {
  dashboard:  () => import('./pages/dashboard.js'),
  inventory:  () => import('./pages/inventory.js'),
  allocation: () => import('./pages/allocation.js'),
  outbound:   () => import('./pages/outbound.js'),
  picked:     () => import('./pages/picked.js'),
  return:     () => import('./pages/return.js'),
  move:       () => import('./pages/move.js').catch(() => stubModule('move')),
  log:        () => import('./pages/log.js'),
  scan:       () => import('./pages/scan.js'),
  tonbag:     () => import('./pages/tonbag.js'),
};

function stubModule(name) {
  return {
    mount(container) {
      container.innerHTML = `
        <section class="page" data-page="${name}">
          <h2>${name}</h2>
          <div class="empty">준비 중 (Tier 3 이관 예정)</div>
        </section>`;
    },
    unmount() {},
  };
}

let currentPage = null;

export async function navigateTo(pageId, container) {
  const target = container || document.getElementById('page-container');
  if (!target) {
    console.error('[router] page-container not found');
    return;
  }
  try {
    if (currentPage?.unmount) currentPage.unmount();
    const loader = PAGE_LOADERS[pageId] || (() => Promise.resolve(stubModule(pageId)));
    const mod = await loader();
    await (mod.mount || (() => {}))(target);
    currentPage = mod;

    // 사이드바 active 표시
    document.querySelectorAll('[data-route]').forEach(el => {
      el.classList.toggle('active', el.dataset.route === pageId);
    });
    // URL hash 동기화
    if (location.hash.slice(1) !== pageId) location.hash = pageId;
    // localStorage 에 마지막 탭 저장
    try { localStorage.setItem('sqm_last_tab', pageId); } catch {}
  } catch (e) {
    console.error('[router] navigate failed', e);
    target.innerHTML = `<div class="empty">페이지 로드 실패: ${e.message}</div>`;
  }
}

export function initRouter() {
  // [fix F-1+F-2] data-route 클릭 바인딩 제거 — sqm-inline.js bindAll()이 단독 권위 라우터
  // router.js의 navigateTo(ES module 방식)는 sqm-core.js renderPage와 충돌하므로 비활성화
  // hashchange 이벤트만 sqm-inline.js의 hashchange 핸들러와 중복되지 않게 등록하지 않음
  // 이 함수는 하위 호환을 위해 존재하나 실질 동작은 없음
  console.info('[SQM router.js] initRouter: 클릭 바인딩 비활성화 (sqm-inline.js 단독 라우팅)');
}
