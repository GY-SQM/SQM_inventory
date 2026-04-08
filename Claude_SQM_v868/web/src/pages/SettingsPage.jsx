import { useState } from 'react';

const card = { padding: '16px 20px', background: 'var(--bg-card)', border: '1px solid var(--border)', borderRadius: 8, marginBottom: 12 };
const label = { fontSize: 13, fontWeight: 600, color: 'var(--text-primary)' };
const desc = { fontSize: 11, color: 'var(--text-muted)', marginTop: 2 };

export default function SettingsPage() {
  const [apiHost] = useState('127.0.0.1');
  const [apiPort] = useState('8000');

  return (
    <div style={{ padding: 24, maxWidth: 600 }}>
      <h2 style={{ marginBottom: 16 }}>Settings</h2>

      <div style={card}>
        <div style={label}>API Server</div>
        <div style={desc}>{apiHost}:{apiPort}</div>
      </div>

      <div style={card}>
        <div style={label}>Version</div>
        <div style={desc}>SQM v868 React</div>
      </div>

      <div style={card}>
        <div style={label}>Theme</div>
        <div style={desc}>Use the toggle button in the top navigation bar</div>
      </div>

      <div style={card}>
        <div style={label}>Database</div>
        <div style={desc}>SQLite — data/db/sqm_inventory.db</div>
      </div>
    </div>
  );
}
