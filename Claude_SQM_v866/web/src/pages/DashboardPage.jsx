import { useEffect, useState } from 'react';
import { getDashboardSummary, getDashboardByProduct } from '../api/dashboardApi';

export default function DashboardPage() {
  const [summary, setSummary] = useState(null);
  const [products, setProducts] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const ctrl = new AbortController();
    setLoading(true);
    Promise.all([getDashboardSummary(), getDashboardByProduct()])
      .then(([sum, prod]) => {
        if (!ctrl.signal.aborted) {
          setSummary(sum);
          setProducts(prod);
        }
      })
      .catch((e) => {
        if (e.name !== 'AbortError') setError(e.message);
      })
      .finally(() => setLoading(false));
    return () => ctrl.abort();
  }, []);

  if (loading) return <div style={{ padding: 32 }}>Loading dashboard...</div>;
  if (error) return <div style={{ padding: 32, color: 'red' }}>Error: {error}</div>;

  return (
    <div style={{ padding: 24 }}>
      <h2>Dashboard</h2>

      {summary && (
        <div>
          <h3>Status Summary</h3>
          <table border="1" cellPadding="6" style={{ borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th>Status</th>
                <th>Bags</th>
                <th>Weight (MT)</th>
              </tr>
            </thead>
            <tbody>
              {summary.items.map((item) => (
                <tr key={item.status}>
                  <td>{item.status}</td>
                  <td style={{ textAlign: 'right' }}>{item.bag_count}</td>
                  <td style={{ textAlign: 'right' }}>{item.weight_mt.toFixed(1)}</td>
                </tr>
              ))}
              <tr style={{ fontWeight: 'bold' }}>
                <td>TOTAL</td>
                <td style={{ textAlign: 'right' }}>{summary.totals.bag_count}</td>
                <td style={{ textAlign: 'right' }}>{summary.totals.weight_mt.toFixed(1)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}

      {products && (
        <div style={{ marginTop: 24 }}>
          <h3>By Product</h3>
          <table border="1" cellPadding="6" style={{ borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th>Product</th>
                <th>LOTs</th>
                <th>Bags</th>
                <th>Available (MT)</th>
                <th>Reserved (MT)</th>
                <th>Picked (MT)</th>
                <th>Outbound (MT)</th>
                <th>Total (MT)</th>
              </tr>
            </thead>
            <tbody>
              {products.rows.map((row) => (
                <tr key={row.product_name}>
                  <td>{row.product_name}</td>
                  <td style={{ textAlign: 'right' }}>{row.lot_count}</td>
                  <td style={{ textAlign: 'right' }}>{row.tonbag_count}</td>
                  <td style={{ textAlign: 'right' }}>{row.available_mt.toFixed(1)}</td>
                  <td style={{ textAlign: 'right' }}>{row.reserved_mt.toFixed(1)}</td>
                  <td style={{ textAlign: 'right' }}>{row.picked_mt.toFixed(1)}</td>
                  <td style={{ textAlign: 'right' }}>{row.outbound_mt.toFixed(1)}</td>
                  <td style={{ textAlign: 'right' }}>{row.total_mt.toFixed(1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p style={{ color: '#888', marginTop: 16, fontSize: 12 }}>
        Generated: {summary?.generated_at}
      </p>
    </div>
  );
}
