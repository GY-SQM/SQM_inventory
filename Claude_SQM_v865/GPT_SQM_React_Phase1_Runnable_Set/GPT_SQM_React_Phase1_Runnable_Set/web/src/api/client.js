import React from "react";

const API_BASE = import.meta.env.VITE_API_BASE || "/api";

export async function apiGet(path) {
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const res = await fetch(`${API_BASE}${normalizedPath}`, {
    method: "GET",
    headers: {
      Accept: "application/json",
    },
  });

  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `API error: ${res.status}`);
  }

  return res.json();
}

export function buildQuery(params = {}) {
  const qs = new URLSearchParams();

  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null) return;
    const text = String(value).trim();
    if (!text) return;
    qs.set(key, text);
  });

  const query = qs.toString();
  return query ? `?${query}` : "";
}

export function formatMt(value) {
  const n = Number(value || 0);
  return `${n.toLocaleString(undefined, { maximumFractionDigits: 3 })} MT`;
}

export function formatKg(value) {
  const n = Number(value || 0);
  return `${n.toLocaleString(undefined, { maximumFractionDigits: 3 })} kg`;
}

export function normalizeDisplayStatus(status) {
  const raw = String(status || "").trim().toUpperCase();
  if (!raw) return "UNKNOWN";
  if (raw === "SOLD") return "OUTBOUND";
  return raw;
}

export function StatusBadge({ status }) {
  const label = normalizeDisplayStatus(status);
  const palette = {
    AVAILABLE: { bg: "#e8fff1", color: "#127a3a" },
    RESERVED: { bg: "#fff7df", color: "#946200" },
    PICKED: { bg: "#eef4ff", color: "#1f57b0" },
    OUTBOUND: { bg: "#f3ecff", color: "#6a35c1" },
    OTHER: { bg: "#f8f7f4", color: "#8a6b00" },
    UNKNOWN: { bg: "#f3f4f6", color: "#4b5563" },
  };
  const style = palette[label] || palette.UNKNOWN;

  return (
    <span
      style={{
        display: "inline-block",
        padding: "4px 10px",
        borderRadius: 999,
        fontSize: 12,
        fontWeight: 700,
        backgroundColor: style.bg,
        color: style.color,
        whiteSpace: "nowrap",
      }}
    >
      {label}
    </span>
  );
}
