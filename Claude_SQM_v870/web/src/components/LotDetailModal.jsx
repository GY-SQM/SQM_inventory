import { useState, useEffect } from 'react';
import Modal from './Modal';
import { getLotDetail } from '../api/inventoryApi';

const badge = (status) => {
  const colors = {
    AVAILABLE: '#22c55e', RESERVED: '#eab308',
    PICKED: '#f97316', OUTBOUND: '#ef4444', SOLD: '#ef4444',
  };
  return {
    display: 'inline-block', padding: '2px 8px', borderRadius: 4,
    fontSize: 11, fontWeight: 600, color: '#fff',
    background: colors[status] || '#94a3b8',
  };
};

const table = { width: '100%', borderCollapse: 'collapse', fontSize: 12 };
const th = { textAlign: 'left', padding: '6px 8px', background: '#f1f5f9', borderBottom: '1px solid #e2e8f0', fontWeight: 600 };
const td = { padding: '6px 8px', borderBottom: '1px solid #f1f5f9' };

function fmt(v) {
  const n = Number(v || 0);
  return n ? n.toLocaleString(undefined, { maximumFractionDigits: 1 }) : '0';
}

export default function LotDetailModal({ open, onClose, lotNo }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!open || !lotNo) return;
    setLoading(true);
    setError(null);
    getLotDetail(lotNo)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [open, lotNo]);

  return (
    <Modal open={open} onClose={onClose} title={`LOT 상세: ${lotNo || ''}`} width={800}>
      {loading && <p>로딩 중...</p>}
      {error && <p style={{ color: 'red' }}>{error}</p>}
      {data && (
        <>
          {/* 기본 정보 */}
          <h4 style={{ margin: '0 0 8px', fontSize: 13 }}>기본 정보</h4>
          <table style={table}>
            <tbody>
              <tr><td style={th}>LOT NO</td><td style={td}>{data.lot_no}</td><td style={th}>제품</td><td style={td}>{data.product_name}</td></tr>
              <tr><td style={th}>SAP NO</td><td style={td}>{data.sap_no}</td><td style={th}>BL NO</td><td style={td}>{data.bl_no}</td></tr>
              <tr><td style={th}>상태</td><td style={td}><span style={badge(data.inventory_status)}>{data.inventory_status}</span></td><td style={th}>톤백 수</td><td style={td}>{data.tonbag_count}</td></tr>
              <tr><td style={th}>CONTAINER</td><td style={td}>{data.container_no || '-'}</td><td style={th}>WAREHOUSE</td><td style={td}>{data.warehouse || '-'}</td></tr>
            </tbody>
          </table>

          {/* 중량 + 물류 정보 */}
          <h4 style={{ margin: '16px 0 8px', fontSize: 13 }}>중량 / 물류 정보</h4>
          <table style={table}>
            <tbody>
              <tr>
                <td style={th}>NET Weight</td><td style={td}>{fmt(data.net_weight)} kg</td>
                <td style={th}>Current Weight</td><td style={td}>{fmt(data.current_weight)} kg</td>
              </tr>
              <tr>
                <td style={th}>Initial Weight</td><td style={td}>{fmt(data.initial_weight)} kg</td>
                <td style={th}>FREE TIME</td><td style={td}>{data.free_time || '-'}</td>
              </tr>
              <tr>
                <td style={th}>SHIP DATE</td><td style={td}>{data.ship_date || '-'}</td>
                <td style={th}>ARRIVAL</td><td style={td}>{data.arrival_date || '-'}</td>
              </tr>
              <tr>
                <td style={th}>CON RETURN</td><td style={td}>{data.con_return || '-'}</td>
                <td style={th}></td><td style={td}></td>
              </tr>
            </tbody>
          </table>

          {/* 상태 요약 */}
          {data.status_summary && data.status_summary.length > 0 && (
            <>
              <h4 style={{ margin: '16px 0 8px', fontSize: 13 }}>배정 상태</h4>
              <table style={table}>
                <thead>
                  <tr><th style={th}>상태</th><th style={th}>수량</th><th style={th}>중량(kg)</th><th style={th}>중량(MT)</th></tr>
                </thead>
                <tbody>
                  {data.status_summary.map((s, i) => (
                    <tr key={i}>
                      <td style={td}><span style={badge(s.status)}>{s.status}</span></td>
                      <td style={td}>{s.bag_count}</td>
                      <td style={td}>{(s.weight_kg || 0).toLocaleString()}</td>
                      <td style={td}>{(s.weight_mt || 0).toFixed(3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}

          {/* 톤백 목록 */}
          {data.tonbags && data.tonbags.length > 0 && (
            <>
              <h4 style={{ margin: '16px 0 8px', fontSize: 13 }}>톤백 목록</h4>
              <div style={{ maxHeight: 300, overflow: 'auto' }}>
                <table style={table}>
                  <thead>
                    <tr>
                      <th style={th}>UID</th><th style={th}>No</th><th style={th}>Sub</th>
                      <th style={th}>상태</th><th style={th}>위치</th><th style={th}>중량(kg)</th>
                      <th style={th}>샘플</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.tonbags.map((t, i) => (
                      <tr key={i}>
                        <td style={td}>{t.tonbag_uid}</td>
                        <td style={td}>{t.tonbag_no}</td>
                        <td style={td}>{t.sub_lt}</td>
                        <td style={td}><span style={badge(t.status)}>{t.status}</span></td>
                        <td style={td}>{t.location}</td>
                        <td style={td}>{(t.weight_kg || 0).toLocaleString()}</td>
                        <td style={td}>{t.is_sample ? 'Y' : ''}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </>
      )}
    </Modal>
  );
}
