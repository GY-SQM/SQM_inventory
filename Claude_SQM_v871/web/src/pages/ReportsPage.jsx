import { useState, useRef } from 'react';

const BASE = '/api/reports';

const cardS = {
  background: '#1e293b', border: '1px solid #334155',
  borderRadius: 8, padding: '16px 20px', marginBottom: 14,
};
const titleS = { fontSize: 13, fontWeight: 700, color: '#94a3b8', marginBottom: 12 };
const inputS = {
  padding: '7px 10px', fontSize: 13, background: '#0f172a',
  border: '1px solid #334155', borderRadius: 6, color: '#f1f5f9',
};
const btnS = (color, disabled) => ({
  padding: '8px 18px', border: 'none', borderRadius: 6,
  background: disabled ? '#334155' : color,
  color: disabled ? '#64748b' : '#fff',
  fontSize: 13, fontWeight: 600,
  cursor: disabled ? 'not-allowed' : 'pointer',
});

function Toast({ msg, ok }) {
  if (!msg) return null;
  return (
    <div style={{
      position: 'fixed', bottom: 28, left: '50%', transform: 'translateX(-50%)',
      padding: '10px 24px', borderRadius: 8, fontSize: 13, fontWeight: 600,
      zIndex: 9999, background: ok ? '#064e3b' : '#450a0a',
      color: ok ? '#34d399' : '#f87171',
    }}>{msg}</div>
  );
}

function Section({ title, children }) {
  return (
    <div style={cardS}>
      <div style={titleS}>{title}</div>
      {children}
    </div>
  );
}

