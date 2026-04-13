import { useState, useEffect } from 'react';
import { useLocation } from 'react-router-dom';
import { addRecentFile } from '../utils/recentFiles';
import {
  getReturnList, getReturnStatistics,
  postReturnSingle, postReturnBulkExcel, postReturnBulkConfirm,
} from '../api/returnApi';

const TABS = [
  { key: 'history', label: '반품 이력' },
  { key: 'single', label: '소량반품' },
  { key: 'excel', label: 'Excel 다량반품' },
];

const REASONS = ['품질불량', '수량오류', '고객요청', '파손', '기타'];

const thStyle = {
  padding: '6px 8px', textAlign: 'center', background: 'var(--card-bg, #1e293b)',
  borderBottom: '2px solid var(--border-color, #334155)', fontSize: 11, fontWeight: 700, whiteSpace: 'nowrap',
  color: 'var(--text-secondary, #94a3b8)',
};
const tdStyle = { padding: '5px 8px', borderBottom: '1px dashed rgba(51,65,85,0.3)', fontSize: 12, whiteSpace: 'nowrap', color: 'var(--text-primary, #e2e8f0)' };
const tdR = { ...tdStyle, textAlign: 'right' };
const tdC = { ...tdStyle, textAlign: 'center' };

const cardStyle = {
  padding: '12px 16px', background: 'var(--card-bg, #1e293b)', borderRadius: 8,
  border: '1px solid var(--border-color, #334155)', minWidth: 120, textAlign: 'center',
};

function fmt(v) {
  const n = Number(v || 0);
  return n ? n.toLocaleString(undefined, { maximumFractionDigits: 1 }) : '0';
}

export default function ReturnPage() {
  const location = useLocation();
  // navigate('/return', { state: { tab: 'single' } }) 로 직접 탭 진입 지원
  const initTab = location.state?.tab || 'history';
  const [tab, setTab] = useState(initTab);
  const [stats, setStats] = useState(null);

  useEffect(() => {
    getReturnStatistics().then(setStats).catch(err => console.error('API error:', err));
  }, []);

  // navigate로 다시 들어올 때 tab 갱신
  useEffect(() => {
    if (location.state?.tab) setTab(location.state.tab);
  }, [location.state]);

  return (
    <div style={{ padding: 24 }}>
      <h2 style={{ marginBottom: 12 }}>Return (반품)</h2>

      {/* 요약 카드 */}
      {stats && (
        <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
          <div style={cardStyle}>
            <div style={{ fontSize: 11, color: '#64748b' }}>총 반품</div>
            <div style={{ fontSize: 20, fontWeight: 700 }}>{stats.total_count}</div>
          </div>
          <div style={cardStyle}>
            <div style={{ fontSize: 11, color: '#64748b' }}>총 중량(Kg)</div>
            <div style={{ fontSize: 20, fontWeight: 700 }}>{fmt(stats.total_weight_kg)}</div>
          </div>
          {stats.by_reason?.slice(0, 3).map((r, i) => (
            <div key={i} style={cardStyle}>
              <div style={{ fontSize: 11, color: '#64748b' }}>{r.reason}</div>
              <div style={{ fontSize: 20, fontWeight: 700 }}>{r.count}건</div>
            </div>
          ))}
        </div>
      )}

      {/* 탭 버튼 */}
      <div style={{ display: 'flex', gap: 0, marginBottom: 16, borderBottom: '2px solid var(--border-color, #334155)' }}>
        {TABS.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)} style={{
            padding: '8px 20px', fontSize: 13, fontWeight: tab === t.key ? 700 : 400,
            color: tab === t.key ? '#2563eb' : '#64748b',
            borderBottom: tab === t.key ? '2px solid #2563eb' : '2px solid transparent',
            background: 'none', border: 'none', cursor: 'pointer', marginBottom: -2,
          }}>{t.label}</button>
        ))}
      </div>

      {tab === 'history' && <HistoryTab />}
      {tab === 'single' && <SingleTab onDone={() => { setTab('history'); getReturnStatistics().then(setStats).catch(err => console.error('API error:', err)); }} />}
      {tab === 'excel' && <ExcelTab onDone={() => { setTab('history'); getReturnStatistics().then(setStats).catch(err => console.error('API error:', err)); }} />}
    </div>
  );
}


