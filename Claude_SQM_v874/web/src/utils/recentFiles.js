/**
 * recentFiles — localStorage 기반 최근 작업 이력 관리
 * 저장 항목: { filename, type, timestamp, path }
 * 최대 10개 유지
 */
const STORAGE_KEY = 'sqm_recent_files';
const MAX_ITEMS = 10;

export function getRecentFiles() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function addRecentFile({ filename, type, path }) {
  const label = filename || path;
  // 동일 라우트라도 작업 설명이 다르면 별도 항목으로 유지 (예: 스캔 /scan 여러 건)
  const items = getRecentFiles().filter(f => !(f.path === path && f.filename === label));
  const newItem = {
    filename: filename || path,
    type: type || '작업',
    path,
    timestamp: new Date().toISOString(),
  };
  const updated = [newItem, ...items].slice(0, MAX_ITEMS);
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
  } catch {}
  return updated;
}

export function clearRecentFiles() {
  localStorage.removeItem(STORAGE_KEY);
}
