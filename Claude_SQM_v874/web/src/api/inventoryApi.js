import { fetchJson } from './client';

export const getInventoryFilters = () => fetchJson('/inventory/filters');

export const searchInventory = (params = {}) => {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null && v !== '') qs.set(k, v);
  }
  return fetchJson(`/inventory/search?${qs.toString()}`);
};

export const getLotDetail = (lotNo) => fetchJson(`/inventory/lot/${lotNo}`);
