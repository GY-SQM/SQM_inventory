import { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, useNavigate } from 'react-router-dom';
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
import { exportCsv, integrityCheck } from './api/writeApi';

function AppInner({ dark, toggleTheme }) {
  const navigate = useNavigate();
  const [inboundOpen, setInboundOpen] = useState(false);
  const [outboundOpen, setOutboundOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [lotDetailOpen, setLotDetailOpen] = useState(false);
  const [selectedLot, setSelectedLot] = useState(null);
  const [doUpdateOpen, setDoUpdateOpen] = useState(false);
  const [locationMapOpen, setLocationMapOpen] = useState(false);
  const [allocationOpen, setAllocationOpen] = useState(false);

  const handleMenuAction = (action) => {
    switch (action) {
      case 'search':
        setSearchOpen(true);
        break;
      case 'inboundModal':
        setInboundOpen(true);
        break;
      case 'outboundModal':
        setOutboundOpen(true);
        break;
      case 'returnPage':
        navigate('/return');
        break;
      case 'doUpdateModal':
        setDoUpdateOpen(true);
        break;
      case 'locationMapModal':
        setLocationMapOpen(true);
        break;
      case 'allocationModal':
        setAllocationOpen(true);
        break;
      case 'exportCsv':
        exportCsv();
        break;
      case 'integrityCheck':
        navigate('/integrity');
        break;
      default:
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
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/inventory" element={<InventoryPage onLotClick={handleSelectLot} />} />
        <Route path="/tonbag" element={<TonbagPage />} />
        <Route path="/allocation" element={<AllocationPage />} />
        <Route path="/outbound" element={<OutboundPage />} />
        <Route path="/picked" element={<PickedPage />} />
        <Route path="/sold" element={<SoldPage />} />
        <Route path="/move" element={<MovePage />} />
        <Route path="/scan" element={<ScanPage />} />
        <Route path="/log" element={<LogPage />} />
        <Route path="/summary" element={<SummaryPage />} />
        <Route path="/cargo" element={<CargoOverviewPage />} />
        <Route path="/return" element={<ReturnPage />} />
        <Route path="/integrity" element={<IntegrityPage />} />
        <Route path="/outbound-history" element={<OutboundHistoryPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>

      <InboundModal open={inboundOpen} onClose={() => setInboundOpen(false)} />
      <OutboundModal open={outboundOpen} onClose={() => setOutboundOpen(false)} />
      <SearchModal open={searchOpen} onClose={() => setSearchOpen(false)} onSelectLot={handleSelectLot} />
      <LotDetailModal open={lotDetailOpen} onClose={() => setLotDetailOpen(false)} lotNo={selectedLot} />
      <DoUpdateModal open={doUpdateOpen} onClose={() => setDoUpdateOpen(false)} />
      <LocationMappingModal open={locationMapOpen} onClose={() => setLocationMapOpen(false)} />
      <AllocationInputModal open={allocationOpen} onClose={() => setAllocationOpen(false)} />
    </>
  );
}

function App() {
  const [dark, setDark] = useState(() => localStorage.getItem('sqm_theme') === 'dark');

  useEffect(() => {
    document.body.classList.toggle('dark', dark);
    localStorage.setItem('sqm_theme', dark ? 'dark' : 'light');
  }, [dark]);

  const toggleTheme = () => setDark(d => !d);

  return (
    <BrowserRouter>
      <AppInner dark={dark} toggleTheme={toggleTheme} />
    </BrowserRouter>
  );
}

export default App;
