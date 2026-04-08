import { useState, useEffect, useCallback, useRef, createContext, useContext } from 'react';
import { BrowserRouter, Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import MenuBar from './components/MenuBar';
import LotDetailModal from './components/LotDetailModal';
import InboundModal from './components/InboundModal';
import OutboundModal from './components/OutboundModal';
import SearchModal from './components/SearchModal';
import DashboardPage from './pages/DashboardPage';
import InventoryPage from './pages/InventoryPage';
import TonbagPage from './pages/TonbagPage';
import AllocationPage from './pages/AllocationPage';
import PickedPage from './pages/PickedPage';
import SoldPage from './pages/SoldPage';
import OutboundPage from './pages/OutboundPage';
import MovePage from './pages/MovePage';
import ScanPage from './pages/ScanPage';
import LogPage from './pages/LogPage';
import SummaryPage from './pages/SummaryPage';
import CargoOverviewPage from './pages/CargoOverviewPage';
import ReturnPage from './pages/ReturnPage';
import IntegrityPage from './pages/IntegrityPage';
import DoUpdateModal from './components/DoUpdateModal';
import AllocationInputModal from './components/AllocationInputModal';
import OutboundHistoryPage from './pages/OutboundHistoryPage';
import SettingsPage from './pages/SettingsPage';
import LocationMappingModal from './components/LocationMappingModal';
import ReportsPage from './pages/ReportsPage';
import ProductMasterPage from './pages/ProductMasterPage';
import ApprovalPage from './pages/ApprovalPage';
import AiChatPage from './pages/AiChatPage';
import HelpPage from './pages/HelpPage';
import TemplatesPage from './pages/TemplatesPage';
import DevPage from './pages/DevPage';
import { exportCsv } from './api/writeApi';

// ── 사이드바 탭 정의 (v864 동일 순서/색상) ─────────────────────────────────
const SIDEBAR_TABS = [
  { key: 'inventory',   icon: '📦', label: '재고 조회',  path: '/inventory',       color: '#4ade80' },
  { key: 'tonbag',      icon: '🎒', label: '톤백',       path: '/tonbag',           color: '#f59e0b' },
  { key: 'allocation',  icon: '📋', label: '판매 배정',  path: '/allocation',       color: '#facc15' },
  { key: 'picked',      icon: '🚛', label: '화물 결정',  path: '/picked',           color: '#a78bfa' },
  { key: 'outbound',    icon: '📤', label: '출고',       path: '/outbound',         color: '#38bdf8' },
  { key: 'return',      icon: '🔄', label: '반품',       path: '/return',           color: '#f87171' },
  { key: 'move',        icon: '🔀', label: '이동',       path: '/move',             color: '#22d3ee' },
  null, // 구분선
  { key: 'dashboard',   icon: '📊', label: '대시보드',   path: '/',                 color: '#00e676' },
  { key: 'log',         icon: '📝', label: '로그',       path: '/log',              color: '#94a3b8' },
  { key: 'scan',        icon: '📷', label: '스캔',       path: '/scan',             color: '#fb923c' },
  null, // 구분선
  { key: 'cargo',       icon: '📋', label: '총괄 재고',  path: '/cargo',            color: '#60a5fa' },
];

// ── Toast 컴포넌트 ──────────────────────────────────────────────────────────
function Toast({ message, onHide }) {
  useEffect(() => {
    if (!message) return;
    const t = setTimeout(onHide, 2500);
    return () => clearTimeout(t);
  }, [message, onHide]);
  if (!message) return null;
  return (
    <div style={{
      position: 'fixed', bottom: 28, left: '50%', transform: 'translateX(-50%)',
      background: '#1e293b', color: '#f1f5f9', padding: '10px 24px',
      borderRadius: 8, fontSize: 13, zIndex: 9999,
      boxShadow: '0 4px 16px rgba(0,0,0,0.4)', pointerEvents: 'none',
      border: '1px solid #334155',
    }}>
      {message}
    </div>
  );
}

// ── 사이드바 컴포넌트 ───────────────────────────────────────────────────────
function Sidebar({ dark, toggleTheme, fontScale, increaseFontScale, decreaseFontScale, resetFontScale, devMode, toggleDevMode }) {
  const navigate = useNavigate();
  const location = useLocation();

  const activeKey = (() => {
    const p = location.pathname;
    if (p === '/') return 'dashboard';
    const found = SIDEBAR_TABS.find(t => t && t.path !== '/' && p.startsWith(t.path));
    return found ? found.key : 'dashboard';
  })();

  return (
    <aside data-sqm-sidebar="" style={{
      width: 72, minWidth: 72, background: 'var(--nav-bg)',
      borderRight: '1px solid var(--nav-border)',
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      padding: '10px 0', overflowY: 'auto', flexShrink: 0,
    }}>
      {SIDEBAR_TABS.map((tab, idx) => {
        if (tab === null) {
          return <div key={`sep-${idx}`} style={{ width: 40, height: 1, background: 'var(--nav-border)', margin: '6px auto' }} />;
        }
        const isActive = activeKey === tab.key;
        return (
          <button
            key={tab.key}
            onClick={() => navigate(tab.path)}
            title={tab.label}
            style={{
              display: 'flex', flexDirection: 'column', alignItems: 'center',
              width: '100%', padding: '8px 4px', cursor: 'pointer',
              border: 'none', background: isActive ? 'var(--nav-bg-active)' : 'none',
              borderLeft: `3px solid ${isActive ? tab.color : 'transparent'}`,
              marginBottom: 2, transition: 'all 0.15s',
            }}
            onMouseEnter={e => { if (!isActive) e.currentTarget.style.background = 'var(--nav-bg-hover)'; }}
            onMouseLeave={e => { if (!isActive) e.currentTarget.style.background = 'none'; }}
          >
            <span style={{ fontSize: 18, lineHeight: 1 }}>{tab.icon}</span>
            <span style={{
              fontSize: 9, marginTop: 3,
              color: isActive ? tab.color : '#64748b',
              fontWeight: isActive ? 700 : 400,
            }}>{tab.label}</span>
          </button>
        );
      })}

      {/* 하단 고정 버튼 */}
      <div className='sqm-sidebar-bottom' style={{ marginTop: 'auto', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4, padding: '8px 0' }}>
        <div style={{ width: 40, height: 1, background: '#1e293b', marginBottom: 4 }} />

        {/* 글꼴 크기 */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
          <button onClick={increaseFontScale} title="글꼴 크기 증가"
            style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 13, color: 'var(--nav-text)', padding: '3px 6px', borderRadius: 4 }}
            onMouseEnter={e => e.currentTarget.style.background='#1e293b'} onMouseLeave={e => e.currentTarget.style.background='none'}>A+</button>
          <span style={{ fontSize: 9, color: 'var(--nav-text)', cursor: 'pointer' }} onClick={resetFontScale} title="글꼴 초기화">
            {Math.round(fontScale * 100)}%
          </span>
          <button onClick={decreaseFontScale} title="글꼴 크기 감소"
            style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 13, color: 'var(--nav-text)', padding: '3px 6px', borderRadius: 4 }}
            onMouseEnter={e => e.currentTarget.style.background='#1e293b'} onMouseLeave={e => e.currentTarget.style.background='none'}>A-</button>
        </div>

        <div style={{ width: 40, height: 1, background: '#1e293b', margin: '2px 0' }} />

        <button onClick={toggleTheme} title="테마 전환"
          style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 16, color: '#64748b', padding: 6, borderRadius: 6 }}
          onMouseEnter={e => e.currentTarget.style.background='#1e293b'} onMouseLeave={e => e.currentTarget.style.background='none'}>
          {dark ? '☀️' : '🌙'}
        </button>
        <button onClick={() => navigate('/settings')} title="설정"
          style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 16, color: '#64748b', padding: 6, borderRadius: 6 }}
          onMouseEnter={e => e.currentTarget.style.background='#1e293b'} onMouseLeave={e => e.currentTarget.style.background='none'}>⚙️</button>
        <button onClick={() => { toggleDevMode(); navigate('/dev'); }} title="개발자 모드"
          style={{ background: 'none', border: 'none', cursor: 'pointer', fontSize: 14, color: devMode ? '#38bdf8' : '#334155', padding: 6, borderRadius: 6 }}
          onMouseEnter={e => e.currentTarget.style.background='#1e293b'} onMouseLeave={e => e.currentTarget.style.background='none'}>🔧</button>
      </div>
    </aside>
  );
}

