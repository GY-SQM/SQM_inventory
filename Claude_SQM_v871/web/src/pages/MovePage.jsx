/**
 * MovePage v2 — 이동 실행 버튼 + 이력 조회 완성
 * 배치: web/src/pages/MovePage.jsx
 */
import { useState, useEffect, useCallback } from 'react';
import { api, fetchJson } from '../api/client';

function Toast({ msg, ok, onClose }) {
  useEffect(() => { const t = setTimeout(onClose, 3000); return () => clearTimeout(t); }, [onClose]);
  return (
    <div style={{ position:'fixed', bottom:24, left:'50%', transform:'translateX(-50%)',
      background:ok?'#16a34a':'#dc2626', color:'#fff', padding:'12px 24px',
      borderRadius:10, fontWeight:700, fontSize:14, zIndex:9999 }}>
      {ok?'✅':'❌'} {msg}
    </div>
  );
}

const th = { padding:'7px 8px', background:'#0f172a', borderBottom:'1px solid #334155',
  fontSize:11, fontWeight:700, color:'#64748b', textAlign:'center', position:'sticky', top:0 };
const td = { padding:'5px 8px', borderBottom:'1px solid #1e293b', fontSize:12 };

const MOVE_TYPES = ['RELOCATE','STAGING','RETURN','ADJUSTMENT'];

