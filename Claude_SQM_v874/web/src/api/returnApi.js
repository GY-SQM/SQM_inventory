import { fetchJson } from './client';

const BASE = '/api';

export const getReturnList = (params = {}) => {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') qs.set(k, v);
  }
  return fetchJson(`/return/list?${qs.toString()}`);
};

export const getReturnStatistics = (params = {}) => {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') qs.set(k, v);
  }
  return fetchJson(`/return/statistics?${qs.toString()}`);
};

export const postReturnSingle = async (body) => {
  const res = await fetch(`${BASE}/return/single`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || `API ${res.status}`);
  }
  return res.json();
};

export const postReturnBulkExcel = async (formData) => {
  const res = await fetch(`${BASE}/return/bulk-excel`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || `API ${res.status}`);
  }
  return res.json();
};

export const postReturnBulkConfirm = async (items) => {
  const res = await fetch(`${BASE}/return/bulk-confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ items }),
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || `API ${res.status}`);
  }
  return res.json();
};
