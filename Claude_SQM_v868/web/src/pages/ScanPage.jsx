import { useState } from 'react';
import { fetchJson } from '../api/client';

export default function ScanPage() {
  const [barcode, setBarcode] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleScan = async () => {
    if (!barcode.trim()) return;
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const data = await fetchJson(`/search/unified?keyword=${encodeURIComponent(barcode.trim())}`);
      setResult(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleScan();
  };

  return (
    <div style={{ padding: 24, maxWidth: 900, margin: '0 auto' }}>
      <h2 style={{ marginBottom: 16 }}>Scan / Barcode Lookup</h2>
      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        <input
          style={{ flex: 1, padding: '8px 12px', fontSize: 16, border: '1px solid #ccc', borderRadius: 4 }}
          placeholder="LOT NO / UID / Barcode"
          value={barcode}
          onChange={(e) => setBarcode(e.target.value)}
          onKeyDown={handleKeyDown}
          autoFocus
        />
        <button
          onClick={handleScan}
          disabled={loading}
          style={{ padding: '8px 20px', fontSize: 14, background: '#2563eb', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer' }}
        >
          {loading ? '...' : 'Search'}
        </button>
      </div>

      {error && <div style={{ color: '#dc2626', marginBottom: 12 }}>{error}</div>}

      {result && (
        <div>
          <div style={{ marginBottom: 8, fontWeight: 600 }}>
            Results: {result.total ?? result.rows?.length ?? 0}
          </div>
          {result.rows && result.rows.length > 0 ? (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead>
                <tr style={{ background: '#f1f5f9' }}>
                  {Object.keys(result.rows[0]).map((k) => (
                    <th key={k} style={{ border: '1px solid #e2e8f0', padding: '6px 8px', textAlign: 'left' }}>{k}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {result.rows.map((row, i) => (
                  <tr key={i} style={{ background: i % 2 ? '#f8fafc' : '#fff' }}>
                    {Object.values(row).map((v, j) => (
                      <td key={j} style={{ border: '1px solid #e2e8f0', padding: '4px 8px' }}>
                        {v != null ? String(v) : ''}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div style={{ color: '#64748b' }}>No results found</div>
          )}
        </div>
      )}
    </div>
  );
}
