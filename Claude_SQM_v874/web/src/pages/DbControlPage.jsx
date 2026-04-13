/**
 * DbControlPage — DB 컨트롤 센터 (5 tabs)
 * P3-7~8 구현: 편집기 / 수정이력 / 백업 / 탐색기 / 정합성
 */
import { useState, useEffect, useCallback, useRef } from 'react';
import { api, downloadFile } from '../api/client';

/* ── palette / shared styles ───────────────────────── */
const BG      = '#0f172a';
const CARD    = '#1e293b';
const BORDER  = '#334155';
const MUTED   = '#64748b';
const TEXT    = '#f1f5f9';
const ACCENT  = '#3b82f6';
const GREEN   = '#16a34a';
const RED     = '#ef4444';
const YELLOW  = '#fbbf24';

const thS = {
  padding: '7px 10px', background: BG, borderBottom: `1px solid ${BORDER}`,
  fontSize: 11, fontWeight: 700, color: MUTED, textAlign: 'left',
  position: 'sticky', top: 0, whiteSpace: 'nowrap',
};
const tdS = {
  padding: '5px 10px', borderBottom: `1px solid #1e293b`,
  fontSize: 12, color: TEXT, whiteSpace: 'nowrap',
};
const inputS = {
  padding: '6px 10px', fontSize: 12, background: BG,
  border: `1px solid ${BORDER}`, borderRadius: 6, color: TEXT,
  boxSizing: 'border-box',
};
const btnS = (bg, disabled) => ({
  padding: '6px 14px', border: 'none', borderRadius: 6,
  background: disabled ? '#334155' : bg, color: disabled ? MUTED : '#fff',
  fontSize: 12, fontWeight: 600, cursor: disabled ? 'not-allowed' : 'pointer',
  whiteSpace: 'nowrap',
});
const cardS = {
  background: CARD, border: `1px solid ${BORDER}`,
  borderRadius: 10, padding: 20, marginBottom: 14,
};

const TABS = [
  { key: 'editor',    label: '\ud83d\udcdd \ud3b8\uc9d1\uae30' },
  { key: 'audit',     label: '\ud83d\udcdc \uc218\uc815\uc774\ub825' },
  { key: 'backup',    label: '\ud83d\udcbe \ubc31\uc5c5' },
  { key: 'explorer',  label: '\ud83d\udcca \ud0d0\uc0c9\uae30' },
  { key: 'integrity', label: '\u2696\ufe0f \uc815\ud569\uc131' },
];

const EDITABLE_FIELDS = [
  'sap_no','bl_no','container_no','ship_date','arrival_date',
  'con_return','free_time','vessel','warehouse','remarks',
];

const BLOCKED_FIELDS = [
  'id','lot_no','status','product_name','net_weight','current_weight',
  'gross_weight','tare_weight','bags','location','zone','created_at','updated_at',
];

/* ── Toast ─────────────────────────────────────────── */
function Toast({ msg, ok }) {
  if (!msg) return null;
  return (
    <div style={{
      position: 'fixed', bottom: 28, left: '50%', transform: 'translateX(-50%)',
      padding: '10px 24px', borderRadius: 8, fontSize: 13, fontWeight: 600, zIndex: 9999,
      background: ok ? '#064e3b' : '#450a0a', color: ok ? '#34d399' : '#f87171',
    }}>{msg}</div>
  );
}

function useToast() {
  const [toast, setToast] = useState(null);
  const tid = useRef(null);
  const show = useCallback((msg, ok = true) => {
    clearTimeout(tid.current);
    setToast({ msg, ok });
    tid.current = setTimeout(() => setToast(null), 3000);
  }, []);
  return [toast, show];
}

