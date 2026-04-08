import { useState, useEffect, useCallback, useRef } from 'react';

const BASE = '/api';

const thStyle = {
  padding: '7px 10px', textAlign: 'left', background: '#1e293b',
  borderBottom: '2px solid #334155', fontSize: 11, fontWeight: 700,
  color: '#64748b', whiteSpace: 'nowrap', position: 'sticky', top: 0,
};
const tdStyle = { padding: '6px 10px', borderBottom: '1px solid #1e293b', fontSize: 12, color: '#e2e8f0', whiteSpace: 'nowrap' };
const tdC = { ...tdStyle, textAlign: 'center' };
const inputStyle = {
  padding: '8px 12px', fontSize: 13, background: '#0f172a',
  border: '1px solid #334155', borderRadius: 6, color: '#f1f5f9',
  fontFamily: 'monospace',
};

function Toast({ msg, ok }) {
  if (!msg) return null;
  return (
    <div style={{
      position: 'fixed', bottom: 28, left: '50%', transform: 'translateX(-50%)',
      background: ok ? '#064e3b' : '#450a0a',
      color: ok ? '#34d399' : '#f87171',
      padding: '10px 24px', borderRadius: 8, fontSize: 13, fontWeight: 600,
      zIndex: 9999, boxShadow: '0 4px 16px rgba(0,0,0,0.5)',
    }}>{msg}</div>
  );
}

