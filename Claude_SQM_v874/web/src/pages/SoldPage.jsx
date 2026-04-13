/**
 * SoldPage v2 — 출고 취소 버튼 + 날짜 필터 + 검색
 * 배치: web/src/pages/SoldPage.jsx
 */
import { useEffect, useState, useCallback } from 'react';
import { getSoldList } from '../api/tabsApi';
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

function CancelDialog({ row, onConfirm, onClose }) {
  return (
    <div style={{ position:'fixed', inset:0, background:'rgba(0,0,0,0.6)',
      display:'flex', alignItems:'center', justifyContent:'center', zIndex:9000 }}>
      <div style={{ background:'#1e293b', borderRadius:14, padding:28, width:360 }}>
        <div style={{ fontSize:18, fontWeight:700, color:'#f1f5f9', marginBottom:12 }}>출고 취소</div>
        <div style={{ color:'#94a3b8', fontSize:14, marginBottom:16 }}>
          <b style={{ color:'#f59e0b' }}>{row.lot_no}</b> — {row.customer||'-'}<br/>
          <span style={{ fontSize:12 }}>SUB_LT: {row.sub_lt??'-'} | {Number(row.sold_qty_mt||0).toFixed(3)} MT</span>
        </div>
        <div style={{ color:'#ef4444', fontSize:12, marginBottom:20 }}>⚠️ OUTBOUND → AVAILABLE 복귀됩니다.</div>
        <div style={{ display:'flex', gap:10 }}>
          <button onClick={onClose} style={{ flex:1, padding:'10px', borderRadius:8, border:'none',
            background:'#334155', color:'#94a3b8', cursor:'pointer' }}>닫기</button>
          <button onClick={onConfirm} style={{ flex:1, padding:'10px', borderRadius:8, border:'none',
            background:'#ef4444', color:'#fff', fontWeight:700, cursor:'pointer' }}>취소 확정</button>
        </div>
      </div>
    </div>
  );
}

const th = { padding:'8px 10px', background:'#f8fafc', borderBottom:'2px solid #e2e8f0',
  fontSize:11, fontWeight:700, whiteSpace:'nowrap', textAlign:'center', position:'sticky', top:0 };
const td = { padding:'6px 10px', borderBottom:'1px dashed rgba(51,65,85,0.3)', fontSize:12, whiteSpace:'nowrap' };

