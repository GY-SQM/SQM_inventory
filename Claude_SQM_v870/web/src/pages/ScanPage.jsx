import { useState, useRef, useEffect } from 'react';
import { addRecentFile } from '../utils/recentFiles';

const BASE = '/api';

// ── 스타일 ──────────────────────────────────────────────────────────────────
const S = {
  wrap:   { padding: 20, maxWidth: 980, margin: '0 auto' },
  card:   { background: '#1e293b', border: '1px solid #334155', borderRadius: 8, padding: '16px 20px', marginBottom: 14 },
  title:  { fontSize: 13, fontWeight: 700, color: '#94a3b8', marginBottom: 10 },
  input:  { padding: '9px 12px', fontSize: 15, background: '#0f172a', border: '2px solid #334155', borderRadius: 6, color: '#f1f5f9', width: '100%', boxSizing: 'border-box', fontFamily: 'monospace' },
  inputFocus: { border: '2px solid #38bdf8' },
  infoRow:{ display: 'flex', gap: 24, flexWrap: 'wrap', marginTop: 8 },
  infoItem:{ fontSize: 12 },
  infoKey:{ color: '#64748b', marginRight: 4 },
  infoVal:{ color: '#f1f5f9', fontWeight: 600 },
  thStyle:{ padding: '6px 10px', textAlign: 'left', background: '#0f172a', borderBottom: '2px solid #334155', fontSize: 11, fontWeight: 700, color: '#64748b', whiteSpace: 'nowrap' },
  tdStyle:{ padding: '5px 10px', borderBottom: '1px solid #1e293b', fontSize: 12, color: '#e2e8f0', whiteSpace: 'nowrap' },
};

const BTN_DEFS = [
  { label: '✅ 출고확정',  color: '#22c55e', hover: '#16a34a', action: 'outbound',   statusNeeded: 'PICKED',   desc: 'PICKED → OUTBOUND' },
  { label: '🔄 반품등록',  color: '#14b8a6', hover: '#0d9488', action: 'return',    statusNeeded: 'OUTBOUND', desc: 'OUTBOUND → RETURN' },
  { label: '📦 재입고',    color: '#8b5cf6', hover: '#7c3aed', action: 'reinbound', statusNeeded: 'RETURN',   desc: 'RETURN → AVAILABLE' },
  { label: '🔀 위치이동',  color: '#0ea5e9', hover: '#0284c7', action: 'move',      statusNeeded: null,       desc: '위치 변경' },
];

const REASON_CODES = ['품질불량', '수량오류', '고객요청', '파손', '기타'];

function StatusBadge({ status }) {
  const map = {
    AVAILABLE: { bg: '#064e3b', fg: '#34d399' },
    RESERVED:  { bg: '#3b2a00', fg: '#fbbf24' },
    PICKED:    { bg: '#1e3a5f', fg: '#93c5fd' },
    OUTBOUND:  { bg: '#2d1f6e', fg: '#c4b5fd' },
    RETURN:    { bg: '#450a0a', fg: '#f87171' },
  };
  const c = map[status] || { bg: '#1e293b', fg: '#94a3b8' };
  return (
    <span style={{ display: 'inline-block', padding: '2px 8px', borderRadius: 999, fontSize: 11, fontWeight: 700, background: c.bg, color: c.fg }}>
      {status || '?'}
    </span>
  );
}

function Toast({ message, ok }) {
  if (!message) return null;
  return (
    <div style={{
      position: 'fixed', bottom: 28, left: '50%', transform: 'translateX(-50%)',
      background: ok ? '#064e3b' : '#450a0a',
      color: ok ? '#34d399' : '#f87171',
      padding: '10px 24px', borderRadius: 8, fontSize: 13, fontWeight: 600,
      zIndex: 9999, boxShadow: '0 4px 16px rgba(0,0,0,0.5)',
      border: `1px solid ${ok ? '#065f46' : '#7f1d1d'}`,
    }}>
      {message}
    </div>
  );
}

