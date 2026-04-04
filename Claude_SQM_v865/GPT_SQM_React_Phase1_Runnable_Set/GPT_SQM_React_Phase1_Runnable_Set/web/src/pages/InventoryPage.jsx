import React, { useEffect, useMemo, useState } from "react";
import { apiGet, buildQuery, formatMt, StatusBadge } from "../api/client";

function FilterRow({ filters, options, onChange, onSearch, onReset, loading }) {
  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(6, minmax(0, 1fr))",
        gap: 12,
        marginBottom: 16,
      }}
    >
      <input
        placeholder="통합 키워드 (LOT / TONBAG / 품목 / BL / SAP)"
        value={filters.keyword}
        onChange={(e) => onChange("keyword", e.target.value)}
        style={inputStyle}
      />
      <input
        placeholder="LOT No"
        value={filters.lot_no}
        onChange={(e) => onChange("lot_no", e.target.value)}
        style={inputStyle}
      />
      <select
        value={filters.status}
        onChange={(e) => onChange("status", e.target.value)}
        style={inputStyle}
      >
        <option value="">전체 상태</option>
        {options.statuses.map((item) => (
          <option key={item} value={item}>
            {item}
          </option>
        ))}
      </select>
      <select
        value={filters.product_name}
        onChange={(e) => onChange("product_name", e.target.value)}
        style={inputStyle}
      >
        <option value="">전체 품목</option>
        {options.products.map((item) => (
          <option key={item} value={item}>
            {item}
          </option>
        ))}
      </select>
      <select
        value={filters.location}
        onChange={(e) => onChange("location", e.target.value)}
        style={inputStyle}
      >
        <option value="">전체 위치</option>
        {options.locations.map((item) => (
          <option key={item} value={item}>
            {item}
          </option>
        ))}
      </select>
      <div style={{ display: "flex", gap: 8 }}>
        <button onClick={onSearch} disabled={loading} style={primaryButtonStyle}>
          조회
        </button>
        <button onClick={onReset} disabled={loading} style={secondaryButtonStyle}>
          초기화
        </button>
      </div>
    </div>
  );
}

