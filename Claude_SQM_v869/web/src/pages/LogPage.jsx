import { useState, useEffect, useCallback } from 'react';

const BASE = '/api';

const thStyle = {
  padding: '7px 10px', textAlign: 'left', background: '#1e293b',
  borderBottom: '2px solid #334155', fontSize: 11, fontWeight: 700,
  color: '#64748b', whiteSpace: 'nowrap', position: 'sticky', top: 0,
};
const tdStyle = { padding: '5px 10px', borderBottom: '1px solid #1e293b', fontSize: 12, color: '#e2e8f0', whiteSpace: 'nowrap' };
const tdC = { ...tdStyle, textAlign: 'center' };

const TABS = [
  { key: 'audit',    label: '📋 감사 로그',     endpoint: '/tabs/audit-log',       cols: ['id','event_type','event_data','created_at'] },
  { key: 'movement', label: '📦 재고 이동',      endpoint: '/tabs/stock-movement',  cols: ['id','lot_no','movement_type','description','qty_kg','created_at'] },
  { key: 'operation',label: '🔧 운영 로그',      endpoint: '/tabs/audit-log',       cols: ['id','event_type','event_data','created_at'] },
];

const COL_LABELS = {
  id:            'ID',
  event_type:    'EVENT TYPE',
  event_data:    'DATA',
  created_at:    'DATE',
  lot_no:        'LOT NO',
  movement_type: 'TYPE',
  description:   'DESCRIPTION',
  qty_kg:        'QTY(Kg)',
};

const EVENT_COLORS = {
  INBOUND:        { bg: '#064e3b', fg: '#34d399' },
  OUTBOUND:       { bg: '#2d1f6e', fg: '#c4b5fd' },
  RETURN:         { bg: '#450a0a', fg: '#f87171' },
  RESERVED:       { bg: '#3b2a00', fg: '#fbbf24' },
  MOVE:           { bg: '#0c2a3e', fg: '#7dd3fc' },
  APPROVED:       { bg: '#064e3b', fg: '#34d399' },
  REJECTED:       { bg: '#450a0a', fg: '#f87171' },
};

function EventBadge({ type }) {
  const key = Object.keys(EVENT_COLORS).find(k => (type || '').includes(k));
  const c = key ? EVENT_COLORS[key] : { bg: '#1e293b', fg: '#94a3b8' };
  return (
    <span style={{ display: 'inline-block', padding: '1px 7px', borderRadius: 999, fontSize: 10, fontWeight: 700, background: c.bg, color: c.fg, whiteSpace: 'nowrap' }}>
      {type || '-'}
    </span>
  );
}

