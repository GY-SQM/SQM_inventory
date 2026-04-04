import { useEffect, useState } from 'react';

const th = {
  padding: '8px 6px', textAlign: 'center', background: '#f8fafc',
  borderBottom: '2px solid #e2e8f0', fontSize: 11, fontWeight: 700,
  position: 'sticky', top: 0, whiteSpace: 'nowrap',
};
const td = { padding: '5px 6px', borderBottom: '1px solid #f1f5f9', fontSize: 12, whiteSpace: 'nowrap' };

function StatusBadge({ status }) {
  const c = {
    AVAILABLE: { bg: '#e8fff1', fg: '#127a3a' }, RESERVED: { bg: '#fff7df', fg: '#946200' },
    PICKED: { bg: '#eef4ff', fg: '#1f57b0' }, OUTBOUND: { bg: '#f3ecff', fg: '#6a35c1' },
    CANCELLED: { bg: '#fef2f2', fg: '#b91c1c' }, ACTIVE: { bg: '#e8fff1', fg: '#127a3a' },
  }[status] || { bg: '#f3f4f6', fg: '#4b5563' };
  return <span style={{ display: 'inline-block', padding: '2px 7px', borderRadius: 999, fontSize: 10, fontWeight: 700, backgroundColor: c.bg, color: c.fg }}>{status || '-'}</span>;
}

export default function DataTable({ title, columns, fetchFn, searchFields = [] }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState({});
  const [page, setPage] = useState(1);

  const load = () => {
    setLoading(true);
    setError(null);
    fetchFn({ ...search, page })
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => { load(); }, [page]);

  const totalPages = data ? Math.max(1, Math.ceil(data.total / 50)) : 1;

  return (
    <div style={{ padding: 24 }}>
      <h2 style={{ marginBottom: 14 }}>{title}</h2>

      {searchFields.length > 0 && (
        <div style={{ display: 'flex', gap: 6, marginBottom: 12, flexWrap: 'wrap', alignItems: 'center' }}>
          {searchFields.map((sf) => (
            <input key={sf.key} placeholder={sf.label} value={search[sf.key] || ''}
              onChange={(e) => setSearch((s) => ({ ...s, [sf.key]: e.target.value }))}
              style={{ padding: 5, width: sf.width || 140, fontSize: 12 }} />
          ))}
          <button onClick={() => { setPage(1); load(); }} style={{ padding: '5px 14px', fontWeight: 700, fontSize: 12 }}>Search</button>
          <button onClick={() => { setSearch({}); setPage(1); setTimeout(load, 50); }} style={{ padding: '5px 10px', fontSize: 12 }}>Reset</button>
        </div>
      )}

      {error && <div style={{ color: 'red', marginBottom: 8, padding: 8, background: '#fef2f2', borderRadius: 6, fontSize: 12 }}>{error}</div>}
      {loading && <div style={{ padding: 12, color: '#475569' }}>Loading...</div>}

      {data && !loading && (
        <>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6, fontSize: 12, color: '#475569' }}>
            <span>Total: <b>{(data.total || 0).toLocaleString()}</b></span>
            <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
              <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>Prev</button>
              <span>{page} / {totalPages}</span>
              <button disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>Next</button>
            </div>
          </div>

          <div style={{ overflow: 'auto', maxHeight: '72vh', border: '1px solid #e2e8f0', borderRadius: 6 }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: columns.length * 120 }}>
              <thead>
                <tr>{columns.map((c) => <th key={c.key} style={th}>{c.label}</th>)}</tr>
              </thead>
              <tbody>
                {(data.rows || []).length === 0 ? (
                  <tr><td colSpan={columns.length} style={{ ...td, textAlign: 'center', padding: 24, color: '#94a3b8' }}>No data</td></tr>
                ) : (
                  data.rows.map((row, idx) => (
                    <tr key={row.id || idx}
                      onMouseEnter={(e) => e.currentTarget.style.background = '#f8fafc'}
                      onMouseLeave={(e) => e.currentTarget.style.background = ''}>
                      {columns.map((c) => {
                        const val = c.key === '_no' ? (page - 1) * 50 + idx + 1 : row[c.key];
                        const style = { ...td, textAlign: c.align || 'left' };
                        if (c.type === 'status') return <td key={c.key} style={style}><StatusBadge status={val} /></td>;
                        if (c.type === 'number') return <td key={c.key} style={style}>{Number(val || 0).toLocaleString(undefined, { maximumFractionDigits: c.decimals ?? 1 })}</td>;
                        return <td key={c.key} style={style}>{val || '-'}</td>;
                      })}
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
          <div style={{ marginTop: 6, fontSize: 10, color: '#94a3b8', textAlign: 'right' }}>Generated: {data.generated_at}</div>
        </>
      )}
    </div>
  );
}
