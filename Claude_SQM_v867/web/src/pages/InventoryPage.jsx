import { useEffect, useState } from 'react';
import { getInventoryFilters, searchInventory } from '../api/inventoryApi';

const thStyle = {
  padding: '8px 6px', textAlign: 'center', background: '#f8fafc',
  borderBottom: '2px solid #e2e8f0', fontSize: 11, fontWeight: 700,
  position: 'sticky', top: 0, whiteSpace: 'nowrap',
};
const tdStyle = { padding: '5px 6px', borderBottom: '1px solid #f1f5f9', fontSize: 12, whiteSpace: 'nowrap' };
const tdRight = { ...tdStyle, textAlign: 'right' };
const tdCenter = { ...tdStyle, textAlign: 'center' };

function StatusBadge({ status }) {
  const colors = {
    AVAILABLE: { bg: '#e8fff1', fg: '#127a3a' },
    RESERVED: { bg: '#fff7df', fg: '#946200' },
    PICKED: { bg: '#eef4ff', fg: '#1f57b0' },
    OUTBOUND: { bg: '#f3ecff', fg: '#6a35c1' },
  };
  const c = colors[status] || { bg: '#f3f4f6', fg: '#4b5563' };
  return (
    <span style={{
      display: 'inline-block', padding: '2px 7px', borderRadius: 999,
      fontSize: 10, fontWeight: 700, backgroundColor: c.bg, color: c.fg,
    }}>{status || 'UNKNOWN'}</span>
  );
}

function fmt(v) {
  const n = Number(v || 0);
  return n ? n.toLocaleString(undefined, { maximumFractionDigits: 1 }) : '0';
}

