/**
 * SummaryPage v2 — Excel 다운로드 + 다크테마 + 30초 갱신
 * 배치: web/src/pages/SummaryPage.jsx
 */
import { useState, useEffect, useCallback } from 'react';

const BASE = '/api';
function fmt(v) {
  if (v == null) return '-';
  return typeof v === 'number' ? v.toLocaleString(undefined, { maximumFractionDigits: 3 }) : v;
}

function KpiCard({ label, value, unit, color = '#3b82f6', sub }) {
  return (
    <div style={{ flex:1, minWidth:130, padding:'14px 16px', borderRadius:10,
      background:'#1e293b', borderTop:`3px solid ${color}`, border:`1px solid #334155` }}>
      <div style={{ fontSize:11, color:'#94a3b8', marginBottom:4 }}>{label}</div>
      <div style={{ fontSize:20, fontWeight:700, color:'#f1f5f9' }}>
        {value}<span style={{ fontSize:12, color:'#64748b', marginLeft:4 }}>{unit}</span>
      </div>
      {sub && <div style={{ fontSize:11, color:'#64748b', marginTop:2 }}>{sub}</div>}
    </div>
  );
}

const STATUS_COLOR = {
  AVAILABLE:'#22c55e', RESERVED:'#f59e0b', PICKED:'#3b82f6',
  OUTBOUND:'#8b5cf6', SOLD:'#8b5cf6', DEPLETED:'#94a3b8',
};

