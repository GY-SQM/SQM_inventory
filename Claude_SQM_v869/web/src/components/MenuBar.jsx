// ═══════════════════════════════════════════════════════════════════════════
// 상단 메뉴: 웹 최종 UI / Tk 레퍼런스와 동일한 7개
//   📤 출고  📁 파일  📝 보고서  🔧 도구  👁 View  ❓ 도움말  📦 품목
// (입고·재고 세부는 파일 / View / 도구 하위에 유지 — v864 기능 동등)
// ═══════════════════════════════════════════════════════════════════════════
import { useState, useRef, useEffect, useContext } from 'react';
import { RefreshContext } from '../App';
import { useLocation } from 'react-router-dom';
import { getRecentFiles } from '../utils/recentFiles';

// ── menuData — 7개 루트 (스크린샷·v864 웹 셸 기준) ─────────────────────────
const menuData = [

  // ① 📤 출고 (Tk 상단에서 출고가 앞에 오는 구성과 동일)
  {
    label: '📤 출고',
    items: [
      { label: '🚀  즉시 출고 (원스톱)',        action: 'outboundModal' },
      { label: '📤  빠른 출고 (붙여넣기)',       action: 'outboundModal' },
      { separator: true },
      { label: '📋  Picking List 업로드 (PDF)',  action: 'navReports' },
      { label: '📊  바코드 스캔 업로드',         action: 'navScan' },
      { label: '📷  스캔 탭으로 이동',           action: 'navScan' },
      { separator: true },
      { label: '📋  Allocation 입력',            action: 'allocationModal' },
      { label: '✅  승인 대기',                  action: 'navApproval' },
      { label: '📌  예약 반영 (승인분)',         action: 'navApproval' },
      { label: '📜  승인 이력 조회',             action: 'navApproval' },
      { label: '📋  판매 배정 탭으로 이동',      action: 'navAllocation' },
      { separator: true },
      { label: '📋  출고 현황 조회',             action: 'navOutboundHistory' },
      { label: '📊  Sales Order 업로드',         action: 'navReports' },
      { label: '🔁  Swap 리포트',                action: 'navTemplates' },
      { label: '📦  출고 피킹 템플릿 관리',      action: 'navTemplates' },
    ],
  },

  // ② 📁 파일
  {
    label: '📁 파일',
    items: [
      {
        label: '📥  입고 (Ctrl+I)',
        children: [
          { label: '📄  PDF 스캔 입고',           action: 'inboundModal' },
          { label: '📊  엑셀 파일 수동 입고',     action: 'inboundModal' },
          { separator: true },
          { label: '📋  D/O 후속 연결',           action: 'doUpdateModal' },
          { label: '📍  톤백 위치 매핑',          action: 'locationMapModal' },
          { label: '✅  대량 이동 승인',          action: 'navTemplates' },
          { separator: true },
          {
            label: '🔄  반품 (재입고)',
            children: [
              { label: '📝  소량 반품 (1~2건)',   action: 'returnSingle' },
              { label: '📂  다량 반품 (Excel)',   action: 'returnExcel' },
            ],
          },
          { label: '📂  반품 입고 (Excel)',       action: 'returnExcel' },
          { label: '📊  반품 사유 통계',          action: 'returnStats' },
          { separator: true },
          { label: '📋  입고 현황 조회',          action: 'navLog' },
          { separator: true },
          { label: '📝  입고 파싱 템플릿 관리',   action: 'navTemplates' },
          { label: '📦  제품 마스터 관리',        action: 'navProducts' },
          { label: '⚙️   이메일 설정',            action: 'navSettings' },
          { separator: true },
          { label: '🔍  정합성 검증 (시각화)',    action: 'navIntegrity' },
          { label: '🛠️   LOT 상태 정합성 복구',  action: 'navIntegrity' },
        ],
      },
      { separator: true },
      {
        label: '💾  내보내기 (Ctrl+E)',
        children: [
          { label: '📋  통관요청 양식',       action: 'exportCsv' },
          { label: '📊  루비리 양식',         action: 'exportCsv' },
          { label: '🎒  톤백 현황',           action: 'exportCsv' },
          { label: '⭐  통합 현황',           action: 'exportCsv' },
          { separator: true },
          { label: '📋  LOT 리스트 Excel',   action: 'exportLotList' },
          { label: '🎒  톤백리스트 Excel',    action: 'exportTonbagList' },
          { label: '💾  로그 내보내기',       action: 'exportLogs' },
        ],
      },
      { separator: true },
      {
        label: '🔐  백업 (Ctrl+B)',
        children: [
          { label: '💾  백업 생성',         action: 'backupCreate' },
          { label: '🔄  복원',              action: 'navSettings' },
          { label: '📋  백업 목록',         action: 'navSettings' },
          { separator: true },
          { label: '⏰  자동 백업 설정',    action: 'navSettings' },
        ],
      },
      { separator: true },
      {
        label: '📄  PDF/이미지 변환',
        children: [
          { label: '📊  → Excel',       action: 'pdfToExcel' },
          { label: '📝  → Word',        action: 'pdfToWord' },
          { separator: true },
          { label: '📁  일괄 변환',     action: 'pdfBatchConvert' },
          { label: '🔍  분석',          action: 'pdfAnalyze' },
        ],
      },
      { separator: true },
      {
        label: '📂  최근 파일',
        children: '__RECENT_FILES__',
      },
      { separator: true },
      { label: '❌  종료',  action: 'exit' },
    ],
  },

  // ③ 📝 보고서
  {
    label: '📝 보고서',
    items: [
      { label: '📄  거래명세서 생성',    action: 'navReports' },
      { separator: true },
      { label: '📦  Detail of Outbound', action: 'navReports' },
      { label: '📋  Sales Order DN',     action: 'navReports' },
      { label: '🔍  DN 교차검증',        action: 'dnCrossCheck' },
      { separator: true },
      { label: '📝  고객 보고서 생성',   action: 'navReports' },
      { label: '📂  보고서 양식 관리',   action: 'navTemplates' },
      { separator: true },
      { label: '📋  보고서 이력 조회',   action: 'navLog' },
      { label: '📦  재고 현황 보고서',   action: 'navReports' },
      { label: '📈  입출고 내역',        action: 'navReports' },
      { label: '📅  월간 실적 PDF',      action: 'navReports' },
      { label: '📊  일일 현황 PDF',      action: 'navReports' },
      { label: '🔖  LOT 상세',           action: 'navReports' },
    ],
  },

  // ④ 🔧 도구 (v864 설정/도구 중 운영·DB·AI)
  {
    label: '🔧 도구',
    items: [
      { label: '━━ 🖥️ 화면 ━━',   action: 'wip', disabled: true },
      { label: '🔄  새로고침 (F5)', action: 'refreshData' },
      { separator: true },
      { label: '🌙  Dark / Light 전환',    action: 'toggleTheme' },
      {
        label: '🎨  테마 선택',
        children: [
          { label: '━━ ☀️ Light ━━', action: 'wip', disabled: true },
          { label: '☀️  Cosmo',       action: 'wip' },
          { label: '☀️  Litera',      action: 'wip' },
          { label: '☀️  Minty',       action: 'wip' },
          { separator: true },
          { label: '━━ 🌙 Dark ━━',  action: 'wip', disabled: true },
          { label: '🌙  Darkly',      action: 'wip' },
          { label: '🌙  Cyborg',      action: 'wip' },
          { label: '🌙  Superhero',   action: 'wip' },
        ],
      },
      { separator: true },
      { label: '━━ 🔧 도구 ━━',              action: 'wip', disabled: true },
      { label: '📊  LOT Allocation·톤백 현황', action: 'navAllocation' },
      { separator: true },
      { label: '📋  D/O 후속 연결',           action: 'doUpdateModal' },
      { separator: true },
      {
        label: '🤖  Gemini AI',
        children: [
          { label: '🚢  선사 BL 등록 도구',  action: 'navSettings' },
          { label: '🔬  선사 패턴 분석',     action: 'navSettings' },
          { separator: true },
          { label: '💬  AI 채팅',            action: 'navAiChat' },
          { label: '⚙️  API 설정',           action: 'navSettings' },
          { label: '🔬  API 테스트',         action: 'navSettings' },
        ],
      },
      { separator: true },
      // ── DB 보호/정합성
      { label: '━━ 🛡️ DB 보호 ━━',          action: 'wip', disabled: true },
      { label: '🩺  데이터 정합성 검사',      action: 'navIntegrity' },
      { label: '🧪  운영 DB 스키마 점검(1회)',   action: 'schemaCheck' },
      { label: '🔍  정합성 검증 (시각화)',    action: 'navIntegrity' },
      { label: '🛠️   LOT 상태 정합성 복구',  action: 'navIntegrity' },
      { separator: true },
      { label: '🔧  DB 최적화',              action: 'dbOptimize' },
      { label: 'ℹ️   DB 정보',               action: 'navSettings' },
      { label: '📋  로그 정리',              action: 'cleanLogs' },
      { label: '📋  감사 로그 조회',         action: 'navAuditLog' },
      { separator: true },
      { label: '🗑️   테스트 DB 초기화',      action: 'resetTestDb' },
      { separator: true },
      { label: '🔄  대시보드 자동 갱신 ON/OFF', action: 'toggleAutoRefresh' },
      { separator: true },
      // ── 설정
      { label: '⚙️   시스템 설정',           action: 'navSettings' },
      { label: '🧪  개발자 모드',            action: 'devMode' },
    ],
  },

  // ⑤ 👁 View — 글꼴·화면·주요 탭 이동 (v864 View + 재고 메뉴 통합)
  {
    label: '👁 View',
    items: [
      { label: '🔄  새로고침 (F5)',           action: 'refreshData' },
      { label: '🔃  창 레이아웃 초기화',      action: 'resetLayout' },
      { separator: true },
      { label: 'A+  글꼴 크게',               action: 'fontIncrease' },
      { label: 'A-  글꼴 작게',               action: 'fontDecrease' },
      { label: '100% 글꼴 기본',              action: 'fontReset' },
      { separator: true },
      { label: '📊  LOT 리스트 Excel',        action: 'exportLotList' },
      { label: '🎒  톤백리스트 Excel',         action: 'exportTonbagList' },
      { label: '📋  출고 현황 조회',          action: 'navOutboundHistory' },
      { label: '📊  재고 추이 (대시보드)',    action: 'navDashboard' },
      { separator: true },
      { label: '📦  재고 조회',               action: 'navInventory' },
      { label: '🎒  톤백',                    action: 'navTonbag' },
      { label: '📋  판매 배정',               action: 'navAllocation' },
      { label: '🚛  화물 결정',               action: 'navPicked' },
      { label: '📤  출고',                    action: 'navOutbound' },
      { label: '🔄  반품',                    action: 'returnPage' },
      { label: '🔀  이동',                    action: 'navMove' },
      { separator: true },
      { label: '📊  대시보드',                action: 'navDashboard' },
      { label: '📋  총괄 재고',               action: 'navCargo' },
    ],
  },

  // ⑥ ❓ 도움말
  {
    label: '❓ 도움말',
    items: [
      { label: '📖  사용법',               action: 'navHelp' },
      { label: '⌨️   단축키 안내',         action: 'navHelp' },
      { separator: true },
      { label: '📊  STATUS 상태값 안내',   action: 'navHelp' },
      { label: '💾  DB 백업/복구 가이드',  action: 'navHelp' },
      { separator: true },
      { label: 'ℹ️   시스템 정보',         action: 'navSettings' },
      { label: '📝  버전 정보',            action: 'navSettings' },
    ],
  },

  // ⑦ 📦 품목 (제품·마스터·템플릿)
  {
    label: '📦 품목',
    items: [
      { label: '📦  제품 마스터 관리',        action: 'navProducts' },
      { label: '📊  제품별 재고 현황',        action: 'navSummary' },
      { separator: true },
      { label: '📝  입고 파싱 템플릿 관리',   action: 'navTemplates' },
      { label: '⚙️   이메일 설정',            action: 'navSettings' },
    ],
  },
];

