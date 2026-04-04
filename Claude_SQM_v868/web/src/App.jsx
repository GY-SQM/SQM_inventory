import { useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
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
import { exportCsv, integrityCheck } from './api/writeApi';

function App() {
  const [inboundOpen, setInboundOpen] = useState(false);
  const [outboundOpen, setOutboundOpen] = useState(false);
  const [searchOpen, setSearchOpen] = useState(false);
  const [lotDetailOpen, setLotDetailOpen] = useState(false);
  const [selectedLot, setSelectedLot] = useState(null);

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
      case 'exportCsv':
        exportCsv();
        break;
      case 'integrityCheck':
        integrityCheck().then((res) => {
          alert(`정합성 체크 완료: ${res.total_issues}건 이슈 발견`);
        });
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
    <BrowserRouter>
      <MenuBar onAction={handleMenuAction} />
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/inventory" element={<InventoryPage onLotClick={handleSelectLot} />} />
        <Route path="/tonbag" element={<TonbagPage />} />
        <Route path="/allocation" element={<AllocationPage />} />
        <Route path="/outbound" element={<OutboundPage />} />
        <Route path="/picked" element={<PickedPage />} />
        <Route path="/sold" element={<SoldPage />} />
      </Routes>

      {/* 모달 */}
      <InboundModal open={inboundOpen} onClose={() => setInboundOpen(false)} />
      <OutboundModal open={outboundOpen} onClose={() => setOutboundOpen(false)} />
      <SearchModal open={searchOpen} onClose={() => setSearchOpen(false)} onSelectLot={handleSelectLot} />
      <LotDetailModal open={lotDetailOpen} onClose={() => setLotDetailOpen(false)} lotNo={selectedLot} />
    </BrowserRouter>
  );
}

export default App;
