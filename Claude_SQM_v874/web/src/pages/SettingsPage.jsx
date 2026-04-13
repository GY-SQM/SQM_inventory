import { useState, useEffect, useRef } from 'react';

const BASE_TOOLS = '/api/tools';
const BASE_RPT   = '/api/reports';

const cardS = {
  background: '#1e293b', border: '1px solid #334155',
  borderRadius: 8, padding: '16px 20px', marginBottom: 14,
};
const titleS  = { fontSize: 13, fontWeight: 700, color: '#94a3b8', marginBottom: 12 };
const inputS  = {
  padding: '7px 10px', fontSize: 13, background: '#0f172a',
  border: '1px solid #334155', borderRadius: 6, color: '#f1f5f9', width: '100%', boxSizing: 'border-box',
};
const labelS  = { fontSize: 11, color: '#64748b', display: 'block', marginBottom: 4 };
const row2    = { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 10 };
const btnS    = (c, dis) => ({
  padding: '7px 16px', border: 'none', borderRadius: 6,
  background: dis ? '#334155' : c, color: dis ? '#64748b' : '#fff',
  fontSize: 12, fontWeight: 600, cursor: dis ? 'not-allowed' : 'pointer',
});

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

function Section({ title, icon, children }) {
  const [open, setOpen] = useState(true);
  return (
    <div style={cardS}>
      <div style={{ display: 'flex', justifyContent: 'space-between', cursor: 'pointer', marginBottom: open ? 12 : 0 }}
        onClick={() => setOpen(o => !o)}>
        <div style={titleS}>{icon} {title}</div>
        <span style={{ color: '#475569', fontSize: 12 }}>{open ? '▲' : '▼'}</span>
      </div>
      {open && children}
    </div>
  );
}

