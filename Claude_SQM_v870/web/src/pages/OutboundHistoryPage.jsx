import { useState, useEffect } from 'react';
import { fetchJson } from '../api/client';

const thStyle = { padding: '6px 8px', textAlign: 'center', background: '#f8fafc', borderBottom: '2px solid #e2e8f0', fontSize: 11, fontWeight: 700, whiteSpace: 'nowrap' };
const tdStyle = { padding: '5px 8px', borderBottom: '1px solid #f1f5f9', fontSize: 12, whiteSpace: 'nowrap' };
const tdR = { ...tdStyle, textAlign: 'right' };
const tdC = { ...tdStyle, textAlign: 'center' };

function fmt(v) {
  const n = Number(v || 0);
  return n ? n.toLocaleString(undefined, { maximumFractionDigits: 1 }) : '0';
}

export default function OutboundHistoryPage() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState({ lot_no: '', customer: '', limit: 100 });

  const load = () => {
    setLoading(true);
    const qs = new URLSearchParams();
    if (filter.lot_no) qs.set('lot_no', filter.lot_no);
    if (filter.customer) qs.set('customer', filter.customer);
    qs.set('limit', String(filter.limit));
    fetchJson(`/advanced/outbound-history?${qs.toString()}`)
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, []);

  return (
    <div style={{ padding: 24 }}>
      <h2 style={{ marginBottom: 12 }}>Outbound History</h2>

      <div style={{ display: 'flex', gap: 6, marginBottom: 12, flexWrap: 'wrap', alignItems: 'center' }}>
        <input placeholder="LOT No" value={filter.lot_no}
          onChange={e => setFilter(f => ({ ...f, lot_no: e.target.value }))}
          style={{ padding: 5, width: 150, fontSize: 12 }} />
        <input placeholder="Customer" value={filter.customer}
          onChange={e => setFilter(f => ({ ...f, customer: e.target.value }))}
          style={{ padding: 5, width: 150, fontSize: 12 }} />
        <button onClick={load} style={{ padding: '5px 14px', fontWeight: 700, fontSize: 12 }}>Search</button>
      </div>

      {loading && <div style={{ padding: 12, color: '#475569' }}>Loading...</div>}

      {data && !loading && (
        <>
          <div style={{ fontSize: 12, color: '#475569', marginBottom: 6 }}>Total: <b>{data.total}</b></div>
          <div style={{ overflow: 'auto', maxHeight: '65vh', border: '1px solid #e2e8f0', borderRadius: 6 }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 800 }}>
              <thead>
                <tr>
                  <th style={thStyle}>LOT NO</th>
                  <th style={thStyle}>Product</th>
                  <th style={thStyle}>SAP NO</th>
                  <th style={thStyle}>Tonbag UID</th>
                  <th style={thStyle}>Picking No</th>
                  <th style={thStyle}>Customer</th>
                  <th style={thStyle}>Qty(Kg)</th>
                  <th style={thStyle}>Qty(MT)</th>
                  <th style={thStyle}>Status</th>
                  <th style={thStyle}>Delivery</th>
                </tr>
              </thead>
              <tbody>
                {(!data.rows || data.rows.length === 0) ? (
                  <tr><td colSpan={10} style={{ ...tdC, padding: 24, color: '#94a3b8' }}>No results</td></tr>
                ) : data.rows.map((r, i) => (
                  <tr key={i}>
                    <td style={tdStyle}>{r.lot_no}</td>
                    <td style={tdStyle}>{r.product || '-'}</td>
                    <td style={tdStyle}>{r.sap_no || '-'}</td>
                    <td style={tdStyle}>{r.tonbag_uid || '-'}</td>
                    <td style={tdStyle}>{r.picking_no || '-'}</td>
                    <td style={tdStyle}>{r.customer || '-'}</td>
                    <td style={tdR}>{fmt(r.sold_qty_kg)}</td>
                    <td style={tdR}>{fmt(r.sold_qty_mt)}</td>
                    <td style={tdC}>{r.status || '-'}</td>
                    <td style={tdC}>{r.delivery_date || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {data.generated_at && <div style={{ marginTop: 6, fontSize: 10, color: '#94a3b8', textAlign: 'right' }}>Generated: {data.generated_at}</div>}
        </>
      )}
    </div>
  );
}