export default function SoldPage() {
  const [rows,       setRows]       = useState([]);
  const [loading,    setLoading]    = useState(true);
  const [error,      setError]      = useState(null);
  const [keyword,    setKeyword]    = useState('');
  const [dateFrom,   setDateFrom]   = useState('');
  const [dateTo,     setDateTo]     = useState('');
  const [cancelRow,  setCancelRow]  = useState(null);
  const [processing, setProcessing] = useState(null);
  const [toast,      setToast]      = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const res = await getSoldList({ keyword });
      setRows(res?.rows || res?.items || []);
    } catch(e) { setError(e.message); }
    finally { setLoading(false); }
  }, [keyword, refreshKey]);

  useEffect(() => { load(); }, [load]);

  // 날짜 필터 (프론트에서 처리)
  const display = rows.filter(r => {
    if (dateFrom && r.sold_date < dateFrom) return false;
    if (dateTo   && r.sold_date > dateTo)   return false;
    return true;
  });

  // 합계
  const totalMt = display.reduce((s, r) => s + Number(r.sold_qty_mt||0), 0);

  const handleCancel = async () => {
    if (!cancelRow) return;
    const row = cancelRow; setCancelRow(null); setProcessing(row.lot_no);
    try {
      const res = await api.put('/outbound/cancel', { lot_no: row.lot_no, sub_lt: row.sub_lt||0 });
      if (res?.success) {
        setToast({ msg: `${row.lot_no} 출고 취소 완료`, ok: true });
        setRefreshKey(k => k+1);
      } else {
        setToast({ msg: res?.message||'취소 실패', ok: false });
      }
    } catch(e) { setToast({ msg: e.message, ok: false }); }
    finally { setProcessing(null); }
  };

  return (
    <div style={{ padding:16, background:'#0f172a', minHeight:'100vh', color:'#f1f5f9' }}>
      {/* 헤더 */}
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:12 }}>
        <h2 style={{ fontSize:16, fontWeight:700, margin:0 }}>
          ✅ Sold (출고 완료)
          <span style={{ fontSize:12, color:'#64748b', marginLeft:8, fontWeight:400 }}>
            {display.length}건 / {totalMt.toFixed(3)} MT
          </span>
        </h2>
        <button onClick={() => { window.location.href='/api/tools/export-lot-list?status=OUTBOUND'; }}
          style={{ padding:'7px 14px', background:'#16a34a', color:'#fff', border:'none',
            borderRadius:8, fontSize:12, fontWeight:700, cursor:'pointer' }}>
          📥 Excel
        </button>
      </div>

      {/* 검색 + 날짜 필터 */}
      <div style={{ display:'flex', gap:8, marginBottom:10, flexWrap:'wrap', alignItems:'center' }}>
        <input value={keyword} onChange={e => setKeyword(e.target.value)}
          placeholder="LOT / Customer / Picking NO..."
          style={{ padding:'6px 10px', fontSize:12, borderRadius:6, border:'1px solid #334155',
            background:'#1e293b', color:'#f1f5f9', width:240 }} />
        <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)}
          style={{ padding:'5px 8px', fontSize:12, borderRadius:6, border:'1px solid #334155',
            background:'#1e293b', color:'#f1f5f9' }} />
        <span style={{ color:'#64748b', fontSize:12 }}>~</span>
        <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)}
          style={{ padding:'5px 8px', fontSize:12, borderRadius:6, border:'1px solid #334155',
            background:'#1e293b', color:'#f1f5f9' }} />
        {(keyword||dateFrom||dateTo) && (
          <button onClick={() => { setKeyword(''); setDateFrom(''); setDateTo(''); }}
            style={{ padding:'5px 10px', fontSize:11, borderRadius:6, border:'none',
              background:'#334155', color:'#94a3b8', cursor:'pointer' }}>초기화</button>
        )}
      </div>

      {error   && <div style={{ color:'#ef4444', fontSize:12, marginBottom:8 }}>❌ {error}</div>}
      {loading && <div style={{ color:'#64748b', padding:16 }}>Loading...</div>}

      {!loading && (
        <div style={{ overflow:'auto', maxHeight:'75vh', border:'1px solid #334155', borderRadius:8 }}>
          <table style={{ width:'100%', borderCollapse:'collapse' }}>
            <thead>
              <tr>{['No.','LOT NO','PRODUCT','TONBAG UID','CUSTOMER','QTY(MT)','SOLD DATE','STATUS','ACTION'].map(h => (
                <th key={h} style={th}>{h}</th>
              ))}</tr>
            </thead>
            <tbody>
              {display.length === 0
                ? <tr><td colSpan={9} style={{...td, textAlign:'center', padding:32, color:'#94a3b8'}}>출고 내역 없음</td></tr>
                : display.map((row, i) => (
                  <tr key={`${row.lot_no}-${i}`}
                    onMouseEnter={e => e.currentTarget.style.background='#1e293b'}
                    onMouseLeave={e => e.currentTarget.style.background=''}>
                    <td style={{...td, textAlign:'center', color:'#64748b'}}>{i+1}</td>
                    <td style={{...td, fontWeight:600, color:'#8b5cf6'}}>{row.lot_no}</td>
                    <td style={td}>{row.product||'-'}</td>
                    <td style={{...td, fontSize:11, color:'#64748b'}}>{row.tonbag_uid||'-'}</td>
                    <td style={td}>{row.customer||'-'}</td>
                    <td style={{...td, textAlign:'right', fontWeight:600}}>{Number(row.sold_qty_mt||0).toFixed(3)}</td>
                    <td style={{...td, textAlign:'center', fontSize:11}}>{row.sold_date||row.delivery_date||'-'}</td>
                    <td style={{...td, textAlign:'center'}}>
                      <span style={{ background:'#8b5cf622', color:'#8b5cf6',
                        border:'1px solid #8b5cf644', borderRadius:4, padding:'2px 8px', fontSize:10, fontWeight:700 }}>
                        {row.status||'SOLD'}
                      </span>
                    </td>
                    <td style={{...td, textAlign:'center'}}>
                      <button onClick={() => setCancelRow(row)}
                        disabled={processing===row.lot_no}
                        style={{ padding:'4px 10px', fontSize:11, fontWeight:700,
                          background:'#ef444422', color:'#ef4444',
                          border:'1px solid #ef444444', borderRadius:5,
                          cursor:'pointer' }}>
                        ↩ 취소
                      </button>
                    </td>
                  </tr>
                ))
              }
            </tbody>
          </table>
        </div>
      )}

      {cancelRow && <CancelDialog row={cancelRow} onConfirm={handleCancel} onClose={() => setCancelRow(null)} />}
      {toast && <Toast msg={toast.msg} ok={toast.ok} onClose={() => setToast(null)} />}
    </div>
  );
}
