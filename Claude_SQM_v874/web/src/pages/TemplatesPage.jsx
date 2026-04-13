import { useState, useEffect, useCallback } from 'react';

const TABS = [
  { key: 'inbound',  label: '📥 입고 파싱 템플릿' },
  { key: 'picking',  label: '📋 피킹 템플릿' },
  { key: 'move',     label: '📦 대량 이동 승인' },
  { key: 'swap',     label: '🔄 Swap 리포트' },
];

// ── 공통 스타일 ──────────────────────────────────────────────────────────────
const cardS = { background: '#1e293b', border: '1px solid #334155', borderRadius: 8, padding: '16px 20px', marginBottom: 12 };
const thS   = { padding: '7px 10px', background: '#0f172a', color: '#64748b', fontWeight: 700, fontSize: 11, textAlign: 'left', borderBottom: '2px solid #334155', whiteSpace: 'nowrap', position: 'sticky', top: 0 };
const tdS   = { padding: '6px 10px', borderBottom: '1px dashed rgba(51,65,85,0.3)', fontSize: 12, color: '#e2e8f0', whiteSpace: 'nowrap' };
const tdC   = { ...tdS, textAlign: 'center' };
const inputS = { padding: '7px 10px', fontSize: 12, background: '#0f172a', border: '1px solid #334155', borderRadius: 6, color: '#f1f5f9', width: '100%', boxSizing: 'border-box' };
const labelS = { fontSize: 11, color: '#64748b', display: 'block', marginBottom: 3 };
const btnS   = (c, dis) => ({ padding: '7px 16px', border: 'none', borderRadius: 6, background: dis ? '#334155' : c, color: dis ? '#64748b' : '#fff', fontSize: 12, fontWeight: 600, cursor: dis ? 'not-allowed' : 'pointer' });

