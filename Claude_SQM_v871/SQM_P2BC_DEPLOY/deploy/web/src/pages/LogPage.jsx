/**
 * LogPage v2 — 다크테마 + 레벨 필터 + 날짜 필터
 * 배치: web/src/pages/LogPage.jsx
 */
import { useState, useEffect, useCallback } from 'react';
import { fetchJson } from '../api/client';

const LEVEL_COLOR = { ERROR:'#ef4444', WARNING:'#f59e0b', INFO:'#3b82f6', DEBUG:'#94a3b8' };
const th = { padding:'7px 8px', background:'#0f172a', borderBottom:'1px solid #334155', fontSize:11, fontWeight:700, color:'#64748b', textAlign:'center', position:'sticky', top:0 };
const td = { padding:'5px 8px', borderBottom:'1px solid #1e293b', fontSize:11, whiteSpace:'nowrap' };

export default function LogPage() {
  const [rows,    setRows]    = useState([]);
  const [loading, setLoading] = useState(true);
  const [level,   setLevel]   = useState('');
  const [keyword, setKeyword] = useState('');
  const [page,    setPage]    = useState(1);
  const PAGE_SIZE = 100;

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const qs = new URLSearchParams();
      if (level)   qs.set('level', level);
      if (keyword) qs.set('keyword', keyword);
      qs.set('page', page); qs.set('page_size', PAGE_SIZE);
      const res = await fetchJson(`/tabs/audit-log?${qs}`);
      setRows(res?.rows || res?.items || []);
    } catch(e) { console.error(e); }
    finally { setLoading(false); }
  }, [level, keyword, page]);

  useEffect(() => { load(); }, [load]);

  return (
    <div style={{ padding:16, background:'#0f172a', minHeight:'100vh', color:'#f1f5f9' }}>
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:12 }}>
        <h2 style={{ fontSize:16, fontWeight:700, margin:0 }}>📋 이벤트 로그</h2>
        <button onClick={() => window.location.href='/api/tools/export-logs'}
          style={{ padding:'7px 14px', background:'#16a34a', color:'#fff', border:'none',
            borderRadius:8, fontSize:12, fontWeight:700, cursor:'pointer' }}>📥 Excel</button>
      </div>

      <div style={{ display:'flex', gap:8, marginBottom:10, flexWrap:'wrap' }}>
        {['','ERROR','WARNING','INFO','DEBUG'].map(l => (
          <button key={l} onClick={() => { setLevel(l); setPage(1); }} style={{
            padding:'4px 12px', borderRadius:20, border:'none',
            background: level===l ? (LEVEL_COLOR[l]||'#3b82f6') : '#1e293b',
            color: level===l ? '#fff' : '#64748b', fontSize:11, cursor:'pointer',
          }}>{l||'전체'}</button>
        ))}
        <input value={keyword} onChange={e => setKeyword(e.target.value)} placeholder="검색..."
          style={{ padding:'4px 10px', fontSize:11, borderRadius:6, border:'1px solid #334155',
            background:'#1e293b', color:'#f1f5f9', width:180 }} />
      </div>

      {loading && <div style={{ color:'#64748b', padding:16 }}>Loading...</div>}
      {!loading && (
        <>
          <div style={{ overflow:'auto', maxHeight:'76vh', border:'1px solid #334155', borderRadius:8 }}>
            <table style={{ width:'100%', borderCollapse:'collapse' }}>
              <thead>
                <tr>{['시각','레벨','이벤트','LOT NO','상세','작업자'].map(h=>(
                  <th key={h} style={th}>{h}</th>
                ))}</tr>
              </thead>
              <tbody>
                {rows.length===0
                  ? <tr><td colSpan={6} style={{...td,textAlign:'center',padding:32,color:'#94a3b8'}}>로그 없음</td></tr>
                  : rows.map((r,i) => {
                    const lc = LEVEL_COLOR[r.level||r.event_type]||'#94a3b8';
                    return (
                      <tr key={i}
                        onMouseEnter={e=>e.currentTarget.style.background='#1e293b'}
                        onMouseLeave={e=>e.currentTarget.style.background=''}>
                        <td style={{...td,fontSize:10,color:'#64748b'}}>{r.created_at||'-'}</td>
                        <td style={{...td,textAlign:'center'}}>
                          <span style={{ background:lc+'22', color:lc, border:`1px solid ${lc}44`,
                            borderRadius:4, padding:'1px 6px', fontSize:9, fontWeight:700 }}>
                            {r.level||r.event_type||'INFO'}
                          </span>
                        </td>
                        <td style={{...td,fontWeight:600,color:'#f1f5f9'}}>{r.action||r.event||'-'}</td>
                        <td style={{...td,color:'#3b82f6'}}>{r.lot_no||'-'}</td>
                        <td style={{...td,maxWidth:300,overflow:'hidden',textOverflow:'ellipsis',color:'#94a3b8'}}>
                          {r.message||r.detail||r.description||'-'}
                        </td>
                        <td style={{...td,fontSize:10,color:'#64748b'}}>{r.operator||r.user_id||'-'}</td>
                      </tr>
                    );
                  })
                }
              </tbody>
            </table>
          </div>
          <div style={{ display:'flex', gap:8, justifyContent:'flex-end', marginTop:8 }}>
            <button disabled={page<=1} onClick={() => setPage(p=>p-1)}
              style={{ padding:'4px 10px', fontSize:11, borderRadius:5, border:'none',
                background:'#334155', color:'#94a3b8', cursor:'pointer' }}>Prev</button>
            <span style={{ fontSize:11, color:'#64748b', alignSelf:'center' }}>Page {page}</span>
            <button disabled={rows.length<PAGE_SIZE} onClick={() => setPage(p=>p+1)}
              style={{ padding:'4px 10px', fontSize:11, borderRadius:5, border:'none',
                background:'#334155', color:'#94a3b8', cursor:'pointer' }}>Next</button>
          </div>
        </>
      )}
    </div>
  );
}
