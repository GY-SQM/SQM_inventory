import { useState, useEffect } from 'react';
import { fetchJson } from '../api/client';

export default function CargoOverviewPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const [summary, byProduct, locationSummary] = await Promise.all([
          fetchJson('/dashboard/summary'),
          fetchJson('/dashboard/by-product'),
          fetchJson('/dashboard/location-summary'),
        ]);
        if (!cancelled) setData({ summary, byProduct, locationSummary });
      } catch (err) {
        if (!cancelled) setError(err.message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => { cancelled = true; };
  }, []);

  if (loading) return <div style={{ padding: 24 }}>Loading...</div>;
  if (error) return <div style={{ padding: 24, color: '#dc2626' }}>{error}</div>;
  if (!data) return null;

  const s = data.summary;

  return (
    <div style={{ padding: 24, maxWidth: 1100, margin: '0 auto' }}>
      <h2 style={{ marginBottom: 16 }}>Cargo Overview</h2>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 12, marginBottom: 24 }}>
        {[
          { label: 'Total LOTs', value: s.total_lots },
          { label: 'Total Tonbags', value: s.total_tonbags },
          { label: 'Available', value: s.available_tonbags },
          { label: 'Picked', value: s.picked_tonbags },
          { label: 'Outbound', value: s.outbound_tonbags },
          { label: 'Total Weight(MT)', value: s.total_weight_mt?.toFixed(2) },
        ].map((c, i) => (
          <div key={i} style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 8, padding: 16, textAlign: 'center' }}>
            <div style={{ fontSize: 12, color: '#64748b' }}>{c.label}</div>
            <div style={{ fontSize: 22, fontWeight: 700, marginTop: 4 }}>{c.value ?? '-'}</div>
          </div>
        ))}
      </div>

      {data.locationSummary?.rows?.length > 0 && (
        <>
          <h3 style={{ marginBottom: 8 }}>Location Summary</h3>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13, marginBottom: 24 }}>
            <thead>
              <tr style={{ background: '#f1f5f9' }}>
                <th style={{ border: '1px solid #e2e8f0', padding: '6px 8px' }}>Location</th>
                <th style={{ border: '1px solid #e2e8f0', padding: '6px 8px' }}>Count</th>
                <th style={{ border: '1px solid #e2e8f0', padding: '6px 8px' }}>Weight(Kg)</th>
              </tr>
            </thead>
            <tbody>
              {data.locationSummary.rows.map((r, i) => (
                <tr key={i} style={{ background: i % 2 ? '#f8fafc' : '#fff' }}>
                  <td style={{ border: '1px solid #e2e8f0', padding: '4px 8px' }}>{r.location || '(empty)'}</td>
                  <td style={{ border: '1px solid #e2e8f0', padding: '4px 8px', textAlign: 'right' }}>{r.count}</td>
                  <td style={{ border: '1px solid #e2e8f0', padding: '4px 8px', textAlign: 'right' }}>{r.total_weight?.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

      {data.byProduct?.rows?.length > 0 && (
        <>
          <h3 style={{ marginBottom: 8 }}>By Product</h3>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ background: '#f1f5f9' }}>
                <th style={{ border: '1px solid #e2e8f0', padding: '6px 8px' }}>Product</th>
                <th style={{ border: '1px solid #e2e8f0', padding: '6px 8px' }}>LOTs</th>
                <th style={{ border: '1px solid #e2e8f0', padding: '6px 8px' }}>Tonbags</th>
                <th style={{ border: '1px solid #e2e8f0', padding: '6px 8px' }}>Weight(MT)</th>
              </tr>
            </thead>
            <tbody>
              {data.byProduct.rows.map((r, i) => (
                <tr key={i} style={{ background: i % 2 ? '#f8fafc' : '#fff' }}>
                  <td style={{ border: '1px solid #e2e8f0', padding: '4px 8px' }}>{r.product}</td>
                  <td style={{ border: '1px solid #e2e8f0', padding: '4px 8px', textAlign: 'right' }}>{r.lot_count}</td>
                  <td style={{ border: '1px solid #e2e8f0', padding: '4px 8px', textAlign: 'right' }}>{r.tonbag_count}</td>
                  <td style={{ border: '1px solid #e2e8f0', padding: '4px 8px', textAlign: 'right' }}>{r.total_weight_mt?.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
  );
}
