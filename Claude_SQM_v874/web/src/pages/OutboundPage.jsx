/**
 * OutboundPage v3 — P0-S3: 확정/취소 버튼 추가
 * 배치: web/src/pages/OutboundPage.jsx (기존 덮어쓰기)
 *
 * 변경사항:
 *   1. 각 행 ACTION 컬럼에 "확정"(PICKED만) / "취소" 버튼 추가
 *   2. 상단 "PICKED 전체 확정" 일괄 버튼 추가
 *   3. confirmOutbound / cancelOutbound API 연결
 *   4. 확인 다이얼로그 + Toast 피드백
 */
import { useEffect, useState, useCallback } from 'react';
import { getOutboundList } from '../api/tabsApi';
import { confirmOutbound, cancelOutbound } from '../api/writeApi';
import OutboundModal from '../components/OutboundModal';

/* ── Toast ── */
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

/* ── Confirm Dialog ── */
function ConfirmDialog({ msg, onYes, onNo }) {
  return (
    <div style={{
      position:'fixed', inset:0, background:'rgba(0,0,0,0.5)', zIndex:10000,
      display:'flex', alignItems:'center', justifyContent:'center',
    }} onClick={onNo}>
      <div style={{
        background:'#1e293b', borderRadius:12, padding:'24px 32px',
        maxWidth:400, boxShadow:'0 8px 32px rgba(0,0,0,0.6)',
      }} onClick={e => e.stopPropagation()}>
        <div style={{ color:'#f1f5f9', fontSize:14, marginBottom:16, lineHeight:1.5 }}>{msg}</div>
        <div style={{ display:'flex', gap:10, justifyContent:'flex-end' }}>
          <button onClick={onNo} style={{
            padding:'8px 20px', borderRadius:6, border:'1px solid #475569',
            background:'transparent', color:'#94a3b8', fontSize:13, fontWeight:600, cursor:'pointer',
          }}>취소</button>
          <button onClick={onYes} style={{
            padding:'8px 20px', borderRadius:6, border:'none',
            background:'#dc2626', color:'#fff', fontSize:13, fontWeight:700, cursor:'pointer',
          }}>확인</button>
        </div>
      </div>
    </div>
  );
}

const STATUS_COLOR = {
  PENDING:'#94a3b8', RESERVED:'#f59e0b', PICKED:'#3b82f6',
  OUTBOUND:'#8b5cf6', COMPLETED:'#22c55e', CANCELLED:'#ef4444',
};

