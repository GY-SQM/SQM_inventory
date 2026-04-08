/**
 * CargoOverviewPage v2 — 다크테마 + KPI + 30초 갱신
 * 배치: web/src/pages/CargoOverviewPage.jsx
 */
import { useState, useEffect, useCallback } from 'react';
import { fetchJson } from '../api/client';

function KpiCard({ label, value, unit='', color='#3b82f6', sub }) {
  return (
    <div style={{ flex:1, minWidth:140, padding:'14px 16px', borderRadius:10,
      background:'#1e293b', borderTop:`3px solid ${color}`, border:`1px solid #334155` }}>
      <div style={{ fontSize:11, color:'#94a3b8', marginBottom:4 }}>{label}</div>
      <div style={{ fontSize:22, fontWeight:700, color:'#f1f5f9' }}>
        {value ?? '-'}<span style={{ fontSize:12, color:'#64748b', marginLeft:4 }}>{unit}</span>
      </div>
      {sub && <div style={{ fontSize:11, color:'#64748b', marginTop:2 }}>{sub}</div>}
    </div>
  );
}

const STATUS_COLOR = { AVAILABLE:'#22c55e', RESERVED:'#f59e0b', PICKED:'#3b82f6',
  OUTBOUND:'#8b5cf6', DEPLETED:'#94a3b8' };

export default function CargoOverviewPage() {
  const [data,        setData]        = useState(null);
  const [loading,     setLoading]     = useState(true);
  const [error,       setError]       = useState('');
  const [lastUpdated, setLastUpdated] = useState(null);

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([
      fetchJson('/dashboard/summary'),
      fetchJson('/dashboard/by-product'),
      fetchJson('/dashboard/location-summary'),
    ]).then(([summary, byProduct, locationSummary]) => {
      setData({ summary, byProduct, locationSummary });
      setLastUpdated(new Date());
    }).catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { const t = setInterval(load, 30000); return () => clearInterval(t); }, [load]);

  if (loading && !data) return <div style={{ padding:32, color:'#64748b' }}>Loading...</div>;
  if (error)            return <div style={{ padding:32, color:'#dc2626' }}>{error}</div>;
  if (!data)            return null;

  const s = data.summary;
  const totals = s?.totals || {};
  const items  = s?.items  || [];

  const availMt = items.find(i=>i.status==='AVAILABLE')?.weight_mt || 0;
  const pickMt  = items.find(i=>i.status==='PICKED')?.weight_mt || 0;
  const resvMt  = items.find(i=>i.status==='RESERVED')?.weight_mt || 0;

  return (
    <div style={{ padding:20, background:'#0f172a', minHeight:'100vh', color:'#f1f5f9' }}>
      {/* 헤더 */}
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:20 }}>
        <h2 style={{ fontSize:18, fontWeight:700, margin:0 }}>🚢 Cargo Overview</h2>
        <div style={{ display:'flex', gap:10, alignItems:'center' }}>
          {lastUpdated && <span style={{ fontSize:11, color:'#64748b' }}>
            {lastUpdated.toLocaleTimeString('ko-KR')} · 30초 갱신
          </span>}
          <button onClick={load} style={{ padding:'5px 12px', fontSize:12, borderRadius:6,
            border:'1px solid #334155', background:'#1e293b', color:'#94a3b8', cursor:'pointer' }}>
            {loading?'⏳':'🔄'}
          </button>
        </div>
      </div>

      {/* KPI 카드 */}
      <div style={{ display:'flex', gap:12, flexWrap:'wrap', marginBottom:20 }}>
        <KpiCard label="총 중량" value={totals.weight_mt?.toFixed(1)} unit="MT" color="#0f172a" sub={`${totals.bag_count?.toLocaleString()||0}톤백`} />
        <KpiCard label="가용" value={availMt.toFixed(1)} unit="MT" color="#22c55e" />
        <KpiCard label="예약" value={resvMt.toFixed(1)} unit="MT" color="#f59e0b" />
        <KpiCard label="피킹" value={pickMt.toFixed(1)} unit="MT" color="#3b82f6" />
      </div>

      {/* 상태 비율 바 */}
      {items.length > 0 && (() => {
        const total = items.reduce((s,i) => s+(i.bag_count||0), 0) || 1;
        return (
          <div style={{ marginBottom:20 }}>
            <div style={{ fontSize:12, color:'#64748b', marginBottom:6 }}>상태별 비율 (톤백 기준)</div>
            <div style={{ display:'flex', height:28, borderRadius:8, overflow:'hidden', gap:1 }}>
              {items.filter(i=>i.bag_count>0).map((i,idx) => (
                <div key={idx}
                  title={`${i.status}: ${i.bag_count}개 (${((i.bag_count/total)*100).toFixed(1)}%)`}
                  style={{ flex:i.bag_count, background:STATUS_COLOR[i.status]||'#94a3b8',
                    display:'flex', alignItems:'center', justifyContent:'center',
                    fontSize:10, color:'#fff', fontWeight:700, minWidth:i.bag_count>0?30:0 }}>
                  {((i.bag_count/total)*100) > 8 ? `${i.status}` : ''}
                </div>
              ))}
            </div>
          </div>
        );
      })()}

      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:16 }}>
        {/* 위치별 현황 */}
        {data.locationSummary?.rows?.length > 0 && (
          <div style={{ background:'#1e293b', border:'1px solid #334155', borderRadius:10, padding:16 }}>
            <h3 style={{ fontSize:14, fontWeight:700, marginBottom:12, color:'#94a3b8' }}>📍 위치별 현황</h3>
            <div style={{ maxHeight:280, overflowY:'auto' }}>
              {data.locationSummary.rows.map((r, i) => (
                <div key={i} style={{ display:'flex', justifyContent:'space-between',
                  padding:'6px 0', borderBottom:'1px solid #334155', fontSize:12 }}>
                  <span style={{ color:'#f1f5f9' }}>{r.location||'(미지정)'}</span>
                  <span style={{ color:'#3b82f6', fontWeight:600 }}>{r.bag_count}개</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* 제품별 현황 */}
        {data.byProduct?.rows?.length > 0 && (
          <div style={{ background:'#1e293b', border:'1px solid #334155', borderRadius:10, padding:16 }}>
            <h3 style={{ fontSize:14, fontWeight:700, marginBottom:12, color:'#94a3b8' }}>📦 제품별 현황</h3>
            <div style={{ maxHeight:280, overflowY:'auto' }}>
              {data.byProduct.rows.map((r, i) => (
                <div key={i} style={{ marginBottom:10 }}>
                  <div style={{ display:'flex', justifyContent:'space-between', fontSize:12, marginBottom:4 }}>
                    <span style={{ fontWeight:600, color:'#f1f5f9' }}>{r.product_name}</span>
                    <span style={{ color:'#22c55e', fontWeight:700 }}>{r.total_mt?.toFixed(1)} MT</span>
                  </div>
                  <div style={{ display:'flex', height:8, borderRadius:4, overflow:'hidden', background:'#334155' }}>
                    {[
                      {v:r.available_mt, c:'#22c55e'},
                      {v:r.reserved_mt, c:'#f59e0b'},
                      {v:r.picked_mt, c:'#3b82f6'},
                      {v:r.outbound_mt, c:'#8b5cf6'},
                    ].map((seg,j) => (
                      <div key={j} style={{ flex:seg.v||0, background:seg.c, minWidth:0 }} />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
