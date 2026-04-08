/**
 * TonbagPage v2 — 위치 수정 + 상태 필터 강화
 * 배치: web/src/pages/TonbagPage.jsx
 */
import { useEffect, useState, useCallback } from 'react';
import { getTonbagList } from '../api/tabsApi';
import { api } from '../api/client';

function Toast({ msg, ok, onClose }) {
  useEffect(() => { const t = setTimeout(onClose, 3000); return () => clearTimeout(t); }, [onClose]);
  return (
    <div style={{ position:'fixed', bottom:24, left:'50%', transform:'translateX(-50%)',
      background: ok?'#16a34a':'#dc2626', color:'#fff', padding:'12px 24px',
      borderRadius:10, fontWeight:700, fontSize:14, zIndex:9999 }}>
      {ok?'✅':'❌'} {msg}
    </div>
  );
}

// 위치 수정 인라인 입력 컴포넌트
function LocationEditor({ row, onSave, onCancel }) {
  const [val, setVal] = useState(row.location || '');
  return (
    <div style={{ display:'flex', gap:4, alignItems:'center' }}>
      <input value={val} onChange={e => setVal(e.target.value)}
        onKeyDown={e => { if(e.key==='Enter') onSave(val); if(e.key==='Escape') onCancel(); }}
        style={{ width:100, padding:'3px 6px', fontSize:11, borderRadius:4,
          border:'1px solid #3b82f6', background:'#0f172a', color:'#f1f5f9' }}
        autoFocus />
      <button onClick={() => onSave(val)} style={{ padding:'3px 8px', fontSize:10,
        background:'#3b82f6', color:'#fff', border:'none', borderRadius:4, cursor:'pointer' }}>저장</button>
      <button onClick={onCancel} style={{ padding:'3px 6px', fontSize:10,
        background:'#334155', color:'#94a3b8', border:'none', borderRadius:4, cursor:'pointer' }}>✕</button>
    </div>
  );
}

const STATUS_COLOR = {
  AVAILABLE:'#22c55e', RESERVED:'#f59e0b', PICKED:'#3b82f6',
  OUTBOUND:'#8b5cf6', SOLD:'#8b5cf6', DEPLETED:'#94a3b8',
};
const th = { padding:'8px 8px', background:'#f8fafc', borderBottom:'2px solid #e2e8f0',
  fontSize:11, fontWeight:700, whiteSpace:'nowrap', textAlign:'center', position:'sticky', top:0 };
const td = { padding:'6px 8px', borderBottom:'1px solid #f1f5f9', fontSize:12, whiteSpace:'nowrap' };

