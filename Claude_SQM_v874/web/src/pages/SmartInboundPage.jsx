import { useState, useRef, useCallback } from 'react';

const DOC_TYPES = [
  { key: 'bl', label: 'B/L', icon: '🚢', desc: 'Bill of Lading' },
  { key: 'pl', label: 'P/L', icon: '📦', desc: 'Packing List' },
  { key: 'fa', label: 'F/A', icon: '💰', desc: 'Freight/Account' },
  { key: 'do', label: 'D/O', icon: '📋', desc: 'Delivery Order' },
];

const cardStyle = {
  border: '1px solid var(--border)',
  borderRadius: 12,
  padding: 20,
  background: 'var(--bg-card)',
};

const btnPrimary = {
  padding: '8px 20px',
  borderRadius: 8,
  border: 'none',
  background: 'var(--accent)',
  color: '#fff',
  fontWeight: 600,
  fontSize: 13,
  cursor: 'pointer',
};

const btnDisabled = { ...btnPrimary, opacity: 0.4, cursor: 'not-allowed' };

function confidenceColor(score) {
  if (score >= 90) return 'var(--success)';
  if (score >= 70) return 'var(--warning)';
  return 'var(--error)';
}

function ConfidenceBadge({ score }) {
  if (score == null) return null;
  const color = confidenceColor(score);
  return (
    <span style={{
      display: 'inline-block', padding: '2px 8px', borderRadius: 4,
      background: color + '22', color, border: `1px solid ${color}44`,
      fontSize: 11, fontWeight: 700,
    }}>
      {score}%
    </span>
  );
}

function Toast({ message, type, onClose }) {
  if (!message) return null;
  const bg = type === 'error' ? 'var(--error)' : type === 'success' ? 'var(--success)' : 'var(--accent)';
  return (
    <div style={{
      position: 'fixed', top: 20, right: 20, zIndex: 9999,
      padding: '12px 24px', borderRadius: 8, background: bg, color: '#fff',
      fontSize: 13, fontWeight: 600, boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
      display: 'flex', alignItems: 'center', gap: 12,
    }}>
      {message}
      <span onClick={onClose} style={{ cursor: 'pointer', opacity: 0.8, fontSize: 16 }}>×</span>
    </div>
  );
}

function FileUploadCard({ docType, file, onFileSelect, loading }) {
  const inputRef = useRef(null);
  const [dragOver, setDragOver] = useState(false);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer.files[0];
    if (f) onFileSelect(docType.key, f);
  }, [docType.key, onFileSelect]);

  const handleDragOver = useCallback((e) => {
    e.preventDefault();
    setDragOver(true);
  }, []);

  return (
    <div
      onDrop={handleDrop}
      onDragOver={handleDragOver}
      onDragLeave={() => setDragOver(false)}
      onClick={() => !loading && inputRef.current?.click()}
      style={{
        ...cardStyle,
        border: dragOver
          ? '2px dashed var(--accent)'
          : file
            ? '2px solid var(--success)'
            : '2px dashed var(--border)',
        textAlign: 'center',
        cursor: loading ? 'not-allowed' : 'pointer',
        transition: 'border-color 0.2s, background 0.2s',
        background: dragOver ? 'var(--accent-light)' : 'var(--bg-card)',
        minHeight: 120,
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
        gap: 6,
      }}
    >
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.png,.jpg"
        style={{ display: 'none' }}
        onChange={(e) => {
          const f = e.target.files[0];
          if (f) onFileSelect(docType.key, f);
          e.target.value = '';
        }}
      />
      <div style={{ fontSize: 28 }}>{docType.icon}</div>
      <div style={{ fontWeight: 700, fontSize: 14, color: 'var(--text-primary)' }}>{docType.label}</div>
      <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{docType.desc}</div>
      {file ? (
        <div style={{
          marginTop: 4, fontSize: 11, color: 'var(--success)',
          maxWidth: '100%', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
        }}>
          {file.name}
        </div>
      ) : (
        <div style={{ marginTop: 4, fontSize: 11, color: 'var(--text-muted)' }}>
          PDF / PNG / JPG
        </div>
      )}
    </div>
  );
}

