import { useState } from 'react';
import Modal from './Modal';

const BASE = '/api';
const thStyle = { padding: '6px 8px', textAlign: 'center', background: '#f8fafc', borderBottom: '2px solid #e2e8f0', fontSize: 11, fontWeight: 700 };
const tdStyle = { padding: '5px 8px', borderBottom: '1px solid #f1f5f9', fontSize: 12 };

export default function AllocationInputModal({ open, onClose }) {
  const [preview, setPreview] = useState(null);
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoading(true);
    setPreview(null);
    setResult(null);
    try {
      const fd = new FormData();
      fd.append('file', file);
      fd.append('file_type', 'allocation');
      const res = await fetch(`${BASE}/files/upload`, { method: 'POST', body: fd });
      const data = await res.json();
      setPreview(data);
    } catch (err) {
      setPreview({ success: false, errors: [err.message] });
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => { setPreview(null); setResult(null); onClose(); };

  return (
    <Modal open={open} onClose={handleClose} title="Allocation 입력 (Excel)" width={700}>
      <div style={{ marginBottom: 12 }}>
        <input type="file" accept=".xlsx,.xls" onChange={handleUpload} style={{ fontSize: 13 }} />
      </div>

      {loading && <div style={{ padding: 12, color: '#475569' }}>파싱 중...</div>}

      {preview?.warnings?.length > 0 && (
        <div style={{ padding: 8, background: '#fffbeb', border: '1px solid #fde68a', borderRadius: 6, marginBottom: 8, fontSize: 12 }}>
          {preview.warnings.map((w, i) => <div key={i} style={{ color: '#92400e' }}>{w}</div>)}
        </div>
      )}

      {preview?.errors?.length > 0 && (
        <div style={{ padding: 8, background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 6, marginBottom: 8, fontSize: 12 }}>
          {preview.errors.map((e, i) => <div key={i} style={{ color: '#991b1b' }}>{e}</div>)}
        </div>
      )}

      {preview?.data?.rows && preview.data.rows.length > 0 && (
        <div style={{ overflow: 'auto', maxHeight: '40vh', border: '1px solid #e2e8f0', borderRadius: 6 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 500 }}>
            <thead>
              <tr>
                <th style={thStyle}>LOT NO</th>
                <th style={thStyle}>Customer</th>
                <th style={thStyle}>Sale Ref</th>
                <th style={thStyle}>Qty(MT)</th>
              </tr>
            </thead>
            <tbody>
              {preview.data.rows.map((r, i) => (
                <tr key={i}>
                  <td style={tdStyle}>{r.lot_no || '-'}</td>
                  <td style={tdStyle}>{r.customer || '-'}</td>
                  <td style={tdStyle}>{r.sale_ref || '-'}</td>
                  <td style={{ ...tdStyle, textAlign: 'right' }}>{r.qty_mt || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {preview?.success && (
        <div style={{
          marginTop: 10, padding: 8, borderRadius: 6, fontSize: 12,
          background: '#f0fdf4', color: '#166534',
        }}>{preview.message || '파싱 완료'}</div>
      )}

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
