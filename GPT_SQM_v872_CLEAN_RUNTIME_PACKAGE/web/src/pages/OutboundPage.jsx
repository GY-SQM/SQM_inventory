/**
 * OutboundPage v2 — 출고 실행 버튼 + 상태 탭 + 검색
 * 배치: web/src/pages/OutboundPage.jsx
 */
import { useEffect, useState, useCallback } from 'react';
import { getOutboundList } from '../api/tabsApi';
import OutboundModal from '../components/OutboundModal';

function Toast({ msg, ok, onClose }) {
  useEffect(() => { const t = setTimeout(onClose, 3000); return () => clearTimeout(t); }, [onClose]);
  return (
    <div style={{
      position:'fixed', bottom:24, left:'50%', transform:'translateX(-50%)',
      background: ok ? '#16a34a' : '#dc2626', color:'#fff',
      padding:'12px 24px', borderRadius:10, fontWeight:700, fontSize:14,
      zIndex:9999, boxShadow:'0 4px 16px rgba(0,0,0,0.4)',
    }}>{ok ? '✅' : '❌'} {msg}</div>
  );
}

const STATUS_COLOR = {
  PENDING:'#94a3b8', RESERVED:'#f59e0b', PICKED:'#3b82f6',
  OUTBOUND:'#8b5cf6', COMPLETED:'#22c55e', CANCELLED:'#ef4444',
};

const th = { padding:'8px 10px', background:'#f8fafc', borderBottom:'2px solid #e2e8f0', fontSize:11, fontWeight:700, whiteSpace:'nowrap', textAlign:'center', position:'sticky', top:0 };
const td = { padding:'6px 10px', borderBottom:'1px solid #f1f5f9', fontSize:12, whiteSpace:'nowrap' };