export default function TonbagPage() {
  const [rows,       setRows]       = useState([]);
  const [loading,    setLoading]    = useState(true);
  const [error,      setError]      = useState(null);
  const [keyword,    setKeyword]    = useState('');
  const [lotNo,      setLotNo]      = useState('');
  const [statusFlt,  setStatusFlt]  = useState('');
  const [editingId,  setEditingId]  = useState(null);
  const [processing, setProcessing] = useState(null);
  const [toast,      setToast]      = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const res = await getTonbagList({ keyword, lot_no: lotNo, status: statusFlt });
      setRows(res?.rows || res?.items || []);
    } catch(e) { setError(e.message); }
    finally { setLoading(false); }
  }, [keyword, lotNo, statusFlt, refreshKey]);

  useEffect(() => { load(); }, [load]);

  const handleSaveLocation = async (row, newLoc) => {
    setEditingId(null); setProcessing(row.id);
    try {
      const res = await api.put('/location/update', {
        lot_no: row.lot_no, sub_lt: row.sub_lt||0,
        new_location: newLoc, operator: 'web_user', reason_code: 'RELOCATE',
      });
      if (res?.success) {
        setToast({ msg: `위치 변경: ${row.lot_no} → ${newLoc}`, ok: true });
        setRefreshKey(k => k+1);
      } else {
        setToast({ msg: res?.message||'변경 실패', ok: false });
      }
    } catch(e) { setToast({ msg: e.message, ok: false }); }
    finally { setProcessing(null); }
  };

  const counts = rows.reduce((a,r) => { a[r.status]=(a[r.status]||0)+1; return a; }, {});

  return (
    <div style={{ padding:16, background:'#0f172a', minHeight:'100vh', color:'#f1f5f9' }}>
      {/* 헤더 */}
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:12 }}>
        <h2 style={{ fontSize:16, fontWeight:700, margin:0 }}>
          🧳 Tonbag List
          <span style={{ fontSize:12, color:'#64748b', marginLeft:8, fontWeight:400 }}>{rows.length}개</span>
        </h2>
        <button onClick={() => { window.location.href='/api/tools/export-tonbag-list'; }}
          style={{ padding:'7px 14px', background:'#2563eb', color:'#fff',
            border:'none', borderRadius:8, fontSize:12, fontWeight:700, cursor:'pointer' }}>
          📥 Excel
        </button>
      </div>

      {/* 상태 탭 */}
      <div style={{ display:'flex', gap:6, marginBottom:10, flexWrap:'wrap' }}>
        {['ALL',...Object.keys(STATUS_COLOR)].map(s => (
          <button key={s} onClick={() => setStatusFlt(s==='ALL'?'':s)} style={{
            padding:'4px 12px', borderRadius:20, border:'none',
            background: (s==='ALL'?statusFlt==='':statusFlt===s) ? (STATUS_COLOR[s]||'#3b82f6') : '#1e293b',
            color: (s==='ALL'?statusFlt==='':statusFlt===s) ? '#fff' : '#64748b',
            fontSize:11, cursor:'pointer',
          }}>
            {s==='ALL'?`전체(${rows.length})`:s} {s!=='ALL'&&counts[s]?`(${counts[s]})`:''}</button>
        ))}
      </div>

      {/* 검색 */}
      <div style={{ display:'flex', gap:8, marginBottom:10, flexWrap:'wrap' }}>
        <input value={keyword} onChange={e => setKeyword(e.target.value)}
          placeholder="UID / BL / 컨테이너..."
          style={{ padding:'6px 10px', fontSize:12, borderRadius:6, border:'1px solid #334155',
            background:'#1e293b', color:'#f1f5f9', width:200 }} />
        <input value={lotNo} onChange={e => setLotNo(e.target.value)}
          placeholder="LOT NO"
          style={{ padding:'6px 10px', fontSize:12, borderRadius:6, border:'1px solid #334155',
            background:'#1e293b', color:'#f1f5f9', width:140 }} />
        {(keyword||lotNo) && <button onClick={() => { setKeyword(''); setLotNo(''); }}
          style={{ padding:'6px 10px', fontSize:11, borderRadius:6, border:'none',
            background:'#334155', color:'#94a3b8', cursor:'pointer' }}>Clear</button>}
      </div>

      {error   && <div style={{ color:'#ef4444', fontSize:12, marginBottom:8 }}>❌ {error}</div>}
      {loading && <div style={{ color:'#64748b', padding:16 }}>Loading...</div>}

      {!loading && (
        <div style={{ overflow:'auto', maxHeight:'72vh', border:'1px solid #334155', borderRadius:8 }}>
          <table style={{ width:'100%', borderCollapse:'collapse' }}>
            <thead>
              <tr>{['No.','LOT NO','UID','STATUS','Weight(Kg)','LOCATION','CON RETURN','WAREHOUSE','ACTION'].map(h=>(
                <th key={h} style={th}>{h}</th>
              ))}</tr>
            </thead>
            <tbody>
              {rows.length === 0
                ? <tr><td colSpan={9} style={{...td,textAlign:'center',padding:32,color:'#94a3b8'}}>톤백 없음</td></tr>
                : rows.map((row, i) => {
                  const isEditing = editingId === row.id;
                  const sc = STATUS_COLOR[row.status]||'#94a3b8';
                  return (
                    <tr key={row.id||i}
                      onMouseEnter={e => e.currentTarget.style.background='#1e293b'}
                      onMouseLeave={e => e.currentTarget.style.background=''}>
                      <td style={{...td,textAlign:'center',color:'#64748b'}}>{i+1}</td>
                      <td style={{...td,fontWeight:600,color:'#3b82f6'}}>{row.lot_no}</td>
                      <td style={{...td,fontSize:11,color:'#64748b'}}>{row.tonbag_uid||'-'}</td>
                      <td style={{...td,textAlign:'center'}}>
                        <span style={{ background:sc+'22', color:sc, border:`1px solid ${sc}44`,
                          borderRadius:4, padding:'2px 8px', fontSize:10, fontWeight:700 }}>
                          {row.status}
                        </span>
                      </td>
                      <td style={{...td,textAlign:'right'}}>{Number(row.weight||0).toLocaleString()}</td>
                      {/* ★ 위치 수정 인라인 */}
                      <td style={{...td,textAlign:'center'}}>
                        {isEditing
                          ? <LocationEditor row={row}
                              onSave={v => handleSaveLocation(row, v)}
                              onCancel={() => setEditingId(null)} />
                          : <span style={{ cursor:'pointer', color:'#94a3b8', fontSize:11 }}
                              onClick={() => setEditingId(row.id)}>
                              {row.location||'(미지정)'} ✏️
                            </span>
                        }
                      </td>
                      <td style={{...td,textAlign:'center',fontSize:11}}>{row.con_return||'-'}</td>
                      <td style={{...td,fontSize:11,color:'#94a3b8'}}>{row.warehouse||'-'}</td>
                      <td style={{...td,textAlign:'center'}}>
                        <button onClick={() => setEditingId(row.id)}
                          style={{ padding:'4px 10px', fontSize:11, background:'#334155',
                            color:'#94a3b8', border:'none', borderRadius:5, cursor:'pointer' }}>
                          📍 위치
                        </button>
                      </td>
                    </tr>
                  );
                })
              }
            </tbody>
          </table>
        </div>
      )}

      {toast && <Toast msg={toast.msg} ok={toast.ok} onClose={() => setToast(null)} />}
    </div>
  );
}