function LotDetailPanel({ detail, onClose }) {
  if (!detail) return null;

  return (
    <div
      style={{
        marginTop: 20,
        border: "1px solid #e5e7eb",
        borderRadius: 16,
        padding: 20,
        background: "#ffffff",
        boxShadow: "0 10px 30px rgba(15, 23, 42, 0.08)",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
        <div>
          <div style={{ fontSize: 22, fontWeight: 800 }}>{detail.lot_no}</div>
          <div style={{ fontSize: 13, color: "#6b7280", marginTop: 4 }}>
            품목: {detail.product_name || "-"} / SAP: {detail.sap_no || "-"} / BL: {detail.bl_no || "-"}
          </div>
        </div>
        <button onClick={onClose} style={secondaryButtonStyle}>닫기</button>
      </div>

      <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginBottom: 16 }}>
        <StatusBadge status={detail.inventory_status} />
        <span style={metaChipStyle}>톤백 수: {detail.tonbag_count}</span>
        <span style={metaChipStyle}>조회시각: {detail.generated_at}</span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "360px 1fr", gap: 16 }}>
        <div style={panelStyle}>
          <div style={panelTitleStyle}>LOT 상태 요약</div>
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thStyle}>상태</th>
                <th style={thStyle}>톤백수</th>
                <th style={thStyle}>중량</th>
              </tr>
            </thead>
            <tbody>
              {(detail.status_summary || []).map((row) => (
                <tr key={row.status}>
                  <td style={tdStyle}><StatusBadge status={row.status} /></td>
                  <td style={tdStyle}>{row.bag_count}</td>
                  <td style={tdStyle}>{formatMt(row.weight_mt)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div style={panelStyle}>
          <div style={panelTitleStyle}>LOT 하위 TONBAG</div>
          <div style={{ maxHeight: 420, overflow: "auto" }}>
            <table style={tableStyle}>
              <thead>
                <tr>
                  <th style={thStyle}>TONBAG UID</th>
                  <th style={thStyle}>TONBAG NO</th>
                  <th style={thStyle}>상태</th>
                  <th style={thStyle}>위치</th>
                  <th style={thStyle}>중량</th>
                  <th style={thStyle}>샘플</th>
                </tr>
              </thead>
              <tbody>
                {(detail.tonbags || []).map((row) => (
                  <tr key={`${row.tonbag_id}-${row.tonbag_uid}`}>
                    <td style={tdStyle}>{row.tonbag_uid || "-"}</td>
                    <td style={tdStyle}>{row.tonbag_no || "-"}</td>
                    <td style={tdStyle}><StatusBadge status={row.status} /></td>
                    <td style={tdStyle}>{row.location || "-"}</td>
                    <td style={tdStyle}>{formatMt(row.weight_mt)}</td>
                    <td style={tdStyle}>{row.is_sample ? "Y" : "N"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}

export default function InventoryPage() {
  const [filters, setFilters] = useState({
    keyword: "",
    lot_no: "",
    status: "",
    product_name: "",
    location: "",
    page: 1,
    page_size: 50,
  });
  const [options, setOptions] = useState({ statuses: [], products: [], locations: [] });
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [generatedAt, setGeneratedAt] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [selectedLot, setSelectedLot] = useState("");
  const [lotDetail, setLotDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const totalPages = useMemo(() => Math.max(1, Math.ceil(total / Number(filters.page_size || 50))), [total, filters.page_size]);

  const loadFilterOptions = async () => {
    try {
      const data = await apiGet("/inventory/filters");
      setOptions({
        statuses: data.statuses || [],
        products: data.products || [],
        locations: data.locations || [],
      });
    } catch (err) {
      console.error(err);
    }
  };

  const loadInventory = async (nextFilters = filters) => {
    setLoading(true);
    setError("");
    try {
      const query = buildQuery(nextFilters);
      const data = await apiGet(`/inventory/search${query}`);
      setRows(data.rows || []);
      setTotal(Number(data.total || 0));
      setGeneratedAt(data.generated_at || "");
    } catch (err) {
      setError(err.message || "재고 조회 중 오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  };

  const loadLotDetail = async (lotNo) => {
    if (!lotNo) return;
    setSelectedLot(lotNo);
    setDetailLoading(true);
    try {
      const data = await apiGet(`/inventory/lot/${encodeURIComponent(lotNo)}`);
      setLotDetail(data);
    } catch (err) {
      setError(err.message || "LOT 상세 조회 중 오류가 발생했습니다.");
    } finally {
      setDetailLoading(false);
    }
  };

  useEffect(() => {
    loadFilterOptions();
    loadInventory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleChange = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value, page: 1 }));
  };

  const handleSearch = () => {
    loadInventory({ ...filters, page: 1 });
  };

  const handleReset = () => {
    const reset = {
      keyword: "",
      lot_no: "",
      status: "",
      product_name: "",
      location: "",
      page: 1,
      page_size: 50,
    };
    setFilters(reset);
    setLotDetail(null);
    setSelectedLot("");
    loadInventory(reset);
  };

  const movePage = (delta) => {
    const nextPage = Math.min(totalPages, Math.max(1, Number(filters.page || 1) + delta));
    const nextFilters = { ...filters, page: nextPage };
    setFilters(nextFilters);
    loadInventory(nextFilters);
  };

  return (
    <div style={pageStyle}>
      <div style={headerStyle}>
        <div>
          <div style={{ fontSize: 30, fontWeight: 900, letterSpacing: -0.4 }}>SQM 재고조회</div>
          <div style={{ color: "#6b7280", marginTop: 6 }}>
            React 1단계 초안 · OUTBOUND 기준 상태 표시 · generated_at: {generatedAt || "-"}
          </div>
        </div>
        <div style={{ display: "flex", gap: 10 }}>
          <span style={metaChipStyle}>총 건수: {total.toLocaleString()}</span>
          <span style={metaChipStyle}>선택 LOT: {selectedLot || "-"}</span>
        </div>
      </div>

      <FilterRow
        filters={filters}
        options={options}
        onChange={handleChange}
        onSearch={handleSearch}
        onReset={handleReset}
        loading={loading}
      />

      {error ? (
        <div style={errorStyle}>{error}</div>
      ) : null}

      <div style={panelStyle}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
          <div style={panelTitleStyle}>재고 목록</div>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <button onClick={() => movePage(-1)} disabled={loading || Number(filters.page) <= 1} style={secondaryButtonStyle}>
              이전
            </button>
            <span style={{ fontSize: 13, color: "#475569" }}>
              {filters.page} / {totalPages}
            </span>
            <button onClick={() => movePage(1)} disabled={loading || Number(filters.page) >= totalPages} style={secondaryButtonStyle}>
              다음
            </button>
          </div>
        </div>

        <div style={{ overflow: "auto", maxHeight: 520 }}>
          <table style={tableStyle}>
            <thead>
              <tr>
                <th style={thStyle}>LOT No</th>
                <th style={thStyle}>TONBAG UID</th>
                <th style={thStyle}>품목</th>
                <th style={thStyle}>상태</th>
                <th style={thStyle}>위치</th>
                <th style={thStyle}>중량</th>
                <th style={thStyle}>샘플</th>
                <th style={thStyle}>상세</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td style={tdStyle} colSpan={8}>조회 중...</td>
                </tr>
              ) : rows.length === 0 ? (
                <tr>
                  <td style={tdStyle} colSpan={8}>조회 결과가 없습니다.</td>
                </tr>
              ) : (
                rows.map((row) => (
                  <tr key={`${row.tonbag_id}-${row.tonbag_uid}`}>
                    <td style={tdStyle}>{row.lot_no}</td>
                    <td style={tdStyle}>{row.tonbag_uid || row.tonbag_no || "-"}</td>
                    <td style={tdStyle}>{row.product_name || "-"}</td>
                    <td style={tdStyle}><StatusBadge status={row.status} /></td>
                    <td style={tdStyle}>{row.location || "-"}</td>
                    <td style={tdStyle}>{formatMt(row.weight_mt)}</td>
                    <td style={tdStyle}>{row.is_sample ? "Y" : "N"}</td>
                    <td style={tdStyle}>
                      <button onClick={() => loadLotDetail(row.lot_no)} style={secondaryButtonStyle}>
                        LOT 보기
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {detailLoading ? <div style={{ marginTop: 12, color: "#475569" }}>LOT 상세 조회 중...</div> : null}
      <LotDetailPanel detail={lotDetail} onClose={() => setLotDetail(null)} />
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
  marginBottom: 10,
};

const inputStyle = {
  width: "100%",
  padding: "12px 14px",
  borderRadius: 12,
  border: "1px solid #d1d5db",
  background: "#ffffff",
  outline: "none",
  fontSize: 14,
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

const secondaryButtonStyle = {
  padding: "10px 14px",
  borderRadius: 12,
  border: "1px solid #d1d5db",
  background: "#ffffff",
  color: "#0f172a",
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