function LogTab({ tabKey, endpoint, cols }) {
  const [rows,    setRows]    = useState([]);
  const [total,   setTotal]   = useState(0);
  const [page,    setPage]    = useState(1);
  const [keyword, setKeyword] = useState('');
  const [loading, setLoading] = useState(false);
  const [dateFrom,setDateFrom]= useState('');
  const [dateTo,  setDateTo]  = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const p = new URLSearchParams({ page, page_size: 100 });
      if (keyword) p.set('keyword', keyword);
      if (dateFrom) p.set('date_from', dateFrom);
      if (dateTo)   p.set('date_to',   dateTo);
      const r = await fetch(`${BASE}${endpoint}?${p}`);
      const d = await r.json();
      const rawRows = d.rows || d.items || [];
      const numbered = rawRows.map((row, i) => ({
        ...row,
        _no: (page - 1) * 100 + i + 1,
      }));
      setRows(numbered);
      setTotal(d.total || rawRows.length);
    } catch {}
    setLoading(false);
  }, [page, keyword, dateFrom, dateTo, endpoint]);

  useEffect(() => { load(); }, [load]);

  const totalPages = Math.max(1, Math.ceil(total / 100));

  return (
    <div>
      {/* 검색바 */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap', alignItems: 'center' }}>
        <input
          placeholder="키워드 검색"
          value={keyword}
          onChange={e => { setKeyword(e.target.value); setPage(1); }}
          style={{ padding: '6px 10px', fontSize: 12, background: '#0f172a', border: '1px solid #334155', borderRadius: 6, color: '#f1f5f9', width: 200 }}
        />
        <input type="date" value={dateFrom} onChange={e => { setDateFrom(e.target.value); setPage(1); }}
          style={{ padding: '6px 8px', fontSize: 12, background: '#0f172a', border: '1px solid #334155', borderRadius: 6, color: '#f1f5f9' }} />
        <span style={{ color: '#475569', fontSize: 12 }}>~</span>
        <input type="date" value={dateTo} onChange={e => { setDateTo(e.target.value); setPage(1); }}
          style={{ padding: '6px 8px', fontSize: 12, background: '#0f172a', border: '1px solid #334155', borderRadius: 6, color: '#f1f5f9' }} />
        <button onClick={load}
          style={{ padding: '6px 14px', background: '#334155', color: '#94a3b8', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 12 }}>
          🔄 새로고침
        </button>
        <span style={{ fontSize: 11, color: '#475569', marginLeft: 4 }}>Total: {total.toLocaleString()}</span>
      </div>

      {loading && <div style={{ padding: 12, color: '#64748b', fontSize: 13 }}>Loading...</div>}

      {!loading && (
        <div style={{ overflow: 'auto', maxHeight: '62vh', border: '1px solid #334155', borderRadius: 8 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={{ ...thStyle, width: 50, textAlign: 'center' }}>No.</th>
                {cols.filter(c => c !== 'id').map(c => (
                  <th key={c} style={thStyle}>{COL_LABELS[c] || c}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 ? (
                <tr><td colSpan={cols.length} style={{ ...tdC, padding: 24, color: '#475569' }}>데이터 없음</td></tr>
              ) : rows.map((row, i) => (
                <tr key={i}
                  onMouseEnter={e => e.currentTarget.style.background = '#1e293b'}
                  onMouseLeave={e => e.currentTarget.style.background = ''}>
                  <td style={{ ...tdC, color: '#475569', fontSize: 11 }}>{row._no}</td>
                  {cols.filter(c => c !== 'id').map(c => (
                    <td key={c} style={{
                      ...tdStyle,
                      maxWidth: c === 'event_data' || c === 'description' ? 320 : undefined,
                      overflow: 'hidden', textOverflow: 'ellipsis',
                    }}>
                      {c === 'event_type' || c === 'movement_type'
                        ? <EventBadge type={row[c]} />
                        : c === 'created_at'
                          ? <span style={{ fontSize: 11, color: '#64748b' }}>{(row[c] || '').slice(0, 16)}</span>
                          : c === 'lot_no'
                            ? <span style={{ color: '#38bdf8', fontWeight: 600 }}>{row[c] || '-'}</span>
                            : c === 'qty_kg'
                              ? <span style={{ textAlign: 'right', display: 'block' }}>{row[c] ? Number(row[c]).toLocaleString() : '-'}</span>
                              : (row[c] !== undefined && row[c] !== null ? String(row[c]) : '-')
                      }
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 페이지네이션 */}
      <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginTop: 8, fontSize: 12 }}>
        <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}
          style={{ padding: '4px 10px', cursor: page > 1 ? 'pointer' : 'not-allowed' }}>Prev</button>
        <span style={{ color: '#94a3b8' }}>{page} / {totalPages}</span>
        <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}
          style={{ padding: '4px 10px', cursor: page < totalPages ? 'pointer' : 'not-allowed' }}>Next</button>
      </div>
    </div>
  );
}

export default function LogPage() {
  const [tab, setTab] = useState('audit');
  const current = TABS.find(t => t.key === tab);

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
        <h2 style={{ color: '#f1f5f9', margin: 0 }}>📝 로그</h2>
        <button
          onClick={() => { window.location.href = '/api/tools/export-logs?format=csv'; }}
          style={{ padding: '5px 12px', fontSize: 12, background: '#7c3aed', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer' }}
        >💾 로그 내보내기 (CSV)</button>
      </div>
      <p style={{ fontSize: 12, color: '#64748b', marginBottom: 16 }}>
        운영 로그, 감사 이력, 재고 변동 내역을 조회합니다.
      </p>

      {/* 탭 */}
      <div style={{ display: 'flex', borderBottom: '2px solid #334155', marginBottom: 16 }}>
        {TABS.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)} style={{
            padding: '8px 20px', fontSize: 13,
            fontWeight: tab === t.key ? 700 : 400,
            color: tab === t.key ? '#38bdf8' : '#64748b',
            borderBottom: tab === t.key ? '2px solid #38bdf8' : '2px solid transparent',
            background: 'none', border: 'none', cursor: 'pointer', marginBottom: -2,
          }}>{t.label}</button>
        ))}
      </div>

      {current && <LogTab key={tab} tabKey={tab} endpoint={current.endpoint} cols={current.cols} />}
    </div>
  );
}
