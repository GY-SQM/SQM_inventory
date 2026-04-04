import React from "react";
import { NavLink, Navigate, Route, Routes } from "react-router-dom";
import DashboardPage from "./pages/DashboardPage";
import InventoryPage from "./pages/InventoryPage";

function NotFoundPage() {
  return (
    <div style={centerPageStyle}>
      <div style={notFoundCardStyle}>
        <div style={{ fontSize: 24, fontWeight: 900, marginBottom: 8 }}>페이지를 찾을 수 없습니다.</div>
        <div style={{ color: "#64748b", marginBottom: 16 }}>
          주소가 잘못되었거나 아직 연결되지 않은 화면입니다.
        </div>
        <NavLink to="/dashboard" style={primaryLinkStyle}>
          대시보드로 이동
        </NavLink>
      </div>
    </div>
  );
}

function AppShell() {
  return (
    <div style={shellStyle}>
      <aside style={sidebarStyle}>
        <div style={brandWrapStyle}>
          <div style={brandBadgeStyle}>SQM</div>
          <div>
            <div style={brandTitleStyle}>SQM React 1단계</div>
            <div style={brandSubStyle}>Dashboard + Inventory</div>
          </div>
        </div>

        <nav style={navStyle}>
          <NavItem to="/dashboard" label="대시보드" />
          <NavItem to="/inventory" label="재고조회" />
        </nav>

        <div style={infoPanelStyle}>
          <div style={infoTitleStyle}>현재 범위</div>
          <ul style={infoListStyle}>
            <li>조회 전용 API</li>
            <li>OUTBOUND 기준 상태 표시</li>
            <li>기존 tkinter write-path 유지</li>
          </ul>
        </div>
      </aside>

      <main style={contentStyle}>
        <div style={topbarStyle}>
          <div>
            <div style={{ fontSize: 12, color: "#64748b", fontWeight: 700 }}>SQM Inventory / React Web</div>
            <div style={{ fontSize: 22, fontWeight: 900, letterSpacing: -0.4 }}>운영 대시보드 초안</div>
          </div>
          <div style={topbarMetaStyle}>Vite + React Router + FastAPI Proxy</div>
        </div>

        <Routes>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/inventory" element={<InventoryPage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </main>
    </div>
  );
}

function NavItem({ to, label }) {
  return (
    <NavLink
      to={to}
      style={({ isActive }) => ({
        ...navLinkStyle,
        background: isActive ? "linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)" : "#ffffff",
        color: isActive ? "#ffffff" : "#0f172a",
        borderColor: isActive ? "#1d4ed8" : "#e5e7eb",
        boxShadow: isActive ? "0 10px 20px rgba(37, 99, 235, 0.18)" : "none",
      })}
    >
      {label}
    </NavLink>
  );
}

export default function App() {
  return <AppShell />;
}

const shellStyle = {
  minHeight: "100vh",
  display: "grid",
  gridTemplateColumns: "280px 1fr",
  background: "#e2e8f0",
};

const sidebarStyle = {
  padding: 20,
  background: "linear-gradient(180deg, #eff6ff 0%, #f8fafc 100%)",
  borderRight: "1px solid #dbeafe",
  display: "flex",
  flexDirection: "column",
  gap: 20,
};

const contentStyle = {
  minWidth: 0,
  background: "#f1f5f9",
};

const topbarStyle = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  padding: "18px 24px",
  background: "#ffffff",
  borderBottom: "1px solid #e5e7eb",
  position: "sticky",
  top: 0,
  zIndex: 20,
};

const topbarMetaStyle = {
  fontSize: 13,
  fontWeight: 700,
  color: "#334155",
  padding: "8px 12px",
  borderRadius: 999,
  background: "#eff6ff",
  border: "1px solid #bfdbfe",
};

const brandWrapStyle = {
  display: "flex",
  alignItems: "center",
  gap: 12,
};

const brandBadgeStyle = {
  width: 48,
  height: 48,
  borderRadius: 14,
  background: "linear-gradient(135deg, #1d4ed8 0%, #2563eb 100%)",
  color: "#ffffff",
  display: "grid",
  placeItems: "center",
  fontWeight: 900,
  fontSize: 16,
  boxShadow: "0 12px 24px rgba(37, 99, 235, 0.22)",
};

const brandTitleStyle = {
  fontSize: 20,
  fontWeight: 900,
  letterSpacing: -0.4,
};

const brandSubStyle = {
  fontSize: 13,
  color: "#64748b",
  marginTop: 4,
};

const navStyle = {
  display: "flex",
  flexDirection: "column",
  gap: 10,
};

const navLinkStyle = {
  display: "block",
  textDecoration: "none",
  fontWeight: 800,
  borderRadius: 14,
  padding: "14px 16px",
  border: "1px solid #e5e7eb",
  transition: "all 0.2s ease",
};

const infoPanelStyle = {
  marginTop: "auto",
  padding: 16,
  borderRadius: 16,
  background: "#ffffff",
  border: "1px solid #e5e7eb",
  boxShadow: "0 10px 20px rgba(15, 23, 42, 0.05)",
};

const infoTitleStyle = {
  fontSize: 14,
  fontWeight: 900,
  marginBottom: 10,
};

const infoListStyle = {
  margin: 0,
  paddingLeft: 18,
  color: "#475569",
  lineHeight: 1.7,
  fontSize: 13,
};

const centerPageStyle = {
  minHeight: "calc(100vh - 80px)",
  display: "grid",
  placeItems: "center",
  padding: 24,
};

const notFoundCardStyle = {
  width: "min(520px, 100%)",
  background: "#ffffff",
  padding: 24,
  borderRadius: 20,
  border: "1px solid #e5e7eb",
  boxShadow: "0 16px 40px rgba(15, 23, 42, 0.08)",
};

const primaryLinkStyle = {
  display: "inline-block",
  textDecoration: "none",
  padding: "12px 16px",
  borderRadius: 12,
  background: "#2563eb",
  color: "#ffffff",
  fontWeight: 800,
};
