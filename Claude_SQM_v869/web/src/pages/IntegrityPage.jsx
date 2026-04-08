import { useState } from 'react';
import { fetchJson } from '../api/client';

const sevColors = {
  ERROR: { bg: '#fef2f2', fg: '#991b1b', border: '#fecaca' },
  WARNING: { bg: '#fffbeb', fg: '#92400e', border: '#fde68a' },
  INFO: { bg: '#eff6ff', fg: '#1e40af', border: '#bfdbfe' },
};

export default function IntegrityPage() {
  const [result,       setResult]       = useState(null);
  const [repairResult, setRepairResult] = useState(null);
  const [loading,      setLoading]      = useState(false);
  const [repairing,    setRepairing]    = useState(false);
  const [showConfirm,  setShowConfirm]  = useState(false);

  const runCheck = async () => {
    setLoading(true);
    setRepairResult(null);
    try {
      const data = await fetchJson('/tools/integrity-check');
      setResult(data);
    } catch (e) {
      setResult({ success: false, total_issues: -1, issues: [{ type: 'FETCH_ERROR', severity: 'ERROR', message: e.message }] });
    } finally {
      setLoading(false);
    }
  };

  const runRepair = async () => {
    setShowConfirm(false);
    setRepairing(true);
    try {
      const res = await fetch('/api/tools/integrity-repair', { method: 'POST' });
      const data = await res.json();
      setRepairResult(data);
      // 복구 후 재검사
      runCheck();
    } catch (e) {
      setRepairResult({ success: false, repaired_count: 0, details: [], error: e.message });
    } finally {
      setRepairing(false);
    }
  };

  return (
    <div style={{ padding: 24 }}>
      <h2 style={{ marginBottom: 8 }}>DB Integrity Check &amp; Repair</h2>
      <p style={{ fontSize: 12, color: '#64748b', marginBottom: 16 }}>
        재고 데이터 정합성을 검사하고, 발견된 이슈를 자동 복구합니다.
      </p>

      {/* 버튼 영역 */}
      <div style={{ display: 'flex', gap: 10, marginBottom: 16, alignItems: 'center' }}>
        <button onClick={runCheck} disabled={loading}
          style={{ padding: '8px 24px', fontWeight: 700, fontSize: 13, background: '#2563eb', color: '#fff', border: 'none', borderRadius: 6, cursor: loading ? 'not-allowed' : 'pointer' }}>
          {loading ? '검사 중...' : '🔍 정합성 검사'}
        </button>
        <button onClick={() => setShowConfirm(true)} disabled={repairing}
          style={{ padding: '8px 24px', fontWeight: 700, fontSize: 13, background: '#dc2626', color: '#fff', border: 'none', borderRadius: 6, cursor: repairing ? 'not-allowed' : 'pointer' }}>
          {repairing ? '복구 중...' : '🛠️ 자동 복구'}
        </button>
      </div>

      {/* 복구 확인 모달 */}
      {showConfirm && (
        <div style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 9999,
        }}>
          <div style={{ background: '#1e293b', border: '1px solid #475569', borderRadius: 10, padding: 28, maxWidth: 400, width: '90%' }}>
            <h3 style={{ color: '#f87171', marginBottom: 12 }}>⚠️ 복구 실행 확인</h3>
            <p style={{ fontSize: 13, color: '#cbd5e1', marginBottom: 8 }}>
              정합성 자동 복구를 실행하시겠습니까?
            </p>
            <p style={{ fontSize: 12, color: '#fbbf24', marginBottom: 16 }}>
              💾 백업을 먼저 생성하는 것을 권장합니다. 복구 작업은 inventory.status를 tonbag 다수결로 동기화합니다.
            </p>
            <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
              <button onClick={() => setShowConfirm(false)}
                style={{ padding: '7px 18px', background: '#334155', color: '#94a3b8', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 13 }}>
                취소
              </button>
              <button onClick={runRepair}
                style={{ padding: '7px 18px', background: '#dc2626', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 13, fontWeight: 700 }}>
                복구 실행
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 복구 결과 */}
      {repairResult && (
        <div style={{
          padding: '12px 16px', borderRadius: 8, marginBottom: 16,
          background: repairResult.success ? '#f0fdf4' : '#fef2f2',
          border: `1px solid ${repairResult.success ? '#bbf7d0' : '#fecaca'}`,
        }}>
          <div style={{ fontWeight: 700, fontSize: 13, color: repairResult.success ? '#166534' : '#991b1b', marginBottom: 6 }}>
            {repairResult.success ? `✅ 복구 완료 — ${repairResult.repaired_count}건 수정` : '❌ 복구 실패'}
          </div>
          {repairResult.details?.length > 0 && (
            <table style={{ width: '100%', fontSize: 11, borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: '#f1f5f9' }}>
                  <th style={{ padding: '3px 8px', textAlign: 'left' }}>LOT NO</th>
                  <th style={{ padding: '3px 8px' }}>이전 상태</th>
                  <th style={{ padding: '3px 8px' }}>복구 상태</th>
                </tr>
              </thead>
              <tbody>
                {repairResult.details.slice(0, 10).map((d, i) => (
                  <tr key={i}>
                    <td style={{ padding: '3px 8px', color: '#1e40af' }}>{d.lot_no}</td>
                    <td style={{ padding: '3px 8px', textAlign: 'center', color: '#dc2626' }}>{d.old}</td>
                    <td style={{ padding: '3px 8px', textAlign: 'center', color: '#16a34a' }}>{d.new}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}

      {/* 검사 결과 */}
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
                      <span style={{ fontSize: 10, fontWeight: 700, padding: '2px 6px', borderRadius: 4, background: c.fg, color: '#fff' }}>
                        {issue.severity}
                      </span>
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