// ── 히스토리 행 ─────────────────────────────────────────────────────────────
function HistRow({ item, idx }) {
  const ok = item.success;
  return (
    <tr style={{ background: ok ? '' : '#2d0a0a' }}>
      <td style={{ ...S.tdStyle, textAlign: 'center', color: '#64748b', fontSize: 11 }}>{idx + 1}</td>
      <td style={{ ...S.tdStyle, fontFamily: 'monospace', color: '#38bdf8' }}>{item.uid}</td>
      <td style={{ ...S.tdStyle, fontWeight: 600 }}>{item.lot_no || '-'}</td>
      <td style={{ ...S.tdStyle, textAlign: 'center' }}>{item.action}</td>
      <td style={{ ...S.tdStyle, textAlign: 'center' }}>{item.status_before ? <StatusBadge status={item.status_before} /> : '-'}</td>
      <td style={{ ...S.tdStyle, textAlign: 'center' }}>→</td>
      <td style={{ ...S.tdStyle, textAlign: 'center' }}>{item.status_after ? <StatusBadge status={item.status_after} /> : '-'}</td>
      <td style={{ ...S.tdStyle, color: ok ? '#34d399' : '#f87171' }}>{item.message}</td>
      <td style={{ ...S.tdStyle, textAlign: 'center', fontSize: 11, color: '#64748b' }}>{item.time}</td>
    </tr>
  );
}

