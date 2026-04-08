/**
 * SQM 중앙 API 클라이언트
 * 모든 fetch 호출은 이 모듈을 경유한다.
 * BASE URL 변경 시 이 파일만 수정하면 됨.
 */

const BASE_URL = '/api';

class ApiError extends Error {
  constructor(status, message, detail = null) {
    super(message);
    this.status  = status;
    this.detail  = detail;
    this.name    = 'ApiError';
  }
}

async function _request(method, path, body = null, isFormData = false) {
  const url  = `${BASE_URL}${path}`;
  const opts = { method };

  if (body !== null) {
    if (isFormData) {
      opts.body = body; // FormData
    } else {
      opts.headers = { 'Content-Type': 'application/json' };
      opts.body    = JSON.stringify(body);
    }
  }

  let res;
  try {
    res = await fetch(url, opts);
  } catch (err) {
    throw new ApiError(0, `네트워크 오류: ${err.message}`);
  }

  // 파일 다운로드 응답 처리
  const ct = res.headers.get('content-type') || '';
  if (ct.includes('spreadsheet') || ct.includes('excel') ||
      ct.includes('pdf') || ct.includes('octet-stream')) {
    if (!res.ok) throw new ApiError(res.status, `다운로드 실패: HTTP ${res.status}`);
    const blob = await res.blob();
    const cd   = res.headers.get('content-disposition') || '';
    const fname = cd.split('filename=')[1]?.replace(/"/g, '') || 'download';
    return { _isBlob: true, blob, filename: fname };
  }

  let data;
  try {
    data = await res.json();
  } catch {
    data = { detail: await res.text().catch(() => '') };
  }

  if (!res.ok) {
    const msg = data?.detail || data?.message || `HTTP ${res.status}`;
    throw new ApiError(res.status, msg, data);
  }
  return data;
}

/** GET 요청 */
export const apiGet = (path) => _request('GET', path);

/** POST JSON 요청 */
export const apiPost = (path, body = {}) => _request('POST', path, body);

/** DELETE 요청 */
export const apiDelete = (path) => _request('DELETE', path);

/** FormData 파일 업로드 */
export const apiUpload = (path, formData) => _request('POST', path, formData, true);

/** 파일 다운로드 — blob을 받아 자동으로 클릭 저장 */
export const apiDownload = async (path, method = 'GET', body = null, fallbackFilename = 'download') => {
  const result = await _request(method, path, body);
  if (result._isBlob) {
    const href = URL.createObjectURL(result.blob);
    const a    = document.createElement('a');
    a.href     = href;
    a.download = result.filename || fallbackFilename;
    document.body.appendChild(a);
    a.click();
    setTimeout(() => { URL.revokeObjectURL(href); a.remove(); }, 500);
  }
  return result;
};

/** query string 생성 헬퍼 */
export const buildQS = (params = {}) => {
  const p = new URLSearchParams(
    Object.fromEntries(Object.entries(params).filter(([, v]) => v !== '' && v !== null && v !== undefined))
  );
  const s = p.toString();
  return s ? `?${s}` : '';
};

export { ApiError };
export default { get: apiGet, post: apiPost, delete: apiDelete, upload: apiUpload, download: apiDownload, qs: buildQS };
