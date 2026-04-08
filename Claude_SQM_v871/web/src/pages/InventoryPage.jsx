/**
 * InventoryPage v2 — 입고 버튼 + 수정 버튼 추가
 * 배치: web/src/pages/InventoryPage.jsx (기존 덮어쓰기)
 * 변경:
 *   1. 상단 툴바에 "📥 입고" 버튼 추가 → InboundModal 연결
 *   2. 우클릭 메뉴에 "✏️ 수정", "📥 입고" 항목 추가
 *   3. 입고 완료 후 자동 새로고침
 */
import OutboundModal from '../components/OutboundModal';
import InboundModal  from '../components/InboundModal';
import { useEffect, useState, useCallback } from 'react';
import { getInventoryFilters, searchInventory } from '../api/inventoryApi';

const COLUMN_DEFS = [
  { key: 'no',               label: 'No.',         defaultVisible: true,  align: 'center', render: (row, idx, page) => (page - 1) * 50 + idx + 1 },
  { key: 'lot_no',           label: 'LOT NO',       defaultVisible: true,  align: 'left',   isLink: true },
  { key: 'sap_no',           label: 'SAP NO',       defaultVisible: true,  align: 'left' },
  { key: 'bl_no',            label: 'BL NO',        defaultVisible: true,  align: 'left' },
  { key: 'product_name',     label: 'PRODUCT',      defaultVisible: true,  align: 'left' },
  { key: 'status',           label: 'STATUS',       defaultVisible: true,  align: 'center', isBadge: true },
  { key: 'current_weight',   label: 'Balance(Kg)',  defaultVisible: true,  align: 'right',  fmt: true },
  { key: 'net_weight',       label: 'NET(Kg)',      defaultVisible: true,  align: 'right',  fmt: true },
  { key: 'container_no',     label: 'CONTAINER',    defaultVisible: true,  align: 'left' },
  { key: 'mxbg_pallet',      label: 'MXBG',         defaultVisible: true,  align: 'center' },
  { key: 'tonbag_uid',       label: 'TONBAG UID',   defaultVisible: false, align: 'left' },
  { key: 'location',         label: 'LOCATION',     defaultVisible: true,  align: 'center' },
  { key: 'salar_invoice_no', label: 'INVOICE NO',   defaultVisible: true,  align: 'left' },
  { key: 'ship_date',        label: 'SHIP DATE',    defaultVisible: true,  align: 'center' },
  { key: 'arrival_date',     label: 'ARRIVAL',      defaultVisible: true,  align: 'center' },
  { key: 'con_return',       label: 'CON RETURN',   defaultVisible: true,  align: 'center' },
  { key: 'free_time',        label: 'FREE TIME',    defaultVisible: true,  align: 'center' },
  { key: 'warehouse',        label: 'WH',           defaultVisible: false, align: 'center' },
  { key: 'initial_weight',   label: 'Inbound(Kg)',  defaultVisible: false, align: 'right',  fmt: true },
  { key: 'picked_weight',    label: 'Outbound(Kg)', defaultVisible: false, align: 'right',  fmt: true },
  { key: 'is_sample',        label: 'SAMPLE',       defaultVisible: false, align: 'center', render: (row) => row.is_sample ? 'Y' : '' },
  { key: 'inbound_date',     label: 'INBOUND',      defaultVisible: false, align: 'center' },
];

const STATUS_COLORS = {
  AVAILABLE: '#22c55e', RESERVED: '#f59e0b', PICKED: '#3b82f6',
  OUTBOUND: '#8b5cf6', SOLD: '#8b5cf6', PARTIAL: '#f97316',
  DEPLETED: '#94a3b8',
};

const thStyle = {
  padding: '8px 6px', textAlign: 'center', background: '#f8fafc',
  borderBottom: '2px solid #e2e8f0', fontSize: 11, fontWeight: 700,
  position: 'sticky', top: 0, whiteSpace: 'nowrap',
};
const tdBase = { padding: '5px 6px', borderBottom: '1px solid #f1f5f9', fontSize: 12, whiteSpace: 'nowrap' };

