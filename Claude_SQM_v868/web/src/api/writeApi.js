const BASE = '/api';

async function postJson(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return res.json();
}

async function putJson(path, body) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return res.json();
}

export function createInbound(data) {
  return postJson('/inbound/create', data);
}

export function executeOutbound(data) {
  return postJson('/outbound/execute', data);
}

export function cancelOutbound(lotNo, subLt) {
  return putJson('/outbound/cancel', { lot_no: lotNo, sub_lt: subLt });
}

export function updateLocation(lotNo, subLt, newLocation) {
  return putJson('/location/update', { lot_no: lotNo, sub_lt: subLt, new_location: newLocation });
}

export async function uploadFile(file) {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${BASE}/files/upload`, {
    method: 'POST',
    body: formData,
  });
  return res.json();
}

export function unifiedSearch(params) {
  const qs = new URLSearchParams(params).toString();
  return fetch(`${BASE}/search/unified?${qs}`).then(r => r.json());
}

export function exportCsv(params = {}) {
  const qs = new URLSearchParams(params).toString();
  window.open(`${BASE}/tools/export/csv?${qs}`, '_blank');
}

export function integrityCheck() {
  return fetch(`${BASE}/tools/integrity-check`).then(r => r.json());
}
