import { useState, useEffect } from 'react';

const BASE = '/api';

const cardS = { background: '#1e293b', border: '1px solid #334155', borderRadius: 8, padding: '16px 20px', marginBottom: 14 };
const titleS = { fontSize: 13, fontWeight: 700, color: '#94a3b8', marginBottom: 10 };
const monoS  = { fontFamily: 'monospace', fontSize: 11 };
const btnS   = (c) => ({ padding: '6px 14px', border: 'none', borderRadius: 6, background: c, color: '#fff', fontSize: 12, fontWeight: 600, cursor: 'pointer' });

export default function DevPage({ devMode, toggleDevMode, fontScale, increaseFontScale, decreaseFontScale, resetFontScale }) {
  const [apiLog,    setApiLog]    = useState([]);
  const [dbInfo,    setDbInfo]    = useState(null);
  const [loading,   setLoading]   = useState({});
  const [pingMs,    setPingMs]    = useState(null);

  // API 응답 시간 측정
  const ping = async () => {
    setLoading(p => ({ ...p, ping: true }));
    const t = Date.now();
    try {
      await fetch(`${BASE}/health`);
      setPingMs(Date.now() - t);
    } catch { setPingMs(-1); }
    setLoading(p => ({ ...p, ping: false }));
  };

  // DB 정보 조회
  const loadDbInfo = async () => {
    setLoading(p => ({ ...p, db: true }));
    try {
      const r = await fetch(`${BASE}/tools/integrity-check`).then(r => r.json());
      setDbInfo(r);
      setApiLog(prev => [{ time: new Date().toTimeString().slice(0,8), url: '/api/tools/integrity-check', ms: 0, status: r.success ? 200 : 500 }, ...prev].slice(0, 20));
    } catch (e) { setDbInfo({ error: e.message }); }
    setLoading(p => ({ ...p, db: false }));
  };

  // 각 API 응답 시간 벤치마크
  const benchmark = async () => {
    setLoading(p => ({ ...p, bench: true }));
    const endpoints = [
      '/api/health',
      '/api/dashboard/summary',
      '/api/tabs/allocation?page=1&page_size=10',
      '/api/tabs/audit-log?page=1&page_size=10',
    ];
    const results = [];
    for (const ep of endpoints) {
      const t = Date.now();
      try {
        const r = await fetch(ep);
        results.push({ url: ep, ms: Date.now() - t, status: r.status, time: new Date().toTimeString().slice(0,8) });
      } catch (e) {
        results.push({ url: ep, ms: -1, status: 0, time: new Date().toTimeString().slice(0,8) });
      }
    }
    setApiLog(prev => [...results, ...prev].slice(0, 30));
    setLoading(p => ({ ...p, bench: false }));
  };

  useEffect(() => { ping(); }, []);

  const lsKeys = Object.keys(localStorage).filter(k => k.startsWith('sqm_'));

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 4 }}>
        <h2 style={{ color: '#f1f5f9', margin: 0 }}>🔧 개발자 모드</h2>
        <span style={{
          padding: '2px 10px', borderRadius: 999, fontSize: 11, fontWeight: 700,
          background: devMode ? '#064e3b' : '#450a0a',
          color: devMode ? '#34d399' : '#f87171',
        }}>{devMode ? 'ON' : 'OFF'}</span>
        <button style={btnS(devMode ? '#ef4444' : '#22c55e')} onClick={toggleDevMode}>
          {devMode ? '끄기' : '켜기'}
        </button>
      </div>
      <p style={{ fontSize: 12, color: '#64748b', marginBottom: 20 }}>
        시스템 진단, API 응답 시간, DB 상태, 설정 값을 확인합니다.
      </p>

      {/* ── 글꼴 크기 ─────────────────────────────────────────────── */}
      <div style={cardS}>
        <div style={titleS}>🔤 글꼴 크기 설정</div>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
          <button style={btnS('#334155')} onClick={decreaseFontScale}>A−</button>
          <span style={{ fontSize: 28, fontWeight: 700, color: '#38bdf8', minWidth: 60, textAlign: 'center' }}>
            {Math.round(fontScale * 100)}%
          </span>
          <button style={btnS('#334155')} onClick={increaseFontScale}>A+</button>
          <button style={btnS('#475569')} onClick={resetFontScale}>초기화 (100%)</button>
          <span style={{ fontSize: 12, color: '#64748b' }}>범위: 70% ~ 150%</span>
        </div>
        <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
          {[0.8, 0.9, 1.0, 1.1, 1.2, 1.3].map(v => (
            <button key={v} onClick={() => { resetFontScale(); [0.8,0.9,1.0,1.1,1.2,1.3].forEach(x => x === v && [
              () => { for(let i=0;i<Math.round((v-1.0)/0.1);i++) increaseFontScale(); },
              () => { for(let i=0;i<Math.round((1.0-v)/0.1);i++) decreaseFontScale(); },
            ][v < 1.0 ? 1 : 0]()); }}
              style={{ ...btnS(Math.abs(fontScale - v) < 0.05 ? '#2563eb' : '#1e293b'), border: '1px solid #334155', fontSize: 11 }}>
              {Math.round(v*100)}%
            </button>
          ))}
        </div>
      </div>

      {/* ── API 응답 시간 ─────────────────────────────────────────── */}
      <div style={cardS}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 10 }}>
          <div style={titleS}>⚡ API 응답 시간</div>
          <span style={{ fontSize: 13, color: pingMs === null ? '#64748b' : pingMs < 0 ? '#f87171' : pingMs < 200 ? '#34d399' : '#fbbf24', fontWeight: 700 }}>
            {pingMs === null ? '측정 중...' : pingMs < 0 ? '연결 실패' : `${pingMs}ms`}
          </span>
        </div>
        <div style={{ display: 'flex', gap: 8, marginBottom: 10 }}>
          <button style={btnS('#2563eb')} onClick={ping} disabled={loading.ping}>{loading.ping ? '...' : '🔄 Ping'}</button>
          <button style={btnS('#7c3aed')} onClick={benchmark} disabled={loading.bench}>{loading.bench ? '측정 중...' : '📊 벤치마크'}</button>
        </div>
        {apiLog.length > 0 && (
          <div style={{ overflow: 'auto', maxHeight: 200, border: '1px solid #334155', borderRadius: 6 }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', ...monoS }}>
              <thead><tr>
                {['시간','API','응답(ms)','상태'].map(h => <th key={h} style={{ padding: '5px 10px', background: '#0f172a', color: '#64748b', textAlign: 'left', fontSize: 10, borderBottom: '1px solid #334155' }}>{h}</th>)}
              </tr></thead>
              <tbody>
                {apiLog.map((r, i) => (
                  <tr key={i}>
                    <td style={{ padding: '4px 10px', color: '#475569', borderBottom: '1px solid #1e293b', fontSize: 10 }}>{r.time}</td>
                    <td style={{ padding: '4px 10px', color: '#94a3b8', borderBottom: '1px solid #1e293b', fontSize: 10 }}>{r.url}</td>
                    <td style={{ padding: '4px 10px', color: r.ms < 0 ? '#f87171' : r.ms < 300 ? '#34d399' : '#fbbf24', borderBottom: '1px solid #1e293b', fontWeight: 700 }}>{r.ms < 0 ? 'ERR' : `${r.ms}ms`}</td>
                    <td style={{ padding: '4px 10px', color: r.status >= 200 && r.status < 300 ? '#34d399' : '#f87171', borderBottom: '1px solid #1e293b' }}>{r.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* ── DB 정보 ───────────────────────────────────────────────── */}
      <div style={cardS}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 10 }}>
          <div style={titleS}>🗄️ DB 정보</div>
          <button style={btnS('#0891b2')} onClick={loadDbInfo} disabled={loading.db}>{loading.db ? '...' : '🔄 조회'}</button>
        </div>
        {dbInfo && (
          <pre style={{ ...monoS, color: '#94a3b8', background: '#0f172a', padding: 12, borderRadius: 6, maxHeight: 200, overflow: 'auto', margin: 0, whiteSpace: 'pre-wrap' }}>
            {JSON.stringify(dbInfo, null, 2)}
          </pre>
        )}
      </div>

      {/* ── localStorage 값 ──────────────────────────────────────── */}
      <div style={cardS}>
        <div style={titleS}>💾 localStorage (SQM 설정 값)</div>
        <table style={{ width: '100%', borderCollapse: 'collapse', ...monoS }}>
          <thead><tr>
            {['키','값','조작'].map(h => <th key={h} style={{ padding: '5px 10px', background: '#0f172a', color: '#64748b', textAlign: 'left', fontSize: 10, borderBottom: '1px solid #334155' }}>{h}</th>)}
          </tr></thead>
          <tbody>
            {lsKeys.length === 0 ? (
              <tr><td colSpan={3} style={{ padding: '12px 10px', color: '#475569', textAlign: 'center', fontSize: 12 }}>없음</td></tr>
            ) : lsKeys.map(k => (
              <tr key={k}>
                <td style={{ padding: '4px 10px', color: '#38bdf8', borderBottom: '1px solid #1e293b' }}>{k}</td>
                <td style={{ padding: '4px 10px', color: '#f1f5f9', borderBottom: '1px solid #1e293b' }}>{localStorage.getItem(k)}</td>
                <td style={{ padding: '4px 10px', borderBottom: '1px solid #1e293b' }}>
                  <button onClick={() => { localStorage.removeItem(k); window.location.reload(); }}
                    style={{ ...btnS('#ef4444'), padding: '2px 8px', fontSize: 10 }}>삭제</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <button style={{ ...btnS('#475569'), marginTop: 10, fontSize: 11 }}
          onClick={() => { lsKeys.forEach(k => localStorage.removeItem(k)); window.location.reload(); }}>
          🗑️ SQM 설정 전체 초기화
        </button>
      </div>

      {/* ── 환경 정보 ─────────────────────────────────────────────── */}
      <div style={cardS}>
        <div style={titleS}>ℹ️ 환경 정보</div>
        <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap', fontSize: 12 }}>
          {[
            ['버전',       'SQM v8.6.9'],
            ['빌드',       'React + Vite'],
            ['API',        `${window.location.origin}/api`],
            ['UA',         navigator.userAgent.slice(0, 60) + '...'],
            ['화면',       `${window.innerWidth} × ${window.innerHeight}`],
            ['글꼴 배율',  `${Math.round(fontScale * 100)}%`],
          ].map(([k, v]) => (
            <div key={k}>
              <span style={{ color: '#64748b', marginRight: 6 }}>{k}</span>
              <span style={{ color: '#38bdf8', fontFamily: 'monospace', fontSize: 11 }}>{v}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