function HistoryTab() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState({ lot_no: '', page: 1 });

  useEffect(() => {
    setLoading(true);
    getReturnList(filter)
      .then(setData)
      .catch(err => console.error('API error:', err))
      .finally(() => setLoading(false));
  }, [filter]);

  const totalPages = data ? Math.max(1, Math.ceil(data.total / 50)) : 1;

  return (
    <>
      <div style={{ display: 'flex', gap: 6, marginBottom: 10, alignItems: 'center' }}>
        <input placeholder="LOT No" value={filter.lot_no}
          onChange={e => setFilter(f => ({ ...f, lot_no: e.target.value, page: 1 }))}
          style={{ padding: 5, width: 150, fontSize: 12 }} />
        <button onClick={() => setFilter(f => ({ ...f, page: 1 }))} style={{ padding: '5px 12px', fontSize: 12 }}>Search</button>
      </div>

      {loading && <div style={{ padding: 12, color: '#475569' }}>Loading...</div>}
      {data && !loading && (
        <>
          <div style={{ fontSize: 12, color: '#475569', marginBottom: 6 }}>Total: <b>{data.total}</b></div>
          <div style={{ overflow: 'auto', maxHeight: '60vh', border: '1px solid #e2e8f0', borderRadius: 6 }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 900 }}>
              <thead>
                <tr>
                  <th style={thStyle}>No.</th>
                  <th style={thStyle}>LOT NO</th>
                  <th style={thStyle}>Sub</th>
                  <th style={thStyle}>제품</th>
                  <th style={thStyle}>고객</th>
                  <th style={thStyle}>Sale Ref</th>
                  <th style={thStyle}>사유</th>
                  <th style={thStyle}>비고</th>
                  <th style={thStyle}>중량(Kg)</th>
                  <th style={thStyle}>반품일</th>
                </tr>
              </thead>
              <tbody>
                {data.rows.length === 0 ? (
                  <tr><td colSpan={10} style={{ ...tdC, padding: 24, color: '#94a3b8' }}>No results</td></tr>
                ) : data.rows.map((r, i) => (
                  <tr key={r.id}>
                    <td style={tdC}>{(data.page - 1) * 50 + i + 1}</td>
                    <td style={tdStyle}>{r.lot_no}</td>
                    <td style={tdC}>{r.sub_lt}</td>
                    <td style={tdStyle}>{r.product || '-'}</td>
                    <td style={tdStyle}>{r.original_customer || '-'}</td>
                    <td style={tdStyle}>{r.original_sale_ref || '-'}</td>
                    <td style={tdC}>{r.reason || '-'}</td>
                    <td style={tdStyle}>{r.remark || '-'}</td>
                    <td style={tdR}>{fmt(r.weight_kg)}</td>
                    <td style={tdC}>{r.return_date || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginTop: 6, fontSize: 12 }}>
            <button disabled={data.page <= 1} onClick={() => setFilter(f => ({ ...f, page: f.page - 1 }))}>Prev</button>
            <span>{data.page} / {totalPages}</span>
            <button disabled={data.page >= totalPages} onClick={() => setFilter(f => ({ ...f, page: f.page + 1 }))}>Next</button>
          </div>
        </>
      )}
    </>
  );
}


