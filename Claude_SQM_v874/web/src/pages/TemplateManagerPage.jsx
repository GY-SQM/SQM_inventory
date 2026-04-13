/**
 * TemplateManagerPage — 스마트 입고 템플릿 관리 (P2 읽기 전용)
 * 배치: web/src/pages/TemplateManagerPage.jsx
 */
import { useState, useEffect, useCallback } from 'react';

const thS = {
  padding: '7px 10px', background: '#0f172a', color: '#64748b',
  fontWeight: 700, fontSize: 11, textAlign: 'center',
  borderBottom: '2px solid #334155', whiteSpace: 'nowrap', position: 'sticky', top: 0,
};
const tdS = {
  padding: '6px 10px', borderBottom: '1px dashed rgba(51,65,85,0.3)',
  fontSize: 12, color: '#e2e8f0', whiteSpace: 'nowrap',
};
const tdC = { ...tdS, textAlign: 'center' };

export default function TemplateManagerPage() {
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState(null);

  const showToast = (msg, ok) => {
    setToast({ msg, ok });
    setTimeout(() => setToast(null), 3000);
  };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch('/api/smart-inbound/templates');
      const d = await r.json();
      setTemplates(d.rows || d.templates || []);
    } catch (e) {
      console.error(e);
      showToast('템플릿 목록 로드 실패: ' + e.message, false);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleDelete = async (id, carrier) => {
    if (!window.confirm(`'${carrier || id}' 템플릿을 삭제하시겠습니까?`)) return;
    try {
      const r = await fetch(`/api/smart-inbound/templates/${id}`, { method: 'DELETE' });
      const d = await r.json();
      if (d.success === false) throw new Error(d.message || '삭제 실패');
      showToast('템플릿 삭제 완료', true);
      load();
    } catch (e) {
      showToast('삭제 실패: ' + e.message, false);
    }
  };

  const fmtDate = (v) => {
    if (!v) return '-';
    return String(v).slice(0, 10);
  };

  const fmtRate = (v) => {
    if (v == null || v === '') return '-';
    const n = Number(v);
    if (isNaN(n)) return '-';
    return (n >= 1 ? n : n * 100).toFixed(1) + '%';
  };

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 4 }}>
        <h2 style={{ color: '#f1f5f9', margin: 0 }}>
          AI 템플릿 관리
        </h2>
        <button
          onClick={load}
          disabled={loading}
          style={{
            padding: '7px 16px', border: 'none', borderRadius: 6,
            background: loading ? '#334155' : '#334155',
            color: loading ? '#64748b' : '#94a3b8',
            fontSize: 12, fontWeight: 600, cursor: loading ? 'not-allowed' : 'pointer',
          }}
        >
          {loading ? '...' : '새로고침'}
        </button>
      </div>
      <p style={{ fontSize: 12, color: '#64748b', marginBottom: 16 }}>
        해운사별 서류 파싱 템플릿 -- AI 학습 결과를 규칙으로 변환
      </p>

      {loading && (
        <div style={{ padding: 32, textAlign: 'center', color: '#64748b', fontSize: 13 }}>
          Loading...
        </div>
      )}

      {!loading && templates.length === 0 && (
        <div style={{
          border: '1px solid #334155', borderRadius: 12, padding: 48,
          background: '#1e293b', textAlign: 'center', color: '#94a3b8',
        }}>
          <div style={{ fontSize: 40, marginBottom: 12, opacity: 0.5 }}>&#x1F4CB;</div>
          <div style={{ fontSize: 14, lineHeight: 1.6 }}>
            아직 등록된 템플릿이 없습니다.<br />
            스마트 입고에서 파싱하면 자동 생성됩니다.
          </div>
        </div>
      )}

      {!loading && templates.length > 0 && (
        <div style={{ overflow: 'auto', maxHeight: '72vh', border: '1px solid #334155', borderRadius: 8 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                {['해운사', '서류유형', '사용횟수', '성공률', '생성일', ''].map(h => (
                  <th key={h} style={thS}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {templates.map((t, i) => (
                <tr
                  key={t.id || t.template_id || i}
                  onMouseEnter={e => e.currentTarget.style.background = '#0f172a'}
                  onMouseLeave={e => e.currentTarget.style.background = ''}
                >
                  <td style={{ ...tdS, color: '#38bdf8', fontWeight: 600 }}>
                    {t.carrier || t.carrier_name || t.carrier_id || '-'}
                  </td>
                  <td style={tdC}>{t.doc_type || t.document_type || '-'}</td>
                  <td style={tdC}>{t.use_count ?? t.usage_count ?? '-'}</td>
                  <td style={tdC}>
                    <span style={{
                      color: Number(t.success_rate ?? t.accuracy ?? 0) >= 0.8 ? '#34d399' : '#f59e0b',
                      fontWeight: 600,
                    }}>
                      {fmtRate(t.success_rate ?? t.accuracy)}
                    </span>
                  </td>
                  <td style={{ ...tdC, fontSize: 11, color: '#64748b' }}>
                    {fmtDate(t.created_at || t.created)}
                  </td>
                  <td style={tdC}>
                    <button
                      onClick={() => handleDelete(t.id || t.template_id, t.carrier || t.carrier_name)}
                      style={{
                        padding: '3px 10px', fontSize: 11, fontWeight: 600,
                        border: 'none', borderRadius: 4, cursor: 'pointer',
                        background: '#450a0a', color: '#f87171',
                      }}
                    >
                      삭제
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {toast && (
        <div style={{
          position: 'fixed', bottom: 28, left: '50%', transform: 'translateX(-50%)',
          padding: '10px 24px', borderRadius: 8, fontSize: 13, fontWeight: 600, zIndex: 9999,
          background: toast.ok ? '#064e3b' : '#450a0a',
          color: toast.ok ? '#34d399' : '#f87171',
        }}>
          {toast.msg}
        </div>
      )}
    </div>
  );
}
