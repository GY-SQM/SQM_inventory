import { useState, useEffect, useCallback, useRef, createContext, useContext } from 'react';
import { BrowserRouter, Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import MenuBar from './components/MenuBar';
import ActionBar from './components/ActionBar';
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
import SmartInboundPage from './pages/SmartInboundPage';
import DbControlPage from './pages/DbControlPage';
import TemplateManagerPage from './pages/TemplateManagerPage';
import MobileDashboard from './pages/MobileDashboard';
import PdfConvertModal from './components/PdfConvertModal';
import { exportCsv } from './api/writeApi';

// ── 사이드바 탭 정의 (v864 동일 순서/색상) ─────────────────────────────────
const SIDEBAR_TABS = [
  { key: 'inventory',   icon: '📦', label: 'Inventory',   path: '/inventory',   color: '#4ade80' },
  { key: 'allocation',  icon: '📋', label: 'Allocation',  path: '/allocation',  color: '#facc15' },
  { key: 'picked',      icon: '🚛', label: 'Picked',      path: '/picked',      color: '#a78bfa' },
  { key: 'outbound',    icon: '📤', label: 'Outbound',    path: '/outbound',    color: '#38bdf8' },
  { key: 'return',      icon: '🔄', label: 'Return',      path: '/return',      color: '#f87171' },
  { key: 'move',        icon: '🔀', label: 'Move',        path: '/move',        color: '#22d3ee' },
  { key: 'smart-inbound', icon: '🤖', label: 'Smart Inbound', path: '/smart-inbound', color: '#10b981' },
  { key: 'db-control',    icon: '📊', label: 'DB Control',     path: '/db-control',    color: '#8b5cf6' },
  null,
  { key: 'dashboard',   icon: '📊', label: 'Dashboard',   path: '/',            color: '#00e676' },
  { key: 'log',         icon: '📝', label: 'Log',         path: '/log',         color: '#94a3b8' },
  { key: 'scan',        icon: '📷', label: 'Scan',        path: '/scan',        color: '#fb923c' },
  null,
  { key: 'tonbag',      icon: '🎒', label: 'Tonbag',      path: '/tonbag',      color: '#f59e0b' },
  { key: 'cargo',       icon: '📋', label: '총괄 재고',    path: '/cargo',       color: '#60a5fa' },
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
      width: 160, minWidth: 160, background: 'var(--nav-bg)',
      borderRight: '1px solid var(--nav-border)',
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      padding: '16px 0', overflowY: 'auto', flexShrink: 0,
    }}>
      {SIDEBAR_TABS.map((tab, idx) => {
        if (tab === null) {
          return <div key={`sep-${idx}`} style={{ width: 100, height: 1, background: 'var(--nav-border)', margin: '10px auto' }} />;
        }
        const isActive = activeKey === tab.key;
        return (
          <button
            key={tab.key}
            onClick={() => navigate(tab.path)}
            title={tab.label}
            aria-label={tab.label}
            style={{
              display: 'flex', flexDirection: 'column', alignItems: 'center',
              width: '100%', padding: isActive ? '18px 8px' : '14px 8px', cursor: 'pointer',
              border: 'none',
              background: isActive ? `linear-gradient(135deg, ${tab.color}22, ${tab.color}11)` : 'none',
              borderLeft: `5px solid ${isActive ? tab.color : 'transparent'}`,
              borderRadius: isActive ? '0 12px 12px 0' : 0,
              marginBottom: 4, transition: 'all 0.2s ease',
            }}
            onMouseEnter={e => { if (!isActive) e.currentTarget.style.background = 'var(--nav-bg-hover)'; }}
            onMouseLeave={e => { if (!isActive) e.currentTarget.style.background = 'none'; }}
          >
            <span style={{
              fontSize: isActive ? 52 : 40,
              lineHeight: 1,
              transition: 'font-size 0.2s ease',
            }}>{tab.icon}</span>
            <span style={{
              fontSize: isActive ? 23 : 18,
              marginTop: 6,
              color: isActive ? tab.color : '#cbd5e1',
              fontWeight: isActive ? 800 : 600,
              textShadow: isActive ? `0 0 8px ${tab.color}44` : 'none',
              transition: 'all 0.2s ease',
            }}>{tab.label}</span>
          </button>
        );
      })}

      {/* 하단 고정 버튼 — 제거됨 (탑메뉴 설정/도구에서 모든 기능 접근 가능) */}
    </aside>
  );
}

