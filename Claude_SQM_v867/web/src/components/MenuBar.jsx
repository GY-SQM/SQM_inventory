import { useState, useRef, useEffect } from 'react';
import { NavLink, useLocation } from 'react-router-dom';

const menuData = [
  {
    label: '검색',
    items: [
      { label: '통합 검색', action: 'search' },
    ],
  },
  {
    label: '도구',
    items: [
      { label: 'CSV 내보내기', action: 'exportCsv' },
      { label: '정합성 체크', action: 'integrityCheck' },
    ],
  },
  {
    label: '입고',
    items: [
      { label: '입고 파싱 (PDF/Excel)', action: 'inboundModal' },
    ],
  },
  {
    label: '출고',
    items: [
      { label: '출고 처리', action: 'outboundModal' },
    ],
  },
];

const navLinks = [
  { to: '/', label: 'Dashboard' },
  { to: '/inventory', label: 'Inventory' },
  { to: '/tonbag', label: 'Tonbag' },
  { to: '/allocation', label: 'Allocation' },
  { to: '/outbound', label: 'Outbound' },
  { to: '/picked', label: 'Picked' },
  { to: '/sold', label: 'Sold' },
];

const styles = {
  bar: {
    display: 'flex', alignItems: 'center', gap: 0,
    padding: '0 16px', background: '#1e293b',
    borderBottom: '2px solid #334155', flexWrap: 'wrap',
    minHeight: 42,
  },
  brand: {
    fontSize: 15, fontWeight: 700, color: '#38bdf8',
    marginRight: 20, padding: '8px 0', userSelect: 'none',
  },
  menuBtn: {
    position: 'relative', padding: '8px 14px',
    color: '#cbd5e1', fontSize: 13, fontWeight: 500,
    cursor: 'pointer', border: 'none', background: 'none',
    transition: 'background 0.15s',
  },
  menuBtnHover: {
    background: '#334155', color: '#f1f5f9',
  },
  dropdown: {
    position: 'absolute', top: '100%', left: 0,
    background: '#1e293b', border: '1px solid #475569',
    borderRadius: 6, padding: '4px 0', minWidth: 180,
    zIndex: 1000, boxShadow: '0 8px 24px rgba(0,0,0,0.3)',
  },
  dropdownItem: {
    display: 'block', width: '100%', padding: '8px 16px',
    color: '#e2e8f0', fontSize: 13, cursor: 'pointer',
    border: 'none', background: 'none', textAlign: 'left',
    transition: 'background 0.1s',
  },
  navArea: {
    display: 'flex', gap: 2, marginLeft: 'auto', alignItems: 'center',
  },
  navLink: (isActive) => ({
    padding: '6px 10px', fontSize: 12, fontWeight: isActive ? 700 : 400,
    color: isActive ? '#38bdf8' : '#94a3b8', textDecoration: 'none',
    borderBottom: isActive ? '2px solid #38bdf8' : '2px solid transparent',
    transition: 'color 0.15s',
  }),
  currentTab: {
    padding: '6px 10px', fontSize: 11, color: '#64748b',
    marginLeft: 8, fontStyle: 'italic',
  },
};

export default function MenuBar({ onAction }) {
  const [openMenu, setOpenMenu] = useState(null);
  const barRef = useRef(null);
  const location = useLocation();

  // 현재 탭 이름 결정
  const currentTab = navLinks.find(n => n.to === location.pathname)?.label || 'Dashboard';

  // 바깥 클릭 시 메뉴 닫기
  useEffect(() => {
    const handleClick = (e) => {
      if (barRef.current && !barRef.current.contains(e.target)) {
        setOpenMenu(null);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const handleAction = (action) => {
    setOpenMenu(null);
    if (onAction) onAction(action);
  };

  return (
    <nav ref={barRef} style={styles.bar}>
      <span style={styles.brand}>SQM Inventory</span>

      {/* 드롭다운 메뉴 */}
      {menuData.map((menu) => (
        <div key={menu.label} style={{ position: 'relative' }}>
          <button
            style={{
              ...styles.menuBtn,
              ...(openMenu === menu.label ? styles.menuBtnHover : {}),
            }}
            onClick={() => setOpenMenu(openMenu === menu.label ? null : menu.label)}
            onMouseEnter={() => openMenu && setOpenMenu(menu.label)}
          >
            {menu.label} ▾
          </button>
          {openMenu === menu.label && (
            <div style={styles.dropdown}>
              {menu.items.map((item) => (
                <button
                  key={item.action}
                  style={styles.dropdownItem}
                  onMouseEnter={(e) => e.target.style.background = '#334155'}
                  onMouseLeave={(e) => e.target.style.background = 'none'}
                  onClick={() => handleAction(item.action)}
                >
                  {item.label}
                </button>
              ))}
            </div>
          )}
        </div>
      ))}

      {/* 탭 네비게이션 */}
      <div style={styles.navArea}>
        {navLinks.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            style={({ isActive }) => styles.navLink(isActive)}
          >
            {link.label}
          </NavLink>
        ))}
        <span style={styles.currentTab}>[ {currentTab} ]</span>
      </div>
    </nav>
  );
}