function Toast({ msg, ok }) {
  if (!msg) return null;
  return (
    <div style={{ position: 'fixed', bottom: 28, left: '50%', transform: 'translateX(-50%)', padding: '10px 24px', borderRadius: 8, fontSize: 13, fontWeight: 600, zIndex: 9999, background: ok ? '#064e3b' : '#450a0a', color: ok ? '#34d399' : '#f87171' }}>
      {msg}
    </div>
  );
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 1. 입고 파싱 템플릿 탭
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const INBOUND_INIT = {
  template_id: '', template_name: '', carrier_id: '', bag_weight_kg: 500,
  product_hint: '', weight_format: '', bl_format: '',
  gemini_hint_packing: '', gemini_hint_invoice: '', gemini_hint_bl: '',
  note: '', is_active: 1,
};

function InboundTplTab({ showToast }) {
  const [rows,    setRows]    = useState([]);
  const [form,    setForm]    = useState(INBOUND_INIT);
  const [editing, setEditing] = useState(false);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    const r = await fetch('/api/templates/inbound/list?active_only=false');
    const d = await r.json();
    setRows(d.rows || []);
  }, []);

  useEffect(() => { load(); }, [load]);

  const sf = (k, v) => setForm(p => ({ ...p, [k]: v }));

  const save = async () => {
    setLoading(true);
    try {
      const r = await fetch('/api/templates/inbound/save', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });
      const d = await r.json();
      showToast(d.message || '저장 완료', d.success !== false);
      if (d.success !== false) { setEditing(false); setForm(INBOUND_INIT); load(); }
    } catch (e) { showToast(`❌ ${e.message}`, false); }
    setLoading(false);
  };

  const del = async (id) => {
    if (!window.confirm(`템플릿 '${id}'를 비활성화하시겠습니까?`)) return;
    await fetch(`/api/templates/inbound/${id}`, { method: 'DELETE' });
    showToast('비활성화 완료', true); load();
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
        <span style={{ fontSize: 12, color: '#64748b' }}>선사별 입고 PDF 파싱 패턴 (BL번호 형식, Gemini 힌트 등)</span>
        <button style={btnS('#2563eb', false)} onClick={() => { setForm(INBOUND_INIT); setEditing(true); }}>
          ＋ 신규 템플릿
        </button>
      </div>

      {/* 폼 */}
      {editing && (
        <div style={{ ...cardS, border: '1px solid #38bdf8' }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: '#38bdf8', marginBottom: 12 }}>
            {form.template_id ? '📝 템플릿 수정' : '➕ 신규 템플릿'}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, marginBottom: 10 }}>
            {[
              ['template_id',   '템플릿 ID *'],
              ['template_name', '템플릿명 *'],
              ['carrier_id',    '선사 코드'],
              ['bag_weight_kg', '톤백 중량(kg)'],
              ['product_hint',  '제품 힌트'],
              ['weight_format', '중량 형식'],
              ['bl_format',     'BL 번호 형식'],
            ].map(([k, l]) => (
              <div key={k}>
                <label style={labelS}>{l}</label>
                <input style={inputS} value={form[k] || ''} onChange={e => sf(k, e.target.value)} />
              </div>
            ))}
          </div>
          {[
            ['gemini_hint_packing', '📦 Gemini Packing 힌트'],
            ['gemini_hint_invoice', '🧾 Gemini Invoice 힌트'],
            ['gemini_hint_bl',      '📄 Gemini BL 힌트'],
            ['note',                '📝 메모'],
          ].map(([k, l]) => (
            <div key={k} style={{ marginBottom: 8 }}>
              <label style={labelS}>{l}</label>
              <textarea style={{ ...inputS, height: 48, resize: 'vertical' }}
                value={form[k] || ''} onChange={e => sf(k, e.target.value)} />
            </div>
          ))}
          <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
            <button style={btnS('#22c55e', loading)} disabled={loading} onClick={save}>
              {loading ? '저장 중...' : '💾 저장'}
            </button>
            <button style={btnS('#475569', false)} onClick={() => setEditing(false)}>취소</button>
          </div>
        </div>
      )}

      {/* 목록 */}
      <div style={{ overflow: 'auto', maxHeight: '55vh', border: '1px solid #334155', borderRadius: 8 }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              {['ID','템플릿명','선사','중량','제품힌트','BL형식','상태',''].map(h => (
                <th key={h} style={thS}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr><td colSpan={8} style={{ ...tdC, padding: 24, color: '#475569' }}>템플릿 없음</td></tr>
            ) : rows.map((r, i) => (
              <tr key={i}
                onMouseEnter={e => e.currentTarget.style.background = '#0f172a'}
                onMouseLeave={e => e.currentTarget.style.background = ''}>
                <td style={{ ...tdS, color: '#38bdf8', fontWeight: 600 }}>{r.template_id}</td>
                <td style={tdS}>{r.template_name}</td>
                <td style={tdC}>{r.carrier_id || '-'}</td>
                <td style={tdC}>{r.bag_weight_kg || '-'}</td>
                <td style={{ ...tdS, color: '#94a3b8' }}>{r.product_hint || '-'}</td>
                <td style={{ ...tdS, fontFamily: 'monospace', fontSize: 11 }}>{r.bl_format || '-'}</td>
                <td style={tdC}>
                  <span style={{ color: r.is_active ? '#34d399' : '#64748b', fontWeight: 600, fontSize: 11 }}>
                    {r.is_active ? '활성' : '비활성'}
                  </span>
                </td>
                <td style={tdC}>
                  <button onClick={() => { setForm({ ...INBOUND_INIT, ...r }); setEditing(true); }}
                    style={{ ...btnS('#334155', false), padding: '3px 8px', fontSize: 11, marginRight: 4 }}>수정</button>
                  <button onClick={() => del(r.template_id)}
                    style={{ ...btnS('#450a0a', false), padding: '3px 8px', fontSize: 11, color: '#f87171' }}>삭제</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 2. 피킹 템플릿 탭
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
const PICKING_INIT = {
  template_id: '', template_name: '', customer: '', customer_code: '',
  port_loading: '', port_discharge: '', delivery_terms: 'CIF',
  contact_person: '', contact_email: '',
  bag_weight_kg: 500, storage_location: '', note: '', is_active: 1,
};

function PickingTplTab({ showToast }) {
  const [rows,    setRows]    = useState([]);
  const [form,    setForm]    = useState(PICKING_INIT);
  const [editing, setEditing] = useState(false);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    const r = await fetch('/api/templates/picking/list?active_only=false');
    const d = await r.json();
    setRows(d.rows || []);
  }, []);

  useEffect(() => { load(); }, [load]);

  const sf = (k, v) => setForm(p => ({ ...p, [k]: v }));

  const save = async () => {
    setLoading(true);
    try {
      const r = await fetch('/api/templates/picking/save', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });
      const d = await r.json();
      showToast(d.message || '저장 완료', d.success !== false);
      if (d.success !== false) { setEditing(false); setForm(PICKING_INIT); load(); }
    } catch (e) { showToast(`❌ ${e.message}`, false); }
    setLoading(false);
  };

  const del = async (id) => {
    if (!window.confirm(`템플릿 '${id}'를 삭제하시겠습니까?`)) return;
    await fetch(`/api/templates/picking/${id}`, { method: 'DELETE' });
    showToast('삭제 완료', true); load();
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
        <span style={{ fontSize: 12, color: '#64748b' }}>고객사별 출고 정보 프로파일 (항구/조건/담당자)</span>
        <button style={btnS('#2563eb', false)} onClick={() => { setForm(PICKING_INIT); setEditing(true); }}>
          ＋ 신규 템플릿
        </button>
      </div>

      {editing && (
        <div style={{ ...cardS, border: '1px solid #38bdf8' }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: '#38bdf8', marginBottom: 12 }}>
            {form.template_id ? '📝 템플릿 수정' : '➕ 신규 템플릿'}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 10, marginBottom: 10 }}>
            {[
              ['template_id',    '템플릿 ID *'],
              ['template_name',  '템플릿명 *'],
              ['customer',       '고객사 *'],
              ['customer_code',  '고객 코드'],
              ['port_loading',   '선적항'],
              ['port_discharge', '양하항'],
              ['delivery_terms', '인도조건 (CIF/FOB)'],
              ['contact_person', '담당자'],
              ['contact_email',  '이메일'],
              ['bag_weight_kg',  '기본 톤백 중량(kg)'],
              ['storage_location','보관 위치'],
            ].map(([k, l]) => (
              <div key={k}>
                <label style={labelS}>{l}</label>
                <input style={inputS} value={form[k] || ''} onChange={e => sf(k, e.target.value)} />
              </div>
            ))}
          </div>
          <div style={{ marginBottom: 8 }}>
            <label style={labelS}>메모</label>
            <textarea style={{ ...inputS, height: 48, resize: 'vertical' }}
              value={form.note || ''} onChange={e => sf('note', e.target.value)} />
          </div>
          <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
            <button style={btnS('#22c55e', loading)} disabled={loading} onClick={save}>
              {loading ? '저장 중...' : '💾 저장'}
            </button>
            <button style={btnS('#475569', false)} onClick={() => setEditing(false)}>취소</button>
          </div>
        </div>
      )}

      <div style={{ overflow: 'auto', maxHeight: '55vh', border: '1px solid #334155', borderRadius: 8 }}>
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              {['ID','템플릿명','고객사','선적항','양하항','인도조건','담당자','상태',''].map(h => (
                <th key={h} style={thS}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 ? (
              <tr><td colSpan={9} style={{ ...tdC, padding: 24, color: '#475569' }}>템플릿 없음</td></tr>
            ) : rows.map((r, i) => (
              <tr key={i}
                onMouseEnter={e => e.currentTarget.style.background = '#0f172a'}
                onMouseLeave={e => e.currentTarget.style.background = ''}>
                <td style={{ ...tdS, color: '#38bdf8', fontWeight: 600 }}>{r.template_id}</td>
                <td style={tdS}>{r.template_name}</td>
                <td style={{ ...tdS, fontWeight: 600 }}>{r.customer}</td>
                <td style={tdC}>{r.port_loading || '-'}</td>
                <td style={tdC}>{r.port_discharge || '-'}</td>
                <td style={tdC}>{r.delivery_terms || '-'}</td>
                <td style={{ ...tdS, color: '#94a3b8' }}>{r.contact_person || '-'}</td>
                <td style={tdC}>
                  <span style={{ color: r.is_active ? '#34d399' : '#64748b', fontWeight: 600, fontSize: 11 }}>
                    {r.is_active ? '활성' : '비활성'}
                  </span>
                </td>
                <td style={tdC}>
                  <button onClick={() => { setForm({ ...PICKING_INIT, ...r }); setEditing(true); }}
                    style={{ ...btnS('#334155', false), padding: '3px 8px', fontSize: 11, marginRight: 4 }}>수정</button>
                  <button onClick={() => del(r.template_id)}
                    style={{ ...btnS('#450a0a', false), padding: '3px 8px', fontSize: 11, color: '#f87171' }}>삭제</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 3. 대량 이동 승인 탭
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function MoveApprovalTab({ showToast }) {
  const [pending, setPending] = useState([]);
  const [history, setHistory] = useState([]);
  const [subTab,  setSubTab]  = useState('pending');
  const [loading, setLoading] = useState(false);
  const [reason,  setReason]  = useState('');

  const loadPending = async () => {
    const r = await fetch('/api/move-approval/pending');
    const d = await r.json();
    setPending(d.rows || []);
  };
  const loadHistory = async () => {
    const r = await fetch('/api/move-approval/history');
    const d = await r.json();
    setHistory(d.rows || []);
  };

  useEffect(() => { loadPending(); loadHistory(); }, []);

  const doApprove = async (batch_id) => {
    if (!window.confirm(`배치 '${batch_id}'를 승인하시겠습니까?`)) return;
    setLoading(true);
    try {
      const r = await fetch('/api/move-approval/approve', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ batch_id }),
      });
      const d = await r.json();
      showToast(d.message, d.success !== false);
      loadPending(); loadHistory();
    } catch (e) { showToast(`❌ ${e.message}`, false); }
    setLoading(false);
  };

  const doReject = async (batch_id) => {
    const r2 = reason.trim() || '반려';
    if (!window.confirm(`배치 '${batch_id}'를 반려하시겠습니까?\n사유: ${r2}`)) return;
    setLoading(true);
    try {
      const r = await fetch('/api/move-approval/reject', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ batch_id, reason: r2 }),
      });
      const d = await r.json();
      showToast(d.message || '반려 완료', d.success !== false);
      loadPending(); loadHistory();
    } catch (e) { showToast(`❌ ${e.message}`, false); }
    setLoading(false);
  };

  return (
    <div>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 12 }}>
        {['pending','history'].map(t => (
          <button key={t} onClick={() => setSubTab(t)} style={{
            padding: '6px 14px', fontSize: 12, fontWeight: subTab === t ? 700 : 400,
            color: subTab === t ? '#38bdf8' : '#64748b',
            background: subTab === t ? '#0f172a' : 'none',
            border: `1px solid ${subTab === t ? '#38bdf8' : '#334155'}`,
            borderRadius: 6, cursor: 'pointer',
          }}>
            {t === 'pending' ? `⏳ 대기 (${pending.length})` : '📜 처리 이력'}
          </button>
        ))}
        <button style={btnS('#334155', false)} onClick={() => { loadPending(); loadHistory(); }}>🔄</button>
        {subTab === 'pending' && (
          <input placeholder="반려 사유 (선택)" value={reason} onChange={e => setReason(e.target.value)}
            style={{ ...inputS, width: 180 }} />
        )}
      </div>

      {subTab === 'pending' && (
        <div style={{ overflow: 'auto', maxHeight: '55vh', border: '1px solid #334155', borderRadius: 8 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                {['배치 ID','수량','사유','요청자','요청시각','비고',''].map(h => (
                  <th key={h} style={thS}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {pending.length === 0 ? (
                <tr><td colSpan={7} style={{ ...tdC, padding: 24, color: '#475569' }}>대기 중인 이동 요청 없음</td></tr>
              ) : pending.map((r, i) => {
                const row = typeof r === 'object' && !Array.isArray(r) ? r : {};
                return (
                  <tr key={i} onMouseEnter={e => e.currentTarget.style.background = '#0f172a'} onMouseLeave={e => e.currentTarget.style.background = ''}>
                    <td style={{ ...tdS, color: '#38bdf8', fontWeight: 600 }}>{row.batch_id}</td>
                    <td style={tdC}>{row.total_count}</td>
                    <td style={tdC}>{row.reason_code || '-'}</td>
                    <td style={tdS}>{row.submitted_by || '-'}</td>
                    <td style={{ ...tdC, fontSize: 11, color: '#64748b' }}>{(row.submitted_at || '').slice(0, 16)}</td>
                    <td style={{ ...tdS, color: '#94a3b8' }}>{row.note || '-'}</td>
                    <td style={tdC}>
                      <button onClick={() => doApprove(row.batch_id)} disabled={loading}
                        style={{ ...btnS('#22c55e', loading), padding: '3px 10px', fontSize: 11, marginRight: 4 }}>
                        ✅ 승인
                      </button>
                      <button onClick={() => doReject(row.batch_id)} disabled={loading}
                        style={{ ...btnS('#ef4444', loading), padding: '3px 10px', fontSize: 11 }}>
                        ❌ 반려
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {subTab === 'history' && (
        <div style={{ overflow: 'auto', maxHeight: '55vh', border: '1px solid #334155', borderRadius: 8 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                {['배치 ID','수량','사유','요청자','요청시각','처리결과'].map(h => (
                  <th key={h} style={thS}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {history.length === 0 ? (
                <tr><td colSpan={6} style={{ ...tdC, padding: 24, color: '#475569' }}>처리 이력 없음</td></tr>
              ) : history.map((r, i) => {
                const row = typeof r === 'object' && !Array.isArray(r) ? r : {};
                const ok  = row.status === 'APPROVED';
                return (
                  <tr key={i} onMouseEnter={e => e.currentTarget.style.background = '#0f172a'} onMouseLeave={e => e.currentTarget.style.background = ''}>
                    <td style={{ ...tdS, color: '#38bdf8', fontWeight: 600 }}>{row.batch_id}</td>
                    <td style={tdC}>{row.total_count}</td>
                    <td style={tdC}>{row.reason_code || '-'}</td>
                    <td style={tdS}>{row.submitted_by || '-'}</td>
                    <td style={{ ...tdC, fontSize: 11, color: '#64748b' }}>{(row.submitted_at || '').slice(0, 16)}</td>
                    <td style={tdC}>
                      <span style={{ color: ok ? '#34d399' : '#f87171', fontWeight: 700, fontSize: 11 }}>
                        {ok ? '✅ 승인' : '❌ 반려'}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 4. Swap 리포트 탭
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
function SwapTab({ showToast }) {
  const [rows,     setRows]     = useState([]);
  const [total,    setTotal]    = useState(0);
  const [page,     setPage]     = useState(1);
  const [lotNo,    setLotNo]    = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo,   setDateTo]   = useState('');
  const [loading,  setLoading]  = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    const p = new URLSearchParams({ page, page_size: 50 });
    if (lotNo)    p.set('lot_no',    lotNo);
    if (dateFrom) p.set('date_from', dateFrom);
    if (dateTo)   p.set('date_to',   dateTo);
    const r = await fetch(`/api/swap/list?${p}`);
    const d = await r.json();
    setRows(d.rows || []); setTotal(d.total || 0);
    setLoading(false);
  }, [page, lotNo, dateFrom, dateTo]);

  useEffect(() => { load(); }, [load]);

  const download = async () => {
    const p = new URLSearchParams();
    if (lotNo)    p.set('lot_no',    lotNo);
    if (dateFrom) p.set('date_from', dateFrom);
    if (dateTo)   p.set('date_to',   dateTo);
    try {
      const r = await fetch(`/api/swap/download?${p}`);
      if (!r.ok) throw new Error(await r.text());
      const blob = await r.blob();
      const href = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = href; a.download = 'SQM_Swap_리포트.xlsx';
      document.body.appendChild(a); a.click();
      setTimeout(() => { URL.revokeObjectURL(href); a.remove(); }, 500);
      showToast('✅ Swap 리포트 다운로드 완료', true);
    } catch (e) { showToast(`❌ ${e.message}`, false); }
  };

  const totalPages = Math.max(1, Math.ceil(total / 50));
  const keys       = rows.length > 0 ? Object.keys(rows[0] instanceof Object ? rows[0] : {}) : [];

  return (
    <div>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 12, flexWrap: 'wrap' }}>
        <input placeholder="LOT NO" value={lotNo} onChange={e => { setLotNo(e.target.value); setPage(1); }}
          style={{ ...inputS, width: 150 }} />
        <input type="date" value={dateFrom} onChange={e => { setDateFrom(e.target.value); setPage(1); }}
          style={{ ...inputS, width: 150 }} />
        <span style={{ color: '#475569' }}>~</span>
        <input type="date" value={dateTo} onChange={e => { setDateTo(e.target.value); setPage(1); }}
          style={{ ...inputS, width: 150 }} />
        <button style={btnS('#334155', false)} onClick={load}>🔄 검색</button>
        <button style={btnS('#16a34a', loading)} disabled={loading} onClick={download}>
          📥 Excel 다운로드
        </button>
        <span style={{ fontSize: 11, color: '#64748b' }}>Total: {total}</span>
      </div>

      {loading && <div style={{ padding: 12, color: '#64748b', fontSize: 13 }}>Loading...</div>}

      {!loading && (
        <div style={{ overflow: 'auto', maxHeight: '55vh', border: '1px solid #334155', borderRadius: 8 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                {rows.length > 0 && keys.map(k => (
                  <th key={k} style={thS}>{k}</th>
                ))}
                {rows.length === 0 && <th style={thS}>데이터</th>}
              </tr>
            </thead>
            <tbody>
              {rows.length === 0 ? (
                <tr><td colSpan={keys.length || 1} style={{ ...tdC, padding: 24, color: '#475569' }}>
                  Swap 이력 없음
                </td></tr>
              ) : rows.map((r, i) => (
                <tr key={i}
                  onMouseEnter={e => e.currentTarget.style.background = '#0f172a'}
                  onMouseLeave={e => e.currentTarget.style.background = ''}>
                  {keys.map(k => (
                    <td key={k} style={tdS}>{r[k] !== null && r[k] !== undefined ? String(r[k]) : '-'}</td>
                  ))}
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

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// 메인 페이지
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
export default function TemplatesPage() {
  const [tab,   setTab]   = useState('inbound');
  const [toast, setToast] = useState(null);

  const showToast = (msg, ok) => {
    setToast({ msg, ok });
    setTimeout(() => setToast(null), 3000);
  };

  return (
    <div style={{ padding: 24 }}>
      <h2 style={{ color: '#f1f5f9', marginBottom: 4 }}>🗂️ 템플릿 & 승인 관리</h2>
      <p style={{ fontSize: 12, color: '#64748b', marginBottom: 16 }}>
        입고/피킹 템플릿 관리 · 대량 이동 승인 · Swap 리포트
      </p>

      {/* 탭 */}
      <div style={{ display: 'flex', borderBottom: '2px solid #334155', marginBottom: 16 }}>
        {TABS.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)} style={{
            padding: '8px 20px', fontSize: 13,
            fontWeight: tab === t.key ? 700 : 400,
            color: tab === t.key ? '#38bdf8' : '#64748b',
            borderBottom: tab === t.key ? '2px solid #38bdf8' : '2px solid transparent',
            background: 'none', border: 'none', cursor: 'pointer', marginBottom: -2,
          }}>{t.label}</button>
        ))}
      </div>

      {tab === 'inbound' && <InboundTplTab showToast={showToast} />}
      {tab === 'picking' && <PickingTplTab showToast={showToast} />}
      {tab === 'move'    && <MoveApprovalTab showToast={showToast} />}
      {tab === 'swap'    && <SwapTab showToast={showToast} />}

      {toast && <Toast msg={toast.msg} ok={toast.ok} />}
    </div>
  );
}
