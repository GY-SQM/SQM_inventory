import { useState } from 'react';
import { addRecentFile } from '../utils/recentFiles';
import Modal from './Modal';

const BASE = '/api/inbound';

// ── 스타일 ──────────────────────────────────────────────────────────────────
const inputS = {
  width: '100%', padding: '6px 10px', boxSizing: 'border-box',
  border: '1px solid #334155', borderRadius: 6, fontSize: 13,
  background: '#0f172a', color: '#f1f5f9',
};
const labelS  = { display: 'block', fontSize: 11, fontWeight: 700, marginBottom: 4, color: '#94a3b8' };
const row2    = { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 12 };
const row3    = { display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, marginBottom: 12 };
const btnS    = (bg, disabled) => ({
  padding: '8px 18px', border: 'none', borderRadius: 6,
  color: disabled ? '#64748b' : '#fff',
  background: disabled ? '#334155' : bg,
  fontSize: 13, fontWeight: 600,
  cursor: disabled ? 'not-allowed' : 'pointer',
});

// ── 서류 업로드 카드 ─────────────────────────────────────────────────────────
const DOC_DEFS = [
  { key: 'pl', label: '📦 PL (Packing List)', required: true,  color: '#22c55e' },
  { key: 'fa', label: '🧾 FA (Invoice)',       required: true,  color: '#3b82f6' },
  { key: 'bl', label: '📄 BL (선하증권)',      required: true,  color: '#8b5cf6' },
  { key: 'do', label: '🚢 DO (선택)',          required: false, color: '#64748b' },
];

/**
 * 파일명에서 문서 유형(bl/pl/fa/do)을 자동 감지합니다.
 * Android에서 폴더 선택 대신 여러 파일을 선택할 때 사용합니다.
 * 우선순위: DO > BL > PL > FA (DO/BL은 고유 키워드로 오탐이 적음)
 * @param {string} name - 파일명
 * @returns {'bl'|'pl'|'fa'|'do'|null}
 */
export function detectDocType(name) {
  const n = name.toLowerCase();
  // _ 도 구분자로 처리: (?:^|[^a-z0-9]) ... (?:[^a-z0-9]|$)
  // [_\s.-]? 로 구분자 제한 (임의 문자 .? 미사용)
  const has = (pat) => pat.test(n);
  if (has(/delivery[_\s.-]?order/) || has(/(?:^|[^a-z0-9])do(?:[^a-z0-9]|$)/)) return 'do';
  if (has(/bill[_\s.-]?of[_\s.-]?lading/) || has(/선하증권/) || has(/(?:^|[^a-z0-9])bl(?:[^a-z0-9]|$)/)) return 'bl';
  if (has(/packing[_\s.-]?list/) || has(/packinglist/) || has(/(?:^|[^a-z0-9])pl(?:[^a-z0-9]|$)/)) return 'pl';
  if (has(/commercial[_\s.-]?invoice/) || has(/invoice/) || has(/(?:^|[^a-z0-9])fa(?:[^a-z0-9]|$)/)) return 'fa';
  return null;
}

function DocCard({ def, file, onChange }) {
  return (
    <div style={{
      border: `2px ${file ? 'solid' : 'dashed'} ${file ? def.color : '#334155'}`,
      borderRadius: 8, padding: '12px 14px',
      background: file ? `${def.color}11` : '#0f172a',
      transition: 'all 0.2s',
    }}>
      <div style={{ fontSize: 12, fontWeight: 700, color: file ? def.color : '#64748b', marginBottom: 6 }}>
        {def.label} {def.required && <span style={{ color: '#ef4444' }}>*</span>}
      </div>
      {file ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 11, color: '#94a3b8', flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            ✅ {file.name}
          </span>
          <button onClick={() => onChange(null)}
            style={{ background: 'none', border: 'none', color: '#ef4444', cursor: 'pointer', fontSize: 14 }}>✕</button>
        </div>
      ) : (
        <label style={{ cursor: 'pointer', display: 'block' }}>
          <input type="file" accept=".pdf" onChange={e => onChange(e.target.files[0] || null)}
            style={{ display: 'none' }} />
          <div style={{ fontSize: 12, color: '#475569', textAlign: 'center', padding: '4px 0' }}>
            클릭하여 PDF 선택
          </div>
        </label>
      )}
    </div>
  );
}

/**
 * 안드로이드/모바일에서 여러 PDF를 한 번에 선택해 자동 분류하는 컴포넌트.
 * Android 브라우저는 webkitdirectory를 지원하지 않으므로
 * multiple 속성으로 여러 파일을 선택한 뒤 파일명으로 자동 분류합니다.
 */
