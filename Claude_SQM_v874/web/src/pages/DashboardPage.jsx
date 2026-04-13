/**
 * DashboardPage v2 — con_return 경고 카드 + 30초 자동 갱신
 * 배치: web/src/pages/DashboardPage.jsx (기존 덮어쓰기)
 * 변경:
 *   ★ Q3-1: Con Return 경고 카드 (3일/7일 이내 LOT 표시)
 *   ★ Q3-2: 30초 자동 새로고침
 *   ★ Q3-3: KPI 요약 카드 (총 재고 / 가용 / 피킹중)
 */
import { useEffect, useMemo, useState, useCallback } from 'react';
import LotDetailModal from '../components/LotDetailModal';
import { getDashboardSummary, getDashboardByProduct } from '../api/dashboardApi';
import { getStatusPieData } from '../api/aiApi';

// ── 스타일 ────────────────────────────────────────────────────
const card = (bg = '#fff', border = '#e2e8f0') => ({
  padding: 16, borderRadius: 10, background: bg,
  border: `1px solid ${border}`, marginBottom: 16,
  boxShadow: '0 1px 3px rgba(15,23,42,0.06)',
});
const th  = { textAlign:'left', padding:'8px 10px', background:'#f8fafc', borderBottom:'2px solid #e2e8f0', fontSize:12, fontWeight:700 };
const td  = { padding:'6px 10px', borderBottom:'1px dashed rgba(51,65,85,0.3)', fontSize:12 };
const tdR = { ...td, textAlign:'right' };

const STATUS_COLORS = {
  AVAILABLE:'#22c55e', RESERVED:'#eab308', PICKED:'#3b82f6',
  OUTBOUND:'#ef4444', SOLD:'#ef4444', OTHER:'#94a3b8',
};

// ── 상태 바 ──────────────────────────────────────────────────
function StatusBar({ data }) {
  const total = (data||[]).reduce((s,d) => s+(d.count||0), 0);
  if (!data?.length || !total)
    return <div style={{ height:32, borderRadius:8, background:'#e2e8f0', marginBottom:16 }} />;
  return (
    <div style={{ display:'flex', height:32, borderRadius:8, overflow:'hidden',
      marginBottom:16, boxShadow:'inset 0 0 0 1px rgba(15,23,42,0.06)' }}>
      {data.map((d,i) => (
        <div key={i}
          title={`${d.label}: ${d.count} (${((d.count/total)*100).toFixed(1)}%)`}
          style={{ width:`${(d.count/total)*100}%`, background:STATUS_COLORS[d.label]||'#94a3b8', minWidth:d.count>0?2:0 }}
        />
      ))}
    </div>
  );
}

// ── KPI 카드 ─────────────────────────────────────────────────
function KpiCard({ label, value, unit, color, sub }) {
  return (
    <div style={{
      flex:1, minWidth:140, padding:'14px 16px', borderRadius:10,
      background:'#fff', border:'1px solid #e2e8f0',
      borderTop:`3px solid ${color}`,
      boxShadow:'0 1px 3px rgba(15,23,42,0.06)',
    }}>
      <div style={{ fontSize:11, color:'#94a3b8', marginBottom:4 }}>{label}</div>
      <div style={{ fontSize:22, fontWeight:700, color:'#0f172a' }}>
        {value}
        <span style={{ fontSize:12, color:'#94a3b8', marginLeft:4 }}>{unit}</span>
      </div>
      {sub && <div style={{ fontSize:11, color:'#64748b', marginTop:2 }}>{sub}</div>}
    </div>
  );
}