export default function SummaryPage() {
  const [summary,    setSummary]    = useState(null);
  const [byProduct,  setByProduct]  = useState([]);
  const [movement,   setMovement]   = useState([]);
  const [loading,    setLoading]    = useState(false);
  const [lastUpdated,setLastUpdated]= useState(null);

  const load = useCallback(() => {
    setLoading(true);
    Promise.all([
      fetch(`${BASE}/dashboard/summary`).then(r=>r.json()).catch(()=>({})),
      fetch(`${BASE}/dashboard/by-product`).then(r=>r.json()).catch(()=>({})),
      fetch(`${BASE}/tabs/stock-movement?page_size=30`).then(r=>r.json()).catch(()=>({})),
    ]).then(([s, p, m]) => {
      setSummary(s); setByProduct(p?.rows||[]); setMovement(m?.rows||[]);
      setLastUpdated(new Date());
    }).finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { const t = setInterval(load, 30000); return () => clearInterval(t); }, [load]);

  const totals = summary?.totals || {};
  const items  = summary?.items  || [];
  const availMt = items.find(i=>i.status==='AVAILABLE')?.weight_mt || 0;
  const pickMt  = items.find(i=>i.status==='PICKED')?.weight_mt    || 0;

  return (
    <div style={{ padding:20, background:'#0f172a', minHeight:'100vh', color:'#f1f5f9' }}>
      {/* 헤더 */}
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:16 }}>
        <h2 style={{ fontSize:16, fontWeight:700, margin:0 }}>📊 Summary</h2>
        <div style={{ display:'flex', gap:8, alignItems:'center' }}>
          {lastUpdated && <span style={{ fontSize:11, color:'#64748b' }}>
            {lastUpdated.toLocaleTimeString('ko-KR')} · 30초
          </span>}
          {/* ★ Excel 다운로드 */}
          <button onClick={() => window.location.href='/api/tools/export-lot-list'}
            style={{ padding:'6px 14px', background:'#16a34a', color:'#fff', border:'none',
              borderRadius:7, fontSize:12, fontWeight:700, cursor:'pointer' }}>📥 Excel</button>
          <button onClick={load} disabled={loading} style={{ padding:'6px 12px', fontSize:12,
            borderRadius:7, border:'1px solid #334155', background:'#1e293b', color:'#94a3b8', cursor:'pointer' }}>
            {loading?'⏳':'🔄'}
          </button>
        </div>
      </div>

      {/* KPI 카드 */}
      <div style={{ display:'flex', gap:10, flexWrap:'wrap', marginBottom:20 }}>
        <KpiCard label="총 중량"  value={fmt(totals.weight_mt)} unit="MT" color="#0f172a" sub={`${totals.bag_count||0}톤백`} />
        <KpiCard label="가용"    value={fmt(availMt)}           unit="MT" color="#22c55e" />
        <KpiCard label="피킹중"  value={fmt(pickMt)}            unit="MT" color="#3b82f6" />
        <KpiCard label="총 LOT"  value={byProduct.reduce((s,r)=>s+(r.lot_count||0),0)} unit="개" color="#8b5cf6" />
      </div>

      {/* 상태 비율 바 */}
      {items.length > 0 && (() => {
        const total = items.reduce((s,i)=>s+(i.bag_count||0),0) || 1;
        return (
          <div style={{ marginBottom:20 }}>
            <div style={{ fontSize:12, color:'#64748b', marginBottom:6 }}>상태별 비율</div>
            <div style={{ display:'flex', height:24, borderRadius:6, overflow:'hidden', gap:1 }}>
              {items.filter(i=>i.bag_count>0).map((i,idx) => (
                <div key={idx} title={`${i.status}: ${i.bag_count}`}
                  style={{ flex:i.bag_count, background:STATUS_COLOR[i.status]||'#94a3b8', minWidth:i.bag_count>0?20:0,
                    display:'flex', alignItems:'center', justifyContent:'center',
                    fontSize:9, color:'#fff', fontWeight:700 }}>
                  {((i.bag_count/total)*100) > 10 ? i.status : ''}
                </div>
              ))}
            </div>
          </div>
        );
      })()}

      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:16 }}>
        {/* 제품별 */}
        <div style={{ background:'#1e293b', border:'1px solid #334155', borderRadius:10, padding:16 }}>
          <h3 style={{ fontSize:13, fontWeight:700, color:'#94a3b8', marginBottom:12 }}>📦 제품별 요약</h3>
          {byProduct.map((r,i) => (
            <div key={i} style={{ marginBottom:10 }}>
              <div style={{ display:'flex', justifyContent:'space-between', fontSize:12, marginBottom:4 }}>
                <span style={{ fontWeight:600 }}>{r.product_name}</span>
                <span style={{ color:'#22c55e', fontWeight:700 }}>{fmt(r.total_mt)} MT</span>
              </div>
              <div style={{ display:'flex', height:6, borderRadius:3, overflow:'hidden', background:'#334155' }}>
                {[{v:r.available_mt,c:'#22c55e'},{v:r.reserved_mt,c:'#f59e0b'},
                  {v:r.picked_mt,c:'#3b82f6'},{v:r.outbound_mt,c:'#8b5cf6'}].map((seg,j)=>(
                  <div key={j} style={{ flex:seg.v||0, background:seg.c, minWidth:0 }} />
                ))}
              </div>
            </div>
          ))}
        </div>

        {/* 최근 이동 */}
        <div style={{ background:'#1e293b', border:'1px solid #334155', borderRadius:10, padding:16 }}>
          <h3 style={{ fontSize:13, fontWeight:700, color:'#94a3b8', marginBottom:12 }}>🔄 최근 재고 이동</h3>
          <div style={{ maxHeight:240, overflowY:'auto' }}>
            {movement.length === 0
              ? <div style={{ color:'#475569', fontSize:12, textAlign:'center', padding:20 }}>이동 이력 없음</div>
              : movement.slice(0,20).map((m,i) => (
                <div key={i} style={{ display:'flex', justifyContent:'space-between',
                  padding:'5px 0', borderBottom:'1px solid #334155', fontSize:11 }}>
                  <div>
                    <span style={{ fontWeight:600, color:'#3b82f6' }}>{m.lot_no}</span>
                    <span style={{ color:'#64748b', marginLeft:6 }}>{m.movement_type}</span>
                  </div>
                  <span style={{ color:'#94a3b8', fontSize:10 }}>
                    {String(m.created_at||'').slice(5,16)}
                  </span>
                </div>
              ))
            }
          </div>
        </div>
      </div>
    </div>
  );
}