function ParseStatusBar({ parsedResults }) {
  const entries = DOC_TYPES.map(dt => ({
    ...dt,
    result: parsedResults[dt.key],
  })).filter(e => e.result);

  if (entries.length === 0) {
    return (
      <div style={{ ...cardStyle, marginBottom: 16 }}>
        <h4 style={{ margin: 0, marginBottom: 8, fontSize: 14, color: 'var(--text-secondary)' }}>
          파싱 상태
        </h4>
        <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>
          서류를 업로드하고 파싱 버튼을 눌러주세요.
        </div>
      </div>
    );
  }

  return (
    <div style={{ ...cardStyle, marginBottom: 16 }}>
      <h4 style={{ margin: 0, marginBottom: 12, fontSize: 14, color: 'var(--text-secondary)' }}>
        파싱 상태
      </h4>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 12 }}>
        {entries.map(e => (
          <div key={e.key} style={{
            flex: '1 1 200px', padding: '10px 14px', borderRadius: 8,
            border: '1px solid var(--border)', background: 'var(--bg-secondary)',
            display: 'flex', alignItems: 'center', gap: 10,
          }}>
            <span style={{ fontSize: 20 }}>{e.icon}</span>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 12, fontWeight: 700, color: 'var(--text-primary)' }}>
                {e.label} — {e.result.carrier_name || 'Unknown'}
              </div>
              <div style={{ fontSize: 11, color: 'var(--text-muted)', display: 'flex', gap: 8, alignItems: 'center' }}>
                <span style={{
                  padding: '1px 6px', borderRadius: 3, fontSize: 10, fontWeight: 600,
                  background: e.result.parse_method === 'TEMPLATE' ? '#22c55e22' : '#3b82f622',
                  color: e.result.parse_method === 'TEMPLATE' ? '#22c55e' : '#3b82f6',
                }}>
                  {e.result.parse_method || 'AI'}
                </span>
                <ConfidenceBadge score={e.result.confidence} />
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ResultTable({ docType, result, onFieldChange }) {
  if (!result || !result.fields) return null;

  const fields = result.fields;
  const fieldKeys = Object.keys(fields);
  if (fieldKeys.length === 0) return null;

  return (
    <div style={{ ...cardStyle, marginBottom: 12 }}>
      <h4 style={{ margin: 0, marginBottom: 10, fontSize: 13, color: 'var(--text-secondary)' }}>
        {docType.icon} {docType.label} 파싱 결과
      </h4>
      <div style={{ overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr>
              <th style={thStyle}>필드명</th>
              <th style={thStyle}>추출값</th>
              <th style={thStyle}>신뢰도</th>
              <th style={thStyle}>수정값</th>
            </tr>
          </thead>
          <tbody>
            {fieldKeys.map(fk => {
              const f = fields[fk];
              const val = typeof f === 'object' ? (f.value ?? '') : f;
              const conf = typeof f === 'object' ? f.confidence : null;
              return (
                <tr key={fk}>
                  <td style={tdStyle}>{fk}</td>
                  <td style={tdStyle}>{String(val)}</td>
                  <td style={{ ...tdStyle, textAlign: 'center' }}>
                    <ConfidenceBadge score={conf} />
                  </td>
                  <td style={tdStyle}>
                    <input
                      type="text"
                      defaultValue={String(val)}
                      onChange={(e) => onFieldChange(docType.key, fk, e.target.value)}
                      style={{
                        width: '100%', padding: '4px 8px', borderRadius: 4,
                        border: '1px solid var(--border)', background: 'var(--bg-secondary)',
                        color: 'var(--text-primary)', fontSize: 12,
                        outline: 'none',
                      }}
                    />
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

const thStyle = {
  padding: '8px 10px', textAlign: 'left',
  borderBottom: '2px solid var(--border)', fontSize: 11, fontWeight: 700,
  color: 'var(--text-secondary)', whiteSpace: 'nowrap',
};

const tdStyle = {
  padding: '6px 10px', borderBottom: '1px solid var(--border)',
  fontSize: 12, color: 'var(--text-primary)',
};

function CrossValidationCard({ crossValidation }) {
  if (!crossValidation) return null;

  const checks = crossValidation.checks || [];
  const statusStyle = (s) => {
    if (s === 'PASS') return { color: 'var(--success)', bg: '#22c55e18' };
    if (s === 'FAIL') return { color: 'var(--error)', bg: '#ef444418' };
    return { color: 'var(--text-muted)', bg: 'var(--bg-secondary)' };
  };

  return (
    <div style={{ ...cardStyle, marginBottom: 16 }}>
      <h4 style={{ margin: 0, marginBottom: 12, fontSize: 14, color: 'var(--text-secondary)' }}>
        교차검증 결과
      </h4>
      {checks.length === 0 ? (
        <div style={{ color: 'var(--text-muted)', fontSize: 13 }}>검증 항목 없음</div>
      ) : (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
          {checks.map((c, i) => {
            const st = statusStyle(c.status);
            return (
              <div key={i} style={{
                flex: '1 1 220px', padding: '10px 14px', borderRadius: 8,
                border: `1px solid ${st.color}33`, background: st.bg,
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
                  <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)' }}>
                    {c.label || c.check_name || `Check ${i + 1}`}
                  </span>
                  <span style={{
                    padding: '2px 8px', borderRadius: 4,
                    fontSize: 10, fontWeight: 700,
                    color: st.color,
                    background: st.color + '22',
                  }}>
                    {c.status}
                  </span>
                </div>
                {c.message && (
                  <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{c.message}</div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default function SmartInboundPage() {
  const [files, setFiles] = useState({ bl: null, pl: null, fa: null, do: null });
  const [parsedResults, setParsedResults] = useState({ bl: null, pl: null, fa: null, do: null });
  const [corrected, setCorrected] = useState({});
  const [crossValidation, setCrossValidation] = useState(null);
  const [loading, setLoading] = useState(false);
  const [saveTemplate, setSaveTemplate] = useState(false);
  const [toast, setToast] = useState(null);

  const showToast = useCallback((message, type = 'info') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3500);
  }, []);

  const handleFileSelect = useCallback((key, file) => {
    setFiles(prev => ({ ...prev, [key]: file }));
  }, []);

  const hasFiles = Object.values(files).some(Boolean);
  const hasParsed = Object.values(parsedResults).some(Boolean);

  const handleParse = useCallback(async () => {
    const entries = DOC_TYPES.filter(dt => files[dt.key]);
    if (entries.length === 0) {
      showToast('파일을 먼저 업로드하세요.', 'error');
      return;
    }
    setLoading(true);
    setCrossValidation(null);

    const newResults = { ...parsedResults };
    try {
      for (const dt of entries) {
        const fd = new FormData();
        fd.append('file', files[dt.key]);
        fd.append('doc_type', dt.key.toUpperCase());
        const res = await fetch('/api/smart-inbound/parse', { method: 'POST', body: fd });
        if (!res.ok) throw new Error(`${dt.label} 파싱 실패: ${res.status}`);
        newResults[dt.key] = await res.json();
      }
      setParsedResults(newResults);
      showToast(`${entries.length}건 파싱 완료`, 'success');
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setLoading(false);
    }
  }, [files, parsedResults, showToast]);

  const handleCrossValidate = useCallback(async () => {
    setLoading(true);
    try {
      const body = {
        bl_data: parsedResults.bl?.fields || null,
        pl_data: parsedResults.pl?.fields || null,
        fa_data: parsedResults.fa?.fields || null,
      };
      const res = await fetch('/api/smart-inbound/cross-validate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(`교차검증 실패: ${res.status}`);
      const data = await res.json();
      setCrossValidation(data);
      showToast('교차검증 완료', 'success');
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setLoading(false);
    }
  }, [parsedResults, showToast]);

  const handleFieldChange = useCallback((docKey, fieldKey, value) => {
    setCorrected(prev => ({
      ...prev,
      [docKey]: { ...(prev[docKey] || {}), [fieldKey]: value },
    }));
  }, []);

  const handleSave = useCallback(async () => {
    setLoading(true);
    try {
      const parsed = {};
      const corr = {};
      for (const dt of DOC_TYPES) {
        if (parsedResults[dt.key]) {
          parsed[dt.key] = parsedResults[dt.key];
          corr[dt.key] = corrected[dt.key] || {};
        }
      }
      const res = await fetch('/api/smart-inbound/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ parsed, corrected: corr, save_template: saveTemplate }),
      });
      if (!res.ok) throw new Error(`저장 실패: ${res.status}`);
      showToast('저장 완료!', 'success');
    } catch (err) {
      showToast(err.message, 'error');
    } finally {
      setLoading(false);
    }
  }, [parsedResults, corrected, saveTemplate, showToast]);

  return (
    <div style={{ padding: 24, maxWidth: 1200, margin: '0 auto' }}>
      <Toast message={toast?.message} type={toast?.type} onClose={() => setToast(null)} />

      {/* Header */}
      <div style={{ marginBottom: 20 }}>
        <h2 style={{ margin: 0, marginBottom: 4, fontSize: 20, color: 'var(--text-primary)' }}>
          스마트 입고 (AI)
        </h2>
        <p style={{ margin: 0, color: 'var(--text-secondary)', fontSize: 13 }}>
          AI 기반 자동 서류 파싱 — BL/PL/FA/DO 업로드 → 자동 인식 → 교차검증 → 입고
        </p>
      </div>

      {/* Upload Area */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
        gap: 12,
        marginBottom: 16,
      }}>
        {DOC_TYPES.map(dt => (
          <FileUploadCard
            key={dt.key}
            docType={dt}
            file={files[dt.key]}
            onFileSelect={handleFileSelect}
            loading={loading}
          />
        ))}
      </div>

      {/* Parse Button */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 20, alignItems: 'center' }}>
        <button
          onClick={handleParse}
          disabled={!hasFiles || loading}
          style={!hasFiles || loading ? btnDisabled : btnPrimary}
        >
          {loading ? '파싱 중...' : '파싱 실행'}
        </button>
        {hasParsed && (
          <button
            onClick={handleCrossValidate}
            disabled={loading}
            style={loading ? btnDisabled : {
              ...btnPrimary,
              background: 'transparent',
              color: 'var(--accent)',
              border: '1px solid var(--accent)',
            }}
          >
            교차검증
          </button>
        )}
      </div>

      {/* Parse Status Bar */}
      <ParseStatusBar parsedResults={parsedResults} />

      {/* Result Tables */}
      {DOC_TYPES.map(dt => (
        <ResultTable
          key={dt.key}
          docType={dt}
          result={parsedResults[dt.key]}
          onFieldChange={handleFieldChange}
        />
      ))}

      {/* Cross Validation */}
      <CrossValidationCard crossValidation={crossValidation} />

      {/* Save Bar */}
      {hasParsed && (
        <div style={{
          ...cardStyle,
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          position: 'sticky', bottom: 0, zIndex: 10,
          boxShadow: '0 -2px 12px rgba(0,0,0,0.15)',
        }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, color: 'var(--text-secondary)', cursor: 'pointer' }}>
            <input
              type="checkbox"
              checked={saveTemplate}
              onChange={(e) => setSaveTemplate(e.target.checked)}
              style={{ accentColor: 'var(--accent)' }}
            />
            템플릿 저장
          </label>
          <button
            onClick={handleSave}
            disabled={loading}
            style={loading ? btnDisabled : { ...btnPrimary, padding: '10px 32px', fontSize: 14 }}
          >
            {loading ? '저장 중...' : '저장'}
          </button>
        </div>
      )}
    </div>
  );
}
