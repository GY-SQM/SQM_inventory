import { fetchJson } from './client';

export const getTonbagList = (params = {}) => {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params))
    if (v !== undefined && v !== null && v !== '') qs.set(k, v);
  return fetchJson(`/tabs/tonbag?${qs}`);
};

export const getAllocationList = (params = {}) => {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params))
    if (v !== undefined && v !== null && v !== '') qs.set(k, v);
  return fetchJson(`/tabs/allocation?${qs}`);
};

export const getPickedList = (params = {}) => {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params))
    if (v !== undefined && v !== null && v !== '') qs.set(k, v);
  return fetchJson(`/tabs/picked?${qs}`);
};

export const getSoldList = (params = {}) => {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params))
    if (v !== undefined && v !== null && v !== '') qs.set(k, v);
  return fetchJson(`/tabs/sold?${qs}`);
};

export const getOutboundList = (params = {}) => {
  const qs = new URLSearchParams();
  for (const [k, v] of Object.entries(params))
    if (v !== undefined && v !== null && v !== '') qs.set(k, v);
  return fetchJson(`/tabs/outbound?${qs}`);
};
