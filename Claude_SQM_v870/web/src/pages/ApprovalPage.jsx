import { useState, useEffect, useCallback } from 'react';

const BASE = '/api/approval';

const thStyle = {
  padding: '7px 10px', textAlign: 'left', background: '#1e293b',
  borderBottom: '2px solid #334155', fontSize: 11, fontWeight: 700,
  color: '#94a3b8', whiteSpace: 'nowrap', position: 'sticky', top: 0,
};
const tdStyle = { padding: '6px 10px', borderBottom: '1px solid #1e293b', fontSize: 12, color: '#e2e8f0', whiteSpace: 'nowrap' };
const tdC = { ...tdStyle, textAlign: 'center' };
const tdR = { ...tdStyle, textAlign: 'right' };

const TABS = [
  { key: 'queue',   label: '✅ 승인 대기' },
  { key: 'history', label: '📜 승인 이력' },
];

function StatusBadge({ status }) {
  const map = {
    APPROVED:        { bg: '#064e3b', fg: '#34d399' },
    REJECTED:        { bg: '#450a0a', fg: '#f87171' },
    PENDING_APPROVAL:{ bg: '#3b2a00', fg: '#fbbf24' },
  };
  const c = map[status] || { bg: '#1e293b', fg: '#94a3b8' };
  return (
    <span style={{
      display: 'inline-block', padding: '2px 8px', borderRadius: 999,
      fontSize: 10, fontWeight: 700, background: c.bg, color: c.fg,
    }}>{status || '-'}</span>
  );
}

function fmt(v) {
  const n = Number(v || 0);
  return n ? n.toLocaleString(undefined, { maximumFractionDigits: 3 }) : '0';
}