export default function ScanPage() {
  const [uid,       setUid]       = useState('');
  const [tonbag,    setTonbag]    = useState(null);   // 조회된 톤백 정보
  const [loading,   setLoading]   = useState(false);
  const [history,   setHistory]   = useState([]);
  const [toast,     setToast]     = useState(null);
  const [newLoc,    setNewLoc]    = useState('');     // 위치이동 목적지
  const [reason,    setReason]    = useState('기타'); // 반품 사유
  const [showMove,  setShowMove]  = useState(false);
  const [showReturn,setShowReturn]= useState(false);
  const inputRef = useRef(null);
  const toastRef = useRef(null);

  useEffect(() => { inputRef.current?.focus(); }, []);

  const showToast = (msg, ok) => {
    setToast({ message: msg, ok });
    if (toastRef.current) clearTimeout(toastRef.current);
    toastRef.current = setTimeout(() => setToast(null), 2500);
  };

  const addHist = (item) => setHistory(prev => [item, ...prev].slice(0, 50));

  const now = () => new Date().toTimeString().slice(0, 8);

  // ── 톤백 조회 ───────────────────────────────────────────────────────────
  const handleLookup = async (val = uid) => {
    const v = val.trim();
    if (!v) return;
    setLoading(true);
    setTonbag(null);
    setShowMove(false);
    setShowReturn(false);
    try {
      const r = await fetch(`${BASE}/search/unified?keyword=${encodeURIComponent(v)}&page_size=1`);
      const d = await r.json();
      const row = d.rows?.[0];
      if (row) {
        setTonbag(row);
      } else {
        showToast(`[${v}] 톤백을 찾을 수 없습니다.`, false);
        addHist({ uid: v, lot_no: '-', action: '조회', status_before: null, status_after: null, message: '톤백 없음', success: false, time: now() });
      }
    } catch (e) {
      showToast(`조회 오류: ${e.message}`, false);
    }
    setLoading(false);
  };

  const handleKey = (e) => {
    if (e.key === 'Enter') handleLookup();
  };

  const clear = () => { setUid(''); setTonbag(null); setShowMove(false); setShowReturn(false); inputRef.current?.focus(); };

  // ── 출고확정 (PICKED → OUTBOUND) ────────────────────────────────────────
  const doOutbound = async () => {
    if (!tonbag) return;
    if (tonbag.status !== 'PICKED') { showToast(`출고확정은 PICKED 상태만 가능 (현재: ${tonbag.status})`, false); return; }
    setLoading(true);
    try {
      const r = await fetch(`${BASE}/outbound/execute`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          items: [{ lot_no: tonbag.lot_no, sub_lt: tonbag.sub_lt || 0, tonbag_uid: tonbag.tonbag_uid }],
          customer: tonbag.customer || 'SCAN',
          source: 'SCAN',
        }),
      });
      const d = await r.json();
      const ok = d.success;
      showToast(ok ? `✅ 출고확정 완료: ${tonbag.lot_no}` : `❌ ${d.message}`, ok);
      addHist({ uid: tonbag.tonbag_uid, lot_no: tonbag.lot_no, action: '출고확정', status_before: 'PICKED', status_after: ok ? 'OUTBOUND' : 'PICKED', message: d.message || '', success: ok, time: now() });
      if (ok) {
        addRecentFile({ filename: `${tonbag.lot_no} 출고확정`, type: '스캔', path: '/scan' });
        clear();
      }
    } catch (e) { showToast(`오류: ${e.message}`, false); }
    setLoading(false);
  };

  // ── 반품등록 (OUTBOUND → RETURN) ────────────────────────────────────────
  const doReturn = async () => {
    if (!tonbag) return;
    if (!['OUTBOUND', 'SOLD'].includes(tonbag.status)) { showToast(`반품등록은 OUTBOUND 상태만 가능 (현재: ${tonbag.status})`, false); return; }
    setLoading(true);
    try {
      const r = await fetch(`${BASE}/return/single`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lot_no: tonbag.lot_no, sub_lt: tonbag.sub_lt || 0, reason_code: reason, note: `SCAN by ${now()}` }),
      });
      const d = await r.json();
      const ok = d.success;
      showToast(ok ? `🔄 반품등록 완료: ${tonbag.lot_no}` : `❌ ${d.message}`, ok);
      addHist({ uid: tonbag.tonbag_uid, lot_no: tonbag.lot_no, action: '반품등록', status_before: 'OUTBOUND', status_after: ok ? 'RETURN' : 'OUTBOUND', message: d.message || '', success: ok, time: now() });
      if (ok) {
        addRecentFile({ filename: `${tonbag.lot_no} 반품등록`, type: '스캔', path: '/scan' });
        setShowReturn(false);
        clear();
      }
    } catch (e) { showToast(`오류: ${e.message}`, false); }
    setLoading(false);
  };

  // ── 재입고 (RETURN → AVAILABLE) ─────────────────────────────────────────
  const doReinbound = async () => {
    if (!tonbag) return;
    if (tonbag.status !== 'RETURN') { showToast(`재입고는 RETURN 상태만 가능 (현재: ${tonbag.status})`, false); return; }
    setLoading(true);
    try {
      const r = await fetch(`${BASE}/return/bulk-confirm`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items: [{ lot_no: tonbag.lot_no, sub_lt: tonbag.sub_lt || 0 }] }),
      });
      const d = await r.json();
      const ok = d.success;
      showToast(ok ? `📦 재입고 완료: ${tonbag.lot_no}` : `❌ ${d.message}`, ok);
      addHist({ uid: tonbag.tonbag_uid, lot_no: tonbag.lot_no, action: '재입고', status_before: 'RETURN', status_after: ok ? 'AVAILABLE' : 'RETURN', message: d.message || '', success: ok, time: now() });
      if (ok) {
        addRecentFile({ filename: `${tonbag.lot_no} 재입고`, type: '스캔', path: '/scan' });
        clear();
      }
    } catch (e) { showToast(`오류: ${e.message}`, false); }
    setLoading(false);
  };

  // ── 위치이동 ─────────────────────────────────────────────────────────────
  const doMove = async () => {
    if (!tonbag || !newLoc.trim()) { showToast('목적지 위치를 입력하세요.', false); return; }
    setLoading(true);
    try {
      const r = await fetch(`${BASE}/location-bulk/single-update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lot_no: tonbag.lot_no, sub_lt: tonbag.sub_lt || 0, location: newLoc.trim(), operator: 'SCAN' }),
      });
      const d = await r.json();
      const ok = d.success;
      showToast(ok ? `🔀 위치이동: ${tonbag.location} → ${newLoc}` : `❌ ${d.message}`, ok);
      addHist({ uid: tonbag.tonbag_uid, lot_no: tonbag.lot_no, action: '위치이동', status_before: tonbag.status, status_after: tonbag.status, message: `${tonbag.location || '?'} → ${newLoc}`, success: ok, time: now() });
      if (ok) {
        addRecentFile({ filename: `${tonbag.lot_no} 위치 ${newLoc}`, type: '스캔', path: '/scan' });
        setShowMove(false);
        setNewLoc('');
        clear();
      }
    } catch (e) { showToast(`오류: ${e.message}`, false); }
    setLoading(false);
  };

  const handleAction = (action) => {
    if (!tonbag) { showToast('먼저 톤백을 스캔하세요.', false); return; }
    setShowMove(action === 'move');
    setShowReturn(action === 'return');
    if (action === 'outbound')  doOutbound();
    if (action === 'reinbound') doReinbound();
  };

  return (
    <div style={S.wrap}>
      <h2 style={{ color: '#f1f5f9', marginBottom: 4 }}>📷 Scan</h2>
      <p style={{ fontSize: 12, color: '#64748b', marginBottom: 16 }}>
        바코드/QR 스캔 또는 직접 입력 후 Enter. 4버튼으로 출고확정/반품/재입고/위치이동 처리.
      </p>

      {/* 스캔 입력 */}
      <div style={S.card}>
        <div style={S.title}>📷 바코드 / QR 스캔 입력</div>
        <div style={{ display: 'flex', gap: 8 }}>
          <input
            ref={inputRef}
            style={S.input}
            placeholder="톤백 UID / LOT NO 스캔 또는 입력 후 Enter"
            value={uid}
            onChange={e => setUid(e.target.value)}
            onKeyDown={handleKey}
            autoFocus
          />
          <button onClick={() => handleLookup()} disabled={loading || !uid.trim()}
            style={{ padding: '9px 18px', background: uid.trim() ? '#2563eb' : '#334155', color: uid.trim() ? '#fff' : '#64748b', border: 'none', borderRadius: 6, cursor: uid.trim() ? 'pointer' : 'not-allowed', fontSize: 13, fontWeight: 600, whiteSpace: 'nowrap' }}>
            🔍 조회
          </button>
          <button onClick={clear}
            style={{ padding: '9px 12px', background: '#334155', color: '#94a3b8', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 13 }}>
            🗑
          </button>
        </div>
      </div>

      {/* 톤백 정보 */}
      {tonbag && (
        <div style={{ ...S.card, border: '1px solid #38bdf8' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <div style={{ ...S.title, color: '#38bdf8' }}>📦 톤백 정보</div>
            <StatusBadge status={tonbag.status} />
          </div>
          <div style={S.infoRow}>
            {[
              ['LOT NO',   tonbag.lot_no],
              ['UID',      tonbag.tonbag_uid],
              ['제품',     tonbag.product_name],
              ['위치',     tonbag.location || '-'],
              ['중량',     tonbag.weight_kg ? `${Number(tonbag.weight_kg).toLocaleString()}kg` : '-'],
              ['SAP NO',   tonbag.sap_no || '-'],
            ].map(([k, v]) => (
              <div key={k} style={S.infoItem}>
                <span style={S.infoKey}>{k}</span>
                <span style={S.infoVal}>{v}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 4버튼 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10, marginBottom: 14 }}>
        {BTN_DEFS.map(b => (
          <button key={b.action}
            onClick={() => handleAction(b.action)}
            disabled={loading}
            title={b.desc}
            style={{
              padding: '14px 8px', background: tonbag ? b.color : '#334155',
              color: tonbag ? '#fff' : '#64748b',
              border: 'none', borderRadius: 8, cursor: tonbag && !loading ? 'pointer' : 'not-allowed',
              fontSize: 13, fontWeight: 700, textAlign: 'center',
              transition: 'all 0.15s',
            }}
            onMouseEnter={e => { if (tonbag) e.currentTarget.style.background = b.hover; }}
            onMouseLeave={e => { e.currentTarget.style.background = tonbag ? b.color : '#334155'; }}
          >
            {b.label}
            <div style={{ fontSize: 10, fontWeight: 400, marginTop: 3, opacity: 0.8 }}>{b.desc}</div>
          </button>
        ))}
      </div>

      {/* 반품 사유 입력 */}
      {showReturn && tonbag && (
        <div style={{ ...S.card, border: '1px solid #14b8a6' }}>
          <div style={{ ...S.title, color: '#14b8a6' }}>🔄 반품 사유 선택</div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
            {REASON_CODES.map(rc => (
              <button key={rc}
                onClick={() => setReason(rc)}
                style={{ padding: '6px 14px', background: reason === rc ? '#14b8a6' : '#334155', color: reason === rc ? '#fff' : '#94a3b8', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 12, fontWeight: reason === rc ? 700 : 400 }}>
                {rc}
              </button>
            ))}
            <button onClick={doReturn} disabled={loading}
              style={{ padding: '6px 18px', background: '#ef4444', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 12, fontWeight: 700, marginLeft: 8 }}>
              {loading ? '처리 중...' : '반품 처리'}
            </button>
            <button onClick={() => setShowReturn(false)}
              style={{ padding: '6px 10px', background: '#475569', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 12 }}>
              취소
            </button>
          </div>
        </div>
      )}

      {/* 위치이동 입력 */}
      {showMove && tonbag && (
        <div style={{ ...S.card, border: '1px solid #0ea5e9' }}>
          <div style={{ ...S.title, color: '#0ea5e9' }}>🔀 이동 목적지 입력</div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <span style={{ fontSize: 12, color: '#64748b' }}>현재: <b style={{ color: '#f1f5f9' }}>{tonbag.location || '미지정'}</b></span>
            <span style={{ color: '#334155' }}>→</span>
            <input
              placeholder="목적지 위치 입력 (예: A-01-03)"
              value={newLoc}
              onChange={e => setNewLoc(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && doMove()}
              style={{ ...S.input, width: 220 }}
              autoFocus
            />
            <button onClick={doMove} disabled={loading || !newLoc.trim()}
              style={{ padding: '8px 18px', background: newLoc.trim() ? '#0ea5e9' : '#334155', color: '#fff', border: 'none', borderRadius: 6, cursor: newLoc.trim() ? 'pointer' : 'not-allowed', fontSize: 12, fontWeight: 700 }}>
              {loading ? '처리 중...' : '이동'}
            </button>
            <button onClick={() => { setShowMove(false); setNewLoc(''); }}
              style={{ padding: '8px 10px', background: '#475569', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 12 }}>
              취소
            </button>
          </div>
        </div>
      )}

      {/* 스캔 이력 */}
      {history.length > 0 && (
        <div style={S.card}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <div style={S.title}>📋 스캔 이력 (최근 {history.length}건)</div>
            <button onClick={() => setHistory([])}
              style={{ padding: '3px 10px', fontSize: 11, background: '#334155', color: '#94a3b8', border: 'none', borderRadius: 4, cursor: 'pointer' }}>
              초기화
            </button>
          </div>
          <div style={{ overflow: 'auto', maxHeight: 260 }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  {['No.','UID','LOT NO','액션','이전상태','','이후상태','결과','시간'].map(h => (
                    <th key={h} style={S.thStyle}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {history.map((item, i) => <HistRow key={i} item={item} idx={i} />)}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {loading && (
        <div style={{ textAlign: 'center', color: '#64748b', fontSize: 13, padding: 12 }}>처리 중...</div>
      )}

      {toast && <Toast message={toast.message} ok={toast.ok} />}
    </div>
  );
}