// ── ★ Con Return 경고 카드 ───────────────────────────────────
function ConReturnCard({ alerts, critCount, warnCount, onLotClick }) {
  const [expanded, setExpanded] = useState(false);

  if (!critCount && !warnCount) {
    return (
      <div style={{ ...card('#f0fdf4', '#86efac'), display:'flex', alignItems:'center', gap:8 }}>
        <span style={{ fontSize:18 }}>✅</span>
        <div>
          <div style={{ fontWeight:700, color:'#16a34a', fontSize:13 }}>Con Return 이상 없음</div>
          <div style={{ fontSize:11, color:'#4ade80' }}>7일 이내 반납 임박 컨테이너 없음</div>
        </div>
      </div>
    );
  }

  const bgColor    = critCount > 0 ? '#fef2f2' : '#fffbeb';
  const borderColor= critCount > 0 ? '#fca5a5' : '#fcd34d';
  const titleColor = critCount > 0 ? '#dc2626' : '#d97706';
  const icon       = critCount > 0 ? '🚨' : '⚠️';

  return (
    <div style={{ ...card(bgColor, borderColor) }}>
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:8 }}>
        <div style={{ display:'flex', alignItems:'center', gap:8 }}>
          <span style={{ fontSize:20 }}>{icon}</span>
          <div>
            <div style={{ fontWeight:700, color:titleColor, fontSize:14 }}>
              컨테이너 반납 임박
            </div>
            <div style={{ fontSize:11, color:'#64748b' }}>
              {critCount > 0 && <span style={{ color:'#dc2626', fontWeight:700 }}>🔴 3일 이내: {critCount}건  </span>}
              {warnCount > 0 && <span style={{ color:'#d97706' }}>🟡 7일 이내: {warnCount}건</span>}
            </div>
          </div>
        </div>
        <button
          onClick={() => setExpanded(e => !e)}
          style={{ padding:'4px 10px', fontSize:11, borderRadius:6, border:'1px solid #e5e7eb',
            background:'#fff', cursor:'pointer', color:'#475569' }}
        >
          {expanded ? '접기 ▲' : '상세 ▼'}
        </button>
      </div>

      {expanded && alerts?.length > 0 && (
        <div style={{ overflow:'auto', maxHeight:200 }}>
          <table style={{ width:'100%', borderCollapse:'collapse', fontSize:12 }}>
            <thead>
              <tr>
                {['LOT NO','반납기한','잔여일','컨테이너','창고'].map(h => (
                  <th key={h} style={{ ...th, background: critCount > 0 ? '#fee2e2' : '#fef3c7' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {alerts.map((a, i) => (
                <tr key={i} style={{ background: a.is_critical ? '#fef2f2' : '' }}>
                  <td
                    style={{ ...td, fontWeight:600, color:'#1e40af',
                      cursor:'pointer', textDecoration:'underline' }}
                    onClick={() => onLotClick && onLotClick(a.lot_no)}
                    title="클릭하면 LOT 상세 보기"
                  >{a.lot_no}</td>
                  <td style={{ ...td, textAlign:'center' }}>{a.con_return}</td>
                  <td style={{ ...td, textAlign:'center' }}>
                    <span style={{
                      fontWeight:700,
                      color: a.days_left <= 3 ? '#dc2626' : a.days_left <= 7 ? '#d97706' : '#64748b'
                    }}>
                      {a.days_left}일
                    </span>
                  </td>
                  <td style={{ ...td, fontSize:11, color:'#64748b' }}>{a.container_no || '-'}</td>
                  <td style={{ ...td, fontSize:11, color:'#64748b' }}>{a.warehouse || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function summaryToBarData(summary) {
  if (!summary?.items?.length) return [];
  return summary.items
    .filter(item => (item.bag_count || 0) > 0)
    .map(item => ({ label: item.status, count: item.bag_count }));
}

// ── 메인 DashboardPage ────────────────────────────────────────
export default function DashboardPage() {
  const [summary,    setSummary]    = useState(null);
  const [products,   setProducts]   = useState(null);
  const [pieData,    setPieData]    = useState(null);
  const [loading,    setLoading]    = useState(true);
  const [error,      setError]      = useState(null);
  const [lastUpdated,   setLastUpdated]   = useState(null);
  // ★ Q2: LOT 상세 모달
  const [lotDetailOpen, setLotDetailOpen] = useState(false);
  const [selectedLot,   setSelectedLot]   = useState(null);
  // ★ ALERTS 패널 상태
  const [alertsData,    setAlertsData]    = useState(null);

  const handleLotClick = useCallback((lotNo) => {
    setSelectedLot(lotNo);
    setLotDetailOpen(true);
  }, []);

  const barData = useMemo(() => {
    if (pieData?.data?.length) return pieData.data;
    return summaryToBarData(summary);
  }, [pieData, summary]);

  // ── 데이터 로드 ─────────────────────────────────────────────
  const load = useCallback(() => {
    const ctrl = new AbortController();
    setLoading(true);
    Promise.all([
      getDashboardSummary(),
      getDashboardByProduct(),
      getStatusPieData().catch(() => null), // optional: silently ignore if unavailable
    ])
      .then(([sum, prod, pie]) => {
        if (!ctrl.signal.aborted) {
          setSummary(sum);
          setProducts(prod);
          setPieData(pie);
          setLastUpdated(new Date());
        }
      })
      .catch(e => { if (e.name !== 'AbortError') setError(e.message); })
      .finally(() => setLoading(false));
    return () => ctrl.abort();
  }, []);

  useEffect(() => { return load(); }, [load]);

  // ★ Q3-2: 30초 자동 새로고침
  useEffect(() => {
    const t = setInterval(load, 30000);
    return () => clearInterval(t);
  }, [load]);

  // ★ ALERTS 데이터 로드 (마운트 + 30초 주기)
  const loadAlerts = useCallback(() => {
    fetch('/api/dashboard/alerts')
      .then(r => r.ok ? r.json() : null)
      .then(d => { if (d) setAlertsData(d); })
      .catch(() => {});
  }, []);
  useEffect(() => { loadAlerts(); }, [loadAlerts]);
  useEffect(() => {
    const t = setInterval(loadAlerts, 30000);
    return () => clearInterval(t);
  }, [loadAlerts]);

  // ── KPI 계산 ────────────────────────────────────────────────
  const kpis = useMemo(() => {
    if (!summary?.items) return null;
    const get = (s) => summary.items.find(i => i.status === s) || { weight_mt: 0, bag_count: 0 };
    return {
      total:    summary.totals,
      avail:    get('AVAILABLE'),
      reserved: get('RESERVED'),
      picked:   get('PICKED'),
    };
  }, [summary]);

  if (loading && !summary)
    return <div style={{ padding:32, color:'#64748b' }}>Loading dashboard...</div>;
  if (error)
    return <div style={{ padding:32, color:'red' }}>Error: {error}</div>;

  return (
    <div style={{ padding:24, maxWidth:1200 }}>

      {/* ── 헤더 ── */}
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:16 }}>
        <h2 style={{ fontSize:20, margin:0, color:'#0f172a', fontWeight:700 }}>Dashboard</h2>
        <div style={{ display:'flex', alignItems:'center', gap:12 }}>
          {lastUpdated && (
            <span style={{ fontSize:11, color:'#94a3b8' }}>
              갱신: {lastUpdated.toLocaleTimeString('ko-KR')}
            </span>
          )}
          <button onClick={load} disabled={loading} style={{
            padding:'5px 12px', fontSize:12, borderRadius:6,
            border:'1px solid #e2e8f0', background:'#fff',
            cursor:'pointer', color:'#475569',
          }}>
            {loading ? '⏳' : '🔄'} 새로고침
          </button>
        </div>
      </div>

      {/* ── 상태 바 ── */}
      <StatusBar data={barData} />

      {/* ★ Q3-1: KPI 카드 행 */}
      {kpis && (
        <div style={{ display:'flex', gap:12, flexWrap:'wrap', marginBottom:16 }}>
          <KpiCard label="총 재고"  value={kpis.total.weight_mt.toFixed(1)}    unit="MT" color="#0f172a" sub={`${kpis.total.bag_count.toLocaleString()}톤백`} />
          <KpiCard label="가용"     value={kpis.avail.weight_mt.toFixed(1)}    unit="MT" color="#22c55e" sub={`${kpis.avail.bag_count}톤백`} />
          <KpiCard label="예약"     value={kpis.reserved.weight_mt.toFixed(1)} unit="MT" color="#eab308" sub={`${kpis.reserved.bag_count}톤백`} />
          <KpiCard label="피킹 중"  value={kpis.picked.weight_mt.toFixed(1)}   unit="MT" color="#3b82f6" sub={`${kpis.picked.bag_count}톤백`} />
        </div>
      )}

      {/* ★ Q3-1: Con Return 경고 카드 */}
      {summary && (
        <ConReturnCard
          alerts={summary.con_return_alerts || []}
          critCount={summary.con_return_critical_count || 0}
          warnCount={summary.con_return_warning_count  || 0}
          onLotClick={handleLotClick}
        />
      )}

      {/* ── Status Summary 테이블 ── */}
      {summary && (
        <div style={card()}>
          <h3 style={{ fontSize:14, marginBottom:12, fontWeight:700, color:'#334155' }}>Status Summary</h3>
          <table style={{ width:'100%', borderCollapse:'collapse' }}>
            <thead>
              <tr>
                <th style={th}>Status</th>
                <th style={{ ...th, textAlign:'right' }}>Bags</th>
                <th style={{ ...th, textAlign:'right' }}>MT</th>
              </tr>
            </thead>
            <tbody>
              {summary.items.map(item => (
                <tr key={item.status}>
                  <td style={td}>
                    <span style={{ display:'inline-block', width:8, height:8, borderRadius:'50%',
                      background:STATUS_COLORS[item.status]||'#94a3b8', marginRight:6, verticalAlign:'middle' }} />
                    {item.status}
                  </td>
                  <td style={tdR}>{item.bag_count.toLocaleString()}</td>
                  <td style={tdR}>{item.weight_mt.toFixed(1)}</td>
                </tr>
              ))}
              <tr style={{ fontWeight:700 }}>
                <td style={td}>TOTAL</td>
                <td style={tdR}>{summary.totals.bag_count.toLocaleString()}</td>
                <td style={tdR}>{summary.totals.weight_mt.toFixed(1)}</td>
              </tr>
            </tbody>
          </table>
        </div>
      )}

      {/* ── By Product 테이블 ── */}
      {products && (
        <div style={card()}>
          <h3 style={{ fontSize:14, marginBottom:12, fontWeight:700, color:'#334155' }}>By Product</h3>
          <div style={{ overflow:'auto' }}>
            <table style={{ width:'100%', borderCollapse:'collapse' }}>
              <thead>
                <tr>
                  {['Product','LOTs','Bags','Available','Reserved','Picked','Outbound','Total MT'].map(h => (
                    <th key={h} style={{ ...th, textAlign: h==='Product' ? 'left' : 'right' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {products.rows.map(row => (
                  <tr key={row.product_name}>
                    <td style={td}><strong>{row.product_name}</strong></td>
                    <td style={tdR}>{row.lot_count}</td>
                    <td style={tdR}>{row.tonbag_count}</td>
                    <td style={{ ...tdR, color:'#22c55e', fontWeight:600 }}>{row.available_mt.toFixed(1)}</td>
                    <td style={{ ...tdR, color:'#eab308' }}>{row.reserved_mt.toFixed(1)}</td>
                    <td style={{ ...tdR, color:'#3b82f6' }}>{row.picked_mt.toFixed(1)}</td>
                    <td style={{ ...tdR, color:'#ef4444' }}>{row.outbound_mt.toFixed(1)}</td>
                    <td style={{ ...tdR, fontWeight:700 }}>{row.total_mt.toFixed(1)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* ★ ALERTS 패널 */}
      {alertsData && (
        <div style={{
          ...card('#0f172a', '#334155'),
          marginTop: 20,
          color: '#e2e8f0',
        }}>
          {/* 헤더 */}
          <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom:14 }}>
            <span style={{ fontSize:18 }}>⚠️</span>
            <h3 style={{ fontSize:15, fontWeight:700, color:'#f1f5f9', margin:0 }}>
              ALERTS 알림 및 경고
            </h3>
            {alertsData.total_count > 0 && (
              <span style={{
                background:'#dc2626', color:'#fff', fontSize:11, fontWeight:700,
                padding:'2px 8px', borderRadius:10, minWidth:20, textAlign:'center',
              }}>
                {alertsData.total_count}
              </span>
            )}
          </div>

          {/* 알림 목록 */}
          {alertsData.alerts.length === 0 ? (
            <div style={{ padding:'12px 0', fontSize:13, color:'#94a3b8' }}>
              현재 알림이 없습니다.
            </div>
          ) : (
            <div style={{ display:'flex', flexDirection:'column', gap:6 }}>
              {alertsData.alerts.map((a, i) => (
                <div key={i} style={{
                  display:'flex', alignItems:'center', gap:10,
                  padding:'8px 12px', borderRadius:8,
                  background: a.severity === 'error' ? 'rgba(248,113,113,0.10)' : 'rgba(251,191,36,0.10)',
                  borderLeft: `3px solid ${a.severity === 'error' ? '#f87171' : '#fbbf24'}`,
                }}>
                  <span style={{ fontSize:16 }}>{a.icon}</span>
                  <span style={{
                    fontSize:13,
                    color: a.severity === 'error' ? '#f87171' : '#fbbf24',
                    fontWeight: 600,
                  }}>
                    {a.message}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* KPI 풋터 */}
          {alertsData.kpi_footer && (
            <div style={{
              marginTop:14, paddingTop:12,
              borderTop:'1px solid #334155',
              fontSize:12, color:'#94a3b8',
              display:'flex', gap:8, flexWrap:'wrap',
            }}>
              <span>위치 미배정 <b style={{ color:'#fbbf24' }}>{alertsData.kpi_footer.unassigned_location_count}</b>개</span>
              <span style={{ color:'#475569' }}>│</span>
              <span>스캔 실패율 <b style={{ color:'#f87171' }}>{alertsData.kpi_footer.scan_failure_rate ?? '—'}</b></span>
              <span style={{ color:'#475569' }}>│</span>
              <span>LOT 평균 재고기간 <b style={{ color:'#38bdf8' }}>{alertsData.kpi_footer.avg_lot_age_days}</b>일</span>
            </div>
          )}
        </div>
      )}

      {/* ★ Q2: LOT 상세 모달 */}
      <LotDetailModal
        open={lotDetailOpen}
        onClose={() => { setLotDetailOpen(false); setSelectedLot(null); }}
        lotNo={selectedLot}
      />

      <p style={{ color:'#94a3b8', marginTop:8, fontSize:11 }}>
        Generated: {summary?.generated_at ?? products?.generated_at ?? '—'}
        {' '} · 30초 자동 갱신
      </p>
    </div>
  );
}
