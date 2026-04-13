/**
 * PickedPage v2 — 출고 확정 버튼 추가
 * 배치: web/src/pages/PickedPage.jsx (기존 덮어쓰기)
 * 변경:
 *   1. 상단에 "📤 선택 출고 확정" 버튼
 *   2. 각 행에 체크박스 → 선택 후 일괄 확정
 *   3. LOT 단위 확정 버튼 (행 우클릭)
 *   4. 확정 완료 후 자동 새로고침 + 결과 토스트
 */
import { useEffect, useState, useCallback } from 'react';
import { getPickedList } from '../api/tabsApi';
import { api } from '../api/client';

// ── 토스트 알림 ──────────────────────────────────────────────
function Toast({ msg, ok, onClose }) {
  useEffect(() => { const t = setTimeout(onClose, 3500); return () => clearTimeout(t); }, [onClose]);
  return (
    <div style={{
      position: 'fixed', bottom: 24, left: '50%', transform: 'translateX(-50%)',
      background: ok ? '#16a34a' : '#dc2626', color: '#fff',
      padding: '12px 24px', borderRadius: 10, fontWeight: 700, fontSize: 14,
      zIndex: 9999, boxShadow: '0 4px 16px rgba(0,0,0,0.4)',
      display: 'flex', alignItems: 'center', gap: 8,
    }}>
      {ok ? '✅' : '❌'} {msg}
    </div>
  );
}

// ── 확인 다이얼로그 ──────────────────────────────────────────
function ConfirmDialog({ count, lotNos, onConfirm, onCancel }) {
  return (
    <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 9000 }}>
      <div style={{ background: '#1e293b', borderRadius: 14, padding: 28,
        width: 380, boxShadow: '0 8px 32px rgba(0,0,0,0.5)' }}>
        <div style={{ fontSize: 18, fontWeight: 700, color: '#f1f5f9', marginBottom: 12 }}>
          📤 출고 확정
        </div>
        <div style={{ color: '#94a3b8', fontSize: 14, marginBottom: 8 }}>
          아래 <b style={{ color: '#f59e0b' }}>{count}건</b>을 출고 확정(OUTBOUND)하시겠습니까?
        </div>
        <div style={{ background: '#0f172a', borderRadius: 8, padding: '8px 12px',
          fontSize: 12, color: '#64748b', marginBottom: 20, maxHeight: 120, overflowY: 'auto' }}>
          {lotNos.slice(0, 10).map((l, i) => <div key={i}>• {l}</div>)}
          {lotNos.length > 10 && <div>...외 {lotNos.length - 10}건</div>}
        </div>
        <div style={{ color: '#ef4444', fontSize: 12, marginBottom: 20 }}>
          ⚠️ 이 작업은 되돌리기 어렵습니다.
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <button onClick={onCancel} style={{ flex: 1, padding: '10px', borderRadius: 8,
            border: 'none', background: '#334155', color: '#94a3b8',
            fontSize: 14, cursor: 'pointer' }}>취소</button>
          <button onClick={onConfirm} style={{ flex: 1, padding: '10px', borderRadius: 8,
            border: 'none', background: '#8b5cf6', color: '#fff',
            fontSize: 14, fontWeight: 700, cursor: 'pointer' }}>확정</button>
        </div>
      </div>
    </div>
  );
}

const thStyle = {
  padding: '8px 6px', background: '#f8fafc', borderBottom: '2px solid #e2e8f0',
  fontSize: 11, fontWeight: 700, position: 'sticky', top: 0,
  whiteSpace: 'nowrap', textAlign: 'center',
};
const tdBase = { padding: '6px 6px', borderBottom: '1px dashed rgba(51,65,85,0.3)', fontSize: 12, whiteSpace: 'nowrap' };

