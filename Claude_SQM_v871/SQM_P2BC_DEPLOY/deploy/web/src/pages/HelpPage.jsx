/**
 * HelpPage v2 — 다크테마 + 섹션 검색
 * 배치: web/src/pages/HelpPage.jsx
 */
import { useState } from 'react';

const cardS = { background:'#1e293b', border:'1px solid #334155', borderRadius:10, padding:'16px 20px', marginBottom:14 };
const titleS = { fontSize:13, fontWeight:700, color:'#94a3b8', marginBottom:12 };
const thS = { padding:'7px 12px', background:'#0f172a', color:'#64748b', fontWeight:700, fontSize:11, textAlign:'left', borderBottom:'2px solid #334155' };
const tdS = { padding:'7px 12px', borderBottom:'1px solid #1e293b', fontSize:12, color:'#e2e8f0' };

const SHORTCUTS = [
  ['F5','새로고침'],
  ['Ctrl+F','통합 검색'],
  ['Ctrl+N','입고 (새 LOT)'],
  ['Ctrl+O','출고'],
  ['Ctrl+R','반품'],
  ['Ctrl+B','백업 생성'],
  ['Esc','모달 닫기'],
  ['우클릭','즉시 출고 (Inventory)'],
];

const STATUSES = [
  { status:'AVAILABLE', color:'#22c55e', desc:'출고 가능 재고. 출고/예약 가능.' },
  { status:'RESERVED',  color:'#f59e0b', desc:'Allocation 예약됨. 출고 대기 중.' },
  { status:'PICKED',    color:'#3b82f6', desc:'피킹 완료. 출고 확정 대기.' },
  { status:'OUTBOUND',  color:'#8b5cf6', desc:'출고 완료. 창고 반출됨.' },
  { status:'RETURN',    color:'#ef4444', desc:'반품 대기 중. 재입고 가능.' },
  { status:'DEPLETED',  color:'#94a3b8', desc:'재고 소진. 사용 불가.' },
];

const WORKFLOW = [
  { step:'1. 입고',       desc:'BL+PL+FA+DO 업로드 → LOT 생성 → AVAILABLE', color:'#22c55e' },
  { step:'2. Allocation', desc:'Excel 업로드 → 승인 → RESERVED 예약',        color:'#f59e0b' },
  { step:'3. Picking',    desc:'Picking List 파싱 → PICKED 상태 전환',        color:'#3b82f6' },
  { step:'4. 출고',       desc:'출고확정 버튼 → OUTBOUND',                    color:'#8b5cf6' },
  { step:'5. 반품',       desc:'Return 탭 → RETURN → 재입고 → AVAILABLE',    color:'#ef4444' },
];

const MOBILE = [
  ['스마트폰 접속',     'http://[서버IP]:5173/mobile'],
  ['바코드 스캔',       '/mobile → 📷 스캔 버튼'],
  ['Telegram 조회',    '@Claude_kdnbot /재고 /출고 /대기'],
  ['Telegram 출고확정','@Claude_kdnbot /확정 LOT번호 → /확인'],
  ['Con Return 경고',  '매일 9시 자동 알림 (3일/7일 이내)'],
];

