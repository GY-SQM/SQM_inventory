/**
 * IntegrityPage v3 — P1-S5: 카드형 요약 + 타입별 그룹핑
 * 배치: web/src/pages/IntegrityPage.jsx (기존 덮어쓰기)
 *
 * 변경사항:
 *   1. 상단 3개 검증 카드 (Orphan / Status / Weight) ✅/❌ 표시
 *   2. 이슈 타입별 그룹핑 + 접기/펼치기
 *   3. 문제 LOT 클릭 → LotDetailModal 연결용 콜백
 *   4. 기존 기능 100% 유지 (자동검사, 복구, DB최적화)
 */
import { useState, useEffect } from 'react';
import { api, fetchJson } from '../api/client';

const SEV = {
  ERROR:   { bg:'#7f1d1d22', fg:'#ef4444', border:'#ef444444', icon:'❌' },
  WARNING: { bg:'#78350f22', fg:'#f59e0b', border:'#f59e0b44', icon:'⚠️' },
  INFO:    { bg:'#1e3a5f22', fg:'#3b82f6', border:'#3b82f644', icon:'ℹ️' },
};

const CHECK_CARDS = [
  { type: 'ORPHAN_TONBAG', label: '고아 톤백',     desc: 'inventory에 없는 LOT의 톤백', icon: '👻' },
  { type: 'STATUS_MISMATCH', label: '상태 불일치', desc: 'LOT vs 톤백 상태 불일치',     icon: '🔀' },
  { type: 'WEIGHT_MISMATCH', label: '중량 불일치', desc: '기록 중량 ≠ 계산 중량',       icon: '⚖️' },
];

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

