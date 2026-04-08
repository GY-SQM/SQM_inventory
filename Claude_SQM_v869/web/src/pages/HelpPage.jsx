import { useState } from 'react';

const cardS = { background: '#1e293b', border: '1px solid #334155', borderRadius: 8, padding: '16px 20px', marginBottom: 14 };
const titleS = { fontSize: 13, fontWeight: 700, color: '#94a3b8', marginBottom: 12 };
const tdS = { padding: '7px 12px', borderBottom: '1px solid #1e293b', fontSize: 12, color: '#e2e8f0' };
const thS = { padding: '7px 12px', background: '#0f172a', color: '#64748b', fontWeight: 700, fontSize: 11, textAlign: 'left', borderBottom: '2px solid #334155' };

const SHORTCUTS = [
  ['F5',            '새로고침'],
  ['Ctrl + F',      '통합 검색'],
  ['Ctrl + N',      '입고 (새 LOT)'],
  ['Ctrl + O',      '출고'],
  ['Ctrl + R',      '반품'],
  ['Ctrl + B',      '백업 생성'],
  ['Ctrl + S',      '설정'],
  ['Alt + 1~9',     '탭 직접 이동'],
  ['Esc',           '모달 닫기'],
  ['우클릭 (Inventory)', '즉시 출고'],
];

const STATUSES = [
  { status: 'AVAILABLE', color: '#34d399', bg: '#064e3b', desc: '출고 가능한 재고. 출고/예약 가능.' },
  { status: 'RESERVED',  color: '#fbbf24', bg: '#3b2a00', desc: 'Allocation 예약됨. 출고 대기 중.' },
  { status: 'PICKED',    color: '#93c5fd', bg: '#1e3a5f', desc: 'Picking 완료. 출고 확정 대기.' },
  { status: 'OUTBOUND',  color: '#c4b5fd', bg: '#2d1f6e', desc: '출고 완료. 창고 반출됨.' },
  { status: 'SOLD',      color: '#a78bfa', bg: '#3b0764', desc: 'Sales Order 처리 완료.' },
  { status: 'RETURN',    color: '#f87171', bg: '#450a0a', desc: '반품 대기 중. 재입고 가능.' },
  { status: 'STAGED',    color: '#fb923c', bg: '#431407', desc: 'Allocation STAGED 예약 상태.' },
  { status: 'DEPLETED',  color: '#94a3b8', bg: '#1e293b', desc: '재고 소진. 더 이상 사용 불가.' },
  { status: 'CANCELLED', color: '#64748b', bg: '#0f172a', desc: '취소된 Allocation 또는 LOT.' },
];

const WORKFLOW = [
  { step: '1. 입고',        desc: '입고 서류 (BL+PL+FA+DO) 업로드 → LOT 생성 → AVAILABLE', color: '#34d399' },
  { step: '2. Allocation',  desc: 'Excel Allocation 업로드 → 승인 → RESERVED 예약', color: '#fbbf24' },
  { step: '3. Picking',     desc: 'Picking List PDF 파싱 → PICKED 상태로 전환', color: '#93c5fd' },
  { step: '4. 출고',        desc: 'Scan 탭 [출고확정] 또는 OutboundModal → OUTBOUND', color: '#c4b5fd' },
  { step: '5. SOLD',        desc: 'Sales Order Excel 업로드 → SOLD 처리 완료', color: '#a78bfa' },
  { step: '6. 반품',        desc: 'Return 탭 → RETURN → 재입고 시 AVAILABLE 복구', color: '#f87171' },
];

const TABS_HELP = [
  ['Dashboard', '재고 요약 KPI + 최근 입출고 현황'],
  ['Inventory', 'LOT별 전체 재고 조회. 우클릭 즉시 출고 가능.'],
  ['Allocation', 'Excel Allocation 계획 목록. 승인/반려 관리.'],
  ['Picked', '피킹 완료 목록. PICKED 상태 톤백.'],
  ['Outbound', '출고 예정/완료 목록.'],
  ['Return', '반품 접수 및 재입고 처리.'],
  ['Move', '바코드 스캔으로 톤백 위치 이동.'],
  ['Scan', '출고확정/반품/재입고/위치이동 4버튼 스캔.'],
  ['Log', '감사 로그 / 재고 이동 이력 / 운영 로그.'],
  ['Summary', '재고 KPI 카드 + 상태별 집계 + 바 차트.'],
  ['AI Chat', 'Gemini AI로 자연어 재고 조회.'],
  ['Reports', '보고서 생성 및 서류 업로드 처리.'],
  ['Settings', '시스템 설정 (Gemini/이메일/백업/선사 패턴).'],
];