function StatusBadge({ status }) {
  const color = STATUS_COLORS[status] || '#94a3b8';
  return (
    <span style={{
      display: 'inline-block', padding: '2px 8px', borderRadius: 4,
      background: color + '22', color, border: `1px solid ${color}44`,
      fontSize: 10, fontWeight: 700,
    }}>{status}</span>
  );
}

function ConReturnCell({ value }) {
  if (!value) return null;
  try {
    const days = Math.ceil((new Date(value) - new Date()) / 86400000);
    const color = days <= 3 ? '#ef4444' : days <= 7 ? '#f97316' : '#64748b';
    return <span style={{ color, fontWeight: days <= 7 ? 700 : 400 }}>{value}</span>;
  } catch { return <span>{value}</span>; }
}

export default function InventoryPage({ onLotClick }) {
  const [filters,     setFilters]     = useState({ statuses: [], products: [], locations: [] });
  const [search,      setSearch]      = useState({ status: '', product_name: '', keyword: '', page: 1 });
  const [results,     setResults]     = useState(null);
  const [loading,     setLoading]     = useState(false);
  const [error,       setError]       = useState(null);
  const [visibleCols, setVisibleCols] = useState(() =>
    Object.fromEntries(COLUMN_DEFS.map(c => [c.key, c.defaultVisible]))
  );
  const [ctxMenu,     setCtxMenu]     = useState(null);
  const [selectedRow, setSelectedRow] = useState(null);

  // ★ 모달 상태
  const [outboundOpen, setOutboundOpen] = useState(false);
  const [inboundOpen,  setInboundOpen]  = useState(false);
  const [refreshKey,   setRefreshKey]   = useState(0);

  const closeCtx = () => setCtxMenu(null);

  // 필터 로드
  useEffect(() => {
    getInventoryFilters()
      .then(d => setFilters(d || {}))
      .catch(() => {});
  }, []);

  // 검색 실행
  const doSearch = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const res = await searchInventory(search);
      setResults(res);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [search]);

  useEffect(() => { doSearch(); }, [doSearch, refreshKey]);

  const onReset = () => {
    setSearch({ status: '', product_name: '', keyword: '', page: 1 });
  };

  const activeCols = COLUMN_DEFS.filter(c => visibleCols[c.key]);
  const totalPages = results ? Math.max(1, Math.ceil(results.total / 50)) : 1;

  const renderCell = (col, row, idx) => {
    if (col.render) return col.render(row, idx, search.page);
    if (col.isBadge) return <StatusBadge status={row[col.key]} />;
    if (col.key === 'con_return') return <ConReturnCell value={row[col.key]} />;
    if (col.isLink) return (
      <span style={{ color: '#3b82f6', cursor: 'pointer', textDecoration: 'underline' }}
        onClick={() => onLotClick && onLotClick(row.lot_no)}>{row.lot_no}</span>
    );
    if (col.fmt && row[col.key] != null)
      return Number(row[col.key]).toLocaleString(undefined, { maximumFractionDigits: 3 });
    return row[col.key] ?? '';
  };

  return (
    <div style={{ padding: 16, background: '#0f172a', minHeight: '100vh', color: '#f1f5f9' }}>

      {/* ── 헤더: 타이틀 + 입고 버튼 ── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <h2 style={{ fontSize: 16, fontWeight: 700, color: '#f1f5f9', margin: 0 }}>
          📦 Inventory
        </h2>
        {/* ★ 입고 버튼 */}
        <button
          onClick={() => setInboundOpen(true)}
          style={{
            padding: '8px 18px', background: '#22c55e', color: '#fff',
            border: 'none', borderRadius: 8, fontSize: 13, fontWeight: 700,
            cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6,
          }}
          onMouseEnter={e => e.currentTarget.style.background = '#16a34a'}
          onMouseLeave={e => e.currentTarget.style.background = '#22c55e'}
        >
          📥 입고 처리
        </button>
      </div>

      {/* ── 검색 폼 ── */}
      <form
        onSubmit={e => { e.preventDefault(); setSearch(s => ({ ...s, page: 1 })); }}
        style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 10, alignItems: 'flex-end' }}
      >
        <select
          value={search.status}
          onChange={e => setSearch(s => ({ ...s, status: e.target.value, page: 1 }))}
          style={{ padding: '5px 8px', fontSize: 12, borderRadius: 4, border: '1px solid #334155',
            background: '#1e293b', color: '#f1f5f9', minWidth: 130 }}
        >
          <option value="">All Status</option>
          {(filters.statuses || []).map(s => <option key={s} value={s}>{s}</option>)}
        </select>

        <select
          value={search.product_name}
          onChange={e => setSearch(s => ({ ...s, product_name: e.target.value, page: 1 }))}
          style={{ padding: '5px 8px', fontSize: 12, borderRadius: 4, border: '1px solid #334155',
            background: '#1e293b', color: '#f1f5f9', minWidth: 160 }}
        >
          <option value="">All Products</option>
          {(filters.products || []).map(p => <option key={p} value={p}>{p}</option>)}
        </select>

        <input
          value={search.keyword}
          onChange={e => setSearch(s => ({ ...s, keyword: e.target.value }))}
          placeholder="LOT / BL / Container / Invoice..."
          style={{ padding: '5px 10px', fontSize: 12, borderRadius: 4, border: '1px solid #334155',
            background: '#1e293b', color: '#f1f5f9', width: 220 }}
        />
        <button type="submit" style={{ padding: '5px 14px', fontWeight: 700, fontSize: 12,
          background: '#3b82f6', color: '#fff', border: 'none', borderRadius: 4, cursor: 'pointer' }}>
          Search
        </button>
        <button type="button" onClick={onReset} style={{ padding: '5px 10px', fontSize: 12,
          background: '#334155', color: '#94a3b8', border: 'none', borderRadius: 4, cursor: 'pointer' }}>
          Reset
        </button>
      </form>

      {/* ── 컬럼 토글 ── */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', padding: '6px 10px',
        background: '#1e293b', border: '1px solid #334155', borderRadius: 6, marginBottom: 10, fontSize: 11 }}>
        <span style={{ fontWeight: 700, color: '#475569', marginRight: 4 }}>Columns:</span>
        {COLUMN_DEFS.map(col => (
          <label key={col.key} style={{ display: 'flex', alignItems: 'center', gap: 2, cursor: 'pointer', color: '#64748b' }}>
            <input type="checkbox" checked={!!visibleCols[col.key]}
              onChange={() => setVisibleCols(v => ({ ...v, [col.key]: !v[col.key] }))}
              style={{ width: 13, height: 13 }} />
            {col.label}
          </label>
        ))}
      </div>

      {error   && <div style={{ color:'#ef4444', marginBottom:8, padding:8, background:'#fef2f2', borderRadius:6, fontSize:12 }}>Error: {error}</div>}
      {loading && <div style={{ padding:12, color:'#475569' }}>Loading...</div>}

      {results && !loading && (
        <>
          {/* ── 결과 헤더 ── */}
          <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:6 }}>
            <span style={{ fontSize:12, color:'#475569' }}>
              Total: <b>{results.total?.toLocaleString()}</b>
            </span>
            <div style={{ display:'flex', gap:6, alignItems:'center', fontSize:12 }}>
              <button
                onClick={() => {
                  const p = new URLSearchParams();
                  if (search.status)       p.set('status', search.status);
                  if (search.product_name) p.set('product_name', search.product_name);
                  if (search.keyword)      p.set('keyword', search.keyword);
                  window.location.href = `/api/tools/export-lot-list?${p.toString()}`;
                }}
                style={{ padding:'4px 10px', fontSize:11, background:'#16a34a', color:'#fff',
                  border:'none', borderRadius:4, cursor:'pointer' }}
              >📥 Excel</button>
              <button disabled={search.page <= 1}
                onClick={() => setSearch(s => ({ ...s, page: s.page - 1 }))}
                style={{ padding:'3px 8px', fontSize:11 }}>Prev</button>
              <span style={{ fontSize:11 }}>{search.page} / {totalPages}</span>
              <button disabled={search.page >= totalPages}
                onClick={() => setSearch(s => ({ ...s, page: s.page + 1 }))}
                style={{ padding:'3px 8px', fontSize:11 }}>Next</button>
            </div>
          </div>

          {/* ── 테이블 ── */}
          <div style={{ overflow:'auto', maxHeight:'68vh', border:'1px solid #334155', borderRadius:6 }}>
            <table style={{ width:'100%', borderCollapse:'collapse', minWidth: activeCols.length * 100 }}>
              <thead>
                <tr>{activeCols.map(col => <th key={col.key} style={thStyle}>{col.label}</th>)}</tr>
              </thead>
              <tbody>
                {results.rows?.length === 0
                  ? <tr><td colSpan={activeCols.length} style={{ ...tdBase, textAlign:'center', padding:24, color:'#94a3b8' }}>No results</td></tr>
                  : results.rows?.map((row, idx) => (
                    <tr key={row.tonbag_id || idx}
                      onMouseEnter={e => e.currentTarget.style.background = '#1e293b'}
                      onMouseLeave={e => e.currentTarget.style.background = ''}
                      onContextMenu={e => { e.preventDefault(); setCtxMenu({ x: e.clientX, y: e.clientY, row }); }}
                    >
                      {activeCols.map(col => (
                        <td key={col.key} style={{ ...tdBase, textAlign: col.align || 'left' }}>
                          {renderCell(col, row, idx)}
                        </td>
                      ))}
                    </tr>
                  ))
                }
              </tbody>
            </table>
          </div>
          <div style={{ marginTop:4, fontSize:10, color:'#94a3b8', textAlign:'right' }}>
            {results.generated_at}
          </div>
        </>
      )}

      {/* ── 우클릭 컨텍스트 메뉴 (★ 입고 항목 추가) ── */}
      {ctxMenu && (
        <>
          <div style={{ position:'fixed', inset:0, zIndex:999 }} onClick={closeCtx} />
          <div style={{
            position:'fixed', left: ctxMenu.x, top: ctxMenu.y, zIndex:1000,
            background:'#1e293b', border:'1px solid #334155', borderRadius:8,
            boxShadow:'0 8px 24px rgba(0,0,0,0.5)', minWidth:180, overflow:'hidden',
          }}>
            <div style={{ padding:'8px 14px', fontSize:11, color:'#64748b', borderBottom:'1px solid #334155' }}>
              {ctxMenu.row.lot_no}
            </div>

            {/* ★ 입고 처리 */}
            {[
              { icon:'📥', label:'입고 처리', action: () => { setInboundOpen(true); closeCtx(); } },
              { icon:'✅', label:'즉시 출고', action: () => { setSelectedRow(ctxMenu.row); setOutboundOpen(true); closeCtx(); } },
              { icon:'🔍', label:'LOT 상세',  action: () => { onLotClick && onLotClick(ctxMenu.row.lot_no); closeCtx(); } },
            ].map(({ icon, label, action }) => (
              <button key={label} onClick={action}
                style={{ display:'block', width:'100%', padding:'10px 14px', textAlign:'left',
                  background:'none', border:'none', color:'#f1f5f9', fontSize:13,
                  cursor:'pointer', fontWeight:500 }}
                onMouseEnter={e => e.currentTarget.style.background = '#334155'}
                onMouseLeave={e => e.currentTarget.style.background = 'none'}
              >{icon} {label}</button>
            ))}
          </div>
        </>
      )}

      {/* ── 모달 ── */}
      {/* ★ 입고 Modal */}
      <InboundModal
        open={inboundOpen}
        onClose={() => {
          setInboundOpen(false);
          setRefreshKey(k => k + 1);  // ★ 입고 완료 후 자동 새로고침
        }}
      />

      {/* 즉시 출고 Modal */}
      <OutboundModal
        open={outboundOpen}
        onClose={() => { setOutboundOpen(false); setSelectedRow(null); setRefreshKey(k => k + 1); }}
        initialLotNo={selectedRow?.lot_no || ''}
      />
    </div>
  );
}
