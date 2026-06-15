// SQM v8.7.1
console.info('[SQM v8.7.1] main.js 로드 시작');

// 모듈 import — 단계별로 try/catch
let mods = {};
async function loadModules() {
  const items = [
    ['toast',   () => import('./toast.js')],
    ['apicli',  () => import('./api-client.js')],
    ['router',  () => import('./router.js')],
    ['menubar', () => import('./handlers/menubar.js')],
    ['toolbar', () => import('./handlers/toolbar.js')],
    ['topbar',  () => import('./handlers/topbar.js')],
    ['short',   () => import('./shortcuts.js')],
    ['state',   () => import('./state.js')],
    ['alerts',  () => import('./components/alerts.js')],
    ['status',  () => import('./components/statusbar.js')],
    ['refresh', () => import('./components/auto_refresh.js')],
  ];
  for (const [name, fn] of items) {
    try {
      mods[name] = await fn();
      console.info(`[SQM] OK 모듈: ${name}`);
    } catch (e) {
      mods[name] = null;
      console.error(`[SQM] FAIL 모듈: ${name}`, e);
      if (name === 'router') {
        reportRouterProblem('라우터 모듈 로드 실패 — 탭 전환 기능이 제한될 수 있습니다.', e);
      }
    }
  }
}

function reportRouterProblem(message, error) {
  window.SQM = window.SQM || {};
  window.SQM.routerInitFailed = true;
  window.SQM.routerInitError = String(error?.message || error || message);
  console.error('[SQM] router init failed:', message, error || '');

  const show = mods.toast?.showToast || window.showToast;
  if (typeof show === 'function') show('error', message);

  const target = document.getElementById('page-container');
  if (target && !document.getElementById('router-error-banner')) {
    const banner = document.createElement('div');
    banner.id = 'router-error-banner';
    banner.className = 'empty router-error-banner';
    banner.style.cssText = 'color:var(--status-error);padding:10px 12px;border-bottom:1px solid var(--panel-border);';
    banner.textContent = message;
    target.prepend(banner);
  }
}

function initRouterSafely() {
  const inlineRouterAvailable =
    typeof window.SQM?.renderPage === 'function' || typeof window.renderPage === 'function';
  if (!mods.router) {
    reportRouterProblem(
      inlineRouterAvailable
        ? 'router.js 모듈 누락 — 기존 라우터로 계속 진행합니다.'
        : 'router.js 모듈 누락 — 화면 전환 기능이 제한될 수 있습니다.'
    );
    return;
  }
  if (typeof mods.router.initRouter !== 'function') {
    reportRouterProblem(
      inlineRouterAvailable
        ? 'initRouter 없음 — 기존 라우터로 계속 진행합니다.'
        : 'initRouter 없음 — 화면 전환 기능이 제한될 수 있습니다.'
    );
    return;
  }
  try {
    mods.router.initRouter();
  } catch (e) {
    reportRouterProblem(
      inlineRouterAvailable
        ? '라우터 초기화 실패 — 기존 라우터로 계속 진행합니다.'
        : '라우터 초기화 실패 — 화면 전환 기능이 제한될 수 있습니다.',
      e
    );
  }
}

// fail-safe 메뉴 핸들러 — 모듈 로드 전에도 메뉴 클릭이 죽지 않게
function installFailSafe() {
  document.querySelectorAll('[data-action]').forEach(el => {
    el.addEventListener('click', (ev) => {
      const action = el.dataset.action;
      // 진짜 핸들러가 바인딩됐으면 그쪽이 처리, 아니면 토스트라도
      if (!el.dataset._bound) {
        ev.preventDefault();
        const msg = `[준비 중]${el.textContent.trim()} (action=${action})`;
        if (window.showToast) window.showToast('info', msg);
        else console.info(msg);
      }
    });
  });
  // 사이드바 라우트도 fail-safe
  document.querySelectorAll('[data-route]').forEach(el => {
    el.addEventListener('click', (ev) => {
      const hasRouteBinding = el.dataset._bound || el.dataset._sqmBound ||
        typeof window.SQM?.renderPage === 'function' || typeof window.renderPage === 'function';
      if (!hasRouteBinding) {
        ev.preventDefault();
        document.querySelectorAll('[data-route]').forEach(e => e.classList.remove('active'));
        el.classList.add('active');
        const target = document.getElementById('page-container');
        if (target) target.innerHTML = '<div class="empty">' + el.textContent.trim() + ' 페이지 (모듈 로딩 대기...)</div>';
      }
    });
  });
  console.info('[SQM] fail-safe 핸들러 설치 완료');
}

async function boot() {
  console.info('[SQM v8.7.1] boot 시작');
  installFailSafe();
  await loadModules();
  try { mods.state?.initStatePersistence?.(); } catch (e) { console.error('state init', e); }
  const alertsEl = document.getElementById('alerts-container');
  if (alertsEl && mods.alerts?.mountAlerts) {
    try { await mods.alerts.mountAlerts(alertsEl); } catch (e) { console.error('alerts', e); }
  }
  const statusbarEl = document.getElementById('statusbar-container');
  if (statusbarEl && mods.status?.mountStatusbar) {
    try { await mods.status.mountStatusbar(statusbarEl); } catch (e) { console.error('statusbar', e); }
  }
  try { mods.menubar?.bindMenubar?.(document); } catch (e) { console.error('menubar bind', e); }
  try { mods.toolbar?.bindToolbar?.(document); } catch (e) { console.error('toolbar bind', e); }
  try { mods.topbar?.bindTopbar?.(document); } catch (e) { console.error('topbar bind', e); }
  try { mods.short?.initShortcuts?.(); } catch (e) { console.error('shortcuts', e); }
  initRouterSafely();
  try { mods.refresh?.startAutoRefresh?.(); } catch (e) { console.error('autorefresh', e); }
  console.info('[SQM v8.7.1] boot 완료');
  console.info('  로드된 모듈:', Object.keys(mods).filter(k => mods[k]).join(', '));
  console.info('  실패한 모듈:', Object.keys(mods).filter(k => !mods[k]).join(', ') || '없음');
  // 콘솔에서 즉시 확인 가능하도록 전역 노출
  window.SQM = window.SQM || {};
  window.SQM.modules = mods;
  window.SQM.bootComplete = true;
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', boot);
} else {
  boot();
}