export default function OutboundPage() {
  const [rows,        setRows]        = useState([]);
  const [loading,     setLoading]     = useState(true);
  const [error,       setError]       = useState(null);
  const [keyword,     setKeyword]     = useState('');
  const [statusTab,   setStatusTab]   = useState('ALL');
  const [outboundOpen,setOutboundOpen]= useState(false);
  const [selectedLot, setSelectedLot] = useState('');
  const [toast,       setToast]       = useState(null);
  const [refreshKey,  setRefreshKey]  = useState(0);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const res = await getOutboundList({ keyword });
      setRows(res?.rows || res?.items || []);
    } catch(e) { setError(e.message); }
    finally { setLoading(false); }
  }, [keyword, refreshKey]);

  useEffect(() => { load(); }, [load]);

  const counts = rows.reduce((a, r) => { a[r.status] = (a[r.status]||0)+1; return a; }, {});
  const display = statusTab === 'ALL' ? rows : rows.filter(r => r.status === statusTab);

  return (
    <div style={{ padding:16, background:'#0f172a', minHeight:'100vh', color:'#f1f5f9' }}>
      {/* 헤더 */}
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:12 }}>
        <h2 style={{ fontSize:16, fontWeight:700, margin:0 }}>
          📤 Outbound Schedule
          <span style={{ fontSize:12, color:'#64748b', marginLeft:8, fontWeight:400 }}>{rows.length}건</span>
        </h2>
        <button onClick={() => setOutboundOpen(true)} style={{
          padding:'8px 18px', background:'#8b5cf6', color:'#fff',
          border:'none', borderRadius:8, fontSize:13, fontWeight:700, cursor:'pointer',
        }}>📤 출고 실행</button>
      </div>

      {/* 상태 탭 */}
      <div style={{ display:'flex', gap:6, marginBottom:10, flexWrap:'wrap' }}>
        {['ALL',...Object.keys(STATUS_COLOR)].map(s => (
          <button key={s} onClick={() => setStatusTab(s)} style={{
            padding:'5px 12px', borderRadius:20, border:'none',
            background: statusTab===s ? (STATUS_COLOR[s]||'#3b82f6') : '#1e293b',
            color: statusTab===s ? '#fff' : '#64748b',
            fontSize:12, fontWeight: statusTab===s ? 700 : 400, cursor:'pointer',
          }}>{s==='ALL'?'전체':s} {s!=='ALL' && counts[s] ? `(${counts[s]})` : ''}</button>
        ))}
      </div>

      {/* 검색 */}
      <div style={{ display:'flex', gap:8, marginBottom:10 }}>
        <input value={keyword} onChange={e => setKeyword(e.target.value)}
          placeholder="Sale Ref / Customer / Outbound NO 검색..."
          style={{ padding:'6px 10px', fontSize:12, borderRadius:6, border:'1px solid #334155',
            background:'#1e293b', color:'#f1f5f9', width:280 }} />
        {keyword && <button onClick={() => setKeyword('')} style={{ padding:'6px 12px', fontSize:12,
          borderRadius:6, border:'none', background:'#334155', color:'#94a3b8', cursor:'pointer' }}>Clear</button>}
      </div>

      {error   && <div style={{ color:'#ef4444', fontSize:12, marginBottom:8 }}>❌ {error}</div>}
      {loading && <div style={{ color:'#64748b', padding:16 }}>Loading...</div>}

      {!loading && (
        <div style={{ overflow:'auto', maxHeight:'75vh', border:'1px solid #334155', borderRadius:8 }}>
          <table style={{ width:'100%', borderCollapse:'collapse' }}>
            <thead>
              <tr>{['No.','OUTBOUND NO','SALE REF','CUSTOMER','QTY(MT)','DATE','DESTINATION','STATUS','REMARKS','ACTION'].map(h => (
                <th key={h} style={th}>{h}</th>
              ))}</tr>
            </thead>
            <tbody>
              {display.length === 0
                ? <tr><td colSpan={10} style={{...td, textAlign:'center', padding:32, color:'#94a3b8'}}>출고 내역 없음</td></tr>
                : display.map((row, i) => (
                  <tr key={row.outbound_no||i}
                    onMouseEnter={e => e.currentTarget.style.background='#1e293b'}
                    onMouseLeave={e => e.currentTarget.style.background=''}>
                    <td style={{...td, textAlign:'center', color:'#64748b'}}>{i+1}</td>
                    <td style={{...td, fontWeight:600, color:'#3b82f6'}}>{row.outbound_no||'-'}</td>
                    <td style={td}>{row.sale_ref||'-'}</td>
                    <td style={td}>{row.customer||'-'}</td>
                    <td style={{...td, textAlign:'right'}}>{Number(row.total_qty_mt||0).toFixed(3)}</td>
                    <td style={{...td, textAlign:'center', fontSize:11}}>{row.outbound_date||'-'}</td>
                    <td style={{...td, fontSize:11, color:'#94a3b8'}}>{row.destination||'-'}</td>
                    <td style={{...td, textAlign:'center'}}>
                      <span style={{ background:(STATUS_COLOR[row.status]||'#94a3b8')+'22',
                        color:STATUS_COLOR[row.status]||'#94a3b8',
                        border:`1px solid ${STATUS_COLOR[row.status]||'#94a3b8'}44`,
                        borderRadius:4, padding:'2px 8px', fontSize:10, fontWeight:700 }}>
                        {row.status||'-'}
                      </span>
                    </td>
                    <td style={{...td, fontSize:11, color:'#64748b', maxWidth:120, overflow:'hidden', textOverflow:'ellipsis'}}>
                      {row.remarks||'-'}
                    </td>
                    <td style={{...td, textAlign:'center'}}>
                      <button onClick={() => { setSelectedLot(row.sale_ref||''); setOutboundOpen(true); }}
                        style={{ padding:'4px 10px', fontSize:11, fontWeight:700,
                          background:'#8b5cf6', color:'#fff', border:'none', borderRadius:5, cursor:'pointer' }}>
                        실행
                      </button>
                    </td>
                  </tr>
                ))
              }
            </tbody>
          </table>
        </div>
      )}

      <OutboundModal open={outboundOpen}
        onClose={() => { setOutboundOpen(false); setSelectedLot(''); setRefreshKey(k=>k+1); }}
        initialLotNo={selectedLot} />
      {toast && <Toast msg={toast.msg} ok={toast.ok} onClose={() => setToast(null)} />}
    </div>
  );
}