/* ── Confirm dialog ────────────────────────────────── */
function ConfirmDialog({ title, msg, onOk, onCancel }) {
  return (
    <div style={{
      position: 'fixed', inset: 0, background: 'rgba(0,0,0,.55)', zIndex: 9000,
      display: 'flex', alignItems: 'center', justifyContent: 'center',
    }} onClick={onCancel}>
      <div style={{
        background: CARD, border: `1px solid ${BORDER}`, borderRadius: 12,
        padding: 24, minWidth: 340, maxWidth: 420,
      }} onClick={e => e.stopPropagation()}>
        <div style={{ fontSize: 15, fontWeight: 700, color: TEXT, marginBottom: 10 }}>{title}</div>
        <div style={{ fontSize: 13, color: MUTED, marginBottom: 18, lineHeight: 1.6 }}>{msg}</div>
        <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
          <button onClick={onCancel} style={btnS('#334155')}>취소</button>
          <button onClick={onOk} style={btnS(RED)}>확인</button>
        </div>
      </div>
    </div>
  );
}

/* ================================================================
   TAB 1: 편집기
   ================================================================ */
function EditorTab({ showToast }) {
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [lotNo, setLotNo] = useState('');
  const [containerNo, setContainerNo] = useState('');
  const [results, setResults] = useState([]);
  const [expanded, setExpanded] = useState({});
  const [editCell, setEditCell] = useState(null); // { lotIdx, bagIdx, field, value }
  const [loading, setLoading] = useState(false);

  const search = async () => {
    setLoading(true);
    try {
      const qs = new URLSearchParams();
      if (dateFrom) qs.set('date_from', dateFrom);
      if (dateTo) qs.set('date_to', dateTo);
      if (lotNo) qs.set('lot_no', lotNo);
      if (containerNo) qs.set('container_no', containerNo);
      const data = await api.get(`/editor/search?${qs}`);
      setResults(data?.lots || data || []);
      setExpanded({});
      setEditCell(null);
    } catch (e) { showToast(e.message, false); }
    finally { setLoading(false); }
  };

  const toggleExpand = (idx) => {
    setExpanded(prev => ({ ...prev, [idx]: !prev[idx] }));
  };

  const startEdit = (lotIdx, bagIdx, field, currentVal) => {
    if (BLOCKED_FIELDS.includes(field)) return;
    setEditCell({ lotIdx, bagIdx, field, value: currentVal ?? '' });
  };

  const saveCell = async () => {
    if (!editCell) return;
    const { lotIdx, bagIdx, field, value } = editCell;
    const lot = results[lotIdx];
    const row = bagIdx != null ? lot.tonbags[bagIdx] : lot;
    const id = row.id;
    try {
      await api.post('/editor/update-cell', {
        id, field, value, table: bagIdx != null ? 'tonbags' : 'lots',
      });
      // update local state
      const copy = JSON.parse(JSON.stringify(results));
      const target = bagIdx != null ? copy[lotIdx].tonbags[bagIdx] : copy[lotIdx];
      target[field] = value;
      setResults(copy);
      setEditCell(null);
      showToast(`${field} 저장 완료`);
    } catch (e) { showToast(e.message, false); }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') saveCell();
    if (e.key === 'Escape') setEditCell(null);
  };

  const renderCell = (lotIdx, bagIdx, field, val) => {
    const isBlocked = BLOCKED_FIELDS.includes(field);
    const isEditing = editCell
      && editCell.lotIdx === lotIdx
      && editCell.bagIdx === bagIdx
      && editCell.field === field;

    if (isEditing) {
      return (
        <input
          autoFocus
          value={editCell.value}
          onChange={e => setEditCell(prev => ({ ...prev, value: e.target.value }))}
          onKeyDown={handleKeyDown}
          onBlur={saveCell}
          style={{
            ...inputS, width: '100%', background: '#422006',
            border: `1px solid ${YELLOW}`, padding: '3px 6px',
          }}
        />
      );
    }

    return (
      <span
        onClick={() => !isBlocked && startEdit(lotIdx, bagIdx, field, val)}
        style={{
          cursor: isBlocked ? 'default' : 'pointer',
          color: isBlocked ? '#475569' : TEXT,
          background: isBlocked ? '#1a1f2e' : 'transparent',
          padding: '1px 4px', borderRadius: 3, display: 'inline-block',
          minWidth: 20,
        }}
        title={isBlocked ? '수정 불가' : '클릭하여 편집'}
      >
        {val ?? '-'}
      </span>
    );
  };

  const allFields = results.length > 0
    ? Object.keys(results[0]).filter(k => k !== 'tonbags')
    : [];

  return (
    <div>
      {/* Search form */}
      <div style={{ ...cardS, display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'flex-end' }}>
        <div>
          <label style={{ fontSize: 11, color: MUTED, display: 'block', marginBottom: 3 }}>기간(FROM)</label>
          <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} style={{ ...inputS, width: 150 }} />
        </div>
        <div>
          <label style={{ fontSize: 11, color: MUTED, display: 'block', marginBottom: 3 }}>기간(TO)</label>
          <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} style={{ ...inputS, width: 150 }} />
        </div>
        <div>
          <label style={{ fontSize: 11, color: MUTED, display: 'block', marginBottom: 3 }}>LOT번호</label>
          <input value={lotNo} onChange={e => setLotNo(e.target.value)} placeholder="LOT-..." style={{ ...inputS, width: 160 }} />
        </div>
        <div>
          <label style={{ fontSize: 11, color: MUTED, display: 'block', marginBottom: 3 }}>컨테이너번호</label>
          <input value={containerNo} onChange={e => setContainerNo(e.target.value)} placeholder="CONT..." style={{ ...inputS, width: 160 }} />
        </div>
        <button onClick={search} disabled={loading} style={btnS(ACCENT, loading)}>
          {loading ? '검색중...' : '검색'}
        </button>
      </div>

      {/* Results */}
      {results.length === 0 && !loading && (
        <div style={{ textAlign: 'center', color: MUTED, padding: 40, fontSize: 13 }}>
          검색 조건을 입력하고 검색 버튼을 누르세요.
        </div>
      )}

      {results.length > 0 && (
        <div style={{ overflow: 'auto', maxHeight: '65vh', border: `1px solid ${BORDER}`, borderRadius: 8 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                <th style={thS}></th>
                {allFields.map(f => (
                  <th key={f} style={{
                    ...thS,
                    color: BLOCKED_FIELDS.includes(f) ? '#475569' : MUTED,
                  }}>{f}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {results.map((lot, li) => (
                <LotRows
                  key={lot.id || li}
                  lot={lot}
                  lotIdx={li}
                  allFields={allFields}
                  expanded={!!expanded[li]}
                  toggleExpand={() => toggleExpand(li)}
                  renderCell={renderCell}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function LotRows({ lot, lotIdx, allFields, expanded, toggleExpand, renderCell }) {
  const bags = lot.tonbags || [];
  return (
    <>
      <tr style={{ background: expanded ? '#1a2744' : 'transparent' }}>
        <td style={tdS}>
          {bags.length > 0 && (
            <button onClick={toggleExpand} style={{
              background: 'none', border: 'none', color: ACCENT,
              cursor: 'pointer', fontSize: 13, padding: '0 4px',
            }}>
              {expanded ? '\u25BC' : '\u25B6'} {bags.length}
            </button>
          )}
        </td>
        {allFields.map(f => (
          <td key={f} style={tdS}>
            {renderCell(lotIdx, null, f, lot[f])}
          </td>
        ))}
      </tr>
      {expanded && bags.map((bag, bi) => {
        const bagFields = Object.keys(bag);
        return (
          <tr key={bag.id || bi} style={{ background: '#0d1829' }}>
            <td style={{ ...tdS, paddingLeft: 28, color: MUTED, fontSize: 10 }}>
              \u2514 {bi + 1}
            </td>
            {allFields.map(f => (
              <td key={f} style={{ ...tdS, fontSize: 11 }}>
                {bagFields.includes(f) ? renderCell(lotIdx, bi, f, bag[f]) : ''}
              </td>
            ))}
          </tr>
        );
      })}
    </>
  );
}

/* ================================================================
   TAB 2: 수정이력
   ================================================================ */
function AuditTab({ showToast }) {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.get('/editor/audit-log');
      setRows(data?.rows || data?.items || data || []);
    } catch (e) { showToast(e.message, false); }
    finally { setLoading(false); }
  }, [showToast]);

  useEffect(() => { load(); }, [load]);

  const revert = async (audit_id) => {
    try {
      await api.post('/editor/revert', { audit_id });
      showToast('되돌리기 완료');
      load();
    } catch (e) { showToast(e.message, false); }
  };

  const exportCsv = () => {
    downloadFile('/editor/audit-export', 'GET', null, 'audit-log.csv');
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <div style={{ fontSize: 13, color: MUTED }}>
          총 {rows.length}건의 수정 이력
        </div>
        <button onClick={exportCsv} style={btnS(GREEN)}>CSV 내보내기</button>
      </div>

      {loading && <div style={{ color: MUTED, padding: 16 }}>로딩중...</div>}

      {!loading && rows.length === 0 && (
        <div style={{ textAlign: 'center', color: MUTED, padding: 40, fontSize: 13 }}>수정 이력이 없습니다.</div>
      )}

      {!loading && rows.length > 0 && (
        <div style={{ overflow: 'auto', maxHeight: '70vh', border: `1px solid ${BORDER}`, borderRadius: 8 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                {['날짜', 'LOT', '필드', '이전값', '새값', ''].map(h => (
                  <th key={h} style={thS}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={r.id || i} style={{ background: i % 2 === 0 ? 'transparent' : '#0d1829' }}>
                  <td style={tdS}>{r.changed_at || r.timestamp || r.date || '-'}</td>
                  <td style={tdS}>{r.lot_no || r.lot || '-'}</td>
                  <td style={{ ...tdS, color: ACCENT }}>{r.field || '-'}</td>
                  <td style={{ ...tdS, color: '#f87171' }}>{r.old_value ?? '-'}</td>
                  <td style={{ ...tdS, color: '#34d399' }}>{r.new_value ?? '-'}</td>
                  <td style={tdS}>
                    <button onClick={() => revert(r.id)} style={btnS('#7c3aed')}>되돌리기</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

/* ================================================================
   TAB 3: 백업
   ================================================================ */
function BackupTab({ showToast }) {
  const [backups, setBackups] = useState([]);
  const [memo, setMemo] = useState('');
  const [loading, setLoading] = useState(false);
  const [confirm, setConfirm] = useState(null); // { type, filename, step }

  const loadList = useCallback(async () => {
    try {
      const data = await api.get('/backup/list');
      setBackups(data?.backups || data || []);
    } catch (e) { showToast(e.message, false); }
  }, [showToast]);

  useEffect(() => { loadList(); }, [loadList]);

  const createBackup = async () => {
    setLoading(true);
    try {
      await api.post('/backup/create', { memo });
      showToast('백업 생성 완료');
      setMemo('');
      loadList();
    } catch (e) { showToast(e.message, false); }
    finally { setLoading(false); }
  };

  const doRestore = async (filename) => {
    if (!confirm || confirm.step < 2) {
      setConfirm({ type: 'restore', filename, step: (confirm?.step || 0) + 1 });
      return;
    }
    try {
      await api.post('/backup/restore', { filename });
      showToast('복원 완료');
      setConfirm(null);
      loadList();
    } catch (e) { showToast(e.message, false); setConfirm(null); }
  };

  const doDownload = (filename) => {
    downloadFile(`/backup/download/${encodeURIComponent(filename)}`, 'GET', null, filename);
  };

  const doDelete = async (filename) => {
    try {
      await api.delete(`/backup/${encodeURIComponent(filename)}`);
      showToast('삭제 완료');
      loadList();
    } catch (e) { showToast(e.message, false); }
  };

  return (
    <div>
      {/* Create backup */}
      <div style={{ ...cardS, display: 'flex', gap: 12, alignItems: 'flex-end' }}>
        <div style={{ flex: 1 }}>
          <label style={{ fontSize: 11, color: MUTED, display: 'block', marginBottom: 3 }}>백업 메모</label>
          <input value={memo} onChange={e => setMemo(e.target.value)}
            placeholder="백업 설명을 입력하세요..." style={{ ...inputS, width: '100%' }} />
        </div>
        <button onClick={createBackup} disabled={loading} style={btnS(GREEN, loading)}>
          {loading ? '백업중...' : '지금 백업'}
        </button>
      </div>

      {/* Backup list */}
      {backups.length === 0 ? (
        <div style={{ textAlign: 'center', color: MUTED, padding: 40, fontSize: 13 }}>백업이 없습니다.</div>
      ) : (
        <div style={{ overflow: 'auto', maxHeight: '60vh', border: `1px solid ${BORDER}`, borderRadius: 8 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr>
                {['날짜', '크기', '메모', ''].map(h => (
                  <th key={h} style={thS}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {backups.map((b, i) => (
                <tr key={b.filename || i} style={{ background: i % 2 === 0 ? 'transparent' : '#0d1829' }}>
                  <td style={tdS}>{b.created_at || b.date || '-'}</td>
                  <td style={tdS}>{b.size || '-'}</td>
                  <td style={{ ...tdS, maxWidth: 300, overflow: 'hidden', textOverflow: 'ellipsis' }}>{b.memo || '-'}</td>
                  <td style={{ ...tdS, display: 'flex', gap: 6 }}>
                    <button onClick={() => doRestore(b.filename)} style={btnS('#7c3aed')}>복원</button>
                    <button onClick={() => doDownload(b.filename)} style={btnS(ACCENT)}>다운로드</button>
                    <button onClick={() => setConfirm({ type: 'delete', filename: b.filename, step: 1 })}
                      style={btnS(RED)}>삭제</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Restore 2-step confirm */}
      {confirm?.type === 'restore' && confirm.step === 1 && (
        <ConfirmDialog
          title="1단계: 복원 확인"
          msg={`"${confirm.filename}" 백업으로 DB를 복원하시겠습니까? 현재 데이터가 덮어씌워집니다.`}
          onOk={() => setConfirm(prev => ({ ...prev, step: 2 }))}
          onCancel={() => setConfirm(null)}
        />
      )}
      {confirm?.type === 'restore' && confirm.step === 2 && (
        <ConfirmDialog
          title="2단계: 최종 확인"
          msg="정말로 복원을 진행합니까? 이 작업은 되돌릴 수 없습니다."
          onOk={() => doRestore(confirm.filename)}
          onCancel={() => setConfirm(null)}
        />
      )}

      {/* Delete confirm */}
      {confirm?.type === 'delete' && (
        <ConfirmDialog
          title="백업 삭제"
          msg={`"${confirm.filename}" 백업 파일을 삭제하시겠습니까?`}
          onOk={() => { doDelete(confirm.filename); setConfirm(null); }}
          onCancel={() => setConfirm(null)}
        />
      )}
    </div>
  );
}

/* ================================================================
   TAB 4: 탐색기
   ================================================================ */
function ExplorerTab({ showToast }) {
  const [tables, setTables] = useState([]);
  const [selected, setSelected] = useState(null);
  const [tableData, setTableData] = useState({ rows: [], columns: [] });
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const PAGE_SIZE = 50;

  useEffect(() => {
    (async () => {
      try {
        const data = await api.get('/editor/tables');
        setTables(data?.tables || data || []);
      } catch (e) { showToast(e.message, false); }
    })();
  }, [showToast]);

  const loadTable = useCallback(async (name, pg) => {
    setLoading(true);
    try {
      const qs = new URLSearchParams({ page: pg, page_size: PAGE_SIZE });
      const data = await api.get(`/editor/table/${encodeURIComponent(name)}?${qs}`);
      setTableData({
        rows: data?.rows || data?.data || [],
        columns: data?.columns || (data?.rows?.[0] ? Object.keys(data.rows[0]) : []),
      });
      setTotal(data?.total || data?.count || 0);
    } catch (e) { showToast(e.message, false); }
    finally { setLoading(false); }
  }, [showToast]);

  const selectTable = (name) => {
    setSelected(name);
    setPage(1);
    loadTable(name, 1);
  };

  const changePage = (newPage) => {
    setPage(newPage);
    if (selected) loadTable(selected, newPage);
  };

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div style={{ display: 'flex', gap: 14, height: '70vh' }}>
      {/* Left: table list */}
      <div style={{
        ...cardS, width: 220, minWidth: 220, overflow: 'auto', marginBottom: 0,
      }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: MUTED, marginBottom: 10 }}>테이블 목록</div>
        {tables.length === 0 && <div style={{ fontSize: 11, color: MUTED }}>로딩중...</div>}
        {tables.map((t, i) => {
          const name = typeof t === 'string' ? t : t.name;
          const count = typeof t === 'object' ? t.row_count ?? t.count : null;
          return (
            <div
              key={name || i}
              onClick={() => selectTable(name)}
              style={{
                padding: '7px 10px', borderRadius: 6, cursor: 'pointer', marginBottom: 2,
                fontSize: 12, display: 'flex', justifyContent: 'space-between',
                background: selected === name ? '#1e3a5f' : 'transparent',
                color: selected === name ? TEXT : MUTED,
              }}
            >
              <span>{name}</span>
              {count != null && (
                <span style={{ fontSize: 10, color: '#475569' }}>{count}</span>
              )}
            </div>
          );
        })}
      </div>

      {/* Right: table data */}
      <div style={{ ...cardS, flex: 1, overflow: 'auto', marginBottom: 0, display: 'flex', flexDirection: 'column' }}>
        {!selected && (
          <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: MUTED, fontSize: 13 }}>
            왼쪽에서 테이블을 선택하세요.
          </div>
        )}
        {selected && (
          <>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
              <div style={{ fontSize: 13, fontWeight: 700, color: TEXT }}>
                {selected} <span style={{ fontWeight: 400, color: MUTED, fontSize: 11 }}>({total}행)</span>
              </div>
              <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                <button onClick={() => changePage(Math.max(1, page - 1))} disabled={page <= 1} style={btnS('#334155', page <= 1)}>이전</button>
                <span style={{ fontSize: 11, color: MUTED }}>{page} / {totalPages}</span>
                <button onClick={() => changePage(Math.min(totalPages, page + 1))} disabled={page >= totalPages} style={btnS('#334155', page >= totalPages)}>다음</button>
              </div>
            </div>

            {loading && <div style={{ color: MUTED, padding: 16 }}>로딩중...</div>}

            {!loading && tableData.rows.length > 0 && (
              <div style={{ flex: 1, overflow: 'auto', border: `1px solid ${BORDER}`, borderRadius: 8 }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr>
                      {tableData.columns.map(c => <th key={c} style={thS}>{c}</th>)}
                    </tr>
                  </thead>
                  <tbody>
                    {tableData.rows.map((row, ri) => (
                      <tr key={ri} style={{ background: ri % 2 === 0 ? 'transparent' : '#0d1829' }}>
                        {tableData.columns.map(c => (
                          <td key={c} style={{ ...tdS, maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                            {row[c] ?? '-'}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {!loading && tableData.rows.length === 0 && (
              <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: MUTED, fontSize: 13 }}>
                데이터가 없습니다.
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

/* ================================================================
   TAB 5: 정합성
   ================================================================ */
function IntegrityTab({ showToast }) {
  const [health, setHealth] = useState(null);
  const [checkResult, setCheckResult] = useState(null);
  const [checking, setChecking] = useState(false);

  useEffect(() => {
    (async () => {
      try {
        const data = await api.get('/editor/db-health');
        setHealth(data);
      } catch (e) { showToast(e.message, false); }
    })();
  }, [showToast]);

  const runCheck = async () => {
    setChecking(true);
    try {
      const data = await api.get('/tools/integrity-check');
      setCheckResult(data);
      showToast('정합성 검사 완료');
    } catch (e) { showToast(e.message, false); }
    finally { setChecking(false); }
  };

  const kpis = health ? [
    { label: 'DB 크기', value: health.db_size || health.dbSize || '-', icon: '\ud83d\uddc4\ufe0f' },
    { label: 'WAL 크기', value: health.wal_size || health.walSize || '-', icon: '\ud83d\udcdd' },
    { label: '인덱스 수', value: health.index_count ?? health.indexCount ?? '-', icon: '\ud83d\uddc2\ufe0f' },
    { label: '24h 수정건수', value: health.changes_24h ?? health.recentChanges ?? '-', icon: '\ud83d\udd04' },
  ] : [];

  const issues = checkResult?.issues || checkResult?.results || checkResult?.items || [];

  return (
    <div>
      {/* KPI cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14, marginBottom: 20 }}>
        {kpis.map(k => (
          <div key={k.label} style={{
            ...cardS, textAlign: 'center', marginBottom: 0, padding: '18px 12px',
          }}>
            <div style={{ fontSize: 24, marginBottom: 6 }}>{k.icon}</div>
            <div style={{ fontSize: 18, fontWeight: 700, color: TEXT, marginBottom: 4 }}>{k.value}</div>
            <div style={{ fontSize: 11, color: MUTED }}>{k.label}</div>
          </div>
        ))}
        {!health && (
          <div style={{ gridColumn: '1 / -1', textAlign: 'center', color: MUTED, padding: 20, fontSize: 12 }}>
            DB 상태 정보를 불러오는 중...
          </div>
        )}
      </div>

      {/* Check button */}
      <div style={{ marginBottom: 16 }}>
        <button onClick={runCheck} disabled={checking} style={btnS(ACCENT, checking)}>
          {checking ? '검사중...' : '정합성 검사 실행'}
        </button>
      </div>

      {/* Results */}
      {checkResult && (
        <div style={cardS}>
          <div style={{ fontSize: 13, fontWeight: 700, color: TEXT, marginBottom: 10 }}>
            검사 결과 {checkResult.ok || checkResult.status === 'ok'
              ? <span style={{ color: '#34d399' }}> PASS</span>
              : <span style={{ color: '#f87171' }}> ISSUES FOUND</span>}
          </div>

          {issues.length === 0 && (
            <div style={{ fontSize: 12, color: '#34d399' }}>모든 항목이 정상입니다.</div>
          )}

          {issues.length > 0 && (
            <div style={{ overflow: 'auto', maxHeight: '40vh' }}>
              {issues.map((item, i) => (
                <div key={i} style={{
                  padding: '8px 12px', borderBottom: `1px solid ${BORDER}`,
                  fontSize: 12, color: item.severity === 'error' ? '#f87171' : YELLOW,
                }}>
                  <span style={{ fontWeight: 600 }}>[{item.severity || item.level || 'info'}]</span>{' '}
                  {item.message || item.description || JSON.stringify(item)}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ================================================================
   MAIN PAGE
   ================================================================ */
export default function DbControlPage() {
  const [tab, setTab] = useState('editor');
  const [toast, showToast] = useToast();

  return (
    <div style={{ padding: 20, background: BG, minHeight: '100vh', color: TEXT }}>
      <h2 style={{ fontSize: 17, fontWeight: 700, margin: '0 0 14px 0' }}>
        DB 컨트롤 센터
      </h2>

      <div style={{ display: 'flex', gap: 0, marginBottom: 20, borderBottom: `2px solid ${BORDER}` }}>
        {TABS.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)} style={{
            padding: '10px 20px', fontSize: 13, fontWeight: tab === t.key ? 700 : 400,
            color: tab === t.key ? ACCENT : MUTED,
            borderBottom: tab === t.key ? `2px solid ${ACCENT}` : '2px solid transparent',
            background: 'none', border: 'none', cursor: 'pointer', marginBottom: -2,
          }}>{t.label}</button>
        ))}
      </div>

      {tab === 'editor'    && <EditorTab showToast={showToast} />}
      {tab === 'audit'     && <AuditTab showToast={showToast} />}
      {tab === 'backup'    && <BackupTab showToast={showToast} />}
      {tab === 'explorer'  && <ExplorerTab showToast={showToast} />}
      {tab === 'integrity' && <IntegrityTab showToast={showToast} />}

      <Toast msg={toast?.msg} ok={toast?.ok} />
    </div>
  );
}