const th = { padding:'8px 10px', background:'#f8fafc', borderBottom:'2px solid #e2e8f0', fontSize:11, fontWeight:700, whiteSpace:'nowrap', textAlign:'center', position:'sticky', top:0 };
const td = { padding:'6px 10px', borderBottom:'1px dashed rgba(51,65,85,0.3)', fontSize:12, whiteSpace:'nowrap' };

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
  const [confirm,     setConfirm]     = useState(null);   // { msg, onYes }
  const [actionLoading, setActionLoading] = useState(''); // 'confirm:LOT' or 'cancel:LOT:SUB'

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const res = await getOutboundList({ keyword });
      setRows(res?.rows || res?.items || []);
    } catch(e) { setError(e.message); }
    finally { setLoading(false); }
  }, [keyword, refreshKey]);

  useEffect(() => { load(); }, [load]);

  const refresh = () => setRefreshKey(k => k + 1);

  /* ── 단건 확정 (PICKED → OUTBOUND) ── */
  const handleConfirmSingle = (lotNo) => {
    setConfirm({
      msg: `LOT ${lotNo}의 PICKED 톤백을 전부 OUTBOUND로 확정하시겠습니까?`,
      onYes: async () => {
        setConfirm(null);
        setActionLoading(`confirm:${lotNo}`);
        try {
          const res = await confirmOutbound(lotNo);
          if (res.success) {
            setToast({ msg: res.message || `${lotNo} 확정 완료`, ok: true });
            refresh();
          } else {
            setToast({ msg: res.message || '확정 실패', ok: false });
          }
        } catch (e) {
          setToast({ msg: e.message, ok: false });
        } finally {
          setActionLoading('');
        }
      },
    });
  };

  /* ── 단건 취소 ── */
  const handleCancelSingle = (lotNo, subLt) => {
    const target = subLt !== undefined ? `LOT ${lotNo} / Sub ${subLt}` : `LOT ${lotNo}`;
    setConfirm({
      msg: `${target} 출고를 취소하시겠습니까?\n취소 시 AVAILABLE 상태로 복원됩니다.`,
      onYes: async () => {
        setConfirm(null);
        setActionLoading(`cancel:${lotNo}:${subLt}`);
        try {
          const res = await cancelOutbound(lotNo, subLt);
          if (res.success) {
            setToast({ msg: res.message || '취소 완료', ok: true });
            refresh();
          } else {
            setToast({ msg: res.message || '취소 실패', ok: false });
          }
        } catch (e) {
          setToast({ msg: e.message, ok: false });
        } finally {
          setActionLoading('');
        }
      },
    });
  };

  /* ── PICKED 전체 확정 ── */
  const pickedRows = rows.filter(r => r.status === 'PICKED');
  const handleBulkConfirm = () => {
    if (pickedRows.length === 0) { setToast({ msg: 'PICKED 상태 항목이 없습니다.', ok: false }); return; }
    const lotNos = [...new Set(pickedRows.map(r => r.lot_no || r.sale_ref))].filter(Boolean);
    setConfirm({
      msg: `PICKED 상태 ${pickedRows.length}건 (LOT ${lotNos.length}개)을 전부 OUTBOUND로 확정하시겠습니까?`,
      onYes: async () => {
        setConfirm(null);
        setActionLoading('bulk-confirm');
        let successCount = 0;
        let failCount = 0;
        for (const lotNo of lotNos) {
          try {
            const res = await confirmOutbound(lotNo, true);
            if (res.success) successCount++; else failCount++;
          } catch { failCount++; }
        }
        setToast({
          msg: `일괄 확정: 성공 ${successCount} / 실패 ${failCount}`,
          ok: failCount === 0,
        });
        setActionLoading('');
        refresh();
      },
    });
  };

  const counts = rows.reduce((a, r) => { a[r.status] = (a[r.status]||0)+1; return a; }, {});
  const display = statusTab === 'ALL' ? rows : rows.filter(r => r.status === statusTab);

  return (
    <div style={{ padding:16, background:'#0f172a', minHeight:'100vh', color:'#f1f5f9' }}>
      {/* 헤더 */}
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:12, flexWrap:'wrap', gap:8 }}>
        <h2 style={{ fontSize:16, fontWeight:700, margin:0 }}>
          📤 Outbound Schedule
          <span style={{ fontSize:12, color:'#64748b', marginLeft:8, fontWeight:400 }}>{rows.length}건</span>
        </h2>
        <div style={{ display:'flex', gap:8 }}>
          {/* PICKED 전체 확정 버튼 */}
          {pickedRows.length > 0 && (
            <button onClick={handleBulkConfirm}
              disabled={actionLoading === 'bulk-confirm'}
              style={{
                padding:'8px 16px', background:'#16a34a', color:'#fff',
                border:'none', borderRadius:8, fontSize:12, fontWeight:700, cursor:'pointer',
                opacity: actionLoading === 'bulk-confirm' ? 0.6 : 1,
              }}>
              {actionLoading === 'bulk-confirm' ? '처리 중...' : `✅ PICKED 전체 확정 (${pickedRows.length})`}
            </button>
          )}
          <button onClick={() => setOutboundOpen(true)} style={{
            padding:'8px 18px', background:'#8b5cf6', color:'#fff',
            border:'none', borderRadius:8, fontSize:13, fontWeight:700, cursor:'pointer',
          }}>📤 출고 실행</button>
        </div>
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
                : display.map((row, i) => {
                  const lotNo = row.lot_no || row.sale_ref || '';
                  const isPicked = row.status === 'PICKED';
                  const isCancellable = ['PICKED','RESERVED','OUTBOUND'].includes(row.status);
                  const isConfirming = actionLoading === `confirm:${lotNo}`;
                  const isCancelling = actionLoading === `cancel:${lotNo}:${row.sub_lt}`;

                  return (
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
                        <div style={{ display:'flex', gap:4, justifyContent:'center' }}>
                          {/* 출고 실행 */}
                          <button onClick={() => { setSelectedLot(row.sale_ref||''); setOutboundOpen(true); }}
                            style={{ padding:'3px 8px', fontSize:10, fontWeight:700,
                              background:'#8b5cf6', color:'#fff', border:'none', borderRadius:4, cursor:'pointer' }}>
                            실행
                          </button>
                          {/* 확정 (PICKED만) */}
                          {isPicked && (
                            <button onClick={() => handleConfirmSingle(lotNo)}
                              disabled={isConfirming}
                              style={{ padding:'3px 8px', fontSize:10, fontWeight:700,
                                background:'#16a34a', color:'#fff', border:'none', borderRadius:4, cursor:'pointer',
                                opacity: isConfirming ? 0.6 : 1 }}>
                              {isConfirming ? '...' : '확정'}
                            </button>
                          )}
                          {/* 취소 */}
                          {isCancellable && (
                            <button onClick={() => handleCancelSingle(lotNo, row.sub_lt)}
                              disabled={isCancelling}
                              style={{ padding:'3px 8px', fontSize:10, fontWeight:700,
                                background:'#dc2626', color:'#fff', border:'none', borderRadius:4, cursor:'pointer',
                                opacity: isCancelling ? 0.6 : 1 }}>
                              {isCancelling ? '...' : '취소'}
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })
              }
            </tbody>
          </table>
        </div>
      )}

      <OutboundModal open={outboundOpen}
        onClose={() => { setOutboundOpen(false); setSelectedLot(''); refresh(); }}
        initialLotNo={selectedLot} />
      {toast && <Toast msg={toast.msg} ok={toast.ok} onClose={() => setToast(null)} />}
      {confirm && <ConfirmDialog msg={confirm.msg} onYes={confirm.onYes} onNo={() => setConfirm(null)} />}
    </div>
  );
}
