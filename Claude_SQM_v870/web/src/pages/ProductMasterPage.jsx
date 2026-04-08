import { useState, useEffect, useCallback } from 'react';

const BASE = '/api/products';
const thSt = { padding: '8px 10px', textAlign: 'center', background: '#f8fafc', borderBottom: '2px solid #e2e8f0', fontSize: 11, fontWeight: 700, whiteSpace: 'nowrap' };
const tdSt = { padding: '6px 10px', borderBottom: '1px solid #f1f5f9', fontSize: 12, whiteSpace: 'nowrap' };
const tdC  = { ...tdSt, textAlign: 'center' };
const inp  = { width: '100%', padding: '6px 10px', fontSize: 13, border: '1px solid #e2e8f0', borderRadius: 6, boxSizing: 'border-box' };
const lbl  = { fontSize: 12, color: '#475569', marginBottom: 4, display: 'block', fontWeight: 600 };
const btn  = (c, dis) => ({ padding: '7px 16px', fontSize: 12, fontWeight: 700, background: dis ? '#e2e8f0' : c, color: dis ? '#94a3b8' : '#fff', border: 'none', borderRadius: 6, cursor: dis ? 'not-allowed' : 'pointer' });
const EMPTY = { code: '', full_name: '', korean_name: '', tonbag_support: false };