// ── AppInner ────────────────────────────────────────────────────────────────
function AppInner({ dark, toggleTheme, fontScale, increaseFontScale, decreaseFontScale, resetFontScale, devMode, toggleDevMode }) {
  const navigate = useNavigate();
  const { setAutoRefresh } = useRefresh();
  const [inboundOpen,    setInboundOpen]    = useState(false);
  const [outboundOpen,   setOutboundOpen]   = useState(false);
  const [searchOpen,     setSearchOpen]     = useState(false);
  const [lotDetailOpen,  setLotDetailOpen]  = useState(false);
  const [selectedLot,    setSelectedLot]    = useState(null);
  const [doUpdateOpen,   setDoUpdateOpen]   = useState(false);
  const [locationMapOpen,setLocationMapOpen]= useState(false);
  const [allocationOpen, setAllocationOpen] = useState(false);
  const [toast,          setToast]          = useState(null);
  const hideToast = useCallback(() => setToast(null), []);

  const showToast = (msg) => setToast(msg);

  const handleMenuAction = (action) => {
    switch (action) {
      // ── Modal 열기 ───────────────────────────────────
      case 'search':          setSearchOpen(true);      break;
      case 'inboundModal':    setInboundOpen(true);     break;
      case 'outboundModal':   setOutboundOpen(true);    break;
      case 'doUpdateModal':   setDoUpdateOpen(true);    break;
      case 'locationMapModal':setLocationMapOpen(true); break;
      case 'allocationModal': setAllocationOpen(true);  break;

      // ── 반품 탭 직접 이동 ───────────────────────────
      case 'returnPage':
      case 'returnSingle':    navigate('/return', { state: { tab: 'single' } });  break;
      case 'returnExcel':     navigate('/return', { state: { tab: 'excel' } });   break;
      case 'returnStats':     navigate('/return', { state: { tab: 'history' } }); break;

      // ── navigate ────────────────────────────────────
      case 'navInventory':        navigate('/inventory');         break;
      case 'navTonbag':           navigate('/tonbag');            break;
      case 'navAllocation':       navigate('/allocation');        break;
      case 'navOutbound':         navigate('/outbound');          break;
      case 'navOutboundHistory':  navigate('/outbound-history');  break;
      case 'navScan':             navigate('/scan');              break;
      case 'navLog':              navigate('/log');               break;
      case 'navSummary':          navigate('/summary');           break;
      case 'navIntegrity':        navigate('/integrity');         break;
      case 'schemaCheck':
        fetch('/api/tools/schema-check')
          .then(r => r.json())
          .then(d => {
            const icon   = d.all_ok ? '✅' : '⚠️';
            const lines  = d.results.map(r => `${r.ok ? '✅' : '❌'} ${r.name}`).join('\n');
            const detail = `[운영 DB 스키마 점검] ${d.passed}/${d.total} 통과\n\n${lines}\n\n${d.message}`;
            showToast(`${icon} 스키마 점검: ${d.passed}/${d.total} 통과`);
            setTimeout(() => alert(detail), 300);
          })
          .catch(() => showToast('❌ 스키마 점검 실패'));
        break;
      case 'navSettings':         navigate('/settings');          break;
      case 'navCargo':            navigate('/cargo');             break;
      case 'navDashboard':        navigate('/');                  break;
      case 'navPicked':           navigate('/picked');            break;
      case 'navMove':             navigate('/move');              break;
      case 'navReports':          navigate('/reports');           break;
      case 'navProducts':         navigate('/products');          break;
      case 'navApproval':         navigate('/approval');          break;
      case 'navAiChat':           navigate('/ai-chat');           break;
      case 'navHelp':             navigate('/help');              break;
      case 'navTemplates':        navigate('/templates');         break;
      case 'toggleTheme':          toggleTheme();                  break;
      case 'fontIncrease':         increaseFontScale();            break;
      case 'fontDecrease':         decreaseFontScale();            break;
      case 'fontReset':            resetFontScale();               break;
      case 'devMode':
      case 'toggleDevMode':        toggleDevMode(); navigate('/dev'); break;

      // ── 도구 ────────────────────────────────────────
      case 'exportCsv':
        exportCsv();
        break;
      case 'exportLotList':
        window.location.href = '/api/tools/export-lot-list';
        break;
      case 'exportTonbagList':
        window.location.href = '/api/tools/export-tonbag-list';
        break;
      case 'exportLogs':
        window.location.href = '/api/tools/export-logs?format=csv';
        break;
      case 'integrityCheck':
        navigate('/integrity');
        break;
      case 'refreshData':
        // 데이터 refetch: 현재 페이지를 유지하며 navigate로 리마운트
        navigate(window.location.pathname, { replace: true });
        showToast('데이터를 새로고침했습니다.');
        break;
      case 'refresh':
        window.location.reload();
        break;
      case 'resetLayout':
        ['sqm_theme', 'sqm_font_scale', 'sqm_dev_mode'].forEach(k => localStorage.removeItem(k));
        window.location.reload();
        break;

      // ── 백업 (API 호출) ─────────────────────────────
      case 'backupCreate':
        fetch('/api/tools/backup/create', { method: 'POST' })
          .then(r => r.json())
          .then(d => showToast(d.success ? `✅ ${d.message}` : `❌ ${d.message}`))
          .catch(() => showToast('❌ 백업 생성 실패'));
        break;

      // ── DB 최적화 (API 호출) ────────────────────────
      case 'dbOptimize':
        fetch('/api/tools/db-optimize', { method: 'POST' })
          .then(r => r.json())
          .then(d => showToast(d.success ? '✅ DB 최적화 완료' : '❌ DB 최적화 실패'))
          .catch(() => showToast('❌ DB 최적화 실패'));
        break;

      // ── DN 교차검증 ─────────────────────────────────
      case 'dnCrossCheck':
        navigate('/integrity');
        showToast('DN 교차검증 → Integrity 페이지');
        break;

      case 'pdfToExcel':
      case 'pdfToWord':
      case 'pdfBatchConvert':
      case 'pdfAnalyze':
        showToast('PDF 변환 기능은 준비 중입니다.');
        break;

      case 'cleanLogs':
        fetch('/api/tools/clean-logs', { method: 'POST' })
          .then(r => r.json())
          .then(d => showToast(d.success ? '로그 정리 완료' : '로그 정리 실패'))
          .catch(() => showToast('로그 정리 실패'));
        break;

      case 'navAuditLog':
        navigate('/log');
        break;

      case 'resetTestDb':
        if (window.confirm('테스트 DB를 초기화하시겠습니까?')) {
          fetch('/api/tools/reset-test-db', { method: 'POST' })
            .then(r => r.json())
            .then(d => showToast(d.success ? '초기화 완료' : '초기화 실패'))
            .catch(() => showToast('초기화 실패'));
        }
        break;

      case 'toggleAutoRefresh':
        setAutoRefresh(a => { showToast(!a ? '자동 새로고침 ON' : '자동 새로고침 OFF'); return !a; });
        break;

      case 'navTonbag':
        navigate('/tonbag');
        break;

      // ── 준비중 (wip) ────────────────────────────────
      case 'wip':
        showToast('해당 기능은 준비 중입니다.');
        break;

      default:
        // 최근 파일 동적 navigate
        if (action && action.startsWith('navRecent:')) {
          const path = action.replace('navRecent:', '');
          navigate(path);
        }
        break;
    }
  };

  const handleSelectLot = (lotNo) => {
    setSelectedLot(lotNo);
    setLotDetailOpen(true);
    setSearchOpen(false);
  };

  return (
    <>
      <MenuBar onAction={handleMenuAction} dark={dark} toggleTheme={toggleTheme} />

      {/* 바디: 메뉴바(z-index) 아래 층 — 드롭다운이 본문에 가리지 않도록 */}
      <div style={{ display: 'flex', height: 'calc(100vh - 42px)', overflow: 'hidden', position: 'relative', zIndex: 0 }}>
        <Sidebar dark={dark} toggleTheme={toggleTheme}
          fontScale={fontScale} increaseFontScale={increaseFontScale}
          decreaseFontScale={decreaseFontScale} resetFontScale={resetFontScale}
          devMode={devMode} toggleDevMode={toggleDevMode} />

        <div className='sqm-page-content' style={{ flex: 1, overflow: 'auto', background: 'var(--bg-primary)' }}>
          <Routes>
            <Route path="/"                 element={<DashboardPage />} />
            <Route path="/inventory"        element={<InventoryPage onLotClick={handleSelectLot} />} />
            <Route path="/tonbag"           element={<TonbagPage />} />
            <Route path="/allocation"       element={<AllocationPage />} />
            <Route path="/outbound"         element={<OutboundPage />} />
            <Route path="/picked"           element={<PickedPage />} />
            <Route path="/sold"             element={<SoldPage />} />
            <Route path="/move"             element={<MovePage />} />
            <Route path="/scan"             element={<ScanPage />} />
            <Route path="/log"              element={<LogPage />} />
            <Route path="/summary"          element={<SummaryPage />} />
            <Route path="/cargo"            element={<CargoOverviewPage />} />
            <Route path="/return"           element={<ReturnPage />} />
            <Route path="/integrity"        element={<IntegrityPage />} />
            <Route path="/outbound-history" element={<OutboundHistoryPage />} />
            <Route path="/settings"         element={<SettingsPage />} />
            <Route path="/reports"          element={<ReportsPage />} />
            <Route path="/products"         element={<ProductMasterPage />} />
            <Route path="/approval"         element={<ApprovalPage />} />
            <Route path="/ai-chat"          element={<AiChatPage />} />
            <Route path="/help"             element={<HelpPage />} />
            <Route path="/templates"        element={<TemplatesPage />} />
            <Route path="/dev"              element={<DevPage devMode={devMode} toggleDevMode={toggleDevMode} fontScale={fontScale} increaseFontScale={increaseFontScale} decreaseFontScale={decreaseFontScale} resetFontScale={resetFontScale} />} />
          </Routes>
        </div>
      </div>

      {/* Modals */}
      <InboundModal      open={inboundOpen}     onClose={() => setInboundOpen(false)} />
      <OutboundModal     open={outboundOpen}    onClose={() => setOutboundOpen(false)} />
      <SearchModal       open={searchOpen}      onClose={() => setSearchOpen(false)} onSelectLot={handleSelectLot} />
      <LotDetailModal    open={lotDetailOpen}   onClose={() => setLotDetailOpen(false)} lotNo={selectedLot} />
      <DoUpdateModal     open={doUpdateOpen}    onClose={() => setDoUpdateOpen(false)} />
      <LocationMappingModal open={locationMapOpen} onClose={() => setLocationMapOpen(false)} />
      <AllocationInputModal open={allocationOpen}  onClose={() => setAllocationOpen(false)} />

      {/* Toast */}
      <Toast message={toast} onHide={hideToast} />
    </>
  );
}

