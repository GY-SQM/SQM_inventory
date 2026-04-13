import { useState, useRef, useEffect } from 'react';

const BASE = '/api/ai';

const QUICK_QUESTIONS = [
  '현재 AVAILABLE 재고 LOT 목록을 보여줘',
  '이번 달 출고된 LOT 수량 합계는?',
  '고객별 출고 현황을 보여줘',
  'RESERVED 상태 LOT 목록은?',
  '최근 반품된 LOT은?',
];

function MsgBubble({ role, content, data, columns }) {
  const isUser = role === 'user';
  return (
    <div style={{
      display: 'flex', justifyContent: isUser ? 'flex-end' : 'flex-start',
      marginBottom: 12,
    }}>
      <div style={{
        maxWidth: '75%',
        background: isUser ? '#1d4ed8' : '#1e293b',
        color: '#f1f5f9', borderRadius: isUser ? '12px 12px 2px 12px' : '12px 12px 12px 2px',
        padding: '10px 14px', fontSize: 13,
      }}>
        <div style={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>{content}</div>

        {/* 조회 결과 테이블 */}
        {data && data.length > 0 && columns && (
          <div style={{ marginTop: 10, overflow: 'auto', maxHeight: 260 }}>
            <table style={{ borderCollapse: 'collapse', fontSize: 11, width: '100%' }}>
              <thead>
                <tr>
                  {columns.map(c => (
                    <th key={c} style={{
                      padding: '4px 8px', background: '#0f172a',
                      color: '#94a3b8', fontWeight: 600, whiteSpace: 'nowrap',
                      borderBottom: '1px solid #334155',
                    }}>{c}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {data.slice(0, 30).map((row, i) => (
                  <tr key={i}>
                    {columns.map(c => (
                      <td key={c} style={{
                        padding: '3px 8px', color: '#cbd5e1',
                        borderBottom: '1px solid #1e293b', whiteSpace: 'nowrap',
                      }}>
                        {row[c] !== null && row[c] !== undefined ? String(row[c]) : '-'}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
            {data.length > 30 && (
              <div style={{ fontSize: 10, color: '#64748b', marginTop: 4 }}>
                … 외 {data.length - 30}건 더 있음
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default function AiChatPage() {
  const [messages, setMessages]   = useState([]);
  const [input,    setInput]      = useState('');
  const [loading,  setLoading]    = useState(false);
  const [status,   setStatus]     = useState(null);
  const bottomRef                 = useRef(null);

  // Gemini 상태 확인
  useEffect(() => {
    fetch(`${BASE}/status`)
      .then(r => r.json())
      .then(setStatus)
      .catch(() => setStatus({ available: false }));
  }, []);

  // 자동 스크롤
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const send = async (q = input.trim()) => {
    if (!q || loading) return;
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: q }]);
    setLoading(true);
    try {
      const r = await fetch(`${BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q }),
      });
      const d = await r.json();
      setMessages(prev => [...prev, {
        role:    'assistant',
        content: d.answer || '응답을 받지 못했습니다.',
        data:    d.data,
        columns: d.columns,
      }]);
    } catch (e) {
      setMessages(prev => [...prev, { role: 'assistant', content: `오류: ${e.message}` }]);
    }
    setLoading(false);
  };

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 42px)', padding: 24, gap: 16 }}>
      <div>
        <h2 style={{ color: '#f1f5f9', marginBottom: 4 }}>🤖 AI 재고 조회</h2>
        <p style={{ fontSize: 12, color: '#64748b' }}>
          자연어로 재고를 조회합니다. Gemini AI가 SQL을 생성하고 결과를 요약합니다.
        </p>
        {status && (
          <div style={{
            display: 'inline-flex', alignItems: 'center', gap: 6,
            padding: '4px 10px', borderRadius: 999, fontSize: 11, marginTop: 6,
            background: status.available ? '#064e3b' : '#450a0a',
            color: status.available ? '#34d399' : '#f87171',
          }}>
            {status.available ? '● Gemini AI 연결됨' : '● Gemini AI 미연결 (기본 조회 모드)'}
          </div>
        )}
      </div>

      {/* 빠른 질문 */}
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
        {QUICK_QUESTIONS.map((q, i) => (
          <button key={i} onClick={() => send(q)} disabled={loading}
            style={{
              padding: '5px 12px', fontSize: 11, background: '#1e293b',
              color: '#94a3b8', border: '1px solid #334155', borderRadius: 999,
              cursor: loading ? 'not-allowed' : 'pointer',
            }}>
            {q}
          </button>
        ))}
      </div>

      {/* 채팅 영역 */}
      <div style={{
        flex: 1, overflow: 'auto', background: '#0f172a',
        border: '1px solid #334155', borderRadius: 8, padding: 16,
      }}>
        {messages.length === 0 && (
          <div style={{ textAlign: 'center', color: '#475569', fontSize: 13, marginTop: 60 }}>
            위의 빠른 질문을 클릭하거나 직접 입력해 주세요.
          </div>
        )}
        {messages.map((m, i) => (
          <MsgBubble key={i} {...m} />
        ))}
        {loading && (
          <div style={{ display: 'flex', justifyContent: 'flex-start', marginBottom: 12 }}>
            <div style={{ background: '#1e293b', color: '#64748b', borderRadius: '12px 12px 12px 2px', padding: '10px 14px', fontSize: 13 }}>
              ⏳ 분석 중...
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* 입력창 */}
      <div style={{ display: 'flex', gap: 8 }}>
        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKey}
          placeholder="예: LC-A 제품의 현재 AVAILABLE 재고 합계를 알려줘"
          rows={2}
          style={{
            flex: 1, padding: '10px 12px', fontSize: 13,
            background: '#1e293b', border: '1px solid #334155', borderRadius: 8,
            color: '#f1f5f9', resize: 'none', fontFamily: 'inherit',
          }}
        />
        <button
          onClick={() => send()}
          disabled={loading || !input.trim()}
          style={{
            padding: '0 20px', background: input.trim() && !loading ? '#2563eb' : '#334155',
            color: input.trim() && !loading ? '#fff' : '#64748b',
            border: 'none', borderRadius: 8, cursor: input.trim() && !loading ? 'pointer' : 'not-allowed',
            fontSize: 13, fontWeight: 700,
          }}
        >
          전송
        </button>
      </div>
      <div style={{ fontSize: 10, color: '#475569' }}>
        Enter로 전송 / Shift+Enter 줄바꿈
      </div>
    </div>
  );
}
