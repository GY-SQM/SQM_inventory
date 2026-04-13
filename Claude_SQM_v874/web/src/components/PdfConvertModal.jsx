import { useState } from 'react';
import Modal from './Modal';

const MODE_INFO = {
  excel:   { title: '📊 PDF → Excel 변환', accept: '.pdf', endpoint: '/api/reports/pdf-to-excel' },
  word:    { title: '📝 PDF → Word 변환',  accept: '.pdf', endpoint: '/api/reports/pdf-to-word' },
  batch:   { title: '📁 PDF 일괄 변환',    accept: '.pdf', endpoint: '/api/reports/pdf-to-excel' },
  analyze: { title: '🔍 PDF 분석',         accept: '.pdf', endpoint: '/api/reports/pdf-to-excel' },
};

const btnS = (bg, disabled) => ({
  padding: '8px 18px', border: 'none', borderRadius: 6,
  color: disabled ? '#64748b' : '#fff',
  background: disabled ? '#334155' : bg,
  fontSize: 13, fontWeight: 600,
  cursor: disabled ? 'not-allowed' : 'pointer',
});

export default function PdfConvertModal({ open, onClose, mode = 'excel' }) {
  const [file, setFile]       = useState(null);
  const [files, setFiles]     = useState([]);
  const [loading, setLoading] = useState(false);
  const [result, setResult]   = useState(null);

  const info = MODE_INFO[mode] || MODE_INFO.excel;
  const isBatch = mode === 'batch';

  const handleClose = () => {
    setFile(null); setFiles([]); setResult(null); setLoading(false);
    onClose();
  };

  const handleConvert = async () => {
    const targetFiles = isBatch ? files : (file ? [file] : []);
    if (targetFiles.length === 0) return;

    setLoading(true); setResult(null);
    try {
      const fd = new FormData();
      targetFiles.forEach(f => fd.append('file', f));
      if (mode === 'analyze') fd.append('analyze_only', 'true');

      const r = await fetch(info.endpoint, { method: 'POST', body: fd });

      if (r.ok) {
        const contentType = r.headers.get('content-type') || '';
        if (contentType.includes('application/json')) {
          const d = await r.json();
          setResult({ success: true, message: d.message || 'PDF 분석 완료', data: d });
        } else {
          // 파일 다운로드
          const blob = await r.blob();
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          const disposition = r.headers.get('content-disposition') || '';
          const match = disposition.match(/filename[^;=\n]*=([^\n;]*)/);
          a.download = match ? match[1].replace(/['"]/g, '') : `converted_${Date.now()}.xlsx`;
          a.href = url;
          a.click();
          URL.revokeObjectURL(url);
          setResult({ success: true, message: `✅ 변환 완료: ${a.download}` });
        }
      } else {
        const d = await r.json().catch(() => ({}));
        setResult({ success: false, message: d.detail || d.message || `변환 실패 (${r.status})` });
      }
    } catch (e) {
      setResult({ success: false, message: e.message });
    }
    setLoading(false);
  };

  return (
    <Modal open={open} onClose={handleClose} title={info.title} width={550}>
      <div style={{ marginBottom: 16 }}>
        <p style={{ fontSize: 12, color: '#94a3b8', marginBottom: 12 }}>
          {mode === 'analyze' ? 'PDF 파일을 업로드하면 내용을 분석합니다.' :
           isBatch ? '여러 PDF를 선택하여 일괄 변환합니다.' :
           'PDF 파일을 업로드하면 변환을 시작합니다.'}
        </p>

        {isBatch ? (
          <input type="file" accept={info.accept} multiple
            onChange={e => setFiles(Array.from(e.target.files || []))}
            style={{ fontSize: 13 }} />
        ) : (
          <input type="file" accept={info.accept}
            onChange={e => setFile(e.target.files?.[0] || null)}
            style={{ fontSize: 13 }} />
        )}

        {(file || files.length > 0) && (
          <div style={{ marginTop: 8, fontSize: 12, color: '#94a3b8' }}>
            선택: {isBatch ? `${files.length}개 파일` : file?.name}
          </div>
        )}
      </div>

      {result && (
        <div style={{
          padding: '10px 14px', borderRadius: 6, marginBottom: 12, fontSize: 12,
          background: result.success ? '#064e3b' : '#450a0a',
          color: result.success ? '#34d399' : '#f87171',
          border: `1px solid ${result.success ? '#065f46' : '#7f1d1d'}`,
        }}>
          {result.message}
          {result.data?.tables && (
            <div style={{ marginTop: 8, color: '#94a3b8' }}>
              감지 테이블: {result.data.tables}개, 행: {result.data.rows}개
            </div>
          )}
        </div>
      )}

      <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
        <button
          style={btnS('#3b82f6', loading || (!file && files.length === 0))}
          onClick={handleConvert}
          disabled={loading || (!file && files.length === 0)}
        >
          {loading ? '처리 중...' : mode === 'analyze' ? '🔍 분석 시작' : '📊 변환 시작'}
        </button>
        <button style={btnS('#475569', false)} onClick={handleClose}>닫기</button>
      </div>
    </Modal>
  );
}
