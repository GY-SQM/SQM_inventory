/**
 * ActionBar.jsx — Quick action button bar (v864 toolbar style)
 */

const ACTION_BUTTONS = [
  { label: '📄 PDF 입고',   action: 'inboundModal',  bg: '#22c55e', hover: '#16a34a' },
  { label: '🚀 즉시 출고',  action: 'outboundModal', bg: '#3b82f6', hover: '#2563eb' },
  { label: '🔄 반품',       action: 'returnPage',    bg: '#64748b', hover: '#475569' },
  { label: '📊 재고 조회',  action: 'navInventory',  bg: '#0ea5e9', hover: '#0284c7' },
  null, // separator
  { label: '🔍 정합성',     action: 'navIntegrity',  bg: '#06b6d4', hover: '#0891b2' },
  { label: '💾 백업',       action: 'backupCreate',  bg: '#64748b', hover: '#475569' },
];

export default function ActionBar({ onAction }) {
  return (
    <div style={{
      height: 40,
      background: 'var(--nav-bg)',
      display: 'flex',
      alignItems: 'center',
      padding: '0 12px',
      gap: 16,
      borderBottom: '1px solid var(--nav-border)',
      flexShrink: 0,
    }}>
      {ACTION_BUTTONS.map((btn, idx) => {
        if (btn === null) {
          return (
            <div
              key={`sep-${idx}`}
              style={{
                width: 1,
                height: 22,
                background: 'var(--nav-border)',
                margin: '0 4px',
              }}
            />
          );
        }
        return (
          <button
            key={btn.action}
            onClick={() => onAction(btn.action)}
            style={{
              background: btn.bg,
              color: '#fff',
              fontSize: 13,
              fontWeight: 700,
              border: 'none',
              borderRadius: 6,
              padding: '6px 16px',
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              transition: 'transform 0.15s ease, background 0.15s ease',
            }}
            onMouseEnter={e => {
              e.currentTarget.style.transform = 'scale(1.03)';
              e.currentTarget.style.background = btn.hover;
            }}
            onMouseLeave={e => {
              e.currentTarget.style.transform = 'scale(1)';
              e.currentTarget.style.background = btn.bg;
            }}
          >
            {btn.label}
          </button>
        );
      })}
    </div>
  );
}