// ── 전역 새로고침 Context ───────────────────────────────────────────────────
export const RefreshContext = createContext({
  lastRefresh: null,
  triggerRefresh: () => {},
  autoRefresh: true,
  setAutoRefresh: () => {},
  countdown: 30,
});
export const useRefresh = () => useContext(RefreshContext);

// ── App ─────────────────────────────────────────────────────────────────────
function App() {
  const [dark,      setDark]      = useState(() => localStorage.getItem('sqm_theme') === 'dark');
  const [lastRefresh,  setLastRefresh]  = useState(new Date());
  const [autoRefresh,  setAutoRefresh]  = useState(
    () => localStorage.getItem('sqm_auto_refresh') !== 'false'
  );
  const [countdown,    setCountdown]    = useState(30);
  const intervalRef  = useRef(null);
  const countdownRef = useRef(null);

  const triggerRefresh = useCallback(() => {
    setLastRefresh(new Date());
    setCountdown(30);
  }, []);

  // 자동 새로고침 30초 타이머
  useEffect(() => {
    localStorage.setItem('sqm_auto_refresh', autoRefresh ? 'true' : 'false');
    if (intervalRef.current)  clearInterval(intervalRef.current);
    if (countdownRef.current) clearInterval(countdownRef.current);
    if (!autoRefresh) { setCountdown(30); return; }

    // 카운트다운
    setCountdown(30);
    countdownRef.current = setInterval(() => {
      setCountdown(c => {
        if (c <= 1) return 30;
        return c - 1;
      });
    }, 1000);

    // 30초마다 새로고침 트리거
    intervalRef.current = setInterval(() => {
      triggerRefresh();
    }, 30000);

    return () => {
      clearInterval(intervalRef.current);
      clearInterval(countdownRef.current);
    };
  }, [autoRefresh, triggerRefresh]);
  const [fontScale, setFontScale] = useState(() => parseFloat(localStorage.getItem('sqm_font_scale') || '1.0'));
  const [devMode,   setDevMode]   = useState(() => localStorage.getItem('sqm_dev_mode') === 'true');

  useEffect(() => {
    document.body.classList.toggle('dark', dark);
    localStorage.setItem('sqm_theme', dark ? 'dark' : 'light');
  }, [dark]);

  useEffect(() => {
    document.documentElement.style.setProperty('--sqm-font-scale', String(fontScale));
    localStorage.setItem('sqm_font_scale', String(fontScale));
  }, [fontScale]);

  useEffect(() => {
    localStorage.setItem('sqm_dev_mode', devMode ? 'true' : 'false');
  }, [devMode]);

  const toggleTheme   = () => setDark(d => !d);
  const increaseFontScale = () => setFontScale(s => Math.min(1.5, parseFloat((s + 0.1).toFixed(1))));
  const decreaseFontScale = () => setFontScale(s => Math.max(0.7, parseFloat((s - 0.1).toFixed(1))));
  const resetFontScale    = () => setFontScale(1.0);
  const toggleDevMode     = () => setDevMode(d => !d);

  return (
    <RefreshContext.Provider value={{ lastRefresh, triggerRefresh, autoRefresh, setAutoRefresh, countdown }}>
    <BrowserRouter>
      <AppInner dark={dark} toggleTheme={toggleTheme}
        fontScale={fontScale} increaseFontScale={increaseFontScale}
        decreaseFontScale={decreaseFontScale} resetFontScale={resetFontScale}
        devMode={devMode} toggleDevMode={toggleDevMode} />
    </BrowserRouter>
    </RefreshContext.Provider>
  );
}

export default App;