export default function InventoryPage({ onLotClick }) {
  const [filters, setFilters] = useState(null);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [search, setSearch] = useState({
    keyword: '', status: '', product_name: '', location: '', lot_no: '', page: 1,
  });

  useEffect(() => {
    const ctrl = new AbortController();
    getInventoryFilters()
      .then((data) => { if (!ctrl.signal.aborted) setFilters(data); })
      .catch((e) => { if (e.name !== 'AbortError') setError(e.message); });
    return () => ctrl.abort();
  }, []);

  useEffect(() => {
    const ctrl = new AbortController();
    setLoading(true);
    searchInventory(search)
      .then((data) => { if (!ctrl.signal.aborted) setResults(data); })
      .catch((e) => { if (e.name !== 'AbortError') setError(e.message); })
      .finally(() => setLoading(false));
    return () => ctrl.abort();
  }, [search]);

  const onSearch = (e) => { e.preventDefault(); setSearch((prev) => ({ ...prev, page: 1 })); };
  const onReset = () => setSearch({ keyword: '', status: '', product_name: '', location: '', lot_no: '', page: 1 });
  const totalPages = results ? Math.max(1, Math.ceil(results.total / 50)) : 1;

  return (
    <div style={{ padding: 24 }}>
      <h2 style={{ marginBottom: 16 }}>SQM Inventory Search</h2>

      <form onSubmit={onSearch} style={{ marginBottom: 14, display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
        <input placeholder="Keyword" value={search.keyword}
          onChange={(e) => setSearch((s) => ({ ...s, keyword: e.target.value }))}
          style={{ padding: 5, width: 180, fontSize: 12 }} />
        <input placeholder="LOT No" value={search.lot_no}
          onChange={(e) => setSearch((s) => ({ ...s, lot_no: e.target.value }))}
          style={{ padding: 5, width: 110, fontSize: 12 }} />
        <select value={search.status} onChange={(e) => setSearch((s) => ({ ...s, status: e.target.value, page: 1 }))}
          style={{ padding: 5, fontSize: 12 }}>
          <option value="">All Status</option>
          {filters?.statuses.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <select value={search.product_name} onChange={(e) => setSearch((s) => ({ ...s, product_name: e.target.value, page: 1 }))}
          style={{ padding: 5, fontSize: 12 }}>
          <option value="">All Products</option>
          {filters?.products.map((p) => <option key={p} value={p}>{p}</option>)}
        </select>
        <select value={search.location} onChange={(e) => setSearch((s) => ({ ...s, location: e.target.value, page: 1 }))}
          style={{ padding: 5, fontSize: 12 }}>
          <option value="">All Locations</option>
          {filters?.locations.map((loc) => <option key={loc} value={loc}>{loc}</option>)}
        </select>
        <button type="submit" style={{ padding: '5px 14px', fontWeight: 700, fontSize: 12 }}>Search</button>
        <button type="button" onClick={onReset} style={{ padding: '5px 10px', fontSize: 12 }}>Reset</button>
      </form>

      {error && <div style={{ color: 'red', marginBottom: 8, padding: 8, background: '#fef2f2', borderRadius: 6, fontSize: 12 }}>Error: {error}</div>}
      {loading && <div style={{ padding: 12, color: '#475569' }}>Loading...</div>}

      {results && !loading && (
        <>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
            <span style={{ fontSize: 12, color: '#475569' }}>Total: <b>{results.total.toLocaleString()}</b></span>
            <div style={{ display: 'flex', gap: 6, alignItems: 'center', fontSize: 12 }}>
              <button disabled={results.page <= 1} onClick={() => setSearch((s) => ({ ...s, page: s.page - 1 }))}>Prev</button>
              <span>{results.page} / {totalPages}</span>
              <button disabled={results.page >= totalPages} onClick={() => setSearch((s) => ({ ...s, page: s.page + 1 }))}>Next</button>
            </div>
          </div>

          <div style={{ overflow: 'auto', maxHeight: '72vh', border: '1px solid #e2e8f0', borderRadius: 6 }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 2200 }}>
              <thead>
                <tr>
                  <th style={thStyle}>No.</th>
                  <th style={thStyle}>LOT NO</th>
                  <th style={thStyle}>SAP NO</th>
                  <th style={thStyle}>BL NO</th>
                  <th style={thStyle}>PRODUCT</th>
                  <th style={thStyle}>STATUS</th>
                  <th style={thStyle}>Balance(Kg)</th>
                  <th style={thStyle}>NET(Kg)</th>
                  <th style={thStyle}>CONTAINER</th>
                  <th style={thStyle}>MXBG</th>
                  <th style={thStyle}>TONBAG UID</th>
                  <th style={thStyle}>TONBAG NO</th>
                  <th style={thStyle}>LOCATION</th>
                  <th style={thStyle}>Weight(Kg)</th>
                  <th style={thStyle}>INVOICE NO</th>
                  <th style={thStyle}>SHIP DATE</th>
                  <th style={thStyle}>ARRIVAL</th>
                  <th style={thStyle}>CON RETURN</th>
                  <th style={thStyle}>FREE TIME</th>
                  <th style={thStyle}>WAREHOUSE</th>
                  <th style={thStyle}>SAMPLE</th>
                  <th style={thStyle}>INBOUND</th>
                </tr>
              </thead>
              <tbody>
                {results.rows.length === 0 ? (
                  <tr><td colSpan={22} style={{ ...tdCenter, padding: 24, color: '#94a3b8' }}>No results found</td></tr>
                ) : (
                  results.rows.map((row, idx) => (
                    <tr key={row.tonbag_id}
                        onMouseEnter={(e) => e.currentTarget.style.background = '#f8fafc'}
                        onMouseLeave={(e) => e.currentTarget.style.background = ''}>
                      <td style={tdCenter}>{(results.page - 1) * 50 + idx + 1}</td>
                      <td style={{ ...tdStyle, cursor: onLotClick ? 'pointer' : 'default', color: onLotClick ? '#2563eb' : undefined, textDecoration: onLotClick ? 'underline' : undefined }} onClick={() => onLotClick && onLotClick(row.lot_no)}>{row.lot_no}</td>
                      <td style={tdStyle}>{row.sap_no || '-'}</td>
                      <td style={tdStyle}>{row.bl_no || '-'}</td>
                      <td style={tdStyle}>{row.product_name || '-'}</td>
                      <td style={tdCenter}><StatusBadge status={row.status} /></td>
                      <td style={tdRight}>{fmt(row.current_weight)}</td>
                      <td style={tdRight}>{fmt(row.net_weight)}</td>
                      <td style={tdStyle}>{row.container_no || '-'}</td>
                      <td style={tdCenter}>{row.mxbg_pallet || '-'}</td>
                      <td style={tdStyle}>{row.tonbag_uid || '-'}</td>
                      <td style={tdCenter}>{row.tonbag_no || '-'}</td>
                      <td style={tdCenter}>{row.location || '-'}</td>
                      <td style={tdRight}>{fmt(row.weight_kg)}</td>
                      <td style={tdStyle}>{row.salar_invoice_no || '-'}</td>
                      <td style={tdCenter}>{row.ship_date || '-'}</td>
                      <td style={tdCenter}>{row.arrival_date || '-'}</td>
                      <td style={tdCenter}>{row.con_return || '-'}</td>
                      <td style={tdCenter}>{row.free_time || '-'}</td>
                      <td style={tdCenter}>{row.warehouse || '-'}</td>
                      <td style={tdCenter}>{row.is_sample ? 'Y' : ''}</td>
                      <td style={tdCenter}>{row.inbound_date || '-'}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          <div style={{ marginTop: 6, fontSize: 10, color: '#94a3b8', textAlign: 'right' }}>
            Generated: {results.generated_at}
          </div>
        </>
      )}
    </div>
  );
}
