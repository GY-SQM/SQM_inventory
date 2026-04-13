/**
 * SearchModal v2 — P0-S6: 검색어 하이라이트 + 결과 타입별 이동
 * 배치: web/src/components/SearchModal.jsx (기존 덮어쓰기)
 *
 * 변경사항:
 *   1. 검색어 매칭 텍스트 볼드 하이라이트
 *   2. onSelectLot 콜백 유지 (기존 호환)
 *   3. 결과 없을 때 안내 메시지 개선
 *   4. Enter 키로 즉시 검색 (기존 유지)
 */
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
const td = { padding: '5px 8px', borderBottom: '1px dashed rgba(51,65,85,0.3)', fontSize: 12 };

const STATUS_COLOR = {
  AVAILABLE: '#22c55e', RESERVED: '#f59e0b', PICKED: '#3b82f6',
  OUTBOUND: '#8b5cf6', SOLD: '#6b7280', RETURN: '#ef4444',
};

/* ── 검색어 하이라이트 ── */
function Highlight({ text, keyword }) {
  if (!keyword || !text) return <>{text || '-'}</>;
  const str = String(text);
  const idx = str.toLowerCase().indexOf(keyword.toLowerCase());
  if (idx === -1) return <>{str}</>;
  return (
    <>
      {str.slice(0, idx)}
      <span style={{ background: '#fef08a', fontWeight: 700, borderRadius: 2, padding: '0 1px' }}>
        {str.slice(idx, idx + keyword.length)}
      </span>
      {str.slice(idx + keyword.length)}
    </>
  );
}

export default function SearchModal({ open, onClose, onSelectLot }) {
  const [keyword, setKeyword] = useState('');
  const [status, setStatus] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    if (!keyword && !status && !dateFrom && !dateTo) return;
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

  const handleRowClick = (row) => {
    if (onSelectLot) onSelectLot(row.lot_no);
  };

  const handleClose = () => {
    setKeyword(''); setStatus(''); setDateFrom(''); setDateTo('');
    setResults(null);
    onClose();
  };

  return (
    <Modal open={open} onClose={handleClose} title="통합 검색" width={800}>
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr auto', gap: 8, marginBottom: 16, alignItems: 'end' }}>
        <div>
          <span style={label}>키워드</span>
          <input style={input} value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            placeholder="LOT, SAP, BL, 제품명..."
            onKeyDown={(e) => e.key === 'Enter' && handleSearch()} />
        </div>
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
        <button style={btn('#3b82f6')} onClick={handleSearch} disabled={loading}>
          {loading ? '...' : '검색'}
        </button>
      </div>

      {results && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <p style={{ fontSize: 12, color: '#64748b', margin: 0 }}>
              총 <b>{results.total}</b>건
              {keyword && <span style={{ marginLeft: 8, color: '#94a3b8' }}>"{keyword}" 검색 결과</span>}
            </p>
            {results.rows?.length > 0 && (
              <span style={{ fontSize: 11, color: '#94a3b8' }}>행 클릭 → LOT 상세 보기</span>
            )}
          </div>

          {results.error && (
            <div style={{ padding: 8, background: '#fef2f2', borderRadius: 6, fontSize: 12, color: '#991b1b', marginBottom: 8 }}>
              {results.error}
            </div>
          )}

          <div style={{ maxHeight: 400, overflow: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  <th style={th}>LOT NO</th>
                  <th style={th}>UID</th>
                  <th style={th}>제품</th>
                  <th style={th}>상태</th>
                  <th style={th}>위치</th>
                  <th style={th}>중량(kg)</th>
                </tr>
              </thead>
              <tbody>
                {(results.rows || []).map((row, i) => (
                  <tr key={i} style={{ cursor: 'pointer' }}
                    onClick={() => handleRowClick(row)}
                    onMouseEnter={(e) => e.currentTarget.style.background = '#f1f5f9'}
                    onMouseLeave={(e) => e.currentTarget.style.background = ''}
                  >
                    <td style={{ ...td, fontWeight: 600, color: '#2563eb' }}>
                      <Highlight text={row.lot_no} keyword={keyword} />
                    </td>
                    <td style={td}>
                      <Highlight text={row.tonbag_uid} keyword={keyword} />
                    </td>
                    <td style={td}>
                      <Highlight text={row.product_name} keyword={keyword} />
                    </td>
                    <td style={td}>
                      <span style={{
                        background: (STATUS_COLOR[row.status] || '#94a3b8') + '18',
                        color: STATUS_COLOR[row.status] || '#94a3b8',
                        border: `1px solid ${STATUS_COLOR[row.status] || '#94a3b8'}44`,
                        borderRadius: 4, padding: '1px 6px', fontSize: 10, fontWeight: 700,
                      }}>
                        {row.status}
                      </span>
                    </td>
                    <td style={td}>{row.location || '-'}</td>
                    <td style={{ ...td, textAlign: 'right' }}>{(row.weight || 0).toLocaleString()}</td>
                  </tr>
                ))}
                {(!results.rows || results.rows.length === 0) && !results.error && (
                  <tr><td colSpan={6} style={{ ...td, textAlign: 'center', color: '#94a3b8', padding: 32 }}>
                    검색 결과가 없습니다. 다른 키워드로 시도해 보세요.
                  </td></tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </Modal>
  );
}
