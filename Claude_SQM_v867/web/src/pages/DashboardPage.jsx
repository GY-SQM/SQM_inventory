import { useEffect, useState } from 'react';
import { getDashboardSummary, getDashboardByProduct } from '../api/dashboardApi';
import { getInsights, getStatusPieData } from '../api/aiApi';

const card = (bg) => ({
  padding: 16, borderRadius: 10, background: bg,
  border: '1px solid #e2e8f0', marginBottom: 12,
});
const th = { textAlign: 'left', padding: '8px 10px', background: '#f8fafc', borderBottom: '2px solid #e2e8f0', fontSize: 12, fontWeight: 700 };
const td = { padding: '6px 10px', borderBottom: '1px solid #f1f5f9', fontSize: 12 };
const tdR = { ...td, textAlign: 'right' };

const statusColors = { AVAILABLE: '#22c55e', RESERVED: '#eab308', PICKED: '#3b82f6', OUTBOUND: '#ef4444', SOLD: '#ef4444' };

function MiniBar({ data }) {
  if (!data || data.length === 0) return null;
  const total = data.reduce((s, d) => s + (d.count || 0), 0);
  if (total === 0) return null;
  return (
    <div style={{ display: 'flex', height: 24, borderRadius: 6, overflow: 'hidden', marginBottom: 12 }}>
      {data.map((d, i) => (
        <div key={i} title={`${d.label}: ${d.count} (${((d.count / total) * 100).toFixed(1)}%)`}
          style={{ width: `${(d.count / total) * 100}%`, background: statusColors[d.label] || '#94a3b8', minWidth: 2 }}
        />
      ))}
    </div>
  );
}

export default function DashboardPage() {
  const [summary, setSummary] = useState(null);
  const [products, setProducts] = useState(null);
  const [insights, setInsights] = useState(null);
  const [pieData, setPieData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const ctrl = new AbortController();
    setLoading(true);
    Promise.all([
      getDashboardSummary(),
      getDashboardByProduct(),
      getInsights().catch(() => null),
      getStatusPieData().catch(() => null),
    ])
      .then(([sum, prod, ins, pie]) => {
        if (!ctrl.signal.aborted) {
          setSummary(sum);
          setProducts(prod);
          setInsights(ins);
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
      <h2 style={{ fontSize: 20, marginBottom: 20, color: '#0f172a' }}>Dashboard</h2>

      {/* 상태 바 */}
      {pieData && <MiniBar data={pieData.data} />}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
        {/* 상태 요약 */}
        {summary && (
          <div style={card('#fff')}>
            <h3 style={{ fontSize: 14, marginBottom: 12 }}>Status Summary</h3>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr><th style={th}>Status</th><th style={{ ...th, textAlign: 'right' }}>Bags</th><th style={{ ...th, textAlign: 'right' }}>MT</th></tr>
              </thead>
              <tbody>
                {summary.items.map((item) => (
                  <tr key={item.status}>
                    <td style={td}>
                      <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: statusColors[item.status] || '#94a3b8', marginRight: 6 }} />
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

        {/* AI 인사이트 */}
        {insights && insights.insights && insights.insights.length > 0 && (
          <div style={card('#fffbeb')}>
            <h3 style={{ fontSize: 14, marginBottom: 12 }}>AI Insights</h3>
            {insights.insights.map((ins, i) => (
              <div key={i} style={{
                padding: '8px 12px', borderRadius: 6, marginBottom: 8,
                background: ins.severity === 'warning' ? '#fef3c7' : '#dbeafe',
                fontSize: 12, color: ins.severity === 'warning' ? '#92400e' : '#1e40af',
              }}>
                <strong>[{ins.type}]</strong> {ins.message}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 제품별 */}
      {products && (
        <div style={{ ...card('#fff'), marginTop: 20 }}>
          <h3 style={{ fontSize: 14, marginBottom: 12 }}>By Product</h3>
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
                    <td style={td}><strong>{row.product_name}</strong></td>
                    <td style={tdR}>{row.lot_count}</td>
                    <td style={tdR}>{row.tonbag_count}</td>
                    <td style={tdR}>{row.available_mt.toFixed(1)}</td>
                    <td style={tdR}>{row.reserved_mt.toFixed(1)}</td>
                    <td style={tdR}>{row.picked_mt.toFixed(1)}</td>
                    <td style={tdR}>{row.outbound_mt.toFixed(1)}</td>
                    <td style={tdR}><strong>{row.total_mt.toFixed(1)}</strong></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      <p style={{ color: '#94a3b8', marginTop: 16, fontSize: 11 }}>
        Generated: {summary?.generated_at}
      </p>
    </div>
  );
}