const TABS = [
  { key: 'shortcut', label: '⌨️ 단축키' },
  { key: 'status',   label: '🏷️ STATUS 안내' },
  { key: 'workflow', label: '🔄 업무 흐름' },
  { key: 'tabs',     label: '📋 탭 안내' },
];

export default function HelpPage() {
  const [tab, setTab] = useState('shortcut');

  return (
    <div style={{ padding: 24 }}>
      <h2 style={{ color: '#f1f5f9', marginBottom: 4 }}>❓ 도움말</h2>
      <p style={{ fontSize: 12, color: '#64748b', marginBottom: 16 }}>SQM v8.6.8 사용 안내</p>

      {/* 탭 */}
      <div style={{ display: 'flex', borderBottom: '2px solid #334155', marginBottom: 16 }}>
        {TABS.map(t => (
          <button key={t.key} onClick={() => setTab(t.key)} style={{
            padding: '8px 18px', fontSize: 13, fontWeight: tab === t.key ? 700 : 400,
            color: tab === t.key ? '#38bdf8' : '#64748b',
            borderBottom: tab === t.key ? '2px solid #38bdf8' : '2px solid transparent',
            background: 'none', border: 'none', cursor: 'pointer', marginBottom: -2,
          }}>{t.label}</button>
        ))}
      </div>

      {/* 단축키 */}
      {tab === 'shortcut' && (
        <div style={cardS}>
          <div style={titleS}>⌨️ 단축키 목록</div>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead><tr><th style={thS}>단축키</th><th style={thS}>기능</th></tr></thead>
            <tbody>
              {SHORTCUTS.map(([k, v]) => (
                <tr key={k}>
                  <td style={{ ...tdS, fontFamily: 'monospace', color: '#38bdf8', fontWeight: 600 }}>{k}</td>
                  <td style={tdS}>{v}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* STATUS 안내 */}
      {tab === 'status' && (
        <div style={cardS}>
          <div style={titleS}>🏷️ STATUS 상태값 안내</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {STATUSES.map(s => (
              <div key={s.status} style={{ display: 'flex', gap: 12, alignItems: 'center', padding: '8px 12px', background: '#0f172a', borderRadius: 6 }}>
                <span style={{ display: 'inline-block', padding: '3px 12px', borderRadius: 999, fontSize: 11, fontWeight: 700, background: s.bg, color: s.color, minWidth: 90, textAlign: 'center' }}>
                  {s.status}
                </span>
                <span style={{ fontSize: 13, color: '#e2e8f0' }}>{s.desc}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 업무 흐름 */}
      {tab === 'workflow' && (
        <div style={cardS}>
          <div style={titleS}>🔄 업무 흐름 (LOT 라이프사이클)</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {WORKFLOW.map((w, i) => (
              <div key={i} style={{ display: 'flex', gap: 12, alignItems: 'flex-start', padding: '10px 14px', background: '#0f172a', borderRadius: 6, borderLeft: `4px solid ${w.color}` }}>
                <span style={{ fontSize: 13, fontWeight: 700, color: w.color, minWidth: 110 }}>{w.step}</span>
                <span style={{ fontSize: 13, color: '#e2e8f0' }}>{w.desc}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 탭 안내 */}
      {tab === 'tabs' && (
        <div style={cardS}>
          <div style={titleS}>📋 각 탭 기능 안내</div>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead><tr><th style={thS}>탭</th><th style={thS}>기능</th></tr></thead>
            <tbody>
              {TABS_HELP.map(([t, d]) => (
                <tr key={t}>
                  <td style={{ ...tdS, fontWeight: 600, color: '#38bdf8', whiteSpace: 'nowrap' }}>{t}</td>
                  <td style={tdS}>{d}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
