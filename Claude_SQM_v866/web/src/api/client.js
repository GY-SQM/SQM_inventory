const BASE = '/api';

export async function fetchJson(path, { signal } = {}) {
  let res;
  try {
    res = await fetch(`${BASE}${path}`, { signal });
  } catch (err) {
    if (err.name === 'AbortError') throw err;
    throw new Error('서버에 연결할 수 없습니다. 네트워크를 확인해주세요.');
  }
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(text || `API ${res.status}: ${res.statusText}`);
  }
  return res.json();
}