export default function ProductMasterPage() {
  const [rows,       setRows]      = useState([]);
  const [loading,    setLoading]   = useState(false);
  const [form,       setForm]      = useState(EMPTY);
  const [editId,     setEditId]    = useState(null);
  const [msg,        setMsg]       = useState(null);
  const [activeOnly, setActiveOnly]= useState(true);

  const showMsg = (ok, text) => { setMsg({ ok, text }); setTimeout(() => setMsg(null), 3000); };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${BASE}/list?active_only=${activeOnly}`);
      const d = await r.json();
      setRows(d.rows || []);
    } catch { showMsg(false, '목록 조회 실패'); }
    setLoading(false);
  }, [activeOnly]);

  useEffect(() => { load(); }, [load]);

  const handleSelect = (row) => {
    setEditId(row.id);
    setForm({ code: row.code || '', full_name: row.full_name || '', korean_name: row.korean_name || '', tonbag_support: !!row.tonbag_support });
  };
  const handleClear = () => { setEditId(null); setForm(EMPTY); };

  const handleSave = async () => {
    if (!form.code || !form.full_name) { showMsg(false, 'Code와 영문명은 필수입니다.'); return; }
    try {
      const url    = editId ? `${BASE}/${editId}` : `${BASE}/create`;
      const method = editId ? 'PUT' : 'POST';
      const r = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(form) });
      const d = await r.json();
      if (d.success) { showMsg(true, d.message); handleClear(); load(); }
      else showMsg(false, d.detail || d.message || '저장 실패');
    } catch { showMsg(false, '저장 요청 실패'); }
  };

  const handleDelete = async (row) => {
    if (!window.confirm(`'${row.code}' 을(를) 비활성화하시겠습니까?`)) return;
    try {
      const r = await fetch(`${BASE}/${row.id}`, { method: 'DELETE' });
      const d = await r.json();
      showMsg(d.success, d.message || (d.success ? '완료' : '실패'));
      if (d.success) load();
    } catch { showMsg(false, '삭제 요청 실패'); }
  };

  return (
    <div style={{ padding: 24 }}>
      <h2 style={{ marginBottom: 20 }}>📦 제품 마스터 관리</h2>
      <div style={{ display: 'flex', gap: 20, alignItems: 'flex-start' }}>

        {/* 목록 */}
        <div style={{ flex: 1 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
            <span style={{ fontSize: 12, color: '#475569' }}>총 <b>{rows.length}</b>개</span>
            <label style={{ fontSize: 12, color: '#475569', display: 'flex', alignItems: 'center', gap: 4 }}>
              <input type="checkbox" checked={activeOnly} onChange={e => setActiveOnly(e.target.checked)} />
              활성만
            </label>
          </div>
          {loading && <div style={{ padding: 12, color: '#475569', fontSize: 12 }}>Loading...</div>}
          <div style={{ border: '1px solid #e2e8f0', borderRadius: 6, overflow: 'auto', maxHeight: '65vh' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 480 }}>
              <thead>
                <tr>
                  <th style={thSt}>CODE</th><th style={thSt}>영문명</th>
                  <th style={thSt}>한글명</th><th style={thSt}>톤백</th>
                  <th style={thSt}>기본</th><th style={thSt}>관리</th>
                </tr>
              </thead>
              <tbody>
                {rows.length === 0 && !loading
                  ? <tr><td colSpan={6} style={{ ...tdC, padding: 24, color: '#94a3b8' }}>등록된 제품이 없습니다.</td></tr>
                  : rows.map(row => (
                    <tr key={row.id || row.code}
                      style={{ background: editId === row.id ? '#eff6ff' : '' }}
                      onMouseEnter={e => { if (editId !== row.id) e.currentTarget.style.background = '#f8fafc'; }}
                      onMouseLeave={e => { if (editId !== row.id) e.currentTarget.style.background = ''; }}
                    >
                      <td style={{ ...tdC, fontWeight: 700, color: '#2563eb' }}>{row.code}</td>
                      <td style={tdSt}>{row.full_name}</td>
                      <td style={tdSt}>{row.korean_name || '-'}</td>
                      <td style={tdC}>{row.tonbag_support ? '✅' : '-'}</td>
                      <td style={tdC}>{row.is_default ? '⭐' : '-'}</td>
                      <td style={tdC}>
                        <button onClick={() => handleSelect(row)} style={{ ...btn('#0ea5e9', false), padding: '4px 10px', marginRight: 4 }}>수정</button>
                        {!row.is_default && (
                          <button onClick={() => handleDelete(row)} style={{ ...btn('#ef4444', false), padding: '4px 10px' }}>삭제</button>
                        )}
                      </td>
                    </tr>
                  ))
                }
              </tbody>
            </table>
          </div>
        </div>

        {/* 입력 폼 */}
        <div style={{ width: 280, background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 8, padding: 20, flexShrink: 0 }}>
          <h3 style={{ fontSize: 14, fontWeight: 700, marginBottom: 16 }}>{editId ? '✏️ 수정' : '➕ 추가'}</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div>
              <label style={lbl}>Code <span style={{ color: '#ef4444' }}>*</span></label>
              <input style={{ ...inp, textTransform: 'uppercase' }} value={form.code} maxLength={10}
                onChange={e => setForm(f => ({ ...f, code: e.target.value.toUpperCase() }))}
                placeholder="예: LC" disabled={!!editId} />
            </div>
            <div>
              <label style={lbl}>영문명 <span style={{ color: '#ef4444' }}>*</span></label>
              <input style={inp} value={form.full_name}
                onChange={e => setForm(f => ({ ...f, full_name: e.target.value }))}
                placeholder="예: LITHIUM CARBONATE" />
            </div>
            <div>
              <label style={lbl}>한글명</label>
              <input style={inp} value={form.korean_name}
                onChange={e => setForm(f => ({ ...f, korean_name: e.target.value }))}
                placeholder="예: 리튬카보네이트" />
            </div>
            <label style={{ ...lbl, display: 'flex', alignItems: 'center', gap: 6 }}>
              <input type="checkbox" checked={form.tonbag_support}
                onChange={e => setForm(f => ({ ...f, tonbag_support: e.target.checked }))} />
              톤백 지원
            </label>
          </div>
          <div style={{ display: 'flex', gap: 8, marginTop: 20 }}>
            <button onClick={handleSave} style={btn('#2563eb', false)}>{editId ? '수정 저장' : '추가'}</button>
            <button onClick={handleClear} style={{ ...btn('#64748b', false), background: '#f1f5f9', color: '#475569' }}>초기화</button>
          </div>
          {msg && (
            <div style={{ marginTop: 12, padding: '8px 12px', borderRadius: 6, fontSize: 12, background: msg.ok ? '#f0fdf4' : '#fef2f2', color: msg.ok ? '#166534' : '#991b1b', border: `1px solid ${msg.ok ? '#bbf7d0' : '#fecaca'}` }}>
              {msg.ok ? '✅' : '❌'} {msg.text}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
