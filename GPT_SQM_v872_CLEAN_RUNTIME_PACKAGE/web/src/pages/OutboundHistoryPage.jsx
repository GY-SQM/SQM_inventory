/**
 * OutboundHistoryPage v2 — 날짜 필터 + 고객별 집계 강화
 * 배치: web/src/pages/OutboundHistoryPage.jsx
 */
import { useState, useEffect, useCallback } from 'react';
import { api } from '../api/client';

const th = { padding:'8px 8px', background:'#1e293b', borderBottom:'1px solid #334155',
  fontSize:11, fontWeight:700, textAlign:'center', position:'sticky', top:0, color:'#94a3b8' };
const td = { padding:'6px 8px', borderBottom:'1px solid #1e293b', fontSize:12, whiteSpace:'nowrap' };

export default function OutboundHistoryPage() {
  const [rows,     setRows]     = useState([]);
  const [loading,  setLoading]  = useState(true);
  const [error,    setError]    = useState(null);
  const [dateFrom, setDateFrom] = useState(() => {
    const d = new Date(); d.setMonth(d.getMonth()-1); return d.toISOString().slice(0,10);
  });
  const [dateTo,   setDateTo]   = useState(new Date().toISOString().slice(0,10));
  const [customer, setCustomer] = useState('');

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const qs = new URLSearchParams();
      if (dateFrom) qs.set('date_from', dateFrom);
      if (dateTo)   qs.set('date_to',   dateTo);
      if (customer) qs.set('customer',  customer);
      const res = await api.get(`/advanced/outbound-history?${qs}`);
      setRows(res?.rows || res?.items || []);
    } catch(e) { setError(e.message); }
    finally { setLoading(false); }
  }, [dateFrom, dateTo, customer]);

  useEffect(() => { load(); }, [load]);

  const totalMt = rows.reduce((s,r) => s+Number(r.total_qty_mt||0), 0);
  const customers = [...new Set(rows.map(r => r.customer).filter(Boolean))];

  return (
    <div style={{ padding:16, background:'#0f172a', minHeight:'100vh', color:'#f1f5f9' }}>
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:12 }}>
        <h2 style={{ fontSize:16, fontWeight:700, margin:0 }}>
          📋 Outbound History
          <span style={{ fontSize:12, color:'#64748b', marginLeft:8, fontWeight:400 }}>
            {rows.length}건 / {totalMt.toFixed(3)} MT
          </span>
        </h2>
        <button onClick={() => window.location.href=`/api/tools/export-lot-list?status=OUTBOUND&date_from=${dateFrom}&date_to=${dateTo}`}
          style={{ padding:'7px 14px', background:'#16a34a', color:'#fff', border:'none',
            borderRadius:8, fontSize:12, fontWeight:700, cursor:'pointer' }}>📥 Excel</button>
      </div>

      {/* 필터 */}
      <div style={{ display:'flex', gap:8, marginBottom:12, flexWrap:'wrap', alignItems:'center' }}>
        <input type="date" value={dateFrom} onChange={e=>setDateFrom(e.target.value)}
          style={{ padding:'5px 8px', fontSize:12, borderRadius:6, border:'1px solid #334155', background:'#1e293b', color:'#f1f5f9' }} />
        <span style={{ color:'#64748b' }}>~</span>
        <input type="date" value={dateTo} onChange={e=>setDateTo(e.target.value)}
          style={{ padding:'5px 8px', fontSize:12, borderRadius:6, border:'1px solid #334155', background:'#1e293b', color:'#f1f5f9' }} />
        <select value={customer} onChange={e=>setCustomer(e.target.value)}
          style={{ padding:'5px 8px', fontSize:12, borderRadius:6, border:'1px solid #334155', background:'#1e293b', color:'#f1f5f9' }}>
          <option value="">전체 고객</option>
          {customers.map(c => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>

      {error   && <div style={{ color:'#ef4444', fontSize:12, marginBottom:8 }}>❌ {error}</div>}
      {loading && <div style={{ color:'#64748b', padding:16 }}>Loading...</div>}

      {!loading && (
        <div style={{ overflow:'auto', maxHeight:'75vh', border:'1px solid #334155', borderRadius:8 }}>
          <table style={{ width:'100%', borderCollapse:'collapse' }}>
            <thead>
              <tr>{['No.','OUTBOUND NO','SALE REF','CUSTOMER','QTY(MT)','DATE','STATUS'].map(h=>(
                <th key={h} style={th}>{h}</th>
              ))}</tr>
            </thead>
            <tbody>
              {rows.length===0
                ? <tr><td colSpan={7} style={{...td,textAlign:'center',padding:32,color:'#94a3b8'}}>출고 이력 없음</td></tr>
                : rows.map((row,i) => (
                  <tr key={i}
                    onMouseEnter={e=>e.currentTarget.style.background='#1e293b'}
                    onMouseLeave={e=>e.currentTarget.style.background=''}>
                    <td style={{...td,textAlign:'center',color:'#64748b'}}>{i+1}</td>
                    <td style={{...td,color:'#8b5cf6',fontWeight:600}}>{row.outbound_no||'-'}</td>
                    <td style={td}>{row.sale_ref||'-'}</td>
                    <td style={td}>{row.customer||'-'}</td>
                    <td style={{...td,textAlign:'right',fontWeight:600}}>{Number(row.total_qty_mt||0).toFixed(3)}</td>
                    <td style={{...td,textAlign:'center',fontSize:11}}>{row.outbound_date||'-'}</td>
                    <td style={{...td,textAlign:'center'}}>
                      <span style={{ background:'#8b5cf622', color:'#8b5cf6',
                        border:'1px solid #8b5cf644', borderRadius:4, padding:'2px 8px', fontSize:10 }}>
                        {row.status||'OUTBOUND'}
                      </span>
                    </td>
                  </tr>
                ))
              }
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
