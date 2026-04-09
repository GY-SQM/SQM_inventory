/**
 * IntegrityPage v2 — 다크테마 + 자동 실행 + DB 최적화 버튼
 * 배치: web/src/pages/IntegrityPage.jsx
 */
import { useState, useEffect } from 'react';
import { api, fetchJson } from '../api/client';

const SEV = {
  ERROR:   { bg:'#7f1d1d22', fg:'#ef4444', border:'#ef444444' },
  WARNING: { bg:'#78350f22', fg:'#f59e0b', border:'#f59e0b44' },
  INFO:    { bg:'#1e3a5f22', fg:'#3b82f6', border:'#3b82f644' },
};

function Toast({ msg, ok, onClose }) {
  useEffect(() => { const t = setTimeout(onClose, 3500); return () => clearTimeout(t); }, [onClose]);
  return (
    <div style={{ position:'fixed', bottom:24, left:'50%', transform:'translateX(-50%)',
      background:ok?'#16a34a':'#dc2626', color:'#fff', padding:'12px 24px',
      borderRadius:10, fontWeight:700, fontSize:14, zIndex:9999 }}>
      {ok?'✅':'❌'} {msg}
    </div>
  );
}

export default function IntegrityPage() {
  const [result,       setResult]       = useState(null);
  const [repairResult, setRepairResult] = useState(null);
  const [loading,      setLoading]      = useState(false);
  const [repairing,    setRepairing]    = useState(false);
  const [optimizing,   setOptimizing]   = useState(false);
  const [showConfirm,  setShowConfirm]  = useState(false);
  const [toast,        setToast]        = useState(null);
  const [autoRan,      setAutoRan]      = useState(false);

  // ★ 페이지 진입 시 자동 검사 실행
  useEffect(() => {
    if (!autoRan) { setAutoRan(true); runCheck(); }
  }, []);

  const runCheck = async () => {
    setLoading(true); setRepairResult(null);
    try {
      const data = await fetchJson('/tools/integrity-check');
      setResult(data);
    } catch(e) {
      setResult({ success:false, total_issues:-1,
        issues:[{ type:'FETCH_ERROR', severity:'ERROR', message:e.message }] });
    } finally { setLoading(false); }
  };

  const runRepair = async () => {
    setShowConfirm(false); setRepairing(true);
    try {
      const res  = await fetch('/api/tools/integrity-repair', { method:'POST' });
      const data = await res.json();
      setRepairResult(data);
      if (data.success) {
        setToast({ msg:`복구 완료 — ${data.repaired_count}건 수정`, ok:true });
        runCheck();
      } else {
        setToast({ msg:'복구 실패', ok:false });
      }
    } catch(e) {
      setRepairResult({ success:false, repaired_count:0, details:[], error:e.message });
      setToast({ msg:e.message, ok:false });
    } finally { setRepairing(false); }
  };

  // ★ DB 최적화 실행
  const runOptimize = async () => {
    setOptimizing(true);
    try {
      const res = await api.post('/tools/db-optimize', {});
      setToast({ msg: res?.message || 'DB 최적화 완료', ok: true });
    } catch(e) {
      setToast({ msg: e.message, ok: false });
    } finally { setOptimizing(false); }
  };

  const issueCount = result?.total_issues || 0;
  const statusColor = issueCount === 0 ? '#22c55e' : issueCount > 5 ? '#ef4444' : '#f59e0b';

  return (
    <div style={{ padding:20, background:'#0f172a', minHeight:'100vh', color:'#f1f5f9' }}>
      {/* 헤더 */}
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:16 }}>
        <div>
          <h2 style={{ fontSize:16, fontWeight:700, margin:0 }}>🔧 DB 정합성 검사</h2>
          <p style={{ fontSize:11, color:'#64748b', margin:'4px 0 0' }}>
            재고 데이터 정합성 검사 · 자동 복구 · DB 최적화
          </p>
        </div>
        {/* 상태 표시 */}
        {result && (
          <div style={{ padding:'8px 16px', borderRadius:8, border:`1px solid ${statusColor}44`,
            background:statusColor+'11', color:statusColor, fontWeight:700, fontSize:13 }}>
            {issueCount === 0 ? '✅ 이상 없음' : `⚠️ ${issueCount}건 이슈`}
          </div>
        )}
      </div>

      {/* 버튼 영역 */}
      <div style={{ display:'flex', gap:10, marginBottom:20, flexWrap:'wrap' }}>
        <button onClick={runCheck} disabled={loading} style={{
          padding:'9px 20px', fontWeight:700, fontSize:13,
          background:'#3b82f6', color:'#fff', border:'none', borderRadius:8,
          cursor:loading?'not-allowed':'pointer', opacity:loading?0.6:1,
        }}>{loading ? '⏳ 검사 중...' : '🔍 정합성 검사'}</button>

        <button onClick={() => setShowConfirm(true)} disabled={repairing} style={{
          padding:'9px 20px', fontWeight:700, fontSize:13,
          background:'#ef4444', color:'#fff', border:'none', borderRadius:8,
          cursor:repairing?'not-allowed':'pointer', opacity:repairing?0.6:1,
        }}>{repairing ? '⏳ 복구 중...' : '🛠️ 자동 복구'}</button>

        {/* ★ DB 최적화 버튼 */}
        <button onClick={runOptimize} disabled={optimizing} style={{
          padding:'9px 20px', fontWeight:700, fontSize:13,
          background:'#8b5cf6', color:'#fff', border:'none', borderRadius:8,
          cursor:optimizing?'not-allowed':'pointer', opacity:optimizing?0.6:1,
        }}>{optimizing ? '⏳ 최적화 중...' : '⚡ DB 최적화'}</button>
      </div>

      {/* 복구 확인 모달 */}
      {showConfirm && (
        <div style={{ position:'fixed', inset:0, background:'rgba(0,0,0,0.7)',
          display:'flex', alignItems:'center', justifyContent:'center', zIndex:9999 }}>
          <div style={{ background:'#1e293b', border:'1px solid #475569', borderRadius:12, padding:28, maxWidth:420, width:'90%' }}>
            <h3 style={{ color:'#ef4444', marginBottom:12 }}>⚠️ 복구 실행 확인</h3>
            <p style={{ fontSize:13, color:'#cbd5e1', marginBottom:8 }}>
              정합성 자동 복구를 실행하시겠습니까?
            </p>
            <p style={{ fontSize:12, color:'#fbbf24', marginBottom:20 }}>
              💾 inventory.status를 tonbag 다수결로 동기화합니다.<br/>
              복구 전 백업을 권장합니다.
            </p>
            <div style={{ display:'flex', gap:10 }}>
              <button onClick={() => setShowConfirm(false)} style={{
                flex:1, padding:'9px', background:'#334155', color:'#94a3b8',
                border:'none', borderRadius:8, cursor:'pointer' }}>취소</button>
              <button onClick={runRepair} style={{
                flex:1, padding:'9px', background:'#ef4444', color:'#fff',
                border:'none', borderRadius:8, cursor:'pointer', fontWeight:700 }}>복구 실행</button>
            </div>
          </div>
        </div>
      )}

      {/* 복구 결과 */}
      {repairResult && (
        <div style={{ padding:'12px 16px', borderRadius:8, marginBottom:16,
          background: repairResult.success ? '#14532d22' : '#7f1d1d22',
          border:`1px solid ${repairResult.success?'#22c55e44':'#ef444444'}` }}>
          <div style={{ fontWeight:700, fontSize:13, color:repairResult.success?'#22c55e':'#ef4444', marginBottom:6 }}>
            {repairResult.success ? `✅ 복구 완료 — ${repairResult.repaired_count}건 수정` : `❌ 복구 실패: ${repairResult.error||''}`}
          </div>
          {repairResult.details?.slice(0,10).map((d,i) => (
            <div key={i} style={{ fontSize:11, color:'#94a3b8' }}>
              {d.lot_no}: {d.old} → <span style={{ color:'#22c55e' }}>{d.new}</span>
            </div>
          ))}
        </div>
      )}

      {/* 검사 결과 */}
      {result && (
        <>
          <div style={{ padding:12, borderRadius:8, marginBottom:16,
            background: issueCount===0 ? '#14532d22' : '#7f1d1d22',
            border:`1px solid ${issueCount===0?'#22c55e44':'#ef444444'}`,
            fontSize:14, fontWeight:700, color:issueCount===0?'#22c55e':'#ef4444' }}>
            {issueCount===0 ? '✅ All Clear — 이슈 없음' : `⚠️ ${issueCount}건 이슈 발견`}
          </div>

          {result.issues?.length > 0 && (
            <div style={{ display:'flex', flexDirection:'column', gap:8 }}>
              {result.issues.map((issue, i) => {
                const c = SEV[issue.severity] || SEV.INFO;
                return (
                  <div key={i} style={{ padding:'10px 14px', borderRadius:8,
                    background:c.bg, border:`1px solid ${c.border}` }}>
                    <div style={{ display:'flex', gap:8, alignItems:'center', marginBottom:4 }}>
                      <span style={{ fontSize:10, fontWeight:700, padding:'2px 6px', borderRadius:4,
                        background:c.fg, color:'#fff' }}>{issue.severity}</span>
                      <span style={{ fontSize:11, fontWeight:600, color:'#94a3b8' }}>{issue.type}</span>
                    </div>
                    <div style={{ fontSize:12, color:c.fg }}>{issue.message}</div>
                    {issue.details && (
                      <div style={{ fontSize:11, color:'#64748b', marginTop:4 }}>
                        {issue.details.slice(0,10).join(', ')}
                        {issue.details.length>10?` ... (+${issue.details.length-10})`:''}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
          {result.generated_at && (
            <div style={{ marginTop:8, fontSize:10, color:'#475569', textAlign:'right' }}>
              검사 시각: {result.generated_at}
            </div>
          )}
        </>
      )}

      {toast && <Toast msg={toast.msg} ok={toast.ok} onClose={() => setToast(null)} />}
    </div>
  );
}
