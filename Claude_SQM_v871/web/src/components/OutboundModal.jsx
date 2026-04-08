import { useState } from 'react';
import Modal from './Modal';
import { executeOutbound } from '../api/writeApi';
import { addRecentFile } from '../utils/recentFiles';

const input = { width: '100%', padding: '6px 10px', border: '1px solid #d1d5db', borderRadius: 4, fontSize: 13 };
const label = { display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4, color: '#374151' };
const btn = (bg) => ({
  padding: '8px 20px', border: 'none', borderRadius: 6,
  color: '#fff', background: bg, fontSize: 13, fontWeight: 600, cursor: 'pointer',
});

const emptyItem = { lot_no: '', sub_lt: '', qty_kg: '' };

export default function OutboundModal({ open, onClose }) {
  const [items, setItems] = useState([{ ...emptyItem }]);
  const [customer, setCustomer] = useState('');
  const [saleRef, setSaleRef] = useState('');
  const [destination, setDestination] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const updateItem = (idx, key, val) => {
    setItems((prev) => prev.map((item, i) => (i === idx ? { ...item, [key]: val } : item)));
  };

  const addItem = () => setItems((prev) => [...prev, { ...emptyItem }]);
  const removeItem = (idx) => setItems((prev) => prev.filter((_, i) => i !== idx));

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const reqItems = items
        .filter((it) => it.lot_no && it.sub_lt)
        .map((it) => ({
          lot_no: it.lot_no,
          sub_lt: parseInt(it.sub_lt) || 1,
          qty_kg: it.qty_kg ? parseFloat(it.qty_kg) : null,
        }));

      if (reqItems.length === 0 || !customer) {
        setResult({ success: false, message: '톤백 정보와 고객명은 필수입니다.' });
        setLoading(false);
        return;
      }

      const res = await executeOutbound({
        items: reqItems,
        customer,
        sale_ref: saleRef,
        destination,
        source: 'WEB',
      });
      setResult(res);
      if (res.success) {
        const label = [saleRef, customer].filter(Boolean).join(' · ')
          || reqItems.map((i) => i.lot_no).join(', ');
        addRecentFile({
          filename: label || '즉시 출고',
          type: '출고',
          path: '/outbound',
        });
      }
    } catch (e) {
      setResult({ success: false, message: e.message });
    }
    setLoading(false);
  };

  const handleClose = () => {
    setItems([{ ...emptyItem }]);
    setCustomer('');
    setSaleRef('');
    setDestination('');
    setResult(null);
    onClose();
  };

  return (
    <Modal open={open} onClose={handleClose} title="출고 처리" width={700}>
      {!result ? (
        <div>
          {/* 고객 정보 */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, marginBottom: 16 }}>
            <div><span style={label}>고객명 *</span><input style={input} value={customer} onChange={(e) => setCustomer(e.target.value)} /></div>
            <div><span style={label}>Sale Ref</span><input style={input} value={saleRef} onChange={(e) => setSaleRef(e.target.value)} /></div>
            <div><span style={label}>출고처</span><input style={input} value={destination} onChange={(e) => setDestination(e.target.value)} /></div>
          </div>

          {/* 톤백 선택 */}
          <h4 style={{ fontSize: 13, marginBottom: 8 }}>출고 톤백</h4>
          {items.map((item, idx) => (
            <div key={idx} style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1.5fr auto', gap: 8, marginBottom: 8, alignItems: 'end' }}>
              <div><span style={label}>LOT NO</span><input style={input} value={item.lot_no} onChange={(e) => updateItem(idx, 'lot_no', e.target.value)} /></div>
              <div><span style={label}>Sub LT</span><input style={input} type="number" value={item.sub_lt} onChange={(e) => updateItem(idx, 'sub_lt', e.target.value)} /></div>
              <div><span style={label}>수량 (kg)</span><input style={input} type="number" value={item.qty_kg} onChange={(e) => updateItem(idx, 'qty_kg', e.target.value)} placeholder="전량" /></div>
              {items.length > 1 && (
                <button style={{ ...btn('#ef4444'), padding: '6px 12px' }} onClick={() => removeItem(idx)}>X</button>
              )}
            </div>
          ))}
          <button style={{ ...btn('#3b82f6'), padding: '6px 14px', fontSize: 12, marginBottom: 16 }} onClick={addItem}>+ 톤백 추가</button>

          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <button style={btn('#f97316')} onClick={handleSubmit} disabled={loading}>
              {loading ? '처리 중...' : '출고 실행'}
            </button>
            <button style={btn('#94a3b8')} onClick={handleClose}>취소</button>
          </div>
        </div>
      ) : (
        <div>
          <div style={{
            padding: 16, borderRadius: 8, marginBottom: 16,
            background: result.success ? '#f0fdf4' : '#fef2f2',
            border: `1px solid ${result.success ? '#86efac' : '#fca5a5'}`,
          }}>
            <strong style={{ color: result.success ? '#16a34a' : '#dc2626' }}>
              {result.success ? '출고 성공' : '출고 실패'}
            </strong>
            <p style={{ margin: '8px 0 0', fontSize: 13 }}>{result.message}</p>
          </div>
          {result.data && (
            <div style={{ fontSize: 12 }}>
              {result.data.processed > 0 && <p>처리된 건수: {result.data.processed}</p>}
              {result.data.total_weight_kg > 0 && <p>총 중량: {result.data.total_weight_kg.toLocaleString()} kg</p>}
              {result.data.errors?.length > 0 && (
                <div style={{ color: '#dc2626' }}>
                  <strong>오류:</strong>
                  <ul>{result.data.errors.map((e, i) => <li key={i}>{e}</li>)}</ul>
                </div>
              )}
            </div>
          )}
          <div style={{ textAlign: 'right', marginTop: 16 }}>
            <button style={btn('#6366f1')} onClick={handleClose}>닫기</button>
          </div>
        </div>
      )}
    </Modal>
  );
}
