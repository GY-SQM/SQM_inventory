import { useState } from 'react';
import Modal from './Modal';
import { addRecentFile } from '../utils/recentFiles';

const BASE = '/api';
const label = { fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 2 };
const input = { width: '100%', padding: 5, fontSize: 12, border: '1px solid #e2e8f0', borderRadius: 4 };
const thStyle = { padding: '6px 8px', textAlign: 'center', background: '#f8fafc', borderBottom: '2px solid #e2e8f0', fontSize: 11, fontWeight: 700 };
const tdStyle = { padding: '5px 8px', borderBottom: '1px solid #f1f5f9', fontSize: 12 };

export default function LocationMappingModal({ open, onClose }) {
  const [tab, setTab] = useState('single');
  const [result, setResult] = useState(null);

  const handleClose = () => { setResult(null); onClose(); };

  return (
    <Modal open={open} onClose={handleClose} title="위치 매핑" width={600}>
      <div style={{ display: 'flex', gap: 0, marginBottom: 12, borderBottom: '2px solid #e2e8f0' }}>
        {[{ key: 'single', label: '단건 입력' }, { key: 'excel', label: 'Excel 일괄' }].map(t => (
          <button key={t.key} onClick={() => { setTab(t.key); setResult(null); }} style={{
            padding: '6px 16px', fontSize: 12, fontWeight: tab === t.key ? 700 : 400,
            color: tab === t.key ? '#2563eb' : '#64748b',
            borderBottom: tab === t.key ? '2px solid #2563eb' : '2px solid transparent',
            background: 'none', border: 'none', cursor: 'pointer', marginBottom: -2,
          }}>{t.label}</button>
        ))}
      </div>
      {tab === 'single' && <SingleTab onResult={setResult} />}
      {tab === 'excel' && <ExcelTab onResult={setResult} />}
      {result && (
        <div style={{
          marginTop: 10, padding: 8, borderRadius: 6, fontSize: 12,
          background: result.success ? '#f0fdf4' : '#fef2f2',
          color: result.success ? '#166534' : '#991b1b',
        }}>{result.message}</div>
      )}
    </Modal>
  );
}

function SingleTab({ onResult }) {
  const [form, setForm] = useState({ lot_no: '', sub_lt: '', location: '' });
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    if (!form.lot_no || form.sub_lt === '' || !form.location) return;
    setLoading(true);
    try {
      const res = await fetch(`${BASE}/location/single-update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lot_no: form.lot_no, sub_lt: parseInt(form.sub_lt, 10), location: form.location }),
      });
      const data = await res.json();
      onResult(data);
      if (data.success) {
        addRecentFile({
          filename: `${form.lot_no} → ${form.location}`,
          type: '위치',
          path: '/inventory',
        });
      }
    } catch (e) {
      onResult({ success: false, message: e.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <label style={label}>LOT NO<input style={input} value={form.lot_no} onChange={e => setForm(f => ({ ...f, lot_no: e.target.value }))} /></label>
      <label style={label}>Sub LT<input type="number" min={0} style={input} value={form.sub_lt} onChange={e => setForm(f => ({ ...f, sub_lt: e.target.value }))} /></label>
      <label style={label}>위치코드<input style={input} value={form.location} onChange={e => setForm(f => ({ ...f, location: e.target.value }))} /></label>
      <button onClick={submit} disabled={loading}
        style={{ padding: '8px 20px', fontWeight: 700, fontSize: 13, background: '#2563eb', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer' }}>
        {loading ? '변경 중...' : '위치 변경'}
      </button>
    </div>
  );
}

function ExcelTab({ onResult }) {
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [lastFileName, setLastFileName] = useState('');

  const upload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setLastFileName(file.name);
    setLoading(true);
    setPreview(null);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const res = await fetch(`${BASE}/location/bulk-upload`, { method: 'POST', body: fd });
      const data = await res.json();
      setPreview(data);
    } catch (err) {
      setPreview({ parse_ok: false, errors: [err.message], rows: [] });
    } finally {
      setLoading(false);
    }
  };

  const confirm = async () => {
    if (!preview?.rows?.length) return;
    setLoading(true);
    try {
      const res = await fetch(`${BASE}/location/bulk-update`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items: preview.rows }),
      });
      const data = await res.json();
      onResult(data);
      if (data.success) {
        addRecentFile({
          filename: lastFileName || `위치 일괄 ${preview.rows.length}건`,
          type: '위치',
          path: '/tonbag',
        });
      }
    } catch (err) {
      onResult({ success: false, message: err.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <input type="file" accept=".xlsx,.xls" onChange={upload} style={{ fontSize: 12, marginBottom: 10 }} />
      {loading && <div style={{ color: '#475569', fontSize: 12 }}>처리 중...</div>}
      {preview?.errors?.length > 0 && (
        <div style={{ padding: 8, background: '#fef2f2', borderRadius: 6, marginBottom: 8, fontSize: 12 }}>
          {preview.errors.map((e, i) => <div key={i} style={{ color: '#991b1b' }}>{e}</div>)}
        </div>
      )}
      {preview?.rows?.length > 0 && (
        <>
          <div style={{ overflow: 'auto', maxHeight: 200, border: '1px solid #e2e8f0', borderRadius: 6, marginBottom: 8 }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead><tr><th style={thStyle}>LOT NO</th><th style={thStyle}>Sub</th><th style={thStyle}>Location</th></tr></thead>
              <tbody>
                {preview.rows.map((r, i) => (
                  <tr key={i}><td style={tdStyle}>{r.lot_no}</td><td style={{ ...tdStyle, textAlign: 'center' }}>{r.sub_lt}</td><td style={tdStyle}>{r.location}</td></tr>
                ))}
              </tbody>
            </table>
          </div>
          <button onClick={confirm} disabled={loading}
            style={{ padding: '8px 20px', fontWeight: 700, fontSize: 13, background: '#dc2626', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer' }}>
            일괄 적용 ({preview.rows.length}건)
          </button>
        </>
      )}
    </div>
  );
}