function AndroidMultiUpload({ onAssign }) {
  const [preview, setPreview] = useState(null); // { bl, pl, fa, do, unmatched }

  const handleChange = (e) => {
    const selected = Array.from(e.target.files || []);
    if (!selected.length) return;

    const result = { bl: null, pl: null, fa: null, do: null, unmatched: [], duplicates: [] };
    for (const file of selected) {
      const type = detectDocType(file.name);
      if (type && !result[type]) {
        result[type] = file;
      } else if (type && result[type]) {
        // 같은 유형이 이미 배정됨 → 중복으로 별도 처리
        result.duplicates.push({ file, type });
      } else {
        result.unmatched.push(file);
      }
    }
    setPreview(result);
    // 미리보기를 설정하면 상위 컴포넌트에 즉시 반영
    onAssign({ bl: result.bl, pl: result.pl, fa: result.fa, do: result.do });
  };

  return (
    <div style={{
      background: '#0c1a2e', border: '2px dashed #1d4ed8',
      borderRadius: 10, padding: '14px 16px', marginBottom: 14,
    }}>
      <div style={{ fontSize: 12, fontWeight: 700, color: '#60a5fa', marginBottom: 8 }}>
        📱 안드로이드 / 모바일 파일 선택
      </div>
      <div style={{ fontSize: 11, color: '#64748b', marginBottom: 10 }}>
        여러 PDF 파일을 한 번에 선택하면 파일명 기준으로 자동 분류합니다.<br />
        <span style={{ color: '#94a3b8' }}>
          (파일명에 BL / PL / FA / DO 포함 시 자동 배정)
        </span>
      </div>
      <label style={{
        display: 'inline-block', padding: '8px 18px',
        background: '#1d4ed8', color: '#fff', borderRadius: 6,
        fontSize: 13, fontWeight: 600, cursor: 'pointer',
      }}>
        📂 파일 선택 (여러 개)
        <input
          type="file"
          accept=".pdf"
          multiple
          onChange={handleChange}
          style={{ display: 'none' }}
        />
      </label>

      {preview && (
        <div style={{ marginTop: 12, fontSize: 11 }}>
          {DOC_DEFS.map(def => (
            <div key={def.key} style={{
              display: 'flex', alignItems: 'center', gap: 6,
              padding: '3px 0', color: preview[def.key] ? def.color : '#475569',
            }}>
              <span style={{ width: 28, fontWeight: 700 }}>{def.key.toUpperCase()}</span>
              <span>{preview[def.key] ? `✅ ${preview[def.key].name}` : '— 미배정'}</span>
            </div>
          ))}
          {preview.duplicates?.length > 0 && (
            <div style={{ marginTop: 6, color: '#f97316' }}>
              ⚠️ 중복 유형(미배정): {preview.duplicates.map(d => `${d.file.name}(${d.type.toUpperCase()})`).join(', ')}
            </div>
          )}
          {preview.unmatched.length > 0 && (
            <div style={{ marginTop: 4, color: '#fbbf24' }}>
              ❓ 유형 미감지: {preview.unmatched.map(f => f.name).join(', ')}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ── 미리보기 행 ─────────────────────────────────────────────────────────────
function PreviewRow({ label, value, highlight }) {
  if (!value && value !== 0) return null;
  return (
    <tr>
      <td style={{ fontSize: 12, color: '#64748b', padding: '3px 8px', whiteSpace: 'nowrap' }}>{label}</td>
      <td style={{ fontSize: 12, color: highlight ? '#38bdf8' : '#f1f5f9', padding: '3px 8px', fontWeight: highlight ? 700 : 400 }}>{value}</td>
    </tr>
  );
}

const INIT_FORM = {
  lot_no: '', product_name: '', bl_no: '', sap_no: '',
  total_weight_kg: '', bag_count: '', location: '',
  container_no: '', invoice_no: '', ship_date: '', arrival_date: '', warehouse: '',
};

export default function InboundModal({ open, onClose }) {
  const [step,        setStep]        = useState('upload');  // upload|preview|form|result
  const [files,       setFiles]       = useState({ bl: null, pl: null, fa: null, do: null });
  const [preview,     setPreview]     = useState(null);
  const [form,        setForm]        = useState(INIT_FORM);
  const [result,      setResult]      = useState(null);
  const [loading,     setLoading]     = useState(false);
  const [msg,         setMsg]         = useState(null);

  const setFile = (key, f) => setFiles(prev => ({ ...prev, [key]: f }));
  const setField = (k, v) => setForm(prev => ({ ...prev, [k]: v }));

  const hasRequired = files.bl || files.pl || files.fa;

  // ── Step1: PDF 파싱 미리보기 ────────────────────────────────────────────
  const handleParsePreview = async () => {
    if (!hasRequired) { setMsg({ ok: false, text: 'BL / PL / FA 중 최소 1개가 필요합니다.' }); return; }
    setLoading(true); setMsg(null);
    try {
      const fd = new FormData();
      if (files.bl) fd.append('bl_file', files.bl);
      if (files.pl) fd.append('pl_file', files.pl);
      if (files.fa) fd.append('fa_file', files.fa);
      if (files.do) fd.append('do_file', files.do);

      const r = await fetch(`${BASE}/parse-preview`, { method: 'POST', body: fd });
      const d = await r.json();

      if (d.success) {
        // 파싱 결과를 폼에 자동 채우기
        const pd = d.data || {};
        setForm({
          lot_no:         pd.lot_no        || '',
          product_name:   pd.product       || '',
          bl_no:          pd.bl_no         || '',
          sap_no:         pd.sap_no        || '',
          total_weight_kg:pd.net_weight    || '',
          bag_count:      pd.mxbg_pallet   || pd.tonbag_count || '',
          location:       '',
          container_no:   pd.container_no  || '',
          invoice_no:     pd.invoice_no    || '',
          ship_date:      pd.ship_date     || '',
          arrival_date:   pd.arrival_date  || '',
          warehouse:      pd.warehouse     || '',
        });
        setPreview(d);
        setStep('preview');
      } else {
        setMsg({ ok: false, text: d.message || '파싱 실패' });
      }
    } catch (e) { setMsg({ ok: false, text: e.message }); }
    setLoading(false);
  };

  // ── Step2: 입고 확정 (DB 저장) ──────────────────────────────────────────
  const handleConfirm = async () => {
    setLoading(true); setMsg(null);
    try {
      const fd = new FormData();
      if (files.bl) fd.append('bl_file', files.bl);
      if (files.pl) fd.append('pl_file', files.pl);
      if (files.fa) fd.append('fa_file', files.fa);
      if (files.do) fd.append('do_file', files.do);
      const fileNames = Object.values(files).filter(Boolean).map(f => f.name).join(',');
      fd.append('source_file', fileNames);

      const r = await fetch(`${BASE}/confirm`, { method: 'POST', body: fd });
      const d = await r.json();
      setResult(d);
      setStep('result');
      if (d.success) {
        const names = Object.values(files).filter(Boolean).map(f => f.name).join(', ');
        addRecentFile({
          filename: names || d.lot_no || 'PDF 입고',
          type: '입고',
          path: '/inventory',
        });
      }
    } catch (e) { setMsg({ ok: false, text: e.message }); }
    setLoading(false);
  };

  // ── Step2b: 수동 입력으로 저장 ──────────────────────────────────────────
  const handleManualSave = async () => {
    if (!form.lot_no || !form.bl_no || !form.total_weight_kg || !form.bag_count) {
      setMsg({ ok: false, text: 'LOT NO / BL NO / 중량 / 톤백 수는 필수입니다.' }); return;
    }
    setLoading(true); setMsg(null);
    try {
      const r = await fetch(`${BASE}/create`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          ...form,
          total_weight_kg: parseFloat(form.total_weight_kg) || 0,
          bag_count:       parseInt(form.bag_count)         || 0,
          source_type:     hasRequired ? 'PDF' : 'WEB_MANUAL',
          source_file:     Object.values(files).filter(Boolean).map(f => f.name).join(',') || '',
        }),
      });
      const d = await r.json();
      setResult(d);
      setStep('result');
      if (d.success) {
        const names = Object.values(files).filter(Boolean).map(f => f.name).join(', ');
        addRecentFile({
          filename: names || form.lot_no || '수동 입고',
          type: '입고',
          path: '/inventory',
        });
      }
    } catch (e) { setMsg({ ok: false, text: e.message }); }
    setLoading(false);
  };

  const handleClose = () => {
    setStep('upload'); setFiles({ bl: null, pl: null, fa: null, do: null });
    setPreview(null); setForm(INIT_FORM); setResult(null); setMsg(null);
    onClose();
  };

  return (
    <Modal open={open} onClose={handleClose} title="📥 PDF 입고 (원스톱)" width={700}>

      {/* ── Step 1: PDF 서류 업로드 ───────────────────────────────────────── */}
      {step === 'upload' && (
        <div>
          <p style={{ fontSize: 12, color: '#64748b', marginBottom: 12 }}>
            BL + PL + FA 3종 필수 / DO 선택. 선택 후 [파싱 미리보기] 클릭.
          </p>

          {/* ── 안드로이드/모바일: 여러 파일 한 번에 선택 ── */}
          <AndroidMultiUpload onAssign={assigned => setFiles(prev => ({ ...prev, ...assigned }))} />

          {/* ── PC: 개별 카드 선택 ── */}
          <div style={{ fontSize: 11, color: '#64748b', marginBottom: 6 }}>
            또는 아래에서 파일을 개별 선택하세요.
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, marginBottom: 16 }}>
            {DOC_DEFS.map(def => (
              <DocCard key={def.key} def={def} file={files[def.key]} onChange={f => setFile(def.key, f)} />
            ))}
          </div>
          {msg && (
            <div style={{ padding: '8px 12px', borderRadius: 6, marginBottom: 12, fontSize: 12,
              background: msg.ok ? '#064e3b' : '#450a0a', color: msg.ok ? '#34d399' : '#f87171' }}>
              {msg.text}
            </div>
          )}
          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            <button style={btnS('#22c55e', !hasRequired || loading)}
              onClick={handleParsePreview} disabled={!hasRequired || loading}>
              {loading ? '파싱 중...' : '🔍 파싱 미리보기'}
            </button>
            <button style={btnS('#64748b', false)} onClick={() => setStep('preview')}>
              ✏️ 수동 입력
            </button>
          </div>
        </div>
      )}

      {/* ── Step 2: 파싱 미리보기 + 폼 수정 ─────────────────────────────── */}
      {(step === 'preview') && (
        <div>
          {preview?.data && (
            <div style={{ background: '#0f172a', border: '1px solid #334155', borderRadius: 8, padding: '12px 16px', marginBottom: 16 }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: '#38bdf8', marginBottom: 8 }}>📊 파싱 결과 미리보기</div>
              <table style={{ width: '100%' }}>
                <tbody>
                  <PreviewRow label="LOT NO"      value={preview.data.lot_no}       highlight />
                  <PreviewRow label="BL NO"       value={preview.data.bl_no}        highlight />
                  <PreviewRow label="제품"        value={preview.data.product} />
                  <PreviewRow label="NET 중량"    value={preview.data.net_weight ? `${preview.data.net_weight} kg` : null} />
                  <PreviewRow label="톤백 수"     value={preview.data.tonbag_count || preview.data.mxbg_pallet} />
                  <PreviewRow label="컨테이너"    value={preview.data.container_no} />
                  <PreviewRow label="Invoice NO"  value={preview.data.invoice_no} />
                  <PreviewRow label="선적일"      value={preview.data.ship_date} />
                  <PreviewRow label="도착일"      value={preview.data.arrival_date} />
                </tbody>
              </table>
              {preview.warnings?.length > 0 && (
                <div style={{ marginTop: 8, fontSize: 11, color: '#fbbf24' }}>
                  ⚠️ {preview.warnings.join(' / ')}
                </div>
              )}
            </div>
          )}

          {/* 폼 수정 */}
          <div style={{ fontSize: 12, color: '#94a3b8', marginBottom: 10 }}>
            내용을 확인하고 필요 시 수정 후 [입고 확정]을 누르세요.
          </div>
          <div style={row2}>
            <div><span style={labelS}>LOT NO *</span><input style={inputS} value={form.lot_no} onChange={e => setField('lot_no', e.target.value)} /></div>
            <div><span style={labelS}>제품명 *</span><input style={inputS} value={form.product_name} onChange={e => setField('product_name', e.target.value)} /></div>
          </div>
          <div style={row2}>
            <div><span style={labelS}>BL NO *</span><input style={inputS} value={form.bl_no} onChange={e => setField('bl_no', e.target.value)} /></div>
            <div><span style={labelS}>SAP NO</span><input style={inputS} value={form.sap_no} onChange={e => setField('sap_no', e.target.value)} /></div>
          </div>
          <div style={row3}>
            <div><span style={labelS}>총 중량 (kg) *</span><input style={inputS} type="number" value={form.total_weight_kg} onChange={e => setField('total_weight_kg', e.target.value)} /></div>
            <div><span style={labelS}>톤백 수 *</span><input style={inputS} type="number" value={form.bag_count} onChange={e => setField('bag_count', e.target.value)} /></div>
            <div><span style={labelS}>위치</span><input style={inputS} value={form.location} onChange={e => setField('location', e.target.value)} /></div>
          </div>
          <div style={row2}>
            <div><span style={labelS}>컨테이너 NO</span><input style={inputS} value={form.container_no} onChange={e => setField('container_no', e.target.value)} /></div>
            <div><span style={labelS}>Invoice NO</span><input style={inputS} value={form.invoice_no} onChange={e => setField('invoice_no', e.target.value)} /></div>
          </div>
          <div style={row3}>
            <div><span style={labelS}>선적일</span><input style={inputS} type="date" value={form.ship_date} onChange={e => setField('ship_date', e.target.value)} /></div>
            <div><span style={labelS}>도착일</span><input style={inputS} type="date" value={form.arrival_date} onChange={e => setField('arrival_date', e.target.value)} /></div>
            <div><span style={labelS}>창고</span><input style={inputS} value={form.warehouse} onChange={e => setField('warehouse', e.target.value)} /></div>
          </div>

          {msg && (
            <div style={{ padding: '8px 12px', borderRadius: 6, marginBottom: 8, fontSize: 12,
              background: msg.ok ? '#064e3b' : '#450a0a', color: msg.ok ? '#34d399' : '#f87171' }}>
              {msg.text}
            </div>
          )}

          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 16 }}>
            {/* PDF 파싱으로 들어온 경우 confirm 사용, 수동인 경우 manualSave */}
            {hasRequired && preview ? (
              <button style={btnS('#22c55e', loading)} onClick={handleConfirm} disabled={loading}>
                {loading ? '처리 중...' : '✅ 입고 확정 (PDF 파싱 결과 저장)'}
              </button>
            ) : (
              <button style={btnS('#22c55e', loading)} onClick={handleManualSave} disabled={loading}>
                {loading ? '처리 중...' : '✅ 입고 확정 (수동 저장)'}
              </button>
            )}
            <button style={btnS('#475569', false)} onClick={() => setStep('upload')}>← 뒤로</button>
          </div>
        </div>
      )}

      {/* ── Step 3: 결과 ─────────────────────────────────────────────────── */}
      {step === 'result' && result && (
        <div>
          <div style={{
            padding: 16, borderRadius: 8, marginBottom: 16,
            background: result.success ? '#064e3b' : '#450a0a',
            border: `1px solid ${result.success ? '#065f46' : '#7f1d1d'}`,
          }}>
            <div style={{ fontSize: 15, fontWeight: 700, color: result.success ? '#34d399' : '#f87171', marginBottom: 6 }}>
              {result.success ? '✅ 입고 완료' : '❌ 입고 실패'}
            </div>
            <div style={{ fontSize: 13, color: '#f1f5f9' }}>{result.message}</div>
          </div>

          {result.success && (
            <table style={{ fontSize: 12, width: '100%', marginBottom: 16 }}>
              <tbody>
                <PreviewRow label="LOT NO"     value={result.lot_no}          highlight />
                <PreviewRow label="생성 톤백"   value={result.created_tonbags ? `${result.created_tonbags}개` : null} />
              </tbody>
            </table>
          )}

          {result.warnings?.length > 0 && (
            <div style={{ background: '#3b2a00', border: '1px solid #92400e', borderRadius: 6, padding: '8px 12px', marginBottom: 12, fontSize: 12, color: '#fbbf24' }}>
              <b>⚠️ 경고:</b>
              <ul style={{ margin: '4px 0 0', paddingLeft: 16 }}>
                {result.warnings.map((w, i) => <li key={i}>{w}</li>)}
              </ul>
            </div>
          )}

          {result.errors?.length > 0 && (
            <div style={{ background: '#450a0a', border: '1px solid #7f1d1d', borderRadius: 6, padding: '8px 12px', marginBottom: 12, fontSize: 12, color: '#f87171' }}>
              <b>❌ 오류:</b>
              <ul style={{ margin: '4px 0 0', paddingLeft: 16 }}>
                {result.errors.map((e, i) => <li key={i}>{e}</li>)}
              </ul>
            </div>
          )}

          <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
            {result.success && (
              <button style={btnS('#3b82f6', false)} onClick={() => { setStep('upload'); setFiles({ bl: null, pl: null, fa: null, do: null }); setPreview(null); setResult(null); setMsg(null); setForm(INIT_FORM); }}>
                ➕ 추가 입고
              </button>
            )}
            <button style={btnS('#475569', false)} onClick={handleClose}>닫기</button>
          </div>
        </div>
      )}
    </Modal>
  );
}