// ── 스타일 ──────────────────────────────────────────────────────────────────
const S = {
  bar: {
    display: 'flex',
    alignItems: 'center',
    padding: '0 12px',
    background: 'var(--nav-bg)',
    borderBottom: '2px solid var(--nav-border)',
    minHeight: 42,
    flexShrink: 0,
    /* 본문 영역보다 위에 그려야 드롭다운이 클릭·표시됨 (z-index만으로는 position 없으면 무시됨) */
    position: 'relative',
    zIndex: 3000,
    flexWrap: 'nowrap',
    overflow: 'visible',
  },
  /* flex:1로 우측 영역 밀기. overflow는 visible만 — auto/scroll이면 드롭다운이 잘려 클릭 불가 */
  menuRow: {
    display: 'flex',
    alignItems: 'center',
    flex: 1,
    minWidth: 0,
    flexWrap: 'nowrap',
    overflow: 'visible',
  },
  brand: {
    fontSize: 14, fontWeight: 700, color: 'var(--nav-accent)',
    marginRight: 12, padding: '8px 0',
    whiteSpace: 'nowrap', userSelect: 'none',
  },
  menuBtn: {
    padding: '8px 10px', color: 'var(--nav-text)', fontSize: 12,
    fontWeight: 500, cursor: 'pointer', border: 'none',
    background: 'none', fontFamily: 'inherit',
    whiteSpace: 'nowrap', flexShrink: 0,
  },
  menuBtnActive: {
    background: 'var(--nav-bg-hover)', color: 'var(--nav-text-active)',
  },
  dropdown: {
    position: 'absolute', top: '100%', left: 0,
    background: '#1e293b', border: '1px solid #475569',
    borderRadius: 6, padding: '4px 0', minWidth: 220,
    zIndex: 1000, boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
    maxHeight: '80vh', overflowY: 'auto',
  },
  item: {
    display: 'flex', alignItems: 'center',
    justifyContent: 'space-between',
    width: '100%', padding: '6px 14px',
    color: '#e2e8f0', fontSize: 12,
    cursor: 'pointer', border: 'none',
    background: 'none', textAlign: 'left',
    fontFamily: 'inherit', whiteSpace: 'nowrap',
  },
  itemDisabled: { color: '#475569', cursor: 'default', fontWeight: 600 },
  itemWip:      { color: '#64748b' },
  sep:    { borderTop: '1px solid #334155', margin: '3px 0' },
  arrow:  { fontSize: 9, color: '#64748b', marginLeft: 10 },
  submenu: {
    position: 'absolute', left: '100%', top: -4,
    background: '#1e293b', border: '1px solid #475569',
    borderRadius: 6, padding: '4px 0', minWidth: 200,
    zIndex: 1001, boxShadow: '0 8px 24px rgba(0,0,0,0.5)',
    maxHeight: '70vh', overflowY: 'auto',
  },
  wipBadge: { fontSize: 10, color: '#475569', marginLeft: 6 },
};