export default function PickedPage() {
  const [rows,       setRows]       = useState([]);
  const [loading,    setLoading]    = useState(true);
  const [error,      setError]      = useState(null);
  const [selected,   setSelected]   = useState(new Set());  // lot_no 집합
  const [confirm,    setConfirm]    = useState(false);
  const [processing, setProcessing] = useState(false);
  const [toast,      setToast]      = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [keyword,    setKeyword]    = useState('');

  // 데이터 로드
  const load = useCallback(async () => {
    setLoading(true); setError(null);
    try {
      const res = await getPickedList({ keyword });
      setRows(res?.rows || res?.items || []);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [keyword, refreshKey]);

  useEffect(() => { load(); }, [load]);

  // 체크박스 선택
  const toggleSelect = (lotNo) => {
    setSelected(prev => {
      const next = new Set(prev);
      next.has(lotNo) ? next.delete(lotNo) : next.add(lotNo);
      return next;
    });
  };

  const toggleAll = () => {
    if (selected.size === rows.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(rows.map(r => r.lot_no)));
    }
  };

  // ★ 출고 확정 실행
  const handleConfirm = async () => {
    setConfirm(false);
    setProcessing(true);
    // ★ Q1 개선: Promise.allSettled — 하나 실패해도 나머지 모두 처리 보장
    // Promise.all과 달리 중간 실패 시에도 전체 결과 수집
    const lotNos = [...new Set([...selected])];

    const settled = await Promise.allSettled(
      lotNos.map(lotNo =>
        api.post('/outbound/confirm', { lot_no: lotNo, force_all: false })
          .then(res => ({ lotNo, ok: res?.success, confirmed: res?.data?.confirmed || 1, msg: res?.message }))
          .catch(e  => ({ lotNo, ok: false, confirmed: 0, msg: e.message }))
      )
    );

    // allSettled → fulfilled/rejected 모두 수집
    const results      = settled.map(s => s.status === 'fulfilled' ? s.value : { ok: false, confirmed: 0 });
    const successCount = results.filter(r => r.ok).reduce((s, r) => s + r.confirmed, 0);
    const failCount    = results.filter(r => !r.ok).length;
    const failLots     = settled
      .filter(s => s.status === 'fulfilled' && !s.value.ok)
      .map(s => s.value.lotNo)
      .slice(0, 3);

    setProcessing(false);
    setSelected(new Set());
    setRefreshKey(k => k + 1);

    if (failCount === 0) {
      setToast({ msg: `출고 확정 완료: ${successCount}톤백 (${lotNos.length}LOT)`, ok: true });
    } else {
      setToast({ msg: `완료 ${successCount}건 / 실패 ${failCount}건${failLots.length ? ' (' + failLots.join(', ') + ')' : ''}`, ok: false });
    }
  };

  const selectedLotNos = [...selected];
  const filteredRows   = keyword
    ? rows.filter(r => r.lot_no?.includes(keyword) || r.customer?.includes(keyword) || r.tonbag_uid?.includes(keyword))
    : rows;

  return (
    <div style={{ padding: 16, background: '#0f172a', minHeight: '100vh', color: '#f1f5f9' }}>

      {/* ── 헤더 ── */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <h2 style={{ fontSize: 16, fontWeight: 700, color: '#f1f5f9', margin: 0 }}>
          📦 Picked (피킹 완료)
          {rows.length > 0 && (
            <span style={{ fontSize: 12, color: '#64748b', marginLeft: 8, fontWeight: 400 }}>
              총 {rows.length}건
            </span>
          )}
        </h2>

        {/* ★ 출고 확정 버튼 */}
        <button
          onClick={() => selected.size > 0 && setConfirm(true)}
          disabled={selected.size === 0 || processing}
          style={{
            padding: '8px 18px',
            background: selected.size > 0 ? '#8b5cf6' : '#334155',
            color: selected.size > 0 ? '#fff' : '#64748b',
            border: 'none', borderRadius: 8, fontSize: 13, fontWeight: 700,
            cursor: selected.size > 0 ? 'pointer' : 'not-allowed',
            transition: 'all 0.15s',
          }}
        >
          {processing ? '⏳ 처리 중...' : `📤 출고 확정 (${selected.size}건 선택)`}
        </button>
      </div>

      {/* ── 검색 ── */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
        <input
          value={keyword}
          onChange={e => setKeyword(e.target.value)}
          placeholder="LOT / Customer / Tonbag UID 검색..."
          style={{ padding: '6px 10px', fontSize: 12, borderRadius: 6,
            border: '1px solid #334155', background: '#1e293b', color: '#f1f5f9', width: 280 }}
        />
        {keyword && (
          <button onClick={() => setKeyword('')} style={{ padding: '6px 12px', fontSize: 12,
            borderRadius: 6, border: 'none', background: '#334155', color: '#94a3b8', cursor: 'pointer' }}>
            Clear
          </button>
        )}
      </div>

      {error   && <div style={{ color: '#ef4444', marginBottom: 8, fontSize: 12 }}>❌ {error}</div>}
      {loading && <div style={{ color: '#64748b', padding: 16 }}>Loading...</div>}

      {!loading && (
        <div style={{ overflow: 'auto', maxHeight: '75vh', border: '1px solid #334155', borderRadius: 8 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                {/* ★ 전체 선택 체크박스 */}
                <th style={{ ...thStyle, width: 36 }}>
                  <input type="checkbox"
                    checked={selected.size === rows.length && rows.length > 0}
                    onChange={toggleAll}
                    style={{ cursor: 'pointer' }}
                  />
                </th>
                {[
                  'No.', 'LOT NO', 'PRODUCT', 'TONBAG UID', 'CUSTOMER',
                  'QTY(Kg)', 'QTY(MT)', 'STATUS', 'PICKING DATE', 'SUB LT',
                ].map(h => <th key={h} style={thStyle}>{h}</th>)}
                <th style={thStyle}>ACTION</th>
              </tr>
            </thead>
            <tbody>
              {filteredRows.length === 0
                ? <tr><td colSpan={12} style={{ ...tdBase, textAlign: 'center', padding: 32, color: '#94a3b8' }}>
                    피킹 완료 항목 없음
                  </td></tr>
                : filteredRows.map((row, idx) => {
                  const isSelected = selected.has(row.lot_no);
                  return (
                    <tr key={row.lot_no + idx}
                      style={{ background: isSelected ? '#1e3a5f' : '' }}
                      onMouseEnter={e => { if (!isSelected) e.currentTarget.style.background = '#1e293b'; }}
                      onMouseLeave={e => { if (!isSelected) e.currentTarget.style.background = ''; }}
                    >
                      <td style={{ ...tdBase, textAlign: 'center' }}>
                        <input type="checkbox" checked={isSelected}
                          onChange={() => toggleSelect(row.lot_no)}
                          style={{ cursor: 'pointer' }}
                        />
                      </td>
                      <td style={{ ...tdBase, textAlign: 'center', color: '#94a3b8' }}>{idx + 1}</td>
                      <td style={{ ...tdBase, fontWeight: 600, color: '#3b82f6' }}>{row.lot_no}</td>
                      <td style={{ ...tdBase }}>{row.product || row.product_name || '-'}</td>
                      <td style={{ ...tdBase, fontSize: 11, color: '#64748b' }}>{row.tonbag_uid || '-'}</td>
                      <td style={{ ...tdBase }}>{row.customer || '-'}</td>
                      <td style={{ ...tdBase, textAlign: 'right' }}>{Number(row.qty_kg || 0).toLocaleString()}</td>
                      <td style={{ ...tdBase, textAlign: 'right' }}>{Number(row.qty_mt || (row.qty_kg / 1000) || 0).toFixed(3)}</td>
                      <td style={{ ...tdBase, textAlign: 'center' }}>
                        <span style={{ background: '#3b82f622', color: '#3b82f6',
                          border: '1px solid #3b82f644', borderRadius: 4,
                          padding: '2px 8px', fontSize: 10, fontWeight: 700 }}>
                          {row.status || 'PICKED'}
                        </span>
                      </td>
                      <td style={{ ...tdBase, textAlign: 'center', fontSize: 11 }}>{row.creation_date || row.picked_date || '-'}</td>
                      <td style={{ ...tdBase, textAlign: 'center' }}>{row.sub_lt ?? '-'}</td>
                      {/* ★ 행별 빠른 확정 버튼 */}
                      <td style={{ ...tdBase, textAlign: 'center' }}>
                        <button
                          onClick={() => { setSelected(new Set([row.lot_no])); setConfirm(true); }}
                          style={{ padding: '4px 10px', fontSize: 11, fontWeight: 700,
                            background: '#8b5cf6', color: '#fff', border: 'none',
                            borderRadius: 6, cursor: 'pointer' }}
                        >
                          확정
                        </button>
                      </td>
                    </tr>
                  );
                })
              }
            </tbody>
          </table>
        </div>
      )}

      {/* ── 확인 다이얼로그 ── */}
      {confirm && (
        <ConfirmDialog
          count={selectedLotNos.length}
          lotNos={selectedLotNos}
          onConfirm={handleConfirm}
          onCancel={() => setConfirm(false)}
        />
      )}

      {/* ── 토스트 ── */}
      {toast && <Toast msg={toast.msg} ok={toast.ok} onClose={() => setToast(null)} />}
    </div>
  );
}
