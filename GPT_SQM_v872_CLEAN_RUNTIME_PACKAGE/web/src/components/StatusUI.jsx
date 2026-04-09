export function Loading({ message = 'Loading...' }) {
  return <div style={{ padding: 24, textAlign: 'center', color: 'var(--text-secondary)' }}>{message}</div>;
}

export function ErrorBox({ message }) {
  return (
    <div style={{
      padding: 12, margin: '8px 0', borderRadius: 6,
      background: '#fef2f2', border: '1px solid #fecaca',
      color: '#991b1b', fontSize: 12,
    }}>
      {message}
    </div>
  );
}

export function EmptyState({ message = 'No results found' }) {
  return (
    <div style={{
      padding: 40, textAlign: 'center',
      color: 'var(--text-muted)', fontSize: 13,
    }}>
      {message}
    </div>
  );
}

export function SuccessBox({ message }) {
  return (
    <div style={{
      padding: 12, margin: '8px 0', borderRadius: 6,
      background: '#f0fdf4', border: '1px solid #bbf7d0',
      color: '#166534', fontSize: 12,
    }}>
      {message}
    </div>
  );
}
