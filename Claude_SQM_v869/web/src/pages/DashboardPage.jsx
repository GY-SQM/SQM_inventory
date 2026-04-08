import { useEffect, useMemo, useState } from 'react';
import { getDashboardSummary, getDashboardByProduct } from '../api/dashboardApi';
import { getStatusPieData } from '../api/aiApi';

const card = (bg) => ({
  padding: 16,
  borderRadius: 10,
  background: bg,
  border: '1px solid #e2e8f0',
  marginBottom: 16,
  boxShadow: '0 1px 3px rgba(15, 23, 42, 0.06), 0 1px 2px rgba(15, 23, 42, 0.04)',
});
const th = {
  textAlign: 'left',
  padding: '8px 10px',
  background: '#f8fafc',
  borderBottom: '2px solid #e2e8f0',
  fontSize: 12,
  fontWeight: 700,
};
const td = { padding: '6px 10px', borderBottom: '1px solid #f1f5f9', fontSize: 12 };
const tdR = { ...td, textAlign: 'right' };

const statusColors = { AVAILABLE: '#22c55e', RESERVED: '#eab308', PICKED: '#3b82f6', OUTBOUND: '#ef4444', SOLD: '#ef4444', OTHER: '#94a3b8' };

function summaryToBarData(summary) {
  if (!summary?.items?.length) return [];
  return summary.items
    .filter((item) => (item.bag_count || 0) > 0)
    .map((item) => ({ label: item.status, count: item.bag_count }));
}

function StatusBar({ data }) {
  if (!data || data.length === 0) {
    return (
      <div
        style={{
          height: 32,
          borderRadius: 8,
          background: '#e2e8f0',
          marginBottom: 16,
        }}
      />
    );
  }
  const total = data.reduce((s, d) => s + (d.count || 0), 0);
  if (total === 0) {
    return (
      <div
        style={{
          height: 32,
          borderRadius: 8,
          background: '#e2e8f0',
          marginBottom: 16,
        }}
      />
    );
  }
  return (
    <div
      style={{
        display: 'flex',
        height: 32,
        borderRadius: 8,
        overflow: 'hidden',
        marginBottom: 16,
        boxShadow: 'inset 0 0 0 1px rgba(15, 23, 42, 0.06)',
      }}
    >
      {data.map((d, i) => (
        <div
          key={i}
          title={`${d.label}: ${d.count} (${((d.count / total) * 100).toFixed(1)}%)`}
          style={{
            width: `${(d.count / total) * 100}%`,
            background: statusColors[d.label] || '#94a3b8',
            minWidth: d.count > 0 ? 2 : 0,
          }}
        />
      ))}
    </div>
  );
}

export default function DashboardPage() {
  const [summary, setSummary] = useState(null);
  const [products, setProducts] = useState(null);
  const [pieData, setPieData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const barData = useMemo(() => {
    if (pieData?.data?.length) return pieData.data;
    return summaryToBarData(summary);
  }, [pieData, summary]);

  useEffect(() => {
    const ctrl = new AbortController();
    setLoading(true);
    Promise.all([
      getDashboardSummary(),
      getDashboardByProduct(),
      getStatusPieData().catch(() => null),
    ])
      .then(([sum, prod, pie]) => {
        if (!ctrl.signal.aborted) {
          setSummary(sum);
          setProducts(prod);
          setPieData(pie);
        }
      })
      .catch((e) => {
        if (e.name !== 'AbortError') setError(e.message);
      })
      .finally(() => setLoading(false));
    return () => ctrl.abort();
  }, []);

  if (loading) return <div style={{ padding: 32, color: '#64748b' }}>Loading dashboard...</div>;
  if (error) return <div style={{ padding: 32, color: 'red' }}>Error: {error}</div>;

  return (
    <div style={{ padding: 24, maxWidth: 1200 }}>
      <h2 style={{ fontSize: 20, marginBottom: 16, color: '#0f172a', fontWeight: 700 }}>Dashboard</h2>

      <StatusBar data={barData} />

      {summary && (
        <div style={card('#fff')}>
          <h3 style={{ fontSize: 14, marginBottom: 12, fontWeight: 700, color: '#334155' }}>Status Summary</h3>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={th}>Status</th>
                <th style={{ ...th, textAlign: 'right' }}>Bags</th>
                <th style={{ ...th, textAlign: 'right' }}>MT</th>
              </tr>
            </thead>
            <tbody>
              {summary.items.map((item) => (
                <tr key={item.status}>
                  <td style={td}>
                    <span
                      style={{
                        display: 'inline-block',
                        width: 8,
                        height: 8,
                        borderRadius: '50%',
                        background: statusColors[item.status] || '#94a3b8',
                        marginRight: 6,
                        verticalAlign: 'middle',
                      }}
                    />
                    {item.status}
                  </td>
                  <td style={tdR}>{item.bag_count.toLocaleString()}</td>
                  <td style={tdR}>{item.weight_mt.toFixed(1)}</td>
                </tr>
              ))}
              <tr style={{ fontWeight: 700 }}>
                <td style={td}>TOTAL</td>
                <td style={tdR}>{summary.totals.bag_count.toLocaleString()}</td>
                <td style={tdR}>{summary.totals.weight_mt.toFixed(1)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}

      {products && (
        <div style={card('#fff')}>
          <h3 style={{ fontSize: 14, marginBottom: 12, fontWeight: 700, color: '#334155' }}>By Product</h3>
          <div style={{ overflow: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  <th style={th}>Product</th>
                  <th style={{ ...th, textAlign: 'right' }}>LOTs</th>
                  <th style={{ ...th, textAlign: 'right' }}>Bags</th>
                  <th style={{ ...th, textAlign: 'right' }}>Available</th>
                  <th style={{ ...th, textAlign: 'right' }}>Reserved</th>
                  <th style={{ ...th, textAlign: 'right' }}>Picked</th>
                  <th style={{ ...th, textAlign: 'right' }}>Outbound</th>
                  <th style={{ ...th, textAlign: 'right' }}>Total MT</th>
                </tr>
              </thead>
              <tbody>
                {products.rows.map((row) => (
                  <tr key={row.product_name}>
                    <td style={td}>
                      <strong>{row.product_name}</strong>
                    </td>
                    <td style={tdR}>{row.lot_count}</td>
                    <td style={tdR}>{row.tonbag_count}</td>
                    <td style={tdR}>{row.available_mt.toFixed(1)}</td>
                    <td style={tdR}>{row.reserved_mt.toFixed(1)}</td>
                    <td style={tdR}>{row.picked_mt.toFixed(1)}</td>
                    <td style={tdR}>{row.outbound_mt.toFixed(1)}</td>
                    <td style={tdR}>
                      <strong>{row.total_mt.toFixed(1)}</strong>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <p style={{ color: '#94a3b8', marginTop: 8, fontSize: 11 }}>
        Generated: {summary?.generated_at ?? products?.generated_at ?? '—'}
      </p>
    </div>
  );
}