// ── 이동 실행 패널 ───────────────────────────────────────────────────────────
function MovePanel({ onSuccess }) {
  const [uid,     setUid]     = useState('');
  const [tonbag,  setTonbag]  = useState(null);
  const [toLoc,   setToLoc]   = useState('');
  const [loading, setLoading] = useState(false);
  const [toast,   setToast]   = useState(null);
  const uidRef = useRef(null);
  const toastRef = useRef(null);

  useEffect(() => { uidRef.current?.focus(); }, []);

  const showToast = (msg, ok) => {
    setToast({ msg, ok });
    if (toastRef.current) clearTimeout(toastRef.current);
    toastRef.current = setTimeout(() => setToast(null), 2500);
  };

  // 톤백 조회
  const lookup = async () => {
    const v = uid.trim();
    if (!v) return;
    setLoading(true); setTonbag(null);
    try {
      const r = await fetch(`${BASE}/search/unified?keyword=${encodeURIComponent(v)}&page_size=1`);
      const d = await r.json();
      const row = d.rows?.[0];
      if (row) setTonbag(row);
      else showToast(`[${v}] 톤백을 찾을 수 없습니다.`, false);
    } catch (e) { showToast(e.message, false); }
    setLoading(false);
  };

  // 이동 실행
  const doMove = async () => {
    if (!tonbag || !toLoc.trim()) { showToast('목적지 위치를 입력하세요.', false); return; }
    setLoading(true);
    try {
      const r = await fetch(`${BASE}/location-bulk/single-update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lot_no:   tonbag.lot_no,
          sub_lt:   tonbag.sub_lt || 0,
          location: toLoc.trim(),
          operator: 'MOVE_UI',
        }),
      });
      const d = await r.json();
      if (d.success) {
        showToast(`✅ 이동 완료: ${tonbag.location || '?'} → ${toLoc}`, true);
        onSuccess?.();
        setUid(''); setTonbag(null); setToLoc('');
        setTimeout(() => uidRef.current?.focus(), 100);
      } else {
        showToast(`❌ ${d.message}`, false);
      }
    } catch (e) { showToast(e.message, false); }
    setLoading(false);
  };

  return (
    <div style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, padding: '18px 20px', marginBottom: 16 }}>
      <div style={{ fontSize: 13, fontWeight: 700, color: '#38bdf8', marginBottom: 14 }}>🔀 톤백 이동 처리</div>

      {/* UID 입력 */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 12, alignItems: 'center' }}>
        <div style={{ flex: 1 }}>
          <label style={{ fontSize: 11, color: '#64748b', display: 'block', marginBottom: 4 }}>톤백 UID / LOT NO</label>
          <input
            ref={uidRef}
            style={{ ...inputStyle, width: '100%', boxSizing: 'border-box' }}
            placeholder="스캔 또는 직접 입력 후 Enter"
            value={uid}
            onChange={e => setUid(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && lookup()}
          />
        </div>
        <div style={{ paddingTop: 18 }}>
          <button onClick={lookup} disabled={loading || !uid.trim()}
            style={{ padding: '8px 16px', background: uid.trim() ? '#2563eb' : '#334155', color: uid.trim() ? '#fff' : '#64748b', border: 'none', borderRadius: 6, cursor: uid.trim() ? 'pointer' : 'not-allowed', fontSize: 12, fontWeight: 600 }}>
            🔍 조회
          </button>
        </div>
      </div>

      {/* 톤백 정보 + 목적지 */}
      {tonbag && (
        <>
          <div style={{ background: '#0f172a', borderRadius: 6, padding: '10px 14px', marginBottom: 12, display: 'flex', gap: 20, flexWrap: 'wrap' }}>
            {[
              ['LOT NO',  tonbag.lot_no,       '#38bdf8'],
              ['UID',     tonbag.tonbag_uid,    '#f1f5f9'],
              ['현재위치', tonbag.location || '미지정', '#fbbf24'],
              ['상태',    tonbag.status,        '#94a3b8'],
              ['중량',    tonbag.weight_kg ? `${Number(tonbag.weight_kg).toLocaleString()}kg` : '-', '#f1f5f9'],
            ].map(([k, v, c]) => (
              <div key={k} style={{ fontSize: 12 }}>
                <span style={{ color: '#475569', marginRight: 4 }}>{k}</span>
                <span style={{ color: c, fontWeight: 600 }}>{v}</span>
              </div>
            ))}
          </div>

          <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
            <div style={{ flex: 1 }}>
              <label style={{ fontSize: 11, color: '#64748b', display: 'block', marginBottom: 4 }}>
                목적지 위치 <span style={{ color: '#ef4444' }}>*</span>
              </label>
              <input
                style={{ ...inputStyle, width: '100%', boxSizing: 'border-box', border: '1px solid #0ea5e9' }}
                placeholder="예: A-01-03, B구역-2열, 야적장-3"
                value={toLoc}
                onChange={e => setToLoc(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && doMove()}
                autoFocus
              />
            </div>
            <button onClick={doMove} disabled={loading || !toLoc.trim()}
            style={{ padding: '8px 20px', background: toLoc.trim() ? '#0ea5e9' : '#334155', color: '#fff', border: 'none', borderRadius: 6, cursor: toLoc.trim() ? 'pointer' : 'not-allowed', fontSize: 13, fontWeight: 700, height: 38 }}>
              {loading ? '처리 중...' : '🔀 이동'}
            </button>
            <button onClick={() => { setUid(''); setTonbag(null); setToLoc(''); uidRef.current?.focus(); }}
              style={{ padding: '8px 12px', background: '#475569', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 12, height: 38 }}>
              초기화
            </button>
          </div>
        </>
      )}

      {toast && <Toast msg={toast.msg} ok={toast.ok} />}
    </div>
  );
}

// ── 이동 이력 목록 ───────────────────────────────────────────────────────────
function MoveHistory({ refreshKey }) {
  const [rows,    setRows]    = useState([]);
  const [total,   setTotal]   = useState(0);
  const [page,    setPage]    = useState(1);
  const [keyword, setKeyword] = useState('');
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const p = new URLSearchParams({ page, page_size: 50 });
      if (keyword) p.set('keyword', keyword);
      const r = await fetch(`${BASE}/tabs/move-log?${p}`);
      const d = await r.json();
      setRows(d.rows || []);
      setTotal(d.total || 0);
    } catch {}
    setLoading(false);
  }, [page, keyword, refreshKey]);

  useEffect(() => { load(); }, [load]);

  const totalPages = Math.max(1, Math.ceil(total / 50));

  return (
    <div style={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, padding: '16px 20px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: '#94a3b8' }}>📋 이동 이력 (Total: {total.toLocaleString()})</div>
        <div style={{ display: 'flex', gap: 8 }}>
          <input placeholder="LOT / 위치 검색" value={keyword}
            onChange={e => { setKeyword(e.target.value); setPage(1); }}
            style={{ ...inputStyle, padding: '5px 10px', fontSize: 12, width: 180 }} />
          <button onClick={load}
            style={{ padding: '5px 12px', background: '#334155', color: '#94a3b8', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 12 }}>
            🔄
          </button>
        </div>
      </div>

      {loading && <div style={{ padding: 12, color: '#64748b', fontSize: 13 }}>Loading...</div>}

      {!loading && (
        <div style={{ overflow: 'auto', maxHeight: '45vh' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                {['No.','LOT NO','Sub','FROM','TO','사유','처리자','메모','일시'].map(h => (
                  <th key={h} style={h === 'No.' ? { ...thStyle, textAlign: 'center', width: 50 } : thStyle}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 ? (
                <tr><td colSpan={9} style={{ ...tdC, padding: 24, color: '#475569' }}>이동 이력 없음</td></tr>
              ) : rows.map((r, i) => (
                <tr key={i}
                  onMouseEnter={e => e.currentTarget.style.background = '#0f172a'}
                  onMouseLeave={e => e.currentTarget.style.background = ''}>
                  <td style={{ ...tdC, color: '#475569', fontSize: 11 }}>{(page - 1) * 50 + i + 1}</td>
                  <td style={{ ...tdStyle, color: '#38bdf8', fontWeight: 600 }}>{r.lot_no || '-'}</td>
                  <td style={tdC}>{r.sub_lt ?? '-'}</td>
                  <td style={{ ...tdStyle, color: '#fbbf24' }}>{r.from_location || '-'}</td>
                  <td style={{ ...tdStyle, color: '#34d399' }}>{r.to_location || r.location || '-'}</td>
                  <td style={tdC}>{r.reason_code || '-'}</td>
                  <td style={{ ...tdStyle, color: '#94a3b8' }}>{r.operator || r.source || '-'}</td>
                  <td style={{ ...tdStyle, maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis', color: '#64748b' }}>{r.note || '-'}</td>
                  <td style={{ ...tdC, fontSize: 11, color: '#475569' }}>{(r.created_at || '').slice(0, 16)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginTop: 8, fontSize: 12 }}>
        <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Prev</button>
        <span style={{ color: '#94a3b8' }}>{page} / {totalPages}</span>
        <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>Next</button>
      </div>
    </div>
  );
}

export default function MovePage() {
  const [refreshKey, setRefreshKey] = useState(0);
  return (
    <div style={{ padding: 24 }}>
      <h2 style={{ color: '#f1f5f9', marginBottom: 4 }}>🔀 Move</h2>
      <p style={{ fontSize: 12, color: '#64748b', marginBottom: 16 }}>
        바코드 스캔으로 톤백 위치를 이동합니다. 이동 후 tonbag_move_log에 기록됩니다.
      </p>
      <MovePanel onSuccess={() => setRefreshKey(k => k + 1)} />
      <MoveHistory refreshKey={refreshKey} />
    </div>
  );
}
