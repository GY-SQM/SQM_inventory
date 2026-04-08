import { useState, useEffect } from 'react';

const BASE = '/api';

const cardStyle = {
  background: '#1e293b', border: '1px solid #334155',
  borderRadius: 8, padding: '16px 20px', marginBottom: 14,
};
const titleStyle = { fontSize: 13, fontWeight: 700, color: '#94a3b8', marginBottom: 12 };

function fmt(v) {
  const n = Number(v || 0);
  return n ? n.toLocaleString(undefined, { maximumFractionDigits: 1 }) : '0';
}

// ── KPI 카드 ─────────────────────────────────────────────────────────────────
function KpiCard({ label, value, unit, color, sub }) {
  return (
    <div style={{
      background: '#0f172a', border: `1px solid ${color}33`,
      borderLeft: `4px solid ${color}`, borderRadius: 8,
      padding: '14px 18px', flex: 1, minWidth: 140,
    }}>
      <div style={{ fontSize: 11, color: '#64748b', marginBottom: 6 }}>{label}</div>
      <div style={{ fontSize: 22, fontWeight: 700, color }}>{value}</div>
      <div style={{ fontSize: 11, color: '#475569', marginTop: 4 }}>{unit}{sub ? ` · ${sub}` : ''}</div>
    </div>
  );
}

// ── 간단 바 차트 (SVG) ────────────────────────────────────────────────────────
function BarChart({ data, color = '#38bdf8', height = 120 }) {
  if (!data || data.length === 0) return <div style={{ color: '#475569', fontSize: 12, padding: 16, textAlign: 'center' }}>데이터 없음</div>;
  const max = Math.max(...data.map(d => d.value), 1);
  const barW = Math.max(8, Math.floor(560 / data.length) - 4);
  return (
    <svg width="100%" height={height + 30} viewBox={`0 0 ${data.length * (barW + 4)} ${height + 30}`} style={{ overflow: 'visible' }}>
      {data.map((d, i) => {
        const barH = Math.max(2, Math.round((d.value / max) * height));
        const x = i * (barW + 4);
        const y = height - barH;
        return (
          <g key={i}>
            <rect x={x} y={y} width={barW} height={barH} fill={color} rx={2} opacity={0.85} />
            <title>{`${d.label}: ${fmt(d.value)}`}</title>
            {data.length <= 20 && (
              <text x={x + barW / 2} y={height + 14} textAnchor="middle" fontSize={9} fill="#475569">
                {(d.label || '').slice(5)}
              </text>
            )}
          </g>
        );
      })}
    </svg>
  );
}

// ── 상태별 집계 테이블 ────────────────────────────────────────────────────────
function StatusSummary({ data }) {
  const STATUS_COLORS = {
    AVAILABLE: '#4ade80', RESERVED: '#facc15', PICKED: '#a78bfa',
    OUTBOUND:  '#38bdf8', RETURN:   '#f87171', DEPLETED: '#94a3b8',
  };
  return (
    <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
      {(data || []).map(row => (
        <div key={row.status} style={{
          background: '#0f172a', borderRadius: 8, padding: '12px 18px',
          border: `1px solid ${(STATUS_COLORS[row.status] || '#334155')}33`,
          borderLeft: `4px solid ${STATUS_COLORS[row.status] || '#334155'}`,
          minWidth: 160,
        }}>
          <div style={{ fontSize: 11, color: '#64748b', marginBottom: 4 }}>{row.status}</div>
          <div style={{ fontSize: 18, fontWeight: 700, color: STATUS_COLORS[row.status] || '#f1f5f9' }}>
            {fmt(row.bags)}개
          </div>
          <div style={{ fontSize: 11, color: '#475569', marginTop: 3 }}>
            {fmt(row.total_kg)} kg
          </div>
        </div>
      ))}
    </div>
  );
}

