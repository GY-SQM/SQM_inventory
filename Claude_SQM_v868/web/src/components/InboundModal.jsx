import { useState } from 'react';
import Modal from './Modal';
import { uploadFile, createInbound } from '../api/writeApi';

const input = { width: '100%', padding: '6px 10px', border: '1px solid #d1d5db', borderRadius: 4, fontSize: 13 };
const label = { display: 'block', fontSize: 12, fontWeight: 600, marginBottom: 4, color: '#374151' };
const row = { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 };
const btn = (bg) => ({
  padding: '8px 20px', border: 'none', borderRadius: 6,
  color: '#fff', background: bg, fontSize: 13, fontWeight: 600, cursor: 'pointer',
});

export default function InboundModal({ open, onClose }) {
  const [step, setStep] = useState('upload'); // upload | form | result
  const [file, setFile] = useState(null);
  const [parseResult, setParseResult] = useState(null);
  const [form, setForm] = useState({
    lot_no: '', product_name: '', bl_no: '', sap_no: '',
    total_weight_kg: '', bag_count: '', location: '',
    container_no: '', invoice_no: '', ship_date: '', arrival_date: '', warehouse: '',
  });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleUpload = async () => {
    if (!file) return;
    setLoading(true);
    try {
      const res = await uploadFile(file);
      setParseResult(res);
      if (res.success) setStep('form');
    } catch (e) {
      setParseResult({ success: false, message: e.message });
    }
    setLoading(false);
  };

  const handleManual = () => setStep('form');

  const handleSubmit = async () => {
    setLoading(true);
    try {
      const res = await createInbound({
        ...form,
        total_weight_kg: parseFloat(form.total_weight_kg) || 0,
        bag_count: parseInt(form.bag_count) || 0,
        source_type: file ? 'WEB_UPLOAD' : 'WEB_MANUAL',
        source_file: file?.name || '',
      });
      setResult(res);
      setStep('result');
    } catch (e) {
      setResult({ success: false, message: e.message });
      setStep('result');
    }
    setLoading(false);
  };

  const handleClose = () => {
    setStep('upload');
    setFile(null);
    setParseResult(null);
    setForm({
      lot_no: '', product_name: '', bl_no: '', sap_no: '',
      total_weight_kg: '', bag_count: '', location: '',
      container_no: '', invoice_no: '', ship_date: '', arrival_date: '', warehouse: '',
    });
    setResult(null);
    onClose();
  };

  const setField = (k, v) => setForm((prev) => ({ ...prev, [k]: v }));

  return (
    <Modal open={open} onClose={handleClose} title="입고 파싱" width={650}>
      {/* Step 1: 업로드 */}
      {step === 'upload' && (
        <div>
          <p style={{ fontSize: 13, color: '#64748b', marginBottom: 16 }}>
            PDF 또는 Excel 파일을 업로드하면 자동 파싱합니다. 수동 입력도 가능합니다.
          </p>
          <div style={{ border: '2px dashed #d1d5db', borderRadius: 8, padding: 30, textAlign: 'center', marginBottom: 16 }}>
            <input
              type="file"
              accept=".pdf,.xlsx,.xls,.csv"
              onChange={(e) => setFile(e.target.files[0])}
              style={{ fontSize: 13 }}
            />
          </div>
          {parseResult && !parseResult.success && (
            <p style={{ color: 'red', fontSize: 12 }}>{parseResult.message}</p>
          )}
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <button style={btn('#6366f1')} onClick={handleUpload} disabled={!file || loading}>
              {loading ? '파싱 중...' : '파일 업로드 & 파싱'}
            </button>
            <button style={btn('#64748b')} onClick={handleManual}>수동 입력</button>
          </div>
        </div>
      )}

      {/* Step 2: 입력 폼 */}
      {step === 'form' && (
        <div>
          {parseResult?.data && (
            <div style={{ background: '#f0fdf4', padding: 10, borderRadius: 6, marginBottom: 16, fontSize: 12 }}>
              파싱 완료: {parseResult.message}
            </div>
          )}
          <div style={row}>
            <div><span style={label}>LOT NO *</span><input style={input} value={form.lot_no} onChange={(e) => setField('lot_no', e.target.value)} /></div>
            <div><span style={label}>제품명 *</span><input style={input} value={form.product_name} onChange={(e) => setField('product_name', e.target.value)} /></div>
          </div>
          <div style={row}>
            <div><span style={label}>BL NO *</span><input style={input} value={form.bl_no} onChange={(e) => setField('bl_no', e.target.value)} /></div>
            <div><span style={label}>SAP NO</span><input style={input} value={form.sap_no} onChange={(e) => setField('sap_no', e.target.value)} /></div>
          </div>
          <div style={row}>
            <div><span style={label}>총 중량 (kg) *</span><input style={input} type="number" value={form.total_weight_kg} onChange={(e) => setField('total_weight_kg', e.target.value)} /></div>
            <div><span style={label}>톤백 수 *</span><input style={input} type="number" value={form.bag_count} onChange={(e) => setField('bag_count', e.target.value)} /></div>
          </div>
          <div style={row}>
            <div><span style={label}>위치</span><input style={input} value={form.location} onChange={(e) => setField('location', e.target.value)} /></div>
            <div><span style={label}>컨테이너 NO</span><input style={input} value={form.container_no} onChange={(e) => setField('container_no', e.target.value)} /></div>
          </div>
          <div style={row}>
            <div><span style={label}>Invoice NO</span><input style={input} value={form.invoice_no} onChange={(e) => setField('invoice_no', e.target.value)} /></div>
            <div><span style={label}>창고</span><input style={input} value={form.warehouse} onChange={(e) => setField('warehouse', e.target.value)} /></div>
          </div>
          <div style={row}>
            <div><span style={label}>선적일</span><input style={input} type="date" value={form.ship_date} onChange={(e) => setField('ship_date', e.target.value)} /></div>
            <div><span style={label}>도착일</span><input style={input} type="date" value={form.arrival_date} onChange={(e) => setField('arrival_date', e.target.value)} /></div>
          </div>
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 16 }}>
            <button style={btn('#22c55e')} onClick={handleSubmit} disabled={loading}>
              {loading ? '처리 중...' : '입고 실행'}
            </button>
            <button style={btn('#94a3b8')} onClick={() => setStep('upload')}>뒤로</button>
          </div>
        </div>
      )}

      {/* Step 3: 결과 */}
      {step === 'result' && result && (
        <div>
          <div style={{
            padding: 16, borderRadius: 8, marginBottom: 16,
            background: result.success ? '#f0fdf4' : '#fef2f2',
            border: `1px solid ${result.success ? '#86efac' : '#fca5a5'}`,
          }}>
            <strong style={{ color: result.success ? '#16a34a' : '#dc2626' }}>
              {result.success ? '입고 성공' : '입고 실패'}
            </strong>
            <p style={{ margin: '8px 0 0', fontSize: 13 }}>{result.message}</p>
          </div>
          {result.data && (
            <div style={{ fontSize: 12 }}>
              {result.data.lot_no && <p>LOT NO: <strong>{result.data.lot_no}</strong></p>}
              {result.data.created_tonbags > 0 && <p>생성된 톤백: {result.data.created_tonbags}개</p>}
              {result.data.warnings?.length > 0 && (
                <div style={{ color: '#ca8a04' }}>
                  <strong>경고:</strong>
                  <ul>{result.data.warnings.map((w, i) => <li key={i}>{w}</li>)}</ul>
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