// ── 승인 대기 탭 ─────────────────────────────────────────────────────────────
function QueueTab() {
  const [rows,    setRows]    = useState([]);
  const [total,   setTotal]   = useState(0);
  const [page,    setPage]    = useState(1);
  const [keyword, setKeyword] = useState('');
  const [selected,setSelected]= useState(new Set());
  const [loading, setLoading] = useState(false);
  const [reason,  setReason]  = useState('');
  const [msg,     setMsg]     = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const p = new URLSearchParams({ page, page_size: 50 });
      if (keyword) p.set('keyword', keyword);
      const r = await fetch(`${BASE}/queue?${p}`);
      const d = await r.json();
      setRows(d.rows || []);
      setTotal(d.total || 0);
    } catch { setMsg({ ok: false, text: '조회 실패' }); }
    setLoading(false);
  }, [page, keyword]);

  useEffect(() => { load(); }, [load]);

  const toggleAll = () => {
    if (selected.size === rows.length) setSelected(new Set());
    else setSelected(new Set(rows.map(r => r.id)));
  };
  const toggleOne = (id) => {
    const s = new Set(selected);
    s.has(id) ? s.delete(id) : s.add(id);
    setSelected(s);
  };

  const doAction = async (action) => {
    if (!selected.size) { setMsg({ ok: false, text: '항목을 선택하세요.' }); return; }
    const label = action === 'approve' ? '승인' : '반려';
    if (!window.confirm(`선택 ${selected.size}건을 ${label} 처리하시겠습니까?`)) return;
    setLoading(true); setMsg(null);
    try {
      const r = await fetch(`${BASE}/${action}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids: Array.from(selected), reason }),
      });
      const d = await r.json();
      setMsg({ ok: d.success, text: d.message });
      if (d.success) { setSelected(new Set()); load(); }
    } catch (e) { setMsg({ ok: false, text: e.message }); }
    setLoading(false);
  };

  const doApplyApproved = async () => {
    if (!window.confirm('APPROVED 상태 전체를 예약 반영(RESERVED)하시겠습니까?')) return;
    setLoading(true); setMsg(null);
    try {
      const r = await fetch(`${BASE}/apply-approved`, { method: 'POST' });
      const d = await r.json();
      setMsg({ ok: d.success, text: d.message });
      if (d.success) load();
    } catch (e) { setMsg({ ok: false, text: e.message }); }
    setLoading(false);
  };

  const totalPages = Math.max(1, Math.ceil(total / 50));

  return (
    <div>
      {/* 검색 + 액션 버튼 */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 12, flexWrap: 'wrap', alignItems: 'center' }}>
        <input
          placeholder="LOT / 고객 / Sale Ref 검색"
          value={keyword}
          onChange={e => { setKeyword(e.target.value); setPage(1); }}
          style={{ padding: '6px 10px', fontSize: 12, background: '#0f172a', border: '1px solid #334155', borderRadius: 6, color: '#f1f5f9', width: 220 }}
        />
        <input
          placeholder="사유 입력 (선택)"
          value={reason}
          onChange={e => setReason(e.target.value)}
          style={{ padding: '6px 10px', fontSize: 12, background: '#0f172a', border: '1px solid #334155', borderRadius: 6, color: '#f1f5f9', width: 180 }}
        />
        <button onClick={() => doAction('approve')} disabled={loading || !selected.size}
          style={{ padding: '6px 14px', background: selected.size ? '#22c55e' : '#334155', color: selected.size ? '#fff' : '#64748b', border: 'none', borderRadius: 6, cursor: selected.size ? 'pointer' : 'not-allowed', fontSize: 12, fontWeight: 600 }}>
          ✅ 승인 ({selected.size})
        </button>
        <button onClick={() => doAction('reject')} disabled={loading || !selected.size}
          style={{ padding: '6px 14px', background: selected.size ? '#ef4444' : '#334155', color: selected.size ? '#fff' : '#64748b', border: 'none', borderRadius: 6, cursor: selected.size ? 'pointer' : 'not-allowed', fontSize: 12, fontWeight: 600 }}>
          ❌ 반려 ({selected.size})
        </button>
        <button onClick={doApplyApproved} disabled={loading}
          style={{ padding: '6px 14px', background: '#8b5cf6', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 12, fontWeight: 600 }}>
          📌 예약 반영 (승인분)
        </button>
        <span style={{ fontSize: 11, color: '#64748b' }}>Total: {total}</span>
      </div>

      {msg && (
        <div style={{ padding: '8px 12px', borderRadius: 6, marginBottom: 10, fontSize: 12,
          background: msg.ok ? '#064e3b' : '#450a0a', color: msg.ok ? '#34d399' : '#f87171',
          border: `1px solid ${msg.ok ? '#065f46' : '#7f1d1d'}` }}>
          {msg.text}
        </div>
      )}

      {loading && <div style={{ padding: 12, color: '#64748b', fontSize: 13 }}>Loading...</div>}

      {!loading && (
        <div style={{ overflow: 'auto', maxHeight: '60vh', border: '1px solid #334155', borderRadius: 8 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={{ ...thStyle, textAlign: 'center', width: 40 }}>
                  <input type="checkbox" checked={selected.size === rows.length && rows.length > 0}
                    onChange={toggleAll} />
                </th>
                <th style={thStyle}>ID</th>
                <th style={thStyle}>LOT NO</th>
                <th style={thStyle}>제품</th>
                <th style={thStyle}>고객</th>
                <th style={thStyle}>Sale Ref</th>
                <th style={{ ...thStyle, textAlign: 'right' }}>QTY(MT)</th>
                <th style={{ ...thStyle, textAlign: 'center' }}>출고일</th>
                <th style={{ ...thStyle, textAlign: 'center' }}>상태</th>
                <th style={{ ...thStyle, textAlign: 'center' }}>등록일</th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 ? (
                <tr><td colSpan={10} style={{ ...tdC, padding: 24, color: '#475569' }}>
                  승인 대기 건이 없습니다.
                </td></tr>
              ) : rows.map(r => (
                <tr key={r.id}
                  style={{ background: selected.has(r.id) ? '#1a2d1a' : '' }}
                  onMouseEnter={e => { if (!selected.has(r.id)) e.currentTarget.style.background = '#1e293b'; }}
                  onMouseLeave={e => { if (!selected.has(r.id)) e.currentTarget.style.background = ''; }}
                >
                  <td style={{ ...tdC, width: 40 }}>
                    <input type="checkbox" checked={selected.has(r.id)}
                      onChange={() => toggleOne(r.id)} />
                  </td>
                  <td style={{ ...tdC, color: '#64748b' }}>{r.id}</td>
                  <td style={{ ...tdStyle, color: '#38bdf8', fontWeight: 600 }}>{r.lot_no}</td>
                  <td style={{ ...tdStyle, color: '#94a3b8' }}>{r.product || '-'}</td>
                  <td style={tdStyle}>{r.customer || '-'}</td>
                  <td style={tdStyle}>{r.sale_ref  || '-'}</td>
                  <td style={tdR}>{fmt(r.qty_mt)}</td>
                  <td style={tdC}>{r.outbound_date || '-'}</td>
                  <td style={tdC}><StatusBadge status={r.workflow_status} /></td>
                  <td style={{ ...tdC, color: '#64748b', fontSize: 11 }}>{(r.created_at || '').slice(0, 10)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* 페이지네이션 */}
      <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginTop: 8, fontSize: 12 }}>
        <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}
          style={{ padding: '4px 10px', cursor: page > 1 ? 'pointer' : 'not-allowed' }}>Prev</button>
        <span style={{ color: '#94a3b8' }}>{page} / {totalPages}</span>
        <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}
          style={{ padding: '4px 10px', cursor: page < totalPages ? 'pointer' : 'not-allowed' }}>Next</button>
      </div>
    </div>
  );
}

// ── 승인 이력 탭 ─────────────────────────────────────────────────────────────
function HistoryTab() {
  const [rows,    setRows]    = useState([]);
  const [total,   setTotal]   = useState(0);
  const [page,    setPage]    = useState(1);
  const [lotNo,   setLotNo]   = useState('');
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const p = new URLSearchParams({ page, page_size: 50 });
      if (lotNo) p.set('lot_no', lotNo);
      const r = await fetch(`${BASE}/history?${p}`);
      const d = await r.json();
      setRows(d.rows || []);
      setTotal(d.total || 0);
    } catch {}
    setLoading(false);
  }, [page, lotNo]);

  useEffect(() => { load(); }, [load]);

  const totalPages = Math.max(1, Math.ceil(total / 50));

  return (
    <div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12, alignItems: 'center' }}>
        <input placeholder="LOT No 검색" value={lotNo}
          onChange={e => { setLotNo(e.target.value); setPage(1); }}
          style={{ padding: '6px 10px', fontSize: 12, background: '#0f172a', border: '1px solid #334155', borderRadius: 6, color: '#f1f5f9', width: 180 }} />
        <span style={{ fontSize: 11, color: '#64748b' }}>Total: {total}</span>
      </div>

      {loading && <div style={{ padding: 12, color: '#64748b' }}>Loading...</div>}

      {!loading && (
        <div style={{ overflow: 'auto', maxHeight: '60vh', border: '1px solid #334155', borderRadius: 8 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={thStyle}>LOT NO</th>
                <th style={thStyle}>고객</th>
                <th style={thStyle}>Sale Ref</th>
                <th style={{ ...thStyle, textAlign: 'center' }}>처리 결과</th>
                <th style={thStyle}>처리자</th>
                <th style={thStyle}>사유</th>
                <th style={{ ...thStyle, textAlign: 'center' }}>처리일</th>
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 ? (
                <tr><td colSpan={7} style={{ ...tdC, padding: 24, color: '#475569' }}>이력이 없습니다.</td></tr>
              ) : rows.map((r, i) => (
                <tr key={i}
                  onMouseEnter={e => e.currentTarget.style.background = '#1e293b'}
                  onMouseLeave={e => e.currentTarget.style.background = ''}>
                  <td style={{ ...tdStyle, color: '#38bdf8', fontWeight: 600 }}>{r.lot_no}</td>
                  <td style={tdStyle}>{r.customer || '-'}</td>
                  <td style={tdStyle}>{r.sale_ref  || '-'}</td>
                  <td style={tdC}><StatusBadge status={r.status} /></td>
                  <td style={{ ...tdStyle, color: '#94a3b8' }}>{r.actor || '-'}</td>
                  <td style={{ ...tdStyle, color: '#64748b' }}>{r.reason || '-'}</td>
                  <td style={{ ...tdC, fontSize: 11, color: '#64748b' }}>{(r.created_at || '').slice(0, 16)}</td>
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

// ── 메인 페이지 ──────────────────────────────────────────────────────────────
export default function ApprovalPage() {
  const [tab, setTab] = useState('queue');
  return (
    <div style={{ padding: 24 }}>
      <h2 style={{ color: '#f1f5f9', marginBottom: 4 }}>✅ Allocation 승인 관리</h2>
      <p style={{ fontSize: 12, color: '#64748b', marginBottom: 16 }}>
        PENDING_APPROVAL 상태의 Allocation 계획을 승인하거나 반려합니다.
        승인 후 [예약 반영] 버튼으로 실제 톤백을 RESERVED 처리합니다.
      </p>

      {/* 탭 */}
      <div style={{ display: 'flex', borderBottom: '2px solid #334155', marginBottom: 16 }}>
        {TABS.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)} style={{
            padding: '8px 20px', fontSize: 13, fontWeight: tab === t.key ? 700 : 400,
            color: tab === t.key ? '#38bdf8' : '#64748b',
            borderBottom: tab === t.key ? '2px solid #38bdf8' : '2px solid transparent',
            background: 'none', border: 'none', cursor: 'pointer', marginBottom: -2,
          }}>{t.label}</button>
        ))}
      </div>

      {tab === 'queue'   && <QueueTab />}
      {tab === 'history' && <HistoryTab />}
    </div>
  );
}