// ── 제품별 현황 테이블 ────────────────────────────────────────────────────────
function ProductTable({ data }) {
  const thS = { padding: '6px 10px', fontSize: 11, fontWeight: 700, color: '#64748b', textAlign: 'left', borderBottom: '1px solid #334155', background: '#0f172a' };
  const tdS = { padding: '5px 10px', fontSize: 12, borderBottom: '1px solid #1e293b', color: '#e2e8f0' };
  return (
    <div style={{ overflow: 'auto', maxHeight: 280 }}>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr>
            <th style={thS}>제품명</th>
            <th style={{ ...thS, textAlign: 'center' }}>AVAILABLE</th>
            <th style={{ ...thS, textAlign: 'center' }}>RESERVED</th>
            <th style={{ ...thS, textAlign: 'center' }}>PICKED</th>
            <th style={{ ...thS, textAlign: 'right' }}>총 중량(kg)</th>
          </tr>
        </thead>
        <tbody>
          {(data || []).map((r, i) => (
            <tr key={i}
              onMouseEnter={e => e.currentTarget.style.background = '#1e293b'}
              onMouseLeave={e => e.currentTarget.style.background = ''}>
              <td style={{ ...tdS, fontWeight: 600, color: '#38bdf8' }}>{r.product || '-'}</td>
              <td style={{ ...tdS, textAlign: 'center', color: '#4ade80' }}>{fmt(r.available_kg)}</td>
              <td style={{ ...tdS, textAlign: 'center', color: '#facc15' }}>{fmt(r.reserved_kg)}</td>
              <td style={{ ...tdS, textAlign: 'center', color: '#a78bfa' }}>{fmt(r.picked_kg)}</td>
              <td style={{ ...tdS, textAlign: 'right', color: '#94a3b8', fontWeight: 600 }}>{fmt(r.total_kg)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function SummaryPage() {
  const [summary,   setSummary]   = useState(null);
  const [byProduct, setByProduct] = useState([]);
  const [movement,  setMovement]  = useState([]);
  const [loading,   setLoading]   = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      // 대시보드 요약
      const [sumRes, prodRes, mvRes] = await Promise.all([
        fetch(`${BASE}/dashboard/summary`).then(r => r.json()).catch(() => ({})),
        fetch(`${BASE}/dashboard/by-product`).then(r => r.json()).catch(() => ({})),
        fetch(`${BASE}/tabs/stock-movement?page_size=30`).then(r => r.json()).catch(() => ({})),
      ]);
      setSummary(sumRes);
      setByProduct(prodRes.rows || prodRes.data || []);

      // stock-movement를 날짜별 집계로 변환
      const rows = mvRes.rows || [];
      const dateMap = {};
      rows.forEach(r => {
        const d = (r.created_at || '').slice(0, 10);
        if (!d) return;
        if (!dateMap[d]) dateMap[d] = 0;
        dateMap[d] += Number(r.qty_kg || 0);
      });
      const chartData = Object.entries(dateMap)
        .sort(([a], [b]) => a.localeCompare(b))
        .map(([label, value]) => ({ label, value }));
      setMovement(chartData);
    } catch {}
    setLoading(false);
  };

  useEffect(() => { load(); }, []);

  // 상태별 집계 계산
  const statusData = (() => {
    if (!summary) return [];
    const keys = ['AVAILABLE', 'RESERVED', 'PICKED', 'OUTBOUND', 'RETURN'];
    return keys.map(k => ({
      status:   k,
      bags:     summary[`${k.toLowerCase()}_lots`] || summary[`${k}_count`] || 0,
      total_kg: summary[`${k.toLowerCase()}_kg`]   || summary[`${k}_kg`]    || 0,
    })).filter(r => r.bags > 0 || r.total_kg > 0);
  })();

  const totalKg   = statusData.reduce((s, r) => s + Number(r.total_kg || 0), 0);
  const totalLots = statusData.reduce((s, r) => s + Number(r.bags || 0), 0);

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <h2 style={{ color: '#f1f5f9', marginBottom: 2 }}>📊 Summary</h2>
          <p style={{ fontSize: 12, color: '#64748b' }}>재고 현황 요약 · 상태별 집계 · 제품별 현황</p>
        </div>
        <button onClick={load} disabled={loading}
          style={{ padding: '7px 14px', background: '#334155', color: '#94a3b8', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 12 }}>
          {loading ? '...' : '🔄 새로고침'}
        </button>
      </div>

      {loading && <div style={{ color: '#64748b', fontSize: 13, padding: 16 }}>Loading...</div>}

      {!loading && (
        <>
          {/* KPI 카드 */}
          <div style={cardStyle}>
            <div style={titleStyle}>📦 전체 현황</div>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              <KpiCard label="전체 중량"     value={fmt(totalKg)}   unit="kg"  color="#38bdf8" />
              <KpiCard label="전체 LOT/톤백" value={fmt(totalLots)} unit="개"  color="#4ade80" />
              <KpiCard label="AVAILABLE"     value={fmt(statusData.find(s => s.status === 'AVAILABLE')?.total_kg || 0)} unit="kg" color="#4ade80" />
              <KpiCard label="RESERVED"      value={fmt(statusData.find(s => s.status === 'RESERVED')?.total_kg  || 0)} unit="kg" color="#facc15" />
              <KpiCard label="PICKED"        value={fmt(statusData.find(s => s.status === 'PICKED')?.total_kg    || 0)} unit="kg" color="#a78bfa" />
            </div>
          </div>

          {/* 상태별 집계 */}
          {statusData.length > 0 && (
            <div style={cardStyle}>
              <div style={titleStyle}>🎯 상태별 재고 현황</div>
              <StatusSummary data={statusData} />
            </div>
          )}

          {/* 재고 이동 차트 */}
          {movement.length > 0 && (
            <div style={cardStyle}>
              <div style={titleStyle}>📈 최근 재고 이동 추이 (날짜별 중량)</div>
              <BarChart data={movement} color="#38bdf8" height={100} />
            </div>
          )}

          {/* 제품별 현황 */}
          {byProduct.length > 0 && (
            <div style={cardStyle}>
              <div style={titleStyle}>🏷️ 제품별 재고 현황</div>
              <ProductTable data={byProduct} />
            </div>
          )}

          {!summary && !loading && (
            <div style={{ color: '#475569', fontSize: 13, padding: 24, textAlign: 'center' }}>
              Dashboard API에서 데이터를 불러올 수 없습니다.
            </div>
          )}
        </>
      )}
    </div>
  );
}