// 파일 다운로드 헬퍼
async function downloadFile(url, method = 'GET', body = null, filename = null) {
  const opts = { method };
  if (body) { opts.headers = { 'Content-Type': 'application/json' }; opts.body = JSON.stringify(body); }
  const r   = await fetch(url, opts);
  if (!r.ok) {
    const t = await r.text().catch(() => '');
    throw new Error(t || `HTTP ${r.status}`);
  }
  const blob = await r.blob();
  const href = URL.createObjectURL(blob);
  const a    = document.createElement('a');
  a.href     = href;
  a.download = filename || (r.headers.get('content-disposition') || '').split('filename=')[1]?.replace(/"/g,'') || 'download';
  document.body.appendChild(a); a.click();
  setTimeout(() => { URL.revokeObjectURL(href); a.remove(); }, 500);
}

export default function ReportsPage() {
  const [loading, setLoading] = useState({});
  const [toast,   setToast]   = useState(null);
  const toastRef              = useRef(null);

  // SO 파싱 결과
  const [soResult,    setSoResult]    = useState(null);
  // PDF변환 결과
  const [convResult,  setConvResult]  = useState(null);
  // Picking 파싱 결과
  const [pickResult,  setPickResult]  = useState(null);

  // 필터 상태
  const [outboundFilter, setOutboundFilter] = useState({ sale_ref: '', outbound_date: '', lot_no: '' });
  const [invoiceFilter,  setInvoiceFilter]  = useState({ customer: '', date_from: '', date_to: '', sale_ref: '' });
  const [transFilter,    setTransFilter]    = useState({ customer: '', date_from: '', date_to: '' });
  const [lotPdfNo,       setLotPdfNo]       = useState('');
  const [monthlyYear,    setMonthlyYear]    = useState('');
  const [monthlyMonth,   setMonthlyMonth]   = useState('');

  const showToast = (msg, ok) => {
    setToast({ msg, ok });
    if (toastRef.current) clearTimeout(toastRef.current);
    toastRef.current = setTimeout(() => setToast(null), 3000);
  };

  const setL = (key, v) => setLoading(prev => ({ ...prev, [key]: v }));

  const run = async (key, fn) => {
    setL(key, true);
    try { await fn(); }
    catch (e) { showToast(`❌ ${e.message}`, false); }
    setL(key, false);
  };

  // ── 파일 업로드 헬퍼 ─────────────────────────────────────────────────────
  const uploadFile = async (file, url) => {
    const fd = new FormData(); fd.append('file', file);
    const r  = await fetch(url, { method: 'POST', body: fd });
    if (!r.ok) throw new Error(await r.text().catch(() => `HTTP ${r.status}`));
    // 파일 응답이면 다운로드
    const ct = r.headers.get('content-type') || '';
    if (ct.includes('spreadsheet') || ct.includes('excel') || ct.includes('pdf')) {
      const blob = await r.blob();
      const href = URL.createObjectURL(blob);
      const a    = document.createElement('a');
      a.href = href;
      a.download = file.name.replace(/\.[^.]+$/, '') + '_converted.xlsx';
      document.body.appendChild(a); a.click();
      setTimeout(() => { URL.revokeObjectURL(href); a.remove(); }, 500);
      return null;
    }
    return r.json();
  };

  const qp = (obj) => '?' + new URLSearchParams(
    Object.fromEntries(Object.entries(obj).filter(([,v]) => v))
  ).toString();

  return (
    <div style={{ padding: 24 }}>
      <h2 style={{ color: '#f1f5f9', marginBottom: 4 }}>📊 보고서</h2>
      <p style={{ fontSize: 12, color: '#64748b', marginBottom: 20 }}>
        각종 보고서 생성 및 서류 업로드 처리.
      </p>

      {/* ── 1. Detail of Outbound ───────────────────────────────────────── */}
      <Section title="📋 Detail of Outbound (Excel)">
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          <input placeholder="Sale Ref" value={outboundFilter.sale_ref}
            onChange={e => setOutboundFilter(p => ({ ...p, sale_ref: e.target.value }))}
            style={{ ...inputS, width: 140 }} />
          <input type="date" value={outboundFilter.outbound_date}
            onChange={e => setOutboundFilter(p => ({ ...p, outbound_date: e.target.value }))}
            style={{ ...inputS, width: 150 }} />
          <input placeholder="LOT NO" value={outboundFilter.lot_no}
            onChange={e => setOutboundFilter(p => ({ ...p, lot_no: e.target.value }))}
            style={{ ...inputS, width: 130 }} />
          <button style={btnS('#2563eb', loading.outbound)} disabled={loading.outbound}
            onClick={() => run('outbound', () =>
              downloadFile(`${BASE}/outbound-detail/download${qp(outboundFilter)}`, 'GET', null, 'Detail_of_Outbound.xlsx')
                .then(() => showToast('✅ Detail of Outbound 다운로드 완료', true))
            )}>
            {loading.outbound ? '생성 중...' : '📥 다운로드'}
          </button>
        </div>
      </Section>

      {/* ── 2. Sales Order DN ───────────────────────────────────────────── */}
      <Section title="📄 Sales Order DN (Excel)">
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          <input placeholder="Sale Ref" value={outboundFilter.sale_ref}
            onChange={e => setOutboundFilter(p => ({ ...p, sale_ref: e.target.value }))}
            style={{ ...inputS, width: 140 }} />
          <input type="date" value={outboundFilter.outbound_date}
            onChange={e => setOutboundFilter(p => ({ ...p, outbound_date: e.target.value }))}
            style={{ ...inputS, width: 150 }} />
          <button style={btnS('#7c3aed', loading.sodn)} disabled={loading.sodn}
            onClick={() => run('sodn', () =>
              downloadFile(`${BASE}/sales-order-dn/download${qp(outboundFilter)}`, 'GET', null, 'Sales_Order_DN.xlsx')
                .then(() => showToast('✅ Sales Order DN 다운로드 완료', true))
            )}>
            {loading.sodn ? '생성 중...' : '📥 다운로드'}
          </button>
        </div>
      </Section>

      {/* ── 3. 거래명세서 ───────────────────────────────────────────────── */}
      <Section title="🧾 거래명세서 (Excel)">
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
          <input placeholder="고객명" value={invoiceFilter.customer}
            onChange={e => setInvoiceFilter(p => ({ ...p, customer: e.target.value }))}
            style={{ ...inputS, width: 140 }} />
          <input placeholder="Sale Ref" value={invoiceFilter.sale_ref}
            onChange={e => setInvoiceFilter(p => ({ ...p, sale_ref: e.target.value }))}
            style={{ ...inputS, width: 140 }} />
          <input type="date" value={invoiceFilter.date_from}
            onChange={e => setInvoiceFilter(p => ({ ...p, date_from: e.target.value }))}
            style={{ ...inputS, width: 150 }} />
          <span style={{ color: '#475569' }}>~</span>
          <input type="date" value={invoiceFilter.date_to}
            onChange={e => setInvoiceFilter(p => ({ ...p, date_to: e.target.value }))}
            style={{ ...inputS, width: 150 }} />
          <button style={btnS('#0891b2', loading.invoice)} disabled={loading.invoice}
            onClick={() => run('invoice', () =>
              downloadFile(`${BASE}/invoice/download${qp(invoiceFilter)}`, 'GET', null, '거래명세서.xlsx')
                .then(() => showToast('✅ 거래명세서 다운로드 완료', true))
            )}>
            {loading.invoice ? '생성 중...' : '📥 다운로드'}
          </button>
        </div>
      </Section>

      {/* ── 4. PDF 보고서 ───────────────────────────────────────────────── */}
      <Section title="📰 PDF 보고서">
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          {/* 일일 재고 */}
          <button style={btnS('#16a34a', loading.daily)} disabled={loading.daily}
            onClick={() => run('daily', () =>
              downloadFile(`${BASE}/daily-pdf/download`, 'POST', {}, null)
                .then(() => showToast('✅ 일일 재고 현황 PDF 다운로드 완료', true))
            )}>
            {loading.daily ? '생성 중...' : '📊 일일 재고 현황 PDF'}
          </button>

          {/* 입출고 내역 */}
          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <input placeholder="고객명" value={transFilter.customer}
              onChange={e => setTransFilter(p => ({ ...p, customer: e.target.value }))}
              style={{ ...inputS, width: 120 }} />
            <input type="date" value={transFilter.date_from}
              onChange={e => setTransFilter(p => ({ ...p, date_from: e.target.value }))}
              style={{ ...inputS, width: 140 }} />
            <span style={{ color: '#475569' }}>~</span>
            <input type="date" value={transFilter.date_to}
              onChange={e => setTransFilter(p => ({ ...p, date_to: e.target.value }))}
              style={{ ...inputS, width: 140 }} />
            <button style={btnS('#0ea5e9', loading.trans)} disabled={loading.trans}
              onClick={() => run('trans', () =>
                downloadFile(`${BASE}/transaction-pdf/download${qp(transFilter)}`)
                  .then(() => showToast('✅ 입출고 내역 PDF 다운로드 완료', true))
              )}>
              {loading.trans ? '생성 중...' : '📋 입출고 내역 PDF'}
            </button>
          </div>

          {/* 월간 실적 */}
          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <input placeholder="연도" value={monthlyYear} onChange={e => setMonthlyYear(e.target.value)}
              style={{ ...inputS, width: 80 }} />
            <input placeholder="월" value={monthlyMonth} onChange={e => setMonthlyMonth(e.target.value)}
              style={{ ...inputS, width: 60 }} />
            <button style={btnS('#8b5cf6', loading.monthly)} disabled={loading.monthly}
              onClick={() => run('monthly', () =>
                downloadFile(`${BASE}/monthly-pdf/download`, 'POST',
                  { year: parseInt(monthlyYear)||null, month: parseInt(monthlyMonth)||null })
                  .then(() => showToast('✅ 월간 실적 PDF 다운로드 완료', true))
              )}>
              {loading.monthly ? '생성 중...' : '📈 월간 실적 PDF'}
            </button>
          </div>

          {/* LOT 상세 */}
          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <input placeholder="LOT NO" value={lotPdfNo} onChange={e => setLotPdfNo(e.target.value)}
              style={{ ...inputS, width: 160 }} />
            <button style={btnS('#f59e0b', loading.lotpdf || !lotPdfNo)} disabled={loading.lotpdf || !lotPdfNo}
              onClick={() => run('lotpdf', () =>
                downloadFile(`${BASE}/lot-detail-pdf/download?lot_no=${encodeURIComponent(lotPdfNo)}`)
                  .then(() => showToast('✅ LOT 상세 PDF 다운로드 완료', true))
              )}>
              {loading.lotpdf ? '생성 중...' : '🔍 LOT 상세 PDF'}
            </button>
          </div>
        </div>
      </Section>

      {/* ── 5. Sales Order 업로드 ────────────────────────────────────────── */}
      <Section title="📤 Sales Order 업로드 (SOLD 처리)">
        <p style={{ fontSize: 12, color: '#64748b', marginBottom: 10 }}>
          Sales Order Excel 업로드 → picking_table 매칭 → SOLD 처리
        </p>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <label style={{
            padding: '8px 14px', background: '#1e293b', border: '1px solid #334155',
            borderRadius: 6, cursor: 'pointer', fontSize: 13, color: '#38bdf8',
          }}>
            📂 SO Excel 선택
            <input type="file" accept=".xlsx,.xls" style={{ display: 'none' }}
              onChange={async e => {
                const file = e.target.files?.[0]; if (!file) return;
                setL('so', true); setSoResult(null);
                try {
                  const d = await uploadFile(file, `${BASE}/sales-order/process`);
                  if (d) { setSoResult(d); showToast(d.message || (d.success ? '✅ 처리 완료' : '❌ 처리 실패'), d.success); }
                } catch (err) { showToast(`❌ ${err.message}`, false); }
                setL('so', false);
                e.target.value = '';
              }} />
          </label>
          {loading.so && <span style={{ color: '#64748b', fontSize: 13 }}>처리 중...</span>}
        </div>

        {soResult && (
          <div style={{
            marginTop: 10, padding: '10px 14px', borderRadius: 8, fontSize: 12,
            background: soResult.success ? '#064e3b' : '#3b2a00',
            border: `1px solid ${soResult.success ? '#065f46' : '#92400e'}`,
            color: soResult.success ? '#34d399' : '#fbbf24',
          }}>
            <b>{soResult.message}</b>
            {soResult.sales_order_no && <span style={{ marginLeft: 12, color: '#94a3b8' }}>SO: {soResult.sales_order_no}</span>}
            {soResult.sold > 0     && <span style={{ marginLeft: 12 }}>SOLD: {soResult.sold}건</span>}
            {soResult.pending > 0  && <span style={{ marginLeft: 12 }}>PENDING: {soResult.pending}건</span>}
          </div>
        )}
      </Section>

      {/* ── 6. Picking List PDF 파싱 ─────────────────────────────────────── */}
      <Section title="📋 Picking List PDF 파싱">
        <p style={{ fontSize: 12, color: '#64748b', marginBottom: 10 }}>
          Picking List PDF 업로드 → LOT / 수량 파싱 결과 확인
        </p>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <label style={{
            padding: '8px 14px', background: '#1e293b', border: '1px solid #334155',
            borderRadius: 6, cursor: 'pointer', fontSize: 13, color: '#38bdf8',
          }}>
            📂 Picking List PDF 선택
            <input type="file" accept=".pdf" style={{ display: 'none' }}
              onChange={async e => {
                const file = e.target.files?.[0]; if (!file) return;
                setL('pick', true); setPickResult(null);
                try {
                  const fd = new FormData(); fd.append('file', file);
                  const r  = await fetch(`${BASE}/picking-list/parse`, { method: 'POST', body: fd });
                  const d  = await r.json();
                  setPickResult(d);
                  showToast(d.parse_ok ? `✅ ${d.total_lots}개 LOT 파싱 완료` : '❌ 파싱 실패', d.parse_ok);
                } catch (err) { showToast(`❌ ${err.message}`, false); }
                setL('pick', false); e.target.value = '';
              }} />
          </label>
          {loading.pick && <span style={{ color: '#64748b', fontSize: 13 }}>파싱 중...</span>}
        </div>

        {pickResult && pickResult.parse_ok && (
          <div style={{ marginTop: 10, overflow: 'auto', maxHeight: 260,
            border: '1px solid #334155', borderRadius: 8 }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
              <thead>
                <tr>
                  {['LOT NO','QTY(MT)','QTY(Kg)','위치','Sample'].map(h => (
                    <th key={h} style={{ padding: '6px 10px', background: '#0f172a',
                      color: '#64748b', fontWeight: 700, textAlign: 'left',
                      borderBottom: '1px solid #334155' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(pickResult.items || []).map((r, i) => (
                  <tr key={i}>
                    <td style={{ padding: '5px 10px', color: '#38bdf8', fontWeight: 600, borderBottom: '1px solid #1e293b' }}>{r.lot_no}</td>
                    <td style={{ padding: '5px 10px', borderBottom: '1px solid #1e293b' }}>{r.qty_mt}</td>
                    <td style={{ padding: '5px 10px', borderBottom: '1px solid #1e293b' }}>{r.qty_kg}</td>
                    <td style={{ padding: '5px 10px', borderBottom: '1px solid #1e293b', color: '#94a3b8' }}>{r.storage_location || '-'}</td>
                    <td style={{ padding: '5px 10px', borderBottom: '1px solid #1e293b' }}>{r.is_sample ? '✅' : '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>

      {/* ── 7. PDF → Excel 변환 ─────────────────────────────────────────── */}
      <Section title="🔄 PDF → Excel 변환">
        <p style={{ fontSize: 12, color: '#64748b', marginBottom: 10 }}>
          PDF 파일 업로드 → 표 데이터 추출 → Excel 다운로드
        </p>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <label style={{
            padding: '8px 14px', background: '#1e293b', border: '1px solid #334155',
            borderRadius: 6, cursor: 'pointer', fontSize: 13, color: '#38bdf8',
          }}>
            📂 PDF 선택 후 자동 변환
            <input type="file" accept=".pdf" style={{ display: 'none' }}
              onChange={async e => {
                const file = e.target.files?.[0]; if (!file) return;
                setL('conv', true); setConvResult(null);
                try {
                  await uploadFile(file, `${BASE}/pdf-to-excel`);
                  showToast('✅ PDF→Excel 변환 완료 — 다운로드됩니다', true);
                  setConvResult({ success: true, filename: file.name });
                } catch (err) { showToast(`❌ ${err.message}`, false); }
                setL('conv', false); e.target.value = '';
              }} />
          </label>
          {loading.conv && <span style={{ color: '#64748b', fontSize: 13 }}>변환 중...</span>}
          {convResult?.success && <span style={{ fontSize: 12, color: '#34d399' }}>✅ 완료</span>}
        </div>
      </Section>

      {toast && <Toast msg={toast.msg} ok={toast.ok} />}
    </div>
  );
}
