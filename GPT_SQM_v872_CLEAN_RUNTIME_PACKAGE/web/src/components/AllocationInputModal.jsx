import { useState } from 'react';
import Modal from './Modal';
import { addRecentFile } from '../utils/recentFiles';

const BASE = '/api';

const thStyle = {
  padding: '6px 10px', textAlign: 'center', background: '#0f172a',
  borderBottom: '2px solid #334155', fontSize: 11, fontWeight: 700,
  whiteSpace: 'nowrap', color: '#64748b', position: 'sticky', top: 0,
};
const tdStyle = { padding: '5px 10px', borderBottom: '1px solid #1e293b', fontSize: 12, whiteSpace: 'nowrap', color: '#e2e8f0' };
const tdR     = { ...tdStyle, textAlign: 'right' };
const tdC     = { ...tdStyle, textAlign: 'center' };

export default function AllocationInputModal({ open, onClose }) {
  const [parsed,  setParsed]  = useState(null);
  const [result,  setResult]  = useState(null);
  const [loading, setLoading] = useState(false);

  // ── 파일 업로드 → AllocationParser 호출 ─────────────────────────────────
  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoading(true);
    setParsed(null);
    setResult(null);
    try {
      const fd = new FormData();
      fd.append('file',      file);
      fd.append('file_type', 'allocation');   // ← files.py가 AllocationParser 호출
      const res  = await fetch(`${BASE}/files/upload`, { method: 'POST', body: fd });
      const data = await res.json();

      // files.py v0.5.1: file_type=allocation 시 data.data.rows 직접 반환
      const rows = data?.data?.rows || [];

      setParsed({
        success:       data.success,
        message:       data.message,
        errors:        data.errors        || [],
        warnings:      data.warnings      || [],
        rows,
        // 헤더 정보 (AllocationParser에서 추출)
        customer:      data?.data?.customer      || '',
        sale_ref:      data?.data?.sale_ref      || '',
        total_qty_mt:  data?.data?.total_qty_mt  || 0,
        source_file:   data?.data?.source_file   || file.name,
      });
    } catch (err) {
      setParsed({ success: false, errors: [err.message], warnings: [], rows: [] });
    } finally {
      setLoading(false);
    }
  };

  // ── 확인 저장 → /api/tools/allocation/save ──────────────────────────────
  const handleConfirm = async () => {
    if (!parsed?.rows?.length) return;
    setLoading(true);
    setResult(null);
    try {
      const res  = await fetch(`${BASE}/tools/allocation/save`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ rows: parsed.rows }),
      });
      const data = await res.json();
      setResult(data);
      if (data.success) {
        addRecentFile({
          filename: parsed.source_file || 'Allocation',
          type: '배정',
          path: '/allocation',
        });
        setTimeout(() => handleClose(), 2000);
      }
    } catch (err) {
      setResult({ success: false, message: err.message });
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => { setParsed(null); setResult(null); onClose(); };

  return (
    <Modal open={open} onClose={handleClose} title="📋 Allocation 입력 (Excel)" width={760}>

      {/* 파일 선택 */}
      {!result?.success && (
        <div style={{ marginBottom: 12 }}>
          <label style={{
            display: 'inline-flex', alignItems: 'center', gap: 10,
            padding: '8px 14px', background: '#1e293b',
            border: '1px solid #334155', borderRadius: 6, cursor: 'pointer',
          }}>
            <span style={{ fontSize: 13, color: '#38bdf8', fontWeight: 600 }}>📂 Excel 파일 선택</span>
            <input type="file" accept=".xlsx,.xls" onChange={handleUpload}
              style={{ display: 'none' }} disabled={loading} />
          </label>
          <span style={{ fontSize: 11, color: '#64748b', marginLeft: 10 }}>
            지원 양식: Song / Woo / Standard / Shipper Original / Easpring / Jakarta
          </span>
        </div>
      )}

      {loading && (
        <div style={{ padding: '12px 0', color: '#64748b', fontSize: 13 }}>⏳ 파싱 중...</div>
      )}

      {/* 오류 */}
      {parsed?.errors?.length > 0 && (
        <div style={{ padding: 10, background: '#450a0a', border: '1px solid #7f1d1d', borderRadius: 6, marginBottom: 8, fontSize: 12 }}>
          {parsed.errors.map((e, i) => <div key={i} style={{ color: '#f87171' }}>❌ {e}</div>)}
        </div>
      )}

      {/* 경고 */}
      {parsed?.warnings?.length > 0 && (
        <div style={{ padding: 10, background: '#3b2a00', border: '1px solid #92400e', borderRadius: 6, marginBottom: 8, fontSize: 12 }}>
          {parsed.warnings.map((w, i) => <div key={i} style={{ color: '#fbbf24' }}>⚠️ {w}</div>)}
        </div>
      )}

      {/* 파싱 성공 — 헤더 요약 */}
      {parsed?.success && parsed.rows?.length > 0 && !result && (
        <>
          {/* 요약 카드 */}
          <div style={{
            display: 'flex', gap: 16, flexWrap: 'wrap',
            background: '#0f172a', border: '1px solid #38bdf8',
            borderRadius: 8, padding: '10px 16px', marginBottom: 12,
          }}>
            {[
              ['파일',      parsed.source_file || '-'],
              ['고객',      parsed.customer    || '-'],
              ['Sale Ref',  parsed.sale_ref    || '-'],
              ['총 행수',   `${parsed.rows.length}행`],
              ['합계 QTY',  `${Number(parsed.total_qty_mt || 0).toFixed(3)} MT`],
            ].map(([k, v]) => (
              <div key={k} style={{ fontSize: 12 }}>
                <span style={{ color: '#64748b', marginRight: 4 }}>{k}</span>
                <span style={{ color: '#38bdf8', fontWeight: 700 }}>{v}</span>
              </div>
            ))}
          </div>

          {/* 미리보기 테이블 */}
          <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 6 }}>
            내용을 확인 후 [✅ 확인 저장]을 누르세요.
          </div>
          <div style={{ overflow: 'auto', maxHeight: '42vh', border: '1px solid #334155', borderRadius: 8, marginBottom: 12 }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 640 }}>
              <thead>
                <tr>
                  <th style={{ ...thStyle, width: 40 }}>No.</th>
                  <th style={thStyle}>LOT NO</th>
                  <th style={thStyle}>SAP NO</th>
                  <th style={thStyle}>Customer</th>
                  <th style={thStyle}>Sale Ref</th>
                  <th style={thStyle}>QTY(MT)</th>
                  <th style={thStyle}>Outbound Date</th>
                  <th style={thStyle}>WH</th>
                  <th style={thStyle}>Sample</th>
                </tr>
              </thead>
              <tbody>
                {parsed.rows.map((r, i) => (
                  <tr key={i}
                    style={{ background: r.is_sample ? '#1e1008' : '' }}
                    onMouseEnter={e => e.currentTarget.style.background = '#1e293b'}
                    onMouseLeave={e => e.currentTarget.style.background = r.is_sample ? '#1e1008' : ''}
                  >
                    <td style={{ ...tdC, color: '#475569', fontSize: 11 }}>{i + 1}</td>
                    <td style={{ ...tdStyle, color: '#38bdf8', fontWeight: 600 }}>{r.lot_no  || '-'}</td>
                    <td style={{ ...tdStyle, color: '#94a3b8' }}>{r.sap_no  || '-'}</td>
                    <td style={tdStyle}>{r.customer || '-'}</td>
                    <td style={tdStyle}>{r.sale_ref || '-'}</td>
                    <td style={tdR}>{r.qty_mt ? Number(r.qty_mt).toFixed(3) : '-'}</td>
                    <td style={tdC}>{r.outbound_date || '-'}</td>
                    <td style={tdC}>{r.warehouse || '-'}</td>
                    <td style={tdC}>{r.is_sample ? <span style={{ color: '#f87171', fontWeight: 700 }}>S</span> : '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div style={{ display: 'flex', gap: 8 }}>
            <button onClick={handleConfirm} disabled={loading} style={{
              padding: '9px 24px', fontWeight: 700, fontSize: 13,
              background: loading ? '#334155' : '#2563eb', color: '#fff',
              border: 'none', borderRadius: 6,
              cursor: loading ? 'not-allowed' : 'pointer',
            }}>
              {loading ? '저장 중...' : '✅ 확인 저장'}
            </button>
            <button onClick={handleClose} style={{
              padding: '9px 16px', fontSize: 13,
              background: '#334155', color: '#94a3b8',
              border: 'none', borderRadius: 6, cursor: 'pointer',
            }}>
              취소
            </button>
          </div>
        </>
      )}

      {/* 파싱됐지만 rows 0 */}
      {parsed && !loading && parsed.rows?.length === 0 && !parsed.errors?.length && (
        <div style={{ padding: 12, background: '#3b2a00', border: '1px solid #92400e', borderRadius: 6, fontSize: 12, color: '#fbbf24' }}>
          ⚠️ 파싱 가능한 행이 없습니다. 지원 양식(Song/Woo/Standard/Easpring/Jakarta)인지 확인해 주세요.
        </div>
      )}

      {/* 저장 결과 */}
      {result && (
        <div style={{
          marginTop: 12, padding: 14, borderRadius: 8, fontSize: 13, fontWeight: 600,
          background: result.success ? '#064e3b' : '#450a0a',
          color:      result.success ? '#34d399' : '#f87171',
          border:     `1px solid ${result.success ? '#065f46' : '#7f1d1d'}`,
        }}>
          {result.success
            ? `✅ ${result.message || `${result.saved}건 저장 완료`}`
            : `❌ ${result.message || '저장 실패'}`}
        </div>
      )}
    </Modal>
  );
}