// ── AppInner ────────────────────────────────────────────────────────────────
function AppInner({ dark, toggleTheme, fontScale, setFontScale, increaseFontScale, decreaseFontScale, resetFontScale, devMode, toggleDevMode }) {
  const navigate = useNavigate();
  const { setAutoRefresh } = useRefresh();
  const [inboundOpen,    setInboundOpen]    = useState(false);
  const [inboundMode,    setInboundMode]    = useState('pdf');   // 'pdf' | 'excel'
  const [outboundOpen,   setOutboundOpen]   = useState(false);
  const [outboundMode,   setOutboundMode]   = useState('form');  // 'form' | 'paste'
  const [searchOpen,     setSearchOpen]     = useState(false);
  const [lotDetailOpen,  setLotDetailOpen]  = useState(false);
  const [selectedLot,    setSelectedLot]    = useState(null);
  const [doUpdateOpen,   setDoUpdateOpen]   = useState(false);
  const [locationMapOpen,setLocationMapOpen]= useState(false);
  const [allocationOpen, setAllocationOpen] = useState(false);
  const [pdfConvertOpen, setPdfConvertOpen] = useState(false);
  const [pdfConvertMode, setPdfConvertMode] = useState('excel'); // 'excel'|'word'|'batch'|'analyze'
  const [toast,          setToast]          = useState(null);
  const hideToast = useCallback(() => setToast(null), []);

  const showToast = (msg) => setToast(msg);

  // ★ P2-S3: 키보드 단축키
  useEffect(() => {
    const handler = (e) => {
      // 입력 중이면 무시
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return;

      if (e.ctrlKey || e.metaKey) {
        switch (e.key.toLowerCase()) {
          case 'k': e.preventDefault(); setSearchOpen(true); break;
          case 'i': e.preventDefault(); setInboundOpen(true); break;
          case 'o': e.preventDefault(); setOutboundOpen(true); break;
          case 'r': e.preventDefault(); navigate(window.location.pathname, { replace: true }); break;
          case 'f': e.preventDefault(); setSearchOpen(true); break;
          case 'e': e.preventDefault(); window.open('/api/tools/export-lot-list', '_blank'); break;
          case 'b': e.preventDefault();
            fetch('/api/tools/backup/create', { method: 'POST' })
              .then(r => r.json())
              .then(d => showToast(d.success ? `✅ ${d.message}` : `❌ ${d.message}`))
              .catch(() => showToast('❌ 백업 실패'));
            break;
          default: break;
        }
      }
      if (e.key === 'Escape') {
        setSearchOpen(false); setInboundOpen(false); setOutboundOpen(false);
        setDoUpdateOpen(false); setLocationMapOpen(false); setAllocationOpen(false);
        setLotDetailOpen(false); setPdfConvertOpen(false);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [navigate]);

  const handleMenuAction = (action) => {
    switch (action) {
      // ── Modal 열기 ───────────────────────────────────
      case 'search':          setSearchOpen(true);      break;
      case 'inboundModal':    setInboundMode('pdf');  setInboundOpen(true);  break;
      case 'inboundExcel':    setInboundMode('excel'); setInboundOpen(true); break;
      case 'outboundModal':   setOutboundMode('form'); setOutboundOpen(true); break;
      case 'outboundPaste':   setOutboundMode('paste'); setOutboundOpen(true); break;
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
      case 'navSmartInbound':   navigate('/smart-inbound'); break;
      case 'navDbControl':      navigate('/db-control');    break;
      case 'navTemplateManager': navigate('/template-mgr'); break;
      case 'navTemplates':        navigate('/templates');         break;
      case 'toggleTheme':          toggleTheme();                  break;
      case 'fontIncrease':         increaseFontScale();            break;
      case 'fontDecrease':         decreaseFontScale();            break;
      case 'fontReset':            resetFontScale();               break;
      case 'devMode':
      case 'toggleDevMode':        toggleDevMode(); navigate('/dev'); break;

      // ── 도구 ────────────────────────────────────────
      case 'exportCustoms':
        window.open('/api/tools/export/csv?type=customs', '_blank');
        break;
      case 'exportRubyli':
        window.open('/api/tools/export/csv?type=rubyli', '_blank');
        break;
      case 'exportTonbagReport':
        window.open('/api/tools/export/csv?type=tonbag', '_blank');
        break;
      case 'exportIntegrated':
        window.open('/api/tools/export/csv?type=integrated', '_blank');
        break;
      case 'exportLotList':
        window.open('/api/tools/export-lot-list', '_blank');
        break;
      case 'exportTonbagList':
        window.open('/api/tools/export-tonbag-list', '_blank');
        break;
      case 'exportLogs':
        window.open('/api/tools/export-logs?format=csv', '_blank');
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

      // ── 체크섬 갱신 ────────────────────────────────
      case 'checksumUpdate':
        fetch('/api/tools/checksum-update', { method: 'POST' })
          .then(r => r.json())
          .then(d => showToast(d.success ? `✅ 체크섬: ${d.checksum} (${d.row_count}행)` : '❌ 체크섬 갱신 실패'))
          .catch(() => showToast('❌ 체크섬 갱신 실패'));
        break;

      // ── DB 무결성 검증 ─────────────────────────────
      case 'dbIntegrityVerify':
        fetch('/api/tools/integrity-check')
          .then(r => r.json())
          .then(d => {
            showToast(`${d.total_issues === 0 ? '✅' : '⚠️'} 무결성 검증: ${d.total_issues}건 이슈`);
            if (d.total_issues > 0) setTimeout(() => alert(JSON.stringify(d.issues.slice(0, 5), null, 2)), 300);
          })
          .catch(() => showToast('❌ 무결성 검증 실패'));
        break;

      // ── 전체 시스템 진단 ───────────────────────────
      case 'selfTest':
        fetch('/api/tools/self-test')
          .then(r => r.json())
          .then(d => {
            const icon = d.passed === d.total ? '✅' : '⚠️';
            const lines = d.results.map(r => `${r.ok ? '✅' : '❌'} ${r.name}`).join('\n');
            showToast(`${icon} 진단: ${d.passed}/${d.total} 통과`);
            setTimeout(() => alert(`[전체 진단]\n${lines}`), 300);
          })
          .catch(() => showToast('❌ 전체 진단 실패'));
        break;

      // ── Dry Run 검증 ──────────────────────────────
      case 'dryRunInbound':
        showToast('🔬 입고 검증 (Dry Run) — 다음 입고 시 자동 검증됩니다.');
        break;

      case 'dryRunOutbound':
        showToast('🔬 출고 검증 (Dry Run) — 다음 출고 시 자동 검증됩니다.');
        break;

      // ── 단위 테스트 ───────────────────────────────
      case 'unitTest':
        fetch('/api/tools/self-test')
          .then(r => r.json())
          .then(d => showToast(`🧪 단위 테스트: ${d.passed}/${d.total} 통과`))
          .catch(() => showToast('❌ 단위 테스트 실패'));
        break;

      // ── DN 교차검증 ─────────────────────────────────
      case 'dnCrossCheck':
        navigate('/integrity');
        showToast('DN 교차검증 → Integrity 페이지');
        break;

      case 'pdfToExcel':      setPdfConvertMode('excel');   setPdfConvertOpen(true); break;
      case 'pdfToWord':       setPdfConvertMode('word');    setPdfConvertOpen(true); break;
      case 'pdfBatchConvert': setPdfConvertMode('batch');   setPdfConvertOpen(true); break;
      case 'pdfAnalyze':      setPdfConvertMode('analyze'); setPdfConvertOpen(true); break;

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
        if (window.confirm('테스트 DB를 초기화하시겠습니까?\n(operation_log, outbound_log, return_log, move_log 테이블)')) {
          fetch('/api/tools/reset-test-db', {
            method: 'POST',
            headers: { 'X-Confirm-Reset': 'CONFIRM_RESET' },
          })
            .then(r => r.json())
            .then(d => showToast(d.success ? `✅ ${d.message}` : `❌ ${d.detail || '초기화 실패'}`))
            .catch(() => showToast('❌ 초기화 실패'));
        }
        break;

      case 'toggleAutoRefresh':
        setAutoRefresh(a => { showToast(!a ? '자동 새로고침 ON' : '자동 새로고침 OFF'); return !a; });
        break;

      // ── 테마 적용 ─────────────────────────────────────
      // ── 창 크기 저장/초기화 ────────────────────────
      case 'saveWindowSize':
        localStorage.setItem('sqm_window_size', JSON.stringify({ w: window.innerWidth, h: window.innerHeight }));
        showToast('창 크기를 저장했습니다.');
        break;
      case 'resetWindowSize':
        window.resizeTo(1500, 900);
        localStorage.removeItem('sqm_window_size');
        showToast('창 크기를 1500×900으로 초기화했습니다.');
        break;

      // ── 글꼴 크기 프리셋 ──────────────────────────
      case 'fontSize11': setFontScale(11/14); break;
      case 'fontSize13': setFontScale(13/14); break;
      case 'fontSize16': setFontScale(16/14); break;

      case 'theme:cosmo':
      case 'theme:litera':
      case 'theme:minty':
      case 'theme:journal':
      case 'theme:yeti':
      case 'theme:morph':
      case 'theme:darkly':
      case 'theme:cyborg':
      case 'theme:superhero':
      case 'theme:solar':
      case 'theme:vapor': {
        const themeName = action.replace('theme:', '');
        document.body.setAttribute('data-theme', themeName);
        localStorage.setItem('sqm_theme_name', themeName);
        const isDark = ['darkly', 'cyborg', 'superhero', 'solar', 'vapor'].includes(themeName);
        if (isDark !== dark) toggleTheme();
        showToast(`테마 적용: ${themeName}`);
        break;
      }

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
      <ActionBar onAction={handleMenuAction} />

      {/* 바디: 메뉴바(z-index) 아래 층 — 드롭다운이 본문에 가리지 않도록 */}
      <div style={{ display: 'flex', height: 'calc(100vh - 60px - 40px)', overflow: 'hidden', position: 'relative', zIndex: 0 }}>
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
            <Route path="/smart-inbound" element={<SmartInboundPage />} />
            <Route path="/db-control" element={<DbControlPage />} />
            <Route path="/template-mgr" element={<TemplateManagerPage />} />
            <Route path="/mobile"      element={<MobileDashboard />} />
            {/* DevPage: devMode 활성화 시에만 접근 가능 */}
            <Route path="/dev" element={devMode ? <DevPage devMode={devMode} toggleDevMode={toggleDevMode} fontScale={fontScale} increaseFontScale={increaseFontScale} decreaseFontScale={decreaseFontScale} resetFontScale={resetFontScale} /> : <div style={{padding:32,color:'#64748b',textAlign:'center'}}>개발자 모드에서만 접근 가능합니다.</div>} />
          </Routes>
        </div>
      </div>

      {/* Modals */}
      <InboundModal      open={inboundOpen}     onClose={() => setInboundOpen(false)} mode={inboundMode} />
      <OutboundModal     open={outboundOpen}    onClose={() => setOutboundOpen(false)} mode={outboundMode} />
      <PdfConvertModal   open={pdfConvertOpen}  onClose={() => setPdfConvertOpen(false)} mode={pdfConvertMode} />
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
  const [fontScale, setFontScale] = useState(() => parseFloat(localStorage.getItem('sqm_font_scale') || '1.5'));
  const [devMode,   setDevMode]   = useState(() => localStorage.getItem('sqm_dev_mode') === 'true');

  useEffect(() => {
    document.body.classList.toggle('dark', dark);
    localStorage.setItem('sqm_theme', dark ? 'dark' : 'light');
  }, [dark]);

  // 테마 프리셋 복원
  useEffect(() => {
    const saved = localStorage.getItem('sqm_theme_name');
    if (saved) document.body.setAttribute('data-theme', saved);
  }, []);

  useEffect(() => {
    document.documentElement.style.setProperty('--sqm-font-scale', String(fontScale));
    localStorage.setItem('sqm_font_scale', String(fontScale));
  }, [fontScale]);

  useEffect(() => {
    localStorage.setItem('sqm_dev_mode', devMode ? 'true' : 'false');
  }, [devMode]);

  const toggleTheme   = () => setDark(d => !d);
  const increaseFontScale = () => setFontScale(s => Math.min(2.0, parseFloat((s + 0.1).toFixed(1))));
  const decreaseFontScale = () => setFontScale(s => Math.max(0.7, parseFloat((s - 0.1).toFixed(1))));
  const resetFontScale    = () => setFontScale(1.5);
  const toggleDevMode     = () => setDevMode(d => !d);

  return (
    <RefreshContext.Provider value={{ lastRefresh, triggerRefresh, autoRefresh, setAutoRefresh, countdown }}>
    <BrowserRouter>
      <AppInner dark={dark} toggleTheme={toggleTheme}
        fontScale={fontScale} setFontScale={setFontScale}
        increaseFontScale={increaseFontScale}
        decreaseFontScale={decreaseFontScale} resetFontScale={resetFontScale}
        devMode={devMode} toggleDevMode={toggleDevMode} />
    </BrowserRouter>
    </RefreshContext.Provider>
  );
}

export default App;