export default function IntegrityPage({ onSelectLot }) {
  const [result,       setResult]       = useState(null);
  const [repairResult, setRepairResult] = useState(null);
  const [loading,      setLoading]      = useState(false);
  const [repairing,    setRepairing]    = useState(false);
  const [optimizing,   setOptimizing]   = useState(false);
  const [showConfirm,  setShowConfirm]  = useState(false);
  const [toast,        setToast]        = useState(null);
  const [autoRan,      setAutoRan]      = useState(false);
  const [expandedType, setExpandedType] = useState(null);

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

  const runOptimize = async () => {
    setOptimizing(true);
    try {
      const res = await api.post('/tools/db-optimize', {});
      setToast({ msg: res?.message || 'DB 최적화 완료', ok: true });
    } catch(e) {
      setToast({ msg: e.message, ok: false });
    } finally { setOptimizing(false); }
  };

  // 이슈를 타입별로 그룹핑
  const issuesByType = {};
  (result?.issues || []).forEach(issue => {
    if (!issuesByType[issue.type]) issuesByType[issue.type] = [];
    issuesByType[issue.type].push(issue);
  });

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

        <button onClick={() => setShowConfirm(true)} disabled={repairing || issueCount === 0} style={{
          padding:'9px 20px', fontWeight:700, fontSize:13,
          background:'#ef4444', color:'#fff', border:'none', borderRadius:8,
          cursor:(repairing||issueCount===0)?'not-allowed':'pointer',
          opacity:(repairing||issueCount===0)?0.5:1,
        }}>{repairing ? '⏳ 복구 중...' : '🛠️ 자동 복구'}</button>

        <button onClick={runOptimize} disabled={optimizing} style={{
          padding:'9px 20px', fontWeight:700, fontSize:13,
          background:'#8b5cf6', color:'#fff', border:'none', borderRadius:8,
          cursor:optimizing?'not-allowed':'pointer', opacity:optimizing?0.6:1,
        }}>{optimizing ? '⏳ 최적화 중...' : '⚡ DB 최적화'}</button>
      </div>

      {/* ★ 검증 카드 3개 */}
      {result && (
        <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fit, minmax(200px, 1fr))', gap:12, marginBottom:20 }}>
          {CHECK_CARDS.map(card => {
            const issues = issuesByType[card.type] || [];
            const ok = issues.length === 0;
            return (
              <div key={card.type} style={{
                padding:16, borderRadius:10,
                background: ok ? '#14532d18' : '#7f1d1d18',
                border: `1px solid ${ok ? '#22c55e44' : '#ef444444'}`,
                cursor: issues.length > 0 ? 'pointer' : 'default',
              }}
              onClick={() => issues.length > 0 && setExpandedType(expandedType === card.type ? null : card.type)}>
                <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:8 }}>
                  <span style={{ fontSize:24 }}>{card.icon}</span>
                  <span style={{ fontSize:28, fontWeight:800, color: ok ? '#22c55e' : '#ef4444' }}>
                    {ok ? '✅' : issues.length}
                  </span>
                </div>
                <div style={{ fontSize:13, fontWeight:700, color: ok ? '#22c55e' : '#f1f5f9' }}>{card.label}</div>
                <div style={{ fontSize:10, color:'#64748b', marginTop:2 }}>{card.desc}</div>
                {issues.length > 0 && (
                  <div style={{ fontSize:10, color:'#94a3b8', marginTop:6 }}>
                    {expandedType === card.type ? '▲ 접기' : '▼ 상세 보기'}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

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

      {/* ★ 확장된 이슈 상세 */}
      {expandedType && issuesByType[expandedType]?.length > 0 && (
        <div style={{ marginBottom:16 }}>
          <h4 style={{ fontSize:13, fontWeight:700, color:'#f59e0b', marginBottom:8 }}>
            {CHECK_CARDS.find(c => c.type === expandedType)?.icon} {expandedType} 상세 ({issuesByType[expandedType].length}건)
          </h4>
          <div style={{ display:'flex', flexDirection:'column', gap:6 }}>
            {issuesByType[expandedType].map((issue, i) => {
              const c = SEV[issue.severity] || SEV.INFO;
              // 메시지에서 LOT 번호 추출
              const lotMatch = issue.message?.match(/LOT\s+(\d{8,11})/);
              return (
                <div key={i} style={{ padding:'10px 14px', borderRadius:8,
                  background:c.bg, border:`1px solid ${c.border}` }}>
                  <div style={{ display:'flex', gap:8, alignItems:'center', marginBottom:4 }}>
                    <span style={{ fontSize:10, fontWeight:700, padding:'2px 6px', borderRadius:4,
                      background:c.fg, color:'#fff' }}>{issue.severity}</span>
                    {lotMatch && onSelectLot && (
                      <button onClick={() => onSelectLot(lotMatch[1])} style={{
                        padding:'1px 8px', fontSize:10, background:'#3b82f622', color:'#3b82f6',
                        border:'1px solid #3b82f644', borderRadius:4, cursor:'pointer', fontWeight:600,
                      }}>{lotMatch[1]} 상세 →</button>
                    )}
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
        </div>
      )}

      {/* 기타 이슈 (카드에 포함되지 않은 타입) */}
      {result && Object.entries(issuesByType)
        .filter(([type]) => !CHECK_CARDS.some(c => c.type === type) && type !== expandedType)
        .map(([type, issues]) => (
          <div key={type} style={{ marginBottom:12 }}>
            {issues.map((issue, i) => {
              const c = SEV[issue.severity] || SEV.INFO;
              return (
                <div key={i} style={{ padding:'10px 14px', borderRadius:8, marginBottom:6,
                  background:c.bg, border:`1px solid ${c.border}` }}>
                  <div style={{ display:'flex', gap:8, alignItems:'center', marginBottom:4 }}>
                    <span style={{ fontSize:10, fontWeight:700, padding:'2px 6px', borderRadius:4,
                      background:c.fg, color:'#fff' }}>{issue.severity}</span>
                    <span style={{ fontSize:11, fontWeight:600, color:'#94a3b8' }}>{issue.type}</span>
                  </div>
                  <div style={{ fontSize:12, color:c.fg }}>{issue.message}</div>
                </div>
              );
            })}
          </div>
        ))
      }

      {result?.generated_at && (
        <div style={{ marginTop:8, fontSize:10, color:'#475569', textAlign:'right' }}>
          검사 시각: {result.generated_at}
        </div>
      )}

      {toast && <Toast msg={toast.msg} ok={toast.ok} onClose={() => setToast(null)} />}
    </div>
  );
}
