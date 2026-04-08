import { useState } from 'react';
import { fetchJson } from '../api/client';

const sevColors = {
  ERROR: { bg: '#fef2f2', fg: '#991b1b', border: '#fecaca' },
  WARNING: { bg: '#fffbeb', fg: '#92400e', border: '#fde68a' },
  INFO: { bg: '#eff6ff', fg: '#1e40af', border: '#bfdbfe' },
};

export default function IntegrityPage() {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const runCheck = async () => {
    setLoading(true);
    try {
      const data = await fetchJson('/tools/integrity-check');
      setResult(data);
    } catch (e) {
      setResult({ success: false, total_issues: -1, issues: [{ type: 'FETCH_ERROR', severity: 'ERROR', message: e.message }] });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: 24 }}>
      <h2 style={{ marginBottom: 16 }}>DB Integrity Check</h2>
      <button onClick={runCheck} disabled={loading}
        style={{ padding: '8px 24px', fontWeight: 700, fontSize: 13, background: '#2563eb', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', marginBottom: 16 }}>
        {loading ? '검사 중...' : '정합성 검사 실행'}
      </button>

      {result && (
        <>
          <div style={{
            padding: 12, borderRadius: 8, marginBottom: 16,
            background: result.total_issues === 0 ? '#f0fdf4' : '#fef2f2',
            border: `1px solid ${result.total_issues === 0 ? '#bbf7d0' : '#fecaca'}`,
            fontSize: 14, fontWeight: 700,
            color: result.total_issues === 0 ? '#166534' : '#991b1b',
          }}>
            {result.total_issues === 0 ? 'All Clear — 이슈 없음' : `${result.total_issues}건 이슈 발견`}
          </div>

          {result.issues?.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {result.issues.map((issue, i) => {
                const c = sevColors[issue.severity] || sevColors.INFO;
                return (
                  <div key={i} style={{ padding: '10px 14px', borderRadius: 6, background: c.bg, border: `1px solid ${c.border}` }}>
                    <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 4 }}>
                      <span style={{
                        fontSize: 10, fontWeight: 700, padding: '2px 6px', borderRadius: 4,
                        background: c.fg, color: '#fff',
                      }}>{issue.severity}</span>
                      <span style={{ fontSize: 11, fontWeight: 600, color: '#475569' }}>{issue.type}</span>
                    </div>
                    <div style={{ fontSize: 12, color: c.fg }}>{issue.message}</div>
                    {issue.details && (
                      <div style={{ fontSize: 11, color: '#64748b', marginTop: 4 }}>
                        {issue.details.slice(0, 10).join(', ')}{issue.details.length > 10 ? ` ... (+${issue.details.length - 10})` : ''}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {result.generated_at && (
            <div style={{ marginTop: 8, fontSize: 10, color: '#94a3b8', textAlign: 'right' }}>
              Generated: {result.generated_at}
            </div>
          )}
        </>
      )}
    </div>
  );
}