export default function SettingsPage() {
  const [loading,   setLoading]   = useState({});
  const [toast,     setToast]     = useState(null);
  const [devMode,   setDevModeLS] = useState(() => localStorage.getItem('sqm_dev_mode') === 'true');
  const [dbResetConfirm1, setDbResetConfirm1] = useState(false);
  const [dbResetConfirm2, setDbResetConfirm2] = useState(false);
  const [dbResetResult,   setDbResetResult]   = useState(null);
  const toastRef              = useRef(null);

  // Gemini
  const [geminiKey,   setGeminiKey]   = useState('');
  const [geminiInfo,  setGeminiInfo]  = useState(null);
  // Email
  const [emailCfg,    setEmailCfg]    = useState({ smtp_host: 'smtp.gmail.com', smtp_port: 587, sender_email: '', app_password: '', enabled: false });
  const [emailTo,     setEmailTo]     = useState('');
  // Auto backup
  const [backupCfg,   setBackupCfg]   = useState({ enabled: false, interval_hours: 24, max_count: 10 });
  // Backup list
  const [backupList,  setBackupList]  = useState([]);
  // BL carrier
  const [carrierSummary, setCarrierSummary] = useState('');
  // Auto refresh
  const [autoRefresh, setAutoRefresh] = useState(false);
  const [refreshSec,  setRefreshSec]  = useState(30);

  const showToast = (msg, ok) => {
    setToast({ msg, ok });
    if (toastRef.current) clearTimeout(toastRef.current);
    toastRef.current = setTimeout(() => setToast(null), 3000);
  };
  const setL = (k, v) => setLoading(p => ({ ...p, [k]: v }));

  const api = async (url, method = 'GET', body = null) => {
    const opts = { method };
    if (body) { opts.headers = { 'Content-Type': 'application/json' }; opts.body = JSON.stringify(body); }
    const r = await fetch(url, opts);
    if (!r.ok) throw new Error(await r.text().catch(() => `HTTP ${r.status}`));
    return r.json();
  };

  // 초기 로드
  useEffect(() => {
    // Gemini 정보
    api(`${BASE_TOOLS}/gemini/config`).then(d => setGeminiInfo(d)).catch(() => {}); // optional: silently ignore if unavailable
    // Email 설정
    api(`${BASE_TOOLS}/email/config`).then(d => { if (d.config) setEmailCfg(prev => ({ ...prev, ...d.config })); }).catch(() => {}); // optional: silently ignore if unavailable
    // 백업 스케줄
    api(`${BASE_TOOLS}/backup/schedule`).then(d => { if (d.config) setBackupCfg(d.config); }).catch(() => {}); // optional: silently ignore if unavailable
    // 백업 목록
    api(`${BASE_TOOLS}/backup/list`).then(d => setBackupList(d.backups || [])).catch(() => {}); // optional: silently ignore if unavailable
    // 선사 패턴
    api(`${BASE_TOOLS}/bl-carrier/list`).then(d => setCarrierSummary(d.summary || '')).catch(() => {}); // optional: silently ignore if unavailable
  }, []);

  // 자동 갱신 (대시보드 새로고침 placeholder)
  useEffect(() => {
    if (!autoRefresh) return;
    const id = setInterval(() => window.dispatchEvent(new Event('sqm-refresh')), refreshSec * 1000);
    return () => clearInterval(id);
  }, [autoRefresh, refreshSec]);

  const run = async (key, fn) => {
    setL(key, true);
    try { const r = await fn(); if (r?.message) showToast(r.message, r.success !== false); }
    catch (e) { showToast(`❌ ${e.message}`, false); }
    setL(key, false);
  };

  return (
    <div style={{ padding: 24, maxWidth: 800 }}>
      <h2 style={{ color: '#f1f5f9', marginBottom: 4 }}>⚙️ 설정</h2>
      <p style={{ fontSize: 12, color: '#64748b', marginBottom: 20 }}>시스템 설정 및 운영 도구</p>

      {/* ── DB 관리 ───────────────────────────────────────────────────────── */}
      <Section title="DB 관리" icon="🗄️">
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <button style={btnS('#0891b2', loading.dbopt)} disabled={loading.dbopt}
            onClick={() => run('dbopt', () => api(`${BASE_TOOLS}/db-optimize`, 'POST'))}>
            {loading.dbopt ? '최적화 중...' : '⚡ DB 최적화 (VACUUM)'}
          </button>
          <button style={btnS('#22c55e', loading.backup)} disabled={loading.backup}
            onClick={() => run('backup', () => api(`${BASE_TOOLS}/backup/create`, 'POST'))}>
            {loading.backup ? '백업 중...' : '💾 백업 생성'}
          </button>
          <button style={btnS('#ef4444', loading.restore)} disabled={loading.restore}
            onClick={async () => {
              if (!window.confirm('최신 백업으로 복원하시겠습니까?\n현재 DB가 덮어씌워집니다.')) return;
              run('restore', () => api(`${BASE_TOOLS}/backup/restore-latest`, 'POST'));
            }}>
            {loading.restore ? '복원 중...' : '♻️ 최신 백업 복원'}
          </button>
          <button style={btnS('#475569', loading.bklist)} disabled={loading.bklist}
            onClick={() => run('bklist', async () => {
              const d = await api(`${BASE_TOOLS}/backup/list`);
              setBackupList(d.backups || []);
              return { success: true, message: `백업 ${(d.backups || []).length}건 조회` };
            })}>
            {loading.bklist ? '...' : '📋 백업 목록 새로고침'}
          </button>
        </div>

        {backupList.length > 0 && (
          <div style={{ marginTop: 10, overflow: 'auto', maxHeight: 160, border: '1px solid #334155', borderRadius: 6 }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 11 }}>
              <thead>
                <tr>
                  {['파일명','크기','날짜'].map(h => (
                    <th key={h} style={{ padding: '5px 10px', background: '#0f172a', color: '#64748b', textAlign: 'left', borderBottom: '1px solid #334155' }}>{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {backupList.map((b, i) => (
                  <tr key={i}>
                    <td style={{ padding: '4px 10px', color: '#e2e8f0', borderBottom: '1px solid #1e293b' }}>{b.filename || b.name}</td>
                    <td style={{ padding: '4px 10px', color: '#94a3b8', borderBottom: '1px solid #1e293b' }}>{b.size || '-'}</td>
                    <td style={{ padding: '4px 10px', color: '#64748b', borderBottom: '1px solid #1e293b' }}>{(b.created_at || b.date || '').slice(0,16)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Section>

      {/* ── 자동 백업 스케줄 ─────────────────────────────────────────────── */}
      <Section title="자동 백업 스케줄" icon="⏰">
        <div style={row2}>
          <div>
            <label style={labelS}>백업 주기 (시간)</label>
            <input style={inputS} type="number" value={backupCfg.interval_hours}
              onChange={e => setBackupCfg(p => ({ ...p, interval_hours: parseInt(e.target.value) || 24 }))} />
          </div>
          <div>
            <label style={labelS}>최대 보관 개수</label>
            <input style={inputS} type="number" value={backupCfg.max_count}
              onChange={e => setBackupCfg(p => ({ ...p, max_count: parseInt(e.target.value) || 10 }))} />
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: '#f1f5f9', cursor: 'pointer' }}>
            <input type="checkbox" checked={backupCfg.enabled}
              onChange={e => setBackupCfg(p => ({ ...p, enabled: e.target.checked }))} />
            자동 백업 활성화
          </label>
          <button style={btnS('#22c55e', loading.bksch)} disabled={loading.bksch}
            onClick={() => run('bksch', () => api(`${BASE_TOOLS}/backup/schedule`, 'POST', backupCfg))}>
            {loading.bksch ? '저장 중...' : '💾 저장'}
          </button>
        </div>
      </Section>

      {/* ── DN 교차검증 ──────────────────────────────────────────────────── */}
      <Section title="DN 교차검증" icon="🔍">
        <button style={btnS('#7c3aed', loading.dn)} disabled={loading.dn}
          onClick={() => run('dn', () => api(`${BASE_TOOLS}/dn-cross-check`))}>
          {loading.dn ? '검증 중...' : '🔍 DN 교차검증 실행'}
        </button>
      </Section>

      {/* ── Gemini AI 설정 ───────────────────────────────────────────────── */}
      <Section title="Gemini AI 설정" icon="🤖">
        {geminiInfo && (
          <div style={{ fontSize: 12, marginBottom: 10, color: geminiInfo.has_key ? '#34d399' : '#f87171' }}>
            {geminiInfo.has_key
              ? `✅ API 키 설정됨 (${geminiInfo.source}) — ${geminiInfo.masked_key}`
              : '❌ API 키 없음'}
          </div>
        )}
        <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
          <input style={{ ...inputS, flex: 1 }} type="password"
            placeholder="Gemini API 키 입력 (AIza...)"
            value={geminiKey} onChange={e => setGeminiKey(e.target.value)} />
          <button style={btnS('#2563eb', loading.gemcfg || !geminiKey)} disabled={loading.gemcfg || !geminiKey}
            onClick={() => run('gemcfg', async () => {
              const r = await api(`${BASE_TOOLS}/gemini/config`, 'POST', { api_key: geminiKey });
              if (r.success) { setGeminiKey(''); const info = await api(`${BASE_TOOLS}/gemini/config`); setGeminiInfo(info); }
              return r;
            })}>
            {loading.gemcfg ? '저장 중...' : '💾 저장'}
          </button>
          <button style={btnS('#0891b2', loading.gemtest)} disabled={loading.gemtest}
            onClick={() => run('gemtest', () => api(`${BASE_TOOLS}/gemini/test`, 'POST'))}>
            {loading.gemtest ? '테스트 중...' : '🔬 테스트'}
          </button>
        </div>
      </Section>

      {/* ── 이메일 설정 ──────────────────────────────────────────────────── */}
      <Section title="이메일 설정 (Gmail SMTP)" icon="📧">
        <div style={row2}>
          <div>
            <label style={labelS}>발신자 이메일</label>
            <input style={inputS} value={emailCfg.sender_email}
              onChange={e => setEmailCfg(p => ({ ...p, sender_email: e.target.value }))}
              placeholder="your@gmail.com" />
          </div>
          <div>
            <label style={labelS}>앱 비밀번호</label>
            <input style={inputS} type="password" value={emailCfg.app_password}
              onChange={e => setEmailCfg(p => ({ ...p, app_password: e.target.value }))}
              placeholder="Gmail 앱 비밀번호" />
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: '#f1f5f9', cursor: 'pointer' }}>
            <input type="checkbox" checked={emailCfg.enabled}
              onChange={e => setEmailCfg(p => ({ ...p, enabled: e.target.checked }))} />
            이메일 알림 활성화
          </label>
          <button style={btnS('#22c55e', loading.emailsave)} disabled={loading.emailsave}
            onClick={() => run('emailsave', () => api(`${BASE_TOOLS}/email/config`, 'POST', emailCfg))}>
            {loading.emailsave ? '저장 중...' : '💾 저장'}
          </button>
          <input style={{ ...inputS, width: 200 }} placeholder="테스트 수신 이메일"
            value={emailTo} onChange={e => setEmailTo(e.target.value)} />
          <button style={btnS('#f59e0b', loading.emailtest || !emailTo)} disabled={loading.emailtest || !emailTo}
            onClick={() => run('emailtest', () => api(`${BASE_TOOLS}/email/test`, 'POST', { to: emailTo }))}>
            {loading.emailtest ? '전송 중...' : '📤 테스트 발송'}
          </button>
        </div>
      </Section>

      {/* ── BL 선사 패턴 ─────────────────────────────────────────────────── */}
      <Section title="BL 선사 패턴" icon="🚢">
        {carrierSummary && (
          <pre style={{ fontSize: 11, color: '#94a3b8', background: '#0f172a',
            padding: 10, borderRadius: 6, marginBottom: 10, whiteSpace: 'pre-wrap' }}>
            {carrierSummary}
          </pre>
        )}
        <button style={btnS('#475569', loading.carrier)} disabled={loading.carrier}
          onClick={() => run('carrier', async () => {
            const d = await api(`${BASE_TOOLS}/bl-carrier/list`);
            setCarrierSummary(d.summary || '');
            return { success: true, message: '선사 패턴 목록 새로고침' };
          })}>
          {loading.carrier ? '...' : '🔄 새로고침'}
        </button>
      </Section>

      {/* ── 대시보드 자동 갱신 ───────────────────────────────────────────── */}
      <Section title="대시보드 자동 갱신" icon="🔄">
        <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: '#f1f5f9', cursor: 'pointer' }}>
            <input type="checkbox" checked={autoRefresh}
              onChange={e => setAutoRefresh(e.target.checked)} />
            자동 갱신 활성화
          </label>
          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <label style={{ fontSize: 12, color: '#64748b' }}>갱신 주기</label>
            <input style={{ ...inputS, width: 70 }} type="number"
              value={refreshSec} onChange={e => setRefreshSec(parseInt(e.target.value) || 30)} />
            <span style={{ fontSize: 12, color: '#64748b' }}>초</span>
          </div>
          <span style={{ fontSize: 12, color: autoRefresh ? '#34d399' : '#475569' }}>
            {autoRefresh ? `✅ ${refreshSec}초마다 갱신 중` : '비활성화'}
          </span>
        </div>
      </Section>

      {/* ── UI 레이아웃 ──────────────────────────────────────────────────── */}
      <Section title="UI 레이아웃" icon="🎨">
        <p style={{ fontSize: 12, color: '#64748b', marginBottom: 10 }}>
          테마, 글꼴 크기, 사이드바 상태 등 UI 설정을 초기값으로 되돌립니다.
        </p>
        <button
          onClick={() => {
            if (window.confirm('UI 설정을 초기화하시겠습니까? 페이지가 새로고침됩니다.')) {
              ['sqm_theme', 'sqm_font_scale', 'sqm_dev_mode'].forEach(k => localStorage.removeItem(k));
              window.location.reload();
            }
          }}
          style={btnS('#475569', false)}
        >
          🔄 레이아웃 초기화 (기본값 복원)
        </button>
      </Section>

      {/* ── 시스템 정보 ──────────────────────────────────────────────────── */}
      <Section title="시스템 정보" icon="ℹ️">
        <div style={{ display: 'flex', gap: 20, flexWrap: 'wrap', fontSize: 12 }}>
          {[
            ['버전', 'SQM v8.6.9'],
            ['API', 'FastAPI v0.6.0'],
            ['React', 'Vite + React 18'],
            ['DB', 'SQLite'],
          ].map(([k, v]) => (
            <div key={k}>
              <span style={{ color: '#64748b', marginRight: 6 }}>{k}</span>
              <span style={{ color: '#38bdf8', fontWeight: 600 }}>{v}</span>
            </div>
          ))}
        </div>
      </Section>

      {/* ── 개발자 도구 (devMode 전용) ──────────────────────────────────── */}
      {devMode && (
        <Section title="개발자 도구" icon="🔧">
          <div style={{ padding: '8px 12px', background: '#450a0a', border: '1px solid #f87171', borderRadius: 6, marginBottom: 12, fontSize: 12, color: '#fca5a5' }}>
            ⚠️ 아래 기능은 개발/테스트 전용입니다. Production 환경에서는 자동 차단됩니다.
          </div>

          {/* 테스트 DB 초기화 */}
          {!dbResetConfirm1 && (
            <button onClick={() => setDbResetConfirm1(true)}
              style={{ padding: '8px 20px', background: '#dc2626', color: '#fff', border: 'none', borderRadius: 6, cursor: 'pointer', fontWeight: 700, fontSize: 13 }}>
              🗑️ 테스트 DB 초기화
            </button>
          )}

          {/* 1단계 확인 */}
          {dbResetConfirm1 && !dbResetConfirm2 && (
            <div style={{ padding: 16, background: '#1e293b', border: '1px solid #dc2626', borderRadius: 8 }}>
              <p style={{ color: '#f87171', fontWeight: 700, marginBottom: 8 }}>정말 모든 로그 데이터를 삭제하시겠습니까?</p>
              <p style={{ fontSize: 12, color: '#94a3b8', marginBottom: 12 }}>audit_log, operation_log 등 이력 테이블이 초기화됩니다.</p>
              <div style={{ display: 'flex', gap: 10 }}>
                <button onClick={() => setDbResetConfirm1(false)}
                  style={btnS('#334155', false)}>취소</button>
                <button onClick={() => setDbResetConfirm2(true)}
                  style={btnS('#dc2626', false)}>계속 진행</button>
              </div>
            </div>
          )}

          {/* 2단계 확인 */}
          {dbResetConfirm2 && (
            <div style={{ padding: 16, background: '#1e293b', border: '2px solid #dc2626', borderRadius: 8 }}>
              <p style={{ color: '#fca5a5', fontWeight: 700, marginBottom: 8 }}>이 작업은 되돌릴 수 없습니다.</p>
              <p style={{ fontSize: 12, color: '#fbbf24', marginBottom: 12 }}>💾 백업을 먼저 생성하는 것을 강력히 권장합니다.</p>
              <div style={{ display: 'flex', gap: 10 }}>
                <button onClick={() => { setDbResetConfirm1(false); setDbResetConfirm2(false); }}
                  style={btnS('#334155', false)}>취소</button>
                <button
                  onClick={async () => {
                    setL('dbReset', true);
                    try {
                      const res = await fetch('/api/tools/reset-test-db', {
                        method: 'POST',
                        headers: { 'X-Confirm-Reset': 'CONFIRM_RESET' },
                      });
                      const data = await res.json();
                      setDbResetResult(data);
                      setDbResetConfirm1(false);
                      setDbResetConfirm2(false);
                      showToast(data.success ? `✅ ${data.message}` : `❌ ${data.detail || 'Failed'}`, data.success);
                    } catch (e) {
                      showToast(`❌ ${e.message}`, false);
                    }
                    setL('dbReset', false);
                  }}
                  disabled={loading.dbReset}
                  style={btnS('#dc2626', loading.dbReset)}>
                  {loading.dbReset ? '초기화 중...' : '최종 확인 — 초기화 실행'}
                </button>
              </div>
            </div>
          )}

          {dbResetResult && (
            <div style={{ marginTop: 12, padding: '8px 14px', background: '#0f172a', borderRadius: 6, fontSize: 12, color: '#94a3b8' }}>
              초기화 결과: {JSON.stringify(dbResetResult)}
            </div>
          )}
        </Section>
      )}

      {toast && <Toast msg={toast.msg} ok={toast.ok} />}
    </div>
  );
}
