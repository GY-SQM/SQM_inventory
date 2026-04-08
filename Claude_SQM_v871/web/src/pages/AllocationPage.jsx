/**
 * AllocationPage v2 — 예약 실행 + 취소 버튼 완성
 * 배치: web/src/pages/AllocationPage.jsx (기존 덮어쓰기)
 * 변경:
 *   1. 상단 "📋 예약 등록" 버튼 → AllocationInputModal 연결
 *   2. 각 행에 "▶ 실행" 버튼 → RESERVED → PICKED
 *   3. 각 행에 "✕ 취소" 버튼 → RESERVED → CANCELLED
 *   4. 상태별 필터 탭
 *   5. 완료 후 자동 새로고침 + 토스트 알림
 */
import { useEffect, useState, useCallback } from 'react';
import AllocationInputModal from '../components/AllocationInputModal';
import { getAllocationList } from '../api/tabsApi';
import { api } from '../api/client';

// ── 상태 색상 ──────────────────────────────────────────────
const STATUS_META = {
  RESERVED:   { color: '#f59e0b', bg: '#f59e0b22', label: '예약' },
  EXECUTED:   { color: '#22c55e', bg: '#22c55e22', label: '실행완료' },
  CANCELLED:  { color: '#ef4444', bg: '#ef444422', label: '취소' },
  PICKED:     { color: '#3b82f6', bg: '#3b82f622', label: '피킹' },
  PENDING:    { color: '#94a3b8', bg: '#94a3b822', label: '대기' },
};

function StatusBadge({ status }) {
  const m = STATUS_META[status] || { color: '#94a3b8', bg: '#94a3b822', label: status };
  return (
    <span style={{
      background: m.bg, color: m.color, border: `1px solid ${m.color}44`,
      borderRadius: 4, padding: '2px 8px', fontSize: 10, fontWeight: 700,
    }}>{m.label}</span>
  );
}

// ── 토스트 ──────────────────────────────────────────────────
function Toast({ msg, ok, onClose }) {
  useEffect(() => { const t = setTimeout(onClose, 3500); return () => clearTimeout(t); }, [onClose]);
  return (
    <div style={{
      position: 'fixed', bottom: 24, left: '50%', transform: 'translateX(-50%)',
      background: ok ? '#16a34a' : '#dc2626', color: '#fff',
      padding: '12px 24px', borderRadius: 10, fontWeight: 700,
      fontSize: 14, zIndex: 9999, boxShadow: '0 4px 16px rgba(0,0,0,0.4)',
    }}>
      {ok ? '✅' : '❌'} {msg}
    </div>
  );
}

// ── 취소 확인 다이얼로그 ────────────────────────────────────
function CancelDialog({ row, onConfirm, onClose }) {
  return (
    <div style={{ position:'fixed', inset:0, background:'rgba(0,0,0,0.6)',
      display:'flex', alignItems:'center', justifyContent:'center', zIndex:9000 }}>
      <div style={{ background:'#1e293b', borderRadius:14, padding:28, width:360 }}>
        <div style={{ fontSize:18, fontWeight:700, color:'#f1f5f9', marginBottom:12 }}>예약 취소</div>
        <div style={{ color:'#94a3b8', fontSize:14, marginBottom:16 }}>
          아래 예약을 취소하시겠습니까?<br />
          <b style={{ color:'#f59e0b' }}>{row.lot_no}</b>
          {row.customer && <> — {row.customer}</>}
          {row.sale_ref && <> ({row.sale_ref})</>}
        </div>
        <div style={{ color:'#ef4444', fontSize:12, marginBottom:20 }}>
          ⚠️ RESERVED → CANCELLED. 되돌리기 어렵습니다.
        </div>
        <div style={{ display:'flex', gap:10 }}>
          <button onClick={onClose} style={{ flex:1, padding:'10px', borderRadius:8,
            border:'none', background:'#334155', color:'#94a3b8', cursor:'pointer' }}>닫기</button>
          <button onClick={onConfirm} style={{ flex:1, padding:'10px', borderRadius:8,
            border:'none', background:'#ef4444', color:'#fff',
            fontWeight:700, cursor:'pointer' }}>취소 확정</button>
        </div>
      </div>
    </div>
  );
}

