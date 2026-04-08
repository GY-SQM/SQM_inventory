/**
 * MobileDashboard v2 — ★ 개선 #10: 바코드 스캔 버튼 추가
 * 배치: web/src/pages/MobileDashboard.jsx (덮어쓰기)
 */
import { useEffect, useState, useCallback, lazy, Suspense } from 'react';
import { api } from '../api/client';

// ★ 개선 #10: BarcodeScanner 지연 로딩
const BarcodeScanner = lazy(() => import('../components/BarcodeScanner'));

const STATUS_COLOR = {
  AVAILABLE: '#22c55e', RESERVED: '#f59e0b',
  PICKED: '#3b82f6',    OUTBOUND: '#8b5cf6',
  PARTIAL: '#f97316',   DEPLETED: '#94a3b8',
};
const STATUS_KO = {
  AVAILABLE:'가용', RESERVED:'예약', PICKED:'피킹',
  OUTBOUND:'출고완료', PARTIAL:'일부출고', DEPLETED:'소진',
};

function StatCard({ label, value, unit, color, sub }) {
  return (
    <div style={{
      background:'#1e293b', borderRadius:12, padding:'16px',
      borderLeft:`4px solid ${color||'#3b82f6'}`, flex:1, minWidth:140,
    }}>
      <div style={{fontSize:12,color:'#94a3b8',marginBottom:4}}>{label}</div>
      <div style={{fontSize:24,fontWeight:700,color:'#f1f5f9'}}>
        {value}<span style={{fontSize:13,color:'#94a3b8',marginLeft:4}}>{unit}</span>
      </div>
      {sub && <div style={{fontSize:11,color:'#64748b',marginTop:2}}>{sub}</div>}
    </div>
  );
}

function Badge({ status }) {
  return (
    <span style={{
      background:STATUS_COLOR[status]+'22', color:STATUS_COLOR[status]||'#94a3b8',
      border:`1px solid ${STATUS_COLOR[status]||'#94a3b8'}44`,
      borderRadius:6, padding:'2px 8px', fontSize:11, fontWeight:600,
    }}>{STATUS_KO[status]||status}</span>
  );
}

function Toast({ msg, ok, onClose }) {
  useEffect(()=>{ const t=setTimeout(onClose,3000); return ()=>clearTimeout(t); },[onClose]);
  return (
    <div style={{
      position:'fixed',bottom:80,left:'50%',transform:'translateX(-50%)',
      background:ok?'#16a34a':'#dc2626', color:'#fff',
      padding:'10px 20px', borderRadius:8, fontWeight:600,
      fontSize:14, zIndex:9999, boxShadow:'0 4px 12px rgba(0,0,0,0.4)',
    }}>{ok?'✅':'❌'} {msg}</div>
  );
}

function ConfirmDialog({ lotNo, onConfirm, onCancel }) {
  return (
    <div style={{
      position:'fixed',inset:0,background:'rgba(0,0,0,0.7)',
      display:'flex',alignItems:'center',justifyContent:'center',
      zIndex:9998, padding:16,
    }}>
      <div style={{background:'#1e293b',borderRadius:16,padding:24,width:'100%',maxWidth:320}}>
        <div style={{fontSize:18,fontWeight:700,color:'#f1f5f9',marginBottom:8}}>출고 확정</div>
        <div style={{color:'#94a3b8',marginBottom:20}}>
          <b style={{color:'#f59e0b'}}>{lotNo}</b> LOT를 출고 확정하시겠습니까?
          <br/><span style={{fontSize:12}}>⚠️ 이 작업은 되돌리기 어렵습니다.</span>
        </div>
        <div style={{display:'flex',gap:10}}>
          <button onClick={onCancel} style={{
            flex:1,padding:'12px',borderRadius:8,border:'none',
            background:'#334155',color:'#94a3b8',fontSize:15,cursor:'pointer',
          }}>취소</button>
          <button onClick={onConfirm} style={{
            flex:1,padding:'12px',borderRadius:8,border:'none',
            background:'#8b5cf6',color:'#fff',fontSize:15,fontWeight:700,cursor:'pointer',
          }}>확정</button>
        </div>
      </div>
    </div>
  );
}