function SingleTab({ onDone }) {
  const [lotNo, setLotNo] = useState('');
  const [subLt, setSubLt] = useState('');
  const [reason, setReason] = useState('품질불량');
  const [note, setNote] = useState('');
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!lotNo || subLt === '') return;
    setLoading(true);
    setResult(null);
    try {
      const res = await postReturnSingle({
        lot_no: lotNo,
        sub_lt: parseInt(subLt, 10),
        reason_code: reason,
        note,
      });
      setResult(res);
      if (res.success) {
        addRecentFile({
          filename: `소량 반품 ${lotNo}`,
          type: '반품',
          path: '/return',
        });
        setTimeout(() => onDone?.(), 1500);
      }
    } catch (err) {
      setResult({ success: false, message: err.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} style={{ maxWidth: 500 }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <label style={{ fontSize: 12 }}>
          LOT NO
          <input value={lotNo} onChange={e => setLotNo(e.target.value)} required
            style={{ display: 'block', width: '100%', padding: 6, fontSize: 13, marginTop: 2 }} />
        </label>
        <label style={{ fontSize: 12 }}>
          Sub LT
          <input type="number" value={subLt} onChange={e => setSubLt(e.target.value)} required min={0}
            style={{ display: 'block', width: '100%', padding: 6, fontSize: 13, marginTop: 2 }} />
        </label>
        <label style={{ fontSize: 12 }}>
          사유코드
          <select value={reason} onChange={e => setReason(e.target.value)}
            style={{ display: 'block', width: '100%', padding: 6, fontSize: 13, marginTop: 2 }}>
            {REASONS.map(r => <option key={r} value={r}>{r}</option>)}
          </select>
        </label>
        <label style={{ fontSize: 12 }}>
          비고
          <input value={note} onChange={e => setNote(e.target.value)}
            style={{ display: 'block', width: '100%', padding: 6, fontSize: 13, marginTop: 2 }} />
        </label>
        <button type="submit" disabled={loading}
          style={{ padding: '8px 20px', fontWeight: 700, fontSize: 13, background: '#2563eb', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer' }}>
          {loading ? '처리 중...' : '반품 실행'}
        </button>
      </div>
      {result && (
        <div style={{
          marginTop: 12, padding: 10, borderRadius: 6, fontSize: 12,
          background: result.success ? '#f0fdf4' : '#fef2f2',
          color: result.success ? '#166534' : '#991b1b',
          border: `1px solid ${result.success ? '#bbf7d0' : '#fecaca'}`,
        }}>
          {result.message}
        </div>
      )}
    </form>
  );
}


function ExcelTab({ onDone }) {
  const [preview, setPreview] = useState(null);
  const [confirmResult, setConfirmResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [excelFileName, setExcelFileName] = useState('');

  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setExcelFileName(file.name);
    setLoading(true);
    setPreview(null);
    setConfirmResult(null);
    try {
      const fd = new FormData();
      fd.append('file', file);
      const res = await postReturnBulkExcel(fd);
      setPreview(res);
    } catch (err) {
      setPreview({ parse_ok: false, errors: [err.message], rows: [] });
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = async () => {
    if (!preview?.rows?.length) return;
    setLoading(true);
    try {
      const res = await postReturnBulkConfirm(preview.rows);
      setConfirmResult(res);
      if (res.success) {
        addRecentFile({
          filename: excelFileName || `다량 반품 ${preview.rows.length}건`,
          type: '반품',
          path: '/return',
        });
        setTimeout(() => onDone?.(), 1500);
      }
    } catch (err) {
      setConfirmResult({ success: false, message: err.message });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <div style={{ marginBottom: 12 }}>
        <input type="file" accept=".xlsx,.xls" onChange={handleUpload} style={{ fontSize: 13 }} />
      </div>

      {loading && <div style={{ padding: 12, color: '#475569' }}>처리 중...</div>}

      {preview && !loading && (
        <>
          {preview.errors?.length > 0 && (
            <div style={{ padding: 10, background: '#fef2f2', border: '1px solid #fecaca', borderRadius: 6, marginBottom: 10, fontSize: 12 }}>
              {preview.errors.map((e, i) => <div key={i} style={{ color: '#991b1b' }}>{e}</div>)}
            </div>
          )}
          {preview.warnings?.length > 0 && (
            <div style={{ padding: 10, background: '#fffbeb', border: '1px solid #fde68a', borderRadius: 6, marginBottom: 10, fontSize: 12 }}>
              {preview.warnings.map((w, i) => <div key={i} style={{ color: '#92400e' }}>{w}</div>)}
            </div>
          )}

          {preview.rows?.length > 0 && (
            <>
              <div style={{ fontSize: 12, color: '#475569', marginBottom: 6 }}>Preview: {preview.total}건</div>
              <div style={{ overflow: 'auto', maxHeight: '40vh', border: '1px solid #e2e8f0', borderRadius: 6, marginBottom: 10 }}>
                <table style={{ width: '100%', borderCollapse: 'collapse', minWidth: 600 }}>
                  <thead>
                    <tr>
                      <th style={thStyle}>LOT NO</th>
                      <th style={thStyle}>PICKING NO</th>
                      <th style={thStyle}>사유</th>
                      <th style={thStyle}>비고</th>
                      <th style={thStyle}>중량(MT)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {preview.rows.map((r, i) => (
                      <tr key={i}>
                        <td style={tdStyle}>{r.lot_no}</td>
                        <td style={tdStyle}>{r.picking_no || '-'}</td>
                        <td style={tdC}>{r.reason || '-'}</td>
                        <td style={tdStyle}>{r.remark || '-'}</td>
                        <td style={tdR}>{r.weight_mt || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {!confirmResult && (
                <button onClick={handleConfirm} disabled={loading}
                  style={{ padding: '8px 20px', fontWeight: 700, fontSize: 13, background: '#dc2626', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer' }}>
                  반품 확인 실행
                </button>
              )}
            </>
          )}
        </>
      )}

      {confirmResult && (
        <div style={{
          marginTop: 12, padding: 10, borderRadius: 6, fontSize: 12,
          background: confirmResult.success ? '#f0fdf4' : '#fef2f2',
          color: confirmResult.success ? '#166534' : '#991b1b',
          border: `1px solid ${confirmResult.success ? '#bbf7d0' : '#fecaca'}`,
        }}>
          {confirmResult.message}
        </div>
      )}
    </div>
  );
}
