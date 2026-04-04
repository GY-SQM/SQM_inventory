import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import DashboardPage from './pages/DashboardPage';
import InventoryPage from './pages/InventoryPage';
import TonbagPage from './pages/TonbagPage';
import AllocationPage from './pages/AllocationPage';
import PickedPage from './pages/PickedPage';
import SoldPage from './pages/SoldPage';
import OutboundPage from './pages/OutboundPage';

const navStyle = ({ isActive }) => ({
  fontWeight: isActive ? 800 : 500,
  color: isActive ? '#2563eb' : '#475569',
  textDecoration: 'none',
  padding: '6px 12px',
  borderRadius: 6,
  background: isActive ? '#eff6ff' : 'transparent',
  fontSize: 13,
});

function App() {
  return (
    <BrowserRouter>
      <nav style={{
        padding: '10px 24px', borderBottom: '2px solid #e2e8f0',
        display: 'flex', gap: 4, alignItems: 'center', flexWrap: 'wrap',
        background: '#ffffff',
      }}>
        <strong style={{ fontSize: 16, marginRight: 16, color: '#0f172a' }}>SQM Inventory</strong>
        <NavLink to="/" style={navStyle}>Dashboard</NavLink>
        <NavLink to="/inventory" style={navStyle}>Inventory</NavLink>
        <NavLink to="/tonbag" style={navStyle}>Tonbag</NavLink>
        <NavLink to="/allocation" style={navStyle}>Allocation</NavLink>
        <NavLink to="/outbound" style={navStyle}>Outbound</NavLink>
        <NavLink to="/picked" style={navStyle}>Picked</NavLink>
        <NavLink to="/sold" style={navStyle}>Sold</NavLink>
      </nav>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/inventory" element={<InventoryPage />} />
        <Route path="/tonbag" element={<TonbagPage />} />
        <Route path="/allocation" element={<AllocationPage />} />
        <Route path="/outbound" element={<OutboundPage />} />
        <Route path="/picked" element={<PickedPage />} />
        <Route path="/sold" element={<SoldPage />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