export default function HelpPage() {
  const [keyword, setKeyword] = useState('');
  const [openSec, setOpenSec] = useState({ workflow:true, status:true, shortcuts:true, mobile:true });

  const toggle = (k) => setOpenSec(s => ({...s, [k]:!s[k]}));

  const filterText = (items, fields) => {
    if (!keyword) return items;
    return items.filter(item =>
      fields.some(f => String(item[f]||'').toLowerCase().includes(keyword.toLowerCase()))
    );
  };

  return (
    <div style={{ padding:20, background:'#0f172a', minHeight:'100vh', color:'#f1f5f9', maxWidth:900 }}>
      <div style={{ display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:20 }}>
        <h2 style={{ fontSize:18, fontWeight:700, margin:0 }}>📖 SQM 도움말</h2>
        <input value={keyword} onChange={e=>setKeyword(e.target.value)}
          placeholder="검색..."
          style={{ padding:'6px 12px', fontSize:12, borderRadius:8, border:'1px solid #334155',
            background:'#1e293b', color:'#f1f5f9', width:200 }} />
      </div>

      {/* 업무 흐름 */}
      <div style={cardS}>
        <div style={{ display:'flex', justifyContent:'space-between', cursor:'pointer' }}
          onClick={() => toggle('workflow')}>
          <div style={titleS}>🔄 업무 흐름 (Workflow)</div>
          <span style={{ color:'#64748b' }}>{openSec.workflow?'▲':'▼'}</span>
        </div>
        {openSec.workflow && (
          <div style={{ display:'flex', flexWrap:'wrap', gap:10 }}>
            {WORKFLOW.map((w,i) => (
              <div key={i} style={{ display:'flex', alignItems:'center', gap:6 }}>
                <div style={{ background:w.color+'22', border:`1px solid ${w.color}44`,
                  borderRadius:8, padding:'8px 14px', minWidth:160 }}>
                  <div style={{ fontSize:12, fontWeight:700, color:w.color }}>{w.step}</div>
                  <div style={{ fontSize:11, color:'#94a3b8', marginTop:3 }}>{w.desc}</div>
                </div>
                {i < WORKFLOW.length-1 && <span style={{ color:'#334155', fontSize:18 }}>→</span>}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 상태 코드 */}
      <div style={cardS}>
        <div style={{ display:'flex', justifyContent:'space-between', cursor:'pointer' }}
          onClick={() => toggle('status')}>
          <div style={titleS}>🏷️ 상태 코드 설명</div>
          <span style={{ color:'#64748b' }}>{openSec.status?'▲':'▼'}</span>
        </div>
        {openSec.status && (
          <table style={{ width:'100%', borderCollapse:'collapse' }}>
            <thead><tr>
              <th style={thS}>상태</th>
              <th style={thS}>설명</th>
            </tr></thead>
            <tbody>
              {filterText(STATUSES,['status','desc']).map((s,i) => (
                <tr key={i}>
                  <td style={tdS}>
                    <span style={{ background:s.color+'22', color:s.color,
                      border:`1px solid ${s.color}44`, borderRadius:4,
                      padding:'2px 8px', fontSize:11, fontWeight:700 }}>{s.status}</span>
                  </td>
                  <td style={{...tdS, color:'#94a3b8'}}>{s.desc}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* 키보드 단축키 */}
      <div style={cardS}>
        <div style={{ display:'flex', justifyContent:'space-between', cursor:'pointer' }}
          onClick={() => toggle('shortcuts')}>
          <div style={titleS}>⌨️ 키보드 단축키</div>
          <span style={{ color:'#64748b' }}>{openSec.shortcuts?'▲':'▼'}</span>
        </div>
        {openSec.shortcuts && (
          <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:6 }}>
            {filterText(SHORTCUTS.map(([k,v])=>({key:k,val:v})),['key','val']).map((s,i) => (
              <div key={i} style={{ display:'flex', gap:10, alignItems:'center', padding:'5px 0',
                borderBottom:'1px solid #334155' }}>
                <kbd style={{ background:'#334155', color:'#f1f5f9', padding:'2px 8px',
                  borderRadius:4, fontSize:11, fontFamily:'monospace', fontWeight:700 }}>{s.key}</kbd>
                <span style={{ fontSize:12, color:'#94a3b8' }}>{s.val}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 모바일 사용법 */}
      <div style={cardS}>
        <div style={{ display:'flex', justifyContent:'space-between', cursor:'pointer' }}
          onClick={() => toggle('mobile')}>
          <div style={titleS}>📱 모바일 & Telegram 사용법</div>
          <span style={{ color:'#64748b' }}>{openSec.mobile?'▲':'▼'}</span>
        </div>
        {openSec.mobile && (
          <table style={{ width:'100%', borderCollapse:'collapse' }}>
            <thead><tr><th style={thS}>기능</th><th style={thS}>방법</th></tr></thead>
            <tbody>
              {MOBILE.map(([f,m],i) => (
                <tr key={i}>
                  <td style={{...tdS, fontWeight:600}}>{f}</td>
                  <td style={{...tdS, color:'#3b82f6', fontFamily:'monospace', fontSize:11}}>{m}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div style={{ color:'#475569', fontSize:11, textAlign:'center', marginTop:20 }}>
        SQM v8.7.1 | GY Logistics | 문의: @Claude_kdnbot
      </div>
    </div>
  );
}
