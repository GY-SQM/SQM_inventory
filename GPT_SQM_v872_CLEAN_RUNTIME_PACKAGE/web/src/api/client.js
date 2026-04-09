/**
 * SQM API 중앙 클라이언트 v1.0
 * 모든 페이지에서 fetch() 직접 호출 대신 이 모듈 사용
 *
 * 사용법:
 *   import { api, downloadFile } from '../api/client';
 *   const data = await api.get('/inventory/list');
 *   const data = await api.post('/inbound/confirm', { lot_no: '...' });
 */

const BASE = '/api';

async function request(method, path, body = null, isFile = false) {
  const opts = { method };
  if (body && !isFile) {
    opts.headers = { 'Content-Type': 'application/json' };
    opts.body = JSON.stringify(body);
  } else if (isFile) {
    opts.body = body; // FormData
  }
  const r = await fetch(`${BASE}${path}`, opts);
  if (!r.ok) {
    const text = await r.text().catch(() => `HTTP ${r.status}`);
    throw new Error(text || `HTTP ${r.status}`);
  }
  return r.json();
}

export const api = {
  get:    (path)          => request('GET',    path),
  post:   (path, body)    => request('POST',   path, body),
  put:    (path, body)    => request('PUT',    path, body),
  delete: (path)          => request('DELETE', path),
  upload: (path, formData) => request('POST',  path, formData, true),
};

/** 파일 다운로드 — Blob → 자동 저장 */
export async function downloadFile(path, method = 'GET', body = null, filename = null) {
  const opts = { method };
  if (body) {
    opts.headers = { 'Content-Type': 'application/json' };
    opts.body = JSON.stringify(body);
  }
  const r = await fetch(`${BASE}${path}`, opts);
  if (!r.ok) throw new Error(await r.text().catch(() => `HTTP ${r.status}`));
  const blob = await r.blob();
  const href = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = href;
  a.download = filename
    || (r.headers.get('content-disposition') || '').split('filename=')[1]?.replace(/"/g, '')
    || 'download';
  document.body.appendChild(a);
  a.click();
  setTimeout(() => { URL.revokeObjectURL(href); a.remove(); }, 500);
}

export default api;

/** fetchJson — 하위 호환 래퍼 (inventoryApi 등에서 사용) */
export async function fetchJson(path, options = {}) {
  const method = options.method || 'GET';
  const body   = options.body   || null;
  return request(method, path, body);
}
