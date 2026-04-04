import { useState } from 'react';
import Modal from './Modal';
import { unifiedSearch } from '../api/writeApi';

const input = { width: '100%', padding: '6px 10px', border: '1px solid #d1d5db', borderRadius: 4, fontSize: 13 };
const label = { display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4, color: '#374151' };
const btn = (bg) => ({
  padding: '8px 20px', border: 'none', borderRadius: 6,
  color: '#fff', background: bg, fontSize: 13, fontWeight: 600, cursor: 'pointer',
});
const th = { textAlign: 'left', padding: '6px 8px', background: '#f1f5f9', borderBottom: '1px solid #e2e8f0', fontWeight: 600, fontSize: 11 };
const td = { padding: '5px 8px', borderBottom: '1px solid #f1f5f9', fontSize: 12 };

export default function SearchModal({ open, onClose, onSelectLot }) {
  const [keyword, setKeyword] = useState('');
  const [status, setStatus] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    setLoading(true);
    try {
      const params = {};
      if (keyword) params.keyword = keyword;
      if (status) params.status = status;
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;
      const res = await unifiedSearch(params);
      setResults(res);
    } catch (e) {
      setResults({ total: 0, rows: [], error: e.message });
    }
    setLoading(false);
  };

  return (
    <Modal open={open} onClose={onClose} title="통합 검색" width={800}>
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr auto', gap: 8, marginBottom: 16, alignItems: 'end' }}>
        <div><span style={label}>키워드</span><input style={input} value={keyword} onChange={(e) => setKeyword(e.target.value)} placeholder="LOT, SAP, BL, 제품명..." onKeyDown={(e) => e.key === 'Enter' && handleSearch()} /></div>
        <div>
          <span style={label}>상태</span>
          <select style={input} value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">전체</option>
            <option value="AVAILABLE">AVAILABLE</option>
            <option value="RESERVED">RESERVED</option>
            <option value="PICKED">PICKED</option>
            <option value="OUTBOUND">OUTBOUND</option>
          </select>
        </div>
        <div><span style={label}>시작일</span><input style={input} type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} /></div>
        <div><span style={label}>종료일</span><input style={input} type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} /></div>
        <button style={btn('#3b82f6')} onClick={handleSearch} disabled={loading}>{loading ? '...' : '검색'}</button>
      </div>

      {results && (
        <div>
          <p style={{ fontSize: 12, color: '#64748b', marginBottom: 8 }}>총 {results.total}건</p>
          <div style={{ maxHeight: 400, overflow: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  <th style={th}>LOT NO</th><th style={th}>UID</th><th style={th}>제품</th>
                  <th style={th}>상태</th><th style={th}>위치</th><th style={th}>중량(kg)</th>
                </tr>
              </thead>
              <tbody>
                {(results.rows || []).map((row, i) => (
                  <tr key={i} style={{ cursor: 'pointer' }}
                    onClick={() => onSelectLot && onSelectLot(row.lot_no)}
                    onMouseEnter={(e) => e.currentTarget.style.background = '#f1f5f9'}
                    onMouseLeave={(e) => e.currentTarget.style.background = ''}
                  >
                    <td style={td}>{row.lot_no}</td>
                    <td style={td}>{row.tonbag_uid}</td>
                    <td style={td}>{row.product_name}</td>
                    <td style={td}>{row.status}</td>
                    <td style={td}>{row.location}</td>
                    <td style={td}>{(row.weight || 0).toLocaleString()}</td>
                  </tr>
                ))}
                {(!results.rows || results.rows.length === 0) && (
                  <tr><td colSpan={6} style={{ ...td, textAlign: 'center', color: '#94a3b8' }}>결과 없음</td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </Modal>
  );
}
