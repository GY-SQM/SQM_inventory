import React, { useEffect, useMemo, useState } from "react";
import { apiGet, formatMt, StatusBadge } from "../api/client";

function KpiCard({ title, value, subValue, badge }) {
  return (
    <div style={kpiCardStyle}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
        <div style={{ fontSize: 13, color: "#64748b", fontWeight: 700 }}>{title}</div>
        {badge}
      </div>
      <div style={{ fontSize: 28, fontWeight: 900, letterSpacing: -0.5 }}>{value}</div>
      <div style={{ marginTop: 6, color: "#475569", fontSize: 13 }}>{subValue}</div>
    </div>
  );
}

function SummaryTable({ items }) {
  return (
    <div style={panelStyle}>
      <div style={panelTitleStyle}>상태별 요약</div>
      <div style={{ overflow: "auto", maxHeight: 420 }}>
        <table style={tableStyle}>
          <thead>
            <tr>
              <th style={thStyle}>상태</th>
              <th style={thStyle}>톤백 수</th>
              <th style={thStyle}>중량(MT)</th>
              <th style={thStyle}>샘플 수</th>
            </tr>
          </thead>
          <tbody>
            {(items || []).map((row) => (
              <tr key={row.status}>
                <td style={tdStyle}><StatusBadge status={row.status} /></td>
                <td style={tdStyle}>{Number(row.bag_count || 0).toLocaleString()}</td>
                <td style={tdStyle}>{formatMt(row.weight_mt)}</td>
                <td style={tdStyle}>{Number(row.sample_bag_count || 0).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ProductTable({ rows }) {
  return (
    <div style={panelStyle}>
      <div style={panelTitleStyle}>품목별 재고 요약</div>
      <div style={{ overflow: "auto", maxHeight: 520 }}>
        <table style={tableStyle}>
          <thead>
            <tr>
              <th style={thStyle}>품목</th>
              <th style={thStyle}>LOT 수</th>
              <th style={thStyle}>톤백 수</th>
              <th style={thStyle}>AVAILABLE</th>
              <th style={thStyle}>RESERVED</th>
              <th style={thStyle}>PICKED</th>
              <th style={thStyle}>OUTBOUND</th>
              <th style={thStyle}>합계(MT)</th>
            </tr>
          </thead>
          <tbody>
            {(rows || []).length === 0 ? (
              <tr>
                <td style={tdStyle} colSpan={8}>조회 결과가 없습니다.</td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr key={`${row.product_name}-${row.lot_count}-${row.tonbag_count}`}>
                  <td style={tdStyle}>{row.product_name || "UNKNOWN"}</td>
                  <td style={tdStyle}>{Number(row.lot_count || 0).toLocaleString()}</td>
                  <td style={tdStyle}>{Number(row.tonbag_count || 0).toLocaleString()}</td>
                  <td style={tdStyle}>{formatMt(row.available_mt)}</td>
                  <td style={tdStyle}>{formatMt(row.reserved_mt)}</td>
                  <td style={tdStyle}>{formatMt(row.picked_mt)}</td>
                  <td style={tdStyle}>{formatMt(row.outbound_mt)}</td>
                  <td style={tdStyle}>{formatMt(row.total_mt)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function LocationTable({ rows }) {
  return (
    <div style={panelStyle}>
      <div style={panelTitleStyle}>위치별 요약</div>
      <div style={{ overflow: "auto", maxHeight: 380 }}>
        <table style={tableStyle}>
          <thead>
            <tr>
              <th style={thStyle}>위치</th>
              <th style={thStyle}>톤백 수</th>
              <th style={thStyle}>중량(MT)</th>
            </tr>
          </thead>
          <tbody>
            {(rows || []).length === 0 ? (
              <tr>
                <td style={tdStyle} colSpan={3}>조회 결과가 없습니다.</td>
              </tr>
            ) : (
              rows.map((row) => (
                <tr key={row.location}>
                  <td style={tdStyle}>{row.location || "UNASSIGNED"}</td>
                  <td style={tdStyle}>{Number(row.bag_count || 0).toLocaleString()}</td>
                  <td style={tdStyle}>{formatMt(row.weight_mt)}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [summary, setSummary] = useState({ items: [], totals: {}, generated_at: "" });
  const [products, setProducts] = useState({ rows: [], generated_at: "" });
  const [locations, setLocations] = useState({ rows: [], generated_at: "" });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const summaryMap = useMemo(() => {
    const bucket = {};
    (summary.items || []).forEach((item) => {
      bucket[item.status] = item;
    });
    return bucket;
  }, [summary.items]);

  const loadDashboard = async (signal) => {
    setLoading(true);
    setError("");
    try {
      const [summaryData, productData, locationData] = await Promise.all([
        apiGet("/dashboard/summary", { signal }),
        apiGet("/dashboard/by-product", { signal }),
        apiGet("/dashboard/location-summary", { signal }),
      ]);

      setSummary(summaryData);
      setProducts(productData);
      setLocations(locationData);
    } catch (err) {
      if (err.name === "AbortError") return;
      setError(err.message || "대시보드 조회 중 오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const ctrl = new AbortController();
    loadDashboard(ctrl.signal);
    return () => ctrl.abort();
  }, []);

  const totals = summary.totals || {};
  const available = summaryMap.AVAILABLE || {};
  const reserved = summaryMap.RESERVED || {};
  const picked = summaryMap.PICKED || {};
  const outbound = summaryMap.OUTBOUND || {};

  return (
    <div style={pageStyle}>
      <div style={headerStyle}>
        <div>
          <div style={{ fontSize: 32, fontWeight: 900, letterSpacing: -0.6 }}>SQM 대시보드</div>
          <div style={{ color: "#64748b", marginTop: 6 }}>
            React 1단계 초안 · 조회 전용 · OUTBOUND 기준 상태 표시
          </div>
        </div>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <span style={metaChipStyle}>generated_at: {summary.generated_at || "-"}</span>
          <button onClick={loadDashboard} disabled={loading} style={primaryButtonStyle}>
            {loading ? "새로고침 중..." : "새로고침"}
          </button>
        </div>
      </div>

      {error ? <div style={errorStyle}>{error}</div> : null}

      <div style={kpiGridStyle}>
        <KpiCard
          title="전체 재고"
          value={formatMt(totals.weight_mt)}
          subValue={`톤백 수 ${Number(totals.bag_count || 0).toLocaleString()} / 샘플 ${Number(totals.sample_bag_count || 0).toLocaleString()}`}
          badge={<StatusBadge status="OTHER" />}
        />
        <KpiCard
          title="AVAILABLE"
          value={formatMt(available.weight_mt)}
          subValue={`톤백 ${Number(available.bag_count || 0).toLocaleString()}개`}
          badge={<StatusBadge status="AVAILABLE" />}
        />
        <KpiCard
          title="RESERVED"
          value={formatMt(reserved.weight_mt)}
          subValue={`톤백 ${Number(reserved.bag_count || 0).toLocaleString()}개`}
          badge={<StatusBadge status="RESERVED" />}
        />
        <KpiCard
          title="PICKED"
          value={formatMt(picked.weight_mt)}
          subValue={`톤백 ${Number(picked.bag_count || 0).toLocaleString()}개`}
          badge={<StatusBadge status="PICKED" />}
        />
        <KpiCard
          title="OUTBOUND"
          value={formatMt(outbound.weight_mt)}
          subValue={`톤백 ${Number(outbound.bag_count || 0).toLocaleString()}개`}
          badge={<StatusBadge status="OUTBOUND" />}
        />
      </div>

      {loading ? <div style={{ color: "#475569", marginBottom: 16 }}>대시보드 조회 중...</div> : null}

      <div style={{ display: "grid", gridTemplateColumns: "420px 1fr", gap: 16, marginBottom: 16 }}>
        <SummaryTable items={summary.items || []} />
        <LocationTable rows={locations.rows || []} />
      </div>

      <ProductTable rows={products.rows || []} />
    </div>
  );
}

const pageStyle = {
  minHeight: "100vh",
  background: "#f8fafc",
  padding: 24,
  color: "#0f172a",
};

const headerStyle = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "flex-start",
  marginBottom: 20,
  gap: 16,
  flexWrap: "wrap",
};

const kpiGridStyle = {
  display: "grid",
  gridTemplateColumns: "repeat(5, minmax(0, 1fr))",
  gap: 16,
  marginBottom: 16,
};

const kpiCardStyle = {
  background: "#ffffff",
  borderRadius: 18,
  padding: 18,
  border: "1px solid #e5e7eb",
  boxShadow: "0 10px 30px rgba(15, 23, 42, 0.06)",
};

const panelStyle = {
  background: "#ffffff",
  borderRadius: 18,
  padding: 18,
  border: "1px solid #e5e7eb",
  boxShadow: "0 10px 30px rgba(15, 23, 42, 0.06)",
};

const panelTitleStyle = {
  fontSize: 18,
  fontWeight: 800,
  marginBottom: 12,
};

const primaryButtonStyle = {
  padding: "11px 16px",
  borderRadius: 12,
  border: "none",
  background: "#2563eb",
  color: "#ffffff",
  fontWeight: 700,
  cursor: "pointer",
};

const tableStyle = {
  width: "100%",
  borderCollapse: "collapse",
};

const thStyle = {
  textAlign: "left",
  padding: "12px 10px",
  borderBottom: "1px solid #e5e7eb",
  fontSize: 13,
  color: "#475569",
  background: "#f8fafc",
  position: "sticky",
  top: 0,
};

const tdStyle = {
  padding: "12px 10px",
  borderBottom: "1px solid #f1f5f9",
  fontSize: 14,
  verticalAlign: "middle",
};

const metaChipStyle = {
  display: "inline-block",
  padding: "8px 12px",
  borderRadius: 999,
  background: "#eef2ff",
  color: "#3730a3",
  fontSize: 13,
  fontWeight: 700,
};

const errorStyle = {
  marginBottom: 16,
  padding: 14,
  borderRadius: 12,
  background: "#fef2f2",
  border: "1px solid #fecaca",
  color: "#b91c1c",
  fontWeight: 600,
};
