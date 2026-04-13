/**
 * ProductMasterPage v2 — 제품 추가/수정/삭제 완성
 * 배치: web/src/pages/ProductMasterPage.jsx
 */
import { useState, useEffect, useCallback } from 'react';
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

const EMPTY = { product_name:'', product_code:'', unit:'MT', description:'' };

export default function ProductMasterPage() {
  const [rows,    setRows]    = useState([]);
  const [loading, setLoading] = useState(true);
  const [form,    setForm]    = useState(EMPTY);
  const [editId,  setEditId]  = useState(null);
  const [toast,   setToast]   = useState(null);
  const [showForm,setShowForm]= useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get('/products/list');
      setRows(res?.rows || res?.items || []);
    } catch(e) { console.error(e); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleSave = async () => {
    try {
      if (editId) {
        await api.put(`/products/${editId}`, form);
        setToast({ msg: `${form.product_name} 수정 완료`, ok: true });
      } else {
        await api.post('/products/create', form);
        setToast({ msg: `${form.product_name} 추가 완료`, ok: true });
      }
      setForm(EMPTY); setEditId(null); setShowForm(false); load();
    } catch(e) { setToast({ msg: e.message, ok: false }); }
  };

  const handleDelete = async (id, name) => {
    if (!window.confirm(`"${name}" 삭제하시겠습니까?`)) return;
    try {
      await api.delete(`/products/${id}`);
      setToast({ msg: `${name} 삭제 완료`, ok: true }); load();
    } catch(e) { setToast({ msg: e.message, ok: false }); }
  };

  const startEdit = (row) => {
    setForm({ product_name: row.product_name||'', product_code: row.product_code||'',
              unit: row.unit||'MT', description: row.description||'' });
    setEditId(row.id); setShowForm(true);
  };

  const inputS = { padding:'7px 10px', fontSize:13, borderRadius:6, border:'1px solid #334155',
    background:'#0f172a', color:'#f1f5f9', width:'100%' };

  return (
    <div style={{ padding:20, background:'#0f172a', minHeight:'100vh', color:'#f1f5f9' }}>
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:16 }}>
        <h2 style={{ fontSize:16, fontWeight:700, margin:0 }}>🏷️ 제품 마스터</h2>
        <button onClick={() => { setForm(EMPTY); setEditId(null); setShowForm(true); }}
          style={{ padding:'8px 18px', background:'#3b82f6', color:'#fff',
            border:'none', borderRadius:8, fontSize:13, fontWeight:700, cursor:'pointer' }}>
          + 제품 추가
        </button>
      </div>

      {/* 폼 */}
      {showForm && (
        <div style={{ background:'#1e293b', border:'1px solid #334155', borderRadius:10, padding:20, marginBottom:16 }}>
          <h3 style={{ fontSize:14, marginBottom:14, color:'#94a3b8' }}>
            {editId ? '제품 수정' : '새 제품 추가'}
          </h3>
          <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:12, marginBottom:14 }}>
            {[
              ['제품명 *', 'product_name'],
              ['제품 코드', 'product_code'],
              ['단위', 'unit'],
              ['설명', 'description'],
            ].map(([label, key]) => (
              <div key={key}>
                <div style={{ fontSize:11, color:'#64748b', marginBottom:4 }}>{label}</div>
                <input value={form[key]} onChange={e => setForm(f => ({...f,[key]:e.target.value}))}
                  style={inputS} />
              </div>
            ))}
          </div>
          <div style={{ display:'flex', gap:8 }}>
            <button onClick={handleSave} disabled={!form.product_name}
              style={{ padding:'8px 20px', background:'#22c55e', color:'#fff', border:'none',
                borderRadius:8, fontSize:13, fontWeight:700, cursor:'pointer' }}>
              {editId ? '수정 저장' : '추가'}
            </button>
            <button onClick={() => { setShowForm(false); setForm(EMPTY); setEditId(null); }}
              style={{ padding:'8px 16px', background:'#334155', color:'#94a3b8',
                border:'none', borderRadius:8, fontSize:13, cursor:'pointer' }}>취소</button>
          </div>
        </div>
      )}

      {loading && <div style={{ color:'#64748b', padding:16 }}>Loading...</div>}

      {!loading && (
        <div style={{ border:'1px solid #334155', borderRadius:8, overflow:'auto' }}>
          <table style={{ width:'100%', borderCollapse:'collapse' }}>
            <thead>
              <tr>{['No.','제품명','코드','단위','설명','수정','삭제'].map(h=>(
                <th key={h} style={{ padding:'8px 10px', background:'#1e293b', borderBottom:'1px solid #334155',
                  fontSize:11, fontWeight:700, color:'#94a3b8', textAlign:'center' }}>{h}</th>
              ))}</tr>
            </thead>
            <tbody>
              {rows.length===0
                ? <tr><td colSpan={7} style={{ textAlign:'center', padding:32, color:'#94a3b8', fontSize:13 }}>
                    제품 없음 — 위 버튼으로 추가하세요
                  </td></tr>
                : rows.map((row,i) => (
                  <tr key={row.id}
                    onMouseEnter={e=>e.currentTarget.style.background='#1e293b'}
                    onMouseLeave={e=>e.currentTarget.style.background=''}>
                    <td style={{ padding:'6px 10px', textAlign:'center', color:'#64748b', fontSize:12 }}>{i+1}</td>
                    <td style={{ padding:'6px 10px', fontWeight:600, fontSize:13 }}>{row.product_name}</td>
                    <td style={{ padding:'6px 10px', fontSize:12, color:'#94a3b8' }}>{row.product_code||'-'}</td>
                    <td style={{ padding:'6px 10px', fontSize:12, textAlign:'center' }}>{row.unit||'MT'}</td>
                    <td style={{ padding:'6px 10px', fontSize:11, color:'#64748b', maxWidth:200, overflow:'hidden', textOverflow:'ellipsis' }}>{row.description||'-'}</td>
                    <td style={{ padding:'6px 10px', textAlign:'center' }}>
                      <button onClick={() => startEdit(row)}
                        style={{ padding:'4px 10px', fontSize:11, background:'#334155', color:'#94a3b8',
                          border:'none', borderRadius:5, cursor:'pointer' }}>✏️ 수정</button>
                    </td>
                    <td style={{ padding:'6px 10px', textAlign:'center' }}>
                      <button onClick={() => handleDelete(row.id, row.product_name)}
                        style={{ padding:'4px 10px', fontSize:11, background:'#ef444422', color:'#ef4444',
                          border:'1px solid #ef444444', borderRadius:5, cursor:'pointer' }}>🗑️ 삭제</button>
                    </td>
                  </tr>
                ))
              }
            </tbody>
          </table>
        </div>
      )}

      {toast && <Toast msg={toast.msg} ok={toast.ok} onClose={() => setToast(null)} />}
    </div>
  );
}