export default function MovePage() {
  const [rows,       setRows]       = useState([]);
  const [loading,    setLoading]    = useState(true);
  const [tab,        setTab]        = useState('history'); // history | move
  const [toast,      setToast]      = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);

  // ── 이동 실행 폼 ─────────────────────────────────────────
  const [form, setForm] = useState({
    lot_no:'', sub_lt:'', new_location:'',
    reason_code:'RELOCATE', note:''
  });
  const [moving, setMoving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetchJson('/tabs/move-log?page_size=100');
      setRows(res?.rows || res?.items || []);
    } catch(e) { console.error(e); }
    finally { setLoading(false); }
  }, [refreshKey]);

  useEffect(() => { load(); }, [load]);

  const handleMove = async () => {
    if (!form.lot_no || !form.new_location) {
      setToast({ msg:'LOT NO와 이동 위치를 입력하세요', ok:false }); return;
    }
    setMoving(true);
    try {
      const res = await api.put('/location/update', {
        lot_no:       form.lot_no,
        sub_lt:       Number(form.sub_lt)||0,
        new_location: form.new_location,
        operator:     'web_user',
        reason_code:  form.reason_code,
        note:         form.note,
      });
      if (res?.success) {
        setToast({ msg:`${form.lot_no} → ${form.new_location} 이동 완료`, ok:true });
        setForm(f => ({...f, lot_no:'', sub_lt:'', new_location:'', note:''}));
        setRefreshKey(k=>k+1);
        setTab('history');
      } else {
        setToast({ msg:res?.message||'이동 실패', ok:false });
      }
    } catch(e) { setToast({ msg:e.message, ok:false }); }
    finally { setMoving(false); }
  };

  const inputS = { padding:'7px 10px', fontSize:13, borderRadius:6, border:'1px solid #334155',
    background:'#0f172a', color:'#f1f5f9' };

  return (
    <div style={{ padding:16, background:'#0f172a', minHeight:'100vh', color:'#f1f5f9' }}>
      {/* 헤더 */}
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:12 }}>
        <h2 style={{ fontSize:16, fontWeight:700, margin:0 }}>📦 위치 이동</h2>
      </div>

      {/* 탭 */}
      <div style={{ display:'flex', gap:8, marginBottom:16 }}>
        {[{id:'history',label:'📋 이동 이력'},{id:'move',label:'📍 이동 실행'}].map(t=>(
          <button key={t.id} onClick={() => setTab(t.id)} style={{
            padding:'8px 18px', borderRadius:8, border:'none', fontSize:13,
            background:tab===t.id?'#3b82f6':'#1e293b',
            color:tab===t.id?'#fff':'#64748b',
            fontWeight:tab===t.id?700:400, cursor:'pointer',
          }}>{t.label}</button>
        ))}
      </div>

      {/* 이동 실행 탭 */}
      {tab === 'move' && (
        <div style={{ background:'#1e293b', border:'1px solid #334155', borderRadius:10, padding:20, maxWidth:480 }}>
          <h3 style={{ fontSize:14, fontWeight:700, color:'#94a3b8', marginBottom:16 }}>위치 이동 실행</h3>
          <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:12, marginBottom:12 }}>
            <div>
              <div style={{ fontSize:11, color:'#64748b', marginBottom:4 }}>LOT NO *</div>
              <input value={form.lot_no} onChange={e=>setForm(f=>({...f,lot_no:e.target.value}))}
                placeholder="LOT-2026-001" style={{...inputS, width:'100%'}} />
            </div>
            <div>
              <div style={{ fontSize:11, color:'#64748b', marginBottom:4 }}>SUB_LT (전체:0)</div>
              <input value={form.sub_lt} onChange={e=>setForm(f=>({...f,sub_lt:e.target.value}))}
                type="number" placeholder="0" style={{...inputS, width:'100%'}} />
            </div>
            <div>
              <div style={{ fontSize:11, color:'#64748b', marginBottom:4 }}>이동 위치 *</div>
              <input value={form.new_location} onChange={e=>setForm(f=>({...f,new_location:e.target.value}))}
                placeholder="A-01-01" style={{...inputS, width:'100%'}} />
            </div>
            <div>
              <div style={{ fontSize:11, color:'#64748b', marginBottom:4 }}>이동 사유</div>
              <select value={form.reason_code} onChange={e=>setForm(f=>({...f,reason_code:e.target.value}))}
                style={{...inputS, width:'100%'}}>
                {MOVE_TYPES.map(t=><option key={t} value={t}>{t}</option>)}
              </select>
            </div>
          </div>
          <div style={{ marginBottom:14 }}>
            <div style={{ fontSize:11, color:'#64748b', marginBottom:4 }}>메모</div>
            <input value={form.note} onChange={e=>setForm(f=>({...f,note:e.target.value}))}
              placeholder="(선택) 이동 사유 메모"
              style={{...inputS, width:'100%'}} />
          </div>
          <button onClick={handleMove} disabled={moving || !form.lot_no || !form.new_location}
            style={{ padding:'10px 24px', background:'#3b82f6', color:'#fff', border:'none',
              borderRadius:8, fontSize:14, fontWeight:700,
              cursor:(!form.lot_no||!form.new_location)?'not-allowed':'pointer',
              opacity:(!form.lot_no||!form.new_location)?0.5:1 }}>
            {moving ? '⏳ 이동 중...' : '📍 이동 실행'}
          </button>
        </div>
      )}

      {/* 이동 이력 탭 */}
      {tab === 'history' && (
        <>
          {loading && <div style={{ color:'#64748b', padding:16 }}>Loading...</div>}
          {!loading && (
            <div style={{ overflow:'auto', maxHeight:'75vh', border:'1px solid #334155', borderRadius:8 }}>
              <table style={{ width:'100%', borderCollapse:'collapse' }}>
                <thead>
                  <tr>{['시각','LOT NO','SUB_LT','이전 위치','→ 이후 위치','사유','작업자'].map(h=>(
                    <th key={h} style={th}>{h}</th>
                  ))}</tr>
                </thead>
                <tbody>
                  {rows.length===0
                    ? <tr><td colSpan={7} style={{...td,textAlign:'center',padding:32,color:'#94a3b8'}}>이동 이력 없음</td></tr>
                    : rows.map((r,i) => (
                      <tr key={i}
                        onMouseEnter={e=>e.currentTarget.style.background='#1e293b'}
                        onMouseLeave={e=>e.currentTarget.style.background=''}>
                        <td style={{...td,fontSize:10,color:'#64748b'}}>{String(r.created_at||'').slice(0,16)}</td>
                        <td style={{...td,fontWeight:600,color:'#3b82f6'}}>{r.lot_no}</td>
                        <td style={{...td,textAlign:'center',color:'#94a3b8'}}>{r.sub_lt??'-'}</td>
                        <td style={{...td,color:'#ef4444'}}>{r.from_location||'-'}</td>
                        <td style={{...td,color:'#22c55e',fontWeight:600}}>{r.to_location||r.location||'-'}</td>
                        <td style={{...td,fontSize:11,color:'#64748b'}}>{r.reason_code||r.move_type||'-'}</td>
                        <td style={{...td,fontSize:11,color:'#64748b'}}>{r.operator||r.user_id||'-'}</td>
                      </tr>
                    ))
                  }
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
      {toast && <Toast msg={toast.msg} ok={toast.ok} onClose={() => setToast(null)} />}
    </div>
  );
}