export default function MobileDashboard() {
  const [summary,    setSummary]    = useState(null);
  const [waiting,    setWaiting]    = useState(null);
  const [lots,       setLots]       = useState([]);
  const [loading,    setLoading]    = useState(true);
  const [error,      setError]      = useState(null);
  const [toast,      setToast]      = useState(null);
  const [confirm,    setConfirm]    = useState(null);
  const [tab,        setTab]        = useState('home');
  const [filter,     setFilter]     = useState('ALL');
  const [refreshAt,  setRefreshAt]  = useState(Date.now());
  // ★ 개선 #10: 바코드 스캔 화면 상태
  const [showScanner, setShowScanner] = useState(false);

  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const [sumRes, invRes] = await Promise.all([
        api.get('/dashboard/summary'),
        api.get('/inventory/search?limit=50'),
      ]);
      setSummary(sumRes);
      const allLots = invRes?.items || invRes?.lots || [];
      setLots(allLots);
      setWaiting({
        reserved: allLots.filter(l=>l.status==='RESERVED').length,
        picked:   allLots.filter(l=>l.status==='PICKED').length,
      });
    } catch(e) { setError(e.message); }
    finally    { setLoading(false); }
  }, []);

  useEffect(()=>{ load(); },[load, refreshAt]);
  useEffect(()=>{ const t=setInterval(()=>setRefreshAt(Date.now()),30000); return()=>clearInterval(t); },[]);

  const handleConfirmOutbound = async (lotNo) => {
    setConfirm(null);
    try {
      const res = await api.post('/outbound/confirm', { lot_no: lotNo, force_all: false });
      if (res?.success) {
        setToast({ msg:`${lotNo} 출고 확정 완료`, ok:true });
        setRefreshAt(Date.now());
      } else {
        setToast({ msg:res?.message||'출고 확정 실패', ok:false });
      }
    } catch(e) { setToast({ msg:e.message, ok:false }); }
  };

  const filteredLots = filter==='ALL' ? lots : lots.filter(l=>l.status===filter);
  const availMt  = ((summary?.available_weight_kg||0)/1000).toFixed(2);
  const pickedMt = ((summary?.picked_weight_kg||0)/1000).toFixed(2);
  const totalLot = summary?.total_lots || lots.length;

  const S = {
    wrap:     { background:'#0f172a', minHeight:'100vh', color:'#f1f5f9',
                fontFamily:'-apple-system, BlinkMacSystemFont, sans-serif', paddingBottom:70 },
    header:   { background:'#1e293b', padding:'14px 16px', display:'flex',
                justifyContent:'space-between', alignItems:'center',
                position:'sticky', top:0, zIndex:100, borderBottom:'1px solid #334155' },
    section:  { padding:'16px 16px 0' },
    sTitle:   { fontSize:13, color:'#64748b', marginBottom:10, fontWeight:600 },
    lotRow:   { background:'#1e293b', borderRadius:10, padding:'12px 14px',
                marginBottom:8, display:'flex', justifyContent:'space-between', alignItems:'center' },
    tab: (a) => ({ flex:1, padding:'8px 0', textAlign:'center',
                   background:a?'#3b82f6':'transparent', color:a?'#fff':'#64748b',
                   border:'none', borderRadius:6, fontSize:13, fontWeight:a?700:400, cursor:'pointer' }),
    bottomNav:{ position:'fixed', bottom:0, left:0, right:0,
                background:'#1e293b', borderTop:'1px solid #334155',
                display:'flex', padding:'8px 16px', gap:8 },
  };

  // ★ 개선 #10: 바코드 스캐너 화면
  if (showScanner) {
    return (
      <Suspense fallback={<div style={{...S.wrap, display:'flex', alignItems:'center', justifyContent:'center', color:'#64748b'}}>⏳ 로딩 중...</div>}>
        <BarcodeScanner onClose={() => setShowScanner(false)} />
      </Suspense>
    );
  }

  if (loading && !summary) {
    return (
      <div style={{...S.wrap,display:'flex',alignItems:'center',justifyContent:'center'}}>
        <div style={{color:'#64748b',fontSize:16}}>⏳ 로딩 중...</div>
      </div>
    );
  }

  return (
    <div style={S.wrap}>
      {/* 헤더 */}
      <div style={S.header}>
        <div>
          <div style={{fontSize:16,fontWeight:700}}>📦 SQM 현장 관리</div>
          <div style={{fontSize:11,color:'#64748b'}}>
            {new Date().toLocaleString('ko-KR',{month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'})}
          </div>
        </div>
        <div style={{display:'flex',gap:8}}>
          {/* ★ 개선 #10: 바코드 스캔 버튼 */}
          <button onClick={()=>setShowScanner(true)} style={{
            background:'#1d4ed8',border:'none',borderRadius:8,
            color:'#fff',padding:'6px 12px',fontSize:13,cursor:'pointer',fontWeight:600,
          }}>📷 스캔</button>
          <button onClick={()=>setRefreshAt(Date.now())} style={{
            background:'#334155',border:'none',borderRadius:8,
            color:'#94a3b8',padding:'6px 12px',fontSize:13,cursor:'pointer',
          }}>{loading?'⏳':'🔄'}</button>
        </div>
      </div>

      {error && (
        <div style={{margin:16,padding:12,background:'#7f1d1d',borderRadius:8,fontSize:13}}>
          ❌ {error}
        </div>
      )}

      {/* 홈 탭 */}
      {tab==='home' && (
        <>
          <div style={S.section}>
            <div style={S.sTitle}>📊 재고 현황</div>
            <div style={{display:'flex',gap:10,flexWrap:'wrap'}}>
              <StatCard label="가용 재고" value={availMt} unit="MT" color="#22c55e" sub={`${totalLot}LOT`}/>
              <StatCard label="피킹 중"   value={pickedMt} unit="MT" color="#3b82f6" sub={`${waiting?.picked||0}건`}/>
            </div>
            <div style={{display:'flex',gap:10,marginTop:10,flexWrap:'wrap'}}>
              <StatCard label="예약 대기" value={waiting?.reserved||0} unit="건" color="#f59e0b"/>
              <StatCard label="총 LOT"   value={totalLot} unit="개" color="#8b5cf6"/>
            </div>
          </div>

          {/* ★ 개선 #10: 바코드 스캔 빠른 접근 카드 */}
          <div style={{...S.section, marginTop:16}}>
            <button onClick={()=>setShowScanner(true)} style={{
              width:'100%', padding:'16px', background:'#1e3a5f',
              border:'2px dashed #3b82f6', borderRadius:12,
              color:'#60a5fa', fontSize:15, fontWeight:700, cursor:'pointer',
              display:'flex', alignItems:'center', justifyContent:'center', gap:10,
            }}>
              📷 바코드 스캔으로 피킹/출고 처리
            </button>
          </div>

          {lots.filter(l=>l.status==='PICKED').length > 0 && (
            <div style={{...S.section, marginTop:16}}>
              <div style={S.sTitle}>🚨 출고 확정 대기 (PICKED)</div>
              {lots.filter(l=>l.status==='PICKED').slice(0,5).map(lot=>(
                <div key={lot.lot_no} style={S.lotRow}>
                  <div>
                    <div style={{fontSize:14,fontWeight:600}}>{lot.lot_no}</div>
                    <div style={{fontSize:11,color:'#64748b'}}>
                      {((lot.current_weight||0)/1000).toFixed(3)} MT
                    </div>
                  </div>
                  <button onClick={()=>setConfirm({lotNo:lot.lot_no})} style={{
                    background:'#8b5cf6',border:'none',borderRadius:8,
                    color:'#fff',padding:'8px 14px',fontSize:13,fontWeight:600,cursor:'pointer',
                  }}>확정</button>
                </div>
              ))}
            </div>
          )}

          {lots.filter(l=>l.status==='RESERVED').length > 0 && (
            <div style={{...S.section, marginTop:16}}>
              <div style={S.sTitle}>⏳ 예약 대기 (RESERVED)</div>
              {lots.filter(l=>l.status==='RESERVED').slice(0,3).map(lot=>(
                <div key={lot.lot_no} style={S.lotRow}>
                  <div>
                    <div style={{fontSize:14,fontWeight:600}}>{lot.lot_no}</div>
                    <div style={{fontSize:11,color:'#64748b'}}>
                      {((lot.current_weight||0)/1000).toFixed(3)} MT
                    </div>
                  </div>
                  <Badge status="RESERVED"/>
                </div>
              ))}
            </div>
          )}
        </>
      )}

      {/* LOT 목록 탭 */}
      {tab==='lots' && (
        <div style={S.section}>
          <div style={{display:'flex',gap:6,marginBottom:14,flexWrap:'wrap'}}>
            {['ALL','AVAILABLE','RESERVED','PICKED','PARTIAL','OUTBOUND'].map(s=>(
              <button key={s} onClick={()=>setFilter(s)} style={{
                padding:'5px 12px',borderRadius:20,border:'none',
                background:filter===s?(STATUS_COLOR[s]||'#3b82f6'):'#1e293b',
                color:filter===s?'#fff':'#64748b',
                fontSize:12,cursor:'pointer',fontWeight:filter===s?700:400,
              }}>{s==='ALL'?'전체':(STATUS_KO[s]||s)}</button>
            ))}
          </div>
          {filteredLots.length===0
            ? <div style={{color:'#475569',textAlign:'center',padding:40}}>해당 상태 LOT 없음</div>
            : filteredLots.slice(0,30).map(lot=>(
              <div key={lot.lot_no} style={S.lotRow}>
                <div style={{flex:1}}>
                  <div style={{fontSize:14,fontWeight:600}}>{lot.lot_no}</div>
                  <div style={{fontSize:11,color:'#64748b',marginTop:2}}>
                    {((lot.current_weight||0)/1000).toFixed(3)} MT
                    {lot.product_code && ` · ${lot.product_code}`}
                    {lot.con_return && ` | 반납:${lot.con_return}`}
                  </div>
                </div>
                <div style={{display:'flex',alignItems:'center',gap:8}}>
                  <Badge status={lot.status}/>
                  {lot.status==='PICKED' && (
                    <button onClick={()=>setConfirm({lotNo:lot.lot_no})} style={{
                      background:'#8b5cf6',border:'none',borderRadius:6,
                      color:'#fff',padding:'5px 10px',fontSize:12,cursor:'pointer',
                    }}>확정</button>
                  )}
                </div>
              </div>
            ))
          }
        </div>
      )}

      {/* 출고 이력 탭 */}
      {tab==='outbound' && (
        <div style={S.section}>
          <div style={S.sTitle}>📤 최근 출고</div>
          {lots.filter(l=>l.status==='OUTBOUND').length===0
            ? <div style={{color:'#475569',textAlign:'center',padding:40}}>출고 완료 LOT 없음</div>
            : lots.filter(l=>l.status==='OUTBOUND').slice(0,20).map(lot=>(
              <div key={lot.lot_no} style={S.lotRow}>
                <div>
                  <div style={{fontSize:14,fontWeight:600}}>{lot.lot_no}</div>
                  <div style={{fontSize:11,color:'#64748b'}}>{lot.sold_to||lot.customer||'-'}</div>
                </div>
                <Badge status="OUTBOUND"/>
              </div>
            ))
          }
        </div>
      )}

      {/* 하단 네비 */}
      <div style={S.bottomNav}>
        {[
          {id:'home',    icon:'🏠', label:'홈'},
          {id:'lots',    icon:'📋', label:'LOT목록'},
          {id:'outbound',icon:'📤', label:'출고이력'},
        ].map(({id,icon,label})=>(
          <button key={id} onClick={()=>setTab(id)} style={S.tab(tab===id)}>
            {icon}<br/><span style={{fontSize:10}}>{label}</span>
          </button>
        ))}
      </div>

      {confirm && (
        <ConfirmDialog
          lotNo={confirm.lotNo}
          onConfirm={()=>handleConfirmOutbound(confirm.lotNo)}
          onCancel={()=>setConfirm(null)}
        />
      )}
      {toast && <Toast msg={toast.msg} ok={toast.ok} onClose={()=>setToast(null)}/>}
    </div>
  );
}