// ── 드롭다운 항목 재귀 렌더러 ───────────────────────────────────────────────
function DropdownItems({ items, onAction }) {
  const [openSub, setOpenSub] = useState(null);

  return (
    <>
      {items.map((item, idx) => {
        if (item.separator) {
          return <div key={`s${idx}`} style={S.sep} />;
        }
        if (item.children) {
          return (
            <div key={`sub${idx}`} style={{ position: 'relative' }}
              onMouseEnter={() => setOpenSub(idx)}
              onMouseLeave={() => setOpenSub(null)}
            >
              <button
                type="button"
                style={S.item}
                onMouseEnter={e => e.currentTarget.style.background = 'var(--nav-bg-hover)'}
                onMouseLeave={e => e.currentTarget.style.background = 'none'}
              >
                {item.label}
                <span style={S.arrow}>▶</span>
              </button>
              {openSub === idx && (
                <div style={S.submenu}>
                  <DropdownItems items={item.children} onAction={onAction} />
                </div>
              )}
            </div>
          );
        }
        const isDisabled = item.disabled;
        const isWip      = item.action === 'wip' && !isDisabled;
        return (
          <button
            type="button"
            key={`i${idx}`}
            style={{
              ...S.item,
              ...(isDisabled ? S.itemDisabled : {}),
              ...(isWip      ? S.itemWip      : {}),
            }}
            onMouseEnter={e => { if (!isDisabled) e.currentTarget.style.background = 'var(--nav-bg-hover)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'none'; }}
            onClick={(e) => {
              e.stopPropagation();
              if (!isDisabled) onAction(item.action);
            }}
          >
            {item.label}
            {isWip && <span style={S.wipBadge}>[준비중]</span>}
          </button>
        );
      })}
    </>
  );
}

// ── 최근 파일 목록 동적 생성 ────────────────────────────────────────────────
function buildRecentFileItems() {
  const files = getRecentFiles();
  if (!files.length) {
    return [{ label: '(최근 작업 없음)', action: 'wip', disabled: true }];
  }
  const typeIcon = { '입고': '📥', '출고': '📤', '반품': '🔄', '보고서': '📊', '스캔': '📷' };
  return files.map(f => ({
    label: `${typeIcon[f.type] || '📄'}  ${f.filename}`,
    action: `navRecent:${f.path}`,
  }));
}

// ── MenuBar 메인 ─────────────────────────────────────────────────────────────
export default function MenuBar({ onAction, dark, toggleTheme }) {
  const { lastRefresh, triggerRefresh, autoRefresh, setAutoRefresh, countdown }
    = useContext(RefreshContext);
  const [openMenu,    setOpenMenu]    = useState(null);
  const [toast,       setToast]       = useState(null);
  const [recentMenu,  setRecentMenu]  = useState(buildRecentFileItems());
  const barRef    = useRef(null);
  const toastRef  = useRef(null);

  // 마지막 갱신 시각 포맷
  const fmtTime = (d) => {
    if (!d) return '--:--:--';
    const h = String(d.getHours()).padStart(2,'0');
    const m = String(d.getMinutes()).padStart(2,'0');
    const s = String(d.getSeconds()).padStart(2,'0');
    return `${h}:${m}:${s}`;
  };
  useLocation(); // 라우트 변경 시 메뉴 닫기 트리거

  // 바깥 클릭 → 메뉴 닫기 (버블 단계: 메뉴 버튼·항목 onClick이 먼저 실행된 뒤 처리)
  useEffect(() => {
    const fn = (e) => {
      if (barRef.current && !barRef.current.contains(e.target)) setOpenMenu(null);
    };
    document.addEventListener('click', fn, false);
    return () => document.removeEventListener('click', fn, false);
  }, []);

  const showToast = msg => {
    setToast(msg);
    if (toastRef.current) clearTimeout(toastRef.current);
    toastRef.current = setTimeout(() => setToast(null), 2200);
  };

  const handleMenuOpen = label => {
    if (openMenu !== label) setRecentMenu(buildRecentFileItems());
    setOpenMenu(openMenu === label ? null : label);
  };

  const handleAction = action => {
    setOpenMenu(null);
    if (!action || action === 'wip') { showToast('해당 기능은 준비 중입니다.'); return; }
    if (action === 'exit') { showToast('브라우저 탭을 직접 닫아 주세요.'); return; }
    if (action === 'toggleTheme' && toggleTheme) { toggleTheme(); return; }
    if (action === 'toggleAutoRefresh') {
      setAutoRefresh((a) => !a);
      showToast('자동 새로고침을 전환했습니다.');
      return;
    }
    if (action.startsWith('navRecent:')) {
      if (onAction) onAction(action);
      return;
    }
    if (onAction) onAction(action);
  };

  // __RECENT_FILES__ placeholder 교체
  const resolveItems = items => items.map(item => {
    if (item.children === '__RECENT_FILES__') return { ...item, children: recentMenu };
    return item;
  });

  return (
    <>
      <nav ref={barRef} data-sqm-menubar="" style={S.bar}>
        {/* 브랜드 */}
        <span style={S.brand}>SQM Inventory</span>

        {/* 메뉴: 출고·파일·보고서·도구·View·도움말·품목 — 드롭다운은 각 버튼 기준 absolute, nav는 overflow visible */}
        <div className="sqm-menu-btn-group" style={S.menuRow}>
        {menuData.map(menu => (
          <div key={menu.label} style={{ position: 'relative', flexShrink: 0 }}>
            <button
              type="button"
              style={{
                ...S.menuBtn,
                ...(openMenu === menu.label ? S.menuBtnActive : {}),
              }}
              onClick={(e) => {
                e.stopPropagation();
                handleMenuOpen(menu.label);
              }}
              onMouseEnter={() => openMenu && handleMenuOpen(menu.label)}
            >
              {menu.label} ▾
            </button>
            {openMenu === menu.label && (
              <div style={S.dropdown} role="menu">
                <DropdownItems
                  items={resolveItems(menu.items)}
                  onAction={handleAction}
                />
              </div>
            )}
          </div>
        ))}
        </div>

        {/* ── 우측 고정 영역 ────────────────────────────────────── */}
        <div style={{
          marginLeft: 'auto', display: 'flex', alignItems: 'center',
          gap: 8, paddingLeft: 12, flexShrink: 0,
        }}>

          {/* ── 마지막 갱신 시각 ── */}
          <div style={{
            display: 'flex', flexDirection: 'column', alignItems: 'flex-end',
            gap: 1, flexShrink: 0,
          }}>
            <span style={{ fontSize: 9, color: 'var(--nav-text)', letterSpacing: '0.03em' }}>
              마지막 갱신
            </span>
            <span style={{
              fontSize: 11, fontWeight: 700,
              color: 'var(--nav-accent)',
              fontFamily: 'monospace', letterSpacing: '0.05em',
            }}>
              {fmtTime(lastRefresh)}
            </span>
          </div>

          {/* ── 수동 새로고침 버튼 ── */}
          <button
            onClick={() => { triggerRefresh(); onAction && onAction('refreshData'); }}
            title="새로고침 (데이터 재로드)"
            style={{
              display: 'flex', alignItems: 'center', gap: 5,
              padding: '5px 11px',
              background: 'rgba(77,163,245,0.12)',
              border: '1px solid rgba(77,163,245,0.3)',
              borderRadius: 20,
              cursor: 'pointer',
              color: 'var(--nav-accent)',
              fontSize: 12, fontWeight: 600,
              flexShrink: 0,
              transition: 'all 0.2s ease',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.background = 'rgba(77,163,245,0.22)';
              e.currentTarget.style.transform = 'scale(1.05)';
            }}
            onMouseLeave={e => {
              e.currentTarget.style.background = 'rgba(77,163,245,0.12)';
              e.currentTarget.style.transform = 'scale(1)';
            }}
          >
            <span style={{ fontSize: 13 }}>🔄</span>
            <span style={{ fontSize: 11 }}>새로고침</span>
          </button>

          {/* ── 자동 새로고침 토글 ── */}
          <button
            onClick={() => setAutoRefresh(a => !a)}
            title={autoRefresh ? `자동 새로고침 ON — ${countdown}초 후` : '자동 새로고침 OFF'}
            style={{
              display: 'flex', alignItems: 'center', gap: 5,
              padding: '5px 11px',
              background: autoRefresh
                ? 'rgba(46,204,113,0.12)'
                : 'rgba(255,255,255,0.05)',
              border: `1px solid ${autoRefresh ? 'rgba(46,204,113,0.35)' : 'rgba(255,255,255,0.1)'}`,
              borderRadius: 20,
              cursor: 'pointer',
              color: autoRefresh ? '#2ecc71' : 'var(--nav-text)',
              fontSize: 12, fontWeight: 600,
              flexShrink: 0,
              transition: 'all 0.2s ease',
              minWidth: 72,
              justifyContent: 'center',
            }}
            onMouseEnter={e => e.currentTarget.style.opacity = '0.8'}
            onMouseLeave={e => e.currentTarget.style.opacity = '1'}
          >
            <span style={{ fontSize: 11 }}>
              {autoRefresh ? `⏱ ${String(countdown).padStart(2,'0')}s` : '⏸ 정지'}
            </span>
          </button>

          {/* 테마 전환 버튼 — 크고 직관적 */}
          {toggleTheme && (
            <button
              onClick={toggleTheme}
              title={dark ? '라이트 모드로 전환' : '다크 모드로 전환'}
              style={{
                display: 'flex', alignItems: 'center', gap: 6,
                padding: '5px 12px',
                background: dark
                  ? 'rgba(255,255,255,0.08)'
                  : 'rgba(255,255,255,0.12)',
                border: `1px solid ${dark ? 'rgba(255,255,255,0.15)' : 'rgba(255,255,255,0.2)'}`,
                borderRadius: 20,           /* pill 형태 */
                cursor: 'pointer',
                color: 'var(--nav-text-active)',
                fontSize: 12,
                fontWeight: 600,
                letterSpacing: '0.02em',
                flexShrink: 0,
                transition: 'all 0.2s ease',
              }}
              onMouseEnter={e => {
                e.currentTarget.style.background = dark
                  ? 'rgba(255,255,255,0.14)'
                  : 'rgba(255,255,255,0.2)';
                e.currentTarget.style.transform = 'scale(1.03)';
              }}
              onMouseLeave={e => {
                e.currentTarget.style.background = dark
                  ? 'rgba(255,255,255,0.08)'
                  : 'rgba(255,255,255,0.12)';
                e.currentTarget.style.transform = 'scale(1)';
              }}
            >
              <span style={{ fontSize: 15, lineHeight: 1 }}>
                {dark ? '☀️' : '🌙'}
              </span>
              <span style={{ fontSize: 11 }}>
                {dark ? 'Light' : 'Dark'}
              </span>
            </button>
          )}
        </div>
      </nav>

      {/* Toast */}
      {toast && (
        <div style={{
          position: 'fixed', bottom: 28, left: '50%', transform: 'translateX(-50%)',
          background: '#334155', color: '#f1f5f9', padding: '10px 24px',
          borderRadius: 8, fontSize: 13, zIndex: 9999,
          boxShadow: '0 4px 16px rgba(0,0,0,0.4)', pointerEvents: 'none',
        }}>
          {toast}
        </div>
      )}
    </>
  );
}
