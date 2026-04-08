import { useEffect, useState } from 'react';
import { getInventoryFilters, searchInventory } from '../api/inventoryApi';

const COLUMN_DEFS = [
  { key: 'no', label: 'No.', defaultVisible: true, align: 'center', render: (row, idx, page) => (page - 1) * 50 + idx + 1 },
  { key: 'lot_no', label: 'LOT NO', defaultVisible: true, align: 'left', isLink: true },
  { key: 'sap_no', label: 'SAP NO', defaultVisible: true, align: 'left' },
  { key: 'bl_no', label: 'BL NO', defaultVisible: true, align: 'left' },
  { key: 'product_name', label: 'PRODUCT', defaultVisible: true, align: 'left' },
  { key: 'status', label: 'STATUS', defaultVisible: true, align: 'center', isBadge: true },
  { key: 'current_weight', label: 'Balance(Kg)', defaultVisible: true, align: 'right', fmt: true },
  { key: 'net_weight', label: 'NET(Kg)', defaultVisible: true, align: 'right', fmt: true },
  { key: 'container_no', label: 'CONTAINER', defaultVisible: true, align: 'left' },
  { key: 'mxbg_pallet', label: 'MXBG', defaultVisible: true, align: 'center' },
  { key: 'tonbag_uid', label: 'TONBAG UID', defaultVisible: false, align: 'left' },
  { key: 'tonbag_no', label: 'TONBAG NO', defaultVisible: false, align: 'center' },
  { key: 'location', label: 'LOCATION', defaultVisible: true, align: 'center' },
  { key: 'weight_kg', label: 'Weight(Kg)', defaultVisible: false, align: 'right', fmt: true },
  { key: 'salar_invoice_no', label: 'INVOICE NO', defaultVisible: true, align: 'left' },
  { key: 'ship_date', label: 'SHIP DATE', defaultVisible: true, align: 'center' },
  { key: 'arrival_date', label: 'ARRIVAL', defaultVisible: true, align: 'center' },
  { key: 'con_return', label: 'CON RETURN', defaultVisible: true, align: 'center' },
  { key: 'free_time', label: 'FREE TIME', defaultVisible: true, align: 'center' },
  { key: 'warehouse', label: 'WH', defaultVisible: false, align: 'center' },
  { key: 'customs', label: 'CUSTOMS', defaultVisible: false, align: 'center' },
  { key: 'initial_weight', label: 'Inbound(Kg)', defaultVisible: false, align: 'right', fmt: true },
  { key: 'picked_weight', label: 'Outbound(Kg)', defaultVisible: false, align: 'right', fmt: true },
  { key: 'is_sample', label: 'SAMPLE', defaultVisible: false, align: 'center', render: (row) => row.is_sample ? 'Y' : '' },
  { key: 'inbound_date', label: 'INBOUND', defaultVisible: false, align: 'center' },
];

const thStyle = {
  padding: '8px 6px', textAlign: 'center', background: '#f8fafc',
  borderBottom: '2px solid #e2e8f0', fontSize: 11, fontWeight: 700,
  position: 'sticky', top: 0, whiteSpace: 'nowrap',
};
const tdBase = { padding: '5px 6px', borderBottom: '1px solid #f1f5f9', fontSize: 12, whiteSpace: 'nowrap' };

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

function initVisibleCols() {
  const v = {};
  COLUMN_DEFS.forEach(c => { v[c.key] = c.defaultVisible; });
  return v;
}

export default function InventoryPage({ onLotClick }) {
  const [filters, setFilters] = useState(null);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [visibleCols, setVisibleCols] = useState(initVisibleCols);

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

  const toggleCol = (key) => setVisibleCols(prev => ({ ...prev, [key]: !prev[key] }));
  const activeCols = COLUMN_DEFS.filter(c => visibleCols[c.key]);

  const renderCell = (col, row, idx) => {
    if (col.render) return col.render(row, idx, results?.page || 1);
    if (col.isBadge) return <StatusBadge status={row[col.key]} />;
    if (col.isLink) return (
      <span style={{ cursor: onLotClick ? 'pointer' : 'default', color: onLotClick ? '#2563eb' : undefined, textDecoration: onLotClick ? 'underline' : undefined }}
            onClick={() => onLotClick && onLotClick(row.lot_no)}>{row.lot_no}</span>
    );
    const val = row[col.key];
    if (col.fmt) return fmt(val);
    return val || '-';
  };

  return (
    <div style={{ padding: 24 }}>
      <h2 style={{ marginBottom: 16 }}>SQM Inventory Search</h2>

      <form onSubmit={onSearch} style={{ marginBottom: 10, display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
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

      {/* Column Toggle Bar */}
      <div style={{
        display: 'flex', flexWrap: 'wrap', gap: '2px 10px', padding: '6px 10px',
        background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 6, marginBottom: 10,
        fontSize: 11, alignItems: 'center',
      }}>
        <span style={{ fontWeight: 700, color: '#475569', marginRight: 4 }}>Columns:</span>
        {COLUMN_DEFS.map(col => (
          <label key={col.key} style={{ display: 'flex', alignItems: 'center', gap: 2, cursor: 'pointer', color: '#64748b' }}>
            <input type="checkbox" checked={!!visibleCols[col.key]} onChange={() => toggleCol(col.key)}
              style={{ width: 13, height: 13 }} />
            {col.label}
          </label>
        ))}
      </div>

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
            <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: activeCols.length * 100 }}>
              <thead>
                <tr>
                  {activeCols.map(col => (
                    <th key={col.key} style={thStyle}>{col.label}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {results.rows.length === 0 ? (
                  <tr><td colSpan={activeCols.length} style={{ ...tdBase, textAlign: 'center', padding: 24, color: '#94a3b8' }}>No results found</td></tr>
                ) : (
                  results.rows.map((row, idx) => (
                    <tr key={row.tonbag_id}
                        onMouseEnter={(e) => e.currentTarget.style.background = '#f8fafc'}
                        onMouseLeave={(e) => e.currentTarget.style.background = ''}>
                      {activeCols.map(col => (
                        <td key={col.key} style={{ ...tdBase, textAlign: col.align || 'left' }}>
                          {renderCell(col, row, idx)}
                        </td>
                      ))}
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