const thS = {
  padding: '8px 6px', background: '#f8fafc', borderBottom: '2px solid #e2e8f0',
  fontSize: 11, fontWeight: 700, position: 'sticky', top: 0,
  whiteSpace: 'nowrap', textAlign: 'center',
};
const tdS = { padding: '6px 6px', borderBottom: '1px solid #1e293b', fontSize: 12, whiteSpace: 'nowrap' };

const STATUS_TABS = ['ALL', 'RESERVED', 'EXECUTED', 'CANCELLED', 'PICKED'];

export default function AllocationPage() {
  const [rows,       setRows]       = useState([]);
  const [loading,    setLoading]    = useState(true);
  const [error,      setError]      = useState(null);
  const [keyword,    setKeyword]    = useState('');
  const [statusTab,  setStatusTab]  = useState('ALL');
  const [allocOpen,  setAllocOpen]  = useState(false);
  const [cancelRow,  setCancelRow]  = useState(null);
  const [toast,      setToast]      = useState(null);
  const [processing, setProcessing] = useState(null);  // plan_id
  const [refreshKey, setRefreshKey] = useState(0);

  // ── 데이터 로드 ────────────────────────────────────────────
  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const res = await getAllocationList({ keyword, status: statusTab === 'ALL' ? '' : statusTab });
      setRows(res?.rows || res?.items || res?.data || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [keyword, statusTab, refreshKey]);

  useEffect(() => { load(); }, [load]);

  // ── 상태별 카운트 ──────────────────────────────────────────
  const counts = rows.reduce((acc, r) => {
    acc[r.status] = (acc[r.status] || 0) + 1;
    return acc;
  }, {});

  // ── 예약 실행 (RESERVED → PICKED) ─────────────────────────
  const handleExecute = async (row) => {
    setProcessing(row.id);
    try {
      const res = await api.post('/outbound/execute', {
        items: [{
          lot_no: row.lot_no,
          sub_lt: row.sub_lt || 0,
          qty_kg: row.qty_kg || 0,
          customer: row.customer || '',
        }],
        sale_ref:      row.sale_ref || '',
        customer:      row.customer || '',
        source:        'WEB_ALLOCATION',
        stop_at_picked: true,
      });
      if (res?.success) {
        setToast({ msg: `${row.lot_no} 피킹 완료`, ok: true });
        setRefreshKey(k => k + 1);
      } else {
        setToast({ msg: res?.message || '실행 실패', ok: false });
      }
    } catch (e) {
      setToast({ msg: e.message, ok: false });
    } finally {
      setProcessing(null);
    }
  };

  // ── 예약 취소 (RESERVED → CANCELLED) ──────────────────────
  const handleCancel = async () => {
    if (!cancelRow) return;
    const row = cancelRow;
    setCancelRow(null);
    setProcessing(row.id);
    try {
      // plan_id 기반 취소 시도
      const res = await api.put('/outbound/cancel', {
        lot_no: row.lot_no,
        sub_lt: row.sub_lt || 0,
        plan_id: row.id,
      });
      if (res?.success) {
        setToast({ msg: `${row.lot_no} 예약 취소 완료`, ok: true });
        setRefreshKey(k => k + 1);
      } else {
        setToast({ msg: res?.message || '취소 실패', ok: false });
      }
    } catch (e) {
      setToast({ msg: e.message, ok: false });
    } finally {
      setProcessing(null);
    }
  };

  // ── ★ Q2: 복귀 처리 (EXECUTED/PICKED → AVAILABLE) ──────────
  const handleRevert = async (row) => {
    setProcessing(row.id);
    try {
      const res = await api.put('/outbound/cancel', {
        lot_no: row.lot_no,
        sub_lt: row.sub_lt || 0,
      });
      if (res?.success) {
        setToast({ msg: `${row.lot_no} AVAILABLE 복귀 완료`, ok: true });
        setRefreshKey(k => k + 1);
      } else {
        setToast({ msg: res?.message || '복귀 실패', ok: false });
      }
    } catch (e) {
      setToast({ msg: e.message, ok: false });
    } finally {
      setProcessing(null);
    }
  };

  // ── 렌더 ──────────────────────────────────────────────────
  const displayRows = statusTab === 'ALL'
    ? rows
    : rows.filter(r => r.status === statusTab);

  return (
    <div style={{ padding:16, background:'#0f172a', minHeight:'100vh', color:'#f1f5f9' }}>

      {/* ── 헤더 ── */}
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:14 }}>
        <h2 style={{ fontSize:16, fontWeight:700, color:'#f1f5f9', margin:0 }}>
          📋 Allocation Plan
          <span style={{ fontSize:12, color:'#64748b', marginLeft:8, fontWeight:400 }}>
            총 {rows.length}건
          </span>
        </h2>
        {/* ★ 예약 등록 버튼 */}
        <button
          onClick={() => setAllocOpen(true)}
          style={{ padding:'8px 18px', background:'#3b82f6', color:'#fff',
            border:'none', borderRadius:8, fontSize:13, fontWeight:700,
            cursor:'pointer' }}
          onMouseEnter={e => e.currentTarget.style.background = '#2563eb'}
          onMouseLeave={e => e.currentTarget.style.background = '#3b82f6'}
        >
          📋 예약 등록 (Excel)
        </button>
      </div>

      {/* ── 상태 탭 ── */}
      <div style={{ display:'flex', gap:6, marginBottom:12, flexWrap:'wrap' }}>
        {STATUS_TABS.map(s => {
          const cnt = s === 'ALL' ? rows.length : (counts[s] || 0);
          const m   = STATUS_META[s] || { color:'#94a3b8' };
          const active = statusTab === s;
          return (
            <button key={s} onClick={() => setStatusTab(s)} style={{
              padding:'5px 14px', borderRadius:20, border:'none',
              background: active ? (m.color || '#3b82f6') : '#1e293b',
              color: active ? '#fff' : '#64748b',
              fontSize:12, fontWeight: active ? 700 : 400, cursor:'pointer',
            }}>
              {s === 'ALL' ? '전체' : (STATUS_META[s]?.label || s)} {cnt > 0 && `(${cnt})`}
            </button>
          );
        })}
      </div>

      {/* ── 검색 ── */}
      <div style={{ display:'flex', gap:8, marginBottom:10 }}>
        <input
          value={keyword}
          onChange={e => setKeyword(e.target.value)}
          placeholder="LOT / Customer / Sale Ref 검색..."
          style={{ padding:'6px 10px', fontSize:12, borderRadius:6,
            border:'1px solid #334155', background:'#1e293b', color:'#f1f5f9', width:280 }}
        />
        {keyword && (
          <button onClick={() => setKeyword('')} style={{ padding:'6px 12px', fontSize:12,
            borderRadius:6, border:'none', background:'#334155', color:'#94a3b8', cursor:'pointer' }}>
            Clear
          </button>
        )}
      </div>

      {error   && <div style={{ color:'#ef4444', marginBottom:8, fontSize:12 }}>❌ {error}</div>}
      {loading && <div style={{ color:'#64748b', padding:16 }}>Loading...</div>}

      {!loading && (
        <div style={{ overflow:'auto', maxHeight:'70vh', border:'1px solid #334155', borderRadius:8 }}>
          <table style={{ width:'100%', borderCollapse:'collapse' }}>
            <thead>
              <tr>
                {['No.','LOT NO','PRODUCT','SAP NO','CUSTOMER','SALE REF',
                  'QTY(MT)','OUTBOUND DATE','STATUS','SUB LT','ACTION'].map(h => (
                  <th key={h} style={thS}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {displayRows.length === 0
                ? <tr><td colSpan={11} style={{ ...tdS, textAlign:'center', padding:32, color:'#94a3b8' }}>
                    예약 항목 없음
                  </td></tr>
                : displayRows.map((row, idx) => {
                  const isProcessing = processing === row.id;
                  const canExecute   = row.status === 'RESERVED';
                  const canCancel    = row.status === 'RESERVED';
                  const canRevert    = row.status === 'EXECUTED' || row.status === 'PICKED';
                  return (
                    <tr key={row.id || idx}
                      onMouseEnter={e => e.currentTarget.style.background = '#1e293b'}
                      onMouseLeave={e => e.currentTarget.style.background = ''}
                    >
                      <td style={{ ...tdS, textAlign:'center', color:'#94a3b8' }}>{idx + 1}</td>
                      <td style={{ ...tdS, fontWeight:600, color:'#3b82f6' }}>{row.lot_no}</td>
                      <td style={{ ...tdS }}>{row.product || '-'}</td>
                      <td style={{ ...tdS, color:'#94a3b8' }}>{row.sap_no || '-'}</td>
                      <td style={{ ...tdS }}>{row.customer || '-'}</td>
                      <td style={{ ...tdS, color:'#94a3b8' }}>{row.sale_ref || '-'}</td>
                      <td style={{ ...tdS, textAlign:'right' }}>
                        {row.qty_mt != null ? Number(row.qty_mt).toFixed(3) : '-'}
                      </td>
                      <td style={{ ...tdS, textAlign:'center', fontSize:11 }}>
                        {row.outbound_date || '-'}
                      </td>
                      <td style={{ ...tdS, textAlign:'center' }}>
                        <StatusBadge status={row.status} />
                      </td>
                      <td style={{ ...tdS, textAlign:'center', color:'#94a3b8' }}>
                        {row.sub_lt ?? '-'}
                      </td>
                      {/* ★ 액션 버튼 */}
                      <td style={{ ...tdS, textAlign:'center' }}>
                        <div style={{ display:'flex', gap:4, justifyContent:'center' }}>
                          {/* 실행 버튼 */}
                          <button
                            onClick={() => !isProcessing && canExecute && handleExecute(row)}
                            disabled={!canExecute || isProcessing}
                            title={canExecute ? '피킹 실행 (RESERVED → PICKED)' : '실행 불가 상태'}
                            style={{
                              padding:'4px 10px', fontSize:11, fontWeight:700,
                              background: canExecute ? '#22c55e' : '#1e293b',
                              color: canExecute ? '#fff' : '#475569',
                              border:'none', borderRadius:5,
                              cursor: canExecute ? 'pointer' : 'not-allowed',
                              opacity: isProcessing ? 0.5 : 1,
                            }}
                          >
                            {isProcessing ? '⏳' : '▶ 실행'}
                          </button>

                          {/* 취소 버튼 */}
                          <button
                            onClick={() => !isProcessing && canCancel && setCancelRow(row)}
                            disabled={!canCancel || isProcessing}
                            title={canCancel ? '예약 취소' : '취소 불가 상태'}
                            style={{
                              padding:'4px 10px', fontSize:11, fontWeight:700,
                              background: canCancel ? '#ef444422' : '#1e293b',
                              color: canCancel ? '#ef4444' : '#475569',
                              border: canCancel ? '1px solid #ef444444' : '1px solid #1e293b',
                              borderRadius:5,
                              cursor: canCancel ? 'pointer' : 'not-allowed',
                            }}
                          >
                            ✕ 취소
                          </button>

                          {/* ★ Q2: 복귀 버튼 (EXECUTED/PICKED → AVAILABLE) */}
                          <button
                            onClick={() => !isProcessing && canRevert && handleRevert(row)}
                            disabled={!canRevert || isProcessing}
                            title={canRevert ? 'AVAILABLE로 복귀' : '복귀 불가 상태'}
                            style={{
                              padding:'4px 10px', fontSize:11, fontWeight:700,
                              background: canRevert ? '#f59e0b22' : '#1e293b',
                              color: canRevert ? '#f59e0b' : '#475569',
                              border: canRevert ? '1px solid #f59e0b44' : '1px solid #1e293b',
                              borderRadius:5,
                              cursor: canRevert ? 'pointer' : 'not-allowed',
                            }}
                          >
                            ↩ 복귀
                          </button>
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

      {/* ── Allocation 등록 모달 ── */}
      <AllocationInputModal
        open={allocOpen}
        onClose={() => {
          setAllocOpen(false);
          setRefreshKey(k => k + 1);
        }}
      />

      {/* ── 취소 확인 다이얼로그 ── */}
      {cancelRow && (
        <CancelDialog
          row={cancelRow}
          onConfirm={handleCancel}
          onClose={() => setCancelRow(null)}
        />
      )}

      {/* ── 토스트 ── */}
      {toast && <Toast msg={toast.msg} ok={toast.ok} onClose={() => setToast(null)} />}
    </div>
  );
}
