import { useState } from 'react';
import Modal from './Modal';
import { getLotDetail } from '../api/inventoryApi';
import { fetchJson } from '../api/client';

const BASE = '/api';
const label = { fontSize: 12, fontWeight: 600, display: 'block', marginBottom: 2 };
const input = { width: '100%', padding: 5, fontSize: 12, border: '1px solid #e2e8f0', borderRadius: 4 };

export default function DoUpdateModal({ open, onClose }) {
  const [lotNo, setLotNo] = useState('');
  const [lotInfo, setLotInfo] = useState(null);
  const [form, setForm] = useState({ do_no: '', ship_date: '', arrival_date: '', con_return: '', free_time: '' });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const search = async () => {
    if (!lotNo) return;
    setLoading(true);
    try {
      const data = await getLotDetail(lotNo);
      setLotInfo(data);
      setForm({
        do_no: data.bl_no || '',
        ship_date: data.ship_date || '',
        arrival_date: data.arrival_date || '',
        con_return: data.con_return || '',
        free_time: data.free_time ? String(data.free_time) : '',
      });
    } catch (e) {
      setLotInfo(null);
    } finally {
      setLoading(false);
    }
  };

  const apply = async () => {
    setLoading(true);
    setResult(null);
    try {
      const res = await fetch(`${BASE}/do-update/apply`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          lot_no: lotNo,
          do_no: form.do_no || null,
          ship_date: form.ship_date || null,
          arrival_date: form.arrival_date || null,
          con_return: form.con_return || null,
          free_time: form.free_time ? parseInt(form.free_time, 10) : null,
        }),
      });
      const data = await res.json();
      setResult(data);
    } catch (e) {
      setResult({ success: false, message: e.message });
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setLotNo(''); setLotInfo(null); setResult(null);
    setForm({ do_no: '', ship_date: '', arrival_date: '', con_return: '', free_time: '' });
    onClose();
  };

  return (
    <Modal open={open} onClose={handleClose} title="D/O 후속 연결" width={500}>
      <div style={{ display: 'flex', gap: 6, marginBottom: 12 }}>
        <input value={lotNo} onChange={e => setLotNo(e.target.value)} placeholder="LOT NO"
          style={{ ...input, flex: 1 }} onKeyDown={e => e.key === 'Enter' && search()} />
        <button onClick={search} style={{ padding: '5px 14px', fontSize: 12, fontWeight: 700 }}>검색</button>
      </div>

      {lotInfo && (
        <div style={{ fontSize: 12, color: '#475569', marginBottom: 12, padding: 8, background: '#f8fafc', borderRadius: 6 }}>
          <b>{lotInfo.lot_no}</b> — {lotInfo.product_name} / {lotInfo.sap_no} / 톤백 {lotInfo.tonbag_count}개
        </div>
      )}

      {lotInfo && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          <label style={label}>D/O No (BL NO)<input style={input} value={form.do_no} onChange={e => setForm(f => ({ ...f, do_no: e.target.value }))} /></label>
          <label style={label}>Ship Date<input type="date" style={input} value={form.ship_date} onChange={e => setForm(f => ({ ...f, ship_date: e.target.value }))} /></label>
          <label style={label}>Arrival Date<input type="date" style={input} value={form.arrival_date} onChange={e => setForm(f => ({ ...f, arrival_date: e.target.value }))} /></label>
          <label style={label}>Con Return<input type="date" style={input} value={form.con_return} onChange={e => setForm(f => ({ ...f, con_return: e.target.value }))} /></label>
          <label style={label}>Free Time (일)<input type="number" style={input} value={form.free_time} onChange={e => setForm(f => ({ ...f, free_time: e.target.value }))} /></label>
          <button onClick={apply} disabled={loading}
            style={{ padding: '8px 20px', fontWeight: 700, fontSize: 13, background: '#2563eb', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', marginTop: 4 }}>
            {loading ? '적용 중...' : '적용'}
          </button>
        </div>
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
